#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


COVERAGE_COLOR = "#5B0DAD"
TIER_LINE_COLOR = "#5BBCCA"
TIER_COLORS = {0: "#C94C4C", 1: "#E59B3A", 2: "#2B8C6B"}
TIER_LABELS = {0: "Compile failure / unparsed", 1: "Proof failure", 2: "Verified"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls-csv", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--title", default="Verifier-call proof progress by output tokens"
    )
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite existing output: {output}")
    with args.calls_csv.resolve().open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    summary = json.loads(args.summary_json.resolve().read_text(encoding="utf-8"))
    if not rows:
        raise ValueError("calls CSV is empty")

    tokens = [int(row["cumulative_output_tokens"]) for row in rows]
    coverage = [100.0 * float(row["proof_coverage"]) for row in rows]
    tiers = [int(row["verifier_tier"]) for row in rows]

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "text.usetex": False,
        }
    )
    figure, (coverage_axis, tier_axis) = plt.subplots(
        2,
        1,
        figsize=(8.8, 6.2),
        sharex=True,
        gridspec_kw={"height_ratios": [2.0, 1.0], "hspace": 0.10},
    )

    for segment in summary.get("stagnation_segments", []):
        for axis in (coverage_axis, tier_axis):
            axis.axvspan(
                segment["start_output_tokens"],
                segment["end_output_tokens"],
                color="#D9D9D9",
                alpha=0.32,
                linewidth=0,
                zorder=0,
            )

    coverage_axis.plot(
        tokens,
        coverage,
        color=COVERAGE_COLOR,
        marker="o",
        markersize=5.2,
        linewidth=1.8,
        zorder=3,
    )
    coverage_axis.set_ylim(-3, 103)
    coverage_axis.set_yticks([0, 25, 50, 75, 100])
    coverage_axis.set_ylabel("Pruned-final proof\ncoverage (%)", fontweight="bold")
    coverage_axis.set_title(args.title, fontsize=13, fontweight="bold", pad=10)

    pruning = summary["pruning"]
    coverage_axis.text(
        0.015,
        0.965,
        (
            f"Greedy pruning removed {pruning['removed_lines']}/"
            f"{pruning['final_proof_nonblank_lines']} lines "
            f"({100 * pruning['removable_fraction_of_final_proof_lines']:.1f}%); "
            f"{100 * pruning['assert_share_of_removed_lines']:.1f}% were asserts"
        ),
        transform=coverage_axis.transAxes,
        ha="left",
        va="top",
        fontsize=8.7,
        color="#333333",
    )

    tier_axis.plot(
        tokens,
        tiers,
        color=TIER_LINE_COLOR,
        linewidth=1.5,
        drawstyle="steps-post",
        zorder=2,
    )
    tier_axis.scatter(
        tokens,
        tiers,
        c=[TIER_COLORS[tier] for tier in tiers],
        edgecolors="white",
        linewidths=0.8,
        s=52,
        zorder=3,
    )
    tier_axis.set_ylim(-0.25, 2.25)
    tier_axis.set_yticks([0, 1, 2])
    tier_axis.set_ylabel("Verifier tier", fontweight="bold")
    tier_axis.set_xlabel("Cumulative output tokens", fontweight="bold")
    tier_axis.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"{value / 1000:.0f}k" if value else "0")
    )

    first_verified = next(
        (token for token, tier in zip(tokens, tiers) if tier == 2), None
    )
    if first_verified is not None:
        for axis in (coverage_axis, tier_axis):
            axis.axvline(first_verified, color=TIER_COLORS[2], linestyle="--", lw=1.0)
        coverage_axis.annotate(
            "First verified",
            xy=(first_verified, 100),
            xytext=(-74, -28),
            textcoords="offset points",
            color=TIER_COLORS[2],
            fontsize=9,
            fontweight="bold",
            arrowprops={"arrowstyle": "->", "color": TIER_COLORS[2], "lw": 1.0},
        )
        post_pass = summary.get("post_first_verified", {})
        extra_calls = int(post_pass.get("additional_verifier_calls") or 0)
        extra_tokens = int(post_pass.get("additional_output_tokens") or 0)
        if extra_calls:
            coverage_axis.text(
                0.985,
                0.82,
                f"Post-pass validation\n+{extra_tokens:,} tokens, {extra_calls} calls",
                transform=coverage_axis.transAxes,
                ha="right",
                va="top",
                fontsize=8.5,
                color=TIER_COLORS[2],
            )

    for axis in (coverage_axis, tier_axis):
        axis.grid(False)
        axis.tick_params(labelsize=10, direction="out", length=4, width=0.8)
        for spine in axis.spines.values():
            spine.set_linewidth(1.0)

    handles = [
        mlines.Line2D(
            [],
            [],
            color=TIER_COLORS[tier],
            marker="o",
            linestyle="None",
            markersize=6,
            label=f"{tier}: {TIER_LABELS[tier]}",
        )
        for tier in (0, 1, 2)
    ]
    handles.append(
        mlines.Line2D(
            [],
            [],
            color="#D9D9D9",
            linewidth=7,
            alpha=0.7,
            label="Search stagnation",
        )
    )
    figure.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.005),
        fontsize=8.3,
        frameon=True,
        facecolor="white",
        edgecolor="#AAAAAA",
        framealpha=1.0,
        ncol=4,
        handletextpad=0.4,
        columnspacing=1.0,
    )
    figure.subplots_adjust(left=0.14, right=0.98, top=0.91, bottom=0.19)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=300, facecolor="white", bbox_inches="tight")
    plt.close(figure)
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
