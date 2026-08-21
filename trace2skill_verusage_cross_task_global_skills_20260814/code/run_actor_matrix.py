#!/usr/bin/env python3
"""Run the frozen cross-task Codex CLI actor on validation/test or a fake smoke."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from dotenv import dotenv_values

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_CODE = REPOSITORY_ROOT / "trace2skill_verusage_baseline_test" / "code"
sys.path.insert(0, str(BASELINE_CODE))

from global_skill_experiment.gate import hash_skill_tree  # noqa: E402
from verus_agent.workspace import prepare_workspace  # noqa: E402

ISOLATION_RUNNER = EXPERIMENT_ROOT / "code" / "actor_isolation.py"
UNSHARE_BIN = Path("/usr/bin/unshare")
WORKSPACE_ROOT = REPOSITORY_ROOT.parent


def configured_path(environment_variable: str, fallback: Path) -> Path:
    value = os.environ.get(environment_variable)
    return Path(value).expanduser() if value else fallback


DEFAULT_SCRATCH_ROOT = configured_path("VERUS_SKILL_SCRATCH_ROOT", WORKSPACE_ROOT)
DEFAULT_RUST_ROOT = configured_path(
    "VERUS_RUST_ROOT", WORKSPACE_ROOT / "tools" / "rust"
)

BRIDGE_MODULE = "verus_agent.codex_harness.upstream_skillopt.codex_deepseek_bridge"
BRIDGE_SOURCE = (
    BASELINE_CODE
    / "verus_agent"
    / "codex_harness"
    / "upstream_skillopt"
    / "codex_deepseek_bridge.py"
)
SPLIT_ROOT = REPOSITORY_ROOT / "fixed-claude-stratified-80-seed20260814"
DEFAULT_RUN_ROOT = configured_path(
    "VERUS_SKILL_RUN_ROOT", WORKSPACE_ROOT / "verus_skill_runs"
)
DEFAULT_M_CORE = (
    DEFAULT_RUN_ROOT
    / "cross-task-global-20260814"
    / "m_core_v3"
    / "m_core"
    / "skill"
    / "verus-proof-repair"
)
DEFAULT_ENV_FILE = configured_path(
    "DEEPSEEK_ENV_FILE", WORKSPACE_ROOT / ".env.deepseek"
)
DEFAULT_CODEX = configured_path(
    "CODEX_BIN", Path(shutil.which("codex") or "codex")
)
DEFAULT_VERUS = configured_path(
    "VERUS_BIN", WORKSPACE_ROOT / "tools" / "verus" / "bin" / "verus"
)
DEFAULT_LYNETTE = configured_path(
    "LYNETTE_BIN", WORKSPACE_ROOT / "tools" / "lynette"
)
EXPECTED_CODEX_VERSION = "codex-cli 0.147.0"
BRIDGE_COMMIT = "d6fc7754602f320db90a32401ec1ca1739ac2b1c"
PROVIDER_REQUEST_MAX_RETRIES = 4
PROVIDER_STREAM_MAX_RETRIES = 4

PROVIDER_PROFILES: dict[str, dict[str, Any]] = {
    "deepseek": {
        "config_name": "deepseek_bridge",
        "display_name": "DeepSeek V4 Pro Native Responses Bridge",
        "model": "deepseek-v4-pro",
        "reasoning_effort": "high",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "model_env": "DEEPSEEK_MODEL",
        "default_api_key": "",
        "default_base_url": "https://api.deepseek.com",
        "requires_api_key": True,
        "requires_budget": True,
        "native_responses": True,
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "chat_reasoning_effort": "high",
        "include_chat_thinking_field": True,
        "chat_template_kwargs": {},
        "reasoning_history_field": "reasoning_content",
        "harness": "codex_cli_0.147.0_native_deepseek_responses_bridge",
        "bridge_log": "deepseek_bridge.log",
    },
    "openai": {
        "config_name": "openai_bridge",
        "display_name": "OpenAI GPT-5.6 Sol Native Responses Bridge",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "max",
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "model_env": "OPENAI_MODEL",
        "default_api_key": "",
        "default_base_url": "https://api.openai.com/v1",
        "requires_api_key": True,
        "requires_budget": True,
        "native_responses": True,
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "chat_reasoning_effort": "high",
        "include_chat_thinking_field": True,
        "chat_template_kwargs": {},
        "reasoning_history_field": "reasoning_content",
        "harness": "codex_cli_0.147.0_native_openai_responses_bridge",
        "bridge_log": "openai_bridge.log",
    },
    "glm": {
        "config_name": "glm_bridge",
        "display_name": "Z.AI GLM-5.3 Responses-to-Chat Bridge",
        "model": "glm-5.3",
        "reasoning_effort": "max",
        "api_key_env": "GLM_API_KEY",
        "base_url_env": "GLM_BASE_URL",
        "model_env": "GLM_MODEL",
        "default_api_key": "",
        "default_base_url": "https://api.z.ai/api/paas/v4",
        "requires_api_key": True,
        "requires_budget": True,
        "native_responses": False,
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "chat_reasoning_effort": "max",
        "include_chat_thinking_field": True,
        "chat_template_kwargs": {},
        "reasoning_history_field": "reasoning_content",
        "harness": "codex_cli_0.147.0_glm53_responses_to_chat_bridge",
        "bridge_log": "glm_responses_bridge.log",
    },
    "qwen_local": {
        "config_name": "qwen_local_bridge",
        "display_name": "Local Qwen3.8-27B FP8 Responses-to-Chat Bridge",
        "model": "qwen38-27b-fp8",
        "reasoning_effort": "xhigh",
        "api_key_env": "QWEN_LOCAL_API_KEY",
        "base_url_env": "QWEN_LOCAL_BASE_URL",
        "model_env": "QWEN_LOCAL_MODEL",
        "default_api_key": "EMPTY",
        "default_base_url": "http://127.0.0.1:8000/v1",
        "requires_api_key": False,
        "requires_budget": False,
        "native_responses": False,
        "context_window": 262144,
        "max_output_tokens": 8192,
        "chat_reasoning_effort": "",
        "include_chat_thinking_field": False,
        "chat_template_kwargs": {
            "enable_thinking": True,
            "preserve_thinking": True,
        },
        "reasoning_history_field": "reasoning",
        "harness": "codex_cli_0.147.0_local_qwen38_responses_to_chat_bridge",
        "bridge_log": "qwen_responses_bridge.log",
    },
    "qwen_bf16_local": {
        "config_name": "qwen_bf16_local_bridge",
        "display_name": "Local Qwen3.8-27B BF16 Responses-to-Chat Bridge",
        "model": "qwen38-27b-bf16",
        "reasoning_effort": "xhigh",
        "api_key_env": "QWEN_BF16_LOCAL_API_KEY",
        "base_url_env": "QWEN_BF16_LOCAL_BASE_URL",
        "model_env": "QWEN_BF16_LOCAL_MODEL",
        "default_api_key": "EMPTY",
        "default_base_url": "http://127.0.0.1:8001/v1",
        "requires_api_key": False,
        "requires_budget": False,
        "native_responses": False,
        "context_window": 262144,
        "max_output_tokens": 8192,
        "chat_reasoning_effort": "",
        "include_chat_thinking_field": False,
        "chat_template_kwargs": {
            "enable_thinking": True,
            "preserve_thinking": True,
        },
        "reasoning_history_field": "reasoning",
        "harness": "codex_cli_0.147.0_local_qwen38_bf16_responses_to_chat_bridge",
        "bridge_log": "qwen_bf16_responses_bridge.log",
    },
}

ADDED_BYPASS_PATTERNS = {
    "assume": re.compile(r"\bassume\s*\("),
    "admit": re.compile(r"\badmit\s*\("),
    "external_body": re.compile(r"verifier::external_body|\bexternal_body\b"),
    "unimplemented": re.compile(r"\bunimplemented\s*!"),
    "axiom": re.compile(r"\baxiom\b", re.IGNORECASE),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def assert_strict_child(path: Path, root: Path) -> None:
    resolved = path.resolve()
    parent = root.resolve()
    if resolved == parent or parent not in resolved.parents:
        raise ValueError(f"output must be a strict child of run root: {resolved}")


def require_executable(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ValueError(f"{label} executable is invalid: {resolved}")
    return resolved


def codex_version(codex_bin: Path) -> str:
    completed = subprocess.run(
        [str(codex_bin), "--version"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return completed.stdout.strip()


def load_split(split: str, split_root: Path = SPLIT_ROOT) -> list[dict[str, Any]]:
    path = split_root / split / "items.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) != 20:
        raise ValueError(f"{split}/items.json must contain exactly 20 tasks")
    task_ids = [str(row.get("task_id") or "") for row in rows]
    if any(not task_id for task_id in task_ids) or len(set(task_ids)) != 20:
        raise ValueError(f"{split} task IDs must be nonempty and unique")
    for index, row in enumerate(rows, 1):
        source = (REPOSITORY_ROOT / row["source_path"]).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"missing {split} source: {source}")
        if sha256_file(source) != row["source_sha256"]:
            raise ValueError(f"frozen source hash mismatch: {row['task_id']}")
        row = dict(row)
        row["_split_index"] = index
        row["_source_resolved"] = str(source)
        rows[index - 1] = row
    return rows


def select_tasks(
    rows: list[dict[str, Any]], task_numbers: list[int] | None
) -> list[dict[str, Any]]:
    if task_numbers is None:
        return rows
    if (
        len(task_numbers) != len(set(task_numbers))
        or any(number < 1 or number > len(rows) for number in task_numbers)
    ):
        raise ValueError(f"task numbers must be unique values in 1..{len(rows)}")
    return [rows[number - 1] for number in task_numbers]


def task_result_path(output: Path, row: dict[str, Any]) -> Path:
    """Return the durable, task-specific result path used by write and resume."""
    return output / "tasks" / row["normalized_task_id"] / "run_result.json"


def skill_audit(skill_dir: Path, require_zero_references: bool) -> dict[str, Any]:
    root = skill_dir.resolve()
    skill_md = root / "SKILL.md"
    metadata = root / "agents" / "openai.yaml"
    if not skill_md.is_file() or not metadata.is_file():
        raise ValueError(f"invalid skill tree: {root}")
    files = sorted(path for path in root.rglob("*") if path.is_file() or path.is_symlink())
    symlinks = [path.relative_to(root).as_posix() for path in files if path.is_symlink()]
    if symlinks:
        raise ValueError(f"skill tree contains symlinks: {symlinks}")
    relative = [path.relative_to(root).as_posix() for path in files]
    references = [name for name in relative if name.startswith("references/")]
    text = skill_md.read_text(encoding="utf-8")
    metadata_text = metadata.read_text(encoding="utf-8")
    if "name: verus-proof-repair" not in text:
        raise ValueError("skill front matter has the wrong name")
    if "$verus-proof-repair" not in metadata_text:
        raise ValueError("skill metadata does not invoke $verus-proof-repair")
    if require_zero_references and references:
        raise ValueError(f"M-core must have zero references: {references}")
    if require_zero_references and (
        "references/" in text or "## Reference map" in text
    ):
        raise ValueError("zero-reference M-core contains a reference route")
    return {
        "skill_dir": str(root),
        "skill_tree_sha256": hash_skill_tree(root),
        "skill_md_sha256": sha256_file(skill_md),
        "files": relative,
        "reference_file_count": len(references),
        "reference_routes_present": "references/" in text,
    }


def provider_profile(provider_name: str) -> dict[str, Any]:
    try:
        return PROVIDER_PROFILES[provider_name]
    except KeyError as exc:
        raise ValueError(f"unsupported provider profile: {provider_name}") from exc


def code_mode_host_for_provider(
    provider_name: str, codex_bin: Path
) -> Path | None:
    """Return the co-versioned Code Mode host only for the OpenAI profile."""
    if provider_name != "openai":
        return None
    return require_executable(
        codex_bin.with_name("codex-code-mode-host"), "Codex Code Mode host"
    )


def load_nonsecret_env(
    env_file: Path, execute: bool, provider_name: str = "deepseek"
) -> dict[str, str]:
    profile = provider_profile(provider_name)
    values = {
        key: str(value or "") for key, value in dotenv_values(env_file).items()
    }
    env = os.environ.copy()
    if not profile["requires_api_key"]:
        sensitive_fragments = (
            "API_KEY",
            "ACCESS_KEY",
            "SECRET",
            "TOKEN",
            "PASSWORD",
            "CREDENTIAL",
        )
        env = {
            key: value
            for key, value in env.items()
            if not any(fragment in key.upper() for fragment in sensitive_fragments)
        }
    for key in (
        profile["api_key_env"],
        profile["base_url_env"],
        profile["model_env"],
    ):
        if key not in env and values.get(key):
            env[key] = values[key]
    env.setdefault(profile["api_key_env"], profile["default_api_key"])
    env.setdefault(profile["base_url_env"], profile["default_base_url"])
    env.setdefault(profile["model_env"], profile["model"])
    if (
        execute
        and profile["requires_api_key"]
        and not env.get(profile["api_key_env"], "").strip()
    ):
        raise ValueError(f"{profile['api_key_env']} is missing")
    if env.get(profile["model_env"]) != profile["model"]:
        raise ValueError(
            f"{provider_name} actor profile requires {profile['model']}"
        )
    env["PYTHONPATH"] = str(BASELINE_CODE) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def actor_prompt(skill_enabled: bool, verus_bin: Path, lynette_bin: Path) -> str:
    skill_rule = (
        "- Read skill/verus-proof-repair/SKILL.md first and follow it. "
        "Consult a file below skill/verus-proof-repair/references/ only when "
        "the root skill explicitly routes you there."
        if skill_enabled
        else "- This is the no-skill control; no proof-repair skill is supplied."
    )
    return f"""Repair the Verus proof in candidate.rs.

Rules:
{skill_rule}
- input.rs is immutable and candidate.rs is the only file you may edit.
- Do not use assume, admit, newly introduced external_body, axioms, or
  unimplemented trusted helpers. Do not weaken or remove requires, ensures,
  recommends, signatures, executable code, or intended specifications.
- Diagnose with {verus_bin} candidate.rs and iterate on the smallest proof-only edit.
- Before finishing, require both {verus_bin} candidate.rs and
  {lynette_bin} compare -t input.rs candidate.rs to exit successfully.
- Do not search for trajectories, verified solutions, sibling task outputs, or
  validation/test metadata. Work only from this task, local Verus/vstd
  documentation, verifier diagnostics, and the supplied immutable skill.
- Finish only after both checks pass. Otherwise leave the best candidate.rs and
  state the precise blocker.
"""


def codex_command(
    work_dir: Path,
    port: int,
    task_key: str,
    codex_bin: Path,
    prompt: str,
    provider_name: str = "deepseek",
) -> list[str]:
    profile = provider_profile(provider_name)
    config_name = profile["config_name"]
    provider = f"model_providers.{config_name}"
    return [
        str(codex_bin),
        "-a",
        "never",
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--json",
        "--skip-git-repo-check",
        "-C",
        str(work_dir),
        "-s",
        "danger-full-access",
        "-m",
        profile["model"],
        "-c",
        f'model_provider="{config_name}"',
        "-c",
        f'{provider}.name="{profile["display_name"]}"',
        "-c",
        f'{provider}.base_url="http://127.0.0.1:{port}/tasks/{task_key}/v1"',
        "-c",
        f'{provider}.env_key="{profile["api_key_env"]}"',
        "-c",
        f'{provider}.wire_api="responses"',
        "-c",
        f"{provider}.request_max_retries={PROVIDER_REQUEST_MAX_RETRIES}",
        "-c",
        f"{provider}.stream_max_retries={PROVIDER_STREAM_MAX_RETRIES}",
        "-c",
        f'model_reasoning_effort="{profile["reasoning_effort"]}"',
        "-c",
        f'model_context_window={profile["context_window"]}',
        "-c",
        f'model_max_output_tokens={profile["max_output_tokens"]}',
        prompt,
    ]


def isolated_codex_command(
    command: list[str],
    *,
    work_dir: Path,
    codex_bin: Path,
    verus_bin: Path,
    rust_root: Path,
    lynette_bin: Path,
    scratch_root: Path,
    bridge_port: int,
    code_mode_host: Path | None = None,
) -> list[str]:
    """Wrap Codex in a mount namespace that exposes only this task and tools."""
    wrapper = [
        str(UNSHARE_BIN),
        "--user",
        "--map-root-user",
        "--mount",
        "--fork",
        "--kill-child=SIGKILL",
        sys.executable,
        str(ISOLATION_RUNNER),
        "--workspace",
        str(work_dir),
        "--scratch-root",
        str(scratch_root),
        "--codex-bin",
        str(codex_bin),
        "--verus-root",
        str(verus_bin.parent.parent),
        "--rust-root",
        str(rust_root),
        "--lynette-bin",
        str(lynette_bin),
    ]
    if code_mode_host is not None:
        wrapper.extend(["--code-mode-host", str(code_mode_host)])
    wrapper.extend(["--bridge-port", str(bridge_port), "--", *command])
    return wrapper


def actor_subprocess_env(
    bridge_env: dict[str, str], provider_name: str = "deepseek"
) -> dict[str, str]:
    """Remove host credentials before model-generated commands can inspect env."""
    sensitive_fragments = (
        "API_KEY",
        "ACCESS_KEY",
        "SECRET",
        "TOKEN",
        "PASSWORD",
        "CREDENTIAL",
    )
    actor_env = {
        key: value
        for key, value in bridge_env.items()
        if not any(fragment in key.upper() for fragment in sensitive_fragments)
    }
    actor_env.pop("PYTHONPATH", None)
    actor_env[provider_profile(provider_name)["api_key_env"]] = (
        "local-bridge-only-not-a-provider-secret"
    )
    return actor_env


def bridge_identity_matches(
    health_payload: dict[str, Any],
    manifest: dict[str, Any],
    expected_instance_id: str,
) -> bool:
    return (
        health_payload.get("instance_id") == expected_instance_id
        and manifest.get("instance_id") == expected_instance_id
    )


def start_bridge(
    output: Path,
    env: dict[str, str],
    port: int,
    *,
    fake: bool,
    provider_name: str = "deepseek",
    budget_state_path: Path | None = None,
    approval_limit_usd: float = 20.0,
    prior_spend_usd: float = 0.0,
    request_reserve_usd: float = 0.25,
) -> subprocess.Popen[bytes]:
    profile = provider_profile(provider_name)
    instance_id = uuid.uuid4().hex
    command = [
        sys.executable,
        "-m",
        BRIDGE_MODULE,
        "--model",
        profile["model"],
        "--upstream-base-url",
        env[profile["base_url_env"]],
        "--api-key-env",
        profile["api_key_env"],
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--ledger-path",
        str(output / "bridge_calls.jsonl"),
        "--manifest-path",
        str(output / "bridge_manifest.json"),
        "--max-output-tokens",
        str(profile["max_output_tokens"]),
        "--chat-reasoning-effort",
        profile["chat_reasoning_effort"],
        "--chat-template-kwargs-json",
        json.dumps(profile["chat_template_kwargs"], separators=(",", ":")),
        "--reasoning-history-field",
        profile["reasoning_history_field"],
        "--request-timeout-seconds",
        "1800",
        "--instance-id",
        instance_id,
    ]
    if not profile["include_chat_thinking_field"]:
        command.append("--omit-chat-thinking-field")
    if fake:
        command.extend(
            [
                "--fake-reply",
                "Fake smoke complete after reading the supplied skill.",
                "--fake-tool-name",
                "exec_command",
                "--fake-tool-arguments",
                json.dumps(
                    {
                        "cmd": "sed -n '1,12p' skill/verus-proof-repair/SKILL.md"
                    }
                ),
            ]
        )
    else:
        if profile["native_responses"]:
            command.append("--native-responses")
        if budget_state_path is not None:
            command.extend(
                [
                    "--budget-state-path",
                    str(budget_state_path),
                    "--approval-limit-usd",
                    str(approval_limit_usd),
                    "--prior-spend-usd",
                    str(prior_spend_usd),
                    "--request-reserve-usd",
                    str(request_reserve_usd),
                ]
            )
    log_path = output / profile["bridge_log"]
    log = log_path.open("wb")
    process = subprocess.Popen(
        command,
        cwd=REPOSITORY_ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.close()
    try:
        deadline = time.monotonic() + 60
        health = f"http://127.0.0.1:{port}/health"
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    f"bridge exited early; see {log_path}"
                )
            try:
                with urlopen(health, timeout=2) as response:
                    if response.status != 200:
                        continue
                    health_payload = json.loads(
                        response.read().decode("utf-8")
                    )
                    manifest_path = output / "bridge_manifest.json"
                    if not manifest_path.is_file():
                        continue
                    manifest = json.loads(
                        manifest_path.read_text(encoding="utf-8")
                    )
                    if bridge_identity_matches(
                        health_payload, manifest, instance_id
                    ) and process.poll() is None:
                        return process
            except Exception:
                time.sleep(0.5)
        raise TimeoutError("DeepSeek bridge did not become healthy")
    except BaseException:
        stop_process_group(process)
        raise


def stop_process_group(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=15)


def run_codex(
    command: list[str],
    work_dir: Path,
    env: dict[str, str],
    log_path: Path,
    timeout_seconds: int,
) -> tuple[int, bool, float]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            command,
            cwd=work_dir,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=timeout_seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            stop_process_group(process)
            returncode = 124
        finally:
            # A supervisor SIGTERM is converted to SystemExit. This finally block
            # prevents the separately-sessioned Codex actor from surviving it.
            stop_process_group(process)
    return returncode, timed_out, round(time.monotonic() - started, 6)


def codex_terminal_status(log_path: Path) -> dict[str, Any]:
    """Return the last explicit Codex turn terminal event, ignoring diagnostics."""
    terminal: dict[str, Any] | None = None
    for line in log_path.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") not in {
            "turn.completed",
            "turn.failed",
        }:
            continue
        terminal = event
    event_type = terminal.get("type") if terminal is not None else None
    error = terminal.get("error") if terminal is not None else None
    message: str | None = None
    if isinstance(error, dict) and error.get("message") is not None:
        message = str(error["message"])
    elif isinstance(error, str):
        message = error
    return {
        "event_type": event_type,
        "completed": event_type == "turn.completed",
        "failed": event_type == "turn.failed",
        "error_message": message,
    }


def result_is_complete(result: dict[str, Any]) -> bool:
    """Legacy results are complete; new interrupted results opt out explicitly."""
    return bool(result.get("task_complete", True))


def archive_interrupted_task_attempt(
    output: Path,
    work: Path,
    log_path: Path,
) -> Path | None:
    """Preserve an interrupted attempt before recreating its task workspace."""
    if not work.exists() and not log_path.exists():
        return None
    attempt_root = (
        output
        / "interrupted_attempts"
        / work.name
        / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{uuid.uuid4().hex[:8]}"
    )
    attempt_root.mkdir(parents=True, exist_ok=False)
    if work.exists():
        shutil.move(str(work), str(attempt_root / "workspace"))
    if log_path.exists():
        shutil.move(str(log_path), str(attempt_root / "codex_events.jsonl"))
    write_json(
        attempt_root / "archive_manifest.json",
        {
            "archived_at": utc_now(),
            "reason": "interrupted_actor_attempt",
            "workspace_present": (attempt_root / "workspace").exists(),
            "codex_log_present": (attempt_root / "codex_events.jsonl").exists(),
        },
    )
    return attempt_root


def usage_for_task(ledger_path: Path, task_key: str) -> dict[str, Any]:
    rows = []
    if ledger_path.is_file():
        rows = [
            json.loads(line)
            for line in ledger_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    selected = [row for row in rows if row.get("task_id") == task_key]
    provider_fields = {
        "input_tokens": "prompt_tokens",
        "cache_hit_input_tokens": "prompt_cache_hit_tokens",
        "cache_miss_input_tokens": "prompt_cache_miss_tokens",
        "cache_write_input_tokens": "prompt_cache_write_tokens",
        "output_tokens": "completion_tokens",
        "reasoning_tokens": "reasoning_tokens",
        "total_tokens": "total_tokens",
    }
    result: dict[str, Any] = {key: 0 for key in provider_fields}
    result.update(
        {
            "request_count": 0,
            "failed_request_count": 0,
            "estimated_cost_usd": 0.0,
        }
    )
    for row in selected:
        for attempt in row.get("attempts") or []:
            usage = attempt.get("usage")
            if isinstance(usage, dict):
                result["request_count"] += 1
                for destination, source in provider_fields.items():
                    result[destination] += int(usage.get(source, 0) or 0)
                result["estimated_cost_usd"] += float(
                    attempt.get("estimated_cost_usd", 0.0) or 0.0
                )
            elif attempt.get("error"):
                result["failed_request_count"] += 1
    result["estimated_cost_usd"] = round(result["estimated_cost_usd"], 8)
    result["primary_uncached_tokens"] = (
        result["cache_miss_input_tokens"]
        + result["cache_write_input_tokens"]
        + result["output_tokens"]
    )
    return result


def added_bypass_audit(before: Path, after: Path) -> dict[str, Any]:
    old = before.read_text(encoding="utf-8").splitlines()
    new = after.read_text(encoding="utf-8").splitlines()
    added = [
        line[1:]
        for line in difflib.ndiff(old, new)
        if line.startswith("+ ")
    ]
    hits = {
        name: [line for line in added if pattern.search(line)]
        for name, pattern in ADDED_BYPASS_PATTERNS.items()
    }
    hits = {name: lines for name, lines in hits.items() if lines}
    return {
        "complete": True,
        "added_line_count": len(added),
        "forbidden_additions": hits,
        "passed": not hits,
    }


def command_access_audit(
    log_path: Path,
    *,
    work_dir: Path,
    verus_bin: Path,
    rust_root: Path,
    lynette_bin: Path,
    scratch_root: Path,
) -> dict[str, Any]:
    """Reject model commands that try to inspect host or sibling experiment roots."""
    allowed = sorted(
        (
            str(work_dir.resolve()),
            str(verus_bin.parent.parent.resolve()),
            str(rust_root.resolve()),
            str(lynette_bin.resolve()),
        ),
        key=len,
        reverse=True,
    )
    categories: set[str] = set()
    scratch_root_text = str(scratch_root.resolve())
    command_count = 0
    diagnostic_line_count = 0
    malformed_event_count = 0
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            if line == "Reading additional input from stdin..." or re.match(
                r"^\d{4}-\d{2}-\d{2}T[^ ]+\s+WARN\s+codex_[^:]+:", line
            ):
                diagnostic_line_count += 1
            else:
                malformed_event_count += 1
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if (
            event.get("type") != "item.started"
            or not isinstance(item, dict)
            or item.get("type") != "command_execution"
            or not isinstance(item.get("command"), str)
        ):
            continue
        command_count += 1
        masked = item["command"]
        for path in allowed:
            masked = masked.replace(path, "<ALLOWED_ROOT>")
        if scratch_root_text in masked:
            categories.add("scratch_root_probe")
        if "/home/" in masked or "/home " in masked:
            categories.add("home_root_probe")
        if re.search(
            r"\b(?:find|rg|grep)\b[^\n]*(?:^|[ \"\x27])/(?:[ \"\x27]|$)",
            masked,
        ):
            categories.add("filesystem_root_probe")
    return {
        "complete": True,
        "passed": not categories and malformed_event_count == 0,
        "command_count": command_count,
        "violation_count": len(categories),
        "violation_categories": sorted(categories),
        "diagnostic_line_count": diagnostic_line_count,
        "malformed_event_count": malformed_event_count,
    }


def score_task_outcome(
    *,
    timed_out: bool,
    actor_completed: bool,
    validation_complete: bool,
    safety_passed: bool,
    source_unchanged: bool,
    input_unchanged: bool,
) -> dict[str, Any]:
    """Separate proof outcome from audit observations and safety disqualification."""
    failure_reasons: list[str] = []
    if timed_out:
        failure_reasons.append("timeout")
    elif actor_completed and not validation_complete:
        failure_reasons.append("final_verification_failed")
    disqualifications: list[str] = []
    if not safety_passed:
        disqualifications.append("unsafe_proof_change")
    if not source_unchanged:
        disqualifications.append("frozen_source_changed")
    if not input_unchanged:
        disqualifications.append("input_rs_changed")
    return {
        "success": (
            actor_completed and not failure_reasons and not disqualifications
        ),
        "outcome_failure_reasons": failure_reasons,
        "safety_disqualifications": disqualifications,
    }


def audit_observations(
    access: dict[str, Any], usage: dict[str, Any]
) -> list[str]:
    observations: list[str] = []
    if int(access.get("violation_count", 0) or 0):
        observations.append("blocked_prohibited_filesystem_probe")
    if int(access.get("malformed_event_count", 0) or 0):
        observations.append("malformed_actor_log_event")
    if int(usage.get("failed_request_count", 0) or 0):
        observations.append("provider_request_failure")
    return observations


def task_summary_row(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": result["task_id"],
        "success": result["success"],
        "timed_out": result["timed_out"],
        "wall_time_seconds": result["wall_time_seconds"],
        "usage": result["usage"],
        "outcome_failure_reasons": result.get("outcome_failure_reasons", []),
        "safety_disqualifications": result.get("safety_disqualifications", []),
        "audit_observations": result.get("audit_observations", []),
    }


def summarize(results: list[dict[str, Any]], expected_count: int) -> dict[str, Any]:
    totals: dict[str, int | float] = defaultdict(int)
    for result in results:
        for key, value in result["usage"].items():
            if key != "estimated_cost_usd":
                totals[key] += int(value or 0)
        totals["estimated_cost_usd"] += float(
            result["usage"].get("estimated_cost_usd", 0.0) or 0.0
        )
    totals["estimated_cost_usd"] = round(
        float(totals["estimated_cost_usd"]), 8
    )
    unsafe = sum(not result["safety_audit"]["passed"] for result in results)
    contracts = sum(bool(result["contract_violations"]) for result in results)
    observation_counts = Counter(
        observation
        for result in results
        for observation in result.get("audit_observations", [])
    )
    return {
        "status": "complete" if len(results) == expected_count else "running",
        "completed_at": utc_now(),
        "completed_tasks": len(results),
        "task_count": expected_count,
        "successes": sum(bool(result["success"]) for result in results),
        "timeout_count": sum(bool(result["timed_out"]) for result in results),
        "wall_time_seconds": round(
            sum(float(result["wall_time_seconds"]) for result in results), 6
        ),
        "total_cost_usd": totals["estimated_cost_usd"],
        "usage": dict(totals),
        "coverage_complete": len(results) == expected_count,
        "fidelity": "V3_AUDITED" if len(results) == expected_count else "INCOMPLETE",
        "fidelity_complete": len(results) == expected_count
        and all(result["fidelity_audit_complete"] for result in results),
        "safety_audit_complete": len(results) == expected_count
        and all(result["safety_audit"]["complete"] for result in results),
        "safety_complete": len(results) == expected_count
        and all(result["safety_audit"]["complete"] for result in results),
        "unsafe_regression_count": unsafe,
        "contract_violation_count": contracts,
        "audit_observation_task_count": sum(
            bool(result.get("audit_observations")) for result in results
        ),
        "audit_observation_counts": dict(sorted(observation_counts.items())),
        "scoring_policy": "proof-outcome-v3",
        "tasks": [task_summary_row(result) for result in results],
    }


def prepare_output(
    output: Path,
    run_root: Path,
    *,
    resume: bool,
) -> None:
    assert_strict_child(output, run_root)
    if output.exists():
        if not resume and any(output.iterdir()):
            raise FileExistsError(f"actor output is not empty: {output}")
    else:
        output.mkdir(parents=True)


def snapshot_skill(output: Path, skill_dir: Path, resume: bool) -> Path:
    destination = output / "skill_snapshot" / "verus-proof-repair"
    if destination.exists():
        if not resume:
            raise FileExistsError(destination)
        if hash_skill_tree(destination) != hash_skill_tree(skill_dir):
            raise ValueError("resume skill snapshot differs from requested skill")
    else:
        shutil.copytree(skill_dir, destination)
    return destination


def run_smoke(args: argparse.Namespace) -> int:
    output = args.output_root.resolve()
    prepare_output(output, args.run_root.resolve(), resume=False)
    codex_bin = require_executable(args.codex_bin, "Codex")
    verus_bin = require_executable(args.verus_bin, "Verus")
    lynette_bin = require_executable(args.lynette_bin, "Lynette")
    rust_root = args.rust_root.resolve()
    if not rust_root.is_dir():
        raise ValueError(f"Rust toolchain root is invalid: {rust_root}")
    require_executable(UNSHARE_BIN, "unshare")
    require_executable(ISOLATION_RUNNER, "actor isolation runner")
    version = codex_version(codex_bin)
    if version != args.expected_codex_version:
        raise ValueError(f"Codex version mismatch: {version}")
    source_skill = args.skill_dir.resolve()
    audit = skill_audit(
        source_skill, require_zero_references=args.require_zero_references
    )
    snapshot = snapshot_skill(output, source_skill, resume=False)
    smoke_source = output / "configuration" / "smoke_input.rs"
    smoke_source.parent.mkdir(parents=True)
    smoke_source.write_text(
        "use vstd::prelude::*;\n\nverus! {\nfn smoke() { assert(true); }\n}\n\nfn main() {}\n",
        encoding="utf-8",
    )
    work = output / "tasks" / "smoke_skill_load"
    workspace = prepare_workspace(smoke_source, work, task="Synthetic skill-load smoke.")
    shutil.copytree(snapshot, work / "skill" / "verus-proof-repair")
    (work / "AGENTS.md").write_text(
        actor_prompt(True, args.verus_bin.resolve(), args.lynette_bin.resolve()),
        encoding="utf-8",
    )
    env = load_nonsecret_env(
        args.env_file.resolve(), execute=False, provider_name=args.provider
    )
    if not args.live_smoke:
        env[provider_profile(args.provider)["api_key_env"]] = "fake-local-smoke-key"
    task_key = "smoke--skill-load"
    proxy = start_bridge(
        output,
        env,
        args.proxy_port,
        fake=not args.live_smoke,
        provider_name=args.provider,
        budget_state_path=(args.budget_state_path if args.live_smoke else None),
        approval_limit_usd=args.approval_limit_usd,
        prior_spend_usd=args.prior_spend_usd,
        request_reserve_usd=args.request_reserve_usd,
    )
    try:
        log_path = output / "logs" / "smoke_skill_load.jsonl"
        command = isolated_codex_command(
            codex_command(
                work,
                args.proxy_port,
                task_key,
                codex_bin,
                "Read the supplied skill as instructed, then complete this smoke check.",
                provider_name=args.provider,
            ),
            work_dir=work,
            codex_bin=codex_bin,
            verus_bin=verus_bin,
            rust_root=rust_root,
            lynette_bin=lynette_bin,
            scratch_root=args.scratch_root.resolve(),
            code_mode_host=code_mode_host_for_provider(args.provider, codex_bin),
            bridge_port=args.proxy_port,
        )
        returncode, timed_out, wall = run_codex(
            command, work, actor_subprocess_env(env, args.provider), log_path, 120
        )
    finally:
        stop_process_group(proxy)
    usage = usage_for_task(output / "bridge_calls.jsonl", task_key)
    if not args.live_smoke:
        usage["estimated_cost_usd"] = 0.0
    usage["synthetic_usage"] = not args.live_smoke
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    access = command_access_audit(
        log_path,
        work_dir=work,
        verus_bin=verus_bin,
        rust_root=rust_root,
        lynette_bin=lynette_bin,
        scratch_root=args.scratch_root.resolve(),
    )
    checks = {
        "filesystem_access_audit": access["passed"],
        "codex_exit_zero": returncode == 0,
        "not_timed_out": not timed_out,
        "skill_path_appears_in_codex_events": (
            "skill/verus-proof-repair/SKILL.md" in log_text
        ),
        "candidate_unchanged": (
            sha256_file(workspace.input_path) == sha256_file(workspace.candidate_path)
        ),
        "provider_requests_recorded": usage["request_count"] >= 2,
        "skill_reference_policy": (
            not args.require_zero_references
            or (
                audit["reference_file_count"] == 0
                and not audit["reference_routes_present"]
            )
        ),
    }
    manifest = json.loads((output / "bridge_manifest.json").read_text(encoding="utf-8"))
    checks["bridge_mode_matches"] = (
        manifest.get("fake_mode") is (not args.live_smoke)
    )
    expected_protocol = (
        "native_responses_passthrough"
        if provider_profile(args.provider)["native_responses"]
        else "responses_to_chat_completions"
    )
    checks["bridge_protocol_matches"] = (
        manifest.get("protocol") == expected_protocol
    )
    result = {
        "status": "complete" if all(checks.values()) else "failed",
        "network_provider_requests": (
            usage["request_count"] if args.live_smoke else 0
        ),
        "codex_version": version,
        "bridge_commit": BRIDGE_COMMIT,
        "actor_runner_sha256": sha256_file(Path(__file__)),
        "bridge_source_sha256": sha256_file(BRIDGE_SOURCE),
        "skill_audit": audit,
        "filesystem_access_audit": access,
        "checks": checks,
        "usage": usage,
        "wall_time_seconds": wall,
        "log_path": str(log_path),
    }
    write_json(output / "smoke_summary.json", result)
    if result["status"] != "complete":
        raise RuntimeError(f"actor smoke failed: {checks}")
    print(json.dumps(result, indent=2), flush=True)
    return 0


def run_matrix(args: argparse.Namespace) -> int:
    profile = provider_profile(args.provider)
    output = args.output_root.resolve()
    prepare_output(output, args.run_root.resolve(), resume=args.resume)
    codex_bin = require_executable(args.codex_bin, "Codex")
    verus_bin = require_executable(args.verus_bin, "Verus")
    lynette_bin = require_executable(args.lynette_bin, "Lynette")
    rust_root = args.rust_root.resolve()
    if not rust_root.is_dir():
        raise ValueError(f"Rust toolchain root is invalid: {rust_root}")
    require_executable(UNSHARE_BIN, "unshare")
    require_executable(ISOLATION_RUNNER, "actor isolation runner")
    version = codex_version(codex_bin)
    if version != args.expected_codex_version:
        raise ValueError(f"Codex version mismatch: {version}")
    rows = select_tasks(load_split(args.split, args.split_root.resolve()), args.task_numbers)
    split_path = args.split_root.resolve() / args.split / "items.json"
    skill_source: Path | None = None
    skill_info: dict[str, Any] | None = None
    if args.condition == "skill":
        skill_source = args.skill_dir.resolve()
        skill_info = skill_audit(
            skill_source, require_zero_references=args.require_zero_references
        )
    prompt_template = actor_prompt(
        skill_source is not None, verus_bin, lynette_bin
    )
    template_work_dir = Path("{work_dir}")
    command_template = isolated_codex_command(
        codex_command(
            template_work_dir,
            args.proxy_port,
            f"{args.split}--{{task_key}}",
            codex_bin,
            prompt_template,
            provider_name=args.provider,
        ),
        work_dir=template_work_dir,
        codex_bin=codex_bin,
        verus_bin=verus_bin,
        rust_root=rust_root,
        lynette_bin=lynette_bin,
        scratch_root=args.scratch_root.resolve(),
        code_mode_host=code_mode_host_for_provider(args.provider, codex_bin),
        bridge_port=args.proxy_port,
    )
    actor_contract = {
        "command_template": command_template,
        "native_responses": profile["native_responses"],
        "provider_request_max_retries": PROVIDER_REQUEST_MAX_RETRIES,
        "provider_stream_max_retries": PROVIDER_STREAM_MAX_RETRIES,
        "outcome_policy": {
            "version": "proof-outcome-v3",
            "ordinary_failure_reasons": [
                "timeout",
                "final_verification_failed",
            ],
            "actor_terminal_event_required_for_final_verification_failure": True,
            "exhausted_provider_retries_block_batch_as_incomplete": True,
            "blocked_filesystem_probe_is_observation_only": True,
            "provider_request_failure_is_observation_only": True,
            "malformed_actor_log_event_is_observation_only": True,
            "requires_verus_and_lynette_pass": True,
            "unsafe_or_mutated_input_is_disqualifying": True,
        },
        "timeout_seconds_per_task": args.timeout_seconds,
        "verification_timeout_seconds": args.verification_timeout_seconds,
        "filesystem_isolation": {
            "mode": "user-mount-pid-network-namespace-whitelist-v2",
            "runner_path": str(ISOLATION_RUNNER.resolve()),
            "runner_sha256": sha256_file(ISOLATION_RUNNER),
            "unshare_path": str(UNSHARE_BIN.resolve()),
            "scratch_root_hidden_then_task_and_tools_rebound": True,
            "home_hidden": True,
            "tmp_private": True,
            "pid_private": True,
            "network_private_bridge_relay_only": True,
            "actor_capabilities_dropped": True,
            "mount_namespace_escape_blocked_by_seccomp": True,
            "workspace_writable": True,
            "verus_rust_lynette_read_only": True,
            "command_access_audit_required": True,
        },
        "credential_isolation": {
            "real_provider_key_exposed_to_actor": False,
            "sensitive_host_environment_removed": True,
            "local_bridge_placeholder_key_only": True,
        },
        "provider_budget": {
            "required": profile["requires_budget"],
            "shared_state_path": (
                str(args.budget_state_path.resolve())
                if args.budget_state_path is not None
                else None
            ),
            "approval_limit_usd": args.approval_limit_usd,
            "prior_spend_usd": args.prior_spend_usd,
            "request_reserve_usd": args.request_reserve_usd,
        },
    }
    manifest = {
        "schema_version": 1,
        "created_at": utc_now(),
        "status": "preflight" if args.preflight else "running",
        "split": args.split,
        "split_items_sha256": sha256_file(split_path),
        "selected_task_count": len(rows),
        "selected_task_numbers": [row["_split_index"] for row in rows],
        "project_counts": dict(sorted(Counter(row["project_code"] for row in rows).items())),
        "condition": args.condition,
        "skill": skill_info,
        "harness": profile["harness"],
        "codex_version": version,
        "codex_bin": str(codex_bin),
        "codex_bin_sha256": sha256_file(codex_bin),
        "verus_bin": str(verus_bin),
        "verus_bin_sha256": sha256_file(verus_bin),
        "lynette_bin": str(lynette_bin),
        "lynette_bin_sha256": sha256_file(lynette_bin),
        "rust_root": str(rust_root),
        "isolation_runner": str(ISOLATION_RUNNER.resolve()),
        "isolation_runner_sha256": sha256_file(ISOLATION_RUNNER),
        "actor_runner_sha256": sha256_file(Path(__file__)),
        "actor_contract": actor_contract,
        "actor_contract_sha256": canonical_sha256(actor_contract),
        "bridge_commit": BRIDGE_COMMIT,
        "bridge_source": str(BRIDGE_SOURCE),
        "bridge_source_sha256": sha256_file(BRIDGE_SOURCE),
        "model": profile["model"],
        "reasoning_effort": profile["reasoning_effort"],
        "timeout_seconds_per_task": args.timeout_seconds,
        "provider_retries": PROVIDER_REQUEST_MAX_RETRIES,
        "heldout_trajectory_or_verified_solution_exposed": False,
        "task_projection_sha256": canonical_sha256(
            [
                {
                    "split_index": row["_split_index"],
                    "task_id": row["task_id"],
                    "project_code": row["project_code"],
                    "source_sha256": row["source_sha256"],
                }
                for row in rows
            ]
        ),
    }
    manifest_path = output / "experiment_manifest.json"
    if args.resume:
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in (
            "split",
            "split_items_sha256",
            "selected_task_numbers",
            "condition",
            "skill",
            "harness",
            "model",
            "reasoning_effort",
            "codex_version",
            "codex_bin_sha256",
            "verus_bin_sha256",
            "lynette_bin_sha256",
            "isolation_runner_sha256",
            "actor_runner_sha256",
            "actor_contract_sha256",
            "bridge_source_sha256",
            "timeout_seconds_per_task",
            "task_projection_sha256",
        ):
            if prior.get(key) != manifest.get(key):
                raise ValueError(f"resume manifest mismatch: {key}")
        manifest = prior
        manifest["status"] = "running"
    else:
        write_json(output / "configuration" / "split_items.snapshot.json", json.loads(split_path.read_text(encoding="utf-8")))
    write_json(manifest_path, manifest)
    if args.preflight:
        write_json(
            output / "preflight.json",
            {
                "valid": True,
                "network_requests": 0,
                "selected_task_count": len(rows),
                "source_hashes_valid": True,
                "skill_valid": skill_info is not None or args.condition == "no-skill",
                "codex_version": version,
                "estimated_actor_invocations": len(rows),
            },
        )
        return 0

    snapshot = (
        snapshot_skill(output, skill_source, args.resume)
        if skill_source is not None
        else None
    )
    env = load_nonsecret_env(
        args.env_file.resolve(), execute=True, provider_name=args.provider
    )
    actor_env = actor_subprocess_env(env, args.provider)
    results: list[dict[str, Any]] = []
    for row in rows:
        result_path = task_result_path(output, row)
        if args.resume and result_path.is_file():
            prior_result = json.loads(result_path.read_text(encoding="utf-8"))
            if result_is_complete(prior_result):
                results.append(prior_result)
    completed_ids = {result["task_id"] for result in results}
    proxy = start_bridge(
        output,
        env,
        args.proxy_port,
        fake=False,
        provider_name=args.provider,
        budget_state_path=(
            args.budget_state_path.resolve()
            if args.budget_state_path is not None
            else None
        ),
        approval_limit_usd=args.approval_limit_usd,
        prior_spend_usd=args.prior_spend_usd,
        request_reserve_usd=args.request_reserve_usd,
    )
    try:
        for position, row in enumerate(rows, 1):
            if row["task_id"] in completed_ids:
                print(f"[{position:02d}/{len(rows):02d}] SKIP {row['task_id']}", flush=True)
                continue
            source = Path(row["_source_resolved"])
            work = output / "tasks" / row["normalized_task_id"]
            result_path = task_result_path(output, row)
            log_path = (
                output
                / "logs"
                / f"{row['_split_index']:02d}_{row['normalized_task_id']}.jsonl"
            )
            if args.resume:
                archived = archive_interrupted_task_attempt(output, work, log_path)
                if archived is not None:
                    print(
                        f"[{position:02d}/{len(rows):02d}] ARCHIVE "
                        f"{row['task_id']} -> {archived}",
                        flush=True,
                    )
            workspace = prepare_workspace(source, work, task="Repair candidate.rs.")
            workspace.verus_bin = workspace._require_executable(verus_bin, "Verus")
            workspace.lynette_bin = workspace._require_executable(lynette_bin, "Lynette")
            workspace.timeout_seconds = args.verification_timeout_seconds
            if snapshot is not None:
                shutil.copytree(snapshot, work / "skill" / "verus-proof-repair")
            (work / "AGENTS.md").write_text(
                actor_prompt(snapshot is not None, verus_bin, lynette_bin),
                encoding="utf-8",
            )
            task_key = f"{args.split}--{row['normalized_task_id']}"
            print(f"[{position:02d}/{len(rows):02d}] START {row['task_id']}", flush=True)
            started_at = utc_now()
            task_started_monotonic = time.monotonic()
            command = isolated_codex_command(
                codex_command(
                    work,
                    args.proxy_port,
                    task_key,
                    codex_bin,
                    actor_prompt(snapshot is not None, verus_bin, lynette_bin),
                    provider_name=args.provider,
                ),
                work_dir=work,
                codex_bin=codex_bin,
                verus_bin=verus_bin,
                rust_root=rust_root,
                lynette_bin=lynette_bin,
                scratch_root=args.scratch_root.resolve(),
                code_mode_host=code_mode_host_for_provider(args.provider, codex_bin),
                bridge_port=args.proxy_port,
            )
            exit_code, timed_out, codex_wall = run_codex(
                command, work, actor_env, log_path, args.timeout_seconds
            )
            terminal = codex_terminal_status(log_path)
            source_unchanged = sha256_file(source) == row["source_sha256"]
            input_unchanged = sha256_file(workspace.input_path) == row["source_sha256"]
            validation: dict[str, Any]
            try:
                workspace.run_verus()
                workspace.run_lynette()
                validation = workspace.validation_status()
            except Exception as exc:
                validation = {
                    "complete": False,
                    "verus_passed": False,
                    "lynette_passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            safety = added_bypass_audit(workspace.input_path, workspace.candidate_path)
            access = command_access_audit(
                log_path,
                work_dir=work,
                verus_bin=verus_bin,
                rust_root=rust_root,
                lynette_bin=lynette_bin,
                scratch_root=args.scratch_root.resolve(),
            )
            usage = usage_for_task(output / "bridge_calls.jsonl", task_key)
            score = score_task_outcome(
                timed_out=timed_out,
                actor_completed=bool(terminal["completed"]),
                validation_complete=bool(validation.get("complete")),
                safety_passed=bool(safety["passed"]),
                source_unchanged=source_unchanged,
                input_unchanged=input_unchanged,
            )
            success = bool(score["success"])
            observations = audit_observations(access, usage)
            contract_violations = list(score["safety_disqualifications"])
            wall = round(time.monotonic() - task_started_monotonic, 6)
            task_complete = bool(timed_out or terminal["completed"])
            result = {
                "split_index": row["_split_index"],
                "task_id": row["task_id"],
                "project_code": row["project_code"],
                "started_at": started_at,
                "finished_at": utc_now(),
                "wall_time_seconds": wall,
                "codex_wall_time_seconds": codex_wall,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "task_complete": task_complete,
                "actor_completed": bool(terminal["completed"]),
                "actor_terminal": terminal,
                "success": success,
                "validation": validation,
                "source_unchanged": source_unchanged,
                "input_unchanged": input_unchanged,
                "fidelity_audit_complete": access["complete"],
                "filesystem_access_audit": access,
                "safety_audit": safety,
                "contract_violations": contract_violations,
                "outcome_failure_reasons": score["outcome_failure_reasons"],
                "safety_disqualifications": score["safety_disqualifications"],
                "audit_observations": observations,
                "scoring_policy": "proof-outcome-v3",
                "usage": usage,
                "work_dir": str(work),
                "log_path": str(log_path),
            }
            write_json(result_path, result)
            if not task_complete:
                interrupted = summarize(results, len(rows))
                interrupted["status"] = "incomplete"
                interrupted["interrupted_task"] = task_summary_row(result)
                interrupted["actor_terminal"] = terminal
                write_json(output / "progress.json", interrupted)
                print(
                    f"[{position:02d}/{len(rows):02d}] INTERRUPTED "
                    f"{row['task_id']} rc={exit_code}; batch remains incomplete",
                    flush=True,
                )
                raise RuntimeError(
                    f"actor task interrupted before a terminal submission: "
                    f"{row['task_id']}"
                )
            results.append(result)
            summary = summarize(results, len(rows))
            write_json(output / "progress.json", summary)
            print(
                f"[{position:02d}/{len(rows):02d}] END {row['task_id']} "
                f"success={success} rc={exit_code}",
                flush=True,
            )
    finally:
        stop_process_group(proxy)
    results.sort(key=lambda result: result["split_index"])
    summary = summarize(results, len(rows))
    write_json(output / "summary.json", summary)
    manifest["status"] = "complete"
    manifest["completed_at"] = utc_now()
    manifest["summary_sha256"] = sha256_file(output / "summary.json")
    write_json(manifest_path, manifest)
    (output / "batch_complete").write_text(utc_now() + "\n", encoding="utf-8")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    result.add_argument(
        "--live-smoke",
        action="store_true",
        help="use the selected real provider during synthetic smoke",
    )
    result.add_argument("--split", choices=("val", "test"), default="val")
    result.add_argument(
        "--provider", choices=tuple(PROVIDER_PROFILES), default="deepseek"
    )
    result.add_argument("--split-root", type=Path, default=SPLIT_ROOT)
    result.add_argument("--condition", choices=("skill", "no-skill"), default="skill")
    result.add_argument("--skill-dir", type=Path, default=DEFAULT_M_CORE)
    result.add_argument("--require-zero-references", action="store_true")
    result.add_argument("--task-numbers", type=int, nargs="+")
    result.add_argument("--output-root", type=Path, required=True)
    result.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    result.add_argument("--scratch-root", type=Path, default=DEFAULT_SCRATCH_ROOT)
    result.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    result.add_argument("--codex-bin", type=Path, default=DEFAULT_CODEX)
    result.add_argument("--verus-bin", type=Path, default=DEFAULT_VERUS)
    result.add_argument("--rust-root", type=Path, default=DEFAULT_RUST_ROOT)
    result.add_argument("--lynette-bin", type=Path, default=DEFAULT_LYNETTE)
    result.add_argument("--expected-codex-version", default=EXPECTED_CODEX_VERSION)
    result.add_argument("--timeout-seconds", type=int, default=900)
    result.add_argument("--verification-timeout-seconds", type=int, default=120)
    result.add_argument("--proxy-port", type=int, default=4017)
    result.add_argument("--budget-state-path", type=Path)
    result.add_argument("--approval-limit-usd", type=float, default=20.0)
    result.add_argument("--prior-spend-usd", type=float, default=0.0)
    result.add_argument("--request-reserve-usd", type=float, default=0.25)
    result.add_argument("--resume", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.timeout_seconds <= 0 or args.verification_timeout_seconds <= 0:
        raise ValueError("timeouts must be positive")
    if (
        args.approval_limit_usd <= 0
        or args.prior_spend_usd < 0
        or args.request_reserve_usd <= 0
    ):
        raise ValueError(
            "provider budget values must be positive with nonnegative prior spend"
        )
    if args.budget_state_path is not None:
        assert_strict_child(args.budget_state_path, args.run_root)
    profile = provider_profile(args.provider)
    if (
        (args.execute or args.live_smoke)
        and profile["requires_budget"]
        and args.budget_state_path is None
    ):
        raise ValueError("paid actor execution requires --budget-state-path")
    if args.execute or args.smoke:
        def terminate_cleanly(signum: int, _frame: Any) -> None:
            raise SystemExit(128 + signum)

        signal.signal(signal.SIGTERM, terminate_cleanly)
        signal.signal(signal.SIGINT, terminate_cleanly)
    if args.live_smoke and not args.smoke:
        raise ValueError("--live-smoke requires --smoke")
    if args.smoke:
        if args.resume or args.condition != "skill":
            raise ValueError("smoke requires a fresh skill condition")
        return run_smoke(args)
    return run_matrix(args)


if __name__ == "__main__":
    raise SystemExit(main())
