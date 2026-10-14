"""Build a frozen short-index revision without modifying reference bodies."""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import shutil

import build_card_organization as builder
from skillopt_verusage import card_organization as organization
from skillopt_verusage.guarded_deepseek import write_json


MARKER = '## Reference index\n\n'
PROMPT = builder.DESIGN/'prompts/compact_index_system.md'
CAP = 32768


def render_index(original, proposal, expected_ids, byte_limit):
    organization.require(proposal.get('schema_version') == 'compact-reference-index-v1', 'Compact index schema')
    entries = organization.unique(proposal['entries'], 'family_id')
    organization.require(set(entries) == set(expected_ids), 'Reference ID coverage changed')
    organization.require(original.count(MARKER) == 1, 'Missing or ambiguous index marker')
    prefix = original.split(MARKER)[0] + MARKER
    lines = []
    for ident, entry in sorted(entries.items()):
        organization.require(organization.SLUG.fullmatch(ident) is not None, 'Unsafe reference ID')
        cue = organization.text(entry.get('description'), 'routing description')
        organization.require(cue.isascii() and len(cue) <= 150, 'Description exceeds ASCII/length limit')
        organization.require(all(32 <= ord(char) < 127 for char in cue), 'Non-printable description')
        organization.require(not any(char in cue for char in '[]<>`'), 'Description contains markup')
        lines.append(f'- [{ident}](references/{ident}.md): {cue}')
    result = prefix + '\n'.join(lines) + '\n'
    organization.require(len(result.encode()) <= byte_limit, 'Main SKILL exceeds flat-control byte limit')
    return result


def prepare(root, source):
    source = builder.output_root(source)
    builder.check_contract(source)
    manifest = json.loads((source/'candidate_manifest.json').read_text())
    bundle = source/'candidate'
    organization.require(manifest['evaluation_authorized'] is False, 'Expected review-only candidate')
    for name, digest in manifest['files'].items():
        path = bundle/name
        organization.require(bundle.resolve() in path.resolve().parents and not path.is_symlink(), 'Unsafe source file')
        organization.require(organization.sha(path) == digest, 'Source bundle changed')
    packet = json.loads((source/'router_input.json').read_text())
    prior_spend, parents = builder.prior_cost(source, 5, packet)
    families = json.loads((source/'proposals/router.json').read_text())['families']
    refs = json.loads((bundle/'reference_manifest.json').read_text())
    organization.require({item['family_id'] for item in families} == set(refs), 'Family/manifest mismatch')
    root.mkdir(parents=True, exist_ok=False)
    write_json(root/'index_input.json', {'schema_version': 'compact-reference-input-v1', 'families': families})
    (root/'index_system.md').write_bytes(PROMPT.read_bytes())
    evidence = [source/'candidate_manifest.json', source/'proposals/router.json', source/'control/SKILL.md',
                *(bundle/name for name in manifest['files']), Path(__file__).resolve(), PROMPT]
    parents.update({str(path): organization.sha(path) for path in evidence})
    contract = {'schema_version': 'compact-reference-build-v1', 'source_run': str(source),
        'model': 'deepseek-v4-pro', 'reasoning_effort': 'max', 'output_cap': CAP,
        'budget_usd': 5, 'prior_spend_usd': prior_spend, 'evaluation_authorized': False,
        'max_skill_bytes': (source/'control/SKILL.md').stat().st_size,
        'inputs': builder.inputs(), 'parent_files': parents,
        'frozen_files': {name: organization.sha(root/name) for name in ('index_input.json', 'index_system.md')}}
    write_json(root/'index_contract.json', contract)
    return contract


def check(root):
    contract = json.loads((root/'index_contract.json').read_text())
    organization.require(contract['inputs'] == builder.inputs(), 'Build code changed')
    for name, digest in contract['parent_files'].items():
        organization.require(organization.sha(name) == digest, 'Frozen source/evidence changed')
    for name, digest in contract['frozen_files'].items():
        organization.require(organization.sha(root/name) == digest, 'Frozen compact input changed')
    return contract


def generate(root, env_file):
    contract = check(root)
    organization.require(not (root/'provider_calls.jsonl').exists() and not (root/'calls').exists(),
                         'A request already exists; no automatic paid retry')
    provider = builder.client(root, env_file, contract)
    result, usage = provider.call(system=(root/'index_system.md').read_text(),
        user=(root/'index_input.json').read_text(), name='compact-index', cap=CAP, effort='max')
    proposal = json.loads(result)
    write_json(root/'index_proposal.json', proposal)
    source = Path(contract['source_run'])
    expected = json.loads((source/'candidate/reference_manifest.json').read_text())
    body = render_index((source/'candidate/SKILL.md').read_text(), proposal, expected, contract['max_skill_bytes'])
    validation = {'entries': len(expected), 'skill_bytes': len(body.encode()),
                  'proposal_sha256': organization.sha(root/'index_proposal.json'), 'usage': usage,
                  'evaluation_authorized': False}
    write_json(root/'index_validation.json', validation)
    return validation


def render(root):
    contract = check(root)
    source = Path(contract['source_run'])
    refs = json.loads((source/'candidate/reference_manifest.json').read_text())
    proposal = json.loads((root/'index_proposal.json').read_text())
    body = render_index((source/'candidate/SKILL.md').read_text(), proposal, refs, contract['max_skill_bytes'])
    budget = json.loads((root/'budget.json').read_text())
    organization.require(not budget['reservations'] and not budget['uncertain_requests'], 'Unresolved provider costs')
    destination = root/'candidate'
    organization.require(not destination.exists(), 'Candidate already exists')
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
        'proposal_sha256': organization.sha(root/'index_proposal.json'), 'unchanged_files': unchanged,
        'original_skill_bytes': (source/'candidate/SKILL.md').stat().st_size,
        'control_skill_bytes': contract['max_skill_bytes'], 'prefix_unchanged': True}
    write_json(root/'candidate_manifest.json', manifest)
    return {'skill_bytes': len(body.encode()), 'unchanged_files': len(unchanged),
            'references': manifest['references'], 'rules': manifest['rules'],
            'cumulative_estimated_cost_usd': manifest['cumulative_estimated_cost_usd']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'generate', 'render'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-run', type=Path)
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    root = builder.output_root(args.output)
    if args.phase == 'prepare':
        if args.source_run is None:
            parser.error('prepare requires --source-run')
        result = prepare(root, args.source_run)
        print(json.dumps({key: result[key] for key in ('model', 'prior_spend_usd', 'max_skill_bytes')}))
        return
    with (root/'build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.phase == 'generate':
            if args.env_file is None:
                parser.error('generate requires --env-file')
            result = generate(root, args.env_file)
        else:
            result = render(root)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
