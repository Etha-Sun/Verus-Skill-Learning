"""Orthogonal proof, budget, safety, and trace-fidelity classification."""

from __future__ import annotations

from typing import Any


TRACE_COMPLETE_CLASSES = {"V1_TRUNCATED", "V2_TRACE"}


def fidelity_class(result: dict[str, Any]) -> str:
    value = result.get("fidelity_class") or result.get("fidelity")
    return value if isinstance(value, str) else "V0_INVALID"


def safety_passed(result: dict[str, Any]) -> bool:
    if "safety_passed" in result:
        return bool(result["safety_passed"])
    validation = result.get("validation") or {}
    if "input_unchanged" in validation:
        return bool(validation["input_unchanged"])
    fidelity = result.get("fidelity") or {}
    if isinstance(fidelity, dict) and "input_unchanged" in fidelity:
        return bool(fidelity["input_unchanged"])
    return False


def proof_solved(result: dict[str, Any]) -> bool:
    if "proof_solved" in result:
        return bool(result["proof_solved"])
    validation = result.get("validation") or {}
    verus = validation.get("verus") or {}
    lynette = validation.get("lynette") or {}
    if "passed" in verus or "passed" in lynette:
        return bool(
            verus.get("passed") and lynette.get("passed") and safety_passed(result)
        )
    if "hard" in result:
        return bool(result["hard"] and safety_passed(result))
    return bool(result.get("status") == "SOLVED" and safety_passed(result))


def within_budget(result: dict[str, Any]) -> bool:
    if "within_budget" in result:
        return bool(result["within_budget"])
    return not bool(result.get("timed_out"))


def outcome_fields(result: dict[str, Any]) -> dict[str, Any]:
    fidelity = fidelity_class(result)
    return {
        "proof_solved": proof_solved(result),
        "within_budget": within_budget(result),
        "safety_passed": safety_passed(result),
        "trace_fidelity": fidelity,
        "trace_complete": fidelity in TRACE_COMPLETE_CLASSES,
    }
