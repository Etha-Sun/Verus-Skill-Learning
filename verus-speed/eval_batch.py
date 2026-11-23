#!/usr/bin/env python3
"""Compare batched verification against one-process-per-file verification.

Both arms get the same CPU budget: --cores concurrent Verus processes, each
with --num-threads 1. Singles hold one file per process, batches up to
--batch-size files.
Reports wall time and whether every per-file verdict agrees.
"""
from __future__ import annotations

import argparse
import json
import resource
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import batch_verify as bv


def child_cpu() -> float:
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime + r.ru_stime


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cores", type=int, default=12)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    tasks = [json.loads(l) for p in args.tasks for l in p.read_text().splitlines() if l.strip()]
    files = [Path(t["candidate_path"]) for t in tasks]

    start, cpu0 = time.perf_counter(), child_cpu()
    with ThreadPoolExecutor(args.cores) as pool:
        single = list(pool.map(lambda f: bv.run_single(bv.DEFAULT_VERUS, f, ["--num-threads", "1"], args.timeout), files))
    t_single, cpu_single = time.perf_counter() - start, child_cpu() - cpu0

    # Same budget: --cores batch processes, one solver thread each.
    start, cpu0 = time.perf_counter(), child_cpu()
    plan = bv.plan_batches(files, args.batch_size)
    batch: list = [None] * len(files)

    def run(idx):
        return bv._verify_group([files[i] for i in idx], bv.DEFAULT_VERUS, len(idx),
                                ["--num-threads", "1"], args.timeout)

    with ThreadPoolExecutor(args.cores) as pool:
        for idx, res in zip(plan, pool.map(run, plan)):
            for i, r in zip(idx, res):
                batch[i] = r
    t_batch, cpu_batch = time.perf_counter() - start, child_cpu() - cpu0

    rows = [{"task_id": t["task_id"], "path": t["candidate_path"], "single": s, "batch": b}
            for t, s, b in zip(tasks, single, batch)]
    summary = {
        "files": len(files), "cores": args.cores, "batch_size": args.batch_size,
        "single_wall_s": round(t_single, 1), "batch_wall_s": round(t_batch, 1),
        "speedup": round(t_single / t_batch, 2),
        "single_cpu_s": round(cpu_single, 1), "batch_cpu_s": round(cpu_batch, 1),
        "cpu_ratio": round(cpu_batch / cpu_single, 3),
        "single_ok": sum(s["success"] for s in single), "batch_ok": sum(b["success"] for b in batch),
        "verdict_mismatch": sum(s["success"] != b["success"] for s, b in zip(single, batch)),
        "ran_in_batch": sum(b["mode"] == "batch" for b in batch),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
