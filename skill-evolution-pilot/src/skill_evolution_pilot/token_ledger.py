from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

from .workspace import sha256_file


REQUIRED_USAGE_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _raw_usage_events(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid raw Codex JSON at line {line_number}: {path}"
                ) from exc
            if isinstance(row, dict) and isinstance(row.get("usage"), dict):
                rows.append(row["usage"])
    return rows


def _nonnegative_int(usage: dict[str, Any], key: str) -> int:
    value = usage.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"usage field {key} must be a nonnegative integer")
    return value


def build_run_ledger(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "run_manifest.json"
    result_path = run_dir / "result.json"
    raw_events_path = run_dir / "codex_events.raw.jsonl"
    fidelity_path = run_dir / "fidelity_audit.json"
    required = (manifest_path, result_path, raw_events_path, fidelity_path)
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise ValueError(f"run is missing required artifacts: {missing}")

    manifest = _read_json(manifest_path)
    result = _read_json(result_path)
    fidelity = _read_json(fidelity_path)
    usage_events = _raw_usage_events(raw_events_path)
    if len(usage_events) != 1:
        raise ValueError(
            f"expected exactly one terminal usage event, found {len(usage_events)}"
        )
    usage = usage_events[0]
    values = {key: _nonnegative_int(usage, key) for key in REQUIRED_USAGE_FIELDS}
    reasoning_raw = usage.get("reasoning_output_tokens")
    reasoning_tokens = (
        None
        if reasoning_raw is None
        else _nonnegative_int(usage, "reasoning_output_tokens")
    )
    input_tokens = values["input_tokens"]
    cached_input_tokens = values["cached_input_tokens"]
    output_tokens = values["output_tokens"]
    if cached_input_tokens > input_tokens:
        raise ValueError("cached_input_tokens exceeds input_tokens")
    if reasoning_tokens is not None and reasoning_tokens > output_tokens:
        raise ValueError("reasoning_output_tokens exceeds output_tokens")

    uncached_input_tokens = input_tokens - cached_input_tokens
    provider_total_tokens = input_tokens + output_tokens
    primary_uncached_tokens = uncached_input_tokens + output_tokens
    visible_output_tokens = (
        None if reasoning_tokens is None else output_tokens - reasoning_tokens
    )
    validation = result.get("validation")
    if not isinstance(validation, dict):
        raise ValueError("result is missing validation")
    verus = validation.get("verus")
    lynette = validation.get("lynette")
    if not isinstance(verus, dict) or not isinstance(lynette, dict):
        raise ValueError("result is missing verifier records")
    success = bool(verus.get("passed") and lynette.get("passed"))

    return {
        "schema_version": "1",
        "run_id": result.get("run_id") or manifest.get("run_id"),
        "condition": "h0" if not manifest.get("skill_present") else "skill",
        "model": manifest.get("model"),
        "reasoning_effort": manifest.get("reasoning_effort"),
        "reasoning_summary": manifest.get("reasoning_summary"),
        "show_raw_agent_reasoning": manifest.get("show_raw_agent_reasoning"),
        "prompt_sha256": manifest.get("prompt_sha256"),
        "source_sha256": manifest.get("source_sha256"),
        "skill_sha256": manifest.get("skill_sha256"),
        "skill_bytes": manifest.get("skill_bytes"),
        "manifest_sha256": sha256_file(manifest_path),
        "result_sha256": sha256_file(result_path),
        "raw_events_sha256": sha256_file(raw_events_path),
        "f3": bool(fidelity.get("f3")),
        "success": success,
        "status": result.get("status"),
        "timed_out": bool(result.get("timed_out")),
        "wall_seconds": result.get("wall_seconds"),
        "usage_source": "codex_turn_completed",
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "uncached_input_tokens": uncached_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning_tokens,
        "visible_output_tokens_if_reasoning_is_subset": visible_output_tokens,
        "provider_total_tokens": provider_total_tokens,
        "primary_uncached_tokens": primary_uncached_tokens,
        "reasoning_count_available": reasoning_tokens is not None,
        "reasoning_is_subset_of_output": True,
        "reasoning_double_counted": False,
    }


def aggregate_ledgers(ledgers: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(ledgers)
    if not rows:
        raise ValueError("at least one ledger is required")
    if not all(row.get("f3") for row in rows):
        raise ValueError("all primary ledgers must pass F3")
    successes = sum(bool(row.get("success")) for row in rows)
    total_primary = sum(int(row["primary_uncached_tokens"]) for row in rows)
    total_provider = sum(int(row["provider_total_tokens"]) for row in rows)
    primary_etts = None if successes == 0 else total_primary / successes
    provider_etts = None if successes == 0 else total_provider / successes
    primary_values = [int(row["primary_uncached_tokens"]) for row in rows]
    provider_values = [int(row["provider_total_tokens"]) for row in rows]

    def variation(values: list[int]) -> dict[str, Any]:
        mean = statistics.fmean(values)
        sample_stdev = statistics.stdev(values) if len(values) > 1 else None
        return {
            "min": min(values),
            "max": max(values),
            "mean": mean,
            "sample_stdev": sample_stdev,
            "coefficient_of_variation": (
                None
                if sample_stdev is None or math.isclose(mean, 0.0)
                else sample_stdev / mean
            ),
        }

    return {
        "schema_version": "1",
        "attempt_count": len(rows),
        "success_count": successes,
        "solve_rate": successes / len(rows),
        "total_primary_uncached_tokens": total_primary,
        "total_provider_tokens": total_provider,
        "expected_primary_uncached_tokens_to_success": primary_etts,
        "expected_provider_tokens_to_success": provider_etts,
        "expected_tokens_to_success_is_infinite": successes == 0,
        "primary_uncached_token_variation": variation(primary_values),
        "provider_token_variation": variation(provider_values),
        "run_ids": [row.get("run_id") for row in rows],
    }


def write_ledger(run_dir: Path, output_path: Path) -> dict[str, Any]:
    if output_path.exists():
        raise ValueError(f"output already exists: {output_path}")
    ledger = build_run_ledger(run_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return ledger
