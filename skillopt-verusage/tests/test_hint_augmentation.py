import copy
import importlib.util
import json
from pathlib import Path
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

if __name__=='__main__':unittest.main()
