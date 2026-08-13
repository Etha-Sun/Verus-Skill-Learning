#!/usr/bin/env python3
"""Repair and audit group 064's source-card ID field only.

The model returned the two input candidate IDs in ``source_card_ids`` rather
than the source memory IDs carried by those candidates. The raw response and
response text remain immutable; the expected provenance is derived exactly
from the partition members and validated family artifacts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (
    resume_semantic_organization_v4 as v4,
)
from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (
    run_semantic_organization_v2 as base,
)


GROUP_ID = "global_group_064"
STAGE = base.DEFAULT_OUTPUT / "reconciliation_v4/merged_groups" / GROUP_ID


def main() -> int:
    if (STAGE / "parsed.json").exists():
        raise FileExistsError("parsed.json already exists; refusing to repair twice")
    payload = base.parse_json((STAGE / "response_text.txt").read_text(encoding="utf-8"))
    partition = json.loads(
        (base.DEFAULT_OUTPUT / "reconciliation_v4/partition/parsed.json").read_text(encoding="utf-8")
    )
    group = next(group for group in partition["groups"] if group["group_id"] == GROUP_ID)
    family_results = v4.load_family_results(
        base.DEFAULT_OUTPUT,
        [memory["local_card_id"] for memory in base.make_memories()],
    )
    _compact, full_by_key = v4.indexed_candidates(family_results)
    members = [full_by_key[key] for key in group["member_candidate_keys"]]
    expected_sources = [source for member in members for source in member["source_card_ids"]]
    expected_trajectories = {
        trajectory for member in members for trajectory in member["source_trajectories"]
    }
    actual_before = list(payload["merged_skill"]["source_card_ids"])
    expected_wrong = [key.split("::", 1)[1] for key in group["member_candidate_keys"]]
    if actual_before != expected_wrong:
        raise ValueError(
            "response does not contain the exact candidate-ID-for-source-ID transcription pattern"
        )
    payload["merged_skill"]["source_card_ids"] = expected_sources

    schema_errors = base.validate_schema(payload, base.load_schema(v4.MERGE_SCHEMA))
    audit = base.combine_audits(
        {
            "valid": payload["merged_skill"]["skill_id"] == "verus_global_064",
            "expected_skill_id": "verus_global_064",
            "actual_skill_id": payload["merged_skill"]["skill_id"],
        },
        base.exact_once(payload["merged_skill"]["source_card_ids"], expected_sources),
        {
            "valid": set(payload["merged_skill"]["source_trajectories"])
            == expected_trajectories,
            "expected_trajectories": sorted(expected_trajectories),
            "actual_trajectories": sorted(payload["merged_skill"]["source_trajectories"]),
        },
        base.transfer_audit(
            {"global_skills": [payload["merged_skill"]], "excluded_cards": []}
        ),
    )
    if schema_errors or not audit["valid"]:
        raise ValueError("provenance-only repair did not pass schema and semantic audits")
    repair = {
        "authorized": True,
        "scope": "source_card_ids provenance transcription only; no semantic field changed",
        "actual_before": actual_before,
        "expected_and_actual_after": expected_sources,
        "raw_response_unchanged": True,
        "response_text_unchanged": True,
        "repaired_at": datetime.now(timezone.utc).isoformat(),
    }
    base.write_json(STAGE / "parsed.json", payload)
    base.write_json(
        STAGE / "validation.json",
        {
            "valid": True,
            "schema_errors": [],
            "semantic_audit": audit,
            "deterministic_repair": repair,
        },
    )
    base.write_json(
        STAGE / "repair_audit.json",
        {
            "status": "PASS",
            "schema_valid": True,
            "exactly_once_valid": True,
            **repair,
        },
    )
    print(json.dumps(json.loads((STAGE / "repair_audit.json").read_text()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
