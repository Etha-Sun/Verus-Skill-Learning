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
import resume_ten_card_seven_arm as previous

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
    original_root=Path(read(parent/'recovery-selection.json')['parent'])
    return e.check(original_root)['schedule']


def parent_outcomes(parent):
    kept=read(parent/'combined-report.json')['rows']
    aborted=[r for r in read(parent/'report.json')['rows'] if r['outcome']=='infrastructure_aborted']
    return kept+aborted


def prepare(parent, root):
    original = previous.check(parent)
    summary = read(parent/'summary.json'); report = read(parent/'report.json')
    require((parent/'stopped.json').exists() and summary['bridge_drained'], 'Parent not stopped/drained')
    jobs, kept, retry = select_remaining(full_schedule(parent), parent_outcomes(parent))
    require(len(kept)==89 and len(retry)==2 and len(jobs)==23, 'Unexpected recovery matrix; inspect before launch')
    require(not root.exists(), 'Fresh recovery root required')
    root.mkdir(parents=True)
    for name in ['TASK.md','EXECUTIVE.md','task-selection.json','exposure.json']:
        shutil.copyfile(parent/name,root/name)
    shutil.copytree(parent/'runtime', root/'runtime')
    shutil.copytree(parent/'bundles', root/'bundles')
    config=read(parent/'config.json');config['source_root']=str(root/'runtime');write_json(root/'config.json',config)
    baseline=read(parent/'budget-baseline.json')
    baseline['states']={str(g.path):read(g.path) for g in e.guards(parent,Path(original['shared_ledger_root']))}
    require(all(not s['reservations'] for s in baseline['states'].values()),'Outstanding provider calls')
    baseline['prior_run']=str(parent)
    baseline['handling']='Explicitly authorized recovery. Preserve all historical known/unknown costs; stop on new unknown cost. Retry two infrastructure-aborted cells once.'
    write_json(root/'budget-baseline.json',baseline)
    auth={'user_instruction':'剩下未完成的题目重发请求吧',
          'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'destination':'https://api.deepseek.com',
          'scope':'Same previously explicitly authorized8unsolved validation inputs, actor candidates/diagnostics and on-demand cards including pseudocode; no reference answers/test data.',
          'recovery_jobs':23,'unstarted_jobs':21,'authorized_infrastructure_retries':retry,
          'preserved_valid_jobs':89,'evaluation_cap_usd':20,'total_cap_usd':70,'automatic_paid_retry':False}
    write_json(root/'authorization.json',auth)
    write_json(root/'recovery-selection.json',{'parent':str(parent),'preserved_keys':kept,'retry_keys':retry,
          'remaining_schedule':jobs,'rule':'Keep every non-infrastructure outcome, including timeout. No best-of selection. Preserve all attempts and costs.'})
    e.preflight(root, config, Path(original['parent_materials']))
    contract=copy.deepcopy(original)
    contract.update(schema_version='ten-card-seven-arm-authorized-resume-v2',schedule=jobs,expected_episodes=len(jobs),
                    authorization=auth,bundle_paths={a:str(root/'bundles'/a) for a in e.ARMS},
                    artifacts={a:e.load_skill_artifact(root/'bundles'/a).manifest() for a in e.ARMS},
                    recovery_parent=str(parent),preserved_valid_jobs=89,original_planned_episodes=112)
    require(contract['artifacts']==original['artifacts'],'Copied actor artifacts changed')
    contract['workers']=1
    contract['caveat']+=' Second recovery keeps89valid outcomes; retries2infra aborts and starts21unstarted. Workers reduced2to1 for conservative budget headroom; timing comparisons have concurrency/period confounds.'
    paths=[p for p in root.rglob('*') if p.is_file() and 'preflight' not in p.parts]
    paths += [root/'preflight.json',Path(__file__),parent/'validation_contract.json',parent/'summary.json',parent/'report.json',parent/'stopped.json',parent/'provider_calls.jsonl',parent/'authorization.json',parent/'combined-report.json']
    contract['input_hashes'].update({str(p.resolve()):sha(p) for p in paths})
    write_json(root/'validation_contract.json',contract)
    write_json(root/'review_receipt.json',{'decision':'APPROVE_WITH_NONBLOCKING_NOTES','contract_sha256':sha(root/'validation_contract.json'),
       'reviewer':'Codex recovery-delta review, not independent','paid_calls':0,'blocking_issues':[],
       'nonblocking_notes':[contract['caveat'],'Historical uncertain fees remain fully reserved, not claimed as actual billing.']})
    check(root)
    report_merged(root, [])
    print(json.dumps({'remaining':23,'retained':89,'infra_retries':2,'unstarted':21,'preflight_arms':7,'paid_calls':0}),flush=True)


def check(root):
    c=read(root/'validation_contract.json');parent=Path(c['recovery_parent']);original=previous.check(parent)
    require(c['schema_version']=='ten-card-seven-arm-authorized-resume-v2' and c['workers']==1,'Wrong resume schema/workers')
    jobs,kept,retry=select_remaining(full_schedule(parent),parent_outcomes(parent))
    require(c['schedule']==jobs and c['expected_episodes']==23 and len(kept)==89 and len(retry)==2,'Resume schedule changed')
    for field in ['items','artifacts','model','reasoning_effort','timeout_seconds','repeats','installed_library_root',
                  'installed_library_conditions','model_context_window','max_output_tokens_per_request','budget_usd','total_cap_usd',
                  'ordinary_retry','transport_retry','reference_proof_supplied','sealed_test_access','shared_ledger_root']:
        require(c[field]==original[field],'Actor/method changed: '+field)
    require(all(sha(p)==h for p,h in c['input_hashes'].items()),'Frozen resume inputs changed')
    require(len(read(root/'preflight.json')['checks'])==7 and all(x['returncode']==0 for x in read(root/'preflight.json')['checks']),'Preflight incomplete')
    e.prior.driver.check_review(root/'review_receipt.json',root/'validation_contract.json')
    return c


def report_merged(root, fresh):
    c=read(root/'validation_contract.json');parent=Path(c['recovery_parent'])
    old=read(parent/'combined-report.json')['rows']
    kept=[dict(r) for r in old]
    aborted=list(read(parent/'combined-report.json')['infrastructure_attempt_history'])
    kept += [dict(r,attempt_source='recovery2') for r in fresh if r['outcome']!='infrastructure_aborted']
    aborted += [dict(r,attempt_source='recovery2') for r in fresh if r['outcome']=='infrastructure_aborted']
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
        gs=e.guards(root,ledger);baseline=read(root/'budget-baseline.json')['states']
        require(all(read(g.path)==baseline[str(g.path)] for g in gs),'Budget changed since recovery review')
        config=read(root/'config.json');e.prior.credentials(config)
        write_json(root/'started.json',{'time':datetime.now(timezone.utc).isoformat(),'contract_sha256':sha(root/'validation_contract.json'),'episodes':23})
        try:
            e.prior.driver.run(config,root,c,expected_episodes=23,budget_guard=e.HistoricalUncertaintyMux(gs,baseline),retrieval_auditor=lambda p:e.audit_reads(p,root))
        except BaseException as error:
            write_json(root/'stopped.json',{'type':type(error).__name__,'reason':str(error),'automatic_retry':False});raise
        finally:
            if (root/'summary.json').exists():report(root)
        require(read(root/'combined-report.json')['valid_terminal']==112,'Incomplete combined matrix')
        write_json(root/'completed.json',{'status':'recovery_complete','recovery_episodes':23,'combined_valid_terminal':112})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['prepare','check','run','report']);p.add_argument('--output',type=Path,required=True);p.add_argument('--parent',type=Path)
    a=p.parse_args();root=e.prior.builder.output_root(a.output)
    if a.phase=='prepare':prepare(e.prior.builder.output_root(a.parent),root)
    else:{'check':check,'run':run,'report':report}[a.phase](root)
