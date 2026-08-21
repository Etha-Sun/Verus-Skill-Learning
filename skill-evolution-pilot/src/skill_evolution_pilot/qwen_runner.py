from __future__ import annotations

import difflib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .events import EventLog, audit_events, load_events
from .openrouter_adapter import DEFAULT_MODEL, OpenRouterClient, SOLVER_TEMPERATURE
from .redaction import secret_match_count
from .workspace import inventory, prepare_solver_workspace, sha256_file


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read one allowlisted file from the isolated workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "enum": ["input.rs", "candidate.rs", "TASK.md", "SKILL.md"],
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_text",
            "description": (
                "Replace exactly one occurrence of old_text in candidate.rs. "
                "Use complete exact text copied from read_file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "old_text": {"type": "string", "minLength": 1},
                    "new_text": {"type": "string"},
                },
                "required": ["old_text", "new_text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_verus",
            "description": "Run Verus on the current candidate.rs.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_lynette",
            "description": "Compare input.rs and candidate.rs for proof-only safety.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Finish only after Verus and Lynette pass or attempts are exhausted.",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
                "additionalProperties": False,
            },
        },
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _external_output(out_dir: Path) -> Path:
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


def _executable(path: Path, name: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ValueError(f"{name} is not executable: {resolved}")
    return resolved


def _run(command: list[str], cwd: Path, timeout_seconds: int = 120) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "timed_out": False,
            "wall_seconds": time.monotonic() - started,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": None,
            "timed_out": True,
            "wall_seconds": time.monotonic() - started,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def _verus_passed(result: dict[str, Any]) -> bool:
    text = str(result["stdout"]) + str(result["stderr"])
    return (
        result["returncode"] == 0
        and not result["timed_out"]
        and "error: aborting" not in text.lower()
    )


def _tool_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    function = tool_call.get("function")
    if not isinstance(function, dict):
        raise ValueError("tool call lacks function")
    raw = function.get("arguments", "{}")
    if isinstance(raw, dict):
        arguments = raw
    elif isinstance(raw, str):
        arguments = json.loads(raw)
    else:
        raise ValueError("tool arguments are neither JSON text nor an object")
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must decode to an object")
    return arguments


def _assistant_message(message: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "role": "assistant",
        "content": message.get("content"),
    }
    if isinstance(message.get("tool_calls"), list):
        result["tool_calls"] = message["tool_calls"]
    return result


def _snapshot(
    snapshots: Path,
    index: int,
    candidate: Path,
    before: str | None = None,
) -> dict[str, Any]:
    snapshots.mkdir(parents=True, exist_ok=True)
    text = candidate.read_text(encoding="utf-8")
    snapshot = snapshots / f"{index:04d}-candidate.rs"
    snapshot.write_text(text, encoding="utf-8")
    diff_path = snapshots / f"{index:04d}.diff"
    diff_text = ""
    if before is not None:
        diff_text = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                text.splitlines(keepends=True),
                fromfile="candidate.before.rs",
                tofile="candidate.after.rs",
            )
        )
    diff_path.write_text(diff_text, encoding="utf-8")
    return {
        "snapshot": str(snapshot),
        "snapshot_sha256": sha256_file(snapshot),
        "diff": str(diff_path),
        "diff_sha256": sha256_file(diff_path),
        "candidate_sha256": sha256_file(candidate),
    }


def _prompt(skill_present: bool) -> str:
    skill_instruction = " Read SKILL.md and follow it." if skill_present else ""
    return (
        "Solve the Verus proof task in candidate.rs from scratch."
        + skill_instruction
        + "\nUse only the provided tools. input.rs is immutable. Edit candidate.rs "
        "only through replace_text. Preserve executable behavior, signatures, "
        "requires, ensures, and decreases. Never use assume, admit, external_body, "
        "new axioms, or verification bypasses. Iterate with Verus, then run Lynette. "
        "Do not finish early merely because one attempt failed."
    )


def run_qwen_agentic_smoke(
    *,
    source: Path,
    out_dir: Path,
    verus_bin: Path,
    lynette_bin: Path,
    model: str = DEFAULT_MODEL,
    max_iters: int = 6,
    max_tokens: int = 8192,
    temperature: float = SOLVER_TEMPERATURE,
    skill_text: str | None = None,
    provider_timeout_seconds: float = 180.0,
    client: OpenRouterClient | None = None,
) -> dict[str, Any]:
    if max_iters < 1:
        raise ValueError("max_iters must be positive")
    out_dir = _external_output(out_dir)
    verus_bin = _executable(verus_bin, "verus")
    lynette_bin = _executable(lynette_bin, "lynette")
    source = source.resolve()
    source_sha = sha256_file(source)
    workspace = out_dir / "workspace"
    prompt = _prompt(skill_text is not None)
    prepare_solver_workspace(
        source=source,
        workspace=workspace,
        task_text=prompt,
        skill_text=skill_text,
    )
    candidate = workspace / "candidate.rs"
    input_path = workspace / "input.rs"
    prompt_path = out_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    secret = os.environ.get("OPENROUTER_API_KEY", "")
    events_path = out_dir / "agent_events.jsonl"
    provider_io = out_dir / "provider_io.jsonl"
    log = EventLog(events_path, out_dir.name, (secret,))
    api = client or OpenRouterClient(
        model=model,
        timeout_seconds=provider_timeout_seconds,
    )
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are an autonomous Verus proof-repair agent. Think carefully, "
                "but interact with the workspace only through the supplied tools."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    manifest = {
        "schema_version": "1",
        "run_id": out_dir.name,
        "created_at": _now(),
        "stage": "qwen_agentic_fidelity_smoke",
        "transport": "openrouter",
        "model": model,
        "temperature": temperature,
        "max_iters": max_iters,
        "max_tokens_per_request": max_tokens,
        "provider_timeout_seconds": provider_timeout_seconds,
        "source_sha256": source_sha,
        "prompt_sha256": sha256_file(prompt_path),
        "reference_proof_visible": False,
        "prior_trace_visible": False,
        "skill_present": skill_text is not None,
        "skill_sha256": (
            sha256_file(workspace / "SKILL.md") if skill_text is not None else None
        ),
        "tool_names": [tool["function"]["name"] for tool in TOOLS],
    }
    (out_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    started = time.monotonic()
    request_count = 0
    finish_requested = False
    last_verus: dict[str, Any] | None = None
    last_lynette: dict[str, Any] | None = None
    tool_boundary = 0
    snapshots = out_dir / "snapshots"
    _snapshot(snapshots, tool_boundary, candidate)

    for iteration in range(1, max_iters + 1):
        response = api.complete(
            messages=messages,
            event_log=log,
            provider_io_path=provider_io,
            temperature=temperature,
            top_p=1.0,
            max_tokens=max_tokens,
            reasoning_effort="high",
            tools=TOOLS,
            tool_choice="auto",
        )
        request_count += 1
        message = response["message"]
        messages.append(_assistant_message(message))
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list) or not tool_calls:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Continue by calling an available tool. Do not provide only "
                        "narration while the proof remains unchecked."
                    ),
                }
            )
            continue

        for tool_call in tool_calls:
            tool_boundary += 1
            tool_id = str(tool_call.get("id") or f"host-{iteration}-{tool_boundary}")
            function = tool_call.get("function")
            name = str(function.get("name")) if isinstance(function, dict) else ""
            before_sha = sha256_file(candidate)
            log.append(
                actor="host",
                event_type="tool_call",
                tool_call_id=tool_id,
                candidate_sha256=before_sha,
                data={"iteration": iteration, "provider_tool_call": tool_call},
            )
            try:
                arguments = _tool_arguments(tool_call)
                if name == "read_file":
                    path = str(arguments["path"])
                    if path not in {"input.rs", "candidate.rs", "TASK.md", "SKILL.md"}:
                        raise ValueError("path is not allowlisted")
                    target = workspace / path
                    if not target.is_file():
                        raise ValueError(f"allowlisted file is absent: {path}")
                    output = target.read_text(encoding="utf-8")
                    tool_data: dict[str, Any] = {"path": path, "content": output}
                elif name == "replace_text":
                    old_text = str(arguments["old_text"])
                    new_text = str(arguments["new_text"])
                    before = candidate.read_text(encoding="utf-8")
                    if before.count(old_text) != 1:
                        raise ValueError("old_text must occur exactly once")
                    candidate.write_text(
                        before.replace(old_text, new_text, 1),
                        encoding="utf-8",
                    )
                    snapshot = _snapshot(snapshots, tool_boundary, candidate, before)
                    log.append(
                        actor="host",
                        event_type="edit",
                        tool_call_id=tool_id,
                        candidate_sha256=snapshot["candidate_sha256"],
                        data={
                            "old_text": old_text,
                            "new_text": new_text,
                            **snapshot,
                        },
                    )
                    output = "candidate.rs updated"
                    tool_data = snapshot
                elif name == "run_verus":
                    result = _run([str(verus_bin), "candidate.rs"], workspace)
                    passed = _verus_passed(result)
                    last_verus = {
                        **result,
                        "passed": passed,
                        "candidate_sha256": sha256_file(candidate),
                    }
                    log.append(
                        actor="verus",
                        event_type="verifier",
                        candidate_sha256=last_verus["candidate_sha256"],
                        data=last_verus,
                    )
                    output = str(result["stdout"]) + str(result["stderr"])
                    tool_data = last_verus
                elif name == "run_lynette":
                    result = _run(
                        [
                            str(lynette_bin),
                            "compare",
                            "-t",
                            "input.rs",
                            "candidate.rs",
                        ],
                        workspace,
                    )
                    last_lynette = {
                        **result,
                        "passed": result["returncode"] == 0
                        and not result["timed_out"],
                        "candidate_sha256": sha256_file(candidate),
                    }
                    log.append(
                        actor="lynette",
                        event_type="verifier",
                        candidate_sha256=last_lynette["candidate_sha256"],
                        data=last_lynette,
                    )
                    output = str(result["stdout"]) + str(result["stderr"])
                    tool_data = last_lynette
                elif name == "finish":
                    finish_requested = True
                    output = str(arguments["summary"])
                    tool_data = {"summary": output}
                else:
                    raise ValueError(f"unsupported tool: {name}")
                tool_result = {"ok": True, "name": name, **tool_data}
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                output = f"{type(exc).__name__}: {exc}"
                tool_result = {"ok": False, "name": name, "error": output}

            after_sha = sha256_file(candidate)
            log.append(
                actor="host",
                event_type="tool_result",
                tool_call_id=tool_id,
                candidate_sha256=after_sha,
                data=tool_result,
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": output,
                }
            )

        current_sha = sha256_file(candidate)
        solved = bool(
            last_verus
            and last_lynette
            and last_verus["passed"]
            and last_lynette["passed"]
            and last_verus["candidate_sha256"] == current_sha
            and last_lynette["candidate_sha256"] == current_sha
        )
        if solved or finish_requested:
            break

    final_verus_result = _run([str(verus_bin), "candidate.rs"], workspace)
    final_lynette_result = _run(
        [str(lynette_bin), "compare", "-t", "input.rs", "candidate.rs"],
        workspace,
    )
    final_sha = sha256_file(candidate)
    final_verus = {
        **final_verus_result,
        "passed": _verus_passed(final_verus_result),
        "candidate_sha256": final_sha,
    }
    final_lynette = {
        **final_lynette_result,
        "passed": final_lynette_result["returncode"] == 0
        and not final_lynette_result["timed_out"],
        "candidate_sha256": final_sha,
    }
    log.append(
        actor="verus",
        event_type="verifier",
        candidate_sha256=final_sha,
        data={"independent_final": True, **final_verus},
    )
    log.append(
        actor="lynette",
        event_type="verifier",
        candidate_sha256=final_sha,
        data={"independent_final": True, **final_lynette},
    )

    rows, parse_errors = load_events(events_path)
    audit = audit_events(rows, parse_errors)
    provider_rows = [
        json.loads(line)
        for line in provider_io.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    request_rows = [row for row in provider_rows if row["direction"] == "request"]
    response_rows = [row for row in provider_rows if row["direction"] == "response"]
    returned_models = {
        row["payload"].get("model")
        for row in response_rows
        if isinstance(row.get("payload"), dict)
    }
    fidelity = {
        **audit,
        "request_count": request_count,
        "provider_request_count": len(request_rows),
        "provider_response_count": len(response_rows),
        "request_count_matches": request_count
        == len(request_rows)
        == len(response_rows),
        "returned_models": sorted(str(value) for value in returned_models),
        "model_identity_matches": returned_models == {model},
        "input_unchanged": sha256_file(input_path) == source_sha,
        "secret_match_count": secret_match_count(out_dir, (secret,)),
        "workspace_inventory": inventory(workspace),
    }
    fidelity["f3"] = bool(
        fidelity["valid_f3_event_stream"]
        and fidelity["request_count_matches"]
        and fidelity["model_identity_matches"]
        and fidelity["input_unchanged"]
        and fidelity["secret_match_count"] == 0
    )
    solved = final_verus["passed"] and final_lynette["passed"]
    result = {
        "run_id": out_dir.name,
        "finished_at": _now(),
        "wall_seconds": time.monotonic() - started,
        "status": "SOLVED" if solved else "UNSOLVED",
        "finish_requested": finish_requested,
        "request_count": request_count,
        "fidelity": fidelity,
        "validation": {"verus": final_verus, "lynette": final_lynette},
    }
    (out_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result
