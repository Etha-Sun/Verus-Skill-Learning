import copy
import resume_ten_card_seven_arm_budget_raised as r


def test_budget_raise_preserves_every_charge_and_usage(tmp_path):
    parent=tmp_path/'parent';control=tmp_path/'control';parent.mkdir();control.mkdir()
    baseline={}
    for key,cap in [('evaluation_ledger',20),('total_ledger',70)]:
        path=tmp_path/key
        g=r.e.SharedBudgetGuard(path,approval_limit_usd=cap,prior_spend_usd=0,optimizer_reserve_usd=0,request_reserve_usd=0)
        g._update(lambda s:s.update(target_spend_usd=11.2,uncertain_spend_usd=5.5,uncertain_requests=3))
        baseline[key]=str(path)
    r.write_json(parent/'budget-baseline.json',baseline)
    before={k:r.read(v) for k,v in baseline.items()}
    r.raise_budgets(parent,control)
    for key,cap in [('evaluation_ledger',30),('total_ledger',80)]:
        after=r.read(baseline[key]);expected=copy.deepcopy(before[key]);expected['approval_limit_usd']=cap
        assert after==expected


def test_only_reservation_blocked_failure_reclassified(tmp_path):
    ancestor=tmp_path/'ancestor';parent=tmp_path/'parent';ancestor.mkdir();parent.mkdir()
    r.write_json(parent/'validation_contract.json',{'recovery_parent':str(ancestor)})
    r.write_json(ancestor/'combined-report.json',{'rows':[],'infrastructure_attempt_history':[]})
    rows=[]
    for name,timeout,code,text,outcome in [('blocked',False,1,'DEEPSEEK_BUDGET_CAPACITY_TIMEOUT','actor_error'),('timeout',True,1,'','timeout'),('success',False,0,'','budgeted_dual_pass')]:
        ep=tmp_path/name;ep.mkdir();r.write_json(ep/'result.json',{'timed_out':timeout,'codex_returncode':code});(ep/'codex_events.raw.jsonl').write_text(text)
        rows.append({'episode':str(ep),'outcome':outcome})
    r.write_json(parent/'report.json',{'rows':rows})
    valid,history,latest=r.normalized_parent(parent)
    assert [x['outcome'] for x in valid]==['timeout','budgeted_dual_pass']
    assert len(history)==1 and history[0]['original_report_outcome']=='actor_error'
    assert latest[0]['outcome']=='infrastructure_aborted'
