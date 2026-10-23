import copy
import pytest
from continue_full_trace_facts import normalize_coverage
from test_chained_full_traces import registry,response
import extract_chained_full_traces as base


def test_map_conversion_is_lossless_and_not_semantic_approval():
    x=response();x['trace_coverage']={r['trace_key']:r for r in x['trace_coverage']};before=copy.deepcopy(x)
    value,change=normalize_coverage(x,registry())
    assert x==before and value['facts']==x['facts'] and 'object -> array' in change
    assert {r['trace_key']:r for r in value['trace_coverage']}==x['trace_coverage']
    assert base.audit(value,registry())[0][0]['semantic_review_required']


def test_conflicting_key_or_missing_trace_is_not_repaired():
    x=response();x['trace_coverage']={r['trace_key']:r for r in x['trace_coverage']}
    x['trace_coverage']['T1']['trace_key']='T0'
    with pytest.raises(ValueError):normalize_coverage(x,registry())
    del x['trace_coverage']['T1']
    with pytest.raises(ValueError):normalize_coverage(x,registry())


def test_conversion_does_not_repair_bad_quotes():
    x=response();x['trace_coverage']={r['trace_key']:r for r in x['trace_coverage']}
    x['facts'][0]['quotes'][1]['text']='precondition not satisfied'
    value,_=normalize_coverage(x,registry())
    assert base.audit(value,registry())[1][0]['status']=='mechanical_reject'
