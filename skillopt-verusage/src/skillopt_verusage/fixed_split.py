from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


PROJECT_TO_GROUP = {
    "AC": "verified-anvil",
    "AL": "verified-anvil",
    "IR": "verified-ironkv",
}
OUTCOME_QUOTAS = {
    ("AC", "failed"): {"train": 4, "val": 2, "test": 2},
    ("AC", "normal"): {"train": 8, "val": 4, "test": 4},
    ("AL", "failed"): {"train": 2, "val": 1, "test": 1},
    ("AL", "normal"): {"train": 12, "val": 6, "test": 6},
    ("IR", "failed"): {"train": 4, "val": 2, "test": 2},
    ("IR", "normal"): {"train": 10, "val": 5, "test": 5},
}
EXPECTED_COUNTS = {"train": 40, "val": 20, "test": 20}
FAILED_STATUSES = {"FAILED", "TIMEOUT"}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalized_task(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def normalize_history_source(text: str) -> str:
    """Remove the one harness-only line before matching historical inputs."""
    normalized = text.replace("\r\n", "\n")
    lines = [
        line.rstrip()
        for line in normalized.splitlines()
        if line.strip() != "#[verifier::loop_isolation(false)]"
    ]
    return "\n".join(lines).rstrip() + "\n"


def _load_prior_tasks(
    prior_split: Path, r040_selection: Path
) -> tuple[set[str], set[str]]:
    old_tasks: set[str] = set()
    for split_name in ("train", "val", "test"):
        path = prior_split / split_name / "items.json"
        for row in json.loads(path.read_text(encoding="utf-8")):
            old_tasks.add(str(row["task_id"]))

    r040_tasks: set[str] = set()
    with r040_selection.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                r040_tasks.add(str(json.loads(line)["task_id"]))
    return old_tasks, r040_tasks


def load_candidates(
    *,
    claude_results_root: Path,
    benchmark_tasks: Path,
    prior_split: Path,
    r040_selection: Path,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    old_tasks, r040_tasks = _load_prior_tasks(prior_split, r040_selection)
    candidates: list[dict[str, Any]] = []
    audit: Counter[str] = Counter()
    seen: set[str] = set()

    for csv_path in sorted(claude_results_root.glob("results-batch_*/results.csv")):
        csv_sha256 = _sha256_file(csv_path)
        with csv_path.open(newline="", encoding="utf-8", errors="replace") as handle:
            for result in csv.DictReader(handle):
                file_name = str(result.get("file") or "")
                if "__" not in file_name or not file_name.endswith(".rs"):
                    continue
                if Path(file_name).name != file_name:
                    audit["unsafe_claude_file_name"] += 1
                    continue
                project, short_file = file_name.split("__", 1)
                if project not in PROJECT_TO_GROUP:
                    continue

                task_id = file_name[:-3]
                short_task = short_file[:-3]
                if task_id in seen:
                    audit["duplicate_claude_result"] += 1
                    continue
                seen.add(task_id)
                if short_task in old_tasks:
                    audit["prior_skillopt_task"] += 1
                    continue
                if short_task in r040_tasks:
                    audit["prior_r040_task"] += 1
                    continue

                status = str(result.get("status") or "")
                if status == "VERIFIED":
                    outcome = "normal"
                elif status in FAILED_STATUSES:
                    outcome = "failed"
                else:
                    audit["unsupported_claude_status"] += 1
                    continue

                source = (benchmark_tasks / file_name).resolve()
                run_dirs = sorted(csv_path.parent.glob(f"o-{task_id}-*"))
                if not source.is_file():
                    audit["missing_benchmark_source"] += 1
                    continue
                if len(run_dirs) != 1:
                    audit[f"historical_run_dir_count_{len(run_dirs)}"] += 1
                    continue
                historical_input = run_dirs[0] / "fix-v0-input.rs"
                if not historical_input.is_file():
                    audit["missing_historical_input"] += 1
                    continue

                source_text = source.read_text(encoding="utf-8", errors="replace")
                history_text = historical_input.read_text(
                    encoding="utf-8", errors="replace"
                )
                source_normalized_sha256 = _sha256_bytes(
                    normalize_history_source(source_text).encode("utf-8")
                )
                history_normalized_sha256 = _sha256_bytes(
                    normalize_history_source(history_text).encode("utf-8")
                )
                if source_normalized_sha256 != history_normalized_sha256:
                    audit["historical_input_mismatch"] += 1
                    continue

                candidates.append(
                    {
                        "id": _stable(f"{task_id}::{_sha256_file(source)}")[:20],
                        "task_id": task_id,
                        "normalized_task_id": _normalized_task(task_id),
                        "project_code": project,
                        "directory_group": PROJECT_TO_GROUP[project],
                        "source_path": str(source),
                        "source_sha256": _sha256_file(source),
                        "source_normalized_sha256": source_normalized_sha256,
                        "source_size_bytes": source.stat().st_size,
                        "source_loc": len(source_text.splitlines()),
                        "claude_status": status,
                        "claude_outcome": outcome,
                        "claude_failed": outcome == "failed",
                        "claude_time_seconds": float(result.get("time_seconds") or 0.0),
                        "claude_total_tokens": int(
                            float(result.get("total_tokens") or 0)
                        ),
                        "claude_batch": csv_path.parent.name,
                        "claude_results_csv_sha256": csv_sha256,
                        "claude_input_sha256": _sha256_file(historical_input),
                        "claude_input_normalized_sha256": history_normalized_sha256,
                    }
                )
                audit["historical_input_match"] += 1
    return candidates, audit


def _precheck(
    row: dict[str, Any], verus_bin: Path, timeout: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        completed = subprocess.run(
            [str(verus_bin), row["source_path"]],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout + completed.stderr
        summary = re.findall(
            r"verification results::\s*(\d+) verified,\s*(\d+) errors?",
            output,
            re.IGNORECASE,
        )
        passed = completed.returncode == 0 and "error: aborting" not in output.lower()
        check = {
            "returncode": completed.returncode,
            "timed_out": False,
            "passed": passed,
            "verified_count": int(summary[-1][0]) if summary else None,
            "error_count": int(summary[-1][1]) if summary else None,
        }
    except subprocess.TimeoutExpired:
        check = {
            "returncode": None,
            "timed_out": True,
            "passed": False,
            "verified_count": None,
            "error_count": None,
        }
    return row, check


def precheck_candidates(
    rows: list[dict[str, Any]], *, verus_bin: Path, workers: int, timeout: int
) -> tuple[list[dict[str, Any]], Counter[str]]:
    eligible: list[dict[str, Any]] = []
    audit: Counter[str] = Counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        checked = executor.map(lambda row: _precheck(row, verus_bin, timeout), rows)
        for row, check in checked:
            if check["timed_out"]:
                audit["source_precheck_timeout"] += 1
            elif check["passed"]:
                audit["source_already_verified"] += 1
            else:
                item = dict(row)
                item["source_precheck"] = check
                eligible.append(item)
                audit["source_precheck_failed_as_expected"] += 1
    return eligible, audit


def _rank_scores(rows: list[dict[str, Any]]) -> None:
    metrics = ("source_loc", "claude_time_seconds", "claude_total_tokens")
    by_stratum: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_stratum[(row["project_code"], row["claude_outcome"])].append(row)
    for pool in by_stratum.values():
        ranks: dict[str, dict[str, float]] = {}
        for metric in metrics:
            ordered = sorted(pool, key=lambda row: (float(row[metric]), row["task_id"]))
            denominator = max(1, len(ordered) - 1)
            ranks[metric] = {
                row["task_id"]: index / denominator for index, row in enumerate(ordered)
            }
        for row in pool:
            row["difficulty_proxy"] = round(
                sum(ranks[metric][row["task_id"]] for metric in metrics) / len(metrics),
                6,
            )


def select_rows(
    rows: list[dict[str, Any]], *, seed: int
) -> dict[str, list[dict[str, Any]]]:
    rows = [dict(row) for row in rows]
    _rank_scores(rows)
    selected: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}

    for stratum, quotas in OUTCOME_QUOTAS.items():
        pool = sorted(
            [
                row
                for row in rows
                if (row["project_code"], row["claude_outcome"]) == stratum
            ],
            key=lambda row: (row["difficulty_proxy"], row["task_id"]),
        )
        needed = sum(quotas.values())
        if len(pool) < needed:
            raise RuntimeError(
                f"insufficient candidates for {stratum}: {len(pool)} < {needed}"
            )
        if needed % 4:
            raise RuntimeError(f"stratum quota is not divisible by four: {stratum}")

        chosen = [
            pool[math.floor((index + 0.5) * len(pool) / needed)]
            for index in range(needed)
        ]
        if len({row["id"] for row in chosen}) != needed:
            raise RuntimeError(f"quantile selection repeated a task: {stratum}")
        for start in range(0, needed, 4):
            quartet = sorted(
                chosen[start : start + 4],
                key=lambda row: _stable(f"fixed80::{seed}::{row['task_id']}"),
            )
            selected["train"].extend(quartet[:2])
            selected["val"].append(quartet[2])
            selected["test"].append(quartet[3])

    for split_name, split_rows in selected.items():
        split_rows.sort(
            key=lambda row: _stable(f"order::{seed}::{split_name}::{row['task_id']}")
        )
        if len(split_rows) != EXPECTED_COUNTS[split_name]:
            raise RuntimeError(f"wrong {split_name} count: {len(split_rows)}")
    all_ids = [row["id"] for split_rows in selected.values() for row in split_rows]
    if len(all_ids) != 80 or len(set(all_ids)) != 80:
        raise RuntimeError("split does not contain 80 unique tasks")
    return selected


def _external_empty(path: Path) -> Path:
    run_root_text = os.environ.get("VERUS_SKILL_RUN_ROOT", "")
    if not run_root_text:
        raise ValueError("VERUS_SKILL_RUN_ROOT is not configured")
    run_root = Path(run_root_text).resolve()
    resolved = path.resolve()
    if resolved == run_root or run_root not in resolved.parents:
        raise ValueError(f"output must be below VERUS_SKILL_RUN_ROOT: {resolved}")
    if resolved.exists() and any(resolved.iterdir()):
        raise ValueError(f"output must be empty: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _summary_stats(rows: list[dict[str, Any]], field: str) -> dict[str, float]:
    values = [float(row[field]) for row in rows]
    return {
        "mean": round(statistics.fmean(values), 3),
        "median": round(statistics.median(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def materialize_split(
    *,
    selected: dict[str, list[dict[str, Any]]],
    out_dir: Path,
    seed: int,
    candidate_audit: Counter[str],
    precheck_audit: Counter[str],
) -> dict[str, Any]:
    out_dir = _external_empty(out_dir)
    emitted: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    csv_rows: list[dict[str, Any]] = []

    for split_name, rows in selected.items():
        split_dir = out_dir / split_name
        split_dir.mkdir()
        for row in rows:
            source = Path(row["source_path"])
            copied_source = (
                out_dir
                / "sources"
                / row["directory_group"]
                / "unverified"
                / f"{row['task_id']}.rs"
            )
            copied_source.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, copied_source)
            item = dict(row)
            item["source_path"] = str(copied_source.resolve())
            if _sha256_file(copied_source) != item["source_sha256"]:
                raise RuntimeError(f"copied source hash mismatch: {copied_source}")
            emitted[split_name].append(item)
            csv_rows.append(
                {
                    "split": "selection" if split_name == "val" else split_name,
                    "task_id": item["task_id"],
                    "project_code": item["project_code"],
                    "claude_status": item["claude_status"],
                    "claude_outcome": item["claude_outcome"],
                    "source_loc": item["source_loc"],
                    "claude_time_seconds": item["claude_time_seconds"],
                    "claude_total_tokens": item["claude_total_tokens"],
                    "difficulty_proxy": item["difficulty_proxy"],
                    "source_sha256": item["source_sha256"],
                }
            )
        (split_dir / "items.json").write_text(
            json.dumps(emitted[split_name], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    with (out_dir / "split_tasks.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)

    digest_payload = {
        split_name: [(row["id"], row["source_sha256"]) for row in rows]
        for split_name, rows in emitted.items()
    }
    audit = {
        "schema_version": "1",
        "seed": seed,
        "counts": {name: len(rows) for name, rows in emitted.items()},
        "by_project": {
            name: dict(sorted(Counter(row["project_code"] for row in rows).items()))
            for name, rows in emitted.items()
        },
        "by_claude_outcome": {
            name: dict(sorted(Counter(row["claude_outcome"] for row in rows).items()))
            for name, rows in emitted.items()
        },
        "by_claude_status": {
            name: dict(sorted(Counter(row["claude_status"] for row in rows).items()))
            for name, rows in emitted.items()
        },
        "by_project_and_outcome": {
            name: {
                f"{project}/{outcome}": count
                for (project, outcome), count in sorted(
                    Counter(
                        (row["project_code"], row["claude_outcome"]) for row in rows
                    ).items()
                )
            }
            for name, rows in emitted.items()
        },
        "difficulty": {
            name: {
                "source_loc": _summary_stats(rows, "source_loc"),
                "claude_time_seconds": _summary_stats(rows, "claude_time_seconds"),
                "claude_total_tokens": _summary_stats(rows, "claude_total_tokens"),
                "difficulty_proxy": _summary_stats(rows, "difficulty_proxy"),
            }
            for name, rows in emitted.items()
        },
        "candidate_audit": dict(sorted(candidate_audit.items())),
        "source_precheck_audit": dict(sorted(precheck_audit.items())),
        "exact_task_overlap": 0,
        "exact_source_hash_overlap": 0,
        "failed_fraction": {
            name: sum(row["claude_failed"] for row in rows) / len(rows)
            for name, rows in emitted.items()
        },
        "split_sha256": _stable(json.dumps(digest_payload, sort_keys=True)),
        "historical_label": "all_batch_results-cyy-claude final CSV status",
        "normal_definition": "VERIFIED",
        "failed_definition": ["FAILED", "TIMEOUT"],
        "selection_directory_name": "val",
        "reference_content_exported": False,
        "sealed_directories_read": [],
    }
    hashes = [row["source_sha256"] for rows in emitted.values() for row in rows]
    if len(set(hashes)) != len(hashes):
        raise RuntimeError("source hash overlap detected")
    (out_dir / "split_manifest.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "README.md").write_text(
        "# Fixed Claude-stratified VeruSAGE split\n\n"
        "This frozen split contains 40 training, 20 selection (`val`), and 20 test tasks. "
        "Each split is 25% historical Claude `FAILED`/`TIMEOUT` and 75% historical Claude "
        "`VERIFIED`, with matched AC/AL/IR quotas and a joint LoC/runtime/token difficulty "
        "proxy. Previously used SkillOpt-100 and R040 tasks were excluded. No verified "
        "reference proof is included.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze a Claude-stratified AC/AL/IR split"
    )
    parser.add_argument("--claude-results-root", type=Path, required=True)
    parser.add_argument("--benchmark-tasks", type=Path, required=True)
    parser.add_argument("--prior-split", type=Path, required=True)
    parser.add_argument("--r040-selection", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--verus-bin", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--precheck-timeout", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates, candidate_audit = load_candidates(
        claude_results_root=args.claude_results_root,
        benchmark_tasks=args.benchmark_tasks,
        prior_split=args.prior_split,
        r040_selection=args.r040_selection,
    )
    eligible, precheck_audit = precheck_candidates(
        candidates,
        verus_bin=args.verus_bin.resolve(),
        workers=args.workers,
        timeout=args.precheck_timeout,
    )
    selected = select_rows(eligible, seed=args.seed)
    audit = materialize_split(
        selected=selected,
        out_dir=args.out_dir,
        seed=args.seed,
        candidate_audit=candidate_audit,
        precheck_audit=precheck_audit,
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
