import importlib.util
import json
from pathlib import Path
import sys

import pytest


@pytest.fixture
def driver(monkeypatch):
    scripts = Path(__file__).resolve().parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('revision_validation_driver',scripts/'validate_card_revision.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_review_gate_requires_exact_hash_and_reasonable_approval(tmp_path, driver):
    contract = tmp_path/'contract.json'; contract.write_text('{}')
    receipt = tmp_path/'review.json'
    for decision in ('APPROVE','APPROVE_WITH_NONBLOCKING_NOTES'):
        receipt.write_text(json.dumps({'decision':decision,'contract_sha256':driver.sha(contract)}))
        driver.check_review(receipt,contract)
    for decision,digest in (('REJECT',driver.sha(contract)),('APPROVE','wrong')):
        receipt.write_text(json.dumps({'decision':decision,'contract_sha256':digest}))
        with pytest.raises(ValueError):
            driver.check_review(receipt,contract)


def test_prepare_freezes_exactly_four_tasks_and_eight_episodes(tmp_path, driver, monkeypatch):
    repo = tmp_path/'repo'; repo.mkdir()
    fixture = repo/'fixed-claude-stratified-80-seed20260814/val'; fixture.mkdir(parents=True)
    items = []
    for ident in driver.TASKS:
        source = repo/(ident+'.rs'); source.write_text('input')
        items.append({'id':ident,'task_id':ident,'directory_group':'verified-anvil',
                      'source_path':source.name,'source_sha256':driver.sha(source)})
    (fixture/'items.json').write_text(json.dumps(items))
    relatives = ('skill-evolution-pilot/src/skill_evolution_pilot/codex_runner.py',
                 'skillopt-verusage/src/skillopt_verusage/codex_flash_runner.py',
                 'skillopt-verusage/src/skillopt_verusage/provider_capture.py',
                 'skillopt-verusage/review/augmented78_revision.json')
    for relative in relatives:
        path = repo/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('method')
    tools = tmp_path/'tool'; tools.write_text('tool')
    catalog = tmp_path/'models.json'; catalog.write_text('{}')
    config = tmp_path/'config.json'
    config.write_text(json.dumps({'repo':str(repo),'source_root':str(tmp_path),
        'codex_bin':str(tools),'verus_bin':str(tools),'lynette_bin':str(tools)}))
    class Artifact:
        def manifest(self):
            return {'files':[],'artifact_sha256':'bundlehash'}
    monkeypatch.setattr(driver,'load_skill_artifact',lambda _:Artifact())
    root = tmp_path/'output'; root.mkdir()
    value = driver.prepare(config,tmp_path/'old',tmp_path/'new',root)
    assert len(value['items']) == 4 and len(value['schedule']) == 8
    assert {(x['id'],x['condition']) for x in value['schedule']} == {
        (ident,condition) for ident in driver.TASKS for condition in ('old','revised')}
    assert value['workers'] == 2 and value['timeout_seconds'] == 600
    assert value['reference_proof_supplied'] is False and value['ordinary_retry'] is False
    assert value['sealed_test_access'] is False
    assert 'installed_library_conditions' not in value
    with pytest.raises(ValueError):
        driver.prepare(config,tmp_path/'old',tmp_path/'new',root)
    expanded = tmp_path/'expanded'; expanded.mkdir()
    value = driver.prepare(config,tmp_path/'old',tmp_path/'new',expanded,
        task_ids=tuple(reversed(driver.TASKS)), installed_library_conditions=('old','revised'))
    assert value['installed_library_conditions']==['old','revised']
    assert [item['id'] for item in value['items']]==list(reversed(driver.TASKS))
    with pytest.raises(ValueError, match='distinct validation'):
        driver.prepare(config,tmp_path/'old',tmp_path/'new',tmp_path/'bad',task_ids=('unknown',))
