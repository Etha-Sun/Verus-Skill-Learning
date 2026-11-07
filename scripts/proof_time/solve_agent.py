#!/usr/bin/env python3
"""Lightweight end-to-end DeepSeek proof-solving loop for controlled A/B tests.

Each episode: the model sees TASK + condition SKILL + the current file, returns
search/replace edits, and gets Verus output back, for up to --rounds rounds.
Every edit is checked by proof_guard against the original task (proof-only).

Conditions (selected by --condition, skill text from --skill):
  base       stop at the first verified file
  rules      same loop, SKILL includes speed guidance; stop at first verified
  procedure  after the first verified file, the model is shown the exact
             per-function Z3 cost profile and may spend up to --cleanup-rounds
             rounds making it cheaper; the cheapest verified file is final

Recorded per episode: success, rounds, tokens, every Verus call's wall time
and outcome, final exact Z3 rlimit (SMT replay) of the final file.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import tempfile
import time
from pathlib import Path

from measure_candidates import DEFAULT_VERUS, verus_env
from optimize_proof import apply_edits, call_deepseek, parse_edits, profile_text
from proof_guard import check as guard_check
from smt_replay import cost as smt_cost, run_group

SYSTEM = """You are an expert Verus proof engineer. Make the given Rust/Verus file verify.
Rules:
- Edit only proof content: proof fn bodies, proof blocks, assert statements, ghost lets, loop invariants/decreases of the target, new helper proof lemmas, and `use`/`broadcast use` lines.
- Never change executable code, spec fn bodies, existing fn signatures or requires/ensures, types, or text outside fns. Never add assume, admit, external_body, rlimit attributes, or unsafe.
Each reply: at most 8 lines of reasoning summary, then exactly one JSON code block
```json
{"edits": [{"find": "<exact unique text from the CURRENT file>", "replace": "<new text>"}]}
```
or, when you have nothing more to change, the block {"edits": [], "done": true}."""


def run_verus(text: str, timeout: int = 300) -> dict:
    with tempfile.TemporaryDirectory(prefix="solve-") as tmp:
        (Path(tmp) / "candidate.rs").write_text(text)
        t0 = time.monotonic()
        try:
            p = run_group([str(DEFAULT_VERUS), "candidate.rs", "--multiple-errors", "8"], timeout,
                          cwd=tmp, env=verus_env())
        except Exception:
            return {"passed": False, "wall": time.monotonic() - t0, "output": "Verus timed out.", "timed_out": True}
        wall = time.monotonic() - t0
    out = (p.stdout + p.stderr).replace(tmp, "")
    out = re.sub(r"(?m)^warning:.*\n(  .*\n|\s*\|.*\n|\s*-->.*\n|\s*=.*\n)*", "", out)
    m = re.search(r"verification results:: (\d+) verified, (\d+) errors", out)
    passed = p.returncode == 0 and bool(m) and m.group(2) == "0"
    return {"passed": passed, "wall": wall, "output": out[-6000:], "timed_out": False}


def episode(task: dict, cond: str, rep: int, a) -> dict:
    edir = a.out_dir / cond / f"{task['task_id'][:100]}__r{rep}"
    edir.mkdir(parents=True, exist_ok=True)
    if (edir / "result.json").exists():
        return json.loads((edir / "result.json").read_text())
    source = Path(task["source_path"]).read_text()
    skill = a.skills[cond]
    cur = source
    first = run_verus(cur)
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": (f"## SKILL\n{skill}\n\n" if skill else "") +
             f"## Task\nMake this file verify (task {task['task_id']}).\n```rust\n{cur}\n```\n\n"
             f"Verus output on the current file:\n```\n{first['output']}\n```"}]
    calls = [{"round": 0, "wall": first["wall"], "passed": first["passed"]}]
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 0}
    log = (edir / "log.jsonl").open("w")
    solved_text, solved_round, cleanup_used = None, None, 0
    best_cost = None
    t_start = time.monotonic()
    last_shown = cur
    for rnd in range(1, a.rounds + 1):
        reply, u = call_deepseek(msgs, a.model, a.effort, max_tokens=64000)
        for k in usage:
            usage[k] += u.get(k, 0) or 0
        msgs.append({"role": "assistant", "content": reply})
        edits = parse_edits(reply)
        done = bool(re.search(r'"done"\s*:\s*true', reply))
        rec = {"round": rnd, "usage": u, "reply_tail": reply[-1500:]}
        fb = None
        if edits is None:
            fb = "Could not parse your JSON block; reply in the required format."
            rec["outcome"] = "parse_error"
        elif not edits:
            rec["outcome"] = "no_edits"
            fb = "No edits given."
        else:
            new, err = apply_edits(cur, edits)
            if new is None:
                fb, rec["outcome"] = f"Edits not applied: {err}", "apply_error"
            elif guard_check(source, new):
                fb = "Rejected (only proof content may change): " + "; ".join(guard_check(source, new)[:4])
                rec["outcome"] = "guard_reject"
            else:
                v = run_verus(new)
                calls.append({"round": rnd, "wall": v["wall"], "passed": v["passed"]})
                rec.update({"outcome": "verified" if v["passed"] else "failed", "verus_wall": v["wall"]})
                if v["passed"]:
                    if solved_text is None:
                        solved_text, solved_round, cur = new, rnd, new
                    elif cond == "procedure":
                        c = smt_cost(new)
                        if c["success"] and c["rlimit"] < best_cost["rlimit"]:
                            solved_text, cur, best_cost = new, new, c
                            rec["cleanup_cost"] = c["rlimit"]
                    else:
                        cur = new
                    if cond != "procedure":
                        log.write(json.dumps(rec) + "\n")
                        break
                    if best_cost is None:
                        best_cost = smt_cost(solved_text)
                    fb = ("The file VERIFIES. Exact solver cost of the best verified version so far:\n"
                          f"{profile_text({'rlimit': best_cost['rlimit'], 'qi': best_cost['qi'], 'functions': {k: v['rlimit'] for k, v in best_cost['functions'].items()}, 'functions_qi': {k: v['qi'] for k, v in best_cost['functions'].items()}})}\n"
                          "Following the SKILL's post-verification procedure, propose edits that make it cheaper while "
                          "keeping it verified, or reply done.")
                else:
                    cur = new if solved_text is None else cur
                    fb = f"Verus output:\n```\n{v['output']}\n```" + (
                        "\n(The last verified version is kept as current.)" if solved_text is not None else "")
        log.write(json.dumps(rec) + "\n")
        log.flush()
        if solved_text is not None and cond == "procedure":
            if rnd > solved_round:
                cleanup_used += 1
            if done or cleanup_used >= a.cleanup_rounds:
                break
        elif solved_text is not None:
            break
        if time.monotonic() - t_start > a.budget_seconds:
            break
        shown = ""
        if cur != last_shown:
            shown, last_shown = f"\n\nCurrent file:\n```rust\n{cur}\n```", cur
        msgs.append({"role": "user", "content": fb + shown})
    final = {"task_id": task["task_id"], "condition": cond, "repeat": rep, "solved": solved_text is not None,
             "solved_round": solved_round, "rounds": rnd, "usage": usage,
             "verus_calls": len(calls), "verus_wall_total": sum(c["wall"] for c in calls),
             "verus_wall_failed": sum(c["wall"] for c in calls if not c["passed"]),
             "elapsed": time.monotonic() - t_start}
    if solved_text is not None:
        (edir / "final.rs").write_text(solved_text)
        c = best_cost if (cond == "procedure" and best_cost) else smt_cost(solved_text)
        final.update({"final_rlimit": c["rlimit"], "final_qi": c["qi"], "final_functions": c["functions"]})
    (edir / "result.json").write_text(json.dumps(final, indent=1))
    return final


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True, help="jsonl: task_id, source_path")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--conditions", nargs="+", default=["base", "rules", "procedure"])
    ap.add_argument("--skill-base", type=Path, required=True)
    ap.add_argument("--skill-rules", type=Path)
    ap.add_argument("--skill-procedure", type=Path)
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=12)
    ap.add_argument("--cleanup-rounds", type=int, default=2)
    ap.add_argument("--budget-seconds", type=int, default=1800)
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    base = a.skill_base.read_text()
    a.skills = {"base": base,
                "rules": base + ("\n\n" + a.skill_rules.read_text() if a.skill_rules else ""),
                "procedure": base + ("\n\n" + a.skill_procedure.read_text() if a.skill_procedure else "")}
    tasks = [json.loads(l) for l in a.tasks.read_text().splitlines()][: a.limit]
    jobs = [(t, c, r) for r in range(a.repeats) for t in tasks for c in a.conditions]
    with cf.ThreadPoolExecutor(a.workers) as pool:
        for out in pool.map(lambda j: episode(*j, a), jobs):
            print(json.dumps({k: out.get(k) for k in ("task_id", "condition", "repeat", "solved", "rounds", "final_rlimit")}), flush=True)


if __name__ == "__main__":
    main()
