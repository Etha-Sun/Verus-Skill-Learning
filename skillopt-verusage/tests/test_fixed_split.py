from __future__ import annotations

import unittest

from skillopt_verusage.fixed_split import (
    OUTCOME_QUOTAS,
    normalize_history_source,
    select_rows,
)


class FixedSplitTest(unittest.TestCase):
    def test_history_normalization_removes_only_harness_instrumentation(self) -> None:
        benchmark = "verus!{\nfn f() {}\n}\n"
        historical = "verus!{\n#[verifier::loop_isolation(false)]\nfn f() {}\n}\n\n"
        self.assertEqual(
            normalize_history_source(benchmark), normalize_history_source(historical)
        )

    def test_selection_has_exact_project_outcome_quotas(self) -> None:
        rows = []
        cursor = 0
        for (project, outcome), quotas in OUTCOME_QUOTAS.items():
            needed = sum(quotas.values())
            for index in range(needed + 4):
                cursor += 1
                rows.append(
                    {
                        "id": f"id-{cursor}",
                        "task_id": f"{project}__task_{outcome}_{index}",
                        "project_code": project,
                        "claude_outcome": outcome,
                        "source_loc": 10 + index,
                        "claude_time_seconds": 20.0 + index,
                        "claude_total_tokens": 1000 + 10 * index,
                    }
                )

        first = select_rows(rows, seed=20260814)
        second = select_rows(rows, seed=20260814)
        self.assertEqual(first, second)
        self.assertEqual(
            {name: len(items) for name, items in first.items()},
            {"train": 40, "val": 20, "test": 20},
        )

        all_ids = [row["id"] for items in first.values() for row in items]
        self.assertEqual(len(all_ids), len(set(all_ids)))
        for stratum, quotas in OUTCOME_QUOTAS.items():
            for split_name, expected in quotas.items():
                actual = sum(
                    (row["project_code"], row["claude_outcome"]) == stratum
                    for row in first[split_name]
                )
                self.assertEqual(actual, expected)
        self.assertEqual(
            sum(row["claude_outcome"] == "failed" for row in first["train"]), 10
        )
        self.assertEqual(
            sum(row["claude_outcome"] == "failed" for row in first["val"]), 5
        )
        self.assertEqual(
            sum(row["claude_outcome"] == "failed" for row in first["test"]), 5
        )


if __name__ == "__main__":
    unittest.main()
