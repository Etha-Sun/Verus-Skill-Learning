from pathlib import Path
import sys,json,hashlib,importlib.util,csv,os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(os.environ['AUGMENT_RUN_ROOT']).resolve();O=ROOT/'research-summary';O.mkdir(exist_ok=True);REPO=Path(__file__).resolve().parents[3]
assert not ROOT.is_relative_to(REPO)
sys.path.insert(0,str(REPO/'src'))
from verus_self_evolve.trajectory_progress import patch_f1_scores
p=REPO/'scripts/audit_trajectory_progress.py'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='642f76ab5774df0685f1268cccf49802cee9ef1f9649c012ea38dae45331ab0e'
sp=importlib.util.spec_from_file_location('audit',p);a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
rows=[];records=[]
for project,tid,count,no_group in [('IR','3a77a3e4e72edf600e2a',6,'no-reference-isolated-v2'),('AL','6fc5661ffaeee1c57342',2,'no-reference-control-v1')]:
 ref=ROOT/'alternative-path-tasks-v1'/tid;no=ROOT/no_group/tid
 B=(ref/'original_input.rs').read_text();F=(ref/'original_final.rs').read_text()
 for n in range(1,count+1):
  pair={'project':project,'task_id':tid,'checkpoint':n,'arms':{}}
  for arm,parent in [('pruned_reference',ref),('no_reference',no),('full_reference',ROOT/'full-reference-two-task-v1'/tid)]:
   d=parent/f'continuation_{n:02d}';contract=json.loads((d/'continuation_contract.json').read_text());rr=a._load_run(d);end=(d/'workspace/candidate.rs').read_text();result=json.loads((d/'result.json').read_text())
   scores=[]
   for i,c in enumerate(rr['checkpoints']):
    q={'project':project,'task_id':tid,'origin_checkpoint':n,'arm':arm,'index':i,'event':c['event_index'],'original_F':patch_f1_scores(B,c['source'],F)['patch_f1'],'own_final':patch_f1_scores(B,c['source'],end)['patch_f1']};scores.append(q);rows.append(q)
   pair['arms'][arm]={'path':str(d),'initial_sha':contract['checkpoint_sha256'],'isolation':json.loads((d/'run_manifest.json').read_text())['actor_isolation']['requested'],'passed':result['validation']['verus']['passed'] and result['validation']['lynette']['passed'],'scores':scores}
  assert len({x['initial_sha'] for x in pair['arms'].values()})==1
  full_contract=json.loads((Path(pair['arms']['full_reference']['path'])/'continuation_contract.json').read_text())
  assert full_contract['reference_sha256']==hashlib.sha256(F.encode()).hexdigest()
  assert all(x['passed'] for x in pair['arms'].values())
  records.append(pair)
(O/'three_groups.json').write_text(json.dumps(records,indent=2)+'\n')
with (O/'three_groups_scores.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
for mode in ['both','original_only']:
 fig,axes=plt.subplots(4,2,figsize=(14,13),sharey=True)
 for ax,r in zip(axes.flat,records):
  for arm,color,marker,label in [('pruned_reference','#337ab7','o','Pruned-F given'),('no_reference','#d77c21','s','No F given'),('full_reference','#22875b','^','Full-F given')]:
   ss=r['arms'][arm]['scores'];xs=[x['index'] for x in ss]
   ax.plot(xs,[x['original_F'] for x in ss],color=color,marker=marker,lw=2,ms={'pruned_reference':9,'no_reference':4,'full_reference':14}[arm],mfc=color if arm=='no_reference' else 'none',mew=1.6,zorder=5,label=label+' | vs original F')
   if mode=='both':ax.plot(xs,[x['own_final'] for x in ss],color=color,marker=marker,ls='--',lw=1.6,ms={'pruned_reference':9,'no_reference':4,'full_reference':14}[arm],mfc=color if arm=='no_reference' else 'none',mew=1.6,zorder=6,label=label+' | vs own final (post hoc)')
  if (r['project'],r['checkpoint'])==('AL',2):
   ax.text(.03,.13,'All three groups overlap exactly.\nOpen circles / triangles + filled squares mark the same values.',transform=ax.transAxes,fontsize=9,color='#333333')
  if (r['project'],r['checkpoint'])==('IR',6):
   ax.text(.03,.13,'Blue / green end at index 1; orange ends at index 2.'+('\nWithin every group, solid and dashed lines coincide.' if mode=='both' else ''),transform=ax.transAxes,fontsize=9,color='#333333')
  length=max(len(x['scores']) for x in r['arms'].values());ax.set_xticks(range(length));ax.set_ylim(-.05,1.07);ax.grid(alpha=.16)
  task='set_map_union' if r['project']=='IR' else 'tla_exists_and_equality'
  ax.set_title(f"{r['project']} {task} | start CP{r['checkpoint']} | all 3 pass")
  ax.set_xlabel('Extracted checkpoint index within each continuation')
 for ax in axes[:,0]:ax.set_ylabel('Patch F1')
 fig.suptitle('Three arms: full F vs pruned F vs no reference\nIR: 1 task / 6 runs; AL: 1 task / 2 runs; AC: 0 (per group)',fontsize=16,fontweight='bold')
 h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc='lower center',bbox_to_anchor=(.5,.055),ncol=3,frameon=False)
 fig.text(.5,.018,'Same 8 starts; each arm passes 8/8. Green open triangles = full F; blue open circles = pruned F; orange squares = no F.\nFull-F and no-F IR are isolated; pruned-F and no-F AL are not. Index is not time/tokens; own-final 1 is by construction.',ha='center',fontsize=10,color='#555555')
 fig.tight_layout(rect=[0,.115,1,.93])
 name='three_groups_curves' if mode=='both' else 'three_groups_original_F'
 for ext in ['png','svg','pdf']:fig.savefig(O/f'{name}.{ext}',dpi=160)
 plt.close(fig)
print('8 matched triplets; 24/24 validator pass; figures and data written')
