import copy
import json
from unittest.mock import Mock
import pytest
import design_full_trace_actions as c
from skillopt_verusage.campaign_evidence import shared_strings,expand_strings


def evidence():
    return [{'interpretation_id':'train:B0','interpretation_sha256':'bhash','fact_ids':['train:0'],'decision':'accept','reason':'Mechanism uncertain.'}], [{'fact_id':'train:0','fact_sha256':'fhash'}]


def response():
    return {'selection_reason':'One question about the current premise.','candidates':[{
      'entry_condition':'A local consequence fails with an available premise.',
      'operation':{'inspect':'Read the accessible contract.','bind':'Identify the current objects and assumptions.',
       'compare':'Compare the bound premise with the failing obligation.','probe':'If a justified instance differs, derive it locally.',
       'fallback':'If no difference is found, stop this diagnosis.'},
      'evidence_summary':'A local edit preceded success; its mechanism remains uncertain.',
      'check':'Recheck the original local obligation.','stop_when':'The required premise is unavailable.',
      'support':{'interpretation_ids':['train:B0'],'fact_ids':['train:0']}}]}


def test_complete_histories_and_review_notes_preserved():
    old={'complete_training_group':{'original':['failed','passed'],'forks':[{'prefix':4,'suffix':['branch']}]},
         'reviewed_facts':[{'fact':'unchanged','review_note':'bundled'}],
         'supplemental_check_evidence':['nonindexed command'], 'output_contract':c.previous.CONTRACT}
    accepted,_=evidence();q=c.make_request({'user':json.dumps(shared_strings(old))},accepted)
    restored=expand_strings(json.loads(q['user']))
    for k in old:
        if k!='output_contract':assert restored[k]==old[k]
    assert restored['reviewed_interpretations']==accepted and q['cap']==32768


def test_five_fields_rendered_without_deployment():
    got,d=c.audit(response(),*evidence());assert len(got)==1
    assert got[0]['semantic_review_required'] and not got[0]['deployed']
    assert got[0]['host_boundaries']=={'train:B0':'Mechanism uncertain.'}
    assert [x.split(':')[0] for x in got[0]['rendered_card'].split('**')[1::2]]==['Trigger','Action','Why','Validate','Avoid when']


def test_empty_output_valid_and_multiple_candidates_stop():
    assert c.audit({'selection_reason':'No useful decision.','candidates':[]},*evidence())==([],[])
    v=response();v['candidates']*=2
    with pytest.raises(ValueError,match='one candidate'):c.audit(v,*evidence())


def test_unknown_or_unrelated_support_rejected():
    v=response();v['candidates'][0]['support']['interpretation_ids']=['other:B0']
    assert not c.audit(v,*evidence())[0]
    interp,facts=evidence();facts.append({'fact_id':'train:1','fact_sha256':'extra'});v=response();v['candidates'][0]['support']['fact_ids']=['train:1']
    assert not c.audit(v,interp,facts)[0]


def test_recipe_or_evidence_id_blocked_preserving_raw():
    for term in ['assert(p.satisfied_by(ex))','`a historical formula`','T3W003','forall|x| target(x)']:
        v=response();v['candidates'][0]['operation']['probe']=term;before=copy.deepcopy(v)
        assert not c.audit(v,*evidence())[0] and v==before


def test_hash_tamper_blocks_dispatch(tmp_path):
    p=tmp_path/'input';p.write_text('reviewed')
    (tmp_path/'contract.json').write_text(json.dumps({'authorization':c.AUTH,'input_hashes':{str(p):c.previous.base.prior.old.sha(p)}}))
    c.check(tmp_path);p.write_text('altered')
    with pytest.raises(ValueError,match='changed'):c.check(tmp_path)


def test_started_run_cannot_restart(tmp_path,monkeypatch):
    parent=tmp_path/'parent';parent.mkdir();(tmp_path/'started.json').write_text('{}')
    monkeypatch.setattr(c,'check',lambda _: {'parent_root':str(parent)})
    client=Mock();monkeypatch.setattr(c.previous,'client',client)
    with pytest.raises(ValueError,match='restart'):c.run(tmp_path)
    client.assert_not_called()


def test_failure_does_not_retry_or_start_next_group(tmp_path,monkeypatch):
    parent=tmp_path/'parent';parent.mkdir();(tmp_path/'config.json').write_text('{}');(tmp_path/'requests').mkdir()
    (tmp_path/'requests/action-first.json').write_text('{}')
    monkeypatch.setattr(c,'check',lambda _: {'parent_root':str(parent),'calls':[{'source_task':'first'},{'source_task':'next'}]})
    monkeypatch.setattr(c.previous.base.prior.old.prior,'credentials',lambda _:None)
    client=Mock();client.call.side_effect=RuntimeError('incomplete');monkeypatch.setattr(c.previous,'client',lambda *args:client)
    with pytest.raises(RuntimeError,match='incomplete'):c.run(tmp_path)
    assert client.call.call_count==1 and not (tmp_path/'completed.json').exists()
    assert json.loads((tmp_path/'stopped.json').read_text())['automatic_retry'] is False
