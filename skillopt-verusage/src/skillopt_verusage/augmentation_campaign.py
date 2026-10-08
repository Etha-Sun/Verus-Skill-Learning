"""One frozen train-only learning pass followed by four paired val conditions."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.server import ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import traceback

from skillopt_verusage.campaign_evidence import (evaluation_schedule, analyze_progress, load_trace,
                                               packet_trace, sha, shared_strings, expand_strings)
from skillopt_verusage.card_bank import build_bundle, audit_retrieval
from skillopt_verusage.codex_deepseek_bridge import BridgeConfig, make_handler, _sha256_json, _native_response_usage
from skillopt_verusage.codex_flash_runner import run_task
from skillopt_verusage.guarded_deepseek import BudgetMux, GuardedDeepSeek, response_text, write_json
from skillopt_verusage.budget_guard import estimate_deepseek_cost
from skillopt_verusage.skill_artifact import load_skill_artifact
from skillopt_verusage.skill_validation import aggregate
from skillopt_verusage.checkpoint_prepare import prepare as prepare_checkpoints
from skillopt_verusage.checkpoint_selection import continuation_context
from skillopt_verusage.native_card_update import SYSTEM as CARD_SYSTEM, audit_response, paired_groups, task_group, update_cards
from verus_self_evolve.trajectory_progress import verifier_state


CONDITIONS = ["initial", "native", "original_only", "augmented"]
ORIGINAL_COST_UPPER = 7.514324136
BINDING_REPAIR_REQUEST = '38c3aa21cdd049a6bf88a17b2354cc7d'
BINDING_REPAIR_KEY = '262a070f48e88a320e0c/cp3'


DEFERRED_SOURCES = {
    "8722b35e3186b217ea38": "original_timeout_no_verified_reference",
    "67a6f714626f9f53eaff": "verified_final_reference_pruning_incomplete",
}
EXECUTION_REVIEW = "user-authorized-train38-hindsight-native-cards-20261006-v1"
APPROVED_TRANSPORT_REQUEST = "4e2bbb0b33224bdc8cf48caca8af72d5"
APPROVED_ACTOR_TRANSPORT_REQUEST = "d0a576bd8d1e4f02952924041ada8967"
APPROVED_ACTOR_TRANSPORT_TASK = "hint_actor_cp2--064562633b00d03570ef"


def require_design_review(config=None):
    if (not config or config.get("execution_review") != EXECUTION_REVIEW
            or config.get("deferred_sources") != DEFERRED_SOURCES):
        raise RuntimeError("Meeting design review pending: paid campaign execution is disabled")


def learning_items(items, deferred):
    if deferred != DEFERRED_SOURCES or not set(deferred) <= {item['id'] for item in items}:
        raise ValueError("Unexpected learning exclusion contract")
    selected = [item for item in items if item['id'] not in deferred]
    if len(selected) != 38 or len({item['id'] for item in selected}) != 38:
        raise ValueError("Expected38 distinct learning questions")
    return selected


def merge_card_banks(paths, destination):
    """Lossless exact-content aggregation of already audited native batch outputs."""
    bank = {"schema_version":"stage-card-bank-v1","cards":[]}
    known, provenance, bindings = {}, {}, []
    for path in paths:
        path = Path(path)
        source = json.loads(path.read_text())
        source_provenance = json.loads((path.parent/"provenance.json").read_text())
        bindings.append({"path":str(path),"sha256":sha(path),
                         "provenance_sha256":sha(path.parent/"provenance.json")})
        for card in source['cards']:
            key = hashlib.sha256(card['content'].encode()).hexdigest()
            if key not in known:
                ident = f"card-{len(bank['cards'])+1:03d}"
                known[key] = ident
                bank['cards'].append({"id":ident,"content":card['content']})
                provenance[ident] = []
            provenance[known[key]].extend({"native_bank":str(path),**entry}
                                         for entry in source_provenance[card['id']])
    write_json(destination,bank)
    write_json(destination.parent/"provenance.json",provenance)
    write_json(destination.parent/"merge.json",{"source_banks":bindings,
               "method":"exact-content-only","utility_established":False})
    return destination


def audit_smoke_receipt(receipt, evidence):
    if (receipt.get('evidence_sha256') != _sha256_json(evidence)
            or receipt.get('accepted') is not True
            or not isinstance(receipt.get('observations'),str) or not receipt['observations'].strip()):
        raise RuntimeError("Smoke quality review missing, rejected or not bound to this evidence")


def audit_rejected_smoke(parent):
    """Known semantic rejection permits repair, not reopening or unknown-cost replay."""
    evidence = json.loads((parent/'smoke_evidence.json').read_text())
    receipt = json.loads((parent/'smoke_review.json').read_text())
    if (receipt.get('accepted') is not False or receipt.get('engineering_passed') is not True
            or receipt.get('semantic_bank_quality_passed') is not False
            or receipt.get('evidence_sha256') != _sha256_json(evidence)
            or not receipt.get('observations')):
        raise ValueError('Semantic recovery requires an evidence-bound rejected review')
    for condition in ('original_only','augmented'):
        bank = parent/'banks'/(condition+'_smoke')
        if (sha(bank/'cards.json') != evidence['card_banks'][condition]
                or sha(bank/'proposals/batch-000.json') != evidence['proposals'][condition]):
            raise ValueError('Semantic recovery card evidence changed')
    for kind, filename, directory in (('hints','hint.json','hints'),('branches','result.json','augmentation')):
        for key, digest in evidence[kind].items():
            if sha(parent/directory/key/filename) != digest:
                raise ValueError('Semantic recovery continuation evidence changed')


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def audit_transport_repair(parent, records):
    """One user-approved lost teacher response; retain its fee as unknown, not zero."""
    review = json.loads((parent/'transport_repair_review.json').read_text())
    inventory = json.loads((parent/'halt_inventory.json').read_text())
    progress = json.loads((parent/'progress.json').read_text())
    unknown = [row for row in records if any(a.get('estimated_cost_usd') is None
                                           for a in row.get('attempts',[]))]
    if (review.get('replacement_authorized') is not True
            or review.get('request_id') != APPROVED_TRANSPORT_REQUEST
            or review.get('ledger_sha256') != sha(parent/'provider_calls.jsonl')
            or review.get('inventory_sha256') != sha(parent/'halt_inventory.json')
            or inventory.get('ledger_sha256') != review['ledger_sha256']
            or progress.get('phase') != 'stopped' or progress.get('error_type') != 'IncompleteRead'
            or inventory.get('progress') != progress or len(unknown) != 1
            or inventory.get('unknown_records') != unknown):
        raise ValueError('Transport repair requires the exact authorized unknown request and unchanged evidence')
    row = unknown[0]
    parts = row.get('task_id','').split('--')
    if (row.get('request_id') != APPROVED_TRANSPORT_REQUEST or row.get('model') != 'deepseek-v4-pro'
            or len(parts) != 3 or parts[0] != 'hint' or review.get('task_id') != row['task_id']
            or len(row.get('attempts',[])) != 1 or row['attempts'][0].get('usage') is not None
            or not row['attempts'][0].get('error','').startswith('IncompleteRead: ')
            or (parent/'augmentation'/parts[1]/parts[2]).exists()
            or (parent/'hints'/parts[1]/parts[2]/'hint.json').exists()):
        raise ValueError('Transport repair is limited to one missing teacher hint, never an actor retry')
    request_path = (parent/review['request_relative_path']).resolve()
    if (parent not in request_path.parents or review.get('request_sha256') != sha(request_path)
            or json.loads((request_path.parent/'error.json').read_text()).get('type') != 'IncompleteRead'):
        raise ValueError('Transport repair request evidence changed')
    payload = json.loads(request_path.read_text())
    serialized = json.dumps(payload,ensure_ascii=False).encode()
    digest = hashlib.sha256(serialized).hexdigest()
    if (payload.get('model') != 'deepseek-v4-pro' or payload.get('max_output_tokens') != 8192
            or request_path != parent/'calls/teacher'/row['task_id']/digest/'request.json'
            or json.loads((request_path.parent/'started.json').read_text()).get('request_sha256')
            != digest
            or row['attempts'][0].get('max_tokens') != 8192):
        raise ValueError('Transport repair payload contract changed')
    upper = estimate_deepseek_cost({'prompt_cache_miss_tokens':len(serialized)+8192,
                                   'completion_tokens':8192},'deepseek-v4-pro',price_band='peak')
    if review.get('unknown_expense_upper_usd') != upper or upper > .15:
        raise ValueError('Transport repair must preserve the approved conservative unknown expense upper')
    for kind, pattern in (('result_hashes','augmentation/*/*/result.json'),('hint_hashes','hints/*/*/hint.json')):
        actual = {str(path.relative_to(parent)):sha(path) for path in parent.glob(pattern)}
        if actual != inventory.get(kind) or len(actual) != progress.get('hint_completed'):
            raise ValueError('Transport repair completed continuation inventory changed')
    return {'request_id':row['request_id'],'source_run':str(parent),
            'unknown_expense_upper_usd':upper,'ledger_sha256':review['ledger_sha256'],
            'review_sha256':sha(parent/'transport_repair_review.json')}


def audit_actor_transport_repair(parent, records):
    """Exclude one unmetered actor and preserve its separately approved expense."""
    review = json.loads((parent/'actor_transport_repair_review.json').read_text())
    inventory = json.loads((parent/'actor_transport_inventory.json').read_text())
    progress = json.loads((parent/'progress.json').read_text())
    unknown = [row for row in records if any(a.get('estimated_cost_usd') is None
                                           for a in row.get('attempts',[]))]
    if (review.get('replacement_authorized') is not True
            or review.get('request_id') != APPROVED_ACTOR_TRANSPORT_REQUEST
            or review.get('ledger_sha256') != sha(parent/'provider_calls.jsonl')
            or review.get('inventory_sha256') != sha(parent/'actor_transport_inventory.json')
            or inventory.get('ledger_sha256') != review['ledger_sha256']
            or progress.get('phase') != 'stopped' or progress.get('error_type') != 'UnresolvedActorProviderCost'
            or inventory.get('progress') != progress or len(unknown) != 1
            or inventory.get('unknown_records') != unknown):
        raise ValueError('Actor repair requires the exact authorized unknown request and unchanged evidence')
    row = unknown[0]
    key = '064562633b00d03570ef/cp2'
    directory = parent/'augmentation'/key
    hint_directory = parent/'hints'/key
    if (row.get('request_id') != APPROVED_ACTOR_TRANSPORT_REQUEST
            or row.get('task_id') != APPROVED_ACTOR_TRANSPORT_TASK
            or review.get('task_id') != APPROVED_ACTOR_TRANSPORT_TASK
            or review.get('excluded_actor_key') != key or row.get('model') != 'deepseek-v4-pro'
            or len(row.get('attempts',[])) != 1 or row['attempts'][0].get('usage') is not None
            or row['attempts'][0].get('max_tokens') != 131072
            or not row['attempts'][0].get('error','').startswith('IncompleteRead: ')
            or not directory.is_dir() or (directory/'result.json').exists()
            or json.loads((hint_directory/'screen.json').read_text()).get('automatic_screen_passed') is not True):
        raise ValueError('Actor repair requires exactly the excluded unmetered actor and its admitted hint')
    upper = estimate_deepseek_cost({'prompt_cache_miss_tokens':1048576,
                                   'completion_tokens':131072},'deepseek-v4-pro',price_band='peak')
    if review.get('unknown_expense_upper_usd') != upper:
        raise ValueError('Actor repair must retain the full-window conservative unknown expense upper')
    for kind, pattern, count in (('result_hashes','augmentation/*/*/result.json',progress['hint_completed']),
                                ('hint_hashes','hints/*/*/hint.json',progress['hint_completed']+1)):
        actual = {str(path.relative_to(parent)):sha(path) for path in parent.glob(pattern)}
        if actual != inventory.get(kind) or len(actual) != count:
            raise ValueError('Actor repair completed continuation inventory changed')
    partial = {str(path.relative_to(parent)):sha(path) for path in directory.rglob('*') if path.is_file()}
    if (partial != inventory.get('excluded_actor_hashes')
            or not {str(directory.relative_to(parent)/name) for name in ('codex_events.raw.jsonl','workspace/candidate.rs')} <= set(partial)):
        raise ValueError('Actor repair excluded evidence changed')
    return {'request_id':row['request_id'],'source_run':str(parent),
            'unknown_expense_upper_usd':upper,'ledger_sha256':review['ledger_sha256'],
            'excluded_actor_key':key,'review_sha256':sha(parent/'actor_transport_repair_review.json')}


def audit_hint_binding_repair(parent, records):
    """Preserve one known-cost rejected response; never correct or admit its hash."""
    review = json.loads((parent/'hint_binding_repair_review.json').read_text())
    inventory = json.loads((parent/'hint_binding_inventory.json').read_text())
    progress = json.loads((parent/'progress.json').read_text())
    task = 'hint--'+BINDING_REPAIR_KEY.replace('/','--')
    rows = [row for row in records if row.get('request_id') == BINDING_REPAIR_REQUEST]
    if (review.get('repair_authorized') is not True
            or review.get('rejected_hint_key') != BINDING_REPAIR_KEY
            or review.get('request_id') != BINDING_REPAIR_REQUEST or review.get('task_id') != task
            or review.get('ledger_sha256') != sha(parent/'provider_calls.jsonl')
            or review.get('inventory_sha256') != sha(parent/'hint_binding_inventory.json')
            or inventory.get('ledger_sha256') != review['ledger_sha256']
            or inventory.get('progress') != progress
            or progress.get('phase') != 'stopped' or progress.get('error_type') != 'AssertionError'
            or progress.get('error') != 'Hint checkpoint mismatch' or len(rows) != 1
            or any(a.get('estimated_cost_usd') is None for row in records for a in row.get('attempts',[]))):
        raise ValueError('Binding repair requires the exact known-cost rejected request and unchanged inventory')
    request = (parent/review['request_relative_path']).resolve()
    if parent not in request.parents:
        raise ValueError('Binding repair request must remain inside its source run')
    directory = parent/'hints'/BINDING_REPAIR_KEY
    paths = {'request_sha256':request,'validated_sha256':request.parent/'validated.json',
             'response_sha256':request.parent/'response.raw','contract_sha256':directory/'contract.json',
             'teacher_packet_sha256':directory/'teacher_packet.json'}
    if any(not path.is_file() or review.get(key) != sha(path) for key,path in paths.items()):
        raise ValueError('Binding repair request/response/contract evidence changed')
    payload = json.loads(request.read_text())
    digest = hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()
    row = rows[0]
    stored = json.loads(paths['validated_sha256'].read_text())
    hint = json.loads(stored['text'])
    contract = json.loads(paths['contract_sha256'].read_text())
    if (request != parent/'calls/teacher'/task/digest/'request.json'
            or json.loads((request.parent/'started.json').read_text()).get('request_sha256') != digest
            or payload.get('model') != 'deepseek-v4-pro' or payload.get('max_output_tokens') != 8192
            or row.get('task_id') != task or row.get('model') != 'deepseek-v4-pro'
            or len(row.get('attempts',[])) != 1 or row['attempts'][0].get('max_tokens') != 8192
            or row['attempts'][0].get('finish_reason') != 'completed'
            or not isinstance(row['attempts'][0].get('usage'),dict)
            or stored.get('record') != row or stored.get('usage') != row['attempts'][0]['usage']
            or response_text(paths['response_sha256'].read_bytes()) != stored['text']
            or contract.get('source_task') != BINDING_REPAIR_KEY.split('/')[0]
            or review.get('expected_checkpoint_sha256') != contract.get('checkpoint_sha256')
            or review.get('returned_checkpoint_sha256') != hint.get('checkpoint_sha256')
            or hint.get('checkpoint_sha256') == contract.get('checkpoint_sha256')
            or (directory/'hint.json').exists() or (directory/'screen.json').exists()
            or (parent/'augmentation'/BINDING_REPAIR_KEY).exists()):
        raise ValueError('Binding repair cannot replace a delivered hint, actor, or different failure')
    for kind,pattern in (('result_hashes','augmentation/*/*/result.json'),('hint_hashes','hints/*/*/hint.json')):
        actual = {str(path.relative_to(parent)):sha(path) for path in parent.glob(pattern)}
        if actual != inventory.get(kind) or len(actual) != progress.get('hint_completed'):
            raise ValueError('Binding repair completed continuation inventory changed')
    return {'rejected_hint_key':BINDING_REPAIR_KEY,'request_id':BINDING_REPAIR_REQUEST,
            'source_run':str(parent),'review_sha256':sha(parent/'hint_binding_repair_review.json'),
            'ledger_sha256':review['ledger_sha256'],'rejected_response_preserved':True}


def audit_native_candidate_repair(parent, records):
    """Replay fully metered native outputs after a prose-only audit mismatch."""
    review = json.loads((parent/'native_candidate_repair_review.json').read_text())
    progress = json.loads((parent/'progress.json').read_text())
    error = 'Native candidate audit: selected edits contain concrete code/formula: ==>'
    if (review.get('repair_authorized') is not True
            or review.get('classification') != 'generic_native_syntax_audit_mismatch'
            or review.get('ledger_sha256') != sha(parent/'provider_calls.jsonl')
            or review.get('progress_sha256') != sha(parent/'progress.json')
            or progress.get('phase') != 'stopped' or progress.get('error_type') != 'RuntimeError'
            or progress.get('error') != error or progress.get('hint_completed') != 114
            or any(a.get('estimated_cost_usd') is None for row in records for a in row.get('attempts',[]))):
        raise ValueError('Native recovery requires the reviewed known-cost syntax-audit mismatch')
    patterns = ('augmentation/*/*/result.json', 'hints/*/*/hint.json',
                'artifacts/native/patches/*.json', 'calls/native/**/*',
                'calls/native_finalization/**/*')
    paths = [path for pattern in patterns for path in parent.glob(pattern)]
    if any(path.is_symlink() for path in paths):
        raise ValueError('Native recovery cannot follow symlink evidence')
    actual = {str(path.relative_to(parent)):sha(path) for path in paths if path.is_file()}
    if actual != review.get('preserved_hashes'):
        raise ValueError('Native recovery preserved evidence changed')
    if (len(list(parent.glob(patterns[0]))) != 114 or len(list(parent.glob(patterns[1]))) != 114
            or len(list(parent.glob(patterns[2]))) != 5
            or any((parent/path).exists() for path in ('artifacts/native/SKILL.md',
                    'artifacts/native/learning.json','frozen_artifacts.json','val_inputs','validation'))):
        raise ValueError('Native recovery requires all continuations and only the rejected native stage')
    requests = list(parent.glob('calls/native/analyst/*/*/request.json'))
    final_requests = list(parent.glob('calls/native_finalization/merge/*/*/request.json'))
    all_requests = list(parent.glob('calls/native/**/request.json')) + list(parent.glob('calls/native_finalization/**/request.json'))
    if len(requests) != 5 or len(final_requests) != 1 or set(all_requests) != set(requests+final_requests):
        raise ValueError('Native recovery requires exactly five analyst calls and one completed merge')
    used = set()
    for request in all_requests:
        payload = json.loads(request.read_text())
        directory = request.parent
        if any(not (directory/name).is_file() for name in ('validated.json','started.json','response.raw')):
            raise ValueError('Native recovery cache is incomplete')
        stored = json.loads((directory/'validated.json').read_text())
        raw = (directory/'response.raw').read_bytes()
        raw_usage,raw_model,raw_status = _native_response_usage(raw)
        response = json.loads(stored['text'])
        patch = response.get('patch') if isinstance(response,dict) and directory.parent.parent.name == 'analyst' else response
        edits = patch.get('edits') if isinstance(patch,dict) else None
        record = stored['record']
        attempts = record.get('attempts',[])
        digest = hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()
        user = payload['input'][0]['content'][0]['text']
        fingerprint = hashlib.sha256((payload['instructions']+user).encode()).hexdigest()
        task = directory.parent.parent.name+'/'+fingerprint
        matches = [row for row in records if row.get('request_id') == record.get('request_id')]
        if (directory.name != digest or directory.parent.name != fingerprint
                or json.loads((directory/'started.json').read_text()).get('request_sha256') != digest
                or payload.get('model') != 'deepseek-v4-pro' or payload.get('reasoning') != {'effort':'high'}
                or payload.get('text') != {'format':{'type':'json_object'}}
                or payload.get('max_output_tokens') != 16384 or payload.get('stream') is not False
                or record.get('model') != 'deepseek-v4-pro' or record.get('task_id') != task
                or len(matches) != 1 or matches[0] != record or len(attempts) != 1
                or attempts[0].get('finish_reason') != 'completed' or attempts[0].get('error')
                or attempts[0].get('max_tokens') != 16384 or not isinstance(attempts[0].get('usage'),dict)
                or stored.get('usage') != attempts[0]['usage']
                or raw_usage != stored['usage'] or raw_model != 'deepseek-v4-pro' or raw_status != 'completed'
                or response_text(raw) != stored['text'] or not isinstance(edits,list)
                or (directory/'error.json').exists() or record['request_id'] in used):
            raise ValueError('Native recovery cache must match the exact metered request and raw response')
        used.add(record['request_id'])
    native_rows = [row for row in records if row.get('task_id','').startswith(('analyst/','merge/','ranking/'))]
    if {row['request_id'] for row in native_rows} != used or len(native_rows) != len(used):
        raise ValueError('Native recovery ledger has an unmatched optimizer call')
    return {'source_run':str(parent),'review_sha256':sha(parent/'native_candidate_repair_review.json'),
            'ledger_sha256':review['ledger_sha256'],'cached_native_requests':len(used),
            'native_outputs_unchanged':True,'new_native_calls':0}


def audit_card_storage_repair(parent, records):
    from skillopt_verusage.card_storage_recovery import audit
    return audit(parent, records, audit_card_stage_repair)


def audit_full_card_semantic_repair(parent, records):
    from skillopt_verusage.full_card_semantic_recovery import audit
    return audit(parent, records, audit_card_storage_repair)


def audit_card_stage_repair(parent, records):
    """Keep valid paid card replies; regenerate one malformed/ungrounded reply."""
    review = json.loads((parent/'card_stage_repair_review.json').read_text())
    if review.get('classification') == 'chained_card_content_type_repair':
        return audit_chained_card_content_repair(parent,records,review)
    progress = json.loads((parent/'progress.json').read_text())
    prefix = 'Native card reflection incomplete: '
    failures = {'Analyst did not cover every trace exactly once',
                'Prior native card audit failure: stop new calls','Benchmark target name in card'}
    if (review.get('repair_authorized') is not True
            or review.get('classification') != 'full_card_schema_and_lexical_audit_repair'
            or review.get('ledger_sha256') != sha(parent/'provider_calls.jsonl')
            or review.get('progress_sha256') != sha(parent/'progress.json')
            or progress.get('phase') != 'stopped' or progress.get('error_type') != 'RuntimeError'
            or not progress.get('error','').startswith(prefix)
            or set(progress['error'][len(prefix):].split('; ')) != failures
            or progress.get('hint_completed') != 114 or len(records) != 10
            or any(a.get('estimated_cost_usd') is None for row in records for a in row.get('attempts',[]))):
        raise ValueError('Card recovery requires the exact reviewed known-cost full-card failure')
    patterns = ('augmentation/*/*/result.json','hints/*/*/hint.json','artifacts/native/**/*',
                'calls/native/**/*','calls/native_finalization/**/*','calls/original_only/**/*',
                'banks/original_only_remaining/proposals/*.json','recovered_native_candidate.json')
    paths = [path for pattern in patterns for path in parent.glob(pattern)]
    actual = {str(path.relative_to(parent)):sha(path) for path in paths if path.is_file()}
    if any(path.is_symlink() for path in paths) or actual != review.get('preserved_hashes'):
        raise ValueError('Card recovery preserved evidence changed')
    if (len(list(parent.glob(patterns[0]))) != 114 or len(list(parent.glob(patterns[1]))) != 114
            or any((parent/path).exists() for path in ('frozen_artifacts.json','val_inputs','validation',
                   'banks/original_only/cards.json','banks/augmented_remaining'))):
        raise ValueError('Card recovery requires all continuations and no downstream outputs')
    ancestor = Path(json.loads((parent/'config.json').read_text())['reused_hint_root']).resolve()
    ancestral_records = [json.loads(line) for line in (ancestor/'provider_calls.jsonl').read_text().splitlines() if line.strip()]
    native_audit = audit_native_candidate_repair(ancestor,ancestral_records)
    if json.loads((parent/'recovered_native_candidate.json').read_text()) != native_audit:
        raise ValueError('Card recovery native receipt changed')
    for label in ('native','native_finalization'):
        copied = {str(p.relative_to(parent)):sha(p) for p in (parent/'calls'/label).rglob('*') if p.is_file()}
        original = {str(p.relative_to(ancestor)):sha(p) for p in (ancestor/'calls'/label).rglob('*') if p.is_file()}
        if copied != original:
            raise ValueError('Card recovery native caches changed from their metered ancestor')
    native_sha = sha(parent/'artifacts/native/SKILL.md')
    native_review = json.loads((ancestor/'native_candidate_repair_review.json').read_text())
    learning = json.loads((parent/'artifacts/native/learning.json').read_text())
    if native_sha != native_review.get('expected_native_candidate_sha256') or learning.get('source_count') != 38 or learning.get('audit') != []:
        raise ValueError('Card recovery native artifact changed')
    requests = list(parent.glob('calls/original_only/card-batch-*/*/request.json'))
    if {p.parent.parent.name for p in requests} != {f'card-batch-{i:03d}' for i in range(10)} or len(requests) != 10:
        raise ValueError('Card recovery requires exactly the ten settled card requests')
    replay = []
    used = set()
    for request in sorted(requests):
        directory = request.parent
        if any(not (directory/name).is_file() for name in ('validated.json','started.json','response.raw')):
            raise ValueError('Card recovery cache is incomplete')
        payload = json.loads(request.read_text())
        stored = json.loads((directory/'validated.json').read_text())
        record = stored['record']; attempts = record.get('attempts',[])
        raw = (directory/'response.raw').read_bytes()
        raw_usage,raw_model,raw_status = _native_response_usage(raw)
        digest = hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()
        name = directory.parent.name
        matches = [row for row in records if row.get('request_id') == record.get('request_id')]
        if (directory.name != digest or json.loads((directory/'started.json').read_text()).get('request_sha256') != digest
                or payload.get('model') != 'deepseek-v4-pro' or payload.get('reasoning') != {'effort':'high'}
                or payload.get('instructions') != CARD_SYSTEM or payload.get('max_output_tokens') != 16384
                or payload.get('text') != {'format':{'type':'json_object'}} or payload.get('stream') is not False
                or record.get('model') != 'deepseek-v4-pro' or record.get('task_id') != name
                or len(matches) != 1 or matches[0] != record or len(attempts) != 1
                or attempts[0].get('finish_reason') != 'completed' or attempts[0].get('error')
                or attempts[0].get('max_tokens') != 16384 or raw_usage != stored.get('usage')
                or raw_usage != attempts[0].get('usage') or raw_model != 'deepseek-v4-pro' or raw_status != 'completed'
                or response_text(raw) != stored['text'] or (directory/'error.json').exists()
                or record['request_id'] in used):
            raise ValueError('Card recovery cache must match its complete metered raw request/response')
        used.add(record['request_id'])
        groups = expand_strings(json.loads(payload['input'][0]['content'][0]['text']))['task_groups']
        if len(groups) != 2 or any(len(group['trace_ids']) != 1 for group in groups):
            raise ValueError('Card recovery is original-only, two-source evidence')
        response = json.loads(stored['text'])
        proposal = parent/'banks/original_only_remaining/proposals'/('batch-'+name[-3:]+'.json')
        if name == 'card-batch-008':
            ids = [tid for group in groups for tid in group['trace_ids']]
            refs = {ref for group in groups for ref in group['evidence_ids']}
            unknown = sorted({ref for card in response['cards'] for ref in card['evidence_refs']} - refs)
            if (review.get('failed_card_task') != name or review.get('failed_request_id') != record['request_id']
                    or record['request_id'] != '59b489b4e74c4880ac630dec4a901250'
                    or review.get('expected_trace_ids') != ids or not isinstance(response['trace_analyses'],dict)
                    or set(response['trace_analyses']) != set(ids) or len(unknown) != 2
                    or unknown != review.get('unknown_evidence_refs') or proposal.exists()):
                raise ValueError('Card recovery cannot admit or rewrite the malformed/unknown-reference reply')
        else:
            audit_response(response,groups)
            if name != 'card-batch-009' and (not proposal.exists() or json.loads(proposal.read_text()) != response):
                raise ValueError('Card recovery accepted proposals changed')
            if name == 'card-batch-009' and proposal.exists():
                raise ValueError('Card recovery lexical rejection must remain preserved as rejected')
            replay.append({'label':'original_only','name':name,'request_relative_path':str(request.relative_to(parent))})
    if len(used) != 10 or len(replay) != 9 or len(list(parent.glob(patterns[6]))) != 8:
        raise ValueError('Card recovery must preserve every settled reply without omissions')
    return {'source_run':str(parent),'review_sha256':sha(parent/'card_stage_repair_review.json'),
            'ledger_sha256':review['ledger_sha256'],'native_candidate_sha256':native_sha,
            'replay_requests':replay,'rejected_card_response_preserved':True}


def audit_chained_card_content_repair(parent, records, review):
    """Recover the exact known-cost content-object halt, preserving paid cache ownership."""
    progress = json.loads((parent/'progress.json').read_text())
    expected_error = "Native card reflection incomplete: 'dict' object has no attribute 'strip'; Prior native card audit failure: stop new calls"
    if (review.get('repair_authorized') is not True or progress.get('phase') != 'stopped'
            or progress.get('error_type') != 'RuntimeError' or progress.get('error') != expected_error
            or progress.get('hint_completed') != 114 or len(records) != 8
            or review.get('ledger_sha256') != sha(parent/'provider_calls.jsonl')
            or review.get('progress_sha256') != sha(parent/'progress.json')
            or any(a.get('estimated_cost_usd') is None for row in records for a in row.get('attempts',[]))):
        raise ValueError('Chained card recovery requires the exact metered content-type halt')
    patterns = ('augmentation/*/*/result.json','hints/*/*/hint.json','artifacts/native/**/*',
                'calls/native/**/*','calls/native_finalization/**/*','calls/original_only/**/*',
                'banks/original_only_remaining/proposals/*.json','recovered_card_requests.json')
    paths = [p for pattern in patterns for p in parent.glob(pattern)]
    if (any(p.is_symlink() for p in paths)
            or {str(p.relative_to(parent)):sha(p) for p in paths if p.is_file()} != review.get('preserved_hashes')
            or len(list(parent.glob(patterns[0]))) != 114 or len(list(parent.glob(patterns[1]))) != 114
            or any((parent/p).exists() for p in ('frozen_artifacts.json','val_inputs','validation',
                       'banks/original_only/cards.json','banks/augmented_remaining'))):
        raise ValueError('Chained card evidence changed or reached downstream outputs')
    ancestor = Path(json.loads((parent/'config.json').read_text())['reused_hint_root']).resolve()
    ancestral_records = [json.loads(s) for s in (ancestor/'provider_calls.jsonl').read_text().splitlines() if s.strip()]
    if json.loads((ancestor/'card_stage_repair_review.json').read_text()).get('classification') != 'full_card_schema_and_lexical_audit_repair':
        raise ValueError('Chained content repair requires the reviewed first card-stage ancestor')
    ancestral = audit_card_stage_repair(ancestor,ancestral_records)
    if json.loads((parent/'recovered_card_requests.json').read_text()) != ancestral:
        raise ValueError('Chained card ancestor receipt changed')
    inherited = {entry['request_relative_path'] for entry in ancestral['replay_requests']}
    for label in ('native','native_finalization'):
        if ({str(p.relative_to(parent)):sha(p) for p in (parent/'calls'/label).rglob('*') if p.is_file()}
                != {str(p.relative_to(ancestor)):sha(p) for p in (ancestor/'calls'/label).rglob('*') if p.is_file()}):
            raise ValueError('Chained card native paid caches changed')
    learning = json.loads((parent/'artifacts/native/learning.json').read_text())
    native_sha = sha(parent/'artifacts/native/SKILL.md')
    if native_sha != ancestral['native_candidate_sha256'] or learning.get('source_count') != 38 or learning.get('audit') != []:
        raise ValueError('Chained card native artifact changed')
    requests = sorted(parent.glob('calls/original_only/card-batch-*/*/request.json'))
    if (len(requests) != 17 or set(requests) != set(parent.glob('calls/original_only/**/request.json'))
            or {p.parent.parent.name for p in requests} != {f'card-batch-{i:03d}' for i in range(17)}):
        raise ValueError('Chained card recovery requires seventeen complete cache requests')
    used, replay = set(), []
    for request in requests:
        directory = request.parent; name = directory.parent.name
        relative = str(request.relative_to(parent))
        if any(not (directory/n).is_file() for n in ('started.json','validated.json','response.raw')):
            raise ValueError('Chained card cache incomplete')
        payload = json.loads(request.read_text()); stored = json.loads((directory/'validated.json').read_text())
        record = stored['record']; attempts = record.get('attempts',[])
        raw = (directory/'response.raw').read_bytes()
        usage,model,status = _native_response_usage(raw)
        fingerprint = hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()
        if relative in inherited:
            if ({p.name:sha(p) for p in directory.iterdir() if p.is_file()}
                    != {p.name:sha(p) for p in (ancestor/relative).parent.iterdir() if p.is_file()}):
                raise ValueError('Chained inherited paid cache changed')
            if any(row.get('request_id') == record.get('request_id') for row in records):
                raise ValueError('Inherited card call appears as a new paid call')
        else:
            matches = [row for row in records if row.get('request_id') == record.get('request_id')]
            if len(matches) != 1 or matches[0] != record or record['request_id'] in used:
                raise ValueError('Chained card call lacks exact current ledger ownership')
            used.add(record['request_id'])
        if (directory.name != fingerprint or json.loads((directory/'started.json').read_text()).get('request_sha256') != fingerprint
                or payload.get('model') != 'deepseek-v4-pro' or payload.get('reasoning') != {'effort':'high'}
                or payload.get('instructions') != CARD_SYSTEM or payload.get('max_output_tokens') != 16384
                or payload.get('text') != {'format':{'type':'json_object'}} or payload.get('stream') is not False
                or record.get('model') != model or model != 'deepseek-v4-pro' or status != 'completed'
                or record.get('task_id') != name or len(attempts) != 1
                or attempts[0].get('finish_reason') != 'completed' or attempts[0].get('error')
                or attempts[0].get('estimated_cost_usd') is None or attempts[0].get('max_tokens') != 16384
                or usage != stored.get('usage') or usage != attempts[0].get('usage')
                or response_text(raw) != stored['text'] or (directory/'error.json').exists()):
            raise ValueError('Chained card cache differs from its complete paid raw request/response')
        groups = expand_strings(json.loads(payload['input'][0]['content'][0]['text']))['task_groups']
        if len(groups) != 2 or any(len(g['trace_ids']) != 1 for g in groups):
            raise ValueError('Chained card recovery requires two original-only source groups')
        response = json.loads(stored['text'])
        proposal = parent/'banks/original_only_remaining/proposals'/('batch-'+name[-3:]+'.json')
        if name == 'card-batch-016':
            if (review.get('failed_card_task') != name or review.get('failed_request_id') != record['request_id'] or record['request_id'] != '0ed7a54eefab4ffebfa279d601e9e4ee'
                    or not isinstance(response.get('trace_analyses'),list) or len(response.get('cards',[])) != 2
                    or any(not isinstance(card.get('content'),dict) for card in response['cards']) or proposal.exists()):
                raise ValueError('Chained recovery must preserve the exact rejected content-object reply')
        else:
            audit_response(response,groups)
            if not proposal.is_file() or json.loads(proposal.read_text()) != response:
                raise ValueError('Chained recovery accepted proposal changed')
            replay.append({'label':'original_only','name':name,'request_relative_path':relative})
    if used != {row['request_id'] for row in records} or len(replay) != 16 or len(list(parent.glob(patterns[6]))) != 16:
        raise ValueError('Chained recovery cannot omit a metered call or accepted proposal')
    return {'source_run':str(parent),'review_sha256':sha(parent/'card_stage_repair_review.json'),
            'ledger_sha256':review['ledger_sha256'],'native_candidate_sha256':native_sha,
            'replay_requests':replay,'rejected_card_response_preserved':True}


class Campaign:
    def __init__(self, config):
        self.config = config
        self.repo = Path(config["repo"]).resolve()
        self.root = Path(config["run_root"]).resolve()
        approved = Path(os.environ["VERUS_SKILL_RUN_ROOT"]).resolve()
        if self.root == approved or approved not in self.root.parents or self.repo in self.root.parents:
            raise ValueError("Campaign output must be an external run-root child")
        self.source_root = Path(config["source_root"]).resolve()
        if self.root==self.source_root or self.source_root in self.root.parents:
            raise ValueError("Campaign output must not overwrite source-run evidence")
        if (self.root/"started.json").exists():
            raise RuntimeError("Archived campaign cannot be reopened; use a fresh reviewed run")
        self.rejected_hint_key = None
        self.reused_smoke_parent = None
        if config.get('reused_hint_root'):
            parent = Path(config['reused_hint_root']).resolve()
            parent_config = json.loads((parent/'config.json').read_text())
            parent_progress = json.loads((parent/'progress.json').read_text())
            require_design_review(parent_config)
            if any(parent_config.get(k) != config.get(k) for k in ('repo','source_root','reviewed_progress_root','checkpoint_policy')):
                raise ValueError('Recovery source/selection configuration changed')
            pre_actor = (parent_progress.get('error_type') == 'ValueError'
                         and parent_progress.get('error','').startswith('output directory must be empty:')
                         and not any((parent/'augmentation').glob('*/*/result.json'))
                         and not any((parent/'augmentation').glob('*/*/codex_events.raw.jsonl')))
            card_contract = (parent_progress.get('error_type') == 'RuntimeError'
                         and parent_progress.get('error','') == 'Native card reflection incomplete: Copied proof code/formula in card'
                         and parent_progress.get('hint_completed') == 6)
            semantic_contract = (parent_progress.get('error_type') == 'RuntimeError'
                         and parent_progress.get('error','') == 'Smoke quality review missing, rejected or not bound to this evidence'
                         and parent_progress.get('hint_completed') == 6
                         and (parent/'smoke_review.json').exists())
            hint_contract = (parent_progress.get('error_type') == 'RuntimeError'
                         and parent_progress.get('error','').startswith('Hint needs review; refusing a missing continuation: ')
                         and parent_progress.get('hint_rejected') == 1
                         and (parent/'hint_repair_review.json').exists())
            binding_contract = (parent_progress.get('error_type') == 'AssertionError'
                                and parent_progress.get('error') == 'Hint checkpoint mismatch'
                                and (parent/'hint_binding_repair_review.json').exists())
            transport_contract = (parent_progress.get('error_type') == 'IncompleteRead'
                                  and (parent/'transport_repair_review.json').exists())
            actor_transport_contract = (parent_progress.get('error_type') == 'UnresolvedActorProviderCost'
                                        and (parent/'actor_transport_repair_review.json').exists())
            native_contract = (parent_progress.get('error_type') == 'RuntimeError'
                               and parent_progress.get('error') == 'Native candidate audit: selected edits contain concrete code/formula: ==>'
                               and (parent/'native_candidate_repair_review.json').exists())
            card_stage_contract = (parent_progress.get('error_type') == 'RuntimeError'
                                   and parent_progress.get('error','').startswith('Native card reflection incomplete: ')
                                   and (parent/'card_stage_repair_review.json').exists())
            storage_contract = (parent/'storage_repair_review.json').exists()
            full_semantic_contract = (parent/'full_card_semantic_repair_review.json').exists()
            if (approved not in parent.parents or parent == self.root
                    or (parent_progress.get('phase') != 'stopped' and not storage_contract)
                    or not (pre_actor or card_contract or semantic_contract or hint_contract or binding_contract or transport_contract or actor_transport_contract or native_contract or card_stage_contract or storage_contract or full_semantic_contract)):
                raise ValueError("Only audited pre-actor, card-contract or hint-contract failure allows recovery")
            records = [json.loads(line) for line in (parent/'provider_calls.jsonl').read_text().splitlines() if line.strip()]
            if transport_contract:
                write_json(self.root/'approved_unknown_expense.json',audit_transport_repair(parent,records))
            elif actor_transport_contract:
                write_json(self.root/'approved_unknown_expense.json',audit_actor_transport_repair(parent,records))
            elif any(a.get('estimated_cost_usd') is None for row in records for a in row.get('attempts',[])):
                raise ValueError("Recovery blocked by unresolved parent usage")
            if semantic_contract:
                audit_rejected_smoke(parent)
            if binding_contract:
                binding_review = audit_hint_binding_repair(parent,records)
                self.rejected_hint_key = binding_review['rejected_hint_key']
                write_json(self.root/'recovered_hint_binding.json',binding_review)
            if native_contract:
                native_review = audit_native_candidate_repair(parent,records)
                for label in ('native','native_finalization'):
                    shutil.copytree(parent/'calls'/label,self.root/'calls'/label)
                write_json(self.root/'recovered_native_candidate.json',native_review)
            if card_stage_contract or storage_contract or full_semantic_contract:
                repair_audit = (audit_full_card_semantic_repair if full_semantic_contract else
                                audit_card_storage_repair if storage_contract else audit_card_stage_repair)
                card_review = repair_audit(parent,records)
                for label in ('native','native_finalization'):
                    shutil.copytree(parent/'calls'/label,self.root/'calls'/label)
                for entry in card_review['replay_requests']:
                    request = parent/entry['request_relative_path']
                    shutil.copytree(request.parent,self.root/request.parent.relative_to(parent))
                write_json(self.root/'recovered_card_requests.json',card_review)
            if hint_contract:
                review = json.loads((parent/'hint_repair_review.json').read_text())
                key = parent_progress['error'].split(': ',1)[1]
                directory = parent/'hints'/key
                if (review.get('repair_authorized') is not True or review.get('rejected_hint_key') != key
                        or review.get('hint_sha256') != sha(directory/'hint.json')
                        or review.get('screen_sha256') != sha(directory/'screen.json')
                        or review.get('ledger_sha256') != sha(parent/'provider_calls.jsonl')
                        or json.loads((directory/'screen.json').read_text()).get('automatic_screen_passed') is not False
                        or (parent/'augmentation'/key).exists()):
                    raise ValueError('Hint repair requires unchanged rejected evidence and no actor launch')
                self.rejected_hint_key = key
            if hint_contract or binding_contract or transport_contract or actor_transport_contract or native_contract or card_stage_contract or storage_contract or full_semantic_contract:
                old_evidence = json.loads((parent/'smoke_evidence.json').read_text())
                audit_smoke_receipt(json.loads((parent/'smoke_review.json').read_text()),old_evidence)
                for condition in ('original_only','augmented'):
                    bank = parent/'banks'/(condition+'_smoke')
                    if (sha(bank/'cards.json') != old_evidence['card_banks'][condition]
                            or sha(bank/'proposals/batch-000.json') != old_evidence['proposals'][condition]
                            or json.loads((bank/'update.json').read_text())['system_sha256'] != hashlib.sha256(CARD_SYSTEM.encode()).hexdigest()):
                        raise ValueError('Reviewed smoke cards changed; no automatic reuse')
                    shutil.copytree(bank,self.root/'banks'/bank.name)
                self.reused_smoke_parent = parent
            if card_contract or semantic_contract or hint_contract or binding_contract or transport_contract or actor_transport_contract or native_contract or card_stage_contract or storage_contract or full_semantic_contract:
                results = list((parent/'augmentation').glob('*/*/result.json'))
                expected = {ident for ident in json.loads((parent/'smoke_plan.json').read_text())['source_tasks']}
                expansion_recovery = hint_contract or binding_contract or transport_contract or actor_transport_contract or native_contract or card_stage_contract or storage_contract or full_semantic_contract
                required_count = parent_progress['hint_completed'] if expansion_recovery else 6
                excluded = {'064562633b00d03570ef/cp2'} if actor_transport_contract else set()
                if (len(results) != required_count
                        or (not expansion_recovery and {p.parent.parent.name for p in results} != expected)
                        or {str(p.relative_to(parent/'augmentation')) for p in (parent/'augmentation').glob('*/*')
                            if not (p/'result.json').exists()} != excluded):
                    raise ValueError("Recovery requires the complete reviewed continuation set")
                for path in results:
                    row = json.loads(path.read_text())
                    if (row.get('fidelity') != 'V2_TRACE' or (not expansion_recovery and not row.get('hard')) or not row.get('safety_passed')
                            or row.get('actor_model') != 'deepseek-v4-pro' or row.get('actor_reasoning_effort') != 'max'
                            or row.get('usage',{}).get('unknown_cost_requests') != 0):
                        raise ValueError("Recovery requires verified safe fully metered smoke branches")
                    destination = self.root/path.relative_to(parent).parent
                    shutil.copytree(path.parent,destination)
                write_json(self.root/'recovered_smoke.json',{'source_run':str(parent),
                           'results':{str(p.relative_to(parent)):sha(p) for p in results},
                           'source_ledger_sha256':sha(parent/'provider_calls.jsonl'),
                           'new_actor_calls':0,'rejected_card_response_preserved':True})
        self.predictions = self.source_root/"rollout/predictions"
        self.prompts = self.repo/"skillopt-verusage/prompts"
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = self.root/"provider_calls.jsonl"
        self.lock = threading.Lock()
        self.progress = {"phase":"preflight", "hint_completed":0, "hint_rejected":0,
                         "original_proposals":0, "augmented_proposals":0, "evaluation_completed":0}
        self.traces = {}; self.refs = {}; self.snapshots = {}; self.selection = {}
        self.branches = {}; self.hints = {}

    def update(self, **changes):
        with self.lock:
            self.progress.update(changes)
            self.progress["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            write_json(self.root/"progress.json", self.progress)
            print(compact(self.progress), flush=True)

    def client(self, label, guards):
        require_design_review(getattr(self,"config",None))
        return GuardedDeepSeek(root=self.root/"calls"/label, api_key=os.environ["DEEPSEEK_API_KEY"],
                              guards=guards, ledger=self.ledger,
                              tokenizer_path=self.config.get('text_tokenizer_path'),
                              tokenizer_sha256=self.config.get('text_tokenizer_sha256'))

    def preflight(self):
        manifest = self.repo/"fixed-claude-stratified-80-seed20260814/train/items.json"
        if sha(manifest)!="0e42aad8c5e8a6789d06e7b15cfdca903479b16dc76f863544f219e6bbe40536":
            raise ValueError("Fixed train manifest changed")
        self.items = json.loads(manifest.read_text())
        if len(self.items)!=40 or len({x["id"] for x in self.items})!=40:
            raise ValueError("Expected exactly 40 unique original sources")
        if self.config.get("execution_review") == EXECUTION_REVIEW:
            self.items = learning_items(self.items,self.config.get("deferred_sources"))
        write_json(self.root/"learning_subset.json",{
            "fixed_train_manifest_sha256":sha(manifest),"included_ids":[item['id'] for item in self.items],
            "deferred_sources":self.config.get("deferred_sources",{}),"rerun_deferred":False})
        self.seed = self.root/"artifacts/initial.md"
        self.seed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.repo/"skillopt-verusage/skills/initial.md",self.seed)
        if sha(self.seed)!="96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40":
            raise ValueError("Initial skill changed")
        self.results = []
        packet_sizes = {}
        for item in self.items:
            ident = item["id"]
            trace,refs,snapshots = load_trace(self.predictions/ident)
            result = trace["result"]
            if result["fidelity"]=="V0_INVALID" or result["actor_model"]!="deepseek-v4-pro" or result["actor_reasoning_effort"]!="max":
                raise ValueError("Unaccepted source run contract")
            if result["source_sha256"]!=item["source_sha256"] or result["skill_sha256"]!=sha(self.seed):
                raise ValueError("Original source/skill hash mismatch")
            if self.config.get("execution_review") == EXECUTION_REVIEW and not result["hard"]:
                raise ValueError("Train38 requires verified original references")
            source = self.repo/item["source_path"]
            if sha(source)!=item["source_sha256"]:
                raise ValueError("Fixed fixture changed")
            target = self.root/"inputs"/item["directory_group"]/"unverified"/source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source,target)
            item["runtime_source"] = str(target)
            self.traces[ident],self.refs[ident],self.snapshots[ident] = trace,refs,snapshots
            self.results.append(result)
            packet_sizes[ident] = len(compact(shared_strings(trace)).encode())
            if packet_sizes[ident]+32768>1048576:
                raise ValueError("Full original evidence fails context admission: "+ident)
        write_json(self.root/"train_items.json",self.items)
        eligible = sum(bool(result["hard"]) for result in self.results)
        write_json(self.root/"preflight.json",{"original_sources":len(self.items),"fixed_train_sources":40,"verified_reference_sources":eligible,
            "checkpoint_selection":self.config.get('checkpoint_policy','rule_based_v1'),
            "execution_review":self.config.get('execution_review'),
            "complete_evidence_packet_bytes":packet_sizes,"source_manifest_sha256":sha(manifest),
            "model":"deepseek-v4-pro","actor_effort":"max","learning_actor_seconds":1800,
            "evaluation_actor_seconds":600,"teacher_effort":"high",
            "learning_budget":"record_only","original_logical_charge_upper_usd":ORIGINAL_COST_UPPER,
            "checkpoints_per_task":3,"card_batch_questions":2,"card_batch_augmented_traces":8,
            "evaluation_repetitions":2,"evaluation_attempts":160,"test_accessed":False,
            "source_unknown_reservation":"preserved in historical source run; not refunded",
            "code_sha256":{p.name:sha(p) for p in (Path(__file__),Path(__file__).with_name('campaign_native.py'),
                        Path(__file__).with_name('campaign_evidence.py'),Path(__file__).with_name('guarded_deepseek.py'),
                        Path(__file__).with_name('checkpoint_selection.py'),Path(__file__).with_name('checkpoint_prepare.py'),
                        Path(__file__).with_name('native_card_update.py'),Path(__file__).with_name('card_bank.py'),
                        Path(__file__).with_name('card_storage_recovery.py'),
                        Path(__file__).with_name('full_card_semantic_recovery.py'),
                        Path(__file__).with_name('text_context.py'))}})
        self.update(phase="inputs_audited",verified_reference_sources=eligible)

    def prepare_progress(self):
        """Offline host-only analysis; does not freeze checkpoints or start actors."""
        ledger = [json.loads(x) for x in (self.source_root/"bridge_calls.jsonl").read_text().splitlines()]
        reports = {}
        for item in self.items:
            ident = item["id"]
            directory = self.root/"proof_progress"/ident
            if directory.exists():
                raise RuntimeError("Refusing to overwrite existing proof-progress evidence")
            directory.mkdir(parents=True)
            candidate = directory/"candidate.rs"
            baseline = directory/"input.rs"
            baseline.write_text(self.traces[ident]["original_input"])

            def verify(source):
                candidate.write_text(source)
                completed = subprocess.run([self.config["verus_bin"],str(candidate)],
                    capture_output=True,text=True,timeout=30,check=False)
                output = completed.stdout+completed.stderr
                return completed.returncode==0 and verifier_state(output)["tier_rank"]==2,output

            def preservation(original, pruned):
                candidate.write_text(pruned)
                completed = subprocess.run([self.config["lynette_bin"],"compare","-t",str(baseline),str(candidate)],
                    capture_output=True,text=True,timeout=30,check=False)
                return completed.returncode==0,completed.stdout+completed.stderr

            report = analyze_progress(self.traces[ident],self.snapshots[ident],ledger,
                        self.traces[ident]["result"]["bridge_task_key"],item["task_id"].split("__")[-1],
                        verify,preservation)
            write_json(directory/"report.json",report)
            reports[ident] = report
        return reports

    def budgets(self):
        require_design_review(getattr(self,"config",None))
        # User requested expense recording, not artificial per-method cash limits.
        self.augmentation_guards = []
        self.teacher = self.client("teacher",[])
        self.extractors = {name:self.client(name,[]) for name in ("native","original_only","augmented")}
        self.final_client = self.client("native_finalization",[])

    def prepare_selection(self):
        """Reviewed helper-inclusive reports feed a replaceable selector, never a paid call."""
        self.selection = prepare_checkpoints(
            self.repo/"fixed-claude-stratified-80-seed20260814/train/items.json", self.source_root,
            Path(self.config["reviewed_progress_root"]), self.root/"checkpoint_preparation",
            policy=self.config.get("checkpoint_policy", "rule_based_v1"), lynette_bin=Path(self.config["lynette_bin"]),
            included_ids=[item['id'] for item in self.items])
        if any(row['report_binding']['reference_kind'] != 'verifier_greedy_pruned'
               for row in self.selection.values()):
            raise ValueError("Current learning subset requires completed pruned references")
        self.update(phase="checkpoints_prepared",checkpoint_count=3*len(self.items))
        return self.selection

    @contextmanager
    def bridge(self, label, guards):
        from skillopt_verusage import codex_deepseek_bridge as implementation
        # Codex requires a provider env key even for this loopback bridge. It
        # must never receive the real upstream credential held by the host.
        os.environ.setdefault('SKILLOPT_CODEX_BRIDGE_TOKEN','local-loopback-only')
        directory = self.root/label
        directory.mkdir(parents=True, exist_ok=True)
        catalog = (self.source_root/"models.json").read_bytes()
        (directory/"models.json").write_bytes(catalog)
        config = BridgeConfig(model="deepseek-v4-pro",upstream_base_url="https://api.deepseek.com",
            api_key=os.environ["DEEPSEEK_API_KEY"],ledger_path=self.ledger,max_output_tokens=131072,
            retry_output_tokens=131072,request_timeout_seconds=1800,native_responses=True,
            expected_upstream_model="deepseek-v4-pro",pricing_profile="deepseek-current",
            model_catalog=catalog,budget_guard=BudgetMux(guards),fail_closed_on_provider_error=True)
        manifest = {"schema_version":"1","model":config.model,"upstream_base_url":config.upstream_base_url,
            "max_output_tokens":131072,"retry_output_tokens":131072,"request_timeout_seconds":1800,
            "expected_upstream_model":config.model,"native_responses":True,"chat_profile":"deepseek",
            "fail_closed_on_provider_error":True,
            "pricing_profile":"deepseek-current","model_catalog_sha256":hashlib.sha256(catalog).hexdigest(),
            "protocol":"native_responses_passthrough","implementation_sha256":sha(Path(implementation.__file__)),
            "fake_mode":False,"rate_limit_retries":0,"budget_mux_paths":[str(g.path) for g in guards]}
        config.config_sha256 = _sha256_json(manifest)
        manifest["config_sha256"] = config.config_sha256
        write_json(directory/"manifest.json",manifest)
        server = ThreadingHTTPServer(("127.0.0.1",0),make_handler(config))
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        # run_task appends /tasks/<key>/v1; pass the server root, not /v1.
        bridge = {"url":f"http://127.0.0.1:{server.server_port}", "manifest":directory/"manifest.json"}
        try:
            yield bridge
        finally:
            server.shutdown()
            # Draining timed-out actor calls preserves real usage before the next phase.
            deadline = time.monotonic()+1810
            while config.active_requests and time.monotonic()<deadline:
                time.sleep(1)
            server.server_close()
            if config.active_requests:
                raise RuntimeError("Bridge still has unknown in-flight costs; stop without refund")

    def actor(self, item, bridge, skill, destination, timeout, stage, checkpoint=None, hint=None):
        require_design_review(getattr(self,"config",None))
        artifact = load_skill_artifact(skill)
        row = run_task(item_id=item["id"],source=Path(item["runtime_source"]),
            expected_source_sha256=item["source_sha256"],directory_group=item["directory_group"],
            out_dir=destination,skill_file=skill if artifact.source_dir is None else None,
            skill_dir=artifact.source_dir,expected_skill_sha256=artifact.artifact_sha256,
            codex_bin=Path(self.config["codex_bin"]),verus_bin=Path(self.config["verus_bin"]),
            lynette_bin=Path(self.config["lynette_bin"]),bridge_url=bridge["url"],
            bridge_ledger_path=self.ledger,bridge_manifest_path=bridge["manifest"],
            bridge_task_key=stage+"--"+item["id"],model="deepseek-v4-pro",reasoning_effort="max",
            timeout_seconds=timeout,model_context_window=1048576,run_stage=stage,
            initial_candidate_source=checkpoint,reference_proof_source=None,reference_kind="none",
            continuation_instructions=hint,actor_isolation_scratch_root=Path(self.config["scratch_root"]),
            actor_isolation_verus_root=Path(self.config["verus_bin"]).parent,
            actor_isolation_rust_root=self.source_root/"toolchain",
            actor_isolation_forbidden_paths=(self.repo,Path(os.environ["VERUS_SKILL_DATA_ROOT"]),
                                             self.source_root/"rollout",self.source_root/"train_items.json"))
        if row["fidelity"]=="V0_INVALID":
            raise RuntimeError("Actor/provider invalid, preserve and stop: "+stage+"--"+item["id"])
        return row

    def hint_branch(self, item, bridge, checkpoint=None):
        require_design_review(getattr(self,"config",None))
        ident = item["id"]
        if checkpoint is None:
            for point in self.selection[ident]["selected"]:
                self.hint_branch(item,bridge,point)
            return
        cp_id = checkpoint["checkpoint_id"]
        key = (ident,cp_id)
        contract = {"source_task":ident,"checkpoint_sha256":checkpoint["checkpoint_sha256"],
                    "evidence_ids":self.refs[ident]}
        # Checkpoint full code is represented by its hash in the complete source diff chain.
        binding = self.selection[ident]['report_binding']
        report_path = Path(binding['report_path'])
        if sha(report_path) != binding['report_sha256']:
            raise ValueError("Reviewed progress changed after selection")
        report = json.loads(report_path.read_text())
        packet = {"contract":contract,"checkpoint":checkpoint,"complete_original":packet_trace(self.traces[ident]),
                  "proof_progress":{"reference_kind":report['reference_kind'],
                                    "curve":report['curve'],"helper_scope":report.get('helper_scope'),
                                    "caveat":"Retrospective line overlap and verifier diagnostics are not semantic progress or causal point value."},
                  "checkpoint_code_instruction":"Reconstruct checkpoint_sha256 from the complete snapshot chain; do not infer it from final proof."}
        directory = self.root/"hints"/ident/cp_id
        write_json(directory/"contract.json",contract)
        if (directory/"hint.json").exists():
            # Reviewed recovery may reuse the already screened intervention exactly.
            hint = json.loads((directory/"hint.json").read_text())
        else:
            write_json(directory/"teacher_packet.json",shared_strings(packet,short_keys=True))
            recovered = Path(self.config['reused_hint_root'])/'hints'/ident/cp_id if self.config.get('reused_hint_root') else None
            if recovered is not None and (recovered/'hint.json').exists():
                if (json.loads((recovered/'teacher_packet.json').read_text()) != shared_strings(packet,short_keys=True)
                        or json.loads((recovered/'contract.json').read_text()) != contract):
                    raise ValueError("Recovered hint evidence changed; no automatic paid replacement")
                if ident+'/'+cp_id != getattr(self,'rejected_hint_key',None):
                    if json.loads((recovered/'screen.json').read_text()).get('automatic_screen_passed') is not True:
                        raise ValueError('Unreviewed rejected hint cannot be reused')
                    hint = json.loads((recovered/'hint.json').read_text())
                    write_json(directory/'reused_hint.json',{'source':str(recovered/'hint.json'),
                               'source_sha256':sha(recovered/'hint.json'),
                               'source_ledger_sha256':sha(recovered.parents[2]/'provider_calls.jsonl'),
                               'new_paid_call':False})
                else:
                    hint = None
            else:
                hint = None
            if hint is None:
                system = (self.prompts/"checkpoint_hints/hint_system.md").read_text()
                system += ('\nSelected checkpoint binding: copy the following literal exactly into '
                           'checkpoint_sha256, without rearranging characters or using another snapshot: '
                           +contract['checkpoint_sha256']+'\n')
                text,_ = self.teacher.call(system=system,
                             user=compact(shared_strings(packet,short_keys=True)),name="hint--"+ident+"--"+cp_id,cap=8192)
                hint = json.loads(text)
        spec = importlib.util.spec_from_file_location("campaign_hint_screen",self.repo/"skillopt-verusage/scripts/run_hint_augmentation.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        write_json(directory/"hint.json",hint)
        try:
            screen = module.screen_hint(hint,contract,json.loads((self.prompts/"checkpoint_hints/hint_output.schema.json").read_text()))
        except Exception as error:
            screen = {'automatic_screen_passed':False,'schema_and_evidence_valid':False,
                      'validation_error_type':type(error).__name__,'validation_error':str(error)}
        write_json(directory/"screen.json",screen)
        self.hints[key] = {"source_task":ident,"checkpoint_id":cp_id,"hint":hint,"screen":screen}
        if not screen["automatic_screen_passed"]:
            with self.lock: self.progress["hint_rejected"]+=1
            self.update(last_rejected_hint=ident+'/'+cp_id)
            raise RuntimeError("Hint needs review; refusing a missing continuation: "+ident+"/"+cp_id)
        candidate = directory/"checkpoint.rs"
        candidate.write_text(self.snapshots[ident][checkpoint["checkpoint_sha256"]])
        if sha(candidate)!=checkpoint["checkpoint_sha256"]:
            raise ValueError("Continuation checkpoint hash mismatch")
        prefix, prefix_sha = continuation_context(self.traces[ident],checkpoint)
        if prefix_sha != checkpoint["visible_prefix_sha256"]:
            raise ValueError("Visible prefix hash mismatch")
        hint_instructions = (self.prompts/"checkpoint_hints/actor_hint.md").read_text().replace("{{hint_text}}",hint["hint_text"])
        instructions = prefix + "\n\n" + hint_instructions
        actor_directory = self.root/"augmentation"/ident/cp_id
        fork_contract = {"source_task":ident,"checkpoint":checkpoint,
                         "visible_prefix_sha256":prefix_sha,"hint_sha256":sha(directory/"hint.json"),
                         "context_mode":"checkpoint_code_plus_visible_prefix_rehydration"}
        if (actor_directory/"result.json").exists():
            row = json.loads((actor_directory/"result.json").read_text())
            continuation = json.loads((actor_directory/"continuation_contract.json").read_text())
            if (json.loads((actor_directory/"fork_contract.json").read_text()) != fork_contract
                    or row.get("fidelity")=="V0_INVALID" or row.get("actor_model")!="deepseek-v4-pro"
                    or row.get("actor_reasoning_effort")!="max" or row.get("source_sha256")!=item["source_sha256"]
                    or row.get("skill_sha256")!=sha(self.seed)
                    or checkpoint["checkpoint_sha256"] not in compact(continuation)):
                raise ValueError("Existing continuation is not an accepted exact replay")
        else:
            # Runner admits only empty output directories. Persist the prelaunch
            # contract beside the hint, then attach it to completed actor evidence.
            write_json(directory/"fork_contract.pending.json",fork_contract)
            row = self.actor(item,bridge,self.seed,actor_directory,1800,"hint_actor_"+cp_id,candidate,instructions)
            write_json(actor_directory/"fork_contract.json",fork_contract)
        self.branches[key] = row
        with self.lock:
            self.progress["hint_completed"] += 1
        self.update(last_hint_source=ident)

    def card_groups(self, condition, items):
        if condition not in ("original_only","augmented"):
            raise ValueError("Unknown card-learning condition")
        groups = []
        for item in items:
            ident = item["id"]
            forks = []
            if condition == "augmented":
                for cp in self.selection[ident]["selected"]:
                    key = (ident,cp["checkpoint_id"])
                    if key not in self.branches:
                        raise RuntimeError("Missing continuation; no silent batch omission: "+str(key))
                    directory = self.root/"augmentation"/ident/cp["checkpoint_id"]
                    branch,_,_ = load_trace(directory)
                    contract = json.loads((directory/"fork_contract.json").read_text())
                    if contract["hint_sha256"] != sha(self.root/"hints"/ident/cp["checkpoint_id"]/"hint.json"):
                        raise ValueError("Hint artifact changed after continuation")
                    forks.append({"checkpoint":cp,"trace":branch,"hint":self.hints[key],
                                  "visible_prefix_sha256":contract["visible_prefix_sha256"]})
            groups.append(task_group(ident,self.traces[ident],forks,augmented=condition=="augmented",
                          forbidden_names=(item["task_id"],item["task_id"].split("__")[-1])))
        return groups

    def extract_batches(self, condition, items=None, suffix=""):
        require_design_review(getattr(self,"config",None))
        groups = self.card_groups(condition,self.items if items is None else items)
        replay_users = {}
        review_path = self.root/'recovered_card_requests.json'
        if review_path.exists() and suffix == '_remaining':
            for entry in json.loads(review_path.read_text())['replay_requests']:
                if entry['label'] != condition: continue
                request = self.root/entry['request_relative_path']
                user = json.loads(request.read_text())['input'][0]['content'][0]['text']
                pair = expand_strings(json.loads(user))['task_groups']
                replay_users[tuple(group['source_task'] for group in pair)] = user
        return update_cards(groups,self.seed,self.root/"banks"/(condition+suffix),self.extractors[condition],
                            workers=self.config.get("card_workers",2),admit=getattr(self.extractors[condition],'admit',None),
                            replay_users=replay_users)

    def learning(self):
        require_design_review(getattr(self,"config",None))
        from skillopt_verusage.campaign_native import learn_native
        original_groups = self.card_groups('original_only',self.items)
        pairs = paired_groups(original_groups)
        smoke_pair = min(pairs,key=lambda pair:len(compact(shared_strings(pair,short_keys=True)).encode()))
        smoke_ids = {group['source_task'] for group in smoke_pair}
        smoke_items = [item for item in self.items if item['id'] in smoke_ids]
        remaining = [item for item in self.items if item['id'] not in smoke_ids]
        write_json(self.root/'smoke_plan.json',{'source_tasks':sorted(smoke_ids),
                   'full_task_pairs':[[g['source_task'] for g in pair] for pair in pairs],
                   'selection':'smallest-full-original-packet-pair-no-outcome-selection',
                   'automatic_continuation_requires':'hash-bound qualitative acceptance receipt'})
        self.update(phase="smoke_hint_augmentation")
        with self.bridge("hint_bridge",self.augmentation_guards) as bridge:
            self.run_forks(smoke_items,bridge,2)
            self.check_costs()
            self.update(phase='smoke_card_extraction')
            smoke_banks = {}
            for condition in ('original_only','augmented'):
                bank = self.root/'banks'/(condition+'_smoke')/'cards.json'
                if getattr(self,'reused_smoke_parent',None) is not None:
                    audit_response(json.loads((bank.parent/'proposals/batch-000.json').read_text()),
                                   self.card_groups(condition,smoke_items))
                    smoke_banks[condition] = bank
                else:
                    smoke_banks[condition] = self.extract_batches(condition,smoke_items,'_smoke')
            if not json.loads(smoke_banks['augmented'].read_text())['cards']:
                raise RuntimeError("Smoke has no supported augmented cards; review before full expansion")
            self.check_costs()
            evidence = {'source_tasks':sorted(smoke_ids),'card_banks':{k:sha(p) for k,p in smoke_banks.items()},
                        'proposals':{k:sha(p.parent/'proposals/batch-000.json') for k,p in smoke_banks.items()},
                        'hints':{},'branches':{}}
            for item in smoke_items:
                for cp in self.selection[item['id']]['selected']:
                    key = item['id']+'/'+cp['checkpoint_id']
                    evidence['hints'][key] = sha(self.root/'hints'/item['id']/cp['checkpoint_id']/'hint.json')
                    evidence['branches'][key] = sha(self.root/'augmentation'/item['id']/cp['checkpoint_id']/'result.json')
            write_json(self.root/'smoke_evidence.json',evidence)
            self.update(phase='smoke_quality_review',smoke_evidence_sha256=_sha256_json(evidence))
            receipt_path = self.root/'smoke_review.json'
            if self.reused_smoke_parent is not None:
                old_receipt = json.loads((self.reused_smoke_parent/'smoke_review.json').read_text())
                audit_smoke_receipt(old_receipt,evidence)
                write_json(receipt_path,{**old_receipt,'reused_from':str(self.reused_smoke_parent),
                                        'no_new_card_calls':True})
            while not receipt_path.exists():
                time.sleep(1)
            audit_smoke_receipt(json.loads(receipt_path.read_text()),evidence)
            self.update(phase='hint_augmentation',smoke_accepted=True)
            self.run_forks(remaining,bridge,self.config.get('actor_workers',6))
        self.update(hint_completed=len(self.branches))
        self.check_costs()
        self.update(phase="native_skillopt")
        native = learn_native(self.results,self.predictions,self.seed,self.root/"artifacts/native",
                             self.extractors["native"],self.final_client)
        self.update(phase="card_extraction")
        artifacts = {"initial":self.seed,"native":native}
        for condition in ("original_only","augmented"):
            remaining_bank = self.extract_batches(condition,remaining,'_remaining')
            bank_path = merge_card_banks([smoke_banks[condition],remaining_bank],
                                        self.root/'banks'/condition/'cards.json')
            if json.loads(bank_path.read_text())["cards"]:
                artifacts[condition] = self.root/"artifacts"/condition
                build_bundle(bank_path,self.seed,artifacts[condition],autonomous_retrieval=True)
            else:
                artifacts[condition] = self.seed  # A legitimate no-update is not a reason to invent cards.
        frozen = {k:{"path":str(p),**load_skill_artifact(p).manifest()} for k,p in artifacts.items()}
        write_json(self.root/"frozen_artifacts.json",frozen)
        self.check_costs()
        self.update(phase="artifacts_frozen")
        evidence = {'frozen_artifacts_sha256':sha(self.root/'frozen_artifacts.json'),
                    'banks':{condition:sha(self.root/'banks'/condition/'cards.json')
                             for condition in ('original_only','augmented')}}
        write_json(self.root/'artifact_quality_evidence.json',evidence)
        self.update(phase='artifact_quality_review',artifact_evidence_sha256=_sha256_json(evidence))
        review_path = self.root/'artifact_review.json'
        while not review_path.exists():
            time.sleep(1)
        audit_smoke_receipt(json.loads(review_path.read_text()),evidence)
        self.update(phase='artifacts_quality_accepted')
        return artifacts,frozen

    def run_forks(self, items, bridge, workers):
        jobs = [(item,cp) for item in items for cp in self.selection[item['id']]['selected']]
        # Bounded waves stop new launches when a worker fails; no queued full campaign.
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for start in range(0,len(jobs),workers):
                futures = [pool.submit(self.hint_branch,item,bridge,cp) for item,cp in jobs[start:start+workers]]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as error:
                        self.update(active_wave_error_type=type(error).__name__,active_wave_error=str(error),
                                    stop_after_wave=True)
                        raise

    def check_costs(self):
        records = [json.loads(line) for line in self.ledger.read_text().splitlines() if line.strip()] if self.ledger.exists() else []
        attempts = [attempt for record in records for attempt in record.get("attempts",[])]
        unknown = sum(a.get("estimated_cost_usd") is None for a in attempts)
        parent_cost = 0
        approved_unknown = []
        parent = getattr(self,'config',{}).get('reused_hint_root')
        visited = set()
        while parent:
            parent = Path(parent).resolve()
            if parent in visited:
                raise ValueError('Cyclic recovery accounting chain')
            visited.add(parent)
            parent_records = [json.loads(line) for line in (parent/'provider_calls.jsonl').read_text().splitlines() if line.strip()]
            parent_attempts = [a for row in parent_records for a in row.get('attempts',[])]
            if any(a.get('estimated_cost_usd') is None for a in parent_attempts):
                audit = audit_actor_transport_repair if (parent/'actor_transport_repair_review.json').exists() else audit_transport_repair
                approved_unknown.append(audit(parent,parent_records))
            if (parent/'storage_repair_review.json').exists():
                approved_unknown.append(audit_card_storage_repair(parent,parent_records)['approved_missing_ledger_unknown'])
            parent_cost += sum(a['estimated_cost_usd'] for a in parent_attempts if a.get('estimated_cost_usd') is not None)
            parent = json.loads((parent/'config.json').read_text()).get('reused_hint_root')
        write_json(self.root/"cost_summary.json",{
            "expense_policy":"record_only","physical_new_cost_counted_once":"provider ledger",
            "estimated_new_cost_usd":sum(a.get("estimated_cost_usd") or 0 for a in attempts),
            "recovery_parent_physical_cost_usd":parent_cost,
            "estimated_campaign_cost_including_parent_usd":parent_cost+sum(a.get("estimated_cost_usd") or 0 for a in attempts),
            "approved_historical_unknown_requests":approved_unknown,
            "approved_historical_unknown_expense_upper_usd":sum(a['unknown_expense_upper_usd'] for a in approved_unknown),
            "known_estimate_plus_historical_unknown_upper_usd":parent_cost+sum(a.get("estimated_cost_usd") or 0 for a in attempts)+sum(a['unknown_expense_upper_usd'] for a in approved_unknown),
            "unknown_cost_requests":unknown,"unknown_cost_requests_scope":"current_run_only",
            "total_unknown_requests_including_approved_history":unknown+len(approved_unknown),
            "logical_original_upper_per_learning_method":ORIGINAL_COST_UPPER,
            "invoice_final":False,"caveat":"Known estimates exclude unresolved costs; historical unknown upper is separate, not settled usage. Expense is record-only; uncertainty is not a dollar gate. Incomplete or unbound execution evidence still requires repair. Not account invoice."})

    def evaluation(self, artifacts, frozen):
        require_design_review(getattr(self,"config",None))
        # Direct callers cannot bypass the quality gate or touch val before hashes.
        evidence = {'frozen_artifacts_sha256':sha(self.root/'frozen_artifacts.json'),
                    'banks':{condition:sha(self.root/'banks'/condition/'cards.json')
                             for condition in ('original_only','augmented')}}
        if (json.loads((self.root/'artifact_quality_evidence.json').read_text()) != evidence
                or json.loads((self.root/'frozen_artifacts.json').read_text()) != frozen
                or set(artifacts) != set(CONDITIONS) or set(frozen) != set(CONDITIONS)):
            raise RuntimeError('Frozen evaluation evidence changed before validation admission')
        audit_smoke_receipt(json.loads((self.root/'artifact_review.json').read_text()),evidence)
        for condition, path in artifacts.items():
            if str(path) != frozen[condition]['path']:
                raise ValueError('Frozen evaluation artifact path changed')
            load_skill_artifact(path,frozen[condition]['artifact_sha256'])
        # First access to validation inputs occurs only after quality/hash admission.
        manifest = self.repo/"fixed-claude-stratified-80-seed20260814/val/items.json"
        items = json.loads(manifest.read_text())
        if len(items)!=20 or len({x["id"] for x in items})!=20 or {x["id"] for x in items}&{x["id"] for x in self.items}:
            raise ValueError("Validation split contract mismatch")
        for item in items:
            source = self.repo/item["source_path"]
            if sha(source)!=item["source_sha256"]:
                raise ValueError("Validation source hash mismatch")
            target = self.root/"val_inputs"/item["directory_group"]/"unverified"/source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source,target)
            item["runtime_source"] = str(target)
        blocks = evaluation_schedule(items,CONDITIONS)
        write_json(self.root/"evaluation_schedule.json",{"manifest_sha256":sha(manifest),"blocks":blocks,
                "frozen_artifacts_sha256":sha(self.root/"frozen_artifacts.json"),"test_accessed":False})
        rows = []
        def run(job, bridge):
            repeat,condition,item = job
            load_skill_artifact(artifacts[condition],frozen[condition]["artifact_sha256"])
            target = self.root/"validation"/f"repeat_{repeat+1}"/condition/item["id"]
            row = self.actor(item,bridge,artifacts[condition],target,600,f"val_r{repeat+1}_{condition}")
            row.update(condition=condition,repetition=repeat+1)
            write_json(target/"retrieval_audit.json",audit_retrieval(target/"codex_events.raw.jsonl"))
            return row
        with self.bridge("evaluation_bridge",[]) as bridge:
            for repeat,block in enumerate(blocks,1):
                self.update(phase="validation",active_repetition=repeat,actor_workers=8)
                # Bounded waves prevent queued launches after a detected infrastructure error.
                with ThreadPoolExecutor(max_workers=8) as pool:
                    for start in range(0,len(block),8):
                        futures = [pool.submit(run,job,bridge) for job in block[start:start+8]]
                        for future in futures:
                            row = future.result()
                            rows.append(row)
                            write_json(self.root/"validation_rows.json",rows)
                            self.update(evaluation_completed=len(rows),last_condition=row["condition"])
                write_json(self.root/f"validation_repeat_{repeat}.json",aggregate(rows,CONDITIONS))
        self.check_costs()
        if len(rows)!=160:
            raise RuntimeError("Full evaluation coverage not complete")
        write_json(self.root/"validation_summary.json",aggregate(rows,CONDITIONS))
        self.update(phase="complete",test_accessed=False)

    def run(self):
        require_design_review(getattr(self,"config",None))
        self.preflight()
        self.prepare_selection()
        self.budgets()
        artifacts,frozen = self.learning()
        self.evaluation(artifacts,frozen)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,required=True)
    parser.add_argument("--preflight-only",action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if not args.preflight_only:
        require_design_review(config)
    campaign = Campaign(config)
    if not args.preflight_only:
        # A launched campaign is never implicitly restarted after a partial paid run.
        started = campaign.root/"started.json"
        if started.exists():
            raise RuntimeError("Campaign already started; audit before any replay")
        write_json(started,{"config_sha256":sha(args.config),"pid":os.getpid(),
                           "started_at_utc":datetime.now(timezone.utc).isoformat()})
    try:
        if args.preflight_only:
            campaign.preflight()
        else:
            campaign.run()
    except Exception as error:
        campaign.update(phase="stopped",error_type=type(error).__name__,error=str(error))
        traceback.print_exc()
        raise


if __name__=="__main__":
    main()
