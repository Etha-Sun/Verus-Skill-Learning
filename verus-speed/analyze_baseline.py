#!/usr/bin/env python3
"""Summarize baseline.py output: per-phase time shares and config ratios.

  python3 verus-speed/analyze_baseline.py RUN/baseline_default.jsonl
  python3 verus-speed/analyze_baseline.py RUN/failing_configs.jsonl --failing
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import statistics as st
from pathlib import Path

PHASES = ["rust_init_ms", "rust_lifetime_ms", "rust_compile_ms", "vir_import_ms",
          "vir_other_ms", "air_ms", "smt_init_ms", "smt_run_ms"]


def geomean(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def best_runs(rows, want_success):
    """Per (task, config): the run with the smallest total (least load noise)."""
    by = collections.defaultdict(list)
    for r in rows:
        if r.get("total_ms") is not None and bool(r.get("success")) == want_success:
            by[(r["task_id"], r["config"])].append(r)
    return {k: min(v, key=lambda r: r["total_ms"]) for k, v in by.items()}


def phase_table(best, config):
    runs = [r for (_, c), r in best.items() if c == config]
    total = sum(r["total_ms"] for r in runs)
    print(f"config={config} tasks={len(runs)} sum_total={total / 1000:.0f}s "
          f"median_total={st.median(r['total_ms'] for r in runs):.0f}ms")
    print(f"{'phase':18s}{'median_ms':>10s}{'p90_ms':>9s}{'sum_s':>9s}{'share':>8s}")
    for k in PHASES:
        v = sorted(r.get(k) or 0 for r in runs)
        print(f"{k:18s}{st.median(v):10.0f}{v[int(.9 * len(v))]:9.0f}{sum(v) / 1000:9.1f}{100 * sum(v) / total:7.1f}%")
    for name, lo, hi in (("light (smt<0.2s)", 0, 200), ("medium", 200, 2000), ("heavy (smt>=2s)", 2000, 1e12)):
        g = [r for r in runs if lo <= (r.get("smt_run_ms") or 0) < hi]
        if g:
            t = sum(r["total_ms"] for r in g)
            print(f"{name:18s} tasks={len(g):4d} ({100 * len(g) / len(runs):.0f}%) time={t / 1000:7.0f}s "
                  f"({100 * t / total:.0f}% of all) smt_share={sum(r.get('smt_run_ms') or 0 for r in g) / t:.2f}")


def config_ratios(best, base="default"):
    configs = sorted({c for _, c in best} - {base})
    for c in configs:
        pairs = [(best[(t, base)]["total_ms"], best[(t, c)]["total_ms"])
                 for (t, cc) in best if cc == c and (t, base) in best]
        if pairs:
            a, b = sum(p[0] for p in pairs), sum(p[1] for p in pairs)
            print(f"{c:14s} n={len(pairs):4d} geomean={geomean([(y + 1) / (x + 1) for x, y in pairs]):.3f} "
                  f"sum {a / 1000:.0f}s -> {b / 1000:.0f}s ({b / a:.3f})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--failing", action="store_true", help="analyze runs that did not verify")
    a = ap.parse_args()
    rows = [json.loads(l) for l in a.path.read_text().splitlines() if l.strip()]
    print("rows", len(rows), "timed_out", sum(bool(r.get("timed_out")) for r in rows),
          "verified", sum(bool(r.get("success")) for r in rows))
    best = best_runs(rows, want_success=not a.failing)
    for c in sorted({c for _, c in best}):
        if c == "default" or len({c for _, c in best}) == 1:
            phase_table(best, c)
    config_ratios(best)


if __name__ == "__main__":
    main()
