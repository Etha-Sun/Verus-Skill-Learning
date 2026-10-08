"""Only the explicitly approved unmetered actor may be excluded and rerun."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import threading
import time

import pytest

from skillopt_verusage.augmentation_campaign import (
    APPROVED_ACTOR_TRANSPORT_REQUEST, APPROVED_ACTOR_TRANSPORT_TASK,
    Campaign, audit_actor_transport_repair,
)
from skillopt_verusage.budget_guard import estimate_deepseek_cost
from skillopt_verusage.guarded_deepseek import GuardedDeepSeek, write_json
from test_transport_recovery import fixture, digest, read_records, write_records


def actor_fixture(base):
    approved, parent, config = fixture(base)
    progress = {'phase':'stopped','error_type':'UnresolvedActorProviderCost','hint_completed':9}
    write_json(parent/'progress.json',progress)
    key = '064562633b00d03570ef/cp2'
    directory = parent/'augmentation'/key
    write_json(directory/'codex_events.raw.jsonl',{'type':'turn.completed'})
    write_json(directory/'workspace/candidate.rs',{'synthetic_proof':True})
    write_json(parent/'hints'/key/'hint.json',{'hint_text':'Keep the admitted hint'})
    write_json(parent/'hints'/key/'screen.json',{'automatic_screen_passed':True})
    unknown = {'request_id':APPROVED_ACTOR_TRANSPORT_REQUEST,'task_id':APPROVED_ACTOR_TRANSPORT_TASK,
               'model':'deepseek-v4-pro','attempts':[{'usage':None,'estimated_cost_usd':None,
               'max_tokens':131072,'error':'IncompleteRead: lost actor response'}]}
    write_records(parent,[read_records(parent)[0],unknown])
    inventory = {'progress':progress,'ledger_sha256':digest(parent/'provider_calls.jsonl'),
                 'unknown_records':[unknown],
                 'result_hashes':{str(p.relative_to(parent)):digest(p) for p in parent.glob('augmentation/*/*/result.json')},
                 'hint_hashes':{str(p.relative_to(parent)):digest(p) for p in parent.glob('hints/*/*/hint.json')},
                 'excluded_actor_hashes':{str(p.relative_to(parent)):digest(p) for p in directory.rglob('*') if p.is_file()}}
    write_json(parent/'actor_transport_inventory.json',inventory)
    upper = estimate_deepseek_cost({'prompt_cache_miss_tokens':1048576,'completion_tokens':131072},
                                   'deepseek-v4-pro',price_band='peak')
    review = {'replacement_authorized':True,'request_id':APPROVED_ACTOR_TRANSPORT_REQUEST,
              'task_id':APPROVED_ACTOR_TRANSPORT_TASK,'excluded_actor_key':key,
              'ledger_sha256':inventory['ledger_sha256'],
              'inventory_sha256':digest(parent/'actor_transport_inventory.json'),
              'unknown_expense_upper_usd':upper}
    write_json(parent/'actor_transport_repair_review.json',review)
    return approved,parent,config,review


def test_actor_recovery_preserves_all_known_results_banks_and_fee(tmp_path,monkeypatch):
    approved,parent,config,review = actor_fixture(tmp_path)
    before = (parent/'provider_calls.jsonl').read_bytes()
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT',str(approved))
    campaign = Campaign(config)
    assert len(list(campaign.root.glob('augmentation/*/*/result.json'))) == 9
    assert len(list(campaign.root.glob('banks/*/cards.json'))) == 2
    assert not (campaign.root/'augmentation'/review['excluded_actor_key']).exists()
    campaign.ledger.write_text(json.dumps({'attempts':[{'estimated_cost_usd':.25}]})+'\n')
    campaign.check_costs()
    costs = json.loads((campaign.root/'cost_summary.json').read_text())
    assert costs['estimated_campaign_cost_including_parent_usd'] == .75
    assert costs['approved_historical_unknown_expense_upper_usd'] == review['unknown_expense_upper_usd']
    assert costs['known_estimate_plus_historical_unknown_upper_usd'] == .75+review['unknown_expense_upper_usd']
    assert costs['total_unknown_requests_including_approved_history'] == 1
    assert (parent/'provider_calls.jsonl').read_bytes() == before
    campaign.ledger.write_text(json.dumps({'attempts':[{'estimated_cost_usd':None}]})+'\n')
    campaign.check_costs()
    assert json.loads((campaign.root/'cost_summary.json').read_text())['unknown_cost_requests'] == 1


@pytest.mark.parametrize('field,value',[('replacement_authorized',False),('request_id','another'),
    ('task_id','another'),('ledger_sha256','bad'),('inventory_sha256','bad'),
    ('excluded_actor_key','another/cp2'),('unknown_expense_upper_usd',0)])
def test_actor_recovery_does_not_generalize_authority(tmp_path,field,value):
    _,parent,_,review = actor_fixture(tmp_path)
    write_json(parent/'actor_transport_repair_review.json',{**review,field:value})
    with pytest.raises(ValueError):
        audit_actor_transport_repair(parent,read_records(parent))


@pytest.mark.parametrize('path',['augmentation/one/cp1/result.json','hints/one/cp1/hint.json',
    'augmentation/064562633b00d03570ef/cp2/workspace/candidate.rs',
    'augmentation/064562633b00d03570ef/cp2/result.json'])
def test_changed_or_mislabeled_actor_evidence_is_rejected(tmp_path,path):
    _,parent,_,_ = actor_fixture(tmp_path)
    write_json(parent/path,{'changed':True})
    with pytest.raises(ValueError):
        audit_actor_transport_repair(parent,read_records(parent))


def test_no_other_partial_actor_can_be_silently_excluded(tmp_path,monkeypatch):
    approved,parent,config,_ = actor_fixture(tmp_path)
    write_json(parent/'augmentation/another/cp1/raw.json',{'partial':True})
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT',str(approved))
    with pytest.raises(ValueError,match='complete reviewed continuation set'):
        Campaign(config)


def test_queued_teacher_cancels_before_dispatch_after_prior_error(tmp_path,monkeypatch):
    client = GuardedDeepSeek(root=tmp_path/'calls',api_key='fixture',guards=[],ledger=tmp_path/'ledger.jsonl')
    client.slots = threading.Semaphore(0)
    def unexpected(*args,**kwargs):
        raise AssertionError('Queued cancelled request must not contact upstream')
    monkeypatch.setattr('skillopt_verusage.guarded_deepseek.forward_native_responses',unexpected)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.call,system='fixture',user='fixture',name='queued')
        deadline = time.monotonic()+3
        while not list((tmp_path/'calls').glob('queued/*/started.json')):
            assert time.monotonic()<deadline
            time.sleep(.01)
        with client.lock:
            client.errors.append('Earlier provider error')
        client.slots.release()
        with pytest.raises(RuntimeError,match='cancelled without an API call'):
            pending.result(timeout=3)
    error = json.loads(next((tmp_path/'calls').glob('queued/*/error.json')).read_text())
    assert error['upstream_dispatched'] is False
    assert not client.ledger.exists()
