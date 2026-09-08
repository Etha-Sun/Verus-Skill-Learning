import unittest

from verus_self_evolve.trajectory_progress import (
    patch_f1_scores,
    verifier_gated_patch_progress,
    verifier_state,
)


BASELINE = """verus! {
proof fn target() {
}
}
"""

REFERENCE = """verus! {
proof fn target() {
    assert(a);
    assert(b);
}
}
"""


class TrajectoryProgressTest(unittest.TestCase):
    def test_patch_f1_has_fixed_endpoints(self):
        start = patch_f1_scores(BASELINE, BASELINE, REFERENCE)
        final = patch_f1_scores(BASELINE, REFERENCE, REFERENCE)

        self.assertEqual(start["patch_f1"], 0.0)
        self.assertEqual(final["patch_f1"], 1.0)

    def test_patch_f1_rewards_partial_reference_patch(self):
        partial = """verus! {
proof fn target() {
    assert(a);
}
}
"""
        score = patch_f1_scores(BASELINE, partial, REFERENCE)

        self.assertGreater(score["patch_f1"], 0.0)
        self.assertLess(score["patch_f1"], 1.0)

    def test_patch_f1_penalizes_extraneous_edits(self):
        clean = """verus! {
proof fn target() {
    assert(a);
}
}
"""
        wandering = """verus! {
proof fn target() {
    assert(a);
    assert(unrelated);
}
}
"""

        clean_score = patch_f1_scores(BASELINE, clean, REFERENCE)
        wandering_score = patch_f1_scores(BASELINE, wandering, REFERENCE)

        self.assertEqual(clean_score["patch_recall"], wandering_score["patch_recall"])
        self.assertGreater(clean_score["patch_f1"], wandering_score["patch_f1"])

    def test_whitespace_only_changes_do_not_count_as_patch_atoms(self):
        spaced = REFERENCE.replace("    assert(a);", "        assert(a);")
        score = patch_f1_scores(BASELINE, spaced, REFERENCE)

        self.assertEqual(score["patch_f1"], 1.0)

    def test_verifier_gate_has_three_ordered_tiers(self):
        compile_failure = verifier_state("error: cannot find value `x`")
        proof_failure = verifier_state(
            "verification results:: 4 verified, 1 errors\n"
        )
        verified = verifier_state("verification results:: 5 verified, 0 errors\n")

        self.assertLess(compile_failure["tier_rank"], proof_failure["tier_rank"])
        self.assertLess(proof_failure["tier_rank"], verified["tier_rank"])

    def test_verifier_gate_overrides_patch_f1_regression_mistake(self):
        passing_source = """verus! {
proof fn target() {
    assert(a && b);
}
}
"""
        failing_but_reference_like = REFERENCE
        passing = verifier_gated_patch_progress(
            BASELINE,
            passing_source,
            REFERENCE,
            "verification results:: 1 verified, 0 errors\n",
        )
        regressed = verifier_gated_patch_progress(
            BASELINE,
            failing_but_reference_like,
            REFERENCE,
            "verification results:: 0 verified, 1 errors\n",
        )

        self.assertGreater(
            regressed["patch"]["patch_f1"], passing["patch"]["patch_f1"]
        )
        self.assertGreater(passing["progress_key"], regressed["progress_key"])

    def test_reference_equal_to_baseline_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must differ"):
            patch_f1_scores(BASELINE, BASELINE, BASELINE)


if __name__ == "__main__":
    unittest.main()
