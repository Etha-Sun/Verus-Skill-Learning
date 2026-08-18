#!/usr/bin/env python3
"""Build and verify a frozen candidate-update schedule from REDUCE artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE_CODE = REPO / "trace2skill_verusage_baseline_test" / "code"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BASELINE_CODE))

from global_skill_experiment.candidates import (  # noqa: E402
    METHOD_UNIT_TYPES,
    SCHEMA_VERSION,
    semantic_content_sha256,
    sha256_file,
    write_candidate_schedule,
)
from global_skill_experiment.gate import hash_skill_tree  # noqa: E402
from skill_evolver.parallel_evolving_agent import (  # noqa: E402
    ParallelSkillEvolver,
    chunk_list,
)
from skill_evolver.semantic_reduce_evolving_agent import (  # noqa: E402
    enumerate_patch_items,
)


def hash_artifact_tree(root: Path) -> str:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"artifact tree not found: {root}")
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise ValueError(f"artifact tree is empty: {root}")
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def load_records(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError("shared memories must contain a non-empty record array")
    ids = [record.get("instance_id") for record in value]
    if not all(isinstance(item, str) and item for item in ids):
        raise ValueError("every shared-memory record requires instance_id")
    if len(ids) != len(set(ids)):
        raise ValueError("shared-memory instance_id values must be unique")
    return value


def parse_semantic_patch(path: Path) -> list[Any]:
    patches, feedback = ParallelSkillEvolver._extract_semantic_patch_blocks_with_feedback(
        path.read_text(encoding="utf-8")
    )
    if not patches:
        raise ValueError(f"cannot parse semantic patch {path}: {feedback}")
    return patches


def native_map_catalog(map_dir: Path) -> list[dict[str, Any]]:
    files = sorted((map_dir / "map_semantic").glob("patch_*.md"))
    if not files:
        raise ValueError(f"no MAP semantic patches below {map_dir / 'map_semantic'}")
    patches = [patch for path in files for patch in parse_semantic_patch(path)]
    return enumerate_patch_items(patches)


def provenance_by_batch(
    records: list[dict[str, Any]], batch_size: int
) -> dict[int, tuple[str, ...]]:
    return {
        index: tuple(str(record["instance_id"]) for record in batch)
        for index, batch in enumerate(chunk_list(records, batch_size), start=1)
    }


def stable_union(values: list[list[str] | tuple[str, ...]]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in values:
        for value in group:
            if value not in seen:
                seen.add(value)
                result.append(value)
    return result


def unit_row(
    *,
    unit_id: str,
    order: int,
    method: str,
    payload_path: Path,
    train_ids: list[str],
    source_ids: list[str],
    family_id: str | None,
) -> dict[str, Any]:
    text = payload_path.read_text(encoding="utf-8")
    return {
        "unit_id": unit_id,
        "order": order,
        "construction_method": method,
        "unit_type": METHOD_UNIT_TYPES[method],
        "family_id": family_id,
        "payload_format": "semantic-patch-markdown-v1",
        "payload_path": str(payload_path.resolve()),
        "payload_sha256": sha256_file(payload_path),
        "content_sha256": semantic_content_sha256(text),
        "train_provenance_ids": train_ids,
        "source_item_ids": source_ids,
    }


def build_native(args: argparse.Namespace, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    if args.native_unit is None:
        raise ValueError("--native-unit is required for native-compressed")
    catalog = native_map_catalog(args.map_dir)
    source_ids = [str(row["item_id"]) for row in catalog]
    train_ids = [str(record["instance_id"]) for record in records]
    return [
        unit_row(
            unit_id="native-compressed-0001",
            order=1,
            method="native-compressed",
            payload_path=args.native_unit,
            train_ids=train_ids,
            source_ids=source_ids,
            family_id=None,
        )
    ], len(catalog)


def build_semantic(args: argparse.Namespace, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    if args.semantic_manifest is None:
        raise ValueError("--semantic-manifest is required for semantic-reduce")
    manifest = json.loads(args.semantic_manifest.read_text(encoding="utf-8"))
    families = manifest.get("families")
    map_items = manifest.get("map_items")
    if not isinstance(families, list) or not families:
        raise ValueError("semantic manifest has no families")
    if not isinstance(map_items, list) or not map_items:
        raise ValueError("semantic manifest has no MAP item catalog")
    batch_train = provenance_by_batch(records, args.batch_size)
    item_batch = {
        str(row["item_id"]): int(row["map_batch_index"])
        for row in map_items
    }
    units: list[dict[str, Any]] = []
    seen_items: set[str] = set()
    root = args.semantic_manifest.parent.parent
    for index, family in enumerate(families, start=1):
        if family.get("candidate_unit_order") != index:
            raise ValueError("semantic family candidate order is not stable/contiguous")
        family_id = str(family["family_id"])
        source_ids = list(map(str, family.get("source_item_ids", [])))
        if not source_ids or any(item in seen_items for item in source_ids):
            raise ValueError(f"family {family_id} has empty or duplicate source lineage")
        seen_items.update(source_ids)
        try:
            train_ids = stable_union([batch_train[item_batch[item]] for item in source_ids])
        except KeyError as exc:
            raise ValueError(f"family {family_id} references unknown MAP lineage {exc}") from exc
        payload_path = root / str(family["candidate_unit_path"])
        units.append(
            unit_row(
                unit_id=f"semantic-{index:04d}-{family_id}",
                order=index,
                method="semantic-reduce",
                payload_path=payload_path,
                train_ids=train_ids,
                source_ids=source_ids,
                family_id=family_id,
            )
        )
    expected = {str(row["item_id"]) for row in map_items}
    if seen_items != expected:
        raise ValueError(
            "semantic candidate families do not cover MAP items exactly once; "
            f"missing={sorted(expected-seen_items)}, unexpected={sorted(seen_items-expected)}"
        )
    return units, len(map_items)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", required=True, choices=sorted(METHOD_UNIT_TYPES))
    parser.add_argument("--schedule-id", required=True)
    parser.add_argument("--m-core", type=Path, required=True)
    parser.add_argument("--memories", type=Path, required=True)
    parser.add_argument("--map-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--native-unit", type=Path)
    parser.add_argument("--semantic-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    records = load_records(args.memories)
    if args.method == "native-compressed":
        units, map_item_count = build_native(args, records)
        ordering = "single native global-REDUCE bundle"
    else:
        units, map_item_count = build_semantic(args, records)
        ordering = "semantic partition family array order; exact-once MAP lineage"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "schedule_id": args.schedule_id,
        "construction_method": args.method,
        "unit_type": METHOD_UNIT_TYPES[args.method],
        "m_core": {
            "path": str(args.m_core.resolve()),
            "sha256": hash_skill_tree(args.m_core),
        },
        "shared_memories": {
            "path": str(args.memories.resolve()),
            "sha256": sha256_file(args.memories),
        },
        "construction": {
            "map_artifact_sha256": hash_artifact_tree(args.map_dir / "map_semantic"),
            "map_item_count": map_item_count,
            "map_batch_size": args.batch_size,
            "ordering_policy": ordering,
        },
        "units": units,
    }
    digest = write_candidate_schedule(payload, args.output)
    print(json.dumps({"schedule": str(args.output.resolve()), "sha256": digest, "unit_count": len(units), "map_item_count": map_item_count}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
