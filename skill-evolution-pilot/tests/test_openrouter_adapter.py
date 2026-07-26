import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_evolution_pilot.events import EventLog, audit_events, load_events
from skill_evolution_pilot.openrouter_adapter import (
    DEFAULT_MODEL,
    OpenRouterClient,
    OpenRouterError,
)
from skill_evolution_pilot.redaction import REDACTED, secret_match_count


class OpenRouterAdapterTest(unittest.TestCase):
    def test_complete_response_and_reasoning_fields_are_preserved(self):
        secret = "canary-openrouter-secret"
        visible_reasoning = "thinking-visible-to-api\n" * 2000
        reasoning_details = [
            {"type": "reasoning.text", "text": "detail\n" * 1000}
        ]
        provider_response = {
            "id": "generation-1",
            "model": DEFAULT_MODEL,
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "READY",
                        "reasoning": visible_reasoning,
                        "reasoning_details": reasoning_details,
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 130,
                "total_tokens": 141,
                "completion_tokens_details": {"reasoning_tokens": 123},
            },
            "provider_extra": {"must_remain": "full"},
        }

        captured_authorization = []

        def fake_transport(request, timeout):
            self.assertGreater(timeout, 0)
            captured_authorization.append(request.get_header("Authorization"))
            return json.dumps(provider_response).encode("utf-8")

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"OPENROUTER_API_KEY": secret}, clear=False
        ):
            root = Path(tmp)
            events = root / "agent_events.jsonl"
            provider_io = root / "provider_io.jsonl"
            log = EventLog(events, "openrouter-fixture", (secret,))
            result = OpenRouterClient(transport=fake_transport).complete(
                messages=[{"role": "user", "content": "Reply READY"}],
                event_log=log,
                provider_io_path=provider_io,
            )

            self.assertEqual(captured_authorization, [f"Bearer {secret}"])
            self.assertEqual(result["usage"]["reasoning_tokens"], 123)
            rows, parse_errors = load_events(events)
            self.assertEqual(parse_errors, 0)
            self.assertTrue(audit_events(rows)["valid_f3_event_stream"])
            response = rows[1]["data"]["provider_response"]
            self.assertEqual(
                response["choices"][0]["message"]["reasoning"],
                visible_reasoning,
            )
            self.assertEqual(
                response["choices"][0]["message"]["reasoning_details"],
                reasoning_details,
            )
            io_rows = [
                json.loads(line)
                for line in provider_io.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                io_rows[1]["payload"]["provider_extra"]["must_remain"], "full"
            )
            self.assertEqual(
                io_rows[0]["payload"]["headers"]["Authorization"], REDACTED
            )
            self.assertEqual(secret_match_count(root, (secret,)), 0)

    def test_model_mismatch_stops_the_run(self):
        response = {
            "model": "different/model",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "READY"},
                }
            ],
            "usage": {},
        }

        def fake_transport(request, timeout):
            return json.dumps(response).encode("utf-8")

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"OPENROUTER_API_KEY": "test-secret"}, clear=False
        ):
            log = EventLog(Path(tmp) / "events.jsonl", "mismatch", ("test-secret",))
            with self.assertRaisesRegex(OpenRouterError, "requested model"):
                OpenRouterClient(transport=fake_transport).complete(
                    messages=[{"role": "user", "content": "READY"}],
                    event_log=log,
                )

    def test_missing_credential_stops_before_transport(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {}, clear=True
        ):
            log = EventLog(Path(tmp) / "events.jsonl", "missing-key")
            with self.assertRaisesRegex(OpenRouterError, "not present"):
                OpenRouterClient(
                    transport=lambda request, timeout: b"never called"
                ).complete(
                    messages=[{"role": "user", "content": "READY"}],
                    event_log=log,
                )


if __name__ == "__main__":
    unittest.main()
