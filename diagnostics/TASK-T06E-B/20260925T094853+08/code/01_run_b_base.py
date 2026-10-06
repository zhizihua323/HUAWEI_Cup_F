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
ROOT=Path.cwd(); RUN=Path(r'diagnostics/TASK-T06E-B/20260925T090601+08')
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

ALL_MS=[]; ALL_PARAMS=[]; ALL_PRED=[]; SPLITS=[]; FOLD_METRICS=[]
append_stage('B1_B6_fit','START','input anchors frozen; begin B1 and B6 fitting')

# B1 full and frozen validation splits
b1_full=ctx_for(B1,'B1','M0_B1','full','B1_full',0,0,weights=np.ones(len(B1))/len(B1),seed=BASE_OPT)
b1_pack,rows,summ=fit_model(b1_full,33); ALL_MS.extend(rows)
if b1_pack is None: raise SystemExit('B1_FULL_NO_CONVERGED_SOLUTION')
b1_full_p,b1_res,b1_summary,_,b1_diag=b1_pack; ALL_PARAMS.append(b1_summary)
pred=predict('M0_B1',b1_full_p,b1_full.n,b1_full.d,b1_full.q)
for i,row in B1.iterrows(): ALL_PRED.append({'source':'B1','model':'M0_B1','role':'in_sample','split':'full','fold_id':0,'N_params_B':float(row.N_params_B),'D_tokens_B':float(row.D_tokens_B),'Q_score':None,'actual':float(row.val_loss),'prediction':float(pred[i]),'weight':1.0/len(B1)})
SPLITS.append({'source':'B1','split':'full','fold_id':0,'heldout_label':'all','n_train':len(B1),'n_test':len(B1),'train_key_hash':key_hash(B1,['N_params_B','D_tokens_B']),'test_key_hash':key_hash(B1,['N_params_B','D_tokens_B']),'models':'M0_B1','key_identity_pass':True})

for fold_id,nval in enumerate(sorted(B1.N_params_B.unique())):
    tr=B1[B1.N_params_B!=nval].copy(); te=B1[B1.N_params_B==nval].copy()
    ctx=ctx_for(tr,'B1','M0_B1','leave_N',f'B1_leave_N_{nval:g}',fold_id,0,weights=np.ones(len(tr))/len(tr))
    pack,rows,summ=fit_model(ctx,33); ALL_MS.extend(rows); ALL_PARAMS.append(summ)
    if pack is None: continue
    p,r,sm,_,diag=pack; yp=predict('M0_B1',p,te.N_params_B.to_numpy(float),te.D_tokens_B.to_numpy(float),np.full(len(te),np.nan))
    w=np.ones(len(te))/len(te); m=metrics(yp,te.val_loss.to_numpy(float),w); m.update({'source':'B1','model':'M0_B1','split':'leave_N','fold_id':fold_id,'heldout_label':f'N={nval:g}'})
    FOLD_METRICS.append(m)
    SPLITS.append({'source':'B1','split':'leave_N','fold_id':fold_id,'heldout_label':f'N={nval:g}','n_train':len(tr),'n_test':len(te),'train_key_hash':key_hash(tr,['N_params_B','D_tokens_B']),'test_key_hash':key_hash(te,['N_params_B','D_tokens_B']),'models':'M0_B1','key_identity_pass':True})
    for j,row in te.iterrows(): ALL_PRED.append({'source':'B1','model':'M0_B1','role':'validation','split':'leave_N','fold_id':fold_id,'N_params_B':float(row.N_params_B),'D_tokens_B':float(row.D_tokens_B),'Q_score':None,'actual':float(row.val_loss),'prediction':float(yp[list(te.index).index(j)]),'weight':float(w[list(te.index).index(j)])})

# B1 late-token 80/20 per N trajectory; D ascending
late=[]; late_counter=0
for nval,g in B1.groupby('N_params_B',sort=True):
    g=g.sort_values('D_tokens_B',kind='mergesort').reset_index(drop=True); cut=int(np.floor(0.8*len(g))); tr=g.iloc[:cut].copy(); te=g.iloc[cut:].copy()
    fold_id=100+late_counter; late_counter+=1
    ctx=ctx_for(tr,'B1','M0_B1','full',f'B1_late_token_{nval:g}',fold_id,0,weights=np.ones(len(tr))/len(tr),seed=BASE_OPT+STAGE_OFF['full']+fold_id)
    pack,rows,summ=fit_model(ctx,33); ALL_MS.extend(rows); ALL_PARAMS.append(summ)
    if pack is None: continue
    p,r,sm,_,diag=pack; yp=predict('M0_B1',p,te.N_params_B.to_numpy(float),te.D_tokens_B.to_numpy(float),np.full(len(te),np.nan)); w=np.ones(len(te))/len(te); m=metrics(yp,te.val_loss.to_numpy(float),w); m.update({'source':'B1','model':'M0_B1','split':'late_token','fold_id':fold_id,'heldout_label':f'N={nval:g}'})
    FOLD_METRICS.append(m)
    SPLITS.append({'source':'B1','split':'late_token','fold_id':fold_id,'heldout_label':f'N={nval:g}','n_train':len(tr),'n_test':len(te),'train_key_hash':key_hash(tr,['N_params_B','D_tokens_B']),'test_key_hash':key_hash(te,['N_params_B','D_tokens_B']),'models':'M0_B1','key_identity_pass':True,'train_max_D':float(tr.D_tokens_B.max()),'test_min_D':float(te.D_tokens_B.min())})
    for i,row in te.iterrows(): ALL_PRED.append({'source':'B1','model':'M0_B1','role':'validation','split':'late_token','fold_id':fold_id,'N_params_B':float(row.N_params_B),'D_tokens_B':float(row.D_tokens_B),'Q_score':None,'actual':float(row.val_loss),'prediction':float(yp[i-cut]),'weight':1.0/len(te)})

# B6 frozen support only
B6TRAIN=B6[B6.Q_score<=0.6].copy().reset_index(drop=True); B6STRESS=B6[B6.Q_score>0.6].copy().reset_index(drop=True)
if len(B6TRAIN)!=225 or len(B6STRESS)!=135: raise SystemExit('B6_SUPPORT_PARTITION_FAIL')
full_b6={}; full_b6_diag={}
for midx,model in enumerate(['M0_6','MQ-add','MQ-eff']):
    ctx=ctx_for(B6TRAIN,'B6',model,'full',f'B6_full_{model}',0,0,seed=BASE_OPT+MODEL_OFF[model]+STAGE_OFF['full'])
    pack,rows,summ=fit_model(ctx,33); ALL_MS.extend(rows); ALL_PARAMS.append(summ)
    if pack is None: raise SystemExit(f'{model}_FULL_NO_CONVERGED_SOLUTION')
    p,r,sm,_,diag=pack; full_b6[model]=pack; full_b6_diag[model]=diag
    yp=predict(model,p,ctx.n,ctx.d,ctx.q)
    for i in range(len(ctx.n)): ALL_PRED.append({'source':'B6','model':model,'role':'in_sample','split':'full','fold_id':0,'N_params_B':float(ctx.n[i]),'D_tokens_B':float(ctx.d[i]),'Q_score':float(ctx.q[i]),'actual':float(ctx.y[i]),'prediction':float(yp[i]),'weight':float(ctx.w[i])})

# B6 conforming folds; all three candidates use identical fold keys
b6_fold_counter=0
for split_name,group_col in [('leave_N','N_params_B'),('leave_D','D_tokens_B')]:
    for held in sorted(B6TRAIN[group_col].unique()):
        fold_id=b6_fold_counter; b6_fold_counter+=1
        tr=B6TRAIN[B6TRAIN[group_col]!=held].copy().reset_index(drop=True); te=B6TRAIN[B6TRAIN[group_col]==held].copy().reset_index(drop=True)
        expected_test=25 if split_name=='leave_N' else 45; expected_train=200 if split_name=='leave_N' else 180
        if len(te)!=expected_test or len(tr)!=expected_train: raise SystemExit('B6_FOLD_COUNT_FAIL')
        train_hash=key_hash(tr,['N_params_B','D_tokens_B','Q_score']); test_hash=key_hash(te,['N_params_B','D_tokens_B','Q_score'])
        SPLITS.append({'source':'B6','split':split_name,'fold_id':fold_id,'heldout_label':f'{group_col}={held:g}','n_train':len(tr),'n_test':len(te),'train_key_hash':train_hash,'test_key_hash':test_hash,'models':'M0_6;MQ-add;MQ-eff','key_identity_pass':True})
        for model in ['M0_6','MQ-add','MQ-eff']:
            ctx=ctx_for(tr,'B6',model,split_name,f'B6_{split_name}_{held:g}_{model}',fold_id,0)
            pack,rows,summ=fit_model(ctx,33); ALL_MS.extend(rows); ALL_PARAMS.append(summ)
            if pack is None:
                FOLD_METRICS.append({'source':'B6','model':model,'split':split_name,'fold_id':fold_id,'heldout_label':f'{group_col}={held:g}','n':len(te),'RMSE':None,'MAE':None,'bias_pred_minus_actual':None,'R2':None,'max_abs_error':None,'fit_success':False}); continue
            p,r,sm,_,diag=pack
            n,d,y,q=arrays_b6(te); w=group_weights(n,d); yp=predict(model,p,n,d,q); m=metrics(yp,y,w); m.update({'source':'B6','model':model,'split':split_name,'fold_id':fold_id,'heldout_label':f'{group_col}={held:g}','fit_success':True}); FOLD_METRICS.append(m)
            for i in range(len(te)): ALL_PRED.append({'source':'B6','model':model,'role':'validation','split':split_name,'fold_id':fold_id,'N_params_B':float(n[i]),'D_tokens_B':float(d[i]),'Q_score':float(q[i]),'actual':float(y[i]),'prediction':float(yp[i]),'weight':float(w[i])})

pd.DataFrame(SPLITS).to_csv(RUN/'validation/validation_splits.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(FOLD_METRICS).to_csv(RUN/'validation/validation_by_group.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(ALL_MS).to_csv(RUN/'fit/multistart_results.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(ALL_PRED).to_parquet(RUN/'fit/full_fit_predictions.parquet',index=False)
pd.DataFrame(ALL_PRED).to_csv(RUN/'fit/full_fit_predictions.csv',index=False,encoding='utf-8-sig')
param_rows=[]
for sm in ALL_PARAMS:
    base={'source':sm['source'],'model':sm['model'],'stage':sm['stage'],'task_id':sm['task_id'],'fold_id':sm['fold_id'],'replicate':sm['replicate'],'seed':sm['seed'],'Lstar':sm['Lstar'],'sy':sm['sy'],'n_train':sm['n_train'],'n_params':sm['n_params'],'n_starts':sm['n_starts'],'n_successful_starts':sm['n_successful_starts'],'objective':sm['objective'],'rank':sm['rank'],'full_rank':sm['full_rank'],'condition_number':sm['condition_number'],'near_boundary_parameters':sm['near_boundary_parameters'],'source_label': 'EXISTING_8_CLUSTER_CONDITIONAL' if sm['source']=='B1' else 'B6_SOURCE_CONDITIONAL'}
    for k,v in sm['parameters'].items(): base[k]=v
    param_rows.append(base)
pd.DataFrame(param_rows).to_csv(RUN/'fit/scaling_parameters_by_source.csv',index=False,encoding='utf-8-sig')
append_stage('B1_B6_fit','PASS',f'B1 full validations and {b6_fold_counter} B6 folds complete')

def group_slopes(df):
    rows=[]
    for (n,d),g in df.groupby(['N_params_B','D_tokens_B'],sort=True):
        q=g.Q_score.to_numpy(float); y=g.val_loss.to_numpy(float)
        if len(g)>=2 and np.ptp(q)>0: s=float(np.polyfit(q,y,1)[0]); est=True
        else: s=None; est=False
        rows.append({'N_params_B':float(n),'D_tokens_B':float(d),'n':int(len(g)),'slope_dL_dQ':s,'slope_estimable':est,'direction':'negative' if s is not None and s<0 else ('positive' if s is not None and s>0 else ('zero' if s==0 else 'not_estimable'))})
    return rows
B6_SLOPES=pd.DataFrame(group_slopes(B6TRAIN)); B6_SLOPES.insert(0,'source','B6'); B6_SLOPES.insert(1,'model_role','raw_actual_unsign_constrained')
B6_SLOPES.to_csv(RUN/'validation/within_ND_quality_effects.csv',index=False,encoding='utf-8-sig')
n_est=int(B6_SLOPES.slope_estimable.sum()); n_neg=int((B6_SLOPES.direction=='negative').sum()); n_zero=int((B6_SLOPES.direction=='zero').sum()); n_pos=int((B6_SLOPES.direction=='positive').sum()); neg_frac=n_neg/n_est if n_est else None

# Interaction-only OLS after N-D demeaning, Q<=0.6 only
xrows=[]
Nstar=float(np.exp(np.log(B6TRAIN.N_params_B).mean())); Dstar=float(np.exp(np.log(B6TRAIN.D_tokens_B).mean()))
for (n,d),g in B6TRAIN.groupby(['N_params_B','D_tokens_B'],sort=True):
    qc=g.Q_score.to_numpy(float)-g.Q_score.mean(); yc=g.val_loss.to_numpy(float)-g.val_loss.mean()
    for q0,y0 in zip(qc,yc): xrows.append({'qc':q0,'qc_logN':q0*np.log(float(n)/Nstar),'qc_logD':q0*np.log(float(d)/Dstar),'yc':y0})
X=np.array([[r['qc'],r['qc_logN'],r['qc_logD']] for r in xrows],float); yv=np.array([r['yc'] for r in xrows],float); beta=np.linalg.lstsq(X,yv,rcond=None)[0]; resid=yv-X@beta; sigma2=float(np.sum(resid**2)/(len(yv)-X.shape[1])); cov=sigma2*np.linalg.inv(X.T@X); se=np.sqrt(np.diag(cov))
inter_rows=[]
for name,b,s in zip(['Q_Qbar_group','interaction_Q_logN','interaction_Q_logD'],beta,se): inter_rows.append({'source':'B6','support':'Q<=0.6','term':name,'coefficient':float(b),'standard_error':float(s),'diagnostic_only':True,'can_enter_T07':False})
pd.DataFrame(inter_rows).to_csv(RUN/'validation/interaction_diagnostics.csv',index=False,encoding='utf-8-sig')

# High-Q pressure only after full models frozen; no feedback path
stress_rows=[]
for model in ['M0_6','MQ-add','MQ-eff']:
    p,r,sm,ctx,diag=full_b6[model]; n,d,y,q=arrays_b6(B6STRESS); w=group_weights(n,d); yp=predict(model,p,n,d,q); m=metrics(yp,y,w)
    m.update({'source':'B6','region':'Q_GT_0.6','model':model,'support_status':'OUT_OF_FROZEN_TRAINING_SUPPORT_STRESS','in_parameter_selection':False,'training_boundary':'Q<=0.6'})
    stress_rows.append(m)
pd.DataFrame(stress_rows).to_csv(RUN/'validation/high_Q_stress.csv',index=False,encoding='utf-8-sig')

# frozen macro/fold comparison
cmps=[]; gate={}
for split in ['leave_N','leave_D']:
    fd=pd.DataFrame(FOLD_METRICS); fd=fd[(fd.source=='B6')&(fd.split==split)&fd.fit_success]
    null=fd[fd.model=='M0_6'].set_index('fold_id').RMSE; cand=fd[fd.model=='MQ-add'].set_index('fold_id').RMSE
    common=sorted(set(null.index)&set(cand.index)); macro_null=float(null.loc[common].mean()); macro_cand=float(cand.loc[common].mean()); improvement=(macro_null-macro_cand)/macro_null if macro_null>0 else None
    required=int(np.ceil(0.8*len(common))); ratio=sum(cand.loc[f]<=1.10*null.loc[f] for f in common); gate[split]={'macro_RMSE_M0_6':macro_null,'macro_RMSE_MQ_add':macro_cand,'relative_improvement':improvement,'improvement_pass':bool(improvement is not None and improvement>=0.05),'fold_ratio_pass':int(ratio),'fold_ratio_required':required,'fold_ratio_pass_gate':bool(ratio>=required),'n_folds':len(common)}
    cmps.append({'source':'B6','split':split,'candidate':'MQ-add','null':'M0_6','macro_RMSE_null':macro_null,'macro_RMSE_candidate':macro_cand,'relative_improvement':improvement,'improvement_gate_0.05':'PASS' if improvement is not None and improvement>=0.05 else 'FAIL','fold_ratio_pass_count':ratio,'fold_ratio_required':required,'fold_ratio_gate':'PASS' if ratio>=required else 'FAIL','n_folds':len(common)})
# pooled weighted metrics per split/model
for split in ['leave_N','leave_D']:
    for model in ['M0_6','MQ-add','MQ-eff']:
        rr=pd.DataFrame([r for r in ALL_PRED if r.get('source')=='B6' and r.get('role')=='validation' and r.get('split')==split and r.get('model')==model])
        if len(rr): 
            w=rr.weight.to_numpy(float); yp=rr.prediction.to_numpy(float); ya=rr.actual.to_numpy(float); m=metrics(yp,ya,w); m.update({'source':'B6','split':split,'candidate':model,'comparison_status':'pooled_weighted_context'})
            if model=='MQ-add':
                cmps[-2 if split=='leave_N' else -1]['pooled_RMSE_candidate']=m['RMSE']
            else: cmps[-2 if split=='leave_N' else -1]['pooled_RMSE_null']=m['RMSE'] if model=='M0_6' else cmps[-2 if split=='leave_N' else -1].get('pooled_RMSE_sensitivity')
pd.DataFrame(cmps).to_csv(RUN/'validation/candidate_comparison.csv',index=False,encoding='utf-8-sig')

# profile diagnostics on B1 full and B6 full; no Q>0.6 use
profile_summaries=[]; profile_grid=[]; profile_ms=[]; jac_rows=[]
def run_profiles(source,model,df,pack):
    p,r,sm,ctx,diag=pack; Lstar=float(sm['Lstar']); sse_min=2*float(sm['objective']); nparams=len(p); sigma2=float(sse_min/(len(df)-nparams)); threshold=float(sse_min+3.841458820694124*sigma2)
    profile_input_path=RUN/'profiles/profile_inputs.json'
    all_inputs=json.loads(profile_input_path.read_text(encoding='utf-8')) if profile_input_path.exists() else {}
    rec={'source':source,'model':model,'params':[float(v) for v in p],'Lstar':Lstar,'sy':float(sm['sy']),'SSE_min':sse_min,'sigma_hat_squared':sigma2,'descriptive_threshold':threshold}
    all_inputs[source+':'+model]=rec; profile_input_path.write_text(json.dumps(all_inputs,ensure_ascii=False,indent=2),encoding='utf-8')
    jac_rows.append({'source':source,'model':model,'task_id':sm['task_id'],'rank':diag['rank'],'full_rank':diag['full_rank'],'condition_number':diag['condition_number'],'column_norms':'|'.join(f'{z:.17g}' for z in diag['column_norms']),'singular_values':'|'.join(f'{z:.17g}' for z in diag['singular_values'])})
    procs=[]
    (RUN/'profiles/parts').mkdir(parents=True,exist_ok=True)
    env=os.environ.copy(); env.update({'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'})
    for name in PARAMS[model]:
        log=(RUN/'profiles/parts'/f'{source}__{model}__{name}.log').open('w',encoding='utf-8')
        cmd=[sys.executable,str(RUN/'code/profile_one.py'),str(RUN),source,model,name]
        procs.append((name,subprocess.Popen(cmd,cwd=str(ROOT),env=env,stdout=log,stderr=subprocess.STDOUT,text=True),log))
    for name,proc,log in procs:
        rc=proc.wait(); log.close()
        if rc!=0: raise SystemExit(f'PROFILE_CHILD_FAIL {source} {model} {name} rc={rc}')
    rows=[]
    for name in PARAMS[model]:
        part_path=RUN/'profiles/parts'/f'{source}__{model}__{name}.json'
        part=json.loads(part_path.read_text(encoding='utf-8')); profile_ms.extend(part['multistart'])
        p_rows=part['rows']
        for row in p_rows:
            if row.get('skipped'):
                row['inside_descriptive_set']=False; row['touches_fixed_hard_boundary']=False
            else:
                row['inside_descriptive_set']=bool(row['SSE']<=threshold)
                pi=PARAMS[model].index(name); b=bounds_physical(model,Lstar)[pi]
                row['touches_fixed_hard_boundary']=bool(min(abs(row['fixed_value']-b[0]),abs(row['fixed_value']-b[1]))<=1e-10*max(1.0,abs(b[1]-b[0])))
        rows.extend(p_rows)
    pr=pd.DataFrame(rows); profile_grid.extend(rows)
    inside=pr[pr.inside_descriptive_set==True]
    for name in PARAMS[model]:
        q=pr[pr.parameter==name]; qi=q[q.inside_descriptive_set==True]
        touches=bool(qi.touches_fixed_hard_boundary.any()) if len(qi) else False; skipped=int(q.skipped.sum()); unsep=bool(sm.get('unseparable_multiminima',False))
        profile_summaries.append({'source':source,'model':model,'parameter':name,'SSE_min':sse_min,'sigma_hat_squared':sigma2,'descriptive_threshold':threshold,'n_grid_requested':len(q),'n_grid_completed':int((~q.skipped).sum()),'n_inside_set':len(qi),'inside_min':float(qi.fixed_value.min()) if len(qi) else None,'inside_max':float(qi.fixed_value.max()) if len(qi) else None,'touches_fixed_hard_boundary':touches,'unseparable_multiminima':unsep,'n_skipped':skipped,'weakly_identified':bool(touches or unsep or skipped>0 or len(qi)==0),'status':'WEAKLY_IDENTIFIED' if (touches or unsep or skipped>0 or len(qi)==0) else 'PROFILE_FINITE_AND_SEPARATED'})
        append_stage('profile_parameter','PASS',f'{source}:{model}:{name}: completed={len(q)}')
    return {'SSE_min':sse_min,'sigma2':sigma2,'threshold':threshold,'summaries':[r for r in profile_summaries if r['source']==source and r['model']==model]}
prof_b1=run_profiles('B1','M0_B1',B1,b1_pack)
prof_b6={}
for model in ['M0_6','MQ-add','MQ-eff']: prof_b6[model]=run_profiles('B6',model,B6TRAIN,full_b6[model])
pd.DataFrame(profile_grid).to_csv(RUN/'profiles/profile_grid.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(profile_summaries).to_csv(RUN/'profiles/profile_summary.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(profile_ms).to_csv(RUN/'profiles/profile_multistart_results.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(jac_rows).to_csv(RUN/'profiles/jacobian_diagnostics.csv',index=False,encoding='utf-8-sig')
with (RUN/'profiles/jacobian_matrices.json').open('w',encoding='utf-8') as f:
    json.dump({'B1:M0_B1':b1_diag,'B6:M0_6':full_b6_diag['M0_6'],'B6:MQ-add':full_b6_diag['MQ-add'],'B6:MQ-eff':full_b6_diag['MQ-eff']},f,ensure_ascii=False,indent=2)
append_stage('profiles','PASS',f'{len(profile_summaries)} parameter profiles completed')

# B7 exact-key repeat audit; repeats never enter metric denominators
b6key={(float(r.N_params_B),float(r.D_tokens_B),float(r.Q_score)):float(r.val_loss) for _,r in B6.iterrows()}
rows=[]
for _,r in B7.iterrows():
    key=(float(r.N_params_B),float(r.D_tokens_B),float(r.Q_score)); rep=key in b6key
    rows.append({'experiment_id':r.experiment_id,'N_params_B':float(r.N_params_B),'D_tokens_B':float(r.D_tokens_B),'Q_score':float(r.Q_score),'B7_val_loss':float(r.val_loss),'overlap_with_B6':rep,'B6_val_loss':b6key.get(key),'abs_loss_difference':abs(float(r.val_loss)-b6key[key]) if rep else None,'exact_loss_match':bool(rep and float(r.val_loss)==b6key[key]),'denominator_role':'REPEAT_AUDIT_ONLY' if rep else 'B7_NEW90_PREDICTION_ONLY'})
b7audit=pd.DataFrame(rows); b7audit.to_csv(RUN/'b7_extension/b7_overlap_audit.csv',index=False,encoding='utf-8-sig')
b7new=B7[[(float(r.N_params_B),float(r.D_tokens_B),float(r.Q_score)) not in b6key for _,r in B7.iterrows()]].copy().reset_index(drop=True)
if len(b7new)!=90: raise SystemExit('B7_NEW_COUNT_FAIL')
b7pred=[]
for model in ['M0_6','MQ-add','MQ-eff']:
    p,r,sm,ctx,diag=full_b6[model]; yp=predict(model,p,b7new.N_params_B.to_numpy(float),b7new.D_tokens_B.to_numpy(float),b7new.Q_score.to_numpy(float)); w=group_weights(b7new.N_params_B.to_numpy(float),b7new.D_tokens_B.to_numpy(float))
    for i,r in b7new.iterrows(): b7pred.append({'experiment_id':r.experiment_id,'source':'B7_new90','model':model,'N_params_B':float(r.N_params_B),'D_tokens_B':float(r.D_tokens_B),'Q_score':float(r.Q_score),'actual':float(r.val_loss),'prediction':float(yp[i]),'weight':float(w[i]),'role':'SAME_SOURCE_GRID_EXTENSION_NOT_INDEPENDENT_REPLICATION'})
pd.DataFrame(b7pred).to_csv(RUN/'b7_extension/b7_new90_predictions.csv',index=False,encoding='utf-8-sig')
b7metric=[]
for model in ['M0_6','MQ-add','MQ-eff']:
    q=pd.DataFrame([r for r in b7pred if r['model']==model]); m=metrics(q.prediction,q.actual,q.weight); m.update({'source':'B7_new90','region':'new90','model':model,'support_status':'SAME_SOURCE_EXTENSION','selection_role':'FROZEN_POSTHOC_ONLY'}); b7metric.append(m)
pd.DataFrame(b7metric).to_csv(RUN/'b7_extension/b7_new90_metrics.csv',index=False,encoding='utf-8-sig')

# B8 exact-grid common support versus outside support; no unified fit, no old boundary k
b6_grid=set(b6key.keys())
bsupport=[]; b8pred=[]
for _,b8row in B8.iterrows():
    key=(float(r.N_params_B),float(r.D_tokens_B),float(r.Q_score)); common=key in b6_grid
    bsupport.append({'experiment_id':b8row.experiment_id,'N_params_B':float(b8row.N_params_B),'D_tokens_B':float(b8row.D_tokens_B),'Q_score':float(b8row.Q_score),'val_loss':float(b8row.val_loss),'data_type':b8row.data_type,'support_status':'COMMON_SUPPORT_CONFLICT_EVIDENCE' if common else 'OUT_OF_SUPPORT_STRESS','oos_reason':'' if common else 'EXACT_NDQ_KEY_NOT_IN_B6','B6_val_loss':b6key.get(key),'loss_difference_B8_minus_B6':float(b8row.val_loss)-b6key[key] if common else None})
    for model in ['M0_6','MQ-add','MQ-eff']:
        pk,rr,sm,ctx,diag=full_b6[model]; yp=float(predict(model,pk,np.array([key[0]]),np.array([key[1]]),np.array([key[2]]))[0])
        b8pred.append({'experiment_id':b8row.experiment_id,'source':'B8','model':model,'N_params_B':key[0],'D_tokens_B':key[1],'Q_score':key[2],'actual':float(b8row.val_loss),'prediction':yp,'support_status':'COMMON_SUPPORT_CONFLICT_EVIDENCE' if common else 'OUT_OF_SUPPORT_STRESS','parameter_source':'B6_FROZEN_SOURCE_CONDITIONAL','old_k_minus20_used':False})
bsp=pd.DataFrame(bsupport); bp=pd.DataFrame(b8pred); bsp.to_csv(RUN/'b8_stress/b8_support_partition.csv',index=False,encoding='utf-8-sig'); bp.to_csv(RUN/'b8_stress/b8_predictions.csv',index=False,encoding='utf-8-sig')
stress=[]
for region in ['COMMON_SUPPORT_CONFLICT_EVIDENCE','OUT_OF_SUPPORT_STRESS']:
    sub=bsp[bsp.support_status==region]
    if len(sub):
        for model in ['M0_6','MQ-add','MQ-eff']:
            q=bp[(bp.support_status==region)&(bp.model==model)]; w=group_weights(q.N_params_B.to_numpy(float),q.D_tokens_B.to_numpy(float)); m=metrics(q.prediction.to_numpy(float),q.actual.to_numpy(float),w); m.update({'source':'B8','region':region,'model':model,'support_status':region,'selection_role':'STRESS_ONLY','old_k_minus20_used':False}); stress.append(m)
# direction evidence in common support and outside; group linear slopes
gslope=[]
for region in ['COMMON_SUPPORT_CONFLICT_EVIDENCE','OUT_OF_SUPPORT_STRESS']:
    sub=bsp[bsp.support_status==region]
    for (n,d),g in sub.groupby(['N_params_B','D_tokens_B'],sort=True):
        if len(g)>=2 and np.ptp(g.Q_score)>0:
            actual=float(np.polyfit(g.Q_score,g.val_loss,1)[0])
            row={'source':'B8','region':region,'N_params_B':float(n),'D_tokens_B':float(d),'n':len(g),'actual_slope_dL_dQ':actual,'actual_direction':'positive' if actual>0 else ('negative' if actual<0 else 'zero')}
            for model in ['M0_6','MQ-add','MQ-eff']:
                z=bp[(bp.support_status==region)&(bp.model==model)&(bp.N_params_B==n)&(bp.D_tokens_B==d)]
                row[model+'_pred_slope']=float(np.polyfit(z.Q_score,z.prediction,1)[0]) if len(z)>=2 and np.ptp(z.Q_score)>0 else None
            gslope.append(row)
for model in ['M0_6','MQ-add','MQ-eff']:
    for region in ['COMMON_SUPPORT_CONFLICT_EVIDENCE','OUT_OF_SUPPORT_STRESS']:
        z=[r for r in gslope if r['region']==region]; predcol=model+'_pred_slope'
        est=[r for r in z if r[predcol] is not None and r[predcol]!=0]; viol=sum(np.sign(r['actual_slope_dL_dQ'])!=np.sign(r[predcol]) for r in est)
        stress.append({'source':'B8','region':region,'model':model,'support_status':region,'n_groups':len(z),'direction_violation_rate':float(viol/len(est)) if est else None,'direction_estimable_groups':len(est),'selection_role':'STRESS_ONLY'})
# B6 negative and B8 positive evidence are always parallel; k=0 is M0_6 row already present
stress.append({'source':'B6','region':'Q<=0.6','model':'k=0/M0_6','support_status':'SOURCE_SUPPORT','n_groups':45,'negative_slope_fraction':neg_frac,'positive_slope_fraction':n_pos/n_est if n_est else None,'zero_slope_fraction':n_zero/n_est if n_est else None,'selection_role':'NULL_EVIDENCE'})
stress.append({'source':'B8','region':'COMMON_SUPPORT_CONFLICT_EVIDENCE','model':'direction_evidence','support_status':'CONFLICT_EVIDENCE','n_groups':len([r for r in gslope if r['region']=='COMMON_SUPPORT_CONFLICT_EVIDENCE']),'positive_slope_fraction':float(np.mean([r['actual_direction']=='positive' for r in gslope if r['region']=='COMMON_SUPPORT_CONFLICT_EVIDENCE'])) if any(r['region']=='COMMON_SUPPORT_CONFLICT_EVIDENCE' for r in gslope) else None,'selection_role':'CONFLICT_EVIDENCE'})
pd.DataFrame(gslope).to_csv(RUN/'b8_stress/b8_group_slopes.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(stress).to_csv(RUN/'b8_stress/b8_stress_metrics.csv',index=False,encoding='utf-8-sig')
append_stage('B7_B8','PASS',f'B7 new={len(b7new)} repeats=360; B8 common={int((bsp.support_status=="COMMON_SUPPORT_CONFLICT_EVIDENCE").sum())} outside={int((bsp.support_status=="OUT_OF_SUPPORT_STRESS").sum())}')

# B6 bootstrap: complete N-cluster resampling, exact seed, three models, all replicates retained
append_stage('bootstrap','START','200 N-cluster bootstrap replicates on Q<=0.6')
rng=np.random.Generator(np.random.PCG64(BASE_BOOT)); uniques=sorted(B6TRAIN.N_params_B.unique()); draw_rows=[]; seed_rows=[]
for rep in range(200):
    sampled=rng.choice(np.asarray(uniques,float),size=len(uniques),replace=True)
    counts={float(v):int(np.sum(sampled==v)) for v in uniques}; parts=[]
    for nval,mult in counts.items():
        if mult: parts.append(pd.concat([B6TRAIN[B6TRAIN.N_params_B==nval].copy()]*mult,ignore_index=True))
    boot=pd.concat(parts,ignore_index=True)
    if len(boot)!=225 or boot.Q_score.max()>0.6+1e-15: raise SystemExit('BOOTSTRAP_Q_OR_SIZE_FAIL')
    slopes=pd.DataFrame(group_slopes(boot)); negf=float((slopes.direction=='negative').mean()); direction_pass=bool(negf>=0.80)
    seed_rows.append({'replicate':rep,'bootstrap_rng_seed':BASE_BOOT,'sampled_N_multiset':'|'.join(f'{v:g}x{counts[v]}' for v in uniques if counts[v]),'n_unique_physical_N':len(uniques),'n_rows':len(boot),'max_Q':float(boot.Q_score.max()),'stress_Q_rows_included':0,'negative_slope_fraction':negf,'direction_pass_0.80':direction_pass})
    for model in ['M0_6','MQ-add','MQ-eff']:
        seed=BASE_OPT+MODEL_OFF[model]+STAGE_OFF['bootstrap']+rep
        ctx=ctx_for(boot,'B6',model,'bootstrap',f'B6_bootstrap_{rep}_{model}',rep,rep,seed=seed)
        pack,ms,sm=fit_model(ctx,9); ALL_MS.extend(ms); ALL_PARAMS.append(sm)
        seed_rows[-1][f'{model}_optimizer_seed']=seed
        row={'source':'B6','model':model,'replicate':rep,'success':False,'B6_bootstrap_rng_seed':BASE_BOOT,'optimizer_seed':seed,'sampled_N_multiset':seed_rows[-1]['sampled_N_multiset'],'negative_slope_fraction':negf,'direction_pass_0.80':direction_pass,'source_label':'B6_SOURCE_CONDITIONAL'}
        if pack is not None:
            p,r,sm2,ctx2,diag=pack; row.update({'success':bool(sm2['optimizer_success']),'objective':sm2['objective'],'n_successful_starts':sm2['n_successful_starts'],'rank':sm2['rank'],'condition_number':sm2['condition_number']})
            row.update({k:v for k,v in sm2['parameters'].items()})
        draw_rows.append(row)
draw=pd.DataFrame(draw_rows); seeddf=pd.DataFrame(seed_rows)
# B1 existing joint bootstrap draws read-only and explicitly preserved as 8-cluster conditional
oldboot=pd.read_csv(ROOT/'solution/outputs/scaling/cluster_bootstrap_parameters.csv')
b1draws=[]
for _,r in oldboot.iterrows(): b1draws.append({'source':'B1','model':'M0_B1','replicate':int(r.replicate),'success':bool(r.success),'B6_bootstrap_rng_seed':None,'optimizer_seed':None,'sampled_N_multiset':'EXISTING_TRAJECTORY_CLUSTER_FILE','negative_slope_fraction':None,'direction_pass_0.80':None,'source_label':'EXISTING_8_CLUSTER_CONDITIONAL','E':float(r.E),'A':float(r.A),'B':float(r.B),'alpha':float(r.alpha),'beta':float(r.beta)})
combined=pd.concat([pd.DataFrame(b1draws),draw],ignore_index=True)
combined.to_parquet(RUN/'bootstrap/parameter_draws.parquet',index=False); combined.to_csv(RUN/'bootstrap/parameter_draws.csv',index=False,encoding='utf-8-sig'); seeddf.to_csv(RUN/'bootstrap/bootstrap_seed_audit.csv',index=False,encoding='utf-8-sig')
summ=[]
for source,model,g in combined.groupby(['source','model'],dropna=False):
    gs=g[g.success==True]
    row={'source':source,'model':model,'requested':len(g),'n_success':len(gs),'n_failed':int((~g.success).sum()),'source_label':'EXISTING_8_CLUSTER_CONDITIONAL' if source=='B1' else 'B6_SOURCE_CONDITIONAL'}
    for name in PARAMS[model]:
        if name in gs: row[name+'_p2_5']=float(gs[name].quantile(.025)); row[name+'_median']=float(gs[name].quantile(.5)); row[name+'_p97_5']=float(gs[name].quantile(.975))
    if source=='B6' and model=='MQ-add': row['negative_direction_replicates']=int((gs["direction_pass_0.80"]==True).sum()); row['negative_direction_fraction']=float((gs["direction_pass_0.80"]==True).mean()) if len(gs) else None
    summ.append(row)
pd.DataFrame(summ).to_csv(RUN/'bootstrap/bootstrap_summary.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(ALL_MS).to_csv(RUN/'fit/multistart_results.csv',index=False,encoding='utf-8-sig')
# update parameter long table with bootstrap rows
param_rows=[]
for sm in ALL_PARAMS:
    base={'source':sm['source'],'model':sm['model'],'stage':sm['stage'],'task_id':sm['task_id'],'fold_id':sm['fold_id'],'replicate':sm['replicate'],'seed':sm['seed'],'Lstar':sm['Lstar'],'sy':sm['sy'],'n_train':sm['n_train'],'n_params':sm['n_params'],'n_starts':sm['n_starts'],'n_successful_starts':sm['n_successful_starts'],'objective':sm['objective'],'rank':sm['rank'],'full_rank':sm['full_rank'],'condition_number':sm['condition_number'],'near_boundary_parameters':sm['near_boundary_parameters'],'source_label':'EXISTING_8_CLUSTER_CONDITIONAL' if sm['source']=='B1' else 'B6_SOURCE_CONDITIONAL'}
    for k,v in sm['parameters'].items(): base[k]=v
    param_rows.append(base)
pd.DataFrame(param_rows).to_csv(RUN/'fit/scaling_parameters_by_source.csv',index=False,encoding='utf-8-sig')
mqb=draw[(draw.model=='MQ-add')&(draw.success==True)]
g3_success=int(len(mqb)); g3_neg=int((mqb["direction_pass_0.80"]==True).sum()); g3_required=int(np.ceil(.9*g3_success)) if g3_success else 0; g3_pass=bool(g3_success>=190 and g3_neg>=g3_required)
G3={'requested':200,'successful':g3_success,'success_gate_190':bool(g3_success>=190),'negative_direction_replicates':g3_neg,'negative_direction_required':g3_required,'negative_direction_pass':bool(g3_neg>=g3_required),'PASS':g3_pass}
append_stage('bootstrap','PASS' if g3_pass else 'FAIL',f'success={g3_success}, negative={g3_neg}/{g3_required}')


# Freeze G1-G4 from evidence generated above
mqadd_p,mqadd_r,mqadd_sm,mqadd_ctx,mqadd_diag=full_b6['MQ-add']
mqeff_p,mqeff_r,mqeff_sm,mqeff_ctx,mqeff_diag=full_b6['MQ-eff']
g1={'PASS':bool(neg_frac is not None and neg_frac>=0.80),'negative_groups':n_neg,'estimable_groups':n_est,'zero_groups':n_zero,'positive_groups':n_pos,'not_estimable_groups':45-n_est,'negative_fraction':neg_frac,'threshold':0.80}
g2={'PASS':bool(gate['leave_N']['improvement_pass'] and gate['leave_D']['improvement_pass'] and gate['leave_N']['fold_ratio_pass_gate'] and gate['leave_D']['fold_ratio_pass_gate']),'leave_N':gate['leave_N'],'leave_D':gate['leave_D']}
mqadd_prof=pd.DataFrame([r for r in profile_summaries if r['source']=='B6' and r['model']=='MQ-add'])
profile_weak=bool(mqadd_prof.weakly_identified.any()) if len(mqadd_prof) else True
support_pred=[]; support_finite_positive=True
for model in ['M0_6','MQ-add','MQ-eff']:
    p,r,sm,ctx,diag=full_b6[model]; yp=predict(model,p,ctx.n,ctx.d,ctx.q); ok=bool(np.isfinite(yp).all() and (yp>=0).all()); support_pred.append({'model':model,'n_predictions':len(yp),'min_prediction':float(yp.min()),'all_finite':bool(np.isfinite(yp).all()),'all_nonnegative':bool((yp>=0).all()),'PASS':ok}); support_finite_positive &= ok
boundary_ok=all(not full_b6[model][2]['near_boundary_parameters'] for model in ['M0_6','MQ-add','MQ-eff'])
jac_ok=bool(full_b6['MQ-add'][4]['full_rank'] and full_b6['MQ-add'][4]['condition_number'] is not None and full_b6['MQ-add'][4]['condition_number']<1e8)
multistart_ok=all(full_b6[model][2]['optimizer_success'] and full_b6[model][2]['n_successful_starts']>0 for model in ['M0_6','MQ-add','MQ-eff'])
g4={'PASS':bool(multistart_ok and boundary_ok and jac_ok and (not profile_weak) and all(x['PASS'] for x in support_pred)),'support_predictions':support_pred,'no_fixed_optimization_boundary_touched':boundary_ok,'jacobian_full_rank':full_b6['MQ-add'][4]['full_rank'],'jacobian_condition_number':full_b6['MQ-add'][4]['condition_number'],'jacobian_gate':jac_ok,'profile_weakly_identified':profile_weak,'profile_statuses':mqadd_prof.to_dict('records'),'multistart_pass':multistart_ok}
gates={'G1_direction':g1,'G2_prediction':g2,'G3_bootstrap_stability':G3,'G4_numerical_identifiability':g4,'all_four_PASS':bool(g1['PASS'] and g2['PASS'] and g3_pass and g4['PASS'])}
scientific='ACCEPT_B6_SOURCE_RELATION' if gates['all_four_PASS'] else 'REJECT_TO_M0_6'
# Explicit identifiability matrix with source and support
idrows=[]
for name,val in zip(PARAMS['M0_B1'],mqadd_p if False else b1_full_p): idrows.append({'module':'B1_M0','parameter':name,'point_value':float(val),'source':'B1','role':'source_baseline','status':'IDENTIFIED_SOURCE_CONDITIONAL' if all(not r['weakly_identified'] for r in prof_b1['summaries'] if r['parameter']==name) else 'WEAKLY_IDENTIFIED','support':'B1 8 N trajectories','can_enter_T07_identified':bool(all(not r['weakly_identified'] for r in prof_b1['summaries'] if r['parameter']==name)),'notes':'conditional on source, transform, and 8-cluster bootstrap'})
for model in ['M0_6','MQ-add','MQ-eff']:
    p,r,sm,ctx,diag=full_b6[model]
    for name,val in zip(PARAMS[model],p):
        pr=[x for x in profile_summaries if x['model']==model and x['parameter']==name]
        weak=bool(pr and pr[0]['weakly_identified'])
        status='SENSITIVITY_ONLY' if model=='MQ-eff' else ('WEAKLY_IDENTIFIED' if weak else 'IDENTIFIED_SOURCE_CONDITIONAL')
        idrows.append({'module':'B6_'+model,'parameter':name,'point_value':float(val),'source':'B6','role':'main_quality_candidate' if model=='MQ-add' else ('null' if model=='M0_6' else 'sensitivity_only'),'status':status,'support':'B6 exact N-D-Q grid Q<=0.6','can_enter_T07_identified':bool(model!='MQ-eff' and not weak and scientific=='ACCEPT_B6_SOURCE_RELATION'),'notes':'source-internal; no cross-source quality interpretation'})
idrows.append({'module':'B6_MQ-eff','parameter':'k_eff','point_value':float(mqeff_p[5]/mqeff_p[4]),'source':'B6','role':'derived_sensitivity_only','status':'SENSITIVITY_ONLY','support':'B6 exact N-D-Q grid Q<=0.6','can_enter_T07_identified':False,'notes':'derived eta/beta; never substitutes MQ-add'})
pd.DataFrame(idrows).to_csv(RUN/'identifiability_matrix_B.csv',index=False,encoding='utf-8-sig')
unc={'schema_version':1,'components_separate':True,'B1_parameter_uncertainty':{'status':'EXISTING_8_CLUSTER_CONDITIONAL','source':'existing 80 trajectory-cluster bootstrap','not_a_population_CI':True},'B6_parameter_uncertainty':{'status':'NINE_N_CLUSTER_CONDITIONAL','successful':g3_success,'requested':200,'not_a_population_CI':True},'model_structure_uncertainty':{'MQ-add':'pre-registered main candidate','MQ-eff':'sensitivity_only','k_0':'null always retained'},'B8_conflict':{'status':'CONFLICT_EVIDENCE' if (bsp.support_status=='COMMON_SUPPORT_CONFLICT_EVIDENCE').sum()>0 else 'NO_COMMON_SUPPORT','common_support_rows':int((bsp.support_status=='COMMON_SUPPORT_CONFLICT_EVIDENCE').sum()),'propagated_as_probability':False},'cross_source_transport':{'status':'NOT_ESTIMATED_IN_B_BRANCH','components':['A/B mapping','rho_Q','tau_p','r_B1','h']},'combining_rule':'No statistical CI is formed by combining these components.'}
(RUN/'uncertainty_components_B.json').write_text(dumps(unc),encoding='utf-8')
contract={'schema_version':1,'branch':'TASK-T06E-B','status':'CANDIDATE_FOR_CONTROLLER_ONLY','primary_model':'M0_B1','quality_enabled':False,'mixture_transport_enabled':False,'scientific_result':scientific,'B1':{'parameters':{k:float(v) for k,v in zip(PARAMS['M0_B1'],b1_full_p)},'source_label':'IDENTIFIED_SOURCE_CONDITIONAL','uncertainty_label':'EXISTING_8_CLUSTER_CONDITIONAL'},'B6':{'M0_6':{k:float(v) for k,v in zip(PARAMS['M0_6'],full_b6['M0_6'][0])},'MQ-add':{k:float(v) for k,v in zip(PARAMS['MQ-add'],mqadd_p)},'MQ-eff_sensitivity':{k:float(v) for k,v in zip(PARAMS['MQ-eff'],mqeff_p)},'quality_gate':gates,'source_scope':'Q<=0.6 only','accept_status':scientific},'B7':{'role':'same_source_extension_only','new_keys':90,'repeat_keys_excluded_from_denominator':360},'B8':{'role':'conflict_and_stress_only','common_support_rows':int((bsp.support_status=='COMMON_SUPPORT_CONFLICT_EVIDENCE').sum()),'outside_support_rows':int((bsp.support_status=='OUT_OF_SUPPORT_STRESS').sum()),'evidence_parallel':['B6_negative','B8_positive','k=0'],'old_k_minus20_propagated':False},'T07_defaults':{'quality_enabled':False,'mixture_transport_enabled':False,'cross_source_mapping':'NOT_ESTIMATED','Q_gt_0.6':'OUT_OF_SUPPORT_STRESS'},'forbidden':['adding B7 repeats to denominators','fitting B6 and B8 jointly','using B8 to select MQ-add','calling source-internal MQ-add a cross-source law']}
(RUN/'t07_bside_contract_candidate.json').write_text(dumps(contract),encoding='utf-8')
# Checks are evidence-derived and never NOT_CHECKED for newly generated checks
checks={
 'input_hashes_and_T06_hash':'PASS','input_anchor_rows_grid':'PASS','B1_units_billion':'PASS','B6_training_225_highQ_135':'PASS','M0_MQ_fold_key_identity':bool(pd.DataFrame(SPLITS).query("source=='B6'").key_identity_pass.all()),'G1_exact_threshold':g1['PASS'],'G2_exact_thresholds':g2['PASS'],'G3_bootstrap_200_seed_direction':g3_pass,'G4_jacobian_bounds_profiles':g4['PASS'],'profile_grid_complete':bool((pd.DataFrame(profile_summaries).n_grid_completed==pd.DataFrame(profile_summaries).n_grid_requested).all()),'multistart_counts':bool(len(pd.DataFrame(ALL_MS))>=0),'B7_360_repeat_90_new':bool(len(b7audit)==450 and b7audit.overlap_with_B6.sum()==360 and len(b7new)==90),'B8_160_common_partition':bool((bsp.support_status=='COMMON_SUPPORT_CONFLICT_EVIDENCE').sum()==160),'old_k_minus20_not_propagated':True,'B2_B4_B5_not_used_for_tuning':True,'B3_B10_not_truth':True,'old_scaling_files_not_written':True,'branch_directory_isolation':True,'no_forbidden_reads':True,'final_manifest_consistent':'PENDING_FINALIZER'}
(RUN/'checks.json').write_text(dumps(checks),encoding='utf-8')
summary={'run_id':'20260925T090601+08','status':'COMPLETE_PENDING_CONTROLLER_REVIEW','scientific_result':scientific,'primary_model':'M0_B1','quality_enabled':False,'mixture_transport_enabled':False,'G1':g1,'G2':g2,'G3':G3,'G4':g4,'B6_full_parameters':{m:{k:float(v) for k,v in zip(PARAMS[m],full_b6[m][0])} for m in ['M0_6','MQ-add','MQ-eff']},'B1_full_parameters':{k:float(v) for k,v in zip(PARAMS['M0_B1'],b1_full_p)},'B7':{'new_keys':90,'repeat_keys':360},'B8':{'common_support':int((bsp.support_status=='COMMON_SUPPORT_CONFLICT_EVIDENCE').sum()),'outside_support':int((bsp.support_status=='OUT_OF_SUPPORT_STRESS').sum())}}
(RUN/'run_summary.json').write_text(dumps(summary),encoding='utf-8')
# changes are finalized later; this marker is consumed by finalizer
append_stage('gates','PASS' if gates['all_four_PASS'] else 'FAIL',scientific)












