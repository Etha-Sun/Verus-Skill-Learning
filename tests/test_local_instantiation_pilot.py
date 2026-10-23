import copy
import hashlib
import json

import pytest

from local_instantiation_extraction import AUTHORIZATION, guards, representation_audit
from skillopt_verusage.guarded_deepseek import BudgetMux
from evaluate_local_instantiation import CASES, schedule, selected_cards


def example(action="Inspect the current declaration and typed object."):
    groups = [{"trace_ids": ["train:original"], "source_task": "train",
               "evidence_ids": ["train:original/event:1"], "forbidden_names": ["target_function"]}]
    response = {"trace_analyses": [{"trace_id": "train:original", "observation": "One observed transition."}],
        "cards": [{"content": f"**Trigger:** A local obligation fails. **Action:** {action} **Why:** Conditional observation. **Validate:** Recheck the same obligation. **Avoid when:** Premise missing.",
                   "evidence_refs": ["train:original/event:1"], "source_tasks": ["train"], "limitations": ["Single source."]}]}
    return response, groups


def test_fragment_gate_retains_provenance_and_proof_boundaries():
    response, groups = example("Inspect `predicate(object)` using the declaration's typed object; this is a probe, not a fact.")
    representation_audit(response, groups, "revised")
    with pytest.raises(ValueError):
        representation_audit(response, groups, "old")
    for action in ("Insert `assert(predicate(object))`.", "Use `x; y`.", "Use `a` and `b` and `c`.", "Use target_function."):
        bad, _ = example(action)
        with pytest.raises(ValueError):
            representation_audit(bad, groups, "revised")
    bad = copy.deepcopy(response)
    bad["cards"][0]["evidence_refs"] = ["validation/event:1"]
    with pytest.raises(ValueError):
        representation_audit(bad, groups, "revised")
    bad = copy.deepcopy(response)
    bad["trace_analyses"] = []
    with pytest.raises(ValueError):
        representation_audit(bad, groups, "revised")


def test_global_and_phase_caps_rollback_unsent_and_keep_unknown_cost(tmp_path):
    assert AUTHORIZATION["total_usd"] == 15
    extraction = BudgetMux(guards(tmp_path, "extraction"))
    key = extraction.reserve(3.45)
    with pytest.raises(Exception):
        extraction.reserve(2)
    total = json.loads((tmp_path / "budget-total.json").read_text())
    assert len(total["reservations"]) == 1
    extraction.settle(key, cost_usd=None, usage={})
    with pytest.raises(RuntimeError, match="Unknown provider cost"):
        BudgetMux(guards(tmp_path, "evaluation")).reserve(.1)


def test_matrix_covers_each_cell_once_and_reverses_order(tmp_path):
    jobs = schedule(tmp_path)
    assert len(jobs) == 12
    assert {(j["id"], j["condition"], j["repeat"]) for j in jobs} == {
        (case["task"], arm, repeat) for case in CASES for arm in ("old", "revised") for repeat in range(2)}
    for case in CASES:
        orders = [[j["condition"] for j in jobs if j["id"] == case["task"] and j["repeat"] == r] for r in range(2)]
        assert orders[0] == orders[1][::-1]


def test_candidate_selection_requires_complete_hash_bound_review(tmp_path):
    path = tmp_path / "learning/banks/old/cards.json"
    path.parent.mkdir(parents=True)
    content = example()[0]["cards"][0]["content"]
    card = {"id": "card-001", "content": content}
    path.write_text(json.dumps({"cards": [card]}))
    decision = {"id": card["id"], "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "decision": "accept", "reason": "Supported inspection mechanism.", "families": ["temporal-transfer"]}
    selection = {"arms": {"old": [decision]}}
    assert selected_cards(tmp_path, selection, "old", "temporal-transfer") == [card]
    with pytest.raises(ValueError, match="No reviewed guidance"):
        selected_cards(tmp_path, selection, "old", "semantic-equality")
    decision["content_sha256"] = "changed"
    with pytest.raises(ValueError, match="changed"):
        selected_cards(tmp_path, selection, "old", "temporal-transfer")


def test_recovery_keeps_evidence_and_inherits_prior_cost(tmp_path):
    from recover_local_instantiation import ReminderClient, guards as recovery_guards
    class Capture:
        def payload(self, **kwargs):
            return kwargs
    adapter = ReminderClient(Capture(), {"cards": "Revised output rules"})
    from skillopt_verusage.campaign_evidence import shared_strings
    packet = shared_strings({"current_skill": "unchanged", "task_groups": [{"source_task": "training"}],
                             "contract": {"n": 2}})
    packet["output_contract_reminder"] = {"cards": "Old output rules"}
    changed = json.loads(adapter.payload(system="system", user=json.dumps(packet), cap=16384)["user"])
    assert {k:v for k,v in packet.items() if k != "output_contract_reminder"} == {
        k:v for k,v in changed.items() if k != "output_contract_reminder"}
    (tmp_path / "recovery.json").write_text(json.dumps({"inherited_cost_usd": 2.56963344}))
    mux = BudgetMux(recovery_guards(tmp_path, "extraction"))
    key = mux.reserve(3.468)
    mux.settle(key, cost_usd=1, usage={})
    with pytest.raises(Exception):
        mux.reserve(3.5)
    assert json.loads((tmp_path / "budget-total.json").read_text())["prior_spend_usd"] == 2.56963344
    evaluation = recovery_guards(tmp_path, "evaluation")
    assert evaluation[1].approval_limit_usd == 8
    assert evaluation[1].prior_spend_usd == 0
