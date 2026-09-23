import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "fork_packets", ROOT / "scripts/export_skillopt_fork_packets.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

adapter_spec = importlib.util.spec_from_file_location(
    "adapt_published_hint_traces",
    ROOT / "scripts/adapt_published_hint_traces.py",
)
adapter = importlib.util.module_from_spec(adapter_spec)
adapter_spec.loader.exec_module(adapter)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value)
    else:
        path.write_text(json.dumps(value) + "\n")


def complete_trace(root, events, candidate="checkpoint\n"):
    files = {
        "agent_events.jsonl": "".join(json.dumps(row) + "\n" for row in events),
        "codex_events.raw.jsonl": json.dumps({"type": "turn.completed"}) + "\n",
        "conversation.json": json.dumps([{"role": "assistant", "content": "full"}]),
        "result.json": json.dumps({"hard": 1}),
        "run_manifest.json": json.dumps({"model": "deepseek-v4-pro"}),
        "prompt.txt": "prompt\n",
        "target_user_prompt.txt": "target\n",
        "workspace/input.rs": "input\n",
        "workspace/candidate.rs": candidate,
    }
    for relative, content in files.items():
        write(root / relative, content)
    write(root / "snapshots/000001-candidate.rs", candidate)
    write(root / "snapshots/000001-candidate.diff", "source diff\n")


class ForkPacketTests(unittest.TestCase):
    def test_adapts_hash_verified_recorded_hint_archive_without_rerun(self):
        checkpoint = "checkpoint\n"
        digest = hashlib.sha256(checkpoint.encode()).hexdigest()
        event = {
            "event_index": 0,
            "actor": "codex",
            "type": "snapshot",
            "candidate_sha256": digest,
            "data": {"snapshot": "snapshots/000001-candidate.rs"},
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive = base / "archive"
            source = archive / "ir/v1/CP01"
            complete_trace(source, [event])
            write(
                source / "hint_contract.json",
                {
                    "checkpoint_sha256": digest,
                    "actor_skill_sha256": adapter.INITIAL_SKILL_SHA256,
                },
            )
            write(source / "hint.txt", "fixed advice")
            write(
                source / "validation.json",
                {"verus": {"passed": True}, "lynette": {"passed": True}},
            )
            file_rows = []
            for path in sorted(source.rglob("*")):
                if path.is_file():
                    file_rows.append(
                        {
                            "path": str(path.relative_to(source)),
                            "published_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        }
                    )
            run = {
                "task": "ir",
                "version": "v1",
                "checkpoint": "CP01",
                "task_id": "task-id",
                "event_count": 1,
                "files": file_rows,
            }
            dummy = {
                "task": "unused",
                "version": "unused",
                "checkpoint": "unused",
                "task_id": "unused",
                "event_count": 0,
                "files": [],
            }
            write(archive / "manifest.json", {"runs": [run, *([dummy] * 37)]})
            publication = base / "publication/ir"
            write(
                publication / "selection_manifest.json",
                {
                    "checkpoints": [
                        {
                            "event_index": 7,
                            "candidate_sha256": digest,
                            "continue": True,
                        }
                    ]
                },
            )
            write(
                publication / "v1/CP01/hint.json",
                {"checkpoint_sha256": digest, "hint_text": "fixed advice"},
            )
            run_root = base / "run-root"
            output = run_root / "adapted"
            with mock.patch.dict(os.environ, {"VERUS_SKILL_RUN_ROOT": str(run_root)}):
                result = adapter.adapt(
                    trace_archive_root=archive,
                    publication_project_root=publication,
                    output_root=output,
                    project="IR",
                    version="v1",
                    source_git_commit="trace-commit",
                )

            self.assertEqual(result["run_count"], 1)
            self.assertEqual(result["dual_verifier_pass_count"], 1)
            self.assertEqual(
                (output / "hint-private/task-id/CP01/checkpoint.rs").read_text(),
                checkpoint,
            )
            provenance = json.loads(
                (output / "runs/task-id/CP01/recorded_trace_provenance.json").read_text()
            )
            self.assertFalse(provenance["trajectory_rerun_in_current_run"])
            self.assertFalse(provenance["hint_generation_api_called_in_current_run"])

    def test_exports_complete_task_group_with_explicit_visibility(self):
        checkpoint = "checkpoint\n"
        digest = hashlib.sha256(checkpoint.encode()).hexdigest()
        verifier = {
            "event_index": 1,
            "actor": "verus",
            "type": "verifier",
            "candidate_sha256": digest,
            "data": {"raw_codex_event": {"item": {"aggregated_output": "proof failed"}}},
        }
        original_events = [
            {"event_index": 0, "actor": "codex", "type": "lifecycle"},
            verifier,
            {"event_index": 2, "actor": "codex", "type": "edit"},
        ]
        branch_events = [{"event_index": 0, "actor": "codex", "type": "lifecycle"}]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); original = base / "original"
            complete_trace(original, original_events)
            arms = {name: base / name for name in ("v1", "v2", "no_hint")}
            task = {"id": "task-id", "task_id": "task-name"}
            selection = {
                "task": task,
                "checkpoints": [
                    {"ordinal": 1, "event_index": 1, "checkpoint_sha256": digest}
                ],
            }
            for name, root in arms.items():
                write(root / "selection.json", {**selection, "condition": "matched_no_hint" if name == "no_hint" else "generated_hint"})
                if name == "no_hint":
                    cp = root / "checkpoints/task-id/CP01.rs"
                else:
                    cp = root / "hint-private/task-id/CP01/checkpoint.rs"
                write(cp, checkpoint)
                run = root / "runs/task-id/CP01"
                complete_trace(run, branch_events)
                if name == "no_hint":
                    write(run / "condition_contract.json", {"condition": "matched_no_hint", "teacher_hint_visible_to_actor": False})
                else:
                    write(root / "hint-private/task-id/CP01/hint.json", {"checkpoint_sha256": digest, "hint_text": f"{name} advice"})
                    write(run / "hint_contract.json", {"condition": f"published_hint_{name}", "checkpoint_sha256": digest})
                    if name == "v1":
                        write(root / "hint-private/task-id/CP01/published_hint_replay.json", {
                            "hint_generation_api_called": False,
                            "checkpoint_sha256": digest,
                            "hint_version": "v1",
                        })

            output = base / "run-root" / "packets"
            config = {
                "output_root": str(output),
                "tasks": [{"project": "IR", "task_id": "task-id", "original_run": str(original), "arms": {name: str(root) for name, root in arms.items()}}],
            }
            with mock.patch.dict(os.environ, {"VERUS_SKILL_RUN_ROOT": str(base / "run-root")}):
                manifest = m.export(config)

            self.assertEqual(manifest["task_count"], 1)
            self.assertEqual(manifest["branch_count"], 3)
            task_root = output / "tasks/ir"
            fork = json.loads((task_root / "checkpoints/CP01/fork.json").read_text())
            self.assertTrue(fork["prefix_plus_suffix_reconstructs_original"])
            self.assertFalse(fork["branches"]["no_hint"]["teacher_hint_visible_to_actor"])
            self.assertTrue(fork["branches"]["v1"]["teacher_hint_visible_to_actor"])
            prefix = m.load_jsonl(task_root / "checkpoints/CP01/original_prefix.agent_events.jsonl")
            suffix = m.load_jsonl(task_root / "checkpoints/CP01/original_suffix.agent_events.jsonl")
            self.assertEqual(prefix + suffix, original_events)
            index = (task_root / "OPTIMIZER_HINT_VISIBLE.md").read_text()
            self.assertIn("matched no-hint continuation", index)
            self.assertIn("teacher intervention", index)
            copied = task_root / "checkpoints/CP01/branches/no_hint/trace/snapshots/000001-candidate.rs"
            self.assertEqual(copied.read_text(), checkpoint)
            self.assertIn("snapshots/000001-candidate.rs", fork["branches"]["no_hint"]["complete_trace_sha256"])
            replay_branch = fork["branches"]["v1"]
            self.assertFalse(replay_branch["hint_generation_api_called_in_current_run"])
            self.assertEqual(replay_branch["hint_source"], "reviewed published intervention replay")
            self.assertTrue((task_root / "checkpoints/CP01/branches/v1/published_hint_replay.json").is_file())
            self.assertIn("hint_contract.json", replay_branch["complete_trace_sha256"])

    def test_rejects_unresolved_snapshot_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            complete_trace(root, [{
                "event_index": 1,
                "actor": "host",
                "type": "lifecycle",
                "candidate_sha256": hashlib.sha256(b"checkpoint\n").hexdigest(),
                "data": {"snapshot": "snapshots/missing-candidate.rs"},
            }])
            with self.assertRaisesRegex(ValueError, "unresolved snapshot"):
                m.copy_complete_trace(root, root.parent / "copied")

    def test_rejects_output_outside_run_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with mock.patch.dict(os.environ, {"VERUS_SKILL_RUN_ROOT": str(base / "allowed")}):
                with self.assertRaises(ValueError):
                    m.require_output_root(base / "elsewhere")


if __name__ == "__main__":
    unittest.main()
