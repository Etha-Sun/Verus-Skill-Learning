import copy
import json
from unittest.mock import Mock
import pytest
import extract_chained_full_traces as new
from skillopt_verusage.campaign_evidence import shared_strings, expand_strings


def registry():
    return {'source_task':'training-fixture','traces':{'T0':{},'T1':{}},
        'windows':{'T0W0':{'trace_key':'T0','before_key':'T0C0','after_key':'T0C1'},
                   'T0W1':{'trace_key':'T0','before_key':'T0C1','after_key':'T0C2'}},
        'records':{'T0C0':{'output':'error: assertion failed','canonical_ref':'original/check0'},
                   'T0C1':{'output':'verification results:: 1 verified, 0 errors','canonical_ref':'original/check1'},
                   'T0C2':{'output':'verification results:: 1 verified, 0 errors','canonical_ref':'original/check2'}}}


def response():
    return {'trace_coverage':[{'trace_key':'T0','considered_window_keys':['T0W0','T0W1'],'note':'Both checks compared'},
                              {'trace_key':'T1','considered_window_keys':[],'note':'No adjacent checks'}],
        'facts':[{'window_keys':['T0W0'],'change':'Added a local assertion.',
                  'observed_result':'The following check passed.','uncertainty':'Mechanism not observed.',
                  'quotes':[{'check_key':'T0C0','text':'error: assertion failed'},
                            {'check_key':'T0C1','text':'1 verified, 0 errors'}]}]}


def test_complete_evidence_and_prefix_connections_preserved():
    original={'current_skill':'Existing skill',
              'complete_training_group':{'original':{'events':['earlier invariant','failed alternative','final result']},
                  'forks':[{'prefix':2,'events':['later branch']}]},
              'evidence_index':registry(),'output_contract':new.prior.EVIDENCE_CONTRACT}
    contract=original.pop('output_contract')
    packed=shared_strings(original,short_keys=True);packed['output_contract']=contract
    req={'user':json.dumps(packed)}
    got,h=new.fresh_request(req); restored=expand_strings(json.loads(got['user']))
    for key in ['current_skill','complete_training_group','evidence_index']:assert restored[key]==original[key]
    assert restored['output_contract']==new.FACT_CONTRACT
    assert got['cap']==32768 and len(h)==64
    assert 'inspection_guidance' not in new.FACT_CONTRACT


def test_unexpected_baseline_contract_is_not_silently_replaced():
    with pytest.raises(ValueError):new.fresh_request({'user':json.dumps({'output_contract':'changed'})})


def test_valid_facts_remain_pending_semantic_review():
    records,decisions=new.audit(response(),registry())
    assert len(records)==1 and records[0]['semantic_review_required'] is True
    assert decisions[0]['status']=='mechanical_pass_semantic_review_pending'
    assert 'decision' not in records[0]


def test_bad_quote_rejects_only_fact_preserving_raw_and_valid_sibling():
    x=response();bad=copy.deepcopy(x['facts'][0]);bad['quotes'][1]['text']='precondition not satisfied'
    x['facts'].append(bad);before=copy.deepcopy(x)
    records,decisions=new.audit(x,registry())
    assert len(records)==1 and decisions[1]['status']=='mechanical_reject' and x==before


def test_invented_or_unrelated_check_not_rebound():
    x=response();x['facts'][0]['quotes'][1]['check_key']='T0C2'
    assert new.audit(x,registry())[1][0]['status']=='mechanical_reject'
    x['facts'][0]['window_keys']=['unknown']
    assert new.audit(x,registry())[1][0]['status']=='mechanical_reject'


def test_multiple_windows_keep_longer_relationships_and_no_window_is_a_call_boundary():
    x=response();x['facts'][0]['window_keys'].append('T0W1')
    x['facts'][0]['quotes'].append({'check_key':'T0C2','text':'1 verified, 0 errors'})
    records,_=new.audit(x,registry());assert len(records[0]['evidence_refs'])==3


def test_coverage_omission_duplicates_or_malformed_envelope_stop():
    x=response();x['trace_coverage'][0]['considered_window_keys'].pop()
    with pytest.raises(ValueError,match='coverage'):new.audit(x,registry())
    x=response();x['trace_coverage'].append(x['trace_coverage'][0])
    with pytest.raises(ValueError,match='coverage'):new.audit(x,registry())
    with pytest.raises(ValueError,match='envelope'):new.audit({'facts':[]},registry())


def test_empty_facts_allowed_and_advice_field_rejected():
    x=response();x['facts']=[];assert new.audit(x,registry())==([],[])
    x=response();x['facts'][0]['inspection_guidance']='use a formula'
    assert new.audit(x,registry())[1][0]['status']=='mechanical_reject'


def test_already_started_run_never_dispatches(tmp_path,monkeypatch):
    (tmp_path/'started.json').write_text('{}')
    monkeypatch.setattr(new,'check',lambda root:{'calls':[]})
    client=Mock();monkeypatch.setattr(new,'client',client)
    with pytest.raises(ValueError,match='restart'):new.run(tmp_path)
    client.assert_not_called()


def test_frozen_input_tampering_blocks_dispatch(tmp_path):
    source=tmp_path/'source.json';source.write_text('original')
    (tmp_path/'contract.json').write_text(json.dumps({'authorization':new.AUTH,
        'input_hashes':{str(source):new.prior.old.sha(source)}}))
    assert new.check(tmp_path)
    source.write_text('changed')
    with pytest.raises(ValueError,match='changed'):new.check(tmp_path)
