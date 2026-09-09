from __future__ import annotations

import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable

from .trajectory_progress import normalize_code_lines, verifier_state


VERUS_CANDIDATE_RE = re.compile(
    r"(?:^|['\";\s])(?:/[^\s'\";]+/)?verus\s+candidate\.rs\b"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def raw_item(event: dict[str, Any]) -> dict[str, Any]:
    return event.get("data", {}).get("raw_codex_event", {}).get("item", {})


def verifier_output(event: dict[str, Any]) -> str:
    item = raw_item(event)
    if item:
        return str(item.get("aggregated_output") or "")
    data = event.get("data", {})
    return f"{data.get('stdout') or ''}{data.get('stderr') or ''}"


def is_verus_candidate_command(command: str) -> bool:
    return bool(VERUS_CANDIDATE_RE.search(command.replace("\n", " ")))


def extract_verifier_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every actual candidate verifier call, including repeated hashes.

    Structured traces synthesize ``actor=verus`` events for simple commands but
    may omit compound edit-and-verify commands. Codex command results are the
    primary source; non-derived verifier events add independent host checks.
    """
    calls: list[dict[str, Any]] = []
    codex_call_ids: set[str] = set()
    for event in events:
        item = raw_item(event)
        command = str(item.get("command") or "")
        if (
            event.get("actor") == "codex"
            and event.get("type") == "tool_result"
            and item.get("type") == "command_execution"
            and is_verus_candidate_command(command)
        ):
            call_id = str(item.get("id") or event.get("tool_call_id") or "")
            if call_id:
                codex_call_ids.add(call_id)
            output = verifier_output(event)
            calls.append(
                {
                    "event_index": event.get("event_index"),
                    "timestamp": event.get("timestamp"),
                    "candidate_sha256": event.get("candidate_sha256"),
                    "tool_call_id": call_id or None,
                    "origin": "actor",
                    "verifier_output": output,
                    "verifier": verifier_state(output),
                }
            )

    for event in events:
        if event.get("actor") != "verus" or event.get("type") != "verifier":
            continue
        source_id = str(event.get("data", {}).get("source_tool_call_id") or "")
        if source_id and source_id in codex_call_ids:
            continue
        output = verifier_output(event)
        calls.append(
            {
                "event_index": event.get("event_index"),
                "timestamp": event.get("timestamp"),
                "candidate_sha256": event.get("candidate_sha256"),
                "tool_call_id": source_id or None,
                "origin": "host_validation",
                "verifier_output": output,
                "verifier": verifier_state(output),
            }
        )

    calls.sort(key=lambda row: int(row["event_index"] or 0))
    for ordinal, call in enumerate(calls, 1):
        call["call_ordinal"] = ordinal
    return calls


def _completion_tokens(record: dict[str, Any]) -> int:
    return sum(
        int((attempt.get("usage") or {}).get("completion_tokens") or 0)
        for attempt in record.get("attempts") or []
    )


def align_tool_calls_to_output_tokens(
    events: list[dict[str, Any]],
    ledger_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Map Codex tool-call ids to cumulative complete-ledger output tokens.

    Each ledger row stores the input item types for the next model request.
    The increase in ``function_call`` count between adjacent requests is the
    number of tool calls emitted by the preceding response.
    """
    tool_ids = []
    for event in events:
        raw = event.get("data", {}).get("raw_codex_event", {})
        item = raw.get("item", {})
        if (
            event.get("actor") == "codex"
            and raw.get("type") == "item.started"
            and item.get("type") in {"command_execution", "file_change"}
        ):
            call_id = item.get("id")
            if isinstance(call_id, str):
                tool_ids.append(call_id)

    cumulative = []
    total = 0
    for record in ledger_records:
        total += _completion_tokens(record)
        cumulative.append(total)

    mapped: dict[str, int] = {}
    cursor = 0
    previous_call_count = None
    for index, record in enumerate(ledger_records):
        current_types = record.get("input_item_types") or []
        current_call_count = sum(kind == "function_call" for kind in current_types)
        if previous_call_count is not None and current_call_count < previous_call_count:
            raise ValueError("ledger function-call count is not monotonic")
        previous_call_count = current_call_count
        if index + 1 < len(ledger_records):
            next_types = ledger_records[index + 1].get("input_item_types") or []
            next_call_count = sum(kind == "function_call" for kind in next_types)
            emitted = next_call_count - current_call_count
        else:
            emitted = len(tool_ids) - cursor
        if emitted < 0 or cursor + emitted > len(tool_ids):
            raise ValueError("ledger/tool-call alignment is inconsistent")
        for call_id in tool_ids[cursor : cursor + emitted]:
            mapped[call_id] = cumulative[index]
        cursor += emitted

    if cursor != len(tool_ids):
        raise ValueError("not every tool call was aligned to a ledger request")
    return {
        "tool_call_output_tokens": mapped,
        "total_output_tokens": total,
        "request_count": len(ledger_records),
        "tool_call_count": len(tool_ids),
        "alignment": "input_item_type_deltas",
    }


def _brace_delta(line: str) -> int:
    line = line.split("//", 1)[0]
    line = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    return line.count("{") - line.count("}")


def function_body_span(source: str, function_name: str) -> tuple[int, int]:
    """Return zero-based line indices delimiting a proof body, excluding braces."""
    lines = source.splitlines(keepends=True)
    pattern = re.compile(rf"\bproof\s+fn\s+{re.escape(function_name)}\b")
    function_start = next(
        (index for index, line in enumerate(lines) if pattern.search(line)), None
    )
    if function_start is None:
        raise ValueError(f"proof function not found: {function_name}")
    body_open = next(
        (index for index in range(function_start, len(lines)) if "{" in lines[index]),
        None,
    )
    if body_open is None:
        raise ValueError(f"proof function body not found: {function_name}")
    depth = 0
    for index in range(body_open, len(lines)):
        depth += _brace_delta(lines[index])
        if depth == 0:
            return body_open + 1, index
    raise ValueError(f"unbalanced proof function body: {function_name}")


def function_body(source: str, function_name: str) -> str:
    lines = source.splitlines(keepends=True)
    start, end = function_body_span(source, function_name)
    return "".join(lines[start:end])


def proof_line_coverage(current_body: str, final_body: str) -> dict[str, float | int]:
    """Measure how many normalized final-proof lines occur in the current proof."""
    current = Counter(normalize_code_lines(current_body))
    final = Counter(normalize_code_lines(final_body))
    denominator = sum(final.values())
    if denominator == 0:
        raise ValueError("final proof body must contain at least one nonblank line")
    matched = sum((current & final).values())
    return {
        "matched_final_lines": matched,
        "final_lines": denominator,
        "coverage": matched / denominator,
    }


def classify_proof_line(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("assert"):
        return "assert"
    if stripped.startswith("let "):
        return "let_binding"
    if stripped in {"{", "}"}:
        return "block_delimiter"
    if stripped.startswith(
        ("if ", "else", "} else", "match ", "for ", "while ", "loop")
    ):
        return "control_flow"
    if re.match(r"(?:[A-Za-z_][A-Za-z0-9_]*::)*[A-Za-z_][A-Za-z0-9_]*\s*\(.*", stripped):
        return "proof_or_lemma_call"
    return "other"


def _added_body_line_indices(
    baseline_source: str, final_source: str, function_name: str
) -> list[int]:
    baseline_body = function_body(baseline_source, function_name)
    final_lines = final_source.splitlines(keepends=True)
    final_start, final_end = function_body_span(final_source, function_name)
    baseline_lines = baseline_body.splitlines(keepends=True)
    body_lines = final_lines[final_start:final_end]
    baseline_normalized = [line.strip() for line in baseline_lines]
    final_normalized = [line.strip() for line in body_lines]
    indices = []
    for tag, _, _, right_start, right_end in SequenceMatcher(
        None, baseline_normalized, final_normalized, autojunk=False
    ).get_opcodes():
        if tag not in {"insert", "replace"}:
            continue
        indices.extend(
            final_start + offset
            for offset in range(right_start, right_end)
            if body_lines[offset].strip()
        )
    return indices


VerifyCallback = Callable[[str], tuple[bool, str]]


def _candidate_block_ranges(
    records: list[tuple[int, str]],
    candidate_ids: set[int],
    function_name: str,
) -> list[tuple[int, int]]:
    source = "".join(line for _, line in records)
    body_start, body_end = function_body_span(source, function_name)
    stack: list[int] = []
    ranges = []
    for position in range(body_start, body_end):
        clean = records[position][1].split("//", 1)[0]
        clean = re.sub(r'"(?:\\.|[^"\\])*"', '""', clean)
        for character in clean:
            if character == "{":
                stack.append(position)
            elif character == "}" and stack:
                opening = stack.pop()
                if opening < position:
                    line_ids = {
                        line_id
                        for line_id, line in records[opening : position + 1]
                        if line.strip()
                    }
                    if line_ids and line_ids <= candidate_ids:
                        ranges.append((opening, position))
    return sorted(set(ranges), key=lambda pair: (pair[1] - pair[0], pair[0]))


def greedy_prune_proof_lines(
    baseline_source: str,
    final_source: str,
    function_name: str,
    verify: VerifyCallback,
) -> dict[str, Any]:
    """Greedily delete added proof lines and balanced blocks to a fixed point."""
    records = list(enumerate(final_source.splitlines(keepends=True)))
    candidates = _added_body_line_indices(baseline_source, final_source, function_name)
    candidate_ids = set(candidates)
    trials = []
    removed_lines: dict[int, dict[str, Any]] = {}
    pass_ordinal = 0
    while True:
        pass_ordinal += 1
        removed_this_pass = 0
        present_ids = {line_id for line_id, _ in records}
        for original_index in candidates:
            if original_index not in present_ids:
                continue
            current_position = next(
                index
                for index, (line_id, _) in enumerate(records)
                if line_id == original_index
            )
            _, text = records[current_position]
            trial_records = records[:current_position] + records[current_position + 1 :]
            trial_source = "".join(line for _, line in trial_records)
            passed, output = verify(trial_source)
            row = {
                "trial_ordinal": len(trials) + 1,
                "pass_ordinal": pass_ordinal,
                "unit_kind": "line",
                "original_line_number": original_index + 1,
                "original_line_numbers": [original_index + 1],
                "line_count": 1,
                "line": text.rstrip("\n"),
                "category": classify_proof_line(text),
                "verus_passed": passed,
                "removed": passed,
                "verifier_output": output,
            }
            trials.append(row)
            if passed:
                records = trial_records
                present_ids.remove(original_index)
                removed_lines[original_index] = {
                    "original_line_number": original_index + 1,
                    "line": text.rstrip("\n"),
                    "category": classify_proof_line(text),
                    "unit_kind": "line",
                    "pass_ordinal": pass_ordinal,
                }
                removed_this_pass += 1

        while True:
            removed_block = False
            for opening, closing in _candidate_block_ranges(
                records, candidate_ids, function_name
            ):
                unit_records = records[opening : closing + 1]
                trial_records = records[:opening] + records[closing + 1 :]
                trial_source = "".join(line for _, line in trial_records)
                passed, output = verify(trial_source)
                header = unit_records[0][1]
                line_numbers = [
                    line_id + 1 for line_id, line in unit_records if line.strip()
                ]
                row = {
                    "trial_ordinal": len(trials) + 1,
                    "pass_ordinal": pass_ordinal,
                    "unit_kind": "balanced_block",
                    "original_line_number": line_numbers[0],
                    "original_line_numbers": line_numbers,
                    "line_count": len(line_numbers),
                    "line": header.rstrip("\n"),
                    "category": classify_proof_line(header),
                    "verus_passed": passed,
                    "removed": passed,
                    "verifier_output": output,
                }
                trials.append(row)
                if not passed:
                    continue
                records = trial_records
                for line_id, text in unit_records:
                    if not text.strip():
                        continue
                    removed_lines[line_id] = {
                        "original_line_number": line_id + 1,
                        "line": text.rstrip("\n"),
                        "category": classify_proof_line(text),
                        "unit_kind": "balanced_block",
                        "pass_ordinal": pass_ordinal,
                    }
                removed_this_pass += len(line_numbers)
                removed_block = True
                break
            if not removed_block:
                break
        if removed_this_pass == 0:
            break

    pruned_source = "".join(line for _, line in records)
    final_nonblank = len(normalize_code_lines(function_body(final_source, function_name)))
    removed = list(removed_lines.values())
    removed_categories = Counter(row["category"] for row in removed)
    removed_assertions = removed_categories["assert"]
    removed_non_assert = Counter(
        row["category"] for row in removed if row["category"] != "assert"
    )
    return {
        "pruned_source": pruned_source,
        "trials": trials,
        "removed_line_records": sorted(
            removed, key=lambda row: row["original_line_number"]
        ),
        "summary": {
            "final_proof_nonblank_lines": final_nonblank,
            "tested_added_nonblank_lines": len(candidates),
            "pruning_passes": pass_ordinal,
            "verifier_trials": len(trials),
            "removed_lines": len(removed),
            "removable_fraction_of_final_proof_lines": (
                len(removed) / final_nonblank if final_nonblank else 0.0
            ),
            "removable_fraction_of_tested_lines": (
                len(removed) / len(candidates) if candidates else 0.0
            ),
            "removed_assert_lines": removed_assertions,
            "assert_share_of_removed_lines": (
                removed_assertions / len(removed) if removed else 0.0
            ),
            "removed_non_assert_distribution": dict(sorted(removed_non_assert.items())),
        },
    }
