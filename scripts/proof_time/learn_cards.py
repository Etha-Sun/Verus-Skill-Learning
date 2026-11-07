#!/usr/bin/env python3
"""Distill proof-speed cards from same-node cost contrasts (train split only).

Contrast packets:
  * optimizer: one verified baseline proof (the node) -> each attempted edit,
    labelled improved / not_improved / verify_fail with exact rlimit and
    quantifier-instantiation (QI) deltas;
  * historical: for the same task (the root node), the cheapest vs the most
    expensive verified DeepSeek proof, and the human proof when it is cheaper.
DeepSeek writes candidate cards per batch of packets; a final call merges them.
"""
from __future__ import annotations

import argparse
import difflib
import json
import random
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

from optimize_proof import call_deepseek
from proof_guard import items, strip_comments

CARD_PROMPT = """You study how the way a Verus proof is written changes the work the Z3 SMT solver must do.
Each packet contrasts proofs that start from the same node (same task, same starting proof). Costs are exact Z3 rlimit-count and quantifier instantiations (QI); lower is faster. "verify_fail" means the edit broke the proof.

Write reusable "speed cards" a proof-writing agent can apply BEFORE seeing costs. Each card must be grounded in at least one packet and must state when it applies, because the meeting that motivated this found that guidance is harmful when applied in the wrong proof state.

Return exactly one JSON code block:
```json
{"cards": [{"title": "...", "when": "observable situation in the proof or Verus output", "do": "concrete rewrite", "avoid": "what not to do / when the card does not apply or breaks proofs", "why": "Z3 mechanism (e-matching, context size, ground terms, ...)", "evidence": ["packet ids"], "effect": "typical observed cost change"}]}
```"""

MERGE_PROMPT = """Merge these candidate Verus proof-speed cards into at most {k} non-overlapping cards, ordered by observed impact. Keep the "when"/"avoid" conditions precise, drop cards whose evidence is a single small effect, and keep each card under 90 words. Return a JSON code block {{"cards": [...]}} with the same fields."""


def diff(a: str, b: str, n: int = 2, limit: int = 140) -> str:
    d = list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=n))[2:]
    if len(d) > limit:
        d = d[:limit] + [f"... ({len(d) - limit} more diff lines)"]
    return "\n".join(d)


def optimizer_packets(opt_dir: Path, tasks: dict) -> list[dict]:
    pk = []
    for tdir in sorted(opt_dir.iterdir()):
        traj = tdir / "trajectory.jsonl"
        if not traj.exists():
            continue
        rows = [json.loads(l) for l in traj.read_text().splitlines()]
        if not rows or rows[0].get("kind") != "baseline":
            continue
        base = Path(tasks[tdir.name]["candidate_path"]).read_text()
        b_rl = rows[0]["rlimit"]
        prev = base
        best_rl = b_rl
        for r in rows[1:]:
            if "candidate" not in r:
                continue
            outcome = r["outcome"]
            ratio = (r["rlimit"] / best_rl) if (r.get("success") and best_rl) else None
            pk.append({"id": f"opt:{tdir.name[:40]}:r{r['round']}", "task": tdir.name, "outcome": outcome,
                       "rlimit_before": best_rl, "rlimit_after": r.get("rlimit") if r.get("success") else None,
                       "ratio": ratio, "rationale": r["reply"].split("```")[0][-800:],
                       "diff": diff(prev, r["candidate"])})
            if outcome == "improved":
                prev, best_rl = r["candidate"], r["rlimit"]
    return pk


def historical_packets(study: Path, train_ids: set, tasks_bench: dict) -> list[dict]:
    cands = {}
    for p in (study / "candidates.jsonl", study / "human-gt/candidates.jsonl"):
        for l in p.read_text().splitlines():
            r = json.loads(l)
            cands[r["candidate_sha256"]] = r
    ctx_cache: dict[str, set] = {}

    def ctx_fns(task: str) -> set:
        """Fn names declared in the original task file plus the pre-query bucket."""
        if task not in ctx_cache:
            src = next(c["source_path"] for c in cands.values()
                       if c["task_id"] == task and "human_ground_truth" not in c["arms"])
            ctx_cache[task] = {it[0] for it in items(strip_comments(Path(src).read_text()))} | {"<none>"}
        return ctx_cache[task]

    per = defaultdict(list)
    human = {}
    for l in (study / "replay.jsonl").read_text().splitlines():
        r = json.loads(l)
        if not r.get("success") or r["seed"] != 0:
            continue
        t = r["task_id"]
        if t not in train_ids:
            continue
        tgt = tasks_bench[t]["target_function"]
        fs = {k.split("::")[-1]: v for k, v in r["functions"].items()}
        cost = fs.get(tgt, {}).get("rlimit", 0)
        qi = fs.get(tgt, {}).get("qi", 0)
        if r["kind"] == "llm":
            llm_t = sum(v.get("rlimit", 0) for k, v in fs.items() if k == tgt or k not in ctx_fns(t))
            per[t].append((llm_t, qi, r["candidate_sha256"]))
        else:
            human[t] = (cost, qi, r["candidate_sha256"])
    pk = []
    # human proof much cheaper than the typical LLM proof: show both target implementations
    for t, xs in per.items():
        if t not in human:
            continue
        tgt = tasks_bench[t]["target_function"]
        med = sorted(xs)[(len(xs) - 1) // 2]
        llm_tgt = med[0]  # whole-file cost is close to target cost for LLM task files
        h_cost = human[t][0]
        if h_cost <= 0 or llm_tgt < 1.5 * h_cost:
            continue
        src_fns = {it[0] for it in items(strip_comments(Path(cands[med[2]]["source_path"]).read_text()))}
        llm_text = strip_comments(Path(cands[med[2]]["candidate_path"]).read_text())
        llm_fns = [it for it in items(llm_text) if it[0] == tgt or it[0] not in src_fns]
        hum_text = strip_comments(Path(cands[human[t][2]]["candidate_path"]).read_text())
        hum_fns = [it for it in items(hum_text) if it[0] == tgt]
        show = lambda txt, its: "\n\n".join(txt[it[4]: it[5]] for it in its)[:6000]
        pk.append({"id": f"human:{t[:40]}", "task": t, "outcome": "llm_vs_cheaper_human",
                   "rlimit_before": llm_tgt, "rlimit_after": h_cost, "qi_before": med[1], "qi_after": human[t][1],
                   "ratio": h_cost / llm_tgt,
                   "diff": f"// typical DeepSeek proof (target + helpers it added):\n{show(llm_text, llm_fns)}\n\n"
                           f"// cheaper human proof of the same target:\n{show(hum_text, hum_fns)}"})
    for t, xs in per.items():
        if len(xs) < 2:
            continue
        xs.sort()
        lo, hi = xs[0], xs[-1]
        if hi[0] < 1.5 * lo[0]:
            continue
        a = Path(cands[hi[2]]["candidate_path"]).read_text()
        b = Path(cands[lo[2]]["candidate_path"]).read_text()
        pk.append({"id": f"hist:{t[:40]}", "task": t, "outcome": "slow_vs_fast_verified",
                   "rlimit_before": hi[0], "rlimit_after": lo[0], "qi_before": hi[1], "qi_after": lo[1],
                   "ratio": lo[0] / hi[0], "diff": diff(a, b)})
    return pk


def fmt(p: dict) -> str:
    head = {k: p[k] for k in p if k not in ("diff", "rationale", "task")}
    s = f"### Packet {p['id']}\n{json.dumps(head)}\n"
    if p.get("rationale"):
        s += f"Editor rationale: {p['rationale'].strip()}\n"
    return s + f"Diff (slower/before -> after):\n```diff\n{p['diff']}\n```\n"


def parse_cards(reply: str):
    m = re.findall(r"```json\s*(\{.*?\})\s*```", reply, flags=re.S)
    try:
        return json.loads(m[-1])["cards"] if m else []
    except Exception:
        return []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, required=True)
    ap.add_argument("--opt-dir", type=Path, required=True)
    ap.add_argument("--tasks", type=Path, required=True, help="opt_tasks_train.jsonl")
    ap.add_argument("--bench-tasks", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--max-cards", type=int, default=10)
    ap.add_argument("--model", default="deepseek-v4-pro")
    a = ap.parse_args()
    tasks = {json.loads(l)["task_id"]: json.loads(l) for l in a.tasks.read_text().splitlines()}
    bench = {json.loads(l)["task_id"]: json.loads(l) for l in a.bench_tasks.read_text().splitlines()}
    pk = optimizer_packets(a.opt_dir, tasks) + historical_packets(a.study, set(tasks), bench)
    # keep informative packets: all improvements, failures, and clear regressions
    keep = [p for p in pk if p["outcome"] in ("improved", "verify_fail", "slow_vs_fast_verified")
            or (p["ratio"] or 1) > 1.2]
    random.Random(0).shuffle(keep)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "packets.jsonl").write_text("".join(json.dumps(p) + "\n" for p in keep))
    print(f"{len(pk)} packets, {len(keep)} kept: "
          f"{sum(p['outcome']=='improved' for p in keep)} improved, {sum(p['outcome']=='verify_fail' for p in keep)} verify_fail, "
          f"{sum(p['outcome']=='slow_vs_fast_verified' for p in keep)} historical")
    cand_cards, usage = [], defaultdict(int)
    for i in range(0, len(keep), a.batch):
        batch = keep[i: i + a.batch]
        msg = CARD_PROMPT + "\n\n" + "\n".join(fmt(p) for p in batch)
        reply, u = call_deepseek([{"role": "user", "content": msg}], a.model, "high")
        for k, v in u.items():
            if isinstance(v, int):
                usage[k] += v
        cand_cards += parse_cards(reply)
    (a.out / "candidate_cards.json").write_text(json.dumps(cand_cards, indent=1))
    reply, u = call_deepseek([{"role": "user", "content": MERGE_PROMPT.format(k=a.max_cards) + "\n\n" + json.dumps(cand_cards)}], a.model, "high")
    for k, v in u.items():
        if isinstance(v, int):
            usage[k] += v
    cards = parse_cards(reply)
    (a.out / "cards.json").write_text(json.dumps(cards, indent=1))
    md = "\n".join(f"{i+1}. **{c['title']}**\n   - When: {c['when']}\n   - Do: {c['do']}\n   - Avoid: {c['avoid']}\n   - Why: {c['why']}\n"
                   for i, c in enumerate(cards))
    (a.out / "cards.md").write_text(md)
    (a.out / "usage.json").write_text(json.dumps(usage))
    print(md)


if __name__ == "__main__":
    main()
