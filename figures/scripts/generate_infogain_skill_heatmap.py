from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm
from matplotlib.patches import Rectangle


PROFILE_SHORT = {"aggressive": "A", "conservative": "C", "structural": "S"}
TASK_SHORT = {
    "seq_filter_contains_implies_seq_contains": "Direct\nseq filter",
    "marshal_v__impl2__lemma_serialize_injective": "Closest\nserialize",
    "marshal_v__impl5__lemma_same_views_serialize_the_same": (
        "Unstable\nsame-view"
    ),
    "delegation_map_v__impl4__range_consistent_impl": (
        "Hard\nrange-consistent"
    ),
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
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.04,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _save(
    fig: mpl.figure.Figure, out_dir: Path, phase: str
) -> dict[str, str]:
    outputs = {}
    stem = (
        "infogain_pre_skill_heatmap"
        if phase == "pre"
        else "infogain_skill_heatmap"
    )
    for suffix in ("pdf", "svg", "png"):
        path = out_dir / f"{stem}.{suffix}"
        fig.savefig(path)
        outputs[suffix] = str(path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--phase", choices=("pre", "post"), default="post")
    args = parser.parse_args()
    _configure_style()

    task_rows = _read_csv(args.data_dir / "infogain_task_skill.csv")
    aggregate_rows = _read_csv(args.data_dir / "infogain_skill_aggregate.csv")
    if len(task_rows) != 36 or len(aggregate_rows) != 9:
        raise ValueError("expected 36 task rows and 9 aggregate rows")
    grouped: dict[tuple[int, int], list[dict[str, str]]] = {}
    for row in task_rows:
        grouped.setdefault(
            (int(row["round_order"]), int(row["profile_order"])), []
        ).append(row)
    conditions = [
        sorted(grouped[key], key=lambda row: int(row["task_order"]))
        for key in sorted(grouped)
    ]
    aggregate_by_key = {
        (int(row["round_order"]), int(row["profile_order"])): row
        for row in aggregate_rows
    }

    if args.phase == "pre":
        value_field = "pre_bits_per_target_token"
        aggregate_field = "mean_pre_bits_per_target_token"
        cmap = LinearSegmentedColormap.from_list(
            "signed_ig", ["#8F5D56", "#F3F0E8", "#356F78"]
        )
        norm = TwoSlopeNorm(vmin=-0.9, vcenter=0, vmax=0.3)
    else:
        value_field = "post_bits_per_target_token"
        aggregate_field = "mean_post_bits_per_target_token"
        cmap = LinearSegmentedColormap.from_list(
            "positive_ig", ["#F3F0E8", "#8FB6AE", "#356F78"]
        )
        norm = Normalize(vmin=0, vmax=0.6)
    fig = plt.figure(figsize=(10.2, 5.45))
    grid = fig.add_gridspec(
        1,
        2,
        width_ratios=[4.35, 2.25],
        left=0.34,
        right=0.98,
        top=0.82,
        bottom=0.16,
        wspace=0.09,
    )
    ax = fig.add_subplot(grid[0, 0])
    agg_ax = fig.add_subplot(grid[0, 1], sharey=ax)
    n_rows = len(conditions)

    for y, condition in enumerate(conditions):
        for x, row in enumerate(condition):
            if row["score_status"] == "complete":
                value = float(row[value_field])
                face, hatch = cmap(norm(value)), None
                if args.phase == "pre":
                    color = (
                        "white"
                        if value <= -0.48 or value >= 0.20
                        else "#202020"
                    )
                else:
                    color = "white" if value >= 0.35 else "#202020"
                text = f"{value:.3f}"
            else:
                face, hatch, color, text = "#D4D2CC", "xx", "#555555", "PENDING"
            ax.add_patch(
                Rectangle(
                    (x - 0.5, y - 0.5),
                    1,
                    1,
                    facecolor=face,
                    edgecolor="white",
                    linewidth=1.1,
                    hatch=hatch,
                )
            )
            ax.text(
                x,
                y,
                text,
                ha="center",
                va="center",
                fontsize=7.3 if text != "PENDING" else 6.8,
                color=color,
            )

    labels = []
    for condition in conditions:
        row = condition[0]
        skill = row["skill_id"].replace("_", " ")
        labels.append(
            f"{row['round']}  {PROFILE_SHORT[row['profile']]}  {skill}"
        )
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(n_rows - 0.5, -0.5)
    ax.set_xticks(
        range(4), [TASK_SHORT[row["task_id"]] for row in conditions[0]]
    )
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=7)
    ax.set_yticks(range(n_rows), labels)
    ax.tick_params(axis="y", length=0, pad=5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for y, condition in enumerate(conditions):
        row = condition[0]
        aggregate = aggregate_by_key[
            (int(row["round_order"]), int(row["profile_order"]))
        ]
        if aggregate["score_status"] == "complete":
            pre = float(aggregate["mean_pre_bits_per_target_token"])
            post = float(aggregate["mean_post_bits_per_target_token"])
            agg_ax.plot(
                [pre, post],
                [y, y],
                color="#9A968F",
                linewidth=1.3,
                zorder=1,
            )
            if args.phase == "pre":
                pre_color = "#356F78" if pre >= 0 else "#8F5D56"
                agg_ax.scatter(
                    [pre],
                    [y],
                    facecolor=pre_color,
                    edgecolor=pre_color,
                    s=29,
                    zorder=3,
                )
                agg_ax.scatter(
                    [post],
                    [y],
                    facecolor="white",
                    edgecolor="#6F6C67",
                    s=28,
                    linewidth=1,
                    zorder=2,
                )
            else:
                agg_ax.scatter(
                    [pre],
                    [y],
                    facecolor="white",
                    edgecolor="#6F6C67",
                    s=28,
                    linewidth=1,
                    zorder=2,
                )
                agg_ax.scatter(
                    [post],
                    [y],
                    facecolor="#356F78",
                    edgecolor="#356F78",
                    s=29,
                    zorder=3,
                )
            aggregate_value = float(aggregate[aggregate_field])
            offset = -0.018 if args.phase == "pre" and aggregate_value < 0 else 0.018
            agg_ax.text(
                aggregate_value + offset,
                y,
                f"{aggregate_value:.3f}",
                va="center",
                ha="right" if offset < 0 else "left",
                fontsize=7.2,
            )
        else:
            if row["profile"] == "conservative":
                agg_ax.text(
                    -0.04,
                    y,
                    "R3 scoring incomplete (all 3 skills)",
                    va="center",
                    color="#6F1D1B",
                    fontsize=7.0,
                )

    agg_ax.axvline(0, color="#303030", linewidth=0.8, zorder=0)
    agg_ax.set_xlim(-0.52, 0.34)
    agg_ax.set_xlabel(
        "Mean InfoGain (bits / target token)\n"
        + (
            "● pre summary   ○ post summary"
            if args.phase == "pre"
            else "○ pre summary   ● post summary"
        ),
        labelpad=8,
    )
    agg_ax.xaxis.set_label_position("top")
    agg_ax.xaxis.tick_top()
    agg_ax.tick_params(axis="y", left=False, labelleft=False)
    agg_ax.grid(axis="x", color="#D8D6D0", linewidth=0.5, zorder=0)
    agg_ax.spines["left"].set_visible(False)
    agg_ax.spines["bottom"].set_visible(False)
    agg_ax.spines["top"].set_visible(False)

    for boundary in (2.5, 5.5):
        ax.axhline(boundary, color="#4A4A4A", linewidth=0.75, clip_on=False)
        agg_ax.axhline(
            boundary, color="#4A4A4A", linewidth=0.75, clip_on=False
        )

    scalar = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    colorbar = fig.colorbar(
        scalar,
        ax=ax,
        orientation="horizontal",
        fraction=0.045,
        pad=0.085,
        aspect=40,
    )
    colorbar.set_label(
        f"{args.phase.capitalize()}-summary InfoGain (bits / target token)"
    )
    colorbar.outline.set_linewidth(0.5)
    fig.suptitle(
        (
            "Full-proof pre-summary InfoGain across skills and tasks"
            if args.phase == "pre"
            else "Full-proof InfoGain across skills and tasks"
        ),
        x=0.59,
        y=0.985,
        fontsize=11,
    )
    fig.text(
        0.34,
        0.025,
        (
            "Pre = skill content before first tool call; task H0 = "
            "no-summary (0). "
            if args.phase == "pre"
            else ""
        )
        + "Exact Qwen3.5-27B teacher forcing; R1/R2 complete; "
        "R3 partial scores excluded.",
        fontsize=7.4,
        color="#555555",
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps(_save(fig, args.out_dir, args.phase), indent=2))
    plt.close(fig)


if __name__ == "__main__":
    main()
