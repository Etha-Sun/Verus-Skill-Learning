from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from skillopt.engine.trainer import _normalise_patches
from skillopt.gradient.aggregate import merge_patches
from skillopt.gradient.reflect import run_minibatch_reflect
from skillopt.model import (
    configure_codex_exec,
    reset_token_tracker,
    set_optimizer_backend,
    set_optimizer_deployment,
    set_reasoning_effort,
)
from skillopt.optimizer.clip import rank_and_select
from skillopt.optimizer.skill import apply_patch_with_report

from skillopt_verusage.dataloader import VeruSAGEDataLoader


DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_CODEX_PATH = os.environ.get("CODEX_CLI_BIN", "codex")
MAX_CANDIDATE_BYTES = 4_000
_LEDGER_LOCK = threading.Lock()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _require_run_root(path: Path) -> Path:
    root_text = os.environ.get("VERUS_SKILL_RUN_ROOT", "")
    if not root_text:
        raise RuntimeError("VERUS_SKILL_RUN_ROOT is not set")
    root = Path(root_text).resolve()
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"output must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    return resolved


def _install_prompt_free_codex_ledger(path: Path) -> None:
    """Record every native optimizer attempt without persisting prompts/traces."""
    from skillopt.model import codex_backend

    original_chat = codex_backend._chat_messages_impl
    original_exec = codex_backend._run_codex_exec
    local = threading.local()
    path.parent.mkdir(parents=True, exist_ok=True)

    def append(row: dict[str, Any]) -> None:
        with _LEDGER_LOCK:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def tracked_exec(
        *,
        model: str,
        prompt: str,
        attachments: list[dict[str, Any]],
        output_schema: dict[str, Any] | None,
        timeout: int | None,
    ):
        call_id = str(getattr(local, "call_id", "") or uuid.uuid4().hex)
        attempt_index = int(getattr(local, "attempt_index", 0)) + 1
        local.attempt_index = attempt_index
        started = time.monotonic()
        status = "success"
        error_type: str | None = None
        usage: dict[str, int] | None = None
        try:
            value, usage = original_exec(
                model=model,
                prompt=prompt,
                attachments=attachments,
                output_schema=output_schema,
                timeout=timeout,
            )
            return value, usage
        except Exception as error:
            status = "error"
            error_type = type(error).__name__
            raise
        finally:
            append(
                {
                    "record_type": "optimizer_attempt",
                    "timestamp_unix": time.time(),
                    "call_id": call_id,
                    "attempt_index": attempt_index,
                    "stage": str(getattr(local, "stage", "unknown")),
                    "model": model,
                    "status": status,
                    "error_type": error_type,
                    "prompt_sha256": _sha256_text(prompt),
                    "attachment_count": len(attachments),
                    "requested_completion_policy": "backend_unbounded",
                    "usage": usage,
                    "usage_known": bool(
                        usage and int(usage.get("total_tokens", 0) or 0) > 0
                    ),
                    "wall_seconds": time.monotonic() - started,
                }
            )

    def tracked(
        model: str,
        messages: list[dict[str, Any]],
        max_completion_tokens: int,
        retries: int,
        stage: str,
        **kwargs: Any,
    ):
        call_id = uuid.uuid4().hex
        local.call_id = call_id
        local.attempt_index = 0
        local.stage = stage
        started = time.monotonic()
        status = "success"
        error_type: str | None = None
        try:
            return original_chat(
                model,
                messages,
                max_completion_tokens,
                retries,
                stage,
                **kwargs,
            )
        except Exception as error:
            status = "error"
            error_type = type(error).__name__
            raise
        finally:
            append(
                {
                    "record_type": "optimizer_logical_call",
                    "timestamp_unix": time.time(),
                    "call_id": call_id,
                    "stage": stage,
                    "model": model,
                    "status": status,
                    "error_type": error_type,
                    "attempts": int(getattr(local, "attempt_index", 0)),
                    "wall_seconds": time.monotonic() - started,
                }
            )
            for name in ("call_id", "attempt_index", "stage"):
                if hasattr(local, name):
                    delattr(local, name)

    codex_backend._run_codex_exec = tracked_exec
    codex_backend._chat_messages_impl = tracked


def _load_evidence(source_run: Path) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    summary = json.loads((source_run / "summary.json").read_text(encoding="utf-8"))
    cfg = dict(summary["config"])
    dataloader = VeruSAGEDataLoader(
        split_dir=cfg["split_dir"], split_mode="split_dir", seed=int(cfg["seed"])
    )
    dataloader.setup(cfg)
    batches = dataloader.plan_train_epoch(
        epoch=1,
        steps_per_epoch=1,
        accumulation=1,
        batch_size=40,
        seed=int(cfg["seed"]),
    )
    if len(batches) != 1 or len(batches[0].payload or []) != 40:
        raise ValueError("source split no longer reconstructs the 40-task epoch")

    prediction_dir = source_run / "steps" / "step_0001" / "rollout" / "predictions"
    results: list[dict[str, Any]] = []
    for item in batches[0].payload or []:
        item_id = str(item["id"])
        task_dir = prediction_dir / item_id
        result = json.loads((task_dir / "result.json").read_text(encoding="utf-8"))
        if result.get("id") != item_id:
            raise ValueError(f"training result id mismatch: {item_id}")
        if result.get("fidelity") == "V0_INVALID":
            raise ValueError(f"invalid source trajectory: {item_id}")
        conversation_path = task_dir / "conversation.json"
        if not conversation_path.is_file() or not json.loads(
            conversation_path.read_text(encoding="utf-8")
        ):
            raise ValueError(f"missing source conversation: {item_id}")
        results.append(result)

    skill_path = source_run / "steps" / "step_0001" / "rollout" / "skill.md"
    current_skill = skill_path.read_text(encoding="utf-8")
    baseline_skill = (source_run / "selection_eval_baseline" / "skill.md").read_text(
        encoding="utf-8"
    )
    if current_skill != baseline_skill:
        raise ValueError("source rollout skill differs from selection baseline skill")
    return cfg, current_skill, results


def _candidate_audit(
    current_skill: str,
    candidate_skill: str,
    ranked_patch: dict[str, Any],
    apply_report: list[dict[str, Any]],
    *,
    max_candidate_bytes: int = MAX_CANDIDATE_BYTES,
) -> list[str]:
    errors: list[str] = []
    candidate_bytes = len(candidate_skill.encode("utf-8"))
    if candidate_skill == current_skill:
        errors.append("candidate is identical to the seed skill")
    if candidate_bytes > max_candidate_bytes:
        errors.append(
            f"candidate exceeds {max_candidate_bytes} bytes: {candidate_bytes}"
        )
    if re.search(r"\b[0-9a-f]{20}\b", candidate_skill, flags=re.IGNORECASE):
        errors.append("candidate contains a task-like identifier")
    unapplied = [
        row for row in apply_report if not str(row.get("status", "")).startswith("applied")
    ]
    if unapplied:
        errors.append(f"{len(unapplied)} selected edits were not applied")

    edits = ranked_patch.get("edits", [])
    changed_text = "\n".join(
        str(edit.get("content", ""))
        for edit in edits
        if isinstance(edit, dict)
    )
    lowered = changed_text.lower()
    for fragment in ("```", "assert(", "forall|", "==>", ".fold_left("):
        if fragment in changed_text:
            errors.append(f"selected edits contain concrete code/formula: {fragment}")
    trusted_terms = ("trusted", "pre-existing", "preexisting", "already present", "existing")
    blanket_bans = ("must not be used", "may not be used", "never use", "do not use")
    if any(term in lowered for term in trusted_terms) and any(
        ban in lowered for ban in blanket_bans
    ):
        errors.append("selected edits forbid use of frozen trusted context")
    dangerous_introduction = re.search(
        r"\b(?:add|create|introduce|write|insert)\b.{0,100}"
        r"\b(?:assume|external_body|admit|axiom)\b",
        lowered,
        flags=re.DOTALL,
    )
    if dangerous_introduction:
        errors.append("selected edits recommend introducing a verification bypass")
    return errors


def _ledger_summary(path: Path) -> dict[str, Any]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if path.is_file() else []
    successful = [row for row in rows if row.get("status") == "success"]
    by_stage: dict[str, dict[str, int]] = {}
    for row in successful:
        stage = str(row.get("stage", "unknown"))
        usage = row.get("usage") or {}
        totals = by_stage.setdefault(
            stage, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
        )
        totals["calls"] += 1
        totals["prompt_tokens"] += int(usage.get("prompt_tokens", 0) or 0)
        totals["completion_tokens"] += int(usage.get("completion_tokens", 0) or 0)
    return {
        "records": len(rows),
        "successful_calls": len(successful),
        "failed_calls": len(rows) - len(successful),
        "by_stage": by_stage,
        "total": {
            key: sum(stage.get(key, 0) for stage in by_stage.values())
            for key in ("calls", "prompt_tokens", "completion_tokens")
        },
    }


def optimize(
    source_run: Path,
    out_dir: Path,
    *,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = "high",
    analyst_workers: int = 5,
    codex_path: str = DEFAULT_CODEX_PATH,
) -> dict[str, Any]:
    out_dir = _require_run_root(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "optimizer_manifest.json"
    manifest = {
        "schema_version": "1",
        "source_run": str(source_run.resolve()),
        "optimizer_backend": "codex_exec",
        "optimizer_model": model,
        "reasoning_effort": reasoning_effort,
        "analyst_workers": analyst_workers,
        "minibatch_size": 8,
        "merge_batch_size": 8,
        "edit_budget": 4,
        "random_seed": 1043,
        "candidate_byte_limit": MAX_CANDIDATE_BYTES,
    }
    if manifest_path.is_file():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
            raise ValueError("existing optimizer manifest does not match this invocation")
    else:
        _write_json(manifest_path, manifest)

    cfg, current_skill, results = _load_evidence(source_run.resolve())
    evidence_manifest = {
        "count": len(results),
        "successes": sum(bool(row.get("hard")) for row in results),
        "failures": sum(not bool(row.get("hard")) for row in results),
        "ordered_ids_sha256": _sha256_text("\n".join(str(row["id"]) for row in results)),
        "seed_skill_sha256": _sha256_text(current_skill),
        "prediction_dir": str(
            source_run.resolve() / "steps" / "step_0001" / "rollout" / "predictions"
        ),
        "batch_seed": 1043,
    }
    _write_json(out_dir / "evidence_manifest.json", evidence_manifest)

    set_optimizer_backend("codex_exec")
    set_optimizer_deployment(model)
    set_reasoning_effort(reasoning_effort)
    configure_codex_exec(
        path=codex_path,
        sandbox="read-only",
        profile="",
        full_auto=False,
        reasoning_effort=reasoning_effort,
        use_sdk="false",
        network_access=False,
        web_search=False,
        approval_policy="never",
    )
    os.environ["CODEX_WORKING_DIRECTORY"] = str(out_dir)
    os.environ["SKILLOPT_PATH_REFERENCES"] = "1"
    ledger_path = out_dir / "optimizer_calls.jsonl"
    _install_prompt_free_codex_ledger(ledger_path)
    reset_token_tracker()

    prediction_dir = source_run.resolve() / "steps" / "step_0001" / "rollout" / "predictions"
    patches_dir = out_dir / "patches"
    raw_patches = run_minibatch_reflect(
        results,
        current_skill,
        str(prediction_dir),
        str(patches_dir),
        workers=analyst_workers,
        failure_only=False,
        minibatch_size=8,
        edit_budget=4,
        random_seed=1043,
        error_system=None,
        success_system=None,
        step_buffer_context="",
        meta_skill_context="",
        update_mode="patch",
        skill_aware_reflection=False,
    )
    failure_patches, success_patches = _normalise_patches(raw_patches, "patch")
    if len(failure_patches) != 4 or len(success_patches) != 1:
        raise RuntimeError(
            "native reflection did not yield the expected 4 failure and 1 success patches"
        )

    merged_path = out_dir / "merged_patch.json"
    if merged_path.is_file():
        merged_patch = json.loads(merged_path.read_text(encoding="utf-8"))
    else:
        merged_patch = merge_patches(
            current_skill,
            failure_patches,
            success_patches,
            batch_size=8,
            verbose=True,
            workers=analyst_workers,
            update_mode="patch",
            meta_skill_context="",
        )
        _write_json(merged_path, merged_patch)

    ranked_path = out_dir / "ranked_edits.json"
    if ranked_path.is_file():
        ranked_patch = json.loads(ranked_path.read_text(encoding="utf-8"))
    else:
        ranked_patch = rank_and_select(
            current_skill,
            merged_patch,
            max_edits=4,
            update_mode="patch",
            meta_skill_context="",
        )
        _write_json(ranked_path, ranked_patch)

    candidate_skill, apply_report = apply_patch_with_report(current_skill, ranked_patch)
    effective_edit_budget = 4
    # SkillOpt's edit-count budget does not bound serialized skill size. If the
    # four-edit candidate crosses the host limit, stay inside the native Select
    # stage and lower L until the selected patch fits; do not hand-edit model output.
    for bounded_budget in (3, 2, 1):
        if len(candidate_skill.encode("utf-8")) <= MAX_CANDIDATE_BYTES:
            break
        bounded_path = out_dir / f"ranked_edits_l{bounded_budget}.json"
        if bounded_path.is_file():
            bounded_patch = json.loads(bounded_path.read_text(encoding="utf-8"))
        else:
            bounded_patch = rank_and_select(
                current_skill,
                merged_patch,
                max_edits=bounded_budget,
                update_mode="patch",
                meta_skill_context="",
            )
            _write_json(bounded_path, bounded_patch)
        bounded_skill, bounded_report = apply_patch_with_report(
            current_skill, bounded_patch
        )
        ranked_patch = bounded_patch
        candidate_skill = bounded_skill
        apply_report = bounded_report
        effective_edit_budget = bounded_budget

    (out_dir / "candidate_skill.md").write_text(candidate_skill, encoding="utf-8")
    _write_json(out_dir / "edit_apply_report.json", apply_report)
    audit_errors = _candidate_audit(
        current_skill, candidate_skill, ranked_patch, apply_report
    )
    result = {
        "status": (
            "candidate_pending_manual_audit"
            if not audit_errors
            else "rejected_by_automatic_audit"
        ),
        "source_run": str(source_run.resolve()),
        "source_rollout_hard": sum(bool(row.get("hard")) for row in results) / len(results),
        "source_rollout_n": len(results),
        "optimizer_model": model,
        "optimizer_backend": "codex_exec",
        "optimizer_cost_usd": 0.0,
        "optimizer_cost_basis": "local Codex quota; no metered API dollar estimate",
        "candidate_bytes": len(candidate_skill.encode("utf-8")),
        "candidate_sha256": _sha256_text(candidate_skill),
        "seed_skill_sha256": _sha256_text(current_skill),
        "n_failure_patches": len(failure_patches),
        "n_success_patches": len(success_patches),
        "n_merged_edits": len(merged_patch.get("edits", [])),
        "n_ranked_edits": len(ranked_patch.get("edits", [])),
        "effective_edit_budget": effective_edit_budget,
        "audit_errors": audit_errors,
        "codex_usage": _ledger_summary(ledger_path),
        "source_config_sha256": _sha256_text(
            json.dumps(cfg, ensure_ascii=False, sort_keys=True)
        ),
    }
    _write_json(out_dir / "optimizer_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--analyst-workers", type=int, default=5)
    parser.add_argument("--codex-path", default=DEFAULT_CODEX_PATH)
    args = parser.parse_args()
    result = optimize(
        args.source_run,
        args.out_dir,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        analyst_workers=args.analyst_workers,
        codex_path=args.codex_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
