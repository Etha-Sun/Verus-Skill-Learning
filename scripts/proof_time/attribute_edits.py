#!/usr/bin/env python3
"""Attribute cost reductions to individual edits (hunks).

For every (before, after) pair where `after` verified and was cheaper, split
the line diff into hunks and apply each hunk *alone* to `before`; verify and
measure exact Z3 cost (SMT replay). This separates the edit that actually
saved solver work from incidental ones.

Pairs come from optimizer trajectories (each 'improved' round vs previous
best) and from assert-pruning results (baseline vs pruned).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import difflib
import json
from pathlib import Path

from optimize_proof import verify
from proof_guard import strip_comments


def hunks(a: list[str], b: list[str]):
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    return [(i1, i2, j1, j2) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]


def pairs_from_optimizer(opt_dir: Path, tasks: dict):
    for tdir in sorted(opt_dir.iterdir()):
        traj = tdir / "trajectory.jsonl"
        if not traj.exists() or tdir.name not in tasks:
            continue
        rows = [json.loads(l) for l in traj.read_text().splitlines()]
        prev = Path(tasks[tdir.name]["candidate_path"]).read_text()
        prev_cost = rows[0]["rlimit"]
        for r in rows[1:]:
            if r.get("outcome") == "improved":
                yield {"source": "optimizer", "task_id": tdir.name, "round": r["round"],
                       "before": prev, "after": r["candidate"], "before_cost": prev_cost, "after_cost": r["rlimit"]}
                prev, prev_cost = r["candidate"], r["rlimit"]


def pairs_from_prune(prune_dir: Path, tasks: dict):
    for tdir in sorted(prune_dir.iterdir()):
        f = tdir / "final.json"
        if not f.exists() or tdir.name not in tasks:
            continue
        fin = json.loads(f.read_text())
        if fin.get("removed", 0) == 0:
            continue
        before = strip_comments(Path(tasks[tdir.name]["candidate_path"]).read_text())
        yield {"source": "prune", "task_id": tdir.name, "round": 0, "before": before,
               "after": (tdir / "best.rs").read_text(), "before_cost": fin["baseline_rlimit"],
               "after_cost": fin["best_rlimit"]}


def attribute(pair: dict) -> dict:
    a, b = pair["before"].splitlines(keepends=True), pair["after"].splitlines(keepends=True)
    hs = hunks(a, b)
    base = verify(pair["before"])
    out = {k: pair[k] for k in ("source", "task_id", "round", "before_cost", "after_cost")}
    out["before_cost_remeasured"] = base.get("rlimit")
    out["hunks"] = []
    for (i1, i2, j1, j2) in hs:
        cand = "".join(a[:i1] + b[j1:j2] + a[i2:])
        r = verify(cand)
        out["hunks"].append({"removed": "".join(a[i1:i2])[:1500], "added": "".join(b[j1:j2])[:1500],
                             "success": r["success"], "cost": r.get("rlimit"), "qi": r.get("qi"),
                             "ratio": (r["rlimit"] / base["rlimit"]) if r["success"] and base.get("rlimit") else None})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    S = a.study
    tasks = {}
    for split in ("train", "val"):
        for l in (S / f"opt_tasks_{split}.jsonl").read_text().splitlines():
            r = json.loads(l)
            tasks[r["task_id"]] = r
    pairs = list(pairs_from_optimizer(S / "opt_train_nocard", tasks)) + list(pairs_from_prune(S / "prune_val", tasks))
    print(len(pairs), "pairs", sum(len(hunks(p["before"].splitlines(True), p["after"].splitlines(True))) for p in pairs), "hunks", flush=True)
    with a.out.open("w") as fh, cf.ThreadPoolExecutor(a.workers) as pool:
        for rec in pool.map(attribute, pairs):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()


if __name__ == "__main__":
    main()
