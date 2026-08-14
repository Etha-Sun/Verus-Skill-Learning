#!/usr/bin/env python3
"""Run Codex CLI + DeepSeek V4 Pro on frozen held-out-15 under a selected skill arm."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from dotenv import dotenv_values

from verus_agent.workspace import VerusWorkspace, prepare_workspace


DELIVERY_ROOT = Path(__file__).resolve().parents[4]
CODE_ROOT = DELIVERY_ROOT / "code"
DEFAULT_OUTPUT_ROOT = CODE_ROOT / "outputs/ironkv_deepseek_strict_heldout15_semantic_v4_codex_v1"
SEMANTIC_SKILL = DELIVERY_ROOT / "skills/semantic_v4/verus-proof-repair"
COMPRESSED_SKILL = DELIVERY_ROOT / "skills/native_compressed/verus-proof-repair"
DEFAULT_ENV_FILE = Path(
    os.environ.get("DEEPSEEK_ENV_FILE", DELIVERY_ROOT / ".env.deepseek")
)
VERUS_BIN = Path(
    os.environ.get(
        "VERUS_BIN", "/zp_vegeta/scratch_sb/xinyueh/tools/verus/bin/verus"
    )
)
LYNETTE_BIN = Path(
    os.environ.get(
        "LYNETTE_BIN",
        "/zp_vegeta/scratch_sb/xinyueh/qwen_five_skill_eval/tools/lynette",
    )
)
STRICT_SELECTION_ROOT = CODE_ROOT / "outputs/ironkv_strict_heldout15_official_v4_selection"
STRICT_TASKS = STRICT_SELECTION_ROOT / "heldout15_tasks.jsonl"
STRICT_SELECTION = STRICT_SELECTION_ROOT / "heldout15_selection.json"
BRIDGE_MODULE = "verus_agent.codex_harness.upstream_skillopt.codex_deepseek_bridge"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 4017
DEFAULT_SEED = 20260811


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_nonsecret_config(env_file: Path) -> tuple[dict[str, Any], dict[str, str]]:
    file_values = (
        {key: str(value or "") for key, value in dotenv_values(env_file).items()}
        if env_file.is_file()
        else {}
    )
    child_env = dict(os.environ)
    for key, value in file_values.items():
        child_env.setdefault(key, value)
    api_key = child_env.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY is missing; export it or provide --env-file"
        )
    child_env.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    return ({"api_key_configured": True}, child_env)


def load_default_rows() -> list[dict[str, Any]]:
    if not STRICT_TASKS.is_file():
        raise FileNotFoundError(
            f"default held-out task manifest is not delivered: {STRICT_TASKS}; "
            "provide --selection-root"
        )
    return [
        json.loads(line)
        for line in STRICT_TASKS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_default_selection(rows: list[dict[str, Any]]) -> None:
    if len(rows) != 15:
        raise ValueError(f"strict held-out manifest must contain 15 tasks, found {len(rows)}")
    selection = json.loads(STRICT_SELECTION.read_text(encoding="utf-8"))
    if selection.get("train_task_id_overlap_count") != 0:
        raise ValueError("strict selection overlaps training data")
    for row in rows:
        source = Path(row["source_path"])
        if not source.is_file() or sha256_file(source) != row["source_sha256"]:
            raise ValueError(f"strict source missing or changed: {row['task_id']}")


def validate_semantic_skill() -> None:
    root = SEMANTIC_SKILL / "SKILL.md"
    references = sorted((SEMANTIC_SKILL / "references").glob("*.md"))
    if not root.is_file() or len(references) != 14:
        raise ValueError(
            "delivered semantic-v4 skill must contain SKILL.md and 14 references"
        )


class _BaseCompat:
    PROJECT_ROOT = CODE_ROOT
    DEFAULT_ENV_FILE = DEFAULT_ENV_FILE
    DEFAULT_SEED = DEFAULT_SEED
    VERUS_BIN = VERUS_BIN
    LYNETTE_BIN = LYNETTE_BIN
    utc_now = staticmethod(utc_now)
    sha256_file = staticmethod(sha256_file)
    sha256_tree = staticmethod(sha256_tree)
    write_json = staticmethod(write_json)
    load_nonsecret_config = staticmethod(load_nonsecret_config)


class _StrictCompat:
    STRICT_SELECTION = STRICT_SELECTION

    @staticmethod
    def load_rows() -> list[dict[str, Any]]:
        return load_default_rows()

    @staticmethod
    def select_frozen(
        rows: list[dict[str, Any]], count: int, _seed: int
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        if count != 15 or len(rows) != 15:
            raise ValueError("the frozen strict evaluation requires exactly 15 tasks")
        return rows, dict(sorted(Counter(row["module"] for row in rows).items()))

    validate_strict_selection = staticmethod(validate_default_selection)


base = _BaseCompat()
strict = _StrictCompat()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    result.add_argument("--env-file", type=Path, default=base.DEFAULT_ENV_FILE)
    result.add_argument(
        "--codex-bin",
        type=Path,
        default=Path(os.environ.get("CODEX_BIN") or shutil.which("codex") or "codex"),
    )
    result.add_argument("--verus-bin", type=Path, default=VERUS_BIN)
    result.add_argument("--lynette-bin", type=Path, default=LYNETTE_BIN)
    result.add_argument("--task-numbers", type=int, nargs="+")
    result.add_argument("--timeout-seconds", type=int, default=3600)
    result.add_argument("--proxy-port", type=int, default=PROXY_PORT)
    result.add_argument("--condition", choices=("semantic-v4", "compressed-skill", "no-skill"), default="semantic-v4")
    result.add_argument("--selection-root", type=Path)
    result.add_argument("--selection-check-only", action="store_true")
    result.add_argument("--keep-proxy", action="store_true")
    return result


def prompt(
    skill_dir: Path | None, verus_bin: Path, lynette_bin: Path
) -> str:
    skill_rule = (
        f"- Read {skill_dir / 'SKILL.md'} first and follow the supplied proof-repair skill. "
        "Read a reference under its references/ directory only when the root skill routes you there."
        if skill_dir is not None else
        "- This is the no-skill control: no proof-repair skill is supplied."
    )
    return f"""Repair the Verus proof in candidate.rs.

Rules:
{skill_rule}
- input.rs is immutable and candidate.rs is the only file you may edit.
- Do not use assume, admit, external_body, axioms, or weaken/remove any requires, ensures, recommends, signatures, or executable code.
- Diagnose with `{verus_bin} candidate.rs` and iterate on the smallest proof-only edit.
- Before finishing, require both `{verus_bin} candidate.rs` and `{lynette_bin} compare -t input.rs candidate.rs` to exit successfully on the current candidate.
- Do not look for held-out trajectories or verified solutions. Work only from this task, local documentation, Verus diagnostics, vstd, and the supplied skill.
- Finish only after both checks pass. If you cannot finish, leave the best candidate.rs and state the blocker.
"""


def write_agents(
    work_dir: Path, skill_dir: Path | None, verus_bin: Path, lynette_bin: Path
) -> None:
    (work_dir / "AGENTS.md").write_text(
        prompt(skill_dir, verus_bin, lynette_bin), encoding="utf-8"
    )


def start_proxy(output: Path, env: dict[str, str], port: int) -> subprocess.Popen:
    log = (output / "deepseek_bridge.log").open("wb")
    command = [
        sys.executable, "-m", BRIDGE_MODULE,
        "--native-responses", "--model", "deepseek-v4-pro",
        "--upstream-base-url", env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "--host", PROXY_HOST, "--port", str(port),
        "--ledger-path", str(output / "bridge_calls.jsonl"),
        "--manifest-path", str(output / "bridge_manifest.json"),
        "--max-output-tokens", "8192",
        "--request-timeout-seconds", "1800",
    ]
    process = subprocess.Popen(
        command, cwd=base.PROJECT_ROOT, env=env, stdout=log,
        stderr=subprocess.STDOUT, start_new_session=True,
    )
    deadline = time.monotonic() + 60
    health = f"http://{PROXY_HOST}:{port}/health"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"DeepSeek bridge exited early; see {output / 'deepseek_bridge.log'}")
        try:
            with urlopen(health, timeout=2) as response:
                if response.status == 200:
                    return process
        except Exception:
            time.sleep(0.5)
    os.killpg(process.pid, signal.SIGTERM)
    raise TimeoutError("DeepSeek bridge did not become healthy")


def stop_proxy(process: subprocess.Popen) -> None:
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)


def codex_command(
    work_dir: Path,
    port: int,
    task_id: str,
    codex_bin: Path,
    verus_bin: Path,
    lynette_bin: Path,
) -> list[str]:
    provider = "model_providers.deepseek_bridge"
    return [
        str(codex_bin), "-a", "never", "exec", "--ignore-user-config", "--ephemeral", "--json",
        "--skip-git-repo-check", "-C", str(work_dir), "-s", "workspace-write",
        "-m", "deepseek-v4-pro",
        "-c", 'model_provider="deepseek_bridge"',
        "-c", f'{provider}.name="DeepSeek V4 Pro Native Responses Bridge"',
        "-c", f'{provider}.base_url="http://{PROXY_HOST}:{port}/tasks/{task_id}/v1"',
        "-c", f'{provider}.env_key="DEEPSEEK_API_KEY"',
        "-c", f'{provider}.wire_api="responses"',
        "-c", f'{provider}.request_max_retries=0',
        "-c", f'{provider}.stream_max_retries=0',
        "-c", 'model_reasoning_effort="high"',
        "-c", 'model_context_window=1048576',
        "-c", 'model_max_output_tokens=8192',
        prompt(
            work_dir / "skill/verus-proof-repair"
            if (work_dir / "skill/verus-proof-repair").is_dir()
            else None,
            verus_bin,
            lynette_bin,
        ),
    ]


def validate(workspace: VerusWorkspace) -> dict[str, Any]:
    workspace.run_verus()
    workspace.run_lynette()
    return workspace.validation_status()


def usage_for_task(path: Path, task_id: str) -> dict[str, Any]:
    records = []
    if path.is_file():
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    selected = [row for row in records if row.get("task_id") == task_id]
    fields = (
        "prompt_tokens", "completion_tokens", "total_tokens",
        "prompt_cache_hit_tokens", "prompt_cache_miss_tokens", "reasoning_tokens",
    )
    result = {field: 0 for field in fields}
    request_count = 0
    failed_request_count = 0
    for row in selected:
        for attempt in row.get("attempts") or []:
            usage = attempt.get("usage")
            if isinstance(usage, dict):
                request_count += 1
                for field in fields:
                    result[field] += int(usage.get(field, 0) or 0)
            elif attempt.get("error"):
                failed_request_count += 1
    result.update({"request_count": request_count, "failed_request_count": failed_request_count})
    return result


def prepare(output: Path, rows: list[dict[str, Any]], args: argparse.Namespace) -> Path | None:
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    snapshot = None
    skill_source = None
    if args.condition == "semantic-v4":
        skill_source = SEMANTIC_SKILL
    elif args.condition == "compressed-skill":
        skill_source = COMPRESSED_SKILL
    if skill_source is not None:
        snapshot = output / "skill_snapshot/verus-proof-repair"
        shutil.copytree(skill_source, snapshot)
    selection_manifest = (
        args.selection_root.resolve() / "hard15_selection.json"
        if args.selection_root
        else strict.STRICT_SELECTION
    )
    shutil.copy2(selection_manifest, output / "heldout15_selection.json")
    (output / "tasks.tsv").write_text(
        "".join(f"{i:02d}\t{row['task_id']}\t{row['source_path']}\n" for i, row in enumerate(rows, 1)),
        encoding="utf-8",
    )
    base.write_json(output / "experiment_manifest.json", {
        "experiment": f"ironkv_deepseek_strict_heldout15_{args.condition.replace(chr(45), chr(95))}_codex_v1",
        "created_at": base.utc_now(), "harness": "codex_cli_native_deepseek_responses_bridge",
        "codex_bin": str(args.codex_bin),
        "condition": args.condition, "task_count": len(rows), "execution": "serial",
        "model": "deepseek-v4-pro", "reasoning_effort": "high", "deepseek_thinking": True,
        "api_transport": "Codex Responses API -> audited native bridge -> DeepSeek Responses API",
        "api_key_source": ".env.deepseek:DEEPSEEK_API_KEY", "api_key_recorded": False,
        "token_accounting": "native bridge ledger using provider-returned Responses usage",
        "timeout_seconds_per_task": args.timeout_seconds,
        "turn_budget": None,
        "comparability_note": "Codex internal agent turns are not equivalent to the prior custom ReAct action-turn budget.",
        "skill_variant": args.condition,
        "skill_source": str(skill_source.resolve()) if skill_source else None,
        "skill_snapshot_sha256": base.sha256_tree(snapshot) if snapshot else None,
        "strict_selection_manifest": str(strict.STRICT_SELECTION.resolve()),
        "strict_selection_manifest_sha256": base.sha256_file(selection_manifest),
        "heldout_trajectory_or_verified_solution_exposed": False,
        "selected_task_numbers": args.task_numbers or list(range(1, 16)),
        "selected_tasks": [{k: row[k] for k in ("task_id", "module", "source_path", "source_sha256")} for row in rows],
    })
    return snapshot


def summarize(output: Path, arms: list[dict[str, Any]]) -> None:
    totals: dict[str, int] = defaultdict(int)
    for arm in arms:
        for key, value in arm["usage"].items():
            totals[key] += int(value or 0)
    base.write_json(output / "summary.json", {
        "completed_at": base.utc_now(), "completed_tasks": len(arms),
        "successes": sum(bool(arm["success"]) for arm in arms),
        "outcomes": {arm["task_id"]: arm["success"] for arm in arms},
        "usage": dict(totals), "tasks": arms,
    })


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.selection_root:
        selection_root = args.selection_root.resolve()
        task_manifest = selection_root / "hard15_tasks.jsonl"
        selection_manifest = selection_root / "hard15_selection.json"
        rows = [json.loads(line) for line in task_manifest.read_text().splitlines() if line.strip()]
        selection = json.loads(selection_manifest.read_text())
        if len(rows) != 15 or selection.get("selection_count") != 15:
            raise ValueError("custom challenge selection must contain exactly 15 tasks")
        if selection.get("train_task_id_overlap_count") != 0:
            raise ValueError("custom challenge selection overlaps train77")
        if any(not Path(row["source_path"]).is_file() or base.sha256_file(Path(row["source_path"])) != row["source_sha256"] for row in rows):
            raise ValueError("custom challenge source missing or changed")
        selected = rows
        quotas = dict(sorted(__import__("collections").Counter(row["module"] for row in rows).items()))
    else:
        selected, quotas = strict.select_frozen(strict.load_rows(), 15, base.DEFAULT_SEED)
        strict.validate_strict_selection(selected)
    if args.condition == "semantic-v4":
        validate_semantic_skill()
    elif args.condition == "compressed-skill" and not (COMPRESSED_SKILL / "SKILL.md").is_file():
        raise FileNotFoundError(COMPRESSED_SKILL / "SKILL.md")
    if args.task_numbers:
        if len(set(args.task_numbers)) != len(args.task_numbers) or any(n < 1 or n > 15 for n in args.task_numbers):
            raise ValueError("--task-numbers must be unique values in 1..15")
        selected = [selected[n - 1] for n in args.task_numbers]
    print(json.dumps({"selection_count": len(selected), "module_quotas": quotas,
                      "task_ids": [row["task_id"] for row in selected]}, indent=2), flush=True)
    if args.selection_check_only:
        return 0
    if not args.codex_bin.is_file() and shutil.which(str(args.codex_bin)) is None:
        raise FileNotFoundError(f"Codex CLI is not executable: {args.codex_bin}")
    _, env = base.load_nonsecret_config(args.env_file.resolve())
    output = args.output_root.resolve()
    snapshot = prepare(output, selected, args)
    if args.selection_root:
        shutil.copy2(selection_manifest, output / "heldout15_selection.json")
        manifest_path = output / "experiment_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest.update({
            "selection_policy": selection["selection_policy"],
            "strict_selection_manifest": str(selection_manifest),
            "strict_selection_manifest_sha256": base.sha256_file(selection_manifest),
            "official_false_count": selection["strict_false_count"],
            "cheat_supplement_count": selection["cheat_supplement_count"],
            "independent_leakage_component_count": selection["independent_leakage_component_count"],
        })
        base.write_json(manifest_path, manifest)
    usage_log = output / "bridge_calls.jsonl"
    env.update({
        "PYTHONPATH": str(base.PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
    })
    proxy = start_proxy(output, env, args.proxy_port)
    arms: list[dict[str, Any]] = []
    try:
        for index, row in enumerate(selected, 1):
            source = Path(row["source_path"])
            if base.sha256_file(source) != row["source_sha256"]:
                raise ValueError(f"source changed: {row['task_id']}")
            work = output / "tasks" / row["task_id"]
            workspace = prepare_workspace(source, work)
            workspace.verus_bin = workspace._require_executable(args.verus_bin, "Verus")
            workspace.lynette_bin = workspace._require_executable(args.lynette_bin, "Lynette")
            task_skill = None
            if snapshot is not None:
                task_skill = work / "skill/verus-proof-repair"
                shutil.copytree(snapshot, task_skill)
            write_agents(work, task_skill, args.verus_bin, args.lynette_bin)
            log_path = output / "logs" / f"{index:02d}_{row['task_id']}.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"[{index:02d}/{len(selected):02d}] START {row['task_id']}", flush=True)
            started = base.utc_now()
            timed_out = False
            with log_path.open("wb") as log:
                try:
                    completed = subprocess.run(codex_command(
                                                   work, args.proxy_port, row["task_id"],
                                                   args.codex_bin, args.verus_bin, args.lynette_bin,
                                               ), cwd=work, env=env,
                                               stdout=log, stderr=subprocess.STDOUT,
                                               timeout=args.timeout_seconds, check=False)
                    exit_code = completed.returncode
                except subprocess.TimeoutExpired:
                    timed_out, exit_code = True, 124
            validation = validate(workspace)
            task_usage = usage_for_task(usage_log, row["task_id"])
            arm = {"task_index": index, "task_id": row["task_id"], "started_at": started,
                   "finished_at": base.utc_now(), "exit_code": exit_code, "timed_out": timed_out,
                   "success": bool(validation["complete"]), "validation": validation,
                   "usage": task_usage, "work_dir": str(work), "log_path": str(log_path)}
            base.write_json(work / "run_result.json", arm)
            arms.append(arm)
            base.write_json(output / "progress.json", {"status": "running", "completed_tasks": len(arms), "tasks": arms})
            print(f"[{index:02d}/{len(selected):02d}] END {row['task_id']} success={arm['success']} rc={exit_code}", flush=True)
        summarize(output, arms)
        base.write_json(output / "progress.json", {"status": "completed", "completed_tasks": len(arms), "tasks": arms})
        (output / "batch_complete").write_text(base.utc_now() + "\n", encoding="utf-8")
    finally:
        if not args.keep_proxy:
            stop_proxy(proxy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
