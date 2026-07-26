import tempfile
import unittest
from pathlib import Path

from skill_evolution_pilot.workspace import prepare_solver_workspace, sha256_file


class WorkspaceTest(unittest.TestCase):
    def test_allowlisted_workspace_and_immutable_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.rs"
            source.write_text("fn proof_task() {}\n", encoding="utf-8")
            source_hash = sha256_file(source)
            workspace = root / "run" / "workspace"
            manifest = prepare_solver_workspace(
                source=source,
                workspace=workspace,
                task_text="Solve candidate.rs.",
                skill_text="Use an invariant.",
                extra_files={"tools/README.md": "allowlisted wrapper"},
            )
            visible = {row["relative_path"] for row in manifest["files"]}
            self.assertEqual(
                visible,
                {
                    "SKILL.md",
                    "TASK.md",
                    "candidate.rs",
                    "input.rs",
                    "tools/README.md",
                },
            )
            self.assertEqual(manifest["input_sha256"], source_hash)
            self.assertFalse(manifest["reference_proof_visible"])
            self.assertEqual((workspace / "input.rs").stat().st_mode & 0o222, 0)

    def test_extra_file_cannot_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.rs"
            source.write_text("fn proof_task() {}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escapes"):
                prepare_solver_workspace(
                    source=source,
                    workspace=root / "workspace",
                    task_text="task",
                    extra_files={"../answer.rs": "leak"},
                )


if __name__ == "__main__":
    unittest.main()
