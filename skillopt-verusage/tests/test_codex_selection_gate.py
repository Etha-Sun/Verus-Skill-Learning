from __future__ import annotations

import unittest

from skillopt_verusage.codex_selection_gate import _paired_summary, _score


class CodexSelectionGateTest(unittest.TestCase):
    def test_score_and_paired_transitions(self) -> None:
        baseline = [
            {"id": "a", "hard": 0, "soft": 0.0},
            {"id": "b", "hard": 1, "soft": 1.0},
        ]
        candidate = [
            {"id": "a", "hard": 1, "soft": 1.0},
            {"id": "b", "hard": 0, "soft": 0.0},
        ]
        self.assertEqual(_score(candidate), (0.5, 0.5))
        self.assertEqual(
            _paired_summary(baseline, candidate)["transitions"],
            {"0_to_0": 0, "0_to_1": 1, "1_to_0": 1, "1_to_1": 0},
        )


if __name__ == "__main__":
    unittest.main()
