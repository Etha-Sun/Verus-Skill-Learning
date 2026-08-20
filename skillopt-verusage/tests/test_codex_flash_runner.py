from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skillopt_verusage.codex_flash_runner import (
    _bridge_usage,
    _classify_fidelity,
    _conversation,
)


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
            usage = _bridge_usage(ledger, "wanted", "deepseek-v4-pro")
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

    def test_bridge_usage_counts_unmetered_incomplete_and_error_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.jsonl"
            ledger.write_text(
                json.dumps(
                    {
                        "task_id": "wanted",
                        "upstream_model": "deepseek-v4-pro-0813",
                        "attempts": [
                            {
                                "finish_reason": "incomplete",
                                "usage": None,
                                "error": "truncated",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            usage = _bridge_usage(ledger, "wanted", "deepseek-v4-pro")
            self.assertEqual(usage["requests"], 1)
            self.assertEqual(usage["unmetered_requests"], 1)
            self.assertEqual(usage["incomplete_requests"], 1)
            self.assertEqual(usage["error_requests"], 1)

    def test_fidelity_fails_closed_on_terminal_or_provider_failure(self) -> None:
        base = {
            "codex_returncode": 0,
            "timed_out": False,
            "fidelity": {"f3": True, "input_unchanged": True},
        }
        completed = {"completed": 1, "failed": 0, "errors": 0}
        self.assertEqual(_classify_fidelity(base, True, completed), "V2_TRACE")
        self.assertEqual(
            _classify_fidelity(
                base,
                True,
                {"completed": 1, "failed": 0, "errors": 2},
            ),
            "V2_TRACE",
        )
        self.assertEqual(_classify_fidelity(base, False, completed), "V0_INVALID")
        self.assertEqual(
            _classify_fidelity({**base, "codex_returncode": 1}, True, completed),
            "V0_INVALID",
        )
        self.assertEqual(
            _classify_fidelity(base, True, {"completed": 0, "failed": 1, "errors": 0}),
            "V0_INVALID",
        )
        self.assertEqual(
            _classify_fidelity({**base, "timed_out": True}, True, completed),
            "V1_TRUNCATED",
        )


if __name__ == "__main__":
    unittest.main()
