#!/usr/bin/env python3
"""Analyze exact SMT-replay costs: seed stability, within-task spread,
human vs DeepSeek target-function cost, feature correlations, perturbations."""
from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

from analyze_measurements import pearson, ranks
from proof_guard import items, strip_comments


def geo(xs):
    return st.geometric_mean([max(x, 1e-9) for x in xs])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, required=True)
    ap.add_argument("--bench-tasks", type=Path, required=True)
    a = ap.parse_args()
    S = a.study
    tasks = {json.loads(l)["task_id"]: json.loads(l) for l in a.bench_tasks.read_text().splitlines()}
    cands = {}
    for p in (S / "candidates.jsonl", S / "human-gt/candidates.jsonl"):
        for l in p.read_text().splitlines():
            r = json.loads(l)
            cands[r["candidate_sha256"]] = r
    runs = defaultdict(list)
    for l in (S / "replay.jsonl").read_text().splitlines():
        r = json.loads(l)
        if r.get("success"):
            runs[(r["kind"], r["candidate_sha256"])].append(r)

    # seed stability of exact cost
    spreads = [max(x["rlimit"] for x in rs) / max(min(x["rlimit"] for x in rs), 1)
               for rs in runs.values() if len(rs) >= 2]
    out = {"proofs_measured": len(runs),
           "seed_stability": {"median_max_over_min_rlimit_across_2_seeds": round(st.median(spreads), 4),
                              "p90": round(sorted(spreads)[int(0.9 * len(spreads))], 3),
                              "frac_over_1.10": round(sum(s > 1.10 for s in spreads) / len(spreads), 3)}}

    # per-proof target cost (target fn + helper lemmas the proof introduced)
    src_fns = {}
    def target_cost(kind, sha):
        c = cands[sha]
        t = c["task_id"]
        tgt = tasks[t]["target_function"]
        names = {tgt}
        if kind == "llm":
            if t not in src_fns:
                src_fns[t] = {it[0] for it in items(strip_comments(Path(c["source_path"]).read_text()))}
            names |= {it[0] for it in items(strip_comments(Path(c["candidate_path"]).read_text()))} - src_fns[t]
        vals, qis = [], []
        for r in runs[(kind, sha)]:
            fs = {k.split("::")[-1]: v for k, v in r["functions"].items()}
            vals.append(sum(fs[n]["rlimit"] for n in names if n in fs))
            qis.append(sum(fs[n]["qi"] for n in names if n in fs))
        return st.median(vals), st.median(qis)

    per_task = defaultdict(lambda: {"llm": [], "human": None})
    for (kind, sha) in runs:
        t = cands[sha]["task_id"]
        rl, qi = target_cost(kind, sha)
        rec = {"sha": sha, "rlimit": rl, "qi": qi, "total": st.median(x["rlimit"] for x in runs[(kind, sha)])}
        if kind == "llm":
            rec["features"] = cands[sha]["features_delta"]
            per_task[t]["llm"].append(rec)
        else:
            per_task[t]["human"] = rec

    # within-task spread among LLM proofs
    spread = []
    for t, d in per_task.items():
        xs = d["llm"]
        if len(xs) >= 2:
            lo, hi = min(x["rlimit"] for x in xs), max(x["rlimit"] for x in xs)
            spread.append({"task_id": t, "n": len(xs), "max_over_min": hi / max(lo, 1), "min": lo, "max": hi})
    spread.sort(key=lambda s: -s["max_over_min"])
    out["within_task_llm_spread"] = {
        "tasks": len(spread),
        "median_max_over_min": round(st.median(s["max_over_min"] for s in spread), 3),
        "frac_tasks_over_2x": round(sum(s["max_over_min"] > 2 for s in spread) / len(spread), 3),
        "top": spread[:8]}

    # human vs LLM
    rows = []
    for t, d in per_task.items():
        h = d["human"]
        if not h or not d["llm"] or h["rlimit"] <= 0:
            continue
        med = st.median(x["rlimit"] for x in d["llm"])
        best = min(x["rlimit"] for x in d["llm"])
        rows.append({"task_id": t, "human": h["rlimit"], "human_qi": h["qi"], "llm_median": med, "llm_best": best,
                     "llm_median_qi": st.median(x["qi"] for x in d["llm"]), "n_llm": len(d["llm"])})
    out["human_vs_llm"] = {
        "tasks": len(rows),
        "geomean_llm_median_over_human": round(geo([r["llm_median"] / r["human"] for r in rows]), 3),
        "geomean_llm_best_over_human": round(geo([r["llm_best"] / r["human"] for r in rows]), 3),
        "frac_llm_median_slower_1.1x": round(sum(r["llm_median"] > 1.1 * r["human"] for r in rows) / len(rows), 3),
        "frac_llm_median_faster_1.1x": round(sum(r["llm_median"] < r["human"] / 1.1 for r in rows) / len(rows), 3),
        "median_qi_human": st.median(r["human_qi"] for r in rows),
        "median_qi_llm": st.median(r["llm_median_qi"] for r in rows),
        "rows": sorted(rows, key=lambda r: -r["llm_median"] / r["human"])}

    # within-task rank correlation of features with target cost (LLM proofs)
    feats = list(next(iter(d["llm"][0]["features"] for d in per_task.values() if d["llm"])).keys())
    corr = {}
    for f in feats + ["qi"]:
        xs, ys = [], []
        for d in per_task.values():
            ps = d["llm"]
            if len(ps) < 3:
                continue
            fx = ranks([p["qi"] if f == "qi" else p["features"][f] for p in ps])
            fy = ranks([p["rlimit"] for p in ps])
            n = len(ps)
            xs += [x - (n - 1) / 2 for x in fx]
            ys += [y - (n - 1) / 2 for y in fy]
        c = pearson(xs, ys)
        corr[f] = None if c is None else round(c, 3)
    out["within_task_rank_corr_with_target_rlimit"] = dict(sorted(corr.items(), key=lambda kv: -(kv[1] or -9)))

    # perturbations
    pp = S / "perturb.jsonl"
    if pp.exists():
        agg = defaultdict(lambda: {"applicable": 0, "verified": 0, "ratios": [], "qi_ratios": []})
        for l in pp.read_text().splitlines():
            r = json.loads(l)
            if not r.get("base_success"):
                continue
            for name, p in r["perturb"].items():
                g = agg[(r["kind"], name)]
                if not p.get("applicable"):
                    continue
                g["applicable"] += 1
                if p.get("success"):
                    g["verified"] += 1
                    g["ratios"].append(p["rlimit"] / max(r["base_rlimit"], 1))
                    g["qi_ratios"].append((p["qi"] + 1) / (r["base_qi"] + 1))
        out["perturbations"] = {
            f"{k}/{n}": {"applicable": g["applicable"], "still_verifies": g["verified"],
                         "geomean_rlimit_ratio": round(geo(g["ratios"]), 3) if g["ratios"] else None,
                         "max_rlimit_ratio": round(max(g["ratios"]), 2) if g["ratios"] else None,
                         "frac_over_1.5x": round(sum(x > 1.5 for x in g["ratios"]) / len(g["ratios"]), 3) if g["ratios"] else None,
                         "geomean_qi_ratio": round(geo(g["qi_ratios"]), 3) if g["qi_ratios"] else None}
            for (k, n), g in sorted(agg.items())}

    (S / "replay_summary.json").write_text(json.dumps(out, indent=1))
    show = dict(out)
    show["human_vs_llm"] = {k: v for k, v in out["human_vs_llm"].items() if k != "rows"}
    print(json.dumps(show, indent=1))
    for r in out["human_vs_llm"]["rows"][:6] + out["human_vs_llm"]["rows"][-3:]:
        print(f"{r['llm_median']/r['human']:7.2f}x human={r['human']:>9.0f}(qi {r['human_qi']:.0f}) llm_med={r['llm_median']:>9.0f}(qi {r['llm_median_qi']:.0f}) best={r['llm_best']:>9.0f} {r['task_id'][:70]}")


if __name__ == "__main__":
    main()
