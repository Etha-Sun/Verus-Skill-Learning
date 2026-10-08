"""Prepare offline, human-reviewed applicability cases; never invoke a model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from skillopt_verusage.card_bank import _index_entry
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.skill_artifact import load_skill_artifact


def prepare_review(bank_path: Path, cases_path: Path, destination: Path, *, bundle_path: Path | None = None):
    bank_bytes = bank_path.read_bytes()
    cases_bytes = cases_path.read_bytes()
    bank_hash = hashlib.sha256(bank_bytes).hexdigest()
    bank = json.loads(bank_bytes)
    fixture = json.loads(cases_bytes)
    if bank.get('schema_version') != 'stage-card-bank-v1':
        raise ValueError('unsupported card bank')
    if fixture.get('schema_version') != 'card-routing-review-cases-v1':
        raise ValueError('unsupported review cases')
    if fixture.get('bank_sha256') != bank_hash:
        raise ValueError('review cases belong to a different bank')
    cards = {card['id']: card for card in bank['cards']}
    index = [_index_entry(card) for card in bank['cards']]
    bundle_manifest = None
    if bundle_path is not None:
        if json.loads((bundle_path/'cards.json').read_text())['cards'] != bank['cards']:
            raise ValueError('review bundle does not preserve the source bank')
        index = (bundle_path/'SKILL.md').read_text().split('## Card index\n\n')[1].splitlines()
        if len(index) != len(cards) or any(
            not line.startswith(f"- {card['id']}: ") for card, line in zip(bank['cards'], index)
        ):
            raise ValueError('review bundle must expose all card IDs in source order')
        bundle_manifest = load_skill_artifact(bundle_path).manifest()
    entries = dict(zip(cards, index))
    cases = fixture.get('cases', [])
    if not cases or len({case['case_id'] for case in cases}) != len(cases):
        raise ValueError('review case IDs must be unique and nonempty')
    rows = []
    for case in cases:
        if case['card_id'] not in cards:
            raise ValueError('unknown review card ID')
        if case['expected_applicability'] not in {'applicable', 'inapplicable', 'optional'}:
            raise ValueError('invalid expected applicability')
        if any(not isinstance(case[key], str) or not case[key].strip()
               for key in ('case_id', 'state', 'rationale')):
            raise ValueError('review cases need a state and rationale')
        card = cards[case['card_id']]
        rows.append({**case, 'index_entry': entries[case['card_id']], 'card_content': card['content'],
                     'review': {'observed_applicability': None, 'read_evidence': None,
                                'premise_evidence': None, 'action_or_decline_evidence': None,
                                'proof_diff_evidence': None, 'verus_evidence': None,
                                'preservation_evidence': None, 'conclusion': None}})
    packet = {'schema_version': 'card-routing-review-packet-v1',
              'scope': 'auxiliary_development_manual_review_not_held_out_evaluation',
              'bank_sha256': bank_hash,
              'cases_sha256': hashlib.sha256(cases_bytes).hexdigest(),
              'caveat': 'Expected applicability is a review hypothesis, not a required read. '
                        'No agent retrieval or semantic correctness has been measured. '
                        'Do not expose this private answer key to a solving actor.',
              'bundle_manifest': bundle_manifest, 'index': index, 'cases': rows}
    destination = _require_run_child(destination)
    destination.mkdir(parents=True, exist_ok=False)
    (destination/'review.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n')
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, help='Review the actual deployed index, including custom descriptions')
    args = parser.parse_args()
    packet = prepare_review(args.bank, args.cases, args.output, bundle_path=args.bundle)
    print(json.dumps({'review_file': str(args.output/'review.json'),
                      'case_count': len(packet['cases']), 'model_calls': 0}))


if __name__ == '__main__':
    main()
