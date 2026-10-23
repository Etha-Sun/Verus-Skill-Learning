import copy
import difflib
import json

import pytest

from extract_grounded_cards import (
    AUTH, apply_diff, build_registry, check, digest, guards,
    validate_cards, validate_observations,
)
from skillopt_verusage.guarded_deepseek import BudgetMux


def fixture():
    before = 'fn main() {\n    old();\n}\n'
    after = 'fn main() {\n    new();\n}\n'
    def event(i, code, output, status='item.completed'):
        return {'event_index': i, 'candidate_sha256': digest(code), 'data': {
            'raw_codex_event': {'type': status, 'item': {'id': f'cmd-{i}',
                'type': 'command_execution', 'command': "/bin/bash -lc './tools/run_verus.sh candidate.rs'",
                'exit_code': 0 if '0 errors' in output else 1, 'aggregated_output': output}}}}
    chain = [
        {'event_index': 0, 'candidate_sha256': digest(before), 'previous_candidate_sha256': None, 'diff_content': {}},
        {'event_index': 4, 'candidate_sha256': digest(after), 'previous_candidate_sha256': digest(before),
         'diff_content': ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True)))},
    ]
    trace = {'snapshots': {'baseline': before, 'chain': chain}, 'events': [
        event(1, before, 'not a completed diagnostic', 'item.started'),
        event(2, before, 'verification results: 0 verified, 1 errors'),
        event(5, after, 'verification results: 1 verified, 0 errors'),
        event(7, after, 'verification results: 1 verified, 0 errors'),
    ]}
    group = {'source_task': 'train', 'trace_ids': ['train:original', 'train:fork'],
        'original': {'trace_id': 'train:original', 'complete_trace': trace},
        'forks': [{'trace_id': 'train:fork', 'complete_suffix': copy.deepcopy(trace),
                  'augmented_trace_recipe': {'original_event_prefix_length': 2}}],
        'forbidden_names': [],
        'evidence_ids': [f'{t}/event:{i}' for t in ['train:original', 'train:fork'] for i in [2, 5, 7]] +
                        [f'{t}/snapshot:{digest(after)}' for t in ['train:original', 'train:fork']]}
    registry = build_registry(group)
    value = {'trace_analyses': [{'trace_key': k, 'observation': 'One local change followed by a repeated check.'}
                              for k in registry['traces']],
        'observations': [{'window_key': 'T0W000', 'before_quote': '0 verified, 1 errors',
            'after_quote': '1 verified, 0 errors', 'observation': 'The edited source passed.',
            'remaining_obligations': 'No failed obligation printed.', 'confounding': 'Mechanism unproven.',
            'inspection_guidance': 'Inspect the declaration before deriving a local probe.'}]}
    return group, registry, value


def test_source_reconstruction_rejects_tampered_context():
    before, after = 'a\nb\nc\n', 'a\nz\nc\n'
    patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True)))
    assert apply_diff(before, patch) == after
    with pytest.raises(ValueError, match='context differs'):
        apply_diff('changed\nb\nc\n', patch)
    assert apply_diff('a', '--- a\n+++ b\n@@ -1 +1 @@\n-a\n\\ No newline at end of file\n+b\n\\ No newline at end of file\n') == 'b'


def test_registry_keeps_negative_and_same_hash_windows_excludes_lifecycle():
    group, registry, _ = fixture()
    assert registry['coverage']['eligible_checks'] == 6
    assert registry['coverage']['adjacent_windows'] == 4
    assert registry['windows']['T0W001']['same_hash'] is True
    assert registry['windows']['T0W000']['changed_snapshots'] == 1
    assert all('/event:1' not in r['canonical_ref'] for r in registry['records'].values())
    assert registry['records']['T1C000']['canonical_ref'] == 'train:fork/event:2'
    group['original']['complete_trace']['snapshots']['chain'][1]['candidate_sha256'] = 'fabricated'
    with pytest.raises(ValueError, match='hash mismatch'):
        build_registry(group)


def test_evidence_gate_accepts_exact_coverage_but_rejects_invented_refs_and_quotes():
    _, registry, value = fixture()
    admitted = validate_observations(value, registry)
    assert admitted[0]['evidence_refs'][:2] == ['train:original/event:2', 'train:original/event:5']
    for change in ('quote', 'window', 'coverage'):
        bad = copy.deepcopy(value)
        if change == 'quote': bad['observations'][0]['after_quote'] = 'fabricated successful verification'
        if change == 'window': bad['observations'][0]['window_key'] = 'T9W000'
        if change == 'coverage': bad['trace_analyses'].append(bad['trace_analyses'][0])
        with pytest.raises(ValueError): validate_observations(bad, registry)


def test_card_provenance_is_host_derived_and_templates_are_rejected():
    group, registry, value = fixture()
    observations = {o['observation_key']: o for o in validate_observations(value, registry)}
    content = ('**Trigger:** A local check fails. **Action:** Inspect the declaration and current typed objects. '
               '**Why:** One source shows an observational transition. **Validate:** Recheck the same obligation. '
               '**Avoid when:** A logical premise is absent.')
    card = {'content': content, 'observation_keys': list(observations), 'limitations': ['Single source.']}
    result = validate_cards({'cards': [card]}, observations, [group])
    assert result[0]['source_tasks'] == ['train']
    assert result[0]['evidence_refs'] == next(iter(observations.values()))['evidence_refs']
    card['content'] = content.replace('Inspect the declaration and current typed objects.', 'Insert `assert(goal);`.')
    with pytest.raises(ValueError): validate_cards({'cards': [card]}, observations, [group])


def test_inherited_cost_and_frozen_input_guards(tmp_path):
    (tmp_path / 'authorization.json').write_text(json.dumps({'inherited_cost_usd': 3.625829504}))
    mux = BudgetMux(guards(tmp_path))
    key = mux.reserve(2.95)
    with pytest.raises(Exception): mux.reserve(.5)
    mux.settle(key, cost_usd=.9, usage={})
    assert json.loads((tmp_path / 'budget-total.json').read_text())['prior_spend_usd'] == 3.625829504
    source = tmp_path / 'request.json'; source.write_text('frozen')
    (tmp_path / 'contract.json').write_text(json.dumps({'authorization': AUTH, 'input_hashes': {str(source): digest('frozen')}}))
    check(tmp_path)
    source.write_text('changed')
    with pytest.raises(ValueError, match='Frozen input changed'): check(tmp_path)
