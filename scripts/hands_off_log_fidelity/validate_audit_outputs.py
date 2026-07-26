#!/usr/bin/env python3
"""Regression checks for the hands-off log fidelity audit outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SAMPLE_EXPECTATIONS = {
    "verified-ironkv/results-sonnet45/delegation_map_v__impl1_to_set.log": {
        "physical_lines": 346,
        "diff_box_edit_events": 9,
        "exact_edit_events": 9,
        "create_events": 1,
        "code_changed_logical_lines": 100,
    },
    "verified-ironkv/results-sonnet4-20251026/host_impl_v__impl2__host_model_next_get_request.log": {
        "physical_lines": 1805,
        "diff_box_edit_events": 44,
        "exact_edit_events": 44,
        "failed_edit_events": 4,
        "create_events": 1,
        "code_changed_logical_lines": 612,
    },
    "verified-ironkv/results-gpt5-20251026/single_delivery_state_v__impl0__clone_up_to_view.log": {
        "physical_lines": 428,
        "diff_box_edit_events": 18,
        "exact_edit_events": 18,
        "create_events": 1,
        "code_changed_logical_lines": 97,
    },
    "verified-ironkv/results_nol-opus45/host_impl_v__impl2__process_received_packet_next.log": {
        "physical_lines": 2810,
        "summary_only_edit_events": 24,
        "summary_declared_changed_lines": 861,
        "failed_edit_events": 1,
        "code_changed_logical_lines": 0,
    },
    "verified-ironkv/results-opus45/marshal_v__impl4__serialized_size.log": {
        "physical_lines": 557,
        "diff_box_edit_events": 0,
        "summary_only_edit_events": 0,
        "code_changed_logical_lines": 0,
    },
    "verified-ironkv/results-o4/delegation_map_v__vec_erase.log": {
        "physical_lines": 80,
        "tool_call_payload_lines": 31,
        "tool_result_payload_lines": 891,
        "file_change_metadata_lines": 14,
        "verifier_result_payload_lines": 182,
    },
}


def load_rows(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    args = parser.parse_args()

    feature_rows = load_rows(args.results_dir / "per_log_features.jsonl")
    edit_rows = load_rows(args.results_dir / "per_log_code_edit.jsonl")
    line_rows = load_rows(args.results_dir / "per_log_line_composition.jsonl")
    assert len(feature_rows) == len(edit_rows) == len(line_rows) == 9383
    paths = [row["relative_log_path"] for row in feature_rows]
    assert paths == [row["relative_log_path"] for row in edit_rows]
    assert paths == [row["relative_log_path"] for row in line_rows]

    edits = {row["relative_log_path"]: row for row in edit_rows}
    lines = {row["relative_log_path"]: row for row in line_rows}
    for path, expectations in SAMPLE_EXPECTATIONS.items():
        combined = {**edits[path], **lines[path]}
        for key, expected in expectations.items():
            actual = combined[key]
            assert actual == expected, (path, key, expected, actual)

    shown = sum(row["shown_changed_lines"] for row in edit_rows)
    classified = sum(row["code_changed_logical_lines"] for row in line_rows)
    assert shown == classified == 1_833_283
    assert sum(row["has_tool_calls"] for row in feature_rows) == 8_447
    assert sum(row["has_tool_result_payload"] for row in feature_rows) == 8_402
    assert sum(row["has_edit_events"] for row in feature_rows) == 8_169
    assert sum(row["has_usage"] for row in feature_rows) == 9_268
    assert sum(row["has_thinking_token_accounting"] for row in feature_rows) == 0
    print("PASS: 6 sample logs and global cross-checks")


if __name__ == "__main__":
    main()
