"""Materialize a hash-bound, reviewed card revision without changing its source."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from skillopt_verusage.card_bank import build_bundle
from skillopt_verusage.card_search import FIELD_LABEL, FIELDS, field, validate_fields
from skillopt_verusage.fork_card_optimize import _require_run_child


def revise_bank(bank_path: Path, revision_path: Path, seed_path: Path, output: Path):
    source = bank_path.read_bytes()
    revision_bytes = revision_path.read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    bank = json.loads(source)
    recipe = json.loads(revision_bytes)
    if (recipe.get('schema_version') != 'reviewed-card-revision-v1'
            or recipe.get('source_bank_sha256') != source_hash):
        raise ValueError('revision does not bind this source bank')
    ids = [c['id'] for c in bank['cards']]
    updates = recipe.get('field_updates', {})
    descriptions = recipe.get('index_descriptions', {})
    if not set(updates) <= set(ids) or set(descriptions) != set(ids):
        raise ValueError('revision updates/descriptions must match source IDs')
    revised = []
    changes = []
    for card in bank['cards']:
        validate_fields(card['content'])
        content = card['content']
        changes_for_card = updates.get(card['id'], {})
        if not set(changes_for_card) <= set(FIELDS) or any(
                not isinstance(text, str) or not text.strip() or re.search(FIELD_LABEL, text)
                for text in changes_for_card.values()):
            raise ValueError('invalid revised field')
        if changes_for_card:
            heading = re.split(FIELD_LABEL, content, maxsplit=1)[0].strip()
            content = (heading+'\n' if heading else '')+'\n'.join(
                f'**{label}:** {changes_for_card.get(label, field(card["content"], label))}'
                for label in FIELDS)
            changes.append({'id':card['id'], 'changed_fields':list(changes_for_card),
                'source_content_sha256':hashlib.sha256(card['content'].encode()).hexdigest(),
                'revised_content_sha256':hashlib.sha256(content.encode()).hexdigest()})
        validate_fields(content)
        revised.append({'id':card['id'], 'content':content})
    output = _require_run_child(output)
    output.mkdir(parents=True, exist_ok=False)
    bank_output = output/'cards.json'
    bank_output.write_text(json.dumps({'schema_version':'stage-card-bank-v1','cards':revised},
                                     ensure_ascii=False, indent=2)+'\n')
    manifest = build_bundle(bank_output, seed_path, output/'bundle', autonomous_retrieval=True,
                            index_descriptions=descriptions)
    provenance = bank_path.parent/'provenance.json'
    receipt = {'schema_version':'reviewed-card-revision-receipt-v1',
        'source_bank_sha256':source_hash,
        'revision_sha256':hashlib.sha256(revision_bytes).hexdigest(),
        'revised_bank_sha256':hashlib.sha256(bank_output.read_bytes()).hexdigest(),
        'source_provenance_sha256':hashlib.sha256(provenance.read_bytes()).hexdigest() if provenance.exists() else None,
        'provenance_policy':'Original evidence refs remain immutable in source sidecar; this is manual correction, not new training evidence.',
        'card_count':len(revised), 'ids_and_order_preserved':[c['id'] for c in revised] == ids,
        'changes':changes, 'bundle_manifest':manifest,
        'claim':'Engineering revision; no measured utility or causal gain.'}
    (output/'revision.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    if bank_path.read_bytes() != source or revision_path.read_bytes() != revision_bytes:
        raise ValueError('Source changed during revision')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--revision', type=Path, required=True)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    receipt = revise_bank(args.bank, args.revision, args.seed, args.output)
    print(json.dumps({'cards':receipt['card_count'], 'changed':len(receipt['changes']),
                      'revision':str(args.output/'revision.json')}))


if __name__ == '__main__':
    main()
