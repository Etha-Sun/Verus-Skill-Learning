from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skillopt_verusage.codex_flash_runner import _bridge_usage, _conversation


class CodexFlashRunnerTests(unittest.TestCase):
    def test_bridge_usage_is_scoped_to_task_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.jsonl"
            rows = [
                {
                    "task_id": "wanted",
                    "attempts": [
                        {
                            "usage": {
                                "prompt_tokens": 10,
                                "prompt_cache_hit_tokens": 3,
                                "prompt_cache_miss_tokens": 7,
                                "completion_tokens": 4,
                            }
                        }
                    ],
                },
                {"task_id": "other", "attempts": [{"usage": {"completion_tokens": 99}}]},
            ]
            ledger.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            usage = _bridge_usage(ledger, "wanted")
            self.assertEqual(usage["requests"], 1)
            self.assertEqual(usage["completion_tokens"], 4)
            self.assertGreater(usage["estimated_cost_usd"], 0)

    def test_conversation_preserves_full_tool_output_and_final_judge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "events.jsonl"
            raw.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "./tools/run_verus.sh candidate.rs",
                            "aggregated_output": "full diagnostic",
                            "exit_code": 1,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            conversation = _conversation(
                raw,
                {
                    "verus": {"passed": False, "stdout": "judge", "stderr": ""},
                    "lynette": {"passed": True, "stdout": "", "stderr": ""},
                },
            )
            self.assertEqual(conversation[0]["obs"], "full diagnostic")
            self.assertIn("Independent final Verus", conversation[-1]["content"])


if __name__ == "__main__":
    unittest.main()
