"""Offline structural and deployment checks; no provider calls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from skillopt_verusage import card_organization as organization


REPO = Path(__file__).resolve().parents[2]
DESIGN = REPO/'research_memory/projects/verus_self_evolving/experiments/20261011-trace2skill-card-organization'


def fixture():
    content = '\n'.join(f'**{field}:** Source {field}.' for field in organization.FIELDS)
    card = {'id': 'card-001', 'content': content}
    packet = {'bank_sha256': 'fixture', 'cards': [card], 'expected_card_ids': ['card-001']}
    family = {'family_id': 'family-one', 'title': 'Fixture family', 'include_when': ['Fixture condition'],
              'exclude_when': [], 'distinguish_from': []}
    case = {field: None for field in ('proof_object', 'goal_shape', 'observable_signal', 'required_premises',
                                     'repair_action', 'avoid_when', 'version_scope')}
    case.update(case_id='case-1', entry_states=['Fixture'], source_anchors=[{'field': 'Trigger', 'excerpt': 'Source Trigger.'}])
    proposal = {'schema_version': 'card-cluster-proposal-v2', 'status': 'candidate',
        'input_bank_sha256': 'fixture', 'families': [family],
        'card_features': [{'card_id': 'card-001', 'cases': [case]}],
        'assignments': [{'card_id': 'card-001', 'primary_family': 'family-one', 'primary_case_ids': ['case-1'],
                         'cross_links': [], 'rationale': 'Fixture source', 'needs_review': False}],
        'relations': [], 'review_items': [], 'blocking_errors': []}
    reduction = {'schema_version': 'card-family-reduction-v2', 'status': 'candidate',
        'input_bank_sha256': 'fixture', 'family_id': 'family-one',
        'rules': [{'rule_id': 'rule-one', 'title': 'Fixture rule', 'kind': 'verbatim',
                   'source_card_ids': ['card-001'], 'clauses': [], 'merge_rationale': 'Unique advice'}],
        'coverage': [{'card_id': 'card-001', 'rule_ids': ['rule-one'], 'disposition': 'retained_verbatim',
                      'preserved_distinctions': ['Fixture']}],
        'case_rule_map': [{'card_id': 'card-001', 'case_id': 'case-1', 'rule_ids': ['rule-one']}],
        'cross_links': [], 'review_items': [], 'blocking_errors': []}
    return packet, proposal, reduction


def test_frozen_repaired_bank():
    packet = organization.router_packet(REPO/'research_artifacts/deepseek-20261011/cards/repaired78.json',
                                       REPO/'skillopt-verusage/review/augmented78_revision.json')
    assert len(packet['cards']) == 78
    assert packet['bank_sha256'] == 'ae38b9ace8560cb7e819eb348d152b916b0486e206b3d09c1b862e8681517f27'


@pytest.mark.parametrize('fault', ['missing_card', 'duplicate_card', 'anchor', 'case', 'path', 'review'])
def test_router_rejects(fault):
    packet, proposal, _ = fixture()
    if fault == 'missing_card':
        proposal['assignments'] = []
    elif fault == 'duplicate_card':
        proposal['assignments'] *= 2
    elif fault == 'anchor':
        proposal['card_features'][0]['cases'][0]['source_anchors'][0]['excerpt'] = 'Invented'
    elif fault == 'case':
        proposal['assignments'][0]['primary_case_ids'] = ['absent']
    elif fault == 'path':
        proposal['families'][0]['family_id'] = '../escape'
    else:
        proposal['assignments'][0]['needs_review'] = True
    with pytest.raises(ValueError):
        organization.validate_router(proposal, packet)


@pytest.mark.parametrize('fault', ['missing_case', 'unrelated_rule', 'missing_coverage', 'verbatim_edit', 'bad_disposition'])
def test_reduction_rejects(fault):
    packet, proposal, reduction = fixture()
    request = organization.reduction_packets(proposal, packet)['family-one']
    if fault == 'missing_case':
        reduction['case_rule_map'] = []
    elif fault == 'unrelated_rule':
        reduction['rules'][0]['source_card_ids'] = ['card-999']
    elif fault == 'missing_coverage':
        reduction['coverage'] = []
    elif fault == 'verbatim_edit':
        reduction['rules'][0]['clauses'] = [{'text': 'Changed'}]
    else:
        reduction['coverage'][0]['disposition'] = 'merged'
    with pytest.raises(ValueError):
        organization.validate_reduction(reduction, request)


def test_render_and_reader(tmp_path):
    packet, proposal, reduction = fixture()
    root = tmp_path/'candidate'
    result = organization.render_bundle(proposal, packet, {'family-one': reduction},
        DESIGN/'templates/SKILL.md.tmpl', REPO/'skillopt-verusage/skills/initial.md', root)
    assert result['review_required'] and not result['evaluation_authorized']
    assert (root/'SKILL.md').read_bytes().startswith((REPO/'skillopt-verusage/skills/initial.md').read_bytes())
    reader = [sys.executable, str(root/'reference_read.py')]
    returned = json.loads(subprocess.check_output(reader + ['family-one'], cwd=tmp_path))
    assert packet['cards'][0]['content'] in returned['content']
    assert returned['source_card_ids'] == ['card-001']
    assert returned['sha256'] == hashlib.sha256(returned['content'].encode()).hexdigest()
    assert subprocess.run(reader + ['../escape'], capture_output=True).returncode == 2
    (root/'references/family-one.md').write_text('tampered')
    assert subprocess.run(reader + ['family-one'], capture_output=True).returncode != 0


def test_guarded_case_cross_link(tmp_path):
    packet, proposal, reduction = fixture()
    family = copy.deepcopy(proposal['families'][0])
    family['family_id'] = 'navigation-only'
    proposal['families'].append(family)
    proposal['assignments'][0]['cross_links'] = [{'family_id': 'navigation-only', 'case_ids': ['case-1'], 'when': 'Fixture'}]
    root = tmp_path/'candidate'
    organization.render_bundle(proposal, packet, {'family-one': reduction}, DESIGN/'templates/SKILL.md.tmpl',
                               REPO/'skillopt-verusage/skills/initial.md', root)
    assert '(family-one.md#rule-one)' in (root/'references/navigation-only.md').read_text()
    assert '(references/navigation-only.md)' in (root/'SKILL.md').read_text()
    manifest = json.loads((root/'reference_manifest.json').read_text())
    assert manifest['navigation-only']['source_card_ids'] == []


@pytest.mark.parametrize('fault', [None, 'missing_avoid', 'unsupported_source', 'lost_case', 'wrong_hash'])
def test_merged_claim_coverage(fault):
    packet, proposal, reduction = fixture()
    packet['cards'].append({**packet['cards'][0], 'id': 'card-002'})
    packet['expected_card_ids'].append('card-002')
    proposal['card_features'].append({**copy.deepcopy(proposal['card_features'][0]), 'card_id': 'card-002'})
    proposal['assignments'].append({**copy.deepcopy(proposal['assignments'][0]), 'card_id': 'card-002'})
    rule = reduction['rules'][0]
    rule.update(kind='merged', source_card_ids=['card-001', 'card-002'], clauses=[
        {'clause_id': f'clause-{number}', 'field': field, 'text': 'Source '+field+'.',
         'supporting_card_ids': ['card-001', 'card-002']} for number, field in enumerate(organization.FIELDS)])
    reduction['coverage'][0]['disposition'] = 'merged'
    reduction['coverage'].append({**copy.deepcopy(reduction['coverage'][0]), 'card_id': 'card-002'})
    reduction['case_rule_map'].append({**reduction['case_rule_map'][0], 'card_id': 'card-002'})
    request = organization.reduction_packets(proposal, packet)['family-one']
    if fault == 'missing_avoid':
        rule['clauses'].pop()
    elif fault == 'unsupported_source':
        rule['clauses'][0]['supporting_card_ids'] = ['card-999']
    elif fault == 'lost_case':
        reduction['case_rule_map'].pop()
    elif fault == 'wrong_hash':
        reduction['input_bank_sha256'] = 'wrong'
    if fault:
        with pytest.raises(ValueError):
            organization.validate_reduction(reduction, request)
    else:
        result = organization.validate_reduction(reduction, request)
        assert result['merged'] == 1 and result['source_cards'] == 2


def test_prepare_is_offline_and_frozen(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('build_organization_test', REPO/'scripts/build_card_organization.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    monkeypatch.setattr(module.GuardedDeepSeek, 'call', lambda *args, **kwargs: pytest.fail('Unexpected paid call'))
    root = module.output_root(tmp_path/'build')
    contract = module.prepare(root, 5)
    assert contract['model'] == 'deepseek-v4-pro'
    assert contract['reasoning_effort'] == 'max'
    assert contract['future_evaluation_episodes'] == 40
    assert not contract['evaluation_authorized']
    assert module.check_contract(root) == contract
    (root/'router_input.json').write_text('{}')
    with pytest.raises(ValueError, match='Frozen run input'):
        module.check_contract(root)
    with pytest.raises(ValueError, match='external run root'):
        module.output_root(tmp_path)


def test_env_model_does_not_override_pro_max(tmp_path):
    spec = importlib.util.spec_from_file_location('build_organization_env_test', REPO/'scripts/build_card_organization.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    env = tmp_path/'fixture.env'
    env.write_text('DEEPSEEK_API_KEY=fixture\nDEEPSEEK_MODEL=other\nDEEPSEEK_BASE_URL=https://api.deepseek.com\n')
    provider = module.client(tmp_path, env, {'budget_usd': 5})
    payload = provider.payload(system='Fixture', user='{}', effort='max')
    assert payload['model'] == 'deepseek-v4-pro' and payload['reasoning'] == {'effort': 'max'}
    env.write_text('DEEPSEEK_API_KEY=fixture\nDEEPSEEK_BASE_URL=https://invalid.example\n')
    with pytest.raises(ValueError, match='unexpected endpoint'):
        module.client(tmp_path, env, {'budget_usd': 5})


def test_retry_carries_prior_spend_and_freezes_evidence(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('build_organization_retry_test', REPO/'scripts/build_card_organization.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    first = tmp_path/'first'
    module.prepare(first, 5)
    (first/'budget.json').write_text(json.dumps({'approval_limit_usd': 5, 'prior_spend_usd': 0,
        'reservations': {}, 'uncertain_requests': 0, 'target_spend_usd': .3}))
    (first/'provider_calls.jsonl').write_text(json.dumps({'attempts': [{'estimated_cost_usd': .3}]})+'\n')
    second = tmp_path/'second'
    contract = module.prepare(second, 5, first, 131072)
    assert contract['prior_spend_usd'] == .3 and contract['budget_usd'] == 5
    assert contract['output_caps']['router'] == 131072
    assert module.check_contract(second) == contract
    (first/'budget.json').write_text('{}')
    with pytest.raises(ValueError, match='Prior attempt evidence changed'):
        module.check_contract(second)
