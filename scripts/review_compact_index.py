"""Render reviewed navigation cues while preserving the raw model proposal."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil

import compact_card_index as compact
from skillopt_verusage import card_organization as organization
from skillopt_verusage.guarded_deepseek import write_json


def navigation_cues(proposal):
    reviewed = copy.deepcopy(proposal)
    changes = []
    for entry in reviewed['entries']:
        original = entry['description']
        if entry['family_id'] != 'post-verification-cleanup':
            cue = original.split(';', 1)[0].strip()
            cue = cue.removesuffix(', closing the proof directly.')
            entry['description'] = cue.rstrip('.') + '.'
        if entry['description'] != original:
            changes.append({'family_id': entry['family_id'], 'before': original,
                            'after': entry['description'], 'reason': 'Keep the entry condition, not the action or success assertion.'})
    return reviewed, changes


def finalize(root):
    contract = compact.check(root)
    source = Path(contract['source_run'])
    refs = json.loads((source/'candidate/reference_manifest.json').read_text())
    original = json.loads((root/'index_proposal.json').read_text())
    prior_body = (source/'candidate/SKILL.md').read_text()
    compact.render_index(prior_body, original, refs, contract['max_skill_bytes'])
    reviewed, changes = navigation_cues(original)
    body = compact.render_index(prior_body, reviewed, refs, contract['max_skill_bytes'])
    budget = json.loads((root/'budget.json').read_text())
    organization.require(not budget['reservations'] and not budget['uncertain_requests'], 'Unresolved provider costs')
    organization.require(not (root/'candidate').exists() and not (root/'index_review.json').exists(), 'Review output already exists')
    write_json(root/'index_reviewed.json', reviewed)
    receipt = {'reviewer': 'coding-assistant', 'method': 'Remove action tails after semicolons; retain cleanup state/diagnostic clause.',
        'reason': 'The raw proposal introduced ungrounded actions such as selecting triggers for universal equivalence. Navigation cues must not add proof advice.',
        'original_sha256': organization.sha(root/'index_proposal.json'),
        'reviewed_sha256': organization.sha(root/'index_reviewed.json'),
        'review_script_sha256': organization.sha(__file__), 'changes': changes,
        'paid_calls': 0, 'evaluation_authorized': False}
    write_json(root/'index_review.json', receipt)
    destination = root/'candidate'
    shutil.copytree(source/'candidate', destination)
    (destination/'SKILL.md').write_text(body)
    manifest = json.loads((source/'candidate_manifest.json').read_text())
    unchanged = []
    for name, digest in manifest['files'].items():
        if name != 'SKILL.md':
            organization.require(organization.sha(destination/name) == digest, 'Non-index artifact changed')
            unchanged.append(name)
    manifest.update(skill_bytes=len(body.encode()), review_required=True, evaluation_authorized=False,
        cumulative_estimated_cost_usd=budget['prior_spend_usd'] + budget['target_spend_usd'])
    manifest['files']['SKILL.md'] = organization.sha(destination/'SKILL.md')
    manifest['index_revision'] = {'source_manifest_sha256': organization.sha(source/'candidate_manifest.json'),
        'original_proposal_sha256': receipt['original_sha256'], 'reviewed_proposal_sha256': receipt['reviewed_sha256'],
        'review_receipt_sha256': organization.sha(root/'index_review.json'), 'unchanged_files': unchanged,
        'original_skill_bytes': len(prior_body.encode()), 'control_skill_bytes': contract['max_skill_bytes'],
        'prefix_unchanged': True}
    write_json(root/'candidate_manifest.json', manifest)
    return {'skill_bytes': len(body.encode()), 'unchanged_files': len(unchanged), 'entries': len(refs),
            'cumulative_estimated_cost_usd': manifest['cumulative_estimated_cost_usd']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(compact.builder.output_root(args.output))))
