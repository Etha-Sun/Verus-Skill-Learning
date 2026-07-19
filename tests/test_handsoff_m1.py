import json
import tempfile
import unittest
from pathlib import Path

from verus_self_evolve.handsoff_m1 import (
    KNOWN_MODELS,
    TRAIN_DIRECTORIES,
    characterize_trace,
    select_traces,
    write_selection,
)


class HandsOffM1Test(unittest.TestCase):
    def test_characterization_finds_domain_and_failure_features(self):
        features = characterize_trace(
            {"task_id": "seq_to_set_invariant"},
            "Verus cannot prove the loop invariant because an index is out of bounds.",
        )
        self.assertIn("sequence_set_map", features["motifs"])
        self.assertIn("invariant", features["motifs"])
        self.assertIn("invariant_failure", features["error_families"])
        self.assertIn("bounds_or_index", features["error_families"])

    def test_selection_is_balanced_unique_and_ignores_sealed_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            index = 0
            for model in KNOWN_MODELS:
                for directory in TRAIN_DIRECTORIES:
                    for duplicate in range(4):
                        index += 1
                        relative = f"{directory}/results/task_{index}.log"
                        path = root / relative
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text("cannot prove invariant bounds for seq! and to_set")
                        rows.append(
                            {
                                "trace_id": f"{index:04d}",
                                "relative_log_path": relative,
                                "directory_group": directory,
                                "split": "train",
                                "model": model,
                                "variant": "standard" if duplicate % 2 else "advanced",
                                "task_id": f"task_{index}",
                                "normalized_task_id": f"task_{index}",
                                "source": {"normalized_code_sha256": f"source_{index}"},
                                "verified": {"path": f"verified_{index}.rs"},
                                "usage": {"available": False},
                            }
                        )
            rows.append(
                {
                    "trace_id": "sealed",
                    "relative_log_path": "verified-nrkernel/results/secret.log",
                    "directory_group": "verified-nrkernel",
                    "split": "test",
                    "model": "claude-opus-4.5",
                    "verified": {"path": "secret.rs"},
                }
            )
            broken_relative = "verified-anvil/results/broken.log"
            (root / broken_relative).parent.mkdir(parents=True, exist_ok=True)
            (root / broken_relative).write_text("trigger checker repair transition")
            rows.append(
                {
                    "trace_id": "0000",
                    "relative_log_path": broken_relative,
                    "directory_group": "verified-anvil",
                    "split": "train",
                    "model": "claude-opus-4.5",
                    "variant": "deletion",
                    "task_id": "broken",
                    "normalized_task_id": "broken",
                    "source": {"normalized_code_sha256": "broken_source"},
                    "verified": {"path": None},
                    "usage": {"available": False},
                }
            )
            selected = select_traces(rows, root, per_stratum=3)
            self.assertEqual(len(selected), 30)
            self.assertNotIn("broken", {r["trace_id"] for r in selected})
            self.assertEqual(len({r["normalized_task_id"] for r in selected}), 30)
            self.assertEqual(
                len({r["source"]["normalized_code_sha256"] for r in selected}), 30
            )
            for model in KNOWN_MODELS:
                self.assertEqual(sum(r["model"] == model for r in selected), 6)
            for directory in TRAIN_DIRECTORIES:
                self.assertEqual(
                    sum(r["directory_group"] == directory for r in selected), 15
                )
            manifest = root / "manifest.jsonl"
            manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
            summary = write_selection(
                manifest, root, root / "selection", per_stratum=3
            )
            self.assertEqual(summary["selection_count"], 30)
            self.assertFalse(summary["method_evidence"])


if __name__ == "__main__":
    unittest.main()
