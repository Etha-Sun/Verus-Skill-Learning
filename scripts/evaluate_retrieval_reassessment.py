"""Offline-first, frozen new_skeleton R0/R1 preparation. No implicit API authority."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import evaluate_ten_card_seven_arm as e
from skillopt_verusage.budget_guard import estimate_deepseek_request_upper_bound
from skillopt_verusage.skill_artifact import load_skill_artifact

REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / 'research_memory/projects/verus_self_evolving/experiments/20261019-local-instantiation-skill-plan'
ARMS = ('R0_current', 'R1_reassess')
TASK_IDS = ('a23a4969155913255f76', '9b9f6ccef89db4103c7f',
            'aded79905be896942897', '62ff0a3cf2c458b36ac8')
FROZEN = {
    'SKILL.md': '5d24245c9e718ac38c465ecaf89d5816839e28b72f1772618c6120f5e8829c8a',
    'cards.json': '213dc075e353f5c4a426c3d06c6c355045176b6d353667201b05736b2f4149d8',
    'card_read.py': '0d6b25e4b6e3506873492d96029cfd2a4bb55f7e71b180586b93ed4c4c76fd57',
}
read, sha, require, write_json = e.read, e.sha, e.require, e.write_json


def rule_text():
    return (DESIGN / 'REASSESSMENT_RULE.md').read_text()


def revised_main(original, rule):
    marker = b'## Card index\n\n'
    require(original.count(marker) == 1, 'Expected one frozen index')
    return original.replace(marker, rule.encode() + b'\n' + marker, 1)


def schedule():
    # Adjacent matched cells; alternate which arm enters the two-worker queue first.
    return [{'id': ident, 'condition': arm, 'repeat': repeat}
            for repeat in range(3) for position, ident in enumerate(TASK_IDS)
            for arm in (ARMS if (position + repeat) % 2 == 0 else ARMS[::-1])]


def evidence_paths(parent):
    return [parent / 'all-task-retrieval-review' / name for name in
            ('REPORT.md', 'READ_EPISODES.md', 'HARNESS_DIAGNOSIS.md')] + [
        parent / 'rely-retrieval-review/REPORT.md',
        parent.parent / 'rely-forced-new-structured-20261023-v1/RESULTS.md',
        parent.parent / 'fork-branch-retrieval-audit-20261023-v1/REPORT.md',
        parent.parent / 'fork-branch-retrieval-audit-20261023-v1/validation.json',
        parent / 'final-review/REPORT.md']


def verify_materials(root, parent):
    source = parent / 'bundles/new_skeleton'
    for name, digest in FROZEN.items():
        require(sha(source / name) == digest, 'v3 source changed: ' + name)
    for arm in ARMS:
        bundle = root / 'bundles' / arm
        require({p.name for p in bundle.iterdir()} == set(FROZEN), 'Unexpected actor file')
        for name in ('cards.json', 'card_read.py'):
            require((bundle / name).read_bytes() == (source / name).read_bytes(), 'Changed ' + name)
        expected = (source / 'SKILL.md').read_bytes()
        if arm == ARMS[1]:
            expected = revised_main(expected, rule_text())
        require((bundle / 'SKILL.md').read_bytes() == expected, 'Main differs beyond intervention')
    for name in ('EXECUTIVE.md', 'TASK.md', 'task-selection.json'):
        require((root / name).read_bytes() == (parent / name).read_bytes(), 'Changed ' + name)


def audit_payloads(events, bank):
    """Exact tool returns only; upstream exposure and semantic use remain separate."""
    seen = set(); reads = []; direct = []; errors = []
    for order, event in enumerate(events):
        item = event.get('item', {})
        key = (item.get('id'), item.get('type'))
        if event.get('type') != 'item.completed' or item.get('type') != 'command_execution':
            continue
        if item.get('id') is not None and key in seen:
            continue
        seen.add(key)
        command = item.get('command', ''); output = item.get('aggregated_output', '')
        found = set()
        for line in output.splitlines():
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if not isinstance(payload, dict) or payload.get('card_retrieval') != 1:
                continue
            ident = payload.get('id')
            if ident not in bank or payload.get('operation') != 'read' or payload.get('content') != bank.get(ident):
                errors.append({'item_id': item.get('id'), 'id': ident, 'reason': 'reader error or body mismatch'})
                continue
            reads.append({'order': order, 'item_id': item.get('id'), 'id': ident, 'mode': 'helper',
                'content_sha256': hashlib.sha256(bank[ident].encode()).hexdigest()})
            found.add(ident)
        if 'cards.json' in command:
            ids = [ident for ident, body in bank.items() if body in output or
                   any(json.dumps(body, ensure_ascii=ascii_only)[1:-1] in output for ascii_only in (True, False))]
            direct.append({'order': order, 'item_id': item.get('id'), 'command': command, 'full_body_ids': ids})
            reads.extend({'order': order, 'item_id': item.get('id'), 'id': ident, 'mode': 'direct',
                          'content_sha256': hashlib.sha256(bank[ident].encode()).hexdigest()}
                         for ident in ids if ident not in found)
    return {'read_calls': sum(x['mode'] == 'helper' for x in reads),
        'read_ids': sorted({x['id'] for x in reads}), 'events': reads,
        'direct_bank_access_commands': direct, 'reader_errors': errors,
        'upstream_exposure': 'requires exact content matching in captured provider requests',
        'application_correctness': 'manual review required; no-read and already-read reuse retained'}


def audit_reads(path, bank_path):
    bank = {x['id']: x['content'] for x in read(bank_path)['cards']}
    return audit_payloads([json.loads(line) for line in path.read_text().splitlines()], bank)


def calibration(root, parent):
    """Select reviewed records, never rerun the historical collectors or actors."""
    path = parent / 'all-task-retrieval-review/evidence.json'
    rows = read(path)['rows']
    def row(task, arm, round_number):
        return next(x for x in rows if (x['task'], x['arm'], x['round']) == (task, arm, round_number))
    no_read = row('Filter', 'new_skeleton', 1)
    rejected = row('Rely', 'new_skeleton', 2)
    first = row('DeMorgan', 'new_skeleton', 1)
    bulk = row('Rank', 'new_prose', 2)
    reuse = row('Unpack', 'new_skeleton', 2)
    require(not no_read['reads'], 'Unread calibration mismatch')
    require(first['first_read_after_edit'] and first['diagnostics'], 'First-read calibration mismatch')
    require(any(x['mode'] == 'bulk' for x in bulk['reads']), 'Bulk calibration mismatch')
    require(reuse['dual_600'] and reuse['edited_failures_after_last_read'], 'Reuse calibration mismatch')
    parser_checks = []
    for reviewed in (no_read, rejected, first, bulk, reuse):
        ep = Path(reviewed['episode']); raw = ep / 'codex_events.raw.jsonl'
        bank = ep.parents[1] / 'bundles' / reviewed['arm'] / 'cards.json'
        observed = audit_reads(raw, bank)
        expected = sorted((x['id'], x['card_id']) for x in reviewed['reads'])
        actual = sorted((x['item_id'], x['id']) for x in observed['events'])
        require(actual == expected and not observed['reader_errors'], 'Selected parser differs from reviewed evidence')
        parser_checks.append({'episode': str(ep), 'source_sha256': sha(raw),
            'exact_return_events_match_review': True, 'observed': observed})
    historical = parent.parent / 'fork-branch-retrieval-audit-20261023-v1/analysis.json'
    old = read(historical)['rows']
    active = next(x for x in old if x.get('active_failure_reread'))
    warning = next(x for x in old if x.get('reread_after_edited_failure') and not x.get('active_failure_reread'))
    snapshot = parent / 'final-review/snapshot.json'
    interrupted = read(snapshot)['infrastructure_attempt_history']
    require(bool(interrupted), 'Missing interruption fixture')
    selected = []
    for label, record in [('no_body_read', no_read), ('rejected_card', rejected),
                          ('first_read_after_failure', first), ('direct_bulk_read', bulk),
                          ('reuse_without_rereading', reuse), ('active_failure_reselection', active),
                          ('post_pass_warning_cleanup', warning)]:
        selected.append({'case': label, 'reviewed_record': record})
    write_json(root / 'offline-calibration.json', {
        'paid_calls': 0, 'historical_reanalysis': False,
        'source_hashes': {str(p): sha(p) for p in (path, historical, snapshot)},
        'cases': selected, 'five_selected_parser_checks': parser_checks, 'infrastructure_attempts': interrupted,
        'semantic_boundary': 'Rejection, obligation change, application and local progress require human review; no keyword proxy is counted as correct reassessment. Historical records remain researcher-only.'})


PROBE = r'''import hashlib,json,socket,subprocess,time
from pathlib import Path
p=json.loads(Path('probe.json').read_text())
for name,digest in p['hashes'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
for name in p['hidden']:
    try: Path(name).read_bytes()
    except OSError: pass
    else: raise AssertionError('Private file visible: '+name)
cards=json.loads(Path('cards.json').read_text())['cards'];assert len(cards)==10
for card in cards:
    assert set(card)=={'id','content'}
    r=subprocess.run(['/usr/bin/python3','card_read.py',card['id']],capture_output=True,text=True,check=True)
    assert json.loads(r.stdout)['content']==card['content']
library=Path(p['library'])/'set.rs';assert library.read_bytes()
try: library.open('r+b')
except OSError: pass
else: raise AssertionError('Library writable')
try: socket.create_connection(('1.1.1.1',443),timeout=1)
except OSError: pass
else: raise AssertionError('External network reachable')
Path('input.rs').write_text('use vstd::prelude::*;\nverus! { proof fn probe() {} }\nfn main() {}\n')
Path('candidate.rs').write_text(Path('input.rs').read_text().replace('probe() {}','probe() { assert(1int == 1int); }'))
records=[]
for tool,argv in [('verus',[p['verus'],'candidate.rs']),('lynette',[p['lynette'],'compare','-t','input.rs','candidate.rs'])]:
    before=hashlib.sha256(Path('candidate.rs').read_bytes()).hexdigest();started=time.monotonic()
    r=subprocess.run(argv,capture_output=True,text=True,timeout=45)
    after=hashlib.sha256(Path('candidate.rs').read_bytes()).hexdigest()
    records.append(dict(tool=tool,elapsed_seconds=time.monotonic()-started,before_sha256=before,after_sha256=after,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
    assert r.returncode==0 and before==after,r.stdout+r.stderr
Path('candidate.rs').write_text(Path('input.rs').read_text().replace('probe() {}','probe() { assert(false); }'))
r=subprocess.run([p['verus'],'candidate.rs'],capture_output=True,text=True,timeout=45)
assert r.returncode!=0
records.append(dict(tool='verus_negative_control',returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,candidate_sha256=hashlib.sha256(Path('candidate.rs').read_bytes()).hexdigest()))
started=time.monotonic()
try: subprocess.run(['/usr/bin/python3','-c','import time;time.sleep(5)'],timeout=.05)
except subprocess.TimeoutExpired: pass
else: raise AssertionError('Timeout not enforced')
assert time.monotonic()-started<2
print(json.dumps(dict(passed=True,reader_payloads=10,private_hidden=True,library_readonly=True,network_blocked=True,timeout_probe=True,verification_records=records)))
'''


def preflight(root, config, parent):
    results = []
    library = Path(config['verus_bin']).parent / 'vstd'
    for arm in ARMS:
        workspace = root / 'preflight' / arm
        shutil.copytree(root / 'bundles' / arm, workspace)
        private = evidence_paths(parent) + [DESIGN / 'RETRIEVAL_REASSESSMENT_PLAN.md',
            root / 'offline-calibration.json', root / 'config.json', Path(config['env_file'])]
        private += [root / 'bundles' / other / 'SKILL.md' for other in ARMS if other != arm]
        private += [REPO / x['source_path'] for x in read(parent / 'task-selection.json')['tasks']]
        write_json(workspace / 'probe.json', {'hidden': list(map(str, private)),
            'library': str(library), 'verus': config['verus_bin'], 'lynette': config['lynette_bin'],
            'hashes': {n: sha(workspace / n) for n in FROZEN}})
        isolation = e.prior.ActorIsolationConfig(Path(config['scratch_root']), library.parent,
            Path(config['rust_root']), 18136, (REPO, parent, root / 'config.json', Path(config['env_file']), Path(config['data_root'])))
        def isolated(argv):
            return e.prior.build_isolated_actor_command(argv, workspace=workspace,
                codex_bin=Path(argv[0]), lynette_bin=Path(config['lynette_bin']), config=isolation)
        r = subprocess.run(isolated(['/usr/bin/python3', '-c', PROBE]),
            env=e.prior._codex_environment(None), capture_output=True, text=True, timeout=60)
        version = subprocess.run(isolated([config['codex_bin'], '--version']),
            env=e.prior._codex_environment(None), capture_output=True, text=True, timeout=30)
        results.append({'arm': arm, 'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr,
            'codex_version': version.stdout, 'codex_returncode': version.returncode, 'isolation': isolation.manifest()})
        write_json(root / 'preflight.json', {'paid_calls': 0, 'checks': results})
        require(r.returncode == 0, 'Offline preflight failed: ' + r.stderr[-2000:])
        require(version.returncode == 0 and version.stdout.strip() == 'codex-cli 0.147.0', 'CLI changed')


def budget_plan(parent):
    snapshot = read(parent / 'final-review/snapshot.json')
    selected = [x for x in snapshot['rows'] if x['condition'] == 'new_skeleton' and x['task_id'] in TASK_IDS]
    require(len(selected) == 8, 'Historical budget reference mismatch')
    # Historical empirical estimate, not a request bound or a current-price claim.
    peak_costs = [(x['prompt_cache_hit_tokens'] * .044 + x['prompt_cache_miss_tokens'] * 1.32
                   + x['completion_tokens'] * 3.96) / 1e6 for x in selected]
    reserve = estimate_deepseek_request_upper_bound(131072, 'deepseek-v4-pro', price_band='peak')
    return {'status': 'proposal_only_not_authorized', 'proposed_new_batch_cap_usd': 20,
        'historical_8_episode_peak_repriced_usd': sum(peak_costs),
        '24_episode_same_usage_projection_usd': sum(peak_costs) * 3,
        '24_episode_all_at_historical_max_usd': max(peak_costs) * 24,
        'frozen_harness_request_reserve_usd': reserve, 'two_inflight_reserve_usd': 2 * reserve,
        'context_window_safe_reserve_usd': (1048576 * 1.32 + 131072 * 3.96) / 1e6,
        'safe_two_inflight_reserve_usd': 2 * (1048576 * 1.32 + 131072 * 3.96) / 1e6,
        'actor_slot_hours_max': 4, 'ideal_two_worker_hours_max': 2,
        'provider_drain_seconds_max': 1810,
        'requests_per_episode': 'adaptive; 131072 is per request, not per episode',
        'reference_source': str(parent / 'final-review/snapshot.json'),
        'pricing': 'Frozen historical harness peak rates, USD/M hit .044, miss 1.32, output 3.96; must verify actual tariff before launch. Reasoning is included in output.',
        'policy': 'Fresh batch ledger only after explicit new authorization; historical ledgers are read-only and not reset or reused as authority. USD20 is an enforceable stop ceiling, not a guarantee of 24 completions. No automatic paid retry or stage2 expansion.',
        'reserve_caveat': 'Unchanged bridge reserves 1,000,000 input tokens while context setting is 1,048,576. Driver guard floors each reservation at the larger conservative bound; actor/harness stays unchanged.'}


def prepare(root, parent):
    require(parent.name == 'on-demand-ten-card-seven-arm-resume-20261022-v3', 'Use the specified v3 baseline')
    require(not root.exists(), 'Fresh output root required')
    old = read(parent / 'validation_contract.json')
    config = read(parent / 'config.json')
    source = parent / 'bundles/new_skeleton'
    for name, digest in FROZEN.items():
        require(sha(source / name) == digest, 'Baseline mismatch: ' + name)
    # Only execution dependencies, not unrelated later scripts, must match v3.
    harness = {p: h for p, h in old['input_hashes'].items()
               if '/skill-evolution-pilot/src/' in p or '/skillopt-verusage/src/' in p
               or Path(p).name in ('validate_card_revision.py', 'export_codex_transcript.py')}
    require(harness and all(sha(p) == h for p, h in harness.items()), 'v3 harness changed')
    toolchain = {p: h for p, h in old['input_hashes'].items()
                 if Path(config['verus_bin']).parent in Path(p).parents
                 or (Path(config['rust_root']) in Path(p).parents and Path(p).name == 'rustc')}
    require(toolchain and all(sha(p) == h for p, h in toolchain.items()), 'v3 toolchain/library changed')
    for key in ('codex_bin', 'lynette_bin'):
        require(sha(config[key]) == e.prior.HISTORICAL[key], 'Tool changed: ' + key)
    require(sha(Path(config['verus_bin']).parent / 'rust_verify') == e.prior.LOCAL_RUST_VERIFY, 'Verifier changed')
    require(sha(Path(config['source_root']) / 'models.json') == e.prior.HISTORICAL['models.json'], 'Model catalog changed')
    items = [next(x for x in old['items'] if x['id'] == ident) for ident in TASK_IDS]
    for item in items:
        require('/unverified/' in item['source_path'] and sha(REPO / item['source_path']) == item['source_sha256'], 'Unsolved source changed')
    root.mkdir(parents=True)
    for name in ('EXECUTIVE.md', 'TASK.md', 'task-selection.json'):
        shutil.copyfile(parent / name, root / name)
    shutil.copyfile(DESIGN / 'RETRIEVAL_REASSESSMENT_PLAN.md', root / 'PLAN_SNAPSHOT.md')
    shutil.copyfile(DESIGN / 'REASSESSMENT_REVIEW_PROTOCOL.md', root / 'REVIEW_PROTOCOL.md')
    shutil.copytree(parent / 'runtime', root / 'runtime')
    config['source_root'] = str(root / 'runtime')
    write_json(root / 'config.json', config)
    for arm in ARMS:
        bundle = root / 'bundles' / arm
        bundle.mkdir(parents=True)
        for name in FROZEN:
            shutil.copyfile(source / name, bundle / name)
        if arm == ARMS[1]:
            (bundle / 'SKILL.md').write_bytes(revised_main((source / 'SKILL.md').read_bytes(), rule_text()))
    diff = ''.join(difflib.unified_diff((root / 'bundles' / ARMS[0] / 'SKILL.md').read_text().splitlines(True),
        (root / 'bundles' / ARMS[1] / 'SKILL.md').read_text().splitlines(True), fromfile='R0_current/SKILL.md', tofile='R1_reassess/SKILL.md'))
    (root / 'R0-R1.diff').write_text(diff)
    verify_materials(root, parent)
    calibration(root, parent)
    write_json(root / 'budget-proposal.json', budget_plan(parent))
    write_json(root / 'evidence-receipt.json', {'reviewed_section': 10, 'historical_reviews_rerun': False,
        'files': {str(p): sha(p) for p in evidence_paths(parent)}})
    preflight(root, config, parent)
    contract = {k: old[k] for k in ('model', 'reasoning_effort', 'timeout_seconds', 'workers',
        'installed_library_root', 'model_context_window', 'max_output_tokens_per_request', 'provider_request_timeout_seconds')}
    contract.update(schema_version='retrieval-reassessment-v1', parent_run=str(parent), items=items,
        schedule=schedule(), expected_episodes=24, repeats=3, budget_usd=20,
        installed_library_conditions=list(ARMS),
        bundle_paths={a: str(root / 'bundles' / a) for a in ARMS},
        artifacts={a: load_skill_artifact(root / 'bundles' / a).manifest() for a in ARMS},
        ordinary_retry=False, transport_retry=False, reference_proof_supplied=False, sealed_test_access=False,
        authorization='OFFLINE_ONLY; separate hash-bound user launch authorization required',
        request_scope='Only original unsolved input, this arm SKILL/index/ten-card bank, current candidate, tool diagnostics and allowed library snippets; no plan, reviews, historical proofs, checkpoints, other-arm outputs or sealed tests.',
        primary='Same candidate SHA256 Verus and Lynette pass observed within 600s; normal exit separate',
        caveat='Four known validation development tasks, three independent samples per arm; repeated numbers are schedule blocks, not shared random seeds. Reads alone are not improvement. Stage2 requires separate review and authorization.')
    files = [p for p in root.rglob('*') if p.is_file() and 'preflight' not in p.parts]
    files += [root / 'preflight.json', Path(__file__), DESIGN / 'REASSESSMENT_RULE.md']
    files += [REPO / x['source_path'] for x in items]
    files += [Path(config[k]) for k in ('codex_bin', 'verus_bin', 'lynette_bin')]
    files += [p for p in Path(config['verus_bin']).parent.rglob('*') if p.is_file()]
    files += [p for p in (REPO / 'scripts').glob('*.py') if p.name in (
        'evaluate_ten_card_seven_arm.py', 'evaluate_card_organization.py', 'evaluate_structural_skeleton_hard.py',
        'continue_card_organization_evaluation.py', 'summarize_success_timeout_tokens.py', 'build_card_organization.py')]
    contract['input_hashes'] = {**harness, **toolchain, **{str(p.resolve()): sha(p) for p in files}}
    write_json(root / 'source-hashes.json', contract['input_hashes'])
    write_json(root / 'validation_contract.json', contract)
    write_json(root / 'offline-status.json', {'paid_calls': 0, 'launch_authorized': False,
        'contract_sha256': sha(root / 'validation_contract.json'), 'episodes_prepared': 24})
    check(root)


def check(root):
    c = read(root / 'validation_contract.json')
    require(c['schema_version'] == 'retrieval-reassessment-v1', 'Wrong contract')
    require(c['schedule'] == schedule() and c['expected_episodes'] == 24, 'Matrix changed')
    require(c['workers'] == 2 and c['timeout_seconds'] == 600 and c['budget_usd'] == 20, 'Scope changed')
    require(c['model'] == 'deepseek-v4-pro' and c['reasoning_effort'] == 'max', 'Model changed')
    require(c['max_output_tokens_per_request'] == 131072 and c['model_context_window'] == 1048576, 'Token configuration changed')
    require(all(sha(p) == h for p, h in c['input_hashes'].items()), 'Frozen inputs changed')
    require(read(root / 'source-hashes.json') == c['input_hashes'], 'Hash manifest changed')
    require(read(root / 'offline-status.json')['contract_sha256'] == sha(root / 'validation_contract.json'), 'Contract changed since preparation')
    verify_materials(root, Path(c['parent_run']))
    checks = read(root / 'preflight.json')['checks']
    require([x['arm'] for x in checks] == list(ARMS) and all(x['returncode'] == 0 and x['codex_returncode'] == 0 for x in checks), 'Preflight incomplete')
    return c


def validate_authorization(root, path):
    require(path is not None, 'No API launch authorization supplied; offline preparation is not permission to run')
    a = read(path)
    expected = {'contract_sha256': sha(root / 'validation_contract.json'), 'approved': True,
        'episodes': 24, 'new_batch_cap_usd': 20, 'destination': 'https://api.deepseek.com',
        'automatic_paid_retry': False, 'background_launch': True, 'pricing_verified': True}
    require(all(a.get(k) == v for k, v in expected.items()), 'Authorization does not cover this exact batch')
    require(bool(a.get('user_instruction')) and bool(a.get('pricing_evidence')), 'Missing user authorization or current tariff evidence')
    return a


def report(root):
    c = read(root / 'validation_contract.json')
    if not (root / 'summary.json').exists():
        attempted = any((root / n).exists() for n in ('started.json', 'episodes', 'provider_calls.jsonl'))
        return {'status': 'started_without_summary' if attempted else 'offline_prepared_no_actor_results',
                'planned': 24, 'paid_calls': 'unknown_pending_ledger_review' if attempted else 0}
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
    result = {'planned': 24, 'completed': len(rows), 'rows': rows, 'failures': summary['failures'],
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
            e.prior.driver.run(config, root, c, expected_episodes=24,
                budget_guard=ConservativeMux([guard]), retrieval_auditor=lambda p: audit_reads(p,
                    root / 'bundles' / p.parent.name.split('--')[0].removeprefix('dev_') / 'cards.json'))
            report(root)
            require(read(root / 'summary.json')['completed_episodes'] == 24, 'Incomplete matrix')
        except BaseException as error:
            write_json(root / 'stopped.json', {'type': type(error).__name__, 'reason': str(error), 'automatic_retry': False})
            raise
        write_json(root / 'completed.json', {'episodes': 24, 'mechanism_review_pending': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', nargs='?', default='prepare', choices=['prepare', 'check', 'run', 'report'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--parent', type=Path)
    parser.add_argument('--authorization', type=Path)
    args = parser.parse_args(); root = e.prior.builder.output_root(args.output)
    if args.phase == 'prepare':
        require(args.parent is not None, '--parent v3 required')
        prepare(root, args.parent.resolve())
    elif args.phase == 'run':
        run(root, args.authorization)
    else:
        result = {'check': check, 'report': report}[args.phase](root)
        print(json.dumps({'status': 'checked', 'episodes': 24} if args.phase == 'check' else result))
