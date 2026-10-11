"""Fresh40cell validation with bounded, checkpointed IncompleteRead replacement."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import time

import full_executive_validation as full
import validate_card_revision as driver
from skillopt_verusage.evaluate_resume import transport_retryable
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.guarded_deepseek import write_json


def prepare(config_path, pilot, audit_source, root):
    (root/'pilot_audit').mkdir()
    shutil.copyfile(audit_source,root/'pilot_audit/audit.json')
    contract = full.prepare(config_path,pilot,root,singleton_scheduler_fix=True)
    contract.update({'schema_version':'single-executive-validation-dev-v1',
        'schedule':[x for x in contract['schedule'] if x['repeat']==0],
        'expected_episodes':40,'repetitions':1,'max_transport_restarts':2,
        'max_cell_attempts':2,'infrastructure_replacement':'proven_IncompleteRead_only',
        'caveat':'Forty fresh episodes: fixed validation20 x two Executive arms, one repeat. '
                 'No old outcome reuse or ordinary outcome retry. Same pilot method. '
                 'Bounded infrastructure-only replacements retained with all attempt costs. '
                 'Development evidence, not untouched test or augmentation ablation.'})
    for path in (Path(__file__).resolve(),Path(transport_retryable.__code__.co_filename).resolve()):
        contract['input_hashes'][str(path)] = driver.sha(path)
    write_json(root/'validation_contract.json',contract)
    return contract


def admitted(entry, job, contract):
    row = entry['row']; usage = entry['settled_usage']
    item = next(x for x in contract['items'] if x['id']==job['id'])
    return (row['id']==job['id'] and entry['condition']==job['condition'] and
        row['provider_valid'] is True and row['fidelity'] in ('V1_TRUNCATED','V2_TRACE') and
        row['source_sha256']==item['source_sha256'] and
        row['skill_sha256']==contract['artifacts'][job['condition']]['artifact_sha256'] and
        usage['requests']>0 and usage['error_requests']==0 and usage['unmetered_requests']==0 and
        usage['completed_requests']==usage['requests'])


def persist(root, contract, selected, sessions, error=None):
    rows = list(selected.values()); expected = {driver.episode_key(x) for x in contract['schedule']}
    unchanged = all(driver.sha(path)==digest for path,digest in contract['input_hashes'].items())
    complete = len(expected)==40 and set(selected)==expected and unchanged and error is None
    result = {'complete':complete,'completed_episodes':len(rows),'expected_episodes':40,
        'rows':rows,'sessions':sessions,'error':error,'reviewed_inputs_unchanged':unchanged,
        'totals':{c:full.totals([x for x in rows if x['condition']==c]) for c in ('old','revised')},
        'strata':{label:{c:full.totals([x for x in rows if x['condition']==c and
            (x['row']['id'] in contract['pilot_task_ids'])==is_pilot]) for c in ('old','revised')}
            for label,is_pilot in (('pilot6',True),('remaining14',False))},
        'all_attempt_recorded_cost_usd':sum(x['recorded_cost_usd'] for x in sessions),
        'all_attempt_unmetered_requests':sum(x['unmetered_requests'] for x in sessions),
        'cost_accounting_complete':not any(x['unmetered_requests'] or x['unknown_cost_requests'] for x in sessions),
        'caveat':contract['caveat']}
    write_json(root/'summary.json',result)
    write_json(root/'single_executive_summary.json',result)
    return result


def run(config, root, contract):
    jobs = {driver.episode_key(x):x for x in contract['schedule']}
    if len(jobs)!=40 or len(contract['items'])!=20 or any(x.get('repeat')!=0 for x in jobs.values()):
        raise ValueError('Expected exactly40unique single-repeat validation cells')
    selected = {}; sessions = []; attempts = {}; fatal = None
    for number in range(contract['max_transport_restarts']+1):
        pending = [job for key,job in jobs.items() if key not in selected]
        if not pending: break
        session = root/'sessions'/f'session-{number:03d}'
        child = deepcopy(contract); child['schedule'] = pending
        child['input_hashes'][str(root/'validation_contract.json')] = driver.sha(root/'validation_contract.json')
        if not session.exists():
            session.mkdir(parents=True)
            write_json(session/'validation_contract.json',child)
            write_json(root/'active_session.json',{'session':str(session),'selected_before':len(selected),
                'active_progress_file':str(session/'progress.json')})
            try:
                driver.run(config,session,deepcopy(child),expected_episodes=len(pending))
            except Exception:
                if not (session/'summary.json').exists(): raise
        summary = json.loads((session/'summary.json').read_text())
        if (not summary['bridge_drained'] or not summary['reviewed_inputs_unchanged'] or
                driver.sha(session/'provider_calls.jsonl')!=summary['ledger_sha256'] or
                json.loads((session/'validation_contract.json').read_text())!=child):
            raise ValueError('Session integrity/drain/contract mismatch; stop')
        records = [json.loads(x) for x in (session/'provider_calls.jsonl').read_text().splitlines()]
        sessions.append({'path':str(session),'summary_sha256':driver.sha(session/'summary.json'),
            'ledger_sha256':summary['ledger_sha256'],
            'recorded_cost_usd':sum(a.get('estimated_cost_usd') or 0 for x in records for a in x.get('attempts',[])),
            'unmetered_requests':sum(bool(x.get('upstream_dispatched')) and
                not any(a.get('usage') is not None for a in x.get('attempts',[])) for x in records),
            'unknown_cost_requests':sum(bool(x.get('upstream_dispatched')) and
                any(a.get('usage') is not None and a.get('estimated_cost_usd') is None
                    for a in x.get('attempts',[])) for x in records)})
        recorded_keys = {x['row']['bridge_task_key'] for x in summary['rows']}
        if any(path.name not in recorded_keys for path in (session/'episodes').iterdir()):
            fatal = 'Started episode missing saved result; no unproven replacement'
        for entry in summary['rows']:
            key = entry['row']['bridge_task_key']
            if key not in {driver.episode_key(x) for x in pending} or key in selected:
                raise ValueError('Unexpected/duplicate episode; stop')
            attempts[key] = attempts.get(key,0)+1
            if admitted(entry,jobs[key],contract):
                selected[key] = entry
            elif (not transport_retryable(entry['row'],Path(entry['episode']),records)
                    or attempts[key]>=contract['max_cell_attempts']):
                fatal = 'Nontransport invalid episode or exhausted cell attempts: '+key
        if summary['failures'] and any(x.get('reason')!='invalid_provider' and
                not x.get('reason','').startswith('IncompleteRead:') for x in summary['failures']):
            fatal = 'Nontransport session failure; preserve and stop'
        if len(selected)<40 and (not summary['failures'] or number==contract['max_transport_restarts']):
            fatal = fatal or 'Incomplete session or exhausted transport restarts'
        result = persist(root,contract,selected,sessions,fatal)
        print(json.dumps({'phase':'checkpoint','selected':len(selected),'session':number,'error':fatal}),flush=True)
        if fatal: raise RuntimeError(fatal)
        if len(selected)<40: time.sleep(5)
    result = persist(root,contract,selected,sessions)
    if not result['complete']: raise RuntimeError('Unique40cell matrix incomplete')
    print(json.dumps({'phase':'complete','episodes':40,'totals':result['totals'],
                      'cost_accounting_complete':result['cost_accounting_complete']}),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pilot',type=Path)
    parser.add_argument('--audit-source',type=Path)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--review',type=Path)
    args = parser.parse_args(); root = _require_run_child(args.output)
    if args.prepare:
        if args.pilot is None or args.audit_source is None: parser.error('prepare needs pilot/audit-source')
        prepare(args.config.resolve(),args.pilot.resolve(),args.audit_source.resolve(),root)
        print(json.dumps({'phase':'prepared','episodes':40,'contract_sha256':driver.sha(root/'validation_contract.json')}))
        return
    if args.review is None: parser.error('fresh Astra receipt required')
    driver.check_review(args.review,root/'validation_contract.json')
    run(json.loads(args.config.read_text()),root,json.loads((root/'validation_contract.json').read_text()))


if __name__=='__main__': main()
