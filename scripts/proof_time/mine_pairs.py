#!/usr/bin/env python3
"""Pool every verified DeepSeek proof with an exact cost and mine same-task
cost-contrast pairs (cheap vs costly proof of the same task, both verified).

Cost = exact Z3 rlimit (SMT replay, seed 0) of the benchmark target fn plus
every fn the proof added. Sources:
  historical  candidates.jsonl + replay.jsonl (kind=llm, seed 0)
  e2e         <run>/<cond>/<task>__r<k>/result.json (+ workspace/candidate.rs)

usage: mine_pairs.py <run_root> <bench tasks.jsonl> <split_tasks.csv> <out_dir>
Writes pool.jsonl and pairs.jsonl (ratio >= --min-ratio) and prints a summary.
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import statistics as st
from pathlib import Path

from proof_guard import items, strip_comments


def names_of(text: str) -> set[str]:
    return {it[0] for it in items(strip_comments(text))}


def target_cost(funcs: dict, tgt: str, cand: str, src: str) -> float:
    names = {tgt} | (names_of(cand) - names_of(src))
    return sum((v["rlimit"] if isinstance(v, dict) else v) for k, v in funcs.items() if k.split("::")[-1] in names)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_root", type=Path)
    ap.add_argument("bench", type=Path)
    ap.add_argument("split_csv", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--min-ratio", type=float, default=1.5)
    a = ap.parse_args()
    bench = {json.loads(l)["task_id"]: json.loads(l) for l in a.bench.read_text().splitlines()}
    split = {r["task_id"]: r["split"] for r in csv.DictReader(a.split_csv.open())}
    pool = []
    # historical candidates
    cands = {json.loads(l)["candidate_sha256"]: json.loads(l) for l in (a.run_root / "candidates.jsonl").read_text().splitlines()}
    for l in (a.run_root / "replay.jsonl").read_text().splitlines():
        r = json.loads(l)
        if r["kind"] != "llm" or r.get("seed") != 0 or not r["success"] or r["candidate_sha256"] not in cands:
            continue
        c = cands[r["candidate_sha256"]]
        t = r["task_id"]
        text = Path(c["candidate_path"]).read_text()
        pool.append({"task_id": t, "origin": "historical", "proof_path": c["candidate_path"],
                     "source_path": c["source_path"],
                     "cost": target_cost(r["functions"], bench[t]["target_function"], text,
                                         Path(c["source_path"]).read_text())})
    # end-to-end runs
    for run, tasks_file in [("e2e_codex", "e2e_val_tasks.jsonl"), ("e2e_heavy", "e2e_heavy_main.jsonl")]:
        tasks = {json.loads(l)["task_id"]: json.loads(l) for l in (a.run_root / tasks_file).read_text().splitlines()}
        for f in glob.glob(str(a.run_root / run / "*/*/result.json")):
            r = json.loads(Path(f).read_text())
            if not r["solved"]:
                continue
            t = r["task_id"]
            p = Path(f).parent / "workspace/candidate.rs"
            pool.append({"task_id": t, "origin": f"{run}:{r['condition']}", "proof_path": str(p),
                         "source_path": tasks[t]["source_path"],
                         "cost": target_cost(r["final_functions"], bench[t]["target_function"], p.read_text(),
                                             Path(tasks[t]["source_path"]).read_text())})
    for x in pool:
        x["split"] = split.get(x["task_id"], "bench_only")
    by = collections.defaultdict(list)
    for x in pool:
        if x["cost"] > 0:
            by[x["task_id"]].append(x)
    pairs = []
    for t, xs in by.items():
        lo, hi = min(xs, key=lambda x: x["cost"]), max(xs, key=lambda x: x["cost"])
        if hi["cost"] / lo["cost"] >= a.min_ratio:
            pairs.append({"task_id": t, "split": lo["split"], "ratio": hi["cost"] / lo["cost"],
                          "n_proofs": len(xs), "cheap": lo, "costly": hi,
                          "median_cost": st.median(x["cost"] for x in xs)})
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "pool.jsonl").write_text("".join(json.dumps(x) + "\n" for x in pool))
    (a.out_dir / "pairs.jsonl").write_text("".join(json.dumps(p) + "\n" for p in sorted(pairs, key=lambda p: -p["ratio"])))
    print(f"pool: {len(pool)} verified proofs over {len(by)} tasks; tasks with >=2 proofs: "
          f"{sum(len(v) >= 2 for v in by.values())}")
    for s in ("train", "val", "test", "selection", "bench_only"):
        ts = [t for t in by if by[t][0]["split"] == s]
        ps = [p for p in pairs if p["split"] == s]
        if ts:
            print(f"  {s:10} tasks={len(ts):3} with>=2={sum(len(by[t]) >= 2 for t in ts):3} "
                  f"pairs(ratio>={a.min_ratio})={len(ps):3} big(>=3x)={sum(p['ratio'] >= 3 for p in ps):2}")
    for p in sorted(pairs, key=lambda p: -p["ratio"])[:25]:
        print(f"  {p['ratio']:6.2f}x n={p['n_proofs']:2} {p['split']:10} median={p['median_cost']/1e6:7.3f}M  {p['task_id'][:70]}")


if __name__ == "__main__":
    main()
