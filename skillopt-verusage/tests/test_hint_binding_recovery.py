"""Synthetic regressions for one metered, rejected checkpoint-binding hint."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from skillopt_verusage.augmentation_campaign import (
    BINDING_REPAIR_KEY, BINDING_REPAIR_REQUEST, Campaign, audit_hint_binding_repair,
)
from skillopt_verusage.guarded_deepseek import write_json
from test_transport_recovery import digest, fixture, read_records, write_records


def binding_fixture(base):
    approved, parent, config = fixture(base)
    (parent / "transport_repair_review.json").unlink()
    (parent / "halt_inventory.json").unlink()
    progress = {"phase": "stopped", "error_type": "AssertionError",
                "error": "Hint checkpoint mismatch", "hint_completed": 9, "hint_rejected": 0}
    write_json(parent / "progress.json", progress)
    ident, cp = BINDING_REPAIR_KEY.split("/")
    task = "hint--" + ident + "--" + cp
    expected, returned = "a" * 64, "b" * 64
    contract = {"source_task": ident, "checkpoint_sha256": expected,
                "evidence_ids": ["original_task", "final_validation"]}
    packet = {"contract": contract, "checkpoint": {"checkpoint_id": cp,
              "checkpoint_sha256": expected}, "complete_original": {"synthetic": True}}
    hint_directory = parent / "hints" / BINDING_REPAIR_KEY
    write_json(hint_directory / "contract.json", contract)
    write_json(hint_directory / "teacher_packet.json", packet)
    payload = {"model": "deepseek-v4-pro", "instructions": "Return the exact supplied checkpoint hash.",
               "input": [{"role": "user", "content": [{"type": "input_text", "text": json.dumps(packet)}]}],
               "max_output_tokens": 8192}
    request_digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
    request = parent / "calls" / "teacher" / task / request_digest / "request.json"
    write_json(request, payload)
    write_json(request.parent / "started.json", {"request_sha256": request_digest})
    hint = {"schema_version": "hint-v1", "checkpoint_sha256": returned,
            "hint_text": "Check whether the current loop invariant preserves the required relation.",
            "evidence_refs": [{"source_id": "original_task", "observation": "The loop must preserve its relation."}],
            "relation_to_original": "later_verified_repair", "limitations": ["Synthetic evidence only."]}
    text = json.dumps(hint)
    usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    record = {"request_id": BINDING_REPAIR_REQUEST, "task_id": task, "model": "deepseek-v4-pro",
              "attempts": [{"estimated_cost_usd": 0.067200804, "usage": usage,
                            "max_tokens": 8192, "error": None, "finish_reason": "completed"}]}
    write_json(request.parent / "validated.json", {"text": text, "usage": usage, "record": record})
    write_json(request.parent / "response.raw", {"status": "completed", "model": "deepseek-v4-pro",
               "output": [{"type": "message", "role": "assistant",
                           "content": [{"type": "output_text", "text": text}]}], "usage": usage})
    write_records(parent, [read_records(parent)[0], record])
    review = {"repair_authorized": True, "rejected_hint_key": BINDING_REPAIR_KEY,
              "request_id": BINDING_REPAIR_REQUEST, "task_id": task,
              "request_relative_path": str(request.relative_to(parent)),
              "expected_checkpoint_sha256": expected, "returned_checkpoint_sha256": returned}
    write_json(parent / "hint_binding_repair_review.json", review)
    rebind(parent)
    return approved, parent, config


def rebind(parent):
    """Refresh hashes after synthetic changes to test semantic checks independently."""
    inventory = {"progress": json.loads((parent / "progress.json").read_text()),
                 "ledger_sha256": digest(parent / "provider_calls.jsonl"),
                 "result_hashes": {str(p.relative_to(parent)): digest(p)
                                   for p in parent.glob("augmentation/*/*/result.json")},
                 "hint_hashes": {str(p.relative_to(parent)): digest(p)
                                 for p in parent.glob("hints/*/*/hint.json")}}
    write_json(parent / "hint_binding_inventory.json", inventory)
    review_path = parent / "hint_binding_repair_review.json"
    review = json.loads(review_path.read_text())
    call = (parent / review["request_relative_path"]).parent
    hints = parent / "hints" / BINDING_REPAIR_KEY
    review.update(ledger_sha256=inventory["ledger_sha256"],
                  inventory_sha256=digest(parent / "hint_binding_inventory.json"),
                  request_sha256=digest(call / "request.json"),
                  validated_sha256=digest(call / "validated.json"),
                  response_sha256=digest(call / "response.raw"),
                  contract_sha256=digest(hints / "contract.json"),
                  teacher_packet_sha256=digest(hints / "teacher_packet.json"))
    write_json(review_path, review)


def call_directory(parent):
    review = json.loads((parent / "hint_binding_repair_review.json").read_text())
    return (parent / review["request_relative_path"]).parent


def test_exact_binding_recovery_preserves_known_results_and_rejects_failed_hint(tmp_path, monkeypatch):
    approved, parent, config = binding_fixture(tmp_path)
    source_ledger = Path(config["source_root"]) / "bridge_calls.jsonl"
    preserved = [parent / "provider_calls.jsonl", source_ledger,
                 parent / "hints" / BINDING_REPAIR_KEY / "contract.json",
                 parent / "hints" / BINDING_REPAIR_KEY / "teacher_packet.json",
                 call_directory(parent) / "validated.json", call_directory(parent) / "response.raw"]
    before = {p: p.read_bytes() for p in preserved}
    audit = audit_hint_binding_repair(parent, read_records(parent))
    assert audit["request_id"] == BINDING_REPAIR_REQUEST
    assert audit["rejected_hint_key"] == BINDING_REPAIR_KEY
    assert audit["rejected_response_preserved"] is True
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    campaign = Campaign(config)
    assert campaign.rejected_hint_key == BINDING_REPAIR_KEY
    assert len(list(campaign.root.glob("augmentation/*/*/result.json"))) == 9
    assert len(list(campaign.root.glob("banks/*_smoke/cards.json"))) == 2
    assert not (campaign.root / "augmentation" / BINDING_REPAIR_KEY).exists()
    assert not (campaign.root / "hints" / BINDING_REPAIR_KEY / "hint.json").exists()
    assert not (campaign.root / "approved_unknown_expense.json").exists()
    for pattern in ("augmentation/*/*/result.json", "augmentation/*/*/copy_marker.json",
                    "banks/*_smoke/cards.json", "banks/*_smoke/proposals/batch-000.json"):
        for path in parent.glob(pattern):
            assert path.read_bytes() == (campaign.root / path.relative_to(parent)).read_bytes()
    write_records(campaign.root, [{"attempts": [{"estimated_cost_usd": .25, "usage": {"prompt_tokens": 5}}]}])
    campaign.check_costs()
    costs = json.loads((campaign.root / "cost_summary.json").read_text())
    assert costs["estimated_campaign_cost_including_parent_usd"] == pytest.approx(.817200804)
    assert costs["unknown_cost_requests"] == 0
    for path, raw in before.items():
        assert path.read_bytes() == raw
    write_records(campaign.root, [{"attempts": [{"estimated_cost_usd": None, "usage": None}]}])
    campaign.check_costs()
    assert json.loads((campaign.root/"cost_summary.json").read_text())["unknown_cost_requests"] == 1


@pytest.mark.parametrize("field,value", [
    ("repair_authorized", False), ("rejected_hint_key", "another/cp3"),
    ("request_id", "another"), ("task_id", "hint--another--cp3"),
    ("ledger_sha256", "bad"), ("inventory_sha256", "bad"),
    ("request_sha256", "bad"), ("validated_sha256", "bad"), ("response_sha256", "bad"),
    ("contract_sha256", "bad"), ("teacher_packet_sha256", "bad"),
    ("expected_checkpoint_sha256", "c" * 64), ("returned_checkpoint_sha256", "c" * 64),
    ("request_relative_path", "../outside/request.json"),
])
def test_receipt_cannot_expand_or_rebind_authority(tmp_path, field, value):
    _, parent, _ = binding_fixture(tmp_path)
    path = parent / "hint_binding_repair_review.json"
    review = json.loads(path.read_text()); review[field] = value; write_json(path, review)
    with pytest.raises(ValueError):
        audit_hint_binding_repair(parent, read_records(parent))


@pytest.mark.parametrize("kind", ["raw", "validated", "contract", "packet", "inventory", "result", "hint", "started", "request"])
def test_mutated_preserved_evidence_is_rejected(tmp_path, kind):
    _, parent, _ = binding_fixture(tmp_path)
    call = call_directory(parent)
    targets = {"raw": call / "response.raw", "validated": call / "validated.json",
               "contract": parent / "hints" / BINDING_REPAIR_KEY / "contract.json",
               "packet": parent / "hints" / BINDING_REPAIR_KEY / "teacher_packet.json",
               "inventory": parent / "hint_binding_inventory.json",
               "result": parent / "augmentation/one/cp1/result.json",
               "hint": parent / "hints/one/cp1/hint.json",
               "started": call / "started.json", "request": call / "request.json"}
    write_json(targets[kind], {"changed": True})
    with pytest.raises(ValueError):
        audit_hint_binding_repair(parent, read_records(parent))


@pytest.mark.parametrize("kind", ["error", "error_type", "phase", "completed_count", "unknown", "wrong_request", "wrong_task", "duplicate_request", "validated_record", "equal_hash", "text_hash"])
def test_fully_rebound_evidence_still_requires_exact_known_binding_failure(tmp_path, kind):
    _, parent, _ = binding_fixture(tmp_path)
    if kind in ("error", "error_type", "phase", "completed_count"):
        path = parent / "progress.json"; value = json.loads(path.read_text())
        key, changed = {"error": ("error", "Other assertion"), "error_type": ("error_type", "ValueError"),
                        "phase": ("phase", "hint_augmentation"), "completed_count": ("hint_completed", 8)}[kind]
        value[key] = changed; write_json(path, value)
    elif kind in ("unknown", "wrong_request", "wrong_task", "duplicate_request"):
        records = read_records(parent)
        if kind == "unknown": records[0]["attempts"][0]["estimated_cost_usd"] = None
        elif kind == "wrong_request": records[-1]["request_id"] = "another"
        elif kind == "wrong_task": records[-1]["task_id"] = "hint--another--cp3"
        else: records.append(copy.deepcopy(records[-1]))
        write_records(parent, records)
    else:
        path = call_directory(parent) / "validated.json"; value = json.loads(path.read_text())
        if kind == "validated_record": value["record"]["attempts"][0]["estimated_cost_usd"] = 0
        else:
            hint = json.loads(value["text"])
            hint["checkpoint_sha256"] = "a" * 64 if kind == "equal_hash" else "c" * 64
            value["text"] = json.dumps(hint)
        write_json(path, value)
    rebind(parent)
    with pytest.raises(ValueError):
        audit_hint_binding_repair(parent, read_records(parent))


@pytest.mark.parametrize("kind", ["hint", "screen", "actor"])
def test_delivered_hint_or_existing_actor_is_never_replaced(tmp_path, kind):
    _, parent, _ = binding_fixture(tmp_path)
    if kind == "actor": (parent / "augmentation" / BINDING_REPAIR_KEY).mkdir(parents=True)
    else: write_json(parent / "hints" / BINDING_REPAIR_KEY / (kind + ".json"), {"delivered": True})
    rebind(parent)
    with pytest.raises(ValueError):
        audit_hint_binding_repair(parent, read_records(parent))


@pytest.mark.parametrize("field,value", [("model", "deepseek-v4-flash"), ("max_output_tokens", 4096)])
def test_rebound_payload_at_correct_digest_path_still_requires_pro_8192(tmp_path, field, value):
    _, parent, _ = binding_fixture(tmp_path)
    old_call = call_directory(parent)
    payload = json.loads((old_call / "request.json").read_text()); payload[field] = value
    request_digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
    request = old_call.parent / request_digest / "request.json"
    write_json(request, payload)
    write_json(request.parent / "started.json", {"request_sha256": request_digest})
    for name in ("validated.json", "response.raw"):
        write_json(request.parent / name, json.loads((old_call / name).read_text()))
    review_path = parent / "hint_binding_repair_review.json"
    review = json.loads(review_path.read_text()); review["request_relative_path"] = str(request.relative_to(parent))
    write_json(review_path, review); rebind(parent)
    with pytest.raises(ValueError):
        audit_hint_binding_repair(parent, read_records(parent))


@pytest.mark.parametrize("field,value", [("model", "deepseek-v4-flash"),
    ("max_tokens", 4096), ("finish_reason", "length"), ("usage", None)])
def test_rebound_matching_record_still_requires_completed_metered_teacher(tmp_path, field, value):
    _, parent, _ = binding_fixture(tmp_path)
    records = read_records(parent)
    if field == "model": records[-1][field] = value
    else: records[-1]["attempts"][0][field] = value
    write_records(parent, records)
    path = call_directory(parent) / "validated.json"; stored = json.loads(path.read_text())
    stored["record"] = records[-1]; stored["usage"] = records[-1]["attempts"][0]["usage"]
    write_json(path, stored); rebind(parent)
    with pytest.raises(ValueError):
        audit_hint_binding_repair(parent, read_records(parent))


def test_missing_binding_review_does_not_authorize_constructor(tmp_path, monkeypatch):
    approved, parent, config = binding_fixture(tmp_path)
    (parent / "hint_binding_repair_review.json").unlink()
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    with pytest.raises(ValueError):
        Campaign(config)


def test_other_partial_actor_cannot_be_omitted(tmp_path, monkeypatch):
    approved, parent, config = binding_fixture(tmp_path)
    write_json(parent / "augmentation/another/cp1/raw.json", {"partial": True})
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    with pytest.raises(ValueError, match="complete reviewed continuation set"):
        Campaign(config)
