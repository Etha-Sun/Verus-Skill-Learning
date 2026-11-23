#!/usr/bin/env python3
"""Merge confirmed in-repo rewrites into a copy of the repository and time it.

Collects every repo_search.py result for a project that changed the proof and
was confirmed, applies each as a patch (original file -> best.rs) onto a fresh
copy of the crate, then runs the full-project check on the original and on the
patched copy, alternating, with repo_run.sh.

  python3 verus-speed/repo_apply.py nrkernel --search-dir RUN/repo_search \
      --patched-repos RUN/repo_patched2 --out RUN/repo/nrkernel_apply.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from repo_search import PROJECTS, REPOS, copy_crate

RUNNER = Path(__file__).with_name("repo_run.sh")


def merge(project: str, search_dir: Path, patched_repos: Path) -> list[dict]:
    crate = patched_repos / PROJECTS[project]["crate"]
    if crate.exists():
        shutil.rmtree(crate)
    crate.parent.mkdir(parents=True, exist_ok=True)
    copy_crate(project, crate)
    applied = []
    for fin in sorted((search_dir / project).glob("*/final.json")):
        d = json.loads(fin.read_text())
        if not d.get("applied") or not d.get("confirmed"):
            continue
        orig = REPOS / PROJECTS[project]["crate"] / d["file"]
        diff = subprocess.run(["diff", "-u", str(orig), str(fin.parent / "best.rs")],
                              capture_output=True, text=True).stdout
        r = subprocess.run(["patch", "--no-backup-if-mismatch", "-s", str(crate / d["file"])],
                           input=diff, capture_output=True, text=True)
        applied.append({"function": d["function"], "file": d["file"], "ratio": d["ratio"],
                        "edits": [a["kind"] for a in d["applied"]], "merged": r.returncode == 0})
    return applied


def full_run(project: str, repos: Path | None, threads: int, extra: list[str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="vapply_") as tmp:
        out = Path(tmp) / "o.json"
        env = dict(os.environ)
        if repos:
            env["VERUS_SPEED_REPOS"] = str(repos)
        subprocess.run([str(RUNNER), project, str(out), "--num-threads", str(threads), *extra],
                       env=env, check=False)
        meta = json.loads(out.with_suffix(".meta").read_text())
        doc = json.loads(out.read_text())
    t, res = doc["times-ms"], doc["verification-results"]
    fns, failed = {}, []
    for m in t["smt"]["smt-run-module-times"]:
        for f in m.get("function-breakdown") or []:
            name = f["function"].split("::")[-1]
            fns[name] = fns.get(name, 0) + f["time-micros"] / 1e6
            if not f.get("success"):
                failed.append(name)
    modules = {m["module"]: m["time"] / 1000 for m in t["total-verify-module-times"]}
    return {"wall_s": meta["wall"], "verified": res.get("verified"), "errors": res.get("errors"),
            "cpu_s": t["estimated-cpu-time"] / 1000, "smt_run_s": t["smt"]["smt-run"] / 1000,
            "failed": sorted(failed), "slowest_module": max(modules.items(), key=lambda kv: kv[1]),
            "functions": fns}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", choices=sorted(PROJECTS))
    ap.add_argument("--search-dir", type=Path, required=True)
    ap.add_argument("--patched-repos", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--extra", nargs="*", default=[], help="extra Verus flags for both arms")
    a = ap.parse_args()
    applied = merge(a.project, a.search_dir, a.patched_repos)
    runs = {"before": [], "after": []}
    for _ in range(a.repeats):
        runs["before"].append(full_run(a.project, None, a.threads, a.extra))
        runs["after"].append(full_run(a.project, a.patched_repos, a.threads, a.extra))
    a.out.write_text(json.dumps({"applied": applied, "runs": runs}, indent=1))
    print(json.dumps({"functions_rewritten": sum(x["merged"] for x in applied),
                      "merge_failures": sum(not x["merged"] for x in applied)}))
    changed = {x["function"] for x in applied if x["merged"]}

    def part(run: dict, inside: bool) -> float:
        return sum(v for k, v in run["functions"].items() if (k in changed) == inside)

    for k, v in runs.items():
        for r in v:
            print(k, "wall", round(r["wall_s"], 1), "verified", r["verified"], "errors", r["errors"],
                  "smt", round(r["smt_run_s"]), "rewritten_fns", round(part(r, True), 1),
                  "other_fns", round(part(r, False), 1), "slowest_module", r["slowest_module"][0],
                  round(r["slowest_module"][1], 1), "failed", r["failed"])
    # Untouched functions measure the load of each run; divide it out.
    def med(xs: list[float]) -> float:
        return sorted(xs)[len(xs) // 2]

    before = med([part(r, True) / part(r, False) for r in runs["before"]])
    after = med([part(r, True) / part(r, False) for r in runs["after"]])
    share = med([part(r, True) / (part(r, True) + part(r, False)) for r in runs["before"]])
    ratio = after / before
    print(json.dumps({"rewritten_share_of_smt_before": round(share, 3),
                      "load_corrected_ratio_rewritten_fns": round(ratio, 3),
                      "implied_total_smt_ratio": round(1 - share * (1 - ratio), 3)}))


if __name__ == "__main__":
    main()
