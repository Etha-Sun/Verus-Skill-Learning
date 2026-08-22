from __future__ import annotations

import json
import os
import hashlib
import re
import signal
import subprocess
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .codex_adapter import CodexStreamRecorder
from .events import audit_events, load_events
from .redaction import secret_match_count
from .workspace import inventory, prepare_solver_workspace, sha256_file


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_executable(path: Path, name: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ValueError(f"{name} is not executable: {resolved}")
    return resolved


def _require_external_output(out_dir: Path) -> Path:
    root_text = os.environ.get("VERUS_SKILL_RUN_ROOT")
    if not root_text:
        raise ValueError("VERUS_SKILL_RUN_ROOT is not configured")
    root = Path(root_text).resolve()
    resolved = out_dir.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"output must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    if resolved.exists() and any(resolved.iterdir()):
        raise ValueError(f"output directory must be empty: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def build_prompt() -> str:
    return """Solve the Verus proof task in candidate.rs from scratch.

Visibility and editing rules:
- Treat input.rs as immutable and edit only candidate.rs.
- Read TASK.md. Read SKILL.md only if it exists.
- Do not inspect files outside this workspace, repository history, prior runs,
  reference proofs, environment variables, credentials, or network resources.
- Make every code edit through the Codex file-edit/patch tool. Do not modify
  candidate.rs with shell redirection, sed, perl, Python, cp, mv, or a generated
  editing script.

Proof rules:
- Preserve executable behavior, signatures, requires, ensures, and decreases.
- Add or edit proof-only assertions, lemmas, invariants, triggers, and proof blocks.
- Never use assume, admit, external_body, new axioms, or verification bypasses.
- Run `./tools/run_verus.sh` after edits and use its complete diagnostics.
- Run `./tools/run_lynette.sh` before finishing.
- Continue exploration until both checks pass or useful
  approaches are exhausted.

Leave the complete best candidate in candidate.rs. In the final response,
report verification status and strategies attempted. Do not omit failed steps.
"""


def build_cross_provider_prompt(
    *,
    skill_present: bool,
    verus_bin: Path,
    lynette_bin: Path,
) -> str:
    first_rule = (
        "- Read skill/verus-proof-repair/SKILL.md first and follow it. "
        "Consult a file below skill/verus-proof-repair/references/ only when "
        "the root skill explicitly routes you there."
        if skill_present
        else "- This is the no-skill control; no proof-repair skill is supplied."
    )
    return f"""Repair the Verus proof in candidate.rs.

Rules:
{first_rule}
- input.rs is immutable and candidate.rs is the only file you may edit.
- Do not use assume, admit, newly introduced external_body, axioms, or
  unimplemented trusted helpers. Do not weaken or remove requires, ensures,
  recommends, signatures, executable code, or intended specifications.
- Diagnose with {verus_bin.resolve()} candidate.rs and iterate on the smallest proof-only edit.
- Before finishing, require both {verus_bin.resolve()} candidate.rs and
  {lynette_bin.resolve()} compare -t input.rs candidate.rs to exit successfully.
- Do not search for trajectories, verified solutions, sibling task outputs, or
  validation/test metadata. Work only from this task, local Verus/vstd
  documentation, verifier diagnostics, and the supplied immutable skill.
- Finish only after both checks pass. Otherwise leave the best candidate.rs and
  state the precise blocker.
"""


def build_command(
    *,
    codex_bin: Path,
    workspace: Path,
    last_message: Path,
    model: str,
    reasoning_effort: str,
    reasoning_summary: str = "detailed",
    show_raw_agent_reasoning: bool = True,
    provider_id: str | None = None,
    provider_base_url: str | None = None,
    provider_env_key: str | None = None,
    model_context_window: int | None = None,
    model_catalog_json: Path | None = None,
    contract_profile: str = "project",
    prompt_text: str | None = None,
) -> list[str]:
    if contract_profile == "cross_provider_20260819":
        if prompt_text is None:
            raise ValueError("cross-provider command requires prompt text")
        command = [
            str(codex_bin),
            "-a",
            "never",
            "exec",
            "--ignore-user-config",
            "--ephemeral",
            "--json",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            "-s",
            "workspace-write",
            "-m",
            model,
        ]
        if any(
            value is not None
            for value in (provider_id, provider_base_url, provider_env_key)
        ):
            if not all((provider_id, provider_base_url, provider_env_key)):
                raise ValueError(
                    "custom Codex provider requires id, base URL, and env key"
                )
            command.extend(
                [
                    "-c",
                    f'model_provider="{provider_id}"',
                    "-c",
                    f'model_providers.{provider_id}.name="Codex Compatibility Bridge"',
                    "-c",
                    f'model_providers.{provider_id}.base_url="{provider_base_url}"',
                    "-c",
                    f'model_providers.{provider_id}.env_key="{provider_env_key}"',
                    "-c",
                    f'model_providers.{provider_id}.wire_api="responses"',
                    "-c",
                    f"model_providers.{provider_id}.request_max_retries=4",
                    "-c",
                    f"model_providers.{provider_id}.stream_max_retries=4",
                ]
            )
        command.extend(
            [
                "-c",
                f'model_reasoning_effort="{reasoning_effort}"',
                "-c",
                "model_max_output_tokens=8192",
            ]
        )
        if model_context_window is not None:
            command.extend(
                ["-c", f"model_context_window={int(model_context_window)}"]
            )
        if model_catalog_json is not None:
            command.extend(
                [
                    "-c",
                    f"model_catalog_json={json.dumps(str(model_catalog_json.resolve()))}",
                ]
            )
        command.append(prompt_text)
        return command
    if contract_profile != "project":
        raise ValueError(f"unsupported Codex contract profile: {contract_profile}")
    disabled_capabilities = (
        "apps",
        "browser_use",
        "browser_use_external",
        "computer_use",
        "default_mode_request_user_input",
        "goals",
        "image_generation",
        "multi_agent",
        "plugins",
        "skill_search",
        "tool_suggest",
        "workspace_dependencies",
    )
    command = [
        str(codex_bin),
        "exec",
        "--model",
        model,
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
        "-c",
        f'model_reasoning_summary="{reasoning_summary}"',
        "-c",
        "model_supports_reasoning_summaries=true",
        "-c",
        "hide_agent_reasoning=false",
        "-c",
        f"show_raw_agent_reasoning={'true' if show_raw_agent_reasoning else 'false'}",
        *(
            value
            for capability in disabled_capabilities
            for value in ("--disable", capability)
        ),
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
        str(last_message),
        "-",
    ]
    if any(
        value is not None
        for value in (provider_id, provider_base_url, provider_env_key)
    ):
        if not all((provider_id, provider_base_url, provider_env_key)):
            raise ValueError("custom Codex provider requires id, base URL, and env key")
        provider_config = [
            "-c",
            f'model_provider="{provider_id}"',
            "-c",
            f'model_providers.{provider_id}.name="Codex Compatibility Bridge"',
            "-c",
            f'model_providers.{provider_id}.base_url="{provider_base_url}"',
            "-c",
            f'model_providers.{provider_id}.env_key="{provider_env_key}"',
            "-c",
            f'model_providers.{provider_id}.wire_api="responses"',
        ]
        command[2:2] = provider_config
    if model_context_window is not None:
        command[2:2] = ["-c", f"model_context_window={int(model_context_window)}"]
    if model_catalog_json is not None:
        command[2:2] = [
            "-c",
            f"model_catalog_json={json.dumps(str(model_catalog_json.resolve()))}",
        ]
    return command


def _version(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [str(path), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _codex_environment(provider_env_key: str | None) -> dict[str, str]:
    allowed = {
        "HOME",
        "PATH",
        "TMPDIR",
        "TERM",
        "LANG",
        "LC_ALL",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "CODEX_HOME",
    }
    if provider_env_key:
        allowed.add(provider_env_key)
    return {key: value for key, value in os.environ.items() if key in allowed}


def _run_complete(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
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
        return {
            "returncode": process.returncode,
            "timed_out": False,
            "wall_seconds": time.monotonic() - started,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        return {
            "returncode": None,
            "timed_out": True,
            "wall_seconds": time.monotonic() - started,
            "stdout": stdout,
            "stderr": stderr,
        }


def _usage_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in reversed(rows):
        raw = row.get("data", {}).get("raw_codex_event", {})
        usage = raw.get("usage") if isinstance(raw, dict) else None
        if isinstance(usage, dict):
            return usage
    return None


def _event_fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _command_modifies_candidate(command: str) -> bool:
    """Flag shell-based candidate edits without treating stderr redirects as edits."""
    if "candidate.rs" not in command:
        return False
    temp_cd = re.search(r"\bcd\s+['\"]?/tmp(?:/[^\s;&|]*)?", command)
    if temp_cd:
        suffix = command[temp_cd.end() :]
        non_temp_absolute_candidate = re.search(
            r"(?:^|\s)/(?!tmp(?:/|\s))[^\s;&|'\"]*/candidate\.rs\b",
            suffix,
        )
        if not non_temp_absolute_candidate:
            command = command[: temp_cd.start()]
    edit_patterns = (
        r"\bsed\b(?=[^;&|\n]*\s-i(?:\s|$))[^;&|\n]*\bcandidate\.rs\b",
        r"\bperl\b(?=[^;&|\n]*\s-i(?:\s|$))[^;&|\n]*\bcandidate\.rs\b",
        r"\bpython(?:3)?\b[^;&|\n]*\bcandidate\.rs\b",
        r"\b(?:cp|mv)\b[^;&|\n]*\s['\"]?(?:\./)?candidate\.rs['\"]?\s*(?:[;&|]|$)",
        r"(?:^|\s)\d*>>?\s*['\"]?(?:\./)?candidate\.rs\b",
        r"(?:^|\s)tee(?:\s+-a)?\s+['\"]?(?:\./)?candidate\.rs\b",
    )
    return any(re.search(pattern, command, re.IGNORECASE) for pattern in edit_patterns)


def run_codex_smoke(
    *,
    source: Path,
    out_dir: Path,
    codex_bin: Path,
    verus_bin: Path,
    lynette_bin: Path,
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "high",
    reasoning_summary: str = "detailed",
    show_raw_agent_reasoning: bool = True,
    timeout_seconds: int = 600,
    skill_text: str | None = None,
    provider_id: str | None = None,
    provider_base_url: str | None = None,
    provider_env_key: str | None = None,
    model_context_window: int | None = None,
    model_catalog_json: Path | None = None,
    contract_profile: str = "project",
    condition_skill_sha256: str | None = None,
    stage: str = "auxiliary_dev_fidelity_smoke",
) -> dict[str, Any]:
    out_dir = _require_external_output(out_dir)
    codex_bin = _require_executable(codex_bin, "codex")
    verus_bin = _require_executable(verus_bin, "verus")
    lynette_bin = _require_executable(lynette_bin, "lynette")
    source = source.resolve()
    source_sha = sha256_file(source)
    workspace = out_dir / "workspace"
    prompt = (
        build_cross_provider_prompt(
            skill_present=skill_text is not None,
            verus_bin=verus_bin,
            lynette_bin=lynette_bin,
        )
        if contract_profile == "cross_provider_20260819"
        else build_prompt()
    )
    verus_wrapper = f"""#!/usr/bin/env bash
set -u
if [[ "$#" -ne 1 || "$1" != "candidate.rs" ]]; then
  echo "usage: ./tools/run_verus.sh candidate.rs" >&2
  exit 2
fi
exec "{verus_bin}" candidate.rs
"""
    lynette_wrapper = f"""#!/usr/bin/env bash
set -u
if [[ "$#" -ne 0 ]]; then
  echo "usage: ./tools/run_lynette.sh" >&2
  exit 2
fi
exec "{lynette_bin}" compare -t input.rs candidate.rs
"""
    if contract_profile == "cross_provider_20260819":
        prepare_solver_workspace(
            source=source,
            workspace=workspace,
            task_text="Repair candidate.rs.\n",
            skill_text=skill_text,
            skill_relative_path="skill/verus-proof-repair/SKILL.md",
            extra_files={"AGENTS.md": prompt},
        )
    elif contract_profile == "project":
        prepare_solver_workspace(
            source=source,
            workspace=workspace,
            task_text=prompt,
            skill_text=skill_text,
            extra_files={
                "tools/run_verus.sh": verus_wrapper,
                "tools/run_lynette.sh": lynette_wrapper,
            },
        )
        (workspace / "tools" / "run_verus.sh").chmod(0o555)
        (workspace / "tools" / "run_lynette.sh").chmod(0o555)
    else:
        raise ValueError(f"unsupported Codex contract profile: {contract_profile}")
    prompt_path = out_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    last_message = out_dir / "last_message.txt"
    raw_events = out_dir / "codex_events.raw.jsonl"
    normalized_events = out_dir / "agent_events.jsonl"
    stderr_path = out_dir / "codex_stderr.log"
    recorder = CodexStreamRecorder(
        raw_path=raw_events,
        normalized_path=normalized_events,
        snapshots_dir=out_dir / "snapshots",
        run_id=out_dir.name,
        candidate_path=workspace / "candidate.rs",
    )
    command = build_command(
        codex_bin=codex_bin,
        workspace=workspace,
        last_message=last_message,
        model=model,
        reasoning_effort=reasoning_effort,
        reasoning_summary=reasoning_summary,
        show_raw_agent_reasoning=show_raw_agent_reasoning,
        provider_id=provider_id,
        provider_base_url=provider_base_url,
        provider_env_key=provider_env_key,
        model_context_window=model_context_window,
        model_catalog_json=model_catalog_json,
        contract_profile=contract_profile,
        prompt_text=prompt,
    )
    manifest = {
        "run_id": out_dir.name,
        "created_at": _now(),
        "stage": stage,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "reasoning_summary": reasoning_summary,
        "model_supports_reasoning_summaries": True,
        "hide_agent_reasoning": False,
        "show_raw_agent_reasoning": show_raw_agent_reasoning,
        "timeout_seconds": timeout_seconds,
        "contract_profile": contract_profile,
        "provider": {
            "id": provider_id,
            "base_url": provider_base_url,
            "env_key": provider_env_key,
            "wire_api": "responses" if provider_id else None,
            "model_context_window": model_context_window,
            "model_catalog_json": (
                str(model_catalog_json.resolve()) if model_catalog_json else None
            ),
        },
        "source_sha256": source_sha,
        "prompt_sha256": sha256_file(prompt_path),
        "skill_present": skill_text is not None,
        "skill_sha256": (
            hashlib.sha256(skill_text.encode("utf-8")).hexdigest()
            if skill_text is not None
            else None
        ),
        "skill_bytes": len(skill_text.encode("utf-8")) if skill_text is not None else 0,
        "condition_skill_sha256": condition_skill_sha256,
        "tools": {
            "codex": {"sha256": sha256_file(codex_bin), "version": _version(codex_bin)},
            "verus": {"sha256": sha256_file(verus_bin)},
            "lynette": {"sha256": sha256_file(lynette_bin)},
        },
        "command": [
            "$CODEX"
            if index == 0
            else "$WORKSPACE"
            if value == str(workspace)
            else "$LAST_MESSAGE"
            if value == str(last_message)
            else "$PROMPT"
            if value == prompt
            else value
            for index, value in enumerate(command)
        ],
        "actor_environment_keys": sorted(_codex_environment(provider_env_key)),
        "raw_log_uncompressed": True,
        "hidden_chain_of_thought_claimed": False,
    }
    (out_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    started_at = _now()
    started = time.monotonic()
    timed_out = threading.Event()
    process: subprocess.Popen[str]
    with stderr_path.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=workspace,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_handle,
            text=True,
            bufsize=1,
            start_new_session=True,
            env=_codex_environment(provider_env_key),
        )
        assert process.stdin is not None
        assert process.stdout is not None
        if contract_profile == "project":
            process.stdin.write(prompt)
        process.stdin.close()

        def stop_process() -> None:
            if process.poll() is None:
                timed_out.set()
                os.killpg(process.pid, signal.SIGINT)

        timer = threading.Timer(timeout_seconds, stop_process)
        timer.start()
        try:
            with process.stdout:
                for line_number, line in enumerate(process.stdout, start=1):
                    recorder.append_raw_line(line, line_number)
            try:
                returncode = process.wait(timeout=15 if timed_out.is_set() else None)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                returncode = None
        finally:
            timer.cancel()
    recorder.snapshot("codex_terminal")

    candidate = workspace / "candidate.rs"
    input_path = workspace / "input.rs"
    candidate_sha = sha256_file(candidate)
    final_checks = {}
    for actor, tool_id, check_command in (
        (
            "verus",
            "independent-final-verus",
            [str(verus_bin), str(candidate)],
        ),
        (
            "lynette",
            "independent-final-lynette",
            [
                str(lynette_bin),
                "compare",
                "-t",
                str(input_path),
                str(candidate),
            ],
        ),
    ):
        recorder.log.append(
            actor="host",
            event_type="tool_call",
            tool_call_id=tool_id,
            candidate_sha256=candidate_sha,
            data={"command": check_command},
        )
        check = _run_complete(
            check_command,
            cwd=workspace,
            timeout_seconds=min(timeout_seconds, 120),
        )
        recorder.log.append(
            actor="host",
            event_type="tool_result",
            tool_call_id=tool_id,
            candidate_sha256=candidate_sha,
            data=check,
        )
        passed = bool(
            check["returncode"] == 0
            and (actor == "lynette" or "verified, 0 errors" in str(check["stdout"]))
        )
        recorder.log.append(
            actor=actor,
            event_type="verifier",
            candidate_sha256=candidate_sha,
            data={"passed": passed, **check},
        )
        final_checks[actor] = {"passed": passed, **check}

    rows, parse_errors = load_events(normalized_events)
    event_audit = audit_events(rows, parse_errors)
    raw_rows = [
        json.loads(line)
        for line in raw_events.read_text(encoding="utf-8").splitlines()
        if line
    ]
    completed_raw_items = [
        row
        for row in raw_rows
        if row.get("type") == "item.completed"
        and isinstance(row.get("item"), dict)
        and row["item"].get("type") in {"command_execution", "file_change"}
    ]
    expected_boundaries = {
        f"{row['item']['type']}:{row['item'].get('id')}" for row in completed_raw_items
    }
    snapshot_rows = [
        row
        for row in rows
        if row.get("actor") == "host"
        and row.get("type") == "lifecycle"
        and row.get("data", {}).get("snapshot")
    ]
    observed_boundaries = {str(row["data"].get("boundary")) for row in snapshot_rows}
    completed_boundaries = len(completed_raw_items)
    snapshots = sorted((out_dir / "snapshots").glob("*-candidate.rs"))
    usage = _usage_from_rows(rows)
    reasoning_items = [
        row
        for row in rows
        if row.get("data", {}).get("raw_codex_event", {}).get("item", {}).get("type")
        == "reasoning"
    ]
    visible_reasoning_chars = sum(
        len(
            str(
                row.get("data", {})
                .get("raw_codex_event", {})
                .get("item", {})
                .get("text")
                or ""
            )
        )
        for row in reasoning_items
    )
    input_unchanged = sha256_file(input_path) == source_sha
    snapshot_coverage = expected_boundaries.issubset(observed_boundaries)
    snapshot_files_complete = all(
        (out_dir / row["data"]["snapshot"]).is_file()
        and (out_dir / row["data"]["diff"]).is_file()
        and sha256_file(out_dir / row["data"]["snapshot"]) == row["candidate_sha256"]
        for row in snapshot_rows
    )
    raw_fingerprints = Counter(_event_fingerprint(row) for row in raw_rows)
    embedded_fingerprints = Counter(
        _event_fingerprint(raw)
        for row in rows
        for raw in [row.get("data", {}).get("raw_codex_event")]
        if isinstance(raw, dict)
    )
    raw_payload_coverage = all(
        embedded_fingerprints[fingerprint] >= count
        for fingerprint, count in raw_fingerprints.items()
    )
    completed_commands = [
        row
        for row in completed_raw_items
        if row["item"].get("type") == "command_execution"
    ]
    completed_command_payloads = all(
        row["item"].get("command") is not None
        and row["item"].get("status") is not None
        and row["item"].get("exit_code") is not None
        and row["item"].get("aggregated_output") is not None
        for row in completed_commands
    )
    truncation_pattern = re.compile(
        r"\.\.\.\s*\[(?:truncated|omitted)\]|"
        r"(?:output|lines?)\s+(?:truncated|omitted)",
        re.IGNORECASE,
    )
    truncation_marker_count = sum(
        bool(truncation_pattern.search(str(row["item"].get("aggregated_output") or "")))
        for row in completed_commands
    )
    shell_edit_suspects = [
        str(row["item"].get("command"))
        for row in completed_commands
        if _command_modifies_candidate(str(row["item"].get("command")))
    ]
    fidelity = {
        **event_audit,
        "raw_event_count": len(raw_rows),
        "all_raw_events_exactly_indexed": raw_payload_coverage,
        "completed_command_payloads_complete": completed_command_payloads,
        "tool_output_truncation_marker_count": truncation_marker_count,
        "shell_edit_suspect_count": len(shell_edit_suspects),
        "shell_edit_suspects": shell_edit_suspects,
        "shell_candidate_edits_allowed": (
            contract_profile == "cross_provider_20260819"
        ),
        "completed_tool_or_edit_boundaries": completed_boundaries,
        "candidate_snapshot_count": len(snapshots),
        "all_boundaries_have_candidate_snapshot": snapshot_coverage,
        "all_snapshot_and_diff_files_hash_valid": snapshot_files_complete,
        "input_unchanged": input_unchanged,
        "raw_codex_jsonl_preserved": True,
        "normalized_log_is_secondary_index": True,
        "visible_reasoning_item_count": len(reasoning_items),
        "visible_reasoning_text_chars": visible_reasoning_chars,
        "reasoning_summary_requested": reasoning_summary,
        "raw_reasoning_display_requested": show_raw_agent_reasoning,
        "reasoning_summary_observed": bool(reasoning_items),
        "reasoning_token_count_available": bool(
            isinstance(usage, dict) and usage.get("reasoning_output_tokens") is not None
        ),
        "raw_hidden_chain_of_thought_claimed": False,
        "usage": usage,
        "secret_match_count": secret_match_count(out_dir, ()),
    }
    fidelity["f3"] = bool(
        event_audit["valid_f3_event_stream"]
        and raw_payload_coverage
        and completed_command_payloads
        and truncation_marker_count == 0
        and (
            not shell_edit_suspects
            or contract_profile == "cross_provider_20260819"
        )
        and snapshot_coverage
        and snapshot_files_complete
        and input_unchanged
        and fidelity["raw_event_count"] > 0
    )
    validation = {
        "input_unchanged": input_unchanged,
        "candidate_sha256": candidate_sha,
        "verus": final_checks["verus"],
        "lynette": final_checks["lynette"],
    }
    result = {
        "run_id": out_dir.name,
        "started_at": started_at,
        "finished_at": _now(),
        "wall_seconds": time.monotonic() - started,
        "codex_returncode": returncode,
        "timed_out": timed_out.is_set(),
        "status": (
            "SOLVED"
            if final_checks["verus"]["passed"] and final_checks["lynette"]["passed"]
            else "UNSOLVED"
        ),
        "fidelity": fidelity,
        "validation": validation,
        "workspace_inventory": inventory(workspace),
    }
    for name, data in (
        ("fidelity_audit.json", fidelity),
        ("validation.json", validation),
        ("result.json", result),
        ("workspace_inventory.json", result["workspace_inventory"]),
    ):
        (out_dir / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result
