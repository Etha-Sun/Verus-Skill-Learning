from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FORBIDDEN_CARD_PATTERNS = (
    re.compile(r"\bassume\b", flags=re.IGNORECASE),
    re.compile(r"\badmit\b", flags=re.IGNORECASE),
    re.compile(r"external_body", flags=re.IGNORECASE),
    re.compile(r"assert\s*\(", flags=re.IGNORECASE),
    re.compile(r"forall\s*\|", flags=re.IGNORECASE),
)


def load_retrieval_cards(path: Path) -> dict[str, Any]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    cards = list(config.get("cards") or [])
    max_cards = int(config.get("max_cards", 0) or 0)
    threshold = int(config.get("abstain_threshold", 0) or 0)
    if max_cards != 12 or len(cards) > max_cards:
        raise ValueError("retrieval card count exceeds the frozen limit")
    if threshold != 2:
        raise ValueError("retrieval abstention threshold must be 2")
    ids = [str(card.get("id") or "") for card in cards]
    if not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("retrieval card ids must be non-empty and unique")
    return config


def retrieve_card(
    config: dict[str, Any],
    messages: list[dict[str, Any]],
    project: str,
) -> dict[str, Any] | None:
    text = "\n".join(str(message.get("content") or "") for message in messages).lower()
    candidates: list[tuple[int, str, dict[str, Any], list[str]]] = []
    for card in config.get("cards") or []:
        if card.get("project") not in {"any", project}:
            continue
        matches = sorted(
            {
                str(trigger).lower()
                for trigger in card.get("triggers") or []
                if str(trigger).strip() and str(trigger).lower() in text
            }
        )
        candidates.append((len(matches), str(card["id"]), card, matches))
    if not candidates:
        return None
    score, _, card, matches = max(candidates, key=lambda row: (row[0], row[1]))
    if score < int(config["abstain_threshold"]):
        return None
    return {"card": card, "score": score, "matched_triggers": matches}


def render_retrieved_card(retrieval: dict[str, Any]) -> str:
    card = retrieval["card"]
    return (
        f"# Retrieved VeruSAGE Card: {card['id']}\n\n"
        f"Positive scope: {card['positive_scope']}\n\n"
        f"Negative scope: {card['negative_scope']}\n\n"
        f"Guidance: {card['guidance']}"
    )


def filter_retrieval_cards(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for card in config.get("cards") or []:
        text = "\n".join(
            str(card.get(key) or "")
            for key in ("positive_scope", "negative_scope", "guidance")
        )
        reasons = [
            pattern.pattern for pattern in FORBIDDEN_CARD_PATTERNS if pattern.search(text)
        ]
        if reasons:
            rejected.append({"id": str(card.get("id") or ""), "reasons": reasons})
        else:
            accepted.append(card)
    filtered = dict(config)
    filtered["cards"] = accepted
    audit = {
        "passed": bool(accepted),
        "input_cards": len(config.get("cards") or []),
        "accepted_cards": len(accepted),
        "rejected_cards": rejected,
    }
    return filtered, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    config = load_retrieval_cards(args.input)
    filtered, audit = filter_retrieval_cards(config)
    if not audit["passed"]:
        raise RuntimeError("all retrieval cards failed the host safety filter")
    args.output.write_text(
        json.dumps(filtered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.audit.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
