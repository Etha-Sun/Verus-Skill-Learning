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

An optional card library is available in this workspace. When a diagnostic is
unfamiliar, attempts repeat without progress, or you are considering rewriting
a proof that already verifies, search using the current proof goal, exact
diagnostic, and the action already attempted:

    python3 card_search.py search "current diagnostic and proof state"

Search returns at most three titles and trigger conditions. Read one promising
card at a time:

    python3 card_search.py read card-001

Use the returned ID. Check Trigger and Avoid when against the current state;
perform required prechecks before acting. Cards are fallible advice, not proof.
You may decline a card, refine the query, or continue without one. After applying
advice, use the normal verification and preservation tools. Briefly identify
the card ID and why it applies or why you decline it in your progress message.
Do not bulk-read cards.json or modify library files. Search/read is optional;
the normal task budget includes its time and context cost.
"""


def build_bundle(bank_path: Path, seed_path: Path, destination: Path):
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
        for label in ("Trigger", "Action", "Why", "Validate", "Avoid when"):
            if not card_search.field(card["content"], label):
                raise ValueError(f"card missing {label}")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "SKILL.md").write_text(seed_path.read_text().rstrip() + "\n" + RETRIEVAL_INSTRUCTIONS)
    (destination / "cards.json").write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n")
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
