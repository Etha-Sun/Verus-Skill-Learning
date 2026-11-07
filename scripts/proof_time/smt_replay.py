#!/usr/bin/env python3
"""Exact per-function Z3 cost by replaying Verus SMT logs.

Verus (0.2025.09.12) refreshes Z3 statistics *before* each query, so its
reported per-function `rlimit-count` lags by one query and never counts the
final query of a context (including every spinoff_prover function). This tool
runs Verus with `--log smt`, inserts `(get-info :all-statistics)` after every
`(check-sat)`, replays each log in the bundled Z3, and attributes the exact
rlimit / quantifier-instantiation deltas to the enclosing `;; Function-Def`.

Usage as a library: cost(text) -> dict; or CLI: smt_replay.py file.rs
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from measure_candidates import DEFAULT_VERUS, verus_env

Z3 = DEFAULT_VERUS.parent / "z3"
STAT_RE = re.compile(r":(rlimit-count|quant-instantiations|time)\s+([0-9.]+)")


def run_group(cmd, timeout, **kw):
    """subprocess.run that kills the whole process group (Verus spawns Z3) on timeout."""
    import os
    import signal
    p = subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE if "input" in kw else None, text=True,
                         cwd=kw.get("cwd"), env=kw.get("env"))
    try:
        out, err = p.communicate(kw.get("input"), timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        raise
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def replay_log(path: Path, timeout: int) -> dict:
    lines = path.read_text().splitlines()
    out_lines, owners = [], []
    owner = None
    for ln in lines:
        if ln.strip().startswith("(get-info"):
            continue  # Verus's own pre-query statistics requests; keep only ours
        m = re.match(r";; Function-Def (\S+)", ln)
        if m:
            owner = m.group(1)
        out_lines.append(ln)
        if ln.strip() == "(check-sat)":
            out_lines.append("(get-info :all-statistics)")
            owners.append(owner)
    script = "\n".join(out_lines) + "\n"
    t0 = time.monotonic()
    proc = run_group([str(Z3), "-in"], timeout, input=script)
    wall = time.monotonic() - t0
    # statistics blocks appear in order, one per check-sat
    blocks = re.split(r"\n(?=\(:)", proc.stdout)
    stats = []
    for b in blocks:
        d = dict((k, float(v)) for k, v in STAT_RE.findall(b))
        if "rlimit-count" in d:
            stats.append(d)
    results = re.findall(r"^(sat|unsat|unknown)$", proc.stdout, flags=re.M)
    funcs = defaultdict(lambda: {"rlimit": 0.0, "qi": 0.0, "queries": 0})
    prev_r = prev_q = 0.0
    for own, st in zip(owners, stats):
        f = funcs[own or "<none>"]
        f["rlimit"] += st["rlimit-count"] - prev_r
        f["qi"] += st.get("quant-instantiations", 0) - prev_q
        f["queries"] += 1
        prev_r, prev_q = st["rlimit-count"], st.get("quant-instantiations", 0)
    return {"funcs": dict(funcs), "wall": wall, "queries": len(owners),
            "stats_parsed": len(stats), "results": results}


def cost(text: str, timeout: int = 900, verus: Path = DEFAULT_VERUS, seed: int = 0) -> dict:
    with tempfile.TemporaryDirectory(prefix="smtr-") as tmp:
        p = Path(tmp) / "candidate.rs"
        p.write_text(text)
        cmd = [str(verus), "candidate.rs", "--log", "smt", "--log-dir", "lg",
               "--smt-option", f"smt.random_seed={seed}", "--output-json"]
        t0 = time.monotonic()
        try:
            proc = run_group(cmd, timeout, cwd=tmp, env=verus_env())
        except subprocess.TimeoutExpired:
            return {"success": False, "timed_out": True}
        vwall = time.monotonic() - t0
        try:
            vr = json.loads(proc.stdout).get("verification-results", {})
            success = bool(vr.get("success"))
        except Exception:
            success = False
        funcs = defaultdict(lambda: {"rlimit": 0.0, "qi": 0.0, "queries": 0})
        replay_wall, nq = 0.0, 0
        for log in sorted((Path(tmp) / "lg").glob("*.smt2")):
            try:
                r = replay_log(log, timeout)
            except subprocess.TimeoutExpired:
                return {"success": False, "timed_out": True}
            replay_wall += r["wall"]
            nq += r["queries"]
            for k, v in r["funcs"].items():
                for kk in ("rlimit", "qi", "queries"):
                    funcs[k][kk] += v[kk]
    total = sum(v["rlimit"] for v in funcs.values())
    return {"success": success, "verus_wall": vwall, "replay_wall": replay_wall, "queries": nq,
            "rlimit": total, "qi": sum(v["qi"] for v in funcs.values()),
            "functions": {k.split("::", 1)[-1]: v for k, v in funcs.items()},
            "stderr": re.sub(r"/tmp/smtr-\w+/", "", proc.stderr)[-3000:]}


if __name__ == "__main__":
    r = cost(Path(sys.argv[1]).read_text())
    top = sorted(r["functions"].items(), key=lambda kv: -kv[1]["rlimit"])[:10]
    print(json.dumps({k: v for k, v in r.items() if k not in ("functions", "stderr")}, indent=1))
    for k, v in top:
        print(f"{v['rlimit']:>12.0f} rl {v['qi']:>9.0f} qi {v['queries']:>3} q  {k}")
