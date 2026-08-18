from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from threading import Lock
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2]
BASELINE_CODE = ROOT / "trace2skill_verusage_baseline_test" / "code"
sys.path.insert(0, str(BASELINE_CODE))

from skill_evolver.parallel_evolving_agent import (  # noqa: E402
    ParallelSkillEvolver,
    SemanticPatch,
    SemanticPatchItem,
)
from skill_evolver.parallel_success_evolving_agent import (  # noqa: E402
    CombinedParallelSkillEvolver,
    _build_combined_merge_user_message_semantic,
)
from skill_evolver.semantic_reduce_evolving_agent import (  # noqa: E402
    SemanticReduceParallelSkillEvolver,
    collapse_family_result,
    enumerate_patch_items,
    family_patch,
    patch_source_item_ids,
    validate_exact_once_provenance,
    validate_partition,
)


def sample_patch() -> SemanticPatch:
    return SemanticPatch(
        reasoning="retain quantifier trigger evidence",
        items=[
            SemanticPatchItem(
                target_file="SKILL.md",
                edit_intent="Add trigger selection guidance",
                location_hint="quantifier section",
                change_instruction="Use a concrete term that matches the forall trigger.",
            )
        ],
        changelog_entries=["quantifier guidance"],
        batch_index=7,
    )


class SemanticReduceTests(unittest.TestCase):
    def test_partition_is_exact_and_routes_to_canonical_reference(self) -> None:
        rows = enumerate_patch_items([sample_patch()])
        partition = {
            "families": [
                {
                    "family_id": "quantifier-instantiation",
                    "title": "Quantifier instantiation",
                    "reference_file": "references/quantifier-instantiation.md",
                    "member_item_ids": [rows[0]["item_id"]],
                }
            ]
        }
        validate_partition(partition, [rows[0]["item_id"]])
        routed = family_patch(partition["families"][0], {rows[0]["item_id"]: rows[0]})
        self.assertEqual(1, len(routed))
        self.assertEqual(
            "SKILL.md, references/quantifier-instantiation.md",
            routed[0].items[0].target_file,
        )
        self.assertIn("Original MAP instruction", routed[0].items[0].change_instruction)
        self.assertEqual((rows[0]["item_id"],), routed[0].items[0].source_item_ids)

    def test_router_disables_thinking_for_structured_partition(self) -> None:
        rows = enumerate_patch_items([sample_patch()])
        item_id = rows[0]["item_id"]
        response = json.dumps(
            {
                "families": [
                    {
                        "family_id": "quantifier-instantiation",
                        "title": "Quantifier instantiation",
                        "reference_file": "references/quantifier-instantiation.md",
                        "member_item_ids": [item_id],
                    }
                ]
            }
        )
        evolver = object.__new__(SemanticReduceParallelSkillEvolver)
        evolver.client = Mock()
        evolver.client.chat.return_value = response
        evolver.temperature = 0.2
        evolver.max_tokens = 8192
        with patch.object(evolver, "_save_prompt_response"):
            partition = evolver._route_semantic_items(rows)
        self.assertEqual(item_id, partition["families"][0]["member_item_ids"][0])
        messages, settings = evolver.client.chat.call_args.args
        self.assertEqual("system", messages[0].role)
        self.assertEqual(8192, settings.max_tokens)
        self.assertEqual(
            {"thinking": {"type": "disabled"}},
            settings.extra_body,
        )

    def test_partition_rejects_duplicate_or_missing_items(self) -> None:
        rows = enumerate_patch_items([sample_patch()])
        item_id = rows[0]["item_id"]
        invalid = {
            "families": [
                {
                    "family_id": "one",
                    "reference_file": "references/one.md",
                    "member_item_ids": [item_id, item_id],
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_partition(invalid, [item_id])

    def test_family_result_becomes_one_reference_creation_unit(self) -> None:
        reduced = sample_patch()
        reduced.items[0].source_item_ids = ("map_0001_item_001",)
        reduced.items.append(
            SemanticPatchItem(
                target_file="SKILL.md",
                edit_intent="Retain a contraindication",
                location_hint="same family",
                change_instruction="Do not add a trigger that never matches a concrete term.",
                source_item_ids=("map_0002_item_001",),
            )
        )
        family = {
            "family_id": "quantifier-instantiation",
            "title": "Quantifier instantiation",
            "reference_file": "references/quantifier-instantiation.md",
            "member_item_ids": ["map_0001_item_001", "map_0002_item_001"],
        }
        bundled = collapse_family_result(family, reduced)
        self.assertEqual(1, len(bundled.items))
        self.assertIn("Use a concrete term", bundled.items[0].change_instruction)
        self.assertIn("Do not add a trigger", bundled.items[0].change_instruction)
        self.assertEqual(
            ["map_0001_item_001", "map_0002_item_001"],
            patch_source_item_ids([bundled]),
        )

    def test_reduce_provenance_accepts_exact_consolidation(self) -> None:
        first = sample_patch()
        first.items[0].source_item_ids = ("map_0001_item_001",)
        second = sample_patch()
        second.items[0].source_item_ids = ("map_0002_item_001",)
        merged = sample_patch()
        merged.items[0].source_item_ids = (
            "map_0001_item_001",
            "map_0002_item_001",
        )
        audit = validate_exact_once_provenance([first, second], [merged])
        self.assertTrue(audit["exact_once"])

    def test_reduce_provenance_rejects_missing_duplicate_and_unknown_ids(self) -> None:
        first = sample_patch()
        first.items[0].source_item_ids = ("map_0001_item_001",)
        second = sample_patch()
        second.items[0].source_item_ids = ("map_0002_item_001",)
        invalid = sample_patch()
        invalid.items[0].source_item_ids = (
            "map_0001_item_001",
            "map_0001_item_001",
            "map_9999_item_999",
        )
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_exact_once_provenance([first, second], [invalid])

    def test_semantic_parser_reads_optional_source_item_ids(self) -> None:
        parsed, feedback = ParallelSkillEvolver._parse_semantic_patch_block(
            """Reasoning:
retain lineage

Changelog:
- merged

Items:

[ITEM_1_START]
Target File: SKILL.md
Edit Intent: merge
Location Hint: section
Source Item IDs: map_0001_item_001, map_0002_item_001
Change Instruction:
keep both
[ITEM_1_END]""",
            1,
        )
        self.assertEqual("", feedback)
        self.assertEqual(
            ("map_0001_item_001", "map_0002_item_001"),
            parsed.items[0].source_item_ids,
        )

    def test_reduce_hook_records_valid_and_rejected_lineage(self) -> None:
        evolver = object.__new__(SemanticReduceParallelSkillEvolver)
        evolver._provenance_audit_events = []
        evolver._provenance_audit_lock = Lock()
        evolver._active_family_id = "quantifier-instantiation"
        source = sample_patch()
        source.items[0].source_item_ids = ("map_0001_item_001",)
        valid = sample_patch()
        valid.items[0].source_item_ids = ("map_0001_item_001",)
        with patch.object(
            CombinedParallelSkillEvolver,
            "_run_single_merge_markdown",
            return_value=[valid],
        ):
            result = evolver._run_single_merge_markdown({}, [source], 1, 1)
        self.assertEqual([valid], result)
        self.assertTrue(evolver._provenance_audit_events[-1]["exact_once"])

        missing = sample_patch()
        with patch.object(
            CombinedParallelSkillEvolver,
            "_run_single_merge_markdown",
            return_value=[missing],
        ):
            with self.assertRaisesRegex(ValueError, "exactly once"):
                evolver._run_single_merge_markdown({}, [source], 1, 2)
        rejected = evolver._provenance_audit_events[-1]
        self.assertFalse(rejected["exact_once"])
        self.assertEqual(2, rejected["merge_index"])

    def test_combined_reduce_message_exposes_source_ids_to_model(self) -> None:
        source = sample_patch()
        source.items[0].source_item_ids = (
            "map_0001_item_001",
            "map_0002_item_001",
        )
        message = _build_combined_merge_user_message_semantic({}, [source])
        self.assertIn(
            "Source Item IDs: map_0001_item_001, map_0002_item_001",
            message,
        )

    def test_partition_rejects_unsafe_reference_path(self) -> None:
        rows = enumerate_patch_items([sample_patch()])
        invalid = {
            "families": [
                {
                    "family_id": "unsafe",
                    "reference_file": "../secret.md",
                    "member_item_ids": [rows[0]["item_id"]],
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "reference_file"):
            validate_partition(invalid, [rows[0]["item_id"]])


if __name__ == "__main__":
    unittest.main()
