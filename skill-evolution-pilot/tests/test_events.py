import json
import tempfile
import unittest
from pathlib import Path

from skill_evolution_pilot.events import EventLog, audit_events, load_events
from skill_evolution_pilot.redaction import REDACTED, secret_match_count


class EventLogTest(unittest.TestCase):
    def test_full_payload_is_preserved_and_secret_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = "canary-secret-value"
            long_output = "verifier-output-" * 2000
            path = root / "events.jsonl"
            log = EventLog(path, "run-1", (secret,))
            log.append(
                actor="qwen",
                event_type="model_request",
                request_id="r1",
                data={
                    "headers": {"Authorization": f"Bearer {secret}"},
                    "prompt": secret,
                },
            )
            log.append(
                actor="qwen",
                event_type="model_response",
                request_id="r1",
                data={"content": "ok", "reasoning_tokens": None},
            )
            log.append(
                actor="host",
                event_type="tool_call",
                tool_call_id="t1",
                data={"command": "verus candidate.rs"},
            )
            log.append(
                actor="host",
                event_type="tool_result",
                tool_call_id="t1",
                data={"exit_code": 0, "output": long_output},
            )
            log.append(
                actor="verus",
                event_type="verifier",
                candidate_sha256="a" * 64,
                data={"passed": True, "output": long_output},
            )

            rows, parse_errors = load_events(path)
            self.assertEqual(parse_errors, 0)
            self.assertEqual(rows[3]["data"]["output"], long_output)
            self.assertEqual(rows[0]["data"]["headers"]["Authorization"], REDACTED)
            self.assertEqual(rows[0]["data"]["prompt"], REDACTED)
            self.assertEqual(secret_match_count(root, (secret,)), 0)
            self.assertTrue(audit_events(rows)["valid_f3_event_stream"])

    def test_incomplete_payload_is_rejected_from_f3(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            log = EventLog(path, "run-2")
            log.append(
                actor="codex",
                event_type="lifecycle",
                payload_complete=False,
                data={"error": "summary-only edit"},
            )
            rows, parse_errors = load_events(path)
            audit = audit_events(rows, parse_errors)
            self.assertEqual(audit["incomplete_payload_count"], 1)
            self.assertFalse(audit["valid_f3_event_stream"])

    def test_raw_jsonl_is_one_complete_object_per_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            log = EventLog(path, "run-3")
            log.append(
                actor="host",
                event_type="lifecycle",
                data={"nested": {"text": "line 1\nline 2"}},
            )
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["data"]["nested"]["text"], "line 1\nline 2")


if __name__ == "__main__":
    unittest.main()
