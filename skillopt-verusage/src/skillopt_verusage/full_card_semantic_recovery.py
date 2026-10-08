"""Preserve a rejected full bank and regenerate only its contradicted batch."""
import hashlib
import json
from pathlib import Path

from skillopt_verusage.campaign_evidence import expand_strings, sha
from skillopt_verusage.card_storage_recovery import STORAGE_PATTERNS
from skillopt_verusage.codex_deepseek_bridge import _native_response_usage, _sha256_json
from skillopt_verusage.guarded_deepseek import response_text
from skillopt_verusage.native_card_update import SYSTEM, audit_response
from skillopt_verusage.skill_artifact import load_skill_artifact


BAD_CARD_HASH = 'fd98fbfd68efacaf218b6161a08c06378df79190ea10fadbe25b2253cca0310e'
SEMANTIC_PATTERNS = STORAGE_PATTERNS + (
    'banks/*_remaining/*', 'banks/augmented/*', 'artifacts/augmented/**/*',
    'frozen_artifacts.json', 'artifact_quality_evidence.json', 'artifact_review.json',
    'audits/trigger_pattern_review.json')


def audit(parent, records, audit_storage_ancestor):
    parent = Path(parent)
    review_path = parent/'full_card_semantic_repair_review.json'
    review = json.loads(review_path.read_text())
    progress = json.loads((parent/'progress.json').read_text())
    bindings = {'ledger_sha256':'provider_calls.jsonl', 'progress_sha256':'progress.json',
        'quality_evidence_sha256':'artifact_quality_evidence.json',
        'frozen_artifacts_sha256':'frozen_artifacts.json', 'rejection_sha256':'artifact_review.json',
        'trigger_review_sha256':'audits/trigger_pattern_review.json'}
    if (review.get('repair_authorized') is not True
            or review.get('classification') != 'full_card_semantic_repair'
            or review.get('bad_card_sha256') != BAD_CARD_HASH
            or review.get('bad_batch') != 'card-batch-006'
            or review.get('rejected_condition') != 'augmented'
            or any(review.get(k) != sha(parent/v) for k,v in bindings.items())
            or progress.get('phase') != 'stopped' or progress.get('error_type') != 'RuntimeError'
            or progress.get('error') != 'Smoke quality review missing, rejected or not bound to this evidence'
            or progress.get('hint_completed') != 114 or progress.get('hint_rejected') != 0
            or progress.get('evaluation_completed',0) != 0
            or len(records) != 14 or len({r['request_id'] for r in records}) != 14
            or any(a.get('estimated_cost_usd') is None for r in records for a in r.get('attempts',[]))
            or any((parent/p).exists() for p in ('val_inputs','validation'))):
        raise ValueError('Semantic recovery requires the exact full-bank quality rejection')
    paths = [p for pattern in SEMANTIC_PATTERNS for p in parent.glob(pattern)]
    inventory = {str(p.relative_to(parent)):sha(p) for p in paths if p.is_file()}
    if any(p.is_symlink() for p in paths) or inventory != review.get('preserved_hashes'):
        raise ValueError('Semantic recovery inventory changed')
    ancestor = Path(json.loads((parent/'config.json').read_text())['reused_hint_root'])
    ancestor_records = [json.loads(s) for s in (ancestor/'provider_calls.jsonl').read_text().splitlines() if s.strip()]
    ancestral = audit_storage_ancestor(ancestor,ancestor_records)
    if (json.loads((parent/'recovered_card_requests.json').read_text()) != ancestral
            or len(ancestral['replay_requests']) != 22):
        raise ValueError('Semantic recovery inherited receipt changed')
    for pattern in ('augmentation/*/*/result.json','hints/*/*/hint.json',
            'calls/native/**/*','calls/native_finalization/**/*','artifacts/native/**/*',
            'banks/*_smoke/**/*','banks/original_only/cards.json','artifacts/original_only/**/*','artifacts/initial.md'):
        current = {str(p.relative_to(parent)):sha(p) for p in parent.glob(pattern) if p.is_file()}
        previous = {str(p.relative_to(ancestor)):sha(p) for p in ancestor.glob(pattern) if p.is_file()}
        if current != previous:
            raise ValueError('Semantic recovery changed preserved actors, native or original-only artifacts')
    if (len(list(parent.glob('augmentation/*/*/result.json'))) != 114
            or len(list(parent.glob('hints/*/*/hint.json'))) != 114
            or len(list(parent.glob('calls/native/**/request.json'))) != 5
            or len(list(parent.glob('calls/native_finalization/**/request.json'))) != 1
            or sha(parent/'artifacts/native/SKILL.md') != ancestral['native_candidate_sha256']):
        raise ValueError('Semantic recovery source or native coverage changed')
    evidence = json.loads((parent/'artifact_quality_evidence.json').read_text())
    expected_evidence = {'frozen_artifacts_sha256':sha(parent/'frozen_artifacts.json'),
        'banks':{label:sha(parent/f'banks/{label}/cards.json') for label in ('original_only','augmented')}}
    rejection = json.loads((parent/'artifact_review.json').read_text())
    if (evidence != expected_evidence or rejection.get('accepted') is not False
            or not isinstance(rejection.get('observations'),str) or not rejection['observations'].strip()
            or rejection.get('evidence_sha256') != _sha256_json(evidence)):
        raise ValueError('Semantic recovery rejection is not bound to the frozen bank')
    frozen = json.loads((parent/'frozen_artifacts.json').read_text())
    artifacts = {'initial':parent/'artifacts/initial.md','native':parent/'artifacts/native/SKILL.md'}
    for label in ('original_only','augmented'):
        artifacts[label] = (parent/'artifacts'/label if json.loads((parent/f'banks/{label}/cards.json').read_text())['cards']
                            else artifacts['initial'])
    if frozen != {k:{'path':str(p),**load_skill_artifact(p).manifest()} for k,p in artifacts.items()}:
        raise ValueError('Semantic recovery frozen deployable artifacts changed')
    trigger = json.loads((parent/'audits/trigger_pattern_review.json').read_text())
    if (trigger.get('status') != 'confirmed_operative_contradiction'
            or trigger.get('affected_batch') != 6 or trigger.get('affected_card_zero_based_index') != 1
            or trigger.get('card_content_sha256') != BAD_CARD_HASH):
        raise ValueError('Semantic recovery lacks the exact operative contradiction review')
    trigger_hashes = trigger.get('preserved_hashes',{})
    for relative,digest in trigger_hashes.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or (parent/path).is_symlink() or sha(parent/path) != digest:
            raise ValueError('Semantic recovery counterexample changed or escaped the run')
    inherited = {e['request_relative_path'] for e in ancestral['replay_requests']}
    used, replay, pairs = set(), [], {}
    bad_directory = None
    for label in ('original_only','augmented'):
        requests = sorted(parent.glob(f'calls/{label}/card-batch-*/*/request.json'))
        proposals = sorted(parent.glob(f'banks/{label}_remaining/proposals/batch-*.json'))
        if (len(requests) != 18 or set(requests) != set(parent.glob(f'calls/{label}/**/request.json'))
                or {p.parent.parent.name for p in requests} != {f'card-batch-{n:03d}' for n in range(18)}
                or {p.name for p in proposals} != {f'batch-{n:03d}.json' for n in range(18)}):
            raise ValueError('Semantic recovery request or proposal coverage changed')
        responses = []
        for request in requests:
            directory = request.parent; name = directory.parent.name
            relative = str(request.relative_to(parent)); payload = json.loads(request.read_text())
            fingerprint = hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()
            if (directory.name != fingerprint
                    or json.loads((directory/'started.json').read_text()).get('request_sha256') != fingerprint
                    or payload.get('model') != 'deepseek-v4-pro' or payload.get('reasoning') != {'effort':'high'}
                    or payload.get('instructions') != SYSTEM or payload.get('max_output_tokens') != 16384
                    or payload.get('text') != {'format':{'type':'json_object'}} or payload.get('stream') is not False):
                raise ValueError('Semantic recovery request contract changed')
            packet = expand_strings(json.loads(payload['input'][0]['content'][0]['text']))
            groups = packet['task_groups']; ids = tuple(g['source_task'] for g in groups)
            if (len(groups) != 2 or len(set(ids)) != 2
                    or any(g['source_weight'] != 1 or len(g['trace_ids']) != (1 if label=='original_only' else 4) for g in groups)
                    or packet['contract'] != {'original_questions':2,'logical_traces':2 if label=='original_only' else 8,
                        'source_weights':{i:1 for i in ids}}):
                raise ValueError('Semantic recovery question grouping changed')
            if label == 'original_only': pairs[name] = ids
            elif pairs[name] != ids:
                raise ValueError('Semantic recovery compared different source questions')
            stored = json.loads((directory/'validated.json').read_text()); record = stored['record']
            raw = (directory/'response.raw').read_bytes(); usage,model,status = _native_response_usage(raw)
            attempts = record.get('attempts',[])
            if relative in inherited:
                if ({p.name:sha(p) for p in directory.iterdir() if p.is_file()}
                        != {p.name:sha(p) for p in (ancestor/relative).parent.iterdir() if p.is_file()}
                        or any(r['request_id'] == record.get('request_id') for r in records)):
                    raise ValueError('Semantic recovery inherited cache changed bytes or ownership')
            else:
                matches = [r for r in records if r['request_id'] == record.get('request_id')]
                if len(matches) != 1 or matches[0] != record or record['request_id'] in used:
                    raise ValueError('Semantic recovery reply lacks exact current metering')
                used.add(record['request_id'])
            if (record.get('model') != model or model != 'deepseek-v4-pro' or status != 'completed'
                    or record.get('task_id') != name or len(attempts) != 1
                    or attempts[0].get('finish_reason') != 'completed' or attempts[0].get('error')
                    or attempts[0].get('estimated_cost_usd') is None or attempts[0].get('max_tokens') != 16384
                    or usage != stored.get('usage') or usage != attempts[0].get('usage')
                    or response_text(raw) != stored['text'] or (directory/'error.json').exists()):
                raise ValueError('Semantic recovery raw response or usage changed')
            response = json.loads(stored['text']); audit_response(response,groups)
            proposal = parent/f'banks/{label}_remaining/proposals/batch-{name[-3:]}.json'
            if json.loads(proposal.read_text()) != response:
                raise ValueError('Semantic recovery cannot rewrite or filter paid proposals')
            responses.append(response)
            if label == 'augmented' and name == 'card-batch-006':
                if (len(response['cards']) < 2
                        or hashlib.sha256(response['cards'][1]['content'].encode()).hexdigest() != BAD_CARD_HASH
                        or trigger.get('request_id') != record['request_id']):
                    raise ValueError('Semantic recovery rejected card changed')
                bad_directory = directory
            else:
                replay.append({'label':label,'name':name,'request_relative_path':relative})
        bank = {'schema_version':'stage-card-bank-v1','cards':[]}; known, provenance = {}, {}
        for n,response in enumerate(responses):
            for card in response['cards']:
                key = hashlib.sha256(card['content'].encode()).hexdigest()
                if key not in known:
                    ident = f"card-{len(bank['cards'])+1:03d}"; known[key] = ident
                    bank['cards'].append({'id':ident,'content':card['content']}); provenance[ident] = []
                provenance[known[key]].append({'batch':n,**card})
        bank_root = parent/f'banks/{label}_remaining'
        if (json.loads((bank_root/'cards.json').read_text()) != bank
                or json.loads((bank_root/'provenance.json').read_text()) != provenance):
            raise ValueError('Semantic recovery subbank does not preserve all proposals')
        merged = {'schema_version':'stage-card-bank-v1','cards':[]}; known, provenance = {}, {}
        for source in (parent/f'banks/{label}_smoke/cards.json',bank_root/'cards.json'):
            source_bank = json.loads(source.read_text()); source_provenance = json.loads((source.parent/'provenance.json').read_text())
            for card in source_bank['cards']:
                key = hashlib.sha256(card['content'].encode()).hexdigest()
                if key not in known:
                    ident = f"card-{len(merged['cards'])+1:03d}"; known[key] = ident
                    merged['cards'].append({'id':ident,'content':card['content']}); provenance[ident] = []
                provenance[known[key]].extend({'native_bank':str(source),**entry} for entry in source_provenance[card['id']])
        stored_provenance = json.loads((parent/f'banks/{label}/provenance.json').read_text())
        # A copied original bank retains its ancestor's private merge-source paths.
        if label == 'original_only':
            source_paths = {str(ancestor/f'banks/{label}_{part}/cards.json'):
                str(parent/f'banks/{label}_{part}/cards.json') for part in ('smoke','remaining')}
            stored_provenance = {ident:[{**entry,'native_bank':source_paths.get(entry['native_bank'],entry['native_bank'])}
                for entry in entries] for ident,entries in stored_provenance.items()}
        if (json.loads((parent/f'banks/{label}/cards.json').read_text()) != merged
                or stored_provenance != provenance):
            raise ValueError('Semantic recovery merged bank changed strategy content or provenance')
    required_counter = [parent/'banks/augmented_remaining/proposals/batch-006.json',
        *[bad_directory/n for n in ('request.json','validated.json','response.raw')]]
    if (any(trigger_hashes.get(str(p.relative_to(parent))) != sha(p) for p in required_counter)
            or not any(p.endswith('-candidate.diff') and p.startswith('augmentation/') for p in trigger_hashes)
            or not any(p.endswith('-candidate.rs') and p.startswith('augmentation/') for p in trigger_hashes)
            or len({i for pair in pairs.values() for i in pair}) != 36
            or used != {r['request_id'] for r in records} or len(replay) != 35):
        raise ValueError('Semantic recovery cannot broaden the contradicted batch or omit settled calls')
    return {'source_run':str(parent),'review_sha256':sha(review_path),'ledger_sha256':review['ledger_sha256'],
        'native_candidate_sha256':ancestral['native_candidate_sha256'],'replay_requests':replay,
        'rejected_card_response_preserved':True,'rejected_batch':'card-batch-006',
        'approved_missing_ledger_unknown':ancestral['approved_missing_ledger_unknown']}
