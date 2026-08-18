#!/usr/bin/env python3
"""Shared CLI implementation for the two M-core-seeded REDUCE branches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from global_skill_experiment.construction import (  # noqa: E402
    execute_native,
    execute_semantic,
    load_shared_records,
    make_client,
    make_evolver,
    preflight,
)


def build_parser(method: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"M-core-seeded {method} construction (no actor/gate calls)."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--m-core", type=Path, required=True)
    parser.add_argument("--memories", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--shared-map-dir", type=Path)
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--base-url")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--cache-path", type=Path)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--merge-batch-size", type=int, default=5)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--max-merge-levels", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--result-json", type=Path)
    return parser


def main(method: str) -> int:
    parser = build_parser(method)
    args = parser.parse_args()
    for name in ("batch_size", "merge_batch_size", "max_workers", "max_merge_levels"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if method == "semantic-reduce" and args.shared_map_dir is None:
        parser.error("semantic-reduce requires --shared-map-dir")
    if args.preflight:
        result = preflight(
            method=method,
            m_core=args.m_core,
            memories=args.memories,
            batch_size=args.batch_size,
            merge_batch_size=args.merge_batch_size,
            max_merge_levels=args.max_merge_levels,
            shared_map_dir=args.shared_map_dir,
        )
        result.update(
            {
                "model": args.model,
                "batch_size": args.batch_size,
                "merge_batch_size": args.merge_batch_size,
                "max_workers": args.max_workers,
                "max_merge_levels": args.max_merge_levels,
                "temperature": args.temperature,
                "max_tokens": args.max_tokens,
                "seed": args.seed,
                "actor_calls": 0,
                "gate_calls": 0,
            }
        )
        if method == "semantic-reduce":
            result["router_thinking"] = "disabled"
    else:
        if args.output is None:
            parser.error("--execute requires --output")
        generation_config = {}
        if args.seed is not None:
            generation_config["seed"] = args.seed
        client = make_client(
            model=args.model,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            cache_path=args.cache_path,
            generation_config=generation_config,
        )
        evolver = make_evolver(
            semantic=method == "semantic-reduce",
            client=client,
            m_core=args.m_core,
            output_dir=args.output,
            batch_size=args.batch_size,
            merge_batch_size=args.merge_batch_size,
            max_workers=args.max_workers,
            max_merge_levels=args.max_merge_levels,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        if method == "native-compressed":
            result = execute_native(
                evolver=evolver,
                records=load_shared_records(args.memories),
                output_dir=args.output,
                batch_size=args.batch_size,
            )
        else:
            result = execute_semantic(
                evolver=evolver,
                shared_map_dir=args.shared_map_dir,
                output_dir=args.output,
            )
        result.update(
            {
                "model": args.model,
                "base_url": args.base_url,
                "batch_size": args.batch_size,
                "merge_batch_size": args.merge_batch_size,
                "max_workers": args.max_workers,
                "max_merge_levels": args.max_merge_levels,
                "temperature": args.temperature,
                "max_tokens": args.max_tokens,
                "seed": args.seed,
                "actor_calls": 0,
                "gate_calls": 0,
            }
        )
        if method == "semantic-reduce":
            result["router_thinking"] = "disabled"
        default_result = args.output / "construction_result.json"
        default_result.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.result_json:
        args.result_json.parent.mkdir(parents=True, exist_ok=True)
        args.result_json.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0
