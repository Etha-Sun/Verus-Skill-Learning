#!/usr/bin/env python3
"""Run the frozen strict official IronKV held-out-15 paired evaluation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from verus_agent.experiments.ironkv_claude_to_deepseek_77_77 import (
    run_heldout20_paired_when_ready as base,
)


PROJECT_ROOT = base.PROJECT_ROOT
SELECTION_ROOT = (
    PROJECT_ROOT / "outputs/ironkv_strict_heldout15_official_v4_selection"
)
STRICT_TASKS = SELECTION_ROOT / "heldout15_tasks.jsonl"
STRICT_SELECTION = SELECTION_ROOT / "heldout15_selection.json"
QUALIFICATION_AUDIT = SELECTION_ROOT / "candidate_qualification_audit.json"
TRAINING_AUDIT = SELECTION_ROOT / "training77_strict_artifact_audit.json"
DEFAULT_OUTPUT_ROOT = (
    PROJECT_ROOT
    / "outputs/ironkv_deepseek_strict_heldout15_paired_raw_combined_v2_v1"
)
ORIGINAL_PREPARE_EXPERIMENT = base.prepare_experiment


def load_rows() -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in STRICT_TASKS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 15:
        raise ValueError(f"strict held-out manifest must contain 15 tasks, found {len(rows)}")
    forbidden = {"trajectory_path", "trajectory_sha256", "verified_path", "verified_sha256"}
    for row in rows:
        leaked = forbidden & set(row)
        if leaked:
            raise ValueError(f"strict held-out manifest leaks private fields: {leaked}")
    return rows


def select_frozen(
    rows: list[dict[str, Any]], count: int, _seed: int
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if count != 15:
        raise ValueError("the frozen strict evaluation requires --count 15")
    return rows, dict(sorted(Counter(row["module"] for row in rows).items()))


def validate_strict_selection(selected: list[dict[str, Any]]) -> None:
    selection = json.loads(STRICT_SELECTION.read_text(encoding="utf-8"))
    qualification = json.loads(QUALIFICATION_AUDIT.read_text(encoding="utf-8"))
    training = json.loads(TRAINING_AUDIT.read_text(encoding="utf-8"))
    if selection.get("status") != "PASS" or qualification.get("status") != "PASS":
        raise ValueError("strict selection or qualification audit is not PASS")
    if training.get("combined_v2_routing") != {
        "success": 53,
        "failure": 24,
        "unresolved": 0,
    }:
        raise ValueError("combined-v2 routing audit is inconsistent")
    if selection.get("train_task_id_overlap_count") != 0:
        raise ValueError("strict selection overlaps train77")
    if selection.get("selected_leakage_component_duplicate_count") != 0:
        raise ValueError("strict selection contains duplicate leakage components")
    if len({row["leakage_group_id"] for row in selected}) != len(selected):
        raise ValueError("runtime rows duplicate a leakage component")
    for row in selected:
        source = Path(row["source_path"])
        if row.get("official_label") != "TRUE":
            raise ValueError(f"non-TRUE strict row: {row['task_id']}")
        if not source.is_file() or base.sha256_file(source) != row["source_sha256"]:
            raise ValueError(f"strict source missing or changed: {row['task_id']}")


def prepare_strict_experiment(
    output_root: Path,
    selected: list[dict[str, Any]],
    quotas: dict[str, int],
    config: dict[str, Any],
    args: Any,
) -> Path:
    skill_dir = ORIGINAL_PREPARE_EXPERIMENT(
        output_root, selected, quotas, config, args
    )
    strict_selection = json.loads(STRICT_SELECTION.read_text(encoding="utf-8"))
    base.write_json(output_root / "heldout15_selection.json", strict_selection)
    manifest_path = output_root / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "experiment": "ironkv_deepseek_strict_heldout15_paired_raw_combined_v2_v1",
            "selection_policy": "strict official TRUE, nontrivial, Verus+Lynette qualified",
            "strict_selection_manifest": str(STRICT_SELECTION.resolve()),
            "strict_selection_manifest_sha256": base.sha256_file(STRICT_SELECTION),
            "qualification_audit": str(QUALIFICATION_AUDIT.resolve()),
            "qualification_audit_sha256": base.sha256_file(QUALIFICATION_AUDIT),
            "training_routing_audit": str(TRAINING_AUDIT.resolve()),
            "training_routing_audit_sha256": base.sha256_file(TRAINING_AUDIT),
            "train_task_id_overlap_count": 0,
            "selected_leakage_component_duplicate_count": 0,
            "heldout_source_policy": "current official VeruSAGE-Bench IR task files",
        }
    )
    base.write_json(manifest_path, manifest)
    return skill_dir


def main() -> int:
    base.HELDOUT_MANIFEST = STRICT_TASKS
    base.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
    base.DEFAULT_COUNT = 15
    base.load_rows = load_rows
    base.select_heldout = select_frozen
    base.validate_selection = validate_strict_selection
    base.prepare_experiment = prepare_strict_experiment
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
