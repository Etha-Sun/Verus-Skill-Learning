from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


ENV_DATA_ROOT = "VERUS_SKILL_DATA_ROOT"
ENV_RUN_ROOT = "VERUS_SKILL_RUN_ROOT"
ENV_LAYOUT = "VERUS_SKILL_DATA_LAYOUT"
LAYOUTS = ("versioned", "legacy")
BATCH_DIRECTORIES = (
    "all_batch_results-cyy-claude",
    "all_batch_results-cyy-claude-s4",
    "all_batch_results-cyy-gpt5",
    "all_batch_results-cyy-o4mini",
)
HANDSOFF_DIRECTORIES = (
    "verified-anvil",
    "verified-atmo",
    "verified-ironkv",
    "verified-memory-allocator",
    "verified-node-replication",
    "verified-nrkernel",
    "verified-storage",
    "verified-vest",
)
SEALED_DIRECTORIES = (
    "verified-memory-allocator",
    "verified-nrkernel",
)


def _configured_path(explicit: Path | None, env_name: str) -> Path:
    value = explicit or (
        Path(os.environ[env_name]) if os.environ.get(env_name) else None
    )
    if value is None:
        raise ValueError(f"set {env_name} or pass the corresponding command-line path")
    return value.expanduser().resolve()


def dataset_paths(data_root: Path, layout: str) -> dict[str, Path]:
    if layout == "versioned":
        return {
            "verusage": data_root / "verusage-batch-v1",
            "handsoff": data_root / "handsoff-v1",
            "eval": data_root / "eval",
        }
    if layout == "legacy":
        return {
            "verusage": data_root,
            "handsoff": data_root / "claude_sonnet_gpt5",
            "eval": data_root / "eval",
        }
    raise ValueError(f"unknown data layout: {layout}")


def selected_dataset_path(
    dataset: str,
    data_root: Path | None = None,
    layout: str | None = None,
) -> Path:
    """Resolve one dataset from the source selected in the local environment."""
    data_root = _configured_path(data_root, ENV_DATA_ROOT)
    layout = layout or os.environ.get(ENV_LAYOUT, "versioned")
    paths = dataset_paths(data_root, layout)
    if dataset not in paths:
        choices = ", ".join(sorted(paths))
        raise ValueError(f"unknown dataset: {dataset}; choose one of: {choices}")
    return paths[dataset]


def inspect_layout(
    data_root: Path | None = None,
    run_root: Path | None = None,
    layout: str | None = None,
) -> dict[str, Any]:
    data_root = _configured_path(data_root, ENV_DATA_ROOT)
    run_root = _configured_path(run_root, ENV_RUN_ROOT)
    layout = layout or os.environ.get(ENV_LAYOUT, "versioned")
    paths = dataset_paths(data_root, layout)
    required = [
        data_root,
        *(paths["verusage"] / name for name in BATCH_DIRECTORIES),
        *(paths["handsoff"] / name for name in HANDSOFF_DIRECTORIES),
    ]
    missing = [str(path) for path in required if not path.is_dir()]
    overlap = (
        data_root == run_root
        or data_root in run_root.parents
        or run_root in data_root.parents
    )
    issues = []
    if missing:
        issues.append("required data directories are missing")
    if overlap:
        issues.append("data and run roots must not overlap")
    return {
        "ok": not issues,
        "layout": layout,
        "data_root": str(data_root),
        "run_root": str(run_root),
        "verusage_root": str(paths["verusage"]),
        "handsoff_root": str(paths["handsoff"]),
        "eval_root": str(paths["eval"]),
        "sealed_directories": list(SEALED_DIRECTORIES),
        "raw_data_read_only": True,
        "missing_directories": missing,
        "issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="verus-skill-data-layout")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--layout", choices=LAYOUTS)
    args = parser.parse_args()
    try:
        report = inspect_layout(args.data_root, args.run_root, args.layout)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
