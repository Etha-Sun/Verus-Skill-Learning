#!/usr/bin/env python3
"""Body-stub slices versus in-repository single-function checks.

For each sampled function of a project (from repo_serve_bench.py's output):
  repo        in-repository single-function check, native Verus (reference)
  slice       same check on a copy where every other body is stubbed (slice_stub.py)
  slice_fast  slice, resident pool, --no-lifetime
Each function is checked as is and broken (`assert(false);` at the start of
its body); the slice must agree with the repository in both cases.

  python3 verus-speed/slice_bench.py --functions RUN/repo_serve_bench.json --out RUN/slice_bench.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics as st
import subprocess
import tempfile
import time
from pathlib import Path

from repo_serve_bench import PROJECTS, selector_args
from serve_bench import DEFAULT_RUST_VERIFY, Z3, verdict
from slice_stub import locate, stub_crate
from verus_serve import Pool, verus_env


def break_fn(crate: Path, name: str) -> bool:
    hits = locate(crate, name)
    if len(hits) != 1:
        return False
    f, b = hits[0]
    text = f.read_text()
    f.write_text(text[:b + 1] + "\n    assert(false);\n" + text[b + 1:])
    return True


def copy(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, symlinks=True,
                    ignore=lambda d, names: ["target"] if Path(d).name == "deps_hack" else [])
    tgt = src / "deps_hack" / "target"
    if tgt.exists():
        (dst / "deps_hack" / "target").symlink_to(tgt)


def summarize(rows: list[dict]) -> dict:
    """Agreement and timing. Only non-trivial rows count: as-is rows where the
    repository verified at least one function, broken rows where the repository
    reported at least one verification error (an insertion that fails before
    SMT in both does not test the slice). Agreement is exact (verified, errors)."""
    key = lambda r: (r.get("verified"), r.get("errors"), bool(r.get("encountered-error")))
    out: dict = {}
    for kind, real in (("ok", lambda r: (r.get("verified") or 0) > 0),
                       ("broken", lambda r: (r.get("errors") or 0) > 0)):
        cases = [x[kind] for x in rows if kind in x]
        counted = [c for c in cases if real(c["repo"]["res"])]
        out[f"{kind}_trivial"] = len(cases) - len(counted)
        for arm in ("slice", "slice_fast"):
            out[f"{arm}_agree_{kind}"] = [sum(key(c["repo"]["res"]) == key(c[arm]["res"]) for c in counted),
                                          len(counted)]
    for arm in ("repo", "slice", "slice_fast"):
        v = [x["ok"][arm]["wall_s"] for x in rows if (x["ok"]["repo"]["res"].get("verified") or 0) > 0]
        out[f"{arm}_median_s"] = round(st.median(v), 2) if v else None
    out["stub_median_s"] = round(st.median(x["stub_s"] for x in rows), 2)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--functions", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    cmd = ["rustup", "run", "1.88.0-x86_64-unknown-linux-gnu", str(DEFAULT_RUST_VERIFY)]
    env = verus_env({"VERUS_Z3_PATH": str(Z3)})
    cold_env = {k: v for k, v in env.items() if k != "VERUS_IMPORT_CACHE"}
    pool = Pool(cmd, size=1, env={"VERUS_Z3_PATH": str(Z3)})
    sampled = json.loads(a.functions.read_text())
    results = json.loads(a.out.read_text()) if a.out.exists() else {}

    def cold(cwd: Path, req: list[str]) -> dict:
        t0 = time.monotonic()
        p = subprocess.run([*cmd, *req], cwd=cwd, env=cold_env, capture_output=True, text=True,
                           timeout=a.timeout)
        return {"wall_s": time.monotonic() - t0, "res": verdict(p.stdout)}

    def warm(cwd: Path, req: list[str]) -> dict:
        r = pool.run(str(cwd), req, a.timeout)
        out = {"wall_s": r["wall_s"], "res": verdict(r.get("stdout", "")), "crashed": r.get("crashed", False)}
        if not out["res"]:
            out["stderr_tail"] = r.get("stderr", "")[-1500:]
        return out

    for proj, data in sampled.items():
        if (a.only and proj not in a.only) or proj in results:
            continue
        src, args = PROJECTS[proj]
        rows = []
        for r in data["rows"]:
            module, fn = r["module"], r["function"]
            name = fn.lstrip("*").split("::")[-1]
            req = [*args, *selector_args(module, fn)]
            row = {"module": module, "function": fn}
            with tempfile.TemporaryDirectory(prefix="vslb_") as tmp:
                tmp = Path(tmp)
                t0 = time.monotonic()
                stats = stub_crate(src, tmp / "slice", {name}, suffix=True)  # same matching as the selector
                row["stub_s"] = round(time.monotonic() - t0, 2)
                row["stub_stats"] = stats
                row["ok"] = {"repo": cold(src, req), "slice": cold(tmp / "slice", req),
                             "slice_fast": warm(tmp / "slice", [*req, "--no-lifetime"])}
                copy(src, tmp / "repo_broken")
                if break_fn(tmp / "repo_broken", name) and break_fn(tmp / "slice", name):
                    row["broken"] = {"repo": cold(tmp / "repo_broken", req),
                                     "slice": cold(tmp / "slice", req),
                                     "slice_fast": warm(tmp / "slice", [*req, "--no-lifetime"])}
            rows.append(row)
            print(proj, name[:40], {k: (v["res"].get("verified"), v["res"].get("errors"), round(v["wall_s"], 1))
                                    for k, v in row["ok"].items()},
                  {k: (v["res"].get("verified"), v["res"].get("errors")) for k, v in row.get("broken", {}).items()},
                  flush=True)

        summary = summarize(rows)
        results[proj] = {"summary": summary, "rows": rows}
        a.out.write_text(json.dumps(results, indent=1))
        print(proj, json.dumps(summary), flush=True)
    pool.close()


if __name__ == "__main__":
    main()
