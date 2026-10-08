from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil

import pytest


spec = importlib.util.spec_from_file_location("hindsight_summary", Path(__file__).resolve().parents[1]/"scripts/summarize_hindsight_campaign.py")
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value)+"\n")


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(tmp_path))
    root = tmp_path/"campaign"
    frozen = {}
    for condition in summary.CONDITIONS:
        artifact = root/"artifacts"/condition
        artifact.mkdir(parents=True)
        (artifact/"SKILL.md").write_text("Public skill\n")
        (artifact/"card_read.py").write_text("# ID reader\n")
        frozen[condition] = {"path": str(artifact), "artifact_sha256": summary.artifact_sha(artifact)}
    for condition in ("original_only", "augmented"):
        write(root/"banks"/condition/"cards.json", {"cards": []})
    write(root/"frozen_artifacts.json", frozen)
    evidence = {"frozen_artifacts_sha256": summary.sha(root/"frozen_artifacts.json"),
                "banks": {c: summary.sha(root/"banks"/c/"cards.json") for c in ("original_only", "augmented")}}
    write(root/"artifact_quality_evidence.json", evidence)
    write(root/"artifact_review.json", {"accepted": True, "evidence_sha256": summary.json_sha(evidence),
                                        "observations": "Synthetic reviewed fixture"})
    items = [{"id": f"task-{i:02d}", "source_path": "NEVER_READ.rs"} for i in range(20)]
    write(root/"progress.json", {"phase": "complete", "evaluation_completed": 160})
    blocks, rows, ledger = [], [], []
    for repeat in range(2):
        blocks.append([(repeat, c, item) for c in summary.CONDITIONS for item in items])
        for condition in summary.CONDITIONS:
            for item in items:
                hard = condition == "native" or (condition == "original_only" and repeat == 1) or (condition == "augmented" and repeat == 0)
                late = condition == "native" and repeat == 1 and item["id"] == "task-19"
                result = {"id": item["id"], "hard": int(hard), "within_budget": not late,
                          "timed_out": late, "fidelity": "V2_TRACE", "actor_model": "deepseek-v4-pro",
                          "actor_reasoning_effort": "max", "skill_sha256": frozen[condition]["artifact_sha256"],
                          "bridge_task_key": f"val_r{repeat+1}_{condition}--{item['id']}", "provider_valid": True,
                          "usage": {"requests": 1, "metered_requests": 1, "completed_requests": 1,
                                    "incomplete_requests": 0, "error_requests": 0, "unknown_status_requests": 0,
                                    "prompt_tokens": 10, "completion_tokens": 100, "reasoning_tokens": 0,
                                    "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 10,
                                    "upstream_models": ["deepseek-v4-pro"],
                                    "estimated_cost_usd": .2, "unknown_cost_requests": 0},
                          "actor_wall_seconds": 5, "final_validation_wall_seconds": 1, "wall_seconds": 6}
                directory = root/"validation"/f"repeat_{repeat+1}"/condition/item["id"]
                write(directory/"result.json", result)
                write(directory/"run_manifest.json", {"model": "deepseek-v4-pro", "reasoning_effort": "max",
                    "timeout_seconds": 600, "condition_skill_sha256": result["skill_sha256"]})
                reads = [{"operation": "read", "id": "card-001", "content": "Advice"}] if condition == "augmented" and repeat == 0 else []
                audit = {"events": reads, "read_calls": len(reads), "search_calls": 0,
                         "read_ids": ["card-001"] if reads else [],
                         "direct_bank_access_commands": [{"command": "cat cards.json"}] if item["id"] == "task-00" and reads else []}
                write(directory/"retrieval_audit.json", audit)
                rows.append({**result, "condition": condition, "repetition": repeat+1})
                ledger.append({"request_id": result["bridge_task_key"], "task_id": result["bridge_task_key"],
                    "upstream_model": "deepseek-v4-pro", "attempts": [{"usage": {k: result["usage"][k]
                      for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")},
                      "estimated_cost_usd": .2, "finish_reason": "completed", "error": None}]})
    write(root/"evaluation_schedule.json", {"blocks": blocks, "test_accessed": False,
                                            "frozen_artifacts_sha256": evidence["frozen_artifacts_sha256"]})
    write(root/"validation_rows.json", rows)
    (root/"provider_calls.jsonl").write_text("\n".join(map(json.dumps, ledger))+"\n")
    return root


def test_task_cluster_bootstrap_keeps_opposed_repetitions_together(campaign):
    result = summary.summarize(campaign)
    primary = result["primary_paired_augmented_minus_original_only"]
    assert primary["independent_tasks"] == 20
    assert primary["mean_delta"] == 0 and primary["percentile_95_ci"] == [0, 0]
    assert primary["seed"] == summary.BOOTSTRAP_SEED
    assert all(delta == 0 for delta in primary["per_task_delta"].values())
    augmented = result["conditions"]["augmented"]
    assert augmented["task_n"] == 20 and augmented["run_n"] == 40
    assert augmented["task_success_histogram"] == {"0": 0, "1": 20, "2": 0}
    assert augmented["repetitions"]["1"]["within_budget_solved"] == 20
    assert augmented["repetitions"]["2"]["within_budget_solved"] == 0
    assert augmented["retrieval_exposure"] == {"runs_with_reads": 20, "read_calls": 20,
        "search_calls": 0, "distinct_card_ids": ["card-001"], "runs_with_direct_bank_access": 1,
        "direct_bank_access_commands": 1}
    assert augmented["all_run"]["completion_tokens"] == 4000
    assert augmented["all_run"]["actor_wall_seconds"] == 200
    assert augmented["all_run"]["final_validation_wall_seconds"] == 40
    assert result["conditions"]["native"]["late_dual_pass"] == 1
    joint = result["joint_success_augmented_vs_original_only"]
    assert joint["paired_runs"] == 0 and joint["task_n"] == 0
    assert joint["augmented"]["completion_tokens"] == 0
    assert result["ledger_reconciliation"]["mismatched_runs"] == 0
    assert result["ledger_reconciliation"]["provider_fidelity_review_keys"] == []
    assert augmented["all_run_settled_ledger"] == augmented["all_run"]
    assert any("not correct application" in caveat for caveat in result["caveats"])


def test_rejected_review_blocks_all_evaluation_reads(campaign, monkeypatch):
    receipt = summary.read_json(campaign/"artifact_review.json")
    write(campaign/"artifact_review.json", {**receipt, "accepted": False})
    original = summary.read_json
    accessed = []
    def audited_read(path):
        accessed.append(path.name)
        return original(path)
    monkeypatch.setattr(summary, "read_json", audited_read)
    with pytest.raises(ValueError, match="Accepted frozen"):
        summary.summarize(campaign)
    assert "validation_rows.json" not in accessed and "evaluation_schedule.json" not in accessed


def test_mutated_reader_fails_before_evaluation_reads(campaign):
    (campaign/"artifacts/augmented/card_read.py").write_text("# changed reader\n")
    with pytest.raises(ValueError, match="Frozen artifact changed"):
        summary.summarize(campaign)


@pytest.mark.parametrize("change", ["missing", "duplicate", "wrong_condition", "wrong_repeat"])
def test_requires_all_160_unique_run_combinations(campaign, change):
    rows = summary.read_json(campaign/"validation_rows.json")
    if change == "missing": rows.pop()
    elif change == "duplicate": rows[-1] = rows[0]
    elif change == "wrong_condition": rows[-1]["condition"] = "other"
    else: rows[-1]["repetition"] = 3
    write(campaign/"validation_rows.json", rows)
    with pytest.raises(ValueError, match="Incomplete or duplicate"):
        summary.summarize(campaign)


def test_result_file_must_exactly_agree_with_validation_rows(campaign):
    path = campaign/"validation/repeat_1/initial/task-00/result.json"
    result = summary.read_json(path)
    write(path, {**result, "hard": 1})
    with pytest.raises(ValueError, match="Result disagrees"):
        summary.summarize(campaign)


def test_retrieval_counts_must_match_actual_audit_events(campaign):
    path = campaign/"validation/repeat_1/augmented/task-00/retrieval_audit.json"
    audit = summary.read_json(path)
    write(path, {**audit, "read_calls": 99})
    with pytest.raises(ValueError, match="Retrieval counters"):
        summary.summarize(campaign)


def change_result(root, condition, ident, repeat, **changes):
    path = root/"validation"/f"repeat_{repeat}"/condition/ident/"result.json"
    result = {**summary.read_json(path), **changes}
    write(path, result)
    rows = summary.read_json(root/"validation_rows.json")
    for row in rows:
        if (row["condition"], row["id"], row["repetition"]) == (condition, ident, repeat):
            row.update(changes)
    write(root/"validation_rows.json", rows)


def test_joint_success_and_invalid_success_do_not_reward_failures(campaign):
    change_result(campaign, "original_only", "task-00", 1, hard=1)
    change_result(campaign, "initial", "task-01", 1, hard=1, fidelity="V0_INVALID")
    result = summary.summarize(campaign)
    assert result["conditions"]["initial"]["invalid"] == 1
    assert result["conditions"]["initial"]["within_budget_solved"] == 0
    joint = result["joint_success_augmented_vs_original_only"]
    assert joint["paired_runs"] == joint["task_n"] == 1
    assert joint["original_only"]["completion_tokens"] == 100
    assert joint["augmented"]["estimated_actor_cost_usd"] == .2
    primary = result["primary_paired_augmented_minus_original_only"]
    assert primary["mean_delta"] == -.025
    assert primary["per_task_delta"]["task-00"] == -.5
    assert primary["percentile_95_ci"] == [-.075, 0]


def test_unknown_snapshot_cost_remains_flagged_when_final_ledger_is_known(campaign):
    result = summary.read_json(campaign/"validation/repeat_1/initial/task-00/result.json")
    change_result(campaign, "initial", "task-00", 1, usage={**result["usage"], "unknown_cost_requests": 1})
    report = summary.summarize(campaign)
    assert report["conditions"]["initial"]["snapshot_unknown_cost_requests"] == 1
    assert report["ledger_reconciliation"]["mismatched_runs"] == 1
    assert report["ledger_reconciliation"]["provider_fidelity_review_keys"] == ["val_r1_initial--task-00"]
    assert report["conditions"]["initial"]["all_run_settled_ledger"]["estimated_actor_cost_usd"] == pytest.approx(8)


def test_runtime_budget_must_match_600s_contract(campaign):
    path = campaign/"validation/repeat_1/initial/task-00/run_manifest.json"
    manifest = summary.read_json(path)
    write(path, {**manifest, "timeout_seconds": 1800})
    with pytest.raises(ValueError, match="runtime contract"):
        summary.summarize(campaign)


def test_summary_output_is_fresh_and_only_under_approved_run_root(campaign, monkeypatch, tmp_path):
    output = campaign/"analysis/summary"
    monkeypatch.setattr("sys.argv", ["summary", "--run-root", str(campaign), "--output-dir", str(output)])
    summary.main()
    assert summary.read_json(output/"summary.json")["conditions"]["initial"]["task_n"] == 20
    with pytest.raises(ValueError, match="overwrite"):
        summary.main()
    with pytest.raises(ValueError, match="external run-root child"):
        summary.approved_child(tmp_path)


def test_bootstrap_constant_effect_and_fixed_seed():
    positive = summary.task_bootstrap({str(i): 1 for i in range(20)})
    assert positive["mean_delta"] == 1 and positive["percentile_95_ci"] == [1, 1]
    mixed = {str(i): (i % 3-1)/2 for i in range(20)}
    assert summary.task_bootstrap(mixed) == summary.task_bootstrap(mixed)


def edit_ledger(root, change):
    path = root/"provider_calls.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    change(rows)
    path.write_text("\n".join(map(json.dumps, rows))+"\n")


def test_late_timeout_charge_is_reported_separately_without_editing_result(campaign):
    key = "val_r1_augmented--task-00"
    change_result(campaign, "augmented", "task-00", 1, within_budget=False, timed_out=True, fidelity="V1_TRUNCATED")
    result_path = campaign/"validation/repeat_1/augmented/task-00/result.json"
    original_result = result_path.read_bytes()
    def add_late(rows):
        rows.append({"request_id": "late-response", "task_id": key, "upstream_model": "deepseek-v4-pro",
                     "attempts": [{"finish_reason": "completed", "estimated_cost_usd": .4, "error": None,
                                   "usage": {"prompt_tokens": 20, "completion_tokens": 200}}]})
    edit_ledger(campaign, add_late)
    result = summary.summarize(campaign)
    reconciliation = result["ledger_reconciliation"]
    assert reconciliation["mismatched_runs"] == 1
    run = reconciliation["runs"][key]
    assert run["snapshot_usage"]["completion_tokens"] == 100
    assert run["settled_ledger_usage"]["completion_tokens"] == 300
    assert run["settled_minus_snapshot"]["completion_tokens"] == 200
    assert run["settled_minus_snapshot"]["estimated_cost_usd"] == pytest.approx(.4)
    assert run["saved_fidelity"] == "V1_TRUNCATED" and run["outcomes_not_reclassified"]
    assert not run["provider_review_needed"]
    augmented = result["conditions"]["augmented"]
    assert augmented["all_run"]["completion_tokens"] == 4000
    assert augmented["all_run_settled_ledger"]["completion_tokens"] == 4200
    assert augmented["all_run_settled_ledger"]["estimated_actor_cost_usd"] == pytest.approx(8.4)
    assert augmented["within_budget_solved"] == 19 and augmented["late_dual_pass"] == 1
    assert result_path.read_bytes() == original_result
    assert result["evidence"]["reporter_sha256"] == summary.sha(Path(summary.__file__))


@pytest.mark.parametrize("change", ["unknown_cost", "missing_task", "duplicate_request", "unmatched_task"])
def test_settled_ledger_must_be_known_complete_and_unique(campaign, change):
    def mutate(rows):
        if change == "unknown_cost": rows[0]["attempts"][0]["estimated_cost_usd"] = None
        elif change == "missing_task": rows.pop(0)
        elif change == "duplicate_request": rows.append(rows[0])
        else: rows[0]["task_id"] = "val_r1_other--task-00"
    edit_ledger(campaign, mutate)
    with pytest.raises(ValueError, match="ledger"):
        summary.summarize(campaign)


def test_model_difference_requires_review_not_fidelity_reclassification(campaign):
    edit_ledger(campaign, lambda rows: rows[0].update(upstream_model="unexpected-model"))
    result = summary.summarize(campaign)
    keys = result["ledger_reconciliation"]["provider_fidelity_review_keys"]
    assert keys == ["val_r1_initial--task-00"]
    assert result["ledger_reconciliation"]["runs"][keys[0]]["saved_fidelity"] == "V2_TRACE"
    assert result["conditions"]["initial"]["invalid"] == 0
    assert result["outcome_metrics_status"] == "requires_provider_fidelity_review"


def test_joint_success_cost_uses_settled_ledger_without_erasing_snapshot(campaign):
    change_result(campaign, "original_only", "task-00", 1, hard=1)
    def add_charge(rows):
        rows.append({"request_id": "late-joint-charge", "task_id": "val_r1_augmented--task-00",
                     "upstream_model": "deepseek-v4-pro", "attempts": [{"finish_reason": "completed",
                     "usage": {"prompt_tokens": 20, "completion_tokens": 200}, "estimated_cost_usd": .4}]})
    edit_ledger(campaign, add_charge)
    joint = summary.summarize(campaign)["joint_success_augmented_vs_original_only"]
    assert joint["paired_runs"] == 1
    assert joint["augmented"]["completion_tokens"] == 100
    assert joint["augmented_settled_ledger"]["completion_tokens"] == 300
    assert joint["augmented_settled_ledger"]["estimated_actor_cost_usd"] == pytest.approx(.6)


def test_unfinished_campaign_cannot_claim_settled_ledger(campaign):
    write(campaign/"progress.json", {"phase": "validation", "evaluation_completed": 160})
    with pytest.raises(ValueError, match="Completed drained"):
        summary.summarize(campaign)


@pytest.fixture
def recovered_campaign(campaign, monkeypatch):
    change_result(campaign, "native", "task-00", 1, timed_out=True,
                  within_budget=False, fidelity="V1_TRUNCATED")
    rows = summary.read_json(campaign/"validation_rows.json")
    inherited = [r for r in rows if r["repetition"] == 1 and int(r["id"].split("-")[1]) < 15]
    inherited_keys = {r["bridge_task_key"] for r in inherited}
    invalid_keys = {f"val_r1_{c}--task-15" for c in summary.CONDITIONS}
    parent = campaign.parent/"parent"
    wave = campaign/"evaluation_attempts/wave-000"
    directories, mapping = {}, {}
    for row in rows:
        relative = Path("validation")/f"repeat_{row['repetition']}"/row["condition"]/row["id"]
        key = row["bridge_task_key"]
        if key in inherited_keys or key in invalid_keys:
            shutil.copytree(campaign/relative, parent/relative)
            if key in invalid_keys:
                result = summary.read_json(parent/relative/"result.json")
                write(parent/relative/"result.json", {**result, "fidelity": "V0_INVALID"})
        if key in inherited_keys:
            directories[key] = str(relative)
            owner = parent
        else:
            shutil.copytree(campaign/relative, wave/relative)
            owner = wave
        mapping[key] = {"ledger_path": str(owner/"provider_calls.jsonl"),
                        "result_path": str(owner/relative/"result.json"),
                        "result_sha256": summary.sha(owner/relative/"result.json")}
    all_records = [json.loads(x) for x in (campaign/"provider_calls.jsonl").read_text().splitlines()]
    parent_records, new_records = [], []
    for record in all_records:
        key = record["task_id"]
        if key in inherited_keys or key in invalid_keys:
            parent_records.append({**record, "request_id": "parent:"+key})
        if key not in inherited_keys:
            new_records.append({**record, "request_id": "new:"+key})
    parent_records += [
        {"request_id": "learning-006", "task_id": "cards-006", "attempts": [{"estimated_cost_usd": .7}]},
        {"request_id": "missing-parent-request", "task_id": "val_r1_initial--task-15",
         "attempts": [{"estimated_cost_usd": None, "usage": None, "error": "IncompleteRead"}]}]
    for owner, records in ((parent, parent_records), (wave, new_records), (campaign, new_records)):
        (owner/"provider_calls.jsonl").write_text("\n".join(map(json.dumps, records))+"\n")
    for entry in mapping.values():
        entry["ledger_sha256"] = summary.sha(Path(entry["ledger_path"]))
    write(parent/"cost_summary.json", {"recovery_parent_physical_cost_usd": 5.0})
    receipt = {"source_run": str(parent), "rows": inherited, "invalid_keys": sorted(invalid_keys),
               "result_directories": directories, "ledger_sha256": summary.sha(parent/"provider_calls.jsonl"),
               "preserved_hashes": {}, "runtime_hashes": {
                   str(p.relative_to(parent)): summary.sha(p) for p in parent.rglob("*") if p.is_file()},
               "review_sha256": "synthetic-reviewed-parent", "unknown_expense": {
                   "source_run": str(parent), "request_id": "missing-parent-request",
                   "unknown_expense_upper_usd": 1.90316544, "fee_status": "unresolved_not_zero"}}
    write(campaign/"recovered_evaluation.json", receipt)
    monkeypatch.setattr(summary, "audit_evaluation_parent", lambda actual: receipt if actual == parent else None)
    write(campaign/"evaluation_episode_sources.json", mapping)
    write(campaign/"physical_ledger_sources.json", [{"ledger_path": str(wave/"provider_calls.jsonl"),
                                                   "ledger_sha256": summary.sha(wave/"provider_calls.jsonl")}])
    selected = [r for r in parent_records if r.get("task_id") in inherited_keys]+new_records
    (campaign/"selected_episode_ledger.jsonl").write_text("\n".join(map(json.dumps, selected))+"\n")
    write(campaign/"cost_summary.json", {"expense_policy": "record_only", "invoice_final": False,
        "estimated_new_cost_usd": 20.0, "recovery_parent_physical_cost_usd": 18.5,
        "estimated_campaign_cost_including_parent_usd": 38.5,
        "approved_historical_unknown_expense_upper_usd": 1.90316544})
    return campaign, parent, wave, receipt


def rebind_wave(root, wave):
    records = [json.loads(x) for x in (wave/"provider_calls.jsonl").read_text().splitlines()]
    (root/"provider_calls.jsonl").write_text("\n".join(map(json.dumps, records))+"\n")
    digest = summary.sha(wave/"provider_calls.jsonl")
    write(root/"physical_ledger_sources.json", [{"ledger_path": str(wave/"provider_calls.jsonl"), "ledger_sha256": digest}])
    mapping = summary.read_json(root/"evaluation_episode_sources.json")
    for entry in mapping.values():
        if entry["ledger_path"] == str(wave/"provider_calls.jsonl"):
            entry["ledger_sha256"] = digest
    write(root/"evaluation_episode_sources.json", mapping)


def test_recovered_selected_metrics_preserve_60_parent_outcomes_and_physical_costs(recovered_campaign):
    root, parent, wave, _ = recovered_campaign
    report = summary.summarize(root)
    recovery = report["evaluation_recovery"]
    assert (recovery["recovered_outcomes"], recovery["new_selected_outcomes"]) == (60, 100)
    assert recovery["parent_all_physical"]["known_estimated_cost_usd"] == pytest.approx(13.5)
    assert recovery["child_all_physical"]["known_estimated_cost_usd"] == pytest.approx(20)
    assert recovery["selected_actor_metrics"]["known_estimated_cost_usd"] == pytest.approx(32)
    assert recovery["parent_excluded_from_actor_metrics"]["known_estimated_cost_usd"] == pytest.approx(1.5)
    assert recovery["parent_all_physical"]["unresolved_request_ids"] == ["missing-parent-request"]
    assert recovery["projection_is_derived_not_physical_billing"]
    assert report["conditions"]["native"]["late_dual_pass"] == 2
    assert report["primary_paired_augmented_minus_original_only"]["percentile_95_ci"] == [0, 0]
    runs = report["ledger_reconciliation"]["runs"]
    assert runs["val_r1_native--task-00"]["saved_fidelity"] == "V1_TRUNCATED"
    assert runs["val_r1_native--task-00"]["physical_episode_source"]["ledger_path"] == str(parent/"provider_calls.jsonl")
    assert runs["val_r1_native--task-15"]["physical_episode_source"]["ledger_path"] == str(wave/"provider_calls.jsonl")
    assert report["ledger_reconciliation"]["provider_fidelity_review_keys"] == []


@pytest.mark.parametrize("change", ["receipt", "source_ledger", "missing_clone", "changed_clone", "extra_clone"])
def test_recovered_receipt_and_full_episode_copy_are_bound(recovered_campaign, change):
    root, parent, _, _ = recovered_campaign
    clone = root/"validation/repeat_1/native/task-00"
    if change == "receipt":
        receipt = summary.read_json(root/"recovered_evaluation.json")
        write(root/"recovered_evaluation.json", {**receipt, "review_sha256": "changed"})
    elif change == "source_ledger":
        edit_ledger(parent, lambda records: records[0].update(upstream_model="changed"))
    elif change == "missing_clone": (clone/"run_manifest.json").unlink()
    elif change == "changed_clone": (clone/"run_manifest.json").write_text("{}\n")
    else: (clone/"extra.txt").write_text("not from parent\n")
    with pytest.raises((ValueError, OSError)):
        summary.summarize(root)


@pytest.mark.parametrize("change", ["missing", "orphan", "parent_owner", "new_owner", "result_hash", "result_path", "source_bytes"])
def test_selected_episode_provenance_is_complete_and_owner_bound(recovered_campaign, change):
    root, parent, wave, _ = recovered_campaign
    path = root/"evaluation_episode_sources.json"
    mapping = summary.read_json(path)
    old, new = "val_r1_native--task-00", "val_r1_native--task-15"
    if change == "missing": mapping.pop(old)
    elif change == "orphan": mapping["unknown"] = mapping[old]
    elif change == "parent_owner": mapping[old] = {**mapping[new]}
    elif change == "new_owner": mapping[new] = {**mapping[old]}
    elif change == "result_hash": mapping[new]["result_sha256"] = "changed"
    elif change == "result_path": mapping[new]["result_path"] = str(parent/"validation/repeat_1/native/task-15/result.json")
    else: (wave/"validation/repeat_1/native/task-15/extra.txt").write_text("not copied\n")
    write(path, mapping)
    with pytest.raises(ValueError):
        summary.summarize(root)


@pytest.mark.parametrize("change", ["selected_cost", "selected_missing", "selected_duplicate", "aggregate_cost", "source_hash", "duplicate_source"])
def test_selected_projection_and_physical_aggregate_cannot_be_fabricated(recovered_campaign, change):
    root, _, wave, _ = recovered_campaign
    path = root/"selected_episode_ledger.jsonl"
    if change.startswith("selected"):
        records = [json.loads(x) for x in path.read_text().splitlines()]
        if change == "selected_cost": records[0]["attempts"][0]["estimated_cost_usd"] = 0
        elif change == "selected_missing": records.pop()
        else: records.append(records[0])
        path.write_text("\n".join(map(json.dumps, records))+"\n")
    elif change == "aggregate_cost":
        edit_ledger(root, lambda records: records[0]["attempts"][0].update(estimated_cost_usd=0))
    else:
        physical = summary.read_json(root/"physical_ledger_sources.json")
        if change == "source_hash": physical[0]["ledger_sha256"] = "changed"
        else: physical.append(physical[0])
        write(root/"physical_ledger_sources.json", physical)
    with pytest.raises(ValueError):
        summary.summarize(root)


@pytest.mark.parametrize("change", ["orphan", "recovered_key", "parent_request"])
def test_new_physical_dispatch_cannot_repurchase_parent_or_add_orphan_keys(recovered_campaign, change):
    root, parent, wave, _ = recovered_campaign
    def extra(records):
        added = json.loads(json.dumps(records[0]))
        added["request_id"] = "extra-physical-request"
        if change == "orphan": added["task_id"] = "val_r1_other--unknown"
        elif change == "recovered_key": added["task_id"] = "val_r1_native--task-00"
        else: added["request_id"] = "parent:val_r1_native--task-00"
        records.append(added)
    edit_ledger(wave, extra)
    rebind_wave(root, wave)
    with pytest.raises(ValueError):
        summary.summarize(root)


def test_discarded_retry_fees_and_unknowns_remain_separate_from_selected_metrics(recovered_campaign):
    root, _, wave, _ = recovered_campaign
    rejected = root/"evaluation_attempts/wave-rejected"
    rejected.mkdir()
    records = [{"request_id": "failed-known", "task_id": "val_r1_native--task-15",
                "attempts": [{"estimated_cost_usd": .4}]},
               {"request_id": "failed-unknown", "task_id": "val_r1_initial--task-15",
                "attempts": [{"estimated_cost_usd": None, "usage": None, "error": "IncompleteRead"}]}]
    (rejected/"provider_calls.jsonl").write_text("\n".join(map(json.dumps, records))+"\n")
    physical = summary.read_json(root/"physical_ledger_sources.json")
    physical.append({"ledger_path": str(rejected/"provider_calls.jsonl"), "ledger_sha256": summary.sha(rejected/"provider_calls.jsonl")})
    write(root/"physical_ledger_sources.json", physical)
    current = (root/"provider_calls.jsonl").read_text()
    (root/"provider_calls.jsonl").write_text(current+"\n".join(map(json.dumps, records))+"\n")
    costs = summary.read_json(root/"cost_summary.json")
    write(root/"cost_summary.json", {**costs, "estimated_new_cost_usd": 20.4,
                                   "estimated_campaign_cost_including_parent_usd": 38.9})
    report = summary.summarize(root)
    recovery = report["evaluation_recovery"]
    assert recovery["child_all_physical"]["known_estimated_cost_usd"] == pytest.approx(20.4)
    assert recovery["child_excluded_from_actor_metrics"]["unresolved_request_ids"] == ["failed-unknown"]
    assert recovery["child_excluded_from_actor_metrics"]["known_estimated_cost_usd"] == .4
    assert recovery["selected_actor_metrics"]["known_estimated_cost_usd"] == pytest.approx(32)
    assert report["conditions"]["native"]["all_run_settled_ledger"]["estimated_actor_cost_usd"] == pytest.approx(8)


def test_recovery_cost_summary_must_count_all_physical_known_fees_once(recovered_campaign):
    root, _, _, _ = recovered_campaign
    costs = summary.read_json(root/"cost_summary.json")
    write(root/"cost_summary.json", {**costs, "estimated_new_cost_usd": 19.8})
    with pytest.raises(ValueError, match="Physical campaign cost"):
        summary.summarize(root)


def test_unknown_selected_episode_cost_is_not_allowed_as_zero(recovered_campaign):
    root, _, wave, _ = recovered_campaign
    def unknown(records):
        next(r for r in records if r["task_id"] == "val_r1_native--task-15")["attempts"][0]["estimated_cost_usd"] = None
    edit_ledger(wave, unknown)
    rebind_wave(root, wave)
    path = root/"selected_episode_ledger.jsonl"
    records = [json.loads(x) for x in path.read_text().splitlines()]
    unknown(records)
    path.write_text("\n".join(map(json.dumps, records))+"\n")
    costs = summary.read_json(root/"cost_summary.json")
    write(root/"cost_summary.json", {**costs, "estimated_new_cost_usd": 19.8,
                                   "estimated_campaign_cost_including_parent_usd": 38.3})
    with pytest.raises(ValueError, match="Unknown settled ledger cost"):
        summary.summarize(root)


def test_physical_source_cannot_escape_child_attempt_directory(recovered_campaign):
    root, parent, _, _ = recovered_campaign
    physical = summary.read_json(root/"physical_ledger_sources.json")
    physical.append({"ledger_path": str(parent/"provider_calls.jsonl"),
                     "ledger_sha256": summary.sha(parent/"provider_calls.jsonl")})
    write(root/"physical_ledger_sources.json", physical)
    with pytest.raises(ValueError, match="physical ledger source"):
        summary.summarize(root)


def test_orphan_parent_ledger_task_is_not_silently_filtered(recovered_campaign):
    root, parent, _, receipt = recovered_campaign
    def orphan(records):
        extra = json.loads(json.dumps(records[0]))
        extra.update(request_id="parent-orphan", task_id="val_r1_other--unknown")
        records.append(extra)
    edit_ledger(parent, orphan)
    receipt["ledger_sha256"] = summary.sha(parent/"provider_calls.jsonl")
    receipt["runtime_hashes"]["provider_calls.jsonl"] = receipt["ledger_sha256"]
    write(root/"recovered_evaluation.json", receipt)
    with pytest.raises(ValueError, match="Orphan parent"):
        summary.summarize(root)


def test_unbound_parent_episode_file_cannot_be_added_to_both_copies(recovered_campaign):
    root, parent, _, _ = recovered_campaign
    relative = "validation/repeat_1/native/task-00/extra.txt"
    (root/relative).write_text("same forged addition\n")
    (parent/relative).write_text("same forged addition\n")
    with pytest.raises(ValueError, match="Unbound recovered episode"):
        summary.summarize(root)
