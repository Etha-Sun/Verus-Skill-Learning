from __future__ import annotations

import unittest

from skillopt_verusage.calibrate import _balanced_items


class CalibrationSelectionTest(unittest.TestCase):
    def test_balanced_items_selects_both_projects(self) -> None:
        items = [
            {"id": f"a{index}", "task_type": "anvil"} for index in range(5)
        ] + [{"id": f"i{index}", "task_type": "ironkv"} for index in range(5)]
        selected = _balanced_items(items, 8)
        self.assertEqual(
            [item["task_type"] for item in selected],
            ["anvil"] * 4 + ["ironkv"] * 4,
        )


if __name__ == "__main__":
    unittest.main()
