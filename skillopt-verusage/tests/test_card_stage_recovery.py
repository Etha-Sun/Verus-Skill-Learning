"""Synthetic checks for exact, known-cost full-card-stage recovery."""
import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from skillopt_verusage import augmentation_campaign as campaign_module
from skillopt_verusage.campaign_evidence import expand_strings, shared_strings
from skillopt_verusage.codex_deepseek_bridge import _native_response_usage
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json
from skillopt_verusage.native_card_update import SYSTEM, update_cards
from test_native_candidate_recovery import native_fixture, rebind as native_rebind
from test_transport_recovery import digest, read_records, write_records


PATTERNS = ("augmentation/*/*/result.json", "hints/*/*/hint.json",
            "artifacts/native/**/*", "calls/native/**/*", "calls/native_finalization/**/*",
            "calls/original_only/**/*", "banks/original_only_remaining/proposals/*.json",
            "recovered_native_candidate.json")
FAILED_ID = "59b489b4e74c4880ac630dec4a901250"
ERROR = "Native card reflection incomplete: " + "; ".join([
    "Analyst did not cover every trace exactly once",
    *["Prior native card audit failure: stop new calls"] * 8,
    "Benchmark target name in card"])


def rebind(parent):
    path = parent / "card_stage_repair_review.json"
    review = json.loads(path.read_text())
    review.update(ledger_sha256=digest(parent / "provider_calls.jsonl"),
                  progress_sha256=digest(parent / "progress.json"),
                  preserved_hashes={str(p.relative_to(parent)): digest(p)
                                    for pattern in PATTERNS for p in parent.glob(pattern)
                                    if p.is_file()})
    write_json(path, review)


def caches(parent):
    return sorted(parent.glob("calls/original_only/*/*/request.json"))


def card_fixture(base):
    approved, ancestor, config = native_fixture(base)
    parent = approved / "card-parent"
    for name in ("augmentation", "hints", "banks", "calls", "smoke_plan.json",
                 "smoke_evidence.json", "smoke_review.json", "config.json"):
        source = ancestor / name
        if source.is_dir(): shutil.copytree(source, parent / name)
        else: shutil.copyfile(source, parent / name)
    shutil.copytree(ancestor / "artifacts", parent / "artifacts")
    config["reused_hint_root"] = str(parent)
    parent_config = json.loads((parent / "config.json").read_text())
    parent_config.update(run_root=str(parent), reused_hint_root=str(ancestor))
    write_json(parent / "config.json", parent_config)
    skill = "Synthetic reviewed native skill."
    (parent / "artifacts/native/SKILL.md").write_text(skill)
    write_json(parent / "artifacts/native/learning.json", {"source_count": 38, "audit": []})
    native_review_path = ancestor / "native_candidate_repair_review.json"
    native_review = json.loads(native_review_path.read_text())
    native_review["expected_native_candidate_sha256"] = digest(parent / "artifacts/native/SKILL.md")
    write_json(native_review_path, native_review)
    write_json(parent / "recovered_native_candidate.json", {
        "source_run": str(ancestor), "review_sha256": digest(native_review_path),
        "ledger_sha256": digest(ancestor / "provider_calls.jsonl"),
        "cached_native_requests": 6, "native_outputs_unchanged": True, "new_native_calls": 0})
    write_json(parent / "progress.json", {"phase": "stopped", "error_type": "RuntimeError",
               "error": ERROR, "hint_completed": 114, "hint_rejected": 0})
    records = []
    for n in range(10):
        ids = [f"task:task-{2*n+j:02d}:original" for j in range(2)]
        groups = [{"source_task": f"task-{2*n+j:02d}", "trace_ids": [tid],
                   "evidence_ids": [tid + "/event:1", tid + "/final_validation"],
                   "forbidden_names": ["deserialize"], "source_weight": 1,
                   "original": {"trace_id": tid, "complete_trace": {
                       "events": [], "fixture_note": "x" * (100 if j == 0 else 0)}}, "forks": []}
                  for j, tid in enumerate(ids)]
        packet = {"current_skill": "Synthetic seed", "task_groups": groups,
                  "contract": {"original_questions": 2, "logical_traces": 2,
                               "source_weights": {g["source_task"]: 1 for g in groups}}}
        user = json.dumps(shared_strings(packet, short_keys=True), ensure_ascii=False,
                          separators=(",", ":"))
        payload = GuardedDeepSeek(root=base / "unused", api_key="fixture", guards=[],
                                 ledger=base / "unused-ledger").payload(
                                     system=SYSTEM, user=user, cap=16384)
        request_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
        name = f"card-batch-{n:03d}"
        directory = parent / "calls/original_only" / name / request_hash
        response = {"trace_analyses": [{"trace_id": tid, "observation": "Synthetic original."}
                                       for tid in ids], "cards": []}
        if n == 8:
            response["trace_analyses"] = {tid: "Synthetic original." for tid in ids}
            response["cards"] = [{"content": "Synthetic rejected card.",
                                  "evidence_refs": [ids[1] + "/event:173", ids[1] + "/event:179"],
                                  "source_tasks": [groups[1]["source_task"]], "limitations": []}]
            expected_ids = ids
            unknown_refs = response["cards"][0]["evidence_refs"]
        elif n == 9:
            response["cards"] = [{
                "content": ("**Trigger:** An inner deserializer contract needs proof facts.\n"
                            "**Action:** Use the existing proof block.\n"
                            "**Why:** Existing facts discharge the obligation.\n"
                            "**Validate:** Run verification and safety checks.\n"
                            "**Avoid when:** The lemma is unavailable; do not add a new axiom."),
                "evidence_refs": [ids[0] + "/event:1"],
                "source_tasks": [groups[0]["source_task"]], "limitations": ["Synthetic observation."]}]
        text = json.dumps(response)
        raw_usage = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
                     "input_tokens_details": {"cached_tokens": 2},
                     "output_tokens_details": {"reasoning_tokens": 3}}
        usage = _native_response_usage(json.dumps({"usage": raw_usage}).encode())[0]
        record = {"request_id": FAILED_ID if n == 8 else f"card-{n}", "task_id": name,
                  "model": "deepseek-v4-pro", "attempts": [{"estimated_cost_usd": .01,
                  "usage": usage, "max_tokens": 16384, "finish_reason": "completed", "error": None}]}
        write_json(directory / "request.json", payload)
        write_json(directory / "started.json", {"request_sha256": request_hash})
        write_json(directory / "validated.json", {"text": text, "usage": usage, "record": record})
        write_json(directory / "response.raw", {"status": "completed", "model": "deepseek-v4-pro",
                   "output": [{"type": "message", "role": "assistant", "content": [
                       {"type": "output_text", "text": text}]}], "usage": raw_usage})
        if n < 8:
            write_json(parent / "banks/original_only_remaining/proposals" / f"batch-{n:03d}.json", response)
        records.append(record)
    write_records(parent, records)
    write_json(parent / "card_stage_repair_review.json", {
        "repair_authorized": True, "classification": "full_card_schema_and_lexical_audit_repair",
        "failed_request_id": FAILED_ID, "failed_card_task": "card-batch-008",
        "expected_trace_ids": expected_ids, "unknown_evidence_refs": unknown_refs})
    rebind(parent)
    return approved, parent, ancestor, config


def audit(parent):
    return campaign_module.audit_card_stage_repair(parent, read_records(parent))


def test_exact_known_recovery_excludes_rejected_cache_and_never_calls_api(tmp_path, monkeypatch):
    approved, parent, ancestor, config = card_fixture(tmp_path)
    before = {p: p.read_bytes() for r in (parent, ancestor) for p in r.rglob("*") if p.is_file()}
    receipt = audit(parent)
    assert len(receipt["replay_requests"]) == 9
    assert {r["name"] for r in receipt["replay_requests"]} == {
        f"card-batch-{n:03d}" for n in range(10) if n != 8}
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    monkeypatch.setattr("skillopt_verusage.guarded_deepseek.forward_native_responses",
                        lambda *a, **k: pytest.fail("No recovery API call allowed"))
    campaign = campaign_module.Campaign(config)
    assert len(list(campaign.root.glob("augmentation/*/*/result.json"))) == 114
    assert len(list(campaign.root.glob("banks/*_smoke/cards.json"))) == 2
    assert len(list(campaign.root.glob("calls/native/**/request.json"))) == 5
    assert len(list(campaign.root.glob("calls/native_finalization/**/request.json"))) == 1
    assert not (campaign.root / "calls/original_only/card-batch-008").exists()
    for request in caches(campaign.root):
        payload = json.loads(request.read_text())
        client = GuardedDeepSeek(root=campaign.root / "calls/original_only", api_key="fixture",
                                guards=[], ledger=campaign.root / "replay-ledger.jsonl")
        text, usage = client.call(system=payload["instructions"],
            user=payload["input"][0]["content"][0]["text"], name=request.parent.parent.name,
            cap=payload["max_output_tokens"], effort=payload["reasoning"]["effort"])
        stored = json.loads((request.parent / "validated.json").read_text())
        assert (text, usage) == (stored["text"], stored["usage"])
    assert len(caches(campaign.root)) == 9
    assert not (campaign.root / "replay-ledger.jsonl").exists()
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize("field,value", [
    ("repair_authorized", False), ("classification", "other_error"),
    ("ledger_sha256", "bad"), ("progress_sha256", "bad"),
    ("failed_request_id", "other"), ("failed_card_task", "card-batch-009"),
    ("expected_trace_ids", []), ("unknown_evidence_refs", [])])
def test_receipt_requires_exact_scoped_authority(tmp_path, field, value):
    _, parent, _, _ = card_fixture(tmp_path)
    p = parent / "card_stage_repair_review.json"
    j = json.loads(p.read_text()); j[field] = value; write_json(p, j)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_changed_preserved_evidence_is_rejected(tmp_path, pattern):
    _, parent, _, _ = card_fixture(tmp_path)
    p = next(p for p in parent.glob(pattern) if p.is_file())
    p.write_bytes(b"changed")
    with pytest.raises((ValueError, OSError)): audit(parent)


@pytest.mark.parametrize("kind", ["wrong_phase", "wrong_error", "count", "missing_result",
    "missing_hint", "extra_call", "missing_call", "known_cost", "duplicate", "008_admitted",
    "changed_proposal", "ancestor_unknown", "ancestor_cache", "skill", "learning"])
def test_rebound_receipt_cannot_broaden_recovery(tmp_path, kind):
    _, parent, ancestor, _ = card_fixture(tmp_path)
    if kind in ("wrong_phase", "wrong_error", "count"):
        p = parent / "progress.json"; j = json.loads(p.read_text())
        j[{"wrong_phase": "phase", "wrong_error": "error", "count": "hint_completed"}[kind]] = {
            "wrong_phase": "card_extraction", "wrong_error": ERROR + "; other failure", "count": 113}[kind]
        write_json(p, j)
    elif kind in ("missing_result", "missing_hint", "missing_call"):
        pattern = {"missing_result": "augmentation/*/*/result.json",
                   "missing_hint": "hints/*/*/hint.json",
                   "missing_call": "calls/original_only/*/*/request.json"}[kind]
        next(parent.glob(pattern)).unlink()
    elif kind == "extra_call":
        shutil.copytree(caches(parent)[0].parent,
                        parent / "calls/original_only/card-batch-010/extra")
    elif kind in ("known_cost", "duplicate"):
        rows = read_records(parent)
        if kind == "known_cost": rows[0]["attempts"][0]["estimated_cost_usd"] = None
        else: rows.append(copy.deepcopy(rows[-1]))
        write_records(parent, rows)
    elif kind in ("008_admitted", "changed_proposal"):
        write_json(parent / "banks/original_only_remaining/proposals" /
                   ("batch-008.json" if kind == "008_admitted" else "batch-000.json"), {})
    elif kind == "ancestor_unknown":
        rows = read_records(ancestor); rows[0]["attempts"][0]["estimated_cost_usd"] = None
        write_records(ancestor, rows); native_rebind(ancestor)
    elif kind == "ancestor_cache":
        next(ancestor.glob("calls/native/**/response.raw")).write_bytes(b"changed")
        native_rebind(ancestor)
    elif kind == "skill": (parent / "artifacts/native/SKILL.md").write_text("changed")
    else: write_json(parent / "artifacts/native/learning.json", {"source_count": 37, "audit": []})
    rebind(parent)
    with pytest.raises((ValueError, OSError)): audit(parent)


@pytest.mark.parametrize("kind", ["request_model", "request_effort", "request_cap", "started",
    "raw_text", "raw_model", "raw_usage", "validated_usage", "ledger_model", "ledger_finish",
    "ledger_cap", "ledger_error", "second_attempt", "unknown_ref", "map_analyses"])
def test_rebound_card_cache_requires_exact_completed_contract(tmp_path, kind):
    _, parent, _, _ = card_fixture(tmp_path)
    directory = caches(parent)[0].parent
    if kind.startswith("request_"):
        p = directory / "request.json"; j = json.loads(p.read_text())
        field = kind.split("_", 1)[1]
        j[{"model": "model", "effort": "reasoning", "cap": "max_output_tokens"}[field]] = {
            "model": "deepseek-v4-flash", "effort": {"effort": "max"}, "cap": 8192}[field]
        new_hash = hashlib.sha256(json.dumps(j, ensure_ascii=False).encode()).hexdigest()
        directory.rename(directory.parent / new_hash); directory = directory.parent / new_hash
        write_json(directory / "request.json", j)
        write_json(directory / "started.json", {"request_sha256": new_hash})
    elif kind == "started": write_json(directory / "started.json", {"request_sha256": "bad"})
    elif kind.startswith("raw_"):
        p = directory / "response.raw"; j = json.loads(p.read_text())
        if kind == "raw_text": j["output"][0]["content"][0]["text"] = "{}"
        else: j[kind[4:]] = {"model": "deepseek-v4-flash", "usage": None}[kind[4:]]
        write_json(p, j)
    else:
        p = directory / "validated.json"; j = json.loads(p.read_text())
        if kind == "validated_usage": j["usage"]["prompt_tokens"] = 999
        elif kind in ("unknown_ref", "map_analyses"):
            response = json.loads(j["text"])
            if kind == "map_analyses": response["trace_analyses"] = {a["trace_id"]: a["observation"] for a in response["trace_analyses"]}
            else: response["cards"] = [{"content": "Synthetic card.", "evidence_refs": ["unknown"], "source_tasks": [], "limitations": []}]
            j["text"] = json.dumps(response)
            raw = json.loads((directory / "response.raw").read_text())
            raw["output"][0]["content"][0]["text"] = j["text"]; write_json(directory / "response.raw", raw)
            write_json(parent / "banks/original_only_remaining/proposals/batch-000.json", response)
        else:
            record = j["record"]
            if kind == "ledger_model": record["model"] = "deepseek-v4-flash"
            elif kind == "second_attempt": record["attempts"].append(copy.deepcopy(record["attempts"][0]))
            else: record["attempts"][0][{"ledger_finish": "finish_reason", "ledger_cap": "max_tokens", "ledger_error": "error"}[kind]] = {"ledger_finish": "length", "ledger_cap": 8192, "ledger_error": "failed"}[kind]
            write_records(parent, [record if row["request_id"] == record["request_id"] else row for row in read_records(parent)])
        write_json(p, j)
    rebind(parent)
    with pytest.raises((ValueError, OSError)): audit(parent)


@pytest.mark.parametrize("change", [None, "seed", "evidence", "contract"])
def test_reviewed_replay_uses_exact_paid_packet_or_rejects_before_api(tmp_path, monkeypatch, change):
    approved, parent, _, _ = card_fixture(tmp_path)
    request = caches(parent)[0]
    payload = json.loads(request.read_text())
    user = payload["input"][0]["content"][0]["text"]
    packet = expand_strings(json.loads(user))
    groups = packet["task_groups"]
    seed = approved / "seed.md"
    seed.write_text("Changed seed" if change == "seed" else packet["current_skill"])
    if change == "evidence": groups[0]["original"]["complete_trace"]["events"].append({"changed": True})
    if change == "contract":
        changed = json.loads(user)
        expanded = expand_strings(changed)
        expanded["contract"]["source_weights"][groups[0]["source_task"]] = 2
        user = json.dumps(shared_strings(expanded, short_keys=True))
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    monkeypatch.setattr("skillopt_verusage.guarded_deepseek.forward_native_responses",
                        lambda *a, **k: pytest.fail("Replay must not call upstream"))
    client = GuardedDeepSeek(root=parent / "calls/original_only", api_key="fixture", guards=[],
                            ledger=approved / "replay-ledger.jsonl")
    output = approved / "replay-bank"
    replay = {tuple(g["source_task"] for g in groups): user}
    if change:
        with pytest.raises(ValueError, match="changed the complete source evidence"):
            update_cards(groups, seed, output, client, workers=1, replay_users=replay)
        assert not output.exists()
    else:
        bank = update_cards(groups, seed, output, client, workers=1, replay_users=replay)
        assert json.loads(bank.read_text())["cards"] == []
        assert json.loads((output / "proposals/batch-000.json").read_text()) == json.loads(
            json.loads((request.parent / "validated.json").read_text())["text"])
    assert not (approved / "replay-ledger.jsonl").exists()
