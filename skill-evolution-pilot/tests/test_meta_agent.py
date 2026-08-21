from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skill_evolution_pilot.meta_agent import (
    _outside_workspace_commands,
    meta_output_schema,
    prepare_meta_workspace,
    prepare_token_meta_workspace,
    token_output_schema,
    validate_meta_output,
    validate_token_meta_output,
)


def valid_output() -> dict[str, object]:
    return {
        "schema_version": "1",
        "objective": "token_cost",
        "diagnosis": "Repeated broad searches dominate tokens.",
        "retained_principle": "Verify after a focused proof edit.",
        "rejected_principle": "Dump every possible lemma into the proof.",
        "revised_meta_skill": "Prefer bounded diagnosis and early verification.",
        "skills": [
            {
                "skill_id": profile,
                "profile": profile,
                "title": profile,
                "hypothesis": "Reduce unproductive exploration.",
                "applicability": "Incomplete Verus proof.",
                "negative_scope": "Do not use after a safety failure.",
                "content": f"Use the {profile} bounded workflow.",
            }
            for profile in ("aggressive", "conservative", "structural")
        ],
    }


class MetaAgentTest(unittest.TestCase):
    def test_schema_const_properties_have_explicit_types(self) -> None:
        properties = token_output_schema()["properties"]
        self.assertEqual(properties["schema_version"]["type"], "string")
        self.assertEqual(properties["objective"]["type"], "string")

    def test_visibility_audit_ignores_shell_runtime_but_flags_external_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw.jsonl"
            raw.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "/usr/bin/bash -lc 'sed -n 1,2p evidence/a'",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(_outside_workspace_commands(raw, root), [])
            raw.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "/usr/bin/bash -lc 'sed -n 1,2p /private/a'",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertTrue(_outside_workspace_commands(raw, root))

    def test_validates_exact_profiles(self) -> None:
        self.assertEqual(validate_token_meta_output(valid_output()), [])
        value = valid_output()
        value["skills"][2]["profile"] = "aggressive"  # type: ignore[index]
        self.assertTrue(validate_token_meta_output(value))

    def test_small_model_objective_is_independent(self) -> None:
        value = valid_output()
        value["objective"] = "small_model_solve_rate"
        self.assertEqual(
            validate_meta_output(value, "small_model_solve_rate"),
            [],
        )
        self.assertEqual(
            meta_output_schema("small_model_solve_rate")["properties"]["objective"][
                "const"
            ],
            "small_model_solve_rate",
        )

    def test_workspace_contains_only_allowlisted_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            run.mkdir()
            (run / "result.json").write_text(
                json.dumps({"status": "UNSOLVED"}), encoding="utf-8"
            )
            (run / "not_allowlisted.secret").write_text("no", encoding="utf-8")
            workspace = root / "meta" / "workspace"
            manifest = prepare_token_meta_workspace(
                workspace=workspace,
                h0_run_dirs=[run],
                current_meta_skill="Analyze token waste.",
            )
            evidence = workspace / "evidence" / "run_01_run"
            self.assertTrue((evidence / "result.json").is_file())
            self.assertFalse((evidence / "not_allowlisted.secret").exists())
            self.assertFalse(manifest["reference_proof_visible"])

    def test_small_model_workspace_excludes_other_objectives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            run.mkdir()
            (run / "result.json").write_text(
                json.dumps({"status": "SOLVED"}), encoding="utf-8"
            )
            workspace = root / "meta" / "workspace"
            manifest = prepare_meta_workspace(
                workspace=workspace,
                h0_run_dirs=[run],
                current_meta_skill="Improve small-model solve rate.",
                objective="small_model_solve_rate",
            )
            task = (workspace / "META_TASK.md").read_text(encoding="utf-8")
            self.assertEqual(manifest["objective"], "small_model_solve_rate")
            self.assertFalse(manifest["other_objective_visible"])
            self.assertIn("Do not optimize token cost", task)

    def test_prior_round_pack_contains_only_declared_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h0 = root / "h0"
            h0.mkdir()
            (h0 / "result.json").write_text("{}", encoding="utf-8")
            baseline = root / "baseline"
            baseline.mkdir()
            (baseline / "result.json").write_text("{}", encoding="utf-8")
            prior_run = root / "prior-run"
            prior_run.mkdir()
            (prior_run / "result.json").write_text("{}", encoding="utf-8")
            (prior_run / "not_allowlisted.txt").write_text(
                "hidden", encoding="utf-8"
            )
            prior_meta = root / "meta.json"
            meta = valid_output()
            meta["objective"] = "small_model_solve_rate"
            prior_meta.write_text(json.dumps(meta), encoding="utf-8")
            prior_summary = root / "summary.json"
            prior_summary.write_text(
                json.dumps({"conditions": {}}), encoding="utf-8"
            )
            workspace = root / "workspace"
            manifest = prepare_meta_workspace(
                workspace=workspace,
                h0_run_dirs=[h0],
                current_meta_skill="Revise student guidance.",
                objective="small_model_solve_rate",
                baseline_run_dirs=[baseline],
                prior_run_dirs=[prior_run],
                prior_meta_output_path=prior_meta,
                prior_summary_path=prior_summary,
            )
            copied = workspace / "previous_round" / "runs"
            copied_run = next(copied.iterdir())
            self.assertTrue((copied_run / "result.json").is_file())
            self.assertFalse((copied_run / "not_allowlisted.txt").exists())
            self.assertTrue(manifest["previous_round_visible"])
            self.assertTrue(manifest["small_model_baseline_visible"])
            self.assertIn(
                "materially changed",
                (workspace / "META_TASK.md").read_text(encoding="utf-8"),
            )

    def test_token_design_brief_is_copied_and_labeled_as_hypothesis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            run.mkdir()
            (run / "result.json").write_text("{}", encoding="utf-8")
            brief = root / "brief.md"
            brief.write_text("Try direct-first solving.\n", encoding="utf-8")
            workspace = root / "workspace"
            manifest = prepare_meta_workspace(
                workspace=workspace,
                h0_run_dirs=[run],
                current_meta_skill="Reduce token cost.",
                objective="token_cost",
                design_brief_path=brief,
            )
            self.assertEqual(
                (workspace / "DESIGN_BRIEF.md").read_text(encoding="utf-8"),
                "Try direct-first solving.\n",
            )
            self.assertTrue(manifest["design_brief_visible"])
            task = (workspace / "META_TASK.md").read_text(encoding="utf-8")
            self.assertIn("hypothesis menu", task)
            self.assertIn("input and output token changes separately", task)


if __name__ == "__main__":
    unittest.main()
