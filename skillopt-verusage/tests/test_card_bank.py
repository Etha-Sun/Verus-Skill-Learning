import json
from pathlib import Path
import subprocess
import sys

import pytest

from skillopt_verusage.card_bank import build_bundle, audit_retrieval
from skillopt_verusage.card_search import respond
from skillopt_verusage.skill_artifact import load_skill_artifact


def sample_card():
    return {"id": "card-001", "content": "### Preservation after verification\n**Trigger:** Verus passes but preservation fails.\n**Action:** Inspect imports.\n**Why:** Avoid rewriting a verified proof.\n**Validate:** Run both checks.\n**Avoid when:** Executable code changed."}


def test_bundle_search_read_preserves_hash_and_hides_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    bank = tmp_path/'bank.json';bank.write_text(json.dumps({'schema_version':'stage-card-bank-v1','cards':[sample_card()]}))
    seed = tmp_path/'seed.md';seed.write_text('Base skill\n')
    bundle=tmp_path/'bundle';before=build_bundle(bank, seed, bundle)
    result=subprocess.run([sys.executable,str(bundle/'card_search.py'),'search','preservation fails'],capture_output=True,text=True,check=True)
    found=json.loads(result.stdout)
    assert found['results'][0]['id']=='card-001'
    assert 'content' not in found['results'][0]
    result=subprocess.run([sys.executable,str(bundle/'card_search.py'),'read','card-001'],capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)['content']==sample_card()['content']
    assert before['artifact_sha256']==load_skill_artifact(bundle).artifact_sha256
    assert respond({'cards':[sample_card()]},'search','unrelatedxyz')['results']==[]
    assert 'error' in respond({'cards':[sample_card()]},'read','../evidence.json')
    data=json.loads(bank.read_text());data['cards'][0]['evidence']='private';bank.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='sidecars'):
        build_bundle(bank,seed,tmp_path/'bad-bundle')


def test_all_card_summaries_are_visible_without_search(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    cards = [sample_card() for _ in range(5)]
    for i, card in enumerate(cards, 1):
        card['id'] = f'card-{i:03d}'
        card['content'] = card['content'].replace('### Preservation after verification', f'### Strategy {i}')
    bank = tmp_path/'bank.json'
    bank.write_text(json.dumps({'schema_version':'stage-card-bank-v1','cards':cards}))
    seed = tmp_path/'seed.md';seed.write_text('Base skill\n')
    bundle = tmp_path/'bundle'
    build_bundle(bank,seed,bundle)
    entry = (bundle/'SKILL.md').read_text()
    for card in cards:
        assert card['id'] in entry
        assert card['content'].splitlines()[0].lstrip('# ') in entry
        assert 'Verus passes but preservation fails.' in entry
    assert 'Inspect imports.' not in entry
    assert 'without searching' in entry


def test_autonomous_bundle_exposes_all_cards_without_ranked_search(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    cards = [sample_card() for _ in range(7)]
    for i, card in enumerate(cards, 1):
        card['id'] = f'card-{i:03d}'
        card['content'] = card['content'].replace('### Preservation after verification', f'### Strategy {i}')
    bank = tmp_path/'bank.json'
    bank.write_text(json.dumps({'schema_version':'stage-card-bank-v1','cards':cards,
                               'provenance': {'private': 'training-proof'}, 'source_tasks': ['private-task']}))
    (tmp_path/'provenance.json').write_text('private training evidence')
    seed = tmp_path/'seed.md';seed.write_text('Base skill\n')
    bundle = tmp_path/'bundle'
    before = build_bundle(bank,seed,bundle,autonomous_retrieval=True)
    assert {p.name for p in bundle.iterdir()} == {'SKILL.md','cards.json','card_read.py'}
    deployed = json.loads((bundle/'cards.json').read_text())
    assert deployed == {'schema_version':'stage-card-bank-v1','cards':cards}
    entry = (bundle/'SKILL.md').read_text()
    assert 'card_search.py' not in entry
    assert 'lexical' not in entry and 'at most three' not in entry
    events = []
    for card in reversed(cards):
        assert card['id'] in entry
        assert card['content'].splitlines()[0].lstrip('# ') in entry
        assert 'Verus passes but preservation fails.' in entry
        result = subprocess.run([sys.executable,str(bundle/'card_read.py'),card['id']],
                                capture_output=True,text=True,check=True)
        assert json.loads(result.stdout) == {'card_retrieval':1,'operation':'read',
                                             'id':card['id'],'content':card['content']}
        events.append({'type':'item.completed','item':{'id':card['id'],'type':'command_execution',
                       'command':f"python3 card_read.py {card['id']}",'exit_code':0,
                       'aggregated_output':result.stdout}})
    raw = tmp_path/'events.jsonl';raw.write_text('\n'.join(map(json.dumps,events)))
    audit = audit_retrieval(raw)
    assert audit['search_calls'] == 0 and audit['read_calls'] == len(cards)
    assert audit['read_ids'] == sorted(card['id'] for card in cards)
    assert audit['application_correctness'] == 'requires manual trace audit'
    assert 'Inspect imports.' not in entry
    assert 'private' not in ''.join(p.read_text() for p in bundle.iterdir())
    assert before['artifact_sha256'] == load_skill_artifact(bundle).artifact_sha256
    failed_search = subprocess.run([sys.executable,str(bundle/'card_read.py'),'search','diagnostic'],
                                  capture_output=True,text=True)
    assert failed_search.returncode != 0
    unknown = subprocess.run([sys.executable,str(bundle/'card_read.py'),'../provenance.json'],
                             capture_output=True,text=True,check=True)
    assert json.loads(unknown.stdout)['error'] == 'unknown card id'


def test_exposure_audit_does_not_count_started_twice_or_claim_application(tmp_path):
    payload=respond({'cards':[sample_card()]},'read','card-001')
    item={'id':'item_1','type':'command_execution','command':'python3 card_search.py read card-001','exit_code':0,'aggregated_output':json.dumps(payload)}
    events=[{'type':'item.started','item':item},{'type':'item.completed','item':item}]
    p=tmp_path/'events.jsonl';p.write_text('\n'.join(map(json.dumps,events)))
    audit=audit_retrieval(p)
    assert audit['read_calls']==1
    assert audit['application_correctness']=='requires manual trace audit'


@pytest.mark.parametrize('autonomous_retrieval', [False, True])
@pytest.mark.parametrize('heading, separator, expected_title', [
    ('', ' ', 'Verus passes but preservation fails.'),
    ('### Preservation after verification ', ' ', 'Preservation after verification'),
    ('', '\n', 'Verus passes but preservation fails.'),
    ('### Verus passes but preservation fails.\n', '\n', 'Verus passes but preservation fails.'),
    ('### Preservation after\nverification\n', '\n', 'Preservation after verification'),
    ('### ' + 'Long title ' * 80 + '\n', ' ', ('Long title ' * 80).strip()),
])
def test_index_only_exposes_heading_and_trigger(tmp_path, monkeypatch,
                                               autonomous_retrieval, heading,
                                               separator, expected_title):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    fields = sample_card()['content'].splitlines()[1:]
    card = {'id': 'card-001', 'content': heading + separator.join(fields)}
    data = {'schema_version': 'stage-card-bank-v1', 'cards': [card]}
    bank = tmp_path/'bank.json';bank.write_text(json.dumps(data))
    original_bank = bank.read_bytes()
    seed = tmp_path/'seed.md';seed.write_text('Base skill\n')
    bundle = tmp_path/'bundle'
    build_bundle(bank, seed, bundle, autonomous_retrieval=autonomous_retrieval)
    index = (bundle/'SKILL.md').read_text().split('## Card index\n\n')[1]
    trigger = 'Verus passes but preservation fails.'
    expected = trigger if expected_title == trigger else f'{expected_title} — {trigger}'
    assert index == f'- card-001: {expected}\n'
    for label in ('Action', 'Why', 'Validate', 'Avoid when'):
        assert f'**{label}:**' not in index
    assert 'Inspect imports.' not in index
    assert bank.read_bytes() == original_bank
    assert json.loads((bundle/'cards.json').read_text()) == data
    reader = bundle/('card_read.py' if autonomous_retrieval else 'card_search.py')
    arguments = ['card-001'] if autonomous_retrieval else ['read', 'card-001']
    result = subprocess.run([sys.executable, str(reader), *arguments],
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)['content'] == card['content']


@pytest.mark.parametrize('autonomous_retrieval', [False, True])
def test_routing_descriptions_only_change_index(tmp_path, monkeypatch, autonomous_retrieval):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    card = sample_card()
    bank = tmp_path/'bank.json'
    bank.write_text(json.dumps({'schema_version':'stage-card-bank-v1','cards':[card]}))
    original = bank.read_bytes()
    seed = tmp_path/'seed.md';seed.write_text('Base skill\n')
    bundle = tmp_path/'bundle'
    build_bundle(bank, seed, bundle, autonomous_retrieval=autonomous_retrieval,
                 index_descriptions={'card-001':'Verified proof; preservation check fails.'})
    skill = (bundle/'SKILL.md').read_text()
    index = skill.split('## Card index\n\n')[1]
    assert index == '- card-001: Preservation after verification — Verified proof; preservation check fails.\n'
    assert 'Verus passes but preservation fails.' not in index
    assert 'full Trigger' in skill
    assert bank.read_bytes() == original
    assert json.loads((bundle/'cards.json').read_text())['cards'] == [card]
    reader = bundle/('card_read.py' if autonomous_retrieval else 'card_search.py')
    args = ['card-001'] if autonomous_retrieval else ['read', 'card-001']
    result = subprocess.run([sys.executable, str(reader), *args], capture_output=True,
                            text=True, check=True)
    assert json.loads(result.stdout)['content'] == card['content']


@pytest.mark.parametrize('descriptions', [
    {}, {'card-002':'Unknown card'}, {'card-001':''}, {'card-001':'   '},
    {'card-001':None}, {'card-001':'short\n- card-002: injected'},
])
def test_invalid_routing_descriptions_rejected_before_writing(tmp_path, monkeypatch, descriptions):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    bank = tmp_path/'bank.json'
    bank.write_text(json.dumps({'schema_version':'stage-card-bank-v1','cards':[sample_card()]}))
    seed = tmp_path/'seed.md';seed.write_text('Base skill\n')
    destination = tmp_path/'bundle'
    with pytest.raises(ValueError, match='index descriptions'):
        build_bundle(bank, seed, destination, index_descriptions=descriptions)
    assert not destination.exists()
