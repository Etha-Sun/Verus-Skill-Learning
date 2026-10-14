"""Build a review-only repaired78 candidate; never launch actor evaluation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path

from skillopt_verusage import card_organization as organization
from skillopt_verusage.budget_guard import SharedBudgetGuard, estimate_deepseek_cost
from skillopt_verusage.card_bank import build_bundle
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json


REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / 'research_memory/projects/verus_self_evolving/experiments/20261011-trace2skill-card-organization'
BANK = REPO / 'research_artifacts/deepseek-20261011/cards/repaired78.json'
RECIPE = REPO / 'skillopt-verusage/review/augmented78_revision.json'
SEED = REPO / 'skillopt-verusage/skills/initial.md'
PUBLISHED = REPO / 'research_artifacts/deepseek-20261011/cards/card-repair-validation-20261008-3gtA3H/revised78/bundle/SKILL.md'
CAPS = {'router': 65536, 'reduce': 32768}


def output_root(path):
    configured = os.environ.get('VERUS_SKILL_RUN_ROOT')
    organization.require(bool(configured), 'VERUS_SKILL_RUN_ROOT required')
    root = Path(configured).resolve()
    path = path.resolve()
    organization.require(root in path.parents and REPO not in path.parents, 'Output must be below external run root')
    return path


def inputs():
    from skillopt_verusage import budget_guard, guarded_deepseek, codex_deepseek_bridge, text_context
    paths = [BANK, RECIPE, SEED, PUBLISHED, Path(__file__), Path(organization.__file__),
             *(Path(module.__file__) for module in (budget_guard, guarded_deepseek, codex_deepseek_bridge, text_context)),
             DESIGN/'prompts/router_system.md', DESIGN/'prompts/reduce_system.md', DESIGN/'templates/SKILL.md.tmpl']
    return {str(path.relative_to(REPO)): organization.sha(path) for path in paths}


def prior_cost(prior_run, budget, packet):
    if prior_run is None:
        return 0.0, {}
    prior_run = output_root(prior_run)
    contract = json.loads((prior_run/'build_contract.json').read_text())
    state = json.loads((prior_run/'budget.json').read_text())
    organization.require(contract['budget_usd'] == budget and state['approval_limit_usd'] == budget, 'Prior budget mismatch')
    organization.require(not state['reservations'] and state['uncertain_requests'] == 0, 'Prior requests unresolved')
    organization.require(contract['bank_sha256'] == packet['bank_sha256'], 'Prior bank mismatch')
    organization.require(json.loads((prior_run/'router_input.json').read_text()) == packet, 'Retry input changed')
    organization.require((prior_run/'router_system.md').read_bytes() == (DESIGN/'prompts/router_system.md').read_bytes(),
                         'Retry router prompt changed')
    records = [json.loads(line) for line in (prior_run/'provider_calls.jsonl').read_text().splitlines()]
    amounts = [attempt['estimated_cost_usd'] for row in records for attempt in row['attempts']]
    organization.require(all(isinstance(amount, (int, float)) for amount in amounts), 'Unknown prior cost')
    organization.require(abs(sum(amounts) - state['target_spend_usd']) < 1e-9, 'Prior ledger does not reconcile')
    files = {str(prior_run/name): organization.sha(prior_run/name) for name in
             ('build_contract.json', 'budget.json', 'provider_calls.jsonl', 'router_input.json', 'router_system.md')}
    return state['target_spend_usd'] + state['prior_spend_usd'], files


def prepare(root, budget, prior_run=None, router_cap=65536):
    organization.require(0 < budget <= 5, 'Construction ceiling must be in (0, 5] USD')
    packet = organization.router_packet(BANK, RECIPE)
    organization.require(router_cap in (65536, 131072), 'Unexpected router output cap')
    prior_spend, prior_files = prior_cost(prior_run, budget, packet)
    caps = {**CAPS, 'router': router_cap}
    root.mkdir(parents=True, exist_ok=False)
    write_json(root/'router_input.json', packet)
    for role in CAPS:
        (root/f'{role}_system.md').write_bytes((DESIGN/f'prompts/{role}_system.md').read_bytes())
    dry_client = GuardedDeepSeek(root=root/'calls', api_key='', guards=[], ledger=root/'provider_calls.jsonl')
    serialized = json.dumps(packet, ensure_ascii=False)
    payload = dry_client.payload(system=(root/'router_system.md').read_text(), user=serialized,
                                 cap=caps['router'], effort='max')
    admission = dry_client.admit(system=payload['instructions'], user=serialized, cap=caps['router'], effort='max')
    bound = estimate_deepseek_cost({'prompt_cache_miss_tokens': len(json.dumps(payload, ensure_ascii=False).encode())+8192,
                                   'completion_tokens': caps['router']}, 'deepseek-v4-pro', price_band='peak')
    control = build_bundle(BANK, SEED, root/'control', autonomous_retrieval=True,
                           index_descriptions=json.loads(RECIPE.read_text())['index_descriptions'],
                           diagnostic_guidance=False)
    organization.require((root/'control/SKILL.md').read_bytes() == PUBLISHED.read_bytes(), 'Control SKILL differs')
    frozen = {str(path.relative_to(root)): organization.sha(path)
              for path in (root/'router_input.json', root/'router_system.md', root/'reduce_system.md')}
    contract = {'schema_version': 'card-organization-build-v1', 'created_at': datetime.now(timezone.utc).isoformat(),
        'model': 'deepseek-v4-pro', 'reasoning_effort': 'max', 'budget_usd': budget,
        'output_caps': caps, 'workers': 1, 'paid_retry': False, 'evaluation_authorized': False,
        'prior_spend_usd': prior_spend, 'prior_files': prior_files, 'capture_public_payloads': True,
        'future_evaluation_episodes': 40, 'inputs': inputs(), 'frozen_files': frozen,
        'router_admission': admission, 'router_peak_request_bound_usd': bound,
        'control': control, 'bank_sha256': packet['bank_sha256'],
        'pricing_source': 'https://api-docs.deepseek.com/quick_start/pricing/',
        'cost_caveat': 'Existing clock-only tariff estimates may overestimate weekends/holidays; peak reservation remains conservative.'}
    write_json(root/'build_contract.json', contract)
    return contract


def check_contract(root):
    contract = json.loads((root/'build_contract.json').read_text())
    organization.require(contract['inputs'] == inputs(), 'Frozen build inputs changed')
    for name, digest in contract['frozen_files'].items():
        organization.require(organization.sha(root/name) == digest, f'Frozen run input changed: {name}')
    for name, digest in contract.get('prior_files', {}).items():
        organization.require(organization.sha(name) == digest, 'Prior attempt evidence changed')
    return contract


def client(root, env_file, contract):
    from dotenv import dotenv_values
    values = dotenv_values(env_file)
    base = values.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')
    organization.require(base in {'https://api.deepseek.com', 'https://api.deepseek.com/v1'}, 'Credential file requests unexpected endpoint')
    key = values.get('DEEPSEEK_API_KEY')
    organization.require(bool(key), 'Missing DEEPSEEK_API_KEY')
    guard = SharedBudgetGuard(root/'budget.json', approval_limit_usd=contract['budget_usd'],
                             prior_spend_usd=contract.get('prior_spend_usd', 0), optimizer_reserve_usd=0, request_reserve_usd=0)
    return GuardedDeepSeek(root=root/'calls', api_key=key, guards=[guard], ledger=root/'provider_calls.jsonl',
                          capture_public_payloads=True)


def generate(root, role, name, packet, provider, cap):
    system = (root/f'{role}_system.md').read_text()
    result, usage = provider.call(system=system, user=json.dumps(packet, ensure_ascii=False),
                                  name=name, cap=cap, effort='max')
    path = root/'proposals'/f'{name}.json'
    value = json.loads(result)
    write_json(path, value)
    return value, usage


def router(root, env_file):
    contract = check_contract(root)
    packet = json.loads((root/'router_input.json').read_text())
    proposal, usage = generate(root, 'router', 'router', packet, client(root, env_file, contract), contract['output_caps']['router'])
    result = organization.validate_router(proposal, packet)
    result['proposal_sha256'] = organization.sha(root/'proposals/router.json')
    result['usage'] = usage
    write_json(root/'router_validation.json', result)
    return result


def reduce(root, env_file, review_path):
    contract = check_contract(root)
    receipt = json.loads(review_path.read_text())
    organization.require(receipt.get('router_sha256') == organization.sha(root/'proposals/router.json'), 'Stale router review')
    organization.require(receipt.get('decision') == 'approve_for_draft_reduction', 'Router requires review')
    organization.require(receipt.get('evaluation_authorized') is False, 'Review cannot authorize evaluation')
    write_json(root/'router_review.json', receipt)
    packet = json.loads((root/'router_input.json').read_text())
    proposal = json.loads((root/'proposals/router.json').read_text())
    provider = client(root, env_file, contract)
    results = []
    for ident, request in sorted(organization.reduction_packets(proposal, packet).items()):
        write_json(root/'reduction_inputs'/f'{ident}.json', request)
        value, usage = generate(root, 'reduce', f'reduce/{ident}', request, provider, contract['output_caps']['reduce'])
        result = organization.validate_reduction(value, request)
        result['usage'] = usage
        result['proposal_sha256'] = organization.sha(root/'proposals/reduce'/f'{ident}.json')
        results.append(result)
        write_json(root/'reduction_progress.json', results)
        print(json.dumps(result), flush=True)
    return {'completed_families': len(results)}


def render(root):
    check_contract(root)
    packet = json.loads((root/'router_input.json').read_text())
    router_value = json.loads((root/'proposals/router.json').read_text())
    reductions = {path.stem: json.loads(path.read_text()) for path in (root/'proposals/reduce').glob('*.json')}
    result = organization.render_bundle(router_value, packet, reductions, DESIGN/'templates/SKILL.md.tmpl',
                                         SEED, root/'candidate')
    result['unresolved_review_items'] = router_value['review_items'] + [
        {'family_id': ident, **item} for ident, value in reductions.items() for item in value['review_items']]
    result['source_proposals'] = {str(path.relative_to(root)): organization.sha(path)
                                for path in sorted((root/'proposals').rglob('*.json'))}
    write_json(root/'candidate_manifest.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'router', 'reduce', 'render'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--router-review', type=Path)
    parser.add_argument('--budget-usd', type=float, default=5)
    parser.add_argument('--prior-run', type=Path)
    parser.add_argument('--router-cap', type=int, choices=(65536, 131072), default=65536)
    args = parser.parse_args()
    root = output_root(args.output)
    if args.phase == 'prepare':
        result = prepare(root, args.budget_usd, args.prior_run, args.router_cap)
    else:
        with (root/'build.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.phase in {'router', 'reduce'} and args.env_file is None:
                parser.error('Paid phases require --env-file')
            if args.phase == 'router':
                result = router(root, args.env_file)
            elif args.phase == 'reduce':
                if args.router_review is None:
                    parser.error('reduce requires --router-review')
                result = reduce(root, args.env_file, args.router_review)
            else:
                result = render(root)
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
