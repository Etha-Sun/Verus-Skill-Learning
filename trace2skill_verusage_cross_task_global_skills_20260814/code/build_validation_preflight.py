#!/usr/bin/env python3
"""Freeze validation/test call counts and conservative planning bounds."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
REPO = EXPERIMENT.parent
BASELINE_CODE = REPO / "trace2skill_verusage_baseline_test" / "code"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BASELINE_CODE))

from global_skill_experiment.candidates import (  # noqa: E402
    load_candidate_schedule,
    sha256_file,
)
from global_skill_experiment.materialization import parse_semantic_unit  # noqa: E402
from verus_agent.codex_harness.upstream_skillopt.budget_guard import (  # noqa: E402
    rates_for_model,
)


MODEL = "deepseek-v4-pro"
ACTOR_MAX_OUTPUT_TOKENS = 8192
TRANSLATION_MAX_ATTEMPTS_PER_ITEM = 5


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def elapsed_seconds(task: dict[str, Any]) -> float:
    if "wall_time_seconds" in task:
        return float(task["wall_time_seconds"])
    started = datetime.fromisoformat(str(task["started_at"]).replace("Z", "+00:00"))
    finished = datetime.fromisoformat(str(task["finished_at"]).replace("Z", "+00:00"))
    return (finished - started).total_seconds()


def prior_baseline(path: Path, rates: dict[str, float]) -> dict[str, Any]:
    value = read_object(path)
    tasks = value.get("tasks")
    usage = value.get("usage")
    if not isinstance(tasks, list) or not tasks or not isinstance(usage, dict):
        raise ValueError(f"prior planning summary is incomplete: {path}")
    count = len(tasks)
    hit = int(usage.get("prompt_cache_hit_tokens", 0) or 0)
    miss = int(usage.get("prompt_cache_miss_tokens", 0) or 0)
    output = int(usage.get("completion_tokens", 0) or 0)
    total = int(usage.get("total_tokens", hit + miss + output) or 0)
    reasoning = int(usage.get("reasoning_tokens", 0) or 0)
    requests = int(usage.get("request_count", 0) or 0)
    wall = sum(elapsed_seconds(task) for task in tasks)
    cost = (
        hit * rates["prompt_cache_hit_tokens"]
        + miss * rates["prompt_cache_miss_tokens"]
        + output * rates["completion_tokens"]
    ) / 1_000_000
    return {
        "summary_path": str(path.resolve()),
        "summary_sha256": sha256_file(path),
        "task_count": count,
        "aggregate_only": {
            "provider_request_count": requests,
            "provider_total_tokens": total,
            "primary_uncached_tokens": miss + output,
            "reasoning_tokens": reasoning,
            "wall_time_seconds": round(wall, 6),
            "estimated_cost_usd": round(cost, 8),
        },
        "per_task": {
            "provider_request_count": requests / count,
            "provider_total_tokens": total / count,
            "primary_uncached_tokens": (miss + output) / count,
            "reasoning_tokens": reasoning / count,
            "wall_time_seconds": wall / count,
            "estimated_cost_usd": cost / count,
        },
    }


def scaled_projection(per_task: dict[str, float], task_runs: int) -> dict[str, Any]:
    integer_fields = {
        "provider_request_count",
        "provider_total_tokens",
        "primary_uncached_tokens",
        "reasoning_tokens",
    }
    result: dict[str, Any] = {}
    for key, value in per_task.items():
        scaled = float(value) * task_runs
        result[key] = int(round(scaled)) if key in integer_fields else round(scaled, 8)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-schedule", type=Path, required=True)
    parser.add_argument("--semantic-schedule", type=Path, required=True)
    parser.add_argument("--no-skill-actor-manifest", type=Path, required=True)
    parser.add_argument("--m-core-actor-manifest", type=Path, required=True)
    parser.add_argument("--native-sequence-preflight", type=Path, required=True)
    parser.add_argument("--semantic-sequence-preflight", type=Path, required=True)
    parser.add_argument("--prior-summary", type=Path, action="append", default=[])
    parser.add_argument("--validation-task-count", type=int, default=20)
    parser.add_argument("--test-task-count", type=int, default=20)
    parser.add_argument("--test-arm-count", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--actor-approval-limit-usd", type=float, default=20.0)
    parser.add_argument("--prior-spend-usd", type=float, default=0.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if min(
        args.validation_task_count,
        args.test_task_count,
        args.test_arm_count,
        args.timeout_seconds,
    ) <= 0:
        parser.error("task counts, arm count, and timeout must be positive")
    if args.actor_approval_limit_usd <= 0:
        parser.error("--actor-approval-limit-usd must be positive")
    if not 0 <= args.prior_spend_usd < args.actor_approval_limit_usd:
        parser.error(
            "--prior-spend-usd must be nonnegative and below the approval limit"
        )

    native = load_candidate_schedule(args.native_schedule)
    semantic = load_candidate_schedule(args.semantic_schedule)
    if native.construction_method != "native-compressed" or len(native.units) != 1:
        raise ValueError("native schedule must contain exactly one compressed unit")
    if semantic.construction_method != "semantic-reduce" or not semantic.units:
        raise ValueError("semantic schedule must contain semantic family units")
    if native.m_core_sha256 != semantic.m_core_sha256:
        raise ValueError("candidate schedules do not share the same M-core")
    if native.shared_memories_sha256 != semantic.shared_memories_sha256:
        raise ValueError("candidate schedules do not share the same memories")
    if native.construction.get("map_artifact_sha256") != semantic.construction.get(
        "map_artifact_sha256"
    ):
        raise ValueError("candidate schedules do not share the same MAP artifact")

    no_skill_manifest = read_object(args.no_skill_actor_manifest)
    m_core_manifest = read_object(args.m_core_actor_manifest)
    for label, manifest, condition in (
        ("no-skill", no_skill_manifest, "no-skill"),
        ("m-core", m_core_manifest, "skill"),
    ):
        if manifest.get("status") != "preflight" or manifest.get("split") != "val":
            raise ValueError(f"{label} actor manifest is not a validation preflight")
        if manifest.get("condition") != condition:
            raise ValueError(f"{label} actor manifest has the wrong condition")
        if manifest.get("selected_task_count") != args.validation_task_count:
            raise ValueError(f"{label} actor manifest has the wrong task count")
        if manifest.get("model") != MODEL or manifest.get("reasoning_effort") != "high":
            raise ValueError(f"{label} actor manifest has the wrong model contract")
        budget = manifest.get("actor_contract", {}).get("provider_budget", {})
        if budget.get("approval_limit_usd") != args.actor_approval_limit_usd:
            raise ValueError(f"{label} actor manifest has the wrong shared budget")
        if budget.get("prior_spend_usd") != args.prior_spend_usd:
            raise ValueError(f"{label} actor manifest has the wrong prior spend")

    actor_budgets = [
        manifest["actor_contract"]["provider_budget"]
        for manifest in (no_skill_manifest, m_core_manifest)
    ]
    actor_budget_paths = {budget.get("shared_state_path") for budget in actor_budgets}
    if None in actor_budget_paths or len(actor_budget_paths) != 1:
        raise ValueError("actor preflights must share one provider budget state path")
    shared_budget_path = next(iter(actor_budget_paths))

    native_sequence = read_object(args.native_sequence_preflight)
    semantic_sequence = read_object(args.semantic_sequence_preflight)
    for label, sequence, schedule in (
        ("native", native_sequence, native),
        ("semantic", semantic_sequence, semantic),
    ):
        if (
            sequence.get("schema_version")
            != "gated-candidate-sequence-preflight-v1"
            or sequence.get("status") != "proposed_no_network"
            or sequence.get("network_requests") != 0
        ):
            raise ValueError(f"{label} sequence preflight is not zero-network proposed")
        digest = sequence.get("preflight_sha256")
        unsigned = dict(sequence)
        unsigned.pop("preflight_sha256", None)
        if digest != canonical_sha256(unsigned):
            raise ValueError(f"{label} sequence preflight hash mismatch")
        if sequence.get("schedule", {}).get("sha256") != schedule.digest:
            raise ValueError(f"{label} sequence preflight has the wrong schedule")
        actor = sequence.get("actor", {})
        if (
            actor.get("candidate_snapshot_count") != len(schedule.units)
            or actor.get("task_count_per_snapshot") != args.validation_task_count
            or actor.get("model") != MODEL
            or actor.get("reasoning_effort") != "high"
        ):
            raise ValueError(f"{label} sequence actor contract mismatch")
        budget = sequence.get("shared_provider_budget", {})
        if (
            budget.get("covers_actor_and_translation") is not True
            or budget.get("state_path") != shared_budget_path
            or budget.get("approval_limit_usd") != args.actor_approval_limit_usd
            or budget.get("prior_spend_usd") != args.prior_spend_usd
        ):
            raise ValueError(f"{label} sequence does not share the provider budget")

    translation_items = sum(
        len(parse_semantic_unit(unit.payload_path).items)
        for unit in (*native.units, *semantic.units)
        if unit.payload_format == "semantic-patch-markdown-v1"
    )
    expected_attempts = translation_items * TRANSLATION_MAX_ATTEMPTS_PER_ITEM
    if (
        native_sequence.get("translation", {}).get("max_provider_attempts")
        + semantic_sequence.get("translation", {}).get("max_provider_attempts")
        != expected_attempts
    ):
        raise ValueError("sequence translation-attempt accounting mismatch")

    validation_runs = {
        "no_skill_diagnostic": args.validation_task_count,
        "m_core_common_incumbent": args.validation_task_count,
        "native_candidate_snapshots": len(native.units) * args.validation_task_count,
        "semantic_candidate_snapshots": len(semantic.units)
        * args.validation_task_count,
    }
    validation_total = sum(validation_runs.values())
    sealed_test_total = args.test_task_count * args.test_arm_count
    rates = rates_for_model(MODEL)
    baselines = [prior_baseline(path, rates) for path in args.prior_summary]
    planning_projection: dict[str, Any] | None = None
    if baselines:
        keys = tuple(baselines[0]["per_task"])
        worst_per_task = {
            key: max(float(row["per_task"][key]) for row in baselines) for key in keys
        }
        planning_projection = {
            "method": "componentwise maximum per task across aggregate-only prior runs",
            "worst_per_task": worst_per_task,
            "validation": scaled_projection(worst_per_task, validation_total),
            "sealed_test": scaled_projection(worst_per_task, sealed_test_total),
            "full_experiment": scaled_projection(
                worst_per_task, validation_total + sealed_test_total
            ),
        }

    cheapest_rate = min(rates.values())
    materialization_units = len(native.units) + len(semantic.units)
    result: dict[str, Any] = {
        "schema_version": "cross-task-validation-preflight-v3",
        "status": "preflight_proposed_no_network",
        "network_requests": 0,
        "model": MODEL,
        "pricing_usd_per_million_tokens": rates,
        "candidate_schedules": {
            "native": {
                "path": str(args.native_schedule.resolve()),
                "sha256": native.digest,
                "unit_count": len(native.units),
            },
            "semantic": {
                "path": str(args.semantic_schedule.resolve()),
                "sha256": semantic.digest,
                "unit_count": len(semantic.units),
            },
            "shared_m_core_sha256": native.m_core_sha256,
            "shared_memories_sha256": native.shared_memories_sha256,
            "shared_map_artifact_sha256": native.construction["map_artifact_sha256"],
        },
        "validation": {
            "execution_order": [
                "no-skill diagnostic",
                "M-core common incumbent",
                "native compressed schedule",
                "semantic-reduce schedule",
            ],
            "task_runs": validation_runs,
            "total_actor_task_runs": validation_total,
            "distinct_conditions_or_snapshots": 2
            + len(native.units)
            + len(semantic.units),
            "timeout_seconds_per_task": args.timeout_seconds,
            "absolute_sequential_timeout_seconds": validation_total
            * args.timeout_seconds,
            "shared_provider_budget": {
                "covers_actor_and_translation": True,
                "shared_across_all_validation_runs": True,
                "state_path": shared_budget_path,
                "approval_limit_usd": args.actor_approval_limit_usd,
                "prior_spend_usd": args.prior_spend_usd,
                "remaining_approval_usd": round(
                    args.actor_approval_limit_usd - args.prior_spend_usd, 8
                ),
                "hard_provider_token_upper_bound_at_cheapest_rate": int(
                    (args.actor_approval_limit_usd - args.prior_spend_usd)
                    * 1_000_000
                    / cheapest_rate
                ),
                "cheapest_rate_field": min(rates, key=rates.get),
            },
        },
        "candidate_materialization": {
            "candidate_unit_count": materialization_units,
            "semantic_item_count": translation_items,
            "max_top_level_translation_calls": translation_items,
            "max_attempts_per_item": TRANSLATION_MAX_ATTEMPTS_PER_ITEM,
            "max_provider_attempts": expected_attempts,
            "max_output_tokens_per_call": ACTOR_MAX_OUTPUT_TOKENS,
            "shared_provider_budget_includes_translation_attempts": True,
            "programmatic_apply_llm_calls": 0,
        },
        "sealed_test_projection": {
            "arm_count": args.test_arm_count,
            "task_count_per_arm": args.test_task_count,
            "total_actor_task_runs": sealed_test_total,
            "absolute_sequential_timeout_seconds": sealed_test_total
            * args.timeout_seconds,
            "arms": [
                "no-skill",
                "m-core-only",
                "m-core-compressed-gated",
                "m-core-semantic-reduce-gated",
            ],
            "budget_status": "must be frozen after final validation skills and before test",
        },
        "full_experiment_actor_task_runs": validation_total + sealed_test_total,
        "full_experiment_absolute_sequential_timeout_seconds": (
            validation_total + sealed_test_total
        )
        * args.timeout_seconds,
        "actor_manifests": {
            "no_skill": {
                "path": str(args.no_skill_actor_manifest.resolve()),
                "sha256": sha256_file(args.no_skill_actor_manifest),
            },
            "m_core": {
                "path": str(args.m_core_actor_manifest.resolve()),
                "sha256": sha256_file(args.m_core_actor_manifest),
            },
        },
        "sequence_preflights": {
            "native": {
                "path": str(args.native_sequence_preflight.resolve()),
                "sha256": native_sequence["preflight_sha256"],
                "file_sha256": sha256_file(args.native_sequence_preflight),
            },
            "semantic": {
                "path": str(args.semantic_sequence_preflight.resolve()),
                "sha256": semantic_sequence["preflight_sha256"],
                "file_sha256": sha256_file(args.semantic_sequence_preflight),
            },
        },
        "prior_aggregate_planning_baselines": baselines,
        "planning_projection": planning_projection,
    }
    result["preflight_sha256"] = canonical_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "preflight": str(args.output.resolve()),
                "sha256": result["preflight_sha256"],
                "validation_actor_task_runs": validation_total,
                "sealed_test_actor_task_runs": sealed_test_total,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
