from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

CODE = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE))

from react_agent.models import OpenAIClient, _make_cache_key  # noqa: E402


class OpenAIWireApiTests(unittest.TestCase):
    def test_responses_wire_maps_input_and_max_output_tokens(self) -> None:
        client = object.__new__(OpenAIClient)
        client.model = "deepseek-v4-pro"
        client.wire_api = "responses"
        transport = mock.Mock()
        transport.responses.create.return_value = SimpleNamespace(output_text="done")
        response = client._send_once(
            transport,
            [{"role": "user", "content": "repair"}],
            {"temperature": 0.2, "max_tokens": 8192},
        )
        self.assertEqual("done", client._parse_response(response)[0])
        transport.responses.create.assert_called_once_with(
            model="deepseek-v4-pro",
            input=[{"role": "user", "content": "repair"}],
            temperature=0.2,
            max_output_tokens=8192,
        )
        self.assertFalse(transport.chat.completions.create.called)

    def test_responses_wire_parses_bridge_sse_text(self) -> None:
        client = object.__new__(OpenAIClient)
        client.wire_api = "responses"
        raw = (
            'event: response.output_text.delta\n'
            'data: {"type":"response.output_text.delta","delta":"hello "}\n\n'
            'event: response.output_text.done\n'
            'data: {"type":"response.output_text.done","text":"hello world"}\n\n'
            'data: [DONE]\n\n'
        )
        self.assertEqual(("hello world", ""), client._parse_response(raw))

    def test_cache_key_separates_chat_and_responses(self) -> None:
        messages = [{"role": "user", "content": "same"}]
        self.assertNotEqual(
            _make_cache_key("model", messages, "chat_completions"),
            _make_cache_key("model", messages, "responses"),
        )


if __name__ == "__main__":
    unittest.main()
