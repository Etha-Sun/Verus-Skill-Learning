import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location('success_statistics',
    Path(__file__).resolve().parents[1] / 'scripts/summarize_success_timeout_tokens.py')
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


def test_outcomes_preserve_timeout_even_if_final_dual_pass():
    row = dict(provider_valid=True, proof_solved=True, safety_passed=True,
               within_budget=False, timed_out=True)
    assert stats.bucket(row) == 'timeout'
    assert stats.bucket(dict(row, provider_valid=False)) == 'invalid'
    assert stats.bucket(dict(row, within_budget=True, timed_out=False)) == 'success'
    assert stats.bucket(dict(row, timed_out=False)) == 'normal_unsolved'


def test_distribution_has_per_trace_mean_median_and_linear_percentiles():
    d = stats.distribution([100, 10, 20, 30])
    assert d['mean'] == 40
    assert d['median'] == 25
    assert d['p25'] == 17.5
    assert d['p90'] == pytest.approx(79)
    assert stats.distribution([]) == {'n': 0, 'sum': 0}


def test_joint_success_pairs_same_task_and_repeat_only():
    def row(arm, repeat, outcome, value):
        return dict(condition=arm, task_id='a', repeat=repeat, outcome=outcome,
                    **dict.fromkeys((*stats.FIELDS, 'total_tokens', 'actor_seconds'), value))
    rows = [row('old', 0, 'success', 10), row('new', 0, 'success', 20),
            row('old', 1, 'timeout', 100), row('new', 1, 'success', 200)]
    result = stats.joint_pairs(rows, 'old', 'new')
    assert result['n'] == 1 and result['task_n'] == 1
    assert result['metrics']['total_tokens']['sum_change_pct'] == 100
    with pytest.raises(AssertionError):
        stats.joint_pairs(rows + [rows[0]], 'old', 'new')
    with pytest.raises(AssertionError):
        stats.joint_pairs(rows[:-1], 'old', 'new')
