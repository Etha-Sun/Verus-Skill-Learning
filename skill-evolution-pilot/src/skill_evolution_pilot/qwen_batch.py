from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path
from typing import Any

from .openrouter_adapter import DEFAULT_MODEL
from .qwen_runner import run_qwen_agentic_smoke
from .workspace import sha256_file


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def prepare_qwen_jobs(
    *,
    tasks_path: Path,
    out_root: Path,
    output_path: Path,
    meta_output_path: Path | None = None,
) -> list[dict[str, Any]]:
    if output_path.exists():
        raise ValueError(f"job file already exists: {output_path}")
    tasks = _read_jsonl(tasks_path)
    if len(tasks) != 4:
        raise ValueError(f"expected exactly four tasks, got {len(tasks)}")
    task_ids = [str(task["task_id"]) for task in tasks]
    if len(set(task_ids)) != 4:
        raise ValueError("task IDs must be unique")

    conditions: list[tuple[str, str | None, str | None]] = [("h0", None, None)]
    if meta_output_path is not None:
        meta = json.loads(meta_output_path.read_text(encoding="utf-8"))
        if meta.get("objective") != "small_model_solve_rate":
            raise ValueError("meta output is not for small_model_solve_rate")
        skills = meta.get("skills")
        if not isinstance(skills, list) or len(skills) != 3:
            raise ValueError("meta output must contain exactly three skills")
        conditions = []
        for skill in skills:
            conditions.append(
                (
                    str(skill["skill_id"]),
                    str(skill["content"]),
                    str(skill["profile"]),
                )
            )

    jobs: list[dict[str, Any]] = []
    skills_dir = out_root / "skills"
    for condition, skill_text, profile in conditions:
        skill_path: Path | None = None
        if skill_text is not None:
            skills_dir.mkdir(parents=True, exist_ok=True)
            skill_path = skills_dir / f"{condition}.md"
            if skill_path.exists():
                raise ValueError(f"skill file already exists: {skill_path}")
            skill_path.write_text(skill_text.rstrip() + "\n", encoding="utf-8")
        for task in tasks:
            source = Path(str(task["source"])).resolve()
            if sha256_file(source) != task["source_sha256"]:
                raise ValueError(f"source hash changed for {task['task_id']}")
            jobs.append(
                {
                    "task_id": task["task_id"],
                    "final_case": task.get("final_case"),
                    "condition": condition,
                    "profile": profile,
                    "source": str(source),
                    "source_sha256": task["source_sha256"],
                    "skill_file": str(skill_path) if skill_path else None,
                    "skill_sha256": sha256_file(skill_path) if skill_path else None,
                    "out_dir": str(out_root / "runs" / condition / task["task_id"]),
                }
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(job, ensure_ascii=False) + "\n" for job in jobs),
        encoding="utf-8",
    )
    return jobs


def _usage(run_dir: Path) -> dict[str, float]:
    totals = {
        "prompt_tokens": 0.0,
        "completion_tokens": 0.0,
        "reasoning_tokens": 0.0,
        "total_tokens": 0.0,
        "cost": 0.0,
    }
    provider = run_dir / "provider_io.jsonl"
    for row in _read_jsonl(provider):
        if row.get("direction") != "response":
            continue
        payload = row.get("payload")
        usage = payload.get("usage") if isinstance(payload, dict) else None
        if not isinstance(usage, dict):
            continue
        details = usage.get("completion_tokens_details")
        if not isinstance(details, dict):
            details = {}
        values = {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": usage.get("reasoning_tokens")
            or details.get("reasoning_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "cost": usage.get("cost"),
        }
        for name, value in values.items():
            if isinstance(value, (int, float)):
                totals[name] += float(value)
    return totals


def run_qwen_batch(
    *,
    jobs_path: Path,
    summary_path: Path,
    verus_bin: Path,
    lynette_bin: Path,
    model: str = DEFAULT_MODEL,
    max_workers: int = 4,
    max_iters: int = 10,
    max_tokens: int = 8192,
    transport_attempts: int = 2,
    provider_timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    if summary_path.exists():
        raise ValueError(f"summary already exists: {summary_path}")
    jobs = _read_jsonl(jobs_path)
    if not jobs:
        raise ValueError("no Qwen jobs")

    if transport_attempts < 1:
        raise ValueError("transport_attempts must be positive")

    def execute(job: dict[str, Any]) -> dict[str, Any]:
        skill_path = Path(job["skill_file"]) if job["skill_file"] else None
        errors = []
        base_out = Path(job["out_dir"])
        completed_result = base_out / "result.json"
        if completed_result.is_file():
            result = json.loads(completed_result.read_text(encoding="utf-8"))
            return {
                **job,
                "actual_out_dir": str(base_out),
                "transport_attempt": 0,
                "status": result["status"],
                "f3": result["fidelity"]["f3"],
                "request_count": result["request_count"],
                "wall_seconds": result["wall_seconds"],
                "usage": _usage(base_out),
                "error": None,
                "prior_transport_errors": [],
                "resumed_existing_result": True,
            }
        base_is_partial = base_out.exists() and any(base_out.iterdir())
        resume_start = 1
        if base_is_partial:
            while (
                base_out.parent / f"{base_out.name}-resume-{resume_start}"
            ).exists():
                resume_start += 1
        for attempt in range(1, transport_attempts + 1):
            if base_is_partial:
                run_dir = base_out.parent / (
                    f"{base_out.name}-resume-{resume_start + attempt - 1}"
                )
            else:
                run_dir = (
                    base_out
                    if attempt == 1
                    else base_out.parent / f"{base_out.name}-transport-retry-{attempt}"
                )
            try:
                result = run_qwen_agentic_smoke(
                    source=Path(job["source"]),
                    out_dir=run_dir,
                    verus_bin=verus_bin,
                    lynette_bin=lynette_bin,
                    model=model,
                    max_iters=max_iters,
                    max_tokens=max_tokens,
                    provider_timeout_seconds=provider_timeout_seconds,
                    skill_text=(
                        skill_path.read_text(encoding="utf-8") if skill_path else None
                    ),
                )
                return {
                    **job,
                    "actual_out_dir": str(run_dir),
                    "transport_attempt": attempt,
                    "status": result["status"],
                    "f3": result["fidelity"]["f3"],
                    "request_count": result["request_count"],
                    "wall_seconds": result["wall_seconds"],
                    "usage": _usage(run_dir),
                    "error": None,
                    "prior_transport_errors": errors,
                }
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
        return {
            **job,
            "actual_out_dir": None,
            "transport_attempt": transport_attempts,
            "status": "RUNNER_ERROR",
            "f3": False,
            "request_count": None,
            "wall_seconds": None,
            "usage": None,
            "error": errors[-1],
            "prior_transport_errors": errors[:-1],
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        rows = list(pool.map(execute, jobs))
    conditions: dict[str, dict[str, Any]] = {}
    for row in rows:
        bucket = conditions.setdefault(
            row["condition"],
            {"runs": 0, "solved": 0, "f3": 0, "requests": 0, "cost": 0.0},
        )
        bucket["runs"] += 1
        bucket["solved"] += int(row["status"] == "SOLVED")
        bucket["f3"] += int(row["f3"])
        if isinstance(row["request_count"], int):
            bucket["requests"] += row["request_count"]
        if isinstance(row["usage"], dict):
            bucket["cost"] += row["usage"]["cost"]
    summary = {
        "schema_version": "1",
        "model": model,
        "max_iters": max_iters,
        "max_tokens_per_request": max_tokens,
        "max_workers": max_workers,
        "transport_attempts": transport_attempts,
        "provider_timeout_seconds": provider_timeout_seconds,
        "jobs_path": str(jobs_path.resolve()),
        "conditions": conditions,
        "rows": rows,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary
