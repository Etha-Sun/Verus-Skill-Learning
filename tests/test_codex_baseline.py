import json
import tempfile
import unittest
from pathlib import Path

from verus_self_evolve.codex_baseline import (
    audit_batch,
    build_codex_command,
    prepare_jobs,
    run_job,
)
from verus_self_evolve.handsoff_m0 import sha256_file


class CodexBaselineTest(unittest.TestCase):
    @staticmethod
    def _executable(path: Path, content: str) -> Path:
        path.write_text(content)
        path.chmod(0o755)
        return path

    def _fixture(self, root: Path):
        corpus = root / "corpus"
        tasks = []
        cases = []
        for index, final_case in enumerate(
            ("stable_pass", "stable_closest_failure", "unstable")
        ):
            calibration_id = f"cal-{index}"
            source = corpus / "verified-anvil" / "unverified" / f"task_{index}.rs"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(f"fn task_{index}() {{}}\n")
            tasks.append(
                {
                    "calibration_id": calibration_id,
                    "task_id": f"task_{index}",
                    "directory_group": "verified-anvil",
                    "canonical_source_path": str(source.relative_to(corpus)),
                    "canonical_source_sha256": sha256_file(source),
                }
            )
            cases.append(
                {
                    "final_case": final_case,
                    "calibration_id": calibration_id,
                }
            )
        tasks_path = root / "tasks.jsonl"
        tasks_path.write_text("".join(json.dumps(row) + "\n" for row in tasks))
        frozen_path = root / "frozen.json"
        frozen_path.write_text(
            json.dumps(
                {
                    "status": "FROZEN",
                    "selection_evidence": "h0_only",
                    "cases": cases,
                }
            )
        )
        tools = root / "tools"
        tools.mkdir()
        codex = self._executable(
            tools / "codex",
            """#!/usr/bin/env python3
import json
import pathlib
import sys
if "--version" in sys.argv:
    print("codex-cli test")
    raise SystemExit(0)
last = pathlib.Path(sys.argv[sys.argv.index("--output-last-message") + 1])
last.write_text("done")
print(json.dumps({"type": "thread.started", "thread_id": "test"}))
print(json.dumps({"type": "item.completed", "item": {"id": "c1", "type": "command_execution", "command": "verus candidate.rs", "status": "completed", "exit_code": 0}}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3}}))
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
        return corpus, tasks_path, frozen_path, codex, verus, lynette

    def test_command_pins_json_ephemeral_workspace_exploration(self):
        command = build_codex_command(
            Path("/tools/codex"),
            Path("/run/workspace"),
            Path("/run/last.txt"),
            "gpt-5.6-sol",
            "high",
        )
        self.assertIn("--json", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("workspace-write", command)
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertEqual(command[-1], "-")

    def test_three_task_contract_and_detailed_run_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus, tasks, frozen, codex, verus, lynette = self._fixture(root)
            experiment = root / "run-root" / "experiment"
            contract = prepare_jobs(
                frozen,
                tasks,
                corpus,
                experiment,
                codex_bin=codex,
                verus_bin=verus,
                lynette_bin=lynette,
                timeout_seconds=30,
            )
            self.assertEqual(contract["job_count"], 3)
            self.assertFalse(contract["old_trajectory_visible"])
            jobs_path = experiment / "codex_baseline_jobs.jsonl"
            jobs = [json.loads(line) for line in jobs_path.read_text().splitlines()]
            result = run_job(
                jobs_path,
                experiment / "codex_baseline_contract.json",
                experiment / "runs",
                jobs[0]["job_id"],
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["events"]["json_parse_errors"], 0)
            self.assertEqual(result["events"]["command_count"], 1)
            self.assertEqual(
                result["events"]["final_usage"],
                {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3},
            )
            run_dir = experiment / jobs[0]["relative_run_path"]
            for name in (
                "codex_events.jsonl",
                "codex_stderr.log",
                "last_message.txt",
                "run_manifest.json",
                "event_summary.json",
                "candidate.diff",
                "verus.log",
                "lynette.log",
                "validation.json",
                "workspace_inventory.json",
                "result.json",
            ):
                self.assertTrue((run_dir / name).is_file(), name)
            with self.assertRaisesRegex(ValueError, "must be empty"):
                run_job(
                    jobs_path,
                    experiment / "codex_baseline_contract.json",
                    experiment / "runs",
                    jobs[0]["job_id"],
                )

    def test_batch_audit_recomputes_event_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus, tasks, frozen, codex, verus, lynette = self._fixture(root)
            experiment = root / "run-root" / "experiment"
            prepare_jobs(
                frozen,
                tasks,
                corpus,
                experiment,
                codex_bin=codex,
                verus_bin=verus,
                lynette_bin=lynette,
                timeout_seconds=30,
            )
            jobs_path = experiment / "codex_baseline_jobs.jsonl"
            jobs = [json.loads(line) for line in jobs_path.read_text().splitlines()]
            for job in jobs:
                run_job(
                    jobs_path,
                    experiment / "codex_baseline_contract.json",
                    experiment / "runs",
                    job["job_id"],
                )
            output = experiment / "batch_audit.json"
            audit = audit_batch(
                jobs_path,
                experiment / "codex_baseline_contract.json",
                experiment / "runs",
                output,
            )
            self.assertEqual(audit["job_count"], 3)
            self.assertEqual(audit["pass_count"], 3)
            self.assertTrue(audit["all_json_valid"])
            self.assertEqual(
                [row["unique_command_count"] for row in audit["runs"]],
                [1, 1, 1],
            )
            self.assertTrue(output.is_file())
            with self.assertRaisesRegex(ValueError, "already exists"):
                audit_batch(
                    jobs_path,
                    experiment / "codex_baseline_contract.json",
                    experiment / "runs",
                    output,
                )


if __name__ == "__main__":
    unittest.main()
