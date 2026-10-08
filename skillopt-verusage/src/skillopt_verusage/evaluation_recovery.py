"""Read-only admission of the one interrupted fixed-160 evaluation campaign."""
import hashlib
import json
import math
from pathlib import Path

from skillopt_verusage.budget_guard import estimate_deepseek_cost
from skillopt_verusage.campaign_evidence import sha
from skillopt_verusage.codex_deepseek_bridge import _sha256_json
from skillopt_verusage.codex_flash_runner import _bridge_usage, _codex_terminal
from skillopt_verusage.skill_artifact import load_skill_artifact


CONDITIONS = ('initial','native','original_only','augmented')
FAILED_ID = '08d1a2c2d3839f127970'
FAILED_REQUEST = '75478abf7fbe46ebbc0b6eb225728de8'
TOP_FILES = ('artifact_quality_evidence.json','artifact_review.json',
    'audits/retrieval_case_studies.json','campaign.log','cost_summary.json',
    'evaluation_schedule.json','frozen_artifacts.json','progress.json','provider_calls.jsonl',
    'validation_rows.json')
EPISODE_FILES = ('result.json','run_manifest.json','fidelity_audit.json','validation.json',
    'codex_events.raw.jsonl','retrieval_audit.json')


def audit_parent(parent):
    parent = Path(parent).resolve()
    review_path = parent/'audits/evaluation_transport_incident_review.json'
    review = json.loads(review_path.read_text())
    progress = json.loads((parent/'progress.json').read_text())
    pid = review.get('process_pid')
    if (review.get('schema_version') != 'evaluation-transport-incident-review-v1'
            or review.get('status') != 'stopped_partial_not_160_complete'
            or review.get('paid_process_running') is not False or not isinstance(pid,int)
            or Path('/proc',str(pid)).exists()
            or progress.get('phase') != 'stopped' or progress.get('error_type') != 'RuntimeError'
            or progress.get('error') != review.get('root_error')
            or progress.get('error') != f'Actor/provider invalid, preserve and stop: val_r1_original_only--{FAILED_ID}'
            or progress.get('evaluation_completed') != 56
            or review.get('reported_evaluation_rows') != 56 or review.get('saved_result_count') != 64
            or review.get('valid_saved_actor_outcomes') != 60 or review.get('invalid_saved_results') != 4
            or review.get('request_id') != FAILED_REQUEST
            or review.get('failed_task_id') != f'val_r1_initial--{FAILED_ID}'
            or review.get('partial_response_accepted') is not False
            or review.get('partial_terminal_or_usage_present') is not False
            or review.get('no_sealed_test_access') is not True):
        raise ValueError('Evaluation recovery requires the exact stopped transport incident')
    paths = [parent/p for p in TOP_FILES]
    paths += list(parent.glob('validation/repeat_*/*/*/*'))
    paths = [p for p in paths if p.is_file() and (p.parent==parent or str(p.relative_to(parent)) in TOP_FILES
        or p.name in EPISODE_FILES)]
    paths += list((parent/'provider_failure_evidence'/FAILED_REQUEST).glob('*'))
    inventory = {str(p.relative_to(parent)):sha(p) for p in paths if p.is_file()}
    expected = review.get('preserved_hashes',{})
    if (len(inventory) != 393 or inventory != expected or any(p.is_symlink() for p in paths)
            or any(Path(p).is_absolute() or '..' in Path(p).parts for p in expected)):
        raise ValueError('Evaluation incident inventory changed or escaped the saved run')
    frozen = json.loads((parent/'frozen_artifacts.json').read_text())
    evidence = json.loads((parent/'artifact_quality_evidence.json').read_text())
    receipt = json.loads((parent/'artifact_review.json').read_text())
    if (set(frozen) != set(CONDITIONS)
            or evidence != {'frozen_artifacts_sha256':sha(parent/'frozen_artifacts.json'),
                'banks':{c:sha(parent/f'banks/{c}/cards.json') for c in ('original_only','augmented')}}
            or receipt.get('accepted') is not True or receipt.get('evidence_sha256') != _sha256_json(evidence)
            or not isinstance(receipt.get('observations'),str) or not receipt['observations'].strip()):
        raise ValueError('Evaluation recovery cannot change or bypass accepted artifacts')
    runtime_hashes = {}
    for condition,manifest in frozen.items():
        path = Path(manifest['path'])
        if parent not in path.resolve().parents or manifest != {'path':str(path),**load_skill_artifact(path).manifest()}:
            raise ValueError('Evaluation recovery frozen artifact changed or escaped the run')
        files = list(path.rglob('*')) if path.is_dir() else [path]
        runtime_hashes.update({str(p.relative_to(parent)):sha(p) for p in files if p.is_file()})
    schedule = json.loads((parent/'evaluation_schedule.json').read_text())
    blocks = schedule.get('blocks',[]); jobs = {}; items = {}
    if (schedule.get('test_accessed') is not False or len(blocks) != 2
            or [len(b) for b in blocks] != [80,80]
            or schedule.get('frozen_artifacts_sha256') != sha(parent/'frozen_artifacts.json')):
        raise ValueError('Evaluation recovery schedule changed')
    for repetition,block in enumerate(blocks,1):
        for repeat,condition,item in block:
            ident = item['id']; key = f'val_r{repetition}_{condition}--{ident}'
            if repeat != repetition-1 or condition not in CONDITIONS or key in jobs:
                raise ValueError('Evaluation recovery has duplicate or changed schedule slots')
            source = Path(item['runtime_source'])
            if parent/'val_inputs' not in source.resolve().parents or sha(source) != item['source_sha256']:
                raise ValueError('Evaluation runtime input changed or escaped val_inputs')
            if ident in items and items[ident] != item:
                raise ValueError('Evaluation source differs across repetitions or conditions')
            items[ident] = item; jobs[key] = (repetition,condition,item)
            runtime_hashes[str(source.relative_to(parent))] = sha(source)
    if len(jobs) != 160 or len(items) != 20 or FAILED_ID not in items:
        raise ValueError('Evaluation recovery must retain20 tasks and160 unique slots')
    ledger = parent/'provider_calls.jsonl'
    records = [json.loads(s) for s in ledger.read_text().splitlines() if s.strip()]
    if len({r['request_id'] for r in records}) != len(records):
        raise ValueError('Evaluation ledger has duplicate physical request IDs')
    unknown = [r for r in records if any(a.get('estimated_cost_usd') is None for a in r.get('attempts',[]))]
    if (len(unknown) != 1 or unknown[0]['request_id'] != FAILED_REQUEST
            or unknown[0]['task_id'] != f'val_r1_initial--{FAILED_ID}' or len(unknown[0].get('attempts',[])) != 1
            or unknown[0]['attempts'][0].get('usage') is not None
            or not str(unknown[0]['attempts'][0].get('error','')).startswith('IncompleteRead:')):
        raise ValueError('Evaluation recovery cannot hide or broaden unresolved usage')
    failure = parent/'provider_failure_evidence'/FAILED_REQUEST
    error = json.loads((failure/'error.json').read_text()); request = json.loads((failure/'request.json').read_text())
    partial = failure/'response.partial.raw'
    upper = estimate_deepseek_cost({'prompt_cache_miss_tokens':1048576,'completion_tokens':131072},
                                  'deepseek-v4-pro',price_band='peak')
    if (error.get('partial_response_accepted') is not False or error.get('partial_body_sha256') != sha(partial)
            or error.get('partial_body_bytes') != partial.stat().st_size
            or error.get('request_sha256') != hashlib.sha256(json.dumps(request,ensure_ascii=False).encode()).hexdigest()
            or request.get('model') != 'deepseek-v4-pro' or request.get('reasoning',{}).get('effort') != 'max'
            or request.get('max_output_tokens') != 131072
            or review.get('current_unresolved_requests') != 1
            or not math.isclose(review.get('current_unresolved_upper_usd',0),upper,abs_tol=1e-12)):
        raise ValueError('Evaluation unresolved transport evidence changed')
    result_files = sorted(parent.glob('validation/repeat_*/*/*/result.json'))
    if len(result_files) != 64:
        raise ValueError('Evaluation recovery saved result count changed')
    rows, invalid, directories, observed, saved_reviews = [], [], {}, {}, []
    for path in result_files:
        directory = path.parent; repeat,condition,ident = directory.parts[-3:]
        repetition = int(repeat.removeprefix('repeat_')); key = f'val_r{repetition}_{condition}--{ident}'
        if key not in jobs or key in observed:
            raise ValueError('Evaluation recovery found an unscheduled result')
        row = json.loads(path.read_text()); observed[key] = row
        manifest = json.loads((directory/'run_manifest.json').read_text())
        validation = json.loads((directory/'validation.json').read_text())
        fidelity = json.loads((directory/'fidelity_audit.json').read_text())
        item = jobs[key][2]; artifact = frozen[condition]
        if (row.get('id') != ident or row.get('bridge_task_key') != key
                or row.get('actor_model') != 'deepseek-v4-pro' or row.get('actor_reasoning_effort') != 'max'
                or manifest.get('model') != 'deepseek-v4-pro' or manifest.get('reasoning_effort') != 'max'
                or manifest.get('timeout_seconds') != 600 or manifest.get('bridge',{}).get('task_key') != key
                or row.get('source_sha256') != item['source_sha256'] or manifest.get('source_sha256') != item['source_sha256']
                or sha(directory/'workspace/input.rs') != item['source_sha256']
                or row.get('skill_sha256') != artifact['artifact_sha256']
                or manifest.get('condition_skill_sha256') != artifact['artifact_sha256']
                or row.get('skill_artifact') != {k:v for k,v in artifact.items() if k!='path'}
                or row.get('validation') != validation or validation.get('input_unchanged') is not True
                or validation.get('skill_unchanged') is not True
                or validation.get('candidate_sha256') != sha(directory/'workspace/candidate.rs')):
            raise ValueError('Evaluation episode input, skill, contract or final validation changed')
        deployed = directory/'workspace'
        for file in artifact['files']:
            relative = file['relative_path'] if artifact['source_kind']=='directory' else 'SKILL.md'
            if sha(deployed/relative) != file['sha256']:
                raise ValueError('Evaluation actor-visible skill files changed')
        terminal = _codex_terminal(directory/'codex_events.raw.jsonl')
        if terminal != row.get('codex_terminal'):
            raise ValueError('Evaluation saved terminal counts do not match the raw stream')
        saved_reviews.append({'path':str(directory.relative_to(parent)),**{k:row[k] for k in (
            'id','fidelity','provider_valid','codex_returncode','safety_passed','within_budget','bridge_task_key')}})
        if row.get('fidelity') == 'V0_INVALID':
            if ident != FAILED_ID or repetition != 1 or row.get('codex_returncode') != 1:
                raise ValueError('Evaluation recovery cannot retry other failed episodes')
            invalid.append(key)
        else:
            settled = _bridge_usage(ledger,key,'deepseek-v4-pro')
            if (row.get('fidelity') not in ('V1_TRUNCATED','V2_TRACE') or row.get('provider_valid') is not True
                    or row.get('safety_passed') is not True or fidelity.get('input_unchanged') is not True
                    or settled['requests'] < 1 or settled['requests'] != settled['metered_requests']
                    or settled['completed_requests'] < 1 or settled['error_requests'] or settled['unknown_cost_requests']
                    or settled['completed_requests']+settled['incomplete_requests'] != settled['requests']
                    or settled['upstream_models'] != ['deepseek-v4-pro']
                    or row.get('within_budget') != (not row.get('timed_out'))
                    or (row['fidelity']=='V1_TRUNCATED' and not row.get('timed_out'))
                    or (row['fidelity']=='V2_TRACE' and (row.get('timed_out') or row.get('codex_returncode') != 0
                        or terminal['completed'] != 1 or terminal['failed'] or fidelity.get('f3') is not True))):
                raise ValueError('Evaluation recovery cannot change a valid outcome or admit invalid provider evidence')
            rows.append({**row,'condition':condition,'repetition':repetition})
            directories[key] = str(directory.relative_to(parent))
        for file in directory.rglob('*'):
            if file.is_symlink():
                raise ValueError('Evaluation runtime evidence contains a symlink')
            if file.is_file() and str(file.relative_to(parent)) not in inventory:
                runtime_hashes[str(file.relative_to(parent))] = sha(file)
    expected_invalid = {f'val_r1_{c}--{FAILED_ID}' for c in CONDITIONS}
    aggregate = json.loads((parent/'validation_rows.json').read_text())
    if (len(rows) != 60 or set(invalid) != expected_invalid or saved_reviews != review.get('saved_results')
            or len(aggregate) != 56 or len({r['bridge_task_key'] for r in aggregate}) != 56
            or any(r != {**observed[r['bridge_task_key']],
                'condition':jobs[r['bridge_task_key']][1],'repetition':jobs[r['bridge_task_key']][0]} for r in aggregate)
            or any(r['bridge_task_key'] in expected_invalid for r in aggregate)
            or any(r['task_id'].startswith('val_') and r['task_id'] not in observed for r in records)):
        raise ValueError('Evaluation recovery cannot change the retained60 or broaden invalid retries')
    return {'source_run':str(parent),'review_sha256':sha(review_path),'ledger_sha256':sha(ledger),
        'schedule_sha256':sha(parent/'evaluation_schedule.json'),
        'frozen_artifacts_sha256':sha(parent/'frozen_artifacts.json'),'preserved_hashes':inventory,
        'runtime_hashes':runtime_hashes,'rows':rows,'invalid_keys':sorted(invalid),'result_directories':directories,
        'unknown_expense':{'source_run':str(parent),'request_id':FAILED_REQUEST,
            'unknown_expense_upper_usd':upper,'fee_status':'unresolved_not_zero'}}
