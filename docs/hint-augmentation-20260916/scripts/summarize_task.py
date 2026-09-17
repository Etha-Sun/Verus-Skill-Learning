"""Export evidence and token-aligned hint-only plot; semantic audit remains explicit."""
import sys,json,hashlib,importlib.util,math,re,difflib
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import ConnectionPatch
from matplotlib.ticker import FuncFormatter,MaxNLocator
R=Path(sys.argv[1]);C=json.loads((R/'config.json').read_text());S=json.loads((R/'selection.json').read_text());O=R/'analysis';O.mkdir(exist_ok=True)
REPO=Path(__file__).resolve().parents[3];sys.path.insert(0,str(REPO/'src'))
from verus_self_evolve.trajectory_progress import patch_f1_scores
ext=REPO/'scripts/audit_trajectory_progress.py';assert hashlib.sha256(ext.read_bytes()).hexdigest()==S['extractor_sha256']
sp=importlib.util.spec_from_file_location('frozen',ext);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def read(p):return json.loads(p.read_text())
def jsonl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def time(t):return datetime.fromisoformat(t.replace('Z','+00:00'))
def calls_for(path,key):
 calls=[x for x in jsonl(path) if x['task_id']==key]
 assert calls
 for c in calls:
  assert c.get('finished_at_utc') and all(a.get('usage') is not None for a in c['attempts'])
  c['tokens']=sum(a['usage'].get('completion_tokens',0) for a in c['attempts'])
 return calls

def count(calls,t):return sum(c['tokens'] for c in calls if time(c['finished_at_utc'])<=time(t))
def tier(e):
 d=e['data'];it=d.get('raw_codex_event',{}).get('item',{});txt=it.get('aggregated_output','') or d.get('stdout','')+'\n'+d.get('stderr','')
 match=re.search(r'verification results::\s*(\d+) verified,\s*(\d+) errors',txt)
 return 0 if not match else 2 if int(match[2])==0 and it.get('exit_code',d.get('returncode',0))==0 else 1
origin=Path(C['original_run']);original=m._load_run(origin);B=original['baseline'];F=original['terminal'];events={x['event_index']:x for x in jsonl(origin/'agent_events.jsonl')}
key=read(origin/'run_manifest.json')['bridge']['task_key'];calls=calls_for(origin.parents[4]/'bridge_calls.jsonl',key)
history=[dict(event=x['event_index'],sha=x['candidate_sha256'],tokens=count(calls,events[x['event_index']]['timestamp']),score=patch_f1_scores(B,x['source'],F)['patch_f1'],tier=tier(events[x['event_index']])) for x in original['checkpoints'] if x['event_index'] is not None]
records=[];sections=[];total_pass=0
for start in S['checkpoints']:
 n=start['ordinal'];run=R/'runs'/C['task_id']/f'CP{n:02}';hintdir=R/'hint-private'/C['task_id']/f'CP{n:02}'
 if not (run/'result.json').exists():continue
 result=read(run/'result.json');data=m._load_run(run);es=jsonl(run/'agent_events.jsonl');ev={e['event_index']:e for e in es};hint=read(hintdir/'hint.json');usage=read(hintdir/'usage.json')['usage']
 assert read(run/'continuation_contract.json')['checkpoint_sha256']==start['checkpoint_sha256']==hint['checkpoint_sha256']
 cc=calls_for(R/'actor_bridge_calls.jsonl',f'hint-v1-cp{n}-{C["task_id"]}');tot=sum(c['tokens'] for c in cc)
 h=[x for x in history if x['event']<=start['event_index']];prefix=h[-1]['tokens'];assert h[-1]['sha']==start['checkpoint_sha256']
 scores=[]
 for x in data['checkpoints']:
  e=x['event_index'];tok=count(cc,ev[e]['timestamp']) if e is not None else tot
  scores.append(dict(event=e,tokens=prefix+tok,score=patch_f1_scores(B,x['source'],F)['patch_f1'],tier=tier(ev[e]) if e is not None else 2 if result['validation']['verus']['passed'] else 0))
 passed=all(result['validation'][k]['passed'] for k in ['verus','lynette']);total_pass+=passed
 records.append(dict(cp=n,history=h,prefix=prefix,scores=scores,actor_output_tokens=tot,hint_usage=usage,passed=passed,total_path_output_tokens=prefix+tot))
 orig=next(x for x in original['checkpoints'] if x['candidate_sha256']==start['checkpoint_sha256'])
 detail=[f'# CP{n}: recorded process evidence\n'];changes=[];last=None
 for e in es:
  d=e.get('data',{});raw=d.get('raw_codex_event',{});it=raw.get('item',{})
  if e['actor']=='codex' and raw.get('type')=='item.completed':
   detail.append(f"## Event {e['event_index']}: {it.get('type')}\n\n"+('```json\n'+json.dumps(it,ensure_ascii=False,indent=2)+'\n```'))
  if d.get('snapshot'):
   digest=e['candidate_sha256']
   if last is not None and digest!=last:
    diff=(run/d['diff']).read_text();changes.append((e['event_index'],diff));detail.append(f"## Event {e['event_index']}: actual source change\n```diff\n{diff}\n```")
   last=digest
 (O/f'CP{n:02}_PROCESS.md').write_text('\n\n'.join(detail))
 check=[e for e in es if e.get('actor')=='verus' and e.get('type')=='verifier']
 sections.append(f'''## CP{n}（原事件{start['event_index']}）

### 客观起点与原诊断

```text
{orig['verifier_output']}
```

### Hint实际判断与提示（原文）

{hint['hint_text']}

### Actor实际修改与反馈

'''+ '\n\n'.join(f'事件{i}实际修改：\n```diff\n{diff}\n```' for i,diff in changes)+f'''\n\n最终状态：{result['status']}；Verus={result['validation']['verus']['passed']}，Lynette={result['validation']['lynette']['passed']}。

**人工语义审计待完成**：须结合上述差分和[完整过程](CP{n:02}_PROCESS.md)，逐项判断提示被采纳、偏离或延迟落实的情况；自动程序不据通过率宣称hint有效或材料已审计合格。
''')
assert records,'No completed run'
(O/'hint_tokens.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False});nr=math.ceil(len(records)/2);fig=plt.figure(figsize=(16,5*nr+1.5));outer=fig.add_gridspec(nr,2,hspace=.43,wspace=.17)
for j,r in enumerate(records):
 grid=outer[j//2,j%2].subgridspec(2,1,height_ratios=[3,1],hspace=.07);ax=fig.add_subplot(grid[0]);vx=fig.add_subplot(grid[1],sharex=ax);h=r['history'];ss=r['scores'];prefix=r['prefix'];xs=[x['tokens'] for x in ss]
 for a in [ax,vx]:a.axvspan(0,prefix,color='#ddd',alpha=.4);a.axvline(prefix,color='#555',ls=':',lw=1)
 ax.plot([x['tokens'] for x in h],[100*x['score'] for x in h],color='#777',marker='.',lw=1.7)
 vx.step([x['tokens'] for x in h],[x['tier'] for x in h],where='post',color='#777');vx.plot([x['tokens'] for x in h],[x['tier'] for x in h],ls='none',marker='.',color='#777')
 ax.plot([prefix]+xs,[100*h[-1]['score']]+[100*x['score'] for x in ss],color='#8e44ad',marker='D',mfc='none',ms=6,markevery=list(range(1,len(xs)+1)),lw=1.9)
 vx.step(xs,[x['tier'] for x in ss],where='post',color='#8e44ad');vx.plot(xs,[x['tier'] for x in ss],ls='none',marker='D',mfc='none',color='#8e44ad',ms=6)
 for x in set(xs):fig.add_artist(ConnectionPatch(xyA=(x,0),coordsA=vx.get_xaxis_transform(),xyB=(x,1),coordsB=ax.get_xaxis_transform(),color='#8e44ad',alpha=.17,lw=.6,clip_on=False))
 first=next((x for x in ss if x['tier']==2),None)
 if first:fig.add_artist(ConnectionPatch(xyA=(first['tokens'],0),coordsA=vx.get_xaxis_transform(),xyB=(first['tokens'],1),coordsB=ax.get_xaxis_transform(),color='#8e44ad',ls='--',alpha=.7,lw=1.3,clip_on=False))
 ax.set_title(f"Start CP{r['cp']} | prefix {prefix:,} tokens | final dual pass: {r['passed']}");ax.set_ylim(-5,106);ax.set_yticks([0,25,50,75,100]);ax.tick_params(labelbottom=False);ax.set_ylabel('Similarity to original F\nPatch F1 (%)');ax.grid(axis='y',alpha=.16)
 vx.set_ylim(-.25,2.3);vx.set_yticks([0,1,2]);vx.set_ylabel('Verus status');vx.set_xlabel('Original prefix + actor output tokens');vx.set_xlim(0,r['total_path_output_tokens']*1.025);vx.xaxis.set_major_locator(MaxNLocator(5));vx.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x/1000:g}k' if x else '0'))
 fig.canvas.draw();assert abs(ax.transData.transform((1000,0))[0]-vx.transData.transform((1000,0))[0])<1e-6
name=S['task']['task_id'].split('__')[-1];project=S['task']['task_id'].split('__')[0]
import textwrap
fig.suptitle(f'{project}: '+ '\n'.join(textwrap.wrap(name,width=85))+f'\nGenerated Hint | {total_pass}/{len(records)} final Verus + Lynette pass',fontsize=17,fontweight='bold',y=.985)
fig.text(.5,.025,'Purple: Generated Hint vs original F. Gray: original prefix. Dashed vertical: first extracted Verus pass (not necessarily Lynette pass).\nAPI output tokens include reasoning once; hint generation/input costs are separate. Prefix is attributed, not replayed to actor.\nFrozen extractor; identical checkpoints in both panels. Patch F1 is reference similarity, not correctness or generic proof progress.',ha='center',fontsize=10,color='#555')
fig.subplots_adjust(top=.90,bottom=.11,left=.075,right=.985)
for ext in ['png','pdf','svg']:fig.savefig(O/f'hint_prefix_tokens.{ext}',dpi=160)
header=f'''# {project} Generated Hint：{name}

**自动证据整理完成；逐checkpoint人工语义审计待完成。** 原数据固定train40、step_0001；原Yuechun提取逻辑、全部非最终源码checkpoint。已完成{len(records)}条，最终双通过{total_pass}条。失败／超时不丢弃。

![Hint组紫线](hint_prefix_tokens.png)

横轴原前缀＋actor输出token；提示生成成本不在轴内。上图对原F的Patch F1，下图同点同token的Verus状态（0编译失败／未解析、1证明失败、2通过）。不以相似度判断正确性，不伪造不存在的三组对照。

## 成本

| CP | actor输出token | hint输入token | hint输出token | 最终双通过 |
|---|---:|---:|---:|---|
'''
for r in records:header+=f"| {r['cp']} | {r['actor_output_tokens']} | {r['hint_usage']['prompt_tokens']} | {r['hint_usage']['completion_tokens']} | {r['passed']} |\n"
target=O/('AUTO_EVIDENCE.md' if (O/'semantic_audit.json').exists() else 'REPORT.md')
target.write_text(header+'\n'+ '\n\n'.join(sections))
print(f'{project}: exported {len(records)} processes, hint-only figures and evidence report; semantic audit pending')
