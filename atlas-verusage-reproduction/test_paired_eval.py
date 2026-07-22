from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from classify_eval import strict_response_validity, validate_pair_contract


MODULE_PATH = Path(__file__).with_name("prepare_paired_eval.py")
SPEC = importlib.util.spec_from_file_location("prepare_paired_eval", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PairedEvalTest(unittest.TestCase):
    def test_strict_response_validity_rejects_missing_fields_and_unknown_code(self):
        valid = {"A.1"}
        complete = {
            "code": "A.1",
            "label": "label",
            "evidence": "evidence",
            "confidence": 0.5,
            "recovery_hint": "hint",
        }
        self.assertEqual(strict_response_validity(complete, valid), (True, True))
        self.assertEqual(
            strict_response_validity({**complete, "code": "Z.9"}, valid),
            (True, False),
        )
        incomplete = dict(complete)
        incomplete.pop("evidence")
        self.assertEqual(strict_response_validity(incomplete, valid), (False, True))

    def test_freezes_balanced_eight_trace_contract_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            taxonomy = root / "taxonomy.json"
            taxonomy.write_text(
                json.dumps(
                    {
                        "full_layer": {
                            "category_a": [{"code": f"A.{i}"} for i in range(6)],
                            "category_b": [{"code": f"B.{i}"} for i in range(11)],
                            "category_c": [{"code": f"C.{i}"} for i in range(11)],
                        }
                    }
                )
            )
            traces = []
            source_records = []
            for index in range(8):
                outcome = "FAILED" if index < 4 else "TIMEOUT"
                model = ("claude", "claude-s4", "gpt5", "o4mini")[index % 4]
                problem_id = f"{model}:task_{index}.rs"
                traces.append(
                    {
                        "problem_id": problem_id,
                        "raw_trajectory": "trace",
                        "metadata": {
                            "outcome": outcome,
                            "llm_name": model,
                            "project": "P",
                            "source_ref": f"source/{index}",
                        },
                    }
                )
                source_records.append(
                    {
                        "problem_id": problem_id,
                        "status": outcome,
                        "source_sha256": str(index) * 64,
                    }
                )
            eval_path = root / "eval.jsonl"
            eval_path.write_text("".join(json.dumps(row) + "\n" for row in traces))
            source_manifest = root / "manifest.json"
            source_manifest.write_text(json.dumps({"eval": {"records": source_records}}))
            out = root / "out"
            manifest = MODULE.prepare_paired_eval(
                taxonomy, eval_path, source_manifest, out
            )
            self.assertEqual(manifest["trace_count"], 8)
            self.assertEqual(manifest["outcome_counts"], {"FAILED": 4, "TIMEOUT": 4})
            self.assertEqual(manifest["source_model_counts"], {
                "claude": 2,
                "claude-s4": 2,
                "gpt5": 2,
                "o4mini": 2,
            })
            with self.assertRaisesRegex(ValueError, "must be empty"):
                MODULE.prepare_paired_eval(taxonomy, eval_path, source_manifest, out)
            validated = validate_pair_contract(
                out / "pair_manifest.json",
                out / "taxonomy.json",
                out / "eval_failures.jsonl",
                "small",
                "qwen35-27b",
                "openai-compatible",
            )
            self.assertEqual(validated["trace_count"], 8)
            with self.assertRaisesRegex(ValueError, "model/transport"):
                validate_pair_contract(
                    out / "pair_manifest.json",
                    out / "taxonomy.json",
                    out / "eval_failures.jsonl",
                    "small",
                    "wrong-model",
                    "openai-compatible",
                )


if __name__ == "__main__":
    unittest.main()
