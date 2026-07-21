from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from prepare_traces import allocate_per_model, ensure_safe_output, parse_quota
from run_taxonomy import canonical_role, canonical_role_for_agent


class PrepareTracesTest(unittest.TestCase):
    def test_raw_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = root / "all_batch_results-cyy-gpt5"
            raw.mkdir()
            with self.assertRaises(ValueError):
                ensure_safe_output(root, raw / "derived")

    def test_sibling_output_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ensure_safe_output(root, root / "runs" / "atlas")

    def test_allocation_preserves_total(self) -> None:
        allocation = allocate_per_model(10, ["a", "b", "c", "d"])
        self.assertEqual(sum(allocation.values()), 10)
        self.assertLessEqual(max(allocation.values()) - min(allocation.values()), 1)

    def test_parse_quota(self) -> None:
        self.assertEqual(
            parse_quota("FAILED=2,TIMEOUT=1,VERIFIED=3"),
            {"FAILED": 2, "TIMEOUT": 1, "VERIFIED": 3},
        )

    def test_role_corrections_are_canonicalized(self) -> None:
        self.assertEqual(canonical_role("postcondition repair specialist"), "refiner")
        self.assertEqual(canonical_role("iterative workflow controller"), "coordinator")
        self.assertEqual(canonical_role("dedicated verifier"), "checker")
        self.assertEqual(
            canonical_role_for_agent("Agent_OtherErrorAgent", "fallback for verifier errors"),
            "refiner",
        )


if __name__ == "__main__":
    unittest.main()
