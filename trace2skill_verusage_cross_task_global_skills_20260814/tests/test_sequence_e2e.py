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
    CommandAggregateEvaluator,
    GateConfig,
    HeldOutGateController,
    hash_skill_tree,
)
from global_skill_experiment.materialization import materialize_candidate_unit  # noqa: E402
from skill_evolver.parallel_evolving_agent import ParallelSkillEvolver  # noqa: E402
from skill_evolver.skill_evolving_agent import SkillEvolver  # noqa: E402


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


FAKE_ACTOR = """#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--skill-dir", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
parser.add_argument("--invocations", type=Path, required=True)
parser.add_argument("--resume", action="store_true")
args = parser.parse_args()
body = (args.skill_dir / "SKILL.md").read_text()
if "bad-one" in body:
    successes, tokens = 4, 120
elif "good-two" in body:
    successes, tokens = 5, 110
else:
    successes, tokens = 4, 100
args.invocations.parent.mkdir(parents=True, exist_ok=True)
with args.invocations.open("a", encoding="utf-8") as handle:
    handle.write(args.skill_dir.parent.name + "\\n")
tasks = [
    {
        "task_id": f"private-val-{index}",
        "success": index < successes,
        "wall_time_seconds": 1.0,
        "usage": {
            "primary_uncached_tokens": tokens,
            "total_tokens": tokens,
            "reasoning_tokens": tokens // 4,
        },
    }
    for index in range(5)
]
payload = {
    "success_count": successes,
    "task_count": 5,
    "coverage_complete": True,
    "fidelity_complete": True,
    "safety_complete": True,
    "tasks": tasks,
}
(args.output_dir / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
"""


class FakeCommandSequenceTests(unittest.TestCase):
    def test_promotion_rejection_cache_and_full_sequence_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            m_core = root / "m-core"
            m_core.mkdir()
            (m_core / "SKILL.md").write_text("# Core\n\nseed\n", encoding="utf-8")
            actor = root / "fake_actor.py"
            actor.write_text(FAKE_ACTOR, encoding="utf-8")
            invocations = root / "invocations.txt"

            units = []
            for index, (name, marker) in enumerate(
                (("one", "bad-one"), ("two", "good-two")), start=1
            ):
                payload = root / f"{name}.json"
                payload.write_text(
                    json.dumps(
                        {
                            "edits": [
                                {
                                    "file": "SKILL.md",
                                    "op": "add_section",
                                    "target_section": f"## {name}",
                                    "content": marker,
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                units.append(
                    CandidateUnit(
                        unit_id=name,
                        order=index,
                        construction_method="semantic-reduce",
                        unit_type="semantic-family-bundle",
                        family_id=name,
                        payload_format="exact-patch-json-v1",
                        payload_path=payload,
                        payload_sha256=sha256_file(payload),
                        content_sha256=semantic_content_sha256(payload.read_text()),
                        train_provenance_ids=(f"train-{name}",),
                        source_item_ids=(f"map-{index}",),
                    )
                )

            m_core_hash = hash_skill_tree(m_core)
            schedule = CandidateSchedule(
                path=root / "schedule.json",
                schedule_id="fake-command-e2e",
                construction_method="semantic-reduce",
                unit_type="semantic-family-bundle",
                m_core_path=m_core,
                m_core_sha256=m_core_hash,
                shared_memories_path=root / "unused",
                shared_memories_sha256="0" * 64,
                construction={},
                units=tuple(units),
                digest="0" * 64,
            )
            initial = CandidateSnapshot(
                candidate_id="m-core",
                skill_dir=m_core,
                construction_method="semantic-v4-root",
                unit_type="m-core",
            )
            actor_argv = (
                sys.executable,
                str(actor),
                "--skill-dir",
                "{skill_dir}",
                "--output-dir",
                "{output_dir}",
                "--invocations",
                str(invocations),
            )
            history = root / "gate_history.json"
            private_cache = root / "private_cache.json"
            candidate_root = root / "candidates"
            evolver = offline_evolver(m_core)

            def materializer(incumbent, unit, output_root):
                return materialize_candidate_unit(
                    incumbent=incumbent,
                    unit=unit,
                    output_root=output_root,
                    m_core_hash=m_core_hash,
                    evolver=evolver,
                    validate_skill=False,
                )

            evaluator = CommandAggregateEvaluator(
                argv=actor_argv,
                resume_argv=actor_argv + ("--resume",),
                output_root=root / "actor",
            )
            controller = HeldOutGateController(
                GateConfig(enabled=True, expected_task_count=5),
                evaluator,
                m_core_snapshot=initial,
                history_path=history,
                evaluation_cache_path=private_cache,
            )
            final, decisions = run_candidate_sequence(
                schedule=schedule,
                initial_snapshot=initial,
                controller=controller,
                materializer=materializer,
                output_root=candidate_root,
            )
            self.assertEqual((False, True), tuple(row.accepted for row in decisions))
            self.assertEqual("two", final.candidate_id)
            final_body = (final.skill_dir / "SKILL.md").read_text()
            self.assertNotIn("bad-one", final_body)
            self.assertIn("good-two", final_body)
            first_invocations = tuple(invocations.read_text().splitlines())
            self.assertEqual(3, len(first_invocations))

            resumed_evaluator = CommandAggregateEvaluator(
                argv=actor_argv,
                resume_argv=actor_argv + ("--resume",),
                output_root=root / "actor",
            )
            resumed_controller = HeldOutGateController(
                GateConfig(enabled=True, expected_task_count=5),
                resumed_evaluator,
                m_core_snapshot=initial,
                history_path=history,
                evaluation_cache_path=private_cache,
            )
            resumed_final, resumed_decisions = run_candidate_sequence(
                schedule=schedule,
                initial_snapshot=initial,
                controller=resumed_controller,
                materializer=materializer,
                output_root=candidate_root,
            )
            self.assertEqual("two", resumed_final.candidate_id)
            self.assertEqual((False, True), tuple(row.accepted for row in resumed_decisions))
            self.assertEqual(first_invocations, tuple(invocations.read_text().splitlines()))

            public_text = history.read_text(encoding="utf-8")
            private_text = private_cache.read_text(encoding="utf-8")
            self.assertEqual(2, len(json.loads(public_text)["decisions"]))
            self.assertNotIn("private-val-", public_text)
            self.assertIn("private-val-", private_text)
            second_lineage = json.loads(
                (candidate_root / "0002_two" / "snapshot_manifest.json").read_text()
            )
            self.assertEqual(m_core_hash, second_lineage["parent_snapshot_hash"])


if __name__ == "__main__":
    unittest.main()
