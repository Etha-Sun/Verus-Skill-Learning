from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
import unittest
import json
from pathlib import Path

from skillopt_verusage.adapter import VeruSAGEAdapter


class AdapterProcessCleanupTest(unittest.TestCase):
    def test_terminate_active_processes_stops_runner_group(self) -> None:
        adapter = object.__new__(VeruSAGEAdapter)
        adapter._process_lock = threading.Lock()
        adapter._active_processes = set()
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            start_new_session=True,
        )
        adapter._active_processes.add(process)

        adapter._terminate_active_processes()

        self.assertIsNotNone(process.poll())

    def test_invalid_task_is_archived_and_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = object.__new__(VeruSAGEAdapter)
            adapter.task_retries = 1
            prediction_dir = Path(temp_dir) / "predictions"
            prediction_dir.mkdir()
            skill_file = Path(temp_dir) / "skill.md"
            skill_file.write_text("skill\n", encoding="utf-8")
            calls = 0

            def fake_attempt(item, prediction_root, unused_skill_file):
                nonlocal calls
                calls += 1
                task_dir = prediction_root / item["id"]
                task_dir.mkdir(exist_ok=True)
                if calls == 2:
                    self.assertEqual(list(task_dir.iterdir()), [])
                (task_dir / "marker.txt").write_text(str(calls), encoding="utf-8")
                result = {
                    "id": item["id"],
                    "hard": int(calls == 2),
                    "fidelity": "V0_INVALID" if calls == 1 else "V2_TRACE",
                    "fail_reason": "provider exhausted" if calls == 1 else "",
                }
                (task_dir / "result.json").write_text(
                    json.dumps(result), encoding="utf-8"
                )
                return result

            adapter._run_one_attempt = fake_attempt
            result = adapter._run_one(
                {"id": "task-one"}, prediction_dir, skill_file
            )

            task_dir = prediction_dir / "task-one"
            self.assertEqual(calls, 2)
            self.assertEqual(result["task_attempt_index"], 2)
            self.assertEqual(
                (
                    prediction_dir
                    / "_attempts"
                    / "task-one"
                    / "attempt-01"
                    / "marker.txt"
                ).read_text(),
                "1",
            )
            self.assertEqual(list(task_dir.glob("attempts")), [])
            self.assertEqual((task_dir / "marker.txt").read_text(), "2")

    def test_rollout_aborts_on_exhausted_invalid_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = object.__new__(VeruSAGEAdapter)
            adapter.workers = 1
            adapter._process_lock = threading.Lock()
            adapter._active_processes = set()
            adapter._run_one = lambda item, prediction_dir, skill_file: {
                "id": item["id"],
                "hard": 0,
                "fidelity": "V0_INVALID",
                "fail_reason": "provider exhausted",
            }

            with self.assertRaisesRegex(RuntimeError, "HARNESS_INVALID"):
                adapter.rollout(
                    [{"id": "task-one"}],
                    "skill\n",
                    str(Path(temp_dir) / "rollout"),
                )

    def test_rollout_can_retain_invalid_task_for_uniform_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = object.__new__(VeruSAGEAdapter)
            adapter.workers = 1
            adapter.fail_on_invalid = False
            adapter._process_lock = threading.Lock()
            adapter._active_processes = set()
            adapter._run_one = lambda item, prediction_dir, skill_file: {
                "id": item["id"],
                "hard": 0,
                "status": "UNSOLVED",
                "fidelity": "V0_INVALID",
                "fail_reason": "provider exhausted",
            }
            results = adapter.rollout(
                [{"id": "task-one"}],
                "skill\n",
                str(Path(temp_dir) / "rollout"),
            )
            self.assertEqual(results[0]["fidelity"], "V0_INVALID")


if __name__ == "__main__":
    unittest.main()
