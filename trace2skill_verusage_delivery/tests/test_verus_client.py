from __future__ import annotations

import unittest

from react_agent import LLMClient
from react_agent.models import Message, ModelSettings

from verus_agent.client import FixedGenerationClient


class RecordingClient(LLMClient):
    def __init__(self) -> None:
        self.settings: ModelSettings | None = None

    def chat(self, messages, settings=None):
        self.settings = settings
        return "ok"

    async def chat_async(self, messages, settings=None):
        return self.chat(messages, settings)


class FixedGenerationClientTests(unittest.TestCase):
    def test_cli_generation_values_override_react_defaults(self) -> None:
        inner = RecordingClient()
        client = FixedGenerationClient(
            inner, temperature=0.6, max_output_tokens=8192
        )
        client.chat(
            [Message(role="user", content="test")],
            ModelSettings(temperature=0.7, stop=["Observation:"]),
        )
        self.assertEqual(inner.settings.temperature, 0.6)
        self.assertEqual(inner.settings.max_tokens, 8192)
        self.assertEqual(inner.settings.stop, ["Observation:"])


if __name__ == "__main__":
    unittest.main()
