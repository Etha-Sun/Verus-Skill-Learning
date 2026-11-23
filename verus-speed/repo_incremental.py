#!/usr/bin/env python3
"""Cost of re-verifying one function of a whole project versus the whole project.

Reads a full-project timing JSON produced by repo_run.sh, picks the heaviest
functions plus a random sample, and re-verifies each alone with
`--verify-only-module M --verify-function F`. A proof-body edit cannot change
what other functions see, so this is the smallest sound re-check for it.

  python3 verus-speed/repo_incremental.py nrkernel RUN/repo/nrkernel_t16.json \
      --out RUN/repo/nrkernel_incremental.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RUNNER = Path(__file__).with_name("repo_run.sh")


def functions(full: dict) -> list[dict]:
    out = []
    for m in full["times-ms"]["smt"]["smt-run-module-times"]:
        for f in m.get("function-breakdown") or []:
            out.append({"module": m["module"], "function": f["function"],
                        "full_smt_s": f["time-micros"] / 1e6, "success": f.get("success")})
    return out


def run_one(project: str, fn: dict) -> dict:
    parts = fn["function"].split("::")
    for name in (parts[-1], "::".join(parts[-2:])):  # widen on an ambiguous match
        with tempfile.TemporaryDirectory(prefix="vinc_") as tmp:
            out = Path(tmp) / "o.json"
            flags = ["--verify-function", name, "--num-threads", "1"]
            flags += ["--verify-only-module", fn["module"]] if fn["module"] else ["--verify-root"]
            subprocess.run([str(RUNNER), project, str(out), *flags], check=False)
            meta = json.loads(out.with_suffix(".meta").read_text())
            stderr = out.with_suffix(".stderr").read_text()
            try:
                doc = json.loads(out.read_text())
            except json.JSONDecodeError:
                doc = {}
        if "more than one match" not in stderr:
            break
    res = doc.get("verification-results") or {}
    t = doc.get("times-ms") or {}
    return {**fn, "selector": name, "wall_s": meta["wall"], "verified": res.get("verified"),
            "errors": res.get("errors"), "smt_run_ms": (t.get("smt") or {}).get("smt-run"),
            "rust_ms": (t.get("rust") or {}).get("total"),
            "vir_ms": ((t.get("verification") or {}).get("vir") or {}).get("total"),
            "air_ms": (t.get("air") or {}).get("total")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("full_json", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--heaviest", type=int, default=6)
    ap.add_argument("--random", type=int, default=14)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    fns = sorted(functions(json.loads(a.full_json.read_text())), key=lambda f: -f["full_smt_s"])
    rest = fns[a.heaviest:]
    random.Random(0).shuffle(rest)
    picked = fns[:a.heaviest] + rest[:a.random]
    with ThreadPoolExecutor(a.workers) as pool, a.out.open("w") as fh:
        for r in pool.map(lambda f: run_one(a.project, f), picked):
            fh.write(json.dumps(r) + "\n")
            fh.flush()


if __name__ == "__main__":
    main()
