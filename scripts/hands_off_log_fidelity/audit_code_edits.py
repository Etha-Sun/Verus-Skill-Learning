#!/usr/bin/env python3
"""Measure how completely hands-off logs retain code edits."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path


EDIT_START_RE = re.compile(
    r"(?i)^[✓●✗]?\s*(Edit|Create|Write|str_replace_editor: create)\b"
)
PAREN_COUNTS_RE = re.compile(r"\((?:\+(\d+)(?:\s+-(\d+))?|-(\d+))\)")
SUMMARY_COUNTS_RE = re.compile(r"(?:\+(\d+)(?:\s+-(\d+))?|-(\d+))\s*$")
FAILED_EDIT_HEADER_RE = re.compile(r"(?mi)^✗\s*Edit\b")
BOX_ADD_RE = re.compile(r"^\s*│\s*\d+\s*\+\s")
BOX_DEL_RE = re.compile(r"^\s*│\s*\d+\s*-\s")
BOX_START_RE = re.compile(r"^\s*╭")
BOX_END_RE = re.compile(r"^\s*╰")
NEXT_EVENT_RE = re.compile(r"^[✓●✗]\s+")
DECORATION_RE = re.compile(r"[\s│╭╮╰╯─]+")


def normalize_for_search(text: str) -> str:
    return DECORATION_RE.sub("", text)


def meaningful(line: str) -> str | None:
    value = "".join(line.split())
    if len(value) < 12:
        return None
    if value.startswith("//"):
        return None
    return value


def changed_lines(before: str, after: str) -> tuple[set[str], set[str]]:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines, autojunk=False)
    added: set[str] = set()
    deleted: set[str] = set()
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            deleted.update(
                value
                for line in before_lines[i1:i2]
                if (value := meaningful(line)) is not None
            )
        if tag in {"replace", "insert"}:
            added.update(
                value
                for line in after_lines[j1:j2]
                if (value := meaningful(line)) is not None
            )
    return added, deleted


def literal_coverage(needles: set[str], normalized_log: str) -> tuple[int, int, float | None]:
    if not needles:
        return 0, 0, None
    found = sum(needle in normalized_log for needle in needles)
    return found, len(needles), found / len(needles)


def parsed_edit_headers(lines: list[str]) -> list[dict]:
    headers = []
    for index, line in enumerate(lines):
        start = EDIT_START_RE.match(line)
        if not start or line.lstrip().startswith("✗"):
            continue
        is_bullet_summary = line.lstrip().startswith("●")
        parts = [line.strip()]
        end = index
        joined = " ".join(parts)
        counts = PAREN_COUNTS_RE.search(joined)
        style = "diff_box"
        if not counts and is_bullet_summary:
            counts = SUMMARY_COUNTS_RE.search(joined)
            style = "summary_only"
        for following_index in range(index + 1, min(index + 9, len(lines))):
            if counts:
                break
            following = lines[following_index]
            if (
                BOX_END_RE.match(following)
                or BOX_ADD_RE.match(following)
                or BOX_DEL_RE.match(following)
                or NEXT_EVENT_RE.match(following)
                or BOX_START_RE.match(following)
            ):
                break
            if not following.startswith((" ", "\t")):
                break
            parts.append(following.strip())
            end = following_index
            joined = " ".join(parts)
            counts = PAREN_COUNTS_RE.search(joined)
            style = "diff_box"
            if not counts and is_bullet_summary:
                counts = SUMMARY_COUNTS_RE.search(joined)
                style = "summary_only"
        if not counts:
            continue
        headers.append(
            {
                "start": index,
                "end": end,
                "operation": start.group(1).lower(),
                "style": style,
                "declared_add": int(counts.group(1) or 0),
                "declared_del": int(counts.group(2) or counts.group(3) or 0),
            }
        )
    return headers


def ui_edit_boxes(text: str) -> dict[str, int | bool | None]:
    lines = text.splitlines()
    events = []
    for header in parsed_edit_headers(lines):
        operation = header["operation"]
        style = header["style"]
        declared_add = header["declared_add"]
        declared_del = header["declared_del"]
        shown_add = 0
        shown_del = 0
        saw_box = False
        if style == "diff_box":
            for following in lines[header["end"] + 1 :]:
                if BOX_END_RE.match(following):
                    saw_box = True
                    break
                if NEXT_EVENT_RE.match(following):
                    break
                if BOX_ADD_RE.match(following):
                    shown_add += 1
                if BOX_DEL_RE.match(following):
                    shown_del += 1
        events.append(
            {
                "operation": operation,
                "style": style,
                "declared": declared_add + declared_del,
                "shown": shown_add + shown_del,
                "exact": saw_box
                and declared_add == shown_add
                and declared_del == shown_del,
            }
        )
    output = {
        "failed_edit_events": len(FAILED_EDIT_HEADER_RE.findall(text)),
        "counted_edit_events": len(events),
        "diff_box_events": sum(event["style"] == "diff_box" for event in events),
        "exact_diff_box_events": sum(
            event["style"] == "diff_box" and event["exact"] for event in events
        ),
        "diff_box_edit_events": sum(
            event["style"] == "diff_box" and event["operation"] == "edit"
            for event in events
        ),
        "summary_only_events": sum(
            event["style"] == "summary_only" for event in events
        ),
        "summary_only_edit_events": sum(
            event["style"] == "summary_only" and event["operation"] == "edit"
            for event in events
        ),
        "summary_only_create_events": sum(
            event["style"] == "summary_only" and event["operation"] == "create"
            for event in events
        ),
        "declared_changed_lines": sum(event["declared"] for event in events),
        "shown_changed_lines": sum(event["shown"] for event in events),
        "exact_count_events": sum(event["exact"] for event in events),
        "all_counted_events_exact": bool(events) and all(event["exact"] for event in events),
    }
    for operation in ("edit", "create", "write", "str_replace_editor: create"):
        selected = [event for event in events if event["operation"] == operation]
        key = operation.replace("str_replace_editor: ", "str_replace_")
        output[f"{key}_events"] = len(selected)
        output[f"exact_{key}_events"] = sum(event["exact"] for event in selected)
    edit_events = [event for event in events if event["operation"] == "edit"]
    output["all_edit_events_exact"] = bool(edit_events) and all(
        event["exact"] for event in edit_events
    )
    return output


def aggregate(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row[key]) for key in keys)].append(row)
    output = []
    for key, items in sorted(groups.items()):
        paired = [row for row in items if row["paired"]]
        with_changed_lines = [
            row for row in paired if row["meaningful_added_lines"] > 0
        ]
        coverages = [
            row["added_line_coverage"]
            for row in with_changed_lines
            if row["added_line_coverage"] is not None
        ]
        result = {name: value for name, value in zip(keys, key)}
        result.update(
            {
                "logs": len(items),
                "paired": len(paired),
                "counted_edit_events": sum(row["counted_edit_events"] for row in items),
                "exact_count_events": sum(row["exact_count_events"] for row in items),
                "failed_edit_events": sum(row["failed_edit_events"] for row in items),
                "diff_box_events": sum(row["diff_box_events"] for row in items),
                "exact_diff_box_events": sum(
                    row["exact_diff_box_events"] for row in items
                ),
                "diff_box_edit_events": sum(
                    row["diff_box_edit_events"] for row in items
                ),
                "summary_only_events": sum(
                    row["summary_only_events"] for row in items
                ),
                "summary_only_edit_events": sum(
                    row["summary_only_edit_events"] for row in items
                ),
                "summary_only_create_events": sum(
                    row["summary_only_create_events"] for row in items
                ),
                "edit_events": sum(row["edit_events"] for row in items),
                "exact_edit_events": sum(row["exact_edit_events"] for row in items),
                "create_events": sum(row["create_events"] for row in items),
                "exact_create_events": sum(row["exact_create_events"] for row in items),
                "logs_all_edit_events_exact": sum(
                    row["all_edit_events_exact"] for row in items
                ),
                "logs_all_counted_events_exact": sum(
                    row["all_counted_events_exact"] for row in items
                ),
                "logs_with_changed_lines": len(with_changed_lines),
                "logs_added_coverage_100": sum(
                    row["added_line_coverage"] == 1.0 for row in with_changed_lines
                ),
                "logs_added_coverage_ge_95": sum(
                    row["added_line_coverage"] is not None
                    and row["added_line_coverage"] >= 0.95
                    for row in with_changed_lines
                ),
                "median_added_line_coverage": round(
                    statistics.median(coverages), 4
                )
                if coverages
                else None,
            }
        )
        output.append(result)
    return output


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
        log_path = args.corpus_root / feature["relative_log_path"]
        source_path = log_path.with_suffix(".rs")
        verified_path = log_path.with_name(f"{log_path.stem}_verified.rs")
        text = log_path.read_text(errors="replace")
        box_metrics = ui_edit_boxes(text)
        row = {
            "relative_log_path": feature["relative_log_path"],
            "directory_group": feature["directory_group"],
            "result_dir": feature["result_dir"],
            "model": feature["model"],
            "format": feature["format"],
            "paired": source_path.exists() and verified_path.exists(),
            **box_metrics,
            "meaningful_added_lines": 0,
            "added_lines_found": 0,
            "added_line_coverage": None,
            "meaningful_deleted_lines": 0,
            "deleted_lines_found": 0,
            "deleted_line_coverage": None,
        }
        if row["paired"]:
            before = source_path.read_text(errors="replace")
            after = verified_path.read_text(errors="replace")
            added, deleted = changed_lines(before, after)
            normalized_log = normalize_for_search(text)
            found, total, coverage = literal_coverage(added, normalized_log)
            row["meaningful_added_lines"] = total
            row["added_lines_found"] = found
            row["added_line_coverage"] = coverage
            found, total, coverage = literal_coverage(deleted, normalized_log)
            row["meaningful_deleted_lines"] = total
            row["deleted_lines_found"] = found
            row["deleted_line_coverage"] = coverage
        rows.append(row)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "per_log_code_edit.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "scope_logs": len(rows),
        "paired_logs": sum(row["paired"] for row in rows),
        "counted_edit_events": sum(row["counted_edit_events"] for row in rows),
        "exact_count_events": sum(row["exact_count_events"] for row in rows),
        "failed_edit_events": sum(row["failed_edit_events"] for row in rows),
        "diff_box_events": sum(row["diff_box_events"] for row in rows),
        "exact_diff_box_events": sum(row["exact_diff_box_events"] for row in rows),
        "diff_box_edit_events": sum(row["diff_box_edit_events"] for row in rows),
        "summary_only_events": sum(row["summary_only_events"] for row in rows),
        "summary_only_edit_events": sum(
            row["summary_only_edit_events"] for row in rows
        ),
        "summary_only_create_events": sum(
            row["summary_only_create_events"] for row in rows
        ),
        "edit_events": sum(row["edit_events"] for row in rows),
        "exact_edit_events": sum(row["exact_edit_events"] for row in rows),
        "create_events": sum(row["create_events"] for row in rows),
        "exact_create_events": sum(row["exact_create_events"] for row in rows),
        "logs_all_edit_events_exact": sum(
            row["all_edit_events_exact"] for row in rows
        ),
        "logs_all_counted_events_exact": sum(
            row["all_counted_events_exact"] for row in rows
        ),
        "by_model_format": aggregate(rows, ("model", "format")),
        "by_directory": aggregate(rows, ("directory_group",)),
    }
    (args.out_dir / "code_edit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    )


if __name__ == "__main__":
    main()
