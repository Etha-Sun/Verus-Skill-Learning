#!/usr/bin/env python3
"""Learn proof-cost cards from same-task cost-contrast pairs.

For each training task with a verified cheap and a verified costly proof
(exact target cost ratio >= --min-ratio), DeepSeek sees a unified diff of the
proof region (fns that differ from the task source or were added), costly ->
cheap, plus both exact costs. It explains each pair, then writes general,
conditional cards (no task-specific names) that become a SKILL section.

usage: learn_pair_cards.py --pool pool.jsonl --train-tasks a.jsonl [b.jsonl] --splits train
                           --out-dir DIR --skill-out cards.md
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import re
from pathlib import Path

from optimize_proof import call_deepseek
from proof_guard import items, strip_comments

PROMPT = """You are studying why some verified Verus proofs are much more expensive for the
SMT solver (Z3) than other verified proofs of the SAME lemma or function. Cost is
the exact Z3 resource count (rlimit) of the target function plus helper
functions the proof added; it is deterministic, so differences are real.

Below are {n} pairs. Each shows a unified diff of the proof region from the
COSTLY proof (-) to the CHEAP proof (+), with both costs. Both versions verify.

Tasks:
1. For each pair, in 2-4 sentences, identify the concrete differences that most
   plausibly explain the cost gap (e.g. which obligations or facts each version
   asks the solver to prove or carry, how a large predicate is handled, lemma
   use, decomposition, ghost/tracked bookkeeping). Be careful: the number of
   asserts is NOT a reliable predictor; sometimes adding asserts makes a proof
   cheaper. Say what the context was when a choice helped or hurt.
2. Then write at most 6 CARDS for a proof-writing agent. Each card:
   - is general (no task, module, function or predicate names from these
     files; describe the shape instead, e.g. "a well-formedness predicate that
     is a conjunction of many sub-predicates");
   - is conditional: "When <situation you can recognize while writing>, do <X>
     rather than <Y>, because <solver-cost mechanism>";
   - cites the pair numbers that support it; drop any idea supported by no pair
     or contradicted by another pair.
Output format: a section "## Pair analysis", then a section "## Cards" with a
numbered list. Keep the Cards section under 450 words.

{pairs}
"""


def region(text: str, src_bodies: dict) -> str:
    t = strip_comments(text)
    return "\n".join(t[it[4]:it[5]] for it in items(t) if src_bodies.get(it[0]) != it[3])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", type=Path, required=True)
    ap.add_argument("--train-tasks", type=Path, nargs="*", default=[])
    ap.add_argument("--splits", nargs="*", default=["train"], help="fixture splits also allowed for training")
    ap.add_argument("--exclude", type=Path, nargs="*", default=[], help="task lists that must never be used")
    ap.add_argument("--min-ratio", type=float, default=1.5)
    ap.add_argument("--max-diff-lines", type=int, default=220)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--skill-out", type=Path, required=True)
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--effort", default="max")
    a = ap.parse_args()
    allowed = {json.loads(l)["task_id"] for f in a.train_tasks for l in f.read_text().splitlines()}
    banned = {json.loads(l)["task_id"] for f in a.exclude for l in f.read_text().splitlines()}
    by = collections.defaultdict(list)
    for l in a.pool.read_text().splitlines():
        x = json.loads(l)
        if x["cost"] > 0 and x["task_id"] not in banned and (x["task_id"] in allowed or x["split"] in a.splits):
            by[x["task_id"]].append(x)
    blocks, meta = [], []
    for t, xs in sorted(by.items()):
        lo, hi = min(xs, key=lambda x: x["cost"]), max(xs, key=lambda x: x["cost"])
        if hi["cost"] / lo["cost"] < a.min_ratio:
            continue
        src = strip_comments(Path(lo["source_path"]).read_text())
        sb = {it[0]: it[3] for it in items(src)}
        d = list(difflib.unified_diff(region(Path(hi["proof_path"]).read_text(), sb).splitlines(),
                                      region(Path(lo["proof_path"]).read_text(), sb).splitlines(),
                                      "costly", "cheap", lineterm="", n=2))
        if len(d) > a.max_diff_lines:
            d = d[: a.max_diff_lines] + [f"... ({len(d) - a.max_diff_lines} more diff lines omitted)"]
        k = len(meta) + 1
        blocks.append(f"### Pair {k}: costly {hi['cost']:.0f} rlimit vs cheap {lo['cost']:.0f} rlimit "
                      f"({hi['cost'] / lo['cost']:.2f}x)\n```diff\n" + "\n".join(d) + "\n```")
        meta.append({"pair": k, "task_id": t, "ratio": hi["cost"] / lo["cost"], "cheap": lo["proof_path"],
                     "costly": hi["proof_path"], "diff_lines": len(d)})
    a.out_dir.mkdir(parents=True, exist_ok=True)
    prompt = PROMPT.format(n=len(meta), pairs="\n\n".join(blocks))
    (a.out_dir / "prompt.md").write_text(prompt)
    (a.out_dir / "pairs_used.json").write_text(json.dumps(meta, indent=1))
    print(f"{len(meta)} pairs, prompt {len(prompt)} chars")
    reply, usage = call_deepseek([{"role": "user", "content": prompt}], a.model, a.effort, max_tokens=64000)
    (a.out_dir / "reply.md").write_text(reply)
    (a.out_dir / "usage.json").write_text(json.dumps(usage))
    m = re.search(r"##\s*Cards\s*\n(.*)", reply, re.S)
    if not m:
        raise SystemExit("no Cards section in reply; see reply.md")
    cards = m.group(1).strip()
    for t in by:  # leak check: no task-specific identifiers
        for name in {t.split("__")[-1]}:
            if name in cards:
                print(f"WARNING: card text mentions {name}")
    a.skill_out.write_text("## Writing proofs that are cheap for the solver (learned from same-task proof pairs)\n\n"
                           + cards + "\n")
    print(cards)
    print("usage", usage)


if __name__ == "__main__":
    main()
