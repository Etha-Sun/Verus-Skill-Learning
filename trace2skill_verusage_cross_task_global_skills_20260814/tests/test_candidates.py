from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


EXPERIMENT = Path(__file__).resolve().parents[1]
CODE = EXPERIMENT / "code"
sys.path.insert(0, str(CODE))

from global_skill_experiment.candidates import (  # noqa: E402
    CandidateSchedule,
    CandidateUnit,
    SCHEMA_VERSION,
    copy_incumbent_snapshot,
    finalize_candidate_snapshot,
    load_candidate_schedule,
    run_candidate_sequence,
    semantic_content_sha256,
    sha256_file,
    write_candidate_schedule,
)
from global_skill_experiment.gate import (  # noqa: E402
    AggregateEvaluation,
    CandidateSnapshot,
    GateConfig,
    HeldOutGateController,
    TaskEvaluation,
    hash_skill_tree,
)


class FakeEvaluator:
    def __init__(self, values: list[AggregateEvaluation]) -> None:
        self.values = list(values)
        self.calls = 0

    def evaluate(self, skill_dir: Path, label: str) -> AggregateEvaluation:
        self.calls += 1
        return self.values.pop(0)


def evaluation(total_tokens: int, wall_time: float) -> AggregateEvaluation:
    tasks = tuple(
        TaskEvaluation(
            task_id=f"val-{index}",
            success=index < 4,
            primary_uncached_tokens=total_tokens,
            total_tokens=total_tokens,
            reasoning_tokens=total_tokens // 4,
            wall_time_seconds=wall_time,
        )
        for index in range(5)
    )
    return AggregateEvaluation(
        success_count=4,
        task_count=5,
        primary_uncached_tokens=sum(task.primary_uncached_tokens for task in tasks),
        total_tokens=sum(task.total_tokens for task in tasks),
        reasoning_tokens=sum(task.reasoning_tokens for task in tasks),
        wall_time_seconds=sum(task.wall_time_seconds for task in tasks),
        coverage_complete=True,
        fidelity_complete=True,
        safety_complete=True,
        task_metrics=tasks,
    )


def make_skill(path: Path, body: str = "# Seed\n") -> Path:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(body, encoding="utf-8")
    return path


class CandidateScheduleTests(unittest.TestCase):
    def test_written_manifest_validates_against_schema_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            m_core = make_skill(root / "m-core")
            memories = root / "memories.json"
            memories.write_text('[{"instance_id":"train-a"}]\n', encoding="utf-8")
            payload_file = root / "family.md"
            payload_file.write_text("semantic family\n", encoding="utf-8")
            manifest = root / "schedule.json"
            payload = {
                "schema_version": SCHEMA_VERSION,
                "schedule_id": "semantic-test",
                "construction_method": "semantic-reduce",
                "unit_type": "semantic-family-bundle",
                "m_core": {"path": str(m_core), "sha256": hash_skill_tree(m_core)},
                "shared_memories": {"path": str(memories), "sha256": sha256_file(memories)},
                "construction": {
                    "map_artifact_sha256": "1" * 64,
                    "map_item_count": 1,
                    "ordering_policy": "family order",
                },
                "units": [
                    {
                        "unit_id": "semantic-0001-family-a",
                        "order": 1,
                        "construction_method": "semantic-reduce",
                        "unit_type": "semantic-family-bundle",
                        "family_id": "family-a",
                        "payload_format": "semantic-patch-markdown-v1",
                        "payload_path": str(payload_file),
                        "payload_sha256": sha256_file(payload_file),
                        "content_sha256": semantic_content_sha256(payload_file.read_text()),
                        "train_provenance_ids": ["train-a"],
                        "source_item_ids": ["map_0001_item_001"],
                    }
                ],
            }
            write_candidate_schedule(payload, manifest)
            schema = json.loads(
                (EXPERIMENT / "schemas" / "candidate_update_manifest.schema.json").read_text()
            )
            jsonschema.validate(json.loads(manifest.read_text()), schema)
            loaded = load_candidate_schedule(manifest)
            self.assertEqual("family-a", loaded.units[0].family_id)

    def test_semantic_manifest_rejects_cross_family_duplicate_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            m_core = make_skill(root / "m-core")
            memories = root / "memories.json"
            memories.write_text("[]\n", encoding="utf-8")
            unit_file = root / "unit.md"
            unit_file.write_text("unit\n", encoding="utf-8")
            common = dict(
                construction_method="semantic-reduce",
                unit_type="semantic-family-bundle",
                payload_format="semantic-patch-markdown-v1",
                payload_path=unit_file,
                payload_sha256=sha256_file(unit_file),
                content_sha256=semantic_content_sha256("unit\n"),
                train_provenance_ids=("train-a",),
                source_item_ids=("map_0001_item_001",),
            )
            schedule = CandidateSchedule(
                path=root / "schedule.json",
                schedule_id="duplicate",
                construction_method="semantic-reduce",
                unit_type="semantic-family-bundle",
                m_core_path=m_core,
                m_core_sha256=hash_skill_tree(m_core),
                shared_memories_path=memories,
                shared_memories_sha256=sha256_file(memories),
                construction={},
                units=(
                    CandidateUnit(unit_id="one", order=1, family_id="a", **common),
                    CandidateUnit(unit_id="two", order=2, family_id="b", **common),
                ),
                digest="0" * 64,
            )
            all_items = [item for unit in schedule.units for item in unit.source_item_ids]
            self.assertNotEqual(len(all_items), len(set(all_items)))

    def test_second_candidate_builds_on_retained_incumbent_after_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            m_core = make_skill(root / "m-core")
            payload_one = root / "one.md"
            payload_two = root / "two.md"
            payload_one.write_text("one", encoding="utf-8")
            payload_two.write_text("two", encoding="utf-8")
            units = tuple(
                CandidateUnit(
                    unit_id=name,
                    order=index,
                    construction_method="semantic-reduce",
                    unit_type="semantic-family-bundle",
                    family_id=name,
                    payload_format="semantic-patch-markdown-v1",
                    payload_path=path,
                    payload_sha256=sha256_file(path),
                    content_sha256=semantic_content_sha256(path.read_text()),
                    train_provenance_ids=(f"train-{name}",),
                    source_item_ids=(f"map_000{index}_item_001",),
                )
                for index, (name, path) in enumerate(
                    (("one", payload_one), ("two", payload_two)), start=1
                )
            )
            schedule = CandidateSchedule(
                path=root / "schedule.json",
                schedule_id="lineage",
                construction_method="semantic-reduce",
                unit_type="semantic-family-bundle",
                m_core_path=m_core,
                m_core_sha256=hash_skill_tree(m_core),
                shared_memories_path=root / "unused",
                shared_memories_sha256="0" * 64,
                construction={},
                units=units,
                digest="0" * 64,
            )
            initial = CandidateSnapshot(
                candidate_id="m-core",
                skill_dir=m_core,
                construction_method="semantic-v4-root",
                unit_type="m-core",
            )

            def materialize(incumbent: CandidateSnapshot, unit: CandidateUnit, out: Path) -> CandidateSnapshot:
                skill, metadata = copy_incumbent_snapshot(incumbent, out)
                skill_file = skill / "SKILL.md"
                skill_file.write_text(
                    skill_file.read_text(encoding="utf-8") + f"{unit.unit_id}\n",
                    encoding="utf-8",
                )
                return finalize_candidate_snapshot(
                    incumbent=incumbent,
                    unit=unit,
                    skill_dir=skill,
                    metadata_path=metadata,
                    m_core_hash=schedule.m_core_sha256,
                )

            evaluator = FakeEvaluator(
                [evaluation(100, 10), evaluation(100, 10), evaluation(80, 8)]
            )
            controller = HeldOutGateController(
                GateConfig(enabled=True, min_common_solved_count=3),
                evaluator,
                m_core_snapshot=initial,
            )
            final, decisions = run_candidate_sequence(
                schedule=schedule,
                initial_snapshot=initial,
                controller=controller,
                materializer=materialize,
                output_root=root / "candidates",
            )
            self.assertFalse(decisions[0].accepted)
            self.assertTrue(decisions[1].accepted)
            body = (final.skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("one", body)
            self.assertIn("two", body)
            lineage = json.loads((final.skill_dir.parent / "snapshot_manifest.json").read_text())
            self.assertEqual(schedule.m_core_sha256, lineage["parent_snapshot_hash"])
            self.assertEqual(schedule.m_core_sha256, lineage["m_core_hash"])
            self.assertEqual(3, evaluator.calls)


if __name__ == "__main__":
    unittest.main()
