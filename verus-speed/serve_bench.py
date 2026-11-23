#!/usr/bin/env python3
"""Cold (one process per request) versus warm (resident pool) Verus verification.

Same binary, same flags, same concurrency in both arms. Each request copies one
task file into its own temporary directory and verifies it with
`--output-json`. Reports latency percentiles, throughput, and whether every
verdict agrees between the arms.

  python3 verus-speed/serve_bench.py --tasks RUN/tasks.jsonl --out RUN/serve_bench.json \
      --concurrency 8 [--arms cold warm] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics as st
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from verus_serve import Pool, verus_env

CACHE = Path.home() / ".cache/verus-skill"
DEFAULT_RUST_VERIFY = CACHE / "src/verus-src-bb1f342/source/target-verus/release/rust_verify"
Z3 = CACHE / "toolchains/bb1f342/verus-release/z3"


def verdict(stdout: str) -> dict:
    """Last JSON object in stdout -> verification-results."""
    i = stdout.rfind('{\n  "verification-results"')
    if i < 0:
        return {}
    try:
        return json.loads(stdout[i:]).get("verification-results", {})
    except json.JSONDecodeError:
        return {}


def stage(src: Path) -> Path:
    d = Path(tempfile.mkdtemp(prefix="vsb_"))
    shutil.copy(src, d / "candidate.rs")
    return d


def run_cold(command: list[str], env: dict, src: Path, args: list[str], timeout: int) -> dict:
    d = stage(src)
    t0 = time.monotonic()
    try:
        p = subprocess.run([*command, "candidate.rs", *args], cwd=d, env=env, capture_output=True,
                           text=True, timeout=timeout)
        out, rc = p.stdout, p.returncode
    except subprocess.TimeoutExpired:
        out, rc = "", None
    wall = time.monotonic() - t0
    shutil.rmtree(d, ignore_errors=True)
    return {"wall_s": wall, "rc": rc, "res": verdict(out)}


def run_warm(pool: Pool, src: Path, args: list[str], timeout: int) -> dict:
    d = stage(src)
    r = pool.run(str(d), ["candidate.rs", *args], timeout)
    shutil.rmtree(d, ignore_errors=True)
    return {"wall_s": r["wall_s"], "rc": r.get("rc"), "res": verdict(r.get("stdout", "")),
            "crashed": r.get("crashed", False), "timed_out": r.get("timed_out", False),
            "cached": r.get("cached_response", False)}


def summarize(rows: list[dict], total_wall: float) -> dict:
    w = sorted(r["wall_s"] for r in rows)
    return {"n": len(rows), "total_wall_s": round(total_wall, 1),
            "throughput_rps": round(len(rows) / total_wall, 3),
            "median_s": round(st.median(w), 3), "p90_s": round(w[int(0.9 * (len(w) - 1))], 3),
            "mean_s": round(st.mean(w), 3),
            "pass": sum(bool(r["res"].get("success")) for r in rows),
            "no_result": sum(not r["res"] for r in rows)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--arms", nargs="+", default=["cold", "warm"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--rust-verify", type=Path, default=DEFAULT_RUST_VERIFY)
    ap.add_argument("--toolchain", default="1.88.0-x86_64-unknown-linux-gnu")
    ap.add_argument("--args", nargs="*", default=["--output-json", "--num-threads", "1"])
    a = ap.parse_args()
    tasks = [json.loads(l) for p in a.tasks for l in p.read_text().splitlines() if l.strip()]
    if a.limit:
        tasks = tasks[: a.limit]
    command = ["rustup", "run", a.toolchain, str(a.rust_verify)]
    env = verus_env({"VERUS_Z3_PATH": str(Z3)})
    cold_env = dict(env)
    cold_env.pop("VERUS_IMPORT_CACHE", None)
    results: dict = {"tasks": len(tasks), "concurrency": a.concurrency, "arms": {}}
    rows: dict = {}
    for arm in a.arms:
        start = time.monotonic()
        if arm == "cold":
            with ThreadPoolExecutor(a.concurrency) as ex:
                rows[arm] = list(ex.map(lambda t: run_cold(command, cold_env, Path(t["candidate_path"]),
                                                           a.args, a.timeout), tasks))
        else:
            pool = Pool(command, size=a.concurrency, env={"VERUS_Z3_PATH": str(Z3)})
            with ThreadPoolExecutor(a.concurrency) as ex:
                rows[arm] = list(ex.map(lambda t: run_warm(pool, Path(t["candidate_path"]), a.args,
                                                           a.timeout), tasks))
            pool.close()
        results["arms"][arm] = summarize(rows[arm], time.monotonic() - start)
        print(arm, json.dumps(results["arms"][arm]), flush=True)
    if "cold" in rows and "warm" in rows:
        mism = [t["task_id"] for t, c, w in zip(tasks, rows["cold"], rows["warm"])
                if bool(c["res"].get("success")) != bool(w["res"].get("success"))]
        results["verdict_mismatch"] = len(mism)
        results["mismatched_tasks"] = mism[:20]
        results["warm_crashes"] = sum(r.get("crashed", False) for r in rows["warm"])
        print(json.dumps({k: results[k] for k in ("verdict_mismatch", "warm_crashes")}))
    results["rows"] = {arm: [{"task_id": t["task_id"], **r} for t, r in zip(tasks, rs)]
                       for arm, rs in rows.items()}
    a.out.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
