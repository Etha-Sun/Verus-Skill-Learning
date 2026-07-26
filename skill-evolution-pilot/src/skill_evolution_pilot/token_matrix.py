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
    by_skill: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(
        list
    )
    for job in jobs:
        task_id = str(job["task_id"])
        if task_id not in task_ids:
            raise ValueError(f"unknown task in skill jobs: {task_id}")
        by_skill[str(job["skill_id"])].append(
            (job, build_run_ledger(Path(job["out_dir"])))
        )
    if len(by_skill) != 3:
        raise ValueError("expected exactly three skills")
    if any(
        {str(job["task_id"]) for job, _ in rows} != task_ids
        for rows in by_skill.values()
    ):
        raise ValueError("every skill must cover every frozen task")
    all_ledgers = list(h0.values()) + [
        ledger for rows in by_skill.values() for _, ledger in rows
    ]
    if not all(ledger["f3"] for ledger in all_ledgers):
        raise ValueError("all primary matrix runs must pass F3")

    baseline = aggregate_ledgers(h0.values())
    aggregates = []
    for skill_id, rows in sorted(by_skill.items()):
        aggregate = aggregate_ledgers(ledger for _, ledger in rows)
        aggregates.append(
            {
                "skill_id": skill_id,
                "skill_profile": rows[0][0]["skill_profile"],
                **aggregate,
                "delta_etts_vs_h0": (
                    None
                    if aggregate["expected_tokens_to_success_is_infinite"]
                    or baseline["expected_tokens_to_success_is_infinite"]
                    else aggregate["expected_primary_uncached_tokens_to_success"]
                    - baseline["expected_primary_uncached_tokens_to_success"]
                ),
            }
        )
    ranked = sorted(
        aggregates,
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
                        "success": ledger["success"],
                        "primary_uncached_tokens": ledger[
                            "primary_uncached_tokens"
                        ],
                    }
                    for skill_id, rows in sorted(by_skill.items())
                    for job, ledger in rows
                    if str(job["task_id"]) == task_id
                ],
            }
        )
    return {
        "schema_version": "1",
        "task_count": 4,
        "skill_count": 3,
        "run_count": 12,
        "all_f3": True,
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
