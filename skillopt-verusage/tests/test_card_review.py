import hashlib
import json

import pytest

from skillopt_verusage.card_review import prepare_review
from skillopt_verusage.card_bank import build_bundle


def inputs(tmp_path):
    bank = tmp_path/'bank.json'
    bank.write_text(json.dumps({'schema_version':'stage-card-bank-v1', 'cards':[
        {'id':'card-001', 'content':'**Trigger:** Verified warning.\n**Action:** Clean warning.\n'
         '**Why:** Not proof construction.\n**Validate:** Both checks.\n**Avoid when:** Proof fails.'}]}))
    cases = tmp_path/'cases.json'
    cases.write_text(json.dumps({'schema_version':'card-routing-review-cases-v1',
        'bank_sha256': hashlib.sha256(bank.read_bytes()).hexdigest(), 'cases':[
            {'case_id':'warning', 'card_id':'card-001', 'state':'Verified with a warning.',
             'expected_applicability':'optional', 'rationale':'Already verified.'}]}))
    return bank, cases


def test_packet_binds_bank_and_keeps_review_unmeasured(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    bank, cases = inputs(tmp_path)
    before = bank.read_bytes(), cases.read_bytes()
    packet = prepare_review(bank, cases, tmp_path/'review')
    assert json.loads((tmp_path/'review/review.json').read_text()) == packet
    assert packet['index'] == ['- card-001: Verified warning.']
    assert packet['cases'][0]['card_content'] == json.loads(bank.read_text())['cards'][0]['content']
    assert all(value is None for value in packet['cases'][0]['review'].values())
    assert 'not a required read' in packet['caveat']
    assert before == (bank.read_bytes(), cases.read_bytes())


@pytest.mark.parametrize('mutation, message', [
    ('hash', 'different bank'), ('unknown', 'unknown review card'),
    ('duplicate', 'unique'), ('empty', 'unique'), ('verdict', 'applicability'),
    ('state', 'state and rationale'), ('schema', 'unsupported review cases'),
])
def test_invalid_case_packets_fail_before_output(tmp_path, monkeypatch, mutation, message):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    bank, cases = inputs(tmp_path)
    fixture = json.loads(cases.read_text())
    if mutation == 'hash': fixture['bank_sha256'] = 'bad'
    if mutation == 'unknown': fixture['cases'][0]['card_id'] = 'card-999'
    if mutation == 'duplicate': fixture['cases'] *= 2
    if mutation == 'empty': fixture['cases'] = []
    if mutation == 'verdict': fixture['cases'][0]['expected_applicability'] = 'must_read'
    if mutation == 'state': fixture['cases'][0]['state'] = ''
    if mutation == 'schema': fixture['schema_version'] = 'unknown'
    cases.write_text(json.dumps(fixture))
    with pytest.raises(ValueError, match=message):
        prepare_review(bank, cases, tmp_path/'review')
    assert not (tmp_path/'review').exists()


def test_review_output_must_be_a_fresh_run_child(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path/'run-root'))
    bank, cases = inputs(tmp_path)
    with pytest.raises(ValueError):
        prepare_review(bank, cases, tmp_path/'outside')
    assert not (tmp_path/'outside').exists()


def test_review_uses_actual_custom_description_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    bank, cases = inputs(tmp_path)
    seed = tmp_path/'seed.md';seed.write_text('Base skill\n')
    bundle = tmp_path/'bundle'
    manifest = build_bundle(bank, seed, bundle, autonomous_retrieval=True,
                            index_descriptions={'card-001':'Post-pass warning cleanup.'})
    packet = prepare_review(bank, cases, tmp_path/'review', bundle_path=bundle)
    assert packet['index'] == ['- card-001: Post-pass warning cleanup.']
    assert packet['cases'][0]['index_entry'] == packet['index'][0]
    assert packet['bundle_manifest'] == manifest
    data = json.loads((bundle/'cards.json').read_text())
    data['cards'][0]['content'] = 'Changed body'
    (bundle/'cards.json').write_text(json.dumps(data))
    with pytest.raises(ValueError, match='preserve the source bank'):
        prepare_review(bank, cases, tmp_path/'bad-review', bundle_path=bundle)
    assert not (tmp_path/'bad-review').exists()
