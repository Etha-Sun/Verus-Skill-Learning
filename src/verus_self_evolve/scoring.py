from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from .mining import gate_event, peer_success_action_prior
from .models import CandidateRule, Trace
from .motifs import motifs_for_trace


def rule_matches_trace(rule: CandidateRule, trace: Trace) -> tuple[int | None, tuple[str, str]]:
    if rule.project != "*" and rule.project != trace.project:
        return None, ("", "")
    if rule.motif != "*" and rule.motif not in motifs_for_trace(trace):
        return None, ("", "")
    gate_idx, pair = gate_event(trace, rule.threshold)
    if gate_idx is None:
        return None, ("", "")
    if pair != (rule.repeated_error, rule.repeated_action):
        return None, ("", "")
    return gate_idx, pair


def score_rules(traces: list[Trace], rules: list[CandidateRule]) -> list[dict[str, object]]:
    traces_by_task: dict[tuple[str, str], list[Trace]] = defaultdict(list)
    for trace in traces:
        traces_by_task[(trace.project, trace.file)].append(trace)

    total_failed_tokens = sum(trace.effective_total_tokens for trace in traces if not trace.verified)
    verified_count = sum(1 for trace in traces if trace.verified)
    rows = []
    for rule in rules:
        covered_failed = 0
        saved_failed_tokens = 0
        verified_false_stops = 0
        reroute_candidates = 0
        peer_action_diff = 0
        for trace in traces:
            gate_idx, _ = rule_matches_trace(rule, trace)
            if gate_idx is None:
                continue
            tail_tokens = sum(attempt.total_tokens for attempt in trace.attempts[gate_idx:])
            if trace.verified:
                verified_false_stops += 1
            else:
                covered_failed += 1
                saved_failed_tokens += tail_tokens
                peer_actions = peer_success_action_prior(trace, traces_by_task, gate_idx)
                if peer_actions:
                    reroute_candidates += 1
                    if peer_actions[0] != rule.repeated_action:
                        peer_action_diff += 1
        rows.append(
            {
                "rule_id": rule.rule_id,
                "level": rule.level,
                "threshold": rule.threshold,
                "project": rule.project,
                "motif": rule.motif,
                "repeated_error": rule.repeated_error,
                "repeated_action": rule.repeated_action,
                "prefer_actions": " ".join(rule.prefer_actions),
                "support_traces": rule.support_traces,
                "covered_failed_traces": covered_failed,
                "saved_failed_tokens": saved_failed_tokens,
                "saved_failed_token_rate": round(saved_failed_tokens / total_failed_tokens, 6)
                if total_failed_tokens
                else 0,
                "verified_false_stops": verified_false_stops,
                "verified_false_stop_rate": round(verified_false_stops / verified_count, 6)
                if verified_count
                else 0,
                "reroute_candidates": reroute_candidates,
                "peer_action_diff_rate": round(peer_action_diff / reroute_candidates, 6)
                if reroute_candidates
                else 0,
                "evidence": rule.evidence,
            }
        )
    return sorted(
        rows,
        key=lambda r: (
            -float(r["saved_failed_tokens"]),
            float(r["verified_false_stop_rate"]),
            -int(r["covered_failed_traces"]),
        ),
    )


def policy_ablation(
    traces: list[Trace],
    rules: list[CandidateRule],
    rule_scores: list[dict[str, object]],
    top_k: int = 20,
) -> list[dict[str, object]]:
    scores_by_level: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rule_scores:
        scores_by_level[str(row["level"])].append(row)

    rules_by_id = {rule.rule_id: rule for rule in rules}
    traces_by_task: dict[tuple[str, str], list[Trace]] = defaultdict(list)
    for trace in traces:
        traces_by_task[(trace.project, trace.file)].append(trace)

    verified_count = sum(1 for trace in traces if trace.verified)

    out = []
    for level, rows in sorted(scores_by_level.items()):
        top = rows[:top_k]
        top_rules = [rules_by_id[str(row["rule_id"])] for row in top if str(row["rule_id"]) in rules_by_id]
        covered_failed = 0
        saved_failed_tokens = 0
        verified_false_stops = 0
        reroute_candidates = 0
        peer_action_diff = 0
        for trace in traces:
            matched: tuple[CandidateRule, int] | None = None
            for rule in top_rules:
                gate_idx, _ = rule_matches_trace(rule, trace)
                if gate_idx is not None:
                    matched = (rule, gate_idx)
                    break
            if matched is None:
                continue
            rule, gate_idx = matched
            if trace.verified:
                verified_false_stops += 1
            else:
                covered_failed += 1
                saved_failed_tokens += sum(attempt.total_tokens for attempt in trace.attempts[gate_idx:])
                peer_actions = peer_success_action_prior(trace, traces_by_task, gate_idx)
                if peer_actions:
                    reroute_candidates += 1
                    if peer_actions[0] != rule.repeated_action:
                        peer_action_diff += 1
        out.append(
            {
                "policy_level": level,
                "rules": len(rows),
                "selected_top_k": len(top_rules),
                "union_covered_failed_traces": covered_failed,
                "union_saved_failed_tokens": saved_failed_tokens,
                "union_verified_false_stops": verified_false_stops,
                "union_verified_false_stop_rate": round(verified_false_stops / verified_count, 6)
                if verified_count
                else 0,
                "union_reroute_candidates": reroute_candidates,
                "union_peer_action_diff_rate": round(peer_action_diff / reroute_candidates, 6)
                if reroute_candidates
                else 0,
                "best_rule": top[0]["rule_id"] if top else "",
                "best_rule_saved_failed_tokens": top[0]["saved_failed_tokens"] if top else 0,
            }
        )
    return out


def dataset_summary(traces: list[Trace]) -> dict[str, object]:
    status = Counter(trace.status for trace in traces)
    projects = Counter(trace.project for trace in traces)
    return {
        "traces": len(traces),
        "verified": status["VERIFIED"],
        "nonverified": len(traces) - status["VERIFIED"],
        "effective_total_tokens": sum(trace.effective_total_tokens for trace in traces),
        "projects": dict(sorted(projects.items())),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
