"""Offline continuation scope and settled-result classification checks."""
import copy
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def continuation(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/'scripts'))
    return importlib.import_module('continue_card_organization_evaluation')


def fixture_matrix(module):
    tasks = ['9b9f6ccef89db4103c7f'] + [f'task-{index}' for index in range(19)]
    schedule = [{'condition': condition, 'id': ident} for ident in tasks for condition in ('old', 'revised')]
    rows = [{'condition': job['condition'], 'row': {
        'bridge_task_key': module.evaluation.driver.episode_key(job), 'id': job['id'],
        'timed_out': False, 'proof_solved': True, 'codex_returncode': 0, 'fidelity': 'V2_TRACE'}} for job in schedule[:25]]
    rows[0]['row'].update(proof_solved=False, codex_returncode=1, fidelity='V0_INVALID')
    rows[2]['row'].update(proof_solved=False, timed_out=True, fidelity='V1_TRUNCATED')
    rows[3]['row']['fidelity'] = 'V0_INVALID'
    return {'schedule': schedule}, {'rows': rows, 'bridge_drained': True, 'reviewed_inputs_unchanged': True}


def test_only_missing_and_authorized_abort_selected(continuation):
    contract, summary = fixture_matrix(continuation)
    before = copy.deepcopy(summary)
    jobs = continuation.plan_remaining(contract, summary)
    assert len(jobs) == 16
    assert continuation.evaluation.driver.episode_key(jobs[0]) == continuation.RETRY_KEY
    assert jobs[1:] == contract['schedule'][25:]
    assert summary == before


@pytest.mark.parametrize('change', ['timeout', 'solved', 'undrained', 'duplicates'])
def test_rejects_unapproved_retry_selection(continuation, change):
    contract, summary = fixture_matrix(continuation)
    if change == 'timeout':
        summary['rows'][0]['row']['timed_out'] = True
    elif change == 'solved':
        summary['rows'][0]['row']['proof_solved'] = True
    elif change == 'undrained':
        summary['bridge_drained'] = False
    else:
        summary['rows'][-1] = summary['rows'][0]
    with pytest.raises(ValueError):
        continuation.plan_remaining(contract, summary)


def test_merge_replaces_only_predeclared_cell(continuation):
    contract, summary = fixture_matrix(continuation)
    jobs = continuation.plan_remaining(contract, summary)
    retained = {entry['row']['bridge_task_key'] for entry in summary['rows']} - {continuation.RETRY_KEY}
    allowed = {continuation.evaluation.driver.episode_key(job) for job in jobs}
    replacement = copy.deepcopy(summary['rows'][0])
    replacement['row']['proof_solved'] = True
    merged = continuation.merge_selected(summary['rows'], [replacement], retained, allowed)
    assert len(merged) == 25
    assert merged[continuation.RETRY_KEY]['row']['proof_solved']
    assert not summary['rows'][0]['row']['proof_solved']
    with pytest.raises(ValueError):
        continuation.merge_selected(summary['rows'], [summary['rows'][1]], retained, allowed)


@pytest.mark.parametrize('kind', ['late_error_timeout', 'bridge_abort', 'editing_violation'])
def test_classification_keeps_dimensions_separate(continuation, tmp_path, kind):
    (tmp_path/'fidelity_audit.json').write_text(json.dumps({'shell_edit_suspect_count': int(kind == 'editing_violation')}))
    (tmp_path/'codex_events.raw.jsonl').write_text('Provider bridge halted pending review' if kind == 'bridge_abort' else '')
    result = {'condition': 'revised', 'episode': str(tmp_path),
        'row': {'id': 'fixture', 'timed_out': kind == 'late_error_timeout',
                'codex_returncode': 0 if kind == 'editing_violation' else 1,
                'proof_solved': kind == 'editing_violation', 'safety_passed': True,
                'within_budget': kind != 'late_error_timeout', 'fidelity': 'V0_INVALID',
                'actor_wall_seconds': 600 if kind == 'late_error_timeout' else 200,
                'provider_valid': True},
        'settled_usage': {'requests': 2, 'prompt_cache_hit_tokens': 100,
                         'prompt_cache_miss_tokens': 100, 'completion_tokens': 100,
                         'unmetered_requests': int(kind == 'late_error_timeout')}, 'retrieval': {}}
    row = continuation.result_dimensions(result)
    if kind == 'late_error_timeout':
        assert row['outcome'] == 'timeout'
        assert not row['settled_provider_complete']
        assert row['recorded_provider_valid']
    elif kind == 'bridge_abort':
        assert row['outcome'] == 'infrastructure_aborted'
    else:
        assert row['outcome'] == 'budgeted_dual_pass'
        assert row['editing_protocol_violation']
    assert row['uniform_off_peak_estimated_usd'] == pytest.approx(.0002662)
