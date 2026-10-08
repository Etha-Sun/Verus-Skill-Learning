#!/usr/bin/env python3
"""Audit completed outputs and replay-copy hashes without loading benchmark sources."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics


CONDITIONS = ("initial", "native", "original_only", "augmented")
BOOTSTRAP_SEED = 20261006
BOOTSTRAP_SAMPLES = 10000
LEDGER_FIELDS = ("requests", "metered_requests", "completed_requests", "incomplete_requests",
                 "error_requests", "unknown_status_requests", "unknown_cost_requests", "prompt_tokens", "completion_tokens",
                 "prompt_cache_hit_tokens", "prompt_cache_miss_tokens", "reasoning_tokens", "estimated_cost_usd")


def read_json(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def approved_child(path):
    path = Path(path).resolve()
    approved = Path(os.environ["VERUS_SKILL_RUN_ROOT"]).resolve()
    repo = Path(__file__).resolve().parents[1]
    if approved not in path.parents or path == repo or repo in path.parents:
        raise ValueError("Path must be an approved external run-root child")
    return path


def artifact_sha(path):
    if path.is_symlink():
        raise ValueError("Symlink artifact")
    if path.is_file():
        return sha(path)
    if not path.is_dir():
        raise ValueError("Artifact must be a file or directory")
    digest = hashlib.sha256()
    for child in sorted(path.rglob("*")):
        if child.is_symlink() or not (child.is_file() or child.is_dir()):
            raise ValueError("Unsafe artifact entry")
        if child.is_file():
            relative = child.relative_to(path).as_posix().encode()
            content = child.read_bytes()
            digest.update(len(relative).to_bytes(8, "big")); digest.update(relative)
            digest.update(len(content).to_bytes(8, "big")); digest.update(content)
    return digest.hexdigest()


def admit_review(root):
    evidence = {"frozen_artifacts_sha256": sha(root/"frozen_artifacts.json"),
                "banks": {c: sha(root/"banks"/c/"cards.json")
                          for c in ("original_only", "augmented")}}
    receipt = read_json(root/"artifact_review.json")
    if (read_json(root/"artifact_quality_evidence.json") != evidence
            or receipt.get("accepted") is not True
            or receipt.get("evidence_sha256") != json_sha(evidence)
            or not isinstance(receipt.get("observations"), str)
            or not receipt["observations"].strip()):
        raise ValueError("Accepted frozen artifact review required before result access")
    frozen = read_json(root/"frozen_artifacts.json")
    if set(frozen) != set(CONDITIONS):
        raise ValueError("Frozen condition mismatch")
    for entry in frozen.values():
        path = Path(entry["path"])
        if not path.exists() or artifact_sha(path) != entry["artifact_sha256"]:
            raise ValueError("Frozen artifact changed")
    return evidence, frozen


def valid_solved(row):
    return bool(row.get("hard")) and row.get("fidelity") != "V0_INVALID" and "runner_error" not in row


def solved(row):
    return valid_solved(row) and bool(row.get("within_budget"))


def measurements(rows, settled_usage=None):
    totals = dict.fromkeys(("prompt_tokens", "completion_tokens", "estimated_actor_cost_usd",
                           "actor_wall_seconds", "final_validation_wall_seconds", "wall_seconds"), 0)
    for row in rows:
        usage = (settled_usage[row["bridge_task_key"]] if settled_usage is not None else row.get("usage") or {})
        for key in totals:
            source = usage if key in ("prompt_tokens", "completion_tokens", "estimated_actor_cost_usd") else row
            field = "estimated_cost_usd" if key == "estimated_actor_cost_usd" else key
            value = source.get(field)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("Missing or invalid measurement: " + field)
            totals[key] += value
    return totals


def audit_evaluation_parent(parent):
    from skillopt_verusage.evaluation_recovery import audit_parent
    return audit_parent(parent)


def ledger_records(path, expected_sha=None):
    before = sha(path)
    if expected_sha is not None and before != expected_sha:
        raise ValueError("Evaluation source ledger hash changed")
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if sha(path) != before:
        raise ValueError("Provider ledger changed during reporting")
    return records, before


def request_index(records):
    indexed = {}
    for record in records:
        request = record.get("request_id")
        if not request or request in indexed:
            raise ValueError("Missing or duplicate physical ledger request")
        if not isinstance(record.get("attempts"), list) or not record["attempts"]:
            raise ValueError("Missing settled ledger attempts")
        indexed[request] = record
    return indexed


def identical_episode(source, target, hashes=None, parent=None):
    files = {}
    for directory in (source, target):
        entries = list(directory.rglob("*"))
        if not directory.is_dir() or any(p.is_symlink() for p in entries):
            raise ValueError("Unsafe recovered episode directory")
        files[directory] = {str(p.relative_to(directory)): p for p in entries if p.is_file()}
    if set(files[source]) != set(files[target]):
        raise ValueError("Recovered episode file set changed")
    for name, original in files[source].items():
        original_sha = sha(original)
        if hashes is not None and hashes.get(str(original.relative_to(parent))) != original_sha:
            raise ValueError("Unbound recovered episode file")
        if sha(files[target][name]) != original_sha:
            raise ValueError("Recovered episode bytes changed")


def evaluation_recovery_sources(root, rows):
    """Bind selected episodes to real immutable ledgers; never treat a projection as billing."""
    receipt_path = root/"recovered_evaluation.json"
    receipt = read_json(receipt_path)
    parent = approved_child(receipt["source_run"])
    if parent == root or receipt != audit_evaluation_parent(parent):
        raise ValueError("Recovered evaluation receipt changed")
    inherited = {r["bridge_task_key"]: r for r in receipt["rows"]}
    by_key = {r["bridge_task_key"]: r for r in rows}
    if len(inherited) != 60 or not set(inherited) <= set(by_key):
        raise ValueError("Expected sixty recovered evaluation outcomes")
    hashes = {**receipt["preserved_hashes"], **receipt["runtime_hashes"]}
    for key, row in inherited.items():
        if row != by_key[key]:
            raise ValueError("Recovered evaluation outcome changed")
        relative = Path(receipt["result_directories"][key])
        expected = Path("validation")/f"repeat_{row['repetition']}"/row["condition"]/row["id"]
        if relative != expected:
            raise ValueError("Recovered episode path mismatch")
        identical_episode(parent/relative, root/relative, hashes, parent)
    parent_path = parent/"provider_calls.jsonl"
    parent_records, parent_sha = ledger_records(parent_path, receipt["ledger_sha256"])
    parent_index = request_index(parent_records)
    invalid = set(receipt["invalid_keys"])
    if any(str(r.get("task_id")).startswith("val_r") and r["task_id"] not in set(inherited)|invalid
           for r in parent_records):
        raise ValueError("Orphan parent evaluation ledger task")
    physical_path = root/"physical_ledger_sources.json"
    physical = read_json(physical_path)
    sources = {str(parent_path): (parent_records, parent_sha)}
    current_records = []
    for entry in physical:
        path = approved_child(entry["ledger_path"])
        if root/"evaluation_attempts" not in path.parents or path.name != "provider_calls.jsonl" or str(path) in sources:
            raise ValueError("Unsafe or duplicate physical ledger source")
        records, digest = ledger_records(path, entry["ledger_sha256"])
        sources[str(path)] = (records, digest)
        current_records.extend(records)
    current_index = request_index(current_records)
    if set(current_index)&set(parent_index):
        raise ValueError("Physical request copied across evaluation owners")
    aggregate, aggregate_sha = ledger_records(root/"provider_calls.jsonl")
    if request_index(aggregate) != current_index:
        raise ValueError("Physical ledger aggregate disagrees with immutable sources")
    map_path = root/"evaluation_episode_sources.json"
    mapping = read_json(map_path)
    if set(mapping) != set(by_key):
        raise ValueError("Incomplete or orphan evaluation episode source map")
    if any(r.get("task_id") not in by_key for r in current_records):
        raise ValueError("Orphan child physical evaluation ledger task")
    selected, provenance = [], {}
    for key, entry in mapping.items():
        if set(entry) != {"ledger_path", "ledger_sha256", "result_path", "result_sha256"}:
            raise ValueError("Evaluation episode source fields changed")
        owner = str(Path(entry["ledger_path"]).resolve())
        if owner not in sources or entry["ledger_sha256"] != sources[owner][1]:
            raise ValueError("Unbound evaluation episode ledger owner")
        if (key in inherited) != (owner == str(parent_path)):
            raise ValueError("Recovered evaluation ledger ownership changed")
        row = by_key[key]
        directory = root/"validation"/f"repeat_{row['repetition']}"/row["condition"]/row["id"]
        result_path = approved_child(entry["result_path"])
        source_root = parent if key in inherited else Path(owner).parent
        relative = directory.relative_to(root)
        if result_path != source_root/relative/"result.json":
            raise ValueError("Evaluation physical episode result path changed")
        if entry["result_sha256"] != sha(result_path) or entry["result_sha256"] != sha(directory/"result.json"):
            raise ValueError("Evaluation source result hash changed")
        if key not in inherited:
            identical_episode(result_path.parent, directory)
        records = [r for r in sources[owner][0] if r.get("task_id") == key]
        if not records:
            raise ValueError("Missing selected evaluation source ledger task")
        selected.extend(records)
        provenance[key] = {"ledger_path": owner, "ledger_sha256": sources[owner][1],
                           "result_path": str(result_path), "result_sha256": entry["result_sha256"],
                           "physical_request_ids": [r["request_id"] for r in records]}
    if any(r.get("task_id") in inherited for r in current_records):
        raise ValueError("Recovered evaluation key dispatched again")
    projection_path = root/"selected_episode_ledger.jsonl"
    projection, projection_sha = ledger_records(projection_path)
    if request_index(projection) != request_index(selected):
        raise ValueError("Selected episode ledger projection changed")
    def expense(records):
        known, unknown = 0, []
        for record in records:
            for attempt in record["attempts"]:
                value = attempt.get("estimated_cost_usd")
                if value is None:
                    unknown.append(record["request_id"])
                elif not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError("Invalid physical ledger expense")
                else:
                    known += value
        return {"known_estimated_cost_usd": known, "physical_requests": len(records),
                "unresolved_request_ids": sorted(set(unknown))}
    parent_expense, current_expense = expense(parent_records), expense(current_records)
    costs = read_json(root/"cost_summary.json")
    previous = read_json(parent/"cost_summary.json")
    parent_known = previous["recovery_parent_physical_cost_usd"] + parent_expense["known_estimated_cost_usd"]
    expected_costs = {"estimated_new_cost_usd": current_expense["known_estimated_cost_usd"],
                      "recovery_parent_physical_cost_usd": parent_known,
                      "estimated_campaign_cost_including_parent_usd": parent_known + current_expense["known_estimated_cost_usd"]}
    if (costs.get("expense_policy") != "record_only" or costs.get("invoice_final") is not False
            or any(not isinstance(costs.get(k), (int, float)) or not math.isfinite(costs[k])
                   or not math.isclose(costs[k], v, rel_tol=1e-10, abs_tol=1e-10) for k, v in expected_costs.items())):
        raise ValueError("Physical campaign cost summary disagrees with ledgers")
    selected_ids = {r["request_id"] for r in selected}
    return projection_path, provenance, {
        "recovered_evaluation_sha256": sha(receipt_path), "source_run": str(parent),
        "source_review_sha256": receipt["review_sha256"], "source_ledger_sha256": parent_sha,
        "source_map_sha256": sha(map_path), "physical_sources_sha256": sha(physical_path),
        "selected_episode_ledger_sha256": projection_sha, "provider_ledger_sha256": aggregate_sha,
        "recovered_outcomes": 60, "new_selected_outcomes": len(rows)-60,
        "parent_all_physical": parent_expense, "child_all_physical": current_expense,
        "selected_actor_metrics": expense(selected),
        "parent_excluded_from_actor_metrics": expense([r for r in parent_records if r["request_id"] not in selected_ids]),
        "child_excluded_from_actor_metrics": expense([r for r in current_records if r["request_id"] not in selected_ids]),
        "parent_unknown_expense": receipt["unknown_expense"],
        "cost_summary": costs, "cost_summary_sha256": sha(root/"cost_summary.json"),
        "excluded_parent_invalid_keys": sorted(invalid), "projection_is_derived_not_physical_billing": True}


def reconcile_ledger(root, rows, ledger_path=None):
    """Keep original snapshots; late responses affect paid usage, not saved outcomes."""
    path = ledger_path or root/"provider_calls.jsonl"
    ledger_sha = sha(path)
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if sha(path) != ledger_sha:
        raise ValueError("Provider ledger changed during reporting")
    by_key = {row["bridge_task_key"]: dict.fromkeys(LEDGER_FIELDS, 0) for row in rows}
    models = {key: set() for key in by_key}
    seen_requests = set()
    for record in records:
        request = record.get("request_id")
        if not request or request in seen_requests:
            raise ValueError("Missing or duplicate physical ledger request")
        seen_requests.add(request)
        attempts = record.get("attempts")
        if not isinstance(attempts, list) or not attempts:
            raise ValueError("Missing settled ledger attempts")
        key = record.get("task_id")
        if str(key).startswith("val_r") and key not in by_key:
            raise ValueError("Unmatched evaluation ledger task")
        for attempt in attempts:
            cost = attempt.get("estimated_cost_usd")
            if not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
                raise ValueError("Unknown settled ledger cost")
            if key not in by_key:
                continue
            usage = attempt.get("usage")
            if not isinstance(usage, dict):
                raise ValueError("Unmetered settled evaluation attempt")
            totals = by_key[key]
            totals["requests"] += 1
            totals["metered_requests"] += 1
            status = attempt.get("finish_reason")
            totals[(status+"_requests") if status in ("completed", "incomplete") else "unknown_status_requests"] += 1
            totals["error_requests"] += bool(attempt.get("error"))
            totals["estimated_cost_usd"] += cost
            for field in ("prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens", "reasoning_tokens"):
                value = usage.get(field, None if field in ("prompt_tokens", "completion_tokens") else 0)
                if not isinstance(value, int) or value < 0:
                    raise ValueError("Missing or invalid settled ledger tokens")
                totals[field] += value
            if record.get("upstream_model"):
                models[key].add(record["upstream_model"])
    reconciliation = {}
    for row in rows:
        key = row["bridge_task_key"]
        settled = by_key[key]
        if not settled["requests"]:
            raise ValueError("Missing evaluation actor ledger usage")
        snapshot = row["usage"]
        difference = {field: settled[field]-snapshot.get(field, 0) for field in LEDGER_FIELDS}
        if math.isclose(difference["estimated_cost_usd"], 0, abs_tol=1e-12):
            difference["estimated_cost_usd"] = 0
        model_changed = models[key] != set(snapshot.get("upstream_models", []))
        provider_valid = (settled["completed_requests"] > 0 and not settled["error_requests"]
                          and not settled["unknown_status_requests"] and bool(models[key])
                          and all(model.strip().lower().replace("_", "-") == "deepseek-v4-pro" for model in models[key]))
        settled["upstream_models"] = sorted(models[key])
        reconciliation[key] = {"snapshot_usage": snapshot, "settled_ledger_usage": settled,
                               "settled_minus_snapshot": difference,
                               "usage_mismatch": any(difference.values()) or model_changed,
                               "provider_review_needed": provider_valid != row.get("provider_valid") or model_changed or bool(snapshot.get("unknown_cost_requests")),
                               "saved_fidelity": row.get("fidelity"), "outcomes_not_reclassified": True}
    return by_key, {"provider_ledger_sha256": ledger_sha,
                    "mismatched_runs": sum(x["usage_mismatch"] for x in reconciliation.values()),
                    "provider_fidelity_review_keys": [key for key, value in reconciliation.items() if value["provider_review_needed"]],
                    "runs": reconciliation}


def percentile(values, probability):
    position = (len(values)-1)*probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper]-values[lower])*(position-lower)


def task_bootstrap(deltas):
    values = [deltas[key] for key in sorted(deltas)]
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(statistics.mean(rng.choices(values, k=len(values)))
                     for _ in range(BOOTSTRAP_SAMPLES))
    return {"mean_delta": statistics.mean(values),
            "percentile_95_ci": [percentile(samples, .025), percentile(samples, .975)],
            "independent_tasks": len(values), "samples": BOOTSTRAP_SAMPLES,
            "seed": BOOTSTRAP_SEED, "unit": "task; both repetitions retained together"}


def summarize(root):
    root = approved_child(root)
    evidence, frozen = admit_review(root)
    progress = read_json(root/"progress.json")
    if progress.get("phase") != "complete" or progress.get("evaluation_completed") != 160:
        raise ValueError("Completed drained campaign required for settled ledger reporting")
    schedule = read_json(root/"evaluation_schedule.json")
    if schedule.get("frozen_artifacts_sha256") != evidence["frozen_artifacts_sha256"] or schedule.get("test_accessed") is not False:
        raise ValueError("Evaluation schedule binding mismatch")
    expected = [(condition, item["id"], repeat+1)
                for block in schedule["blocks"] for repeat, condition, item in block]
    ids = sorted({ident for _, ident, _ in expected})
    if any(not ident or ident in (".", "..") or Path(ident).name != ident for ident in ids):
        raise ValueError("Unsafe task identifier")
    required = {(c, ident, r) for c in CONDITIONS for ident in ids for r in (1, 2)}
    if len(ids) != 20 or len(expected) != 160 or len(set(expected)) != 160 or set(expected) != required:
        raise ValueError("Expected four conditions, twenty tasks and two repetitions")
    rows = read_json(root/"validation_rows.json")
    keys = [(r["condition"], r["id"], r["repetition"]) for r in rows]
    if len(keys) != 160 or len(set(keys)) != 160 or set(keys) != required:
        raise ValueError("Incomplete or duplicate evaluation rows")
    indexed, audits, bindings = {}, {}, {}
    for row, key in zip(rows, keys):
        condition, ident, repeat = key
        directory = root/"validation"/f"repeat_{repeat}"/condition/ident
        result = read_json(directory/"result.json")
        if {k: v for k, v in row.items() if k not in ("condition", "repetition")} != result:
            raise ValueError("Result disagrees with validation rows")
        if (row.get("actor_model") != "deepseek-v4-pro" or row.get("actor_reasoning_effort") != "max"
                or row.get("skill_sha256") != frozen[condition]["artifact_sha256"]):
            raise ValueError("Actor model or frozen skill mismatch")
        if row.get("bridge_task_key") != f"val_r{repeat}_{condition}--{ident}":
            raise ValueError("Evaluation bridge task key mismatch")
        manifest = read_json(directory/"run_manifest.json")
        if (manifest.get("model") != "deepseek-v4-pro" or manifest.get("reasoning_effort") != "max"
                or manifest.get("timeout_seconds") != 600
                or manifest.get("condition_skill_sha256") != row["skill_sha256"]):
            raise ValueError("Evaluation runtime contract mismatch")
        audit = read_json(directory/"retrieval_audit.json")
        if audit.get("audit_incomplete"):
            raise ValueError("Retrieval audit incomplete")
        reads = [e for e in audit["events"] if e.get("operation") == "read" and "content" in e]
        searches = [e for e in audit["events"] if e.get("operation") == "search"]
        if (audit["read_calls"] != len(reads) or audit["search_calls"] != len(searches)
                or audit["read_ids"] != sorted({e["id"] for e in reads})):
            raise ValueError("Retrieval counters disagree with events")
        indexed[key], audits[key] = row, audit
        bindings[str(directory.relative_to(root))] = {"result_sha256": sha(directory/"result.json"),
                                                     "run_manifest_sha256": sha(directory/"run_manifest.json"),
                                                     "retrieval_audit_sha256": sha(directory/"retrieval_audit.json")}
    recovery = None
    if (root/"recovered_evaluation.json").exists():
        ledger_path, provenance, recovery = evaluation_recovery_sources(root, rows)
        settled_usage, reconciliation = reconcile_ledger(root, rows, ledger_path)
        reconciliation["selected_episode_ledger_sha256"] = reconciliation["provider_ledger_sha256"]
        reconciliation["provider_ledger_sha256"] = recovery["provider_ledger_sha256"]
        for key, source in provenance.items():
            reconciliation["runs"][key]["physical_episode_source"] = source
    else:
        settled_usage, reconciliation = reconcile_ledger(root, rows)
    conditions = {}
    for condition in CONDITIONS:
        selected = [indexed[(condition, ident, r)] for ident in ids for r in (1, 2)]
        selected_audits = [audits[(condition, ident, r)] for ident in ids for r in (1, 2)]
        histogram = Counter(sum(solved(indexed[(condition, ident, r)]) for r in (1, 2)) for ident in ids)
        conditions[condition] = {
            "task_n": 20, "run_n": 40, "within_budget_solved": sum(map(solved, selected)),
            "dual_pass_including_late": sum(map(valid_solved, selected)),
            "late_dual_pass": sum(valid_solved(x) and not x.get("within_budget") for x in selected),
            "timeouts": sum(bool(x.get("timed_out")) for x in selected),
            "invalid": sum(x.get("fidelity") == "V0_INVALID" or "runner_error" in x for x in selected),
            "task_success_histogram": {str(n): histogram[n] for n in (0, 1, 2)},
            "repetitions": {str(r): {"run_n": 20, "within_budget_solved": sum(solved(indexed[(condition, ident, r)]) for ident in ids)} for r in (1, 2)},
            "all_run": measurements(selected),
            "snapshot_unknown_cost_requests": sum(x["usage"].get("unknown_cost_requests", 0) for x in selected),
            "all_run_settled_ledger": measurements(selected, settled_usage),
            "retrieval_exposure": {
                "runs_with_reads": sum(a["read_calls"] > 0 for a in selected_audits),
                "read_calls": sum(a["read_calls"] for a in selected_audits),
                "search_calls": sum(a["search_calls"] for a in selected_audits),
                "distinct_card_ids": sorted({card for a in selected_audits for card in a["read_ids"]}),
                "runs_with_direct_bank_access": sum(bool(a.get("direct_bank_access_commands")) for a in selected_audits),
                "direct_bank_access_commands": sum(len(a.get("direct_bank_access_commands", [])) for a in selected_audits)}}
    deltas = {ident: statistics.mean(int(solved(indexed[("augmented", ident, r)]))
                                   - int(solved(indexed[("original_only", ident, r)])) for r in (1, 2)) for ident in ids}
    joint = [(indexed[("original_only", ident, r)], indexed[("augmented", ident, r)])
             for ident in ids for r in (1, 2)
             if solved(indexed[("original_only", ident, r)]) and solved(indexed[("augmented", ident, r)])]
    return {"schema_version": "hindsight-campaign-summary-v1", "conditions": conditions,
            "outcome_metrics_status": "requires_provider_fidelity_review" if reconciliation["provider_fidelity_review_keys"] else "saved_classifications_retained",
            "primary_paired_augmented_minus_original_only": {**task_bootstrap(deltas), "per_task_delta": deltas},
            "joint_success_augmented_vs_original_only": {"paired_runs": len(joint),
                "task_n": len({a["id"] for a, _ in joint}),
                "original_only": measurements([a for a, _ in joint]),
                "augmented": measurements([b for _, b in joint]),
                "original_only_settled_ledger": measurements([a for a, _ in joint], settled_usage),
                "augmented_settled_ledger": measurements([b for _, b in joint], settled_usage)},
            "ledger_reconciliation": reconciliation,
            "evaluation_recovery": recovery,
            "evidence": {"frozen_review": evidence, "validation_rows_sha256": sha(root/"validation_rows.json"),
                         "reporter_sha256": sha(Path(__file__)),
                         "provider_ledger_sha256": reconciliation["provider_ledger_sha256"],
                         "evaluation_schedule_sha256": sha(root/"evaluation_schedule.json"), "outputs": bindings},
            "caveats": ["20 independent tasks, not 40 independent trials; bootstrap retains both repetitions.",
                "Bootstrap CI describes validation tasks only, not sealed-test generalization.",
                "Joint-success costs condition on both methods solving; read with all-run outcomes.",
                "Lower failed-run cost/token/time does not demonstrate efficiency improvement.",
                "600s is actor search budget; independent final validation and termination grace add wall time.",
                "Within-budget success uses the saved episode timeout flag, not the first intermediate verifier pass.",
                "Summed per-run wall times are not elapsed campaign time under concurrent execution.",
                "Actor costs exclude training, recovery and historical original costs; ledger estimates are not invoices.",
                "Recovered actor metrics select one valid physical episode per logical key; rejected transport episodes remain in separate physical expenses.",
                "all_run and joint original_only/augmented retain result usage snapshots; settled_ledger fields are authoritative paid usage.",
                "Snapshot costs can be partial when snapshot_unknown_cost_requests is positive; only final known ledger costs are authoritative.",
                "Late upstream outputs can add paid tokens the actor never consumed; usage mismatches do not establish efficiency or change outcomes.",
                "Provider-validity or model differences require root fidelity review; saved classifications are never rewritten.",
                "Retrieval counters measure exposure, not correct application or causal benefit.",
                "Direct filesystem reads can bypass retrieval counters; flagged commands are not exhaustive."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = approved_child(args.run_root)
    destination = approved_child(args.output_dir or root/"analysis/hindsight-summary")
    if destination.exists():
        raise ValueError("Refusing to overwrite summary output")
    result = summarize(root)
    destination.mkdir(parents=True)
    (destination/"summary.json").write_text(json.dumps(result, indent=2)+"\n")
    print(destination/"summary.json")


if __name__ == "__main__":
    main()
