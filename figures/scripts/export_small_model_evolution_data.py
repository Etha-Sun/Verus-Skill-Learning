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
    "impl_u__wrapped_token__impl1__lemma_interps_match_aux1": 3,
}
TASK_CLASS = {
    "seq_filter_contains_implies_seq_contains": "Direct",
    "marshal_v__impl2__lemma_serialize_injective": "Closest",
    "marshal_v__impl5__lemma_same_views_serialize_the_same": "Unstable",
    "impl_u__wrapped_token__impl1__lemma_interps_match_aux1": "Hard",
}
PROFILE_ORDER = {"aggressive": 0, "conservative": 1, "structural": 2}


def _provider_usage(path: Path) -> dict[str, float]:
    totals = {
        "prompt_tokens": 0.0,
        "completion_tokens": 0.0,
        "reasoning_tokens": 0.0,
        "total_tokens": 0.0,
    }
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("direction") != "response":
            continue
        usage = record["payload"]["usage"]
        totals["prompt_tokens"] += float(usage["prompt_tokens"])
        totals["completion_tokens"] += float(usage["completion_tokens"])
        totals["total_tokens"] += float(usage["total_tokens"])
        totals["reasoning_tokens"] += float(
            usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        )
    return totals


def _h0_row(task_id: str, run_dir: Path) -> dict[str, Any]:
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    usage = _provider_usage(run_dir / "provider_io.jsonl")
    return {
        "task_id": task_id,
        "final_case": {
            0: "stable_pass",
            1: "stable_closest_failure",
            2: "unstable",
            3: "current_codex_failure",
        }[TASK_ORDER[task_id]],
        "condition": "h0",
        "profile": "baseline",
        "status": result["status"],
        "f3": result["fidelity"]["valid_f3_event_stream"],
        "request_count": result["request_count"],
        "usage": usage,
    }


def _condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = all(row["f3"] and row["usage"] is not None for row in rows)
    return {
        "matrix_valid": valid,
        "solve_count": sum(row["status"] == "SOLVED" for row in rows),
        "total_requests": (
            sum(int(row["request_count"]) for row in rows) if valid else None
        ),
        "total_tokens": (
            sum(float(row["usage"]["total_tokens"]) for row in rows)
            if valid
            else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0-dir", type=Path, required=True)
    parser.add_argument("--h0-hard-retry", type=Path, required=True)
    parser.add_argument("--round-dir", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if len(args.round_dir) != 3:
        raise ValueError("expected exactly three --round-dir arguments")

    h0_rows = []
    for task_id in TASK_ORDER:
        run_dir = args.h0_dir / "runs" / "h0" / task_id
        if task_id == "impl_u__wrapped_token__impl1__lemma_interps_match_aux1":
            run_dir = args.h0_hard_retry
        h0_rows.append(_h0_row(task_id, run_dir))

    all_conditions: list[tuple[str, list[dict[str, Any]]]] = [("H0", h0_rows)]
    for round_index, round_dir in enumerate(args.round_dir, start=1):
        summary = json.loads(
            (round_dir / "summary.json").read_text(encoding="utf-8")
        )
        if len(summary["rows"]) != 12:
            raise ValueError(f"{round_dir}: expected 12 rows")
        by_condition: dict[str, list[dict[str, Any]]] = {}
        for row in summary["rows"]:
            by_condition.setdefault(row["condition"], []).append(row)
        ordered = sorted(
            by_condition.values(),
            key=lambda rows: PROFILE_ORDER[rows[0]["profile"]],
        )
        for rows in ordered:
            all_conditions.append((f"R{round_index}", rows))

    baseline = _condition_summary(h0_rows)
    if baseline != {
        "matrix_valid": True,
        "solve_count": 2,
        "total_requests": 29,
        "total_tokens": 312656.0,
    }:
        raise ValueError(f"unexpected H0 reconstruction: {baseline}")

    output_rows = []
    for condition_order, (round_name, rows) in enumerate(all_conditions):
        aggregate = _condition_summary(rows)
        profile = rows[0]["profile"]
        skill_id = rows[0]["condition"]
        for row in sorted(rows, key=lambda item: TASK_ORDER[item["task_id"]]):
            usage = row["usage"]
            total_tokens = float(usage["total_tokens"]) if usage else None
            output_rows.append(
                {
                    "condition_order": condition_order,
                    "round": round_name,
                    "profile": profile,
                    "skill_id": skill_id,
                    "task_order": TASK_ORDER[row["task_id"]],
                    "task_class": TASK_CLASS[row["task_id"]],
                    "task_id": row["task_id"],
                    "status": row["status"],
                    "f3": str(bool(row["f3"])).lower(),
                    "request_count": row["request_count"],
                    "total_tokens": total_tokens,
                    "prompt_tokens": (
                        float(usage["prompt_tokens"]) if usage else None
                    ),
                    "completion_tokens": (
                        float(usage["completion_tokens"]) if usage else None
                    ),
                    "reasoning_tokens": (
                        float(usage["reasoning_tokens"]) if usage else None
                    ),
                    "matrix_valid": str(aggregate["matrix_valid"]).lower(),
                    "solve_count": aggregate["solve_count"],
                    "total_requests": aggregate["total_requests"],
                    "aggregate_total_tokens": aggregate["total_tokens"],
                    "aggregate_delta_pct": (
                        100
                        * (aggregate["total_tokens"] - baseline["total_tokens"])
                        / baseline["total_tokens"]
                        if aggregate["total_tokens"] is not None
                        else None
                    ),
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "rows": len(output_rows),
                "conditions": len(all_conditions),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
