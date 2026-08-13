from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_BYPASS_PATTERNS = (
    re.compile(r"\bassume\s*\("),
    re.compile(r"\badmit\s*\("),
    re.compile(r"external_body"),
    re.compile(r"\baxiom\b"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _curly_brace_balance(text: str) -> int:
    """Count structural Rust braces while ignoring comments and literals."""
    balance = 0
    index = 0
    block_comment_depth = 0
    length = len(text)
    while index < length:
        if block_comment_depth:
            if text.startswith("/*", index):
                block_comment_depth += 1
                index += 2
            elif text.startswith("*/", index):
                block_comment_depth -= 1
                index += 2
            else:
                index += 1
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if text.startswith("/*", index):
            block_comment_depth = 1
            index += 2
            continue

        raw = re.match(r'(?:br|cr|r)(?P<hashes>#{0,255})"', text[index:])
        if raw and (index == 0 or not (text[index - 1].isalnum() or text[index - 1] == "_")):
            delimiter = '"' + raw.group("hashes")
            end = text.find(delimiter, index + raw.end())
            index = length if end < 0 else end + len(delimiter)
            continue

        char = text[index]
        if char == '"':
            index += 1
            while index < length:
                if text[index] == "\\":
                    index += 2
                elif text[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            continue
        if char == "'":
            end = index + 1
            escaped = False
            while end < length and text[end] != "\n":
                if not escaped and text[end] == "'":
                    break
                if not escaped and text[end] == "\\":
                    escaped = True
                else:
                    escaped = False
                end += 1
            if end < length and text[end] == "'":
                index = end + 1
                continue
        if char == "{":
            balance += 1
        elif char == "}":
            balance -= 1
        index += 1
    return balance


def _assert_preserves_curly_balance(before: str, after: str, operation: str) -> None:
    before_balance = _curly_brace_balance(before)
    after_balance = _curly_brace_balance(after)
    if after_balance != before_balance:
        raise ValueError(
            f"{operation} rejected: structural curly-brace balance would change "
            f"from {before_balance} to {after_balance}; candidate.rs was not modified. "
            "Read at least one line beyond both edit boundaries and include each "
            "existing opening or closing brace exactly once."
        )


def prepare_workspace(source: Path, work_dir: Path, task: str = "") -> "VerusWorkspace":
    source = source.resolve()
    work_dir = work_dir.resolve()
    if not source.is_file():
        raise ValueError(f"input source does not exist: {source}")
    if source.suffix != ".rs":
        raise ValueError(f"input source must be a .rs file: {source}")
    if work_dir.exists() and any(work_dir.iterdir()):
        raise ValueError(f"workspace must be absent or empty: {work_dir}")
    work_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, work_dir / "input.rs")
    shutil.copy2(source, work_dir / "candidate.rs")
    (work_dir / "TASK.md").write_text(task, encoding="utf-8")
    return VerusWorkspace(root=work_dir, source_path=source)


@dataclass
class VerusWorkspace:
    root: Path
    source_path: Path
    verus_bin: Path | None = None
    lynette_bin: Path | None = None
    timeout_seconds: int = 120
    initial_source_sha256: str = field(init=False)
    input_sha256: str = field(init=False)
    last_verus: dict[str, Any] | None = field(default=None, init=False)
    last_lynette: dict[str, Any] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.root = self.root.resolve()
        self.source_path = self.source_path.resolve()
        self.initial_source_sha256 = sha256_file(self.source_path)
        self.input_sha256 = sha256_file(self.input_path)
        if self.verus_bin is not None:
            self.verus_bin = self._require_executable(self.verus_bin, "Verus")
        if self.lynette_bin is not None:
            self.lynette_bin = self._require_executable(self.lynette_bin, "Lynette")

    @property
    def input_path(self) -> Path:
        return self.root / "input.rs"

    @property
    def candidate_path(self) -> Path:
        return self.root / "candidate.rs"

    @property
    def audit_path(self) -> Path:
        return self.root / "tool_audit.jsonl"

    @staticmethod
    def _require_executable(path: Path, label: str) -> Path:
        resolved = path.resolve()
        if not resolved.is_file() or not os.access(resolved, os.X_OK):
            raise ValueError(f"{label} executable is invalid: {resolved}")
        return resolved

    def _assert_source_unchanged(self) -> None:
        if sha256_file(self.source_path) != self.initial_source_sha256:
            raise RuntimeError("source trajectory changed during the run")
        if sha256_file(self.input_path) != self.input_sha256:
            raise RuntimeError("immutable input.rs changed during the run")

    def _audit(self, operation: str, payload: dict[str, Any]) -> None:
        self._assert_source_unchanged()
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "candidate_sha256": sha256_file(self.candidate_path),
            **payload,
        }
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_file(self, path: str, line_start: int = 1, line_end: int = 400) -> str:
        allowlist = {"input.rs", "candidate.rs", "TASK.md"}
        if path not in allowlist:
            raise ValueError(f"path is not allowlisted: {path}")
        if line_start < 1 or line_end < line_start or line_end - line_start > 999:
            raise ValueError("request a valid range of at most 1000 lines")
        lines = (self.root / path).read_text(encoding="utf-8").splitlines()
        selected = lines[line_start - 1 : line_end]
        self._audit(
            "read_file",
            {"path": path, "line_start": line_start, "line_end": min(line_end, len(lines))},
        )
        return "\n".join(
            f"{index:06d}: {line}"
            for index, line in enumerate(selected, start=line_start)
        )

    @staticmethod
    def _validate_edit_lines(lines: list, label: str) -> list[str]:
        if not isinstance(lines, list) or any(not isinstance(line, str) for line in lines):
            raise ValueError(f"{label} must be a JSON array of strings")
        if len(lines) > 300:
            raise ValueError(f"{label} may contain at most 300 lines")
        if any("\n" in line or "\r" in line for line in lines):
            raise ValueError(
                f"each {label} item must be one physical line without newline characters"
            )
        if sum(len(line) for line in lines) > 30000:
            raise ValueError(f"{label} may contain at most 30000 characters")
        return lines

    def replace_text(self, old_text: str, new_text: str) -> str:
        if not old_text:
            raise ValueError("old_text must not be empty")
        if any(char in old_text or char in new_text for char in ("\n", "\r")):
            raise ValueError(
                "replace_text is single-line only; use edit_lines with a JSON array "
                "containing one string per physical line"
            )
        for pattern in _BYPASS_PATTERNS:
            if pattern.search(new_text) and not pattern.search(old_text):
                raise ValueError(f"forbidden verification bypass: {pattern.pattern}")
        before = self.candidate_path.read_text(encoding="utf-8")
        if before.count(old_text) != 1:
            raise ValueError("old_text must occur exactly once in candidate.rs")
        after = before.replace(old_text, new_text, 1)
        _assert_preserves_curly_balance(before, after, "replace_text")
        self.candidate_path.write_text(after, encoding="utf-8")
        self.last_verus = None
        self.last_lynette = None
        self._audit(
            "replace_text",
            {
                "old_text_sha256": hashlib.sha256(old_text.encode()).hexdigest(),
                "new_text_sha256": hashlib.sha256(new_text.encode()).hexdigest(),
            },
        )
        return "candidate.rs updated; run Verus on the new candidate next."

    def edit_lines(
        self, line_start: int, line_end: int, replacement_lines: list
    ) -> str:
        replacement = self._validate_edit_lines(replacement_lines, "replacement_lines")
        before = self.candidate_path.read_text(encoding="utf-8")
        lines = before.splitlines()
        if (
            line_start < 1
            or line_end < line_start
            or line_end > len(lines)
            or line_end - line_start + 1 > 200
        ):
            raise ValueError(
                "edit_lines requires a current inclusive range of at most 200 lines"
            )
        old_lines = lines[line_start - 1 : line_end]
        old_text = "\n".join(old_lines)
        new_text = "\n".join(replacement)
        for pattern in _BYPASS_PATTERNS:
            if pattern.search(new_text) and not pattern.search(old_text):
                raise ValueError(f"forbidden verification bypass: {pattern.pattern}")
        updated_lines = lines[: line_start - 1] + replacement + lines[line_end:]
        after = "\n".join(updated_lines)
        if before.endswith("\n"):
            after += "\n"
        _assert_preserves_curly_balance(before, after, "edit_lines")
        self.candidate_path.write_text(after, encoding="utf-8")
        self.last_verus = None
        self.last_lynette = None
        self._audit(
            "edit_lines",
            {
                "line_start": line_start,
                "line_end": line_end,
                "removed_line_count": len(old_lines),
                "inserted_line_count": len(replacement),
                "old_lines_sha256": hashlib.sha256(old_text.encode()).hexdigest(),
                "new_lines_sha256": hashlib.sha256(new_text.encode()).hexdigest(),
            },
        )
        return (
            f"candidate.rs lines {line_start}-{line_end} replaced with "
            f"{len(replacement)} line(s); run Verus next."
        )

    def insert_lines(self, after_line: int, new_lines: list) -> str:
        insertion = self._validate_edit_lines(new_lines, "new_lines")
        if not insertion:
            raise ValueError("new_lines must not be empty")
        before = self.candidate_path.read_text(encoding="utf-8")
        lines = before.splitlines()
        if after_line < 0 or after_line > len(lines):
            raise ValueError(
                "insert_lines after_line must be between 0 and the current line count"
            )
        new_text = "\n".join(insertion)
        for pattern in _BYPASS_PATTERNS:
            if pattern.search(new_text):
                raise ValueError(f"forbidden verification bypass: {pattern.pattern}")
        updated_lines = lines[:after_line] + insertion + lines[after_line:]
        after = "\n".join(updated_lines)
        if before.endswith("\n"):
            after += "\n"
        _assert_preserves_curly_balance(before, after, "insert_lines")
        self.candidate_path.write_text(after, encoding="utf-8")
        self.last_verus = None
        self.last_lynette = None
        self._audit(
            "insert_lines",
            {
                "after_line": after_line,
                "inserted_line_count": len(insertion),
                "new_lines_sha256": hashlib.sha256(new_text.encode()).hexdigest(),
            },
        )
        return (
            f"{len(insertion)} line(s) inserted after candidate.rs line {after_line}; "
            "run Verus next."
        )

    def _run(self, command: list[str]) -> dict[str, Any]:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            return {
                "returncode": completed.returncode,
                "timed_out": False,
                "wall_seconds": round(time.monotonic() - started, 6),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        except subprocess.TimeoutExpired as error:
            return {
                "returncode": None,
                "timed_out": True,
                "wall_seconds": round(time.monotonic() - started, 6),
                "stdout": error.stdout or "",
                "stderr": error.stderr or "",
            }

    def run_verus(self) -> str:
        if self.verus_bin is None:
            raise ValueError("Verus executable is not configured")
        result = self._run([str(self.verus_bin), "candidate.rs"])
        text = str(result["stdout"]) + str(result["stderr"])
        result["passed"] = (
            result["returncode"] == 0
            and not result["timed_out"]
            and "error: aborting" not in text.lower()
        )
        result["candidate_sha256"] = sha256_file(self.candidate_path)
        self.last_verus = result
        self._audit("run_verus", {"passed": result["passed"], "returncode": result["returncode"]})
        return text or json.dumps(result, ensure_ascii=False)

    def run_lynette(self) -> str:
        if self.lynette_bin is None:
            raise ValueError("Lynette executable is not configured")
        result = self._run(
            [str(self.lynette_bin), "compare", "-t", "input.rs", "candidate.rs"]
        )
        result["passed"] = result["returncode"] == 0 and not result["timed_out"]
        result["candidate_sha256"] = sha256_file(self.candidate_path)
        self.last_lynette = result
        self._audit("run_lynette", {"passed": result["passed"], "returncode": result["returncode"]})
        return str(result["stdout"]) + str(result["stderr"]) or json.dumps(result)

    def validation_status(self) -> dict[str, Any]:
        current_sha = sha256_file(self.candidate_path)
        verus_ok = bool(
            self.last_verus
            and self.last_verus.get("passed")
            and self.last_verus.get("candidate_sha256") == current_sha
        )
        lynette_ok = bool(
            self.last_lynette
            and self.last_lynette.get("passed")
            and self.last_lynette.get("candidate_sha256") == current_sha
        )
        self._assert_source_unchanged()
        return {
            "candidate_sha256": current_sha,
            "verus_passed": verus_ok,
            "lynette_passed": lynette_ok,
            "source_unchanged": True,
            "complete": verus_ok and lynette_ok,
        }
