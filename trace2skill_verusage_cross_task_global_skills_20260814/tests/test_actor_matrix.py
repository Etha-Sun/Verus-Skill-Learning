from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CODE = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE))

import actor_isolation  # noqa: E402
import run_actor_matrix as subject  # noqa: E402
from global_skill_experiment.gate import CommandAggregateEvaluator  # noqa: E402


class ActorMatrixTests(unittest.TestCase):
    def make_skill(self, root: Path, *, reference: bool = False) -> Path:
        skill = root / "verus-proof-repair"
        (skill / "agents").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: verus-proof-repair\ndescription: test\n---\n# Test\n",
            encoding="utf-8",
        )
        (skill / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: "Test"\n  default_prompt: "Use $verus-proof-repair."\n',
            encoding="utf-8",
        )
        if reference:
            (skill / "references").mkdir()
            (skill / "references" / "detail.md").write_text("# Detail\n")
        return skill

    def test_frozen_val_and_test_manifests_resolve_exactly(self) -> None:
        for split in ("val", "test"):
            rows = subject.load_split(split)
            self.assertEqual(20, len(rows))
            self.assertEqual(set(range(1, 21)), {row["_split_index"] for row in rows})
            self.assertEqual(
                {"AC": 6, "AL": 7, "IR": 7},
                dict(__import__("collections").Counter(row["project_code"] for row in rows)),
            )

    def test_skill_audit_enforces_zero_reference_m_core(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plain = self.make_skill(root / "plain")
            audit = subject.skill_audit(plain, require_zero_references=True)
            self.assertEqual(0, audit["reference_file_count"])
            with_reference = self.make_skill(root / "with_ref", reference=True)
            with self.assertRaises(ValueError):
                subject.skill_audit(with_reference, require_zero_references=True)
            self.assertEqual(
                1,
                subject.skill_audit(
                    with_reference, require_zero_references=False
                )["reference_file_count"],
            )

    def test_actor_environment_removes_host_credentials(self) -> None:
        actor_env = subject.actor_subprocess_env(
            {
                "PATH": "/usr/bin",
                "PYTHONPATH": "/private/code",
                "DEEPSEEK_API_KEY": "real-provider-key",
                "GITHUB_TOKEN": "secret-token",
                "AWS_SECRET_ACCESS_KEY": "secret-key",
                "HARMLESS": "visible",
            }
        )
        self.assertEqual("/usr/bin", actor_env["PATH"])
        self.assertEqual("visible", actor_env["HARMLESS"])
        self.assertEqual(
            "local-bridge-only-not-a-provider-secret",
            actor_env["DEEPSEEK_API_KEY"],
        )
        self.assertNotIn("PYTHONPATH", actor_env)
        self.assertNotIn("GITHUB_TOKEN", actor_env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", actor_env)

    def test_isolation_cleanup_never_recurses_into_nonempty_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = root / "stage"
            mounted_placeholder = stage / "workspace"
            mounted_placeholder.mkdir(parents=True)
            sentinel = mounted_placeholder / "must-survive.txt"
            sentinel.write_text("preserve", encoding="utf-8")

            actor_isolation.remove_empty_stage(stage, (mounted_placeholder,))

            self.assertEqual("preserve", sentinel.read_text(encoding="utf-8"))
            self.assertTrue(stage.is_dir())

    def test_isolated_codex_command_freezes_namespace_wrapper(self) -> None:
        command = subject.isolated_codex_command(
            ["/opt/codex", "exec", "prompt"],
            work_dir=Path("/scratch/run/task"),
            codex_bin=Path("/opt/codex"),
            verus_bin=Path("/scratch/tools/verus/bin/verus"),
            rust_root=Path("/scratch/tools/rust"),
            lynette_bin=Path("/scratch/tools/lynette"),
            scratch_root=Path("/scratch"),
            bridge_port=4017,
        )
        self.assertEqual(str(subject.UNSHARE_BIN), command[0])
        self.assertIn("--map-root-user", command)
        self.assertIn(str(subject.ISOLATION_RUNNER), command)
        self.assertIn("--bridge-port", command)
        self.assertIn("4017", command)
        separator = command.index("--")
        self.assertEqual(["/opt/codex", "exec", "prompt"], command[separator + 1 :])

    def test_command_access_audit_rejects_actual_broad_scratch_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "events.jsonl"
            work = root / "task"
            work.mkdir()
            command = f"rg -n pattern {root}/tools/verus {root}"
            log.write_text(
                json.dumps(
                    {
                        "type": "item.started",
                        "item": {"type": "command_execution", "command": command},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            audit = subject.command_access_audit(
                log,
                work_dir=work,
                verus_bin=root / "tools" / "verus" / "bin" / "verus",
                rust_root=root / "tools" / "rust",
                lynette_bin=root / "tools" / "lynette",
                scratch_root=root,
            )
        self.assertFalse(audit["passed"])
        self.assertIn("scratch_root_probe", audit["violation_categories"])

    def test_command_access_audit_accepts_codex_stderr_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / "task"
            work.mkdir()
            log = root / "events.jsonl"
            log.write_text(
                "Reading additional input from stdin...\n"
                "2026-08-16T22:55:50Z  WARN codex_core_plugins::startup_sync: "
                "network unavailable\n"
                + json.dumps({"type": "thread.started", "thread_id": "test"})
                + "\n",
                encoding="utf-8",
            )
            audit = subject.command_access_audit(
                log,
                work_dir=work,
                verus_bin=root / "tools" / "verus" / "bin" / "verus",
                rust_root=root / "tools" / "rust",
                lynette_bin=root / "tools" / "lynette",
                scratch_root=root,
            )
        self.assertTrue(audit["passed"])
        self.assertEqual(2, audit["diagnostic_line_count"])
        self.assertEqual(0, audit["malformed_event_count"])

    def test_codex_command_freezes_provider_contract(self) -> None:
        command = subject.codex_command(
            Path("/tmp/work"), 4017, "val--task", Path("/bin/true"), "prompt"
        )
        joined = "\n".join(command)
        self.assertIn('model_provider="deepseek_bridge"', joined)
        self.assertIn('wire_api="responses"', joined)
        self.assertIn("request_max_retries=4", joined)
        self.assertIn("stream_max_retries=4", joined)
        self.assertIn('model_reasoning_effort="high"', joined)
        self.assertIn("/tasks/val--task/v1", joined)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--json", command)
        sandbox_index = command.index("-s")
        self.assertEqual("danger-full-access", command[sandbox_index + 1])

    def test_bridge_identity_rejects_stale_healthy_process(self) -> None:
        expected = "new-instance"
        self.assertFalse(
            subject.bridge_identity_matches(
                {"instance_id": "old-instance"},
                {"instance_id": expected},
                expected,
            )
        )
        self.assertFalse(
            subject.bridge_identity_matches(
                {"instance_id": expected},
                {"instance_id": "old-instance"},
                expected,
            )
        )
        self.assertTrue(
            subject.bridge_identity_matches(
                {"instance_id": expected},
                {"instance_id": expected},
                expected,
            )
        )

    def test_actor_confinement_denies_mount_and_namespace_syscalls(self) -> None:
        self.assertIn("mount", actor_isolation.FORBIDDEN_ACTOR_SYSCALLS)
        self.assertIn("umount2", actor_isolation.FORBIDDEN_ACTOR_SYSCALLS)
        self.assertIn("unshare", actor_isolation.FORBIDDEN_ACTOR_SYSCALLS)
        self.assertIn("setns", actor_isolation.FORBIDDEN_ACTOR_SYSCALLS)
        self.assertTrue(actor_isolation.CLONE_NAMESPACE_FLAGS)

    def test_blocked_probe_and_provider_error_do_not_override_proof_success(self) -> None:
        score = subject.score_task_outcome(
            timed_out=False,
            actor_completed=True,
            validation_complete=True,
            safety_passed=True,
            source_unchanged=True,
            input_unchanged=True,
        )
        observations = subject.audit_observations(
            {"violation_count": 1, "malformed_event_count": 0},
            {"failed_request_count": 1},
        )
        self.assertTrue(score["success"])
        self.assertEqual([], score["outcome_failure_reasons"])
        self.assertEqual(
            ["blocked_prohibited_filesystem_probe", "provider_request_failure"],
            observations,
        )

    def test_only_timeout_or_failed_final_verification_are_outcome_failures(self) -> None:
        timeout = subject.score_task_outcome(
            timed_out=True,
            actor_completed=False,
            validation_complete=True,
            safety_passed=True,
            source_unchanged=True,
            input_unchanged=True,
        )
        failed = subject.score_task_outcome(
            timed_out=False,
            actor_completed=True,
            validation_complete=False,
            safety_passed=True,
            source_unchanged=True,
            input_unchanged=True,
        )
        self.assertEqual(["timeout"], timeout["outcome_failure_reasons"])
        self.assertEqual(
            ["final_verification_failed"], failed["outcome_failure_reasons"]
        )
        self.assertFalse(timeout["success"])
        self.assertFalse(failed["success"])

    def test_failed_provider_turn_is_incomplete_not_final_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "events.jsonl"
            log.write_text(
                "2026-08-17T22:23:16Z WARN provider interrupted\n"
                + json.dumps(
                    {
                        "type": "error",
                        "message": "502 Bad Gateway: IncompleteRead",
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "type": "turn.failed",
                        "error": {
                            "message": "502 Bad Gateway: IncompleteRead"
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            terminal = subject.codex_terminal_status(log)
        score = subject.score_task_outcome(
            timed_out=False,
            actor_completed=terminal["completed"],
            validation_complete=False,
            safety_passed=True,
            source_unchanged=True,
            input_unchanged=True,
        )
        self.assertEqual("turn.failed", terminal["event_type"])
        self.assertFalse(terminal["completed"])
        self.assertIn("IncompleteRead", terminal["error_message"])
        self.assertFalse(score["success"])
        self.assertEqual([], score["outcome_failure_reasons"])

    def test_resume_does_not_reuse_explicitly_incomplete_result(self) -> None:
        self.assertFalse(subject.result_is_complete({"task_complete": False}))
        self.assertTrue(subject.result_is_complete({"task_complete": True}))
        self.assertTrue(subject.result_is_complete({"success": False}))

    def test_usage_and_summary_match_gate_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / "bridge_calls.jsonl"
            ledger.write_text(
                json.dumps(
                    {
                        "task_id": "val--a",
                        "attempts": [
                            {
                                "usage": {
                                    "prompt_tokens": 100,
                                    "prompt_cache_hit_tokens": 60,
                                    "prompt_cache_miss_tokens": 40,
                                    "completion_tokens": 20,
                                    "reasoning_tokens": 10,
                                    "total_tokens": 120,
                                },
                                "estimated_cost_usd": 0.01,
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            usage = subject.usage_for_task(ledger, "val--a")
            self.assertEqual(60, usage["primary_uncached_tokens"])
            result = {
                "split_index": 1,
                "task_id": "private-a",
                "success": True,
                "timed_out": False,
                "wall_time_seconds": 5.0,
                "usage": usage,
                "safety_audit": {"complete": True, "passed": True},
                "contract_violations": [],
                "fidelity_audit_complete": True,
            }
            summary = subject.summarize([result], 1)
            parsed = CommandAggregateEvaluator.parse_summary(summary)
            self.assertEqual(1, parsed.success_count)
            self.assertEqual(60, parsed.primary_uncached_tokens)
            self.assertEqual(120, parsed.total_tokens)
            self.assertEqual(10, parsed.reasoning_tokens)
            self.assertTrue(parsed.coverage_complete)
            self.assertTrue(parsed.fidelity_complete)
            self.assertTrue(parsed.safety_complete)

    def test_added_bypass_audit_ignores_existing_policy_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = root / "before.rs"
            after = root / "after.rs"
            original = "#[verifier::external_body]\nfn approved_external() {}\n"
            before.write_text(original, encoding="utf-8")
            after.write_text(original + "proof fn helper() {}\n", encoding="utf-8")
            self.assertTrue(subject.added_bypass_audit(before, after)["passed"])
            after.write_text(original + "proof fn helper() { assume(true); }\n")
            audit = subject.added_bypass_audit(before, after)
            self.assertFalse(audit["passed"])
            self.assertIn("assume", audit["forbidden_additions"])

    def test_output_must_be_strict_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subject.assert_strict_child(root / "actor", root)
            with self.assertRaises(ValueError):
                subject.assert_strict_child(root, root)
            with self.assertRaises(ValueError):
                subject.assert_strict_child(root.parent / "elsewhere", root)

    def test_paid_execution_requires_shared_budget_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "requires --budget-state-path"):
                subject.main(
                    [
                        "--execute",
                        "--output-root",
                        str(root / "actor"),
                        "--run-root",
                        str(root),
                    ]
                )

    def test_task_number_selection_is_exact(self) -> None:
        rows = [{"n": number} for number in range(1, 21)]
        self.assertEqual([{"n": 2}, {"n": 5}], subject.select_tasks(rows, [2, 5]))
        with self.assertRaises(ValueError):
            subject.select_tasks(rows, [1, 1])
        with self.assertRaises(ValueError):
            subject.select_tasks(rows, [21])

    def test_run_codex_cleans_separate_session_on_supervisor_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            process = mock.Mock()
            process.wait.side_effect = SystemExit(143)
            process.poll.return_value = None
            with (
                mock.patch.object(subject.subprocess, "Popen", return_value=process),
                mock.patch.object(subject, "stop_process_group") as stop,
                self.assertRaises(SystemExit),
            ):
                subject.run_codex(
                    ["/bin/true"], root, {}, root / "actor.jsonl", 10
                )
            stop.assert_called_once_with(process)

    def test_per_task_results_have_distinct_durable_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            rows = [
                {"normalized_task_id": "task-a", "task_id": "private-a"},
                {"normalized_task_id": "task-b", "task_id": "private-b"},
            ]
            paths = [subject.task_result_path(output, row) for row in rows]
            self.assertNotEqual(paths[0], paths[1])
            for row, path in zip(rows, paths, strict=True):
                subject.write_json(path, {"task_id": row["task_id"]})
            self.assertEqual("private-a", json.loads(paths[0].read_text())["task_id"])
            self.assertEqual("private-b", json.loads(paths[1].read_text())["task_id"])


if __name__ == "__main__":
    unittest.main()
