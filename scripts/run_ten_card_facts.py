"""Ten-source A stage; guarded background execution, no automatic paid restart.

Uses the prepared complete histories without validation inputs. B/C and actor
evaluation require reviewed predecessor artifacts and separate executors.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil

import extract_chained_full_traces as facts
import continue_full_trace_facts as coverage
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json

REPO = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def scoped_root(path):
    path = path.resolve()
    require(Path(os.environ['VERUS_SKILL_RUN_ROOT']).resolve() in path.parents,
            'Output must be below configured run root')
    return path


def transport(root, paid=False):
    guards = []
    if paid:
        guards = [SharedBudgetGuard(root/name, approval_limit_usd=cap,
            prior_spend_usd=0, optimizer_reserve_usd=0, request_reserve_usd=0)
            for name,cap in [('budget-new-extraction.json',50),('budget-new-total.json',70)]]
    return GuardedDeepSeek(root=root/'calls',
        api_key=os.environ['DEEPSEEK_API_KEY'] if paid else 'offline', guards=guards,
        ledger=root/'provider_calls.jsonl', tokenizer_path=root/'tokenizer.json',
        tokenizer_sha256=facts.prior.old.TOKENIZER_SHA,capture_public_payloads=True)


def prepare(root, preparation, prior):
    require(not root.exists(), 'Fresh output root required')
    receipt=read(preparation/'receipt.json')
    require(all(sha(preparation/p)==h for p,h in receipt['files'].items()),'Preparation changed')
    require(receipt['paid_calls']==0 and receipt['old_draft_reserve_usd']==0,'Unexpected preparation')
    manifest=read(preparation/'training/manifest.json')
    train={r['id'] for r in read(REPO/'fixed-claude-stratified-80-seed20260814/train/items.json')}
    ids=[r['id'] for r in manifest['sources']]
    require(len(ids)==len(set(ids))==10 and set(ids)<=train,'Expected ten training sources')
    root.mkdir(parents=True)
    for name in ('sources','registries'):
        shutil.copytree(preparation/'training'/name,root/name)
    for name in ('config.json','tokenizer.json'):
        shutil.copyfile(prior/name,root/name)
    write_json(root/'authorization.json',{
        'basis':'User approved launching the prepared experiment in server background after directing reuse of existing old cards.',
        'new_extraction_cap_usd':50,'new_evaluation_cap_usd':20,'new_total_cap_usd':70,
        'historical_conservative_extraction_usd':9.351585716,
        'historical_settled_evaluation_usd':1.612713564,
        'accounting':'New experiment allowance is additional; historical ledgers remain unchanged. Later stages must inherit this experiment spend and total guard.',
        'destination':'https://api.deepseek.com','model':'deepseek-v4-pro','effort':'high',
        'stage_now':'A_facts_only','requests_now':10,'output_cap':65536,
        'automatic_paid_retry':False,'old_extraction_calls':0,'actor_calls_now':0,
        'gate':'Stop after A for source-based semantic review; schema pass is not semantic acceptance.',
        'preparation_root':str(preparation)})
    client=transport(root)
    calls=[]
    for row in manifest['sources']:
        ident=row['id']; request=read(preparation/'training/requests'/f'A-{ident}.json')
        require(request['cap']==65536 and request['system']==facts.FACT_SYSTEM,'Unexpected A settings')
        packet=facts.expand_strings(json.loads(request['user']))
        require(packet['complete_training_group']==read(root/'sources'/f'{ident}.json'),'Group mismatch')
        registry=read(root/'registries'/f'{ident}.json')
        require(packet['evidence_index']=={k:v for k,v in registry.items() if k!='source_texts'},'Registry mismatch')
        require(packet['output_contract']==facts.FACT_CONTRACT,'Wrong responsibility')
        require(registry['coverage']['excluded_direct_checks']==0,'Excluded direct checks')
        write_json(root/'requests'/f'A-{ident}.json',request)
        calls.append({'source_task':ident,'admission':client.admit(**request),
                      'reserve_usd':facts.prior.bound(client.payload(**request))})
    calls.sort(key=lambda c:-c['reserve_usd'])
    require(sum(c['reserve_usd'] for c in calls)<50,'A worst cases exceed extraction budget')
    paths=[p for p in root.rglob('*') if p.is_file()]
    paths += [Path(__file__),Path(facts.__file__),Path(coverage.__file__),Path(facts.prior.__file__),
              preparation/'receipt.json',REPO/'fixed-claude-stratified-80-seed20260814/train/items.json']
    paths += [REPO/'skillopt-verusage/src/skillopt_verusage'/f'{n}.py'
              for n in ['guarded_deepseek','budget_guard','text_context','codex_deepseek_bridge','campaign_evidence']]
    write_json(root/'contract.json',{'stage':'A_facts_only','calls':calls,
        'hashes':{str(p.resolve()):sha(p) for p in paths},
        'normalization':'Only trace-keyed coverage map to array with exact keys/values; no fact rewriting.',
        'individual_rejection':'Preserve raw and reject malformed individual facts; invalid JSON/envelope/coverage stops run.',
        'semantic_review_required':True,'sum_reserves_usd':sum(c['reserve_usd'] for c in calls)})
    print(json.dumps({'prepared':True,'requests':len(calls),'sum_reserves_usd':sum(c['reserve_usd'] for c in calls)}))


def check(root):
    contract=read(root/'contract.json')
    require(contract['stage']=='A_facts_only' and len(contract['calls'])==10,'Wrong executor contract')
    require(all(sha(p)==h for p,h in contract['hashes'].items()),'Frozen input or implementation changed')
    auth=read(root/'authorization.json')
    require((auth['new_extraction_cap_usd'],auth['new_evaluation_cap_usd'],auth['new_total_cap_usd'])==(50,20,70),'Changed caps')
    return contract


def run(root):
    contract=check(root)
    with (root/'execution.lock').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (root/'started.json').exists(),'No automatic restart/retry')
        write_json(root/'started.json',{'stage':'A','request_count':10})
        rows=[]
        try:
            facts.prior.old.prior.credentials(read(root/'config.json'))
            client=transport(root,paid=True)
            for call in contract['calls']:
                ident=call['source_task']
                print('A full training group '+ident,flush=True)
                text,usage=client.call(**read(root/'requests'/f'A-{ident}.json'),name='A-'+ident)
                # Always retain text before parsing; transport also saves raw response.
                (root/'facts').mkdir(exist_ok=True)
                (root/'facts'/f'{ident}.response.txt').write_text(text)
                value=json.loads(text)
                write_json(root/'facts'/f'{ident}.raw.json',value)
                registry=read(root/'registries'/f'{ident}.json')
                normalized,change=coverage.normalize_coverage(value,registry)
                write_json(root/'facts'/f'{ident}.normalized.json',normalized)
                admitted,decisions=facts.audit(normalized,registry)
                write_json(root/'facts'/f'{ident}.mechanical.json',admitted)
                write_json(root/'facts'/f'{ident}.audit.json',decisions)
                rows.append({'source_task':ident,'raw_facts':len(value['facts']),
                             'mechanical_pass':len(admitted),'normalization':change,'usage':usage})
                write_json(root/'progress.json',{'groups':rows,'completed_groups':len(rows),'semantic_accept':0})
                print(json.dumps({k:v for k,v in rows[-1].items() if k!='usage'}),flush=True)
            write_json(root/'completed.json',{'status':'A_complete_awaiting_semantic_review',
                'groups':rows,'B_calls':0,'C_calls':0,'actor_calls':0,'new_cards':0})
        except Exception as error:
            write_json(root/'stopped.json',{'type':type(error).__name__,'reason':str(error),
                'automatic_retry':False,'completed_groups':len(rows)})
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','check','run'])
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--preparation',type=Path)
    parser.add_argument('--prior',type=Path)
    args=parser.parse_args();root=scoped_root(args.output)
    if args.phase=='prepare':
        prepare(root,args.preparation,args.prior)
    elif args.phase=='check':
        check(root);print('Frozen input check passed')
    else:
        run(root)
