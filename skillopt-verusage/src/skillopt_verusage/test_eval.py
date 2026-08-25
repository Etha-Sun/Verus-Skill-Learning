from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from skill_evolution_pilot.actor_isolation import (
    ActorIsolationConfig,
    isolation_preflight,
)
from skill_evolution_pilot.codex_runner import (
    build_cross_provider_prompt,
    build_prompt,
    run_codex_smoke,
)
from skill_evolution_pilot.workspace import sha256_file

from skillopt_verusage.codex_flash_adapter import CodexDeepSeekAdapter
from skillopt_verusage.dataloader import VeruSAGEDataLoader
from skillopt_verusage.outcome import (
    TRACE_COMPLETE_CLASSES,
    fidelity_class,
    proof_solved,
    within_budget,
)
from skillopt_verusage.skill_artifact import SkillArtifact, load_skill_artifact
from skillopt_verusage.verus_release import require_formal_verus


FIXED_SPLIT_SHA256 = "a71e2a3838c2222312cc2487fc35b6a24cbc924e0a917d5e9120499f0ba2b49c"
TEST_ITEMS_SHA256 = "81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42"
KNOWN_VERUS_VERSION_SENSITIVE_ITEM_IDS = (
    "f24cf9cc9db98c56f792",
    "826687f9c56eb8e65d5d",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _require_run_dir(path: Path) -> Path:
    root_text = os.environ.get("VERUS_SKILL_RUN_ROOT", "")
    if not root_text:
        raise RuntimeError("VERUS_SKILL_RUN_ROOT is not set")
    root = Path(root_text).resolve()
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"output must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    if resolved.exists():
        allowed = {
            "bridge.log",
            "bridge_calls.jsonl",
            "bridge_manifest.json",
            "models.json",
            "test.log",
        }
        unexpected = sorted(item.name for item in resolved.iterdir() if item.name not in allowed)
        if unexpected:
            raise ValueError(f"run directory contains unexpected files: {unexpected}")
    return resolved


def _load_test_items(split_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    test_items_path = split_dir / "test" / "items.json"
    actual_test_sha256 = sha256_file(test_items_path)
    if actual_test_sha256 != TEST_ITEMS_SHA256:
        raise ValueError(
            f"frozen test items hash mismatch: {actual_test_sha256}"
        )
    manifest = json.loads((split_dir / "split_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("split_sha256") != FIXED_SPLIT_SHA256:
        raise ValueError("frozen split hash mismatch")
    loader = VeruSAGEDataLoader(
        split_dir=str(split_dir),
        split_mode="split_dir",
        seed=42,
    )
    loader.setup({})
    items = loader.get_split_items("test")
    if len(items) != 20 or len({str(item["id"]) for item in items}) != 20:
        raise ValueError("held-out test split is not 20 unique items")
    return items, manifest


def _select_test_items(
    items: list[dict[str, Any]], requested_ids: list[str]
) -> list[dict[str, Any]]:
    if not requested_ids:
        return items
    if len(requested_ids) != len(set(requested_ids)):
        raise ValueError("duplicate --item-id")
    available = {str(item["id"]) for item in items}
    unknown = sorted(set(requested_ids) - available)
    if unknown:
        raise ValueError(f"unknown --item-id: {', '.join(unknown)}")
    requested = set(requested_ids)
    return [item for item in items if str(item["id"]) in requested]


def _load_skill_artifact(path: Path, expected_sha256: str) -> SkillArtifact:
    return load_skill_artifact(path, expected_sha256)


def _load_skill(path: Path, expected_sha256: str) -> tuple[str, str]:
    artifact = _load_skill_artifact(path, expected_sha256)
    return artifact.entrypoint_text, artifact.artifact_sha256


def _local_fidelity(result: dict[str, Any]) -> str:
    fidelity = result.get("fidelity") or {}
    if result.get("timed_out") and fidelity.get("input_unchanged"):
        return "V1_TRUNCATED"
    if fidelity.get("f3") and fidelity.get("input_unchanged"):
        return "V2_TRACE"
    return "V0_INVALID"


def _archive_attempt(task_dir: Path, attempt_index: int) -> None:
    archive = task_dir.parent / "_attempts" / task_dir.name / f"attempt-{attempt_index:02d}"
    archive.mkdir(parents=True, exist_ok=False)
    for path in list(task_dir.iterdir()):
        shutil.move(str(path), archive / path.name)


def _run_direct(
    *,
    items: list[dict[str, Any]],
    out_dir: Path,
    skill_text: str,
    skill_dir: Path | None = None,
    skill_sha256: str,
    model: str,
    reasoning_effort: str,
    codex_bin: Path,
    verus_bin: Path,
    lynette_bin: Path,
    workers: int,
    timeout_seconds: int,
    model_context_window: int,
    actor_contract_profile: str,
    condition_skill_present: bool,
) -> list[dict[str, Any]]:
    predictions = out_dir / "predictions"
    predictions.mkdir(parents=True)
    if condition_skill_present:
        (out_dir / "skill.md").write_text(skill_text, encoding="utf-8")

    def execute(item: dict[str, Any]) -> dict[str, Any]:
        task_dir = predictions / str(item["id"])
        last_error = ""
        for attempt_index in range(1, 4):
            try:
                result = run_codex_smoke(
                    source=Path(str(item["source_path"])),
                    out_dir=task_dir,
                    codex_bin=codex_bin,
                    verus_bin=verus_bin,
                    lynette_bin=lynette_bin,
                    model=model,
                    reasoning_effort=reasoning_effort,
                    reasoning_summary="detailed",
                    show_raw_agent_reasoning=True,
                    timeout_seconds=timeout_seconds,
                    skill_text=(
                        skill_text
                        if condition_skill_present and skill_dir is None
                        else None
                    ),
                    skill_dir=skill_dir if condition_skill_present else None,
                    model_context_window=model_context_window,
                    contract_profile=actor_contract_profile,
                    condition_skill_sha256=skill_sha256,
                    stage="fixed_test20_evaluation",
                )
                result.update(
                    {
                        "id": item["id"],
                        "task_id": item["task_id"],
                        "project_code": item["project_code"],
                        "claude_failed": bool(item["claude_failed"]),
                        "actor_model": model,
                        "actor_harness": "codex-cli-native-responses",
                        "actor_reasoning_effort": reasoning_effort,
                        "actor_contract_profile": actor_contract_profile,
                        "condition_skill_present": condition_skill_present,
                        "fidelity_class": _local_fidelity(result),
                        "task_attempt_index": attempt_index,
                        "skill_sha256": skill_sha256,
                    }
                )
                _write_json(task_dir / "result.json", result)
                return result
            except Exception as error:
                last_error = f"{type(error).__name__}: {error}"
            if attempt_index < 3 and task_dir.exists() and any(task_dir.iterdir()):
                _archive_attempt(task_dir, attempt_index)
        task_dir.mkdir(parents=True, exist_ok=True)
        fallback = {
            "id": item["id"],
            "task_id": item["task_id"],
            "project_code": item["project_code"],
            "claude_failed": bool(item["claude_failed"]),
            "status": "UNSOLVED",
            "actor_model": model,
            "actor_harness": "codex-cli-native-responses",
            "actor_reasoning_effort": reasoning_effort,
            "actor_contract_profile": actor_contract_profile,
            "condition_skill_present": condition_skill_present,
            "fidelity_class": "V0_INVALID",
            "task_attempt_index": 3,
            "skill_sha256": skill_sha256,
            "fail_reason": last_error,
        }
        _write_json(task_dir / "result.json", fallback)
        return fallback

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(execute, item): item for item in items}
        for future in as_completed(futures):
            results.append(future.result())
    by_id = {str(result["id"]): result for result in results}
    return [by_id[str(item["id"])] for item in items]


def _attach_item_metadata(
    results: list[dict[str, Any]], items: list[dict[str, Any]]
) -> None:
    items_by_id = {str(item["id"]): item for item in items}
    for result in results:
        item = items_by_id.get(str(result.get("id") or ""))
        if item is None:
            raise ValueError(f"result has unknown test item id: {result.get('id')}")
        result.update(
            {
                "task_id": item["task_id"],
                "project_code": item["project_code"],
                "claude_failed": bool(item["claude_failed"]),
            }
        )


def _bridge_ledger_usage(path: Path) -> tuple[dict[str, int], float]:
    attempts = []
    ledger_text = path.read_text(encoding="utf-8") if path.is_file() else ""
    for line in ledger_text.splitlines():
        if line.strip():
            attempts.extend(json.loads(line).get("attempts") or [])
    usage = {
        "requests": len(attempts),
        **{
            key: sum(int((attempt.get("usage") or {}).get(key, 0) or 0) for attempt in attempts)
            for key in (
                "prompt_tokens",
                "prompt_cache_hit_tokens",
                "prompt_cache_miss_tokens",
                "completion_tokens",
                "reasoning_tokens",
            )
        },
    }
    cost = sum(float(attempt.get("estimated_cost_usd", 0.0) or 0.0) for attempt in attempts)
    return usage, cost


def _summarize(
    results: list[dict[str, Any]],
    *,
    transport: str,
    model: str,
    bridge_ledger: Path | None = None,
) -> dict[str, Any]:
    if transport == "direct":
        usage_rows = [(row.get("fidelity") or {}).get("usage") or {} for row in results]
        usage = {
            key: sum(int(row.get(key, 0) or 0) for row in usage_rows)
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
            )
        }
        estimated_cost = 0.0
        trace_complete = lambda row: fidelity_class(row) in TRACE_COMPLETE_CLASSES  # noqa: E731
    else:
        usage_rows = [row.get("usage") or {} for row in results]
        retained_usage = {
            key: sum(int(row.get(key, 0) or 0) for row in usage_rows)
            for key in (
                "requests",
                "prompt_tokens",
                "prompt_cache_hit_tokens",
                "prompt_cache_miss_tokens",
                "completion_tokens",
                "reasoning_tokens",
            )
        }
        retained_cost = sum(
            float(row.get("estimated_cost_usd", 0.0) or 0.0) for row in usage_rows
        )
        if bridge_ledger is not None:
            usage, estimated_cost = _bridge_ledger_usage(bridge_ledger)
            cost_basis = "complete bridge ledger including archived attempts"
        else:
            usage, estimated_cost = retained_usage, retained_cost
            cost_basis = "retained task results"
        trace_complete = lambda row: fidelity_class(row) in TRACE_COMPLETE_CLASSES  # noqa: E731
    fidelity_counts = {
        fidelity: sum(fidelity_class(row) == fidelity for row in results)
        for fidelity in ("V0_INVALID", "V1_TRUNCATED", "V2_TRACE")
    }
    valid = sum(trace_complete(row) for row in results)
    solved = sum(proof_solved(row) for row in results)
    summary = {
        "status": "complete",
        "finished_at": _now(),
        "model": model,
        "test_n": len(results),
        "solved": solved,
        "claude_failed_n": sum(bool(row.get("claude_failed")) for row in results),
        "claude_failed_solved": sum(
            bool(row.get("claude_failed"))
            and proof_solved(row)
            for row in results
        ),
        "timeouts": sum(bool(row.get("timed_out")) for row in results),
        "timeout_solved": sum(
            bool(row.get("timed_out")) and proof_solved(row) for row in results
        ),
        "within_budget_solved": sum(
            within_budget(row) and proof_solved(row) for row in results
        ),
        "valid_results": valid,
        "trace_complete_results": valid,
        "trace_incomplete_results": len(results) - valid,
        "trace_status": "complete" if valid == len(results) else "partial",
        "fidelity_counts": fidelity_counts,
        "v0_solved_included": sum(
            not trace_complete(row) and proof_solved(row) for row in results
        ),
        "invalid_solved_excluded": 0,
        "usage": usage,
        "estimated_api_cost_usd": estimated_cost,
        "cost_basis": "local quota" if transport == "direct" else cost_basis,
        "usage_scope": (
            "retained task attempts; archived direct attempts are not included"
            if transport == "direct"
            else "complete bridge ledger including archived attempts"
            if bridge_ledger is not None
            else "retained task attempts"
        ),
        "archived_attempt_usage_included": bool(
            transport == "bridge" and bridge_ledger is not None
        ),
        "retained_task_wall_seconds_sum": sum(
            float(row.get("wall_seconds", 0.0) or 0.0) for row in results
        ),
        "retained_actor_wall_seconds_sum": sum(
            float(row.get("actor_wall_seconds", 0.0) or 0.0) for row in results
        ),
        "retained_final_validation_wall_seconds_sum": sum(
            float(row.get("final_validation_wall_seconds", 0.0) or 0.0)
            for row in results
        ),
    }
    if transport == "bridge" and bridge_ledger is not None:
        summary["retained_task_estimated_api_cost_usd"] = retained_cost
        summary["archived_or_replaced_attempt_cost_usd"] = max(
            0.0, estimated_cost - retained_cost
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--split-dir", type=Path, required=True)
    skill_group = parser.add_mutually_exclusive_group(required=True)
    skill_group.add_argument("--skill-file", type=Path)
    skill_group.add_argument("--skill-dir", type=Path)
    parser.add_argument("--skill-label", required=True)
    parser.add_argument("--expected-skill-sha256", required=True)
    parser.add_argument("--codex-bin", type=Path, required=True)
    parser.add_argument("--verus-bin", type=Path, required=True)
    parser.add_argument("--lynette-bin", type=Path, required=True)
    parser.add_argument("--transport", choices=("direct", "bridge"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", default="max")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--model-context-window", type=int, default=262144)
    parser.add_argument(
        "--actor-contract-profile",
        choices=("project", "cross_provider_20260819"),
        default="project",
    )
    parser.add_argument("--codex-provider-id", default="deepseek_bridge")
    parser.add_argument("--bridge-url")
    parser.add_argument("--bridge-ledger", type=Path)
    parser.add_argument("--bridge-manifest", type=Path)
    parser.add_argument("--actor-isolation-scratch-root", type=Path)
    parser.add_argument("--actor-isolation-verus-root", type=Path)
    parser.add_argument("--actor-isolation-rust-root", type=Path)
    parser.add_argument(
        "--actor-isolation-forbidden-path", type=Path, action="append", default=[]
    )
    parser.add_argument("--item-id", action="append", default=[])
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    split_dir = args.split_dir.resolve()
    os.chdir(split_dir.parent)
    items, split_manifest = _load_test_items(split_dir)
    items = _select_test_items(items, args.item_id)
    skill_path = args.skill_file if args.skill_file is not None else args.skill_dir
    assert skill_path is not None
    skill_artifact = _load_skill_artifact(skill_path, args.expected_skill_sha256)
    skill_text = skill_artifact.entrypoint_text
    skill_sha256 = skill_artifact.artifact_sha256
    if args.skill_dir is not None and args.skill_label == "blank":
        raise ValueError("a skill bundle cannot use the reserved blank label")
    condition_skill_present = args.skill_label != "blank"
    prompt = (
        build_cross_provider_prompt(
            skill_present=condition_skill_present,
            verus_bin=args.verus_bin,
            lynette_bin=args.lynette_bin,
        )
        if args.actor_contract_profile == "cross_provider_20260819"
        else build_prompt()
    )
    for binary in (args.codex_bin, args.verus_bin, args.lynette_bin):
        if not binary.resolve().is_file():
            raise ValueError(f"required executable does not exist: {binary.resolve()}")
    verus_identity = require_formal_verus(args.verus_bin)
    isolation_values = (
        args.actor_isolation_scratch_root,
        args.actor_isolation_verus_root,
        args.actor_isolation_rust_root,
    )
    if any(value is not None for value in isolation_values) and not all(
        value is not None for value in isolation_values
    ):
        raise ValueError("actor isolation requires scratch, Verus, and Rust roots")
    actor_isolation_check: dict[str, Any] = {"requested": False, "mode": "none"}
    if args.transport == "bridge":
        if not all((args.bridge_url, args.bridge_ledger, args.bridge_manifest)):
            raise ValueError("bridge transport requires URL, ledger, and manifest")
        bridge_manifest = json.loads(args.bridge_manifest.read_text(encoding="utf-8"))
        if bridge_manifest.get("fake_mode") or bridge_manifest.get("model") != args.model:
            raise ValueError("bridge manifest is fake or has the wrong model")
        if all(value is not None for value in isolation_values):
            bridge_port = urlparse(args.bridge_url).port
            if bridge_port is None:
                raise ValueError("actor isolation bridge URL requires an explicit port")
            isolation = ActorIsolationConfig(
                scratch_root=args.actor_isolation_scratch_root,
                verus_root=args.actor_isolation_verus_root,
                rust_root=args.actor_isolation_rust_root,
                bridge_port=bridge_port,
                forbidden_paths=tuple(args.actor_isolation_forbidden_path),
            )
            isolation.validate(
                workspace=args.actor_isolation_scratch_root / ".actor-preflight",
                codex_bin=args.codex_bin,
                lynette_bin=args.lynette_bin,
            )
            host_preflight = isolation_preflight()
            if not host_preflight["supported"]:
                raise ValueError(f"actor isolation preflight failed: {host_preflight}")
            actor_isolation_check = {
                **isolation.manifest(),
                "host_preflight": host_preflight,
            }
    elif any(value is not None for value in isolation_values):
        raise ValueError("actor isolation currently requires bridge transport")

    check = {
        "status": "ok",
        "test_n": len(items),
        "test_manifest_sha256": sha256_file(split_dir / "test" / "items.json"),
        "split_sha256": split_manifest["split_sha256"],
        "known_verus_version_sensitive_item_ids": [
            str(item["id"])
            for item in items
            if str(item["id"]) in KNOWN_VERUS_VERSION_SENSITIVE_ITEM_IDS
        ],
        "version_sensitive_item_scoring": "included unchanged; selected verifier outcome counts toward solved denominator",
        "skill_label": args.skill_label,
        "skill_sha256": skill_sha256,
        "skill_bytes": int(skill_artifact.manifest()["total_bytes"]),
        "skill_artifact": skill_artifact.manifest(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "transport": args.transport,
        "model": args.model,
        "actor_contract_profile": args.actor_contract_profile,
        "condition_skill_present": condition_skill_present,
        "codex_provider_id": args.codex_provider_id,
        "workers": args.workers,
        "timeout_seconds": args.timeout_seconds,
        "model_context_window": args.model_context_window,
        "actor_isolation": actor_isolation_check,
        "verus_identity": verus_identity,
    }
    if args.check_only:
        print(json.dumps(check, ensure_ascii=False, indent=2))
        return
    if args.run_dir is None:
        raise ValueError("--run-dir is required unless --check-only is used")
    run_dir = _require_run_dir(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    execution_skill_dir: Path | None = None
    if skill_artifact.source_dir is not None:
        frozen_skill_dir = run_dir / "condition_skill"
        shutil.copytree(skill_artifact.source_dir, frozen_skill_dir)
        execution_skill_dir = _load_skill_artifact(
            frozen_skill_dir, skill_sha256
        ).source_dir
    contract = {
        **check,
        "created_at": _now(),
        "status": "RUNNING",
        "purpose": "one-pass recurring test-20 evaluation under the fixed baseline contract",
        "test_ids": [item["id"] for item in items],
        "reasoning_effort": args.reasoning_effort,
        "valid_timeout_retries": 0,
        "runner_exception_retries": 2,
        "fidelity_triggered_retries": 0,
        "hard_metric": "independent Verus pass AND Lynette proof-only pass AND input/skill safety",
        "reference_proof_injected": False,
        "prior_trajectory_injected": False,
        "filesystem_visibility_enforced": bool(
            actor_isolation_check.get("requested")
        ),
        "leakage_scope": (
            "actor filesystem allowlist enforced"
            if actor_isolation_check.get("requested")
            else "prompt/workspace inputs controlled; external filesystem reads not enforced"
        ),
        "claim_scope": (
            "leakage-controlled recurring benchmark"
            if actor_isolation_check.get("requested")
            else "diagnostic recurring benchmark; not leakage-safe"
        ),
        "cost_cap_usd": None,
        "raw_data_read_only": True,
    }
    _write_json(run_dir / "run_contract.json", contract)

    if args.transport == "direct":
        results = _run_direct(
            items=items,
            out_dir=run_dir,
            skill_text=skill_text,
            skill_dir=execution_skill_dir,
            skill_sha256=skill_sha256,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            codex_bin=args.codex_bin.resolve(),
            verus_bin=args.verus_bin.resolve(),
            lynette_bin=args.lynette_bin.resolve(),
            workers=args.workers,
            timeout_seconds=args.timeout_seconds,
            model_context_window=args.model_context_window,
            actor_contract_profile=args.actor_contract_profile,
            condition_skill_present=condition_skill_present,
        )
    else:
        adapter = CodexDeepSeekAdapter(
            split_dir=str(split_dir),
            codex_bin=str(args.codex_bin),
            verus_bin=str(args.verus_bin),
            lynette_bin=str(args.lynette_bin),
            bridge_url=str(args.bridge_url),
            bridge_ledger_path=str(args.bridge_ledger),
            bridge_manifest_path=str(args.bridge_manifest),
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            workers=args.workers,
            analyst_workers=1,
            task_retries=2,
            timeout_retries=0,
            codex_timeout_seconds=args.timeout_seconds,
            max_codex_timeout_seconds=args.timeout_seconds,
            model_context_window=args.model_context_window,
            fail_on_invalid=False,
            seed=42,
            actor_contract_profile=args.actor_contract_profile,
            condition_skill_present=condition_skill_present,
            codex_provider_id=args.codex_provider_id,
            run_stage="fixed_test20_evaluation",
            actor_isolation_scratch_root=(
                str(args.actor_isolation_scratch_root)
                if args.actor_isolation_scratch_root
                else None
            ),
            actor_isolation_verus_root=(
                str(args.actor_isolation_verus_root)
                if args.actor_isolation_verus_root
                else None
            ),
            actor_isolation_rust_root=(
                str(args.actor_isolation_rust_root)
                if args.actor_isolation_rust_root
                else None
            ),
            actor_isolation_forbidden_paths=tuple(
                str(path) for path in args.actor_isolation_forbidden_path
            ),
            condition_skill_dir=(
                str(execution_skill_dir)
                if execution_skill_dir is not None
                else None
            ),
        )
        adapter.setup({"out_root": str(run_dir)})
        results = adapter.rollout(items, skill_text, str(run_dir))

    _attach_item_metadata(results, items)
    _write_json(run_dir / "per_task.json", results)
    summary = _summarize(
        results,
        transport=args.transport,
        model=args.model,
        bridge_ledger=args.bridge_ledger if args.transport == "bridge" else None,
    )
    _write_json(run_dir / "summary.json", summary)
    contract["status"] = summary["status"]
    contract["finished_at"] = summary["finished_at"]
    _write_json(run_dir / "run_contract.json", contract)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
