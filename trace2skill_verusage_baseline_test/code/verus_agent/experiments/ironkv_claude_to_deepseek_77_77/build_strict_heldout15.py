#!/usr/bin/env python3
"""Build an offline-audited, non-trivial IronKV held-out-15 selection.

The existing 77/77 split remains frozen.  This script only filters its public
held-out half.  It does not expose held-out trajectories or verified solutions
to an evaluation agent and it does not make network requests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from verus_agent.experiments.ironkv_claude_to_deepseek_77_77 import build_split


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = Path(__file__).resolve().parent
SPLIT_ROOT = EXPERIMENT_ROOT / "split"
TRAIN_MANIFEST = SPLIT_ROOT / "train_trajectories.jsonl"
HELDOUT_MANIFEST = SPLIT_ROOT / "heldout_tasks.jsonl"
LEAKAGE_AUDIT = SPLIT_ROOT / "leakage_audit.json"
DATASET_DIR = Path(
    os.environ.get("IRONKV_DATASET_DIR", "UNCONFIGURED_IRONKV_DATASET_DIR")
)
OFFICIAL_RESULTS = DATASET_DIR.parent / "results-sonnet45.csv"
TRIVIAL_RESULTS = DATASET_DIR / "trivialresults"
OFFICIAL_TASKS = Path(
    os.environ.get("VERUSAGE_TASK_ROOT", "UNCONFIGURED_VERUSAGE_TASK_ROOT")
)
VERUS_BIN = Path(os.environ.get("VERUS_BIN", "UNCONFIGURED_VERUS_BIN"))
LYNETTE_BIN = Path(os.environ.get("LYNETTE_BIN", "UNCONFIGURED_LYNETTE_BIN"))
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "outputs/ironkv_strict_heldout15_official_v4_selection"
)
DEFAULT_SEED = 20260811
DEFAULT_COUNT = 15


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_official_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    with OFFICIAL_RESULTS.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle, skipinitialspace=True):
            if len(row) >= 2:
                labels[row[0].strip()] = row[1].strip()
    if len(labels) != 118:
        raise ValueError(f"expected 118 official IR labels, found {len(labels)}")
    return labels


def run_command(command: list[str], timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout or ""
        return {
            "command_without_secrets": command,
            "exit_code": completed.returncode,
            "passed": completed.returncode == 0,
            "output_tail": output[-4000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return {
            "command_without_secrets": command,
            "exit_code": None,
            "passed": False,
            "output_tail": output[-4000:],
            "timed_out": True,
        }


def official_task_path(task_id: str) -> Path:
    return OFFICIAL_TASKS / f"IR__{task_id}.rs"


def task_target(task_id: str) -> str:
    return task_id.split("__")[-1]


def normalized_source_similarity(left: Path, right: Path) -> float:
    return build_split.jaccard(
        build_split.shingles(left.read_text(encoding="utf-8", errors="replace"), 7),
        build_split.shingles(right.read_text(encoding="utf-8", errors="replace"), 7),
    )


def training_outcome_audit(
    train_rows: list[dict[str, Any]], labels: dict[str, str]
) -> dict[str, Any]:
    trivial_ids = {path.stem for path in TRIVIAL_RESULTS.glob("*.log")}
    rows: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for row in train_rows:
        task_id = row["task_id"]
        official = labels.get(task_id)
        if official == "TRUE":
            combined_v2_route = "success"
            category = "official_true_success"
        elif official is not None:
            combined_v2_route = "failure"
            category = "official_nontrue_failure"
        elif task_id in trivial_ids:
            combined_v2_route = "success"
            category = "trivial_success_outside_official_118"
        else:
            combined_v2_route = "unresolved"
            category = "missing_label"
        counts[category] += 1
        rows.append(
            {
                "task_id": task_id,
                "official_label": official or "NOT_IN_OFFICIAL_118",
                "combined_v2_route": combined_v2_route,
                "category": category,
            }
        )
    return {
        "status": "PASS_WITH_CONTAMINATION_WARNING"
        if counts["missing_label"] == 0
        else "FAIL",
        "train_count": len(train_rows),
        "counts": dict(sorted(counts.items())),
        "combined_v2_success_count": sum(
            row["combined_v2_route"] == "success" for row in rows
        ),
        "combined_v2_failure_count": sum(
            row["combined_v2_route"] == "failure" for row in rows
        ),
        "finding": (
            "combined_v2 correctly routed official FALSE/CHEAT trajectories to "
            "failure analysis, but its success side includes trivial tasks outside "
            "the official 118-task IR benchmark"
        ),
        "tasks": rows,
    }


def qualify_candidate(
    row: dict[str, Any],
    labels: dict[str, str],
    train_rows: list[dict[str, Any]],
    timeout: int,
) -> dict[str, Any]:
    task_id = row["task_id"]
    dataset_source = Path(row["source_path"])
    verified = DATASET_DIR / f"{task_id}_verified.rs"
    official_source = official_task_path(task_id)
    checks: dict[str, Any] = {
        "official_label_true": labels.get(task_id) == "TRUE",
        "public_heldout_source_unchanged": (
            dataset_source.is_file()
            and sha256_file(dataset_source) == row["source_sha256"]
        ),
        "official_task_exists": official_source.is_file(),
        "dataset_verified_exists": verified.is_file(),
    }
    record: dict[str, Any] = {
        "task_id": task_id,
        "module": row["module"],
        "official_label": labels.get(task_id, "NOT_IN_OFFICIAL_118"),
        "dataset_source_path": str(dataset_source),
        "official_source_path": str(official_source),
        "dataset_verified_path_used_for_offline_qualification_only": str(verified),
        "checks": checks,
    }
    if not all(checks.values()):
        record["eligible"] = False
        return record

    source_check = run_command([str(VERUS_BIN), str(official_source)], timeout)
    verified_check = run_command([str(VERUS_BIN), str(verified)], timeout)
    lynette_check = run_command(
        [str(LYNETTE_BIN), "compare", "-t", str(dataset_source), str(verified)],
        timeout,
    )
    checks.update(
        {
            "official_source_is_nontrivial_verus_failure": not source_check["passed"],
            "dataset_verified_solution_verus_passes": verified_check["passed"],
            "dataset_solution_strict_lynette_passes": lynette_check["passed"],
        }
    )

    train_official_sources = [
        official_task_path(train_row["task_id"])
        for train_row in train_rows
        if official_task_path(train_row["task_id"]).is_file()
    ]
    exact_sha_overlap = any(
        sha256_file(path) == sha256_file(official_source)
        for path in train_official_sources
    )
    max_similarity = 0.0
    max_similarity_task: str | None = None
    for train_row in train_rows:
        train_source = official_task_path(train_row["task_id"])
        if not train_source.is_file():
            continue
        similarity = normalized_source_similarity(official_source, train_source)
        if similarity > max_similarity:
            max_similarity = similarity
            max_similarity_task = train_row["task_id"]
    train_targets = {task_target(train_row["task_id"]) for train_row in train_rows}
    train_canonical_targets = {
        build_split.canonical_target(task_target(train_row["task_id"]))
        for train_row in train_rows
    }
    checks.update(
        {
            "no_exact_official_source_sha_overlap_with_train": not exact_sha_overlap,
            "no_exact_target_name_overlap_with_train": task_target(task_id)
            not in train_targets,
            "no_canonical_target_overlap_with_train": build_split.canonical_target(
                task_target(task_id)
            )
            not in train_canonical_targets,
            "current_official_source_similarity_below_0_80": max_similarity < 0.80,
        }
    )
    record.update(
        {
            "official_source_sha256": sha256_file(official_source),
            "dataset_source_sha256": sha256_file(dataset_source),
            "dataset_source_matches_current_official_source": (
                dataset_source.read_bytes() == official_source.read_bytes()
            ),
            "max_current_official_source_similarity_to_train": round(
                max_similarity, 6
            ),
            "most_similar_train_task": max_similarity_task,
            "verus_source_check": source_check,
            "verus_verified_check": verified_check,
            "lynette_check": lynette_check,
        }
    )
    record["eligible"] = all(checks.values())
    return record


def select_stratified(
    eligible: list[dict[str, Any]], count: int, seed: int
) -> list[dict[str, Any]]:
    # Keep at most one representative per frozen leakage component so that
    # encoding variants and near-duplicate sibling tasks are not counted as
    # independent evaluation evidence.
    representatives: list[dict[str, Any]] = []
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_group[row["leakage_group_id"]].append(row)
    for group_rows in by_group.values():
        group_rows.sort(
            key=lambda row: hashlib.sha256(
                f"{seed}:component:{row['task_id']}".encode("utf-8")
            ).hexdigest()
        )
        representatives.append(group_rows[0])
    if len(representatives) < count:
        raise ValueError(
            f"only {len(representatives)} independent strict candidates for "
            f"{count} slots"
        )
    by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in representatives:
        by_module[row["module"]].append(row)
    for rows in by_module.values():
        rows.sort(
            key=lambda row: hashlib.sha256(
                f"{seed}:{row['task_id']}".encode("utf-8")
            ).hexdigest()
        )
    selected: list[dict[str, Any]] = []
    modules = sorted(
        by_module,
        key=lambda module: (-len(by_module[module]), module),
    )
    for module in modules:
        if len(selected) == count:
            break
        selected.append(by_module[module].pop(0))
    while len(selected) < count:
        available = [module for module in modules if by_module[module]]
        module = max(available, key=lambda item: (len(by_module[item]), item))
        selected.append(by_module[module].pop(0))
    return sorted(selected, key=lambda row: row["task_id"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    for required in (
        TRAIN_MANIFEST,
        HELDOUT_MANIFEST,
        LEAKAGE_AUDIT,
        OFFICIAL_RESULTS,
        VERUS_BIN,
        LYNETTE_BIN,
    ):
        if not required.exists():
            raise FileNotFoundError(required)
    leakage = json.loads(LEAKAGE_AUDIT.read_text(encoding="utf-8"))
    if leakage.get("status") != "PASS":
        raise ValueError("frozen 77/77 leakage audit is not PASS")

    train_rows = load_jsonl(TRAIN_MANIFEST)
    heldout_rows = load_jsonl(HELDOUT_MANIFEST)
    labels = load_official_labels()
    if len(train_rows) != 77 or len(heldout_rows) != 77:
        raise ValueError("frozen split is not 77/77")
    train_ids = {row["task_id"] for row in train_rows}
    if train_ids & {row["task_id"] for row in heldout_rows}:
        raise ValueError("train/held-out task-id overlap")

    official_true_heldout = [
        row for row in heldout_rows if labels.get(row["task_id"]) == "TRUE"
    ]
    group_by_task = {
        task_id: group["group_id"]
        for group in leakage["groups"]
        for task_id in group["task_ids"]
    }
    qualifications = [
        qualify_candidate(row, labels, train_rows, args.timeout_seconds)
        for row in official_true_heldout
    ]
    for row in qualifications:
        row["leakage_group_id"] = group_by_task[row["task_id"]]
    eligible = [row for row in qualifications if row["eligible"]]
    selected = select_stratified(eligible, args.count, args.seed)

    output_dir.mkdir(parents=True)
    training_audit = training_outcome_audit(train_rows, labels)
    write_json(output_dir / "training77_outcome_audit.json", training_audit)
    write_json(
        output_dir / "candidate_qualification_audit.json",
        {
            "status": "PASS" if len(eligible) >= args.count else "FAIL",
            "official_true_heldout_count": len(official_true_heldout),
            "strict_eligible_count": len(eligible),
            "strict_independent_component_count": len(
                {row["leakage_group_id"] for row in eligible}
            ),
            "eligibility_rules": [
                "task is in the frozen held-out77 and absent from train77",
                "official 118-task IR result label is exactly TRUE",
                "current official benchmark source does not already pass Verus",
                "trajectory-associated verified solution passes local Verus",
                "trajectory-associated source/solution passes lynette compare -t",
                "no exact/canonical target or source-similarity leakage to train77",
                "at most one selected task per frozen leakage component",
            ],
            "verus_version": run_command([str(VERUS_BIN), "--version"], 30),
            "records": qualifications,
        },
    )

    public_rows: list[dict[str, Any]] = []
    for row in selected:
        source = Path(row["official_source_path"])
        public_rows.append(
            {
                "task_id": row["task_id"],
                "module": row["module"],
                "source_path": str(source),
                "source_sha256": sha256_file(source),
                "source_bytes": source.stat().st_size,
                "source_lines": build_split.line_count(source),
                "official_label": "TRUE",
                "leakage_group_id": row["leakage_group_id"],
            }
        )
    write_jsonl(output_dir / "heldout15_tasks.jsonl", public_rows)
    (output_dir / "tasks.tsv").write_text(
        "".join(
            f"{index:02d}\t{row['task_id']}\t{row['source_path']}\n"
            for index, row in enumerate(public_rows, start=1)
        ),
        encoding="utf-8",
    )
    write_json(
        output_dir / "heldout15_selection.json",
        {
            "status": "PASS",
            "selection_count": len(public_rows),
            "selection_seed": args.seed,
            "selection_method": (
                "strict qualification followed by deterministic module-stratified "
                "selection"
            ),
            "train_task_id_overlap_count": len(
                train_ids & {row["task_id"] for row in public_rows}
            ),
            "selected_leakage_component_duplicate_count": (
                len(public_rows)
                - len({row["leakage_group_id"] for row in public_rows})
            ),
            "heldout_trajectories_exposed_to_evaluation": False,
            "heldout_verified_solutions_exposed_to_evaluation": False,
            "source_policy": "current official VeruSAGE-Bench IR task files",
            "training_outcome_audit": "training77_outcome_audit.json",
            "qualification_audit": "candidate_qualification_audit.json",
            "tasks": public_rows,
        },
    )
    print(f"strict eligible: {len(eligible)}/{len(official_true_heldout)}")
    print(f"selected: {len(public_rows)}")
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
