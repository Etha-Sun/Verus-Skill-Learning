import hashlib
import json

import pytest

from skillopt_verusage.card_revision import revise_bank
from skillopt_verusage.card_search import field


def fixture(tmp_path):
    content = '**Trigger:** Need stability. **Action:** Old advice. **Why:** Rule. **Validate:** Both checks. **Avoid when:** Wrong rule.'
    bank = tmp_path/'bank.json'
    bank.write_text(json.dumps({'schema_version':'stage-card-bank-v1','cards':[
        {'id':'card-001','content':content}, {'id':'card-002','content':content}]}))
    recipe = {'schema_version':'reviewed-card-revision-v1',
        'source_bank_sha256':hashlib.sha256(bank.read_bytes()).hexdigest(),
        'field_updates':{'card-001':{'Action':'Inner temporal predicate; retain state lifting.'}},
        'index_descriptions':{'card-001':'Extra always wrapper.', 'card-002':'Different stability route.'}}
    revision = tmp_path/'revision.json'; revision.write_text(json.dumps(recipe))
    seed = tmp_path/'seed.md'; seed.write_text('Preserve proof safety.\n')
    return bank, revision, seed, content


def test_revision_preserves_ids_unchanged_bodies_source_and_private_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    bank, revision, seed, original = fixture(tmp_path)
    before = bank.read_bytes()
    receipt = revise_bank(bank, revision, seed, tmp_path/'new')
    cards = json.loads((tmp_path/'new/cards.json').read_text())['cards']
    assert [c['id'] for c in cards] == ['card-001','card-002']
    assert field(cards[0]['content'], 'Action') == 'Inner temporal predicate; retain state lifting.'
    assert cards[1]['content'] == original
    assert bank.read_bytes() == before
    assert receipt['ids_and_order_preserved'] and len(receipt['changes']) == 1
    assert 'source_bank_sha256' not in (tmp_path/'new/bundle/cards.json').read_text()
    with pytest.raises(FileExistsError): revise_bank(bank, revision, seed, tmp_path/'new')


@pytest.mark.parametrize('defect', ['hash', 'id', 'descriptions', 'empty', 'injected'])
def test_invalid_revision_rejected_before_output(tmp_path, monkeypatch, defect):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    bank, revision, seed, _ = fixture(tmp_path)
    recipe = json.loads(revision.read_text())
    if defect == 'hash': recipe['source_bank_sha256'] = '0'*64
    elif defect == 'id': recipe['field_updates']['card-999'] = {'Action':'Unknown.'}
    elif defect == 'descriptions': recipe['index_descriptions'].pop('card-002')
    else: recipe['field_updates']['card-001']['Action'] = '' if defect == 'empty' else '**Why:** Injected'
    revision.write_text(json.dumps(recipe))
    with pytest.raises(ValueError): revise_bank(bank, revision, seed, tmp_path/'new')
    assert not (tmp_path/'new').exists()
