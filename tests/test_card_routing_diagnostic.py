import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from skillopt_verusage.card_query import search


CARDS = [
    {'id':'card-002','content':'**Trigger:** Missing antecedent. **Action:** Use implies.'},
    {'id':'card-001','content':'**Trigger:** Missing antecedent. **Action:** Branch explicitly.'},
    {'id':'card-003','content':'**Trigger:** Sequence goal. **Action:** Find a library lemma.'},
]


def test_query_ranks_matches_deterministically_and_pages():
    first = search(CARDS,'missing antecedent',limit=1)
    assert first['results'][0]['id']=='card-001'
    assert first['total_matches']==2 and first['next_offset']==1
    second = search(CARDS,'missing antecedent',limit=10,offset=1)
    assert [r['id'] for r in second['results']]==['card-002']
    assert second['next_offset'] is None
    assert search(CARDS,'zzzz')['results']==[]
    assert search(CARDS,'library')['results'][0]['id']=='card-003'
    assert len(search(CARDS,'missing sequence',limit=100)['results'])==3


@pytest.mark.parametrize('query,kwargs', [('',{}),('the and',{}),('proof',{'limit':0}),
                                         ('proof',{'offset':-1})])
def test_query_rejects_empty_or_bad_page(query,kwargs):
    with pytest.raises(ValueError):
        search(CARDS,query,**kwargs)


def test_deployed_query_is_standalone_and_emits_auditable_json(tmp_path):
    from skillopt_verusage import card_query
    script = tmp_path/'card_query.py'
    script.write_bytes(Path(card_query.__file__).read_bytes())
    (tmp_path/'cards.json').write_text(json.dumps({'cards':CARDS}))
    result = subprocess.run([sys.executable,str(script),'antecedent','--limit','78'],
                            capture_output=True,text=True,check=True,cwd=tmp_path)
    payload = json.loads(result.stdout)
    assert payload['card_retrieval']==1 and payload['operation']=='search'
    assert len(payload['results'])==2


@pytest.fixture
def driver(monkeypatch):
    scripts = Path(__file__).resolve().parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('routing_diagnostic',scripts/'card_routing_diagnostic.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_has_four_distinct_cases_and_explicit_coverage_gaps(driver):
    assert len(driver.CASES)==4 and len({c[0] for c in driver.CASES})==4
    assert len(driver.ARMS)==4
    assert sum(not case[3] for case in driver.CASES)==2
    assert driver.CASES[1][1]=='000037-candidate.rs'
    assert driver.CASES[1][3]==['card-006','card-058']


def test_hash_gate_rejects_modified_or_missing_input(driver,tmp_path):
    source = tmp_path/'source'; source.write_text('original')
    contract = {'input_hashes':{str(source):driver.sha(source)}}
    driver.check_inputs(contract)
    source.write_text('changed')
    with pytest.raises(ValueError,match='Frozen inputs changed'):
        driver.check_inputs(contract)
    source.unlink()
    with pytest.raises(ValueError,match='Frozen inputs changed'):
        driver.check_inputs(contract)


@pytest.mark.parametrize('provider_valid',[True,False])
def test_execute_continues_checkpoint_without_reference_and_collects_all(driver,tmp_path,monkeypatch,provider_valid):
    from contextlib import contextmanager
    from types import SimpleNamespace
    repo = tmp_path/'repo'; repo.mkdir(); (repo/'.env').write_text('')
    root = tmp_path/'run'; root.mkdir()
    source = repo/'original.rs'; source.write_text('original')
    checkpoint = tmp_path/'checkpoint.rs'; checkpoint.write_text('checkpoint')
    context = tmp_path/'context.txt'; context.write_text('failed diagnostic')
    config = {k:str(tmp_path) for k in ('source_root','scratch_root','codex_bin','verus_bin','lynette_bin')}
    config['repo']=str(repo)
    config_path = tmp_path/'config.json'; config_path.write_text(json.dumps(config))
    monkeypatch.setenv('DEEPSEEK_API_KEY','mock-no-network')
    monkeypatch.setenv('VERUS_SKILL_DATA_ROOT',str(tmp_path/'data'))
    ledger = root/'provider_calls.jsonl'; ledger.write_text('')
    @contextmanager
    def mock_bridge(*args):
        yield SimpleNamespace(ledger_path=ledger,halted_error=None),'mock-url',tmp_path/'manifest'
    calls = []
    def mock_task(**kwargs):
        calls.append(kwargs)
        kwargs['out_dir'].mkdir()
        return {'bridge_task_key':kwargs['bridge_task_key'],'proof_solved':True,
                'provider_valid':provider_valid}
    monkeypatch.setattr(driver,'bridge',mock_bridge)
    monkeypatch.setattr(driver,'run_task',mock_task)
    monkeypatch.setattr(driver,'_bridge_usage',lambda *a:{})
    monkeypatch.setattr(driver,'audit_retrieval',lambda *a:{'read_ids':['card-001']})
    monkeypatch.setattr(driver,'export_transcript',lambda *a:{'completeness':'mock'})
    case = {'id':'one','source_path':'original.rs','source_sha256':driver.sha(source),
            'directory_group':'verified-anvil','checkpoint':str(checkpoint),'context':str(context),
            'bundle_paths':{arm:str(tmp_path) for arm in driver.ARMS},
            'artifacts':{arm:{'artifact_sha256':'mock'} for arm in driver.ARMS},
            'reviewed_card_ids':['card-001']}
    contract = {'config_path':str(config_path),'input_hashes':{},'items':[case],
                'schedule':[{'id':'one','condition':arm} for arm in driver.ARMS],
                'workers':2,'model':'deepseek-v4-pro','reasoning_effort':'max',
                'timeout_seconds':600,'installed_library_root':str(tmp_path),'caveat':'mock'}
    if provider_valid:
        driver.execute(root,contract)
        assert len(calls)==4
    else:
        with pytest.raises(RuntimeError,match='Diagnostic partial/failed'):
            driver.execute(root,contract)
        assert len(calls)==2  # Drain the already dispatched pair, submit no more.
    assert all(c['initial_candidate_source']==checkpoint for c in calls)
    assert all(c['reference_proof_source'] is None and c['reference_kind']=='none' for c in calls)
    assert all(c['continuation_instructions']=='failed diagnostic' for c in calls)
    assert all(c['timeout_seconds']==600 and c['reasoning_effort']=='max' for c in calls)
    summary = json.loads((root/'summary.json').read_text())
    assert summary['completed_episodes']==len(calls) and summary['bridge_drained']
    assert bool(summary['failures']) != provider_valid
    assert all(r['reviewed_card_body_hits']==['card-001'] for r in summary['rows'])


def test_report_excludes_invalid_outcomes_but_preserves_all_attempt_costs():
    scripts = Path(__file__).resolve().parents[1]/'scripts'
    spec = importlib.util.spec_from_file_location('routing_report',scripts/'report_card_routing_diagnostic.py')
    report = importlib.util.module_from_spec(spec); spec.loader.exec_module(report)
    def row(ident,arm,solved,valid=True):
        return {'id':ident,'condition':arm,'row':{'provider_valid':valid,'proof_solved':solved,
            'timed_out':not solved,'actor_wall_seconds':100},
            'settled_usage':{'prompt_tokens':10,'completion_tokens':2,'estimated_cost_usd':0.1},
            'retrieval':{'search_calls':0,'read_calls':0},'reviewed_card_body_hits':[]}
    totals = report.summarize({'rows':[row('a','none',True),row('a','query',True),
                                       row('b','query',False),row('c','query',True,False)]})
    query = totals['arms']['query']
    assert query['valid']==2 and query['success']==1 and query['timeouts']==1
    assert query['all_attempt_usage']['prompt_tokens']==30
    assert query['success_only_usage']['prompt_tokens']==10
    assert totals['joint_success_vs_none']['query']['joint_success_count']==1
