#!/usr/bin/env python3
"""Materialize the exact frozen 40-task train list from local Claude artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from global_skill_experiment.shared_train import materialize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-items", type=Path, required=True)
    parser.add_argument("--claude-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--run-name", default="cross-task-global-20260814")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output = args.run_root.resolve() / args.run_name / "shared_train_input"
    manifest = materialize(
        args.train_items, args.claude_root, args.run_root, output
    )
    print(json.dumps({"output": str(output), **manifest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
