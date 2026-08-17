from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skillopt_verusage.calibrate import _balanced_items, _response_audit


class CalibrationSelectionTest(unittest.TestCase):
    def test_balanced_items_selects_both_projects(self) -> None:
        items = [
            {"id": f"a{index}", "task_type": "anvil"} for index in range(5)
        ] + [{"id": f"i{index}", "task_type": "ironkv"} for index in range(5)]
        selected = _balanced_items(items, 8)
        self.assertEqual(
            [item["task_type"] for item in selected],
            ["anvil"] * 4 + ["ironkv"] * 4,
        )

    def test_response_audit_reads_codex_bridge_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bridge_calls.jsonl").write_text(
                json.dumps(
                    {
                        "task_id": "calibration--task-a--a01",
                        "attempts": [
                            {
                                "finish_reason": "completed",
                                "usage": {"prompt_tokens": 10},
                                "error": None,
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            audit = _response_audit(root, [{"fidelity": "V2_TRACE"}])
            self.assertEqual(audit["requests"], 1)
            self.assertEqual(audit["accepted_requests"], 1)
            self.assertEqual(audit["task_ledgers"], 1)
            self.assertTrue(audit["passed"])


if __name__ == "__main__":
    unittest.main()
