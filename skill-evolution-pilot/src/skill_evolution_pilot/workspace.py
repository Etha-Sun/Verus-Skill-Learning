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
                    "executable": bool(path.stat().st_mode & 0o111),
                }
            )
    return rows


def prepare_solver_workspace(
    *,
    source: Path,
    workspace: Path,
    task_text: str,
    skill_text: str | None = None,
    skill_source_dir: Path | None = None,
    skill_relative_path: str = "SKILL.md",
    extra_files: Mapping[str, str] | None = None,
    filesystem_visibility_enforced: bool = False,
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
    if skill_text is not None and skill_source_dir is not None:
        raise ValueError("skill_text and skill_source_dir are mutually exclusive")
    skill_paths: set[str] = set()
    if skill_text is not None:
        skill_path = Path(skill_relative_path)
        if skill_path.is_absolute() or ".." in skill_path.parts:
            raise ValueError(f"skill file escapes workspace: {skill_relative_path}")
        destination = workspace / skill_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(skill_text, encoding="utf-8")
        destination.chmod(0o444)
        skill_paths.add(skill_path.as_posix())
    elif skill_source_dir is not None:
        if skill_source_dir.is_symlink():
            raise ValueError(f"skill bundle root must not be a symlink: {skill_source_dir}")
        source_root = skill_source_dir.resolve()
        if not source_root.is_dir() or not (source_root / "SKILL.md").is_file():
            raise ValueError(f"skill bundle must contain SKILL.md: {source_root}")
        skill_path = Path(skill_relative_path)
        if skill_path.is_absolute() or ".." in skill_path.parts:
            raise ValueError(f"skill file escapes workspace: {skill_relative_path}")
        destination_root = workspace / skill_path.parent
        for source_path in sorted(source_root.rglob("*")):
            if source_path.is_symlink():
                raise ValueError(f"skill bundle must not contain symlinks: {source_path}")
            if source_path.is_dir():
                continue
            if not source_path.is_file():
                raise ValueError(f"skill bundle contains a non-file entry: {source_path}")
            relative = source_path.relative_to(source_root)
            destination = destination_root / relative
            if destination.exists():
                raise ValueError(f"skill bundle collides with workspace file: {relative}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)
            destination.chmod(source_path.stat().st_mode & 0o555)
            skill_paths.add(destination.relative_to(workspace).as_posix())

    for relative_path, content in (extra_files or {}).items():
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"extra file escapes workspace: {relative_path}")
        destination = workspace / path
        if destination.exists():
            raise ValueError(f"extra file collides with workspace file: {relative_path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    initial = inventory(workspace)
    roles = {
        "input.rs": "immutable_task",
        "candidate.rs": "writable_candidate",
        "TASK.md": "solver_instruction",
    }
    manifest = {
        "schema_version": "1",
        "workspace": "$WORKSPACE",
        "files": [
            {
                **row,
                "role": (
                    "candidate_skill"
                    if str(row["relative_path"]) in skill_paths
                    else roles.get(str(row["relative_path"]), "allowlisted_tool")
                ),
            }
            for row in initial
        ],
        "input_sha256": sha256_file(input_path),
        "initial_candidate_sha256": sha256_file(candidate_path),
        "reference_proof_visible": False,
        "prior_trace_visible": False,
        "reference_proof_injected": False,
        "prior_trace_injected": False,
        "filesystem_visibility_enforced": filesystem_visibility_enforced,
        "visibility_scope": (
            "allowlisted workspace and external filesystem"
            if filesystem_visibility_enforced
            else "allowlisted workspace inventory only; external reads not enforced"
        ),
        "credential_visible": False,
    }
    (workspace.parent / "visibility_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
