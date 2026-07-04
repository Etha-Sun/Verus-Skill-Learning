from __future__ import annotations

import argparse
import json
from pathlib import Path

from .data import load_traces, write_data_manifest
from .mining import mine_candidate_rules, write_rules, write_skeleton_cache
from .report import write_report
from .scoring import dataset_summary, policy_ablation, score_rules, write_csv


def run(args: argparse.Namespace) -> None:
    data_root = Path(args.data_root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    traces = load_traces(data_root)
    dataset = dataset_summary(traces)
    write_data_manifest(data_root, out_dir / "data_manifest.json", traces)

    rules = mine_candidate_rules(traces, thresholds=tuple(args.thresholds))
    write_rules(out_dir / "candidate_rules.jsonl", rules)
    write_skeleton_cache(out_dir / "skeleton_cache.jsonl", traces)

    scores = score_rules(traces, rules)
    ablation = policy_ablation(traces, rules, scores)
    write_csv(out_dir / "rule_scores.csv", scores)
    write_csv(out_dir / "policy_ablation.csv", ablation)

    summary = {
        "dataset": dataset,
        "rule_count": len(rules),
        "top_rule": scores[0] if scores else None,
        "ablation": ablation,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    write_report(out_dir / "report.md", dataset, len(rules), scores, ablation)


def main() -> None:
    parser = argparse.ArgumentParser(prog="verus-self-evolve")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_parser = sub.add_parser("run", help="run offline rule mining and replay evaluation")
    run_parser.add_argument("--data-root", required=True, help="path containing all_batch_results-cyy-*")
    run_parser.add_argument("--out", required=True, help="output run directory")
    run_parser.add_argument("--thresholds", nargs="+", type=int, default=[4, 6, 8])
    run_parser.set_defaults(func=run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
