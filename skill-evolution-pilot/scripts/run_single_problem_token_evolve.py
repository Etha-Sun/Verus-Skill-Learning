from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from skill_evolution_pilot.batch_runner import prepare_skill_jobs, run_batch
from skill_evolution_pilot.cli import model_free_smoke
from skill_evolution_pilot.codex_adapter import normalize_codex_jsonl
from skill_evolution_pilot.codex_runner import build_command
from skill_evolution_pilot.meta_agent import run_token_meta_agent, validate_meta_output
from skill_evolution_pilot.token_ledger import build_run_ledger
from skill_evolution_pilot.workspace import sha256_file


LOGGER = logging.getLogger("single-problem-token-evolve")
PROFILES = ("aggressive", "conservative", "structural")
REQUIRED_RUN_FILES = (
    "codex_events.raw.jsonl",
    "agent_events.jsonl",
    "fidelity_audit.json",
    "result.json",
    "run_manifest.json",
    "validation.json",
    "visibility_manifest.json",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object row {line_number}: {path}")
            rows.append(value)
    return rows


def run_capture(command: list[str], *, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "returncode": result.returncode,
            "timed_out": False,
            "wall_seconds": time.monotonic() - started,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": None,
            "timed_out": True,
            "wall_seconds": time.monotonic() - started,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def validate_r6_inputs(
    *,
    jobs_path: Path,
    meta_output_path: Path,
    task_id: str,
    codex_bin: Path,
    verus_bin: Path,
    lynette_bin: Path,
) -> dict[str, Any]:
    target_jobs = [row for row in read_jsonl(jobs_path) if row.get("task_id") == task_id]
    if len(target_jobs) != 3:
        raise ValueError(f"expected three R6 target jobs, found {len(target_jobs)}")
    if {row.get("skill_profile") for row in target_jobs} != set(PROFILES):
        raise ValueError("R6 target jobs do not have the three required profiles")
    sources = {str(row["source"]) for row in target_jobs}
    source_hashes = {str(row["source_sha256"]) for row in target_jobs}
    if len(sources) != 1 or len(source_hashes) != 1:
        raise ValueError("R6 target jobs disagree on source identity")
    source = Path(next(iter(sources))).resolve()
    source_sha = next(iter(source_hashes))
    if sha256_file(source) != source_sha:
        raise ValueError("target source hash differs from R6 jobs")

    meta = read_json(meta_output_path)
    errors = validate_meta_output(meta, "token_cost")
    if errors:
        raise ValueError(f"R6 meta output is invalid: {errors}")
    meta_skills = {str(skill["skill_id"]): skill for skill in meta["skills"]}
    resolved_skills = []
    for job in target_jobs:
        skill_path = Path(str(job["skill_path"])).resolve()
        observed_sha = sha256_file(skill_path)
        expected_sha = str(job["skill_sha256"])
        if observed_sha != expected_sha:
            raise ValueError(f"R6 skill hash mismatch: {skill_path}")
        skill_id = str(job["skill_id"])
        meta_skill = meta_skills.get(skill_id)
        if meta_skill is None:
            raise ValueError(f"R6 skill is missing from meta output: {skill_id}")
        meta_sha = hashlib.sha256(
            (str(meta_skill["content"]).rstrip() + "\n").encode("utf-8")
        ).hexdigest()
        if meta_sha != expected_sha:
            raise ValueError(f"R6 meta content differs from skill file: {skill_id}")
        resolved_skills.append(
            {
                "skill_id": skill_id,
                "profile": str(job["skill_profile"]),
                "path": str(skill_path),
                "sha256": observed_sha,
            }
        )

    representative = target_jobs[0]
    r6_manifest = read_json(Path(str(representative["out_dir"])) / "run_manifest.json")
    tool_paths = {
        "codex": codex_bin.resolve(),
        "verus": verus_bin.resolve(),
        "lynette": lynette_bin.resolve(),
    }
    tool_hashes = {name: sha256_file(path) for name, path in tool_paths.items()}
    for name, observed in tool_hashes.items():
        expected = str(r6_manifest["tools"][name]["sha256"])
        if observed != expected:
            raise ValueError(f"{name} hash differs from R6 manifest")

    return {
        "task_id": task_id,
        "source": str(source),
        "source_sha256": source_sha,
        "final_case": str(representative.get("final_case")),
        "r6_jobs_path": str(jobs_path.resolve()),
        "r6_jobs_sha256": sha256_file(jobs_path),
        "r6_meta_output_path": str(meta_output_path.resolve()),
        "r6_meta_output_sha256": sha256_file(meta_output_path),
        "r6_model_contract": {
            key: r6_manifest[key]
            for key in (
                "model",
                "reasoning_effort",
                "reasoning_summary",
                "model_supports_reasoning_summaries",
                "hide_agent_reasoning",
                "show_raw_agent_reasoning",
                "timeout_seconds",
                "prompt_sha256",
            )
        },
        "tools": {
            name: {"path": str(path), "sha256": tool_hashes[name]}
            for name, path in tool_paths.items()
        },
        "seed_skills": sorted(resolved_skills, key=lambda row: PROFILES.index(row["profile"])),
    }


def codex_transport_preflight(
    *,
    out_dir: Path,
    codex_bin: Path,
    model: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=False)
    workspace = out_dir / "workspace"
    workspace.mkdir()
    prompt = "Reply with exactly READY and nothing else."
    prompt_path = out_dir / "prompt.txt"
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    last_message = out_dir / "last_message.txt"
    raw_path = out_dir / "codex_events.raw.jsonl"
    normalized_path = out_dir / "agent_events.jsonl"
    stderr_path = out_dir / "codex_stderr.log"
    command = build_command(
        codex_bin=codex_bin,
        workspace=workspace,
        last_message=last_message,
        model=model,
        reasoning_effort=reasoning_effort,
        reasoning_summary="detailed",
        show_raw_agent_reasoning=True,
    )
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=workspace,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    raw_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    normalized = normalize_codex_jsonl(
        raw_path=raw_path,
        normalized_path=normalized_path,
        run_id="codex-transport-preflight",
        candidate_path=None,
    )
    raw_rows = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    usage_events = [row["usage"] for row in raw_rows if isinstance(row.get("usage"), dict)]
    ready = last_message.is_file() and last_message.read_text(encoding="utf-8").strip() == "READY"
    summary = {
        "returncode": result.returncode,
        "wall_seconds": time.monotonic() - started,
        "ready": ready,
        "terminal_usage_event_count": len(usage_events),
        "usage": usage_events[0] if len(usage_events) == 1 else None,
        "normalized": normalized,
        "raw_log_uncompressed": True,
        "reasoning_summary_requested": "detailed",
        "hidden_chain_of_thought_claimed": False,
    }
    summary["passed"] = bool(result.returncode == 0 and ready and len(usage_events) == 1)
    write_json(out_dir / "summary.json", summary)
    return summary


def run_preflight(
    *,
    out_root: Path,
    contract: dict[str, Any],
    codex_bin: Path,
    verus_bin: Path,
    lynette_bin: Path,
    model: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    preflight = out_root / "preflight"
    preflight.mkdir()
    source = Path(str(contract["source"]))
    source_sha_before = sha256_file(source)
    verus = run_capture([str(verus_bin.resolve()), str(source)], timeout=120)
    write_json(preflight / "verus_source.json", verus)
    lynette = run_capture(
        [
            str(lynette_bin.resolve()),
            "compare",
            "-t",
            str(source),
            str(source),
        ],
        timeout=120,
    )
    write_json(preflight / "lynette_identity.json", lynette)
    model_free = model_free_smoke(preflight / "model-free-logging")
    transport = codex_transport_preflight(
        out_dir=preflight / "codex-transport",
        codex_bin=codex_bin,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    source_sha_after = sha256_file(source)
    source_expected_failure = bool(
        not verus["timed_out"]
        and verus["returncode"] not in (None, 0)
        and "verification results::" in str(verus["stdout"])
        and "errors" in str(verus["stdout"])
    )
    summary = {
        "created_at": now(),
        "output_collision_check": "passed",
        "source_sha256_expected": contract["source_sha256"],
        "source_sha256_before": source_sha_before,
        "source_sha256_after": source_sha_after,
        "source_hash_passed": (
            source_sha_before == contract["source_sha256"] == source_sha_after
        ),
        "verus_source_expected_failure_passed": source_expected_failure,
        "lynette_identity_passed": bool(
            not lynette["timed_out"] and lynette["returncode"] == 0
        ),
        "codex_transport_passed": transport["passed"],
        "logging_contract_passed": bool(model_free["valid"]),
        "gpu_required": False,
        "reference_proof_visible": False,
    }
    summary["passed"] = all(
        bool(summary[key])
        for key in (
            "source_hash_passed",
            "verus_source_expected_failure_passed",
            "lynette_identity_passed",
            "codex_transport_passed",
            "logging_contract_passed",
        )
    )
    write_json(preflight / "preflight_summary.json", summary)
    return summary


def completed_tool_calls(run_dir: Path) -> int | None:
    raw_path = run_dir / "codex_events.raw.jsonl"
    if not raw_path.is_file():
        return None
    count = 0
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        item = row.get("item")
        if (
            row.get("type") == "item.completed"
            and isinstance(item, dict)
            and item.get("type") == "command_execution"
        ):
            count += 1
    return count


def build_attempt_record(job: dict[str, Any]) -> dict[str, Any]:
    run_dir = Path(str(job["out_dir"]))
    result = read_json(run_dir / "result.json") if (run_dir / "result.json").is_file() else {}
    missing_files = [name for name in REQUIRED_RUN_FILES if not (run_dir / name).is_file()]
    ledger = None
    ledger_error = None
    try:
        ledger = build_run_ledger(run_dir)
        write_json(run_dir / "token_ledger.json", ledger)
    except Exception as exc:
        ledger_error = f"{type(exc).__name__}: {exc}"
        write_json(run_dir / "token_ledger_error.json", {"error": ledger_error})
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    record = {
        "job_id": job.get("job_id"),
        "task_id": job.get("task_id"),
        "condition": job.get("condition"),
        "skill_id": job.get("skill_id"),
        "skill_profile": job.get("skill_profile"),
        "skill_path": job.get("skill_path"),
        "run_dir": str(run_dir),
        "required_artifacts_complete": not missing_files,
        "missing_artifacts": missing_files,
        "terminal_usage_complete": ledger is not None,
        "ledger_error": ledger_error,
        "status": result.get("status"),
        "timed_out": bool(result.get("timed_out")),
        "f3": bool(result.get("fidelity", {}).get("f3")),
        "input_unchanged": bool(validation.get("input_unchanged")),
        "verus_passed": bool(validation.get("verus", {}).get("passed")),
        "lynette_passed": bool(validation.get("lynette", {}).get("passed")),
        "tool_call_count": completed_tool_calls(run_dir),
        "wall_seconds": result.get("wall_seconds"),
        "ledger": ledger,
    }
    record["invalid"] = bool(
        missing_files
        or ledger is None
        or not record["f3"]
        or not record["input_unchanged"]
    )
    return record


def summarize_jobs(
    *,
    jobs_path: Path,
    output_path: Path,
    h0_etts: float | None,
) -> dict[str, Any]:
    jobs = read_jsonl(jobs_path)
    attempts = [build_attempt_record(job) for job in jobs]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attempts:
        grouped[str(row["condition"])].append(row)
    conditions = []
    for condition, rows in grouped.items():
        ledgers = [row["ledger"] for row in rows if row["ledger"] is not None]
        usage_complete = len(ledgers) == len(rows)
        successes = sum(bool(row["ledger"]["success"]) for row in rows if row["ledger"])
        total_primary = (
            sum(int(row["ledger"]["primary_uncached_tokens"]) for row in rows)
            if usage_complete
            else None
        )
        infinite = usage_complete and successes == 0
        etts = (
            None
            if not usage_complete or successes == 0
            else float(total_primary) / successes
        )
        primary_values = (
            [int(row["ledger"]["primary_uncached_tokens"]) for row in rows]
            if usage_complete
            else []
        )
        decomposition = {}
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "uncached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
        ):
            if usage_complete and all(row["ledger"].get(key) is not None for row in rows):
                decomposition[key] = sum(int(row["ledger"][key]) for row in rows)
            else:
                decomposition[key] = None
        all_f3 = all(bool(row["f3"]) for row in rows)
        all_input_unchanged = all(bool(row["input_unchanged"]) for row in rows)
        all_artifacts_complete = all(bool(row["required_artifacts_complete"]) for row in rows)
        claim_admissible = bool(
            usage_complete and all_f3 and all_input_unchanged and all_artifacts_complete
        )
        skill_id = rows[0].get("skill_id")
        condition_summary = {
            "condition": condition,
            "skill_id": skill_id,
            "skill_profile": rows[0].get("skill_profile"),
            "skill_path": rows[0].get("skill_path"),
            "attempt_count": len(rows),
            "success_count": successes,
            "solve_rate": successes / len(rows),
            "terminal_usage_complete_count": len(ledgers),
            "all_terminal_usage_complete": usage_complete,
            "all_f3": all_f3,
            "all_input_unchanged": all_input_unchanged,
            "all_required_artifacts_complete": all_artifacts_complete,
            "claim_admissible": claim_admissible,
            "verifier_safe_all": successes == len(rows),
            "total_primary_uncached_tokens": total_primary,
            "expected_primary_uncached_tokens_to_success": etts,
            "expected_tokens_to_success_is_infinite": infinite,
            "relative_delta_vs_h0": (
                None
                if etts is None or h0_etts is None
                else (etts - h0_etts) / h0_etts
            ),
            "token_decomposition": decomposition,
            "primary_uncached_token_distribution": (
                {
                    "median": statistics.median(primary_values),
                    "mean": statistics.fmean(primary_values),
                    "min": min(primary_values),
                    "max": max(primary_values),
                    "range": max(primary_values) - min(primary_values),
                }
                if primary_values
                else None
            ),
            "wall_seconds_total": sum(
                float(row["wall_seconds"]) for row in rows if row["wall_seconds"] is not None
            ),
            "tool_calls_total": sum(
                int(row["tool_call_count"]) for row in rows if row["tool_call_count"] is not None
            ),
            "invalid_count": sum(bool(row["invalid"]) for row in rows),
            "timeout_count": sum(bool(row["timed_out"]) for row in rows),
            "attempts": rows,
        }
        conditions.append(condition_summary)

    def rank_key(row: dict[str, Any]) -> tuple[bool, float]:
        etts = row["expected_primary_uncached_tokens_to_success"]
        return (etts is None, float("inf") if etts is None else float(etts))

    admissible = [
        row
        for row in conditions
        if row["claim_admissible"] and row["verifier_safe_all"]
    ]
    usage_complete_conditions = [
        row for row in conditions if row["all_terminal_usage_complete"]
    ]
    summary = {
        "schema_version": "1",
        "created_at": now(),
        "jobs_path": str(jobs_path),
        "attempt_count": len(attempts),
        "completed_result_count": sum(
            (Path(str(row["run_dir"])) / "result.json").is_file() for row in attempts
        ),
        "invalid_count": sum(bool(row["invalid"]) for row in attempts),
        "timeout_count": sum(bool(row["timed_out"]) for row in attempts),
        "conditions": conditions,
        "best_admissible_skill": (
            min(admissible, key=rank_key)["skill_id"] if admissible else None
        ),
        "worst_observed_skill": (
            max(
                usage_complete_conditions,
                key=lambda row: (
                    row["expected_tokens_to_success_is_infinite"],
                    float(row["expected_primary_uncached_tokens_to_success"] or 0),
                ),
            )["skill_id"]
            if usage_complete_conditions
            else None
        ),
    }
    write_json(output_path, summary)
    return summary


def one_condition(summary: dict[str, Any]) -> dict[str, Any]:
    conditions = summary["conditions"]
    if len(conditions) != 1:
        raise ValueError(f"expected one condition, found {len(conditions)}")
    return conditions[0]


def render_injectable_meta(meta_dir: Path) -> Path:
    raw_path = meta_dir / "meta_output.json"
    raw = read_json(raw_path)
    errors = validate_meta_output(raw, "token_cost")
    if errors:
        raise ValueError(f"meta output schema errors: {errors}")
    injectable = json.loads(json.dumps(raw))
    for skill in injectable["skills"]:
        original = str(skill["content"]).strip()
        skill["content"] = (
            "---\n"
            f"name: {skill['skill_id']}\n"
            f"description: {skill['title']}\n"
            "---\n\n"
            f"# {skill['title']}\n\n"
            "## Applicable state\n\n"
            f"{skill['applicability'].strip()}\n\n"
            "## Ordered policy\n\n"
            f"{original}\n\n"
            "## Stop/self-disable condition\n\n"
            f"{skill['negative_scope'].strip()} Stop using this skill when its "
            "applicability no longer holds; continue normal safe solving and never "
            "submit an unverified result.\n\n"
            "## Predicted token-saving mechanism\n\n"
            f"{skill['hypothesis'].strip()}\n\n"
            "## Known failure risk\n\n"
            f"{skill['negative_scope'].strip()}\n"
        )
    output = meta_dir / "meta_output.injectable.json"
    write_json(output, injectable)
    write_json(
        meta_dir / "injectable_render_manifest.json",
        {
            "source": str(raw_path),
            "source_sha256": sha256_file(raw_path),
            "output": str(output),
            "output_sha256": sha256_file(output),
            "transformation": (
                "deterministic standalone-skill rendering from meta-agent title, "
                "applicability, content, hypothesis, and negative_scope fields"
            ),
        },
    )
    return output


def make_task_jobs(path: Path, contract: dict[str, Any]) -> None:
    write_jsonl(
        path,
        [
            {
                "job_id": "task-template",
                "final_case": contract["final_case"],
                "task_id": contract["task_id"],
                "source": contract["source"],
                "source_sha256": contract["source_sha256"],
                "condition": "template",
                "status": "PENDING",
            }
        ],
    )


def make_h0_jobs(path: Path, out_root: Path, contract: dict[str, Any]) -> None:
    rows = []
    for index in range(1, 4):
        run_id = f"h0-fresh-{index:02d}"
        rows.append(
            {
                "job_id": run_id,
                "final_case": contract["final_case"],
                "task_id": contract["task_id"],
                "source": contract["source"],
                "source_sha256": contract["source_sha256"],
                "out_dir": str(out_root / "runs" / run_id),
                "condition": "h0",
                "status": "PENDING",
            }
        )
    write_jsonl(path, rows)


def run_solver_batch(
    *,
    jobs_path: Path,
    summary_path: Path,
    codex_bin: Path,
    verus_bin: Path,
    lynette_bin: Path,
    workers: int,
    timeout_seconds: int,
    model: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    LOGGER.info("starting solver batch: %s", jobs_path)
    return run_batch(
        jobs_path=jobs_path,
        summary_path=summary_path,
        codex_bin=codex_bin,
        verus_bin=verus_bin,
        lynette_bin=lynette_bin,
        max_workers=workers,
        timeout_seconds=timeout_seconds,
        model=model,
        reasoning_effort=reasoning_effort,
        reasoning_summary="detailed",
    )


def current_counts(out_root: Path) -> tuple[int, int, int]:
    result_paths = [
        *out_root.glob("h0/runs/*/result.json"),
        *out_root.glob("seed/runs/*/result.json"),
        *out_root.glob("round-*/runs/*/result.json"),
        *out_root.glob("final-confirmation/runs/*/result.json"),
    ]
    invalid = 0
    timeout = 0
    for path in result_paths:
        result = read_json(path)
        timeout += bool(result.get("timed_out"))
        raw_path = path.parent / "codex_events.raw.jsonl"
        usage_count = 0
        if raw_path.is_file():
            usage_count = sum(
                isinstance(json.loads(line).get("usage"), dict)
                for line in raw_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        invalid += bool(
            not result.get("fidelity", {}).get("f3")
            or not result.get("validation", {}).get("input_unchanged")
            or usage_count != 1
        )
    return len(result_paths), invalid, timeout


def write_status(
    *,
    out_root: Path,
    tmux_session: str,
    phase: str,
    round_index: int | None,
    h0_etts: float | None,
    best: dict[str, Any] | None,
    remaining_stage_count: int,
) -> None:
    completed, invalid, timeout = current_counts(out_root)
    status = {
        "updated_at": now(),
        "phase": phase,
        "round": round_index,
        "completed_trajectories": min(completed, 18),
        "total_trajectories": 18,
        "h0_etts": h0_etts,
        "best_skill": None if best is None else best.get("skill_id"),
        "best_skill_etts": (
            None
            if best is None
            else best.get("expected_primary_uncached_tokens_to_success")
        ),
        "best_relative_delta_vs_h0": (
            None if best is None else best.get("relative_delta_vs_h0")
        ),
        "invalid_count": invalid,
        "timeout_count": timeout,
        "tmux_session": tmux_session,
        "output_dir": str(out_root),
        "estimated_remaining_seconds_upper_bound": remaining_stage_count * 660,
    }
    write_json(out_root / "status.json", status)


def best_eligible(summaries: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = []
    for summary in summaries:
        for row in summary["conditions"]:
            if (
                row.get("skill_id")
                and row["attempt_count"] == 1
                and row["success_count"] == 1
                and row["claim_admissible"]
                and row["verifier_safe_all"]
                and row["expected_primary_uncached_tokens_to_success"] is not None
            ):
                eligible.append(row)
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda row: float(row["expected_primary_uncached_tokens_to_success"]),
    )


def ensure_source_unchanged(contract: dict[str, Any]) -> None:
    observed = sha256_file(Path(str(contract["source"])))
    if observed != contract["source_sha256"]:
        raise RuntimeError("immutable source hash changed during experiment")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--tmux-session", required=True)
    parser.add_argument("--r6-jobs", type=Path, required=True)
    parser.add_argument("--r6-meta-output", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--codex-bin", type=Path, required=True)
    parser.add_argument("--verus-bin", type=Path, required=True)
    parser.add_argument("--lynette-bin", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()

    out_root = args.out_root.resolve()
    if out_root.exists():
        raise ValueError(f"output collision: {out_root}")
    contract = validate_r6_inputs(
        jobs_path=args.r6_jobs,
        meta_output_path=args.r6_meta_output,
        task_id=args.task_id,
        codex_bin=args.codex_bin,
        verus_bin=args.verus_bin,
        lynette_bin=args.lynette_bin,
    )
    frozen = contract["r6_model_contract"]
    if (
        args.model != frozen["model"]
        or args.reasoning_effort != frozen["reasoning_effort"]
        or args.timeout_seconds != frozen["timeout_seconds"]
        or frozen["reasoning_summary"] != "detailed"
        or not frozen["show_raw_agent_reasoning"]
    ):
        raise ValueError("requested solver configuration differs from R6")

    out_root.mkdir(parents=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(out_root / "orchestrator.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    LOGGER.info("validated R6 inputs and created output root")
    protocol = {
        "schema_version": "1",
        "created_at": now(),
        "objective": "intentional_single_problem_token_cost_overfit",
        "primary_metric": (
            "all primary uncached tokens from every usage-complete attempt divided "
            "by verifier-safe successes"
        ),
        "task": contract,
        "sampling": {
            "fresh_h0": 3,
            "seed_skills": 1,
            "new_skill_per_round": 1,
            "meta_rounds": 3,
            "final_confirmation": 3,
            "solver_trajectory_total": 18,
            "user_override": (
                "The user reduced seed and per-round skill sampling from two to one; "
                "final confirmation remains three fresh runs."
            ),
        },
        "selection": (
            "Lowest ETtS among single-run seed/R1/R2/R3 candidates with terminal "
            "usage, F3, unchanged input, and verifier-safe success; selected candidate "
            "then receives three fresh confirmation runs."
        ),
        "inconclusive_rule": (
            "A favorable final ETtS delta smaller than the fresh H0 primary-token "
            "range is labeled inconclusive."
        ),
        "reference_proof_visible_to_solver": False,
        "reference_proof_visible_to_meta_agent": False,
        "hidden_chain_of_thought_claimed": False,
        "raw_dataset_bulk_copy": False,
        "legacy_source_mode": "read_only; only the frozen task is staged by the runner",
        "tmux_session": args.tmux_session,
        "output_dir": str(out_root),
    }
    write_json(out_root / "experiment_manifest.json", protocol)
    write_status(
        out_root=out_root,
        tmux_session=args.tmux_session,
        phase="preflight",
        round_index=None,
        h0_etts=None,
        best=None,
        remaining_stage_count=8,
    )

    preflight = run_preflight(
        out_root=out_root,
        contract=contract,
        codex_bin=args.codex_bin,
        verus_bin=args.verus_bin,
        lynette_bin=args.lynette_bin,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    if not preflight["passed"]:
        raise RuntimeError(f"preflight failed: {preflight}")
    LOGGER.info("preflight passed")
    task_jobs = out_root / "task.jsonl"
    make_task_jobs(task_jobs, contract)

    h0_root = out_root / "h0"
    h0_jobs = h0_root / "jobs.jsonl"
    make_h0_jobs(h0_jobs, h0_root, contract)
    write_status(
        out_root=out_root,
        tmux_session=args.tmux_session,
        phase="fresh_h0",
        round_index=None,
        h0_etts=None,
        best=None,
        remaining_stage_count=7,
    )
    run_solver_batch(
        jobs_path=h0_jobs,
        summary_path=h0_root / "batch_summary.json",
        codex_bin=args.codex_bin,
        verus_bin=args.verus_bin,
        lynette_bin=args.lynette_bin,
        workers=args.max_workers,
        timeout_seconds=args.timeout_seconds,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    h0_summary = summarize_jobs(
        jobs_path=h0_jobs,
        output_path=h0_root / "metric_summary.json",
        h0_etts=None,
    )
    h0_condition = one_condition(h0_summary)
    h0_etts = h0_condition["expected_primary_uncached_tokens_to_success"]
    if h0_etts is None:
        raise RuntimeError("fresh H0 lacks complete terminal usage or successes")
    ensure_source_unchanged(contract)
    LOGGER.info("fresh H0 complete: ETtS=%s", h0_etts)

    seed_root = out_root / "seed"
    seed_jobs = seed_root / "jobs.jsonl"
    prepare_skill_jobs(
        task_jobs_path=task_jobs,
        meta_output_path=args.r6_meta_output,
        out_root=seed_root,
        output_path=seed_jobs,
        iteration="seed-r6",
    )
    write_status(
        out_root=out_root,
        tmux_session=args.tmux_session,
        phase="seed_evaluation",
        round_index=None,
        h0_etts=h0_etts,
        best=None,
        remaining_stage_count=6,
    )
    run_solver_batch(
        jobs_path=seed_jobs,
        summary_path=seed_root / "batch_summary.json",
        codex_bin=args.codex_bin,
        verus_bin=args.verus_bin,
        lynette_bin=args.lynette_bin,
        workers=args.max_workers,
        timeout_seconds=args.timeout_seconds,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    seed_summary = summarize_jobs(
        jobs_path=seed_jobs,
        output_path=seed_root / "metric_summary.json",
        h0_etts=h0_etts,
    )
    ensure_source_unchanged(contract)
    all_skill_summaries = [seed_summary]
    best = best_eligible(all_skill_summaries)
    LOGGER.info("seed evaluation complete: best=%s", None if best is None else best["skill_id"])

    meta_supplement = (
        "\n\nSingle-problem experiment supplement:\n"
        "Optimize ETtS only on the one fixed task exposed in the allowlisted traces. "
        "Failures, timeouts, and invalid attempts are costs, never savings. Do not "
        "use or request a reference proof. Emit exactly aggressive, conservative, "
        "and structural skills. Every skill must supply a name, applicable state, "
        "ordered policy, stop/self-disable condition, predicted token-saving "
        "mechanism, and known failure risk. The aggressive skill should cut "
        "exploration or verifier cycles; the conservative skill must be minimal, "
        "low-overhead, and self-disabling; the structural skill must reorganize "
        "proof state or obligations."
    )
    current_meta_skill = (
        read_json(args.r6_meta_output)["revised_meta_skill"] + meta_supplement
    )
    previous_meta = args.r6_meta_output
    previous_summary = seed_root / "metric_summary.json"
    previous_runs = [Path(str(row["out_dir"])) for row in read_jsonl(seed_jobs)]

    for round_index in range(1, 4):
        round_root = out_root / f"round-{round_index}"
        meta_root = round_root / "meta"
        write_status(
            out_root=out_root,
            tmux_session=args.tmux_session,
            phase="meta_evolution",
            round_index=round_index,
            h0_etts=h0_etts,
            best=best,
            remaining_stage_count=7 - round_index * 2,
        )
        meta_dir = None
        meta_result = None
        for attempt_index in range(1, 4):
            attempt_dir = meta_root / f"attempt-{attempt_index:02d}"
            meta_result = run_token_meta_agent(
                out_dir=attempt_dir,
                h0_run_dirs=[
                    Path(str(row["out_dir"])) for row in read_jsonl(h0_jobs)
                ],
                current_meta_skill=current_meta_skill,
                codex_bin=args.codex_bin,
                prior_run_dirs=previous_runs,
                prior_meta_output_path=previous_meta,
                prior_summary_path=previous_summary,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=args.timeout_seconds,
            )
            if meta_result["audit"]["valid"]:
                meta_dir = attempt_dir
                break
            LOGGER.warning(
                "round %d meta attempt %d invalid; retrying",
                round_index,
                attempt_index,
            )
        if meta_dir is None or meta_result is None:
            raise RuntimeError(f"round {round_index} has no valid meta-agent output")
        injectable_meta = render_injectable_meta(meta_dir)
        round_jobs = round_root / "jobs.jsonl"
        prepare_skill_jobs(
            task_jobs_path=task_jobs,
            meta_output_path=injectable_meta,
            out_root=round_root,
            output_path=round_jobs,
            iteration=f"round-{round_index}",
        )
        write_status(
            out_root=out_root,
            tmux_session=args.tmux_session,
            phase="solver_evaluation",
            round_index=round_index,
            h0_etts=h0_etts,
            best=best,
            remaining_stage_count=6 - round_index * 2,
        )
        run_solver_batch(
            jobs_path=round_jobs,
            summary_path=round_root / "batch_summary.json",
            codex_bin=args.codex_bin,
            verus_bin=args.verus_bin,
            lynette_bin=args.lynette_bin,
            workers=args.max_workers,
            timeout_seconds=args.timeout_seconds,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
        )
        round_summary = summarize_jobs(
            jobs_path=round_jobs,
            output_path=round_root / "metric_summary.json",
            h0_etts=h0_etts,
        )
        all_skill_summaries.append(round_summary)
        best = best_eligible(all_skill_summaries)
        ensure_source_unchanged(contract)
        previous_meta = injectable_meta
        previous_summary = round_root / "metric_summary.json"
        previous_runs = [Path(str(row["out_dir"])) for row in read_jsonl(round_jobs)]
        current_meta_skill = (
            read_json(injectable_meta)["revised_meta_skill"] + meta_supplement
        )
        LOGGER.info(
            "round %d complete: best=%s",
            round_index,
            None if best is None else best["skill_id"],
        )

    if best is None:
        raise RuntimeError("no eligible successful candidate for final confirmation")
    selected_source = Path(str(best["skill_path"]))
    final_root = out_root / "final-confirmation"
    final_root.mkdir()
    selected_skill = final_root / "selected_skill.md"
    shutil.copyfile(selected_source, selected_skill)
    selection = {
        "selected_skill_id": best["skill_id"],
        "selected_profile": best["skill_profile"],
        "screen_etts": best["expected_primary_uncached_tokens_to_success"],
        "relative_delta_vs_h0": best["relative_delta_vs_h0"],
        "source_skill_path": str(selected_source),
        "source_skill_sha256": sha256_file(selected_source),
        "selected_skill_path": str(selected_skill),
        "selected_skill_sha256": sha256_file(selected_skill),
        "eligibility": (
            "1/1 verifier-safe, F3, unchanged input, complete terminal usage; "
            "single-sample screen follows the user's override"
        ),
    }
    write_json(final_root / "selection.json", selection)
    final_jobs = []
    for index in range(1, 4):
        run_id = f"final-{best['skill_id']}-{index:02d}"
        final_jobs.append(
            {
                "job_id": run_id,
                "final_case": contract["final_case"],
                "task_id": contract["task_id"],
                "source": contract["source"],
                "source_sha256": contract["source_sha256"],
                "out_dir": str(final_root / "runs" / run_id),
                "condition": f"skill:{best['skill_id']}",
                "skill_id": best["skill_id"],
                "skill_profile": best["skill_profile"],
                "skill_path": str(selected_skill),
                "skill_sha256": sha256_file(selected_skill),
                "status": "PENDING",
            }
        )
    final_jobs_path = final_root / "jobs.jsonl"
    write_jsonl(final_jobs_path, final_jobs)
    write_status(
        out_root=out_root,
        tmux_session=args.tmux_session,
        phase="final_confirmation",
        round_index=None,
        h0_etts=h0_etts,
        best=best,
        remaining_stage_count=1,
    )
    run_solver_batch(
        jobs_path=final_jobs_path,
        summary_path=final_root / "batch_summary.json",
        codex_bin=args.codex_bin,
        verus_bin=args.verus_bin,
        lynette_bin=args.lynette_bin,
        workers=args.max_workers,
        timeout_seconds=args.timeout_seconds,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    final_summary = summarize_jobs(
        jobs_path=final_jobs_path,
        output_path=final_root / "metric_summary.json",
        h0_etts=h0_etts,
    )
    final_condition = one_condition(final_summary)
    final_etts = final_condition["expected_primary_uncached_tokens_to_success"]
    h0_distribution = h0_condition["primary_uncached_token_distribution"]
    h0_range = h0_distribution["range"] if h0_distribution else None
    delta = None if final_etts is None else final_etts - h0_etts
    if (
        not final_condition["claim_admissible"]
        or not final_condition["verifier_safe_all"]
        or final_etts is None
    ):
        conclusion = "invalid_or_not_verifier_safe"
    elif delta >= 0:
        conclusion = "regression"
    elif h0_range is not None and abs(delta) < h0_range:
        conclusion = "inconclusive_within_h0_range"
    else:
        conclusion = "observed_single_problem_improvement"
    matched = {
        "schema_version": "1",
        "created_at": now(),
        "h0": h0_condition,
        "candidate": final_condition,
        "delta_primary_uncached_tokens": delta,
        "relative_delta_vs_h0": (
            None if delta is None else delta / h0_etts
        ),
        "h0_primary_uncached_token_range": h0_range,
        "conclusion": conclusion,
        "generalization_claimed": False,
        "hidden_chain_of_thought_claimed": False,
    }
    write_json(out_root / "matched_final_report.json", matched)
    ensure_source_unchanged(contract)
    write_status(
        out_root=out_root,
        tmux_session=args.tmux_session,
        phase="complete",
        round_index=None,
        h0_etts=h0_etts,
        best=final_condition,
        remaining_stage_count=0,
    )
    write_json(
        out_root / "completion.json",
        {
            "completed_at": now(),
            "status": "COMPLETE",
            "matched_report": str(out_root / "matched_final_report.json"),
            "source_sha256_after": sha256_file(Path(str(contract["source"]))),
            "raw_data_modified": False,
            "reference_proof_visible": False,
        },
    )
    LOGGER.info("experiment complete: %s", conclusion)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
