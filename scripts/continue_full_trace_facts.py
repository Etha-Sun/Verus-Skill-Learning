"""Lossless coverage-container adapter; continue only three unstarted full groups."""
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import extract_chained_full_traces as base
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json
read,require=base.read,base.require


def normalize_coverage(value,registry):
    out=copy.deepcopy(value)
    coverage=out.get('trace_coverage') if isinstance(out,dict) else None
    if isinstance(coverage,dict):
        require(set(coverage)==set(registry['traces']),'Coverage map missing/unknown trace')
        require(all(isinstance(row,dict) and row.get('trace_key')==key for key,row in coverage.items()),'Coverage map key disagrees with trace_key')
        out['trace_coverage']=[coverage[k] for k in sorted(coverage)]
        change='trace-keyed coverage object -> array; all values and facts unchanged'
    else:change='none'
    # Missing entries, source mismatches and altered quotes still use original gates.
    base.validate_coverage(out,registry)
    require(out['facts']==value['facts'],'Facts altered')
    return out,change


def prepare(root):
    base.check(root)
    require(read(root/'budget-amendment-applied.json')['extraction_usd']==25,'Budget amendment not applied')
    require(read(root/'stopped.json')['reason']=='Invalid arrays','Unexpected prior stop')
    contract=read(root/'contract.json');done=contract['calls'][0]['source_task']
    require(read(root/'budget-extraction.json')['settled_requests']==1,'Unexpected previous calls')
    raw=root/'facts'/f'{done}.raw.json';reg=read(root/'registries'/f'{done}.json')
    value,change=normalize_coverage(read(raw),reg)
    records,decisions=base.audit(value,reg)
    write_json(root/'facts'/f'{done}.shape-normalized.json',value)
    write_json(root/'facts'/f'{done}.mechanical.json',records)
    write_json(root/'facts'/f'{done}.audit.json',decisions)
    remaining=[row['source_task'] for row in contract['calls'][1:]]
    require(all(not (root/'calls'/('facts-'+ident)).exists() for ident in remaining),'Continuation would revisit a sent request')
    paths=[Path(__file__),Path(base.__file__),raw,root/'budget-amendment-approved.json',root/'budget-amendment-applied.json']
    paths += [root/'requests'/f'facts-{ident}.json' for ident in remaining]
    write_json(root/'facts-continuation-contract.json',{'remaining':remaining,'completed_group':done,
        'completed_row':{'source_task':done,'raw_facts':len(value['facts']),'mechanical_pass':len(records)},
        'representation_change':change,'new_paid_calls':3,'paid_retries':0,
        'authorization':'Existing full-extraction authorization, plus explicit cumulative USD25/USD33 amendment; only unstarted requests.',
        'input_hashes':{str(p.resolve()):base.prior.old.sha(p) for p in paths},
        'policy':'Apply same lossless coverage-container adapter to remaining groups; raw results unchanged, semantic review still required.'})
    print(json.dumps({'first_group':done,'raw_facts':len(value['facts']),'mechanical_pass':len(records),'remaining_requests':3,'paid_retry':False}),flush=True)


def run(root):
    base.check(root);c=read(root/'facts-continuation-contract.json')
    require(all(base.prior.old.sha(p)==h for p,h in c['input_hashes'].items()),'Continuation input changed')
    with (root/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (root/'facts-continuation-started.json').exists(),'No automatic continuation restart')
        require(all(not (root/'calls'/('facts-'+i)).exists() for i in c['remaining']),'Previously started request')
        write_json(root/'facts-continuation-started.json',{'paid_retries':0})
        try:
            a=read(root/'authorization.json')
            guards=[SharedBudgetGuard(root/n,approval_limit_usd=cap,prior_spend_usd=a['conservative_inherited_usd'],optimizer_reserve_usd=0,request_reserve_usd=0)
                for n,cap in [('budget-total.json',33),('budget-extraction.json',25)]]
            base.prior.old.prior.credentials(read(root/'config.json'))
            transport=GuardedDeepSeek(root=root/'calls',api_key=os.environ['DEEPSEEK_API_KEY'],guards=guards,
                ledger=root/'provider_calls.jsonl',tokenizer_path=root/'tokenizer.json',
                tokenizer_sha256=base.prior.old.TOKENIZER_SHA,capture_public_payloads=True)
            rows=[c['completed_row']]
            for ident in c['remaining']:
                print('Recording unstarted full group '+ident,flush=True)
                text,_=transport.call(**read(root/'requests'/f'facts-{ident}.json'),name='facts-'+ident)
                raw=json.loads(text);write_json(root/'facts'/f'{ident}.raw.json',raw)
                registry=read(root/'registries'/f'{ident}.json')
                value,change=normalize_coverage(raw,registry)
                write_json(root/'facts'/f'{ident}.shape-normalized.json',value)
                records,decisions=base.audit(value,registry)
                write_json(root/'facts'/f'{ident}.mechanical.json',records)
                write_json(root/'facts'/f'{ident}.audit.json',decisions)
                rows.append({'source_task':ident,'raw_facts':len(raw['facts']),'mechanical_pass':len(records),'representation_change':change})
                write_json(root/'progress.json',{'completed_groups':rows,'semantic_accept':0})
                print(json.dumps(rows[-1]),flush=True)
            write_json(root/'facts-completed.json',{'status':'facts_complete_awaiting_semantic_review','groups':rows,
                'interpretation_calls':0,'action_calls':0,'deployed_cards':0,'actor_episodes':0,'paid_retries':0})
        except Exception as e:
            write_json(root/'facts-continuation-stopped.json',{'type':type(e).__name__,'reason':str(e),'automatic_retry':False})
            raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['prepare','run']);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();{'prepare':prepare,'run':run}[a.phase](a.output)
