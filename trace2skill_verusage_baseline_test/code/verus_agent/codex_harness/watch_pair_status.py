#!/usr/bin/env python3
"""Print a compact status table for one or more Codex batch output roots."""

import json
import sys
from pathlib import Path


def main() -> int:
    for raw in sys.argv[1:]:
        root = Path(raw)
        name = "semantic-v4" if "semantic_v4" in root.name else "no-skill"
        progress = root / "progress.json"
        manifest = root / "experiment_manifest.json"
        cap = "?"
        if manifest.is_file():
            cap = json.loads(manifest.read_text()).get("timeout_seconds_per_task", "?")
        tasks = []
        status = "running"
        if progress.is_file():
            data = json.loads(progress.read_text())
            tasks = data.get("tasks", [])
            status = data.get("status", "running")
        print(f"{name}: {len(tasks)}/15 completed")
        for task in tasks:
            mark = "✅" if task.get("success") else ("⏱" if task.get("timed_out") else "❌")
            print(f"  {task['task_index']:02d} {mark} {task['task_id']}")
        if status != "completed":
            logs = sorted((root / "logs").glob("*.jsonl"))
            current = logs[-1].stem.split("_", 1)[1] if logs else "starting"
            print(f"  {len(tasks) + 1:02d} ▶ {current} (running; {cap}s cap)")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
