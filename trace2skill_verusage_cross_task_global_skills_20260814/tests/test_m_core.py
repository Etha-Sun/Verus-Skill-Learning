from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE))

import build_m_core as subject  # noqa: E402
import rerender_m_core_layout as rerender  # noqa: E402


def sample_layout() -> dict:
    return {
        "status": "candidate_unvalidated",
        "root": {
            "title": "Verifier-Grounded Repair",
            "description": "Repair Verus proofs with small checked steps.",
            "core_procedures": [
                {
                    "title": "Ground the obligation",
                    "when": "A proof does not verify.",
                    "steps": ["Read the diagnostic.", "State the missing bridge."],
                    "check": "Run Verus after the smallest justified edit.",
                }
            ],
            "consultation_workflow": ["Open references/secret.md."],
            "safety_and_stopping_rules": ["Never add an assume or admit."],
        },
        "references": [
            {
                "filename": "secret.md",
                "title": "Secret",
                "consult_when": "Never in root-only mode.",
                "do_not_consult_when": "Always.",
                "skill_ids": ["verus_global_001"],
            }
        ],
        "layout_notes": [],
    }


class MCoreBuilderTests(unittest.TestCase):
    def test_m_core_prompts_are_local_complete_and_distribution_neutral(self) -> None:
        expected_files = set(subject.PROMPT_NAMES)
        actual_files = {path.name for path in subject.PROMPT_ROOT.glob("*.txt")}
        self.assertEqual(expected_files, actual_files)

        combined = []
        for name in subject.PROMPT_NAMES:
            path = subject.PROMPT_ROOT / name
            text = subject.load_prompt(name)
            self.assertEqual(path.read_text(encoding="utf-8"), text)
            combined.append(text)

        corpus = "\n".join(combined).lower()
        for forbidden in ("ironkv", "train77", "ac/al/ir", "anvil"):
            self.assertNotIn(forbidden, corpus)
        self.assertIn("heterogeneous cross-task", corpus)
        self.assertIn("provenance, not grouping keys", corpus)
        self.assertIn("candidate_unvalidated", corpus)

    def test_layout_prompt_matches_root_only_m_core_contract(self) -> None:
        text = subject.load_prompt("layout_v2_system.txt")
        self.assertIn("only actor-visible artifact", text)
        self.assertIn("must never mention, route to, or depend on R_analysis", text)
        self.assertIn("not included in the M-core baseline", text)
        self.assertIn("separate held-out gate", text)
        self.assertTrue(rerender.trusted_boundary_prompt_audit(text)["valid"])
        self.assertIn("do not categorically ban", text)
        self.assertIn("explicitly permitted by project policy", text)
        self.assertIn("grep hit is therefore an audit trigger", text)
        self.assertIn("do not mandate an unconditional second full verifier run", text.lower())

    def test_unknown_prompt_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            subject.load_prompt("../outside.txt")

    def test_prompt_template_markers_match_builder_contract(self) -> None:
        expected = {
            "discover_v2_user.txt": {"BATCH_ID", "INPUT_MEMORY_COUNT", "CARDS_JSON", "SCHEMA_JSON"},
            "taxonomy_reduce_v3_user.txt": {"LEVEL", "BATCH_ID", "OUTPUT_NODE_ID_PREFIX", "INPUT_NODE_COUNT", "NODES_JSON", "SCHEMA_JSON"},
            "taxonomy_final_v3_user.txt": {"INPUT_NODE_COUNT", "NODES_JSON", "SCHEMA_JSON"},
            "cluster_v2_user.txt": {"CLUSTER_ID", "FAMILY_TITLE", "FAMILY_SCOPE", "INCLUSION_CRITERIA", "EXCLUSION_CRITERIA", "INPUT_CARD_COUNT", "CARDS_JSON", "SCHEMA_JSON"},
            "global_partition_v4_user.txt": {"INPUT_CANDIDATE_COUNT", "COMPACT_CANDIDATES_JSON", "SCHEMA_JSON"},
            "global_group_merge_v4_user.txt": {"GROUP_ID", "OUTPUT_SKILL_ID", "GROUP_TITLE", "MERGE_RATIONALE", "INPUT_CARDS_JSON", "SCHEMA_JSON"},
            "layout_v4_user.txt": {"GLOBAL_SKILL_COUNT", "COMPACT_LIBRARY_JSON", "SCHEMA_JSON"},
        }
        for name, markers in expected.items():
            actual = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", subject.load_prompt(name)))
            self.assertEqual(markers, actual, name)

    def test_cross_task_taxonomy_schema_uses_neutral_family_ids(self) -> None:
        schema = subject.adapted_schema("taxonomy_v2.schema.json")
        family = schema["properties"]["reference_families"]["items"]
        self.assertEqual(
            "^verus_family_[0-9]{3}$",
            family["properties"]["family_id"]["pattern"],
        )

    def test_root_only_renderer_omits_all_reference_routes_and_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            skill_dir = Path(temporary) / "verus-proof-repair"
            audit = subject.render_root_only(skill_dir, sample_layout())
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("secret.md", text)
            self.assertNotIn("verus_global_001", text)
            self.assertNotIn("references/", text)
            self.assertNotIn("consultation", text.lower())
            self.assertFalse((skill_dir / "references").exists())
            self.assertEqual(0, audit["reference_file_count"])
            self.assertEqual(
                ["SKILL.md", "agents/openai.yaml"], audit["skill_tree_files"]
            )
            self.assertGreater(audit["o200k_base_token_count"], 0)

    def test_output_root_must_be_strictly_below_run_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subject.assert_below(root / "m_core", root)
            with self.assertRaises(ValueError):
                subject.assert_below(root, root)
            with self.assertRaises(ValueError):
                subject.assert_below(root.parent / "elsewhere", root)


if __name__ == "__main__":
    unittest.main()
