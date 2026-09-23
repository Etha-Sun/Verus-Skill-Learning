#!/usr/bin/env python3
"""Validate and adapt the reviewed trace publication to the exporter layout.

This is an offline copy operation. It does not invoke a model, verifier, or
hint provider, and it preserves every published trajectory file byte-for-byte.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any


INITIAL_SKILL_SHA256 = (
    "96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40"
)
REQUIRED_TRACE_FILES = (
    "agent_events.jsonl",
    "codex_events.raw.jsonl",
    "conversation.json",
    "result.json",
    "run_manifest.json",
    "prompt.txt",
    "target_user_prompt.txt",
    "workspace/input.rs",
    "workspace/candidate.rs",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def require_fresh_output(path: Path) -> Path:
    configured = os.environ.get("VERUS_SKILL_RUN_ROOT")
    if not configured:
        raise RuntimeError("VERUS_SKILL_RUN_ROOT is not set")
    run_root = Path(configured).resolve()
    output = path.resolve()
    if output == run_root or run_root not in output.parents:
        raise ValueError(f"output must be a child of VERUS_SKILL_RUN_ROOT: {output}")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    return output


def archive_run(
    manifest: dict[str, Any], project: str, version: str, checkpoint: str
) -> dict[str, Any]:
    matches = [
        row
        for row in manifest["runs"]
        if row["task"] == project
        and row["version"] == version
        and row["checkpoint"] == checkpoint
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one archive manifest row for {project}/{version}/{checkpoint}"
        )
    return matches[0]


def validate_archived_run(source: Path, record: dict[str, Any]) -> None:
    published = {str(row["path"]): row for row in record["files"]}
    for relative in REQUIRED_TRACE_FILES:
        if relative not in published:
            raise FileNotFoundError(f"archive manifest omits {source / relative}")
    for relative, row in published.items():
        path = source / relative
        if not path.is_file():
            raise FileNotFoundError(f"archive file is missing: {path}")
        if sha256(path) != row["published_sha256"]:
            raise ValueError(f"archive hash mismatch: {path}")
        if path.suffix == ".json":
            load_json(path)
        elif path.suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    json.loads(line)

    events = [
        json.loads(line)
        for line in (source / "agent_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(events) != int(record["event_count"]):
        raise ValueError(f"event count mismatch: {source}")
    for event in events:
        data = event.get("data") or {}
        for key in ("snapshot", "diff"):
            relative = data.get(key)
            if relative is None:
                continue
            if not isinstance(relative, str) or relative not in published:
                raise ValueError(f"unresolved {key} reference in {source}")
            if key == "snapshot" and event.get("candidate_sha256") != sha256(
                source / relative
            ):
                raise ValueError(f"snapshot hash mismatch in {source}: {relative}")


def adapt(
    *,
    trace_archive_root: Path,
    publication_project_root: Path,
    output_root: Path,
    project: str,
    version: str,
    source_git_commit: str,
) -> dict[str, Any]:
    project_lower = project.lower()
    if project_lower not in {"ir", "ac", "al"}:
        raise ValueError(f"unsupported project: {project}")
    if version not in {"v1", "v2"}:
        raise ValueError(f"unsupported hint version: {version}")

    trace_archive_root = trace_archive_root.resolve()
    publication_project_root = publication_project_root.resolve()
    output = require_fresh_output(output_root)
    archive_manifest_path = trace_archive_root / "manifest.json"
    archive_manifest = load_json(archive_manifest_path)
    if len(archive_manifest.get("runs", [])) != 38:
        raise ValueError("published trace archive must contain exactly 38 runs")

    project_runs = [
        row
        for row in archive_manifest["runs"]
        if row["task"] == project_lower and row["version"] == version
    ]
    task_ids = {str(row["task_id"]) for row in project_runs}
    if len(task_ids) != 1:
        raise ValueError(f"archive task identity is ambiguous: {project}/{version}")
    task_id = task_ids.pop()
    source_selection_path = publication_project_root / "selection_manifest.json"
    selected = [
        row
        for row in load_json(source_selection_path)["checkpoints"]
        if row.get("continue") is True
    ]
    selection = {
        "schema_version": "recorded-hint-trace-selection-v1",
        "condition": f"historical_generated_hint_{version}",
        "task": {
            "id": task_id,
            "task_id": task_id,
            "project_code": project.upper(),
        },
        "checkpoints": [
            {
                "ordinal": ordinal,
                "event_index": int(row["event_index"]),
                "checkpoint_sha256": str(row["candidate_sha256"]),
            }
            for ordinal, row in enumerate(selected, 1)
        ],
        "checkpoint_source_kind": "reviewed_recorded_trace_archive",
        "source_selection_sha256": sha256(source_selection_path),
        "source_trace_archive_manifest_sha256": sha256(archive_manifest_path),
        "source_git_commit": source_git_commit,
    }

    adapted_runs: list[dict[str, Any]] = []
    for row in selection["checkpoints"]:
        ordinal = int(row["ordinal"])
        checkpoint = f"CP{ordinal:02d}"
        checkpoint_sha = str(row["checkpoint_sha256"])
        source = trace_archive_root / project_lower / version / checkpoint
        record = archive_run(archive_manifest, project_lower, version, checkpoint)
        if record.get("task_id") != task_id:
            raise ValueError(f"task mismatch in archive: {source}")
        validate_archived_run(source, record)

        contract = load_json(source / "hint_contract.json")
        if contract.get("checkpoint_sha256") != checkpoint_sha:
            raise ValueError(f"checkpoint contract mismatch: {source}")
        if contract.get("actor_skill_sha256") != INITIAL_SKILL_SHA256:
            raise ValueError(f"actor skill mismatch: {source}")
        candidates = sorted((source / "snapshots").glob("*-candidate.rs"))
        if not candidates or sha256(candidates[0]) != checkpoint_sha:
            raise ValueError(f"first actor snapshot is not the checkpoint: {source}")

        hint_source = publication_project_root / version / checkpoint / "hint.json"
        hint = load_json(hint_source)
        if hint.get("checkpoint_sha256") != checkpoint_sha:
            raise ValueError(f"published hint checkpoint mismatch: {hint_source}")
        hint_text = (source / "hint.txt").read_text(encoding="utf-8")
        if hint_text not in {str(hint["hint_text"]), str(hint["hint_text"]) + "\n"}:
            raise ValueError(f"published hint text mismatch: {source}")

        private = output / "hint-private" / task_id / checkpoint
        private.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidates[0], private / "checkpoint.rs")
        shutil.copyfile(hint_source, private / "hint.json")
        run_destination = output / "runs" / task_id / checkpoint
        shutil.copytree(source, run_destination)
        provenance = {
            "schema_version": "recorded-hint-trace-provenance-v1",
            "source_git_commit": source_git_commit,
            "source_archive_manifest_sha256": sha256(archive_manifest_path),
            "source_archive_run": f"{project_lower}/{version}/{checkpoint}",
            "source_files_verified": len(record["files"]),
            "path_redaction_preserved": True,
            "hint_generation_api_called_in_current_run": False,
            "trajectory_rerun_in_current_run": False,
        }
        write_json(private / "recorded_trace_provenance.json", provenance)
        write_json(run_destination / "recorded_trace_provenance.json", provenance)
        row["checkpoint_path"] = str(private / "checkpoint.rs")
        adapted_runs.append(
            {
                "checkpoint": checkpoint,
                "event_count": int(record["event_count"]),
                "source_files_verified": len(record["files"]),
                "dual_verifier_pass": bool(
                    load_json(source / "validation.json")["verus"]["passed"]
                    and load_json(source / "validation.json")["lynette"]["passed"]
                ),
            }
        )

    write_json(output / "selection.json", selection)
    result = {
        "schema_version": "recorded-hint-trace-adaptation-v1",
        "project": project.upper(),
        "version": version,
        "task_id": task_id,
        "run_count": len(adapted_runs),
        "dual_verifier_pass_count": sum(
            int(row["dual_verifier_pass"]) for row in adapted_runs
        ),
        "source_git_commit": source_git_commit,
        "source_archive_manifest_sha256": sha256(archive_manifest_path),
        "runs": adapted_runs,
    }
    write_json(output / "adaptation_manifest.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-archive-root", type=Path, required=True)
    parser.add_argument("--publication-project-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--project", choices=("IR", "AC", "AL"), required=True)
    parser.add_argument("--version", choices=("v1", "v2"), required=True)
    parser.add_argument("--source-git-commit", required=True)
    args = parser.parse_args()
    result = adapt(**vars(args))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
