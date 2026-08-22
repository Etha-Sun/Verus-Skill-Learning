from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from skillopt.evaluation.gate import evaluate_gate

from skillopt_verusage.adapter import VeruSAGEAdapter
from skillopt_verusage.cost_ledger import write_cost_ledger


DEFAULT_PRIOR_SPEND_USD = 17.083853


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
        raise ValueError(f"run must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    return resolved


def _load_results(prediction_dir: Path, ordered_ids: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item_id in ordered_ids:
        path = prediction_dir / item_id / "result.json"
        if not path.is_file():
            raise ValueError(f"missing result: {item_id}")
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("id") != item_id or "hard" not in result:
            raise ValueError(f"invalid result: {item_id}")
        results.append(result)
    return results


def _score(results: list[dict[str, Any]]) -> tuple[float, float]:
    if not results:
        return 0.0, 0.0
    return (
        sum(float(row.get("hard", 0) or 0) for row in results) / len(results),
        sum(float(row.get("soft", 0) or 0) for row in results) / len(results),
    )


def _resume_partition(
    items: list[dict[str, Any]], prediction_dir: Path, skill_sha256: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    complete: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    recovery_root = prediction_dir.parent / "_recovery"
    for item in items:
        task_dir = prediction_dir / str(item["id"])
        result_path = task_dir / "result.json"
        manifest_path = task_dir / "run_manifest.json"
        if result_path.is_file() and manifest_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                result.get("id") == item["id"]
                and "hard" in result
                and manifest.get("skill_sha256") == skill_sha256
            ):
                complete.append(result)
                continue
        if task_dir.exists():
            recovery_root.mkdir(parents=True, exist_ok=True)
            suffix = int(time.time() * 1_000_000)
            shutil.move(str(task_dir), recovery_root / f"{item['id']}-{suffix}")
        pending.append(item)
    return complete, pending


def _paired_summary(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> dict[str, Any]:
    baseline_by_id = {str(row["id"]): bool(row.get("hard")) for row in baseline}
    candidate_by_id = {str(row["id"]): bool(row.get("hard")) for row in candidate}
    transitions = {"0_to_0": 0, "0_to_1": 0, "1_to_0": 0, "1_to_1": 0}
    rows: list[dict[str, Any]] = []
    for item_id in baseline_by_id:
        before = int(baseline_by_id[item_id])
        after = int(candidate_by_id[item_id])
        transitions[f"{before}_to_{after}"] += 1
        rows.append({"id": item_id, "baseline_hard": before, "candidate_hard": after})
    return {"transitions": transitions, "items": rows}


def run_gate(
    run_dir: Path,
    *,
    workers: int = 60,
    prior_spend_usd: float = DEFAULT_PRIOR_SPEND_USD,
    approval_limit_usd: float = 20.0,
) -> dict[str, Any]:
    run_dir = _require_run_root(run_dir)
    optimizer_result = json.loads(
        (run_dir / "optimizer_result.json").read_text(encoding="utf-8")
    )
    if optimizer_result.get("status") != "candidate_pending_manual_audit":
        raise RuntimeError("optimizer candidate did not pass automatic audit")
    manual_audit = json.loads((run_dir / "manual_audit.json").read_text(encoding="utf-8"))
    if manual_audit.get("status") != "approved_for_selection_gate":
        raise RuntimeError("manual audit has not approved the selection gate")

    source_run = Path(str(optimizer_result["source_run"])).resolve()
    source_summary = json.loads((source_run / "summary.json").read_text(encoding="utf-8"))
    cfg = dict(source_summary["config"])
    candidate_skill = (run_dir / "candidate_skill.md").read_text(encoding="utf-8")
    candidate_sha256 = _sha256_text(candidate_skill)
    if candidate_sha256 != optimizer_result["candidate_sha256"]:
        raise ValueError("candidate skill changed after optimizer audit")

    budget_state_path = run_dir / "deepseek_gate_budget.json"
    gate_cfg = dict(cfg)
    gate_cfg["out_root"] = str(run_dir)
    gate_cfg["budget_state_path"] = str(budget_state_path)
    gate_cfg["budget_prior_spend_usd"] = prior_spend_usd
    gate_cfg["budget_optimizer_reserve_usd"] = 0.0
    gate_cfg["budget_approval_limit_usd"] = approval_limit_usd
    adapter = VeruSAGEAdapter(
        split_dir=cfg["split_dir"],
        verusage_src_root=cfg["verusage_src_root"],
        verus_bin=cfg["verus_bin"],
        lynette_bin=cfg["lynette_bin"],
        model="deepseek-v4-flash",
        workers=workers,
        analyst_workers=int(cfg["analyst_workers"]),
        failure_only=bool(cfg["failure_only"]),
        minibatch_size=int(cfg["minibatch_size"]),
        edit_budget=int(cfg["edit_budget"]),
        repair_attempts=int(cfg["repair_attempts"]),
        request_cap=int(cfg["request_cap"]),
        action_output_tokens=int(cfg["action_output_tokens"]),
        reasoning_output_tokens=int(cfg["reasoning_output_tokens"]),
        retry_action_output_tokens=int(cfg["retry_action_output_tokens"]),
        retry_reasoning_output_tokens=int(cfg["retry_reasoning_output_tokens"]),
        max_action_output_tokens=int(cfg["max_action_output_tokens"]),
        max_reasoning_output_tokens=int(cfg["max_reasoning_output_tokens"]),
        task_retries=int(cfg["task_retries"]),
        request_timeout_seconds=int(cfg["request_timeout_seconds"]),
        task_timeout_seconds=int(cfg["task_timeout_seconds"]),
        budget_state_path=str(budget_state_path),
        budget_approval_limit_usd=approval_limit_usd,
        budget_prior_spend_usd=prior_spend_usd,
        budget_optimizer_reserve_usd=0.0,
        budget_request_reserve_usd=float(cfg["budget_request_reserve_usd"]),
        seed=int(cfg["seed"]),
    )
    adapter.setup(gate_cfg)
    batch = adapter.dataloader.build_eval_batch(
        env_num=20, split="selection", seed=int(cfg["seed"])
    )
    items = list(batch.payload or [])
    if len(items) != 20:
        raise ValueError(f"expected 20 selection items, found {len(items)}")
    ordered_ids = [str(item["id"]) for item in items]

    baseline_dir = source_run / "selection_eval_baseline" / "predictions"
    baseline = _load_results(baseline_dir, ordered_ids)
    baseline_hard, baseline_soft = _score(baseline)
    if abs(baseline_hard - float(source_summary["baseline_selection_hard"])) > 1e-12:
        raise ValueError("reconstructed baseline score differs from source summary")

    gate_dir = run_dir / "selection_gate"
    prediction_dir = gate_dir / "predictions"
    prediction_dir.mkdir(parents=True, exist_ok=True)
    complete, pending = _resume_partition(items, prediction_dir, candidate_sha256)
    if pending:
        adapter.rollout(pending, candidate_skill, str(gate_dir))
    candidate = _load_results(prediction_dir, ordered_ids)
    candidate_hard, candidate_soft = _score(candidate)
    decision = evaluate_gate(
        candidate_skill,
        candidate_hard,
        (source_run / "selection_eval_baseline" / "skill.md").read_text(
            encoding="utf-8"
        ),
        baseline_hard,
        (source_run / "selection_eval_baseline" / "skill.md").read_text(
            encoding="utf-8"
        ),
        baseline_hard,
        0,
        1,
        cand_soft=candidate_soft,
        metric="hard",
    )
    paired = _paired_summary(baseline, candidate)
    _write_json(run_dir / "paired_selection_results.json", paired)
    cost_ledger = write_cost_ledger(run_dir)
    cost_ledger["status"] = "complete"
    _write_json(run_dir / "cost_ledger.json", cost_ledger)
    budget_state = json.loads(budget_state_path.read_text(encoding="utf-8"))
    result = {
        "status": "complete",
        "action": decision.action,
        "candidate_accepted": decision.action != "reject",
        "selection_n": len(candidate),
        "baseline_hard": baseline_hard,
        "baseline_soft": baseline_soft,
        "candidate_hard": candidate_hard,
        "candidate_soft": candidate_soft,
        "baseline_solved": sum(bool(row.get("hard")) for row in baseline),
        "candidate_solved": sum(bool(row.get("hard")) for row in candidate),
        "candidate_sha256": candidate_sha256,
        "target_model": "deepseek-v4-flash",
        "configured_task_workers": workers,
        "budget_prior_spend_usd": prior_spend_usd,
        "budget_approval_limit_usd": approval_limit_usd,
        "gate_target_cost_usd": budget_state["target_spend_usd"],
        "gate_uncertain_cost_usd": budget_state["uncertain_spend_usd"],
        "conservative_total_usd": (
            float(budget_state["prior_spend_usd"])
            + float(budget_state["target_spend_usd"])
            + float(budget_state["uncertain_spend_usd"])
        ),
        "resumed_complete_tasks": len(complete),
        "newly_run_tasks": len(pending),
        "paired_transitions": paired["transitions"],
        "cost_ledger": cost_ledger,
    }
    _write_json(run_dir / "gate_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=60)
    parser.add_argument("--prior-spend-usd", type=float, default=DEFAULT_PRIOR_SPEND_USD)
    parser.add_argument("--approval-limit-usd", type=float, default=20.0)
    args = parser.parse_args()
    result = run_gate(
        args.run_dir,
        workers=args.workers,
        prior_spend_usd=args.prior_spend_usd,
        approval_limit_usd=args.approval_limit_usd,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
