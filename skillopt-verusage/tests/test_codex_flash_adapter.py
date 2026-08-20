from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skillopt_verusage.codex_flash_adapter import CodexDeepSeekAdapter


class CodexFlashAdapterTest(unittest.TestCase):
    def test_unsolved_timeout_retries_with_expanded_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = object.__new__(CodexDeepSeekAdapter)
            adapter.task_retries = 2
            adapter.timeout_retries = 2
            adapter.codex_timeout_seconds = 1200
            adapter.max_codex_timeout_seconds = 3600
            adapter._resume_result = lambda *args, **kwargs: None
            calls: list[int] = []

            def run_attempt(
                item, prediction_dir, skill_file, *, attempt_index, timeout_seconds
            ):
                del skill_file
                calls.append(timeout_seconds)
                (prediction_dir / item["id"]).mkdir(exist_ok=True)
                return {
                    "id": item["id"],
                    "hard": int(attempt_index == 2),
                    "timed_out": attempt_index == 1,
                    "fidelity": "V1_TRUNCATED" if attempt_index == 1 else "V2_TRACE",
                }

            adapter._run_one_attempt_with_timeout = run_attempt
            prediction_dir = Path(tmp) / "predictions"
            prediction_dir.mkdir()
            skill = Path(tmp) / "skill.md"
            skill.write_text("skill\n", encoding="utf-8")
            result = adapter._run_one({"id": "task"}, prediction_dir, skill)
            self.assertEqual(calls, [1200, 2400])
            self.assertEqual(result["hard"], 1)
            self.assertEqual(result["task_attempt_index"], 2)

    def test_unsolved_timeout_does_not_retry_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = object.__new__(CodexDeepSeekAdapter)
            adapter.task_retries = 2
            adapter.timeout_retries = 0
            adapter.codex_timeout_seconds = 600
            adapter.max_codex_timeout_seconds = 600
            adapter._resume_result = lambda *args, **kwargs: None
            calls: list[int] = []

            def run_attempt(
                item,
                prediction_dir,
                skill_file,
                *,
                attempt_index,
                timeout_seconds,
            ):
                del skill_file, attempt_index
                calls.append(timeout_seconds)
                (prediction_dir / item["id"]).mkdir(exist_ok=True)
                return {
                    "id": item["id"],
                    "hard": 0,
                    "timed_out": True,
                    "fidelity": "V1_TRUNCATED",
                }

            adapter._run_one_attempt_with_timeout = run_attempt
            prediction_dir = Path(tmp) / "predictions"
            prediction_dir.mkdir()
            skill = Path(tmp) / "skill.md"
            skill.write_text("skill\n", encoding="utf-8")
            result = adapter._run_one({"id": "task"}, prediction_dir, skill)
            self.assertEqual(calls, [600])
            self.assertEqual(result["hard"], 0)
            self.assertEqual(result["task_attempt_index"], 1)

    def test_invalid_harness_still_retries_when_timeout_retry_is_disabled(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = object.__new__(CodexDeepSeekAdapter)
            adapter.task_retries = 2
            adapter.timeout_retries = 0
            adapter.codex_timeout_seconds = 600
            adapter.max_codex_timeout_seconds = 600
            adapter._resume_result = lambda *args, **kwargs: None
            calls: list[int] = []

            def run_attempt(
                item,
                prediction_dir,
                skill_file,
                *,
                attempt_index,
                timeout_seconds,
            ):
                del skill_file
                calls.append(timeout_seconds)
                (prediction_dir / item["id"]).mkdir(exist_ok=True)
                return {
                    "id": item["id"],
                    "hard": int(attempt_index == 2),
                    "timed_out": False,
                    "fidelity": ("V0_INVALID" if attempt_index == 1 else "V2_TRACE"),
                }

            adapter._run_one_attempt_with_timeout = run_attempt
            prediction_dir = Path(tmp) / "predictions"
            prediction_dir.mkdir()
            skill = Path(tmp) / "skill.md"
            skill.write_text("skill\n", encoding="utf-8")
            result = adapter._run_one({"id": "task"}, prediction_dir, skill)
            self.assertEqual(calls, [600, 600])
            self.assertEqual(result["hard"], 1)
            self.assertEqual(result["task_attempt_index"], 2)

    def test_task_key_includes_step_scope(self) -> None:
        task = Path("run/steps/step_0002/selection_eval/predictions/item")
        self.assertEqual(
            CodexDeepSeekAdapter._task_key(task, 1),
            "step_0002-selection_eval--item--a01",
        )


if __name__ == "__main__":
    unittest.main()
