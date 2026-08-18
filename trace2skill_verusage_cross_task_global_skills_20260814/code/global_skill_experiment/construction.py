"""M-core-seeded construction phases shared by compressed and semantic REDUCE."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


EXPERIMENT = Path(__file__).resolve().parents[2]
REPO = EXPERIMENT.parent
BASELINE_CODE = REPO / "trace2skill_verusage_baseline_test" / "code"
if str(BASELINE_CODE) not in sys.path:
    sys.path.insert(0, str(BASELINE_CODE))

from react_agent.models import OpenAIClient  # noqa: E402
from skill_evolver.parallel_evolving_agent import (  # noqa: E402
    ParallelSkillEvolver,
    SemanticPatch,
    chunk_list,
)
from skill_evolver.parallel_success_evolving_agent import (  # noqa: E402
    CombinedParallelSkillEvolver,
)
from skill_evolver.semantic_reduce_evolving_agent import (  # noqa: E402
    SemanticReduceParallelSkillEvolver,
    enumerate_patch_items,
)


def load_shared_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("shared memories must be a non-empty JSON array")
    ids = [record.get("instance_id") for record in payload]
    if not all(isinstance(item, str) and item for item in ids):
        raise ValueError("every shared-memory record requires instance_id")
    if len(ids) != len(set(ids)):
        raise ValueError("shared-memory instance IDs must be unique")
    return payload


def preflight(
    *,
    method: str,
    m_core: Path,
    memories: Path,
    batch_size: int,
    merge_batch_size: int,
    max_merge_levels: int,
    shared_map_dir: Path | None = None,
) -> dict[str, Any]:
    if not (m_core / "SKILL.md").is_file():
        raise ValueError(f"invalid M-core skill: {m_core}")
    records = load_shared_records(memories)
    map_batches = chunk_list(records, batch_size)
    result: dict[str, Any] = {
        "mode": "preflight",
        "network_requests": 0,
        "method": method,
        "record_count": len(records),
        "map_batch_size": batch_size,
        "map_batch_count": len(map_batches),
        "merge_batch_size": merge_batch_size,
        "max_merge_levels": max_merge_levels,
        "m_core": str(m_core.resolve()),
        "memories": str(memories.resolve()),
    }
    if method == "native-compressed":
        remaining = len(map_batches)
        merge_calls = 0
        levels = 0
        while remaining > 1 and levels < max_merge_levels:
            remaining = len(chunk_list(list(range(remaining)), merge_batch_size))
            merge_calls += remaining
            levels += 1
        if remaining > 1:
            merge_calls += 1
        result.update(
            {
                "shared_map_action": "generate_once",
                "estimated_map_calls": len(map_batches),
                "estimated_reduce_calls_upper_bound": merge_calls,
                "candidate_unit_count": 1,
            }
        )
    else:
        if shared_map_dir is None:
            raise ValueError("semantic-reduce requires --shared-map-dir")
        patches, map_manifest = load_frozen_map(shared_map_dir)
        result.update(
            {
                "shared_map_action": "reuse_frozen",
                "shared_map_dir": str(shared_map_dir.resolve()),
                "shared_map_patch_count": len(patches),
                "shared_map_item_count": len(enumerate_patch_items(patches)),
                "shared_map_manifest": map_manifest,
                "candidate_unit_count": "data-dependent family count",
            }
        )
    return result


def make_client(
    *,
    model: str,
    base_url: str | None,
    api_key_env: str,
    cache_path: Path | None,
    generation_config: dict[str, Any],
) -> OpenAIClient:
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ValueError(f"required API key environment variable is unset: {api_key_env}")
    kwargs: dict[str, Any] = {
        "model": model,
        "api_key": api_key,
        "generation_config": generation_config,
    }
    if base_url:
        kwargs["base_url"] = base_url
    if cache_path:
        kwargs["cache_path"] = str(cache_path)
    return OpenAIClient(**kwargs)


def make_evolver(
    *,
    semantic: bool,
    client: OpenAIClient,
    m_core: Path,
    output_dir: Path,
    batch_size: int,
    merge_batch_size: int,
    max_workers: int,
    max_merge_levels: int,
    temperature: float,
    max_tokens: int | None,
) -> CombinedParallelSkillEvolver:
    cls = SemanticReduceParallelSkillEvolver if semantic else CombinedParallelSkillEvolver
    return cls(
        client=client,
        skill_dir=m_core,
        batch_size=batch_size,
        merge_batch_size=merge_batch_size,
        max_workers=max_workers,
        max_merge_levels=max_merge_levels,
        temperature=temperature,
        max_tokens=max_tokens,
        verbose=True,
        dry_run=True,
        output_dir=output_dir,
        max_skill_lines=500,
        max_references=256 if semantic else 5,
        patch_pipeline="markdown",
    )


def _ensure_new_output(output_dir: Path) -> None:
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)


def save_frozen_map(
    evolver: CombinedParallelSkillEvolver,
    patches: list[SemanticPatch],
    output_dir: Path,
    records: list[dict[str, Any]],
    batch_size: int,
) -> dict[str, Any]:
    map_dir = output_dir / "map_semantic"
    map_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for index, patch in enumerate(patches, start=1):
        relative = Path("map_semantic") / f"patch_{index:04d}.md"
        evolver._save_semantic_patch(patch, output_dir / relative)
        rows.append(
            {
                "patch_index": index,
                "batch_index": patch.batch_index,
                "path": relative.as_posix(),
                "item_count": len(patch.items),
            }
        )
    manifest = {
        "schema_version": "shared-map-manifest-v1",
        "record_count": len(records),
        "record_ids": [record["instance_id"] for record in records],
        "batch_size": batch_size,
        "batch_count": len(chunk_list(records, batch_size)),
        "patch_count": len(patches),
        "map_item_count": sum(row["item_count"] for row in rows),
        "patches": rows,
    }
    (map_dir / "map_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def load_frozen_map(output_dir: Path) -> tuple[list[SemanticPatch], dict[str, Any]]:
    manifest_path = output_dir / "map_semantic" / "map_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    patches: list[SemanticPatch] = []
    for row in manifest.get("patches", []):
        path = output_dir / row["path"]
        parsed, feedback = ParallelSkillEvolver._extract_semantic_patch_blocks_with_feedback(
            path.read_text(encoding="utf-8")
        )
        if len(parsed) != 1:
            raise ValueError(f"frozen MAP patch parse failed for {path}: {feedback}")
        parsed[0].batch_index = int(row["batch_index"])
        if len(parsed[0].items) != int(row["item_count"]):
            raise ValueError(f"frozen MAP item count changed: {path}")
        patches.append(parsed[0])
    if len(patches) != int(manifest.get("patch_count", -1)):
        raise ValueError("frozen MAP patch count mismatch")
    if len(enumerate_patch_items(patches)) != int(manifest.get("map_item_count", -1)):
        raise ValueError("frozen MAP item catalog mismatch")
    return patches, manifest


def execute_native(
    *,
    evolver: CombinedParallelSkillEvolver,
    records: list[dict[str, Any]],
    output_dir: Path,
    batch_size: int,
) -> dict[str, Any]:
    _ensure_new_output(output_dir)
    evolver.output_dir = output_dir
    state = evolver.read_skill_state()
    patches = evolver.run_map_phase_markdown(state, records)
    if not patches:
        raise RuntimeError("shared MAP produced no patches")
    map_manifest = save_frozen_map(evolver, patches, output_dir, records, batch_size)
    final_patch = evolver.run_reduce_phase_markdown(state, patches)
    if final_patch is None:
        raise RuntimeError("native global REDUCE produced no candidate bundle")
    native_dir = output_dir / "native_reduce"
    native_dir.mkdir(parents=True, exist_ok=True)
    native_unit = native_dir / "final_semantic_patch.md"
    evolver._save_semantic_patch(final_patch, native_unit)
    return {
        "method": "native-compressed",
        "shared_map": map_manifest,
        "native_unit": str(native_unit.resolve()),
        "candidate_unit_count": 1,
    }


def execute_semantic(
    *,
    evolver: SemanticReduceParallelSkillEvolver,
    shared_map_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    _ensure_new_output(output_dir)
    evolver.output_dir = output_dir
    patches, map_manifest = load_frozen_map(shared_map_dir)
    state = evolver.read_skill_state()
    result = evolver.run_reduce_phase_markdown(state, patches)
    if result is None or evolver.semantic_reduce_manifest is None:
        raise RuntimeError("semantic REDUCE produced no candidate families")
    return {
        "method": "semantic-reduce",
        "shared_map_source": str(shared_map_dir.resolve()),
        "shared_map": map_manifest,
        "semantic_manifest": str(
            (output_dir / "semantic_reduce" / "partition.json").resolve()
        ),
        "candidate_unit_count": len(evolver.semantic_family_bundles),
    }


def copy_shared_map(source: Path, destination: Path) -> None:
    """Optional immutable copy used when sealing a semantic branch run."""
    target = destination / "shared_map_snapshot"
    if target.exists():
        raise ValueError(f"shared MAP snapshot already exists: {target}")
    shutil.copytree(source / "map_semantic", target)
