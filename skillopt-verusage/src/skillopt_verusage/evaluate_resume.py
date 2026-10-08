"""Resume the audited fixed160 evaluation without rerunning learning."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import traceback

from skillopt_verusage.augmentation_campaign import Campaign, CONDITIONS, require_design_review
from skillopt_verusage.budget_guard import estimate_deepseek_cost
from skillopt_verusage.campaign_evidence import sha
from skillopt_verusage.card_bank import audit_retrieval
from skillopt_verusage.codex_flash_runner import _bridge_usage, _codex_terminal
from skillopt_verusage.evaluation_recovery import audit_parent
from skillopt_verusage.guarded_deepseek import write_json
from skillopt_verusage.skill_artifact import load_skill_artifact
from skillopt_verusage.skill_validation import aggregate


def records(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []


def job_key(job):
    repeat, condition, item = job
    return f'val_r{repeat+1}_{condition}--{item["id"]}'


def episode_path(root, job):
    repeat, condition, item = job
    return root/'validation'/f'repeat_{repeat+1}'/condition/item['id']


def copy_episode(source, target):
    if target.exists():
        raise ValueError('Refusing to overwrite a selected evaluation episode')
    files = list(source.rglob('*'))
    if any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in files):
        raise ValueError('Unsafe evaluation episode file')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    for p in files:
        if p.is_file() and sha(p) != sha(target/p.relative_to(source)):
            raise ValueError('Evaluation episode copy changed bytes')


def transport_retryable(row, directory, wave_records):
    """Require a real bridge IncompleteRead and its matching failed Codex terminal."""
    if (row.get('fidelity') != 'V0_INVALID' or row.get('codex_returncode') != 1
            or row.get('actor_model') != 'deepseek-v4-pro' or row.get('actor_reasoning_effort') != 'max'):
        return False
    faults = [r for r in wave_records if any(str(a.get('error','')).startswith('IncompleteRead:')
                                           for a in r.get('attempts',[]))]
    if not faults or row.get('codex_terminal',{}).get('failed') != 1:
        return False
    key = row['bridge_task_key']
    for event in records(directory/'codex_events.raw.jsonl'):
        message = event.get('error',{}).get('message','') if event.get('type') == 'turn.failed' else ''
        if (f'/tasks/{key}/v1/responses' in message and '409 Conflict' in message
                and 'IncompleteRead:' in message):
            return True
    return False


def admit_settled(row, directory, ledger, job, artifact):
    """Do not replay valid failures/timeouts or accept late unmetered provider faults."""
    item = job[2]; key = job_key(job)
    manifest = json.loads((directory/'run_manifest.json').read_text())
    validation = json.loads((directory/'validation.json').read_text())
    fidelity = json.loads((directory/'fidelity_audit.json').read_text())
    usage = _bridge_usage(ledger,key,'deepseek-v4-pro')
    selected = [r for r in records(ledger) if r.get('task_id') == key]
    if (row.get('fidelity') not in ('V1_TRUNCATED','V2_TRACE') or row.get('bridge_task_key') != key
            or row.get('actor_model') != 'deepseek-v4-pro' or row.get('actor_reasoning_effort') != 'max'
            or row.get('provider_valid') is not True
            or row.get('source_sha256') != item['source_sha256']
            or sha(directory/'workspace/input.rs') != item['source_sha256']
            or row.get('skill_sha256') != artifact['artifact_sha256']
            or manifest.get('model') != 'deepseek-v4-pro' or manifest.get('reasoning_effort') != 'max'
            or manifest.get('timeout_seconds') != 600 or manifest.get('bridge',{}).get('task_key') != key
            or row.get('validation') != validation or validation.get('input_unchanged') is not True
            or validation.get('skill_unchanged') is not True
            or validation.get('candidate_sha256') != sha(directory/'workspace/candidate.rs')
            or _codex_terminal(directory/'codex_events.raw.jsonl') != row.get('codex_terminal')
            or (row['fidelity']=='V1_TRUNCATED' and not row.get('timed_out'))
            or (row['fidelity']=='V2_TRACE' and (row.get('timed_out') or row.get('codex_returncode') != 0 or fidelity.get('f3') is not True
                or row['codex_terminal']['completed'] != 1 or row['codex_terminal']['failed']))
            or row.get('within_budget') != (not row.get('timed_out'))
            or not selected or usage['requests'] != usage['metered_requests']
            or usage['completed_requests'] < 1 or usage['error_requests'] or usage['unknown_cost_requests']
            or usage['completed_requests']+usage['incomplete_requests'] != usage['requests']
            or usage['upstream_models'] != ['deepseek-v4-pro']
            or any(a.get('estimated_cost_usd') is None for r in selected for a in r.get('attempts',[]))):
        raise ValueError('Settled episode evidence invalid; preserve without performance replay: '+key)
    for file in artifact['files']:
        relative = file['relative_path'] if artifact['source_kind']=='directory' else 'SKILL.md'
        if sha(directory/'workspace'/relative) != file['sha256']:
            raise ValueError('Deployed evaluation skill changed')


class EvaluationResume(Campaign):
    def __init__(self, config):
        require_design_review(config)
        self.config = config
        self.repo = Path(config['repo']).resolve()
        self.source_root = Path(config['source_root']).resolve()
        self.root = Path(config['run_root']).resolve()
        approved = Path(os.environ['VERUS_SKILL_RUN_ROOT']).resolve()
        if approved not in self.root.parents or self.repo in self.root.parents:
            raise ValueError('Evaluation recovery requires an external approved run child')
        if (self.root/'started.json').exists():
            raise ValueError('Previously started recovery requires a separate audit')
        self.parent = Path(config['evaluation_recovery_parent']).resolve()
        if approved not in self.parent.parents or self.parent == self.root:
            raise ValueError('Invalid evaluation recovery parent')
        parent_config = json.loads((self.parent/'config.json').read_text())
        for name in ('repo','source_root','codex_bin','verus_bin','lynette_bin','scratch_root',
                     'execution_review','deferred_sources'):
            if config.get(name) != parent_config.get(name):
                raise ValueError('Evaluation recovery changed a frozen runtime setting: '+name)
        self.receipt = audit_parent(self.parent)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.progress = {'phase':'recovery_audited','evaluation_completed':60,'hint_completed':114,
                         'actor_workers':8,'test_accessed':False}
        self.rows = list(self.receipt['rows'])
        self.sources = {}
        self.physical_sources = []
        self.ledger = self.root/'provider_calls.jsonl'

    def prepare(self):
        for name in ('frozen_artifacts.json','artifact_quality_evidence.json','artifact_review.json',
                     'evaluation_schedule.json'):
            shutil.copyfile(self.parent/name,self.root/name)
        for condition in ('original_only','augmented'):
            target = self.root/'banks'/condition/'cards.json'
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(self.parent/'banks'/condition/'cards.json',target)
        write_json(self.root/'recovered_evaluation.json',self.receipt)
        for key, relative in self.receipt['result_directories'].items():
            source = self.parent/relative
            target = self.root/relative
            copy_episode(source,target)
            self.sources[key] = {'ledger_path':str(self.parent/'provider_calls.jsonl'),
                'ledger_sha256':self.receipt['ledger_sha256'],'result_path':str(source/'result.json'),
                'result_sha256':sha(target/'result.json')}
        self.frozen = json.loads((self.root/'frozen_artifacts.json').read_text())
        self.artifacts = {c:Path(m['path']) for c,m in self.frozen.items()}
        self.jobs = [tuple(job) for block in json.loads((self.root/'evaluation_schedule.json').read_text())['blocks']
                     for job in block]
        for job in self.jobs:
            item = job[2]
            source = Path(item['runtime_source'])
            relative = source.relative_to(self.parent)
            target = self.root/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():
                shutil.copyfile(source,target)
            if sha(target) != item['source_sha256']:
                raise ValueError('Recovery original validation input changed')
            item['runtime_source'] = str(target)
        self.persist()
        self.update(phase='recovery_ready',evaluation_remaining=100)

    def persist(self):
        write_json(self.root/'validation_rows.json',self.rows)
        write_json(self.root/'evaluation_episode_sources.json',self.sources)
        write_json(self.root/'physical_ledger_sources.json',self.physical_sources)
        physical = []
        for entry in self.physical_sources:
            path = Path(entry['ledger_path'])
            if sha(path) != entry['ledger_sha256']:
                raise ValueError('Immutable physical evaluation ledger changed')
            physical.extend(records(path))
        if len({r['request_id'] for r in physical}) != len(physical):
            raise ValueError('Duplicate physical evaluation request')
        self.write_ledger(self.root/'provider_calls.jsonl',physical)
        selected = []
        for path in dict.fromkeys(s['ledger_path'] for s in self.sources.values()):
            selected.extend(r for r in records(Path(path)) if r.get('task_id') in self.sources
                            and self.sources[r['task_id']]['ledger_path'] == path)
        if len({r['request_id'] for r in selected}) != len(selected):
            raise ValueError('Duplicate selected evaluation request')
        self.write_ledger(self.root/'selected_episode_ledger.jsonl',selected)
        parent_cost = json.loads((self.parent/'cost_summary.json').read_text())
        parent_known = parent_cost['recovery_parent_physical_cost_usd'] + sum(
            float(a['estimated_cost_usd']) for r in records(self.parent/'provider_calls.jsonl')
            for a in r.get('attempts',[]) if a.get('estimated_cost_usd') is not None)
        known = sum(float(a['estimated_cost_usd']) for r in physical for a in r.get('attempts',[])
                    if a.get('estimated_cost_usd') is not None)
        upper = estimate_deepseek_cost({'prompt_cache_miss_tokens':1048576,'completion_tokens':131072},
                                      'deepseek-v4-pro',price_band='peak')
        unknown = [{'request_id':r['request_id'],'unknown_expense_upper_usd':upper,'fee_status':'unresolved_not_zero'}
                   for r in physical if any(a.get('estimated_cost_usd') is None for a in r.get('attempts',[]))]
        historical = parent_cost['approved_historical_unknown_requests']+[self.receipt['unknown_expense']]
        write_json(self.root/'cost_summary.json',{'expense_policy':'record_only','invoice_final':False,
            'estimated_new_cost_usd':known,'recovery_parent_physical_cost_usd':parent_known,
            'estimated_campaign_cost_including_parent_usd':parent_known+known,
            'approved_historical_unknown_requests':historical,
            'approved_historical_unknown_expense_upper_usd':sum(x['unknown_expense_upper_usd'] for x in historical),
            'unknown_cost_requests':len(unknown),'unresolved_new_requests':unknown,
            'new_unknown_expense_upper_usd':sum(x['unknown_expense_upper_usd'] for x in unknown),
            'source40_acquisition_included':False,
            'caveat':'All physical attempts counted once. Unknown bounds are not settled fees or zero. Selected episode ledger is a metric projection, not another invoice.'})

    @staticmethod
    def write_ledger(path, rows):
        path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))

    def run_episode(self, job, bridge, wave):
        repeat,condition,item = job
        load_skill_artifact(self.artifacts[condition],self.frozen[condition]['artifact_sha256'])
        target = episode_path(wave,job)
        row = self.actor(item,bridge,self.artifacts[condition],target,600,f'val_r{repeat+1}_{condition}')
        write_json(target/'retrieval_audit.json',audit_retrieval(target/'codex_events.raw.jsonl'))
        return row

    def run(self):
        pending = [job for job in self.jobs if job_key(job) not in self.sources]
        attempts = {job_key(job):int(job_key(job) in self.receipt['invalid_keys']) for job in pending}
        wave_number = 0
        while pending:
            wave = self.root/'evaluation_attempts'/f'wave-{wave_number:03d}'
            wave.mkdir(parents=True)
            jobs, pending = pending[:8],pending[8:]
            self.ledger = wave/'provider_calls.jsonl'
            self.ledger.touch(exist_ok=False)
            write_json(wave/'jobs.json',[{'key':job_key(j),'attempt':attempts[job_key(j)]} for j in jobs])
            self.update(phase='validation',active_wave=wave_number,evaluation_remaining=160-len(self.rows))
            errors = {}
            with self.bridge(str(wave.relative_to(self.root)/'bridge'),[]) as bridge:
                with ThreadPoolExecutor(max_workers=8) as pool:
                    futures = {pool.submit(self.run_episode,j,bridge,wave):j for j in jobs}
                    for future in as_completed(futures):
                        job = futures[future]
                        try:
                            future.result()
                        except Exception as exc:
                            errors[job_key(job)] = {'type':type(exc).__name__,'error':str(exc)}
                        self.update(wave_finished=len([f for f in futures if f.done()]),
                                    wave_dispatched=len(jobs))
            # No source ledger hash is frozen until all upstream requests drain.
            self.physical_sources.append({'ledger_path':str(self.ledger),'ledger_sha256':sha(self.ledger)})
            settled = records(self.ledger)
            retries, fatal = [],[]
            for job in jobs:
                key = job_key(job); directory = episode_path(wave,job)
                if not (directory/'result.json').exists():
                    fatal.append({'key':key,**errors.get(key,{'error':'Missing saved result'})})
                    continue
                row = json.loads((directory/'result.json').read_text())
                if row.get('fidelity') == 'V0_INVALID':
                    if transport_retryable(row,directory,settled) and attempts[key] < 2:
                        attempts[key] += 1
                        retries.append(job)
                    else:
                        fatal.append({'key':key,'error':'Non-retryable or exhausted invalid episode',
                                      'attempt':attempts[key],**errors.get(key,{})})
                    continue
                try:
                    if key in errors:
                        raise RuntimeError('Valid result followed by runner error: '+str(errors[key]))
                    admit_settled(row,directory,self.ledger,job,self.frozen[job[1]])
                    target = episode_path(self.root,job)
                    copy_episode(directory,target)
                    self.sources[key] = {'ledger_path':str(self.ledger),'ledger_sha256':sha(self.ledger),
                        'result_path':str(directory/'result.json'),'result_sha256':sha(target/'result.json')}
                    self.rows.append({**row,'condition':job[1],'repetition':job[0]+1})
                except Exception as exc:
                    fatal.append({'key':key,'error':str(exc)})
            write_json(wave/'disposition.json',{'errors':errors,'retry_keys':[job_key(j) for j in retries],
                       'fatal':fatal,'bridge_drained':True,'ledger_sha256':sha(self.ledger)})
            self.persist()
            self.update(evaluation_completed=len(self.rows),transport_retry_episodes=sum(attempts.values())-4)
            if fatal:
                raise RuntimeError('Evaluation technical incident preserved: '+json.dumps(fatal))
            pending = retries+pending
            wave_number += 1
        if len(self.rows) != 160 or len(self.sources) != 160:
            raise RuntimeError('Full evaluation coverage incomplete')
        self.ledger = self.root/'provider_calls.jsonl'
        write_json(self.root/'validation_summary.json',aggregate(self.rows,CONDITIONS))
        self.update(phase='complete',evaluation_completed=160,test_accessed=False)
        subprocess.run([self.config['python_bin'],str(self.repo/'scripts/summarize_hindsight_campaign.py'),
                        '--run-root',str(self.root)],check=True,cwd=self.repo)
        self.update(report_complete=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--prepare-only',action='store_true')
    args = parser.parse_args()
    campaign = EvaluationResume(json.loads(args.config.read_text()))
    try:
        campaign.prepare()
        if args.prepare_only:
            return
        code_paths = [campaign.repo/'scripts/summarize_hindsight_campaign.py']
        for relative in ('src','skillopt-verusage/src','skill-evolution-pilot/src','skillopt-verusage/SkillOpt'):
            code_paths.extend((campaign.repo/relative).rglob('*.py'))
        write_json(campaign.root/'production_snapshot.json',{
            str(p.relative_to(campaign.repo)):sha(p) for p in code_paths if p.is_file()})
        write_json(campaign.root/'started.json',{'pid':os.getpid(),'config_sha256':sha(args.config),
                   'command':['python','-m','skillopt_verusage.evaluate_resume','--config',str(args.config)],
                   'production_snapshot_sha256':sha(campaign.root/'production_snapshot.json'),
                   'started_at_utc':datetime.now(timezone.utc).isoformat()})
        campaign.run()
    except BaseException as exc:
        campaign.update(phase='stopped',error_type=type(exc).__name__,error=str(exc))
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
