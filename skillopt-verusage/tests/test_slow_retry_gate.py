from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from skillopt_verusage.slow_retry_gate import _apply_decision


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    run_dir = tmp_path / "run"
    retry_dir = run_dir / "slow_update" / "epoch_02" / "retry_pointer_top3"
    pre_gate = retry_dir / "pre_gate"
    _write(pre_gate / "current_skill.md", "current")
    _write(pre_gate / "best_skill.md", "best")
    _write(pre_gate / "cost_ledger.json", json.dumps({"target": {"estimated_cost_usd": 3.0}}))
    _write(run_dir / "skills" / "skill_v0002.md", "current")
    _write(run_dir / "best_skill.md", "best")
    state = {
        "last_completed_step": 2,
        "current_skill_path": str(run_dir / "skills" / "skill_v0002.md"),
        "current_score": 0.7,
        "current_origin": "step_0001",
        "best_skill_path": str(run_dir / "best_skill.md"),
        "best_score": 0.7,
        "best_step": 1,
        "best_origin": "step_0001",
    }
    return run_dir, retry_dir, state


def test_apply_accept_new_best_is_idempotent(tmp_path: Path) -> None:
    run_dir, retry_dir, state = _fixture(tmp_path)
    retry_result = {
        "wall_seconds": 12.5,
        "result": {"reasoning": "reason", "slow_update_content": "guidance"},
    }
    decision = {
        "action": "accept_new_best",
        "candidate_hash": "candidate",
        "candidate_hard": 0.75,
        "candidate_soft": 0.75,
    }
    ledger = {"target": {"estimated_cost_usd": 4.25}}

    with patch(
        "skillopt_verusage.slow_retry_gate.write_cost_ledger",
        return_value=ledger,
    ):
        result = _apply_decision(
            run_dir, retry_dir, state, "candidate skill", retry_result, decision
        )
        _apply_decision(
            run_dir, retry_dir, state, "candidate skill", retry_result, decision
        )

    runtime = json.loads((run_dir / "runtime_state.json").read_text(encoding="utf-8"))
    assert (run_dir / "skills" / "skill_v0002.md").read_text() == "candidate skill"
    assert (run_dir / "best_skill.md").read_text() == "candidate skill"
    assert runtime["current_score"] == 0.75
    assert runtime["best_score"] == 0.75
    assert runtime["best_step"] == 2
    assert result["incremental_actor_cost_usd"] == 1.25


def test_apply_reject_restores_pre_gate_state(tmp_path: Path) -> None:
    run_dir, retry_dir, state = _fixture(tmp_path)
    _write(run_dir / "skills" / "skill_v0002.md", "partial mutation")
    decision = {
        "action": "reject",
        "candidate_hash": "candidate",
        "candidate_hard": 0.65,
        "candidate_soft": 0.65,
    }
    ledger = {"target": {"estimated_cost_usd": 3.5}}

    with patch(
        "skillopt_verusage.slow_retry_gate.write_cost_ledger",
        return_value=ledger,
    ):
        _apply_decision(
            run_dir,
            retry_dir,
            state,
            "candidate skill",
            {"wall_seconds": 1.0, "result": {"slow_update_content": "guidance"}},
            decision,
        )

    runtime = json.loads((run_dir / "runtime_state.json").read_text(encoding="utf-8"))
    assert (run_dir / "skills" / "skill_v0002.md").read_text() == "current"
    assert (run_dir / "best_skill.md").read_text() == "best"
    assert runtime == state
