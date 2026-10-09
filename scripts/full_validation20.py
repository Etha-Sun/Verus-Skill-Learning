"""User-authorized scope extension, keeping the Astra-approved method frozen."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import validate_card_revision as driver
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.guarded_deepseek import write_json


def prepare(parent, root, config_path):
    contract_path = parent/'validation_contract.json'
    driver.check_review(parent/'astra-review/implementation_review.json',contract_path)
    base = json.loads(contract_path.read_text())
    prior = json.loads((parent/'summary.json').read_text())
    if prior['completed_episodes'] != 8 or prior['failures'] or not prior['reviewed_inputs_unchanged']:
        raise ValueError('Parent is not a complete accepted eight-episode result')
    config = json.loads(config_path.read_text()); repo = Path(config['repo'])
    manifest = repo/'fixed-claude-stratified-80-seed20260814/val/items.json'
    items = json.loads(manifest.read_text())
    if len(items)!=20 or len({i['id'] for i in items})!=20:
        raise ValueError('Expected fixed validation20')
    previous = {(e['row']['id'],e['condition']) for e in prior['rows']}
    expected_previous = {(ident,condition) for ident in driver.TASKS for condition in ('old','revised')}
    if previous != expected_previous:
        raise ValueError('Parent task/condition coverage mismatch')
    expected_config = next(p for p in base['input_hashes'] if p.endswith('/config.json'))
    if driver.sha(config_path)!=base['input_hashes'][expected_config]:
        raise ValueError('Runtime config differs from approved method')
    inputs = dict(base['input_hashes'])
    old_driver = repo/'scripts/validate_card_revision.py'
    if driver.sha(root/'parent_driver_snapshot.py') != inputs[str(old_driver)]:
        raise ValueError('Parent driver snapshot does not bind approved code')
    # Only orchestrator result-count metadata changes; actor/prompt/bundle code stays exact.
    inputs[str(old_driver)] = driver.sha(old_driver)
    inputs[str(Path(__file__).resolve())] = driver.sha(__file__)
    for path in (contract_path,parent/'summary.json',parent/'astra-review/implementation_review.json',
                 root/'parent_driver_snapshot.py'):
        inputs[str(path)] = driver.sha(path)
    sources = []
    for item in items:
        source = repo/item['source_path']
        if driver.sha(source)!=item['source_sha256']:
            raise ValueError('Validation input changed')
        inputs[str(source)] = item['source_sha256']
        if item['id'] not in driver.TASKS:
            sources.append({k:item[k] for k in ('id','task_id','directory_group','source_path','source_sha256')})
    if any(driver.sha(p)!=h for p,h in inputs.items()):
        raise ValueError('Frozen method or evidence changed')
    contract = deepcopy(base)
    contract.update({'schema_version':'full-validation20-extension-v1','items':sources,
        'schedule':[{'id':item['id'],'condition':condition} for i,item in enumerate(sources)
                    for condition in (('old','revised') if i%2==0 else ('revised','old'))],
        'input_hashes':inputs,'parent_root':str(parent), 'parent_summary_sha256':driver.sha(parent/'summary.json'),
        'authorization':'User requests overall validation; extend approved method, no new Astra scope approval claimed.',
        'caveat':'Development validation20, eight prior +32 continuation episodes. Report purpose-selected four separately from remaining16; no sealed-test or isolated card-effect claim.'})
    if len(contract['schedule'])!=32 or (root/'validation_contract.json').exists():
        raise ValueError('Need a fresh 32-episode continuation')
    write_json(root/'validation_contract.json',contract)


def aggregate(root, contract):
    prior_path = Path(contract['parent_root'])/'summary.json'
    if driver.sha(prior_path)!=contract['parent_summary_sha256']:
        raise ValueError('Parent summary changed')
    prior = json.loads(prior_path.read_text()); fresh = json.loads((root/'summary.json').read_text())
    rows = [dict(e,cohort='prior_development4') for e in prior['rows']]
    rows += [dict(e,cohort='remaining16') for e in fresh['rows']]
    if len({(e['row']['id'],e['condition']) for e in rows})!=len(rows):
        raise ValueError('Duplicate result')
    totals = {}
    for cohort in ('prior_development4','remaining16','all20'):
        totals[cohort] = {}
        for condition in ('old','revised'):
            selected = [e for e in rows if e['condition']==condition and (cohort=='all20' or e['cohort']==cohort)]
            totals[cohort][condition] = {'n':len(selected),
                'dual_pass':sum(bool(e['row']['proof_solved'] and e['row']['safety_passed']) for e in selected),
                'actor_seconds':sum(e['row']['actor_wall_seconds'] for e in selected),
                'usage':{k:sum(e['settled_usage'][k] for e in selected) for k in
                    ('requests','prompt_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens',
                     'completion_tokens','reasoning_tokens','estimated_cost_usd','unknown_cost_requests')},
                'episodes_with_body_reads':sum(bool(e['retrieval'].get('read_ids')) for e in selected)}
    write_json(root/'full_validation_summary.json',{'rows':rows,'totals':totals,
        'complete':len(rows)==40 and not fresh['failures'], 'fresh_failures':fresh['failures'],
        'parent_summary_sha256':driver.sha(prior_path),'continuation_summary_sha256':driver.sha(root/'summary.json'),
        'caveat':contract['caveat']})
    print(json.dumps({'phase':'full_validation_aggregated','totals':totals}),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--prepare',action='store_true')
    args = parser.parse_args(); root = _require_run_child(args.output)
    if args.prepare:
        prepare(args.parent.resolve(),root,args.config.resolve()); return
    contract = json.loads((root/'validation_contract.json').read_text())
    driver.check_review(Path(contract['parent_root'])/'astra-review/implementation_review.json',
                        Path(contract['parent_root'])/'validation_contract.json')
    try:
        driver.run(json.loads(args.config.read_text()),root,contract,expected_episodes=32)
    finally:
        if (root/'summary.json').exists():
            aggregate(root,contract)


if __name__=='__main__':
    main()
