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
                                "price_band": "off_peak",
                                "estimated_cost_usd": 0.125,
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
            self.assertEqual(ledger["target"]["estimated_cost_usd"], 0.125)
            self.assertEqual(
                ledger["target"]["price_band_requests"], {"off_peak": 1}
            )
            self.assertEqual(ledger["target_by_phase"]["rollout"]["tasks"], 1)
            self.assertEqual(ledger["target_by_phase"]["rollout"]["requests"], 1)
            self.assertEqual(ledger["optimizer"]["calls"], 1)
            self.assertEqual(ledger["optimizer"]["actual_metered_cost_usd"], 0.0)
            self.assertEqual(ledger["combined_estimated_cost_usd"], 0.125)

    def test_unknown_actor_and_optimizer_usage_fail_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bridge_manifest.json").write_text(
                json.dumps({"model": "deepseek-v4-pro"}), encoding="utf-8"
            )
            (root / "bridge_calls.jsonl").write_text(
                json.dumps(
                    {
                        "task_id": "rollout--task-a--a01",
                        "phase": "rollout",
                        "attempts": [
                            {
                                "finish_reason": None,
                                "estimated_cost_usd": None,
                                "usage": None,
                                "error": "HTTP 502",
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
                        "record_type": "optimizer_attempt",
                        "status": "error",
                        "usage": None,
                        "usage_known": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            ledger = build_cost_ledger(root)
            self.assertEqual(ledger["target"]["requests"], 1)
            self.assertEqual(ledger["target"]["unmetered_requests"], 1)
            self.assertEqual(ledger["target"]["error_requests"], 1)
            self.assertFalse(ledger["target"]["accounting_complete"])
            self.assertEqual(ledger["optimizer"]["failed_attempts"], 1)
            self.assertFalse(ledger["accounting_complete"])

    def test_recorded_non_deepseek_cost_needs_no_optimizer_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bridge_manifest.json").write_text(
                json.dumps({"model": "glm-5.3"}), encoding="utf-8"
            )
            (root / "bridge_calls.jsonl").write_text(
                json.dumps(
                    {
                        "task_id": "calibration--task-a--a01",
                        "attempts": [
                            {
                                "estimated_cost_usd": 0.25,
                                "usage": {
                                    "prompt_tokens": 10,
                                    "completion_tokens": 2,
                                },
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "summary.json").write_text("{}\n", encoding="utf-8")
            ledger = build_cost_ledger(root)
            self.assertEqual(ledger["model"], "glm-5.3")
            self.assertEqual(ledger["target"]["estimated_cost_usd"], 0.25)
            self.assertEqual(ledger["optimizer"]["source"], "none")
            self.assertEqual(ledger["optimizer"]["calls"], 0)


if __name__ == "__main__":
    unittest.main()
