import json
from unittest.mock import Mock
import pytest
import run_ten_card_actions as c
from skillopt_verusage.campaign_evidence import shared_strings, expand_strings


def evidence():
    items=[{'interpretation_id':'train:B0','fact_ids':['train:0'],
            'interpretation_sha256':'b-hash','reason':'Bundled edit, no necessity claim.'}]
    facts=[{'fact_id':'train:0','fact_sha256':'a-hash'}]
    return items,facts


def candidate():
    return {'entry_condition':'An unresolved local obligation with an available contract.',
            'operation':{k:'Inspect the current obligation within its scope.' for k in ['inspect','bind','compare','probe','fallback']},
            'evidence_summary':'A joint edit passed; causality remains unisolated.',
            'check':'Recheck the same obligation.','stop_when':'Stop when the premises are absent.',
            'support':{'interpretation_ids':['train:B0'],'fact_ids':['train:0']}}


def test_full_history_and_review_annotations_survive_C_request():
    items,_=evidence()
    old={'complete_training_group':{'original':['all events'],'forks':[{'prefix':'full','events':['suffix']}]},
         'reviewed_facts':[{'fact_id':'train:0','review_note':'A qualification'}],
         'supplemental_check_evidence':{'records':['comparison output']},'output_contract':c.b.b.CONTRACT}
    req=c.make_request({'user':json.dumps(shared_strings(old))},items)
    packet=expand_strings(json.loads(req['user']))
    assert all(packet[k]==v for k,v in old.items() if k!='output_contract')
    assert packet['reviewed_interpretations']==items and req['cap']==65536
    assert packet['support_catalog']==[{'interpretation_id':'train:B0','fact_ids':['train:0']}]
    assert 'fixed_v2_principles' not in packet
    assert packet['output_contract']==c.CONTRACT


def test_two_supported_candidates_or_empty_allowed_but_no_deployment():
    items,facts=evidence()
    rows,ds=c.audit({'candidates':[candidate(),candidate()],'selection_reason':'Two candidates.'},items,facts)
    assert [r['index'] for r in rows]==[0,1]
    assert all(not r['deployed'] and not r['representation_frozen'] for r in rows)
    assert all('rendered_card' not in r for r in rows)
    assert c.audit({'candidates':[],'selection_reason':'No justified candidate.'},items,facts)==([],[])
    with pytest.raises(ValueError,match='two'):
        c.audit({'candidates':[candidate()]*3,'selection_reason':'Too many'},items,facts)


def test_support_mandatory_not_replaced_by_selection_reason_and_cross_link_rejected():
    items,facts=evidence();bad=candidate();del bad['support']
    rows,ds=c.audit({'candidates':[bad],'selection_reason':'train:B0 train:0'},items,facts)
    assert not rows and ds[0]['status']=='mechanical_reject'
    bad=candidate();bad['support']['fact_ids']=['train:1']
    rows,_=c.audit({'candidates':[bad],'selection_reason':'Claim'},items,facts+[{'fact_id':'train:1','fact_sha256':'other'}])
    assert not rows


def test_transport_failure_no_second_call_and_no_restart(tmp_path,monkeypatch):
    ledger=tmp_path/'A';root=tmp_path/'C';ledger.mkdir();root.mkdir();(root/'requests').mkdir()
    (root/'requests/C-first.json').write_text('{}');(root/'config.json').write_text('{}')
    monkeypatch.setattr(c,'check',lambda _:{'shared_ledger_root':str(ledger),'calls':[{'source_task':'first'},{'source_task':'second'}]})
    monkeypatch.setattr(c.b,'budget_snapshot',lambda _: {})
    monkeypatch.setattr(c.b.b.base.prior.old.prior,'credentials',lambda _:None)
    transport=Mock();transport.call.side_effect=RuntimeError('provider failure')
    factory=Mock(return_value=transport);monkeypatch.setattr(c.b,'client',factory)
    with pytest.raises(RuntimeError,match='provider failure'):c.run(root)
    assert transport.call.call_count==1
    assert json.loads((root/'stopped.json').read_text())['automatic_retry'] is False
    with pytest.raises(ValueError,match='restart'):c.run(root)
    assert factory.call_count==1


def test_truncated_json_saved_before_stop(tmp_path,monkeypatch):
    ledger=tmp_path/'A';root=tmp_path/'C';ledger.mkdir();root.mkdir();(root/'requests').mkdir()
    (root/'requests/C-first.json').write_text('{}');(root/'config.json').write_text('{}')
    monkeypatch.setattr(c,'check',lambda _:{'shared_ledger_root':str(ledger),'calls':[{'source_task':'first'}]})
    monkeypatch.setattr(c.b,'budget_snapshot',lambda _: {})
    monkeypatch.setattr(c.b.b.base.prior.old.prior,'credentials',lambda _:None)
    transport=Mock();transport.call.return_value=('{"truncated',{})
    monkeypatch.setattr(c.b,'client',lambda *a,**k:transport)
    with pytest.raises(json.JSONDecodeError):c.run(root)
    assert (root/'candidates/first.response.txt').read_text()=='{"truncated'
    assert not (root/'completed.json').exists()
