#!/usr/bin/env python3
"""Manage the isolated local Qwen3.8-27B FP8 vLLM service and protocol smokes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WORKSPACE_ROOT = Path("/zp_vegeta/scratch_sb/xinyueh")
RUN_ROOT = WORKSPACE_ROOT / "verus_skill_runs" / "baseline-test-20260819" / "qwen"
MODEL_DIR = WORKSPACE_ROOT / "models" / "Qwen3.8-27B-FP8"
OLD_MODEL_DIR = WORKSPACE_ROOT / "models" / "Qwen3.6-27B"
VLLM_PYTHON = WORKSPACE_ROOT / "vllm-0.19.1-env" / "bin" / "python"
RUNTIME_OVERLAY = RUN_ROOT / "runtime_overlay"
MODEL_MANIFEST = RUN_ROOT / "model_snapshot_manifest.json"
RUNTIME_MANIFEST = RUN_ROOT / "runtime_manifest.json"
SERVICE_MANIFEST = RUN_ROOT / "service_manifest.json"
SERVICE_PID = RUN_ROOT / "service.pid"
SERVICE_LOG = RUN_ROOT / "vllm_service.log"
SMOKE_REPORT = RUN_ROOT / "service_smoke.json"
HOST = "127.0.0.1"
PORT = 8000
MODEL_NAME = "qwen38-27b-fp8"
LOCAL_API_KEY = "EMPTY"
EXPECTED_REVISION = "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def overlay_env() -> dict[str, str]:
    sensitive_fragments = (
        "API_KEY", "ACCESS_KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in sensitive_fragments)
    }
    prior = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(RUNTIME_OVERLAY) + (os.pathsep + prior if prior else "")
    env["CUDA_VISIBLE_DEVICES"] = "0,1,2,3"
    env["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    return env


def service_command() -> list[str]:
    return [
        str(VLLM_PYTHON),
        "-m",
        "vllm.entrypoints.cli.main",
        "serve",
        str(MODEL_DIR),
        "--host",
        HOST,
        "--port",
        str(PORT),
        "--api-key",
        LOCAL_API_KEY,
        "--served-model-name",
        MODEL_NAME,
        "--tensor-parallel-size",
        "4",
        "--max-model-len",
        "262144",
        "--kv-cache-dtype",
        "fp8",
        "--structured-outputs-config.reasoning_parser",
        "qwen3",
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        "qwen3_coder",
        "--default-chat-template-kwargs",
        json.dumps({"enable_thinking": True, "preserve_thinking": True}, separators=(",", ":")),
        "--enable-force-include-usage",
        "--max-num-seqs",
        "4",
        "--gpu-memory-utilization",
        "0.90",
        "--seed",
        "0",
    ]


def request_json(path: str, payload: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    url = f"http://{HOST}:{PORT}{path}"
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        url,
        data=data,
        method="GET" if payload is None else "POST",
        headers={"Authorization": f"Bearer {LOCAL_API_KEY}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def read_pid() -> int | None:
    if not SERVICE_PID.is_file():
        return None
    try:
        return int(SERVICE_PID.read_text().strip())
    except ValueError:
        return None


def process_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    stat_path = Path(f"/proc/{pid}/stat")
    try:
        if stat_path.is_file() and stat_path.read_text().split()[2] == "Z":
            return False
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, FileNotFoundError):
        return False
    except PermissionError:
        return True


def process_owned(pid: int) -> bool:
    command_path = Path(f"/proc/{pid}/cmdline")
    if not command_path.is_file():
        return False
    command = command_path.read_bytes().replace(b"\0", b" ").decode(errors="replace")
    return str(MODEL_DIR) in command and f"--port {PORT}" in command


def health() -> dict[str, Any]:
    pid = read_pid()
    result: dict[str, Any] = {"pid": pid, "process_alive": process_alive(pid), "process_owned": False, "api_healthy": False, "model_present": False}
    if pid and result["process_alive"]:
        result["process_owned"] = process_owned(pid)
    try:
        models = request_json("/v1/models", timeout=5)
        ids = [row.get("id") for row in models.get("data", [])]
        result.update({"api_healthy": True, "models": ids, "model_present": MODEL_NAME in ids})
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        result["api_error"] = f"{type(error).__name__}: {error}"
    result["healthy"] = bool(result["process_alive"] and result["process_owned"] and result["api_healthy"] and result["model_present"])
    return result


def assert_port_available() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        if stream.connect_ex((HOST, PORT)) == 0:
            raise RuntimeError(f"port {PORT} is occupied by an unrecognized service")


def runtime_versions() -> dict[str, Any]:
    code = "import json,torch,transformers,vllm; print(json.dumps({'torch':torch.__version__,'cuda':torch.version.cuda,'transformers':transformers.__version__,'vllm':vllm.__version__,'cuda_available':torch.cuda.is_available(),'gpu_count':torch.cuda.device_count()}))"
    completed = subprocess.run([str(VLLM_PYTHON), "-c", code], env=overlay_env(), text=True, capture_output=True, check=True)
    return json.loads(completed.stdout.strip().splitlines()[-1])


def preflight() -> dict[str, Any]:
    if not MODEL_MANIFEST.is_file():
        raise FileNotFoundError(MODEL_MANIFEST)
    model_manifest = json.loads(MODEL_MANIFEST.read_text())
    checks = {
        "model_manifest_all_ok": model_manifest.get("all_ok") is True,
        "model_revision_exact": model_manifest.get("resolved_revision") == EXPECTED_REVISION,
        "model_directory_present": MODEL_DIR.is_dir(),
        "old_model_retirement_acknowledged": True,
        "vllm_python_present": VLLM_PYTHON.is_file(),
        "runtime_overlay_present": RUNTIME_OVERLAY.is_dir(),
    }
    versions = runtime_versions()
    checks.update({
        "vllm_0_19_1": versions.get("vllm") == "0.19.1",
        "transformers_5_8_0": versions.get("transformers") == "5.8.0",
        "cuda_available": versions.get("cuda_available") is True,
        "four_visible_gpus": versions.get("gpu_count") == 4,
    })
    result = {
        "schema_version": 1,
        "valid": all(checks.values()),
        "created_at": utc_now(),
        "checks": checks,
        "versions": versions,
        "model_dir": str(MODEL_DIR),
        "model_revision": EXPECTED_REVISION,
        "model_manifest_sha256": sha256_file(MODEL_MANIFEST),
        "runtime_overlay": str(RUNTIME_OVERLAY),
        "runtime_overlay_sha256": hash_tree(RUNTIME_OVERLAY),
        "vllm_python": str(VLLM_PYTHON),
        "service_command": service_command(),
        "service_endpoint": f"http://{HOST}:{PORT}/v1",
        "served_model_name": MODEL_NAME,
        "paid_provider_credentials_used": False,
        "old_model_rollback_present": OLD_MODEL_DIR.is_dir(),
    }
    write_json(RUNTIME_MANIFEST, result)
    if not result["valid"]:
        raise RuntimeError(f"runtime preflight failed: {checks}")
    return result


def start(wait_seconds: int) -> dict[str, Any]:
    existing = health()
    if existing["healthy"]:
        return {"status": "already_running", **existing}
    if existing["process_alive"]:
        raise RuntimeError(f"recorded Qwen PID is alive but unhealthy: {existing}")
    assert_port_available()
    runtime = preflight()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    log = SERVICE_LOG.open("ab", buffering=0)
    process = subprocess.Popen(
        service_command(),
        cwd=RUN_ROOT,
        env=overlay_env(),
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.close()
    SERVICE_PID.write_text(f"{process.pid}\n")
    manifest = {
        "schema_version": 1,
        "status": "starting",
        "started_at": utc_now(),
        "pid": process.pid,
        "pgid": os.getpgid(process.pid),
        "host": HOST,
        "port": PORT,
        "model": MODEL_NAME,
        "model_dir": str(MODEL_DIR),
        "runtime_manifest_sha256": sha256_file(RUNTIME_MANIFEST),
        "command": service_command(),
        "log": str(SERVICE_LOG),
        "detached_session": True,
    }
    write_json(SERVICE_MANIFEST, manifest)
    deadline = time.monotonic() + wait_seconds
    stable_since: float | None = None
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"vLLM exited rc={process.returncode}; see {SERVICE_LOG}")
        last = health()
        if last["healthy"]:
            stable_since = stable_since or time.monotonic()
            if time.monotonic() - stable_since >= 20:
                manifest.update({"status": "healthy", "healthy_at": utc_now(), "health": last})
                write_json(SERVICE_MANIFEST, manifest)
                return manifest
        else:
            stable_since = None
        time.sleep(5)
    raise TimeoutError(f"Qwen service did not become stably healthy in {wait_seconds}s: {last}")


def direct_smoke() -> dict[str, Any]:
    state = health()
    if not state["healthy"]:
        raise RuntimeError(f"Qwen service is not healthy: {state}")
    common = {"model": MODEL_NAME, "stream": False, "reasoning_effort": "low", "chat_template_kwargs": {"enable_thinking": True, "preserve_thinking": True}}
    text_payload = {**common, "messages": [{"role": "user", "content": "Reply with exactly: QWEN38_OK"}], "max_tokens": 256}
    text_response = request_json("/v1/chat/completions", text_payload, timeout=300)
    text_message = text_response["choices"][0]["message"]
    tool = {"type": "function", "function": {"name": "multiply", "description": "Multiply two integers", "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"], "additionalProperties": False}}}
    tool_payload = {**common, "messages": [{"role": "user", "content": "Use the multiply tool to compute 6 times 7. You must call the tool."}], "tools": [tool], "tool_choice": "auto", "max_tokens": 512}
    tool_response = request_json("/v1/chat/completions", tool_payload, timeout=300)
    assistant = tool_response["choices"][0]["message"]
    calls = assistant.get("tool_calls") or []
    if not calls:
        raise RuntimeError(f"Qwen tool smoke returned no tool call: {assistant}")
    call = calls[0]
    continuation_payload = {**common, "messages": tool_payload["messages"] + [assistant, {"role": "tool", "tool_call_id": call["id"], "content": "42"}], "tools": [tool], "max_tokens": 256}
    continuation_response = request_json("/v1/chat/completions", continuation_payload, timeout=300)
    continuation_message = continuation_response["choices"][0]["message"]
    checks = {
        "models_endpoint": state["model_present"],
        "text_content_or_reasoning": bool(text_message.get("content") or text_message.get("reasoning") or text_message.get("reasoning_content")),
        "text_usage": int((text_response.get("usage") or {}).get("total_tokens", 0)) > 0,
        "tool_name": call.get("function", {}).get("name") == "multiply",
        "tool_arguments_json": isinstance(json.loads(call.get("function", {}).get("arguments") or "{}"), dict),
        "tool_usage": int((tool_response.get("usage") or {}).get("total_tokens", 0)) > 0,
        "continuation_content_or_reasoning": bool(continuation_message.get("content") or continuation_message.get("reasoning") or continuation_message.get("reasoning_content")),
        "continuation_usage": int((continuation_response.get("usage") or {}).get("total_tokens", 0)) > 0,
    }
    report = {"schema_version": 1, "status": "complete" if all(checks.values()) else "failed", "created_at": utc_now(), "checks": checks, "text_response": text_response, "tool_response": tool_response, "continuation_response": continuation_response}
    write_json(SMOKE_REPORT, report)
    if report["status"] != "complete":
        raise RuntimeError(f"Qwen direct protocol smoke failed: {checks}")
    return report


def process_group_members(pgid: int) -> list[int]:
    members: list[int] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == pgid:
                members.append(int(entry.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError, IndexError):
            continue
    return sorted(members)


def recorded_group_owned(pid: int) -> bool:
    if not SERVICE_MANIFEST.is_file():
        return False
    try:
        manifest = json.loads(SERVICE_MANIFEST.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return bool(
        manifest.get("pid") == pid
        and manifest.get("pgid") == pid
        and manifest.get("port") == PORT
        and manifest.get("model") == MODEL_NAME
        and manifest.get("model_dir") == str(MODEL_DIR)
    )


def stop() -> dict[str, Any]:
    pid = read_pid()
    if pid is None:
        return {"status": "not_running", "pid": pid}
    members = process_group_members(pid)
    if not members:
        return {"status": "not_running", "pid": pid}
    if not recorded_group_owned(pid):
        raise RuntimeError(f"refusing to stop unowned process group {pid}: {members}")
    if process_alive(pid) and not process_owned(pid):
        raise RuntimeError(f"refusing to stop unowned PID {pid}")
    os.killpg(pid, signal.SIGTERM)
    deadline = time.monotonic() + 60
    while process_group_members(pid) and time.monotonic() < deadline:
        time.sleep(1)
    forced = False
    members = process_group_members(pid)
    if members:
        if not recorded_group_owned(pid):
            raise RuntimeError(f"refusing to force-stop unowned process group {pid}: {members}")
        os.killpg(pid, signal.SIGKILL)
        forced = True
        deadline = time.monotonic() + 10
        while process_group_members(pid) and time.monotonic() < deadline:
            time.sleep(0.5)
    members = process_group_members(pid)
    if members:
        raise TimeoutError(f"Qwen service group {pid} survived exact-group SIGKILL: {members}")
    return {
        "status": "stopped",
        "pid": pid,
        "forced_after_sigterm": forced,
        "stopped_at": utc_now(),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--start", action="store_true")
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--stop", action="store_true")
    result.add_argument("--wait-seconds", type=int, default=1800)
    return result


def main() -> int:
    args = parser().parse_args()
    if args.wait_seconds <= 0:
        raise ValueError("--wait-seconds must be positive")
    if args.preflight:
        value = preflight()
    elif args.start:
        value = start(args.wait_seconds)
    elif args.status:
        value = health()
    elif args.smoke:
        value = direct_smoke()
    else:
        value = stop()
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
