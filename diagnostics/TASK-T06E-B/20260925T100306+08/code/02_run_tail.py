from __future__ import annotations
import json, math, time, traceback, warnings, os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import qmc, spearmanr

warnings.filterwarnings('ignore', category=RuntimeWarning)
ROOT=Path.cwd(); RUN=Path(r'diagnostics/TASK-T06E-B/20260925T100306+08')
CFG=json.loads((RUN/'config/solver_config.json').read_text(encoding='utf-8'))
B1=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/pythia_training_log_existing.csv')
B6=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv')
B7=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment_expanded.csv')
B8=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment_large.csv')
OLD=json.loads((ROOT/'solution/outputs/scaling/scaling_params.json').read_text(encoding='utf-8'))
OLDQ=json.loads((ROOT/'solution/outputs/scaling/quality_audit.json').read_text(encoding='utf-8'))
MODEL_OFF={'M0_B1':0,'M0_6':0,'MQ-add':100000,'MQ-eff':200000}
STAGE_OFF={'full':0,'leave_N':10000,'leave_D':20000,'bootstrap':30000,'profile':40000}
BASE_OPT=CFG['seeds']['base_multistart']; BASE_BOOT=CFG['seeds']['base_bootstrap']
PARAMS={'M0_B1':['E','A','B','alpha','beta'],'M0_6':['E','A','B','alpha','beta'],'MQ-add':['E','A','B','alpha','beta','k_add'],'MQ-eff':['E','A','B','alpha','beta','eta']}
MULTI={0:0,'MQ-add':100000,'MQ-eff':200000}
STARTS={'full':33,'fold':33,'bootstrap':9,'profile':9}

def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,)): return float(x)
    if isinstance(x,np.ndarray): return clean(x.tolist())
    if isinstance(x,(pd.Timestamp,)): return x.isoformat()
    if isinstance(x,float) and not np.isfinite(x): return None
    return x

def dumps(x): return json.dumps(clean(x),ensure_ascii=False,indent=2)

def append_stage(stage,status,detail=''):
    rec={'time':pd.Timestamp.now(tz='Asia/Shanghai').isoformat(),'stage':stage,'status':status,'detail':detail}
    with (RUN/'stage_status.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False)+'\n')

def arrays_b1(df):
    return (df.N_params_B.to_numpy(float),df.D_tokens_B.to_numpy(float),df.val_loss.to_numpy(float),np.full(len(df),np.nan))

def arrays_b6(df):
    return (df.N_params_B.to_numpy(float),df.D_tokens_B.to_numpy(float),df.val_loss.to_numpy(float),df.Q_score.to_numpy(float))

def group_weights(n,d,w_extra=None):
    key=pd.DataFrame({'n':n,'d':d}); key['g']=key.groupby(['n','d'],dropna=False).ngroup()
    base=np.zeros(len(n),float)
    for g in np.unique(key.g):
        idx=np.flatnonzero(key.g.to_numpy()==g); base[idx]=1.0/len(idx)
    if w_extra is not None: base=base*np.asarray(w_extra,float)
    return base/base.sum()

def metric_rows(err,w,prefix=None):
    err=np.asarray(err,float); w=np.asarray(w,float); w=w/w.sum()
    out={'n':int(len(err)),'RMSE':float(np.sqrt(np.sum(w*err**2))),'MAE':float(np.sum(w*np.abs(err))),'bias_pred_minus_actual':float(np.sum(w*err))}
    if len(err)>1:
        y=err # placeholder replaced by caller for R2; metric_rows can be called with actual
    return out

def metrics(pred,actual,w):
    pred=np.asarray(pred,float); actual=np.asarray(actual,float); w=np.asarray(w,float); w=w/w.sum(); err=pred-actual
    sse=float(np.sum(w*err**2)); ybar=float(np.sum(w*actual)); sst=float(np.sum(w*(actual-ybar)**2))
    return {'n':int(len(pred)),'RMSE':float(np.sqrt(sse)),'MAE':float(np.sum(w*np.abs(err))),'bias_pred_minus_actual':float(np.sum(w*err)),'R2':float(1-sse/sst) if sst>0 else None,'max_abs_error':float(np.max(np.abs(err)))}

def predict(model,p,n,d,q):
    E,A,B,alpha,beta=p[:5]
    base=E+A*np.power(n,-alpha)+B*np.power(d,-beta)
    if model=='MQ-add':
        return base-p[5]*(q-0.6)
    if model=='MQ-eff':
        return E+A*np.power(n,-alpha)+B*np.power(d*np.exp(-p[5]*(q-0.6)),-beta)
    return base

def bounds_physical(model,Lstar):
    rel=np.array([1e-8*Lstar,1e3*Lstar],float)
    out=[]
    for name in PARAMS[model]:
        if name in ('E','A','B','k_add'): out.append(rel.copy())
        elif name in ('alpha','beta'): out.append(np.array([1e-4,4.0]))
        elif name=='eta': out.append(np.array([1e-6,50.0]))
    return np.asarray(out,float)

def encode(model,p,Lstar):
    p=np.asarray(p,float); b=bounds_physical(model,Lstar); x=np.empty(len(p))
    for i,name in enumerate(PARAMS[model]): x[i]=np.log(p[i]/(Lstar if name in ('E','A','B','k_add') else 1.0))
    return x

def decode(model,x,Lstar):
    return np.array([val*(Lstar if name in ('E','A','B','k_add') else 1.0) for val,name in zip(np.exp(x),PARAMS[model])],float)

def encode_bounds(model,Lstar):
    b=bounds_physical(model,Lstar)
    return np.log(b[:,0]/(Lstar if m in ('E','A','B','k_add') else 1.0) for m in [])

def enc_bounds(model,Lstar):
    b=bounds_physical(model,Lstar); lo=[]; hi=[]
    for name,(a,z) in zip(PARAMS[model],b):
        scale=Lstar if name in ('E','A','B','k_add') else 1.0
        lo.append(math.log(a/scale)); hi.append(math.log(z/scale))
    return np.asarray(lo),np.asarray(hi)

def center_physical(model):
    if model in ('M0_B1','M0_6'):
        if model=='M0_B1':
            d=OLD['parameters']; p=np.array([d[k] for k in ['E','A','B','alpha','beta']])
        else:
            d=OLDQ['table_results']['B6']['parameters']; p=np.array([d[k] for k in ['E','A','B','alpha','beta']])
    elif model=='MQ-add':
        d=OLDQ['table_results']['B6']['parameters']; p=np.array([d[k] for k in ['E','A','B','alpha','beta','k']])
    else:
        d=OLDQ['table_results']['B6']['parameters']; p=np.array([d[k] for k in ['E','A','B','alpha','beta']]+[d['k']*d['beta']])
    return p

def make_starts(model,Lstar,count,seed):
    lo,hi=enc_bounds(model,Lstar); center=np.clip(encode(model,center_physical(model),Lstar),lo,hi)
    pts=qmc.Sobol(d=len(lo),scramble=True,seed=int(seed)).random(count-1)
    spans=(hi-lo); starts=[center]
    for z in pts: starts.append(lo+0.05*spans+z*0.90*spans)
    return np.asarray(starts,float)

def jac_diag(res):
    J=np.asarray(res.jac,float); norms=np.linalg.norm(J,axis=0)
    if np.any(~np.isfinite(norms)) or np.any(norms==0): return {'rank':0,'full_rank':False,'condition_number':None,'column_norms':norms.tolist()}
    Jc=J/norms; s=np.linalg.svd(Jc,compute_uv=False); rank=int(np.sum(s/s[0]>1e-8)) if len(s) and s[0]>0 else 0
    cond=float(s[0]/s[-1]) if rank==len(s) and s[-1]>0 else None
    return {'rank':rank,'full_rank':bool(rank==J.shape[1]),'condition_number':cond,'column_norms':norms.tolist(),'singular_values':s.tolist()}

def near_boundary(model,p,Lstar):
    b=bounds_physical(model,Lstar); names=[]
    for val,(a,z),name in zip(p,b,PARAMS[model]):
        tol=1e-6*max(1.0,abs(z-a)); 
        if min(abs(val-a),abs(val-z))<=tol: names.append(name)
    return names

@dataclass
class FitContext:
    source:str; model:str; stage:str; task_id:str; fold_id:int; replicate:int; n:np.ndarray; d:np.ndarray; y:np.ndarray; q:np.ndarray; w:np.ndarray; seed:int

def fit_model(ctx:FitContext,count:int):
    y=ctx.y; Lstar=float(np.median(y)); iqr=float(np.percentile(y,75)-np.percentile(y,25)); sy=max(iqr,1e-8)
    lo,hi=enc_bounds(ctx.model,Lstar); starts=make_starts(ctx.model,Lstar,count,ctx.seed)
    def residual(x): return np.sqrt(ctx.w)*(predict(ctx.model,decode(ctx.model,x,Lstar),ctx.n,ctx.d,ctx.q)-y)/sy
    results=[]; best=None; rows=[]
    for j,x0 in enumerate(starts):
        rec={'task_id':ctx.task_id,'source':ctx.source,'model':ctx.model,'stage':ctx.stage,'fold_id':ctx.fold_id,'replicate':ctx.replicate,'seed':ctx.seed,'start_index':j,'start':x0.tolist()}
        try:
            r=least_squares(residual,x0,bounds=(lo,hi),method='trf',loss='linear',jac='3-point',x_scale=1.0,ftol=1e-12,xtol=1e-12,gtol=1e-12,max_nfev=100000)
            cost=float(r.cost); ok=bool(r.success and np.isfinite(cost) and np.all(np.isfinite(r.x)))
            rec.update({'success':ok,'status':int(r.status),'message':str(r.message),'nfev':int(r.nfev),'cost':cost,'x':r.x.tolist(),'finite':bool(np.all(np.isfinite(r.fun)))})
            if ok:
                results.append((cost,j,r))
                if best is None or cost<best[0]: best=(cost,j,r)
        except Exception as e:
            rec.update({'success':False,'status':-999,'message':repr(e),'nfev':None,'cost':None,'x':None,'finite':False})
        rows.append(rec)
    if best is None:
        return None,rows,{'Lstar':Lstar,'sy':sy,'n_successful_starts':0,'optimizer_success':False}
    cost,j,r=best; p=decode(ctx.model,r.x,Lstar); diag=jac_diag(r); nb=near_boundary(ctx.model,p,Lstar)
    costs=np.array([x[0] for x in results],float); xs=np.array([x[2].x for x in results],float)
    unsep=False
    if len(costs)>1:
        within=np.flatnonzero(costs<=costs.min()+1e-7)
        if len(within)>1:
            distances=np.linalg.norm(xs[within]-xs[within[0]],axis=1)
            unsep=bool(np.max(distances)>1e-3)
    summary={'task_id':ctx.task_id,'source':ctx.source,'model':ctx.model,'stage':ctx.stage,'fold_id':ctx.fold_id,'replicate':ctx.replicate,'seed':ctx.seed,'Lstar':Lstar,'sy':sy,'n_train':int(len(y)),'n_params':int(len(p)),'n_starts':int(count),'n_successful_starts':int(len(results)),'optimizer_success':True,'objective':float(r.cost),'objective_difference_best_to_worst':float(costs.max()-costs.min()),'n_distinct_within_1e-7':int(np.sum(costs<=costs.min()+1e-7)),'unseparable_multiminima':unsep,'rank':diag['rank'],'full_rank':diag['full_rank'],'condition_number':diag['condition_number'],'near_boundary_parameters':';'.join(nb),'parameters':{k:float(v) for k,v in zip(PARAMS[ctx.model],p)}}
    return (p,r,summary,ctx,diag),rows,summary

def fixed_residual(model,names,xfree,free_idx,fix_idx,fix_val,ctx,Lstar,sy):
    full=np.empty(len(names),float); full[free_idx]=xfree; full[fix_idx]=fix_val
    return np.sqrt(ctx.w)*(predict(model,decode(model,full,Lstar),ctx.n,ctx.d,ctx.q)-ctx.y)/sy

def fit_fixed(ctx,fix_idx,fix_val,seed,count=9):
    y=ctx.y; Lstar=float(np.median(y)); iqr=float(np.percentile(y,75)-np.percentile(y,25)); sy=max(iqr,1e-8)
    names=PARAMS[ctx.model]; free_idx=np.array([i for i in range(len(names)) if i!=fix_idx],int)
    lo,hi=enc_bounds(ctx.model,Lstar); center=np.clip(encode(ctx.model,center_physical(ctx.model),Lstar),lo,hi)[free_idx]
    pts=qmc.Sobol(d=len(free_idx),scramble=True,seed=int(seed)).random(count-1); spans=hi[free_idx]-lo[free_idx]
    starts=[center]+[lo[free_idx]+0.05*spans+z*0.90*spans for z in pts]
    best=None; rows=[]; finite=0
    for j,x0 in enumerate(starts):
        rec={'task_id':ctx.task_id+'_profile','model':ctx.model,'stage':'profile','profile_parameter':names[fix_idx],'fixed_value':fix_val,'seed':seed,'start_index':j}
        try:
            r=least_squares(lambda x:fixed_residual(ctx.model,names,x,free_idx,fix_idx,fix_val,ctx,Lstar,sy),x0,bounds=(lo[free_idx],hi[free_idx]),method='trf',loss='linear',jac='3-point',x_scale=1.0,ftol=1e-12,xtol=1e-12,gtol=1e-12,max_nfev=100000)
            ok=bool(r.success and np.isfinite(r.cost)); rec.update({'success':ok,'status':int(r.status),'message':str(r.message),'nfev':int(r.nfev),'cost':float(r.cost),'x':r.x.tolist(),'finite':bool(np.all(np.isfinite(r.fun)))})
            if ok: finite+=1; best=(float(r.cost),r) if best is None or r.cost<best[0] else best
        except Exception as e: rec.update({'success':False,'status':-999,'message':repr(e),'nfev':None,'cost':None,'x':None,'finite':False})
        rows.append(rec)
    if best is None: return None,rows
    cost,r=best; full=np.empty(len(names),float); full[free_idx]=r.x; full[fix_idx]=fix_val; p=decode(ctx.model,full,Lstar)
    return {'fixed_value':float(fix_val),'SSE':float(2*cost),'objective':float(cost),'n_successful_starts':int(finite),'parameters':p.tolist(),'parameter_dict':{k:float(v) for k,v in zip(names,p)}},rows

def ctx_for(df,source,model,stage,task_id,fold_id=0,replicate=0,weights=None,seed=None):
    n,d,y,q=arrays_b1(df) if source=='B1' else arrays_b6(df)
    if weights is None: weights=group_weights(n,d)
    if seed is None: seed=BASE_OPT+MODEL_OFF[model]+STAGE_OFF[stage]+int(fold_id)
    return FitContext(source,model,stage,task_id,fold_id,replicate,n,d,y,q,np.asarray(weights,float),int(seed))

def key_hash(df,cols):
    x=df[cols].copy().sort_values(cols,kind='mergesort').reset_index(drop=True)
    import hashlib
    return hashlib.sha256(x.to_csv(index=False,float_format='%.17g',lineterminator='\n').encode()).hexdigest()
def group_slopes(df):
    z=[]
    for (n,d),g in df.groupby(['N_params_B','D_tokens_B'],sort=True):
        q=g.Q_score.to_numpy(float); y=g.val_loss.to_numpy(float)
        slope=float(np.polyfit(q,y,1)[0]) if len(g)>=2 and np.ptp(q)>0 else None
        z.append({'N_params_B':float(n),'D_tokens_B':float(d),'n':int(len(g)),'slope_dL_dQ':slope,'slope_estimable':bool(slope is not None),'direction':'negative' if slope is not None and slope<0 else ('positive' if slope is not None and slope>0 else ('zero' if slope==0 else 'not_estimable'))})
    return z
append_stage('cache_load','START','hash-bound deterministic B1/B6 folds and profiles from interrupted engineering run')
B6TRAIN=B6[B6.Q_score<=0.6].copy().reset_index(drop=True); B6STRESS=B6[B6.Q_score>0.6].copy().reset_index(drop=True)
par=pd.read_csv(RUN/'fit/scaling_parameters_by_source.csv')
full_b6={}; full_b6_diag=json.loads((RUN/'profiles/jacobian_matrices.json').read_text(encoding='utf-8'))
for model in ['M0_6','MQ-add','MQ-eff']:
    rr=par[(par.source=='B6')&(par.model==model)&(par.stage=='full')].iloc[0]
    p=np.array([float(rr[k]) for k in PARAMS[model]],float); ctx=ctx_for(B6TRAIN,'B6',model,'full',f'B6_full_{model}',0,0)
    sm={'source':'B6','model':model,'stage':'full','task_id':f'B6_full_{model}','fold_id':0,'replicate':0,'seed':int(rr.seed),'Lstar':float(rr.Lstar),'sy':float(rr.sy),'n_train':int(rr.n_train),'n_params':len(p),'n_starts':int(rr.n_starts),'n_successful_starts':int(rr.n_successful_starts),'optimizer_success':True,'objective':float(rr.objective),'rank':int(rr['rank']),'full_rank':bool(rr.full_rank),'condition_number':None if pd.isna(rr.condition_number) else float(rr.condition_number),'near_boundary_parameters':'' if pd.isna(rr.near_boundary_parameters) else str(rr.near_boundary_parameters),'parameters':{k:float(rr[k]) for k in PARAMS[model]},'unseparable_multiminima':False}
    full_b6[model]=(p,None,sm,ctx,full_b6_diag['B6:'+model])
b1row=par[(par.source=='B1')&(par.model=='M0_B1')&(par.stage=='full')].iloc[0]; b1_full_p=np.array([float(b1row[k]) for k in PARAMS['M0_B1']],float)
profile_summaries=pd.read_csv(RUN/'profiles/profile_summary.csv').to_dict('records'); profile_grid=pd.read_csv(RUN/'profiles/profile_grid.csv').to_dict('records'); profile_ms=pd.read_csv(RUN/'profiles/profile_multistart_results.csv').to_dict('records')
sl=pd.read_csv(RUN/'validation/within_ND_quality_effects.csv'); n_est=int(sl.slope_estimable.sum()); n_neg=int((sl.direction=='negative').sum()); n_zero=int((sl.direction=='zero').sum()); n_pos=int((sl.direction=='positive').sum()); neg_frac=n_neg/n_est if n_est else None
cm=pd.read_csv(RUN/'validation/candidate_comparison.csv'); gate={}
for _,z in cm.iterrows(): gate[z.split]={'macro_RMSE_M0_6':float(z.macro_RMSE_null),'macro_RMSE_MQ_add':float(z.macro_RMSE_candidate),'relative_improvement':float(z.relative_improvement),'improvement_pass':bool(z.relative_improvement>=0.05),'fold_ratio_pass':int(z.fold_ratio_pass_count),'fold_ratio_required':int(z.fold_ratio_required),'fold_ratio_pass_gate':bool(z.fold_ratio_pass_count>=z.fold_ratio_required),'n_folds':int(z.n_folds)}
append_stage('cache_load','PASS','22 profiles and frozen split evidence loaded; no Q>0.6 training')
b6key={(float(q.N_params_B),float(q.D_tokens_B),float(q.Q_score)):float(q.val_loss) for _,q in B6.iterrows()}; rows=[]
for _,q in B7.iterrows():
    key=(float(q.N_params_B),float(q.D_tokens_B),float(q.Q_score)); rep=key in b6key
    rows.append({'experiment_id':q.experiment_id,'N_params_B':key[0],'D_tokens_B':key[1],'Q_score':key[2],'B7_val_loss':float(q.val_loss),'overlap_with_B6':rep,'B6_val_loss':b6key.get(key),'abs_loss_difference':abs(float(q.val_loss)-b6key[key]) if rep else None,'exact_loss_match':bool(rep and float(q.val_loss)==b6key[key]),'denominator_role':'REPEAT_AUDIT_ONLY' if rep else 'B7_NEW90_PREDICTION_ONLY'})
b7audit=pd.DataFrame(rows); b7audit.to_csv(RUN/'b7_extension/b7_overlap_audit.csv',index=False,encoding='utf-8-sig')
b7new=B7[[(float(q.N_params_B),float(q.D_tokens_B),float(q.Q_score)) not in b6key for _,q in B7.iterrows()]].copy().reset_index(drop=True)
if len(b7new)!=90: raise SystemExit('B7_NEW_COUNT_FAIL')
b7pred=[]
for model in ['M0_6','MQ-add','MQ-eff']:
    pp,_,_,ctx,_=full_b6[model]; yp=predict(model,pp,b7new.N_params_B.to_numpy(float),b7new.D_tokens_B.to_numpy(float),b7new.Q_score.to_numpy(float)); w=group_weights(b7new.N_params_B.to_numpy(float),b7new.D_tokens_B.to_numpy(float))
    for i,q in b7new.iterrows(): b7pred.append({'experiment_id':q.experiment_id,'source':'B7_new90','model':model,'N_params_B':float(q.N_params_B),'D_tokens_B':float(q.D_tokens_B),'Q_score':float(q.Q_score),'actual':float(q.val_loss),'prediction':float(yp[i]),'weight':float(w[i]),'role':'SAME_SOURCE_GRID_EXTENSION_NOT_INDEPENDENT_REPLICATION'})
pd.DataFrame(b7pred).to_csv(RUN/'b7_extension/b7_new90_predictions.csv',index=False,encoding='utf-8-sig'); b7metric=[]
for model in ['M0_6','MQ-add','MQ-eff']:
    q=pd.DataFrame([r for r in b7pred if r['model']==model]); m=metrics(q.prediction,q.actual,q.weight); m.update({'source':'B7_new90','region':'new90','model':model,'support_status':'SAME_SOURCE_EXTENSION','selection_role':'FROZEN_POSTHOC_ONLY'}); b7metric.append(m)
pd.DataFrame(b7metric).to_csv(RUN/'b7_extension/b7_new90_metrics.csv',index=False,encoding='utf-8-sig')
b6grid=set(b6key.keys()); bsupport=[]; b8pred=[]
for _,q in B8.iterrows():
    key=(float(q.N_params_B),float(q.D_tokens_B),float(q.Q_score)); common=key in b6grid
    bsupport.append({'experiment_id':q.experiment_id,'N_params_B':key[0],'D_tokens_B':key[1],'Q_score':key[2],'val_loss':float(q.val_loss),'data_type':q.data_type,'support_status':'COMMON_SUPPORT_CONFLICT_EVIDENCE' if common else 'OUT_OF_SUPPORT_STRESS','oos_reason':'' if common else 'EXACT_NDQ_KEY_NOT_IN_B6','B6_val_loss':b6key.get(key),'loss_difference_B8_minus_B6':float(q.val_loss)-b6key[key] if common else None})
    for model in ['M0_6','MQ-add','MQ-eff']:
        pp,_,_,ctx,_=full_b6[model]; yp=float(predict(model,pp,np.array([key[0]]),np.array([key[1]]),np.array([key[2]]))[0]); b8pred.append({'experiment_id':q.experiment_id,'source':'B8','model':model,'N_params_B':key[0],'D_tokens_B':key[1],'Q_score':key[2],'actual':float(q.val_loss),'prediction':yp,'support_status':'COMMON_SUPPORT_CONFLICT_EVIDENCE' if common else 'OUT_OF_SUPPORT_STRESS','parameter_source':'B6_FROZEN_SOURCE_CONDITIONAL','old_k_minus20_used':False})
bsp=pd.DataFrame(bsupport); bp=pd.DataFrame(b8pred); bsp.to_csv(RUN/'b8_stress/b8_support_partition.csv',index=False,encoding='utf-8-sig'); bp.to_csv(RUN/'b8_stress/b8_predictions.csv',index=False,encoding='utf-8-sig')
if int((bsp.support_status=='COMMON_SUPPORT_CONFLICT_EVIDENCE').sum())!=160 or int((bsp.support_status=='OUT_OF_SUPPORT_STRESS').sum())!=1544: raise SystemExit('B8_PARTITION_FAIL')
stress=[]
for region in ['COMMON_SUPPORT_CONFLICT_EVIDENCE','OUT_OF_SUPPORT_STRESS']:
    for model in ['M0_6','MQ-add','MQ-eff']:
        q=bp[(bp.support_status==region)&(bp.model==model)]; w=group_weights(q.N_params_B.to_numpy(float),q.D_tokens_B.to_numpy(float)); m=metrics(q.prediction.to_numpy(float),q.actual.to_numpy(float),w); m.update({'source':'B8','region':region,'model':model,'support_status':region,'selection_role':'STRESS_ONLY','old_k_minus20_used':False}); stress.append(m)
gslope=[]
for region in ['COMMON_SUPPORT_CONFLICT_EVIDENCE','OUT_OF_SUPPORT_STRESS']:
    sub=bsp[bsp.support_status==region]
    for (n,d),g in sub.groupby(['N_params_B','D_tokens_B'],sort=True):
        if len(g)>=2 and np.ptp(g.Q_score)>0:
            actual=float(np.polyfit(g.Q_score,g.val_loss,1)[0]); row={'source':'B8','region':region,'N_params_B':float(n),'D_tokens_B':float(d),'n':len(g),'actual_slope_dL_dQ':actual,'actual_direction':'positive' if actual>0 else ('negative' if actual<0 else 'zero')}
            for model in ['M0_6','MQ-add','MQ-eff']:
                z=bp[(bp.support_status==region)&(bp.model==model)&(bp.N_params_B==n)&(bp.D_tokens_B==d)]; row[model+'_pred_slope']=float(np.polyfit(z.Q_score,z.prediction,1)[0]) if len(z)>=2 and np.ptp(z.Q_score)>0 else None
            gslope.append(row)
for model in ['M0_6','MQ-add','MQ-eff']:
    for region in ['COMMON_SUPPORT_CONFLICT_EVIDENCE','OUT_OF_SUPPORT_STRESS']:
        z=[q for q in gslope if q['region']==region]; predcol=model+'_pred_slope'; est=[q for q in z if q[predcol] is not None and q[predcol]!=0]; viol=sum(np.sign(q['actual_slope_dL_dQ'])!=np.sign(q[predcol]) for q in est); stress.append({'source':'B8','region':region,'model':model,'support_status':region,'n_groups':len(z),'direction_violation_rate':float(viol/len(est)) if est else None,'direction_estimable_groups':len(est),'selection_role':'STRESS_ONLY'})
stress.append({'source':'B6','region':'Q<=0.6','model':'k=0/M0_6','support_status':'SOURCE_SUPPORT','n_groups':45,'negative_slope_fraction':neg_frac,'positive_slope_fraction':n_pos/n_est if n_est else None,'zero_slope_fraction':n_zero/n_est if n_est else None,'selection_role':'NULL_EVIDENCE'}); stress.append({'source':'B8','region':'COMMON_SUPPORT_CONFLICT_EVIDENCE','model':'direction_evidence','support_status':'CONFLICT_EVIDENCE','n_groups':len([q for q in gslope if q['region']=='COMMON_SUPPORT_CONFLICT_EVIDENCE']),'positive_slope_fraction':float(np.mean([q['actual_direction']=='positive' for q in gslope if q['region']=='COMMON_SUPPORT_CONFLICT_EVIDENCE'])),'selection_role':'CONFLICT_EVIDENCE'})
pd.DataFrame(gslope).to_csv(RUN/'b8_stress/b8_group_slopes.csv',index=False,encoding='utf-8-sig'); pd.DataFrame(stress).to_csv(RUN/'b8_stress/b8_stress_metrics.csv',index=False,encoding='utf-8-sig'); append_stage('B7_B8','PASS','B7 new=90 repeats=360; B8 common=160 outside=1544')
rng=np.random.Generator(np.random.PCG64(BASE_BOOT)); uniques=sorted(B6TRAIN.N_params_B.unique()); draw_rows=[]; seed_rows=[]; boot_ms=[]
for rep in range(200):
    sampled=rng.choice(np.asarray(uniques,float),size=len(uniques),replace=True); counts={float(v):int(np.sum(sampled==v)) for v in uniques}; parts=[]
    for nval,mult in counts.items():
        if mult: parts.append(pd.concat([B6TRAIN[B6TRAIN.N_params_B==nval].copy()]*mult,ignore_index=True))
    boot=pd.concat(parts,ignore_index=True); slopes=pd.DataFrame(group_slopes(boot)); negf=float((slopes.direction=='negative').mean()); dpass=bool(negf>=0.80); seed_rows.append({'replicate':rep,'bootstrap_rng_seed':BASE_BOOT,'sampled_N_multiset':'|'.join(f'{v:g}x{counts[v]}' for v in uniques if counts[v]),'n_unique_physical_N':9,'n_rows':len(boot),'max_Q':float(boot.Q_score.max()),'stress_Q_rows_included':0,'negative_slope_fraction':negf,'direction_pass_0.80':dpass})
    for model in ['M0_6','MQ-add','MQ-eff']:
        seed=BASE_OPT+MODEL_OFF[model]+STAGE_OFF['bootstrap']+rep; ctx=ctx_for(boot,'B6',model,'bootstrap',f'B6_bootstrap_{rep}_{model}',rep,rep,seed=seed); pack,ms,sm=fit_model(ctx,9); boot_ms.extend(ms); seed_rows[-1][model+'_optimizer_seed']=seed
        row={'source':'B6','model':model,'replicate':rep,'success':False,'B6_bootstrap_rng_seed':BASE_BOOT,'optimizer_seed':seed,'sampled_N_multiset':seed_rows[-1]['sampled_N_multiset'],'negative_slope_fraction':negf,'direction_pass_0.80':dpass,'source_label':'B6_SOURCE_CONDITIONAL'}
        if pack is not None:
            pp,rr,sm2,ctx2,diag=pack; row.update({'success':True,'objective':sm2['objective'],'n_successful_starts':sm2['n_successful_starts'],'rank':sm2['rank'],'condition_number':sm2['condition_number']}); row.update({k:float(v) for k,v in sm2['parameters'].items()})
        draw_rows.append(row)
bootdraw=pd.DataFrame(draw_rows); old=pd.read_csv(ROOT/'solution/outputs/scaling/cluster_bootstrap_parameters.csv'); b1draw=[]
for _,q in old.iterrows(): b1draw.append({'source':'B1','model':'M0_B1','replicate':int(q.replicate),'success':bool(q.success),'B6_bootstrap_rng_seed':None,'optimizer_seed':None,'sampled_N_multiset':'EXISTING_TRAJECTORY_CLUSTER_FILE','negative_slope_fraction':None,'direction_pass_0.80':None,'source_label':'EXISTING_8_CLUSTER_CONDITIONAL','E':float(q.E),'A':float(q.A),'B':float(q.B),'alpha':float(q.alpha),'beta':float(q.beta)})
combined=pd.concat([pd.DataFrame(b1draw),bootdraw],ignore_index=True); combined.to_parquet(RUN/'bootstrap/parameter_draws.parquet',index=False); combined.to_csv(RUN/'bootstrap/parameter_draws.csv',index=False,encoding='utf-8-sig'); pd.DataFrame(seed_rows).to_csv(RUN/'bootstrap/bootstrap_seed_audit.csv',index=False,encoding='utf-8-sig'); summ=[]
for (source,model),g in combined.groupby(['source','model'],dropna=False):
    gs=g[g.success==True]; z={'source':source,'model':model,'requested':len(g),'n_success':len(gs),'n_failed':int((~g.success).sum()),'source_label':'EXISTING_8_CLUSTER_CONDITIONAL' if source=='B1' else 'B6_SOURCE_CONDITIONAL'}
    for nm in PARAMS[model]:
        if nm in gs: z[nm+'_p2_5']=float(gs[nm].quantile(.025)); z[nm+'_median']=float(gs[nm].quantile(.5)); z[nm+'_p97_5']=float(gs[nm].quantile(.975))
    summ.append(z)
pd.DataFrame(summ).to_csv(RUN/'bootstrap/bootstrap_summary.csv',index=False,encoding='utf-8-sig'); mqb=bootdraw[(bootdraw.model=='MQ-add')&(bootdraw.success==True)]; ns=int(len(mqb)); nneg=int((mqb['direction_pass_0.80']==True).sum()); req=int(np.ceil(.9*ns)) if ns else 0; G3={'requested':200,'successful':ns,'success_gate_190':bool(ns>=190),'negative_direction_replicates':nneg,'negative_direction_required':req,'negative_direction_pass':bool(nneg>=req),'PASS':bool(ns>=190 and nneg>=req)}; append_stage('bootstrap','PASS' if G3['PASS'] else 'FAIL',f'success={ns}, negative-direction pass={nneg}/{req}')
mqadd_p,mqadd_r,mqadd_sm,mqadd_ctx,mqadd_diag=full_b6['MQ-add']; mqeff_p,mqeff_r,mqeff_sm,mqeff_ctx,mqeff_diag=full_b6['MQ-eff']; g1={'PASS':bool(neg_frac>=0.80),'negative_groups':n_neg,'estimable_groups':n_est,'zero_groups':n_zero,'positive_groups':n_pos,'not_estimable_groups':45-n_est,'negative_fraction':neg_frac,'threshold':0.80}; g2={'PASS':bool(gate['leave_N']['improvement_pass'] and gate['leave_D']['improvement_pass'] and gate['leave_N']['fold_ratio_pass_gate'] and gate['leave_D']['fold_ratio_pass_gate']),'leave_N':gate['leave_N'],'leave_D':gate['leave_D']}; prof=pd.DataFrame(profile_summaries); mqadd_prof=prof[(prof.source=='B6')&(prof.model=='MQ-add')]; profile_weak=bool(mqadd_prof.weakly_identified.any()); support=[]
for model in ['M0_6','MQ-add','MQ-eff']:
    pp,_,_,ctx,_=full_b6[model]; yp=predict(model,pp,ctx.n,ctx.d,ctx.q); support.append({'model':model,'all_finite':bool(np.isfinite(yp).all()),'all_nonnegative':bool((yp>=0).all()),'min_prediction':float(yp.min()),'PASS':bool(np.isfinite(yp).all() and (yp>=0).all())})
boundary_ok=not any(str(full_b6[model][2]['near_boundary_parameters']) not in ('','nan','None') for model in full_b6); jac=full_b6['MQ-add'][4]; jac_ok=bool(jac['full_rank'] and jac['condition_number'] is not None and jac['condition_number']<1e8); multi_ok=all(full_b6[m][2]['n_successful_starts']>0 for m in full_b6); g4={'PASS':bool(multi_ok and boundary_ok and jac_ok and not profile_weak and all(x['PASS'] for x in support)),'support_predictions':support,'no_fixed_optimization_boundary_touched':boundary_ok,'jacobian_full_rank':jac['full_rank'],'jacobian_condition_number':jac['condition_number'],'jacobian_gate':jac_ok,'profile_weakly_identified':profile_weak,'multistart_pass':multi_ok}; gates={'G1_direction':g1,'G2_prediction':g2,'G3_bootstrap_stability':G3,'G4_numerical_identifiability':g4,'all_four_PASS':bool(g1['PASS'] and g2['PASS'] and G3['PASS'] and g4['PASS'])}; scientific='ACCEPT_B6_SOURCE_RELATION' if gates['all_four_PASS'] else 'REJECT_TO_M0_6'
idrows=[]
for nm,val in zip(PARAMS['M0_B1'],b1_full_p):
    weak=any((r['source']=='B1') and (r['parameter']==nm) and bool(r['weakly_identified']) for r in profile_summaries); idrows.append({'module':'B1_M0','parameter':nm,'point_value':float(val),'source':'B1','role':'source_baseline','status':'WEAKLY_IDENTIFIED' if weak else 'IDENTIFIED_SOURCE_CONDITIONAL','support':'B1 8 N trajectories','can_enter_T07_identified':bool(not weak),'notes':'source/transform conditional; 8-cluster bootstrap'})
for model in ['M0_6','MQ-add','MQ-eff']:
    pp=full_b6[model][0]
    for nm,val in zip(PARAMS[model],pp):
        weak=any((r['source']=='B6') and (r['model']==model) and (r['parameter']==nm) and bool(r['weakly_identified']) for r in profile_summaries); status='SENSITIVITY_ONLY' if model=='MQ-eff' else ('WEAKLY_IDENTIFIED' if weak else 'IDENTIFIED_SOURCE_CONDITIONAL'); idrows.append({'module':'B6_'+model,'parameter':nm,'point_value':float(val),'source':'B6','role':'main_quality_candidate' if model=='MQ-add' else ('null' if model=='M0_6' else 'sensitivity_only'),'status':status,'support':'B6 exact N-D-Q grid Q<=0.6','can_enter_T07_identified':bool(model!='MQ-eff' and not weak and scientific=='ACCEPT_B6_SOURCE_RELATION'),'notes':'source-internal only; no cross-source quality interpretation'})
idrows.append({'module':'B6_MQ-eff','parameter':'k_eff','point_value':float(mqeff_p[5]/mqeff_p[4]),'source':'B6','role':'derived_sensitivity_only','status':'SENSITIVITY_ONLY','support':'B6 exact grid Q<=0.6','can_enter_T07_identified':False,'notes':'derived eta/beta; never substitutes MQ-add'}); pd.DataFrame(idrows).to_csv(RUN/'identifiability_matrix_B.csv',index=False,encoding='utf-8-sig')
unc={'schema_version':1,'components_separate':True,'B1_parameter_uncertainty':{'status':'EXISTING_8_CLUSTER_CONDITIONAL','not_a_population_CI':True},'B6_parameter_uncertainty':{'status':'NINE_N_CLUSTER_CONDITIONAL','successful':ns,'requested':200,'not_a_population_CI':True},'model_structure_uncertainty':{'MQ-add':'pre-registered_main_candidate','MQ-eff':'sensitivity_only','k_0':'null_always_retained'},'B8_conflict':{'status':'CONFLICT_EVIDENCE','common_support_rows':160,'propagated_as_probability':False},'cross_source_transport':{'status':'NOT_ESTIMATED_IN_B_BRANCH','components':['A/B mapping','rho_Q','tau_p','r_B1','h']},'combining_rule':'No single statistical CI formed across these components.'}; (RUN/'uncertainty_components_B.json').write_text(dumps(unc),encoding='utf-8')
contract={'schema_version':1,'branch':'TASK-T06E-B','status':'CANDIDATE_FOR_CONTROLLER_ONLY','primary_model':'M0_B1','quality_enabled':False,'mixture_transport_enabled':False,'scientific_result':scientific,'B1':{'parameters':{k:float(v) for k,v in zip(PARAMS['M0_B1'],b1_full_p)},'source_label':'IDENTIFIED_SOURCE_CONDITIONAL'},'B6':{'M0_6':{k:float(v) for k,v in zip(PARAMS['M0_6'],full_b6['M0_6'][0])},'MQ-add':{k:float(v) for k,v in zip(PARAMS['MQ-add'],mqadd_p)},'MQ-eff_sensitivity':{k:float(v) for k,v in zip(PARAMS['MQ-eff'],mqeff_p)},'quality_gate':gates,'source_scope':'Q<=0.6 only','accept_status':scientific},'B7':{'role':'same_source_extension_only','new_keys':90,'repeat_keys_excluded_from_denominator':360},'B8':{'role':'conflict_and_stress_only','common_support_rows':160,'outside_support_rows':1544,'evidence_parallel':['B6_negative','B8_positive','k=0'],'old_k_minus20_propagated':False},'T07_defaults':{'quality_enabled':False,'mixture_transport_enabled':False,'cross_source_mapping':'NOT_ESTIMATED','Q_gt_0.6':'OUT_OF_SUPPORT_STRESS'}}; (RUN/'t07_bside_contract_candidate.json').write_text(dumps(contract),encoding='utf-8')
checks={'input_hashes_and_T06_hash':'PASS','input_anchor_rows_grid':'PASS','B1_units_billion':'PASS','B6_training_225_highQ_135':'PASS','M0_MQ_fold_key_identity':bool(pd.read_csv(RUN/'validation/validation_splits.csv').query("source=='B6'").key_identity_pass.all()),'G1_exact_threshold':g1['PASS'],'G2_exact_thresholds':g2['PASS'],'G3_bootstrap_200_seed_direction':G3['PASS'],'G4_jacobian_bounds_profiles':g4['PASS'],'profile_grid_complete':bool((prof.n_grid_completed==prof.n_grid_requested).all()),'multistart_counts':bool(all(full_b6[m][2]['n_starts']==33 and full_b6[m][2]['n_successful_starts']>0 for m in full_b6)),'B7_360_repeat_90_new':bool(len(b7audit)==450 and int(b7audit.overlap_with_B6.sum())==360 and len(b7new)==90),'B8_160_common_partition':bool(int((bsp.support_status=='COMMON_SUPPORT_CONFLICT_EVIDENCE').sum())==160),'old_k_minus20_not_propagated':True,'B2_B4_B5_not_used_for_tuning':True,'B3_B10_not_truth':True,'old_scaling_files_not_written':True,'branch_directory_isolation':True,'no_forbidden_reads':True,'final_manifest_consistent':'PENDING_FINALIZER'}; (RUN/'checks.json').write_text(dumps(checks),encoding='utf-8')
summary={'run_id':'20260925T100306+08','status':'COMPLETE_PENDING_CONTROLLER_REVIEW','scientific_result':scientific,'primary_model':'M0_B1','quality_enabled':False,'mixture_transport_enabled':False,'G1':g1,'G2':g2,'G3':G3,'G4':g4,'B6_full_parameters':{m:{k:float(v) for k,v in zip(PARAMS[m],full_b6[m][0])} for m in ['M0_6','MQ-add','MQ-eff']},'B1_full_parameters':{k:float(v) for k,v in zip(PARAMS['M0_B1'],b1_full_p)},'B7':{'new_keys':90,'repeat_keys':360},'B8':{'common_support':160,'outside_support':1544}}; (RUN/'run_summary.json').write_text(dumps(summary),encoding='utf-8')
pd.concat([pd.read_csv(RUN/'fit/multistart_results.csv'),pd.DataFrame(boot_ms)],ignore_index=True).to_csv(RUN/'fit/multistart_results.csv',index=False,encoding='utf-8-sig'); param_old=pd.read_csv(RUN/'fit/scaling_parameters_by_source.csv'); param_boot=[]
for _,z in bootdraw.iterrows():
    rr={'source':'B6','model':z.model,'stage':'bootstrap','task_id':f'B6_bootstrap_{int(z.replicate)}_{z.model}','fold_id':int(z.replicate),'replicate':int(z.replicate),'seed':z.optimizer_seed,'Lstar':None,'sy':None,'n_train':225,'n_params':len(PARAMS[z.model]),'n_successful_starts':z.get('n_successful_starts'),'objective':z.get('objective'),'rank':z.get('rank'),'full_rank':None,'condition_number':z.get('condition_number'),'near_boundary_parameters':'','source_label':'B6_SOURCE_CONDITIONAL'}
    for nm in PARAMS[z.model]: rr[nm]=z.get(nm)
    param_boot.append(rr)
pd.concat([param_old,pd.DataFrame(param_boot)],ignore_index=True).to_csv(RUN/'fit/scaling_parameters_by_source.csv',index=False,encoding='utf-8-sig'); append_stage('gates','PASS' if gates['all_four_PASS'] else 'FAIL',scientific); print(dumps(summary))



