"""Adopt a saved router with audited format-only normalization; no API calls."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import build_card_organization as builder
from skillopt_verusage import card_organization as organization
from skillopt_verusage.guarded_deepseek import write_json


def normalize(proposal):
    value = copy.deepcopy(proposal)
    changes = []
    for field in ('card_features', 'assignments'):
        rows = value[field]
        if isinstance(rows, dict):
            organization.require(all(isinstance(row, dict) and ident == row.get('card_id')
                                     for ident, row in rows.items()), 'Object key/card_id mismatch')
            value[field] = list(rows.values())
            changes.append({'path': field, 'operation': 'keyed_object_to_array', 'keys': list(rows)})
    names = {field.lower(): field for field in organization.FIELDS}
    for feature in value['card_features']:
        for case in feature['cases']:
            for position, anchor in enumerate(case['source_anchors']):
                original = anchor['field']
                canonical = names.get(original.lower())
                organization.require(canonical is not None, 'Unknown source field')
                if canonical != original:
                    anchor['field'] = canonical
                    changes.append({'card_id': feature['card_id'], 'case_id': case['case_id'],
                                    'anchor': position, 'operation': 'field_case',
                                    'before': original, 'after': canonical})
    return value, changes


def adopt(source, destination):
    source = builder.output_root(source)
    destination = builder.output_root(destination)
    builder.check_contract(source)
    original = source/'proposals/router.json'
    packet = json.loads((source/'router_input.json').read_text())
    normalized, changes = normalize(json.loads(original.read_text()))
    validation = organization.validate_router(normalized, packet)
    contract = builder.prepare(destination, 5, source, 131072)
    write_json(destination/'proposals/router.json', normalized)
    audit = {'schema_version': 'router-normalization-v1', 'source_sha256': organization.sha(original),
             'normalized_sha256': organization.sha(destination/'proposals/router.json'),
             'changes': changes, 'validation': validation, 'semantic_edits': False,
             'model_calls': 0, 'evaluation_authorized': False}
    write_json(destination/'router_normalization.json', audit)
    contract['prior_files'][str(original)] = organization.sha(original)
    contract['prior_files'][str(Path(__file__).resolve())] = organization.sha(__file__)
    for name in ('proposals/router.json', 'router_normalization.json'):
        contract['frozen_files'][name] = organization.sha(destination/name)
    contract['stage'] = 'reduce_saved_router_no_new_router_call'
    write_json(destination/'build_contract.json', contract)
    builder.check_contract(destination)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = adopt(args.source_run, args.output)
    print(json.dumps({key: value for key, value in result.items() if key != 'changes'}))


if __name__ == '__main__':
    main()
