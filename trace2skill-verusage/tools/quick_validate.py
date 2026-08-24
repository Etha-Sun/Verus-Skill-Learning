#!/usr/bin/env python3
"""Validate the bounded Markdown skill format expected by the producer."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


ALLOWED_FRONTMATTER = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}
SAFE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    root = skill_dir.resolve()
    if not root.is_dir():
        return [f"skill directory does not exist: {root}"]
    entries = sorted(root.rglob("*"))
    symlinks = [path for path in entries if path.is_symlink()]
    if symlinks:
        errors.append(f"symlinks are not allowed: {symlinks[0]}")
    skill_file = root / "SKILL.md"
    if not skill_file.is_file():
        return [*errors, "SKILL.md is required"]
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) > 500:
        errors.append(f"SKILL.md exceeds 500 lines: {len(lines)}")
    if len(lines) < 3 or lines[0] != "---":
        errors.append("SKILL.md must start with YAML frontmatter")
    else:
        try:
            end = lines.index("---", 1)
        except ValueError:
            errors.append("SKILL.md frontmatter is not closed")
        else:
            try:
                frontmatter = yaml.safe_load("\n".join(lines[1:end]))
            except yaml.YAMLError as error:
                errors.append(f"invalid YAML frontmatter: {error}")
            else:
                if not isinstance(frontmatter, dict):
                    errors.append("frontmatter must be an object")
                else:
                    unexpected = sorted(set(frontmatter) - ALLOWED_FRONTMATTER)
                    if unexpected:
                        errors.append(
                            "unsupported frontmatter fields: " + ", ".join(unexpected)
                        )
                    name = frontmatter.get("name")
                    description = frontmatter.get("description")
                    if (
                        not isinstance(name, str)
                        or len(name) > 64
                        or not SAFE_NAME.fullmatch(name)
                    ):
                        errors.append("frontmatter name must be safe kebab-case")
                    if (
                        not isinstance(description, str)
                        or not description
                        or len(description) > 1024
                        or "<" in description
                        or ">" in description
                    ):
                        errors.append("frontmatter description is invalid")
    references = root / "references"
    reference_files = (
        sorted(path for path in references.rglob("*") if path.is_file())
        if references.is_dir()
        else []
    )
    for path in reference_files:
        if path.suffix != ".md":
            errors.append(f"reference must be Markdown: {path.relative_to(root)}")
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > 300:
            errors.append(
                f"reference exceeds 300 lines: {path.relative_to(root)} ({line_count})"
            )
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} SKILL_DIR", file=sys.stderr)
        return 2
    errors = validate(Path(sys.argv[1]))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Skill is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
