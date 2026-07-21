from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


ENV_DATA_ROOT = "VERUS_SKILL_DATA_ROOT"
ENV_RUN_ROOT = "VERUS_SKILL_RUN_ROOT"
ENV_LAYOUT = "VERUS_SKILL_DATA_LAYOUT"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
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


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _run_root_issues(run_root: Path, data_root: Path | None = None) -> list[str]:
    issues = []
    if not run_root.is_dir():
        issues.append("run root must be an existing directory")
    elif not os.access(run_root, os.W_OK | os.X_OK):
        issues.append("run root must be writable")
    if _paths_overlap(run_root, REPOSITORY_ROOT):
        issues.append("run root must be outside the repository")
    if data_root is not None and _paths_overlap(run_root, data_root):
        issues.append("run root must not overlap data root")
    return issues


def validate_output_path(
    output_path: Path | str,
    *,
    run_root: Path | None = None,
    data_root: Path | None = None,
) -> Path:
    """Resolve an experiment output and require it to stay under the run root."""
    configured_run_root = _configured_path(run_root, ENV_RUN_ROOT)
    configured_data_root = data_root
    if configured_data_root is None and os.environ.get(ENV_DATA_ROOT):
        configured_data_root = Path(os.environ[ENV_DATA_ROOT])
    if configured_data_root is not None:
        configured_data_root = configured_data_root.expanduser().resolve()
    issues = _run_root_issues(configured_run_root, configured_data_root)
    if issues:
        raise ValueError("; ".join(issues))

    output = Path(output_path).expanduser().resolve()
    if output != configured_run_root and configured_run_root not in output.parents:
        raise ValueError(f"output path must be inside {ENV_RUN_ROOT}")
    return output


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
    issues = []
    if missing:
        issues.append("required data directories are missing")
    if _paths_overlap(data_root, run_root):
        issues.append("data and run roots must not overlap")
    issues.extend(_run_root_issues(run_root))
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
        "run_root_exists": run_root.is_dir(),
        "run_root_writable": run_root.is_dir()
        and os.access(run_root, os.W_OK | os.X_OK),
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
