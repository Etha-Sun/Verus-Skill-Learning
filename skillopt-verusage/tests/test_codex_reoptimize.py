from __future__ import annotations

import unittest

from skillopt_verusage.codex_reoptimize import _candidate_audit


class CodexReoptimizeTest(unittest.TestCase):
    def test_candidate_audit_accepts_compact_applied_update(self) -> None:
        errors = _candidate_audit(
            "# Seed\n",
            "# Seed\n\nPrefer the smallest proof repair supported by repeated evidence.\n",
            {
                "edits": [
                    {
                        "op": "append",
                        "content": "Prefer the smallest proof repair supported by repeated evidence.",
                    }
                ]
            },
            [{"status": "applied_append"}],
        )
        self.assertEqual(errors, [])

    def test_candidate_audit_rejects_formula_and_unapplied_edit(self) -> None:
        errors = _candidate_audit(
            "# Seed\n",
            "# Seed\n\nUse assert(x ==> y).\n",
            {"edits": [{"op": "append", "content": "Use assert(x ==> y)."}]},
            [{"status": "skipped_unknown_op"}],
        )
        self.assertTrue(any("concrete code/formula" in error for error in errors))
        self.assertTrue(any("were not applied" in error for error in errors))

    def test_candidate_audit_rejects_task_id_and_trusted_context_ban(self) -> None:
        content = (
            "Existing trusted declarations must not be used for "
            "e66407e3b527e0337808."
        )
        errors = _candidate_audit(
            "# Seed\n",
            "# Seed\n\n" + content + "\n",
            {"edits": [{"op": "append", "content": content}]},
            [{"status": "applied_append"}],
        )
        self.assertIn("candidate contains a task-like identifier", errors)
        self.assertIn("selected edits forbid use of frozen trusted context", errors)


if __name__ == "__main__":
    unittest.main()
