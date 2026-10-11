import importlib.util
import hashlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def full(monkeypatch):
    scripts = Path(__file__).resolve().parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('full_executive',scripts/'full_executive_validation.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_schedule_has80_unique_balanced_keys(full):
    ids = [str(i) for i in range(20)]; jobs = full.schedule(ids)
    assert len(jobs)==80 and len({full.driver.episode_key(x) for x in jobs})==80
    for i in range(20): assert jobs[2*i]['condition']!=jobs[40+2*i]['condition']


@pytest.mark.parametrize('scheduler_fix',[False,True])
def test_prepare_preserves_pilot_methods_prompt_and_bundles(tmp_path,monkeypatch,full,scheduler_fix):
    repo = tmp_path/'repo'; fixture = repo/'fixed-claude-stratified-80-seed20260814/val'
    fixture.mkdir(parents=True)
    ids = list(full.PILOT_TASKS)+[str(i) for i in range(14)]
    (fixture/'items.json').write_text(json.dumps([{'id':i} for i in ids]))
    config = tmp_path/'config.json'; config.write_text(json.dumps({'repo':str(repo)}))
    seeds = repo/'skillopt-verusage/skills'; seeds.mkdir(parents=True)
    (seeds/'initial.md').write_text('Old\n'); (seeds/'diagnostic-first-v1.md').write_text('New\n')
    method = repo/'scripts/validate_executive_revision.py'; method.parent.mkdir()
    method.write_text('frozen method')
    (method.parent/'audit_executive_pilot.py').write_text('audit method')
    pilot = tmp_path/'pilot'; pilot.mkdir(); bundles = {}
    for condition,prefix in (('old','Old'),('revised','New')):
        bundle = pilot/condition; bundle.mkdir(); bundles[condition] = str(bundle)
        (bundle/'SKILL.md').write_text(prefix+'\nSAME RETRIEVAL INDEX\n')
        (bundle/'cards.json').write_text('same cards'); (bundle/'card_read.py').write_text('same reader')
    parent = {'input_hashes':{},'bundle_paths':bundles,'arm_labels':{'old':'initial','revised':'new'},
              'primary_endpoint':'within_budget_dual_pass'}
    if scheduler_fix:
        path = Path(full.driver.__file__).resolve()
        old_source = path.read_text().replace(
            'range(min(2,len(contract[\'schedule\'])))','range(2)')
        parent['input_hashes'][str(path)] = hashlib.sha256(old_source.encode()).hexdigest()
    (pilot/'validation_contract.json').write_text(json.dumps(parent))
    (pilot/'executive_summary.json').write_text(json.dumps({'complete':True}))
    prompt = full.build_prompt(installed_library_root=Path('/installed/vstd'))
    (pilot/'shared_task_prompt.txt').write_text(prompt)
    captured = {}
    def prepare(*args,**kwargs):
        captured.update(kwargs)
        return {'input_hashes':{},'installed_library_root':'/installed/vstd'}
    monkeypatch.setattr(full.driver,'prepare',prepare)
    root = tmp_path/'run'; (root/'pilot_audit').mkdir(parents=True)
    (root/'pilot_audit/audit.json').write_text('{}')
    result = full.prepare(config,pilot,root,singleton_scheduler_fix=scheduler_fix)
    assert result['expected_episodes']==80 and not result['historical_results_reused']
    assert captured['installed_library_conditions']==('old','revised')
    assert (root/'shared_task_prompt.txt').read_text()==prompt
    assert (root/'control/cards.json').read_bytes()==(root/'diagnostic/cards.json').read_bytes()
    assert str(root/'pilot_audit/audit.json') in result['input_hashes']
    assert bool(result['scheduler_only_updates'])==scheduler_fix
    parent['input_hashes'][str(method)] = 'unexpected-method-drift'
    (pilot/'validation_contract.json').write_text(json.dumps(parent))
    with pytest.raises(ValueError,match='Pilot methods changed'):
        full.prepare(config,pilot,tmp_path/'bad',singleton_scheduler_fix=True)


def test_aggregate_matrix_strata_and_late_errors(tmp_path,full):
    ids = list(full.PILOT_TASKS)+[str(i) for i in range(14)]
    jobs = full.schedule(ids)
    contract = {'items':[{'id':i} for i in ids],'schedule':jobs,
                'pilot_task_ids':list(full.PILOT_TASKS),'caveat':'dev'}
    (tmp_path/'validation_contract.json').write_text(json.dumps(contract))
    rows = [{'condition':job['condition'],'row':{'id':job['id'],
        'bridge_task_key':full.driver.episode_key(job),'proof_solved':True,'safety_passed':True,
        'within_budget':True,'timed_out':False,'actor_wall_seconds':10},
        'retrieval':{'read_ids':[],'read_calls':0},'settled_usage':dict.fromkeys(
            (*full.USAGE,'error_requests','unmetered_requests','completed_requests'),0)} for job in jobs]
    value = {'rows':rows,'failures':[],'reviewed_inputs_unchanged':True,'bridge_drained':True}
    source = tmp_path/'summary.json'
    source.write_text(json.dumps(value)); result = full.aggregate(tmp_path)
    assert result['complete'] and result['totals']['old']['n']==40
    assert result['strata']['pilot6']['old']['n']==12
    assert result['strata']['remaining14']['revised']['n']==28
    assert result['by_repeat']['0']['old']['n']==20
    value['rows'] = rows[:-1]+rows[:1]; source.write_text(json.dumps(value))
    assert not full.aggregate(tmp_path)['complete']
    value['rows'] = rows; rows[0]['settled_usage']['error_requests'] = 1
    source.write_text(json.dumps(value)); assert not full.aggregate(tmp_path)['complete']


def test_audit_distinguishes_allowed_library_and_outside_commands(full):
    import audit_executive_pilot as audit
    library = Path('/allowed/vstd')
    assert audit.command_flags('rg term /allowed/vstd/set.rs',library)==[]
    assert 'environment_inspection' in audit.command_flags('echo "$PATH"',library)
    assert 'outside_toolchain_introspection' in audit.command_flags('head /home/tool/verus',library)
    assert 'outside_scratch_or_generated_log' in audit.command_flags('cat /tmp/test.rs',library)
    source = '#[verifier::external_body]\npub proof fn helper()\n    ensures true,\n{\n    unimplemented!()\n}\n'
    blocks = audit.trusted_blocks(source)
    assert len(blocks)==1 and blocks[0][0]=='helper' and blocks[0][1]==source
    stacked = source.replace('#[verifier::external_body]',
        '#[verifier::external_body]\n#[verifier(external_body)]')
    assert audit.trusted_blocks(stacked)==[('helper',stacked)]
    alternative = source.replace('#[verifier::external_body]','#[verifier(external_body)]')
    assert audit.trusted_blocks(alternative)==[('helper',alternative)]
