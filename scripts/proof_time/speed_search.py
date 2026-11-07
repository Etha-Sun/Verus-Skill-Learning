#!/usr/bin/env python3
"""Search-based proof-speed post-processor (no LLM).

Phase 1 (singles): every one-change variant in the proof region
  (delete one assert / assert-by / assert-forall / reveal, delete one
  `broadcast use`, add #[verifier::spinoff_prover] to one region fn) is
  verified and costed (exact SMT-replay rlimit). These are clean
  single-factor contrast pairs.
Phase 2 (greedy): beneficial singles are applied cumulatively, best first;
  each step is kept only if the proof still verifies and cost decreases.
Phase 3 (confirm): the final proof must verify on seeds 1 and 2.

Proof region: the benchmark target fn, plus (for LLM proofs) every fn whose
body differs from the original task or that the proof added.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
from pathlib import Path

from optimize_proof import verify
from proof_guard import check as guard_check, items, strip_comments
from prune_proof import assert_spans


def region_fns(text: str, source: str | None, target: str) -> set[str]:
    names = {target}
    if source is not None:
        src = {(it[0], " ".join(it[3].split())) for it in items(strip_comments(source))}
        names |= {it[0] for it in items(text) if (it[0], " ".join(it[3].split())) not in src}
    return names


def variants(text: str, names: set[str], cap: int = 60):
    out = []
    for it in items(text):
        if it[0] not in names:
            continue
        for s, e in assert_spans(text, [(it[4], it[5])])[:cap]:
            stmt = text[s:e]
            kind = ("del_assert_forall" if re.match(r"\s*assert\s+forall", stmt) else
                    "del_assert_by" if re.search(r"\)\s*by\s*(\(|\{)", stmt) else "del_assert")
            out.append({"kind": kind, "fn": it[0], "stmt": stmt.strip(), "text": text[:s] + text[e:]})
        for m in re.finditer(r"(?m)^[ \t]*reveal(_with_fuel)?\s*\([^;]*\);\s*$", text[it[4]:it[5]]):
            s, e = it[4] + m.start(), it[4] + m.end()
            out.append({"kind": "del_reveal", "fn": it[0], "stmt": text[s:e].strip(), "text": text[:s] + text[e:]})
        if "spinoff_prover" not in text[max(0, it[4] - 200): it[4] + 200]:
            out.append({"kind": "add_spinoff", "fn": it[0], "stmt": f"#[verifier::spinoff_prover] {it[0]}",
                        "text": text[:it[4]] + "#[verifier::spinoff_prover]\n" + text[it[4]:]})
    for m in re.finditer(r"(?m)^[ \t]*broadcast\s+use\s[^;]*;\s*$", text):
        out.append({"kind": "del_broadcast_use", "fn": None, "stmt": m.group(0).strip(),
                    "text": text[:m.start()] + text[m.end():]})
    return out


def key(v):
    return (v["kind"], v["fn"], " ".join(v["stmt"].split()))


def search(task: dict, a) -> dict:
    tdir = a.out_dir / task.get("key", task["task_id"])
    tdir.mkdir(parents=True, exist_ok=True)
    if (tdir / "final.json").exists():
        return json.loads((tdir / "final.json").read_text())
    text = strip_comments(Path(task["candidate_path"]).read_text())
    source = Path(task["source_path"]).read_text() if task.get("source_path") else None
    names = region_fns(text, source, task["target_function"])
    tmo = task.get("timeout", 900)
    base = verify(text, timeout=tmo)
    if not base["success"]:
        out = {"task_id": task["task_id"], "skipped": "baseline does not verify"}
        (tdir / "final.json").write_text(json.dumps(out))
        return out
    # phase 1: singles (parallel within task)
    vs = variants(text, names)
    with cf.ThreadPoolExecutor(a.inner_workers) as pool:
        res = list(pool.map(lambda v: verify(v["text"], timeout=tmo), vs))
    singles = []
    for v, r in zip(vs, res):
        ok_guard = (not source) or not guard_check(source, v["text"])
        singles.append({"kind": v["kind"], "fn": v["fn"], "stmt": v["stmt"][:2000],
                        "success": r["success"] and ok_guard, "timed_out": r.get("timed_out", False),
                        "rlimit": r.get("rlimit"), "qi": r.get("qi"),
                        "ratio": r["rlimit"] / base["rlimit"] if r["success"] and base["rlimit"] else None})
    with (tdir / "singles.jsonl").open("w") as fh:
        for s in singles:
            fh.write(json.dumps(s) + "\n")
    # phase 2: greedy combination, best single first
    good = sorted([s for s in singles if s["success"] and s["ratio"] is not None and s["ratio"] < 0.995],
                  key=lambda s: s["ratio"])
    cur, cur_res, applied = text, base, []
    for s in good:
        k = (s["kind"], s["fn"], " ".join(s["stmt"].split()))
        match = [v for v in variants(cur, names) if key(v) == k]
        if len(match) != 1:
            continue
        r = verify(match[0]["text"], timeout=tmo)
        if r["success"] and r["rlimit"] < cur_res["rlimit"] and ((not source) or not guard_check(source, match[0]["text"])):
            cur, cur_res = match[0]["text"], r
            applied.append({"kind": s["kind"], "stmt": s["stmt"][:300], "single_ratio": s["ratio"],
                            "cum_ratio": r["rlimit"] / base["rlimit"]})
    # phase 3: confirm on other seeds
    seeds_ok = all(verify(cur, seed=sd, timeout=tmo)["success"] for sd in (1, 2)) if applied else True
    (tdir / "best.rs").write_text(cur)
    out = {"task_id": task["task_id"], "key": task.get("key"), "baseline_rlimit": base["rlimit"], "best_rlimit": cur_res["rlimit"],
           "ratio": cur_res["rlimit"] / base["rlimit"], "n_singles": len(singles),
           "n_beneficial_singles": len(good), "applied": applied, "seeds_ok": seeds_ok,
           "best_single_ratio": good[0]["ratio"] if good else 1.0}
    (tdir / "final.json").write_text(json.dumps(out, indent=1))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True,
                    help="jsonl: task_id, candidate_path, target_function, [source_path], [timeout]")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8, help="tasks in parallel")
    ap.add_argument("--inner-workers", type=int, default=8, help="singles in parallel per task")
    a = ap.parse_args()
    tasks = [json.loads(l) for l in a.tasks.read_text().splitlines()]
    a.out_dir.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(a.workers) as pool:
        for out in pool.map(lambda t: search(t, a), tasks):
            print(json.dumps({k: out.get(k) for k in ("task_id", "ratio", "n_beneficial_singles", "seeds_ok", "skipped")}), flush=True)


if __name__ == "__main__":
    main()
