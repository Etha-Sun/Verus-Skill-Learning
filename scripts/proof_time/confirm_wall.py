#!/usr/bin/env python3
"""Confirm rlimit savings in real seconds: baseline vs top single-factor variants
of heavy proofs, plain Verus runs (no replay) with 3 Z3 seeds each."""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import statistics as st
from pathlib import Path

from heavy_ablation import variants
from measure_candidates import DEFAULT_VERUS, run_once
from proof_guard import strip_comments


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ablation", type=Path, required=True)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--bench-tasks", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=48)
    a = ap.parse_args()
    rows = [json.loads(l) for l in a.ablation.read_text().splitlines()]
    base = {r["task_id"]: r for r in rows if r["kind"] == "baseline"}
    picks = [r for r in rows if r["kind"] != "baseline" and r["success"]
             and r["rlimit"] / base[r["task_id"]]["rlimit"] < a.threshold]
    bench = {json.loads(l)["task_id"]: json.loads(l) for l in a.bench_tasks.read_text().splitlines()}
    cands = {json.loads(l)["task_id"]: json.loads(l) for l in a.candidates.read_text().splitlines()}
    tmp = a.out.parent / "confirm_wall_files"
    tmp.mkdir(exist_ok=True)
    jobs = []
    for t in sorted({p["task_id"] for p in picks}):
        text = strip_comments(Path(cands[t]["candidate_path"]).read_text())
        vs = {(k, s): v for k, s, v in variants(text, bench[t]["target_function"], 40)}
        f = tmp / f"{t[:80]}__baseline.rs"
        f.write_text(text)
        jobs += [(t, "baseline", "", 1.0, f, s) for s in range(a.seeds)]
        for i, p in enumerate(x for x in picks if x["task_id"] == t):
            f = tmp / f"{t[:80]}__v{i}.rs"
            f.write_text(vs[(p["kind"], p["stmt"])])
            ratio = p["rlimit"] / base[t]["rlimit"]
            jobs += [(t, p["kind"], p["stmt"], ratio, f, s) for s in range(a.seeds)]
    print(len(jobs), "runs", flush=True)

    def run(j):
        t, kind, stmt, ratio, f, seed = j
        r = run_once(DEFAULT_VERUS, f, seed, None, 3600)
        return {"task_id": t, "kind": kind, "stmt": stmt[:200], "rlimit_ratio": ratio, "seed": seed,
                "success": r.get("success"), "wall": r.get("wall_seconds"), "smt_ms": r.get("smt_run_ms")}

    with a.out.open("w") as fh, cf.ThreadPoolExecutor(a.workers) as pool:
        for rec in pool.map(run, jobs):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()


if __name__ == "__main__":
    main()
