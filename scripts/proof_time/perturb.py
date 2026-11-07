#!/usr/bin/env python3
"""Controlled perturbations of verified proofs to measure causal proof-time effects.

For each verified proof, apply one mechanical perturbation at a time and
record success and Z3 rlimit (seed 0, deterministic) against the unperturbed
proof:
  dup_asserts   duplicate every plain `assert(...);` statement (redundancy)
  broadcast     add module-level `broadcast use` of large vstd lemma groups
  unscope_by    turn `assert(P) by { B }` into `{ B } assert(P);`-style
                unscoped proof (B's facts leak into the rest of the function)
  drop_triggers remove explicit `#[trigger]` annotations (auto trigger choice)
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
from pathlib import Path

from optimize_proof import verify
from proof_guard import match_brace

BROADCAST = ("broadcast use vstd::seq_lib::group_seq_properties, vstd::set_lib::group_set_properties, "
             "vstd::map_lib::group_map_properties, vstd::multiset::group_multiset_properties;\n")


def dup_asserts(t: str) -> str:
    return re.sub(r"(?m)^(\s*)(assert\((?:[^;{}]|\([^;{}]*\))*\);)\s*$", r"\1\2\n\1\2", t)


def broadcast(t: str) -> str:
    m = re.search(r"verus!\s*\{", t)
    return t[: m.end()] + "\n" + BROADCAST + t[m.end():] if m else t


def unscope_by(t: str) -> str:
    out, i = [], 0
    for m in re.finditer(r"\bassert\s*\(", t):
        if m.start() < i:
            continue
        # find closing paren of assert(...)
        depth, j = 0, m.end() - 1
        while j < len(t):
            depth += t[j] == "("
            depth -= t[j] == ")"
            if depth == 0:
                break
            j += 1
        k = j + 1
        mby = re.match(r"\s*by\s*\{", t[k:])
        if not mby:
            continue
        bstart = k + mby.end() - 1
        bend = match_brace(t, bstart)
        semi = re.match(r"\s*;", t[bend:])
        tail = bend + (semi.end() if semi else 0)
        body = t[bstart + 1: bend - 1]
        out.append(t[i: m.start()])
        out.append(body.strip() + "\n" + t[m.start(): j + 1] + ";")
        i = tail
    out.append(t[i:])
    return "".join(out)


def drop_triggers(t: str) -> str:
    return re.sub(r"#\[\s*trigger\s*\]\s*", "", t)


PERTURB = {"dup_asserts": dup_asserts, "broadcast": broadcast,
           "unscope_by": unscope_by, "drop_triggers": drop_triggers}


def run(item: dict) -> dict:
    text = Path(item["candidate_path"]).read_text()
    base = verify(text)
    rec = {"task_id": item["task_id"], "kind": item["kind"], "base_success": base["success"],
           "base_rlimit": base.get("rlimit"), "base_qi": base.get("qi"), "base_smt_ms": base.get("smt_ms"), "perturb": {}}
    if not base["success"]:
        return rec
    for name, fn in PERTURB.items():
        new = fn(text)
        if new == text:
            rec["perturb"][name] = {"applicable": False}
            continue
        r = verify(new)
        rec["perturb"][name] = {"applicable": True, "success": r["success"],
                                "rlimit": r.get("rlimit"), "qi": r.get("qi"), "smt_ms": r.get("smt_ms"),
                                "timed_out": r.get("timed_out", False)}
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()
    items = [json.loads(l) for l in args.items.read_text().splitlines()]
    with args.out.open("w") as fh, cf.ThreadPoolExecutor(args.workers) as pool:
        for rec in pool.map(run, items):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()


if __name__ == "__main__":
    main()
