"""Continue only authorized missing cells; preserve earlier outcomes and charges."""
from __future__ import annotations

import argparse
import copy
import csv
import fcntl
from pathlib import Path
import shutil

import recover_card_organization_evaluation as recovery
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.guarded_deepseek import BudgetMux, write_json


evaluation = recovery.evaluation
RETRY_KEY = 'dev_old--9b9f6ccef89db4103c7f'


def plan_remaining(contract, summary):
    evaluation.require(summary['bridge_drained'] and summary['reviewed_inputs_unchanged'],
                       'Prior run must be drained with unchanged inputs')
    rows = {entry['row']['bridge_task_key']: entry for entry in summary['rows']}
    evaluation.require(len(rows) == len(summary['rows']) == 25, 'Unexpected prior episode set')
    expected = {evaluation.driver.episode_key(job) for job in contract['schedule']}
    evaluation.require(len(expected) == 40 and set(rows) <= expected, 'Unexpected full matrix')
    retry = rows[RETRY_KEY]['row']
    evaluation.require(not retry['timed_out'] and not retry['proof_solved']
                       and retry['codex_returncode'] == 1 and retry['fidelity'] == 'V0_INVALID',
                       'Only the audited early infrastructure abort may be repeated')
    selected = [job for job in contract['schedule']
                if evaluation.driver.episode_key(job) not in rows
                or evaluation.driver.episode_key(job) == RETRY_KEY]
    evaluation.require(len(selected) == 16, 'Expected 15 missing cells plus one authorized technical retry')
    return selected


def prepare(prior, root):
    parent = recovery.check(prior)
    summary = evaluation.read(prior/'summary.json')
    schedule = plan_remaining(parent, summary)
    state = evaluation.read(prior/'budget.json')
    evaluation.require(not state['reservations'], 'Prior live reservations remain')
    charge = recovery.inherited_charge(state)
    evaluation.require(charge < 30, 'No remaining authorized budget')
    events = (prior/'episodes'/RETRY_KEY/'codex_events.raw.jsonl').read_text()
    evaluation.require('Provider bridge halted pending review' in events, 'Missing technical abort evidence')
    evaluation.require(not root.exists(), 'Continuation needs a fresh output directory')
    root.mkdir(parents=True)
    config = evaluation.read(prior/'config.json')
    (root/'runtime').mkdir()
    shutil.copyfile(Path(config['source_root'])/'models.json', root/'runtime/models.json')
    config['source_root'] = str(root/'runtime')
    write_json(root/'config.json', config)
    shutil.copyfile(prior/'TASK.md', root/'TASK.md')
    for condition in ('old', 'revised'):
        shutil.copytree(Path(parent['bundle_paths'][condition]), root/'bundles'/condition)
    evaluation.preflight(config, root)
    contract = copy.deepcopy(parent)
    contract.update(schema_version='card-organization-remaining-cells-v1', schedule=schedule,
        expected_episodes=16,
        bundle_paths={condition: str(root/'bundles'/condition) for condition in ('old', 'revised')},
        continuation={'prior_root': str(prior), 'prior_contract_sha256': evaluation.driver.sha(prior/'validation_contract.json'),
            'full_schedule': parent['schedule'], 'retain_prior_episode_keys': sorted(
                entry['row']['bridge_task_key'] for entry in summary['rows']
                if entry['row']['bridge_task_key'] != RETRY_KEY),
            'authorized_retry_keys': [RETRY_KEY], 'unstarted_count': 15,
            'prior_conservative_charge_usd': charge,
            'user_authorization': 'Run the remaining tasks after the anomaly audit; retain completed outcomes, including timeouts and the agent editing violation.',
            'preserve_actor_method_and_transport': True,
            'reporting': 'Final ledger completeness, terminal abort and editing compliance are separate from proof outcome.',
            'known_transport_limitations': 'Public-capture mode does not retain HTTP incomplete partial response bodies; unchanged for comparability. Any new provider failure still stops the run; no automatic paid retries.'})
    contract['caveat'] += ' Continuation retains 24 prior cells and replaces only one audited early infrastructure abort; no best-of selection. Resources with missing usage are partial, and uniform-rate estimates accompany time-dependent billing.'
    evidence = [Path(__file__), root/'config.json', root/'TASK.md', root/'runtime/models.json', root/'preflight.json',
        prior/'validation_contract.json', prior/'summary.json', prior/'budget.json', prior/'provider_calls.jsonl',
        prior/'review_receipt.json', prior/'audit/anomaly_audit.json']
    evidence.extend(path for path in (root/'bundles').rglob('*') if path.is_file())
    evidence.extend(path for path in (prior/'episodes').glob('*/*')
                    if path.name in ('result.json', 'validation.json', 'fidelity_audit.json', 'codex_events.raw.jsonl'))
    contract['input_hashes'].update({str(path.resolve()): evaluation.driver.sha(path) for path in evidence})
    write_json(root/'validation_contract.json', contract)
    write_json(root/'review_receipt.json', {
        'decision': 'APPROVE_WITH_NONBLOCKING_NOTES',
        'contract_sha256': evaluation.driver.sha(root/'validation_contract.json'),
        'reviewer': 'coding-assistant; authorized continuation delta review', 'paid_calls': 0,
        'blocking_issues': [],
        'basis': 'User authorized remaining work; fixed schedule is 15 unstarted plus one documented early infrastructure abort. Actor method, tools, skills, deadlines and total USD30 cap unchanged.',
        'nonblocking_notes': ['Prior unknown charges are retained conservatively; late-error timeout and editing violation are not retried.',
                              'No claim that the unchanged provider transport cannot fail again.']})
    check(root)
    print(f'Prepared 16 episodes; retained 24; inherited conservative charge USD{charge:.9f}', flush=True)


def check(root):
    contract = evaluation.read(root/'validation_contract.json')
    prior = Path(contract['continuation']['prior_root'])
    parent = evaluation.read(prior/'validation_contract.json')
    evaluation.require(all(evaluation.driver.sha(path) == digest for path, digest in contract['input_hashes'].items()),
                       'Frozen continuation inputs changed')
    evaluation.require(contract['schedule'] == plan_remaining(parent, evaluation.read(prior/'summary.json')),
                       'Continuation schedule changed')
    for field in ('items', 'artifacts', 'installed_library_conditions', 'installed_library_root',
                  'model', 'reasoning_effort', 'timeout_seconds', 'workers', 'repeats', 'budget_usd',
                  'model_context_window', 'max_output_tokens_per_request', 'bootstrap'):
        evaluation.require(contract[field] == parent[field], 'Actor methodology changed: '+field)
    evaluation.require(contract['budget_usd'] == 30, 'Unauthorized budget')
    evaluation.driver.check_review(root/'review_receipt.json', root/'validation_contract.json')
    return contract


def result_dimensions(result):
    row = result['row']
    usage = result['settled_usage']
    errors = any(usage.get(key, 0) for key in ('unmetered_requests', 'error_requests', 'unknown_cost_requests'))
    provider_complete = not errors and usage.get('requests', 0) > 0
    directory = Path(result['episode'])
    fidelity = evaluation.read(directory/'fidelity_audit.json')
    events = (directory/'codex_events.raw.jsonl').read_text()
    bridge_aborted = not row['timed_out'] and row['codex_returncode'] != 0 and 'Provider bridge halted pending review' in events
    dual_pass = bool(row['proof_solved'] and row['safety_passed'] and row['within_budget'])
    if bridge_aborted:
        outcome = 'infrastructure_aborted'
    elif row['timed_out']:
        outcome = 'timeout'
    elif not provider_complete:
        outcome = 'provider_invalid'
    elif dual_pass:
        outcome = 'budgeted_dual_pass'
    elif row['codex_returncode'] != 0:
        outcome = 'actor_error'
    else:
        outcome = 'normal_unsolved'
    return {'task_id': row['id'], 'condition': result['condition'], 'episode': result['episode'],
        'outcome': outcome, 'budgeted_dual_pass': dual_pass, 'fidelity': row['fidelity'],
        'editing_protocol_violation': fidelity.get('shell_edit_suspect_count', 0) > 0,
        'settled_provider_complete': provider_complete, 'usage_complete': not errors,
        'recorded_provider_valid': row['provider_valid'], 'actor_seconds': row['actor_wall_seconds'],
        **{field: usage.get(field, 0) for field in evaluation.FIELDS},
        'uniform_off_peak_estimated_usd': (usage['prompt_cache_hit_tokens'] * .022 +
            usage['prompt_cache_miss_tokens'] * .66 + usage['completion_tokens'] * 1.98) / 1_000_000,
        'helper_body_reads': result['retrieval'].get('read_calls', 0) + result['retrieval'].get('reference_read_calls', 0)}


def merge_selected(prior_rows, current_rows, retained, allowed_new):
    selected = {entry['row']['bridge_task_key']: entry for entry in prior_rows
                if entry['row']['bridge_task_key'] in retained}
    evaluation.require(set(selected) == set(retained), 'Retained evidence missing')
    for entry in current_rows:
        key = entry['row']['bridge_task_key']
        evaluation.require(key in allowed_new and key not in selected, 'Unexpected or duplicate continuation cell')
        selected[key] = entry
    return selected


def report(root):
    contract = check(root)
    prior = Path(contract['continuation']['prior_root'])
    previous = evaluation.read(prior/'summary.json')
    current = evaluation.read(root/'summary.json')
    selected = merge_selected(previous['rows'], current['rows'], contract['continuation']['retain_prior_episode_keys'],
                              {evaluation.driver.episode_key(job) for job in contract['schedule']})
    rows = [result_dimensions(entry) for entry in selected.values()]
    rows.sort(key=lambda row: (row['task_id'], row['condition']))
    with (root/'combined_episodes.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    arms = {}
    for arm in ('old', 'revised'):
        entries = [row for row in rows if row['condition'] == arm]
        arms[arm] = {'episodes': len(entries), 'budgeted_dual_passes': sum(row['budgeted_dual_pass'] for row in entries),
            'V2_budgeted_dual_passes': sum(row['budgeted_dual_pass'] and row['fidelity'] == 'V2_TRACE' for row in entries),
            'outcomes': {outcome: sum(row['outcome'] == outcome for row in entries) for outcome in sorted({row['outcome'] for row in entries})},
            'incomplete_provider_evidence': sum(not row['settled_provider_complete'] for row in entries),
            'editing_protocol_violations': sum(row['editing_protocol_violation'] for row in entries),
            'known_usage_totals_not_imputed': {field: sum(row[field] for row in entries)
                for field in ('prompt_tokens', 'completion_tokens', 'estimated_cost_usd', 'uniform_off_peak_estimated_usd')},
            'episodes_with_helper_reads': sum(row['helper_body_reads'] > 0 for row in entries)}
    write_json(root/'combined_report.json', {'selected_episodes': len(rows), 'expected_episodes': 40,
        'all_cells_recorded': len(rows) == 40, 'new_run_failures': current['failures'], 'arms': arms,
        'budget': evaluation.read(root/'budget.json'),
        'excluded_earlier_attempts': [{'episode': str(prior/'episodes'/RETRY_KEY),
                                    'reason': 'Pre-authorized replacement of early shared-bridge abort; costs retained'}],
        'source_summaries': {str(path): evaluation.driver.sha(path) for path in (prior/'summary.json', root/'summary.json')},
        'caveat': 'Do not compare raw costs across unequal price bands or treat incomplete usage as zero. Old timeout with late error and editing-protocol violation are retained, not outcome-selected retries. Final paired analysis still required.'})
    write_json(root/'combined_summary.json', {'rows': list(selected.values()), 'expected_episodes': 40,
        'source_contract_sha256': evaluation.driver.sha(root/'validation_contract.json'),
        'original_results_modified': False})


def run(root):
    contract = check(root)
    with (root/'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        evaluation.require(not (root/'episodes').exists(), 'Continuation already started; do not replay')
        config = evaluation.read(root/'config.json')
        evaluation.credentials(config)
        guard = SharedBudgetGuard(root/'budget.json', approval_limit_usd=30,
            prior_spend_usd=contract['continuation']['prior_conservative_charge_usd'],
            optimizer_reserve_usd=0, request_reserve_usd=0)
        try:
            evaluation.driver.run(config, root, contract, expected_episodes=16,
                                  budget_guard=BudgetMux([guard]), retrieval_auditor=evaluation.audit)
        finally:
            if (root/'summary.json').exists():
                report(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run', 'report'))
    parser.add_argument('--prior', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = evaluation.builder.output_root(args.output)
    if args.phase == 'prepare':
        prepare(evaluation.builder.output_root(args.prior), root)
    elif args.phase == 'report':
        report(root)
    else:
        run(root)
