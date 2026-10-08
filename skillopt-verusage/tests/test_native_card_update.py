import copy
import difflib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from skillopt_verusage.campaign_evidence import expand_strings
from skillopt_verusage.checkpoint_selection import select_checkpoints
from skillopt_verusage.native_card_update import audit_response, paired_groups, task_group, update_cards
from test_checkpoint_selection import fixture


CARD = ('**Trigger:** Repeated unproved implication.\n**Action:** Establish its missing premise.\n'
        '**Why:** A conclusion depends on that premise.\n**Validate:** Run both validators.\n'
        '**Avoid when:** The premise is already established.')


def group_fixture(ident):
    report, original, snapshots = fixture()
    points = select_checkpoints(report, original, snapshots)['selected']
    forks = []
    for cp in points:
        branch = copy.deepcopy(original)
        branch['snapshots']['baseline'] = snapshots[cp['checkpoint_sha256']]
        branch['snapshots']['chain'] = [
            {'event_index': 1, 'boundary': 'initial', 'candidate_sha256': cp['checkpoint_sha256'],
             'diff_content': ''.join(difflib.unified_diff([], branch['snapshots']['baseline'].splitlines(keepends=True)))},
            {'event_index': 9, 'boundary': 'final', 'candidate_sha256': original['snapshots']['chain'][-1]['candidate_sha256'],
             'diff_content': ''.join(difflib.unified_diff(branch['snapshots']['baseline'].splitlines(keepends=True),
                                                       branch['final_source'].splitlines(keepends=True)))}]
        branch['result']['hard'] = 0
        branch['result']['timeout'] = True
        hint = {'source_task': ident, 'checkpoint_id': cp['checkpoint_id'],
                'hint': {'checkpoint_sha256': cp['checkpoint_sha256'],
                         'hint_text': 'Consider an intermediate premise'},
                'screen': {'automatic_screen_passed': True}}
        forks.append({'checkpoint': cp, 'trace': branch, 'hint': hint,
                      'visible_prefix_sha256': cp['visible_prefix_sha256']})
    return original, forks, task_group(ident, original, forks)


class FakeClient:
    def __init__(self, *, omit_trace=False, no_cards=False, bad_ref=False):
        self.calls = []
        self.omit_trace, self.no_cards, self.bad_ref = omit_trace, no_cards, bad_ref

    def call(self, **kwargs):
        self.calls.append(kwargs)
        packet = expand_strings(json.loads(kwargs['user']))
        groups = packet['task_groups']
        analyses = [{'trace_id': tid, 'observation': 'Inspect actual outcome and suffix evidence'}
                    for g in groups for tid in g['trace_ids']]
        if self.omit_trace: analyses.pop()
        cards = [] if self.no_cards else [{'content': CARD,
             'evidence_refs': ['invented'] if self.bad_ref else [g['evidence_ids'][0] for g in groups],
             'source_tasks': [g['source_task'] for g in groups], 'limitations': ['Mock provider; no utility claim']}]
        return json.dumps({'trace_analyses': analyses, 'cards': cards}), {'mock': True}


class NativeCardTests(unittest.TestCase):
    def test_real_native_reflect_one_call_two_questions_eight_traces(self):
        from skillopt.gradient import reflect
        groups = [group_fixture(ident)[2] for ident in ('one', 'two')]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); seed = base/'seed.md'; seed.write_text('unchanged initial skill')
            client = FakeClient(); old = reflect.chat_optimizer
            with patch.dict(os.environ, {'VERUS_SKILL_RUN_ROOT': str(base), 'SKILLOPT_PATH_REFERENCES': '1'}), \
                 patch('skillopt.gradient.reflect.run_minibatch_reflect', wraps=reflect.run_minibatch_reflect) as native:
                bank = update_cards(groups, seed, base/'update', client)
                self.assertEqual(os.environ['SKILLOPT_PATH_REFERENCES'], '1')
            self.assertIs(reflect.chat_optimizer, old)
            self.assertEqual(native.call_args.kwargs['minibatch_size'], 2)
            self.assertEqual(len(client.calls), 1)
            packet = expand_strings(json.loads(client.calls[0]['user']))
            self.assertEqual(packet['contract']['logical_traces'], 8)
            self.assertEqual(packet['task_groups'], paired_groups(groups)[0])
            self.assertEqual(len(json.loads(bank.read_text())['cards']), 1)
            metadata = json.loads((bank.parent/'update.json').read_text())
            self.assertEqual(metadata['source_weights'], {'one': 1, 'two': 1})
            self.assertFalse(metadata['generic_skill_edits_applied'])
            self.assertEqual(seed.read_text(), 'unchanged initial skill')

    def test_all_four_traces_and_failed_branch_results_are_kept(self):
        _, _, group = group_fixture('one')
        self.assertEqual(len(group['trace_ids']), 4)
        self.assertTrue(all(not f['complete_suffix']['result']['hard'] for f in group['forks']))
        self.assertTrue(all(f['augmented_trace_recipe']['original_event_prefix_length'] > 0 for f in group['forks']))

    def test_missing_branch_prefix_hash_or_hint_screen_rejected(self):
        original, forks, _ = group_fixture('one')
        with self.assertRaisesRegex(ValueError, 'three'):
            task_group('one', original, forks[:2])
        forks[0]['visible_prefix_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'prefix'):
            task_group('one', original, forks)
        forks[0]['visible_prefix_sha256'] = forks[0]['checkpoint']['visible_prefix_sha256']
        forks[0]['hint']['screen']['automatic_screen_passed'] = False
        with self.assertRaisesRegex(ValueError, 'Unscreened'):
            task_group('one', original, forks)

    def test_bad_response_does_not_apply_edits_or_silently_drop_a_batch(self):
        from skillopt.gradient import reflect
        groups = [group_fixture(ident)[2] for ident in ('one', 'two')]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); seed = base/'seed.md'; seed.write_text('seed')
            old = reflect.chat_optimizer
            with patch.dict(os.environ, {'VERUS_SKILL_RUN_ROOT': str(base)}):
                with self.assertRaisesRegex(RuntimeError, 'every trace'):
                    update_cards(groups, seed, base/'bad', FakeClient(omit_trace=True))
            self.assertIs(reflect.chat_optimizer, old)
            self.assertFalse((base/'bad/cards.json').exists())

    def test_full_pair_context_admission_happens_before_any_call(self):
        groups = [group_fixture(ident)[2] for ident in ('one', 'two')]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); seed = base/'seed.md'; seed.write_text('seed')
            client = FakeClient()
            with patch.dict(os.environ, {'VERUS_SKILL_RUN_ROOT': str(base)}):
                with self.assertRaisesRegex(ValueError, 'context admission'):
                    update_cards(groups, seed, base/'large', client, max_request_bytes=100)
            self.assertEqual(client.calls, [])
            self.assertFalse((base/'large').exists())

    def test_exact_card_dedup_preserves_distinct_source_evidence(self):
        groups = [group_fixture(ident)[2] for ident in ('one', 'two', 'three', 'four')]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); seed = base/'seed.md'; seed.write_text('seed')
            client = FakeClient()
            with patch.dict(os.environ, {'VERUS_SKILL_RUN_ROOT': str(base)}):
                bank = update_cards(groups, seed, base/'dedup', client)
            self.assertEqual(len(client.calls), 2)
            self.assertEqual(len(json.loads(bank.read_text())['cards']), 1)
            provenance = json.loads((bank.parent/'provenance.json').read_text())['card-001']
            self.assertEqual(len(provenance), 2)
            self.assertEqual({t for p in provenance for t in p['source_tasks']}, {'one', 'two', 'three', 'four'})

    def test_token_admission_checks_every_complete_pair_before_transport(self):
        groups = [group_fixture(ident)[2] for ident in ('one', 'two', 'three', 'four')]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); seed = base/'seed.md'; seed.write_text('seed')
            client = FakeClient(); admitted = []
            def admit(**kwargs):
                self.assertEqual(client.calls, [])
                packet = expand_strings(json.loads(kwargs['user']))
                self.assertEqual(packet['contract']['logical_traces'], 8)
                self.assertEqual(kwargs['cap'], 16384)
                admitted.append(kwargs['user'])
                return {'method': 'test-tokenizer', 'complete': True}
            with patch.dict(os.environ, {'VERUS_SKILL_RUN_ROOT': str(base)}):
                bank = update_cards(groups, seed, base/'admitted', client,
                                    max_request_bytes=1, admit=admit)
            self.assertEqual(len(admitted), 2)
            self.assertEqual({c['user'] for c in client.calls}, set(admitted))
            self.assertTrue(bank.exists())
            self.assertEqual(len(list((bank.parent/'admission').glob('*.json'))), 2)

    def test_failed_token_admission_never_starts_transport(self):
        groups = [group_fixture(ident)[2] for ident in ('one', 'two', 'three', 'four')]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); seed = base/'seed.md'; seed.write_text('seed')
            client = FakeClient(); admitted = []
            def admit(**kwargs):
                admitted.append(kwargs['user'])
                if len(admitted) == 2:
                    raise ValueError('second complete pair fails token admission')
                return {'method': 'test-tokenizer'}
            with patch.dict(os.environ, {'VERUS_SKILL_RUN_ROOT': str(base)}):
                with self.assertRaisesRegex(ValueError, 'second complete pair'):
                    update_cards(groups, seed, base/'rejected', client, admit=admit)
            self.assertEqual(client.calls, [])
            self.assertFalse((base/'rejected/cards.json').exists())

    def test_original_only_comparator_uses_same_native_two_question_batch(self):
        groups = [task_group(ident, group_fixture(ident)[0], augmented=False) for ident in ('one', 'two')]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); seed = base/'seed.md'; seed.write_text('seed')
            client = FakeClient(no_cards=True)
            with patch.dict(os.environ, {'VERUS_SKILL_RUN_ROOT': str(base)}):
                bank = update_cards(groups, seed, base/'original', client)
            self.assertEqual(json.loads(bank.read_text())['cards'], [])
            self.assertEqual(expand_strings(json.loads(client.calls[0]['user']))['contract']['logical_traces'], 2)

    def test_unknown_refs_and_false_source_support_rejected(self):
        groups = [group_fixture(ident)[2] for ident in ('one', 'two')]
        client = FakeClient(bad_ref=True)
        from skillopt_verusage.campaign_evidence import shared_strings
        response, _ = client.call(user=json.dumps(shared_strings({'task_groups': groups})))
        with self.assertRaisesRegex(ValueError, 'evidence'):
            audit_response(json.loads(response), groups)

    def test_pairing_is_identical_for_original_only_and_augmented_conditions(self):
        augmented = [group_fixture(ident)[2] for ident in ('one', 'two', 'three', 'four')]
        original_only = []
        for group in augmented:
            reduced = copy.deepcopy(group)
            reduced['forks'] = []; reduced['trace_ids'] = reduced['trace_ids'][:1]
            original_only.append(reduced)
        ids = lambda batches: [[g['source_task'] for g in b] for b in batches]
        self.assertEqual(ids(paired_groups(augmented)), ids(paired_groups(original_only)))


class CampaignWiringTests(unittest.TestCase):
    def test_three_isolated_forks_feed_one_two_question_card_batch(self):
        from skillopt_verusage.augmentation_campaign import Campaign
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            campaign = Campaign.__new__(Campaign)
            campaign.root = base/'campaign'
            campaign.repo = Path(__file__).resolve().parents[2]
            campaign.prompts = campaign.repo/'skillopt-verusage/prompts'
            campaign.seed = base/'seed.md'; campaign.seed.write_text('seed')
            campaign.selection = {}; campaign.traces = {}; campaign.refs = {}; campaign.snapshots = {}
            campaign.items = [{'id': ident, 'task_id': 'IR__target'} for ident in ('one', 'two')]
            campaign.hints = {}; campaign.branches = {}; campaign.config = {}
            campaign.progress = {'hint_completed': 0, 'hint_rejected': 0}
            campaign.lock = __import__('threading').Lock()
            campaign.update = lambda **changes: campaign.progress.update(changes)
            branch_traces = {}
            for item in campaign.items:
                report, trace, snapshots = fixture()
                ident = item['id']
                campaign.selection[ident] = select_checkpoints(report, trace, snapshots)
                report_path = base/(ident+'-report.json')
                report_path.write_text(json.dumps({**report,'reference_kind':'verifier_greedy_pruned'}))
                from skillopt_verusage.campaign_evidence import sha
                campaign.selection[ident]['report_binding'] = {'report_path':str(report_path),
                                                               'report_sha256':sha(report_path)}
                campaign.traces[ident], campaign.snapshots[ident] = trace, snapshots
                campaign.refs[ident] = ['event:2']
                _, forks, _ = group_fixture(ident)
                for fork in forks:
                    branch_traces[campaign.root/'augmentation'/ident/fork['checkpoint']['checkpoint_id']] = fork['trace']
            def teach(**kwargs):
                packet = expand_strings(json.loads(kwargs['user']))
                self.assertIn('curve',packet['proof_progress'])
                return json.dumps({'schema_version': 'hint-v1',
                    'checkpoint_sha256': packet['checkpoint']['checkpoint_sha256'],
                    'hint_text': 'Establish the missing premise, then check the diagnostic.',
                    'evidence_refs': [{'source_id': 'event:2', 'observation': 'A proof obligation failed'}],
                    'relation_to_original': 'alternative_supported_action', 'limitations': []}), {}
            campaign.teacher = Mock(); campaign.teacher.call.side_effect = teach
            def run_actor(item, bridge, skill, destination, *args):
                self.assertFalse(destination.exists(), 'Runner output must be empty before launch')
                self.assertTrue((campaign.root/'hints'/item['id']/destination.name/'fork_contract.pending.json').exists())
                return branch_traces[destination]['result']
            campaign.actor = Mock(side_effect=run_actor)
            client = FakeClient()
            campaign.extractors = {'augmented': client}
            with patch.dict(os.environ, {'VERUS_SKILL_RUN_ROOT': str(base)}), \
                 patch('skillopt_verusage.augmentation_campaign.require_design_review'), \
                 patch('skillopt_verusage.augmentation_campaign.load_trace', side_effect=lambda path: (branch_traces[path], [], {})):
                for item in campaign.items:
                    campaign.hint_branch(item, {})
                bank = campaign.extract_batches('augmented')
            self.assertEqual(campaign.actor.call_count, 6)
            self.assertEqual(len(campaign.hints), 6)
            self.assertEqual(len(campaign.branches), 6)
            self.assertEqual(len({call.args[3] for call in campaign.actor.call_args_list}), 6)
            self.assertEqual({call.args[5] for call in campaign.actor.call_args_list},
                             {'hint_actor_cp1', 'hint_actor_cp2', 'hint_actor_cp3'})
            self.assertTrue(all('past, completed actor observations' in call.args[7]
                                for call in campaign.actor.call_args_list))
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(len(json.loads(bank.read_text())['cards']), 1)


if __name__ == '__main__':
    unittest.main()
