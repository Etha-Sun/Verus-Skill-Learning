from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from skillopt.config import flatten_config, load_config
from skillopt.evaluation.gate import evaluate_gate
from skillopt.optimizer.slow_update import replace_slow_update_field
from skillopt.utils import compute_score, skill_hash

from skillopt_verusage.cost_ledger import write_cost_ledger
from skillopt_verusage.train import _adapter, _expand


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _write_text(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _copy_once(source: Path, destination: Path) -> None:
    if destination.exists():
        return
    shutil.copy2(source, destination)


def _require_below_run_root(path: Path) -> Path:
    configured = os.environ.get("VERUS_SKILL_RUN_ROOT", "")
    if not configured:
        raise RuntimeError("VERUS_SKILL_RUN_ROOT is not set")
    root = Path(configured).resolve()
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"run directory must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    return resolved


def _load_retry_guidance(retry_dir: Path) -> tuple[dict[str, Any], str]:
    retry_result = json.loads(
        (retry_dir / "slow_result.json").read_text(encoding="utf-8")
    )
    if retry_result.get("status") != "success":
        raise RuntimeError("slow optimizer retry did not complete successfully")
    optimizer_result = retry_result.get("result") or {}
    guidance = str(optimizer_result.get("slow_update_content") or "").strip()
    if not guidance:
        raise RuntimeError("slow optimizer retry produced no guidance")
    return retry_result, guidance


def _load_or_create_pre_gate(run_dir: Path, retry_dir: Path) -> dict[str, Any]:
    pre_gate_dir = retry_dir / "pre_gate"
    pre_gate_dir.mkdir(parents=True, exist_ok=True)
    state_path = pre_gate_dir / "runtime_state.json"
    if not state_path.exists():
        runtime_state = json.loads(
            (run_dir / "runtime_state.json").read_text(encoding="utf-8")
        )
        if int(runtime_state.get("last_completed_step", -1)) != 2:
            raise RuntimeError("slow retry gate requires completed epoch 2")
        _write_json(state_path, runtime_state)
        _copy_once(
            Path(str(runtime_state["current_skill_path"])),
            pre_gate_dir / "current_skill.md",
        )
        _copy_once(
            Path(str(runtime_state["best_skill_path"])),
            pre_gate_dir / "best_skill.md",
        )
        _copy_once(
            run_dir / "slow_update" / "epoch_02" / "slow_result.json",
            pre_gate_dir / "slow_result.json",
        )
        _write_json(pre_gate_dir / "cost_ledger.json", write_cost_ledger(run_dir))
    return json.loads(state_path.read_text(encoding="utf-8"))


def _validate_config(cfg: dict[str, Any], run_dir: Path) -> None:
    expected = {
        "out_root": str(run_dir),
        "target_harness": "codex_cli_native_responses",
        "target_model": "deepseek-v4-pro",
        "sel_env_num": 20,
        "gate_metric": "hard",
        "codex_timeout_seconds": 600,
        "max_codex_timeout_seconds": 600,
        "workers": 40,
    }
    mismatches = {
        key: {"actual": cfg.get(key), "expected": value}
        for key, value in expected.items()
        if cfg.get(key) != value
    }
    if mismatches:
        raise RuntimeError(f"slow retry gate config mismatch: {mismatches}")


def _apply_decision(
    run_dir: Path,
    retry_dir: Path,
    pre_gate_state: dict[str, Any],
    candidate_skill: str,
    retry_result: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    pre_gate_dir = retry_dir / "pre_gate"
    current_skill = (pre_gate_dir / "current_skill.md").read_text(encoding="utf-8")
    best_skill = (pre_gate_dir / "best_skill.md").read_text(encoding="utf-8")
    action = str(decision["action"])

    runtime_state = dict(pre_gate_state)
    if action in {"accept", "accept_new_best"}:
        _write_text(run_dir / "skills" / "skill_v0002.md", candidate_skill)
        runtime_state["current_score"] = float(decision["candidate_hard"])
        runtime_state["current_origin"] = "slow_update_epoch_02_retry_pointer_top3"
        if action == "accept_new_best":
            _write_text(run_dir / "best_skill.md", candidate_skill)
            runtime_state["best_score"] = float(decision["candidate_hard"])
            runtime_state["best_step"] = 2
            runtime_state["best_origin"] = runtime_state["current_origin"]
    else:
        _write_text(run_dir / "skills" / "skill_v0002.md", current_skill)
        _write_text(run_dir / "best_skill.md", best_skill)
    _write_json(run_dir / "runtime_state.json", runtime_state)

    optimizer_result = dict(retry_result["result"])
    canonical_result = {
        **optimizer_result,
        "schema_version": "1",
        "action": action,
        "time_s": retry_result.get("wall_seconds"),
        "selection_hard": decision["candidate_hard"],
        "selection_soft": decision["candidate_soft"],
        "candidate_hash": decision["candidate_hash"],
        "update_origin": "slow_update_momentum_retry_pointer_top3",
        "update_target": (
            "Address longitudinal regressions and persistent failures observed "
            "across adjacent epochs."
        ),
        "retry_artifact": str(retry_dir),
    }
    _write_json(
        run_dir / "slow_update" / "epoch_02" / "slow_result.json",
        canonical_result,
    )

    final_ledger = write_cost_ledger(run_dir)
    before_ledger = json.loads(
        (pre_gate_dir / "cost_ledger.json").read_text(encoding="utf-8")
    )
    before_cost = float((before_ledger.get("target") or {}).get("estimated_cost_usd", 0))
    after_cost = float((final_ledger.get("target") or {}).get("estimated_cost_usd", 0))
    result = {
        **decision,
        "status": "complete",
        "candidate_accepted": action in {"accept", "accept_new_best"},
        "target_model": "deepseek-v4-pro",
        "selection_n": 20,
        "incremental_actor_cost_usd": after_cost - before_cost,
        "total_actor_cost_usd": after_cost,
        "cost_ledger": final_ledger,
    }
    _write_json(retry_dir / "gate_result.json", result)
    return result


def run_gate(run_dir: Path, config_path: Path) -> dict[str, Any]:
    run_dir = _require_below_run_root(run_dir)
    retry_dir = run_dir / "slow_update" / "epoch_02" / "retry_pointer_top3"
    retry_result, guidance = _load_retry_guidance(retry_dir)
    pre_gate_state = _load_or_create_pre_gate(run_dir, retry_dir)
    pre_gate_dir = retry_dir / "pre_gate"
    current_skill = (pre_gate_dir / "current_skill.md").read_text(encoding="utf-8")
    best_skill = (pre_gate_dir / "best_skill.md").read_text(encoding="utf-8")
    candidate_skill = replace_slow_update_field(current_skill, guidance)
    candidate_hash = skill_hash(candidate_skill)
    candidate_path = retry_dir / "candidate_skill.md"
    if candidate_path.exists() and candidate_path.read_text(encoding="utf-8") != candidate_skill:
        raise RuntimeError("stored slow retry candidate does not match optimizer guidance")
    _write_text(candidate_path, candidate_skill)

    completed_path = retry_dir / "gate_result.json"
    if completed_path.exists():
        completed = json.loads(completed_path.read_text(encoding="utf-8"))
        if completed.get("candidate_hash") != candidate_hash:
            raise RuntimeError("completed gate refers to a different candidate")
        return completed

    decision_path = retry_dir / "gate_decision.json"
    if decision_path.exists():
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        if decision.get("candidate_hash") != candidate_hash:
            raise RuntimeError("stored gate decision refers to a different candidate")
    else:
        cfg = flatten_config(_expand(load_config(str(config_path), [])))
        _validate_config(cfg, run_dir)
        adapter = _adapter(cfg)
        adapter.setup(cfg)
        batch = adapter.dataloader.build_eval_batch(
            env_num=20,
            split="valid_seen",
            seed=int(cfg["seed"]),
            out_root=str(run_dir),
        )
        items = list(batch.payload or [])
        if len(items) != 20:
            raise RuntimeError(f"expected 20 selection items, found {len(items)}")
        gate_dir = retry_dir / "selection_eval"
        results = adapter.rollout(items, candidate_skill, str(gate_dir))
        candidate_hard, candidate_soft = compute_score(results)
        gate = evaluate_gate(
            candidate_skill=candidate_skill,
            cand_hard=candidate_hard,
            current_skill=current_skill,
            current_score=float(pre_gate_state["current_score"]),
            best_skill=best_skill,
            best_score=float(pre_gate_state["best_score"]),
            best_step=int(pre_gate_state["best_step"]),
            global_step=2,
            cand_soft=candidate_soft,
            metric="hard",
        )
        decision = {
            "schema_version": "1",
            "action": gate.action,
            "candidate_hash": candidate_hash,
            "candidate_sha256": _sha256_text(candidate_skill),
            "base_skill_sha256": _sha256_text(current_skill),
            "current_hard": float(pre_gate_state["current_score"]),
            "best_hard": float(pre_gate_state["best_score"]),
            "candidate_hard": candidate_hard,
            "candidate_soft": candidate_soft,
            "selection_ids": [str(item["id"]) for item in items],
        }
        _write_json(decision_path, decision)

    return _apply_decision(
        run_dir,
        retry_dir,
        pre_gate_state,
        candidate_skill,
        retry_result,
        decision,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    result = run_gate(args.run_dir, args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
