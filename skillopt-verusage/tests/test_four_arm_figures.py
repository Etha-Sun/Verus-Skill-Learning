import importlib
from pathlib import Path

import pytest


@pytest.fixture
def figures(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / 'scripts'))
    return importlib.import_module('plot_four_arm_evaluation')


def row(index, condition, passed=True):
    return dict(task_id=str(index), condition=condition, passed=passed, usage_complete=True,
                prompt_tokens=100, completion_tokens=10, actor_seconds=20,
                estimated_cost_usd=.01, uniform_usd=.01)


def test_joint_pairs_and_incomplete_costs(figures):
    rows = [row(index, condition) for index in range(20) for condition in ('old', 'revised')]
    rows[0]['usage_complete'] = False
    rows[2]['passed'] = False
    result = figures.paired(rows)
    assert result['complete_billing_pairs']['n'] == 19
    assert result['joint_success']['n'] == 18
    assert result['success_delta_pp'] == 5
    assert result['wins'] == ['1']
    assert result['complete_billing_pairs']['metrics']['prompt_tokens']['percent_change'] == 0


def test_rejects_incomplete_matrix(figures):
    with pytest.raises(AssertionError):
        figures.paired([row(0, 'old')])


def test_rejects_duplicate_cell(figures):
    with pytest.raises(AssertionError):
        figures.paired([row(0, 'old'), row(0, 'old')])


def test_timeout_is_not_success(figures):
    entry = dict(condition='old', episode='example',
        row=dict(id='one', proof_solved=True, safety_passed=True, within_budget=False,
                 timed_out=True, provider_valid=True, fidelity='V1_TRUNCATED', actor_wall_seconds=600),
        settled_usage=dict(requests=1, prompt_tokens=100, completion_tokens=10,
                           prompt_cache_hit_tokens=80, prompt_cache_miss_tokens=20, estimated_cost_usd=.1),
        retrieval=dict(reference_directory_calls=1))
    result = figures.normalize(entry, 1)
    assert not result['passed']
    assert result['body_reads'] == 0
    assert result['directory_reads'] == 1


def test_two_table_report_matches_reviewed_matrix(figures):
    import csv
    import json
    base = Path(__file__).resolve().parents[3] / 'verus_skill_runs/skillopt-verusage'
    data = base / 'four-arm-evaluation-20261014/episodes.csv'
    contract = base / 'selective-reference-evaluation-20261013-v2/validation_contract.json'
    if not data.exists() or not contract.exists():
        pytest.skip('Reviewed local matrix unavailable')
    with data.open() as handle:
        rows = list(csv.DictReader(handle))
    for record in rows:
        record['round'] = int(record['round'])
        for field in ('passed', 'strict_pass', 'timed_out'):
            record[field] = record[field] == 'True'
    names = {item['id']: item['task_id'] for item in json.loads(contract.read_text())['items']}
    report = figures.comparison_report(rows, names)
    assert report.index("## Shared Setup: Yuechun's Recommended Baseline") < report.index('## Table 1')
    assert '## A/B/C Variants' in report
    assert 'R1-B and R2-B have identical skill-package hashes' in report
    assert 'combined reading-interface and navigation intervention' in report
    assert report.count('## Table') == 2
    assert '| R1-B Whole-reference reading | 13 | 1 | 0 |' in report
    assert '| R2-B Whole-reference reading | 12 | 2 | 1 |' in report
    assert '| R2-C Selective reading | 11 | 3 | 2 |' in report
    assert '| `delegation_map::impl4::new` | ✗ | ✓ | ✓ | ✓ |' in report
    assert '10 were solved by all four arms, and 4 timed out in all four arms' in report
    assert not any('\u4e00' <= character <= '\u9fff' for character in report)
