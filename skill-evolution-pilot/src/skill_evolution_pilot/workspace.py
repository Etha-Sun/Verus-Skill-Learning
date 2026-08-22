from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Mapping


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(workspace: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "relative_path": str(path.relative_to(workspace)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return rows


def prepare_solver_workspace(
    *,
    source: Path,
    workspace: Path,
    task_text: str,
    skill_text: str | None = None,
    skill_relative_path: str = "SKILL.md",
    extra_files: Mapping[str, str] | None = None,
) -> dict[str, object]:
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError(f"workspace must be empty: {workspace}")
    workspace.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")

    input_path = workspace / "input.rs"
    candidate_path = workspace / "candidate.rs"
    shutil.copyfile(source, input_path)
    shutil.copyfile(source, candidate_path)
    input_path.chmod(0o444)
    (workspace / "TASK.md").write_text(task_text, encoding="utf-8")
    if skill_text is not None:
        skill_path = Path(skill_relative_path)
        if skill_path.is_absolute() or ".." in skill_path.parts:
            raise ValueError(f"skill file escapes workspace: {skill_relative_path}")
        destination = workspace / skill_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(skill_text, encoding="utf-8")

    for relative_path, content in (extra_files or {}).items():
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"extra file escapes workspace: {relative_path}")
        destination = workspace / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    initial = inventory(workspace)
    roles = {
        "input.rs": "immutable_task",
        "candidate.rs": "writable_candidate",
        "TASK.md": "solver_instruction",
        skill_relative_path: "candidate_skill",
    }
    manifest = {
        "schema_version": "1",
        "workspace": "$WORKSPACE",
        "files": [
            {
                **row,
                "role": roles.get(str(row["relative_path"]), "allowlisted_tool"),
            }
            for row in initial
        ],
        "input_sha256": sha256_file(input_path),
        "initial_candidate_sha256": sha256_file(candidate_path),
        "reference_proof_visible": False,
        "prior_trace_visible": False,
        "credential_visible": False,
    }
    (workspace.parent / "visibility_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
