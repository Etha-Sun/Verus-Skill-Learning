#!/usr/bin/env python3
"""Measure visible line composition of hands-off logs by model and format."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

from audit_code_edits import parsed_edit_headers


UI_EVENT_RE = re.compile(r"^[✓✗]\s+")
UI_NARRATION_RE = re.compile(r"^●\s+")
UI_BULLET_TOOL_RE = re.compile(
    r"^●\s+(?:Read|List|Run|Edit|Create|Write|Copy|Search|Find|Grep|Glob|"
    r"Bash|Shell|Check|Verify)\b",
    re.IGNORECASE,
)
UI_FAILED_EDIT_HEADER_RE = re.compile(r"^✗\s*Edit\b", re.IGNORECASE)
UI_SHELL_RE = re.compile(r"^\s*\$\s+")
UI_COLLAPSED_RE = re.compile(r"^\s*↪\s*\d+\s+lines\.\.\.")
UI_DIFF_START_RE = re.compile(r"^\s*╭")
UI_DIFF_END_RE = re.compile(r"^\s*╰")
UI_DIFF_ADD_RE = re.compile(r"^\s*│\s*\d+\s*\+\s")
UI_DIFF_DEL_RE = re.compile(r"^\s*│\s*\d+\s*-\s")
UI_USAGE_START_RE = re.compile(
    r"^(?:Total usage est:|Total duration \(API\):|Usage by model:|Tokens\s+↑)"
)
VERUS_RE = re.compile(r"(?i)(?:^|[\s'\"/])(?:verus|verus-checker)(?:\s|$)")
THINKING_RE = re.compile(
    r"(?i)(?:thinking_tokens|reasoning_tokens|thinking tokens|reasoning tokens)"
)


def logical_lines(value: str) -> int:
    if not value:
        return 0
    return len(value.splitlines()) or 1


def nonempty_logical_lines(value: str) -> int:
    return sum(bool(line.strip()) for line in value.splitlines())


def classify_jsonl(text: str) -> list[dict] | None:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].lstrip().startswith("{"):
        return None
    events = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(event, dict):
            return None
        events.append(event)
    return events


def json_metrics(text: str, events: list[dict]) -> dict[str, int]:
    metrics = {
        "physical_lines": len(text.splitlines()),
        "nonempty_physical_lines": sum(
            bool(line.strip()) for line in text.splitlines()
        ),
        "narration_payload_lines": 0,
        "tool_call_payload_lines": 0,
        "tool_result_payload_lines": 0,
        "code_edit_display_lines": 0,
        "code_changed_logical_lines": 0,
        "create_summary_lines": 0,
        "file_change_metadata_lines": 0,
        "verifier_call_payload_lines": 0,
        "verifier_result_payload_lines": 0,
        "usage_lines": 0,
        "thinking_token_lines": 0,
        "collapsed_result_markers": 0,
        "failed_edit_events": 0,
        "summary_only_edit_events": 0,
        "summary_declared_changed_lines": 0,
    }
    started_ids: set[str] = set()
    for event in events:
        status = str(event.get("type", ""))
        if status == "turn.completed" and isinstance(event.get("usage"), dict):
            metrics["usage_lines"] += 1
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", ""))
        item_id = str(item.get("id", ""))
        if item_type in {"agent_message", "reasoning", "thinking"}:
            text_value = str(item.get("text", ""))
            metrics["narration_payload_lines"] += nonempty_logical_lines(text_value)
            metrics["thinking_token_lines"] += sum(
                bool(THINKING_RE.search(line)) for line in text_value.splitlines()
            )
        elif item_type == "command_execution":
            command = str(item.get("command", ""))
            output = str(item.get("aggregated_output", ""))
            is_verifier = bool(VERUS_RE.search(command))
            count_command = status == "item.started"
            if count_command:
                started_ids.add(item_id)
            elif status == "item.completed" and item_id not in started_ids:
                count_command = True
            if count_command:
                command_lines = logical_lines(command)
                metrics["tool_call_payload_lines"] += command_lines
                if is_verifier:
                    metrics["verifier_call_payload_lines"] += command_lines
            if status == "item.completed" and output:
                output_lines = logical_lines(output)
                metrics["tool_result_payload_lines"] += output_lines
                if is_verifier:
                    metrics["verifier_result_payload_lines"] += output_lines
        elif item_type == "file_change" and status == "item.completed":
            metrics["file_change_metadata_lines"] += 1
            for key in ("patch", "diff", "content", "old_text", "new_text"):
                value = item.get(key)
                if isinstance(value, str):
                    metrics["code_edit_display_lines"] += logical_lines(value)
                    metrics["code_changed_logical_lines"] += logical_lines(value)
        serialized = json.dumps(item, ensure_ascii=False)
        metrics["thinking_token_lines"] += sum(
            bool(THINKING_RE.search(line)) for line in serialized.splitlines()
        )
    return metrics


def ui_blocks(lines: list[str]) -> list[tuple[int, int]]:
    starts = [
        index
        for index, line in enumerate(lines)
        if UI_EVENT_RE.match(line)
        or UI_NARRATION_RE.match(line)
        or UI_USAGE_START_RE.match(line)
    ]
    for index, line in enumerate(lines):
        if UI_SHELL_RE.match(line) and (
            index == 0
            or not UI_EVENT_RE.match(lines[index - 1])
            and not UI_NARRATION_RE.match(lines[index - 1])
        ):
            previous = index - 1
            while previous >= 0 and not lines[previous].strip():
                previous -= 1
            starts.append(previous if previous >= 0 else index)
    starts = sorted(set(starts))
    if not starts:
        return [(0, len(lines))] if lines else []
    if starts[0] != 0:
        starts.insert(0, 0)
    return [
        (start, starts[position + 1] if position + 1 < len(starts) else len(lines))
        for position, start in enumerate(starts)
    ]


def text_metrics(text: str) -> dict[str, int]:
    lines = text.splitlines()
    edit_headers = parsed_edit_headers(lines)
    edit_headers_by_start = {
        int(header["start"]): header for header in edit_headers
    }
    edit_header_continuations = {
        index
        for header in edit_headers
        for index in range(int(header["start"]) + 1, int(header["end"]) + 1)
    }
    metrics = {
        "physical_lines": len(lines),
        "nonempty_physical_lines": sum(bool(line.strip()) for line in lines),
        "narration_payload_lines": 0,
        "tool_call_payload_lines": 0,
        "tool_result_payload_lines": 0,
        "code_edit_display_lines": 0,
        "code_changed_logical_lines": 0,
        "create_summary_lines": 0,
        "file_change_metadata_lines": 0,
        "verifier_call_payload_lines": 0,
        "verifier_result_payload_lines": 0,
        "usage_lines": 0,
        "thinking_token_lines": sum(bool(THINKING_RE.search(line)) for line in lines),
        "collapsed_result_markers": sum(bool(UI_COLLAPSED_RE.match(line)) for line in lines),
        "failed_edit_events": sum(
            bool(UI_FAILED_EDIT_HEADER_RE.match(line)) for line in lines
        ),
        "summary_only_edit_events": 0,
        "summary_declared_changed_lines": 0,
    }
    in_diff = False
    usage_started = False
    for index, line in enumerate(lines):
        if usage_started and (
            UI_EVENT_RE.match(line) or UI_NARRATION_RE.match(line)
        ):
            usage_started = False
        if UI_USAGE_START_RE.match(line):
            usage_started = True
        if usage_started:
            if line.strip():
                metrics["usage_lines"] += 1
            continue
        header = edit_headers_by_start.get(index)
        if header:
            metrics["code_edit_display_lines"] += (
                int(header["end"]) - int(header["start"]) + 1
            )
            if header["operation"] == "create":
                metrics["create_summary_lines"] += 1
            if header["style"] == "summary_only":
                metrics["summary_only_edit_events"] += 1
                metrics["summary_declared_changed_lines"] += (
                    int(header["declared_add"]) + int(header["declared_del"])
                )
        if index in edit_header_continuations:
            continue
        if UI_DIFF_START_RE.match(line):
            in_diff = True
        if in_diff:
            metrics["code_edit_display_lines"] += 1
            metrics["code_changed_logical_lines"] += bool(
                UI_DIFF_ADD_RE.match(line) or UI_DIFF_DEL_RE.match(line)
            )
        if UI_DIFF_END_RE.match(line):
            in_diff = False

    for start, end in ui_blocks(lines):
        block = lines[start:end]
        if not block:
            continue
        first = block[0]
        header = edit_headers_by_start.get(start)
        if UI_USAGE_START_RE.match(first) or (
            header and header["style"] == "diff_box"
        ):
            continue
        if header and header["style"] == "summary_only":
            header_lines = int(header["end"]) - int(header["start"]) + 1
            metrics["narration_payload_lines"] += sum(
                bool(line.strip()) for line in block[header_lines:]
            )
            continue
        nonempty = sum(bool(line.strip()) for line in block)
        if UI_NARRATION_RE.match(first) and not UI_BULLET_TOOL_RE.match(first):
            metrics["narration_payload_lines"] += nonempty
            continue
        if UI_BULLET_TOOL_RE.match(first):
            command_lines = sum(
                bool(re.match(r"^\s*│", line)) for line in block[1:]
            )
            result_lines = sum(
                bool(re.match(r"^\s*└", line)) for line in block[1:]
            )
            call_lines = 1 + command_lines
            metrics["tool_call_payload_lines"] += call_lines
            metrics["tool_result_payload_lines"] += result_lines
            metrics["narration_payload_lines"] += sum(
                bool(line.strip())
                and not re.match(r"^\s*[│└]", line)
                for line in block[1:]
            )
            if any(VERUS_RE.search(line) for line in block):
                metrics["verifier_call_payload_lines"] += call_lines
                metrics["verifier_result_payload_lines"] += result_lines
            continue
        shell_indexes = [
            index for index, line in enumerate(block) if UI_SHELL_RE.match(line)
        ]
        collapsed_indexes = [
            index for index, line in enumerate(block) if UI_COLLAPSED_RE.match(line)
        ]
        saw_shell = bool(shell_indexes)
        command_lines = len(shell_indexes)
        continuation_lines = 0
        result_lines = len(collapsed_indexes)
        if saw_shell:
            last_shell = shell_indexes[-1]
            if collapsed_indexes:
                first_result = collapsed_indexes[0]
                continuation_lines = sum(
                    bool(line.strip())
                    for line in block[last_shell + 1 : first_result]
                )
            else:
                result_lines += sum(
                    bool(line.strip()) for line in block[last_shell + 1 :]
                )
        call_lines = int(bool(UI_EVENT_RE.match(first))) + command_lines + continuation_lines
        if saw_shell and not UI_EVENT_RE.match(first) and first.strip():
            call_lines += 1
        if not saw_shell and UI_EVENT_RE.match(first):
            result_lines += sum(bool(line.strip()) for line in block[1:])
        metrics["tool_call_payload_lines"] += call_lines
        metrics["tool_result_payload_lines"] += result_lines
        if any(VERUS_RE.search(line) for line in block):
            metrics["verifier_call_payload_lines"] += call_lines
            metrics["verifier_result_payload_lines"] += result_lines

    if not any(UI_NARRATION_RE.match(line) for line in lines):
        excluded = (
            metrics["usage_lines"]
            + metrics["code_edit_display_lines"]
            + metrics["tool_call_payload_lines"]
            + metrics["tool_result_payload_lines"]
        )
        metrics["narration_payload_lines"] = max(
            0, metrics["nonempty_physical_lines"] - excluded
        )
    return metrics


def mean(values: list[int]) -> float:
    return round(statistics.mean(values), 2) if values else 0.0


def aggregate(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    grouped: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row[key]) for key in keys)].append(row)
    metric_names = [
        "physical_lines",
        "nonempty_physical_lines",
        "narration_payload_lines",
        "tool_call_payload_lines",
        "tool_result_payload_lines",
        "code_edit_display_lines",
        "code_changed_logical_lines",
        "create_summary_lines",
        "file_change_metadata_lines",
        "verifier_call_payload_lines",
        "verifier_result_payload_lines",
        "usage_lines",
        "thinking_token_lines",
        "collapsed_result_markers",
        "failed_edit_events",
        "summary_only_edit_events",
        "summary_declared_changed_lines",
    ]
    output = []
    for group, items in sorted(grouped.items()):
        result = {key: value for key, value in zip(keys, group)}
        result["logs"] = len(items)
        for metric in metric_names:
            values = [int(item[metric]) for item in items]
            result[f"mean_{metric}"] = mean(values)
            result[f"median_{metric}"] = round(statistics.median(values), 2)
        output.append(result)
    return output


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    feature_rows = [
        json.loads(line)
        for line in args.features.read_text().splitlines()
        if line.strip()
    ]
    rows = []
    for feature in feature_rows:
        path = args.corpus_root / feature["relative_log_path"]
        text = path.read_text(errors="replace")
        events = classify_jsonl(text)
        metrics = json_metrics(text, events) if events is not None else text_metrics(text)
        rows.append(
            {
                "relative_log_path": feature["relative_log_path"],
                "directory_group": feature["directory_group"],
                "result_dir": feature["result_dir"],
                "model": feature["model"],
                "format": feature["format"],
                **metrics,
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "per_log_line_composition.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    by_model_format = aggregate(rows, ("model", "format"))
    by_model = aggregate(rows, ("model",))
    by_directory = aggregate(rows, ("directory_group",))
    write_csv(args.out_dir / "line_composition_by_model_format.csv", by_model_format)
    write_csv(args.out_dir / "line_composition_by_model.csv", by_model)
    write_csv(args.out_dir / "line_composition_by_directory.csv", by_directory)
    (args.out_dir / "line_composition_summary.json").write_text(
        json.dumps(
            {
                "scope_logs": len(rows),
                "overall": aggregate(rows, ())[0],
                "by_model_format": by_model_format,
                "by_model": by_model,
                "by_directory": by_directory,
                "notes": {
                    "physical_lines": "Raw splitlines count. JSONL output payloads remain encoded inside event lines.",
                    "payload_lines": "Decoded logical lines for JSONL; visible physical evidence lines for UI/plain logs.",
                    "verifier_lines": "Subset of tool call/result payload lines and must not be added to them.",
                    "code_changed_logical_lines": "UI +/- logical lines or native JSON patch lines; excludes diff context and wrapped continuations.",
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
