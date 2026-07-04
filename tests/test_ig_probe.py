import unittest

from verus_self_evolve.ig_probe import (
    _action_options,
    _artifact_text,
    _artifact_conditioned_context,
    _canonical_action,
    _evidence_artifact,
    _length_matched_neutral,
    _match_artifact_intervention,
    _permuted_action_options,
    parse_attempts,
    _scoring_context,
)


class IgProbeTest(unittest.TestCase):
    def setUp(self):
        self.prefix = {
            "target_error": "AssertFail",
            "error_text": "assertion failed at line 10",
            "history_actions": "uselemma|case_analysis",
            "history_errors": "AssertFail|AssertFail",
        }

    def test_action_options_are_deterministic(self):
        key_to_action, action_to_key = _action_options(["uselemma", "case_analysis", "uselemma"])
        self.assertEqual(key_to_action, {"A": "case_analysis", "B": "uselemma"})
        self.assertEqual(action_to_key["uselemma"], "B")

    def test_per_sample_option_permutation_is_reproducible(self):
        first, _ = _permuted_action_options(["uselemma", "case_analysis", "compute"], "sample-a", 7)
        second, _ = _permuted_action_options(["compute", "uselemma", "case_analysis"], "sample-a", 7)
        self.assertEqual(first, second)

    def test_neutral_control_matches_reference_word_count(self):
        reference = _artifact_text(self.prefix, "trace_rationale")
        neutral = _length_matched_neutral(reference)
        self.assertEqual(len(reference.split()), len(neutral.split()))
        self.assertNotIn("AssertFail", neutral)

    def test_action_aliases_are_canonicalized(self):
        self.assertEqual(_canonical_action("case-analysis"), "case_analysis")

    def test_attempt_acceptance_is_parsed(self):
        attempts = parse_attempts(
            "Repair attempt 1/1\nTarget error: AssertFail\n"
            "'primary_action': 'case_analysis'\nAction accepted\n"
        )
        self.assertTrue(attempts[0].accepted)

    def test_wrong_error_control_changes_diagnosis(self):
        wrong = _artifact_text(self.prefix, "wrong_error_rationale")
        self.assertNotIn("`AssertFail`", wrong)

    def test_choice_prompt_records_all_options(self):
        prompt = _scoring_context(
            "state",
            "action_primary",
            "choices",
            action_options={"A": "case_analysis", "B": "uselemma"},
        )
        self.assertIn("A. case_analysis", prompt)
        self.assertIn("B. uselemma", prompt)
        self.assertTrue(prompt.endswith("Option:"))

    def test_json_action_prompt_lists_labels_and_schema(self):
        prompt = _scoring_context(
            "state",
            "action_primary",
            "json_action",
            action_options={"A": "case_analysis", "B": "uselemma"},
        )
        self.assertIn("case_analysis, uselemma", prompt)
        self.assertIn('{"action":"<primary_action>"}', prompt)
        self.assertNotIn("A. case_analysis", prompt)

    def test_action_context_does_not_include_current_action_or_final_code(self):
        prefix = {
            "state_text": "Selected error text: assertion failed",
            "prefix_code_path": "/path/that/does/not/exist",
        }
        prompt = _scoring_context(prefix["state_text"], "action_primary", "explicit")
        self.assertNotIn("case_analysis", prompt)
        self.assertNotIn("final verified", prompt.lower())

    def test_evidence_artifact_does_not_read_target_action_or_final_proof(self):
        prefix = {
            **self.prefix,
            "primary_action": "SECRET_TARGET_ACTION",
            "final_code_path": "SECRET_FINAL_PROOF",
            "prefix_code_path": "/path/that/does/not/exist",
        }
        artifact = _evidence_artifact(prefix)
        self.assertNotIn("SECRET_TARGET_ACTION", artifact)
        self.assertNotIn("SECRET_FINAL_PROOF", artifact)

    def test_control_intervention_is_exactly_matched(self):
        class CharacterTokenizer:
            def encode(self, text, add_special_tokens=False):
                return [ord(char) for char in text]

            def decode(self, token_ids):
                return "".join(chr(token_id) for token_id in token_ids)

            def apply_chat_template(self, messages, tokenize, add_generation_prompt):
                return [1, 2] + self.encode(messages[0]["content"])

        tokenizer = CharacterTokenizer()
        make_context = lambda text: _artifact_conditioned_context(
            "state", text, "control", "action_primary", "explicit", None
        )
        baseline = _scoring_context("state", "action_primary", "explicit")
        baseline_count = len(tokenizer.apply_chat_template(
            [{"role": "user", "content": baseline}], tokenize=True, add_generation_prompt=True
        ))
        reference_delta = len(make_context("reference text")) - len(baseline)
        _, _, matched_delta = _match_artifact_intervention(
            tokenizer, "short", reference_delta, make_context, baseline_count, "chat"
        )
        self.assertEqual(matched_delta, reference_delta)


if __name__ == "__main__":
    unittest.main()
