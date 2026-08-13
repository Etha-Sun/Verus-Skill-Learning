from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from skillopt_verusage.retrieval import filter_retrieval_cards, retrieve_card
from skillopt_verusage.retrieval_gate import _audit_support


class RetrievalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "abstain_threshold": 2,
            "max_cards": 12,
            "cards": [
                {
                    "id": "quantifier",
                    "project": "anvil",
                    "triggers": ["forall", "trigger", "postcondition"],
                },
                {
                    "id": "scope",
                    "project": "any",
                    "triggers": ["cannot find", "scope"],
                },
            ],
        }

    def test_retrieves_top_card_after_two_matches(self) -> None:
        result = retrieve_card(
            self.config,
            [{"role": "user", "content": "forall trigger failed"}],
            "anvil",
        )
        self.assertEqual(result["card"]["id"], "quantifier")
        self.assertEqual(result["score"], 2)

    def test_abstains_below_threshold_and_respects_project(self) -> None:
        self.assertIsNone(
            retrieve_card(
                self.config,
                [{"role": "user", "content": "forall trigger failed"}],
                "ironkv",
            )
        )

    def test_support_audit_checks_stored_hard_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prediction_dir = Path(temp_dir)
            task_dir = prediction_dir / "task1"
            task_dir.mkdir()
            (task_dir / "result.json").write_text(
                json.dumps({"id": "task1", "hard": 1}),
                encoding="utf-8",
            )
            cards = {
                "cards": [
                    {
                        "id": "card1",
                        "support": [
                            {"task_id": "task1", "verifier_label": "solved"}
                        ],
                    }
                ]
            }
            self.assertTrue(_audit_support(cards, prediction_dir)["passed"])

    def test_filter_rejects_assume_guidance_without_rewriting(self) -> None:
        config = {
            "cards": [
                {"id": "unsafe", "guidance": "Assume the antecedent."},
                {"id": "safe", "guidance": "Inspect the helper contract."},
            ]
        }
        filtered, audit = filter_retrieval_cards(config)
        self.assertEqual([card["id"] for card in filtered["cards"]], ["safe"])
        self.assertEqual(audit["rejected_cards"][0]["id"], "unsafe")


if __name__ == "__main__":
    unittest.main()
