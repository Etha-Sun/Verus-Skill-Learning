"""Six seen validation tasks, two arms and two repeats; development evidence only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import validate_card_revision as driver
from skill_evolution_pilot.codex_runner import build_prompt
from skillopt_verusage.card_bank import build_bundle
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.guarded_deepseek import write_json


TASKS = ('aded79905be896942897', 'a23a4969155913255f76',
         '3ce00a38706256ab00ea', '9b9f6ccef89db4103c7f',
         'b9e5384e929589f7b0cd', '599792dd13f472f45fa4')
USAGE = ('requests', 'prompt_tokens', 'prompt_cache_hit_tokens',
         'prompt_cache_miss_tokens', 'completion_tokens', 'reasoning_tokens',
         'estimated_cost_usd', 'unknown_cost_requests')


def schedule():
    return [{'id':ident, 'condition':condition, 'repeat':repeat}
            for repeat in range(2) for i,ident in enumerate(TASKS)
            for condition in (('old','revised') if (i+repeat)%2==0 else ('revised','old'))]


def prepare(config_path, baseline, old_seed, new_seed, descriptions, root):
    recipe = json.loads(descriptions.read_text())
    for name,seed in (('control',old_seed), ('diagnostic',new_seed)):
        build_bundle(baseline/'cards.json', seed, root/name, autonomous_retrieval=True,
                     index_descriptions=recipe['index_descriptions'], diagnostic_guidance=False)
    for path in baseline.iterdir():
        if path.read_bytes() != (root/'control'/path.name).read_bytes():
            raise ValueError('Control must reproduce frozen repaired78 bundle')
    for name in ('cards.json','card_read.py'):
        if (root/'control'/name).read_bytes() != (root/'diagnostic'/name).read_bytes():
            raise ValueError('Only Executive may differ')
    tails = [(root/name/'SKILL.md').read_text()[len(seed.read_text().rstrip()):]
             for name,seed in (('control',old_seed), ('diagnostic',new_seed))]
    if tails[0] != tails[1]:
        raise ValueError('Retrieval instructions/index must be identical')
    contract = driver.prepare(config_path, root/'control', root/'diagnostic', root,
        task_ids=TASKS, installed_library_conditions=('old','revised'))
    contract.update({'schema_version':'executive-pilot-dev-v1', 'schedule':schedule(),
        'expected_episodes':24, 'repetitions':2,
        'arm_labels':{'old':'initial_executive','revised':'diagnostic_first_v1'},
        'primary_endpoint':'proof_solved and safety_passed and within_budget',
        'bank_changed':False, 'index_changed':False, 'diagnostic_retrieval_guidance':False,
        'shared_task_prompt_corrected':True,
        'caveat':'Six purpose-selected already-analyzed validation tasks, two repeats per arm. '
                 'Only Executive differs; both arms share corrected TASK. Not general efficacy, '
                 'not independent held-out confirmation, not augmentation versus nonaugmentation.'})
    prompt_path = root/'shared_task_prompt.txt'
    prompt_path.write_text(build_prompt(installed_library_root=Path(contract['installed_library_root'])))
    for path in (Path(__file__).resolve(), Path(build_bundle.__code__.co_filename).resolve(),
                 old_seed.resolve(), new_seed.resolve(), descriptions.resolve(), prompt_path.resolve()):
        contract['input_hashes'][str(path)] = driver.sha(path)
    write_json(root/'validation_contract.json',contract)
    return contract


def aggregate(root):
    contract = json.loads((root/'validation_contract.json').read_text())
    summary = json.loads((root/'summary.json').read_text())
    expected = {(x['id'],x['condition'],x['repeat']) for x in contract['schedule']}
    jobs = {driver.episode_key(job):job for job in contract['schedule']}
    actual = []
    for result in summary['rows']:
        job = jobs[result['row']['bridge_task_key']]
        actual.append((result['row']['id'],result['condition'],job['repeat']))
    totals = {}
    for condition in ('old','revised'):
        rows = [x for x in summary['rows'] if x['condition']==condition]
        totals[condition] = {'n':len(rows), 'within_budget_dual_pass':sum(
            bool(x['row']['proof_solved'] and x['row']['safety_passed'] and x['row']['within_budget'])
            for x in rows), 'final_dual_pass':sum(bool(x['row']['proof_solved'] and
                x['row']['safety_passed']) for x in rows),
            'timeouts':sum(bool(x['row']['timed_out']) for x in rows),
            'actor_seconds':sum(x['row']['actor_wall_seconds'] for x in rows),
            'body_read_episodes':sum(bool(x['retrieval'].get('read_ids')) for x in rows),
            'body_read_calls':sum(x['retrieval']['read_calls'] for x in rows),
            'usage':{k:sum(x['settled_usage'][k] for x in rows) for k in USAGE}}
    complete = (len(actual)==24 and set(actual)==expected and len(expected)==24
        and not summary['failures'] and summary['reviewed_inputs_unchanged'] and summary['bridge_drained'])
    result = {'complete':complete,'totals':totals,'completed_matrix':actual,
        'summary_sha256':driver.sha(root/'summary.json'),'failures':summary['failures'],
        'caveat':contract['caveat']}
    write_json(root/'executive_summary.json',result)
    print(json.dumps(result),flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--old-seed',type=Path)
    parser.add_argument('--new-seed',type=Path)
    parser.add_argument('--descriptions',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--review',type=Path)
    args = parser.parse_args(); root = _require_run_child(args.output)
    if args.prepare:
        if not all((args.baseline,args.old_seed,args.new_seed,args.descriptions)):
            parser.error('prepare requires baseline, both seeds and descriptions')
        contract = prepare(args.config.resolve(),args.baseline.resolve(),args.old_seed.resolve(),
                           args.new_seed.resolve(),args.descriptions.resolve(),root)
        print(json.dumps({'phase':'prepared','episodes':len(contract['schedule']),
                          'contract_sha256':driver.sha(root/'validation_contract.json')}),flush=True)
        return
    if args.review is None:
        parser.error('run requires fresh Astra review receipt')
    driver.check_review(args.review,root/'validation_contract.json')
    contract = json.loads((root/'validation_contract.json').read_text())
    try:
        driver.run(json.loads(args.config.read_text()),root,contract,expected_episodes=24)
    finally:
        if (root/'summary.json').exists():
            aggregate(root)


if __name__=='__main__':
    main()
