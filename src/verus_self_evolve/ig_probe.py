from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import math
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable

from .data import batch_from_path, file_from_output_dir, model_from_path, project_from_file, read_result_rows
from .data_layout import selected_dataset_path, validate_output_path


ATTEMPT_RE = re.compile(r"Repair attempt\s+(\d+)/(\d+)")
TARGET_RE = re.compile(r"Target error:\s*(?:VerusErrorType\.)?([A-Za-z0-9_]+)")
ACTION_RE = re.compile(r"['\"]primary_action['\"]:\s*['\"]([^'\"]+)['\"]")
AGENT_RE = re.compile(r"Using\s+([A-Za-z0-9_]+Agent)\s+for repair")
ERROR_LOCATION_RE = re.compile(r"['\"]error_location['\"]:\s*\((\d+),\s*(\d+)\)")
CURRENT_SCORE_RE = re.compile(r"Current score:\s*(.*)")
HUNK_HEADER_RE = re.compile(r"@@ -(?P<old_start>\d+)(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@")
SUCCESS_FILE_RE = re.compile(r"fix-v(?P<version>\d+)-a(?P<attempt>\d+)-success-(?P<action>[^.]+)\.rs$")
FINAL_SUCCESS_RE = re.compile(r"fix-v(?P<version>\d+)-success\.rs$")

PROOF_MARKERS = (
    "assert",
    "proof",
    "requires",
    "ensures",
    "invariant",
    "decreases",
    "lemma",
    "by {",
    "reveal",
    "forall",
    "exists",
    "trigger",
    "calc",
    "assert_by",
    "ghost",
    "tracked",
)


@dataclass(frozen=True)
class ParsedAttempt:
    index: int
    target_error: str
    primary_action: str
    agent: str
    error_text: str
    current_score: str
    error_location_start: int | None
    error_location_end: int | None
    accepted: bool
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class TraceRecord:
    trace_id: str
    model: str
    batch: str
    project: str
    file: str
    status: str
    trace_dir: str
    log_path: str
    input_code_path: str
    final_code_path: str
    attempt_count: int


@dataclass(frozen=True)
class PrefixRecord:
    sample_id: str
    trace_id: str
    prefix_id: str
    prefix_kind: str
    attempt_index: int
    model: str
    batch: str
    project: str
    file: str
    trace_dir: str
    log_path: str
    prefix_code_path: str
    final_code_path: str
    prefix_code_sha256: str
    final_code_sha256: str
    target_error: str
    primary_action: str
    action_accepted: bool
    coarse_action: str
    agent: str
    error_text: str
    current_score: str
    history_actions: str
    history_errors: str
    state_text: str


@dataclass(frozen=True)
class TargetRecord:
    sample_id: str
    trace_id: str
    prefix_id: str
    target_type: str
    target_text: str
    target_char_count: int
    target_line_count: int
    source: str
    metadata: dict[str, object]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(errors="replace")


def write_jsonl(path: Path, rows: Iterable[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            if hasattr(row, "__dataclass_fields__"):
                payload = asdict(row)
            else:
                payload = row
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _extract_error_text(chunk: str) -> str:
    marker = "Error text:"
    start = chunk.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end_candidates = [
        chunk.find("Using ", start),
        chunk.find("Phase 1: Observing", start),
        chunk.find("[", start),
    ]
    end_candidates = [x for x in end_candidates if x > start]
    end = min(end_candidates) if end_candidates else min(len(chunk), start + 2000)
    return chunk[start:end].strip()


def parse_attempts(text: str) -> list[ParsedAttempt]:
    matches = list(ATTEMPT_RE.finditer(text))
    attempts: list[ParsedAttempt] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end]
        target = TARGET_RE.search(chunk)
        action = ACTION_RE.search(chunk)
        agent = AGENT_RE.search(chunk)
        location = ERROR_LOCATION_RE.search(chunk)
        score = CURRENT_SCORE_RE.search(chunk)
        attempts.append(
            ParsedAttempt(
                index=int(match.group(1)),
                target_error=target.group(1) if target else "",
                primary_action=_normalize_action(action.group(1)) if action else "",
                agent=agent.group(1) if agent else "",
                error_text=_extract_error_text(chunk),
                current_score=score.group(1).strip() if score else "",
                error_location_start=int(location.group(1)) if location else None,
                error_location_end=int(location.group(2)) if location else None,
                accepted=(
                    "Action accepted" in chunk
                    or "Candidate 1 accepted" in chunk
                    or "is the new best candidate" in chunk
                    or "Repair accepted" in chunk
                ),
                input_tokens=sum(int(x) for x in re.findall(r"Input tokens:\s*(\d+)", chunk)),
                output_tokens=sum(int(x) for x in re.findall(r"Output tokens:\s*(\d+)", chunk)),
            )
        )
    return attempts


def _normalize_action(action: str) -> str:
    return action.strip().lower()


def coarse_action(action: str) -> str:
    action = _normalize_action(action)
    if not action:
        return ""
    if "lemma" in action:
        return "lemma"
    if "forall" in action or "exists" in action or "trigger" in action:
        return "quantifier"
    if "invariant" in action or action == "loopinv":
        return "invariant"
    if "arith" in action or "compute" in action or "ring" in action:
        return "arithmetic"
    if "case" in action:
        return "case_analysis"
    if "postcondition" in action or "precondition" in action:
        return "condition_repair"
    if "seq" in action or "set" in action or "map" in action:
        return "collection"
    return action


def _success_files(trace_dir: Path) -> dict[int, Path]:
    successes: dict[int, tuple[int, Path]] = {}
    for path in trace_dir.glob("fix-v*-a*-success-*.rs"):
        match = SUCCESS_FILE_RE.match(path.name)
        if not match:
            continue
        attempt = int(match.group("attempt"))
        version = int(match.group("version"))
        if attempt not in successes or version > successes[attempt][0]:
            successes[attempt] = (version, path)
    return {attempt: path for attempt, (_, path) in successes.items()}


def _final_code_path(trace_dir: Path) -> Path | None:
    finals: list[tuple[int, Path]] = []
    for path in trace_dir.glob("fix-v*-success.rs"):
        match = FINAL_SUCCESS_RE.match(path.name)
        if match:
            finals.append((int(match.group("version")), path))
    if finals:
        return max(finals, key=lambda item: item[0])[1]

    successes = []
    for path in trace_dir.glob("fix-v*-a*-success-*.rs"):
        match = SUCCESS_FILE_RE.match(path.name)
        if match:
            successes.append((int(match.group("version")), path))
    if successes:
        return max(successes, key=lambda item: item[0])[1]
    return None


def _input_code_path(trace_dir: Path) -> Path | None:
    path = trace_dir / "fix-v0-input.rs"
    return path if path.exists() else None


def _prefix_code_by_attempt(trace_dir: Path, attempts: list[ParsedAttempt]) -> dict[int, Path]:
    input_path = _input_code_path(trace_dir)
    if input_path is None:
        return {}
    success_by_attempt = _success_files(trace_dir)
    out: dict[int, Path] = {}
    current = input_path
    for attempt in attempts:
        out[attempt.index] = current
        if attempt.index in success_by_attempt:
            current = success_by_attempt[attempt.index]
    return out


def _prefix_indices(attempt_positions: list[int]) -> list[tuple[str, int]]:
    if not attempt_positions:
        return []
    positions = [
        ("early", 0),
        ("middle", len(attempt_positions) // 2),
        ("late", len(attempt_positions) - 1),
    ]
    seen = set()
    out = []
    for kind, pos in positions:
        pos = max(0, min(pos, len(attempt_positions) - 1))
        if pos not in seen:
            seen.add(pos)
            out.append((kind, attempt_positions[pos]))
    return out


def iter_verified_trace_dirs(data_root: Path, model_filter: str | None = None) -> list[tuple[Path, dict[str, str]]]:
    result_rows = read_result_rows(data_root)
    out: list[tuple[Path, dict[str, str]]] = []
    for log_path in sorted(data_root.glob("all_batch_results-cyy-*/results-batch_*/o-*/verus-repair.log")):
        model = model_from_path(log_path)
        if model_filter and model != model_filter:
            continue
        batch = batch_from_path(log_path)
        file_name = file_from_output_dir(log_path.parent)
        row = result_rows.get((model, batch, file_name))
        if not row or row.get("status") != "VERIFIED":
            continue
        out.append((log_path.parent, row))
    return out


def _trace_id(model: str, batch: str, file_name: str, trace_dir: Path) -> str:
    raw = f"{model}|{batch}|{file_name}|{trace_dir.name}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _state_text(trace: TraceRecord, attempt: ParsedAttempt, history_actions: list[str], history_errors: list[str]) -> str:
    parts = [
        f"Task: {trace.project}/{trace.file}",
        f"Model: {trace.model}",
        f"Attempt: {attempt.index}",
        f"Current score: {attempt.current_score}",
        f"Selected error type: {attempt.target_error}",
        "Selected error text:",
        attempt.error_text[:2000],
        "Previous actions: " + ", ".join(history_actions),
        "Previous errors: " + ", ".join(history_errors),
    ]
    return "\n".join(parts).strip()


def build_prefix_records(data_root: Path, limit: int, model_filter: str | None = None) -> tuple[list[TraceRecord], list[PrefixRecord]]:
    traces: list[TraceRecord] = []
    prefixes: list[PrefixRecord] = []
    for trace_dir, row in iter_verified_trace_dirs(data_root, model_filter=model_filter):
        log_path = trace_dir / "verus-repair.log"
        input_path = _input_code_path(trace_dir)
        final_path = _final_code_path(trace_dir)
        if input_path is None or final_path is None:
            continue
        text = read_text(log_path)
        attempts = parse_attempts(text)
        if not attempts:
            continue

        model = model_from_path(log_path)
        batch = batch_from_path(log_path)
        file_name = file_from_output_dir(trace_dir)
        trace = TraceRecord(
            trace_id=_trace_id(model, batch, file_name, trace_dir),
            model=model,
            batch=batch,
            project=project_from_file(file_name),
            file=file_name,
            status=row.get("status", ""),
            trace_dir=str(trace_dir),
            log_path=str(log_path),
            input_code_path=str(input_path),
            final_code_path=str(final_path),
            attempt_count=len(attempts),
        )
        prefix_code_by_attempt = _prefix_code_by_attempt(trace_dir, attempts)
        history_actions: list[str] = []
        history_errors: list[str] = []
        selectable_positions = [
            pos for pos, attempt in enumerate(attempts) if attempt.target_error or attempt.primary_action
        ]
        selected_positions = dict(_prefix_indices(selectable_positions))
        selected_by_pos = {pos: kind for kind, pos in selected_positions.items()}
        for pos, attempt in enumerate(attempts):
            if pos in selected_by_pos and attempt.index in prefix_code_by_attempt:
                prefix_path = prefix_code_by_attempt[attempt.index]
                prefix_text = read_text(prefix_path)
                final_text = read_text(final_path)
                prefix_id = f"{selected_by_pos[pos]}-a{attempt.index}"
                sample_id = f"{trace.trace_id}:{prefix_id}"
                prefixes.append(
                    PrefixRecord(
                        sample_id=sample_id,
                        trace_id=trace.trace_id,
                        prefix_id=prefix_id,
                        prefix_kind=selected_by_pos[pos],
                        attempt_index=attempt.index,
                        model=trace.model,
                        batch=trace.batch,
                        project=trace.project,
                        file=trace.file,
                        trace_dir=trace.trace_dir,
                        log_path=trace.log_path,
                        prefix_code_path=str(prefix_path),
                        final_code_path=str(final_path),
                        prefix_code_sha256=sha256_text(prefix_text),
                        final_code_sha256=sha256_text(final_text),
                        target_error=attempt.target_error,
                        primary_action=attempt.primary_action,
                        action_accepted=attempt.accepted,
                        coarse_action=coarse_action(attempt.primary_action),
                        agent=attempt.agent,
                        error_text=attempt.error_text,
                        current_score=attempt.current_score,
                        history_actions="|".join(history_actions),
                        history_errors="|".join(history_errors),
                        state_text=_state_text(trace, attempt, history_actions, history_errors),
                    )
                )
            if attempt.primary_action:
                history_actions.append(attempt.primary_action)
            if attempt.target_error:
                history_errors.append(attempt.target_error)
        traces.append(trace)
        if len(traces) >= limit:
            break
    return traces, prefixes


def _line_count(text: str) -> int:
    return 0 if not text else text.count("\n") + 1


def _split_unified_hunks(diff_text: str) -> list[str]:
    hunks: list[str] = []
    current: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("@@ "):
            if current:
                hunks.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        hunks.append("\n".join(current))
    return hunks


def _hunk_new_start(hunk: str) -> int | None:
    first = hunk.splitlines()[0] if hunk else ""
    match = HUNK_HEADER_RE.search(first)
    return int(match.group("new_start")) if match else None


def _marker_matches(hunk: str) -> list[str]:
    lowered = hunk.lower()
    return [marker for marker in PROOF_MARKERS if marker.lower() in lowered]


def _make_patch_target(prefix: PrefixRecord, max_hunks: int) -> tuple[str, dict[str, object]]:
    prefix_text = read_text(Path(prefix.prefix_code_path))
    final_text = read_text(Path(prefix.final_code_path))
    diff_lines = list(
        difflib.unified_diff(
            prefix_text.splitlines(),
            final_text.splitlines(),
            fromfile="prefix_code",
            tofile="final_code",
            lineterm="",
            n=3,
        )
    )
    hunks = _split_unified_hunks("\n".join(diff_lines))
    scored = []
    for idx, hunk in enumerate(hunks):
        markers = _marker_matches(hunk)
        new_start = _hunk_new_start(hunk)
        location = _parse_error_location(prefix.error_text)
        distance = abs((new_start or 0) - location) if location and new_start else 10**9
        scored.append(
            {
                "idx": idx,
                "hunk": hunk,
                "markers": markers,
                "new_start": new_start,
                "distance": distance,
                "line_count": _line_count(hunk),
            }
        )

    retained = [row for row in scored if row["markers"]]
    fallback = False
    if not retained and scored:
        fallback = True
        retained = sorted(scored, key=lambda row: (row["distance"], row["line_count"], row["idx"]))[:1]
    retained = sorted(retained, key=lambda row: (row["distance"], row["idx"]))
    dropped = retained[max_hunks:]
    retained = retained[:max_hunks]
    retained_ids = {row["idx"] for row in retained}
    dropped = [row for row in scored if row["idx"] not in retained_ids]
    target = "\n\n".join(str(row["hunk"]) for row in retained)
    audit = {
        "prefix_code_sha256": prefix.prefix_code_sha256,
        "final_code_sha256": prefix.final_code_sha256,
        "total_hunks": len(scored),
        "retained_hunks": [
            {
                "idx": row["idx"],
                "new_start": row["new_start"],
                "markers": row["markers"],
                "distance": row["distance"],
                "line_count": row["line_count"],
                "hunk": row["hunk"],
            }
            for row in retained
        ],
        "dropped_hunks": [
            {
                "idx": row["idx"],
                "new_start": row["new_start"],
                "markers": row["markers"],
                "distance": row["distance"],
                "line_count": row["line_count"],
            }
            for row in dropped
        ],
        "patch_fallback": fallback,
        "max_hunks": max_hunks,
    }
    return target, audit


def _parse_error_location(error_text: str) -> int | None:
    match = re.search(r"Line\s+(\d+)-", error_text)
    return int(match.group(1)) if match else None


def build_targets(prefixes: list[PrefixRecord], max_patch_hunks: int) -> tuple[list[TargetRecord], list[dict[str, object]]]:
    targets: list[TargetRecord] = []
    patch_audits: list[dict[str, object]] = []
    for prefix in prefixes:
        action_targets = [
            (
                "action_primary",
                prefix.primary_action,
                "observed_demonstrator_action",
                {
                    "coarse_action": prefix.coarse_action,
                    "action_accepted": prefix.action_accepted,
                    "source_log_path": prefix.log_path,
                    "source_attempt_index": prefix.attempt_index,
                },
            ),
            ("action_coarse", prefix.coarse_action, "derived_coarse_action", {"primary_action": prefix.primary_action}),
        ]
        for target_type, target_text, source, metadata in action_targets:
            targets.append(
                TargetRecord(
                    sample_id=prefix.sample_id,
                    trace_id=prefix.trace_id,
                    prefix_id=prefix.prefix_id,
                    target_type=target_type,
                    target_text=target_text,
                    target_char_count=len(target_text),
                    target_line_count=_line_count(target_text),
                    source=source,
                    metadata=metadata,
                )
            )

        final_text = read_text(Path(prefix.final_code_path))
        targets.append(
            TargetRecord(
                sample_id=prefix.sample_id,
                trace_id=prefix.trace_id,
                prefix_id=prefix.prefix_id,
                target_type="full_proof",
                target_text=final_text,
                target_char_count=len(final_text),
                target_line_count=_line_count(final_text),
                source="final_verified_code",
                metadata={"final_code_path": prefix.final_code_path},
            )
        )

        patch_text, audit = _make_patch_target(prefix, max_hunks=max_patch_hunks)
        patch_audits.append({"sample_id": prefix.sample_id, "trace_id": prefix.trace_id, "prefix_id": prefix.prefix_id, **audit})
        targets.append(
            TargetRecord(
                sample_id=prefix.sample_id,
                trace_id=prefix.trace_id,
                prefix_id=prefix.prefix_id,
                target_type="patch_span",
                target_text=patch_text,
                target_char_count=len(patch_text),
                target_line_count=_line_count(patch_text),
                source="deterministic_diff_filter",
                metadata={
                    "patch_fallback": bool(audit["patch_fallback"]),
                    "total_hunks": int(audit["total_hunks"]),
                    "retained_hunks": len(audit["retained_hunks"]),
                },
            )
        )
    return targets, patch_audits


def _coverage(values: list[object], pred) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if pred(value)) / len(values)


def summarize(traces: list[TraceRecord], prefixes: list[PrefixRecord], targets: list[TargetRecord], patch_audits: list[dict[str, object]]) -> dict[str, object]:
    targets_by_type: dict[str, list[TargetRecord]] = {}
    for target in targets:
        targets_by_type.setdefault(target.target_type, []).append(target)
    target_stats = {}
    for target_type, rows in sorted(targets_by_type.items()):
        lengths = [row.target_char_count for row in rows]
        target_stats[target_type] = {
            "count": len(rows),
            "non_empty_rate": _coverage(rows, lambda row: bool(str(row.target_text).strip())),
            "mean_chars": round(mean(lengths), 2) if lengths else 0,
            "max_chars": max(lengths) if lengths else 0,
        }
    patch_nonempty = _coverage([t for t in targets if t.target_type == "patch_span"], lambda row: bool(row.target_text.strip()))
    return {
        "trace_count": len(traces),
        "prefix_count": len(prefixes),
        "target_count": len(targets),
        "primary_action_coverage": _coverage(prefixes, lambda row: bool(row.primary_action)),
        "final_proof_coverage": _coverage([t for t in targets if t.target_type == "full_proof"], lambda row: bool(row.target_text.strip())),
        "patch_span_non_empty_rate": patch_nonempty,
        "patch_fallback_rate": _coverage(patch_audits, lambda row: bool(row.get("patch_fallback"))),
        "target_stats": target_stats,
        "projects": sorted({trace.project for trace in traces}),
        "models": sorted({trace.model for trace in traces}),
    }


def write_report(path: Path, summary: dict[str, object], out_dir: Path) -> None:
    lines = [
        "# Information Gain Probe Preparation Report",
        "",
        f"- output directory: `{out_dir}`",
        f"- traces: {summary['trace_count']}",
        f"- prefixes: {summary['prefix_count']}",
        f"- targets: {summary['target_count']}",
        f"- primary action coverage: {summary['primary_action_coverage']:.3f}",
        f"- final proof coverage: {summary['final_proof_coverage']:.3f}",
        f"- patch span non-empty rate: {summary['patch_span_non_empty_rate']:.3f}",
        f"- patch fallback rate: {summary['patch_fallback_rate']:.3f}",
        "",
        "## Target Stats",
        "",
        "| target_type | count | non_empty_rate | mean_chars | max_chars |",
        "|---|---:|---:|---:|---:|",
    ]
    for target_type, row in summary["target_stats"].items():
        lines.append(
            f"| {target_type} | {row['count']} | {row['non_empty_rate']:.3f} | {row['mean_chars']} | {row['max_chars']} |"
        )
    lines.extend(
        [
            "",
            "## Data Safety",
            "",
            "Raw VeruSAGE directories were read only. Derived artifacts were written only to the output directory.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _context_text(prefix: dict[str, object], include_code: bool = True) -> str:
    state_text = str(prefix.get("state_text", "")).strip()
    if not include_code:
        return state_text
    code_path = Path(str(prefix.get("prefix_code_path", "")))
    code = read_text(code_path) if code_path.exists() else ""
    return (
        f"{state_text}\n\n"
        "Current prefix code:\n"
        "```verus\n"
        f"{code}\n"
        "```"
    ).strip()


def _trace_rationale(prefix: dict[str, object]) -> str:
    error_type = str(prefix.get("target_error", "unknown error"))
    error_text = str(prefix.get("error_text", "")).strip()
    history_actions = str(prefix.get("history_actions", "")).replace("|", ", ")
    history_errors = str(prefix.get("history_errors", "")).replace("|", ", ")
    return (
        f"The current verifier state reports `{error_type}`. "
        f"The relevant error text is: {error_text[:800]} "
        f"Previous repair actions were: {history_actions or 'none'}. "
        f"Previous error types were: {history_errors or 'none'}. "
        "A useful next repair should address the selected error directly and should account for "
        "why previous attempts did not fully discharge the verifier obligation."
    )


def _local_code_window(prefix: dict[str, object], radius: int = 4) -> str:
    code_path = Path(str(prefix.get("prefix_code_path", "")))
    if not code_path.exists():
        return ""
    code_lines = read_text(code_path).splitlines()
    error_lines = [
        line.strip()
        for line in str(prefix.get("error_text", "")).splitlines()
        if len(line.strip()) >= 12 and not line.strip().startswith(("Error:", "Location:", "Details:", "202"))
    ]
    center = None
    for error_line in error_lines:
        for index, code_line in enumerate(code_lines):
            if error_line in code_line or code_line.strip() == error_line:
                center = index
                break
        if center is not None:
            break
    if center is None:
        return ""
    start = max(0, center - radius)
    end = min(len(code_lines), center + radius + 1)
    return "\n".join(f"{index + 1}: {code_lines[index]}" for index in range(start, end))


def _evidence_artifact(prefix: dict[str, object], error_override: str | None = None) -> str:
    actual_error = str(prefix.get("target_error", "unknown"))
    error_type = error_override or actual_error
    history_actions = [value for value in str(prefix.get("history_actions", "")).split("|") if value]
    history_errors = [value for value in str(prefix.get("history_errors", "")).split("|") if value]
    repeated_error_count = sum(value == actual_error for value in history_errors)
    local_code = _local_code_window(prefix)
    markers = sorted({marker for marker in PROOF_MARKERS if marker.lower() in local_code.lower()})
    error_evidence_lines = [
        line for line in str(prefix.get("error_text", "")).strip().splitlines()
        if not re.match(r"^20\d\d-\d\d-\d\d", line.strip()) and "agents:repair_with_agent" not in line
    ]
    error_evidence = "\n".join(error_evidence_lines).strip()[:500] or "not available"
    return (
        "Decision-time verifier evidence:\n"
        f"- obligation class: {error_type}\n"
        f"- prior occurrences of the current obligation: {repeated_error_count}\n"
        f"- prior repair actions: {', '.join(history_actions) or 'none'}\n"
        f"- distinct prior actions: {len(set(history_actions))}\n"
        f"- local proof markers: {', '.join(markers) or 'none detected'}\n"
        f"- verifier evidence: {error_evidence}\n"
        "- current prefix code near the reported obligation:\n"
        f"{local_code or 'no exact source line was recoverable'}"
    )


def _wrong_error_type(actual: str) -> str:
    return {
        "PostCondFail": "ArithmeticFlow",
        "PreCondFail": "BitVAssertFail",
        "AssertFail": "LoopNoDec",
        "ArithmeticFlow": "PostCondFail",
    }.get(actual, "PostCondFail")


def _counterfactual_artifact(prefix: dict[str, object]) -> str:
    wrong = _wrong_error_type(str(prefix.get("target_error", "")))
    history_actions = [value for value in str(prefix.get("history_actions", "")).split("|") if value]
    wrong_evidence = {
        "ArithmeticFlow": (
            "Error: possible arithmetic overflow in a bounded integer expression\n"
            "Location: the addition may exceed the machine-word upper bound\n"
            "Details: establish operand bounds before evaluating the expression"
        ),
        "LoopNoDec": (
            "Error: loop termination measure did not decrease\n"
            "Location: the loop back-edge preserves the current variant\n"
            "Details: provide a nonnegative decreases expression that becomes smaller"
        ),
        "BitVAssertFail": (
            "Error: bit-vector assertion could not be normalized\n"
            "Location: a shift-and-mask expression has incompatible widths\n"
            "Details: establish the shift bound and reason at the concrete word width"
        ),
        "PostCondFail": (
            "Error: function postcondition is not established at return\n"
            "Location: the final state does not imply the declared ensures clause\n"
            "Details: connect the body result to the postcondition"
        ),
    }[wrong]
    wrong_code = {
        "ArithmeticFlow": "101: let total = left + right;\n102: assert(total >= left);\n103: return total;",
        "LoopNoDec": "201: while index < limit\n202:     invariant index <= limit\n203: { index = index; }",
        "BitVAssertFail": "301: assert((value & (1usize << bit)) != 0);\n302: assert(bit < 64);",
        "PostCondFail": "401: ensures result.is_valid()\n402: {\n403:     return result;\n404: }",
    }[wrong]
    return (
        "Decision-time verifier evidence:\n"
        f"- obligation class: {wrong}\n"
        "- prior occurrences of the current obligation: 0\n"
        f"- prior repair actions: {', '.join(history_actions) or 'none'}\n"
        f"- distinct prior actions: {len(set(history_actions))}\n"
        "- local proof markers: assert, ensures, decreases\n"
        f"- verifier evidence: {wrong_evidence}\n"
        "- current prefix code near the reported obligation:\n"
        f"{wrong_code}"
    )


def _block_shuffled_evidence(prefix: dict[str, object]) -> str:
    lines = _evidence_artifact(prefix).splitlines()
    if len(lines) <= 2:
        return "\n".join(reversed(lines))
    return "\n".join([lines[0], *reversed(lines[1:])])


def _wrong_error_rationale(prefix: dict[str, object]) -> str:
    actual = str(prefix.get("target_error", "unknown error"))
    wrong_by_error = {
        "PostCondFail": ("ArithmeticFlow", "focus on nonlinear arithmetic and overflow bounds"),
        "PreCondFail": ("BitVAssertFail", "focus on bit-vector normalization"),
        "AssertFail": ("LoopNoDec", "focus on a loop decreases clause"),
        "ArithmeticFlow": ("PostCondFail", "strengthen the function postcondition"),
    }
    wrong, advice = wrong_by_error.get(actual, ("PostCondFail", "strengthen the function postcondition"))
    return (
        f"Treat the current verifier state as `{wrong}` and {advice}. "
        "Prioritize that diagnosis even if the reported obligation appears to have another form."
    )


def _length_matched_neutral(reference: str) -> str:
    words = reference.split()
    if not words:
        return ""
    neutral = (
        "Verus programs contain executable code specifications proof blocks ghost state tracked values "
        "functions modules types expressions statements and declarations organized as Rust source text"
    ).split()
    return " ".join(neutral[i % len(neutral)] for i in range(len(words)))


def _artifact_text(
    prefix: dict[str, object],
    artifact_type: str,
    shuffled_prefix: dict[str, object] | None = None,
) -> str:
    if artifact_type == "generic_skill":
        return (
            "When repairing a Verus proof, first identify the selected verifier error, "
            "then choose the smallest proof-oriented action that can expose the missing fact. "
            "Prefer local assertions, quantifier instantiation, relevant lemmas, or invariant strengthening "
            "according to the error type. Avoid repeating an action if the same error did not change."
        )
    if artifact_type == "trace_rationale":
        return _trace_rationale(prefix)
    if artifact_type == "evidence_artifact":
        return _evidence_artifact(prefix)
    if artifact_type in {"cross_trace_same_error", "cross_trace_any"}:
        return _evidence_artifact(shuffled_prefix or prefix)
    if artifact_type == "block_shuffled":
        return _block_shuffled_evidence(prefix)
    if artifact_type == "counterfactual_error":
        return _counterfactual_artifact(prefix)
    if artifact_type == "irrelevant_archive":
        return (
            "A municipal archive organizes historical photographs by neighborhood, year, photographer, "
            "and physical condition. Staff first inspect each envelope for dust or moisture, then assign "
            "a catalog number and record the visible date without guessing missing details. Descriptions "
            "name streets, buildings, public events, and signs that can be read clearly. Uncertain names "
            "remain marked as unknown until another document confirms them. The original print stays in "
            "an acid-free sleeve while a digital copy is stored with color and resolution metadata. Each "
            "month, a librarian reviews a sample of records for consistent spelling and duplicate entries. "
            "Boxes are placed on numbered shelves away from direct sunlight, heating vents, and exterior "
            "walls. Visitors request materials through a reading-room form and handle prints with clean "
            "hands on a flat table. Exhibitions use copies whenever prolonged light could damage an original. "
            "When donors provide additional context, the archive records the source and date of the note "
            "instead of silently replacing earlier descriptions. A separate index connects people, places, "
            "organizations, and recurring civic events. Annual inventories compare shelf locations against "
            "the catalog and flag missing envelopes for manual search. Preservation reports summarize torn "
            "edges, fading, adhesive residue, and other conditions that may require a conservator. These "
            "procedures help future visitors locate material while preserving the distinction between what "
            "the photograph shows and what later contributors remember about it. Public copies may receive "
            "short captions, but internal records retain fuller provenance and handling history."
        )
    if artifact_type == "shuffled_rationale":
        return _trace_rationale(shuffled_prefix or prefix)
    if artifact_type == "wrong_error_rationale":
        return _wrong_error_rationale(prefix)
    if artifact_type == "word_count_matched_control":
        return _length_matched_neutral(_trace_rationale(prefix))
    if artifact_type == "irrelevant_control":
        return (
            "Prefer concise code comments, consistent indentation, and descriptive variable names. "
            "When editing a file, keep formatting readable and avoid unrelated stylistic churn."
        )
    if artifact_type in {"none", "empty_container"}:
        return ""
    raise ValueError(f"unknown artifact_type: {artifact_type}")


def _option_key(index: int) -> str:
    if index < 0 or index >= 26:
        raise ValueError("action-choice pilot supports at most 26 candidates")
    return chr(ord("A") + index)


ACTION_ALIASES = {
    "case-analysis": "case_analysis",
    "instantiate-forall": "instantiate_forall",
    "postcondition-repair": "postcondition_repair",
    "add-trigger-assert": "add_trigger_assert",
}


def _canonical_action(action: str) -> str:
    normalized = _normalize_action(action).replace(" ", "_")
    return ACTION_ALIASES.get(normalized, normalized)


def _action_options(actions: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    canonical = sorted({_canonical_action(action) for action in actions if action.strip()})
    key_to_action = {_option_key(i): action for i, action in enumerate(canonical)}
    action_to_key = {action: key for key, action in key_to_action.items()}
    return key_to_action, action_to_key


def _permuted_action_options(actions: list[str], sample_id: str, seed: int) -> tuple[dict[str, str], dict[str, str]]:
    canonical = sorted({_canonical_action(action) for action in actions if action.strip()})
    digest = int(sha256_text(f"{seed}|{sample_id}")[:16], 16)
    random.Random(digest).shuffle(canonical)
    key_to_action = {_option_key(i): action for i, action in enumerate(canonical)}
    return key_to_action, {action: key for key, action in key_to_action.items()}


def _read_action_ontology(path: Path) -> list[str]:
    return [
        _canonical_action(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _scoring_context(
    context: str,
    target_type: str,
    prompt_style: str,
    action_options: dict[str, str] | None = None,
) -> str:
    if prompt_style == "raw":
        return context
    if prompt_style not in {"explicit", "choices", "json_action"}:
        raise ValueError(f"unknown prompt style: {prompt_style}")
    if prompt_style == "choices" and target_type == "action_primary":
        if not action_options:
            raise ValueError("action choices require a non-empty candidate map")
        options = "\n".join(f"{key}. {action}" for key, action in action_options.items())
        suffix = (
            "Scoring task:\n"
            "Select the next VeruSAGE primary_action from the candidate list. "
            "Return only the option key without analysis or reasoning.\n"
            f"{options}\n"
            "Option:"
        )
    elif prompt_style == "json_action" and target_type == "action_primary":
        if not action_options:
            raise ValueError("JSON action scoring requires a non-empty candidate map")
        labels = ", ".join(action_options.values())
        suffix = (
            "Scoring task:\n"
            "Select the next VeruSAGE primary_action from the allowed labels below. "
            "Return exactly one JSON object without analysis or reasoning.\n"
            f"Allowed labels: {labels}\n"
            'Required schema: {"action":"<primary_action>"}'
        )
    elif target_type == "action_primary":
        suffix = (
            "Scoring task:\n"
            "Predict the next VeruSAGE primary_action. Return only the action label.\n"
            "Next primary_action: "
        )
    elif target_type == "action_coarse":
        suffix = (
            "Scoring task:\n"
            "Predict the coarse repair-action category. Return only the category label.\n"
            "Next coarse_action: "
        )
    elif target_type == "patch_span":
        suffix = (
            "Scoring task:\n"
            "Write only the proof-relevant patch span that leads from this prefix toward the verified proof.\n"
            "Patch span:\n"
        )
    elif target_type == "full_proof":
        suffix = (
            "Scoring task:\n"
            "Write the complete final verified Verus file.\n"
            "Final verified file:\n"
        )
    else:
        suffix = "Scoring task:\nPredict the target text.\nTarget:\n"
    return f"{context}\n\n{suffix}"


def _artifact_conditioned_context(
    base_context_raw: str,
    artifact: str,
    artifact_type: str,
    target_type: str,
    prompt_style: str,
    action_options: dict[str, str] | None,
) -> str:
    artifact_context_raw = base_context_raw
    if artifact or artifact_type == "empty_container":
        artifact_context_raw = f"{base_context_raw}\n\nAdditional artifact:\n{artifact}"
    return _scoring_context(artifact_context_raw, target_type, prompt_style, action_options=action_options)


def _prompt_token_count(tokenizer, text: str, prompt_format: str) -> int:
    if prompt_format == "raw":
        return len(tokenizer.encode(text, add_special_tokens=False))
    if prompt_format == "chat_direct":
        rendered = tokenizer.apply_chat_template(
            [{"role": "user", "content": text}], tokenize=False, add_generation_prompt=False
        )
        return len(tokenizer.encode(rendered + "<|im_start|>assistant\n", add_special_tokens=False))
    token_ids = tokenizer.apply_chat_template(
        [{"role": "user", "content": text}],
        tokenize=True,
        add_generation_prompt=True,
        **({"enable_thinking": False} if prompt_format == "chat_nonthinking" else {}),
    )
    if hasattr(token_ids, "get") and token_ids.get("input_ids") is not None:
        token_ids = token_ids["input_ids"]
    if token_ids and isinstance(token_ids[0], list):
        token_ids = token_ids[0]
    return len(token_ids)


def _match_artifact_intervention(
    tokenizer,
    artifact: str,
    target_delta: int,
    make_context,
    baseline_token_count: int,
    prompt_format: str,
) -> tuple[str, str, int]:
    artifact_ids = list(tokenizer.encode(artifact, add_special_tokens=False))
    padding_families = (" neutral", " context", " proof", " state", " verifier", " x", ".")
    for padding in padding_families:
        retained = min(len(artifact_ids), target_delta)
        pad_count = max(0, target_delta - retained)
        seen = set()
        for _ in range(32):
            state = (retained, pad_count)
            if state in seen:
                break
            seen.add(state)
            base = tokenizer.decode(artifact_ids[:retained]).strip()
            candidate = base + padding * pad_count
            context = make_context(candidate)
            delta = _prompt_token_count(tokenizer, context, prompt_format) - baseline_token_count
            if delta == target_delta:
                return candidate, context, delta
            error = delta - target_delta
            if error > 0:
                if pad_count:
                    pad_count = max(0, pad_count - error)
                else:
                    retained = max(0, retained - error)
            else:
                pad_count += -error
    raise ValueError(f"could not token-match artifact intervention to delta {target_delta}")


def _match_artifact_group_by_truncation(
    tokenizer,
    artifacts: dict[str, str],
    make_context,
    baseline_token_count: int,
    prompt_format: str,
) -> tuple[dict[str, str], dict[str, str], int]:
    achievable: dict[str, dict[int, tuple[str, str]]] = {}
    for artifact_type, artifact in artifacts.items():
        if artifact_type == "empty_container":
            continue
        ids = list(tokenizer.encode(artifact, add_special_tokens=False))
        by_delta: dict[int, tuple[str, str]] = {}
        for retained in range(len(ids), -1, -1):
            candidate = tokenizer.decode(ids[:retained]).strip()
            context = make_context(artifact_type, candidate)
            delta = _prompt_token_count(tokenizer, context, prompt_format) - baseline_token_count
            by_delta.setdefault(delta, (candidate, context))
        achievable[artifact_type] = by_delta
    common = set.intersection(*(set(values) for values in achievable.values()))
    common = {delta for delta in common if delta > 3}
    if not common:
        raise ValueError("artifacts have no common exact intervention-token delta under truncation")
    target_delta = max(common)
    matched_text = dict(artifacts)
    matched_contexts = {}
    for artifact_type, values in achievable.items():
        matched_text[artifact_type], matched_contexts[artifact_type] = values[target_delta]
    return matched_text, matched_contexts, target_delta


def build_cases(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    out_path = validate_output_path(args.out)
    prefixes = {row["sample_id"]: row for row in read_jsonl(run_dir / "prefix_manifest.jsonl")}
    targets = read_jsonl(run_dir / "targets.jsonl")
    artifact_types = args.artifact_types
    ordered_prefixes = sorted(prefixes.values(), key=lambda row: str(row["sample_id"]))
    cross_trace_any: dict[str, dict[str, object]] = {}
    cross_trace_same_error: dict[str, dict[str, object]] = {}
    for index, prefix in enumerate(ordered_prefixes):
        alternatives = [row for row in ordered_prefixes if row.get("trace_id") != prefix.get("trace_id")]
        pool = alternatives or ordered_prefixes
        same_error = [row for row in alternatives if row.get("target_error") == prefix.get("target_error")]
        same_pool = same_error or pool
        same_choice = same_pool[index % len(same_pool)]
        cross_trace_same_error[str(prefix["sample_id"])] = same_choice
        distinct_error = [row for row in alternatives if row.get("target_error") != prefix.get("target_error")]
        distinct_source = [row for row in alternatives if row.get("sample_id") != same_choice.get("sample_id")]
        any_pool = distinct_error or distinct_source or pool
        cross_trace_any[str(prefix["sample_id"])] = any_pool[(index + 1) % len(any_pool)]

    observed_actions = [
        str(target["target_text"])
        for target in targets
        if target["target_type"] == "action_primary" and str(target["target_text"]).strip()
    ]
    ontology_actions = _read_action_ontology(Path(args.action_ontology)) if args.action_ontology else observed_actions
    key_to_action, action_to_key = _action_options(ontology_actions)
    observed_canonical = {_canonical_action(action) for action in observed_actions}
    ontology_canonical = set(action_to_key)
    oov_actions = sorted(observed_canonical - ontology_canonical)
    metric_tokenizer = None
    if args.match_tokenizer:
        from transformers import AutoTokenizer

        metric_tokenizer = AutoTokenizer.from_pretrained(args.match_tokenizer, trust_remote_code=True)
    rows = []
    for target in targets:
        prefix = prefixes.get(str(target["sample_id"]))
        if not prefix:
            continue
        if args.target_types and target["target_type"] not in set(args.target_types):
            continue
        if (
            args.accepted_actions_only
            and not bool(prefix.get("action_accepted", False))
        ):
            continue
        base_context_raw = _context_text(prefix, include_code=not args.no_code_context)
        target_type = str(target["target_type"])
        if args.prompt_style in {"choices", "json_action"} and target_type == "action_primary":
            if args.shuffle_option_order:
                choices, per_sample_action_to_key = _permuted_action_options(
                    ontology_actions, str(target["sample_id"]), args.seed
                )
            else:
                choices, per_sample_action_to_key = key_to_action, action_to_key
        else:
            choices, per_sample_action_to_key = None, {}
        base_context = _scoring_context(base_context_raw, target_type, args.prompt_style, action_options=choices)
        artifact_texts = {}
        artifact_sources: dict[str, dict[str, object]] = {}
        for artifact_type in artifact_types:
            source_prefix = None
            if artifact_type == "cross_trace_same_error":
                source_prefix = cross_trace_same_error.get(str(prefix["sample_id"]))
            elif artifact_type in {"cross_trace_any", "shuffled_rationale"}:
                source_prefix = cross_trace_any.get(str(prefix["sample_id"]))
            artifact_texts[artifact_type] = _artifact_text(
                prefix,
                artifact_type,
                shuffled_prefix=source_prefix,
            )
            artifact_sources[artifact_type] = source_prefix or prefix
        reference_delta = None
        baseline_token_count = None
        matched_contexts: dict[str, str] = {}
        if metric_tokenizer and args.reference_artifact in artifact_texts:
            baseline_token_count = _prompt_token_count(metric_tokenizer, base_context, args.prompt_format)
            reference_artifact = artifact_texts[args.reference_artifact]
            reference_context = _artifact_conditioned_context(
                base_context_raw,
                reference_artifact,
                args.reference_artifact,
                target_type,
                args.prompt_style,
                choices,
            )
            reference_delta = (
                _prompt_token_count(metric_tokenizer, reference_context, args.prompt_format)
                - baseline_token_count
            )
            matched_contexts[args.reference_artifact] = reference_context
            for artifact_type, artifact in list(artifact_texts.items()):
                if artifact_type in {args.reference_artifact, "empty_container"}:
                    continue
                matched_artifact, matched_context, matched_delta = _match_artifact_intervention(
                    metric_tokenizer,
                    artifact,
                    reference_delta,
                    lambda text, artifact_type=artifact_type: _artifact_conditioned_context(
                        base_context_raw, text, artifact_type, target_type, args.prompt_style, choices
                    ),
                    baseline_token_count,
                    args.prompt_format,
                )
                if matched_delta != reference_delta:
                    raise AssertionError("exact intervention matching returned an inconsistent delta")
                artifact_texts[artifact_type] = matched_artifact
                matched_contexts[artifact_type] = matched_context
        for artifact_type in artifact_types:
            artifact = artifact_texts[artifact_type]
            conditioned_context = matched_contexts.get(artifact_type) or _artifact_conditioned_context(
                base_context_raw, artifact, artifact_type, target_type, args.prompt_style, choices
            )
            token_match_exact = None
            intervention_token_count = None
            if metric_tokenizer:
                assert baseline_token_count is not None
                intervention_token_count = (
                    _prompt_token_count(metric_tokenizer, conditioned_context, args.prompt_format)
                    - baseline_token_count
                )
                token_match_exact = (
                    intervention_token_count == reference_delta
                    if artifact_type != "empty_container" and reference_delta is not None
                    else None
                )
            raw_target = str(target["target_text"])
            original_target = _canonical_action(raw_target) if target_type == "action_primary" else raw_target
            serialized_target = original_target
            candidate_targets: list[str] = []
            assistant_prefix = ""
            if choices:
                if original_target not in per_sample_action_to_key:
                    continue
                if args.prompt_style == "json_action":
                    assistant_prefix = '{"action":"'
                    serialized_target = original_target + '"}'
                    candidate_targets = [action + '"}' for action in choices.values()]
                else:
                    serialized_target = per_sample_action_to_key[original_target]
                    candidate_targets = list(choices.keys())
            rows.append(
                {
                    "case_id": sha256_text(
                        f"{target['sample_id']}|{target['target_type']}|{artifact_type}"
                    )[:16],
                    "sample_id": target["sample_id"],
                    "trace_id": target["trace_id"],
                    "prefix_id": target["prefix_id"],
                    "target_type": target["target_type"],
                    "artifact_type": artifact_type,
                    "artifact_text": artifact,
                    "baseline_context": base_context,
                    "artifact_context": conditioned_context,
                    "target_text": serialized_target,
                    "target_sha256": sha256_text(raw_target),
                    "target_char_count": len(serialized_target),
                    "assistant_prefix": assistant_prefix,
                    "observed_action_text": original_target if target_type == "action_primary" else "",
                    "action_accepted": bool(prefix.get("action_accepted", False)),
                    "source_log_path": prefix.get("log_path", ""),
                    "source_attempt_index": prefix.get("attempt_index"),
                    "candidate_targets": candidate_targets,
                    "action_options": choices or {},
                    "candidate_scope": (
                        "predeclared_action_ontology" if choices and args.action_ontology else
                        "pilot_manifest_observed_actions" if choices else "not_applicable"
                    ),
                    "option_order_seed": args.seed if args.shuffle_option_order else None,
                    "option_map_sha256": sha256_text(json.dumps(choices or {}, sort_keys=True)),
                    "prepared_prompt_format": args.prompt_format,
                    "reference_artifact": args.reference_artifact,
                    "reference_intervention_token_count": reference_delta,
                    "prepared_intervention_token_count": intervention_token_count,
                    "token_match_exact": token_match_exact,
                    "artifact_source_sample_id": artifact_sources[artifact_type].get("sample_id", ""),
                    "artifact_source_trace_id": artifact_sources[artifact_type].get("trace_id", ""),
                    "source": target["source"],
                }
            )
    write_jsonl(out_path, rows)
    ontology_path = Path(args.action_ontology) if args.action_ontology else None
    tokenizer_config = Path(args.match_tokenizer) / "tokenizer_config.json" if args.match_tokenizer else None
    summary = {
        "run_dir": str(run_dir),
        "case_count": len(rows),
        "artifact_types": artifact_types,
        "target_types": sorted({row["target_type"] for row in rows}),
        "include_code_context": not args.no_code_context,
        "prompt_style": args.prompt_style,
        "action_options": "per-sample deterministic permutation" if args.shuffle_option_order else key_to_action,
        "action_ontology": args.action_ontology,
        "accepted_actions_only": args.accepted_actions_only,
        "observed_action_count": len(observed_canonical),
        "observed_state_count": len({row["sample_id"] for row in rows}),
        "trace_count": len({row["trace_id"] for row in rows}),
        "action_ontology_count": len(ontology_canonical),
        "action_ontology_coverage": (
            len(observed_canonical & ontology_canonical) / len(observed_canonical) if observed_canonical else 1.0
        ),
        "oov_actions": oov_actions,
        "target_filter": args.target_types,
        "match_tokenizer": args.match_tokenizer,
        "prompt_format": args.prompt_format,
        "reference_artifact": args.reference_artifact,
        "shuffle_option_order": args.shuffle_option_order,
        "seed": args.seed,
        "cases_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "ontology_sha256": hashlib.sha256(ontology_path.read_bytes()).hexdigest() if ontology_path else None,
        "tokenizer_config_sha256": (
            hashlib.sha256(tokenizer_config.read_bytes()).hexdigest() if tokenizer_config and tokenizer_config.exists() else None
        ),
        "ig_probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    Path(str(out_path) + ".summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")


def prepare(args: argparse.Namespace) -> None:
    data_root = (
        Path(args.data_root)
        if args.data_root
        else selected_dataset_path("verusage")
    )
    out_dir = validate_output_path(args.out, data_root=data_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    traces, prefixes = build_prefix_records(data_root, limit=args.limit, model_filter=args.model)
    targets, patch_audits = build_targets(prefixes, max_patch_hunks=args.max_patch_hunks)
    summary = summarize(traces, prefixes, targets, patch_audits)

    write_jsonl(out_dir / "traces.jsonl", traces)
    write_jsonl(out_dir / "prefix_manifest.jsonl", prefixes)
    write_jsonl(out_dir / "targets.jsonl", targets)
    write_jsonl(out_dir / "patch_audit.jsonl", patch_audits)
    write_csv(
        out_dir / "prefix_manifest.csv",
        [
            {
                "sample_id": row.sample_id,
                "trace_id": row.trace_id,
                "prefix_kind": row.prefix_kind,
                "attempt_index": row.attempt_index,
                "model": row.model,
                "project": row.project,
                "file": row.file,
                "target_error": row.target_error,
                "primary_action": row.primary_action,
                "action_accepted": row.action_accepted,
                "coarse_action": row.coarse_action,
                "prefix_code_path": row.prefix_code_path,
                "final_code_path": row.final_code_path,
            }
            for row in prefixes
        ],
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_report(out_dir / "report.md", summary, out_dir)


def add_prepare_parser(subparsers) -> None:
    parser = subparsers.add_parser("ig-probe-prepare", help="prepare hands-on trace prefixes and IG targets")
    parser.add_argument(
        "--data-root",
        help="path containing all_batch_results-cyy-*; defaults to the locally selected source",
    )
    parser.add_argument("--out", required=True, help="output run directory")
    parser.add_argument("--limit", type=int, default=5, help="number of verified trace directories to parse")
    parser.add_argument("--model", default=None, help="optional model filter, e.g. claude, claude-s4, gpt5, o4mini")
    parser.add_argument("--max-patch-hunks", type=int, default=5)
    parser.set_defaults(func=prepare)

    cases = subparsers.add_parser("ig-probe-build-cases", help="build baseline/artifact-conditioned scoring cases")
    cases.add_argument("--run-dir", required=True, help="directory produced by ig-probe-prepare")
    cases.add_argument("--out", required=True, help="JSONL scoring case output")
    cases.add_argument(
        "--artifact-types",
        nargs="+",
        default=[
            "evidence_artifact",
            "cross_trace_same_error",
            "cross_trace_any",
            "block_shuffled",
            "counterfactual_error",
            "irrelevant_archive",
            "empty_container",
        ],
        choices=[
            "none",
            "empty_container",
            "generic_skill",
            "trace_rationale",
            "shuffled_rationale",
            "wrong_error_rationale",
            "word_count_matched_control",
            "irrelevant_control",
            "evidence_artifact",
            "cross_trace_same_error",
            "cross_trace_any",
            "block_shuffled",
            "counterfactual_error",
            "irrelevant_archive",
        ],
    )
    cases.add_argument("--no-code-context", action="store_true", help="omit full prefix code from scoring context")
    cases.add_argument(
        "--prompt-style", choices=["raw", "explicit", "choices", "json_action"], default="raw"
    )
    cases.add_argument("--action-ontology", default=None, help="predeclared newline-delimited action ontology")
    cases.add_argument(
        "--accepted-actions-only",
        action="store_true",
        help="retain every requested target only for states whose demonstrator action was locally accepted",
    )
    cases.add_argument("--target-types", nargs="+", default=None)
    cases.add_argument("--match-tokenizer", default=None, help="tokenizer used for exact intervention matching")
    cases.add_argument(
        "--prompt-format", choices=["raw", "chat", "chat_direct", "chat_nonthinking"], default="chat_direct"
    )
    cases.add_argument("--reference-artifact", default="evidence_artifact")
    cases.add_argument("--shuffle-option-order", action="store_true")
    cases.add_argument("--seed", type=int, default=20260713)
    cases.set_defaults(func=build_cases)
