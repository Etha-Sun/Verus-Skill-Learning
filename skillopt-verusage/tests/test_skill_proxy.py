from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from skillopt_verusage.budget_guard import (
    SharedBudgetGuard,
    estimate_deepseek_cost,
)
from skillopt_verusage.skill_proxy import BEGIN, SkillAwareDeepSeekLLM


class FakeCompletions:
    def __init__(self, responses=None):
        self.kwargs = None
        self.calls = []
        self.responses = list(responses or [("proof idea", "reasoning", "stop")])

    def create(self, **kwargs):
        self.kwargs = kwargs
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        content, reasoning, finish_reason = response
        message = SimpleNamespace(content=content, reasoning_content=reasoning)
        choice = SimpleNamespace(message=message, finish_reason=finish_reason)
        details = SimpleNamespace(reasoning_tokens=12)
        usage = SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            prompt_cache_hit_tokens=60,
            prompt_cache_miss_tokens=40,
            completion_tokens_details=details,
        )
        return SimpleNamespace(choices=[choice], usage=usage)


class SkillProxyTest(unittest.TestCase):
    def test_pro_pricing_is_model_aware(self) -> None:
        usage = {
            "prompt_cache_hit_tokens": 1_000_000,
            "prompt_cache_miss_tokens": 1_000_000,
            "completion_tokens": 1_000_000,
        }
        self.assertAlmostEqual(
            estimate_deepseek_cost(usage, "deepseek-v4-pro"),
            1.308625,
        )

    def test_proxy_injects_exact_skill_and_records_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completions = FakeCompletions()
            client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
            calls = Path(temp_dir) / "calls.jsonl"
            llm = SkillAwareDeepSeekLLM(
                {},
                None,
                skill_text="Use the verifier.\n",
                calls_path=calls,
                request_cap=1,
                client=client,
            )
            result = llm.infer_llm(
                "deepseek-v4-flash",
                None,
                None,
                "repair",
                system_info="original",
            )
            self.assertEqual(result, ["proof idea"])
            system = completions.kwargs["messages"][0]["content"]
            self.assertTrue(system.startswith("original"))
            self.assertIn(BEGIN, system)
            row = json.loads(calls.read_text(encoding="utf-8"))
            self.assertEqual(row["usage"]["prompt_cache_hit_tokens"], 60)
            self.assertEqual(row["usage"]["reasoning_tokens"], 12)
            self.assertEqual(row["mode"], "thinking")
            self.assertEqual(row["requested_max_tokens"], 8192)
            self.assertEqual(row["effective_max_tokens"], 32768)
            self.assertEqual(row["finish_reasons"], ["stop"])
            self.assertTrue(row["accepted"])
            self.assertEqual(
                row["skill_sha256"],
                hashlib.sha256(b"Use the verifier.\n").hexdigest(),
            )
            with self.assertRaisesRegex(RuntimeError, "REQUEST_BUDGET_EXCEEDED"):
                llm.infer_llm("deepseek-v4-flash", None, None, "again")

    def test_action_calls_restore_three_candidates_without_thinking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completions = FakeCompletions(
                [
                    ("patch one", "", "stop"),
                    ("patch two", "", "stop"),
                    ("patch three", "", "stop"),
                ]
            )
            client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
            llm = SkillAwareDeepSeekLLM(
                {},
                None,
                skill_text="Use the verifier.\n",
                calls_path=Path(temp_dir) / "calls.jsonl",
                request_cap=3,
                client=client,
            )
            answers = llm.infer_llm(
                "deepseek-v4-flash",
                None,
                None,
                "repair",
                answer_num=3,
                max_tokens=4096,
            )
            self.assertEqual(answers, ["patch one", "patch two", "patch three"])
            self.assertEqual(len(completions.calls), 3)
            for kwargs in completions.calls:
                self.assertEqual(kwargs["max_tokens"], 32768)
                self.assertEqual(
                    kwargs["extra_body"]["thinking"], {"type": "disabled"}
                )
                self.assertNotIn("reasoning_effort", kwargs["extra_body"])

    def test_length_limited_reasoning_retries_at_256k(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completions = FakeCompletions(
                [("", "unfinished", "length"), ("final answer", "done", "stop")]
            )
            client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
            calls_path = Path(temp_dir) / "calls.jsonl"
            llm = SkillAwareDeepSeekLLM(
                {},
                None,
                skill_text="Use the verifier.\n",
                calls_path=calls_path,
                request_cap=2,
                client=client,
            )
            self.assertEqual(
                llm.infer_llm("deepseek-v4-flash", None, None, "analyze"),
                ["final answer"],
            )
            rows = [json.loads(line) for line in calls_path.read_text().splitlines()]
            self.assertEqual(
                [row["effective_max_tokens"] for row in rows], [32768, 262144]
            )
            self.assertEqual(rows[0]["response_issue"], "finish_reason_length")
            self.assertFalse(rows[0]["accepted"])
            self.assertTrue(rows[1]["accepted"])

    def test_length_limited_action_retries_at_256k(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completions = FakeCompletions(
                [("partial patch", "", "length"), ("complete patch", "", "stop")]
            )
            client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
            calls_path = Path(temp_dir) / "calls.jsonl"
            llm = SkillAwareDeepSeekLLM(
                {},
                None,
                skill_text="Use the verifier.\n",
                calls_path=calls_path,
                request_cap=2,
                client=client,
            )
            self.assertEqual(
                llm.infer_llm(
                    "deepseek-v4-flash",
                    None,
                    None,
                    "repair",
                    max_tokens=4096,
                ),
                ["complete patch"],
            )
            rows = [json.loads(line) for line in calls_path.read_text().splitlines()]
            self.assertEqual(
                [row["effective_max_tokens"] for row in rows], [32768, 262144]
            )
            self.assertEqual(rows[0]["response_issue"], "finish_reason_length")
            self.assertTrue(rows[1]["accepted"])

    def test_second_length_limit_expands_to_384k(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completions = FakeCompletions(
                [
                    ("partial one", "", "length"),
                    ("partial two", "", "length"),
                    ("complete patch", "", "stop"),
                ]
            )
            client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
            calls_path = Path(temp_dir) / "calls.jsonl"
            llm = SkillAwareDeepSeekLLM(
                {},
                None,
                skill_text="Use the verifier.\n",
                calls_path=calls_path,
                request_cap=3,
                client=client,
            )
            self.assertEqual(
                llm.infer_llm(
                    "deepseek-v4-flash",
                    None,
                    None,
                    "repair",
                    max_tokens=4096,
                ),
                ["complete patch"],
            )
            rows = [json.loads(line) for line in calls_path.read_text().splitlines()]
            self.assertEqual(
                [row["effective_max_tokens"] for row in rows],
                [32768, 262144, 384000],
            )
            self.assertTrue(rows[2]["accepted"])

    def test_provider_timeout_retries_same_output_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completions = FakeCompletions(
                [TimeoutError("read timed out"), ("complete patch", "", "stop")]
            )
            client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
            calls_path = Path(temp_dir) / "calls.jsonl"
            llm = SkillAwareDeepSeekLLM(
                {},
                None,
                skill_text="Use the verifier.\n",
                calls_path=calls_path,
                request_cap=2,
                client=client,
            )
            self.assertEqual(
                llm.infer_llm(
                    "deepseek-v4-flash",
                    None,
                    None,
                    "repair",
                    max_tokens=4096,
                ),
                ["complete patch"],
            )
            rows = [json.loads(line) for line in calls_path.read_text().splitlines()]
            self.assertEqual(
                [row["effective_max_tokens"] for row in rows], [32768, 32768]
            )
            self.assertEqual(
                [row["transport_retry_index"] for row in rows], [0, 1]
            )
            self.assertEqual(rows[0]["response_issue"], "provider_error")
            self.assertTrue(rows[1]["accepted"])

    def test_shared_budget_guard_reserves_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "budget.json"
            kwargs = {
                "approval_limit_usd": 1.0,
                "prior_spend_usd": 0.1,
                "optimizer_reserve_usd": 0.2,
                "request_reserve_usd": 0.3,
            }
            first = SharedBudgetGuard(path, **kwargs)
            second = SharedBudgetGuard(path, **kwargs)
            reservation_one = first.reserve()
            second.reserve()
            with self.assertRaisesRegex(RuntimeError, "BUDGET_CAPACITY_TIMEOUT"):
                first.reserve(wait_timeout_seconds=0)
            first.settle(
                reservation_one,
                cost_usd=0.01,
                usage={"completion_tokens": 1},
            )
            first.reserve(0.35)
            self.assertAlmostEqual(first.mark_stale_reservations_uncertain(), 0.65)
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["reservations"], {})
            self.assertEqual(state["uncertain_requests"], 2)


if __name__ == "__main__":
    unittest.main()
