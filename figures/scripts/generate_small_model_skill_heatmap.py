from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


PROFILE_SHORT = {
    "baseline": "H0",
    "aggressive": "A",
    "conservative": "C",
    "structural": "S",
}
TASK_SHORT = {
    "seq_filter_contains_implies_seq_contains": "Direct\nseq filter",
    "marshal_v__impl2__lemma_serialize_injective": "Closest\nserialize injective",
    "marshal_v__impl5__lemma_same_views_serialize_the_same": (
        "Unstable\nsame-view serialize"
    ),
    "impl_u__wrapped_token__impl1__lemma_interps_match_aux1": (
        "Hard\nNRKernel interps"
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


def _read(path: Path) -> list[list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 40:
        raise ValueError(f"expected 40 rows, found {len(rows)}")
    grouped: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(int(row["condition_order"]), []).append(row)
    conditions = [
        sorted(grouped[index], key=lambda row: int(row["task_order"]))
        for index in sorted(grouped)
    ]
    if any(len(rows) != 4 for rows in conditions):
        raise ValueError("every condition must cover four tasks")
    return conditions


def _float(value: str) -> float | None:
    return None if value == "" else float(value)


def _label(rows: list[dict[str, str]]) -> str:
    row = rows[0]
    if row["round"] == "H0":
        return "H0  no skill"
    skill = row["skill_id"].replace("verus-", "").replace("-", " ")
    return f"{row['round']}  {PROFILE_SHORT[row['profile']]}  {skill}"


def _save(fig: mpl.figure.Figure, out_dir: Path) -> dict[str, str]:
    outputs = {}
    for suffix in ("pdf", "svg", "png"):
        path = out_dir / f"small_model_skill_heatmap.{suffix}"
        fig.savefig(path)
        outputs[suffix] = str(path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    _configure_style()
    conditions = _read(args.input)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(10.2, 5.7))
    grid = fig.add_gridspec(
        1,
        2,
        width_ratios=[4.5, 2.0],
        left=0.34,
        right=0.98,
        top=0.82,
        bottom=0.13,
        wspace=0.09,
    )
    ax = fig.add_subplot(grid[0, 0])
    agg_ax = fig.add_subplot(grid[0, 1], sharey=ax)
    n_rows = len(conditions)

    for y, condition in enumerate(conditions):
        for x, row in enumerate(condition):
            status = row["status"]
            f3 = row["f3"] == "true"
            tokens = _float(row["total_tokens"])
            requests = row["request_count"]
            if status == "SOLVED" and f3:
                face, color, hatch = "#7DAA92", "#10251A", None
                text = f"PASS\n{tokens / 1000:.1f}k · {requests} req"
            elif status == "UNSOLVED" and f3:
                face, color, hatch = "#E4B2A9", "#58221E", None
                text = f"FAIL\n{tokens / 1000:.1f}k · {requests} req"
            else:
                face, color, hatch = "#D4D2CC", "#555555", "xx"
                text = "RUNNER\nERROR"
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
                color=color,
                fontsize=7.1,
                linespacing=1.15,
            )

    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(n_rows - 0.5, -0.5)
    ax.set_xticks(
        range(4),
        [TASK_SHORT[row["task_id"]] for row in conditions[0]],
    )
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=7)
    ax.set_yticks(range(n_rows), [_label(rows) for rows in conditions])
    ax.tick_params(axis="y", length=0, pad=5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    values = []
    for y, condition in enumerate(conditions):
        row = condition[0]
        valid = row["matrix_valid"] == "true"
        delta = _float(row["aggregate_delta_pct"])
        solved = int(row["solve_count"])
        total = _float(row["aggregate_total_tokens"])
        if valid and delta is not None and total is not None:
            values.append(delta)
            color = "#4C78A8" if delta <= 0 else "#C9644A"
            if abs(delta) < 0.05:
                color = "#8B8B86"
            agg_ax.barh(y, delta, height=0.56, color=color, zorder=2)
            x_text = delta + (1.4 if delta >= 0 else -1.4)
            agg_ax.text(
                x_text,
                y,
                f"{total / 1000:.1f}k  {solved}/4",
                va="center",
                ha="left" if delta >= 0 else "right",
                fontsize=7.2,
            )
        else:
            agg_ax.text(
                2,
                y,
                f"× incomplete  {solved}/4",
                va="center",
                fontsize=7.2,
                color="#6F1D1B",
            )

    agg_ax.axvline(0, color="#303030", linewidth=0.8, zorder=1)
    agg_ax.set_xlim(-5, max(values) + 24)
    agg_ax.set_xlabel(
        "Total provider-token Δ vs H0 (%)\nsolve count shown at right",
        labelpad=8,
    )
    agg_ax.xaxis.set_label_position("top")
    agg_ax.xaxis.tick_top()
    agg_ax.tick_params(axis="y", left=False, labelleft=False)
    agg_ax.grid(axis="x", color="#D8D6D0", linewidth=0.5, zorder=0)
    agg_ax.spines["left"].set_visible(False)
    agg_ax.spines["bottom"].set_visible(False)
    agg_ax.spines["top"].set_visible(False)

    for boundary in (0.5, 3.5, 6.5):
        ax.axhline(boundary, color="#4A4A4A", linewidth=0.75, clip_on=False)
        agg_ax.axhline(
            boundary, color="#4A4A4A", linewidth=0.75, clip_on=False
        )

    fig.suptitle(
        "Small-model evolution: complete conditions stay at 2/4",
        x=0.58,
        y=0.985,
        fontsize=11,
    )
    fig.text(
        0.34,
        0.035,
        "Qwen3.6-27B · temperature 0.2 · at most 10 API requests · "
        "one trajectory per task-condition; hatched cells fail the F3 contract.",
        fontsize=7.4,
        color="#555555",
    )
    print(json.dumps(_save(fig, args.out_dir), indent=2))
    plt.close(fig)


if __name__ == "__main__":
    main()
