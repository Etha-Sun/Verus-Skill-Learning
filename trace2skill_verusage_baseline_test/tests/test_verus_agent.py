from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from react_agent import LLMClient
from react_agent.models import Message, ModelSettings

from verus_agent.agent import VerusProofAgent, _prompt_builder
from verus_agent.cli import build_parser
from verus_agent.docs import VerusDocumentation
from verus_agent.tools import SkillReferenceReader
from verus_agent.workspace import prepare_workspace, sha256_file


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "semantic_v4" / "verus-proof-repair"


class FakeClient(LLMClient):
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls = 0

    def chat(self, messages: list[Message], settings: ModelSettings | None = None) -> str:
        self.calls += 1
        if not self.replies:
            raise AssertionError("fake client exhausted")
        return self.replies.pop(0)

    async def chat_async(self, messages: list[Message], settings: ModelSettings | None = None) -> str:
        return self.chat(messages, settings)


def _action(name: str, arguments: dict | None = None) -> str:
    return "Action:\n" + json.dumps({"name": name, "arguments": arguments or {}})


def _executable(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)
    return path


def _docs(root: Path) -> VerusDocumentation:
    guide = root / "guide.json"
    guide.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "title": "Quantifiers",
                        "url": "local://quantifiers",
                        "body": "forall trigger syntax and proof guidance",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    vstd = root / "vstd"
    vstd.mkdir()
    (vstd / "seq.rs").write_text("pub proof fn lemma_len() {}\n", encoding="utf-8")
    return VerusDocumentation(guide, vstd)


class WorkspaceTests(unittest.TestCase):
    def test_source_is_immutable_and_exact_edit_is_audited(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.rs"
            source.write_text("fn proof() { assert(false); }\n", encoding="utf-8")
            before = sha256_file(source)
            workspace = prepare_workspace(source, root / "run")
            workspace.replace_text("assert(false)", "assert(true)")
            self.assertEqual(before, sha256_file(source))
            self.assertIn("assert(true)", workspace.candidate_path.read_text())
            self.assertNotIn("assert(true)", workspace.input_path.read_text())
            self.assertTrue(workspace.audit_path.is_file())

    def test_workspace_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.rs"
            source.write_text("fn proof() {}\n", encoding="utf-8")
            run = root / "run"
            prepare_workspace(source, run)
            with self.assertRaisesRegex(ValueError, "absent or empty"):
                prepare_workspace(source, run)

    def test_verification_bypass_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.rs"
            source.write_text("fn proof() {}\n", encoding="utf-8")
            workspace = prepare_workspace(source, root / "run")
            with self.assertRaisesRegex(ValueError, "bypass"):
                workspace.replace_text("{}", "{ assume(true); }")


class SkillAndDocsTests(unittest.TestCase):
    def test_different_references_load_dynamically_but_duplicate_is_suppressed(self) -> None:
        reader = SkillReferenceReader(SKILL_DIR)
        first = reader.read("recursive_sequence_fold_induction.md")
        second = reader.read("finite_set_membership_equality.md")
        third = reader.read("recursive_sequence_fold_induction.md")
        self.assertIn("Recursive Sequence and Fold Induction", first)
        self.assertIn("Finite-Set Cardinality", second)
        self.assertIn("already loaded", third)
        self.assertNotIn("Recursive Sequence and Fold Induction", third)
        self.assertEqual(
            reader.read_history,
            ["recursive_sequence_fold_induction.md", "finite_set_membership_equality.md"],
        )

    def test_card_id_loads_hidden_middle_card_and_suppresses_exact_duplicate(self) -> None:
        reader = SkillReferenceReader(SKILL_DIR)
        first = reader.read(
            "references/finite_set_membership_equality.md", "verus_global_015"
        )
        duplicate = reader.read(
            "finite_set_membership_equality.md", "verus_global_015"
        )
        different_card = reader.read(
            "finite_set_membership_equality.md", "verus_global_016"
        )
        self.assertIn("choose-based witness extraction", first)
        self.assertNotIn("verus_global_011", first)
        self.assertIn("already loaded", duplicate)
        self.assertNotIn("choose-based witness extraction", duplicate)
        self.assertIn("explicit forall", different_card)
        self.assertEqual(
            reader.read_history,
            [
                "finite_set_membership_equality.md#verus_global_015",
                "finite_set_membership_equality.md#verus_global_016",
            ],
        )

    def test_whole_reference_is_not_returned_after_targeted_card_read(self) -> None:
        reader = SkillReferenceReader(SKILL_DIR)
        reader.read("finite_set_membership_equality.md", "verus_global_015")
        result = reader.read("finite_set_membership_equality.md")
        self.assertIn("already loaded", result)
        self.assertIn("verus_global_016", result)
        self.assertNotIn("choose-based witness extraction", result)

    def test_long_card_is_paged_below_observation_limit(self) -> None:
        reader = SkillReferenceReader(SKILL_DIR)
        first = reader.read(
            "ordering_sortedness_range_proofs.md", "verus_global_007", page=1
        )
        with self.assertRaisesRegex(ValueError, "out of range"):
            reader.read(
                "ordering_sortedness_range_proofs.md", "verus_global_007", page=2
            )
        duplicate = reader.read(
            "ordering_sortedness_range_proofs.md", "verus_global_007", page=1
        )
        self.assertIn("old/new key split", first)
        self.assertLess(len(first), 5000)
        self.assertIn("already loaded", duplicate)
        self.assertEqual(
            reader.read_history,
            ["ordering_sortedness_range_proofs.md#verus_global_007"],
        )

    def test_root_index_reference_path_is_accepted_and_normalized(self) -> None:
        reader = SkillReferenceReader(SKILL_DIR)
        text = reader.read("references/finite_set_membership_equality.md")
        self.assertIn("Finite-Set Cardinality", text)
        self.assertEqual(reader.read_history, ["finite_set_membership_equality.md"])

    def test_documentation_is_local_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = _docs(Path(temp))
            result = docs.search("forall trigger", top_k=1)
            self.assertFalse(result["network_access"])
            self.assertEqual(len(result["results"]), 1)
            lookup = docs.lookup("lemma_len")
            self.assertFalse(lookup["network_access"])
            self.assertEqual(lookup["matches"][0]["matched_line"], 1)

    def test_all_root_index_cards_have_one_runtime_reference(self) -> None:
        root_ids = set(re.findall(r"verus_global_\d{3}", (SKILL_DIR / "SKILL.md").read_text()))
        reference_ids = set()
        for path in (SKILL_DIR / "references").glob("*.md"):
            reference_ids.update(re.findall(r"^## (verus_global_\d{3}) — ", path.read_text(), re.MULTILINE))
        self.assertEqual(len(root_ids), 88)
        self.assertEqual(root_ids, reference_ids)


class SkillPromptTests(unittest.TestCase):
    def test_root_skill_contains_procedure_and_complete_reference_map(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Core procedures", skill)
        self.assertIn("## Progressive reference consultation", skill)
        self.assertIn("## Progressive reference consultation", skill)
        self.assertIn("## Reference map", skill)
        self.assertIn("return to M", skill)
        self.assertIn("do not preload all references", skill)
        self.assertNotIn("first Action must be read_skill_reference", skill)
        card_ids = set(re.findall(r"verus_global_\d{3}", skill))
        self.assertEqual(card_ids, {f"verus_global_{index:03d}" for index in range(1, 89)})

    def test_with_skill_matches_upstream_preloaded_skill_resource_policy(self) -> None:
        prompt = _prompt_builder("# Root procedure\n- Classify the obligation").build(tools=[])
        self.assertIn("has been loaded for this session", prompt)
        self.assertIn("its full guidance is included below", prompt)
        self.assertIn("If the skill is relevant", prompt)
        self.assertIn("follow its instructions", prompt)
        self.assertIn("own judgment only when", prompt)
        self.assertIn("Reference resources mentioned by the root", prompt)
        self.assertIn("read_skill_reference", prompt)
        self.assertIn("Open them on demand", prompt)
        self.assertIn("not a mandatory first action", prompt)
        self.assertNotIn("your first Action must be read_skill_reference", prompt)
        self.assertNotIn("Select exactly one card", prompt)
        self.assertIn("record_proof_progress", prompt)
        self.assertIn("next Action MUST be record_proof_progress", prompt)
        self.assertIn("evidence_turns", prompt)
        self.assertIn("structurally unbalanced edits are rejected", prompt)

    def test_no_skill_prompt_has_no_reference_requirement(self) -> None:
        prompt = _prompt_builder(None).build(tools=[])
        self.assertNotIn("your first Action must be read_skill_reference", prompt)
        self.assertNotIn("root SKILL.md is preloaded", prompt)
        self.assertNotIn("Reference consultation is optional", prompt)


class AgentTests(unittest.TestCase):
    def test_same_react_conversation_reads_multiple_refs_edits_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.rs"
            source.write_text("fn proof() { assert(false); }\n", encoding="utf-8")
            verus = _executable(
                root / "verus",
                "#!/bin/sh\nif grep -q 'assert(true)' candidate.rs; then echo '1 verified, 0 errors'; exit 0; fi\necho 'error: assertion failed' >&2\nexit 1\n",
            )
            lynette = _executable(root / "lynette", "#!/bin/sh\nexit 0\n")
            workspace = prepare_workspace(source, root / "run")
            workspace.verus_bin = verus
            workspace.lynette_bin = lynette
            client = FakeClient(
                [
                    _action("read_skill_reference", {"reference": "ordering_sortedness_range_proofs.md"}),
                    _action("read_skill_reference", {"reference": "finite_set_membership_equality.md"}),
                    _action("read_file", {"path": "candidate.rs", "line_start": 1, "line_end": 20}),
                    _action("replace_text", {"old_text": "assert(false)", "new_text": "assert(true)"}),
                    _action("run_verus"),
                    _action("run_lynette"),
                    "ACTION: TASK_COMPLETE",
                ]
            )
            runner = VerusProofAgent(
                client=client,
                workspace=workspace,
                documentation=_docs(root),
                skill_dir=SKILL_DIR,
                max_turns=12,
                verbose=False,
            )
            result = runner.run()
            self.assertTrue(result.success)
            self.assertEqual(client.calls, 7)
            self.assertEqual(
                result.reference_reads,
                ["ordering_sortedness_range_proofs.md", "finite_set_membership_equality.md"],
            )
            self.assertTrue(result.validation["complete"])
            self.assertFalse(result.loop_control["skill_navigation_enabled"])
            self.assertEqual(result.loop_control["skill_navigation_checkpoints"], 0)
            self.assertIn("assert(false)", source.read_text())

    def test_premature_completion_resumes_same_conversation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.rs"
            source.write_text("fn proof() {}\n", encoding="utf-8")
            verus = _executable(root / "verus", "#!/bin/sh\necho '1 verified, 0 errors'\nexit 0\n")
            lynette = _executable(root / "lynette", "#!/bin/sh\nexit 0\n")
            workspace = prepare_workspace(source, root / "run")
            workspace.verus_bin = verus
            workspace.lynette_bin = lynette
            client = FakeClient(["ACTION: TASK_COMPLETE", _action("run_lynette"), "ACTION: TASK_COMPLETE"])
            runner = VerusProofAgent(
                client=client,
                workspace=workspace,
                documentation=_docs(root),
                skill_dir=None,
                max_turns=6,
                verbose=False,
            )
            result = runner.run()
            self.assertTrue(result.success)
            self.assertEqual(client.calls, 3)


    def test_host_validation_counts_success_without_final_completion_signal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.rs"
            source.write_text("fn proof() {}\n", encoding="utf-8")
            verus = _executable(
                root / "verus", "#!/bin/sh\necho '1 verified, 0 errors'\nexit 0\n"
            )
            lynette = _executable(root / "lynette", "#!/bin/sh\nexit 0\n")
            workspace = prepare_workspace(source, root / "run")
            workspace.verus_bin = verus
            workspace.lynette_bin = lynette
            client = FakeClient([_action("run_verus"), _action("run_lynette")])
            runner = VerusProofAgent(
                client=client,
                workspace=workspace,
                documentation=_docs(root),
                skill_dir=None,
                max_turns=2,
                verbose=False,
            )

            result = runner.run()

            self.assertFalse(result.agent_result.success)
            self.assertIn("Max turns", result.agent_result.error)
            self.assertTrue(result.validation["complete"])
            self.assertTrue(result.success)


class CliTests(unittest.TestCase):
    def test_cli_uses_same_defaults_for_both_experiment_arms(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--input", "task.rs",
                "--work-dir", "run",
                "--verus-bin", "verus",
                "--lynette-bin", "lynette",
                "--guide-snapshot", "guide.json",
                "--vstd-root", "vstd",
            ]
        )
        self.assertEqual(args.model, "qwen35-27b")
        self.assertEqual(args.base_url, "http://127.0.0.1:8000/v1")
        self.assertEqual(args.max_turns, 60)
        self.assertEqual(args.max_no_progress_turns, 10)
        self.assertEqual(args.temperature, 0.2)
        self.assertFalse(args.no_skill)


if __name__ == "__main__":
    unittest.main()
