#!/usr/bin/env python3
"""Summarize speed_search results: final ratios, beneficial single changes by kind
and by asserted-statement shape (does it assert a predicate call, a quantifier,
an equality/arithmetic fact, ...)."""
import json, re, statistics as st, sys
from collections import defaultdict, Counter
from pathlib import Path

def shape(stmt: str) -> str:
    s = " ".join(stmt.split())
    if s.startswith("#[verifier::spinoff_prover]"): return "spinoff"
    if s.startswith("broadcast use"): return "broadcast_use"
    if s.startswith("reveal"): return "reveal"
    m = re.match(r"assert\s*\((.*)\)\s*(by.*)?;?$", s)
    body = m.group(1) if m else s
    if re.match(r"assert\s+forall", s) or body.lstrip("(").startswith("forall"): return "quantified"
    if re.search(r"\bexists\b", body): return "quantified"
    if re.search(r"\.(contains|dom|len|index)\b|\[", body) and re.search(r"==|<|>", body): return "collection_fact"
    if re.search(r"(==|!=|<=|>=|<|>)", body) and not re.search(r"\w\s*\(", body.split("==")[0]): return "equality_or_arith"
    if re.fullmatch(r"[\w:.@!&\s]*\w+(::<[^>]*>)?\s*\(.*\)(\.\w+\(.*\))*", body.strip()): return "predicate_call"
    if re.search(r"==", body): return "equality_of_calls"
    return "other"

root = Path(sys.argv[1])
fins = [json.loads(p.read_text()) for p in root.glob("*/final.json")]
fins = [f for f in fins if "ratio" in f]
r = [f["ratio"] for f in fins]
print(f"tasks {len(fins)} | final ratio geomean {st.geometric_mean(r):.3f} median {st.median(r):.3f} | "
      f"<0.95: {sum(x<0.95 for x in r)} <0.8: {sum(x<0.8 for x in r)} <0.5: {sum(x<0.5 for x in r)} | seeds_ok {sum(f['seeds_ok'] for f in fins)}")
print("best single ratio median", round(st.median(f["best_single_ratio"] for f in fins), 3))
tot = Counter(); ben = defaultdict(list); n_ok = Counter()
for p in root.glob("*/singles.jsonl"):
    for l in p.read_text().splitlines():
        s = json.loads(l); k = s["kind"] if s["kind"] in ("add_spinoff","del_broadcast_use","del_reveal") else shape(s["stmt"])
        tot[k] += 1
        if s["success"]:
            n_ok[k] += 1
            ben[k].append(s["ratio"])
print(f"{'statement shape':20} {'n':>5} {'deletable':>9} {'saves>5%':>8} {'saves>20%':>9} {'median ratio (ok)':>17}")
for k in sorted(tot, key=lambda k: -tot[k]):
    v = ben[k]
    print(f"{k:20} {tot[k]:5} {n_ok[k]:9} {sum(x<0.95 for x in v):8} {sum(x<0.8 for x in v):9} {st.median(v) if v else float('nan'):17.3f}")
