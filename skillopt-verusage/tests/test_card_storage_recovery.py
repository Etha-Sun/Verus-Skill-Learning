"""Storage recovery must keep incomplete dispatches unknown and paid replies owned."""
import copy
import hashlib
import json
import shutil

import pytest

from skillopt_verusage import augmentation_campaign as campaign_module
from skillopt_verusage.budget_guard import estimate_deepseek_cost
from skillopt_verusage.campaign_evidence import expand_strings, shared_strings
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json
from test_chained_card_content_recovery import chained_fixture
from test_transport_recovery import digest, read_records, write_records


KNOWN_MISSING_ID = "be5eb5af99914cfbbee2512973cd126a"
AUTHORITY = "现在有空间了，请你继续跑"
PATTERNS = ("augmentation/*/*/result.json", "hints/*/*/hint.json", "artifacts/native/**/*",
            "calls/native/**/*", "calls/native_finalization/**/*", "calls/original_only/**/*",
            "calls/augmented/**/*", "banks/original_only_remaining/proposals/*.json",
            "banks/augmented_remaining/proposals/*.json", "recovered_card_requests.json",
            "banks/original_only/**/*")


def complete_cache(parent, template, label, n, *, complete=True):
    payload = json.loads((template / "request.json").read_text())
    packet = expand_strings(json.loads(payload["input"][0]["content"][0]["text"]))
    for j, group in enumerate(packet["task_groups"]):
        task = f"task-{2*n+j:02d}"; tid = f"task:{task}:original"
        ids = [tid] if label == "original_only" else [tid, *[f"task:{task}:cp{k}" for k in range(1, 4)]]
        group.update(source_task=task, trace_ids=ids,
                     evidence_ids=[t + suffix for t in ids for suffix in ("/event:1", "/final_validation")])
        group["original"]["trace_id"] = tid
        group["forks"] = [] if label == "original_only" else [{"trace_id": t} for t in ids[1:]]
    packet["contract"].update(logical_traces=2 if label == "original_only" else 8,
                             source_weights={g["source_task"]: 1 for g in packet["task_groups"]})
    payload["input"][0]["content"][0]["text"] = json.dumps(shared_strings(packet, short_keys=True), ensure_ascii=False, separators=(",", ":"))
    local_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
    directory = parent / "calls" / label / f"card-batch-{n:03d}" / local_hash
    record = copy.deepcopy(json.loads((template / "validated.json").read_text())["record"])
    record.update(request_id=KNOWN_MISSING_ID if label == "augmented" and n == 4 else f"storage-{label}-{n}",
                  task_id=f"card-batch-{n:03d}")
    write_json(directory / "request.json", payload)
    write_json(directory / "started.json", {"request_sha256": local_hash})
    write_json(directory / "context_admission.json", {"fixture": True})
    if complete:
        response = {"trace_analyses": [{"trace_id": tid, "observation": "Synthetic full trace."}
                    for g in packet["task_groups"] for tid in g["trace_ids"]], "cards": []}
        text = json.dumps(response)
        raw = json.loads((template / "response.raw").read_text())
        raw["output"][0]["content"][0]["text"] = text
        write_json(directory / "response.raw", raw)
        write_json(directory / "validated.json", {"text": text, "usage": record["attempts"][0]["usage"], "record": record})
        write_json(parent / "banks" / (label + "_remaining") / "proposals" / f"batch-{n:03d}.json", response)
    return directory, record


def rebind(parent):
    incident_path = parent / "storage_incident.json"
    incident = json.loads(incident_path.read_text())
    incident.update(provider_ledger_sha256=digest(parent / "provider_calls.jsonl"),
                    progress_sha256=digest(parent / "progress.json"),
                    campaign_log_sha256=digest(parent / "campaign.log"),
                    preserved_hashes={str(p.relative_to(parent)): digest(p)
                        for pattern in PATTERNS for p in parent.glob(pattern) if p.is_file()})
    write_json(incident_path, incident)
    path = parent / "storage_repair_review.json"; review = json.loads(path.read_text())
    from skillopt_verusage.card_storage_recovery import STORAGE_PATTERNS
    review.update(incident_sha256=digest(incident_path),
                  ledger_sha256=digest(parent / "provider_calls.jsonl"),
                  progress_sha256=digest(parent / "progress.json"),
                  log_sha256=digest(parent / "campaign.log"),
                  preserved_hashes={str(p.relative_to(parent)): digest(p)
                      for pattern in STORAGE_PATTERNS for p in parent.glob(pattern) if p.is_file()})
    write_json(path, review)


def storage_fixture(base, monkeypatch):
    approved, ancestor, _, _, config = chained_fixture(base)
    parent = approved / "storage-parent"
    shutil.copytree(ancestor, parent)
    shutil.rmtree(parent / "calls/original_only/card-batch-016")
    write_json(parent / "recovered_card_requests.json", campaign_module.audit_card_stage_repair(ancestor, read_records(ancestor)))
    parent_config = json.loads((parent / "config.json").read_text())
    parent_config.update(run_root=str(parent), reused_hint_root=str(ancestor)); write_json(parent / "config.json", parent_config)
    config["reused_hint_root"] = str(parent)
    template = next(ancestor.glob("calls/original_only/card-batch-000/*/request.json")).parent
    rows = [complete_cache(parent, template, "original_only", n)[1] for n in (16, 17)]
    for n in range(6):
        directory, record = complete_cache(parent, template, "augmented", n, complete=n < 4)
        if n != 5: rows.append(record)
        else:
            unknown_hash = directory.name
            unknown_bytes = len(json.dumps(json.loads((directory / "request.json").read_text()), ensure_ascii=False).encode())
    write_records(parent, rows)
    write_json(parent / "progress.json", {"phase": "card_extraction", "hint_completed": 114, "hint_rejected": 0})
    (parent / "campaign.log").write_text("OSError: [Errno 28] No space left on device\n")
    write_json(parent / "banks/original_only/cards.json", {"schema_version": "stage-card-bank-v1", "cards": []})
    incident = {"schema_version": "storage-incident-v1", "phase": "stopped_storage_failure_requires_new_fee_authority",
        "process_exit_code": 1, "paid_process_running": False, "progress_file_is_stale": True,
        "original_progress_preserved": True, "completed_forks": 114, "complete_original_card_batches": 19,
        "complete_augmented_remaining_batches": 4, "known_new_requests": 7,
        "frozen_artifacts_created": False, "validation_started": False, "sealed_test_accessed": False,
        "known_new_cost_usd": sum(a["estimated_cost_usd"] for r in rows for a in r["attempts"]),
        "known_missing_response": {"task": "card-batch-004", "request_id": KNOWN_MISSING_ID,
            "estimated_cost_usd": rows[-1]["attempts"][0]["estimated_cost_usd"], "response_saved": False,
            "must_not_replay_missing_response": True},
        "new_unresolved_cost": {"task": "card-batch-005", "local_request_sha256": unknown_hash,
            "server_or_internal_request_id": None, "dispatch_status": "unresolved_possibly_dispatched",
            "canonical_http_bytes": unknown_bytes, "conservative_byte_framing_reserve": 8192, "output_cap": 16384,
            "peak_uncached_expense_upper_usd": estimate_deepseek_cost({"prompt_cache_miss_tokens": unknown_bytes + 8192,
                "completion_tokens": 16384}, "deepseek-v4-pro", price_band="peak"), "historical_request": False,
            "user_approved": False, "must_not_assume_zero_or_unsent": True}}
    write_json(parent / "storage_incident.json", incident)
    write_json(parent / "storage_repair_review.json", {"repair_authorized": True,
        "classification": "full_card_storage_repair", "user_authorization": AUTHORITY})
    rebind(parent)
    # Real requests remain exactly scoped; the synthetic payload has a different hash.
    from skillopt_verusage import card_storage_recovery
    monkeypatch.setattr(card_storage_recovery, "UNKNOWN_LOCAL_HASH", unknown_hash)
    return approved, parent, ancestor, config


def audit(parent):
    return campaign_module.audit_card_storage_repair(parent, read_records(parent))


def test_storage_recovery_preserves_unknown_and_only_replays_saved_paid_replies(tmp_path, monkeypatch):
    _, parent, ancestor, _ = storage_fixture(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for root in (parent, ancestor) for p in root.rglob("*") if p.is_file()}
    receipt = audit(parent)
    assert len(receipt["replay_requests"]) == 22
    assert sum(r["label"] == "original_only" for r in receipt["replay_requests"]) == 18
    assert sum(r["label"] == "augmented" for r in receipt["replay_requests"]) == 4
    assert all(r["name"] not in {"card-batch-004", "card-batch-005"} or r["label"] != "augmented"
               for r in receipt["replay_requests"])
    assert all(p.read_bytes() == value for p, value in before.items())


def test_storage_constructor_replays_all_22_exact_inputs_without_api_or_new_ledger(tmp_path, monkeypatch):
    approved, parent, _, config = storage_fixture(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in parent.rglob("*") if p.is_file()}
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    monkeypatch.setattr("skillopt_verusage.guarded_deepseek.forward_native_responses",
                        lambda *a, **k: pytest.fail("Storage cache replay must not call the API"))
    campaign = campaign_module.Campaign(config)
    receipt = json.loads((campaign.root / "recovered_card_requests.json").read_text())
    assert len(receipt["replay_requests"]) == 22
    assert len(list(campaign.root.glob("augmentation/*/*/result.json"))) == 114
    assert len(list(campaign.root.glob("calls/native/**/request.json"))) == 5
    assert len(list(campaign.root.glob("calls/native_finalization/**/request.json"))) == 1
    for entry in receipt["replay_requests"]:
        request = campaign.root / entry["request_relative_path"]
        payload = json.loads(request.read_text())
        client = GuardedDeepSeek(root=campaign.root / "calls" / entry["label"], api_key="fixture", guards=[],
                                ledger=campaign.root / "unused-ledger.jsonl")
        text, usage = client.call(system=payload["instructions"], user=payload["input"][0]["content"][0]["text"],
                                 name=entry["name"], cap=16384)
        stored = json.loads((request.parent / "validated.json").read_text())
        assert (text, usage) == (stored["text"], stored["usage"])
    for n in (4, 5):
        assert not (campaign.root / "calls/augmented" / f"card-batch-{n:03d}").exists()
    assert not (campaign.root / "unused-ledger.jsonl").exists()
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_missing_ledger_unknown_is_counted_once_and_current_uncertainty_is_record_only(tmp_path, monkeypatch):
    _, parent, _, _ = storage_fixture(tmp_path, monkeypatch)
    campaign = campaign_module.Campaign.__new__(campaign_module.Campaign)
    campaign.root = tmp_path / "cost-child"; campaign.root.mkdir()
    campaign.ledger = campaign.root / "provider_calls.jsonl"
    campaign.config = {"reused_hint_root": str(parent)}
    write_records(campaign.root, [{"request_id": "new-uncertain", "attempts": [{"estimated_cost_usd": None}]},
                                 {"request_id": "new-known", "attempts": [{"estimated_cost_usd": .125}]}])
    campaign.check_costs()
    summary = json.loads((campaign.root / "cost_summary.json").read_text())
    unknown = json.loads((parent / "storage_incident.json").read_text())["new_unresolved_cost"]
    assert summary["expense_policy"] == "record_only"
    assert summary["unknown_cost_requests"] == 1
    assert summary["total_unknown_requests_including_approved_history"] == 2
    assert summary["estimated_new_cost_usd"] == .125
    assert summary["recovery_parent_physical_cost_usd"] == pytest.approx(.81)
    assert summary["estimated_campaign_cost_including_parent_usd"] == pytest.approx(.935)
    assert len(summary["approved_historical_unknown_requests"]) == 1
    pending = summary["approved_historical_unknown_requests"][0]
    assert pending["request_id"] is None
    assert pending["fee_status"] == "unresolved_not_zero"
    assert pending["local_request_sha256"] == unknown["local_request_sha256"]
    assert summary["approved_historical_unknown_expense_upper_usd"] == unknown["peak_uncached_expense_upper_usd"]
    assert summary["known_estimate_plus_historical_unknown_upper_usd"] == pytest.approx(
        summary["estimated_campaign_cost_including_parent_usd"] + unknown["peak_uncached_expense_upper_usd"])
    campaign.check_costs()
    assert json.loads((campaign.root / "cost_summary.json").read_text()) == summary


@pytest.mark.parametrize("field,value", [("repair_authorized", False), ("classification", "other"),
    ("user_authorization", "space is free"), ("incident_sha256", "wrong"), ("ledger_sha256", "wrong"),
    ("progress_sha256", "wrong"), ("log_sha256", "wrong")])
def test_storage_repair_requires_exact_new_authority_and_bindings(tmp_path, monkeypatch, field, value):
    _, parent, _, _ = storage_fixture(tmp_path, monkeypatch)
    path = parent / "storage_repair_review.json"; j = json.loads(path.read_text()); j[field] = value; write_json(path, j)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("field,value", [("phase", "running"), ("process_exit_code", 0),
    ("paid_process_running", True), ("progress_file_is_stale", False), ("completed_forks", 113),
    ("known_new_requests", 6), ("complete_augmented_remaining_batches", 5)])
def test_storage_incident_cannot_reclassify_running_or_different_failure(tmp_path, monkeypatch, field, value):
    _, parent, _, _ = storage_fixture(tmp_path, monkeypatch)
    path = parent / "storage_incident.json"; j = json.loads(path.read_text()); j[field] = value; write_json(path, j); rebind(parent)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("kind", ["unsent", "zero", "known_unknown_id", "wrong_local_hash", "known004_id",
    "known004_missing_ledger", "unknown005_ledger", "duplicate", "unknown_current", "inherited_as_current",
    "inherited_changed", "current_raw_changed", "current_proposal_changed", "new_unknown_reply",
    "new_known_reply", "extra_request", "ancestor_authority", "native_learning", "known004_model",
    "known004_error", "known004_finish", "known004_cap", "frozen", "validation", "sealed"])
def test_rebound_storage_receipt_cannot_broaden_paid_ownership_or_unknown_scope(tmp_path, monkeypatch, kind):
    _, parent, ancestor, _ = storage_fixture(tmp_path, monkeypatch)
    path = parent / "storage_incident.json"; j = json.loads(path.read_text())
    if kind in {"unsent", "zero", "known_unknown_id", "wrong_local_hash", "known004_id"}:
        if kind == "known004_id": j["known_missing_response"]["request_id"] = "wrong"
        else:
            field, value = {"unsent": ("dispatch_status", "unsent"), "zero": ("peak_uncached_expense_upper_usd", 0),
                "known_unknown_id": ("server_or_internal_request_id", "invented"),
                "wrong_local_hash": ("local_request_sha256", "wrong")}[kind]
            j["new_unresolved_cost"][field] = value
        write_json(path, j)
    elif kind in {"known004_missing_ledger", "unknown005_ledger", "duplicate", "unknown_current", "inherited_as_current"}:
        rows = read_records(parent)
        if kind == "known004_missing_ledger": rows.pop()
        elif kind == "unknown005_ledger":
            r = copy.deepcopy(rows[-1]); r.update(request_id="invented", task_id="card-batch-005"); rows.append(r)
        elif kind == "duplicate": rows[0] = copy.deepcopy(rows[1])
        elif kind == "unknown_current": rows[0]["attempts"][0]["estimated_cost_usd"] = None
        else: rows[0] = json.loads(next(parent.glob("calls/original_only/card-batch-000/*/validated.json")).read_text())["record"]
        write_records(parent, rows)
    elif kind in {"inherited_changed", "current_raw_changed"}:
        pattern = "calls/original_only/card-batch-000/*/response.raw" if kind == "inherited_changed" else "calls/augmented/card-batch-000/*/response.raw"
        next(parent.glob(pattern)).write_bytes(b"changed")
    elif kind == "current_proposal_changed": write_json(parent / "banks/augmented_remaining/proposals/batch-000.json", {})
    elif kind in {"new_unknown_reply", "new_known_reply"}:
        n = 5 if kind == "new_unknown_reply" else 4
        write_json(next(parent.glob(f"calls/augmented/card-batch-{n:03d}/*/request.json")).parent / "response.raw", {})
    elif kind == "extra_request": write_json(parent / "calls/augmented/card-batch-006/extra/request.json", {})
    elif kind == "ancestor_authority":
        p = ancestor / "card_stage_repair_review.json"; r = json.loads(p.read_text()); r["repair_authorized"] = False; write_json(p, r)
    elif kind == "native_learning": write_json(parent / "artifacts/native/learning.json", {"source_count": 37, "audit": []})
    elif kind.startswith("known004_"):
        rows = read_records(parent); record = rows[-1]
        if kind == "known004_model": record["model"] = "deepseek-v4-flash"
        else:
            field, value = {"known004_error": ("error", "failed"), "known004_finish": ("finish_reason", "incomplete"),
                            "known004_cap": ("max_tokens", 8192)}[kind]
            record["attempts"][0][field] = value
        write_records(parent, rows)
    else: write_json(parent / {"frozen": "frozen_artifacts.json", "validation": "val_inputs/result.json", "sealed": "validation/result.json"}[kind], {})
    rebind(parent)
    with pytest.raises((ValueError, OSError, KeyError)): audit(parent)


@pytest.mark.parametrize("kind", ["absolute", "traversal"])
def test_incident_inventory_cannot_read_outside_the_saved_evidence(tmp_path, monkeypatch, kind):
    _, parent, _, _ = storage_fixture(tmp_path, monkeypatch)
    outside = parent.parent / "outside.json"; write_json(outside, {"unrelated": True})
    incident_path = parent / "storage_incident.json"; j = json.loads(incident_path.read_text())
    j["preserved_hashes"][str(outside) if kind == "absolute" else "../outside.json"] = digest(outside)
    write_json(incident_path, j)
    review_path = parent / "storage_repair_review.json"; review = json.loads(review_path.read_text())
    review["incident_sha256"] = digest(incident_path); write_json(review_path, review)
    with pytest.raises(ValueError): audit(parent)
