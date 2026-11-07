#!/usr/bin/env python3
"""End-to-end proof-speed A/B with the real Codex agent driving DeepSeek V4 Pro.

Mirrors the project's earlier Codex evaluation contract (workspace with
AGENTS.md/TASK.md/input.rs/candidate.rs, same rule prompt, 600 s actor budget)
with two documented substitutions: Codex's own workspace-write sandbox instead
of the outer namespace sandbox, and proof_guard instead of Lynette.

Conditions:
  base       SKILL.md = VeruSAGE Executive core
  rules      + speed rules/cards
  procedure  + post-verification cost procedure and a tools/proof_cost.sh tool
             that prints exact per-function Z3 cost
After the agent stops, the host verifies candidate.rs, runs the guard, and
measures exact Z3 cost (SMT replay). Verifier-call times come from Codex events.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from measure_candidates import DEFAULT_VERUS  # noqa: E402
from proof_guard import check as guard_check  # noqa: E402
from smt_replay import cost as smt_cost  # noqa: E402
from solve_agent import run_verus  # noqa: E402

PROMPT = """Repair the Verus proof in candidate.rs.

Rules:
- Read SKILL.md first and follow it.
- input.rs is immutable and candidate.rs is the only file you may edit.
- Do not use assume, admit, newly introduced external_body, axioms, or
  unimplemented trusted helpers. Do not weaken or remove requires, ensures,
  recommends, signatures, executable code, or intended specifications.
- Diagnose with ./tools/run_verus.sh candidate.rs and iterate on the smallest proof-only edit.
- Before finishing, require both ./tools/run_verus.sh candidate.rs and
  ./tools/check_proof_only.sh to exit successfully.
- Do not search for trajectories, verified solutions, sibling task outputs, or
  validation/test metadata. Work only from this task, local Verus/vstd
  documentation, verifier diagnostics, and the supplied immutable skill.
- Finish only after both checks pass. Otherwise leave the best candidate.rs and
  state the precise blocker.
"""


def write_tools(ws: Path, with_cost: bool) -> None:
    tools = ws / "tools"
    tools.mkdir()
    base = Path.home() / ".cache/verus-skill"
    env = (f'export RUSTUP_HOME="{base}/rustup" CARGO_HOME="{base}/cargo"\n'
           f'export PATH="{base}/cargo/bin:$PATH" TMPDIR="{ws}/tmp"\n')
    (tools / "run_verus.sh").write_text(
        "#!/usr/bin/env bash\n" + env + f'exec "{DEFAULT_VERUS}" "${{1:-candidate.rs}}"\n')
    (tools / "check_proof_only.sh").write_text(
        "#!/usr/bin/env bash\n" + env + f'cd "{ws}" && exec python3 -I -c '
        f'"import sys; sys.path.insert(0, \'{HERE}\'); from proof_guard import check; '
        f'e = check(open(\'input.rs\').read(), open(\'candidate.rs\').read()); '
        f'print(\'OK: proof-only\' if not e else \'\\n\'.join(e)); sys.exit(1 if e else 0)"\n')
    if with_cost:
        (tools / "proof_cost.sh").write_text(
            "#!/usr/bin/env bash\n" + env + f'cd "{ws}" && exec python3 -I -c '
            f'"import sys; sys.path.insert(0, \'{HERE}\'); from smt_replay import cost; '
            f'r = cost(open(\'candidate.rs\').read()); '
            f'print(\'verified:\', r[\'success\'], \' total rlimit:\', int(r[\'rlimit\']), \' quantifier instantiations:\', int(r[\'qi\'])); '
            f'[print(f\'  {{int(v[\\"rlimit\\"]):>10}} rlimit {{int(v[\\"qi\\"]):>8}} QI  {{k}}\') for k, v in sorted(r[\'functions\'].items(), key=lambda kv: -kv[1][\'rlimit\'])[:12]]"\n')
    for f in tools.iterdir():
        f.chmod(0o755)


def sandbox_prefix(edir: Path, hide: list[str]) -> list[str]:
    """bwrap: hide the parent of $HOME (all homes) and --hide dirs (benchmark ground truth, run outputs,
    research repo, Codex/Claude state); re-expose read-only only the
    toolchains, node/codex and the guard/cost scripts; the episode dir is the
    only writable path. CODEX_HOME is a fresh empty dir inside the episode."""
    home = Path.home().resolve()
    cache = home / ".cache/verus-skill"
    ro = [home / ".nvm", cache / "rustup", cache / "cargo", cache / "toolchains", HERE]
    out = ["bwrap", "--ro-bind", "/", "/", "--tmpfs", str(home.parent)]
    for h in hide:
        out += ["--tmpfs", h]
    out += ["--tmpfs", "/tmp", "--dev", "/dev", "--proc", "/proc"]
    for p in ro:
        out += ["--ro-bind", str(p), str(p)]
    return out + ["--bind", str(edir), str(edir), "--die-with-parent", "--"]


def episode(task: dict, cond: str, rep: int, a) -> dict:
    edir = a.out_dir / cond / f"{task['task_id'][:100]}__r{rep}"
    if (edir / "result.json").exists():
        return json.loads((edir / "result.json").read_text())
    if edir.exists():
        shutil.rmtree(edir)
    ws = edir / "workspace"
    ws.mkdir(parents=True)
    (ws / "tmp").mkdir()
    src = Path(task["source_path"]).read_text()
    (ws / "input.rs").write_text(src)
    (ws / "candidate.rs").write_text(src)
    (ws / "TASK.md").write_text("Repair candidate.rs.\n")
    (ws / "AGENTS.md").write_text(PROMPT)
    (ws / "SKILL.md").write_text(a.skills[cond])
    write_tools(ws, cond == "procedure")
    cmd = [a.codex, "-a", "never", "exec", "--ignore-user-config", "--ephemeral", "--json",
           "--skip-git-repo-check", "-C", str(ws), "-s", "workspace-write", "-m", a.model,
           "-c", 'model_provider="deepseek_direct"',
           "-c", 'model_providers.deepseek_direct.name="DeepSeek"',
           "-c", f'model_providers.deepseek_direct.base_url="{a.base_url}"',
           "-c", 'model_providers.deepseek_direct.env_key="DEEPSEEK_API_KEY"',
           "-c", 'model_providers.deepseek_direct.wire_api="responses"',
           "-c", "model_providers.deepseek_direct.request_max_retries=4",
           "-c", "model_providers.deepseek_direct.stream_max_retries=4",
           "-c", f'model_reasoning_effort="{a.effort}"',
           "-c", "model_context_window=1048576",
           "-c", "model_max_output_tokens=8192",
           PROMPT]
    env = None
    if a.sandbox:
        cmd = sandbox_prefix(edir.resolve(), a.hide) + cmd
        env = dict(os.environ, CODEX_HOME=str(edir.resolve() / "codex_home"))
        (edir / "codex_home").mkdir()
    t0 = time.monotonic()
    with (edir / "codex_events.jsonl").open("w") as out, (edir / "codex_stderr.log").open("w") as err:
        p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True, cwd=ws, env=env)
        try:
            p.wait(timeout=a.budget)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGTERM)
            time.sleep(5)
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            p.wait()
            timed_out = True
    actor_wall = time.monotonic() - t0
    cand = (ws / "candidate.rs").read_text()
    v = run_verus(cand)
    g = guard_check(src, cand)
    usage, vcalls = {}, []
    started = {}
    for l in (edir / "codex_events.jsonl").read_text().splitlines():
        try:
            e = json.loads(l)
        except Exception:
            continue
        if e.get("type") == "turn.completed":
            for k, val in (e.get("usage") or {}).items():
                if isinstance(val, int):
                    usage[k] = usage.get(k, 0) + val
        it = e.get("item") or {}
        if it.get("type") == "command_execution" and "run_verus" in it.get("command", ""):
            if e.get("type") == "item.started":
                started[it["id"]] = time.monotonic()
            elif e.get("type") == "item.completed":
                out_text = it.get("aggregated_output") or ""
                vcalls.append({"exit_code": it.get("exit_code"),
                               "passed": "0 errors" in out_text and it.get("exit_code") == 0})
    res = {"task_id": task["task_id"], "condition": cond, "repeat": rep, "timed_out": timed_out,
           "actor_wall": actor_wall, "verified": v["passed"], "guard_ok": not g, "guard_errors": g[:5],
           "solved": v["passed"] and not g, "usage": usage, "agent_verus_calls": len(vcalls),
           "agent_verus_failed_calls": sum(not c["passed"] for c in vcalls)}
    if res["solved"]:
        c = smt_cost(cand)
        res.update({"final_rlimit": c["rlimit"], "final_qi": c["qi"],
                    "final_functions": {k: val["rlimit"] for k, val in c["functions"].items()}})
    (edir / "result.json").write_text(json.dumps(res, indent=1))
    shutil.rmtree(ws / "tmp", ignore_errors=True)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--conditions", nargs="+", default=["base", "rules", "procedure"])
    ap.add_argument("--skill-base", type=Path, required=True)
    ap.add_argument("--skill-rules", type=Path, required=True)
    ap.add_argument("--skill-procedure", type=Path, required=True)
    ap.add_argument("--skill-paircards", type=Path, help="cards learned from same-task cost pairs")
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--budget", type=int, default=600)
    ap.add_argument("--codex", default=shutil.which("codex") or "codex")
    ap.add_argument("--base-url", default="https://api.deepseek.com/v1")
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--effort", default="max")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only-task")
    ap.add_argument("--sandbox", action="store_true", help="run codex inside bwrap (hides ground truth)")
    ap.add_argument("--hide", nargs="*", default=[], help="extra dirs to hide in the sandbox (e.g. shared data mounts)")
    a = ap.parse_args()
    a.out_dir = a.out_dir.resolve()  # codex gets -C <ws> and cwd=<ws>; must be absolute
    base = a.skill_base.read_text()
    a.skills = {"base": base, "rules": base + "\n\n" + a.skill_rules.read_text(),
                "procedure": base + "\n\n" + a.skill_procedure.read_text().replace(
                    "you will be shown the exact", "run ./tools/proof_cost.sh to see the exact")}
    if a.skill_paircards:
        a.skills["paircards"] = base + "\n\n" + a.skill_paircards.read_text()
    tasks = [json.loads(l) for l in a.tasks.read_text().splitlines()]
    if a.only_task:
        tasks = [t for t in tasks if t["task_id"] == a.only_task]
    tasks = tasks[: a.limit]
    a.out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(t, c, r) for r in range(a.repeats) for t in tasks for c in a.conditions]
    with cf.ThreadPoolExecutor(a.workers) as pool:
        for res in pool.map(lambda j: episode(*j, a), jobs):
            print(json.dumps({k: res.get(k) for k in ("task_id", "condition", "repeat", "solved", "final_rlimit", "actor_wall")}), flush=True)


if __name__ == "__main__":
    main()
