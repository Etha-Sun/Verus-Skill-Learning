from __future__ import annotations

import json
from pathlib import Path


def write_report(
    path: Path,
    dataset: dict[str, object],
    rule_count: int,
    rule_scores: list[dict[str, object]],
    ablation_rows: list[dict[str, object]],
) -> None:
    top_rules = rule_scores[:10]
    lines = [
        "# Experiment Report",
        "",
        "## Dataset",
        "",
        f"- traces: {dataset['traces']}",
        f"- verified: {dataset['verified']}",
        f"- nonverified: {dataset['nonverified']}",
        f"- effective_total_tokens: {dataset['effective_total_tokens']}",
        "",
        "Project counts:",
        "",
        "```json",
        json.dumps(dataset["projects"], indent=2),
        "```",
        "",
        "## Candidate Rules",
        "",
        f"- mined rules: {rule_count}",
        "",
        "## Policy Ablation",
        "",
        "The ablation table uses trace-level union over the selected top rules, so",
        "a trace covered by multiple rules is counted once.",
        "",
        "| policy_level | rules | selected_top_k | union_covered_failed | union_saved_failed_tokens | false_stop_rate | peer_diff_rate | best_rule |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in ablation_rows:
        lines.append(
            "| {policy_level} | {rules} | {selected_top_k} | {union_covered_failed_traces} | "
            "{union_saved_failed_tokens} | {union_verified_false_stop_rate} | "
            "{union_peer_action_diff_rate} | {best_rule} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Top Rules",
            "",
            "| rule_id | level | covered_failed | saved_failed_tokens | false_stop_rate | peer_action_diff_rate | prefer_actions |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in top_rules:
        lines.append(
            "| {rule_id} | {level} | {covered_failed_traces} | {saved_failed_tokens} | "
            "{verified_false_stop_rate} | {peer_action_diff_rate} | {prefer_actions} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Claim Update",
            "",
            "This run supports the scaffold-level claim that Verus repair traces contain",
            "enough structure to mine decision rules with measurable failed-token coverage",
            "and peer-success reroute support. These are offline replay metrics, not yet",
            "a live repair success improvement.",
            "",
            "## Next Action",
            "",
            "Run a small live rerun on the highest-token traces matched by the best",
            "project-aware or motif-aware rules, comparing baseline action selection",
            "against rule-guided reroute.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
