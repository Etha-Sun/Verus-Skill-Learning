from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .data_layout import validate_output_path
from .handsoff_harness import (
    _run_and_log,
    configured_tool_path,
    lynette_succeeded,
    resolve_tool_path,
    verus_succeeded,
)
from .handsoff_m0 import sha256_file


FINAL_CASES = ("stable_pass", "stable_closest_failure", "unstable")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _require_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"output directory must be empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _resolve_within(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    allowed = root.resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError(f"path escapes allowed root {allowed}: {resolved}")
    return resolved


def _version(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=30, check=False
    )
    return {
        "returncode": result.returncode,
        "output": (result.stdout + result.stderr).strip(),
    }


def build_codex_prompt(verus_bin: Path, lynette_bin: Path) -> str:
    return f"""Solve the Verus proof task in candidate.rs from scratch.

Operate autonomously and explore normally:
- Treat input.rs as the immutable original and edit only candidate.rs.
- Preserve executable behavior, function signatures, requires, ensures, and decreases clauses.
- You may add or edit proof-only code: assertions, lemmas, invariants, triggers, and proof blocks.
- Never introduce assume, admit, external_body, new axioms, or another verification bypass.
- Do not use network access, git history, files outside this workspace, old trajectories, or prior answers.
- Run `{verus_bin} candidate.rs` after edits and use the exact diagnostics to iterate.
- Run `{lynette_bin} compare -t input.rs candidate.rs` and keep every edit proof-safe.
- Continue until both verification and the safety comparison pass, or until you have exhausted useful approaches.
- Leave the complete best candidate in candidate.rs even if verification does not pass.

In the final response, briefly state the result, remaining verifier error if any, and the main strategies tried.
"""


def _tool_paths(
    codex_bin: Path | None = None,
    verus_bin: Path | None = None,
    lynette_bin: Path | None = None,
) -> dict[str, Path]:
    paths = {
        "codex": resolve_tool_path(codex_bin or configured_tool_path("CODEX_BIN", "codex")),
        "verus": resolve_tool_path(verus_bin or configured_tool_path("VERUS_BIN", "verus")),
        "lynette": resolve_tool_path(
            lynette_bin or configured_tool_path("LYNETTE_BIN", "lynette")
        ),
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ValueError(f"missing tool binaries: {missing}")
    return paths


def prepare_jobs(
    frozen_cases_path: Path,
    tasks_path: Path,
    corpus_root: Path,
    out_dir: Path,
    *,
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "high",
    timeout_seconds: int = 1200,
    repetitions: int = 1,
    codex_bin: Path | None = None,
    verus_bin: Path | None = None,
    lynette_bin: Path | None = None,
) -> dict[str, Any]:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    frozen = json.loads(frozen_cases_path.read_text(encoding="utf-8"))
    cases = frozen.get("cases") or []
    if (
        frozen.get("status") != "FROZEN"
        or {row.get("final_case") for row in cases} != set(FINAL_CASES)
        or frozen.get("selection_evidence") != "h0_only"
    ):
        raise ValueError("the three-case H0-only freeze is invalid")
    tasks = {row["calibration_id"]: row for row in _load_jsonl(tasks_path)}
    tools = _tool_paths(codex_bin, verus_bin, lynette_bin)
    prompt = build_codex_prompt(tools["verus"], tools["lynette"])
    tool_sha256 = {name: sha256_file(path) for name, path in tools.items()}
    codex_version = _version([str(tools["codex"]), "--version"])
    if codex_version["returncode"] != 0:
        raise ValueError("codex version check failed")

    jobs = []
    by_case = {row["final_case"]: row for row in cases}
    for final_case in FINAL_CASES:
        calibration_id = by_case[final_case]["calibration_id"]
        task = tasks.get(calibration_id)
        if task is None:
            raise ValueError(f"frozen case missing from tasks: {calibration_id}")
        source = _resolve_within(
            corpus_root / task["canonical_source_path"],
            corpus_root / task["directory_group"] / "unverified",
        )
        if sha256_file(source) != task["canonical_source_sha256"]:
            raise ValueError(f"canonical source hash mismatch: {calibration_id}")
        for repetition in range(1, repetitions + 1):
            job_id = f"{calibration_id}-rep{repetition}-codex-h0"
            jobs.append(
                {
                    "job_id": job_id,
                    "execution_order": len(jobs) + 1,
                    "final_case": final_case,
                    "calibration_id": calibration_id,
                    "task_id": task["task_id"],
                    "repetition": repetition,
                    "condition": "codex_h0",
                    "source_path": str(source),
                    "source_sha256": task["canonical_source_sha256"],
                    "relative_run_path": f"runs/{job_id}",
                    "status": "PENDING",
                }
            )

    _require_empty(out_dir)
    jobs_path = out_dir / "codex_baseline_jobs.jsonl"
    _write_jsonl(jobs_path, jobs)
    contract = {
        "created_at": _now(),
        "status": "FROZEN",
        "run_id": "R041B_CODEX_BASELINE",
        "purpose": "fresh_codex_exploration_on_three_r041a_tasks",
        "model": model,
        "reasoning_effort": reasoning_effort,
        "sandbox": "workspace-write",
        "ephemeral_session": True,
        "timeout_seconds": timeout_seconds,
        "repetitions": repetitions,
        "job_count": len(jobs),
        "condition": "codex_h0",
        "old_trajectory_visible": False,
        "verified_answer_visible": False,
        "rationale_visible": False,
        "prompt_sha256": _sha256_text(prompt),
        "frozen_cases_sha256": sha256_file(frozen_cases_path),
        "tasks_sha256": sha256_file(tasks_path),
        "jobs_sha256": sha256_file(jobs_path),
        "tools": {name: str(path) for name, path in tools.items()},
        "tool_sha256": tool_sha256,
        "codex_version": codex_version,
        "raw_data_read_only": True,
    }
    _write_json(out_dir / "codex_baseline_contract.json", contract)
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    return contract


def build_codex_command(
    codex_bin: Path,
    workspace: Path,
    last_message_path: Path,
    model: str,
    reasoning_effort: str,
) -> list[str]:
    return [
        str(codex_bin),
        "exec",
        "--model",
        model,
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
        "--sandbox",
        "workspace-write",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--color",
        "never",
        "--json",
        "-C",
        str(workspace),
        "--output-last-message",
        str(last_message_path),
        "-",
    ]


def _run_codex_streaming(
    command: list[str],
    prompt: str,
    events_path: Path,
    stderr_path: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started_at = _now()
    started = time.monotonic()
    with events_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=stdout,
            stderr=stderr,
            text=True,
            start_new_session=True,
        )
        assert process.stdin is not None
        process.stdin.write(prompt)
        process.stdin.close()
        try:
            returncode: int | None = process.wait(timeout=timeout_seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            returncode = None
            timed_out = True
    return {
        "started_at": started_at,
        "finished_at": _now(),
        "wall_seconds": time.monotonic() - started,
        "returncode": returncode,
        "timed_out": timed_out,
        "events_path": str(events_path),
        "stderr_path": str(stderr_path),
    }


def summarize_events(events_path: Path) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    parse_errors = 0
    final_usage = None
    commands_by_id: dict[str, dict[str, Any]] = {}
    event_count = 0
    with events_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            event_count += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            event_type = str(event.get("type") or "unknown")
            counts[event_type] += 1
            usage = event.get("usage")
            if isinstance(usage, dict):
                final_usage = usage
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "command_execution":
                item_id = str(item.get("id") or f"event_{event_count}")
                record = {
                    "id": item.get("id"),
                    "command": item.get("command"),
                    "status": item.get("status"),
                    "exit_code": item.get("exit_code"),
                }
                if item_id not in commands_by_id or event_type == "item.completed":
                    commands_by_id[item_id] = record
    commands = list(commands_by_id.values())
    return {
        "event_count": event_count,
        "event_type_counts": dict(sorted(counts.items())),
        "json_parse_errors": parse_errors,
        "final_usage": final_usage,
        "command_count": len(commands),
        "commands": commands,
    }


def _workspace_inventory(workspace: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "relative_path": str(path.relative_to(workspace)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return rows


def run_job(
    jobs_path: Path,
    contract_path: Path,
    runs_dir: Path,
    job_id: str,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if (
        contract.get("status") != "FROZEN"
        or contract.get("jobs_sha256") != sha256_file(jobs_path)
    ):
        raise ValueError("Codex baseline contract mismatch")
    jobs = {row["job_id"]: row for row in _load_jsonl(jobs_path)}
    job = jobs.get(job_id)
    if job is None or job.get("status") != "PENDING":
        raise ValueError(f"unknown or non-pending job: {job_id}")
    expected_runs_dir = jobs_path.parent / "runs"
    if runs_dir.resolve() != expected_runs_dir.resolve():
        raise ValueError("runs directory does not match the frozen contract")

    tools = {name: Path(path) for name, path in contract["tools"].items()}
    if any(
        not path.is_file() or sha256_file(path) != contract["tool_sha256"][name]
        for name, path in tools.items()
    ):
        raise ValueError("tool identity changed after job freeze")
    source = Path(job["source_path"])
    if not source.is_file() or sha256_file(source) != job["source_sha256"]:
        raise ValueError("source identity changed after job freeze")
    prompt = build_codex_prompt(tools["verus"], tools["lynette"])
    if _sha256_text(prompt) != contract["prompt_sha256"]:
        raise ValueError("prompt identity changed after job freeze")

    out_dir = runs_dir / job_id
    _require_empty(out_dir)
    workspace = out_dir / "workspace"
    workspace.mkdir()
    input_path = workspace / "input.rs"
    candidate_path = workspace / "candidate.rs"
    shutil.copyfile(source, input_path)
    shutil.copyfile(source, candidate_path)
    input_path.chmod(0o444)
    prompt_path = out_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    last_message_path = out_dir / "last_message.txt"
    events_path = out_dir / "codex_events.jsonl"
    stderr_path = out_dir / "codex_stderr.log"
    command = build_codex_command(
        tools["codex"],
        workspace,
        last_message_path,
        contract["model"],
        contract["reasoning_effort"],
    )
    run_manifest = {
        "created_at": _now(),
        "run_id": contract["run_id"],
        "job_id": job_id,
        "final_case": job["final_case"],
        "calibration_id": job["calibration_id"],
        "task_id": job["task_id"],
        "repetition": job["repetition"],
        "condition": job["condition"],
        "model": contract["model"],
        "reasoning_effort": contract["reasoning_effort"],
        "sandbox": contract["sandbox"],
        "timeout_seconds": contract["timeout_seconds"],
        "source_path": str(source),
        "source_sha256": job["source_sha256"],
        "input_copy_sha256": sha256_file(input_path),
        "initial_candidate_sha256": sha256_file(candidate_path),
        "prompt_sha256": contract["prompt_sha256"],
        "jobs_sha256": contract["jobs_sha256"],
        "contract_sha256": sha256_file(contract_path),
        "tool_sha256": contract["tool_sha256"],
        "codex_version": contract["codex_version"],
        "command": [
            "$CODEX",
            *command[1:command.index("-C") + 1],
            "$WORKSPACE",
            "--output-last-message",
            "$LAST_MESSAGE",
            "-",
        ],
        "old_trajectory_visible": False,
        "verified_answer_visible": False,
        "rationale_visible": False,
    }
    _write_json(out_dir / "run_manifest.json", run_manifest)

    codex = _run_codex_streaming(
        command,
        prompt,
        events_path,
        stderr_path,
        contract["timeout_seconds"],
    )
    event_summary = summarize_events(events_path)
    _write_json(out_dir / "event_summary.json", event_summary)

    input_unchanged = sha256_file(input_path) == job["source_sha256"]
    candidate_present = candidate_path.is_file()
    verus: dict[str, Any] = {"checked": False, "passed": False}
    lynette: dict[str, Any] = {"checked": False, "passed": False}
    if candidate_present:
        verus_run = _run_and_log(
            [str(tools["verus"]), str(candidate_path)],
            workspace,
            out_dir / "verus.log",
            contract["timeout_seconds"],
        )
        verus_output = (out_dir / "verus.log").read_text(errors="replace")
        verus = {
            **verus_run,
            "checked": verus_run["returncode"] is not None,
            "passed": verus_succeeded(verus_run["returncode"], verus_output),
        }
        lynette_run = _run_and_log(
            [
                str(tools["lynette"]),
                "compare",
                "-t",
                str(input_path),
                str(candidate_path),
            ],
            workspace,
            out_dir / "lynette.log",
            contract["timeout_seconds"],
        )
        lynette = {
            **lynette_run,
            "checked": lynette_run["returncode"] is not None,
            "passed": lynette_succeeded(lynette_run["returncode"]),
        }
        diff = "".join(
            difflib.unified_diff(
                input_path.read_text(errors="replace").splitlines(keepends=True),
                candidate_path.read_text(errors="replace").splitlines(keepends=True),
                fromfile="input.rs",
                tofile="candidate.rs",
            )
        )
        (out_dir / "candidate.diff").write_text(diff, encoding="utf-8")

    validation = {
        "input_unchanged": input_unchanged,
        "candidate_present": candidate_present,
        "candidate_sha256": sha256_file(candidate_path) if candidate_present else None,
        "verus": verus,
        "lynette": lynette,
    }
    _write_json(out_dir / "validation.json", validation)
    inventory = _workspace_inventory(workspace)
    _write_json(out_dir / "workspace_inventory.json", inventory)
    passed = bool(
        input_unchanged
        and candidate_present
        and verus["passed"]
        and lynette["passed"]
    )
    result = {
        **run_manifest,
        "status": "PASS" if passed else "FAIL",
        "codex": codex,
        "events": event_summary,
        "validation": validation,
        "workspace_file_count": len(inventory),
        "raw_data_read_only": True,
    }
    _write_json(out_dir / "result.json", result)
    return result


def audit_batch(
    jobs_path: Path,
    contract_path: Path,
    runs_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if (
        contract.get("status") != "FROZEN"
        or contract.get("jobs_sha256") != sha256_file(jobs_path)
    ):
        raise ValueError("Codex baseline contract mismatch")
    if runs_dir.resolve() != (jobs_path.parent / "runs").resolve():
        raise ValueError("runs directory does not match the frozen contract")
    if output_path.resolve().parent != jobs_path.parent.resolve():
        raise ValueError("audit output must be written beside the frozen contract")

    rows = []
    totals: Counter[str] = Counter()
    jobs = _load_jsonl(jobs_path)
    for job in jobs:
        run_dir = runs_dir / job["job_id"]
        result_path = run_dir / "result.json"
        events_path = run_dir / "codex_events.jsonl"
        validation_path = run_dir / "validation.json"
        required = (result_path, events_path, validation_path)
        if any(not path.is_file() for path in required):
            raise ValueError(f"incomplete run artifacts: {job['job_id']}")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        events = summarize_events(events_path)
        usage = events.get("final_usage") or {}
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
        ):
            totals[key] += int(usage.get(key) or 0)
        passed = bool(
            validation["input_unchanged"]
            and validation["candidate_present"]
            and validation["verus"]["passed"]
            and validation["lynette"]["passed"]
        )
        rows.append(
            {
                "job_id": job["job_id"],
                "final_case": job["final_case"],
                "task_id": job["task_id"],
                "status": "PASS" if passed else "FAIL",
                "codex_returncode": result["codex"]["returncode"],
                "codex_timed_out": result["codex"]["timed_out"],
                "wall_seconds": result["codex"]["wall_seconds"],
                "event_count": events["event_count"],
                "json_parse_errors": events["json_parse_errors"],
                "unique_command_count": events["command_count"],
                "stored_command_count": result["events"]["command_count"],
                "usage": usage,
                "input_unchanged": validation["input_unchanged"],
                "verus_passed": validation["verus"]["passed"],
                "lynette_passed": validation["lynette"]["passed"],
                "result_sha256": sha256_file(result_path),
                "events_sha256": sha256_file(events_path),
                "candidate_diff_sha256": sha256_file(run_dir / "candidate.diff"),
            }
        )

    audit = {
        "audited_at": _now(),
        "status": "COMPLETE",
        "job_count": len(jobs),
        "pass_count": sum(row["status"] == "PASS" for row in rows),
        "all_json_valid": all(row["json_parse_errors"] == 0 for row in rows),
        "all_inputs_unchanged": all(row["input_unchanged"] for row in rows),
        "all_lynette_passed": all(row["lynette_passed"] for row in rows),
        "contract_sha256": sha256_file(contract_path),
        "jobs_sha256": sha256_file(jobs_path),
        "totals": dict(totals),
        "runs": rows,
        "raw_events_preserved": True,
        "raw_data_read_only": True,
    }
    if output_path.exists():
        raise ValueError(f"audit output already exists: {output_path}")
    _write_json(output_path, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(prog="codex-baseline")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--frozen-cases", type=Path, required=True)
    prepare.add_argument("--tasks", type=Path, required=True)
    prepare.add_argument("--corpus-root", type=Path, required=True)
    prepare.add_argument("--out-dir", type=Path, required=True)
    prepare.add_argument("--model", default="gpt-5.6-sol")
    prepare.add_argument("--reasoning-effort", default="high")
    prepare.add_argument("--timeout-seconds", type=int, default=1200)
    prepare.add_argument("--repetitions", type=int, default=1)
    prepare.add_argument("--codex-bin", type=Path)
    prepare.add_argument("--verus-bin", type=Path)
    prepare.add_argument("--lynette-bin", type=Path)
    run = commands.add_parser("run-job")
    run.add_argument("--jobs", type=Path, required=True)
    run.add_argument("--contract", type=Path, required=True)
    run.add_argument("--runs-dir", type=Path, required=True)
    run.add_argument("--job-id", required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("--jobs", type=Path, required=True)
    audit.add_argument("--contract", type=Path, required=True)
    audit.add_argument("--runs-dir", type=Path, required=True)
    audit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare_jobs(
            args.frozen_cases,
            args.tasks,
            args.corpus_root,
            validate_output_path(args.out_dir, data_root=args.corpus_root),
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout_seconds,
            repetitions=args.repetitions,
            codex_bin=args.codex_bin,
            verus_bin=args.verus_bin,
            lynette_bin=args.lynette_bin,
        )
    elif args.command == "run-job":
        result = run_job(
            args.jobs,
            args.contract,
            validate_output_path(args.runs_dir),
            args.job_id,
        )
    else:
        result = audit_batch(
            args.jobs,
            args.contract,
            validate_output_path(args.runs_dir),
            validate_output_path(args.output),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
