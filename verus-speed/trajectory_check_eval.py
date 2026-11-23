#!/usr/bin/env python3
"""Run both acceptance checkers on final files of recorded agent episodes.

Each episode directory holds workspace/input.rs (the task as given),
workspace/candidate.rs (the agent's final file) and result.json (the host's
Verus verdict). No new agent runs and no new verification: the verdict comes
from result.json. Reports where VeruSAGE's check and ours disagree, which is
where real cheating or false rejections show up.

  python3 verus-speed/trajectory_check_eval.py --episodes 'STUDY/e2e_*/*/*' --out RUN/trajectory_checks.json
"""
from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import verify_proof as vp
from cheat_eval import verusage_check


def judge(ep: Path) -> dict | None:
    ws = ep / "workspace"
    try:
        orig, cand = (ws / "input.rs").read_text(), (ws / "candidate.rs").read_text()
        res = json.loads((ep / "result.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    problems = vp.structure(orig, cand)
    return {"episode": str(ep), "task_id": res.get("task_id"), "verified": bool(res.get("verified")),
            "changed": orig != cand, "verusage_accepts": verusage_check(orig, cand),
            "ours_accepts": not problems, "ours_problems": problems[:3]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", nargs="+", required=True, help="glob patterns of episode dirs")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    eps = sorted({Path(p) for pat in a.episodes for p in glob.glob(pat) if Path(p, "result.json").exists()})
    with ThreadPoolExecutor(16) as ex:
        rows = [r for r in ex.map(judge, eps) if r]
    c = Counter()
    for r in rows:
        if not r["verified"]:
            continue
        c["verified"] += 1
        c[f"verusage={'A' if r['verusage_accepts'] else 'R'} ours={'A' if r['ours_accepts'] else 'R'}"] += 1
    a.out.write_text(json.dumps({"counts": dict(c), "rows": rows}, indent=1))
    print("episodes", len(rows), dict(c))
    for r in rows:
        if r["verified"] and r["verusage_accepts"] != r["ours_accepts"]:
            print(" disagree:", r["task_id"], "verusage", r["verusage_accepts"], "ours", r["ours_accepts"],
                  r["ours_problems"][:1])


if __name__ == "__main__":
    main()
