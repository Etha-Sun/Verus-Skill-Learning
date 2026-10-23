"""Ten-source B stage: full histories, reviewed A, shared incremental budget.

No automatic restart or retry. Stop at B outputs for semantic review before C.
Historical A/B executors and their frozen contracts are unchanged.
"""
from __future__ import annotations
import argparse
import fcntl
import os
from pathlib import Path
import shutil

import run_ten_card_facts as a
import interpret_full_trace_facts as b
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json

read, sha, require = a.read, a.sha, a.require
CAP = 65536
SYSTEM = b.SYSTEM + '''\nSupplemental records include comparator/tool-help commands as context, not all
are verifier checks. A shell exit code of zero after an echo does not establish
that Verus or the proof-only comparator succeeded; inspect the actual output.
Use review_note qualifications with the original fact. A factual endpoint summary
is not evidence that every intermediate source was checked. Do not turn the
historical source expressions into a general prescription.\n'''


def client(root, parent, paid=False):
    guards = []
    if paid:
        # Use exactly the existing experiment ledgers; no copied/reset allowance.
        guards = [SharedBudgetGuard(parent/name, approval_limit_usd=cap,
                    prior_spend_usd=0, optimizer_reserve_usd=0, request_reserve_usd=0)
                  for name, cap in [('budget-new-extraction.json', 50), ('budget-new-total.json', 70)]]
    return GuardedDeepSeek(root=root/'calls', api_key=os.environ['DEEPSEEK_API_KEY'] if paid else 'offline',
        guards=guards, ledger=root/'provider_calls.jsonl', tokenizer_path=root/'tokenizer.json',
        tokenizer_sha256=b.base.prior.old.TOKENIZER_SHA, capture_public_payloads=True)


def budget_snapshot(parent):
    states = {name: read(parent/name) for name in ['budget-new-extraction.json', 'budget-new-total.json']}
    for name, cap in [('budget-new-extraction.json',50), ('budget-new-total.json',70)]:
        s=states[name]
        require(s['approval_limit_usd']==cap and s['prior_spend_usd']==0 and s['optimizer_reserve_usd']==0,
                'Changed shared budget configuration')
        require(not s['reservations'] and not s['uncertain_requests'], 'Unsettled or unknown prior cost')
    return states


def make_request(previous, facts, supplemental):
    request = b.make_request(previous, facts, supplemental)
    request.update(system=SYSTEM, cap=CAP)
    return request


def prepare(root, parent):
    a.check(parent)
    require(read(parent/'completed.json')['status']=='A_complete_awaiting_semantic_review','A incomplete')
    handoff=read(parent/'semantic-review-v1/interpretation-handoff.json')
    require(handoff['status']=='review_complete_not_dispatched','A review not ready')
    for key in ['review','accepted_facts','supplemental_index']:
        require(sha(parent/handoff[key])==handoff[key+'_sha256'],'Handoff hash mismatch')
    review=read(parent/handoff['review'])
    require(review['complete'] and all(sha(parent/p)==h for p,h in review['input_sha256'].items()),'Reviewed inputs changed')
    accepted=read(parent/handoff['accepted_facts'])['facts']
    require(len(accepted)==review['counts']['accepted_facts'],'Fact count mismatch')
    decisions={d['fact_id']:d for d in review['decisions']}
    for f in accepted:
        d=decisions[f['fact_id']]
        require(d['semantic_status']=='accept_fact' and d['eligible_for_interpretation'],'Unreviewed fact')
        require(f['fact_sha256']==d['fact_sha256']==b.base.prior.digest(b.json.dumps(f['fact'],sort_keys=True,ensure_ascii=False)), 'Fact content changed')
    ids=[g['source_task'] for g in handoff['full_groups']]
    train={row['id'] for row in read(a.REPO/'fixed-claude-stratified-80-seed20260814/train/items.json')}
    require(len(ids)==len(set(ids))==10 and set(ids)<=train,'Expected ten training groups')
    require({f['source_task'] for f in accepted}==set(ids),'Missing reviewed source')
    states=budget_snapshot(parent)
    approval=read(parent/'explicit-launch-approval.json')
    require(approval and read(parent/'authorization.json')['destination']=='https://api.deepseek.com','Destination approval missing')
    require(not root.exists(),'Fresh B root required')
    root.mkdir(parents=True)
    for name in ['config.json','tokenizer.json']:shutil.copyfile(parent/name,root/name)
    write_json(root/'authorization.json',{
        'basis':'Existing explicit ten-group training transfer and USD50/20/70 authorization; user agreed FOUR_ARM_ON_DEMAND_PLAN and explicitly permitted API continuation.',
        'destination':'https://api.deepseek.com','model':'deepseek-v4-pro','effort':'high','output_cap':CAP,
        'requests_now':10,'stage':'B_interpretation_only','automatic_paid_retry':False,
        'parent_root':str(parent),'shared_ledger_root':str(parent),
        'new_extraction_cap_usd':50,'new_evaluation_cap_usd':20,'new_total_cap_usd':70,
        'prior_stage_spend_included':True,'C_calls_now':0,'actor_calls_now':0})
    write_json(root/'budget-at-preparation.json',states)
    extra=read(parent/handoff['supplemental_index']);transport=client(root,parent);rows=[]
    for ident in ids:
        facts=[f for f in accepted if f['source_task']==ident]
        supplemental={'recognizer':extra['recognizer'],'records':[x for x in extra['records'] if x['source_task']==ident]}
        request=make_request(read(parent/'requests'/f'A-{ident}.json'),facts,supplemental)
        restored=b.expand_strings(b.json.loads(request['user']))
        require(restored['complete_training_group']==read(parent/'sources'/f'{ident}.json'),'History changed')
        write_json(root/'requests'/f'B-{ident}.json',request)
        write_json(root/'facts'/f'{ident}.json',facts)
        rows.append({'source_task':ident,'accepted_facts':len(facts),'admission':transport.admit(**request),
                     'reserve_usd':b.base.prior.bound(transport.payload(**request))})
    rows.sort(key=lambda x:-x['reserve_usd'])
    reserve=sum(r['reserve_usd'] for r in rows)
    for state in states.values():
        require(state['target_spend_usd']+state['uncertain_spend_usd']+reserve<=state['approval_limit_usd'],
                'B full-batch reserve exceeds remaining allowance')
    paths=[p for p in root.rglob('*') if p.is_file()]
    paths += [parent/'explicit-launch-approval.json',parent/'authorization.json',parent/'semantic-review-v1/interpretation-handoff.json']
    paths += [parent/handoff[k] for k in ['review','accepted_facts','supplemental_index']]
    paths += [Path(__file__),Path(a.__file__),Path(b.__file__),Path(b.base.__file__),Path(b.base.prior.__file__),Path(b.base.prior.old.__file__)]
    paths += [a.REPO/'skillopt-verusage/src/skillopt_verusage'/f'{n}.py' for n in
              ['guarded_deepseek','budget_guard','codex_deepseek_bridge','text_context','campaign_evidence']]
    hashes={str((parent/p).resolve()):h for p,h in review['input_sha256'].items()}
    hashes.update({str(p.resolve()):sha(p) for p in paths})
    write_json(root/'contract.json',{'stage':'B_interpretation_only','parent_root':str(parent),'calls':rows,
        'hashes':hashes,'cap':CAP,'sum_reserves_usd':reserve,'full_groups_preserved':True,
        'raw_facts_unchanged':True,'accepted_facts':len(accepted),
        'stop':'Review B semantically before C. No automatic paid retry or whole-chain launch.'})
    write_json(root/'offline-summary.json',{'prepared':True,'requests':len(rows),'accepted_facts':len(accepted),
        'output_cap':CAP,'A_settled_usd':states['budget-new-extraction.json']['target_spend_usd'],
        'B_conservative_reserve_usd':reserve,'shared_extraction_cap_usd':50,'shared_total_cap_usd':70})
    print(b.json.dumps(read(root/'offline-summary.json')),flush=True)


def check(root):
    c=read(root/'contract.json')
    require(c['stage']=='B_interpretation_only' and c['cap']==CAP and len(c['calls'])==10,'Unexpected B contract')
    require(all(sha(p)==h for p,h in c['hashes'].items()),'Frozen B input or implementation changed')
    auth=read(root/'authorization.json')
    require(auth['shared_ledger_root']==c['parent_root'] and auth['destination']=='https://api.deepseek.com','Wrong ledger/destination')
    require((auth['new_extraction_cap_usd'],auth['new_evaluation_cap_usd'],auth['new_total_cap_usd'])==(50,20,70),'Wrong caps')
    return c


def run(root):
    c=check(root);parent=Path(c['parent_root'])
    with (parent/'execution.lock').open('a') as previous_lock, (root/'execution.lock').open('a') as lock:
        for handle in [previous_lock,lock]:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (root/'started.json').exists(),'No automatic B restart/retry')
        budget_snapshot(parent)
        write_json(root/'started.json',{'stage':'B','requests':len(c['calls']),'output_cap':CAP})
        rows=[]
        try:
            b.base.prior.old.prior.credentials(read(root/'config.json'))
            transport=client(root,parent,paid=True)
            for row in c['calls']:
                check(root);budget_snapshot(parent)
                ident=row['source_task'];print('B full training group '+ident,flush=True)
                response,usage=transport.call(**read(root/'requests'/f'B-{ident}.json'),name='B-'+ident)
                (root/'interpretations').mkdir(exist_ok=True)
                (root/'interpretations'/f'{ident}.response.txt').write_text(response)
                value=b.json.loads(response)
                write_json(root/'interpretations'/f'{ident}.raw.json',value)
                admitted,decisions=b.audit(value,read(root/'facts'/f'{ident}.json'))
                write_json(root/'interpretations'/f'{ident}.mechanical.json',admitted)
                write_json(root/'interpretations'/f'{ident}.audit.json',decisions)
                rows.append({'source_task':ident,'raw_interpretations':len(value['interpretations']),
                    'mechanical_pass':len(admitted),'uninterpreted_facts':len(value['uninterpreted_facts']),'usage':usage})
                write_json(root/'progress.json',{'completed_groups':len(rows),'groups':rows,'semantic_accept':0})
                print(b.json.dumps({k:v for k,v in rows[-1].items() if k!='usage'}),flush=True)
            write_json(root/'completed.json',{'status':'B_complete_awaiting_semantic_review','groups':rows,'C_calls':0,'actor_calls':0})
        except Exception as error:
            write_json(root/'stopped.json',{'type':type(error).__name__,'reason':str(error),'completed_groups':len(rows),'automatic_retry':False})
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','check','run']);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--parent',type=Path)
    args=parser.parse_args();root=a.scoped_root(args.output)
    if args.phase=='prepare':prepare(root,a.scoped_root(args.parent))
    elif args.phase=='check':check(root);print('Frozen B input check passed')
    else:run(root)
