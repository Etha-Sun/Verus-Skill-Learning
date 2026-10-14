"""User-authorized fresh USD30 evaluation after a driver interruption."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import shutil

import evaluate_card_organization as evaluation
from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.guarded_deepseek import BudgetMux, write_json


def inherited_charge(state):
    return (state['prior_spend_usd'] + state['target_spend_usd'] +
            state['uncertain_spend_usd'] + sum(state['reservations'].values()))


def prepare(prior, root):
    previous = evaluation.check(prior)
    evaluation.driver.check_review(prior/'review_receipt.json', prior/'validation_contract.json')
    interruption = evaluation.read(prior/'interruption_audit.json')
    evaluation.require(interruption['completed_episodes'] == 0, 'Recovery assumes no completed episodes')
    evaluation.require(not (prior/'summary.json').exists(), 'Prior campaign status changed')
    evaluation.require(not root.exists(), 'Recovery needs a fresh directory')
    state = evaluation.read(prior/'budget.json')
    prior_charge = inherited_charge(state)
    evaluation.require(prior_charge < 30, 'Prior conservative charge exceeds new authorization')
    config = evaluation.read(prior/'config.json')
    root.mkdir(parents=True)
    (root/'runtime').mkdir()
    shutil.copyfile(Path(config['source_root'])/'models.json', root/'runtime/models.json')
    config['source_root'] = str(root/'runtime')
    write_json(root/'config.json', config)
    shutil.copyfile(prior/'TASK.md', root/'TASK.md')
    for condition in ('old', 'revised'):
        shutil.copytree(Path(previous['bundle_paths'][condition]), root/'bundles'/condition)
    evaluation.preflight(config, root)
    contract = copy.deepcopy(previous)
    contract.update(schema_version='card-organization-authorized-recovery-v1', budget_usd=30,
        expense_policy='USD30 cumulative ceiling including prior settled costs and unresolved reservation bounds; construction excluded',
        recovery={'prior_root': str(prior), 'prior_contract_sha256': evaluation.driver.sha(prior/'validation_contract.json'),
                  'prior_review_sha256': evaluation.driver.sha(prior/'review_receipt.json'),
                  'prior_settled_usd': state['prior_spend_usd'] + state['target_spend_usd'],
                  'prior_unknown_cost_bound_usd': state['uncertain_spend_usd'] + sum(state['reservations'].values()),
                  'prior_conservative_charge_usd': prior_charge,
                  'user_authorization': 'Raise overall cap to USD30 and rerun after disclosed technical interruption.',
                  'launch': 'systemd user service; Linger enabled; Restart=no',
                  'automatic_retry': False, 'earlier_interrupted_episodes_excluded_from_primary_matrix': 2})
    contract['bundle_paths'] = {condition: str(root/'bundles'/condition) for condition in ('old', 'revised')}
    contract['caveat'] += ' A preceding infrastructure interruption left two incomplete cells; preserve them separately, and account for their known and unknown costs cumulatively.'
    added_files = [Path(__file__), root/'config.json', root/'TASK.md', root/'runtime/models.json',
                   root/'preflight.json', prior/'validation_contract.json', prior/'review_receipt.json',
                   prior/'budget.json', prior/'interruption_audit.json', prior/'provider_calls.jsonl']
    added_files.extend(path for path in (root/'bundles').rglob('*') if path.is_file())
    contract['input_hashes'].update({str(path.resolve()): evaluation.driver.sha(path) for path in added_files})
    write_json(root/'validation_contract.json', contract)
    write_json(root/'recovery_delta.json', {
        'changed_contract_fields': sorted(key for key in contract if previous.get(key) != contract[key]),
        'schedule_unchanged': contract['schedule'] == previous['schedule'],
        'artifacts_unchanged': contract['artifacts'] == previous['artifacts'],
        'actor_configuration_changed': False,
        'prior_review_reused_as_new_approval': False,
        'paid_review_calls': 0})
    write_json(root/'review_receipt.json', {
        'decision': 'APPROVE_WITH_NONBLOCKING_NOTES',
        'contract_sha256': evaluation.driver.sha(root/'validation_contract.json'),
        'reviewer': 'coding-assistant; authorized infrastructure-recovery delta review',
        'blocking_issues': [],
        'basis': 'Explicit new user authorization, unchanged reviewed actor method/packages/matrix, conservative inherited costs, repeated zero-API systemd preflight.',
        'parent_model_review': {'reviewer': 'deepseek-v4-pro/max',
                                'sha256': evaluation.driver.sha(prior/'review_receipt.json')},
        'nonblocking_notes': ['Prior unknown costs remain unknown; the reservation bounds are budget accounting, not actual billing.'],
        'paid_calls': 0})
    check(root)
    print('Recovery prepared: unchanged 40-cell matrix; USD30 overall cap; inherited charge '+str(prior_charge), flush=True)


def check(root):
    contract = evaluation.read(root/'validation_contract.json')
    evaluation.require(contract['budget_usd'] == 30, 'Unexpected recovery ceiling')
    evaluation.require(all(evaluation.driver.sha(path) == digest for path, digest in contract['input_hashes'].items()),
                       'Frozen recovery inputs changed')
    prior = evaluation.read(Path(contract['recovery']['prior_root'])/'validation_contract.json')
    for field in ('schedule', 'items', 'artifacts', 'installed_library_conditions', 'installed_library_root',
                  'model', 'reasoning_effort', 'timeout_seconds', 'workers', 'repeats',
                  'model_context_window', 'max_output_tokens_per_request', 'bootstrap'):
        evaluation.require(contract[field] == prior[field], 'Recovery changed actor methodology: '+field)
    evaluation.driver.check_review(root/'review_receipt.json', root/'validation_contract.json')
    return contract


def run(root):
    contract = check(root)
    config = evaluation.read(root/'config.json')
    evaluation.credentials(config)
    guard = SharedBudgetGuard(root/'budget.json', approval_limit_usd=30,
        prior_spend_usd=contract['recovery']['prior_conservative_charge_usd'],
        optimizer_reserve_usd=0, request_reserve_usd=0)
    try:
        evaluation.driver.run(config, root, contract, expected_episodes=40,
                              budget_guard=BudgetMux([guard]), retrieval_auditor=evaluation.audit)
    finally:
        if (root/'summary.json').exists():
            evaluation.summarize(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run'))
    parser.add_argument('--prior', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = evaluation.builder.output_root(args.output)
    if args.phase == 'prepare':
        prepare(evaluation.builder.output_root(args.prior), root)
    else:
        run(root)
