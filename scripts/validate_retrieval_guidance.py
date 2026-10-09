"""Paired validation20 of optional guidance, with unchanged bank and permissions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import validate_card_revision as driver
from skillopt_verusage.card_bank import build_bundle
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.guarded_deepseek import write_json


def prepare(config_path, baseline, seed, descriptions, root):
    config = json.loads(config_path.read_text())
    repo = Path(config['repo'])
    manifest = repo/'fixed-claude-stratified-80-seed20260814/val/items.json'
    ids = tuple(item['id'] for item in json.loads(manifest.read_text()))
    if len(ids) != 20 or len(set(ids)) != 20:
        raise ValueError('Expected complete fixed validation20')
    recipe = json.loads(descriptions.read_text())
    for name, guided in (('control', False), ('guided', True)):
        build_bundle(baseline/'cards.json', seed, root/name, autonomous_retrieval=True,
                     index_descriptions=recipe['index_descriptions'], diagnostic_guidance=guided)
    for path in baseline.iterdir():
        if path.read_bytes() != (root/'control'/path.name).read_bytes():
            raise ValueError('Control must exactly reproduce frozen repaired bundle')
    for name in ('cards.json', 'card_read.py'):
        if (root/'control'/name).read_bytes() != (root/'guided'/name).read_bytes():
            raise ValueError('Only guidance may change')
    contract = driver.prepare(config_path, root/'control', root/'guided', root,
        task_ids=ids, installed_library_conditions=('old', 'revised'))
    contract.update({'schema_version':'retrieval-guidance-validation20-v1',
        'arm_labels':{'old':'frozen_repaired78_control','revised':'same78_optional_guidance'},
        'primary_endpoint':'proof_solved and safety_passed and within_budget',
        'ordinary_retry':False, 'bank_changed':False, 'index_changed':False,
        'guidance_only':True, 'baseline_commit':'3c39643',
        'caveat':'Forty contemporaneous development episodes, not untouched evaluation. '
                 'Same repaired78 bank/index and exact vstd permission; only optional guidance differs. '
                 'Body-read frequency is not adoption or benefit. Not an augmentation ablation.'})
    for path in (Path(__file__).resolve(), Path(build_bundle.__code__.co_filename).resolve(),
                 seed.resolve(), descriptions.resolve()):
        contract['input_hashes'][str(path)] = driver.sha(path)
    write_json(root/'validation_contract.json', contract)
    return contract


def aggregate(root):
    source = root/'summary.json'
    summary = json.loads(source.read_text())
    totals = {}
    for condition in ('old', 'revised'):
        rows = [e for e in summary['rows'] if e['condition'] == condition]
        totals[condition] = {'n':len(rows), 'within_budget_dual_pass':sum(
            bool(e['row']['proof_solved'] and e['row']['safety_passed'] and e['row']['within_budget'])
            for e in rows), 'final_dual_pass':sum(bool(e['row']['proof_solved'] and e['row']['safety_passed']) for e in rows),
            'timeouts':sum(bool(e['row']['timed_out']) for e in rows),
            'body_read_episodes':sum(bool(e['retrieval'].get('read_ids')) for e in rows),
            'body_read_calls':sum(e['retrieval']['read_calls'] for e in rows),
            'actor_seconds':sum(e['row']['actor_wall_seconds'] for e in rows),
            'usage':{k:sum(e['settled_usage'][k] for e in rows) for k in
                ('requests','prompt_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens',
                 'completion_tokens','reasoning_tokens','estimated_cost_usd','unknown_cost_requests')}}
    expected = {(item['id'], c) for item in json.loads((root/'validation_contract.json').read_text())['items']
                for c in ('old','revised')}
    actual = [(e['row']['id'],e['condition']) for e in summary['rows']]
    complete = (len(actual)==len(expected) and set(actual)==expected and not summary['failures']
                and summary['reviewed_inputs_unchanged'] and summary['bridge_drained'])
    result = {'complete':complete,'totals':totals,'summary_sha256':driver.sha(source),
              'failures':summary['failures'],'caveat':summary['caveat']}
    write_json(root/'guidance_summary.json',result)
    print(json.dumps(result),flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--seed',type=Path)
    parser.add_argument('--descriptions',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--review',type=Path)
    args = parser.parse_args(); root = _require_run_child(args.output)
    if args.prepare:
        if not all((args.baseline,args.seed,args.descriptions)):
            parser.error('prepare requires baseline, seed and descriptions')
        prepare(args.config.resolve(),args.baseline.resolve(),args.seed.resolve(),args.descriptions.resolve(),root)
        return
    if args.review is None:
        parser.error('run requires review receipt')
    driver.check_review(args.review,root/'validation_contract.json')
    contract = json.loads((root/'validation_contract.json').read_text())
    try:
        driver.run(json.loads(args.config.read_text()),root,contract,expected_episodes=40)
    finally:
        if (root/'summary.json').exists():
            aggregate(root)


if __name__=='__main__':
    main()
