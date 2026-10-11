"""Bounded, method-neutral interface to the existing actor and provider ledger."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import hashlib
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import sys
import threading
import time

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO/'skillopt-verusage/src'), str(REPO/'skill-evolution-pilot/src')]
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.codex_deepseek_bridge import BridgeConfig, make_handler
from skillopt_verusage.codex_flash_runner import run_task, _bridge_usage
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def credential():
    for line in (REPO/'.env').read_text().splitlines():
        key, sep, value = line.strip().removeprefix('export ').partition('=')
        if sep and key.strip()=='DEEPSEEK_API_KEY':
            words = shlex.split(value, comments=True)
            if words:
                os.environ.setdefault(key.strip(), words[0])
    os.environ.setdefault('SKILLOPT_CODEX_BRIDGE_TOKEN','local-loopback-only')
    return os.environ['DEEPSEEK_API_KEY']


@contextmanager
def bridge(config, root, guard):
    directory = root/'bridge'
    directory.mkdir()
    catalog = (Path(config['source_root'])/'models.json').read_bytes()
    (directory/'models.json').write_bytes(catalog)
    settings = BridgeConfig(model='deepseek-v4-pro', upstream_base_url='https://api.deepseek.com',
        api_key=credential(), ledger_path=root/'provider_calls.jsonl', max_output_tokens=131072,
        retry_output_tokens=131072, request_timeout_seconds=1800, native_responses=True,
        expected_upstream_model='deepseek-v4-pro', pricing_profile='deepseek-current',
        model_catalog=catalog, fail_closed_on_provider_error=True, capture_public_payloads=True,
        budget_guard=guard, rate_limit_retries=0)
    manifest = {'model':settings.model,'max_output_tokens':131072,'retry_output_tokens':131072,
        'request_timeout_seconds':1800,'expected_upstream_model':settings.model,
        'native_responses':True,'chat_profile':'deepseek','pricing_profile':'deepseek-current',
        'model_catalog_sha256':hashlib.sha256(catalog).hexdigest(),
        'protocol':'native_responses_passthrough','implementation_sha256':sha(sys.modules[BridgeConfig.__module__].__file__),
        'fake_mode':False,'capture_public_payloads':True,'rate_limit_retries':0}
    settings.config_sha256 = hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    manifest['config_sha256'] = settings.config_sha256
    write_json(directory/'manifest.json',manifest)
    server = ThreadingHTTPServer(('127.0.0.1',0), make_handler(settings))
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
            raise RuntimeError('Provider requests unresolved: preserve evidence and stop')


def actors(request, root, runtime, guard):
    config = runtime['config']
    backend = root.parents[1]
    items = {x['id']:x for x in runtime['probes']}
    jobs = request['schedule']
    if not jobs or len(jobs)>40 or len({x['key'] for x in jobs})!=len(jobs):
        raise ValueError('Need 1..40 unique scheduled attempts')
    contract = Path(request['contract_path']).resolve()
    if sha(contract)!=request['contract_sha256']:
        raise ValueError('Frozen comparison contract changed')
    markers = backend/'attempts'
    markers.mkdir(exist_ok=True)
    if len(list(markers.iterdir()))+len(jobs)>runtime['actor_episode_limit']:
        raise ValueError('Phase episode ceiling exceeded')
    for job in jobs:
        if job['id'] not in items or Path(job['key']).name!=job['key']:
            raise ValueError('Only frozen training probes and safe keys are permitted')
        path = Path(job['skill_file']).resolve()
        if sha(path)!=job['skill_sha256'] or path.stat().st_size>runtime.get('context_byte_limit',1024):
            raise ValueError('Context changed or exceeds the phase byte ceiling')
    for job in jobs:
        with (markers/job['key']).open('x') as handle:
            json.dump({'request_sha256':sha(root/'request.json'),'job':job},handle)
    rows = []
    failures = []
    with bridge(config,root,guard) as (settings,url,manifest):
        def episode(job):
            item = items[job['id']]
            source = backend/'inputs'/item['directory_group']/'unverified'/Path(item['source_path']).name
            print(json.dumps({'phase':'actor_start','key':job['key']}),flush=True)
            row = run_task(item_id=item['id'],source=source,expected_source_sha256=item['source_sha256'],
                directory_group=item['directory_group'],out_dir=root/'episodes'/job['key'],
                skill_file=Path(job['skill_file']),expected_skill_sha256=job['skill_sha256'],
                condition_skill_present=job.get('condition_skill_present',True),
                codex_bin=Path(config['codex_bin']),verus_bin=Path(config['verus_bin']),
                lynette_bin=Path(config['lynette_bin']),bridge_url=url,bridge_ledger_path=settings.ledger_path,
                bridge_manifest_path=manifest,bridge_task_key=job['key'],model='deepseek-v4-pro',
                reasoning_effort='max',timeout_seconds=600,model_context_window=1048576,
                run_stage='trace_experience_'+job['arm'],reference_proof_source=None,reference_kind='none',
                actor_isolation_scratch_root=Path(config['scratch_root']),
                actor_isolation_verus_root=Path(config['verus_bin']).parent,
                actor_isolation_rust_root=Path(config['source_root'])/'toolchain',
                actor_isolation_forbidden_paths=(REPO,Path(os.environ['VERUS_SKILL_DATA_ROOT']),
                    Path(config['source_root'])/'rollout',backend/'runtime.json',backend/'inputs',
                    backend/'attempts',backend.parent/'deepscientist'),
                installed_library_root=Path(config['verus_bin']).parent/'vstd')
            print(json.dumps({'phase':'actor_end','key':job['key'],'proof_solved':row['proof_solved'],
                              'within_budget':row['within_budget'],'provider_valid':row['provider_valid']}),flush=True)
            return {'job':job,'row':row}
        # Submit only two at a time; do not dispatch queued work after infrastructure failure.
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = {}
            iterator = iter(jobs)
            for _ in range(min(2,len(jobs))):
                job = next(iterator)
                pending[pool.submit(episode,job)] = job
            while pending:
                future = next(as_completed(pending))
                job = pending.pop(future)
                try:
                    result = future.result()
                    rows.append(result)
                    if not result['row']['provider_valid'] or result['row']['fidelity']=='V0_INVALID':
                        failures.append({'key':job['key'],'reason':'invalid_provider_or_trace'})
                except Exception as error:
                    failures.append({'key':job['key'],'reason':type(error).__name__+': '+str(error)})
                write_json(root/'progress.json',{'completed':len(rows),'scheduled':len(jobs),'failures':failures})
                if not failures and not settings.halted_error:
                    following = next(iterator,None)
                    if following:
                        pending[pool.submit(episode,following)] = following
    for result in rows:
        row = result['row']
        result['settled_usage'] = _bridge_usage(settings.ledger_path,row['bridge_task_key'],'deepseek-v4-pro')
        result['budgeted_success'] = bool(row['proof_solved'] and row['within_budget'] and row['provider_valid'])
    summary = {'rows':rows,'failures':failures,'scheduled':len(jobs),'completed':len(rows),
               'complete':len(rows)==len(jobs) and not failures,'bridge_drained':True,
               'accounting':'Provider ledger estimates, not settled invoice charges',
               'clock':'600s actor process; frozen read-only final grading after stop, no post-deadline edits; timeouts are non-success'}
    write_json(root/'summary.json',summary)
    if not summary['complete']:
        raise RuntimeError('Incomplete or invalid actor batch; see preserved summary')


def analyze(request, root, runtime, guard):
    backend = root.parents[1]
    receipts = list((backend/'batches').glob('*/analyzer_admission.json'))
    used_input = sum(json.loads(p.read_text())['input_bytes'] for p in receipts)
    used_output = sum(json.loads(p.read_text())['output_cap'] for p in receipts)
    system, user = request['system'], request['user']
    size = len((system+user).encode())
    cap = int(request.get('output_cap',8192))
    if (len(receipts)>=runtime['analyzer_call_limit'] or size+used_input>runtime['analyzer_input_byte_limit']
            or cap<=0 or cap+used_output>runtime['analyzer_output_limit']):
        raise ValueError('Analyzer phase ceiling exceeded')
    write_json(root/'analyzer_admission.json',{'input_bytes':size,'output_cap':cap})
    client = GuardedDeepSeek(root=root/'responses',api_key=credential(),guards=[guard],
                             ledger=root/'provider_calls.jsonl',output_cap=cap)
    text, usage = client.call(system=system,user=user,name='extraction',cap=cap,effort='high')
    write_json(root/'summary.json',{'text':text,'usage':usage,'model':'deepseek-v4-pro'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',type=Path,required=True)
    parser.add_argument('--request',type=Path,required=True)
    args = parser.parse_args()
    backend = args.backend.resolve()
    runtime = json.loads((backend/'runtime.json').read_text())
    request = json.loads(args.request.read_text())
    name = request['batch_id']
    if Path(name).name!=name:
        raise ValueError('Unsafe batch ID')
    root = backend/'batches'/name
    root.mkdir(parents=True,exist_ok=False)
    write_json(root/'request.json',request)
    write_json(root/'adapter_receipt.json',{'adapter_sha256':sha(__file__),
                                          'packet_manifest_sha256':runtime['packet_manifest_sha256']})
    guard = SharedBudgetGuard(backend/'phase_budget.json',approval_limit_usd=runtime['phase_limit_usd'],
                              prior_spend_usd=0,optimizer_reserve_usd=0,request_reserve_usd=0)
    try:
        {'actors':actors,'analyze':analyze}[request['kind']](request,root,runtime,guard)
    except Exception as error:
        write_json(root/'error.json',{'type':type(error).__name__,'message':str(error)})
        raise
    print(json.dumps({'phase':'complete','batch_id':name,'summary':str(root/'summary.json')}),flush=True)


if __name__=='__main__':
    main()
