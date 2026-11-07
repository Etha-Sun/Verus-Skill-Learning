#!/usr/bin/env python3
"""In-trajectory verifier time: every Verus call an agent made, from its events.

Pairs item.started / item.completed command_execution events whose command
invokes Verus, and records duration, pass/fail (from the verification summary)
and error count. Reports per-call and per-episode statistics, split by
pass/fail, and the share of episode wall time spent waiting on the verifier.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# an actual invocation: run_verus.sh <file> or a verus binary followed by a .rs file
VERUS_CMD = re.compile(r"run_verus\.sh\s+\S+\.rs|(^|[\s/'\"])verus\s+[^|;]*\.rs")
NOT_CALL = re.compile(r"^\s*/bin/bash -lc '\s*(cat|sed|grep|head|tail|less|wc|ls)\b")
SUMMARY = re.compile(r"verification results::\s*(\d+) verified,\s*(\d+) errors?")


def ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def episode_calls(events: Path):
    started, calls = {}, []
    first = last = None
    for l in events.read_text().splitlines():
        try:
            e = json.loads(l)
        except Exception:
            continue
        t = ts(e["timestamp"])
        first = t if first is None else first
        last = t
        raw = (e.get("data") or {}).get("raw_codex_event") or {}
        item = raw.get("item") or {}
        if item.get("type") != "command_execution":
            continue
        cmd = item.get("command", "")
        if not VERUS_CMD.search(cmd) or NOT_CALL.search(cmd):
            continue
        if raw.get("type") == "item.started":
            started[item["id"]] = t
        elif raw.get("type") == "item.completed" and item["id"] in started:
            out = item.get("aggregated_output") or ""
            m = SUMMARY.search(out)
            if m:
                status = "pass" if int(m.group(2)) == 0 else "fail"
                errs = int(m.group(2))
            elif "rustup not found" in out or "command not found" in out:
                status, errs = "env_error", None
            elif re.search(r"^error(\[E\d+\])?:", out, flags=re.M):
                status, errs = "fail_before_smt", None  # parse/type/mode error: no SMT summary
            else:
                status, errs = "summary_truncated", None
            calls.append({"dur": t - started.pop(item["id"]), "status": status, "errors": errs,
                          "exit_code": item.get("exit_code")})
    return calls, (last - first) if first is not None else None


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    eps = []
    for root in a.roots:
        for ev in sorted(root.rglob("agent_events.jsonl")):
            calls, wall = episode_calls(ev)
            if not calls:
                continue
            task = None
            try:
                task = json.loads((ev.parent / "run_manifest.json").read_text()).get("source_sha256")
            except Exception:
                pass
            res = {}
            try:
                res = json.loads((ev.parent / "result.json").read_text())
            except Exception:
                pass
            eps.append({"episode": str(ev.parent.relative_to(root.parent)), "source_sha256": task,
                        "solved": res.get("proof_solved"), "episode_wall": wall, "calls": calls})
    by = defaultdict(list)
    for e in eps:
        for c in e["calls"]:
            by[c["status"]].append(c["dur"])
    per_call = {k: {"n": len(v), "median_s": round(st.median(v), 2), "p90_s": round(q(v, .9), 2),
                    "max_s": round(max(v), 1), "total_s": round(sum(v))} for k, v in by.items()}
    # paired within task: fail vs pass call duration
    task_pf = defaultdict(lambda: defaultdict(list))
    for e in eps:
        for c in e["calls"]:
            if c["status"] in ("pass", "fail"):
                task_pf[e["source_sha256"]][c["status"]].append(c["dur"])
    ratios = [st.median(d["fail"]) / st.median(d["pass"]) for d in task_pf.values()
              if d["fail"] and d["pass"] and st.median(d["pass"]) > 0]
    shares = [sum(c["dur"] for c in e["calls"]) / e["episode_wall"] for e in eps if e["episode_wall"]]
    ncalls = [len(e["calls"]) for e in eps]
    fail_share = [sum(c["dur"] for c in e["calls"] if c["status"] != "pass") /
                  max(sum(c["dur"] for c in e["calls"]), 1e-9) for e in eps]
    summary = {
        "episodes": len(eps), "verifier_calls": sum(ncalls),
        "calls_per_episode_median": st.median(ncalls), "calls_per_episode_p90": q(ncalls, .9),
        "per_call_by_status": per_call,
        "within_task_fail_over_pass_median_duration": {
            "tasks": len(ratios), "median_ratio": round(st.median(ratios), 3) if ratios else None,
            "p10": round(q(ratios, .1), 3) if ratios else None, "p90": round(q(ratios, .9), 3) if ratios else None},
        "verifier_share_of_episode_wall": {"median": round(st.median(shares), 3), "p90": round(q(shares, .9), 3)},
        "share_of_verifier_time_on_non_passing_calls_median": round(st.median(fail_share), 3),
        "episode_verifier_seconds": {"median": round(st.median(sum(c['dur'] for c in e['calls']) for e in eps), 1),
                                     "p90": round(q([sum(c['dur'] for c in e['calls']) for e in eps], .9), 1)},
    }
    a.out.write_text(json.dumps({"summary": summary, "episodes": eps}))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
