import json
from unittest.mock import Mock
import pytest
import run_ten_card_representations as r


def card():
    text='**Trigger:** A local goal is open.\n**Action:** Inspect its actual contract. Prove the missing premise.\n**Why:** A joint edit passed; its mechanism is unknown.\n**Validate:** Recheck the goal.\n**Avoid when:** The premise is unavailable.'
    return {'id':'card-x','title':'Contract check','content':text,'clauses':r.source_clauses(text)}


def result(source):
    return {'actor_card':'# Contract check\nO1: Applicability\nO2: Local proof\nO3: Limits',
            'review_mapping':[{'source_clause_id':x['id'],'output_obligation_ids':['O1','O2','O3'],'preservation_note':'Mapped for semantic review.'} for x in source['clauses']], 'issues':[]}


def test_conversion_contains_only_card_and_contract():
    x=card();request=r.make_request(x);p=json.loads(request['user'])
    assert set(p)=={'source_card','output_contract'} and p['source_card']==x
    assert request['cap']==65536
    with pytest.raises(ValueError,match='Only frozen'):
        r.make_request({**x,'training_trace':'not allowed'})


def test_clause_indexing_preserves_every_section_and_source_spans():
    x=card();assert len(x['clauses'])==6
    assert {p['role'] for p in x['clauses']}=={'Trigger','Action','Why','Validate','Avoid when'}
    assert all(p['text'] in x['content'] for p in x['clauses'])
    with pytest.raises(ValueError,match='source sections'):r.source_clauses('only action')


def test_schema_mapping_pass_is_not_semantic_equivalence():
    x=card();audit=r.audit(result(x),x)
    assert audit['mechanical_pass'] and audit['semantic_equivalence_review_required'] and not audit['actor_ready']


@pytest.mark.parametrize('kind',['missing_source','duplicate_source','unknown_output','unsupported_output','private_id'])
def test_invalid_mapping_is_rejected(kind):
    x=card();v=result(x)
    if kind=='missing_source':v['review_mapping'].pop()
    elif kind=='duplicate_source':v['review_mapping'].append(v['review_mapping'][0])
    elif kind=='unknown_output':v['review_mapping'][0]['output_obligation_ids']=['O99']
    elif kind=='unsupported_output':v['actor_card']+='\nO99: invented'
    elif kind=='private_id':v['actor_card']+='\nS1'
    with pytest.raises(ValueError):r.audit(v,x)


def test_invalid_json_preserved_and_no_second_call_or_restart(tmp_path,monkeypatch):
    ledger=tmp_path/'A';root=tmp_path/'D';ledger.mkdir();root.mkdir();(root/'requests').mkdir()
    (root/'requests/one.json').write_text('{}');(root/'config.json').write_text('{}')
    monkeypatch.setattr(r,'check',lambda _:{'shared_ledger_root':str(ledger),'calls':[{'name':'one'},{'name':'two'}]})
    monkeypatch.setattr(r.c.b,'budget_snapshot',lambda _: {})
    monkeypatch.setattr(r.c.b.b.base.prior.old.prior,'credentials',lambda _:None)
    client=Mock();client.call.return_value=('truncated json',{})
    factory=Mock(return_value=client);monkeypatch.setattr(r.c.b,'client',factory)
    with pytest.raises(json.JSONDecodeError):r.run(root)
    assert client.call.call_count==1 and (root/'responses/one.response.txt').read_text()=='truncated json'
    assert json.loads((root/'stopped.json').read_text())['automatic_retry'] is False
    with pytest.raises(ValueError,match='restart'):r.run(root)
    assert factory.call_count==1
