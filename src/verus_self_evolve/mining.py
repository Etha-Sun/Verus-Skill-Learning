from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .models import CandidateRule, Trace
from .motifs import motifs_for_trace


def gate_event(trace: Trace, threshold: int) -> tuple[int | None, tuple[str, str]]:
    seen: Counter[tuple[str, str]] = Counter()
    for idx, attempt in enumerate(trace.attempts):
        pair = (attempt.target_error or "unknown_error", attempt.action or "unknown_action")
        seen[pair] += 1
        if seen[pair] >= threshold:
            return idx, pair
    return None, ("", "")


def peer_success_action_prior(
    trace: Trace,
    traces_by_task: dict[tuple[str, str], list[Trace]],
    gate_idx: int,
) -> tuple[str, ...]:
    votes: Counter[str] = Counter()
    for peer in traces_by_task[(trace.project, trace.file)]:
        if peer.model == trace.model or not peer.verified:
            continue
        actions = peer.action_sequence
        if not actions:
            continue
        votes[actions[min(gate_idx, len(actions) - 1)]] += 1
    return tuple(action for action, _ in votes.most_common(3))


def mine_candidate_rules(traces: list[Trace], thresholds: tuple[int, ...] = (4, 6, 8)) -> list[CandidateRule]:
    traces_by_task: dict[tuple[str, str], list[Trace]] = defaultdict(list)
    for trace in traces:
        traces_by_task[(trace.project, trace.file)].append(trace)

    grouped: dict[tuple[str, int, str, str, str, str], Counter[str]] = defaultdict(Counter)
    support: Counter[tuple[str, int, str, str, str, str]] = Counter()
    evidence_tokens: Counter[tuple[str, int, str, str, str, str]] = Counter()

    for trace in traces:
        if trace.verified:
            continue
        trace_motifs = motifs_for_trace(trace) or ("any",)
        for threshold in thresholds:
            gate_idx, pair = gate_event(trace, threshold)
            if gate_idx is None:
                continue
            peer_actions = peer_success_action_prior(trace, traces_by_task, gate_idx)
            if not peer_actions:
                continue
            repeated_error, repeated_action = pair
            keys = [
                ("generic", threshold, "*", "*", repeated_error, repeated_action),
                ("project", threshold, trace.project, "*", repeated_error, repeated_action),
            ]
            keys.extend(
                ("motif", threshold, trace.project, motif, repeated_error, repeated_action)
                for motif in trace_motifs
            )
            for key in keys:
                support[key] += 1
                evidence_tokens[key] += trace.effective_total_tokens
                grouped[key].update(peer_actions)

    rules = []
    for key, counter in grouped.items():
        level, threshold, project, motif, repeated_error, repeated_action = key
        if support[key] < 2 and level != "generic":
            continue
        prefer_actions = tuple(action for action, _ in counter.most_common(3) if action != repeated_action)
        if not prefer_actions:
            continue
        rule_id = "__".join(
            [
                level,
                str(threshold),
                project.replace("*", "all"),
                motif.replace("*", "any"),
                repeated_error,
                repeated_action,
            ]
        )
        rules.append(
            CandidateRule(
                rule_id=rule_id,
                level=level,
                threshold=threshold,
                project=project,
                motif=motif,
                repeated_error=repeated_error,
                repeated_action=repeated_action,
                prefer_actions=prefer_actions,
                support_traces=support[key],
                evidence=f"peer_success_actions={dict(counter.most_common(5))}; covered_tokens={evidence_tokens[key]}",
            )
        )
    return sorted(rules, key=lambda r: (r.level, -r.support_traces, r.rule_id))


def write_rules(path: Path, rules: list[CandidateRule]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for rule in rules:
            f.write(json.dumps(rule.__dict__, ensure_ascii=False) + "\n")


def write_skeleton_cache(path: Path, traces: list[Trace]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for trace in traces:
            if not trace.verified or not trace.action_sequence:
                continue
            payload = {
                "model": trace.model,
                "project": trace.project,
                "file": trace.file,
                "motifs": motifs_for_trace(trace),
                "lemmas": trace.lemmas,
                "recursive_functions": trace.recursive_functions,
                "opaque_functions": trace.opaque_functions,
                "effective_total_tokens": trace.effective_total_tokens,
                "action_sequence": trace.action_sequence,
                "error_action_sequence": [
                    {
                        "error": attempt.target_error,
                        "action": attempt.action,
                        "accepted": attempt.accepted,
                        "tokens": attempt.total_tokens,
                    }
                    for attempt in trace.attempts
                    if attempt.action
                ],
                "log_path": trace.log_path,
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

