from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any


SCHEMA_VERSION = "verus-progress-v1"
METRIC_NAME = "verifier-gated-patch-f1"
VERIFICATION_RESULTS_RE = re.compile(
    r"verification results::\s*(?P<verified>\d+)\s+verified,\s*"
    r"(?P<errors>\d+)\s+errors?",
    re.IGNORECASE,
)
VERIFIER_TIERS = {
    "compile_failure_or_unparsed": 0,
    "proof_failure": 1,
    "verified": 2,
}


def normalize_code_lines(source: str) -> list[str]:
    """Remove blank lines and normalize whitespace without changing tokens."""
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in source.splitlines()
        if line.strip()
    ]


def _patch_atoms(
    baseline: list[str], candidate: list[str]
) -> Counter[tuple[str, str]]:
    atoms: Counter[tuple[str, str]] = Counter()
    matcher = SequenceMatcher(None, baseline, candidate, autojunk=False)
    for tag, base_start, base_end, candidate_start, candidate_end in matcher.get_opcodes():
        if tag in {"delete", "replace"}:
            atoms.update(("-", line) for line in baseline[base_start:base_end])
        if tag in {"insert", "replace"}:
            atoms.update(("+", line) for line in candidate[candidate_start:candidate_end])
    return atoms


def patch_f1_scores(
    baseline_source: str,
    candidate_source: str,
    verified_reference_source: str,
) -> dict[str, float | int]:
    """Compare candidate edits with one known verified patch.

    The score is hindsight-only: the verified reference must never be exposed
    to a live proof-repair actor or a held-out evaluation prompt.
    """
    baseline = normalize_code_lines(baseline_source)
    candidate = normalize_code_lines(candidate_source)
    reference = normalize_code_lines(verified_reference_source)
    reference_atoms = _patch_atoms(baseline, reference)
    if not reference_atoms:
        raise ValueError("verified reference must differ from the baseline")
    candidate_atoms = _patch_atoms(baseline, candidate)
    overlap = sum((candidate_atoms & reference_atoms).values())
    candidate_count = sum(candidate_atoms.values())
    reference_count = sum(reference_atoms.values())
    precision = overlap / candidate_count if candidate_count else 0.0
    recall = overlap / reference_count
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "matched_atoms": overlap,
        "candidate_atoms": candidate_count,
        "reference_atoms": reference_count,
        "patch_precision": precision,
        "patch_recall": recall,
        "patch_f1": f1,
    }


def verifier_state(output: str) -> dict[str, Any]:
    match = VERIFICATION_RESULTS_RE.search(output)
    if not match:
        tier = "compile_failure_or_unparsed"
        verified = None
        errors = None
    else:
        verified = int(match.group("verified"))
        errors = int(match.group("errors"))
        tier = "verified" if errors == 0 else "proof_failure"
    return {
        "tier": tier,
        "tier_rank": VERIFIER_TIERS[tier],
        "verified_functions": verified,
        "reported_errors": errors,
    }


def verifier_gated_patch_progress(
    baseline_source: str,
    candidate_source: str,
    verified_reference_source: str,
    verifier_output: str,
) -> dict[str, Any]:
    """Return the lexicographic progress key ``(verifier tier, patch F1)``."""
    patch = patch_f1_scores(
        baseline_source,
        candidate_source,
        verified_reference_source,
    )
    verifier = verifier_state(verifier_output)
    return {
        "schema_version": SCHEMA_VERSION,
        "metric": METRIC_NAME,
        "hindsight_only": True,
        "verifier": verifier,
        "patch": patch,
        "progress_key": [verifier["tier_rank"], patch["patch_f1"]],
    }
