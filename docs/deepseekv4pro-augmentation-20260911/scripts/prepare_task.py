"""Stage the reviewed eight starts; optionally verify extraction on original data."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, sys
p=argparse.ArgumentParser()
p.add_argument('--project', choices=['IR','AL'], required=True)
p.add_argument('--arm', choices=['full_reference','pruned_reference','no_reference'], required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--source-run', type=Path)
a=p.parse_args()
D=Path(__file__).resolve().parents[1];repo=D.parents[1]
out=a.out.resolve()
if out.is_relative_to(repo):p.error('output must be outside repository')
task=json.loads((D/'tasks.json').read_text())[a.project]
extractor=repo/'scripts/audit_trajectory_progress.py'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(extractor)==task['extractor_sha256']
if a.source_run:
 sys.path.insert(0,str(repo/'src'))
 spec=importlib.util.spec_from_file_location('frozen_audit',extractor)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 run=module._load_run(a.source_run)
 assert run is not None
 final_sha=sha(a.source_run/'workspace/candidate.rs')
 actual=[(c['event_index'],c['candidate_sha256']) for c in run['checkpoints'] if c['candidate_sha256']!=final_sha]
 expected=[(c['event_index'],c['candidate_sha256']) for c in task['checkpoints']]
 assert actual==expected, 'original extraction differs from published checkpoint contract'
assert sha(repo/task['source_path'])==task['source_sha256']
out.mkdir(parents=True,exist_ok=False)
checkpoints=[]
for c in task['checkpoints']:
 source=D/c['source_file'];assert sha(source)==c['candidate_sha256']
 name=source.name;shutil.copyfile(source,out/name)
 checkpoints.append({**c,'source_file':name})
proofdir=D/'proofs'/a.project
for name in ['original_input.rs','original_final.rs','pruned_final.rs']:
 shutil.copyfile(proofdir/name,out/name)
shutil.copyfile(D/'protocols'/f'{a.arm}_{a.project}.txt',out/'continuation_instructions.txt')
manifest={'task':{k:v for k,v in task.items() if k not in ['checkpoints','extractor_sha256']},'checkpoints':checkpoints,'extractor_sha256':task['extractor_sha256'],'offline_reference_dir':str(proofdir),'status':'prepared'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Prepared {len(checkpoints)} starts for {a.project} / {a.arm}; no API calls.')
