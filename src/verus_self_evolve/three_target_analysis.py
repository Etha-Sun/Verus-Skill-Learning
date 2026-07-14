from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from .ig_analysis import CONTROL_ARTIFACTS, REFERENCE_ARTIFACT, _read_jsonl


TARGET_TYPES = ("action_primary", "patch_span", "full_proof")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average_rank = (start + end - 1) / 2
        for index in order[start:end]:
            ranks[index] = average_rank
        start = end
    return ranks


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    left_mean = mean(left)
    right_mean = mean(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    denominator = math.sqrt(
        sum((value - left_mean) ** 2 for value in left)
        * sum((value - right_mean) ** 2 for value in right)
    )
    return numerator / denominator if denominator else None


def analyze_three_targets(
    aggregate_path: Path,
    out_dir: Path,
    expected_state_count: int = 6,
    target_types: tuple[str, ...] = TARGET_TYPES,
    reference_artifact: str = REFERENCE_ARTIFACT,
    control_artifacts: tuple[str, ...] = CONTROL_ARTIFACTS,
) -> dict[str, object]:
    rows = [row for row in _read_jsonl(aggregate_path) if row.get("target_type") in target_types]
    expected_artifacts = {reference_artifact, *control_artifacts}
    by_cell: dict[tuple[str, str], dict[str, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        key = (str(row["sample_id"]), str(row["target_type"]))
        artifact = str(row["artifact_type"])
        if artifact in by_cell[key]:
            raise ValueError(f"duplicate aggregate row for {key} and {artifact}")
        by_cell[key][artifact] = row

    errors: list[str] = []
    states = sorted({sample_id for sample_id, _ in by_cell})
    if len(states) != expected_state_count:
        errors.append(f"expected {expected_state_count} states, found {len(states)}")
    for sample_id in states:
        for target_type in target_types:
            artifacts = by_cell.get((sample_id, target_type), {})
            missing = expected_artifacts - artifacts.keys()
            if missing:
                errors.append(f"{sample_id}/{target_type}: missing {sorted(missing)}")
                continue
            relevant = [artifacts[name] for name in expected_artifacts]
            if any(bool(row.get("sequence_truncated")) for row in relevant):
                errors.append(f"{sample_id}/{target_type}: truncated sequence")
            if any(row.get("token_match_exact") is not True for row in relevant):
                errors.append(f"{sample_id}/{target_type}: matched artifact has inexact intervention length")
            if len({row.get("target_sha256") for row in relevant}) != 1:
                errors.append(f"{sample_id}/{target_type}: target hash mismatch")
            if len({int(row["target_token_count"]) for row in relevant}) != 1:
                errors.append(f"{sample_id}/{target_type}: target token count mismatch")
            actual_tokens = {int(row["intervention_token_count"]) for row in relevant}
            prepared_tokens = {int(row["prepared_intervention_token_count"]) for row in relevant}
            if len(actual_tokens) != 1 or actual_tokens != prepared_tokens:
                errors.append(f"{sample_id}/{target_type}: intervention token counts differ")
    if errors:
        raise ValueError("three-target integrity gate failed: " + "; ".join(errors))

    artifact_summary: list[dict[str, object]] = []
    for target_type in target_types:
        for artifact_type in sorted({str(row["artifact_type"]) for row in rows}):
            group = [
                row
                for row in rows
                if row["target_type"] == target_type and row["artifact_type"] == artifact_type
            ]
            if not group:
                continue
            total = [float(row["target_loglikelihood_ig_bits"]) for row in group]
            per_token = [value / int(row["target_token_count"]) for value, row in zip(total, group)]
            artifact_summary.append(
                {
                    "target_type": target_type,
                    "artifact_type": artifact_type,
                    "state_count": len(group),
                    "mean_total_ig_bits": mean(total),
                    "median_total_ig_bits": median(total),
                    "mean_ig_bits_per_target_token": mean(per_token),
                    "median_ig_bits_per_target_token": median(per_token),
                    "positive_total_ig_count": sum(value > 0 for value in total),
                }
            )

    paired_rows: list[dict[str, object]] = []
    specific_rows: list[dict[str, object]] = []
    for sample_id in states:
        for target_type in target_types:
            artifacts = by_cell[(sample_id, target_type)]
            reference_row = artifacts[reference_artifact]
            reference_total = float(reference_row["target_loglikelihood_ig_bits"])
            target_tokens = int(reference_row["target_token_count"])
            control_totals = []
            for control in control_artifacts:
                control_total = float(artifacts[control]["target_loglikelihood_ig_bits"])
                control_totals.append(control_total)
                paired_rows.append(
                    {
                        "sample_id": sample_id,
                        "trace_id": reference_row["trace_id"],
                        "target_type": target_type,
                        "target_token_count": target_tokens,
                        "control_artifact": control,
                        "evidence_total_ig_bits": reference_total,
                        "control_total_ig_bits": control_total,
                        "specific_total_ig_bits": reference_total - control_total,
                        "specific_ig_bits_per_target_token": (reference_total - control_total) / target_tokens,
                        "evidence_wins": reference_total > control_total,
                    }
                )
            null_mean = mean(control_totals)
            specific_rows.append(
                {
                    "sample_id": sample_id,
                    "trace_id": reference_row["trace_id"],
                    "target_type": target_type,
                    "target_token_count": target_tokens,
                    "evidence_total_ig_bits": reference_total,
                    "matched_control_mean_total_ig_bits": null_mean,
                    "specific_total_ig_bits": reference_total - null_mean,
                    "evidence_ig_bits_per_target_token": reference_total / target_tokens,
                    "matched_control_mean_ig_bits_per_target_token": null_mean / target_tokens,
                    "specific_ig_bits_per_target_token": (reference_total - null_mean) / target_tokens,
                    "specific_gain_positive": reference_total > null_mean,
                }
            )

    target_summary: list[dict[str, object]] = []
    for target_type in target_types:
        group = [row for row in specific_rows if row["target_type"] == target_type]
        total = [float(row["specific_total_ig_bits"]) for row in group]
        per_token = [float(row["specific_ig_bits_per_target_token"]) for row in group]
        target_summary.append(
            {
                "target_type": target_type,
                "state_count": len(group),
                "mean_specific_total_ig_bits": mean(total),
                "median_specific_total_ig_bits": median(total),
                "mean_specific_ig_bits_per_target_token": mean(per_token),
                "median_specific_ig_bits_per_target_token": median(per_token),
                "positive_specific_state_count": sum(value > 0 for value in total),
            }
        )

    control_summary: list[dict[str, object]] = []
    for target_type in target_types:
        for control in control_artifacts:
            group = [
                row
                for row in paired_rows
                if row["target_type"] == target_type and row["control_artifact"] == control
            ]
            total = [float(row["specific_total_ig_bits"]) for row in group]
            per_token = [float(row["specific_ig_bits_per_target_token"]) for row in group]
            control_summary.append(
                {
                    "target_type": target_type,
                    "control_artifact": control,
                    "state_count": len(group),
                    "mean_evidence_minus_control_bits": mean(total),
                    "median_evidence_minus_control_bits": median(total),
                    "mean_evidence_minus_control_bits_per_target_token": mean(per_token),
                    "evidence_win_count": sum(bool(row["evidence_wins"]) for row in group),
                }
            )

    correlation_rows: list[dict[str, object]] = []
    specific_map = {
        (str(row["sample_id"]), str(row["target_type"])): float(row["specific_ig_bits_per_target_token"])
        for row in specific_rows
    }
    for index, left_target in enumerate(target_types):
        for right_target in target_types[index + 1 :]:
            left = [specific_map[(state, left_target)] for state in states]
            right = [specific_map[(state, right_target)] for state in states]
            correlation_rows.append(
                {
                    "left_target_type": left_target,
                    "right_target_type": right_target,
                    "state_count": len(states),
                    "pearson_specific_per_token": _pearson(left, right),
                    "spearman_specific_per_token": _pearson(_rank(left), _rank(right)),
                    "sign_agreement_count": sum((a > 0) == (b > 0) for a, b in zip(left, right)),
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_dir / "artifact_summary.csv", artifact_summary)
    _write_csv(out_dir / "paired_control_differences.csv", paired_rows)
    _write_csv(out_dir / "specific_state_gain.csv", specific_rows)
    _write_csv(out_dir / "target_summary.csv", target_summary)
    _write_csv(out_dir / "control_summary.csv", control_summary)
    _write_csv(out_dir / "cross_target_correlations.csv", correlation_rows)
    _write_csv(
        out_dir / "state_mapping.csv",
        [
            {
                "figure_label": f"S{index + 1}",
                "sample_id": sample_id,
                "trace_id": by_cell[(sample_id, target_types[0])][reference_artifact]["trace_id"],
                "prefix_id": by_cell[(sample_id, target_types[0])][reference_artifact]["prefix_id"],
            }
            for index, sample_id in enumerate(states)
        ],
    )
    summary = {
        "aggregates": str(aggregate_path),
        "integrity_gate": {
            "passed": True,
            "state_count": len(states),
            "target_types": list(target_types),
            "reference_artifact": reference_artifact,
            "matched_controls": list(control_artifacts),
            "empty_container_excluded_from_matched_controls": True,
        },
        "target_summary": target_summary,
        "control_summary": control_summary,
        "cross_target_correlations": correlation_rows,
        "interpretation": {
            "raw_ig": "log2 p(target|state,artifact) - log2 p(target|state)",
            "specific_ig": "raw evidence IG minus the mean raw IG of matched controls",
            "per_token": "total IG divided by the fixed target token count; use for cross-target scale comparison",
        },
    }
    (out_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def _plot(out_dir: Path) -> None:
    import matplotlib.pyplot as plt

    rows = list(csv.DictReader((out_dir / "specific_state_gain.csv").open(encoding="utf-8")))
    targets = list(dict.fromkeys(row["target_type"] for row in rows))
    fig, axes = plt.subplots(1, len(targets), figsize=(15, 4.4), constrained_layout=True)
    if len(targets) == 1:
        axes = [axes]
    for axis, target in zip(axes, targets):
        group = [row for row in rows if row["target_type"] == target]
        values = [float(row["specific_ig_bits_per_target_token"]) for row in group]
        labels = [f"S{index + 1}" for index in range(len(group))]
        colors = ["#2878B5" if value >= 0 else "#C82423" for value in values]
        axis.bar(labels, values, color=colors, width=0.72)
        axis.axhline(0, color="#333333", linewidth=0.8)
        axis.set_title(target.replace("_", " "))
        axis.set_xlabel("State")
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.6)
    axes[0].set_ylabel("Specific IG (bits / target token)")
    fig.savefig(out_dir / "specific_ig_three_targets.png", dpi=240)
    fig.savefig(out_dir / "specific_ig_three_targets.pdf")
    plt.close(fig)


def run(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    analyze_three_targets(
        Path(args.aggregates),
        out_dir,
        expected_state_count=args.expected_state_count,
        target_types=tuple(args.target_types),
        reference_artifact=args.reference_artifact,
        control_artifacts=tuple(args.control_artifacts),
    )
    if not args.no_plot:
        _plot(out_dir)


def add_three_target_analysis_parser(subparsers) -> None:
    parser = subparsers.add_parser("ig-three-target-analyze", help="analyze action, patch, and full-proof IG")
    parser.add_argument("--aggregates", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--expected-state-count", type=int, default=6)
    parser.add_argument("--target-types", nargs="+", default=list(TARGET_TYPES))
    parser.add_argument("--reference-artifact", default=REFERENCE_ARTIFACT)
    parser.add_argument("--control-artifacts", nargs="+", default=list(CONTROL_ARTIFACTS))
    parser.add_argument("--no-plot", action="store_true")
    parser.set_defaults(func=run)
