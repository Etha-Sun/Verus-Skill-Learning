"""Token-aligned display; leaves the frozen checkpoint extractor and scores unchanged."""
from pathlib import Path
from datetime import datetime
import json, csv, re, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
from matplotlib.patches import ConnectionPatch
O=Path(os.environ['AUGMENT_RUN_ROOT']).resolve()/'research-summary'
assert not O.is_relative_to(Path(__file__).resolve().parents[3])
records=json.loads((O/'three_groups.json').read_text())
ARMS=[('full_reference','#22875b','^','Full F',12),('pruned_reference','#337ab7','o','Pruned F',8),('no_reference','#d77c21','s','No F',4)]
def time(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def tier(e):
 d=e['data'];item=d.get('raw_codex_event',{}).get('item',{})
 out=item.get('aggregated_output','') or (d.get('stdout','')+'\n'+d.get('stderr',''))
 m=re.search(r'verification results::\s*(\d+) verified,\s*(\d+) errors',out)
 if m:return 2 if int(m[2])==0 and item.get('exit_code',d.get('returncode',0))==0 else 1
 return 0
flat=[];summary=[]
for r in records:
 for arm,v in r['arms'].items():
  p=Path(v['path']);key=json.loads((p/'run_manifest.json').read_text())['bridge']['task_key']
  calls=[json.loads(l) for l in (p.parent/'bridge_calls.jsonl').read_text().splitlines()];calls=[c for c in calls if c['task_id']==key]
  assert calls
  for c in calls:
   assert c.get('finished_at_utc') and all(a.get('usage') is not None for a in c['attempts'])
   c['tokens']=sum(a['usage'].get('completion_tokens',0) for a in c['attempts'])
  calls.sort(key=lambda c:time(c['finished_at_utc']))
  total=sum(c['tokens'] for c in calls)
  events=[json.loads(l) for l in (p/'agent_events.jsonl').read_text().splitlines()];byid={e['event_index']:e for e in events}
  def count(t):return sum(c['tokens'] for c in calls if time(c['finished_at_utc'])<=time(t))
  for s in v['scores']:
   s['output_tokens']=count(byid[s['event']]['timestamp']) if s['event'] is not None else total
   s['verifier_tier']=tier(byid[s['event']]) if s['event'] is not None else (2 if v['passed'] else 0)
   flat.append(s.copy())
  assert all(a['output_tokens']<=b['output_tokens'] for a,b in zip(v['scores'],v['scores'][1:]))
  states=[{'event':e['event_index'],'output_tokens':count(e['timestamp']),'tier':tier(e),'sha':e.get('candidate_sha256')} for e in events if e.get('actor')=='verus' and e.get('type')=='verifier']
  assert states and states[-1]['tier']==2
  first=next(s for s in states if s['tier']==2)
  v['checkpoint_states']=[{'event':s['event'],'output_tokens':s['output_tokens'],'tier':s['verifier_tier']} for s in v['scores']]
  assert [(s['event'],s['output_tokens']) for s in v['checkpoint_states']]==[(s['event'],s['output_tokens']) for s in v['scores']]
  v['verifier_states']=states;v['total_output_tokens']=total;v['first_verified_tokens']=first['output_tokens']
  summary.append({'project':r['project'],'start_checkpoint':r['checkpoint'],'arm':arm,'total_output_tokens':total,'first_verified_output_tokens':first['output_tokens'],'output_tokens_after_first_verified':total-first['output_tokens'],'verifier_events':len(states),'extracted_checkpoints':len(v['scores'])})
(O/'three_groups_tokens.json').write_text(json.dumps(records,indent=2)+'\n')
for name,data in [('three_groups_token_scores.csv',flat),('three_groups_token_summary.csv',summary)]:
 with (O/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
for both in [False,True]:
 fig=plt.figure(figsize=(16,19));outer=fig.add_gridspec(4,2,hspace=.43,wspace=.16)
 for j,r in enumerate(records):
  grid=outer[j//2,j%2].subgridspec(2,1,height_ratios=[3,1],hspace=.08)
  ax=fig.add_subplot(grid[0]);vx=fig.add_subplot(grid[1],sharex=ax)
  for arm,col,mark,label,size in ARMS:
   v=r['arms'][arm];ss=v['scores'];xs=[s['output_tokens'] for s in ss]
   style=dict(color=col,marker=mark,ms=size,mfc=col if arm=='no_reference' else 'none',mew=1.5)
   ax.plot(xs,[100*s['original_F'] for s in ss],lw=1.8,**style)
   if both:ax.plot(xs,[100*s['own_final'] for s in ss],lw=1.6,ls='--',**style)
   st=v['checkpoint_states'];vx.step([s['output_tokens'] for s in st],[s['tier'] for s in st],where='post',lw=1.3,color=col,alpha=.8)
   vx.plot([s['output_tokens'] for s in st],[s['tier'] for s in st],ls='none',**style)
   # A single artist spans both axes and their gap at the identical data x.
   for x in sorted(set(xs)):
    guide=ConnectionPatch(xyA=(x,0),coordsA=vx.get_xaxis_transform(),xyB=(x,1),coordsB=ax.get_xaxis_transform(),color=col,lw=.65,alpha=.18,zorder=0,clip_on=False)
    fig.add_artist(guide)
   passed=[s for s in st if s['tier']==2]
   if passed:
    first_x=passed[0]['output_tokens']
    guide=ConnectionPatch(xyA=(first_x,0),coordsA=vx.get_xaxis_transform(),xyB=(first_x,1),coordsB=ax.get_xaxis_transform(),color=col,lw=1.35,ls=(0,(4,3)),alpha=.75,zorder=1,clip_on=False)
    fig.add_artist(guide)
  ax.set_ylim(-4,106);ax.set_yticks([0,25,50,75,100]);ax.tick_params(labelbottom=False);ax.grid(alpha=.16)
  if j%2==0:ax.set_ylabel('Reference-path similarity\nPatch F1 (%)')
  task='set_map_union' if r['project']=='IR' else 'tla_exists_and_equality'
  ax.set_title(f"{r['project']} {task} | start CP{r['checkpoint']} | all 3 pass",fontsize=11)
  vx.set_ylim(-.25,2.35);vx.set_yticks([0,1,2]);vx.set_ylabel('Verus tier');vx.grid(alpha=.16)
  vx.set_xlim(0,max(v['total_output_tokens'] for v in r['arms'].values())*1.04)
  vx.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x/1000:g}k' if x else '0'))
  vx.set_xlabel('Cumulative output tokens within each continuation')
 fig.suptitle('Three-arm checkpoint continuation: token cost and reference-path similarity\nIR: 1 task / 6 starts; AL: 1 task / 2 starts; AC: 0 | 24/24 Verus + Lynette pass',fontsize=16,fontweight='bold',y=.99)
 handles=[Line2D([0],[0],color=c,marker=m,mfc=c if a=='no_reference' else 'none',ms=s,label=l) for a,c,m,l,s in ARMS]
 handles+=[Line2D([0],[0],color='#555',label='Solid: vs original F')]
 if both:handles+=[Line2D([0],[0],color='#555',ls='--',label="Dashed: vs own final F-prime (post hoc)")]
 handles+=[Line2D([0],[0],color='#555',ls='--',lw=1.35,label='Vertical dashed: first passing checkpoint')]
 fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.047),ncol=3,frameon=False)
 fig.text(.5,.014,'Tokens: API completion_tokens summed over completed calls (reasoning included, not added twice); original-prefix/input tokens excluded.\nTop and bottom: IDENTICAL extracted checkpoints and token coordinates; vertical guides align each pair of points.\nTier 0 = compile failure or unparsed; 1 = proof failure; 2 = verified. Vertical dashed lines mark first passing checkpoints; a starting state may already pass.\nFull F and no-F IR isolated; pruned F and no-F AL not isolated. No stagnation claim; own-endpoint 100% is by construction.',ha='center',fontsize=9,color='#555')
 fig.subplots_adjust(top=.94,bottom=.12,left=.07,right=.985)
 # Verify actual rendered pixel x coordinates, not only data equality.
 fig.canvas.draw()
 for k in range(0,len(fig.axes),2):
  upper,lower=fig.axes[k:k+2]
  for x in [0,upper.get_xlim()[1]]:
   assert abs(upper.transData.transform((x,0))[0]-lower.transData.transform((x,0))[0])<1e-6
 name='three_groups_tokens_curves' if both else 'three_groups_tokens_original_F'
 for ext in ['png','svg','pdf']:fig.savefig(O/f'{name}.{ext}',dpi=160)
 plt.close(fig)
print('24 continuations aligned to API ledger; two token figures and audit CSVs written.')
