import json
import argparse
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from verus_self_evolve.ig_analysis import CONTROL_ARTIFACTS, REFERENCE_ARTIFACT, analyze, analyze_aggregates


class IgAnalysisTest(unittest.TestCase):
    def test_specific_gain_uses_mean_of_controls(self):
        artifacts = {
            "evidence_artifact": 1.0,
            "cross_trace_same_error": 0.2,
            "block_shuffled": 0.4,
            "irrelevant_style": -0.3,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregates.jsonl"
            with path.open("w", encoding="utf-8") as handle:
                for artifact, pmi in artifacts.items():
                    handle.write(json.dumps({
                        "sample_id": "s1",
                        "trace_id": "t1",
                        "target_type": "action_primary",
                        "artifact_type": artifact,
                        "decision_pmi_bits": pmi,
                        "intervention_token_count": 10,
                        "context_token_count_baseline": 100,
                        "context_token_count_artifact": 110,
                    }) + "\n")
            _, _, _, specific = analyze_aggregates(
                path,
                control_artifacts=("cross_trace_same_error", "block_shuffled", "irrelevant_style"),
            )
        self.assertEqual(len(specific), 1)
        self.assertAlmostEqual(specific[0]["specific_gain_bits"], 0.9)

    def test_integrity_gate_rejects_delta_and_target_mismatch(self):
        rows = []
        for state in range(6):
            for artifact in (REFERENCE_ARTIFACT, *CONTROL_ARTIFACTS):
                rows.append({
                    "case_id": f"s{state}-{artifact}",
                    "sample_id": f"s{state}",
                    "trace_id": f"t{state // 2}",
                    "target_type": "action_primary",
                    "artifact_type": artifact,
                    "decision_pmi_bits": 0.1,
                    "intervention_token_count": 10,
                    "prepared_intervention_token_count": 10,
                    "context_token_count_baseline": 100,
                    "context_token_count_artifact": 110,
                    "candidate_count": 22,
                    "action_accepted": True,
                    "token_match_exact": True,
                    "option_map_sha256": f"map-{state}",
                    "prompt_format": "chat_direct",
                    "serialized_target": "A",
                    "observed_action_text": "case_analysis",
                })
        args = argparse.Namespace(
            aggregates="",
            out_dir="",
            reference_artifact=REFERENCE_ARTIFACT,
            control_artifacts=list(CONTROL_ARTIFACTS),
            expected_state_count=6,
            expected_candidate_count=22,
            expected_prompt_format="chat_direct",
            action_distributions=None,
        )
        with tempfile.TemporaryDirectory() as tmp:
            args.aggregates = str(Path(tmp) / "aggregates.jsonl")
            args.out_dir = str(Path(tmp) / "analysis")
            def write_rows():
                Path(args.aggregates).write_text(
                    "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
                )
            rows[0]["intervention_token_count"] = 9
            write_rows()
            with patch.dict("os.environ", {"VERUS_SKILL_RUN_ROOT": tmp}):
                with self.assertRaises(ValueError):
                    analyze(args)
                rows[0]["intervention_token_count"] = 10
                rows[0]["serialized_target"] = "B"
                write_rows()
                with self.assertRaises(ValueError):
                    analyze(args)

    def test_candidate_raw_mass_diagnostic_uses_unnormalized_scores(self):
        rows = []
        distributions = []
        for state in range(6):
            for artifact in (REFERENCE_ARTIFACT, *CONTROL_ARTIFACTS):
                case_id = f"s{state}-{artifact}"
                rows.append({
                    "case_id": case_id,
                    "sample_id": f"s{state}",
                    "trace_id": f"t{state // 2}",
                    "target_type": "action_primary",
                    "artifact_type": artifact,
                    "decision_pmi_bits": 0.1,
                    "intervention_token_count": 10,
                    "prepared_intervention_token_count": 10,
                    "context_token_count_baseline": 100,
                    "context_token_count_artifact": 110,
                    "candidate_count": 22,
                    "action_accepted": True,
                    "token_match_exact": True,
                    "option_map_sha256": f"map-{state}",
                    "prompt_format": "chat_direct",
                    "serialized_target": "A",
                    "observed_action_text": "case_analysis",
                })
                distributions.append({
                    "case_id": case_id,
                    "sample_id": f"s{state}",
                    "artifact_type": artifact,
                    "baseline_log_scores": {"A": math.log(1e-10), "B": math.log(2e-10)},
                    "artifact_log_scores": {"A": math.log(2e-10), "B": math.log(3e-10)},
                })
        with tempfile.TemporaryDirectory() as tmp:
            aggregate_path = Path(tmp) / "aggregates.jsonl"
            distribution_path = Path(tmp) / "action_distributions.jsonl"
            out_dir = Path(tmp) / "analysis"
            aggregate_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            distribution_path.write_text(
                "".join(json.dumps(row) + "\n" for row in distributions), encoding="utf-8"
            )
            with patch.dict("os.environ", {"VERUS_SKILL_RUN_ROOT": tmp}):
                analyze(argparse.Namespace(
                    aggregates=str(aggregate_path),
                    action_distributions=str(distribution_path),
                    out_dir=str(out_dir),
                    reference_artifact=REFERENCE_ARTIFACT,
                    control_artifacts=list(CONTROL_ARTIFACTS),
                    expected_state_count=6,
                    expected_candidate_count=22,
                    expected_prompt_format="chat_direct",
                ))
            summary = json.loads((out_dir / "analysis_summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["candidate_mass_diagnostic"]["all_below_1e_6"])
            self.assertAlmostEqual(summary["candidate_mass_diagnostic"]["minimum"], 3e-10)
            self.assertAlmostEqual(summary["candidate_mass_diagnostic"]["maximum"], 5e-10)
            self.assertTrue((out_dir / "candidate_raw_mass.csv").exists())


if __name__ == "__main__":
    unittest.main()
