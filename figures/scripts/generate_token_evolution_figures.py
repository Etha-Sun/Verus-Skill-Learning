from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Rectangle


PROFILE_SHORT = {
    "baseline": "H0",
    "aggressive": "A",
    "conservative": "C",
    "structural": "S",
}
TASK_COLORS = {
    "Direct": "#4C78A8",
    "Closest": "#E07A5F",
    "Unstable": "#59A14F",
    "Hard": "#9C6ADE",
}


def _configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.size": 8.5,
            "font.family": "serif",
            "font.serif": ["DejaVu Serif"],
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 8,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.04,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 76:
        raise ValueError(f"expected 76 task-condition rows, found {len(rows)}")
    return rows


def _float(value: str) -> float | None:
    return None if value == "" else float(value)


def _condition_rows(rows: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    by_order: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        by_order.setdefault(int(row["row_order"]), []).append(row)
    conditions = []
    for order in sorted(by_order):
        condition = sorted(by_order[order], key=lambda row: int(row["task_order"]))
        if len(condition) != 4:
            raise ValueError(f"condition {order} does not cover four tasks")
        conditions.append(condition)
    return conditions


def _row_label(condition: list[dict[str, str]]) -> str:
    row = condition[0]
    if row["round"] == "H0":
        return "H0  no skill"
    return (
        f"{row['round']}  {PROFILE_SHORT[row['profile']]}  "
        f"{row['skill_id'].replace('-', ' ')}"
    )


def _text_color(delta: float) -> str:
    return "white" if delta <= -24 or delta >= 62 else "#202020"


def _save(fig: mpl.figure.Figure, out_dir: Path, stem: str) -> dict[str, str]:
    outputs = {}
    for suffix in ("pdf", "svg", "png"):
        path = out_dir / f"{stem}.{suffix}"
        fig.savefig(path)
        outputs[suffix] = str(path)
    return outputs


def draw_heatmap(
    conditions: list[list[dict[str, str]]], out_dir: Path
) -> dict[str, str]:
    cmap = LinearSegmentedColormap.from_list(
        "token_delta", ["#3B6EA8", "#F6F4EF", "#C9644A"]
    )
    norm = TwoSlopeNorm(vmin=-40, vcenter=0, vmax=100)
    task_labels = [
        f"{row['task_class']}\n{row['task_id']}"
        for row in conditions[0]
    ]
    task_labels = [
        label.replace("seq_filter_contains_implies_seq_contains", "seq filter")
        .replace("marshal_v__impl2__lemma_serialize_injective", "serialize injective")
        .replace(
            "marshal_v__impl5__lemma_same_views_serialize_the_same",
            "same-view serialize",
        )
        .replace(
            "delegation_map_v__impl4__range_consistent_impl",
            "range consistent",
        )
        for label in task_labels
    ]
    n_rows = len(conditions)
    fig = plt.figure(figsize=(10.2, 8.7))
    grid = fig.add_gridspec(
        1,
        2,
        width_ratios=[4.3, 1.7],
        left=0.33,
        right=0.98,
        top=0.92,
        bottom=0.10,
        wspace=0.08,
    )
    ax = fig.add_subplot(grid[0, 0])
    aggregate_ax = fig.add_subplot(grid[0, 1], sharey=ax)

    for y, condition in enumerate(conditions):
        for x, row in enumerate(condition):
            status = row["run_status"]
            delta = _float(row["delta_pct"])
            tokens = _float(row["tokens"])
            if status == "valid" and delta is not None:
                face = cmap(norm(delta))
                text = (
                    f"{tokens / 1000:.1f}k\nbaseline"
                    if row["round"] == "H0"
                    else f"{tokens / 1000:.1f}k\n{delta:+.1f}%"
                )
                color = _text_color(delta)
                hatch = None
            elif status == "failed":
                face, color, hatch = "#D9D7D1", "#6F1D1B", "///"
                text = f"FAIL\n{tokens / 1000:.1f}k" if tokens is not None else "FAIL"
            else:
                face, color, hatch = "#C8C8C8", "#444444", "xx"
                text = "NO USAGE" if status == "no_usage" else "INVALID"
            patch = Rectangle(
                (x - 0.5, y - 0.5),
                1,
                1,
                facecolor=face,
                edgecolor="white",
                linewidth=1.1,
                hatch=hatch,
            )
            ax.add_patch(patch)
            ax.text(
                x,
                y,
                text,
                ha="center",
                va="center",
                color=color,
                fontsize=7.1,
                linespacing=1.15,
            )

    labels = [_row_label(condition) for condition in conditions]
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(n_rows - 0.5, -0.5)
    ax.set_xticks(range(4), task_labels)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=7)
    ax.set_yticks(range(n_rows), labels)
    ax.tick_params(axis="y", length=0, pad=5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for boundary in (0.5, 3.5, 6.5, 9.5, 12.5, 15.5):
        ax.axhline(boundary, color="#4A4A4A", linewidth=0.75, clip_on=False)
        aggregate_ax.axhline(
            boundary, color="#4A4A4A", linewidth=0.75, clip_on=False
        )

    aggregate_values = []
    for y, condition in enumerate(conditions):
        row = condition[0]
        valid = row["matrix_valid"] == "true"
        delta = _float(row["aggregate_delta_pct"])
        etts = _float(row["etts"])
        solved = int(row["solve_count"])
        if valid and delta is not None and etts is not None:
            aggregate_values.append(delta)
            bar_color = "#3B6EA8" if delta < 0 else "#C9644A"
            if abs(delta) < 0.05:
                bar_color = "#8B8B86"
            aggregate_ax.barh(
                y,
                delta,
                height=0.58,
                color=bar_color,
                edgecolor="none",
                zorder=2,
            )
            x_text = delta + (1.2 if delta >= 0 else -1.2)
            ha = "left" if delta >= 0 else "right"
            aggregate_ax.text(
                x_text,
                y,
                f"{etts / 1000:.1f}k  {solved}/4",
                va="center",
                ha=ha,
                fontsize=7.2,
                color="#202020",
            )
        else:
            aggregate_ax.text(
                2,
                y,
                f"× invalid  {solved}/4",
                va="center",
                ha="left",
                fontsize=7.2,
                color="#6F1D1B",
            )
    aggregate_ax.axvline(0, color="#303030", linewidth=0.8, zorder=1)
    aggregate_ax.set_xlim(-8, max(85, max(aggregate_values) + 18))
    aggregate_ax.set_xlabel("Aggregate ETtS Δ vs H0 (%)\n← fewer tokens")
    aggregate_ax.xaxis.set_label_position("top")
    aggregate_ax.xaxis.tick_top()
    aggregate_ax.tick_params(axis="y", left=False, labelleft=False)
    aggregate_ax.grid(axis="x", color="#D8D6D0", linewidth=0.5, zorder=0)
    aggregate_ax.spines["left"].set_visible(False)
    aggregate_ax.spines["bottom"].set_visible(False)
    aggregate_ax.spines["top"].set_visible(False)

    scalar = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    colorbar = fig.colorbar(
        scalar,
        ax=ax,
        orientation="horizontal",
        fraction=0.035,
        pad=0.055,
        aspect=45,
        extend="both",
    )
    colorbar.set_label("Per-task primary uncached token change vs H0 (%)")
    colorbar.outline.set_linewidth(0.5)
    outputs = _save(fig, out_dir, "token_evolution_skill_heatmap")
    plt.close(fig)
    return outputs


def draw_round_best(
    conditions: list[list[dict[str, str]]], out_dir: Path
) -> dict[str, str]:
    selected = [conditions[0]]
    selected_ids = ["no skill"]
    for round_index in range(1, 7):
        candidates = [
            condition
            for condition in conditions
            if condition[0]["round"] == f"R{round_index}"
            and condition[0]["matrix_valid"] == "true"
            and _float(condition[0]["etts"]) is not None
        ]
        best = min(candidates, key=lambda row: float(row[0]["etts"]))
        selected.append(best)
        selected_ids.append(best[0]["skill_id"])

    x = np.arange(7)
    fig, (ax, agg_ax) = plt.subplots(
        1,
        2,
        figsize=(10.2, 3.35),
        gridspec_kw={"width_ratios": [2.25, 1]},
    )
    task_classes = [row["task_class"] for row in selected[0]]
    for task_index, task_class in enumerate(task_classes):
        values = [
            float(condition[task_index]["tokens"]) / 1000 for condition in selected
        ]
        ax.plot(
            x,
            values,
            color=TASK_COLORS[task_class],
            marker="o",
            linewidth=1.7,
            markersize=4,
            label=task_class,
        )
    ax.set_xticks(x, ["H0", "R1", "R2", "R3", "R4", "R5", "R6"])
    ax.set_ylabel("Primary uncached tokens (thousands)")
    ax.set_xlabel("Evolution round; each round uses its best admissible skill")
    ax.grid(axis="y", color="#D8D6D0", linewidth=0.55)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13))

    aggregate = [float(condition[0]["etts"]) / 1000 for condition in selected]
    agg_ax.plot(
        x,
        aggregate,
        color="#333333",
        marker="o",
        linewidth=1.8,
        markersize=4,
    )
    agg_ax.axhline(52.35, color="#8B8B86", linestyle="--", linewidth=1)
    for index, value in enumerate(aggregate):
        agg_ax.text(index, value + 0.7, f"{value:.1f}", ha="center", fontsize=7)
    agg_ax.set_xticks(x, ["H0", "R1", "R2", "R3", "R4", "R5", "R6"])
    agg_ax.set_ylabel("ETtS (thousands)")
    agg_ax.set_xlabel("Round-best aggregate")
    agg_ax.set_ylim(min(aggregate) - 2.5, max(aggregate) + 3.5)
    agg_ax.grid(axis="y", color="#D8D6D0", linewidth=0.55)
    fig.tight_layout()
    outputs = _save(fig, out_dir, "token_evolution_round_best")
    plt.close(fig)

    (out_dir / "token_evolution_round_best_selection.json").write_text(
        json.dumps(
            {
                "rounds": ["H0", "R1", "R2", "R3", "R4", "R5", "R6"],
                "selected_skill_ids": selected_ids,
                "etts": [float(condition[0]["etts"]) for condition in selected],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    _configure_style()
    rows = _read_rows(args.input)
    conditions = _condition_rows(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "heatmap": draw_heatmap(conditions, args.out_dir),
        "round_best": draw_round_best(conditions, args.out_dir),
    }
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
