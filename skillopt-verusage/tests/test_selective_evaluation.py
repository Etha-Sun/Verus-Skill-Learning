"""Zero-API evaluation checks: real payloads, budgets, reporting and frozen matrix."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def evaluation(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / 'scripts'))
    return importlib.import_module('evaluate_selective_references')


@pytest.fixture
def bundle():
    path = Path(__file__).resolve().parents[3] / 'verus_skill_runs/skillopt-verusage/card-organization-20261013-selective-v2/candidate'
    if not path.exists():
        pytest.skip('Reviewed local candidate unavailable')
    return path


@pytest.fixture
def reader(bundle):
    spec = importlib.util.spec_from_file_location('selective_eval_reader', bundle / 'reference_read.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def events(path, outputs):
    rows = [{'type': 'item.completed', 'item': {'type': 'command_execution', 'id': str(index),
            'command': command, 'aggregated_output': output, 'exit_code': 0}}
            for index, (command, output) in enumerate(outputs)]
    path.write_text('\n'.join(json.dumps(row) for row in rows))


def test_index_never_counts_as_body_and_multiselect_counts_once(evaluation, bundle, reader, tmp_path):
    family = 'direct-existing-lemma-bridge'
    index = reader.retrieve(bundle, family)
    body = reader.retrieve(bundle, family, ['original-card-003', 'original-card-043'])
    path = tmp_path / 'events.jsonl'
    events(path, [('python3 reference_read.py family', json.dumps(index)),
                  ('python3 reference_read.py family --rules selected', json.dumps(body)),
                  ('ls references', 'file names'), ('cat references/family.md', 'partial text')])
    result = evaluation.audit_events(path, bundle)
    assert result['reference_read_calls'] == result['reference_directory_calls'] == 1
    assert result['helper_selected_rule_calls'] == 1
    assert result['exposed_source_card_ids'] == ['card-003', 'card-043']
    assert result['helper_directory_visits_with_later_helper_body'] == 1
    assert result['helper_body_content_bytes'] == body['bytes']
    assert len(result['direct_reference_commands']) == 2
    assert result['directory_to_any_body_conversion_requires_manual_audit']
    assert not result['reader_errors_or_invalid_payloads']


def test_same_command_multiple_payloads_and_index_abandonment(evaluation, bundle, reader, tmp_path):
    family = 'direct-existing-lemma-bridge'
    path = tmp_path / 'events.jsonl'
    index = reader.retrieve(bundle, family)
    body = reader.retrieve(bundle, family, full=True)
    events(path, [('python3 reference_read.py family; python3 reference_read.py family --full',
                   json.dumps(index) + '\n' + json.dumps(body)),
                  ('python3 reference_read.py family', json.dumps(index))])
    result = evaluation.audit_events(path, bundle)
    assert result['helper_directory_visits_with_later_helper_body'] == 1
    assert result['helper_directory_visits_without_later_helper_body'] == 1
    assert result['helper_command_count'] == 2
    assert result['helper_full_fallback_calls'] == 1


@pytest.mark.parametrize('fault', ['body', 'sha', 'source_cards', 'rules', 'operation', 'body_flag'])
def test_payload_not_matching_frozen_content_is_not_counted(evaluation, bundle, reader, tmp_path, fault):
    payload = reader.retrieve(bundle, 'direct-existing-lemma-bridge', ['original-card-003'])
    if fault == 'body':
        payload['content'] += 'fabricated'
    elif fault == 'sha':
        payload['sha256'] = 'bad'
    elif fault == 'source_cards':
        payload['source_card_ids'] = ['card-043']
    elif fault == 'rules':
        payload['rule_ids'] = ['original-card-043']
    elif fault == 'operation':
        payload['operation'] = 'index'
    else:
        payload['body_read'] = False
    path = tmp_path / 'events.jsonl'
    events(path, [('python3 reference_read.py family', json.dumps(payload))])
    result = evaluation.audit_events(path, bundle)
    assert result['reference_read_calls'] == result['reference_directory_calls'] == 0
    assert len(result['reader_errors_or_invalid_payloads']) == 1


def test_every_real_C_reader_mode_validates_against_frozen_package(evaluation, bundle, reader):
    references = json.loads((bundle / 'reference_manifest.json').read_text())
    for family, entry in references.items():
        evaluation.expected_payload(bundle, reader.retrieve(bundle, family))
        evaluation.expected_payload(bundle, reader.retrieve(bundle, family, full=True))
        for rule in entry['rules']:
            evaluation.expected_payload(bundle, reader.retrieve(bundle, family, [rule]))
        evaluation.expected_payload(bundle, reader.retrieve(bundle, family, list(entry['rules'])))


def test_legacy_B_full_payload_and_failed_reader(evaluation, bundle, tmp_path):
    control = bundle.parent / 'control'
    family = 'direct-existing-lemma-bridge'
    entry = json.loads((control / 'reference_manifest.json').read_text())[family]
    payload = {'reference_retrieval': 1, 'operation': 'read', 'id': family,
               'source_card_ids': entry['source_card_ids'], 'content': (control / entry['path']).read_text(),
               'bytes': entry['bytes'], 'sha256': entry['sha256']}
    path = tmp_path / 'events.jsonl'
    events(path, [('python3 reference_read.py family', json.dumps(payload)),
                  ('python3 reference_read.py invalid', json.dumps({'reference_retrieval': 1, 'error': 'unknown reference id'}))])
    result = evaluation.audit_events(path, control)
    assert result['reference_read_calls'] == 1 and result['reference_directory_calls'] == 0
    assert len(result['reader_errors_or_invalid_payloads']) == 1


def test_shared_new_thirty_dollar_cap_and_unknown_cost(evaluation, tmp_path):
    first = evaluation.guard(tmp_path)
    reservation = first.reserve(29, wait_timeout_seconds=0)
    second = evaluation.guard(tmp_path)
    with pytest.raises(RuntimeError):
        second.reserve(2, wait_timeout_seconds=0)
    first.settle(reservation, cost_usd=None, usage=None)
    with pytest.raises(RuntimeError, match='Unknown provider cost'):
        evaluation.BudgetMux([second]).reserve(1)
    state = evaluation.prior.read(tmp_path / 'budget.json')
    assert state['prior_spend_usd'] == 0 and state['approval_limit_usd'] == 30
    assert state['uncertain_spend_usd'] == 29


def test_paired_resources_do_not_impute_incomplete_billing(evaluation):
    rows = []
    for ident in ('first', 'second'):
        for condition in ('old', 'revised'):
            rows.append({'task_id': ident, 'condition': condition,
                         'budgeted_dual_pass': condition == 'revised',
                         'settled_provider_complete': not (ident == 'second' and condition == 'revised'),
                         **{field: 2 if condition == 'revised' else 1 for field in evaluation.FIELDS}})
    result = evaluation.paired_summary(rows)
    assert result['complete_task_pairs'] == 2 and result['complete_billing_pairs'] == 1
    assert result['complete_billing_totals']['revised']['prompt_tokens'] == 2
    assert result['bootstrap_C_minus_B']['budgeted_dual_pass']['n'] == 2
    assert result['bootstrap_C_minus_B']['prompt_tokens']['n'] == 1
    duplicate = copy.deepcopy(rows)
    duplicate.append(rows[0])
    with pytest.raises(ValueError, match='Duplicate'):
        evaluation.paired_summary(duplicate)
