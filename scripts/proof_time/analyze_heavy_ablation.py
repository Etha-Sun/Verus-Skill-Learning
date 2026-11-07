#!/usr/bin/env python3
"""Summarize heavy-task single-factor ablations (relative to each task's baseline)."""
from __future__ import annotations

import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

rows = [json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines()]
base = {r["task_id"]: r for r in rows if r["kind"] == "baseline" and r["success"]}
by = defaultdict(list)
per_task_best = defaultdict(lambda: 1.0)
for r in rows:
    if r["kind"] == "baseline" or r["task_id"] not in base:
        continue
    b = base[r["task_id"]]
    ratio = r["rlimit"] / b["rlimit"] if r["success"] and b["rlimit"] else None
    r["ratio"] = ratio
    by[r["kind"]].append(r)
    if ratio is not None:
        per_task_best[r["task_id"]] = min(per_task_best[r["task_id"]], ratio)

print(f"tasks with verified baseline: {len(base)} / {len({r['task_id'] for r in rows})}")
print(f"{'kind':20} {'n':>5} {'still verifies':>15} {'median ratio':>13} {'<0.9':>5} {'<0.7':>5} {'>1.1':>5}  min")
for k, rs in sorted(by.items()):
    ok = [r["ratio"] for r in rs if r["ratio"] is not None]
    if not ok:
        print(f"{k:20} {len(rs):5} {0:15}")
        continue
    print(f"{k:20} {len(rs):5} {len(ok):15} {st.median(ok):13.3f} {sum(x < 0.9 for x in ok):5} "
          f"{sum(x < 0.7 for x in ok):5} {sum(x > 1.1 for x in ok):5}  {min(ok):.3f}")
best = sorted(per_task_best.values())
print("best single-factor ratio per task: median", round(st.median(best), 3),
      "| tasks with some single change <0.9:", sum(x < 0.9 for x in best), "<0.7:", sum(x < 0.7 for x in best))
print("\nlargest single-factor savings:")
allr = sorted([r for rs in by.values() for r in rs if r["ratio"] is not None], key=lambda r: r["ratio"])
for r in allr[:15]:
    print(f"  {r['ratio']:.3f} {r['kind']:18} {r['task_id'][:60]}  | {r['stmt'][:110]!r}")
