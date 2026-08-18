"""Translate/apply one frozen candidate unit against the retained incumbent."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from global_skill_experiment.candidates import (
    CandidateUnit,
    copy_incumbent_snapshot,
    finalize_candidate_snapshot,
)
from global_skill_experiment.gate import CandidateSnapshot


EXPERIMENT = Path(__file__).resolve().parents[2]
REPO = EXPERIMENT.parent
BASELINE_CODE = REPO / "trace2skill_verusage_baseline_test" / "code"
if str(BASELINE_CODE) not in sys.path:
    sys.path.insert(0, str(BASELINE_CODE))

from skill_evolver.parallel_evolving_agent import (  # noqa: E402
    ParallelSkillEvolver,
    Patch,
    PatchEdit,
)


def parse_semantic_unit(path: Path, marker_format: str = "bracket") -> Any:
    patches, feedback = ParallelSkillEvolver._extract_semantic_patch_blocks_with_feedback(
        path.read_text(encoding="utf-8"),
        semantic_item_marker_format=marker_format,
    )
    if len(patches) != 1:
        raise ValueError(f"candidate semantic unit must contain exactly one patch: {feedback}")
    return patches[0]


def parse_exact_patch(path: Path) -> Patch:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("edits"), list):
        raise ValueError("exact patch payload requires an edits array")
    edits: list[PatchEdit] = []
    for row in value["edits"]:
        if not isinstance(row, dict) or not row.get("file") or not row.get("op"):
            raise ValueError("every exact patch edit requires file and op")
        edits.append(
            PatchEdit(
                file=str(row["file"]),
                op=str(row["op"]),
                target_section=str(row.get("target_section", "")),
                target_text=str(row.get("target_text", "")),
                content=str(row.get("content", "")),
                old_text=str(row.get("old_text", "")),
                after_section=str(row.get("after_section", "")),
            )
        )
    return Patch(
        reasoning=str(value.get("reasoning", "frozen exact patch")),
        edits=edits,
        changelog_entries=list(map(str, value.get("changelog_entries", []))),
        raw_json=value,
    )


def materialize_candidate_unit(
    *,
    incumbent: CandidateSnapshot,
    unit: CandidateUnit,
    output_root: Path,
    m_core_hash: str,
    evolver: Any,
    validate_skill: bool = True,
) -> CandidateSnapshot:
    """Build a complete candidate without mutating the retained incumbent."""
    skill_dir, metadata_path = copy_incumbent_snapshot(incumbent, output_root)
    old_skill_dir = evolver.skill_dir
    old_nested_skill_dir = evolver._evolver.skill_dir
    old_output_dir = evolver.output_dir
    try:
        evolver.skill_dir = skill_dir
        evolver._evolver.skill_dir = skill_dir
        evolver.output_dir = output_root / "application_artifacts"
        state = evolver.read_skill_state()
        if unit.payload_format == "semantic-patch-markdown-v1":
            semantic = parse_semantic_unit(
                unit.payload_path,
                marker_format=evolver.semantic_item_marker_format,
            )
            translated = evolver.run_translation_phase_from_semantic(state, semantic)
        elif unit.payload_format == "exact-patch-json-v1":
            translated = parse_exact_patch(unit.payload_path)
        else:
            raise ValueError(f"unsupported candidate payload format: {unit.payload_format}")
        translated = Patch(
            reasoning=translated.reasoning,
            edits=evolver._sanitize_translated_edits(state, translated.edits),
            changelog_entries=translated.changelog_entries,
            batch_index=translated.batch_index,
            raw_json=translated.raw_json,
        )
        if not translated.edits:
            raise ValueError(f"candidate unit {unit.unit_id} translated to no applicable edits")
        evolver._save_translated_patch(translated)
        edits, _, _ = evolver.run_apply_phase_programmatic(state, translated)
        if not edits:
            raise ValueError(f"candidate unit {unit.unit_id} produced no skill snapshot edits")
        evolver._evolver.apply_edits(edits)
        if validate_skill:
            valid, message = evolver._evolver.validate_skill()
            if not valid:
                raise ValueError(
                    f"candidate unit {unit.unit_id} failed deterministic skill validation: {message}"
                )
        return finalize_candidate_snapshot(
            incumbent=incumbent,
            unit=unit,
            skill_dir=skill_dir,
            metadata_path=metadata_path,
            m_core_hash=m_core_hash,
        )
    finally:
        evolver.skill_dir = old_skill_dir
        evolver._evolver.skill_dir = old_nested_skill_dir
        evolver.output_dir = old_output_dir
