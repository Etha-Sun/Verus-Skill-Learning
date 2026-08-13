from __future__ import annotations

import hashlib
from pathlib import Path

from skillopt.datasets.base import SplitDataLoader


FORBIDDEN_FIELDS = {
    "answer",
    "reference",
    "reference_text",
    "verified",
    "verified_path",
    "paired_verified_path",
}
ALLOWED_GROUPS = {"verified-anvil": "anvil", "verified-ironkv": "ironkv"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class VeruSAGEDataLoader(SplitDataLoader):
    """Load a frozen, reference-free VeruSAGE train/val/test split."""

    def load_split_items(self, split_path: str) -> list[dict]:
        items = super().load_split_items(split_path)
        seen: set[str] = set()
        clean: list[dict] = []
        for raw in items:
            if not isinstance(raw, dict):
                raise ValueError(f"split item is not an object: {type(raw).__name__}")
            forbidden = sorted(FORBIDDEN_FIELDS.intersection(raw))
            if forbidden:
                raise ValueError(f"split item exposes reference fields: {forbidden}")
            item_id = str(raw.get("id") or "")
            if not item_id or Path(item_id).name != item_id:
                raise ValueError(f"unsafe or missing item id: {item_id!r}")
            if item_id in seen:
                raise ValueError(f"duplicate item id: {item_id}")
            seen.add(item_id)

            group = str(raw.get("directory_group") or "")
            if group not in ALLOWED_GROUPS:
                raise ValueError(f"forbidden directory group: {group!r}")
            source = Path(str(raw.get("source_path") or "")).resolve()
            expected = str(raw.get("source_sha256") or "")
            if not source.is_file() or not expected:
                raise ValueError(f"missing source or source hash for {item_id}")
            if group not in source.parts or "unverified" not in source.parts:
                raise ValueError(f"source is outside the allowed unverified tree: {source}")
            if sha256_file(source) != expected:
                raise ValueError(f"stale source hash for {item_id}")

            item = dict(raw)
            item["source_path"] = str(source)
            item["task_type"] = ALLOWED_GROUPS[group]
            clean.append(item)
        return clean

    def get_task_types(self) -> list[str]:
        return ["anvil", "ironkv"]
