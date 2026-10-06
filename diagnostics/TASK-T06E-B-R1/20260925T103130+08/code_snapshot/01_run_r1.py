from __future__ import annotations
import hashlib,json,os,sys,subprocess
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path.cwd(); RUN=Path(r'diagnostics/TASK-T06E-B-R1/20260925T103130+08'); OLD=Path(r'diagnostics/TASK-T06E-B/20260925T100306+08')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def stage(name,status,detail=''):
 with (RUN/'stage_status.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps({'time':pd.Timestamp.now(tz='Asia/Shanghai').isoformat(),'stage':name,'status':status,'detail':detail},ensure_ascii=False)+'\n')
def write(name,obj): (RUN/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
pi=json.loads((RUN/'config/profile_inputs_frozen.json').read_text(encoding='utf-8'))
jobs=[('B1','M0_B1',['E','A','B','alpha','beta']),('B6','M0_6',['E','A','B','alpha','beta']),('B6','MQ-add',['E','A','B','alpha','beta','k_add']),('B6','MQ-eff',['E','A','B','alpha','beta','eta'])]
stage('profiles_recompute','START','22 corrected physical-fixed profile tasks; no full/fold/bootstrap/B7/B8 refit')
env=os.environ.copy(); env.update({'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'})
procs=[]; logs=[]
for source,model,names in jobs:
 for name in names:
  log=(RUN/'corrected_profiles'/f'{source}__{model}__{name}.log').open('w',encoding='utf-8'); logs.append(log)
  cmd=[sys.executable,str(RUN/'code/profile_fixed_worker.py'),source,model,name]
  procs.append((source,model,name,subprocess.Popen(cmd,cwd=str(ROOT),env=env,stdout=log,stderr=subprocess.STDOUT,text=True)))
for source,model,name,proc in procs:
 rc=proc.wait()
 if rc!=0: raise SystemExit(f'CORRECTED_PROFILE_FAIL {source}:{model}:{name} rc={rc}')
for log in logs: log.close()
grid=[]; summaries=[]; ms=[]; repro=[]; statuses={}
for source,model,names in jobs:
 for name in names:
  part=json.loads((RUN/'corrected_profiles/parts'/f'{source}__{model}__{name}.json').read_text(encoding='utf-8')); rows=part['rows']; ms.extend(part['multistart']); fullval=float(part['full_value']); full_sse=float(part['SSE_min']); threshold=float(part['descriptive_threshold'])
  free_scale=(pi[source+':'+model]['params'] if False else None)
  # physical fixed-value consistency and full-point hard checks
  for r in rows:
   if r.get('skipped'): r['inside_descriptive_set']=False; r['touches_fixed_hard_boundary']=False; continue
   cond=r[name+'_conditional']; ok=abs(cond-r['fixed_value'])<=1e-12+1e-10*abs(r['fixed_value'])
   if not ok: raise SystemExit('CONDITIONAL_FIXED_MISMATCH')
   r['inside_descriptive_set']=bool(r['SSE']<=threshold)
   if name in ('E','A','B','k_add'):
    s=float(pi[source+':'+model]['Lstar']); bounds=(1e-8*s,1e3*s)
   elif name in ('alpha','beta'): bounds=(1e-4,4.0)
   else: bounds=(1e-6,50.0)
   r['touches_fixed_hard_boundary']=bool(abs(r['fixed_value']-bounds[0])<=1e-10*max(1,abs(bounds[1]-bounds[0])) or abs(r['fixed_value']-bounds[1])<=1e-10*max(1,abs(bounds[1]-bounds[0])))
  grid.extend(rows)
  frow=next((r for r in rows if not r.get('skipped') and r['fixed_value']==fullval),None)
  if frow is None: raise SystemExit('FULL_POINT_MISSING_IN_GRID')
  rpass=bool(frow['SSE']<=full_sse*(1+1e-6)+1e-12 and frow['inside_descriptive_set'] and abs(frow[name+'_conditional']-fullval)<=1e-12+1e-10*abs(fullval))
  repro.append({'source':source,'model':model,'parameter':name,'full_value':fullval,'fixed_value':frow['fixed_value'],'conditional_value':frow[name+'_conditional'],'SSE_full':full_sse,'SSE_profile_at_full_point':frow['SSE'],'ratio':frow['SSE']/full_sse,'inside_set':frow['inside_descriptive_set'],'atol_rtol_pass':bool(abs(frow[name+'_conditional']-fullval)<=1e-12+1e-10*abs(fullval)),'hard_reproduction_pass':rpass})
  if not rpass: raise SystemExit('FULL_POINT_REPRODUCTION_FAIL '+source+':'+model+':'+name)
  q=pd.DataFrame(rows); skipped=int(q.skipped.sum()); inside=q[q.inside_descriptive_set==True]; touches=bool(inside.touches_fixed_hard_boundary.any()) if len(inside) else False
  weak=bool(skipped>0 or len(inside)==0 or touches)
  summaries.append({'source':source,'model':model,'parameter':name,'SSE_min':full_sse,'descriptive_threshold':threshold,'n_grid_requested':len(rows),'n_grid_completed':int((~q.skipped).sum()),'n_skipped':skipped,'n_inside_set':len(inside),'inside_min':float(inside.fixed_value.min()) if len(inside) else None,'inside_max':float(inside.fixed_value.max()) if len(inside) else None,'touches_fixed_hard_boundary':touches,'weakly_identified':weak,'status':'WEAKLY_IDENTIFIED' if weak else 'PROFILE_FINITE_AND_SEPARATED','full_point_in_inside_set':bool(frow['inside_descriptive_set'])})
  statuses[(source,model,name)]='WEAKLY_IDENTIFIED' if weak else 'PROFILE_FINITE_AND_SEPARATED'
pd.DataFrame(grid).to_csv(RUN/'corrected_profiles/profile_grid_corrected.csv',index=False,encoding='utf-8-sig'); pd.DataFrame(summaries).to_csv(RUN/'corrected_profiles/profile_summary_corrected.csv',index=False,encoding='utf-8-sig'); pd.DataFrame(ms).to_csv(RUN/'corrected_profiles/profile_multistart_results.csv',index=False,encoding='utf-8-sig'); pd.DataFrame(repro).to_csv(RUN/'corrected_profiles/full_point_reproduction.csv',index=False,encoding='utf-8-sig')
stage('profiles_recompute','PASS',f'{len(repro)}/22 full-point production passes')
# MQ-add own G4: predictions, own boundary, own Jacobian, own multistart, own six profiles
b6=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv'); bt=b6[b6.Q_score<=.6].reset_index(drop=True); n=bt.N_params_B.to_numpy(float); d=bt.D_tokens_B.to_numpy(float); y=bt.val_loss.to_numpy(float); q=bt.Q_score.to_numpy(float)
key=pd.DataFrame({'n':n,'d':d}); key['g']=key.groupby(['n','d']).ngroup(); w=np.zeros(len(bt))
for g in np.unique(key.g):
 ii=np.flatnonzero(key.g.to_numpy()==g); w[ii]=1/len(ii)
w=w/w.sum(); p=np.asarray(pi['B6:MQ-add']['params'],float); L=float(pi['B6:MQ-add']['Lstar']); sy=float(pi['B6:MQ-add']['sy'])
def pvec(x,names=['E','A','B','alpha','beta','k_add']): return np.array([v*(L if names[i] in ('E','A','B','k_add') else 1.0) for i,v in enumerate(np.exp(x))])
def pred(pp): return pvec(np.log(p/np.array([L,L,L,1,1,L])))*0 + (p[0]+p[1]*n**(-p[3])+p[2]*d**(-p[4])-p[5]*(q-.6))
yp=p[0]+p[1]*n**(-p[3])+p[2]*d**(-p[4])-p[5]*(q-.6); finite_pos=bool(np.isfinite(yp).all() and (yp>=0).all())
bounds=np.array([[1e-8*L,1e3*L],[1e-8*L,1e3*L],[1e-8*L,1e3*L],[1e-4,4],[1e-4,4],[1e-8*L,1e3*L]])
near=[float(p[i]) for i in range(6) if min(abs(p[i]-bounds[i,0]),abs(p[i]-bounds[i,1]))<=1e-6*max(1,abs(bounds[i,1]-bounds[i,0]))]
names=['E','A','B','alpha','beta','k_add']; x0=np.array([np.log(p[i]/(L if names[i] in ('E','A','B','k_add') else 1.0)) for i in range(6)])
def res(x):
 pp=pvec(x); return np.sqrt(w)*(pp[0]+pp[1]*n**(-pp[3])+pp[2]*d**(-pp[4])-pp[5]*(q-.6)-y)/sy
J=np.empty((len(bt),6)); h=1e-5
for jj in range(6):
 xp=x0.copy(); xm=x0.copy(); xp[jj]+=h; xm[jj]-=h; J[:,jj]=(res(xp)-res(xm))/(2*h)
norms=np.linalg.norm(J,axis=0); Jc=J/norms; s=np.linalg.svd(Jc,compute_uv=False); rank=int(np.sum(s/s[0]>1e-8)); cond=float(s[0]/s[-1]) if rank==6 else None; own={'full_rank':bool(rank==6),'rank':rank,'condition_number':cond,'condition_pass':bool(cond is not None and cond<1e8),'column_norms':norms.tolist(),'singular_values':s.tolist(),'near_boundary_parameters':near,'boundary_pass':len(near)==0,'support_finite_nonnegative':finite_pos,'support_min':float(yp.min()),'multistart_pass':bool(int(pd.read_csv(OLD/'fit/scaling_parameters_by_source.csv').query("source=='B6' and model=='MQ-add' and stage=='full'").iloc[0].n_successful_starts)>0),'profile_pass':all(not s['weakly_identified'] for s in summaries if s['source']=='B6' and s['model']=='MQ-add'),'profile_statuses':[{'parameter':s['parameter'],'status':s['status'],'n_inside_set':s['n_inside_set'],'n_skipped':s['n_skipped'],'touches_fixed_hard_boundary':s['touches_fixed_hard_boundary']} for s in summaries if s['source']=='B6' and s['model']=='MQ-add']}
own['PASS']=bool(own['support_finite_nonnegative'] and own['boundary_pass'] and own['full_rank'] and own['condition_pass'] and own['multistart_pass'] and own['profile_pass'])
# MQ-eff boundary is separate sensitivity evidence only.
pe=np.asarray(pi['B6:MQ-eff']['params'],float); eff_boundary=bool(abs(pe[-1]-1e-6)<=1e-12)
write('corrected_gates/G4_corrected.json',{'run_id':'20260925T103130+08','model':'MQ-add','source':'B6','support':'Q<=0.6','G4':own,'MQ_eff_boundary':{'eta':float(pe[-1]),'lower_bound':1e-6,'at_lower_bound':eff_boundary,'role':'SENSITIVITY_ONLY_SEPARATE','can_enter_MQ_add_G4':False}})
# Reconcile only frozen G1-G3 booleans from the original run; they are never recomputed here.
os_=json.loads((OLD/'run_summary.json').read_text(encoding='utf-8')); g1=os_['G1']; g2=os_['G2']; g3=os_['G3']; g4=own
final=bool(g1['PASS'] and g2['PASS'] and g3['PASS'] and g4['PASS']); sci='ACCEPT_B6_SOURCE_RELATION' if final else 'REJECT_TO_M0_6'
write('corrected_gates/G1_G4_reconciliation.json',{'run_id':'20260925T103130+08','G1_source':'original formal B run, read-only','G2_source':'original formal B run, read-only','G3_source':'original formal B run, read-only','G1':g1,'G2':g2,'G3':g3,'G4_corrected':g4,'all_four_PASS':final,'scientific_result':sci})
# Corrected identifiability/contract bindings; no full/fold/bootstrap/B7/B8 refit.
idrows=[]
for s in summaries:
 weak=bool(s['weakly_identified']); role='sensitivity_only' if s['model']=='MQ-eff' else ('main_quality_candidate' if s['model']=='MQ-add' else 'null_or_baseline'); idrows.append({'module':s['source']+'_'+s['model'],'parameter':s['parameter'],'source':s['source'],'role':role,'status':'SENSITIVITY_ONLY' if s['model']=='MQ-eff' else ('WEAKLY_IDENTIFIED' if weak else 'IDENTIFIED_SOURCE_CONDITIONAL'),'profile_status':s['status'],'full_point_in_inside_set':s['full_point_in_inside_set'],'can_enter_T07_identified':bool(s['model']!='MQ-eff' and not weak and sci=='ACCEPT_B6_SOURCE_RELATION')})
pd.DataFrame(idrows).to_csv(RUN/'identifiability_matrix_B_corrected.csv',index=False,encoding='utf-8-sig')
write('t07_bside_contract_candidate_corrected.json',{'schema_version':1,'branch':'TASK-T06E-B-R1','status':'CANDIDATE_FOR_CONTROLLER_ONLY','primary_model':'M0_B1','quality_enabled':False,'mixture_transport_enabled':False,'scientific_result':sci,'G1':g1,'G2':g2,'G3':g3,'G4_corrected':g4,'MQ_add_profiles':[s for s in summaries if s['model']=='MQ-add'],'MQ_eff_boundary':{'eta':float(pe[-1]),'at_lower_bound':eff_boundary,'status':'SENSITIVITY_ONLY_SEPARATE'},'B7_B8_unchanged':True,'full_fold_bootstrap_refit':False})
stage('G4_reconciliation','PASS' if final else 'FAIL',sci); print(json.dumps({'status':'COMPLETE_PENDING_CONTROLLER_REVIEW','scientific_result':sci,'MQ_add_G4':own['PASS'],'profiles_reproduced':len(repro)},ensure_ascii=False))
