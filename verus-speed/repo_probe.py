#!/usr/bin/env python3
"""Find which Verus projects verify cleanly with which toolchain, and how long it takes.

Each entry of PROBES names a clone under $VERUS_SPEED_REPOS, a commit, a
toolchain ("old" = 0.2025.09.12, "new" = 0.2026.11.02) and how to verify:
`file` runs `verus ROOT ARGS`, `cargo` runs `cargo verus verify ARGS` in DIR.
Every probe gets its own git worktree, so clones are never moved.

  python3 verus-speed/repo_probe.py --out RUN/probe.jsonl [--only NAME ...]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CACHE = Path.home() / ".cache/verus-skill"
REPOS = Path(os.environ.get("VERUS_SPEED_REPOS", CACHE / "src/repos"))
WORKTREES = Path(os.environ.get("VERUS_SPEED_WORKTREES", CACHE / "src/worktrees"))
TOOLCHAINS = {
    "old": {"bin": CACHE / "toolchains/bb1f342/verus-release", "z3": None},
    "new": {"bin": CACHE / "toolchains/8bf68ee/verus-x86-linux", "z3": CACHE / "toolchains/z3-4.16.0/z3"},
}
SEPT = "2025-10-15"  # last commit before this date is the "old" pin

# name, repo, commit ("sept" | "HEAD" | sha), toolchain, mode, dir (in repo), root/args
PROBES = [
    ("ironkv-old", "verified-ironkv", "472c621", "old", "file", "ironsht/src", ["lib.rs", "--crate-type=dylib"]),
    ("ironkv-new", "verified-ironkv", "HEAD", "new", "file", "ironsht/src", ["lib.rs", "--crate-type=dylib"]),
    ("nrkernel-old", "verified-nrkernel", "733950a", "old", "file", "page-table/src",
     ["lib.rs", "--crate-type=lib", "--cfg", 'feature="impl"', "--rlimit", "30"]),
    ("nrkernel-new", "verified-nrkernel", "HEAD", "new", "file", "page-table/src",
     ["lib.rs", "--crate-type=lib", "--cfg", 'feature="impl"', "--rlimit", "30"]),
    ("noderep-old", "verified-node-replication", "c3acacf", "old", "file", "verified-node-replication/src",
     ["lib.rs", "--crate-type=lib"]),
    ("noderep-new", "verified-node-replication", "HEAD", "new", "file", "verified-node-replication/src",
     ["lib.rs", "--crate-type=lib"]),
    ("verified-pt-old", "verified-pt", "HEAD", "old", "file", "src", ["lib.rs", "--crate-type=lib"]),
    ("mimalloc-old", "verified-memory-allocator", "sept", "old", "file", "verus-mimalloc",
     ["lib.rs", "--crate-type=lib", "--extern", "libc=../build/liblibc.rlib"]),
    ("mimalloc-new", "verified-memory-allocator", "HEAD", "new", "file", "verus-mimalloc",
     ["lib.rs", "--crate-type=lib", "--extern", "libc=../build/liblibc.rlib"]),
    ("vest-old", "vest", "sept", "old", "file", "vest/src", ["lib.rs", "--crate-type=lib"]),
    ("vest-new", "vest", "HEAD", "new", "cargo", ".", []),
    ("pmemlog-old", "verified-storage", "sept", "old", "cargo", "pmemlog", []),
    ("pmemlog-new", "verified-storage", "HEAD", "new", "cargo", "pmemlog", []),
    ("capybarakv-old", "verified-storage", "sept", "old", "cargo", "capybaraKV/capybarakv", []),
    ("capybarakv-new", "verified-storage", "HEAD", "new", "cargo", "capybaraKV/capybarakv", []),
    ("multilog-old", "verified-storage", "sept", "old", "cargo", "multilog/multilog", []),
    ("multilog-new", "verified-storage", "HEAD", "new", "cargo", "multilog/multilog", []),
    ("cedar-json-new", "cedar-json-parser", "HEAD", "new", "cargo", ".", []),
    ("verified-graphs-new", "verified-graphs", "HEAD", "new", "cargo", ".", []),
    ("verified-tiff-new", "verified-tiff", "HEAD", "new", "cargo", ".", []),
    ("veruft-new", "veruft", "HEAD", "new", "cargo", ".", []),
    # single-crate cargo projects, verified directly against the release's own vstd
    ("cedar-json-file-new", "cedar-json-parser", "HEAD", "new", "file", "src", ["lib.rs", "--crate-type=lib"]),
    ("verified-graphs-file-new", "verified-graphs", "HEAD", "new", "file", "src", ["lib.rs", "--crate-type=lib"]),
    ("verified-graphs-file-old", "verified-graphs", "HEAD", "old", "file", "src", ["lib.rs", "--crate-type=lib"]),
    ("veruft-file-new", "veruft", "HEAD", "new", "file", "src", ["lib.rs", "--crate-type=lib"]),
    ("veruft-file-old", "veruft", "sept", "old", "file", "src", ["lib.rs", "--crate-type=lib"]),
    ("verified-pt-new", "verified-pt", "HEAD", "new", "file", "src", ["lib.rs", "--crate-type=lib"]),
    ("vest-lib-old", "vest", "sept", "old", "file", "vest_lib/src", ["lib.rs", "--crate-type=lib"]),
    ("vest-lib-new", "vest", "HEAD", "new", "file", "vest_lib/src", ["lib.rs", "--crate-type=lib"]),
    ("pmemlog-file-old", "verified-storage", "sept", "old", "file", "pmemlog/src", ["lib.rs", "--crate-type=lib"]),
    ("anvil-old", "anvil", "a65d68c1", "old", "file", "src", ["anvil.rs", "--crate-type=lib", "--rlimit", "50"]),
    ("anvil-new", "anvil", "HEAD", "new", "file", "src", ["anvil.rs", "--crate-type=lib", "--rlimit", "50"]),
    ("atmosphere-new", "atmosphere", "HEAD", "new", "file", "kernel/verified", ["lib.rs", "--crate-type=lib"]),
]

RESULT = re.compile(r"verification results:: (\d+) verified, (\d+) errors?")


def env_for(tc: str) -> dict:
    env = dict(os.environ)
    env["RUSTUP_HOME"] = str(CACHE / "rustup")
    env["CARGO_HOME"] = str(CACHE / "cargo")
    env["PATH"] = f"{TOOLCHAINS[tc]['bin']}:{CACHE / 'cargo/bin'}:{env.get('PATH', '')}"
    if TOOLCHAINS[tc]["z3"]:
        env["VERUS_Z3_PATH"] = str(TOOLCHAINS[tc]["z3"])
    return env


def worktree(repo: str, commit: str) -> tuple[Path, str]:
    clone = REPOS / repo
    if commit == "sept":
        branch = subprocess.run(["git", "-C", clone, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
                                capture_output=True, text=True).stdout.strip() or "origin/main"
        commit = subprocess.run(["git", "-C", clone, "rev-list", "-1", f"--before={SEPT}", branch],
                                capture_output=True, text=True).stdout.strip()
    elif commit == "HEAD":
        branch = subprocess.run(["git", "-C", clone, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
                                capture_output=True, text=True).stdout.strip() or "origin/main"
        commit = subprocess.run(["git", "-C", clone, "rev-parse", branch], capture_output=True, text=True).stdout.strip()
    sha = subprocess.run(["git", "-C", clone, "rev-parse", "--short=8", commit],
                         capture_output=True, text=True).stdout.strip()
    wt = WORKTREES / f"{repo}@{sha}"
    if not wt.exists():
        WORKTREES.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", clone, "worktree", "add", "--detach", str(wt), sha],
                       capture_output=True, check=True)
    return wt, sha


def probe(entry, timeout: int, threads: int) -> dict:
    name, repo, commit, tc, mode, sub, args = entry
    try:
        wt, sha = worktree(repo, commit)
    except subprocess.CalledProcessError as e:
        return {"name": name, "error": f"worktree: {e.stderr[-300:] if e.stderr else e}"}
    cwd = wt / sub
    if not cwd.is_dir():
        return {"name": name, "repo": repo, "commit": sha, "clean": False, "error": f"no directory {sub}"}
    if mode == "file":
        cmd = [str(TOOLCHAINS[tc]["bin"] / "verus"), *args, "--num-threads", str(threads)]
    else:
        cmd = ["cargo", "verus", "verify", *args, "--", "--num-threads", str(threads)]
    t0 = time.monotonic()
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env_for(tc), capture_output=True, text=True, timeout=timeout)
        out, rc, timed_out = p.stdout + p.stderr, p.returncode, False
    except subprocess.TimeoutExpired as e:
        out, rc, timed_out = (e.stdout or b"").decode() + (e.stderr or b"").decode(), None, True
    wall = time.monotonic() - t0
    found = [(int(a), int(b)) for a, b in RESULT.findall(out)]
    errors = [l for l in out.splitlines() if l.startswith("error")]
    return {"name": name, "repo": repo, "commit": sha, "toolchain": tc, "mode": mode, "dir": sub,
            "rc": rc, "timed_out": timed_out, "wall_s": round(wall, 1), "crates": len(found),
            "verified": sum(a for a, _ in found), "errors": sum(b for _, b in found),
            "clean": rc == 0 and bool(found) and all(b == 0 for _, b in found),
            "first_errors": sorted(set(errors))[:6]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()
    todo = [p for p in PROBES if not a.only or p[0] in a.only]
    with ThreadPoolExecutor(a.parallel) as pool, a.out.open("a") as fh:
        for r in pool.map(lambda e: probe(e, a.timeout, a.threads), todo):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(json.dumps({k: r.get(k) for k in ("name", "commit", "clean", "verified", "errors",
                                                    "crates", "wall_s", "timed_out")}), flush=True)


if __name__ == "__main__":
    main()
