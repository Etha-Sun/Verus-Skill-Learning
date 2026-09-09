import unittest

from verus_self_evolve.proof_progress import (
    align_tool_calls_to_output_tokens,
    extract_verifier_calls,
    function_body,
    greedy_prune_proof_lines,
    proof_line_coverage,
)


def _codex_event(index, raw_type, item, digest="a"):
    return {
        "event_index": index,
        "actor": "codex",
        "type": "tool_result" if raw_type == "item.completed" else "tool_call",
        "candidate_sha256": digest,
        "data": {"raw_codex_event": {"type": raw_type, "item": item}},
    }


class ProofProgressTest(unittest.TestCase):
    def test_extracts_compound_and_repeated_verifier_calls_once_each(self):
        command = "apply_patch ...; /tools/verus candidate.rs"
        events = [
            _codex_event(
                1,
                "item.completed",
                {
                    "id": "item_1",
                    "type": "command_execution",
                    "command": command,
                    "aggregated_output": "verification results:: 0 verified, 1 errors",
                },
            ),
            {
                "event_index": 2,
                "actor": "verus",
                "type": "verifier",
                "candidate_sha256": "a",
                "data": {"source_tool_call_id": "item_1"},
            },
            _codex_event(
                3,
                "item.completed",
                {
                    "id": "item_2",
                    "type": "command_execution",
                    "command": "/tools/verus candidate.rs",
                    "aggregated_output": "verification results:: 1 verified, 0 errors",
                },
            ),
            {
                "event_index": 4,
                "actor": "verus",
                "type": "verifier",
                "candidate_sha256": "a",
                "data": {"passed": True, "stdout": "verification results:: 1 verified, 0 errors"},
            },
        ]

        calls = extract_verifier_calls(events)

        self.assertEqual(len(calls), 3)
        self.assertEqual([row["candidate_sha256"] for row in calls], ["a", "a", "a"])
        self.assertEqual([row["verifier"]["tier_rank"] for row in calls], [1, 2, 2])

    def test_aligns_tool_calls_from_ledger_input_deltas(self):
        events = [
            _codex_event(
                1,
                "item.started",
                {"id": "item_1", "type": "command_execution"},
            ),
            _codex_event(
                2,
                "item.started",
                {"id": "item_2", "type": "command_execution"},
            ),
            _codex_event(
                3,
                "item.started",
                {"id": "item_3", "type": "file_change"},
            ),
        ]
        ledger = [
            {
                "input_item_types": ["message"],
                "attempts": [{"usage": {"completion_tokens": 10}}],
            },
            {
                "input_item_types": ["message", "function_call", "function_call_output"],
                "attempts": [{"usage": {"completion_tokens": 20}}],
            },
            {
                "input_item_types": [
                    "message",
                    "function_call",
                    "function_call_output",
                    "function_call",
                    "function_call_output",
                ],
                "attempts": [{"usage": {"completion_tokens": 30}}],
            },
        ]

        aligned = align_tool_calls_to_output_tokens(events, ledger)

        self.assertEqual(
            aligned["tool_call_output_tokens"],
            {"item_1": 10, "item_2": 30, "item_3": 60},
        )
        self.assertEqual(aligned["total_output_tokens"], 60)

    def test_function_body_and_line_coverage(self):
        source = "verus! {\nproof fn target() {\n    assert(a);\n}\n}\n"
        current = "    assert(a);\n    assert(extra);\n"

        body = function_body(source, "target")
        score = proof_line_coverage(current, body)

        self.assertEqual(body, "    assert(a);\n")
        self.assertEqual(score["coverage"], 1.0)

    def test_greedy_pruning_is_sequential_and_verifier_gated(self):
        baseline = "verus! {\nproof fn target() {\n}\n}\n"
        final = (
            "verus! {\nproof fn target() {\n"
            "    assert(needed);\n"
            "    assert(redundant);\n"
            "}\n}\n"
        )

        def verify(source):
            passed = "assert(needed);" in source
            return passed, "pass" if passed else "fail"

        result = greedy_prune_proof_lines(baseline, final, "target", verify)

        self.assertIn("assert(needed);", result["pruned_source"])
        self.assertNotIn("assert(redundant);", result["pruned_source"])
        self.assertEqual(result["summary"]["removed_lines"], 1)
        self.assertEqual(result["summary"]["assert_share_of_removed_lines"], 1.0)

    def test_greedy_pruning_revisits_earlier_dependencies(self):
        baseline = "verus! {\nproof fn target() {\n}\n}\n"
        final = (
            "verus! {\nproof fn target() {\n"
            "    let obsolete = true;\n"
            "    assert(obsolete);\n"
            "}\n}\n"
        )

        def verify(source):
            passed = not (
                "assert(obsolete);" in source and "let obsolete = true;" not in source
            )
            return passed, "pass" if passed else "fail"

        result = greedy_prune_proof_lines(baseline, final, "target", verify)

        self.assertNotIn("obsolete", result["pruned_source"])
        self.assertEqual(result["summary"]["removed_lines"], 2)
        self.assertGreaterEqual(result["summary"]["pruning_passes"], 2)

    def test_greedy_pruning_can_remove_a_balanced_block(self):
        baseline = "verus! {\nproof fn target() {\n}\n}\n"
        final = (
            "verus! {\nproof fn target() {\n"
            "    if redundant {\n"
            "    }\n"
            "    assert(needed);\n"
            "}\n}\n"
        )

        def verify(source):
            balanced = source.count("{") == source.count("}")
            passed = balanced and "assert(needed);" in source
            return passed, "pass" if passed else "fail"

        result = greedy_prune_proof_lines(baseline, final, "target", verify)

        self.assertNotIn("redundant", result["pruned_source"])
        self.assertIn("assert(needed);", result["pruned_source"])
        self.assertEqual(result["summary"]["removed_lines"], 2)
        self.assertEqual(
            {row["unit_kind"] for row in result["removed_line_records"]},
            {"balanced_block"},
        )


if __name__ == "__main__":
    unittest.main()
