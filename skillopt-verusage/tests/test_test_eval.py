from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_evolution_pilot.codex_runner import build_prompt
from skillopt_verusage.test_eval import _load_skill, _require_run_dir, _summarize


class TestFixedTestEvalContract(unittest.TestCase):
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

    def test_direct_summary_excludes_invalid_solved_rows(self) -> None:
        summary = _summarize(
            [
                {
                    "status": "SOLVED",
                    "fidelity_class": "V0_INVALID",
                    "fidelity": {"usage": {}},
                    "claude_failed": True,
                },
                {
                    "status": "SOLVED",
                    "fidelity_class": "V2_TRACE",
                    "fidelity": {"usage": {}},
                    "claude_failed": False,
                },
            ],
            transport="direct",
            model="gpt-5.6-sol",
        )
        self.assertEqual(summary["solved"], 1)
        self.assertEqual(summary["valid_results"], 1)
        self.assertEqual(summary["invalid_solved_excluded"], 1)
        self.assertEqual(summary["claude_failed_solved"], 0)

    def test_bridge_summary_excludes_invalid_solved_rows(self) -> None:
        summary = _summarize(
            [
                {
                    "status": "SOLVED",
                    "fidelity": "V0_INVALID",
                    "usage": {},
                    "claude_failed": False,
                }
            ],
            transport="bridge",
            model="qwen3.8-27b",
        )
        self.assertEqual(summary["solved"], 0)
        self.assertEqual(summary["invalid_solved_excluded"], 1)


if __name__ == "__main__":
    unittest.main()
