from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verus_self_evolve.data_layout import validate_output_path


FAILURE_OUTCOMES = {"FAILED", "TIMEOUT"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def prepare_paired_eval(
    taxonomy: Path,
    eval_traces: Path,
    source_manifest: Path,
    out_dir: Path,
) -> dict[str, Any]:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {out_dir}")
    taxonomy_data = json.loads(taxonomy.read_text(encoding="utf-8"))
    code_count = sum(
        len((taxonomy_data.get("full_layer") or {}).get(key, []))
        for key in ("category_a", "category_b", "category_c")
    )
    if code_count != 28:
        raise ValueError(f"expected the canonical 28-code taxonomy, got {code_count}")

    traces = [
        row
        for row in load_jsonl(eval_traces)
        if (row.get("metadata") or {}).get("outcome") in FAILURE_OUTCOMES
    ]
    if len(traces) != 8 or len({row.get("problem_id") for row in traces}) != 8:
        raise ValueError("expected exactly eight unique FAILED/TIMEOUT eval traces")
    source = json.loads(source_manifest.read_text(encoding="utf-8"))
    source_records = {
        row["problem_id"]: row for row in (source.get("eval") or {}).get("records", [])
    }
    records = []
    for index, trace in enumerate(traces, start=1):
        problem_id = trace["problem_id"]
        metadata = trace["metadata"]
        source_record = source_records.get(problem_id)
        if source_record is None or source_record.get("status") != metadata.get("outcome"):
            raise ValueError(f"source manifest mismatch: {problem_id}")
        records.append(
            {
                "pair_index": index,
                "problem_id": problem_id,
                "outcome": metadata["outcome"],
                "project": metadata.get("project"),
                "source_model": metadata.get("llm_name"),
                "source_ref": metadata.get("source_ref"),
                "source_sha256": source_record.get("source_sha256"),
            }
        )
    outcomes = Counter(row["outcome"] for row in records)
    source_models = Counter(row["source_model"] for row in records)
    if outcomes != Counter({"FAILED": 4, "TIMEOUT": 4}):
        raise ValueError(f"unbalanced outcome contract: {dict(outcomes)}")
    if set(source_models.values()) != {2} or len(source_models) != 4:
        raise ValueError(f"unbalanced source-model contract: {dict(source_models)}")

    out_dir.mkdir(parents=True)
    trace_path = out_dir / "eval_failures.jsonl"
    with trace_path.open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace, ensure_ascii=False) + "\n")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest_version": 1,
        "purpose": "paired_atlas_failure_diagnosis",
        "status": "FROZEN",
        "taxonomy_source_sha256": sha256_file(taxonomy),
        "taxonomy_copy_sha256": None,
        "taxonomy_code_count": code_count,
        "eval_source_sha256": sha256_file(eval_traces),
        "eval_failure_copy_sha256": sha256_file(trace_path),
        "source_manifest_sha256": sha256_file(source_manifest),
        "trace_count": len(records),
        "outcome_counts": dict(sorted(outcomes.items())),
        "source_model_counts": dict(sorted(source_models.items())),
        "records": records,
        "arms": {
            "small": {
                "model": "qwen35-27b",
                "transport": "openai-compatible",
                "decoding": {"temperature": 0, "enable_thinking": False},
            },
            "large": {
                "model": "gpt-5.6-sol",
                "transport": "codex-cli",
                "reasoning_effort": "high",
            },
        },
        "repetitions": 1,
        "accuracy_gold_available": False,
        "large_model_is_gold": False,
        "raw_data_read_only": True,
    }
    taxonomy_copy = out_dir / "taxonomy.json"
    taxonomy_copy.write_text(taxonomy.read_text(encoding="utf-8"), encoding="utf-8")
    manifest["taxonomy_copy_sha256"] = sha256_file(taxonomy_copy)
    manifest_path = out_dir / "pair_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze the paired ATLAS eval set")
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--eval-traces", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = prepare_paired_eval(
        args.taxonomy,
        args.eval_traces,
        args.source_manifest,
        validate_output_path(args.out),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
