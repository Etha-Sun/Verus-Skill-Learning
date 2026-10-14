"""Fresh validation20 grouped-B versus selective-v2-C evaluation; shared USD30 cap."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import fcntl
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess

import evaluate_card_organization as prior
import continue_card_organization_evaluation as continuation
from skill_evolution_pilot.actor_isolation import ActorIsolationConfig, build_isolated_actor_command
from skill_evolution_pilot.codex_runner import _codex_environment, build_prompt
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.guarded_deepseek import BudgetMux, write_json
from skillopt_verusage.skill_artifact import load_skill_artifact


REPO = Path(__file__).resolve().parents[1]
PROBE = Path(__file__).with_name('probe_selective_package.py')
LABELS = {'old': 'B-grouped-whole-reference-compact-v1', 'revised': 'C-selective-v2-with-routing-revision'}
FIELDS = ('prompt_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens', 'completion_tokens',
          'estimated_cost_usd', 'uniform_off_peak_estimated_usd')


def file_hashes(root):
    paths = list(root.rglob('*'))
    prior.require(not any(path.is_symlink() for path in paths), 'Symlink in frozen package')
    return {path.relative_to(root).as_posix(): prior.driver.sha(path) for path in paths if path.is_file()}


def expected_payload(bundle, payload):
    refs = prior.read(bundle / 'reference_manifest.json')
    family = refs[payload['id']]
    operation = payload.get('operation')
    if 'rules' not in family:
        prior.require(payload.get('reference_retrieval') == 1 and operation == 'read', 'Invalid B operation')
        content = (bundle / family['path']).read_text()
        rule_ids = []
        cards = family['source_card_ids']
        is_body = True
    else:
        prior.require(payload.get('reference_retrieval') == 2, 'Invalid C schema')
        rule_ids = payload['rule_ids']
        prior.require(isinstance(rule_ids, list) and len(set(rule_ids)) == len(rule_ids)
                      and set(rule_ids) <= set(family['rules']), 'Invalid selected rule IDs')
        if operation == 'index':
            prior.require(not rule_ids and len(family['rules']) > 1, 'Invalid index response')
            content = (bundle / family['path']).read_text()
        elif operation in ('read_full', 'read_single'):
            prior.require(rule_ids == list(family['rules']), 'Full read omitted rules')
            prior.require(operation != 'read_single' or len(rule_ids) == 1, 'Invalid singleton read')
            content = (bundle / family['full']['path']).read_text()
        elif operation == 'read_rules':
            prior.require(bool(rule_ids), 'Empty selected read')
            scope, links = family['shared_scope'], family['shared_links']
            parts = []
            for rule in rule_ids:
                part = (bundle / family['rules'][rule]['path']).read_text()
                prior.require(part.startswith(scope) and part.endswith(links), 'Shared context mismatch')
                parts.append(part[len(scope):len(part) - len(links) if links else len(part)])
            content = scope + ''.join(parts) + links
        else:
            raise ValueError('Unknown reference operation')
        cards = sorted({card for rule in rule_ids for card in family['rules'][rule]['source_card_ids']})
        is_body = operation != 'index'
        prior.require(payload.get('body_read') is is_body, 'Incorrect body-read flag')
    prior.require(payload.get('content') == content and payload.get('bytes') == len(content.encode())
                  and payload.get('sha256') == hashlib.sha256(content.encode()).hexdigest()
                  and sorted(payload.get('source_card_ids', [])) == sorted(cards), 'Payload does not match frozen package')
    return {'family_id': payload['id'], 'operation': operation, 'body_read': is_body,
            'rule_ids': rule_ids, 'source_card_ids': cards, 'content_bytes': len(content.encode()),
            'payload_integrity_valid': True}


def audit_events(raw_events, bundle):
    events, errors, direct = [], [], []
    command_count = 0
    command_output_bytes = 0
    for line_number, line in enumerate(raw_events.read_text().splitlines(), 1):
        try:
            event = json.loads(line)
        except ValueError:
            errors.append({'line': line_number, 'reason': 'Malformed event JSON'})
            continue
        item = event.get('item', {})
        if event.get('type') != 'item.completed' or item.get('type') != 'command_execution':
            continue
        command_count += 1
        output = str(item.get('aggregated_output', ''))
        command_output_bytes += len(output.encode())
        command = str(item.get('command', ''))
        if ('references' in command or 'reference_manifest.json' in command) and 'reference_read.py' not in command:
            direct.append({'item_id': item.get('id'), 'line': line_number, 'command': command,
                           'classification': 'possible listing/search/direct/partial access; manual extent audit required'})
        for output_line in output.splitlines():
            try:
                payload = json.loads(output_line)
            except ValueError:
                continue
            if not isinstance(payload, dict) or payload.get('reference_retrieval') not in (1, 2):
                continue
            if 'error' in payload:
                errors.append({'line': line_number, 'reason': 'Reader error response', 'item_id': item.get('id')})
                continue
            try:
                record = expected_payload(bundle, payload)
            except (ValueError, KeyError, TypeError, OSError) as error:
                errors.append({'line': line_number, 'reason': str(error), 'item_id': item.get('id')})
                continue
            events.append({**record, 'line': line_number, 'event_order': len(events), 'item_id': item.get('id'),
                           'serialized_payload_bytes': len(output_line.encode())})
    body = [event for event in events if event['body_read']]
    directories = [event for event in events if not event['body_read']]
    converted = sum(any(later['family_id'] == entry['family_id'] and later['event_order'] > entry['event_order']
                        for later in body) for entry in directories)
    return {'read_calls': 0, 'reference_read_calls': len(body), 'reference_directory_calls': len(directories),
            'reference_events': events, 'reader_errors_or_invalid_payloads': errors,
            'reference_read_ids': sorted({event['family_id'] for event in body}),
            'exposed_source_card_ids': sorted({card for event in body for card in event['source_card_ids']}),
            'helper_full_fallback_calls': sum(event['operation'] == 'read_full' for event in events),
            'helper_single_rule_calls': sum(event['operation'] == 'read_single' for event in events),
            'helper_selected_rule_calls': sum(event['operation'] == 'read_rules' for event in events),
            'helper_body_content_bytes': sum(event['content_bytes'] for event in body),
            'helper_directory_content_bytes': sum(event['content_bytes'] for event in directories),
            'helper_serialized_payload_bytes': sum(event['serialized_payload_bytes'] for event in events),
            'helper_command_count': len({event['item_id'] or event['line'] for event in events}),
            'command_count': command_count, 'command_output_bytes': command_output_bytes,
            'helper_directory_visits_with_later_helper_body': converted,
            'helper_directory_visits_without_later_helper_body': len(directories) - converted,
            'direct_reference_commands': direct,
            'directory_to_any_body_conversion_requires_manual_audit': bool(direct),
            'exposure_caveat': 'Verified helper payload exposure is not relevance or adoption. Directory counts exclude body reads. Direct commands are flags, not automatic reads; helper-only conversion is not overall abandonment.'}


def preflight(config, root):
    checks = []
    for condition in ('old', 'revised'):
        workspace = root / 'preflight' / condition
        shutil.copytree(root / 'bundles' / condition, workspace)
        shutil.copyfile(PROBE, workspace / 'probe_selective_package.py')
        hidden = [str(REPO / 'AGENTS.md'), config['env_file'], str(root / 'config.json')]
        write_json(workspace / 'probe_config.json', {'hidden': hidden,
            'library': str(Path(config['verus_bin']).parent / 'vstd'),
            'verus': config['verus_bin'], 'lynette': config['lynette_bin']})
        isolation = ActorIsolationConfig(Path(config['scratch_root']), Path(config['verus_bin']).parent,
            Path(config['rust_root']), 18136, (REPO, Path(config['env_file']), root / 'config.json', Path(config['data_root'])))
        command = build_isolated_actor_command(['/usr/bin/python3', 'probe_selective_package.py'], workspace=workspace,
            codex_bin=Path('/usr/bin/python3'), lynette_bin=Path(config['lynette_bin']), config=isolation)
        result = subprocess.run(command, env=_codex_environment(None), capture_output=True, text=True, timeout=240)
        record = {'condition': condition, 'returncode': result.returncode, 'stdout': result.stdout,
                  'stderr': result.stderr, 'isolation': isolation.manifest()}
        checks.append(record)
        write_json(root / 'preflight.json', {'paid_calls': 0, 'checks': checks})
        prior.require(result.returncode == 0, 'Isolation/package preflight failed')
        command = build_isolated_actor_command([config['codex_bin'], '--version'], workspace=workspace,
            codex_bin=Path(config['codex_bin']), lynette_bin=Path(config['lynette_bin']), config=isolation)
        result = subprocess.run(command, env=_codex_environment(None), capture_output=True, text=True, timeout=45)
        record['codex_version'] = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        write_json(root / 'preflight.json', {'paid_calls': 0, 'checks': checks})
        prior.require(result.returncode == 0 and '0.147.0' in result.stdout, 'Codex preflight failed')


def prepare(root, config_path, source):
    prior.require(not root.exists(), 'Fresh run directory required')
    config = prior.read(config_path)
    manifest = prior.read(source / 'candidate_manifest.json')
    prior.require(manifest['schema_version'] == 'selective-reference-candidate-v2', 'Expected reviewed v2 candidate')
    prior.require(file_hashes(source / 'candidate') == manifest['files'], 'Reviewed C package changed')
    prior.require(file_hashes(source / 'control') == manifest['source_files'], 'Reviewed B package changed')
    prior.require(Path(config['repo']).resolve() == REPO and config['allow_same_version_verus'], 'Wrong repo/tool approval')
    prior.require(Path(config['env_file']).resolve() == REPO.parent / 'Trace2Skill/.env.deepseek', 'Wrong credential file')
    for key in ('codex_bin', 'lynette_bin'):
        prior.require(prior.driver.sha(config[key]) == prior.HISTORICAL[key], 'Historical tool mismatch: ' + key)
    prior.require(prior.driver.sha(config['catalog']) == prior.HISTORICAL['models.json'], 'Catalog changed')
    verus_root = Path(config['verus_bin']).parent
    prior.require(prior.driver.sha(verus_root / 'rust_verify') == prior.LOCAL_RUST_VERIFY, 'Local verifier changed')
    version = subprocess.check_output([config['verus_bin'], '--version'], text=True)
    prior.require('0.2025.09.12.bb1f342' in version, 'Unexpected Verus version')
    root.mkdir(parents=True)
    for condition, folder in [('old', 'control'), ('revised', 'candidate')]:
        shutil.copytree(source / folder, root / 'bundles' / condition)
    (root / 'runtime').mkdir()
    shutil.copyfile(config['catalog'], root / 'runtime/models.json')
    config['source_root'] = str(root / 'runtime')
    write_json(root / 'config.json', config)
    (root / 'TASK.md').write_text(build_prompt(installed_library_root=verus_root / 'vstd'))
    prior.require(prior.driver.sha(root / 'TASK.md') == '5f32a1cc4ef90b5898ebef41eb20f22d3abaa732055fc20d4e097834afbd7e5d',
                  'Recommended TASK changed')
    preflight(config, root)
    items = prior.read(REPO / 'fixed-claude-stratified-80-seed20260814/val/items.json')
    prior.require(len(items) == 20, 'Expected fixed validation20')
    contract = prior.driver.prepare(root / 'config.json', root / 'bundles/old', root / 'bundles/revised', root,
        task_ids=tuple(item['id'] for item in items), installed_library_conditions=('old', 'revised'))
    evidence = [Path(__file__), PROBE, Path(prior.__file__), Path(continuation.__file__),
                REPO / 'scripts/recover_card_organization_evaluation.py', REPO / 'scripts/summarize_success_timeout_tokens.py',
                REPO / 'scripts/build_card_organization.py', root / 'TASK.md', root / 'preflight.json',
                source / 'candidate_manifest.json', source / 'routing_review_v2.json', source / 'rule_cues.json']
    for folder in ['skill-evolution-pilot/src', 'skillopt-verusage/src']:
        evidence.extend((REPO / folder).rglob('*.py'))
    evidence.extend(path for path in verus_root.rglob('*') if path.is_file())
    evidence.append(Path(config['rust_root']) / 'rustup/toolchains/1.88.0-x86_64-unknown-linux-gnu/bin/rustc')
    contract['input_hashes'].update({str(path.resolve()): prior.driver.sha(path) for path in evidence})
    contract.update(schema_version='selective-reference-validation20-v1', budget_usd=30,
        expected_episodes=40, repeats=1, arm_labels=LABELS, source_candidate_run=str(source),
        comparison='Unchanged grouped B versus selective-v2 C, including five navigation Scope corrections; user explicitly confirmed combined intervention.',
        model_context_window=1048576, max_output_tokens_per_request=131072,
        provider_request_timeout_seconds=1800, transport_retry=False,
        bootstrap={'resamples': 10000, 'seed': 20261006, 'unit': 'paired task'},
        expense_policy='New campaign USD30 shared cap, zero inherited charges; current failed/unknown calls retained conservatively. Prior campaign and construction excluded.',
        environment_deviation={'user_authorized': True, 'verus_version': version.strip(),
            'historical_rust_verify_sha256': prior.HISTORICAL['rust_verify'],
            'local_rust_verify_sha256': prior.LOCAL_RUST_VERIFY, 'same_in_both_arms': True},
        review_policy='User reviewed candidate and approved combined B/C comparison; coding-assistant hash-bound wiring review and offline/isolation checks, not an independent model review.',
        known_transport_limitations='Frozen transport unchanged: public capture may not preserve incomplete HTTP response body; provider failure stops dispatch, unknown charges reserved. No paid automatic retry.',
        caveat='Reused development validation20, one run per arm/task. Combined organization/navigation intervention, not pure granularity or causal retrieval adoption. Same-version local Verus differs from historical build; both arms share it.')
    write_json(root / 'validation_contract.json', contract)
    write_json(root / 'review_receipt.json', {'decision': 'APPROVE_WITH_NONBLOCKING_NOTES',
        'contract_sha256': prior.driver.sha(root / 'validation_contract.json'),
        'reviewer': 'coding-assistant; user-authorized combined B/C launch wiring review', 'paid_calls': 0,
        'blocking_issues': [], 'nonblocking_notes': [contract['caveat'], contract['known_transport_limitations']],
        'basis': 'Explicit user authorization: validation20 x2 x1, USD30, persistent server service; combined navigation change confirmed. Actual isolated tools and both package readers pass zero-API preflight.'})
    check(root)
    print(json.dumps({'prepared': True, 'episodes': 40, 'budget_usd': 30,
                      'contract_sha256': prior.driver.sha(root / 'validation_contract.json')}), flush=True)


def check(root):
    contract = prior.read(root / 'validation_contract.json')
    prior.require(contract['schema_version'] == 'selective-reference-validation20-v1', 'Wrong contract schema')
    prior.require(contract['budget_usd'] == 30 and contract['expected_episodes'] == 40, 'Unauthorized scope')
    prior.require(contract['arm_labels'] == LABELS, 'Wrong comparison')
    expected = [{'id': item['id'], 'condition': condition} for position, item in enumerate(contract['items'])
                for condition in (('old', 'revised') if position % 2 == 0 else ('revised', 'old'))]
    prior.require(len(contract['items']) == 20 and len({item['id'] for item in contract['items']}) == 20
                  and contract['schedule'] == expected, 'Wrong matrix/order')
    for key, value in {'model': 'deepseek-v4-pro', 'reasoning_effort': 'max', 'timeout_seconds': 600,
                        'workers': 2, 'installed_library_conditions': ['old', 'revised'], 'repeats': 1,
                        'model_context_window': 1048576, 'max_output_tokens_per_request': 131072}.items():
        prior.require(contract[key] == value, 'Fixed configuration changed: ' + key)
    prior.require(all(prior.driver.sha(path) == digest for path, digest in contract['input_hashes'].items()),
                  'Frozen evaluation input changed')
    for condition, path in contract['bundle_paths'].items():
        load_skill_artifact(Path(path), contract['artifacts'][condition]['artifact_sha256'])
    prior.driver.check_review(root / 'review_receipt.json', root / 'validation_contract.json')
    return contract


def guard(root):
    return SharedBudgetGuard(root / 'budget.json', approval_limit_usd=30, prior_spend_usd=0,
                             optimizer_reserve_usd=0, request_reserve_usd=0)


def paired_summary(rows):
    pairs = {}
    for row in rows:
        pair = pairs.setdefault(row['task_id'], {})
        prior.require(row['condition'] not in pair, 'Duplicate primary cell')
        pair[row['condition']] = row
    complete = [pair for pair in pairs.values() if set(pair) == {'old', 'revised'}]
    billing = [pair for pair in complete if all(row['settled_provider_complete'] for row in pair.values())]
    result = {'complete_task_pairs': len(complete), 'complete_billing_pairs': len(billing),
              'all_pairs_outcomes': dict(Counter(f"B{int(pair['old']['budgeted_dual_pass'])}_C{int(pair['revised']['budgeted_dual_pass'])}"
                                                 for pair in complete)),
              'complete_billing_totals': {arm: {field: sum(pair[arm][field] for pair in billing) for field in FIELDS}
                                          for arm in ('old', 'revised')}, 'bootstrap_C_minus_B': {}}
    for metric in ('budgeted_dual_pass', 'prompt_tokens', 'completion_tokens', 'uniform_off_peak_estimated_usd'):
        population = complete if metric == 'budgeted_dual_pass' else billing
        deltas = [pair['revised'][metric] - pair['old'][metric] for pair in population]
        if not deltas:
            continue
        rng = random.Random(20261006)
        sampled = sorted(sum(rng.choices(deltas, k=len(deltas))) / len(deltas) for _ in range(10000))
        result['bootstrap_C_minus_B'][metric] = {'n': len(deltas), 'mean_delta': sum(deltas) / len(deltas),
                                                'percentile_95': [sampled[249], sampled[9749]]}
    return result


def report(root):
    summary = prior.read(root / 'summary.json')
    rows = []
    for result in summary['rows']:
        row = continuation.result_dimensions(result)
        row.update(reference_directory_calls=result['retrieval']['reference_directory_calls'],
                   helper_body_content_bytes=result['retrieval']['helper_body_content_bytes'],
                   helper_directory_content_bytes=result['retrieval']['helper_directory_content_bytes'],
                   direct_access_flags=len(result['retrieval']['direct_reference_commands']))
        rows.append(row)
    with (root / 'episodes.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ['condition'])
        writer.writeheader()
        writer.writerows(rows)
    arms = {}
    for condition in LABELS:
        selected = [row for row in rows if row['condition'] == condition]
        arms[condition] = {'label': LABELS[condition], 'episodes': len(selected),
            'budgeted_dual_passes': sum(row['budgeted_dual_pass'] for row in selected),
            'V2_budgeted_dual_passes': sum(row['budgeted_dual_pass'] and row['fidelity'] == 'V2_TRACE' for row in selected),
            'outcomes': dict(Counter(row['outcome'] for row in selected)),
            'incomplete_provider_evidence': sum(not row['settled_provider_complete'] for row in selected),
            'editing_protocol_violations': sum(row['editing_protocol_violation'] for row in selected),
            'known_usage_totals_not_imputed': {field: sum(row[field] for row in selected) for field in FIELDS},
            'episodes_with_helper_body_reads': sum(row['helper_body_reads'] > 0 for row in selected),
            'episodes_with_directory_reads': sum(row['reference_directory_calls'] > 0 for row in selected),
            'helper_body_content_bytes': sum(row['helper_body_content_bytes'] for row in selected),
            'helper_directory_content_bytes': sum(row['helper_directory_content_bytes'] for row in selected),
            'episodes_needing_direct_access_audit': sum(row['direct_access_flags'] > 0 for row in selected)}
    write_json(root / 'report.json', {'episodes': len(rows), 'expected_episodes': 40, 'arms': arms,
        'paired': paired_summary(rows), 'failures': summary['failures'], 'budget': prior.read(root / 'budget.json'),
        'bridge_drained': summary['bridge_drained'], 'reviewed_inputs_unchanged': summary['reviewed_inputs_unchanged'],
        'caveat': summary['caveat'] + ' All-task proof and settled-provider validity are separate. Incomplete costs are not zero; paired resource summaries exclude incomplete billing pairs.'})


def run(root):
    contract = check(root)
    with (root / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior.require(not (root / 'episodes').exists(), 'Already launched; no replay')
        config = prior.read(root / 'config.json')
        prior.credentials(config)
        def audit(path):
            name = path.parent.name
            condition = 'old' if name.startswith('dev_old--') else 'revised' if name.startswith('dev_revised--') else None
            prior.require(condition is not None, 'Unknown actor condition')
            return audit_events(path, root / 'bundles' / condition)
        try:
            prior.driver.run(config, root, contract, expected_episodes=40,
                             budget_guard=BudgetMux([guard(root)]), retrieval_auditor=audit)
        finally:
            if (root / 'summary.json').exists():
                report(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run', 'report', 'check'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--source-run', type=Path)
    args = parser.parse_args()
    root = prior.builder.output_root(args.output)
    if args.phase == 'prepare':
        prior.require(args.config is not None and args.source_run is not None, 'Prepare requires config and reviewed source')
        prepare(root, args.config, prior.builder.output_root(args.source_run))
    elif args.phase == 'check':
        check(root)
        print('Frozen contract and packages verified')
    elif args.phase == 'report':
        report(root)
    else:
        run(root)


if __name__ == '__main__':
    main()
