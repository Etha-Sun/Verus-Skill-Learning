from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = (
    REPO_ROOT
    / "trace2skill-verusage"
    / "vendor"
    / "trace2skill_verus"
)
sys.path.insert(0, str(RUNTIME_ROOT))

from skill_evolver.parallel_evolving_agent import (  # noqa: E402
    ParallelSkillEvolver,
    PatchEdit as ParallelPatchEdit,
)
from skill_evolver.skill_evolving_agent import (  # noqa: E402
    FileEdit,
    SkillEvolver,
)


@pytest.mark.parametrize(
    "relative_path",
    [
        "../../../../escaped.txt",
        "/tmp/trace2skill-escaped.md",
        "references/../escaped.md",
        "references/nested/escaped.md",
        "references/escaped.txt",
        "./SKILL.md",
    ],
)
def test_translated_edits_reject_unsafe_or_unsupported_paths(
    relative_path: str,
) -> None:
    edit = ParallelPatchEdit(file=relative_path, op="create", content="escaped")
    assert ParallelSkillEvolver._sanitize_translated_edits({}, [edit]) == []


def test_translated_edits_allow_skill_and_linked_markdown_reference() -> None:
    edits = [
        ParallelPatchEdit(
            file="SKILL.md",
            op="add_section",
            content="See [details](references/details.md).",
        ),
        ParallelPatchEdit(
            file="references/details.md",
            op="create",
            content="# Details\n",
        ),
    ]

    sanitized = ParallelSkillEvolver._sanitize_translated_edits(
        {"SKILL.md": "# Skill\n"},
        edits,
    )

    assert [edit.file for edit in sanitized] == [
        "SKILL.md",
        "references/details.md",
    ]


@pytest.mark.parametrize(
    "relative_path",
    [
        "../../../../escaped.txt",
        "/tmp/trace2skill-escaped.md",
    ],
)
def test_apply_edits_reject_paths_outside_skill_directory(
    tmp_path: Path,
    relative_path: str,
) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    evolver = SkillEvolver(
        client=None,
        skill_dir=skill_dir,
        verbose=False,
        parse_failure_dir=tmp_path / "parse_failures",
    )

    with pytest.raises(ValueError, match="skill edit"):
        evolver.apply_edits(
            [FileEdit(relative_path=relative_path, content="escaped", action="create")]
        )

    assert not (tmp_path / "escaped.txt").exists()


def test_apply_edits_reject_reference_symlink_escape(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    outside = tmp_path / "outside"
    skill_dir.mkdir()
    outside.mkdir()
    (skill_dir / "references").symlink_to(outside, target_is_directory=True)
    evolver = SkillEvolver(
        client=None,
        skill_dir=skill_dir,
        verbose=False,
        parse_failure_dir=tmp_path / "parse_failures",
    )

    with pytest.raises(ValueError, match="escapes the skill directory"):
        evolver.apply_edits(
            [
                FileEdit(
                    relative_path="references/escaped.md",
                    content="escaped",
                    action="create",
                )
            ]
        )

    assert not (outside / "escaped.md").exists()


def test_apply_edits_writes_allowed_markdown_reference(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    evolver = SkillEvolver(
        client=None,
        skill_dir=skill_dir,
        verbose=False,
        parse_failure_dir=tmp_path / "parse_failures",
    )

    evolver.apply_edits(
        [
            FileEdit(
                relative_path="references/details.md",
                content="# Details\n",
                action="create",
            )
        ]
    )

    assert (skill_dir / "references" / "details.md").read_text(
        encoding="utf-8"
    ) == "# Details\n"


def test_parallel_evolver_renders_literal_json_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    evolver = ParallelSkillEvolver(
        client=None,
        skill_dir=skill_dir,
        verbose=False,
    )

    assert '{"reasoning"' in evolver._map_system_prompt
