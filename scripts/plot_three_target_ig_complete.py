from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


TARGETS = ("action_primary", "patch_span", "full_proof")
TARGET_LABELS = {
    "action_primary": "Action",
    "patch_span": "Proof patch",
    "full_proof": "Full proof",
}
CONTROLS = (
    "cross_trace_same_error",
    "cross_trace_any",
    "block_shuffled",
    "counterfactual_error",
    "irrelevant_archive",
)
CONTROL_LABELS = {
    "cross_trace_same_error": "Same-error\nother trace",
    "cross_trace_any": "Any other\ntrace",
    "block_shuffled": "Shuffled\nevidence",
    "counterfactual_error": "Wrong-error\nevidence",
    "irrelevant_archive": "Irrelevant\narchive",
}
ARTIFACTS = (
    "evidence_artifact",
    *CONTROLS,
    "empty_container",
)
ARTIFACT_LABELS = {
    "evidence_artifact": "Evidence",
    "cross_trace_same_error": "Same-error trace",
    "cross_trace_any": "Any other trace",
    "block_shuffled": "Shuffled",
    "counterfactual_error": "Wrong error",
    "irrelevant_archive": "Irrelevant",
    "empty_container": "Empty wrapper",
}
ARTIFACT_COLORS = {
    "evidence_artifact": "#0072B2",
    "cross_trace_same_error": "#009E73",
    "cross_trace_any": "#56B4E9",
    "block_shuffled": "#E69F00",
    "counterfactual_error": "#D55E00",
    "irrelevant_archive": "#CC79A7",
    "empty_container": "#6E6E6E",
}
ARTIFACT_MARKERS = {
    "evidence_artifact": "D",
    "cross_trace_same_error": "o",
    "cross_trace_any": "o",
    "block_shuffled": "s",
    "counterfactual_error": "v",
    "irrelevant_archive": "P",
    "empty_container": "x",
}
TRACE_COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )


def save_figure(fig, out_dir: Path, stem: str) -> list[str]:
    outputs = []
    for suffix in ("png", "pdf", "svg"):
        path = out_dir / f"{stem}.{suffix}"
        fig.savefig(path, dpi=300 if suffix == "png" else None)
        outputs.append(str(path))
    plt.close(fig)
    return outputs


def state_metadata(mapping_rows: list[dict[str, str]]) -> tuple[list[str], dict[str, str], dict[str, str]]:
    states = [row["sample_id"] for row in mapping_rows]
    labels = {row["sample_id"]: row["figure_label"] for row in mapping_rows}
    traces = {row["sample_id"]: row["trace_id"] for row in mapping_rows}
    return states, labels, traces


def trace_palette(traces: dict[str, str]) -> dict[str, str]:
    unique = list(dict.fromkeys(traces.values()))
    return {trace: TRACE_COLORS[index % len(TRACE_COLORS)] for index, trace in enumerate(unique)}


def format_axis(axis) -> None:
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.grid(axis="y", color="#D9D9D9", linewidth=0.6, alpha=0.8)
    axis.set_axisbelow(True)


def figure_raw_landscape(
    aggregates: list[dict[str, object]],
    states: list[str],
    state_labels: dict[str, str],
    out_dir: Path,
) -> list[str]:
    by_key = {
        (str(row["sample_id"]), str(row["target_type"]), str(row["artifact_type"])): row
        for row in aggregates
    }
    offsets = {artifact: (index - 3) * 0.075 for index, artifact in enumerate(ARTIFACTS)}
    fig, axes = plt.subplots(1, 3, figsize=(17.2, 5.4), constrained_layout=True)
    for axis, target in zip(axes, TARGETS):
        evidence_values = []
        for state_index, state in enumerate(states, start=1):
            matched_values = []
            evidence_value = None
            for artifact in ARTIFACTS:
                row = by_key[(state, target, artifact)]
                value = float(row["target_loglikelihood_ig_bits"]) / int(row["target_token_count"])
                if artifact in CONTROLS:
                    matched_values.append(value)
                if artifact == "evidence_artifact":
                    evidence_value = value
                    evidence_values.append(value)
                axis.scatter(
                    state_index + offsets[artifact],
                    value,
                    s=55 if artifact == "evidence_artifact" else 34,
                    marker=ARTIFACT_MARKERS[artifact],
                    color=ARTIFACT_COLORS[artifact],
                    edgecolor="white" if ARTIFACT_MARKERS[artifact] != "x" else None,
                    linewidth=0.6,
                    zorder=4 if artifact == "evidence_artifact" else 3,
                )
            control_mean = mean(matched_values)
            axis.scatter(state_index, control_mean, marker="_", s=260, color="#111111", linewidth=2.0, zorder=5)
            axis.plot(
                [state_index, state_index],
                [control_mean, evidence_value],
                color="#999999",
                linewidth=0.8,
                zorder=1,
            )
        axis.axhline(0, color="#222222", linewidth=0.9)
        axis.set_xticks(range(1, len(states) + 1), [state_labels[state] for state in states])
        axis.set_xlabel("Trajectory state")
        axis.set_title(TARGET_LABELS[target])
        format_axis(axis)
        axis.text(
            0.02,
            0.98,
            f"Evidence raw mean: {mean(evidence_values):+.4f}\n"
            f"median: {median(evidence_values):+.4f}\n"
            f"positive: {sum(value > 0 for value in evidence_values)}/6",
            transform=axis.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"boxstyle": "square,pad=0.35", "facecolor": "white", "edgecolor": "#BDBDBD", "alpha": 0.92},
        )
    axes[0].set_ylabel("Raw IG (bits / target token)")
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=ARTIFACT_MARKERS[artifact],
            color="none",
            markerfacecolor=ARTIFACT_COLORS[artifact],
            markeredgecolor=ARTIFACT_COLORS[artifact],
            markersize=7,
            label=ARTIFACT_LABELS[artifact],
        )
        for artifact in ARTIFACTS
    ]
    legend_handles.append(Line2D([0], [0], marker="_", color="#111111", markersize=14, linewidth=0, label="Matched-control mean"))
    fig.legend(handles=legend_handles, loc="outside lower center", ncol=4, frameon=False)
    fig.suptitle("All raw artifact effects: every state, target, and control", fontsize=15)
    return save_figure(fig, out_dir, "fig1_raw_artifact_landscape")


def figure_specific_statewise(
    specific_rows: list[dict[str, str]],
    target_summary: list[dict[str, str]],
    states: list[str],
    state_labels: dict[str, str],
    traces: dict[str, str],
    out_dir: Path,
) -> list[str]:
    by_key = {(row["sample_id"], row["target_type"]): row for row in specific_rows}
    summary = {row["target_type"]: row for row in target_summary}
    palette = trace_palette(traces)
    fig, axes = plt.subplots(1, 3, figsize=(16.2, 5.2), constrained_layout=True)
    for axis, target in zip(axes, TARGETS):
        values = [float(by_key[(state, target)]["specific_ig_bits_per_target_token"]) for state in states]
        for index, (state, value) in enumerate(zip(states, values), start=1):
            axis.vlines(index, 0, value, color=palette[traces[state]], linewidth=1.2, alpha=0.75)
            axis.scatter(index, value, s=58, color=palette[traces[state]], edgecolor="white", linewidth=0.7, zorder=3)
        value_mean = mean(values)
        value_median = median(values)
        axis.axhline(0, color="#222222", linewidth=0.9)
        axis.axhline(value_mean, color="#111111", linewidth=1.5, label="Mean")
        axis.axhline(value_median, color="#666666", linewidth=1.2, linestyle="--", label="Median")
        axis.set_xticks(range(1, len(states) + 1), [state_labels[state] for state in states])
        axis.set_xlabel("Trajectory state")
        axis.set_title(TARGET_LABELS[target])
        row = summary[target]
        axis.text(
            0.02,
            0.98,
            f"Mean total: {float(row['mean_specific_total_ig_bits']):+.3f} bits\n"
            f"Mean/token: {float(row['mean_specific_ig_bits_per_target_token']):+.5f}\n"
            f"Median/token: {float(row['median_specific_ig_bits_per_target_token']):+.5f}\n"
            f"Positive: {row['positive_specific_state_count']}/6",
            transform=axis.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"boxstyle": "square,pad=0.35", "facecolor": "white", "edgecolor": "#BDBDBD", "alpha": 0.92},
        )
        format_axis(axis)
    axes[0].set_ylabel("Specific IG (bits / target token)")
    trace_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor="white", markersize=8, label=f"Trace {index + 1}")
        for index, (_, color) in enumerate(trace_palette(traces).items())
    ]
    trace_handles.extend(
        [
            Line2D([0], [0], color="#111111", linewidth=1.5, label="Mean"),
            Line2D([0], [0], color="#666666", linewidth=1.2, linestyle="--", label="Median"),
        ]
    )
    fig.legend(handles=trace_handles, loc="outside lower center", ncol=5, frameon=False)
    fig.suptitle("State-wise evidence gain after matched-control correction", fontsize=15)
    return save_figure(fig, out_dir, "fig2_statewise_specific_ig")


def figure_control_small_multiples(
    paired_rows: list[dict[str, str]],
    states: list[str],
    state_labels: dict[str, str],
    traces: dict[str, str],
    out_dir: Path,
) -> list[str]:
    by_cell: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in paired_rows:
        by_cell[(row["target_type"], row["control_artifact"])].append(row)
    order = {state: index for index, state in enumerate(states)}
    palette = trace_palette(traces)
    row_limits = {}
    for target in TARGETS:
        values = [
            float(row["specific_ig_bits_per_target_token"])
            for control in CONTROLS
            for row in by_cell[(target, control)]
        ]
        bound = max(abs(min(values)), abs(max(values))) * 1.15
        row_limits[target] = (-bound, bound)
    fig, axes = plt.subplots(3, 5, figsize=(18.5, 11.8), constrained_layout=True)
    for row_index, target in enumerate(TARGETS):
        for column_index, control in enumerate(CONTROLS):
            axis = axes[row_index][column_index]
            rows = sorted(by_cell[(target, control)], key=lambda row: order[row["sample_id"]])
            values = [float(row["specific_ig_bits_per_target_token"]) for row in rows]
            for index, (state, value) in enumerate(zip(states, values), start=1):
                axis.scatter(index, value, s=34, color=palette[traces[state]], edgecolor="white", linewidth=0.5, zorder=3)
            axis.scatter(7, mean(values), marker="D", s=48, color="#111111", zorder=4)
            axis.scatter(7, median(values), marker="_", s=170, color="#666666", linewidth=1.8, zorder=5)
            axis.axhline(0, color="#222222", linewidth=0.8)
            axis.set_xlim(0.5, 7.5)
            axis.set_ylim(*row_limits[target])
            axis.set_xticks(range(1, 8), [*[state_labels[state] for state in states], "Mean"])
            axis.tick_params(axis="x", rotation=45)
            if row_index == 0:
                axis.set_title(CONTROL_LABELS[control], pad=38)
            if column_index == 0:
                axis.set_ylabel(f"{TARGET_LABELS[target]}\nEvidence - control\n(bits / target token)")
            wins = sum(value > 0 for value in values)
            axis.text(
                0.5,
                1.01,
                f"wins {wins}/6 | mean {mean(values):+.4g} | median {median(values):+.4g}",
                transform=axis.transAxes,
                va="bottom",
                ha="center",
                fontsize=7.6,
            )
            format_axis(axis)
    fig.suptitle("Evidence versus each matched control: all 90 paired state-level differences", fontsize=15)
    return save_figure(fig, out_dir, "fig3_control_paired_differences")


def figure_cross_target(
    specific_rows: list[dict[str, str]],
    correlation_rows: list[dict[str, str]],
    states: list[str],
    state_labels: dict[str, str],
    traces: dict[str, str],
    out_dir: Path,
) -> list[str]:
    values = {
        (row["sample_id"], row["target_type"]): float(row["specific_ig_bits_per_target_token"])
        for row in specific_rows
    }
    correlations = {(row["left_target_type"], row["right_target_type"]): row for row in correlation_rows}
    pairs = (
        ("action_primary", "patch_span"),
        ("action_primary", "full_proof"),
        ("patch_span", "full_proof"),
    )
    palette = trace_palette(traces)
    fig, axes = plt.subplots(1, 3, figsize=(15.8, 5.0), constrained_layout=True)
    for axis, pair in zip(axes, pairs):
        left, right = pair
        for state in states:
            x_value = values[(state, left)]
            y_value = values[(state, right)]
            axis.scatter(x_value, y_value, s=62, color=palette[traces[state]], edgecolor="white", linewidth=0.7)
            axis.annotate(state_labels[state], (x_value, y_value), xytext=(4, 4), textcoords="offset points", fontsize=8)
        axis.axhline(0, color="#777777", linewidth=0.7)
        axis.axvline(0, color="#777777", linewidth=0.7)
        axis.margins(x=0.10, y=0.14)
        axis.set_xlabel(f"{TARGET_LABELS[left]} specific IG/token")
        axis.set_ylabel(f"{TARGET_LABELS[right]} specific IG/token")
        row = correlations[pair]
        axis.text(
            0.03,
            0.97,
            f"Spearman: {float(row['spearman_specific_per_token']):.3f}\n"
            f"Pearson: {float(row['pearson_specific_per_token']):.3f}\n"
            f"Sign agreement: {row['sign_agreement_count']}/6",
            transform=axis.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"boxstyle": "square,pad=0.35", "facecolor": "white", "edgecolor": "#BDBDBD", "alpha": 0.92},
        )
        format_axis(axis)
    fig.suptitle("Cross-target agreement of state-level specific information gain", fontsize=15)
    return save_figure(fig, out_dir, "fig4_cross_target_agreement")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render complete three-target IG visualizations")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    analysis_dir = run_dir / "analysis"
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    configure_style()

    aggregates_path = run_dir / "aggregates.jsonl"
    specific_path = analysis_dir / "specific_state_gain.csv"
    paired_path = analysis_dir / "paired_control_differences.csv"
    target_summary_path = analysis_dir / "target_summary.csv"
    correlations_path = analysis_dir / "cross_target_correlations.csv"
    mapping_path = analysis_dir / "state_mapping.csv"

    aggregates = read_jsonl(aggregates_path)
    specific_rows = read_csv(specific_path)
    paired_rows = read_csv(paired_path)
    target_summary = read_csv(target_summary_path)
    correlation_rows = read_csv(correlations_path)
    mapping_rows = read_csv(mapping_path)
    states, state_labels, traces = state_metadata(mapping_rows)

    outputs = []
    outputs.extend(figure_raw_landscape(aggregates, states, state_labels, out_dir))
    outputs.extend(figure_specific_statewise(specific_rows, target_summary, states, state_labels, traces, out_dir))
    outputs.extend(figure_control_small_multiples(paired_rows, states, state_labels, traces, out_dir))
    outputs.extend(figure_cross_target(specific_rows, correlation_rows, states, state_labels, traces, out_dir))

    manifest = {
        "run_dir": str(run_dir),
        "state_count": len(states),
        "aggregate_point_count": len(aggregates),
        "specific_point_count": len(specific_rows),
        "paired_control_point_count": len(paired_rows),
        "target_types": list(TARGETS),
        "controls": list(CONTROLS),
        "inputs": {
            str(path): sha256_file(path)
            for path in (
                aggregates_path,
                specific_path,
                paired_path,
                target_summary_path,
                correlations_path,
                mapping_path,
            )
        },
        "outputs": outputs,
        "notes": [
            "All cross-target panels use bits per target token.",
            "Each target panel has its own y-axis because target scales differ substantially.",
            "Means and medians are descriptive only; six states come from three trace clusters.",
        ],
    }
    (out_dir / "visualization_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
