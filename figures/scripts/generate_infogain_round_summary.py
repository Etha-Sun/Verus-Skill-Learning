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
            "legend.fontsize": 8,
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


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _save(fig: mpl.figure.Figure, out_dir: Path) -> dict[str, str]:
    outputs = {}
    for suffix in ("pdf", "svg", "png"):
        path = out_dir / f"infogain_round_summary.{suffix}"
        fig.savefig(path)
        outputs[suffix] = str(path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    _configure_style()

    aggregates = _read(args.data_dir / "infogain_skill_aggregate.csv")
    status = {
        row["round"]: row
        for row in _read(args.data_dir / "infogain_round_status.csv")
    }
    complete = [
        row for row in aggregates if row["score_status"] == "complete"
    ]
    by_round: dict[str, list[dict[str, str]]] = {}
    for row in complete:
        by_round.setdefault(row["round"], []).append(row)

    best_rows = {
        round_name: max(
            rows, key=lambda row: float(row["mean_post_bits_per_target_token"])
        )
        for round_name, rows in by_round.items()
    }
    best = [
        0.0,
        float(best_rows["R1"]["mean_post_bits_per_target_token"]),
        float(best_rows["R2"]["mean_post_bits_per_target_token"]),
    ]
    mean = [
        0.0,
        sum(
            float(row["mean_post_bits_per_target_token"])
            for row in by_round["R1"]
        )
        / 3,
        sum(
            float(row["mean_post_bits_per_target_token"])
            for row in by_round["R2"]
        )
        / 3,
    ]
    x = [0, 1, 2]

    fig, ax = plt.subplots(figsize=(7.2, 3.25))
    ax.plot(
        x,
        best,
        color="#356F78",
        marker="o",
        linewidth=1.9,
        label="Best skill mean",
    )
    ax.plot(
        x,
        mean,
        color="#9A968F",
        marker="o",
        linewidth=1.4,
        label="Three-skill mean",
    )
    ax.scatter(
        [3],
        [0],
        marker="x",
        s=50,
        linewidth=1.5,
        color="#6F1D1B",
        zorder=3,
    )
    ax.text(
        3,
        0.018,
        f"pending\n{status['R3']['scored_pairs']}/"
        f"{status['R3']['expected_pairs']} partial pairs excluded",
        ha="center",
        va="bottom",
        fontsize=7.2,
        color="#6F1D1B",
    )
    for index, value in enumerate(best):
        ax.text(index, value + 0.012, f"{value:.3f}", ha="center", fontsize=7.5)
    ax.axhline(0, color="#303030", linewidth=0.8)
    ax.set_xlim(-0.2, 3.2)
    ax.set_ylim(-0.025, 0.265)
    ax.set_xticks(range(4), ["H0", "R1", "R2", "R3"])
    ax.set_ylabel("Mean post InfoGain (bits / target token)")
    ax.set_xlabel("Evolution round")
    ax.grid(axis="y", color="#D8D6D0", linewidth=0.55)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title(
        "Completed rounds do not improve monotonically",
        fontsize=11,
        pad=9,
    )
    fig.text(
        0.5,
        0.012,
        "H0 is the no-summary likelihood reference (InfoGain = 0). "
        "InfoGain is an offline proxy, not live solve-rate evidence.",
        ha="center",
        fontsize=7.4,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "infogain_round_summary_selection.json").write_text(
        json.dumps(
            {
                "rounds": ["H0", "R1", "R2", "R3"],
                "best_skill_ids": [
                    "no summary",
                    best_rows["R1"]["skill_id"],
                    best_rows["R2"]["skill_id"],
                    None,
                ],
                "best_mean_post_bits_per_target_token": best + [None],
                "three_skill_mean_post_bits_per_target_token": mean + [None],
                "r3_status": status["R3"],
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
