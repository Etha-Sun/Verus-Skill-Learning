import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def executive(monkeypatch):
    scripts = Path(__file__).resolve().parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('executive_validation',scripts/'validate_executive_revision.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_unique_balanced_repeated_schedule_and_legacy_keys(executive):
    jobs = executive.schedule()
    assert len(jobs)==24 and len({executive.driver.episode_key(x) for x in jobs})==24
    assert {(j['id'],j['condition'],j['repeat']) for j in jobs} == {
        (i,c,r) for i in executive.TASKS for c in ('old','revised') for r in range(2)}
    assert executive.driver.episode_key({'id':'x','condition':'old'})=='dev_old--x'
    for i in range(6):
        assert jobs[2*i]['condition'] != jobs[12+2*i]['condition']


def test_prepare_changes_only_executive(tmp_path,monkeypatch,executive):
    from skillopt_verusage.card_bank import build_bundle, DIAGNOSTIC_RETRIEVAL_GUIDANCE
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT',str(tmp_path))
    bank = tmp_path/'bank.json'
    bank.write_text(json.dumps({'schema_version':'stage-card-bank-v1','cards':[
        {'id':'card-001','content':'**Trigger:** failure **Action:** inspect **Why:** evidence **Validate:** both **Avoid when:** absent'}]}))
    old = tmp_path/'old.md'; old.write_text('Old Executive\n')
    new = tmp_path/'new.md'; new.write_text('New Executive\n')
    desc = tmp_path/'descriptions.json'
    desc.write_text(json.dumps({'index_descriptions':{'card-001':'failure routing'}}))
    baseline = tmp_path/'baseline'
    build_bundle(bank,old,baseline,autonomous_retrieval=True,index_descriptions={'card-001':'failure routing'})
    captured = {}
    def prepare(*args,**kwargs):
        captured.update(kwargs)
        return {'input_hashes':{},'installed_library_root':'/installed/vstd'}
    monkeypatch.setattr(executive.driver,'prepare',prepare)
    root = tmp_path/'run'; root.mkdir()
    value = executive.prepare(tmp_path/'config',baseline,old,new,desc,root)
    assert captured['task_ids']==executive.TASKS
    assert captured['installed_library_conditions']==('old','revised')
    assert value['shared_task_prompt_corrected'] and not value['diagnostic_retrieval_guidance']
    assert len(value['schedule'])==24
    for name in ('cards.json','card_read.py'):
        assert (root/'control'/name).read_bytes()==(root/'diagnostic'/name).read_bytes()
    assert DIAGNOSTIC_RETRIEVAL_GUIDANCE not in (root/'diagnostic/SKILL.md').read_text()
    prompt = (root/'shared_task_prompt.txt').read_text()
    assert 'Pre-existing trusted declarations' in prompt and 'assert(condition)' in prompt
    assert str(root/'shared_task_prompt.txt') in value['input_hashes']


def test_aggregate_requires_full_matrix_and_separates_late_pass(tmp_path,executive):
    jobs = executive.schedule()
    (tmp_path/'validation_contract.json').write_text(json.dumps({'schedule':jobs,'caveat':'development'}))
    rows = []
    for job in jobs:
        rows.append({'condition':job['condition'], 'row':{'id':job['id'],
            'bridge_task_key':executive.driver.episode_key(job),
            'proof_solved':True,'safety_passed':True,'within_budget':False,
            'timed_out':True,'actor_wall_seconds':600},
            'settled_usage':dict.fromkeys(executive.USAGE,0),
            'retrieval':{'read_ids':[],'read_calls':0}})
    value = {'rows':rows,'failures':[],'reviewed_inputs_unchanged':True,'bridge_drained':True}
    source = tmp_path/'summary.json'; source.write_text(json.dumps(value))
    result = executive.aggregate(tmp_path)
    assert result['complete'] and result['totals']['old']['final_dual_pass']==12
    assert result['totals']['old']['within_budget_dual_pass']==0
    value['rows'] = rows[:-1]+rows[:1]
    source.write_text(json.dumps(value))
    assert not executive.aggregate(tmp_path)['complete']
    value['rows'] = rows; value['bridge_drained'] = False
    source.write_text(json.dumps(value))
    assert not executive.aggregate(tmp_path)['complete']
