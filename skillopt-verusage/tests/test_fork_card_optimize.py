import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "fork_card_optimize",
    ROOT / "src/skillopt_verusage/fork_card_optimize.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ForkCardOptimizeTests(unittest.TestCase):
    def test_prepares_one_equal_weight_reflection_item_per_task(self):
        with tempfile.TemporaryDirectory() as directory:
            run_root = Path(directory) / "run-root"
            packet = run_root / "packet"
            tasks = []
            for project, count in (("IR", 6), ("AC", 6), ("AL", 7)):
                index = packet / f"tasks/{project.lower()}/OPTIMIZER_HINT_VISIBLE.md"
                index.parent.mkdir(parents=True, exist_ok=True)
                index.write_text(f"# {project}\n")
                tasks.append({
                    "project": project,
                    "task_id": f"{project.lower()}-task",
                    "task_weight": 1,
                    "checkpoint_count": count,
                    "optimizer_index": f"tasks/{project.lower()}/OPTIMIZER_HINT_VISIBLE.md",
                })
            (packet / "manifest.json").write_text(json.dumps({
                "schema_version": "skillopt-fork-packet-v1",
                "optimizer_view": "hint_visible",
                "tasks": tasks,
            }))
            out = packet / "skillopt"
            with mock.patch.dict(os.environ, {"VERUS_SKILL_RUN_ROOT": str(run_root)}):
                results, predictions = m.prepare_reflection_inputs(packet, out)
            self.assertEqual(len(results), 3)
            self.assertEqual(sum(row["task_weight"] for row in results), 3)
            self.assertEqual([row["n_turns"] for row in results], [6, 6, 7])
            for row in results:
                conversation = json.loads((predictions / row["id"] / "conversation.json").read_text())
                self.assertIn("total task weight one", conversation[0]["content"])

    def test_card_audit_requires_triggered_card_shape(self):
        valid = {
            "edits": [{"content": "**Trigger:** x\n**Action:** y\n**Validate:** z\n**Avoid when:** q"}]
        }
        report = [{"status": "applied_append"}]
        self.assertEqual(m._card_audit("seed", valid, report), [])
        invalid = {"edits": [{"content": "generic advice"}]}
        self.assertIn("selected cards omit Trigger:", m._card_audit("seed", invalid, report))


if __name__ == "__main__":
    unittest.main()
