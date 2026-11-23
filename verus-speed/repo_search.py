#!/usr/bin/env python3
"""Cheaper-proof search for one function inside a whole repository.

Same search as scripts/proof_time/speed_search.py (single-change variants:
delete one assert / assert-by / assert-forall / reveal, add
`#[verifier::spinoff_prover]`; then greedy combination), but every candidate
is verified in the repository context with
`--verify-only-module M --verify-function F`, because a rewrite that is
cheaper in the single-file task can be costlier or fail in the repository.

Costing is one capped solve (see fast_cost.py): Verus only writes the SMT log
under a tiny resource limit, the log is replayed in Z3 with the project's real
limit capped at the current best cost. The final proof is confirmed by normal
Verus runs on seeds 0, 1 and 2, and written to --out-dir. The repository clone
itself is never modified; each candidate runs in a temporary copy of the crate.

  python3 verus-speed/repo_search.py nrkernel spec_t::os_code_vc lemma_concurrent_trs_no_lock \
      --out-dir RUN/repo_search
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/proof_time"))

import fast_cost  # noqa: E402
from measure_candidates import DEFAULT_VERUS, verus_env  # noqa: E402
from smt_replay import run_group  # noqa: E402
from speed_search import key, variants  # noqa: E402

REPOS = Path(os.environ.get("VERUS_SPEED_REPOS", Path.home() / ".cache/verus-skill/src/repos"))
PROJECTS = {
    "nrkernel": {"crate": "verified-nrkernel/page-table/src", "root": "lib.rs", "rlimit": 30,
                 "args": ["--crate-type=lib", "--cfg", 'feature="impl"']},
    "anvil_vrs": {"crate": "anvil/src", "root": "vreplicaset_controller.rs", "rlimit": 50,
                  "args": ["--crate-type=lib", "-L", "dependency=deps_hack/target/debug/deps",
                           "--extern=deps_hack=deps_hack/target/debug/libdeps_hack.rlib"]},
    "ironkv": {"crate": "verified-ironkv/ironsht/src", "root": "lib.rs", "rlimit": 10,
               "args": ["--crate-type=dylib"]},
}


def copy_crate(project: str, dst: Path) -> Path:
    src = REPOS / PROJECTS[project]["crate"]
    shutil.copytree(src, dst, symlinks=True,
                    ignore=lambda d, names: ["target"] if Path(d).name == "deps_hack" else [])
    target = src / "deps_hack" / "target"
    if target.exists():
        (dst / "deps_hack" / "target").symlink_to(target)
    return dst


def verus_cmd(project: str, module: str, fn: str) -> list[str]:
    p = PROJECTS[project]
    return [str(DEFAULT_VERUS), p["root"], *p["args"], "--verify-only-module", module,
            "--verify-function", fn, "--num-threads", "1", "--output-json"]


def cost(project: str, rel: str, text: str, module: str, fn: str, cap: float | None,
         timeout: int, seed: int = 0, exact: bool = True) -> dict:
    """Verdict and exact rlimit of `fn` when file `rel` of the crate has content `text`.

    exact=False runs normal Verus only (used for the final confirmation)."""
    proj_units = PROJECTS[project]["rlimit"] * fast_cost.UNITS_PER_RLIMIT
    tiny = exact and not fast_cost.COMPUTE.search(text)
    with tempfile.TemporaryDirectory(prefix="vrs_") as tmp:
        crate = copy_crate(project, Path(tmp) / "crate")
        marked, real = fast_cost.mark_rlimit_attrs(text) if tiny else (text, {})
        real[1] = proj_units
        (crate / rel).write_text(marked)
        cmd = verus_cmd(project, module, fn) + ["--smt-option", f"smt.random_seed={seed}"]
        cmd += ["--rlimit", str(fast_cost.TINY if tiny else PROJECTS[project]["rlimit"])]
        if exact:
            cmd += ["--log", "smt", "--log-dir", str(Path(tmp) / "lg"),
                    "--multiple-errors", "0", "--no-auto-recommends-check"]
        t0 = time.monotonic()
        try:
            proc = run_group(cmd, timeout, cwd=crate, env=verus_env())
        except subprocess.TimeoutExpired:
            return {"success": False, "timed_out": True}
        try:
            vr = json.loads(proc.stdout).get("verification-results", {})
        except Exception:
            vr = {"encountered-vir-error": True}
        reached = not vr.get("encountered-vir-error") and (vr.get("verified") or 0) + (vr.get("errors") or 0) > 0
        if not reached and "more than one match" in proc.stderr:
            return {"success": False, "ambiguous": True}
        if not exact:
            return {"success": bool(vr.get("verified")) and not vr.get("errors") and reached,
                    "wall": time.monotonic() - t0}
        if not reached or (not tiny and vr.get("errors")):
            return {"success": False, "wall": time.monotonic() - t0}
        total, ok = 0.0, True
        logs = sorted((Path(tmp) / "lg").glob("*.smt2"))
        for log in logs:
            script, owners = fast_cost.build_script(log.read_text(), cap, real)
            r = fast_cost.replay(script, owners, timeout, stop_early=True)
            total += sum(v["rlimit"] for v in r["funcs"].values())
            if r["timed_out"]:
                return {"success": False, "timed_out": True}
            if not r["ok"]:
                ok = False
                break
        return {"success": ok and bool(logs), "rlimit": total, "wall": time.monotonic() - t0}


def find_file(project: str, fn: str) -> list[Path]:
    crate = REPOS / PROJECTS[project]["crate"]
    return [p for p in crate.rglob("*.rs") if "deps_hack" not in p.parts
            and re.search(rf"\bfn\s+{re.escape(fn)}\s*[(<]", p.read_text())]


def search(project: str, module: str, fn: str, out_dir: Path, workers: int, timeout: int) -> dict:
    tdir = out_dir / project / fn
    tdir.mkdir(parents=True, exist_ok=True)
    if (tdir / "final.json").exists():
        return json.loads((tdir / "final.json").read_text())
    files = find_file(project, fn)
    if len(files) != 1:
        return {"function": fn, "skipped": f"{len(files)} files define the function"}
    rel = str(files[0].relative_to(REPOS / PROJECTS[project]["crate"]))
    text = files[0].read_text()
    t_start = time.monotonic()
    name = fn  # the name used to find the function in the source
    base = cost(project, rel, text, module, fn, None, timeout)
    if base.get("ambiguous"):
        fn = "*" + fn  # --verify-function matches substrings; anchor at the end instead
        base = cost(project, rel, text, module, fn, None, timeout)
    if not base["success"]:
        out = {"function": name, "skipped": "baseline does not verify in the repository"}
        (tdir / "final.json").write_text(json.dumps(out))
        return out
    cap = base["rlimit"]
    vs = [v for v in variants(text, {name}) if v["kind"] != "del_broadcast_use"]
    with ThreadPoolExecutor(workers) as pool:
        res = list(pool.map(lambda v: cost(project, rel, v["text"], module, fn, cap, timeout), vs))
    singles = [{"kind": v["kind"], "stmt": v["stmt"][:2000], "success": r["success"],
                "ratio": r["rlimit"] / cap if r["success"] else None} for v, r in zip(vs, res)]
    (tdir / "singles.jsonl").write_text("".join(json.dumps(s) + "\n" for s in singles))
    good = sorted([(s, v) for s, v in zip(singles, vs) if s["success"] and s["ratio"] < 0.995],
                  key=lambda sv: sv[0]["ratio"])
    cur, cur_cost, applied = text, cap, []
    for s, v in good:
        match = [x for x in variants(cur, {name}) if key(x) == key(v)]
        if len(match) != 1:
            continue
        r = cost(project, rel, match[0]["text"], module, fn, cur_cost, timeout)
        if r["success"] and r["rlimit"] < cur_cost:
            cur, cur_cost = match[0]["text"], r["rlimit"]
            applied.append({"kind": s["kind"], "stmt": s["stmt"][:300], "single_ratio": s["ratio"],
                            "cum_ratio": cur_cost / cap})
    confirmed = all(cost(project, rel, cur, module, fn, None, timeout, seed=sd, exact=False)["success"]
                    for sd in (0, 1, 2)) if applied else True
    if not confirmed:
        cur, cur_cost, applied = text, cap, []
    (tdir / "best.rs").write_text(cur)
    out = {"project": project, "module": module, "function": name, "file": rel,
           "baseline_rlimit": cap, "best_rlimit": cur_cost, "ratio": cur_cost / cap,
           "n_singles": len(singles), "n_beneficial_singles": len(good), "applied": applied,
           "confirmed": confirmed, "search_wall_s": round(time.monotonic() - t_start, 1)}
    (tdir / "final.json").write_text(json.dumps(out, indent=1))
    return out


def heaviest(full_json: Path, top: int) -> list[tuple[str, str]]:
    fns = []
    for m in json.loads(full_json.read_text())["times-ms"]["smt"]["smt-run-module-times"]:
        for f in m.get("function-breakdown") or []:
            fns.append((f["time-micros"], m["module"], f["function"].split("::")[-1]))
    return [(m, f) for _, m, f in sorted(fns, reverse=True)[:top]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", choices=sorted(PROJECTS))
    ap.add_argument("module", nargs="?")
    ap.add_argument("function", nargs="?")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8, help="candidates in parallel per function")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--full-json", type=Path, help="repo_run.sh output; search its heaviest functions")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--parallel", type=int, default=4, help="functions in parallel with --full-json")
    a = ap.parse_args()
    targets = heaviest(a.full_json, a.top) if a.full_json else [(a.module, a.function)]
    with ThreadPoolExecutor(a.parallel) as pool:
        for out in pool.map(lambda t: search(a.project, t[0], t[1], a.out_dir, a.workers, a.timeout), targets):
            print(json.dumps({k: out.get(k) for k in ("function", "ratio", "n_singles", "n_beneficial_singles",
                                                       "confirmed", "search_wall_s", "skipped")}), flush=True)


if __name__ == "__main__":
    main()
