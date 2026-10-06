from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import qmc

ROOT=Path.cwd(); RUN=Path(sys.argv[1]); source=sys.argv[2]; model=sys.argv[3]; pname=sys.argv[4]
CFG=json.loads((RUN/'config/solver_config.json').read_text(encoding='utf-8'))
inputs=json.loads((RUN/'profiles/profile_inputs.json').read_text(encoding='utf-8'))
rec=inputs[source+':'+model]; p=np.asarray(rec['params'],float); Lstar=float(rec['Lstar']); sy=float(rec['sy'])
PARAMS={'M0_B1':['E','A','B','alpha','beta'],'M0_6':['E','A','B','alpha','beta'],'MQ-add':['E','A','B','alpha','beta','k_add'],'MQ-eff':['E','A','B','alpha','beta','eta']}
MODEL_OFF={'M0_B1':0,'M0_6':0,'MQ-add':100000,'MQ-eff':200000}
names=PARAMS[model]; pi=names.index(pname); name=pname
if source=='B1':
    df=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/pythia_training_log_existing.csv'); n=df.N_params_B.to_numpy(float); d=df.D_tokens_B.to_numpy(float); y=df.val_loss.to_numpy(float); q=np.full(len(df),np.nan); w=np.ones(len(df))/len(df)
else:
    df=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv'); df=df[df.Q_score<=0.6].reset_index(drop=True); n=df.N_params_B.to_numpy(float); d=df.D_tokens_B.to_numpy(float); y=df.val_loss.to_numpy(float); q=df.Q_score.to_numpy(float)
    keys=pd.DataFrame({'n':n,'d':d}); keys['g']=keys.groupby(['n','d'],dropna=False).ngroup(); w=np.zeros(len(df))
    for g in np.unique(keys.g):
        idx=np.flatnonzero(keys.g.to_numpy()==g); w[idx]=1/len(idx)
    w=w/w.sum()

def bounds_physical():
    rel=np.array([1e-8*Lstar,1e3*Lstar]); out=[]
    for nm in names:
        if nm in ('E','A','B','k_add'): out.append(rel.copy())
        elif nm in ('alpha','beta'): out.append(np.array([1e-4,4.0]))
        else: out.append(np.array([1e-6,50.0]))
    return np.asarray(out,float)
def enc_bounds():
    lo=[]; hi=[]
    for nm,(a,z) in zip(names,bounds_physical()):
        scale=Lstar if nm in ('E','A','B','k_add') else 1.0; lo.append(math.log(a/scale)); hi.append(math.log(z/scale))
    return np.asarray(lo),np.asarray(hi)
def decode(x):
    return np.array([v*(Lstar if nm in ('E','A','B','k_add') else 1.0) for v,nm in zip(np.exp(x),names)],float)
def predict(pp):
    E,A,B,alpha,beta=pp[:5]; base=E+A*np.power(n,-alpha)+B*np.power(d,-beta)
    if model=='MQ-add': return base-pp[5]*(q-0.6)
    if model=='MQ-eff': return E+A*np.power(n,-alpha)+B*np.power(d*np.exp(-pp[5]*(q-0.6)),-beta)
    return base
lo,hi=enc_bounds(); free_idx=np.array([i for i in range(len(names)) if i!=pi],int)
vals=[]
if name in ('k_add','eta'): vals.append(0.0)
for u in np.linspace(lo[pi],hi[pi],41):
    scale=Lstar if name in ('E','A','B','k_add') else 1.0; vals.append(float(np.exp(u)*scale))
vals.append(float(p[pi])); vals=sorted(set(float(np.round(v,14)) for v in vals))
raw=np.array([math.log(float(val)/(Lstar if nm in ('E','A','B','k_add') else 1.0)) for nm,val in zip(names,p)],float)
center=np.clip(raw[free_idx],lo[free_idx],hi[free_idx])
rows=[]; ms=[]; base_seed=int(CFG['seeds']['base_multistart'])+int(MODEL_OFF[model])+int(CFG['seeds']['stage_offsets']['profile'])
for gi,fv in enumerate(vals):
    seed=base_seed+pi*1000+gi
    def residual(x):
        full=np.empty(len(names),float); full[free_idx]=x; full[pi]=fv
        return np.sqrt(w)*(predict(decode(full))-y)/sy
    pts=qmc.Sobol(d=len(free_idx),scramble=True,seed=int(seed)).random(8); spans=hi[free_idx]-lo[free_idx]
    starts=[center]+[lo[free_idx]+0.05*spans+z*0.90*spans for z in pts]
    best=None; nsuccess=0
    for j,x0 in enumerate(starts):
        rr={'task_id':source+':'+model+':profile','model':model,'stage':'profile','profile_parameter':name,'fixed_value':fv,'seed':seed,'start_index':j}
        try:
            fit=least_squares(residual,x0,bounds=(lo[free_idx],hi[free_idx]),method='trf',loss='linear',jac='3-point',x_scale=1.0,ftol=1e-12,xtol=1e-12,gtol=1e-12,max_nfev=100000)
            ok=bool(fit.success and np.isfinite(fit.cost)); rr.update({'success':ok,'status':int(fit.status),'message':str(fit.message),'nfev':int(fit.nfev),'cost':float(fit.cost),'x':fit.x.tolist(),'finite':bool(np.all(np.isfinite(fit.fun)))})
            if ok:
                nsuccess+=1
                if best is None or fit.cost<best[0]: best=(float(fit.cost),fit)
        except Exception as exc:
            rr.update({'success':False,'status':-999,'message':repr(exc),'nfev':None,'cost':None,'x':None,'finite':False})
        ms.append(rr)
    if best is None:
        rows.append({'source':source,'model':model,'parameter':name,'grid_index':gi,'fixed_value':fv,'SSE':None,'n_successful_starts':0,'skipped':True,'skip_reason':'NO_FINITE_CONVERGED_REFIT','seed':seed})
    else:
        cost,fit=best; full=np.empty(len(names),float); full[free_idx]=fit.x; full[pi]=fv; pp=decode(full)
        row={'source':source,'model':model,'parameter':name,'grid_index':gi,'fixed_value':fv,'SSE':float(2*cost),'n_successful_starts':int(nsuccess),'skipped':False,'skip_reason':'','seed':seed}
        row.update({f'{nm}_conditional':float(val) for nm,val in zip(names,pp)}); rows.append(row)
out={'source':source,'model':model,'parameter':name,'rows':rows,'multistart':ms}
(RUN/'profiles/parts'/f'{source}__{model}__{name}.json').write_text(json.dumps(out,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'source':source,'model':model,'parameter':name,'n':len(rows),'skipped':sum(bool(r.get('skipped')) for r in rows)}))


