from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .token_ledger import build_run_ledger


def compare_token_runs(
    baseline_dir: Path,
    candidate_dirs: Iterable[Path],
) -> dict[str, Any]:
    baseline = build_run_ledger(baseline_dir)
    candidates = [build_run_ledger(path) for path in candidate_dirs]
    if not candidates:
        raise ValueError("at least one candidate run is required")
    if not baseline["f3"] or not all(row["f3"] for row in candidates):
        raise ValueError("all compared runs must pass F3")
    source_hash = baseline["source_sha256"]
    if any(row["source_sha256"] != source_hash for row in candidates):
        raise ValueError("all compared runs must use the same source")
    model = baseline["model"]
    if any(row["model"] != model for row in candidates):
        raise ValueError("all compared runs must use the same model")

    baseline_tokens = int(baseline["primary_uncached_tokens"])
    rows = []
    for ledger in [baseline, *candidates]:
        tokens = int(ledger["primary_uncached_tokens"])
        success = bool(ledger["success"])
        rows.append(
            {
                "run_id": ledger["run_id"],
                "condition": ledger["condition"],
                "skill_sha256": ledger.get("skill_sha256"),
                "skill_bytes": ledger.get("skill_bytes"),
                "success": success,
                "primary_uncached_tokens": tokens,
                "delta_vs_h0": tokens - baseline_tokens,
                "relative_delta_vs_h0": (
                    (tokens - baseline_tokens) / baseline_tokens
                    if baseline_tokens
                    else None
                ),
                "expected_tokens_to_success": tokens if success else None,
                "expected_tokens_to_success_is_infinite": not success,
            }
        )
    ranked = sorted(
        rows[1:],
        key=lambda row: (
            not row["success"],
            row["primary_uncached_tokens"] if row["success"] else 0,
        ),
    )
    return {
        "schema_version": "1",
        "source_sha256": source_hash,
        "model": model,
        "baseline_run_id": baseline["run_id"],
        "all_f3": True,
        "rows": rows,
        "best_candidate_run_id": ranked[0]["run_id"],
        "worst_candidate_run_id": ranked[-1]["run_id"],
    }


def write_token_comparison(
    baseline_dir: Path,
    candidate_dirs: Iterable[Path],
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ValueError(f"output already exists: {output_path}")
    value = compare_token_runs(baseline_dir, candidate_dirs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return value
