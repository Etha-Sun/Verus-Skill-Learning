from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from global_skill_experiment.memories import (
    freeze_memory_set,
    parse_failure_items,
    parse_success_items,
    validate_items,
)


class MemoryTests(unittest.TestCase):
    def test_parse_success(self) -> None:
        text = """# Lean Solution Path
## Overview
Done.
# Success Memory Item 1
## Title
Reveal the trigger
## Description
Expose the quantified term.
## Content
Use an explicit assertion before the final step.
"""
        items = parse_success_items(text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Reveal the trigger")
        self.assertEqual(validate_items("success", items), [])

    def test_parse_failure(self) -> None:
        text = """# Failure Cause Item 1
## Title
Unsound shortcut
## Description
The run used external_body.
## Content
The edit introduced the forbidden annotation.
# Failure Memory Item 1
## Title
Reject trusted-body shortcuts
## Description
Keep proof obligations verifier-visible.
## Content
Do not add external_body to discharge a proof.
"""
        items = parse_failure_items(text)
        self.assertEqual([item["type"] for item in items], ["failure_cause", "failure_memory"])
        self.assertEqual(validate_items("failure", items), [])


    def test_freeze_uses_baseline_error_then_success_contract(self) -> None:
        rows = [
            {"order": 1, "task_id": "success_task", "memory_route": "success", "claude_outcome_raw": "TRUE", "artifacts": {"trajectory": {"sha256": "s"}}},
            {"order": 2, "task_id": "failure_task", "memory_route": "failure", "claude_outcome_raw": "FALSE", "artifacts": {"trajectory": {"sha256": "f"}}},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run_manifest.json").write_text("{}", encoding="utf-8")
            for task_id, source, digest in (("success_task", "success", "s"), ("failure_task", "error", "f")):
                task_root = root / "by_task" / task_id
                task_root.mkdir(parents=True)
                record = {"instance_id": task_id, "source_file": "trajectory.log", "record_source": source, "items": [{"type": "success_memory" if source == "success" else "failure_memory", "number": 1, "title": "t", "description": "d", "content": "c"}], "provenance": {"trajectory_sha256": digest}}
                (task_root / "record.json").write_text(json.dumps(record), encoding="utf-8")
            frozen = freeze_memory_set(rows, root)
            combined = json.loads((root / "combined_records.json").read_text(encoding="utf-8"))
            self.assertEqual([record["record_source"] for record in combined], ["error", "success"])
            self.assertEqual(frozen["record_count"], 2)


if __name__ == "__main__":
    unittest.main()
