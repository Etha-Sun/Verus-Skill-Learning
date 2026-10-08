import copy
import difflib
import hashlib
import unittest

from skillopt_verusage.checkpoint_selection import continuation_context, select_checkpoints, visible_prefix


def fixture(states=None):
    states = states or [(1, 0, 0, 2, 100), (1, 0, 0, 2, 500),
                        (1, 1, 0, 1, 600), (1, 1, 0, 1, 900)]
    snapshots, events, chain, curve = {}, [], [], []
    base = 'verus! { proof fn target() {} proof fn helper() {} }'
    first_hash = hashlib.sha256(base.encode()).hexdigest()
    snapshots[first_hash] = base
    events.append({'event_index': 1, 'actor': 'host', 'type': 'lifecycle', 'candidate_sha256': first_hash})
    chain.append({'event_index': 1, 'boundary': 'initial', 'candidate_sha256': first_hash})
    chain[0]['diff_content'] = ''.join(difflib.unified_diff([], base.splitlines(keepends=True)))
    previous = base
    for n, (tier, target, helper, errors, tokens) in enumerate(states):
        source = f'verus! {{ proof fn target() {{ assert({n} == {n}); }} proof fn helper() {{}} }}'
        code_hash = hashlib.sha256(source.encode()).hexdigest()
        snapshots[code_hash] = source
        index = 2+2*n
        output = ('error[E0425]: missing function' if tier == 0 else
                  f'verification results:: 0 verified, {errors or 0} errors')
        raw = {'type': 'item.completed', 'item': {'id': f'item_{n}', 'type': 'command_execution',
               'command': './tools/run_verus.sh', 'aggregated_output': output, 'exit_code': int(tier != 2)}}
        events.append({'event_index': index, 'actor': 'codex', 'candidate_sha256': code_hash,
                       'data': {'raw_codex_event': raw}})
        events.append({'event_index': index+1, 'actor': 'host', 'candidate_sha256': code_hash})
        chain.append({'event_index': index+1, 'boundary': f'command_execution:item_{n}', 'candidate_sha256': code_hash})
        chain[-1]['diff_content'] = ''.join(difflib.unified_diff(previous.splitlines(keepends=True), source.splitlines(keepends=True)))
        previous = source
        curve.append({'event_index': index, 'tool_call_id': f'item_{n}', 'candidate_sha256': code_hash,
                      'verifier_tier': tier, 'verifier_output': output, 'cumulative_output_tokens': tokens,
                      'proof_coverage': (target+helper)/20, 'target_proof_coverage': target/10,
                      'component_coverage': [{'key': 'target', 'matched_lines': target, 'reference_lines': 10},
                                             {'key': 'helper', 'matched_lines': helper, 'reference_lines': 10}],
                      'verifier': {'reported_errors': errors}})
    trace = {'events': events, 'snapshots': {'chain': chain, 'baseline': base}, 'original_input': base,
             'final_source': source, 'supplemental_raw': [], 'prompt': 'solve',
             'result': {'hard': 1, 'fidelity': 'V2_TRACE', 'actor_model': 'deepseek-v4-pro',
                        'actor_reasoning_effort': 'max', 'source_sha256': first_hash, 'skill_sha256': 'seed'}}
    report = {'function_name': 'target', 'curve': curve, 'reference_kind': 'synthetic_test'}
    return report, trace, snapshots


class SelectionTests(unittest.TestCase):
    def test_longest_joint_platform_first_and_exact_three(self):
        report, trace, snapshots = fixture()
        result = select_checkpoints(report, trace, snapshots)
        self.assertEqual(len(result['selected']), 3)
        self.assertEqual([c['event_index'] for c in result['selected'][:2]], [3, 7])
        self.assertEqual(result['selected'][0]['output_token_span'], 400)
        self.assertEqual(result, select_checkpoints(report, trace, snapshots))

    def test_helper_progress_and_offsetting_counts_do_not_make_a_platform(self):
        report, trace, snapshots = fixture([(1, 2, 0, 1, 100), (1, 1, 1, 1, 500),
                                           (1, 1, 2, 1, 600), (1, 2, 2, 1, 800)])
        self.assertTrue(all(c['fallback'] for c in select_checkpoints(report, trace, snapshots)['selected']))
        # Target-only control sees the unchanged target even while helpers improve.
        control = select_checkpoints(report, trace, snapshots, policy='coverage_top3_v1')
        self.assertEqual(control['selected'][0]['kind'], 'target_platform_start')

    def test_error_count_improvement_breaks_platform_unknown_is_not_zero(self):
        report, trace, snapshots = fixture([(1, 0, 0, 3, 100), (1, 0, 0, 1, 500),
                                           (1, 1, 0, None, 600), (1, 1, 0, 0, 800)])
        result = select_checkpoints(report, trace, snapshots)
        self.assertEqual(result['selected'][0]['event_index'], 7)
        self.assertFalse(result['selected'][0]['error_counts_known'])

    def test_unknown_error_count_inside_a_platform_is_not_labeled_known(self):
        report, trace, snapshots = fixture([(1, 0, 0, 1, 100), (1, 0, 0, None, 200),
                                           (1, 0, 0, 1, 300), (1, 1, 0, 1, 400)])
        self.assertFalse(select_checkpoints(report, trace, snapshots)['selected'][0]['error_counts_known'])

    def test_compile_regression_span_can_end_at_first_success(self):
        report, trace, snapshots = fixture([(1, 1, 0, 1, 100), (0, 0, 0, None, 300),
                                           (2, 3, 0, 0, 900)])
        # A separate initial prefix plus proof failure fills the other two slots.
        result = select_checkpoints(report, trace, snapshots)
        regression = next(c for c in result['selected'] if c['kind'] == 'compile_regression_after')
        self.assertEqual(regression['output_token_span'], 600)

    def test_continuous_compiler_failure_has_at_most_one_point(self):
        report, trace, snapshots = fixture([(1, 1, 0, 1, 100), (0, 0, 0, None, 300),
            (0, 0, 0, None, 600), (0, 0, 0, None, 900), (1, 2, 0, 1, 1000)])
        selected = select_checkpoints(report, trace, snapshots)['selected']
        self.assertEqual(sum(c['compile_episode'] is not None for c in selected), 1)

    def test_unknown_tier_without_actual_compiler_error_is_not_regression(self):
        report, trace, snapshots = fixture([(1, 0, 0, 1, 100), (0, 1, 0, None, 200),
                                           (1, 2, 0, 1, 300), (1, 3, 0, 1, 400)])
        report['curve'][1]['verifier_output'] = 'process timeout, no diagnostics'
        selected = select_checkpoints(report, trace, snapshots)['selected']
        self.assertFalse(any(c['kind'] == 'compile_regression_after' for c in selected))

    def test_passing_code_and_post_success_boundaries_are_excluded(self):
        report, trace, snapshots = fixture([(1, 0, 0, 1, 100), (1, 1, 0, 1, 200),
            (1, 2, 0, 1, 300), (2, 3, 0, 0, 400), (1, 4, 0, 1, 500)])
        passing_hash = report['curve'][3]['candidate_sha256']
        selected = select_checkpoints(report, trace, snapshots)['selected']
        self.assertTrue(all(c['event_index'] < 8 and c['checkpoint_sha256'] != passing_hash for c in selected))

    def test_new_provider_uses_same_validation_and_duplicate_filter(self):
        report, trace, snapshots = fixture()
        def custom(context):
            return [{'event_index': i, 'kind': 'custom', 'reason': 'test', 'fallback': False,
                     'output_token_span': i} for i in [999, 9, 9, 7, 5]]
        selected = select_checkpoints(report, trace, snapshots, policy='custom-v1', providers=[custom])['selected']
        self.assertEqual([c['event_index'] for c in selected], [9, 7, 5])
        self.assertEqual({c['policy'] for c in selected}, {'custom-v1'})

    def test_no_reference_still_fills_three_without_inventing_coverage(self):
        report, trace, snapshots = fixture()
        report['reference_kind'] = 'no_verified_reference'
        for row in report['curve']:
            row.pop('component_coverage'); row.pop('proof_coverage'); row.pop('target_proof_coverage')
        self.assertTrue(all(c['fallback'] for c in select_checkpoints(report, trace, snapshots)['selected']))

    def test_prefix_has_no_future_or_started_events_and_is_hash_bound(self):
        report, trace, snapshots = fixture()
        cp = select_checkpoints(report, trace, snapshots)['selected'][0]
        prefix = visible_prefix(trace, cp)
        text, code_hash = continuation_context(trace, cp)
        self.assertEqual(len(prefix), 1)
        self.assertNotIn('item_1', text)
        self.assertEqual(code_hash, cp['visible_prefix_sha256'])
        bad = copy.deepcopy(cp); bad['checkpoint_sha256'] = 'wrong'
        with self.assertRaises(ValueError): visible_prefix(trace, bad)

    def test_probe_cannot_cut_off_target_or_be_selected(self):
        report, trace, snapshots = fixture()
        row = report['curve'][0]
        probe = 'verus! { proof fn other() {} }'
        code_hash = hashlib.sha256(probe.encode()).hexdigest()
        snapshots[code_hash] = probe
        row.update(candidate_sha256=code_hash, verifier_tier=2)
        row['component_coverage'][0]['matched_lines'] = None
        for event in trace['events'][1:3]: event['candidate_sha256'] = code_hash
        trace['snapshots']['chain'][1]['candidate_sha256'] = code_hash
        self.assertTrue(all(c['checkpoint_sha256'] != code_hash for c in select_checkpoints(report, trace, snapshots)['selected']))

    def test_preservation_rejection_falls_back_and_is_recorded(self):
        report, trace, snapshots = fixture()
        result = select_checkpoints(report, trace, snapshots, checkpoint_allowed=lambda cp: cp['event_index'] != 3)
        self.assertEqual(len(result['selected']), 3)
        self.assertNotIn(3, [cp['event_index'] for cp in result['selected']])
        self.assertEqual(result['rejected_checkpoints'][0]['event_index'], 3)


if __name__ == '__main__':
    unittest.main()
