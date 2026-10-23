import resume_ten_card_seven_arm_second as r


def test_second_recovery_keeps_all_89_outcomes_and_selects_only_23():
    jobs=r.e.schedule([{'id':str(i)} for i in range(8)])
    rows=[{'task_id':j['id'],'condition':j['condition'],'repeat':j['repeat'],
           'outcome':'timeout' if i%2 else 'budgeted_dual_pass'} for i,j in enumerate(jobs[:89])]
    rows += [{'task_id':j['id'],'condition':j['condition'],'repeat':j['repeat'],
              'outcome':'infrastructure_aborted'} for j in jobs[89:91]]
    remaining,kept,retry=r.select_remaining(jobs,rows)
    assert remaining==jobs[89:]
    assert len(kept)==89 and len(retry)==2 and len(remaining)==23
    assert not set(kept)&{r.e.prior.driver.episode_key(j) for j in remaining}


def test_merge_preserves_all_previous_infrastructure_attempts(tmp_path):
    parent=tmp_path/'parent';root=tmp_path/'new';parent.mkdir();root.mkdir()
    old={'task_id':'a','condition':'no_skill','repeat':0,'budgeted_dual_pass':False,'outcome':'timeout'}
    infra={**old,'task_id':'b','outcome':'infrastructure_aborted'}
    r.write_json(parent/'combined-report.json',{'rows':[old],'infrastructure_attempt_history':[infra,infra]})
    r.write_json(root/'validation_contract.json',{'recovery_parent':str(parent),'caveat':'test'})
    for n in ['evaluation','total']:r.write_json(tmp_path/n,{})
    r.write_json(root/'budget-baseline.json',{'evaluation_ledger':str(tmp_path/'evaluation'),'total_ledger':str(tmp_path/'total')})
    r.report_merged(root,[{**old,'task_id':'b','budgeted_dual_pass':True,'outcome':'budgeted_dual_pass'}])
    out=r.read(root/'combined-report.json')
    assert out['valid_terminal']==2 and len(out['infrastructure_attempt_history'])==2
    assert out['rows'][0]==old and out['rows'][1]['attempt_source']=='recovery2'
