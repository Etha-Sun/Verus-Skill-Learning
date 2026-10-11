"""Create an outcome-blind training holdout and read-only trace copies."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def family(item):
    parts = item['task_id'].split('__')
    return '__'.join(parts[:-1]) if len(parts) > 2 else parts[0]+'__'+parts[-1].split('_')[0]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n')


def main():
    repo = Path(__file__).resolve().parents[1]
    root = Path(sys.argv[1]).resolve()
    config_path = Path(sys.argv[2]).resolve()
    config = json.loads(config_path.read_text())
    packet = root/'deepscientist/quests/trace-experience-001/userfiles/training_packet_v1'
    packet.mkdir(exist_ok=False)
    manifest = repo/'fixed-claude-stratified-80-seed20260814/train/items.json'
    items = json.loads(manifest.read_text())
    probes = []
    seen = set()
    for project, count in [('AC',3), ('AL',3), ('IR',2)]:
        ordered = sorted((x for x in items if x['project_code']==project),
                         key=lambda x: hashlib.sha256(('trace-experience-pilot-v1:'+x['id']).encode()).hexdigest())
        selected = []
        for item in ordered:
            if family(item) not in seen:
                selected.append(item)
                seen.add(family(item))
            if len(selected)==count:
                break
        assert len(selected)==count
        probes.extend(selected)
    probe_hashes = {x['source_sha256'] for x in probes}
    donors = [x for x in items if family(x) not in seen and x['source_sha256'] not in probe_hashes]
    source_root = Path(config['source_root'])
    records = []
    for item in donors:
        ident = item['id']
        episode = source_root/'rollout/predictions'/ident
        result = json.loads((episode/'result.json').read_text())
        runtime = json.loads((episode/'run_manifest.json').read_text())
        assert result['source_sha256']==item['source_sha256']==sha(repo/item['source_path'])
        assert not runtime.get('reference_proof_source') and not runtime.get('initial_candidate_source')
        target = packet/'traces'/ident
        target.mkdir(parents=True)
        files = {}
        names = ['codex_events.raw.jsonl','agent_events.jsonl','conversation.json',
                 'result.json','run_manifest.json','validation.json','prompt.txt',
                 'target_user_prompt.txt','workspace/input.rs','workspace/SKILL.md',
                 'workspace/candidate.rs']
        names += [str(x.relative_to(episode)) for x in sorted((episode/'snapshots').rglob('*')) if x.is_file()]
        for name in names:
            source = episode/name
            if not source.is_file():
                continue
            destination = target/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source,destination)
            files[name] = sha(source)
        records.append({'id':ident,'task_id':item['task_id'],'family':family(item),
                        'source_sha256':item['source_sha256'],'files':files,
                        'proof_solved':result['proof_solved'],'timed_out':result['timed_out'],
                        'provider_valid':result['provider_valid'],'collection_timeout_seconds':runtime['timeout_seconds'],
                        'collection_model':runtime['model'],'collection_reasoning_effort':runtime['reasoning_effort'],
                        'usage':result['usage']})
    safe = lambda x: {k:x[k] for k in ('id','task_id','project_code','directory_group','source_sha256','source_size_bytes')}
    packet_manifest = {'version':'training-packet-v1','selection_seed':'trace-experience-pilot-v1',
        'selection':'SHA256 rank within AC/AL/IR; 3/3/2 probes, one per structural family; no outcomes inspected for selection',
        'family_rule':'module path excluding function for AC/IR; first name component for AL',
        'train_manifest_sha256':sha(manifest),'probes':[{**safe(x),'family':family(x)} for x in probes],
        'donors':records,'excluded_other_train_ids':[x['id'] for x in items if x not in probes and x not in donors],
        'collection_caveat':'Historical 1800s initial-policy traces; includes collection prompt. No learned cards or augmented episodes supplied. Success-biased collection may limit inference.',
        'ancestry_caveat':'Exact hashes and conservative module/name families excluded. No comprehensive semantic dependency/clone graph is available; this is development evidence, not certified unseen generalization.',
        'validation_or_test_traces_supplied':False,'source_outcomes':dict(Counter(str(x['proof_solved']) for x in records))}
    write(packet/'manifest.json',packet_manifest)
    backend = root/'backend'
    backend.mkdir(exist_ok=False)
    private = {'config':config,'probes':probes,'packet_manifest_sha256':sha(packet/'manifest.json'),
               'phase_limit_usd':20.0,'actor_episode_limit':34,'analyzer_call_limit':4,
               'analyzer_input_byte_limit':400000,'analyzer_output_limit':32768}
    write(backend/'runtime.json',private)
    for item in probes:
        source = repo/item['source_path']
        assert sha(source)==item['source_sha256']
        target = backend/'inputs'/item['directory_group']/'unverified'/source.name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    print(json.dumps({'packet':str(packet),'packet_manifest_sha256':sha(packet/'manifest.json'),
                      'probes':len(probes),'donors':len(donors),'source_outcomes':packet_manifest['source_outcomes']}))


if __name__=='__main__':
    main()
