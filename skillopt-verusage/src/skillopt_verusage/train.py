from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from skillopt.config import flatten_config, load_config
from skillopt.engine.trainer import ReflACTTrainer

from skillopt_verusage.adapter import VeruSAGEAdapter
from skillopt_verusage.codex_flash_adapter import CodexDeepSeekAdapter
from skillopt_verusage.codex_reoptimize import _install_prompt_free_codex_ledger
from skillopt_verusage.cost_ledger import write_cost_ledger


ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _bridge_health(bridge_url: str) -> dict[str, Any]:
    with urlopen(bridge_url.rstrip("/") + "/health", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_bridge_drain(bridge_url: str, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        health = _bridge_health(bridge_url)
        if int(health.get("active_requests", -1)) == 0:
            return health
        if time.monotonic() >= deadline:
            raise RuntimeError(f"BRIDGE_DRAIN_TIMEOUT: {health}")
        time.sleep(2)


def _validate_fresh_formal_run(cfg: dict[str, Any]) -> None:
    if cfg.get("formal_epoch_contract") == "fixed_600s_v1":
        timeout_contract = {
            "task_retries": 2,
            "timeout_retries": 0,
            "codex_timeout_seconds": 600,
            "max_codex_timeout_seconds": 600,
            "formal_epoch_contract": "fixed_600s_v1",
        }
    else:
        timeout_contract = {
            "task_retries": 2,
            "codex_timeout_seconds": 1200,
            "max_codex_timeout_seconds": 3600,
            "formal_epoch_contract": True,
        }
    contract = {
        "target_harness": "codex_cli_native_responses",
        "target_model": "deepseek-v4-pro",
        "optimizer_model": "gpt-5.6-sol",
        "optimizer_backend": "codex_exec",
        "reasoning_effort": "max",
        "num_epochs": 1,
        "train_size": 40,
        "batch_size": 40,
        "seed": 42,
        "sel_env_num": 20,
        "test_env_num": 20,
        "eval_test": False,
        "use_gate": True,
        "gate_metric": "hard",
        "workers": 40,
        "model_context_window": 1048576,
        **timeout_contract,
    }
    mismatches = {
        key: {"actual": cfg.get(key), "expected": value}
        for key, value in contract.items()
        if cfg.get(key) != value
    }
    if mismatches:
        raise RuntimeError(f"FORMAL_RECIPE_MISMATCH: {mismatches}")
    split_manifest = json.loads(
        (Path(cfg["split_dir"]) / "split_manifest.json").read_text(encoding="utf-8")
    )
    expected_split_sha = (
        "a71e2a3838c2222312cc2487fc35b6a24cbc924e0a917d5e9120499f0ba2b49c"
    )
    if split_manifest.get("split_sha256") != expected_split_sha:
        raise RuntimeError("FORMAL_SPLIT_SHA_MISMATCH")
    initial_skill_sha = hashlib.sha256(Path(cfg["skill_init"]).read_bytes()).hexdigest()
    if (
        initial_skill_sha
        != "96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40"
    ):
        raise RuntimeError("FORMAL_INITIAL_SKILL_SHA_MISMATCH")
    root = Path(cfg["out_root"]).resolve()
    allowed = {
        "bridge.log",
        "bridge_calls.jsonl",
        "bridge_manifest.json",
        "launch_manifest.json",
        "models.json",
        "train.log",
    }
    if root.is_dir():
        unexpected = sorted(
            path.name for path in root.iterdir() if path.name not in allowed
        )
        if unexpected:
            raise RuntimeError(f"FORMAL_RUN_ROOT_NOT_FRESH: {unexpected}")
    manifest_path = Path(cfg["codex_bridge_manifest_path"])
    if not manifest_path.is_file():
        raise RuntimeError(f"missing bridge manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "model": cfg["target_model"],
        "expected_upstream_model": "deepseek-v4-pro",
        "native_responses": True,
        "fake_mode": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise RuntimeError(
                f"bridge manifest mismatch for {key}: {manifest.get(key)!r} != {value!r}"
            )
    if not manifest.get("model_catalog_sha256"):
        raise RuntimeError("bridge manifest is missing model_catalog_sha256")
    if int(manifest.get("request_timeout_seconds", 0)) >= int(
        cfg["codex_timeout_seconds"]
    ):
        raise RuntimeError(
            "bridge request timeout must be below the actor task timeout"
        )
    health = _bridge_health(cfg["codex_bridge_url"])
    if health.get("model") != cfg["target_model"]:
        raise RuntimeError(f"bridge health model mismatch: {health}")
    if int(health.get("active_requests", -1)) != 0:
        raise RuntimeError(f"bridge is not idle before launch: {health}")


def _result_count(path: Path) -> int:
    predictions = path / "predictions"
    if not predictions.is_dir():
        return 0
    return sum(
        (task / "result.json").is_file()
        for task in predictions.iterdir()
        if task.is_dir()
    )


def _validate_formal_epoch(
    cfg: dict[str, Any], summary: dict[str, Any], ledger: dict[str, Any]
) -> dict[str, Any]:
    root = Path(cfg["out_root"]).resolve()
    counts = {
        "baseline_selection": _result_count(root / "selection_eval_baseline"),
        "train": _result_count(root / "steps" / "step_0001" / "rollout"),
        "candidate_selection": _result_count(
            root / "steps" / "step_0001" / "selection_eval"
        ),
    }
    errors: list[str] = []
    expected_counts = {"baseline_selection": 20, "train": 40, "candidate_selection": 20}
    if counts != expected_counts:
        errors.append(f"actor task schedule mismatch: {counts} != {expected_counts}")
    if int(summary.get("total_steps", -1)) != 1:
        errors.append(
            f"expected one completed optimizer step: {summary.get('total_steps')}"
        )
    if int(summary.get("total_skips", 0)):
        failed_optimizer = int((ledger.get("optimizer") or {}).get("failed_calls", 0))
        errors.append(
            "optimizer infrastructure failed before producing S1"
            if failed_optimizer
            else "optimizer produced no distinct usable S1"
        )
    decisions = int(summary.get("total_accepts", 0)) + int(
        summary.get("total_rejects", 0)
    )
    if decisions != 1:
        errors.append(f"expected exactly one strict gate decision, got {decisions}")
    baseline_skill = root / "selection_eval_baseline" / "skill.md"
    candidate_skill = root / "steps" / "step_0001" / "candidate_skill.md"
    if not baseline_skill.is_file() or not candidate_skill.is_file():
        errors.append("missing baseline or candidate skill")
    elif baseline_skill.read_bytes() == candidate_skill.read_bytes():
        errors.append("candidate S1 is byte-identical to S0")
    if not (ledger.get("target") or {}).get("accounting_complete"):
        errors.append("actor cost accounting contains unknown usage or cost")
    if not (ledger.get("optimizer") or {}).get("accounting_complete"):
        errors.append("optimizer attempt accounting contains unknown usage")
    if any(root.glob("*test*")):
        errors.append("held-out test artifacts unexpectedly exist")
    validation = {
        "schema_version": "1",
        "status": "pass" if not errors else "fail",
        "actor_task_counts": counts,
        "expected_actor_task_counts": expected_counts,
        "errors": errors,
    }
    _write_json(root / "formal_epoch_validation.json", validation)
    if errors:
        raise RuntimeError("FORMAL_EPOCH_INVALID: " + "; ".join(errors))
    return validation


def _expand(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand(item) for item in value]
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in os.environ:
            raise ValueError(f"required environment variable is not set: {key}")
        return os.environ[key]

    return ENV_PATTERN.sub(replace, value)


def _adapter(cfg: dict[str, Any]) -> VeruSAGEAdapter:
    if cfg.get("target_harness") in {
        "codex_cli_bridge",
        "codex_cli_native_responses",
    }:
        return CodexDeepSeekAdapter(
            split_dir=cfg["split_dir"],
            codex_bin=cfg["codex_exec_path"],
            verus_bin=cfg["verus_bin"],
            lynette_bin=cfg["lynette_bin"],
            bridge_url=cfg["codex_bridge_url"],
            bridge_ledger_path=cfg["codex_bridge_ledger_path"],
            bridge_manifest_path=cfg["codex_bridge_manifest_path"],
            model=cfg["target_model"],
            reasoning_effort=cfg.get("reasoning_effort", "high"),
            workers=cfg.get("workers", 40),
            analyst_workers=cfg["analyst_workers"],
            failure_only=cfg["failure_only"],
            minibatch_size=cfg["minibatch_size"],
            edit_budget=cfg["edit_budget"],
            task_retries=cfg.get("task_retries", 2),
            timeout_retries=cfg.get("timeout_retries"),
            codex_timeout_seconds=cfg.get("codex_timeout_seconds", 1200),
            max_codex_timeout_seconds=cfg.get("max_codex_timeout_seconds", 1200),
            model_context_window=cfg.get("model_context_window", 262144),
            seed=cfg["seed"],
        )
    return VeruSAGEAdapter(
        split_dir=cfg["split_dir"],
        verusage_src_root=cfg["verusage_src_root"],
        verus_bin=cfg["verus_bin"],
        lynette_bin=cfg["lynette_bin"],
        model=cfg["target_model"],
        workers=cfg.get("workers", 16),
        analyst_workers=cfg["analyst_workers"],
        failure_only=cfg["failure_only"],
        minibatch_size=cfg["minibatch_size"],
        edit_budget=cfg["edit_budget"],
        repair_attempts=cfg.get("repair_attempts", 20),
        request_cap=cfg.get("request_cap", 512),
        action_output_tokens=cfg.get("action_output_tokens", 32768),
        reasoning_output_tokens=cfg.get("reasoning_output_tokens", 32768),
        retry_action_output_tokens=cfg.get("retry_action_output_tokens", 262144),
        retry_reasoning_output_tokens=cfg.get("retry_reasoning_output_tokens", 262144),
        max_action_output_tokens=cfg.get("max_action_output_tokens", 384000),
        max_reasoning_output_tokens=cfg.get("max_reasoning_output_tokens", 384000),
        task_retries=cfg.get("task_retries", 2),
        request_timeout_seconds=cfg.get("request_timeout_seconds", 1800),
        task_timeout_seconds=cfg.get("task_timeout_seconds", 86400),
        budget_state_path=cfg.get("budget_state_path"),
        budget_approval_limit_usd=cfg.get("budget_approval_limit_usd", 20.0),
        budget_prior_spend_usd=cfg.get("budget_prior_spend_usd", 0.0),
        budget_optimizer_reserve_usd=cfg.get("budget_optimizer_reserve_usd", 1.0),
        budget_request_reserve_usd=cfg.get("budget_request_reserve_usd", 0.3),
        retrieval_cards_path=cfg.get("retrieval_cards_path"),
        seed=cfg["seed"],
    )


def _configure_deepseek(cfg: dict[str, Any]) -> None:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    from skillopt.model import configure_openai_compatible

    os.environ["OPENAI_COMPATIBLE_API_KEY"] = key
    os.environ["OPENAI_COMPATIBLE_BASE_URL"] = "https://api.deepseek.com"
    os.environ["OPENAI_COMPATIBLE_MAX_TOKENS"] = "32768"
    os.environ["OPENAI_COMPATIBLE_TIMEOUT_SECONDS"] = "600"
    configure_openai_compatible(
        base_url="https://api.deepseek.com",
        api_key=key,
        optimizer_model=cfg["optimizer_model"],
        target_model=cfg["target_model"],
        timeout_seconds=600,
        max_tokens=32768,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--cfg-options", nargs="*", default=[])
    args = parser.parse_args()
    structured = _expand(load_config(str(args.config), args.cfg_options))
    cfg = flatten_config(structured)
    adapter = _adapter(cfg)
    if args.check_only:
        adapter.setup(cfg)
        counts = {
            "train": len(adapter.dataloader.train_items),
            "val": len(adapter.dataloader.val_items),
            "test": len(adapter.dataloader.test_items),
        }
        print(json.dumps({"status": "ok", "counts": counts}, indent=2))
        return
    formal_epoch = bool(cfg.get("formal_epoch_contract", False))
    if formal_epoch:
        _validate_fresh_formal_run(cfg)
    if cfg.get("optimizer_backend") == "openai_compatible":
        _configure_deepseek(cfg)
    elif cfg.get("optimizer_backend") == "codex_exec":
        os.environ.pop("DEEPSEEK_API_KEY", None)
        os.environ["SKILLOPT_CODEX_BRIDGE_TOKEN"] = "local-bridge-only"
        os.environ["CODEX_WORKING_DIRECTORY"] = str(Path(cfg["out_root"]).resolve())
        _install_prompt_free_codex_ledger(
            Path(cfg["out_root"]) / "optimizer_calls.jsonl"
        )
    else:
        raise ValueError(
            f"unsupported optimizer backend: {cfg.get('optimizer_backend')}"
        )
    try:
        summary = ReflACTTrainer(cfg, adapter).train()
    except BaseException:
        if formal_epoch:
            _wait_for_bridge_drain(
                cfg["codex_bridge_url"],
                int(cfg["max_codex_timeout_seconds"]) + 180,
            )
            write_cost_ledger(Path(cfg["out_root"]))
        raise
    if formal_epoch:
        _wait_for_bridge_drain(
            cfg["codex_bridge_url"],
            int(cfg["max_codex_timeout_seconds"]) + 180,
        )
    summary["cost_ledger"] = write_cost_ledger(Path(cfg["out_root"]))
    if formal_epoch:
        summary["formal_epoch_validation"] = _validate_formal_epoch(
            cfg, summary, summary["cost_ledger"]
        )
        _write_json(Path(cfg["out_root"]) / "summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
