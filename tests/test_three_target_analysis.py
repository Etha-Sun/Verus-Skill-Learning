import csv
import json
import tempfile
import unittest
from pathlib import Path

from verus_self_evolve.three_target_analysis import analyze_three_targets


class ThreeTargetAnalysisTest(unittest.TestCase):
    def test_pairs_evidence_with_controls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            aggregates = root / "aggregates.jsonl"
            artifacts = [
                "evidence_artifact",
                "cross_trace_same_error",
                "cross_trace_any",
                "block_shuffled",
                "counterfactual_error",
                "irrelevant_archive",
                "empty_container",
            ]
            rows = []
            for target_index, target in enumerate(("action_primary", "patch_span", "full_proof"), start=1):
                for artifact_index, artifact in enumerate(artifacts):
                    rows.append(
                        {
                            "sample_id": "state-1",
                            "trace_id": "trace-1",
                            "prefix_id": "early-a1",
                            "target_type": target,
                            "artifact_type": artifact,
                            "target_sha256": f"hash-{target}",
                            "target_token_count": target_index,
                            "target_loglikelihood_ig_bits": (
                                10.0 if artifact == "evidence_artifact" else artifact_index
                            ),
                            "sequence_truncated": False,
                            "token_match_exact": artifact != "empty_container",
                            "intervention_token_count": 20 if artifact != "empty_container" else 4,
                            "prepared_intervention_token_count": 20 if artifact != "empty_container" else 4,
                        }
                    )
            aggregates.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

            out_dir = root / "analysis"
            summary = analyze_three_targets(aggregates, out_dir, expected_state_count=1)

            self.assertTrue(summary["integrity_gate"]["passed"])
            self.assertTrue(summary["integrity_gate"]["empty_container_excluded_from_matched_controls"])
            with (out_dir / "specific_state_gain.csv").open(encoding="utf-8") as handle:
                specific = list(csv.DictReader(handle))
            self.assertEqual(len(specific), 3)
            self.assertEqual(float(specific[0]["matched_control_mean_total_ig_bits"]), 3.0)
            self.assertEqual(float(specific[0]["specific_total_ig_bits"]), 7.0)
            self.assertAlmostEqual(float(specific[2]["specific_ig_bits_per_target_token"]), 7.0 / 3.0)
            with (out_dir / "control_summary.csv").open(encoding="utf-8") as handle:
                controls = list(csv.DictReader(handle))
            self.assertEqual(len(controls), 15)
            self.assertEqual(float(controls[0]["mean_evidence_minus_control_bits"]), 9.0)
            with (out_dir / "state_mapping.csv").open(encoding="utf-8") as handle:
                mapping = list(csv.DictReader(handle))
            self.assertEqual(mapping[0]["figure_label"], "S1")
            self.assertEqual(mapping[0]["prefix_id"], "early-a1")

    def test_rejects_missing_control(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            aggregates = root / "aggregates.jsonl"
            aggregates.write_text(
                json.dumps(
                    {
                        "sample_id": "state-1",
                        "trace_id": "trace-1",
                        "prefix_id": "early-a1",
                        "target_type": "action_primary",
                        "artifact_type": "evidence_artifact",
                        "target_sha256": "hash",
                        "target_token_count": 1,
                        "target_loglikelihood_ig_bits": 1.0,
                        "sequence_truncated": False,
                        "token_match_exact": True,
                        "intervention_token_count": 20,
                        "prepared_intervention_token_count": 20,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "missing"):
                analyze_three_targets(aggregates, root / "analysis", expected_state_count=1)


if __name__ == "__main__":
    unittest.main()
