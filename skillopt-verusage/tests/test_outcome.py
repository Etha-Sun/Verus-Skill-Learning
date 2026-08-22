from skillopt_verusage.outcome import outcome_fields, proof_solved


def _result(*, timed_out: bool, input_unchanged: bool, fidelity: str):
    return {
        "timed_out": timed_out,
        "fidelity_class": fidelity,
        "validation": {
            "input_unchanged": input_unchanged,
            "verus": {"passed": True},
            "lynette": {"passed": True},
        },
    }


def test_solved_timeout_counts_but_is_outside_budget() -> None:
    outcome = outcome_fields(
        _result(timed_out=True, input_unchanged=True, fidelity="V1_TRUNCATED")
    )
    assert outcome == {
        "proof_solved": True,
        "within_budget": False,
        "safety_passed": True,
        "trace_fidelity": "V1_TRUNCATED",
        "trace_complete": True,
    }


def test_v0_does_not_invalidate_a_safe_proof() -> None:
    outcome = outcome_fields(
        _result(timed_out=False, input_unchanged=True, fidelity="V0_INVALID")
    )
    assert outcome["proof_solved"] is True
    assert outcome["trace_complete"] is False


def test_input_mutation_vetoes_a_verifier_pass() -> None:
    result = _result(
        timed_out=True, input_unchanged=False, fidelity="V1_TRUNCATED"
    )
    assert proof_solved(result) is False
