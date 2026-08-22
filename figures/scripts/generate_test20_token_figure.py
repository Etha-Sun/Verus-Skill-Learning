from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


MODEL_ORDER = (
    "GPT-5.6 Sol",
    "DeepSeek V4 Pro",
    "GLM-5.3",
    "Qwen3.8-27B BF16",
)
CONDITION_ORDER = ("blank", "S1", "S2")
CONDITION_LABELS = {"blank": "No skill", "S1": "S1", "S2": "S2"}
COLORS = {
    "uncached": "#0072B2",
    "cached": "#56B4E9",
    "nonreasoning": "#009E73",
    "reasoning": "#CC79A7",
    "unreported": "#999999",
}


def _int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    if not value:
        raise ValueError(f"missing {key} for {row.get('model')}/{row.get('condition')}")
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"negative {key}")
    return parsed


def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        raw_rows = list(csv.DictReader(handle))
    if len(raw_rows) != len(MODEL_ORDER) * len(CONDITION_ORDER):
        raise ValueError("token figure requires 12 model/condition rows")
    by_key = {(row["model"], row["condition"]): row for row in raw_rows}
    if len(by_key) != len(raw_rows):
        raise ValueError("duplicate model/condition token row")
    rows: list[dict[str, Any]] = []
    for model in MODEL_ORDER:
        for condition in CONDITION_ORDER:
            raw = by_key.get((model, condition))
            if raw is None:
                raise ValueError(f"missing {model}/{condition} token row")
            if _int(raw, "n") != 20:
                raise ValueError("every plotted condition must use n=20")
            cached = _int(raw, "cached_input_tokens")
            uncached = _int(raw, "uncached_input_tokens")
            total_input = _int(raw, "input_tokens")
            output = _int(raw, "output_tokens")
            if cached + uncached != total_input:
                raise ValueError("cached + uncached input differs from total input")
            reasoning_available = raw["reasoning_breakdown_available"] == "True"
            reasoning = (
                _int(raw, "reasoning_output_tokens") if reasoning_available else None
            )
            if reasoning is not None and reasoning > output:
                raise ValueError("reasoning output exceeds total output")
            rows.append(
                {
                    "model": model,
                    "condition": condition,
                    "cached": cached,
                    "uncached": uncached,
                    "input": total_input,
                    "output": output,
                    "reasoning": reasoning,
                }
            )
    return rows


def _style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
        }
    )


def generate_figure(rows: list[dict[str, Any]], output_stem: Path) -> None:
    _style()
    x = np.arange(len(rows), dtype=float)
    width = 0.74
    fig, (input_ax, output_ax) = plt.subplots(2, 1, figsize=(9.2, 5.8), sharex=True)

    uncached_m = np.array([row["uncached"] for row in rows], dtype=float) / 1e6
    cached_m = np.array([row["cached"] for row in rows], dtype=float) / 1e6
    input_ax.bar(
        x,
        uncached_m,
        width,
        color=COLORS["uncached"],
        label="Uncached input",
    )
    input_ax.bar(
        x,
        cached_m,
        width,
        bottom=uncached_m,
        color=COLORS["cached"],
        label="Cached input",
    )
    input_ax.set_ylabel("Input tokens (million)")
    input_ax.set_ylim(0, float(np.max(uncached_m + cached_m)) * 1.25)
    input_ax.text(0.0, 1.02, "(a) Input", transform=input_ax.transAxes, fontweight="bold")
    input_ax.legend(frameon=False, ncol=2, loc="upper right")

    output_k = np.array([row["output"] for row in rows], dtype=float) / 1e3
    reasoning_k = np.array(
        [float(row["reasoning"] or 0) for row in rows], dtype=float
    ) / 1e3
    nonreasoning_k = output_k - reasoning_k
    available = np.array([row["reasoning"] is not None for row in rows])
    output_ax.bar(
        x[available],
        nonreasoning_k[available],
        width,
        color=COLORS["nonreasoning"],
        label="Other output",
    )
    output_ax.bar(
        x[available],
        reasoning_k[available],
        width,
        bottom=nonreasoning_k[available],
        color=COLORS["reasoning"],
        label="Reasoning output (subset)",
    )
    output_ax.bar(
        x[~available],
        output_k[~available],
        width,
        color=COLORS["unreported"],
        hatch="///",
        edgecolor="white",
        label="Total output; reasoning unreported",
    )
    output_ax.set_ylabel("Output tokens (thousand)")
    output_ax.set_ylim(0, float(np.max(output_k)) * 1.28)
    output_ax.text(
        0.0, 1.02, "(b) Output", transform=output_ax.transAxes, fontweight="bold"
    )
    output_ax.legend(frameon=False, ncol=3, loc="upper right")
    output_ax.set_xticks(
        x, [CONDITION_LABELS[row["condition"]] for row in rows], rotation=35, ha="right"
    )

    for axis in (input_ax, output_ax):
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.6, alpha=0.7)
        axis.set_axisbelow(True)
        for boundary in (2.5, 5.5, 8.5):
            axis.axvline(boundary, color="#BDBDBD", linewidth=0.7)
    for index, model in enumerate(MODEL_ORDER):
        center = index * len(CONDITION_ORDER) + 1
        output_ax.text(
            center,
            -0.43,
            model.replace(" BF16", "\nBF16"),
            ha="center",
            va="top",
            transform=output_ax.get_xaxis_transform(),
            fontsize=8.2,
        )
    fig.text(
        0.5,
        0.005,
        "Totals over all 20 held-out tasks per condition. Cached tokens remain part of total input; "
        "reasoning is a subset of output, not an additive category.\n"
        "Bridge-provider bars include archived attempts; GPT direct bars use retained Responses usage.",
        ha="center",
        va="bottom",
        fontsize=8,
    )
    fig.subplots_adjust(left=0.085, right=0.99, top=0.98, bottom=0.25, hspace=0.28)
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".pdf"))
    fig.savefig(output_stem.with_suffix(".png"))
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-stem", type=Path, required=True)
    args = parser.parse_args()
    rows = load_rows(args.input.resolve())
    generate_figure(rows, args.output_stem.resolve())
    print(
        json.dumps(
            {
                "input": str(args.input),
                "rows": len(rows),
                "pdf": str(args.output_stem.with_suffix(".pdf")),
                "png": str(args.output_stem.with_suffix(".png")),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
