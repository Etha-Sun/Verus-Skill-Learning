"""Build a review-only, zero-API read-granularity ablation from frozen references."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil


REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / 'research_memory/projects/verus_self_evolving/experiments/20261013-selective-reference-reading'
INDEX = '## Reference index\n\n'
OPTIONAL = '## On-demand proof repair references\n\n'
ANCHOR = re.compile(r'^<a id="([a-z0-9-]+)"></a>\n', re.M)
SOURCE_SKILL_SHA = '6d4e410ecd43bca58c2fe0dcd2164c8b10455d732759c581b5b0b56fa4f7c8ca'
READER = Path(__file__).with_name('reference_rule_read.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def file_hashes(root):
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'Symlink in source package')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def parse_reference(body):
    text = body.decode('utf-8')
    anchors = list(ANCHOR.finditer(text))
    require(bool(anchors) and len({match[1] for match in anchors}) == len(anchors), 'Missing/duplicate rule anchors')
    prefix = text[:anchors[0].start()]
    require(prefix.count('## Rules\n') == 1, 'Missing rule TOC')
    scope = prefix.split('## Rules\n')[0]
    ending = re.search(r'^## Conditional links\n|^- Distinguish from |^- Related ', text[anchors[-1].end():], re.M)
    end = anchors[-1].end() + ending.start() if ending else len(text)
    footer = text[end:]
    rules = {}
    for position, match in enumerate(anchors):
        stop = anchors[position + 1].start() if position + 1 < len(anchors) else end
        block = text[match.start():stop]
        source = re.search(r'^Source cards: (.+)$', block, re.M)
        require(source is not None, 'Rule missing source provenance')
        cards = source[1].split(', ')
        require(all(re.fullmatch(r'card-\d{3}', card) for card in cards), 'Invalid source card IDs')
        require('**Trigger:**' in block and '**Avoid when:**' in block, 'Missing rule boundaries')
        rules[match[1]] = {'body': block, 'source_card_ids': cards}
    require((prefix + ''.join(rule['body'] for rule in rules.values()) + footer).encode() == body,
            'Reference did not round-trip byte-for-byte')
    return scope, rules, footer


def validate_cues(cues, families):
    expected = {(family, rule) for family, (_, rules, _) in families.items() if len(rules) > 1 for rule in rules}
    require(set(cues) == {family for family, _ in expected}, 'Cue family coverage mismatch')
    require({(family, rule) for family, entries in cues.items() for rule in entries} == expected,
            'Cue rule coverage mismatch')
    for entries in cues.values():
        for cue in entries.values():
            require(set(cue) == {'title', 'when', 'avoid'}, 'Cue fields mismatch')
            for field, limit in [('title', 80), ('when', 180), ('avoid', 180)]:
                value = cue[field]
                require(isinstance(value, str) and 0 < len(value) <= limit, 'Cue exceeds length limit')
                require(all(32 <= ord(char) < 127 for char in value) and not any(char in value for char in '[]<>`|'),
                        'Unsafe cue markup')


def skill_text(original):
    require(original.count(INDEX) == original.count(OPTIONAL) == 1, 'Ambiguous SKILL sections')
    old = 'Read any indexed reference by ID:\n'
    new = ('Read any indexed reference by ID (one-rule references return the full body;\n'
           'multi-rule references return a short rule directory):\n')
    require(original.count(old) == 1, 'Unexpected reading instructions')
    result = original.replace(old, new)
    command = '    python3 reference_read.py compound-stability-existing-rules\n'
    require(result.count(command) == 1, 'Missing example')
    result = result.replace(command, command + '\nSelect rule IDs from that directory with `--rules ID [ID ...]`, or use\n'
                            '`--full` for the whole reference. Directory cues are not rule bodies.\n')
    require(result.split(OPTIONAL)[0] == original.split(OPTIONAL)[0], 'Executive changed')
    require(result.split(INDEX)[1] == original.split(INDEX)[1], 'Top-level index changed')
    return result


def write_file(root, name, body):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return {'path': name, 'bytes': len(body), 'sha256': digest(body)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def build(source_run, output, cues_path):
    source_run = source_run.resolve()
    output = output.resolve()
    run_root = Path(os.environ.get('VERUS_SKILL_RUN_ROOT', REPO.parent / 'verus_skill_runs')).resolve()
    require(run_root in output.parents and run_root in source_run.parents, 'Use generated run root only')
    require(source_run not in output.parents and output not in source_run.parents, 'Overlapping source/output')
    require(not output.exists(), 'Output exists; do not overwrite reviewed artifacts')
    source = source_run / 'candidate'
    manifest = json.loads((source_run / 'candidate_manifest.json').read_text())
    before = file_hashes(source)
    require(before == manifest['files'], 'Frozen source package/manifest mismatch')
    require(before['SKILL.md'] == SOURCE_SKILL_SHA, 'Not the reviewed compact B candidate')
    refs = json.loads((source / 'reference_manifest.json').read_text())
    families = {}
    for family, entry in refs.items():
        require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', family) is not None, 'Unsafe family id')
        require(entry['path'] == f'references/{family}.md', 'Unexpected source layout')
        require(before[entry['path']] == entry['sha256'], 'Reference hash mismatch')
        families[family] = parse_reference((source / entry['path']).read_bytes())
    distribution = dict(sorted(Counter(len(rules) for _, rules, _ in families.values()).items()))
    require(distribution == {1: 16, 2: 9, 3: 10, 4: 2}, 'Frozen rule distribution changed')
    all_cards = [card for _, rules, _ in families.values() for rule in rules.values() for card in rule['source_card_ids']]
    require(len(all_cards) == len(set(all_cards)) == 78, 'Source cards missing or duplicated')
    cues = json.loads(cues_path.read_text())
    validate_cues(cues, families)
    output.mkdir(parents=True)
    shutil.copytree(source, output / 'control')
    candidate = output / 'candidate'
    candidate.mkdir()
    write_file(candidate, 'SKILL.md', skill_text((source / 'SKILL.md').read_text()).encode())
    write_file(candidate, 'reference_read.py', READER.read_bytes())
    manifest_refs = {}
    receipts = {}
    for family, (scope, rules, footer) in families.items():
        original = (source / refs[family]['path']).read_bytes()
        full_path = f'references/{family}.md' if len(rules) == 1 else f'references/{family}--full.md'
        full = write_file(candidate, full_path, original)
        rule_entries = {}
        rule_hashes = {}
        directory = [scope, '## Rules\n\n',
                     'Routing cues only; read the selected full rule before acting.\n\n']
        for rule_id, rule in rules.items():
            if len(rules) == 1:
                entry = dict(full)
            else:
                name = f'references/{family}--{rule_id}.md'
                entry = write_file(candidate, name, (scope + rule['body'] + footer).encode())
                cue = cues[family][rule_id]
                directory.append(f'<a id="{rule_id}"></a>\n'
                                 f'- [{rule_id}]({Path(name).name}): {cue["title"]}. '
                                 f'When: {cue["when"]}. Avoid: {cue["avoid"]}.\n\n')
            entry['source_card_ids'] = rule['source_card_ids']
            entry['original_rule_sha256'] = digest(rule['body'].encode())
            rule_entries[rule_id] = entry
            rule_hashes[rule_id] = entry['original_rule_sha256']
        if len(rules) == 1:
            entrypoint = dict(full)
        else:
            directory.append(f'Read: `python3 reference_read.py {family} --rules ID [ID ...]`\n\n'
                             f'Whole reference: `python3 reference_read.py {family} --full` '
                             f'or [{family}--full.md]({family}--full.md).\n')
            entrypoint = write_file(candidate, f'references/{family}.md', ''.join(directory).encode())
            require(entrypoint['bytes'] < full['bytes'], 'Directory is not smaller than original')
        manifest_refs[family] = {**entrypoint, 'source_card_ids': refs[family]['source_card_ids'],
                                 'full': full, 'rules': rule_entries, 'shared_scope': scope, 'shared_links': footer}
        receipts[family] = {'rules': len(rules), 'original_bytes': len(original),
                            'entry_bytes': entrypoint['bytes'], 'original_sha256': digest(original),
                            'scope_sha256': digest(scope.encode()), 'footer_sha256': digest(footer.encode()),
                            'rule_sha256': rule_hashes}
    write_json(candidate / 'reference_manifest.json', manifest_refs)
    require(file_hashes(source) == before == file_hashes(output / 'control'), 'Baseline changed')
    record = {
        'schema_version': 'selective-reference-candidate-v1', 'review_required': True,
        'evaluation_authorized': False, 'model_calls': 0, 'new_cost_usd': 0,
        'source_run': str(source_run), 'parent_manifest_sha256': digest((source_run / 'candidate_manifest.json').read_bytes()),
        'source_files': before, 'files': file_hashes(candidate), 'references': len(refs), 'rules': 72, 'cards': 78,
        'single_rule_references': 16, 'indexed_references': 21,
        'skill_bytes': (candidate / 'SKILL.md').stat().st_size,
        'source_skill_bytes': (source / 'SKILL.md').stat().st_size,
        'executive_unchanged': True, 'top_index_unchanged': True,
        'unresolved_review_items': manifest['unresolved_review_items'],
        'router_review_items': manifest['router_review_items'],
        'construction': 'Deterministic split; coding-assistant-authored source-only routing cues; no model API calls.',
        'inputs': {str(path.relative_to(REPO)): digest(path.read_bytes())
                   for path in [Path(__file__).resolve(), READER, cues_path.resolve()]},
        'references_audit': receipts,
    }
    write_json(output / 'candidate_manifest.json', record)
    shutil.copyfile(cues_path, output / 'rule_cues.json')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = build(args.source_run, args.output, DESIGN / 'rule_cues.json')
    print(json.dumps({key: result[key] for key in ['references', 'rules', 'skill_bytes', 'model_calls', 'evaluation_authorized']}))


if __name__ == '__main__':
    main()
