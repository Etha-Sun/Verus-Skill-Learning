#!/usr/bin/env python3
"""Apply and audit the single authorized taxonomy ID transcription repair."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (
    resume_semantic_organization_v3 as v3,
)
from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (
    run_semantic_organization_v2 as v2,
)


STAGE = (
    v2.DEFAULT_OUTPUT
    / "taxonomy_hierarchy/level_04/batch_003"
)
WRONG = "taxonomy_l04_b004_family_008"
CORRECT = "taxonomy_l03_b004_family_008"


def main() -> int:
    if (STAGE / "parsed.json").exists():
        raise FileExistsError("parsed.json already exists; refusing to repair twice")
    payload = json.loads((STAGE / "response_text.txt").read_text(encoding="utf-8"))
    occurrences = 0
    for family in payload["provisional_families"]:
        repaired = []
        for node_id in family["source_node_ids"]:
            if node_id == WRONG:
                node_id = CORRECT
                occurrences += 1
            repaired.append(node_id)
        family["source_node_ids"] = repaired
    if occurrences != 1:
        raise ValueError(f"expected one transcription error, found {occurrences}")

    memories = v2.make_memories()
    groups = v3.load_discovery(v2.DEFAULT_OUTPUT, memories)
    nodes = [{
        "node_id": group["local_group_id"],
        "title": group["label"],
        "observable_trigger": group["observable_trigger"],
        "missing_bridge": group["missing_bridge"],
        "mechanism_summary": group["mechanism_summary"],
        "boundary": group["boundary"],
    } for group in groups]
    for level in range(1, 4):
        next_nodes = []
        for batch_index, _batch in enumerate(v3.node_batches(nodes, 28), 1):
            path = v2.DEFAULT_OUTPUT / f"taxonomy_hierarchy/level_{level:02d}/batch_{batch_index:03d}/parsed.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            next_nodes.extend({
                "node_id": family["node_id"],
                "title": family["title"],
                "observable_trigger": family["observable_trigger"],
                "missing_bridge": family["missing_bridge"],
                "mechanism_summary": family["mechanism_summary"],
                "boundary": family["boundary"],
            } for family in result["provisional_families"])
        nodes = next_nodes
    batch = v3.node_batches(nodes, 28)[2]
    expected_ids = [node["node_id"] for node in batch]
    schema = v2.load_schema(v3.NODE_SCHEMA)
    schema_errors = sorted(
        Draft202012Validator(schema).iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    audit = v2.combine_audits(
        v2.exact_once(v3.source_node_ids(payload), expected_ids),
        v3.node_id_audit(payload, "taxonomy_l04_b003_family_"),
        {
            "valid": payload["level"] == 4 and payload["batch_id"] == "level_04_batch_003",
            "expected_level": 4,
            "actual_level": payload["level"],
            "expected_batch": "level_04_batch_003",
            "actual_batch": payload["batch_id"],
        },
    )
    valid = not schema_errors and audit["valid"]
    if not valid:
        raise ValueError("corrected response did not pass schema and semantic audits")
    v2.write_json(STAGE / "parsed.json", payload)
    v2.write_json(STAGE / "validation.json", {
        "valid": True,
        "schema_errors": [],
        "semantic_audit": audit,
        "deterministic_repair": {
            "authorized": True,
            "scope": "one source_node_id transcription only; no semantic field changed",
            "from": WRONG,
            "to": CORRECT,
            "occurrences": occurrences,
            "raw_response_unchanged": True,
            "response_text_unchanged": True,
            "repaired_at": datetime.now(timezone.utc).isoformat(),
        },
    })
    v2.write_json(STAGE / "repair_audit.json", {
        "status": "PASS",
        "from": WRONG,
        "to": CORRECT,
        "occurrences": occurrences,
        "schema_valid": True,
        "exactly_once_valid": True,
        "raw_response_unchanged": True,
        "response_text_unchanged": True,
    })
    print(json.dumps(json.loads((STAGE / "repair_audit.json").read_text()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
