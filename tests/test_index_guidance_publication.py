"""Publication integrity and result consistency, without private archives."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1] / 'research_artifacts/index-guidance-followups-20261028'


def test_published_source_hashes_and_verbatim_materials():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for item in manifest['files']:
        digest = hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest()
        assert digest == item['sha256']
        if item['transformation'] == 'verbatim':
            assert digest == item['source_sha256']
    bundles = list(ROOT.glob('*/bundles/*'))
    assert len(bundles) == 6
    for name in ('cards.json', 'card_read.py'):
        assert len({hashlib.sha256((p / name).read_bytes()).hexdigest() for p in bundles}) == 1


def test_interventions_match_approved_factor_boundaries():
    def main(batch, arm):
        return (ROOT / batch / 'bundles' / arm / 'SKILL.md').read_text()
    old = main('index_v2', 'I0_old_index')
    v2 = main('index_v2', 'I2_matching_v2')
    assert old.split('## Card index\n')[0] == v2.split('## Card index\n')[0]
    g0 = main('main_G1', 'G0_original_main')
    g1 = main('main_G1', 'G1_obligation_main')
    assert g0 == v2.replace('python3 card_read.py card-001', 'python3 card_read.py new-001', 1)
    receipt = json.loads((ROOT / 'main_G1/reviewed-insertions.json').read_text())
    assert len(receipt['insertions']) == 3
    inverse = g1
    for text in receipt['insertions']:
        assert inverse.count(text) == 1
        inverse = inverse.replace(text, '', 1)
    assert inverse == g0
    assert g1 == main('premise_G2', 'G1_current')
    import evaluate_guidance_premises as g2
    assert main('premise_G2', 'G2_premise_check') == g1.replace(g2.OLD_TEXT, g2.NEW_TEXT, 1)


def test_published_episode_counts_and_primary_results():
    expected = {'index_v2': (16, {'I0_old_index': 5, 'I2_matching_v2': 6}),
                'main_G1': (24, {'G0_original_main': 9, 'G1_obligation_main': 10}),
                'premise_G2': (24, {'G1_current': 10, 'G2_premise_check': 8})}
    for batch, (count, passes) in expected.items():
        with (ROOT / batch / 'episodes.csv').open(newline='') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == len({(r['task_id'], r['condition'], r['repeat']) for r in rows}) == count
        for arm, successes in passes.items():
            assert sum(r['condition'] == arm and r['primary_same_hash_dual_600'] == 'True' for r in rows) == successes


def test_time_ratios_reproduce_from_all_published_cells():
    spec = importlib.util.spec_from_file_location('publication_ratios', ROOT / 'timing/recompute_ratios.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.compute()
    assert result['index_v2']['wall_seconds'] < 1
    assert result['main_G1']['wall_seconds'] > 1
