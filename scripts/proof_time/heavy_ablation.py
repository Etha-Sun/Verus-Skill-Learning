#!/usr/bin/env python3
"""Single-factor ablations inside the target function of heavy proofs.

For each heavy task's human proof, create variants that each change exactly
one thing in the target function:
  del_assert / del_assert_by / del_assert_forall   delete one assert statement
  del_reveal          delete one reveal(...) / reveal_with_fuel(...) statement
  del_broadcast_use   delete one `broadcast use ...;` line (anywhere in file)
  add_spinoff         add #[verifier::spinoff_prover] to the target function
Each variant is verified and its exact Z3 cost measured (SMT replay).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

from optimize_proof import verify
from proof_guard import items, strip_comments
from prune_proof import assert_spans


def variants(text: str, target: str, cap: int):
    its = [it for it in items(text) if it[0] == target]
    if not its:
        return []
    out = []
    for it in its[:1]:
        region = [(it[4], it[5])]
        for s, e in assert_spans(text, region)[:cap]:
            stmt = text[s:e]
            kind = ("del_assert_forall" if re.match(r"\s*assert\s+forall", stmt) else
                    "del_assert_by" if re.search(r"\)\s*by\s*(\(|\{)", stmt) else "del_assert")
            out.append((kind, stmt.strip()[:300], text[:s] + text[e:]))
        for m in re.finditer(r"(?m)^[ \t]*reveal(_with_fuel)?\s*\([^;]*\);\s*$", text[it[4]:it[5]]):
            s, e = it[4] + m.start(), it[4] + m.end()
            out.append(("del_reveal", text[s:e].strip(), text[:s] + text[e:]))
        out.append(("add_spinoff", "#[verifier::spinoff_prover]",
                    text[:it[4]] + "#[verifier::spinoff_prover]\n" + text[it[4]:]))
    for m in re.finditer(r"(?m)^[ \t]*broadcast\s+use\s[^;]*;\s*$", text):
        out.append(("del_broadcast_use", m.group(0).strip()[:300], text[:m.start()] + text[m.end():]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--task-ids", type=Path, required=True)
    ap.add_argument("--bench-tasks", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cap", type=int, default=40, help="max assert variants per task")
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--measurements", type=Path, required=True,
                    help="human-gt measurements.jsonl, for per-task baseline wall time")
    ap.add_argument("--timeout-factor", type=float, default=4.0)
    a = ap.parse_args()
    keep = set(a.task_ids.read_text().split())
    bench = {json.loads(l)["task_id"]: json.loads(l) for l in a.bench_tasks.read_text().splitlines()}
    walls = defaultdict(list)
    for l in a.measurements.read_text().splitlines():
        m = json.loads(l)
        if m.get("success"):
            walls[m["candidate_sha256"]].append(m["wall_seconds"])
    jobs, bases, tmo = [], {}, {}
    for l in a.candidates.read_text().splitlines():
        r = json.loads(l)
        if r["task_id"] not in keep:
            continue
        text = strip_comments(Path(r["candidate_path"]).read_text())
        bases[r["task_id"]] = text
        w = st.median(walls[r["candidate_sha256"]]) if walls[r["candidate_sha256"]] else 60
        tmo[r["task_id"]] = int(max(60, a.timeout_factor * w))
        jobs.append((r["task_id"], "baseline", "", text))
        for kind, stmt, v in variants(text, bench[r["task_id"]]["target_function"], a.cap):
            jobs.append((r["task_id"], kind, stmt, v))
    print(len(jobs), "verifications over", len(bases), "tasks", flush=True)

    def run(j):
        t, kind, stmt, text = j
        res = verify(text, timeout=tmo[t])
        return {"task_id": t, "kind": kind, "stmt": stmt, "success": res["success"],
                "rlimit": res.get("rlimit"), "qi": res.get("qi"), "smt_ms": res.get("smt_ms"),
                "timed_out": res.get("timed_out", False), "timeout_s": tmo[t]}

    with a.out.open("w") as fh, cf.ThreadPoolExecutor(a.workers) as pool:
        for i, rec in enumerate(pool.map(run, jobs), 1):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            if i % 100 == 0:
                print(i, flush=True)


if __name__ == "__main__":
    main()
