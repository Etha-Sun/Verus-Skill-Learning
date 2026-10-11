"""Run one bounded implementation -> paired pilot -> case-analysis cycle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(path)


def controller(root, run_id, skill, message):
    payload = {'run_id':run_id,'skill_id':skill,'runner':'codex','model':'gpt-6.1-sol',
               'model_reasoning_effort':'high','message':message}
    write(root/(run_id+'-request.json'),payload)
    request = urllib.request.Request('http://127.0.0.1:21001/api/quests/trace-experience-001/runs',
        data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request,timeout=10800) as response:
        result = json.load(response)
    write(root/(run_id+'-result.json'),result)
    if not result.get('ok'):
        raise RuntimeError('Controller failed: '+run_id)


def validate(root):
    quest = root/'deepscientist/quests/trace-experience-001'
    frozen = json.loads((quest/'PILOT_FROZEN.json').read_text())
    path = (quest/frozen['request_path']).resolve()
    if quest not in path.parents or sha(path)!=frozen['request_sha256']:
        raise ValueError('Pilot request missing or changed')
    contract = (quest/frozen['contract_path']).resolve()
    if quest not in contract.parents or sha(contract)!=frozen['contract_sha256']:
        raise ValueError('Pilot contract missing or changed')
    request = json.loads(path.read_text())
    runtime = json.loads((root/'backend/runtime.json').read_text())
    packet = quest/'userfiles/training_packet_v1'
    if sha(packet/'manifest.json')!=runtime['packet_manifest_sha256']:
        raise ValueError('Training manifest changed')
    manifest = json.loads((packet/'manifest.json').read_text())
    donors = {x['id'] for x in manifest['donors']}
    for donor in manifest['donors']:
        for name,digest in donor['files'].items():
            if sha(packet/'traces'/donor['id']/name)!=digest:
                raise ValueError('Training trace changed')
    ids = {x['id'] for x in runtime['probes']}
    expected = {(ident,arm) for ident in ids for arm in 'NGBA'}
    jobs = request['schedule']
    if (request['kind']!='actors' or request['batch_id']!='pilot-001' or len(jobs)!=32
            or {(x['id'],x['arm']) for x in jobs}!=expected):
        raise ValueError('Expected exactly eight frozen probes x four arms')
    for job in jobs:
        skill = Path(job['skill_file']).resolve()
        if quest not in skill.parents or sha(skill)!=job['skill_sha256'] or skill.stat().st_size>1024:
            raise ValueError('Invalid, oversized or changed auxiliary context')
        if job['arm']=='N' and (job.get('condition_skill_present',True) or skill.read_bytes()):
            raise ValueError('N must have no experience context')
        if job['arm'] in 'AB' and (not job.get('source_ids') or not set(job['source_ids'])<=donors):
            raise ValueError('Experience sources must be permitted donors')
    for ident in ids:
        pair = {x['arm']:x for x in jobs if x['id']==ident and x['arm'] in 'AB'}
        if pair['A']['source_ids']!=pair['B']['source_ids']:
            raise ValueError('A/B must expose the same source episodes')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--actor-python',required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    state_path = root/'campaign_state.json'
    if state_path.exists():
        raise RuntimeError('Campaign already dispatched; do not replay')
    state = {'status':'running','phase':'implementation','started_at':time.time(),
             'controller_model':'gpt-6.1-sol','actor_model':'deepseek-v4-pro',
             'actor_timeout_seconds':600,'pilot_episodes':32,'smoke_episodes':2,
             'method_phase_ceiling_usd':20.0,'controller_cost_separate':True}
    write(state_path,state)
    try:
        message = (root/'deepscientist/quests/trace-experience-001/userfiles/EXECUTION_HANDOFF.md').read_text()
        controller(root,'implementation-freeze-001','idea',message)
        request_path = validate(root)
        state.update(phase='waiting_smoke',implementation_completed_at=time.time(),request_sha256=sha(request_path))
        write(state_path,state)
        smoke = root/'backend/batches/smoke-001'
        deadline = time.monotonic()+2400
        while not (smoke/'summary.json').exists():
            if (smoke/'error.json').exists() or time.monotonic()>deadline:
                raise RuntimeError('Smoke failed or did not settle; no pilot dispatch')
            time.sleep(5)
        summary = json.loads((smoke/'summary.json').read_text())
        if not summary['complete'] or not summary['bridge_drained']:
            raise RuntimeError('Smoke not valid and settled; no pilot dispatch')
        state.update(phase='pilot_running',pilot_started_at=time.time())
        write(state_path,state)
        adapter = Path(__file__).with_name('evaluation_adapter.py')
        command = [args.actor_python,str(adapter),'--backend',str(root/'backend'),'--request',str(request_path)]
        with (root/'pilot.log').open('xb') as log:
            process = subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
            state['pilot_pid'] = process.pid
            write(state_path,state)
            result = process.wait()
        state.update(phase='analysis',pilot_exit_code=result,pilot_finished_at=time.time())
        write(state_path,state)
        analysis = '''The frozen pilot was executed by the parent adapter. Continue automatically through honest results and case-level interpretation; do not ask for another start authorization. Read the immutable frozen contract and the actual backend/batches/pilot-001/summary.json, progress/error files and provider ledger through the allowed backend. Analyze all scheduled tasks/arms including missing, invalid and timeout attempts; do not reduce denominators. Read raw actor events and code snapshots for gain, regression, persistent failure and common-success cost differences where those categories exist. Reconstruct access -> action -> verifier evidence with line/event hashes. Distinguish method failure, inconclusive evidence and infrastructure failure. Do not spend any further actor/analyzer calls or tune on probe outcomes. Record actual learning cost separately from actor costs, and controller telemetry separately. Report token overlap correctly, estimates versus invoice charges, exposed development status, collection bias and incomplete clone/dependency ancestry. Write PILOT_REPORT.md, CASE_STUDIES.md and NEXT_DECISION.md with supported/refuted/inconclusive claims and a justified next bounded research direction. Use baseline/experiment/artifact records as applicable to preserve the actual comparator and experiment; never invent missing metrics or force a main-evidence claim. If no trustworthy result exists, write an infrastructure incident instead of a performance narrative. Keep all outputs in the quest, leave raw inputs unchanged, and finish this full analysis pass.'''
        controller(root,'pilot-analysis-001','analysis-campaign',analysis)
        quest = root/'deepscientist/quests/trace-experience-001'
        if not all((quest/name).is_file() for name in ('PILOT_REPORT.md','CASE_STUDIES.md','NEXT_DECISION.md')):
            raise RuntimeError('Analysis report incomplete; see controller logs')
        state.update(status='completed' if result==0 else 'failed_analyzed',phase='cycle_complete',finished_at=time.time())
    except Exception as error:
        state.update(status='failed',error_type=type(error).__name__,error=str(error),finished_at=time.time())
    write(state_path,state)
    print(json.dumps(state),flush=True)


if __name__=='__main__':
    main()
