#!/usr/bin/env python3
"""Conservative proof-only edit guard (local substitute for Lynette).

Checks that `new` differs from `ref` only in proof content:
  * every fn in `ref` still exists with an identical header (attributes,
    signature, requires/ensures/decreases), compared modulo whitespace;
  * spec fn bodies are identical; exec fn bodies are identical after removing
    proof blocks and assert statements;
  * proof fn bodies may change freely;
  * new fns must be `proof fn` lemmas;
  * text outside fn items is identical apart from `use` / `broadcast use` lines;
  * no new assume/admit/external_body/external/rlimit attributes appear.

It errs on the side of rejecting. It is not a full Rust parser.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

FN_RE = re.compile(
    r"(?m)^[ \t]*((?:#\[[^\]]*\]\s*|#!\[[^\]]*\]\s*)*)"            # attributes
    r"((?:pub(?:\([^)]*\))?\s+)?(?:(?:open|closed|uninterp)\s+)*"
    r"(?:(?:spec|proof|exec)(?:\(checked\))?\s+)?(?:const\s+|unsafe\s+|broadcast\s+)*fn\s+(\w+))"
)
FORBIDDEN = [r"\bassume\s*\(", r"\badmit\s*\(", r"external_body", r"verifier::external\b",
             r"verifier\(external\)", r"verifier::rlimit", r"verifier\(rlimit",
             r"assume_specification", r"\bunsafe\b"]
SPINOFF = r"#\s*\[\s*verifier\s*(::\s*spinoff_prover|\(\s*spinoff_prover\s*\))\s*\]"


def strip_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def match_brace(s: str, i: int) -> int:
    """Index just past the brace block opening at s[i] == '{'."""
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        elif c == '"':
            j += 1
            while j < len(s) and s[j] != '"':
                j += 2 if s[j] == "\\" else 1
        j += 1
    raise ValueError("unbalanced braces")


def items(text: str):
    """Yield (name, mode, header, body, start, end) for every fn with a body."""
    out = []
    for m in FN_RE.finditer(text):
        start = m.start()
        sig_kw = m.group(2)
        mode = "proof" if re.search(r"\bproof\b", sig_kw) else (
            "spec" if re.search(r"\bspec\b", sig_kw) else "exec")
        # find body: first '{' at paren depth 0 after the name, skipping
        # brace blocks belonging to requires/ensures expressions is hard; we
        # take the first '{' that follows a line break or ')' / type at depth 0.
        j = m.end()
        par = 0
        body_start = None
        while j < len(text):
            c = text[j]
            if c in "([":
                par += 1
            elif c in ")]":
                par -= 1
            elif c == ";" and par == 0:
                break  # declaration without body
            elif c == "{" and par == 0:
                body_start = j
                break
            j += 1
        if body_start is None:
            out.append((m.group(3), mode, norm(text[start:j]), "", start, j))
            continue
        end = match_brace(text, body_start)
        out.append((m.group(3), mode, norm(text[start:body_start]), text[body_start:end], start, end))
    # drop fns nested inside other fns (keep outermost)
    out.sort(key=lambda t: t[4])
    keep, last_end = [], -1
    for it in out:
        if it[4] >= last_end:
            keep.append(it)
            last_end = it[5]
    return keep


def strip_proof(body: str) -> str:
    """Remove proof blocks and assert statements from an exec body."""
    s = body
    while True:
        m = re.search(r"\bproof\s*\{", s)
        if not m:
            break
        e = match_brace(s, m.end() - 1)
        s = s[: m.start()] + s[e:]
    out = []
    i = 0
    for m in re.finditer(r"\bassert\b|\blet\s+(ghost|tracked)\b|\bbroadcast\s+use\b", s):
        if m.start() < i:
            continue
        # skip to end of statement: matching ';' at depth 0
        j, depth = m.start(), 0
        while j < len(s):
            if s[j] in "({[":
                depth += 1
            elif s[j] in ")}]":
                depth -= 1
            elif s[j] == ";" and depth == 0:
                break
            j += 1
        out.append(s[i: m.start()])
        i = j + 1
    out.append(s[i:])
    return norm("".join(out))


def outside(text: str, its) -> str:
    parts, i = [], 0
    for it in its:
        parts.append(text[i: it[4]])
        i = it[5]
    parts.append(text[i:])
    lines = [l for l in "".join(parts).splitlines()
             if not re.match(r"\s*(broadcast\s+)?use\b", l)]
    return norm("\n".join(lines))


def check(ref_text: str, new_text: str) -> list[str]:
    # spinoff_prover only changes how the query is sent to Z3, never what is
    # proved, so adding or removing it is a proof-only change.
    ref, new = (re.sub(SPINOFF, "", strip_comments(t)) for t in (ref_text, new_text))
    errs = []
    for pat in FORBIDDEN:
        if len(re.findall(pat, new)) > len(re.findall(pat, ref)):
            errs.append(f"new forbidden construct: {pat}")
    ri, ni = items(ref), items(new)
    rmap, nmap = defaultdict(list), defaultdict(list)
    for it in ri:
        rmap[it[0]].append(it)
    for it in ni:
        nmap[it[0]].append(it)
    for name, rs in rmap.items():
        ns = nmap.get(name, [])
        if len(ns) < len(rs):
            errs.append(f"fn removed: {name}")
            continue
        for r in rs:
            cands = [n for n in ns if n[2] == r[2]]
            if not cands:
                errs.append(f"header changed: {name}")
                continue
            if r[1] == "proof":
                continue
            if r[1] == "spec" and not any(norm(n[3]) == norm(r[3]) for n in cands):
                errs.append(f"spec body changed: {name}")
            if r[1] == "exec" and not any(strip_proof(n[3]) == strip_proof(r[3]) for n in cands):
                errs.append(f"exec body changed: {name}")
    for name, ns in nmap.items():
        extra = len(ns) - len(rmap.get(name, []))
        if extra > 0:
            new_modes = Counter(n[1] for n in ns) - Counter(r[1] for r in rmap.get(name, []))
            if any(mode != "proof" for mode in new_modes.elements()):
                errs.append(f"new non-proof fn: {name}")
    if outside(ref, ri) != outside(new, ni):
        errs.append("non-fn text changed")
    return errs


if __name__ == "__main__":
    e = check(Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text())
    print("OK" if not e else "\n".join(e))
    sys.exit(1 if e else 0)
