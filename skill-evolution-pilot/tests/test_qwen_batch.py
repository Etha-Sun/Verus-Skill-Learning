from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skill_evolution_pilot.qwen_batch import prepare_qwen_jobs
from skill_evolution_pilot.workspace import sha256_file


class QwenBatchTest(unittest.TestCase):
    def test_prepares_h0_and_three_skill_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = root / "tasks.jsonl"
            rows = []
            for index in range(4):
                source = root / f"task_{index}.rs"
                source.write_text(f"task {index}\n", encoding="utf-8")
                rows.append(
                    {
                        "task_id": f"task_{index}",
                        "source": str(source),
                        "source_sha256": sha256_file(source),
                    }
                )
            tasks.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            h0 = prepare_qwen_jobs(
                tasks_path=tasks,
                out_root=root / "h0",
                output_path=root / "h0" / "jobs.jsonl",
            )
            self.assertEqual(len(h0), 4)
            self.assertTrue(all(job["skill_file"] is None for job in h0))

            meta = root / "meta.json"
            meta.write_text(
                json.dumps(
                    {
                        "objective": "small_model_solve_rate",
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
                        ],
                    }
                ),
                encoding="utf-8",
            )
            skill_jobs = prepare_qwen_jobs(
                tasks_path=tasks,
                out_root=root / "skills",
                output_path=root / "skills" / "jobs.jsonl",
                meta_output_path=meta,
            )
            self.assertEqual(len(skill_jobs), 12)
            self.assertEqual(
                {job["condition"] for job in skill_jobs},
                {"aggressive", "conservative", "structural"},
            )


if __name__ == "__main__":
    unittest.main()
