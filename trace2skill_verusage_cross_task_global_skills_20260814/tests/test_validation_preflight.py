from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_CODE = ROOT / "trace2skill_verusage_cross_task_global_skills_20260814" / "code"
BASELINE_CODE = ROOT / "trace2skill_verusage_baseline_test" / "code"
sys.path.insert(0, str(EXPERIMENT_CODE))
sys.path.insert(0, str(BASELINE_CODE))

from build_validation_preflight import prior_baseline, scaled_projection  # noqa: E402
from verus_agent.codex_harness.upstream_skillopt.budget_guard import (  # noqa: E402
    rates_for_model,
)


class ValidationPreflightTests(unittest.TestCase):
    def test_scaled_projection_preserves_integer_usage_counts(self) -> None:
        projected = scaled_projection(
            {
                "provider_request_count": 2.5,
                "provider_total_tokens": 100.25,
                "primary_uncached_tokens": 20.5,
                "reasoning_tokens": 10.0,
                "wall_time_seconds": 3.25,
                "estimated_cost_usd": 0.01,
            },
            20,
        )
        self.assertEqual(50, projected["provider_request_count"])
        self.assertEqual(2005, projected["provider_total_tokens"])
        self.assertEqual(65.0, projected["wall_time_seconds"])
        self.assertEqual(0.2, projected["estimated_cost_usd"])

    def test_prior_baseline_emits_aggregate_only_planning_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            path.write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "task_id": "heldout-private-id",
                                "wall_time_seconds": 2.0,
                            }
                        ],
                        "usage": {
                            "prompt_cache_hit_tokens": 100,
                            "prompt_cache_miss_tokens": 200,
                            "completion_tokens": 50,
                            "reasoning_tokens": 25,
                            "request_count": 2,
                            "total_tokens": 350,
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = prior_baseline(path, rates_for_model("deepseek-v4-pro"))
        self.assertNotIn("heldout-private-id", json.dumps(result))
        self.assertEqual(250, result["aggregate_only"]["primary_uncached_tokens"])
        self.assertEqual(350, result["per_task"]["provider_total_tokens"])


if __name__ == "__main__":
    unittest.main()
