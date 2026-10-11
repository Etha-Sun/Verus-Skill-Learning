"""Eight reviewer-gated development episodes; not an independent efficacy test."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import shutil
import threading
import time

from export_codex_transcript import export_transcript
from skillopt_verusage import codex_deepseek_bridge as implementation
from skillopt_verusage.card_bank import audit_retrieval
from skillopt_verusage.codex_deepseek_bridge import BridgeConfig, make_handler
from skillopt_verusage.codex_flash_runner import run_task, _bridge_usage
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.guarded_deepseek import write_json
from skillopt_verusage.skill_artifact import load_skill_artifact


TASKS = ('599792dd13f472f45fa4', '9a3d1aae6d0ea05a5ee1',
         'aa78e84a931f703c7e9c', '4dc90b360e4b603c1826')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def episode_key(job):
    key = 'dev_'+job['condition']+'--'+job['id']
    return key if 'repeat' not in job else key+'--repeat-'+str(job['repeat'])


def check_review(receipt, contract):
    approval = json.loads(receipt.read_text())
    if (approval.get('decision') not in ('APPROVE', 'APPROVE_WITH_NONBLOCKING_NOTES')
            or approval.get('contract_sha256') != sha(contract)):
        raise ValueError('Live run requires Astra approval of this exact contract')


def prepare(config_path, old, new, root, *, task_ids=TASKS,
            installed_library_conditions=('revised',)):
    config = json.loads(config_path.read_text())
    repo = Path(config['repo']).resolve()
    manifest = repo/'fixed-claude-stratified-80-seed20260814/val/items.json'
    items = {item['id']:item for item in json.loads(manifest.read_text())}
    artifacts = {name:load_skill_artifact(path).manifest() for name,path in
                 (('old',old), ('revised',new))}
    inputs = {str(config_path.resolve()):sha(config_path), str(manifest):sha(manifest)}
    for name,path in (('old',old), ('revised',new)):
        for entry in artifacts[name]['files']:
            inputs[str(path.resolve()/entry['relative_path'])] = entry['sha256']
    sources = []
    if not task_ids or len(set(task_ids)) != len(task_ids) or not set(task_ids) <= set(items):
        raise ValueError('Expected distinct validation task IDs')
    if not set(installed_library_conditions) <= {'old', 'revised'}:
        raise ValueError('Unknown installed-library condition')
    for ident in task_ids:
        item = items[ident]
        source = repo/item['source_path']
        if sha(source) != item['source_sha256']:
            raise ValueError('Frozen validation input changed')
        inputs[str(source)] = item['source_sha256']
        sources.append({key:item[key] for key in
                        ('id','task_id','directory_group','source_path','source_sha256')})
    method_files = [Path(__file__), Path(__file__).with_name('export_codex_transcript.py'),
                   Path(implementation.__file__)]
    for relative in ('skill-evolution-pilot/src/skill_evolution_pilot/codex_runner.py',
                     'skillopt-verusage/src/skillopt_verusage/codex_flash_runner.py',
                     'skillopt-verusage/src/skillopt_verusage/provider_capture.py',
                     'skillopt-verusage/review/augmented78_revision.json'):
        method_files.append(repo/relative)
    inputs.update({str(path.resolve()):sha(path) for path in method_files})
    inputs.update({config[key]:sha(config[key]) for key in ('codex_bin','verus_bin','lynette_bin')})
    catalog = Path(config['source_root'])/'models.json'
    inputs[str(catalog)] = sha(catalog)
    schedule = [{'id':ident, 'condition':condition} for i,ident in enumerate(task_ids)
                for condition in (('old','revised') if i % 2 == 0 else ('revised','old'))]
    contract = {'schema_version':'card-revision-validation-dev-v1', 'items':sources,
        'schedule':schedule, 'model':'deepseek-v4-pro', 'reasoning_effort':'max',
        'timeout_seconds':600, 'workers':2, 'artifacts':artifacts,
        'bundle_paths':{'old':str(old.resolve()),'revised':str(new.resolve())},
        'input_hashes':inputs, 'installed_library_root':str(Path(config['verus_bin']).parent/'vstd'),
        'public_provider_capture':True, 'reference_proof_supplied':False,
        'ordinary_retry':False, 'sealed_test_access':False, 'expense_policy':'record_only',
        'caveat':'Four purpose-selected analyzed validation tasks, package-level development comparison; not causal or independent confirmation.'}
    if installed_library_conditions != ('revised',):
        contract['installed_library_conditions'] = list(installed_library_conditions)
    if not root.is_dir() or (root/'validation_contract.json').exists():
        raise ValueError('Need a prepared external root and no prior validation contract')
    write_json(root/'validation_contract.json',contract)
    return contract


@contextmanager
def bridge(config, root):
    directory = root/'bridge'; directory.mkdir()
    catalog = (Path(config['source_root'])/'models.json').read_bytes()
    (directory/'models.json').write_bytes(catalog)
    ledger = root/'provider_calls.jsonl'; ledger.touch(exist_ok=False)
    settings = BridgeConfig(model='deepseek-v4-pro', upstream_base_url='https://api.deepseek.com',
        api_key=os.environ['DEEPSEEK_API_KEY'], ledger_path=ledger, max_output_tokens=131072,
        retry_output_tokens=131072, request_timeout_seconds=1800, native_responses=True,
        expected_upstream_model='deepseek-v4-pro', pricing_profile='deepseek-current',
        model_catalog=catalog, fail_closed_on_provider_error=True, capture_public_payloads=True)
    manifest = {'schema_version':'1', 'model':settings.model, 'upstream_base_url':settings.upstream_base_url,
        'max_output_tokens':131072, 'retry_output_tokens':131072, 'request_timeout_seconds':1800,
        'expected_upstream_model':settings.model, 'native_responses':True, 'chat_profile':'deepseek',
        'fail_closed_on_provider_error':True, 'capture_public_payloads':True,
        'pricing_profile':'deepseek-current', 'model_catalog_sha256':hashlib.sha256(catalog).hexdigest(),
        'protocol':'native_responses_passthrough', 'implementation_sha256':sha(implementation.__file__),
        'fake_mode':False, 'rate_limit_retries':0}
    settings.config_sha256 = hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    manifest['config_sha256'] = settings.config_sha256
    write_json(directory/'manifest.json',manifest)
    server = ThreadingHTTPServer(('127.0.0.1',0),make_handler(settings))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        yield settings, f'http://127.0.0.1:{server.server_port}', directory/'manifest.json'
    finally:
        server.shutdown()
        deadline = time.monotonic()+1810
        while settings.active_requests and time.monotonic()<deadline:
            time.sleep(1)
        server.server_close()
        if settings.active_requests:
            raise RuntimeError('Provider requests remain in flight; costs unknown, preserve and stop')


def run(config, root, contract, *, expected_episodes=8):
    repo = Path(config['repo']).resolve()
    for line in (repo/'.env').read_text().splitlines():
        key, separator, value = line.strip().removeprefix('export ').partition('=')
        if separator and key.strip() in ('DEEPSEEK_API_KEY','VERUS_SKILL_DATA_ROOT'):
            words = shlex.split(value,comments=True)
            if words:
                os.environ.setdefault(key.strip(),words[0])
    if not os.environ.get('DEEPSEEK_API_KEY') or not os.environ.get('VERUS_SKILL_DATA_ROOT'):
        raise RuntimeError('Provider credential/data root missing; values not logged')
    os.environ.setdefault('SKILLOPT_CODEX_BRIDGE_TOKEN','local-loopback-only')
    if any(sha(path) != digest for path,digest in contract['input_hashes'].items()):
        raise ValueError('Reviewed contract inputs changed before execution')
    (root/'episodes').mkdir(exist_ok=False)
    items = {item['id']:item for item in contract['items']}
    for item in items.values():
        source = repo/item['source_path']
        target = root/'inputs'/item['directory_group']/'unverified'/source.name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        item['runtime_source'] = str(target)
    rows = []; failures = []
    with bridge(config,root) as (settings,url,manifest):
        def episode(job):
            item = items[job['id']]; condition = job['condition']
            key = episode_key(job); out = root/'episodes'/key
            print(json.dumps({'phase':'starting','key':key}),flush=True)
            row = run_task(item_id=item['id'], source=Path(item['runtime_source']),
                expected_source_sha256=item['source_sha256'], directory_group=item['directory_group'],
                out_dir=out, skill_file=None, skill_dir=Path(contract['bundle_paths'][condition]),
                expected_skill_sha256=contract['artifacts'][condition]['artifact_sha256'],
                codex_bin=Path(config['codex_bin']), verus_bin=Path(config['verus_bin']),
                lynette_bin=Path(config['lynette_bin']), bridge_url=url,
                bridge_ledger_path=settings.ledger_path, bridge_manifest_path=manifest,
                bridge_task_key=key, model=contract['model'], reasoning_effort='max',
                timeout_seconds=600, model_context_window=1048576, run_stage='dev_'+condition,
                reference_proof_source=None, reference_kind='none',
                actor_isolation_scratch_root=Path(config['scratch_root']),
                actor_isolation_verus_root=Path(config['verus_bin']).parent,
                actor_isolation_rust_root=Path(config['source_root'])/'toolchain',
                actor_isolation_forbidden_paths=(repo,Path(os.environ['VERUS_SKILL_DATA_ROOT']),
                    Path(config['source_root'])/'rollout',Path(config['source_root'])/'train_items.json'),
                installed_library_root=Path(contract['installed_library_root'])
                    if condition in contract.get('installed_library_conditions', ['revised']) else None)
            return {'condition':condition,'episode':str(out),'row':row}

        jobs = iter(contract['schedule'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = {pool.submit(episode,next(jobs)) for _ in range(min(2,len(contract['schedule'])))}
            while pending:
                done,pending = wait(pending,return_when=FIRST_COMPLETED)
                for future in done:
                    try:
                        result = future.result(); rows.append(result)
                        row = result['row']
                        print(json.dumps({'phase':'finished','key':row['bridge_task_key'],
                                          'solved':row['proof_solved'],'fidelity':row['fidelity']}),flush=True)
                        if not row['provider_valid']:
                            failures.append({'episode':result['episode'],'reason':'invalid_provider'})
                    except Exception as error:
                        failures.append({'reason':type(error).__name__+': '+str(error)})
                if settings.halted_error:
                    failures.append({'reason':settings.halted_error})
                write_json(root/'progress.json',{'completed':len(rows),'failures':failures})
                while len(pending)<2 and not failures:
                    job = next(jobs,None)
                    if job is None:
                        break
                    pending.add(pool.submit(episode,job))
    for result in rows:
        out = Path(result['episode']); key = result['row']['bridge_task_key']
        result['settled_usage'] = _bridge_usage(root/'provider_calls.jsonl',key,'deepseek-v4-pro')
        result['retrieval'] = audit_retrieval(out/'codex_events.raw.jsonl')
        write_json(out/'retrieval_audit.json',result['retrieval'])
        packet = export_transcript(out,root/'provider_calls.jsonl',root/'full_traces'/key)
        result['transcript_completeness'] = packet['completeness']
    unchanged = all(sha(path)==digest for path,digest in contract['input_hashes'].items())
    summary = {'rows':rows,'failures':failures,'completed_episodes':len(rows),
        'expected_episodes':expected_episodes,'bridge_drained':True,'reviewed_inputs_unchanged':unchanged,
        'ledger_sha256':sha(root/'provider_calls.jsonl'),
        'finished_at':datetime.now(timezone.utc).isoformat(),'caveat':contract['caveat']}
    write_json(root/'summary.json',summary)
    print(json.dumps({'phase':'complete','episodes':len(rows),'failures':len(failures),
                      'inputs_unchanged':unchanged}),flush=True)
    if failures or not unchanged:
        raise RuntimeError('Development run stopped; inspect preserved summary')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--old',type=Path,required=True)
    parser.add_argument('--new',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--review',type=Path)
    args = parser.parse_args(); root = _require_run_child(args.output)
    if args.prepare:
        prepare(args.config,args.old,args.new,root)
        print(json.dumps({'phase':'prepared','contract_sha256':sha(root/'validation_contract.json')}))
        return
    if args.review is None:
        raise ValueError('Astra review receipt required')
    check_review(args.review,root/'validation_contract.json')
    run(json.loads(args.config.read_text()),root,json.loads((root/'validation_contract.json').read_text()))


if __name__ == '__main__':
    main()
