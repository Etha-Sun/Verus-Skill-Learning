from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .data_layout import validate_output_path
from .handsoff_m0 import parse_copilot_usage, sha256_file


SEALED_GROUPS = {"verified-memory-allocator", "verified-nrkernel"}
CONDITIONS = {"h0", "h1", "h2"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _sealed_group(path: Path) -> str | None:
    return next((part for part in path.resolve().parts if part in SEALED_GROUPS), None)


def validate_paths(source: Path, out_dir: Path) -> None:
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")
    sealed_group = _sealed_group(source)
    if sealed_group:
        raise ValueError(f"sealed source is forbidden: {sealed_group}")
    source_resolved = source.resolve()
    verified_parent = next(
        (parent for parent in source_resolved.parents if parent.name.startswith("verified-")),
        None,
    )
    if verified_parent is not None:
        raw_root = verified_parent.parent
        output = out_dir.resolve()
        if output == raw_root or raw_root in output.parents:
            raise ValueError("output directory must be outside the raw corpus")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {out_dir}")


def build_prompt(
    knowledge_payload: str | None = None,
    verus_command: str = "verus",
    lynette_command: str = "lynette",
) -> str:
    prompt = f"""Solve the Verus proof task in input.rs.

Requirements:
- Preserve all executable behavior, function signatures, requires, ensures, and decreases clauses.
- You may add or edit proof-only code such as assertions, lemmas, invariants, triggers, and proof blocks.
- Do not add assume, admit, external_body, or other verification bypasses.
- Work only in the current directory.
- Write the complete final program to candidate.rs.
- Run {verus_command} candidate.rs and iterate until it succeeds.
- Run {lynette_command} target-mode comparison against input.rs and keep the edit proof-safe.
- Do not ask the user questions. Finish with candidate.rs present even if verification fails.
"""
    if knowledge_payload is not None:
        prompt += "\n<provided_knowledge>\n" + knowledge_payload.rstrip() + "\n</provided_knowledge>\n"
    return prompt


def configured_tool_path(env_name: str, executable: str) -> Path:
    return Path(os.environ.get(env_name) or shutil.which(executable) or executable)


def resolve_tool_path(path: Path) -> Path:
    path = path.expanduser()
    if path.is_absolute() or path.parent != Path("."):
        return path.resolve()
    located = shutil.which(str(path))
    return Path(located).resolve() if located else path


def build_copilot_command(copilot_bin: Path, model: str, prompt: str) -> list[str]:
    return [
        str(copilot_bin),
        "--model",
        model,
        "--prompt",
        prompt,
        "--allow-all-tools",
        "--no-ask-user",
        "--no-auto-update",
        "--no-remote",
        "--no-custom-instructions",
        "--no-bash-env",
        "--disable-builtin-mcps",
        "--no-color",
        "--output-format",
        "text",
    ]


def _version(command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
        return {
            "returncode": result.returncode,
            "output": (result.stdout + result.stderr).strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"returncode": None, "output": str(error)}


def verus_succeeded(returncode: int | None, output: str) -> bool:
    return returncode == 0 and "error: aborting" not in output.lower()


def lynette_succeeded(returncode: int | None) -> bool:
    return returncode == 0


def _run_and_log(
    command: list[str], cwd: Path, log_path: Path, timeout_seconds: int
) -> dict[str, Any]:
    started_at = _now()
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            returncode: int | None = process.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGINT)
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
            returncode = None
            timed_out = True
        output = stdout + stderr
        if timed_out:
            output += f"\nTIMEOUT after {timeout_seconds}s\n"
    except OSError as error:
        output = f"EXECUTION ERROR: {error}\n"
        returncode = None
        timed_out = False
    log_path.write_text(output)
    return {
        "started_at": started_at,
        "finished_at": _now(),
        "returncode": returncode,
        "timed_out": timed_out,
        "log_path": str(log_path.resolve()),
    }


def run_harness(
    source: Path,
    out_dir: Path,
    condition: str,
    model: str,
    copilot_bin: Path,
    verus_bin: Path,
    lynette_bin: Path,
    knowledge_file: Path | None = None,
    timeout_seconds: int = 1200,
    dry_run: bool = False,
) -> dict[str, Any]:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")
    if condition == "h0" and knowledge_file is not None:
        raise ValueError("h0 must not receive a knowledge file")
    if condition != "h0" and knowledge_file is None:
        raise ValueError(f"{condition} requires a knowledge file")
    validate_paths(source, out_dir)
    source = source.resolve()
    out_dir = out_dir.resolve()
    copilot_bin = resolve_tool_path(copilot_bin)
    verus_bin = resolve_tool_path(verus_bin)
    lynette_bin = resolve_tool_path(lynette_bin)
    knowledge_payload = knowledge_file.read_text() if knowledge_file else None

    out_dir.mkdir(parents=True, exist_ok=True)
    workspace = out_dir / "workspace"
    workspace.mkdir()
    input_path = workspace / "input.rs"
    candidate_path = workspace / "candidate.rs"
    shutil.copyfile(source, input_path)

    base_prompt = build_prompt(
        verus_command=str(verus_bin), lynette_command=str(lynette_bin)
    )
    prompt = build_prompt(
        knowledge_payload,
        verus_command=str(verus_bin),
        lynette_command=str(lynette_bin),
    )
    prompt_path = out_dir / "prompt.txt"
    prompt_path.write_text(prompt)
    command = build_copilot_command(copilot_bin, model, prompt)
    manifest: dict[str, Any] = {
        "created_at": _now(),
        "condition": condition,
        "model": model,
        "provider": {
            "type": os.environ.get("COPILOT_PROVIDER_TYPE"),
            "base_url": os.environ.get("COPILOT_PROVIDER_BASE_URL"),
            "wire_model": os.environ.get("COPILOT_PROVIDER_WIRE_MODEL"),
            "model_path": os.environ.get("HANDSOFF_MODEL_PATH"),
            "offline": os.environ.get("COPILOT_OFFLINE"),
        },
        "dry_run": dry_run,
        "source_path": str(source.resolve()),
        "source_sha256": sha256_file(source),
        "input_copy_sha256": sha256_file(input_path),
        "base_prompt_sha256": _sha256_text(base_prompt),
        "prompt_sha256": _sha256_text(prompt),
        "knowledge_payload_sha256": (
            _sha256_text(knowledge_payload) if knowledge_payload is not None else None
        ),
        "knowledge_payload_chars": len(knowledge_payload or ""),
        "copilot_command": ["$COPILOT", "--model", model, "--prompt", "$PROMPT"]
        + command[5:],
        "copilot_version": _version([str(copilot_bin), "--version"]),
        "verus_version": _version([str(verus_bin), "--version"]),
        "lynette_version": _version([str(lynette_bin), "--version"]),
        "timeout_seconds": timeout_seconds,
    }
    _write_json(out_dir / "run_manifest.json", manifest)
    if dry_run:
        result = {**manifest, "status": "DRY_RUN", "mechanical_only": True}
        _write_json(out_dir / "result.json", result)
        return result

    copilot = _run_and_log(
        command, workspace, out_dir / "copilot.log", timeout_seconds
    )
    usage = parse_copilot_usage((out_dir / "copilot.log").read_text(errors="replace"))
    _write_json(out_dir / "usage.json", usage)

    candidate_present = candidate_path.is_file()
    verus: dict[str, Any] = {"checked": False, "passed": False}
    lynette: dict[str, Any] = {"checked": False, "passed": False}
    if candidate_present:
        verus_run = _run_and_log(
            [str(verus_bin), str(candidate_path)],
            workspace,
            out_dir / "verus.log",
            timeout_seconds,
        )
        verus_output = (out_dir / "verus.log").read_text(errors="replace")
        verus = {
            **verus_run,
            "checked": verus_run["returncode"] is not None,
            "passed": verus_succeeded(verus_run["returncode"], verus_output),
        }
        lynette_run = _run_and_log(
            [str(lynette_bin), "compare", "-t", str(input_path), str(candidate_path)],
            workspace,
            out_dir / "lynette.log",
            timeout_seconds,
        )
        lynette = {
            **lynette_run,
            "checked": lynette_run["returncode"] is not None,
            "passed": lynette_succeeded(lynette_run["returncode"]),
        }

    validation = {
        "candidate_present": candidate_present,
        "candidate_sha256": sha256_file(candidate_path) if candidate_present else None,
        "verus": verus,
        "lynette": lynette,
    }
    _write_json(out_dir / "validation.json", validation)
    status = (
        "PASS"
        if candidate_present and verus["passed"] and lynette["passed"]
        else "FAIL"
    )
    result = {
        **manifest,
        "status": status,
        "mechanical_only": True,
        "copilot": copilot,
        "usage_available": usage["available"],
        "validation": validation,
    }
    _write_json(out_dir / "result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(prog="handsoff-harness")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--condition", choices=sorted(CONDITIONS), required=True)
    parser.add_argument("--knowledge-file", type=Path)
    parser.add_argument("--model", default="claude-sonnet-4.5")
    parser.add_argument(
        "--copilot-bin",
        type=Path,
        default=configured_tool_path("COPILOT_BIN", "copilot"),
    )
    parser.add_argument(
        "--verus-bin",
        type=Path,
        default=configured_tool_path("VERUS_BIN", "verus"),
    )
    parser.add_argument(
        "--lynette-bin",
        type=Path,
        default=configured_tool_path("LYNETTE_BIN", "lynette"),
    )
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run_harness(
        source=args.source,
        out_dir=validate_output_path(args.out_dir),
        condition=args.condition,
        model=args.model,
        copilot_bin=args.copilot_bin,
        verus_bin=args.verus_bin,
        lynette_bin=args.lynette_bin,
        knowledge_file=args.knowledge_file,
        timeout_seconds=args.timeout_seconds,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
