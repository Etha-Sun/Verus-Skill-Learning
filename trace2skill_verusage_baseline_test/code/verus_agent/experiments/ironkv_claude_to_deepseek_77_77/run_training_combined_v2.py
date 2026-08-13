#!/usr/bin/env python3
"""Repair train77 routing and run native-style combined Trace2Skill evolution.

The frozen train split contains both successful and failed Claude trajectories.
This runner reuses the 51 valid success records from the superseded v1 run,
reissues the two truncated successful analyses, analyzes all 24 failed
trajectories with Failure Cause/Memory prompts, and then invokes the upstream
CombinedParallelSkillEvolver.  It never reads held-out trajectories or proofs.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import shutil
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from openai import OpenAI

from analysis.parse_error_analysis_outputs import parse_items as parse_failure_items
from skill_evolver.parallel_success_evolving_agent import (
    CombinedParallelSkillEvolver,
    normalize_mixed_records,
)
from verus_agent.experiments.ironkv_claude_to_deepseek_77_77 import (
    run_training_evolution as v1,
)


LOG = logging.getLogger("ironkv_trace2skill_combined_v2")
EXPERIMENT_ROOT = Path(__file__).resolve().parent
PROMPT_ROOT = EXPERIMENT_ROOT / "prompts"
FAILURE_SYSTEM_PROMPT = PROMPT_ROOT / "failure_analysis_system.txt"
FAILURE_USER_PROMPT = PROMPT_ROOT / "failure_analysis_user.txt"
V1_OUTPUT_ROOT = (
    v1.PROJECT_ROOT / "outputs/ironkv_claude_to_deepseek_trace2skill_train77_v1"
)
DEFAULT_OUTPUT_ROOT = (
    v1.PROJECT_ROOT
    / "outputs/ironkv_claude_to_deepseek_trace2skill_train77_combined_v2"
)
DEFAULT_ANALYSIS_MAX_TOKENS = 8192


def dataset_paths() -> tuple[Path, Path, Path]:
    manifest = json.loads(
        (v1.SPLIT_ROOT / "split_manifest.json").read_text(encoding="utf-8")
    )
    dataset_dir = Path(manifest["dataset_dir"])
    dataset_root = dataset_dir.parent
    return (
        dataset_dir,
        dataset_root / "results-sonnet45.csv",
        dataset_dir / "trivialresults",
    )


def load_outcome_labels() -> dict[str, str]:
    dataset_dir, csv_path, trivial_dir = dataset_paths()
    if not dataset_dir.is_dir() or not csv_path.is_file() or not trivial_dir.is_dir():
        raise FileNotFoundError("IronKV outcome-label inputs are incomplete")
    labels: dict[str, str] = {}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle, skipinitialspace=True):
            if len(row) < 2:
                continue
            task_id = row[0].strip()
            outcome = row[1].strip().upper()
            # The dataset also labels several non-successes as CHEAT variants.
            # Trace2Skill routes every non-TRUE trajectory through failure
            # analysis; none may contribute a Success Memory record.
            if outcome != "TRUE" and not (
                outcome == "FALSE" or outcome.startswith("CHEAT")
            ):
                raise ValueError(f"unexpected outcome for {task_id}: {outcome}")
            labels[task_id] = "success" if outcome == "TRUE" else "failure"
    for path in trivial_dir.glob("*.log"):
        task_id = path.stem
        previous = labels.get(task_id)
        if previous not in (None, "success"):
            raise ValueError(f"conflicting trivial outcome for {task_id}")
        labels[task_id] = "success"
    return labels


def valid_v1_success_record(task_id: str) -> bool:
    task_dir = V1_OUTPUT_ROOT / "success_analysis" / task_id
    validation_path = task_dir / "validation.json"
    record_path = task_dir / "record.json"
    if not validation_path.is_file() or not record_path.is_file():
        return False
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    return validation.get("valid") is True


def build_repair_plan() -> dict[str, Any]:
    rows = v1.load_jsonl(v1.TRAIN_MANIFEST)
    labels = load_outcome_labels()
    unknown = sorted(row["task_id"] for row in rows if row["task_id"] not in labels)
    if unknown:
        raise ValueError(f"missing outcome labels: {unknown}")
    successful = [row for row in rows if labels[row["task_id"]] == "success"]
    failed = [row for row in rows if labels[row["task_id"]] == "failure"]
    reused = [row for row in successful if valid_v1_success_record(row["task_id"])]
    reissue = [row for row in successful if not valid_v1_success_record(row["task_id"])]
    counts = {
        "train_total": len(rows),
        "successful_trajectories": len(successful),
        "failed_trajectories": len(failed),
        "reused_valid_success_records": len(reused),
        "reissued_success_analyses": len(reissue),
        "new_failure_analyses": len(failed),
        "new_analysis_requests": len(reissue) + len(failed),
    }
    expected = {
        "train_total": 77,
        "successful_trajectories": 53,
        "failed_trajectories": 24,
        "reused_valid_success_records": 51,
        "reissued_success_analyses": 2,
        "new_failure_analyses": 24,
        "new_analysis_requests": 26,
    }
    if counts != expected:
        raise ValueError(f"repair-plan cardinality mismatch: {counts} != {expected}")
    return {
        "counts": counts,
        "success_reuse_ids": [row["task_id"] for row in reused],
        "success_reissue_ids": [row["task_id"] for row in reissue],
        "failure_analysis_ids": [row["task_id"] for row in failed],
        "labels": {row["task_id"]: labels[row["task_id"]] for row in rows},
    }


def expected_manifest(config: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment": "ironkv_claude_teacher_to_deepseek_trace2skill_train77_combined_v2",
        "protocol": (
            "outcome-routed success/failure analysis -> combined MAP -> "
            "hierarchical REDUCE -> TRANSLATE -> APPLY -> VALIDATE"
        ),
        "created_at": v1.utc_now(),
        "status": "prepared",
        "train_manifest": str(v1.TRAIN_MANIFEST.resolve()),
        "train_manifest_sha256": v1.sha256_file(v1.TRAIN_MANIFEST),
        "heldout_inputs_used": False,
        "teacher": "claude-sonnet-4.5 IronKV trajectories",
        "student_and_evolution_model": config["model"],
        "post_consolidation_despecialization": False,
        "configuration": config,
        "repair_plan": plan["counts"],
        "analysis": {
            "one_complete_trajectory_per_request": True,
            "successful_trajectories_use": "Success Memory",
            "failed_trajectories_use": "Failure Cause and Failure Memory",
            "max_success_memory_items": 3,
            "max_failure_memory_items": 3,
            "automatic_http_retries": 0,
        },
        "evolution": {
            "upstream_class": "CombinedParallelSkillEvolver",
            "batch_size": 1,
            "merge_batch_size": 5,
            "max_merge_levels": 5,
            "max_skill_lines": 500,
            "max_references": 5,
            "max_verification_rounds": 3,
            "patch_pipeline": "json",
            "translation_skipped": False,
            "json_format_self_fix": True,
        },
    }


def prepare_output(
    output_root: Path,
    config: dict[str, Any],
    plan: dict[str, Any],
    resume: bool,
) -> None:
    manifest_path = output_root / "run_manifest.json"
    if output_root.exists():
        if not resume:
            raise FileExistsError(f"output exists; use --resume: {output_root}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("configuration") != config:
            raise ValueError("resume configuration mismatch")
        if manifest.get("repair_plan") != plan["counts"]:
            raise ValueError("resume repair-plan mismatch")
        return

    output_root.mkdir(parents=True)
    configuration = output_root / "configuration"
    configuration.mkdir()
    for source, name in (
        (v1.TRAIN_MANIFEST, "train_trajectories.snapshot.jsonl"),
        (v1.SPLIT_ROOT / "split_manifest.json", "split_manifest.snapshot.json"),
        (v1.SPLIT_ROOT / "leakage_audit.json", "leakage_audit.snapshot.json"),
        (v1.SUCCESS_SYSTEM_PROMPT, "success_analysis_system.txt"),
        (v1.SUCCESS_USER_PROMPT, "success_analysis_user.txt"),
        (FAILURE_SYSTEM_PROMPT, "failure_analysis_system.txt"),
        (FAILURE_USER_PROMPT, "failure_analysis_user.txt"),
    ):
        shutil.copy2(source, configuration / name)
    v1.write_json(configuration / "repair_plan.json", plan)
    v1.write_json(manifest_path, expected_manifest(config, plan))

    for task_id in plan["success_reuse_ids"]:
        source = V1_OUTPUT_ROOT / "success_analysis" / task_id
        target = output_root / "success_analysis" / task_id
        shutil.copytree(source, target)
        v1.write_json(
            target / "reuse_provenance.json",
            {
                "reused_from": str(source.resolve()),
                "reason": "valid success record from superseded v1 run",
                "reused_at": v1.utc_now(),
            },
        )


def validate_failure_items(items: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    type_counts = Counter(item.get("type") for item in items)
    if type_counts["failure_cause"] < 1:
        errors.append("expected at least one failure cause item")
    if not 1 <= type_counts["failure_memory"] <= 3:
        errors.append(
            f"expected 1..3 failure memory items, found {type_counts['failure_memory']}"
        )
    for index, item in enumerate(items, start=1):
        if item.get("type") not in {"failure_cause", "failure_memory"}:
            errors.append(f"item {index} has invalid type")
        # The upstream Trace2Skill parser preserves a Failure Cause even when
        # the model omits its optional display title.  Description and content
        # carry the causal evidence; Failure Memory titles remain required for
        # downstream procedural consolidation.
        required_fields = (
            ("description", "content")
            if item.get("type") == "failure_cause"
            else ("title", "description", "content")
        )
        for field in required_fields:
            if not str(item.get(field, "")).strip():
                errors.append(f"item {index} has empty {field}")
    return not errors, errors


def analyze_failure_one(
    row: dict[str, Any],
    output_root: Path,
    config: dict[str, Any],
    secret: str,
    ledger: v1.RequestLedger,
) -> tuple[str, bool, str]:
    task_id = row["task_id"]
    task_dir = output_root / "failure_analysis" / task_id
    task_dir.mkdir(parents=True, exist_ok=False)
    trajectory_path = Path(row["trajectory_path"])
    raw_bytes = trajectory_path.read_bytes()
    if v1.sha256_bytes(raw_bytes) != row["trajectory_sha256"]:
        raise ValueError(f"trajectory hash changed before request: {task_id}")
    raw_log = raw_bytes.decode("utf-8", errors="replace")
    system_prompt = FAILURE_SYSTEM_PROMPT.read_text(encoding="utf-8")
    template = FAILURE_USER_PROMPT.read_text(encoding="utf-8")
    if template.count("{agent_log}") != 1:
        raise ValueError("failure user template must contain {agent_log} exactly once")
    user_prompt = template.replace("{agent_log}", raw_log)
    request_index = ledger.next_index()
    started_at = v1.utc_now()
    v1.write_json(
        task_dir / "request_manifest.json",
        {
            "request_index": request_index,
            "phase": "failure_analysis",
            "task_id": task_id,
            "trajectory_path": str(trajectory_path),
            "trajectory_sha256": row["trajectory_sha256"],
            "trajectory_bytes": len(raw_bytes),
            "trajectory_lines": row["trajectory_lines"],
            "complete_trajectory_included": True,
            "trajectory_template_occurrences": 1,
            "model": config["model"],
            "base_url": config["base_url"],
            "temperature": config["temperature"],
            "max_output_tokens": config["analysis_max_tokens"],
            "api_key_env_var": config["api_key_env_var"],
            "api_key_configured": True,
            "sdk_max_retries": 0,
            "started_at": started_at,
        },
    )
    (task_dir / "system_prompt.txt").write_text(system_prompt, encoding="utf-8")
    (task_dir / "user_prompt.txt").write_text(user_prompt, encoding="utf-8")
    request_started = time.monotonic()
    event: dict[str, Any] = {
        "request_index": request_index,
        "phase": "failure_analysis",
        "task_id": task_id,
        "started_at": started_at,
        "sdk_max_retries": 0,
    }
    try:
        client = OpenAI(
            api_key=secret,
            base_url=config["base_url"],
            timeout=config["timeout_seconds"],
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=config["temperature"],
            max_tokens=config["analysis_max_tokens"],
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        v1.write_json(task_dir / "raw_response.json", response.model_dump(mode="json"))
        response_text = response.choices[0].message.content or ""
        (task_dir / "response_text.md").write_text(response_text, encoding="utf-8")
        usage = v1.response_usage(response)
        v1.write_json(task_dir / "usage.json", usage)
        items = parse_failure_items(response_text)
        valid, errors = validate_failure_items(items)
        v1.write_json(
            task_dir / "validation.json",
            {"valid": valid, "errors": errors, "item_count": len(items)},
        )
        if valid:
            v1.write_json(
                task_dir / "record.json",
                {
                    "instance_id": task_id,
                    "source_file": trajectory_path.name,
                    "items": items,
                },
            )
        else:
            v1.write_json(
                task_dir / "error.json",
                {"type": "response_validation_error", "errors": errors},
            )
        event.update(
            {
                "status": "success" if valid else "invalid_response",
                "model_returned": getattr(response, "model", None),
                **usage,
            }
        )
        return task_id, valid, "ok" if valid else "; ".join(errors)
    except Exception as exc:
        safe_error = v1.sanitize(str(exc), secret)
        v1.write_json(
            task_dir / "error.json",
            {"type": "api_or_transport_error", "error": safe_error},
        )
        event.update({"status": "error", "error": safe_error})
        return task_id, False, safe_error
    finally:
        event["latency_seconds"] = round(time.monotonic() - request_started, 6)
        ledger.record(event)


def analysis_status(
    output_root: Path, rows: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, Any]:
    labels = plan["labels"]
    valid: list[str] = []
    invalid: list[str] = []
    pending: list[str] = []
    by_kind = Counter()
    for row in rows:
        task_id = row["task_id"]
        kind = labels[task_id]
        task_dir = output_root / f"{kind}_analysis" / task_id
        validation_path = task_dir / "validation.json"
        if validation_path.is_file():
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            if validation.get("valid"):
                valid.append(task_id)
                by_kind[f"valid_{kind}"] += 1
            else:
                invalid.append(task_id)
                by_kind[f"invalid_{kind}"] += 1
        elif (task_dir / "error.json").is_file():
            invalid.append(task_id)
            by_kind[f"invalid_{kind}"] += 1
        else:
            pending.append(task_id)
            by_kind[f"pending_{kind}"] += 1
    return {
        "total": len(rows),
        "valid": len(valid),
        "invalid": len(invalid),
        "pending": len(pending),
        "by_kind": dict(sorted(by_kind.items())),
        "valid_task_ids": valid,
        "invalid_task_ids": invalid,
        "pending_task_ids": pending,
        "updated_at": v1.utc_now(),
    }


def revalidate_existing_failure_responses(
    output_root: Path, rows: list[dict[str, Any]], plan: dict[str, Any]
) -> list[str]:
    """Re-parse complete saved responses after an offline validator update."""
    accepted: list[str] = []
    for row in rows:
        task_id = row["task_id"]
        if plan["labels"][task_id] != "failure":
            continue
        task_dir = output_root / "failure_analysis" / task_id
        response_path = task_dir / "response_text.md"
        validation_path = task_dir / "validation.json"
        if not response_path.is_file() or not validation_path.is_file():
            continue
        previous = json.loads(validation_path.read_text(encoding="utf-8"))
        if previous.get("valid") is True:
            continue
        items = parse_failure_items(response_path.read_text(encoding="utf-8"))
        valid, errors = validate_failure_items(items)
        if not valid:
            continue
        warnings = [
            f"item {index} has no optional Failure Cause title"
            for index, item in enumerate(items, start=1)
            if item.get("type") == "failure_cause"
            and not str(item.get("title", "")).strip()
        ]
        v1.write_json(
            task_dir / "record.json",
            {
                "instance_id": task_id,
                "source_file": Path(row["trajectory_path"]).name,
                "items": items,
            },
        )
        v1.write_json(
            validation_path,
            {
                "valid": True,
                "errors": [],
                "warnings": warnings,
                "item_count": len(items),
                "offline_revalidated": True,
                "prior_validation": previous,
            },
        )
        accepted.append(task_id)
    return accepted


def run_analysis(
    output_root: Path,
    config: dict[str, Any],
    secret: str,
    plan: dict[str, Any],
    max_new: int | None,
) -> dict[str, Any]:
    rows = v1.load_jsonl(v1.TRAIN_MANIFEST)
    accepted = revalidate_existing_failure_responses(output_root, rows, plan)
    if accepted:
        LOG.info("Offline-revalidated saved failure responses: %s", accepted)
    status = analysis_status(output_root, rows, plan)
    if status["invalid"]:
        LOG.error("Invalid records block automatic retry: %d", status["invalid"])
        v1.write_json(output_root / "analysis_summary.json", status)
        return status
    pending_ids = set(status["pending_task_ids"])
    pending = [row for row in rows if row["task_id"] in pending_ids]
    if max_new is not None:
        pending = pending[:max_new]
    ledger = v1.RequestLedger(output_root / "api_requests.jsonl", secret)
    LOG.info(
        "Combined analysis: valid=%d pending_now=%d workers=%d",
        status["valid"],
        len(pending),
        config["analysis_workers"],
    )
    with ThreadPoolExecutor(max_workers=config["analysis_workers"]) as executor:
        futures = {}
        for row in pending:
            if plan["labels"][row["task_id"]] == "success":
                future = executor.submit(
                    v1.analyze_one, row, output_root, config, secret, ledger
                )
            else:
                future = executor.submit(
                    analyze_failure_one, row, output_root, config, secret, ledger
                )
            futures[future] = row["task_id"]
        for future in as_completed(futures):
            task_id, valid, message = future.result()
            LOG.info("analysis task=%s valid=%s result=%s", task_id, valid, message)
            v1.write_json(
                output_root / "analysis_summary.json",
                analysis_status(output_root, rows, plan),
            )
    final = analysis_status(output_root, rows, plan)
    v1.write_json(output_root / "analysis_summary.json", final)
    return final


class NativeStyleVerusCombinedEvolver(CombinedParallelSkillEvolver):
    """Upstream mixed-record hierarchy with domain-wording substitutions only."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._map_system_prompt = v1.native_verus_map_prompt(self._map_system_prompt)
        self._map_patterns_system_prompt = v1.native_verus_map_prompt(
            self._map_patterns_system_prompt
        )


def collect_records(
    output_root: Path, rows: list[dict[str, Any]], plan: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    success_records: list[dict[str, Any]] = []
    error_records: list[dict[str, Any]] = []
    for row in rows:
        kind = plan["labels"][row["task_id"]]
        path = output_root / f"{kind}_analysis" / row["task_id"] / "record.json"
        if not path.is_file():
            raise ValueError(f"missing valid {kind} record: {row['task_id']}")
        record = json.loads(path.read_text(encoding="utf-8"))
        (success_records if kind == "success" else error_records).append(record)
    if len(success_records) != 53 or len(error_records) != 24:
        raise ValueError("combined record cardinality mismatch")
    return success_records, error_records


def run_evolution(
    output_root: Path,
    config: dict[str, Any],
    secret: str,
    plan: dict[str, Any],
) -> None:
    evolution_root = output_root / "evolution"
    completion = evolution_root / "evolution_summary.json"
    if completion.is_file():
        LOG.info("Evolution already completed; refusing duplicate execution")
        return
    if evolution_root.exists():
        raise FileExistsError("partial evolution exists; refusing paid rerun")
    skill_dir = evolution_root / "skill/verus-proof-repair"
    skill_dir.parent.mkdir(parents=True)
    shutil.copytree(v1.NEUTRAL_SEED, skill_dir)
    intermediates = evolution_root / "intermediates"
    intermediates.mkdir(parents=True)
    rows = v1.load_jsonl(v1.TRAIN_MANIFEST)
    success_records, error_records = collect_records(output_root, rows, plan)
    mixed_records = normalize_mixed_records(error_records, success_records)
    v1.write_json(evolution_root / "input/success_records.json", success_records)
    v1.write_json(evolution_root / "input/error_records.json", error_records)
    v1.write_json(evolution_root / "input/combined_records.json", mixed_records)
    v1.write_json(
        evolution_root / "input/input_audit.json",
        {
            "success_record_count": len(success_records),
            "error_record_count": len(error_records),
            "combined_record_count": len(mixed_records),
            "heldout_inputs_used": False,
        },
    )
    ledger = v1.RequestLedger(output_root / "api_requests.jsonl", secret)
    client = v1.PersistentAuditedClient(
        secret=secret,
        ledger=ledger,
        model=config["model"],
        base_url=config["base_url"],
        generation_config={
            "reasoning_effort": "high",
            "extra_body": {"thinking": {"type": "enabled"}},
        },
        timeout=config["timeout_seconds"],
    )
    import skill_evolver.skill_evolving_agent as sequential_module

    quick_validate = os.environ.get("SKILL_CREATOR_VALIDATE_SCRIPT")
    if quick_validate:
        sequential_module.QUICK_VALIDATE_SCRIPT = Path(quick_validate)
    evolver = NativeStyleVerusCombinedEvolver(
        client=client,
        skill_dir=skill_dir,
        batch_size=1,
        merge_batch_size=5,
        max_workers=config["evolution_workers"],
        max_merge_levels=5,
        temperature=config["temperature"],
        max_tokens=config["evolution_max_tokens"],
        verbose=True,
        dry_run=False,
        output_dir=intermediates,
        parse_failure_dir=evolution_root / "parse_failures",
        max_skill_lines=500,
        max_references=5,
        max_verification_rounds=3,
        skip_translation=False,
        patch_pipeline="json",
        enable_json_format_self_fix=True,
    )
    configuration = evolution_root / "configuration"
    configuration.mkdir(parents=True)
    for name, content in (
        ("map_system_prompt.txt", evolver._map_system_prompt),
        ("merge_system_prompt.txt", evolver._merge_system_prompt),
        ("apply_system_prompt.txt", evolver._apply_system_prompt),
        ("translation_system_prompt.txt", evolver._translation_system_prompt),
    ):
        (configuration / name).write_text(content, encoding="utf-8")
    v1.write_json(
        evolution_root / "evolution_manifest.json",
        {
            "status": "running",
            "started_at": v1.utc_now(),
            "upstream_class": "CombinedParallelSkillEvolver",
            "domain_adaptation": "spreadsheet terminology replaced with Verus terminology only",
            "additional_despecialization": False,
            "record_count": len(mixed_records),
            "configuration": config,
        },
    )
    try:
        result = evolver.run(mixed_records, input_mode="records")
        if not result.get("edits"):
            raise RuntimeError("combined evolver produced no applied skill edits")
        v1.write_json(
            completion,
            {
                "status": "completed",
                "completed_at": v1.utc_now(),
                "map_patch_count": len(result.get("patches", [])),
                "applied_file_edit_count": len(result.get("edits", [])),
                "reasoning": result.get("reasoning", ""),
                "changelog": result.get("changelog", []),
                "estimated_upstream_llm_calls": result.get("total_llm_calls"),
                "skill_sha256": v1.sha256_tree(skill_dir),
            },
        )
        manifest_path = evolution_root / "evolution_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update({"status": "completed", "completed_at": v1.utc_now()})
        v1.write_json(manifest_path, manifest)
    except Exception as exc:
        safe_error = v1.sanitize(str(exc), secret)
        v1.write_json(
            evolution_root / "error.json",
            {"status": "error", "occurred_at": v1.utc_now(), "error": safe_error},
        )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("analyze", "evolve", "all"), default="all")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--env-file", type=Path, default=v1.DEFAULT_ENV_FILE)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--temperature", type=float, default=v1.DEFAULT_TEMPERATURE)
    parser.add_argument(
        "--analysis-max-tokens", type=int, default=DEFAULT_ANALYSIS_MAX_TOKENS
    )
    parser.add_argument(
        "--evolution-max-tokens", type=int, default=v1.DEFAULT_EVOLUTION_MAX_TOKENS
    )
    parser.add_argument(
        "--analysis-workers", type=int, default=v1.DEFAULT_ANALYSIS_WORKERS
    )
    parser.add_argument(
        "--evolution-workers", type=int, default=v1.DEFAULT_EVOLUTION_WORKERS
    )
    parser.add_argument("--timeout", type=float, default=v1.DEFAULT_TIMEOUT)
    parser.add_argument("--max-new", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args(argv)
    config, secret = v1.load_config(args)
    plan = build_repair_plan()
    output_root = args.output_root.resolve()
    prepare_output(output_root, config, plan, args.resume)
    if args.prepare_only:
        audit = v1.credential_audit(output_root, secret)
        v1.write_json(output_root / "credential_audit.json", audit)
        return 0 if audit["credential_value_absent"] else 1
    try:
        if args.phase in {"analyze", "all"}:
            status = run_analysis(
                output_root, config, secret, plan, args.max_new
            )
            if status["invalid"]:
                v1.update_run_manifest(output_root, status="blocked_invalid_analysis")
                return 2
            if args.phase == "all" and status["valid"] != 77:
                v1.update_run_manifest(output_root, status="analysis_incomplete")
                return 3
        if args.phase in {"evolve", "all"}:
            status = analysis_status(
                output_root, v1.load_jsonl(v1.TRAIN_MANIFEST), plan
            )
            if status["valid"] != 77 or status["invalid"]:
                raise ValueError("evolution requires 53 success and 24 failure records")
            v1.update_run_manifest(output_root, status="evolution_running")
            run_evolution(output_root, config, secret, plan)
            v1.update_run_manifest(
                output_root, status="completed", completed_at=v1.utc_now()
            )
    except Exception as exc:
        safe_error = v1.sanitize(str(exc), secret)
        v1.write_json(
            output_root / "error.json",
            {"status": "error", "occurred_at": v1.utc_now(), "error": safe_error},
        )
        v1.update_run_manifest(
            output_root, status="error", completed_at=v1.utc_now()
        )
        LOG.error("%s", safe_error)
        return 1
    finally:
        audit = v1.credential_audit(output_root, secret)
        v1.write_json(output_root / "credential_audit.json", audit)
        if not audit["credential_value_absent"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
