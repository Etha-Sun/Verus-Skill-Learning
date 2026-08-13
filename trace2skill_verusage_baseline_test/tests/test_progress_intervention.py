from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from react_agent import LLMClient
from react_agent.agent import AgentStep
from react_agent.converter import ParsedAction
from react_agent.models import Message, ModelSettings
from verus_agent.loop_control import (
    PROGRESS_PROTOCOL_PREFIX,
    ExplicitCompletionReActConverter,
    ProgressInterventionClient,
    VerusLoopGuard,
    create_reasoning_progress_tool,
)
from verus_agent.workspace import prepare_workspace


class RecordingClient(LLMClient):
    def __init__(self):
        self.messages = None

    def chat(self, messages, settings=None):
        self.messages = messages
        return "ACTION: TASK_COMPLETE"

    async def chat_async(self, messages, settings=None):
        return self.chat(messages, settings)


def workspace(root: Path):
    source = root / "source.rs"
    source.write_text("\n".join(f"line {i}" for i in range(30)) + "\n")
    return prepare_workspace(source, root / "run")


def step(name: str, arguments: dict, observation: str, turn: int = 1):
    return AgentStep(
        turn=turn,
        action=ParsedAction(name=name, arguments=arguments),
        observation=observation,
    )


def progress_fields():
    return {
        "observed_fact": (
            "The cited tool output reports that the current proof obligation remains unproved."
        ),
        "working_hypothesis": (
            "The available evidence may indicate that a supporting proof bridge is insufficient."
        ),
        "next_test": (
            "Inspect the cited source and test the smallest targeted proof change against Verus."
        ),
    }


class ProgressInterventionTests(unittest.TestCase):
    def test_pre_edit_exploration_is_not_stopped_and_guard_arms_after_cycle(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            for i in range(15):
                guard(
                    step(
                        "search_file",
                        {"query": f"symbol_{i}"},
                        f"new evidence {i}",
                        i + 1,
                    )
                )
            self.assertFalse(guard.summary()["no_progress_guard_armed"])
            self.assertEqual(guard.summary()["steps_without_material_progress_at_end"], 0)

            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 16))
            self.assertFalse(guard.summary()["no_progress_guard_armed"])
            guard(step("run_verus", {}, "error: after first edit", 17))
            self.assertTrue(guard.summary()["no_progress_guard_armed"])
            self.assertEqual(guard.summary()["edit_verus_cycles"], 1)

            for i in range(9):
                guard(step("read_file", {"line": i}, f"different {i}", i + 18))
            with self.assertRaisesRegex(RuntimeError, "10 consecutive tool turns"):
                guard(step("read_file", {"line": 9}, "different 9", 27))

    def test_real_edit_resets_armed_no_progress_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: after first edit", 2))
            for i in range(9):
                guard(step("search_file", {"query": f"before_{i}"}, f"evidence {i}", i + 3))
            ws.replace_text("line 29", "changed line 29")
            guard(step("replace_text", {}, "ok", 12))
            self.assertEqual(guard.summary()["steps_without_material_progress_at_end"], 0)
            for i in range(9):
                guard(step("read_file", {"line": i}, f"different {i}", i + 13))
            self.assertEqual(guard.summary()["steps_without_material_progress_at_end"], 9)

    def test_changed_verus_diagnostic_resets_armed_no_progress_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: after first edit", 2))
            for i in range(9):
                guard(step("search_file", {"query": f"q{i}"}, f"evidence {i}", i + 3))
            guard(step("run_verus", {}, "error: different obligation", 12))
            self.assertEqual(guard.summary()["steps_without_material_progress_at_end"], 0)

    def test_evidence_backed_reasoning_progress_extends_budget_by_five(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: first obligation\nerror: second obligation")
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: changed obligation", 2))
            guard(step("read_file", {"line": 12}, "new invariant evidence", 3))

            accepted = guard.record_proof_progress(
                obstacle="The remaining well-formedness conjunct is still failing.",
                evidence_turns=[2, 3],
                **progress_fields(),
                next_action="edit_lines",
            )
            guard(
                step(
                    "record_proof_progress",
                    {
                        "obstacle": "The remaining well-formedness conjunct is still failing.",
                        "evidence_turns": [2, 3],
                        **progress_fields(),
                        "next_action": "edit_lines",
                    },
                    accepted,
                    4,
                )
            )
            for index in range(12):
                guard(
                    step(
                        "read_file",
                        {"line": index + 13},
                        f"distinct follow-up evidence {index}",
                        index + 5,
                    )
                )
            self.assertEqual(guard.summary()["steps_without_material_progress_at_end"], 14)
            self.assertEqual(guard.summary()["reasoning_progress_accepted"], 1)
            self.assertEqual(guard.summary()["max_adaptive_no_progress_limit_seen"], 15)
            event = guard.reasoning_progress_events[0]
            self.assertEqual(event["progress_kind"], "confirmed_verifier_progress")
            self.assertEqual(event["extension_turns"], 5)
            self.assertIn("primary_error_count_decreased", event["verifier_diffs"][0]["confirmed_reasons"])
            with self.assertRaisesRegex(RuntimeError, "bounded per-stage allowance"):
                guard(step("read_file", {"line": 29}, "final evidence", 17))

    def test_armed_guard_injects_low_frequency_mandatory_progress_reminders(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")

            for i in range(8):
                guard(step("read_file", {"line": i}, f"pre-edit evidence {i}", i + 1))
            self.assertNotIn("[Progress", guard.consume_intervention() or "")

            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 9))
            guard(step("run_verus", {}, "error: changed obligation", 10))
            guard.consume_intervention()

            for i in range(4):
                guard(step("read_file", {"line": i + 1}, f"new evidence {i}", i + 11))
            self.assertIsNone(guard.consume_intervention())

            guard(step("read_file", {"line": 5}, "new evidence midpoint", 15))
            midpoint = guard.consume_intervention()
            self.assertIn("[Progress Check 5/10]", midpoint)
            self.assertIn("MUST be record_proof_progress", midpoint)
            self.assertLess(len(midpoint), 600)

            for i in range(2):
                guard(step("read_file", {"line": i + 6}, f"later evidence {i}", i + 16))
            self.assertIsNone(guard.consume_intervention())
            guard(step("read_file", {"line": 8}, "deadline evidence", 18))
            deadline = guard.consume_intervention()
            self.assertIn("[Progress Deadline 8/10]", deadline)
            self.assertLess(len(deadline), 500)
            self.assertEqual(guard.summary()["reasoning_progress_reminders"], 2)

    def test_current_changed_verus_diagnostic_is_valid_progress_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")

            diagnostic = "error[E0608]: cannot index into a Map value"
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, diagnostic, 2))

            accepted = guard.record_proof_progress(
                obstacle="The changed verifier diagnostic reports invalid Map indexing.",
                evidence_turns=[2],
                **progress_fields(),
                next_action="search_file",
            )

            self.assertIn("Reasoning progress accepted", accepted)
            event = guard.reasoning_progress_events[0]
            self.assertEqual(event["evidence_turns"], [2])
            self.assertNotIn("evidence_snippets", event)
            self.assertEqual(event["evidence_sources"][0]["action"], "run_verus")
            self.assertEqual(
                event["evidence_sources"][0]["observation_chars"], len(diagnostic)
            )
            self.assertEqual(
                len(event["evidence_sources"][0]["observation_sha256"]), 64
            )
            self.assertEqual(guard.summary()["reasoning_progress_accepted"], 1)
            self.assertEqual(event["progress_kind"], "hypothesis_refinement")
            self.assertEqual(event["extension_turns"], 3)
            self.assertIn("observed_fact", event)
            self.assertIn("working_hypothesis", event)
            self.assertIn("next_test", event)
            self.assertNotIn("conclusion", event)

    def test_host_blocks_non_progress_action_until_required_report_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: changed obligation", 2))
            converter = ExplicitCompletionReActConverter(guard=guard)

            blocked = converter.parse_response(
                'Action:\n{"name":"read_file","arguments":{"path":"candidate.rs"}}'
            )
            self.assertTrue(blocked.is_format_error)
            self.assertIn("Action 'read_file' was not executed", blocked.error_message)
            self.assertIn("evidence_turns: [2]", blocked.error_message)
            self.assertEqual(guard.summary()["progress_action_enforcements"], 1)
            self.assertTrue(guard.summary()["required_progress_action_pending_at_end"])

            protocol_step = AgentStep(
                turn=3,
                is_format_error=True,
                observation=blocked.error_message,
            )
            guard(protocol_step)
            self.assertEqual(guard.summary()["format_errors"], 0)

            with self.assertRaisesRegex(ValueError, r"must be cited.*evidence_turns: \[2\]"):
                guard.record_proof_progress(
                    obstacle="The verifier now reports a different concrete obstacle.",
                    evidence_turns=[1],
                    **progress_fields(),
                    next_action="read_file",
                )

            accepted = guard.record_proof_progress(
                obstacle="The verifier now reports a different concrete obstacle.",
                evidence_turns=[2],
                **progress_fields(),
                next_action="read_file",
            )
            self.assertIn("Reasoning progress accepted", accepted)
            self.assertFalse(guard.summary()["required_progress_action_pending_at_end"])

            allowed = converter.parse_response(
                'Action:\n{"name":"read_file","arguments":{"path":"candidate.rs"}}'
            )
            self.assertTrue(allowed.is_action)

    def test_host_stops_after_three_ignored_mandatory_progress_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: changed obligation", 2))
            converter = ExplicitCompletionReActConverter(guard=guard)
            response = 'Action:\n{"name":"search_file","arguments":{"query":"x"}}'

            self.assertTrue(converter.parse_response(response).is_format_error)
            self.assertTrue(converter.parse_response(response).is_format_error)
            with self.assertRaisesRegex(RuntimeError, "ignoring the mandatory"):
                converter.parse_response(response)

    def test_changed_diagnostic_intervention_exposes_exact_run_verus_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws, skill_navigation_enabled=True)
            guard.set_initial_diagnostic("error: initial")

            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: changed obligation", 2))

            intervention = guard.consume_intervention()
            self.assertIn("run_verus Action turn 2", intervention)
            self.assertIn("evidence_turns: [2]", intervention)

    def test_stale_evidence_error_identifies_current_stage_and_latest_verus_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")
            guard(step("read_file", {"line": 1}, "old supporting evidence", 1))
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 2))
            guard(step("run_verus", {}, "error: changed obligation", 3))

            with self.assertRaisesRegex(
                ValueError,
                r"start at 3; the latest eligible run_verus Action turn is 3.*evidence_turns: \[3\]",
            ):
                guard.record_proof_progress(
                    obstacle="The remaining postcondition is the current proof obstacle.",
                    evidence_turns=[1, 3],
                    **progress_fields(),
                    next_action="read_file",
                )

    def test_progress_tool_schema_requests_turn_ids_and_exact_next_action(self):
        with tempfile.TemporaryDirectory() as temp:
            guard = VerusLoopGuard(workspace(Path(temp)))
            schema = create_reasoning_progress_tool(guard).get_params_schema()

            self.assertIn("evidence_turns", schema["properties"])
            self.assertIn("observed_fact", schema["properties"])
            self.assertIn("working_hypothesis", schema["properties"])
            self.assertIn("next_test", schema["properties"])
            self.assertNotIn("conclusion", schema["properties"])
            self.assertNotIn("evidence_snippets", schema["properties"])
            self.assertEqual(schema["properties"]["evidence_turns"]["type"], "array")
            self.assertIn(
                "One or two integer Action turn IDs",
                schema["properties"]["evidence_turns"]["description"],
            )
            self.assertIn(
                "immediately preceding run_verus Action turn",
                schema["properties"]["evidence_turns"]["description"],
            )
            self.assertIn(
                "Exact tool name",
                schema["properties"]["next_action"]["description"],
            )

    def test_reasoning_progress_rejects_missing_or_repeated_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: changed obligation", 2))
            with self.assertRaisesRegex(ValueError, "does not exist"):
                guard.record_proof_progress(
                    obstacle="A concrete proof obligation remains after the edit.",
                    evidence_turns=[2, 999],
                    **progress_fields(),
                    next_action="edit_lines",
                )
            guard(step("read_file", {"line": 4}, "specific invariant", 3))
            guard.record_proof_progress(
                obstacle="A concrete proof obligation remains after the edit.",
                evidence_turns=[2, 3],
                **progress_fields(),
                next_action="edit_lines",
            )
            with self.assertRaisesRegex(ValueError, "already used"):
                guard.record_proof_progress(
                    obstacle="A concrete proof obligation remains after the edit.",
                    evidence_turns=[2, 3],
                    **progress_fields(),
                    next_action="edit_lines",
                )
            self.assertEqual(guard.summary()["reasoning_progress_rejected"], 2)

    def test_progress_report_rejects_falsehood_claim_in_observed_fact(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: changed obligation", 2))
            fields = progress_fields()
            fields["observed_fact"] = (
                "The failed assertion proves that the state invariant is false."
            )
            with self.assertRaisesRegex(ValueError, "unproved, not false or violated"):
                guard.record_proof_progress(
                    obstacle="The verifier still reports an unproved state invariant.",
                    evidence_turns=[2],
                    next_action="read_file",
                    **fields,
                )

    def test_progress_report_accepts_literal_cannot_prove_diagnostic(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(
                step(
                    "run_verus",
                    {},
                    "error: postcondition not satisfied\n"
                    "note: cannot prove that there exists values that satisfy "
                    "the condition of the choose expression",
                    2,
                )
            )
            fields = progress_fields()
            fields["observed_fact"] = (
                "The cited run_verus output reports 'postcondition not satisfied' "
                "and 'cannot prove that there exists values that satisfy the "
                "condition of the choose expression'."
            )
            accepted = guard.record_proof_progress(
                obstacle="The existential witness obligation remains unproved.",
                evidence_turns=[2],
                next_action="lookup_vstd_symbol",
                **fields,
            )
            self.assertIn("Reasoning progress accepted", accepted)

    def test_progress_report_still_rejects_affirmative_proves_that_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: changed obligation", 2))
            fields = progress_fields()
            fields["observed_fact"] = (
                "The failed obligation proves that the proposed witness is invalid."
            )
            with self.assertRaisesRegex(ValueError, "unproved, not false or violated"):
                guard.record_proof_progress(
                    obstacle="The existential witness obligation remains unproved.",
                    evidence_turns=[2],
                    next_action="lookup_vstd_symbol",
                    **fields,
                )

    def test_reasoning_progress_is_capped_at_two_extensions_per_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = workspace(Path(temp))
            guard = VerusLoopGuard(ws)
            guard.set_initial_diagnostic("error: initial")
            ws.replace_text("line 0", "changed line 0")
            guard(step("replace_text", {}, "ok", 1))
            guard(step("run_verus", {}, "error: changed obligation", 2))
            guard(step("read_file", {"line": 3}, "first invariant", 3))
            guard.record_proof_progress(
                obstacle="The first remaining invariant has a concrete mismatch.",
                evidence_turns=[2, 3],
                **progress_fields(),
                next_action="read_file",
            )
            guard(step("read_file", {"line": 4}, "second invariant", 4))
            guard.record_proof_progress(
                obstacle="The second remaining invariant has a concrete mismatch.",
                evidence_turns=[4],
                **progress_fields(),
                next_action="edit_lines",
            )
            with self.assertRaisesRegex(ValueError, "extension limit"):
                guard.record_proof_progress(
                    obstacle="A third remaining invariant has a concrete mismatch.",
                    evidence_turns=[4],
                    **progress_fields(),
                    next_action="edit_lines",
                )
            self.assertEqual(guard.summary()["maximum_adaptive_no_progress_limit"], 20)
            self.assertEqual(guard.summary()["max_adaptive_no_progress_limit_seen"], 16)

    def test_skill_navigation_checkpoint_is_enabled_only_for_skill_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            guard = VerusLoopGuard(
                workspace(Path(temp)),
                skill_navigation_enabled=True,
                skill_navigation_interval=3,
            )
            for index in range(3):
                guard(step("read_file", {"line": index}, f"evidence {index}", index + 1))
            message = guard.consume_intervention()
            self.assertIn("[Skill Procedure Check]", message)
            self.assertIn("root SKILL.md procedure", message)
            self.assertEqual(guard.summary()["skill_navigation_checkpoints"], 1)

        with tempfile.TemporaryDirectory() as temp:
            guard = VerusLoopGuard(
                workspace(Path(temp)),
                skill_navigation_enabled=False,
                skill_navigation_interval=3,
            )
            for index in range(3):
                guard(step("read_file", {"line": index}, f"evidence {index}", index + 1))
            self.assertIsNone(guard.consume_intervention())

    def test_two_fruitless_searches_trigger_skill_navigation_check(self):
        with tempfile.TemporaryDirectory() as temp:
            guard = VerusLoopGuard(
                workspace(Path(temp)),
                skill_navigation_enabled=True,
            )
            guard(step("search_file", {"query": "first"}, "0 result(s)", 1))
            guard(step("search_file", {"query": "second"}, "0 result(s)", 2))
            message = guard.consume_intervention()
            self.assertIn("repeated empty or failed searches", message)

    def test_same_tool_error_class_stops_but_diverse_errors_do_not(self):
        with tempfile.TemporaryDirectory() as temp:
            guard = VerusLoopGuard(workspace(Path(temp)))
            for i, name in enumerate(("read_file", "search_file", "lookup_vstd_symbol")):
                guard(step(name, {"value": i}, f"Error: different class {name}", i + 1))
            self.assertEqual(guard.summary()["tool_errors"], 3)

        with tempfile.TemporaryDirectory() as temp:
            guard = VerusLoopGuard(workspace(Path(temp)))
            with self.assertRaisesRegex(RuntimeError, "same tool failure repeated 4"):
                for i in range(4):
                    guard(
                        step(
                            "search_file",
                            {"query": f"q{i}"},
                            f"Error executing tool 'search_file': invalid bound {i}",
                            i + 1,
                        )
                    )

    def test_identical_successful_action_and_observation_stops_at_five(self):
        with tempfile.TemporaryDirectory() as temp:
            guard = VerusLoopGuard(workspace(Path(temp)))
            with self.assertRaisesRegex(RuntimeError, "identical action and observation 5"):
                for i in range(5):
                    guard(step("read_file", {"path": "candidate.rs"}, "same", i + 1))

    def test_pending_soft_intervention_is_added_only_to_request_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            guard = VerusLoopGuard(
                workspace(Path(temp)), max_steps_without_material_progress=20
            )
            for i in range(10):
                guard(step("search_file", {"query": f"q{i}"}, f"evidence {i}", i + 1))
            inner = RecordingClient()
            client = ProgressInterventionClient(inner, guard)
            original = [Message(role="user", content="Observation: evidence")]
            client.chat(original, ModelSettings())
            self.assertEqual(original[-1].content, "Observation: evidence")
            self.assertIn("[Host Progress Intervention]", inner.messages[-1].content)
            self.assertIn("Exploration remains allowed", inner.messages[-1].content)


if __name__ == "__main__":
    unittest.main()
