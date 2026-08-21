from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


def _configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.size": 8.5,
            "font.family": "serif",
            "font.serif": ["DejaVu Serif"],
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
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


def _save(fig: mpl.figure.Figure, out_dir: Path) -> dict[str, str]:
    outputs = {}
    for suffix in ("pdf", "svg", "png"):
        path = out_dir / f"small_model_round_summary.{suffix}"
        fig.savefig(path)
        outputs[suffix] = str(path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    _configure_style()

    with args.input.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    conditions: dict[int, dict[str, str]] = {}
    for row in rows:
        conditions.setdefault(int(row["condition_order"]), row)
    selected = []
    for round_name in ("H0", "R1", "R2", "R3"):
        candidates = [
            row
            for row in conditions.values()
            if row["round"] == round_name and row["matrix_valid"] == "true"
        ]
        selected.append(
            max(
                candidates,
                key=lambda row: (
                    int(row["solve_count"]),
                    -float(row["aggregate_total_tokens"]),
                ),
            )
        )

    labels = ["H0", "R1", "R2", "R3"]
    solved = [int(row["solve_count"]) for row in selected]
    tokens = [float(row["aggregate_total_tokens"]) / 1000 for row in selected]
    skill_labels = [
        "no skill"
        if row["round"] == "H0"
        else row["skill_id"].replace("verus-", "").replace("-", " ")
        for row in selected
    ]

    fig, (solve_ax, token_ax) = plt.subplots(
        1,
        2,
        figsize=(7.2, 3.25),
        gridspec_kw={"width_ratios": [0.8, 1.45]},
    )
    solve_ax.plot(
        labels,
        [value / 4 for value in solved],
        color="#4C78A8",
        marker="o",
        linewidth=1.8,
    )
    solve_ax.set_ylim(0, 1.03)
    solve_ax.set_ylabel("Verifier-safe solve rate")
    solve_ax.set_xlabel("Best complete condition per round")
    solve_ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    solve_ax.grid(axis="y", color="#D8D6D0", linewidth=0.55)
    for x, value in enumerate(solved):
        solve_ax.text(x, value / 4 + 0.045, f"{value}/4", ha="center")

    token_ax.plot(
        labels,
        tokens,
        color="#C9644A",
        marker="o",
        linewidth=1.8,
    )
    token_ax.axhline(tokens[0], color="#8B8B86", linestyle="--", linewidth=1)
    token_ax.set_ylabel("Total provider tokens (thousands)")
    token_ax.set_xlabel("Ties on solve rate broken by fewer tokens")
    token_ax.grid(axis="y", color="#D8D6D0", linewidth=0.55)
    for x, (value, skill) in enumerate(zip(tokens, skill_labels)):
        token_ax.text(
            x,
            value + 4,
            f"{value:.1f}k",
            ha="center",
            fontsize=7.5,
        )
        token_ax.text(
            x,
            min(tokens) - 15,
            skill.replace(" ", "\n", 1),
            ha="center",
            va="top",
            fontsize=6.8,
            color="#555555",
        )
    token_ax.set_ylim(min(tokens) - 24, max(tokens) + 26)

    fig.suptitle(
        "Small-model evolution remains flat in solve rate",
        fontsize=11,
    )
    fig.text(
        0.5,
        0.005,
        "Single-run pilot: selected skills retain 2/4 solves and exceed H0 token use.",
        ha="center",
        fontsize=7.4,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "small_model_round_summary_selection.json").write_text(
        json.dumps(
            {
                "rounds": labels,
                "selected_skill_ids": skill_labels,
                "solve_count": solved,
                "total_provider_tokens": [value * 1000 for value in tokens],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(_save(fig, args.out_dir), indent=2))
    plt.close(fig)


if __name__ == "__main__":
    main()
