"""Offline diagnostic probes, not model reruns or prompt-efficacy measurements."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re

from skill_evolution_pilot.codex_runner import _run_complete
from skillopt_verusage.fork_card_optimize import _require_run_child
from verus_self_evolve.proof_progress import function_body_span


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_body(source, name, body):
    lines = source.splitlines(keepends=True)
    start, end = function_body_span(source, name)
    return ''.join(lines[:start]) + body + ''.join(lines[end:])


def fix_assert_parentheses(source):
    """Mechanical ablation of the observed one-line assertion syntax, not a solver."""
    return re.sub(r'^(\s*)assert (?!forall\b)([^\n]+);$', r'\1assert(\2);', source, flags=re.M)


def distinct_snapshots(episode):
    result = []
    for path in sorted((episode / 'snapshots').glob('*candidate.rs')):
        source = path.read_text()
        if not result or source != result[-1][1]:
            result.append((path, source))
    return result


def probe_specs(parent):
    episodes = parent / 'episodes'
    scope = episodes / 'dev_revised--3ce00a38706256ab00ea'
    initial_path = scope / 'workspace/input.rs'
    initial = initial_path.read_text()
    scoped = replace_body(initial, 'spec_entails_always_tla_forall', (
        '    let a_to_always: spec_fn(A) -> TempPred<T> = |a: A| always(a_to_p(a));\n'
        '    tla_forall_always_equality_variant::<T, A>(a_to_always, a_to_p);\n'
        '    spec_entails_tla_forall::<T, A>(spec, a_to_always);\n'
    ))
    syntax = episodes / 'dev_revised--9b9f6ccef89db4103c7f'
    syntax_path, broken = distinct_snapshots(syntax)[1]
    unfold = episodes / 'dev_revised--a23a4969155913255f76'
    unfold_path = unfold / 'workspace/candidate.rs'
    failed = unfold_path.read_text()
    explicit = replace_body(failed, 'lemma_entails_unfold', (
        '    assert forall |ex: Execution<T>| #[trigger] spec.satisfied_by(ex)\n'
        '        implies p.satisfied_by(ex) by {\n'
        '        assert((spec.implies(p)).satisfied_by(ex));\n'
        '    }\n'
    ))
    trigger = episodes / 'dev_old--aded79905be896942897'
    trigger_path = trigger / 'workspace/candidate.rs'
    verified = trigger_path.read_text()
    exact = 'assert((|a2: A| not(a_to_p(a2)))(a).satisfied_by(ex));'
    if verified.count(exact) != 1:
        raise ValueError('Expected the exact recorded lambda-instantiation step')
    reduced = verified.replace(exact, 'assert((not(a_to_p(a))).satisfied_by(ex));')
    return [
        ('scope_existing_lemmas', scope, initial_path, initial, scoped),
        ('syntax_parentheses_only', syntax, syntax_path, broken, fix_assert_parentheses(broken)),
        ('entailment_exact_term_only', unfold, unfold_path, failed, explicit),
        ('trigger_term_ablation', trigger, trigger_path, reduced, verified),
    ]


def run_probe(root, name, episode, source_path, before, after):
    result = {'name': name, 'evidence_source': str(source_path), 'evidence_sha256': sha(source_path),
              'interpretation': 'Offline intervention in observed code; not a fresh solve or a prompt treatment.'}
    directory = root / name
    directory.mkdir()
    (directory / 'change.diff').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile='before.rs', tofile='after.rs')))
    for variant, source in (('before', before), ('after', after)):
        workspace = directory / variant
        workspace.mkdir()
        (workspace / 'input.rs').write_bytes((episode / 'workspace/input.rs').read_bytes())
        candidate = workspace / 'candidate.rs'
        candidate.write_text(source)
        checks = {}
        for tool, arguments in (('verus', ['candidate.rs']), ('lynette', [])):
            wrapper = episode / 'workspace/tools' / f'run_{tool}.sh'
            check = _run_complete(['bash', str(wrapper), *arguments], cwd=workspace, timeout_seconds=30)
            (workspace / f'{tool}.stdout.txt').write_text(check['stdout'])
            (workspace / f'{tool}.stderr.txt').write_text(check['stderr'])
            checks[tool] = {**check, 'wrapper_sha256': sha(wrapper)}
        result[variant] = {'candidate_sha256': sha(candidate), 'checks': checks,
                           'external_body_attributes': source.count('#[verifier::external_body]')}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    parent = args.parent.resolve()
    root = _require_run_child(args.output)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError('Refuse to overwrite an existing analysis')
    summary = parent / 'summary.json'
    original_hash = sha(summary)
    specs = probe_specs(parent)
    evidence = {str(path): sha(path) for _, episode, source_path, _, _ in specs
                for path in (source_path, episode / 'workspace/input.rs',
                             episode / 'workspace/tools/run_verus.sh',
                             episode / 'workspace/tools/run_lynette.sh')}
    results = []
    for spec in specs:
        result = run_probe(root, *spec)
        results.append(result)
        print(json.dumps({'case': result['name'], **{
            variant: {tool: result[variant]['checks'][tool]['returncode']
                      for tool in ('verus', 'lynette')} for variant in ('before', 'after')}}), flush=True)
    unchanged = original_hash == sha(summary) and all(sha(Path(path)) == value for path, value in evidence.items())
    record = {'parent_summary_sha256': original_hash, 'evidence_hashes': evidence,
              'inputs_unchanged': unchanged, 'probes': results,
              'claim_boundary': 'Local solver mechanism checks only; no model/prompt efficacy measurement.'}
    (root / 'probes.json').write_text(json.dumps(record, indent=2) + '\n')
    if not unchanged:
        raise ValueError('Frozen evidence changed during analysis')


if __name__ == '__main__':
    main()
