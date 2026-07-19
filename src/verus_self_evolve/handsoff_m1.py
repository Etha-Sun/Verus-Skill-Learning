from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRAIN_DIRECTORIES = ("verified-anvil", "verified-ironkv")
KNOWN_MODELS = (
    "claude-opus-4.5",
    "claude-sonnet-4",
    "claude-sonnet-4.5",
    "gpt-5",
    "o4",
)
MOTIF_TERMS = {
    "invariant": ("invariant",),
    "sequence_set_map": ("sequence", "seq_", "seq!", "to_set", " map"),
    "quantifier_trigger": ("forall", "exists", "quantifier", "trigger"),
    "arithmetic_bounds": ("arithmetic", "integer", " usize", " nat", "bound"),
    "temporal_state": ("always", "eventually", "state machine", "transition"),
    "termination_recursion": ("decreases", "termination", "recursive", "induction"),
}
ERROR_TERMS = {
    "assertion_or_postcondition": ("assertion failed", "postcondition not satisfied"),
    "precondition_or_recommendation": ("precondition not satisfied", "recommendation not met"),
    "invariant_failure": ("invariant",),
    "type_or_coercion": ("mismatched types", "type mismatch", "as int", "as nat"),
    "bounds_or_index": ("out of bounds", "index", "bounds"),
    "solver_guidance": ("cannot prove", "can't prove", "smt solver", "verus needs"),
    "checker_repair": ("checker detected", "safety checker", "lynette"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _labels(text: str, patterns: dict[str, tuple[str, ...]]) -> list[str]:
    lowered = text.lower()
    return sorted(
        label for label, terms in patterns.items() if any(term in lowered for term in terms)
    )


def characterize_trace(row: dict[str, Any], log_text: str) -> dict[str, Any]:
    text = row["task_id"] + "\n" + log_text
    return {
        "motifs": _labels(text, MOTIF_TERMS) or ["other"],
        "error_families": _labels(text, ERROR_TERMS) or ["unspecified"],
    }


def _selection_score(
    row: dict[str, Any], motif_counts: Counter[str], error_counts: Counter[str], variant_counts: Counter[str]
) -> float:
    features = row["selection_features"]
    score = 8.0 / (1 + variant_counts[row["variant"]])
    score += sum(5.0 / (1 + motif_counts[label]) for label in features["motifs"])
    score += sum(5.0 / (1 + error_counts[label]) for label in features["error_families"])
    return score


def select_traces(
    rows: list[dict[str, Any]], corpus_root: Path, per_stratum: int = 3
) -> list[dict[str, Any]]:
    candidates = []
    for row in rows:
        if row.get("split") != "train" or row.get("directory_group") not in TRAIN_DIRECTORIES:
            continue
        if row.get("model") not in KNOWN_MODELS or not row.get("verified", {}).get("path"):
            continue
        log_path = corpus_root / row["relative_log_path"]
        if not log_path.is_file():
            continue
        enriched = dict(row)
        enriched["selection_features"] = characterize_trace(
            row, log_path.read_text(errors="replace")
        )
        candidates.append(enriched)

    selected: list[dict[str, Any]] = []
    used_sources: set[str] = set()
    used_tasks: set[str] = set()
    motif_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    variant_counts: Counter[str] = Counter()
    for round_index in range(per_stratum):
        for model in KNOWN_MODELS:
            for directory in TRAIN_DIRECTORIES:
                eligible = [
                    row
                    for row in candidates
                    if row["model"] == model
                    and row["directory_group"] == directory
                    and row["source"]["normalized_code_sha256"] not in used_sources
                    and row["normalized_task_id"] not in used_tasks
                ]
                if not eligible:
                    raise ValueError(
                        f"insufficient unique candidates for {model}/{directory} round {round_index}"
                    )
                eligible.sort(key=lambda row: row["trace_id"])
                chosen = max(
                    eligible,
                    key=lambda row: _selection_score(
                        row, motif_counts, error_counts, variant_counts
                    ),
                )
                selected.append(chosen)
                used_sources.add(chosen["source"]["normalized_code_sha256"])
                used_tasks.add(chosen["normalized_task_id"])
                motif_counts.update(chosen["selection_features"]["motifs"])
                error_counts.update(chosen["selection_features"]["error_families"])
                variant_counts.update([chosen["variant"]])
    return selected


def write_selection(
    manifest: Path, corpus_root: Path, out_dir: Path, per_stratum: int = 3
) -> dict[str, Any]:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {out_dir}")
    rows = [json.loads(line) for line in manifest.read_text().splitlines()]
    selected = select_traces(rows, corpus_root, per_stratum=per_stratum)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_rows = []
    for rank, row in enumerate(selected, start=1):
        output_rows.append(
            {
                "selection_rank": rank,
                "trace_id": row["trace_id"],
                "relative_log_path": row["relative_log_path"],
                "directory_group": row["directory_group"],
                "model": row["model"],
                "variant": row["variant"],
                "task_id": row["task_id"],
                "normalized_task_id": row["normalized_task_id"],
                "source": row["source"],
                "verified": row["verified"],
                "usage": row["usage"],
                "selection_features": row["selection_features"],
            }
        )
    (out_dir / "selected_traces.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output_rows)
    )
    summary = {
        "created_at": _now(),
        "status": "DONE",
        "selection_count": len(output_rows),
        "success_definition": "effective-train row with a paired verified artifact",
        "deduplication": ["normalized source hash", "normalized task id"],
        "per_model_directory_stratum": per_stratum,
        "directory_counts": dict(sorted(Counter(r["directory_group"] for r in output_rows).items())),
        "model_counts": dict(sorted(Counter(r["model"] for r in output_rows).items())),
        "variant_counts": dict(sorted(Counter(r["variant"] for r in output_rows).items())),
        "motif_counts": dict(sorted(Counter(x for r in output_rows for x in r["selection_features"]["motifs"]).items())),
        "error_family_counts": dict(sorted(Counter(x for r in output_rows for x in r["selection_features"]["error_families"]).items())),
        "unique_source_count": len({r["source"]["normalized_code_sha256"] for r in output_rows}),
        "unique_task_count": len({r["normalized_task_id"] for r in output_rows}),
        "sealed_content_scanned": 0,
        "method_evidence": False,
    }
    (out_dir / "selection_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    )
    run_manifest = {
        "created_at": _now(),
        "run_id": "R040",
        "input_manifest": str(manifest.resolve()),
        "corpus_root": str(corpus_root.resolve()),
        "raw_data_read_only": True,
        "allowed_directory_groups": list(TRAIN_DIRECTORIES),
        "excluded_models": ["unknown"],
        "selection_algorithm": "three deterministic greedy diversity rounds over each model/directory stratum",
        "outputs": ["selected_traces.jsonl", "selection_summary.json"],
    }
    (out_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2, ensure_ascii=False) + "\n"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(prog="handsoff-m1")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--per-stratum", type=int, default=3)
    args = parser.parse_args()
    print(
        json.dumps(
            write_selection(
                args.manifest, args.corpus_root, args.out_dir, args.per_stratum
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
