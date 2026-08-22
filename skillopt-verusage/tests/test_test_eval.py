from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_evolution_pilot.codex_runner import build_prompt
from skillopt_verusage.test_eval import (
    _attach_item_metadata,
    _load_skill,
    _require_run_dir,
    _run_direct,
    _select_test_items,
    _summarize,
)


class TestFixedTestEvalContract(unittest.TestCase):
    def test_select_test_items_preserves_frozen_split_order(self) -> None:
        items = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        self.assertEqual(
            _select_test_items(items, ["c", "a"]),
            [{"id": "a"}, {"id": "c"}],
        )

    def test_select_test_items_rejects_unknown_or_duplicate_ids(self) -> None:
        items = [{"id": "a"}, {"id": "b"}]
        with self.assertRaisesRegex(ValueError, "unknown --item-id"):
            _select_test_items(items, ["c"])
        with self.assertRaisesRegex(ValueError, "duplicate --item-id"):
            _select_test_items(items, ["a", "a"])

    def test_bridge_results_receive_frozen_item_metadata(self) -> None:
        results = [{"id": "case-a", "status": "UNSOLVED"}]
        _attach_item_metadata(
            results,
            [
                {
                    "id": "case-a",
                    "task_id": "AC__case_a",
                    "project_code": "AC",
                    "claude_failed": True,
                }
            ],
        )
        self.assertEqual(results[0]["task_id"], "AC__case_a")
        self.assertTrue(results[0]["claude_failed"])

    def test_run_dir_allows_tee_log_created_before_evaluator_start(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "runs"
            run_dir = root / "bridge-arm"
            run_dir.mkdir(parents=True)
            (run_dir / "test.log").write_text("", encoding="utf-8")
            with patch.dict(
                "os.environ", {"VERUS_SKILL_RUN_ROOT": str(root)}, clear=False
            ):
                self.assertEqual(_require_run_dir(run_dir), run_dir.resolve())

    def test_blank_skill_has_no_strategy_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "blank.md"
            path.write_text("\n", encoding="utf-8")
            expected = hashlib.sha256(b"\n").hexdigest()
            text, actual = _load_skill(path, expected)
        self.assertEqual(text.strip(), "")
        self.assertEqual(actual, expected)

    def test_skill_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "skill.md"
            path.write_text("content\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "skill hash mismatch"):
                _load_skill(path, "0" * 64)

    def test_common_prompt_has_no_hands_off_framework_label(self) -> None:
        self.assertNotIn("hands-off", build_prompt().lower())

    def test_direct_reference_blank_propagates_profile_and_omits_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "run"
            out_dir.mkdir()
            fake_result = {
                "status": "UNSOLVED",
                "timed_out": False,
                "fidelity": {"f3": True, "input_unchanged": True},
            }
            with patch(
                "skillopt_verusage.test_eval.run_codex_smoke",
                return_value=fake_result,
            ) as run_smoke:
                results = _run_direct(
                    items=[
                        {
                            "id": "case-a",
                            "task_id": "AC__case_a",
                            "project_code": "AC",
                            "claude_failed": False,
                            "source_path": "/sealed/case-a.rs",
                        }
                    ],
                    out_dir=out_dir,
                    skill_text="\n",
                    skill_sha256=hashlib.sha256(b"\n").hexdigest(),
                    model="gpt-5.6-sol",
                    reasoning_effort="max",
                    codex_bin=Path("/bin/true"),
                    verus_bin=Path("/bin/true"),
                    lynette_bin=Path("/bin/true"),
                    workers=1,
                    timeout_seconds=600,
                    model_context_window=1048576,
                    actor_contract_profile="cross_provider_20260819",
                    condition_skill_present=False,
                )
            skill_file_exists = (out_dir / "skill.md").exists()
        kwargs = run_smoke.call_args.kwargs
        self.assertIsNone(kwargs["skill_text"])
        self.assertEqual(kwargs["contract_profile"], "cross_provider_20260819")
        self.assertEqual(kwargs["stage"], "formal_held_out_evaluation")
        self.assertFalse(skill_file_exists)
        self.assertFalse(results[0]["condition_skill_present"])
        self.assertEqual(
            results[0]["actor_contract_profile"], "cross_provider_20260819"
        )

    def test_direct_summary_counts_safe_v0_solved_rows(self) -> None:
        summary = _summarize(
            [
                {
                    "status": "SOLVED",
                    "fidelity_class": "V0_INVALID",
                    "fidelity": {"usage": {}},
                    "proof_solved": True,
                    "claude_failed": True,
                },
                {
                    "status": "SOLVED",
                    "fidelity_class": "V2_TRACE",
                    "fidelity": {"usage": {}},
                    "proof_solved": True,
                    "claude_failed": False,
                },
            ],
            transport="direct",
            model="gpt-5.6-sol",
        )
        self.assertEqual(summary["solved"], 2)
        self.assertEqual(summary["valid_results"], 1)
        self.assertEqual(summary["trace_status"], "partial")
        self.assertEqual(summary["v0_solved_included"], 1)
        self.assertEqual(summary["invalid_solved_excluded"], 0)
        self.assertEqual(summary["claude_failed_solved"], 1)

    def test_bridge_summary_counts_safe_v0_solved_rows(self) -> None:
        summary = _summarize(
            [
                {
                    "status": "SOLVED",
                    "fidelity": "V0_INVALID",
                    "proof_solved": True,
                    "usage": {},
                    "claude_failed": False,
                }
            ],
            transport="bridge",
            model="qwen3.8-27b",
        )
        self.assertEqual(summary["solved"], 1)
        self.assertEqual(summary["v0_solved_included"], 1)

    def test_bridge_summary_uses_complete_ledger_cost(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = Path(temp_dir) / "bridge.jsonl"
            rows = [
                {
                    "attempts": [
                        {
                            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
                            "estimated_cost_usd": 0.1,
                        }
                    ]
                },
                {
                    "attempts": [
                        {
                            "usage": {"prompt_tokens": 20, "completion_tokens": 3},
                            "estimated_cost_usd": 0.2,
                        }
                    ]
                },
            ]
            ledger.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            summary = _summarize(
                [
                    {
                        "status": "SOLVED",
                        "fidelity": "V2_TRACE",
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 2,
                            "estimated_cost_usd": 0.1,
                        },
                        "claude_failed": False,
                    }
                ],
                transport="bridge",
                model="glm-5.3",
                bridge_ledger=ledger,
            )
        self.assertEqual(summary["usage"]["requests"], 2)
        self.assertAlmostEqual(summary["estimated_api_cost_usd"], 0.3)
        self.assertAlmostEqual(summary["archived_or_replaced_attempt_cost_usd"], 0.2)


if __name__ == "__main__":
    unittest.main()
