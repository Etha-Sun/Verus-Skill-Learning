#!/usr/bin/env python3
"""Offline Verusage trace experiments.

This script intentionally reads the original traces/results in place and writes
all derived artifacts under the selected output directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

from verus_self_evolve.data_layout import validate_output_path

ATTEMPT_RE = re.compile(r"Repair attempt\s+(\d+)/(\d+)")
TARGET_RE = re.compile(r"Target error:\s*(?:VerusErrorType\.)?([A-Za-z0-9_]+)")
ACTION_RE = re.compile(r"['\"]primary_action['\"]:\s*['\"]([^'\"]+)['\"]")
INPUT_RE = re.compile(r"Input tokens:\s*(\d+)")
OUTPUT_RE = re.compile(r"Output tokens:\s*(\d+)")
LEMMA_RE = re.compile(r"Lemmas found:\s*\d+\s*-\s*\[(.*?)\]")
TIME_SUFFIX_RE = re.compile(r"-\d{8}-\d{6}$")


@dataclass
class ResultRow:
    model: str
    batch: str
    file: str
    status: str
    time_seconds: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    result_csv: str


@dataclass
class Attempt:
    index: int
    target_error: str
    action: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    accepted: bool


@dataclass
class TraceRow:
    model: str
    batch: str
    file: str
    project: str
    status: str
    csv_input_tokens: int
    csv_output_tokens: int
    csv_total_tokens: int
    time_seconds: float
    attempts: list[Attempt]
    lemmas: list[str]
    log_path: str


def model_from_path(path: Path) -> str:
    for part in path.parts:
        if part.startswith("all_batch_results-cyy-"):
            return part.removeprefix("all_batch_results-cyy-")
    return "unknown"


def batch_from_path(path: Path) -> str:
    for part in path.parts:
        if part.startswith("results-batch_"):
            return part
    return "unknown"


def file_from_log(path: Path) -> str:
    name = path.parent.name
    if name.startswith("o-"):
        name = name[2:]
    name = TIME_SUFFIX_RE.sub("", name)
    return f"{name}.rs"


def file_from_odir(path: Path) -> str:
    name = path.name
    if name.startswith("o-"):
        name = name[2:]
    name = TIME_SUFFIX_RE.sub("", name)
    return f"{name}.rs"


def project_from_file(file_name: str) -> str:
    return file_name.split("__", 1)[0]


def to_int(value: str) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def to_float(value: str) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def read_results(root: Path) -> dict[tuple[str, str, str], ResultRow]:
    rows: dict[tuple[str, str, str], ResultRow] = {}
    for csv_path in root.glob("all_batch_results-cyy-*/results-batch_*/results.csv"):
        model = model_from_path(csv_path)
        batch = batch_from_path(csv_path)
        with csv_path.open(newline="", errors="replace") as f:
            for row in csv.DictReader(f):
                file_name = row.get("file", "")
                if not file_name:
                    continue
                rows[(model, batch, file_name)] = ResultRow(
                    model=model,
                    batch=batch,
                    file=file_name,
                    status=row.get("status", ""),
                    time_seconds=to_float(row.get("time_seconds", "")),
                    input_tokens=to_int(row.get("input_tokens", "")),
                    output_tokens=to_int(row.get("output_tokens", "")),
                    total_tokens=to_int(row.get("total_tokens", "")),
                    result_csv=str(csv_path),
                )
    return rows


def parse_lemmas(text: str) -> list[str]:
    match = LEMMA_RE.search(text)
    if not match:
        return []
    raw = match.group(1)
    lemmas = []
    for item in raw.split(","):
        item = item.strip().strip("'\"")
        if item:
            lemmas.append(item)
    return lemmas


def parse_attempts(text: str) -> list[Attempt]:
    matches = list(ATTEMPT_RE.finditer(text))
    attempts: list[Attempt] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end]
        target = ""
        target_match = TARGET_RE.search(chunk)
        if target_match:
            target = target_match.group(1)
        action = ""
        action_match = ACTION_RE.search(chunk)
        if action_match:
            action = action_match.group(1)
        input_tokens = sum(int(x) for x in INPUT_RE.findall(chunk))
        output_tokens = sum(int(x) for x in OUTPUT_RE.findall(chunk))
        accepted = (
            "Action accepted" in chunk
            or "Candidate 1 accepted" in chunk
            or "is the new best candidate" in chunk
        )
        attempts.append(
            Attempt(
                index=int(match.group(1)),
                target_error=target,
                action=action,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                accepted=accepted,
            )
        )
    return attempts


def read_traces(root: Path, results: dict[tuple[str, str, str], ResultRow]) -> list[TraceRow]:
    traces: list[TraceRow] = []
    for log_path in root.glob("all_batch_results-cyy-*/results-batch_*/o-*/verus-repair.log"):
        model = model_from_path(log_path)
        batch = batch_from_path(log_path)
        file_name = file_from_log(log_path)
        result = results.get((model, batch, file_name))
        if result is None:
            continue
        text = log_path.read_text(errors="replace")
        traces.append(
            TraceRow(
                model=model,
                batch=batch,
                file=file_name,
                project=project_from_file(file_name),
                status=result.status,
                csv_input_tokens=result.input_tokens,
                csv_output_tokens=result.output_tokens,
                csv_total_tokens=result.total_tokens,
                time_seconds=result.time_seconds,
                attempts=parse_attempts(text),
                lemmas=parse_lemmas(text),
                log_path=str(log_path),
            )
        )
    return traces


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def repetition_gate(traces: list[TraceRow], out_dir: Path) -> dict[str, object]:
    summary_rows = []
    project_rows = []
    example_rows = []
    thresholds = [2, 3, 4, 5, 6, 8]
    for threshold in thresholds:
        per_project = defaultdict(lambda: Counter())
        gated_nonverified = 0
        gated_verified = 0
        saved_nonverified = 0
        saved_verified = 0
        total_nonverified = 0
        total_verified = 0
        verified_count = 0
        nonverified_count = 0
        for trace in traces:
            if trace.status == "VERIFIED":
                verified_count += 1
                total_verified += effective_total_tokens(trace)
            else:
                nonverified_count += 1
                total_nonverified += effective_total_tokens(trace)
            seen = Counter()
            gate_at = None
            gate_pair = ("", "")
            for idx, attempt in enumerate(trace.attempts):
                pair = (attempt.target_error or "unknown_error", attempt.action or "unknown_action")
                seen[pair] += 1
                if seen[pair] >= threshold:
                    gate_at = idx
                    gate_pair = pair
                    break
            if gate_at is None:
                continue
            tail_log_tokens = sum(a.total_tokens for a in trace.attempts[gate_at:])
            if tail_log_tokens <= 0:
                tail_log_tokens = max(
                    effective_total_tokens(trace) - sum(a.total_tokens for a in trace.attempts[:gate_at]),
                    0,
                )
            row_counter = per_project[trace.project]
            row_counter["traces"] += 1
            row_counter["saved_total_tokens"] += tail_log_tokens
            if trace.status == "VERIFIED":
                gated_verified += 1
                saved_verified += tail_log_tokens
                row_counter["verified_false_stops"] += 1
            else:
                gated_nonverified += 1
                saved_nonverified += tail_log_tokens
                row_counter["nonverified_gated"] += 1
                if len(example_rows) < 100:
                    example_rows.append(
                        {
                            "threshold": threshold,
                            "model": trace.model,
                            "project": trace.project,
                            "file": trace.file,
                            "status": trace.status,
                            "gate_attempt": trace.attempts[gate_at].index,
                            "pair_error": gate_pair[0],
                            "pair_action": gate_pair[1],
                            "estimated_saved_tokens": tail_log_tokens,
                            "effective_total_tokens": effective_total_tokens(trace),
                            "log_path": trace.log_path,
                        }
                    )
        summary_rows.append(
            {
                "threshold": threshold,
                "verified_traces": verified_count,
                "nonverified_traces": nonverified_count,
                "gated_nonverified": gated_nonverified,
                "gated_nonverified_rate": round(gated_nonverified / nonverified_count, 4) if nonverified_count else 0,
                "verified_false_stops": gated_verified,
                "verified_false_stop_rate": round(gated_verified / verified_count, 4) if verified_count else 0,
                "saved_nonverified_tokens": saved_nonverified,
                "saved_verified_tokens_if_bad": saved_verified,
                "nonverified_total_tokens": total_nonverified,
                "saved_nonverified_token_rate": round(saved_nonverified / total_nonverified, 4) if total_nonverified else 0,
            }
        )
        for project, counter in sorted(per_project.items()):
            project_rows.append(
                {
                    "threshold": threshold,
                    "project": project,
                    "gated_traces": counter["traces"],
                    "nonverified_gated": counter["nonverified_gated"],
                    "verified_false_stops": counter["verified_false_stops"],
                    "saved_total_tokens": counter["saved_total_tokens"],
                }
            )
    write_csv(
        out_dir / "repetition_gate_summary.csv",
        summary_rows,
        [
            "threshold",
            "verified_traces",
            "nonverified_traces",
            "gated_nonverified",
            "gated_nonverified_rate",
            "verified_false_stops",
            "verified_false_stop_rate",
            "saved_nonverified_tokens",
            "saved_verified_tokens_if_bad",
            "nonverified_total_tokens",
            "saved_nonverified_token_rate",
        ],
    )
    write_csv(
        out_dir / "repetition_gate_by_project.csv",
        project_rows,
        ["threshold", "project", "gated_traces", "nonverified_gated", "verified_false_stops", "saved_total_tokens"],
    )
    write_csv(
        out_dir / "top_loop_examples.csv",
        sorted(example_rows, key=lambda r: int(r["estimated_saved_tokens"]), reverse=True)[:50],
        [
            "threshold",
            "model",
            "project",
            "file",
            "status",
            "gate_attempt",
            "pair_error",
            "pair_action",
            "estimated_saved_tokens",
            "effective_total_tokens",
            "log_path",
        ],
    )
    return {"summary": summary_rows[:], "examples": example_rows[:5]}


def action_sequence(trace: TraceRow) -> tuple[str, ...]:
    return tuple(a.action for a in trace.attempts if a.action)


def log_total_tokens(trace: TraceRow) -> int:
    return sum(a.total_tokens for a in trace.attempts)


def effective_total_tokens(trace: TraceRow) -> int:
    return max(trace.csv_total_tokens, log_total_tokens(trace))


def tokenize_file(file_name: str) -> set[str]:
    stem = file_name.removesuffix(".rs")
    return {tok.lower() for tok in re.split(r"[^A-Za-z0-9]+", stem) if len(tok) >= 3}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def skeleton_coverage(traces: list[TraceRow], out_dir: Path) -> dict[str, object]:
    by_task_model: dict[tuple[str, str], list[TraceRow]] = defaultdict(list)
    for trace in traces:
        by_task_model[(trace.project, trace.file)].append(trace)

    coverage_rows = []
    for trace in traces:
        if trace.status == "VERIFIED":
            continue
        peer_success = [
            t for t in by_task_model[(trace.project, trace.file)] if t.model != trace.model and t.status == "VERIFIED"
        ]
        if not peer_success:
            continue
        best = min(peer_success, key=effective_total_tokens)
        coverage_rows.append(
            {
                "model": trace.model,
                "project": trace.project,
                "file": trace.file,
                "status": trace.status,
                "failed_total_tokens": effective_total_tokens(trace),
                "peer_model": best.model,
                "peer_tokens": effective_total_tokens(best),
                "peer_attempts": len(best.attempts),
                "peer_action_seq": " ".join(action_sequence(best)[:12]),
                "log_path": trace.log_path,
                "peer_log_path": best.log_path,
            }
        )

    corpus = [t for t in traces if t.status == "VERIFIED" and action_sequence(t)]
    labels = {
        (t.project, t.file): set(action_sequence(t))
        for t in corpus
    }
    eval_rows = []
    aggregate = Counter()
    for trace in traces:
        if trace.status == "VERIFIED":
            continue
        label_actions = labels.get((trace.project, trace.file))
        if not label_actions:
            continue
        query_tokens = tokenize_file(trace.file) | {x.lower() for x in trace.lemmas}
        scored = []
        for candidate in corpus:
            if candidate.file == trace.file:
                continue
            cand_tokens = tokenize_file(candidate.file) | {x.lower() for x in candidate.lemmas}
            score = jaccard(query_tokens, cand_tokens)
            if candidate.project == trace.project:
                score += 0.25
            if score <= 0:
                continue
            scored.append((score, candidate))
        scored.sort(key=lambda item: (-item[0], effective_total_tokens(item[1])))
        top = scored[:5]
        if not top:
            continue
        top_actions = [set(action_sequence(c)) for _, c in top]
        hits = {}
        for k in [1, 3, 5]:
            merged = set()
            for action_set in top_actions[:k]:
                merged.update(action_set)
            hit = bool(merged & label_actions)
            hits[f"hit_at_{k}"] = int(hit)
            aggregate[f"hit_at_{k}"] += int(hit)
        aggregate["n"] += 1
        eval_rows.append(
            {
                "model": trace.model,
                "project": trace.project,
                "file": trace.file,
                "query_status": trace.status,
                "top1_score": round(top[0][0], 4),
                "top1_file": top[0][1].file,
                "top1_model": top[0][1].model,
                "top1_actions": " ".join(action_sequence(top[0][1])[:12]),
                "label_actions": " ".join(sorted(label_actions)[:12]),
                **hits,
            }
        )

    exact_summary = []
    by_model_project = defaultdict(lambda: Counter())
    total_failed_tokens = sum(effective_total_tokens(t) for t in traces if t.status != "VERIFIED")
    for row in coverage_rows:
        key = (row["model"], row["project"])
        by_model_project[key]["covered_failures"] += 1
        by_model_project[key]["covered_failed_tokens"] += int(row["failed_total_tokens"])
    for (model, project), counter in sorted(by_model_project.items()):
        exact_summary.append(
            {
                "model": model,
                "project": project,
                "covered_failures": counter["covered_failures"],
                "covered_failed_tokens": counter["covered_failed_tokens"],
            }
        )

    retrieval_summary = []
    n = aggregate["n"]
    if n:
        retrieval_summary.append(
            {
                "eval_queries": n,
                "hit_at_1": round(aggregate["hit_at_1"] / n, 4),
                "hit_at_3": round(aggregate["hit_at_3"] / n, 4),
                "hit_at_5": round(aggregate["hit_at_5"] / n, 4),
            }
        )
    write_csv(
        out_dir / "cross_model_skeleton_coverage.csv",
        sorted(coverage_rows, key=lambda r: int(r["failed_total_tokens"]), reverse=True),
        [
            "model",
            "project",
            "file",
            "status",
            "failed_total_tokens",
            "peer_model",
            "peer_tokens",
            "peer_attempts",
            "peer_action_seq",
            "log_path",
            "peer_log_path",
        ],
    )
    write_csv(
        out_dir / "cross_model_skeleton_coverage_by_project.csv",
        exact_summary,
        ["model", "project", "covered_failures", "covered_failed_tokens"],
    )
    write_csv(
        out_dir / "retrieval_eval.csv",
        eval_rows,
        [
            "model",
            "project",
            "file",
            "query_status",
            "top1_score",
            "top1_file",
            "top1_model",
            "top1_actions",
            "label_actions",
            "hit_at_1",
            "hit_at_3",
            "hit_at_5",
        ],
    )
    write_csv(
        out_dir / "retrieval_eval_summary.csv",
        retrieval_summary,
        ["eval_queries", "hit_at_1", "hit_at_3", "hit_at_5"],
    )
    return {
        "exact_covered_failures": len(coverage_rows),
        "exact_covered_failed_tokens": sum(int(r["failed_total_tokens"]) for r in coverage_rows),
        "total_failed_tokens": total_failed_tokens,
        "retrieval_summary": retrieval_summary,
    }


def percentile(values: list[int], q: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    idx = min(len(values) - 1, max(0, math.ceil(q * len(values)) - 1))
    return values[idx]


def prompt_cost_audit(root: Path, traces: list[TraceRow], out_dir: Path) -> dict[str, object]:
    task_index = {(t.model, t.batch, t.file): t for t in traces}
    rows = []
    grouped: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for prompt_path in root.glob("all_batch_results-cyy-*/results-batch_*/o-*/llm-prompts/*-input.txt"):
        model = model_from_path(prompt_path)
        batch = batch_from_path(prompt_path)
        file_name = file_from_odir(prompt_path.parent.parent)
        trace = task_index.get((model, batch, file_name))
        if trace is None:
            continue
        size = prompt_path.stat().st_size
        grouped[(model, trace.project, trace.status)].append(size)
    for (model, project, status), sizes in sorted(grouped.items()):
        rows.append(
            {
                "model": model,
                "project": project,
                "status": status,
                "prompt_count": len(sizes),
                "mean_bytes": round(mean(sizes), 1),
                "median_bytes": int(median(sizes)),
                "p90_bytes": percentile(sizes, 0.90),
                "p99_bytes": percentile(sizes, 0.99),
                "over_100k": sum(1 for x in sizes if x > 100_000),
                "over_200k": sum(1 for x in sizes if x > 200_000),
            }
        )
    write_csv(
        out_dir / "prompt_cost_summary.csv",
        rows,
        [
            "model",
            "project",
            "status",
            "prompt_count",
            "mean_bytes",
            "median_bytes",
            "p90_bytes",
            "p99_bytes",
            "over_100k",
            "over_200k",
        ],
    )
    return {"groups": len(rows), "prompt_files": sum(len(v) for v in grouped.values())}


def gate_index(trace: TraceRow, threshold: int) -> tuple[int | None, tuple[str, str]]:
    seen = Counter()
    for idx, attempt in enumerate(trace.attempts):
        pair = (attempt.target_error or "unknown_error", attempt.action or "unknown_action")
        seen[pair] += 1
        if seen[pair] >= threshold:
            return idx, pair
    return None, ("", "")


def skeleton_cache_and_reroute(traces: list[TraceRow], out_dir: Path, threshold: int = 8) -> dict[str, object]:
    by_task: dict[tuple[str, str], list[TraceRow]] = defaultdict(list)
    for trace in traces:
        by_task[(trace.project, trace.file)].append(trace)

    skeleton_path = out_dir / "skeleton_cache.jsonl"
    skeleton_count = 0
    with skeleton_path.open("w") as f:
        for trace in traces:
            if trace.status != "VERIFIED":
                continue
            actions = action_sequence(trace)
            if not actions:
                continue
            payload = {
                "model": trace.model,
                "project": trace.project,
                "file": trace.file,
                "effective_total_tokens": effective_total_tokens(trace),
                "attempts": len(trace.attempts),
                "lemmas": trace.lemmas,
                "action_sequence": actions,
                "error_action_sequence": [
                    {
                        "error": a.target_error,
                        "action": a.action,
                        "accepted": a.accepted,
                        "tokens": a.total_tokens,
                    }
                    for a in trace.attempts
                    if a.action
                ],
                "log_path": trace.log_path,
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            skeleton_count += 1

    rows = []
    for trace in traces:
        if trace.status == "VERIFIED":
            continue
        idx, repeated_pair = gate_index(trace, threshold)
        if idx is None:
            continue
        peers = [t for t in by_task[(trace.project, trace.file)] if t.status == "VERIFIED" and t.model != trace.model]
        if not peers:
            continue
        action_votes = Counter()
        peer_models = []
        for peer in peers:
            peer_actions = list(action_sequence(peer))
            if not peer_actions:
                continue
            action_votes[peer_actions[min(idx, len(peer_actions) - 1)]] += 1
            peer_models.append(peer.model)
        if not action_votes:
            continue
        top_action, votes = action_votes.most_common(1)[0]
        rows.append(
            {
                "threshold": threshold,
                "model": trace.model,
                "project": trace.project,
                "file": trace.file,
                "gate_attempt": trace.attempts[idx].index,
                "repeated_error": repeated_pair[0],
                "repeated_action": repeated_pair[1],
                "top_peer_action_at_same_index": top_action,
                "votes": votes,
                "peer_successes": len(peers),
                "peer_models": " ".join(sorted(set(peer_models))),
                "different_from_repeated_action": int(top_action != repeated_pair[1]),
                "effective_total_tokens": effective_total_tokens(trace),
                "log_path": trace.log_path,
            }
        )
    write_csv(
        out_dir / "reroute_prior_threshold8.csv",
        sorted(rows, key=lambda r: int(r["effective_total_tokens"]), reverse=True),
        [
            "threshold",
            "model",
            "project",
            "file",
            "gate_attempt",
            "repeated_error",
            "repeated_action",
            "top_peer_action_at_same_index",
            "votes",
            "peer_successes",
            "peer_models",
            "different_from_repeated_action",
            "effective_total_tokens",
            "log_path",
        ],
    )
    changed = sum(int(r["different_from_repeated_action"]) for r in rows)
    return {
        "skeletons": skeleton_count,
        "reroute_candidates": len(rows),
        "different_top_action": changed,
        "different_top_action_rate": round(changed / len(rows), 4) if rows else 0,
    }


def dataset_summary(traces: list[TraceRow], out_dir: Path) -> dict[str, object]:
    rows = []
    grouped = defaultdict(lambda: Counter())
    for trace in traces:
        counter = grouped[(trace.model, trace.project)]
        counter["tasks"] += 1
        counter[f"status_{trace.status}"] += 1
        counter["total_tokens"] += effective_total_tokens(trace)
        counter["attempts"] += len(trace.attempts)
    for (model, project), counter in sorted(grouped.items()):
        rows.append(
            {
                "model": model,
                "project": project,
                "tasks": counter["tasks"],
                "verified": counter["status_VERIFIED"],
                "failed": counter["tasks"] - counter["status_VERIFIED"],
                "verify_rate": round(counter["status_VERIFIED"] / counter["tasks"], 4) if counter["tasks"] else 0,
                "total_tokens": counter["total_tokens"],
                "mean_attempts": round(counter["attempts"] / counter["tasks"], 2) if counter["tasks"] else 0,
            }
        )
    write_csv(
        out_dir / "dataset_summary_by_model_project.csv",
        rows,
        ["model", "project", "tasks", "verified", "failed", "verify_rate", "total_tokens", "mean_attempts"],
    )
    total = Counter()
    for trace in traces:
        total["tasks"] += 1
        total[f"status_{trace.status}"] += 1
        total["total_tokens"] += effective_total_tokens(trace)
    return {
        "traces": total["tasks"],
        "verified": total["status_VERIFIED"],
        "nonverified": total["tasks"] - total["status_VERIFIED"],
        "total_tokens": total["total_tokens"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir = validate_output_path(args.out_dir, data_root=args.root)

    results = read_results(args.root)
    traces = read_traces(args.root, results)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "dataset": dataset_summary(traces, args.out_dir),
        "result_rows": len(results),
        "matched_traces": len(traces),
    }
    summary["repetition_gate"] = repetition_gate(traces, args.out_dir)
    summary["skeleton_coverage"] = skeleton_coverage(traces, args.out_dir)
    summary["prompt_cost"] = prompt_cost_audit(args.root, traces, args.out_dir)
    summary["skeleton_cache_and_reroute"] = skeleton_cache_and_reroute(traces, args.out_dir)

    with (args.out_dir / "experiment_summary.json").open("w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
