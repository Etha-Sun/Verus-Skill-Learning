"""Render a review-only candidate with explicit, source-verbatim merge fallback."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import build_card_organization as builder
from skillopt_verusage import card_organization as organization
from skillopt_verusage.guarded_deepseek import write_json


def retain_originals(proposal, packet, review):
    organization.validate_reduction(proposal, packet)
    value = copy.deepcopy(proposal)
    rules = organization.unique(value['rules'], 'rule_id')
    selected = organization.ids(review['rule_ids'], rules, 'review rule IDs')
    organization.require(all(rules[ident]['kind'] == 'merged' for ident in selected), 'Fallback requires merged rules')
    affected = {card for ident in selected for card in rules[ident]['source_card_ids']}
    untouched = [rule for rule in value['rules'] if rule['rule_id'] not in selected]
    organization.require(not affected.intersection(card for rule in untouched for card in rule['source_card_ids']),
                         'Select every rule sharing an affected source before fallback')
    replacements = {card: f'original-{card}' for card in sorted(affected)}
    organization.require(not set(replacements.values()).intersection(rules), 'Fallback rule ID collision')
    organization.text(review.get('issue'), 'review issue')
    organization.text(review.get('required_check'), 'required check')
    value['rules'] = untouched + [{'rule_id': replacements[card], 'title': f'Original {card}',
        'kind': 'verbatim', 'source_card_ids': [card], 'clauses': [],
        'merge_rationale': 'Review rejected the proposed merge; retain the frozen original without resolving its wording.'}
        for card in sorted(affected)]
    for item in value['coverage']:
        if item['card_id'] in affected:
            item['rule_ids'] = [replacements[item['card_id']]]
            item['disposition'] = 'retained_verbatim'
            item['preserved_distinctions'] = ['Entire frozen source body retained; unresolved source wording is not repaired.']
    for item in value['case_rule_map']:
        if item['card_id'] in affected:
            item['rule_ids'] = [replacements[item['card_id']]]
    for item in value['review_items']:
        if set(item['rule_ids']).intersection(selected):
            item['rule_ids'] = sorted((set(item['rule_ids']) - selected) | set(replacements.values()))
    value['review_items'].append({'card_ids': sorted(affected), 'rule_ids': list(replacements.values()),
                                  'issue': review['issue'], 'required_check': review['required_check']})
    value['status'] = 'needs_review'
    organization.validate_reduction(value, packet)
    return value


def finalize(root, review_path):
    root = builder.output_root(root)
    builder.check_contract(root)
    review = json.loads(review_path.read_text())
    organization.require(review.get('evaluation_authorized') is False, 'Review cannot authorize evaluation')
    budget = json.loads((root/'budget.json').read_text())
    organization.require(not budget['reservations'] and not budget['uncertain_requests'], 'Unsettled provider calls')
    router = json.loads((root/'proposals/router.json').read_text())
    packet = json.loads((root/'router_input.json').read_text())
    packets = organization.reduction_packets(router, packet)
    originals = {path.stem: json.loads(path.read_text()) for path in (root/'proposals/reduce').glob('*.json')}
    organization.require(set(originals) == set(packets), 'Incomplete reductions')
    organization.require(set(review['fallbacks']) <= set(originals), 'Unknown reviewed family')
    reviewed = {}
    receipts = {}
    for ident, proposal in sorted(originals.items()):
        source = root/'proposals/reduce'/f'{ident}.json'
        if ident in review['fallbacks']:
            decision = review['fallbacks'][ident]
            organization.require(decision['proposal_sha256'] == organization.sha(source), 'Stale reduction review')
            proposal = retain_originals(proposal, packets[ident], decision)
        organization.validate_reduction(proposal, packets[ident])
        reviewed[ident] = proposal
        receipts[ident] = {'original_sha256': organization.sha(source), 'fallback': ident in review['fallbacks']}
    organization.require(not (root/'reviewed_proposals').exists(), 'Reviewed output already exists')
    for ident, proposal in reviewed.items():
        path = root/'reviewed_proposals'/f'{ident}.json'
        write_json(path, proposal)
        receipts[ident]['reviewed_sha256'] = organization.sha(path)
    result = organization.render_bundle(router, packet, reviewed, builder.DESIGN/'templates/SKILL.md.tmpl',
                                        builder.SEED, root/'candidate')
    result['review_sha256'] = organization.sha(review_path)
    result['finalizer_sha256'] = organization.sha(__file__)
    result['reduction_receipts'] = receipts
    result['cumulative_estimated_cost_usd'] = budget['prior_spend_usd'] + budget['target_spend_usd']
    result['unresolved_review_items'] = [{'family_id': ident, **item}
        for ident, value in reviewed.items() for item in value['review_items']]
    result['router_review_items'] = json.loads((root/'router_review.json').read_text())['unresolved_review_items']
    write_json(root/'candidate_manifest.json', result)
    return {key: value for key, value in result.items()
            if key not in {'files', 'reduction_receipts', 'unresolved_review_items', 'router_review_items'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--review', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(finalize(args.output, args.review)))


if __name__ == '__main__':
    main()
