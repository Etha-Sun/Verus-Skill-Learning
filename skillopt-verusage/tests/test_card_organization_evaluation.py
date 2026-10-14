"""No-provider checks of the fixed paired evaluation wiring."""
from contextlib import contextmanager
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def evaluation(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/'scripts'))
    return importlib.import_module('evaluate_card_organization')


def test_reference_audit_separates_exposure_and_direct_access(evaluation, tmp_path):
    content = 'One proof rule'
    payload = {'reference_retrieval': 1, 'operation': 'read', 'id': 'family',
               'content': content, 'bytes': len(content), 'source_card_ids': ['card-001'],
               'sha256': hashlib.sha256(content.encode()).hexdigest()}
    commands = [('python reference_read.py family', json.dumps(payload)),
                ('head references/family.md', 'partial rule'),
                ('cat SKILL.md', 'index only')]
    events = [{'type': 'item.completed', 'item': {'type': 'command_execution', 'command': command,
               'aggregated_output': output, 'exit_code': 0}} for command, output in commands]
    path = tmp_path/'events.jsonl'
    path.write_text('\n'.join(json.dumps(event) for event in events))
    result = evaluation.audit(path)
    assert result['read_calls'] == 0
    assert result['reference_read_calls'] == 1
    assert result['reference_events'][0]['payload_integrity_valid']
    assert result['exposed_source_card_ids'] == ['card-001']
    assert len(result['direct_reference_commands']) == 1


@pytest.mark.parametrize('invalid', [False, True])
def test_fixed_runner_shared_parameters_and_no_retry(evaluation, tmp_path, monkeypatch, invalid):
    driver = evaluation.driver
    calls = []
    marker = object()
    root = tmp_path/'run'
    root.mkdir()
    source = tmp_path/'input.rs'
    source.write_text('fixture')
    config = {'repo': str(tmp_path), 'source_root': str(tmp_path/'runtime'),
              'rust_root': str(tmp_path/'rust'), 'scratch_root': str(tmp_path),
              **{name: str(tmp_path/name) for name in ('codex_bin', 'verus_bin', 'lynette_bin')}}
    items = [{'id': str(index), 'source_path': source.name, 'directory_group': 'group',
              'source_sha256': driver.sha(source)} for index in range(20)]
    contract = {'items': items, 'input_hashes': {}, 'installed_library_root': str(tmp_path/'vstd'),
                'installed_library_conditions': ['old', 'revised'], 'model': 'deepseek-v4-pro',
                'bundle_paths': {name: str(tmp_path/name) for name in ('old', 'revised')},
                'artifacts': {name: {'artifact_sha256': name} for name in ('old', 'revised')},
                'schedule': [{'id': item['id'], 'condition': condition} for item in items
                             for condition in ('old', 'revised')], 'caveat': 'test'}
    @contextmanager
    def bridge(config, root, *, budget_guard):
        assert budget_guard is marker
        ledger = root/'provider_calls.jsonl'
        ledger.touch()
        yield SimpleNamespace(ledger_path=ledger, halted_error=None), 'http://127.0.0.1:1', root/'manifest.json'
    def task(**kwargs):
        calls.append(kwargs)
        kwargs['out_dir'].mkdir()
        return {'bridge_task_key': kwargs['bridge_task_key'], 'proof_solved': True,
                'fidelity': 'test', 'provider_valid': not invalid}
    monkeypatch.setattr(driver, 'bridge', bridge)
    monkeypatch.setattr(driver, 'run_task', task)
    monkeypatch.setattr(driver, '_bridge_usage', lambda *args: {})
    monkeypatch.setattr(driver, 'export_transcript', lambda *args: {'completeness': 'test'})
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'not-a-real-key')
    monkeypatch.setenv('VERUS_SKILL_DATA_ROOT', str(tmp_path/'forbidden'))
    if invalid:
        with pytest.raises(RuntimeError, match='stopped'):
            driver.run(config, root, contract, expected_episodes=40, budget_guard=marker,
                       retrieval_auditor=lambda path: {'audited': True})
        assert len(calls) == 2
    else:
        driver.run(config, root, contract, expected_episodes=40, budget_guard=marker,
                   retrieval_auditor=lambda path: {'audited': True})
        assert len(calls) == 40
        assert len({entry['bridge_task_key'] for entry in calls}) == 40
    for entry in calls:
        assert entry['installed_library_root'] == tmp_path/'vstd'
        assert entry['timeout_seconds'] == 600
        assert entry['model_context_window'] == 1048576
        assert entry['reasoning_effort'] == 'max'
        assert entry['model'] == 'deepseek-v4-pro'
        assert entry['reference_proof_source'] is None
        assert entry['actor_isolation_rust_root'] == tmp_path/'rust'


def test_review_gate_rejects_wrong_hash(evaluation, tmp_path):
    contract = tmp_path/'contract.json'
    receipt = tmp_path/'receipt.json'
    contract.write_text('{}')
    receipt.write_text(json.dumps({'decision': 'APPROVE', 'contract_sha256': 'wrong'}))
    with pytest.raises(ValueError):
        evaluation.driver.check_review(receipt, contract)


def test_unknown_cost_blocks_next_dispatch(evaluation, tmp_path):
    guard = evaluation.guard(tmp_path)
    reservation = guard.reserve(1, wait_timeout_seconds=0)
    guard.settle(reservation, cost_usd=None, usage=None)
    with pytest.raises(RuntimeError, match='Unknown provider cost'):
        evaluation.BudgetMux([guard]).reserve(1)


def test_cap_is_shared_and_excludes_construction(evaluation, tmp_path):
    first = evaluation.guard(tmp_path)
    reservation = first.reserve(19, wait_timeout_seconds=0)
    second = evaluation.guard(tmp_path)
    with pytest.raises(RuntimeError):
        second.reserve(2, wait_timeout_seconds=0)
    first.settle(reservation, cost_usd=19, usage={})
    with pytest.raises(RuntimeError, match='exceeds'):
        second.reserve(2, wait_timeout_seconds=0)
    assert json.loads((tmp_path/'budget.json').read_text())['prior_spend_usd'] == 0


@pytest.mark.parametrize('invalid', [False, True])
def test_summary_keeps_timeout_and_invalid_separate(evaluation, tmp_path, invalid):
    evaluation.guard(tmp_path)
    results = []
    for condition in ('old', 'revised'):
        solved = condition == 'old'
        results.append({'condition': condition,
            'row': {'id': 'fixture-task', 'provider_valid': solved or not invalid,
                    'proof_solved': solved, 'safety_passed': True, 'within_budget': solved,
                    'timed_out': not solved, 'actor_wall_seconds': 12 if solved else 600},
            'settled_usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'reasoning_tokens': 15,
                             'estimated_cost_usd': .01},
            'retrieval': {'read_calls': 0, 'reference_read_calls': 1 if not solved else 0}})
    (tmp_path/'summary.json').write_text(json.dumps({'rows': results, 'caveat': 'fixture'}))
    evaluation.summarize(tmp_path)
    result = json.loads((tmp_path/'statistics.json').read_text())
    assert result['completed_episodes'] == 2
    assert result['expected_episodes'] == 40
    assert result['arms']['old']['outcomes']['success'] == 1
    assert result['arms']['revised']['outcomes']['invalid' if invalid else 'timeout'] == 1
    assert result['arms']['old']['all_attempts']['total_tokens']['sum'] == 120
    assert result['arms']['revised']['success_only']['total_tokens']['n'] == 0
    assert result['complete_valid_pairs'] == (0 if invalid else 1)
    if not invalid:
        assert result['paired_bootstrap']['success']['mean_delta_B_minus_A'] == -1
        assert result['joint_success']['n'] == 0
