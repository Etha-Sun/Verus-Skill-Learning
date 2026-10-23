import json
from unittest.mock import Mock
import pytest
import evaluate_ten_card_seven_arm as e


def test_seven_arms_two_repeats_and_no_body_injection():
    jobs=e.schedule([{'id':str(i)} for i in range(8)])
    assert len(jobs)==len({e.prior.driver.episode_key(j) for j in jobs})==112
    for arm in e.ARMS:
        assert len([j for j in jobs if j['condition']==arm])==16
    for task in range(8):
        for rep in range(2):
            assert {j['condition'] for j in jobs if j['id']==str(task) and j['repeat']==rep}==set(e.ARMS)
    assert all(set(j)=={'id','condition','repeat'} for j in jobs)


def test_no_skill_only_shared_executive_without_cards_index_reader(tmp_path):
    e.make_no_skill_bundle('Executive\n',tmp_path/'none')
    assert {p.name for p in (tmp_path/'none').iterdir()}=={'SKILL.md'}
    assert (tmp_path/'none/SKILL.md').read_text()=='Executive\n'


def test_three_representations_have_identical_retrieval_entry(tmp_path):
    ids=[f'new-{i:03d}' for i in range(10)]
    index={'cards':[{'id':i,'title':i,'description':'same source trigger'} for i in ids]}
    for rep in ['prose','skeleton','pseudocode']:
        e.make_bundle({'cards':[{'id':i,'content':rep+' body'} for i in ids]},index,'Executive',tmp_path/rep)
    assert len({(tmp_path/r/'SKILL.md').read_bytes() for r in ['prose','skeleton','pseudocode']})==1
    assert 'pseudocode body' not in (tmp_path/'pseudocode/SKILL.md').read_text()


def prepare_budgets(tmp_path):
    ledger=tmp_path/'A';prev=tmp_path/'previous';root=tmp_path/'new';root.mkdir()
    guards=[e.SharedBudgetGuard(p,approval_limit_usd=cap,prior_spend_usd=0,optimizer_reserve_usd=0,request_reserve_usd=0)
            for p,cap in [(prev/'budget-evaluation.json',20),(ledger/'budget-new-total.json',70)]]
    for g in guards:
        k=g.reserve(1);g.settle(k,cost_usd=.5,usage={})
        k=g.reserve(1.84);g.settle(k,cost_usd=None,usage=None)
    baseline={str(g.path):e.read(g.path) for g in guards}
    (root/'budget-baseline.json').write_text(json.dumps({'evaluation_ledger':str(guards[0].path),'states':baseline}))
    return root,ledger,guards,baseline


def test_known_uncertainty_kept_in_same_ledgers_new_unknown_stops(tmp_path):
    root,ledger,guards,baseline=prepare_budgets(tmp_path)
    actual=e.guards(root,ledger)
    assert actual[0].path==guards[0].path and actual[1].path==guards[1].path
    mux=e.HistoricalUncertaintyMux(actual,baseline)
    k=mux.reserve(.1);mux.settle(k,cost_usd=.05,usage={})
    for g in actual:
        state=e.read(g.path);assert state['target_spend_usd']==.55
        assert state['uncertain_requests']==1 and state['uncertain_spend_usd']==1.84
    k=mux.reserve(.1);mux.settle(k,cost_usd=None,usage=None)
    with pytest.raises(ValueError,match='New unknown'):mux.reserve(.1)
    assert all(not e.read(g.path)['reservations'] for g in actual)


def test_uncertainty_still_reduces_budget_capacity(tmp_path):
    _,_,guards,baseline=prepare_budgets(tmp_path)
    mux=e.HistoricalUncertaintyMux(guards,baseline)
    # 0.5 known + 1.84 uncertain + 18 requested exceeds the20cap.
    with pytest.raises(RuntimeError,match='BUDGET_APPROVAL_REQUIRED'):mux.reserve(18)
    assert all(not e.read(g.path)['reservations'] for g in guards)


def test_second_guard_failure_rolls_back_unsent_first_reservation(tmp_path):
    _,_,guards,baseline=prepare_budgets(tmp_path)
    k=guards[1].reserve(.1);guards[1].settle(k,cost_usd=None,usage=None)
    with pytest.raises(ValueError,match='New unknown'):e.HistoricalUncertaintyMux(guards,baseline).reserve(.1)
    assert all(not e.read(g.path)['reservations'] for g in guards)


def test_no_skill_retrieval_audit_rejects_fabricated_card(tmp_path):
    ep=tmp_path/'episodes/dev_no_skill--task--repeat-0';ep.mkdir(parents=True)
    p=ep/'codex_events.raw.jsonl'
    payload={'card_retrieval':1,'operation':'read','id':'card-002','content':'leaked'}
    p.write_text(json.dumps({'type':'item.completed','item':{'type':'command_execution','command':'cat cards.json','aggregated_output':json.dumps(payload)}}))
    audit=e.audit_reads(p,tmp_path)
    assert audit['read_calls']==0 and len(audit['reader_errors'])==1 and audit['direct_bank_access_commands']


def test_no_paid_restart_after_failure(tmp_path,monkeypatch):
    root,ledger,guards,baseline=prepare_budgets(tmp_path)
    (root/'config.json').write_text('{}');(root/'validation_contract.json').write_text('{}')
    monkeypatch.setattr(e,'check',lambda _:{'shared_ledger_root':str(ledger)})
    monkeypatch.setattr(e.prior,'credentials',lambda _:None)
    run=Mock(side_effect=RuntimeError('provider error'));monkeypatch.setattr(e.prior.driver,'run',run)
    with pytest.raises(RuntimeError,match='provider'):e.run(root)
    assert e.read(root/'stopped.json')['automatic_retry'] is False
    with pytest.raises(ValueError,match='restart'):e.run(root)
    assert run.call_count==1
