#!/usr/bin/env python3
"""Does proof strategy explain the within-task cost spread?

Per task, DeepSeek sees every verified proof region (shuffled, no costs) and
groups the proofs by proof strategy. We then compute the share of within-task
log-cost variance explained by the groups (eta squared) and a permutation p
over random groupings with the same group sizes.

usage: path_strategies.py --pool pool.jsonl --tasks tasks.jsonl --out-dir DIR
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
from pathlib import Path

from learn_pair_cards import region
from optimize_proof import call_deepseek
from proof_guard import items, strip_comments

PROMPT = """Below are {n} different verified Verus proofs of the SAME function
(only the proof-relevant region is shown: functions that were changed or added).

Group these proofs by PROOF STRATEGY: the overall approach to discharging the
obligations (e.g. which existing lemmas are called vs reasoning done manually,
whether a large well-formedness predicate is re-established by unfolding its
conjuncts or by a lemma, how quantified facts are established, what helper
lemmas are introduced, ghost-state bookkeeping). Ignore cosmetic differences:
comments, naming, assert order, small numbers of extra or missing asserts that
do not change the approach.

Use as few groups as the real strategic differences require (1 group is fine if
all proofs share one strategy). Reply with only a JSON object:
{{"groups": [{{"name": "...", "strategy": "2-4 sentences", "members": ["P1", ...]}}]}}
Every proof must appear in exactly one group.

{proofs}
"""


def eta2(costs: list[float], labels: list[int]) -> float:
    y = [math.log(c) for c in costs]
    m = sum(y) / len(y)
    tot = sum((v - m) ** 2 for v in y)
    if tot == 0:
        return float("nan")
    between = 0.0
    for g in set(labels):
        ys = [v for v, l in zip(y, labels) if l == g]
        between += len(ys) * (sum(ys) / len(ys) - m) ** 2
    return between / tot


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", type=Path, required=True)
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--perms", type=int, default=10000)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    pool = [json.loads(l) for l in a.pool.read_text().splitlines()]
    tasks = [json.loads(l)["task_id"] for l in a.tasks.read_text().splitlines()]
    rng = random.Random(0)
    summary = []
    for t in tasks:
        xs = [x for x in pool if x["task_id"] == t and x["cost"] > 0]
        rng.shuffle(xs)
        sb = {it[0]: it[3] for it in items(strip_comments(Path(xs[0]["source_path"]).read_text()))}
        blocks = [f"### P{i + 1}\n```rust\n{region(Path(x['proof_path']).read_text(), sb)}\n```"
                  for i, x in enumerate(xs)]
        out = a.out_dir / (t[-80:] + ".json")
        if out.exists():
            res = json.loads(out.read_text())
        else:
            reply, usage = call_deepseek([{"role": "user", "content": PROMPT.format(
                n=len(xs), proofs="\n\n".join(blocks))}], a.model, a.effort, max_tokens=64000)
            m = re.search(r"\{.*\}", reply, re.S)
            res = {"task_id": t, "groups": json.loads(m.group(0))["groups"] if m else [], "usage": usage,
                   "proofs": [{"id": f"P{i + 1}", "origin": x["origin"], "cost": x["cost"],
                               "proof_path": x["proof_path"]} for i, x in enumerate(xs)]}
            out.write_text(json.dumps(res, indent=1))
        lab = {p: gi for gi, g in enumerate(res["groups"]) for p in g["members"]}
        costs = [p["cost"] for p in res["proofs"]]
        labels = [lab.get(p["id"], -1) for p in res["proofs"]]
        e = eta2(costs, labels)
        null = []
        for _ in range(a.perms):
            sh = labels[:]
            rng.shuffle(sh)
            null.append(eta2(costs, sh))
        pval = (1 + sum(v >= e - 1e-12 for v in null)) / (1 + a.perms) if not math.isnan(e) else float("nan")
        spread = max(costs) / min(costs)
        print(f"\n{t}\n  n={len(costs)} spread={spread:.2f}x groups={len(res['groups'])} "
              f"eta2={e:.2f} p={pval:.3f} missing={labels.count(-1)}")
        for gi, g in enumerate(res["groups"]):
            cs = sorted(c / 1e6 for c, l in zip(costs, labels) if l == gi)
            print(f"  [{g['name']}] costs(M)={[round(c, 1) for c in cs]}\n     {g['strategy']}")
        summary.append({"task_id": t, "n": len(costs), "spread": spread, "groups": len(res["groups"]),
                        "eta2": e, "p": pval})
    (a.out_dir / "summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
