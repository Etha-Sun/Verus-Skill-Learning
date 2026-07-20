import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from verus_self_evolve.data_layout import (
    BATCH_DIRECTORIES,
    HANDSOFF_DIRECTORIES,
    inspect_layout,
    selected_dataset_path,
)


def make_layout(root: Path, layout: str) -> None:
    verusage = root / "verusage-batch-v1" if layout == "versioned" else root
    handsoff = (
        root / "handsoff-v1"
        if layout == "versioned"
        else root / "claude_sonnet_gpt5"
    )
    for name in BATCH_DIRECTORIES:
        (verusage / name).mkdir(parents=True)
    for name in HANDSOFF_DIRECTORIES:
        (handsoff / name).mkdir(parents=True)


class DataLayoutTest(unittest.TestCase):
    def test_versioned_layout_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            run_root = root / "runs"
            make_layout(data_root, "versioned")
            report = inspect_layout(data_root, run_root)
            self.assertTrue(report["ok"])
            self.assertTrue(report["raw_data_read_only"])
            self.assertEqual(report["missing_directories"], [])

    def test_legacy_layout_supports_existing_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "legacy"
            make_layout(data_root, "legacy")
            report = inspect_layout(data_root, root / "runs", layout="legacy")
            self.assertTrue(report["ok"])
            self.assertEqual(
                Path(report["handsoff_root"]),
                data_root / "claude_sonnet_gpt5",
            )

    def test_overlapping_run_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "data"
            make_layout(data_root, "versioned")
            report = inspect_layout(data_root, data_root / "runs")
            self.assertFalse(report["ok"])
            self.assertIn("data and run roots must not overlap", report["issues"])

    def test_environment_variables_are_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            run_root = root / "runs"
            make_layout(data_root, "versioned")
            with patch.dict(
                os.environ,
                {
                    "VERUS_SKILL_DATA_ROOT": str(data_root),
                    "VERUS_SKILL_RUN_ROOT": str(run_root),
                    "VERUS_SKILL_DATA_LAYOUT": "versioned",
                },
            ):
                self.assertTrue(inspect_layout()["ok"])

    def test_selected_dataset_uses_local_legacy_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "collaborator-data"
            with patch.dict(
                os.environ,
                {
                    "VERUS_SKILL_DATA_ROOT": str(data_root),
                    "VERUS_SKILL_DATA_LAYOUT": "legacy",
                },
            ):
                self.assertEqual(
                    selected_dataset_path("verusage"),
                    data_root.resolve(),
                )
                self.assertEqual(
                    selected_dataset_path("handsoff"),
                    (data_root / "claude_sonnet_gpt5").resolve(),
                )

    def test_explicit_data_root_overrides_local_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            explicit_root = Path(tmp) / "explicit"
            with patch.dict(
                os.environ,
                {"VERUS_SKILL_DATA_ROOT": "/unused/source"},
            ):
                self.assertEqual(
                    selected_dataset_path(
                        "verusage",
                        data_root=explicit_root,
                        layout="versioned",
                    ),
                    (explicit_root / "verusage-batch-v1").resolve(),
                )


if __name__ == "__main__":
    unittest.main()
