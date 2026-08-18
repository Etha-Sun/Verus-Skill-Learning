#!/usr/bin/env python3
"""Materialize and validate one frozen candidate schedule sequentially."""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
REPO = EXPERIMENT.parent
BASELINE_CODE = REPO / "trace2skill_verusage_baseline_test" / "code"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BASELINE_CODE))

from global_skill_experiment.candidates import (  # noqa: E402
    CandidateSchedule,
    CandidateUnit,
    load_candidate_schedule,
    run_candidate_sequence,
)
from global_skill_experiment.gate import (  # noqa: E402
    CandidateSnapshot,
    CommandAggregateEvaluator,
    GateConfig,
    HeldOutGateController,
    hash_skill_tree,
)
from global_skill_experiment.materialization import (  # noqa: E402
    materialize_candidate_unit,
    parse_semantic_unit,
)
from react_agent.models import OpenAIClient  # noqa: E402
from run_actor_matrix import (  # noqa: E402
    BRIDGE_SOURCE,
    DEFAULT_CODEX,
    DEFAULT_ENV_FILE,
    DEFAULT_LYNETTE,
    DEFAULT_RUST_ROOT,
    DEFAULT_RUN_ROOT,
    DEFAULT_VERUS,
    EXPECTED_CODEX_VERSION,
    assert_strict_child,
    load_nonsecret_env,
    start_bridge,
    stop_process_group,
)
from skill_evolver.parallel_evolving_agent import ParallelSkillEvolver  # noqa: E402


MODEL = "deepseek-v4-pro"
TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 8192
MAX_WORKERS = 2
MAX_TRANSLATION_ATTEMPTS_PER_ITEM = 5


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def actor_argv(args: argparse.Namespace, *, resume: bool) -> list[str]:
    command = [
        sys.executable,
        str(args.actor_runner.resolve()),
        "--execute",
        "--split",
        "val",
        "--condition",
        "skill",
        "--skill-dir",
        "{skill_dir}",
        "--output-root",
        "{output_dir}",
        "--run-root",
        str(args.run_root.resolve()),
        "--env-file",
        str(args.env_file.resolve()),
        "--codex-bin",
        str(args.codex_bin.resolve()),
        "--verus-bin",
        str(args.verus_bin.resolve()),
        "--rust-root",
        str(args.rust_root.resolve()),
        "--lynette-bin",
        str(args.lynette_bin.resolve()),
        "--expected-codex-version",
        args.expected_codex_version,
        "--timeout-seconds",
        str(args.actor_timeout_seconds),
        "--verification-timeout-seconds",
        str(args.verification_timeout_seconds),
        "--proxy-port",
        str(args.actor_proxy_port),
        "--budget-state-path",
        str(args.budget_state_path.resolve()),
        "--approval-limit-usd",
        str(args.approval_limit_usd),
        "--prior-spend-usd",
        str(args.prior_spend_usd),
        "--request-reserve-usd",
        str(args.request_reserve_usd),
    ]
    if resume:
        command.append("--resume")
    return command


def translation_item_count(schedule: CandidateSchedule) -> int:
    count = 0
    for unit in schedule.units:
        if unit.payload_format == "semantic-patch-markdown-v1":
            count += len(parse_semantic_unit(unit.payload_path).items)
    return count


def preflight_payload(
    args: argparse.Namespace,
    schedule: CandidateSchedule,
) -> dict[str, Any]:
    gate = GateConfig(enabled=True, expected_task_count=20)
    translation_items = translation_item_count(schedule)
    payload: dict[str, Any] = {
        "schema_version": "gated-candidate-sequence-preflight-v1",
        "status": "proposed_no_network",
        "network_requests": 0,
        "implementation": {
            "sequence_runner": {
                "path": str(Path(__file__).resolve()),
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "candidate_lineage": {
                "path": str((HERE / "global_skill_experiment" / "candidates.py").resolve()),
                "sha256": sha256_file(
                    (HERE / "global_skill_experiment" / "candidates.py").resolve()
                ),
            },
            "gate": {
                "path": str((HERE / "global_skill_experiment" / "gate.py").resolve()),
                "sha256": sha256_file(
                    (HERE / "global_skill_experiment" / "gate.py").resolve()
                ),
            },
            "materialization": {
                "path": str(
                    (HERE / "global_skill_experiment" / "materialization.py").resolve()
                ),
                "sha256": sha256_file(
                    (HERE / "global_skill_experiment" / "materialization.py").resolve()
                ),
            },
            "parallel_evolver": {
                "path": str(
                    (BASELINE_CODE / "skill_evolver" / "parallel_evolving_agent.py").resolve()
                ),
                "sha256": sha256_file(
                    (BASELINE_CODE / "skill_evolver" / "parallel_evolving_agent.py").resolve()
                ),
            },
            "translation_client": {
                "path": str((BASELINE_CODE / "react_agent" / "models.py").resolve()),
                "sha256": sha256_file(
                    (BASELINE_CODE / "react_agent" / "models.py").resolve()
                ),
            },
            "bridge": {
                "path": str(BRIDGE_SOURCE.resolve()),
                "sha256": sha256_file(BRIDGE_SOURCE.resolve()),
            },
        },
        "schedule": {
            "path": str(schedule.path),
            "schedule_id": schedule.schedule_id,
            "sha256": schedule.digest,
            "construction_method": schedule.construction_method,
            "unit_type": schedule.unit_type,
            "unit_count": len(schedule.units),
            "m_core_sha256": schedule.m_core_sha256,
            "shared_memories_sha256": schedule.shared_memories_sha256,
        },
        "output_contract": {
            "output_root": str(args.output_root.resolve()),
            "run_root": str(args.run_root.resolve()),
            "candidate_root": str((args.output_root / "candidates").resolve()),
            "actor_output_root": str((args.output_root / "actor").resolve()),
            "gate_history_path": str((args.output_root / "gate_history.json").resolve()),
            "private_evaluation_cache_path": str(
                args.shared_evaluation_cache.resolve()
            ),
        },
        "gate_config": asdict(gate),
        "actor": {
            "runner": str(args.actor_runner.resolve()),
            "runner_sha256": sha256_file(args.actor_runner.resolve()),
            "model": MODEL,
            "reasoning_effort": "high",
            "split": "val",
            "task_count_per_snapshot": 20,
            "candidate_snapshot_count": len(schedule.units),
            "candidate_actor_task_runs": 20 * len(schedule.units),
            "m_core_evaluation_is_shared_by_snapshot_hash": True,
            "m_core_evaluated_before_candidate_materialization": True,
            "timeout_seconds_per_task": args.actor_timeout_seconds,
            "command_timeout_seconds": args.actor_command_timeout_seconds,
            "fresh_argv": actor_argv(args, resume=False),
            "resume_argv": actor_argv(args, resume=True),
        },
        "translation": {
            "model": MODEL,
            "wire_api": "responses",
            "temperature": TEMPERATURE,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_workers": MAX_WORKERS,
            "seed": None,
            "semantic_item_count": translation_items,
            "max_attempts_per_item": MAX_TRANSLATION_ATTEMPTS_PER_ITEM,
            "max_provider_attempts": (
                translation_items * MAX_TRANSLATION_ATTEMPTS_PER_ITEM
            ),
            "programmatic_apply_llm_calls": 0,
            "proxy_port": args.translation_proxy_port,
            "cache_path": str(
                (args.output_root / "translation_cache.diskcache").resolve()
            ),
        },
        "shared_provider_budget": {
            "covers_actor_and_translation": True,
            "state_path": str(args.budget_state_path.resolve()),
            "approval_limit_usd": args.approval_limit_usd,
            "prior_spend_usd": args.prior_spend_usd,
            "request_reserve_usd": args.request_reserve_usd,
        },
        "resume_contract": {
            "reuse_complete_actor_summary_without_command": True,
            "resume_incomplete_actor_output_with_actor_resume_flag": True,
            "reuse_materialized_candidate_only_after_full_lineage_hash_audit": True,
            "reuse_gate_decision_only_after_snapshot_hash_match": True,
            "incomplete_candidate_materialization_is_a_hard_error": True,
        },
    }
    payload["preflight_sha256"] = canonical_sha256(payload)
    return payload


def validate_args(args: argparse.Namespace) -> None:
    if args.model != MODEL:
        raise ValueError(f"candidate sequence requires {MODEL}")
    if args.temperature != TEMPERATURE or args.max_tokens != MAX_OUTPUT_TOKENS:
        raise ValueError("candidate sequence requires temperature=0.2 and max_tokens=8192")
    if args.max_workers != MAX_WORKERS:
        raise ValueError("candidate sequence requires max_workers=2")
    if (
        args.actor_timeout_seconds <= 0
        or args.actor_command_timeout_seconds <= 0
        or args.verification_timeout_seconds <= 0
    ):
        raise ValueError("timeouts must be positive")
    if args.actor_command_timeout_seconds < 20 * args.actor_timeout_seconds:
        raise ValueError("actor command timeout cannot be below the 20-task timeout sum")
    if args.actor_proxy_port == args.translation_proxy_port:
        raise ValueError("actor and translation proxy ports must differ")
    if (
        args.approval_limit_usd <= 0
        or args.prior_spend_usd < 0
        or args.request_reserve_usd <= 0
    ):
        raise ValueError("provider budget values are invalid")
    assert_strict_child(args.output_root, args.run_root)
    assert_strict_child(args.shared_evaluation_cache, args.run_root)
    assert_strict_child(args.budget_state_path, args.run_root)


def make_materializer(
    args: argparse.Namespace,
    schedule: CandidateSchedule,
    translation_base_url: str,
):
    cache_path = args.output_root / "translation_cache.diskcache"

    def materializer(
        incumbent: CandidateSnapshot,
        unit: CandidateUnit,
        candidate_root: Path,
    ) -> CandidateSnapshot:
        task_url = f"{translation_base_url}/tasks/translate--{unit.unit_id}/v1"
        client = OpenAIClient(
            model=MODEL,
            api_key="budget-enforced-local-bridge",
            base_url=task_url,
            cache_path=str(cache_path),
            generation_config={},
            retry_times=(5, 10, 30, 60),
            timeout=1800,
            wire_api="responses",
        )
        evolver = ParallelSkillEvolver(
            client=client,
            skill_dir=incumbent.skill_dir,
            batch_size=5,
            merge_batch_size=5,
            max_workers=MAX_WORKERS,
            max_merge_levels=5,
            temperature=TEMPERATURE,
            max_tokens=MAX_OUTPUT_TOKENS,
            verbose=True,
            dry_run=False,
            output_dir=candidate_root / "application_artifacts",
            max_skill_lines=500,
            max_references=(
                256 if schedule.construction_method == "semantic-reduce" else 5
            ),
            patch_pipeline="markdown",
            semantic_item_marker_format="bracket",
        )
        return materialize_candidate_unit(
            incumbent=incumbent,
            unit=unit,
            output_root=candidate_root,
            m_core_hash=schedule.m_core_sha256,
            evolver=evolver,
        )

    return materializer


def execute(
    args: argparse.Namespace,
    schedule: CandidateSchedule,
    preflight: dict[str, Any],
) -> int:
    approved = args.approved_preflight_sha256
    if approved != preflight["preflight_sha256"]:
        raise ValueError(
            "--approved-preflight-sha256 must exactly match the current preflight"
        )
    stored_path = args.output_root / "sequence_preflight.json"
    if not stored_path.is_file():
        raise FileNotFoundError("execute requires a previously written sequence preflight")
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    if stored != preflight:
        raise ValueError("stored sequence preflight differs from current configuration")

    initial = CandidateSnapshot(
        candidate_id="m-core",
        skill_dir=schedule.m_core_path,
        construction_method="semantic-v4-root",
        unit_type="m-core",
    )
    evaluator = CommandAggregateEvaluator(
        argv=actor_argv(args, resume=False),
        resume_argv=actor_argv(args, resume=True),
        output_root=args.output_root / "actor",
        summary_relative_path="summary.json",
        timeout_seconds=args.actor_command_timeout_seconds,
    )
    controller = HeldOutGateController(
        GateConfig(enabled=True, expected_task_count=20),
        evaluator,
        m_core_snapshot=initial,
        history_path=args.output_root / "gate_history.json",
        evaluation_cache_path=args.shared_evaluation_cache,
    )

    # Freeze the common baseline score before any candidate is translated or applied.
    controller.evaluate_m_core()

    missing_semantic = any(
        unit.payload_format == "semantic-patch-markdown-v1"
        and not (args.output_root / "candidates" / f"{unit.order:04d}_{unit.unit_id}").exists()
        for unit in schedule.units
    )
    bridge = None
    translation_root = args.output_root / "translation_provider"
    translation_base_url = f"http://127.0.0.1:{args.translation_proxy_port}"
    try:
        if missing_semantic:
            translation_root.mkdir(parents=True, exist_ok=True)
            env = load_nonsecret_env(args.env_file.resolve(), execute=True)
            bridge = start_bridge(
                translation_root,
                env,
                args.translation_proxy_port,
                fake=False,
                budget_state_path=args.budget_state_path.resolve(),
                approval_limit_usd=args.approval_limit_usd,
                prior_spend_usd=args.prior_spend_usd,
                request_reserve_usd=args.request_reserve_usd,
            )
        final, decisions = run_candidate_sequence(
            schedule=schedule,
            initial_snapshot=initial,
            controller=controller,
            materializer=make_materializer(
                args, schedule, translation_base_url
            ),
            output_root=args.output_root / "candidates",
        )
    finally:
        if bridge is not None:
            stop_process_group(bridge)

    result = {
        "schema_version": "gated-candidate-sequence-result-v1",
        "status": "complete",
        "preflight_sha256": preflight["preflight_sha256"],
        "schedule_sha256": schedule.digest,
        "construction_method": schedule.construction_method,
        "decision_count": len(decisions),
        "accepted_count": sum(decision.accepted for decision in decisions),
        "final_candidate_id": final.candidate_id,
        "final_skill_dir": str(final.skill_dir.resolve()),
        "final_skill_sha256": hash_skill_tree(final.skill_dir),
        "shared_budget_state_path": str(args.budget_state_path.resolve()),
    }
    write_json(args.output_root / "sequence_result.json", result)
    print(json.dumps(result, indent=2), flush=True)
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    result.add_argument("--schedule", type=Path, required=True)
    result.add_argument("--output-root", type=Path, required=True)
    result.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    result.add_argument("--shared-evaluation-cache", type=Path, required=True)
    result.add_argument("--budget-state-path", type=Path, required=True)
    result.add_argument("--approval-limit-usd", type=float, default=20.0)
    result.add_argument("--prior-spend-usd", type=float, default=0.0)
    result.add_argument("--request-reserve-usd", type=float, default=0.25)
    result.add_argument("--approved-preflight-sha256")
    result.add_argument("--actor-runner", type=Path, default=HERE / "run_actor_matrix.py")
    result.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    result.add_argument("--codex-bin", type=Path, default=DEFAULT_CODEX)
    result.add_argument("--verus-bin", type=Path, default=DEFAULT_VERUS)
    result.add_argument("--rust-root", type=Path, default=DEFAULT_RUST_ROOT)
    result.add_argument("--lynette-bin", type=Path, default=DEFAULT_LYNETTE)
    result.add_argument("--expected-codex-version", default=EXPECTED_CODEX_VERSION)
    result.add_argument("--actor-timeout-seconds", type=int, default=900)
    result.add_argument("--actor-command-timeout-seconds", type=int, default=21600)
    result.add_argument("--verification-timeout-seconds", type=int, default=120)
    result.add_argument("--actor-proxy-port", type=int, default=4017)
    result.add_argument("--translation-proxy-port", type=int, default=4018)
    result.add_argument("--model", default=MODEL)
    result.add_argument("--temperature", type=float, default=TEMPERATURE)
    result.add_argument("--max-tokens", type=int, default=MAX_OUTPUT_TOKENS)
    result.add_argument("--max-workers", type=int, default=MAX_WORKERS)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_args(args)
    schedule = load_candidate_schedule(args.schedule)
    preflight = preflight_payload(args, schedule)
    if args.preflight:
        if args.approved_preflight_sha256 is not None:
            raise ValueError("preflight does not accept an approved hash")
        write_json(args.output_root / "sequence_preflight.json", preflight)
        print(json.dumps(preflight, indent=2), flush=True)
        return 0
    if args.approved_preflight_sha256 is None:
        raise ValueError("execute requires --approved-preflight-sha256")

    def terminate_cleanly(signum: int, _frame: Any) -> None:
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate_cleanly)
    signal.signal(signal.SIGINT, terminate_cleanly)
    return execute(args, schedule, preflight)


if __name__ == "__main__":
    raise SystemExit(main())
