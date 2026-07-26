import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_evolution_pilot.batch_runner import (
    freeze_four_task_set,
    prepare_h0_jobs,
    prepare_skill_jobs,
    run_batch,
)


class BatchRunnerTest(unittest.TestCase):
    def test_freeze_requires_unsolved_fourth_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs = root / "jobs.jsonl"
            with jobs.open("w", encoding="utf-8") as handle:
                for index in range(3):
                    handle.write(
                        json.dumps(
                            {
                                "task_id": f"t{index}",
                                "final_case": f"c{index}",
                                "source": f"/s{index}",
                                "source_sha256": str(index),
                                "out_dir": f"/r{index}",
                            }
                        )
                        + "\n"
                    )
            source = root / "fourth.rs"
            source.write_text("fn fourth() {}\n", encoding="utf-8")
            run = root / "run"
            run.mkdir()
            from skill_evolution_pilot.workspace import sha256_file

            (run / "result.json").write_text(
                json.dumps({"status": "SOLVED", "fidelity": {"f3": True}}),
                encoding="utf-8",
            )
            (run / "run_manifest.json").write_text(
                json.dumps({"source_sha256": sha256_file(source)}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "was solved"):
                freeze_four_task_set(
                    three_h0_jobs_path=jobs,
                    fourth_task_id="fourth",
                    fourth_source=source,
                    fourth_run_dir=run,
                    output_path=root / "frozen.jsonl",
                )

    def test_prepare_skill_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = root / "tasks.jsonl"
            tasks.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "final_case": "stable_pass",
                        "source": "/source.rs",
                        "source_sha256": "a" * 64,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            meta = root / "meta.json"
            meta.write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "skill_id": profile,
                                "profile": profile,
                                "content": f"{profile} guidance",
                            }
                            for profile in (
                                "aggressive",
                                "conservative",
                                "structural",
                            )
                        ]
                    }
                ),
                encoding="utf-8",
            )
            jobs = prepare_skill_jobs(
                task_jobs_path=tasks,
                meta_output_path=meta,
                out_root=root / "matrix",
                output_path=root / "matrix" / "jobs.jsonl",
                iteration="r1",
                task_ids={"task-a"},
            )
            self.assertEqual(len(jobs), 3)
            self.assertEqual(
                {job["skill_profile"] for job in jobs},
                {"aggressive", "conservative", "structural"},
            )
            self.assertTrue(all(Path(job["skill_path"]).is_file() for job in jobs))

    def test_prepare_and_run_three_case_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root / "baseline.jsonl"
            cases = ("stable_pass", "stable_closest_failure", "unstable")
            with baseline.open("w", encoding="utf-8") as handle:
                for index, final_case in enumerate(cases):
                    source = root / f"source-{index}.rs"
                    source.write_text(f"fn task_{index}() {{}}\n")
                    handle.write(
                        json.dumps(
                            {
                                "final_case": final_case,
                                "task_id": f"task-{index}",
                                "source_path": str(source),
                                "source_sha256": f"sha-{index}",
                            }
                        )
                        + "\n"
                    )
            jobs_path = root / "batch" / "jobs.jsonl"
            jobs = prepare_h0_jobs(
                baseline_jobs_path=baseline,
                out_root=root / "runs",
                output_path=jobs_path,
                run_suffix="test",
            )
            self.assertEqual(len(jobs), 3)
            self.assertEqual([row["final_case"] for row in jobs], list(cases))

            def fake_run(**kwargs):
                out_dir = kwargs["out_dir"]
                out_dir.mkdir(parents=True)
                (out_dir / "result.json").write_text("{}")
                return {"status": "SOLVED", "fidelity": {"f3": True}}

            summary_path = root / "batch" / "summary.json"
            with patch(
                "skill_evolution_pilot.batch_runner.run_codex_smoke",
                side_effect=fake_run,
            ):
                summary = run_batch(
                    jobs_path=jobs_path,
                    summary_path=summary_path,
                    codex_bin=Path("/fake/codex"),
                    verus_bin=Path("/fake/verus"),
                    lynette_bin=Path("/fake/lynette"),
                    max_workers=3,
                    timeout_seconds=10,
                )
            self.assertEqual(summary["complete_count"], 3)
            self.assertEqual(summary["f3_count"], 3)
            self.assertEqual(summary["solved_count"], 3)
            self.assertEqual(summary["max_workers"], 3)
            self.assertTrue(summary_path.is_file())


if __name__ == "__main__":
    unittest.main()
