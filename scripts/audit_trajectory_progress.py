#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean, median
from typing import Any

from verus_self_evolve.trajectory_progress import (
    METRIC_NAME,
    normalize_code_lines,
    patch_f1_scores,
    verifier_state,
)


METRICS = (
    "whole_file_similarity",
    "relative_edit_progress",
    "patch_recall",
    "patch_f1",
    "verifier_tier",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _event_item(event: dict[str, Any]) -> dict[str, Any]:
    return event.get("data", {}).get("raw_codex_event", {}).get("item", {})


def _edit_cost(left: list[str], right: list[str]) -> int:
    return sum(
        max(left_end - left_start, right_end - right_start)
        for tag, left_start, left_end, right_start, right_end in SequenceMatcher(
            None, left, right, autojunk=False
        ).get_opcodes()
        if tag != "equal"
    )


def _hindsight_scores(
    baseline: str,
    candidate: str,
    reference: str,
) -> dict[str, float]:
    patch = patch_f1_scores(baseline, candidate, reference)
    baseline_lines = normalize_code_lines(baseline)
    candidate_lines = normalize_code_lines(candidate)
    reference_lines = normalize_code_lines(reference)
    denominator = _edit_cost(baseline_lines, reference_lines)
    return {
        "whole_file_similarity": SequenceMatcher(
            None, candidate_lines, reference_lines, autojunk=False
        ).ratio(),
        "relative_edit_progress": 1.0
        - _edit_cost(candidate_lines, reference_lines) / denominator,
        "patch_recall": float(patch["patch_recall"]),
        "patch_f1": float(patch["patch_f1"]),
    }


def _rankdata(values: list[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[index]]:
            end += 1
        rank = (index + end - 1) / 2.0
        for position in ordered[index:end]:
            ranks[position] = rank
        index = end
    return ranks


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2:
        return None
    left_mean = mean(left)
    right_mean = mean(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right)
    )
    left_ss = sum((value - left_mean) ** 2 for value in left)
    right_ss = sum((value - right_mean) ** 2 for value in right)
    if left_ss == 0 or right_ss == 0:
        return None
    return numerator / math.sqrt(left_ss * right_ss)


def _spearman(left: list[float], right: list[float]) -> float | None:
    return _pearson(_rankdata(left), _rankdata(right))


def _auc(rows: list[tuple[bool, float]]) -> float | None:
    positive = [score for label, score in rows if label]
    negative = [score for label, score in rows if not label]
    if not positive or not negative:
        return None
    wins = sum(
        1.0 if positive_score > negative_score else 0.5 if positive_score == negative_score else 0.0
        for positive_score in positive
        for negative_score in negative
    )
    return wins / (len(positive) * len(negative))


def _load_run(prediction_dir: Path) -> dict[str, Any] | None:
    paths = {
        "result": prediction_dir / "result.json",
        "events": prediction_dir / "agent_events.jsonl",
        "input": prediction_dir / "workspace/input.rs",
        "terminal": prediction_dir / "workspace/candidate.rs",
    }
    if not all(path.is_file() for path in paths.values()):
        return None
    result = json.loads(paths["result"].read_text(encoding="utf-8"))
    baseline = paths["input"].read_text(encoding="utf-8", errors="replace")
    terminal = paths["terminal"].read_text(encoding="utf-8", errors="replace")
    snapshots: dict[str, str] = {}
    for snapshot in (prediction_dir / "snapshots").glob("*-candidate.rs"):
        snapshots.setdefault(
            _sha256(snapshot),
            snapshot.read_text(encoding="utf-8", errors="replace"),
        )
    checkpoints = []
    seen_hashes: set[str] = set()
    for event in _load_jsonl(paths["events"]):
        if event.get("actor") != "verus" or event.get("type") != "verifier":
            continue
        digest = event.get("candidate_sha256")
        if not isinstance(digest, str) or digest not in snapshots or digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        output = str(_event_item(event).get("aggregated_output") or "")
        checkpoints.append(
            {
                "event_index": event.get("event_index"),
                "candidate_sha256": digest,
                "source": snapshots[digest],
                "verifier_output": output,
                "verifier": verifier_state(output),
            }
        )
    terminal_hash = _sha256(paths["terminal"])
    if terminal_hash not in seen_hashes:
        validation_output = str(
            ((result.get("validation") or {}).get("verus") or {}).get("stdout") or ""
        )
        checkpoints.append(
            {
                "event_index": None,
                "candidate_sha256": terminal_hash,
                "source": terminal,
                "verifier_output": validation_output,
                "verifier": verifier_state(validation_output),
            }
        )
    if not checkpoints:
        return None
    validation = result.get("validation") or {}
    solved = bool(
        result.get("status") == "SOLVED"
        and ((validation.get("verus") or {}).get("passed"))
    )
    return {
        "task_id": str(result.get("id") or prediction_dir.name),
        "task_type": result.get("task_type"),
        "step": prediction_dir.parents[2].name,
        "solved": solved,
        "baseline": baseline,
        "terminal": terminal,
        "terminal_hash": terminal_hash,
        "checkpoints": checkpoints,
    }


def _score_successful_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for run in runs:
        if not run["solved"]:
            continue
        checkpoint_count = len(run["checkpoints"])
        if checkpoint_count < 2 or run["baseline"] == run["terminal"]:
            continue
        for ordinal, checkpoint in enumerate(run["checkpoints"]):
            scores = _hindsight_scores(
                run["baseline"], checkpoint["source"], run["terminal"]
            )
            rows.append(
                {
                    "task_id": run["task_id"],
                    "task_type": run["task_type"],
                    "step": run["step"],
                    "checkpoint_ordinal": ordinal + 1,
                    "checkpoint_count": checkpoint_count,
                    "event_index": checkpoint["event_index"],
                    "candidate_sha256": checkpoint["candidate_sha256"],
                    "verifier_tier": checkpoint["verifier"]["tier_rank"] / 2.0,
                    "verifier_tier_name": checkpoint["verifier"]["tier"],
                    **scores,
                }
            )
    return rows


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    trajectories = defaultdict(list)
    for row in rows:
        trajectories[(row["step"], row["task_id"])].append(row)
    result = {}
    for metric in METRICS:
        correlations = []
        ranges = []
        terminal_unique_max = 0
        for trajectory in trajectories.values():
            trajectory.sort(key=lambda row: row["checkpoint_ordinal"])
            values = [float(row[metric]) for row in trajectory]
            target = [index / (len(values) - 1) for index in range(len(values))]
            correlation = _spearman(values, target)
            if correlation is not None:
                correlations.append(correlation)
            ranges.append(max(values) - min(values))
            terminal_unique_max += values[-1] > max(values[:-1])
        result[metric] = {
            "macro_spearman_vs_checkpoint_order": mean(correlations),
            "median_dynamic_range": median(ranges),
            "terminal_unique_max_fraction": terminal_unique_max / len(trajectories),
            "trajectory_count": len(trajectories),
        }
    return result


def _cross_final_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_task = defaultdict(list)
    for run in runs:
        if run["solved"] and len(run["checkpoints"]) >= 2:
            by_task[run["task_id"]].append(run)
    correlations = defaultdict(list)
    distinct_pair_counts = Counter()
    for task_runs in by_task.values():
        for run in task_runs:
            own_scores = [
                _hindsight_scores(run["baseline"], row["source"], run["terminal"])
                for row in run["checkpoints"]
            ]
            for sibling in task_runs:
                if sibling["terminal_hash"] == run["terminal_hash"]:
                    continue
                cross_scores = [
                    _hindsight_scores(run["baseline"], row["source"], sibling["terminal"])
                    for row in run["checkpoints"]
                ]
                for metric in METRICS:
                    if metric == "verifier_tier":
                        continue
                    correlation = _spearman(
                        [row[metric] for row in own_scores],
                        [row[metric] for row in cross_scores],
                    )
                    if correlation is not None:
                        correlations[metric].append(correlation)
                        distinct_pair_counts[metric] += 1
    return {
        metric: {
            "pair_count": distinct_pair_counts[metric],
            "median_curve_spearman": median(values) if values else None,
        }
        for metric, values in correlations.items()
    }


def _pass_boundary_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    trajectories = defaultdict(list)
    for row in rows:
        trajectories[(row["step"], row["task_id"])].append(row)
    directions = {
        kind: {metric: Counter() for metric in METRICS}
        for kind in ("pass_to_fail", "fail_to_pass")
    }
    for trajectory in trajectories.values():
        trajectory.sort(key=lambda row: row["checkpoint_ordinal"])
        for left, right in zip(trajectory, trajectory[1:]):
            left_pass = left["verifier_tier_name"] == "verified"
            right_pass = right["verifier_tier_name"] == "verified"
            if left_pass == right_pass:
                continue
            kind = "pass_to_fail" if left_pass else "fail_to_pass"
            for metric in METRICS:
                delta = float(right[metric]) - float(left[metric])
                direction = "up" if delta > 1e-12 else "down" if delta < -1e-12 else "flat"
                directions[kind][metric][direction] += 1
    return {
        kind: {metric: dict(counts) for metric, counts in metric_counts.items()}
        for kind, metric_counts in directions.items()
    }


def _outcome_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_task = defaultdict(list)
    for run in runs:
        by_task[run["task_id"]].append(run)
    score_rows = {metric: [] for metric in METRICS if metric != "verifier_tier"}
    score_values = {
        metric: {True: [], False: []}
        for metric in METRICS
        if metric != "verifier_tier"
    }
    eligible = 0
    for task_runs in by_task.values():
        references = [run for run in task_runs if run["solved"]]
        for run in task_runs:
            sibling_references = [
                reference
                for reference in references
                if reference is not run
                and reference["terminal_hash"] != run["terminal_hash"]
            ]
            if not sibling_references:
                sibling_references = [reference for reference in references if reference is not run]
            if not sibling_references:
                continue
            eligible += 1
            for metric in score_rows:
                score = max(
                    _hindsight_scores(
                        run["baseline"], run["terminal"], reference["terminal"]
                    )[metric]
                    for reference in sibling_references
                )
                score_rows[metric].append((run["solved"], score))
                score_values[metric][run["solved"]].append(score)
    return {
        "eligible_leave_one_run_out_count": eligible,
        "metrics": {
            metric: {
                "auc": _auc(rows),
                "solved_median": median(score_values[metric][True]),
                "unsolved_median": median(score_values[metric][False]),
                "solved_n": len(score_values[metric][True]),
                "unsolved_n": len(score_values[metric][False]),
            }
            for metric, rows in score_rows.items()
            if score_values[metric][True] and score_values[metric][False]
        },
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "task_id",
        "task_type",
        "step",
        "checkpoint_ordinal",
        "checkpoint_count",
        "event_index",
        "candidate_sha256",
        "verifier_tier_name",
        "verifier_tier",
        "patch_f1",
        "patch_recall",
        "relative_edit_progress",
        "whole_file_similarity",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({column: row.get(column) for column in columns} for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    steps_root = args.steps_root.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir == steps_root or steps_root in output_dir.parents:
        raise ValueError("output directory must be outside the input run tree")
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite existing output: {output_dir}")

    runs = []
    for result_path in sorted(
        steps_root.glob("step_*/rollout/predictions/*/result.json")
    ):
        run = _load_run(result_path.parent)
        if run:
            runs.append(run)
    rows = _score_successful_runs(runs)
    summary = {
        "schema_version": "trajectory-progress-audit-v1",
        "selection_contract": "fixed80_train_rollouts_only",
        "raw_data_read_only": True,
        "selected_metric": {
            "name": METRIC_NAME,
            "ordering": "lexicographic(verifier_tier, patch_f1)",
            "hindsight_only": True,
        },
        "run_count": len(runs),
        "outcomes": dict(
            Counter("solved" if run["solved"] else "unsolved" for run in runs)
        ),
        "successful_trajectory_count": len(
            {(row["step"], row["task_id"]) for row in rows}
        ),
        "checkpoint_count": len(rows),
        "metric_summary": _metric_summary(rows),
        "metric_summary_by_task_type": {
            task_type: _metric_summary(
                [row for row in rows if row["task_type"] == task_type]
            )
            for task_type in sorted({row["task_type"] for row in rows})
        },
        "cross_final_summary": _cross_final_summary(runs),
        "pass_boundary_transitions": _pass_boundary_summary(rows),
        "leave_one_run_out_terminal_outcome": _outcome_summary(runs),
    }
    output_dir.mkdir(parents=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(output_dir / "checkpoint_metrics.csv", rows)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
