import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_evolution_pilot.codex_runner import build_command, run_codex_smoke


class CodexRunnerTest(unittest.TestCase):
    @staticmethod
    def _executable(path: Path, text: str) -> Path:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_fake_codex_produces_audited_lossless_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run-root"
            run_root.mkdir()
            source = root / "source.rs"
            source.write_text("fn task() {}\n", encoding="utf-8")
            tools = root / "tools"
            tools.mkdir()
            codex = self._executable(
                tools / "codex",
                """#!/usr/bin/env python3
import json
import pathlib
import sys

if "--version" in sys.argv:
    print("codex-cli fake")
    raise SystemExit(0)

workspace = pathlib.Path(sys.argv[sys.argv.index("-C") + 1])
last = pathlib.Path(sys.argv[sys.argv.index("--output-last-message") + 1])
candidate = workspace / "candidate.rs"
print(json.dumps({"type": "thread.started", "thread_id": "fake"}), flush=True)
print(json.dumps({"type": "turn.started"}), flush=True)
print(json.dumps({"type": "item.started", "item": {
    "id": "edit-1", "type": "file_change", "status": "in_progress",
    "changes": [{"path": str(candidate), "kind": "update"}]
}}), flush=True)
candidate.write_text("fn task() { assert(true); }\\n")
print(json.dumps({"type": "item.completed", "item": {
    "id": "edit-1", "type": "file_change", "status": "completed",
    "changes": [{"path": str(candidate), "kind": "update"}]
}}), flush=True)
command = "./tools/run_verus.sh candidate.rs"
print(json.dumps({"type": "item.started", "item": {
    "id": "cmd-1", "type": "command_execution", "command": command,
    "status": "in_progress", "aggregated_output": "", "exit_code": None
}}), flush=True)
print(json.dumps({"type": "item.completed", "item": {
    "id": "cmd-1", "type": "command_execution", "command": command,
    "status": "completed", "aggregated_output":
    "verification results:: 1 verified, 0 errors\\n", "exit_code": 0
}}), flush=True)
print(json.dumps({"type": "item.completed", "item": {
    "id": "msg-1", "type": "agent_message", "text": "complete"
}}), flush=True)
print(json.dumps({"type": "turn.completed", "usage": {
    "input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 5,
    "reasoning_output_tokens": 3
}}), flush=True)
last.write_text("complete")
""",
            )
            verus = self._executable(
                tools / "verus",
                "#!/usr/bin/env bash\necho 'verification results:: 1 verified, 0 errors'\n",
            )
            lynette = self._executable(
                tools / "lynette",
                "#!/usr/bin/env bash\nexit 0\n",
            )
            out_dir = run_root / "fake-codex-smoke"
            with patch.dict(
                os.environ,
                {"VERUS_SKILL_RUN_ROOT": str(run_root)},
                clear=False,
            ):
                result = run_codex_smoke(
                    source=source,
                    out_dir=out_dir,
                    codex_bin=codex,
                    verus_bin=verus,
                    lynette_bin=lynette,
                    timeout_seconds=30,
                )

            self.assertEqual(result["status"], "SOLVED")
            self.assertTrue(result["fidelity"]["f3"])
            self.assertEqual(
                result["fidelity"]["completed_tool_or_edit_boundaries"], 2
            )
            self.assertGreaterEqual(
                result["fidelity"]["candidate_snapshot_count"], 4
            )
            self.assertTrue(result["fidelity"]["reasoning_token_count_available"])
            self.assertEqual(result["fidelity"]["visible_reasoning_item_count"], 0)
            self.assertEqual(result["fidelity"]["visible_reasoning_text_chars"], 0)
            self.assertFalse(
                result["fidelity"]["raw_hidden_chain_of_thought_claimed"]
            )
            raw_rows = [
                json.loads(line)
                for line in (out_dir / "codex_events.raw.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(raw_rows[-1]["usage"]["reasoning_output_tokens"], 3)
            self.assertTrue((out_dir / "visibility_manifest.json").is_file())
            self.assertTrue((out_dir / "validation.json").is_file())
            self.assertTrue((out_dir / "snapshots").is_dir())

    def test_command_explicitly_requests_reasoning_summary_and_raw_events(self):
        command = build_command(
            codex_bin=Path("/tools/codex"),
            workspace=Path("/run/workspace"),
            last_message=Path("/run/last.txt"),
            model="gpt-5.6-sol",
            reasoning_effort="high",
        )
        joined = " ".join(command)
        self.assertIn('model_reasoning_summary="detailed"', joined)
        self.assertIn("model_supports_reasoning_summaries=true", joined)
        self.assertIn("hide_agent_reasoning=false", joined)
        self.assertIn("show_raw_agent_reasoning=true", joined)


if __name__ == "__main__":
    unittest.main()
