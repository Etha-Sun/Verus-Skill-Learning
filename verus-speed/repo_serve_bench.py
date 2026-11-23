#!/usr/bin/env python3
"""Single-function checks inside whole projects: native Verus versus the resident pool.

For each project: one full run lists its functions; a random sample of them is
then re-verified one at a time with `--verify-only-module M --verify-function F`
in three arms, interleaved per request:
  cold       native Verus, one process per request (rust_verify via rustup)
  warm       resident pool (verus_serve.Pool, import cache)
  warm_fast  resident pool plus --no-lifetime (iteration mode; needs a final full check)
Verdicts of cold and warm must agree.

  python3 verus-speed/repo_serve_bench.py --out RUN/repo_serve_bench.json [--only ironkv ...]
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st
import subprocess
import time
from pathlib import Path

from serve_bench import DEFAULT_RUST_VERIFY, Z3, verdict
from verus_serve import Pool, verus_env

CACHE = Path.home() / ".cache/verus-skill"
WT = CACHE / "src/worktrees"
DEPS = ["-L", "dependency=deps_hack/target/debug/deps",
        "--extern=deps_hack=deps_hack/target/debug/libdeps_hack.rlib"]
PROJECTS = {
    "ironkv": (WT / "verified-ironkv@472c6213/ironsht/src", ["lib.rs", "--crate-type=dylib"]),
    "noderep": (WT / "verified-node-replication@c3acacfb/verified-node-replication/src", ["lib.rs", "--crate-type=lib"]),
    "nrkernel": (WT / "verified-nrkernel@733950a5/page-table/src",
                 ["lib.rs", "--crate-type=lib", "--cfg", 'feature="impl"', "--rlimit", "30"]),
    "anvil_vrs": (CACHE / "src/repos/anvil/src",
                  ["vreplicaset_controller.rs", "--crate-type=lib", *DEPS, "--rlimit", "50"]),
    "vest": (WT / "vest@1d6acdc1/vest/src", ["lib.rs", "--crate-type=lib"]),
    "pmemlog": (WT / "verified-storage@b4bf3373/pmemlog/src", ["lib.rs", "--crate-type=lib"]),
    "verified_graphs": (WT / "verified-graphs@4412d9b3/src", ["lib.rs", "--crate-type=lib"]),
}


def functions(cmd: list[str], env: dict, cwd: Path, args: list[str]) -> list[tuple[str, str]]:
    p = subprocess.run([*cmd, *args, "--output-json", "--time-expanded", "--num-threads", "16"], cwd=cwd,
                       env=env, capture_output=True, text=True, timeout=7200)
    i = p.stdout.rfind("\n{\n")
    doc = json.loads(p.stdout[i + 1 if i >= 0 else 0:])
    out = []
    for m in doc["times-ms"]["smt"]["smt-run-module-times"]:
        for f in m.get("function-breakdown") or []:
            parts = f["function"].split("::")[1:]  # drop the crate name
            mod = m["module"].split("::") if m["module"] else []
            rel = parts[len(mod):] if parts[:len(mod)] == mod else parts[-1:]
            out.append((m["module"], "*" + "::".join(rel[-2:])))
    return out


def selector_args(module: str, fn: str) -> list[str]:
    scope = ["--verify-only-module", module] if module else ["--verify-root"]
    return [*scope, "--verify-function", fn, "--num-threads", "1", "--output-json"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--sample", type=int, default=12)
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    cmd = ["rustup", "run", "1.88.0-x86_64-unknown-linux-gnu", str(DEFAULT_RUST_VERIFY)]
    env = verus_env({"VERUS_Z3_PATH": str(Z3)})
    cold_env = {k: v for k, v in env.items() if k != "VERUS_IMPORT_CACHE"}
    results = json.loads(a.out.read_text()) if a.out.exists() else {}
    pool = Pool(cmd, size=1, env={"VERUS_Z3_PATH": str(Z3)})
    for name, (cwd, args) in PROJECTS.items():
        if (a.only and name not in a.only) or name in results:
            continue
        fns = functions(cmd, cold_env, cwd, args)
        random.Random(0).shuffle(fns)
        rows = []
        for module, fn in fns[: a.sample]:
            req = [*args, *selector_args(module, fn)]
            row = {"module": module, "function": fn, "cold": [], "warm": [], "warm_fast": []}
            for _ in range(a.repeats):
                t0 = time.monotonic()
                p = subprocess.run([*cmd, *req], cwd=cwd, env=cold_env, capture_output=True, text=True,
                                   timeout=a.timeout)
                row["cold"].append({"wall_s": time.monotonic() - t0, "res": verdict(p.stdout)})
                for arm, extra in (("warm", []), ("warm_fast", ["--no-lifetime"])):
                    r = pool.run(str(cwd), [*req, *extra], a.timeout)
                    res = verdict(r.get("stdout", ""))
                    rec = {"wall_s": r["wall_s"], "res": res, "rc": r.get("rc"),
                           "crashed": r.get("crashed", False), "timed_out": r.get("timed_out", False)}
                    if not res:
                        rec["stderr_tail"] = r.get("stderr", "")[-2000:]
                        rec["stdout_tail"] = r.get("stdout", "")[-500:]
                    row[arm].append(rec)
            rows.append(row)
        ok = [r for r in rows if r["cold"][0]["res"].get("verified")]
        summary = {"functions_sampled": len(rows), "selector_ok": len(ok),
                   "verdict_mismatch": sum((c["res"].get("verified"), c["res"].get("errors"))
                                           != (w["res"].get("verified"), w["res"].get("errors"))
                                           for r in ok for c, w in zip(r["cold"], r["warm"]))}
        for arm in ("cold", "warm", "warm_fast"):
            v = [st.median(x["wall_s"] for x in r[arm]) for r in ok]
            summary[f"{arm}_median_s"] = round(st.median(v), 2) if v else None
        results[name] = {"summary": summary, "rows": rows}
        a.out.write_text(json.dumps(results, indent=1))
        print(name, json.dumps(summary), flush=True)
    pool.close()


if __name__ == "__main__":
    main()
