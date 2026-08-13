from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from skillopt.config import flatten_config, load_config
from skillopt.engine.trainer import ReflACTTrainer

from skillopt_verusage.adapter import VeruSAGEAdapter
from skillopt_verusage.cost_ledger import write_cost_ledger


ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


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
        retry_reasoning_output_tokens=cfg.get(
            "retry_reasoning_output_tokens", 262144
        ),
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
    _configure_deepseek(cfg)
    summary = ReflACTTrainer(cfg, adapter).train()
    summary["cost_ledger"] = write_cost_ledger(Path(cfg["out_root"]))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
