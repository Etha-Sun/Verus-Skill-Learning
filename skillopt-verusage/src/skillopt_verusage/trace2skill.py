"""Immutable Trace2Skill candidate schedules and snapshot lineage.

This module is adapted from the reusable candidate layer in the upstream
Trace2Skill experiment.  Candidate construction is deliberately injected: the
local held-out gate remains the only promotion policy, and frozen training data
never needs to be copied into this repository.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol


SCHEDULE_SCHEMA = "candidate-update-manifest-v1"
SNAPSHOT_SCHEMA = "candidate-snapshot-lineage-v1"
METHOD_UNIT_TYPES = {
    "native-compressed": "native-compressed-bundle",
    "semantic-reduce": "semantic-family-bundle",
}
PAYLOAD_FORMATS = {"semantic-patch-markdown-v1", "exact-patch-json-v1"}
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def schedule_sha256(payload: Mapping[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("schedule_sha256", None)
    return sha256_bytes(canonical_json_bytes(unsigned))


def semantic_content_sha256(text: str) -> str:
    normalized = "\n".join(
        line.rstrip() for line in text.replace("\r\n", "\n").split("\n")
    )
    return sha256_bytes(normalized.strip().encode("utf-8"))


def hash_skill_tree(skill_dir: Path) -> str:
    root = skill_dir.resolve()
    if not root.is_dir():
        raise ValueError(f"skill snapshot is not a directory: {root}")
    digest = hashlib.sha256()
    entries = sorted(root.rglob("*"))
    symlinks = [path for path in entries if path.is_symlink()]
    if symlinks:
        raise ValueError(f"skill snapshot must not contain symlinks: {symlinks[0]}")
    files = [path for path in entries if path.is_file()]
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


@dataclass(frozen=True)
class CandidateSnapshot:
    candidate_id: str
    skill_dir: Path
    construction_method: str
    unit_type: str
    train_provenance_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateUnit:
    unit_id: str
    order: int
    construction_method: str
    unit_type: str
    payload_format: str
    payload_path: Path
    payload_sha256: str
    content_sha256: str
    train_provenance_ids: tuple[str, ...]
    source_item_ids: tuple[str, ...]
    family_id: str | None = None


@dataclass(frozen=True)
class CandidateSchedule:
    path: Path
    schedule_id: str
    construction_method: str
    unit_type: str
    m_core_path: Path
    m_core_sha256: str
    shared_memories_path: Path
    shared_memories_sha256: str
    construction: Mapping[str, Any]
    units: tuple[CandidateUnit, ...]
    digest: str


class PromotionDecision(Protocol):
    next_snapshot: CandidateSnapshot


class PromotionController(Protocol):
    def promote(
        self, incumbent: CandidateSnapshot, candidate: CandidateSnapshot
    ) -> PromotionDecision: ...


def _require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _resolve_path(manifest_path: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("artifact path must be a non-empty string")
    path = Path(value)
    return path.resolve() if path.is_absolute() else (manifest_path.parent / path).resolve()


def _unique_strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{field} must be a non-empty string array")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} must not contain duplicates")
    return tuple(value)


def load_candidate_schedule(path: Path, *, verify_files: bool = True) -> CandidateSchedule:
    manifest_path = path.resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("candidate schedule must be a JSON object")
    if payload.get("schema_version") != SCHEDULE_SCHEMA:
        raise ValueError(
            f"unsupported candidate schedule schema: {payload.get('schema_version')!r}"
        )
    schedule_id = payload.get("schedule_id")
    if not isinstance(schedule_id, str) or not _SAFE_ID.fullmatch(schedule_id):
        raise ValueError("schedule_id is unsafe")
    method = payload.get("construction_method")
    if method not in METHOD_UNIT_TYPES:
        raise ValueError(f"unsupported construction_method: {method!r}")
    unit_type = payload.get("unit_type")
    if unit_type != METHOD_UNIT_TYPES[method]:
        raise ValueError("unit_type does not match construction_method")
    digest = _require_sha256(payload.get("schedule_sha256"), "schedule_sha256")
    if schedule_sha256(payload) != digest:
        raise ValueError("candidate schedule hash mismatch")

    m_core = payload.get("m_core")
    memories = payload.get("shared_memories")
    if not isinstance(m_core, dict) or not isinstance(memories, dict):
        raise ValueError("m_core and shared_memories must be objects")
    m_core_path = _resolve_path(manifest_path, m_core.get("path"))
    memories_path = _resolve_path(manifest_path, memories.get("path"))
    m_core_hash = _require_sha256(m_core.get("sha256"), "m_core.sha256")
    memories_hash = _require_sha256(
        memories.get("sha256"), "shared_memories.sha256"
    )

    construction = payload.get("construction")
    if not isinstance(construction, dict):
        raise ValueError("construction must be an object")
    _require_sha256(
        construction.get("map_artifact_sha256"),
        "construction.map_artifact_sha256",
    )
    if (
        not isinstance(construction.get("map_item_count"), int)
        or construction["map_item_count"] <= 0
    ):
        raise ValueError("construction.map_item_count must be positive")
    if not isinstance(construction.get("ordering_policy"), str) or not construction[
        "ordering_policy"
    ]:
        raise ValueError("construction.ordering_policy is required")

    raw_units = payload.get("units")
    if not isinstance(raw_units, list) or not raw_units:
        raise ValueError("units must be a non-empty array")
    units: list[CandidateUnit] = []
    for index, raw in enumerate(raw_units, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"unit {index} must be an object")
        unit_id = raw.get("unit_id")
        if not isinstance(unit_id, str) or not _SAFE_ID.fullmatch(unit_id):
            raise ValueError(f"unit {index} has unsafe unit_id")
        if raw.get("order") != index:
            raise ValueError("candidate unit order must be contiguous")
        if raw.get("construction_method") != method or raw.get("unit_type") != unit_type:
            raise ValueError(f"unit {unit_id} method/type differs from schedule")
        payload_format = raw.get("payload_format")
        if payload_format not in PAYLOAD_FORMATS:
            raise ValueError(f"unit {unit_id} has unsupported payload_format")
        payload_path = _resolve_path(manifest_path, raw.get("payload_path"))
        unit = CandidateUnit(
            unit_id=unit_id,
            order=index,
            construction_method=method,
            unit_type=unit_type,
            family_id=raw.get("family_id"),
            payload_format=payload_format,
            payload_path=payload_path,
            payload_sha256=_require_sha256(
                raw.get("payload_sha256"), f"unit {unit_id} payload_sha256"
            ),
            content_sha256=_require_sha256(
                raw.get("content_sha256"), f"unit {unit_id} content_sha256"
            ),
            train_provenance_ids=_unique_strings(
                raw.get("train_provenance_ids"),
                f"unit {unit_id} train_provenance_ids",
            ),
            source_item_ids=_unique_strings(
                raw.get("source_item_ids"), f"unit {unit_id} source_item_ids"
            ),
        )
        if method == "semantic-reduce" and not unit.family_id:
            raise ValueError(f"semantic unit {unit_id} requires family_id")
        if method == "native-compressed" and unit.family_id is not None:
            raise ValueError(f"native unit {unit_id} must not declare family_id")
        if verify_files:
            if not payload_path.is_file() or sha256_file(payload_path) != unit.payload_sha256:
                raise ValueError(f"unit {unit_id} payload file/hash mismatch")
            if (
                semantic_content_sha256(payload_path.read_text(encoding="utf-8"))
                != unit.content_sha256
            ):
                raise ValueError(f"unit {unit_id} semantic content hash mismatch")
        units.append(unit)
    if len({unit.unit_id for unit in units}) != len(units):
        raise ValueError("candidate unit IDs must be unique")
    all_items = [item for unit in units for item in unit.source_item_ids]
    if method == "semantic-reduce" and len(all_items) != len(set(all_items)):
        raise ValueError("semantic source_item_ids must be exact-once")
    if verify_files:
        if hash_skill_tree(m_core_path) != m_core_hash:
            raise ValueError("frozen M-core tree/hash mismatch")
        if not memories_path.is_file() or sha256_file(memories_path) != memories_hash:
            raise ValueError("shared memories file/hash mismatch")
    return CandidateSchedule(
        path=manifest_path,
        schedule_id=schedule_id,
        construction_method=method,
        unit_type=unit_type,
        m_core_path=m_core_path,
        m_core_sha256=m_core_hash,
        shared_memories_path=memories_path,
        shared_memories_sha256=memories_hash,
        construction=construction,
        units=tuple(units),
        digest=digest,
    )


def write_candidate_schedule(payload: Mapping[str, Any], path: Path) -> str:
    value = dict(payload)
    value["schedule_sha256"] = schedule_sha256(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
    load_candidate_schedule(path)
    return value["schedule_sha256"]


def copy_incumbent_snapshot(
    incumbent: CandidateSnapshot, output_root: Path
) -> tuple[Path, Path]:
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError(f"candidate output is non-empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    skill_dir = output_root / "skill"
    shutil.copytree(incumbent.skill_dir, skill_dir, symlinks=False)
    return skill_dir, output_root / "snapshot_manifest.json"


def finalize_candidate_snapshot(
    *,
    incumbent: CandidateSnapshot,
    unit: CandidateUnit,
    skill_dir: Path,
    metadata_path: Path,
    m_core_hash: str,
) -> CandidateSnapshot:
    metadata = {
        "schema_version": SNAPSHOT_SCHEMA,
        "candidate_id": unit.unit_id,
        "construction_method": unit.construction_method,
        "unit_type": unit.unit_type,
        "unit_order": unit.order,
        "m_core_hash": m_core_hash,
        "parent_candidate_id": incumbent.candidate_id,
        "parent_snapshot_hash": hash_skill_tree(incumbent.skill_dir),
        "candidate_snapshot_hash": hash_skill_tree(skill_dir),
        "payload_sha256": unit.payload_sha256,
        "content_sha256": unit.content_sha256,
        "train_provenance_ids": list(unit.train_provenance_ids),
        "source_item_ids": list(unit.source_item_ids),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return CandidateSnapshot(
        candidate_id=unit.unit_id,
        skill_dir=skill_dir,
        construction_method=unit.construction_method,
        unit_type=unit.unit_type,
        train_provenance_ids=unit.train_provenance_ids,
    )


def load_candidate_snapshot(
    *,
    incumbent: CandidateSnapshot,
    unit: CandidateUnit,
    output_root: Path,
    m_core_hash: str,
) -> CandidateSnapshot:
    skill_dir = output_root / "skill"
    metadata_path = output_root / "snapshot_manifest.json"
    if not skill_dir.is_dir() or not metadata_path.is_file():
        raise FileNotFoundError(f"incomplete candidate snapshot: {output_root}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError(f"candidate snapshot manifest must be an object: {metadata_path}")
    expected = {
        "schema_version": SNAPSHOT_SCHEMA,
        "candidate_id": unit.unit_id,
        "construction_method": unit.construction_method,
        "unit_type": unit.unit_type,
        "unit_order": unit.order,
        "m_core_hash": m_core_hash,
        "parent_candidate_id": incumbent.candidate_id,
        "parent_snapshot_hash": hash_skill_tree(incumbent.skill_dir),
        "candidate_snapshot_hash": hash_skill_tree(skill_dir),
        "payload_sha256": unit.payload_sha256,
        "content_sha256": unit.content_sha256,
        "train_provenance_ids": list(unit.train_provenance_ids),
        "source_item_ids": list(unit.source_item_ids),
    }
    mismatches = [key for key, value in expected.items() if metadata.get(key) != value]
    if mismatches:
        raise ValueError(
            f"candidate snapshot lineage mismatch for {unit.unit_id}: {mismatches}"
        )
    return CandidateSnapshot(
        candidate_id=unit.unit_id,
        skill_dir=skill_dir,
        construction_method=unit.construction_method,
        unit_type=unit.unit_type,
        train_provenance_ids=unit.train_provenance_ids,
    )


Materializer = Callable[[CandidateSnapshot, CandidateUnit, Path], CandidateSnapshot]


def run_candidate_sequence(
    *,
    schedule: CandidateSchedule,
    initial_snapshot: CandidateSnapshot,
    controller: PromotionController,
    materializer: Materializer,
    output_root: Path,
) -> tuple[CandidateSnapshot, list[PromotionDecision]]:
    """Materialize each unit from the retained incumbent and invoke one gate."""
    if hash_skill_tree(initial_snapshot.skill_dir) != schedule.m_core_sha256:
        raise ValueError("initial snapshot does not match schedule M-core")
    incumbent = initial_snapshot
    decisions: list[PromotionDecision] = []
    for unit in schedule.units:
        candidate_root = output_root / f"{unit.order:04d}_{unit.unit_id}"
        if candidate_root.exists():
            candidate = load_candidate_snapshot(
                incumbent=incumbent,
                unit=unit,
                output_root=candidate_root,
                m_core_hash=schedule.m_core_sha256,
            )
        else:
            candidate = materializer(incumbent, unit, candidate_root)
        if (
            candidate.candidate_id != unit.unit_id
            or candidate.construction_method != unit.construction_method
            or candidate.unit_type != unit.unit_type
            or candidate.train_provenance_ids != unit.train_provenance_ids
        ):
            raise ValueError(f"materializer returned mismatched candidate {unit.unit_id}")
        resume = getattr(controller, "resume_promotion", None)
        decision = resume(incumbent, candidate) if callable(resume) else None
        if decision is None:
            decision = controller.promote(incumbent, candidate)
        decisions.append(decision)
        incumbent = decision.next_snapshot
    return incumbent, decisions
