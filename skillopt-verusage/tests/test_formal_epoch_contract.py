from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skillopt_verusage.train import _validate_formal_epoch


class FormalEpochContractTest(unittest.TestCase):
    @staticmethod
    def _results(root: Path, relative: str, count: int) -> None:
        predictions = root / relative / "predictions"
        for index in range(count):
            task = predictions / f"task-{index:02d}"
            task.mkdir(parents=True, exist_ok=True)
            (task / "result.json").write_text(
                json.dumps({"id": task.name, "fidelity": "V2_TRACE"}),
                encoding="utf-8",
            )

    def test_requires_exact_distinct_20_40_20_epoch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._results(root, "selection_eval_baseline", 20)
            self._results(root, "steps/step_0001/rollout", 40)
            self._results(root, "steps/step_0001/selection_eval", 20)
            (root / "selection_eval_baseline" / "skill.md").write_text(
                "S0\n", encoding="utf-8"
            )
            (root / "steps" / "step_0001" / "candidate_skill.md").write_text(
                "S1\n", encoding="utf-8"
            )
            summary = {
                "total_steps": 1,
                "total_skips": 0,
                "total_accepts": 0,
                "total_rejects": 1,
            }
            ledger = {
                "target": {"accounting_complete": True},
                "optimizer": {"accounting_complete": True, "failed_calls": 0},
            }
            validation = _validate_formal_epoch(
                {"out_root": str(root)}, summary, ledger
            )
            self.assertEqual(validation["status"], "pass")

            missing = (
                root
                / "steps"
                / "step_0001"
                / "selection_eval"
                / "predictions"
                / "task-19"
                / "result.json"
            )
            missing.unlink()
            with self.assertRaisesRegex(RuntimeError, "actor task schedule mismatch"):
                _validate_formal_epoch({"out_root": str(root)}, summary, ledger)


if __name__ == "__main__":
    unittest.main()
