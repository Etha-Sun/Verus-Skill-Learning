"""Normalize test-20 provider ledgers for comparable token reporting."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


MODEL_ORDER = (
    "GPT-5.6 Sol",
    "DeepSeek V4 Pro",
    "GLM-5.3",
    "Qwen3.8-27B BF16",
)
CONDITION_ORDER = ("blank", "S1", "S2")


def _nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer")
    return value


def normalize_usage(model: str, result: dict[str, Any]) -> dict[str, Any]:
    usage = result.get("usage")
    if not isinstance(usage, dict):
        raise ValueError(f"{model} result has no usage object")
    if "input_tokens" in usage:
        total_input = _nonnegative_int(usage.get("input_tokens"), "input_tokens")
        cached_input = _nonnegative_int(
            usage.get("cached_input_tokens"), "cached_input_tokens"
        )
        output = _nonnegative_int(usage.get("output_tokens"), "output_tokens")
        reasoning = _nonnegative_int(
            usage.get("reasoning_output_tokens"), "reasoning_output_tokens"
        )
        uncached_input = total_input - cached_input
    else:
        total_input = _nonnegative_int(usage.get("prompt_tokens"), "prompt_tokens")
        cached_input = _nonnegative_int(
            usage.get("prompt_cache_hit_tokens"), "prompt_cache_hit_tokens"
        )
        uncached_input = _nonnegative_int(
            usage.get("prompt_cache_miss_tokens"), "prompt_cache_miss_tokens"
        )
        output = _nonnegative_int(
            usage.get("completion_tokens"), "completion_tokens"
        )
        reasoning = _nonnegative_int(usage.get("reasoning_tokens"), "reasoning_tokens")
    if cached_input + uncached_input != total_input:
        raise ValueError(f"{model} cached + uncached input differs from total input")
    if reasoning > output:
        raise ValueError(f"{model} reasoning tokens exceed output tokens")
    reasoning_available = model != "Qwen3.8-27B BF16"
    return {
        "cached_input_tokens": cached_input,
        "uncached_input_tokens": uncached_input,
        "input_tokens": total_input,
        "output_tokens": output,
        "reasoning_output_tokens": reasoning if reasoning_available else None,
        "nonreasoning_output_tokens": output - reasoning if reasoning_available else None,
        "reasoning_breakdown_available": reasoning_available,
    }


def export_test20_token_data(matrix_path: Path, output_csv: Path) -> list[dict[str, Any]]:
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    section = matrix.get("reference_july")
    if not isinstance(section, dict):
        raise ValueError("matrix has no reference_july object")
    rows: list[dict[str, Any]] = []
    for model_order, model in enumerate(MODEL_ORDER):
        conditions = section.get(model)
        if not isinstance(conditions, dict):
            raise ValueError(f"matrix has no reference_july results for {model}")
        for condition_order, condition in enumerate(CONDITION_ORDER):
            result = conditions.get(condition)
            if not isinstance(result, dict):
                raise ValueError(f"missing {model}/{condition} result")
            n = _nonnegative_int(result.get("n"), "n")
            if n != 20:
                raise ValueError(f"{model}/{condition} must contain all 20 tasks")
            rows.append(
                {
                    "model_order": model_order,
                    "condition_order": condition_order,
                    "model": model,
                    "condition": condition,
                    "n": n,
                    **normalize_usage(model, result),
                    "usage_scope": (
                        "retained direct Responses usage"
                        if model == "GPT-5.6 Sol"
                        else "complete bridge ledger including archived attempts"
                    ),
                }
            )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows
