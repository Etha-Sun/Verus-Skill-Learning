from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from react_agent import LLMClient
from react_agent.converter import ParseResultType
from react_agent.models import Message, ModelSettings
from verus_agent.agent import VerusProofAgent
from verus_agent.docs import VerusDocumentation
from verus_agent.loop_control import ExplicitCompletionReActConverter
from verus_agent.workspace import prepare_workspace


class FakeClient(LLMClient):
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def chat(self, messages: list[Message], settings: ModelSettings | None = None):
        self.calls += 1
        return self.replies.pop(0)

    async def chat_async(self, messages, settings=None):
        return self.chat(messages, settings)


def setup_case(root: Path):
    source = root / "source.rs"
    source.write_text("fn proof() { assert(false); }\n", encoding="utf-8")
    workspace = prepare_workspace(source, root / "run")
    for name, body in {
        "verus": "#!/bin/sh\necho error >&2\nexit 1\n",
        "lynette": "#!/bin/sh\nexit 0\n",
    }.items():
        path = root / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
        setattr(workspace, f"{name}_bin", path)
    guide = root / "guide.json"
    guide.write_text(json.dumps({"documents": []}), encoding="utf-8")
    vstd = root / "vstd"
    vstd.mkdir()
    return workspace, VerusDocumentation(guide, vstd)


class StrictConverterTests(unittest.TestCase):
    def test_requires_exact_completion_or_action(self):
        converter = ExplicitCompletionReActConverter()
        self.assertEqual(
            converter.parse_response("narrative only").type,
            ParseResultType.FORMAT_ERROR,
        )
        self.assertEqual(
            converter.parse_response("Done. ACTION: TASK_COMPLETE").type,
            ParseResultType.FORMAT_ERROR,
        )
        self.assertEqual(
            converter.parse_response("ACTION: TASK_COMPLETE").type,
            ParseResultType.TASK_COMPLETE,
        )
        action = converter.parse_response(
            'Action:\n{"name":"read_file","arguments":{"path":"candidate.rs"}}'
        )
        self.assertEqual(action.type, ParseResultType.ACTION)
        self.assertEqual(action.action.name, "read_file")


    def test_action_parser_ignores_rust_braces_inside_json_strings(self):
        converter = ExplicitCompletionReActConverter()
        payload = json.dumps(
            {
                "name": "edit_lines",
                "arguments": {
                    "line_start": 10,
                    "line_end": 12,
                    "replacement_lines": [
                        "        proof {",
                        "            assert(self.wf());",
                        "        }",
                        "    }",
                    ],
                },
            }
        )
        result = converter.parse_response("Action:\n" + payload)
        self.assertEqual(result.type, ParseResultType.ACTION)
        self.assertEqual(result.action.name, "edit_lines")
        self.assertEqual(len(result.action.arguments["replacement_lines"]), 4)


class LoopGuardTests(unittest.TestCase):
    def run_case(self, replies):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        workspace, documentation = setup_case(root)
        client = FakeClient(replies)
        runner = VerusProofAgent(
            client=client,
            workspace=workspace,
            documentation=documentation,
            skill_dir=None,
            max_turns=100,
            verbose=False,
        )
        return temp, client, runner.run()

    def test_six_narratives_receive_escalation_then_fail_fast(self):
        temp, client, result = self.run_case(["narrative only"] * 6)
        try:
            self.assertFalse(result.success)
            self.assertEqual(client.calls, 6)
            self.assertEqual(result.agent_result.total_turns, 6)
            self.assertIn("6 consecutive responses", result.agent_result.error)
            self.assertEqual(result.loop_control["format_errors"], 6)
        finally:
            temp.cleanup()

    def test_six_premature_completions_receive_intervention_then_fail_fast(self):
        temp, client, result = self.run_case(["ACTION: TASK_COMPLETE"] * 6)
        try:
            self.assertFalse(result.success)
            self.assertEqual(client.calls, 6)
            self.assertEqual(result.agent_result.total_turns, 6)
            self.assertIn("6 consecutive premature completion signals", result.agent_result.error)
            self.assertEqual(result.loop_control["premature_completions"], 6)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
