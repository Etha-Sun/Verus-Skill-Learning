from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from skill_evolution_pilot.token_compare import compare_token_runs


class TokenCompareTest(unittest.TestCase):
    def test_failed_short_run_is_ranked_worse_than_success(self) -> None:
        ledgers = {
            "h0": {
                "run_id": "h0",
                "condition": "h0",
                "source_sha256": "a",
                "model": "m",
                "f3": True,
                "success": True,
                "primary_uncached_tokens": 100,
            },
            "good": {
                "run_id": "good",
                "condition": "skill",
                "source_sha256": "a",
                "model": "m",
                "f3": True,
                "success": True,
                "primary_uncached_tokens": 80,
                "skill_sha256": "b",
                "skill_bytes": 10,
            },
            "failed": {
                "run_id": "failed",
                "condition": "skill",
                "source_sha256": "a",
                "model": "m",
                "f3": True,
                "success": False,
                "primary_uncached_tokens": 5,
                "skill_sha256": "c",
                "skill_bytes": 10,
            },
        }
        with patch(
            "skill_evolution_pilot.token_compare.build_run_ledger",
            side_effect=lambda path: ledgers[path.name],
        ):
            result = compare_token_runs(
                Path("h0"), [Path("failed"), Path("good")]
            )
        self.assertEqual(result["best_candidate_run_id"], "good")
        self.assertEqual(result["worst_candidate_run_id"], "failed")
        failed = next(row for row in result["rows"] if row["run_id"] == "failed")
        self.assertTrue(failed["expected_tokens_to_success_is_infinite"])


if __name__ == "__main__":
    unittest.main()
