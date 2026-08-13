from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from skill_evolution_pilot.codex_runner import build_prompt, run_codex_smoke
from skill_evolution_pilot.workspace import sha256_file
from skillopt_verusage.budget_guard import estimate_deepseek_cost


def _external_file(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"required file does not exist: {resolved}")
    return resolved


def _bridge_usage(path: Path, task_key: str) -> dict[str, Any]:
    totals: dict[str, Any] = {
        "requests": 0,
        "prompt_tokens": 0,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
    }
    if not path.is_file():
        totals["estimated_cost_usd"] = 0.0
        return totals
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("task_id") != task_key:
            continue
        for attempt in record.get("attempts") or []:
            usage = attempt.get("usage")
            if not isinstance(usage, dict):
                continue
            totals["requests"] += 1
            for key in (
                "prompt_tokens",
                "prompt_cache_hit_tokens",
                "prompt_cache_miss_tokens",
                "completion_tokens",
                "reasoning_tokens",
            ):
                totals[key] += int(usage.get(key, 0) or 0)
    totals["estimated_cost_usd"] = estimate_deepseek_cost(
        totals, "deepseek-v4-flash"
    )
    return totals


def _conversation(raw_events: Path, validation: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in raw_events.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    conversation: list[dict[str, Any]] = []
    for row in rows:
        if row.get("type") != "item.completed":
            continue
        item = row.get("item") or {}
        item_type = item.get("type")
        if item_type == "command_execution":
            conversation.append(
                {
                    "type": "tool_call",
                    "cmd": str(item.get("command") or ""),
                    "obs": str(item.get("aggregated_output") or ""),
                    "exit_code": item.get("exit_code"),
                }
            )
        elif item_type in {"agent_message", "reasoning"}:
            content = item.get("text") or item.get("content") or item.get("summary")
            if content is not None:
                conversation.append(
                    {
                        "role": "assistant",
                        "type": str(item_type),
                        "content": str(content),
                    }
                )
        elif item_type == "file_change":
            conversation.append(
                {
                    "role": "assistant",
                    "type": "file_change",
                    "content": json.dumps(
                        item.get("changes") or [], ensure_ascii=False
                    ),
                }
            )
    verus = validation["verus"]
    lynette = validation["lynette"]
    conversation.append(
        {
            "role": "system",
            "content": (
                f"Independent final Verus passed={verus['passed']}; "
                f"Lynette proof-only passed={lynette['passed']}.\n"
                f"Verus output:\n{verus.get('stdout', '')}{verus.get('stderr', '')}\n"
                f"Lynette output:\n{lynette.get('stdout', '')}{lynette.get('stderr', '')}"
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
    codex_bin: Path,
    verus_bin: Path,
    lynette_bin: Path,
    bridge_url: str,
    bridge_ledger_path: Path,
    bridge_manifest_path: Path,
    bridge_task_key: str,
    timeout_seconds: int,
    model_context_window: int,
) -> dict[str, Any]:
    if Path(item_id).name != item_id:
        raise ValueError(f"unsafe item id: {item_id!r}")
    if directory_group not in {"verified-anvil", "verified-ironkv"}:
        raise ValueError(f"forbidden directory group: {directory_group}")
    source = _external_file(source)
    if directory_group not in source.parts or "unverified" not in source.parts:
        raise ValueError(f"source is outside allowed unverified data: {source}")
    if sha256_file(source) != expected_source_sha256:
        raise ValueError(f"stale source hash: {source}")
    skill_file = _external_file(skill_file)
    bridge_manifest_path = _external_file(bridge_manifest_path)
    bridge_manifest = json.loads(bridge_manifest_path.read_text(encoding="utf-8"))
    if bridge_manifest.get("fake_mode"):
        raise ValueError("live Codex task cannot use a fake bridge")
    if bridge_manifest.get("model") != "deepseek-v4-flash":
        raise ValueError("bridge manifest model mismatch")
    skill_text = skill_file.read_text(encoding="utf-8")
    provider_base_url = (
        bridge_url.rstrip("/") + f"/tasks/{bridge_task_key}/v1"
    )
    result = run_codex_smoke(
        source=source,
        out_dir=out_dir,
        codex_bin=codex_bin,
        verus_bin=verus_bin,
        lynette_bin=lynette_bin,
        model="deepseek-v4-flash",
        reasoning_effort="high",
        reasoning_summary="detailed",
        show_raw_agent_reasoning=True,
        timeout_seconds=timeout_seconds,
        skill_text=skill_text,
        provider_id="deepseek_bridge",
        provider_base_url=provider_base_url,
        provider_env_key="DEEPSEEK_API_KEY",
        model_context_window=model_context_window,
    )
    manifest_path = out_dir / "run_manifest.json"
    run_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_manifest["bridge"] = {
        "task_key": bridge_task_key,
        "config_sha256": bridge_manifest["config_sha256"],
        "implementation_sha256": bridge_manifest["implementation_sha256"],
        "allowed_tool_names": bridge_manifest["allowed_tool_names"],
        "fake_mode": bridge_manifest["fake_mode"],
    }
    manifest_path.write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validation = result["validation"]
    hard = bool(validation["verus"]["passed"] and validation["lynette"]["passed"])
    raw_events = out_dir / "codex_events.raw.jsonl"
    conversation = _conversation(raw_events, validation)
    usage = _bridge_usage(bridge_ledger_path, bridge_task_key)
    fail_reason = ""
    if not hard:
        if result.get("timed_out"):
            fail_reason = f"codex-timeout-after-{timeout_seconds}s"
        else:
            diagnostic = (
                str(validation["verus"].get("stdout") or "")
                + str(validation["verus"].get("stderr") or "")
            ).strip()
            fail_reason = diagnostic[-4000:] or "independent-final-verus-failed"
    fidelity = (
        "V2_TRACE"
        if bool(result["fidelity"].get("f3"))
        else (
            "V1_TRUNCATED"
            if bool(result["fidelity"].get("input_unchanged"))
            and result.get("timed_out")
            else "V0_INVALID"
        )
    )
    enriched = {
        **result,
        "schema_version": "1",
        "id": item_id,
        "hard": int(hard),
        "soft": float(hard),
        "task_type": "anvil" if directory_group == "verified-anvil" else "ironkv",
        "task_description": "Repair a Verus proof while preserving executable behavior.",
        "fail_reason": fail_reason,
        "n_turns": sum(
            row.get("type") in {"tool_call", "file_change"} for row in conversation
        ),
        "fidelity": fidelity,
        "actor_model": "deepseek-v4-flash",
        "actor_harness": "codex-cli-responses-bridge",
        "bridge_task_key": bridge_task_key,
        "source_sha256": expected_source_sha256,
        "skill_sha256": hashlib.sha256(skill_text.encode("utf-8")).hexdigest(),
        "usage": usage,
    }
    (out_dir / "conversation.json").write_text(
        json.dumps(conversation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "target_user_prompt.txt").write_text(
        build_prompt(), encoding="utf-8"
    )
    (out_dir / "result.json").write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--directory-group", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--skill-file", type=Path, required=True)
    parser.add_argument("--codex-bin", type=Path, required=True)
    parser.add_argument("--verus-bin", type=Path, required=True)
    parser.add_argument("--lynette-bin", type=Path, required=True)
    parser.add_argument("--bridge-url", required=True)
    parser.add_argument("--bridge-ledger-path", type=Path, required=True)
    parser.add_argument("--bridge-manifest-path", type=Path, required=True)
    parser.add_argument("--bridge-task-key", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--model-context-window", type=int, default=262144)
    args = parser.parse_args()
    result = run_task(
        item_id=args.item_id,
        source=args.source,
        expected_source_sha256=args.expected_source_sha256,
        directory_group=args.directory_group,
        out_dir=args.out_dir,
        skill_file=args.skill_file,
        codex_bin=args.codex_bin,
        verus_bin=args.verus_bin,
        lynette_bin=args.lynette_bin,
        bridge_url=args.bridge_url,
        bridge_ledger_path=args.bridge_ledger_path,
        bridge_manifest_path=args.bridge_manifest_path,
        bridge_task_key=args.bridge_task_key,
        timeout_seconds=args.timeout_seconds,
        model_context_window=args.model_context_window,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
