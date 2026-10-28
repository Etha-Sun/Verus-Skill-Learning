import shutil
import pytest
import evaluate_index_ablation as i
import evaluate_retrieval_reassessment as r


def test_index_schedule_is_balanced_without_mutating_historical_module():
    assert r.ARMS == ('R0_current', 'R1_reassess')
    jobs = i.schedule()
    assert len(jobs) == len({(j['id'], j['condition'], j['repeat']) for j in jobs}) == 24
    assert all(set(j) == {'id', 'condition', 'repeat'} for j in jobs)
    for start in range(0, 24, 2):
        a, b = jobs[start:start + 2]
        assert a['id'] == b['id'] and a['repeat'] == b['repeat']
        assert {a['condition'], b['condition']} == set(i.ARMS)
    assert sum(jobs[n]['condition'] == i.ARMS[0] for n in range(0, 24, 2)) == 6


def test_missing_authorization_stops_before_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(i.shared, 'check', lambda root: {})
    monkeypatch.setattr(i.e.prior, 'credentials', lambda *a: pytest.fail('credentials touched'))
    with pytest.raises(ValueError, match='No API launch authorization'):
        i.run(tmp_path, None)
    assert not list(tmp_path.iterdir())


def test_index_tamper_or_extra_actor_file_is_rejected(tmp_path):
    review = tmp_path / 'review'; root = tmp_path / 'run'; baseline = tmp_path / 'baseline'
    source = i.shared.REPO / 'research_artifacts/skill-chain-seven-arm-20261022/bundles/new_skeleton'
    for arm in i.ARMS:
        shutil.copytree(source, review / 'bundles' / arm)
    new = review / 'bundles' / i.ARMS[1] / 'SKILL.md'
    prefix = new.read_bytes().split(b'## Card index\n')[0]
    new.write_bytes(prefix + (i.shared.DESIGN / 'INDEX_COMPACT_V1.md').read_bytes())
    i.write_json(review / 'material-checks.json', {'artifact_hashes': {
        str(p.relative_to(review)): i.sha(p) for p in review.rglob('*') if p.is_file()}})
    shutil.copytree(review / 'bundles', root / 'bundles')
    baseline.mkdir()
    for name in ('EXECUTIVE.md', 'TASK.md', 'task-selection.json'):
        (baseline / name).write_text('unchanged')
        shutil.copyfile(baseline / name, root / name)
    i.verify_materials(root, review, baseline)
    changed = root / 'bundles' / i.ARMS[1] / 'SKILL.md'
    original = changed.read_bytes(); changed.write_bytes(b'Extra rule\n' + original)
    with pytest.raises(ValueError): i.verify_materials(root, review, baseline)
    changed.write_bytes(original)
    (changed.parent / 'answer.rs').write_text('not permitted')
    with pytest.raises(ValueError): i.verify_materials(root, review, baseline)
