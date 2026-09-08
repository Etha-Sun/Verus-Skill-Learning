import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from verus_self_evolve.trajectory_parsers import (
    _write_result,
    parse_sonnet45_trace,
    parse_structured_prediction,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TrajectoryParsersTest(unittest.TestCase):
    def test_sonnet_parser_marks_intermediate_code_as_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "results-sonnet45"
            root.mkdir()
            log = root / "task.log"
            log.write_text(
                "● I will inspect the proof.\n\n"
                "✓ Edit task_verified.rs (+3 -1)\n"
                "Run Verus on the verified file\n"
                "   $ verus task_verified.rs\n"
                "   verification results:: 1 verified, 0 errors\n"
                "Total usage est:       1 Premium requests\n"
                "Total duration (wall): 2m 3.5s\n"
                "    claude-sonnet-4.5 2k input, 50 output, 1.5k cache read\n",
                encoding="utf-8",
            )
            (root / "task.rs").write_text("fn task() {}\n", encoding="utf-8")
            (root / "task_verified.rs").write_text(
                "fn task() { assert(true); }\n", encoding="utf-8"
            )

            parsed = parse_sonnet45_trace(log)

            self.assertEqual(parsed["model"], "claude-sonnet-4.5")
            self.assertEqual(
                parsed["reconstruction_fidelity"], "partial_terminal_transcript"
            )
            self.assertFalse(parsed["checkpoint_contract"]["intermediate_source_exact"])
            edits = [row for row in parsed["events"] if row["type"] == "code_edit"]
            self.assertEqual(len(edits), 1)
            self.assertEqual(edits[0]["added_lines_reported"], 3)
            self.assertEqual(edits[0]["deleted_lines_reported"], 1)
            verus = [
                row for row in parsed["events"] if row["type"] == "verifier_invocation"
            ]
            self.assertEqual(verus[0]["command"], "verus task_verified.rs")
            self.assertTrue(verus[0]["verifier"]["passed"])
            self.assertEqual(parsed["usage"]["totals"]["uncached_total_tokens"], 550)
            self.assertEqual(parsed["usage"]["wall_seconds"], 123.5)

    def test_structured_parser_aligns_exact_snapshots_and_complete_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            prediction = run / "predictions/task-id"
            workspace = prediction / "workspace"
            snapshots = prediction / "snapshots"
            workspace.mkdir(parents=True)
            snapshots.mkdir()
            source = "fn task() {}\n"
            candidate = "fn task() { assert(true); }\n"
            source_hash = _sha256(source)
            candidate_hash = _sha256(candidate)
            (workspace / "input.rs").write_text(source, encoding="utf-8")
            (workspace / "candidate.rs").write_text(candidate, encoding="utf-8")
            (snapshots / "000001-candidate.rs").write_text(source, encoding="utf-8")
            (snapshots / "000001-candidate.diff").write_text("", encoding="utf-8")
            (snapshots / "000005-candidate.rs").write_text(
                candidate, encoding="utf-8"
            )
            (prediction / "conversation.json").write_text(
                json.dumps(
                    [
                        {"role": "user", "content": "Repair candidate.rs."},
                        {
                            "role": "assistant",
                            "type": "agent_message",
                            "content": "I added the proof.",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            events = [
                {
                    "schema_version": "1",
                    "event_index": 1,
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "run_id": "task-id",
                    "actor": "host",
                    "type": "lifecycle",
                    "payload_complete": True,
                    "candidate_sha256": source_hash,
                    "data": {},
                },
                {
                    "schema_version": "1",
                    "event_index": 5,
                    "timestamp": "2026-01-01T00:01:00+00:00",
                    "run_id": "task-id",
                    "actor": "verus",
                    "type": "verifier",
                    "payload_complete": True,
                    "candidate_sha256": candidate_hash,
                    "data": {
                        "raw_codex_event": {
                            "item": {
                                "type": "command_execution",
                                "command": "verus candidate.rs",
                                "aggregated_output": (
                                    "verification results:: 1 verified, 0 errors\n"
                                ),
                                "exit_code": 0,
                                "status": "completed",
                            }
                        }
                    },
                },
            ]
            (prediction / "agent_events.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in events),
                encoding="utf-8",
            )
            (prediction / "result.json").write_text(
                json.dumps(
                    {
                        "id": "task-id",
                        "actor_model": "model-id",
                        "status": "complete",
                        "proof_solved": True,
                        "within_budget": True,
                        "timed_out": False,
                        "safety_passed": True,
                        "fidelity": "V2_TRACE",
                        "actor_wall_seconds": 60,
                        "usage": {"input_tokens": 10, "output_tokens": 2},
                    }
                ),
                encoding="utf-8",
            )
            (run / "bridge_calls.jsonl").write_text(
                json.dumps(
                    {
                        "task_id": "arm--task-id--attempt-1",
                        "attempts": [
                            {
                                "usage": {
                                    "prompt_tokens": 11,
                                    "completion_tokens": 3,
                                    "prompt_cache_hit_tokens": 7,
                                }
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            parsed = parse_structured_prediction(prediction)

            self.assertEqual(parsed["model"], "model-id")
            self.assertEqual(
                parsed["reconstruction_fidelity"], "exact_candidate_snapshots"
            )
            self.assertEqual(len(parsed["checkpoints"]), 2)
            self.assertTrue(
                parsed["checkpoint_contract"]["all_snapshot_hashes_observed_in_events"]
            )
            verifier = [row for row in parsed["events"] if row["type"] == "verifier"]
            self.assertTrue(verifier[0]["verifier"]["passed"])
            self.assertEqual(parsed["usage"]["complete_ledger"]["total_tokens"], 14)

    def test_structured_parser_requires_complete_core_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "structured prediction is missing"):
                parse_structured_prediction(Path(tmp))

    def test_writer_refuses_raw_directory_and_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "raw"
            source.mkdir()
            with self.assertRaisesRegex(ValueError, "outside the raw trace directory"):
                _write_result({}, source / "parsed.json", source)

            output = root / "results/parsed.json"
            output.parent.mkdir()
            output.write_text("keep me\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                _write_result({}, output, source)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep me\n")


if __name__ == "__main__":
    unittest.main()
