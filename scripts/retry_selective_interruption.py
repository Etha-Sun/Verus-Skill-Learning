"""One explicitly authorized SIGKILL replacement, after the original run drains."""
from __future__ import annotations

import argparse
import copy
import fcntl
from pathlib import Path
import shutil

import evaluate_selective_references as evaluation


KEY = 'dev_old--3f17ea7c76a0ce99c098'


def validate_interruption(row):
    evaluation.prior.require(
        row['bridge_task_key'] == KEY and row['codex_returncode'] == -9
        and not row['timed_out'] and not row['proof_solved'],
        'Only the user-confirmed externally killed B episode may be replaced')


def merge_rows(original, replacement):
    original_keys = [entry['row']['bridge_task_key'] for entry in original]
    evaluation.prior.require(len(original_keys) == len(set(original_keys)) == 40,
                             'Expected the original 40 unique cells')
    evaluation.prior.require(len(replacement) == 1
                             and replacement[0]['row']['bridge_task_key'] == KEY,
                             'Expected exactly one authorized replacement')
    evaluation.prior.require(KEY in original_keys, 'Interrupted cell missing')
    validate_interruption(next(entry['row'] for entry in original
                               if entry['row']['bridge_task_key'] == KEY))
    return [replacement[0] if entry['row']['bridge_task_key'] == KEY else entry
            for entry in original]


def prepare(parent, root):
    contract = copy.deepcopy(evaluation.check(parent))
    interrupted = parent / 'episodes' / KEY / 'result.json'
    validate_interruption(evaluation.prior.read(interrupted))
    evaluation.prior.require(not root.exists(), 'Use a fresh replacement directory')
    root.mkdir(parents=True)
    shutil.copyfile(parent / 'config.json', root / 'config.json')
    shutil.copyfile(parent / 'TASK.md', root / 'TASK.md')
    contract['schedule'] = [job for job in contract['schedule']
                            if evaluation.prior.driver.episode_key(job) == KEY]
    evaluation.prior.require(len(contract['schedule']) == 1, 'Wrong replacement schedule')
    contract.update(schema_version='selective-authorized-interruption-retry-v1',
                    expected_episodes=1, parent_root=str(parent),
                    authorization='User reports accidental process kill and explicitly requests one retry.',
                    budget_path=str(parent / 'budget.json'),
                    execution_policy='Wait for parent execution lock and drained successful summary; no other retries.')
    contract['caveat'] += ' One user-confirmed SIGKILL attempt is retained but excluded from efficacy; its replacement is selected regardless of success, and all costs remain charged.'
    contract['input_hashes'].update({str(path.resolve()): evaluation.prior.driver.sha(path)
        for path in (Path(__file__), interrupted, parent / 'validation_contract.json',
                     root / 'config.json', root / 'TASK.md')})
    evaluation.write_json(root / 'validation_contract.json', contract)
    evaluation.write_json(root / 'status.json', {'phase': 'prepared_not_launched', 'key': KEY})


def run(root):
    contract = evaluation.prior.read(root / 'validation_contract.json')
    parent = Path(contract['parent_root'])
    with (root / 'execution.lock').open('a') as retry_lock:
        fcntl.flock(retry_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        evaluation.prior.require(not (root / 'episodes').exists(), 'Replacement already launched; no replay')
        evaluation.write_json(root / 'status.json', {'phase': 'waiting_for_parent', 'key': KEY})
        with (parent / 'execution.lock').open('a') as parent_lock:
            fcntl.flock(parent_lock.fileno(), fcntl.LOCK_EX)
            evaluation.check(parent)
            original = evaluation.prior.read(parent / 'summary.json')
            evaluation.prior.require(original['bridge_drained'] and original['reviewed_inputs_unchanged']
                                     and original['completed_episodes'] == 40 and not original['failures'],
                                     'Parent must finish and drain cleanly before the replacement')
            evaluation.prior.require(not evaluation.prior.read(parent / 'budget.json')['reservations'],
                                     'Unsettled parent requests remain')
            config = evaluation.prior.read(root / 'config.json')
            evaluation.prior.credentials(config)
            evaluation.write_json(root / 'status.json', {'phase': 'running', 'key': KEY})
            def audit(path):
                return evaluation.audit_events(path, Path(contract['bundle_paths']['old']))
            evaluation.prior.driver.run(config, root, contract, expected_episodes=1,
                budget_guard=evaluation.BudgetMux([evaluation.guard(parent)]), retrieval_auditor=audit)
            replacement = evaluation.prior.read(root / 'summary.json')
            merged = copy.deepcopy(original)
            merged.update(rows=merge_rows(original['rows'], replacement['rows']),
                          failures=original['failures'] + replacement['failures'],
                          reviewed_inputs_unchanged=replacement['reviewed_inputs_unchanged'],
                          finished_at=replacement['finished_at'], caveat=contract['caveat'])
            merged.pop('ledger_sha256', None)
            merged['ledger_hashes'] = {str(path): evaluation.prior.driver.sha(path)
                for path in (parent / 'provider_calls.jsonl', root / 'provider_calls.jsonl')}
            merged['excluded_attempt'] = str(parent / 'episodes' / KEY)
            combined = root / 'combined'
            combined.mkdir()
            evaluation.write_json(combined / 'summary.json', merged)
            shutil.copyfile(parent / 'budget.json', combined / 'budget.json')
            evaluation.report(combined)
            evaluation.write_json(root / 'status.json', {'phase': 'complete', 'key': KEY,
                'combined_report': str(combined / 'report.json'), 'total_attempts': 41,
                'selected_cells': 40, 'shared_budget_includes_interrupted_attempt': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run'))
    parser.add_argument('--parent', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = evaluation.prior.builder.output_root(args.output)
    if args.phase == 'prepare':
        evaluation.prior.require(args.parent is not None, 'Parent required')
        prepare(evaluation.prior.builder.output_root(args.parent), root)
    else:
        run(root)
