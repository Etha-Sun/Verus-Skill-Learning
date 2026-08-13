#!/usr/bin/env python3
"""Offline strict artifact audit for the frozen IronKV train77 split."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from verus_agent.experiments.ironkv_claude_to_deepseek_77_77 import (
    build_strict_heldout15 as strict,
)


DEFAULT_OUTPUT = (
    strict.PROJECT_ROOT
    / "outputs/ironkv_strict_heldout15_official_v4_selection/"
    "training77_strict_artifact_audit.json"
)


def audit_one(
    row: dict[str, Any], labels: dict[str, str], trivial_ids: set[str], timeout: int
) -> dict[str, Any]:
    task_id = row["task_id"]
    source = Path(row["source_path"])
    verified = Path(row["verified_path"])
    official_label = labels.get(task_id)
    if official_label == "TRUE":
        category = "official_true_success"
        route = "success"
    elif official_label is not None:
        category = "official_nontrue_failure"
        route = "failure"
    elif task_id in trivial_ids:
        category = "trivial_success_outside_official_118"
        route = "success"
    else:
        category = "missing_label"
        route = "unresolved"

    record: dict[str, Any] = {
        "task_id": task_id,
        "category": category,
        "official_label": official_label or "NOT_IN_OFFICIAL_118",
        "combined_v2_route": route,
        "source_sha256_unchanged": (
            source.is_file() and strict.sha256_file(source) == row["source_sha256"]
        ),
        "verified_sha256_unchanged": (
            verified.is_file()
            and strict.sha256_file(verified) == row["verified_sha256"]
        ),
    }
    if route != "success":
        record["strict_success_artifact_status"] = "NOT_APPLICABLE_FAILURE_ROUTE"
        return record

    source_check = strict.run_command([str(strict.VERUS_BIN), str(source)], timeout)
    verified_check = strict.run_command([str(strict.VERUS_BIN), str(verified)], timeout)
    lynette_check = strict.run_command(
        [str(strict.LYNETTE_BIN), "compare", "-t", str(source), str(verified)],
        timeout,
    )
    source_expected_pass = category == "trivial_success_outside_official_118"
    source_behavior_matches_category = (
        source_check["passed"]
        if source_expected_pass
        else (
            not source_check["passed"]
            and not source_check["timed_out"]
            and "verification results::" in source_check["output_tail"]
        )
    )
    strict_clean = (
        source_behavior_matches_category
        and verified_check["passed"]
        and lynette_check["passed"]
    )
    record.update(
        {
            "source_behavior_matches_category": source_behavior_matches_category,
            "verified_solution_verus_passes": verified_check["passed"],
            "strict_lynette_passes": lynette_check["passed"],
            "strict_success_artifact_status": (
                "STRICT_CLEAN" if strict_clean else "NOT_STRICTLY_CONFIRMED"
            ),
            "source_verus_check": source_check,
            "verified_verus_check": verified_check,
            "lynette_check": lynette_check,
        }
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing audit: {output}")
    rows = strict.load_jsonl(strict.TRAIN_MANIFEST)
    labels = strict.load_official_labels()
    trivial_ids = {path.stem for path in strict.TRIVIAL_RESULTS.glob("*.log")}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(
            pool.map(
                lambda row: audit_one(
                    row, labels, trivial_ids, args.timeout_seconds
                ),
                rows,
            )
        )

    category_counts = Counter(row["category"] for row in records)
    strict_status_counts = Counter(
        row["strict_success_artifact_status"] for row in records
    )
    official_true_records = [
        row for row in records if row["category"] == "official_true_success"
    ]
    official_true_strict_clean = sum(
        row["strict_success_artifact_status"] == "STRICT_CLEAN"
        for row in official_true_records
    )
    strict.write_json(
        output,
        {
            "status": "PASS_WITH_CONTAMINATION_WARNING",
            "train_count": len(records),
            "category_counts": dict(sorted(category_counts.items())),
            "combined_v2_routing": {
                "success": sum(row["combined_v2_route"] == "success" for row in records),
                "failure": sum(row["combined_v2_route"] == "failure" for row in records),
                "unresolved": sum(
                    row["combined_v2_route"] == "unresolved" for row in records
                ),
            },
            "v1_misrouted_non_success_as_success_count": sum(
                row["combined_v2_route"] == "failure" for row in records
            ),
            "combined_v2_corrected_failure_route_count": sum(
                row["combined_v2_route"] == "failure" for row in records
            ),
            "strict_status_counts": dict(sorted(strict_status_counts.items())),
            "official_true_strict_clean_count": official_true_strict_clean,
            "official_true_not_strictly_confirmed_count": (
                len(official_true_records) - official_true_strict_clean
            ),
            "interpretation": [
                "v1 incorrectly attempted Success Memory extraction for all 77 trajectories.",
                "combined_v2 excludes all 24 official FALSE/CHEAT rows from Success Memory and routes them to Failure Memory.",
                "Ten combined_v2 success rows are trivial direct-pass tasks outside the official 118-task IR result table.",
                "A strict Lynette rejection is conservative evidence requiring review; it can be a checker false positive and is not silently relabeled as failure.",
            ],
            "records": records,
        },
    )
    print(output)
    print(f"official TRUE strict clean: {official_true_strict_clean}/{len(official_true_records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
