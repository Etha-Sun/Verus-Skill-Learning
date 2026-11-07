#!/usr/bin/env python3
"""Collect verified Verus candidates from local runs and measure proof time.

Subcommands:
  collect  scan run roots for verified candidates (workspace/candidate.rs next
           to a result.json whose final Verus check passed); dedupe by content.
  measure  re-verify each unique candidate K times with different Z3 seeds and
           record wall time, SMT time and Z3 rlimit-count (total and per function).

Outputs go to --out-dir (must be outside the repository, below the run root).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

DEFAULT_VERUS = Path.home() / ".cache/verus-skill/toolchains/bb1f342/verus-release/verus"


def verus_env() -> dict[str, str]:
    env = dict(os.environ)
    base = Path.home() / ".cache/verus-skill"
    env.setdefault("RUSTUP_HOME", str(base / "rustup"))
    env.setdefault("CARGO_HOME", str(base / "cargo"))
    env["PATH"] = f"{env['CARGO_HOME']}/bin:{env['PATH']}"
    return env


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


PROOF_PATTERNS = {
    "assert": r"\bassert\s*\(",
    "assert_forall": r"\bassert\s+forall\b",
    "assert_by": r"\bassert\s*\([^;]*\)\s*by\b",
    "forall": r"\bforall\s*\|",
    "exists": r"\bexists\s*\|",
    "trigger_attr": r"#\[\s*trigger\s*\]",
    "auto_trigger": r"#!\[\s*auto\s*\]",
    "broadcast_use": r"\bbroadcast\s+use\b",
    "reveal": r"\breveal(_with_fuel)?\s*\(",
    "nonlinear": r"nonlinear_arith",
    "bit_vector": r"bit_vector",
    "proof_block": r"\bproof\s*\{",
    "lemma_call": r"\blemma_\w+\s*\(",
    "decreases": r"\bdecreases\b",
    "invariant": r"\binvariant\b",
}


def static_features(text: str) -> dict[str, int]:
    feats = {k: len(re.findall(p, text)) for k, p in PROOF_PATTERNS.items()}
    feats["lines"] = text.count("\n")
    return feats


def fixture_sources(repo: Path) -> dict[str, dict]:
    """Map source sha256 -> fixture item (split, task id, source path)."""
    out = {}
    fx = repo / "fixed-claude-stratified-80-seed20260814"
    for split in ("train", "val", "test"):
        for it in json.loads((fx / split / "items.json").read_text()):
            out[it["source_sha256"]] = {"split": split, "task_id": it["task_id"],
                                        "path": repo / it["source_path"]}
    return out


def locate(run_dir: Path, res: dict, fixture: dict[str, dict]) -> tuple[Path | None, Path | None]:
    """Find the final candidate and original source for a run directory.

    Live runs keep workspace/{candidate,input}.rs; archived runs keep only
    snapshots, so the final candidate is the snapshot whose hash matches the
    validated candidate and the source comes from the fixed fixture.
    """
    ws = run_dir / "workspace"
    if (ws / "candidate.rs").exists() and (ws / "input.rs").exists():
        return ws / "candidate.rs", ws / "input.rs"
    want = (res.get("validation") or {}).get("candidate_sha256")
    cand = None
    for snap in sorted(run_dir.glob("snapshots/*-candidate.rs")):
        if sha256(snap) == want:
            cand = snap
    try:
        manifest = json.loads((run_dir / "run_manifest.json").read_text())
    except Exception:
        manifest = {}
    item = fixture.get(manifest.get("source_sha256"))
    return cand, (item["path"] if item else None)


def collect(args: argparse.Namespace) -> None:
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    fixture = fixture_sources(Path(__file__).resolve().parents[2])
    by_sha = {k: v["task_id"] for k, v in fixture.items()}
    seen: dict[str, dict] = {}
    for root in args.run_roots:
        for result in sorted(root.rglob("result.json")):
            run_dir = result.parent
            try:
                res = json.loads(result.read_text())
            except Exception:
                continue
            verus = (res.get("validation") or {}).get("verus") or {}
            if not verus.get("passed"):
                continue
            cand, src = locate(run_dir, res, fixture)
            if cand is None or src is None:
                continue
            csha = sha256(cand)
            ssha = sha256(src)
            if csha == ssha:
                continue
            rel = str(run_dir.relative_to(root.parent))
            arm = re.sub(r"(/|--)[0-9a-f]{20}$", "", rel)
            rec = seen.setdefault(csha, {
                "candidate_sha256": csha,
                "source_sha256": ssha,
                "task_id": by_sha.get(ssha),
                "candidate_path": str(cand),
                "source_path": str(src),
                "arms": [],
                "historical_final_verus_seconds": verus.get("wall_seconds"),
                "solved_within_budget": res.get("within_budget"),
            })
            rec["arms"].append(arm)
    rows = list(seen.values())
    for r in rows:
        ctext = Path(r["candidate_path"]).read_text(errors="replace")
        stext = Path(r["source_path"]).read_text(errors="replace")
        cf_, sf = static_features(ctext), static_features(stext)
        r["features_delta"] = {k: cf_[k] - sf[k] for k in cf_}
        r["source_lines"] = sf["lines"]
    with (out / "candidates.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    tasks = {r["source_sha256"] for r in rows}
    print(f"unique verified candidates: {len(rows)} across {len(tasks)} source tasks")


def run_once(verus: Path, cand: Path, seed: int, rlimit: float | None, timeout: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="ptime-") as tmp:
        target = Path(tmp) / "candidate.rs"
        shutil.copyfile(cand, target)
        cmd = [str(verus), "candidate.rs", "--time-expanded", "--output-json",
               "--smt-option", f"smt.random_seed={seed}"]
        if rlimit is not None:
            cmd += ["--rlimit", str(rlimit)]
        t0 = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=tmp, env=verus_env(), capture_output=True,
                                  text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"seed": seed, "timed_out": True, "wall_seconds": time.monotonic() - t0}
        wall = time.monotonic() - t0
    rec = {"seed": seed, "timed_out": False, "returncode": proc.returncode, "wall_seconds": wall}
    try:
        data = json.loads(proc.stdout)
    except Exception:
        rec["parse_error"] = proc.stdout[-500:] + proc.stderr[-500:]
        return rec
    vr = data.get("verification-results", {})
    rec["verified"] = vr.get("verified")
    rec["errors"] = vr.get("errors")
    rec["success"] = bool(vr.get("success"))
    times = data.get("times-ms", {})
    smt = times.get("smt", {})
    rec["total_ms"] = times.get("total")
    rec["smt_run_ms"] = smt.get("smt-run")
    funcs = []
    rl_total = 0
    for mod in smt.get("smt-run-module-times", []):
        rl_total += mod.get("rlimit-count", 0) or 0
        for f in mod.get("function-breakdown", []):
            funcs.append({"function": f["function"], "micros": f.get("time-micros"),
                          "rlimit": f.get("rlimit-count"), "success": f.get("success")})
    rec["rlimit_total"] = rl_total
    rec["functions"] = funcs
    return rec


def measure(args: argparse.Namespace) -> None:
    rows = [json.loads(l) for l in (args.out_dir / "candidates.jsonl").read_text().splitlines()]
    if args.limit:
        rows = rows[: args.limit]
    out_path = args.out_dir / args.output
    done = set()
    if out_path.exists():
        for l in out_path.read_text().splitlines():
            r = json.loads(l)
            done.add((r["candidate_sha256"], r["seed"]))
    jobs = [(r, s) for r in rows for s in range(args.repeats) if (r["candidate_sha256"], s) not in done]
    print(f"{len(jobs)} verification jobs, {args.workers} workers")
    with out_path.open("a") as fh, cf.ThreadPoolExecutor(args.workers) as pool:
        futs = {pool.submit(run_once, args.verus, Path(r["candidate_path"]), s, args.rlimit,
                            args.timeout): (r, s) for r, s in jobs}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            r, s = futs[fut]
            rec = fut.result()
            rec["candidate_sha256"] = r["candidate_sha256"]
            rec["source_sha256"] = r["source_sha256"]
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            if i % 50 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--run-roots", type=Path, nargs="+", required=True)
    c.add_argument("--out-dir", type=Path, required=True)
    m = sub.add_parser("measure")
    m.add_argument("--out-dir", type=Path, required=True)
    m.add_argument("--output", default="measurements.jsonl")
    m.add_argument("--verus", type=Path, default=DEFAULT_VERUS)
    m.add_argument("--repeats", type=int, default=10)
    m.add_argument("--workers", type=int, default=16)
    m.add_argument("--rlimit", type=float)
    m.add_argument("--timeout", type=int, default=900)
    m.add_argument("--limit", type=int)
    args = ap.parse_args()
    {"collect": collect, "measure": measure}[args.cmd](args)


if __name__ == "__main__":
    main()
