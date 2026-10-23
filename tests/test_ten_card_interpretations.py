import json
from pathlib import Path
from unittest.mock import Mock
import pytest
import run_ten_card_interpretations as ten
from skillopt_verusage.campaign_evidence import shared_strings, expand_strings


def test_B_preserves_full_history_and_review_notes_with_65536_cap():
    original={'complete_training_group':{'original':['before','after'],'forks':[{'prefix':'all earlier events','events':['suffix']}]},
              'evidence_index':{},'output_contract':ten.b.base.FACT_CONTRACT}
    facts=[{'fact_id':'training:0','fact':{'change':'raw'},'review_note':'Joint edit, not causal.'}]
    req=ten.make_request({'user':json.dumps(shared_strings(original))},facts,{'records':[]})
    packet=expand_strings(json.loads(req['user']))
    assert packet['complete_training_group']==original['complete_training_group']
    assert packet['reviewed_facts']==facts and req['cap']==65536
    assert packet['output_contract']==ten.b.CONTRACT


def test_paid_client_uses_existing_parent_ledgers_without_reset(tmp_path,monkeypatch):
    parent=tmp_path/'parent';root=tmp_path/'B';parent.mkdir();root.mkdir()
    monkeypatch.setenv('DEEPSEEK_API_KEY','test-only')
    for name,cap in [('budget-new-extraction.json',50),('budget-new-total.json',70)]:
        g=ten.SharedBudgetGuard(parent/name,approval_limit_usd=cap,prior_spend_usd=0,optimizer_reserve_usd=0,request_reserve_usd=0)
        key=g.reserve(4);g.settle(key,cost_usd=3.03,usage={})
    c=ten.client(root,parent,True)
    assert [g.path for g in c.guards]==[parent/'budget-new-extraction.json',parent/'budget-new-total.json']
    assert all(json.loads(g.path.read_text())['target_spend_usd']==3.03 for g in c.guards)
    assert not (root/'budget-new-extraction.json').exists()


def setup_run(tmp_path,monkeypatch):
    parent=tmp_path/'A';parent.mkdir();root=tmp_path/'B';root.mkdir()
    (root/'requests').mkdir();(root/'requests/B-first.json').write_text('{}');(root/'config.json').write_text('{}')
    contract={'parent_root':str(parent),'calls':[{'source_task':'first'},{'source_task':'second'}]}
    monkeypatch.setattr(ten,'check',lambda _:contract)
    monkeypatch.setattr(ten,'budget_snapshot',lambda _: {})
    monkeypatch.setattr(ten.b.base.prior.old.prior,'credentials',lambda _:None)
    return root


def test_invalid_json_is_preserved_and_stops_no_second_call_or_restart(tmp_path,monkeypatch):
    root=setup_run(tmp_path,monkeypatch);c=Mock();c.call.return_value=('broken json',{})
    factory=Mock(return_value=c);monkeypatch.setattr(ten,'client',factory)
    with pytest.raises(json.JSONDecodeError):ten.run(root)
    assert c.call.call_count==1
    assert (root/'interpretations/first.response.txt').read_text()=='broken json'
    assert json.loads((root/'stopped.json').read_text())['automatic_retry'] is False
    with pytest.raises(ValueError,match='restart'):ten.run(root)
    assert factory.call_count==1


def test_transport_failure_stops_before_second_group(tmp_path,monkeypatch):
    root=setup_run(tmp_path,monkeypatch);c=Mock();c.call.side_effect=RuntimeError('failed request')
    monkeypatch.setattr(ten,'client',lambda *args,**kwargs:c)
    with pytest.raises(RuntimeError,match='failed request'):ten.run(root)
    assert c.call.call_count==1 and not (root/'completed.json').exists()


def test_frozen_fact_tampering_rejected(tmp_path):
    frozen=tmp_path/'facts.json';frozen.write_text('reviewed')
    (tmp_path/'contract.json').write_text(json.dumps({'stage':'B_interpretation_only','cap':65536,
        'calls':[{}]*10,'hashes':{str(frozen):ten.sha(frozen)},'parent_root':str(tmp_path/'A')}))
    (tmp_path/'authorization.json').write_text(json.dumps({'shared_ledger_root':str(tmp_path/'A'),
        'destination':'https://api.deepseek.com','new_extraction_cap_usd':50,'new_evaluation_cap_usd':20,'new_total_cap_usd':70}))
    ten.check(tmp_path);frozen.write_text('changed')
    with pytest.raises(ValueError,match='changed'):ten.check(tmp_path)
