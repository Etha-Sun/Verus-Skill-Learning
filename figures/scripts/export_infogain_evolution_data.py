from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


TASK_ORDER = {
    "seq_filter_contains_implies_seq_contains": 0,
    "marshal_v__impl2__lemma_serialize_injective": 1,
    "marshal_v__impl5__lemma_same_views_serialize_the_same": 2,
    "delegation_map_v__impl4__range_consistent_impl": 3,
}
PROFILE_ORDER = {"aggressive": 0, "conservative": 1, "structural": 2}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-summary", action="append", type=Path, required=True)
    parser.add_argument("--r3-trajectories", type=Path, required=True)
    parser.add_argument("--r3-partial-tokens", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if len(args.score_summary) != 2:
        raise ValueError("expected complete R1 and R2 --score-summary paths")

    task_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    for round_index, path in enumerate(args.score_summary, start=1):
        summary = json.loads(path.read_text(encoding="utf-8"))
        if summary["run_count"] != 12 or not summary["all_exact"]:
            raise ValueError(f"{path}: expected 12 exact rows")
        for row in summary["rows"]:
            if row["pre"]["truncated"] or row["post"]["truncated"]:
                raise ValueError(f"{path}: truncated score")
            task_rows.append(
                {
                    "round": f"R{round_index}",
                    "round_order": round_index,
                    "profile": row["skill_profile"],
                    "profile_order": PROFILE_ORDER[row["skill_profile"]],
                    "skill_id": row["skill_id"],
                    "task_id": row["task_id"],
                    "task_order": TASK_ORDER[row["task_id"]],
                    "solver_status": row["solver_status"],
                    "score_status": "complete",
                    "target_tokens": row["post"]["target_tokens"],
                    "pre_bits_per_target_token": row["pre"][
                        "ig_bits_per_target_token"
                    ],
                    "post_bits_per_target_token": row["post"][
                        "ig_bits_per_target_token"
                    ],
                    "pre_bits": row["pre"]["ig_bits"],
                    "post_bits": row["post"]["ig_bits"],
                }
            )
        for skill_id, values in summary["aggregates"].items():
            skill_rows = [
                row
                for row in summary["rows"]
                if row["skill_id"] == skill_id
            ]
            aggregate_rows.append(
                {
                    "round": f"R{round_index}",
                    "round_order": round_index,
                    "profile": skill_rows[0]["skill_profile"],
                    "profile_order": PROFILE_ORDER[
                        skill_rows[0]["skill_profile"]
                    ],
                    "skill_id": skill_id,
                    "score_status": "complete",
                    "scored_pairs": 4,
                    "mean_pre_bits_per_target_token": values[
                        "mean_ig_pre_bits_per_token"
                    ],
                    "mean_post_bits_per_target_token": values[
                        "mean_ig_post_bits_per_token"
                    ],
                    "mean_pre_bits": values["mean_ig_pre_bits"],
                    "mean_post_bits": values["mean_ig_post_bits"],
                }
            )

    r3 = json.loads(
        (args.r3_trajectories / "batch_summary.json").read_text(encoding="utf-8")
    )
    if r3["complete_count"] != 12 or r3["f3_count"] != 12:
        raise ValueError("R3 trajectory matrix is not 12/12 complete and F3")
    r3_by_skill: dict[str, dict[str, Any]] = {}
    for row in r3["results"]:
        r3_by_skill.setdefault(
            row["skill_id"],
            {
                "profile": row["skill_profile"],
                "solver_status": {},
            },
        )["solver_status"][row["task_id"]] = row["solver_status"]

    for skill_id, details in sorted(
        r3_by_skill.items(), key=lambda item: PROFILE_ORDER[item[1]["profile"]]
    ):
        for task_id in TASK_ORDER:
            task_rows.append(
                {
                    "round": "R3",
                    "round_order": 3,
                    "profile": details["profile"],
                    "profile_order": PROFILE_ORDER[details["profile"]],
                    "skill_id": skill_id,
                    "task_id": task_id,
                    "task_order": TASK_ORDER[task_id],
                    "solver_status": details["solver_status"][task_id],
                    "score_status": "pending",
                    "target_tokens": "",
                    "pre_bits_per_target_token": "",
                    "post_bits_per_target_token": "",
                    "pre_bits": "",
                    "post_bits": "",
                }
            )
        aggregate_rows.append(
            {
                "round": "R3",
                "round_order": 3,
                "profile": details["profile"],
                "profile_order": PROFILE_ORDER[details["profile"]],
                "skill_id": skill_id,
                "score_status": "pending",
                "scored_pairs": "",
                "mean_pre_bits_per_target_token": "",
                "mean_post_bits_per_target_token": "",
                "mean_pre_bits": "",
                "mean_post_bits": "",
            }
        )

    partial_files = list(args.r3_partial_tokens.glob("*.jsonl"))
    if len(partial_files) % 2:
        raise ValueError("R3 partial token file count is not paired")
    round_rows = [
        {
            "round": "R1",
            "round_order": 1,
            "status": "complete",
            "scored_pairs": 12,
            "expected_pairs": 12,
        },
        {
            "round": "R2",
            "round_order": 2,
            "status": "complete",
            "scored_pairs": 12,
            "expected_pairs": 12,
        },
        {
            "round": "R3",
            "round_order": 3,
            "status": "pending",
            "scored_pairs": len(partial_files) // 2,
            "expected_pairs": 12,
        },
    ]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.out_dir / "infogain_task_skill.csv", task_rows)
    _write_csv(args.out_dir / "infogain_skill_aggregate.csv", aggregate_rows)
    _write_csv(args.out_dir / "infogain_round_status.csv", round_rows)
    print(
        json.dumps(
            {
                "out_dir": str(args.out_dir),
                "task_rows": len(task_rows),
                "aggregate_rows": len(aggregate_rows),
                "r3_partial_pairs_excluded": len(partial_files) // 2,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
