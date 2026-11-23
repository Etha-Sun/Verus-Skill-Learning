#!/usr/bin/env python3
"""Fast check of one function in a large Verus crate by stubbing every other body.

Copies the crate and, inside `verus!` blocks, replaces the bodies of all
proof and exec functions except the target with trusted
`#[verifier::external_body]` stubs. Items, signatures, requires/ensures and
spec function bodies stay, so the target's proof obligation sees the same
callee specs; rustc and Verus no longer type-check and convert the other
bodies. Verus then also prunes the module context to what the remaining
bodies use, so the target's query can only lose declarations it cannot call.
The result is a filter for iteration only: the final verdict must come from
the full in-repository check.

Function spans come from `fnspans` (a syn_verus parser, verus-speed/fnspans);
a file it cannot parse is left unchanged. Kept unchanged: spec functions,
the target, proof functions that return a value (a stub could not produce
it), functions already external or used as termination / recommends proofs,
const/unsafe/async/extern functions, and everything outside `verus!`.

  python3 verus-speed/slice_stub.py CRATE_DIR OUT_DIR --keep NAME [--keep NAME ...]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

FNSPANS = Path(os.environ.get("FNSPANS", Path.home() / ".cache/verus-skill/build/fnspans/release/fnspans"))
SKIP_ATTR = re.compile(r"verifier\s*(::|\()\s*(external|external_body|admit|decreases_by|via_fn|recommends_by)\b"
                       r"|via_fn")


def spans(files: list[Path]) -> dict[str, dict]:
    out = {}
    for i in range(0, len(files), 200):
        p = subprocess.run([str(FNSPANS), *map(str, files[i:i + 200])], capture_output=True, text=True,
                           check=True)
        for line in p.stdout.splitlines():
            d = json.loads(line)
            out[d["file"]] = d
    return out


def offset_table(text: str) -> list[int]:
    starts, pos = [0], 0
    for line in text.split("\n"):
        pos += len(line) + 1
        starts.append(pos)
    return starts


def fn_items(text: str, info: dict) -> list[dict]:
    """Functions of one file with char offsets added (item, b0 = body start, b1 = body end)."""
    lines = offset_table(text)
    out = []
    for f in info.get("functions", []):
        (il, _), (bl, bc), (el, ec) = f["item_start"], f["body_start"], f["body_end"]
        b0, b1 = lines[bl - 1] + bc, lines[el - 1] + ec
        if text[b0:b0 + 1] != "{" or text[b1 - 1:b1] != "}":
            continue  # span does not line up with the text; leave this function alone
        out.append({**f, "item": lines[il - 1], "b0": b0, "b1": b1})
    return out


def stub_text(text: str, info: dict, keep: set[str], suffix: bool = False) -> tuple[str, int]:
    """keep: names to leave intact; with suffix, also every name ending in one of
    them (Verus's `--verify-function '*name'` matches that way)."""
    edits = []
    for f in fn_items(text, info):
        kept = f["name"] in keep or (suffix and any(f["name"].endswith(k) for k in keep))
        if kept or f["mode"] == "spec" or not f["in_verus"] or f["qualifiers"]:
            continue
        if any(SKIP_ATTR.search(a) for a in f["attrs"]):
            continue
        if f["mode"] == "proof" and f["returns"]:
            continue
        new_body = "{}" if f["mode"] == "proof" else "{ unimplemented!() }"
        indent = re.match(r"[ \t]*", text[f["item"]:]).group(0)
        edits.append((f["item"], f["item"], f"{indent}#[verifier::external_body]\n"))
        edits.append((f["b0"], f["b1"], new_body))
    for a, b, s in sorted(edits, key=lambda e: e[0], reverse=True):
        text = text[:a] + s + text[b:]
    return text, len(edits) // 2


def stub_crate(src: Path, dst: Path, keep: set[str], suffix: bool = False) -> dict:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True,
                    ignore=lambda d, names: ["target"] if Path(d).name == "deps_hack" else [])
    tgt = src / "deps_hack" / "target"
    if tgt.exists():
        (dst / "deps_hack" / "target").symlink_to(tgt)
    files = [f for f in dst.rglob("*.rs") if "deps_hack" not in f.parts and not f.is_symlink()]
    info = spans(files)
    stats = {"files": len(files), "unparsed": 0, "stubbed": 0, "bytes_before": 0, "bytes_after": 0}
    for f in files:
        text = f.read_text()
        d = info.get(str(f), {})
        stats["unparsed"] += "error" in d
        new, n = stub_text(text, d, keep, suffix)
        stats["stubbed"] += n
        stats["bytes_before"] += len(text)
        stats["bytes_after"] += len(new)
        if n:
            f.write_text(new)
    return stats


def locate(crate: Path, name: str) -> list[tuple[Path, int]]:
    """(file, body start offset) of every function with this name and a body."""
    files = [f for f in crate.rglob("*.rs") if "deps_hack" not in f.parts and not f.is_symlink()]
    files = [f for f in files if name in f.read_text()]
    info = spans(files) if files else {}
    hits = []
    for f in files:
        text = f.read_text()
        hits += [(f, x["b0"]) for x in fn_items(text, info.get(str(f), {})) if x["name"] == name]
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--keep", action="append", default=[])
    a = ap.parse_args()
    print(stub_crate(a.src, a.dst, set(a.keep)))


if __name__ == "__main__":
    main()
