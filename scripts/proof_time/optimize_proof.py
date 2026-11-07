#!/usr/bin/env python3
"""DeepSeek proof-speed optimizer for already-verified Verus proofs.

For each task, start from a verified baseline proof and ask the model, over up
to K rounds, for search/replace edits that keep the proof verified while
lowering Z3 resource usage (rlimit-count, deterministic for a fixed seed).
Every attempt is verified with Verus and checked by proof_guard against the
original unverified task, so only proof content can change.

Optional --cards injects learned "speed cards" into the system prompt.
All attempts are logged to <out-dir>/<task>/trajectory.jsonl.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess  # noqa: F401
import tempfile
import time
import urllib.request
from pathlib import Path

from measure_candidates import DEFAULT_VERUS, verus_env
from proof_guard import check as guard_check
from smt_replay import cost as smt_cost

API = "https://api.deepseek.com/chat/completions"

SYSTEM = """You are an expert Verus (Rust + Z3) proof engineer. You are given a Verus file whose proof ALREADY VERIFIES. Your job is to make it cheaper for the SMT solver to check, measured by Z3 rlimit-count (deterministic resource usage), while keeping it verified.

Hard rules:
- Change proof content only: bodies of proof fns, proof blocks, assert/assert-by/assert-forall statements, ghost lets, loop invariants of the target, new helper proof fn lemmas, and `use`/`broadcast use` lines.
- Never change executable code, spec fn bodies, any fn signature, requires/ensures/decreases of existing fns, types, or text outside fns.
- Never add assume, admit, external_body, rlimit attributes or unsafe.

Respond with a short rationale (at most 6 lines) and then exactly one JSON code block:
```json
{"edits": [{"find": "<exact text that occurs exactly once in the current file>", "replace": "<new text>"}]}
```
`find` must be copied verbatim (including indentation) from the CURRENT file and must be unique. Use several small edits rather than one huge one."""


def call_deepseek(messages, model, effort, max_tokens=32000, retries=4):
    key = os.environ["DEEPSEEK_API_KEY"]
    body = json.dumps({"model": model, "reasoning_effort": effort, "messages": messages,
                       "max_tokens": max_tokens}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API, body, {"Authorization": f"Bearer {key}",
                                                     "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                d = json.loads(r.read())
            return d["choices"][0]["message"].get("content") or "", d.get("usage", {})
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"deepseek failed: {err}")


def verify(text: str, seed: int = 0, timeout: int = 900, verus: Path = DEFAULT_VERUS) -> dict:
    """Verify and measure exact per-function Z3 cost via SMT-log replay."""
    r = smt_cost(text, timeout=timeout, verus=verus, seed=seed)
    if r.get("timed_out"):
        return {"success": False, "timed_out": True, "stderr": "verification timed out"}
    return {"success": r["success"], "wall": r["verus_wall"], "smt_ms": round(r["replay_wall"] * 1000, 1),
            "rlimit": r["rlimit"], "qi": r["qi"],
            "functions": {k: v["rlimit"] for k, v in r["functions"].items()},
            "functions_qi": {k: v["qi"] for k, v in r["functions"].items()},
            "stderr": r["stderr"]}


def apply_edits(text: str, edits: list[dict]) -> tuple[str | None, str]:
    for i, e in enumerate(edits):
        f, r = e.get("find", ""), e.get("replace", "")
        n = text.count(f) if f else 0
        if n != 1:
            return None, f"edit {i}: find text occurs {n} times (must be exactly once)"
        text = text.replace(f, r, 1)
    return text, ""


def parse_edits(reply: str):
    m = re.findall(r"```json\s*(\{.*?\})\s*```", reply, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m[-1]).get("edits")
    except Exception:
        return None


def profile_text(res: dict, top: int = 8) -> str:
    fs = sorted(res["functions"].items(), key=lambda kv: -kv[1])[:top]
    lines = [f"  {n}: {v}" for n, v in fs]
    lines = [f"  {n}: rlimit {v:.0f}, quantifier instantiations {res.get('functions_qi', {}).get(n, 0):.0f}" for n, v in fs]
    return (f"total rlimit-count = {res['rlimit']:.0f}, total quantifier instantiations = {res.get('qi', 0):.0f}\n"
            "most expensive functions:\n" + "\n".join(lines))


def optimize_task(task: dict, args) -> dict:
    tdir = args.out_dir / task["task_id"]
    tdir.mkdir(parents=True, exist_ok=True)
    traj_path = tdir / "trajectory.jsonl"
    if (tdir / "final.json").exists():
        return json.loads((tdir / "final.json").read_text())
    source = Path(task["source_path"]).read_text()
    base = Path(task["candidate_path"]).read_text()
    base_res = verify(base)
    if not base_res["success"]:
        out = {"task_id": task["task_id"], "skipped": "baseline does not verify"}
        (tdir / "final.json").write_text(json.dumps(out))
        return out
    system = SYSTEM
    if args.cards:
        system += "\n\nLearned guidance about what makes Verus proofs cheaper to check:\n" + args.cards.read_text()
    user0 = (f"Current verified file (task {task['task_id']}):\n```rust\n{base}\n```\n\n"
             f"Baseline cost: {profile_text(base_res)}\n\nPropose edits that lower the total rlimit-count.")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user0}]
    best_text, best = base, base_res
    log = open(traj_path, "a")
    log.write(json.dumps({"round": 0, "kind": "baseline", "rlimit": base_res["rlimit"],
                          "functions": base_res["functions"], "smt_ms": base_res["smt_ms"]}) + "\n")
    usage_tot = {"prompt_tokens": 0, "completion_tokens": 0, "prompt_cache_hit_tokens": 0}
    current = last_shown = base
    for rnd in range(1, args.rounds + 1):
        reply, usage = call_deepseek(messages, args.model, args.effort)
        for k in usage_tot:
            usage_tot[k] += usage.get(k, 0) or 0
        messages.append({"role": "assistant", "content": reply})
        edits = parse_edits(reply)
        rec = {"round": rnd, "reply": reply, "usage": usage}
        if edits is None:
            fb, rec["outcome"] = "Could not parse a ```json {\"edits\": [...]}``` block. Reply again in the required format.", "parse_error"
        else:
            new, err = apply_edits(current, edits)
            if new is None:
                fb, rec["outcome"] = f"Edits not applied: {err}. Edits are applied to the CURRENT file shown last; copy find text verbatim.", "apply_error"
            else:
                g = guard_check(source, new)
                if g:
                    fb, rec["outcome"] = "Rejected by the proof-only guard: " + "; ".join(g[:5]) + ". Only proof content may change.", "guard_reject"
                else:
                    res = verify(new)
                    rec.update({"rlimit": res.get("rlimit"), "functions": res.get("functions"),
                                "smt_ms": res.get("smt_ms"), "success": res["success"]})
                    rec["candidate"] = new
                    if not res["success"]:
                        fb, rec["outcome"] = ("The edited file FAILS verification; the previous file is kept as current.\n"
                                              f"Verus output:\n{res['stderr'][-2500:]}"), "verify_fail"
                    else:
                        delta = res["rlimit"] / best["rlimit"] if best["rlimit"] else 1
                        rec["outcome"] = "improved" if res["rlimit"] < best["rlimit"] else "not_improved"
                        if res["rlimit"] < best["rlimit"]:
                            best_text, best = new, res
                        current = best_text
                        fb = (f"Edits applied and the file verifies. New cost: {profile_text(res)}\n"
                              f"Ratio to best-so-far before this round: {delta:.3f}. "
                              f"{'This is the new best and is now current.' if rec['outcome']=='improved' else 'Not an improvement; the best file remains current.'}")
        log.write(json.dumps(rec) + "\n")
        log.flush()
        if rnd < args.rounds:
            if current != last_shown:
                shown = f"\n\nCurrent file (changed):\n```rust\n{current}\n```"
                last_shown = current
            else:
                shown = "\n\nThe current file is unchanged from the last full copy shown above."
            messages.append({"role": "user", "content": fb + shown + f"\nPropose further edits (or the same idea fixed). Round {rnd + 1} of {args.rounds}."})
    # stability check of the best proof across seeds
    seeds = [verify(best_text, seed=s) for s in (1, 2)] if best_text != base else []
    out = {"task_id": task["task_id"], "baseline_rlimit": base_res["rlimit"], "best_rlimit": best["rlimit"],
           "ratio": best["rlimit"] / base_res["rlimit"] if base_res["rlimit"] else 1,
           "baseline_smt_ms": base_res["smt_ms"], "best_smt_ms": best["smt_ms"],
           "seed_check": [{"success": s["success"], "rlimit": s.get("rlimit")} for s in seeds],
           "usage": usage_tot, "cards": str(args.cards) if args.cards else None}
    (tdir / "best.rs").write_text(best_text)
    (tdir / "final.json").write_text(json.dumps(out, indent=1))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True, help="jsonl with task_id, source_path, candidate_path")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--cards", type=Path)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines()]
    if args.limit:
        tasks = tasks[: args.limit]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(args.workers) as pool:
        for out in pool.map(lambda t: optimize_task(t, args), tasks):
            print(json.dumps({k: out.get(k) for k in ("task_id", "baseline_rlimit", "best_rlimit", "ratio", "skipped")}), flush=True)


if __name__ == "__main__":
    main()
