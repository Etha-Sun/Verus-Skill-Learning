"""The portable renderer must preserve every evaluated pseudocode card body."""
import hashlib
import json
from pathlib import Path

from render_reviewed_pseudocode import render

PACKAGE = Path(__file__).resolve().parents[1] / 'research_artifacts/skill-chain-seven-arm-20261022'


def test_published_bundles_have_exact_recorded_bytes_and_shared_indexes():
    for row in json.loads((PACKAGE / 'manifest.json').read_text())['files']:
        assert hashlib.sha256((PACKAGE / row['file']).read_bytes()).hexdigest() == row['sha256']
    for family in ['old', 'new']:
        roots = [PACKAGE / 'bundles' / f'{family}_{rep}' for rep in ['prose', 'skeleton', 'pseudocode']]
        assert len({(p / 'SKILL.md').read_bytes() for p in roots}) == 1
        assert all(len(json.loads((p / 'cards.json').read_text())['cards']) == 10 for p in roots)


def test_portable_renderer_reproduces_all_twenty_evaluated_card_bodies(tmp_path):
    out = tmp_path / 'rendered'
    rows = render(PACKAGE / 'source-cards', PACKAGE / 'pseudocode-routes.txt', out)
    assert len(rows) == 20
    for family in ['old', 'new']:
        expected = json.loads((PACKAGE / 'bundles' / f'{family}_pseudocode/cards.json').read_text())['cards']
        actual = json.loads((out / 'banks' / f'{family}_pseudocode.json').read_text())['cards']
        assert {c['id']: c['content'] for c in actual} == {c['id']: c['content'] for c in expected}
