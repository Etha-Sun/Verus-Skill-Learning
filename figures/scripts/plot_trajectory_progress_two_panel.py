#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt


PATCH_COLOR = "#5B0DAD"
TIER_LINE_COLOR = "#5BBCCA"
TIER_COLORS = {
    0: "#C94C4C",
    1: "#E59B3A",
    2: "#2B8C6B",
}
TIER_LABELS = {
    0: "Compile failure / unparsed",
    1: "Proof failure",
    2: "Verified",
}


def _load_rows(csv_path: Path, task_id: str, step: str) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["task_id"] == task_id and row["step"] == step
        ]
    rows.sort(key=lambda row: int(row["checkpoint_ordinal"]))
    if not rows:
        raise ValueError(f"no checkpoint rows for task {task_id!r} and step {step!r}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite existing output: {output}")
    rows = _load_rows(args.input_csv.resolve(), args.task_id, args.step)
    checkpoints = [int(row["checkpoint_ordinal"]) for row in rows]
    patch_f1 = [float(row["patch_f1"]) for row in rows]
    tiers = [round(float(row["verifier_tier"]) * 2) for row in rows]

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "text.usetex": False,
        }
    )
    figure, (patch_axis, tier_axis) = plt.subplots(
        2,
        1,
        figsize=(8.6, 6.1),
        sharex=True,
        gridspec_kw={"height_ratios": [2.0, 1.0], "hspace": 0.10},
    )

    patch_axis.plot(
        checkpoints,
        patch_f1,
        color=PATCH_COLOR,
        marker="o",
        markersize=5.5,
        linewidth=1.8,
        zorder=3,
    )
    patch_axis.set_ylim(0.65, 1.02)
    patch_axis.set_yticks([0.7, 0.8, 0.9, 1.0])
    patch_axis.set_ylabel("Patch F1", fontsize=12, fontweight="bold")
    patch_axis.set_title(
        "Verifier-gated trajectory progress",
        fontsize=13,
        fontweight="bold",
        pad=10,
    )

    tier_axis.plot(
        checkpoints,
        tiers,
        color=TIER_LINE_COLOR,
        linewidth=1.5,
        drawstyle="steps-mid",
        zorder=2,
    )
    tier_axis.scatter(
        checkpoints,
        tiers,
        c=[TIER_COLORS[tier] for tier in tiers],
        edgecolors="white",
        linewidths=0.8,
        s=52,
        zorder=3,
    )
    tier_axis.set_ylim(-0.25, 2.25)
    tier_axis.set_yticks([0, 1, 2])
    tier_axis.set_ylabel("Verifier tier", fontsize=12, fontweight="bold")
    tier_axis.set_xlabel("Verifier checkpoint", fontsize=12, fontweight="bold")
    tier_axis.set_xticks(checkpoints)

    for axis in (patch_axis, tier_axis):
        axis.grid(False)
        axis.tick_params(labelsize=10, direction="out", length=4, width=0.8)
        for spine in axis.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(1.0)

    regression_indices = [
        index
        for index in range(1, len(tiers))
        if tiers[index - 1] == 2 and tiers[index] < 2
    ]
    if regression_indices:
        index = regression_indices[0]
        checkpoint = checkpoints[index]
        patch_axis.annotate(
            f"Patch F1 rises ({patch_f1[index] - patch_f1[index - 1]:+.2f})",
            xy=(checkpoint, patch_f1[index]),
            xytext=(checkpoint - 2.0, min(1.005, patch_f1[index] + 0.06)),
            fontsize=9,
            color=PATCH_COLOR,
            arrowprops={"arrowstyle": "->", "color": PATCH_COLOR, "lw": 1.0},
        )
        tier_axis.annotate(
            "Verifier regresses (2 → 1)",
            xy=(checkpoint, tiers[index]),
            xytext=(checkpoint - 2.0, tiers[index] - 0.70),
            fontsize=9,
            fontweight="bold",
            color=TIER_COLORS[0],
            arrowprops={"arrowstyle": "->", "color": TIER_COLORS[0], "lw": 1.0},
        )

    legend_handles = [
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
    figure.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.005),
        fontsize=8.5,
        frameon=True,
        facecolor="white",
        edgecolor="#AAAAAA",
        framealpha=1.0,
        ncol=3,
        handletextpad=0.4,
        columnspacing=1.1,
    )

    figure.subplots_adjust(left=0.12, right=0.98, top=0.91, bottom=0.19)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=300, facecolor="white", bbox_inches="tight")
    plt.close(figure)
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
