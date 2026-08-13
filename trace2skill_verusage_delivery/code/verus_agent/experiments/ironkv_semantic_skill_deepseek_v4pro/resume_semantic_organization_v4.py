#!/usr/bin/env python3
"""Finish semantic organization without rewriting the whole library in one response.

V4 preserves the validated taxonomy and family consolidations from V3. It asks
the model for a compact global equivalence partition, calls the model only for
multi-card merges, deterministically promotes singleton cards, and then asks
for a compact M/R layout. This avoids the V3 32K-token truncation while keeping
every supported mechanism and every provenance disposition auditable.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (
    run_semantic_organization_v2 as base,
)


DEFAULT_OUTPUT = base.DEFAULT_OUTPUT
PARTITION_SCHEMA = base.SCHEMAS / "global_partition_v4.schema.json"
MERGE_SCHEMA = base.SCHEMAS / "global_group_merge_v4.schema.json"


def candidate_key(cluster_id: str, skill: dict[str, Any]) -> str:
    return f"{cluster_id}::{skill['candidate_id']}"


def load_family_results(output: Path, expected_memory_ids: Iterable[str]) -> list[dict[str, Any]]:
    family_root = output / "families"
    paths = sorted(family_root.glob("ironkv_family_*"))
    if not paths:
        raise FileNotFoundError(f"no family results found under {family_root}")
    results: list[dict[str, Any]] = []
    dispositions: list[str] = []
    for path in paths:
        validation = json.loads((path / "validation.json").read_text(encoding="utf-8"))
        if validation.get("valid") is not True:
            raise ValueError(f"invalid family result: {path}")
        payload = json.loads((path / "parsed.json").read_text(encoding="utf-8"))
        results.append(payload)
        dispositions.extend(base.disposition_ids(payload))
    audit = base.exact_once(dispositions, expected_memory_ids)
    if not audit["valid"]:
        raise ValueError(f"family provenance audit failed: {audit}")
    return results


def indexed_candidates(family_results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    compact: list[dict[str, Any]] = []
    full: dict[str, dict[str, Any]] = {}
    for family in family_results:
        cluster_id = family["cluster_id"]
        for skill in family["consolidated_skills"]:
            key = candidate_key(cluster_id, skill)
            if key in full:
                raise ValueError(f"duplicate candidate key: {key}")
            full[key] = skill
            compact.append({
                "candidate_key": key,
                "title": skill["title"],
                "family": skill["family"],
                "support_level": skill["support_level"],
                "applicability_signature": skill["applicability_signature"],
                "proof_obstacle": skill["proof_obstacle"],
                "mechanism": skill["mechanism"],
                "procedure": skill["procedure"],
                "why": skill["why"],
                "check": skill["check"],
                "contraindications": skill["contraindications"],
            })
    return compact, full


def partition_keys(payload: dict[str, Any]) -> list[str]:
    return [key for group in payload["groups"] for key in group["member_candidate_keys"]]


def partition_id_audit(payload: dict[str, Any]) -> dict[str, Any]:
    actual = [group["group_id"] for group in payload["groups"]]
    expected = [f"global_group_{index:03d}" for index in range(1, len(actual) + 1)]
    return {"valid": actual == expected, "expected_ids": expected, "actual_ids": actual}


def unique_strings(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def promote_singleton(skill: dict[str, Any], skill_id: str) -> dict[str, Any]:
    promoted = {key: value for key, value in skill.items() if key not in {"candidate_id", "decision"}}
    promoted["skill_id"] = skill_id
    promoted["status"] = "candidate_unvalidated"
    promoted["transfer_status"] = "untested"
    return promoted


def compact_library(library: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "skill_id", "title", "family", "support_level", "applicability_signature",
        "proof_obstacle", "mechanism", "procedure", "check", "contraindications",
        "limitations",
    )
    return {
        "status": library["status"],
        "library_summary": library["library_summary"],
        "skills": [{key: skill[key] for key in fields} for skill in library["global_skills"]],
        "unresolved_conflicts": library["unresolved_conflicts"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--env-file", type=Path, default=base.DEFAULT_ENV)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args(argv)
    output = args.output_root.resolve()
    if not output.is_dir():
        raise FileNotFoundError(f"existing semantic organization output is missing: {output}")
    config = base.load_config(args)
    memories = base.make_memories()
    memory_ids = [memory["local_card_id"] for memory in memories]
    family_results = load_family_results(output, memory_ids)
    compact, full_by_key = indexed_candidates(family_results)

    configuration = output / "configuration"
    sources = [PARTITION_SCHEMA, MERGE_SCHEMA, base.LAYOUT_SCHEMA]
    sources += [base.PROMPTS / name for name in (
        "global_partition_v4_system.txt", "global_partition_v4_user.txt",
        "global_group_merge_v4_system.txt", "global_group_merge_v4_user.txt",
        "layout_v2_system.txt", "layout_v4_user.txt",
    )]
    for source in sources:
        target = configuration / source.name
        if not target.exists():
            shutil.copy2(source, target)

    partition_schema = base.load_schema(PARTITION_SCHEMA)
    partition_system = (base.PROMPTS / "global_partition_v4_system.txt").read_text(encoding="utf-8")
    partition_user = base.render(
        "global_partition_v4_user.txt",
        INPUT_CANDIDATE_COUNT=str(len(compact)),
        COMPACT_CANDIDATES_JSON=json.dumps(compact, ensure_ascii=False, indent=2),
        SCHEMA_JSON=json.dumps(partition_schema, ensure_ascii=False, indent=2),
    )
    print(f"[GLOBAL PARTITION] {len(compact)} family candidates", flush=True)
    partition = base.execute_stage(
        out=output / "reconciliation_v4" / "partition",
        stage="compact_global_equivalence_partition", item_id="global_partition",
        system=partition_system, user=partition_user, schema=partition_schema,
        config=config, execute=True, resume=args.resume,
        semantic_validator=lambda value: base.combine_audits(
            base.exact_once(partition_keys(value), full_by_key), partition_id_audit(value),
        ),
    )
    assert partition is not None

    merge_schema = base.load_schema(MERGE_SCHEMA)
    merge_system = (base.PROMPTS / "global_group_merge_v4_system.txt").read_text(encoding="utf-8")
    global_skills: list[dict[str, Any]] = []
    singleton_count = 0
    model_merge_count = 0
    for index, group in enumerate(partition["groups"], 1):
        skill_id = f"verus_global_{index:03d}"
        members = [full_by_key[key] for key in group["member_candidate_keys"]]
        if len(members) == 1:
            global_skills.append(promote_singleton(members[0], skill_id))
            singleton_count += 1
            continue
        source_ids = [source for member in members for source in member["source_card_ids"]]
        source_trajectories = {trajectory for member in members for trajectory in member["source_trajectories"]}
        merge_user = base.render(
            "global_group_merge_v4_user.txt", GROUP_ID=group["group_id"],
            OUTPUT_SKILL_ID=skill_id, GROUP_TITLE=group["title"],
            MERGE_RATIONALE=group["merge_rationale"],
            INPUT_CARDS_JSON=json.dumps(members, ensure_ascii=False, indent=2),
            SCHEMA_JSON=json.dumps(merge_schema, ensure_ascii=False, indent=2),
        )
        print(f"[GROUP MERGE {index}/{len(partition['groups'])}] {group['group_id']}: {len(members)} cards", flush=True)
        merged = base.execute_stage(
            out=output / "reconciliation_v4" / "merged_groups" / group["group_id"],
            stage="semantic_equivalence_group_merge", item_id=group["group_id"],
            system=merge_system, user=merge_user, schema=merge_schema,
            config=config, execute=True, resume=args.resume,
            semantic_validator=lambda value, sid=skill_id, sources=source_ids, trajectories=source_trajectories: base.combine_audits(
                {"valid": value["merged_skill"]["skill_id"] == sid,
                 "expected_skill_id": sid, "actual_skill_id": value["merged_skill"]["skill_id"]},
                base.exact_once(value["merged_skill"]["source_card_ids"], sources),
                {"valid": set(value["merged_skill"]["source_trajectories"]) == trajectories,
                 "expected_trajectories": sorted(trajectories),
                 "actual_trajectories": sorted(value["merged_skill"]["source_trajectories"])},
                base.transfer_audit({"global_skills": [value["merged_skill"]], "excluded_cards": []}),
            ),
        )
        assert merged is not None
        global_skills.append(merged["merged_skill"])
        model_merge_count += 1

    excluded = [item for family in family_results for item in family["excluded_cards"]]
    library = {
        "status": "candidate_unvalidated",
        "library_summary": (
            f"Data-driven IronKV Verus library reconciled from {len(compact)} family-level candidates "
            f"into {len(global_skills)} evidence-preserving semantic skills."
        ),
        "global_skills": global_skills,
        "excluded_cards": excluded,
        "unresolved_conflicts": partition["unresolved_conflicts"],
    }
    global_schema = base.load_schema(base.GLOBAL_SCHEMA)
    schema_errors = base.validate_schema(library, global_schema)
    provenance = base.exact_once(base.disposition_ids(library), memory_ids)
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
        raise ValueError(f"assembled global library is invalid: {output / 'reconciliation_v4/library_validation.json'}")
    base.write_json(output / "global_skills_v4.json", library)

    layout_schema = base.load_schema(base.LAYOUT_SCHEMA)
    layout_system = (base.PROMPTS / "layout_v2_system.txt").read_text(encoding="utf-8")
    layout_user = base.render(
        "layout_v4_user.txt", GLOBAL_SKILL_COUNT=str(len(global_skills)),
        COMPACT_LIBRARY_JSON=json.dumps(compact_library(library), ensure_ascii=False, indent=2),
        SCHEMA_JSON=json.dumps(layout_schema, ensure_ascii=False, indent=2),
    )
    skill_ids = [skill["skill_id"] for skill in global_skills]
    print(f"[M/R LAYOUT] {len(skill_ids)} skills", flush=True)
    layout = base.execute_stage(
        out=output / "layout_v4", stage="compact_model_driven_mr_layout", item_id="mr_layout",
        system=layout_system, user=layout_user, schema=layout_schema,
        config=config, execute=True, resume=args.resume,
        semantic_validator=lambda value: base.combine_audits(
            base.exact_once(
                (skill_id for reference in value["references"] for skill_id in reference["skill_ids"]),
                skill_ids,
            ),
            {"valid": len({reference["filename"] for reference in value["references"]}) == len(value["references"]),
             "reference_count": len(value["references"])},
        ),
    )
    assert layout is not None
    base.write_json(output / "mr_layout_v4.json", layout)
    skill_dir = output / "skill_v4" / "verus-proof-repair"
    if skill_dir.exists():
        raise FileExistsError(f"final skill already exists: {skill_dir}")
    base.render_skill(skill_dir, library, layout)

    final_audit = {
        "valid": True,
        "train_record_count": 77,
        "memory_count": 284,
        "family_candidate_count": len(compact),
        "global_skill_count": len(global_skills),
        "singleton_promotions": singleton_count,
        "model_merged_groups": model_merge_count,
        "model_designed_reference_count": len(layout["references"]),
        "host_defined_family_names": False,
        "host_keyword_routing": False,
        "heldout_inputs_used": False,
        "skill_dir": str(skill_dir),
    }
    base.write_json(output / "final_audit_v4.json", final_audit)
    manifest_path = output / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "status": "completed_v4", "completed_at": base.utc_now(),
        "v3_reconciliation_failure_preserved": True,
        "v4_reconciliation": "compact global partition plus isolated multi-card merges",
        "global_skill_count": len(global_skills),
        "model_designed_reference_count": len(layout["references"]),
        "skill_dir": str(skill_dir),
    })
    base.write_json(manifest_path, manifest)
    print(json.dumps(final_audit, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
