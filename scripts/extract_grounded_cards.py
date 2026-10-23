"""Two-stage train-only extraction: immutable windows, reviewed observations, cards."""
from __future__ import annotations
import argparse
from collections import Counter
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil

import local_instantiation_extraction as old
import recover_local_instantiation as recovery
from skillopt_verusage.campaign_evidence import shared_strings
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json
from skillopt_verusage.budget_guard import SharedBudgetGuard, estimate_deepseek_cost

REPO, DOC = old.REPO, old.DOC
AUTH = {"basis": "User requested restarting extraction under the literature-informed evidence-check-synthesis design.",
        "total_usd": 15, "extraction_usd": 7, "evaluation_usd": 8,
        "evidence_calls": 4, "synthesis_calls": 2, "automatic_retry": False,
        "actor_calls_in_this_run": 0, "sealed_test_access": False}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def apply_diff(source, diff):
    if not diff:
        return source
    lines = source.splitlines(keepends=True)
    patch = diff.splitlines(keepends=True)
    result, cursor, i = [], 0, 0
    while i < len(patch):
        if not patch[i].startswith('@@ '):
            require(patch[i].startswith(('--- ', '+++ ')), 'Unexpected patch header')
            i += 1
            continue
        match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', patch[i])
        require(match is not None, 'Invalid diff hunk')
        start, count = int(match[1]), int(match[2] or 1)
        at = start if count == 0 else start - 1
        require(cursor <= at <= len(lines), 'Overlapping diff hunk')
        result.extend(lines[cursor:at]); cursor = at; i += 1
        used = added = 0
        while i < len(patch) and not patch[i].startswith('@@ '):
            line = patch[i]
            require(line[:1] in (' ', '+', '-'), 'Unsupported diff line')
            text = line[1:]
            if i + 1 < len(patch) and patch[i + 1].startswith('\\ No newline'):
                text = text.removesuffix('\n'); i += 1
            if line[0] in (' ', '-'):
                require(cursor < len(lines) and lines[cursor] == text, 'Patch context differs from source')
                cursor += 1; used += 1
            if line[0] in (' ', '+'):
                result.append(text); added += 1
            i += 1
        require(used == count and added == int(match[4] or 1), 'Diff hunk size mismatch')
    result.extend(lines[cursor:])
    return ''.join(result)


def traces(group):
    return [(group['original']['trace_id'], group['original']['complete_trace'])] + [
        (fork['trace_id'], fork['complete_suffix']) for fork in group['forks']]


def verus_command(command):
    try:
        parts = shlex.split(command)
        if len(parts) == 3 and parts[0] in ('/bin/bash', 'bash') and parts[1] in ('-lc', '-c'):
            parts = shlex.split(parts[2])
        return parts == ['./tools/run_verus.sh', 'candidate.rs']
    except ValueError:
        return False


def build_registry(group):
    registry = {'source_task': group['source_task'], 'traces': {}, 'records': {}, 'windows': {}, 'source_texts': {}}
    total_events = 0
    for number, (trace_id, trace) in enumerate(traces(group)):
        trace_key = f'T{number}'
        chain = trace['snapshots']['chain']
        source = trace['snapshots']['baseline']
        hashes = {}
        for i, node in enumerate(chain):
            if i:
                require(node['previous_candidate_sha256'] == digest(source), 'Broken source chain')
                source = apply_diff(source, node['diff_content'])
            require(digest(source) == node['candidate_sha256'], 'Reconstructed source hash mismatch')
            hashes[node['candidate_sha256']] = source
        registry['source_texts'].update(hashes)
        events = trace['events']
        total_events += len(events)
        checks, seen, excluded = [], set(), []
        for event in events:
            raw = event.get('data', {}).get('raw_codex_event', {})
            item = raw.get('item', {})
            if (raw.get('type') != 'item.completed' or item.get('type') != 'command_execution'
                    or not verus_command(item.get('command', '')) or item.get('id') in seen):
                continue
            seen.add(item.get('id'))
            h = event.get('candidate_sha256')
            if h not in hashes:
                excluded.append({'event_index': event['event_index'],
                    'reason': 'No matching reconstructed candidate snapshot'})
                continue
            key = f'{trace_key}C{len(checks):03d}'
            record = {'trace_key': trace_key, 'kind': 'completed_verus_command',
                'canonical_ref': f'{trace_id}/event:{event["event_index"]}',
                'event_index': event['event_index'], 'candidate_sha256': h,
                'exit_code': item.get('exit_code'), 'output': item.get('aggregated_output', '')}
            require(record['canonical_ref'] in group['evidence_ids'], 'Check reference absent from source manifest')
            registry['records'][key] = record
            checks.append(key)
        for before, after in zip(checks, checks[1:]):
            b, a = registry['records'][before], registry['records'][after]
            changes = [node for node in chain if b['event_index'] < node['event_index'] <= a['event_index'] + 2
                       and node['previous_candidate_sha256'] is not None
                       and node['previous_candidate_sha256'] != node['candidate_sha256']]
            current = b['candidate_sha256']
            for node in changes:
                require(node['previous_candidate_sha256'] == current, 'Window diff-chain discontinuity')
                current = node['candidate_sha256']
            require(current == a['candidate_sha256'], 'Window missing intervening change')
            window_key = f'{trace_key}W{len([w for w in registry["windows"].values() if w["trace_key"] == trace_key]):03d}'
            registry['windows'][window_key] = {'trace_key': trace_key, 'before_key': before, 'after_key': after,
                'change_nodes': changes, 'changed_snapshots': len(changes),
                'same_hash': b['candidate_sha256'] == a['candidate_sha256'],
                'net_diff': ''.join(difflib.unified_diff(hashes[b['candidate_sha256']].splitlines(True),
                    hashes[a['candidate_sha256']].splitlines(True), fromfile='before.rs', tofile='after.rs'))}
        registry['traces'][trace_key] = {'trace_id': trace_id, 'complete_event_count': len(events),
            'check_keys': checks, 'checks_indexed': len(checks),
            'excluded_direct_checks': excluded,
            'prefix': None if number == 0 else group['forks'][number - 1]['augmented_trace_recipe']}
    registry['coverage'] = {'complete_events': total_events, 'source_hashes_verified': len(registry['source_texts']),
        'eligible_checks': len(registry['records']), 'adjacent_windows': len(registry['windows']),
        'excluded_direct_checks': sum(len(t['excluded_direct_checks']) for t in registry['traces'].values()),
        'selection': 'All adjacent recognized direct Verus checks, including unsuccessful and same-hash transitions. Other commands remain in the complete source group.',
        'prefix': 'Original records retain their original keys; no events are renamed into fork namespaces.'}
    return registry


EVIDENCE_CONTRACT = '''Return exactly one JSON object with trace_analyses and observations.
trace_analyses: one object for each supplied trace_key, with exactly trace_key and observation (nonempty factual string).
observations: an array, empty allowed. Each object has exactly:
window_key (copy from the window index), before_quote (short exact substring of that window's before-check output),
after_quote (short exact substring of its after-check output), observation (the local transition),
remaining_obligations (string), confounding (string), inspection_guidance (conditional suggestion grounded in the transition).
Choose a window_key, never reproduce/reconstruct task IDs, branch names, hashes, event refs or edit lists.
The host already binds before/after/edit identities atomically to the selected window.
Use exact diagnostic text, not a paraphrase, for quotes; each quote must be 8-500 characters. Other fields are prose.
Quotes are private training-evidence metadata, not actor-facing card code.
One observation per selected window; do not invent windows or diagnose a mechanism from an unrelated lifecycle event.
Do not force a fixed observation count. Analyze all four traces, retain failed attempts/confounding, and admit uncertainty.
The index includes all eligible adjacent check windows, not just successes. Full training traces remain supplied.
'''

SYNTHESIS_CONTRACT = '''Return exactly {"cards": [...]}.
Each card has exactly content (one string), observation_keys (array of supplied opaque keys), limitations (array of strings).
Use all five ordered labels **Trigger:**, **Action:**, **Why:**, **Validate:**, **Avoid when:** in content.
No code fences, complete proof/quantifier/assertion templates, paths, task names or benchmark answers.
Only Action may contain at most two short optional inline TERM fragments; use prose when sufficient.
Source/branch/task IDs and canonical evidence_refs are inserted by the host, not generated by you.
Single-source/confounded support and causal uncertainty must appear in deployable content when material.
No required minimum card count. Empty cards is legitimate when no useful operation is supported.
The human-written EXPECTED_CARDS examples are NOT inputs. Derive your content from the admitted observations.
The outer v2 skeleton is fixed by the host: your guidance is entered at an unresolved local obligation,
binds objects/premises in that current scope, and returns to the same obligation after checking.
Do not generate, rewrite or fill the skeleton or prescribe a target solution.
'''


def guards(root):
    inherited = old.read(root / 'authorization.json')['inherited_cost_usd']
    return [SharedBudgetGuard(root / name, approval_limit_usd=cap, prior_spend_usd=inherited,
        optimizer_reserve_usd=0, request_reserve_usd=0) for name, cap in [('budget-total.json', 15), ('budget-extraction.json', 7)]]


def client(root, paid=False):
    return GuardedDeepSeek(root=root / 'calls', api_key=os.environ['DEEPSEEK_API_KEY'] if paid else 'offline',
        guards=guards(root) if paid else [], ledger=root / 'provider_calls.jsonl',
        tokenizer_path=root / 'tokenizer.json', tokenizer_sha256=old.TOKENIZER_SHA, capture_public_payloads=True)


def bound(payload):
    return estimate_deepseek_cost({'prompt_cache_miss_tokens': len(json.dumps(payload, ensure_ascii=False).encode()) + 8192,
                                  'completion_tokens': payload['max_output_tokens']}, 'deepseek-v4-pro', price_band='peak')


def check(root):
    contract = old.read(root / 'contract.json')
    require(contract['authorization'] == AUTH, 'Run authorization differs from implementation')
    require(all(old.sha(path) == h for path, h in contract['input_hashes'].items()), 'Frozen input changed')
    return contract


def prepare(root, parent):
    recovery.check(parent)
    state = old.read(parent / 'budget-total.json')
    require(not state['reservations'] and state['uncertain_requests'] == 0, 'Unsettled prior costs')
    require(not root.exists(), 'Fresh run root required')
    root.mkdir(parents=True)
    for name in ('config.json', 'source_receipt.json'):
        shutil.copyfile(parent / name, root / name)
    shutil.copytree(parent / 'learning/sources', root / 'sources')
    shutil.copyfile(parent / 'learning/tokenizer/tokenizer.json', root / 'tokenizer.json')
    shutil.copyfile(parent / 'learning/seed.md', root / 'seed.md')
    (root / 'prompts').mkdir()
    for source, dest in [('EVIDENCE_PROMPT.draft.txt', 'evidence.txt'), ('CARD_SYNTHESIS_PROMPT.draft.txt', 'synthesis.txt')]:
        text = (DOC / source).read_text().split('\n', 1)[1]
        if dest == 'evidence.txt':
            # Host, not model, supplies record identities and edit lists.
            start = text.index('For each observation, return:')
            end = text.index('If no actual failing/check/edit transition', start)
            text = text[:start] + 'Use the exact response contract after the training input. The host binds check/edit identities to window keys.\n\n' + text[end:]
        (root / 'prompts' / dest).write_text(text)
    inherited = state['prior_spend_usd'] + state['target_spend_usd']
    write_json(root / 'authorization.json', {**AUTH, 'inherited_cost_usd': inherited, 'prior_root': str(parent)})
    groups = [old.read(root / 'sources' / (ident + '.json')) for ident in old.TRAIN]
    require({g['source_task'] for g in groups} <= {x['id'] for x in old.read(REPO / 'fixed-claude-stratified-80-seed20260814/train/items.json')}, 'Non-training source')
    records = []
    transport = client(root)
    for group in groups:
        ident = group['source_task']
        registry = build_registry(group)
        write_json(root / 'registries' / (ident + '.json'), registry)
        # Full historical group retained, byte-equivalent after lossless expansion.
        index = {k: v for k, v in registry.items() if k != 'source_texts'}
        packet = shared_strings({'current_skill': (root / 'seed.md').read_text(), 'complete_training_group': group,
            'evidence_index': index}, short_keys=True)
        packet['output_contract'] = EVIDENCE_CONTRACT
        user = json.dumps(packet, ensure_ascii=False, separators=(',', ':'))
        system = (root / 'prompts/evidence.txt').read_text()
        request = {'system': system, 'user': user, 'cap': 16384}
        admission = transport.admit(**request)
        request_bound = bound(transport.payload(**request))
        write_json(root / 'requests' / ('evidence-' + ident + '.json'), request)
        records.append({'source_task': ident, 'request_bound_usd': request_bound, 'admission': admission, 'coverage': registry['coverage']})
    records.sort(key=lambda row: -row['request_bound_usd'])
    pairs = [[g['source_task'] for g in pair] for pair in old.native.paired_groups(groups)]
    paths = [p for p in root.rglob('*') if p.is_file()]
    paths += [Path(__file__), Path(old.__file__), parent / 'budget-total.json', parent / 'learning/failure_audit.json']
    paths += [REPO / 'skillopt-verusage/src/skillopt_verusage' / (name + '.py') for name in
              ('guarded_deepseek', 'budget_guard', 'codex_deepseek_bridge', 'text_context', 'campaign_evidence', 'native_card_update')]
    paths += [REPO / 'fixed-claude-stratified-80-seed20260814/train/items.json']
    write_json(root / 'contract.json', {'authorization': AUTH, 'stage1': records, 'stage2_pairs': pairs,
        'stage2_gate': 'All stage1 observations must be programmatically checked and manually reviewed before synthesis.',
        'full_group_evidence_preserved': True, 'current78_modified': False,
        'native_reflect_deviation': 'Standalone staged extraction adapter; not the original one-call native Reflect sink or a controlled comparison with retained old cards.',
        'input_hashes': {str(p.resolve()): old.sha(p) for p in paths}})
    first = records[0]['request_bound_usd']
    print(json.dumps({'prepared': True, 'calls': '4 evidence + 2 synthesis', 'inherited_usd': inherited,
        'largest_request_reservation': first, 'first_request_fits': inherited + first <= 7,
        'tasks': [{k: r[k] for k in ('source_task', 'request_bound_usd', 'coverage')} for r in records]}, indent=2), flush=True)


def validate_observations(value, registry):
    require(set(value) == {'trace_analyses', 'observations'}, 'Evidence response fields mismatch')
    analyses = value['trace_analyses']
    require(isinstance(analyses, list) and Counter(a.get('trace_key') for a in analyses) == Counter(registry['traces'].keys()), 'Incomplete trace coverage')
    require(all(set(a) == {'trace_key', 'observation'} and isinstance(a['observation'], str) and a['observation'].strip() for a in analyses), 'Invalid trace analysis')
    require(isinstance(value['observations'], list), 'Observations must be a list')
    seen, admitted = set(), []
    for observation in value['observations']:
        require(set(observation) == {'window_key', 'before_quote', 'after_quote', 'observation', 'remaining_obligations', 'confounding', 'inspection_guidance'}, 'Observation fields mismatch')
        key = observation['window_key']
        require(key in registry['windows'] and key not in seen, 'Unknown or duplicate window')
        seen.add(key); window = registry['windows'][key]
        before, after = [registry['records'][window[k]] for k in ('before_key', 'after_key')]
        for label, record in [('before_quote', before), ('after_quote', after)]:
            quote = observation[label]
            require(isinstance(quote, str) and 8 <= len(quote) <= 500 and quote in record['output'], 'Diagnostic quote does not match selected check')
        require(all(isinstance(observation[k], str) and observation[k].strip() for k in ('observation', 'remaining_obligations', 'confounding', 'inspection_guidance')), 'Missing factual observation')
        refs = [before['canonical_ref'], after['canonical_ref']]
        trace = registry['traces'][window['trace_key']]['trace_id']
        refs += [trace + '/snapshot:' + n['candidate_sha256'] for n in window['change_nodes']]
        admitted.append({'observation_key': registry['source_task'] + '/' + key, 'model_observation': observation,
            'source_task': registry['source_task'], 'trace_id': trace, 'evidence_refs': sorted(set(refs)),
            'window': window, 'before_check': before, 'after_check': after,
            'before_source': registry['source_texts'][before['candidate_sha256']],
            'after_source': registry['source_texts'][after['candidate_sha256']],
            'semantic_review_required': True})
    return admitted


def run_evidence(root):
    contract = check(root)
    with (root / 'evidence.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (root / 'evidence-started.json').exists(), 'No automatic evidence restart')
        write_json(root / 'evidence-started.json', {'authorization': AUTH})
        old.prior.credentials(old.read(root / 'config.json'))
        transport = client(root, True)
        try:
            for row in contract['stage1']:
                ident = row['source_task']
                print('Evidence extraction: ' + ident, flush=True)
                text, usage = transport.call(**old.read(root / 'requests' / ('evidence-' + ident + '.json')), name='evidence-' + ident)
                value = json.loads(text)
                write_json(root / 'observations' / (ident + '.raw.json'), value)
                admitted = validate_observations(value, old.read(root / 'registries' / (ident + '.json')))
                write_json(root / 'observations' / (ident + '.checked.json'), admitted)
                print(f'Checked {len(admitted)} observations; semantic review pending', flush=True)
            write_json(root / 'evidence-completed.json', {'paid_requests': 4, 'status': 'awaiting_manual_semantic_review'})
        except Exception as error:
            write_json(root / 'evidence-stopped.json', {'type': type(error).__name__, 'reason': str(error), 'automatic_retry': False})
            raise


def prepare_synthesis(root):
    contract = check(root)
    require((root / 'evidence-completed.json').exists(), 'Evidence incomplete')
    review_path = root / 'evidence-review.json'
    review = old.read(review_path)
    require(review['complete'] is True and not (root / 'synthesis-contract.json').exists(), 'Manual review missing or already sealed')
    observations = {}
    for path in (root / 'observations').glob('*.checked.json'):
        for value in old.read(path):
            observations[value['observation_key']] = value
    require(set(review['decisions']) == set(observations), 'Every observation requires a decision')
    accepted = {}
    for key, decision in review['decisions'].items():
        require(decision['decision'] in ('accept', 'reject') and decision['reason'], 'Missing review reason')
        require(decision['observation_sha256'] == digest(json.dumps(observations[key], sort_keys=True, ensure_ascii=False)), 'Reviewed observation changed')
        if decision['decision'] == 'accept':
            accepted[key] = observations[key]
    calls = []
    for i, pair in enumerate(contract['stage2_pairs']):
        selected = {k: v for k, v in accepted.items() if v['source_task'] in pair}
        require(selected, 'No admitted observations for pair; report coverage gap')
        packet = shared_strings({'admitted_observations': selected, 'instruction': 'Only these host-reviewed observations may support cards.'}, short_keys=True)
        packet['output_contract'] = SYNTHESIS_CONTRACT
        request = {'system': (root / 'prompts/synthesis.txt').read_text(), 'user': json.dumps(packet, ensure_ascii=False, separators=(',', ':')), 'cap': 16384}
        transport = client(root)
        admission = transport.admit(**request)
        write_json(root / 'requests' / f'synthesis-{i}.json', request)
        write_json(root / 'synthesis-inputs' / f'batch-{i}.json', selected)
        calls.append({'batch': i, 'source_tasks': pair, 'request_bound_usd': bound(transport.payload(**request)), 'admission': admission})
    paths = [review_path, root / 'contract.json'] + list((root / 'observations').glob('*.json')) + list((root / 'synthesis-inputs').glob('*.json')) + list((root / 'requests').glob('synthesis-*.json'))
    write_json(root / 'synthesis-contract.json', {'calls': calls, 'input_hashes': {str(p): old.sha(p) for p in paths}})
    print('Synthesis frozen after semantic review; zero synthesis calls so far', flush=True)


def validate_cards(value, observations, groups):
    require(set(value) == {'cards'} and isinstance(value['cards'], list), 'Cards-only synthesis required')
    proposals = []
    for card in value['cards']:
        require(set(card) == {'content', 'observation_keys', 'limitations'}, 'Synthesis card fields mismatch')
        keys = card['observation_keys']
        require(isinstance(keys, list) and keys and len(set(keys)) == len(keys) and set(keys) <= set(observations), 'Unknown or duplicate observation key')
        proposals.append({'content': card['content'], 'limitations': card['limitations'],
            'evidence_refs': sorted({ref for key in keys for ref in observations[key]['evidence_refs']}),
            'source_tasks': sorted({observations[key]['source_task'] for key in keys})})
    audit = {'trace_analyses': [{'trace_id': tid, 'observation': 'Covered in the separate evidence stage; canonical provenance host-rendered.'} for g in groups for tid in g['trace_ids']], 'cards': proposals}
    old.representation_audit(audit, groups, 'revised')
    return proposals


def run_synthesis(root):
    check(root)
    contract = old.read(root / 'synthesis-contract.json')
    require(all(old.sha(p) == h for p, h in contract['input_hashes'].items()), 'Synthesis reviewed input changed')
    with (root / 'synthesis.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (root / 'synthesis-started.json').exists(), 'No automatic synthesis restart')
        write_json(root / 'synthesis-started.json', {'authorization': AUTH})
        old.prior.credentials(old.read(root / 'config.json')); transport = client(root, True)
        bank, provenance, known = [], {}, {}
        try:
            for call in contract['calls']:
                i = call['batch']
                print('Card synthesis batch ' + str(i), flush=True)
                text, usage = transport.call(**old.read(root / 'requests' / f'synthesis-{i}.json'), name=f'synthesis-{i}')
                value = json.loads(text); write_json(root / 'proposals' / f'batch-{i}.raw.json', value)
                groups = [old.read(root / 'sources' / (ident + '.json')) for ident in call['source_tasks']]
                observations = old.read(root / 'synthesis-inputs' / f'batch-{i}.json')
                proposals = validate_cards(value, observations, groups)
                write_json(root / 'proposals' / f'batch-{i}.checked.json', proposals)
                for card in proposals:
                    h = digest(card['content'])
                    if h not in known:
                        ident = f'card-{len(bank)+1:03d}'; known[h] = ident
                        bank.append({'id': ident, 'content': card['content']}); provenance[ident] = []
                    provenance[known[h]].append(card)
            write_json(root / 'cards.json', {'schema_version': 'stage-card-bank-v1', 'cards': bank})
            write_json(root / 'provenance.json', provenance)
            write_json(root / 'completed.json', {'cards': len(bank), 'utility_established': False, 'manual_card_review_required': True, 'actor_episodes': 0})
        except Exception as error:
            write_json(root / 'synthesis-stopped.json', {'type': type(error).__name__, 'reason': str(error), 'automatic_retry': False})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'check', 'evidence', 'prepare-synthesis', 'synthesis'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prior', type=Path)
    args = parser.parse_args(); root = old.prior.builder.output_root(args.output)
    if args.phase == 'prepare': prepare(root, args.prior)
    else: {'check': check, 'evidence': run_evidence, 'prepare-synthesis': prepare_synthesis, 'synthesis': run_synthesis}[args.phase](root)


if __name__ == '__main__':
    main()
