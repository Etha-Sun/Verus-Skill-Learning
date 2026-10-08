#!/usr/bin/env python3
"""Offline train-trace progress statistics and case-study evidence, without inference."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import traceback

from skillopt_verusage.campaign_evidence import analyze_progress, load_trace
from verus_self_evolve.proof_progress import function_body, load_jsonl, greedy_prune_proof_lines, stagnation_segments
from verus_self_evolve.proof_dependencies import compiler_functions, proof_scope
from verus_self_evolve.trajectory_progress import verifier_state
from verus_self_evolve.trajectory_progress import normalize_code_lines


# Reviewed against the unchanged fixed training inputs, not inferred from filenames.
TARGET_OVERRIDES = {
    "5b577761f2b5267cf0c4": ("invariants_since_phase_ii_is_stable", 0),
    "5f3fbbb9f3042f601f15": ("invariants_since_phase_iii_is_stable", 0),
    "4ed253b9f6582520b718": ("invariants_since_phase_i_is_stable", 0),
    "46f4d879d37da0eb8835": ("lemma_from_pending_req_in_flight_or_resp_in_flight_at_all_delete_to_delete_n", 0),
    "0a8794c662f44dedfa7f": ("sht_marshal_data_injective", 0),
    "3d762c82c4ba18b0c1b6": ("remove", 0),
    "e9a2851a9535ba78c7e6": ("deserialize", 8),
    "0e4238ecd50d3918b7fb": ("lemma_serialize_injective", 4),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def write_csv(path, rows):
    columns = list(rows[0]) if rows else ["task_id"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def diagnostic_signature(output):
    text = re.sub(r"(?:/[^\s:]+)?candidate\.rs", "candidate.rs", output)
    text = re.sub(r"\b\d+:\d+\b", "<location>", text)
    text = re.sub(r"(?m)^\s*\d+\s*\|", " |", text)
    return hashlib.sha256(text.encode()).hexdigest()


def segments(curve, predicate):
    result = []
    for left, right in zip(curve, curve[1:]):
        if right["cumulative_output_tokens"] <= left["cumulative_output_tokens"] or not predicate(left, right):
            continue
        if result and result[-1]["end_call"] == left["call_ordinal"]:
            row = result[-1]
            row["end_call"] = right["call_ordinal"]
            row["end_output_tokens"] = right["cumulative_output_tokens"]
        else:
            row = {"start_call": left["call_ordinal"], "end_call": right["call_ordinal"],
                   "start_output_tokens": left["cumulative_output_tokens"],
                   "end_output_tokens": right["cumulative_output_tokens"]}
            result.append(row)
        row["output_token_delta"] = row["end_output_tokens"] - row["start_output_tokens"]
    return result


def enrich(report, snapshots, name, occurrence):
    curve = report["curve"]
    for row in curve:
        body = (function_body(snapshots[row["candidate_sha256"]], name, occurrence=occurrence)
                if row.get("target_proof_coverage", row["proof_coverage"]) is not None else None)
        row["target_body_sha256"] = hashlib.sha256(body.encode()).hexdigest() if body is not None else None
        row["diagnostic_signature"] = diagnostic_signature(row["verifier_output"])
    first_pass = next((r["call_ordinal"] for r in curve if r["verifier_tier"] == 2
                       and r.get("target_proof_coverage", r["proof_coverage"]) is not None), len(curve) + 1)
    report["first_verified_call"] = first_pass if first_pass <= len(curve) else None
    report["coverage_only_platforms"] = segments(curve, lambda a, b:
        a["call_ordinal"] < first_pass and b["call_ordinal"] < first_pass
        and a["proof_coverage"] is not None and b["proof_coverage"] is not None
        and abs(a["proof_coverage"] - b["proof_coverage"]) < 1e-12)
    report["repeated_diagnostic_spans"] = segments(curve, lambda a, b:
        a["call_ordinal"] < first_pass and b["call_ordinal"] < first_pass
        and a["diagnostic_signature"] == b["diagnostic_signature"])
    report["transitions"] = []
    for left, right in zip(curve, curve[1:]):
        known = left["proof_coverage"] is not None and right["proof_coverage"] is not None
        same_coverage = known and abs(left["proof_coverage"] - right["proof_coverage"]) < 1e-12
        errors_left, errors_right = left["verifier"]["reported_errors"], right["verifier"]["reported_errors"]
        report["transitions"].append({
            "from_call": left["call_ordinal"], "to_call": right["call_ordinal"],
            "output_token_delta": right["cumulative_output_tokens"] - left["cumulative_output_tokens"],
            "before_first_pass": left["call_ordinal"] < first_pass,
            "coverage_delta": right["proof_coverage"] - left["proof_coverage"] if known else None,
            "tier_delta": right["verifier_tier"] - left["verifier_tier"],
            "target_body_changed": left["target_body_sha256"] != right["target_body_sha256"],
            "candidate_changed": left["candidate_sha256"] != right["candidate_sha256"],
            "diagnostic_changed": left["diagnostic_signature"] != right["diagnostic_signature"],
            "flat_coverage_but_fewer_errors": same_coverage and errors_left is not None
                and errors_right is not None and errors_right < errors_left,
        })
    return report


def summarize(item, report):
    platforms = report["stagnation_segments"]
    tokens = sorted((s["output_token_delta"] for s in platforms), reverse=True)
    transitions = report["transitions"]
    row = {"id": item["id"], "task_id": item["task_id"], "project": item["project_code"],
            "reference_kind": report["reference_kind"],
            "function": report["function_name"], "occurrence": report["function_occurrence"],
            "verifier_calls": len(report["curve"]), "total_output_tokens": report["total_output_tokens"],
            "platform_count": len(platforms), "platform_tokens_total": sum(tokens),
            "platform_tokens_max": max(tokens, default=0),
            "top3_platform_tokens": ";".join(map(str, tokens[:3])),
            "coverage_only_platform_count": len(report["coverage_only_platforms"]),
            "regression_count": len(report["regression_transitions"]),
            "coverage_drop_count": sum(t["coverage_delta"] is not None and t["coverage_delta"] < 0 for t in transitions),
            "tier_drop_count": sum(t["coverage_delta"] is not None and t["tier_delta"] < 0 for t in transitions),
            "coverage_unavailable_calls": sum(r["proof_coverage"] is None for r in report["curve"]),
            "flat_with_error_improvement_count": sum(t["flat_coverage_but_fewer_errors"] for t in transitions),
            "flat_with_target_change_count": sum(t["coverage_delta"] is not None and abs(t["coverage_delta"]) < 1e-12 and t["target_body_changed"]
                                                   and t["before_first_pass"] for t in transitions),
            "repeated_diagnostic_span_count": len(report["repeated_diagnostic_spans"]),
            "pruned_lines": report["pruning"]["summary"]["removed_lines"],
            "pruning_verifier_trials": report["pruning"]["summary"]["verifier_trials"]}
    if "helper_scope" in report:
        first = report["first_verified_call"] or len(report["curve"]) + 1
        row.update({"related_helper_count": len(report["helper_scope"]["components"]) - 1,
                    "excluded_changed_helper_count": len(report["helper_scope"]["excluded_changed_proofs"]),
                    "paired_target_platform_count": sum(s["start_call"] < first for s in report["target_only_platforms"]),
                    "paired_target_coverage_only_platform_count": len(report["target_only_coverage_platforms"]),
                    "target_flat_helper_gain_transitions": sum(t["target_flat_helper_gain"] for t in transitions)})
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--verus-bin", required=True, type=Path)
    parser.add_argument("--lynette-bin", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--verifier-timeout-seconds", type=int, default=30)
    parser.add_argument("--reference-only", action="store_true",
                        help="Explicitly use the verified unpruned final; not a completed pruning result")
    parser.add_argument("--parent-report-root", type=Path,
                        help="Reviewed consolidation whose hash-bound references can be reused")
    parser.add_argument("--include-helpers", action="store_true")
    args = parser.parse_args()
    if args.include_helpers and (not args.parent_report_root or args.reference_only):
        raise ValueError("Helper reanalysis requires reviewed parent references, not reference-only mode")
    repo = Path(__file__).resolve().parents[1]
    root, source_root = args.output_dir.resolve(), args.source_root.resolve()
    if root == args.run_root.resolve() or args.run_root.resolve() not in root.parents:
        raise ValueError("Output must be below the approved external run root")
    if source_root == root or source_root in root.parents or repo in root.parents:
        raise ValueError("Output must not be inside source evidence or repository")
    if not root.is_dir() or any(root.iterdir()):
        raise ValueError("Output must be a fresh, empty directory")
    started = time.monotonic()
    manifest_path = repo / "fixed-claude-stratified-80-seed20260814/train/items.json"
    source_manifest = json.loads((source_root / "run_manifest.json").read_text())
    if sha(manifest_path) != source_manifest["train_manifest_sha256"]:
        raise ValueError("Training manifest identity mismatch")
    items = json.loads(manifest_path.read_text())
    ledger_path = source_root / "bridge_calls.jsonl"
    ledger = load_jsonl(ledger_path)
    sources, skipped = [], []
    for item in items:
        directory = source_root / "rollout/predictions" / item["id"]
        result = json.loads((directory / "result.json").read_text())
        if sha(directory / "workspace/input.rs") != item["source_sha256"]:
            raise ValueError("Original input hash mismatch")
        if result["source_sha256"] != item["source_sha256"] or result["skill_sha256"] != source_manifest["skill_sha256"]:
            raise ValueError("Source/skill contract mismatch")
        if not result["hard"]:
            skipped.append({"id": item["id"], "task_id": item["task_id"], "status": "no_verified_reference"})
            continue
        if not result["safety_passed"] or result["fidelity"] != "V2_TRACE":
            raise ValueError("Solved source failed safety/trace contract")
        sources.append(item)
    if len(sources) != 39 or len(skipped) != 1:
        raise ValueError("Expected the reviewed 39 solved originals and one unsolved original")
    if args.task_id:
        if not set(args.task_id) <= {item["id"] for item in sources}:
            raise ValueError("Requested task is not a verified training source")
        sources = [item for item in sources if item["id"] in args.task_id]
    bindings = {"script": sha(Path(__file__)), "proof_progress": sha(repo / "src/verus_self_evolve/proof_progress.py"),
                "proof_dependencies": sha(repo / "src/verus_self_evolve/proof_dependencies.py"),
                "campaign_evidence": sha(repo / "skillopt-verusage/src/skillopt_verusage/campaign_evidence.py"),
                "ledger": sha(ledger_path), "train_manifest": sha(manifest_path),
                "verus": sha(args.verus_bin), "lynette": sha(args.lynette_bin)}
    parent_reports = {}
    if args.parent_report_root:
        provenance_path = args.parent_report_root / "report_provenance.json"
        bindings["parent_provenance"] = sha(provenance_path)
        for row in json.loads(provenance_path.read_text())["reports"]:
            path = Path(row["report_path"])
            if sha(path) != row["report_sha256"]:
                raise ValueError("Parent report identity mismatch")
            parent_reports[row["id"]] = (json.loads(path.read_text()), row)
    write_json(root / "manifest.json", {"created_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root), "workers": args.workers, "bindings": bindings,
        "scope": "train-only offline checkpoint investigation, no frozen selector or provider calls",
        "expected_solved": len(sources), "skipped": skipped, "raw_data_read_only": True,
        "verifier_timeout_seconds": args.verifier_timeout_seconds,
        "reference_only": args.reference_only,
        "include_helpers": args.include_helpers, "verus_threads": 4,
        "metric_caveats": ["textual hindsight overlap, not semantic proof progress",
                           "execution-function coverage includes unchanged executable scaffold",
                           "every accepted pruning deletion passes Verus and Lynette preservation"]})

    def analyze(item):
        directory = root / item["id"]
        directory.mkdir()
        trace, refs, snapshots = load_trace(source_root / "rollout/predictions" / item["id"])
        name, occurrence = TARGET_OVERRIDES.get(item["id"], (item["task_id"].split("__")[-1], 0))
        function_body(trace["original_input"], name, occurrence=occurrence)
        baseline, candidate = directory / "input.rs", directory / "candidate.rs"
        baseline.write_text(trace["original_input"])
        verification_count = 0

        def command(command):
            nonlocal verification_count
            verification_count += 1
            now = time.monotonic()
            try:
                completed = subprocess.run(command, capture_output=True, text=True, cwd=directory,
                                           timeout=args.verifier_timeout_seconds, check=False)
                output = completed.stdout + completed.stderr
                returncode, timed_out = completed.returncode, False
            except subprocess.TimeoutExpired as error:
                decode = lambda value: value.decode(errors="replace") if isinstance(value, bytes) else (value or "")
                output = decode(error.stdout) + decode(error.stderr) + "\nVerifier wall-time limit reached; deletion not accepted."
                returncode, timed_out = None, True
            with (directory / "verification.jsonl").open("a") as handle:
                handle.write(json.dumps({"ordinal": verification_count, "command": command,
                    "candidate_sha256": sha(candidate), "returncode": returncode, "timed_out": timed_out,
                    "seconds": time.monotonic() - now, "output": output}) + "\n")
            return returncode == 0, output

        def preserve(original, pruned):
            candidate.write_text(pruned)
            return command([str(args.lynette_bin), "compare", "-t", str(baseline), str(candidate)])

        def verify(source):
            candidate.write_text(source)
            passed, output = command([str(args.verus_bin), str(candidate), "--num-threads", "4",
                                      "--triggers-mode", "silent"])
            passed = passed and verifier_state(output)["tier_rank"] == 2
            if passed:
                preserved, preservation_output = preserve(trace["original_input"], source)
                passed = preserved
                output += preservation_output
            return passed, output

        reference_pruning = None
        helper_scope = None
        reference_kind = "verified_original_final_unpruned" if args.reference_only else "verifier_greedy_pruned"
        if args.include_helpers:
            parent, parent_binding = parent_reports[item["id"]]
            if (parent["original_final_sha256"] != hashlib.sha256(trace["final_source"].encode()).hexdigest()
                    or parent["source_events_sha256"] != sha(source_root / "rollout/predictions" / item["id"] / "agent_events.jsonl")):
                raise ValueError("Parent source identity mismatch")
            reference_kind = parent_binding["reference_kind"]
            reference = parent["pruned_source"]
            if not verify(reference)[0]:
                raise ValueError("Reused reference failed fresh verification/preservation")

            def functions(source, label):
                logs = directory / label
                logs.mkdir()
                candidate.write_text(source)
                passed, output = command([str(args.verus_bin), str(candidate), "--no-verify", "--log", "vir",
                                          "--log-dir", str(logs), "--triggers-mode", "silent"])
                if not passed:
                    raise ValueError("Compiler dependency export failed: " + output[-800:])
                return compiler_functions((logs / "crate.vir").read_text(), source, str(candidate))

            baseline_functions = functions(trace["original_input"], "baseline_vir")
            reference_functions = functions(reference, "initial_reference_vir")
            helper_scope = proof_scope(reference_functions, baseline_functions, reference, trace["original_input"], name, occurrence)
            initial_scope = helper_scope
            trials, removed, rounds = [], [], 0
            # The parent target is already at a line/block fixed point. Revisit it only
            # if helper deletions changed the candidate; keep the expensive unpruned target separate.
            while True:
                rounds += 1
                removed_this_round = 0
                for component in helper_scope["components"]:
                    if component["is_target"] and (rounds == 1 or reference_kind != "verifier_greedy_pruned"):
                        continue
                    result = greedy_prune_proof_lines(trace["original_input"], reference, component["name"], verify,
                        occurrence=component["occurrence"], baseline_body=component["baseline_body"])
                    reference = result["pruned_source"]
                    trials.extend({**t, "component_key": component["key"], "scope_round": rounds} for t in result["trials"])
                    removed.extend({**t, "component_key": component["key"], "scope_round": rounds} for t in result["removed_line_records"])
                    removed_this_round += result["summary"]["removed_lines"]
                if not removed_this_round:
                    break
            helper_scope = proof_scope(functions(reference, "final_reference_vir"), baseline_functions,
                                       reference, trace["original_input"], name, occurrence)
            helper_scope["initial_components"] = initial_scope["components"]
            reference_pruning = {"pruned_source": reference, "trials": trials, "removed_line_records": removed,
                "parent_binding": parent_binding, "reused_target_pruning_summary": parent["pruning"]["summary"],
                "summary": {"removed_lines": len(removed), "verifier_trials": len(trials), "scope_rounds": rounds,
                            "status": "target_pruning_incomplete" if reference_kind != "verifier_greedy_pruned" else "completed",
                            "final_proof_nonblank_lines": sum(len(normalize_code_lines(function_body(reference,
                                c["name"], occurrence=c["occurrence"]))) for c in helper_scope["components"])}}
        if args.reference_only:
            reference_pruning = {"pruned_source": trace["final_source"], "trials": [], "removed_line_records": [],
                "summary": {"final_proof_nonblank_lines": len(normalize_code_lines(function_body(
                    trace["final_source"], name, occurrence=occurrence))),
                            "removed_lines": 0, "verifier_trials": 0, "status": "pruning_not_completed"}}
        report = analyze_progress(trace, snapshots, ledger, trace["result"]["bridge_task_key"],
                                  name, verify, preserve, function_occurrence=occurrence,
                                  reference_pruning=reference_pruning,
                                  reference_components=helper_scope["components"] if helper_scope else None)
        report["reference_kind"] = reference_kind
        if args.reference_only:
            report["metric"] = "unpruned-final-target-line-coverage-v1"
        report.update({"task_id": item["task_id"], "id": item["id"], "function_name": name,
                       "function_occurrence": occurrence, "total_output_tokens": sum(
                           sum(int((a.get("usage") or {}).get("completion_tokens") or 0) for a in r.get("attempts") or [])
                           for r in ledger if r.get("task_id") == trace["result"]["bridge_task_key"]),
                       "source_events_sha256": sha(source_root / "rollout/predictions" / item["id"] / "agent_events.jsonl")})
        enrich(report, snapshots, name, occurrence)
        if helper_scope:
            report["helper_scope"] = helper_scope
            target_curve = [{**r, "proof_coverage": r["target_proof_coverage"]} for r in report["curve"]]
            report["target_only_platforms"] = stagnation_segments(target_curve)
            first = report["first_verified_call"] or len(target_curve) + 1
            report["target_only_coverage_platforms"] = segments(target_curve, lambda a, b:
                b["call_ordinal"] < first and a["proof_coverage"] is not None and b["proof_coverage"] is not None
                and abs(a["proof_coverage"] - b["proof_coverage"]) < 1e-12)
            for transition, left, right in zip(report["transitions"], report["curve"], report["curve"][1:]):
                transition["target_flat_helper_gain"] = (left["target_proof_coverage"] is not None
                    and right["target_proof_coverage"] == left["target_proof_coverage"]
                    and transition["coverage_delta"] is not None and transition["coverage_delta"] > 0)
        (directory / "pruned_candidate.rs").write_text(report["pruned_source"])
        write_json(directory / "report.json", report)
        write_csv(directory / "curve.csv", [{k: v for k, v in r.items() if k not in ("verifier", "verifier_output")}
                                             for r in report["curve"]])
        write_csv(directory / "platforms.csv", report["stagnation_segments"])
        write_csv(directory / "regressions.csv", report["regression_transitions"])
        return summarize(item, report)

    completed, failures = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(analyze, item): item for item in sources}
        for future in as_completed(pending):
            item = pending[future]
            try:
                row = future.result()
                completed.append(row)
                print(json.dumps({"completed": len(completed), "failed": len(failures), **row}), flush=True)
            except Exception as error:
                failure = {"id": item["id"], "task_id": item["task_id"], "error": str(error), "traceback": traceback.format_exc()}
                failures.append(failure)
                write_json(root / item["id"] / "failure.json", failure)
                print(json.dumps({"completed": len(completed), "failed": len(failures), "failure": failure}), flush=True)
            write_json(root / "progress.json", {"completed": len(completed), "failed": len(failures),
                "expected": len(sources), "elapsed_seconds": time.monotonic() - started})
    completed.sort(key=lambda r: r["task_id"])
    write_csv(root / "task_statistics.csv", completed)
    write_json(root / "summary.json", {"completed": len(completed), "failed": len(failures),
        "failures": failures, "skipped": skipped, "platform_count_distribution": dict(sorted(Counter(
            r["platform_count"] for r in completed).items())), "regression_count_distribution": dict(sorted(Counter(
            r["regression_count"] for r in completed).items())), "rows": completed,
        "elapsed_seconds": time.monotonic() - started,
        "source_ledger_unchanged": sha(ledger_path) == bindings["ledger"],
        "no_paid_inference": True, "no_checkpoint_selection_frozen": True})
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
