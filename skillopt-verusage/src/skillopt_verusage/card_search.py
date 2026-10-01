"""Dependency-free search/read interface copied into frozen actor skill bundles."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re


STOP_WORDS = set("a an the is are to of in on and or for with by from as at it this that be when then only".split())


def terms(text):
    return [w for w in re.findall(r"[a-z][a-z0-9_]*", text.lower()) if w not in STOP_WORDS]


def field(content, label):
    match = re.search(r"\*\*" + re.escape(label) + r":\*\*\s*(.*?)(?=\n\*\*|\Z)", content, re.S)
    return match.group(1).strip() if match else ""


def search(cards, query, limit=3):
    """Rank lexical matches; expose only titles/triggers until explicitly read."""
    query_terms = set(terms(query))
    docs = [Counter(terms(c["content"])) for c in cards]
    results = []
    for card, counts in zip(cards, docs):
        title = card["content"].splitlines()[0].lstrip("# ")
        trigger = field(card["content"], "Trigger")
        salient = set(terms(title + " " + trigger))
        score = sum((1 + math.log(counts[w])) * math.log(1 + len(cards) / (1 + sum(w in d for d in docs)))
                    * (2 if w in salient else 1) for w in query_terms if counts[w])
        if score > 0:
            results.append({"id": card["id"], "title": title, "trigger": trigger, "score": round(score, 6)})
    return sorted(results, key=lambda x: (-x["score"], x["id"]))[:limit]


def respond(bank, operation, value):
    cards = bank["cards"]
    if operation == "search":
        return {"card_retrieval": 1, "operation": "search", "query": value, "results": search(cards, value)}
    card = next((c for c in cards if c["id"] == value), None)
    return {"card_retrieval": 1, "operation": "read", "id": value,
            **({"content": card["content"]} if card else {"error": "unknown card id"})}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("search", "read"))
    parser.add_argument("value")
    args = parser.parse_args()
    bank = json.loads(Path(__file__).with_name("cards.json").read_text())
    print(json.dumps(respond(bank, args.operation, args.value), ensure_ascii=False))


if __name__ == "__main__":
    main()
