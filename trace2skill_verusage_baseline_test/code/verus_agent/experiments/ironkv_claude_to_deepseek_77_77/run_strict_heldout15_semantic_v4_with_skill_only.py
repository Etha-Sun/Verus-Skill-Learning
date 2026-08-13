#!/usr/bin/env python3
"""Run semantic-v4 with-skill only on the frozen strict held-out 15.

The already completed native-Trace2Skill paired experiment supplies the
historical baseline and native-skill comparison. This runner evaluates only
the new semantic-v4 M/R skill under the identical task, model, agent, Verus,
contract-audit, and stopping settings.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from verus_agent.experiments.ironkv_claude_to_deepseek_77_77 import (
    run_heldout20_paired_when_ready as base,
)
from verus_agent.experiments.ironkv_claude_to_deepseek_77_77 import (
    run_strict_heldout15_paired as strict,
)
from verus_agent.experiments.ironkv_claude_to_deepseek_77_77 import (
    run_strict_heldout15_semantic_v4_paired as semantic,
)


DEFAULT_OUTPUT_ROOT = (
    base.PROJECT_ROOT
    / "outputs/ironkv_deepseek_strict_heldout15_semantic_v4_with_skill_only_v1"
)
NATIVE_COMPARISON = (
    base.PROJECT_ROOT
    / "outputs/ironkv_deepseek_strict_heldout15_paired_raw_combined_v2_v1"
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    result.add_argument("--env-file", type=Path, default=base.DEFAULT_ENV_FILE)
    result.add_argument("--max-turns", type=int, default=base.DEFAULT_MAX_TURNS)
    result.add_argument(
        "--max-no-progress-turns", type=int, default=base.DEFAULT_MAX_NO_PROGRESS
    )
    result.add_argument(
        "--max-output-tokens", type=int, default=base.DEFAULT_MAX_OUTPUT_TOKENS
    )
    result.add_argument("--temperature", type=float, default=base.DEFAULT_TEMPERATURE)
    result.add_argument(
        "--task-numbers",
        type=int,
        nargs="+",
        help="Optional one-based positions from the frozen held-out-15 to rerun.",
    )
    result.add_argument("--selection-check-only", action="store_true")
    return result


def prepare(
    output: Path,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
    args: argparse.Namespace,
) -> Path:
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    snapshot = output / "skill_snapshot/verus-proof-repair"
    shutil.copytree(semantic.SEMANTIC_SKILL, snapshot)
    (output / "tasks.tsv").write_text(
        "".join(
            f"{index:02d}\t{row['task_id']}\t{row['source_path']}\n"
            for index, row in enumerate(rows, 1)
        ),
        encoding="utf-8",
    )
    selection = json.loads(strict.STRICT_SELECTION.read_text(encoding="utf-8"))
    base.write_json(output / "heldout15_selection.json", selection)
    base.write_json(
        output / "experiment_manifest.json",
        {
            "experiment": "ironkv_deepseek_strict_heldout15_semantic_v4_with_skill_only_v1",
            "created_at": base.utc_now(),
            "harness": "self_written_verus_agent_react",
            "conditions_run": ["with_skill"],
            "task_count": len(rows),
            "arm_count": len(rows),
            "model": config["model"],
            "base_url": config["base_url"],
            "api_key_env_var": config["api_key_env_var"],
            "api_key_configured": True,
            "deepseek_thinking": True,
            "reasoning_effort": "high",
            "temperature_requested": args.temperature,
            "temperature_effective": None,
            "temperature_note": "DeepSeek thinking mode does not send temperature",
            "max_turns_per_arm": args.max_turns,
            "max_no_progress_turns": args.max_no_progress_turns,
            "max_output_tokens_per_request": args.max_output_tokens,
            "automatic_retries": False,
            "execution": "serial",
            "skill_variant": "semantic_v4_unmodified",
            "skill_source": str(semantic.SEMANTIC_SKILL.resolve()),
            "skill_source_final_audit": str(semantic.SEMANTIC_AUDIT.resolve()),
            "skill_source_final_audit_sha256": base.sha256_file(semantic.SEMANTIC_AUDIT),
            "skill_snapshot": str(snapshot.resolve()),
            "skill_snapshot_sha256": base.sha256_tree(snapshot),
            "semantic_memory_count": 284,
            "semantic_global_skill_count": 88,
            "semantic_reference_count": 14,
            "comparison_uses_completed_historical_baseline": True,
            "comparison_experiment": str(NATIVE_COMPARISON.resolve()),
            "comparison_summary": str((NATIVE_COMPARISON / "paired_summary.json").resolve()),
            "comparison_caveat": "The baseline and native-skill arms are from the prior completed run; API sampling is not paired within this new run.",
            "heldout_trajectory_or_verified_solution_exposed": False,
            "strict_selection_manifest": str(strict.STRICT_SELECTION.resolve()),
            "strict_selection_manifest_sha256": base.sha256_file(strict.STRICT_SELECTION),
            "train_task_id_overlap_count": 0,
            "selected_leakage_component_duplicate_count": 0,
            "selected_task_numbers": list(args.task_numbers or range(1, 16)),
            "selected_tasks": [
                {
                    "task_id": row["task_id"],
                    "module": row["module"],
                    "source_path": row["source_path"],
                    "source_sha256": row["source_sha256"],
                }
                for row in rows
            ],
        },
    )
    return snapshot


def run_arm(
    output: Path,
    snapshot: Path,
    row: dict[str, Any],
    index: int,
    config: dict[str, Any],
    child_env: dict[str, str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    source = Path(row["source_path"])
    if base.sha256_file(source) != row["source_sha256"]:
        raise ValueError(f"source changed before arm: {row['task_id']}")
    work_dir = output / "with_skill" / row["task_id"]
    log_path = output / "logs" / f"{index:02d}_with_skill_{row['task_id']}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "verus_agent.cli",
        "--input", str(source), "--work-dir", str(work_dir),
        "--verus-bin", str(base.VERUS_BIN), "--lynette-bin", str(base.LYNETTE_BIN),
        "--guide-snapshot", str(base.GUIDE_SNAPSHOT), "--vstd-root", str(base.VSTD_ROOT),
        "--model", config["model"], "--base-url", config["base_url"],
        "--api-key-env-var", "DEEPSEEK_API_KEY", "--deepseek-thinking",
        "--max-turns", str(args.max_turns),
        "--max-no-progress-turns", str(args.max_no_progress_turns),
        "--max-output-tokens", str(args.max_output_tokens),
        "--temperature", str(args.temperature), "--skill-dir", str(snapshot),
    ]
    print(
        f"[{index:02d}/{args.run_count:02d}] START "
        f"task={row['task_id']} condition=with_skill",
        flush=True,
    )
    started = base.utc_now()
    with log_path.open("wb") as handle:
        completed = subprocess.run(
            command, cwd=base.PROJECT_ROOT, env=child_env,
            stdout=handle, stderr=subprocess.STDOUT, check=False,
        )
    print(
        f"[{index:02d}/{args.run_count:02d}] END "
        f"task={row['task_id']} condition=with_skill rc={completed.returncode}",
        flush=True,
    )
    return {
        "arm_index": index, "task_index": index, "task_id": row["task_id"],
        "condition": "with_skill", "exit_code": completed.returncode,
        "started_at": started, "finished_at": base.utc_now(),
        "log_path": str(log_path), "work_dir": str(work_dir),
    }


def summarize(output: Path, arms: list[dict[str, Any]]) -> None:
    successes = 0
    total_tokens = 0
    outcomes: dict[str, bool] = {}
    for arm in arms:
        work = Path(arm["work_dir"])
        result_path = work / "run_result.json"
        usage_path = work / "usage.json"
        result = json.loads(result_path.read_text()) if result_path.is_file() else {}
        usage = json.loads(usage_path.read_text()) if usage_path.is_file() else {}
        success = bool(result.get("success"))
        successes += int(success)
        total_tokens += int(usage.get("total_tokens", 0) or 0)
        outcomes[arm["task_id"]] = success
    base.write_json(
        output / "with_skill_summary.json",
        {
            "completed_at": base.utc_now(), "completed_arms": len(arms),
            "successes": successes, "total_tokens": total_tokens,
            "outcomes": outcomes,
            "historical_comparison_summary": str((NATIVE_COMPARISON / "paired_summary.json").resolve()),
        },
    )


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    rows = strict.load_rows()
    selected, quotas = strict.select_frozen(rows, 15, base.DEFAULT_SEED)
    strict.validate_strict_selection(selected)
    if args.task_numbers:
        if (
            len(set(args.task_numbers)) != len(args.task_numbers)
            or any(number < 1 or number > 15 for number in args.task_numbers)
        ):
            raise ValueError("--task-numbers must be unique values in the range 1..15")
        selected = [selected[number - 1] for number in args.task_numbers]
    args.run_count = len(selected)
    semantic.validate_semantic_skill(0)
    print(json.dumps({"selection_count": len(selected), "module_quotas": quotas,
                      "task_numbers": args.task_numbers or list(range(1, 16)),
                      "task_ids": [row["task_id"] for row in selected]}, indent=2), flush=True)
    if args.selection_check_only:
        return 0
    config, child_env = base.load_nonsecret_config(args.env_file.resolve())
    output = args.output_root.resolve()
    snapshot = prepare(output, selected, config, args)
    arms: list[dict[str, Any]] = []
    base.write_json(output / "progress.json", {"status": "running", "arms": arms})
    for index, row in enumerate(selected, 1):
        arm = run_arm(output, snapshot, row, index, config, child_env, args)
        arms.append(arm)
        base.write_json(output / "progress.json", {
            "status": "running", "completed_arms": len(arms), "arms": arms,
        })
    summarize(output, arms)
    base.write_json(output / "progress.json", {
        "status": "completed", "completed_arms": len(arms), "arms": arms,
    })
    (output / "batch_complete").write_text(base.utc_now() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
