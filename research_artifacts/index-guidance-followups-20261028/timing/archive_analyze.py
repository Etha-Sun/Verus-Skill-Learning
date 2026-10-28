"""Read-only timing analysis for two independent four-task comparisons."""
from pathlib import Path
from datetime import datetime
import collections,csv,hashlib,json,re,shlex,statistics
ROOT=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
TASKS={'a23a4969155913255f76':'Rely','9b9f6ccef89db4103c7f':'Unpack','aded79905be896942897':'De Morgan','62ff0a3cf2c458b36ac8':'Filter'}
CONFIGS=[('index_v2','index-matching-20261024-run16-v1','I0_old_index','I2_matching_v2',2),('main_G1','obligation-guidance-20261024-run24-v1','G0_original_main','G1_obligation_main',3)]
def extract(cells):
 rows=[];command_rows=[];source_hashes={};unmatched=[];excluded=collections.Counter()
 def seconds(s):return datetime.fromisoformat(s).timestamp()
 def inner(command):
  try:
   parts=shlex.split(command)
   for switch in ['-lc','-c']:
    if switch in parts:return parts[parts.index(switch)+1]
  except ValueError:pass
  return command
 # Find invocations at shell command boundaries, not filenames passed to cat/grep.
 invoke=re.compile(r"""(?:^|[;&|\n])\s*(?:timeout\s+\d+\s+)?["']?(?:[^\s"';&|]+/)?(?:run_verus\.sh|verus-env|verus)["']?(?=\s|$)""")
 for cell in cells:
  ep=Path(cell['episode']);rp=ep/'result.json';events_path=ep/'agent_events.jsonl';result=json.loads(rp.read_text())
  for p in [rp,events_path]:source_hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
  events=[json.loads(l) for l in events_path.read_text().splitlines()];start={};end={};host=[]
  for n,e in enumerate(events,1):
   data=e.get('data',{});raw=data.get('raw_codex_event',{});item=raw.get('item',{})
   if e.get('actor')=='verus' and e.get('type')=='verifier' and 'wall_seconds' in data:host.append(data)
   if e.get('actor')!='codex' or item.get('type')!='command_execution':continue
   key=item['id']
   if raw.get('type')=='item.started':start.setdefault(key,(e,n))
   if raw.get('type')=='item.completed':end.setdefault(key,(e,n))
  verus=result['validation']['verus'];assert len(host)==1 and host[0]['wall_seconds']==verus['wall_seconds']
  subtotal=0.;mixed=0.;pure=0.;ncomplete=0;nmissing=0;nmixed=0;nprobe=0
  for key,(e,lineno) in start.items():
   item=e['data']['raw_codex_event']['item'];cmd=item.get('command','');shell=inner(cmd);matches=list(invoke.finditer(shell))
   if not matches:continue
   done=end.get(key)
   if done:
    output=done[0]['data']['raw_codex_event']['item'].get('aggregated_output','')
    if output.strip().startswith('usage: ./tools/run_verus.sh'):
     excluded['invalid_wrapper_usage']+=1;continue
   if not done:
    nmissing+=1;unmatched.append({'episode':str(ep),'item':key,'command':cmd,'line':lineno});continue
   duration=seconds(done[0]['timestamp'])-seconds(e['timestamp']);assert duration>=0
   # No timestamp subtraction can isolate Verus from a mixed command.
   has_lynette=bool(re.search(r'(?:^|[;&|\n])\s*\./tools/run_lynette\.sh',shell))
   # A broader check catches the same invocation in unusual shell spellings.
   has_lynette=has_lynette or './tools/run_lynette.sh' in shell
   other=has_lynette or bool(re.search(r'(?:^|[;&|\n])\s*(?:cat|sed|ls|wc|diff|mkdir|python\d*|printf)\b',shell)) or '\n' in shell
   # Pipeline filters (tail/head/grep/etc.) and shell startup remain overhead even in ordinary calls.
   probe=bool(re.search(r'\b(?:scratch|probe\d*)\.rs\b',shell))
   row={'episode':str(ep),'task':cell['task'],'arm':cell['arm'],'repeat':cell['repeat'],'item_id':key,'start_line':lineno,'end_line':done[1],'command':cmd,'command_wall_seconds':duration,'mixed_command':other,'includes_lynette':has_lynette,'scratch_probe':probe,'visible_invocations':len(matches),'exit_code':done[0]['data']['raw_codex_event']['item'].get('exit_code')}
   command_rows.append(row);subtotal+=duration;ncomplete+=1;nprobe+=probe
   if other:mixed+=duration;nmixed+=1
   else:pure+=duration
  # Detect completed invocation records missing a start, instead of silently treating them as zero.
  for key,(e,n) in end.items():
   if key not in start and invoke.search(inner(e['data']['raw_codex_event']['item'].get('command',''))):
    nmissing+=1;unmatched.append({'episode':str(ep),'item':key,'line':n,'reason':'missing_start'})
  r={k:cell[k] for k in ['task','arm','repeat','dual_pass','body_read','bulk_body_read','episode']}
  r.update(wall_seconds=result['wall_seconds'],actor_seconds=result['actor_wall_seconds'],final_verus_seconds=verus['wall_seconds'],final_verus_passed=verus['passed'],final_verus_returncode=verus['returncode'],final_verus_timed_out=verus['timed_out'],completed_verus_commands=ncomplete,mixed_commands=nmixed,probe_commands=nprobe,unmatched_commands=nmissing,ordinary_command_seconds=pure,mixed_command_seconds=mixed,cumulative_command_proxy_seconds=subtotal+verus['wall_seconds'],host_lynette_seconds=result['validation']['lynette']['wall_seconds'])
  rows.append(r)
 return rows,command_rows,source_hashes,unmatched,dict(excluded)

def main():
 batches=[];allcells=[];allcommands=[];alltasks=[];hashes={}
 for name,run,control,modified,repeats in CONFIGS:
  rp=ROOT/run/'report.json';ap=ROOT/run/'final-review/analysis.json'
  report=json.loads(rp.read_text());audit=json.loads(ap.read_text());amap={r['episode']:r for r in audit['rows']}
  for p in [rp,ap]:hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
  assert report['planned']==report['completed']==len(report['rows'])==2*4*repeats
  cells=[]
  for r in report['rows']:
   a=amap[r['episode']];assert a['primary_same_hash_dual_600']==r['primary_same_hash_dual_600']
   ep=Path(r['episode']);dp=ep/'deadline_dual_audit.json';deadline=json.loads(dp.read_text());hashes[str(dp)]=hashlib.sha256(dp.read_bytes()).hexdigest()
   assert deadline['observed_dual_within_deadline']==r['primary_same_hash_dual_600']
   cells.append({'task':TASKS[r['task_id']],'arm':r['condition'],'repeat':r['repeat']+1,'dual_pass':r['primary_same_hash_dual_600'],'body_read':bool(a.get('all_body_returns',a['helper_body_reads'])),'bulk_body_read':bool(a.get('direct_body_returns',0)),'episode':r['episode']})
  assert len({(c['task'],c['arm'],c['repeat']) for c in cells})==len(cells)
  rows,commands,h,unmatched,excluded=extract(cells);hashes.update(h)
  for r in rows:
   orig=next(x for x in report['rows'] if x['episode']==r['episode']);assert abs(orig['actor_seconds']-r['actor_seconds'])<1e-8
  metrics=['wall_seconds','final_verus_seconds','cumulative_command_proxy_seconds']
  per_task=[]
  for task in TASKS.values():
   baseline=[r for r in rows if r['task']==task and r['arm']==control];changed=[r for r in rows if r['task']==task and r['arm']==modified]
   assert len(baseline)==len(changed)==repeats
   for metric in metrics:
    b=statistics.mean(r[metric] for r in baseline);m=statistics.mean(r[metric] for r in changed)
    per_task.append({'batch':name,'task':task,'metric':metric,'baseline_mean_seconds':b,'modified_mean_seconds':m,'modified_over_baseline':m/b,'baseline_passes':sum(r['dual_pass'] for r in baseline),'modified_passes':sum(r['dual_pass'] for r in changed),'repeats':repeats})
  ratios={metric:statistics.mean(r['modified_over_baseline'] for r in per_task if r['metric']==metric) for metric in metrics}
  summary={}
  for arm in [control,modified]:
   rs=[r for r in rows if r['arm']==arm]
   summary[arm]={'runs':len(rs),'passes':sum(r['dual_pass'] for r in rs),**{metric:statistics.mean(r[metric] for r in rs) for metric in metrics},'completed_actor_verus_commands':sum(r['completed_verus_commands'] for r in rs),'mixed_commands':sum(r['mixed_commands'] for r in rs),'mixed_command_seconds':sum(r['mixed_command_seconds'] for r in rs)}
  for r in rows:r['batch']=name
  for r in commands:r['batch']=name
  batches.append({'name':name,'source_run':run,'control':control,'modified':modified,'repeats':repeats,'summary':summary,'mean_per_task_ratios':ratios,'unmatched':unmatched,'excluded':excluded})
  allcells+=rows;allcommands+=commands;alltasks+=per_task
 data={'definition':'For each task, average all repeats including failures; compute modified/control; arithmetic-mean the four task ratios. Lower is better.','metrics':{'wall_seconds':'result.wall_seconds, episode start to actor exit/timeout and final host checks','final_verus_seconds':'One separately timed host check of the last candidate; process startup/front end/SMT included; generation and Lynette excluded; pure SMT time unavailable','cumulative_command_proxy_seconds':'Completed actor Verus-command windows plus final host Verus time; includes failures/probes, shell/output overhead and mixed-command ancillary work. Not isolated solver time.'},'batches':batches,'per_task':alltasks,'rows':allcells,'commands':allcommands,'source_hashes':hashes,'checks':{'episodes':len(allcells),'unique_episodes':len({r['episode'] for r in allcells}),'final_host_event_times_match':True,'historical_outcomes_unchanged':True,'raw_data_changed':False,'new_api_or_prover_calls':0}}
 for p,digest in hashes.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest
 (OUT/'analysis.json').write_text(json.dumps(data,indent=2)+'\n')
 for fname,rs in [('cells.csv',allcells),('commands.csv',allcommands),('per-task.csv',alltasks)]:
  with (OUT/fname).open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
 print(json.dumps(batches,indent=2))
if __name__=='__main__':main()
