"""Short directory rendering preserves the preamble and rejects truncation."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def compact(monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('compact_index_test', scripts/'compact_card_index.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def proposal():
    return {'schema_version': 'compact-reference-index-v1', 'entries': [
        {'family_id': 'trigger-inference', 'description': 'Active trigger inference errors, not post-verification warnings.'}]}


def test_preserves_prefix_and_links(compact):
    original = 'Executive and optional-reading instructions.\n\n' + compact.MARKER + 'Long old index\n'
    body = compact.render_index(original, proposal(), ['trigger-inference'], 500)
    assert body.split(compact.MARKER)[0] == original.split(compact.MARKER)[0]
    assert '[trigger-inference](references/trigger-inference.md)' in body
    assert 'Long old index' not in body


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'long', 'newline', 'markup', 'budget', 'id'])
def test_rejects_invalid_short_index(compact, fault):
    value = proposal()
    limit = 500
    if fault == 'missing':
        value['entries'] = []
    elif fault == 'duplicate':
        value['entries'] *= 2
    elif fault == 'long':
        value['entries'][0]['description'] = 'word ' * 31
    elif fault == 'newline':
        value['entries'][0]['description'] = 'First\nSecond'
    elif fault == 'markup':
        value['entries'][0]['description'] = '[external](https://example.com)'
    elif fault == 'id':
        value['entries'][0]['family_id'] = '../escape'
    else:
        limit = 20
    with pytest.raises(ValueError):
        compact.render_index('Executive\n' + compact.MARKER, value, ['trigger-inference'], limit)


def test_revision_copies_every_non_index_file_unchanged(compact, tmp_path, monkeypatch):
    source = tmp_path/'source'
    bundle = source/'candidate'
    (bundle/'references').mkdir(parents=True)
    (bundle/'SKILL.md').write_text('Executive and reader instructions\n' + compact.MARKER + 'Old verbose index\n')
    (bundle/'references/trigger-inference.md').write_text('Exact original reference body.\n')
    (bundle/'reference_read.py').write_text('reader fixture\n')
    (bundle/'reference_manifest.json').write_text(json.dumps({'trigger-inference': {}}))
    files = {str(path.relative_to(bundle)): compact.organization.sha(path)
             for path in bundle.rglob('*') if path.is_file()}
    (source/'candidate_manifest.json').write_text(json.dumps({'files': files, 'references': 1, 'rules': 2,
        'unresolved_review_items': ['Keep original source ambiguity visible.']}))
    (source/'control').mkdir()
    (source/'control/SKILL.md').write_text('control' * 100)
    root = tmp_path/'revision'
    root.mkdir()
    (root/'index_proposal.json').write_text(json.dumps(proposal()))
    (root/'budget.json').write_text(json.dumps({'reservations': {}, 'uncertain_requests': 0,
        'prior_spend_usd': 1.7, 'target_spend_usd': .1}))
    monkeypatch.setattr(compact, 'check', lambda path: {'source_run': str(source), 'max_skill_bytes': 700})
    result = compact.render(root)
    assert result['unchanged_files'] == 3
    for name, digest in files.items():
        assert compact.organization.sha(bundle/name) == digest
        if name != 'SKILL.md':
            assert compact.organization.sha(root/'candidate'/name) == digest
    revised = json.loads((root/'candidate_manifest.json').read_text())
    assert revised['unresolved_review_items'] == ['Keep original source ambiguity visible.']
    assert revised['review_required'] and not revised['evaluation_authorized']


def test_review_removes_action_tails_without_overwriting_model(monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('review_compact_test', scripts/'review_compact_index.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = {'entries': [
        {'family_id': 'universal-equivalence', 'description': 'Equivalent universal formulas; select triggers.'},
        {'family_id': 'post-verification-cleanup', 'description': 'Verification passed; warnings remain.'},
        {'family_id': 'direct-lemma', 'description': 'Matching lemma with available premises, closing the proof directly.'}]}
    before = json.dumps(value)
    revised, changes = module.navigation_cues(value)
    assert json.dumps(value) == before
    assert revised['entries'][0]['description'] == 'Equivalent universal formulas.'
    assert revised['entries'][1] == value['entries'][1]
    assert revised['entries'][2]['description'] == 'Matching lemma with available premises.'
    assert len(changes) == 2
