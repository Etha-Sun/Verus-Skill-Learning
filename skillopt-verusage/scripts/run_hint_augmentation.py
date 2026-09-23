"""One-shot hindsight hint generation and isolated checkpoint continuation.

All run artifacts are external; no automatic hint regeneration or actor retries.
"""
from pathlib import Path
import argparse, datetime, difflib, hashlib, importlib.util, json, os, re, shlex, shutil
import subprocess, sys, time, urllib.request, urllib.error

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO/'src'), str(REPO/'skillopt-verusage/src'), str(REPO/'skill-evolution-pilot/src')]
EXTRACTOR_SHA = '642f76ab5774df0685f1268cccf49802cee9ef1f9649c012ea38dae45331ab0e'
TRAIN_SHA = '0e42aad8c5e8a6789d06e7b15cfdca903479b16dc76f863544f219e6bbe40536'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()

def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp'); tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n'); tmp.replace(p)

def credentials(c):
    result={}
    for line in Path(c['credential_file']).read_text().splitlines():
        line=line.strip().removeprefix('export ')
        if line and not line.startswith('#') and '=' in line:
            k,v=line.split('=',1)
            if k.strip() in ['DEEPSEEK_API_KEY','DEEPSEEK_BASE_URL']:
                words=shlex.split(v,comments=True); result[k.strip()]=words[0] if words else ''
    assert result.get('DEEPSEEK_API_KEY'), 'Missing API credential'
    return result

def render(template, fields):
    slots=set(re.findall(r'\{\{(\w+)\}\}',template))
    assert slots==set(fields), (slots,set(fields))
    return re.sub(r'\{\{(\w+)\}\}',lambda m:fields[m[1]],template)

def paths(c, cp):
    root=Path(c['output_root']); ident=c['task_id']
    return root/'hint-private'/ident/f'CP{cp:02d}', root/'runs'/ident/f'CP{cp:02d}'

def no_hint_paths(c, cp):
    root=Path(c['output_root']); ident=c['task_id']
    return root/'checkpoints'/ident/f'CP{cp:02d}.rs', root/'runs'/ident/f'CP{cp:02d}'

def snapshot_evidence(baseline, snapshots, compact=False):
    """Lossless, baseline-relative line edits; keep every snapshot and verify reconstruction."""
    if not compact:
        return snapshots
    base = baseline.splitlines(keepends=True)
    encoded = {}
    for digest, source in snapshots.items():
        lines = source.splitlines(keepends=True)
        edits = [{'start_line_0based':i, 'end_line_exclusive':j, 'replacement_lines':lines[a:b]}
                 for tag,i,j,a,b in difflib.SequenceMatcher(None,base,lines,autojunk=False).get_opcodes()
                 if tag != 'equal']
        restored = list(base)
        for edit in reversed(edits):
            restored[edit['start_line_0based']:edit['end_line_exclusive']] = edit['replacement_lines']
        assert ''.join(restored) == source
        assert hashlib.sha256(source.encode()).hexdigest() == digest
        encoded[digest] = edits
    return {'encoding':'lossless_baseline_relative_line_edits_v1',
            'baseline':'original_task_json.input_rs (complete source supplied above)',
            'instructions':'For each snapshot, start from the original input.rs. Apply edits in reverse listed order. Line indices are zero-based; the end is exclusive. All unlisted lines are identical to input.rs. Each snapshot is independently reconstructible; this is not a sequential patch chain.',
            'snapshots':encoded}

def prepare(c):
    root=Path(c['output_root']); root.mkdir(parents=True,exist_ok=True)
    assert not root.resolve().is_relative_to(REPO)
    train=REPO/'fixed-claude-stratified-80-seed20260814/train/items.json'; assert sha(train)==TRAIN_SHA
    items=json.loads(train.read_text()); assert len(items)==40
    item=next(x for x in items if x['id']==c['task_id'])
    origin=Path(c['original_run']); assert origin.name==item['id'] and 'step_0001' in origin.parts
    m=json.loads((origin/'run_manifest.json').read_text()); assert m['model']=='deepseek-v4-pro'
    result=json.loads((origin/'result.json').read_text()); assert all(result['validation'][k]['passed'] for k in ['verus','lynette'])
    ext=REPO/'scripts/audit_trajectory_progress.py'; assert sha(ext)==EXTRACTOR_SHA
    spec=importlib.util.spec_from_file_location('frozen_extract',ext); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    run=mod._load_run(origin); assert run
    finalsha=sha(origin/'workspace/candidate.rs')
    chosen=[x for x in run['checkpoints'] if x['candidate_sha256']!=finalsha]
    prior=json.loads(Path(c['original_selection_manifest']).read_text())
    assert [(x['event_index'],x['candidate_sha256']) for x in chosen]==[(x['event_index'],x['candidate_sha256']) for x in prior['checkpoints'] if x['continue']]
    events=[json.loads(l) for l in (origin/'agent_events.jsonl').read_text().splitlines()]
    eventmap={e['event_index']:e for e in events}
    raw=[json.loads(l) for l in (origin/'codex_events.raw.jsonl').read_text().splitlines()]
    canonical=lambda x:json.dumps(x,sort_keys=True)
    represented={canonical(e['data']['raw_codex_event']) for e in events if 'raw_codex_event' in e.get('data',{})}
    supplemental=[{'source_id':f'raw:{i+1}','record':e} for i,e in enumerate(raw) if canonical(e) not in represented]
    snapshots={sha(p):p.read_text() for p in sorted((origin/'snapshots').glob('*candidate.rs'))}
    index=[{'source_id':f"event:{e['event_index']}"} for e in events]+[{'source_id':f'snapshot:{h}'} for h in snapshots]+[{'source_id':'final_validation'},{'source_id':'final_proof'},{'source_id':'original_task'}]+[{'source_id':x['source_id']} for x in supplemental]
    prompts=Path(c.get('prompt_dir',REPO/'skillopt-verusage/prompts/checkpoint_hints'))
    prompt_names=('actor_hint.md','hint_output.schema.json','hint_system.md','hint_user.md')
    prompt_hashes={name:sha(prompts/name) for name in prompt_names}
    prompt_manifest=root/'prompt_manifest.json'
    if prompt_manifest.exists(): assert json.loads(prompt_manifest.read_text())['prompts']==prompt_hashes, 'Frozen prompts changed'
    else: write(prompt_manifest,{'schema_version':'checkpoint-hint-prompt-manifest-v1','prompts':prompt_hashes})
    selection=[]
    for n,x in enumerate(chosen,1):
        private,_=paths(c,n);private.mkdir(parents=True,exist_ok=True)
        checkpoint=private/'checkpoint.rs'
        if checkpoint.exists(): assert sha(checkpoint)==x['candidate_sha256']
        else: checkpoint.write_text(x['source'])
        assert sha(checkpoint)==x['candidate_sha256']
        data={'task_and_checkpoint_json':{'task_id':item['id'],'task_name':item['task_id'],'checkpoint_ordinal':n,'event_index':x['event_index'],'checkpoint_sha256':x['candidate_sha256']},
          'original_task_json':{'input_rs':(origin/'workspace/input.rs').read_text(),'original_prompt':(origin/'prompt.txt').read_text(),'original_user_prompt':(origin/'target_user_prompt.txt').read_text()},
          'checkpoint_json':{'source':x['source'],'diagnostic':x['verifier_output'],'event':eventmap.get(x['event_index']),'note':'This is a Verus observation, not an assertion that Lynette passed.'},
          'original_trajectory_json':{'events':events,'supplemental_raw_records':supplemental},
          'source_snapshots_json':snapshot_evidence((origin/'workspace/input.rs').read_text(),snapshots,c.get('compact_snapshot_evidence',False)),
          'original_final_json':{'source':(origin/'workspace/candidate.rs').read_text(),'sha256':finalsha,'validation':result['validation']},'evidence_index_json':index}
        fields={k:json.dumps(v,ensure_ascii=False) for k,v in data.items()}
        user=render((prompts/'hint_user.md').read_text(),fields); system=(prompts/'hint_system.md').read_text()
        # Conservative input-size admission; exact provider usage is recorded after the call.
        input_bytes=len((system+user).encode())
        assert input_bytes+c['hint_max_output_tokens']<c['input_byte_budget'], 'Complete input exceeds conservative admission budget; no truncation'
        payload={'model':c['model'],'instructions':system,'input':[{'role':'user','content':[{'type':'input_text','text':user}]}],'reasoning':{'effort':'high'},'max_output_tokens':c['hint_max_output_tokens'],'stream':False}
        request=private/'request.json'
        if request.exists(): assert json.loads(request.read_text())==payload, 'Frozen request changed'
        else: write(request,payload)
        write(private/'input_contract.json',{'source_run':str(origin),'original_final_sha256':finalsha,'checkpoint_sha256':x['candidate_sha256'],'original_event_index':x['event_index'],'request_sha256':sha(request),'canonical_event_count':len(events),'supplemental_raw_count':len(supplemental),'snapshot_count':len(snapshots),'complete_recorded_trajectory':True,'input_utf8_bytes':input_bytes,'context_check':'conservative byte admission; exact provider input tokens checked after generation','evidence_ids':[e['source_id'] for e in index]})
        selection.append({'ordinal':n,'event_index':x['event_index'],'checkpoint_sha256':x['candidate_sha256'],'checkpoint_path':str(checkpoint),'request_sha256':sha(request),'input_utf8_bytes':input_bytes})
    write(root/'selection.json',{'task':item,'checkpoints':selection,'extractor_sha256':EXTRACTOR_SHA,'train_sha256':TRAIN_SHA,'original_final_sha256':finalsha})
    print('Prepared',len(selection),'unchanged original checkpoints; no truncation; input bytes', [x['input_utf8_bytes'] for x in selection],flush=True)

def prepare_no_hint(c):
    """Freeze the exact hint-arm checkpoints for a fresh matched no-hint arm."""
    root=Path(c['output_root']); root.mkdir(parents=True,exist_ok=True)
    assert not root.resolve().is_relative_to(REPO)
    has_run_source=bool(c.get('checkpoint_source_root'))
    has_publication_source=bool(c.get('checkpoint_publication_root'))
    assert has_run_source != has_publication_source, 'Set exactly one checkpoint source'
    source_root=Path(c.get('checkpoint_source_root') or c['checkpoint_publication_root']).resolve()
    assert source_root != root.resolve()
    train=REPO/'fixed-claude-stratified-80-seed20260814/train/items.json'; assert sha(train)==TRAIN_SHA
    train_items=json.loads(train.read_text())
    if has_run_source:
        source_selection_path=source_root/'selection.json'
        assert source_selection_path.is_file(), 'Missing source selection.json'
        source_selection=json.loads(source_selection_path.read_text())
        item=source_selection['task']; assert item['id']==c['task_id']
        source_rows=source_selection['checkpoints']
        source_kind='completed_hint_arm_run'
    else:
        source_selection_path=source_root/'selection_manifest.json'
        assert source_selection_path.is_file(), 'Missing publication selection_manifest.json'
        source_selection=json.loads(source_selection_path.read_text())
        item=next(x for x in train_items if x['id']==c['task_id'])
        selected=[x for x in source_selection['checkpoints'] if x.get('continue') is True]
        source_rows=[{
            'ordinal':n,
            'event_index':row['event_index'],
            'checkpoint_sha256':row['candidate_sha256'],
        } for n,row in enumerate(selected,1)]
        assert c['model']=='deepseek-v4-pro'
        assert int(c.get('actor_timeout_seconds',600))==600
        assert c.get('actor_skill_sha256')=='96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40'
        source_kind='reviewed_publication_checkpoint_source'
    assert any(x==item for x in train_items)
    frozen=[]
    for row in source_rows:
        cp=int(row['ordinal'])
        source=(source_root/'hint-private'/item['id']/f'CP{cp:02d}'/'checkpoint.rs'
                if has_run_source else source_root/'checkpoints'/f'CP{cp:02d}.rs')
        assert source.is_file(), f'Missing source checkpoint CP{cp:02d}'
        assert sha(source)==row['checkpoint_sha256']
        matched_manifest_sha=None
        if has_run_source:
            source_manifest_path=source_root/'runs'/item['id']/f'CP{cp:02d}'/'run_manifest.json'
            assert source_manifest_path.is_file(), f'Missing completed hint-arm manifest CP{cp:02d}'
            source_manifest=json.loads(source_manifest_path.read_text())
            assert source_manifest['model']==c['model'], f'Actor model mismatch CP{cp:02d}'
            assert source_manifest['reasoning_effort']=='high', f'Reasoning effort mismatch CP{cp:02d}'
            assert int(source_manifest['timeout_seconds'])==int(c.get('actor_timeout_seconds',600)), f'Actor budget mismatch CP{cp:02d}'
            assert source_manifest['skill_sha256']==c.get('actor_skill_sha256'), f'Actor skill mismatch CP{cp:02d}'
            matched_manifest_sha=sha(source_manifest_path)
        checkpoint,_=no_hint_paths(c,cp); checkpoint.parent.mkdir(parents=True,exist_ok=True)
        if checkpoint.exists(): assert sha(checkpoint)==row['checkpoint_sha256']
        else: shutil.copyfile(source,checkpoint)
        frozen_row={
            'ordinal':cp,
            'event_index':row['event_index'],
            'checkpoint_sha256':row['checkpoint_sha256'],
            'checkpoint_path':str(checkpoint),
        }
        if matched_manifest_sha:
            frozen_row['matched_hint_run_manifest_sha256']=matched_manifest_sha
        frozen.append(frozen_row)
    selection={
        'schema_version':'checkpoint-no-hint-selection-v1',
        'condition':'matched_no_hint',
        'task':item,
        'checkpoints':frozen,
        'checkpoint_source_kind':source_kind,
        'source_selection_sha256':sha(source_selection_path),
        'source_train_sha256':source_selection.get('train_sha256') if has_run_source else None,
        'train_sha256':TRAIN_SHA,
        'matching_contract':{
            'fresh_actor_session':True,
            'teacher_hint_visible_to_actor':False,
            'historical_prefix_visible_to_actor':False,
            'checkpoint_model_skill_budget_must_match_hint_arms':True,
        },
    }
    existing=root/'selection.json'
    if existing.exists(): assert json.loads(existing.read_text())==selection, 'Frozen no-hint selection changed'
    else: write(existing,selection)
    print('Prepared',len(frozen),'matched no-hint checkpoints',flush=True)

def screen_hint(obj, contract, schema):
    import jsonschema
    jsonschema.validate(obj,schema)
    assert obj['checkpoint_sha256']==contract['checkpoint_sha256'], 'Hint checkpoint mismatch'
    assert all(e['source_id'] in contract['evidence_ids'] for e in obj['evidence_refs']), 'Unknown evidence ID'
    text=obj['hint_text']; assert text.strip()
    flags=[]
    patterns={'code_fence':r'```','verus_statement':r'\b(?:assert|assume|admit)\s*\(|\b(?:proof\s+fn|verus!)|\blet\s+\w+\s*=','literal_call':r'\b\w+(?:::\w+|\.\w+)*\([^\n]*\)\s*;','private_path':r'/zp_vegeta/|/home/|hint-private|reference_final\.rs','exact_edit_recipe':r'(?i)replace\s+line|insert\s+the\s+following|change\s+line\s+\d','whole_answer_lemma':r'\blemma_map_union_commute\b'}
    for name,pat in patterns.items():
        if re.search(pat,text):flags.append(name)
    return {'schema_and_evidence_valid':True,'logic_hint_screen_flags':flags,'automatic_screen_passed':not flags,'semantic_correctness':'not established by automatic checks','words':len(text.split())}

def hint_screen_approved(private):
    review=json.loads((private/'screen.json').read_text())
    if review['automatic_screen_passed']:return True
    approval=private/'manual_screen_review.json'
    if not approval.exists():return False
    decision=json.loads(approval.read_text())
    return (review.get('schema_and_evidence_valid') is True
            and review.get('logic_hint_screen_flags')==['literal_call']
            and decision.get('verdict')=='false_positive_literal_call'
            and decision.get('hint_sha256')==sha(private/'hint.json')
            and decision.get('screen_sha256')==sha(private/'screen.json'))

def seed_published_hints(c, cps):
    """Freeze reviewed repository hints without making a hint-provider call."""
    root=Path(c['output_root']); selection=json.loads((root/'selection.json').read_text())
    publication=Path(c['published_project_root']).resolve()
    repo=REPO.resolve()
    assert publication != repo and repo in publication.parents, 'Published hints must come from this repository'
    version=c['hint_version']; assert version in {'v1','v2'}
    published_selection=json.loads((publication/'selection_manifest.json').read_text())
    published_rows=[x for x in published_selection['checkpoints'] if x.get('continue') is True]
    expected=[(int(x['ordinal']),int(x['event_index']),x['checkpoint_sha256']) for x in selection['checkpoints']]
    observed=[(n,int(x['event_index']),x['candidate_sha256']) for n,x in enumerate(published_rows,1)]
    assert observed==expected, 'Published checkpoint selection differs from prepared original trajectory'
    schema=json.loads((Path(c['prompt_dir'])/'hint_output.schema.json').read_text())
    for cp in cps:
        row=next(x for x in selection['checkpoints'] if int(x['ordinal'])==cp)
        private,_=paths(c,cp)
        for name in ('call_started.json','response.raw','usage.json','output_text.txt'):
            assert not (private/name).exists(), f'Hint-provider artifact exists during replay: {private/name}'
        source_dir=publication/version/f'CP{cp:02d}'
        source_hint=source_dir/'hint.json'; assert source_hint.is_file()
        hint=json.loads(source_hint.read_text())
        contract=json.loads((private/'input_contract.json').read_text())
        assert row['checkpoint_sha256']==contract['checkpoint_sha256']==hint['checkpoint_sha256']
        assert sha(private/'checkpoint.rs')==row['checkpoint_sha256']
        review=screen_hint(hint,contract,schema)
        hint_path=private/'hint.json'; screen_path=private/'screen.json'
        if hint_path.exists(): assert json.loads(hint_path.read_text())==hint, 'Frozen published hint changed'
        else: shutil.copyfile(source_hint,hint_path)
        if screen_path.exists(): assert json.loads(screen_path.read_text())==review, 'Published hint screen changed'
        else: write(screen_path,review)
        if not review['automatic_screen_passed']:
            source_review=source_dir/'manual_screen_review.json'; assert source_review.is_file(), 'Published hint requires reviewed manual approval'
            decision=json.loads(source_review.read_text())
            assert decision.get('hint_sha256')==sha(hint_path)
            assert decision.get('screen_sha256')==sha(screen_path)
            audit_source=(source_dir/decision['review_source']).resolve()
            assert publication in audit_source.parents and audit_source.is_file()
            assert decision.get('review_source_sha256')==sha(audit_source)
            review_path=private/'manual_screen_review.json'
            if review_path.exists(): assert json.loads(review_path.read_text())==decision, 'Manual review changed'
            else: shutil.copyfile(source_review,review_path)
        assert hint_screen_approved(private), 'Published hint is not approved'
        provenance={
            'schema_version':'published-hint-replay-v1',
            'condition':f'published_hint_{version}',
            'hint_version':version,
            'hint_generation_api_called':False,
            'published_hint_path':str(source_hint.relative_to(repo)),
            'published_hint_sha256':sha(source_hint),
            'checkpoint_sha256':row['checkpoint_sha256'],
            'original_event_index':row['event_index'],
            'publication_selection_sha256':sha(publication/'selection_manifest.json'),
        }
        provenance_path=private/'published_hint_replay.json'
        if provenance_path.exists(): assert json.loads(provenance_path.read_text())==provenance, 'Replay provenance changed'
        else: write(provenance_path,provenance)
        print('Seeded published',version,'hint CP',cp,'without a hint-provider call',flush=True)

def generate_hint(c, cp):
    private,_=paths(c,cp); request=private/'request.json'; assert request.exists()
    if (private/'hint.json').exists():
        assert hint_screen_approved(private), 'Hint requires screen review';return
    assert not (private/'call_started.json').exists(), 'Previous attempt exists; inspect instead of automatic regeneration'
    payload=json.loads(request.read_text()); secrets=credentials(c)
    assert secrets['DEEPSEEK_API_KEY'] not in request.read_text(), 'Credential value found in input'
    write(private/'call_started.json',{'time':now(),'request_sha256':sha(request)})
    start=time.monotonic()
    req=urllib.request.Request(secrets.get('DEEPSEEK_BASE_URL','https://api.deepseek.com').rstrip('/')+'/responses',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+secrets['DEEPSEEK_API_KEY'],'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=c['hint_timeout_seconds']) as response:body=response.read()
    except urllib.error.HTTPError as e:
        (private/'error_body.txt').write_bytes(e.read());write(private/'error.json',{'time':now(),'http_status':e.code,'elapsed_seconds':time.monotonic()-start});raise RuntimeError(f'Hint HTTP {e.code}; inspect private error artifact') from None
    (private/'response.raw').write_bytes(body)
    from skillopt_verusage.codex_deepseek_bridge import _native_response_usage
    usage,model,status=_native_response_usage(body)
    write(private/'usage.json',{'usage':usage,'model':model,'status':status,'finished_at':now(),'elapsed_seconds':time.monotonic()-start})
    assert status=='completed' and model==c['model'] and usage, 'Incomplete hint response/model/usage'
    assert usage['prompt_tokens']+c['hint_max_output_tokens']<c['context_window']
    if body.lstrip().startswith(b'{'):
        response=json.loads(body); response=response.get('response',response)
    else:
        candidates=[json.loads(line[5:].strip()) for line in body.decode().splitlines() if line.startswith('data:') and line[5:].strip() not in ['', '[DONE]']]
        response=next(e['response'] for e in reversed(candidates) if e.get('type')=='response.completed')
    text=''.join(part['text'] for out in response.get('output',[]) if out.get('type')=='message' for part in out.get('content',[]) if part.get('type')=='output_text')
    (private/'output_text.txt').write_text(text)
    obj=json.loads(text);contract=json.loads((private/'input_contract.json').read_text())
    review=screen_hint(obj,contract,json.loads((Path(c.get('prompt_dir',REPO/'skillopt-verusage/prompts/checkpoint_hints'))/'hint_output.schema.json').read_text()))
    write(private/'hint.json',obj);write(private/'screen.json',review)
    assert review['automatic_screen_passed'], 'Code-like hint flagged; stop for inspection'
    print('Hint CP',cp,'generated;',review['words'],'words; output tokens',usage['completion_tokens'],flush=True)

def actor(c, cp):
    private,out=paths(c,cp);root=Path(c['output_root'])
    if (out/'result.json').exists():return json.loads((out/'result.json').read_text())
    assert not out.exists(), 'Partial actor run exists; inspect first'
    obj=json.loads((private/'hint.json').read_text());assert hint_screen_approved(private)
    contract=json.loads((private/'input_contract.json').read_text());assert sha(private/'request.json')==contract['request_sha256']
    assert sha(private/'checkpoint.rs')==obj['checkpoint_sha256']
    from skillopt_verusage.codex_flash_runner import run_task
    item=json.loads((root/'selection.json').read_text())['task']
    instructions=Path(c['actor_protocol']).read_text()+'\n'+render((Path(c.get('prompt_dir',REPO/'skillopt-verusage/prompts/checkpoint_hints'))/'actor_hint.md').read_text(),{'hint_text':obj['hint_text']})
    replay_path=private/'published_hint_replay.json'
    replay=json.loads(replay_path.read_text()) if replay_path.exists() else None
    condition=replay['condition'] if replay else 'generated_hint'
    audit={'condition':condition,'hint_hindsight_guided':True,'direct_reference_proof':False,'checkpoint_sha256':obj['checkpoint_sha256'],'hint_sha256':hashlib.sha256(obj['hint_text'].encode()).hexdigest(),'request_sha256':contract['request_sha256'],'original_final_sha256':contract['original_final_sha256'],'model':c['model'],'prompt_manifest':json.loads((root/'prompt_manifest.json').read_text()),'actor_instructions_sha256':hashlib.sha256(instructions.encode()).hexdigest(),'hint_generation_api_called_in_current_run':not bool(replay)}
    if replay:
        assert replay['hint_generation_api_called'] is False
        audit['published_hint_replay']=replay
    write(private/'actor_handoff.json',audit)
    skill=Path(c.get('actor_skill_file',REPO/'skillopt-verusage/skills/blank.md'))
    skill_present=bool(c.get('actor_skill_present',False))
    if skill_present:
        assert sha(skill)==c['actor_skill_sha256']
        original_manifest=json.loads((Path(c['original_run'])/'run_manifest.json').read_text())
        assert original_manifest['skill_present'] and original_manifest['skill_sha256']==sha(skill)
    forbidden=[root/'hint-private',Path(c['original_run']),Path(c['credential_file']),Path(c['old_reference_dir'])]
    if replay:
        forbidden.append(Path(c['published_project_root']))
    hint_version=replay['hint_version'] if replay else c.get('hint_version','v1')
    result=run_task(item_id=item['id'],source=REPO/item['source_path'],expected_source_sha256=item['source_sha256'],directory_group=item['directory_group'],out_dir=out,skill_file=skill,expected_skill_sha256=c.get('actor_skill_sha256'),codex_bin=Path(c['codex_bin']),verus_bin=Path(c['verus_bin']),lynette_bin=Path(c['lynette_bin']),bridge_url=f"http://127.0.0.1:{c['bridge_port']}",bridge_ledger_path=root/'actor_bridge_calls.jsonl',bridge_manifest_path=root/'actor_bridge_manifest.json',bridge_task_key=f"hint-{hint_version}-cp{cp}-{item['id']}",model=c['model'],reasoning_effort='high',timeout_seconds=600,model_context_window=c['context_window'],actor_contract_profile='project',condition_skill_present=skill_present,initial_candidate_source=private/'checkpoint.rs',reference_proof_source=None,continuation_instructions=instructions,reference_kind='none',run_stage='checkpoint_published_hint_continuation' if replay else 'checkpoint_generated_hint_continuation',actor_isolation_scratch_root=Path(c['scratch_root']),actor_isolation_verus_root=Path(c['verus_root']),actor_isolation_rust_root=Path(c['rust_root']),actor_isolation_forbidden_paths=tuple(forbidden))
    if skill_present:
        assert sha(out/'workspace/SKILL.md')==sha(skill)
        manifest=json.loads((out/'run_manifest.json').read_text())
        assert manifest['skill_present'] and manifest['skill_sha256']==sha(skill)
    audit['actor_skill_present']=skill_present
    audit['actor_skill_sha256']=sha(skill)
    write(out/'hint_contract.json',audit); (out/'hint.txt').write_text(obj['hint_text'])
    assert not (out/'workspace/reference_final.rs').exists()
    assert obj['hint_text'] in (out/'prompt.txt').read_text()
    print('Actor CP',cp,'finished',result.get('status'),flush=True)
    return result

def actor_no_hint(c, cp):
    checkpoint,out=no_hint_paths(c,cp);root=Path(c['output_root'])
    if (out/'result.json').exists():return json.loads((out/'result.json').read_text())
    assert not out.exists(), 'Partial actor run exists; inspect first'
    selection=json.loads((root/'selection.json').read_text())
    assert selection['condition']=='matched_no_hint'
    row=next(x for x in selection['checkpoints'] if int(x['ordinal'])==cp)
    assert sha(checkpoint)==row['checkpoint_sha256']
    item=selection['task']; instructions=Path(c['actor_protocol']).read_text()
    skill=Path(c.get('actor_skill_file',REPO/'skillopt-verusage/skills/blank.md'))
    skill_present=bool(c.get('actor_skill_present',False))
    if skill_present: assert sha(skill)==c['actor_skill_sha256']
    audit={
        'schema_version':'checkpoint-continuation-condition-v1',
        'condition':'matched_no_hint',
        'teacher_hint_visible_to_actor':False,
        'historical_prefix_visible_to_actor':False,
        'direct_reference_proof':False,
        'checkpoint_sha256':row['checkpoint_sha256'],
        'original_event_index':row['event_index'],
        'model':c['model'],
        'reasoning_effort':'high',
        'timeout_seconds':int(c.get('actor_timeout_seconds',600)),
        'actor_instructions_sha256':hashlib.sha256(instructions.encode()).hexdigest(),
        'source_selection_sha256':selection['source_selection_sha256'],
    }
    result=run_task_no_hint(c,item,checkpoint,out,skill,skill_present,instructions,cp,root)
    audit['actor_skill_present']=skill_present; audit['actor_skill_sha256']=sha(skill)
    write(out/'condition_contract.json',audit)
    assert not (out/'workspace/reference_final.rs').exists()
    assert not (out/'hint.txt').exists()
    print('No-hint actor CP',cp,'finished',result.get('status'),flush=True)
    return result

def run_task_no_hint(c,item,checkpoint,out,skill,skill_present,instructions,cp,root):
    from skillopt_verusage.codex_flash_runner import run_task
    source_root=c.get('checkpoint_source_root') or c['checkpoint_publication_root']
    forbidden=[Path(source_root),Path(c['credential_file']),Path(c['old_reference_dir'])]
    if c.get('original_run'): forbidden.append(Path(c['original_run']))
    result=run_task(item_id=item['id'],source=REPO/item['source_path'],expected_source_sha256=item['source_sha256'],directory_group=item['directory_group'],out_dir=out,skill_file=skill,expected_skill_sha256=c.get('actor_skill_sha256'),codex_bin=Path(c['codex_bin']),verus_bin=Path(c['verus_bin']),lynette_bin=Path(c['lynette_bin']),bridge_url=f"http://127.0.0.1:{c['bridge_port']}",bridge_ledger_path=root/'actor_bridge_calls.jsonl',bridge_manifest_path=root/'actor_bridge_manifest.json',bridge_task_key=f"no-hint-cp{cp}-{item['id']}",model=c['model'],reasoning_effort='high',timeout_seconds=int(c.get('actor_timeout_seconds',600)),model_context_window=c['context_window'],actor_contract_profile='project',condition_skill_present=skill_present,initial_candidate_source=checkpoint,reference_proof_source=None,continuation_instructions=instructions,reference_kind='none',run_stage='checkpoint_no_hint_continuation',actor_isolation_scratch_root=Path(c['scratch_root']),actor_isolation_verus_root=Path(c['verus_root']),actor_isolation_rust_root=Path(c['rust_root']),actor_isolation_forbidden_paths=tuple(forbidden))
    if skill_present:
        assert sha(out/'workspace/SKILL.md')==sha(skill)
        manifest=json.loads((out/'run_manifest.json').read_text())
        assert manifest['skill_present'] and manifest['skill_sha256']==sha(skill)
    return result

def bridge_budget_args(c):
    state=c.get('budget_state_path')
    if not state:
        assert 'approval_limit_usd' not in c and 'prior_spend_usd' not in c and 'request_reserve_usd' not in c
        return []
    limit=float(c['approval_limit_usd']); assert limit>0
    prior=float(c.get('prior_spend_usd',0)); reserve=float(c.get('request_reserve_usd',0.25))
    assert prior>=0 and reserve>0 and prior<limit
    return ['--budget-state-path',str(Path(state)),'--approval-limit-usd',str(limit),'--prior-spend-usd',str(prior),'--request-reserve-usd',str(reserve)]

def with_bridge(c, cps, *, published_replay=False):
    root=Path(c['output_root']);secrets=credentials(c)
    catalog=root/'models.json'
    if catalog.exists():assert sha(catalog)==sha(c['model_catalog'])
    else:shutil.copyfile(c['model_catalog'],catalog)
    env=os.environ.copy();env['DEEPSEEK_API_KEY']=secrets['DEEPSEEK_API_KEY'];env['PYTHONPATH']=os.pathsep.join(sys.path[:3])
    cmd=[sys.executable,'-m','skillopt_verusage.codex_deepseek_bridge','--native-responses','--model',c['model'],'--port',str(c['bridge_port']),'--upstream-base-url',secrets.get('DEEPSEEK_BASE_URL','https://api.deepseek.com'),'--expected-upstream-model',c['model'],'--request-timeout-seconds','540','--ledger-path',str(root/'actor_bridge_calls.jsonl'),'--manifest-path',str(root/'actor_bridge_manifest.json'),'--model-catalog-path',c['model_catalog']]
    cmd+=bridge_budget_args(c)
    with (root/'bridge.log').open('a') as log:
        bridge=subprocess.Popen(cmd,env=env,stdout=log,stderr=log)
        try:
            for _ in range(30):
                if bridge.poll() is not None:raise RuntimeError('Bridge exited')
                try:urllib.request.urlopen(f"http://127.0.0.1:{c['bridge_port']}/health",timeout=1).read();break
                except Exception:time.sleep(1)
            else:raise RuntimeError('Bridge not ready')
            for k in list(os.environ):
                if k.endswith('API_KEY'):os.environ.pop(k)
            os.environ['SKILLOPT_CODEX_BRIDGE_TOKEN']='local-bridge-only'
            for cp in cps:
                if published_replay:
                    private,_=paths(c,cp)
                    replay=json.loads((private/'published_hint_replay.json').read_text())
                    assert replay['hint_generation_api_called'] is False
                    for name in ('call_started.json','response.raw','usage.json','output_text.txt'):
                        assert not (private/name).exists(), f'Hint-provider artifact exists during replay: {private/name}'
                else:
                    write(root/'status.json',{'state':'running','checkpoint':cp,'phase':'hint','updated_at':now(),'pid':os.getpid()})
                    generate_hint(c,cp)
                write(root/'status.json',{'state':'running','checkpoint':cp,'phase':'actor','updated_at':now(),'pid':os.getpid()})
                actor(c,cp)
            write(root/'status.json',{'state':'requested_batch_completed','condition':'published_hint_replay' if published_replay else 'generated_hint','checkpoints':cps,'updated_at':now()})
        finally:
            bridge.terminate()
            try:bridge.wait(timeout=10)
            except subprocess.TimeoutExpired:bridge.kill();bridge.wait()

def with_bridge_no_hint(c, cps):
    root=Path(c['output_root']);secrets=credentials(c)
    catalog=root/'models.json'
    if catalog.exists():assert sha(catalog)==sha(c['model_catalog'])
    else:shutil.copyfile(c['model_catalog'],catalog)
    env=os.environ.copy();env['DEEPSEEK_API_KEY']=secrets['DEEPSEEK_API_KEY'];env['PYTHONPATH']=os.pathsep.join(sys.path[:3])
    cmd=[sys.executable,'-m','skillopt_verusage.codex_deepseek_bridge','--native-responses','--model',c['model'],'--port',str(c['bridge_port']),'--upstream-base-url',secrets.get('DEEPSEEK_BASE_URL','https://api.deepseek.com'),'--expected-upstream-model',c['model'],'--request-timeout-seconds','540','--ledger-path',str(root/'actor_bridge_calls.jsonl'),'--manifest-path',str(root/'actor_bridge_manifest.json'),'--model-catalog-path',c['model_catalog']]
    cmd+=bridge_budget_args(c)
    with (root/'bridge.log').open('a') as log:
        bridge=subprocess.Popen(cmd,env=env,stdout=log,stderr=log)
        try:
            for _ in range(30):
                if bridge.poll() is not None:raise RuntimeError('Bridge exited')
                try:urllib.request.urlopen(f"http://127.0.0.1:{c['bridge_port']}/health",timeout=1).read();break
                except Exception:time.sleep(1)
            else:raise RuntimeError('Bridge not ready')
            for k in list(os.environ):
                if k.endswith('API_KEY'):os.environ.pop(k)
            os.environ['SKILLOPT_CODEX_BRIDGE_TOKEN']='local-bridge-only'
            for cp in cps:
                write(root/'status.json',{'state':'running','checkpoint':cp,'phase':'no_hint_actor','updated_at':now(),'pid':os.getpid()})
                actor_no_hint(c,cp)
            write(root/'status.json',{'state':'requested_batch_completed','condition':'matched_no_hint','checkpoints':cps,'updated_at':now()})
        finally:
            bridge.terminate()
            try:bridge.wait(timeout=10)
            except subprocess.TimeoutExpired:bridge.kill();bridge.wait()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True);parser.add_argument('mode',choices=['prepare','hint','run','seed-published-hints','run-published-hints','prepare-no-hint','run-no-hint']);parser.add_argument('--checkpoints',type=int,nargs='+',default=[1]);a=parser.parse_args();c=json.loads(a.config.read_text())
    root=Path(c['output_root']);assert not root.resolve().is_relative_to(REPO)
    os.environ['VERUS_SKILL_RUN_ROOT']=str(root);os.environ['CARGO_HOME']=str(Path(c['rust_root'])/'cargo');os.environ['RUSTUP_HOME']=str(Path(c['rust_root'])/'rustup');os.environ['PATH']=os.environ['CARGO_HOME']+'/bin:'+os.environ['PATH']
    assert all(n>=1 for n in a.checkpoints) and len(set(a.checkpoints))==len(a.checkpoints)
    if a.mode not in {'prepare','prepare-no-hint'}:
        allowed={x['ordinal'] for x in json.loads((root/'selection.json').read_text())['checkpoints']}
        assert set(a.checkpoints)<=allowed, 'Checkpoint not in frozen selection'
    try:
        if a.mode=='prepare':prepare(c)
        elif a.mode=='prepare-no-hint':prepare_no_hint(c)
        elif a.mode=='seed-published-hints':seed_published_hints(c,a.checkpoints)
        elif a.mode=='run-published-hints':with_bridge(c,a.checkpoints,published_replay=True)
        elif a.mode=='hint':
            for n in a.checkpoints:generate_hint(c,n)
        elif a.mode=='run':with_bridge(c,a.checkpoints)
        else:with_bridge_no_hint(c,a.checkpoints)
    except Exception as e:
        write(root/'status.json',{'state':'blocked','error_type':type(e).__name__,'detail':str(e)[:500],'updated_at':now()});raise
if __name__=='__main__':main()
