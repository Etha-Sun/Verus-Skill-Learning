from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


STAGES = [
    ("seed", "R6 seed"),
    ("round-1", "R1"),
    ("round-2", "R2"),
    ("round-3", "R3"),
]
PROFILES = ["aggressive", "conservative", "structural"]
PROFILE_LABELS = {
    "aggressive": "Aggressive",
    "conservative": "Conservative",
    "structural": "Structural",
}
PROFILE_COLORS = {
    "aggressive": "#3E6488",
    "conservative": "#8E9A7D",
    "structural": "#C08A72",
}
STYLE_PATH = Path(__file__).with_name("deepscientist-academic-fixed.mplstyle")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _condition(summary: dict[str, Any], profile: str | None) -> dict[str, Any]:
    matches = [
        condition
        for condition in summary["conditions"]
        if condition["skill_profile"] == profile
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one condition for profile {profile}, found {len(matches)}")
    return matches[0]


def _attempt_tokens(condition: dict[str, Any]) -> list[int]:
    values = []
    for attempt in condition["attempts"]:
        ledger = attempt.get("ledger")
        if ledger is not None and ledger.get("primary_uncached_tokens") is not None:
            values.append(int(ledger["primary_uncached_tokens"]))
    return values


def _load(run_root: Path) -> dict[str, Any]:
    summaries = {
        stage: _read_json(run_root / stage / "metric_summary.json")
        for stage, _ in STAGES
    }
    h0_summary = _read_json(run_root / "h0" / "metric_summary.json")
    final_summary = _read_json(
        run_root / "final-confirmation" / "metric_summary.json"
    )
    report = _read_json(run_root / "matched_final_report.json")

    h0 = _condition(h0_summary, None)
    final = final_summary["conditions"][0]
    if h0["attempt_count"] != 3 or h0["success_count"] != 3:
        raise ValueError("expected three successful H0 attempts")
    if final["attempt_count"] != 3 or final["success_count"] != 3:
        raise ValueError("expected three successful final-confirmation attempts")
    if report["conclusion"] != "inconclusive_within_h0_range":
        raise ValueError(f"unexpected final conclusion: {report['conclusion']}")

    return {
        "summaries": summaries,
        "h0": h0,
        "final": final,
        "report": report,
    }


def _write_plot_data(data: dict[str, Any], path: Path) -> None:
    fields = [
        "evidence_scope",
        "stage",
        "profile",
        "skill_id",
        "attempt_id",
        "primary_uncached_tokens",
        "etts",
        "relative_delta_vs_h0",
        "success",
        "claim_admissible",
        "invalid",
        "timeout",
    ]
    rows: list[dict[str, Any]] = []
    for stage, stage_label in STAGES:
        summary = data["summaries"][stage]
        for profile in PROFILES:
            condition = _condition(summary, profile)
            attempt = condition["attempts"][0]
            ledger = attempt.get("ledger")
            rows.append(
                {
                    "evidence_scope": "single_run_screen",
                    "stage": stage_label,
                    "profile": profile,
                    "skill_id": condition["skill_id"],
                    "attempt_id": attempt["job_id"],
                    "primary_uncached_tokens": (
                        ""
                        if ledger is None
                        else ledger.get("primary_uncached_tokens", "")
                    ),
                    "etts": (
                        ""
                        if condition["expected_primary_uncached_tokens_to_success"]
                        is None
                        else condition[
                            "expected_primary_uncached_tokens_to_success"
                        ]
                    ),
                    "relative_delta_vs_h0": (
                        ""
                        if condition["relative_delta_vs_h0"] is None
                        else condition["relative_delta_vs_h0"]
                    ),
                    "success": attempt["status"] == "SOLVED",
                    "claim_admissible": condition["claim_admissible"],
                    "invalid": attempt["invalid"],
                    "timeout": attempt["timed_out"],
                }
            )

    for stage_label, condition in (("H0", data["h0"]), ("Final", data["final"])):
        for attempt in condition["attempts"]:
            ledger = attempt["ledger"]
            rows.append(
                {
                    "evidence_scope": "matched_repeated_confirmation",
                    "stage": stage_label,
                    "profile": condition["skill_profile"] or "baseline",
                    "skill_id": condition["skill_id"] or "no-skill",
                    "attempt_id": attempt["job_id"],
                    "primary_uncached_tokens": ledger["primary_uncached_tokens"],
                    "etts": condition[
                        "expected_primary_uncached_tokens_to_success"
                    ],
                    "relative_delta_vs_h0": (
                        ""
                        if stage_label == "H0"
                        else data["report"]["relative_delta_vs_h0"]
                    ),
                    "success": attempt["status"] == "SOLVED",
                    "claim_admissible": condition["claim_admissible"],
                    "invalid": attempt["invalid"],
                    "timeout": attempt["timed_out"],
                }
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _configure_style() -> None:
    plt.style.use(STYLE_PATH)
    mpl.rcParams.update(
        {
            "axes.edgecolor": "#D8D1C7",
            "axes.labelcolor": "#4B5563",
            "figure.dpi": 160,
            "grid.color": "#E7E5E4",
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "hatch.color": "white",
            "hatch.linewidth": 1.2,
            "xtick.color": "#6B7280",
            "ytick.color": "#6B7280",
        }
    )


def _draw_screen(ax: mpl.axes.Axes, data: dict[str, Any]) -> None:
    h0 = data["h0"]
    h0_dist = h0["primary_uncached_token_distribution"]
    h0_mean = float(h0["expected_primary_uncached_tokens_to_success"]) / 1000
    stage_x = np.arange(len(STAGES), dtype=float)
    total_width = 0.72
    bar_width = total_width / len(PROFILES)

    ax.axhspan(
        h0_dist["min"] / 1000,
        h0_dist["max"] / 1000,
        color="#D7D4CE",
        alpha=0.38,
        linewidth=0,
        zorder=0,
        label="H0 run range",
    )
    ax.axhline(
        h0_mean,
        color="#545454",
        linewidth=1.15,
        linestyle=(0, (4, 3)),
        zorder=1,
    )

    for index, profile in enumerate(PROFILES):
        offset = (index - 1) * bar_width
        for stage_index, (stage, _) in enumerate(STAGES):
            condition = _condition(data["summaries"][stage], profile)
            value = condition["expected_primary_uncached_tokens_to_success"]
            x = stage_x[stage_index] + offset
            if value is None:
                ax.scatter(
                    [x],
                    [123.5],
                    marker="X",
                    s=52,
                    color="#696969",
                    zorder=4,
                    clip_on=False,
                )
                ax.text(
                    x,
                    119.8,
                    "invalid*",
                    ha="center",
                    va="top",
                    fontsize=7.1,
                    color="#5B5B5B",
                )
                continue

            value_k = float(value) / 1000
            selected = condition["skill_id"] == "local-proof-surface-cap"
            ax.bar(
                x,
                value_k,
                width=bar_width,
                color=PROFILE_COLORS[profile],
                hatch="//" if selected else "",
                edgecolor="white",
                linewidth=0.7,
                zorder=2,
            )
            delta_pct = 100 * float(condition["relative_delta_vs_h0"])
            ax.text(
                x,
                value_k + 1.5,
                f"{value_k:.1f}k\n{delta_pct:+.1f}%",
                ha="center",
                va="bottom",
                fontsize=6.8,
                fontweight="bold" if selected else "normal",
                color="#243746" if selected else "#3F3F3F",
                linespacing=1.0,
            )

    ax.set_title("(a) Single-run skill screening (n=1 per skill)", pad=7)
    ax.set_ylabel("Primary uncached tokens (k; lower is better)")
    ax.set_xticks(stage_x, [label for _, label in STAGES])
    ax.set_ylim(0, 128)
    ax.set_xlim(-0.55, 3.45)
    ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(20))
    ax.grid(axis="x", visible=False)

    handles = [
        Patch(facecolor=PROFILE_COLORS[p], edgecolor="none", label=PROFILE_LABELS[p])
        for p in PROFILES
    ]
    handles.extend(
        [
            Patch(
                facecolor="#D7D4CE",
                edgecolor="none",
                alpha=0.6,
                label="H0 run range",
            ),
            Line2D(
                [0],
                [0],
                color="#545454",
                linewidth=1.15,
                linestyle=(0, (4, 3)),
                label=f"H0 mean {h0_mean:.1f}k",
            ),
            Patch(
                facecolor=PROFILE_COLORS["aggressive"],
                hatch="//",
                edgecolor="white",
                label="Selected screen",
            ),
        ]
    )
    ax.legend(
        handles=handles,
        ncol=6,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.13),
        fontsize=6.5,
        columnspacing=0.65,
        handlelength=1.25,
    )


def _draw_confirmation(ax: mpl.axes.Axes, data: dict[str, Any]) -> None:
    h0 = data["h0"]
    final = data["final"]
    report = data["report"]
    h0_values = np.array(_attempt_tokens(h0), dtype=float) / 1000
    final_values = np.array(_attempt_tokens(final), dtype=float) / 1000
    means = np.array(
        [
            h0["expected_primary_uncached_tokens_to_success"],
            final["expected_primary_uncached_tokens_to_success"],
        ],
        dtype=float,
    ) / 1000
    colors = ["#A8B6C3", "#3E6488"]
    x = np.arange(2, dtype=float)

    ax.bar(
        x,
        means,
        width=0.56,
        color=colors,
        edgecolor="white",
        linewidth=0.8,
        zorder=2,
    )
    jitters = np.array([-0.10, 0.0, 0.10])
    for index, values in enumerate((h0_values, final_values)):
        ax.vlines(
            x[index],
            values.min(),
            values.max(),
            color="#343434",
            linewidth=1.0,
            zorder=3,
        )
        ax.scatter(
            x[index] + jitters,
            values,
            s=27,
            facecolor="white",
            edgecolor="#2F2F2F",
            linewidth=0.8,
            zorder=4,
        )
        ax.text(
            x[index],
            values.max() + 2.2,
            f"ETtS {means[index]:.1f}k",
            ha="center",
            va="bottom",
            fontsize=8.2,
            fontweight="bold" if index == 1 else "normal",
            color="#243746" if index == 1 else "#454545",
        )

    delta_pct = 100 * float(report["relative_delta_vs_h0"])
    delta_k = float(report["delta_primary_uncached_tokens"]) / 1000
    h0_range_k = float(report["h0_primary_uncached_token_range"]) / 1000
    ax.annotate(
        "",
        xy=(0.72, means[1] + 0.4),
        xytext=(0.28, means[0] - 0.4),
        arrowprops={"arrowstyle": "->", "color": "#A35D36", "lw": 1.2},
        zorder=5,
    )
    ax.text(
        0.52,
        (means[0] + means[1]) / 2 + 2.6,
        f"{delta_pct:.2f}%",
        ha="center",
        va="center",
        fontsize=9,
        color="#A35D36",
        fontweight="bold",
    )
    ax.text(
        0.5,
        47,
        f"|mean Δ| = {abs(delta_k):.1f}k < H0 range = {h0_range_k:.1f}k\n"
        "Conclusion: inconclusive within H0 variation",
        ha="center",
        va="center",
        fontsize=8.2,
        color="#493E38",
        bbox={
            "boxstyle": "round,pad=0.38",
            "facecolor": "#F2E9DF",
            "edgecolor": "#D2B9A5",
            "linewidth": 0.8,
        },
    )

    ax.set_title("(b) Matched confirmation (3/3 verifier-safe each)", pad=7)
    ax.set_ylabel("Primary uncached tokens (k)")
    ax.set_xticks(x, ["Fresh H0", "Final skill\nlocal-proof-surface-cap"])
    ax.set_ylim(0, 106)
    ax.set_xlim(-0.52, 1.52)
    ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(20))
    ax.grid(axis="x", visible=False)


def _save_figure(fig: mpl.figure.Figure, directories: list[Path], stem: str) -> None:
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        for suffix in ("pdf", "svg", "png"):
            fig.savefig(directory / f"{stem}.{suffix}", dpi=300, facecolor="white")


def _write_manifest(
    run_root: Path,
    output_dir: Path,
    repo_figure_dir: Path,
    data_csv: Path,
    script_path: Path,
    review_note: str,
) -> None:
    stem = "single_problem_token_cost_overfit"
    source_files = [
        run_root / "h0" / "metric_summary.json",
        run_root / "seed" / "metric_summary.json",
        run_root / "round-1" / "metric_summary.json",
        run_root / "round-2" / "metric_summary.json",
        run_root / "round-3" / "metric_summary.json",
        run_root / "final-confirmation" / "metric_summary.json",
        run_root / "matched_final_report.json",
    ]
    manifest = {
        "schema_version": "1",
        "surface_class": "paper_main",
        "source_data": str(data_csv),
        "source_summaries": [
            {"path": str(path), "sha256": _sha256(path)} for path in source_files
        ],
        "generator": str(script_path),
        "exports": [
            str(directory / f"{stem}.{suffix}")
            for directory in (output_dir, repo_figure_dir)
            for suffix in ("pdf", "svg", "png")
        ],
        "main_comparison": (
            "Single-run skill screening across the R6 seed and R1-R3 evolution "
            "rounds, followed by matched three-run H0 versus final-skill confirmation."
        ),
        "correctness_notes": [
            "The timed-out seed with missing terminal usage is marked invalid and has no token-height encoding.",
            "Every screening skill has n=1 and is labeled as single-run evidence.",
            "H0 and final confirmation each show all three verifier-safe run values.",
            "The final favorable mean delta is explicitly labeled inconclusive because it is smaller than the H0 range.",
        ],
        "review_note": review_note,
    }
    manifest_path = output_dir / "figure_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--repo-figure-dir", type=Path, required=True)
    parser.add_argument(
        "--review-note",
        default="First durable render; visual review pending.",
    )
    args = parser.parse_args()

    output_dir = args.run_root / "visualization"
    output_dir.mkdir(parents=True, exist_ok=True)
    data = _load(args.run_root)
    data_csv = output_dir / "single_problem_token_cost_overfit_plot_data.csv"
    _write_plot_data(data, data_csv)

    _configure_style()
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(10.6, 4.15),
        gridspec_kw={"width_ratios": [1.75, 1]},
    )
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.23, top=0.84, wspace=0.25)
    _draw_screen(axes[0], data)
    _draw_confirmation(axes[1], data)
    fig.suptitle(
        "IronKV single-problem token-cost evolution",
        x=0.075,
        y=0.98,
        ha="left",
        fontsize=12,
        fontweight="bold",
        color="#243746",
    )
    stem = "single_problem_token_cost_overfit"
    _save_figure(fig, [output_dir, args.repo_figure_dir], stem)
    plt.close(fig)

    _write_manifest(
        args.run_root,
        output_dir,
        args.repo_figure_dir,
        data_csv,
        Path(__file__).resolve(),
        args.review_note,
    )
    print(output_dir / f"{stem}.png")
    print(args.repo_figure_dir / f"{stem}.png")


if __name__ == "__main__":
    main()
