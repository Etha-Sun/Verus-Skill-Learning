"""Validate the published archive without model or verifier calls."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'manifest.json').read_text())
assert len(manifest['runs']) == 38
for run in manifest['runs']:
    base = root / run['task'] / run['version'] / run['checkpoint']
    for file in run['files']:
        path = base / file['path']
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == file['published_sha256'], path
        if path.suffix == '.rs':
            assert file['source_sha256'] == file['published_sha256'], path
        if path.suffix == '.json':
            json.loads(data)
        if path.suffix == '.jsonl':
            for line in data.splitlines():
                json.loads(line)
    events = [json.loads(line) for line in (base / 'agent_events.jsonl').read_text().splitlines()]
    assert len(events) == run['event_count']
    for event in events:
        record = event.get('data', {})
        if record.get('snapshot'):
            data = (base / record['snapshot']).read_bytes()
            if record.get('candidate_sha256'):
                assert hashlib.sha256(data).hexdigest() == record['candidate_sha256']
        if record.get('diff'):
            assert (base / record['diff']).is_file()
print('Validated 38 runs: file hashes, JSON streams, source identity and snapshot references.')
