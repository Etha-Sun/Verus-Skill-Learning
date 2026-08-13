#!/usr/bin/env python3
"""Resume v2 after discovery using hierarchical model-induced taxonomy."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (
    run_semantic_organization_v2 as base,
)


DEFAULT_OUTPUT = base.DEFAULT_OUTPUT
NODE_SCHEMA = base.SCHEMAS / "taxonomy_node_v3.schema.json"
DEFAULT_BATCH_NODES = 28
DEFAULT_FINAL_THRESHOLD = 48


def node_batches(nodes: list[dict[str, Any]], batch_nodes: int) -> list[list[dict[str, Any]]]:
    ordered = sorted(nodes, key=lambda node: hashlib.sha256(node["node_id"].encode()).hexdigest())
    return [ordered[index:index + batch_nodes] for index in range(0, len(ordered), batch_nodes)]


def source_node_ids(payload: dict[str, Any]) -> list[str]:
    return [source for family in payload["provisional_families"] for source in family["source_node_ids"]]


def node_id_audit(payload: dict[str, Any], prefix: str) -> dict[str, Any]:
    ids = [family["node_id"] for family in payload["provisional_families"]]
    expected = [f"{prefix}{index:03d}" for index in range(1, len(ids) + 1)]
    return {"valid": ids == expected, "expected_ids": expected, "actual_ids": ids}


def load_discovery(output: Path, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    batches = base.make_batches(memories, base.DEFAULT_BATCH_CHARS)
    groups: list[dict[str, Any]] = []
    for index, batch in enumerate(batches, 1):
        batch_id = f"batch_{index:03d}"
        path = output / "discovery" / batch_id
        validation = json.loads((path / "validation.json").read_text(encoding="utf-8"))
        if not validation.get("valid"):
            raise ValueError(f"discovery stage is not valid: {path}")
        payload = json.loads((path / "parsed.json").read_text(encoding="utf-8"))
        expected = [memory["local_card_id"] for memory in batch]
        audit = base.exact_once(base.discovery_ids(payload), expected)
        if not audit["valid"]:
            raise ValueError(f"discovery ID audit failed: {batch_id}")
        groups.extend(payload["local_groups"])
    if len({group["local_group_id"] for group in groups}) != len(groups):
        raise ValueError("duplicate local group IDs across discovery batches")
    return groups


def leaf_ids(node_id: str, children: dict[str, list[str]], leaves: set[str], stack: tuple[str, ...] = ()) -> list[str]:
    if node_id in leaves:
        return [node_id]
    if node_id in stack:
        raise ValueError(f"taxonomy hierarchy cycle: {stack + (node_id,)}")
    if node_id not in children:
        raise ValueError(f"taxonomy hierarchy references unknown node: {node_id}")
    return [leaf for child in children[node_id] for leaf in leaf_ids(child, children, leaves, stack + (node_id,))]


def exact_ids(items: Iterable[str], expected: Iterable[str]) -> dict[str, Any]:
    return base.exact_once(items, expected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--env-file", type=Path, default=base.DEFAULT_ENV)
    parser.add_argument("--taxonomy-batch-nodes", type=int, default=DEFAULT_BATCH_NODES)
    parser.add_argument("--taxonomy-final-threshold", type=int, default=DEFAULT_FINAL_THRESHOLD)
    parser.add_argument("--max-taxonomy-levels", type=int, default=5)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args(argv)
    output = args.output_root.resolve()
    if not output.is_dir():
        raise FileNotFoundError(f"v2 output is missing: {output}")
    config = base.load_config(args)
    memories = base.make_memories()
    memory_by_id = {memory["local_card_id"]: memory for memory in memories}
    groups = load_discovery(output, memories)
    leaf_group_ids = {group["local_group_id"] for group in groups}
    nodes = [{
        "node_id": group["local_group_id"], "title": group["label"],
        "observable_trigger": group["observable_trigger"], "missing_bridge": group["missing_bridge"],
        "mechanism_summary": group["mechanism_summary"], "boundary": group["boundary"],
    } for group in groups]
    children: dict[str, list[str]] = {}
    node_schema = base.load_schema(NODE_SCHEMA)
    reduce_system = (base.PROMPTS / "taxonomy_reduce_v3_system.txt").read_text(encoding="utf-8")
    configuration = output / "configuration"
    for source in [NODE_SCHEMA] + sorted(base.PROMPTS.glob("taxonomy_*_v3_*.txt")):
        target = configuration / source.name
        if not target.exists():
            shutil.copy2(source, target)
    hierarchy_summary: list[dict[str, Any]] = []
    level = 1
    while len(nodes) > args.taxonomy_final_threshold:
        if level > args.max_taxonomy_levels:
            raise ValueError(f"taxonomy did not reach final threshold after {args.max_taxonomy_levels} levels")
        batches = node_batches(nodes, args.taxonomy_batch_nodes)
        next_nodes: list[dict[str, Any]] = []
        print(f"[TAXONOMY L{level}] {len(nodes)} nodes -> {len(batches)} model batches", flush=True)
        for batch_index, batch in enumerate(batches, 1):
            batch_id = f"level_{level:02d}_batch_{batch_index:03d}"
            prefix = f"taxonomy_l{level:02d}_b{batch_index:03d}_family_"
            input_ids = [node["node_id"] for node in batch]
            user = base.render("taxonomy_reduce_v3_user.txt", LEVEL=str(level), BATCH_ID=batch_id, OUTPUT_NODE_ID_PREFIX=prefix, INPUT_NODE_COUNT=str(len(batch)), NODES_JSON=json.dumps(batch, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(node_schema, ensure_ascii=False, indent=2))
            payload = base.execute_stage(
                out=output / "taxonomy_hierarchy" / f"level_{level:02d}" / f"batch_{batch_index:03d}",
                stage="hierarchical_open_taxonomy", item_id=batch_id, system=reduce_system, user=user,
                schema=node_schema, config=config, execute=True, resume=args.resume,
                semantic_validator=lambda value, ids=input_ids, lvl=level, bid=batch_id, pre=prefix: base.combine_audits(
                    exact_ids(source_node_ids(value), ids), node_id_audit(value, pre),
                    {"valid": value["level"] == lvl and value["batch_id"] == bid, "expected_level": lvl, "actual_level": value["level"], "expected_batch": bid, "actual_batch": value["batch_id"]},
                ),
            )
            assert payload is not None
            for family in payload["provisional_families"]:
                children[family["node_id"]] = list(family["source_node_ids"])
                next_nodes.append({
                    "node_id": family["node_id"], "title": family["title"],
                    "observable_trigger": family["observable_trigger"], "missing_bridge": family["missing_bridge"],
                    "mechanism_summary": family["mechanism_summary"], "boundary": family["boundary"],
                })
        if len(next_nodes) >= len(nodes):
            raise ValueError(f"taxonomy level {level} did not reduce node count: {len(nodes)} -> {len(next_nodes)}")
        hierarchy_summary.append({"level": level, "input_nodes": len(nodes), "batch_count": len(batches), "output_nodes": len(next_nodes)})
        nodes = next_nodes
        level += 1
    final_schema = base.load_schema(base.TAXONOMY_SCHEMA)
    final_system = (base.PROMPTS / "taxonomy_final_v3_system.txt").read_text(encoding="utf-8")
    final_user = base.render("taxonomy_final_v3_user.txt", INPUT_NODE_COUNT=str(len(nodes)), NODES_JSON=json.dumps(nodes, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(final_schema, ensure_ascii=False, indent=2))
    current_node_ids = [node["node_id"] for node in nodes]
    print(f"[TAXONOMY FINAL] {len(nodes)} hierarchy nodes", flush=True)
    taxonomy = base.execute_stage(
        out=output / "taxonomy_hierarchy" / "final", stage="final_open_taxonomy", item_id="global_taxonomy",
        system=final_system, user=final_user, schema=final_schema, config=config, execute=True, resume=args.resume,
        semantic_validator=lambda value: exact_ids(base.taxonomy_group_ids(value), current_node_ids),
    )
    assert taxonomy is not None
    expanded = json.loads(json.dumps(taxonomy))
    for family in expanded["reference_families"]:
        family["source_group_ids"] = [leaf for node_id in family["source_group_ids"] for leaf in leaf_ids(node_id, children, leaf_group_ids)]
    expanded_group_ids = base.taxonomy_group_ids(expanded)
    expansion_audit = exact_ids(expanded_group_ids, leaf_group_ids)
    if not expansion_audit["valid"]:
        raise ValueError("hierarchical taxonomy did not expand to all local groups exactly once")
    group_by_id = {group["local_group_id"]: group for group in groups}
    family_memory_ids: list[str] = []
    for family in expanded["reference_families"]:
        ids = [member for group_id in family["source_group_ids"] for member in group_by_id[group_id]["member_ids"]]
        family["source_memory_ids"] = ids
        family_memory_ids.extend(ids)
    memory_audit = exact_ids(family_memory_ids, memory_by_id)
    if not memory_audit["valid"]:
        raise ValueError("hierarchical taxonomy did not cover all 284 memories exactly once")
    base.write_json(output / "taxonomy_hierarchy/hierarchy_summary.json", {"levels": hierarchy_summary, "final_input_nodes": len(nodes), "local_group_count": len(groups), "family_count": len(expanded["reference_families"]), "group_expansion_audit": expansion_audit, "memory_expansion_audit": memory_audit})
    base.write_json(output / "taxonomy_hierarchical.json", expanded)
    print(f"[TAXONOMY COMPLETE] {len(expanded['reference_families'])} model-induced families", flush=True)

    cluster_schema = base.load_schema(base.CLUSTER_SCHEMA)
    cluster_system = (base.PROMPTS / "cluster_v2_system.txt").read_text(encoding="utf-8")
    family_results: list[dict[str, Any]] = []
    for index, family in enumerate(expanded["reference_families"], 1):
        family_id = family["family_id"]
        ids = family.pop("source_memory_ids")
        family_memories = [memory_by_id[memory_id] for memory_id in ids]
        user = base.render("cluster_v2_user.txt", CLUSTER_ID=family_id, FAMILY_TITLE=family["title"], FAMILY_SCOPE=family["scope"], INCLUSION_CRITERIA=json.dumps(family["inclusion_criteria"], ensure_ascii=False), EXCLUSION_CRITERIA=json.dumps(family["exclusion_criteria"], ensure_ascii=False), INPUT_CARD_COUNT=str(len(ids)), CARDS_JSON=json.dumps(family_memories, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(cluster_schema, ensure_ascii=False, indent=2))
        print(f"[FAMILY {index}/{len(expanded['reference_families'])}] {family_id} {family['title']}: {len(ids)} memories", flush=True)
        payload = base.execute_stage(
            out=output / "families" / family_id, stage="family_consolidation", item_id=family_id,
            system=cluster_system, user=user, schema=cluster_schema, config=config, execute=True, resume=args.resume,
            semantic_validator=lambda value, expected=ids, fid=family_id: base.combine_audits(
                exact_ids(base.disposition_ids(value), expected), base.transfer_audit(value),
                {"valid": value["cluster_id"] == fid and value["input_card_count"] == len(expected), "expected_cluster_id": fid, "actual_cluster_id": value["cluster_id"], "expected_input_count": len(expected), "actual_input_count": value["input_card_count"]},
            ),
        )
        assert payload is not None
        family_results.append(payload)

    global_schema = base.load_schema(base.GLOBAL_SCHEMA)
    reconcile_system = (base.PROMPTS / "reconcile_v2_system.txt").read_text(encoding="utf-8")
    reconcile_user = base.render("reconcile_v2_user.txt", TOTAL_LOCAL_CARD_COUNT=str(len(memories)), CLUSTER_RESULTS_JSON=json.dumps(family_results, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(global_schema, ensure_ascii=False, indent=2))
    all_memory_ids = list(memory_by_id)
    print(f"[RECONCILIATION] {len(family_results)} families", flush=True)
    library = base.execute_stage(
        out=output / "reconciliation_v3", stage="global_reconciliation", item_id="global_library",
        system=reconcile_system, user=reconcile_user, schema=global_schema, config=config, execute=True, resume=args.resume,
        semantic_validator=lambda value: base.combine_audits(exact_ids(base.disposition_ids(value), all_memory_ids), base.transfer_audit(value)),
    )
    assert library is not None
    base.write_json(output / "global_skills_v3.json", library)

    layout_schema = base.load_schema(base.LAYOUT_SCHEMA)
    layout_system = (base.PROMPTS / "layout_v2_system.txt").read_text(encoding="utf-8")
    layout_user = base.render("layout_v2_user.txt", GLOBAL_SKILL_COUNT=str(len(library["global_skills"])), LIBRARY_JSON=json.dumps(library, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(layout_schema, ensure_ascii=False, indent=2))
    skill_ids = [skill["skill_id"] for skill in library["global_skills"]]
    print(f"[M/R LAYOUT] {len(skill_ids)} skills", flush=True)
    layout = base.execute_stage(
        out=output / "layout_v3", stage="model_driven_mr_layout", item_id="mr_layout",
        system=layout_system, user=layout_user, schema=layout_schema, config=config, execute=True, resume=args.resume,
        semantic_validator=lambda value: base.combine_audits(
            exact_ids((skill_id for reference in value["references"] for skill_id in reference["skill_ids"]), skill_ids),
            {"valid": len({reference["filename"] for reference in value["references"]}) == len(value["references"]), "reference_count": len(value["references"])},
        ),
    )
    assert layout is not None
    base.write_json(output / "mr_layout_v3.json", layout)
    skill_dir = output / "skill_v3/verus-proof-repair"
    if skill_dir.exists():
        raise FileExistsError(f"final skill already exists: {skill_dir}")
    base.render_skill(skill_dir, library, layout)
    final_audit = {
        "valid": True, "train_record_count": 77, "memory_count": 284,
        "local_group_count": len(groups), "taxonomy_levels": hierarchy_summary,
        "model_induced_family_count": len(expanded["reference_families"]),
        "global_skill_count": len(skill_ids), "model_designed_reference_count": len(layout["references"]),
        "host_defined_family_names": False, "host_keyword_routing": False,
        "heldout_inputs_used": False, "skill_dir": str(skill_dir),
    }
    base.write_json(output / "final_audit_v3.json", final_audit)
    manifest_path = output / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({"status": "completed_v3", "taxonomy_repair": "hierarchical model-induced reduction after the preserved single-pass taxonomy exhausted its reasoning budget", "model_induced_family_count": len(expanded["reference_families"]), "global_skill_count": len(skill_ids), "model_designed_reference_count": len(layout["references"]), "skill_dir": str(skill_dir)})
    base.write_json(manifest_path, manifest)
    print(json.dumps(final_audit, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
