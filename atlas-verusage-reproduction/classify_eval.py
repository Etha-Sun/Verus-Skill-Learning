from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from verus_self_evolve.data_layout import validate_output_path
from run_taxonomy import CodexCLIClient
from vendor.atlas.classifier import TaxonomyClassifier
from vendor.atlas.config import PipelineConfig
from vendor.atlas.traces.loader import load_traces


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify held-out VeruSAGE failures")
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    args.out = validate_output_path(args.out)

    args.out.mkdir(parents=True, exist_ok=True)
    traces = [
        trace
        for trace in load_traces(args.traces, verbose=False)
        if trace.get("metadata", {}).get("outcome") in {"FAILED", "TIMEOUT"}
    ]
    os.environ.setdefault("OPENAI_API_KEY", "codex-cli-transport-unused")
    config = PipelineConfig(model=args.model, timeout=args.timeout)
    classifier = TaxonomyClassifier(args.taxonomy, config=config)
    classifier.client = CodexCLIClient(
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        log_dir=args.out / "codex_calls",
        timeout=args.timeout,
    )

    output_path = args.out / "diagnoses.jsonl"
    diagnoses = []
    with output_path.open("w", encoding="utf-8") as output:
        for trace in traces:
            diagnosis = classifier.classify(trace)
            row = {
                "problem_id": trace.get("problem_id"),
                "task_outcome": trace.get("metadata", {}).get("outcome"),
                "source_ref": trace.get("metadata", {}).get("source_ref"),
                "diagnosis": diagnosis.to_dict() if diagnosis else None,
            }
            diagnoses.append(row)
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            output.flush()
            print(
                f"{row['problem_id']}: "
                f"{row['diagnosis']['code'] if row['diagnosis'] else 'NO_DIAGNOSIS'}",
                flush=True,
            )

    valid = [row["diagnosis"] for row in diagnoses if row["diagnosis"]]
    summary = {
        "taxonomy": str(args.taxonomy),
        "eval_source": str(args.traces),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "eligible_failure_traces": len(traces),
        "diagnosed_traces": len(valid),
        "diagnosis_coverage": len(valid) / len(traces) if traces else 0.0,
        "code_counts": dict(sorted(Counter(item["code"] for item in valid).items())),
        "category_counts": dict(sorted(Counter(item["category"] for item in valid).items())),
        "mean_self_reported_confidence": (
            sum(item["confidence"] for item in valid) / len(valid) if valid else 0.0
        ),
        "accuracy_note": "No human failure-code gold labels exist; diagnosis accuracy is not estimated.",
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
