#!/usr/bin/env python3
"""Run the frozen strict held-out-15 pair with the semantic-v4 M/R skill.

This is deliberately a thin specialization of the existing strict native-
Trace2Skill runner. The frozen tasks, agent harness, condition ordering,
DeepSeek settings, stopping policy, Verus/Lynette contract checks, and output
accounting remain unchanged. Only the immutable skill snapshot is replaced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from verus_agent.experiments.ironkv_claude_to_deepseek_77_77 import (
    run_heldout20_paired_when_ready as base,
)
from verus_agent.experiments.ironkv_claude_to_deepseek_77_77 import (
    run_strict_heldout15_paired as strict,
)


SEMANTIC_ROOT = (
    base.PROJECT_ROOT
    / "outputs/ironkv_deepseek_v4pro_semantic_organization_train77_v2"
)
SEMANTIC_SKILL = SEMANTIC_ROOT / "skill_v4/verus-proof-repair"
SEMANTIC_AUDIT = SEMANTIC_ROOT / "final_audit_v4.json"
LIBRARY_VALIDATION = SEMANTIC_ROOT / "reconciliation_v4/library_validation.json"
LAYOUT_VALIDATION = SEMANTIC_ROOT / "layout_v4/validation.json"
DEFAULT_OUTPUT_ROOT = (
    base.PROJECT_ROOT
    / "outputs/ironkv_deepseek_strict_heldout15_paired_semantic_v4_v1"
)
ORIGINAL_STRICT_PREPARE = strict.prepare_strict_experiment


def validate_semantic_skill(_poll_seconds: int) -> None:
    checks = {
        "final_audit": SEMANTIC_AUDIT,
        "library_validation": LIBRARY_VALIDATION,
        "layout_validation": LAYOUT_VALIDATION,
        "root_skill": SEMANTIC_SKILL / "SKILL.md",
    }
    missing = [name for name, path in checks.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"semantic-v4 skill is incomplete: {missing}")
    for path in (SEMANTIC_AUDIT, LIBRARY_VALIDATION, LAYOUT_VALIDATION):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("valid") is not True:
            raise ValueError(f"semantic-v4 audit is not valid: {path}")
    audit = json.loads(SEMANTIC_AUDIT.read_text(encoding="utf-8"))
    if audit.get("memory_count") != 284 or audit.get("global_skill_count") != 88:
        raise ValueError("semantic-v4 final counts changed")
    references = sorted((SEMANTIC_SKILL / "references").glob("*.md"))
    if len(references) != audit.get("model_designed_reference_count"):
        raise ValueError("semantic-v4 reference count does not match final audit")


def prepare_semantic_experiment(
    output_root: Path,
    selected: list[dict[str, Any]],
    quotas: dict[str, int],
    config: dict[str, Any],
    args: Any,
) -> Path:
    snapshot = ORIGINAL_STRICT_PREPARE(output_root, selected, quotas, config, args)
    manifest_path = output_root / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "experiment": "ironkv_deepseek_strict_heldout15_paired_semantic_v4_v1",
            "comparison_target": "native Trace2Skill compressed skill on the identical frozen strict held-out-15",
            "comparison_experiment": str(
                (
                    base.PROJECT_ROOT
                    / "outputs/ironkv_deepseek_strict_heldout15_paired_raw_combined_v2_v1"
                ).resolve()
            ),
            "skill_variant": "semantic_v4_unmodified",
            "skill_source": str(SEMANTIC_SKILL.resolve()),
            "skill_source_final_audit": str(SEMANTIC_AUDIT.resolve()),
            "skill_source_final_audit_sha256": base.sha256_file(SEMANTIC_AUDIT),
            "semantic_memory_count": 284,
            "semantic_global_skill_count": 88,
            "semantic_reference_count": 14,
            "only_intended_experimental_variable": "skill snapshot; baseline is rerun as a stochastic control",
        }
    )
    base.write_json(manifest_path, manifest)
    return snapshot


def main() -> int:
    validate_semantic_skill(0)
    base.EVOLVED_SKILL = SEMANTIC_SKILL
    base.EVOLUTION_SUMMARY = SEMANTIC_AUDIT
    base.wait_for_skill = validate_semantic_skill
    strict.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
    strict.prepare_strict_experiment = prepare_semantic_experiment
    return strict.main()


if __name__ == "__main__":
    raise SystemExit(main())
