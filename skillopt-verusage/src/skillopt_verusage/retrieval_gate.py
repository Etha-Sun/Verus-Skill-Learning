from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from skillopt.config import flatten_config, load_config

from skillopt_verusage.adapter import VeruSAGEAdapter
from skillopt_verusage.codex_selection_gate import _paired_summary, _score
from skillopt_verusage.cost_ledger import write_cost_ledger
from skillopt_verusage.retrieval import load_retrieval_cards
from skillopt_verusage.train import _expand


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _audit_support(cards: dict[str, Any], prediction_dir: Path) -> dict[str, Any]:
    checked: list[dict[str, str]] = []
    errors: list[str] = []
    for card in cards["cards"]:
        for support in card["support"]:
            item_id = str(support["task_id"])
            result_path = prediction_dir / item_id / "result.json"
            if not result_path.is_file():
                errors.append(f"{card['id']}: missing support task {item_id}")
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            actual = "solved" if bool(result.get("hard")) else "failed"
            expected = str(support["verifier_label"])
            if actual != expected:
                errors.append(
                    f"{card['id']}: support label mismatch for {item_id}: "
                    f"{expected} != {actual}"
                )
            checked.append(
                {"card_id": str(card["id"]), "task_id": item_id, "label": actual}
            )
    return {"passed": not errors, "checked": checked, "errors": errors}


def _adapter(
    cfg: dict[str, Any],
    *,
    out_root: Path,
    budget_state_path: Path,
    cards_path: Path | None,
    prior_spend_usd: float,
    approval_limit_usd: float,
    workers: int,
) -> VeruSAGEAdapter:
    adapter = VeruSAGEAdapter(
        split_dir=cfg["split_dir"],
        verusage_src_root=cfg["verusage_src_root"],
        verus_bin=cfg["verus_bin"],
        lynette_bin=cfg["lynette_bin"],
        model="deepseek-v4-pro",
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
        retrieval_cards_path=str(cards_path) if cards_path else None,
        seed=int(cfg["seed"]),
    )
    setup_cfg = dict(cfg)
    setup_cfg["out_root"] = str(out_root)
    adapter.setup(setup_cfg)
    return adapter


def run_gate(
    *,
    config_path: Path,
    cards_path: Path,
    source_prediction_dir: Path,
    run_dir: Path,
    budget_state_path: Path | None,
    prior_spend_usd: float,
    approval_limit_usd: float,
    workers: int,
) -> dict[str, Any]:
    cfg = flatten_config(_expand(load_config(str(config_path), [])))
    run_dir.mkdir(parents=True, exist_ok=True)
    cards = load_retrieval_cards(cards_path)
    support_audit = _audit_support(cards, source_prediction_dir)
    _write_json(run_dir / "card_support_audit.json", support_audit)
    if not support_audit["passed"]:
        raise RuntimeError("retrieval card support audit failed")

    budget_state_path = budget_state_path or run_dir / "gate_budget.json"
    s0_adapter = _adapter(
        cfg,
        out_root=run_dir,
        budget_state_path=budget_state_path,
        cards_path=None,
        prior_spend_usd=prior_spend_usd,
        approval_limit_usd=approval_limit_usd,
        workers=workers,
    )
    retrieval_adapter = _adapter(
        cfg,
        out_root=run_dir,
        budget_state_path=budget_state_path,
        cards_path=cards_path,
        prior_spend_usd=prior_spend_usd,
        approval_limit_usd=approval_limit_usd,
        workers=workers,
    )
    batch = s0_adapter.dataloader.build_eval_batch(
        env_num=20,
        split="selection",
        seed=int(cfg["seed"]),
    )
    items = list(batch.payload or [])
    if len(items) != 20:
        raise ValueError(f"expected 20 selection items, found {len(items)}")
    skill_text = Path(cfg["skill_init"]).read_text(encoding="utf-8")
    s0_dir = run_dir / "s0"
    retrieval_dir = run_dir / "retrieval"
    with ThreadPoolExecutor(max_workers=2) as executor:
        s0_future = executor.submit(s0_adapter.rollout, items, skill_text, str(s0_dir))
        retrieval_future = executor.submit(
            retrieval_adapter.rollout,
            items,
            skill_text,
            str(retrieval_dir),
        )
        s0_results = s0_future.result()
        retrieval_results = retrieval_future.result()

    s0_hard, s0_soft = _score(s0_results)
    retrieval_hard, retrieval_soft = _score(retrieval_results)
    paired = _paired_summary(s0_results, retrieval_results)
    s0_cost = sum(float(row["usage"]["estimated_cost_usd"]) for row in s0_results)
    retrieval_cost = sum(
        float(row["usage"]["estimated_cost_usd"]) for row in retrieval_results
    )
    lynette_regressions = sum(
        bool(before.get("final_lynette_passed"))
        and not bool(after.get("final_lynette_passed"))
        for before, after in zip(s0_results, retrieval_results)
    )
    cost_ok = retrieval_cost <= s0_cost * 1.10
    transitions = paired["transitions"]
    gate_passed = (
        transitions["0_to_1"] >= 2
        and transitions["1_to_0"] == 0
        and lynette_regressions == 0
        and cost_ok
    )
    cost_ledger = write_cost_ledger(run_dir)
    budget_state = json.loads(budget_state_path.read_text(encoding="utf-8"))
    result = {
        "schema_version": "1",
        "status": "complete",
        "target_model": "deepseek-v4-pro",
        "selection_n": 20,
        "configured_workers_per_condition": workers,
        "configured_total_task_workers": workers * 2,
        "cards_sha256": hashlib.sha256(cards_path.read_bytes()).hexdigest(),
        "card_count": len(cards["cards"]),
        "abstain_threshold": cards["abstain_threshold"],
        "s0_hard": s0_hard,
        "s0_soft": s0_soft,
        "retrieval_hard": retrieval_hard,
        "retrieval_soft": retrieval_soft,
        "paired_transitions": transitions,
        "lynette_regressions": lynette_regressions,
        "s0_cost_usd": s0_cost,
        "retrieval_cost_usd": retrieval_cost,
        "retrieval_cost_ratio": retrieval_cost / s0_cost if s0_cost else None,
        "cost_within_10_percent": cost_ok,
        "internal_go": gate_passed,
        "budget": budget_state,
        "cost_ledger": cost_ledger,
    }
    _write_json(run_dir / "paired_results.json", paired)
    _write_json(run_dir / "gate_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cards", type=Path, required=True)
    parser.add_argument("--source-prediction-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--budget-state-path", type=Path)
    parser.add_argument("--prior-spend-usd", type=float, required=True)
    parser.add_argument("--approval-limit-usd", type=float, default=12.0)
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()
    result = run_gate(
        config_path=args.config,
        cards_path=args.cards,
        source_prediction_dir=args.source_prediction_dir,
        run_dir=args.run_dir,
        budget_state_path=args.budget_state_path,
        prior_spend_usd=args.prior_spend_usd,
        approval_limit_usd=args.approval_limit_usd,
        workers=args.workers,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
