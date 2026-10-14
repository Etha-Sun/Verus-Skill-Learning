"""Check published skill hashes and recompute four-arm metrics without API calls."""
from pathlib import Path
import csv
import hashlib
import json

from plot_four_arm_evaluation import normalize, paired, summarize


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'research_artifacts/card-organization-20261014'


def read(path):
    return json.loads(path.read_text())


def main():
    manifest = read(ARTIFACT / 'PUBLICATION_MANIFEST.json')
    for entry in manifest['files']:
        path = ROOT / entry['published_path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['published_sha256'], path
    contracts = [read(ARTIFACT / 'contracts' / label / 'validation_contract.json')
                 for label in ('round1', 'round2')]
    assert contracts[0]['artifacts']['revised'] == contracts[1]['artifacts']['old']
    tasks = [{item['id']: item['source_sha256'] for item in contract['items']}
             for contract in contracts]
    assert tasks[0] == tasks[1] and len(tasks[0]) == 20
    for package, artifact in (
        ('A-flat78', contracts[0]['artifacts']['old']),
        ('B-grouped', contracts[0]['artifacts']['revised']),
        ('C-selective', contracts[1]['artifacts']['revised']),
    ):
        directory = ARTIFACT / 'skills' / package
        actual = {str(path.relative_to(directory)) for path in directory.rglob('*') if path.is_file()}
        assert actual == {entry['relative_path'] for entry in artifact['files']}, package
        for entry in artifact['files']:
            content = (directory / entry['relative_path']).read_bytes()
            assert hashlib.sha256(content).hexdigest() == entry['sha256'], entry
            assert len(content) == entry['size_bytes'], entry
    rows = []
    for round_number, relative in enumerate(
        ('round1/combined_summary.json', 'round2/summary.json'), 1
    ):
        summary = read(ARTIFACT / 'contracts' / relative)
        assert len(summary['rows']) == 40
        for entry in summary['rows']:
            assert entry['row']['source_sha256'] == tasks[0][entry['row']['id']]
            rows.append(normalize(entry, round_number))
    with (ARTIFACT / 'evaluation/episodes.csv').open(newline='') as handle:
        published_rows = list(csv.DictReader(handle))
    assert len(published_rows) == 80
    for expected, actual in zip(rows, published_rows):
        assert {key: '' if value is None else str(value) for key, value in expected.items()} == actual
    metrics = read(ARTIFACT / 'evaluation/metrics.json')
    groups = [[row for row in rows if row['round'] == number and row['condition'] == condition]
              for number in (1, 2) for condition in ('old', 'revised')]
    assert all(len(group) == 20 for group in groups)
    assert [summarize(group) for group in groups] == metrics['arms']
    assert [paired([row for row in rows if row['round'] == number])
            for number in (1, 2)] == metrics['paired']
    print('Verified publication hashes, three frozen packages, 80 episode rows, and all aggregate/paired metrics.')


if __name__ == '__main__':
    main()
