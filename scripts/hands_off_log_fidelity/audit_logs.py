#!/usr/bin/env python3
"""Audit structural fidelity of historical hands-off Copilot logs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from audit_code_edits import ui_edit_boxes
from audit_line_composition import text_metrics


TEXT_TOOL_RE = re.compile(
    r"(?m)^[✓●✗]\s+(?:Run|Read|Edit|Create|Write|Copy|List|Search|"
    r"Find|Grep|Glob|Bash|Shell|str_replace_editor)\b"
)
TEXT_COMMAND_RE = re.compile(r"(?m)^\s*\$\s+")
TEXT_EDIT_RE = re.compile(
    r"(?mi)^[✓●✗]?\s*(?:Edit|Create|Write|str_replace_editor: create)\b"
)
TEXT_INLINE_DIFF_RE = re.compile(
    r"(?m)(?:^diff --git |^[ \t]*[│|]\s*\d*\s*[+-]\s)"
)
TEXT_COLLAPSED_RE = re.compile(r"(?m)↪\s*\d+\s+lines\.\.\.")
TEXT_SUMMARY_RESULT_RE = re.compile(
    r"(?m)(?:↪\s*\d+\s+lines\.\.\.|└\s+.*(?:lines? read|files? found))"
)
VERUS_COMMAND_RE = re.compile(
    r"(?i)(?:^|[\s'\"/])(?:verus|verus-checker)(?:\s|$)"
)
VERUS_RESULT_RE = re.compile(
    r"(?i)(?:verification results::|error: aborting due to|"
    r"verus-checker.*(?:pass|fail)|verified,\s*\d+\s+errors)"
)
VISIBLE_REASONING_RE = re.compile(r"(?m)^●\s+")
USAGE_RE = re.compile(
    r"(?:Total usage est:|Usage by model:|Tokens\s+↑|"
    r'"usage"\s*:\s*\{)'
)
THINKING_TOKEN_RE = re.compile(
    r"(?i)(?:thinking_tokens|reasoning_tokens|thinking tokens|reasoning tokens)"
)
SECRET_LIKE_RE = re.compile(
    r"(?i)(?:\b(?:CODEX|OPENAI|ANTHROPIC|GITHUB|GH)_API_KEY\s*=\s*\S+|"
    r"\b(?:sk-(?:proj-)?|ghp_|github_pat_)[A-Za-z0-9_-]{16,})"
)


def classify_jsonl(text: str) -> tuple[bool, list[dict]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].lstrip().startswith("{"):
        return False, []
    parsed = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            return False, []
        if not isinstance(value, dict):
            return False, []
        parsed.append(value)
    return True, parsed


def inspect_json_events(events: list[dict]) -> dict[str, int | bool]:
    command_started = 0
    command_completed = 0
    command_with_output = 0
    file_changes = 0
    file_changes_with_patch = 0
    verus_calls = 0
    verus_results = 0
    visible_reasoning = 0
    usage = 0
    thinking_tokens = 0
    item_types: Counter[str] = Counter()

    for event in events:
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage += 1
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", ""))
        item_types[item_type] += 1
        status = event.get("type")
        if item_type == "command_execution":
            command = str(item.get("command", ""))
            output = str(item.get("aggregated_output", ""))
            if status == "item.started":
                command_started += 1
            if status == "item.completed":
                command_completed += 1
                if output:
                    command_with_output += 1
            if VERUS_COMMAND_RE.search(command):
                verus_calls += status == "item.completed"
                if status == "item.completed" and (
                    VERUS_RESULT_RE.search(output) or item.get("exit_code") is not None
                ):
                    verus_results += 1
        elif item_type == "file_change" and status == "item.completed":
            file_changes += 1
            if any(key in item for key in ("patch", "diff", "content", "old_text", "new_text")):
                file_changes_with_patch += 1
        elif item_type in {"agent_message", "reasoning", "thinking"}:
            visible_reasoning += 1

        serialized = json.dumps(item, ensure_ascii=False)
        thinking_tokens += bool(THINKING_TOKEN_RE.search(serialized))

    return {
        "tool_calls": command_started,
        "tool_completed": command_completed,
        "tool_result_payload": command_with_output,
        "edit_events": file_changes,
        "inline_edit_payload": file_changes_with_patch,
        "collapsed_outputs": 0,
        "verus_calls": verus_calls,
        "verus_result_payload": verus_results,
        "visible_reasoning": visible_reasoning,
        "usage": usage,
        "thinking_token_accounting": thinking_tokens,
        "json_item_types": dict(item_types),
    }


def inspect_text(text: str) -> dict[str, int | bool]:
    composition = text_metrics(text)
    edits = ui_edit_boxes(text)
    return {
        "tool_calls": composition["tool_call_payload_lines"],
        "tool_completed": 0,
        "tool_result_payload": composition["tool_result_payload_lines"],
        "edit_events": edits["counted_edit_events"],
        "inline_edit_payload": composition["code_changed_logical_lines"],
        "collapsed_outputs": len(TEXT_COLLAPSED_RE.findall(text)),
        "verus_calls": composition["verifier_call_payload_lines"],
        "verus_result_payload": len(VERUS_RESULT_RE.findall(text)),
        "visible_reasoning": composition["narration_payload_lines"],
        "usage": composition["usage_lines"],
        "thinking_token_accounting": len(THINKING_TOKEN_RE.findall(text)),
        "json_item_types": {},
    }


def infer_format(text: str) -> tuple[str, dict, list[dict]]:
    is_jsonl, events = classify_jsonl(text)
    if is_jsonl:
        return "jsonl_events", inspect_json_events(events), events
    if text.lstrip().startswith(("●", "✓", "✗")):
        return "rendered_ui", inspect_text(text), []
    return "plain_or_mixed", inspect_text(text), []


def detects_self_log_redirection(
    text: str, events: list[dict], log_name: str
) -> bool:
    target = re.compile(rf">\s*(?:[^\s]*/)?{re.escape(log_name)}(?:\s|$)")
    if events:
        for event in events:
            item = event.get("item")
            if (
                isinstance(item, dict)
                and item.get("type") == "command_execution"
                and target.search(str(item.get("command", "")))
            ):
                return True
        return False

    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.match(r"^\s*\$\s+", line):
            continue
        command_block = "\n".join(lines[index : index + 4])
        if target.search(command_block):
            return True
    return False


def summarize(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    grouped: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row[key]) for key in keys)].append(row)

    output = []
    boolean_fields = (
        "has_tool_calls",
        "has_tool_result_payload",
        "has_edit_events",
        "has_inline_edit_payload",
        "has_collapsed_outputs",
        "has_verus_calls",
        "has_verus_result_payload",
        "has_visible_reasoning",
        "has_usage",
        "has_thinking_token_accounting",
        "has_self_log_redirection",
        "has_secret_like_material",
        "source_exists",
        "verified_exists",
    )
    for group, items in sorted(grouped.items()):
        result = {key: value for key, value in zip(keys, group)}
        result["logs"] = len(items)
        sizes = [item["size_bytes"] for item in items]
        result["median_bytes"] = int(statistics.median(sizes))
        result["mean_bytes"] = round(statistics.mean(sizes), 1)
        for field in boolean_fields:
            count = sum(bool(item[field]) for item in items)
            result[field] = count
            result[f"{field}_pct"] = round(100 * count / len(items), 2)
        output.append(result)
    return output


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest_rows = [
        json.loads(line)
        for line in args.manifest.read_text().splitlines()
        if line.strip()
    ]
    rows = []
    format_counts: Counter[str] = Counter()
    json_item_types: Counter[str] = Counter()

    for manifest in manifest_rows:
        log_path = args.corpus_root / manifest["relative_log_path"]
        text = log_path.read_text(errors="replace")
        log_format, features, events = infer_format(text)
        format_counts[log_format] += 1
        json_item_types.update(features.pop("json_item_types"))
        source_path = log_path.with_suffix(".rs")
        verified_path = log_path.with_name(f"{log_path.stem}_verified.rs")
        self_log_redirection = detects_self_log_redirection(
            text, events, log_path.name
        )
        row = {
            "relative_log_path": manifest["relative_log_path"],
            "directory_group": manifest["directory_group"],
            "result_dir": manifest["result_dir"],
            "model": manifest["model"],
            "variant": manifest["variant"],
            "split": manifest["split"],
            "format": log_format,
            "size_bytes": log_path.stat().st_size,
            **features,
            "has_tool_calls": features["tool_calls"] > 0,
            "has_tool_result_payload": features["tool_result_payload"] > 0,
            "has_edit_events": features["edit_events"] > 0,
            "has_inline_edit_payload": features["inline_edit_payload"] > 0,
            "has_collapsed_outputs": features["collapsed_outputs"] > 0,
            "has_verus_calls": features["verus_calls"] > 0,
            "has_verus_result_payload": features["verus_result_payload"] > 0,
            "has_visible_reasoning": features["visible_reasoning"] > 0,
            "has_usage": features["usage"] > 0,
            "has_thinking_token_accounting": features["thinking_token_accounting"] > 0,
            "has_self_log_redirection": self_log_redirection,
            "has_secret_like_material": bool(SECRET_LIKE_RE.search(text)),
            "source_exists": source_path.exists(),
            "verified_exists": verified_path.exists(),
        }
        rows.append(row)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "per_log_features.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    by_model_format = summarize(rows, ("model", "format"))
    by_directory = summarize(rows, ("directory_group",))
    by_result_dir = summarize(rows, ("directory_group", "result_dir", "model", "format"))
    write_csv(args.out_dir / "by_model_format.csv", by_model_format)
    write_csv(args.out_dir / "by_directory.csv", by_directory)
    write_csv(args.out_dir / "by_result_dir.csv", by_result_dir)

    summary = {
        "scope": "claude_sonnet_gpt5/verified-*/*/*.log",
        "logs": len(rows),
        "format_counts": dict(format_counts),
        "json_item_types": dict(json_item_types),
        "notes": {
            "tool_result_payload": "Any captured/summarized result marker; not necessarily complete.",
            "inline_edit_payload": "Some inline diff/patch evidence; not proof that every edit byte is retained.",
            "verus_result_payload": "Explicit Verus result/error payload, not narrative success alone.",
            "thinking_token_accounting": "Explicit thinking/reasoning token field only.",
        },
    }
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    )


if __name__ == "__main__":
    main()
