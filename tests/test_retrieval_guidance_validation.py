import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def guidance_driver(monkeypatch):
    scripts = Path(__file__).resolve().parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('guidance_validation',scripts/'validate_retrieval_guidance.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_prepare_enforces_same_bank_index_and_both_permissions(tmp_path, monkeypatch, guidance_driver):
    from skillopt_verusage.card_bank import build_bundle, DIAGNOSTIC_RETRIEVAL_GUIDANCE
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT',str(tmp_path))
    repo = tmp_path/'repo'; fixture = repo/'fixed-claude-stratified-80-seed20260814/val'
    fixture.mkdir(parents=True)
    (fixture/'items.json').write_text(json.dumps([{'id':str(i)} for i in range(20)]))
    config = tmp_path/'config.json'; config.write_text(json.dumps({'repo':str(repo)}))
    seed = tmp_path/'seed.md'; seed.write_text('Base skill\n')
    bank = tmp_path/'bank.json'; bank.write_text(json.dumps({'schema_version':'stage-card-bank-v1','cards':[
        {'id':'card-001','content':'**Trigger:** failure **Action:** inspect **Why:** evidence **Validate:** both **Avoid when:** absent'}]}))
    descriptions = tmp_path/'descriptions.json'
    descriptions.write_text(json.dumps({'index_descriptions':{'card-001':'failure routing'}}))
    baseline = tmp_path/'baseline'; build_bundle(bank,seed,baseline,autonomous_retrieval=True,
        index_descriptions={'card-001':'failure routing'})
    captured = {}
    def prepare(config, old, new, root, **kwargs):
        captured.update(kwargs)
        return {'input_hashes':{}}
    monkeypatch.setattr(guidance_driver.driver,'prepare',prepare)
    root = tmp_path/'run'; root.mkdir()
    result = guidance_driver.prepare(config,baseline,seed,descriptions,root)
    assert len(captured['task_ids'])==20
    assert captured['installed_library_conditions']==('old','revised')
    assert result['guidance_only'] and not result['bank_changed'] and not result['index_changed']
    for name in ('cards.json','card_read.py'):
        assert (root/'control'/name).read_bytes()==(root/'guided'/name).read_bytes()
    assert (root/'guided/SKILL.md').read_text().replace(DIAGNOSTIC_RETRIEVAL_GUIDANCE,'') == (baseline/'SKILL.md').read_text()


def test_summary_separates_late_dual_pass_and_incomplete_schedule(tmp_path,guidance_driver):
    row = {'id':'one','proof_solved':True,'safety_passed':True,'within_budget':False,
           'timed_out':True,'actor_wall_seconds':600}
    usage = {k:0 for k in ('requests','prompt_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens',
        'completion_tokens','reasoning_tokens','estimated_cost_usd','unknown_cost_requests')}
    (tmp_path/'validation_contract.json').write_text(json.dumps({'items':[{'id':'one'}]}))
    value = {'rows':[{'condition':'old','row':row,'retrieval':{'read_calls':1,'read_ids':['card-001']},
        'settled_usage':usage}], 'failures':[],'reviewed_inputs_unchanged':True,'bridge_drained':True,'caveat':'dev'}
    (tmp_path/'summary.json').write_text(json.dumps(value))
    result = guidance_driver.aggregate(tmp_path)
    assert not result['complete']
    assert result['totals']['old']['within_budget_dual_pass']==0
    assert result['totals']['old']['final_dual_pass']==1
    assert result['totals']['old']['body_read_episodes']==1
