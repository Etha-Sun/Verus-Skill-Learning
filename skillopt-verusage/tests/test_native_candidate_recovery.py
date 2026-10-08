"""Synthetic boundaries for replaying a known-cost native syntax-audit halt."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from skillopt_verusage import augmentation_campaign as campaign_module
from skillopt_verusage.codex_deepseek_bridge import _native_response_usage
from skillopt_verusage.codex_reoptimize import _candidate_audit
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json
from test_transport_recovery import digest, fixture, read_records, write_records


ERROR = "Native candidate audit: selected edits contain concrete code/formula: ==>"
PATTERNS = ("augmentation/*/*/result.json", "hints/*/*/hint.json",
            "artifacts/native/patches/*.json", "calls/native/**/*",
            "calls/native_finalization/**/*")


def preserved(parent):
    return {str(p.relative_to(parent)): digest(p)
            for pattern in PATTERNS for p in parent.glob(pattern) if p.is_file()}


def rebind(parent):
    path = parent / "native_candidate_repair_review.json"
    review = json.loads(path.read_text())
    review.update(ledger_sha256=digest(parent / "provider_calls.jsonl"),
                  progress_sha256=digest(parent / "progress.json"),
                  preserved_hashes=preserved(parent))
    write_json(path, review)


def native_fixture(base):
    approved, parent, config = fixture(base)
    for name in ("transport_repair_review.json", "halt_inventory.json"):
        (parent / name).unlink()
    template = json.loads((parent / "augmentation/one/cp1/result.json").read_text())
    for ident in [f"task-{n:02d}" for n in range(35)]:
        for cp in ("cp1", "cp2", "cp3"):
            write_json(parent / "augmentation" / ident / cp / "result.json",
                       {**template, "id": ident})
            write_json(parent / "augmentation" / ident / cp / "copy_marker.json", {"cp": cp})
            write_json(parent / "hints" / ident / cp / "hint.json", {"hint_text": "synthetic hint"})
    write_json(parent / "progress.json", {"phase": "stopped", "error_type": "RuntimeError",
               "error": ERROR, "hint_completed": 114, "hint_rejected": 0})
    records = [read_records(parent)[0]]
    for index in range(6):
        label, stage = ("native", "analyst") if index < 5 else ("native_finalization", "merge")
        payload = GuardedDeepSeek(root=base / "unused", api_key="fixture", guards=[],
                                 ledger=base / "unused-ledger").payload(
                                     system="synthetic native optimizer", user=f"batch {index}", cap=16384)
        request_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
        fingerprint = hashlib.sha256((payload["instructions"] + f"batch {index}").encode()).hexdigest()
        task = stage + "/" + fingerprint
        directory = parent / "calls" / label / task / request_hash
        edits = [{"op": "append", "content": "Use explicit antecedent reasoning for ==> obligations."}]
        response = {"patch": {"edits": edits}, "reasoning": "synthetic reflection"} if index < 5 else {"edits": edits}
        text = json.dumps(response)
        raw_usage = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
                     "input_tokens_details": {"cached_tokens": 2},
                     "output_tokens_details": {"reasoning_tokens": 3}}
        usage = _native_response_usage(json.dumps({"usage": raw_usage}).encode())[0]
        record = {"request_id": f"native-{index}", "task_id": task, "model": "deepseek-v4-pro",
                  "attempts": [{"estimated_cost_usd": .01, "usage": usage, "max_tokens": 16384,
                                "finish_reason": "completed", "error": None}]}
        write_json(directory / "request.json", payload)
        write_json(directory / "started.json", {"request_sha256": request_hash})
        write_json(directory / "validated.json", {"text": text, "usage": usage, "record": record})
        write_json(directory / "response.raw", {"status": "completed", "model": "deepseek-v4-pro",
                   "output": [{"type": "message", "role": "assistant",
                               "content": [{"type": "output_text", "text": text}]}], "usage": raw_usage})
        if index < 5:
            write_json(parent / "artifacts/native/patches" / f"minibatch_succ_{index:03d}.json", response["patch"])
        records.append(record)
    write_records(parent, records)
    write_json(parent / "native_candidate_repair_review.json", {
        "repair_authorized": True, "classification": "generic_native_syntax_audit_mismatch"})
    rebind(parent)
    return approved, parent, config


def audit(parent):
    return campaign_module.audit_native_candidate_repair(parent, read_records(parent))


def caches(parent):
    return sorted([*parent.glob("calls/native/**/request.json"),
                   *parent.glob("calls/native_finalization/**/request.json")])


def test_exact_native_repair_and_constructor_replay_without_api(tmp_path, monkeypatch):
    approved, parent, config = native_fixture(tmp_path)
    before = {p: p.read_bytes() for p in parent.rglob("*") if p.is_file()}
    review = audit(parent)
    assert review["cached_native_requests"] == 6
    assert review["new_native_calls"] == 0
    assert review["native_outputs_unchanged"] is True
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    monkeypatch.setattr("skillopt_verusage.guarded_deepseek.forward_native_responses",
                        lambda *a, **k: pytest.fail("Recovery replay must not contact upstream"))
    campaign = campaign_module.Campaign(config)
    assert len(list(campaign.root.glob("augmentation/*/*/result.json"))) == 114
    assert len(list(campaign.root.glob("banks/*_smoke/cards.json"))) == 2
    assert campaign.reused_smoke_parent == parent
    for pattern in ("augmentation/*/*/copy_marker.json", "banks/*_smoke/cards.json",
                    "banks/*_smoke/proposals/batch-000.json", "calls/native/**/*",
                    "calls/native_finalization/**/*"):
        for p in parent.glob(pattern):
            if p.is_file():
                assert p.read_bytes() == (campaign.root / p.relative_to(parent)).read_bytes()
    for request in caches(parent):
        payload = json.loads(request.read_text())
        relative = request.relative_to(parent)
        label = relative.parts[1]
        name = str(Path(*relative.parts[2:-2]))
        client = GuardedDeepSeek(root=campaign.root / "calls" / label, api_key="fixture", guards=[],
                                ledger=campaign.root / "replay-ledger.jsonl")
        text, usage = client.call(system=payload["instructions"],
            user=payload["input"][0]["content"][0]["text"], name=name,
            cap=payload["max_output_tokens"], effort=payload["reasoning"]["effort"])
        stored = json.loads((request.parent / "validated.json").read_text())
        assert (text, usage) == (stored["text"], stored["usage"])
    assert not (campaign.root / "replay-ledger.jsonl").exists()
    for p, raw in before.items():
        assert p.read_bytes() == raw


@pytest.mark.parametrize("field,value", [
    ("repair_authorized", False), ("classification", "different_failure"),
    ("ledger_sha256", "bad"), ("progress_sha256", "bad")])
def test_receipt_requires_exact_authority_and_bindings(tmp_path, field, value):
    _, parent, _ = native_fixture(tmp_path)
    p = parent / "native_candidate_repair_review.json"
    j = json.loads(p.read_text()); j[field] = value; write_json(p, j)
    with pytest.raises(ValueError):
        audit(parent)


@pytest.mark.parametrize("change", ["missing", "extra", "traversal", "absolute"])
def test_preserved_inventory_is_exact_and_confined(tmp_path, change):
    _, parent, _ = native_fixture(tmp_path)
    p = parent / "native_candidate_repair_review.json"; j = json.loads(p.read_text())
    if change == "missing": j["preserved_hashes"].pop(next(iter(j["preserved_hashes"])))
    else: j["preserved_hashes"][{"extra": "unreviewed.json", "traversal": "../outside.json",
                                "absolute": "/outside.json"}[change]] = "a" * 64
    write_json(p, j)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_mutation_of_each_preserved_evidence_class_is_rejected(tmp_path, pattern):
    _, parent, _ = native_fixture(tmp_path)
    p = next(p for p in parent.glob(pattern) if p.is_file())
    write_json(p, {"changed": True})
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("field,value", [("phase", "native_learning"), ("error_type", "ValueError"),
    ("error", ERROR + "; other failure"), ("hint_completed", 113)])
def test_rebound_progress_cannot_broaden_recovery(tmp_path, field, value):
    _, parent, _ = native_fixture(tmp_path)
    p = parent / "progress.json"; j = json.loads(p.read_text()); j[field] = value; write_json(p, j)
    rebind(parent)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("kind", ["result_count", "hint_count", "unknown", "duplicate",
    "orphan_native", "attempts", "result_unsafe", "result_model", "result_unmetered"])
def test_rebound_count_usage_and_actor_boundaries(tmp_path, monkeypatch, kind):
    approved, parent, config = native_fixture(tmp_path)
    if kind in ("result_count", "hint_count"):
        pattern = "augmentation/*/*/result.json" if kind == "result_count" else "hints/*/*/hint.json"
        next(parent.glob(pattern)).unlink()
    elif kind.startswith("result_"):
        p = next(parent.glob("augmentation/*/*/result.json")); j = json.loads(p.read_text())
        if kind == "result_unsafe": j["safety_passed"] = False
        elif kind == "result_model": j["actor_model"] = "deepseek-v4-flash"
        else: j["usage"]["unknown_cost_requests"] = 1
        write_json(p, j)
    else:
        records = read_records(parent)
        if kind == "unknown": records[0]["attempts"][0]["estimated_cost_usd"] = None
        elif kind == "duplicate": records.append(copy.deepcopy(records[-1]))
        elif kind == "orphan_native":
            row = copy.deepcopy(records[-1]); row["request_id"] = "orphan"; row["task_id"] = "analyst/orphan"; records.append(row)
        else: records[-1]["attempts"].append(copy.deepcopy(records[-1]["attempts"][0]))
        write_records(parent, records)
    rebind(parent)
    with pytest.raises(ValueError):
        if kind.startswith("result_") and kind != "result_count":
            monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
            campaign_module.Campaign(config)
        else:
            audit(parent)


@pytest.mark.parametrize("kind", ["started", "raw_text", "raw_model", "raw_status", "raw_usage",
    "validated_record", "validated_usage", "response_schema", "error", "missing_raw"])
def test_rebound_cache_still_requires_exact_metered_completed_response(tmp_path, kind):
    _, parent, _ = native_fixture(tmp_path); directory = caches(parent)[0].parent
    if kind == "error": write_json(directory / "error.json", {"type": "IncompleteRead"})
    elif kind == "missing_raw": (directory / "response.raw").unlink()
    elif kind == "started": write_json(directory / "started.json", {"request_sha256": "bad"})
    elif kind.startswith("raw_"):
        p = directory / "response.raw"; j = json.loads(p.read_text())
        if kind == "raw_text": j["output"][0]["content"][0]["text"] = "{}"
        else: j[kind[4:]] = {"model": "deepseek-v4-flash", "status": "incomplete", "usage": None}[kind[4:]]
        write_json(p, j)
    else:
        p = directory / "validated.json"; j = json.loads(p.read_text())
        if kind == "validated_record": j["record"]["request_id"] = "wrong"
        elif kind == "validated_usage": j["usage"]["prompt_tokens"] = 999
        else:
            j["text"] = "{}"
            raw = json.loads((directory / "response.raw").read_text())
            raw["output"][0]["content"][0]["text"] = j["text"]; write_json(directory / "response.raw", raw)
        write_json(p, j)
    rebind(parent)
    with pytest.raises((ValueError, OSError)): audit(parent)


@pytest.mark.parametrize("field,value", [("model", "deepseek-v4-flash"),
    ("reasoning", {"effort": "max"}), ("text", {"format": {"type": "json_schema"}}),
    ("max_output_tokens", 8192), ("stream", True)])
def test_rebound_payload_at_correct_digest_still_requires_frozen_native_contract(tmp_path, field, value):
    _, parent, _ = native_fixture(tmp_path); old = caches(parent)[0].parent
    payload = json.loads((old / "request.json").read_text()); payload[field] = value
    request_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
    new = old.parent / request_hash; old.rename(new)
    write_json(new / "request.json", payload)
    write_json(new / "started.json", {"request_sha256": request_hash})
    rebind(parent)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("kind", ["patch_count", "request_count", "extra_request", "digest_path",
                                   "fingerprint_path", "stage_path"])
def test_rebound_native_cache_count_and_request_paths_remain_exact(tmp_path, kind):
    _, parent, _ = native_fixture(tmp_path)
    request = caches(parent)[0]
    if kind == "patch_count": next(parent.glob("artifacts/native/patches/*.json")).unlink()
    elif kind == "request_count": request.unlink()
    elif kind == "extra_request":
        write_json(parent / "calls/native/ranking/extra/request.json", {})
    elif kind == "digest_path": request.parent.rename(request.parent.with_name("wrong-digest"))
    elif kind == "fingerprint_path": request.parent.parent.rename(request.parent.parent.with_name("wrong-fingerprint"))
    else: request.parent.parent.parent.rename(request.parent.parent.parent.with_name("ranking"))
    rebind(parent)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("field,value", [("model", "deepseek-v4-flash"), ("task_id", "analyst/wrong"),
    ("max_tokens", 8192), ("finish_reason", "length"), ("error", "failed"), ("usage", None)])
def test_rebound_matching_ledger_record_still_requires_frozen_single_completed_attempt(tmp_path, field, value):
    _, parent, _ = native_fixture(tmp_path)
    directory = caches(parent)[0].parent
    p = directory / "validated.json"; stored = json.loads(p.read_text())
    record = stored["record"]
    if field in ("model", "task_id"): record[field] = value
    else: record["attempts"][0][field] = value
    stored["usage"] = record["attempts"][0]["usage"]
    records = read_records(parent)
    records = [record if row.get("request_id") == record["request_id"] else row for row in records]
    write_records(parent, records); write_json(p, stored); rebind(parent)
    with pytest.raises(ValueError): audit(parent)


def test_native_sse_cache_uses_normalized_usage_without_an_api_call(tmp_path):
    _, parent, _ = native_fixture(tmp_path)
    p = caches(parent)[0].parent / "response.raw"
    response = json.loads(p.read_text())
    p.write_text("data: " + json.dumps({"type": "response.completed", "response": response}) + "\n\ndata: [DONE]\n")
    rebind(parent)
    assert audit(parent)["cached_native_requests"] == 6


@pytest.mark.parametrize("name", ["request.json", "started.json", "validated.json", "response.raw"])
def test_rebound_missing_cache_file_is_fail_closed(tmp_path, name):
    _, parent, _ = native_fixture(tmp_path)
    (caches(parent)[0].parent / name).unlink()
    rebind(parent)
    with pytest.raises((ValueError, OSError)): audit(parent)


@pytest.mark.parametrize("stage,value", [("analyst", {"patch": {"edits": "not-a-list"}}),
    ("analyst", {"patch": []}), ("merge", {"edits": "not-a-list"}), ("merge", {})])
def test_matching_raw_and_validated_text_cannot_bypass_native_response_schema(tmp_path, stage, value):
    _, parent, _ = native_fixture(tmp_path)
    directory = next(p.parent for p in caches(parent) if p.parent.parent.parent.name == stage)
    p = directory / "validated.json"; stored = json.loads(p.read_text()); stored["text"] = json.dumps(value)
    write_json(p, stored)
    p = directory / "response.raw"; raw = json.loads(p.read_text())
    raw["output"][0]["content"][0]["text"] = stored["text"]; write_json(p, raw)
    rebind(parent)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("pattern", ["augmentation/*/*/result.json", "hints/*/*/hint.json",
                                     "calls/native/**/response.raw"])
def test_rebound_symlink_cannot_import_outside_evidence(tmp_path, pattern):
    _, parent, _ = native_fixture(tmp_path)
    p = next(parent.glob(pattern)); outside = tmp_path / "outside-evidence.json"
    outside.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(outside)
    rebind(parent)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("path", ["artifacts/native/SKILL.md", "artifacts/native/learning.json",
    "frozen_artifacts.json", "val_inputs/result.json", "validation/result.json"])
def test_existing_learning_or_downstream_outputs_block_recovery(tmp_path, path):
    _, parent, _ = native_fixture(tmp_path); write_json(parent / path, {"unreviewed": True})
    rebind(parent)
    with pytest.raises(ValueError): audit(parent)


def test_missing_native_review_does_not_authorize_constructor(tmp_path, monkeypatch):
    approved, parent, config = native_fixture(tmp_path)
    (parent / "native_candidate_repair_review.json").unlink()
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    with pytest.raises(ValueError): campaign_module.Campaign(config)


def test_native_syntax_opt_out_keeps_default_card_gate_and_other_candidate_guards():
    edit = {"edits": [{"op": "append", "content": "Use explicit reasoning for ==> obligations."}]}
    report = [{"status": "applied_append"}]
    assert any("concrete code/formula" in x for x in _candidate_audit("seed", "candidate", edit, report))
    assert _candidate_audit("seed", "candidate", edit, report, prose_only=False) == []
    for candidate, patch, statuses, expected in [
        ("x" * 4001, edit, report, "exceeds"),
        ("0123456789abcdefabcd", edit, report, "identifier"),
        ("candidate", edit, [{"status": "unapplied"}], "not applied"),
        ("candidate", {"edits": [{"content": "Introduce assume to bypass verification."}]}, report, "bypass")]:
        assert any(expected in x for x in _candidate_audit("seed", candidate, patch, statuses, prose_only=False))
