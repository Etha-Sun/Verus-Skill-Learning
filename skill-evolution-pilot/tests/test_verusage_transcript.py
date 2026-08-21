import json
import tempfile
import unittest
from pathlib import Path

from skill_evolution_pilot.verusage_transcript import render_verusage_transcript


def _exact_blocks(text: str, tag: str) -> list[str]:
    lines = text.split("\n")
    values: list[str] = []
    opening = f"<{tag} "
    closing = f"</{tag}>"
    for index, line in enumerate(lines):
        if line.startswith(opening):
            values.append(lines[index + 1])
            if lines[index + 2] != closing:
                raise AssertionError(f"unterminated {tag} block")
    return values


class VerusageTranscriptTest(unittest.TestCase):
    def test_readable_layer_and_exact_jsonl_blocks_are_lossless(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            output = "first line\nsecond line\nUnicode: λ\u2028kept in JSONL\n"
            raw_rows = [
                {"type": "thread.started", "thread_id": "thread-1"},
                {
                    "type": "item.completed",
                    "item": {
                        "id": "reason-1",
                        "type": "reasoning",
                        "summary": "try the finite-subset lemma",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "id": "cmd-1",
                        "type": "command_execution",
                        "command": "./tools/run_verus.sh candidate.rs",
                        "aggregated_output": output,
                        "exit_code": 0,
                        "status": "completed",
                    },
                },
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "reasoning_output_tokens": 12,
                    },
                },
            ]
            raw_lines = [
                json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                for row in raw_rows
            ]
            (run_dir / "codex_events.raw.jsonl").write_text(
                "\n".join(raw_lines) + "\n",
                encoding="utf-8",
            )

            normalized_rows = [
                {
                    "schema_version": "1",
                    "event_index": 1,
                    "actor": "codex",
                    "type": "tool_result",
                    "payload_complete": True,
                    "data": {"raw_codex_event": raw_rows[2]},
                },
                {
                    "schema_version": "1",
                    "event_index": 2,
                    "actor": "host",
                    "type": "lifecycle",
                    "payload_complete": True,
                    "data": {
                        "boundary": "command_execution:cmd-1",
                        "snapshot": "snapshots/000002-candidate.rs",
                        "diff": "snapshots/000002-candidate.diff",
                    },
                },
            ]
            normalized_lines = [
                json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                for row in normalized_rows
            ]
            (run_dir / "agent_events.jsonl").write_text(
                "\n".join(normalized_lines) + "\n",
                encoding="utf-8",
            )
            (run_dir / "run_manifest.json").write_text(
                json.dumps({"run_id": "fixture", "model": "gpt-5.5"}),
                encoding="utf-8",
            )
            snapshots = run_dir / "snapshots"
            snapshots.mkdir()
            complete_diff = (
                "--- previous-candidate.rs\n"
                "+++ candidate.rs\n"
                "@@\n"
                "+    assert(true);\n"
            )
            (snapshots / "000002-candidate.diff").write_text(
                complete_diff,
                encoding="utf-8",
            )

            transcript = run_dir / "verusage_transcript.log"
            summary = render_verusage_transcript(
                run_dir=run_dir,
                output_path=transcript,
            )
            text = transcript.read_text(encoding="utf-8")

            self.assertIn("✓ Run command", text)
            self.assertIn("./tools/run_verus.sh candidate.rs", text)
            for output_line in output.splitlines():
                self.assertIn(f"   {output_line}\n", text)
            self.assertIn("● Reasoning summary", text)
            self.assertIn("host/lifecycle", text)
            self.assertIn(complete_diff.replace("\n", "\n   ").rstrip(), text)
            self.assertEqual(_exact_blocks(text, "raw_event_json"), raw_lines)
            self.assertEqual(
                _exact_blocks(text, "normalized_event_json"),
                normalized_lines,
            )
            self.assertEqual(summary["raw_event_count"], len(raw_lines))
            self.assertEqual(
                summary["normalized_event_count"],
                len(normalized_lines),
            )
            self.assertTrue(summary["tool_outputs_untruncated_by_renderer"])

    def test_malformed_raw_line_is_still_embedded_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            malformed = "{malformed raw event"
            (run_dir / "codex_events.raw.jsonl").write_text(
                malformed + "\n",
                encoding="utf-8",
            )
            (run_dir / "agent_events.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "event_index": 1,
                        "actor": "codex",
                        "type": "lifecycle",
                        "payload_complete": False,
                        "data": {"codex_event_type": "malformed_json"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            transcript = run_dir / "readable.log"
            summary = render_verusage_transcript(
                run_dir=run_dir,
                output_path=transcript,
            )
            text = transcript.read_text(encoding="utf-8")
            self.assertEqual(_exact_blocks(text, "raw_event_json"), [malformed])
            self.assertEqual(summary["malformed_raw_count"], 1)
            self.assertIn("Malformed raw JSONL", text)

    def test_refuses_to_overwrite_existing_or_source_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            raw = run_dir / "codex_events.raw.jsonl"
            normalized = run_dir / "agent_events.jsonl"
            raw.write_text("{}\n", encoding="utf-8")
            normalized.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not replace"):
                render_verusage_transcript(run_dir=run_dir, output_path=raw)
            output = run_dir / "readable.log"
            output.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "already exists"):
                render_verusage_transcript(run_dir=run_dir, output_path=output)


if __name__ == "__main__":
    unittest.main()
