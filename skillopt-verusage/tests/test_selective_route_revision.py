"""Review-only routing changes preserve frozen rules and expose overlaps honestly."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

import pytest


REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def revision(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / 'scripts'))
    spec = importlib.util.spec_from_file_location('selective_route_revision_test', REPO / 'scripts/revise_selective_routes.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source(tmp_path, monkeypatch):
    root = REPO.parent / 'verus_skill_runs/skillopt-verusage/card-organization-20261013-selective-v1'
    if not root.exists():
        pytest.skip('Frozen local selective-v1 package not installed')
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    copied = tmp_path / 'source'
    shutil.copytree(root, copied)
    return copied


def test_review_all_families_with_valid_source_rule_ids(revision, source):
    review = json.loads(revision.REVIEW.read_text())
    _, cues, _, families, prepared = revision.prepare_revision(source, review)
    assert len(prepared) == len(cues) == 21
    assert sum(len(entries) for entries in cues.values()) == 56
    assert sum(len(rules) for _, rules, _ in families.values()) == 72
    assert len([entry for entry in review['families'].values() if entry.get('scope_replacements')]) == 5


@pytest.mark.parametrize('fault', ['missing_family', 'unknown_rule', 'missing_scope', 'structural_scope',
                                  'markup', 'too_long', 'unknown_relation'])
def test_bad_review_rejected_before_writing(revision, source, fault):
    review = json.loads(revision.REVIEW.read_text())
    family = review['families']['direct-existing-lemma-bridge']
    if fault == 'missing_family':
        del review['families']['trigger-inference-annotation']
    elif fault == 'unknown_rule':
        family['cue_overrides']['not-in-this-family'] = copy.deepcopy(family['cue_overrides']['original-card-003'])
    elif fault == 'missing_scope':
        family['scope_replacements'][0]['old'] = '- nonexistent source condition\n'
    elif fault == 'structural_scope':
        family['scope_replacements'][0]['new'] = '- New scope\n## New rule\n'
    elif fault == 'markup':
        family['cue_overrides']['original-card-003']['when'] = 'bad [link]'
    elif fault == 'too_long':
        family['note'] = 'x' * 421
    else:
        family['relation'] = 'mutually_exclusive_without_evidence'
    with pytest.raises(ValueError):
        revision.prepare_revision(source, review)


def test_v2_preserves_all_bodies_controls_links_and_main_skill(revision, source, tmp_path):
    before = revision.base.file_hashes(source)
    output = tmp_path / 'v2'
    record = revision.revise(source, output)
    assert revision.base.file_hashes(source) == before
    assert record['original_rule_blocks_unchanged'] == 72
    assert record['full_reference_bytes_unchanged'] == 32
    assert record['model_calls'] == 0 and not record['evaluation_authorized']
    assert record['files'] == revision.base.file_hashes(output / 'candidate')
    assert record['source_files'] == revision.base.file_hashes(output / 'control')
    spec = importlib.util.spec_from_file_location('v2_reader_test', output / 'candidate/reference_read.py')
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    refs = json.loads((output / 'candidate/reference_manifest.json').read_text())
    review = json.loads(revision.REVIEW.read_text())
    for family, entry in refs.items():
        original = (source / 'control/references' / f'{family}.md').read_bytes()
        scope, rules, footer = revision.base.parse_reference(original)
        replacements = review['families'].get(family, {}).get('scope_replacements', [])
        corrected_scope = revision.revised_scope(scope, replacements)
        full = reader.retrieve(output / 'candidate', family, full=True)['content']
        assert full == corrected_scope + original.decode()[len(scope):]
        _, current_rules, current_footer = revision.base.parse_reference(full.encode())
        assert current_rules == rules and current_footer == footer
        for rule_id, rule in rules.items():
            selected = reader.retrieve(output / 'candidate', family, [rule_id])['content']
            assert selected == (full if len(rules) == 1 else corrected_scope + rule['body'] + footer)
            assert revision.base.digest(rule['body'].encode()) == entry['rules'][rule_id]['original_rule_sha256']
        if len(rules) > 1:
            directory = reader.retrieve(output / 'candidate', family)
            assert not directory['body_read'] and directory['rule_ids'] == []
            assert all(rule['body'] not in directory['content'] for rule in rules.values())
            multi = reader.retrieve(output / 'candidate', family, list(rules))
            assert multi['content'] == corrected_scope + ''.join(rule['body'] for rule in rules.values()) + footer
        else:
            assert full.encode() == original
    for name in ['SKILL.md', 'reference_read.py']:
        assert (output / 'candidate' / name).read_bytes() == (source / 'candidate' / name).read_bytes()
    for path in (output / 'candidate').rglob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            name, _, anchor = link.partition('#')
            target = path.parent / name if name else path
            assert target.is_file(), (path, link)
            if anchor:
                assert f'<a id="{anchor}"></a>' in target.read_text(), (path, link)
    with pytest.raises(ValueError, match='Output exists'):
        revision.revise(source, output)


def test_tampered_parent_is_rejected(revision, source, tmp_path):
    (source / 'candidate/SKILL.md').write_text('changed')
    output = tmp_path / 'v2'
    with pytest.raises(ValueError, match='Frozen candidate changed'):
        revision.revise(source, output)
    assert not output.exists()


def test_directory_relationship_preserves_nonexclusive_selection(revision, source):
    review = json.loads(revision.REVIEW.read_text())
    _, _, _, _, prepared = revision.prepare_revision(source, review)
    trigger_scope, trigger_directory = prepared['trigger-inference-annotation']
    assert '- Not for: Failure is a missing antecedent rather than trigger selection' not in trigger_scope
    assert 'original-card-018' in trigger_directory and 'original-card-034' in trigger_directory
    assert 'original-card-057' in trigger_directory and 'can match all three' in trigger_directory
    for family in ['function-field-projection-syntax', 'quantified-proof-antecedent-binder-scope']:
        assert review['families'][family]['relation'] == 'overlap'
    assert review['families']['sequence-fold-concat-equality']['relation'] == 'alternatives'
    assert review['families']['transition-system-step-safety']['relation'] == 'complementary'
