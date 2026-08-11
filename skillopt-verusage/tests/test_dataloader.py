from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from skillopt_verusage.dataloader import VeruSAGEDataLoader


def _split(tmp_path: Path, *, extra: dict | None = None) -> Path:
    source_dir = tmp_path / "verified-anvil" / "unverified"
    source_dir.mkdir(parents=True)
    source = source_dir / "task.rs"
    source.write_text("verus! { fn task() {} }\n", encoding="utf-8")
    item = {
        "id": "abc123",
        "task_id": "task",
        "directory_group": "verified-anvil",
        "source_path": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    item.update(extra or {})
    split = tmp_path / "split"
    for name in ("train", "val", "test"):
        path = split / name
        path.mkdir(parents=True)
        (path / "items.json").write_text(json.dumps([item]), encoding="utf-8")
    return split


class DataLoaderTest(unittest.TestCase):
    def test_loader_accepts_reference_free_unverified_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            loader = VeruSAGEDataLoader(
                split_dir=str(_split(Path(temp_dir))),
                split_mode="split_dir",
            )
            loader.setup({})
            self.assertEqual(loader.get_train_size(), 1)
            self.assertEqual(loader.train_items[0]["task_type"], "anvil")

    def test_loader_rejects_reference_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            loader = VeruSAGEDataLoader(
                split_dir=str(
                    _split(
                        Path(temp_dir),
                        extra={"verified_path": "/hidden/proof.rs"},
                    )
                ),
                split_mode="split_dir",
            )
            with self.assertRaisesRegex(ValueError, "reference fields"):
                loader.setup({})


if __name__ == "__main__":
    unittest.main()
