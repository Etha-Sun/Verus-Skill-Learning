import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_evolution_pilot.codex_runner import (
    _codex_environment,
    _command_modifies_candidate,
    _interrupt_then_kill_process_group,
    _run_complete,
    _verus_tool_manifest,
    build_command,
    run_codex_smoke,
)


class CodexRunnerTest(unittest.TestCase):
    def test_verus_manifest_hashes_the_real_rust_verify_implementation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            verus = self._executable(
                root / "verus", "#!/bin/sh\necho 'Version: test'\n"
            )
            implementation = self._executable(
                root / "rust_verify", "#!/bin/sh\necho implementation\n"
            )
            manifest = _verus_tool_manifest(verus)
            self.assertNotEqual(manifest["sha256"], manifest["implementation_sha256"])
            self.assertEqual(
                manifest["implementation_sha256"],
                hashlib.sha256(implementation.read_bytes()).hexdigest(),
            )

    def test_complete_timeout_kills_the_entire_process_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            started = time.monotonic()
            result = _run_complete(
                ["bash", "-c", "sleep 30 & wait"],
                cwd=Path(tmp),
                timeout_seconds=1,
            )
            self.assertTrue(result["timed_out"])
            self.assertIsNone(result["returncode"])
            self.assertLess(time.monotonic() - started, 5)

    def test_actor_timeout_force_kills_a_process_that_ignores_sigint(self):
        process = subprocess.Popen(
            ["bash", "-c", "trap '' INT; sleep 30 & wait"],
            start_new_session=True,
            text=True,
        )
        timed_out = threading.Event()
        started = time.monotonic()
        _interrupt_then_kill_process_group(
            process, timed_out, grace_seconds=0.2
        )
        process.wait(timeout=2)
        self.assertTrue(timed_out.is_set())
        self.assertLess(time.monotonic() - started, 2)

    def test_shell_edit_audit_allows_read_only_commands_and_stderr_merge(self):
        self.assertFalse(
            _command_modifies_candidate("./tools/run_verus.sh candidate.rs 2>&1")
        )
        self.assertFalse(_command_modifies_candidate("sed -n '1,80p' candidate.rs"))
        self.assertFalse(_command_modifies_candidate("git diff -- candidate.rs"))
        self.assertFalse(
            _command_modifies_candidate(
                "cp candidate.rs /tmp/probe.rs && sed -i 's/a/b/' /tmp/probe.rs"
            )
        )
        self.assertFalse(
            _command_modifies_candidate(
                "cp input.rs /tmp/probe/candidate.rs && cd /tmp/probe "
                "&& sed -i 's/a/b/' candidate.rs"
            )
        )
        self.assertTrue(_command_modifies_candidate("sed -i 's/a/b/' candidate.rs"))
        self.assertTrue(
            _command_modifies_candidate(
                "cd /tmp/probe && sed -i 's/a/b/' /workspace/candidate.rs"
            )
        )
        self.assertTrue(_command_modifies_candidate("cp proof.rs candidate.rs"))
        self.assertTrue(_command_modifies_candidate("printf x > candidate.rs"))
        self.assertTrue(_command_modifies_candidate("cat proof.rs | tee candidate.rs"))

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
                    stage="formal_held_out_evaluation",
                )

            self.assertEqual(result["status"], "SOLVED")
            self.assertTrue(result["fidelity"]["f3"])
            self.assertEqual(result["fidelity"]["completed_tool_or_edit_boundaries"], 2)
            self.assertGreaterEqual(result["fidelity"]["candidate_snapshot_count"], 4)
            self.assertTrue(result["fidelity"]["reasoning_token_count_available"])
            self.assertEqual(result["fidelity"]["visible_reasoning_item_count"], 0)
            self.assertEqual(result["fidelity"]["visible_reasoning_text_chars"], 0)
            self.assertFalse(result["fidelity"]["raw_hidden_chain_of_thought_claimed"])
            raw_rows = [
                json.loads(line)
                for line in (out_dir / "codex_events.raw.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(raw_rows[-1]["usage"]["reasoning_output_tokens"], 3)
            self.assertTrue((out_dir / "visibility_manifest.json").is_file())
            self.assertTrue((out_dir / "validation.json").is_file())
            self.assertTrue((out_dir / "actor_phase_complete.json").is_file())
            self.assertTrue((out_dir / "snapshots").is_dir())
            manifest = json.loads(
                (out_dir / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["stage"], "formal_held_out_evaluation")

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
        for capability in (
            "apps",
            "browser_use",
            "computer_use",
            "goals",
            "multi_agent",
            "plugins",
            "skill_search",
        ):
            self.assertIn(f"--disable {capability}", joined)

    def test_command_supports_responses_bridge_without_changing_defaults(self):
        command = build_command(
            codex_bin=Path("/tools/codex"),
            workspace=Path("/run/workspace"),
            last_message=Path("/run/last.txt"),
            model="deepseek-v4-flash",
            reasoning_effort="high",
            provider_id="deepseek_bridge",
            provider_base_url="http://127.0.0.1:18080/tasks/task-1/v1",
            provider_env_key="DEEPSEEK_API_KEY",
            model_context_window=262144,
            model_catalog_json=Path("/run/models.json"),
        )
        joined = " ".join(command)
        self.assertIn('model_provider="deepseek_bridge"', joined)
        self.assertIn('wire_api="responses"', joined)
        self.assertIn("model_context_window=262144", joined)
        self.assertIn('model_catalog_json="/run/models.json"', joined)
        self.assertNotIn("dummy-secret", joined)

    def test_cross_provider_command_matches_frozen_invocation_contract(self):
        prompt = "Repair the Verus proof in candidate.rs."
        command = build_command(
            codex_bin=Path("/tools/codex"),
            workspace=Path("/run/workspace"),
            last_message=Path("/run/last.txt"),
            model="glm-5.3",
            reasoning_effort="max",
            provider_id="glm",
            provider_base_url="http://127.0.0.1:18083/v1",
            provider_env_key="SKILLOPT_CODEX_BRIDGE_TOKEN",
            model_context_window=1048576,
            contract_profile="cross_provider_20260819",
            prompt_text=prompt,
        )
        joined = " ".join(command)
        self.assertEqual(command[-1], prompt)
        self.assertIn("-a never exec", joined)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--json", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("-s workspace-write", joined)
        self.assertIn('model_provider="glm"', joined)
        self.assertIn("request_max_retries=4", joined)
        self.assertIn("stream_max_retries=4", joined)
        self.assertIn('model_reasoning_effort="max"', joined)
        self.assertIn("model_context_window=1048576", joined)
        self.assertIn("model_max_output_tokens=8192", joined)
        self.assertNotIn("model_reasoning_summary", joined)

        isolated = build_command(
            codex_bin=Path("/tools/codex"),
            workspace=Path("/run/workspace"),
            last_message=Path("/run/last.txt"),
            model="glm-5.3",
            reasoning_effort="max",
            contract_profile="cross_provider_20260819",
            prompt_text=prompt,
            outer_isolation=True,
        )
        self.assertIn("-s danger-full-access", " ".join(isolated))

    def test_actor_environment_excludes_unrelated_credentials(self):
        with patch.dict(
            os.environ,
            {
                "HOME": "/home/test",
                "PATH": "/usr/bin",
                "DEEPSEEK_API_KEY": "upstream-secret",
                "SKILLOPT_CODEX_BRIDGE_TOKEN": "bridge-secret",
            },
            clear=True,
        ):
            direct = _codex_environment(None)
            bridged = _codex_environment("SKILLOPT_CODEX_BRIDGE_TOKEN")
        self.assertNotIn("DEEPSEEK_API_KEY", direct)
        self.assertNotIn("DEEPSEEK_API_KEY", bridged)
        self.assertNotIn("SKILLOPT_CODEX_BRIDGE_TOKEN", direct)
        self.assertEqual(
            bridged["SKILLOPT_CODEX_BRIDGE_TOKEN"], "bridge-secret"
        )


if __name__ == "__main__":
    unittest.main()
