#!/usr/bin/env python3
"""Can guidance help a model spot proof statements that are unneeded AND costly?

Ground truth: single-statement deletion results on heavy human proofs
(heavy_ablation.jsonl). A statement is positive if deleting it alone keeps the
proof verified and cuts exact Z3 rlimit by >= --pos-threshold.

For each test task the target function is shown with statement markers
/*S<k>*/; the model returns the ids of the K statements it believes are most
likely unneeded and expensive. Conditions: none | rules | cards (file) |
random | heuristic. Metrics need no new verification: precision@K and the
saving of the best single deletion among the top K.

Subcommands:
  build   write units.jsonl (task, annotated target fn, labels, train/test split)
  run     query the model per unit/condition/repeat -> predictions.jsonl
  learn   distill cards from TRAIN units' single-factor contrasts -> cards.md
  score   summarize predictions
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

from heavy_ablation import variants
from optimize_proof import call_deepseek
from proof_guard import items, strip_comments

RULES = """Evidence-based guidance (measured on real Verus projects):
1. Every assert(P) is an extra proof obligation. If P is a large predicate (a wf()/invariant/inv_* predicate, next_step(...), a refinement relation, or equality of whole structs/records) and the final goal does not need P as a stepping stone, the solver must unfold P's definition and case-split just to prove it. Such asserts are the most common source of avoidable cost.
2. An `assert forall ... by { }` with an empty or trivial body that restates a property not used afterwards forces quantifier reasoning for nothing.
3. Asserts of small facts (simple equalities, arithmetic, a single membership) are usually cheap whether needed or not.
4. Statements that bridge to a lemma call (they establish the lemma's precondition) are usually needed; deleting them breaks the proof."""

ASK = """Below is the target function of a verified Verus proof from a real project (the file's other definitions are included for reference). Statements in the target function are marked /*S<k>*/.
Some statements may be unnecessary for verification AND make the SMT solver (Z3) do significant extra work; deleting such a statement would keep the proof verified and make it faster.
List the {k} statement ids you consider MOST likely to be both unnecessary and expensive, best first.
Answer with a JSON code block: {{"ids": ["S3", "S7", ...]}}"""


def annotate(text: str, target: str, stmts: list[str]) -> tuple[str, dict]:
    it = next(i for i in items(text) if i[0] == target)
    body = text[it[4]:it[5]]
    ids, out, pos = {}, [], 0
    for k, s in enumerate(stmts):
        j = body.find(s, pos)
        if j < 0:
            continue
        out.append(body[pos:j])
        out.append(f"/*S{k}*/ ")
        ids[f"S{k}"] = s
        pos = j
    out.append(body[pos:])
    return "".join(out), ids


def build(a) -> None:
    S = a.study
    bench = {json.loads(l)["task_id"]: json.loads(l) for l in a.bench_tasks.read_text().splitlines()}
    cands = {json.loads(l)["task_id"]: json.loads(l) for l in (S / "human-gt/candidates.jsonl").read_text().splitlines()}
    rows = [json.loads(l) for l in (S / "heavy_ablation.jsonl").read_text().splitlines()]
    base = {r["task_id"]: r for r in rows if r["kind"] == "baseline" and r["success"]}
    lab = defaultdict(dict)
    for r in rows:
        if r["kind"].startswith("del_") and r["kind"] != "del_broadcast_use" and r["task_id"] in base:
            ratio = r["rlimit"] / base[r["task_id"]]["rlimit"] if r["success"] else None
            lab[r["task_id"]][(r["kind"], r["stmt"])] = {"success": r["success"], "ratio": ratio,
                                                         "timed_out": r.get("timed_out", False)}
    tasks = sorted(lab)
    rng = random.Random(20261106)
    by_proj = defaultdict(list)
    for t in tasks:
        by_proj[t[:2]].append(t)
    split = {}
    for p, ts in by_proj.items():
        rng.shuffle(ts)
        for i, t in enumerate(ts):
            split[t] = "train" if i % 2 == 0 else "test"
    with (S / "rank_units.jsonl").open("w") as fh:
        for t in tasks:
            text = strip_comments(Path(cands[t]["candidate_path"]).read_text())
            tgt = bench[t]["target_function"]
            vs = [(k, s, v) for k, s, v in variants(text, tgt, 40) if k.startswith("del_") and k != "del_broadcast_use"]
            full = []
            for k, s, _ in vs:
                # recover the full statement text from the file (s is truncated to 300 chars)
                j = text.find(s[:120])
                if j >= 0:
                    full.append((j, k, s, text[j: j + len(s)]))
            full.sort()
            full = [(k, s, f) for _, k, s, f in full]
            ann, ids = annotate(text, tgt, [f for _, _, f in full])
            labels = {}
            for (k, s, f), sid in zip(full, [f"S{i}" for i in range(len(full))]):
                if sid in ids and (k, s) in lab[t]:
                    L = lab[t][(k, s)]
                    labels[sid] = {"kind": k, "stmt": f[:400], **L,
                                   "positive": bool(L["success"] and L["ratio"] is not None and L["ratio"] <= 1 - a.pos_threshold)}
            if not labels:
                continue
            it = next(i for i in items(text) if i[0] == tgt)
            context = text[: it[4]] + "/* ===== TARGET FUNCTION BELOW ===== */\n" + ann + "\n/* ===== END TARGET ===== */" + text[it[5]:]
            fh.write(json.dumps({"task_id": t, "split": split[t], "context": context, "labels": labels}) + "\n")


def parse_ids(reply: str) -> list[str]:
    m = re.findall(r"```json\s*(\{.*?\})\s*```", reply, flags=re.S) or re.findall(r"(\{\s*\"ids\".*?\})", reply, flags=re.S)
    try:
        return [str(x) for x in json.loads(m[-1])["ids"]]
    except Exception:
        return re.findall(r"S\d+", reply)[:10]


def heuristic(labels: dict) -> list[str]:
    def score(sid):
        s = labels[sid]["stmt"]
        big = bool(re.search(r"\b(wf|inv\w*|next_step|refines|valid\w*)\s*\(", s))
        return (labels[sid]["kind"] == "del_assert_forall") * 2 + big * 2 + len(s) / 400
    return sorted(labels, key=score, reverse=True)


def run(a) -> None:
    S = a.study
    units = [json.loads(l) for l in (S / "rank_units.jsonl").read_text().splitlines()]
    units = [u for u in units if u["split"] in a.splits]
    cards = a.cards.read_text() if a.cards else None
    jobs = []
    for u in units:
        for cond in a.conditions:
            for rep in range(a.repeats if cond not in ("heuristic",) else 1):
                jobs.append((u, cond, rep))
    out = S / a.output
    done = set()
    if out.exists():
        for l in out.read_text().splitlines():
            r = json.loads(l)
            done.add((r["task_id"], r["condition"], r["repeat"]))
    jobs = [j for j in jobs if (j[0]["task_id"], j[1], j[2]) not in done]
    print(len(jobs), "queries", flush=True)

    def job(j):
        u, cond, rep = j
        sids = list(u["labels"])
        if cond == "random":
            r = random.Random(rep * 7919 + hash(u["task_id"]) % 10007)
            pred, usage = r.sample(sids, len(sids)), {}
        elif cond == "heuristic":
            pred, usage = heuristic(u["labels"]), {}
        else:
            guide = {"none": "", "rules": RULES, "cards": f"Learned guidance:\n{cards}"}[cond]
            msg = (guide + "\n\n" if guide else "") + ASK.format(k=a.k) + "\n\n```rust\n" + u["context"] + "\n```"
            reply, usage = call_deepseek([{"role": "user", "content": msg}], a.model, a.effort, max_tokens=64000)
            if not reply.strip():
                return {"task_id": u["task_id"], "split": u["split"], "condition": cond, "repeat": rep, "pred": [], "usage": usage, "empty_reply": True}
            pred = [p for p in parse_ids(reply) if p in u["labels"]]
        return {"task_id": u["task_id"], "split": u["split"], "condition": cond, "repeat": rep,
                "pred": pred[: a.k], "usage": usage}

    with out.open("a") as fh, cf.ThreadPoolExecutor(a.workers) as pool:
        for rec in pool.map(job, jobs):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()


def learn(a) -> None:
    S = a.study
    units = [json.loads(l) for l in (S / "rank_units.jsonl").read_text().splitlines() if json.loads(l)["split"] == "train"]
    ex = []
    for u in units:
        for sid, L in u["labels"].items():
            if L["positive"]:
                tag = f"DELETABLE AND COSTLY: deleting it alone cut solver work to {L['ratio']:.2f}x"
            elif not L["success"]:
                tag = "NEEDED: deleting it " + ("made verification run past 4x the original time" if L["timed_out"] else "breaks the proof")
            elif L["ratio"] is not None and L["ratio"] > 0.97:
                tag = f"DELETABLE BUT CHEAP: deleting it changes solver work to {L['ratio']:.2f}x"
            else:
                continue
            ex.append((u["task_id"], tag, L["stmt"]))
    rng = random.Random(0)
    pos = [e for e in ex if e[1].startswith("DELETABLE AND")]
    neg = [e for e in ex if not e[1].startswith("DELETABLE AND")]
    rng.shuffle(neg)
    sample = pos + neg[: 3 * len(pos)]
    rng.shuffle(sample)
    body = "\n\n".join(f"[{t[:70]}] {tag}\n{stmt}" for t, tag, stmt in sample)
    prompt = ("Each item is one statement from the target function of a verified Verus proof in a large real project, "
              "with the measured effect of deleting ONLY that statement (exact Z3 resource count). "
              "Derive at most 6 concise, general rules that let someone reading a proof predict which statements are "
              "unnecessary AND expensive, versus needed or cheap. Base every rule on patterns visible in the statements; "
              "say what distinguishes costly-deletable statements from needed ones. Output the rules as a numbered list, "
              "under 250 words total.\n\n" + body)
    reply, usage = call_deepseek([{"role": "user", "content": prompt}], a.model, "high", max_tokens=16000)
    (S / "rank_cards.md").write_text(reply.strip() + "\n")
    (S / "rank_cards_meta.json").write_text(json.dumps({"n_items": len(sample), "n_pos": len(pos), "usage": usage}))
    print(reply)


def score(a) -> None:
    S = a.study
    units = {json.loads(l)["task_id"]: json.loads(l) for l in (S / "rank_units.jsonl").read_text().splitlines()}
    preds = [json.loads(l) for l in (S / a.output).read_text().splitlines()]
    per = defaultdict(lambda: defaultdict(list))
    for p in preds:
        u = units[p["task_id"]]
        L = u["labels"]
        npos = sum(v["positive"] for v in L.values())
        if npos == 0:
            continue
        top = p["pred"][: a.k]
        prec = sum(L[s]["positive"] for s in top) / a.k
        best = min([L[s]["ratio"] for s in top if L[s]["success"] and L[s]["ratio"] is not None] + [1.0])
        oracle = min(v["ratio"] for v in L.values() if v["success"] and v["ratio"] is not None)
        captured = (1 - best) / (1 - oracle) if oracle < 1 else 0
        broke = sum(not L[s]["success"] for s in top)
        per[(p["split"], p["condition"])][p["task_id"]].append((prec, captured, broke))
    print(f"K={a.k}; tasks with >=1 positive only")
    print(f"{'split':6} {'condition':10} {'tasks':>5} {'precision@K':>12} {'saving captured':>16} {'needed stmts in top-K':>22}")
    agg = {}
    for (split, cond), d in sorted(per.items()):
        m = {t: tuple(st.mean(x[i] for x in v) for i in range(3)) for t, v in d.items()}
        agg[(split, cond)] = m
        print(f"{split:6} {cond:10} {len(m):5} {st.mean(x[0] for x in m.values()):12.3f} "
              f"{st.mean(x[1] for x in m.values()):16.3f} {st.mean(x[2] for x in m.values()):22.2f}")
    # paired sign tests on test split, captured saving
    for c1, c2 in [("rules", "none"), ("cards", "none"), ("cards", "rules"), ("none", "heuristic"),
                   ("rules", "heuristic"), ("cards", "heuristic"), ("none", "random")]:
        for split in ("train", "test"):
            A, B = agg.get((split, c1)), agg.get((split, c2))
            if not A or not B:
                continue
            ts = set(A) & set(B)
            w = sum(A[t][1] > B[t][1] + 1e-9 for t in ts)
            l = sum(A[t][1] < B[t][1] - 1e-9 for t in ts)
            print(f"  {split}: {c1} vs {c2}: wins {w}, losses {l}, ties {len(ts) - w - l}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "run", "learn", "score"])
    ap.add_argument("--study", type=Path, required=True)
    ap.add_argument("--bench-tasks", type=Path)
    ap.add_argument("--pos-threshold", type=float, default=0.10)
    ap.add_argument("--conditions", nargs="+", default=["random", "heuristic", "none", "rules"])
    ap.add_argument("--splits", nargs="+", default=["train", "test"])
    ap.add_argument("--cards", type=Path)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--output", default="rank_predictions.jsonl")
    a = ap.parse_args()
    {"build": build, "run": run, "learn": learn, "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
