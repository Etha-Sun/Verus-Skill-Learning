#!/usr/bin/env python3
"""Extract one frozen outcome-aware memory set from shared train trajectories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from global_skill_experiment.memories import credential_audit, load_config, run


HERE = Path(__file__).resolve().parent
DEFAULT_PROMPTS = HERE.parent / "prompts" / "shared_memory"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--run-name", default="cross-task-global-20260814")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--prompt-root", type=Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-new", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_root = args.run_root.resolve()
    experiment_root = run_root / args.run_name
    materialized_root = experiment_root / "shared_train_input"
    output_root = experiment_root / "shared_memories"
    config, secret = load_config(
        args.env_file.resolve(),
        args.model,
        args.base_url,
        args.temperature,
        args.max_tokens,
        args.timeout,
        args.workers,
    )
    try:
        result = run(
            materialized_root,
            output_root,
            run_root,
            args.prompt_root.resolve(),
            config,
            secret,
            args.resume,
            args.max_new,
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("valid") == 40 and not result.get("invalid") else 2
    finally:
        if output_root.exists():
            audit = credential_audit(output_root, secret)
            if not audit["credential_value_absent"]:
                raise RuntimeError("credential leakage audit failed")


if __name__ == "__main__":
    raise SystemExit(main())
