"""Fresh index-only trials using the unchanged R0 actor execution harness."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

# Private orchestration instance; do not alter the historical module or harness.
_spec = importlib.util.spec_from_file_location('_index_trial_shared', Path(__file__).with_name('evaluate_retrieval_reassessment.py'))
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
e = shared.e
read, sha, require, write_json = shared.read, shared.sha, shared.require, shared.write_json
ARMS = ('I0_old_index', 'I1_compact_index')
shared.ARMS = ARMS
SCHEMA = 'index-ablation-v1'


def schedule():
    return shared.schedule()


def verify_materials(root, review, baseline):
    checks = read(review / 'material-checks.json')
    for name, digest in checks['artifact_hashes'].items():
        require(sha(review / name) == digest, 'Reviewed artifact changed: ' + name)
    for arm in ARMS:
        bundle = root / 'bundles' / arm
        require({p.name for p in bundle.iterdir()} == set(shared.FROZEN), 'Unexpected actor file')
        for name in shared.FROZEN:
            require((bundle / name).read_bytes() == (review / 'bundles' / arm / name).read_bytes(),
                    'Reviewed bundle changed: ' + arm + '/' + name)
    for name in ('EXECUTIVE.md', 'TASK.md', 'task-selection.json'):
        require((root / name).read_bytes() == (baseline / name).read_bytes(), 'Fixed file changed: ' + name)
    old = (root / 'bundles' / ARMS[0] / 'SKILL.md').read_bytes()
    new = (root / 'bundles' / ARMS[1] / 'SKILL.md').read_bytes()
    require(old.split(b'## Card index\n')[0] == new.split(b'## Card index\n')[0], 'R0 prefix changed')
    require(sha(root / 'bundles' / ARMS[0] / 'SKILL.md') == shared.FROZEN['SKILL.md'], 'R0 changed')


def prepare(root, review, baseline):
    require(not root.exists(), 'Fresh run root required')
    require(root.parent == review.parent == baseline.parent, 'Use external sibling run roots')
    old = read(baseline / 'validation_contract.json')
    require(old['expected_episodes'] == 24, 'Unexpected baseline')
    frozen = read(baseline / 'source-hashes.json')
    require(all(sha(p) == h for p, h in frozen.items()), 'Prior frozen input changed')
    review_checks = read(review / 'material-checks.json')
    require(review_checks['status'] == 'offline_material_review_only', 'Unexpected review package')
    root.mkdir(parents=True)
    shutil.copytree(review / 'bundles', root / 'bundles')
    for name in ('EXECUTIVE.md', 'TASK.md', 'task-selection.json'):
        shutil.copyfile(baseline / name, root / name)
    for name in ('INDEX_OLD.md', 'INDEX_NEW.md', 'I0-I1.diff', 'REVIEW.md', 'material-checks.json'):
        shutil.copyfile(review / name, root / name)
    shutil.copytree(baseline / 'runtime', root / 'runtime')
    config = read(baseline / 'config.json')
    config['source_root'] = str(root / 'runtime')
    write_json(root / 'config.json', config)
    verify_materials(root, review, baseline)
    # Same real sandbox/positive/negative controls; add new researcher-only files.
    original_evidence_paths = shared.evidence_paths
    shared.evidence_paths = lambda p: original_evidence_paths(p) + [
        review / 'REVIEW.md', root / 'REVIEW.md', root / 'INDEX_OLD.md', root / 'INDEX_NEW.md',
        baseline / 'final-review/REPORT.md', review / 'bundles' / ARMS[1] / 'SKILL.md']
    try:
        shared.preflight(root, config, Path(old['parent_run']))
    finally:
        shared.evidence_paths = original_evidence_paths
    budget = read(baseline / 'budget-proposal.json')
    budget.update(status='new_24_episode_batch_cap_20_usd', reference_completed_batch=str(baseline),
                  reference_completed_24_cost_usd=read(baseline / 'budget.json')['target_spend_usd'],
                  authorization_basis='Current user explicitly requests new old/new index experiment: four tasks, two arms, three repeats; same USD20 protective ceiling as prior equal-size batch, separate ledger.')
    write_json(root / 'budget-proposal.json', budget)
    c = {k: old[k] for k in ('model', 'reasoning_effort', 'timeout_seconds', 'workers',
        'installed_library_root', 'model_context_window', 'max_output_tokens_per_request',
        'provider_request_timeout_seconds', 'items', 'primary', 'request_scope')}
    c.update(schema_version=SCHEMA, parent_run=str(baseline), reviewed_materials=str(review),
        schedule=schedule(), expected_episodes=24, repeats=3, budget_usd=20,
        installed_library_conditions=list(ARMS), bundle_paths={a: str(root / 'bundles' / a) for a in ARMS},
        artifacts={a: shared.load_skill_artifact(root / 'bundles' / a).manifest() for a in ARMS},
        ordinary_retry=False, transport_retry=False, reference_proof_supplied=False, sealed_test_access=False,
        intervention='Only final Card index section; exact R0 workflow, Executive, ten new_skeleton bodies, reader, harness.',
        authorization='Explicit current user authorization required, bound to this contract before API startup.',
        caveat='Four known development tasks, independent fresh samples; repeat labels are scheduling blocks, not shared seeds. Reads are not improvement. Index wording, boundary salience and length change jointly. Wrong card-001 example is retained identically in both arms. No checkpoint resumes, historical answers, retries or expansion.')
    files = [p for p in root.rglob('*') if p.is_file() and 'preflight' not in p.parts]
    files += [root / 'preflight.json', Path(__file__).resolve(), review / 'material-checks.json']
    files += [review / n for n in review_checks['artifact_hashes']]
    c['input_hashes'] = {**frozen, **{str(p.resolve()): sha(p) for p in files}}
    write_json(root / 'source-hashes.json', c['input_hashes'])
    write_json(root / 'validation_contract.json', c)
    write_json(root / 'offline-status.json', dict(paid_calls=0, contract_sha256=sha(root / 'validation_contract.json'),
                                                episodes_prepared=24, runtime_preflight_passed=True))
    check(root)


def check(root):
    c = read(root / 'validation_contract.json')
    require(c['schema_version'] == SCHEMA, 'Wrong contract')
    require(c['schedule'] == schedule() and c['expected_episodes'] == 24 and c['repeats'] == 3, 'Matrix changed')
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


shared.check = check


def run(root, authorization):
    shared.run(root, authorization)


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
        result = check(root) if args.phase == 'check' else shared.report(root)
        print(json.dumps({'status': 'checked', 'episodes': 24} if args.phase == 'check' else result))
