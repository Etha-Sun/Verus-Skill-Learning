#!/usr/bin/env python3
"""Rewrite one verified Verus file into a cheaper proof that still verifies.

Thin single-file front end to scripts/proof_time/speed_search.py (delete an
unneeded assert / assert-by / assert-forall / reveal / `broadcast use`, or add
`#[verifier::spinoff_prover]`; keep a change only if the file still verifies
and exact Z3 rlimit drops; confirm the result on two more seeds).
Candidates are costed with `fast_cost.py` (one capped solve) unless --slow.

Files whose solver time is below --min-smt-ms are returned unchanged: on such
files the removable cost is about 4% and the search costs more than it saves.

  python3 verus-speed/auto_speed.py PROOF.rs --target FN --out-dir RUN/auto/NAME
  [--source ORIGINAL_TASK.rs]   also reject edits outside proof code
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/proof_time"))

import fast_cost  # noqa: E402
import speed_search  # noqa: E402
from optimize_proof import verify  # noqa: E402


def use_fast_costing() -> None:
    """Make the search cost candidates with one capped solve instead of two.

    The first call (the input proof) and the final seed confirmations still go
    through normal Verus; only intermediate candidates use the filter. The cap
    is the input's total cost: a candidate above it cannot be an improvement.
    """
    state: dict = {}

    def fast_verify(text: str, seed: int = 0, timeout: int = 900) -> dict:
        if "cap" not in state or seed != 0:
            r = verify(text, seed=seed, timeout=timeout)
            if r["success"]:
                state.setdefault("cap", r["rlimit"])
            return r
        return fast_cost.verify(text, timeout=timeout, cap=state["cap"])

    speed_search.verify = fast_verify


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("proof", type=Path)
    ap.add_argument("--target", required=True, help="function whose proof may be rewritten")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--source", type=Path)
    ap.add_argument("--min-smt-ms", type=float, default=1000)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--inner-workers", type=int, default=8)
    ap.add_argument("--slow", action="store_true", help="cost every candidate with two full solves")
    a = ap.parse_args()

    base = verify(a.proof.read_text(), timeout=a.timeout)
    if not base["success"]:
        print(json.dumps({"changed": False, "reason": "input does not verify"}))
        return
    if base["smt_ms"] < a.min_smt_ms:
        print(json.dumps({"changed": False, "reason": "solver time below threshold",
                          "smt_ms": base["smt_ms"], "rlimit": base["rlimit"]}))
        return
    task = {"task_id": a.proof.stem, "candidate_path": str(a.proof), "target_function": a.target,
            "timeout": a.timeout}
    if a.source:
        task["source_path"] = str(a.source)
    if not a.slow:
        use_fast_costing()
    out = speed_search.search(task, a)
    best = a.out_dir / a.proof.stem / "best.rs"
    print(json.dumps({"changed": bool(out.get("applied")), "rlimit_ratio": out.get("ratio"),
                      "edits": len(out.get("applied") or []), "seeds_ok": out.get("seeds_ok"),
                      "best": str(best)}))


if __name__ == "__main__":
    main()
