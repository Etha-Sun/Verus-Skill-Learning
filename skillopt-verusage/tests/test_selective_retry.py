import importlib
from pathlib import Path

import pytest


@pytest.fixture
def retry(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / 'scripts'))
    return importlib.import_module('retry_selective_interruption')


def interrupted(retry):
    return {'bridge_task_key': retry.KEY, 'codex_returncode': -9,
            'timed_out': False, 'proof_solved': False}


@pytest.mark.parametrize('change', [{'timed_out': True}, {'proof_solved': True},
                                  {'codex_returncode': 1}, {'bridge_task_key': 'another'}])
def test_rejects_non_authorized_cases(retry, change):
    row = interrupted(retry)
    row.update(change)
    with pytest.raises(Exception):
        retry.validate_interruption(row)


def test_selects_replacement_even_if_unsolved(retry):
    original = [{'row': interrupted(retry)}] + [
        {'row': {'bridge_task_key': f'other-{index}'}} for index in range(39)]
    replacement = [{'row': {**interrupted(retry), 'codex_returncode': 0}}]
    merged = retry.merge_rows(original, replacement)
    assert len(merged) == 40
    assert merged[0] is replacement[0]
    assert merged[1:] == original[1:]
    assert original[0]['row']['codex_returncode'] == -9


def test_rejects_duplicate_matrix(retry):
    with pytest.raises(Exception):
        retry.merge_rows([{'row': interrupted(retry)}] * 40,
                         [{'row': interrupted(retry)}])
