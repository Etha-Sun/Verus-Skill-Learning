from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .data_layout import selected_dataset_path, validate_output_path
from .handsoff_harness import (
    build_prompt,
    configured_tool_path,
    resolve_tool_path,
    run_harness,
    verus_succeeded,
)
from .handsoff_m0 import _code_shingles, _jaccard, normalized_code_sha256, sha256_file


TRAIN_DIRECTORIES = ("verified-anvil", "verified-ironkv")
SEALED_DIRECTORIES = {"verified-memory-allocator", "verified-nrkernel"}
SIZE_BINS = ("small", "medium", "large")
TIERS = ("pass", "near_miss", "stalled")
VERUS_SUMMARY_RE = re.compile(
    r"verification results::\s*(\d+) verified,\s*(\d+) errors?", re.IGNORECASE
)
CONTEXT_FAILURE_RE = re.compile(
    r"context.{0,40}(?:exhaust|limit|length|window)|"
    r"(?:maximum|max).{0,20}(?:context|token)",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _require_empty_output(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"output directory must be empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _resolve_within(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    allowed = root.resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError(f"path escapes allowed root {allowed}: {resolved}")
    return resolved


def _safe_task_id(task_id: Any) -> str:
    if not isinstance(task_id, str) or not task_id or Path(task_id).name != task_id:
        raise ValueError(f"unsafe task id: {task_id!r}")
    if task_id in {".", ".."} or "/" in task_id or "\\" in task_id:
        raise ValueError(f"unsafe task id: {task_id!r}")
    return task_id


def parse_verus_diagnostics(text: str) -> dict[str, Any]:
    matches = VERUS_SUMMARY_RE.findall(text)
    if not matches:
        return {"summary_found": False, "verified_count": None, "error_count": None}
    verified, errors = matches[-1]
    return {
        "summary_found": True,
        "verified_count": int(verified),
        "error_count": int(errors),
    }


def _manifest_artifact(
    corpus_root: Path, row: dict[str, Any], kind: str
) -> tuple[Path, dict[str, Any]]:
    directory = row.get("directory_group")
    if directory not in TRAIN_DIRECTORIES:
        raise ValueError(f"forbidden directory group: {directory}")
    metadata = row.get(kind) or {}
    log_path = corpus_root / str(row["relative_log_path"])
    if kind == "source":
        path = log_path.with_suffix(".rs")
    elif kind == "verified":
        path = log_path.with_name(f"{log_path.stem}_verified.rs")
    else:
        raise ValueError(f"unknown artifact kind: {kind}")
    path = _resolve_within(path, corpus_root / directory)
    if not path.is_file():
        raise ValueError(f"missing {kind} artifact: {path}")
    expected_sha = metadata.get("sha256")
    expected_normalized = metadata.get("normalized_code_sha256")
    if not expected_sha or sha256_file(path) != expected_sha:
        raise ValueError(f"stale {kind} SHA-256 metadata: {path}")
    text = path.read_text(errors="replace")
    if not expected_normalized or normalized_code_sha256(text) != expected_normalized:
        raise ValueError(f"stale {kind} normalized SHA-256 metadata: {path}")
    return path, metadata


def _canonical_source(corpus_root: Path, row: dict[str, Any]) -> tuple[Path, str, str]:
    directory = row["directory_group"]
    task_id = _safe_task_id(row.get("task_id"))
    path = _resolve_within(
        corpus_root / directory / "unverified" / f"{task_id}.rs",
        corpus_root / directory / "unverified",
    )
    if not path.is_file():
        raise ValueError(f"missing canonical unverified source: {path}")
    text = path.read_text(errors="replace")
    return path, sha256_file(path), normalized_code_sha256(text)


def _standard_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter[str]]:
    counts: Counter[str] = Counter()
    by_task: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        directory = row.get("directory_group")
        if directory in SEALED_DIRECTORIES:
            counts["sealed_metadata_rejected"] += 1
            continue
        if (
            row.get("split") != "train"
            or directory not in TRAIN_DIRECTORIES
            or row.get("variant") != "standard"
        ):
            counts["not_standard_allowed_train"] += 1
            continue
        if not all(
            (row.get(kind) or {}).get(field)
            for kind in ("source", "verified")
            for field in ("sha256", "normalized_code_sha256")
        ):
            counts["missing_source_or_verified_metadata"] += 1
            continue
        task_id = _safe_task_id(row.get("task_id"))
        key = (directory, task_id)
        existing = by_task.get(key)
        if existing is None or str(row["trace_id"]) < str(existing["trace_id"]):
            by_task[key] = row
    valid_standard_count = sum(
        1
        for row in rows
        if row.get("split") == "train"
        and row.get("directory_group") in TRAIN_DIRECTORIES
        and row.get("variant") == "standard"
        and all(
            (row.get(kind) or {}).get(field)
            for kind in ("source", "verified")
            for field in ("sha256", "normalized_code_sha256")
        )
    )
    counts["duplicate_standard_trace"] = valid_standard_count - len(by_task)
    return list(by_task.values()), counts


def _size_bins(rows: list[dict[str, Any]]) -> dict[str, str]:
    ordered = sorted(
        rows,
        key=lambda row: (
            row["canonical_source_size_bytes"],
            row["normalized_task_id"],
        ),
    )
    return {
        row["candidate_id"]: SIZE_BINS[min(2, index * 3 // len(ordered))]
        for index, row in enumerate(ordered)
    }


def _stable_key(row: dict[str, Any]) -> str:
    return _sha256_text(
        f"{row['directory_group']}::{row['normalized_task_id']}::"
        f"{row['canonical_source_normalized_sha256']}"
    )


def _verified_candidate_rows(
    rows: list[dict[str, Any]], corpus_root: Path
) -> tuple[list[dict[str, Any]], Counter[str]]:
    standard, counts = _standard_rows(rows)
    candidates: list[dict[str, Any]] = []
    for row in standard:
        try:
            trace_source, _ = _manifest_artifact(corpus_root, row, "source")
            verified, verified_metadata = _manifest_artifact(corpus_root, row, "verified")
            source, source_sha, source_normalized = _canonical_source(corpus_root, row)
        except ValueError as error:
            message = str(error)
            if "missing canonical" in message:
                counts["missing_canonical_source"] += 1
                continue
            raise
        candidate_id = _sha256_text(
            f"{row['directory_group']}::{row['normalized_task_id']}::{source_normalized}"
        )[:20]
        candidates.append(
            {
                "candidate_id": candidate_id,
                "directory_group": row["directory_group"],
                "task_id": row["task_id"],
                "normalized_task_id": row["normalized_task_id"],
                "standard_trace_id": row["trace_id"],
                "standard_trace_source": str(trace_source.relative_to(corpus_root)),
                "canonical_source_path": str(source.relative_to(corpus_root)),
                "canonical_source_sha256": source_sha,
                "canonical_source_normalized_sha256": source_normalized,
                "canonical_source_size_bytes": source.stat().st_size,
                "paired_verified_path": str(verified.relative_to(corpus_root)),
                "paired_verified_sha256": verified_metadata["sha256"],
                "paired_verified_normalized_sha256": verified_metadata[
                    "normalized_code_sha256"
                ],
            }
        )
    return candidates, counts


def _r040_exclusions(
    excluded_rows: list[dict[str, Any]], corpus_root: Path
) -> tuple[set[str], set[str], list[tuple[str, set[str]]]]:
    tasks: set[str] = set()
    hashes: set[str] = set()
    shingles: list[tuple[str, set[str]]] = []
    for row in excluded_rows:
        if row.get("directory_group") not in TRAIN_DIRECTORIES:
            raise ValueError("R040 selection contains a forbidden directory")
        source, metadata = _manifest_artifact(corpus_root, row, "source")
        text = source.read_text(errors="replace")
        tasks.add(str(row["normalized_task_id"]))
        hashes.add(str(metadata["normalized_code_sha256"]))
        shingles.append((str(row["normalized_task_id"]), _code_shingles(text)))
    return tasks, hashes, shingles


def select_calibration_tasks(
    rows: list[dict[str, Any]],
    excluded_rows: list[dict[str, Any]],
    corpus_root: Path,
    source_precheck: Callable[[Path, str], dict[str, Any]],
    paired_precheck: Callable[[Path, Path, str], dict[str, Any]],
    token_counter: Callable[[str], int],
    *,
    per_directory: int = 15,
    near_threshold: float = 0.90,
    max_model_len: int = 32768,
    context_reserve: int = 4096,
    base_prompt: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if per_directory % 3:
        raise ValueError("per_directory must be divisible by three size bins")
    corpus_root = corpus_root.resolve()
    candidates, rejection_counts = _verified_candidate_rows(rows, corpus_root)
    excluded_tasks, excluded_hashes, excluded_shingles = _r040_exclusions(
        excluded_rows, corpus_root
    )
    prompt = base_prompt or build_prompt()
    prompt_tokens = token_counter(prompt)
    eligible: list[dict[str, Any]] = []
    for row in candidates:
        if row["normalized_task_id"] in excluded_tasks:
            rejection_counts["r040_task_match"] += 1
            continue
        if row["canonical_source_normalized_sha256"] in excluded_hashes:
            rejection_counts["r040_source_match"] += 1
            continue
        source = corpus_root / row["canonical_source_path"]
        text = source.read_text(errors="replace")
        nearest_task, similarity = max(
            (
                (task_id, _jaccard(_code_shingles(text), reference))
                for task_id, reference in excluded_shingles
            ),
            key=lambda item: item[1],
            default=(None, 0.0),
        )
        if similarity >= near_threshold:
            rejection_counts["r040_near_match"] += 1
            continue
        source_tokens = token_counter(text)
        static_tokens = prompt_tokens + source_tokens
        if static_tokens > max_model_len - context_reserve:
            rejection_counts["context_ineligible"] += 1
            continue
        eligible.append(
            {
                **row,
                "base_prompt_sha256": _sha256_text(prompt),
                "base_prompt_tokens": prompt_tokens,
                "canonical_source_tokens": source_tokens,
                "static_context_tokens": static_tokens,
                "max_model_len": max_model_len,
                "context_reserve": context_reserve,
                "r040_nearest_task_id": nearest_task,
                "r040_max_jaccard_7gram": similarity,
            }
        )

    selected: list[dict[str, Any]] = []
    precheck_counts: Counter[str] = Counter()
    per_bin = per_directory // 3
    for directory in TRAIN_DIRECTORIES:
        directory_rows = [row for row in eligible if row["directory_group"] == directory]
        bins = _size_bins(directory_rows)
        for size_bin in SIZE_BINS:
            pool = sorted(
                [row for row in directory_rows if bins[row["candidate_id"]] == size_bin],
                key=_stable_key,
            )
            chosen = 0
            for row in pool:
                if row["canonical_source_normalized_sha256"] in {
                    item["canonical_source_normalized_sha256"] for item in selected
                }:
                    precheck_counts["duplicate_canonical_source"] += 1
                    continue
                source = corpus_root / row["canonical_source_path"]
                verified = corpus_root / row["paired_verified_path"]
                paired = paired_precheck(source, verified, row["candidate_id"])
                paired_verus = paired.get("verus") or {}
                paired_lynette = paired.get("lynette") or {}
                if paired_verus.get("timed_out") or paired_lynette.get("timed_out"):
                    precheck_counts["paired_precheck_timeout"] += 1
                    continue
                if not paired_verus.get("passed"):
                    precheck_counts["paired_verified_verus_failure"] += 1
                    continue
                if not paired_lynette.get("passed"):
                    precheck_counts["paired_verified_lynette_failure"] += 1
                    continue
                result = source_precheck(source, row["candidate_id"])
                diagnostics = result.get("diagnostics") or {}
                if result.get("timed_out"):
                    precheck_counts["source_precheck_timeout"] += 1
                    continue
                if not result.get("checked") or not diagnostics.get("summary_found"):
                    precheck_counts["source_precheck_unavailable"] += 1
                    continue
                if result.get("passed") or diagnostics.get("error_count") == 0:
                    precheck_counts["source_precheck_already_passed"] += 1
                    continue
                selected.append(
                    {
                        **row,
                        "calibration_id": row["candidate_id"],
                        "source_size_bin": size_bin,
                        "source_precheck": result,
                        "paired_verified_precheck": paired,
                    }
                )
                chosen += 1
                if chosen == per_bin:
                    break
            if chosen != per_bin:
                raise ValueError(
                    f"insufficient eligible tasks for {directory}/{size_bin}: "
                    f"needed {per_bin}, selected {chosen}"
                )
    selected.sort(
        key=lambda row: (
            TRAIN_DIRECTORIES.index(row["directory_group"]),
            SIZE_BINS.index(row["source_size_bin"]),
            _stable_key(row),
        )
    )
    for rank, row in enumerate(selected, start=1):
        row["selection_rank"] = rank
    expected = per_directory * len(TRAIN_DIRECTORIES)
    task_count = len({row["normalized_task_id"] for row in selected})
    source_count = len({row["canonical_source_normalized_sha256"] for row in selected})
    if len(selected) != expected or task_count != expected or source_count != expected:
        raise ValueError("selection uniqueness/count gate failed")
    audit = {
        "candidate_count_after_physical_audit": len(candidates),
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "precheck_counts": dict(sorted(precheck_counts.items())),
        "near_threshold": near_threshold,
        "selected_exact_task_overlap": sum(
            row["normalized_task_id"] in excluded_tasks for row in selected
        ),
        "selected_exact_source_overlap": sum(
            row["canonical_source_normalized_sha256"] in excluded_hashes
            for row in selected
        ),
        "selected_near_overlap": sum(
            row["r040_max_jaccard_7gram"] >= near_threshold for row in selected
        ),
        "sealed_content_reads": 0,
        "max_model_len": max_model_len,
        "context_reserve": context_reserve,
        "base_prompt_tokens": prompt_tokens,
    }
    if any(
        audit[key]
        for key in (
            "selected_exact_task_overlap",
            "selected_exact_source_overlap",
            "selected_near_overlap",
        )
    ):
        raise ValueError("selection leakage gate failed")
    return selected, audit


def build_token_counter(tokenizer_path: Path) -> Callable[[str], int]:
    try:
        from transformers import AutoTokenizer
    except ImportError as error:
        raise RuntimeError("transformers is required for tokenizer-based selection") from error
    tokenizer = AutoTokenizer.from_pretrained(
        str(tokenizer_path.resolve()), local_files_only=True, trust_remote_code=True
    )

    def count(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=True))

    return count


def _run_source_precheck(
    verus_bin: Path, log_dir: Path, timeout_seconds: int
) -> Callable[[Path, str], dict[str, Any]]:
    def run(source: Path, calibration_id: str) -> dict[str, Any]:
        try:
            result = subprocess.run(
                [str(verus_bin), str(source)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            output = result.stdout + result.stderr
            returncode: int | None = result.returncode
            timed_out = False
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else error.stdout or ""
            stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr or ""
            output = stdout + stderr + f"\nTIMEOUT after {timeout_seconds}s\n"
            returncode = None
            timed_out = True
        (log_dir / f"{calibration_id}.log").write_text(output)
        return {
            "checked": returncode is not None,
            "passed": verus_succeeded(returncode, output),
            "returncode": returncode,
            "timed_out": timed_out,
            "diagnostics": parse_verus_diagnostics(output),
        }

    return run


def _run_paired_precheck(
    verus_bin: Path, lynette_bin: Path, log_dir: Path, timeout_seconds: int
) -> Callable[[Path, Path, str], dict[str, Any]]:
    def run(source: Path, verified: Path, calibration_id: str) -> dict[str, Any]:
        results: dict[str, Any] = {}
        commands = {
            "verus": [str(verus_bin), str(verified)],
            "lynette": [str(lynette_bin), "compare", "-t", str(source), str(verified)],
        }
        for tool, command in commands.items():
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                output = completed.stdout + completed.stderr
                returncode: int | None = completed.returncode
                timed_out = False
            except subprocess.TimeoutExpired as error:
                stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else error.stdout or ""
                stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr or ""
                output = stdout + stderr + f"\nTIMEOUT after {timeout_seconds}s\n"
                returncode = None
                timed_out = True
            (log_dir / f"{calibration_id}.{tool}.log").write_text(output)
            results[tool] = {
                "checked": returncode is not None,
                "passed": returncode == 0 and (
                    tool != "verus" or verus_succeeded(returncode, output)
                ),
                "returncode": returncode,
                "timed_out": timed_out,
                "diagnostics": parse_verus_diagnostics(output) if tool == "verus" else None,
            }
        return results

    return run


def write_selection(
    manifest: Path,
    r040_selection: Path,
    corpus_root: Path,
    out_dir: Path,
    verus_bin: Path,
    lynette_bin: Path,
    copilot_bin: Path,
    tokenizer_path: Path,
    *,
    per_directory: int = 15,
    near_threshold: float = 0.90,
    timeout_seconds: int = 120,
    max_model_len: int = 32768,
    context_reserve: int = 4096,
    model_alias: str = "qwen35-27b",
    inference_timeout_seconds: int = 1200,
) -> dict[str, Any]:
    _require_empty_output(out_dir)
    log_dir = out_dir / "source_precheck_logs"
    log_dir.mkdir()
    paired_log_dir = out_dir / "paired_verified_precheck_logs"
    paired_log_dir.mkdir()
    verus_bin = resolve_tool_path(verus_bin)
    lynette_bin = resolve_tool_path(lynette_bin)
    copilot_bin = resolve_tool_path(copilot_bin)
    selected, audit = select_calibration_tasks(
        _load_jsonl(manifest),
        _load_jsonl(r040_selection),
        corpus_root,
        _run_source_precheck(verus_bin, log_dir, timeout_seconds),
        _run_paired_precheck(verus_bin, lynette_bin, paired_log_dir, timeout_seconds),
        build_token_counter(tokenizer_path),
        per_directory=per_directory,
        near_threshold=near_threshold,
        max_model_len=max_model_len,
        context_reserve=context_reserve,
        base_prompt=build_prompt(
            verus_command=str(verus_bin), lynette_command=str(lynette_bin)
        ),
    )
    model_config = tokenizer_path / "config.json"
    if not model_config.is_file():
        raise ValueError(f"missing model config: {model_config}")
    model_config_sha256 = sha256_file(model_config)
    expected_tool_sha256 = {
        "copilot": sha256_file(copilot_bin),
        "verus": sha256_file(verus_bin),
        "lynette": sha256_file(lynette_bin),
    }
    for row in selected:
        row["expected_model_config_sha256"] = model_config_sha256
        row["expected_model_alias"] = model_alias
        row["expected_model_path"] = str(tokenizer_path.resolve())
        row["expected_timeout_seconds"] = inference_timeout_seconds
        row["expected_tool_sha256"] = expected_tool_sha256
    tasks_path = out_dir / "r040a_tasks.jsonl"
    _write_jsonl(tasks_path, selected)
    summary = {
        "created_at": _now(),
        "status": "DONE",
        "selection_count": len(selected),
        "directory_counts": dict(sorted(Counter(x["directory_group"] for x in selected).items())),
        "size_bin_counts": dict(sorted(Counter(x["source_size_bin"] for x in selected).items())),
        "unique_task_count": len({x["normalized_task_id"] for x in selected}),
        "unique_source_count": len({x["canonical_source_normalized_sha256"] for x in selected}),
        "selected_tasks_sha256": sha256_file(tasks_path),
        "raw_data_read_only": True,
        "method_evidence": False,
    }
    _write_json(out_dir / "r040a_selection_summary.json", summary)
    _write_json(out_dir / "r040a_leakage_report.json", {**audit, "verdict": "PASS"})
    tokenizer_files = {}
    for name in ("config.json", "tokenizer_config.json", "tokenizer.json"):
        path = tokenizer_path / name
        if path.is_file():
            tokenizer_files[name] = sha256_file(path)
    _write_json(
        out_dir / "run_manifest.json",
        {
            "created_at": _now(),
            "run_id": "R040A",
            "input_manifest": str(manifest.resolve()),
            "input_manifest_sha256": sha256_file(manifest),
            "r040_selection": str(r040_selection.resolve()),
            "r040_selection_sha256": sha256_file(r040_selection),
            "corpus_root": str(corpus_root.resolve()),
            "tokenizer_path": str(tokenizer_path.resolve()),
            "verus_bin": str(verus_bin),
            "lynette_bin": str(lynette_bin),
            "copilot_bin": str(copilot_bin),
            "expected_tool_sha256": expected_tool_sha256,
            "model_alias": model_alias,
            "inference_timeout_seconds": inference_timeout_seconds,
            "tokenizer_files": tokenizer_files,
            "max_model_len": max_model_len,
            "context_reserve": context_reserve,
            "raw_data_read_only": True,
            "sealed_content_reads": 0,
        },
    )
    return summary


def prepare_screen(
    tasks_path: Path, out_dir: Path, *, repetitions: tuple[int, ...] = (1,)
) -> dict[str, Any]:
    _require_empty_output(out_dir)
    tasks = _load_jsonl(tasks_path)
    jobs = []
    for task in tasks:
        for repetition in repetitions:
            jobs.append(
                {
                    "job_id": f"{task['calibration_id']}-rep{repetition}",
                    "calibration_id": task["calibration_id"],
                    "selection_rank": task["selection_rank"],
                    "repetition": repetition,
                    "condition": "h0",
                    "canonical_source_sha256": task["canonical_source_sha256"],
                    "base_prompt_sha256": task["base_prompt_sha256"],
                    "relative_source_path": task["canonical_source_path"],
                    "relative_run_path": f"runs/{task['calibration_id']}/rep_{repetition}/h0",
                    "status": "PENDING",
                }
            )
    path = out_dir / "r040b_screen_manifest.jsonl"
    _write_jsonl(path, jobs)
    summary = {
        "created_at": _now(),
        "task_count": len(tasks),
        "repetitions": list(repetitions),
        "job_count": len(jobs),
        "condition": "h0",
        "jobs_sha256": sha256_file(path),
    }
    _write_json(out_dir / "r040b_screen_summary.json", summary)
    return summary


def run_calibration_job(
    tasks_path: Path,
    corpus_root: Path,
    runs_dir: Path,
    calibration_id: str,
    repetition: int,
    condition: str,
    model: str,
    timeout_seconds: int,
    *,
    knowledge_file: Path | None = None,
    expected_max_model_len: int = 32768,
) -> dict[str, Any]:
    if condition == "h0" and knowledge_file is not None:
        raise ValueError("h0 must not receive a knowledge file")
    if condition != "h0" and knowledge_file is None:
        raise ValueError(f"{condition} requires a knowledge file")
    configured = os.environ.get("HANDSOFF_MAX_MODEL_LEN")
    if configured is None or int(configured) != expected_max_model_len:
        raise ValueError(
            f"HANDSOFF_MAX_MODEL_LEN must equal {expected_max_model_len}, got {configured!r}"
        )
    tasks = {row["calibration_id"]: row for row in _load_jsonl(tasks_path)}
    if calibration_id not in tasks:
        raise ValueError(f"unknown calibration id: {calibration_id}")
    task = tasks[calibration_id]
    if model != task.get("expected_model_alias"):
        raise ValueError("model alias does not match the frozen selection")
    if timeout_seconds != task.get("expected_timeout_seconds"):
        raise ValueError("timeout does not match the frozen selection")
    model_path = os.environ.get("HANDSOFF_MODEL_PATH")
    model_config = Path(model_path) / "config.json" if model_path else None
    if (
        model_config is None
        or not model_config.is_file()
        or sha256_file(model_config) != task.get("expected_model_config_sha256")
    ):
        raise ValueError("HANDSOFF_MODEL_PATH does not match the frozen model config")
    if Path(model_path).resolve() != Path(task["expected_model_path"]).resolve():
        raise ValueError("HANDSOFF_MODEL_PATH does not match the frozen model path")
    tools = {
        "copilot": resolve_tool_path(configured_tool_path("COPILOT_BIN", "copilot")),
        "verus": resolve_tool_path(configured_tool_path("VERUS_BIN", "verus")),
        "lynette": resolve_tool_path(configured_tool_path("LYNETTE_BIN", "lynette")),
    }
    if any(
        not path.is_file()
        or sha256_file(path) != task["expected_tool_sha256"].get(name)
        for name, path in tools.items()
    ):
        raise ValueError("tool binaries do not match the frozen selection")
    source = _resolve_within(
        corpus_root / task["canonical_source_path"],
        corpus_root / task["directory_group"] / "unverified",
    )
    if sha256_file(source) != task["canonical_source_sha256"]:
        raise ValueError("canonical source changed after selection")
    return run_harness(
        source=source,
        out_dir=runs_dir / calibration_id / f"rep_{repetition}" / condition,
        condition=condition,
        model=model,
        copilot_bin=tools["copilot"],
        verus_bin=tools["verus"],
        lynette_bin=tools["lynette"],
        knowledge_file=knowledge_file,
        timeout_seconds=timeout_seconds,
    )


def run_screen_job(
    tasks_path: Path,
    corpus_root: Path,
    runs_dir: Path,
    calibration_id: str,
    repetition: int,
    model: str,
    timeout_seconds: int,
    *,
    expected_max_model_len: int = 32768,
) -> dict[str, Any]:
    return run_calibration_job(
        tasks_path,
        corpus_root,
        runs_dir,
        calibration_id,
        repetition,
        "h0",
        model,
        timeout_seconds,
        expected_max_model_len=expected_max_model_len,
    )


def _run_record(
    task: dict[str, Any],
    run_dir: Path,
    repetition: int,
    *,
    condition: str = "h0",
    expected_knowledge_sha256: str | None = None,
) -> dict[str, Any]:
    base = {
        "calibration_id": task["calibration_id"],
        "repetition": repetition,
        "condition": condition,
    }
    result_path = run_dir / "result.json"
    manifest_path = run_dir / "run_manifest.json"
    if not result_path.is_file() or not manifest_path.is_file():
        return {**base, "outcome": "missing", "result_available": False}
    result = json.loads(result_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    expected = {
        "source_sha256": task["canonical_source_sha256"],
        "base_prompt_sha256": task["base_prompt_sha256"],
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"run identity mismatch for {task['calibration_id']}: {key}")
    if manifest.get("condition") != condition:
        message = "non-H0 prompt identity" if condition == "h0" else "condition mismatch"
        raise ValueError(f"{message} for {task['calibration_id']}")
    if condition == "h0":
        if manifest.get("prompt_sha256") != manifest.get("base_prompt_sha256"):
            raise ValueError(f"non-H0 prompt identity for {task['calibration_id']}")
        if manifest.get("knowledge_payload_sha256") is not None:
            raise ValueError(f"unexpected H0 knowledge for {task['calibration_id']}")
    elif (
        expected_knowledge_sha256 is None
        or manifest.get("knowledge_payload_sha256") != expected_knowledge_sha256
    ):
        raise ValueError(f"knowledge identity mismatch for {task['calibration_id']}")
    if manifest.get("provider", {}).get("model_config_sha256") != task.get("expected_model_config_sha256"):
        raise ValueError(f"run model config mismatch for {task['calibration_id']}")
    if manifest.get("model") != task.get("expected_model_alias"):
        raise ValueError(f"run model alias mismatch for {task['calibration_id']}")
    model_path = manifest.get("provider", {}).get("model_path")
    if not model_path or Path(model_path).resolve() != Path(task["expected_model_path"]).resolve():
        raise ValueError(f"run model path mismatch for {task['calibration_id']}")
    if manifest.get("provider", {}).get("max_model_len") != task.get("max_model_len", 32768):
        raise ValueError(f"run max_model_len mismatch for {task['calibration_id']}")
    if manifest.get("timeout_seconds") != task.get("expected_timeout_seconds"):
        raise ValueError(f"run timeout mismatch for {task['calibration_id']}")
    if manifest.get("tool_sha256") != task.get("expected_tool_sha256"):
        raise ValueError(f"run tool identity mismatch for {task['calibration_id']}")
    validation = result.get("validation") or {}
    verus = validation.get("verus") or {}
    lynette = validation.get("lynette") or {}
    copilot = result.get("copilot") or {}
    copilot_log = (run_dir / "copilot.log").read_text(errors="replace") if (run_dir / "copilot.log").is_file() else ""
    verus_log = (run_dir / "verus.log").read_text(errors="replace") if (run_dir / "verus.log").is_file() else ""
    diagnostics = parse_verus_diagnostics(verus_log)
    infrastructure = bool(
        copilot.get("timed_out")
        or CONTEXT_FAILURE_RE.search(copilot_log)
        or not validation.get("candidate_present")
        or not verus.get("checked")
        or verus.get("timed_out")
        or not lynette.get("checked")
        or lynette.get("timed_out")
    )
    if infrastructure:
        outcome = "infrastructure_failure"
    elif not lynette.get("passed"):
        outcome = "unsafe"
    elif result.get("status") == "PASS" and verus.get("passed"):
        outcome = "pass"
    else:
        source_errors = task["source_precheck"]["diagnostics"]["error_count"]
        progressed = bool(
            diagnostics["summary_found"]
            and diagnostics["error_count"] is not None
            and diagnostics["error_count"] < source_errors
        )
        outcome = "near_miss" if progressed else "stalled"
    return {
        **base,
        "outcome": outcome,
        "result_available": True,
        "candidate_diagnostics": diagnostics,
        "source_diagnostics": task["source_precheck"]["diagnostics"],
        "source_sha256": manifest["source_sha256"],
        "base_prompt_sha256": manifest["base_prompt_sha256"],
        "prompt_sha256": manifest.get("prompt_sha256"),
        "model": manifest.get("model"),
        "model_path": manifest.get("provider", {}).get("model_path"),
        "model_config_sha256": manifest.get("provider", {}).get("model_config_sha256"),
        "max_model_len": manifest.get("provider", {}).get("max_model_len"),
    }


def classify_task(records: list[dict[str, Any]]) -> str:
    if len(records) != 3 or any(not row.get("result_available") for row in records):
        return "incomplete"
    identities = {
        (row.get("source_sha256"), row.get("base_prompt_sha256"), row.get("model"), row.get("model_path"), row.get("model_config_sha256"), row.get("max_model_len"))
        for row in records
    }
    if len(identities) != 1:
        return "identity_mismatch"
    counts = Counter(row["outcome"] for row in records)
    for outcome in ("infrastructure_failure", "unsafe"):
        if counts[outcome]:
            return outcome
    for tier in TIERS:
        if counts[tier] >= 2:
            return tier
    return "unstable"


def _diverse_pick(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    pools: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        pools.setdefault((row["directory_group"], row["source_size_bin"]), []).append(row)
    for key in pools:
        pools[key].sort(key=lambda row: (_sha256_text(row["calibration_id"]), row["calibration_id"]))
    chosen: list[dict[str, Any]] = []
    strata = sorted(pools)
    while len(chosen) < limit and any(pools.values()):
        for stratum in strata:
            if pools[stratum] and len(chosen) < limit:
                chosen.append(pools[stratum].pop(0))
    return chosen


def select_boundary_candidates(
    tasks_path: Path, runs_dir: Path, out_dir: Path, *, per_class: int = 5
) -> dict[str, Any]:
    tasks = _load_jsonl(tasks_path)
    records = [
        {**task, **_run_record(task, runs_dir / task["calibration_id"] / "rep_1" / "h0", 1)}
        for task in tasks
    ]
    complete = len(records) == 30 and all(row["result_available"] for row in records)
    selected = []
    for tier in TIERS:
        selected.extend(_diverse_pick([row for row in records if row["outcome"] == tier], per_class))
    summary = {
        "created_at": _now(),
        "status": "DONE" if complete else "INCOMPLETE",
        "screen_count": len(records),
        "result_count": sum(row["result_available"] for row in records),
        "outcome_counts": dict(sorted(Counter(row["outcome"] for row in records).items())),
        "boundary_counts": dict(sorted(Counter(row["outcome"] for row in selected).items())),
        "method_evidence": False,
        "source_tasks_sha256": sha256_file(tasks_path),
    }
    _require_empty_output(out_dir)
    _write_json(out_dir / "r040c_boundary_summary.json", summary)
    if complete:
        boundary_path = out_dir / "r040c_boundary_candidates.jsonl"
        _write_jsonl(boundary_path, selected)
        summary["boundary_sha256"] = sha256_file(boundary_path)
        _write_json(out_dir / "r040c_boundary_summary.json", summary)
    return summary


def freeze_tiers(
    boundary_path: Path, runs_dir: Path, out_dir: Path, *, per_tier: int = 3
) -> dict[str, Any]:
    boundary_summary_path = boundary_path.parent / "r040c_boundary_summary.json"
    if not boundary_summary_path.is_file():
        raise ValueError("missing boundary DONE summary")
    boundary_summary = json.loads(boundary_summary_path.read_text())
    if (
        boundary_summary.get("status") != "DONE"
        or boundary_summary.get("boundary_sha256") != sha256_file(boundary_path)
    ):
        raise ValueError("boundary provenance is incomplete or mismatched")
    tasks = _load_jsonl(boundary_path)
    if boundary_summary.get("boundary_counts") != dict(
        sorted(Counter(row["outcome"] for row in tasks).items())
    ):
        raise ValueError("boundary contents do not match the DONE summary")
    _require_empty_output(out_dir)
    classified = []
    all_records = []
    for task in tasks:
        records = [
            _run_record(task, runs_dir / task["calibration_id"] / f"rep_{rep}" / "h0", rep)
            for rep in (1, 2, 3)
        ]
        all_records.extend(records)
        classified.append({**task, "tier": classify_task(records)})
    complete = all(row["result_available"] for row in all_records)
    frozen = []
    for tier in TIERS:
        frozen.extend(_diverse_pick([row for row in classified if row["tier"] == tier], per_tier))
    counts = Counter(row["tier"] for row in frozen)
    can_freeze = complete and all(counts[tier] > 0 for tier in TIERS)
    summary = {
        "created_at": _now(),
        "status": "DONE" if can_freeze else "INCOMPLETE",
        "boundary_task_count": len(tasks),
        "result_count": sum(row["result_available"] for row in all_records),
        "classification_counts": dict(sorted(Counter(row["tier"] for row in classified).items())),
        "frozen_counts": dict(sorted(counts.items())),
        "evidence_level": "diagnostic" if can_freeze and all(counts[tier] == per_tier for tier in TIERS) else "qualitative",
        "method_evidence": False,
    }
    _write_jsonl(out_dir / "r040c_repetitions.jsonl", all_records)
    _write_json(out_dir / "capability_summary.json", summary)
    if can_freeze:
        _write_json(out_dir / "r040d_frozen_tiers.json", {"created_at": _now(), "tasks": frozen})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(prog="handsoff-calibration")
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select")
    select.add_argument("--manifest", type=Path, required=True)
    select.add_argument("--r040-selection", type=Path, required=True)
    select.add_argument("--corpus-root", type=Path)
    select.add_argument("--out-dir", type=Path, required=True)
    select.add_argument("--verus-bin", type=Path, default=configured_tool_path("VERUS_BIN", "verus"))
    select.add_argument("--lynette-bin", type=Path, default=configured_tool_path("LYNETTE_BIN", "lynette"))
    select.add_argument("--copilot-bin", type=Path, default=configured_tool_path("COPILOT_BIN", "copilot"))
    select.add_argument("--tokenizer-path", type=Path, required=True)
    select.add_argument("--per-directory", type=int, default=15)
    select.add_argument("--near-threshold", type=float, default=0.90)
    select.add_argument("--timeout-seconds", type=int, default=120)
    select.add_argument("--max-model-len", type=int, default=32768)
    select.add_argument("--context-reserve", type=int, default=4096)
    select.add_argument("--model-alias", default="qwen35-27b")
    select.add_argument("--inference-timeout-seconds", type=int, default=1200)
    prepare = commands.add_parser("prepare-screen")
    prepare.add_argument("--tasks", type=Path, required=True)
    prepare.add_argument("--out-dir", type=Path, required=True)
    prepare.add_argument("--repetitions", type=int, nargs="+", default=[1])
    run_job = commands.add_parser("run-job")
    run_job.add_argument("--tasks", type=Path, required=True)
    run_job.add_argument("--corpus-root", type=Path)
    run_job.add_argument("--runs-dir", type=Path, required=True)
    run_job.add_argument("--calibration-id", required=True)
    run_job.add_argument("--repetition", type=int, required=True)
    run_job.add_argument("--model", default="qwen35-27b")
    run_job.add_argument("--timeout-seconds", type=int, default=1200)
    boundary = commands.add_parser("select-boundary")
    boundary.add_argument("--tasks", type=Path, required=True)
    boundary.add_argument("--runs-dir", type=Path, required=True)
    boundary.add_argument("--out-dir", type=Path, required=True)
    freeze = commands.add_parser("freeze-tiers")
    freeze.add_argument("--boundary", type=Path, required=True)
    freeze.add_argument("--runs-dir", type=Path, required=True)
    freeze.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "select":
        corpus_root = args.corpus_root or selected_dataset_path("handsoff")
        result = write_selection(
            args.manifest, args.r040_selection, corpus_root,
            validate_output_path(args.out_dir, data_root=corpus_root),
            args.verus_bin, args.lynette_bin, args.copilot_bin, args.tokenizer_path,
            per_directory=args.per_directory, near_threshold=args.near_threshold,
            timeout_seconds=args.timeout_seconds, max_model_len=args.max_model_len,
            context_reserve=args.context_reserve,
            model_alias=args.model_alias,
            inference_timeout_seconds=args.inference_timeout_seconds,
        )
    elif args.command == "prepare-screen":
        result = prepare_screen(args.tasks, validate_output_path(args.out_dir), repetitions=tuple(args.repetitions))
    elif args.command == "run-job":
        corpus_root = args.corpus_root or selected_dataset_path("handsoff")
        result = run_screen_job(
            args.tasks, corpus_root, validate_output_path(args.runs_dir, data_root=corpus_root),
            args.calibration_id, args.repetition, args.model, args.timeout_seconds,
        )
    elif args.command == "select-boundary":
        result = select_boundary_candidates(args.tasks, args.runs_dir, validate_output_path(args.out_dir))
    else:
        result = freeze_tiers(args.boundary, args.runs_dir, validate_output_path(args.out_dir))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
