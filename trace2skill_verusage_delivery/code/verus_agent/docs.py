from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from react_agent import Tool, tool


_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|==>|<==>|&&|\|\||<=|>=")
_SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*$")


def _tokens(text: str) -> Counter[str]:
    result: Counter[str] = Counter()
    for token in _TOKEN_RE.findall(text.lower()):
        result[token] += 1
        for part in token.split("_"):
            if part != token:
                result[part] += 1
    return result


class VerusDocumentation:
    """Offline-only search over a local guide snapshot and installed vstd."""

    def __init__(self, guide_snapshot: Path, vstd_root: Path) -> None:
        self.guide_snapshot = guide_snapshot.resolve()
        self.vstd_root = vstd_root.resolve()
        if not self.guide_snapshot.is_file():
            raise ValueError(f"guide snapshot does not exist: {self.guide_snapshot}")
        if not self.vstd_root.is_dir():
            raise ValueError(f"vstd root does not exist: {self.vstd_root}")
        payload = json.loads(self.guide_snapshot.read_text(encoding="utf-8"))
        documents = payload.get("documents")
        if not isinstance(documents, list):
            raise ValueError("guide snapshot must contain a documents array")
        self.documents = [document for document in documents if isinstance(document, dict)]
        self.vstd_files = tuple(sorted(self.vstd_root.rglob("*.rs")))

    def search(self, query: str, top_k: int = 3) -> dict:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= top_k <= 5:
            raise ValueError("top_k must be between 1 and 5")
        query_terms = _tokens(query)
        scored = []
        for index, document in enumerate(self.documents):
            text = " ".join(
                str(document.get(field, ""))
                for field in ("title", "breadcrumbs", "body")
            )
            terms = _tokens(text)
            score = sum(min(count, terms.get(term, 0)) for term, count in query_terms.items())
            if score:
                scored.append((score, index))
        scored.sort(key=lambda item: (-item[0], item[1]))
        results = []
        for score, index in scored[:top_k]:
            document = self.documents[index]
            body = str(document.get("body", ""))
            results.append(
                {
                    "title": document.get("title", ""),
                    "url": document.get("url", ""),
                    "score": score,
                    "excerpt": body[:1600],
                }
            )
        return {"network_access": False, "query": query, "results": results}

    def lookup(self, symbol: str, max_results: int = 3) -> dict:
        symbol = symbol.strip()
        if not _SYMBOL_RE.fullmatch(symbol):
            raise ValueError("symbol must be an identifier or ::-qualified identifier")
        if not 1 <= max_results <= 5:
            raise ValueError("max_results must be between 1 and 5")
        leaf = symbol.rsplit("::", 1)[-1]
        pattern = re.compile(rf"\b{re.escape(leaf)}\b")
        matches = []
        for path in self.vstd_files:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for index, line in enumerate(lines):
                if not pattern.search(line):
                    continue
                start = max(0, index - 3)
                end = min(len(lines), index + 8)
                matches.append(
                    {
                        "path": str(path.relative_to(self.vstd_root)),
                        "matched_line": index + 1,
                        "snippet": "\n".join(
                            f"{number + 1:06d}: {lines[number]}"
                            for number in range(start, end)
                        ),
                    }
                )
                if len(matches) >= max_results:
                    return {"network_access": False, "symbol": symbol, "matches": matches}
        return {"network_access": False, "symbol": symbol, "matches": matches}

    @staticmethod
    def classify(diagnostic: str) -> dict:
        lowered = diagnostic.lower()
        routes = (
            ("syntax_or_parse", ("unexpected token", "expected one of", "delimiter"), "search_verus_docs"),
            ("name_or_vstd_api", ("cannot find", "unresolved import", "no method named", "failed to resolve"), "lookup_vstd_symbol"),
            ("mode_or_type", ("mismatched types", "spec mode", "proof mode", "exec mode", "borrow", "moved value"), "search_verus_docs"),
            ("quantifier_or_trigger", ("trigger", "quantifier", "forall", "exists"), "search_verus_docs"),
            ("termination", ("decreases", "termination", "recursive"), "search_verus_docs"),
        )
        for category, needles, next_tool in routes:
            if any(needle in lowered for needle in needles):
                return {"category": category, "recommended_tool": next_tool}
        return {
            "category": "proof_obligation",
            "recommended_tool": "read_file",
            "guidance": (
                "Apply the preloaded root SKILL.md workflow first; consult one reference "
                "only for a matching lower-frequency obstacle."
            ),
        }

    def create_tools(self) -> list[Tool]:
        @tool(name="explain_verus_diagnostic", description="Classify a Verus diagnostic as syntax/API grounding or proof reasoning.")
        def explain_verus_diagnostic(diagnostic: str) -> str:
            return json.dumps(self.classify(diagnostic), ensure_ascii=False)

        @tool(name="search_verus_docs", description="Search the local official Verus guide snapshot; this never uses the network.")
        def search_verus_docs(query: str, top_k: int = 3) -> str:
            return json.dumps(self.search(query, top_k), ensure_ascii=False, indent=2)

        @tool(name="lookup_vstd_symbol", description="Look up a symbol in the locally installed vstd source before inventing an API.")
        def lookup_vstd_symbol(symbol: str, max_results: int = 3) -> str:
            return json.dumps(self.lookup(symbol, max_results), ensure_ascii=False, indent=2)

        return [explain_verus_diagnostic, search_verus_docs, lookup_vstd_symbol]
