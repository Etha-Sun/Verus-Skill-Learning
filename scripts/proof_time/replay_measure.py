#!/usr/bin/env python3
"""Exact (SMT-replay) cost for every proof in candidates.jsonl files, 2 seeds."""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
from pathlib import Path

from smt_replay import cost


def job(arg):
    rec, kind, seed = arg
    r = cost(Path(rec["candidate_path"]).read_text(), seed=seed)
    return {"candidate_sha256": rec["candidate_sha256"], "task_id": rec["task_id"], "kind": kind,
            "seed": seed, "success": r.get("success"), "timed_out": r.get("timed_out", False),
            "rlimit": r.get("rlimit"), "qi": r.get("qi"), "verus_wall": r.get("verus_wall"),
            "replay_wall": r.get("replay_wall"), "functions": r.get("functions")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="kind=path/to/candidates.jsonl")
    ap.add_argument("--tasks", type=Path, help="restrict to task ids listed (one per line)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    keep = set(a.tasks.read_text().split()) if a.tasks else None
    jobs = []
    for spec in a.inputs:
        kind, path = spec.split("=", 1)
        for l in Path(path).read_text().splitlines():
            r = json.loads(l)
            if keep is None or r["task_id"] in keep:
                jobs += [(r, kind, s) for s in range(a.seeds)]
    print(len(jobs), "jobs", flush=True)
    with a.out.open("w") as fh, cf.ThreadPoolExecutor(a.workers) as pool:
        for i, rec in enumerate(pool.map(job, jobs), 1):
            fh.write(json.dumps(rec) + "\n")
            if i % 100 == 0:
                print(i, flush=True)


if __name__ == "__main__":
    main()
