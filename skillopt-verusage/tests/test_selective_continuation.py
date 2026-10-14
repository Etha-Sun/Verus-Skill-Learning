import copy
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def continuation(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / 'scripts'))
    return importlib.import_module('continue_selective_evaluation')


@pytest.fixture
def records():
    root = Path(__file__).resolve().parents[3] / 'verus_skill_runs/skillopt-verusage/selective-reference-evaluation-20261013-v1'
    if not (root / 'summary.json').exists():
        pytest.skip('Local frozen interrupted run unavailable')
    return json.loads((root / 'validation_contract.json').read_text()), json.loads((root / 'summary.json').read_text())


def test_exact_schedule_preserves_normal_timeouts(continuation, records):
    parent, summary = records
    jobs, retained = continuation.plan_remaining(parent, summary)
    keys = {continuation.evaluation.prior.driver.episode_key(job) for job in jobs}
    original = {entry['row']['bridge_task_key'] for entry in summary['rows']}
    assert len(jobs) == 15
    assert len(retained) == 25
    assert keys & original == continuation.RETRY_KEYS
    assert not keys & set(retained)
    assert len(keys | set(retained)) == 40
    for entry in summary['rows']:
        if entry['row']['timed_out']:
            assert entry['row']['bridge_task_key'] in retained


@pytest.mark.parametrize('change', [{'timed_out': True}, {'proof_solved': True}, {'codex_returncode': 0}])
def test_rejects_outcome_selected_retry(continuation, records, change):
    parent, original = records
    summary = copy.deepcopy(original)
    row = next(entry['row'] for entry in summary['rows']
               if entry['row']['bridge_task_key'] == 'dev_old--6a7283f1b8a3f1d862db')
    row.update(change)
    with pytest.raises(Exception):
        continuation.plan_remaining(parent, summary)


def test_rejects_live_parent(continuation, records):
    parent, original = records
    summary = copy.deepcopy(original)
    summary['bridge_drained'] = False
    with pytest.raises(Exception):
        continuation.plan_remaining(parent, summary)


def test_merge_preserves_retained_and_replaces_exactly(continuation, records):
    parent, summary = records
    jobs, retained = continuation.plan_remaining(parent, summary)
    keys = {continuation.evaluation.prior.driver.episode_key(job) for job in jobs}
    replacements = [{'row': {'bridge_task_key': key}} for key in keys]
    merged = continuation.evaluation.continuation.merge_selected(summary['rows'], replacements, retained, keys)
    assert len(merged) == 40
    for entry in summary['rows']:
        key = entry['row']['bridge_task_key']
        if key in retained:
            assert merged[key] is entry
    assert continuation.inherited_charge({'prior_spend_usd': 0, 'target_spend_usd': 2.062757664,
        'uncertain_spend_usd': 1.83904512, 'reservations': {}}) == pytest.approx(3.901802784)
