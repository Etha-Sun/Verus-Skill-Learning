"""Four-arm development diagnostic from frozen code checkpoints, not replay."""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil

from export_codex_transcript import export_transcript
from validate_card_revision import bridge, sha
from skill_evolution_pilot.codex_runner import _run_complete
from skillopt_verusage import card_query, codex_deepseek_bridge, codex_flash_runner
from skillopt_verusage.card_bank import audit_retrieval
from skillopt_verusage.codex_flash_runner import _bridge_usage, run_task
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.guarded_deepseek import write_json
from skillopt_verusage.skill_artifact import load_skill_artifact


ARMS = ('none', 'exposed', 'index', 'query')
# Snapshot and diagnostic IDs were selected before any new continuation output.
CASES = (
    ('62ff0a3cf2c458b36ac8', '000001-candidate.rs', 'item_6', ['card-001']),
    ('a23a4969155913255f76', '000037-candidate.rs', 'item_12', ['card-006', 'card-058']),
    ('599792dd13f472f45fa4', '000001-candidate.rs', 'item_5', []),
    ('3f17ea7c76a0ce99c098', '000001-candidate.rs', 'item_5', []),
)
QUERY_GUIDE = '''

## Optional keyword lookup

You may also search the same card library when the index is hard to scan:

    python3 card_query.py "keywords from the current diagnostic or proof obligation"

The tool searches the full card text and returns lexical excerpts, not advice.
You choose whether to search, refine the query, page with --offset, or change
--limit. Read any promising full card with card_read.py before relying on it.
There is no required query, read count, or automatic injection into your proof.
'''


def check_inputs(contract):
    changed = [path for path, digest in contract['input_hashes'].items()
               if not Path(path).is_file() or sha(path) != digest]
    if changed:
        raise ValueError('Frozen inputs changed: ' + ', '.join(changed))


def prepare(config_path, baseline, parent, root):
    if any(root.iterdir()):
        raise ValueError('Refuse to overwrite a diagnostic directory')
    config = json.loads(config_path.read_text())
    repo = Path(config['repo'])
    manifest = repo/'fixed-claude-stratified-80-seed20260814/val/items.json'
    sources = {row['id']: row for row in json.loads(manifest.read_text())}
    bank = json.loads((baseline/'cards.json').read_text())
    cards = {card['id']: card for card in bank['cards']}
    original_skill = (baseline/'SKILL.md').read_text()
    seed, marker, _ = original_skill.partition('## On-demand proof repair cards')
    if not marker or len(cards) != 78:
        raise ValueError('Expected the frozen short-index repaired-78 baseline')
    inputs = {}
    def freeze(path):
        inputs[str(path.resolve())] = sha(path)
    for path in (config_path, manifest, Path(__file__), Path(card_query.__file__),
                 Path(codex_deepseek_bridge.__file__), Path(codex_flash_runner.__file__),
                 Path(__file__).with_name('validate_card_revision.py'),
                 Path(__file__).with_name('export_codex_transcript.py'),
                 repo/'skill-evolution-pilot/src/skill_evolution_pilot/codex_runner.py',
                 repo/'skillopt-verusage/src/skillopt_verusage/provider_capture.py',
                 Path(config['source_root'])/'models.json',
                 *(Path(config[k]) for k in ('codex_bin','verus_bin','lynette_bin'))):
        freeze(path)
    for path in baseline.rglob('*'):
        if path.is_file():
            freeze(path)
    cases = []
    for ident, snapshot, diagnostic_item, selected in CASES:
        source = sources[ident]
        episode = parent/'episodes'/('dev_revised--'+ident)
        checkpoint = episode/'snapshots'/snapshot
        original = repo/source['source_path']
        if sha(original) != source['source_sha256'] or sha(original) != sha(episode/'workspace/input.rs'):
            raise ValueError('Original source mismatch: '+ident)
        events_path = episode/'codex_events.raw.jsonl'
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        records = [e['item'] for e in events if e.get('type') == 'item.completed'
                   and e.get('item',{}).get('id') == diagnostic_item]
        if len(records) != 1 or 'error:' not in records[0].get('aggregated_output',''):
            raise ValueError('Expected one recorded failing diagnostic: '+ident)
        # Independently verify the saved candidate, so an event/snapshot mismatch
        # cannot silently turn this into a different proof state.
        workspace = root/'checkpoints'/ident
        workspace.mkdir(parents=True)
        shutil.copyfile(original, workspace/'input.rs')
        shutil.copyfile(checkpoint, workspace/'candidate.rs')
        checks = {}
        for tool, arguments in (('verus', ['candidate.rs']), ('lynette', [])):
            wrapper = episode/'workspace/tools'/('run_'+tool+'.sh')
            freeze(wrapper)
            check = _run_complete(['bash', str(wrapper), *arguments], cwd=workspace, timeout_seconds=90)
            checks[tool] = check
        write_json(workspace/'preflight.json', checks)
        if (checks['verus']['returncode'] == 0 or checks['lynette']['returncode'] != 0
                or 'verification results::' not in checks['verus']['stdout']+checks['verus']['stderr']):
            raise ValueError('Checkpoint must fail Verus and pass proof-only comparison: '+ident)
        # Use the freshly checked diagnostic, not a truncated historical head/tail.
        diagnostic = checks['verus']['stdout'] + checks['verus']['stderr']
        diagnostic = diagnostic.replace(str(workspace/'candidate.rs'), 'candidate.rs')
        context = ('Continue the supplied code checkpoint. Its most recent local Verus '
                   'diagnostic is below. Recheck it as needed. No reference solution '
                   'or prior conversation is supplied.\n\n'+diagnostic)
        (workspace/'context.txt').write_text(context)
        bundle_paths = {}; artifacts = {}
        for arm in ARMS:
            bundle = root/'bundles'/ident/arm
            bundle.mkdir(parents=True)
            if arm in ('index', 'query'):
                shutil.copytree(baseline, bundle, dirs_exist_ok=True)
                if arm == 'query':
                    shutil.copyfile(Path(card_query.__file__), bundle/'card_query.py')
                    (bundle/'SKILL.md').write_text(original_skill + QUERY_GUIDE)
            else:
                text = seed
                if selected and arm == 'exposed':
                    text += ('## Optional proof repair advice\n\nThe following cards are '
                             'fallible advice. Check Trigger and Avoid when before use; '
                             'you may decline them. Normal verification and safety rules apply.\n\n')
                    text += '\n\n'.join(ident+'\n'+cards[ident]['content'] for ident in selected)+'\n'
                (bundle/'SKILL.md').write_text(text)
            bundle_paths[arm] = str(bundle)
            artifacts[arm] = load_skill_artifact(bundle).manifest()
            for path in bundle.rglob('*'):
                if path.is_file():
                    freeze(path)
        for path in (original, checkpoint, events_path, workspace/'input.rs',
                     workspace/'candidate.rs', workspace/'context.txt'):
            freeze(path)
        cases.append({**source, 'checkpoint':str(workspace/'candidate.rs'),
                      'context':str(workspace/'context.txt'), 'historical_snapshot':str(checkpoint),
                      'historical_diagnostic_item':diagnostic_item, 'reviewed_card_ids':selected,
                      'applicability': 'reviewed applicable advice, not a complete solution' if selected
                          else 'no confirmed exact match; not a proven absence of useful advice',
                      'bundle_paths':bundle_paths, 'artifacts':artifacts})
        print(json.dumps({'phase':'checkpoint_preflight_passed','id':ident,
                          'reviewed_card_ids':selected}),flush=True)
    schedule = [{'id':case['id'], 'condition':arm} for i,case in enumerate(cases)
                for arm in ARMS[i:]+ARMS[:i]]
    contract = {'schema_version':'card-routing-checkpoint-dev-v1', 'config_path':str(config_path),
                'items':cases, 'schedule':schedule, 'input_hashes':inputs,
                'model':'deepseek-v4-pro', 'reasoning_effort':'max', 'timeout_seconds':600,
                'workers':2, 'reference_proof_supplied':False, 'ordinary_retry':False,
                'sealed_test_access':False, 'expense_policy':'record_only',
                'installed_library_root':str(Path(config['verus_bin']).parent/'vstd'),
                'caveat':'Purpose-selected development cases, one attempt per cell; fresh '
                    'checkpoint continuations, not original conversation replay. Empty exposed '
                    'arms duplicate none information. Query retains the full index; this tests '
                    'search availability, not index replacement. No efficacy or held-out claims.'}
    write_json(root/'contract.json',contract)
    check_inputs(contract)
    return contract


def execute(root, contract):
    config = json.loads(Path(contract['config_path']).read_text())
    repo = Path(config['repo'])
    for line in (repo/'.env').read_text().splitlines():
        key, sep, value = line.strip().removeprefix('export ').partition('=')
        if sep and key.strip() in ('DEEPSEEK_API_KEY', 'VERUS_SKILL_DATA_ROOT'):
            words = shlex.split(value, comments=True)
            if words:
                os.environ.setdefault(key.strip(),words[0])
    if not os.environ.get('DEEPSEEK_API_KEY') or not os.environ.get('VERUS_SKILL_DATA_ROOT'):
        raise RuntimeError('Credential/data root missing; values not logged')
    os.environ.setdefault('SKILLOPT_CODEX_BRIDGE_TOKEN','local-loopback-only')
    check_inputs(contract)
    (root/'episodes').mkdir()
    cases = {row['id']:row for row in contract['items']}
    rows = []; failures = []
    with bridge(config,root) as (settings,url,manifest):
        def episode(job):
            check_inputs(contract)
            case = cases[job['id']]; arm = job['condition']
            key = 'routing_'+arm+'--'+job['id']; out = root/'episodes'/key
            source = repo/case['source_path']
            target = root/'inputs'/case['directory_group']/'unverified'/source.name
            # One input copy per case, prepared before concurrent dispatch below.
            print(json.dumps({'phase':'starting','key':key}),flush=True)
            row = run_task(item_id=case['id'], source=target,
                expected_source_sha256=case['source_sha256'], directory_group=case['directory_group'],
                out_dir=out, skill_file=None, skill_dir=Path(case['bundle_paths'][arm]),
                expected_skill_sha256=case['artifacts'][arm]['artifact_sha256'],
                codex_bin=Path(config['codex_bin']), verus_bin=Path(config['verus_bin']),
                lynette_bin=Path(config['lynette_bin']), bridge_url=url,
                bridge_ledger_path=settings.ledger_path, bridge_manifest_path=manifest,
                bridge_task_key=key, model=contract['model'], reasoning_effort=contract['reasoning_effort'],
                timeout_seconds=contract['timeout_seconds'], model_context_window=1048576,
                run_stage='dev_routing_'+arm, initial_candidate_source=Path(case['checkpoint']),
                continuation_instructions=Path(case['context']).read_text(),
                reference_proof_source=None, reference_kind='none',
                actor_isolation_scratch_root=Path(config['scratch_root']),
                actor_isolation_verus_root=Path(config['verus_bin']).parent,
                actor_isolation_rust_root=Path(config['source_root'])/'toolchain',
                actor_isolation_forbidden_paths=(repo,Path(os.environ['VERUS_SKILL_DATA_ROOT']),
                    Path(config['source_root'])/'rollout',Path(config['source_root'])/'train_items.json'),
                installed_library_root=Path(contract['installed_library_root']))
            return {'id':case['id'], 'condition':arm, 'episode':str(out), 'row':row}
        for case in cases.values():
            source = repo/case['source_path']
            target = root/'inputs'/case['directory_group']/'unverified'/source.name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
        jobs = iter(contract['schedule'])
        with ThreadPoolExecutor(max_workers=contract['workers']) as pool:
            pending = {pool.submit(episode,next(jobs)) for _ in range(contract['workers'])}
            while pending:
                done,pending = wait(pending,return_when=FIRST_COMPLETED)
                for future in done:
                    try:
                        result = future.result(); rows.append(result)
                        print(json.dumps({'phase':'finished','id':result['id'],
                            'condition':result['condition'],'solved':result['row']['proof_solved']}),flush=True)
                        if not result['row']['provider_valid']:
                            failures.append({'episode':result['episode'],'reason':'invalid_provider'})
                    except Exception as error:
                        failures.append({'reason':type(error).__name__+': '+str(error)})
                if settings.halted_error:
                    failures.append({'reason':settings.halted_error})
                write_json(root/'progress.json',{'rows':rows,'completed':len(rows),'failures':failures})
                while len(pending)<contract['workers'] and not failures:
                    job = next(jobs,None)
                    if job is None:
                        break
                    pending.add(pool.submit(episode,job))
    for result in rows:
        out = Path(result['episode']); key = result['row']['bridge_task_key']
        result['settled_usage'] = _bridge_usage(root/'provider_calls.jsonl',key,contract['model'])
        result['retrieval'] = audit_retrieval(out/'codex_events.raw.jsonl')
        result['reviewed_card_body_hits'] = sorted(set(result['retrieval'].get('read_ids',[])) &
                                                  set(cases[result['id']]['reviewed_card_ids']))
        packet = export_transcript(out,root/'provider_calls.jsonl',root/'full_traces'/key)
        result['transcript_completeness'] = packet['completeness']
    try:
        check_inputs(contract); unchanged = True
    except ValueError as error:
        unchanged = False; failures.append({'reason':str(error)})
    summary = {'rows':rows, 'failures':failures, 'completed_episodes':len(rows),
               'expected_episodes':len(contract['schedule']), 'bridge_drained':True,
               'frozen_inputs_unchanged':unchanged, 'ledger_sha256':sha(root/'provider_calls.jsonl'),
               'finished_at':datetime.now(timezone.utc).isoformat(),'caveat':contract['caveat']}
    write_json(root/'summary.json',summary)
    print(json.dumps({'phase':'complete','episodes':len(rows),'failures':len(failures)}),flush=True)
    if failures or len(rows)!=len(contract['schedule']):
        raise RuntimeError('Diagnostic partial/failed; inspect preserved outputs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--config',type=Path)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--parent',type=Path)
    args = parser.parse_args()
    root = _require_run_child(args.output.resolve())
    if args.prepare:
        if not all((args.config,args.baseline,args.parent)):
            parser.error('prepare requires config, baseline and parent')
        root.mkdir(parents=True,exist_ok=True)
        prepare(args.config.resolve(),args.baseline.resolve(),args.parent.resolve(),root)
    else:
        execute(root,json.loads((root/'contract.json').read_text()))


if __name__ == '__main__':
    main()
