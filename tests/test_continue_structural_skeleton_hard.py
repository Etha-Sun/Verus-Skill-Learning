import copy

import pytest

from continue_structural_skeleton_hard import AUTHORIZATION, RETRY_KEYS, prior_charge, validate_attempts
from evaluate_structural_skeleton_hard import schedule


def stopped_summary():
    return {"bridge_drained": True, "reviewed_inputs_unchanged": True,
        "rows": [{"row": {"bridge_task_key": key, "timed_out": False, "proof_solved": False,
            "codex_returncode": 1, "fidelity": "V0_INVALID"}} for key in sorted(RETRY_KEYS)]}


def test_exact_authorized_replacements(tmp_path):
    jobs = schedule(tmp_path)
    validate_attempts({"schedule": jobs}, stopped_summary())
    assert len(jobs) == 18 and AUTHORIZATION["budget_usd"] == 15
    assert all("knowledge_path" not in job for job in jobs if job["condition"] == "p0")


@pytest.mark.parametrize("field,value", [("timed_out", True), ("proof_solved", True),
    ("codex_returncode", 0), ("fidelity", "V2_TRACE"), ("bridge_task_key", "unexpected")])
def test_no_outcome_selected_retry(tmp_path, field, value):
    summary = stopped_summary()
    summary["rows"][0]["row"][field] = value
    with pytest.raises(ValueError):
        validate_attempts({"schedule": schedule(tmp_path)}, summary)


def test_no_duplicate_or_extra_cells(tmp_path):
    summary = stopped_summary()
    summary["rows"].append(copy.deepcopy(summary["rows"][0]))
    with pytest.raises(ValueError):
        validate_attempts({"schedule": schedule(tmp_path)}, summary)


def test_prior_known_and_unknown_charges_carry():
    state = {"reservations": {}, "prior_spend_usd": 0, "target_spend_usd": .444126232,
        "uncertain_spend_usd": 1.83904512}
    assert prior_charge(state) == pytest.approx(2.283171352)
    state["reservations"] = {"pending": 1}
    with pytest.raises(ValueError):
        prior_charge(state)


@pytest.mark.parametrize("charge", [15, -1, float("nan"), float("inf")])
def test_invalid_or_exhausted_budget(charge):
    with pytest.raises(ValueError):
        prior_charge({"reservations": {}, "prior_spend_usd": 0,
            "target_spend_usd": charge, "uncertain_spend_usd": 0})
