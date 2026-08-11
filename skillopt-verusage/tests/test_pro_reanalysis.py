from __future__ import annotations

import unittest
from unittest import mock

from skillopt_verusage.pro_reanalysis import (
    _audit_evidence_claims,
    _lint_appendix,
    _normalize_appendix,
    _usage_cost,
)
from skillopt_verusage.train import _configure_deepseek


class ProReanalysisTest(unittest.TestCase):
    def test_deepseek_roles_are_configured_separately(self) -> None:
        with mock.patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}):
            with mock.patch("skillopt.model.configure_openai_compatible") as configure:
                _configure_deepseek(
                    {
                        "optimizer_model": "deepseek-v4-pro",
                        "target_model": "deepseek-v4-flash",
                    }
                )
        kwargs = configure.call_args.kwargs
        self.assertEqual(kwargs["optimizer_model"], "deepseek-v4-pro")
        self.assertEqual(kwargs["target_model"], "deepseek-v4-flash")

    def test_usage_cost_uses_cache_split(self) -> None:
        cost = _usage_cost(
            {
                "prompt_tokens": 1_000_000,
                "prompt_cache_hit_tokens": 750_000,
                "prompt_cache_miss_tokens": 250_000,
                "completion_tokens": 100_000,
            }
        )
        self.assertAlmostEqual(cost, 0.19846875)

    def test_lint_accepts_compact_rule(self) -> None:
        errors = _lint_appendix(
            "Treat existing trusted declarations as frozen context; never add a new bypass.\n\n"
            "Promote only a strategy supported by multiple independent trajectories.",
            "# Seed\n",
        )
        self.assertEqual(errors, [])

    def test_lint_rejects_concrete_formula(self) -> None:
        errors = _lint_appendix("Use `assert(x == y)`.", "# Seed\n")
        self.assertTrue(any("concrete code/formula" in error for error in errors))

    def test_normalize_appendix_joins_json_list_as_markdown(self) -> None:
        appendix = _normalize_appendix(["First rule.", "Second rule."])
        self.assertEqual(appendix, "- First rule.\n- Second rule.")

    def test_lint_rejects_ban_on_existing_trusted_context(self) -> None:
        errors = _lint_appendix(
            "Existing trusted helper lemmas must not be used.",
            "# Seed\n",
        )
        self.assertIn("appendix forbids use of frozen trusted context", errors)

    def test_evidence_audit_rejects_false_lynette_attribution(self) -> None:
        evidence = [
            {
                "training_item_id": "task-a",
                "strict_success": False,
                "final_verus_passed": False,
                "final_lynette_passed": True,
            }
        ]
        errors = _audit_evidence_claims(
            {
                "evidence_map": [
                    {
                        "training_item": "task-a",
                        "success": False,
                        "pattern": "The proof was rejected by Lynette.",
                    }
                ]
            },
            evidence,
        )
        self.assertIn(
            "analysis falsely attributes failure to Lynette for task-a",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
