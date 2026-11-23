#!/usr/bin/env python3
"""Per-class comparison of cold and warm arms from serve_bench.py outputs.

Classes come from baseline.py's default run (solver time of the human proof):
light (< 0.2 s), medium, heavy (>= 2 s); tasks without a passing baseline run
(the unproved tasks) form the class "unproved".

  python3 verus-speed/analyze_serve.py RUN/serve_bench_c8_wc.json [RUN/serve_bench_c8.json] \
      --baseline RUN/baseline_default.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path


def classes(baseline: Path) -> dict[str, str]:
    best: dict[str, float] = {}
    for line in baseline.read_text().splitlines():
        r = json.loads(line)
        if r.get("success"):
            best[r["task_id"]] = min(best.get(r["task_id"], 1e18), r["smt_run_ms"])
    return {t: "light" if v < 200 else "heavy" if v >= 2000 else "medium" for t, v in best.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--n-proofs", type=int, default=849, help="rows before the unproved tasks")
    a = ap.parse_args()
    cls = classes(a.baseline)
    walls: dict = defaultdict(lambda: defaultdict(list))  # (class, arm) -> task -> [wall]
    for run in a.runs:
        d = json.loads(run.read_text())
        for arm, rows in d["rows"].items():
            for i, r in enumerate(rows):
                # rows follow the --tasks order: the human proofs first, then the
                # unproved task files (which reuse the same task ids)
                unproved = i >= a.n_proofs
                c = "unproved" if unproved else cls.get(r["task_id"], "no_baseline")
                walls[(c, arm)][(i, r["task_id"])].append(r["wall_s"])
    print(f"{'class':10s}{'n':>6s}{'cold med':>10s}{'warm med':>10s}{'cold sum':>10s}{'warm sum':>10s}"
          f"{'sum ratio':>10s}{'paired geo':>11s}")
    for c in ("light", "medium", "heavy", "unproved"):
        cold, warm = walls[(c, "cold")], walls[(c, "warm")]
        both = [t for t in cold if t in warm]
        if not both:
            continue
        cm = {t: st.median(cold[t]) for t in both}
        wm = {t: st.median(warm[t]) for t in both}
        geo = math.exp(st.mean(math.log(wm[t] / cm[t]) for t in both))
        print(f"{c:10s}{len(both):6d}{st.median(cm.values()):10.3f}{st.median(wm.values()):10.3f}"
              f"{sum(cm.values()):10.1f}{sum(wm.values()):10.1f}{sum(wm.values()) / sum(cm.values()):10.3f}"
              f"{geo:11.3f}")


if __name__ == "__main__":
    main()
