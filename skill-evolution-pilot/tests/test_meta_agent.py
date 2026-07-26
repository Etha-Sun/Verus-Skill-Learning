from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skill_evolution_pilot.meta_agent import (
    _outside_workspace_commands,
    prepare_token_meta_workspace,
    token_output_schema,
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


if __name__ == "__main__":
    unittest.main()
