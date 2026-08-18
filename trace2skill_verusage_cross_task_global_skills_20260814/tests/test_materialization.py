from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
CODE = EXPERIMENT / "code"
BASELINE_CODE = EXPERIMENT.parent / "trace2skill_verusage_baseline_test" / "code"
sys.path.insert(0, str(CODE))
sys.path.insert(0, str(BASELINE_CODE))

from global_skill_experiment.candidates import (  # noqa: E402
    CandidateSchedule,
    CandidateUnit,
    run_candidate_sequence,
    semantic_content_sha256,
    sha256_file,
)
from global_skill_experiment.gate import (  # noqa: E402
    CandidateSnapshot,
    GateConfig,
    HeldOutGateController,
    hash_skill_tree,
)
from global_skill_experiment.materialization import (  # noqa: E402
    materialize_candidate_unit,
)
from skill_evolver.parallel_evolving_agent import (  # noqa: E402
    ParallelSkillEvolver,
    PatchEdit,
    _apply_patch_edit_to_content,
)
from skill_evolver.skill_evolving_agent import SkillEvolver  # noqa: E402


class NeverEvaluator:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, skill_dir: Path, label: str):
        self.calls += 1
        raise AssertionError("gate-disabled sequence invoked validation actor")


def offline_evolver(skill_dir: Path) -> ParallelSkillEvolver:
    evolver = object.__new__(ParallelSkillEvolver)
    evolver.skill_dir = skill_dir
    evolver.output_dir = None
    evolver.semantic_item_marker_format = "bracket"
    nested = object.__new__(SkillEvolver)
    nested.skill_dir = skill_dir
    nested.dry_run = False
    nested._files_created = set()
    nested._files_modified = set()
    evolver._evolver = nested
    return evolver


class MaterializationTests(unittest.TestCase):
    def test_replace_in_section_uses_unique_exact_old_text_fallback(self) -> None:
        content = (
            "### Full section heading\n\n"
            "1. Exact sentence to replace.\n\n"
            "### Next section\n"
            "Keep this.\n"
        )
        edit = PatchEdit(
            file="SKILL.md",
            op="replace_in_section",
            target_section="### Shortened section heading",
            old_text="1. Exact sentence to replace.",
            content="1. Replacement sentence.",
        )

        updated = _apply_patch_edit_to_content(content, edit)

        self.assertIn("1. Replacement sentence.", updated)
        self.assertNotIn("1. Exact sentence to replace.", updated)
        self.assertIn("### Next section\nKeep this.", updated)

    def test_json_continuation_recovers_complete_restarted_payload(self) -> None:
        complete = {
            "reasoning": "complete continuation",
            "edits": [
                {
                    "file": "references/patterns.md",
                    "op": "create",
                    "content": "# Patterns\n",
                },
                {
                    "file": "SKILL.md",
                    "op": "append_to_section",
                    "target_section": "## References",
                    "content": "See references/patterns.md",
                },
            ],
            "changelog_entries": [],
        }
        response = (
            "```json\n"
            '{"reasoning":"partial","edits":[{"file":"references/patterns.md",'
            '"op":"create","content":"cut off'
            "```json\n"
            + json.dumps(complete)
            + "\n```"
        )

        payloads, feedback = ParallelSkillEvolver._extract_json_payloads_with_feedback(
            response,
            "patch",
        )

        self.assertEqual("", feedback)
        self.assertEqual([complete], payloads)

    def test_malformed_nonempty_edits_are_not_recovered_as_empty(self) -> None:
        malformed = (
            '{"reasoning":"partial","edits":[BROKEN],'
            '"changelog_entries":[]}'
        )
        self.assertIsNone(
            ParallelSkillEvolver._heuristic_parse_patch_payload(malformed)
        )

    def test_gate_disabled_native_and_semantic_sequences_never_invoke_actor(self) -> None:
        for method, unit_type in (
            ("native-compressed", "native-compressed-bundle"),
            ("semantic-reduce", "semantic-family-bundle"),
        ):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                m_core = root / "m-core"
                m_core.mkdir()
                (m_core / "SKILL.md").write_text("# Core\n\nseed\n", encoding="utf-8")
                payload_path = root / "exact.json"
                payload_path.write_text(
                    json.dumps(
                        {
                            "reasoning": "offline fake",
                            "edits": [
                                {
                                    "file": "SKILL.md",
                                    "op": "add_section",
                                    "target_section": "## Added",
                                    "content": method,
                                }
                            ],
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                unit = CandidateUnit(
                    unit_id=f"{method}-0001",
                    order=1,
                    construction_method=method,
                    unit_type=unit_type,
                    family_id="family" if method == "semantic-reduce" else None,
                    payload_format="exact-patch-json-v1",
                    payload_path=payload_path,
                    payload_sha256=sha256_file(payload_path),
                    content_sha256=semantic_content_sha256(payload_path.read_text()),
                    train_provenance_ids=("train-a",),
                    source_item_ids=("map_0001_item_001",),
                )
                m_core_hash = hash_skill_tree(m_core)
                schedule = CandidateSchedule(
                    path=root / "schedule.json",
                    schedule_id=method,
                    construction_method=method,
                    unit_type=unit_type,
                    m_core_path=m_core,
                    m_core_sha256=m_core_hash,
                    shared_memories_path=root / "unused",
                    shared_memories_sha256="0" * 64,
                    construction={},
                    units=(unit,),
                    digest="0" * 64,
                )
                initial = CandidateSnapshot(
                    candidate_id="m-core",
                    skill_dir=m_core,
                    construction_method="semantic-v4-root",
                    unit_type="m-core",
                )
                evaluator = NeverEvaluator()
                controller = HeldOutGateController(GateConfig(enabled=False), evaluator)
                evolver = offline_evolver(m_core)

                def materializer(incumbent, candidate_unit, output_root):
                    return materialize_candidate_unit(
                        incumbent=incumbent,
                        unit=candidate_unit,
                        output_root=output_root,
                        m_core_hash=m_core_hash,
                        evolver=evolver,
                        validate_skill=False,
                    )

                final, decisions = run_candidate_sequence(
                    schedule=schedule,
                    initial_snapshot=initial,
                    controller=controller,
                    materializer=materializer,
                    output_root=root / "outputs",
                )
                self.assertTrue(decisions[0].accepted)
                self.assertEqual(0, evaluator.calls)
                self.assertIn(
                    method,
                    (final.skill_dir / "SKILL.md").read_text(encoding="utf-8"),
                )
                self.assertEqual("# Core\n\nseed\n", (m_core / "SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()
