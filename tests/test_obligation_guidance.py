import shutil
import pytest
import evaluate_obligation_guidance as m
import evaluate_index_matching_v2 as previous


def test_matrix_is_exact24_with_shared_v2_index():
    jobs=m.schedule()
    assert len(jobs)==len({(j['id'],j['condition'],j['repeat']) for j in jobs})==24
    assert m.ARMS==('G0_original_main','G1_obligation_main')
    assert len(previous.schedule())==16
    assert all(set(j)=={'id','condition','repeat'} for j in jobs)
    for task in m.shared.TASK_IDS:
        for arm in m.ARMS:
            assert sorted(j['repeat'] for j in jobs if j['id']==task and j['condition']==arm)==[0,1,2]
    for n in range(0,24,2):
        a,b=jobs[n:n+2]
        assert (a['id'],a['repeat'])==(b['id'],b['repeat'])
        assert {a['condition'],b['condition']}==set(m.ARMS)
    assert sum(jobs[n]['condition']==m.ARMS[0] for n in range(0,24,2))==6


def approval(root):
    (root/'validation_contract.json').write_text('{}')
    packet=dict(contract_sha256=m.sha(root/'validation_contract.json'),approved=True,episodes=24,
                new_batch_cap_usd=20,destination='https://api.deepseek.com',automatic_paid_retry=False,
                background_launch=True,pricing_verified=True,explicit_data_transfer_approved=True,
                user_instruction='Synthetic fixture only',pricing_evidence='fixture')
    path=root/'approval.json';m.write_json(path,packet)
    return path,packet


def test_reject_wrong_matrix_stale_contract_and_missing_transfer_authority(tmp_path):
    path,a=approval(tmp_path);m.validate_authorization(tmp_path,path)
    for key,value in [('episodes',16),('contract_sha256','stale'),('explicit_data_transfer_approved',False),('new_batch_cap_usd',80)]:
        m.write_json(path,{**a,key:value})
        with pytest.raises(ValueError):m.validate_authorization(tmp_path,path)


def test_no_authority_stops_before_credentials(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'check',lambda p:{})
    monkeypatch.setattr(m.e.prior,'credentials',lambda *a:pytest.fail('credentials touched'))
    with pytest.raises(ValueError,match='No API launch authorization'):m.run(tmp_path,None)
    assert not list(tmp_path.iterdir())


def test_materials_detect_index_body_and_control_tampering(tmp_path):
    source=m.shared.REPO/'research_artifacts/skill-chain-seven-arm-20261022/bundles/new_skeleton'
    baseline=tmp_path/'baseline';review=tmp_path/'review';root=tmp_path/'run'
    shutil.copytree(source,baseline/'bundles/I2_matching_v2');review.mkdir()
    old=baseline/'bundles/I2_matching_v2/SKILL.md'
    old.write_bytes(old.read_bytes().split(b'## Card index\n')[0]+(m.shared.DESIGN/'INDEX_COMPACT_V2.md').read_bytes())
    control=old.read_text().replace('python3 card_read.py card-001','python3 card_read.py new-001')
    additions=['First insertion. ', 'Second insertion. ', 'Third insertion. ']
    draft=review/'SKILL.draft.md';draft.write_text(''.join(additions)+control)
    m.write_json(review/'checks.json',dict(status='minimal_in_place_revision_review_only',draft_sha256=m.sha(draft),insertions=additions))
    for arm,main in zip(m.ARMS,[control,draft.read_text()]):
        shutil.copytree(source,root/'bundles'/arm)
        (root/'bundles'/arm/'SKILL.md').write_text(main)
    for name in ('EXECUTIVE.md','TASK.md','task-selection.json'):
        (baseline/name).write_text('unchanged');shutil.copyfile(baseline/name,root/name)
    m.verify_materials(root,review,baseline)
    for target in [root/'bundles'/m.ARMS[0]/'SKILL.md',root/'bundles'/m.ARMS[1]/'SKILL.md',root/'bundles'/m.ARMS[1]/'cards.json',root/'TASK.md']:
        old_content=target.read_bytes();target.write_bytes(old_content+b'changed')
        with pytest.raises(ValueError):m.verify_materials(root,review,baseline)
        target.write_bytes(old_content)
    # Even a newly hashed draft cannot silently alter the frozen index or delete original text.
    draft.write_text(draft.read_text().replace('new-010:', 'changed-010:'))
    packet=m.read(review/'checks.json');packet['draft_sha256']=m.sha(draft);m.write_json(review/'checks.json',packet)
    with pytest.raises(ValueError,match='exceed reviewed insertions'):m.reviewed_mains(review,baseline)


def test_run_requests24_and_never_automatically_restarts(tmp_path,monkeypatch):
    path,a=approval(tmp_path)
    m.write_json(tmp_path/'config.json',{})
    m.write_json(tmp_path/'budget-proposal.json',{'context_window_safe_reserve_usd':1.90316544})
    monkeypatch.setattr(m,'check',lambda p:{'schedule':m.schedule()})
    monkeypatch.setattr(m.e.prior,'credentials',lambda config:None)
    def fake_run(config,root,contract,**kw):
        assert kw['expected_episodes']==24 and len(contract['schedule'])==24
        m.write_json(root/'summary.json',{'completed_episodes':24})
    monkeypatch.setattr(m.e.prior.driver,'run',fake_run)
    monkeypatch.setattr(m,'report',lambda root:{'planned':24})
    m.run(tmp_path,path)
    assert m.read(tmp_path/'completed.json')['episodes']==24
    with pytest.raises(ValueError,match='No automatic restart'):m.run(tmp_path,path)


def test_prepared_report_says24_and_started_cost_not_zero(tmp_path):
    m.write_json(tmp_path/'validation_contract.json',{})
    assert m.report(tmp_path)=={'status':'offline_prepared_no_actor_results','planned':24,'paid_calls':0}
    (tmp_path/'started.json').write_text('{}')
    assert m.report(tmp_path)['paid_calls']=='unknown_pending_ledger_review'
