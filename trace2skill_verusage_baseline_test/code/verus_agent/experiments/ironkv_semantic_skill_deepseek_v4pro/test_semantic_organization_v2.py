from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from verus_agent.experiments.ironkv_semantic_skill_deepseek_v4pro import (
    run_semantic_organization_v2 as subject,
)


class SemanticOrganizationV2Tests(unittest.TestCase):
    @unittest.skip("requires excluded full 284-memory input artifact")
    def test_shared_input_has_284_unique_complete_memories(self) -> None:
        memories = subject.make_memories()
        self.assertEqual(len(memories), 284)
        self.assertEqual(len({item["local_card_id"] for item in memories}), 284)
        self.assertTrue(all(item["memory"]["content"] for item in memories))

    @unittest.skip("requires excluded full 284-memory input artifact")
    def test_batches_are_content_agnostic_and_exact(self) -> None:
        memories = subject.make_memories()
        batches = subject.make_batches(memories, 42000)
        actual = [item["local_card_id"] for batch in batches for item in batch]
        expected = [item["local_card_id"] for item in memories]
        self.assertEqual(actual, expected)
        self.assertGreater(len(batches), 1)

    def test_runner_contains_no_fixed_taxonomy_or_keyword_router(self) -> None:
        source = Path(subject.__file__).read_text(encoding="utf-8")
        self.assertNotIn("CLUSTER_RULES", source)
        self.assertNotIn("FAMILIES =", source)
        self.assertNotIn("family_for(", source)

    def test_new_schemas_are_valid_draft_202012(self) -> None:
        for path in (subject.DISCOVERY_SCHEMA, subject.TAXONOMY_SCHEMA, subject.LAYOUT_SCHEMA):
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    @unittest.skip("requires excluded full 284-memory input artifact")
    def test_dry_run_cannot_call_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dry_run"
            with patch.object(subject, "call_once", side_effect=AssertionError("network forbidden")):
                status = subject.main(["--dry-run", "--output-root", str(output)])
            self.assertEqual(status, 0)
            summary = json.loads((output / "dry_run_summary.json").read_text())
            self.assertEqual(summary["network_requests"], 0)
            self.assertTrue(summary["all_284_memories_included_complete"])


if __name__ == "__main__":
    unittest.main()
