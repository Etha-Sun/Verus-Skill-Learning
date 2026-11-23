#!/usr/bin/env python3
"""Verus compile/verify baseline with per-phase breakdown.

Runs each verified source under one or more named flag configurations and
records wall time, child CPU time and the phase times Verus reports with
`--time-expanded --output-json`. Outputs go to --out (outside the repository).

Example:
  python3 verus-speed/baseline.py --tasks TASKS.jsonl --out RUN/baseline.jsonl \
      --configs default no_lifetime --repeats 3 --workers 12
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

CACHE = Path.home() / ".cache/verus-skill"
DEFAULT_VERUS = CACHE / "toolchains/bb1f342/verus-release/verus"

# Named flag sets. "sound" marks configurations whose verdict equals a full check.
CONFIGS = {
    "default": {"flags": [], "sound": True},
    "threads1": {"flags": ["--num-threads", "1"], "sound": True},
    "no_lifetime": {"flags": ["--no-lifetime"], "sound": False},
    "spinoff_all": {"flags": ["-V", "spinoff-all"], "sound": True},
    "one_error": {"flags": ["--multiple-errors", "0"], "sound": True},
    "no_recommends": {"flags": ["--no-auto-recommends-check"], "sound": True},
    "fail_fast": {"flags": ["--multiple-errors", "0", "--no-auto-recommends-check"], "sound": True},
    "no_verify": {"flags": ["--no-verify"], "sound": False},
    "frontend_only": {"flags": ["--no-verify", "--no-lifetime"], "sound": False},
}


def verus_env() -> dict:
    env = dict(os.environ)
    env["RUSTUP_HOME"] = str(CACHE / "rustup")
    env["CARGO_HOME"] = str(CACHE / "cargo")
    env["PATH"] = f"{CACHE / 'cargo/bin'}:{env.get('PATH', '')}"
    return env


def phases(doc: dict) -> dict:
    t = doc.get("times-ms") or {}
    rust = t.get("rust") or {}
    vir = (t.get("verification") or {}).get("vir") or {}
    smt = t.get("smt") or {}
    funcs = []
    for mod in smt.get("smt-run-module-times") or []:
        for f in mod.get("function-breakdown") or []:
            funcs.append({"function": f.get("function"), "micros": f.get("time-micros", 0)})
    return {
        "total_ms": t.get("total"),
        "cpu_ms": t.get("estimated-cpu-time"),
        "num_threads": t.get("num-threads"),
        "rust_init_ms": rust.get("init-and-types"),
        "rust_lifetime_ms": rust.get("lifetime"),
        "rust_compile_ms": rust.get("compile"),
        "vir_import_ms": vir.get("import"),
        "vir_other_ms": (vir.get("total") or 0) - (vir.get("import") or 0),
        "air_ms": (t.get("air") or {}).get("total"),
        "smt_init_ms": smt.get("smt-init"),
        "smt_run_ms": smt.get("smt-run"),
        "functions": funcs,
    }


def run_once(verus: Path, src: Path, flags: list[str], timeout: int) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="vspeed_"))
    try:
        shutil.copy(src, tmp / "candidate.rs")
        cmd = [str(verus), "candidate.rs", "--time-expanded", "--output-json", *flags]
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        start = time.perf_counter()
        try:
            proc = subprocess.run(cmd, cwd=tmp, env=verus_env(), capture_output=True,
                                  text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"timed_out": True, "wall_seconds": time.perf_counter() - start}
        wall = time.perf_counter() - start
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        rec = {"timed_out": False, "returncode": proc.returncode, "wall_seconds": wall}
        try:
            doc = json.loads(proc.stdout)
        except json.JSONDecodeError:
            rec["parse_error"] = proc.stderr[-400:]
            return rec
        res = doc.get("verification-results") or {}
        rec.update(verified=res.get("verified"), errors=res.get("errors"),
                   success=bool(res.get("success")), **phases(doc))
        # Child CPU is process-wide, so it is only meaningful with --workers 1.
        rec["child_cpu_seconds"] = (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime)
        return rec
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True,
                    help="jsonl with task_id and candidate_path (a verified .rs file)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--configs", nargs="+", default=["default"], choices=sorted(CONFIGS))
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--verus", type=Path, default=DEFAULT_VERUS)
    args = ap.parse_args()

    tasks = [json.loads(line) for line in args.tasks.read_text().splitlines() if line.strip()]
    if args.limit:
        tasks = tasks[: args.limit]
    done = set()
    if args.out.exists():
        for line in args.out.read_text().splitlines():
            r = json.loads(line)
            done.add((r["task_id"], r["config"], r["repeat"]))
    jobs = [(t, c, i) for i in range(args.repeats) for c in args.configs for t in tasks
            if (t["task_id"], c, i) not in done]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("a") as out, ThreadPoolExecutor(args.workers) as pool:
        futs = {pool.submit(run_once, args.verus, Path(t["candidate_path"]),
                            CONFIGS[c]["flags"], args.timeout): (t, c, i) for t, c, i in jobs}
        for n, fut in enumerate(as_completed(futs), 1):
            t, c, i = futs[fut]
            rec = {"task_id": t["task_id"], "config": c, "repeat": i, **fut.result()}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            if n % 200 == 0:
                print(f"{n}/{len(jobs)}", flush=True)


if __name__ == "__main__":
    main()
