"""Build deployable card bundles without private evidence and audit tool exposure."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil

from skillopt_verusage import card_search
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.skill_artifact import load_skill_artifact


RETRIEVAL_INSTRUCTIONS = """
## On-demand proof repair cards

An optional card library is available in this workspace. The index below lists
every card's title and trigger. Use your current proof state to choose a card
and read it directly by ID without searching. You decide whether and when to
retrieve advice; a hint of stagnation is not a mandatory retrieval trigger.

If you want help narrowing the index, optionally search using the current proof
goal, exact diagnostic, and the action already attempted:

    python3 card_search.py search "current diagnostic and proof state"

Search is only a lexical helper and returns at most three matches; it does not
limit which indexed cards you may choose. Read a promising card by ID:

    python3 card_search.py read card-001

Use the returned ID. Check Trigger and Avoid when against the current state;
perform required prechecks before acting. Cards are fallible advice, not proof.
You may decline a card, refine the query, or continue without one. After applying
advice, use the normal verification and preservation tools. Briefly identify
the card ID and why it applies or why you decline it in your progress message.
Do not bulk-read cards.json or modify library files. Search/read is optional;
the normal task budget includes its time and context cost.
"""


AUTONOMOUS_RETRIEVAL_INSTRUCTIONS = """
## On-demand proof repair cards

An optional card library is available in this workspace. The complete index
below lists every card's title and trigger. You decide whether, when, and which
cards to read based on your current proof state; no retrieval ranking or fixed
card count is imposed. Read any indexed card by ID:

    python3 card_read.py card-001

You may read additional cards, decline their advice, or continue without them.
Check Trigger and Avoid when against the current state, perform required
prechecks, and use normal verification and preservation tools after acting.
Cards are fallible advice, not proof. Briefly identify a consulted card's ID
and why it applies or why you decline it in your progress message. Do not
bulk-read cards.json or modify library files. Reading is optional and uses the
normal task time and context budget.
"""

DIAGNOSTIC_RETRIEVAL_GUIDANCE = """
### When a card can help

Treat the index as a map, not a replacement for a card's conditions. Consider
reading a matching card before inventing an unfamiliar helper, choosing between
proof strategies, or repeating an edit after the same obligation fails again.
An unfamiliar diagnostic, uncertain lemma contract, or no clear next logical
step is also a reason to consult the index. These are decision cues, not a
mandatory stall detector or a requirement to read a fixed number of cards.

Choose by the current failed obligation, available premises, and attempted
action, not by a shared topic word alone. Read the selected card's full Trigger,
Action, Validate and Avoid when before relying on its advice. A missing
antecedent, missing trigger, and missing logical premise are different problems;
similarly, raw state predicates, lifted temporal predicates and always wrappers
are different types of argument. Check the exact current diagnostic and local
helper contract. If adjacent cards suggest different routes, inspect the
relevant alternatives rather than assuming the first match is applicable.

After reading, briefly say which condition matches (or why you decline), try
one justified proof-only change, and check its diagnostics and preservation.
Do not keep rereading the same advice when a premise is absent. Prefer a known
small repair or a confirmed local lemma without a card when that is sufficient;
no matching card is a valid outcome. A warning after verification is optional
cleanup, not a failed proof. Once both checks pass, stop unless cleanup is
worth its cost. A card read or an index mention is not itself progress.
"""

AUTONOMOUS_CARD_READER = '''"""Read an agent-selected card ID without search or ranking."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("card_id")
args = parser.parse_args()
cards = json.loads(Path(__file__).with_name("cards.json").read_text())["cards"]
card = next((c for c in cards if c["id"] == args.card_id), None)
print(json.dumps({"card_retrieval": 1, "operation": "read", "id": args.card_id,
                  **({"content": card["content"]} if card else {"error": "unknown card id"})},
                 ensure_ascii=False))
'''


def _index_entry(card, description=None):
    labels = r"\*\*(?:Trigger|Action|Why|Validate|Avoid when):\*\*"
    heading = re.split(labels, card['content'], maxsplit=1)[0].strip().lstrip('# ')
    trigger = re.split(labels, card_search.field(card['content'], 'Trigger'), maxsplit=1)[0]
    title = ' '.join(heading.split())
    description = ' '.join((trigger if description is None else description).split())
    summary = f'{title} — {description}' if title and title != description else description
    return f"- {card['id']}: {summary}"


def build_bundle(bank_path: Path, seed_path: Path, destination: Path, *, autonomous_retrieval=False,
                 index_descriptions: dict[str, str] | None = None, diagnostic_guidance=False):
    if diagnostic_guidance and not autonomous_retrieval:
        raise ValueError('diagnostic guidance requires autonomous retrieval')
    destination = _require_run_child(destination)
    bank = json.loads(bank_path.read_text())
    cards = bank.get("cards", [])
    if bank.get("schema_version") != "stage-card-bank-v1" or not cards:
        raise ValueError("empty or unsupported card bank")
    ids = [c["id"] for c in cards]
    if len(set(ids)) != len(ids) or not all(re.fullmatch(r"card-\d{3,}", x) for x in ids):
        raise ValueError("invalid card ids")
    for card in cards:
        if set(card) != {"id", "content"}:
            raise ValueError("deployable card must not expose evidence sidecars")
        card_search.validate_fields(card["content"])
    if index_descriptions is not None:
        if set(index_descriptions) != set(ids) or any(
            not isinstance(text, str) or not text.strip() or len(text.splitlines()) != 1
            for text in index_descriptions.values()
        ):
            raise ValueError('index descriptions must cover every card with nonempty single-line text')
    destination.mkdir(parents=True, exist_ok=False)
    index = "\n## Card index\n\n" + "\n".join(
        _index_entry(card, None if index_descriptions is None else index_descriptions[card['id']])
        for card in cards
    ) + "\n"
    instructions = AUTONOMOUS_RETRIEVAL_INSTRUCTIONS if autonomous_retrieval else RETRIEVAL_INSTRUCTIONS
    if index_descriptions is not None:
        instructions = instructions.replace("title and trigger", "title and routing description")
        instructions += '\nIndex descriptions are routing cues only. Read the full Trigger and Avoid when before acting.\n'
    if diagnostic_guidance:
        instructions += DIAGNOSTIC_RETRIEVAL_GUIDANCE
    (destination / "SKILL.md").write_text(seed_path.read_text().rstrip() + "\n" + instructions + index)
    deployed_bank = {"schema_version": bank["schema_version"], "cards": cards} if autonomous_retrieval else bank
    (destination / "cards.json").write_text(json.dumps(deployed_bank, ensure_ascii=False, indent=2) + "\n")
    if autonomous_retrieval:
        (destination / "card_read.py").write_text(AUTONOMOUS_CARD_READER)
    else:
        shutil.copyfile(Path(card_search.__file__), destination / "card_search.py")
    return load_skill_artifact(destination).manifest()


def audit_retrieval(raw_events: Path):
    """Count returned search/read payloads; semantic application needs manual audit."""
    rows = []
    bypass = []
    mentions = []
    if not raw_events.exists():
        return {"search_calls": 0, "read_calls": 0, "events": [], "audit_incomplete": True}
    for line in raw_events.read_text().splitlines():
        event = json.loads(line)
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            ids = re.findall(r"\bcard-\d{3,}\b", item.get("text", ""))
            if ids:
                mentions.append({"item_id": item.get("id"), "card_ids": sorted(set(ids)), "text": item["text"]})
        if item.get("type") != "command_execution":
            continue
        command = item.get("command", "")
        if "cards.json" in command:
            bypass.append({"item_id": item.get("id"), "command": command})
        for output_line in str(item.get("aggregated_output", "")).splitlines():
            try:
                payload = json.loads(output_line)
            except ValueError:
                continue
            if isinstance(payload, dict) and payload.get("card_retrieval") == 1:
                rows.append({"item_id": item.get("id"), "command": command, "exit_code": item.get("exit_code"), **payload})
    searches = [x for x in rows if x.get("operation") == "search"]
    reads = [x for x in rows if x.get("operation") == "read" and "content" in x]
    return {"search_calls": len(searches), "read_calls": len(reads),
            "read_ids": sorted({x["id"] for x in reads}),
            "empty_searches": sum(not x.get("results") for x in searches),
            "direct_bank_access_commands": bypass, "agent_card_mentions": mentions,
            "events": rows, "application_correctness": "requires manual trace audit",
            "caveat": "Visible tool payloads and self-reports measure exposure, not causal use; direct filesystem reads may bypass the helper."}
