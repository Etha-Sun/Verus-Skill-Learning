from pathlib import Path
import sys,json,subprocess,datetime,os,hashlib
root=Path(sys.argv[1]);scripts=Path(__file__).parent
runner=Path(__file__).resolve().parents[3]/'skillopt-verusage/scripts/run_hint_augmentation.py'
plot=sys.executable;results=[]
def status(state,**kw):
 (root/'batch_status.json').write_text(json.dumps(dict(state=state,pid=os.getpid(),updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),results=results,**kw),indent=2)+'\n')
try:
 for version in ['v1','v2']:
  r=root/version;c=json.loads((r/'config.json').read_text());cp=json.loads((r/'selection.json').read_text())['checkpoints']
  for start in cp:
   n=start['ordinal'];status('running',version=version,checkpoint=n)
   with (r/'driver.log').open('a') as log:
    p=subprocess.run([sys.executable,str(runner),'--config',str(r/'config.json'),'run','--checkpoints',str(n)],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
   results.append(dict(version=version,cp=n,returncode=p.returncode))
   # Preserve a blocked checkpoint; other independent starts can still run.
  with (r/'analysis.log').open('a') as log:
   p=subprocess.run([plot,str(scripts/'summarize_task.py'),str(r)],stdout=log,stderr=log)
  results.append(dict(version=version,phase='summary',returncode=p.returncode))
 status('plotting')
 with (root/'comparison.log').open('a') as log:
  p=subprocess.run([plot,str(scripts/'compare_versions.py'),str(root/'v2')],stdout=log,stderr=log)
 results.append(dict(phase='comparison',returncode=p.returncode))
 for version in ['v1','v2']:
  report=root/version/'analysis/REPORT.md'
  with report.open('a') as f:f.write('\n\n本轮actor装备原始initial skill；hint全新生成。两版对比见[对比报告](../../v2/analysis/REPORT.md)和[对比图](../../v2/analysis/comparison_prefix_tokens.png)。自动证据报告完成不等于逐点语义审计完成。\n')
 status('completed_pending_semantic_audit' if all(x['returncode']==0 for x in results) else 'finished_with_blocks_or_export_errors')
except Exception as e:status('stopped_for_inspection',error=repr(e));raise
