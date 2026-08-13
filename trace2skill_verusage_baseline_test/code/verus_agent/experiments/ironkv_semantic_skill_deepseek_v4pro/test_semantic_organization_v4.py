from __future__ import annotations

import json
import unittest

from jsonschema import Draft202012Validator

from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (
    resume_semantic_organization_v4 as subject,
)
from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (
    run_semantic_organization_v2 as base,
)


class SemanticOrganizationV4Tests(unittest.TestCase):
    def test_new_schemas_are_valid(self) -> None:
        for path in (subject.PARTITION_SCHEMA, subject.MERGE_SCHEMA):
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    def test_partition_audit_requires_exactly_once_and_consecutive_ids(self) -> None:
        payload = {
            "groups": [
                {"group_id": "global_group_001", "member_candidate_keys": ["a"]},
                {"group_id": "global_group_002", "member_candidate_keys": ["b", "c"]},
            ]
        }
        self.assertTrue(base.exact_once(subject.partition_keys(payload), ["a", "b", "c"])["valid"])
        self.assertTrue(subject.partition_id_audit(payload)["valid"])
        payload["groups"][1]["member_candidate_keys"].append("a")
        self.assertFalse(base.exact_once(subject.partition_keys(payload), ["a", "b", "c"])["valid"])

    def test_singleton_promotion_preserves_content_and_adds_global_contract(self) -> None:
        source = {
            "candidate_id": "x_candidate_001", "decision": "singleton",
            "title": "T", "transfer_status": "same_task_validated", "procedure": ["step"],
        }
        promoted = subject.promote_singleton(source, "verus_global_001")
        self.assertNotIn("candidate_id", promoted)
        self.assertNotIn("decision", promoted)
        self.assertEqual(promoted["skill_id"], "verus_global_001")
        self.assertEqual(promoted["status"], "candidate_unvalidated")
        self.assertEqual(promoted["transfer_status"], "untested")
        self.assertEqual(promoted["procedure"], ["step"])

    def test_compact_library_omits_provenance_but_keeps_actionable_fields(self) -> None:
        skill = {
            "skill_id": "verus_global_001", "title": "T", "family": "F",
            "support_level": "single_trajectory", "applicability_signature": "when",
            "proof_obstacle": "obstacle", "mechanism": "mechanism", "procedure": ["step"],
            "check": "check", "contraindications": [], "limitations": [],
            "source_card_ids": ["secretly-large-provenance"],
        }
        compact = subject.compact_library({
            "status": "candidate_unvalidated", "library_summary": "summary",
            "global_skills": [skill], "unresolved_conflicts": [],
        })
        self.assertEqual(compact["skills"][0]["procedure"], ["step"])
        self.assertNotIn("source_card_ids", compact["skills"][0])

    def test_v4_has_no_automatic_retry_loop(self) -> None:
        source = open(subject.__file__, encoding="utf-8").read()
        self.assertNotIn("for attempt", source)
        self.assertNotIn("while retry", source)


if __name__ == "__main__":
    unittest.main()
