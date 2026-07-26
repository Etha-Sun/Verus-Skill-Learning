import json
import tempfile
import unittest
from pathlib import Path

from skill_evolution_pilot.token_ledger import (
    aggregate_ledgers,
    build_run_ledger,
)


class TokenLedgerTest(unittest.TestCase):
    @staticmethod
    def _run_fixture(
        root: Path,
        name: str,
        *,
        input_tokens: int = 100,
        cached_input_tokens: int = 60,
        output_tokens: int = 30,
        reasoning_output_tokens: int | None = 10,
        success: bool = True,
        f3: bool = True,
    ) -> Path:
        run = root / name
        run.mkdir()
        manifest = {
            "run_id": name,
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high",
            "reasoning_summary": "detailed",
            "show_raw_agent_reasoning": True,
            "prompt_sha256": "p",
            "source_sha256": "s",
            "skill_present": False,
        }
        result = {
            "run_id": name,
            "status": "SOLVED" if success else "UNSOLVED",
            "timed_out": False,
            "wall_seconds": 1.0,
            "validation": {
                "verus": {"passed": success},
                "lynette": {"passed": success},
            },
        }
        usage = {
            "input_tokens": input_tokens,
            "cached_input_tokens": cached_input_tokens,
            "output_tokens": output_tokens,
        }
        if reasoning_output_tokens is not None:
            usage["reasoning_output_tokens"] = reasoning_output_tokens
        (run / "run_manifest.json").write_text(json.dumps(manifest))
        (run / "result.json").write_text(json.dumps(result))
        (run / "fidelity_audit.json").write_text(json.dumps({"f3": f3}))
        (run / "codex_events.raw.jsonl").write_text(
            json.dumps({"type": "turn.completed", "usage": usage}) + "\n"
        )
        return run

    def test_reasoning_is_not_double_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self._run_fixture(Path(tmp), "run-1")
            ledger = build_run_ledger(run)
            self.assertEqual(ledger["uncached_input_tokens"], 40)
            self.assertEqual(ledger["provider_total_tokens"], 130)
            self.assertEqual(ledger["primary_uncached_tokens"], 70)
            self.assertEqual(ledger["visible_output_tokens_if_reasoning_is_subset"], 20)
            self.assertFalse(ledger["reasoning_double_counted"])

    def test_missing_reasoning_count_is_null_but_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self._run_fixture(
                Path(tmp),
                "run-2",
                reasoning_output_tokens=None,
            )
            ledger = build_run_ledger(run)
            self.assertIsNone(ledger["reasoning_output_tokens"])
            self.assertFalse(ledger["reasoning_count_available"])
            self.assertEqual(ledger["primary_uncached_tokens"], 70)

    def test_expected_tokens_to_success_includes_failed_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            passed = build_run_ledger(
                self._run_fixture(root, "passed", success=True)
            )
            failed = build_run_ledger(
                self._run_fixture(
                    root,
                    "failed",
                    input_tokens=80,
                    cached_input_tokens=20,
                    output_tokens=20,
                    reasoning_output_tokens=5,
                    success=False,
                )
            )
            aggregate = aggregate_ledgers([passed, failed])
            self.assertEqual(aggregate["success_count"], 1)
            self.assertEqual(
                aggregate["expected_primary_uncached_tokens_to_success"],
                150,
            )
            self.assertEqual(aggregate["solve_rate"], 0.5)

    def test_zero_success_is_explicitly_infinite(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = build_run_ledger(
                self._run_fixture(Path(tmp), "failed", success=False)
            )
            aggregate = aggregate_ledgers([run])
            self.assertIsNone(
                aggregate["expected_primary_uncached_tokens_to_success"]
            )
            self.assertTrue(aggregate["expected_tokens_to_success_is_infinite"])

    def test_non_f3_run_cannot_enter_primary_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = build_run_ledger(
                self._run_fixture(Path(tmp), "not-f3", f3=False)
            )
            with self.assertRaisesRegex(ValueError, "pass F3"):
                aggregate_ledgers([run])


if __name__ == "__main__":
    unittest.main()
