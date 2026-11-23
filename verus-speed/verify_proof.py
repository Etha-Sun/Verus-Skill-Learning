#!/usr/bin/env python3
"""Trusted verification of a candidate proof against the original task (AXLE `verify_proof` for Verus).

A candidate is accepted only if
1. Verus verifies it, and
2. it is the original task with proof code added (lynette `additions` or the
   repository proof guard: exec code, signatures and specs unchanged), and it
   adds no trust escape. Trust escapes are counted on a token stream (comments and
   whitespace removed), so `assume (`, `#[verifier(external_body)]` and the
   like cannot slip past a plain-text count, and a candidate may not move an
   escape that exists in the original (for example a dependency stub) to
   another function.

The structural check takes about 0.1 s and runs in parallel with Verus.

  python3 verus-speed/verify_proof.py ORIGINAL.rs CANDIDATE.rs
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/proof_time"))
from proof_guard import check as guard_check  # noqa: E402

CACHE = Path.home() / ".cache/verus-skill"
LYNETTE = Path(os.environ.get("LYNETTE", CACHE / "build/lynette/release/lynette"))
VERUS = CACHE / "toolchains/bb1f342/verus-release/verus"

# Each pattern runs on the token stream (no whitespace, no comments).
ESCAPES = {
    # statements, also path-qualified (builtin::admit(), vstd::prelude::assume_(...))
    "assume": r"(?<!\w)assume_?\(",
    "admit": r"(?<!\w)admit\(",
    # attributes in any position (#[...], #![...], cfg_attr(..., ...)) and either syntax
    "external_body": r"verifier(::external_body|\(external_body\))\b",
    "external": r"verifier(::external|\(external\))(?!_)\b",
    "admit_attr": r"verifier(::admit|\(admit\))\b",
    "assume_specification": r"assume_specification",
    "external_fn_specification": r"external_fn_specification",
    "external_type_specification": r"external_type_specification",
    "external_trait_specification": r"external_trait_specification",
    "trusted": r"verus::trusted",
    "unsafe": r"(?<!\w)unsafe(?!\w)",
    "no_decreases": r"exec_allows_no_decreases_clause",
    "inline_air": r"inline_air_stmt",
}
FN_NAME = re.compile(r"fn(\w+)")


def tokens(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return re.sub(r"\s+", "", text)


def escapes(text: str) -> Counter:
    """(kind, enclosing fn) -> count, on the token stream."""
    t = tokens(text)
    fn_starts = [(m.start(), m.group(1)) for m in FN_NAME.finditer(t)]
    out: Counter = Counter()
    for kind, pat in ESCAPES.items():
        for m in re.finditer(pat, t):
            # attributes belong to the next fn, statements to the previous one
            if kind in ("assume", "admit", "unsafe", "inline_air"):
                owner = next((n for s, n in reversed(fn_starts) if s < m.start()), "<top>")
            else:
                owner = next((n for s, n in fn_starts if s > m.start()), "<end>")
            out[(kind, owner)] += 1
    return out


def structure(original: str, candidate: str) -> list[str]:
    """Problems that make the candidate not a proof-only change of the original.

    Two structural checks with different blind spots are combined: lynette
    `additions` (AST level) and the repository's proof guard
    (scripts/proof_time/proof_guard.py: headers, spec bodies and proof-stripped
    exec bodies unchanged). The candidate passes if either accepts it; trust
    escapes are checked separately and always apply."""
    problems = []
    extra = escapes(candidate) - escapes(original)
    for (kind, owner), n in sorted(extra.items()):
        problems.append(f"new trust escape: {kind} in {owner} (x{n})")
    with tempfile.TemporaryDirectory(prefix="vproof_") as d:
        o, c = Path(d) / "orig.rs", Path(d) / "cand.rs"
        o.write_text(original)
        c.write_text(candidate)
        # `additions`, not `compare`: compare extracts pure Rust and so drops proof
        # functions, including their requires/ensures.
        p = subprocess.run([str(LYNETTE), "additions", str(o), str(c)], capture_output=True, text=True)
    if p.returncode != 0:
        guard_errors = guard_check(original, candidate)
        if guard_errors:
            out = (p.stdout + p.stderr).strip()[-160:]
            problems.append(f"not a proof-only change (lynette: {out}; guard: {guard_errors[:2]})")
    return problems


def verify(candidate: str, timeout: int = 900, extra_args: list[str] | None = None) -> dict:
    d = Path(tempfile.mkdtemp(prefix="vproofv_"))
    try:
        (d / "candidate.rs").write_text(candidate)
        env = dict(os.environ, RUSTUP_HOME=str(CACHE / "rustup"), CARGO_HOME=str(CACHE / "cargo"))
        env["PATH"] = f"{CACHE / 'cargo/bin'}:{env.get('PATH', '')}"
        try:
            p = subprocess.run([str(VERUS), "candidate.rs", "--output-json", *(extra_args or [])], cwd=d,
                               env=env, capture_output=True, text=True, timeout=timeout)
            res = json.loads(p.stdout).get("verification-results", {})
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            res = {}
        return {"verified": bool(res.get("success")), "errors": res.get("errors")}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def verify_proof(original: str, candidate: str, timeout: int = 900) -> dict:
    with ThreadPoolExecutor(2) as ex:
        s = ex.submit(structure, original, candidate)
        v = ex.submit(verify, candidate, timeout)
        problems, ver = s.result(), v.result()
    return {"okay": ver["verified"] and not problems, "verified": ver["verified"], "problems": problems}


def main() -> None:
    orig, cand = (Path(p).read_text() for p in sys.argv[1:3])
    print(json.dumps(verify_proof(orig, cand), indent=1))


if __name__ == "__main__":
    main()
