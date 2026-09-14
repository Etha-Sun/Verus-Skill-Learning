"""Historical launcher; only local tool/input paths parameterized. See CODE.md."""
from pathlib import Path
import os,sys,json,subprocess,time,urllib.request,shlex,hashlib
REPO=Path(__file__).resolve().parents[3];OUT=Path(os.environ['AUGMENT_TASK_DIR']).resolve()
assert not OUT.is_relative_to(REPO), 'Run outputs must be outside repository'
os.environ['PYTHONPATH']=str(REPO/'skillopt-verusage/src')+':'+str(REPO/'skill-evolution-pilot/src');sys.path[:0]=os.environ['PYTHONPATH'].split(':')
os.environ['VERUS_SKILL_RUN_ROOT']=str(OUT.parent)
os.environ['CARGO_HOME']=str(Path(os.environ['RUST_ROOT'])/'cargo');os.environ['RUSTUP_HOME']=str(Path(os.environ['RUST_ROOT'])/'rustup');os.environ['PATH']=os.environ['CARGO_HOME']+'/bin:'+os.environ['PATH']
credentials={}
for line in Path(os.environ['DEEPSEEK_ENV_FILE']).read_text().splitlines():
 line=line.strip().removeprefix('export ')
 if line and not line.startswith('#') and '=' in line:
  k,v=line.split('=',1)
  if k.strip() in ['DEEPSEEK_API_KEY','DEEPSEEK_BASE_URL','DEEPSEEK_MODEL']:
   a=shlex.split(v,comments=True);credentials[k.strip()]=a[0] if a else ''
assert credentials.get('DEEPSEEK_API_KEY')
model='deepseek-v4-pro';base=credentials.get('DEEPSEEK_BASE_URL','https://api.deepseek.com').rstrip('/')
if not (OUT/'models.json').exists():(OUT/'models.json').write_bytes(Path(os.environ['MODEL_CATALOG']).read_bytes())
manifest=json.loads((OUT/'manifest.json').read_text());item=manifest['task'];source=REPO/item['source_path']
verus=Path(os.environ['VERUS_BIN'])
lynette=Path(os.environ['LYNETTE_BIN']);codex=Path(os.environ['CODEX_BIN'])
mode='all-checkpoints'
port=18129;url=f'http://127.0.0.1:{port}'
bridge_env=os.environ.copy();bridge_env['DEEPSEEK_API_KEY']=credentials['DEEPSEEK_API_KEY']
cmd=[sys.executable,'-m','skillopt_verusage.codex_deepseek_bridge','--native-responses','--model',model,'--port',str(port),'--upstream-base-url',base,'--expected-upstream-model',model,'--request-timeout-seconds','540','--ledger-path',str(OUT/'bridge_calls.jsonl'),'--manifest-path',str(OUT/'bridge_manifest.json'),'--model-catalog-path',str(OUT/'models.json')]
log=(OUT/f'bridge-{mode}.log').open('w');bridge=subprocess.Popen(cmd,env=bridge_env,stdout=log,stderr=log)
try:
 for n in range(30):
  if bridge.poll() is not None:raise RuntimeError('bridge exited')
  try:urllib.request.urlopen(url+'/health',timeout=1).read();break
  except Exception:time.sleep(1)
 else:raise RuntimeError('bridge not ready')
 for k in list(os.environ):
  if k.endswith('API_KEY'):os.environ.pop(k)
 os.environ['SKILLOPT_CODEX_BRIDGE_TOKEN']='local-bridge-only'
 from skillopt_verusage.codex_flash_runner import run_task
 results=[]
 for checkpoint in manifest['checkpoints']:
  if not checkpoint['continue']:
   continue
  ordinal=checkpoint['ordinal'];runout=OUT/f'continuation_{ordinal:02d}'
  if (runout/'result.json').exists():
   results.append(json.loads((runout/'result.json').read_text()))
   print('already completed',ordinal,flush=True)
   continue
  assert not runout.exists(), 'Partial run exists; inspect before retry'
  print('starting checkpoint',ordinal,'event',checkpoint['event_index'],flush=True)
  result=run_task(item_id=item['id'],source=source,expected_source_sha256=item['source_sha256'],directory_group=item['directory_group'],out_dir=runout,skill_file=REPO/'skillopt-verusage/skills/blank.md',codex_bin=codex,verus_bin=verus,lynette_bin=lynette,bridge_url=url,bridge_ledger_path=OUT/'bridge_calls.jsonl',bridge_manifest_path=OUT/'bridge_manifest.json',bridge_task_key='augmentation-no-reference-cp'+str(ordinal)+'-'+item['id'],model=model,reasoning_effort='high',timeout_seconds=600,model_context_window=1048576,actor_contract_profile='project',condition_skill_present=False,initial_candidate_source=OUT/checkpoint['source_file'],reference_proof_source=None,continuation_instructions=(OUT/'continuation_instructions.txt').read_text(),reference_kind='none')
  results.append(result)
  print('completed checkpoint',ordinal,result.get('status'),flush=True)
  manifest['status']='running';manifest['completed_checkpoints']=len(results)
  (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 manifest['status']='completed';(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

finally:
 bridge.terminate()
 try:bridge.wait(timeout=10)
 except subprocess.TimeoutExpired:bridge.kill();bridge.wait()
 log.close()
