"""Run frozen validation conditions through the existing isolated actor harness."""
from __future__ import annotations

import argparse
import fcntl
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request

from skill_evolution_pilot.actor_isolation import ActorIsolationConfig, isolation_preflight
from skillopt_verusage.codex_flash_runner import run_task
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.verus_release import require_formal_verus
from skillopt_verusage.skill_artifact import load_skill_artifact
from skillopt_verusage.card_bank import audit_retrieval


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def prepare(root):
    root = _require_run_child(root)
    cfg = json.loads((root / 'runtime_config.json').read_text())
    contract = json.loads((root / 'experiment_contract.json').read_text())
    split = Path(cfg['split_dir']).resolve()
    os.chdir(split.parent)
    val_file = split / 'val/items.json'
    if sha(val_file) != contract['validation_manifest_sha256']:
        raise ValueError('validation manifest changed')
    items = json.loads(val_file.read_text())
    train = json.loads((split / 'train/items.json').read_text())
    ids = {x['id'] for x in items}
    if len(items) != 20 or len(ids) != 20 or ids & {x['id'] for x in train}:
        raise ValueError('validation membership mismatch')
    if not set(contract['training_ids']) <= {x['id'] for x in train}:
        raise ValueError('extraction source not in train')
    for item in items:
        source = Path(item['source_path']).resolve()
        if sha(source) != item['source_sha256']:
            raise ValueError('validation source changed')
        item['source_path'] = str(source)
    os.environ['CARGO_HOME'] = str(Path(cfg['rust_root']) / 'cargo')
    os.environ['RUSTUP_HOME'] = str(Path(cfg['rust_root']) / 'rustup')
    os.environ['PATH'] = os.environ['CARGO_HOME'] + '/bin:' + os.environ['PATH']
    identity = require_formal_verus(Path(cfg['verus_bin']))
    probe = isolation_preflight()
    if not probe['supported']:
        raise RuntimeError(f'actor isolation unavailable: {probe}')
    isolation = ActorIsolationConfig(scratch_root=root/'rollouts', verus_root=Path(cfg['verus_root']), rust_root=Path(cfg['rust_root']), bridge_port=cfg['bridge_port'])
    isolation.validate(workspace=root/'rollouts/.preflight', codex_bin=Path(cfg['codex_bin']), lynette_bin=Path(cfg['lynette_bin']))
    write(root/'preflight.json', {'status':'passed', 'validation_count':20, 'verus':identity, 'isolation':probe, 'test_used':False})
    return root, cfg, contract, items


def schedule(items, conditions, pilot_ids, repetitions):
    pilot = [(0, c, x) for x in items if x['id'] in pilot_ids for c in conditions]
    rest = [(r,c,x) for r in range(repetitions) for x in items for c in conditions
            if not (r == 0 and x['id'] in pilot_ids)]
    random.Random(20260923).shuffle(pilot)
    random.Random(20260924).shuffle(rest)
    return pilot, rest


def valid_solved(row):
    return bool(row.get('hard')) and row.get('fidelity') != 'V0_INVALID' and 'runner_error' not in row


def aggregate(rows, conditions):
    groups = {}
    for condition in conditions:
        selected = [x for x in rows if x['condition'] == condition]
        groups[condition] = {'n':len(selected), 'within_budget_solved':sum(valid_solved(x) and x.get('within_budget',False) for x in selected),
            'dual_pass_including_late':sum(valid_solved(x) for x in selected),
            'timeouts':sum(bool(x.get('timed_out')) for x in selected),
            'invalid':sum(x.get('fidelity')=='V0_INVALID' or 'runner_error' in x for x in selected),
            'usage':{k:sum(int((x.get('usage') or {}).get(k,0) or 0) for x in selected) for k in ['requests','prompt_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens','completion_tokens']}, 'estimated_actor_cost_usd':sum(float((x.get('usage') or {}).get('estimated_cost_usd',0) or 0) for x in selected), 'per_repeat':{str(r):{'n':sum(x['repetition']==r for x in selected), 'within_budget_solved':sum(x['repetition']==r and valid_solved(x) and bool(x.get('within_budget')) for x in selected)} for r in sorted({x['repetition'] for x in selected})}}
    pairs = {}
    base = {(x['repetition'],x['id']):x for x in rows if x['condition']=='original_only'}
    for cond in conditions:
        if cond=='original_only': continue
        both = [(base[(x['repetition'],x['id'])],x) for x in rows if x['condition']==cond and (x['repetition'],x['id']) in base]
        joint = [(a,b) for a,b in both if valid_solved(a) and valid_solved(b) and a.get('within_budget') and b.get('within_budget')]
        pairs[cond]={'paired_n':len(both),'jointly_solved_n':len(joint),
            'original_completion':sum(a['usage']['completion_tokens'] for a,b in joint),
            'condition_completion':sum(b['usage']['completion_tokens'] for a,b in joint),
            'original_only_solves':sum(bool(valid_solved(a) and a.get('within_budget')) and not bool(valid_solved(b) and b.get('within_budget')) for a,b in both),
            'condition_only_solves':sum(bool(valid_solved(b) and b.get('within_budget')) and not bool(valid_solved(a) and a.get('within_budget')) for a,b in both)}
    return {'conditions':groups,'paired_against_original_only':pairs,'caveat':'Validation diagnostic; joint-success costs are conditional and must be read with all-run outcomes.'}


def run(root):
    root,cfg,contract,items = prepare(root)
    conditions = contract['primary_conditions'] + contract['secondary_conditions']
    audit = json.loads((root/'matched_audit.json').read_text())
    frozen = {}
    skills = {}
    for cond in conditions:
        skill = root/'skills'/cond if contract.get('deployment') == 'autonomous_card_retrieval' else root/'skills'/f'{cond}.md'
        skills[cond] = skill
        frozen[cond] = load_skill_artifact(skill).artifact_sha256
        if audit['skill_sha256'].get(cond) != frozen[cond] or audit['status']!='approved_for_validation':
            raise ValueError('skill differs from pre-validation audit')
    invocation={'contract_sha256':sha(root/'experiment_contract.json'), 'runtime_sha256':sha(root/'runtime_config.json'), 'skills':frozen,
                'driver_sha256':sha(Path(__file__)), 'verus_sha256':sha(cfg['verus_bin']), 'lynette_sha256':sha(cfg['lynette_bin']), 'codex_sha256':sha(cfg['codex_bin'])}
    invocation_path=root/'evaluation_invocation.json'
    if invocation_path.exists() and json.loads(invocation_path.read_text()) != invocation:
        raise ValueError('evaluation invocation changed; use a distinct experiment root')
    write(invocation_path,invocation)
    write(root/'frozen_skills.json', frozen)
    env = dict(os.environ)
    for line in Path(cfg['credential_file']).read_text().splitlines():
        line=line.strip().removeprefix('export ')
        if '=' not in line or line.startswith('#'):continue
        key,value=line.split('=',1)
        if key.strip() in {'DEEPSEEK_API_KEY','DEEPSEEK_BASE_URL'}:
            words=shlex.split(value,comments=True);env[key.strip()]=words[0] if words else ''
    if not env.get('DEEPSEEK_API_KEY'):raise RuntimeError('missing provider credential')
    env['PYTHONPATH']=os.pathsep.join(str(Path(p).resolve()) for p in sys.path if p)
    shutil.copyfile(cfg['model_catalog'],root/'models.json')
    cmd=[sys.executable,'-m','skillopt_verusage.codex_deepseek_bridge','--native-responses','--model',contract['actor_model'],'--expected-upstream-model',contract['actor_model'],
         '--port',str(cfg['bridge_port']),'--upstream-base-url',env.get('DEEPSEEK_BASE_URL','https://api.deepseek.com'),
         '--ledger-path',str(root/'bridge_calls.jsonl'),'--manifest-path',str(root/'bridge_manifest.json'),'--model-catalog-path',str(root/'models.json'),
         '--request-timeout-seconds','540','--budget-state-path',str(root/'budget.json'),'--approval-limit-usd',str(contract['budget_limit_usd'])]
    rows=[]
    def execute(job):
        repeat,cond,item=job
        out=root/'rollouts'/f'repeat_{repeat:02d}'/cond/item['id']
        result_file=out/'result.json'
        if result_file.exists():
            manifest=json.loads((out/'run_manifest.json').read_text())
            if manifest['skill_sha256'] != frozen[cond]:raise ValueError('resume skill mismatch')
            result=json.loads(result_file.read_text())
        else:
            if out.exists():raise RuntimeError(f'partial run requires audit: {out}')
            result=run_task(item_id=item['id'],source=Path(item['source_path']),expected_source_sha256=item['source_sha256'],directory_group=item['directory_group'],out_dir=out,
                skill_file=skills[cond] if skills[cond].is_file() else None,
                skill_dir=skills[cond] if skills[cond].is_dir() else None,
                expected_skill_sha256=frozen[cond],codex_bin=Path(cfg['codex_bin']),verus_bin=Path(cfg['verus_bin']),lynette_bin=Path(cfg['lynette_bin']),
                bridge_url=f"http://127.0.0.1:{cfg['bridge_port']}",bridge_ledger_path=root/'bridge_calls.jsonl',bridge_manifest_path=root/'bridge_manifest.json',
                bridge_task_key=f"validation--r{repeat}-{cond}-{item['id']}",model=contract['actor_model'],reasoning_effort=contract['reasoning_effort'],timeout_seconds=contract['timeout_seconds'],
                model_context_window=cfg['context_window'],reference_kind='none',run_stage='matched_skill_validation',actor_isolation_scratch_root=root/'rollouts',
                actor_isolation_verus_root=Path(cfg['verus_root']),actor_isolation_rust_root=Path(cfg['rust_root']),
                actor_isolation_forbidden_paths=(Path.cwd(),root/'extraction',root/'skills',Path(cfg['credential_file']),root.parent/'skillopt-fork-packets-20260922'))
        if contract.get('deployment') == 'autonomous_card_retrieval':
            retrieval = audit_retrieval(out/'codex_events.raw.jsonl')
            write(out/'retrieval_audit.json', retrieval)
            result = {**result, 'retrieval': {k: retrieval[k] for k in ('search_calls','read_calls','read_ids','empty_searches')}}
        return {**result,'condition':cond,'repetition':repeat,'project':item['project_code']}
    with (root/'bridge.log').open('a') as log:
        bridge=subprocess.Popen(cmd,env=env,stdout=log,stderr=log)
        try:
            for _ in range(30):
                if bridge.poll() is not None:raise RuntimeError('bridge exited')
                try:urllib.request.urlopen(f"http://127.0.0.1:{cfg['bridge_port']}/health",timeout=1).read();break
                except Exception:time.sleep(1)
            else:raise RuntimeError('bridge not ready')
            for key in list(os.environ):
                if key.endswith('API_KEY'):os.environ.pop(key)
            os.environ['SKILLOPT_CODEX_BRIDGE_TOKEN']='local-bridge-only'
            phases=schedule(items,conditions,contract['pilot_ids'],contract['repetitions'])
            if contract.get('pilot_only'):
                phases = (phases[0],)
            for phase,jobs in zip(['pilot','main'],phases):
                for start in range(0,len(jobs),contract['workers']):
                    chunk=jobs[start:start+contract['workers']]
                    write(root/'status.json',{'state':'running','phase':phase,'completed':len(rows),'planned':sum(map(len,phases)),'pid':os.getpid()})
                    errors=[]
                    with ThreadPoolExecutor(max_workers=contract['workers']) as pool:
                        futures={pool.submit(execute,j):j for j in chunk}
                        for future in as_completed(futures):
                            repeat,cond,item=futures[future]
                            try:row=future.result()
                            except Exception as error:
                                row={'id':item['id'],'condition':cond,'repetition':repeat,'runner_error':f'{type(error).__name__}: {error}'};errors.append(row)
                            rows.append(row)
                            write(root/'results.json',rows);write(root/'summary.json',aggregate(rows,conditions))
                            print(json.dumps({'condition':cond,'repeat':repeat,'id':item['id'],'hard':row.get('hard'),'fidelity':row.get('fidelity'),'completed':len(rows)}),flush=True)
                    if errors or any(r.get('fidelity')=='V0_INVALID' for r in rows):
                        raise RuntimeError('invalid infrastructure result; retained all records, stopped before next batch')
                write(root/f'{phase}_complete.json',{'n':len(rows),'no_skill_tuning':True})
            summary=aggregate(rows,conditions)
            text=['# Frozen validation results', '', 'Validation only. Skills were frozen before actor calls. Costs below are actor costs; teacher and extractor costs are separate.', '', '| Condition | Solved within budget | Runs | Completion tokens | Timeouts |', '|---|---:|---:|---:|---:|']
            for cond,g in summary['conditions'].items():
                text.append(f"| {cond} | {g['within_budget_solved']} | {g['n']} | {g['usage']['completion_tokens']} | {g['timeouts']} |")
            text += ['', 'Read summary.json for matched original-only pairs and per-repeat results. Do not treat lower tokens from failed/timeout attempts as efficiency success.', 'Full traces, costs, and failures are retained. Test split was not used.']
            if contract.get('pilot_only'):
                text += ['', 'This is a small pilot only, not the complete validation split or a conclusive transfer estimate.']
            (root/'RESULTS.md').write_text('\n'.join(text)+'\n')
            write(root/'status.json',{'state':'complete','completed':len(rows),'pid':os.getpid()})
        except Exception as error:
            write(root/'status.json',{'state':'stopped_for_audit','completed':len(rows),'error':f'{type(error).__name__}: {error}','pid':os.getpid()});raise
        finally:
            bridge.terminate()
            try:bridge.wait(timeout=10)
            except subprocess.TimeoutExpired:bridge.kill();bridge.wait()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-root',type=Path,required=True);parser.add_argument('--preflight-only',action='store_true');args=parser.parse_args()
    if args.preflight_only:
        prepare(args.run_root);print('preflight passed')
    else:
        root=_require_run_child(args.run_root)
        with (root/'runner.lock').open('a') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            run(root)


if __name__=='__main__':main()
