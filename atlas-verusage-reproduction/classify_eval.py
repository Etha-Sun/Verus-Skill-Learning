from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import threading
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verus_self_evolve.data_layout import validate_output_path
from run_taxonomy import CodexCLIClient
from vendor.atlas.classifier import TaxonomyClassifier
from vendor.atlas.config import PipelineConfig
from vendor.atlas.llm import extract_json
from vendor.atlas.traces.loader import load_traces


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class OpenAICompatibleClient:
    def __init__(
        self,
        model: str,
        base_url: str,
        log_dir: Path,
        timeout: int,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.log_dir = log_dir
        self.timeout = timeout
        self.call_index = 0
        self.last_response = ""
        self.lock = threading.Lock()
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def chat(self, prompt: str, system: str = "") -> str:
        with self.lock:
            self.call_index += 1
            call_id = f"call_{self.call_index:02d}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 1024,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
        )
        started = time.monotonic()
        response_body = ""
        error = None
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_body = response.read().decode("utf-8")
            response = json.loads(response_body)
            content = response["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            response = {}
            content = "{}"
        record = {
            "call_id": call_id,
            "transport": "openai-compatible",
            "model": self.model,
            "base_url": self.base_url,
            "prompt_chars": len(full_prompt),
            "prompt_sha256": hashlib.sha256(full_prompt.encode()).hexdigest(),
            "response_chars": len(content),
            "response_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "wall_time_seconds": time.monotonic() - started,
            "usage": response.get("usage"),
            "error": error,
        }
        (self.log_dir / f"{call_id}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (self.log_dir / f"{call_id}.response.txt").write_text(content, encoding="utf-8")
        if response_body:
            (self.log_dir / f"{call_id}.raw.json").write_text(response_body, encoding="utf-8")
        self.last_response = content
        return content


def _require_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"output directory must be empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def validate_pair_contract(
    pair_manifest_path: Path,
    taxonomy_path: Path,
    traces_path: Path,
    arm: str,
    model: str,
    transport: str,
) -> dict[str, Any]:
    manifest = json.loads(pair_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN" or manifest.get("trace_count") != 8:
        raise ValueError("pair manifest is not a frozen eight-trace contract")
    if sha256_file(taxonomy_path) != manifest.get("taxonomy_copy_sha256"):
        raise ValueError("taxonomy does not match the pair manifest")
    if sha256_file(traces_path) != manifest.get("eval_failure_copy_sha256"):
        raise ValueError("eval traces do not match the pair manifest")
    expected_arm = (manifest.get("arms") or {}).get(arm)
    if expected_arm is None:
        raise ValueError(f"unknown pair arm: {arm}")
    if expected_arm.get("model") != model or expected_arm.get("transport") != transport:
        raise ValueError(f"model/transport do not match the frozen {arm} arm")
    return manifest


def strict_response_validity(raw_data: dict[str, Any], valid_codes: set[str]) -> tuple[bool, bool]:
    required_fields = {"code", "label", "evidence", "confidence", "recovery_hint"}
    return required_fields.issubset(raw_data), raw_data.get("code") in valid_codes


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify held-out VeruSAGE failures")
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--pair-manifest", type=Path, required=True)
    parser.add_argument("--arm", choices=("small", "large"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument(
        "--transport", choices=("codex-cli", "openai-compatible"), default="codex-cli"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    args.out = validate_output_path(args.out)

    pair_manifest = validate_pair_contract(
        args.pair_manifest,
        args.taxonomy,
        args.traces,
        args.arm,
        args.model,
        args.transport,
    )
    expected_arm = pair_manifest["arms"][args.arm]
    if (
        args.arm == "large"
        and expected_arm.get("reasoning_effort") != args.reasoning_effort
    ):
        raise ValueError("reasoning effort does not match the frozen large arm")

    _require_empty(args.out)
    traces = [
        trace
        for trace in load_traces(args.traces, verbose=False)
        if trace.get("metadata", {}).get("outcome") in {"FAILED", "TIMEOUT"}
    ]
    if len(traces) != 8 or len({trace.get("problem_id") for trace in traces}) != 8:
        raise ValueError("paired classification requires exactly eight unique failures")
    expected_problem_ids = [row["problem_id"] for row in pair_manifest["records"]]
    if [trace.get("problem_id") for trace in traces] != expected_problem_ids:
        raise ValueError("trace order does not match the pair manifest")
    os.environ.setdefault("OPENAI_API_KEY", "transport-placeholder")
    config = PipelineConfig(model=args.model, timeout=args.timeout)
    classifier = TaxonomyClassifier(args.taxonomy, config=config)
    if args.transport == "codex-cli":
        classifier.client = CodexCLIClient(
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            log_dir=args.out / "calls",
            timeout=args.timeout,
        )
    else:
        classifier.client = OpenAICompatibleClient(
            model=args.model,
            base_url=args.base_url,
            log_dir=args.out / "calls",
            timeout=args.timeout,
        )

    run_manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "taxonomy": str(args.taxonomy.resolve()),
        "taxonomy_sha256": sha256_file(args.taxonomy),
        "eval_source": str(args.traces.resolve()),
        "eval_source_sha256": sha256_file(args.traces),
        "problem_ids": [trace.get("problem_id") for trace in traces],
        "pair_manifest": str(args.pair_manifest.resolve()),
        "pair_manifest_sha256": sha256_file(args.pair_manifest),
        "arm": args.arm,
        "model": args.model,
        "transport": args.transport,
        "reasoning_effort": args.reasoning_effort if args.transport == "codex-cli" else None,
        "base_url": args.base_url if args.transport == "openai-compatible" else None,
        "timeout": args.timeout,
        "decoding": (
            {"temperature": 0, "enable_thinking": False}
            if args.transport == "openai-compatible"
            else {"provider_default_sampling": True}
        ),
        "codex_version": (
            subprocess.run(
                ["codex", "--version"], capture_output=True, text=True, check=False
            ).stdout.strip()
            if args.transport == "codex-cli"
            else None
        ),
    }
    (args.out / "run_manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    output_path = args.out / "diagnoses.jsonl"
    diagnoses = []
    valid_codes = {item["code"] for item in classifier.codes}
    client = classifier.client
    with output_path.open("w", encoding="utf-8") as output:
        for trace in traces:
            diagnosis = classifier.classify(trace)
            raw_data = extract_json(getattr(client, "last_response", "")) or {}
            raw_code = raw_data.get("code")
            strict_schema_valid, strict_code_valid = strict_response_validity(
                raw_data, valid_codes
            )
            row = {
                "problem_id": trace.get("problem_id"),
                "task_outcome": trace.get("metadata", {}).get("outcome"),
                "source_ref": trace.get("metadata", {}).get("source_ref"),
                "diagnosis": diagnosis.to_dict() if diagnosis else None,
                "raw_code": raw_code,
                "strict_schema_valid": strict_schema_valid,
                "strict_code_valid": strict_code_valid,
                "vendor_code_coerced": bool(
                    diagnosis and raw_code and diagnosis.code != raw_code
                ),
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
    strict_valid = [
        row
        for row in diagnoses
        if row["diagnosis"] and row["strict_schema_valid"] and row["strict_code_valid"]
    ]
    summary = {
        "taxonomy": str(args.taxonomy),
        "eval_source": str(args.traces),
        "model": args.model,
        "transport": args.transport,
        "reasoning_effort": args.reasoning_effort,
        "eligible_failure_traces": len(traces),
        "diagnosed_traces": len(valid),
        "strict_valid_diagnoses": len(strict_valid),
        "vendor_code_coercions": sum(row["vendor_code_coerced"] for row in diagnoses),
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
