#!/usr/bin/env python3
"""One-solve exact cost for search candidates, with an optional cost cap.

`scripts/proof_time/smt_replay.py` solves every candidate twice: Verus solves
it for the verdict, then the SMT log is replayed in Z3 for exact statistics.
Here Verus runs with a resource limit so small that it gives up at once; its
SMT log is still identical to a normal run except for the limit value. The
replay restores the real limit and yields both the verdict and the cost.

With `cap`, each query's limit is lowered to `cap` and the replay stops at the
first query that does not return `unsat`. A candidate that exceeds the cap on
one query cannot be cheaper than `cap` in total, so a search loses nothing.

`#[verifier::rlimit(n)]` attributes are swapped for tiny marker values in the
logging pass and restored in the replay. Files using `by (compute)` fall back
to the two-solve path, because the compute interpreter obeys the same limit.

This is a filter for search loops, not a verifier: results that matter must be
confirmed by a normal Verus run.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/proof_time"))

from measure_candidates import DEFAULT_VERUS, verus_env  # noqa: E402
from smt_replay import STAT_RE, Z3, cost as two_solve_cost, run_group  # noqa: E402

TINY = 0.00001            # --rlimit for the logging pass
TINY_UNITS = 30           # what Verus writes for it: TINY * 3,000,000
DEFAULT_UNITS = 30_000_000  # Verus default --rlimit 10
UNITS_PER_RLIMIT = 3_000_000
RLIMIT_LINE = re.compile(r"^(\s*)\(set-option :rlimit (\d+)\)\s*$")
RLIMIT_ATTR = re.compile(r"(verifier::rlimit\(|verifier\(rlimit\()\s*([0-9.]+)\s*\)")
COMPUTE = re.compile(r"by\s*\(\s*compute")


def mark_rlimit_attrs(text: str) -> tuple[str, dict[int, int]]:
    """Replace each `#[verifier::rlimit(n)]` by a distinct tiny value so Verus
    gives up at once; returns the text and marker index -> real limit units."""
    real: dict[int, int] = {1: DEFAULT_UNITS}

    def sub(m: re.Match) -> str:
        k = len(real) + 1
        real[k] = round(float(m.group(2)) * UNITS_PER_RLIMIT)
        return f"{m.group(1)}{k * TINY:.5f})"

    return RLIMIT_ATTR.sub(sub, text), real


def build_script(log_text: str, cap: float | None,
                 real: dict[int, int] | None = None) -> tuple[str, list[str | None]]:
    real = real or {1: DEFAULT_UNITS}
    out, owners, owner = [], [], None
    for ln in log_text.splitlines():
        s = ln.strip()
        if s.startswith("(get-info"):
            continue
        m = re.match(r";; Function-Def (\S+)", ln)
        if m:
            owner = m.group(1)
        m = RLIMIT_LINE.match(ln)
        if m and int(m.group(2)) > 0:
            units = int(m.group(2))
            if units < 100_000:  # a marker: k * TINY_UNITS, up to float rounding
                units = real.get(round(units / TINY_UNITS), DEFAULT_UNITS)
            if cap is not None:
                units = max(1, min(units, int(cap)))
            ln = f"{m.group(1)}(set-option :rlimit {units})"
        out.append(ln)
        if s == "(check-sat)":
            out.append("(get-info :all-statistics)")
            owners.append(owner)
    return "\n".join(out) + "\n", owners


def replay(script: str, owners: list, timeout: float, stop_early: bool) -> dict:
    """Run Z3 on the script; with stop_early, kill it at the first non-unsat answer."""
    with tempfile.NamedTemporaryFile("w", suffix=".smt2", delete=False) as fh:
        fh.write(script)
        path = fh.name
    t0 = time.monotonic()
    p = subprocess.Popen([str(Z3), path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, start_new_session=True)
    lines, stopped, expired = [], False, threading.Event()

    def kill() -> None:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def on_timeout() -> None:
        expired.set()
        kill()

    timer = threading.Timer(timeout, on_timeout)
    timer.start()
    try:
        for ln in p.stdout:  # type: ignore[union-attr]
            lines.append(ln)
            if stop_early and ln.strip() in ("unknown", "sat"):
                stopped = True
                break
    finally:
        timer.cancel()
        if p.poll() is None:
            kill()
        p.wait()
        os.unlink(path)
    timed_out = expired.is_set()
    text = "".join(lines)
    results = re.findall(r"^(sat|unsat|unknown)$", text, flags=re.M)
    stats = []
    for b in re.split(r"\n(?=\(:)", text):
        d = dict((k, float(v)) for k, v in STAT_RE.findall(b))
        if "rlimit-count" in d:
            stats.append(d)
    funcs = defaultdict(lambda: {"rlimit": 0.0, "qi": 0.0, "queries": 0})
    prev_r = prev_q = 0.0
    for own, st in zip(owners, stats):
        f = funcs[own or "<none>"]
        f["rlimit"] += st["rlimit-count"] - prev_r
        f["qi"] += st.get("quant-instantiations", 0) - prev_q
        f["queries"] += 1
        prev_r, prev_q = st["rlimit-count"], st.get("quant-instantiations", 0)
    ok = (not stopped and not timed_out and len(results) == len(owners)
          and all(r == "unsat" for r in results))
    return {"funcs": dict(funcs), "wall": time.monotonic() - t0, "ok": ok,
            "stopped": stopped, "timed_out": timed_out, "queries": len(owners)}


def cost(text: str, timeout: int = 900, verus: Path = DEFAULT_VERUS, seed: int = 0,
         cap: float | None = None) -> dict:
    """Same shape as smt_replay.cost, plus `capped` (stopped at the cap or a failing query)."""
    if COMPUTE.search(text):
        # `by (compute)` is bounded by the same limit, so the logging pass would fail.
        return {**two_solve_cost(text, timeout=timeout, verus=verus, seed=seed), "capped": False}
    marked, real = mark_rlimit_attrs(text)
    with tempfile.TemporaryDirectory(prefix="fastc-") as tmp:
        (Path(tmp) / "candidate.rs").write_text(marked)
        cmd = [str(verus), "candidate.rs", "--log", "smt", "--log-dir", "lg",
               "--rlimit", str(TINY), "--multiple-errors", "0", "--no-auto-recommends-check",
               "--smt-option", f"smt.random_seed={seed}", "--output-json"]
        t0 = time.monotonic()
        try:
            proc = run_group(cmd, timeout, cwd=tmp, env=verus_env())
        except subprocess.TimeoutExpired:
            return {"success": False, "timed_out": True}
        vwall = time.monotonic() - t0
        try:
            vr = json.loads(proc.stdout).get("verification-results", {})
        except Exception:
            vr = {"encountered-vir-error": True}
        reached_smt = (not vr.get("encountered-vir-error")
                       and (vr.get("verified") or 0) + (vr.get("errors") or 0) > 0)
        funcs = defaultdict(lambda: {"rlimit": 0.0, "qi": 0.0, "queries": 0})
        ok, capped, replay_wall, nq = reached_smt, False, 0.0, 0
        logs = sorted((Path(tmp) / "lg").glob("*.smt2")) if reached_smt else []
        for log in logs:
            script, owners = build_script(log.read_text(), cap, real)
            r = replay(script, owners, timeout, stop_early=True)
            replay_wall += r["wall"]
            nq += r["queries"]
            for k, v in r["funcs"].items():
                for kk in ("rlimit", "qi", "queries"):
                    funcs[k][kk] += v[kk]
            if r["timed_out"]:
                return {"success": False, "timed_out": True}
            if not r["ok"]:
                ok, capped = False, True
                break
    return {"success": ok and bool(logs), "capped": capped, "verus_wall": vwall,
            "replay_wall": replay_wall, "queries": nq,
            "rlimit": sum(v["rlimit"] for v in funcs.values()),
            "qi": sum(v["qi"] for v in funcs.values()),
            "functions": {k.split("::", 1)[-1]: v for k, v in funcs.items()},
            "stderr": re.sub(r"/tmp/fastc-\w+/", "", proc.stderr)[-3000:]}


def verify(text: str, seed: int = 0, timeout: int = 900, cap: float | None = None) -> dict:
    """Drop-in for optimize_proof.verify."""
    r = cost(text, timeout=timeout, seed=seed, cap=cap)
    if r.get("timed_out"):
        return {"success": False, "timed_out": True, "stderr": "verification timed out"}
    return {"success": r["success"], "wall": r["verus_wall"], "smt_ms": round(r["replay_wall"] * 1000, 1),
            "rlimit": r["rlimit"], "qi": r["qi"],
            "functions": {k: v["rlimit"] for k, v in r["functions"].items()},
            "functions_qi": {k: v["qi"] for k, v in r["functions"].items()},
            "stderr": r["stderr"]}


if __name__ == "__main__":
    r = cost(Path(sys.argv[1]).read_text(), cap=float(sys.argv[2]) if len(sys.argv) > 2 else None)
    print(json.dumps({k: v for k, v in r.items() if k not in ("functions", "stderr")}, indent=1))
