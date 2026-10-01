import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "fork_card_optimize",
    ROOT / "src/skillopt_verusage/fork_card_optimize.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ForkCardOptimizeTests(unittest.TestCase):
    def test_evidence_survives_native_normalization_with_bound_source_ids(self):
        from skillopt.engine.trainer import _normalise_patches
        original = {"card_index": 0, "counterexample_or_boundary": "hint failed",
                    "available_costs": "no paired cost for original-only"}
        proposal = {"patch": {"edits": [{"op": "append", "content": "card"}]},
                    "card_evidence": [original]}
        m.attach_card_evidence(proposal, "fork_ir")
        failures, _ = _normalise_patches([proposal], "patch")
        self.assertEqual(failures[0]["card_evidence"][0], {**original, "source_card": "fork_ir:0"})
        self.assertEqual(failures[0]["edits"][0]["source_cards"], ["fork_ir:0"])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            m.attach_card_evidence({"patch": {"edits": [{}]}, "card_evidence": []}, "fork_ir")

    def test_bank_rejects_lost_evidence_and_inflated_support(self):
        patches = [{"card_evidence": [{"source_card": "fork_ir:0"}, {"source_card": "fork_ir:1"}]}]
        merged = {"edits": [{"source_cards": ["fork_ir:0", "fork_ir:1"], "support_count": 1}],
                  "evidence_review": [{"source_card": "fork_ir:0"}, {"source_card": "fork_ir:1"}]}
        self.assertEqual(m.audit_bank_provenance(merged, patches), [])
        merged["edits"][0]["support_count"] = 2
        self.assertIn("support count differs from distinct source tasks", m.audit_bank_provenance(merged, patches))
        merged["edits"][0]["source_cards"] = ["fork_ir:0"]
        self.assertIn("each source card must be retained/merged/dropped exactly once", m.audit_bank_provenance(merged, patches))

    def test_prepares_one_equal_weight_reflection_item_per_task(self):
        with tempfile.TemporaryDirectory() as directory:
            run_root = Path(directory) / "run-root"
            packet = run_root / "packet"
            tasks = []
            for project, count in (("IR", 6), ("AC", 6), ("AL", 7)):
                index = packet / f"tasks/{project.lower()}/OPTIMIZER_HINT_VISIBLE.md"
                index.parent.mkdir(parents=True, exist_ok=True)
                index.write_text(f"# {project}\n")
                tasks.append({
                    "project": project,
                    "task_id": f"{project.lower()}-task",
                    "task_weight": 1,
                    "checkpoint_count": count,
                    "optimizer_index": f"tasks/{project.lower()}/OPTIMIZER_HINT_VISIBLE.md",
                })
            (packet / "manifest.json").write_text(json.dumps({
                "schema_version": "skillopt-fork-packet-v1",
                "optimizer_view": "hint_visible",
                "tasks": tasks,
            }))
            out = packet / "skillopt"
            with mock.patch.dict(os.environ, {"VERUS_SKILL_RUN_ROOT": str(run_root)}):
                results, predictions = m.prepare_reflection_inputs(packet, out)
            self.assertEqual(len(results), 3)
            self.assertEqual(sum(row["task_weight"] for row in results), 3)
            self.assertEqual([row["n_turns"] for row in results], [6, 6, 7])
            for row in results:
                conversation = json.loads((predictions / row["id"] / "conversation.json").read_text())
                self.assertIn("total task weight one", conversation[0]["content"])

    def test_contrast_pair_excludes_failed_shortcuts_and_retains_failure(self):
        def row(cp, tokens, passed):
            return {"checkpoint": cp, "arms": {
                "no_hint": {"dual_pass": True, "actor_completion_tokens": 100},
                "v1": {"dual_pass": passed, "actor_completion_tokens": tokens},
                "v2": {"dual_pass": True, "actor_completion_tokens": 100}}}
        rows = [row("CP01", 1, False), row("CP02", 20, True), row("CP03", 200, True)]
        self.assertEqual(m.select_contrast_pair(rows), ["CP02", "CP01"])
        with self.assertRaisesRegex(ValueError, "two distinct"):
            m.select_contrast_pair([rows[1]])

    def test_card_audit_requires_triggered_card_shape(self):
        valid = {
            "edits": [{"op": "append", "content": "**Trigger:** x\n**Action:** y\n**Validate:** z\n**Avoid when:** q"}]
        }
        report = [{"status": "applied_append"}]
        self.assertEqual(m._card_audit("seed", valid, report), [])
        invalid = {"edits": [{"content": "generic advice"}]}
        self.assertIn("card 0 omits Trigger:", m._card_audit("seed", invalid, report))

    def test_card_labels_must_be_present_in_each_append(self):
        labels = "Trigger: x\nAction: y\nValidate: z\nAvoid when: q"
        ranked = {"edits": [{"op": "append", "content": labels}, {"op": "insert_after", "content": "generic advice"}]}
        errors = m._card_audit("seed", ranked, [{"status": "applied_append"}])
        self.assertIn("card 1 omits Trigger:", errors)
        self.assertIn("card 1 is not an append edit", errors)

    def test_call_usage_does_not_double_count_logical_records(self):
        from skillopt_verusage.codex_reoptimize import _ledger_summary
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calls.jsonl"
            rows = [
                {"record_type": "optimizer_attempt", "status": "success", "stage": "analyst", "usage": {"prompt_tokens": 12, "completion_tokens": 3}},
                {"record_type": "optimizer_logical_call", "status": "success", "stage": "analyst"},
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            result = _ledger_summary(path)
            self.assertEqual(result["successful_calls"], 1)
            self.assertEqual(result["logical_calls"], 1)
            self.assertEqual(result["total"], {"calls": 1, "prompt_tokens": 12, "completion_tokens": 3})


if __name__ == "__main__":
    unittest.main()
