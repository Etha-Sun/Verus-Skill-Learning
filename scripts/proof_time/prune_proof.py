#!/usr/bin/env python3
"""Non-LLM baseline: greedy assert pruning (linear-scan proof minimizer).

Within functions whose bodies differ from the original task (the proof region),
try deleting each assert statement (`assert(..);`, `assert(..) by {..}`,
`assert forall .. by {..};`) one at a time, last to first; keep a deletion if
the file still verifies and exact Z3 rlimit does not increase.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
from pathlib import Path

from optimize_proof import verify
from proof_guard import items, match_brace, strip_comments


def assert_spans(text: str, region: list[tuple[int, int]]) -> list[tuple[int, int]]:
    spans = []
    for m in re.finditer(r"(?m)^[ \t]*assert\b", text):
        s = m.start()
        if not any(a <= s < b for a, b in region):
            continue
        j, depth = m.end(), 0
        while j < len(text):
            c = text[j]
            if c == "{" and depth == 0:
                j = match_brace(text, j)
                k = re.match(r"\s*;", text[j:])
                j += k.end() if k else 0
                break
            if c in "([":
                depth += 1
            elif c in ")]":
                depth -= 1
            elif c == ";" and depth == 0:
                j += 1
                break
            j += 1
        spans.append((s, j))
    return spans


def prune(task: dict, out_dir: Path) -> dict:
    tdir = out_dir / task["task_id"]
    tdir.mkdir(parents=True, exist_ok=True)
    if (tdir / "final.json").exists():
        return json.loads((tdir / "final.json").read_text())
    src = strip_comments(Path(task["source_path"]).read_text())
    text = strip_comments(Path(task["candidate_path"]).read_text())
    base = verify(text)
    if not base["success"]:
        return {"task_id": task["task_id"], "skipped": "baseline (comment-stripped) does not verify"}
    src_bodies = {(it[0], it[3]) for it in items(src)}
    best, n_try, n_removed = base, 0, 0
    i = None
    while True:
        region = [(it[4], it[5]) for it in items(text) if (it[0], it[3]) not in src_bodies]
        spans = assert_spans(text, region)
        if i is None:
            i = len(spans)
        i -= 1
        if i < 0:
            break
        s, e = spans[i]
        cand = text[:s] + text[e:]
        n_try += 1
        r = verify(cand)
        if r["success"] and r["rlimit"] <= best["rlimit"]:
            text, best, n_removed = cand, r, n_removed + 1
    (tdir / "best.rs").write_text(text)
    out = {"task_id": task["task_id"], "baseline_rlimit": base["rlimit"], "best_rlimit": best["rlimit"],
           "ratio": best["rlimit"] / base["rlimit"] if base["rlimit"] else 1,
           "tries": n_try, "removed": n_removed}
    (tdir / "final.json").write_text(json.dumps(out, indent=1))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    tasks = [json.loads(l) for l in a.tasks.read_text().splitlines()]
    with cf.ThreadPoolExecutor(a.workers) as pool:
        for out in pool.map(lambda t: prune(t, a.out_dir), tasks):
            print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
