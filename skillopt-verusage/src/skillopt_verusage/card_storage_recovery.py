"""Narrow recovery of saved card replies after the reviewed storage failure."""
import hashlib
import json
import math
from pathlib import Path

from skillopt_verusage.budget_guard import estimate_deepseek_cost
from skillopt_verusage.campaign_evidence import expand_strings, sha
from skillopt_verusage.codex_deepseek_bridge import _native_response_usage
from skillopt_verusage.guarded_deepseek import response_text
from skillopt_verusage.native_card_update import SYSTEM, audit_response


UNKNOWN_LOCAL_HASH = '2491c1eb07a19509895d3d600fe260d97a118f7d76b72deddaa5971003433acf'
KNOWN_MISSING_ID = 'be5eb5af99914cfbbee2512973cd126a'
STORAGE_PATTERNS = ('augmentation/*/*/result.json', 'hints/*/*/hint.json',
    'artifacts/native/**/*', 'calls/native/**/*', 'calls/native_finalization/**/*',
    'calls/original_only/**/*', 'calls/augmented/**/*',
    'banks/original_only_remaining/proposals/*.json', 'banks/augmented_remaining/proposals/*.json',
    'recovered_card_requests.json', 'banks/*_smoke/proposals/*.json',
    'banks/original_only/*', 'artifacts/original_only/**/*', 'original_only_independent_review.json',
    'artifacts/initial.md')


def audit(parent, records, audit_ancestor):
    parent = Path(parent)
    review_path = parent/'storage_repair_review.json'
    review = json.loads(review_path.read_text())
    incident = json.loads((parent/'storage_incident.json').read_text())
    if (review.get('repair_authorized') is not True
            or review.get('classification') != 'full_card_storage_repair'
            or review.get('user_authorization') != '现在有空间了，请你继续跑'
            or review.get('incident_sha256') != sha(parent/'storage_incident.json')
            or review.get('ledger_sha256') != sha(parent/'provider_calls.jsonl')
            or review.get('progress_sha256') != sha(parent/'progress.json')
            or review.get('log_sha256') != sha(parent/'campaign.log')
            or incident.get('provider_ledger_sha256') != review['ledger_sha256']
            or incident.get('progress_sha256') != review['progress_sha256']
            or incident.get('campaign_log_sha256') != review['log_sha256']
            or incident.get('phase') != 'stopped_storage_failure_requires_new_fee_authority'
            or incident.get('paid_process_running') is not False
            or incident.get('process_exit_code') != 1
            or incident.get('progress_file_is_stale') is not True
            or incident.get('completed_forks') != 114 or incident.get('known_new_requests') != 7
            or incident.get('complete_original_card_batches') != 19
            or incident.get('complete_augmented_remaining_batches') != 4
            or incident.get('frozen_artifacts_created') is not False
            or incident.get('validation_started') is not False or incident.get('sealed_test_accessed') is not False
            or Path('/proc',str(incident.get('pid'))).exists()
            or len(records) != 7
            or any(a.get('estimated_cost_usd') is None for row in records for a in row.get('attempts',[]))):
        raise ValueError('Storage recovery requires the reviewed exited process and unchanged fee evidence')
    paths = [p for pattern in STORAGE_PATTERNS for p in parent.glob(pattern)]
    actual = {str(p.relative_to(parent)):sha(p) for p in paths if p.is_file()}
    if (any(p.is_symlink() for p in paths) or actual != review.get('preserved_hashes')
            or any(p not in actual or actual[p] != h for p,h in incident.get('preserved_hashes',{}).items())
            or len(list(parent.glob(STORAGE_PATTERNS[0]))) != 114
            or len(list(parent.glob(STORAGE_PATTERNS[1]))) != 114
            or any((parent/p).exists() for p in ('frozen_artifacts.json','val_inputs','validation'))):
        raise ValueError('Storage recovery evidence changed or reached downstream outputs')
    ancestor = Path(json.loads((parent/'config.json').read_text())['reused_hint_root'])
    ancestral_records = [json.loads(s) for s in (ancestor/'provider_calls.jsonl').read_text().splitlines() if s.strip()]
    ancestral = audit_ancestor(ancestor,ancestral_records)
    if json.loads((parent/'recovered_card_requests.json').read_text()) != ancestral:
        raise ValueError('Storage recovery inherited ownership receipt changed')
    inherited = {e['request_relative_path'] for e in ancestral['replay_requests']}
    for label in ('native','native_finalization'):
        if ({str(p.relative_to(parent)):sha(p) for p in (parent/'calls'/label).rglob('*') if p.is_file()}
                != {str(p.relative_to(ancestor)):sha(p) for p in (ancestor/'calls'/label).rglob('*') if p.is_file()}):
            raise ValueError('Storage recovery native paid caches changed')
    native_sha = sha(parent/'artifacts/native/SKILL.md')
    learning = json.loads((parent/'artifacts/native/learning.json').read_text())
    if native_sha != ancestral['native_candidate_sha256'] or learning.get('source_count') != 38 or learning.get('audit') != []:
        raise ValueError('Storage recovery native skill changed')
    used, replay = set(), []
    missing_known = incident.get('known_missing_response',{})
    unknown = incident.get('new_unresolved_cost',{})
    if (missing_known.get('task') != 'card-batch-004' or missing_known.get('request_id') != KNOWN_MISSING_ID
            or missing_known.get('response_saved') is not False
            or unknown.get('task') != 'card-batch-005' or unknown.get('local_request_sha256') != UNKNOWN_LOCAL_HASH
            or unknown.get('dispatch_status') != 'unresolved_possibly_dispatched'
            or unknown.get('server_or_internal_request_id') is not None):
        raise ValueError('Storage recovery cannot broaden the missing response exception')
    for label,count in (('original_only',18),('augmented',6)):
        requests = sorted(parent.glob(f'calls/{label}/card-batch-*/*/request.json'))
        if (len(requests) != count or set(requests) != set(parent.glob(f'calls/{label}/**/request.json'))
                or {p.parent.parent.name for p in requests} != {f'card-batch-{n:03d}' for n in range(count)}):
            raise ValueError('Storage recovery request set is incomplete or unexpected')
        for request in requests:
            directory = request.parent; name = directory.parent.name
            relative = str(request.relative_to(parent)); payload = json.loads(request.read_text())
            serialized = json.dumps(payload,ensure_ascii=False).encode()
            fingerprint = hashlib.sha256(serialized).hexdigest()
            if (directory.name != fingerprint
                    or json.loads((directory/'started.json').read_text()).get('request_sha256') != fingerprint
                    or payload.get('model') != 'deepseek-v4-pro' or payload.get('reasoning') != {'effort':'high'}
                    or payload.get('instructions') != SYSTEM or payload.get('max_output_tokens') != 16384
                    or payload.get('text') != {'format':{'type':'json_object'}} or payload.get('stream') is not False):
                raise ValueError('Storage recovery request contract changed')
            groups = expand_strings(json.loads(payload['input'][0]['content'][0]['text']))['task_groups']
            if len(groups) != 2 or any(len(g['trace_ids']) != (1 if label=='original_only' else 4) for g in groups):
                raise ValueError('Storage recovery group cardinality changed')
            proposal = parent/f'banks/{label}_remaining/proposals/batch-{name[-3:]}.json'
            if label == 'augmented' and name in ('card-batch-004','card-batch-005'):
                if (set(p.name for p in directory.iterdir()) != {'request.json','started.json','context_admission.json'}
                        or proposal.exists() or relative in inherited):
                    raise ValueError('Storage recovery cannot replay absent or altered replies')
                if name == 'card-batch-004':
                    matches = [r for r in records if r.get('request_id') == KNOWN_MISSING_ID]
                    if (len(matches) != 1 or matches[0].get('task_id') != name
                            or matches[0].get('model') != 'deepseek-v4-pro'
                            or len(matches[0].get('attempts',[])) != 1
                            or matches[0]['attempts'][0].get('finish_reason') != 'completed'
                            or matches[0]['attempts'][0].get('error')
                            or matches[0]['attempts'][0].get('max_tokens') != 16384
                            or not matches[0]['attempts'][0].get('usage')
                            or matches[0]['attempts'][0].get('estimated_cost_usd') != missing_known.get('estimated_cost_usd')):
                        raise ValueError('Storage recovery lost-response fee ownership changed')
                    used.add(KNOWN_MISSING_ID)
                else:
                    bound = estimate_deepseek_cost({'prompt_cache_miss_tokens':len(serialized)+8192,
                        'completion_tokens':16384},'deepseek-v4-pro',price_band='peak')
                    if (fingerprint != UNKNOWN_LOCAL_HASH or unknown.get('canonical_http_bytes') != len(serialized)
                            or unknown.get('conservative_byte_framing_reserve') != 8192 or unknown.get('output_cap') != 16384
                            or not math.isclose(unknown.get('peak_uncached_expense_upper_usd',0),bound,abs_tol=1e-12)
                            or any(r.get('task_id') == name for r in records)):
                        raise ValueError('Storage recovery must retain the exact missing-ledger expense exposure')
                continue
            stored = json.loads((directory/'validated.json').read_text())
            record = stored['record']; attempts = record.get('attempts',[])
            raw = (directory/'response.raw').read_bytes(); usage,model,status = _native_response_usage(raw)
            if relative in inherited:
                if ({p.name:sha(p) for p in directory.iterdir() if p.is_file()}
                        != {p.name:sha(p) for p in (ancestor/relative).parent.iterdir() if p.is_file()}
                        or any(r.get('request_id') == record.get('request_id') for r in records)):
                    raise ValueError('Storage recovery inherited card cache changed ownership or bytes')
            else:
                matches = [r for r in records if r.get('request_id') == record.get('request_id')]
                if len(matches) != 1 or matches[0] != record or record['request_id'] in used:
                    raise ValueError('Storage recovery card cache lacks exact metered ownership')
                used.add(record['request_id'])
            if (record.get('model') != model or model != 'deepseek-v4-pro' or status != 'completed'
                    or record.get('task_id') != name or len(attempts) != 1
                    or attempts[0].get('finish_reason') != 'completed' or attempts[0].get('error')
                    or attempts[0].get('estimated_cost_usd') is None or attempts[0].get('max_tokens') != 16384
                    or usage != stored.get('usage') or usage != attempts[0].get('usage')
                    or response_text(raw) != stored['text'] or (directory/'error.json').exists()):
                raise ValueError('Storage recovery paid raw response or usage changed')
            response = json.loads(stored['text']); audit_response(response,groups)
            if not proposal.is_file() or json.loads(proposal.read_text()) != response:
                raise ValueError('Storage recovery cannot alter accepted proposals')
            replay.append({'label':label,'name':name,'request_relative_path':relative})
    if (used != {r['request_id'] for r in records} or len(replay) != 22
            or len(list(parent.glob(STORAGE_PATTERNS[7]))) != 18 or len(list(parent.glob(STORAGE_PATTERNS[8]))) != 4):
        raise ValueError('Storage recovery cannot omit settled calls or valid proposals')
    return {'source_run':str(parent),'review_sha256':sha(review_path),'ledger_sha256':review['ledger_sha256'],
        'native_candidate_sha256':native_sha,'replay_requests':replay,'rejected_card_response_preserved':True,
        'approved_missing_ledger_unknown':{'source_run':str(parent),'request_id':None,
            'local_request_sha256':UNKNOWN_LOCAL_HASH,'unknown_expense_upper_usd':unknown['peak_uncached_expense_upper_usd'],
            'review_sha256':sha(review_path),'fee_status':'unresolved_not_zero'}}
