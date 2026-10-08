"""Synthetic recovery waves preserve outcomes and isolate physical retry costs."""
from contextlib import contextmanager
import json
from pathlib import Path
import threading

import pytest

from skillopt_verusage import evaluate_resume as resume
from skillopt_verusage.campaign_evidence import sha
from test_evaluation_recovery import parent, put


def fault_row(key):
    return {'bridge_task_key':key,'fidelity':'V0_INVALID','codex_returncode':1,
        'actor_model':'deepseek-v4-pro','actor_reasoning_effort':'max',
        'codex_terminal':{'failed':1}}


def transport_event(key):
    return {'type':'turn.failed','error':{'message':
        f'409 Conflict /tasks/{key}/v1/responses IncompleteRead: synthetic fault'}}


@pytest.mark.parametrize('mutation',[
    None,'ordinary','no_fault','generic_409','wrong_path','no_terminal','completed',
    'wrong_model','wrong_reasoning','wrong_fidelity','wrong_returncode'])
def test_transport_retry_is_narrow(tmp_path,mutation):
    key='val_r1_initial--synthetic';row=fault_row(key);event=transport_event(key)
    ledger=[{'task_id':key,'attempts':[{'error':'IncompleteRead: synthetic fault'}]}]
    if mutation=='ordinary':ledger[0]['attempts'][0]['error']='ValueError: actor model mismatch'
    if mutation=='no_fault':ledger=[]
    if mutation=='generic_409':event['error']['message']=f'409 Conflict /tasks/{key}/v1/responses'
    if mutation=='wrong_path':event=transport_event('different')
    if mutation=='no_terminal':row['codex_terminal']={}
    if mutation=='completed':event['type']='turn.completed'
    if mutation=='wrong_model':row['actor_model']='different-model'
    if mutation=='wrong_reasoning':row['actor_reasoning_effort']='high'
    if mutation=='wrong_fidelity':row['fidelity']='V2_TRACE'
    if mutation=='wrong_returncode':row['codex_returncode']=0
    (tmp_path/'codex_events.raw.jsonl').write_text(json.dumps(event)+'\n')
    assert resume.transport_retryable(row,tmp_path,ledger) is (mutation is None)


@pytest.mark.parametrize('ident',['question-01','question-02','question-03'])
def test_settled_first_valid_timeout_or_failure_retained(parent,ident):
    directory=parent/'validation/repeat_1/initial'/ident
    row=json.loads((directory/'result.json').read_text())
    frozen=json.loads((parent/'frozen_artifacts.json').read_text())
    jobs=json.loads((parent/'evaluation_schedule.json').read_text())['blocks'][0]
    job=next(j for j in jobs if j[1]=='initial' and j[2]['id']==ident)
    resume.admit_settled(row,directory,parent/'provider_calls.jsonl',job,frozen['initial'])
    if ident=='question-01':assert row['timed_out'] and row['fidelity']=='V1_TRUNCATED'
    if ident=='question-02':assert not row['hard'] and row['fidelity']=='V2_TRACE'


def test_valid_timeout_with_failed_safety_is_not_performance_replayed(parent):
    directory=parent/'validation/repeat_1/initial/question-01'
    row=json.loads((directory/'result.json').read_text());row['safety_passed']=False
    frozen=json.loads((parent/'frozen_artifacts.json').read_text())
    jobs=json.loads((parent/'evaluation_schedule.json').read_text())['blocks'][0]
    job=next(j for j in jobs if j[1]=='initial' and j[2]['id']=='question-01')
    resume.admit_settled(row,directory,parent/'provider_calls.jsonl',job,frozen['initial'])
    assert row['fidelity']=='V1_TRUNCATED' and not row['hard']


@pytest.mark.parametrize('mutation',[
    'actor_model','reasoning','provider_invalid','not_truncated','v2_timeout',
    'v2_returncode','v2_terminal','v2_f3','bad_manifest','input','skill','candidate',
    'validation','unknown_cost','upstream_model'])
def test_settled_rejects_invalid_evidence(parent,mutation):
    ident='question-01' if mutation=='not_truncated' else 'question-03'
    directory=parent/'validation/repeat_1/initial'/ident
    row=json.loads((directory/'result.json').read_text())
    frozen=json.loads((parent/'frozen_artifacts.json').read_text())
    jobs=json.loads((parent/'evaluation_schedule.json').read_text())['blocks'][0]
    job=next(j for j in jobs if j[1]=='initial' and j[2]['id']==ident)
    if mutation=='actor_model':row['actor_model']='other'
    if mutation=='reasoning':row['actor_reasoning_effort']='high'
    if mutation=='provider_invalid':row['provider_valid']=False
    if mutation=='not_truncated':row.update(timed_out=False,within_budget=True)
    if mutation=='v2_timeout':row.update(timed_out=True,within_budget=False)
    if mutation=='v2_returncode':row['codex_returncode']=1
    if mutation=='v2_terminal':
        (directory/'codex_events.raw.jsonl').write_text(json.dumps({'type':'turn.failed'})+'\n')
        row['codex_terminal']={'completed':0,'failed':1,'errors':0}
    if mutation=='v2_f3':put(directory/'fidelity_audit.json',{'input_unchanged':True,'f3':False})
    if mutation=='bad_manifest':
        manifest=json.loads((directory/'run_manifest.json').read_text());manifest['timeout_seconds']=1800
        put(directory/'run_manifest.json',manifest)
    if mutation in ('input','skill','candidate'):
        filename={'input':'input.rs','skill':'SKILL.md','candidate':'candidate.rs'}[mutation]
        (directory/'workspace'/filename).write_text('changed')
    if mutation=='validation':row['validation']={}
    if mutation in ('unknown_cost','upstream_model'):
        ledger=resume.records(parent/'provider_calls.jsonl')
        record=next(r for r in ledger if r['task_id']==row['bridge_task_key'])
        if mutation=='unknown_cost':record['attempts'][0]['estimated_cost_usd']=None
        else:record['upstream_model']='other'
        resume.EvaluationResume.write_ledger(parent/'provider_calls.jsonl',ledger)
    with pytest.raises(ValueError):
        resume.admit_settled(row,directory,parent/'provider_calls.jsonl',job,frozen['initial'])


def test_copy_episode_is_byte_exact_and_rejects_overwrite_or_symlink(tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'raw').write_bytes(b'original\x00bytes')
    target=tmp_path/'target';resume.copy_episode(source,target)
    assert (target/'raw').read_bytes()==b'original\x00bytes'
    with pytest.raises(ValueError):resume.copy_episode(source,target)
    (source/'linked').symlink_to(source/'raw')
    with pytest.raises(ValueError):resume.copy_episode(source,tmp_path/'unsafe')


def test_prepare_copies_retained_episode_and_original_input_without_mutating_parent(tmp_path):
    parent=tmp_path/'parent';parent.mkdir();root=tmp_path/'child';root.mkdir()
    directory=parent/'validation/repeat_1/initial/q';directory.mkdir(parents=True)
    (directory/'raw.bin').write_bytes(b'unchanged\x00episode')
    put(directory/'result.json',{'hard':0})
    source=parent/'val_inputs/q.rs';source.parent.mkdir();source.write_text('original input')
    job=[0,'initial',{'id':'q','runtime_source':str(source),'source_sha256':sha(source)}]
    put(parent/'evaluation_schedule.json',{'blocks':[[job]]})
    for name in ('frozen_artifacts.json','artifact_quality_evidence.json','artifact_review.json'):
        put(parent/name,{} if name=='frozen_artifacts.json' else {'unchanged':True})
    for condition in ('original_only','augmented'):put(parent/f'banks/{condition}/cards.json',{'cards':[]})
    campaign=resume.EvaluationResume.__new__(resume.EvaluationResume)
    campaign.parent=parent;campaign.root=root;campaign.sources={}
    campaign.receipt={'result_directories':{'val_r1_initial--q':str(directory.relative_to(parent))},
        'ledger_sha256':'parent-sha','rows':[{'hard':0}]}
    campaign.persist=lambda:None;campaign.update=lambda **kw:None
    before={str(p.relative_to(parent)):sha(p) for p in parent.rglob('*') if p.is_file()}
    campaign.prepare()
    after={str(p.relative_to(parent)):sha(p) for p in parent.rglob('*') if p.is_file()}
    assert before==after
    assert (root/'validation/repeat_1/initial/q/raw.bin').read_bytes()==b'unchanged\x00episode'
    assert campaign.jobs[0][2]['runtime_source']==str(root/'val_inputs/q.rs')
    assert (root/'val_inputs/q.rs').read_text()=='original input'
    assert campaign.sources['val_r1_initial--q']['result_path']==str(directory/'result.json')
    assert json.loads((root/'evaluation_schedule.json').read_text())['blocks'][0][0][2]['runtime_source']==str(source)
    with pytest.raises(ValueError,match='overwrite'):campaign.prepare()


def wave_campaign(tmp_path,monkeypatch,faults=0,previous_invalid=True,ordinary=False):
    campaign=resume.EvaluationResume.__new__(resume.EvaluationResume)
    campaign.root=tmp_path/'child';campaign.root.mkdir()
    campaign.parent=tmp_path/'parent';campaign.parent.mkdir()
    campaign.jobs=[(r,c,{'id':f'question-{n:02d}'}) for r in (0,1)
                   for n in range(20) for c in resume.CONDITIONS]
    parent_invalid={resume.job_key(j) for j in campaign.jobs[:4]}
    retained=[j for j in campaign.jobs[:64] if resume.job_key(j) not in parent_invalid]
    campaign.receipt={'invalid_keys':sorted(parent_invalid) if previous_invalid else [],
        'unknown_expense':{'request_id':'old-unknown','unknown_expense_upper_usd':1.90316544}}
    campaign.rows=[{'bridge_task_key':resume.job_key(j),'condition':j[1],
                   'repetition':j[0]+1,'hard':0} for j in retained]
    parent_ledger=campaign.parent/'provider_calls.jsonl'
    campaign.write_ledger(parent_ledger,[{'request_id':'parent-'+resume.job_key(j),
        'task_id':resume.job_key(j),'attempts':[{'estimated_cost_usd':.01}]} for j in campaign.jobs[:64]])
    put(campaign.parent/'cost_summary.json',{'recovery_parent_physical_cost_usd':2,
        'approved_historical_unknown_requests':[]})
    campaign.sources={resume.job_key(j):{'ledger_path':str(parent_ledger),
        'ledger_sha256':sha(parent_ledger),'result_path':'parent-result','result_sha256':'parent-sha'} for j in retained}
    campaign.physical_sources=[];campaign.frozen={c:{} for c in resume.CONDITIONS}
    campaign.config={'python_bin':'synthetic-python'};campaign.repo=tmp_path
    campaign.updates=[];campaign.update=lambda **kw:campaign.updates.append(kw)
    campaign.calls={};lock=threading.Lock();failure_key=resume.job_key(campaign.jobs[0])
    @contextmanager
    def bridge(*args):yield object()
    campaign.bridge=bridge
    def run_episode(job,bridge,wave):
        key=resume.job_key(job);directory=resume.episode_path(wave,job);directory.mkdir(parents=True)
        with lock:
            count=campaign.calls.get(key,0);campaign.calls[key]=count+1
            invalid=key==failure_key and count<faults
            physical=resume.records(campaign.ledger)
            physical.append({'request_id':f'physical-{wave.name}-{key}','task_id':key,
                'attempts':[{'estimated_cost_usd':None if invalid else .01,
                    'error':'ordinary mismatch' if ordinary else ('IncompleteRead: synthetic' if invalid else None)}]})
            campaign.write_ledger(campaign.ledger,physical)
        row=fault_row(key) if invalid else {'bridge_task_key':key,'fidelity':'V1_TRUNCATED' if job==campaign.jobs[1]
            else 'V2_TRACE','timed_out':job==campaign.jobs[1],'hard':0}
        put(directory/'result.json',row)
        (directory/'codex_events.raw.jsonl').write_text(json.dumps(transport_event(key))+'\n' if invalid else '')
        return row
    campaign.run_episode=run_episode
    monkeypatch.setattr(resume,'admit_settled',lambda *args:None)
    monkeypatch.setattr(resume,'aggregate',lambda rows,conditions:{'runs':len(rows)})
    monkeypatch.setattr(resume.subprocess,'run',lambda *args,**kwargs:None)
    return campaign,failure_key


@pytest.mark.parametrize('previous_invalid,faults,expected_calls',[(True,0,1),(True,1,2),(False,2,3)])
def test_waves_full_coverage_attempt_limits_and_physical_projection(tmp_path,monkeypatch,previous_invalid,faults,expected_calls):
    campaign,key=wave_campaign(tmp_path,monkeypatch,faults,previous_invalid)
    campaign.run()
    assert len(campaign.rows)==len(campaign.sources)==160
    assert campaign.calls[key]==expected_calls
    assert len(campaign.calls)==100
    assert campaign.calls[resume.job_key(campaign.jobs[1])]==1  # Valid timeout retained first time.
    assert all(row['hard']==0 for row in campaign.rows)  # Valid failures are not performance-replayed.
    physical=resume.records(campaign.root/'provider_calls.jsonl')
    selected=resume.records(campaign.root/'selected_episode_ledger.jsonl')
    assert len(physical)==100+faults and len(selected)==160
    assert len({r['request_id'] for r in physical})==len(physical)
    assert not ({r['request_id'] for r in physical}&{r['request_id'] for r in selected if r['request_id'].startswith('parent-')})
    assert len({r['task_id'] for r in selected})==160
    cost=json.loads((campaign.root/'cost_summary.json').read_text())
    assert cost['unknown_cost_requests']==faults and cost['expense_policy']=='record_only'
    assert len(cost['approved_historical_unknown_requests'])==1
    assert sum(u['unknown_expense_upper_usd'] for u in cost['unresolved_new_requests'])==pytest.approx(faults*1.90316544)
    for entry in campaign.physical_sources:assert sha(Path(entry['ledger_path']))==entry['ledger_sha256']
    waves=sorted((campaign.root/'evaluation_attempts').glob('wave-*'))
    assert json.loads((waves[0]/'jobs.json').read_text())[0]['attempt']==int(previous_invalid)
    for wave in waves:assert json.loads((wave/'disposition.json').read_text())['bridge_drained'] is True


@pytest.mark.parametrize('previous_invalid,faults,ordinary,expected_calls',[(True,2,False,2),(False,3,False,3),(True,1,True,1)])
def test_nontransport_or_exhausted_episode_stops_preserving_physical_attempts(tmp_path,monkeypatch,previous_invalid,faults,ordinary,expected_calls):
    campaign,key=wave_campaign(tmp_path,monkeypatch,faults,previous_invalid,ordinary)
    with pytest.raises(RuntimeError,match='technical incident preserved'):campaign.run()
    assert campaign.calls[key]==expected_calls and key not in campaign.sources
    assert not resume.episode_path(campaign.root,campaign.jobs[0]).exists()
    assert len(resume.records(campaign.root/'provider_calls.jsonl'))==sum(campaign.calls.values())
    assert all(r['task_id']!=key for r in resume.records(campaign.root/'selected_episode_ledger.jsonl'))
