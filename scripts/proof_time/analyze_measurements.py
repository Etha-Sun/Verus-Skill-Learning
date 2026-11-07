#!/usr/bin/env python3
"""Summarize repeated proof-time measurements of verified candidates.

Reads candidates.jsonl and measurements.jsonl from --out-dir and writes
summary.json plus per_candidate.csv. Reports:
  * measurement noise: coefficient of variation of wall/SMT time vs rlimit
    across Z3 seeds for the same proof;
  * within-task spread: how much proof time differs between distinct verified
    proofs of the same task (max/min of per-candidate medians);
  * correlation (Spearman) between static proof-feature deltas and rlimit,
    computed within task (ranks inside each task) to remove task difficulty.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics as st
from collections import defaultdict
from pathlib import Path


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2
        i = j + 1
    return r


def pearson(a, b):
    if len(a) < 3:
        return None
    ma, mb = st.mean(a), st.mean(b)
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va == 0 or vb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (va * vb) ** 0.5


def cv(xs):
    return st.pstdev(xs) / st.mean(xs) if len(xs) > 1 and st.mean(xs) > 0 else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    cands = {json.loads(l)["candidate_sha256"]: json.loads(l)
             for l in (args.out_dir / "candidates.jsonl").read_text().splitlines()}
    meas = defaultdict(list)
    for l in (args.out_dir / "measurements.jsonl").read_text().splitlines():
        r = json.loads(l)
        if r.get("success"):
            meas[r["candidate_sha256"]].append(r)

    per = []
    for sha, rs in meas.items():
        c = cands[sha]
        walls = [r["wall_seconds"] for r in rs]
        smts = [r["smt_run_ms"] for r in rs]
        rls = [r["rlimit_total"] for r in rs]
        # dominant function by median rlimit
        fn = defaultdict(list)
        for r in rs:
            for f in r["functions"]:
                fn[f["function"]].append(f["rlimit"] or 0)
        top = max(fn.items(), key=lambda kv: st.median(kv[1])) if fn else (None, [0])
        per.append({
            "candidate_sha256": sha, "task_id": c["task_id"], "arms": ";".join(sorted(set(c["arms"]))),
            "n": len(rs), "wall_median": st.median(walls), "wall_cv": cv(walls),
            "smt_ms_median": st.median(smts), "smt_cv": cv(smts),
            "rlimit_median": st.median(rls), "rlimit_cv": cv(rls),
            "top_function": top[0], "top_function_rlimit_share":
                st.median(top[1]) / st.median(rls) if st.median(rls) else 0,
            **{f"d_{k}": v for k, v in c["features_delta"].items()},
        })

    with (args.out_dir / "per_candidate.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per[0].keys()))
        w.writeheader()
        w.writerows(per)

    by_task = defaultdict(list)
    for p in per:
        by_task[p["task_id"]].append(p)

    spread = []
    for t, ps in by_task.items():
        if len(ps) < 2:
            continue
        rl = [p["rlimit_median"] for p in ps]
        sm = [p["smt_ms_median"] for p in ps]
        spread.append({"task_id": t, "n": len(ps),
                       "rlimit_max_over_min": max(rl) / max(min(rl), 1),
                       "smt_max_over_min": max(sm) / max(min(sm), 1),
                       "smt_ms_min": min(sm), "smt_ms_max": max(sm),
                       "wall_min": min(p["wall_median"] for p in ps),
                       "wall_max": max(p["wall_median"] for p in ps)})
    spread.sort(key=lambda s: -s["rlimit_max_over_min"])

    # within-task rank correlation: rank features and rlimit inside each task
    feats = [k for k in per[0] if k.startswith("d_")]
    corr = {}
    for f in feats:
        xs, ys = [], []
        for ps in by_task.values():
            if len(ps) < 3:
                continue
            fx = ranks([p[f] for p in ps])
            fy = ranks([p["rlimit_median"] for p in ps])
            n = len(ps)
            xs += [x - (n - 1) / 2 for x in fx]
            ys += [y - (n - 1) / 2 for y in fy]
        corr[f] = pearson(xs, ys)

    summary = {
        "candidates": len(per), "tasks": len(by_task),
        "tasks_with_multiple_proofs": len(spread),
        "noise_median_cv": {k: st.median(p[k] for p in per)
                            for k in ("wall_cv", "smt_cv", "rlimit_cv")},
        "noise_p90_cv": {k: sorted(p[k] for p in per)[int(0.9 * len(per))]
                         for k in ("wall_cv", "smt_cv", "rlimit_cv")},
        "smt_ms_median_overall": st.median(p["smt_ms_median"] for p in per),
        "wall_median_overall": st.median(p["wall_median"] for p in per),
        "within_task_spread_median": {
            "rlimit_max_over_min": st.median(s["rlimit_max_over_min"] for s in spread),
            "smt_max_over_min": st.median(s["smt_max_over_min"] for s in spread)},
        "top_spread_tasks": spread[:12],
        "within_task_rank_corr_feature_vs_rlimit": dict(
            sorted(corr.items(), key=lambda kv: -(kv[1] or 0))),
    }
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
