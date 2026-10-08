"""Synthetic-only regression coverage for the one explicitly authorized repair."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from skillopt_verusage.augmentation_campaign import (
    APPROVED_TRANSPORT_REQUEST, CARD_SYSTEM, DEFERRED_SOURCES, EXECUTION_REVIEW,
    Campaign, audit_transport_repair,
)
from skillopt_verusage.budget_guard import estimate_deepseek_cost
from skillopt_verusage.codex_deepseek_bridge import _sha256_json
from skillopt_verusage.guarded_deepseek import write_json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_records(parent):
    return [json.loads(line) for line in (parent / "provider_calls.jsonl").read_text().splitlines()]


def write_records(parent, records):
    (parent / "provider_calls.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records))


def request_upper(payload):
    return estimate_deepseek_cost({"prompt_cache_miss_tokens": len(json.dumps(payload, ensure_ascii=False).encode()) + 8192,
                                  "completion_tokens": 8192}, "deepseek-v4-pro", price_band="peak")


def fixture(base):
    approved = base / "approved"
    parent = approved / "parent"
    source = approved / "original"
    source.mkdir(parents=True)
    (source / "bridge_calls.jsonl").write_text('{"synthetic_source_ledger": true}\n')
    config = {"repo": str(base / "repository"), "source_root": str(source),
              "run_root": str(approved / "recovery"), "reused_hint_root": str(parent),
              "reviewed_progress_root": str(approved / "reviewed"),
              "checkpoint_policy": "rule_based_v1", "execution_review": EXECUTION_REVIEW,
              "deferred_sources": copy.deepcopy(DEFERRED_SOURCES)}
    parent_config = {key: value for key, value in config.items() if key != "reused_hint_root"}
    parent_config["run_root"] = str(parent)
    write_json(parent / "config.json", parent_config)
    progress = {"phase": "stopped", "error_type": "IncompleteRead", "error": "lost teacher response",
                "hint_completed": 9, "hint_rejected": 0}
    write_json(parent / "progress.json", progress)
    write_json(parent / "smoke_plan.json", {"source_tasks": ["one", "two"]})
    for ident in ("one", "two", "three"):
        for cp in ("cp1", "cp2", "cp3"):
            write_json(parent / "augmentation" / ident / cp / "result.json",
                       {"id": ident, "hard": 1, "fidelity": "V2_TRACE", "safety_passed": True,
                        "actor_model": "deepseek-v4-pro", "actor_reasoning_effort": "max",
                        "usage": {"unknown_cost_requests": 0}})
            write_json(parent / "augmentation" / ident / cp / "copy_marker.json", {"ident": ident, "cp": cp})
            write_json(parent / "hints" / ident / cp / "hint.json", {"hint_text": "synthetic accepted hint"})
    evidence = {"card_banks": {}, "proposals": {}}
    for condition in ("original_only", "augmented"):
        bank = parent / "banks" / (condition + "_smoke")
        write_json(bank / "cards.json", {"schema_version": "stage-card-bank-v1", "cards": []})
        write_json(bank / "proposals" / "batch-000.json", {"trace_analyses": [], "cards": []})
        write_json(bank / "update.json", {"system_sha256": hashlib.sha256(CARD_SYSTEM.encode()).hexdigest()})
        write_json(bank / "provenance.json", {})
        evidence["card_banks"][condition] = digest(bank / "cards.json")
        evidence["proposals"][condition] = digest(bank / "proposals" / "batch-000.json")
    write_json(parent / "smoke_evidence.json", evidence)
    write_json(parent / "smoke_review.json", {"accepted": True, "observations": "synthetic accepted review",
                                              "evidence_sha256": _sha256_json(evidence)})
    task = "hint--missing--cp1"
    payload = {"model": "deepseek-v4-pro", "instructions": "synthetic teacher",
               "input": [{"role": "user", "content": [{"type": "input_text", "text": "synthetic evidence"}]}],
               "max_output_tokens": 8192}
    request_digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
    request = parent / "calls" / "teacher" / task / request_digest / "request.json"
    write_json(request, payload)
    write_json(request.parent / "error.json", {"type": "IncompleteRead"})
    write_json(request.parent / "started.json",
               {"request_sha256": request_digest})
    unknown = {"request_id": APPROVED_TRANSPORT_REQUEST, "model": "deepseek-v4-pro", "task_id": task,
               "attempts": [{"estimated_cost_usd": None, "usage": None, "max_tokens": 8192,
                             "error": "IncompleteRead: synthetic interrupted response"}]}
    records = [{"request_id": "known-request", "attempts": [{"estimated_cost_usd": .5, "usage": {"prompt_tokens": 10}}]},
               unknown]
    write_records(parent, records)
    inventory = {"ledger_sha256": digest(parent / "provider_calls.jsonl"), "progress": progress,
                 "unknown_records": [unknown],
                 "result_hashes": {str(p.relative_to(parent)): digest(p) for p in parent.glob("augmentation/*/*/result.json")},
                 "hint_hashes": {str(p.relative_to(parent)): digest(p) for p in parent.glob("hints/*/*/hint.json")}}
    write_json(parent / "halt_inventory.json", inventory)
    review = {"replacement_authorized": True, "request_id": APPROVED_TRANSPORT_REQUEST, "task_id": task,
              "ledger_sha256": digest(parent / "provider_calls.jsonl"),
              "inventory_sha256": digest(parent / "halt_inventory.json"),
              "request_relative_path": str(request.relative_to(parent)), "request_sha256": digest(request),
              "unknown_expense_upper_usd": request_upper(payload)}
    write_json(parent / "transport_repair_review.json", review)
    return approved, parent, config


def rebind_ledger(parent):
    """Refresh bindings so negative tests exercise the selected contract, not stale hashes."""
    inventory = json.loads((parent / "halt_inventory.json").read_text())
    inventory["ledger_sha256"] = digest(parent / "provider_calls.jsonl")
    inventory["unknown_records"] = [row for row in read_records(parent)
                                    if any(a.get("estimated_cost_usd") is None for a in row.get("attempts", []))]
    write_json(parent / "halt_inventory.json", inventory)
    review = json.loads((parent / "transport_repair_review.json").read_text())
    review["ledger_sha256"] = inventory["ledger_sha256"]
    review["inventory_sha256"] = digest(parent / "halt_inventory.json")
    write_json(parent / "transport_repair_review.json", review)


class TransportRecoveryTests(unittest.TestCase):
    def test_exact_approved_request_and_constructor_preserve_all_actors_and_banks(self):
        with tempfile.TemporaryDirectory() as directory:
            approved, parent, config = fixture(Path(directory))
            ledger_before = (parent / "provider_calls.jsonl").read_bytes()
            source_ledger = Path(config["source_root"]) / "bridge_calls.jsonl"
            source_before = source_ledger.read_bytes()
            receipt = audit_transport_repair(parent, read_records(parent))
            self.assertEqual(receipt["request_id"], APPROVED_TRANSPORT_REQUEST)
            self.assertGreater(receipt["unknown_expense_upper_usd"], 0)
            self.assertLessEqual(receipt["unknown_expense_upper_usd"], .15)
            with patch.dict(os.environ, {"VERUS_SKILL_RUN_ROOT": str(approved)}):
                campaign = Campaign(config)
            self.assertEqual(len(list(campaign.root.glob("augmentation/*/*/result.json"))), 9)
            for pattern in ["augmentation/*/*/result.json", "augmentation/*/*/copy_marker.json", "banks/*_smoke/cards.json",
                            "banks/*_smoke/proposals/batch-000.json"]:
                for path in parent.glob(pattern):
                    self.assertEqual(path.read_bytes(), (campaign.root / path.relative_to(parent)).read_bytes())
            self.assertEqual(campaign.reused_smoke_parent, parent)
            self.assertEqual(json.loads((campaign.root / "approved_unknown_expense.json").read_text()), receipt)
            self.assertEqual(ledger_before, (parent / "provider_calls.jsonl").read_bytes())
            self.assertEqual(source_before, source_ledger.read_bytes())

    def test_missing_review_blocks_constructor(self):
        with tempfile.TemporaryDirectory() as directory:
            approved, parent, config = fixture(Path(directory))
            (parent / "transport_repair_review.json").unlink()
            with patch.dict(os.environ, {"VERUS_SKILL_RUN_ROOT": str(approved)}), self.assertRaises(ValueError):
                Campaign(config)

    def test_wrong_review_id_hash_authority_or_upper_is_rejected(self):
        changes = {"request_id": "other-request", "ledger_sha256": "0" * 64,
                   "inventory_sha256": "0" * 64, "request_sha256": "0" * 64,
                   "replacement_authorized": False, "unknown_expense_upper_usd": 0}
        for key, value in changes.items():
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                _, parent, _ = fixture(Path(directory))
                review = json.loads((parent / "transport_repair_review.json").read_text())
                review[key] = value; write_json(parent / "transport_repair_review.json", review)
                with self.assertRaises(ValueError):
                    audit_transport_repair(parent, read_records(parent))

    def test_extra_unknown_or_wrong_bound_request_id_is_rejected(self):
        for extra in (False, True):
            with self.subTest(extra_unknown=extra), tempfile.TemporaryDirectory() as directory:
                _, parent, _ = fixture(Path(directory)); records = read_records(parent)
                if extra:
                    other = copy.deepcopy(records[-1]); other["request_id"] = "second-unknown"; records.append(other)
                else:
                    records[-1]["request_id"] = "wrong-request"
                write_records(parent, records); rebind_ledger(parent)
                with self.assertRaises(ValueError):
                    audit_transport_repair(parent, read_records(parent))

    def test_existing_actor_or_delivered_hint_cannot_be_replaced(self):
        for kind in ("actor", "hint"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                _, parent, _ = fixture(Path(directory))
                if kind == "actor":
                    (parent / "augmentation" / "missing" / "cp1").mkdir(parents=True)
                else:
                    write_json(parent / "hints" / "missing" / "cp1" / "hint.json", {"delivered": True})
                with self.assertRaisesRegex(ValueError, "missing teacher hint"):
                    audit_transport_repair(parent, read_records(parent))

    def test_same_payload_at_another_path_is_not_the_authorized_request(self):
        with tempfile.TemporaryDirectory() as directory:
            _, parent, _ = fixture(Path(directory))
            review = json.loads((parent / "transport_repair_review.json").read_text())
            original = parent / review["request_relative_path"]
            other = parent / "other" / "request.json"
            write_json(other, json.loads(original.read_text()))
            for name in ("started.json", "error.json"):
                write_json(other.parent / name, json.loads((original.parent / name).read_text()))
            review["request_relative_path"] = str(other.relative_to(parent))
            self.assertEqual(review["request_sha256"], digest(other))
            write_json(parent / "transport_repair_review.json", review)
            with self.assertRaisesRegex(ValueError, "payload contract changed"):
                audit_transport_repair(parent, read_records(parent))

    def test_inventory_or_completed_evidence_mutation_is_rejected(self):
        for kind in ("inventory", "result", "hint"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                _, parent, _ = fixture(Path(directory))
                if kind == "inventory":
                    write_json(parent / "halt_inventory.json", {})
                elif kind == "result":
                    write_json(parent / "augmentation" / "one" / "cp1" / "result.json", {"mutated": True})
                else:
                    write_json(parent / "hints" / "one" / "cp1" / "hint.json", {"mutated": True})
                with self.assertRaises(ValueError):
                    audit_transport_repair(parent, read_records(parent))

    def test_fully_rebound_upper_above_user_ceiling_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            _, parent, _ = fixture(Path(directory))
            review = json.loads((parent / "transport_repair_review.json").read_text())
            old_request = parent / review["request_relative_path"]
            payload = json.loads(old_request.read_text()); payload["instructions"] = "x" * 200000
            request_digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
            request = old_request.parent.parent / request_digest / "request.json"
            write_json(request, payload)
            write_json(request.parent / "error.json", {"type": "IncompleteRead"})
            write_json(request.parent / "started.json",
                       {"request_sha256": request_digest})
            review["request_relative_path"] = str(request.relative_to(parent))
            review["request_sha256"] = digest(request); review["unknown_expense_upper_usd"] = request_upper(payload)
            self.assertGreater(review["unknown_expense_upper_usd"], .15)
            write_json(parent / "transport_repair_review.json", review)
            with self.assertRaisesRegex(ValueError, "unknown expense upper"):
                audit_transport_repair(parent, read_records(parent))

    def test_known_costs_and_approved_historical_upper_remain_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            approved, parent, config = fixture(Path(directory))
            parent_before = (parent / "provider_calls.jsonl").read_bytes()
            source_ledger = Path(config["source_root"]) / "bridge_calls.jsonl"
            source_before = source_ledger.read_bytes()
            with patch.dict(os.environ, {"VERUS_SKILL_RUN_ROOT": str(approved)}):
                campaign = Campaign(config)
            write_records(campaign.root, [{"attempts": [{"estimated_cost_usd": .25, "usage": {"prompt_tokens": 5}}]}])
            campaign.check_costs()
            summary = json.loads((campaign.root / "cost_summary.json").read_text())
            upper = json.loads((parent / "transport_repair_review.json").read_text())["unknown_expense_upper_usd"]
            self.assertEqual(summary["estimated_new_cost_usd"], .25)
            self.assertEqual(summary["recovery_parent_physical_cost_usd"], .5)
            self.assertEqual(summary["estimated_campaign_cost_including_parent_usd"], .75)
            self.assertEqual(summary["approved_historical_unknown_expense_upper_usd"], upper)
            self.assertEqual(summary["known_estimate_plus_historical_unknown_upper_usd"], .75 + upper)
            self.assertEqual(len(summary["approved_historical_unknown_requests"]), 1)
            self.assertEqual(summary["unknown_cost_requests"], 0)
            self.assertFalse(summary["invoice_final"])
            self.assertEqual(parent_before, (parent / "provider_calls.jsonl").read_bytes())
            self.assertEqual(source_before, source_ledger.read_bytes())

    def test_new_unknown_cost_is_recorded_without_expense_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            approved, _, config = fixture(Path(directory))
            with patch.dict(os.environ, {"VERUS_SKILL_RUN_ROOT": str(approved)}):
                campaign = Campaign(config)
            write_records(campaign.root, [{"attempts": [{"estimated_cost_usd": None, "usage": None}]}])
            campaign.check_costs()
            self.assertEqual(json.loads((campaign.root / "cost_summary.json").read_text())["unknown_cost_requests"], 1)


if __name__ == "__main__":
    unittest.main()
