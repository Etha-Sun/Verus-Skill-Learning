from __future__ import annotations

import difflib
import json
import shutil
from pathlib import Path
from typing import Any

from .events import EventLog
from .redaction import redact_text
from .workspace import sha256_file


def _candidate_hash(candidate_path: Path | None) -> str | None:
    if candidate_path is None or not candidate_path.is_file():
        return None
    return sha256_file(candidate_path)


def append_codex_event(
    *,
    raw: dict[str, Any],
    log: EventLog,
    candidate_path: Path | None = None,
) -> None:
    """Index one raw Codex event without dropping any provider field."""
    raw_type = str(raw.get("type") or "unknown")
    item = raw.get("item")
    if isinstance(item, dict):
        item_type = str(item.get("type") or "unknown")
        item_id = str(item.get("id") or f"codex-item-{log.next_index}")
        candidate_sha = _candidate_hash(candidate_path)
        if item_type == "command_execution":
            event_type = "tool_call" if raw_type == "item.started" else "tool_result"
            complete = bool(item.get("command")) and (
                event_type == "tool_call"
                or (
                    item.get("status") is not None
                    and item.get("aggregated_output") is not None
                    and item.get("exit_code") is not None
                )
            )
            log.append(
                actor="codex",
                event_type=event_type,
                tool_call_id=item_id,
                payload_complete=complete,
                candidate_sha256=candidate_sha,
                data={"raw_codex_event": raw},
            )
            if event_type == "tool_result":
                command = str(item.get("command") or "")
                verifier_actor = None
                if "lynette" in command:
                    verifier_actor = "lynette"
                elif "verus" in command:
                    verifier_actor = "verus"
                if verifier_actor is not None:
                    log.append(
                        actor=verifier_actor,
                        event_type="verifier",
                        payload_complete=complete,
                        candidate_sha256=candidate_sha,
                        data={
                            "source_tool_call_id": item_id,
                            "raw_codex_event": raw,
                        },
                    )
            return
        if item_type == "file_change":
            changes = item.get("changes")
            log.append(
                actor="codex",
                event_type="edit",
                payload_complete=isinstance(changes, list) and bool(changes),
                candidate_sha256=candidate_sha,
                data={"raw_codex_event": raw},
            )
            return
        if item_type in {"agent_message", "reasoning"}:
            visible_content = (
                item.get("text")
                or item.get("content")
                or item.get("summary")
            )
            log.append(
                actor="codex",
                event_type="lifecycle",
                payload_complete=visible_content is not None,
                candidate_sha256=candidate_sha,
                data={"raw_codex_event": raw},
            )
            return
        if item_type == "todo_list":
            log.append(
                actor="codex",
                event_type="lifecycle",
                payload_complete=isinstance(item.get("items"), list),
                candidate_sha256=candidate_sha,
                data={"raw_codex_event": raw},
            )
            return
        log.append(
            actor="codex",
            event_type="lifecycle",
            payload_complete=False,
            candidate_sha256=candidate_sha,
            data={"raw_codex_event": raw},
        )
        return

    log.append(
        actor="codex",
        event_type="lifecycle",
        payload_complete=raw_type != "unknown",
        candidate_sha256=_candidate_hash(candidate_path),
        data={"raw_codex_event": raw},
    )


class CodexStreamRecorder:
    """Persist raw Codex JSONL and full candidate states during execution."""

    def __init__(
        self,
        *,
        raw_path: Path,
        normalized_path: Path,
        snapshots_dir: Path,
        run_id: str,
        candidate_path: Path,
        secrets: tuple[str, ...] = (),
    ) -> None:
        if raw_path.exists():
            raise ValueError(f"raw event log already exists: {raw_path}")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.raw_path = raw_path
        self.snapshots_dir = snapshots_dir
        self.candidate_path = candidate_path
        self.log = EventLog(normalized_path, run_id, secrets)
        self.secrets = secrets
        self._previous_snapshot: Path | None = None
        self._snapshot("initial")

    def _snapshot(self, boundary: str) -> None:
        if not self.candidate_path.is_file():
            self.log.append(
                actor="host",
                event_type="lifecycle",
                payload_complete=False,
                data={"boundary": boundary, "error": "candidate_missing"},
            )
            return
        event_index = self.log.next_index
        snapshot = self.snapshots_dir / f"{event_index:06d}-candidate.rs"
        shutil.copyfile(self.candidate_path, snapshot)
        previous_sha = (
            sha256_file(self._previous_snapshot)
            if self._previous_snapshot is not None
            else None
        )
        current_sha = sha256_file(snapshot)
        diff_path = self.snapshots_dir / f"{event_index:06d}-candidate.diff"
        before = (
            self._previous_snapshot.read_text(errors="replace").splitlines(
                keepends=True
            )
            if self._previous_snapshot is not None
            else []
        )
        after = snapshot.read_text(errors="replace").splitlines(keepends=True)
        diff_path.write_text(
            "".join(
                difflib.unified_diff(
                    before,
                    after,
                    fromfile="previous-candidate.rs",
                    tofile="candidate.rs",
                )
            ),
            encoding="utf-8",
        )
        self.log.append(
            actor="host",
            event_type="lifecycle",
            payload_complete=True,
            candidate_sha256=current_sha,
            data={
                "boundary": boundary,
                "snapshot": str(snapshot.relative_to(self.raw_path.parent)),
                "diff": str(diff_path.relative_to(self.raw_path.parent)),
                "previous_candidate_sha256": previous_sha,
                "candidate_sha256": current_sha,
                "snapshot_size_bytes": snapshot.stat().st_size,
                "diff_size_bytes": diff_path.stat().st_size,
            },
        )
        self._previous_snapshot = snapshot

    def snapshot(self, boundary: str) -> None:
        self._snapshot(boundary)

    def append_raw_line(self, line: str, line_number: int) -> bool:
        with self.raw_path.open("a", encoding="utf-8") as raw_handle:
            raw_handle.write(line)
            if line and not line.endswith("\n"):
                raw_handle.write("\n")
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            self.log.append(
                actor="codex",
                event_type="lifecycle",
                payload_complete=False,
                candidate_sha256=_candidate_hash(self.candidate_path),
                data={
                    "codex_event_type": "malformed_json",
                    "line_number": line_number,
                    "raw_line": redact_text(line, self.secrets),
                },
            )
            return False
        if not isinstance(raw, dict):
            self.log.append(
                actor="codex",
                event_type="lifecycle",
                payload_complete=False,
                candidate_sha256=_candidate_hash(self.candidate_path),
                data={
                    "codex_event_type": "non_object_json",
                    "line_number": line_number,
                    "raw_value": raw,
                },
            )
            return False
        append_codex_event(
            raw=raw,
            log=self.log,
            candidate_path=self.candidate_path,
        )
        item = raw.get("item")
        if (
            isinstance(item, dict)
            and raw.get("type") == "item.completed"
            and item.get("type") in {"command_execution", "file_change"}
        ):
            self._snapshot(f"{item.get('type')}:{item.get('id')}")
        return True


def normalize_codex_jsonl(
    *,
    raw_path: Path,
    normalized_path: Path,
    run_id: str,
    candidate_path: Path | None = None,
    secrets: tuple[str, ...] = (),
) -> dict[str, int]:
    """Normalize an existing raw log; live snapshots require CodexStreamRecorder."""
    log = EventLog(normalized_path, run_id, secrets)
    raw_count = 0
    malformed_count = 0
    with raw_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw_count += 1
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                malformed_count += 1
                log.append(
                    actor="codex",
                    event_type="lifecycle",
                    payload_complete=False,
                    candidate_sha256=_candidate_hash(candidate_path),
                    data={
                        "codex_event_type": "malformed_json",
                        "line_number": line_number,
                        "raw_line": redact_text(line, secrets),
                    },
                )
                continue
            if not isinstance(raw, dict):
                malformed_count += 1
                log.append(
                    actor="codex",
                    event_type="lifecycle",
                    payload_complete=False,
                    candidate_sha256=_candidate_hash(candidate_path),
                    data={
                        "codex_event_type": "non_object_json",
                        "line_number": line_number,
                        "raw_value": raw,
                    },
                )
                continue
            append_codex_event(raw=raw, log=log, candidate_path=candidate_path)
    return {
        "raw_event_count": raw_count,
        "normalized_event_count": log.next_index - 1,
        "malformed_event_count": malformed_count,
    }
