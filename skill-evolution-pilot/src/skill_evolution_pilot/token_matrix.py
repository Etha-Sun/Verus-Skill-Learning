from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .token_ledger import aggregate_ledgers, build_run_ledger


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize_token_matrix(
    *,
    frozen_tasks_path: Path,
    skill_jobs_path: Path,
) -> dict[str, Any]:
    tasks = _load_jsonl(frozen_tasks_path)
    jobs = _load_jsonl(skill_jobs_path)
    if len(tasks) != 4:
        raise ValueError("expected exactly four frozen tasks")
    task_ids = {str(task["task_id"]) for task in tasks}
    if len(task_ids) != 4:
        raise ValueError("frozen task IDs must be unique")

    h0 = {
        str(task["task_id"]): build_run_ledger(Path(task["h0_run_dir"]))
        for task in tasks
    }
    by_skill: dict[
        str, list[tuple[dict[str, Any], dict[str, Any] | None, str | None]]
    ] = defaultdict(list)
    for job in jobs:
        task_id = str(job["task_id"])
        if task_id not in task_ids:
            raise ValueError(f"unknown task in skill jobs: {task_id}")
        try:
            ledger = build_run_ledger(Path(job["out_dir"]))
            error = None
        except ValueError as exc:
            ledger = None
            error = str(exc)
        by_skill[str(job["skill_id"])].append((job, ledger, error))
    if len(by_skill) != 3:
        raise ValueError("expected exactly three skills")
    if any(
        {str(job["task_id"]) for job, _, _ in rows} != task_ids
        for rows in by_skill.values()
    ):
        raise ValueError("every skill must cover every frozen task")
    if not all(ledger["f3"] for ledger in h0.values()):
        raise ValueError("all H0 matrix runs must pass F3")

    baseline = aggregate_ledgers(h0.values())
    aggregates = []
    for skill_id, rows in sorted(by_skill.items()):
        valid_ledgers = [
            ledger
            for _, ledger, _ in rows
            if ledger is not None and ledger["f3"]
        ]
        invalid_runs = [
            {
                "task_id": str(job["task_id"]),
                "error": error or "fidelity audit failed",
            }
            for job, ledger, error in rows
            if ledger is None or not ledger["f3"]
        ]
        matrix_valid = len(valid_ledgers) == len(tasks)
        aggregate = aggregate_ledgers(valid_ledgers) if matrix_valid else None
        aggregates.append(
            {
                "skill_id": skill_id,
                "skill_profile": rows[0][0]["skill_profile"],
                "matrix_valid": matrix_valid,
                "valid_run_count": len(valid_ledgers),
                "invalid_runs": invalid_runs,
                **(aggregate or {}),
                "delta_etts_vs_h0": (
                    None
                    if aggregate is None
                    or aggregate["expected_tokens_to_success_is_infinite"]
                    or baseline["expected_tokens_to_success_is_infinite"]
                    else aggregate["expected_primary_uncached_tokens_to_success"]
                    - baseline["expected_primary_uncached_tokens_to_success"]
                ),
            }
        )
    eligible = [row for row in aggregates if row["matrix_valid"]]
    if not eligible:
        raise ValueError("no skill has a complete F3-valid matrix")
    ranked = sorted(
        eligible,
        key=lambda row: (
            row["expected_tokens_to_success_is_infinite"],
            row["expected_primary_uncached_tokens_to_success"] or 0,
        ),
    )
    individual = []
    for task in tasks:
        task_id = str(task["task_id"])
        individual.append(
            {
                "task_id": task_id,
                "final_case": task["final_case"],
                "h0": {
                    "success": h0[task_id]["success"],
                    "primary_uncached_tokens": h0[task_id][
                        "primary_uncached_tokens"
                    ],
                },
                "skills": [
                    {
                        "skill_id": skill_id,
                        "skill_profile": job["skill_profile"],
                        "f3": bool(ledger and ledger["f3"]),
                        "success": None if ledger is None else ledger["success"],
                        "primary_uncached_tokens": (
                            None
                            if ledger is None
                            else ledger["primary_uncached_tokens"]
                        ),
                        "exclusion_reason": (
                            error
                            if ledger is None
                            else None
                            if ledger["f3"]
                            else "fidelity audit failed"
                        ),
                    }
                    for skill_id, rows in sorted(by_skill.items())
                    for job, ledger, error in rows
                    if str(job["task_id"]) == task_id
                ],
            }
        )
    return {
        "schema_version": "1",
        "task_count": 4,
        "skill_count": 3,
        "run_count": 12,
        "all_f3": all(row["matrix_valid"] for row in aggregates),
        "h0": baseline,
        "skill_aggregates": aggregates,
        "best_skill_id": ranked[0]["skill_id"],
        "worst_skill_id": ranked[-1]["skill_id"],
        "individual": individual,
    }


def write_token_matrix_summary(
    *,
    frozen_tasks_path: Path,
    skill_jobs_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ValueError(f"output already exists: {output_path}")
    result = summarize_token_matrix(
        frozen_tasks_path=frozen_tasks_path,
        skill_jobs_path=skill_jobs_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result
