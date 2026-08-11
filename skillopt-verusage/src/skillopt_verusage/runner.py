from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path
from typing import Any

from skillopt_verusage.budget_guard import FLASH_RATES_USD_PER_MILLION
from skillopt_verusage.skill_proxy import SkillAwareDeepSeekLLM


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _external_task_dir(path: Path) -> Path:
    root_text = os.environ.get("VERUS_SKILL_RUN_ROOT", "")
    if not root_text:
        raise ValueError("VERUS_SKILL_RUN_ROOT is not configured")
    root = Path(root_text).resolve()
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"task output must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    if resolved.exists() and any(resolved.iterdir()):
        raise ValueError(f"task output must be empty: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _executable(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ValueError(f"{label} is not executable: {resolved}")
    return resolved


def _run(command: list[str], cwd: Path, timeout: int = 120) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "timed_out": False,
            "wall_seconds": time.monotonic() - started,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "returncode": None,
            "timed_out": True,
            "wall_seconds": time.monotonic() - started,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
        }


def _verus_passed(result: dict[str, Any]) -> bool:
    output = str(result["stdout"]) + str(result["stderr"])
    return (
        result["returncode"] == 0
        and not result["timed_out"]
        and "error: aborting" not in output.lower()
    )


def _load_calls(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _usage_summary(calls: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Any] = {
        "requests": len(calls),
        "prompt_tokens": 0,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 0,
        "completion_tokens": 0,
    }
    for call in calls:
        usage = call.get("usage") or {}
        for key in totals:
            if key != "requests":
                totals[key] += int(usage.get(key, 0) or 0)
    cost = sum(
        totals[key] * rate / 1_000_000
        for key, rate in FLASH_RATES_USD_PER_MILLION.items()
    )
    totals["estimated_cost_usd"] = round(cost, 8)
    return totals


def _compact_conversation(
    calls: list[dict[str, Any]],
    validation: dict[str, Any],
    error: str | None,
) -> list[dict[str, str]]:
    conversation: list[dict[str, str]] = []
    accepted_calls = [
        call
        for call in calls
        if bool(call.get("accepted", call.get("error") is None))
    ]
    for call in accepted_calls[-3:]:
        messages = call.get("messages") or []
        user_text = next(
            (
                str(message.get("content") or "")
                for message in reversed(messages)
                if message.get("role") == "user"
            ),
            "",
        )
        response = str((call.get("responses") or [""])[0])
        reasoning = str((call.get("reasoning_content") or [""])[0])
        assistant_text = response[-1800:]
        if reasoning:
            assistant_text = (
                f"Reasoning excerpt:\n{reasoning[-900:]}\n\n"
                f"Final response:\n{assistant_text}"
            )
        conversation.extend(
            [
                {
                    "role": "user",
                    "content": f"VeruSAGE call {call.get('call_index')}: {user_text[-1200:]}",
                },
                {"role": "assistant", "content": assistant_text},
            ]
        )
    verus = validation["verus"]
    lynette = validation["lynette"]
    verifier_text = (str(verus["stdout"]) + str(verus["stderr"]))[-1800:]
    conversation.append(
        {
            "role": "system",
            "content": (
                "Independent final validation: "
                f"Verus passed={verus['passed']}; "
                f"Lynette proof-only passed={lynette['passed']}; "
                f"runner_error={error or 'none'}.\n{verifier_text}"
            ),
        }
    )
    return conversation


def run_task(
    *,
    item_id: str,
    source: Path,
    expected_source_sha256: str,
    directory_group: str,
    out_dir: Path,
    skill_file: Path,
    model: str,
    verusage_src_root: Path,
    verus_bin: Path,
    lynette_bin: Path,
    repair_attempts: int = 20,
    request_cap: int = 512,
    action_output_tokens: int = 32768,
    reasoning_output_tokens: int = 32768,
    retry_action_output_tokens: int = 262144,
    retry_reasoning_output_tokens: int = 262144,
    max_action_output_tokens: int = 384000,
    max_reasoning_output_tokens: int = 384000,
    request_timeout_seconds: int = 1800,
    budget_state_path: Path | None = None,
    budget_approval_limit_usd: float = 20.0,
    budget_prior_spend_usd: float = 0.0,
    budget_optimizer_reserve_usd: float = 1.0,
    budget_request_reserve_usd: float = 0.3,
) -> dict[str, Any]:
    started = time.monotonic()
    if Path(item_id).name != item_id:
        raise ValueError(f"unsafe item id: {item_id!r}")
    if directory_group not in {"verified-anvil", "verified-ironkv"}:
        raise ValueError(f"forbidden directory group: {directory_group}")
    source = source.resolve()
    if directory_group not in source.parts or "unverified" not in source.parts:
        raise ValueError(f"source is outside the allowed unverified tree: {source}")
    if _sha256_file(source) != expected_source_sha256:
        raise ValueError(f"stale source hash: {source}")

    out_dir = _external_task_dir(out_dir)
    verus_bin = _executable(verus_bin, "verus")
    lynette_bin = _executable(lynette_bin, "lynette")
    verusage_src_root = verusage_src_root.resolve()
    if not (verusage_src_root / "repair_runner.py").is_file():
        raise ValueError(f"invalid VeruSAGE source root: {verusage_src_root}")

    temp_root = out_dir / "tmp"
    temp_root.mkdir()
    os.environ["TMPDIR"] = str(temp_root)
    tempfile.tempdir = str(temp_root)
    workspace = out_dir / "workspace"
    workspace.mkdir()
    input_path = workspace / "input.rs"
    candidate_path = workspace / "candidate.rs"
    shutil.copyfile(source, input_path)
    shutil.copyfile(source, candidate_path)
    skill_text = skill_file.read_text(encoding="utf-8")
    calls_path = out_dir / "target_calls.jsonl"
    calls_path.touch()

    manifest = {
        "schema_version": "1",
        "item_id": item_id,
        "directory_group": directory_group,
        "model": model,
        "source_sha256": expected_source_sha256,
        "skill_sha256": hashlib.sha256(skill_text.encode("utf-8")).hexdigest(),
        "repair_attempts": repair_attempts,
        "request_cap": request_cap,
        "action_output_tokens": action_output_tokens,
        "reasoning_output_tokens": reasoning_output_tokens,
        "retry_action_output_tokens": retry_action_output_tokens,
        "retry_reasoning_output_tokens": retry_reasoning_output_tokens,
        "max_action_output_tokens": max_action_output_tokens,
        "max_reasoning_output_tokens": max_reasoning_output_tokens,
        "request_timeout_seconds": request_timeout_seconds,
        "budget_approval_limit_usd": budget_approval_limit_usd,
        "budget_prior_spend_usd": budget_prior_spend_usd,
        "budget_optimizer_reserve_usd": budget_optimizer_reserve_usd,
        "reference_proof_visible": False,
        "prior_trace_visible": False,
    }
    (out_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    error_text: str | None = None
    internal_exit_code: int | None = None
    try:
        from loguru import logger

        logger.remove()
        logger.add(out_dir / "verusage.log", rotation="100 MB")

        class BoundLLM(SkillAwareDeepSeekLLM):
            def __init__(self, config, bound_logger):
                super().__init__(
                    config,
                    bound_logger,
                    skill_text=skill_text,
                    calls_path=calls_path,
                    request_cap=request_cap,
                    action_output_tokens=action_output_tokens,
                    reasoning_output_tokens=reasoning_output_tokens,
                    retry_action_output_tokens=retry_action_output_tokens,
                    retry_reasoning_output_tokens=retry_reasoning_output_tokens,
                    max_action_output_tokens=max_action_output_tokens,
                    max_reasoning_output_tokens=max_reasoning_output_tokens,
                    request_timeout_seconds=request_timeout_seconds,
                    budget_state_path=budget_state_path,
                    budget_approval_limit_usd=budget_approval_limit_usd,
                    budget_prior_spend_usd=budget_prior_spend_usd,
                    budget_optimizer_reserve_usd=budget_optimizer_reserve_usd,
                    budget_request_reserve_usd=budget_request_reserve_usd,
                )

        infer_module = types.ModuleType("infer")
        setattr(infer_module, "LLM", BoundLLM)
        sys.modules["infer"] = infer_module
        sys.path.insert(0, str(verusage_src_root))

        from utils import AttrDict
        from veval import verus
        from lynette import lynette as internal_lynette
        from global_config import GlobalConfig
        from repair_runner import RepairRunner

        internal_lynette.meta_command = [str(lynette_bin)]
        verus.set_verus_path(str(verus_bin))
        config = AttrDict(
            {
                "use_openai": True,
                "aoai_api_base": ["https://api.deepseek.com"],
                "aoai_api_version": "",
                "aoai_api_key": [],
                "aoai_max_retries": 0,
                "max_token": action_output_tokens,
                "aoai_generation_model": model,
                "aoai_debug_model": model,
                "verus_path": str(verus_bin),
            }
        )
        verusage_dir = out_dir / "verusage"
        verusage_dir.mkdir()
        GlobalConfig.initialize(config, logger, verusage_dir)
        args = {
            "repair": repair_attempts,
            "func_name": None,
            "tree_search": False,
            "accept_rule": "default",
            "ablation_mode": False,
            "swap_case_compute": False,
        }
        runner = RepairRunner(
            ablation_mode=False,
            accept_rule="default",
            args=args,
        )
        internal_exit_code = runner.run(
            str(input_path),
            str(candidate_path),
            args,
        )
    except Exception as error:
        error_text = f"{type(error).__name__}: {error}"

    final_verus = _run([str(verus_bin), "candidate.rs"], workspace)
    final_verus["passed"] = _verus_passed(final_verus)
    final_lynette = _run(
        [str(lynette_bin), "compare", "-t", "input.rs", "candidate.rs"],
        workspace,
    )
    final_lynette["passed"] = (
        final_lynette["returncode"] == 0 and not final_lynette["timed_out"]
    )
    input_unchanged = _sha256_file(input_path) == expected_source_sha256
    validation = {
        "input_unchanged": input_unchanged,
        "verus": final_verus,
        "lynette": final_lynette,
    }
    (out_dir / "validation.json").write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    calls = _load_calls(calls_path)
    usage = _usage_summary(calls)
    accepted_calls = [call for call in calls if call.get("accepted") is True]
    rejected_responses = [
        call for call in calls if call.get("response_issue") not in {None, "provider_error"}
    ]
    silent_truncations = [
        call
        for call in accepted_calls
        if "length" in (call.get("finish_reasons") or [])
        or not any(str(value).strip() for value in call.get("responses") or [])
    ]
    response_integrity = {
        "accepted_calls": len(accepted_calls),
        "explicitly_rejected_responses": len(rejected_responses),
        "silent_truncations": len(silent_truncations),
    }
    (out_dir / "usage.json").write_text(
        json.dumps(usage, indent=2) + "\n",
        encoding="utf-8",
    )
    solved = bool(
        input_unchanged
        and final_verus["passed"]
        and final_lynette["passed"]
        and error_text is None
    )
    result = {
        "id": item_id,
        "hard": int(solved),
        "soft": float(solved),
        "task_type": "anvil" if directory_group == "verified-anvil" else "ironkv",
        "task_description": "Repair a Verus proof while preserving executable behavior.",
        "fail_reason": "" if solved else (error_text or "independent verifier rejected candidate"),
        "n_turns": usage["requests"],
        "internal_exit_code": internal_exit_code,
        "request_count": usage["requests"],
        "usage": usage,
        "response_integrity": response_integrity,
        "input_unchanged": input_unchanged,
        "final_verus_passed": final_verus["passed"],
        "final_lynette_passed": final_lynette["passed"],
        "candidate_sha256": _sha256_file(candidate_path),
        "wall_seconds": time.monotonic() - started,
        "fidelity": "V0_INVALID" if error_text is not None else "V2_TRACE",
    }
    (out_dir / "conversation.json").write_text(
        json.dumps(
            _compact_conversation(calls, validation, error_text),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--directory-group", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--skill-file", type=Path, required=True)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--verusage-src-root", type=Path, required=True)
    parser.add_argument("--verus-bin", type=Path, required=True)
    parser.add_argument("--lynette-bin", type=Path, required=True)
    parser.add_argument("--repair-attempts", type=int, default=20)
    parser.add_argument("--request-cap", type=int, default=512)
    parser.add_argument("--action-output-tokens", type=int, default=32768)
    parser.add_argument("--reasoning-output-tokens", type=int, default=32768)
    parser.add_argument("--retry-action-output-tokens", type=int, default=262144)
    parser.add_argument("--retry-reasoning-output-tokens", type=int, default=262144)
    parser.add_argument("--max-action-output-tokens", type=int, default=384000)
    parser.add_argument("--max-reasoning-output-tokens", type=int, default=384000)
    parser.add_argument("--request-timeout-seconds", type=int, default=1800)
    parser.add_argument("--budget-state-path", type=Path)
    parser.add_argument("--budget-approval-limit-usd", type=float, default=20.0)
    parser.add_argument("--budget-prior-spend-usd", type=float, default=0.0)
    parser.add_argument("--budget-optimizer-reserve-usd", type=float, default=1.0)
    parser.add_argument("--budget-request-reserve-usd", type=float, default=0.3)
    args = parser.parse_args()
    result = run_task(**vars(args))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
