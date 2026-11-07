#!/usr/bin/env python3
"""Analyze the end-to-end A/B (base / rules / procedure).

Per task, uses the median over solved repeats of the final proof's exact Z3
cost (target fn + helpers the proof added; whole-file total also reported),
then compares conditions paired over tasks solved in both conditions.
Also reports solve rates, actor wall time, and agent Verus calls.
A sign-flip permutation test on per-task log ratios gives a p-value.
"""
import json
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from proof_guard import items, strip_comments

root = Path(sys.argv[1])
tasks = {json.loads(l)["task_id"]: json.loads(l) for l in Path(sys.argv[2]).read_text().splitlines()}
bench = {json.loads(l)["task_id"]: json.loads(l) for l in Path(sys.argv[3]).read_text().splitlines()}
rs = [json.loads(p.read_text()) for p in root.glob("*/*/result.json")]
conds = ["base", "rules", "procedure"]
src_fns = {}


def target_cost(r):
    t = r["task_id"]
    if t not in src_fns:
        src_fns[t] = {it[0] for it in items(strip_comments(Path(tasks[t]["source_path"]).read_text()))}
    tgt = bench[t]["target_function"]
    final = root / r["condition"] / f"{t[:100]}__r{r['repeat']}" / "workspace" / "candidate.rs"
    names = {tgt} | ({it[0] for it in items(strip_comments(final.read_text()))} - src_fns[t])
    return sum(v for k, v in r["final_functions"].items() if k.split("::")[-1] in names)


by = defaultdict(lambda: defaultdict(list))
print(f"episodes: {len(rs)}")
for c in conds:
    x = [r for r in rs if r["condition"] == c]
    if not x:
        continue
    print(f"{c:10} n={len(x):3} solved={sum(r['solved'] for r in x):3} ({sum(r['solved'] for r in x)/len(x):.2f}) "
          f"timeouts={sum(r['timed_out'] for r in x):2} median actor wall={st.median(r['actor_wall'] for r in x):6.1f}s "
          f"median agent verus calls={st.median(r['agent_verus_calls'] for r in x)}")
    for r in x:
        if r["solved"]:
            by[r["task_id"]][c].append((target_cost(r), r["final_rlimit"], r["actor_wall"]))


def perm_p(logs, n=20000):
    obs = abs(sum(logs))
    rng = random.Random(0)
    hits = sum(abs(sum(l if rng.random() < 0.5 else -l for l in logs)) >= obs - 1e-12 for _ in range(n))
    return hits / n


for a_, b_ in [("rules", "base"), ("procedure", "base"), ("procedure", "rules")]:
    for label, idx in [("target cost", 0), ("whole-file cost", 1), ("actor wall", 2)]:
        logs = [math.log(st.median(v[0] for v in by[t][a_]) if idx == 0 else st.median(x[idx] for x in by[t][a_]))
                - math.log(st.median(v[0] for v in by[t][b_]) if idx == 0 else st.median(x[idx] for x in by[t][b_]))
                for t in by if by[t][a_] and by[t][b_]
                and (st.median(x[idx] for x in by[t][b_]) > 0)]
        if not logs:
            continue
        print(f"{a_:9} / {b_:9} {label:15} tasks={len(logs):2} geomean ratio={math.exp(st.mean(logs)):.3f} "
              f"cheaper(>5%)={sum(l < math.log(0.95) for l in logs):2} costlier(>5%)={sum(l > math.log(1.05) for l in logs):2} "
              f"p={perm_p(logs):.3f}")
# within-condition run-to-run spread (noise floor)
spread = [max(v[0] for v in by[t][c]) / max(min(v[0] for v in by[t][c]), 1)
          for t in by for c in conds if len(by[t][c]) >= 2]
if spread:
    print(f"noise floor: same task+condition, max/min target cost across repeats: median {st.median(spread):.3f}, "
          f"p75 {sorted(spread)[int(.75*len(spread))]:.3f}")
