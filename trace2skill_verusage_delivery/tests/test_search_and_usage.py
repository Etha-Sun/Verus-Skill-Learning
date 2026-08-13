from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from react_agent.models import Message, ModelSettings

from verus_agent.search import search_workspace_file
from verus_agent.tools import create_workspace_tools
from verus_agent.usage_client import TokenUsageLedger, UsageTrackingOpenAIClient
from verus_agent.workspace import prepare_workspace, sha256_file


class SearchFileTests(unittest.TestCase):
    def _workspace(self, root: Path):
        source = root / "source.rs"
        source.write_text(
            "line one\nTarget needle\nline three\ntarget second\nline five\n",
            encoding="utf-8",
        )
        return source, prepare_workspace(source, root / "run")

    def test_literal_search_is_bounded_line_numbered_and_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source, workspace = self._workspace(Path(temp))
            before = sha256_file(source)
            result = search_workspace_file(
                workspace,
                "target",
                path="candidate.rs",
                max_results=1,
                context_lines=1,
                case_sensitive=False,
            )
            self.assertIn("1 result(s) returned", result)
            self.assertIn(">000002: Target needle", result)
            self.assertIn(" 000001: line one", result)
            self.assertNotIn("target second", result)
            self.assertEqual(before, sha256_file(source))
            self.assertEqual(
                workspace.input_path.read_text(encoding="utf-8"),
                workspace.candidate_path.read_text(encoding="utf-8"),
            )

    def test_search_rejects_paths_and_unsafe_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, workspace = self._workspace(Path(temp))
            with self.assertRaisesRegex(ValueError, "allowlisted"):
                search_workspace_file(workspace, "needle", path="../source.rs")
            with self.assertRaisesRegex(ValueError, "between 1 and 50"):
                search_workspace_file(workspace, "needle", max_results=51)
            with self.assertRaisesRegex(ValueError, "between 0 and 5"):
                search_workspace_file(workspace, "needle", context_lines=6)

    def test_audit_hashes_query_instead_of_recording_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, workspace = self._workspace(Path(temp))
            secret_query = "Target needle"
            search_workspace_file(workspace, secret_query)
            audit_text = workspace.audit_path.read_text(encoding="utf-8")
            record = json.loads(audit_text.splitlines()[-1])
            self.assertEqual(record["operation"], "search_file")
            self.assertIn("query_sha256", record)
            self.assertNotIn(secret_query, audit_text)

    def test_workspace_tool_registry_exposes_search_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, workspace = self._workspace(Path(temp))
            names = [tool.name for tool in create_workspace_tools(workspace)]
            self.assertEqual(
                names,
                [
                    "read_file",
                    "search_file",
                    "edit_lines",
                    "insert_lines",
                    "replace_text",
                    "run_verus",
                    "run_lynette",
                ],
            )


class TokenUsageTests(unittest.TestCase):
    @staticmethod
    def _response(
        *,
        prompt: int = 10,
        completion: int = 4,
        cached: int = 2,
        reasoning: int = 1,
        model: str = "qwen35-27b",
    ) -> SimpleNamespace:
        usage = SimpleNamespace(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
            prompt_tokens_details=SimpleNamespace(cached_tokens=cached),
            completion_tokens_details=SimpleNamespace(reasoning_tokens=reasoning),
        )
        return SimpleNamespace(
            id="response-1",
            model=model,
            created=123,
            usage=usage,
        )

    def test_ledger_aggregates_provider_usage_and_latency(self) -> None:
        ledger = TokenUsageLedger()
        ledger.record_response(self._response(), 0.25)
        ledger.record_response(
            self._response(prompt=20, completion=8, cached=3, reasoning=2), 0.75
        )
        summary = ledger.summary()
        self.assertEqual(summary["request_count"], 2)
        self.assertEqual(summary["requests_with_usage"], 2)
        self.assertTrue(summary["usage_complete"])
        self.assertEqual(summary["prompt_tokens"], 30)
        self.assertEqual(summary["completion_tokens"], 12)
        self.assertEqual(summary["total_tokens"], 42)
        self.assertEqual(summary["cached_prompt_tokens"], 5)
        self.assertEqual(summary["reasoning_tokens"], 3)
        self.assertEqual(summary["latency_seconds_total"], 1.0)
        self.assertEqual(len(summary["requests"]), 2)

    def test_missing_provider_usage_is_explicit(self) -> None:
        ledger = TokenUsageLedger()
        ledger.record_response(
            SimpleNamespace(id="response-2", model="qwen35-27b", created=124, usage=None),
            0.1,
        )
        summary = ledger.summary()
        self.assertEqual(summary["request_count"], 1)
        self.assertEqual(summary["requests_with_usage"], 0)
        self.assertFalse(summary["usage_complete"])
        self.assertIsNone(summary["total_tokens"])

    def test_tracking_client_uses_fake_transport_without_network(self) -> None:
        client = object.__new__(UsageTrackingOpenAIClient)
        client.model = "qwen35-27b"
        client.generation_config = {"temperature": 0.6, "max_tokens": 8192}
        client.usage_ledger = TokenUsageLedger()
        captured: dict[str, object] = {}

        def fake_send(messages, config):
            captured["messages"] = messages
            captured["config"] = config
            return self._response()

        client._send_request_with_retry = fake_send
        client._parse_response = lambda response: ("ACTION: TASK_COMPLETE", "")
        reply = client.chat(
            [Message(role="user", content="offline")],
            ModelSettings(temperature=0.2, max_tokens=1024),
        )
        self.assertEqual(reply, "ACTION: TASK_COMPLETE")
        self.assertEqual(captured["config"]["temperature"], 0.2)
        self.assertEqual(captured["config"]["max_tokens"], 1024)
        summary = client.usage_summary()
        self.assertEqual(summary["request_count"], 1)
        self.assertEqual(summary["total_tokens"], 14)


if __name__ == "__main__":
    unittest.main()
