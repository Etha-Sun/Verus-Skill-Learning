from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from verus_agent.tools import create_workspace_tools
from verus_agent.workspace import prepare_workspace, sha256_file


def make_workspace(root: Path):
    source = root / "source.rs"
    source.write_text(
        "fn proof() {\n    assert(false);\n    assert(1 == 1);\n}\n",
        encoding="utf-8",
    )
    return source, prepare_workspace(source, root / "run")


class StructuredLineEditTests(unittest.TestCase):
    def test_multiline_edit_uses_json_line_array_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source, workspace = make_workspace(Path(temp))
            source_sha = sha256_file(source)
            result = workspace.edit_lines(
                2,
                3,
                ["    assert(true);", "    assert(2 == 2);", "    assert(3 == 3);"],
            )
            self.assertIn("replaced with 3 line", result)
            self.assertEqual(
                workspace.candidate_path.read_text(encoding="utf-8"),
                "fn proof() {\n    assert(true);\n    assert(2 == 2);\n    assert(3 == 3);\n}\n",
            )
            self.assertEqual(source_sha, sha256_file(source))
            self.assertIn("assert(false)", workspace.input_path.read_text())
            audit = json.loads(workspace.audit_path.read_text().splitlines()[-1])
            self.assertEqual(audit["operation"], "edit_lines")
            self.assertNotIn("assert(true)", json.dumps(audit))

    def test_insert_and_delete_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            _, workspace = make_workspace(Path(temp))
            workspace.insert_lines(1, ["    // proof setup", "    assert(true);"])
            self.assertEqual(
                workspace.candidate_path.read_text().splitlines()[1:3],
                ["    // proof setup", "    assert(true);"],
            )
            workspace.edit_lines(2, 3, [])
            self.assertNotIn("proof setup", workspace.candidate_path.read_text())

    def test_unbalanced_block_replacement_is_rejected_without_modifying_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            _, workspace = make_workspace(Path(temp))
            before = workspace.candidate_path.read_text(encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError, r"curly-brace balance.*candidate.rs was not modified"
            ):
                workspace.edit_lines(
                    1,
                    3,
                    ["fn proof() {", "    assert(true);", "}"],
                )
            self.assertEqual(before, workspace.candidate_path.read_text(encoding="utf-8"))
            self.assertFalse(workspace.audit_path.exists())

    def test_braces_in_strings_and_comments_do_not_trigger_structure_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            _, workspace = make_workspace(Path(temp))
            result = workspace.edit_lines(
                2,
                2,
                ['    assert("}".len() == 1); // { is documentation only'],
            )
            self.assertIn("run Verus next", result)
            self.assertIn('assert("}".len()', workspace.candidate_path.read_text())

    def test_rejects_embedded_newline_and_multiline_replace_text(self):
        with tempfile.TemporaryDirectory() as temp:
            _, workspace = make_workspace(Path(temp))
            with self.assertRaisesRegex(ValueError, "one physical line"):
                workspace.edit_lines(2, 2, ["a\nb"])
            with self.assertRaisesRegex(ValueError, "single-line only"):
                workspace.replace_text("assert(false);\n", "assert(true);\n")

    def test_line_edits_keep_bypass_protection(self):
        with tempfile.TemporaryDirectory() as temp:
            _, workspace = make_workspace(Path(temp))
            with self.assertRaisesRegex(ValueError, "bypass"):
                workspace.edit_lines(2, 2, ["    assume(true);"])
            with self.assertRaisesRegex(ValueError, "bypass"):
                workspace.insert_lines(1, ["    admit();"])

    def test_tool_schema_exposes_arrays_not_multiline_strings(self):
        with tempfile.TemporaryDirectory() as temp:
            _, workspace = make_workspace(Path(temp))
            tools = {tool.name: tool for tool in create_workspace_tools(workspace)}
            edit_schema = tools["edit_lines"].get_params_schema()
            insert_schema = tools["insert_lines"].get_params_schema()
            self.assertEqual(
                edit_schema["properties"]["replacement_lines"]["type"], "array"
            )
            self.assertEqual(insert_schema["properties"]["new_lines"]["type"], "array")
            self.assertIn(
                "unbalance structural curly braces", tools["edit_lines"].description
            )
            result = tools["edit_lines"].execute(
                line_start=2,
                line_end=3,
                replacement_lines=["    assert(true);"],
            )
            self.assertNotIn("Error", result)
            self.assertIn("assert(true)", workspace.candidate_path.read_text())


if __name__ == "__main__":
    unittest.main()
