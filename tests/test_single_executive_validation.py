import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def single(monkeypatch):
    scripts = Path(__file__).resolve().parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('single_executive',scripts/'single_executive_validation.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def contract(single,root):
    ids = list(single.full.PILOT_TASKS)+[str(i) for i in range(14)]
    value = {'items':[{'id':i,'source_sha256':'source'} for i in ids],
        'schedule':single.full.schedule(ids)[:40], 'input_hashes':{},
        'artifacts':{c:{'artifact_sha256':'skill'} for c in ('old','revised')},
        'pilot_task_ids':list(single.full.PILOT_TASKS),'caveat':'dev',
        'max_transport_restarts':2,'max_cell_attempts':2}
    (root/'validation_contract.json').write_text(json.dumps(value))
    return value


def entry(single,job,*,valid=True,solved=True,timeout=False):
    return {'condition':job['condition'],'episode':'mock',
        'row':{'bridge_task_key':single.driver.episode_key(job),'id':job['id'],
        'provider_valid':valid,'fidelity':'V1_TRUNCATED' if timeout else ('V2_TRACE' if valid else 'V0_INVALID'),
        'source_sha256':'source','skill_sha256':'skill','proof_solved':solved,
        'safety_passed':True,'within_budget':not timeout,'timed_out':timeout,'actor_wall_seconds':600 if timeout else 10},
        'retrieval':{'read_calls':0,'read_ids':[]},'settled_usage':{
        **dict.fromkeys(single.full.USAGE,0),'requests':1,'completed_requests':int(valid),
        'error_requests':int(not valid),'unmetered_requests':int(not valid)}}


def mock_run(single,session,child,rows,failures):
    (session/'episodes').mkdir()
    for e in rows: (session/'episodes'/e['row']['bridge_task_key']).mkdir()
    records = [{'upstream_dispatched':True,'attempts':[{'usage':{} if e['row']['provider_valid'] else None,
        'estimated_cost_usd':1 if e['row']['provider_valid'] else None}]} for e in rows]
    ledger = session/'provider_calls.jsonl'
    ledger.write_text(''.join(json.dumps(x)+'\n' for x in records))
    (session/'summary.json').write_text(json.dumps({'rows':rows,'failures':failures,
        'bridge_drained':True,'reviewed_inputs_unchanged':True,'ledger_sha256':single.driver.sha(ledger)}))


def test_one_fresh_repeat_preparation(tmp_path,monkeypatch,single):
    root = tmp_path/'run'; root.mkdir(); audit = tmp_path/'audit.json'; audit.write_text('{}')
    value = contract(single,tmp_path)
    value['schedule'] = single.full.schedule([x['id'] for x in value['items']])
    monkeypatch.setattr(single.full,'prepare',lambda *a,**kw:value)
    result = single.prepare(tmp_path/'config',tmp_path/'pilot',audit,root)
    assert len(result['schedule'])==40 and result['repetitions']==1
    assert all(x['repeat']==0 for x in result['schedule'])


def test_transport_only_replacement_preserves_failure_and_timeout(tmp_path,monkeypatch,single):
    value = contract(single,tmp_path); dispatched = []
    def run(config,session,child,**kwargs):
        dispatched.append(child['schedule'])
        rows = [entry(single,j) for j in child['schedule']]
        failures = []
        if len(dispatched)==1:
            rows = [entry(single,child['schedule'][0],solved=False,timeout=True),
                    entry(single,child['schedule'][1],valid=False)]
            failures = [{'reason':'invalid_provider'},{'reason':'IncompleteRead: test'}]
        mock_run(single,session,child,rows,failures)
        if failures: raise RuntimeError('Development run stopped')
    monkeypatch.setattr(single.driver,'run',run)
    monkeypatch.setattr(single,'transport_retryable',lambda *a:True)
    monkeypatch.setattr(single.time,'sleep',lambda _:None)
    single.run({},tmp_path,value)
    result = json.loads((tmp_path/'summary.json').read_text())
    assert result['complete'] and result['completed_episodes']==40
    assert len(dispatched[0])==40 and len(dispatched[1])==39
    assert dispatched[0][0] not in dispatched[1]
    assert result['totals']['old']['within_budget_dual_pass']==19
    assert result['all_attempt_unmetered_requests']==1 and not result['cost_accounting_complete']
    assert result['all_attempt_recorded_cost_usd']==40
    dispatched.clear()
    single.run({},tmp_path,value)
    assert not dispatched  # Read settled checkpoints; never rerun valid outcomes.


@pytest.mark.parametrize('transport',[False,True])
def test_nontransport_or_repeated_invalid_stops(tmp_path,monkeypatch,single,transport):
    value = contract(single,tmp_path); calls = []
    def run(config,session,child,**kwargs):
        calls.append(1)
        mock_run(single,session,child,[entry(single,child['schedule'][0],valid=False)],
                 [{'reason':'invalid_provider'},{'reason':'IncompleteRead: test'}])
    monkeypatch.setattr(single.driver,'run',run)
    monkeypatch.setattr(single,'transport_retryable',lambda *a:transport)
    monkeypatch.setattr(single.time,'sleep',lambda _:None)
    with pytest.raises(RuntimeError): single.run({},tmp_path,value)
    assert len(calls)==(2 if transport else 1)
    assert not json.loads((tmp_path/'summary.json').read_text())['complete']


def test_late_provider_error_not_admitted(tmp_path,single):
    value = contract(single,tmp_path); job = value['schedule'][0]; result = entry(single,job)
    assert single.admitted(result,job,value)
    result['settled_usage']['error_requests'] = 1
    assert not single.admitted(result,job,value)


def test_single_remaining_replacement(tmp_path,monkeypatch,single):
    value = contract(single,tmp_path); dispatched = []
    def run(config,session,child,**kwargs):
        dispatched.append(child['schedule'])
        rows = [entry(single,j) for j in child['schedule']]
        failures = []
        if len(dispatched)==1:
            rows[-1] = entry(single,child['schedule'][-1],valid=False)
            failures = [{'reason':'invalid_provider'},{'reason':'IncompleteRead: test'}]
        mock_run(single,session,child,rows,failures)
    monkeypatch.setattr(single.driver,'run',run)
    monkeypatch.setattr(single,'transport_retryable',lambda *a:True)
    monkeypatch.setattr(single.time,'sleep',lambda _:None)
    single.run({},tmp_path,value)
    assert [len(x) for x in dispatched]==[40,1]
    result = json.loads((tmp_path/'summary.json').read_text())
    assert result['complete'] and len(result['rows'])==40
    assert dispatched[1]==[dispatched[0][-1]]
