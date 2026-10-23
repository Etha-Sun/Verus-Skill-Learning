import copy
import json
from unittest.mock import Mock
import pytest
import interpret_full_trace_facts as b
from skillopt_verusage.campaign_evidence import shared_strings, expand_strings


def facts():
    return [{'fact_id':'train:0','fact_sha256':'hash0','fact':{'change':'unchanged original'},'review_note':'Bundled edits.'},
            {'fact_id':'train:1','fact_sha256':'hash1','fact':{'change':'background'},'review_note':'Context only.'}]


def value():
    return {'interpretations':[{'fact_ids':['train:0'],
        'supported_claims':[{'claim':'Multiple changes precede the reported pass.','fact_ids':['train:0']}],
        'hypotheses':[{'claim':'A premise may be missing.','fact_ids':['train:0'],'uncertainty':'Changes not isolated.'}],
        'discriminating_question':'Which premise is available at this scope?', 'missing_context':[]}],
        'uninterpreted_facts':[{'fact_id':'train:1','reason':'Background, no new interpretation.'}]}


def test_full_original_and_fork_history_and_review_limits_are_preserved():
    old={'complete_training_group':{'original':['earlier failure','later pass'],
         'forks':[{'prefix_recipe':'original through event 4','suffix':['failed attempt']}]},
         'evidence_index':{'windows':['W0']},'current_skill':'old training context',
         'output_contract':b.base.FACT_CONTRACT}
    extra={'records':[{'command':'combined check','output':'failed'}]}
    req=b.make_request({'user':json.dumps(shared_strings(old))},facts(),extra)
    restored=expand_strings(json.loads(req['user']))
    for key in ['complete_training_group','evidence_index','current_skill']:assert restored[key]==old[key]
    assert restored['reviewed_facts']==facts() and restored['supplemental_check_evidence']==extra
    assert req['cap']==32768 and req['effort']=='high'
    assert restored['output_contract']==b.CONTRACT


def test_valid_interpretation_remains_semantic_pending_and_hash_bound():
    got,decisions=b.audit(value(),facts())
    assert got[0]['semantic_review_required'] is True
    assert got[0]['fact_hashes']=={'train:0':'hash0'}
    assert decisions[0]['status']=='mechanical_pass_semantic_review_pending'


def test_uncertainty_is_required_without_rewriting_item():
    v=value();del v['interpretations'][0]['hypotheses'][0]['uncertainty'];before=copy.deepcopy(v)
    got,d=b.audit(v,facts());assert not got and d[0]['status']=='mechanical_reject' and v==before


def test_unknown_or_cross_group_fact_is_not_rebound():
    v=value();v['interpretations'][0]['fact_ids']=['another-train:0']
    with pytest.raises(ValueError,match='fact ID'):b.audit(v,facts())
    v=value();v['interpretations'][0]['supported_claims'][0]['fact_ids']=['train:1']
    assert b.audit(v,facts())[1][0]['status']=='mechanical_reject'


def test_missing_or_duplicate_coverage_stops_envelope():
    v=value();v['uninterpreted_facts']=[]
    with pytest.raises(ValueError,match='coverage'):b.audit(v,facts())
    v=value();v['uninterpreted_facts'].append({'fact_id':'train:0','reason':'also unused'})
    with pytest.raises(ValueError,match='coverage'):b.audit(v,facts())
    v=value();v['uninterpreted_facts']*=2
    with pytest.raises(ValueError,match='duplicate'):b.audit(v,facts())


def test_empty_interpretations_allowed_without_forcing_insights():
    v={'interpretations':[], 'uninterpreted_facts':[{'fact_id':f['fact_id'],'reason':'Insufficient evidence.'} for f in facts()]}
    assert b.audit(v,facts())==([],[])


def test_action_field_rejected_while_raw_and_valid_sibling_preserved():
    v=value();v['interpretations'].append(copy.deepcopy(v['interpretations'][0]));v['interpretations'][1]['action']='insert a formula';before=copy.deepcopy(v)
    got,d=b.audit(v,facts());assert len(got)==1 and d[1]['status']=='mechanical_reject' and v==before


def test_frozen_input_tampering_blocks_check(tmp_path):
    p=tmp_path/'facts.json';p.write_text('reviewed')
    (tmp_path/'contract.json').write_text(json.dumps({'authorization':b.AUTH,'input_hashes':{str(p):b.base.prior.old.sha(p)}}))
    b.check(tmp_path);p.write_text('edited')
    with pytest.raises(ValueError,match='changed'):b.check(tmp_path)


def test_restart_cannot_dispatch(tmp_path,monkeypatch):
    parent=tmp_path/'parent';parent.mkdir();(tmp_path/'started.json').write_text('{}')
    monkeypatch.setattr(b,'check',lambda _: {'parent_root':str(parent),'calls':[]})
    dispatch=Mock();monkeypatch.setattr(b,'client',dispatch)
    with pytest.raises(ValueError,match='restart'):b.run(tmp_path)
    dispatch.assert_not_called()


def test_transport_failure_stops_before_second_group_without_retry(tmp_path,monkeypatch):
    parent=tmp_path/'parent';parent.mkdir();(tmp_path/'config.json').write_text('{}')
    (tmp_path/'requests').mkdir();(tmp_path/'requests/interpret-first.json').write_text('{}')
    monkeypatch.setattr(b,'check',lambda _: {'parent_root':str(parent),'calls':[{'source_task':'first'},{'source_task':'second'}]})
    monkeypatch.setattr(b.base.prior.old.prior,'credentials',lambda _:None)
    transport=Mock();transport.call.side_effect=RuntimeError('incomplete')
    monkeypatch.setattr(b,'client',lambda *args:transport)
    with pytest.raises(RuntimeError,match='incomplete'):b.run(tmp_path)
    assert transport.call.call_count==1
    assert json.loads((tmp_path/'stopped.json').read_text())['automatic_retry'] is False
    assert not (tmp_path/'completed.json').exists()
