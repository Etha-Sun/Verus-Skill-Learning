#!/usr/bin/env python3
"""Per-quantifier instantiation profile of a Verus proof via SMT-log replay.

Runs Verus with --log smt, replays every log in the bundled Z3 with
smt.qi.profile=true, and aggregates instantiation counts by quantifier id and
by family:
  prelude      Verus built-in axioms (arithmetic, boxing, fuel)
  definition   unfolding of spec fn definitions (internal_..._definition)
  user         quantifiers written in user specs/proofs/lemma ensures (user_...)
  other_internal / skolem
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path

from measure_candidates import DEFAULT_VERUS, verus_env

Z3 = DEFAULT_VERUS.parent / "z3"
LINE = re.compile(r"\[quantifier_instances\]\s+(\S+)\s+:\s+(\d+)")


def family(qid: str) -> str:
    if qid.startswith("prelude_"):
        return "prelude"
    if qid.startswith("user_"):
        return "user"
    if qid.startswith("internal_") and qid.endswith("_definition"):
        return "definition"
    if qid.startswith("internal_"):
        return "other_internal"
    return "skolem_or_other"


def profile(text: str, timeout: int = 1800) -> dict:
    with tempfile.TemporaryDirectory(prefix="qip-") as tmp:
        (Path(tmp) / "candidate.rs").write_text(text)
        subprocess.run([str(DEFAULT_VERUS), "candidate.rs", "--log", "smt", "--log-dir", "lg"],
                       cwd=tmp, env=verus_env(), capture_output=True, timeout=timeout)
        counts: Counter = Counter()
        stats: dict = {}
        wall = 0.0
        for log in sorted((Path(tmp) / "lg").glob("*.smt2")):
            body = "\n".join(l for l in log.read_text().splitlines() if not l.strip().startswith("(get-info"))
            t0 = time.monotonic()
            body = body.replace("(check-sat)", "(check-sat)\n(get-info :all-statistics)")
            p = subprocess.run([str(Z3), "-in"], input="(set-option :smt.qi.profile true)\n" + body,
                               capture_output=True, text=True, timeout=timeout)
            wall += time.monotonic() - t0
            for q, n in LINE.findall(p.stdout + p.stderr):
                counts[q] += int(n)
            # statistics are cumulative per Z3 process: keep the last block of each log
            blocks = re.findall(r"\(:added-eqs.*?\)", p.stdout, flags=re.S)
            if blocks:
                for k, v in re.findall(r":([a-z\-]+)\s+([0-9.]+)", blocks[-1]):
                    stats[k] = stats.get(k, 0) + float(v)
    total = sum(counts.values())
    fam = Counter()
    for q, n in counts.items():
        fam[family(q)] += n
    top = counts.most_common(15)
    keys = ("rlimit-count", "time", "quant-instantiations", "decisions", "conflicts", "propagations",
            "datatype-accessor-ax", "datatype-constructor-ax", "datatype-splits", "arith-pivots",
            "arith-conflicts", "added-eqs", "mk-clause", "restarts", "max-generation")
    return {"total_qi": total, "z3_wall": wall, "stats": {k: stats.get(k) for k in keys},
            "family_share": {k: round(v / total, 3) for k, v in fam.most_common()} if total else {},
            "top": [{"qid": q, "n": n, "share": round(n / total, 3)} for q, n in top],
            "top1_share": round(top[0][1] / total, 3) if top else 0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--task-ids", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    keep = set(a.task_ids.read_text().split())
    items = [json.loads(l) for l in a.candidates.read_text().splitlines()]
    items = [r for r in items if r["task_id"] in keep]

    def job(r):
        try:
            p = profile(Path(r["candidate_path"]).read_text())
        except subprocess.TimeoutExpired:
            p = {"timed_out": True}
        return {"task_id": r["task_id"], "candidate_sha256": r["candidate_sha256"], **p}

    with a.out.open("w") as fh, cf.ThreadPoolExecutor(a.workers) as pool:
        for rec in pool.map(job, items):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()


if __name__ == "__main__":
    main()
