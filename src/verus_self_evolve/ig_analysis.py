from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev


REFERENCE_ARTIFACT = "evidence_artifact"
CONTROL_ARTIFACTS = (
    "cross_trace_same_error",
    "cross_trace_any",
    "block_shuffled",
    "counterfactual_error",
    "irrelevant_archive",
)
LEGACY_CONTROL_ARTIFACTS = (
    "empty_container",
    "generic_skill",
    "shuffled_rationale",
    "wrong_error_rationale",
    "word_count_matched_control",
    "neutral_matched_control",
    "irrelevant_control",
)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    index = (len(ordered) - 1) * q
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - index) + ordered[high] * (index - low)


def _cluster_bootstrap_ci(rows: list[dict[str, object]]) -> tuple[float | None, float | None, int]:
    by_trace: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_trace[str(row["trace_id"])].append(float(row["difference_bits"]))
    traces = sorted(by_trace)
    if len(traces) < 2:
        return None, None, len(traces)
    cluster_means = {trace: mean(by_trace[trace]) for trace in traces}
    draws = [mean(cluster_means[trace] for trace in sample) for sample in itertools.product(traces, repeat=len(traces))]
    return _percentile(draws, 0.025), _percentile(draws, 0.975), len(traces)


def analyze_aggregates(
    aggregate_path: Path,
    reference_artifact: str = REFERENCE_ARTIFACT,
    control_artifacts: tuple[str, ...] = CONTROL_ARTIFACTS,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    rows = _read_jsonl(aggregate_path)
    action_rows = [row for row in rows if row.get("target_type") == "action_primary"]
    by_artifact: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_state: dict[tuple[str, str], dict[str, dict[str, object]]] = defaultdict(dict)
    for row in action_rows:
        artifact = str(row["artifact_type"])
        by_artifact[artifact].append(row)
        by_state[(str(row["sample_id"]), str(row["trace_id"]))][artifact] = row

    artifact_summary = []
    for artifact, group in sorted(by_artifact.items()):
        pmi = [float(row["decision_pmi_bits"]) for row in group]
        intervention_tokens = [
            int(row.get("intervention_token_count") or 0)
            or int(row["context_token_count_artifact"]) - int(row["context_token_count_baseline"])
            for row in group
        ]
        artifact_summary.append(
            {
                "artifact_type": artifact,
                "state_count": len(group),
                "mean_decision_pmi_bits": mean(pmi),
                "median_decision_pmi_bits": median(pmi),
                "stdev_decision_pmi_bits": stdev(pmi) if len(pmi) > 1 else 0.0,
                "positive_state_count": sum(value > 0 for value in pmi),
                "total_intervention_tokens": sum(intervention_tokens),
                "global_density_bits_per_intervention_token": (
                    sum(pmi) / sum(intervention_tokens) if sum(intervention_tokens) else None
                ),
            }
        )

    paired_rows = []
    for (sample_id, trace_id), artifacts in sorted(by_state.items()):
        if reference_artifact not in artifacts:
            continue
        reference = float(artifacts[reference_artifact]["decision_pmi_bits"])
        for control in control_artifacts:
            if control not in artifacts:
                continue
            control_value = float(artifacts[control]["decision_pmi_bits"])
            paired_rows.append(
                {
                    "sample_id": sample_id,
                    "trace_id": trace_id,
                    "observed_action_text": artifacts[reference_artifact].get("observed_action_text", ""),
                    "reference_artifact": reference_artifact,
                    "control_artifact": control,
                    "reference_pmi_bits": reference,
                    "control_pmi_bits": control_value,
                    "difference_bits": reference - control_value,
                    "reference_wins": reference > control_value,
                }
            )

    comparison_summary = []
    for control in control_artifacts:
        group = [row for row in paired_rows if row["control_artifact"] == control]
        if not group:
            continue
        differences = [float(row["difference_bits"]) for row in group]
        ci_low, ci_high, trace_count = _cluster_bootstrap_ci(group)
        comparison_summary.append(
            {
                "reference_artifact": reference_artifact,
                "control_artifact": control,
                "state_count": len(group),
                "trace_cluster_count": trace_count,
                "mean_paired_difference_bits": mean(differences),
                "median_paired_difference_bits": median(differences),
                "reference_win_count": sum(bool(row["reference_wins"]) for row in group),
                "reference_win_rate": mean(bool(row["reference_wins"]) for row in group),
                "cluster_bootstrap_95ci_low": ci_low,
                "cluster_bootstrap_95ci_high": ci_high,
                "predeclared_direction": "positive",
            }
        )
    specific_rows = []
    grouped_pairs: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in paired_rows:
        grouped_pairs[(str(row["sample_id"]), str(row["trace_id"]))].append(row)
    for (sample_id, trace_id), group in sorted(grouped_pairs.items()):
        reference = float(group[0]["reference_pmi_bits"])
        controls = [float(row["control_pmi_bits"]) for row in group]
        specific_rows.append(
            {
                "sample_id": sample_id,
                "trace_id": trace_id,
                "observed_action_text": group[0].get("observed_action_text", ""),
                "reference_artifact": reference_artifact,
                "control_count": len(controls),
                "reference_pmi_bits": reference,
                "null_mean_pmi_bits": mean(controls),
                "specific_gain_bits": reference - mean(controls),
                "reference_null_percentile": sum(reference > value for value in controls) / len(controls),
                "specific_gain_positive": reference > mean(controls),
            }
        )
    return artifact_summary, paired_rows, comparison_summary, specific_rows


def analyze(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    control_artifacts = tuple(args.control_artifacts)
    raw_rows = _read_jsonl(Path(args.aggregates))
    action_rows = [row for row in raw_rows if row.get("target_type") == "action_primary"]
    by_state: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in action_rows:
        by_state[str(row["sample_id"])].append(row)
    expected_artifacts = {args.reference_artifact, *control_artifacts}
    integrity_errors = []
    if len(by_state) != args.expected_state_count:
        integrity_errors.append(f"expected {args.expected_state_count} states, found {len(by_state)}")
    for sample_id, rows in sorted(by_state.items()):
        counts = {artifact: sum(row["artifact_type"] == artifact for row in rows) for artifact in expected_artifacts}
        if any(count != 1 for count in counts.values()):
            integrity_errors.append(f"{sample_id}: incomplete/duplicate artifact matrix {counts}")
        relevant_rows = [row for row in rows if row["artifact_type"] in expected_artifacts]
        if any(int(row.get("candidate_count", 0)) != args.expected_candidate_count for row in relevant_rows):
            integrity_errors.append(f"{sample_id}: candidate count mismatch")
        if any(row.get("action_accepted") is not True for row in relevant_rows):
            integrity_errors.append(f"{sample_id}: target action is not locally accepted")
        if any(row.get("token_match_exact") is not True for row in relevant_rows):
            integrity_errors.append(f"{sample_id}: intervention token matching failed")
        actual_deltas = {int(row.get("intervention_token_count", -1)) for row in relevant_rows}
        prepared_deltas = {int(row.get("prepared_intervention_token_count", -2)) for row in relevant_rows}
        if len(actual_deltas) != 1 or actual_deltas != prepared_deltas:
            integrity_errors.append(
                f"{sample_id}: actual/prepared intervention deltas differ: actual={actual_deltas}, prepared={prepared_deltas}"
            )
        if len({row.get("option_map_sha256") for row in relevant_rows}) != 1:
            integrity_errors.append(f"{sample_id}: option map differs across artifacts")
        if len({row.get("serialized_target") for row in relevant_rows}) != 1:
            integrity_errors.append(f"{sample_id}: serialized target differs across artifacts")
        if len({row.get("observed_action_text") for row in relevant_rows}) != 1:
            integrity_errors.append(f"{sample_id}: observed action differs across artifacts")
        if any(row.get("prompt_format") != args.expected_prompt_format for row in relevant_rows):
            integrity_errors.append(f"{sample_id}: prompt format mismatch")
    if integrity_errors:
        raise ValueError("analysis integrity gate failed: " + "; ".join(integrity_errors))
    artifact_summary, paired_rows, comparison_summary, specific_rows = analyze_aggregates(
        Path(args.aggregates),
        reference_artifact=args.reference_artifact,
        control_artifacts=control_artifacts,
    )
    _write_csv(out_dir / "artifact_summary.csv", artifact_summary)
    _write_csv(out_dir / "paired_state_differences.csv", paired_rows)
    _write_csv(out_dir / "paired_comparisons.csv", comparison_summary)
    _write_csv(out_dir / "specific_state_gain.csv", specific_rows)
    by_action: dict[str, list[float]] = defaultdict(list)
    for row in specific_rows:
        by_action[str(row["observed_action_text"])].append(float(row["specific_gain_bits"]))
    specific_by_action = [
        {
            "observed_action_text": action,
            "state_count": len(values),
            "mean_specific_gain_bits": mean(values),
            "positive_state_count": sum(value > 0 for value in values),
        }
        for action, values in sorted(by_action.items())
    ]
    _write_csv(out_dir / "specific_by_action.csv", specific_by_action)
    specific_gains = [float(row["specific_gain_bits"]) for row in specific_rows]
    positive_specific_states = sum(bool(row["specific_gain_positive"]) for row in specific_rows)
    required_wins = math.ceil(len(specific_rows) * 2 / 3) if specific_rows else 0
    decisive_controls = {"cross_trace_same_error", "block_shuffled", "irrelevant_archive"}
    decisive_pass = all(
        int(row["reference_win_count"]) >= required_wins
        for row in comparison_summary
        if row["control_artifact"] in decisive_controls
    ) and decisive_controls.issubset({str(row["control_artifact"]) for row in comparison_summary})
    gate = {
        "mean_specific_gain_bits": mean(specific_gains) if specific_gains else None,
        "median_specific_gain_bits": median(specific_gains) if specific_gains else None,
        "positive_specific_state_count": positive_specific_states,
        "state_count": len(specific_rows),
        "required_positive_state_count": required_wins,
        "decisive_control_families_pass": decisive_pass,
        "artifact_quality_gate_pass": bool(
            specific_gains
            and mean(specific_gains) > 0
            and positive_specific_states >= required_wins
            and decisive_pass
        ),
    }
    candidate_mass_rows = []
    action_distributions = getattr(args, "action_distributions", None)
    if action_distributions:
        distribution_rows = _read_jsonl(Path(action_distributions))
        aggregate_case_ids = {str(row["case_id"]) for row in action_rows}
        distribution_case_ids = {str(row["case_id"]) for row in distribution_rows}
        if aggregate_case_ids != distribution_case_ids:
            raise ValueError("action-distribution cases do not match aggregate cases")
        for row in distribution_rows:
            baseline_scores = {key: float(value) for key, value in row["baseline_log_scores"].items()}
            artifact_scores = {key: float(value) for key, value in row["artifact_log_scores"].items()}
            baseline_mass = sum(math.exp(value) for value in baseline_scores.values())
            artifact_mass = sum(math.exp(value) for value in artifact_scores.values())
            candidate_mass_rows.append(
                {
                    "case_id": row["case_id"],
                    "sample_id": row["sample_id"],
                    "artifact_type": row["artifact_type"],
                    "baseline_candidate_raw_mass": baseline_mass,
                    "artifact_candidate_raw_mass": artifact_mass,
                }
            )
        _write_csv(out_dir / "candidate_raw_mass.csv", candidate_mass_rows)
    all_candidate_masses = [
        float(row[key])
        for row in candidate_mass_rows
        for key in ("baseline_candidate_raw_mass", "artifact_candidate_raw_mass")
    ]
    candidate_mass_diagnostic = {
        "available": bool(all_candidate_masses),
        "semantics": "Raw next-token probability mass assigned to the fixed candidate option tokens before normalization.",
        "minimum": min(all_candidate_masses) if all_candidate_masses else None,
        "median": median(all_candidate_masses) if all_candidate_masses else None,
        "maximum": max(all_candidate_masses) if all_candidate_masses else None,
        "all_below_1e_6": bool(all_candidate_masses and max(all_candidate_masses) < 1e-6),
        "interpretation": (
            "If candidate mass is tiny, normalized action probabilities are a forced-choice conditional proxy, "
            "not the model's unconstrained next-action distribution."
        ),
    }
    summary = {
        "aggregates": args.aggregates,
        "reference_artifact": args.reference_artifact,
        "control_artifacts": list(control_artifacts),
        "artifact_summary": artifact_summary,
        "paired_comparisons": comparison_summary,
        "specific_gain_summary": gate,
        "specific_by_action": specific_by_action,
        "candidate_mass_diagnostic": candidate_mass_diagnostic,
        "integrity_gate": {
            "passed": True,
            "expected_state_count": args.expected_state_count,
            "expected_candidate_count": args.expected_candidate_count,
            "expected_prompt_format": args.expected_prompt_format,
            "expected_artifact_matrix": sorted(expected_artifacts),
        },
        "uncertainty_note": "Exact cluster bootstrap over observed trace clusters; three clusters are insufficient for firm inference.",
    }
    (out_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def add_analysis_parser(subparsers) -> None:
    parser = subparsers.add_parser("ig-probe-analyze", help="produce durable paired action-IG summaries")
    parser.add_argument("--aggregates", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--reference-artifact", default=REFERENCE_ARTIFACT)
    parser.add_argument("--control-artifacts", nargs="+", default=list(CONTROL_ARTIFACTS))
    parser.add_argument("--expected-state-count", type=int, default=6)
    parser.add_argument("--expected-candidate-count", type=int, default=22)
    parser.add_argument("--expected-prompt-format", default="chat_direct")
    parser.add_argument("--action-distributions", default=None)
    parser.set_defaults(func=analyze)
