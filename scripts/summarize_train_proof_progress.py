#!/usr/bin/env python3
"""Consolidate provenance-preserving offline progress reports and render curves."""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def distribution(values):
    return {"count": len(values), "minimum": min(values, default=0),
            "median": statistics.median(values) if values else 0,
            "maximum": max(values, default=0), "total": sum(values)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-roots", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.output_dir.resolve()
    if args.run_root.resolve() not in root.parents or not root.is_dir() or any(root.iterdir()):
        raise ValueError("Consolidation output must be a fresh empty run-root child")
    spec = importlib.util.spec_from_file_location("progress_audit", Path(__file__).with_name("analyze_train_proof_progress.py"))
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    repo = Path(__file__).resolve().parents[1]
    items = {row["id"]: row for row in json.loads((repo / "fixed-claude-stratified-80-seed20260814/train/items.json").read_text())}
    reports = {}
    bindings = []
    for source in args.report_roots:
        bindings.append({"root": str(source), "manifest_sha256": audit.sha(source / "manifest.json")})
        for path in sorted(source.glob("*/report.json")):
            report = json.loads(path.read_text())
            report.setdefault("reference_kind", "verifier_greedy_pruned")
            reports[report["id"]] = (report, path)
    rows, platforms, regressions, provenance = [], [], [], []
    for ident, (report, path) in sorted(reports.items(), key=lambda x: x[1][0]["task_id"]):
        row = audit.summarize(items[ident], report)
        first = report["first_verified_call"] or len(report["curve"]) + 1
        before = [p for p in report["stagnation_segments"] if p["start_call"] < first]
        row.update({"pre_first_pass_platform_count": len(before),
                    "pre_first_pass_platform_tokens": sum(p["output_token_delta"] for p in before),
                    "pre_first_pass_regression_count": sum(p["to_call"] < first for p in report["regression_transitions"]),
                    "coverage_only_platform_token_spans": ";".join(str(p["output_token_delta"]) for p in report["coverage_only_platforms"]),
                    "report_path": str(path)})
        rows.append(row)
        platforms.extend({"id": ident, "task_id": report["task_id"], "reference_kind": report["reference_kind"],
                          "before_first_pass": p["start_call"] < first, **p} for p in report["stagnation_segments"])
        regressions.extend({"id": ident, "task_id": report["task_id"], "reference_kind": report["reference_kind"],
                            "before_first_pass": p["to_call"] < first, **p} for p in report["regression_transitions"])
        provenance.append({"id": ident, "report_path": str(path), "report_sha256": audit.sha(path),
                           "reference_kind": report["reference_kind"]})
    primary = [r for r in rows if r["reference_kind"] == "verifier_greedy_pruned"]
    primary_platforms = [p["output_token_delta"] for p in platforms
                         if p["reference_kind"] == "verifier_greedy_pruned" and p["before_first_pass"]]
    coverage_only_tokens = [p["output_token_delta"] for report, _ in reports.values()
                            if report["reference_kind"] == "verifier_greedy_pruned"
                            for p in report["coverage_only_platforms"]]
    summary = {"tasks_with_curves": len(rows), "pruned_primary_tasks": len(primary),
               "unpruned_supplemental_tasks": len(rows) - len(primary),
               "verifier_calls": sum(r["verifier_calls"] for r in rows),
               "primary_pre_first_pass_platform_count_distribution": dict(sorted(Counter(
                   r["pre_first_pass_platform_count"] for r in primary).items())),
               "primary_pre_first_pass_platform_tokens": distribution(primary_platforms),
               "primary_coverage_only_platform_count_distribution": dict(sorted(Counter(
                   r["coverage_only_platform_count"] for r in primary).items())),
               "primary_coverage_only_platform_tokens": distribution(coverage_only_tokens),
               "primary_regression_count_distribution": dict(sorted(Counter(r["regression_count"] for r in primary).items())),
               "primary_regression_transitions": sum(r["regression_count"] for r in primary),
               "primary_regressions_before_first_pass": sum(r["pre_first_pass_regression_count"] for r in primary),
               "primary_coverage_drop_count": sum(r["coverage_drop_count"] for r in primary),
               "primary_tier_drop_count": sum(r["tier_drop_count"] for r in primary),
               "primary_flat_error_improvements": sum(r["flat_with_error_improvement_count"] for r in primary),
               "primary_tasks_with_flat_error_improvements": sum(r["flat_with_error_improvement_count"] > 0 for r in primary),
               "coverage_unavailable_calls": sum(r["coverage_unavailable_calls"] for r in rows),
               "reference_pruning_trials": sum(r["pruning_verifier_trials"] for r in primary),
               "no_checkpoint_rule_frozen": True, "no_paid_inference": True,
               "scope": "initial investigation; one expensive pruning case remains incomplete"}
    if all("helper_scope" in report for report, _ in reports.values()):
        summary.update({
            "scope": "compiler-scoped helper-inclusive repair; one target-pruning supplement remains incomplete",
            "tasks_with_related_helpers": sum(r["related_helper_count"] > 0 for r in rows),
            "related_helper_total": sum(r["related_helper_count"] for r in rows),
            "excluded_changed_helpers": sum(r["excluded_changed_helper_count"] for r in rows),
            "paired_primary_target_platform_distribution": dict(sorted(Counter(
                r["paired_target_platform_count"] for r in primary).items())),
            "paired_primary_target_coverage_platform_distribution": dict(sorted(Counter(
                r["paired_target_coverage_only_platform_count"] for r in primary).items())),
            "target_flat_helper_gain_transitions": sum(r["target_flat_helper_gain_transitions"] for r in rows),
            "tasks_with_target_flat_helper_gains": sum(r["target_flat_helper_gain_transitions"] > 0 for r in rows),
            "primary_paired_target_platform_tokens": distribution([p["output_token_delta"]
                for report, _ in reports.values() if report["reference_kind"] == "verifier_greedy_pruned"
                for p in report["target_only_platforms"]
                if p["start_call"] < (report["first_verified_call"] or len(report["curve"]) + 1)]),
            "primary_paired_target_coverage_platform_tokens": distribution([p["output_token_delta"]
                for report, _ in reports.values() if report["reference_kind"] == "verifier_greedy_pruned"
                for p in report["target_only_coverage_platforms"]]),
        })
        components = [{"id": ident, "call": c["call_ordinal"], "output_tokens": c["cumulative_output_tokens"], **part}
                      for ident, (report, _) in reports.items() for c in report["curve"] for part in c["component_coverage"]]
        audit.write_csv(root / "component_curves.csv", components)
        # Inventory signal coverage, not a frozen three-point selector. Context
        # fallbacks are distinct prefix boundaries even when the code is identical.
        inventory = []
        for ident, (report, path) in reports.items():
            by_call = {c["call_ordinal"]: c for c in report["curve"]}
            first = report["first_verified_call"] or len(by_call) + 1
            first_event = by_call[first]["event_index"] if first in by_call else float("inf")
            signal_calls = set()
            for family, spans, field in (
                    ("coverage_platform_start", report["coverage_only_platforms"], "start_call"),
                    ("repeated_literal_diagnostic_start", report["repeated_diagnostic_spans"], "start_call"),
                    ("pre_regression", report["regression_transitions"], "from_call"),
                    ("post_regression", report["regression_transitions"], "to_call")):
                for span in spans:
                    call = by_call[span[field]]
                    if call["call_ordinal"] >= first or call["target_proof_coverage"] is None:
                        continue
                    signal_calls.add(call["call_ordinal"])
                    inventory.append({"id":ident,"family":family,"event_index":call["event_index"],
                        "call":call["call_ordinal"],"candidate_sha256":call["candidate_sha256"]})
            source_root = Path(json.loads((path.parent.parent / "manifest.json").read_text())["source_root"])
            trace, _, snapshots = audit.load_trace(source_root / "rollout/predictions" / ident)
            context = []
            for node in trace["snapshots"]["chain"]:
                if node["event_index"] >= first_event:
                    continue
                try:
                    audit.function_body(snapshots[node["candidate_sha256"]], report["function_name"],
                                        occurrence=report["function_occurrence"])
                except ValueError:
                    continue
                context.append(node)
                inventory.append({"id":ident,"family":"presolution_context_boundary",
                    "event_index":node["event_index"],"call":None,"candidate_sha256":node["candidate_sha256"]})
            row = next(r for r in rows if r["id"] == ident)
            row.update({"distinct_signal_calls":len(signal_calls),"presolution_context_boundaries":len(context),
                        "presolution_distinct_code_states":len({n["candidate_sha256"] for n in context})})
        summary.update({"tasks_with_at_least_three_signal_calls":sum(r["distinct_signal_calls"] >= 3 for r in rows),
                        "tasks_with_at_least_three_context_boundaries":sum(r["presolution_context_boundaries"] >= 3 for r in rows),
                        "tasks_with_at_least_three_code_states":sum(r["presolution_distinct_code_states"] >= 3 for r in rows)})
        audit.write_csv(root / "checkpoint_candidate_inventory.csv", inventory)
    audit.write_csv(root / "task_statistics.csv", rows)
    audit.write_csv(root / "platforms.csv", platforms)
    audit.write_csv(root / "regressions.csv", regressions)
    audit.write_json(root / "summary.json", summary)
    audit.write_json(root / "report_provenance.json", {"inputs": bindings, "reports": provenance,
        "summary_script_sha256": audit.sha(Path(__file__)),
        "supersession": "later roots replace only same-ID reports; superseded raw reports are preserved"})
    curves = root / "curves"
    curves.mkdir()
    fig, axes = plt.subplots(7, 6, figsize=(21, 22), constrained_layout=True)
    for index, row in enumerate(rows):
        report, path = reports[row["id"]]
        curve = report["curve"]
        xs = [c["cumulative_output_tokens"] / 1000 for c in curve]
        ys = [c["proof_coverage"] if c["proof_coverage"] is not None else float("nan") for c in curve]
        tiers = [c["verifier_tier"] for c in curve]
        axis = axes.flat[index]
        axis.plot(xs, ys, "o-", ms=3, lw=1.1)
        targets = [c.get("target_proof_coverage", c["proof_coverage"]) for c in curve]
        targets = [y if y is not None else float("nan") for y in targets]
        if "helper_scope" in report:
            axis.plot(xs, targets, "--", color="gray", lw=.8)
        axis.set_ylim(-0.05, 1.05)
        axis.set_title(f"{row['project']}: {row['function'][:34]}\n"
                       f"platforms {row['pre_first_pass_platform_count']}; drops {row['regression_count']}"
                       + ("; UNPRUNED" if row["reference_kind"] != "verifier_greedy_pruned" else ""), fontsize=8)
        axis.tick_params(labelsize=7)
        axis.grid(alpha=.2)
        detail, (top, bottom) = plt.subplots(2, 1, figsize=(10, 5.2), sharex=True,
                                            gridspec_kw={"height_ratios": [3, 1]}, constrained_layout=True)
        top.plot(xs, ys, "o-", ms=4, label="Target + related helpers" if "helper_scope" in report else "Target")
        if "helper_scope" in report:
            top.plot(xs, targets, "--", color="gray", label="Target only (same reference)")
            top.legend(fontsize=8)
        top.set_ylim(-0.05, 1.05)
        top.set_ylabel("Final-reference line overlap")
        bottom.step(xs, tiers, where="post", color="#9c4f00")
        bottom.set_yticks([0, 1, 2], ["Unparsed/compile", "Proof errors", "Verified"])
        bottom.set_xlabel("Recorded cumulative output tokens (thousands)")
        detail.suptitle(f"{row['project']}: {row['function']}\n{row['reference_kind']}", fontsize=10)
        for span in report["stagnation_segments"]:
            if span["start_call"] < (report["first_verified_call"] or len(curve) + 1):
                top.axvspan(span["start_output_tokens"] / 1000, span["end_output_tokens"] / 1000,
                            color="#d9a300", alpha=.15)
        for drop in report["regression_transitions"]:
            top.axvline(drop["to_output_tokens"] / 1000, color="#a80000", alpha=.4, lw=.8)
        for call, x, y in zip(curve, xs, ys):
            if call["proof_coverage"] is not None:
                top.annotate(str(call["call_ordinal"]), (x, y), fontsize=6, xytext=(0, 5), textcoords="offset points")
        top.grid(alpha=.2)
        detail.savefig(curves / f"{row['id']}.png", dpi=150)
        plt.close(detail)
    for axis in list(axes.flat)[len(rows):]:
        axis.set_visible(False)
    fig.suptitle("Training proof progress: hindsight text proxy, not semantic stagnation\n"
                 "Per-task token scales vary; one unpruned reference is supplemental", fontsize=16)
    fig.savefig(root / "all_curves.png", dpi=150)
    plt.close(fig)
    text = ["# Train proof-progress statistics", "",
            "Initial investigation only. Primary statistics use38 verifier-pruned references;",
            "one expensive task has a separately labeled verified unpruned reference.", "",
            "Platform counts are before the first observed target verification. Regression",
            "counts cover the full trace and combine text-overlap drops with verifier-tier drops.",
            "Coverage-only platforms merge consecutive equal-overlap endpoints regardless of",
            "verification tier; state-aware platforms also require an unchanged nonpassing tier.",
            "No minimum span threshold is imposed. Output tokens include recorded reasoning",
            "tokens when the provider ledger includes them, not just visible proof text.",
            "Neither measure establishes semantic stagnation or the usefulness of an intervention.", "",
            "| Project / target | Coverage-only platforms | Coverage-only output-token spans | State-aware platforms | State-aware output-token spans | Regressions | Reference |",
            "|---|---:|---|---:|---|---:|---|"]
    if "related_helper_total" in summary:
        text[2] = ("Helper-inclusive repair: primary statistics use 38 verifier-pruned target references, "
                   "with full-candidate gated helper pruning and paired target-only curves.")
        text[3] = "One expensive task has a separately labeled verified unpruned target reference."
        text[5:5] = ["Scope uses compiler-resolved local new/changed proof dependencies, not all helpers.",
                     "Dashed gray curves are target-only on the same new reference. A missing target is unknown.",
                     "Candidate inventory lists options only: no checkpoints or selection rule are frozen.", ""]
    for row in rows:
        spans = [p["output_token_delta"] for p in platforms if p["id"] == row["id"] and p["before_first_pass"]]
        coverage_spans = row['coverage_only_platform_token_spans'].replace(';', ', ')
        text.append(f"| {row['project']} / {row['function']} | {row['coverage_only_platform_count']} | "
                    f"{coverage_spans or 'none'} | {row['pre_first_pass_platform_count']} | "
                    f"{', '.join(map(str, spans)) or 'none'} | {row['regression_count']} | {row['reference_kind']} |")
    text += ["", "![All curves](all_curves.png)", "", "## Individual curves", ""]
    text.extend(f"- [{r['project']} / {r['function']}](curves/{r['id']}.png)" for r in rows)
    (root / "STATISTICS.md").write_text("\n".join(text) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
