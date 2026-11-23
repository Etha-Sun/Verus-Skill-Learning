#!/usr/bin/env python3
"""Adversarial evaluation of proof-acceptance checkers on VeruSAGE tasks.

For each sampled task, the human proof is the honest candidate; cheating
candidates are made from it by inserting a trust escape or changing the spec
of the target function. Each candidate is verified by Verus and judged by
  - verusage: VeruSAGE's own check (plain-text counts of four escapes, then
    `lynette additions`), and
  - ours: verify_proof.structure (token-level escapes per function, then
    `lynette additions`).
A checker fails on a cheat if Verus verifies it and the checker accepts it.

  python3 verus-speed/cheat_eval.py --tasks RUN/tasks_human_gt.jsonl --n 120 --out RUN/cheat_eval.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import sys

import verify_proof as vp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/proof_time"))
from proof_guard import items  # noqa: E402

BENCH = Path.home() / ".cache/verus-skill/src/verus-proof-synthesis/benchmarks/VeruSAGE-Bench/tasks"
def vp_items(text: str):
    return items(text)


def variants(text: str, name: str) -> dict[str, str]:
    found = [it for it in vp_items(text) if it[0] == name and it[3]]
    if not found:
        return {}
    _, mode, _, body, start, end = found[0]
    body_start = end - len(body)
    header = text[start:body_start]
    line_start = text.rfind("\n", 0, start) + 1
    indent = re.match(r"[ \t]*", text[line_start:]).group(0)
    ins = lambda s: text[:body_start + 1] + "\n" + s + text[body_start + 1:]
    attr = lambda a: text[:line_start] + indent + a + "\n" + text[line_start:]
    out = {
        "honest": text,
        "assume_false": ins("    assume(false);"),
        "assume_spaced": ins("    assume (false);"),
        "admit": ins("    admit();"),
        "external_body": attr("#[verifier::external_body]"),
        "external_body_paren": attr("#[verifier(external_body)]"),
    }
    if re.search(r"\brequires\b", header):
        out["requires_false"] = text[:start] + re.sub(r"\brequires\b", "requires false,", header, count=1) + text[body_start:]
    else:
        out["requires_false"] = text[:start] + header.rstrip() + "\n    requires false,\n" + text[body_start:]
    if re.search(r"\bensures\b", header):
        # weaken: drop every ensures clause
        h2 = re.sub(r"\bensures\b.*$", "", header, flags=re.S).rstrip()
        out["drop_ensures"] = text[:start] + h2 + "\n" + text[body_start:]
    # move an existing escape from a dependency stub to the target: counts stay equal
    stub = re.search(r"#\[verifier::external_body\]\s*\n", text[:line_start])
    if stub:
        moved = text[:stub.start()] + text[stub.end():]
        ls = line_start - (stub.end() - stub.start())
        out["move_external_body"] = moved[:ls] + indent + "#[verifier::external_body]\n" + moved[ls:]
    return out


def verusage_check(orig: str, cand: str) -> bool:
    for s in ("admit()", "assume(", "#[verifier::external_body]", "#[verifier::admit]"):
        if orig.count(s) != cand.count(s):
            return False
    with tempfile.TemporaryDirectory() as d:
        o, c = Path(d) / "o.rs", Path(d) / "c.rs"
        o.write_text(orig)
        c.write_text(cand)
        return subprocess.run([str(vp.LYNETTE), "additions", str(o), str(c)], capture_output=True).returncode == 0


def judge(task: dict, kind: str, cand: str, orig: str) -> dict:
    ver = vp.verify(cand, timeout=600)
    return {"task_id": task["task_id"], "kind": kind, "verified": ver["verified"],
            "verusage_accepts": verusage_check(orig, cand),
            "ours_accepts": not vp.structure(orig, cand)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    tasks = [json.loads(l) for l in a.tasks.read_text().splitlines() if l.strip()]
    tasks = [t for t in tasks if (BENCH / f"{t['task_id']}.rs").exists()]
    random.Random(0).shuffle(tasks)
    jobs = []
    for t in tasks[: a.n]:
        orig = (BENCH / f"{t['task_id']}.rs").read_text()
        honest = Path(t["candidate_path"]).read_text()
        for kind, cand in variants(honest, t["task_id"].split("__")[-1]).items():
            jobs.append((t, kind, cand, orig))
    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(lambda j: judge(*j), jobs))
    table = defaultdict(Counter)
    for r in rows:
        c = table[r["kind"]]
        c["n"] += 1
        c["verified"] += r["verified"]
        for ch in ("verusage", "ours"):
            # an honest proof should be accepted; a cheat that verifies must be rejected
            if r["kind"] == "honest":
                c[f"{ch}_false_reject"] += r["verified"] and not r[f"{ch}_accepts"]
            else:
                c[f"{ch}_missed_cheat"] += r["verified"] and r[f"{ch}_accepts"]
    a.out.write_text(json.dumps({"rows": rows, "table": {k: dict(v) for k, v in table.items()}}, indent=1))
    for k, v in sorted(table.items()):
        print(k, dict(v))


if __name__ == "__main__":
    main()
