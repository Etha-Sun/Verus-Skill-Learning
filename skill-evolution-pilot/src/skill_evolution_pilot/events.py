from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .redaction import redact


SCHEMA_VERSION = "1"
EVENT_TYPES = {
    "model_request",
    "model_response",
    "tool_call",
    "tool_result",
    "edit",
    "verifier",
    "lifecycle",
}
ACTORS = {"codex", "qwen", "host", "verus", "lynette"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_event(
    *,
    event_index: int,
    run_id: str,
    actor: str,
    event_type: str,
    data: dict[str, Any],
    request_id: str | None = None,
    tool_call_id: str | None = None,
    payload_complete: bool = True,
    candidate_sha256: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    if event_index < 1:
        raise ValueError("event_index must be positive")
    if actor not in ACTORS:
        raise ValueError(f"unsupported actor: {actor}")
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unsupported event type: {event_type}")
    return {
        "schema_version": SCHEMA_VERSION,
        "event_index": event_index,
        "timestamp": timestamp or utc_now(),
        "run_id": run_id,
        "actor": actor,
        "type": event_type,
        "request_id": request_id,
        "tool_call_id": tool_call_id,
        "payload_complete": bool(payload_complete),
        "candidate_sha256": candidate_sha256,
        "data": data,
    }


@dataclass
class EventLog:
    path: Path
    run_id: str
    secrets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise ValueError(f"event log already exists: {self.path}")
        self._next_index = 1

    @property
    def next_index(self) -> int:
        return self._next_index

    def append(
        self,
        *,
        actor: str,
        event_type: str,
        data: dict[str, Any],
        request_id: str | None = None,
        tool_call_id: str | None = None,
        payload_complete: bool = True,
        candidate_sha256: str | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        event = make_event(
            event_index=self._next_index,
            run_id=self.run_id,
            actor=actor,
            event_type=event_type,
            data=redact(data, self.secrets),
            request_id=request_id,
            tool_call_id=tool_call_id,
            payload_complete=payload_complete,
            candidate_sha256=candidate_sha256,
            timestamp=timestamp,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._next_index += 1
        return event


def load_events(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    parse_errors = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            if not isinstance(row, dict):
                parse_errors += 1
                continue
            rows.append(row)
    return rows, parse_errors


def _duplicate_ids(ids: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in ids:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def audit_events(rows: list[dict[str, Any]], parse_errors: int = 0) -> dict[str, Any]:
    schema_errors: list[str] = []
    expected_indices = list(range(1, len(rows) + 1))
    observed_indices = [row.get("event_index") for row in rows]
    if observed_indices != expected_indices:
        schema_errors.append("event_indices_not_contiguous")

    request_calls: list[str] = []
    request_results: list[str] = []
    tool_calls: list[str] = []
    tool_results: list[str] = []
    unbound_verifiers = 0
    incomplete_payloads = 0

    for row in rows:
        if row.get("schema_version") != SCHEMA_VERSION:
            schema_errors.append("schema_version")
        if row.get("actor") not in ACTORS:
            schema_errors.append("actor")
        if row.get("type") not in EVENT_TYPES:
            schema_errors.append("type")
        if row.get("run_id") in (None, ""):
            schema_errors.append("run_id")
        if not isinstance(row.get("data"), dict):
            schema_errors.append("data")
        if row.get("payload_complete") is not True:
            incomplete_payloads += 1
        event_type = row.get("type")
        request_id = row.get("request_id")
        tool_call_id = row.get("tool_call_id")
        if event_type == "model_request":
            if request_id:
                request_calls.append(str(request_id))
            else:
                schema_errors.append("model_request_missing_id")
        elif event_type == "model_response":
            if request_id:
                request_results.append(str(request_id))
            else:
                schema_errors.append("model_response_missing_id")
        elif event_type == "tool_call":
            if tool_call_id:
                tool_calls.append(str(tool_call_id))
            else:
                schema_errors.append("tool_call_missing_id")
        elif event_type == "tool_result":
            if tool_call_id:
                tool_results.append(str(tool_call_id))
            else:
                schema_errors.append("tool_result_missing_id")
        elif event_type == "verifier" and not row.get("candidate_sha256"):
            unbound_verifiers += 1

    unpaired_requests = sorted(set(request_calls) ^ set(request_results))
    unpaired_tools = sorted(set(tool_calls) ^ set(tool_results))
    duplicate_requests = _duplicate_ids(request_calls) + _duplicate_ids(request_results)
    duplicate_tools = _duplicate_ids(tool_calls) + _duplicate_ids(tool_results)
    schema_errors = sorted(set(schema_errors))
    valid = not any(
        (
            parse_errors,
            schema_errors,
            unpaired_requests,
            unpaired_tools,
            duplicate_requests,
            duplicate_tools,
            unbound_verifiers,
            incomplete_payloads,
        )
    )
    return {
        "event_count": len(rows),
        "parse_errors": parse_errors,
        "schema_errors": schema_errors,
        "unpaired_request_ids": unpaired_requests,
        "unpaired_tool_call_ids": unpaired_tools,
        "duplicate_request_ids": sorted(set(duplicate_requests)),
        "duplicate_tool_call_ids": sorted(set(duplicate_tools)),
        "unbound_verifier_count": unbound_verifiers,
        "incomplete_payload_count": incomplete_payloads,
        "valid_f3_event_stream": valid,
    }
