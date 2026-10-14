"""Selective reading preserves proof advice and fails closed on invalid selections."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, REPO / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_script('build_selective_references')
reader = load_script('reference_rule_read')


def reference():
    return ('# Fixture\n\n## Scope\n\nRequired shared premise.\n\n## Rules\n\n'
            '- [First](#first)\n- [Second](#second)\n\n'
            '<a id="first"></a>\n## First\n\nSource cards: card-001\n\n'
            '**Trigger:** First failure\n**Action:** Preserve first action\n**Avoid when:** Missing premise\n\n'
            '<a id="second"></a>\n## Second\n\nSource cards: card-002, card-003\n\n'
            '**Trigger:** Second failure\n**Action:** Preserve second action\n**Avoid when:** Wrong shape\n\n'
            '## Conditional links\n\n- When applicable: [Other](other.md#rule)\n').encode()


def test_partition_preserves_rules_scope_and_shared_links():
    scope, rules, footer = builder.parse_reference(reference())
    assert 'Required shared premise.' in scope
    assert list(rules) == ['first', 'second']
    assert rules['second']['source_card_ids'] == ['card-002', 'card-003']
    assert 'Conditional links' in footer
    for rule in rules.values():
        assert rule['body'].encode() in reference()
        assert '**Action:**' in rule['body'] and 'Conditional links' not in rule['body']


@pytest.mark.parametrize('fault', ['anchor', 'sources', 'boundary', 'toc'])
def test_rejects_malformed_source(fault):
    body = reference()
    if fault == 'anchor':
        body = body.replace(b'id="second"', b'id="first"')
    elif fault == 'sources':
        body = body.replace(b'Source cards:', b'Unknown:')
    elif fault == 'boundary':
        body = body.replace(b'**Avoid when:**', b'**Unknown:**')
    else:
        body = body.replace(b'## Rules', b'## Other')
    with pytest.raises(ValueError):
        builder.parse_reference(body)


@pytest.fixture
def library(tmp_path):
    scope, rules, footer = builder.parse_reference(reference())
    full = builder.write_file(tmp_path, 'references/family--full.md', reference())
    entry = builder.write_file(tmp_path, 'references/family.md', b'Routing directory without actions.\n')
    entries = {}
    for rule_id, rule in rules.items():
        entries[rule_id] = builder.write_file(tmp_path, f'references/family--{rule_id}.md',
                                               (scope + rule['body'] + footer).encode())
        entries[rule_id]['source_card_ids'] = rule['source_card_ids']
    manifest = {'family': {**entry, 'full': full, 'rules': entries,
                           'shared_scope': scope, 'shared_links': footer}}
    builder.write_json(tmp_path / 'reference_manifest.json', manifest)
    shutil.copyfile(builder.READER, tmp_path / 'reference_read.py')
    return tmp_path


def test_index_does_not_count_as_body_read(library):
    result = reader.retrieve(library, 'family')
    assert result['operation'] == 'index' and not result['body_read']
    assert result['rule_ids'] == result['source_card_ids'] == []
    assert 'Preserve first action' not in result['content']


def test_selective_read_preserves_constraints_but_not_other_rules(library):
    result = reader.retrieve(library, 'family', ['second'])
    assert result['operation'] == 'read_rules' and result['body_read']
    assert result['source_card_ids'] == ['card-002', 'card-003']
    assert '**Action:** Preserve second action' in result['content']
    assert 'Required shared premise.' in result['content']
    assert 'Conditional links' in result['content']
    assert 'Preserve first action' not in result['content']
    assert result['bytes'] == len(result['content'].encode())
    assert result['sha256'] == builder.digest(result['content'].encode())


def test_multi_selection_and_full_fallback(library):
    result = reader.retrieve(library, 'family', ['second', 'first'])
    assert result['rule_ids'] == ['second', 'first']
    assert result['source_card_ids'] == ['card-001', 'card-002', 'card-003']
    assert result['content'].count('Required shared premise.') == 1
    assert result['content'].count('## Conditional links') == 1
    assert reader.retrieve(library, 'family', full=True)['content'].encode() == reference()


def test_single_rule_returns_full_reference_immediately(library):
    path = library / 'reference_manifest.json'
    manifest = json.loads(path.read_text())
    del manifest['family']['rules']['second']
    builder.write_json(path, manifest)
    result = reader.retrieve(library, 'family')
    assert result['operation'] == 'read_single' and result['body_read']
    assert result['rule_ids'] == ['first']


@pytest.mark.parametrize('selected', [['missing'], ['first', 'first'], ['../first']])
def test_invalid_selection_fails_before_content(library, selected):
    with pytest.raises(ValueError):
        reader.retrieve(library, 'family', selected)


def test_unknown_family_and_conflicting_flags(library):
    with pytest.raises(ValueError):
        reader.retrieve(library, '../family')
    with pytest.raises(ValueError):
        reader.retrieve(library, 'family', ['first'], full=True)


@pytest.mark.parametrize('fault', ['tamper', 'traversal', 'absolute', 'symlink'])
def test_integrity_and_path_safety(library, fault):
    manifest_path = library / 'reference_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    entry = manifest['family']['rules']['first']
    path = library / entry['path']
    if fault == 'tamper':
        path.write_text('altered proof advice')
    elif fault == 'traversal':
        entry['path'] = 'references/../secret'
    elif fault == 'absolute':
        entry['path'] = str(path)
    else:
        path.unlink()
        path.symlink_to(library / 'references/family--full.md')
    builder.write_json(manifest_path, manifest)
    with pytest.raises(ValueError):
        reader.retrieve(library, 'family', ['first'])


def test_cli_records_directory_and_rule_reads(library):
    for args, operation in [([], 'index'), (['--rules', 'first'], 'read_rules'), (['--full'], 'read_full')]:
        result = subprocess.run([sys.executable, str(library / 'reference_read.py'), 'family', *args],
                                capture_output=True, text=True, check=True)
        assert json.loads(result.stdout)['operation'] == operation
    result = subprocess.run([sys.executable, str(library / 'reference_read.py'), 'family', '--rules', 'invalid'],
                            capture_output=True, text=True)
    assert result.returncode == 2 and 'content' not in json.loads(result.stdout)


def test_full_real_candidate_build_and_exhaustive_preservation(tmp_path, monkeypatch):
    source = REPO.parent / 'verus_skill_runs/skillopt-verusage/card-organization-20261012-compact-v1'
    if not source.exists():
        pytest.skip('Frozen local candidate not installed')
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    copied = tmp_path / 'source'
    shutil.copytree(source / 'candidate', copied / 'candidate')
    shutil.copyfile(source / 'candidate_manifest.json', copied / 'candidate_manifest.json')
    output = tmp_path / 'selective'
    record = builder.build(copied, output, builder.DESIGN / 'rule_cues.json')
    assert record['rules'] == 72 and record['cards'] == 78
    assert not record['evaluation_authorized'] and record['model_calls'] == 0
    assert builder.file_hashes(copied / 'candidate') == builder.file_hashes(output / 'control')
    candidate = output / 'candidate'
    entries = json.loads((candidate / 'reference_manifest.json').read_text())
    for family, entry in entries.items():
        original = (copied / 'candidate/references' / f'{family}.md').read_bytes()
        assert reader.retrieve(candidate, family, full=True)['content'].encode() == original
        scope, rules, footer = builder.parse_reference(original)
        if len(rules) > 1:
            all_read = reader.retrieve(candidate, family, list(rules))
            assert all_read['content'] == scope + ''.join(rule['body'] for rule in rules.values()) + footer
        for rule_id, rule in rules.items():
            content = reader.retrieve(candidate, family, [rule_id])['content']
            if len(rules) == 1:
                assert content.encode() == original
            else:
                assert content == scope + rule['body'] + footer
                assert rule_id in reader.retrieve(candidate, family)['content']
                for other_id, other in rules.items():
                    if other_id != rule_id:
                        assert other['body'] not in content
    for path in candidate.rglob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            name, _, anchor = link.partition('#')
            target = path.parent / name if name else path
            assert target.is_file(), (path, link)
            if anchor:
                assert f'<a id="{anchor}"></a>' in target.read_text(), (path, link)
    with pytest.raises(ValueError, match='Output exists'):
        builder.build(copied, output, builder.DESIGN / 'rule_cues.json')
