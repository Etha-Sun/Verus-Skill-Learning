import json,sys,math,textwrap
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import ConnectionPatch
from matplotlib.ticker import FuncFormatter,MaxNLocator
root=Path(sys.argv[1]); read=lambda p:json.loads(p.read_text());c=read(root/'config.json');out=root/'analysis';new=read(out/'hint_tokens.json');v1=Path(c['v1_root'])
styles={'full_reference':('Full F','#22875b','^',9),'pruned_reference':('Pruned F','#337ab7','o',7),'no_reference':('No F','#d77c21','s',4),'generated_hint':('Initial skill + Hint v1','#8e44ad','D',6),'hint_v2':('Initial skill + Hint v2','#c0392b','P',7)}
if c['project']=='IR' and not c.get('comparison_two_hint_arms'): old={r['checkpoint']:r for r in read(v1/'analysis/quality-audit/four_groups_prefix_tokens.json')}
else: old={r['cp']:r for r in read(v1/'analysis/hint_tokens.json')}
rows=[]
for n in new:
 o=old[n['cp']];arms={}
 if c['project']=='IR' and not c.get('comparison_two_hint_arms'):
  assert n['prefix']==o['prefix_output_tokens']
  for k in ['full_reference','pruned_reference','no_reference','generated_hint']:
   a=o['arms'][k];arms[k]={'passed':a['passed'],'actor_output_tokens':a['total_output_tokens'],'scores':[{'tokens':s['total_path_output_tokens'],'score':s['original_F'],'tier':s['verifier_tier']} for s in a['scores']]}
 else:
  assert n['prefix']==o['prefix'] and n['history']==o['history']
  arms['generated_hint']=o
 arms['hint_v2']=n;rows.append(dict(cp=n['cp'],prefix=n['prefix'],history=n['history'],arms=arms))
(out/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
nr=math.ceil(len(rows)/2);fig=plt.figure(figsize=(17,5.1*nr+1.6));grid=fig.add_gridspec(nr,2,hspace=.44,wspace=.18)
for i,r in enumerate(rows):
 g=grid[i//2,i%2].subgridspec(2,1,height_ratios=[3,1],hspace=.06);ax=fig.add_subplot(g[0]);vx=fig.add_subplot(g[1],sharex=ax);h=r['history'];p=r['prefix'];end=p
 for a in [ax,vx]:a.axvspan(0,p,color='#ddd',alpha=.4);a.axvline(p,color='#666',ls=':',lw=1)
 ax.plot([x['tokens'] for x in h],[100*x['score'] for x in h],color='#888',marker='.',lw=1.4)
 vx.step([x['tokens'] for x in h],[x['tier'] for x in h],where='post',color='#888',lw=1.2)
 for key,a in r['arms'].items():
  label,color,marker,size=styles[key];ss=a['scores'];xs=[s['tokens'] for s in ss];end=max(end,p+a['actor_output_tokens'])
  ax.plot([p]+xs,[100*h[-1]['score']]+[100*s['score'] for s in ss],color=color,marker=marker,mfc='none',ms=size,markevery=list(range(1,len(xs)+1)),lw=1.6)
  vx.step(xs,[s['tier'] for s in ss],where='post',color=color,lw=1);vx.plot(xs,[s['tier'] for s in ss],ls='none',color=color,marker=marker,mfc='none',ms=size)
  first=next((s for s in ss if s['tier']==2),None)
  if first:fig.add_artist(ConnectionPatch(xyA=(first['tokens'],0),coordsA=vx.get_xaxis_transform(),xyB=(first['tokens'],1),coordsB=ax.get_xaxis_transform(),color=color,ls='--',lw=1,alpha=.6,clip_on=False))
 ax.set_title(f"Start CP{r['cp']} | original prefix: {p:,} output tokens");ax.set_ylim(-5,106);ax.set_yticks([0,25,50,75,100]);ax.set_ylabel('Reference-path similarity\nPatch F1 (%)');ax.tick_params(labelbottom=False);ax.grid(alpha=.15)
 vx.set_ylim(-.2,2.3);vx.set_yticks([0,1,2]);vx.set_ylabel('Verus status');vx.set_xlabel('Original prefix + continuation output tokens');vx.set_xlim(0,end*1.025);vx.xaxis.set_major_locator(MaxNLocator(5));vx.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x/1000:g}k' if x else '0'))
 fig.canvas.draw();assert abs(ax.transData.transform((1000,0))[0]-vx.transData.transform((1000,0))[0])<1e-6
keys=list(rows[0]['arms']);counts={k:sum(r['arms'][k]['passed'] for r in rows) for k in keys}
name=read(root/'selection.json')['task']['task_id'].split('__')[-1]
fig.suptitle(c['project']+': '+ '\n'.join(textwrap.wrap(name,85))+'\n'+ ' | '.join(f'{styles[k][0]}: {counts[k]}/{len(rows)} dual pass' for k in keys),fontsize=16,fontweight='bold',y=.99)
fig.legend([Line2D([],[],color=styles[k][1],marker=styles[k][2],mfc='none',label=styles[k][0]) for k in keys], [styles[k][0] for k in keys],loc='lower center',bbox_to_anchor=(.5,.062),ncol=len(keys))
fig.text(.5,.023,'All scores vs original F; similarity is not correctness. Gray: original prefix (attributed, not replayed).\nVertical dashed: first extracted Verus pass, not necessarily Lynette pass. Output tokens include reasoning once; hint costs are separate.\nBoth arms use the original initial skill and fresh hints; one sample per checkpoint, not a causal estimate.',ha='center',fontsize=9,color='#555')
fig.subplots_adjust(top=.90,bottom=.13,left=.075,right=.985)
for ext in ['png','svg','pdf']:fig.savefig(out/f'comparison_prefix_tokens.{ext}',dpi=170)
p=out/('AUTO_EVIDENCE.md' if (out/'semantic_audit.json').exists() else 'REPORT.md');body=p.read_text();body=body.replace('![Hint组紫线](hint_prefix_tokens.png)','![版本对照](comparison_prefix_tokens.png)')
intro='## 版本对照（自动统计，过程语义审计待完成）\n\n| 组别 | 最终 Verus＋Lynette 通过 | Actor 输出 token 合计 |\n|---|---:|---:|\n'
for k in keys:intro+=f"| {styles[k][0]} | {counts[k]}/{len(rows)} | {sum(r['arms'][k]['actor_output_tokens'] for r in rows):,} |\n"
intro+='\n原始最终源码：['+str(Path(c['original_run'])/'workspace/candidate.rs')+']('+str(Path(c['original_run'])/'workspace/candidate.rs')+')。\n\n图中计入原前缀归属成本；hint生成费用单列于下文，不计入actor横轴。v1/v2起点相同，均装备原initial skill并重新生成hint；单次续跑不能据此作因果提速结论。每点保留原诊断、hint原文、实际修改与完整工具事件，采纳情况仍需逐点人工审计。\n\n'
p.write_text(body.split('\n',1)[0]+'\n\n'+intro+body.split('\n',1)[1])
print('Comparison exported',c['project'],counts)
