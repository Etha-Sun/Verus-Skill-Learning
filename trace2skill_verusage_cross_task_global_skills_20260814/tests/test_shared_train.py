from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from global_skill_experiment.shared_train import (
    canonical_sha256,
    parse_outcome_csv,
    result_class,
)


class SharedTrainTests(unittest.TestCase):
    def test_parse_both_csv_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "results.csv"
            path.write_text(
                "plain_task, TRUE\n"
                "cheat_task, CHEAT (external_body)\n"
                "*** advanced_task: FALSE\n"
                "verification results:: 0 verified, 1 errors\n",
                encoding="utf-8",
            )
            self.assertEqual(
                parse_outcome_csv(path),
                {
                    "plain_task": "TRUE",
                    "cheat_task": "CHEAT (EXTERNAL_BODY)",
                    "advanced_task": "FALSE",
                },
            )

    def test_result_class_preserves_cheat(self) -> None:
        self.assertEqual(result_class("TRUE"), "true")
        self.assertEqual(result_class("FALSE"), "false")
        self.assertEqual(result_class("CHEAT (MAYBE)"), "cheat")

    def test_canonical_hash_is_key_order_independent(self) -> None:
        left = {"a": 1, "b": [2, 3]}
        right = json.loads('{"b":[2,3],"a":1}')
        self.assertEqual(canonical_sha256(left), canonical_sha256(right))


if __name__ == "__main__":
    unittest.main()
