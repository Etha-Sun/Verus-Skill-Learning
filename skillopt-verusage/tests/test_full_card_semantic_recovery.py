"""Only one contradicted full-bank batch may be regenerated after quality rejection."""
import copy
import hashlib
import json
import shutil

import pytest

from skillopt_verusage import augmentation_campaign as campaign_module
from skillopt_verusage.card_bank import build_bundle
from skillopt_verusage.codex_deepseek_bridge import _sha256_json
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json
from skillopt_verusage.skill_artifact import load_skill_artifact
from test_card_storage_recovery import complete_cache, storage_fixture
from test_transport_recovery import digest, read_records, write_records


ERROR = "Smoke quality review missing, rejected or not bound to this evidence"
BAD_CONTENT = ("**Trigger:** Trigger inference fails.\n"
    "**Action:** Annotate a term containing the bound variable.\n"
    "**Why:** This selects a matching pattern.\n"
    "**Validate:** Check verification and preservation.\n"
    "**Avoid when:** The chosen term is not ground.")
GOOD_CONTENT = ("**Trigger:** A witness is needed.\n"
    "**Action:** Expose an existing witness fact.\n"
    "**Why:** The existing premise supports that fact.\n"
    "**Validate:** Check verification and preservation.\n"
    "**Avoid when:** No witness premise is available.")


def build_subbank(root):
    bank = {"schema_version": "stage-card-bank-v1", "cards": []}; provenance = {}; known = {}
    for n, proposal in enumerate(sorted((root / "proposals").glob("batch-*.json"))):
        for card in json.loads(proposal.read_text())["cards"]:
            key = hashlib.sha256(card["content"].encode()).hexdigest()
            if key not in known:
                ident = f"card-{len(bank['cards'])+1:03d}"; known[key] = ident
                bank["cards"].append({"id": ident, "content": card["content"]}); provenance[ident] = []
            provenance[known[key]].append({"batch": n, **card})
    write_json(root / "cards.json", bank); write_json(root / "provenance.json", provenance)


def rebind(parent):
    from skillopt_verusage.full_card_semantic_recovery import SEMANTIC_PATTERNS
    path = parent / "full_card_semantic_repair_review.json"; review = json.loads(path.read_text())
    review.update(ledger_sha256=digest(parent / "provider_calls.jsonl"),
        progress_sha256=digest(parent / "progress.json"),
        quality_evidence_sha256=digest(parent / "artifact_quality_evidence.json"),
        frozen_artifacts_sha256=digest(parent / "frozen_artifacts.json"),
        rejection_sha256=digest(parent / "artifact_review.json"),
        trigger_review_sha256=digest(parent / "audits/trigger_pattern_review.json"),
        preserved_hashes={str(p.relative_to(parent)): digest(p)
            for pattern in SEMANTIC_PATTERNS for p in parent.glob(pattern) if p.is_file()})
    write_json(path, review)


def semantic_fixture(base, monkeypatch):
    from skillopt_verusage import full_card_semantic_recovery
    from test_card_storage_recovery import rebind as storage_rebind
    approved, ancestor, _, config = storage_fixture(base, monkeypatch)
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    seed = ancestor / "artifacts/initial.md"; seed.write_text("Synthetic seed")
    build_subbank(ancestor / "banks/original_only_remaining")
    campaign_module.merge_card_banks([ancestor / "banks/original_only_smoke/cards.json",
        ancestor / "banks/original_only_remaining/cards.json"], ancestor / "banks/original_only/cards.json")
    build_bundle(ancestor / "banks/original_only/cards.json", seed, ancestor / "artifacts/original_only", autonomous_retrieval=True)
    storage_rebind(ancestor)
    parent = approved / "semantic-parent"
    for name in ("augmentation", "hints", "banks", "calls", "artifacts", "smoke_plan.json",
                 "smoke_evidence.json", "smoke_review.json", "config.json"):
        source = ancestor / name
        if source.is_dir(): shutil.copytree(source, parent / name)
        else: shutil.copyfile(source, parent / name)
    for n in (4, 5): shutil.rmtree(parent / "calls/augmented" / f"card-batch-{n:03d}")
    inherited = campaign_module.audit_card_storage_repair(ancestor, read_records(ancestor))
    write_json(parent / "recovered_card_requests.json", inherited)
    parent_config = json.loads((parent / "config.json").read_text())
    parent_config.update(run_root=str(parent), reused_hint_root=str(ancestor)); write_json(parent / "config.json", parent_config)
    config["reused_hint_root"] = str(parent)
    template = next(ancestor.glob("calls/original_only/card-batch-000/*/request.json")).parent
    rows = []
    for n in range(4, 18):
        directory, record = complete_cache(parent, template, "augmented", n)
        record["request_id"] = f"semantic-new-{n}"
        path = directory / "validated.json"; stored = json.loads(path.read_text()); stored["record"] = record
        if n == 6:
            response = json.loads(stored["text"])
            tasks = [f"task-{2*n+j:02d}" for j in range(2)]
            response["cards"] = [{"content": content, "source_tasks": [tasks[0]],
                "evidence_refs": [f"task:{tasks[0]}:cp1/event:1"], "limitations": ["Synthetic observed case."]}
                for content in (GOOD_CONTENT, BAD_CONTENT)]
            stored["text"] = json.dumps(response)
            raw_path = directory / "response.raw"; raw = json.loads(raw_path.read_text())
            raw["output"][0]["content"][0]["text"] = stored["text"]; write_json(raw_path, raw)
            write_json(parent / "banks/augmented_remaining/proposals/batch-006.json", response)
        write_json(path, stored); rows.append(record)
    write_records(parent, rows)
    build_subbank(parent / "banks/augmented_remaining")
    campaign_module.merge_card_banks([parent / "banks/augmented_smoke/cards.json",
        parent / "banks/augmented_remaining/cards.json"], parent / "banks/augmented/cards.json")
    build_bundle(parent / "banks/augmented/cards.json", parent / "artifacts/initial.md", parent / "artifacts/augmented", autonomous_retrieval=True)
    artifacts = {"initial": parent / "artifacts/initial.md", "native": parent / "artifacts/native/SKILL.md",
                 "original_only": parent / "artifacts/original_only", "augmented": parent / "artifacts/augmented"}
    frozen = {k: {"path": str(p), **load_skill_artifact(p).manifest()} for k, p in artifacts.items()}
    write_json(parent / "frozen_artifacts.json", frozen)
    evidence = {"frozen_artifacts_sha256": digest(parent / "frozen_artifacts.json"),
        "banks": {k: digest(parent / "banks" / k / "cards.json") for k in ("original_only", "augmented")}}
    write_json(parent / "artifact_quality_evidence.json", evidence)
    write_json(parent / "artifact_review.json", {"accepted": False, "evidence_sha256": _sha256_json(evidence),
                                               "observations": "Confirmed operative pattern/instance contradiction."})
    write_json(parent / "progress.json", {"phase": "stopped", "error_type": "RuntimeError", "error": ERROR,
               "hint_completed": 114, "hint_rejected": 0, "evaluation_completed": 0})
    bad_hash = hashlib.sha256(BAD_CONTENT.encode()).hexdigest()
    monkeypatch.setattr(full_card_semantic_recovery, "BAD_CARD_HASH", bad_hash)
    counterexample = parent / "augmentation/task-12/cp1/snapshots"
    counterexample.mkdir(parents=True)
    (counterexample / "000013-candidate.diff").write_text("+ let witness = choose |a: A| #[trigger] predicate(a);\n")
    (counterexample / "000013-candidate.rs").write_text("let witness = choose |a: A| #[trigger] predicate(a);\n")
    bad_directory = next(parent.glob("calls/augmented/card-batch-006/*/validated.json")).parent
    counter_paths = [parent / "banks/augmented_remaining/proposals/batch-006.json",
        bad_directory / "request.json", bad_directory / "validated.json", bad_directory / "response.raw",
        counterexample / "000013-candidate.diff", counterexample / "000013-candidate.rs"]
    write_json(parent / "audits/trigger_pattern_review.json", {"status": "confirmed_operative_contradiction",
        "affected_batch": 6, "affected_card_zero_based_index": 1, "card_content_sha256": bad_hash,
        "request_id": "semantic-new-6", "preserved_hashes": {str(p.relative_to(parent)): digest(p) for p in counter_paths}})
    write_json(parent / "full_card_semantic_repair_review.json", {"repair_authorized": True,
        "classification": "full_card_semantic_repair", "bad_card_sha256": bad_hash,
        "bad_batch": "card-batch-006", "rejected_condition": "augmented"})
    rebind(parent)
    return approved, parent, ancestor, config


def audit(parent):
    return campaign_module.audit_full_card_semantic_repair(parent, read_records(parent))


def test_full_semantic_recovery_preserves_raw_bad_card_and_replays_other_35_batches(tmp_path, monkeypatch):
    _, parent, ancestor, _ = semantic_fixture(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for root in (parent, ancestor) for p in root.rglob("*") if p.is_file()}
    receipt = audit(parent)
    assert len(receipt["replay_requests"]) == 35
    assert sum(r["label"] == "original_only" for r in receipt["replay_requests"]) == 18
    assert sum(r["label"] == "augmented" for r in receipt["replay_requests"]) == 17
    assert not any(r["label"] == "augmented" and r["name"] == "card-batch-006" for r in receipt["replay_requests"])
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_semantic_constructor_excludes_only_whole_bad_batch_and_replays35_without_api(tmp_path, monkeypatch):
    approved, parent, _, config = semantic_fixture(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in parent.rglob("*") if p.is_file()}
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(approved))
    monkeypatch.setattr("skillopt_verusage.guarded_deepseek.forward_native_responses",
                        lambda *a, **k: pytest.fail("Semantic recovery must replay saved requests without API"))
    campaign = campaign_module.Campaign(config)
    receipt = json.loads((campaign.root / "recovered_card_requests.json").read_text())
    assert len(receipt["replay_requests"]) == 35
    assert not (campaign.root / "calls/augmented/card-batch-006").exists()
    assert not (campaign.root / "frozen_artifacts.json").exists()
    assert not (campaign.root / "artifact_review.json").exists()
    for entry in receipt["replay_requests"]:
        request = campaign.root / entry["request_relative_path"]; payload = json.loads(request.read_text())
        client = GuardedDeepSeek(root=campaign.root / "calls" / entry["label"], api_key="fixture", guards=[],
                                ledger=campaign.root / "unused-ledger.jsonl")
        text, usage = client.call(system=payload["instructions"], user=payload["input"][0]["content"][0]["text"],
                                 name=entry["name"], cap=16384)
        stored = json.loads((request.parent / "validated.json").read_text())
        assert (text, usage) == (stored["text"], stored["usage"])
    assert not (campaign.root / "unused-ledger.jsonl").exists()
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize("field,value", [("repair_authorized", False), ("classification", "other"),
    ("ledger_sha256", "wrong"), ("progress_sha256", "wrong"), ("quality_evidence_sha256", "wrong"),
    ("frozen_artifacts_sha256", "wrong"), ("rejection_sha256", "wrong"), ("trigger_review_sha256", "wrong"),
    ("bad_card_sha256", "wrong"), ("bad_batch", "card-batch-007")])
def test_semantic_repair_scope_and_bindings_are_exact(tmp_path, monkeypatch, field, value):
    _, parent, _, _ = semantic_fixture(tmp_path, monkeypatch)
    path = parent / "full_card_semantic_repair_review.json"; review = json.loads(path.read_text()); review[field] = value; write_json(path, review)
    with pytest.raises(ValueError): audit(parent)


@pytest.mark.parametrize("kind", ["unknown", "duplicate", "inherited_as_current", "missing_own", "orphan_own",
    "inherited_raw", "current_raw", "bad_card_rewritten", "bad_card_removed", "good_proposal_changed",
    "extra_request", "missing_request", "gate_accepted", "gate_binding", "wrong_error", "wrong_phase",
    "evaluation_started", "val_inputs", "validation", "native_skill", "original_bank", "ancestor_authority",
    "review_classification", "review_card_index", "review_bad_hash", "empty_observations",
    "whitespace_observations", "nonstring_observations"])
def test_rebound_semantic_review_cannot_broaden_replay_or_rewrite_rejected_cards(tmp_path, monkeypatch, kind):
    _, parent, ancestor, _ = semantic_fixture(tmp_path, monkeypatch)
    if kind in {"unknown", "duplicate", "inherited_as_current", "missing_own", "orphan_own"}:
        rows = read_records(parent)
        if kind == "unknown": rows[0]["attempts"][0]["estimated_cost_usd"] = None
        elif kind == "duplicate": rows[0] = copy.deepcopy(rows[1])
        elif kind == "missing_own": rows.pop()
        elif kind == "orphan_own": rows[0]["request_id"] = "unmatched"
        else: rows[0] = json.loads(next(parent.glob("calls/augmented/card-batch-000/*/validated.json")).read_text())["record"]
        write_records(parent, rows)
    elif kind in {"inherited_raw", "current_raw"}:
        n = 0 if kind == "inherited_raw" else 4
        next(parent.glob(f"calls/augmented/card-batch-{n:03d}/*/response.raw")).write_bytes(b"changed")
    elif kind in {"bad_card_rewritten", "bad_card_removed", "good_proposal_changed"}:
        path = parent / "banks/augmented_remaining/proposals" / ("batch-007.json" if kind == "good_proposal_changed" else "batch-006.json")
        response = json.loads(path.read_text())
        if kind == "bad_card_rewritten": response["cards"][1]["content"] = GOOD_CONTENT
        elif kind == "bad_card_removed": response["cards"].pop()
        else: response["trace_analyses"][0]["observation"] = "changed"
        write_json(path, response)
    elif kind == "extra_request": write_json(parent / "calls/augmented/card-batch-018/extra/request.json", {})
    elif kind == "missing_request": next(parent.glob("calls/augmented/card-batch-017/*/request.json")).unlink()
    elif kind in {"gate_accepted", "gate_binding", "empty_observations", "whitespace_observations", "nonstring_observations"}:
        path = parent / "artifact_review.json"; j = json.loads(path.read_text())
        if kind in {"gate_accepted", "gate_binding"}:
            j["accepted" if kind == "gate_accepted" else "evidence_sha256"] = True if kind == "gate_accepted" else "wrong"
        else: j["observations"] = {"empty_observations": "", "whitespace_observations": " \n\t", "nonstring_observations": {"text": "rejected"}}[kind]
        write_json(path, j)
    elif kind in {"wrong_error", "wrong_phase", "evaluation_started"}:
        path = parent / "progress.json"; j = json.loads(path.read_text())
        field, value = {"wrong_error": ("error", ERROR + "; other failure"), "wrong_phase": ("phase", "artifact_quality_review"),
                        "evaluation_started": ("evaluation_completed", 1)}[kind]
        j[field] = value; write_json(path, j)
    elif kind in {"val_inputs", "validation"}: write_json(parent / kind / "result.json", {})
    elif kind == "native_skill": (parent / "artifacts/native/SKILL.md").write_text("changed")
    elif kind == "original_bank": write_json(parent / "banks/original_only/cards.json", {})
    elif kind == "ancestor_authority":
        path = ancestor / "storage_repair_review.json"; j = json.loads(path.read_text()); j["repair_authorized"] = False; write_json(path, j)
    else:
        path = parent / "audits/trigger_pattern_review.json"; j = json.loads(path.read_text())
        field, value = {"review_classification": ("status", "hypothesis"), "review_card_index": ("affected_card_zero_based_index", 0),
                        "review_bad_hash": ("card_content_sha256", "wrong")}[kind]
        j[field] = value; write_json(path, j)
    rebind(parent)
    with pytest.raises((ValueError, OSError, KeyError)): audit(parent)
