from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path.cwd(); RUN=Path(r'diagnostics/TASK-T06E-B/20260925T100306+08')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def metric(pred,actual,w):
 pred=np.asarray(pred,float); actual=np.asarray(actual,float); w=np.asarray(w,float); w=w/w.sum(); e=pred-actual
 return {'n':len(e),'RMSE':float(np.sqrt(np.sum(w*e*e))),'MAE':float(np.sum(w*np.abs(e))),'bias_pred_minus_actual':float(np.sum(w*e))}
def gw(n,d):
 z=pd.DataFrame({'n':n,'d':d}); z['g']=z.groupby(['n','d']).ngroup(); w=np.zeros(len(z))
 for g in np.unique(z.g):
  i=np.flatnonzero(z.g.to_numpy()==g); w[i]=1/len(i)
 return w/w.sum()
def pred(model,p,n,d,q):
 E,A,B,al,be=p[:5]; base=E+A*np.power(n,-al)+B*np.power(d,-be)
 if model=='MQ-add': return base-p[5]*(q-.6)
 if model=='MQ-eff': return E+A*np.power(n,-al)+B*np.power(d*np.exp(-p[5]*(q-.6)),-be)
 return base
checks=[]; failures=[]
def ck(name,ok,detail=''):
 checks.append({'check':name,'status':'PASS' if ok else 'FAIL','detail':detail})
 if not ok: failures.append(name)
b1=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/pythia_training_log_existing.csv'); b6=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv'); b7=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment_expanded.csv'); b8=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment_large.csv')
k6=set(map(tuple,b6[['N_params_B','D_tokens_B','Q_score']].to_numpy())); k7=set(map(tuple,b7[['N_params_B','D_tokens_B','Q_score']].to_numpy())); k8=set(map(tuple,b8[['N_params_B','D_tokens_B','Q_score']].to_numpy()))
ck('raw_shapes',len(b1)==1176 and len(b6)==360 and len(b7)==450 and len(b8)==1704,(len(b1),len(b6),len(b7),len(b8))); ck('B6_support_partition',(b6.Q_score<=.6).sum()==225 and (b6.Q_score>.6).sum()==135); ck('B7_360_repeat_90_new',len(k6&k7)==360 and len(k7-k6)==90); ck('B8_160_common',len(k6&k8)==160)
man=json.loads((RUN/'input_manifest.json').read_text(encoding='utf-8')); ck('input_manifest_hashes',all(sha(ROOT/x['path'])==x['sha256'] for x in man['inputs']))
con=json.loads((RUN/'t07_bside_contract_candidate.json').read_text(encoding='utf-8')); p1=np.array([con['B1']['parameters'][k] for k in ['E','A','B','alpha','beta']],float); full={}
for m in ['M0_6','MQ-add','MQ-eff']: full[m]=np.array([con['B6'][('MQ-eff_sensitivity' if m=='MQ-eff' else m)][k] for k in (['E','A','B','alpha','beta'] if m=='M0_6' else (['E','A','B','alpha','beta','k_add'] if m=='MQ-add' else ['E','A','B','alpha','beta','eta']))],float)
b1p=pd.read_parquet(RUN/'fit/full_fit_predictions.parquet'); z=b1p[(b1p.source=='B1')&(b1p.model=='M0_B1')&(b1p.split=='full')]; expected=pred('M0_B1',p1,z.N_params_B.to_numpy(float),z.D_tokens_B.to_numpy(float),np.full(len(z),np.nan)); ck('B1_formula_predictions',float(np.max(np.abs(expected-z.prediction.values)))<=1e-10)
b6p=b1p; maxerr=0.0
for m in full:
 for role in ['in_sample']:
  z=b6p[(b6p.source=='B6')&(b6p.model==m)&(b6p.role==role)]
  if len(z): maxerr=max(maxerr,float(np.max(np.abs(pred(m,full[m],z.N_params_B.to_numpy(float),z.D_tokens_B.to_numpy(float),z.Q_score.to_numpy(float))-z.prediction.values))))
ck('B6_formula_predictions',maxerr<=2e-10,str(maxerr))
fprm=pd.read_csv(RUN/'fit/scaling_parameters_by_source.csv')
ferr=0.0
for _,rr in fprm[(fprm.source=='B6')&(fprm.stage.isin(['leave_N','leave_D']))].iterrows():
 m=rr.model; keys=['E','A','B','alpha','beta']+(['k_add'] if m=='MQ-add' else (['eta'] if m=='MQ-eff' else [])); pp=np.array([float(rr[k]) for k in keys]); z=b6p[(b6p.source=='B6')&(b6p.model==m)&(b6p.split==rr.stage)&(b6p.fold_id==rr.fold_id)]
 if len(z): ferr=max(ferr,float(np.max(np.abs(pred(m,pp,z.N_params_B.to_numpy(float),z.D_tokens_B.to_numpy(float),z.Q_score.to_numpy(float))-z.prediction.values))))
ck('B6_fold_parameter_formula_predictions',ferr<=2e-10,str(ferr))
slopes=[]
for (n,d),g in b6[b6.Q_score<=.6].groupby(['N_params_B','D_tokens_B']): slopes.append(float(np.polyfit(g.Q_score,g.val_loss,1)[0]))
ck('G1_recomputed',sum(s<0 for s in slopes)>=np.ceil(.8*len(slopes)),str(sum(s<0 for s in slopes))+'/'+str(len(slopes)))
vg=pd.read_csv(RUN/'validation/validation_by_group.csv'); g2_ok=True; g2_detail=[]
for split in ['leave_N','leave_D']:
 z=vg[(vg.source=='B6')&(vg.split==split)&(vg.fit_success==True)]; null=z[z.model=='M0_6'].set_index('fold_id').RMSE; cand=z[z.model=='MQ-add'].set_index('fold_id').RMSE; ids=sorted(set(null.index)&set(cand.index)); imp=(null.loc[ids].mean()-cand.loc[ids].mean())/null.loc[ids].mean(); ratio=sum(cand.loc[i]<=1.10*null.loc[i] for i in ids); req=int(np.ceil(.8*len(ids))); ok=imp>=.05 and ratio>=req; g2_ok &= ok; g2_detail.append({'split':split,'improvement':float(imp),'ratio_count':int(ratio),'required':req})
ck('G2_recomputed',g2_ok,json.dumps(g2_detail))
draw=pd.read_parquet(RUN/'bootstrap/parameter_draws.parquet'); aud=pd.read_csv(RUN/'bootstrap/bootstrap_seed_audit.csv'); mq=draw[(draw.source=='B6')&(draw.model=='MQ-add')&(draw.success==True)]; ns=len(mq); neg=int((mq['direction_pass_0.80']==True).sum()); req=int(np.ceil(.9*ns)); ck('G3_bootstrap',ns>=190 and neg>=req,str(ns)+'/'+str(neg)+'/'+str(req)); ck('bootstrap_seed_and_no_highQ',bool((aud.bootstrap_rng_seed==20260925).all() and (aud.max_Q<=.600000000001).all() and (aud.stress_Q_rows_included==0).all()))
prm=pd.read_csv(RUN/'fit/scaling_parameters_by_source.csv'); rr=prm[(prm.source=='B6')&(prm.model=='MQ-add')&(prm.stage=='full')].iloc[0]; L=float(rr.Lstar); sy=float(rr.sy); bt=b6[b6.Q_score<=.6]; n=bt.N_params_B.to_numpy(float); d=bt.D_tokens_B.to_numpy(float); y=bt.val_loss.to_numpy(float); q=bt.Q_score.to_numpy(float); w=gw(n,d); names=['E','A','B','alpha','beta','k_add']; scale=np.array([L,L,L,1,1,L]); x=np.log(np.array([full['MQ-add'][i]/(scale[i] if names[i] in ['E','A','B','k_add'] else 1) for i in range(6)]))
def residual(xx): return np.sqrt(w)*(pred('MQ-add',scale*np.exp(xx),n,d,q)-y)/sy
J=np.empty((len(y),6)); h=1e-5
for j in range(6):
 xp=x.copy(); xm=x.copy(); xp[j]+=h; xm[j]-=h; J[:,j]=(residual(xp)-residual(xm))/(2*h)
norms=np.linalg.norm(J,axis=0); s=np.linalg.svd(J/norms,compute_uv=False); cond=float(s[0]/s[-1]); jd=json.loads((RUN/'profiles/jacobian_matrices.json').read_text(encoding='utf-8'))['B6:MQ-add']; ck('G4_jacobian_finite_difference',np.all(np.isfinite(J)) and cond<1e8 and jd['full_rank'] and abs(cond-jd['condition_number'])/cond<1e-3,str(cond)+' vs '+str(jd['condition_number']))
ps=pd.read_csv(RUN/'profiles/profile_summary.csv'); accounted=((ps.n_grid_completed+ps.n_skipped)==ps.n_grid_requested).all(); weak_matches=((ps.weakly_identified==True)==((ps.n_skipped>0)|(ps.touches_fixed_hard_boundary==True)|(ps.unseparable_multiminima==True)|(ps.n_inside_set==0))).all(); ck('profile_grid_accounted_and_weakness_propagated',bool(accounted and weak_matches and len(ps)==22),str(len(ps)))
ba=pd.read_csv(RUN/'b7_extension/b7_overlap_audit.csv'); bn=pd.read_csv(RUN/'b7_extension/b7_new90_predictions.csv'); ck('B7_repeat_isolation',len(ba)==450 and ba.overlap_with_B6.sum()==360 and len(bn)==270 and set(bn.model)==set(full)); ck('B7_new_formula',max(float(np.max(np.abs(pred(r.model,full[r.model],np.array([r.N_params_B]),np.array([r.D_tokens_B]),np.array([r.Q_score]))[0]-r.prediction))) for r in bn.itertuples())<1e-10)
bsp=pd.read_csv(RUN/'b8_stress/b8_support_partition.csv'); bp=pd.read_csv(RUN/'b8_stress/b8_predictions.csv'); ck('B8_partition',(bsp.support_status=='COMMON_SUPPORT_CONFLICT_EVIDENCE').sum()==160 and (bsp.support_status=='OUT_OF_SUPPORT_STRESS').sum()==1544); ck('B8_no_old_k',not bp.old_k_minus20_used.any())
ch=json.loads((RUN/'checks.json').read_text(encoding='utf-8')); uns=any(str(v) in ('NOT_CHECKED','NOT_VERIFIABLE','PENDING_FINALIZER') for k,v in ch.items() if k!='final_manifest_consistent'); ck('checks_have_no_unresolved_critical',not uns)
ver={'status':'PASS' if not failures else 'FAIL','run_id':'20260925T100306+08','independent_verifier':True,'imports_fit_module':False,'failures':failures,'checks':checks}; (RUN/'verification.json').write_text(json.dumps(ver,ensure_ascii=False,indent=2),encoding='utf-8'); pd.DataFrame(checks).to_csv(RUN/'verification/verifier_checks.csv',index=False,encoding='utf-8-sig'); print(json.dumps(ver,ensure_ascii=False,indent=2))
if failures: sys.exit(1)






