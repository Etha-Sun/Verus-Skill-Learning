"""Resume the authorized B/C matrix without replaying valid completed cells."""
from __future__ import annotations

import argparse
import copy
import fcntl
from pathlib import Path
import shutil

import evaluate_selective_references as evaluation
from recover_card_organization_evaluation import inherited_charge
from retry_selective_interruption import validate_interruption


RETRY_KEYS = {'dev_old--3f17ea7c76a0ce99c098',
              'dev_revised--9b9f6ccef89db4103c7f',
              'dev_old--6a7283f1b8a3f1d862db'}
FIELDS = ('items', 'artifacts', 'installed_library_conditions', 'installed_library_root',
          'model', 'reasoning_effort', 'timeout_seconds', 'workers', 'repeats', 'budget_usd',
          'model_context_window', 'max_output_tokens_per_request', 'bootstrap', 'arm_labels')


def plan_remaining(parent, summary):
    require = evaluation.prior.require
    require(summary['bridge_drained'] and summary['reviewed_inputs_unchanged'],
            'Parent must be drained with unchanged inputs')
    rows = {entry['row']['bridge_task_key']: entry for entry in summary['rows']}
    require(len(rows) == len(summary['rows']) == 28, 'Expected original 28 attempts')
    expected = {evaluation.prior.driver.episode_key(job) for job in parent['schedule']}
    require(len(expected) == 40 and set(rows) <= expected, 'Unexpected matrix')
    require(RETRY_KEYS <= rows.keys(), 'Authorized interrupted attempts missing')
    for key in RETRY_KEYS:
        row = rows[key]['row']
        if row['codex_returncode'] == -9:
            validate_interruption(row)
        else:
            require(key != 'dev_old--3f17ea7c76a0ce99c098'
                    and row['codex_returncode'] == 1 and not row['timed_out']
                    and not row['proof_solved'] and row['fidelity'] == 'V0_INVALID',
                    'Only the audited early provider abort may be repeated')
            events = (Path(rows[key]['episode']) / 'codex_events.raw.jsonl').read_text()
            require('Provider bridge halted pending review: IncompleteRead' in events,
                    'Missing provider abort evidence')
    jobs = [job for job in parent['schedule']
            if evaluation.prior.driver.episode_key(job) not in rows
            or evaluation.prior.driver.episode_key(job) in RETRY_KEYS]
    require(len(jobs) == 15, 'Expected 12 missing plus 3 interrupted cells')
    return jobs, sorted(set(rows) - RETRY_KEYS)


def prepare(parent_root, root):
    parent = evaluation.check(parent_root)
    summary = evaluation.prior.read(parent_root / 'summary.json')
    jobs, retained = plan_remaining(parent, summary)
    state = evaluation.prior.read(parent_root / 'budget.json')
    evaluation.prior.require(not state['reservations'], 'Parent reservations remain')
    charge = inherited_charge(state)
    evaluation.prior.require(charge < 30, 'Campaign budget exhausted')
    evaluation.prior.require(not root.exists(), 'Fresh output directory required')
    root.mkdir(parents=True)
    config = evaluation.prior.read(parent_root / 'config.json')
    (root / 'runtime').mkdir()
    shutil.copyfile(Path(config['source_root']) / 'models.json', root / 'runtime/models.json')
    config['source_root'] = str(root / 'runtime')
    evaluation.write_json(root / 'config.json', config)
    shutil.copyfile(parent_root / 'TASK.md', root / 'TASK.md')
    for condition in evaluation.LABELS:
        shutil.copytree(Path(parent['bundle_paths'][condition]), root / 'bundles' / condition)
    evaluation.preflight(config, root)
    contract = copy.deepcopy(parent)
    contract.update(schema_version='selective-reference-continuation-v1', schedule=jobs,
        expected_episodes=15,
        bundle_paths={condition: str(root / 'bundles' / condition) for condition in evaluation.LABELS},
        continuation={'parent_root': str(parent_root), 'retained_keys': retained,
            'retry_keys': sorted(RETRY_KEYS), 'unstarted_count': 12,
            'prior_conservative_charge_usd': charge,
            'authorization': 'User explicitly requests finishing round two after incomplete result audit.',
            'supersedes_unstarted_single_retry': 'selective-reference-evaluation-20261013-retry-v1',
            'budget_policy': 'Same USD30 campaign cap; all prior known and uncertain charges retained.'})
    contract['caveat'] += ' Continuation retains 25 completed cells and replaces only 3 documented technical interruptions; 12 cells were unstarted. No best-of selection or timeout replay. All attempt costs retained.'
    evidence = [Path(__file__), root / 'config.json', root / 'TASK.md', root / 'preflight.json',
                root / 'runtime/models.json', parent_root / 'validation_contract.json',
                parent_root / 'summary.json', parent_root / 'budget.json',
                parent_root / 'provider_calls.jsonl',
                Path(__file__).with_name('retry_selective_interruption.py')]
    evidence.extend(path for path in (root / 'bundles').rglob('*') if path.is_file())
    evidence.extend(path for path in (parent_root / 'episodes').glob('*/*')
                    if path.name in ('result.json', 'validation.json', 'fidelity_audit.json',
                                     'codex_events.raw.jsonl'))
    contract['input_hashes'].update({str(path.resolve()): evaluation.prior.driver.sha(path)
                                   for path in evidence})
    evaluation.write_json(root / 'validation_contract.json', contract)
    evaluation.write_json(root / 'review_receipt.json', {
        'decision': 'APPROVE_WITH_NONBLOCKING_NOTES',
        'contract_sha256': evaluation.prior.driver.sha(root / 'validation_contract.json'),
        'reviewer': 'coding-assistant; user-authorized continuation wiring review', 'paid_calls': 0,
        'blocking_issues': [], 'basis': '12 missing cells plus 3 audited technical replacements only.',
        'nonblocking_notes': ['Not an independent model review.',
            'Frozen actor and transport unchanged; new provider errors stop dispatch.',
            'Unknown prior charge is an upper-bound reserve, not an actual bill.']})
    check(root)
    evaluation.write_json(root / 'status.json', {'phase': 'prepared', 'episodes': 15,
        'retained': 25, 'prior_conservative_charge_usd': charge})
    print(f'Prepared15; retained25; prior conservative charge USD{charge:.9f}', flush=True)


def check(root):
    contract = evaluation.prior.read(root / 'validation_contract.json')
    evaluation.prior.require(contract['schema_version'] == 'selective-reference-continuation-v1',
                             'Wrong continuation schema')
    parent_root = Path(contract['continuation']['parent_root'])
    parent = evaluation.check(parent_root)
    jobs, retained = plan_remaining(parent, evaluation.prior.read(parent_root / 'summary.json'))
    evaluation.prior.require(contract['schedule'] == jobs
        and contract['continuation']['retained_keys'] == retained
        and contract['expected_episodes'] == 15, 'Continuation matrix changed')
    for field in FIELDS:
        evaluation.prior.require(contract[field] == parent[field], 'Fixed setting changed: ' + field)
    evaluation.prior.require(all(evaluation.prior.driver.sha(path) == digest
        for path, digest in contract['input_hashes'].items()), 'Frozen continuation input changed')
    for condition, path in contract['bundle_paths'].items():
        evaluation.load_skill_artifact(Path(path), contract['artifacts'][condition]['artifact_sha256'])
    evaluation.prior.driver.check_review(root / 'review_receipt.json', root / 'validation_contract.json')
    return contract


def report(root):
    contract = check(root)
    parent_root = Path(contract['continuation']['parent_root'])
    previous = evaluation.prior.read(parent_root / 'summary.json')
    current = evaluation.prior.read(root / 'summary.json')
    selected = evaluation.continuation.merge_selected(previous['rows'], current['rows'],
        contract['continuation']['retained_keys'],
        {evaluation.prior.driver.episode_key(job) for job in contract['schedule']})
    combined = root / 'combined'
    combined.mkdir(exist_ok=True)
    summary = dict(rows=list(selected.values()), failures=current['failures'],
        completed_episodes=len(selected), expected_episodes=40,
        all_cells_recorded=len(selected) == 40, bridge_drained=current['bridge_drained'],
        reviewed_inputs_unchanged=current['reviewed_inputs_unchanged'],
        finished_at=current['finished_at'], caveat=contract['caveat'],
        excluded_attempts=[str(parent_root / 'episodes' / key) for key in sorted(RETRY_KEYS)],
        source_summaries={str(path): evaluation.prior.driver.sha(path)
            for path in (parent_root / 'summary.json', root / 'summary.json')})
    evaluation.write_json(combined / 'summary.json', summary)
    shutil.copyfile(root / 'budget.json', combined / 'budget.json')
    evaluation.report(combined)
    evaluation.write_json(root / 'status.json', {'phase': 'complete' if len(selected) == 40
        and not current['failures'] else 'stopped_incomplete',
        'selected_cells': len(selected), 'expected_cells': 40,
        'failures': current['failures'], 'combined_report': str(combined / 'report.json')})


def run(root):
    contract = check(root)
    parent = Path(contract['continuation']['parent_root'])
    with (root / 'execution.lock').open('a') as lock, (parent / 'execution.lock').open('a') as parent_lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(parent_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        evaluation.prior.require(not (root / 'episodes').exists(), 'Already launched; no duplicate replay')
        config = evaluation.prior.read(root / 'config.json')
        evaluation.prior.credentials(config)
        guard = evaluation.SharedBudgetGuard(root / 'budget.json', approval_limit_usd=30,
            prior_spend_usd=contract['continuation']['prior_conservative_charge_usd'],
            optimizer_reserve_usd=0, request_reserve_usd=0)
        def audit(path):
            condition = 'old' if path.parent.name.startswith('dev_old--') else 'revised'
            return evaluation.audit_events(path, root / 'bundles' / condition)
        evaluation.write_json(root / 'status.json', {'phase': 'running', 'episodes': 15, 'retained': 25})
        try:
            evaluation.prior.driver.run(config, root, contract, expected_episodes=15,
                budget_guard=evaluation.BudgetMux([guard]), retrieval_auditor=audit)
        finally:
            if (root / 'summary.json').exists():
                report(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'check', 'run', 'report'))
    parser.add_argument('--parent', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = evaluation.prior.builder.output_root(args.output)
    if args.phase == 'prepare':
        evaluation.prior.require(args.parent is not None, 'Parent required')
        prepare(evaluation.prior.builder.output_root(args.parent), root)
    elif args.phase == 'check':
        check(root)
        print('Frozen continuation verified')
    elif args.phase == 'report':
        report(root)
    else:
        run(root)
