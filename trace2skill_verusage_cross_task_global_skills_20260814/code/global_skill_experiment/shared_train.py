"""Materialize and hash the frozen cross-task Claude training inputs."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_SOURCES = {
    "AC": ("verified-anvil", "results_advanced-sonnet45", "results_advanced-sonnet45.csv"),
    "AL": ("verified-anvil", "results-sonnet45", "results-sonnet45.csv"),
    "IR": ("verified-ironkv", "results-sonnet45", "results-sonnet45.csv"),
}
OUTCOME_RE = re.compile(r"^(TRUE|FALSE|CHEAT(?:\s*\([^)]*\))?)$", re.IGNORECASE)
ADVANCED_ROW_RE = re.compile(
    r"^\*\*\*\s+(.+?):\s*(TRUE|FALSE|CHEAT(?:\s*\([^)]*\))?)\s*$",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(payload)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def assert_below(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"output must be below run root: {root}") from exc


def parse_outcome_csv(path: Path) -> dict[str, str]:
    """Parse both ordinary ``task, RESULT`` and advanced ``*** task: RESULT`` rows."""
    labels: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        advanced = ADVANCED_ROW_RE.match(line)
        if advanced:
            task_id, label = advanced.groups()
        else:
            row = next(csv.reader([line], skipinitialspace=True))
            if len(row) < 2:
                continue
            task_id, label = row[0].strip(), row[1].strip()
            if not OUTCOME_RE.fullmatch(label):
                continue
        normalized = label.upper()
        previous = labels.get(task_id)
        if previous is not None and previous != normalized:
            raise ValueError(f"conflicting labels for {task_id} in {path}")
        labels[task_id] = normalized
    return labels


def result_class(raw_label: str) -> str:
    if raw_label == "TRUE":
        return "true"
    if raw_label == "FALSE":
        return "false"
    if raw_label.startswith("CHEAT"):
        return "cheat"
    raise ValueError(f"unsupported Claude outcome: {raw_label}")


def memory_route(raw_label: str) -> str:
    return "success" if raw_label == "TRUE" else "failure"


def artifact_record(path: Path, materialized_relative_path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "materialized_path": materialized_relative_path.as_posix(),
        "sha256": sha256_bytes(raw),
        "size_bytes": len(raw),
        "line_count": len(raw.splitlines()),
    }


def load_train_items(path: Path) -> list[dict[str, Any]]:
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list) or len(items) != 40:
        raise ValueError("frozen train/items.json must contain exactly 40 items")
    task_ids = [str(item.get("task_id", "")) for item in items]
    if len(set(task_ids)) != 40 or any(not task_id for task_id in task_ids):
        raise ValueError("frozen train task IDs must be non-empty and unique")
    return items


def materialize(
    train_items_path: Path,
    claude_root: Path,
    run_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Copy the 40 selected local Claude artifact triplets into a frozen run input."""
    train_items_path = train_items_path.resolve()
    claude_root = claude_root.resolve()
    run_root = run_root.resolve()
    output_root = output_root.resolve()
    assert_below(output_root, run_root)
    if output_root.exists():
        raise FileExistsError(f"materialized output already exists: {output_root}")
    if not claude_root.is_dir():
        raise FileNotFoundError(f"Claude root does not exist: {claude_root}")

    items = load_train_items(train_items_path)
    labels_by_csv: dict[Path, dict[str, str]] = {}
    records: list[dict[str, Any]] = []
    output_root.mkdir(parents=True)
    configuration = output_root / "configuration"
    configuration.mkdir()
    shutil.copyfile(train_items_path, configuration / "train_items.snapshot.json")

    for order, item in enumerate(items, start=1):
        project = item["project_code"]
        if project not in PROJECT_SOURCES:
            raise ValueError(f"unsupported project code: {project}")
        expected_prefix = f"{project}__"
        task_id = item["task_id"]
        if not task_id.startswith(expected_prefix):
            raise ValueError(f"task prefix mismatch: {task_id}")
        stem = task_id[len(expected_prefix) :]
        group, result_dir_name, csv_name = PROJECT_SOURCES[project]
        if item.get("directory_group") != group:
            raise ValueError(f"directory group mismatch: {task_id}")
        result_dir = claude_root / group / result_dir_name
        csv_path = claude_root / group / csv_name
        labels = labels_by_csv.setdefault(csv_path, parse_outcome_csv(csv_path))
        if stem not in labels:
            raise ValueError(f"local Claude outcome missing for {task_id}")
        raw_label = labels[stem]

        source_path = result_dir / f"{stem}.rs"
        trajectory_path = result_dir / f"{stem}.log"
        candidate_path = result_dir / f"{stem}_verified.rs"
        for kind, path in (
            ("source", source_path),
            ("trajectory", trajectory_path),
            ("candidate", candidate_path),
        ):
            if not path.is_file():
                raise FileNotFoundError(f"missing {kind} for {task_id}: {path}")

        task_dir = output_root / "artifacts" / task_id
        task_dir.mkdir(parents=True)
        destinations = {
            "source": task_dir / "source.rs",
            "trajectory": task_dir / "trajectory.log",
            "candidate": task_dir / "candidate.rs",
        }
        for source, destination in (
            (source_path, destinations["source"]),
            (trajectory_path, destinations["trajectory"]),
            (candidate_path, destinations["candidate"]),
        ):
            shutil.copyfile(source, destination)
            if sha256_file(source) != sha256_file(destination):
                raise RuntimeError(f"copy hash mismatch for {source}")

        artifacts = {
            name: artifact_record(source, destination.relative_to(output_root))
            for name, source, destination in (
                ("source", source_path, destinations["source"]),
                ("trajectory", trajectory_path, destinations["trajectory"]),
                ("candidate", candidate_path, destinations["candidate"]),
            )
        }
        source_hash_matches_selection = (
            artifacts["source"]["sha256"] == item.get("source_sha256")
        )
        record = {
            "order": order,
            "selection_item_id": item["id"],
            "task_id": task_id,
            "task_stem": stem,
            "project_code": project,
            "directory_group": group,
            "claude_result_set": result_dir_name,
            "claude_outcome_raw": raw_label,
            "claude_result_class": result_class(raw_label),
            "memory_route": memory_route(raw_label),
            "artifacts": artifacts,
            "selection_metadata": {
                "claude_status": item.get("claude_status"),
                "claude_batch": item.get("claude_batch"),
                "source_sha256": item.get("source_sha256"),
                "source_hash_matches_local_claude_artifact": source_hash_matches_selection,
            },
        }
        write_json(
            task_dir / "outcome.json",
            {
                "task_id": task_id,
                "claude_outcome_raw": raw_label,
                "claude_result_class": record["claude_result_class"],
                "memory_route": record["memory_route"],
            },
        )
        records.append(record)

    records_path = output_root / "records.jsonl"
    write_jsonl(records_path, records)
    content_projection = [
        {
            "order": row["order"],
            "task_id": row["task_id"],
            "project_code": row["project_code"],
            "claude_outcome_raw": row["claude_outcome_raw"],
            "memory_route": row["memory_route"],
            "artifact_hashes": {
                name: artifact["sha256"]
                for name, artifact in sorted(row["artifacts"].items())
            },
        }
        for row in records
    ]
    manifest = {
        "schema_version": 1,
        "created_at": utc_now(),
        "status": "complete",
        "scope": "the exact 40 IDs from frozen train/items.json only",
        "cross_split_similarity_or_overlap_reaudit_performed": False,
        "train_items_sha256": sha256_file(train_items_path),
        "train_count": len(records),
        "project_counts": dict(sorted(Counter(r["project_code"] for r in records).items())),
        "result_class_counts": dict(
            sorted(Counter(r["claude_result_class"] for r in records).items())
        ),
        "memory_route_counts": dict(
            sorted(Counter(r["memory_route"] for r in records).items())
        ),
        "selection_source_hash_match_count": sum(
            bool(r["selection_metadata"]["source_hash_matches_local_claude_artifact"])
            for r in records
        ),
        "selection_source_hash_mismatch_count": sum(
            not r["selection_metadata"]["source_hash_matches_local_claude_artifact"]
            for r in records
        ),
        "records_jsonl_sha256": sha256_file(records_path),
        "materialized_input_sha256": canonical_sha256(content_projection),
        "artifact_source_contract": {
            project: {
                "directory_group": values[0],
                "result_directory": values[1],
                "outcome_csv": values[2],
            }
            for project, values in sorted(PROJECT_SOURCES.items())
        },
    }
    write_json(output_root / "manifest.json", manifest)
    return manifest
