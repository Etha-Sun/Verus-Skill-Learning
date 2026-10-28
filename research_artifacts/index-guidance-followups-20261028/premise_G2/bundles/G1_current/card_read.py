"""Read an agent-selected card ID without search or ranking."""
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
