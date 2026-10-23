"""Explicitly authorized continuation: preserve valid outcomes, retry only infra aborts."""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import shutil
import json

import evaluate_ten_card_seven_arm as e
import resume_ten_card_seven_arm_second as previous
import time
import subprocess

read, sha, require, write_json = e.read, e.sha, e.require, e.write_json


def row_key(row):
    return e.prior.driver.episode_key({'id': row['task_id'], 'condition': row['condition'], 'repeat': row['repeat']})


def select_remaining(schedule, rows):
    planned = {e.prior.driver.episode_key(j): j for j in schedule}
    require(len(planned) == len(schedule), 'Duplicate planned jobs')
    seen = set(); kept = []; retry = []
    for row in rows:
        key = row_key(row)
        require(key in planned and key not in seen, 'Unknown or duplicate outcome')
        seen.add(key)
        if row['outcome'] == 'infrastructure_aborted':
            retry.append(key)
        else:
            # Includes ordinary failure and timeout, not only success.
            kept.append(key)
    remaining = [j for j in schedule if e.prior.driver.episode_key(j) not in set(kept)]
    return remaining, kept, retry


def full_schedule(parent):
    node=parent
    while 'recovery_parent' in read(node/'validation_contract.json'):
        node=Path(read(node/'validation_contract.json')['recovery_parent'])
    return e.check(node)['schedule']


def normalized_parent(parent):
    ancestor=Path(read(parent/'validation_contract.json')['recovery_parent'])
    prior=read(ancestor/'combined-report.json')
    valid=list(prior['rows']); history=list(prior['infrastructure_attempt_history']); latest=[]
    for raw in read(parent/'report.json')['rows']:
        row=dict(raw);ep=Path(row['episode']);result=read(ep/'result.json')
        events=(ep/'codex_events.raw.jsonl').read_text()
        if not result['timed_out'] and result['codex_returncode']!=0 and 'DEEPSEEK_BUDGET_CAPACITY_TIMEOUT' in events:
            row['original_report_outcome']=row['outcome']
            row['outcome']='infrastructure_aborted'
            row['recovery_reason']='Budget reservation contention: driver fixed at two workers'
        latest.append(row)
        if row['outcome']=='infrastructure_aborted':history.append(row)
        else:valid.append(row)
    return valid,history,latest


def parent_outcomes(parent):
    valid,history,latest=normalized_parent(parent)
    return valid+[r for r in latest if r['outcome']=='infrastructure_aborted']


def guards(root,ledger):
    baseline=read(root/'budget-baseline.json')
    return [e.SharedBudgetGuard(Path(baseline['evaluation_ledger']),approval_limit_usd=30,prior_spend_usd=0,optimizer_reserve_usd=0,request_reserve_usd=0),
            e.SharedBudgetGuard(ledger/'budget-new-total.json',approval_limit_usd=80,prior_spend_usd=0,optimizer_reserve_usd=0,request_reserve_usd=0)]


def raise_budgets(parent,control):
    baseline=read(parent/'budget-baseline.json');receipts=[]
    for key,old,new in [('evaluation_ledger',20,30),('total_ledger',70,80)]:
        path=Path(baseline[key]);state=read(path)
        require(state['approval_limit_usd']==old and not state['reservations'],'Budget not drained or already changed')
        guard=e.SharedBudgetGuard(path,approval_limit_usd=old,prior_spend_usd=0,optimizer_reserve_usd=0,request_reserve_usd=0)
        def update(state):
            require(not state['reservations'],'Outstanding provider request')
            state['approval_limit_usd']=new
        guard._update(update)
        after=read(path)
        require({k:v for k,v in state.items() if k!='approval_limit_usd'}=={k:v for k,v in after.items() if k!='approval_limit_usd'},'Historical budget mutated')
        receipts.append({'path':str(path),'before':state,'after':after})
    write_json(control/'budget-increase.json',{'user_approval':'按 USD30／USD80 执行','ledgers':receipts})


def prepare(parent, root):
    original = previous.check(parent)
    summary = read(parent/'summary.json'); report = read(parent/'report.json')
    require((parent/'stopped.json').exists() and summary['bridge_drained'], 'Parent not stopped/drained')
    jobs, kept, retry = select_remaining(full_schedule(parent), parent_outcomes(parent))
    require(89<=len(kept)<=90 and 22<=len(jobs)<=23 and len(kept)+len(jobs)==112, 'Unexpected recovery matrix')
    require(not root.exists(), 'Fresh recovery root required')
    root.mkdir(parents=True)
    for name in ['TASK.md','EXECUTIVE.md','task-selection.json','exposure.json']:
        shutil.copyfile(parent/name,root/name)
    shutil.copytree(parent/'runtime', root/'runtime')
    shutil.copytree(parent/'bundles', root/'bundles')
    config=read(parent/'config.json');config['source_root']=str(root/'runtime');write_json(root/'config.json',config)
    baseline=read(parent/'budget-baseline.json')
    baseline['states']={str(g.path):read(g.path) for g in guards(parent,Path(original['shared_ledger_root']))}
    require(all(not s['reservations'] for s in baseline['states'].values()),'Outstanding provider calls')
    baseline['prior_run']=str(parent)
    baseline['handling']='Explicitly authorized recovery. Preserve all historical known/unknown costs; stop on new unknown cost. Retry two infrastructure-aborted cells once.'
    write_json(root/'budget-baseline.json',baseline)
    auth={'user_instruction':'提高USD上限，保持2并发；按 USD30／USD80 执行',
          'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'destination':'https://api.deepseek.com',
          'scope':'Same previously explicitly authorized8unsolved validation inputs, actor candidates/diagnostics and on-demand cards including pseudocode; no reference answers/test data.',
          'recovery_jobs':len(jobs),'unstarted_jobs':len(jobs)-len(retry),'authorized_infrastructure_retries':retry,
          'preserved_valid_jobs':len(kept),'evaluation_cap_usd':30,'total_cap_usd':80,'automatic_paid_retry':False}
    write_json(root/'authorization.json',auth)
    write_json(root/'recovery-selection.json',{'parent':str(parent),'preserved_keys':kept,'retry_keys':retry,
          'remaining_schedule':jobs,'rule':'Keep every non-infrastructure outcome, including timeout. No best-of selection. Preserve all attempts and costs.'})
    e.preflight(root, config, Path(original['parent_materials']))
    contract=copy.deepcopy(original)
    contract.update(schema_version='ten-card-seven-arm-budget-raised-v3',schedule=jobs,expected_episodes=len(jobs),
                    authorization=auth,bundle_paths={a:str(root/'bundles'/a) for a in e.ARMS},
                    artifacts={a:e.load_skill_artifact(root/'bundles'/a).manifest() for a in e.ARMS},
                    recovery_parent=str(parent),preserved_valid_jobs=len(kept),original_planned_episodes=112)
    require(contract['artifacts']==original['artifacts'],'Copied actor artifacts changed')
    contract.update(workers=2,budget_usd=30,total_cap_usd=80)
    contract['caveat']+=' Budget-raised recovery retains all valid original/continuation cells, retries only infra/reservation-blocked cells and starts unstarted cells. Actual workers2 match contract, cumulative capsUSD30/80; historical costs preserved.'
    paths=[p for p in root.rglob('*') if p.is_file() and 'preflight' not in p.parts]
    paths += [root/'preflight.json',Path(__file__),parent/'validation_contract.json',parent/'summary.json',parent/'report.json',parent/'stopped.json',parent/'provider_calls.jsonl',parent/'authorization.json',parent/'combined-report.json']
    contract['input_hashes'].update({str(p.resolve()):sha(p) for p in paths})
    write_json(root/'validation_contract.json',contract)
    write_json(root/'review_receipt.json',{'decision':'APPROVE_WITH_NONBLOCKING_NOTES','contract_sha256':sha(root/'validation_contract.json'),
       'reviewer':'Codex recovery-delta review, not independent','paid_calls':0,'blocking_issues':[],
       'nonblocking_notes':[contract['caveat'],'Historical uncertain fees remain fully reserved, not claimed as actual billing.']})
    check(root)
    report_merged(root, [])
    print(json.dumps({'remaining':len(jobs),'retained':len(kept),'infra_retries':len(retry),'unstarted':len(jobs)-len(retry),'preflight_arms':7,'paid_calls':0}),flush=True)


def check(root):
    c=read(root/'validation_contract.json');parent=Path(c['recovery_parent']);original=previous.check(parent)
    require(c['schema_version']=='ten-card-seven-arm-budget-raised-v3' and c['workers']==2 and c['budget_usd']==30 and c['total_cap_usd']==80,'Wrong resume schema/workers')
    jobs,kept,retry=select_remaining(full_schedule(parent),parent_outcomes(parent))
    require(c['schedule']==jobs and c['expected_episodes']==len(jobs) and len(kept)+len(jobs)==112 and 89<=len(kept)<=90,'Resume schedule changed')
    for field in ['items','artifacts','model','reasoning_effort','timeout_seconds','repeats','installed_library_root',
                  'installed_library_conditions','model_context_window','max_output_tokens_per_request',
                  'ordinary_retry','transport_retry','reference_proof_supplied','sealed_test_access','shared_ledger_root']:
        require(c[field]==original[field],'Actor/method changed: '+field)
    require(all(sha(p)==h for p,h in c['input_hashes'].items()),'Frozen resume inputs changed')
    require(len(read(root/'preflight.json')['checks'])==7 and all(x['returncode']==0 for x in read(root/'preflight.json')['checks']),'Preflight incomplete')
    e.prior.driver.check_review(root/'review_receipt.json',root/'validation_contract.json')
    return c


def report_merged(root, fresh):
    c=read(root/'validation_contract.json');parent=Path(c['recovery_parent'])
    old,aborted,latest=normalized_parent(parent)
    kept=[dict(r) for r in old]
    kept += [dict(r,attempt_source='budget_raised_recovery') for r in fresh if r['outcome']!='infrastructure_aborted']
    aborted += [dict(r,attempt_source='budget_raised_recovery') for r in fresh if r['outcome']=='infrastructure_aborted']
    require(len({row_key(r) for r in kept})==len(kept),'Duplicate accepted outcomes')
    require(not ({row_key(r) for r in old if r['outcome']!='infrastructure_aborted'} & {row_key(r) for r in fresh}), 'Valid original cell rerun')
    baseline=read(root/'budget-baseline.json')
    write_json(root/'combined-report.json',{'planned':112,'valid_terminal':len(kept),'remaining_without_valid_outcome':112-len(kept),
        'rows':kept,'infrastructure_attempt_history':aborted,'recovery_started_records':len(fresh),
        'arms':{a:{'valid_terminal':sum(r['condition']==a for r in kept),'planned':16,
                  'budgeted_dual_pass':sum(r['condition']==a and r['budgeted_dual_pass'] for r in kept)} for a in e.ARMS},
        'cost_note':'All attempts, including infrastructure aborts, remain charged to the same shared ledgers. Row sums do not replace cumulative accounting.',
        'evaluation_budget':read(Path(baseline['evaluation_ledger'])),'total_budget':read(Path(baseline['total_ledger'])),
        'caveat':c['caveat']})


def report(root):
    # Reuse identical outcome/reading/deadline audit, then correct batch denominators.
    e.report(root)
    d=read(root/'report.json');c=read(root/'validation_contract.json')
    d['planned']=c['expected_episodes'];d['scope']='Recovery batch only; combined-report.json merges preserved original cells.'
    for a in e.ARMS:d['arms'][a]['planned']=sum(j['condition']==a for j in c['schedule'])
    write_json(root/'report.json',d);report_merged(root,d['rows'])


def run(root):
    c=check(root);ledger=Path(c['shared_ledger_root'])
    with (ledger/'execution.lock').open('a') as shared,(root/'execution.lock').open('a') as local:
        for f in [shared,local]:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (root/'started.json').exists() and not (root/'episodes').exists(),'No automatic recovery restart')
        gs=guards(root,ledger);baseline=read(root/'budget-baseline.json')['states']
        require(all(read(g.path)==baseline[str(g.path)] for g in gs),'Budget changed since recovery review')
        config=read(root/'config.json');e.prior.credentials(config)
        write_json(root/'started.json',{'time':datetime.now(timezone.utc).isoformat(),'contract_sha256':sha(root/'validation_contract.json'),'episodes':c['expected_episodes']})
        try:
            e.prior.driver.run(config,root,c,expected_episodes=c['expected_episodes'],budget_guard=e.HistoricalUncertaintyMux(gs,baseline),retrieval_auditor=lambda p:e.audit_reads(p,root))
        except BaseException as error:
            write_json(root/'stopped.json',{'type':type(error).__name__,'reason':str(error),'automatic_retry':False});raise
        finally:
            if (root/'summary.json').exists():report(root)
        require(read(root/'combined-report.json')['valid_terminal']==112,'Incomplete combined matrix')
        write_json(root/'completed.json',{'status':'recovery_complete','recovery_episodes':c['expected_episodes'],'combined_valid_terminal':112})


def await_and_run(parent,root,unit):
    control=root.with_name(root.name+'-control');control.mkdir(parents=True,exist_ok=True)
    require(not (control/'started.json').exists(),'Supervisor already started')
    write_json(control/'started.json',{'user_approval':'按 USD30／USD80 执行','workers':2,'destination':'https://api.deepseek.com','parent':str(parent),'output':str(root),'automatic_retry':False})
    deadline=time.monotonic()+1500
    while True:
        status=subprocess.run(['systemctl','--user','show',unit,'--property=ActiveState','--value'],capture_output=True,text=True,check=True).stdout.strip()
        if status not in ('active','activating','deactivating'):break
        require(time.monotonic()<deadline,'Parent did not drain in25minutes')
        write_json(control/'status.json',{'phase':'waiting_for_parent_drain','parent_state':status,'time':datetime.now(timezone.utc).isoformat()})
        time.sleep(10)
    previous.check(parent)
    require((parent/'summary.json').exists() and read(parent/'summary.json')['bridge_drained'],'Parent not fully drained')
    ledger=Path(read(parent/'validation_contract.json')['shared_ledger_root'])
    with (ledger/'execution.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        raise_budgets(parent,control)
        prepare(parent,root)
    write_json(control/'status.json',{'phase':'launching','time':datetime.now(timezone.utc).isoformat()})
    run(root)
    write_json(control/'status.json',{'phase':'complete','time':datetime.now(timezone.utc).isoformat()})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['prepare','check','run','report','await-run']);p.add_argument('--output',type=Path,required=True);p.add_argument('--parent',type=Path);p.add_argument('--parent-unit')
    a=p.parse_args();root=e.prior.builder.output_root(a.output)
    if a.phase=='prepare':prepare(e.prior.builder.output_root(a.parent),root)
    elif a.phase=='await-run':await_and_run(e.prior.builder.output_root(a.parent),root,a.parent_unit)
    else:{'check':check,'run':run,'report':report}[a.phase](root)
