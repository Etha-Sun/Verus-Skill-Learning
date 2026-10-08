import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import os
from subprocess import CompletedProcess
from urllib.request import Request,urlopen
from unittest.mock import patch

from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.campaign_evidence import (audit_cards,evaluation_schedule,exact_bank,
                                               expand_strings,packet_trace,shared_strings)
from skillopt_verusage.guarded_deepseek import BudgetMux,GuardedDeepSeek,response_text


CARD = "**Trigger:** Repeated unproved implication.\n**Action:** Establish its missing premise.\n**Why:** A conclusion depends on that premise.\n**Validate:** Run both validators.\n**Avoid when:** The premise is already established."


def guard(path,limit):
    return SharedBudgetGuard(path,approval_limit_usd=limit,prior_spend_usd=0,
                            optimizer_reserve_usd=0,request_reserve_usd=0)


def progress_fixture():
    def source(body):
        return "verus! {\nproof fn target() {\n"+body+"}\n}\n"
    final = source("    assert(a);\n    assert(b);\n    assert(redundant);\n")
    codes = [source("    assert(a);\n    assert(extra);\n"),
             source("    assert(a);\n    assert(other);\n"),
             source("    assert(a);\n    assert(b);\n"),source("    assert(a);\n"),final]
    snapshots = {};events = [];ledger = []
    for i,code in enumerate(codes,1):
        digest = hashlib.sha256(code.encode()).hexdigest();snapshots[digest] = code
        item = {"id":f"item_{i}","type":"command_execution","command":"verus candidate.rs",
                "aggregated_output":f"verification results:: {1 if i==5 else 0} verified, {0 if i==5 else 1} errors"}
        for offset,kind in ((-1,"item.started"),(0,"item.completed")):
            events.append({"event_index":2*i+offset,"actor":"codex",
                "type":"tool_call" if offset else "tool_result","candidate_sha256":digest,
                "data":{"raw_codex_event":{"type":kind,"item":item}}})
        ledger.append({"task_id":"t","input_item_types":["message"]+["function_call","function_call_output"]*(i-1),
                       "attempts":[{"usage":{"completion_tokens":100}}]})
    trace = {"original_input":source(""),"final_source":final,"events":events,
             "snapshots":{"chain":[{"candidate_sha256":hashlib.sha256(final.encode()).hexdigest()}]},
             "result":{"hard":1,"fidelity":"V2_TRACE"}}
    return trace,snapshots,ledger


def verify_fixture(source):
    return "assert(a);" in source and "assert(b);" in source,"fresh verifier output"


class EvidenceTests(unittest.TestCase):
    def test_helper_inclusive_progress_exposes_target_flat_helper_gain(self):
        from skillopt_verusage.campaign_evidence import analyze_progress
        trace, snapshots, ledger = progress_fixture()
        helper = "proof fn helper() {\n    assert(h);\n}\n"
        # Every candidate has the same target proof. Only the last creates the helper.
        base = "verus! {\nproof fn target() {\n    assert(a);\n    assert(b);\n}\n}\n"
        trace["final_source"] = base + helper
        for index in range(5):
            source = base + (helper if index == 4 else "")
            digest = hashlib.sha256(source.encode()).hexdigest()
            snapshots[digest] = source
            for event in trace["events"][2*index:2*index+2]:
                event["candidate_sha256"] = digest
        components = [
            {"key":"target.","name":"target","occurrence":0,"is_target":True,"is_new":False},
            {"key":"helper.","name":"helper","occurrence":0,"is_target":False,"is_new":True}]
        report = analyze_progress(trace, snapshots, ledger, "t", "target", verify_fixture,
            lambda baseline, candidate:(True,"preserved"), reference_components=components,
            reference_pruning={"pruned_source":trace["final_source"],"summary":{},"trials":[]})
        self.assertEqual([c["target_proof_coverage"] for c in report["curve"]], [1]*5)
        self.assertEqual([c["proof_coverage"] for c in report["curve"]], [2/3]*4+[1])
        self.assertEqual(report["metric"], "compiler-scoped-target-and-helper-line-coverage-v2")

    def test_progress_uses_pruned_target_proof_not_unchanged_error_counts(self):
        from skillopt_verusage.campaign_evidence import analyze_progress
        trace,snapshots,ledger = progress_fixture()
        report = analyze_progress(trace,snapshots,ledger,"t","target",verify_fixture,
                                  lambda baseline,candidate:(True,"preservation passed"))
        self.assertEqual([x["proof_coverage"] for x in report["curve"]],[.5,.5,1,.5,1])
        self.assertNotIn("redundant",report["pruned_source"])
        self.assertEqual([x["start_call"] for x in report["stagnation_segments"]],[1])
        self.assertEqual([x["to_call"] for x in report["regression_transitions"]],[4])
        self.assertNotIn("selected_checkpoint",report)
        self.assertEqual([x["cumulative_output_tokens"] for x in report["curve"]],[100,200,300,400,500])

    def test_progress_rejects_unverified_reference_and_bad_snapshot(self):
        from skillopt_verusage.campaign_evidence import analyze_progress
        trace,snapshots,ledger = progress_fixture()
        with self.assertRaisesRegex(ValueError,"[Ff]inal proof"):
            analyze_progress(trace,snapshots,ledger,"t","target",lambda source:(False,"fail"),
                             lambda baseline,candidate:(True,"ok"))
        snapshots[trace["events"][0]["candidate_sha256"]] = "different source"
        with self.assertRaisesRegex(ValueError,"snapshot"):
            analyze_progress(trace,snapshots,ledger,"t","target",verify_fixture,
                             lambda baseline,candidate:(True,"ok"))

    def test_progress_keeps_unsolved_original_without_inventing_reference(self):
        from skillopt_verusage.campaign_evidence import analyze_progress
        trace,snapshots,ledger = progress_fixture();trace["result"]["hard"] = 0
        verify = unittest.mock.Mock()
        report = analyze_progress(trace,snapshots,ledger,"t","target",verify,verify)
        self.assertEqual(report["status"],"no_verified_reference")
        self.assertEqual(report["curve"],[])
        verify.assert_not_called()

    def test_isolated_probe_has_unknown_target_coverage_not_fake_progress(self):
        from skillopt_verusage.campaign_evidence import analyze_progress
        trace,snapshots,ledger = progress_fixture()
        probe = "verus! {\nproof fn probe() {\n    assert(true);\n}\n}\n"
        digest = hashlib.sha256(probe.encode()).hexdigest();snapshots[digest] = probe
        for event in trace["events"][:2]: event["candidate_sha256"] = digest
        report = analyze_progress(trace,snapshots,ledger,"t","target",verify_fixture,
                                  lambda baseline,candidate:(True,"ok"))
        self.assertIsNone(report["curve"][0]["proof_coverage"])
        self.assertIn("not found",report["curve"][0]["coverage_error"])
        self.assertEqual(report["stagnation_segments"],[])

    def test_supplied_reference_still_requires_fresh_verification_and_preservation(self):
        from skillopt_verusage.campaign_evidence import analyze_progress
        trace,snapshots,ledger = progress_fixture()
        reference = {"pruned_source":trace["final_source"],"summary":{},"trials":[]}
        with patch("skillopt_verusage.campaign_evidence.greedy_prune_proof_lines") as prune:
            with self.assertRaisesRegex(ValueError,"preservation"):
                analyze_progress(trace,snapshots,ledger,"t","target",verify_fixture,
                                 lambda baseline,candidate:(False,"changed"),reference_pruning=reference)
            prune.assert_not_called()

    def test_pruned_reference_requires_preservation(self):
        from skillopt_verusage.campaign_evidence import analyze_progress
        trace,snapshots,ledger = progress_fixture()
        with self.assertRaisesRegex(ValueError,"preservation"):
            analyze_progress(trace,snapshots,ledger,"t","target",verify_fixture,
                             lambda baseline,candidate:(False,"changed executable code"))

    def test_fork_comparison_reconstructs_original_and_keeps_failed_suffix(self):
        from skillopt_verusage.campaign_evidence import fork_comparison
        trace,snapshots,ledger = progress_fixture()
        checkpoint = {"event_index":4,"checkpoint_sha256":trace["events"][3]["candidate_sha256"]}
        branch = {"events":[{"event_index":1,"type":"failure"}],"result":{"hard":0,"timeout":True},
                  "original_input":trace["original_input"],
                  "snapshots":{"baseline":snapshots[checkpoint["checkpoint_sha256"]]}}
        hint = {"hint":{"checkpoint_sha256":checkpoint["checkpoint_sha256"],"hint_text":"try another premise"},
                "screen":{"automatic_screen_passed":True}}
        view = fork_comparison(trace,checkpoint,branch,hint)
        self.assertEqual(view["original_prefix"]+view["original_suffix"],trace["events"])
        self.assertEqual(view["augmented_suffix"],branch["events"])
        self.assertEqual(view["augmented_trace"],view["original_prefix"]+branch["events"])
        self.assertFalse(view["augmented_result"]["hard"])
        hint["hint"]["checkpoint_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError,"checkpoint"):
            fork_comparison(trace,checkpoint,branch,hint)
        hint["hint"]["checkpoint_sha256"] = checkpoint["checkpoint_sha256"]
        branch["snapshots"]["baseline"] = "different initial checkpoint"
        with self.assertRaisesRegex(ValueError,"initial checkpoint"):
            fork_comparison(trace,checkpoint,branch,hint)

    def test_cards_have_no_unapproved_two_card_or_700_byte_cap(self):
        proposal = {"source_task":"s1","cards":[
            {"content":CARD+"\n"+"Reusable qualification. "*40,"evidence_refs":["event:1"]}
            for _ in range(3)]}
        audit_cards(proposal,"s1",["event:1"])

    def test_encoding_lossless(self):
        text = "Long source line.\n"*300
        original = {"a":text,"events":[{"obs":text},{"unique":"other"}]}
        self.assertEqual(expand_strings(shared_strings(original)),original)
        self.assertLess(len(json.dumps(shared_strings(original))),len(json.dumps(original)))
        self.assertEqual(expand_strings(shared_strings(original,short_keys=True)),original)

    def test_bank_keeps_40_sources_and_exact_dedup_provenance(self):
        proposals = [{"source_task":f"task-{i}","cards":[{"content":CARD,"evidence_refs":["event:1"]}]} for i in range(40)]
        bank,provenance = exact_bank(proposals)
        self.assertEqual(len(bank["cards"]),1)
        self.assertEqual(len(provenance["card-001"]),40)
        self.assertEqual(set(bank["cards"][0]),{"id","content"})
        proposals[1]["cards"][0]["content"] += " "
        self.assertEqual(len(exact_bank(proposals)[0]["cards"]),2)

    def test_card_contract(self):
        proposal = {"source_task":"s1","cards":[{"content":CARD,"evidence_refs":["event:1"]}]}
        audit_cards(proposal,"s1",["event:1"])
        with self.assertRaises(ValueError): audit_cards(proposal,"s2",["event:1"])
        proposal["cards"][0]["content"] = CARD.replace("**Why:**","**Reason:**")
        with self.assertRaises(ValueError): audit_cards(proposal,"s1",["event:1"])

    def test_final_source_reference_requires_complete_matching_chain(self):
        source = "complete proof"
        digest = hashlib.sha256(source.encode()).hexdigest()
        trace = {"final_source":source,"snapshots":{"chain":[{"candidate_sha256":digest}]}}
        self.assertEqual(packet_trace(trace)["final_source"]["sha256"],digest)
        trace["final_source"] = "different"
        with self.assertRaises(ValueError): packet_trace(trace)

    def test_bank_has_no_eight_card_limit(self):
        proposals = [{"source_task":str(i),"cards":[{"content":CARD+str(i),"evidence_refs":["event:1"]}]} for i in range(40)]
        bank,provenance = exact_bank(proposals)
        self.assertEqual(len(bank["cards"]),40)
        self.assertEqual(len(provenance),40)

    def test_card_copied_inline_proof_is_rejected(self):
        proposal = {"source_task":"s1","cards":[{"content":CARD+" choose |x| predicate(x)","evidence_refs":["event:1"]}]}
        with self.assertRaisesRegex(ValueError,"Copied proof"): audit_cards(proposal,"s1",["event:1"])

    def test_schedule_two_whole_paired_repetitions(self):
        items = [{"id":str(i)} for i in range(20)]
        conditions = ["initial","native","original_only","augmented"]
        blocks = evaluation_schedule(items,conditions)
        self.assertEqual([len(b) for b in blocks],[80,80])
        for repeat,block in enumerate(blocks):
            self.assertEqual({r for r,c,i in block},{repeat})
            self.assertEqual(len({(c,i["id"]) for r,c,i in block}),80)
            self.assertEqual([c for r,c,i in block[:4]],conditions[repeat:]+conditions[:repeat])

class GuardTests(unittest.TestCase):
    def test_native_fallback_is_rejected_but_legitimate_no_update_is_allowed(self):
        from skillopt_verusage.campaign_native import reject_fallback
        reject_fallback({'reasoning':'no updates from either group','edits':[]})
        for reasoning in ('fallback concatenation','fallback: failure first, then success',
                          'prior rationale [fallback truncated 8->4 edits]'):
            with self.assertRaisesRegex(RuntimeError,'fallback'):
                reject_fallback({'reasoning':reasoning,'edits':[]})

    def test_native_transport_records_pre_network_admission_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = GuardedDeepSeek(root=root,api_key='fake',guards=[],ledger=root/'ledger.jsonl')
            with patch.object(client,'call',side_effect=ValueError('oversized request')):
                with self.assertRaises(ValueError):
                    client.optimizer(system='system',user='input',stage='ranking')
            self.assertEqual(client.errors,['Native optimizer failure: ranking'])

    def test_only_current_train38_review_releases_paid_entry(self):
        from skillopt_verusage.augmentation_campaign import DEFERRED_SOURCES, EXECUTION_REVIEW, require_design_review
        require_design_review({'execution_review':EXECUTION_REVIEW,'deferred_sources':DEFERRED_SOURCES})
        for config in ({}, {'execution_review':EXECUTION_REVIEW},
                       {'execution_review':'old-campaign','deferred_sources':DEFERRED_SOURCES},
                       {'execution_review':EXECUTION_REVIEW,'deferred_sources':{}}):
            with self.assertRaisesRegex(RuntimeError,'design review'):
                require_design_review(config)

    def test_explicit_subset_excludes_only_the_two_deferred_questions(self):
        from skillopt_verusage.augmentation_campaign import DEFERRED_SOURCES, learning_items
        items = [{'id':str(i)} for i in range(38)]+[{'id':ident} for ident in DEFERRED_SOURCES]
        selected = learning_items(items,DEFERRED_SOURCES)
        self.assertEqual(len(selected),38)
        self.assertFalse({item['id'] for item in selected}&set(DEFERRED_SOURCES))
        self.assertEqual(len(items),40)
        with self.assertRaises(ValueError):
            learning_items(items,{})

    def test_smoke_review_cannot_accept_different_or_rejected_evidence(self):
        from skillopt_verusage.augmentation_campaign import audit_smoke_receipt, _sha256_json
        evidence = {'branches':['one','two'],'cards':'three'}
        receipt = {'accepted':True,'evidence_sha256':_sha256_json(evidence),
                   'observations':'Reviewed grounded hints and conditional cards.'}
        audit_smoke_receipt(receipt,evidence)
        for change in ({'accepted':False},{'evidence_sha256':'wrong'},{'observations':''}):
            with self.assertRaisesRegex(RuntimeError,'Smoke quality'):
                audit_smoke_receipt({**receipt,**change},evidence)

    def test_merge_smoke_bank_keeps_all_provenance_without_duplicate_cards(self):
        from skillopt_verusage.augmentation_campaign import merge_card_banks
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for stage in ('smoke','remaining'):
                path = root/stage/'cards.json';path.parent.mkdir()
                path.write_text(json.dumps({'schema_version':'stage-card-bank-v1',
                    'cards':[{'id':'card-001','content':CARD}]}))
                (path.parent/'provenance.json').write_text(json.dumps({'card-001':[{'batch':0,'source_tasks':[stage]}]}))
                paths.append(path)
            destination = merge_card_banks(paths,root/'combined/cards.json')
            self.assertEqual(len(json.loads(destination.read_text())['cards']),1)
            provenance = json.loads((destination.parent/'provenance.json').read_text())
            self.assertEqual(len(provenance['card-001']),2)
            self.assertEqual({p['source_tasks'][0] for p in provenance['card-001']},{'smoke','remaining'})

    def test_hint_recovery_only_after_known_pre_actor_failure(self):
        from skillopt_verusage.augmentation_campaign import Campaign, DEFERRED_SOURCES, EXECUTION_REVIEW
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            parent = base/'runs/failed'; parent.mkdir(parents=True)
            config = {'execution_review':EXECUTION_REVIEW,'deferred_sources':DEFERRED_SOURCES,
                      'repo':str(base/'repo'),'source_root':str(base/'source'),
                      'run_root':str(base/'runs/fresh'),'reused_hint_root':str(parent)}
            (parent/'config.json').write_text(json.dumps(config))
            progress = {'phase':'stopped','error_type':'ValueError','error':'output directory must be empty: actor'}
            (parent/'progress.json').write_text(json.dumps(progress))
            (parent/'provider_calls.jsonl').write_text(json.dumps({'attempts':[{'estimated_cost_usd':.1}]})+'\n')
            with patch.dict(os.environ,{'VERUS_SKILL_RUN_ROOT':str(base/'runs')}):
                Campaign(config)
                (parent/'provider_calls.jsonl').write_text(json.dumps({'attempts':[{'estimated_cost_usd':None}]})+'\n')
                with self.assertRaisesRegex(ValueError,'unresolved parent'):
                    Campaign(config)
                (parent/'provider_calls.jsonl').write_text(json.dumps({'attempts':[{'estimated_cost_usd':.1}]})+'\n')
                (parent/'augmentation/s1/cp1').mkdir(parents=True)
                (parent/'augmentation/s1/cp1/codex_events.raw.jsonl').write_text('')
                with self.assertRaisesRegex(ValueError,'pre-actor'):
                    Campaign(config)

    def test_completed_smoke_is_preserved_after_card_contract_failure(self):
        from skillopt_verusage.augmentation_campaign import Campaign, DEFERRED_SOURCES, EXECUTION_REVIEW
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            parent = base/'runs/failed'; parent.mkdir(parents=True)
            config = {'execution_review':EXECUTION_REVIEW,'deferred_sources':DEFERRED_SOURCES,
                      'repo':str(base/'repo'),'source_root':str(base/'source'),
                      'run_root':str(base/'runs/fresh'),'reused_hint_root':str(parent)}
            (parent/'config.json').write_text(json.dumps(config))
            (parent/'progress.json').write_text(json.dumps({'phase':'stopped','error_type':'RuntimeError',
                'error':'Native card reflection incomplete: Copied proof code/formula in card','hint_completed':6}))
            (parent/'smoke_plan.json').write_text(json.dumps({'source_tasks':['one','two']}))
            (parent/'provider_calls.jsonl').write_text(json.dumps({'attempts':[{'estimated_cost_usd':.2}]})+'\n')
            results = []
            for ident in ('one','two'):
                for cp in ('cp1','cp2','cp3'):
                    path = parent/'augmentation'/ident/cp/'result.json';path.parent.mkdir(parents=True)
                    path.write_text(json.dumps({'fidelity':'V2_TRACE','hard':1,'safety_passed':True,
                         'actor_model':'deepseek-v4-pro','actor_reasoning_effort':'max','usage':{'unknown_cost_requests':0}}))
                    results.append(path)
            before = [path.read_bytes() for path in results]
            with patch.dict(os.environ,{'VERUS_SKILL_RUN_ROOT':str(base/'runs')}):
                campaign = Campaign(config)
                self.assertEqual(len(list((campaign.root/'augmentation').glob('*/*/result.json'))),6)
                self.assertTrue((campaign.root/'recovered_smoke.json').exists())
            self.assertEqual(before,[path.read_bytes() for path in results])

    def test_semantic_recovery_binds_rejected_receipt_and_every_evidence_file(self):
        from skillopt_verusage.augmentation_campaign import audit_rejected_smoke, _sha256_json
        from skillopt_verusage.campaign_evidence import sha
        from skillopt_verusage.guarded_deepseek import write_json
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            evidence = {'card_banks':{},'proposals':{},'hints':{},'branches':{}}
            for condition in ('original_only','augmented'):
                bank = parent/'banks'/(condition+'_smoke')
                for key, path in (('card_banks',bank/'cards.json'),
                                  ('proposals',bank/'proposals/batch-000.json')):
                    write_json(path,{'condition':condition});evidence[key][condition] = sha(path)
            for kind, filename, folder in (('hints','hint.json','hints'),('branches','result.json','augmentation')):
                path = parent/folder/'one/cp1'/filename
                write_json(path,{'value':'unchanged'});evidence[kind]['one/cp1'] = sha(path)
            write_json(parent/'smoke_evidence.json',evidence)
            receipt = {'accepted':False,'engineering_passed':True,'semantic_bank_quality_passed':False,
                       'evidence_sha256':_sha256_json(evidence),'observations':'Known content failure'}
            write_json(parent/'smoke_review.json',receipt)
            audit_rejected_smoke(parent)
            write_json(parent/'smoke_review.json',{**receipt,'accepted':True})
            with self.assertRaisesRegex(ValueError,'rejected review'):
                audit_rejected_smoke(parent)
            write_json(parent/'smoke_review.json',receipt)
            write_json(parent/'augmentation/one/cp1/result.json',{'value':'changed'})
            with self.assertRaisesRegex(ValueError,'continuation evidence changed'):
                audit_rejected_smoke(parent)

    def test_reviewed_hint_repair_reuses_all_completed_actors_and_accepted_cards(self):
        from skillopt_verusage.augmentation_campaign import Campaign, DEFERRED_SOURCES, EXECUTION_REVIEW, _sha256_json
        from skillopt_verusage.native_card_update import SYSTEM
        from skillopt_verusage.campaign_evidence import sha
        from skillopt_verusage.guarded_deepseek import write_json
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); parent = base/'runs/failed'
            config = {'execution_review':EXECUTION_REVIEW,'deferred_sources':DEFERRED_SOURCES,
                      'repo':str(base/'repo'),'source_root':str(base/'source'),
                      'run_root':str(base/'runs/fresh'),'reused_hint_root':str(parent)}
            write_json(parent/'config.json',config)
            write_json(parent/'progress.json',{'phase':'stopped','error_type':'RuntimeError',
                'error':'Hint needs review; refusing a missing continuation: third/cp2',
                'hint_completed':7,'hint_rejected':1})
            write_json(parent/'smoke_plan.json',{'source_tasks':['one','two']})
            (parent/'provider_calls.jsonl').write_text(json.dumps({'attempts':[{'estimated_cost_usd':.2}]})+'\n')
            evidence = {'card_banks':{},'proposals':{}}
            for condition in ('original_only','augmented'):
                bank = parent/'banks'/(condition+'_smoke')
                for name, file in (('card_banks','cards.json'),('proposals','proposals/batch-000.json')):
                    write_json(bank/file,{'unchanged':condition});evidence[name][condition] = sha(bank/file)
                write_json(bank/'update.json',{'system_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest()})
            write_json(parent/'smoke_evidence.json',evidence)
            write_json(parent/'smoke_review.json',{'accepted':True,'evidence_sha256':_sha256_json(evidence),
                'observations':'Accepted full smoke evidence'})
            for ident, cp in [(i,c) for i in ('one','two') for c in ('cp1','cp2','cp3')]+[('third','cp1')]:
                write_json(parent/'augmentation'/ident/cp/'result.json',{'fidelity':'V2_TRACE','hard':1,
                    'safety_passed':True,'actor_model':'deepseek-v4-pro','actor_reasoning_effort':'max',
                    'usage':{'unknown_cost_requests':0}})
            hint = parent/'hints/third/cp2'
            write_json(hint/'hint.json',{'hint_text':'Rejected code quotation'})
            write_json(hint/'screen.json',{'automatic_screen_passed':False})
            review = {'repair_authorized':True,'rejected_hint_key':'third/cp2',
                      'hint_sha256':sha(hint/'hint.json'),'screen_sha256':sha(hint/'screen.json'),
                      'ledger_sha256':sha(parent/'provider_calls.jsonl')}
            write_json(parent/'hint_repair_review.json',review)
            with patch.dict(os.environ,{'VERUS_SKILL_RUN_ROOT':str(base/'runs')}):
                campaign = Campaign(config)
                self.assertEqual(campaign.rejected_hint_key,'third/cp2')
                self.assertEqual(campaign.reused_smoke_parent,parent)
                self.assertEqual(len(list((campaign.root/'augmentation').glob('*/*/result.json'))),7)
                self.assertEqual(sha(campaign.root/'banks/augmented_smoke/cards.json'),evidence['card_banks']['augmented'])
                write_json(parent/'hint_repair_review.json',{**review,'hint_sha256':'changed'})
                with self.assertRaisesRegex(ValueError,'unchanged rejected evidence'):
                    Campaign({**config,'run_root':str(base/'runs/bad-hash')})
                write_json(parent/'hint_repair_review.json',review)
                (parent/'augmentation/third/cp2').mkdir()
                with self.assertRaisesRegex(ValueError,'no actor launch'):
                    Campaign({**config,'run_root':str(base/'runs/actor-launched')})

    def test_direct_evaluation_rejects_changed_artifact_before_reading_val(self):
        from skillopt_verusage.augmentation_campaign import Campaign, CONDITIONS, _sha256_json
        from skillopt_verusage.campaign_evidence import sha
        from skillopt_verusage.guarded_deepseek import write_json
        from skillopt_verusage.skill_artifact import load_skill_artifact
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = Campaign.__new__(Campaign);campaign.root = root;campaign.repo = root/'missing-val'
            campaign.config = {}
            artifacts = {};frozen = {}
            for condition in CONDITIONS:
                path = root/'artifacts'/(condition+'.md');path.parent.mkdir(exist_ok=True)
                path.write_text('Frozen skill')
                artifacts[condition] = path
                frozen[condition] = {'path':str(path),**load_skill_artifact(path).manifest()}
            for condition in ('original_only','augmented'):
                write_json(root/'banks'/condition/'cards.json',{'cards':[]})
            write_json(root/'frozen_artifacts.json',frozen)
            evidence = {'frozen_artifacts_sha256':sha(root/'frozen_artifacts.json'),
                        'banks':{c:sha(root/'banks'/c/'cards.json') for c in ('original_only','augmented')}}
            write_json(root/'artifact_quality_evidence.json',evidence)
            write_json(root/'artifact_review.json',{'accepted':True,'evidence_sha256':_sha256_json(evidence),
                                                  'observations':'Reviewed complete artifacts'})
            artifacts['augmented'].write_text('Mutated after review')
            with patch('skillopt_verusage.augmentation_campaign.require_design_review'):
                with self.assertRaisesRegex(ValueError,'hash'):
                    campaign.evaluation(artifacts,frozen)
            self.assertFalse((root/'val_inputs').exists())

    def test_offline_progress_driver_writes_report_without_selecting_or_calling_provider(self):
        from skillopt_verusage.augmentation_campaign import Campaign
        trace,snapshots,ledger = progress_fixture()
        trace["result"]["bridge_task_key"] = "t"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/"source";source.mkdir()
            (source/"bridge_calls.jsonl").write_text("\n".join(map(json.dumps,ledger)))
            campaign = Campaign.__new__(Campaign)
            campaign.root = root/"output";campaign.source_root = source
            campaign.items = [{"id":"s1","task_id":"IR__target"}]
            campaign.traces = {"s1":trace};campaign.snapshots = {"s1":snapshots}
            campaign.config = {"verus_bin":"mock-verus","lynette_bin":"mock-lynette"}
            def run(command, **kwargs):
                if command[0]=="mock-verus":
                    passed,_ = verify_fixture(Path(command[1]).read_text())
                    return CompletedProcess(command,0 if passed else 1,
                        stdout=f"verification results:: {int(passed)} verified, {int(not passed)} errors",stderr="")
                self.assertEqual(command[0],"mock-lynette")
                return CompletedProcess(command,0,stdout="preservation passed",stderr="")
            with patch("skillopt_verusage.augmentation_campaign.subprocess.run",side_effect=run), \
                 patch("skillopt_verusage.guarded_deepseek.forward_native_responses") as provider:
                reports = campaign.prepare_progress()
                provider.assert_not_called()
            stored = json.loads((campaign.root/"proof_progress/s1/report.json").read_text())
            self.assertEqual(stored,reports["s1"])
            self.assertEqual(stored["selection_policy"],"pending_design_review")
            self.assertNotIn("redundant",stored["pruned_source"])

    def test_archived_campaign_cannot_be_reopened_or_overwritten(self):
        from skillopt_verusage.augmentation_campaign import Campaign
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base/"runs/archived";root.mkdir(parents=True)
            (root/"started.json").write_text('{}')
            (root/"progress.json").write_text('{"phase":"stopped"}')
            config = {"repo":str(base/"repo"),"source_root":str(base/"source"),"run_root":str(root)}
            with patch.dict(os.environ,{"VERUS_SKILL_RUN_ROOT":str(base/"runs")}):
                with self.assertRaisesRegex(RuntimeError,"Archived campaign"):
                    Campaign(config)
            self.assertEqual((root/"progress.json").read_text(),'{"phase":"stopped"}')

    def test_budget_and_learning_entry_points_cannot_bypass_review(self):
        from skillopt_verusage.augmentation_campaign import Campaign
        campaign = Campaign.__new__(Campaign)
        for call in (campaign.budgets,campaign.learning,lambda:campaign.extract_batches("augmented"),
                     lambda:campaign.client("test",[]),lambda:campaign.hint_branch({},{}),
                     lambda:campaign.evaluation({},{})):
            with self.assertRaisesRegex(RuntimeError,"design review"):
                call()

    def test_paid_campaign_waits_for_method_review_before_preflight(self):
        from skillopt_verusage.augmentation_campaign import Campaign
        campaign = Campaign.__new__(Campaign)
        with patch.object(campaign,"preflight") as preflight, patch.object(campaign,"budgets") as budgets:
            with self.assertRaisesRegex(RuntimeError,"design review"):
                campaign.run()
        preflight.assert_not_called()
        budgets.assert_not_called()

    def test_record_only_clients_have_no_artificial_currency_caps(self):
        from skillopt_verusage.augmentation_campaign import Campaign
        from unittest.mock import Mock
        campaign = Campaign.__new__(Campaign)
        campaign.client = Mock()
        with patch("skillopt_verusage.augmentation_campaign.require_design_review"):
            campaign.budgets()
        self.assertEqual(campaign.augmentation_guards, [])
        self.assertEqual(set(campaign.extractors), {"native","original_only","augmented"})
        self.assertTrue(all(call.args[1] == [] for call in campaign.client.call_args_list))

    def test_record_only_cost_summary_retains_unknown_usage_without_expense_gate(self):
        from skillopt_verusage.augmentation_campaign import Campaign
        with tempfile.TemporaryDirectory() as directory:
            campaign = Campaign.__new__(Campaign)
            campaign.root = Path(directory)
            campaign.ledger = campaign.root/"provider_calls.jsonl"
            campaign.ledger.write_text(json.dumps({"attempts":[{"estimated_cost_usd":1.5},{"estimated_cost_usd":.9}]})+"\n")
            campaign.check_costs()
            summary = json.loads((campaign.root/"cost_summary.json").read_text())
            self.assertEqual(summary["expense_policy"], "record_only")
            self.assertAlmostEqual(summary["estimated_new_cost_usd"], 2.4)
            campaign.ledger.write_text(json.dumps({"attempts":[{"estimated_cost_usd":None}]})+"\n")
            campaign.check_costs()
            self.assertEqual(json.loads((campaign.root/"cost_summary.json").read_text())["unknown_cost_requests"], 1)

    def test_campaign_bridge_matches_actor_routed_url(self):
        from skillopt_verusage.augmentation_campaign import Campaign
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base/"source"
            source.mkdir()
            (source/"models.json").write_text('{"models":[]}')
            config = {"repo":str(base/"repo"),"source_root":str(source),"run_root":str(base/"runs/campaign")}
            with patch.dict(os.environ,{"VERUS_SKILL_RUN_ROOT":str(base/"runs"),"DEEPSEEK_API_KEY":"test"}):
                campaign = Campaign(config)
                with patch("skillopt_verusage.codex_deepseek_bridge.forward_native_responses",return_value=(b"{}","application/json",{})) as forward:
                    with campaign.bridge("bridge",[]) as bridge:
                        self.assertTrue(os.environ.get('SKILLOPT_CODEX_BRIDGE_TOKEN'))
                        self.assertNotEqual(os.environ['SKILLOPT_CODEX_BRIDGE_TOKEN'],os.environ['DEEPSEEK_API_KEY'])
                        url = bridge["url"]+"/tasks/hint_actor--task/v1/responses"
                        with urlopen(Request(url,data=b"{}",headers={"Content-Type":"application/json"})) as response:
                            self.assertEqual(response.status,200)
                        self.assertEqual(forward.call_args.kwargs["task_id"],"hint_actor--task")

    def test_mux_rolls_back_only_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            a = guard(Path(directory)/"a.json",10)
            b = guard(Path(directory)/"b.json",1)
            with self.assertRaises(RuntimeError): BudgetMux([a,b]).reserve(2)
            self.assertEqual(json.loads(a.path.read_text())["reservations"],{})
            reservation = BudgetMux([a,b]).reserve(.5)
            BudgetMux([a,b]).settle(reservation,cost_usd=None,usage=None)
            self.assertEqual(json.loads(a.path.read_text())["uncertain_spend_usd"],.5)
            self.assertEqual(json.loads(b.path.read_text())["uncertain_requests"],1)

    def test_response_json_and_sse(self):
        response = {"output":[{"type":"message","content":[{"type":"output_text","text":"{}"}]}]}
        self.assertEqual(response_text(json.dumps(response).encode()),"{}")
        event = "data: "+json.dumps({"type":"response.completed","response":response})+"\n\n"
        self.assertEqual(response_text(event.encode()),"{}")

    def test_no_paid_replay_after_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = GuardedDeepSeek(root=root/"calls",api_key="test",guards=[guard(root/"budget.json",80)],ledger=root/"ledger.jsonl")
            with patch("skillopt_verusage.guarded_deepseek.forward_native_responses",side_effect=RuntimeError("mock network error")) as forward:
                with self.assertRaises(RuntimeError): client.call(system="JSON",user="data",name="teacher")
                fresh = GuardedDeepSeek(root=root/"calls",api_key="test",guards=client.guards,ledger=client.ledger)
                with self.assertRaisesRegex(RuntimeError,"unresolved"): fresh.call(system="JSON",user="data",name="teacher")
                self.assertEqual(forward.call_count,1)

    def test_interrupted_response_preserves_partial_bytes_without_accepting_or_retrying(self):
        from http.client import IncompleteRead
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = GuardedDeepSeek(root=root/'calls',api_key='test',guards=[],ledger=root/'ledger.jsonl')
            partial = b'{"status":"in_progress","output":['
            with patch('skillopt_verusage.guarded_deepseek.forward_native_responses',
                       side_effect=IncompleteRead(partial)) as forward:
                with self.assertRaises(IncompleteRead):
                    client.call(system='JSON',user='data',name='teacher')
                paths = list((root/'calls').glob('teacher/*/response.partial.raw'))
                self.assertEqual(len(paths),1)
                self.assertEqual(paths[0].read_bytes(),partial)
                error = json.loads((paths[0].parent/'error.json').read_text())
                self.assertEqual(error['partial_body_sha256'],hashlib.sha256(partial).hexdigest())
                self.assertFalse((paths[0].parent/'validated.json').exists())
                fresh = GuardedDeepSeek(root=root/'calls',api_key='test',guards=[],ledger=root/'ledger.jsonl')
                with self.assertRaisesRegex(RuntimeError,'unresolved'):
                    fresh.call(system='JSON',user='data',name='teacher')
                self.assertEqual(forward.call_count,1)

    def test_identical_validated_response_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = GuardedDeepSeek(root=root/"calls",api_key="test",guards=[guard(root/"budget.json",80)],ledger=root/"ledger.jsonl")
            body = json.dumps({"output":[{"type":"message","content":[{"type":"output_text","text":"{}"}]}]}).encode()
            record = {"attempts":[{"usage":{"prompt_tokens":12}}]}
            with patch("skillopt_verusage.guarded_deepseek.forward_native_responses",return_value=(body,"application/json",record)) as forward:
                client.call(system="JSON",user="data",name="teacher")
                client.call(system="JSON",user="data",name="teacher")
                self.assertEqual(forward.call_count,1)


if __name__=="__main__":
    unittest.main()
