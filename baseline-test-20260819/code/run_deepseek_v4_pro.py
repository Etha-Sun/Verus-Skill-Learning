#!/usr/bin/env python3
"""Run DeepSeek V4 Pro no-skill/official-baseline evaluation on heldout-40."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPOSITORY_ROOT.parent
SHARED_EXPERIMENT = (
    REPOSITORY_ROOT / "trace2skill_verusage_cross_task_global_skills_20260814"
)
ACTOR_RUNNER = SHARED_EXPERIMENT / "code" / "run_actor_matrix.py"
SPLIT_ROOT = REPOSITORY_ROOT / "fixed-claude-stratified-80-seed20260814"
DEFAULT_RUN_ROOT = Path(
    os.environ.get("VERUS_SKILL_RUN_ROOT", WORKSPACE_ROOT / "verus_skill_runs")
)
DEFAULT_OUTPUT_ROOT = (
    DEFAULT_RUN_ROOT / "baseline-test-20260819" / "deepseek-v4-pro"
)
DEFAULT_SKILL_DIR = (
    DEFAULT_RUN_ROOT
    / "cross-task-global-20260814"
    / "native_official_baseline_v1"
    / "skill"
    / "verus-proof-repair"
)
EXPECTED_SKILL_SHA256 = (
    "fc2c51a283212ffe365fcd9bc91fedca1c6a46d43a51c4310facd7f76f41b74b"
)
GENERATOR_SKILL_SHA256 = (
    "195ab1294871689873e3bd6d9d2dbfb0a89a0d13b2ea0bdd1f7d716d826437c2"
)
CONDITIONS = ("no-skill", "with-native-official-baseline")
SPLITS = ("val", "test")
PORTS = {
    ("no-skill", "val"): 4317,
    ("no-skill", "test"): 4318,
    ("with-native-official-baseline", "val"): 4319,
    ("with-native-official-baseline", "test"): 4320,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        item for item in root.rglob("*") if item.is_file() or item.is_symlink()
    )
    for path in files:
        if path.is_symlink():
            raise ValueError(f"skill tree may not contain symlinks: {path}")
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def append_status(output_root: Path, message: str) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    line = f"{utc_now()} {message}"
    with (output_root / "live_status.log").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")
    print(line, flush=True)


def default_env_file() -> Path:
    configured = os.environ.get("DEEPSEEK_ENV_FILE")
    if configured:
        return Path(configured).expanduser()
    candidates = (
        WORKSPACE_ROOT / "Trace2Skill" / ".env.deepseek",
        WORKSPACE_ROOT / ".env.deepseek",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def heldout_projection() -> tuple[list[dict[str, Any]], str]:
    projection: list[dict[str, Any]] = []
    for split in SPLITS:
        path = SPLIT_ROOT / split / "items.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        if len(rows) != 20:
            raise ValueError(f"{path} must contain exactly 20 tasks")
        for index, row in enumerate(rows, 1):
            projection.append(
                {
                    "heldout_index": len(projection) + 1,
                    "source_split": split,
                    "source_split_index": index,
                    "task_id": row["task_id"],
                    "project_code": row["project_code"],
                    "source_sha256": row["source_sha256"],
                }
            )
    task_ids = [row["task_id"] for row in projection]
    if len(projection) != 40 or len(set(task_ids)) != 40:
        raise ValueError("heldout-40 task IDs must be exactly 40 and unique")
    return projection, canonical_sha256(projection)


def actor_command(
    args: argparse.Namespace,
    *,
    condition: str,
    split: str,
    output: Path,
    preflight: bool,
    resume: bool,
) -> list[str]:
    condition_arg = "no-skill" if condition == "no-skill" else "skill"
    command = [
        sys.executable,
        str(ACTOR_RUNNER),
        "--preflight" if preflight else "--execute",
        "--split",
        split,
        "--split-root",
        str(SPLIT_ROOT),
        "--condition",
        condition_arg,
        "--skill-dir",
        str(args.skill_dir),
        "--output-root",
        str(output),
        "--run-root",
        str(args.run_root),
        "--scratch-root",
        str(args.scratch_root),
        "--env-file",
        str(args.env_file),
        "--codex-bin",
        str(args.codex_bin),
        "--verus-bin",
        str(args.verus_bin),
        "--rust-root",
        str(args.rust_root),
        "--lynette-bin",
        str(args.lynette_bin),
        "--timeout-seconds",
        "600",
        "--verification-timeout-seconds",
        "120",
        "--proxy-port",
        str(PORTS[(condition, split)]),
        "--approval-limit-usd",
        str(args.approval_limit_usd),
        "--prior-spend-usd",
        "0",
        "--request-reserve-usd",
        "0.25",
    ]
    if not preflight:
        command.extend(
            [
                "--budget-state-path",
                str(args.output_root / "provider_budget_state.json"),
            ]
        )
    if resume:
        command.append("--resume")
    return command


def aggregate_condition(output_root: Path, condition: str) -> dict[str, Any]:
    summaries: list[tuple[str, dict[str, Any]]] = []
    for split in SPLITS:
        path = output_root / condition / split / "summary.json"
        if not path.is_file():
            raise FileNotFoundError(path)
        summaries.append((split, json.loads(path.read_text(encoding="utf-8"))))
    tasks: list[dict[str, Any]] = []
    usage: dict[str, int | float] = {}
    for split, summary in summaries:
        for task in summary["tasks"]:
            tasks.append({"source_split": split, **task})
        for key, value in summary["usage"].items():
            usage[key] = usage.get(key, 0) + value
    if "estimated_cost_usd" in usage:
        usage["estimated_cost_usd"] = round(
            float(usage["estimated_cost_usd"]), 8
        )
    result = {
        "schema_version": 1,
        "status": "complete",
        "condition": condition,
        "model": "deepseek-v4-pro",
        "task_count": 40,
        "completed_tasks": len(tasks),
        "successes": sum(bool(task["success"]) for task in tasks),
        "timeout_count": sum(bool(task["timed_out"]) for task in tasks),
        "wall_time_seconds": round(
            sum(float(summary["wall_time_seconds"]) for _, summary in summaries), 6
        ),
        "total_cost_usd": round(
            sum(float(summary["total_cost_usd"]) for _, summary in summaries), 8
        ),
        "usage": usage,
        "coverage_complete": len(tasks) == 40,
        "fidelity_complete": all(
            bool(summary["fidelity_complete"]) for _, summary in summaries
        ),
        "safety_complete": all(
            bool(summary["safety_complete"]) for _, summary in summaries
        ),
        "scoring_policy": "proof-outcome-v3",
        "tasks": tasks,
        "completed_at": utc_now(),
    }
    write_json(output_root / condition / "summary_heldout40.json", result)
    return result


def validate_static_inputs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], str]:
    if not ACTOR_RUNNER.is_file():
        raise FileNotFoundError(ACTOR_RUNNER)
    if not args.skill_dir.is_dir():
        raise FileNotFoundError(args.skill_dir)
    actual_skill_hash = hash_tree(args.skill_dir)
    if actual_skill_hash != EXPECTED_SKILL_SHA256:
        raise ValueError(
            f"native official baseline hash mismatch: {actual_skill_hash}"
        )
    run_manifest_path = args.skill_dir.parents[1] / "run_manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    if run_manifest.get("skill_tree_sha256") != GENERATOR_SKILL_SHA256:
        raise ValueError("baseline generator manifest hash mismatch")
    projection, projection_hash = heldout_projection()
    return projection, projection_hash


def run_preflight(args: argparse.Namespace) -> int:
    projection, projection_hash = validate_static_inputs(args)
    preflight_root = args.output_root / "preflight_v1"
    manifests: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        for split in SPLITS:
            output = preflight_root / condition / split
            append_status(args.output_root, f"PREFLIGHT START {condition}/{split}")
            subprocess.run(
                actor_command(
                    args,
                    condition=condition,
                    split=split,
                    output=output,
                    preflight=True,
                    resume=False,
                ),
                cwd=REPOSITORY_ROOT,
                check=True,
            )
            manifest = json.loads(
                (output / "experiment_manifest.json").read_text(encoding="utf-8")
            )
            manifests.append(manifest)
            append_status(args.output_root, f"PREFLIGHT END {condition}/{split}")
    result = {
        "schema_version": 1,
        "valid": True,
        "network_requests": 0,
        "model": "deepseek-v4-pro",
        "timeout_seconds_per_task": 600,
        "conditions": list(CONDITIONS),
        "heldout_task_count_per_condition": 40,
        "total_actor_invocations": 80,
        "heldout_projection_sha256": projection_hash,
        "heldout_projection": projection,
        "native_official_baseline_actor_sha256": EXPECTED_SKILL_SHA256,
        "native_official_baseline_generator_sha256": GENERATOR_SKILL_SHA256,
        "actor_runner_sha256": sha256_file(ACTOR_RUNNER),
        "subrun_actor_contract_sha256": sorted(
            {manifest["actor_contract_sha256"] for manifest in manifests}
        ),
        "approval_limit_usd": args.approval_limit_usd,
        "created_at": utc_now(),
    }
    result["preflight_sha256"] = canonical_sha256(result)
    write_json(args.output_root / "preflight.json", result)
    print(json.dumps(result, indent=2), flush=True)
    return 0


def run_execute(args: argparse.Namespace) -> int:
    _, projection_hash = validate_static_inputs(args)
    preflight_path = args.output_root / "preflight.json"
    if not preflight_path.is_file():
        raise FileNotFoundError("run --preflight before --execute")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if not preflight.get("valid") or preflight.get("heldout_projection_sha256") != projection_hash:
        raise ValueError("preflight is invalid or stale")
    append_status(
        args.output_root,
        f"EXECUTE START preflight_sha256={preflight['preflight_sha256']}",
    )
    for condition in CONDITIONS:
        for split in SPLITS:
            output = args.output_root / condition / split
            if (output / "batch_complete").is_file():
                append_status(args.output_root, f"SKIP COMPLETE {condition}/{split}")
                continue
            for attempt in range(1, 6):
                resume = output.exists() and any(output.iterdir())
                append_status(
                    args.output_root,
                    f"RUN START {condition}/{split} attempt={attempt} resume={str(resume).lower()}",
                )
                completed = subprocess.run(
                    actor_command(
                        args,
                        condition=condition,
                        split=split,
                        output=output,
                        preflight=False,
                        resume=resume,
                    ),
                    cwd=REPOSITORY_ROOT,
                    check=False,
                )
                if completed.returncode == 0 and (output / "batch_complete").is_file():
                    append_status(args.output_root, f"RUN END {condition}/{split}")
                    break
                append_status(
                    args.output_root,
                    f"RUN INTERRUPTED {condition}/{split} rc={completed.returncode}",
                )
                if attempt == 5:
                    raise RuntimeError(
                        f"{condition}/{split} did not complete after {attempt} attempts"
                    )
                time.sleep(5)
        aggregate_condition(args.output_root, condition)
    no_skill = aggregate_condition(args.output_root, "no-skill")
    with_skill = aggregate_condition(
        args.output_root, "with-native-official-baseline"
    )
    final = {
        "schema_version": 1,
        "status": "complete",
        "model": "deepseek-v4-pro",
        "timeout_seconds_per_task": 600,
        "heldout_projection_sha256": projection_hash,
        "native_official_baseline_actor_sha256": EXPECTED_SKILL_SHA256,
        "native_official_baseline_generator_sha256": GENERATOR_SKILL_SHA256,
        "results": {
            "no-skill": {
                "successes": no_skill["successes"],
                "task_count": 40,
                "summary": str(
                    args.output_root / "no-skill" / "summary_heldout40.json"
                ),
            },
            "with-native-official-baseline": {
                "successes": with_skill["successes"],
                "task_count": 40,
                "summary": str(
                    args.output_root
                    / "with-native-official-baseline"
                    / "summary_heldout40.json"
                ),
            },
        },
        "completed_at": utc_now(),
    }
    write_json(args.output_root / "final_summary.json", final)
    (args.output_root / "experiment_complete").write_text(
        utc_now() + "\n", encoding="utf-8"
    )
    append_status(args.output_root, "EXECUTE COMPLETE")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    result.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    result.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    result.add_argument("--skill-dir", type=Path, default=DEFAULT_SKILL_DIR)
    result.add_argument("--scratch-root", type=Path, default=WORKSPACE_ROOT)
    result.add_argument("--env-file", type=Path, default=default_env_file())
    result.add_argument(
        "--codex-bin", type=Path, default=Path(shutil.which("codex") or "codex")
    )
    result.add_argument(
        "--verus-bin",
        type=Path,
        default=WORKSPACE_ROOT / "tools" / "verus" / "bin" / "verus",
    )
    result.add_argument(
        "--rust-root", type=Path, default=WORKSPACE_ROOT / "tools" / "rust"
    )
    result.add_argument(
        "--lynette-bin",
        type=Path,
        default=WORKSPACE_ROOT / "qwen_five_skill_eval" / "tools" / "lynette",
    )
    result.add_argument("--approval-limit-usd", type=float, default=20.0)
    return result


def main() -> int:
    args = parser().parse_args()
    args.run_root = args.run_root.resolve()
    args.output_root = args.output_root.resolve()
    args.skill_dir = args.skill_dir.resolve()
    args.scratch_root = args.scratch_root.resolve()
    args.env_file = args.env_file.resolve()
    args.codex_bin = args.codex_bin.resolve()
    args.verus_bin = args.verus_bin.resolve()
    args.rust_root = args.rust_root.resolve()
    args.lynette_bin = args.lynette_bin.resolve()
    if args.output_root == args.run_root or args.run_root not in args.output_root.parents:
        raise ValueError("output root must be a strict child of run root")
    if args.preflight:
        return run_preflight(args)
    return run_execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
