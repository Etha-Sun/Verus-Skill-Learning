from __future__ import annotations

from pathlib import Path

import pytest

from skillopt_verusage.skill_artifact import load_skill_artifact
from skillopt_verusage.trace2skill import hash_skill_tree


def test_single_file_artifact_preserves_existing_text_hash(tmp_path: Path) -> None:
    skill = tmp_path / "skill.md"
    skill.write_text("one skill\n", encoding="utf-8")
    artifact = load_skill_artifact(skill)
    assert artifact.source_dir is None
    assert artifact.hash_kind == "skill-markdown-text-sha256"
    assert artifact.manifest()["file_count"] == 1
    load_skill_artifact(skill, artifact.artifact_sha256)


def test_trace2skill_bundle_uses_candidate_tree_hash(tmp_path: Path) -> None:
    bundle = tmp_path / "verus-proof-repair"
    (bundle / "references").mkdir(parents=True)
    (bundle / "SKILL.md").write_text("Read references/loops.md.\n", encoding="utf-8")
    (bundle / "references" / "loops.md").write_text(
        "Keep the invariant.\n", encoding="utf-8"
    )
    artifact = load_skill_artifact(bundle)
    assert artifact.source_dir == bundle.resolve()
    assert artifact.artifact_sha256 == hash_skill_tree(bundle)
    assert artifact.manifest()["file_count"] == 2
    load_skill_artifact(bundle, artifact.artifact_sha256)


def test_trace2skill_bundle_requires_entrypoint_and_rejects_symlinks(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    missing.mkdir()
    with pytest.raises(ValueError, match="SKILL.md"):
        load_skill_artifact(missing)

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "SKILL.md").write_text("skill\n", encoding="utf-8")
    (bundle / "alias.md").symlink_to(bundle / "SKILL.md")
    with pytest.raises(ValueError, match="symlinks"):
        load_skill_artifact(bundle)
