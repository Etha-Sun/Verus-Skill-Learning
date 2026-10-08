"""A second schema halt cannot change paid cache ownership or admit dict cards."""
import copy
import hashlib
import json
import shutil

import pytest

from skillopt_verusage import augmentation_campaign as campaign_module
from skillopt_verusage.campaign_evidence import expand_strings, shared_strings
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json
from skillopt_verusage.native_card_update import update_cards
from test_card_stage_recovery import card_fixture, caches, rebind as legacy_rebind
from test_transport_recovery import digest, read_records, write_records


FAILED_ID = "0ed7a54eefab4ffebfa279d601e9e4ee"
ERROR = "Native card reflection incomplete: 'dict' object has no attribute 'strip'; Prior native card audit failure: stop new calls"
PATTERNS = ("augmentation/*/*/result.json", "hints/*/*/hint.json", "artifacts/native/**/*",
            "calls/native/**/*", "calls/native_finalization/**/*", "calls/original_only/**/*",
            "banks/original_only_remaining/proposals/*.json", "recovered_card_requests.json")


def rebind(parent):
    p = parent / "card_stage_repair_review.json"; review = json.loads(p.read_text())
    review.update(ledger_sha256=digest(parent / "provider_calls.jsonl"),
                  progress_sha256=digest(parent / "progress.json"),
                  preserved_hashes={str(p.relative_to(parent)): digest(p)
                      for pattern in PATTERNS for p in parent.glob(pattern) if p.is_file()})
    write_json(p, review)


def chained_fixture(base):
    approved, ancestor, native_ancestor, config = card_fixture(base)
    parent = approved / "content-parent"
    shutil.copytree(ancestor, parent)
    shutil.rmtree(parent / "calls/original_only/card-batch-008")
    inherited = campaign_module.audit_card_stage_repair(ancestor, read_records(ancestor))
    write_json(parent / "recovered_card_requests.json", inherited)
    parent_config = json.loads((parent / "config.json").read_text())
    parent_config.update(run_root=str(parent), reused_hint_root=str(ancestor))
    write_json(parent / "config.json", parent_config)
    config["reused_hint_root"] = str(parent)
    write_json(parent / "progress.json", {"phase": "stopped", "error_type": "RuntimeError",
               "error": ERROR, "hint_completed": 114, "hint_rejected": 0})
    template = caches(ancestor)[0].parent
    payload_template = json.loads((template / "request.json").read_text())
    record_template = json.loads((template / "validated.json").read_text())["record"]
    raw_template = json.loads((template / "response.raw").read_text())
    rows = []
    for n in [8, *range(10, 17)]:
        name = f"card-batch-{n:03d}"
        payload = copy.deepcopy(payload_template)
        packet = expand_strings(json.loads(payload["input"][0]["content"][0]["text"]))
        for j, group in enumerate(packet["task_groups"]):
            task = f"task-{2*n+j:02d}"; tid = f"task:{task}:original"
            group.update(source_task=task, trace_ids=[tid], evidence_ids=[tid + "/event:1", tid + "/final_validation"])
            group["original"]["trace_id"] = tid
        packet["contract"]["source_weights"] = {g["source_task"]: 1 for g in packet["task_groups"]}
        packed = shared_strings(packet, short_keys=True)
        packed["output_contract_reminder"] = {"trace_analyses": "A JSON array, never an object."}
        payload["input"][0]["content"][0]["text"] = json.dumps(packed, ensure_ascii=False, separators=(",", ":"))
        request_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
        directory = parent / "calls/original_only" / name / request_hash
        response = {"trace_analyses": [{"trace_id": g["trace_ids"][0], "observation": "Synthetic original."}
                                      for g in packet["task_groups"]], "cards": []}
        if n == 16:
            response["cards"] = [{"content": {"**Trigger:**": "Missing fact", "**Action:**": "Expose it",
                "**Why:**": "Existing premises", "**Validate:**": "Both validators", "**Avoid when:**": "No premise"},
                "source_tasks": [g["source_task"]], "evidence_refs": [g["evidence_ids"][0]], "limitations": []}
                for g in packet["task_groups"]]
        text = json.dumps(response)
        record = copy.deepcopy(record_template)
        record.update(request_id=FAILED_ID if n == 16 else f"new-card-{n}", task_id=name)
        raw = copy.deepcopy(raw_template); raw["output"][0]["content"][0]["text"] = text
        write_json(directory / "request.json", payload)
        write_json(directory / "started.json", {"request_sha256": request_hash})
        write_json(directory / "validated.json", {"text": text, "usage": record["attempts"][0]["usage"], "record": record})
        write_json(directory / "response.raw", raw)
        if n != 16: write_json(parent / "banks/original_only_remaining/proposals" / f"batch-{n:03d}.json", response)
        rows.append(record)
    p = next(p for p in caches(parent) if p.parent.parent.name == "card-batch-009")
    write_json(parent / "banks/original_only_remaining/proposals/batch-009.json",
               json.loads(json.loads((p.parent / "validated.json").read_text())["text"]))
    write_records(parent, rows)
    write_json(parent / "card_stage_repair_review.json", {"repair_authorized": True,
        "classification": "chained_card_content_type_repair", "failed_request_id": FAILED_ID,
        "failed_card_task": "card-batch-016"})
    rebind(parent)
    return approved, parent, ancestor, native_ancestor, config


def audit(parent):
    return campaign_module.audit_card_stage_repair(parent, read_records(parent))


def cache(parent, n):
    return next(p.parent for p in caches(parent) if p.parent.parent.name == f"card-batch-{n:03d}")


def test_exact_chained_recovery_copies_all_valid_evidence_without_api_or_parent_mutation(tmp_path, monkeypatch):
    approved, parent, ancestor, native, config = chained_fixture(tmp_path)
    before = {p: p.read_bytes() for r in (parent, ancestor, native) for p in r.rglob("*") if p.is_file()}
    review = audit(parent)
    assert len(review["replay_requests"]) == 16
    assert {entry["name"] for entry in review["replay_requests"]} == {f"card-batch-{n:03d}" for n in range(16)}
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    monkeypatch.setattr("skillopt_verusage.guarded_deepseek.forward_native_responses",
                        lambda *a, **k: pytest.fail("No API call authorized in recovery test"))
    campaign = campaign_module.Campaign(config)
    assert len(list(campaign.root.glob("augmentation/*/*/result.json"))) == 114
    assert len(list(campaign.root.glob("banks/*_smoke/cards.json"))) == 2
    assert len(list(campaign.root.glob("calls/native/**/request.json"))) == 5
    assert len(list(campaign.root.glob("calls/native_finalization/**/request.json"))) == 1
    assert len(caches(campaign.root)) == 16
    assert not (campaign.root / "calls/original_only/card-batch-016").exists()
    for request in caches(campaign.root):
        payload = json.loads(request.read_text())
        client = GuardedDeepSeek(root=campaign.root / "calls/original_only", api_key="fixture", guards=[],
                                ledger=campaign.root / "unused-ledger.jsonl")
        result = client.call(system=payload["instructions"], user=payload["input"][0]["content"][0]["text"],
                             name=request.parent.parent.name, cap=16384)
        stored = json.loads((request.parent / "validated.json").read_text())
        assert result == (stored["text"], stored["usage"])
    assert not (campaign.root / "unused-ledger.jsonl").exists()
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize("kind", ["authority", "classification", "failed_id", "failed_task", "ledger_hash", "progress_hash",
    "progress_error", "ancestor_receipt", "ancestor_unknown", "copied_receipt", "inherited_cache",
    "inherited_as_current", "current_duplicate", "current_orphan", "current_unknown", "rejected_proposal",
    "valid_proposal", "missing_proposal", "missing_request", "extra_request", "orphan_request",
    "inherited_extra_file", "native_artifact", "native_cache"])
def test_rebound_receipt_does_not_broaden_chain_or_cache_ownership(tmp_path, kind):
    _, parent, ancestor, _, _ = chained_fixture(tmp_path)
    if kind in ("authority", "classification", "failed_id", "failed_task", "ledger_hash", "progress_hash"):
        p = parent / "card_stage_repair_review.json"; j = json.loads(p.read_text())
        field = {"authority": "repair_authorized", "classification": "classification", "failed_id": "failed_request_id",
                 "failed_task": "failed_card_task", "ledger_hash": "ledger_sha256", "progress_hash": "progress_sha256"}[kind]
        j[field] = False if kind == "authority" else "wrong"; write_json(p, j)
        with pytest.raises(ValueError): audit(parent)
        return
    if kind == "progress_error":
        p = parent / "progress.json"; j = json.loads(p.read_text()); j["error"] += "; another failure"; write_json(p, j)
    elif kind == "ancestor_receipt":
        p = ancestor / "card_stage_repair_review.json"; j = json.loads(p.read_text()); j["repair_authorized"] = False; write_json(p, j)
    elif kind == "ancestor_unknown":
        rows = read_records(ancestor); rows[0]["attempts"][0]["estimated_cost_usd"] = None
        write_records(ancestor, rows); legacy_rebind(ancestor)
    elif kind == "copied_receipt": write_json(parent / "recovered_card_requests.json", {"changed": True})
    elif kind == "inherited_cache": write_json(cache(parent, 0) / "validated.json", {"changed": True})
    elif kind.startswith("current_") or kind == "inherited_as_current":
        rows = read_records(parent)
        if kind == "inherited_as_current": rows[0] = json.loads((cache(parent, 0) / "validated.json").read_text())["record"]
        elif kind == "current_duplicate": rows[0] = copy.deepcopy(rows[1])
        elif kind == "current_orphan": rows[0]["request_id"] = "unmatched"
        else: rows[0]["attempts"][0]["estimated_cost_usd"] = None
        write_records(parent, rows)
    elif kind in ("rejected_proposal", "valid_proposal"):
        write_json(parent / "banks/original_only_remaining/proposals" / ("batch-016.json" if kind == "rejected_proposal" else "batch-000.json"), {})
    elif kind == "missing_proposal": next(parent.glob("banks/original_only_remaining/proposals/*.json")).unlink()
    elif kind == "missing_request": (cache(parent, 10) / "request.json").unlink()
    elif kind == "extra_request": write_json(parent / "calls/original_only/card-batch-017/extra/request.json", {})
    elif kind == "orphan_request": write_json(parent / "calls/original_only/unused/request.json", {})
    elif kind == "inherited_extra_file": write_json(cache(parent, 0) / "extra.json", {})
    elif kind == "native_artifact": (parent / "artifacts/native/SKILL.md").write_text("changed")
    else: next(parent.glob("calls/native/**/response.raw")).write_bytes(b"changed")
    rebind(parent)
    with pytest.raises((ValueError, OSError, KeyError)): audit(parent)


@pytest.mark.parametrize("kind", ["raw_text", "raw_model", "raw_status", "raw_usage", "started", "error",
                                   "second_attempt", "dict_coerced", "wrong_rejected_id", "unknown_ref"])
def test_rebound_current_reply_requires_exact_raw_metering_and_no_dict_coercion(tmp_path, kind):
    _, parent, _, _, _ = chained_fixture(tmp_path)
    directory = cache(parent, 16 if kind in ("dict_coerced", "wrong_rejected_id") else 10)
    if kind == "error": write_json(directory / "error.json", {"type": "IncompleteRead"})
    elif kind == "started": write_json(directory / "started.json", {"request_sha256": "wrong"})
    elif kind.startswith("raw_"):
        p = directory / "response.raw"; j = json.loads(p.read_text())
        if kind == "raw_text": j["output"][0]["content"][0]["text"] = "{}"
        else: j[kind[4:]] = {"model": "deepseek-v4-flash", "status": "incomplete", "usage": None}[kind[4:]]
        write_json(p, j)
    else:
        p = directory / "validated.json"; stored = json.loads(p.read_text())
        if kind in ("second_attempt", "wrong_rejected_id"):
            record = stored["record"]
            if kind == "second_attempt": record["attempts"].append(copy.deepcopy(record["attempts"][0]))
            else: record["request_id"] = "wrong-rejected-id"
            rows = read_records(parent)
            rows = [record if row["task_id"] == record["task_id"] else row for row in rows]
            write_records(parent, rows)
        else:
            response = json.loads(stored["text"])
            if kind == "dict_coerced":
                for c in response["cards"]: c["content"] = "\n".join(k + " " + v for k, v in c["content"].items())
            else:
                packet = expand_strings(json.loads(json.loads((directory / "request.json").read_text())["input"][0]["content"][0]["text"]))
                group = packet["task_groups"][0]
                response["cards"] = [{"content": "**Trigger:** Missing fact\n**Action:** Expose it\n**Why:** Existing premise\n**Validate:** Verify\n**Avoid when:** No premise", "source_tasks": [group["source_task"]], "evidence_refs": [group["trace_ids"][0] + "/event:999"], "limitations": []}]
            stored["text"] = json.dumps(response)
            raw = json.loads((directory / "response.raw").read_text()); raw["output"][0]["content"][0]["text"] = stored["text"]
            write_json(directory / "response.raw", raw)
        write_json(p, stored)
    rebind(parent)
    with pytest.raises((ValueError, OSError)): audit(parent)


@pytest.mark.parametrize("path", ["frozen_artifacts.json", "val_inputs/result.json", "validation/result.json",
                                   "banks/original_only/cards.json", "banks/augmented_remaining/result.json"])
def test_chained_recovery_never_reopens_downstream_state(tmp_path, path):
    _, parent, _, _, _ = chained_fixture(tmp_path); write_json(parent / path, {"unreviewed": True}); rebind(parent)
    with pytest.raises(ValueError): audit(parent)


def test_new_output_reminder_keeps_valid_old_paid_input_and_response_unchanged(tmp_path, monkeypatch):
    approved, parent, _, _, _ = chained_fixture(tmp_path)
    directory = cache(parent, 0); request = directory / "request.json"
    payload = json.loads(request.read_text()); user = payload["input"][0]["content"][0]["text"]
    packet = expand_strings(json.loads(user)); groups = packet["task_groups"]
    seed = approved / "seed.md"; seed.write_text(packet["current_skill"])
    before = {p: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    monkeypatch.setattr("skillopt_verusage.guarded_deepseek.forward_native_responses",
                        lambda *a, **k: pytest.fail("Reminder must not pay to replace valid input"))
    client = GuardedDeepSeek(root=parent / "calls/original_only", api_key="fixture", guards=[],
                            ledger=approved / "unused-ledger.jsonl")
    bank = update_cards(groups, seed, approved / "replayed-bank", client, workers=1,
                        replay_users={tuple(g["source_task"] for g in groups): user})
    assert json.loads(bank.read_text())["cards"] == []
    assert not (approved / "unused-ledger.jsonl").exists()
    assert all(p.read_bytes() == raw for p, raw in before.items())
