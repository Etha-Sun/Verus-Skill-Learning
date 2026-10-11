import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("guardian", Path(__file__).with_name("watch_controller.py"))
guardian = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guardian)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.state = {"status": "running", "active_run_id": "finished-run", "continuation_policy": "auto"}

    def test_completed_stale_turn_recovers(self):
        self.assertEqual(guardian.recovery_reason(self.state, "completed", 600, False),
                         "completed_turn_still_active")

    def test_live_or_not_completed_turn_never_interrupted(self):
        self.assertIsNone(guardian.recovery_reason(self.state, "completed", 600, True))
        self.assertIsNone(guardian.recovery_reason(self.state, None, 600, False))

    def test_native_cleanup_has_time_to_finish(self):
        self.assertIsNone(guardian.recovery_reason(self.state, "completed", 299, False))

    def test_explicit_stop_and_resource_checkpoint_respected(self):
        for status in ["paused", "stopped", "completed", "error", "waiting_for_user"]:
            with self.subTest(status=status):
                self.assertIsNone(guardian.recovery_reason(dict(self.state, status=status), "completed", 600, False))
        for policy in ["none", "wait_for_user_or_resume"]:
            with self.subTest(policy=policy):
                self.assertIsNone(guardian.recovery_reason(dict(self.state, continuation_policy=policy), "completed", 600, False))

    def test_idle_native_stage_recovers(self):
        self.assertEqual(guardian.recovery_reason(dict(self.state, active_run_id=None), None, 600, False),
                         "native_continuation_idle")

    def test_completed_turn_file_triggers_native_resume_without_changing_result(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            quest = home / "quests/test"
            result = quest / ".ds/runs/finished-run/result.json"
            result.parent.mkdir(parents=True)
            result.write_text('{"completed_at":"2026-10-11T04:19:34Z","exit_code":0}')
            runtime = quest / ".ds/runtime_state.json"
            runtime.write_text(json.dumps(self.state))
            old = time.time() - 600
            for path in [result, runtime]:
                os.utime(path, (old, old))
            original = result.read_bytes()
            state_dir = home / "guardian"
            state_dir.mkdir()
            with patch.object(guardian, "api", side_effect=[self.state, {"ok": True}]) as request:
                with patch.object(guardian, "controller_alive", return_value=False):
                    recovered = guardian.check(home, "test", "http://localhost", state_dir, 0)
            self.assertGreater(recovered, old)
            self.assertEqual(request.call_args.args[1], "/api/quests/test/control")
            self.assertEqual(request.call_args.args[2]["action"], "resume")
            self.assertEqual(result.read_bytes(), original)
            self.assertTrue(json.loads((state_dir / "state.json").read_text())["native_resume_ok"])
            # A second check inside the cooldown cannot duplicate the recovery.
            with patch.object(guardian, "api", return_value=self.state) as request:
                with patch.object(guardian, "controller_alive", return_value=False):
                    guardian.check(home, "test", "http://localhost", state_dir, recovered)
            self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
