from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


RAW_LOG_NAME = "codex_events.raw.jsonl"
NORMALIZED_LOG_NAME = "agent_events.jsonl"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nonempty_lines(path: Path) -> list[tuple[int, str]]:
    return [
        (line_number, line.removesuffix("\r"))
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").split("\n"),
            start=1,
        )
        if line.strip()
    ]


def _display_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def _visible_item_text(item: dict[str, Any]) -> str | None:
    for key in ("text", "summary", "content"):
        value = item.get(key)
        if value not in (None, ""):
            return _display_text(value)
    return None


def _render_command(item: dict[str, Any], raw_type: str) -> list[str]:
    exit_code = item.get("exit_code")
    status = str(item.get("status") or "")
    if raw_type == "item.started":
        marker = "…"
    elif exit_code == 0 and status in {"completed", "success"}:
        marker = "✓"
    else:
        marker = "✗"
    lines = [f"{marker} Run command", f"   $ {item.get('command', '')}"]
    if raw_type != "item.started" or item.get("aggregated_output"):
        lines.append("   <tool_output>")
        output = str(item.get("aggregated_output") or "")
        lines.extend(f"   {line}" for line in output.splitlines())
        if output.endswith("\n"):
            lines.append("   ")
        lines.append("   </tool_output>")
        lines.append(
            f"   status={status or 'unknown'} exit_code={exit_code!r}"
        )
    return lines


def _render_item(item: dict[str, Any], raw_type: str) -> list[str]:
    item_type = str(item.get("type") or "unknown")
    if item_type == "command_execution":
        return _render_command(item, raw_type)
    if item_type == "file_change":
        marker = "✓" if raw_type == "item.completed" else "…"
        return [
            f"{marker} Edit",
            _display_text(item.get("changes", [])),
        ]
    if item_type == "reasoning":
        text = _visible_item_text(item)
        return ["● Reasoning summary", text or "(no visible reasoning text)"]
    if item_type == "agent_message":
        text = _visible_item_text(item)
        return ["● Agent", text or "(empty agent message)"]
    if item_type == "todo_list":
        lines = ["● Plan"]
        for todo in item.get("items") or []:
            if isinstance(todo, dict):
                done = bool(todo.get("completed") or todo.get("status") == "completed")
                text = todo.get("text") or todo.get("step") or _display_text(todo)
                lines.append(f"   {'✓' if done else '□'} {text}")
            else:
                lines.append(f"   □ {_display_text(todo)}")
        return lines
    return [f"● {item_type} ({raw_type})", _display_text(item)]


def _render_raw_event(raw: Any) -> list[str]:
    if not isinstance(raw, dict):
        return ["● Non-object raw JSON value", _display_text(raw)]
    raw_type = str(raw.get("type") or "unknown")
    item = raw.get("item")
    if isinstance(item, dict):
        return _render_item(item, raw_type)
    if raw_type == "thread.started":
        return [f"● Thread started: {raw.get('thread_id', 'unknown')}"]
    if raw_type == "turn.started":
        return ["● Turn started"]
    if raw_type == "turn.completed":
        return ["● Turn completed", _display_text(raw.get("usage", {}))]
    if raw_type == "turn.failed":
        return ["✗ Turn failed", _display_text(raw)]
    return [f"● {raw_type}", _display_text(raw)]


def _render_host_event(row: dict[str, Any], run_dir: Path) -> list[str]:
    actor = row.get("actor", "unknown")
    event_type = row.get("type", "unknown")
    marker = "✓" if row.get("payload_complete") is True else "!"
    lines = [
        f"{marker} {actor}/{event_type} event {row.get('event_index', '?')}",
        _display_text(row.get("data", {})),
    ]
    data = row.get("data")
    if not isinstance(data, dict) or data.get("boundary") == "initial":
        return lines
    diff_reference = data.get("diff")
    if not isinstance(diff_reference, str):
        return lines
    diff_path = (run_dir / diff_reference).resolve()
    if run_dir != diff_path and run_dir not in diff_path.parents:
        lines.append(f"! Unsafe diff reference not opened: {diff_reference}")
        return lines
    if not diff_path.is_file():
        lines.append(f"! Referenced diff is missing: {diff_reference}")
        return lines
    diff = diff_path.read_text(encoding="utf-8")
    if diff:
        lines.extend(
            [
                "   <code_diff>",
                *[f"   {line}" for line in diff.splitlines()],
                "   </code_diff>",
            ]
        )
    return lines


def _metadata(run_dir: Path) -> tuple[str, str]:
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.is_file():
        return run_dir.name, "unknown"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return run_dir.name, "unknown"
    if not isinstance(manifest, dict):
        return run_dir.name, "unknown"
    return str(manifest.get("run_id") or run_dir.name), str(
        manifest.get("model") or "unknown"
    )


def render_verusage_transcript(
    *,
    run_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Render a readable transcript without replacing either source event log."""
    run_dir = run_dir.resolve()
    raw_path = run_dir / RAW_LOG_NAME
    normalized_path = run_dir / NORMALIZED_LOG_NAME
    if not raw_path.is_file():
        raise ValueError(f"missing raw Codex log: {raw_path}")
    if not normalized_path.is_file():
        raise ValueError(f"missing normalized event log: {normalized_path}")

    output_path = output_path.resolve()
    if output_path in {raw_path, normalized_path}:
        raise ValueError("output must not replace a source event log")
    if output_path.exists():
        raise ValueError(f"output already exists: {output_path}")

    raw_lines = _nonempty_lines(raw_path)
    normalized_lines = _nonempty_lines(normalized_path)
    run_id, model = _metadata(run_dir)
    malformed_raw = 0
    malformed_normalized = 0
    rendered: list[str] = [
        "VeruSAGE-style readable Codex transcript",
        f"Run: {run_id}",
        f"Model: {model}",
        f"Raw source: {RAW_LOG_NAME}",
        f"Normalized source: {NORMALIZED_LOG_NAME}",
        "",
        "The readable layer is followed by exact source JSONL blocks.",
        "No event field or tool output is intentionally compressed or redacted.",
        "",
        "=== Readable trajectory ===",
    ]

    for event_number, (line_number, line) in enumerate(raw_lines, start=1):
        rendered.extend(["", f"[{event_number:06d}] raw line {line_number}"])
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            malformed_raw += 1
            rendered.extend(["! Malformed raw JSONL (preserved below)", line])
            continue
        rendered.extend(_render_raw_event(raw))

    rendered.extend(["", "=== Host-side normalized-only events ==="])
    for _, line in normalized_lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            malformed_normalized += 1
            continue
        if not isinstance(row, dict):
            continue
        data = row.get("data")
        if isinstance(data, dict) and isinstance(data.get("raw_codex_event"), dict):
            continue
        rendered.extend(["", *_render_host_event(row, run_dir)])

    rendered.extend(["", "=== Exact raw Codex JSONL ==="])
    for line_number, line in raw_lines:
        rendered.extend(
            [
                f'<raw_event_json line="{line_number}">',
                line,
                "</raw_event_json>",
            ]
        )

    rendered.extend(["", "=== Exact normalized event JSONL ==="])
    for line_number, line in normalized_lines:
        rendered.extend(
            [
                f'<normalized_event_json line="{line_number}">',
                line,
                "</normalized_event_json>",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(rendered) + "\n", encoding="utf-8")
    return {
        "run_id": run_id,
        "model": model,
        "output": str(output_path),
        "raw_event_count": len(raw_lines),
        "normalized_event_count": len(normalized_lines),
        "malformed_raw_count": malformed_raw,
        "malformed_normalized_count": malformed_normalized,
        "raw_log_sha256": _sha256(raw_path),
        "normalized_log_sha256": _sha256(normalized_path),
        "transcript_sha256": _sha256(output_path),
        "exact_raw_jsonl_embedded": True,
        "exact_normalized_jsonl_embedded": True,
        "tool_outputs_untruncated_by_renderer": True,
    }
