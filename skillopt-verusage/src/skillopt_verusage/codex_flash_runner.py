from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from skill_evolution_pilot.codex_runner import (
    build_cross_provider_prompt,
    build_prompt,
    run_codex_smoke,
)
from skill_evolution_pilot.workspace import sha256_file
from skillopt_verusage.budget_guard import estimate_deepseek_cost


def _external_file(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"required file does not exist: {resolved}")
    return resolved


def _bridge_usage(
    path: Path, task_key: str, model: str = "deepseek-v4-flash"
) -> dict[str, Any]:
    totals: dict[str, Any] = {
        "requests": 0,
        "metered_requests": 0,
        "unmetered_requests": 0,
        "error_requests": 0,
        "completed_requests": 0,
        "incomplete_requests": 0,
        "unknown_status_requests": 0,
        "prompt_tokens": 0,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "estimated_cost_usd": 0.0,
        "unknown_cost_requests": 0,
        "price_bands": {},
        "upstream_models": [],
    }
    if not path.is_file():
        return totals
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("task_id") != task_key:
            continue
        upstream_model = str(record.get("upstream_model") or "")
        if upstream_model and upstream_model not in totals["upstream_models"]:
            totals["upstream_models"].append(upstream_model)
        for attempt in record.get("attempts") or []:
            totals["requests"] += 1
            status = str(attempt.get("finish_reason") or "")
            if status == "completed":
                totals["completed_requests"] += 1
            elif status == "incomplete":
                totals["incomplete_requests"] += 1
            else:
                totals["unknown_status_requests"] += 1
            if attempt.get("error"):
                totals["error_requests"] += 1
            usage = attempt.get("usage")
            if not isinstance(usage, dict):
                totals["unmetered_requests"] += 1
                continue
            totals["metered_requests"] += 1
            for key in (
                "prompt_tokens",
                "prompt_cache_hit_tokens",
                "prompt_cache_miss_tokens",
                "completion_tokens",
                "reasoning_tokens",
            ):
                totals[key] += int(usage.get(key, 0) or 0)
            price_band = str(attempt.get("price_band") or "")
            if price_band:
                totals["price_bands"][price_band] = (
                    int(totals["price_bands"].get(price_band, 0)) + 1
                )
            recorded_cost = attempt.get("estimated_cost_usd")
            if recorded_cost is not None:
                totals["estimated_cost_usd"] += float(recorded_cost)
            else:
                try:
                    totals["estimated_cost_usd"] += estimate_deepseek_cost(
                        usage,
                        model,
                        price_band=price_band or None,
                    )
                except ValueError:
                    totals["unknown_cost_requests"] += 1
    return totals


def _codex_terminal(raw_events: Path) -> dict[str, int]:
    totals = {"completed": 0, "failed": 0, "errors": 0}
    if not raw_events.is_file():
        return totals
    for line in raw_events.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            totals["errors"] += 1
            continue
        row_type = str(row.get("type") or "")
        if row_type == "turn.completed":
            totals["completed"] += 1
        elif row_type == "turn.failed":
            totals["failed"] += 1
        elif row_type == "error":
            totals["errors"] += 1
    return totals


def _compatible_upstream_model(configured: str, returned: str) -> bool:
    expected = configured.strip().lower().replace("_", "-")
    actual = returned.strip().lower().replace("_", "-")
    return actual == expected


def _classify_fidelity(
    result: dict[str, Any], provider_valid: bool, terminal: dict[str, int]
) -> str:
    # Codex emits `error` events for recoverable reconnects. A later unique
    # turn.completed plus a clean provider ledger is the terminal success.
    terminal_valid = bool(
        result.get("codex_returncode") == 0
        and not result.get("timed_out")
        and terminal["completed"] == 1
        and terminal["failed"] == 0
    )
    if (
        result.get("timed_out")
        and bool(result["fidelity"].get("input_unchanged"))
        and provider_valid
    ):
        return "V1_TRUNCATED"
    if bool(result["fidelity"].get("f3")) and provider_valid and terminal_valid:
        return "V2_TRACE"
    return "V0_INVALID"


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
    model: str,
    reasoning_effort: str,
    timeout_seconds: int,
    model_context_window: int,
    actor_contract_profile: str = "project",
    condition_skill_present: bool = True,
    codex_provider_id: str = "deepseek_bridge",
    run_stage: str = "skillopt_actor_rollout",
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
    if bridge_manifest.get("model") != model:
        raise ValueError("bridge manifest model mismatch")
    model_catalog_path = _external_file(bridge_manifest_path.parent / "models.json")
    if sha256_file(model_catalog_path) != bridge_manifest.get("model_catalog_sha256"):
        raise ValueError("Codex model catalog hash mismatch")
    protocol = str(bridge_manifest.get("protocol") or "")
    if protocol not in {
        "native_responses_passthrough",
        "responses_to_chat_completions",
    }:
        raise ValueError(f"unsupported bridge protocol: {protocol!r}")
    skill_text = skill_file.read_text(encoding="utf-8")
    injected_skill_text = skill_text if condition_skill_present else None
    provider_base_url = bridge_url.rstrip("/") + f"/tasks/{bridge_task_key}/v1"
    result = run_codex_smoke(
        source=source,
        out_dir=out_dir,
        codex_bin=codex_bin,
        verus_bin=verus_bin,
        lynette_bin=lynette_bin,
        model=model,
        reasoning_effort=reasoning_effort,
        reasoning_summary="detailed",
        show_raw_agent_reasoning=True,
        timeout_seconds=timeout_seconds,
        skill_text=injected_skill_text,
        provider_id=codex_provider_id,
        provider_base_url=provider_base_url,
        provider_env_key="SKILLOPT_CODEX_BRIDGE_TOKEN",
        model_context_window=model_context_window,
        model_catalog_json=model_catalog_path,
        contract_profile=actor_contract_profile,
        condition_skill_sha256=hashlib.sha256(
            skill_text.encode("utf-8")
        ).hexdigest(),
        stage=run_stage,
    )
    manifest_path = out_dir / "run_manifest.json"
    run_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_manifest["bridge"] = {
        "task_key": bridge_task_key,
        "config_sha256": bridge_manifest["config_sha256"],
        "implementation_sha256": bridge_manifest["implementation_sha256"],
        "protocol": bridge_manifest["protocol"],
        "native_responses": bridge_manifest["native_responses"],
        "fake_mode": bridge_manifest["fake_mode"],
        "chat_profile": bridge_manifest.get("chat_profile"),
        "pricing_profile": bridge_manifest.get("pricing_profile"),
        "model_catalog_sha256": bridge_manifest.get("model_catalog_sha256"),
    }
    run_manifest["condition_skill_present"] = condition_skill_present
    run_manifest["codex_provider_id"] = codex_provider_id
    manifest_path.write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validation = result["validation"]
    hard = bool(validation["verus"]["passed"] and validation["lynette"]["passed"])
    raw_events = out_dir / "codex_events.raw.jsonl"
    conversation = _conversation(raw_events, validation)
    usage = _bridge_usage(bridge_ledger_path, bridge_task_key, model)
    terminal = _codex_terminal(raw_events)
    returned_models = list(usage.get("upstream_models") or [])
    provider_valid = bool(
        usage["requests"] > 0
        and usage["metered_requests"] == usage["requests"]
        and usage["completed_requests"] > 0
        and usage["completed_requests"] + usage["incomplete_requests"]
        == usage["requests"]
        and usage["error_requests"] == 0
        and usage["unknown_cost_requests"] == 0
        and all(
            _compatible_upstream_model(
                str(bridge_manifest.get("expected_upstream_model") or model), value
            )
            for value in returned_models
        )
        and bool(returned_models)
    )
    # Preserve transient-error counts for audit without treating recovered
    # reconnects as a failed terminal state.
    terminal_valid = bool(
        result.get("codex_returncode") == 0
        and not result.get("timed_out")
        and terminal["completed"] == 1
        and terminal["failed"] == 0
    )
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
    fidelity = _classify_fidelity(result, provider_valid, terminal)
    if fidelity == "V0_INVALID" and not fail_reason:
        fail_reason = (
            "invalid-bridge-provider-or-codex-terminal: "
            f"provider={provider_valid} terminal={terminal_valid} "
            f"usage={usage} codex_terminal={terminal}"
        )[-4000:]
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
        "actor_model": model,
        "actor_harness": (
            "codex-cli-native-responses"
            if protocol == "native_responses_passthrough"
            else "codex-cli-responses-via-chat-bridge"
        ),
        "actor_reasoning_effort": reasoning_effort,
        "actor_contract_profile": actor_contract_profile,
        "bridge_task_key": bridge_task_key,
        "source_sha256": expected_source_sha256,
        "skill_sha256": hashlib.sha256(skill_text.encode("utf-8")).hexdigest(),
        "usage": usage,
        "codex_terminal": terminal,
        "provider_valid": provider_valid,
    }
    (out_dir / "conversation.json").write_text(
        json.dumps(conversation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    target_prompt = (
        build_cross_provider_prompt(
            skill_present=condition_skill_present,
            verus_bin=verus_bin,
            lynette_bin=lynette_bin,
        )
        if actor_contract_profile == "cross_provider_20260819"
        else build_prompt()
    )
    (out_dir / "target_user_prompt.txt").write_text(
        target_prompt, encoding="utf-8"
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
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--model-context-window", type=int, default=262144)
    parser.add_argument(
        "--actor-contract-profile",
        choices=("project", "cross_provider_20260819"),
        default="project",
    )
    parser.add_argument("--condition-skill-absent", action="store_true")
    parser.add_argument("--codex-provider-id", default="deepseek_bridge")
    parser.add_argument("--run-stage", default="skillopt_actor_rollout")
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
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        timeout_seconds=args.timeout_seconds,
        model_context_window=args.model_context_window,
        actor_contract_profile=args.actor_contract_profile,
        condition_skill_present=not args.condition_skill_absent,
        codex_provider_id=args.codex_provider_id,
        run_stage=args.run_stage,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
