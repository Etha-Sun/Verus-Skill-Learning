from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skillopt_verusage.cost_ledger import build_cost_ledger


class CostLedgerCodexBridgeTests(unittest.TestCase):
    def test_counts_bridge_target_and_local_codex_optimizer_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bridge_calls.jsonl").write_text(
                json.dumps(
                    {
                        "task_id": "rollout--task-a--a01",
                        "phase": "rollout",
                        "attempts": [
                            {
                                "usage": {
                                    "prompt_tokens": 10,
                                    "prompt_cache_hit_tokens": 4,
                                    "prompt_cache_miss_tokens": 6,
                                    "completion_tokens": 5,
                                }
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "optimizer_calls.jsonl").write_text(
                json.dumps(
                    {
                        "status": "success",
                        "usage": {"prompt_tokens": 20, "completion_tokens": 7},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            ledger = build_cost_ledger(root)
            self.assertEqual(ledger["target"]["requests"], 1)
            self.assertEqual(ledger["target"]["completion_tokens"], 5)
            self.assertEqual(ledger["target_by_phase"]["rollout"]["tasks"], 1)
            self.assertEqual(ledger["target_by_phase"]["rollout"]["requests"], 1)
            self.assertEqual(ledger["optimizer"]["calls"], 1)
            self.assertEqual(ledger["optimizer"]["actual_metered_cost_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
