"""Saved router normalization cannot repair or rewrite semantic claims."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

from test_card_organization import fixture
from skillopt_verusage import card_organization as organization


@pytest.fixture
def normalizer(monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('adopt_router_test', scripts/'adopt_card_router.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_format_conversion_preserves_source(normalizer):
    packet, canonical, _ = fixture()
    raw = copy.deepcopy(canonical)
    raw['card_features'][0]['cases'][0]['source_anchors'][0]['field'] = 'trigger'
    for field in ('card_features', 'assignments'):
        raw[field] = {row['card_id']: row for row in raw[field]}
    before = copy.deepcopy(raw)
    normalized, changes = normalizer.normalize(raw)
    assert normalized == canonical and raw == before
    assert len(changes) == 3
    organization.validate_router(normalized, packet)
    assert normalizer.normalize(normalized) == (normalized, [])


def test_reject_mismatched_object_key(normalizer):
    _, proposal, _ = fixture()
    proposal['assignments'] = {'wrong-id': proposal['assignments'][0]}
    with pytest.raises(ValueError, match='key/card_id'):
        normalizer.normalize(proposal)


def test_does_not_repair_unsupported_anchor(normalizer):
    packet, proposal, _ = fixture()
    proposal['card_features'][0]['cases'][0]['source_anchors'][0]['excerpt'] = 'Invented advice'
    normalized, _ = normalizer.normalize(proposal)
    with pytest.raises(ValueError, match='anchor not in source'):
        organization.validate_router(normalized, packet)


def test_unknown_field_rejected(normalizer):
    _, proposal, _ = fixture()
    proposal['card_features'][0]['cases'][0]['source_anchors'][0]['field'] = 'premise'
    with pytest.raises(ValueError, match='Unknown source field'):
        normalizer.normalize(proposal)


def test_offline_adoption_pins_source_and_carries_cost(normalizer, tmp_path, monkeypatch):
    builder = normalizer.builder
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    monkeypatch.setattr(builder.GuardedDeepSeek, 'call', lambda *args, **kwargs: pytest.fail('Unexpected API call'))
    source = tmp_path/'source'
    builder.prepare(source, 5)
    packet = json.loads((source/'router_input.json').read_text())
    _, proposal, _ = fixture()
    feature_template = proposal['card_features'][0]
    assignment_template = proposal['assignments'][0]
    proposal['input_bank_sha256'] = packet['bank_sha256']
    proposal['card_features'] = {}
    proposal['assignments'] = {}
    for card in packet['cards']:
        feature = copy.deepcopy(feature_template)
        feature['card_id'] = card['id']
        feature['cases'][0]['source_anchors'] = [{'field': 'trigger',
            'excerpt': organization.source_field(card['content'], 'Trigger')}]
        proposal['card_features'][card['id']] = feature
        proposal['assignments'][card['id']] = {**assignment_template, 'card_id': card['id']}
    (source/'proposals').mkdir()
    original = source/'proposals/router.json'
    original.write_text(json.dumps(proposal))
    original_bytes = original.read_bytes()
    (source/'budget.json').write_text(json.dumps({'approval_limit_usd': 5, 'prior_spend_usd': .3,
        'reservations': {}, 'uncertain_requests': 0, 'target_spend_usd': .29}))
    (source/'provider_calls.jsonl').write_text(json.dumps({'attempts': [{'estimated_cost_usd': .29}]})+'\n')
    destination = tmp_path/'adopted'
    audit = normalizer.adopt(source, destination)
    contract = builder.check_contract(destination)
    assert contract['prior_spend_usd'] == pytest.approx(.59)
    assert not audit['semantic_edits'] and audit['model_calls'] == 0
    assert original.read_bytes() == original_bytes
    assert audit['validation']['cards'] == 78
    original.write_text('{}')
    with pytest.raises(ValueError, match='Prior attempt evidence changed'):
        builder.check_contract(destination)
