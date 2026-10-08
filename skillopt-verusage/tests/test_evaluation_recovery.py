"""Synthetic fixed-160 transport recovery never retries a valid timeout/failure."""
import hashlib
import json
from pathlib import Path

import pytest

from skillopt_verusage import evaluation_recovery as recovery
from skillopt_verusage.codex_deepseek_bridge import _sha256_json
from skillopt_verusage.skill_artifact import load_skill_artifact


def put(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rebind(root):
    review_path = root/'audits/evaluation_transport_incident_review.json'
    review = json.loads(review_path.read_text())
    paths = [root/p for p in recovery.TOP_FILES]
    paths += [p for p in root.glob('validation/repeat_*/*/*/*') if p.name in recovery.EPISODE_FILES]
    paths += list((root/'provider_failure_evidence'/recovery.FAILED_REQUEST).glob('*'))
    review['preserved_hashes'] = {str(p.relative_to(root)):digest(p) for p in paths if p.is_file()}
    put(review_path,review)


@pytest.fixture
def parent(tmp_path):
    root = tmp_path/'parent';root.mkdir()
    frozen = {}
    for condition in recovery.CONDITIONS:
        location = root/'artifacts'/condition
        location.mkdir(parents=True)
        (location/'SKILL.md').write_text('Synthetic unchanged '+condition)
        path = location if condition in ('original_only','augmented') else location/'SKILL.md'
        frozen[condition] = {'path':str(path),**load_skill_artifact(path).manifest()}
    put(root/'frozen_artifacts.json',frozen)
    for condition in ('original_only','augmented'):
        put(root/'banks'/condition/'cards.json',{'schema_version':'stage-card-bank-v1','cards':[]})
    evidence = {'frozen_artifacts_sha256':digest(root/'frozen_artifacts.json'),
        'banks':{c:digest(root/f'banks/{c}/cards.json') for c in ('original_only','augmented')}}
    put(root/'artifact_quality_evidence.json',evidence)
    put(root/'artifact_review.json',{'accepted':True,'evidence_sha256':_sha256_json(evidence),'observations':'Synthetic accepted artifacts.'})
    ids = [recovery.FAILED_ID]+[f'question-{n:02d}' for n in range(1,20)]
    items = []
    for ident in ids:
        source = root/'val_inputs'/f'{ident}.rs';source.parent.mkdir(exist_ok=True)
        source.write_text('Synthetic original '+ident)
        items.append({'id':ident,'runtime_source':str(source),'source_sha256':digest(source)})
    blocks = [[[repeat,c,item] for item in items for c in recovery.CONDITIONS] for repeat in (0,1)]
    put(root/'evaluation_schedule.json',{'blocks':blocks,'test_accessed':False,
        'frozen_artifacts_sha256':digest(root/'frozen_artifacts.json'),'manifest_sha256':'synthetic-fixed-manifest'})
    records=[];aggregate=[]
    for n,item in enumerate(items[:16]):
        for condition in recovery.CONDITIONS:
            key = f"val_r1_{condition}--{item['id']}";directory=root/'validation/repeat_1'/condition/item['id'];workspace=directory/'workspace'
            workspace.mkdir(parents=True)
            (workspace/'input.rs').write_text(Path(item['runtime_source']).read_text())
            (workspace/'candidate.rs').write_text('Synthetic candidate '+key)
            (workspace/'SKILL.md').write_text((root/'artifacts'/condition/'SKILL.md').read_text())
            invalid=n==0;timeout=n==1;solved=n!=2 and not timeout
            terminal={'completed':0 if invalid or timeout else 1,'failed':int(invalid),'errors':0}
            (directory/'codex_events.raw.jsonl').write_text('' if timeout else json.dumps({'type':'turn.failed' if invalid else 'turn.completed'})+'\n')
            validation={'input_unchanged':True,'skill_unchanged':True,'candidate_sha256':digest(workspace/'candidate.rs'),
                'verus':{'passed':solved},'lynette':{'passed':True}}
            put(directory/'validation.json',validation)
            put(directory/'fidelity_audit.json',{'input_unchanged':True,'f3':True})
            put(directory/'run_manifest.json',{'model':'deepseek-v4-pro','reasoning_effort':'max','timeout_seconds':600,
                'source_sha256':item['source_sha256'],'condition_skill_sha256':frozen[condition]['artifact_sha256'],
                'bridge':{'task_key':key}})
            row={'id':item['id'],'bridge_task_key':key,'fidelity':'V0_INVALID' if invalid else ('V1_TRUNCATED' if timeout else 'V2_TRACE'),
                'provider_valid':True,'codex_returncode':1 if timeout or invalid else 0,'safety_passed':True,
                'within_budget':not timeout,'timed_out':timeout,'hard':int(solved),'proof_solved':solved,
                'actor_model':'deepseek-v4-pro','actor_reasoning_effort':'max','source_sha256':item['source_sha256'],
                'skill_sha256':frozen[condition]['artifact_sha256'],
                'skill_artifact':{k:v for k,v in frozen[condition].items() if k!='path'},'validation':validation,'codex_terminal':terminal}
            put(directory/'result.json',row)
            if not invalid:
                put(directory/'retrieval_audit.json',{'read_calls':0})
                if n<15:aggregate.append({**row,'condition':condition,'repetition':1})
            request_id=recovery.FAILED_REQUEST if invalid and condition=='initial' else f'request-{n}-{condition}'
            attempt={'finish_reason':'completed','usage':{'prompt_tokens':10,'completion_tokens':2},'estimated_cost_usd':.01,'error':None}
            if request_id==recovery.FAILED_REQUEST:attempt.update(finish_reason=None,usage=None,estimated_cost_usd=None,error='IncompleteRead: synthetic incomplete stream')
            records.append({'request_id':request_id,'task_id':key,'model':'deepseek-v4-pro','upstream_model':'deepseek-v4-pro','attempts':[attempt]})
    (root/'provider_calls.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    put(root/'validation_rows.json',aggregate)
    error=f'Actor/provider invalid, preserve and stop: val_r1_original_only--{recovery.FAILED_ID}'
    put(root/'progress.json',{'phase':'stopped','error_type':'RuntimeError','error':error,'evaluation_completed':56})
    for name in ['audits/retrieval_case_studies.json','cost_summary.json']:put(root/name,{'synthetic':True})
    (root/'campaign.log').write_text('Synthetic stopped transport incident')
    failed=root/'provider_failure_evidence'/recovery.FAILED_REQUEST
    request={'model':'deepseek-v4-pro','reasoning':{'effort':'max'},'max_output_tokens':131072}
    put(failed/'request.json',request);(failed/'response.partial.raw').write_bytes(b'data: partial incomplete response\n')
    put(failed/'error.json',{'partial_response_accepted':False,'partial_body_sha256':digest(failed/'response.partial.raw'),
        'partial_body_bytes':(failed/'response.partial.raw').stat().st_size,
        'request_sha256':hashlib.sha256(json.dumps(request,ensure_ascii=False).encode()).hexdigest()})
    saved=[]
    for result in sorted(root.glob('validation/repeat_*/*/*/result.json')):
        row=json.loads(result.read_text());saved.append({'path':str(result.parent.relative_to(root)),**{k:row[k] for k in (
            'id','fidelity','provider_valid','codex_returncode','safety_passed','within_budget','bridge_task_key')}})
    put(root/'audits/evaluation_transport_incident_review.json',{'schema_version':'evaluation-transport-incident-review-v1',
        'status':'stopped_partial_not_160_complete','process_pid':2147483647,'paid_process_running':False,
        'root_error':error,'reported_evaluation_rows':56,'saved_result_count':64,'valid_saved_actor_outcomes':60,
        'invalid_saved_results':4,'request_id':recovery.FAILED_REQUEST,'failed_task_id':f'val_r1_initial--{recovery.FAILED_ID}',
        'partial_response_accepted':False,'partial_terminal_or_usage_present':False,'no_sealed_test_access':True,
        'current_unresolved_requests':1,'current_unresolved_upper_usd':1.90316544,'saved_results':saved})
    rebind(root)
    return root


def test_retain60_including_timeouts_failures_and_unaggregated_four_without_writes(parent):
    before={p:p.read_bytes() for p in parent.rglob('*') if p.is_file()}
    report=recovery.audit_parent(parent)
    assert len(report['rows'])==60 and len(report['invalid_keys'])==4
    assert len(report['preserved_hashes'])==393 and len(report['result_directories'])==60
    assert sum(r['fidelity']=='V1_TRUNCATED' for r in report['rows'])==4
    assert all(not r['within_budget'] for r in report['rows'] if r['timed_out'])
    assert sum(r['id']=='question-15' for r in report['rows'])==4
    assert any(not r['hard'] and not r['timed_out'] for r in report['rows'])
    assert report['unknown_expense']['unknown_expense_upper_usd']==pytest.approx(1.90316544)
    assert all(p.read_bytes()==content for p,content in before.items())
    for key,path in report['result_directories'].items():
        assert key not in report['invalid_keys']
        for file in (parent/path).rglob('*'):
            if file.is_file():assert str(file.relative_to(parent)) in (report['preserved_hashes']|report['runtime_hashes'])


@pytest.mark.parametrize('kind',['inventory','running','accepted_gate','gate_hash','frozen_skill','source','actor_skill',
    'actor_model','reasoning','timeout_contract','timeout_reclassified','safe_failure','terminal','unknown_scope',
    'partial','upper_zero','duplicate_ledger','orphan_ledger','changed_schedule','duplicate_slot','sealed_flag',
    'unlisted_result','aggregate_row','aggregate_duplicate','retry_valid','wrong_invalid','symlink','traversal'])
def test_rebound_receipt_cannot_change_outputs_or_broaden_whole_episode_retry(parent,kind):
    d=parent/'validation/repeat_1/initial/question-01'
    target=None;field=None;value=None
    if kind=='inventory':(d/'codex_events.raw.jsonl').write_text('changed');return check(parent)
    if kind=='running':target=parent/'audits/evaluation_transport_incident_review.json';field='process_pid';value=__import__('os').getpid()
    elif kind=='accepted_gate':target=parent/'artifact_review.json';field='accepted';value=False
    elif kind=='gate_hash':target=parent/'artifact_review.json';field='evidence_sha256';value='changed'
    elif kind=='frozen_skill':(parent/'artifacts/native/SKILL.md').write_text('changed')
    elif kind=='source':(parent/'val_inputs/question-01.rs').write_text('changed')
    elif kind=='actor_skill':(d/'workspace/SKILL.md').write_text('changed')
    elif kind in ['actor_model','reasoning','timeout_contract']:
        target=d/'run_manifest.json';field,value={'actor_model':('model','other'),'reasoning':('reasoning_effort','high'),'timeout_contract':('timeout_seconds',1800)}[kind]
    elif kind in ['timeout_reclassified','safe_failure','retry_valid','wrong_invalid']:
        target=d/'result.json';field,value={'timeout_reclassified':('within_budget',True),'safe_failure':('safety_passed',False),
            'retry_valid':('fidelity','V0_INVALID'),'wrong_invalid':('bridge_task_key','val_r2_initial--question-01')}[kind]
    elif kind=='terminal':(d/'codex_events.raw.jsonl').write_text(json.dumps({'type':'turn.completed'})+'\n')
    elif kind in ['unknown_scope','duplicate_ledger','orphan_ledger']:
        p=parent/'provider_calls.jsonl';rows=[json.loads(s) for s in p.read_text().splitlines()]
        if kind=='unknown_scope':rows[5]['attempts'][0]['estimated_cost_usd']=None
        elif kind=='duplicate_ledger':rows.append(rows[5])
        else:rows[5]['task_id']='val_r1_initial--orphan'
        p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    elif kind=='partial':(parent/'provider_failure_evidence'/recovery.FAILED_REQUEST/'response.partial.raw').write_bytes(b'changed')
    elif kind=='upper_zero':target=parent/'audits/evaluation_transport_incident_review.json';field='current_unresolved_upper_usd';value=0
    elif kind in ['changed_schedule','duplicate_slot','sealed_flag']:
        target=parent/'evaluation_schedule.json';j=json.loads(target.read_text())
        if kind=='changed_schedule':j['blocks'][1].pop()
        elif kind=='duplicate_slot':j['blocks'][1][1]=j['blocks'][1][0]
        else:j['test_accessed']=True
        put(target,j);target=None
    elif kind=='unlisted_result':put(parent/'validation/repeat_2/initial/question-01/result.json',{})
    elif kind in ['aggregate_row','aggregate_duplicate']:
        target=parent/'validation_rows.json';j=json.loads(target.read_text())
        if kind=='aggregate_row':j[0]['hard']=1-j[0]['hard']
        else:j[1]=j[0]
        put(target,j);target=None
    elif kind=='symlink':(d/'workspace/extra.rs').symlink_to(parent/'val_inputs/question-01.rs')
    elif kind=='traversal':
        target=parent/'audits/evaluation_transport_incident_review.json';j=json.loads(target.read_text());j['preserved_hashes']['../outside']='fake';put(target,j);return check(parent)
    if target:
        j=json.loads(target.read_text());j[field]=value;put(target,j)
    rebind(parent)
    check(parent)


def check(parent):
    with pytest.raises((ValueError,KeyError,OSError)):
        recovery.audit_parent(parent)
