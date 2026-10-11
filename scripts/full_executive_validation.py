"""Fresh validation20 x two Executive arms x two repeats; development only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import validate_card_revision as driver
from validate_executive_revision import TASKS as PILOT_TASKS, USAGE
from skill_evolution_pilot.codex_runner import build_prompt
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.guarded_deepseek import write_json


def schedule(ids):
    return [{'id':ident,'condition':condition,'repeat':repeat}
            for repeat in range(2) for i,ident in enumerate(ids)
            for condition in (('old','revised') if (i+repeat)%2==0 else ('revised','old'))]


def prepare(config_path, pilot, root, *, singleton_scheduler_fix=False):
    parent_path = pilot/'validation_contract.json'
    parent = json.loads(parent_path.read_text())
    scheduling_updates = {}
    for path,digest in parent['input_hashes'].items():
        if driver.sha(path)==digest: continue
        old = 'pending = {pool.submit(episode,next(jobs)) for _ in range(2)}'
        new = 'pending = {pool.submit(episode,next(jobs)) for _ in range(min(2,len(contract[\'schedule\'])))}'
        source = Path(path).read_text()
        if (not singleton_scheduler_fix or Path(path).resolve()!=Path(driver.__file__).resolve()
                or source.count(new)!=1 or
                hashlib.sha256(source.replace(new,old).encode()).hexdigest()!=digest):
            raise ValueError('Pilot methods changed; preserve comparability before scaling')
        scheduling_updates[path] = {'pilot_sha256':digest,'current_sha256':driver.sha(path),
            'change':'Initial worker submission capped by remaining schedule length; no method change'}
    if not json.loads((pilot/'executive_summary.json').read_text())['complete']:
        raise ValueError('Need completed pilot')
    repo = Path(json.loads(config_path.read_text())['repo'])
    manifest = repo/'fixed-claude-stratified-80-seed20260814/val/items.json'
    ids = [x['id'] for x in json.loads(manifest.read_text())]
    if len(ids)!=20 or len(set(ids))!=20 or not set(PILOT_TASKS)<=set(ids):
        raise ValueError('Expected complete fixed validation20 with pilot subset')
    for condition,name in (('old','control'),('revised','diagnostic')):
        shutil.copytree(parent['bundle_paths'][condition],root/name)
    for name in ('cards.json','card_read.py'):
        if (root/'control'/name).read_bytes()!=(root/'diagnostic'/name).read_bytes():
            raise ValueError('Executive-only comparison requires identical cards/reader')
    old_seed = repo/'skillopt-verusage/skills/initial.md'
    new_seed = repo/'skillopt-verusage/skills/diagnostic-first-v1.md'
    tails = []
    for name,seed in (('control',old_seed),('diagnostic',new_seed)):
        text = (root/name/'SKILL.md').read_text(); prefix = seed.read_text().rstrip()
        if not text.startswith(prefix+'\n'): raise ValueError('Unexpected Executive seed')
        tails.append(text[len(prefix):])
    if tails[0]!=tails[1]: raise ValueError('Retrieval/index tail changed')
    contract = driver.prepare(config_path,root/'control',root/'diagnostic',root,
        task_ids=tuple(ids),installed_library_conditions=('old','revised'))
    prompt = root/'shared_task_prompt.txt'
    prompt.write_text(build_prompt(installed_library_root=Path(contract['installed_library_root'])))
    if prompt.read_bytes()!=(pilot/'shared_task_prompt.txt').read_bytes():
        raise ValueError('Shared TASK changed since pilot')
    contract.update({'schema_version':'full-executive-validation-dev-v1','schedule':schedule(ids),
        'expected_episodes':80,'repetitions':2,'pilot_task_ids':list(PILOT_TASKS),
        'arm_labels':parent['arm_labels'],'bank_changed':False,'index_changed':False,
        'diagnostic_retrieval_guidance':False,'shared_task_prompt_corrected':True,
        'primary_endpoint':parent['primary_endpoint'],'historical_results_reused':False,
        'pilot_contract_sha256':driver.sha(parent_path),
        'scheduler_only_updates':scheduling_updates,
        'caveat':'Eighty fresh episodes on all20 previously exposed validation tasks, two repeats per arm. '
                 'Same pilot method, Executive only; report pilot6 and remaining14 separately. '
                 'Not untouched test, augmentation ablation or independent80-problem evidence. '
                 'Terminal proof safety does not certify operational access compliance.'})
    for path in (Path(__file__).resolve(),repo/'scripts/validate_executive_revision.py',
                 repo/'scripts/audit_executive_pilot.py',
                 old_seed,new_seed,prompt,parent_path,pilot/'executive_summary.json',
                 root/'pilot_audit/audit.json'):
        contract['input_hashes'][str(path.resolve())] = driver.sha(path)
    write_json(root/'validation_contract.json',contract)
    return contract


def totals(rows):
    return {'n':len(rows),'within_budget_dual_pass':sum(bool(x['row']['proof_solved'] and
        x['row']['safety_passed'] and x['row']['within_budget']) for x in rows),
        'final_dual_pass':sum(bool(x['row']['proof_solved'] and x['row']['safety_passed']) for x in rows),
        'timeouts':sum(bool(x['row']['timed_out']) for x in rows),
        'actor_seconds':sum(x['row']['actor_wall_seconds'] for x in rows),
        'body_read_episodes':sum(bool(x['retrieval'].get('read_ids')) for x in rows),
        'body_read_calls':sum(x['retrieval']['read_calls'] for x in rows),
        'usage':{k:sum(x['settled_usage'][k] for x in rows) for k in USAGE},
        'settled_errors':sum(x['settled_usage']['error_requests'] for x in rows),
        'unmetered_requests':sum(x['settled_usage']['unmetered_requests'] for x in rows)}


def aggregate(root):
    contract = json.loads((root/'validation_contract.json').read_text())
    summary = json.loads((root/'summary.json').read_text())
    expected = {(i['id'],c,r) for i in contract['items'] for c in ('old','revised') for r in range(2)}
    jobs = {driver.episode_key(x):x for x in contract['schedule']}
    actual = []; annotated = []
    for result in summary['rows']:
        job = jobs.get(result['row']['bridge_task_key'],{})
        actual.append((result['row']['id'],result['condition'],job.get('repeat')))
        annotated.append((result,job.get('repeat')))
    provider_valid = all(x['settled_usage']['error_requests']==0 and
        x['settled_usage']['unmetered_requests']==0 and
        x['settled_usage']['completed_requests']==x['settled_usage']['requests'] for x in summary['rows'])
    complete = (len(actual)==80 and len(expected)==80 and set(actual)==expected and
        not summary['failures'] and summary['reviewed_inputs_unchanged'] and
        summary['bridge_drained'] and provider_valid)
    strata = {'all':{x['id'] for x in contract['items']},'pilot6':set(contract['pilot_task_ids']),
              'remaining14':{x['id'] for x in contract['items']}-set(contract['pilot_task_ids'])}
    result = {'complete':complete,'settled_provider_valid':provider_valid,
        'totals':{c:totals([x for x in summary['rows'] if x['condition']==c]) for c in ('old','revised')},
        'strata':{name:{c:totals([x for x in summary['rows'] if x['condition']==c and
            x['row']['id'] in ids]) for c in ('old','revised')} for name,ids in strata.items()},
        'by_repeat':{str(r):{c:totals([x for x,repeat in annotated if repeat==r and
            x['condition']==c]) for c in ('old','revised')} for r in range(2)},
        'completed_matrix':actual,'failures':summary['failures'],
        'summary_sha256':driver.sha(root/'summary.json'),'caveat':contract['caveat']}
    write_json(root/'full_executive_summary.json',result)
    print(json.dumps({'phase':'aggregated','complete':complete,'totals':result['totals']}),flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--pilot',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--review',type=Path)
    args = parser.parse_args(); root = _require_run_child(args.output)
    if args.prepare:
        if args.pilot is None: parser.error('prepare requires completed pilot root')
        prepare(args.config.resolve(),args.pilot.resolve(),root)
        print(json.dumps({'phase':'prepared','episodes':80,
                         'contract_sha256':driver.sha(root/'validation_contract.json')}),flush=True)
        return
    if args.review is None: parser.error('fresh Astra review required')
    driver.check_review(args.review,root/'validation_contract.json')
    contract = json.loads((root/'validation_contract.json').read_text())
    try:
        driver.run(json.loads(args.config.read_text()),root,contract,expected_episodes=80)
    finally:
        if (root/'summary.json').exists(): aggregate(root)


if __name__=='__main__': main()
