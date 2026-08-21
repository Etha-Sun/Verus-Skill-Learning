from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PROFILE_ORDER = {"aggressive": 0, "conservative": 1, "structural": 2}
TASK_LABELS = {
    "stable_pass": "Direct",
    "stable_closest_failure": "Closest",
    "unstable": "Unstable",
    "hard_solved": "Hard",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _bool_text(value: Any) -> str:
    if value is None:
        return ""
    return "true" if bool(value) else "false"


def _number_text(value: Any) -> str:
    return "" if value is None else str(value)


def export_data(run_root: Path, output: Path) -> list[dict[str, str]]:
    summaries = [
        _load(
            run_root
            / "skill-evolution-pilot"
            / f"token-r{round_index}-matrix-20260726"
            / "token_matrix_summary.json"
        )
        for round_index in range(1, 7)
    ]
    first = summaries[0]
    task_rows = first["individual"]
    if len(task_rows) != 4:
        raise ValueError("expected exactly four frozen tasks")

    rows: list[dict[str, str]] = []
    h0_etts = float(first["h0"]["expected_primary_uncached_tokens_to_success"])
    for task_index, task in enumerate(task_rows):
        rows.append(
            {
                "row_order": "0",
                "round": "H0",
                "profile": "baseline",
                "skill_id": "no-skill",
                "task_order": str(task_index),
                "task_class": TASK_LABELS.get(
                    str(task["final_case"]), str(task["final_case"])
                ),
                "task_id": str(task["task_id"]),
                "h0_tokens": str(task["h0"]["primary_uncached_tokens"]),
                "tokens": str(task["h0"]["primary_uncached_tokens"]),
                "delta_pct": "0.0",
                "run_f3": "true",
                "success": _bool_text(task["h0"]["success"]),
                "run_status": "valid",
                "matrix_valid": "true",
                "solve_count": "4",
                "etts": str(h0_etts),
                "aggregate_delta_pct": "0.0",
            }
        )

    row_order = 1
    for round_index, summary in enumerate(summaries, start=1):
        aggregate_by_skill = {
            str(item["skill_id"]): item for item in summary["skill_aggregates"]
        }
        skills = sorted(
            aggregate_by_skill,
            key=lambda skill_id: PROFILE_ORDER[
                str(aggregate_by_skill[skill_id]["skill_profile"])
            ],
        )
        task_by_id = {
            str(task["task_id"]): task for task in summary["individual"]
        }
        for skill_id in skills:
            aggregate = aggregate_by_skill[skill_id]
            profile = str(aggregate["skill_profile"])
            task_items = []
            for task_index, first_task in enumerate(task_rows):
                task_id = str(first_task["task_id"])
                task = task_by_id[task_id]
                skill_result = next(
                    item
                    for item in task["skills"]
                    if str(item["skill_id"]) == skill_id
                )
                task_items.append(skill_result)
                tokens = skill_result.get("primary_uncached_tokens")
                success = skill_result.get("success")
                f3 = bool(
                    skill_result.get("f3")
                    if "f3" in skill_result
                    else summary.get("all_f3")
                )
                if tokens is None:
                    run_status = "no_usage"
                    delta_pct = None
                elif success is not True:
                    run_status = "failed"
                    delta_pct = (
                        (float(tokens) / float(task["h0"]["primary_uncached_tokens"]))
                        - 1.0
                    ) * 100.0
                elif not f3:
                    run_status = "invalid"
                    delta_pct = None
                else:
                    run_status = "valid"
                    delta_pct = (
                        (float(tokens) / float(task["h0"]["primary_uncached_tokens"]))
                        - 1.0
                    ) * 100.0
                rows.append(
                    {
                        "row_order": str(row_order),
                        "round": f"R{round_index}",
                        "profile": profile,
                        "skill_id": skill_id,
                        "task_order": str(task_index),
                        "task_class": TASK_LABELS.get(
                            str(task["final_case"]), str(task["final_case"])
                        ),
                        "task_id": task_id,
                        "h0_tokens": str(task["h0"]["primary_uncached_tokens"]),
                        "tokens": _number_text(tokens),
                        "delta_pct": _number_text(delta_pct),
                        "run_f3": _bool_text(skill_result.get("f3")),
                        "success": _bool_text(success),
                        "run_status": run_status,
                        "matrix_valid": "",
                        "solve_count": "",
                        "etts": "",
                        "aggregate_delta_pct": "",
                    }
                )

            inferred_valid = all(
                item.get("primary_uncached_tokens") is not None for item in task_items
            ) and bool(summary.get("all_f3"))
            matrix_valid = aggregate.get("matrix_valid")
            if matrix_valid is None:
                matrix_valid = inferred_valid
            solve_count = aggregate.get("success_count")
            if solve_count is None:
                solve_count = sum(item.get("success") is True for item in task_items)
            etts = aggregate.get("expected_primary_uncached_tokens_to_success")
            delta = None if etts is None else (float(etts) / h0_etts - 1.0) * 100.0
            for row in rows[-4:]:
                row["matrix_valid"] = _bool_text(matrix_valid)
                row["solve_count"] = str(solve_count)
                row["etts"] = _number_text(etts)
                row["aggregate_delta_pct"] = _number_text(delta)
            row_order += 1

    expected_rows = (1 + 6 * 3) * 4
    if len(rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} rows, found {len(rows)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = export_data(args.run_root.resolve(), args.output.resolve())
    print(json.dumps({"output": str(args.output), "row_count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
