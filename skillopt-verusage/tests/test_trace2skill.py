from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from skillopt_verusage.trace2skill import (
    CandidateSnapshot,
    copy_incumbent_snapshot,
    finalize_candidate_snapshot,
    hash_skill_tree,
    load_candidate_schedule,
    load_candidate_snapshot,
    run_candidate_sequence,
    semantic_content_sha256,
    sha256_file,
    write_candidate_schedule,
)


def _schedule(tmp_path: Path):
    core = tmp_path / "core"
    core.mkdir()
    (core / "SKILL.md").write_text("core\n", encoding="utf-8")
    memories = tmp_path / "memories.json"
    memories.write_text("{}\n", encoding="utf-8")
    payload = tmp_path / "unit.md"
    payload.write_text("add invariant\n", encoding="utf-8")
    path = tmp_path / "schedule.json"
    value = {
        "schema_version": "candidate-update-manifest-v1",
        "schedule_id": "test-schedule",
        "construction_method": "native-compressed",
        "unit_type": "native-compressed-bundle",
        "m_core": {"path": "core", "sha256": hash_skill_tree(core)},
        "shared_memories": {"path": "memories.json", "sha256": sha256_file(memories)},
        "construction": {
            "map_artifact_sha256": "a" * 64,
            "map_item_count": 1,
            "ordering_policy": "fixed",
        },
        "units": [
            {
                "unit_id": "unit-1",
                "order": 1,
                "construction_method": "native-compressed",
                "unit_type": "native-compressed-bundle",
                "payload_format": "semantic-patch-markdown-v1",
                "payload_path": "unit.md",
                "payload_sha256": sha256_file(payload),
                "content_sha256": semantic_content_sha256(payload.read_text()),
                "train_provenance_ids": ["train-1"],
                "source_item_ids": ["item-1"],
            }
        ],
    }
    write_candidate_schedule(value, path)
    return load_candidate_schedule(path)


def test_schedule_hash_and_snapshot_lineage_detect_mutation(tmp_path: Path) -> None:
    schedule = _schedule(tmp_path)
    incumbent = CandidateSnapshot(
        "m-core", schedule.m_core_path, "frozen", "m-core"
    )
    unit = schedule.units[0]
    skill_dir, metadata = copy_incumbent_snapshot(incumbent, tmp_path / "candidate")
    (skill_dir / "SKILL.md").write_text("candidate\n", encoding="utf-8")
    finalize_candidate_snapshot(
        incumbent=incumbent,
        unit=unit,
        skill_dir=skill_dir,
        metadata_path=metadata,
        m_core_hash=schedule.m_core_sha256,
    )
    load_candidate_snapshot(
        incumbent=incumbent,
        unit=unit,
        output_root=tmp_path / "candidate",
        m_core_hash=schedule.m_core_sha256,
    )
    (skill_dir / "SKILL.md").write_text("mutated\n", encoding="utf-8")
    with pytest.raises(ValueError, match="candidate_snapshot_hash"):
        load_candidate_snapshot(
            incumbent=incumbent,
            unit=unit,
            output_root=tmp_path / "candidate",
            m_core_hash=schedule.m_core_sha256,
        )


def test_schedule_rejects_manifest_mutation(tmp_path: Path) -> None:
    schedule = _schedule(tmp_path)
    value = json.loads(schedule.path.read_text(encoding="utf-8"))
    value["schedule_id"] = "changed"
    schedule.path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="schedule hash mismatch"):
        load_candidate_schedule(schedule.path)


def test_sequence_uses_retained_incumbent(tmp_path: Path) -> None:
    schedule = _schedule(tmp_path)
    initial = CandidateSnapshot("m-core", schedule.m_core_path, "frozen", "m-core")

    @dataclass
    class Decision:
        next_snapshot: CandidateSnapshot

    class Controller:
        def promote(self, incumbent, candidate):
            return Decision(candidate)

    def materialize(incumbent, unit, output_root):
        skill_dir, metadata = copy_incumbent_snapshot(incumbent, output_root)
        (skill_dir / "SKILL.md").write_text("candidate\n", encoding="utf-8")
        return finalize_candidate_snapshot(
            incumbent=incumbent,
            unit=unit,
            skill_dir=skill_dir,
            metadata_path=metadata,
            m_core_hash=schedule.m_core_sha256,
        )

    incumbent, decisions = run_candidate_sequence(
        schedule=schedule,
        initial_snapshot=initial,
        controller=Controller(),
        materializer=materialize,
        output_root=tmp_path / "sequence",
    )
    assert incumbent.candidate_id == "unit-1"
    assert len(decisions) == 1
