import importlib.util
import json
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location('publication', Path(__file__).parents[1]/'scripts/publish_deepseek_artifacts.py')
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


def test_sanitization_preserves_code_and_removes_paths_credentials():
    obj = {'prompt':'assert(x == x); /home/person/proof.rs /zp_vegeta/scratch_sb/user/proof.rs',
           'authorization':'secret value', 'nested':{'encrypted_content':'opaque'},
           'content':'Bearer abc.defgh sk-'+'x'*30+' known-secret'}
    data, counts = publication.sanitize(json.dumps(obj).encode(), '.json', [], ['known-secret'])
    result = json.loads(data)
    assert result['prompt'] == 'assert(x == x); <HOME>/proof.rs <SCRATCH_PATH>'
    assert result['authorization'] == '[REDACTED]'
    assert result['nested']['encrypted_content'] == '[REDACTED]'
    assert counts['known_secret'] == 1
    assert 'abc.defgh' not in data.decode() and 'known-secret' not in data.decode()


def test_text_credentials_and_private_key_fail_closed():
    data, _ = publication.sanitize(b'api_key = "secret-value"\nproof unchanged', '.md', [])
    assert b'secret-value' not in data and b'proof unchanged' in data
    with pytest.raises(ValueError, match='Private key'):
        publication.sanitize(b'-----BEGIN PRIVATE KEY-----\nvalue', '.txt', [])


def test_allowlist_excludes_workspaces_and_sealed():
    assert publication.selected(Path('episodes/a/codex_events.raw.jsonl'))
    assert publication.selected(Path('calls/b/response.raw'))
    assert publication.selected(Path('hints/a/teacher_packet.json'))
    assert publication.selected(Path('provider_failure_evidence/call/response.partial.raw'))
    assert publication.selected(Path('episodes/a/codex_stderr.log'))
    assert not publication.selected(Path('episodes/a/workspace/auth.json'))
    assert not publication.selected(Path('sealed/provider_capture/request.json'))
    assert not publication.selected(Path('models.json'))


def test_export_roundtrip_duplicate_alias_split_archives_and_readonly_sources(tmp_path, monkeypatch):
    root, repo, output = tmp_path/'source', tmp_path/'repo', tmp_path/'publication'
    repo.mkdir()
    (repo/'.env').write_text('DEEPSEEK_API_KEY="private-test-secret"\n')
    run = root/'example-20261011'
    run.mkdir(parents=True)
    original = json.dumps({'text':'proof private-test-secret', 'authorization':'hidden'}).encode()
    (run/'conversation.json').write_bytes(original)
    (run/'prompt.txt').write_text('same prompt')
    second = root/'second-20261011'
    second.mkdir()
    (second/'prompt.txt').write_text('same prompt')
    bank = run/'banks/augmented'
    bank.mkdir(parents=True)
    (bank/'cards.json').write_text(json.dumps({'cards':[{'id':'card-001','action':'assert(x == x);'}]}))
    (run/'workspace').mkdir()
    (run/'workspace/auth.json').write_text('must not publish')
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    monkeypatch.setattr(publication, 'PART_BYTES', 100)
    summary = publication.publish(root, repo, output)
    assert summary['totals']['duplicate_files'] == 1
    assert list((output/'cards').rglob('cards.json'))
    assert all(a['bytes'] <= 100 for r in summary['runs'] for a in r['archives'])
    extra = run/'revised78'
    extra.mkdir()
    (extra/'cards.json').write_text(json.dumps({'cards':[{'id':'card-002'}]}))
    before[extra/'cards.json'] = (extra/'cards.json').read_bytes()
    publication.complete_cards(root, repo, output)
    receipt = publication.audit(output, repo)
    assert receipt['all_aliases_resolvable']
    restored = tmp_path/'restored'
    publication.restore(output, restored)
    assert (restored/'second-20261011/prompt.txt').read_text() == 'same prompt'
    assert 'private-test-secret' not in (restored/run.name/'conversation.json').read_text()
    assert json.loads((restored/run.name/'revised78/cards.json').read_text())['cards'][0]['id']=='card-002'
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='already exists'):
        publication.publish(root, repo, output)
    part = next(output.glob('*.part*'))
    part.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        publication.restore(output, tmp_path/'bad-restore')
