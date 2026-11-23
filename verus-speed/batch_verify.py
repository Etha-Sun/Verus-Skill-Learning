#!/usr/bin/env python3
"""Verify many independent single-file Verus programs in one Verus invocation.

Each file becomes a module of one synthetic crate, so the per-invocation fixed
cost (rustc start-up, vstd import, Z3 start-up) is paid once and modules are
verified on parallel threads.

Verdict safety:
- A file is reported verified only if no diagnostic points into its module and
  every one of its functions passed.
- A file that fails inside a batch is re-run alone and that verdict is used.
- A batch that cannot be attributed file by file (build error, VIR error,
  unattributed diagnostic) is split in half and retried, down to single runs.
- Files with crate-wide trusted declarations always run alone; files are only
  batched with files declaring the same `global` layout directives.

Library use:  results = verify_batch([Path, ...])
CLI:          python3 verus-speed/batch_verify.py FILE.rs ... [--batch-size 8]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

CACHE = Path.home() / ".cache/verus-skill"
DEFAULT_VERUS = CACHE / "toolchains/bb1f342/verus-release/verus"

# Crate-level items that are only legal (or only resolve as `::name`) in the root.
HOIST = re.compile(r"(?m)^[ \t]*(extern\s+crate\s+[^;]+;|#!\[feature\([^\]]*\])[ \t]*\n?")
GLOBAL = re.compile(r"(?m)^[ \t]*global\s+(?:size_of|layout)\b[^;]*;[ \t]*\n?")
# Crate-wide trusted declarations would leak into the other files of a batch and
# could let a file verify that fails on its own, so such files always run alone.
CRATE_WIDE = re.compile(r"assume_specification|external_fn_specification"
                        r"|external_type_specification|external_trait_specification|broadcast_forall")
EXPORTED_MACRO = re.compile(r"#\[macro_export\]\s*macro_rules!\s*(\w+)")
DIAG = re.compile(r"(?m)^error(?:\[E\d+\])?: (.*)$")


def verus_env() -> dict:
    env = dict(os.environ)
    env["RUSTUP_HOME"] = str(CACHE / "rustup")
    env["CARGO_HOME"] = str(CACHE / "cargo")
    env["PATH"] = f"{CACHE / 'cargo/bin'}:{env.get('PATH', '')}"
    return env


def global_key(text: str) -> tuple[str, ...]:
    """Normalized crate-wide `global size_of/layout` directives of a file."""
    out = set()
    for m in GLOBAL.finditer(text):
        d = re.sub(r"\s*(==|,)\s*", r" \1 ", " ".join(m.group(0).split())[:-1].strip())
        out.add(" ".join(d.split()) + ";")
    return tuple(sorted(out))


def build_crate(files: list[Path], tmp: Path) -> None:
    """All files must share the same global_key; it is declared once in the root."""
    hoisted: list[str] = []
    mods = []
    globals_ = global_key(files[0].read_text())
    for i, f in enumerate(files):
        text = f.read_text()
        for m in HOIST.finditer(text):
            item = " ".join(m.group(1).split())
            if item not in hoisted:
                hoisted.append(item)
        text = GLOBAL.sub("", HOIST.sub("", text))
        # The file's own root is now the module. Exported macros stay at the
        # crate root, so the module imports them to keep bare `name!` working.
        macros = sorted(set(EXPORTED_MACRO.findall(text)))
        text = re.sub(r"(?<![\w$])crate::(\w+|\{)",
                      lambda m: m.group(0) if m.group(1) in macros else f"crate::m{i}::{m.group(1)}", text)
        if macros:
            text += "\n#[allow(unused_imports)] use crate::{" + ", ".join(macros) + "};\n"
        (tmp / f"m{i}.rs").write_text(text)
        mods.append(f'#[path = "m{i}.rs"] mod m{i};')
    inner = [h for h in hoisted if h.startswith("#!")]
    outer = [h for h in hoisted if not h.startswith("#!")]
    root = inner + ["#![allow(unused_imports, dead_code, unused_variables)]"] + outer
    if globals_:
        root += ["use vstd::prelude::*;", "verus! {", *globals_, "}"]
    root += mods + ["fn main() {}"]
    (tmp / "root.rs").write_text("\n".join(root) + "\n")


def run_single(verus: Path, f: Path, flags: list[str], timeout: int) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="vbatch1_"))
    try:
        shutil.copy(f, tmp / "candidate.rs")
        try:
            p = subprocess.run([str(verus), "candidate.rs", "--output-json", "--time", *flags],
                               cwd=tmp, env=verus_env(), capture_output=True, text=True, timeout=timeout)
            res = (json.loads(p.stdout).get("verification-results") or {})
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            res = {}
        return {"success": bool(res.get("success")), "verified": res.get("verified"),
                "errors": res.get("errors"), "mode": "single"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_batch(verus: Path, files: list[Path], flags: list[str], timeout: int) -> list[dict] | None:
    """Per-file results, or None when the outcome cannot be attributed per file."""
    tmp = Path(tempfile.mkdtemp(prefix="vbatch_"))
    try:
        build_crate(files, tmp)
        try:
            p = subprocess.run([str(verus), "root.rs", "--output-json", "--time-expanded", *flags],
                               cwd=tmp, env=verus_env(), capture_output=True, text=True,
                               timeout=timeout * len(files))  # `timeout` is per file
            doc = json.loads(p.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            return None
        res = doc.get("verification-results") or {}
        verified, errors = res.get("verified") or 0, res.get("errors") or 0
        if res.get("encountered-vir-error") or (res.get("encountered-error") and verified + errors == 0):
            return None  # the crate did not reach verification
        out = [{"success": True, "verified": 0, "errors": 0, "mode": "batch"} for _ in files]
        smt = (doc.get("times-ms") or {}).get("smt") or {}
        for mod in smt.get("smt-run-module-times") or []:
            m = re.match(r"m(\d+)(::|$)", mod.get("module") or "")
            if not m:
                continue
            r = out[int(m.group(1))]
            for fn in mod.get("function-breakdown") or []:
                r["verified" if fn.get("success") else "errors"] += 1
                r["success"] = r["success"] and bool(fn.get("success"))
        # Every error diagnostic must point into exactly one module.
        diags = list(DIAG.finditer(p.stderr))
        for j, d in enumerate(diags):
            if d.group(1).startswith("aborting due to"):
                continue
            body = p.stderr[d.end(): diags[j + 1].start() if j + 1 < len(diags) else len(p.stderr)]
            loc = re.search(r"--> m(\d+)\.rs:", body)
            if not loc:
                return None
            out[int(loc.group(1))]["success"] = False
        if bool(res.get("success")) != all(r["success"] for r in out):
            return None
        # A proof near its resource limit can fail inside a batch and pass alone
        # (module renaming perturbs the solver), so a batch failure is re-checked.
        return [r if r["success"] else {**run_single(verus, f, flags, timeout), "mode": "single_recheck"}
                for f, r in zip(files, out)]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _verify_group(files: list[Path], verus: Path, batch_size: int, flags: list[str], timeout: int) -> list[dict]:
    results: list[dict] = []
    for i in range(0, len(files), batch_size):
        chunk = files[i:i + batch_size]
        res = run_batch(verus, chunk, flags, timeout) if len(chunk) > 1 else None
        if res is None:
            if len(chunk) > 2:  # bisect so one bad file does not cost the whole batch
                half = len(chunk) // 2
                res = (_verify_group(chunk[:half], verus, half, flags, timeout)
                       + _verify_group(chunk[half:], verus, len(chunk) - half, flags, timeout))
            else:
                res = [run_single(verus, f, flags, timeout) for f in chunk]
        results += res
    return results


def plan_batches(files: list[Path], batch_size: int) -> list[list[int]]:
    """Index lists that may share a crate: same global layout, no clashing exported macros."""
    batches: list[tuple[object, set[str], list[int]]] = []
    for i, f in enumerate(files):
        text = f.read_text()
        key = ("alone", i) if CRATE_WIDE.search(text) else global_key(text)
        macros = set(EXPORTED_MACRO.findall(text))
        for bkey, bmacros, idx in batches:
            if bkey == key and len(idx) < batch_size and not (bmacros & macros):
                idx.append(i)
                bmacros |= macros
                break
        else:
            batches.append((key, set(macros), [i]))
    return [idx for _, _, idx in batches]


def verify_batch(files: list[Path], verus: Path = DEFAULT_VERUS, batch_size: int = 8,
                 flags: list[str] | None = None, timeout: int = 900) -> list[dict]:
    """Per-file verdicts, in input order."""
    flags = flags or []
    results: list[dict | None] = [None] * len(files)
    for idx in plan_batches(files, batch_size):
        for i, r in zip(idx, _verify_group([files[i] for i in idx], verus, len(idx), flags, timeout)):
            results[i] = r
    return results  # type: ignore[return-value]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--verus", type=Path, default=DEFAULT_VERUS)
    args = ap.parse_args()
    start = time.perf_counter()
    res = verify_batch(args.files, args.verus, args.batch_size)
    for f, r in zip(args.files, res):
        print(json.dumps({"file": str(f), **r}))
    print(json.dumps({"files": len(res), "ok": sum(r["success"] for r in res),
                      "wall_seconds": round(time.perf_counter() - start, 2)}))


if __name__ == "__main__":
    main()
