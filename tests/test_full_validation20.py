import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def module(monkeypatch):
    scripts = Path(__file__).resolve().parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('full_validation20_test',scripts/'full_validation20.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_combines_exact20_per_arm_and_keeps_failed_outcomes(tmp_path, module):
    parent = tmp_path/'parent'; parent.mkdir()
    def entry(i,condition):
        return {'condition':condition,'row':{'id':str(i),'proof_solved':i!=19,
            'safety_passed':True,'actor_wall_seconds':2},'retrieval':{'read_ids':[]},
            'settled_usage':{k:1 for k in ('requests','prompt_tokens','prompt_cache_hit_tokens',
                'prompt_cache_miss_tokens','completion_tokens','reasoning_tokens',
                'estimated_cost_usd','unknown_cost_requests')}}
    rows = [entry(i,c) for i in range(20) for c in ('old','revised')]
    (parent/'summary.json').write_text(json.dumps({'rows':rows[:8]}))
    (tmp_path/'summary.json').write_text(json.dumps({'rows':rows[8:],'failures':[]}))
    contract = {'parent_root':str(parent),'parent_summary_sha256':module.driver.sha(parent/'summary.json'),
                'caveat':'development'}
    module.aggregate(tmp_path,contract)
    result = json.loads((tmp_path/'full_validation_summary.json').read_text())
    assert result['complete'] and len(result['rows'])==40
    assert result['totals']['all20']['revised']['n']==20
    assert result['totals']['all20']['revised']['dual_pass']==19
    assert result['totals']['remaining16']['old']['n']==16
    (tmp_path/'summary.json').write_text(json.dumps({'rows':[rows[0]],'failures':[]}))
    with pytest.raises(ValueError,match='Duplicate'):
        module.aggregate(tmp_path,contract)
