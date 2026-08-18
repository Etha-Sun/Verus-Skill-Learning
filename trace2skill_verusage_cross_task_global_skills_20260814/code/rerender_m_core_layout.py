#!/usr/bin/env python3
"""Rerun only semantic-v4 layout from a frozen validated global library."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_m_core as builder

base = builder.base
v4 = builder.v4


def aggregate_usage(root: Path) -> dict[str, Any]:
    rows = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(root.rglob("usage.json"))
    ]
    fields = ("input_tokens", "output_tokens", "total_tokens", "reasoning_tokens")
    result: dict[str, Any] = {"request_count": len(rows)}
    for field in fields:
        values = [row.get(field) for row in rows]
        result[field] = sum(value for value in values if isinstance(value, int))
        result[f"{field}_complete"] = all(isinstance(value, int) for value in values)
    result["latency_seconds"] = round(
        sum(float(row.get("latency_seconds", 0.0)) for row in rows), 6
    )
    return result


def retry_provenance(source: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(source.rglob("retry_audit.json")):
        records.append(
            {
                "relative_path": path.relative_to(source).as_posix(),
                "sha256": builder.sha256_file(path),
                "audit": json.loads(path.read_text(encoding="utf-8")),
            }
        )
    return records


def validate_source(source: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = source / "run_manifest.json"
    library_path = source / "global_skills_v4.json"
    validation_path = source / "reconciliation_v4" / "library_validation.json"
    for path in (manifest_path, library_path, validation_path):
        if not path.is_file():
            raise FileNotFoundError(f"missing frozen source artifact: {path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or validation.get("valid") is not True:
        raise ValueError("source M-core run is not complete and globally validated")
    library = json.loads(library_path.read_text(encoding="utf-8"))
    schema_errors = base.validate_schema(
        library, builder.adapted_schema("global_skill_library.schema.json")
    )
    skill_ids = [skill["skill_id"] for skill in library["global_skills"]]
    if schema_errors or len(skill_ids) != len(set(skill_ids)) or not skill_ids:
        raise ValueError("source global library failed schema/identity validation")
    if not base.transfer_audit(library)["valid"]:
        raise ValueError("source global library contains non-untested transfer claims")
    return manifest, library


def trusted_boundary_prompt_audit(system: str) -> dict[str, Any]:
    required = (
        "do not categorically ban",
        "empty or axiom-like `ext_equal`",
        "`external_body` proof functions with `unimplemented!()`",
        "explicitly permitted by project policy",
        "grep hit is therefore an audit trigger",
        "do not mandate an unconditional second full verifier run",
    )
    normalized = system.lower()
    missing = [phrase for phrase in required if phrase not in normalized]
    return {"valid": not missing, "required_phrases_missing": missing}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--source-run-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args(argv)

    source = args.source_run_root.resolve()
    output = args.output_root.resolve()
    run_root = args.run_root.resolve()
    builder.assert_below(output, run_root)
    if output.exists():
        raise FileExistsError(f"layout-only output already exists: {output}")
    if source == output:
        raise ValueError("layout-only output must not overwrite its source run")

    source_manifest, library = validate_source(source)
    config = base.load_config(args)
    output.mkdir(parents=True)
    configuration_hashes = builder.snapshot_configuration(output)
    system = builder.load_prompt("layout_v2_system.txt")
    prompt_audit = trusted_boundary_prompt_audit(system)
    if not prompt_audit["valid"]:
        raise ValueError(f"layout safety prompt audit failed: {prompt_audit}")

    source_library = source / "global_skills_v4.json"
    frozen_library = output / "input" / "global_skills_v4.json"
    frozen_library.parent.mkdir(parents=True)
    frozen_library.write_bytes(source_library.read_bytes())
    source_retries = retry_provenance(source)
    manifest_path = output / "run_manifest.json"
    manifest = {
        "schema_version": 1,
        "experiment": "cross_task_semantic_v4_m_core_layout_only_v3_20260815",
        "created_at": base.utc_now(),
        "status": "running",
        "mode": "layout_only_from_frozen_global_library",
        "source_run_root": str(source),
        "source_run_manifest_sha256": builder.sha256_file(source / "run_manifest.json"),
        "source_global_library_sha256": builder.sha256_file(source_library),
        "copied_global_library_sha256": builder.sha256_file(frozen_library),
        "source_shared_memory_set_sha256": source_manifest["shared_memory_set_sha256"],
        "source_combined_records_sha256": source_manifest["combined_records_sha256"],
        "source_construction_usage_including_rejected_attempts": aggregate_usage(source),
        "source_manual_retry_audits": source_retries,
        "heldout_inputs_used": False,
        "configuration": base.public_config(config),
        "prompt_audit": prompt_audit,
        **configuration_hashes,
    }
    base.write_json(manifest_path, manifest)

    schema = builder.adapted_schema("layout_v2.schema.json")
    compact = v4.compact_library(library)
    user = builder.render_prompt(
        "layout_v4_user.txt",
        GLOBAL_SKILL_COUNT=str(len(library["global_skills"])),
        COMPACT_LIBRARY_JSON=json.dumps(compact, ensure_ascii=False, indent=2),
        SCHEMA_JSON=json.dumps(schema, ensure_ascii=False, indent=2),
    )
    skill_ids = [skill["skill_id"] for skill in library["global_skills"]]
    print(f"[M-CORE LAYOUT ONLY] {len(skill_ids)} frozen skills", flush=True)
    layout = base.execute_stage(
        out=output / "layout_v4",
        stage="compact_model_driven_mr_layout_layout_only_v3",
        item_id="mr_layout",
        system=system,
        user=user,
        schema=schema,
        config=config,
        execute=True,
        resume=False,
        semantic_validator=lambda value: base.combine_audits(
            builder.exact_once(
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
    skill_dir = output / "m_core" / "skill" / "verus-proof-repair"
    root_audit = builder.render_root_only(skill_dir, layout)
    final_audit = {
        "valid": True,
        "mode": "layout_only_from_frozen_global_library",
        "global_skill_count": len(skill_ids),
        "model_designed_reference_count": len(layout["references"]),
        **root_audit,
        "heldout_inputs_used": False,
        "skill_dir": str(skill_dir),
    }
    base.write_json(output / "m_core" / "m_core_manifest.json", final_audit)
    completed = json.loads(manifest_path.read_text(encoding="utf-8"))
    completed.update(
        {
            "status": "complete",
            "completed_at": base.utc_now(),
            "layout_usage": aggregate_usage(output / "layout_v4"),
            "rendered_reference_count": 0,
            "m_core_skill_dir": str(skill_dir),
            "m_core_skill_md_sha256": root_audit["skill_md_sha256"],
            "m_core_skill_tree_sha256": root_audit["skill_tree_sha256"],
        }
    )
    base.write_json(manifest_path, completed)
    print(json.dumps(final_audit, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
