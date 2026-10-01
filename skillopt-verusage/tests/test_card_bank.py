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


def test_exposure_audit_does_not_count_started_twice_or_claim_application(tmp_path):
    payload=respond({'cards':[sample_card()]},'read','card-001')
    item={'id':'item_1','type':'command_execution','command':'python3 card_search.py read card-001','exit_code':0,'aggregated_output':json.dumps(payload)}
    events=[{'type':'item.started','item':item},{'type':'item.completed','item':item}]
    p=tmp_path/'events.jsonl';p.write_text('\n'.join(map(json.dumps,events)))
    audit=audit_retrieval(p)
    assert audit['read_calls']==1
    assert audit['application_correctness']=='requires manual trace audit'
