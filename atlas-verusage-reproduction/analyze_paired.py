from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verus_self_evolve.data_layout import validate_output_path
from vendor.atlas.classifier import _flatten_codes
from vendor.atlas.llm import extract_json


REQUIRED_FIELDS = {"code", "label", "evidence", "confidence", "recovery_hint"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _quoted_support(evidence: str, trace_text: str) -> dict[str, Any]:
    quoted = [
        value.strip()
        for value in re.findall(r"['\"`]([^'\"`]{8,})['\"`]", evidence)
    ]
    trace = _normalize(trace_text)
    supported = [value for value in quoted if _normalize(value) in trace]
    return {
        "quoted_span_count": len(quoted),
        "supported_quoted_span_count": len(supported),
        "all_quoted_spans_supported": bool(quoted) and len(supported) == len(quoted),
    }


def _strict_rows(arm_dir: Path, valid_codes: set[str]) -> list[dict[str, Any]]:
    diagnoses = load_jsonl(arm_dir / "diagnoses.jsonl")
    calls = sorted((arm_dir / "calls").glob("call_[0-9][0-9].json"))
    responses = sorted((arm_dir / "calls").glob("call_*.response.txt"))
    if len(diagnoses) != 8 or len(calls) != 8 or len(responses) != 8:
        raise ValueError(f"incomplete arm outputs: {arm_dir}")
    rows = []
    for diagnosis, call_path, response_path in zip(diagnoses, calls, responses):
        call = json.loads(call_path.read_text(encoding="utf-8"))
        raw = extract_json(response_path.read_text(encoding="utf-8")) or {}
        raw_code = raw.get("code")
        rows.append(
            {
                **diagnosis,
                "raw_diagnosis": raw,
                "raw_code": raw_code,
                "strict_schema_valid": REQUIRED_FIELDS.issubset(raw),
                "strict_code_valid": raw_code in valid_codes,
                "vendor_code_coerced": bool(
                    diagnosis.get("diagnosis")
                    and diagnosis["diagnosis"].get("code") != raw_code
                ),
                "prompt_sha256": call.get("prompt_sha256"),
                "call_record_sha256": sha256_file(call_path),
                "response_sha256": sha256_file(response_path),
            }
        )
    return rows


def analyze(
    pair_manifest_path: Path,
    small_dir: Path,
    large_dir: Path,
    out_dir: Path,
) -> dict[str, Any]:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {out_dir}")
    pair_manifest = json.loads(pair_manifest_path.read_text(encoding="utf-8"))
    input_dir = pair_manifest_path.parent
    taxonomy_path = input_dir / "taxonomy.json"
    traces_path = input_dir / "eval_failures.jsonl"
    if sha256_file(taxonomy_path) != pair_manifest.get("taxonomy_copy_sha256"):
        raise ValueError("taxonomy hash mismatch")
    if sha256_file(traces_path) != pair_manifest.get("eval_failure_copy_sha256"):
        raise ValueError("trace hash mismatch")
    expected_ids = [row["problem_id"] for row in pair_manifest["records"]]
    traces = load_jsonl(traces_path)
    trace_by_id = {row["problem_id"]: row for row in traces}
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    valid_codes = {row["code"] for row in _flatten_codes(taxonomy)}

    arm_specs = (
        ("small", small_dir, pair_manifest["arms"]["small"]),
        ("large", large_dir, pair_manifest["arms"]["large"]),
    )
    arms: dict[str, list[dict[str, Any]]] = {}
    arm_manifests = {}
    for name, arm_dir, expected in arm_specs:
        run_manifest = json.loads((arm_dir / "run_manifest.json").read_text())
        if (
            run_manifest.get("taxonomy_sha256") != pair_manifest["taxonomy_copy_sha256"]
            or run_manifest.get("eval_source_sha256") != pair_manifest["eval_failure_copy_sha256"]
            or run_manifest.get("problem_ids") != expected_ids
            or run_manifest.get("model") != expected["model"]
            or run_manifest.get("transport") != expected["transport"]
            or (
                name == "large"
                and run_manifest.get("reasoning_effort") != expected.get("reasoning_effort")
            )
        ):
            raise ValueError(f"{name} arm does not match the pair contract")
        arm_manifests[name] = {
            "run_manifest_sha256": sha256_file(arm_dir / "run_manifest.json"),
            "model": run_manifest["model"],
            "transport": run_manifest["transport"],
        }
        arms[name] = _strict_rows(arm_dir, valid_codes)
        if [row["problem_id"] for row in arms[name]] != expected_ids:
            raise ValueError(f"{name} diagnosis order mismatch")

    paired = []
    for index, problem_id in enumerate(expected_ids):
        small = arms["small"][index]
        large = arms["large"][index]
        trace = trace_by_id[problem_id]
        if small["prompt_sha256"] != large["prompt_sha256"]:
            raise ValueError(f"visible prompt mismatch: {problem_id}")
        small_raw = small["raw_diagnosis"]
        large_raw = large["raw_diagnosis"]
        flip = int(hashlib.sha256(problem_id.encode()).hexdigest(), 16) % 2
        blinded = [small_raw, large_raw] if not flip else [large_raw, small_raw]
        paired.append(
            {
                "problem_id": problem_id,
                "outcome": trace["metadata"]["outcome"],
                "project": trace["metadata"].get("project"),
                "source_model": trace["metadata"].get("llm_name"),
                "visible_prompt_sha256": small["prompt_sha256"],
                "small": {
                    **small_raw,
                    **_quoted_support(small_raw.get("evidence", ""), trace["raw_trajectory"]),
                },
                "large": {
                    **large_raw,
                    **_quoted_support(large_raw.get("evidence", ""), trace["raw_trajectory"]),
                },
                "exact_code_agreement": small["raw_code"] == large["raw_code"],
                "category_agreement": str(small["raw_code"])[:1] == str(large["raw_code"])[:1],
                "blind_label_mapping": {
                    "A": "small" if not flip else "large",
                    "B": "large" if not flip else "small",
                },
                "blind_A": blinded[0],
                "blind_B": blinded[1],
            }
        )

    strict_valid = {
        name: sum(row["strict_schema_valid"] and row["strict_code_valid"] for row in rows)
        for name, rows in arms.items()
    }
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "VALID" if strict_valid == {"small": 8, "large": 8} else "INVALID",
        "pair_manifest_sha256": sha256_file(pair_manifest_path),
        "arm_manifests": arm_manifests,
        "pair_count": len(paired),
        "strict_valid_diagnoses": strict_valid,
        "vendor_code_coercions": {
            name: sum(row["vendor_code_coerced"] for row in rows)
            for name, rows in arms.items()
        },
        "visible_prompt_hash_matches": len(paired),
        "exact_code_agreement_count": sum(row["exact_code_agreement"] for row in paired),
        "category_agreement_count": sum(row["category_agreement"] for row in paired),
        "small_code_counts": dict(sorted(Counter(row["raw_code"] for row in arms["small"]).items())),
        "large_code_counts": dict(sorted(Counter(row["raw_code"] for row in arms["large"]).items())),
        "accuracy_gold_available": False,
        "confidence_is_accuracy": False,
        "evidence_boundary": "one-repetition qualitative operational comparison",
    }
    out_dir.mkdir(parents=True)
    (out_dir / "paired_diagnoses.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in paired),
        encoding="utf-8",
    )
    blinded = [
        {
            "problem_id": row["problem_id"],
            "outcome": row["outcome"],
            "project": row["project"],
            "source_model": row["source_model"],
            "diagnosis_A": row["blind_A"],
            "diagnosis_B": row["blind_B"],
        }
        for row in paired
    ]
    (out_dir / "blinded_pairs_for_review.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in blinded),
        encoding="utf-8",
    )
    (out_dir / "strict_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Strictly audit paired ATLAS diagnoses")
    parser.add_argument("--pair-manifest", type=Path, required=True)
    parser.add_argument("--small", type=Path, required=True)
    parser.add_argument("--large", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        args.pair_manifest,
        args.small,
        args.large,
        validate_output_path(args.out),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
