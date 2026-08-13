#!/usr/bin/env python3
"""Build a data-driven semantic IronKV skill from shared train77 memories.

DeepSeek, rather than host keyword rules, induces the mechanism taxonomy and
the final Trace2Skill M/R layout. Every memory is presented in full once during
discovery and again during its assigned family consolidation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dotenv import dotenv_values
from jsonschema import Draft202012Validator
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PROMPTS = HERE / "prompts"
SCHEMAS = HERE / "schemas"
SHARED_INPUT = PROJECT_ROOT / "outputs/ironkv_claude_to_deepseek_trace2skill_train77_combined_v2/evolution/input/combined_records.json"
SHARED_AUDIT = SHARED_INPUT.with_name("input_audit.json")
HISTORICAL_SCHEMAS = SCHEMAS
NEUTRAL_SEED = PROJECT_ROOT / "verus_agent/skill_evolution/neutral_seed/verus-proof-repair"
DEFAULT_ENV = PROJECT_ROOT / ".env.deepseek"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/ironkv_deepseek_v4pro_semantic_organization_train77_v2"
DEFAULT_BATCH_CHARS = 42000

DISCOVERY_SCHEMA = SCHEMAS / "discovery_v2.schema.json"
TAXONOMY_SCHEMA = SCHEMAS / "taxonomy_v2.schema.json"
CLUSTER_SCHEMA = HISTORICAL_SCHEMAS / "cluster_consolidation.schema.json"
GLOBAL_SCHEMA = HISTORICAL_SCHEMAS / "global_skill_library.schema.json"
LAYOUT_SCHEMA = SCHEMAS / "layout_v2.schema.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if key != "api_key"}


def load_config(args: argparse.Namespace) -> dict[str, Any]:
    file_values = {key: str(value or "") for key, value in dotenv_values(args.env_file).items()}
    value = lambda key, default="": os.environ.get(key, file_values.get(key, default))
    api_key = value("DEEPSEEK_API_KEY").strip()
    base_url = value("DEEPSEEK_BASE_URL").strip()
    model = value("DEEPSEEK_MODEL", "deepseek-v4-pro").strip()
    if args.execute and not api_key:
        raise ValueError("DEEPSEEK_API_KEY is empty or missing")
    if args.execute and not base_url:
        raise ValueError("DEEPSEEK_BASE_URL is empty or missing")
    if model != "deepseek-v4-pro":
        raise ValueError(f"this experiment requires deepseek-v4-pro, found {model!r}")
    if not 0 <= args.temperature <= 2:
        raise ValueError("temperature must be between 0 and 2")
    if args.max_output_tokens < 1024:
        raise ValueError("max-output-tokens is too small")
    return {
        "api_key": api_key,
        "api_key_env_var": "DEEPSEEK_API_KEY",
        "api_key_configured": bool(api_key),
        "base_url": base_url,
        "model": model,
        "temperature": args.temperature,
        "max_output_tokens": args.max_output_tokens,
        "thinking_enabled": True,
        "reasoning_effort": "high",
        "sdk_max_retries": 0,
        "automatic_retries": False,
    }


def make_memories() -> list[dict[str, Any]]:
    audit = json.loads(SHARED_AUDIT.read_text(encoding="utf-8"))
    expected_audit = {"combined_record_count": 77, "error_record_count": 24, "heldout_inputs_used": False, "success_record_count": 53}
    if audit != expected_audit:
        raise ValueError(f"shared input audit changed: {audit!r}")
    records = json.loads(SHARED_INPUT.read_text(encoding="utf-8"))
    if len(records) != 77:
        raise ValueError(f"expected 77 records, found {len(records)}")
    memories: list[dict[str, Any]] = []
    for record in records:
        for item in record["items"]:
            local_id = f"{record['instance_id']}::{item['type']}::{int(item['number']):03d}"
            memories.append({
                "local_card_id": local_id,
                "source_trajectory_key": record["instance_id"],
                "source_file": record["source_file"],
                "record_source": record["record_source"],
                "evidence_type": item["type"],
                "memory": item,
            })
    ids = [memory["local_card_id"] for memory in memories]
    if len(memories) != 284 or len(ids) != len(set(ids)):
        raise ValueError("shared memories are not the expected 284 unique items")
    # Deterministic dispersion prevents the original file ordering from becoming
    # a hidden taxonomy. It does not inspect or route by memory content.
    memories.sort(key=lambda memory: hashlib.sha256(memory["local_card_id"].encode()).hexdigest())
    return memories


def make_batches(memories: list[dict[str, Any]], max_chars: int) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 2
    for memory in memories:
        size = len(json.dumps(memory, ensure_ascii=False)) + 2
        if current and current_chars + size > max_chars:
            batches.append(current)
            current = []
            current_chars = 2
        current.append(memory)
        current_chars += size
    if current:
        batches.append(current)
    flattened = [item["local_card_id"] for batch in batches for item in batch]
    expected = [item["local_card_id"] for item in memories]
    if Counter(flattened) != Counter(expected):
        raise ValueError("batch construction lost or duplicated memories")
    return batches


def load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def render(template_name: str, **values: str) -> str:
    text = (PROMPTS / template_name).read_text(encoding="utf-8")
    for key, value in values.items():
        marker = "{{" + key + "}}"
        if text.count(marker) != 1:
            raise ValueError(f"template marker {marker} must occur exactly once in {template_name}")
        text = text.replace(marker, value)
    leftovers = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    if leftovers:
        raise ValueError(f"unrendered markers in {template_name}: {leftovers}")
    return text


def parse_json(text: str) -> dict[str, Any]:
    candidate = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("response JSON is not an object")
    return parsed


def validate_schema(payload: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: list(error.absolute_path))
    return [{"path": "/" + "/".join(map(str, error.absolute_path)), "message": error.message} for error in errors]


def exact_once(actual: Iterable[str], expected: Iterable[str]) -> dict[str, Any]:
    actual_list = list(actual)
    expected_list = list(expected)
    counts = Counter(actual_list)
    missing = sorted(set(expected_list) - set(actual_list))
    unexpected = sorted(set(actual_list) - set(expected_list))
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    return {
        "valid": not missing and not unexpected and not duplicates and len(actual_list) == len(expected_list),
        "expected_count": len(expected_list), "actual_count": len(actual_list),
        "missing": missing, "unexpected": unexpected, "duplicates": duplicates,
    }


def response_usage(response: Any, latency: float) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    details = getattr(usage, "completion_tokens_details", None)
    return {
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "reasoning_tokens": getattr(details, "reasoning_tokens", None),
        "latency_seconds": round(latency, 6),
    }


def call_once(config: dict[str, Any], system: str, user: str) -> Any:
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"], timeout=900, max_retries=0)
    return client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=config["temperature"], max_tokens=config["max_output_tokens"],
        reasoning_effort="high", extra_body={"thinking": {"type": "enabled"}},
    )


def execute_stage(
    *, out: Path, stage: str, item_id: str, system: str, user: str,
    schema: dict[str, Any], config: dict[str, Any], execute: bool, resume: bool,
    semantic_validator: Any,
) -> dict[str, Any] | None:
    parsed_path = out / "parsed.json"
    if resume and parsed_path.is_file():
        validation = json.loads((out / "validation.json").read_text(encoding="utf-8"))
        if not validation.get("valid"):
            raise ValueError(f"cannot resume invalid stage: {out}")
        return json.loads(parsed_path.read_text(encoding="utf-8"))
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"partial or existing stage; refusing second request: {out}")
    out.mkdir(parents=True)
    (out / "system_prompt.txt").write_text(system, encoding="utf-8")
    (out / "user_prompt.txt").write_text(user, encoding="utf-8")
    write_json(out / "request_manifest.json", {"stage": stage, "item_id": item_id, "system_chars": len(system), "user_chars": len(user), **public_config(config)})
    if not execute:
        return None
    started = time.monotonic()
    try:
        response = call_once(config, system, user)
        write_json(out / "raw_response.json", response.model_dump(mode="json"))
        text = response.choices[0].message.content or ""
        (out / "response_text.txt").write_text(text, encoding="utf-8")
        payload = parse_json(text)
        schema_errors = validate_schema(payload, schema)
        semantic = semantic_validator(payload) if not schema_errors else {"valid": False, "skipped": True}
        valid = not schema_errors and semantic.get("valid") is True
        write_json(out / "validation.json", {"valid": valid, "schema_errors": schema_errors, "semantic_audit": semantic})
        write_json(out / "usage.json", response_usage(response, time.monotonic() - started))
        if not valid:
            raise ValueError(f"invalid stage response; see {out / 'validation.json'}")
        write_json(parsed_path, payload)
        return payload
    except Exception as exc:
        safe = str(exc).replace(config["api_key"], "[REDACTED]") if config["api_key"] else str(exc)
        write_json(out / "error.json", {"type": type(exc).__name__, "message": safe, "latency_seconds": round(time.monotonic() - started, 6)})
        raise


def discovery_ids(payload: dict[str, Any]) -> list[str]:
    return [memory_id for group in payload["local_groups"] for memory_id in group["member_ids"]]


def taxonomy_group_ids(payload: dict[str, Any]) -> list[str]:
    return [group_id for family in payload["reference_families"] for group_id in family["source_group_ids"]]


def disposition_ids(payload: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for skill in payload.get("consolidated_skills", payload.get("global_skills", [])):
        ids.extend(skill["source_card_ids"])
    ids.extend(exclusion["local_card_id"] for exclusion in payload["excluded_cards"])
    return ids


def transfer_audit(payload: dict[str, Any]) -> dict[str, Any]:
    skills = payload.get("consolidated_skills", payload.get("global_skills", []))
    invalid = [skill.get("candidate_id", skill.get("skill_id")) for skill in skills if skill.get("transfer_status") != "untested"]
    return {"valid": not invalid, "non_untested_skills": invalid}


def combine_audits(*audits: dict[str, Any]) -> dict[str, Any]:
    return {"valid": all(audit.get("valid") for audit in audits), "checks": list(audits)}


def render_skill(skill_dir: Path, library: dict[str, Any], layout: dict[str, Any]) -> None:
    shutil.copytree(NEUTRAL_SEED, skill_dir)
    root = layout["root"]
    lines = [
        "---", "name: verus-proof-repair", f"description: {root['description']}", "---", "",
        f"# {root['title']}", "",
        "Use the broadly applicable procedures below before opening a reference.", "",
        "## Core procedures", "",
    ]
    for procedure in root["core_procedures"]:
        lines.extend([f"### {procedure['title']}", "", f"**When:** {procedure['when']}", ""])
        lines.extend(f"{index}. {step}" for index, step in enumerate(procedure["steps"], 1))
        lines.extend(["", f"**Check:** {procedure['check']}", ""])
    lines.extend(["## Progressive reference consultation", ""])
    lines.extend(f"{index}. {step}" for index, step in enumerate(root["consultation_workflow"], 1))
    lines.extend(["", "## Safety and stopping rules", ""])
    lines.extend(f"- {rule}" for rule in root["safety_and_stopping_rules"])
    lines.extend(["", "## Reference map", ""])
    skills = {skill["skill_id"]: skill for skill in library["global_skills"]}
    for reference in layout["references"]:
        lines.extend([
            f"### [{reference['title']}](references/{reference['filename']})", "",
            f"**Consult when:** {reference['consult_when']}", "",
            f"**Do not consult when:** {reference['do_not_consult_when']}", "",
        ])
        for skill_id in reference["skill_ids"]:
            skill = skills[skill_id]
            lines.append(f"- `{skill_id}` — {skill['title']}: {skill['applicability_signature']}")
        lines.append("")
    (skill_dir / "SKILL.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    for reference in layout["references"]:
        ref_lines = [f"# {reference['title']}", "", f"**Consult when:** {reference['consult_when']}", "", f"**Do not consult when:** {reference['do_not_consult_when']}", ""]
        for skill_id in reference["skill_ids"]:
            skill = skills[skill_id]
            ref_lines.extend([
                f"## {skill_id} — {skill['title']}", "",
                f"**Status:** `{skill['status']}` · `{skill['support_level']}` · `{skill['transfer_status']}`", "",
                f"**When:** {skill['applicability_signature']}", "",
                f"**Obstacle:** {skill['proof_obstacle']}", "",
                f"**Mechanism:** {skill['mechanism']}", "", "**Procedure:**",
            ])
            ref_lines.extend(f"{index}. {step}" for index, step in enumerate(skill["procedure"], 1))
            ref_lines.extend(["", f"**Why:** {skill['why']}", "", f"**Check:** {skill['check']}", "", "**Avoid or stop:**"])
            ref_lines.extend([f"- {item}" for item in skill["contraindications"]] or ["- No additional contraindication recorded."])
            ref_lines.append("")
        (skill_dir / "references" / reference["filename"]).write_text("\n".join(ref_lines).rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--discovery-batch-chars", type=int, default=DEFAULT_BATCH_CHARS)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args(argv)
    output = args.output_root.resolve()
    if output.exists() and not args.resume:
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True, exist_ok=True)
    config = load_config(args)
    memories = make_memories()
    batches = make_batches(memories, args.discovery_batch_chars)
    write_json(output / "input/normalized_memories.json", {"memory_count": len(memories), "memories": memories})
    write_json(output / "input/discovery_batches.json", {
        "batching_uses_memory_content": False,
        "deterministic_order": "sha256(local_card_id)",
        "max_serialized_memory_chars_per_batch": args.discovery_batch_chars,
        "batch_count": len(batches),
        "batches": [{"batch_id": f"batch_{index:03d}", "memory_count": len(batch), "memory_ids": [item["local_card_id"] for item in batch], "serialized_chars": len(json.dumps(batch, ensure_ascii=False))} for index, batch in enumerate(batches, 1)],
    })
    schema_paths = [DISCOVERY_SCHEMA, TAXONOMY_SCHEMA, CLUSTER_SCHEMA, GLOBAL_SCHEMA, LAYOUT_SCHEMA]
    configuration_dir = output / "configuration"
    configuration_dir.mkdir(exist_ok=True)
    snapshot_sources = schema_paths + sorted(PROMPTS.glob("*_v2_*.txt"))
    for source in snapshot_sources:
        target = configuration_dir / source.name
        if not target.exists():
            shutil.copy2(source, target)
    manifest_path = output / "run_manifest.json"
    if not manifest_path.exists():
        write_json(manifest_path, {
            "experiment": "ironkv_deepseek_v4pro_semantic_organization_train77_v2",
            "created_at": utc_now(), "status": "dry_run" if args.dry_run else "running",
            "shared_input_with_native_trace2skill": True,
            "shared_input": str(SHARED_INPUT.resolve()), "shared_input_sha256": sha256_file(SHARED_INPUT),
            "train_record_count": 77, "memory_count": 284, "discovery_batch_count": len(batches),
            "taxonomy": "open data-driven induction by DeepSeek; no host-defined family names or keyword routing",
            "heldout_inputs_used": False, "configuration": public_config(config),
        })
    discovery_schema = load_schema(DISCOVERY_SCHEMA)
    discovery_system = (PROMPTS / "discover_v2_system.txt").read_text(encoding="utf-8")
    discovered: list[dict[str, Any]] = []
    for index, batch in enumerate(batches, 1):
        batch_id = f"batch_{index:03d}"
        expected_ids = [item["local_card_id"] for item in batch]
        user = render("discover_v2_user.txt", BATCH_ID=batch_id, INPUT_MEMORY_COUNT=str(len(batch)), CARDS_JSON=json.dumps(batch, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(discovery_schema, ensure_ascii=False, indent=2))
        print(f"[DISCOVERY {index}/{len(batches)}] {batch_id}: {len(batch)} complete memories", flush=True)
        payload = execute_stage(out=output / "discovery" / batch_id, stage="open_taxonomy_discovery", item_id=batch_id, system=discovery_system, user=user, schema=discovery_schema, config=config, execute=args.execute, resume=args.resume, semantic_validator=lambda value, ids=expected_ids, bid=batch_id: combine_audits(exact_once(discovery_ids(value), ids), {"valid": value["batch_id"] == bid, "expected_batch_id": bid, "actual_batch_id": value["batch_id"]}))
        if payload:
            discovered.extend(payload["local_groups"])
    if args.dry_run:
        write_json(output / "dry_run_summary.json", {"network_requests": 0, "discovery_requests_planned": len(batches), "later_request_count_is_data_dependent": True, "all_284_memories_included_complete": True})
        return 0
    group_ids = [group["local_group_id"] for group in discovered]
    if len(group_ids) != len(set(group_ids)):
        raise ValueError("discovery produced duplicate local_group_id values across batches")
    taxonomy_schema = load_schema(TAXONOMY_SCHEMA)
    taxonomy_system = (PROMPTS / "taxonomy_v2_system.txt").read_text(encoding="utf-8")
    taxonomy_user = render("taxonomy_v2_user.txt", LOCAL_GROUP_COUNT=str(len(discovered)), LOCAL_GROUPS_JSON=json.dumps(discovered, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(taxonomy_schema, ensure_ascii=False, indent=2))
    print(f"[TAXONOMY] synthesizing {len(discovered)} open local groups", flush=True)
    taxonomy = execute_stage(out=output / "taxonomy", stage="global_open_taxonomy", item_id="global_taxonomy", system=taxonomy_system, user=taxonomy_user, schema=taxonomy_schema, config=config, execute=True, resume=args.resume, semantic_validator=lambda value: exact_once(taxonomy_group_ids(value), group_ids))
    assert taxonomy is not None
    write_json(output / "taxonomy.json", taxonomy)
    groups_by_id = {group["local_group_id"]: group for group in discovered}
    memories_by_id = {memory["local_card_id"]: memory for memory in memories}
    family_inputs: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    all_expanded_ids: list[str] = []
    for family in taxonomy["reference_families"]:
        ids = [member_id for group_id in family["source_group_ids"] for member_id in groups_by_id[group_id]["member_ids"]]
        all_expanded_ids.extend(ids)
        family_inputs.append((family, [memories_by_id[memory_id] for memory_id in ids]))
    expansion_audit = exact_once(all_expanded_ids, memories_by_id)
    write_json(output / "taxonomy_expansion_audit.json", expansion_audit)
    if not expansion_audit["valid"]:
        raise ValueError("taxonomy expansion did not cover all 284 memories exactly once")
    cluster_schema = load_schema(CLUSTER_SCHEMA)
    cluster_system = (PROMPTS / "cluster_v2_system.txt").read_text(encoding="utf-8")
    family_results = []
    for index, (family, family_memories) in enumerate(family_inputs, 1):
        family_id = family["family_id"]
        ids = [memory["local_card_id"] for memory in family_memories]
        user = render("cluster_v2_user.txt", CLUSTER_ID=family_id, FAMILY_TITLE=family["title"], FAMILY_SCOPE=family["scope"], INCLUSION_CRITERIA=json.dumps(family["inclusion_criteria"], ensure_ascii=False), EXCLUSION_CRITERIA=json.dumps(family["exclusion_criteria"], ensure_ascii=False), INPUT_CARD_COUNT=str(len(ids)), CARDS_JSON=json.dumps(family_memories, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(cluster_schema, ensure_ascii=False, indent=2))
        print(f"[FAMILY {index}/{len(family_inputs)}] {family_id} {family['title']}: {len(ids)} memories", flush=True)
        payload = execute_stage(out=output / "families" / family_id, stage="family_consolidation", item_id=family_id, system=cluster_system, user=user, schema=cluster_schema, config=config, execute=True, resume=args.resume, semantic_validator=lambda value, expected=ids, fid=family_id: combine_audits(exact_once(disposition_ids(value), expected), transfer_audit(value), {"valid": value["cluster_id"] == fid, "expected_cluster_id": fid, "actual_cluster_id": value["cluster_id"]}))
        assert payload is not None
        family_results.append(payload)
    global_schema = load_schema(GLOBAL_SCHEMA)
    reconcile_system = (PROMPTS / "reconcile_v2_system.txt").read_text(encoding="utf-8")
    reconcile_user = render("reconcile_v2_user.txt", TOTAL_LOCAL_CARD_COUNT=str(len(memories)), CLUSTER_RESULTS_JSON=json.dumps(family_results, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(global_schema, ensure_ascii=False, indent=2))
    all_memory_ids = list(memories_by_id)
    print(f"[RECONCILIATION] {len(family_results)} families and {len(memories)} memories", flush=True)
    library = execute_stage(out=output / "reconciliation", stage="global_reconciliation", item_id="global_library", system=reconcile_system, user=reconcile_user, schema=global_schema, config=config, execute=True, resume=args.resume, semantic_validator=lambda value: combine_audits(exact_once(disposition_ids(value), all_memory_ids), transfer_audit(value)))
    assert library is not None
    write_json(output / "global_skills.json", library)
    layout_schema = load_schema(LAYOUT_SCHEMA)
    layout_system = (PROMPTS / "layout_v2_system.txt").read_text(encoding="utf-8")
    layout_user = render("layout_v2_user.txt", GLOBAL_SKILL_COUNT=str(len(library["global_skills"])), LIBRARY_JSON=json.dumps(library, ensure_ascii=False, indent=2), SCHEMA_JSON=json.dumps(layout_schema, ensure_ascii=False, indent=2))
    skill_ids = [skill["skill_id"] for skill in library["global_skills"]]
    print(f"[M/R LAYOUT] organizing {len(skill_ids)} final skills", flush=True)
    layout = execute_stage(out=output / "layout", stage="model_driven_mr_layout", item_id="mr_layout", system=layout_system, user=layout_user, schema=layout_schema, config=config, execute=True, resume=args.resume, semantic_validator=lambda value: combine_audits(exact_once((skill_id for reference in value["references"] for skill_id in reference["skill_ids"]), skill_ids), {"valid": len({reference["filename"] for reference in value["references"]}) == len(value["references"]), "filename_count": len(value["references"])}))
    assert layout is not None
    write_json(output / "mr_layout.json", layout)
    skill_dir = output / "skill/verus-proof-repair"
    if skill_dir.exists():
        raise FileExistsError(f"skill output already exists: {skill_dir}")
    render_skill(skill_dir, library, layout)
    final_audit = {
        "valid": True, "train_record_count": 77, "memory_count": 284,
        "discovery_batch_count": len(batches), "local_group_count": len(discovered),
        "model_induced_family_count": len(family_inputs), "global_skill_count": len(skill_ids),
        "model_designed_reference_count": len(layout["references"]),
        "host_defined_family_names": False, "host_keyword_routing": False,
        "heldout_inputs_used": False, "skill_dir": str(skill_dir),
    }
    write_json(output / "final_audit.json", final_audit)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({"status": "completed", "completed_at": utc_now(), "local_group_count": len(discovered), "model_induced_family_count": len(family_inputs), "global_skill_count": len(skill_ids), "model_designed_reference_count": len(layout["references"]), "actual_request_count": len(batches) + 1 + len(family_inputs) + 2, "skill_dir": str(skill_dir)})
    write_json(manifest_path, manifest)
    print(json.dumps(final_audit, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
