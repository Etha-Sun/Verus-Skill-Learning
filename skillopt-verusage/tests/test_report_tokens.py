import json
from pathlib import Path

import pytest

from skillopt_verusage.report_tokens import export_test20_token_data, normalize_usage


def test_cached_input_is_part_of_total_and_reasoning_is_output_subset() -> None:
    row = normalize_usage(
        "GLM-5.3",
        {
            "usage": {
                "prompt_tokens": 100,
                "prompt_cache_hit_tokens": 80,
                "prompt_cache_miss_tokens": 20,
                "completion_tokens": 30,
                "reasoning_tokens": 10,
            }
        },
    )
    assert row["input_tokens"] == 100
    assert row["cached_input_tokens"] + row["uncached_input_tokens"] == 100
    assert row["nonreasoning_output_tokens"] + row["reasoning_output_tokens"] == 30


def test_qwen_reasoning_breakdown_is_marked_unavailable() -> None:
    row = normalize_usage(
        "Qwen3.8-27B BF16",
        {
            "usage": {
                "prompt_tokens": 100,
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": 100,
                "completion_tokens": 30,
                "reasoning_tokens": 0,
            }
        },
    )
    assert row["reasoning_breakdown_available"] is False
    assert row["reasoning_output_tokens"] is None


def test_export_rejects_non_test20_rows(tmp_path: Path) -> None:
    usage = {
        "input_tokens": 10,
        "cached_input_tokens": 3,
        "output_tokens": 2,
        "reasoning_output_tokens": 1,
    }
    matrix = {
        "reference_july": {
            model: {
                condition: {"n": 19, "usage": usage}
                for condition in ("blank", "S1", "S2")
            }
            for model in (
                "GPT-5.6 Sol",
                "DeepSeek V4 Pro",
                "GLM-5.3",
                "Qwen3.8-27B BF16",
            )
        }
    }
    path = tmp_path / "matrix.json"
    path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="all 20 tasks"):
        export_test20_token_data(path, tmp_path / "tokens.csv")
