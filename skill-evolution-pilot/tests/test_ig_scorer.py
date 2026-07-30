from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from skill_evolution_pilot.ig_scorer import proof_context, run_scorer_gate


class FakeScorer:
    model = "fake-qwen"

    def score(self, *, context: str, target: str, token_output: Path):
        token_output.parent.mkdir(parents=True, exist_ok=True)
        token_output.write_text(
            json.dumps({"token": target[0], "logprob": -1.0}) + "\n",
            encoding="utf-8",
        )
        return {
            "model": self.model,
            "exact_teacher_forcing": True,
            "truncated": False,
            "context_tokens": len(context),
            "target_tokens": len(target),
            "sequence_tokens": len(context + target),
            "max_model_len": 100000,
            "sum_logprob_nats": -float(len(target)),
            "avg_logprob_nats": -1.0,
            "token_rows": str(token_output),
        }


class IgScorerTest(unittest.TestCase):
    def test_context_places_summary_before_target(self) -> None:
        context = proof_context("unfinished", "proof rationale")
        self.assertIn("proof rationale", context)
        self.assertTrue(context.endswith("<BEGIN_COMPLETE_VERUS>\n"))

    def test_gate_requires_reproducible_exact_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_root = os.environ.get("VERUS_SKILL_RUN_ROOT")
            os.environ["VERUS_SKILL_RUN_ROOT"] = str(root)
            try:
                rows = []
                for index in range(4):
                    source = root / f"source-{index}.rs"
                    reference = root / f"reference-{index}.rs"
                    source.write_text("unfinished", encoding="utf-8")
                    reference.write_text("finished", encoding="utf-8")
                    rows.append(
                        {
                            "task_id": f"task-{index}",
                            "source": str(source),
                            "reference": str(reference),
                        }
                    )
                manifest = root / "manifest.json"
                manifest.write_text(
                    json.dumps({"valid": True, "rows": rows}),
                    encoding="utf-8",
                )
                result = run_scorer_gate(
                    reference_manifest_path=manifest,
                    out_dir=root / "gate",
                    scorer=FakeScorer(),
                )
                self.assertTrue(result["valid"])
                self.assertEqual(len(result["baseline_rows"]), 4)
            finally:
                if old_root is None:
                    os.environ.pop("VERUS_SKILL_RUN_ROOT", None)
                else:
                    os.environ["VERUS_SKILL_RUN_ROOT"] = old_root


if __name__ == "__main__":
    unittest.main()
