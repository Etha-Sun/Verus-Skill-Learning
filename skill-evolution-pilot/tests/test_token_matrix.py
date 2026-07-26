from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_evolution_pilot.token_matrix import summarize_token_matrix


class TokenMatrixTest(unittest.TestCase):
    def test_matrix_ranks_success_before_short_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = root / "tasks.jsonl"
            jobs = root / "jobs.jsonl"
            task_rows = [
                {
                    "task_id": f"t{i}",
                    "final_case": f"c{i}",
                    "h0_run_dir": f"h0-{i}",
                }
                for i in range(4)
            ]
            tasks.write_text(
                "".join(json.dumps(row) + "\n" for row in task_rows),
                encoding="utf-8",
            )
            job_rows = [
                {
                    "task_id": f"t{i}",
                    "skill_id": skill,
                    "skill_profile": skill,
                    "out_dir": f"{skill}-{i}",
                }
                for skill in ("aggressive", "conservative", "structural")
                for i in range(4)
            ]
            jobs.write_text(
                "".join(json.dumps(row) + "\n" for row in job_rows),
                encoding="utf-8",
            )

            def ledger(path: Path):
                failed = path.name.startswith("structural")
                return {
                    "run_id": path.name,
                    "f3": True,
                    "success": not failed,
                    "primary_uncached_tokens": 1 if failed else 10,
                    "provider_total_tokens": 20,
                }

            with patch(
                "skill_evolution_pilot.token_matrix.build_run_ledger",
                side_effect=ledger,
            ):
                result = summarize_token_matrix(
                    frozen_tasks_path=tasks,
                    skill_jobs_path=jobs,
                )
            self.assertNotEqual(result["best_skill_id"], "structural")
            structural = next(
                row
                for row in result["skill_aggregates"]
                if row["skill_id"] == "structural"
            )
            self.assertTrue(structural["expected_tokens_to_success_is_infinite"])


if __name__ == "__main__":
    unittest.main()
