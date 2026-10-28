import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil

import pytest
import evaluate_retrieval_reassessment as r

BUNDLE = r.REPO / 'research_artifacts/skill-chain-seven-arm-20261022/bundles/new_skeleton'


def materials(tmp_path):
    parent = tmp_path / 'v3'; root = tmp_path / 'new'
    shutil.copytree(BUNDLE, parent / 'bundles/new_skeleton')
    for name in ('EXECUTIVE.md', 'TASK.md', 'task-selection.json'):
        (parent / name).write_text('unchanged\n')
        root.mkdir(exist_ok=True); shutil.copyfile(parent / name, root / name)
    for arm in r.ARMS:
        shutil.copytree(BUNDLE, root / 'bundles' / arm)
    p = root / 'bundles' / r.ARMS[1] / 'SKILL.md'
    p.write_bytes(r.revised_main(p.read_bytes(), r.rule_text()))
    return root, parent


def test_materials_exact_and_each_frozen_surface_detects_tamper(tmp_path):
    root, parent = materials(tmp_path)
    r.verify_materials(root, parent)
    for path in [root / 'EXECUTIVE.md', root / 'TASK.md',
                 root / 'bundles' / r.ARMS[0] / 'SKILL.md',
                 root / 'bundles' / r.ARMS[1] / 'SKILL.md',
                 root / 'bundles' / r.ARMS[1] / 'cards.json',
                 root / 'bundles' / r.ARMS[0] / 'card_read.py']:
        old = path.read_bytes(); path.write_bytes(old + b' ')
        with pytest.raises(ValueError): r.verify_materials(root, parent)
        path.write_bytes(old)
    (root / 'bundles' / r.ARMS[1] / 'answer.rs').write_text('forbidden')
    with pytest.raises(ValueError): r.verify_materials(root, parent)


def test_matrix_is_fresh_balanced_and_has_no_injection_fields():
    jobs = r.schedule()
    assert len(jobs) == len({(j['id'], j['condition'], j['repeat']) for j in jobs}) == 24
    assert all(set(j) == {'id', 'condition', 'repeat'} for j in jobs)
    for i in range(0, 24, 2):
        a, b = jobs[i:i+2]
        assert (a['id'], a['repeat']) == (b['id'], b['repeat'])
        assert {a['condition'], b['condition']} == set(r.ARMS)
    assert sum(jobs[i]['condition'] == r.ARMS[0] for i in range(0, 24, 2)) == 6


def event_fixture(root, checks):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    r.write_json(root / 'result.json', {'started_at': start.isoformat()})
    events = [{'timestamp': (start + timedelta(seconds=seconds)).isoformat(),
               'type': 'verifier', 'actor': tool, 'candidate_sha256': digest,
               'data': {'passed': passed}} for seconds, tool, digest, passed in checks]
    (root / 'agent_events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))


@pytest.mark.parametrize('checks,expected', [
    ([(599, 'verus', 'a', True), (600, 'lynette', 'a', True)], True),
    ([(599, 'verus', 'a', True), (600.001, 'lynette', 'a', True)], False),
    ([(100, 'verus', 'a', True), (101, 'lynette', 'b', True)], False),
    ([(100, 'verus', 'a', False), (101, 'lynette', 'a', True)], False),
])
def test_same_candidate_and_completion_deadline(tmp_path, checks, expected):
    event_fixture(tmp_path, checks)
    audit = r.e.hard.deadline_audit(tmp_path, 600)
    assert audit['observed_dual_within_deadline'] is expected


def test_run_without_authorization_never_reads_credentials_or_creates_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(r, 'check', lambda root: {})
    monkeypatch.setattr(r.e.prior, 'credentials', lambda *a: pytest.fail('credentials touched'))
    with pytest.raises(ValueError, match='No API launch authorization'):
        r.run(tmp_path, None)
    assert list(tmp_path.iterdir()) == []


def test_authorization_is_bound_to_contract_and_budget(tmp_path):
    (tmp_path / 'validation_contract.json').write_text('{}')
    path = tmp_path / 'approval.json'
    approval = dict(contract_sha256=r.sha(tmp_path / 'validation_contract.json'), approved=True,
        episodes=24, new_batch_cap_usd=20, destination='https://api.deepseek.com',
        automatic_paid_retry=False, background_launch=True, pricing_verified=True,
        user_instruction='Synthetic test only', pricing_evidence='Synthetic test only')
    r.write_json(path, approval); r.validate_authorization(tmp_path, path)
    for key, bad in [('episodes', 48), ('new_batch_cap_usd', 80), ('contract_sha256', 'stale'), ('pricing_verified', False)]:
        r.write_json(path, {**approval, key: bad})
        with pytest.raises(ValueError): r.validate_authorization(tmp_path, path)


def test_budget_reserves_two_inflight_and_stops_on_unknown(tmp_path):
    guard = r.e.SharedBudgetGuard(tmp_path / 'budget.json', approval_limit_usd=4,
        prior_spend_usd=0, optimizer_reserve_usd=0, request_reserve_usd=0)
    mux = r.e.BudgetMux([guard]); reserve = 1.90316544
    a = mux.reserve(reserve); b = mux.reserve(reserve)
    with pytest.raises(Exception): mux.reserve(reserve)
    state = r.read(guard.path)
    assert len(state['reservations']) == 2
    mux.settle(a, cost_usd=.1, usage={})
    mux.settle(b, cost_usd=None, usage={})
    with pytest.raises(RuntimeError, match='Unknown provider cost'): mux.reserve(.01)
    state = r.read(guard.path)
    assert state['uncertain_spend_usd'] == pytest.approx(reserve)
    assert state['target_spend_usd'] == pytest.approx(.1)


def test_report_keeps_dual_pass_separate_from_exit_timeout(tmp_path):
    ep = tmp_path / 'episodes' / 'sample'; ep.mkdir(parents=True)
    event_fixture(ep, [(500, 'verus', 'a', True), (501, 'lynette', 'a', True)])
    (ep / 'codex_events.raw.jsonl').write_text('')
    (ep / 'prompt.txt').write_text('task\n'); (tmp_path / 'TASK.md').write_text('task\n')
    r.write_json(ep / 'fidelity_audit.json', {'shell_edit_suspect_count': 0})
    job = r.schedule()[0]; key = r.e.prior.driver.episode_key(job)
    row = dict(id=job['id'], bridge_task_key=key, timed_out=True, codex_returncode=-9,
        proof_solved=False, safety_passed=False, within_budget=False, fidelity='V2_TRACE',
        provider_valid=True, actor_wall_seconds=600.1)
    usage = dict(requests=1, prompt_cache_hit_tokens=100, prompt_cache_miss_tokens=200,
        completion_tokens=300, reasoning_tokens=250)
    r.write_json(tmp_path / 'validation_contract.json', {'schedule': r.schedule(), 'caveat': 'fixture'})
    r.write_json(tmp_path / 'summary.json', {'rows': [dict(row=row, episode=str(ep), condition=job['condition'],
        settled_usage=usage, retrieval={'read_calls': 0})], 'failures': []})
    r.write_json(tmp_path / 'budget.json', {'target_spend_usd': .1})
    result = r.report(tmp_path)['rows'][0]
    assert result['primary_same_hash_dual_600'] and not result['normal_exit']
    assert result['first_confirmed_dual_seconds'] == 501
    assert result['completion_tokens'] == 300 and result['reasoning_tokens'] == 250


def test_exact_payload_dedup_bulk_and_rejection_are_distinct():
    bank = {'c1': 'First complete body\nwith another line', 'c2': 'Second complete body'}
    def event(ident, command, output):
        return {'type': 'item.completed', 'item': {'id': ident, 'type': 'command_execution',
            'command': command, 'aggregated_output': output}}
    payload = json.dumps(dict(card_retrieval=1, operation='read', id='c1', content=bank['c1']))
    a = event('read1', 'python3 card_read.py c1', payload)
    bulk = event('bulk1', 'head -50 cards.json', json.dumps({'cards': [{'id': k, 'content': v} for k,v in bank.items()]}))
    bad = event('bad1', 'python3 card_read.py c2', json.dumps(dict(card_retrieval=1, operation='read', id='c2', content='wrong body')))
    result = r.audit_payloads([a, a, bulk, bad], bank)
    assert result['read_calls'] == 1 and len(result['events']) == 3
    assert result['read_ids'] == ['c1', 'c2'] and len(result['reader_errors']) == 1
    assert len(result['direct_bank_access_commands']) == 1
    assert 'manual review' in result['application_correctness']
    assert not r.audit_payloads([event('partial', 'head -c 10 cards.json', 'First comp')], bank)['events']


def test_incomplete_live_run_is_not_reported_as_zero_cost(tmp_path):
    r.write_json(tmp_path / 'validation_contract.json', {})
    assert r.report(tmp_path)['paid_calls'] == 0
    (tmp_path / 'started.json').write_text('{}')
    report = r.report(tmp_path)
    assert report['status'] == 'started_without_summary'
    assert report['paid_calls'] == 'unknown_pending_ledger_review'
