from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skillopt_verusage.codex_reoptimize import (
    _candidate_audit,
    _install_prompt_free_codex_ledger,
)


class CodexReoptimizeTest(unittest.TestCase):
    def test_optimizer_ledger_records_each_internal_attempt(self) -> None:
        from skillopt.model import codex_backend

        original_chat = codex_backend._chat_messages_impl
        original_exec = codex_backend._run_codex_exec
        calls = 0

        def fake_exec(**kwargs):
            nonlocal calls
            del kwargs
            calls += 1
            if calls == 1:
                raise RuntimeError("transient")
            return "done", {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "total_tokens": 12,
            }

        def fake_chat(model, messages, max_completion_tokens, retries, stage, **kwargs):
            del messages, max_completion_tokens, retries, stage, kwargs
            try:
                codex_backend._run_codex_exec(
                    model=model,
                    prompt="prompt",
                    attachments=[],
                    output_schema=None,
                    timeout=None,
                )
            except RuntimeError:
                pass
            return codex_backend._run_codex_exec(
                model=model,
                prompt="prompt",
                attachments=[],
                output_schema=None,
                timeout=None,
            )

        try:
            codex_backend._chat_messages_impl = fake_chat
            codex_backend._run_codex_exec = fake_exec
            with tempfile.TemporaryDirectory() as tmp:
                ledger = Path(tmp) / "optimizer.jsonl"
                _install_prompt_free_codex_ledger(ledger)
                codex_backend._chat_messages_impl(
                    "gpt-5.6-sol", [], 1, 3, "analyst"
                )
                rows = [
                    json.loads(line)
                    for line in ledger.read_text(encoding="utf-8").splitlines()
                ]
                attempts = [
                    row for row in rows if row["record_type"] == "optimizer_attempt"
                ]
                logical = [
                    row
                    for row in rows
                    if row["record_type"] == "optimizer_logical_call"
                ]
                self.assertEqual([row["status"] for row in attempts], ["error", "success"])
                self.assertEqual(logical[0]["attempts"], 2)
        finally:
            codex_backend._chat_messages_impl = original_chat
            codex_backend._run_codex_exec = original_exec

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
