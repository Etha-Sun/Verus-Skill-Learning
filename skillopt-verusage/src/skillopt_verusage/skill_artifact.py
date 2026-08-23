from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from skillopt_verusage.trace2skill import hash_skill_tree


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SkillArtifact:
    source: Path
    entrypoint: Path
    entrypoint_text: str
    artifact_sha256: str
    hash_kind: str
    files: tuple[dict[str, object], ...]

    @property
    def source_dir(self) -> Path | None:
        return self.source if self.source.is_dir() else None

    def manifest(self) -> dict[str, object]:
        return {
            "source_kind": "directory" if self.source_dir is not None else "file",
            "entrypoint": "SKILL.md" if self.source_dir is not None else self.source.name,
            "entrypoint_sha256": hashlib.sha256(
                self.entrypoint_text.encode("utf-8")
            ).hexdigest(),
            "artifact_sha256": self.artifact_sha256,
            "hash_kind": self.hash_kind,
            "file_count": len(self.files),
            "total_bytes": sum(int(row["size_bytes"]) for row in self.files),
            "files": list(self.files),
        }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _directory_inventory(root: Path) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"skill bundle must not contain symlinks: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"skill bundle contains a non-file entry: {path}")
        rows.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
                "executable": bool(path.stat().st_mode & 0o111),
            }
        )
    return tuple(rows)


def load_skill_artifact(
    path: Path, expected_sha256: str | None = None
) -> SkillArtifact:
    if path.is_symlink():
        raise ValueError(f"skill artifact must not be a symlink: {path}")
    source = path.resolve()
    if source.is_file():
        entrypoint = source
        entrypoint_text = entrypoint.read_text(encoding="utf-8")
        artifact_sha256 = hashlib.sha256(entrypoint_text.encode("utf-8")).hexdigest()
        files = (
            {
                "relative_path": source.name,
                "size_bytes": source.stat().st_size,
                "sha256": _sha256_file(source),
                "executable": bool(source.stat().st_mode & 0o111),
            },
        )
        hash_kind = "skill-markdown-text-sha256"
    elif source.is_dir():
        entrypoint = source / "SKILL.md"
        if not entrypoint.is_file() or entrypoint.is_symlink():
            raise ValueError(f"skill bundle must contain a regular SKILL.md: {source}")
        entrypoint_text = entrypoint.read_text(encoding="utf-8")
        files = _directory_inventory(source)
        artifact_sha256 = hash_skill_tree(source)
        hash_kind = "skill-tree-v1"
    else:
        raise ValueError(f"skill artifact does not exist: {source}")
    if expected_sha256 is not None:
        if not _SHA256.fullmatch(expected_sha256):
            raise ValueError("expected skill hash must be a lowercase SHA-256")
        if artifact_sha256 != expected_sha256:
            raise ValueError(
                f"skill hash mismatch: expected {expected_sha256}, got {artifact_sha256}"
            )
    return SkillArtifact(
        source=source,
        entrypoint=entrypoint,
        entrypoint_text=entrypoint_text,
        artifact_sha256=artifact_sha256,
        hash_kind=hash_kind,
        files=files,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a fixed-test skill artifact")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    artifact = load_skill_artifact(args.path)
    if args.json:
        print(json.dumps(artifact.manifest(), ensure_ascii=False, indent=2))
    else:
        print(artifact.artifact_sha256)


if __name__ == "__main__":
    main()
