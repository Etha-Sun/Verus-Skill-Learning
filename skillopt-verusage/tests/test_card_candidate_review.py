"""Review fallback preserves source bodies and all applicability case routes."""
import copy
import importlib.util
from pathlib import Path

import pytest

from test_card_organization import fixture
from skillopt_verusage import card_organization as organization


@pytest.fixture
def finalizer(monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('finalize_candidate_test', scripts/'finalize_card_candidate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def merged_fixture():
    packet, router, proposal = fixture()
    second = copy.deepcopy(packet['cards'][0])
    second['id'] = 'card-002'
    packet['cards'].append(second)
    for field in ('card_features', 'assignments'):
        item = copy.deepcopy(router[field][0])
        item['card_id'] = 'card-002'
        router[field].append(item)
    request = organization.reduction_packets(router, packet)['family-one']
    rule = proposal['rules'][0]
    rule['kind'] = 'merged'
    rule['source_card_ids'] = ['card-001', 'card-002']
    rule['clauses'] = [{'clause_id': f'clause-{position}', 'field': field, 'text': f'Source {field}.',
                       'supporting_card_ids': rule['source_card_ids']} for position, field in enumerate(organization.FIELDS)]
    proposal['coverage'][0]['disposition'] = 'merged'
    for field in ('coverage', 'case_rule_map'):
        proposal[field].append({**proposal[field][0], 'card_id': 'card-002'})
    return request, proposal


def test_fallback_preserves_cases_and_original_proposal(finalizer):
    packet, proposal = merged_fixture()
    before = copy.deepcopy(proposal)
    value = finalizer.retain_originals(proposal, packet,
        {'rule_ids': ['rule-one'], 'issue': 'Distinct obligations.', 'required_check': 'Review the separate originals.'})
    assert proposal == before
    assert value['status'] == 'needs_review'
    assert len(value['rules']) == 2 and all(rule['kind'] == 'verbatim' for rule in value['rules'])
    assert {item['card_id'] for item in value['case_rule_map']} == {'card-001', 'card-002'}
    assert all(item['rule_ids'] == [f"original-{item['card_id']}"] for item in value['case_rule_map'])
    organization.validate_reduction(value, packet)


def test_stale_rule_review_rejected(finalizer):
    packet, proposal = merged_fixture()
    with pytest.raises(ValueError):
        finalizer.retain_originals(proposal, packet,
            {'rule_ids': ['missing'], 'issue': 'Fixture', 'required_check': 'Fixture'})
