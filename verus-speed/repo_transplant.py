#!/usr/bin/env python3
"""Apply proof rewrites found on single-file tasks to the whole repository.

For each repository function whose single-file task was made cheaper by
scripts/proof_time/speed_search.py, re-apply the same edits (delete the same
statement, or add `#[verifier::spinoff_prover]`) to the function in a copy of
the repository, then time the function alone before and after.

  python3 verus-speed/repo_transplant.py nrkernel RUN/repo/nrkernel_t16.json \
      --search-dir STUDY/search_heavy --patched-repos RUN/repo_patched \
      --out RUN/repo/nrkernel_transplant.json
The copy under --patched-repos must already exist (same layout as the clones).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RUNNER = Path(__file__).with_name("repo_run.sh")
CRATE_DIR = {"nrkernel": "verified-nrkernel/page-table/src", "anvil_vrs": "anvil/src"}


def load_rewrites(search_dir: Path) -> dict[str, list[dict]]:
    """function name -> full applied edits (statement text recovered from singles.jsonl)."""
    out = {}
    for fin in search_dir.glob("*/final.json"):
        d = json.loads(fin.read_text())
        if not d.get("applied") or d.get("ratio", 1) >= 0.95:
            continue
        singles = [json.loads(l) for l in (fin.parent / "singles.jsonl").read_text().splitlines()]
        edits = []
        for a in d["applied"]:
            full = [s["stmt"] for s in singles if s["kind"] == a["kind"] and s["stmt"].startswith(a["stmt"])]
            edits.append({"kind": a["kind"], "stmt": full[0] if full else a["stmt"]})
        out[d["task_id"].split("__")[-1]] = {"ratio": d["ratio"], "edits": edits}
    return out


def apply_edits(text: str, name: str, edits: list[dict]) -> tuple[str, list[str]]:
    notes = []
    m = re.search(rf"(?m)^([ \t]*)[^\n]*\bfn\s+{re.escape(name)}\s*[(<]", text)
    if not m:
        return text, ["function not found"]
    for e in edits:
        m = re.search(rf"(?m)^([ \t]*)[^\n]*\bfn\s+{re.escape(name)}\s*[(<]", text)
        if e["kind"] == "add_spinoff":
            text = text[:m.start()] + m.group(1) + "#[verifier::spinoff_prover]\n" + text[m.start():]
            notes.append("add_spinoff: applied")
            continue
        pat = re.compile(r"\s*".join(re.escape(tok) for tok in e["stmt"].split()))
        hit = pat.search(text, m.end())
        if not hit:
            notes.append(f"{e['kind']}: statement not found")
            continue
        end = hit.end()
        while end < len(text) and text[end] in " \t":
            end += 1
        if end < len(text) and text[end] == "\n":
            end += 1
        text = text[:hit.start()] + text[end:]
        notes.append(f"{e['kind']}: applied")
    return text, notes


def time_alone(project: str, repos: str | None, module: str, name: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="vtr_") as tmp:
        out = Path(tmp) / "o.json"
        env = dict(os.environ)
        if repos:
            env["VERUS_SPEED_REPOS"] = repos
        subprocess.run([str(RUNNER), project, str(out), "--verify-only-module", module,
                        "--verify-function", name, "--num-threads", "1"], env=env, check=False)
        try:
            doc = json.loads(out.read_text())
        except json.JSONDecodeError:
            return {"ok": False}
    res = doc.get("verification-results") or {}
    smt = ((doc.get("times-ms") or {}).get("smt") or {}).get("smt-run")
    return {"ok": bool(res.get("verified")) and not res.get("errors"), "smt_ms": smt}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", choices=sorted(CRATE_DIR))
    ap.add_argument("full_json", type=Path)
    ap.add_argument("--search-dir", type=Path, required=True)
    ap.add_argument("--patched-repos", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--min-smt-s", type=float, default=2.0)
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    rewrites = load_rewrites(a.search_dir)
    crate = a.patched_repos / CRATE_DIR[a.project]
    targets = {}
    for m in json.loads(a.full_json.read_text())["times-ms"]["smt"]["smt-run-module-times"]:
        for f in m.get("function-breakdown") or []:
            name = f["function"].split("::")[-1]
            if name in rewrites and f["time-micros"] / 1e6 >= a.min_smt_s and name not in targets:
                targets[name] = {"module": m["module"], "full_smt_s": f["time-micros"] / 1e6,
                                 "task_ratio": rewrites[name]["ratio"]}
    for name, t in targets.items():
        files = [p for p in crate.rglob("*.rs") if "deps_hack" not in p.parts
                 and re.search(rf"\bfn\s+{re.escape(name)}\s*[(<]", p.read_text())]
        if len(files) != 1:
            t["notes"] = [f"{len(files)} files define the function"]
            continue
        new, notes = apply_edits(files[0].read_text(), name, rewrites[name]["edits"])
        t["notes"], t["file"] = notes, str(files[0].relative_to(crate))
        if any(n.endswith("applied") for n in notes):
            files[0].write_text(new)
            t["patched"] = True

    todo = [n for n, t in targets.items() if t.get("patched")]
    jobs = [(n, which) for _ in range(a.repeats) for n in todo for which in ("before", "after")]

    def run(job):
        n, which = job
        return job, time_alone(a.project, str(a.patched_repos) if which == "after" else None,
                               targets[n]["module"], n)

    with ThreadPoolExecutor(a.workers) as pool:
        for (n, which), r in pool.map(run, jobs):
            targets[n].setdefault(which, []).append(r)
    a.out.write_text(json.dumps(targets, indent=1))
    for n, t in targets.items():
        def best(which):
            v = [r["smt_ms"] for r in t.get(which, []) if r.get("ok") and r.get("smt_ms")]
            return min(v) / 1000 if v else None
        b, af = best("before"), best("after")
        print(f"{n[:55]:55s} task_ratio={t['task_ratio']:.2f} before={b} after={af} "
              f"ratio={af / b if b and af else None} notes={t.get('notes')}")


if __name__ == "__main__":
    main()
