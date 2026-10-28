"""Twenty-four fresh trials: tested G1 versus one applicability-explanation replacement."""
from __future__ import annotations
import argparse
import difflib
import fcntl
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

# Private orchestration instance; do not alter the historical module or harness.
_spec = importlib.util.spec_from_file_location('_guidance_premises24_shared', Path(__file__).with_name('evaluate_retrieval_reassessment.py'))
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
e = shared.e
read, sha, require, write_json = shared.read, shared.sha, shared.require, shared.write_json
ARMS = ('G1_current', 'G2_premise_check')
EPISODES = 24
REPEATS = 3
shared.ARMS = ARMS
SCHEMA = 'guidance-premises-v2-index-24'
CONTROL_SHA = '7df0f0299b9c041fb4eb46f1bb95fba0358c578a5a70ee531233b3b347e05820'
OLD_TEXT = "Briefly identify a consulted card's ID\nand why it applies or why you decline it in your progress message."
NEW_TEXT = 'Briefly identify a consulted card’s ID and connect its advice to the current\nobligation and available premises. Distinguish applying its route from borrowing\na general technique; check the premises needed for the step you actually take,\nand decline advice that requires unavailable premises.'


def schedule():
    return [{'id': ident, 'condition': arm, 'repeat': repeat}
            for repeat in range(REPEATS) for position, ident in enumerate(shared.TASK_IDS)
            for arm in (ARMS if (position + repeat) % 2 == 0 else ARMS[::-1])]


def reviewed_mains(review, baseline):
    checks = read(review / 'checks.json')
    require(checks['status'] == 'single_sentence_replacement_reviewed', 'Wrong reviewed revision')
    source = baseline / 'bundles/G1_obligation_main/SKILL.md'
    control = source.read_text()
    require(sha(source) == CONTROL_SHA, 'Tested G1 source changed')
    require(checks['control_sha256'] == CONTROL_SHA, 'Control manifest changed')
    require(checks['old_text'] == OLD_TEXT and checks['new_text'] == NEW_TEXT, 'Replacement text changed')
    candidate = (review / 'SKILL.draft.md').read_text()
    require(sha(review / 'SKILL.draft.md') == checks['draft_sha256'], 'Reviewed main changed')
    require(control.count(OLD_TEXT) == 1, 'Expected one original sentence')
    require(candidate == control.replace(OLD_TEXT, NEW_TEXT, 1), 'Changes exceed single approved replacement')
    require(candidate.split('## Card index\n')[1] == control.split('## Card index\n')[1], 'Index changed')
    return control, candidate


def verify_materials(root, review, baseline):
    mains = reviewed_mains(review, baseline)
    for arm, main in zip(ARMS, mains):
        bundle = root / 'bundles' / arm
        require({p.name for p in bundle.iterdir()} == set(shared.FROZEN), 'Unexpected actor file')
        require((bundle / 'SKILL.md').read_text() == main, 'Actor main changed')
        for name in ('cards.json', 'card_read.py'):
            require(sha(bundle / name) == shared.FROZEN[name], 'Body/reader changed')
    for name in ('EXECUTIVE.md', 'TASK.md', 'task-selection.json'):
        require((root / name).read_bytes() == (baseline / name).read_bytes(), 'Fixed file changed: ' + name)


def prepare(root, review, baseline):
    require(not root.exists(), 'Fresh run root required')
    require(root.parent == review.parent == baseline.parent, 'Use external sibling run roots')
    old = read(baseline / 'validation_contract.json')
    require(old['expected_episodes'] == 24 and read(baseline / 'summary.json')['completed_episodes'] == 24, 'Unexpected completed baseline')
    frozen = read(baseline / 'source-hashes.json')
    require(all(sha(p) == h for p, h in frozen.items()), 'Prior frozen input changed')
    mains = reviewed_mains(review, baseline)
    root.mkdir(parents=True)
    for arm, main in zip(ARMS, mains):
        shutil.copytree(baseline / 'bundles/G1_obligation_main', root / 'bundles' / arm)
        (root / 'bundles' / arm / 'SKILL.md').write_text(main)
    for name in ('EXECUTIVE.md', 'TASK.md', 'task-selection.json'):
        shutil.copyfile(baseline / name, root / name)
    for name in ('GUIDANCE.md', 'REVIEW.md', 'checks.json', 'SKILL.draft.md'):
        shutil.copyfile(review / name, root / name)
    (root / 'INDEX_V2.md').write_text('## Card index\n' + mains[0].split('## Card index\n')[1])
    (root / 'G1-G2.diff').write_text(''.join(difflib.unified_diff(
        mains[0].splitlines(True), mains[1].splitlines(True),
        fromfile=ARMS[0]+'/SKILL.md', tofile=ARMS[1]+'/SKILL.md')))
    shutil.copytree(baseline / 'runtime', root / 'runtime')
    config = read(baseline / 'config.json')
    config['source_root'] = str(root / 'runtime')
    write_json(root / 'config.json', config)
    verify_materials(root, review, baseline)
    # Same real sandbox/positive/negative controls; add new researcher-only files.
    original_evidence_paths = shared.evidence_paths
    shared.evidence_paths = lambda p: original_evidence_paths(p) + [
        review / 'REVIEW.md', root / 'REVIEW.md', root / 'INDEX_V2.md',
        baseline / 'final-review/REPORT.md', review / 'SKILL.draft.md',
        review / 'checks.json', root / 'G1-G2.diff']
    try:
        original = baseline
        while not (original / 'bundles/new_skeleton').exists():
            original = Path(read(original / 'validation_contract.json')['parent_run'])
        shared.preflight(root, config, original)
    finally:
        shared.evidence_paths = original_evidence_paths
    prior = read(baseline / 'report.json')['rows']
    peak = [(x['prompt_cache_hit_tokens'] * .044 + x['prompt_cache_miss_tokens'] * 1.32
             + x['completion_tokens'] * 3.96) / 1e6 for x in prior]
    floor = (1048576 * 1.32 + 131072 * 3.96) / 1e6
    budget = dict(status='new_24_episode_batch_independent_20_usd_cap', proposed_new_batch_cap_usd=20,
        context_window_safe_reserve_usd=floor, safe_two_inflight_reserve_usd=2 * floor,
        reference_completed_batch=str(baseline), reference_completed_24_cost_usd=sum(x['estimated_cost_usd'] for x in prior),
        reference_usage_peak_repriced_24_projection_usd=sum(peak),
        twenty_four_at_max_observed_peak_usage_usd=max(peak) * 24,
        actor_slot_hours_max=24 * 600 / 3600, ideal_two_worker_minutes_max=120,
        provider_drain_seconds_max=1810, automatic_paid_retry=False,
        caveat='Empirical usage projections, not guaranteed expense; peak reserve ceiling, independent ledger. Same authorized USD20 protective limit; no old ledger resets or expansion.')
    write_json(root / 'budget-proposal.json', budget)
    c = {k: old[k] for k in ('model', 'reasoning_effort', 'timeout_seconds', 'workers',
        'installed_library_root', 'model_context_window', 'max_output_tokens_per_request',
        'provider_request_timeout_seconds', 'items', 'primary', 'request_scope')}
    c.update(schema_version=SCHEMA, parent_run=str(baseline), reviewed_materials=str(review),
        schedule=schedule(), expected_episodes=EPISODES, repeats=REPEATS, budget_usd=20,
        installed_library_conditions=list(ARMS), bundle_paths={a: str(root / 'bundles' / a) for a in ARMS},
        artifacts={a: shared.load_skill_artifact(root / 'bundles' / a).manifest() for a in ARMS},
        ordinary_retry=False, transport_retry=False, reference_proof_supplied=False, sealed_test_access=False,
        intervention='Only the approved consulted-card explanation sentence differs. Control is exact previously tested G1. Both retain its three insertions, v2 index, new_skeleton bodies, reader, Executive wording, TASK and harness.',
        authorization='Explicit current user authorization required, bound to this contract before API startup.',
        caveat='Four known development tasks, independent fresh samples; repeat labels are scheduling blocks, not shared seeds. Reads are not improvement. Both arms share the v2 index and corrected new-001 example. One sentence replacement requests obligation/premise grounding and distinguishes route application from general-technique transfer; prior three insertions are common to both arms. Historical entry context alone does not establish an unavailable logical premise. Correctness requires actual-step evidence, not read counts or applicability self-reports. No deadline-awareness prompt. No checkpoint resumes, historical answers, retries or expansion.')
    files = [p for p in root.rglob('*') if p.is_file() and 'preflight' not in p.parts]
    files += [root / 'preflight.json', Path(__file__).resolve(), review / 'checks.json']
    files += [review / 'SKILL.draft.md', review / 'GUIDANCE.md', Path(__file__).resolve().parents[1] / 'tests/test_guidance_premises.py']
    c['input_hashes'] = {**frozen, **{str(p.resolve()): sha(p) for p in files}}
    write_json(root / 'source-hashes.json', c['input_hashes'])
    write_json(root / 'validation_contract.json', c)
    write_json(root / 'offline-status.json', dict(paid_calls=0, contract_sha256=sha(root / 'validation_contract.json'),
                                                episodes_prepared=EPISODES, runtime_preflight_passed=True))
    check(root)


def check(root):
    c = read(root / 'validation_contract.json')
    require(c['schema_version'] == SCHEMA, 'Wrong contract')
    require(c['schedule'] == schedule() and c['expected_episodes'] == EPISODES and c['repeats'] == REPEATS, 'Matrix changed')
    require([x['id'] for x in c['items']] == list(shared.TASK_IDS), 'Tasks changed')
    require(c['workers'] == 2 and c['timeout_seconds'] == 600 and c['budget_usd'] == 20, 'Scope changed')
    require(c['model'] == 'deepseek-v4-pro' and c['reasoning_effort'] == 'max', 'Model changed')
    require(c['max_output_tokens_per_request'] == 131072 and c['model_context_window'] == 1048576, 'Token configuration changed')
    require(all(sha(p) == h for p, h in c['input_hashes'].items()), 'Frozen inputs changed')
    require(read(root / 'source-hashes.json') == c['input_hashes'], 'Hash manifest changed')
    require(read(root / 'offline-status.json')['contract_sha256'] == sha(root / 'validation_contract.json'), 'Contract changed')
    require(c['installed_library_conditions'] == list(ARMS), 'Arms changed')
    verify_materials(root, Path(c['reviewed_materials']), Path(c['parent_run']))
    checks = read(root / 'preflight.json')['checks']
    require([x['arm'] for x in checks] == list(ARMS) and all(x['returncode'] == 0 and x['codex_returncode'] == 0 for x in checks), 'Preflight incomplete')
    return c


def validate_authorization(root, path):
    require(path is not None, 'No API launch authorization supplied; offline preparation is not permission to run')
    a = read(path)
    expected = {'contract_sha256': sha(root / 'validation_contract.json'), 'approved': True,
        'episodes': EPISODES, 'new_batch_cap_usd': 20, 'destination': 'https://api.deepseek.com',
        'automatic_paid_retry': False, 'background_launch': True, 'pricing_verified': True, 'explicit_data_transfer_approved': True}
    require(all(a.get(k) == v for k, v in expected.items()), 'Authorization does not cover this exact batch')
    require(bool(a.get('user_instruction')) and bool(a.get('pricing_evidence')), 'Missing user authorization or current tariff evidence')
    return a


def report(root):
    c = read(root / 'validation_contract.json')
    if not (root / 'summary.json').exists():
        attempted = any((root / n).exists() for n in ('started.json', 'episodes', 'provider_calls.jsonl'))
        return {'status': 'started_without_summary' if attempted else 'offline_prepared_no_actor_results',
                'planned': EPISODES, 'paid_calls': 'unknown_pending_ledger_review' if attempted else 0}
    summary = read(root / 'summary.json'); rows = []
    jobs = {e.prior.driver.episode_key(j): j for j in c['schedule']}
    for entry in summary['rows']:
        row = e.result_dimensions(entry); ep = Path(entry['episode'])
        deadline = e.hard.deadline_audit(ep, 600)
        write_json(ep / 'deadline_dual_audit.json', deadline)
        row.update(repeat=jobs[entry['row']['bridge_task_key']]['repeat'],
            primary_same_hash_dual_600=deadline['observed_dual_within_deadline'],
            first_confirmed_dual_seconds=deadline['first_confirmed_dual_seconds'],
            normal_exit=entry['row']['codex_returncode'] == 0 and not entry['row']['timed_out'],
            initial_prompt_exact=(ep / 'prompt.txt').read_bytes() == (root / 'TASK.md').read_bytes(),
            mechanism_review='pending; helper returns alone are not upstream exposure, adoption or progress')
        require(row['initial_prompt_exact'], 'Unexpected supplemental prompt')
        rows.append(row)
    result = {'planned': EPISODES, 'completed': len(rows), 'rows': rows, 'failures': summary['failures'],
        'arms': {a: {'completed': sum(r['condition'] == a for r in rows),
            'same_hash_dual_600': sum(r['condition'] == a and r['primary_same_hash_dual_600'] for r in rows)} for a in ARMS},
        'budget': read(root / 'budget.json'), 'caveat': c['caveat']}
    write_json(root / 'report.json', result)
    return result


def run(root, authorization):
    c = check(root)
    a = validate_authorization(root, authorization)  # Before credentials, ledgers or transport.
    with (root / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not any((root / n).exists() for n in ('started.json', 'episodes', 'budget.json')), 'No automatic restart')
        config = read(root / 'config.json')
        e.prior.credentials(config)
        guard = e.SharedBudgetGuard(root / 'budget.json', approval_limit_usd=20,
            prior_spend_usd=0, optimizer_reserve_usd=0, request_reserve_usd=0)
        floor = read(root / 'budget-proposal.json')['context_window_safe_reserve_usd']
        class ConservativeMux(e.BudgetMux):
            def reserve(self, amount_usd):
                return super().reserve(max(amount_usd, floor))
        write_json(root / 'launch-authorization.json', a)
        write_json(root / 'started.json', {'time': datetime.now(timezone.utc).isoformat(),
            'contract_sha256': sha(root / 'validation_contract.json')})
        try:
            e.prior.driver.run(config, root, c, expected_episodes=EPISODES,
                budget_guard=ConservativeMux([guard]), retrieval_auditor=lambda p: shared.audit_reads(p,
                    root / 'bundles' / p.parent.name.split('--')[0].removeprefix('dev_') / 'cards.json'))
            report(root)
            require(read(root / 'summary.json')['completed_episodes'] == EPISODES, 'Incomplete matrix')
        except BaseException as error:
            write_json(root / 'stopped.json', {'type': type(error).__name__, 'reason': str(error), 'automatic_retry': False})
            raise
        write_json(root / 'completed.json', {'episodes': EPISODES, 'mechanism_review_pending': True})




if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=['prepare', 'check', 'run', 'report'])
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--review', type=Path)
    p.add_argument('--baseline', type=Path)
    p.add_argument('--authorization', type=Path)
    args = p.parse_args()
    root = e.prior.builder.output_root(args.output)
    if args.phase == 'prepare':
        require(args.review is not None and args.baseline is not None, 'Review and baseline required')
        prepare(root, args.review.resolve(), args.baseline.resolve())
    elif args.phase == 'run':
        run(root, args.authorization)
    else:
        result = check(root) if args.phase == 'check' else report(root)
        print(json.dumps({'status': 'checked', 'episodes': EPISODES} if args.phase == 'check' else result))
