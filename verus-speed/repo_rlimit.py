#!/usr/bin/env python3
"""Exact per-function Z3 resource count for a whole project (load-independent).

Runs the full-project check once with `--log smt`, then replays every module's
SMT log in Z3 with statistics after each query. Unlike seconds, the resulting
rlimit does not depend on machine load, so two versions of a repository can be
compared from one run each.

  python3 verus-speed/repo_rlimit.py nrkernel --out RUN/repo/nrkernel_rlimit_before.json
  python3 verus-speed/repo_rlimit.py nrkernel --repos RUN/repo_patched2 \
      --out RUN/repo/nrkernel_rlimit_after.json
  python3 verus-speed/repo_rlimit.py --compare BEFORE.json AFTER.json [--changed APPLY.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/proof_time"))

import fast_cost  # noqa: E402
from measure_candidates import DEFAULT_VERUS, verus_env  # noqa: E402
from repo_search import PROJECTS, REPOS  # noqa: E402


def measure(project: str, repos: Path, threads: int, timeout: int) -> dict:
    p = PROJECTS[project]
    crate = repos / p["crate"]
    with tempfile.TemporaryDirectory(prefix="vrl_") as tmp:
        cmd = [str(DEFAULT_VERUS), p["root"], *p["args"], "--rlimit", str(p["rlimit"]),
               "--num-threads", str(threads), "--log", "smt", "--log-dir", str(Path(tmp) / "lg"),
               "--output-json"]
        proc = subprocess.run(cmd, cwd=crate, env=verus_env(), capture_output=True, text=True, timeout=timeout)
        res = json.loads(proc.stdout).get("verification-results", {})
        logs = sorted((Path(tmp) / "lg").glob("*.smt2"))

        def one(log: Path) -> dict:
            script, owners = fast_cost.build_script(log.read_text(), None, {})
            return fast_cost.replay(script, owners, timeout, stop_early=False)["funcs"]

        funcs: dict = defaultdict(float)
        with ThreadPoolExecutor(threads) as pool:
            for part in pool.map(one, logs):
                for k, v in part.items():
                    funcs[k.split("::")[-1]] += v["rlimit"]
    return {"project": project, "verified": res.get("verified"), "errors": res.get("errors"),
            "logs": len(logs), "total_rlimit": sum(funcs.values()), "functions": dict(funcs)}


def compare(before: dict, after: dict, changed: set[str]) -> None:
    b, a = before["functions"], after["functions"]
    tb, ta = before["total_rlimit"], after["total_rlimit"]
    print(f"total rlimit {tb:.0f} -> {ta:.0f}  ratio {ta / tb:.3f}  "
          f"(verified {before['verified']} -> {after['verified']}, errors {before['errors']} -> {after['errors']})")
    if changed:
        cb, ca = sum(b.get(k, 0) for k in changed), sum(a.get(k, 0) for k in changed)
        ob, oa = tb - cb, ta - ca
        print(f"rewritten functions {cb:.0f} -> {ca:.0f}  ratio {ca / cb:.3f}  (share before {cb / tb:.3f})")
        print(f"other functions     {ob:.0f} -> {oa:.0f}  ratio {oa / ob:.3f}")
    moved = sorted(((a.get(k, 0) - v, k) for k, v in b.items() if k not in changed and v > 0),
                   key=lambda x: -abs(x[0]))[:5]
    print("largest changes among untouched functions:",
          [(k[:40], round(d / 1e6, 2)) for d, k in moved], "(millions of rlimit)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?", choices=sorted(PROJECTS))
    ap.add_argument("--repos", type=Path, default=REPOS)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--compare", nargs=2, type=Path)
    ap.add_argument("--changed", type=Path, help="repo_apply.py output naming the rewritten functions")
    a = ap.parse_args()
    if a.compare:
        changed = set()
        if a.changed:
            changed = {x["function"] for x in json.loads(a.changed.read_text())["applied"] if x["merged"]}
        compare(json.loads(a.compare[0].read_text()), json.loads(a.compare[1].read_text()), changed)
        return
    out = measure(a.project, a.repos, a.threads, a.timeout)
    a.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "functions"}))


if __name__ == "__main__":
    main()
