from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE))

from global_skill_experiment.gate import (  # noqa: E402
    AggregateEvaluation,
    CandidateSnapshot,
    CommandAggregateEvaluator,
    GateConfig,
    HeldOutGateController,
    TaskEvaluation,
)


class FakeEvaluator:
    def __init__(self, values: list[AggregateEvaluation]) -> None:
        self.values = list(values)
        self.calls: list[tuple[Path, str]] = []

    def evaluate(self, skill_dir: Path, label: str) -> AggregateEvaluation:
        self.calls.append((skill_dir, label))
        return self.values.pop(0)


def make_skill(root: Path, name: str, body: str) -> Path:
    skill = root / name
    skill.mkdir()
    (skill / "SKILL.md").write_text(body, encoding="utf-8")
    return skill


def snapshot(path: Path, candidate_id: str = "candidate") -> CandidateSnapshot:
    return CandidateSnapshot(
        candidate_id=candidate_id,
        skill_dir=path,
        construction_method="semantic-reduce",
        unit_type="semantic-family-bundle",
        train_provenance_ids=("train-001",),
    )


def evaluation(
    success_ids: set[str],
    *,
    task_count: int = 20,
    total_tokens: int = 100,
    primary_uncached_tokens: int | None = None,
    reasoning_tokens: int = 40,
    wall_time_seconds: float = 10.0,
    coverage_complete: bool = True,
    fidelity_complete: bool = True,
    safety_complete: bool = True,
    unsafe_regression_count: int = 0,
    contract_violation_count: int = 0,
) -> AggregateEvaluation:
    if primary_uncached_tokens is None:
        primary_uncached_tokens = int(total_tokens * 0.7)
    tasks = tuple(
        TaskEvaluation(
            task_id=f"heldout-{index:02d}",
            success=f"heldout-{index:02d}" in success_ids,
            primary_uncached_tokens=primary_uncached_tokens,
            total_tokens=total_tokens,
            reasoning_tokens=reasoning_tokens,
            wall_time_seconds=wall_time_seconds,
        )
        for index in range(task_count)
    )
    return AggregateEvaluation(
        success_count=len(success_ids),
        task_count=task_count,
        primary_uncached_tokens=sum(task.primary_uncached_tokens for task in tasks),
        total_tokens=sum(task.total_tokens for task in tasks),
        reasoning_tokens=sum(task.reasoning_tokens for task in tasks),
        wall_time_seconds=sum(task.wall_time_seconds for task in tasks),
        coverage_complete=coverage_complete,
        fidelity_complete=fidelity_complete,
        safety_complete=safety_complete,
        unsafe_regression_count=unsafe_regression_count,
        contract_violation_count=contract_violation_count,
        task_metrics=tasks,
    )


def first_successes(count: int) -> set[str]:
    return {f"heldout-{index:02d}" for index in range(count)}


class HeldOutGateTests(unittest.TestCase):
    def test_enabled_gate_requires_explicit_frozen_m_core(self) -> None:
        with self.assertRaisesRegex(ValueError, "frozen M-core"):
            HeldOutGateController(GateConfig(enabled=True), FakeEvaluator([]))

    def test_m_core_can_be_evaluated_and_cached_before_candidate_construction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = snapshot(make_skill(root, "baseline", "m-core"), "m-core")
            evaluator = FakeEvaluator([evaluation(first_successes(8))])
            controller = HeldOutGateController(
                GateConfig(enabled=True, expected_task_count=20),
                evaluator,
                m_core_snapshot=baseline,
            )
            first = controller.evaluate_m_core()
            second = controller.evaluate_m_core()
            self.assertEqual(8, first.success_count)
            self.assertEqual(first, second)
            self.assertEqual([(baseline.skill_dir, "m-core__baseline")], evaluator.calls)

    def test_disabled_gate_directly_accepts_without_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator([])
            result = HeldOutGateController(GateConfig(enabled=False), evaluator).promote(
                incumbent, candidate
            )
            self.assertTrue(result.accepted)
            self.assertEqual("gate_disabled_direct_merge", result.reason)
            self.assertEqual(candidate, result.next_snapshot)
            self.assertEqual([], evaluator.calls)

    def test_success_gain_is_accepted_within_resource_caps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator(
                [evaluation(first_successes(8)), evaluation(first_successes(9))]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True, expected_task_count=20),
                evaluator,
                m_core_snapshot=incumbent,
            ).promote(incumbent, candidate)
            self.assertTrue(result.accepted)
            self.assertEqual("success_gain_within_resource_caps", result.reason)
            self.assertEqual(2, len(evaluator.calls))

    def test_success_gain_is_rejected_when_resource_cap_is_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator(
                [
                    evaluation(first_successes(8)),
                    evaluation(first_successes(9), total_tokens=125),
                ]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=incumbent
            ).promote(incumbent, candidate)
            self.assertFalse(result.accepted)
            self.assertEqual("success_gain_resource_cap_exceeded", result.reason)

    def test_success_regression_is_rejected_despite_large_efficiency_gain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator(
                [
                    evaluation(first_successes(9)),
                    evaluation(
                        first_successes(8),
                        total_tokens=10,
                        reasoning_tokens=4,
                        wall_time_seconds=1,
                    ),
                ]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=incumbent
            ).promote(incumbent, candidate)
            self.assertFalse(result.accepted)
            self.assertEqual("success_regression", result.reason)

    def test_equal_success_material_efficiency_gain_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator(
                [
                    evaluation(first_successes(8)),
                    evaluation(
                        first_successes(8),
                        total_tokens=80,
                        reasoning_tokens=30,
                        wall_time_seconds=8,
                    ),
                ]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=incumbent
            ).promote(incumbent, candidate)
            self.assertTrue(result.accepted)
            self.assertEqual("equal_success_material_efficiency_gain", result.reason)
            self.assertEqual(8, result.comparison["common_solved_count"])
            self.assertAlmostEqual(0.22, result.comparison["token_gain"])

    def test_equal_success_token_gain_below_fifteen_percent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator(
                [
                    evaluation(first_successes(8)),
                    evaluation(
                        first_successes(8),
                        total_tokens=100,
                        primary_uncached_tokens=62,
                        reasoning_tokens=35,
                        wall_time_seconds=10,
                    ),
                ]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=incumbent
            ).promote(incumbent, candidate)
            self.assertFalse(result.accepted)
            self.assertEqual("equal_success_no_material_efficiency_gain", result.reason)
            self.assertLess(result.comparison["token_gain"], 0.15)

    def test_equal_success_total_token_cap_rejects_fast_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator(
                [
                    evaluation(first_successes(8)),
                    evaluation(
                        first_successes(8),
                        total_tokens=120,
                        reasoning_tokens=40,
                        wall_time_seconds=5,
                    ),
                ]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=incumbent
            ).promote(incumbent, candidate)
            self.assertFalse(result.accepted)
            self.assertEqual("equal_success_resource_cap_exceeded", result.reason)

    def test_missing_usage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator(
                [
                    AggregateEvaluation(
                        8,
                        20,
                        coverage_complete=True,
                        fidelity_complete=True,
                        safety_complete=True,
                    ),
                    AggregateEvaluation(
                        8,
                        20,
                        coverage_complete=True,
                        fidelity_complete=True,
                        safety_complete=True,
                    ),
                ]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=incumbent
            ).promote(incumbent, candidate)
            self.assertFalse(result.accepted)
            self.assertEqual("missing_required_efficiency_metrics", result.reason)

    def test_equal_success_requires_common_solved_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator(
                [
                    evaluation({"heldout-00", "heldout-01", "heldout-02"}),
                    evaluation(
                        {"heldout-03", "heldout-04", "heldout-05"},
                        total_tokens=80,
                        reasoning_tokens=30,
                        wall_time_seconds=8,
                    ),
                ]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=incumbent
            ).promote(incumbent, candidate)
            self.assertFalse(result.accepted)
            self.assertEqual("equal_success_insufficient_common_solved", result.reason)
            self.assertEqual(
                {"0_to_0": 14, "0_to_1": 3, "1_to_0": 3, "1_to_1": 0},
                result.comparison["paired_transitions"],
            )

    def test_candidate_unsafe_regression_is_a_hard_veto(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            evaluator = FakeEvaluator(
                [
                    evaluation(first_successes(8)),
                    evaluation(first_successes(9), unsafe_regression_count=1),
                ]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=incumbent
            ).promote(incumbent, candidate)
            self.assertFalse(result.accepted)
            self.assertEqual("candidate_unsafe_regression", result.reason)

    def test_success_gain_cannot_ratchet_above_m_core_token_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            m_core = snapshot(make_skill(root, "m-core", "seed"), "m-core")
            candidate_one = snapshot(make_skill(root, "candidate-one", "one"), "one")
            candidate_two = snapshot(make_skill(root, "candidate-two", "two"), "two")
            evaluator = FakeEvaluator(
                [
                    evaluation(first_successes(8)),
                    evaluation(
                        first_successes(9),
                        total_tokens=115,
                        primary_uncached_tokens=75,
                        reasoning_tokens=45,
                    ),
                    evaluation(
                        first_successes(10),
                        total_tokens=132,
                        primary_uncached_tokens=80,
                        reasoning_tokens=50,
                    ),
                ]
            )
            controller = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=m_core
            )
            first = controller.promote(m_core, candidate_one)
            second = controller.promote(first.next_snapshot, candidate_two)
            self.assertTrue(first.accepted)
            self.assertFalse(second.accepted)
            self.assertEqual("success_gain_m_core_token_cap_exceeded", second.reason)
            self.assertAlmostEqual(1.32, second.comparison["total_token_ratio_to_m_core"])
            self.assertEqual(candidate_one, second.next_snapshot)

    def test_snapshot_hash_cache_reuses_rejected_incumbent_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate_one = snapshot(make_skill(root, "candidate-one", "new one"), "one")
            candidate_two = snapshot(make_skill(root, "candidate-two", "new two"), "two")
            baseline = evaluation(first_successes(8))
            evaluator = FakeEvaluator(
                [
                    baseline,
                    evaluation(first_successes(8)),
                    evaluation(
                        first_successes(8),
                        total_tokens=80,
                        reasoning_tokens=30,
                        wall_time_seconds=8,
                    ),
                ]
            )
            controller = HeldOutGateController(
                GateConfig(enabled=True), evaluator, m_core_snapshot=incumbent
            )
            first = controller.promote(incumbent, candidate_one)
            second = controller.promote(first.next_snapshot, candidate_two)
            self.assertFalse(first.accepted)
            self.assertTrue(second.accepted)
            self.assertEqual(3, len(evaluator.calls))

    def test_private_cache_and_aggregate_history_resume_across_controllers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            m_core = snapshot(make_skill(root, "m-core", "seed"), "m-core")
            candidate_one = snapshot(make_skill(root, "candidate-one", "one"), "one")
            candidate_two = snapshot(make_skill(root, "candidate-two", "two"), "two")
            history = root / "history.json"
            private_cache = root / "private-evaluations.json"
            first_evaluator = FakeEvaluator(
                [evaluation(first_successes(8)), evaluation(first_successes(8))]
            )
            first_controller = HeldOutGateController(
                GateConfig(enabled=True),
                first_evaluator,
                m_core_snapshot=m_core,
                history_path=history,
                evaluation_cache_path=private_cache,
            )
            first = first_controller.promote(m_core, candidate_one)
            self.assertFalse(first.accepted)
            self.assertEqual(2, len(first_evaluator.calls))

            second_evaluator = FakeEvaluator(
                [
                    evaluation(
                        first_successes(8),
                        total_tokens=80,
                        reasoning_tokens=30,
                        wall_time_seconds=8,
                    )
                ]
            )
            resumed = HeldOutGateController(
                GateConfig(enabled=True),
                second_evaluator,
                m_core_snapshot=m_core,
                history_path=history,
                evaluation_cache_path=private_cache,
            )
            second = resumed.promote(first.next_snapshot, candidate_two)
            self.assertTrue(second.accepted)
            self.assertEqual(1, len(second_evaluator.calls))
            history_payload = json.loads(history.read_text(encoding="utf-8"))
            self.assertEqual(2, len(history_payload["decisions"]))
            self.assertNotIn("heldout-00", history.read_text(encoding="utf-8"))
            self.assertIn("heldout-00", private_cache.read_text(encoding="utf-8"))

    def test_history_and_result_do_not_expose_heldout_task_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incumbent = snapshot(make_skill(root, "incumbent", "old"), "seed")
            candidate = snapshot(make_skill(root, "candidate", "new"))
            history = root / "gate-history.json"
            evaluator = FakeEvaluator(
                [
                    evaluation(first_successes(8)),
                    evaluation(
                        first_successes(8),
                        total_tokens=80,
                        reasoning_tokens=30,
                        wall_time_seconds=8,
                    ),
                ]
            )
            result = HeldOutGateController(
                GateConfig(enabled=True),
                evaluator,
                m_core_snapshot=incumbent,
                history_path=history,
            ).promote(incumbent, candidate)
            self.assertEqual((), result.candidate_evaluation.task_metrics)
            serialized = history.read_text(encoding="utf-8")
            self.assertNotIn("heldout-00", serialized)
            payload = json.loads(serialized)
            row = payload["decisions"][0]
            self.assertEqual(result.incumbent_hash, row["m_core_hash"])
            self.assertEqual(8, row["candidate_aggregate"]["success_count"])
            self.assertEqual(1120, row["candidate_aggregate"]["primary_uncached_tokens"])
            self.assertEqual(8, row["comparison"]["common_solved_count"])
            self.assertEqual(
                {"0_to_0": 12, "0_to_1": 0, "1_to_0": 0, "1_to_1": 8},
                row["comparison"]["paired_transitions"],
            )
            self.assertNotIn("per_task", row)
            self.assertNotIn("diagnostics", row)

    def test_current_codex_actor_summary_format_is_parsed(self) -> None:
        payload = {
            "completed_tasks": 2,
            "successes": 1,
            "coverage_complete": True,
            "fidelity": "V3_AUDITED",
            "safety_audit_complete": True,
            "usage": {
                "cache_miss_input_tokens": 80,
                "output_tokens": 50,
                "total_tokens": 300,
                "reasoning_tokens": 120,
            },
            "tasks": [
                {
                    "task_id": "private-a",
                    "success": True,
                    "timed_out": False,
                    "started_at": "2026-08-14T12:00:00+00:00",
                    "finished_at": "2026-08-14T12:00:10+00:00",
                    "usage": {
                        "cache_miss_input_tokens": 30,
                        "output_tokens": 20,
                        "total_tokens": 100,
                        "reasoning_tokens": 40,
                    },
                },
                {
                    "task_id": "private-b",
                    "success": False,
                    "timed_out": True,
                    "started_at": "2026-08-14T12:01:00+00:00",
                    "finished_at": "2026-08-14T12:01:20+00:00",
                    "usage": {
                        "cache_miss_input_tokens": 50,
                        "output_tokens": 30,
                        "total_tokens": 200,
                        "reasoning_tokens": 80,
                    },
                },
            ],
        }
        parsed = CommandAggregateEvaluator.parse_summary(payload)
        self.assertEqual(1, parsed.success_count)
        self.assertEqual(1, parsed.timeout_count)
        self.assertEqual(130, parsed.primary_uncached_tokens)
        self.assertEqual(300, parsed.total_tokens)
        self.assertEqual(120, parsed.reasoning_tokens)
        self.assertEqual(30.0, parsed.wall_time_seconds)
        self.assertTrue(parsed.coverage_complete)
        self.assertTrue(parsed.fidelity_complete)
        self.assertTrue(parsed.safety_complete)

    def test_config_validation_rejects_hackable_or_incoherent_weights(self) -> None:
        self.assertEqual(0.15, GateConfig().min_token_gain)
        self.assertEqual(1.10, GateConfig().max_total_token_ratio_to_m_core_equal_success)
        self.assertEqual(1.20, GateConfig().max_total_token_ratio_to_m_core_success_gain)
        with self.assertRaises(ValueError):
            GateConfig.from_mapping({"enabled": "false"})
        with self.assertRaises(ValueError):
            GateConfig.from_mapping(
                {"success_weight": 1.0, "token_weight": 0.0, "wall_time_weight": 0.0}
            )
        with self.assertRaises(ValueError):
            GateConfig.from_mapping(
                {"success_weight": 0.7, "token_weight": 0.2, "wall_time_weight": 0.2}
            )


class CommandEvaluatorResumeTests(unittest.TestCase):
    def test_incomplete_output_resumes_then_complete_summary_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = make_skill(root, "skill", "# Skill\n")
            counter = root / "invocations.txt"
            fail_code = (
                "import sys; from pathlib import Path; "
                "Path(sys.argv[2]).open(\"a\").write(\"fresh\\n\"); "
                "raise SystemExit(7)"
            )
            resume_code = (
                "import json,sys; from pathlib import Path; "
                "out=Path(sys.argv[1]); "
                "Path(sys.argv[2]).open(\"a\").write(\"resume\\n\"); "
                "payload={\"success_count\":1,\"task_count\":1,"
                "\"coverage_complete\":True,\"fidelity_complete\":True,"
                "\"safety_complete\":True,\"tasks\":[{\"task_id\":\"private-val-1\","
                "\"success\":True,\"wall_time_seconds\":1.0,\"usage\":{"
                "\"primary_uncached_tokens\":10,\"total_tokens\":20,"
                "\"reasoning_tokens\":5}}]}; "
                "(out/\"summary.json\").write_text(json.dumps(payload))"
            )
            evaluator = CommandAggregateEvaluator(
                argv=(
                    sys.executable,
                    "-c",
                    fail_code,
                    "{output_dir}",
                    str(counter),
                ),
                resume_argv=(
                    sys.executable,
                    "-c",
                    resume_code,
                    "{output_dir}",
                    str(counter),
                ),
                output_root=root / "actor",
            )
            with self.assertRaises(subprocess.CalledProcessError):
                evaluator.evaluate(skill, "candidate")

            parsed = evaluator.evaluate(skill, "candidate")
            self.assertEqual(1, parsed.success_count)
            self.assertEqual(("fresh", "resume"), tuple(counter.read_text().splitlines()))

            reused = evaluator.evaluate(skill, "candidate")
            self.assertEqual(parsed, reused)
            self.assertEqual(("fresh", "resume"), tuple(counter.read_text().splitlines()))

    def test_existing_incomplete_output_requires_explicit_resume_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = make_skill(root, "skill", "# Skill\n")
            incomplete = root / "actor" / "candidate"
            incomplete.mkdir(parents=True)
            evaluator = CommandAggregateEvaluator(
                argv=(sys.executable, "-c", "raise SystemExit(0)"),
                output_root=root / "actor",
            )
            with self.assertRaisesRegex(FileExistsError, "resume_argv"):
                evaluator.evaluate(skill, "candidate")


if __name__ == "__main__":
    unittest.main()
