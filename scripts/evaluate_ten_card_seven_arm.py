"""Seven-arm ten-card on-demand development evaluation,112cells,sharedUSD20/70 guards.

No extraction, full-body injection, task-routed skeleton, or automatic paid retry.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime,timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from functools import lru_cache

import evaluate_card_organization as prior
import evaluate_structural_skeleton_hard as hard
import run_ten_card_representations as representation
from continue_card_organization_evaluation import result_dimensions
from skillopt_verusage.card_bank import AUTONOMOUS_CARD_READER, AUTONOMOUS_RETRIEVAL_INSTRUCTIONS
from skillopt_verusage.guarded_deepseek import BudgetMux,write_json
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.skill_artifact import load_skill_artifact

REPO=Path(__file__).resolve().parents[1]
read,sha,require=representation.read,representation.sha,representation.require
ARMS=('no_skill','old_prose','old_skeleton','old_pseudocode','new_prose','new_skeleton','new_pseudocode')
AUTH={'episodes':112,'tasks':8,'repeats':2,'cards_per_skill_arm':10,'no_skill_cards':0,'timeout_seconds':600,'workers':2,
      'evaluation_usd':20,'new_total_usd':70,'destination':'https://api.deepseek.com','automatic_paid_retry':False,
      'basis':'User authorized actor launch with the selected validation tasks repeated twice and explicitly selected seven groups retaining all prior arms; existing DeepSeek data-transfer approval and USD20 evaluation/USD70 cumulative caps persist.'}
# Same neutral reading instructions for both representations; avoid requiring prose-only headings.
READING=AUTONOMOUS_RETRIEVAL_INSTRUCTIONS.replace('Check Trigger and Avoid when against the current state, perform required',
    'Check applicability and rejection conditions against the current state, perform required')


def schedule(tasks):
    jobs=[]
    for repeat in range(2):
        for position,task in enumerate(tasks):
            offset=(position+repeat)%len(ARMS);order=ARMS[offset:]+ARMS[:offset]
            if repeat%2:order=tuple(reversed(order))
            for arm in order:jobs.append({'id':task['id'],'condition':arm,'repeat':repeat})
    return jobs


def make_bundle(bank,index,executive,destination):
    require(len(bank['cards'])==len(index['cards'])==10,'Expected10card bank/index')
    require(all(set(x)=={'id','content'} for x in bank['cards']),'Private metadata in actor bank')
    require([x['id'] for x in bank['cards']]==[x['id'] for x in index['cards']],'Index order/IDs differ')
    destination.mkdir(parents=True,exist_ok=False)
    skill=executive.rstrip()+'\n'+READING+'\n## Card index\n\n'
    skill+='\n'.join('- '+x['id']+': '+x['title']+' — '+x['description'] for x in index['cards'])+'\n'
    (destination/'SKILL.md').write_text(skill)
    write_json(destination/'cards.json',bank)
    (destination/'card_read.py').write_text(AUTONOMOUS_CARD_READER)
    return load_skill_artifact(destination).manifest()


def guards(root,ledger):
    shared_eval=Path(read(root/'budget-baseline.json')['evaluation_ledger'])
    return [SharedBudgetGuard(shared_eval,approval_limit_usd=20,prior_spend_usd=0,optimizer_reserve_usd=0,request_reserve_usd=0),
            SharedBudgetGuard(ledger/'budget-new-total.json',approval_limit_usd=70,prior_spend_usd=0,optimizer_reserve_usd=0,request_reserve_usd=0)]



class HistoricalUncertaintyMux(BudgetMux):
    """Keep a reviewed stopped-run uncertainty charge; halt on any NEW unknown charge.

    Uses the same existing ledgers/caps; does not settle, waive, release or retry
    the historical request. SharedBudgetGuard includes that full reserve in cost.
    """
    def __init__(self, guards, baseline):
        super().__init__(guards)
        self.baseline = baseline

    def reserve(self, amount_usd):
        reservations=[]
        try:
            for guard in self.guards:
                state=guard._update(lambda s:s)
                old=self.baseline[str(guard.path)]
                require(state['uncertain_requests']==old['uncertain_requests'] and
                        abs(state['uncertain_spend_usd']-old['uncertain_spend_usd'])<1e-9,
                        'New unknown provider cost: stop, no automatic retry')
                require(state['target_spend_usd']+1e-9>=old['target_spend_usd'], 'Historical costs decreased')
                reservations.append(guard.reserve(amount_usd,wait_timeout_seconds=0))
        except Exception:
            for guard,key in zip(self.guards,reservations):
                guard._update(lambda state,key=key:state['reservations'].pop(key))
            raise
        return json.dumps(reservations)


def make_no_skill_bundle(executive,destination):
    destination.mkdir(parents=True,exist_ok=False)
    (destination/'SKILL.md').write_text(executive.rstrip()+'\n')
    return load_skill_artifact(destination).manifest()

def preflight(root,config,parent):
    results=[];library=Path(config['verus_bin']).parent/'vstd'
    for arm in ARMS:
        workspace=root/'preflight'/arm;shutil.copytree(root/'bundles'/arm,workspace)
        hidden=[REPO/'AGENTS.md',root/'config.json',Path(config['env_file']),parent/'semantic-review-v1/review.json',
                parent.parent/'on-demand-ten-card-actions-20261021-v1/semantic-review-v1/selected-content.json']
        hidden += [root/'bundles'/other/'cards.json' for other in ARMS if other!=arm]
        # The benchmark repository, raw data and all sibling runs are hidden by scratch namespace.
        hidden += [REPO/read(root/'task-selection.json')['tasks'][0]['source_path']]
        write_json(workspace/'probe.json',{'hidden':list(map(str,hidden)),'library':str(library),'verus':config['verus_bin'],
          'lynette':config['lynette_bin'],'codex':config['codex_bin'],'skill_sha':sha(workspace/'SKILL.md'),'bank_sha':sha(workspace/'cards.json') if arm!='no_skill' else None,'expected_cards':0 if arm=='no_skill' else 10})
        code='''import json,hashlib,socket,subprocess
from pathlib import Path
s=json.loads(Path('probe.json').read_text())
for name in s['hidden']:
    try: Path(name).read_bytes()
    except OSError: pass
    else: raise AssertionError('Private material visible: '+name)
for name,k in [('SKILL.md','skill_sha')]+([('cards.json','bank_sha')] if s['expected_cards'] else []):
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==s[k]
bank=json.loads(Path('cards.json').read_text())['cards'] if s['expected_cards'] else []
assert len(bank)==s['expected_cards']
if not s['expected_cards']:
    assert not Path('cards.json').exists() and not Path('card_read.py').exists()
for card in bank:
    assert set(card)=={'id','content'}
    r=subprocess.run(['/usr/bin/python3','card_read.py',card['id']],capture_output=True,text=True,check=True)
    p=json.loads(r.stdout);assert p['content']==card['content'] and p['id']==card['id']
p=Path(s['library'])/'set.rs';assert p.read_bytes()
try:p.open('r+b')
except OSError:pass
else:raise AssertionError('Library writable')
try:socket.create_connection(('1.1.1.1',443),timeout=1)
except OSError:pass
else:raise AssertionError('External network reachable')
Path('input.rs').write_text('use vstd::prelude::*;\\nverus! { proof fn probe() {} }\\nfn main() {}\\n')
Path('candidate.rs').write_text(Path('input.rs').read_text().replace('probe() {}','probe() { assert(1int == 1int); }'))
for cmd in [[s['verus'],'candidate.rs'],[s['lynette'],'compare','-t','input.rs','candidate.rs']]:
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=45);assert r.returncode==0,r.stdout+r.stderr
print('PASS',len(bank),'reader payloads; private/other banks hidden; library RO; network blocked; Verus+Lynette')
'''
        isolation=prior.ActorIsolationConfig(Path(config['scratch_root']),library.parent,Path(config['rust_root']),18136,
            (REPO,parent,Path(config['env_file']),Path(config['data_root']),root/'config.json'))
        command=prior.build_isolated_actor_command(['/usr/bin/python3','-c',code],workspace=workspace,
            codex_bin=Path('/usr/bin/python3'),lynette_bin=Path(config['lynette_bin']),config=isolation)
        result=subprocess.run(command,env=prior._codex_environment(None),capture_output=True,text=True,timeout=60)
        results.append({'arm':arm,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'isolation':isolation.manifest()})
        write_json(root/'preflight.json',{'paid_calls':0,'checks':results})
        require(result.returncode==0,'Isolation/reader/tool preflight failed '+arm+': '+result.stderr[-1200:])
        command=prior.build_isolated_actor_command([config['codex_bin'],'--version'],workspace=workspace,
            codex_bin=Path(config['codex_bin']),lynette_bin=Path(config['lynette_bin']),config=isolation)
        version=subprocess.run(command,env=prior._codex_environment(None),capture_output=True,text=True,timeout=30)
        results[-1]['codex_version']={'returncode':version.returncode,'stdout':version.stdout,'stderr':version.stderr}
        write_json(root/'preflight.json',{'paid_calls':0,'checks':results})
        require(version.returncode==0 and '0.147.0' in version.stdout,'Codex isolated version check failed')


def prepare(root,parent,pseudocode,previous,selection_path,executive_path):
    representation.check(parent)
    frozen=read(parent/'semantic-review-v1/freeze.json')
    require(frozen['status']=='four_banks_semantically_reviewed' and all(sha(p)==h for p,h in frozen['files'].items()),'Representation review not frozen')
    material_review=read(parent/'semantic-review-v1/review.json')
    require(material_review['complete'] and all(sha(p)==h for p,h in material_review['input_hashes'].items()),'Source material changed')
    pc=read(parent/'contract.json');ledger=Path(pc['shared_ledger_root'])
    pf=read(pseudocode/'freeze.json')
    require(all(sha(pseudocode/p)==h for p,h in pf['files'].items()),'Pseudocode freeze changed')
    require(all(sha(p)==h for p,h in pf['source_hashes'].items()),'Pseudocode sources changed')
    require((previous/'stopped.json').exists() and read(previous/'summary.json')['bridge_drained'],'Previous run not stopped/drained')
    eval_path=previous/'budget-evaluation.json';total_path=ledger/'budget-new-total.json'
    states={str(p):read(p) for p in [eval_path,total_path]}
    require(all(not v['reservations'] for v in states.values()),'Historical requests in flight')
    require(states[str(eval_path)]['approval_limit_usd']==20 and states[str(total_path)]['approval_limit_usd']==70,'Wrong shared caps')
    baseline={'evaluation_ledger':str(eval_path),'total_ledger':str(total_path),'states':states,
      'prior_run':str(previous),'handling':'Retain full known historical uncertainty; only new experiment calls authorized. New unknown cost halts. No replay of the old failed request.'}
    selection=read(selection_path);tasks=selection['tasks'];require(len(tasks)==8,'Expected8devtasks')
    require(sum(t['provisional_relevance']=='strong' for t in tasks)==4,'Expected4strong/4partial')
    for t in tasks:require(sha(REPO/t['source_path'])==t['source_sha256'],'Selected task changed')
    require(not root.exists(),'Fresh evaluation root required');root.mkdir(parents=True)
    config=read(parent/'config.json');config['repo']=str(REPO)
    for k in ['codex_bin','lynette_bin']:require(sha(config[k])==prior.HISTORICAL[k],'Actor tool changed '+k)
    require(sha(config['catalog'])==prior.HISTORICAL['models.json'],'Model catalog changed')
    require(sha(Path(config['verus_bin']).parent/'rust_verify')==prior.LOCAL_RUST_VERIFY,'Verifier changed')
    (root/'runtime').mkdir();shutil.copyfile(config['catalog'],root/'runtime/models.json');config['source_root']=str(root/'runtime')
    shutil.copyfile(parent/'tokenizer.json',root/'runtime/tokenizer.json')
    write_json(root/'config.json',config);write_json(root/'authorization.json',AUTH)
    write_json(root/'budget-at-preparation.json',states);write_json(root/'budget-baseline.json',baseline)
    selection['status']='frozen_before_actor';selection['review']='Retain preselected4strong/4partial dev strata. Final bank coverage differs across content families; not guarantees of applicability or success.'
    selection['coverage_notes']={
      'strong':'Rely/Unpack/forall: old058/076 and new003/005 offer premise/instance checks; stability:old062/new006 inspect composition. Whole-card representation preserves within-family coverage.',
      'partial':'DeMorgan: outer equality/scope only, no duality recipe. Rank: temporal premise overlap, rank argument missing. Filter: old037 element facts broader than new002 packet-loop entry; new004 set-image witness also not a filter solution. Deserialize: old022 concrete fold and new007 closed conversion interface differ; neither provides decoder proof. Cross-content comparison is package-level, not matched task-specific knowledge.'}
    write_json(root/'task-selection.json',selection)
    executive=executive_path.read_text();(root/'EXECUTIVE.md').write_text(executive)
    (root/'TASK.md').write_text(prior.build_prompt(installed_library_root=Path(config['verus_bin']).parent/'vstd'))
    artifacts={};exposure={}
    for arm in ARMS:
        if arm=='no_skill':
            artifacts[arm]=make_no_skill_bundle(executive,root/'bundles'/arm)
            exposure[arm]={'ids':[],'body_bytes':0,'entrypoint_bytes':len(executive.encode()),'full_bodies_in_prompt':False,'baseline':'Same Executive only; no index, card bank or reader'}
            continue
        family=arm.split('_')[0]
        bank=read(pseudocode/'banks'/f'{arm}.json') if arm.endswith('_pseudocode') else read(parent/'semantic-review-v1/banks'/f'{arm}.json')
        index=read(parent/'indexes'/f'{family}.json')
        artifacts[arm]=make_bundle(bank,index,executive,root/'bundles'/arm)
        exposure[arm]={'ids':[x['id'] for x in bank['cards']],'entrypoint_bytes':len((root/'bundles'/arm/'SKILL.md').read_bytes()),
          'body_bytes':sum(len(x['content'].encode()) for x in bank['cards']),'full_bodies_in_prompt':False,'forced_read_count':None}
    for f in ['old','new']:
        require(len({(root/'bundles'/f'{f}_{kind}/SKILL.md').read_bytes() for kind in ['prose','skeleton','pseudocode']})==1,'Paired index differs')
    write_json(root/'exposure.json',exposure)
    preflight(root,config,parent)
    contract=prior.driver.prepare(root/'config.json',root/'bundles/old_prose',root/'bundles/new_prose',root,
         task_ids=tuple(x['id'] for x in tasks),installed_library_conditions=('old','revised'))
    contract.update(schema_version='ten-card-seven-arm-on-demand-v1',authorization=AUTH,artifacts=artifacts,
       bundle_paths={a:str(root/'bundles'/a) for a in ARMS},installed_library_conditions=list(ARMS),schedule=schedule(tasks),
       expected_episodes=112,repeats=2,budget_usd=20,total_cap_usd=70,timeout_seconds=600,workers=2,
       model_context_window=1048576,max_output_tokens_per_request=131072,provider_request_timeout_seconds=1800,
       transport_retry=False,shared_ledger_root=str(ledger),parent_materials=str(parent),
       extraction_settled_before_eval_usd=read(ledger/'budget-new-extraction.json')['target_spend_usd'],pseudocode_materials=str(pseudocode),previous_evaluation=str(previous),evaluation_ledger=str(eval_path),
       retrieval='Autonomous card_read; no search ranking, forced body read or task-selected skeleton. Index/body file reads remain observable; direct reads are flagged for review.',
       caveat='Known8development tasks x7arms x2 repeats,16runs but8independent tasks per arm; not held-out evidence. No_skill is Executive-only, not an unprompted actor. Pseudocode is Codex-authored and development-informed; numbered skeleton is distinct. New content includes8Codex revisions; skeletons8representation repairs. Within-family index identical; cross-family index/content package differs. Budget may stop incomplete112matrix; no automatic retries.')
    paths=[p for p in root.rglob('*') if p.is_file() and p.name!='validation_contract.json' and 'preflight' not in p.parts]
    paths += [root/'preflight.json',executive_path,selection_path,parent/'semantic-review-v1/freeze.json',parent/'explicit-card-transfer-approval.json',pseudocode/'freeze.json',previous/'explicit-evaluation-transfer-approval.json',previous/'stopped.json',previous/'summary.json']
    for folder in ['scripts','skill-evolution-pilot/src','skillopt-verusage/src']:paths+=list((REPO/folder).rglob('*.py'))
    paths += [p for p in Path(config['verus_bin']).parent.rglob('*') if p.is_file()]
    paths += [Path(config['rust_root'])/'rustup/toolchains/1.88.0-x86_64-unknown-linux-gnu/bin/rustc']
    contract['input_hashes'].update({str(pseudocode/p):h for p,h in pf['files'].items()});contract['input_hashes'].update(frozen['files']);contract['input_hashes'].update({str(p.resolve()):sha(p) for p in paths})
    write_json(root/'validation_contract.json',contract)
    write_json(root/'review_receipt.json',{'decision':'APPROVE_WITH_NONBLOCKING_NOTES','contract_sha256':sha(root/'validation_contract.json'),
       'reviewer':'Codex wiring/material/isolation review, not independent review','paid_calls':0,'blocking_issues':[],'nonblocking_notes':[contract['caveat']]})
    guards(root,ledger);check(root)
    write_json(root/'offline-summary.json',{'episodes':112,'tasks':8,'arms':list(ARMS),'repeats':2,'seconds':600,'workers':2,'eval_cap_usd':20,'total_cap_usd':70,
       'prior_extraction_usd':contract['extraction_settled_before_eval_usd'],'preflight_arms':7,'paid_calls':0})
    print(json.dumps(read(root/'offline-summary.json')),flush=True)


def check(root):
    x=read(root/'validation_contract.json')
    require(x['schema_version']=='ten-card-seven-arm-on-demand-v1' and x['authorization']==AUTH,'Wrong evaluation contract')
    expected={'expected_episodes':112,'repeats':2,'budget_usd':20,'total_cap_usd':70,'timeout_seconds':600,'workers':2,
       'model':'deepseek-v4-pro','reasoning_effort':'max','max_output_tokens_per_request':131072,'model_context_window':1048576,
       'ordinary_retry':False,'transport_retry':False,'reference_proof_supplied':False,'sealed_test_access':False,'installed_library_conditions':list(ARMS)}
    require(all(x[k]==v for k,v in expected.items()),'Scope/model/budget changed')
    require(x['schedule']==schedule(read(root/'task-selection.json')['tasks']),'Matrix changed')
    require(all('knowledge_path' not in job for job in x['schedule']),'Forced knowledge exposure')
    require(all(sha(p)==h for p,h in x['input_hashes'].items()),'Frozen evaluation inputs changed')
    checks=read(root/'preflight.json')['checks'];require(len(checks)==7 and all(p['returncode']==0 for p in checks),'Preflight incomplete')
    for f in ['old','new']:require(len({(root/'bundles'/f'{f}_{kind}/SKILL.md').read_bytes() for kind in ['prose','skeleton','pseudocode']})==1,'Paired index changed')
    require({p.name for p in (root/'bundles/no_skill').iterdir()}=={'SKILL.md'},'Card material in no-skill arm')
    require((root/'bundles/no_skill/SKILL.md').read_text()==(root/'EXECUTIVE.md').read_text().rstrip()+'\n','No-skill Executive differs')
    prior.driver.check_review(root/'review_receipt.json',root/'validation_contract.json');return x


@lru_cache(maxsize=1)
def tokenizer(path):
    from tokenizers import Tokenizer
    return Tokenizer.from_file(path)


def audit_reads(raw_events,root):
    arm=raw_events.parent.name.split('--')[0].removeprefix('dev_');require(arm in ARMS,'Unknown episode arm')
    bank={x['id']:x['content'] for x in read(root/'bundles'/arm/'cards.json')['cards']} if arm!='no_skill' else {}
    events=[];errors=[];direct=[];mentions=[];first_edit=None
    if not raw_events.exists():return {'read_calls':0,'audit_incomplete':True}
    for order,line in enumerate(raw_events.read_text().splitlines()):
        try:event=json.loads(line)
        except ValueError:errors.append({'order':order,'error':'malformed event'});continue
        item=event.get('item',{});typ=item.get('type')
        if event.get('type')!='item.completed':continue
        if typ=='file_change' and first_edit is None:first_edit=order
        if typ=='agent_message':
            ids=re.findall(r'\b(?:card|new)-\d{3,}\b',item.get('text',''))
            if ids:mentions.append({'order':order,'ids':sorted(set(ids)),'text':item.get('text')})
        if typ!='command_execution':continue
        command=str(item.get('command',''))
        if 'cards.json' in command:direct.append({'order':order,'command':command,'reason':'possible direct/bulk access; manual exposure review required'})
        for output in str(item.get('aggregated_output','')).splitlines():
            try:p=json.loads(output)
            except ValueError:continue
            if not isinstance(p,dict) or p.get('card_retrieval')!=1:continue
            if p.get('operation')!='read' or p.get('id') not in bank or p.get('content')!=bank.get(p.get('id')):
                errors.append({'order':order,'id':p.get('id'),'error':'reader error or mismatched frozen payload'});continue
            content=p['content'];tok=tokenizer(str(root/'runtime/tokenizer.json'))
            events.append({'order':order,'id':p['id'],'item_id':item.get('id'),'content_sha256':hashlib.sha256(content.encode()).hexdigest(),
              'content_bytes':len(content.encode()),'body_tokens':len(tok.encode(content,add_special_tokens=False).ids),
              'before_first_file_edit':first_edit is None})
    return {'read_calls':len(events),'read_ids':sorted({e['id'] for e in events}),'events':events,'reader_errors':errors,
        'body_bytes':sum(e['content_bytes'] for e in events),'body_tokens':sum(e['body_tokens'] for e in events),'first_file_edit_order':first_edit,
        'direct_bank_access_commands':direct,'agent_card_mentions':mentions,'application_correctness':'requires manual trace review',
        'caveat':'Exact frozen helper payload exposure, not adoption. Static tokenizer counts include repeated reads; direct/partial reads need manual audit.'}


def report(root):
    summary=read(root/'summary.json');jobs={prior.driver.episode_key(x):x for x in read(root/'validation_contract.json')['schedule']}
    tiers={t['id']:t['provisional_relevance'] for t in read(root/'task-selection.json')['tasks']};rows=[]
    for result in summary['rows']:
        row=result_dimensions(result);job=jobs[result['row']['bridge_task_key']];ep=Path(result['episode'])
        deadline=hard.deadline_audit(ep);write_json(ep/'deadline_dual_audit.json',deadline)
        row.update(repeat=job['repeat'],relevance=tiers[row['task_id']],observed_dual_within_deadline=deadline['observed_dual_within_deadline'],
          first_confirmed_dual_seconds=deadline['first_confirmed_dual_seconds'],capped_first_dual_seconds=deadline['first_confirmed_dual_seconds'] if deadline['first_confirmed_dual_seconds'] is not None else 600,
          prompt_has_no_card_body=(ep/'prompt.txt').read_text()==(root/'TASK.md').read_text(),
          card_body_tokens=result['retrieval'].get('body_tokens',0),card_ids_read=result['retrieval'].get('read_ids',[]),
          no_helper_read=result['retrieval'].get('read_calls',0)==0,
          direct_bank_access_flag=bool(result['retrieval'].get('direct_bank_access_commands',[])))
        rows.append(row)
    with (root/'episodes.csv').open('w') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]) if rows else ['condition']);writer.writeheader();writer.writerows(rows)
    arms={a:{'completed':len([x for x in rows if x['condition']==a]),'planned':16,
        'budgeted_dual_pass':sum(x['budgeted_dual_pass'] for x in rows if x['condition']==a),
        'strict_V2_dual_pass':sum(x['budgeted_dual_pass'] and x['fidelity']=='V2_TRACE' for x in rows if x['condition']==a),
        'observed_dual_within_deadline':sum(x['observed_dual_within_deadline'] for x in rows if x['condition']==a)} for a in ARMS}
    write_json(root/'report.json',{'rows':rows,'arms':arms,'planned':112,'completed':len(rows),'unstarted':len(set(jobs)-{x['row']['bridge_task_key'] for x in summary['rows']}),
        'failures':summary['failures'],'inputs_unchanged':summary['reviewed_inputs_unchanged'],'budget_evaluation':read(Path(read(root/'budget-baseline.json')['evaluation_ledger'])),
        'budget_total':read(Path(read(root/'validation_contract.json')['shared_ledger_root'])/'budget-new-total.json'),
        'caveat':summary['caveat'],'mechanism_review':'pending; reads are not evidence of correct application'} )


def run(root):
    contract=check(root);ledger=Path(contract['shared_ledger_root'])
    with (ledger/'execution.lock').open('a') as shared,(root/'execution.lock').open('a') as local:
        for handle in [shared,local]:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (root/'started.json').exists() and not (root/'episodes').exists(),'No automatic paid restart')
        require(all(read(g.path)==read(root/'budget-baseline.json')['states'][str(g.path)] for g in guards(root,ledger)),'Historical budget changed since review')
        config=read(root/'config.json');prior.credentials(config)
        write_json(root/'started.json',{'time':datetime.now(timezone.utc).isoformat(),'contract_sha256':sha(root/'validation_contract.json'),'episodes':112})
        try:
            prior.driver.run(config,root,contract,expected_episodes=112,budget_guard=HistoricalUncertaintyMux(guards(root,ledger),read(root/'budget-baseline.json')['states']),retrieval_auditor=lambda p:audit_reads(p,root))
        except BaseException as error:
            write_json(root/'stopped.json',{'type':type(error).__name__,'reason':str(error),'automatic_retry':False});raise
        finally:
            if (root/'summary.json').exists():report(root)
        require(read(root/'summary.json')['completed_episodes']==112,'Incomplete matrix')
        write_json(root/'completed.json',{'status':'evaluation_complete','episodes':112,'trace_review_pending':True})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['prepare','check','run','report']);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--materials',type=Path);p.add_argument('--pseudocode',type=Path);p.add_argument('--previous',type=Path);p.add_argument('--selection',type=Path);p.add_argument('--executive',type=Path)
    a=p.parse_args();root=prior.builder.output_root(a.output)
    if a.phase=='prepare':prepare(root,a.materials.resolve(),a.pseudocode.resolve(),a.previous.resolve(),a.selection.resolve(),a.executive.resolve())
    else:{'check':check,'run':run,'report':report}[a.phase](root)
