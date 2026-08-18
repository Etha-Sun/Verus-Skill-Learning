#!/usr/bin/env python3
"""Build the train-only semantic-v4 library and render a zero-reference M-core."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

import tiktoken


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_CODE = REPOSITORY_ROOT / "trace2skill_verusage_baseline_test" / "code"
sys.path.insert(0, str(BASELINE_CODE))

from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (  # noqa: E402
    resume_semantic_organization_v3 as v3,
)
from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (  # noqa: E402
    resume_semantic_organization_v4 as v4,
)
from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (  # noqa: E402
    run_semantic_organization_v2 as base,
)
from global_skill_experiment.gate import hash_skill_tree  # noqa: E402

PROMPT_ROOT = EXPERIMENT_ROOT / "prompts" / "m_core_semantic_v4"

PROMPT_NAMES = (
    "discover_v2_system.txt",
    "discover_v2_user.txt",
    "taxonomy_reduce_v3_system.txt",
    "taxonomy_reduce_v3_user.txt",
    "taxonomy_final_v3_system.txt",
    "taxonomy_final_v3_user.txt",
    "cluster_v2_system.txt",
    "cluster_v2_user.txt",
    "global_partition_v4_system.txt",
    "global_partition_v4_user.txt",
    "global_group_merge_v4_system.txt",
    "global_group_merge_v4_user.txt",
    "layout_v2_system.txt",
    "layout_v4_user.txt",
)
SCHEMA_NAMES = (
    "discovery_v2.schema.json",
    "taxonomy_node_v3.schema.json",
    "taxonomy_v2.schema.json",
    "cluster_consolidation.schema.json",
    "global_partition_v4.schema.json",
    "global_group_merge_v4.schema.json",
    "global_skill_library.schema.json",
    "layout_v2.schema.json",
)
NEUTRAL_SEED = (
    BASELINE_CODE / "verus_agent" / "skill_evolution" / "neutral_seed" / "verus-proof-repair"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def assert_below(path: Path, root: Path) -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if resolved_path == resolved_root or resolved_root not in resolved_path.parents:
        raise ValueError(f"output must be a strict child of run root: {resolved_path}")


def load_prompt(name: str) -> str:
    if name not in PROMPT_NAMES:
        raise ValueError(f"unknown M-core prompt: {name}")
    path = PROMPT_ROOT / name
    if not path.is_file():
        raise FileNotFoundError(f"missing local M-core prompt: {path}")
    return path.read_text(encoding="utf-8")


def adapted_schema(name: str) -> dict[str, Any]:
    payload = json.loads((base.SCHEMAS / name).read_text(encoding="utf-8"))
    if name == "taxonomy_v2.schema.json":
        family = payload["properties"]["reference_families"]["items"]
        family["properties"]["family_id"]["pattern"] = "^verus_family_[0-9]{3}$"
    return payload


def render_prompt(name: str, **values: str) -> str:
    text = load_prompt(name)
    for key, value in values.items():
        marker = "{{" + key + "}}"
        if text.count(marker) != 1:
            raise ValueError(f"template marker {marker} must occur once in {name}")
        text = text.replace(marker, value)
    if "{{" in text or "}}" in text:
        raise ValueError(f"unrendered template marker in {name}")
    return text


def load_memories(combined_records: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_path = combined_records.with_name("run_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or manifest.get("record_count") != 40:
        raise ValueError("shared memory manifest is not the frozen complete 40-task set")
    if sha256_file(combined_records) != manifest.get("combined_records_file_sha256"):
        raise ValueError("shared combined_records hash does not match its manifest")
    records = json.loads(combined_records.read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != 40:
        raise ValueError("combined_records must contain exactly 40 records")
    memories: list[dict[str, Any]] = []
    for record in records:
        instance_id = str(record["instance_id"])
        for item in record["items"]:
            local_id = f"{instance_id}::{item['type']}::{int(item['number']):03d}"
            memories.append(
                {
                    "local_card_id": local_id,
                    "source_trajectory_key": instance_id,
                    "source_file": record["source_file"],
                    "record_source": record["record_source"],
                    "evidence_type": item["type"],
                    "memory": item,
                }
            )
    ids = [memory["local_card_id"] for memory in memories]
    expected_count = int(manifest["memory_item_count"])
    if len(memories) != expected_count or len(ids) != len(set(ids)):
        raise ValueError("shared memories are not the expected unique frozen items")
    memories.sort(
        key=lambda memory: hashlib.sha256(memory["local_card_id"].encode()).hexdigest()
    )
    return memories, manifest


def exact_once(actual: Iterable[str], expected: Iterable[str]) -> dict[str, Any]:
    return base.exact_once(actual, expected)


def snapshot_configuration(output: Path) -> dict[str, dict[str, str]]:
    configuration = output / "configuration"
    configuration.mkdir(parents=True, exist_ok=True)
    prompt_hashes: dict[str, str] = {}
    schema_hashes: dict[str, str] = {}
    for name in PROMPT_NAMES:
        text = load_prompt(name)
        (configuration / name).write_text(text, encoding="utf-8")
        prompt_hashes[name] = sha256_bytes(text.encode())
    for name in SCHEMA_NAMES:
        text = json.dumps(adapted_schema(name), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (configuration / name).write_text(text, encoding="utf-8")
        schema_hashes[name] = sha256_bytes(text.encode())
    return {"prompt_hashes": prompt_hashes, "schema_hashes": schema_hashes}


def run_discovery(
    output: Path,
    memories: list[dict[str, Any]],
    batches: list[list[dict[str, Any]]],
    config: dict[str, Any],
    execute: bool,
    resume: bool,
) -> list[dict[str, Any]]:
    schema = adapted_schema("discovery_v2.schema.json")
    system = load_prompt("discover_v2_system.txt")
    discovered: list[dict[str, Any]] = []
    for index, batch in enumerate(batches, 1):
        batch_id = f"batch_{index:03d}"
        expected_ids = [item["local_card_id"] for item in batch]
        user = render_prompt(
            "discover_v2_user.txt",
            BATCH_ID=batch_id,
            INPUT_MEMORY_COUNT=str(len(batch)),
            CARDS_JSON=json.dumps(batch, ensure_ascii=False, indent=2),
            SCHEMA_JSON=json.dumps(schema, ensure_ascii=False, indent=2),
        )
        print(f"[DISCOVERY {index}/{len(batches)}] {len(batch)} memories", flush=True)
        payload = base.execute_stage(
            out=output / "discovery" / batch_id,
            stage="open_taxonomy_discovery",
            item_id=batch_id,
            system=system,
            user=user,
            schema=schema,
            config=config,
            execute=execute,
            resume=resume,
            semantic_validator=lambda value, ids=expected_ids, bid=batch_id: base.combine_audits(
                exact_once(base.discovery_ids(value), ids),
                {
                    "valid": value["batch_id"] == bid,
                    "expected_batch_id": bid,
                    "actual_batch_id": value["batch_id"],
                },
            ),
        )
        if payload:
            discovered.extend(payload["local_groups"])
    if execute:
        group_ids = [group["local_group_id"] for group in discovered]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("discovery produced duplicate local_group_id values")
    return discovered


def run_taxonomy_and_families(
    output: Path,
    memories: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    config: dict[str, Any],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    memory_by_id = {memory["local_card_id"]: memory for memory in memories}
    leaf_group_ids = {group["local_group_id"] for group in groups}
    nodes = [
        {
            "node_id": group["local_group_id"],
            "title": group["label"],
            "observable_trigger": group["observable_trigger"],
            "missing_bridge": group["missing_bridge"],
            "mechanism_summary": group["mechanism_summary"],
            "boundary": group["boundary"],
        }
        for group in groups
    ]
    children: dict[str, list[str]] = {}
    node_schema = adapted_schema("taxonomy_node_v3.schema.json")
    reduce_system = load_prompt("taxonomy_reduce_v3_system.txt")
    hierarchy: list[dict[str, Any]] = []
    level = 1
    while len(nodes) > args.taxonomy_final_threshold:
        if level > args.max_taxonomy_levels:
            raise ValueError("taxonomy exceeded the frozen maximum hierarchy depth")
        batches = v3.node_batches(nodes, args.taxonomy_batch_nodes)
        next_nodes: list[dict[str, Any]] = []
        print(f"[TAXONOMY L{level}] {len(nodes)} nodes / {len(batches)} batches", flush=True)
        for batch_index, batch in enumerate(batches, 1):
            batch_id = f"level_{level:02d}_batch_{batch_index:03d}"
            prefix = f"taxonomy_l{level:02d}_b{batch_index:03d}_family_"
            input_ids = [node["node_id"] for node in batch]
            user = render_prompt(
                "taxonomy_reduce_v3_user.txt",
                LEVEL=str(level),
                BATCH_ID=batch_id,
                OUTPUT_NODE_ID_PREFIX=prefix,
                INPUT_NODE_COUNT=str(len(batch)),
                NODES_JSON=json.dumps(batch, ensure_ascii=False, indent=2),
                SCHEMA_JSON=json.dumps(node_schema, ensure_ascii=False, indent=2),
            )
            payload = base.execute_stage(
                out=output / "taxonomy_hierarchy" / f"level_{level:02d}" / f"batch_{batch_index:03d}",
                stage="hierarchical_open_taxonomy",
                item_id=batch_id,
                system=reduce_system,
                user=user,
                schema=node_schema,
                config=config,
                execute=True,
                resume=args.resume,
                semantic_validator=lambda value, ids=input_ids, lvl=level, bid=batch_id, pre=prefix: base.combine_audits(
                    exact_once(v3.source_node_ids(value), ids),
                    v3.node_id_audit(value, pre),
                    {
                        "valid": value["level"] == lvl and value["batch_id"] == bid,
                        "expected_level": lvl,
                        "actual_level": value["level"],
                        "expected_batch": bid,
                        "actual_batch": value["batch_id"],
                    },
                ),
            )
            assert payload is not None
            for family in payload["provisional_families"]:
                children[family["node_id"]] = list(family["source_node_ids"])
                next_nodes.append(
                    {
                        "node_id": family["node_id"],
                        "title": family["title"],
                        "observable_trigger": family["observable_trigger"],
                        "missing_bridge": family["missing_bridge"],
                        "mechanism_summary": family["mechanism_summary"],
                        "boundary": family["boundary"],
                    }
                )
        if len(next_nodes) >= len(nodes):
            raise ValueError("taxonomy hierarchy failed to reduce node count")
        hierarchy.append(
            {
                "level": level,
                "input_nodes": len(nodes),
                "batch_count": len(batches),
                "output_nodes": len(next_nodes),
            }
        )
        nodes = next_nodes
        level += 1

    taxonomy_schema = adapted_schema("taxonomy_v2.schema.json")
    taxonomy_user = render_prompt(
        "taxonomy_final_v3_user.txt",
        INPUT_NODE_COUNT=str(len(nodes)),
        NODES_JSON=json.dumps(nodes, ensure_ascii=False, indent=2),
        SCHEMA_JSON=json.dumps(taxonomy_schema, ensure_ascii=False, indent=2),
    )
    current_node_ids = [node["node_id"] for node in nodes]
    print(f"[TAXONOMY FINAL] {len(nodes)} hierarchy nodes", flush=True)
    taxonomy = base.execute_stage(
        out=output / "taxonomy_hierarchy" / "final",
        stage="final_open_taxonomy",
        item_id="global_taxonomy",
        system=load_prompt("taxonomy_final_v3_system.txt"),
        user=taxonomy_user,
        schema=taxonomy_schema,
        config=config,
        execute=True,
        resume=args.resume,
        semantic_validator=lambda value: exact_once(
            base.taxonomy_group_ids(value), current_node_ids
        ),
    )
    assert taxonomy is not None
    expanded = copy.deepcopy(taxonomy)
    for family in expanded["reference_families"]:
        family["source_group_ids"] = [
            leaf
            for node_id in family["source_group_ids"]
            for leaf in v3.leaf_ids(node_id, children, leaf_group_ids)
        ]
    group_audit = exact_once(base.taxonomy_group_ids(expanded), leaf_group_ids)
    if not group_audit["valid"]:
        raise ValueError("taxonomy expansion lost or duplicated discovery groups")
    group_by_id = {group["local_group_id"]: group for group in groups}
    all_family_memory_ids: list[str] = []
    for family in expanded["reference_families"]:
        ids = [
            member
            for group_id in family["source_group_ids"]
            for member in group_by_id[group_id]["member_ids"]
        ]
        family["source_memory_ids"] = ids
        all_family_memory_ids.extend(ids)
    memory_audit = exact_once(all_family_memory_ids, memory_by_id)
    if not memory_audit["valid"]:
        raise ValueError("taxonomy expansion lost or duplicated frozen memories")
    base.write_json(
        output / "taxonomy_hierarchy" / "hierarchy_summary.json",
        {
            "levels": hierarchy,
            "final_input_nodes": len(nodes),
            "local_group_count": len(groups),
            "family_count": len(expanded["reference_families"]),
            "group_expansion_audit": group_audit,
            "memory_expansion_audit": memory_audit,
        },
    )
    base.write_json(output / "taxonomy_hierarchical.json", expanded)

    cluster_schema = adapted_schema("cluster_consolidation.schema.json")
    family_results: list[dict[str, Any]] = []
    for index, family in enumerate(expanded["reference_families"], 1):
        family_id = family["family_id"]
        ids = family["source_memory_ids"]
        family_memories = [memory_by_id[memory_id] for memory_id in ids]
        user = render_prompt(
            "cluster_v2_user.txt",
            CLUSTER_ID=family_id,
            FAMILY_TITLE=family["title"],
            FAMILY_SCOPE=family["scope"],
            INCLUSION_CRITERIA=json.dumps(family["inclusion_criteria"], ensure_ascii=False),
            EXCLUSION_CRITERIA=json.dumps(family["exclusion_criteria"], ensure_ascii=False),
            INPUT_CARD_COUNT=str(len(ids)),
            CARDS_JSON=json.dumps(family_memories, ensure_ascii=False, indent=2),
            SCHEMA_JSON=json.dumps(cluster_schema, ensure_ascii=False, indent=2),
        )
        print(f"[FAMILY {index}/{len(expanded['reference_families'])}] {family_id}: {len(ids)}", flush=True)
        payload = base.execute_stage(
            out=output / "families" / family_id,
            stage="family_consolidation",
            item_id=family_id,
            system=load_prompt("cluster_v2_system.txt"),
            user=user,
            schema=cluster_schema,
            config=config,
            execute=True,
            resume=args.resume,
            semantic_validator=lambda value, expected=ids, fid=family_id: base.combine_audits(
                exact_once(base.disposition_ids(value), expected),
                base.transfer_audit(value),
                {
                    "valid": value["cluster_id"] == fid
                    and value["input_card_count"] == len(expected),
                    "expected_cluster_id": fid,
                    "actual_cluster_id": value["cluster_id"],
                    "expected_input_count": len(expected),
                    "actual_input_count": value["input_card_count"],
                },
            ),
        )
        assert payload is not None
        family_results.append(payload)
    return family_results


def run_reconciliation_and_layout(
    output: Path,
    memories: list[dict[str, Any]],
    family_results: list[dict[str, Any]],
    config: dict[str, Any],
    resume: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    compact, full_by_key = v4.indexed_candidates(family_results)
    partition_schema = adapted_schema("global_partition_v4.schema.json")
    partition_user = render_prompt(
        "global_partition_v4_user.txt",
        INPUT_CANDIDATE_COUNT=str(len(compact)),
        COMPACT_CANDIDATES_JSON=json.dumps(compact, ensure_ascii=False, indent=2),
        SCHEMA_JSON=json.dumps(partition_schema, ensure_ascii=False, indent=2),
    )
    print(f"[GLOBAL PARTITION] {len(compact)} family candidates", flush=True)
    partition = base.execute_stage(
        out=output / "reconciliation_v4" / "partition",
        stage="compact_global_equivalence_partition",
        item_id="global_partition",
        system=load_prompt("global_partition_v4_system.txt"),
        user=partition_user,
        schema=partition_schema,
        config=config,
        execute=True,
        resume=resume,
        semantic_validator=lambda value: base.combine_audits(
            exact_once(v4.partition_keys(value), full_by_key),
            v4.partition_id_audit(value),
        ),
    )
    assert partition is not None

    merge_schema = adapted_schema("global_group_merge_v4.schema.json")
    global_skills: list[dict[str, Any]] = []
    singleton_count = 0
    model_merge_count = 0
    for index, group in enumerate(partition["groups"], 1):
        skill_id = f"verus_global_{index:03d}"
        members = [full_by_key[key] for key in group["member_candidate_keys"]]
        if len(members) == 1:
            global_skills.append(v4.promote_singleton(members[0], skill_id))
            singleton_count += 1
            continue
        source_ids = [source for member in members for source in member["source_card_ids"]]
        source_trajectories = {
            trajectory for member in members for trajectory in member["source_trajectories"]
        }
        merge_user = render_prompt(
            "global_group_merge_v4_user.txt",
            GROUP_ID=group["group_id"],
            OUTPUT_SKILL_ID=skill_id,
            GROUP_TITLE=group["title"],
            MERGE_RATIONALE=group["merge_rationale"],
            INPUT_CARDS_JSON=json.dumps(members, ensure_ascii=False, indent=2),
            SCHEMA_JSON=json.dumps(merge_schema, ensure_ascii=False, indent=2),
        )
        print(f"[GROUP MERGE {index}/{len(partition['groups'])}] {len(members)} cards", flush=True)
        merged = base.execute_stage(
            out=output / "reconciliation_v4" / "merged_groups" / group["group_id"],
            stage="semantic_equivalence_group_merge",
            item_id=group["group_id"],
            system=load_prompt("global_group_merge_v4_system.txt"),
            user=merge_user,
            schema=merge_schema,
            config=config,
            execute=True,
            resume=resume,
            semantic_validator=lambda value, sid=skill_id, sources=source_ids, trajectories=source_trajectories: base.combine_audits(
                {
                    "valid": value["merged_skill"]["skill_id"] == sid,
                    "expected_skill_id": sid,
                    "actual_skill_id": value["merged_skill"]["skill_id"],
                },
                exact_once(value["merged_skill"]["source_card_ids"], sources),
                {
                    "valid": set(value["merged_skill"]["source_trajectories"])
                    == trajectories,
                    "expected_trajectories": sorted(trajectories),
                    "actual_trajectories": sorted(
                        value["merged_skill"]["source_trajectories"]
                    ),
                },
                base.transfer_audit(
                    {"global_skills": [value["merged_skill"]], "excluded_cards": []}
                ),
            ),
        )
        assert merged is not None
        global_skills.append(merged["merged_skill"])
        model_merge_count += 1

    memory_ids = [memory["local_card_id"] for memory in memories]
    excluded = [item for family in family_results for item in family["excluded_cards"]]
    library = {
        "status": "candidate_unvalidated",
        "library_summary": (
            f"Cross-project Verus library reconciled from {len(compact)} family candidates "
            f"into {len(global_skills)} evidence-preserving semantic skills."
        ),
        "global_skills": global_skills,
        "excluded_cards": excluded,
        "unresolved_conflicts": partition["unresolved_conflicts"],
    }
    global_schema = adapted_schema("global_skill_library.schema.json")
    schema_errors = base.validate_schema(library, global_schema)
    provenance = exact_once(base.disposition_ids(library), memory_ids)
    transfer = base.transfer_audit(library)
    library_validation = {
        "valid": not schema_errors and provenance["valid"] and transfer["valid"],
        "schema_errors": schema_errors,
        "semantic_audit": base.combine_audits(provenance, transfer),
        "input_candidate_count": len(compact),
        "output_skill_count": len(global_skills),
        "singleton_promotions": singleton_count,
        "model_merged_groups": model_merge_count,
    }
    base.write_json(output / "reconciliation_v4" / "library_validation.json", library_validation)
    if not library_validation["valid"]:
        raise ValueError("assembled global library failed schema/provenance validation")
    base.write_json(output / "global_skills_v4.json", library)

    layout_schema = adapted_schema("layout_v2.schema.json")
    layout_user = render_prompt(
        "layout_v4_user.txt",
        GLOBAL_SKILL_COUNT=str(len(global_skills)),
        COMPACT_LIBRARY_JSON=json.dumps(v4.compact_library(library), ensure_ascii=False, indent=2),
        SCHEMA_JSON=json.dumps(layout_schema, ensure_ascii=False, indent=2),
    )
    skill_ids = [skill["skill_id"] for skill in global_skills]
    print(f"[M-CORE LAYOUT] {len(skill_ids)} skills", flush=True)
    layout = base.execute_stage(
        out=output / "layout_v4",
        stage="compact_model_driven_mr_layout",
        item_id="mr_layout",
        system=load_prompt("layout_v2_system.txt"),
        user=layout_user,
        schema=layout_schema,
        config=config,
        execute=True,
        resume=resume,
        semantic_validator=lambda value: base.combine_audits(
            exact_once(
                (
                    skill_id
                    for reference in value["references"]
                    for skill_id in reference["skill_ids"]
                ),
                skill_ids,
            ),
            {
                "valid": len({ref["filename"] for ref in value["references"]})
                == len(value["references"]),
                "reference_count": len(value["references"]),
            },
        ),
    )
    assert layout is not None
    base.write_json(output / "mr_layout_v4.json", layout)
    counts = {
        "family_candidate_count": len(compact),
        "global_skill_count": len(global_skills),
        "singleton_promotions": singleton_count,
        "model_merged_groups": model_merge_count,
        "model_designed_reference_count": len(layout["references"]),
    }
    return library, layout, counts


def render_root_only(skill_dir: Path, layout: dict[str, Any]) -> dict[str, Any]:
    if skill_dir.exists():
        raise FileExistsError(f"M-core skill already exists: {skill_dir}")
    shutil.copytree(NEUTRAL_SEED, skill_dir)
    references = skill_dir / "references"
    if references.exists():
        if any(references.iterdir()):
            raise ValueError("neutral seed unexpectedly contains reference files")
        references.rmdir()
    root = layout["root"]
    lines = [
        "---",
        "name: verus-proof-repair",
        f"description: {root['description']}",
        "---",
        "",
        f"# {root['title']}",
        "",
        "## Core procedures",
        "",
    ]
    for procedure in root["core_procedures"]:
        lines.extend([f"### {procedure['title']}", "", f"**When:** {procedure['when']}", ""])
        lines.extend(f"{index}. {step}" for index, step in enumerate(procedure["steps"], 1))
        lines.extend(["", f"**Check:** {procedure['check']}", ""])
    lines.extend(["## Safety and stopping rules", ""])
    lines.extend(f"- {rule}" for rule in root["safety_and_stopping_rules"])
    text = "\n".join(lines).rstrip() + "\n"
    forbidden = [
        skill_id
        for reference in layout["references"]
        for skill_id in reference["skill_ids"]
    ]
    forbidden.extend(reference["filename"] for reference in layout["references"])
    forbidden.extend(["references/", "## Reference map", "## Progressive reference consultation"])
    leaked = [value for value in forbidden if value and value in text]
    if leaked:
        raise ValueError(f"root-only rendering leaked reference routes: {leaked}")
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(text, encoding="utf-8")
    encoding = tiktoken.get_encoding("o200k_base")
    files = sorted(path.relative_to(skill_dir).as_posix() for path in skill_dir.rglob("*") if path.is_file())
    if files != ["SKILL.md", "agents/openai.yaml"]:
        raise ValueError(f"unexpected root-only skill files: {files}")
    return {
        "skill_tree_files": files,
        "skill_md_sha256": sha256_file(skill_path),
        "skill_tree_sha256": hash_skill_tree(skill_dir),
        "utf8_bytes": len(text.encode()),
        "line_count": len(text.splitlines()),
        "o200k_base_token_count": len(encoding.encode(text)),
        "reference_file_count": 0,
        "reference_routes_present": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--combined-records", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--discovery-batch-chars", type=int, default=42000)
    parser.add_argument("--taxonomy-batch-nodes", type=int, default=28)
    parser.add_argument("--taxonomy-final-threshold", type=int, default=48)
    parser.add_argument("--max-taxonomy-levels", type=int, default=5)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args(argv)

    output = args.output_root.resolve()
    run_root = args.run_root.resolve()
    assert_below(output, run_root)
    if output.exists() and not args.resume:
        raise FileExistsError(f"output exists; use --resume: {output}")
    output.mkdir(parents=True, exist_ok=True)
    memories, source_manifest = load_memories(args.combined_records.resolve())
    batches = base.make_batches(memories, args.discovery_batch_chars)
    config = base.load_config(args)
    configuration_hashes = snapshot_configuration(output)
    base.write_json(output / "input" / "normalized_memories.json", {"memory_count": len(memories), "memories": memories})
    base.write_json(
        output / "input" / "discovery_batches.json",
        {
            "batching_uses_memory_content": False,
            "deterministic_order": "sha256(local_card_id)",
            "max_serialized_memory_chars_per_batch": args.discovery_batch_chars,
            "batch_count": len(batches),
            "batches": [
                {
                    "batch_id": f"batch_{index:03d}",
                    "memory_count": len(batch),
                    "memory_ids": [item["local_card_id"] for item in batch],
                    "serialized_chars": len(json.dumps(batch, ensure_ascii=False)),
                }
                for index, batch in enumerate(batches, 1)
            ],
        },
    )
    manifest_path = output / "run_manifest.json"
    manifest = {
        "schema_version": 1,
        "experiment": "cross_task_semantic_v4_m_core_20260815",
        "created_at": base.utc_now(),
        "status": "dry_run" if args.dry_run else "running",
        "combined_records_sha256": sha256_file(args.combined_records),
        "shared_memory_set_sha256": source_manifest["shared_memory_set_sha256"],
        "train_record_count": 40,
        "memory_count": len(memories),
        "discovery_batch_count": len(batches),
        "taxonomy": "model-induced hierarchical semantic organization; no host keyword routing",
        "heldout_inputs_used": False,
        "prompt_bundle": {
            "contract_version": 1,
            "repository_path": PROMPT_ROOT.relative_to(REPOSITORY_ROOT).as_posix(),
            "runtime_text_replacement": False,
        },
        "configuration": base.public_config(config),
        **configuration_hashes,
    }
    if not manifest_path.exists():
        base.write_json(manifest_path, manifest)
    elif args.resume:
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ("combined_records_sha256", "shared_memory_set_sha256", "prompt_bundle", "configuration", "prompt_hashes", "schema_hashes"):
            if prior.get(key) != manifest[key]:
                raise ValueError(f"resume mismatch: {key}")

    groups = run_discovery(output, memories, batches, config, args.execute, args.resume)
    if args.dry_run:
        base.write_json(
            output / "dry_run_summary.json",
            {
                "network_requests": 0,
                "memory_count": len(memories),
                "discovery_requests_planned": len(batches),
                "later_request_count_is_data_dependent": True,
                "all_memories_included_exactly_once": True,
            },
        )
        return 0

    family_results = run_taxonomy_and_families(output, memories, groups, config, args)
    _, layout, counts = run_reconciliation_and_layout(
        output, memories, family_results, config, args.resume
    )
    skill_dir = output / "m_core" / "skill" / "verus-proof-repair"
    root_audit = render_root_only(skill_dir, layout)
    final_audit = {
        "valid": True,
        "train_record_count": 40,
        "memory_count": len(memories),
        **counts,
        **root_audit,
        "host_defined_family_names": False,
        "host_keyword_routing": False,
        "heldout_inputs_used": False,
        "skill_dir": str(skill_dir),
    }
    base.write_json(output / "m_core" / "m_core_manifest.json", final_audit)
    completed = json.loads(manifest_path.read_text(encoding="utf-8"))
    completed.update(
        {
            "status": "complete",
            "completed_at": base.utc_now(),
            "global_skill_count": counts["global_skill_count"],
            "model_designed_reference_count": counts["model_designed_reference_count"],
            "rendered_reference_count": 0,
            "m_core_skill_dir": str(skill_dir),
            "m_core_skill_md_sha256": root_audit["skill_md_sha256"],
        }
    )
    base.write_json(manifest_path, completed)
    print(json.dumps(final_audit, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
