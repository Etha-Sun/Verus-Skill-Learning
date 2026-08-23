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
            self.assertFalse(manifest["filesystem_visibility_enforced"])
            self.assertEqual((workspace / "input.rs").stat().st_mode & 0o222, 0)
            self.assertEqual((workspace / "SKILL.md").stat().st_mode & 0o222, 0)

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

    def test_skill_can_use_reference_nested_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.rs"
            source.write_text("fn proof_task() {}\n", encoding="utf-8")
            workspace = root / "run" / "workspace"
            manifest = prepare_solver_workspace(
                source=source,
                workspace=workspace,
                task_text="Repair candidate.rs.\n",
                skill_text="Use the smallest proof-only edit.\n",
                skill_relative_path="skill/verus-proof-repair/SKILL.md",
            )
            nested = workspace / "skill" / "verus-proof-repair" / "SKILL.md"
            self.assertTrue(nested.is_file())
            roles = {
                row["relative_path"]: row["role"] for row in manifest["files"]
            }
            self.assertEqual(
                roles["skill/verus-proof-repair/SKILL.md"], "candidate_skill"
            )

    def test_skill_bundle_copies_entrypoint_and_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.rs"
            source.write_text("fn proof_task() {}\n", encoding="utf-8")
            bundle = root / "verus-proof-repair"
            (bundle / "references").mkdir(parents=True)
            (bundle / "SKILL.md").write_text(
                "Read references/loops.md.\n", encoding="utf-8"
            )
            (bundle / "references" / "loops.md").write_text(
                "Preserve the loop invariant.\n", encoding="utf-8"
            )
            executable = bundle / "scripts" / "inspect.sh"
            executable.parent.mkdir()
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o755)
            workspace = root / "run" / "workspace"
            manifest = prepare_solver_workspace(
                source=source,
                workspace=workspace,
                task_text="Repair candidate.rs.\n",
                skill_source_dir=bundle,
                skill_relative_path="skill/verus-proof-repair/SKILL.md",
            )
            reference = (
                workspace / "skill" / "verus-proof-repair" / "references" / "loops.md"
            )
            self.assertTrue(reference.is_file())
            roles = {
                row["relative_path"]: row["role"] for row in manifest["files"]
            }
            self.assertEqual(
                roles["skill/verus-proof-repair/references/loops.md"],
                "candidate_skill",
            )
            copied_executable = (
                workspace / "skill" / "verus-proof-repair" / "scripts" / "inspect.sh"
            )
            self.assertNotEqual(copied_executable.stat().st_mode & 0o111, 0)
            self.assertEqual(copied_executable.stat().st_mode & 0o222, 0)

    def test_skill_bundle_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.rs"
            source.write_text("fn proof_task() {}\n", encoding="utf-8")
            bundle = root / "verus-proof-repair"
            bundle.mkdir()
            (bundle / "SKILL.md").write_text("skill\n", encoding="utf-8")
            (bundle / "linked.md").symlink_to(bundle / "SKILL.md")
            with self.assertRaisesRegex(ValueError, "must not contain symlinks"):
                prepare_solver_workspace(
                    source=source,
                    workspace=root / "workspace",
                    task_text="task",
                    skill_source_dir=bundle,
                )


if __name__ == "__main__":
    unittest.main()
