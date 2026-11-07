#!/usr/bin/env python3
"""Compare Z3 cost of the target function: human ground truth vs DeepSeek proofs.

Only the benchmark's target function (plus helper lemmas the proof itself
introduces, for LLM proofs) is compared, because ground-truth files also
verify context lemmas that the task files declare as external_body.
Also summarizes the whole VeruSAGE-Bench ground-truth timing distribution.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

from proof_guard import items, strip_comments


def last(name: str) -> str:
    return name.split("::")[-1]


def load_meas(path: Path):
    m = defaultdict(list)
    for l in path.read_text().splitlines():
        r = json.loads(l)
        if r.get("success"):
            m[r["candidate_sha256"]].append(r)
    return m


def target_cost(runs, fn_names: set[str]) -> float:
    vals = []
    for r in runs:
        vals.append(sum(f["rlimit"] or 0 for f in r["functions"] if last(f["function"]) in fn_names))
    return st.median(vals)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, required=True)
    ap.add_argument("--bench-tasks", type=Path, required=True)
    args = ap.parse_args()
    tasks = {json.loads(l)["task_id"]: json.loads(l) for l in args.bench_tasks.read_text().splitlines()}
    gt_c = [json.loads(l) for l in (args.study / "human-gt/candidates.jsonl").read_text().splitlines()]
    gt_m = load_meas(args.study / "human-gt/measurements.jsonl")
    llm_c = [json.loads(l) for l in (args.study / "candidates.jsonl").read_text().splitlines()]
    llm_m = load_meas(args.study / "measurements.jsonl")

    # 1. ground-truth distribution per project
    proj = defaultdict(list)
    for c in gt_c:
        runs = gt_m.get(c["candidate_sha256"])
        if not runs:
            continue
        r = runs[0]
        tgt = tasks[c["task_id"]]["target_function"]
        tcost = st.median(sum(f["micros"] or 0 for f in x["functions"] if last(f["function"]) == tgt) for x in runs) / 1e3
        proj[c["task_id"].split("__")[0]].append({
            "wall": st.median(x["wall_seconds"] for x in runs),
            "smt_ms": st.median(x["smt_run_ms"] for x in runs),
            "target_smt_ms": tcost,
            "rlimit": st.median(x["rlimit_total"] for x in runs)})
    dist = {}
    for p, xs in sorted(proj.items()):
        dist[p] = {"n": len(xs),
                   "wall_median_s": round(st.median(x["wall"] for x in xs), 2),
                   "wall_max_s": round(max(x["wall"] for x in xs), 1),
                   "smt_ms_median": st.median(x["smt_ms"] for x in xs),
                   "smt_ms_max": max(x["smt_ms"] for x in xs),
                   "smt_share_of_wall_median": round(st.median(x["smt_ms"] / 1e3 / x["wall"] for x in xs), 3),
                   "target_smt_ms_median": st.median(x["target_smt_ms"] for x in xs),
                   "target_smt_ms_max": max(x["target_smt_ms"] for x in xs)}
    all_x = [x for xs in proj.values() for x in xs]
    dist["ALL"] = {"n": len(all_x), "wall_median_s": round(st.median(x["wall"] for x in all_x), 2),
                   "frac_wall_over_10s": round(sum(x["wall"] > 10 for x in all_x) / len(all_x), 3),
                   "frac_smt_over_1s": round(sum(x["smt_ms"] > 1000 for x in all_x) / len(all_x), 3),
                   "smt_share_of_wall_median": round(st.median(x["smt_ms"] / 1e3 / x["wall"] for x in all_x), 3)}
    missing = len(gt_c) - len(all_x)

    # 2. human vs LLM on the target function (+ LLM-introduced helper lemmas)
    by_task = defaultdict(list)
    for c in llm_c:
        if c["candidate_sha256"] in llm_m:
            by_task[c["task_id"]].append(c)
    gt_by_task = {c["task_id"]: c for c in gt_c}
    rows = []
    for t, cs in sorted(by_task.items()):
        gt = gt_by_task.get(t)
        if not gt or gt["candidate_sha256"] not in gt_m:
            continue
        tgt = tasks[t]["target_function"]
        h = target_cost(gt_m[gt["candidate_sha256"]], {tgt})
        src_fns = {it[0] for it in items(strip_comments(Path(cs[0]["source_path"]).read_text()))}
        llm_costs = []
        for c in cs:
            new_fns = {it[0] for it in items(strip_comments(Path(c["candidate_path"]).read_text()))} - src_fns
            llm_costs.append(target_cost(llm_m[c["candidate_sha256"]], {tgt} | new_fns))
        if h <= 0:
            continue
        rows.append({"task_id": t, "human": h, "llm_median": st.median(llm_costs),
                     "llm_min": min(llm_costs), "llm_max": max(llm_costs), "n_llm": len(llm_costs)})
    ratios_med = [r["llm_median"] / r["human"] for r in rows]
    ratios_min = [r["llm_min"] / r["human"] for r in rows]
    geo = lambda xs: st.geometric_mean([max(x, 1e-6) for x in xs])
    cmp = {"tasks": len(rows),
           "geomean_llm_median_over_human": round(geo(ratios_med), 3),
           "geomean_llm_best_over_human": round(geo(ratios_min), 3),
           "frac_tasks_llm_median_slower": round(sum(x > 1.05 for x in ratios_med) / len(rows), 3),
           "frac_tasks_llm_median_faster": round(sum(x < 0.95 for x in ratios_med) / len(rows), 3),
           "frac_tasks_best_llm_beats_human": round(sum(x < 0.95 for x in ratios_min) / len(rows), 3),
           "rows": sorted(rows, key=lambda r: -r["llm_median"] / r["human"])}
    out = {"ground_truth_distribution": dist, "gt_unmeasured": missing, "human_vs_llm": cmp}
    (args.study / "human_vs_llm.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "human_vs_llm"}, indent=1))
    print(json.dumps({k: v for k, v in cmp.items() if k != "rows"}, indent=1))
    for r in cmp["rows"][:8] + cmp["rows"][-4:]:
        print(f"{r['llm_median']/r['human']:8.2f}x  human={r['human']:>9.0f} llm_med={r['llm_median']:>9.0f} llm_min={r['llm_min']:>9.0f} n={r['n_llm']} {r['task_id'][:80]}")


if __name__ == "__main__":
    main()
