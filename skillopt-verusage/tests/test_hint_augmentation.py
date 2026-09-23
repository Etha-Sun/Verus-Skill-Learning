import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hint_augmentation',ROOT/'scripts/run_hint_augmentation.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class HintBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.contract={'checkpoint_sha256':'a'*64,'evidence_ids':['event:33']}
        self.schema=json.loads((ROOT/'prompts/checkpoint_hints/hint_output.schema.json').read_text())
        self.hint={'schema_version':'hint-v1','checkpoint_sha256':'a'*64,'hint_text':'Establish existence of the witness under the current branch premise, then check the verifier diagnostic.','evidence_refs':[{'source_id':'event:33','observation':'A missing witness premise is reported.'}],'relation_to_original':'later_verified_repair','limitations':[]}
    def test_logical_hint_passes_structural_screen(self):
        self.assertTrue(m.screen_hint(self.hint,self.contract,self.schema)['automatic_screen_passed'])
    def test_code_answer_is_not_admitted(self):
        for text in ['assert(x == y);','```rust\nproof fn answer() {}\n```','s1.lemma_map_union_commute(s2, f);']:
            h=copy.deepcopy(self.hint);h['hint_text']=text
            self.assertFalse(m.screen_hint(h,self.contract,self.schema)['automatic_screen_passed'])
    def test_wrong_checkpoint_or_unknown_evidence_rejected(self):
        for change in [{'checkpoint_sha256':'b'*64},{'evidence_refs':[{'source_id':'event:999','observation':'unsupported'}]}]:
            h={**self.hint,**change}
            with self.assertRaises(AssertionError):m.screen_hint(h,self.contract,self.schema)
    def test_compact_snapshot_evidence_is_lossless(self):
        import hashlib
        baseline='first\nrepeat\nrepeat\nlast\n'
        variants=['first\ninserted\nrepeat\nrepeat\nlast\n','first\nlast','',baseline]
        snapshots={hashlib.sha256(x.encode()).hexdigest():x for x in variants}
        packed=m.snapshot_evidence(baseline,snapshots,True)
        for digest,edits in packed['snapshots'].items():
            restored=baseline.splitlines(keepends=True)
            for edit in reversed(edits):
                restored[edit['start_line_0based']:edit['end_line_exclusive']]=edit['replacement_lines']
            self.assertEqual(''.join(restored),snapshots[digest])
        self.assertEqual(m.snapshot_evidence(baseline,snapshots,False),snapshots)

    def test_actor_template_only_projects_hint(self):
        text=m.render((ROOT/'prompts/checkpoint_hints/actor_hint.md').read_text(),{'hint_text':self.hint['hint_text']})
        self.assertIn(self.hint['hint_text'],text)
        self.assertNotIn('event:33',text)
        self.assertNotIn('a'*64,text)
        with self.assertRaises(AssertionError):m.render('{{hint_text}}',self.hint)

    def test_bridge_budget_requires_explicit_shared_state(self):
        self.assertEqual(m.bridge_budget_args({}),[])
        with self.assertRaises(AssertionError):
            m.bridge_budget_args({'approval_limit_usd':5})
        args=m.bridge_budget_args({
            'budget_state_path':'/external/shared-budget.json',
            'approval_limit_usd':5,
            'prior_spend_usd':0,
            'request_reserve_usd':0.25,
        })
        self.assertIn('/external/shared-budget.json',args)
        self.assertIn('5.0',args)

    def test_prepare_no_hint_freezes_exact_checkpoint_without_hint(self):
        item=json.loads((ROOT.parent/'fixed-claude-stratified-80-seed20260814/train/items.json').read_text())[0]
        source_text='fn checkpoint() {}\n'; digest=hashlib.sha256(source_text.encode()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); source_root=base/'source'; output_root=base/'output'
            checkpoint=source_root/'hint-private'/item['id']/'CP01'/'checkpoint.rs'
            checkpoint.parent.mkdir(parents=True); checkpoint.write_text(source_text)
            m.write(source_root/'selection.json',{
                'task':item,
                'train_sha256':m.TRAIN_SHA,
                'checkpoints':[{'ordinal':1,'event_index':17,'checkpoint_sha256':digest}],
            })
            skill_sha='b'*64
            m.write(source_root/'runs'/item['id']/'CP01'/'run_manifest.json',{
                'model':'deepseek-v4-pro','reasoning_effort':'high','timeout_seconds':600,'skill_sha256':skill_sha,
            })
            config={'output_root':str(output_root),'checkpoint_source_root':str(source_root),'task_id':item['id'],'model':'deepseek-v4-pro','actor_skill_sha256':skill_sha}
            m.prepare_no_hint(config); m.prepare_no_hint(config)
            frozen=json.loads((output_root/'selection.json').read_text())
            self.assertEqual(frozen['condition'],'matched_no_hint')
            self.assertFalse(frozen['matching_contract']['teacher_hint_visible_to_actor'])
            self.assertEqual((output_root/'checkpoints'/item['id']/'CP01.rs').read_text(),source_text)
            self.assertFalse((output_root/'hint-private').exists())

    def test_prepare_no_hint_from_reviewed_publication(self):
        item=json.loads((ROOT.parent/'fixed-claude-stratified-80-seed20260814/train/items.json').read_text())[0]
        source_text='fn published_checkpoint() {}\n'; digest=hashlib.sha256(source_text.encode()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); publication=base/'publication'; output_root=base/'output'
            checkpoint=publication/'checkpoints'/'CP01.rs'
            checkpoint.parent.mkdir(parents=True); checkpoint.write_text(source_text)
            m.write(publication/'selection_manifest.json',{'checkpoints':[
                {'event_index':17,'candidate_sha256':digest,'continue':True},
                {'event_index':18,'candidate_sha256':'f'*64,'continue':False},
            ]})
            config={
                'output_root':str(output_root),'checkpoint_publication_root':str(publication),
                'task_id':item['id'],'model':'deepseek-v4-pro','actor_timeout_seconds':600,
                'actor_skill_sha256':'96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40',
            }
            m.prepare_no_hint(config); m.prepare_no_hint(config)
            frozen=json.loads((output_root/'selection.json').read_text())
            self.assertEqual(frozen['checkpoint_source_kind'],'reviewed_publication_checkpoint_source')
            self.assertEqual(len(frozen['checkpoints']),1)
            self.assertNotIn('matched_hint_run_manifest_sha256',frozen['checkpoints'][0])
            self.assertEqual((output_root/'checkpoints'/item['id']/'CP01.rs').read_text(),source_text)

    def test_seed_all_published_hints_without_provider_artifacts(self):
        repository=ROOT.parent
        publication_root=repository/'docs/hint-augmentation-20260916'
        for project in ('ir','ac','al'):
            publication=publication_root/project
            task_id=json.loads((publication/'checkpoints.json').read_text())['task_id']
            published_selection=json.loads((publication/'selection_manifest.json').read_text())
            rows=[row for row in published_selection['checkpoints'] if row.get('continue') is True]
            for version in ('v1','v2'):
                with self.subTest(project=project,version=version), tempfile.TemporaryDirectory() as directory:
                    output=Path(directory)
                    selection=[]
                    for ordinal,row in enumerate(rows,1):
                        hint=json.loads((publication/version/f'CP{ordinal:02d}'/'hint.json').read_text())
                        private=output/'hint-private'/task_id/f'CP{ordinal:02d}'
                        private.mkdir(parents=True)
                        checkpoint=publication/'checkpoints'/f'CP{ordinal:02d}.rs'
                        (private/'checkpoint.rs').write_bytes(checkpoint.read_bytes())
                        m.write(private/'input_contract.json',{
                            'checkpoint_sha256':row['candidate_sha256'],
                            'evidence_ids':[entry['source_id'] for entry in hint['evidence_refs']],
                        })
                        selection.append({
                            'ordinal':ordinal,
                            'event_index':row['event_index'],
                            'checkpoint_sha256':row['candidate_sha256'],
                        })
                    m.write(output/'selection.json',{'task':{'id':task_id},'checkpoints':selection})
                    config={
                        'output_root':str(output),
                        'published_project_root':str(publication),
                        'hint_version':version,
                        'prompt_dir':str(publication_root/'prompts'/version),
                        'task_id':task_id,
                    }
                    checkpoints=list(range(1,len(rows)+1))
                    m.seed_published_hints(config,checkpoints)
                    m.seed_published_hints(config,checkpoints)
                    for ordinal in checkpoints:
                        private=output/'hint-private'/task_id/f'CP{ordinal:02d}'
                        provenance=json.loads((private/'published_hint_replay.json').read_text())
                        self.assertFalse(provenance['hint_generation_api_called'])
                        self.assertEqual(provenance['hint_version'],version)
                        self.assertTrue(m.hint_screen_approved(private))
                        for name in ('call_started.json','response.raw','usage.json','output_text.txt'):
                            self.assertFalse((private/name).exists())

if __name__=='__main__':unittest.main()
