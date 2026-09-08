from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .handsoff_m0 import infer_model, parse_copilot_usage


SCHEMA_VERSION = "verus-trajectory-v1"
ASSISTANT_RE = re.compile(r"^\s*●\s?(.*)$")
TOOL_RE = re.compile(r"^\s*(?P<status>[✓✗])\s+(?P<label>.*)$")
COMMAND_RE = re.compile(r"^\s*\$\s+(?P<command>.*)$")
EDIT_RE = re.compile(
    r"^(?P<operation>Create|Edit)\s+(?P<path>.+?)\s+"
    r"\((?P<delta>[^)]*)\)\s*$",
    re.IGNORECASE,
)
DELTA_RE = re.compile(r"(?P<sign>[+-])(?P<count>\d+)")
VERUS_RESULT_RE = re.compile(
    r"verification results::\s*(?P<verified>\d+)\s+verified,\s*"
    r"(?P<errors>\d+)\s+errors?",
    re.IGNORECASE,
)
ERROR_RE = re.compile(r"(?m)^error(?:\[[^]]+\])?:\s*([^\n]+)")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _file_record(path: Path, root: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _edit_details(label: str) -> dict[str, Any]:
    match = EDIT_RE.match(label)
    if not match:
        return {}
    added = 0
    deleted = 0
    for delta in DELTA_RE.finditer(match.group("delta")):
        count = int(delta.group("count"))
        if delta.group("sign") == "+":
            added += count
        else:
            deleted += count
    return {
        "operation": match.group("operation").lower(),
        "path": match.group("path"),
        "added_lines_reported": added,
        "deleted_lines_reported": deleted,
    }


def _sonnet_events(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    events: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        assistant = ASSISTANT_RE.match(line)
        if assistant:
            content = [assistant.group(1).strip()]
            end = index + 1
            while end < len(lines):
                if ASSISTANT_RE.match(lines[end]) or TOOL_RE.match(lines[end]):
                    break
                if end + 1 < len(lines) and COMMAND_RE.match(lines[end + 1]):
                    break
                content.append(lines[end].strip())
                end += 1
            events.append(
                {
                    "event_index": len(events) + 1,
                    "type": "assistant_message",
                    "line_start": index + 1,
                    "line_end": end,
                    "content": "\n".join(content).strip(),
                }
            )
            index = end
            continue

        tool = TOOL_RE.match(line)
        bare_tool = (
            not tool
            and index + 1 < len(lines)
            and bool(COMMAND_RE.match(lines[index + 1]))
        )
        if tool or bare_tool:
            label = tool.group("label").strip() if tool else line.strip()
            event_type = "code_edit" if EDIT_RE.match(label) else "tool_call"
            if "verus" in label.lower():
                event_type = "verifier_invocation"
            event = {
                "event_index": len(events) + 1,
                "type": event_type,
                "line_start": index + 1,
                "line_end": index + 1,
                "status_marker": tool.group("status") if tool else None,
                "label": label,
                **_edit_details(label),
            }
            events.append(event)
            index += 1
            continue

        command = COMMAND_RE.match(line)
        if command:
            if not events or events[-1]["type"] == "assistant_message":
                events.append(
                    {
                        "event_index": len(events) + 1,
                        "type": "tool_call",
                        "line_start": index + 1,
                        "line_end": index + 1,
                        "label": "unlabeled command",
                    }
                )
            events[-1]["command"] = command.group("command").strip()
            if "verus" in command.group("command").lower():
                events[-1]["type"] = "verifier_invocation"
            events[-1]["line_end"] = index + 1
            index += 1
            continue

        result = VERUS_RESULT_RE.search(line)
        if result:
            for event in reversed(events):
                if event["type"] == "verifier_invocation":
                    event["verifier"] = _verifier_summary(line)
                    event["line_end"] = index + 1
                    break
        index += 1

    return events


def parse_sonnet45_trace(log_path: Path) -> dict[str, Any]:
    log_path = log_path.resolve()
    if not log_path.is_file():
        raise ValueError(f"Sonnet trace log does not exist: {log_path}")
    if log_path.suffix != ".log":
        raise ValueError("Sonnet trace input must be a .log file")
    source_path = log_path.with_suffix(".rs")
    verified_path = log_path.with_name(f"{log_path.stem}_verified.rs")
    text = log_path.read_text(encoding="utf-8", errors="replace")
    events = _sonnet_events(text)
    result_dir = log_path.parent.name
    counts = Counter(event["type"] for event in events)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_format": "sonnet45_terminal_log",
        "reconstruction_fidelity": "partial_terminal_transcript",
        "raw_data_read_only": True,
        "trace_id": _sha256_bytes(log_path.read_bytes())[:20],
        "task_id": log_path.stem,
        "model": infer_model(result_dir),
        "artifacts": {
            "log": _file_record(log_path, log_path.parent),
            "input_source": _file_record(source_path, log_path.parent),
            "paired_final_source": _file_record(verified_path, log_path.parent),
        },
        "event_counts": dict(sorted(counts.items())),
        "events": events,
        "usage": parse_copilot_usage(text),
        "checkpoint_contract": {
            "input_source_exact": source_path.is_file(),
            "paired_final_source_exact": verified_path.is_file(),
            "intermediate_source_exact": False,
            "reason": (
                "The terminal log contains rendered or collapsed edit summaries; "
                "it does not preserve complete machine-applicable intermediate patches."
            ),
        },
    }


def _raw_item(event: dict[str, Any]) -> dict[str, Any]:
    return (
        event.get("data", {})
        .get("raw_codex_event", {})
        .get("item", {})
    )


def _verifier_summary(output: str) -> dict[str, Any]:
    result = VERUS_RESULT_RE.search(output)
    errors = ERROR_RE.findall(output)
    summary: dict[str, Any] = {
        "passed": bool(result and int(result.group("errors")) == 0 and not errors),
        "verified_functions": int(result.group("verified")) if result else None,
        "reported_errors": int(result.group("errors")) if result else None,
        "error_headlines": errors,
    }
    return summary


def _structured_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for event in events:
        item = _raw_item(event)
        row = {
            "event_index": event.get("event_index"),
            "timestamp": event.get("timestamp"),
            "type": event.get("type"),
            "actor": event.get("actor"),
            "candidate_sha256": event.get("candidate_sha256"),
            "payload_complete": event.get("payload_complete"),
            "tool_call_id": event.get("tool_call_id"),
        }
        if item:
            row.update(
                {
                    "tool_type": item.get("type"),
                    "command": item.get("command"),
                    "tool_status": item.get("status"),
                    "exit_code": item.get("exit_code"),
                }
            )
        if event.get("type") == "verifier":
            output = str(item.get("aggregated_output") or "")
            row["verifier"] = _verifier_summary(output)
        normalized.append(row)
    return normalized


def _complete_ledger_usage(prediction_dir: Path, task_id: str) -> dict[str, Any] | None:
    ledger_path = prediction_dir.parent.parent / "bridge_calls.jsonl"
    if not ledger_path.is_file():
        return None
    totals: Counter[str] = Counter()
    records = 0
    for record in _load_jsonl(ledger_path):
        ledger_task = str(record.get("task_id") or "")
        if ledger_task != task_id and f"--{task_id}--" not in ledger_task:
            continue
        records += 1
        attempts = record.get("attempts") or []
        totals["attempts"] += len(attempts)
        for attempt in attempts:
            usage = attempt.get("usage") or {}
            for key in (
                "prompt_tokens",
                "completion_tokens",
                "prompt_cache_hit_tokens",
                "prompt_cache_miss_tokens",
                "reasoning_tokens",
            ):
                totals[key] += int(usage.get(key) or 0)
    if not records:
        return None
    totals["requests"] = records
    totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
    return dict(totals)


def parse_structured_prediction(prediction_dir: Path) -> dict[str, Any]:
    prediction_dir = prediction_dir.resolve()
    required = {
        "conversation": prediction_dir / "conversation.json",
        "events": prediction_dir / "agent_events.jsonl",
        "result": prediction_dir / "result.json",
        "input_source": prediction_dir / "workspace/input.rs",
        "final_source": prediction_dir / "workspace/candidate.rs",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise ValueError(f"structured prediction is missing: {', '.join(missing)}")

    conversation = _load_json(required["conversation"])
    if not isinstance(conversation, list):
        raise ValueError("conversation.json must contain an array")
    raw_events = _load_jsonl(required["events"])
    result = _load_json(required["result"])
    task_id = str(result.get("id") or prediction_dir.name)
    event_hashes: dict[str, list[int]] = {}
    for event in raw_events:
        digest = event.get("candidate_sha256")
        event_index = event.get("event_index")
        if isinstance(digest, str) and isinstance(event_index, int):
            event_hashes.setdefault(digest, []).append(event_index)

    checkpoints = []
    snapshots = prediction_dir / "snapshots"
    for source_path in sorted(snapshots.glob("*-candidate.rs")):
        digest = _sha256_file(source_path)
        prefix = source_path.name.split("-", 1)[0]
        event_index = int(prefix) if prefix.isdigit() else None
        diff_path = source_path.with_suffix(".diff")
        checkpoints.append(
            {
                "ordinal": len(checkpoints) + 1,
                "event_index": event_index,
                "candidate_sha256": digest,
                "recorded_hash_match": digest in event_hashes,
                "related_event_indices": event_hashes.get(digest, []),
                "source_path": source_path.relative_to(prediction_dir).as_posix(),
                "source_size_bytes": source_path.stat().st_size,
                "diff_path": (
                    diff_path.relative_to(prediction_dir).as_posix()
                    if diff_path.is_file()
                    else None
                ),
            }
        )

    visible_messages = [
        {
            "ordinal": index + 1,
            "role": item.get("role"),
            "type": item.get("type"),
            "content": item.get("content"),
        }
        for index, item in enumerate(conversation)
        if isinstance(item, dict) and isinstance(item.get("content"), str)
    ]
    event_counts = Counter(
        f"{event.get('actor')}:{event.get('type')}" for event in raw_events
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "source_format": "structured_agent_run",
        "reconstruction_fidelity": "exact_candidate_snapshots",
        "raw_data_read_only": True,
        "trace_id": task_id,
        "task_id": task_id,
        "model": result.get("actor_model"),
        "artifacts": {
            name: _file_record(path, prediction_dir)
            for name, path in required.items()
        },
        "event_counts": dict(sorted(event_counts.items())),
        "events": _structured_events(raw_events),
        "visible_messages": visible_messages,
        "checkpoints": checkpoints,
        "checkpoint_contract": {
            "input_source_exact": True,
            "paired_final_source_exact": True,
            "intermediate_source_exact": bool(checkpoints),
            "snapshot_count": len(checkpoints),
            "all_snapshot_hashes_observed_in_events": bool(checkpoints)
            and all(row["recorded_hash_match"] for row in checkpoints),
        },
        "outcome": {
            key: result.get(key)
            for key in (
                "status",
                "proof_solved",
                "within_budget",
                "timed_out",
                "safety_passed",
                "fidelity",
                "actor_wall_seconds",
            )
        },
        "usage": {
            "retained": result.get("usage"),
            "complete_ledger": _complete_ledger_usage(prediction_dir, task_id),
        },
    }


def _write_result(payload: dict[str, Any], output: Path | None, source_root: Path) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        print(rendered, end="")
        return
    output = output.resolve()
    source_root = source_root.resolve()
    if output == source_root or source_root in output.parents:
        raise ValueError("output must be outside the raw trace directory")
    if output.exists():
        raise ValueError(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="format", required=True)
    sonnet = subparsers.add_parser("sonnet45")
    sonnet.add_argument("--log", type=Path, required=True)
    sonnet.add_argument("--output", type=Path)
    structured = subparsers.add_parser("structured")
    structured.add_argument("--prediction-dir", type=Path, required=True)
    structured.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.format == "sonnet45":
        payload = parse_sonnet45_trace(args.log)
        _write_result(payload, args.output, args.log.resolve().parent)
    else:
        payload = parse_structured_prediction(args.prediction_dir)
        _write_result(payload, args.output, args.prediction_dir)


if __name__ == "__main__":
    main()
