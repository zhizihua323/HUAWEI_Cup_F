# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import json,math,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.optimize import least_squares
from scipy.stats import qmc
ROOT=Path.cwd(); RUN=Path(r'diagnostics/TASK-T06E-B-R1/20260925T103130+08'); OLD=Path(r'diagnostics/TASK-T06E-B/20260925T100306+08')
source,model,pname=sys.argv[1],sys.argv[2],sys.argv[3]
pi=json.loads((RUN/'config/profile_inputs_frozen.json').read_text(encoding='utf-8')); rec=pi[source+':'+model]; p=np.asarray(rec['params'],float); Lstar=float(rec['Lstar']); sy=float(rec['sy']); sse_full=float(rec['SSE_min']); threshold=float(rec['descriptive_threshold'])
names={'M0_B1':['E','A','B','alpha','beta'],'M0_6':['E','A','B','alpha','beta'],'MQ-add':['E','A','B','alpha','beta','k_add'],'MQ-eff':['E','A','B','alpha','beta','eta']}[model]; j=names.index(pname); nparam=len(names)
if source=='B1':
 df=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/pythia_training_log_existing.csv'); n=df.N_params_B.to_numpy(float); d=df.D_tokens_B.to_numpy(float); y=df.val_loss.to_numpy(float); q=np.full(len(df),np.nan); w=np.ones(len(df))/len(df)
else:
 df=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv'); df=df[df.Q_score<=.6].reset_index(drop=True); n=df.N_params_B.to_numpy(float); d=df.D_tokens_B.to_numpy(float); y=df.val_loss.to_numpy(float); q=df.Q_score.to_numpy(float)
 key=pd.DataFrame({'n':n,'d':d}); key['g']=key.groupby(['n','d']).ngroup(); w=np.zeros(len(df))
 for g in np.unique(key.g):
  ii=np.flatnonzero(key.g.to_numpy()==g); w[ii]=1/len(ii)
 w=w/w.sum()
def scale_for(name): return Lstar if name in ('E','A','B','k_add') else 1.0
def lo_hi():
 lo=[]; hi=[]
 for name in names:
  s=scale_for(name)
  if name in ('E','A','B','k_add'): a,z=1e-8*s,1e3*s
  elif name in ('alpha','beta'): a,z=1e-4,4.0
  else: a,z=1e-6,50.0
  lo.append(math.log(a/s)); hi.append(math.log(z/s))
 return np.asarray(lo),np.asarray(hi)
def encode_full(vec): return np.array([math.log(vec[i]/scale_for(names[i])) for i in range(nparam)],float)
def decode_free(xfree):
 full=np.empty(nparam,float); full[j]=fixed; free=np.array([i for i in range(nparam) if i!=j],int); full[free]=np.exp(xfree)*np.array([scale_for(names[i]) for i in free]); return full
def predict(pp):
 E,A,B,al,be=pp[:5]; base=E+A*np.power(n,-al)+B*np.power(d,-be)
 if model=='MQ-add': return base-pp[5]*(q-.6)
 if model=='MQ-eff': return E+A*np.power(n,-al)+B*np.power(d*np.exp(-pp[5]*(q-.6)),-be)
 return base
lo,hi=lo_hi(); free_idx=np.array([i for i in range(nparam) if i!=j],int); free_lo=lo[free_idx]; free_hi=hi[free_idx]
# physical-value grid, no second transformation
vals=[]
if pname in ('k_add','eta'): vals.append(0.0)
if pname in ('E','A','B','k_add'):
 s=scale_for(pname); phys=(1e-8*s,1e3*s)
else: phys=(1e-4,4.0) if pname in ('alpha','beta') else (1e-6,50.0)
for u in np.linspace(math.log(phys[0]/scale_for(pname)),math.log(phys[1]/scale_for(pname)),41): vals.append(float(math.exp(u)*scale_for(pname)))
vals.append(float(p[j])); vals=sorted(set(float(v) for v in vals))
# seed derivation unchanged from original profile worker: base+model offset+profile offset+param_index*1000+grid_index
model_off={'M0_B1':0,'M0_6':0,'MQ-add':100000,'MQ-eff':200000}[model]; base=20260926+model_off+40000
rows=[]; ms=[]
for gi,fixed in enumerate(vals):
 seed=base+j*1000+gi; center=encode_full(p)[free_idx]
 pts=qmc.Sobol(d=len(free_idx),scramble=True,seed=int(seed)).random(8); spans=free_hi-free_lo; starts=[center]+[free_lo+.05*spans+z*.90*spans for z in pts]
 best=None; ns=0
 for si,x0 in enumerate(starts):
  rr={'task_id':source+':'+model+':profile','source':source,'model':model,'stage':'profile','profile_parameter':pname,'fixed_value':float(fixed),'seed':int(seed),'start_index':int(si)}
  try:
   def residual(x): return np.sqrt(w)*(predict(decode_free(x))-y)/sy
   fit=least_squares(residual,x0,bounds=(free_lo,free_hi),method='trf',loss='linear',jac='3-point',x_scale=1.0,ftol=1e-12,xtol=1e-12,gtol=1e-12,max_nfev=100000)
   ok=bool(fit.success and np.isfinite(fit.cost) and np.all(np.isfinite(fit.fun))); rr.update({'success':ok,'status':int(fit.status),'message':str(fit.message),'nfev':int(fit.nfev),'cost':float(fit.cost),'x':fit.x.tolist(),'finite':bool(np.all(np.isfinite(fit.fun)))})
   if ok:
    ns+=1; best=(float(fit.cost),fit) if best is None or fit.cost<best[0] else best
  except Exception as exc: rr.update({'success':False,'status':-999,'message':repr(exc),'nfev':None,'cost':None,'x':None,'finite':False})
  ms.append(rr)
 if best is None:
  rows.append({'source':source,'model':model,'parameter':pname,'grid_index':gi,'fixed_value':float(fixed),'seed':int(seed),'SSE':None,'n_successful_starts':0,'skipped':True,'skip_reason':'NO_FINITE_CONVERGED_REFIT'})
 else:
  cost,fit=best; pp=decode_free(fit.x); row={'source':source,'model':model,'parameter':pname,'grid_index':gi,'fixed_value':float(fixed),'seed':int(seed),'SSE':float(2*cost),'n_successful_starts':int(ns),'skipped':False,'skip_reason':''}; row.update({f'{nm}_conditional':float(v) for nm,v in zip(names,pp)}); rows.append(row)
# hard-check the formal full-fit point by an explicit physical-vector fit
fullrow=[r for r in rows if not r['skipped'] and r['fixed_value']==float(p[j])]
if not fullrow: raise SystemExit('FULL_POINT_NOT_IN_GRID')
fr=fullrow[0]; err=abs(fr[f'{pname}_conditional']-p[j]); tol=1e-12+1e-10*abs(p[j])
if err>tol: raise SystemExit('FIXED_PHYSICAL_VALUE_MISMATCH')
if fr['SSE']>sse_full*(1+1e-6)+1e-12: raise SystemExit(f'FULL_POINT_SSE_FAIL {fr["SSE"]} {sse_full}')
out={'source':source,'model':model,'parameter':pname,'full_value':float(p[j]),'SSE_min':sse_full,'descriptive_threshold':threshold,'rows':rows,'multistart':ms}
(RUN/'corrected_profiles/parts'/f'{source}__{model}__{pname}.json').write_text(json.dumps(out,ensure_ascii=False),encoding='utf-8'); print(json.dumps({'status':'PASS','source':source,'model':model,'parameter':pname,'n':len(rows),'full_SSE':fr['SSE']},ensure_ascii=False))
