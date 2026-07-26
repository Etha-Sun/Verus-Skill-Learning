import json
import tempfile
import unittest
from pathlib import Path

from skill_evolution_pilot.codex_adapter import CodexStreamRecorder
from skill_evolution_pilot.events import audit_events, load_events
from skill_evolution_pilot.workspace import sha256_file


class CodexAdapterTest(unittest.TestCase):
    def test_raw_fields_tool_output_reasoning_and_snapshots_are_lossless(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate.rs"
            candidate.write_text("fn task() {}\n", encoding="utf-8")
            recorder = CodexStreamRecorder(
                raw_path=root / "codex_events.raw.jsonl",
                normalized_path=root / "agent_events.jsonl",
                snapshots_dir=root / "snapshots",
                run_id="codex-fixture",
                candidate_path=candidate,
            )
            long_output = "verification diagnostic\n" * 2000
            visible_reasoning = "visible reasoning summary\n" * 1000
            raw_events = [
                {"type": "thread.started", "thread_id": "thread-1"},
                {
                    "type": "item.started",
                    "item": {
                        "id": "cmd-1",
                        "type": "command_execution",
                        "command": "verus candidate.rs",
                        "status": "in_progress",
                    },
                },
            ]
            for index, raw in enumerate(raw_events, start=1):
                recorder.append_raw_line(json.dumps(raw), index)

            candidate.write_text("fn task() { assert(true); }\n", encoding="utf-8")
            completed = {
                "type": "item.completed",
                "item": {
                    "id": "cmd-1",
                    "type": "command_execution",
                    "command": "verus candidate.rs",
                    "status": "completed",
                    "exit_code": 0,
                    "aggregated_output": long_output,
                },
            }
            recorder.append_raw_line(json.dumps(completed), 3)
            candidate.write_text(
                "fn task() {\n    assert(true);\n}\n",
                encoding="utf-8",
            )
            edit = {
                "type": "item.completed",
                "item": {
                    "id": "edit-1",
                    "type": "file_change",
                    "status": "completed",
                    "changes": [
                        {
                            "path": "candidate.rs",
                            "kind": "update",
                            "patch": "@@ complete uncompressed patch @@",
                        }
                    ],
                },
            }
            reasoning = {
                "type": "item.completed",
                "item": {
                    "id": "reason-1",
                    "type": "reasoning",
                    "summary": visible_reasoning,
                },
            }
            recorder.append_raw_line(json.dumps(edit), 4)
            recorder.append_raw_line(json.dumps(reasoning), 5)
            recorder.append_raw_line(
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 20,
                            "reasoning_output_tokens": 12,
                        },
                    }
                ),
                6,
            )

            raw_rows = [
                json.loads(line)
                for line in (root / "codex_events.raw.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(raw_rows[2], completed)
            self.assertEqual(raw_rows[4]["item"]["summary"], visible_reasoning)

            rows, parse_errors = load_events(root / "agent_events.jsonl")
            self.assertEqual(parse_errors, 0)
            tool_result = next(row for row in rows if row["type"] == "tool_result")
            self.assertEqual(
                tool_result["data"]["raw_codex_event"]["item"]["aggregated_output"],
                long_output,
            )
            reasoning_row = next(
                row
                for row in rows
                if row["data"].get("raw_codex_event", {})
                .get("item", {})
                .get("type")
                == "reasoning"
            )
            self.assertEqual(
                reasoning_row["data"]["raw_codex_event"]["item"]["summary"],
                visible_reasoning,
            )
            snapshots = sorted((root / "snapshots").glob("*-candidate.rs"))
            diffs = sorted((root / "snapshots").glob("*-candidate.diff"))
            self.assertEqual(len(snapshots), 3)
            self.assertEqual(len(diffs), 3)
            self.assertEqual(sha256_file(snapshots[-1]), sha256_file(candidate))
            self.assertIn("assert(true)", diffs[-1].read_text(encoding="utf-8"))
            self.assertTrue(audit_events(rows)["valid_f3_event_stream"])

    def test_malformed_raw_line_is_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate.rs"
            candidate.write_text("fn task() {}\n", encoding="utf-8")
            recorder = CodexStreamRecorder(
                raw_path=root / "raw.jsonl",
                normalized_path=root / "normalized.jsonl",
                snapshots_dir=root / "snapshots",
                run_id="bad-fixture",
                candidate_path=candidate,
            )
            raw_line = "{not valid json and not truncated}"
            self.assertFalse(recorder.append_raw_line(raw_line, 1))
            self.assertEqual((root / "raw.jsonl").read_text().strip(), raw_line)
            rows, parse_errors = load_events(root / "normalized.jsonl")
            self.assertEqual(parse_errors, 0)
            malformed = next(
                row
                for row in rows
                if row["data"].get("codex_event_type") == "malformed_json"
            )
            self.assertEqual(malformed["data"]["raw_line"], raw_line)
            self.assertFalse(audit_events(rows)["valid_f3_event_stream"])

    def test_todo_list_events_are_complete_lossless_lifecycle_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate.rs"
            candidate.write_text("fn task() {}\n", encoding="utf-8")
            recorder = CodexStreamRecorder(
                raw_path=root / "raw.jsonl",
                normalized_path=root / "normalized.jsonl",
                snapshots_dir=root / "snapshots",
                run_id="todo-fixture",
                candidate_path=candidate,
            )
            todos = [
                {"text": "inspect", "completed": False},
                {"text": "verify", "completed": False},
            ]
            for index, event_type in enumerate(
                ("item.started", "item.updated", "item.completed"),
                start=1,
            ):
                raw = {
                    "type": event_type,
                    "item": {
                        "id": "todo-1",
                        "type": "todo_list",
                        "items": todos,
                    },
                }
                self.assertTrue(
                    recorder.append_raw_line(json.dumps(raw), index)
                )
            rows, parse_errors = load_events(root / "normalized.jsonl")
            self.assertEqual(parse_errors, 0)
            todo_rows = [
                row
                for row in rows
                if row["data"].get("raw_codex_event", {})
                .get("item", {})
                .get("type")
                == "todo_list"
            ]
            self.assertEqual(len(todo_rows), 3)
            self.assertTrue(all(row["payload_complete"] for row in todo_rows))
            self.assertEqual(
                todo_rows[1]["data"]["raw_codex_event"]["item"]["items"],
                todos,
            )
            self.assertTrue(audit_events(rows)["valid_f3_event_stream"])


if __name__ == "__main__":
    unittest.main()
