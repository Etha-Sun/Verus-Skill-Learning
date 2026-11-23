#!/usr/bin/env python3
"""Do rewritten proofs stay verified on new solver seeds, compared with the originals?

For every confirmed repo_search.py rewrite of a project, verifies the function
in the repository with normal Verus on seeds the search never used, for the
original and for the rewritten file. Hint removal is known to make proofs
less stable, so the comparison is against the original on the same seeds.

  python3 verus-speed/repo_stability.py nrkernel --search-dir RUN/repo_search \
      --out RUN/repo/nrkernel_stability.json
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from repo_search import PROJECTS, REPOS, cost


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", choices=sorted(PROJECTS))
    ap.add_argument("--search-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[11, 12, 13, 14, 15])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    jobs = []
    for fin in sorted((a.search_dir / a.project).glob("*/final.json")):
        d = json.loads(fin.read_text())
        if not d.get("applied") or not d.get("confirmed"):
            continue
        orig = (REPOS / PROJECTS[a.project]["crate"] / d["file"]).read_text()
        new = (fin.parent / "best.rs").read_text()
        for seed in a.seeds:
            for arm, text in (("before", orig), ("after", new)):
                jobs.append((d, arm, seed, text))

    def run(job):
        d, arm, seed, text = job
        # the selector must be the one the search settled on; "*name" is always safe
        r = cost(a.project, d["file"], text, d["module"], "*" + d["function"], None,
                 a.timeout, seed=seed, exact=False)
        return d["function"], arm, seed, bool(r.get("success"))

    table: dict = {}
    with ThreadPoolExecutor(a.workers) as pool:
        for fn, arm, seed, ok in pool.map(run, jobs):
            table.setdefault(fn, {"before": {}, "after": {}})[arm][seed] = ok
    a.out.write_text(json.dumps(table, indent=1))
    n = len(a.seeds)
    for fn, t in table.items():
        b, af = sum(t["before"].values()), sum(t["after"].values())
        if b != n or af != n:
            print(f"{fn}: before {b}/{n}, after {af}/{n}")
    print(json.dumps({"functions": len(table), "seeds": n,
                      "before_pass": sum(sum(t["before"].values()) for t in table.values()),
                      "after_pass": sum(sum(t["after"].values()) for t in table.values()),
                      "runs_per_arm": len(table) * n}))


if __name__ == "__main__":
    main()
