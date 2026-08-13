from __future__ import annotations

import json
import re
from pathlib import Path

from react_agent import Tool, tool

from .search import search_workspace_file
from .workspace import VerusWorkspace


class SkillReferenceReader:
    """Read one-level references from a single Trace2Skill skill directory."""

    _CARD_HEADING = re.compile(
        r'^<a id="(verus-global-\d{3})"></a>\n\n'
        r'## (verus_global_\d{3}) — ',
        re.MULTILINE,
    )
    _CARD_PAGE_CHARS = 5000

    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir.resolve()
        self.references_dir = (self.skill_dir / "references").resolve()
        self.allowed = {
            path.name: path.resolve()
            for path in self.references_dir.glob("*.md")
            if path.is_file()
        }
        self.read_history: list[str] = []
        self._loaded: set[tuple[str, str | None, int | None]] = set()

    def _normalize_reference(self, reference: str) -> str:
        normalized = reference
        if normalized.startswith("references/"):
            normalized = normalized[len("references/") :]
        if "/" in normalized or "\\" in normalized or normalized not in self.allowed:
            raise ValueError(
                f"unknown reference {reference!r}; available: {sorted(self.allowed)}"
            )
        return normalized

    def _card_sections(self, normalized: str) -> dict[str, str]:
        text = self.allowed[normalized].read_text(encoding="utf-8")
        matches = list(self._CARD_HEADING.finditer(text))
        sections: dict[str, str] = {}
        for index, match in enumerate(matches):
            anchor, card_id = match.groups()
            if anchor.replace("-", "_") != card_id:
                continue
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections[card_id] = text[match.start() : end].rstrip() + "\n"
        return sections

    @staticmethod
    def _already_loaded_message(
        normalized: str,
        card_id: str | None,
        page: int | None,
        available_cards: list[str],
    ) -> str:
        target = (
            f" card {card_id} page {page}"
            if card_id
            else " in full-file mode"
        )
        card_hint = (
            " To inspect a card that was hidden by observation truncation, call "
            "read_skill_reference with the same reference and one of these card_id "
            f"values: {available_cards}."
            if not card_id and available_cards
            else ""
        )
        return (
            f"Reference {normalized!r}{target} was already loaded in this run; "
            "the content is already present in the conversation and will not be "
            f"returned again.{card_hint}"
        )

    def read(self, reference: str, card_id: str = "", page: int = 1) -> str:
        normalized = self._normalize_reference(reference)
        sections = self._card_sections(normalized)
        requested_card = card_id.strip() or None

        if page < 1:
            raise ValueError("page must be at least 1")
        if requested_card is None and page != 1:
            raise ValueError("page is only valid when card_id is supplied")
        if requested_card is not None and requested_card not in sections:
            raise ValueError(
                f"unknown card_id {requested_card!r} for reference {normalized!r}; "
                f"available: {sorted(sections)}"
            )

        if requested_card is not None:
            content = sections[requested_card]
            total_pages = max(
                1, (len(content) + self._CARD_PAGE_CHARS - 1) // self._CARD_PAGE_CHARS
            )
            if page > total_pages:
                raise ValueError(
                    f"page {page} is out of range for {requested_card}; "
                    f"available pages: 1-{total_pages}"
                )
            key = (normalized, requested_card, page)
        else:
            content = self.allowed[normalized].read_text(encoding="utf-8")
            total_pages = 1
            key = (normalized, None, None)

        if key in self._loaded:
            return self._already_loaded_message(
                normalized, requested_card, page if requested_card else None, sorted(sections)
            )

        # Once any content from a reference has been loaded, do not inject the
        # entire multi-card file later. Specific, not-yet-loaded cards remain
        # available so skill navigation can adapt to a new verifier obstruction.
        if requested_card is None and any(
            name == normalized for name, _, _ in self._loaded
        ):
            return self._already_loaded_message(
                normalized, None, None, sorted(sections)
            )

        self._loaded.add(key)
        if requested_card is None:
            history_entry = normalized
        elif total_pages == 1:
            history_entry = f"{normalized}#{requested_card}"
        else:
            history_entry = f"{normalized}#{requested_card}@page={page}"
        self.read_history.append(history_entry)

        if requested_card is None or total_pages == 1:
            return content

        start = (page - 1) * self._CARD_PAGE_CHARS
        chunk = content[start : start + self._CARD_PAGE_CHARS]
        next_hint = (
            f" Call read_skill_reference again with page={page + 1}."
            if page < total_pages
            else " This is the final page."
        )
        return (
            f"[CARD PAGE {page}/{total_pages}: {normalized}#{requested_card}]\n"
            f"{chunk}\n"
            f"[END CARD PAGE {page}/{total_pages}].{next_hint}"
        )


def create_workspace_tools(workspace: VerusWorkspace) -> list[Tool]:
    @tool(name="read_file", description="Read an allowlisted line range from input.rs, candidate.rs, or TASK.md.")
    def read_file(path: str, line_start: int = 1, line_end: int = 400) -> str:
        return workspace.read_file(path, line_start, line_end)

    @tool(
        name="search_file",
        description=(
            "Search literal text in input.rs, candidate.rs, or TASK.md and return "
            "bounded line-numbered matches with context. context_lines must be between "
            "0 and 5. Use this before broad reads."
        ),
    )
    def search_file(
        query: str,
        path: str = "candidate.rs",
        max_results: int = 20,
        context_lines: int = 2,
        case_sensitive: bool = True,
    ) -> str:
        return search_workspace_file(
            workspace=workspace,
            query=query,
            path=path,
            max_results=max_results,
            context_lines=context_lines,
            case_sensitive=case_sensitive,
        )

    @tool(
        name="edit_lines",
        description=(
            "Replace an inclusive current line range in candidate.rs. "
            "replacement_lines MUST be a JSON array with one string per physical "
            "code line; never put literal newlines inside one JSON string. Use [] "
            "to delete the range. Edits that unbalance structural curly braces are "
            "rejected before candidate.rs is modified; read beyond both range boundaries."
        ),
    )
    def edit_lines(
        line_start: int, line_end: int, replacement_lines: list
    ) -> str:
        return workspace.edit_lines(line_start, line_end, replacement_lines)

    @tool(
        name="insert_lines",
        description=(
            "Insert code after a current candidate.rs line (0 means before line 1). "
            "new_lines MUST be a JSON array with one string per physical code line; "
            "never put literal newlines inside one JSON string."
        ),
    )
    def insert_lines(after_line: int, new_lines: list) -> str:
        return workspace.insert_lines(after_line, new_lines)

    @tool(name="replace_text", description="Replace one exact single-line string in candidate.rs. For every multiline change use edit_lines or insert_lines instead.")
    def replace_text(old_text: str, new_text: str) -> str:
        return workspace.replace_text(old_text, new_text)

    @tool(name="run_verus", description="Run the configured Verus executable on the current candidate.rs.")
    def run_verus() -> str:
        return workspace.run_verus()

    @tool(name="run_lynette", description="Check that candidate.rs contains proof-only changes relative to immutable input.rs.")
    def run_lynette() -> str:
        return workspace.run_lynette()

    return [
        read_file,
        search_file,
        edit_lines,
        insert_lines,
        replace_text,
        run_verus,
        run_lynette,
    ]


def create_reference_tool(reader: SkillReferenceReader) -> Tool:
    @tool(
        name="read_skill_reference",
        description=(
            "Open a reference resource linked by the preloaded root SKILL.md. "
            "Accept either references/name.md or name.md. When a multi-card resource "
            "contains the needed verus_global_NNN entry, pass that ID as card_id to "
            "return the relevant section without observation truncation. If the returned "
            "section has multiple pages, request its remaining pages. Resources may be "
            "opened on demand in the same conversation; duplicate page reads return only "
            "a short already-loaded notice."
        ),
    )
    def read_skill_reference(
        reference: str, card_id: str = "", page: int = 1
    ) -> str:
        return reader.read(reference, card_id, page)

    return read_skill_reference


def json_result(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)
