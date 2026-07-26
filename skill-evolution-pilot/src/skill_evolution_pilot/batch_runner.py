from __future__ import annotations

import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .codex_runner import run_codex_smoke
from .workspace import sha256_file


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"non-object JSONL row: {path}")
                rows.append(value)
    return rows


def prepare_h0_jobs(
    *,
    baseline_jobs_path: Path,
    out_root: Path,
    output_path: Path,
    run_suffix: str,
) -> list[dict[str, Any]]:
    if output_path.exists():
        raise ValueError(f"output already exists: {output_path}")
    baseline_jobs = _load_jsonl(baseline_jobs_path)
    by_case: dict[str, dict[str, Any]] = {}
    for row in baseline_jobs:
        final_case = row.get("final_case")
        if final_case and final_case not in by_case:
            by_case[str(final_case)] = row
    expected = {"stable_pass", "stable_closest_failure", "unstable"}
    if set(by_case) != expected:
        raise ValueError(f"expected exactly the three frozen cases, found {set(by_case)}")
    jobs = []
    for final_case in ("stable_pass", "stable_closest_failure", "unstable"):
        source_row = by_case[final_case]
        run_id = f"h0-{final_case}-{run_suffix}"
        jobs.append(
            {
                "job_id": run_id,
                "final_case": final_case,
                "task_id": source_row.get("task_id"),
                "source": source_row["source_path"],
                "source_sha256": source_row["source_sha256"],
                "out_dir": str(out_root / run_id),
                "condition": "h0",
                "status": "PENDING",
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in jobs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return jobs


def prepare_skill_jobs(
    *,
    task_jobs_path: Path,
    meta_output_path: Path,
    out_root: Path,
    output_path: Path,
    iteration: str,
    task_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    if output_path.exists():
        raise ValueError(f"output already exists: {output_path}")
    tasks = _load_jsonl(task_jobs_path)
    if task_ids is not None:
        tasks = [task for task in tasks if str(task.get("task_id")) in task_ids]
        found = {str(task["task_id"]) for task in tasks}
        if found != task_ids:
            raise ValueError(f"requested task IDs not found: {sorted(task_ids - found)}")
    if not tasks:
        raise ValueError("skill batch contains no tasks")
    meta = json.loads(meta_output_path.read_text(encoding="utf-8"))
    skills = meta.get("skills")
    if not isinstance(skills, list) or len(skills) != 3:
        raise ValueError("meta output must contain exactly three skills")
    profiles = {skill.get("profile") for skill in skills if isinstance(skill, dict)}
    if profiles != {"aggressive", "conservative", "structural"}:
        raise ValueError("skill profiles must be aggressive/conservative/structural")

    skills_root = out_root / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    skill_rows = []
    for skill in skills:
        skill_id = str(skill["skill_id"])
        if not skill_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in skill_id):
            raise ValueError(f"unsafe skill_id: {skill_id}")
        content = str(skill["content"]).rstrip() + "\n"
        path = skills_root / f"{skill_id}.md"
        if path.exists():
            raise ValueError(f"skill file already exists: {path}")
        path.write_text(content, encoding="utf-8")
        skill_rows.append(
            {
                "skill_id": skill_id,
                "profile": skill["profile"],
                "path": path,
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )

    jobs: list[dict[str, Any]] = []
    for task in tasks:
        for skill in skill_rows:
            task_id = str(task["task_id"])
            run_id = f"{iteration}-{skill['profile']}-{task_id}"
            jobs.append(
                {
                    "job_id": run_id,
                    "final_case": task.get("final_case"),
                    "task_id": task_id,
                    "source": task["source"],
                    "source_sha256": task["source_sha256"],
                    "out_dir": str(out_root / "runs" / run_id),
                    "condition": f"skill:{skill['skill_id']}",
                    "skill_id": skill["skill_id"],
                    "skill_profile": skill["profile"],
                    "skill_path": str(skill["path"]),
                    "skill_sha256": skill["sha256"],
                    "status": "PENDING",
                }
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in jobs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return jobs


def freeze_four_task_set(
    *,
    three_h0_jobs_path: Path,
    fourth_task_id: str,
    fourth_source: Path,
    fourth_run_dir: Path,
    output_path: Path,
    require_fourth_unsolved: bool = True,
) -> list[dict[str, Any]]:
    if output_path.exists():
        raise ValueError(f"output already exists: {output_path}")
    tasks = _load_jsonl(three_h0_jobs_path)
    if len(tasks) != 3:
        raise ValueError("expected exactly three existing H0 tasks")
    result_path = fourth_run_dir / "result.json"
    manifest_path = fourth_run_dir / "run_manifest.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not result.get("fidelity", {}).get("f3"):
        raise ValueError("fourth-task screen did not pass F3")
    if require_fourth_unsolved and result.get("status") != "UNSOLVED":
        raise ValueError("fourth task was solved under H0 and cannot be frozen")
    fourth_source = fourth_source.resolve()
    source_sha = sha256_file(fourth_source)
    if source_sha != manifest.get("source_sha256"):
        raise ValueError("fourth source hash differs from screened source")
    frozen = [
        {
            "task_id": task["task_id"],
            "final_case": task["final_case"],
            "source": task["source"],
            "source_sha256": task["source_sha256"],
            "h0_run_dir": task["out_dir"],
        }
        for task in tasks
    ]
    frozen.append(
        {
            "task_id": fourth_task_id,
            "final_case": (
                "current_codex_failure"
                if result.get("status") == "UNSOLVED"
                else "hard_solved"
            ),
            "source": str(fourth_source),
            "source_sha256": source_sha,
            "h0_run_dir": str(fourth_run_dir.resolve()),
            "screen_result_sha256": sha256_file(result_path),
            "screen_status": result.get("status"),
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in frozen:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return frozen


def run_batch(
    *,
    jobs_path: Path,
    summary_path: Path,
    codex_bin: Path,
    verus_bin: Path,
    lynette_bin: Path,
    max_workers: int,
    timeout_seconds: int,
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "high",
    reasoning_summary: str = "detailed",
) -> dict[str, Any]:
    if max_workers < 1:
        raise ValueError("max_workers must be positive")
    if summary_path.exists():
        raise ValueError(f"summary already exists: {summary_path}")
    jobs = _load_jsonl(jobs_path)
    if not jobs:
        raise ValueError("batch contains no jobs")
    started_at = _now()

    def execute(job: dict[str, Any]) -> dict[str, Any]:
        try:
            skill_text = None
            if job.get("skill_path"):
                skill_path = Path(job["skill_path"])
                skill_text = skill_path.read_text(encoding="utf-8")
                observed = hashlib.sha256(skill_text.encode("utf-8")).hexdigest()
                if observed != job.get("skill_sha256"):
                    raise ValueError(f"skill hash mismatch: {skill_path}")
            result = run_codex_smoke(
                source=Path(job["source"]),
                out_dir=Path(job["out_dir"]),
                codex_bin=codex_bin,
                verus_bin=verus_bin,
                lynette_bin=lynette_bin,
                model=model,
                reasoning_effort=reasoning_effort,
                reasoning_summary=reasoning_summary,
                show_raw_agent_reasoning=True,
                timeout_seconds=timeout_seconds,
                skill_text=skill_text,
            )
            return {
                "job_id": job["job_id"],
                "final_case": job.get("final_case"),
                "task_id": job.get("task_id"),
                "condition": job.get("condition"),
                "skill_id": job.get("skill_id"),
                "skill_profile": job.get("skill_profile"),
                "status": "COMPLETE",
                "solver_status": result["status"],
                "f3": result["fidelity"]["f3"],
                "result_path": str(Path(job["out_dir"]) / "result.json"),
                "error_type": None,
                "error": None,
            }
        except Exception as exc:
            return {
                "job_id": job.get("job_id"),
                "final_case": job.get("final_case"),
                "task_id": job.get("task_id"),
                "status": "ERROR",
                "solver_status": None,
                "f3": False,
                "result_path": None,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(jobs))) as executor:
        futures = {executor.submit(execute, job): job for job in jobs}
        for future in as_completed(futures):
            results.append(future.result())
    order = {job["job_id"]: index for index, job in enumerate(jobs)}
    results.sort(key=lambda row: order[str(row["job_id"])])
    summary = {
        "schema_version": "1",
        "started_at": started_at,
        "finished_at": _now(),
        "model": model,
        "reasoning_effort": reasoning_effort,
        "reasoning_summary": reasoning_summary,
        "show_raw_agent_reasoning": True,
        "max_workers": min(max_workers, len(jobs)),
        "job_count": len(jobs),
        "complete_count": sum(row["status"] == "COMPLETE" for row in results),
        "f3_count": sum(bool(row["f3"]) for row in results),
        "solved_count": sum(row["solver_status"] == "SOLVED" for row in results),
        "results": results,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary
