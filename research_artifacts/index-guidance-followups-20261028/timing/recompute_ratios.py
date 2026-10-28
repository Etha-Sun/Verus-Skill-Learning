"""Recompute the published per-task ratios without logs, model calls or verifiers."""
from pathlib import Path
import csv
import json
import math
import statistics

ROOT = Path(__file__).resolve().parent
METRICS = ("wall_seconds", "final_verus_seconds", "cumulative_command_proxy_seconds")

def compute():
    with (ROOT / "cells.csv").open(newline="") as f:
        cells = list(csv.DictReader(f))
    summary = json.loads((ROOT / "summary.json").read_text())
    result = {}
    assert len(cells) == 40
    assert len({(r["batch"], r["task"], r["arm"], r["repeat"]) for r in cells}) == 40
    for batch in summary["batches"]:
        rows = [r for r in cells if r["batch"] == batch["name"]]
        tasks = sorted({r["task"] for r in rows})
        assert len(tasks) == 4 and len(rows) == 8 * batch["repeats"]
        ratios = {}
        for metric in METRICS:
            per_task = []
            for task in tasks:
                means = []
                for arm in (batch["control"], batch["modified"]):
                    values = [float(r[metric]) for r in rows if r["task"] == task and r["arm"] == arm]
                    assert len(values) == batch["repeats"] and all(math.isfinite(v) and v > 0 for v in values)
                    means.append(statistics.mean(values))
                per_task.append(means[1] / means[0])
            ratios[metric] = statistics.mean(per_task)
            assert math.isclose(ratios[metric], batch["mean_per_task_ratios"][metric], rel_tol=1e-12)
        for arm in (batch["control"], batch["modified"]):
            assert sum(r["dual_pass"] == "True" for r in rows if r["arm"] == arm) == batch["summary"][arm]["passes"]
        result[batch["name"]] = ratios
    return result

if __name__ == "__main__":
    print(json.dumps(compute(), indent=2))
