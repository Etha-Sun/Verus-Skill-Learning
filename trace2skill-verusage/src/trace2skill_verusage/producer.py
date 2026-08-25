"""Reproducible Trace2Skill native MAP/REDUCE producer for Verus records."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "trace2skill-verus-producer-v1"
SOURCE_SNAPSHOT_COMMIT = "92a1e8ab55d79b0831f251bbd9b9e61e1562bc9e"
SOURCE_SNAPSHOT_PATH = "trace2skill_verusage_baseline_test/code"
VERUS_RUNTIME_TREE_SHA256 = (
    "8a80dd6a9fbf8298310a3a241697bd8098bc0e3a6e228d13c402139aa3301a9e"
)
OFFICIAL_RECORDS_SHA256 = (
    "4151b9c4ca39ca98628f33bc0355a7f49d509e28a18258482d66f935733d8466"
)
OFFICIAL_NEUTRAL_SEED_SHA256 = (
    "f67322cd47bc25f993f92788767b58047c11a6863d0d7a6ba987f5dff163d7a2"
)
WORKSTREAM_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_ROOT = WORKSTREAM_ROOT / "vendor" / "trace2skill_verus"
DEFAULT_SEED_DIR = (
    WORKSTREAM_ROOT / "producer" / "neutral-seed" / "verus-proof-repair"
)
DEFAULT_VALIDATOR = WORKSTREAM_ROOT / "tools" / "quick_validate.py"
PROMPT_PATHS = {
    "map": (
        "skill_evolver/prompts/skill_evolving_agent/system_prompt_base.txt",
        "4bdafecb8340e6023517dda14c8de5da669ab8b20ef10f09beac9f8f77d436ca",
    ),
    "merge": (
        "skill_evolver/prompts/success_evolving_agent/combined_merge_system_prompt.txt",
        "c9b707e3dafacd96536c92fe43b78507d3b20e6b6d1552d67e61d3b5377e706f",
    ),
    "translation": (
        "skill_evolver/prompts/parallel_evolving_agent/translation_system_prompt.txt",
        "3870a22f3cd2ff066220393f6e991c7c2858c0f67e1e90601408920b4084802e",
    ),
    "verification": (
        "skill_evolver/prompts/parallel_evolving_agent/verification_system_prompt.txt",
        "bb925b81873aed35af89bc9a1116ec5e70f4a1eb01371db91023e0115e9ad91a",
    ),
}
EXCLUDED_EXPERIMENT_PATHS = (
    "react_agent",
    "skill_evolver/semantic_reduce_evolving_agent.py",
    "skill_evolver/prompts/semantic_reduce_evolving_agent",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def hash_skill_tree(skill_dir: Path) -> str:
    root = skill_dir.resolve()
    if not root.is_dir():
        raise ValueError(f"skill directory does not exist: {root}")
    entries = sorted(root.rglob("*"))
    symlinks = [path for path in entries if path.is_symlink()]
    if symlinks:
        raise ValueError(f"skill directory must not contain symlinks: {symlinks[0]}")
    digest = hashlib.sha256()
    for path in (item for item in entries if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def load_records(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    resolved = path.resolve()
    raw = resolved.read_bytes()
    digest = sha256_bytes(raw)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError(
            f"records hash mismatch: expected {expected_sha256}, got {digest}"
        )
    payload = json.loads(raw)
    if not isinstance(payload, list) or not payload:
        raise ValueError("records must be a non-empty JSON array")

    records: list[dict[str, Any]] = []
    instance_ids: list[str] = []
    item_count = 0
    sources: Counter[str] = Counter()
    for index, value in enumerate(payload):
        if not isinstance(value, dict):
            raise ValueError(f"record {index} must be an object")
        source = value.get("record_source")
        instance_id = value.get("instance_id")
        items = value.get("items")
        if source not in {"error", "success"}:
            raise ValueError(f"record {index} has invalid record_source")
        if not isinstance(instance_id, str) or not instance_id:
            raise ValueError(f"record {index} has invalid instance_id")
        if not isinstance(items, list) or not items:
            raise ValueError(f"record {index} must contain memory items")
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"record {index} item {item_index} must be an object")
            for field in ("type", "description", "content"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ValueError(
                        f"record {index} item {item_index} has invalid {field}"
                    )
        records.append(value)
        instance_ids.append(instance_id)
        item_count += len(items)
        sources[source] += 1
    if len(instance_ids) != len(set(instance_ids)):
        raise ValueError("record instance_id values must be unique")
    return records, {
        "path": str(resolved),
        "sha256": digest,
        "record_count": len(records),
        "error_record_count": sources["error"],
        "success_record_count": sources["success"],
        "item_count": item_count,
    }


def require_output_below_run_root(output_dir: Path, run_root: Path) -> Path:
    root = run_root.resolve()
    output = output_dir.resolve()
    if output == root or root not in output.parents:
        raise ValueError(f"output must be below VERUS_SKILL_RUN_ROOT: {output}")
    return output


def verify_runtime(
    runtime_root: Path,
    seed_dir: Path,
    validator: Path,
) -> dict[str, Any]:
    runtime = runtime_root.resolve()
    required = (
        "skill_evolver/model_clients.py",
        "skill_evolver/parallel_evolving_agent.py",
        "skill_evolver/parallel_success_evolving_agent.py",
        "skill_evolver/run_parallel_combined_skill_evolution.py",
    )
    for relative in required:
        if not (runtime / relative).is_file():
            raise ValueError(f"vendored Verus Trace2Skill runtime is missing: {relative}")
    for relative in EXCLUDED_EXPERIMENT_PATHS:
        if (runtime / relative).exists():
            raise ValueError(f"excluded experimental Trace2Skill path is present: {relative}")
    runtime_hash = hash_skill_tree(runtime)
    if runtime_hash != VERUS_RUNTIME_TREE_SHA256:
        raise ValueError(f"vendored Verus Trace2Skill runtime hash mismatch: {runtime_hash}")
    if not validator.resolve().is_file():
        raise ValueError(f"skill validator is missing: {validator.resolve()}")
    seed_hash = hash_skill_tree(seed_dir)
    if seed_hash != OFFICIAL_NEUTRAL_SEED_SHA256:
        raise ValueError(f"neutral seed hash mismatch: {seed_hash}")
    prompt_hashes: dict[str, str] = {}
    for name, (relative, expected) in PROMPT_PATHS.items():
        actual = sha256_file(runtime / relative)
        if actual != expected:
            raise ValueError(f"{name} prompt hash mismatch: {actual}")
        prompt_hashes[name] = actual
    return {
        "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT,
        "source_snapshot_path": SOURCE_SNAPSHOT_PATH,
        "runtime_tree_sha256": runtime_hash,
        "excluded_experiment_paths": list(EXCLUDED_EXPERIMENT_PATHS),
        "neutral_seed_sha256": seed_hash,
        "prompt_sha256": prompt_hashes,
        "validator": str(validator.resolve()),
    }


def build_runtime_command(
    *,
    runtime_root: Path,
    error_json: Path,
    success_json: Path,
    working_skill: Path,
    output_skill: Path,
    run_dir: Path,
    model: str,
) -> list[str]:
    return [
        os.environ.get("TRACE2SKILL_PYTHON_BIN", "python3"),
        "-m",
        "skill_evolver.run_parallel_combined_skill_evolution",
        "--error-json",
        str(error_json),
        "--success-json",
        str(success_json),
        "--skill-dir",
        str(working_skill),
        "--model",
        model,
        "--cache-path",
        str(run_dir / "cache"),
        "--batch-size",
        "1",
        "--merge-batch-size",
        "5",
        "--max-workers",
        "4",
        "--max-merge-levels",
        "5",
        "--temperature",
        "0.6",
        "--max-skill-lines",
        "500",
        "--output-dir",
        str(output_skill),
        "--save-intermediates",
        "--intermediates-dir",
        str(run_dir / "intermediates"),
        "--parse-failure-dir",
        str(run_dir / "parse_failures"),
        "--changelog",
        str(run_dir / "change.log"),
        "--patch-file",
        str(run_dir / "cumulative.patch"),
        "--input-mode",
        "records",
        "--patch-pipeline",
        "json",
        "--semantic-item-marker-format",
        "bracket",
    ]


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def preflight(
    *,
    records_path: Path,
    output_dir: Path,
    run_root: Path,
    runtime_root: Path,
    seed_dir: Path,
    validator: Path,
    expected_records_sha256: str | None,
    model: str,
    base_url: str | None,
    api_key_env: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records, records_manifest = load_records(
        records_path,
        expected_sha256=expected_records_sha256,
    )
    output = require_output_below_run_root(output_dir, run_root)
    runtime = verify_runtime(runtime_root, seed_dir, validator)
    check = {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "network_requests": 0,
        "output_dir": str(output),
        "records": records_manifest,
        "runtime": runtime,
        "configuration": {
            "model": model,
            "base_url_configured": bool(base_url),
            "api_key_env": api_key_env,
            "api_key_configured": bool(os.environ.get(api_key_env)),
            "batch_size": 1,
            "merge_batch_size": 5,
            "max_workers": 4,
            "max_merge_levels": 5,
            "temperature": 0.6,
            "max_tokens": None,
            "seed": None,
            "max_skill_lines": 500,
            "max_references": 5,
            "max_verification_rounds": 3,
            "patch_pipeline": "json",
            "semantic_item_marker_format": "bracket",
            "skip_translation": False,
            "enable_json_format_self_fix": True,
            "reduce_strategy": "global",
        },
    }
    return records, check


def validate_final_skill(validator: Path, skill_dir: Path) -> dict[str, Any]:
    """Run the repository validator and return a manifest-safe result."""
    try:
        result = subprocess.run(
            [sys.executable, str(validator.resolve()), str(skill_dir.resolve())],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "returncode": None,
            "message": "validation timed out",
        }
    except OSError as exc:
        return {
            "status": "failed",
            "returncode": None,
            "message": f"validation error: {exc}",
        }

    message = result.stdout.strip() or result.stderr.strip()
    return {
        "status": "passed" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "message": message,
    }


def execute(
    *,
    records: list[dict[str, Any]],
    check: dict[str, Any],
    output_dir: Path,
    runtime_root: Path,
    seed_dir: Path,
    validator: Path,
    model: str,
    base_url: str | None,
    api_key_env: str,
) -> dict[str, Any]:
    api_key = os.environ.get(api_key_env, "")
    if not api_key:
        raise ValueError(f"{api_key_env} is required for producer execution")
    if not base_url:
        raise ValueError("an OpenAI-compatible base URL is required for execution")
    run_dir = output_dir.resolve()
    if run_dir.exists():
        raise FileExistsError(f"producer output already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    inputs_dir = run_dir / "inputs"
    inputs_dir.mkdir()
    error_json = inputs_dir / "error_records.json"
    success_json = inputs_dir / "success_records.json"
    error_json.write_text(
        json.dumps(
            [row for row in records if row["record_source"] == "error"],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    success_json.write_text(
        json.dumps(
            [row for row in records if row["record_source"] == "success"],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    working_skill = run_dir / "working_skill" / "verus-proof-repair"
    working_skill.parent.mkdir()
    shutil.copytree(seed_dir, working_skill)
    output_skill = run_dir / "final_skill" / "verus-proof-repair"
    output_skill.parent.mkdir()
    command = build_runtime_command(
        runtime_root=runtime_root,
        error_json=error_json,
        success_json=success_json,
        working_skill=working_skill,
        output_skill=output_skill,
        run_dir=run_dir,
        model=model,
    )
    manifest = {
        **check,
        "status": "running",
        "started_at": utc_now(),
        "records": {
            **{
                key: value
                for key, value in check["records"].items()
                if key != "path"
            },
            "error_records_path": "inputs/error_records.json",
            "success_records_path": "inputs/success_records.json",
        },
        "execution": {
            "module": "skill_evolver.run_parallel_combined_skill_evolution",
            "credentials_recorded": False,
            "stdout_log": "producer.log",
        },
    }
    write_json(run_dir / "run_manifest.json", manifest)

    env = os.environ.copy()
    python_paths = [str(runtime_root.resolve())]
    if env.get("PYTHONPATH"):
        python_paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    env["OPENAI_API_KEY"] = api_key
    env["OPENAI_BASE_URL"] = base_url
    env["TRACE2SKILL_QUICK_VALIDATE_SCRIPT"] = str(validator.resolve())
    with (run_dir / "producer.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command,
            cwd=run_dir,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
    manifest["returncode"] = result.returncode
    if result.returncode != 0:
        manifest["finished_at"] = utc_now()
        manifest["status"] = "failed"
        write_json(run_dir / "run_manifest.json", manifest)
        raise RuntimeError(
            f"Trace2Skill producer failed; inspect {run_dir / 'producer.log'}"
        )

    final_validation = validate_final_skill(validator, output_skill)
    manifest["final_validation"] = final_validation
    if final_validation["status"] != "passed":
        manifest["finished_at"] = utc_now()
        manifest["status"] = "failed"
        write_json(run_dir / "run_manifest.json", manifest)
        raise RuntimeError(
            "Trace2Skill producer returned an invalid final skill; "
            f"inspect {run_dir / 'run_manifest.json'}"
        )

    final_hash = hash_skill_tree(output_skill)
    manifest["finished_at"] = utc_now()
    manifest["status"] = "complete"
    manifest["final_skill"] = {
        "path": "final_skill/verus-proof-repair",
        "skill_tree_sha256": final_hash,
    }
    write_json(run_dir / "run_manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--seed-dir", type=Path, default=DEFAULT_SEED_DIR)
    parser.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--expected-records-sha256", default=None)
    parser.add_argument("--check-only", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    records, check = preflight(
        records_path=args.records,
        output_dir=args.output_dir,
        run_root=args.run_root,
        runtime_root=args.runtime_root,
        seed_dir=args.seed_dir,
        validator=args.validator,
        expected_records_sha256=args.expected_records_sha256,
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
    )
    if args.check_only:
        print(json.dumps(check, ensure_ascii=False, indent=2))
        return
    manifest = execute(
        records=records,
        check=check,
        output_dir=args.output_dir,
        runtime_root=args.runtime_root,
        seed_dir=args.seed_dir,
        validator=args.validator,
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
