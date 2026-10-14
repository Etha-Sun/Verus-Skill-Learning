"""Revise routing cues and scoped navigation only; preserve every original rule."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import json
import os
from pathlib import Path
import shutil

import build_selective_references as base


REVIEW = base.DESIGN / 'routing_review_v2.json'


def revised_scope(scope, replacements):
    result = scope
    for replacement in replacements:
        old, new = replacement['old'], replacement['new']
        base.require(bool(old) and result.count(old) == 1, 'Scope replacement is missing or ambiguous')
        base.require(old.startswith('- ') and new.startswith('- '), 'Scope edits must replace routing bullets')
        base.require('## ' not in new and '<a ' not in new and 'Source cards:' not in new,
                     'Scope edit changes rule structure')
        result = result.replace(old, new, 1)
    return result


def render_directory(family, scope, rules, cues, note):
    parts = [scope, '## Rules\n\n',
             'Routing cues only; read the selected full rule before acting.\n\n',
             f'**Relationship:** {note}\n\n']
    for rule_id in rules:
        cue = cues[rule_id]
        name = f'{family}--{rule_id}.md'
        parts.append(f'<a id="{rule_id}"></a>\n'
                     f'- [{rule_id}]({name}): {cue["title"]}.\n'
                     f'  - When: {cue["when"]}.\n'
                     f'  - Avoid: {cue["avoid"]}.\n\n')
    parts.append(f'Read: `python3 reference_read.py {family} --rules ID [ID ...]`\n\n'
                 f'Whole reference: `python3 reference_read.py {family} --full` '
                 f'or [{family}--full.md]({family}--full.md).\n')
    return ''.join(parts)


def prepare_revision(source, review):
    base.require(review['schema_version'] == 'reference-routing-review-v2', 'Wrong routing review schema')
    controls = source / 'control'
    candidate = source / 'candidate'
    manifest = json.loads((source / 'candidate_manifest.json').read_text())
    base.require(manifest['schema_version'] == 'selective-reference-candidate-v1', 'Expected selective-v1 source')
    base.require(base.file_hashes(candidate) == manifest['files'], 'Frozen candidate changed')
    base.require(base.file_hashes(controls) == manifest['source_files'], 'Frozen control changed')
    base.require(manifest['source_files']['SKILL.md'] == base.SOURCE_SKILL_SHA, 'Wrong B baseline')
    cues = json.loads((source / 'rule_cues.json').read_text())
    refs = json.loads((candidate / 'reference_manifest.json').read_text())
    families = {family: base.parse_reference((controls / f'references/{family}.md').read_bytes()) for family in refs}
    multi = {family for family, (_, rules, _) in families.items() if len(rules) > 1}
    base.require(set(review['families']) == multi, 'Must review exactly all multi-rule families')
    prepared = {}
    for family, entry in review['families'].items():
        scope, rules, footer = families[family]
        note = entry['note']
        base.require(entry['relation'] in {'mixed', 'specialization', 'distinct', 'overlap',
                                           'complementary', 'refinement', 'alternatives'}, 'Unknown relation')
        base.require(0 < len(note) <= 420 and all(32 <= ord(char) < 127 for char in note), 'Invalid routing note')
        base.require(not any(char in note for char in '[]<>`'), 'Unexpected note markup')
        base.require(set(entry['cue_overrides']) <= set(rules), 'Unknown rule in cue overrides')
        cues[family].update(entry['cue_overrides'])
        scope = revised_scope(scope, entry.get('scope_replacements', []))
        directory = render_directory(family, scope, rules, cues[family], note)
        original = (controls / f'references/{family}.md').read_text()
        base.require(len(directory.encode()) < len(original.encode()), 'Directory exceeds original full reference')
        prepared[family] = (scope, directory)
    base.validate_cues(cues, families)
    return manifest, cues, refs, families, prepared


def revise(source, output, review_path=REVIEW):
    source, output = source.resolve(), output.resolve()
    run_root = Path(os.environ.get('VERUS_SKILL_RUN_ROOT', base.REPO.parent / 'verus_skill_runs')).resolve()
    base.require(run_root in source.parents and run_root in output.parents, 'Use generated run root only')
    base.require(source != output and source not in output.parents and output not in source.parents, 'Overlapping paths')
    base.require(not output.exists(), 'Output exists; never replace frozen artifacts')
    review = json.loads(review_path.read_text())
    manifest, cues, refs, families, prepared = prepare_revision(source, review)
    parent_files = base.file_hashes(source)
    output.mkdir(parents=True)
    shutil.copytree(source / 'candidate', output / 'candidate')
    shutil.copytree(source / 'control', output / 'control')
    candidate = output / 'candidate'
    receipts = copy.deepcopy(manifest['references_audit'])
    scope_changes = []
    for family, (scope, directory) in prepared.items():
        original_scope, rules, footer = families[family]
        family_entry = refs[family]
        entrypoint = base.write_file(candidate, family_entry['path'], directory.encode())
        family_entry.update(entrypoint)
        family_entry['shared_scope'] = scope
        if scope != original_scope:
            scope_changes.append(family)
            original = (source / 'control' / f'references/{family}.md').read_text()
            base.require(original.startswith(original_scope), 'Original scope is not a prefix')
            full = scope + original[len(original_scope):]
            family_entry['full'] = base.write_file(candidate, family_entry['full']['path'], full.encode())
            for rule_id, rule in rules.items():
                entry = family_entry['rules'][rule_id]
                entry.update(base.write_file(candidate, entry['path'], (scope + rule['body'] + footer).encode()))
            parsed_scope, parsed_rules, parsed_footer = base.parse_reference(full.encode())
            base.require(parsed_scope == scope and parsed_rules == rules and parsed_footer == footer,
                         'Routing edit altered a rule or shared link')
        receipts[family].update(entry_bytes=entrypoint['bytes'], original_scope_sha256=base.digest(original_scope.encode()),
                                scope_sha256=base.digest(scope.encode()), scope_navigation_changed=scope != original_scope,
                                relation=review['families'][family]['relation'])
    base.write_json(candidate / 'reference_manifest.json', refs)
    base.require(base.file_hashes(output / 'control') == manifest['source_files'], 'Control copy changed')
    base.require((candidate / 'SKILL.md').read_bytes() == (source / 'candidate/SKILL.md').read_bytes(), 'Main skill changed')
    base.require((candidate / 'reference_read.py').read_bytes() == (source / 'candidate/reference_read.py').read_bytes(),
                 'Reader changed')
    record = copy.deepcopy(manifest)
    record.update(
        schema_version='selective-reference-candidate-v2', review_required=True, evaluation_authorized=False,
        revision_parent=str(source), revision_parent_manifest_sha256=base.digest((source / 'candidate_manifest.json').read_bytes()),
        revision_inputs={str(path.relative_to(base.REPO)): base.digest(path.read_bytes()) for path in
                         [Path(__file__).resolve(), Path(base.__file__).resolve(), review_path.resolve()]},
        routing_review_sha256=base.digest(review_path.read_bytes()), files=base.file_hashes(candidate),
        references_audit=receipts, navigation_scope_changed_families=scope_changes,
        full_reference_bytes_unchanged=37 - len(scope_changes), original_rule_blocks_unchanged=72,
        semantic_review='Coding-assistant source-only review, not independent or empirically validated retrieval.',
        relation_counts=dict(Counter(entry['relation'] for entry in review['families'].values())),
        construction='Source-only routing revision; 21 family relationship notes, cue revisions and scoped navigation corrections; no API calls.',
    )
    base.write_json(output / 'candidate_manifest.json', record)
    base.write_json(output / 'rule_cues.json', cues)
    shutil.copyfile(review_path, output / 'routing_review_v2.json')
    base.require(base.file_hashes(source) == parent_files, 'Frozen parent changed during revision')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = revise(args.source_run, args.output)
    print(json.dumps({key: record[key] for key in ['rules', 'skill_bytes', 'navigation_scope_changed_families',
                                                   'relation_counts', 'evaluation_authorized']}))


if __name__ == '__main__':
    main()
