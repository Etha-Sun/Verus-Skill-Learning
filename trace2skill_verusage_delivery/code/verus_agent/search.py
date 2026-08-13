from __future__ import annotations

import hashlib

from .workspace import VerusWorkspace


def search_workspace_file(
    workspace: VerusWorkspace,
    query: str,
    path: str = "candidate.rs",
    max_results: int = 20,
    context_lines: int = 2,
    case_sensitive: bool = True,
) -> str:
    """Search literal text in an allowlisted workspace file without shell access."""
    allowlist = {"input.rs", "candidate.rs", "TASK.md"}
    if path not in allowlist:
        raise ValueError(f"path is not allowlisted: {path}")
    if not query or len(query) > 200:
        raise ValueError("query must contain between 1 and 200 characters")
    if not 1 <= max_results <= 50:
        raise ValueError("max_results must be between 1 and 50")
    if not 0 <= context_lines <= 5:
        raise ValueError("context_lines must be between 0 and 5")

    lines = (workspace.root / path).read_text(encoding="utf-8").splitlines()
    needle = query if case_sensitive else query.casefold()
    matched_lines: list[int] = []
    for index, line in enumerate(lines):
        haystack = line if case_sensitive else line.casefold()
        if needle in haystack:
            matched_lines.append(index)
            if len(matched_lines) >= max_results:
                break

    blocks: list[str] = []
    for result_number, matched_index in enumerate(matched_lines, start=1):
        start = max(0, matched_index - context_lines)
        end = min(len(lines), matched_index + context_lines + 1)
        rendered = []
        for line_index in range(start, end):
            marker = ">" if line_index == matched_index else " "
            rendered.append(f"{marker}{line_index + 1:06d}: {lines[line_index]}")
        blocks.append(
            f"Match {result_number} at line {matched_index + 1}:\n"
            + "\n".join(rendered)
        )

    workspace._audit(
        "search_file",
        {
            "path": path,
            "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "case_sensitive": case_sensitive,
            "context_lines": context_lines,
            "max_results": max_results,
            "match_count_returned": len(matched_lines),
        },
    )
    header = (
        f"Literal search in {path}: {len(matched_lines)} result(s) returned"
        + (f" (limited to {max_results})" if len(matched_lines) == max_results else "")
    )
    return header + ("\n\n" + "\n\n".join(blocks) if blocks else "")
