# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path.cwd(); RUN=Path(r'diagnostics/TASK-T06E-B-R1/20260925T103130+08'); OLD=Path(r'diagnostics/TASK-T06E-B/20260925T100306+08')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def weights(n,d):
 z=pd.DataFrame({'n':n,'d':d}); z['g']=z.groupby(['n','d']).ngroup(); w=np.zeros(len(z))
 for g in np.unique(z.g):
  i=np.flatnonzero(z.g.to_numpy()==g); w[i]=1/len(i)
 return w/w.sum()
def model_pred(model,p,n,d,q):
 E,A,B,al,be=p[:5]; base=E+A*np.power(n,-al)+B*np.power(d,-be)
 if model=='MQ-add': return base-p[5]*(q-.6)
 if model=='MQ-eff': return E+A*np.power(n,-al)+B*np.power(d*np.exp(-p[5]*(q-.6)),-be)
 return base
checks=[]; failures=[]
def ck(name,ok,detail=''):
 checks.append({'check':name,'status':'PASS' if ok else 'FAIL','detail':detail})
 if not ok: failures.append(name)
b1=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/pythia_training_log_existing.csv'); b6=pd.read_csv(ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv'); b6=b6[b6.Q_score<=.6].reset_index(drop=True)
pi=json.loads((RUN/'config/profile_inputs_frozen.json').read_text(encoding='utf-8')); grid=pd.read_csv(RUN/'corrected_profiles/profile_grid_corrected.csv'); summ=pd.read_csv(RUN/'corrected_profiles/profile_summary_corrected.csv'); repro=pd.read_csv(RUN/'corrected_profiles/full_point_reproduction.csv')
bad=[]
for (src,model,param),g in grid.groupby(['source','model','parameter'],sort=False):
 z=pi[src+':'+model]; names={'B1:M0_B1':['E','A','B','alpha','beta'],'B6:M0_6':['E','A','B','alpha','beta'],'B6:MQ-add':['E','A','B','alpha','beta','k_add'],'B6:MQ-eff':['E','A','B','alpha','beta','eta']}[src+':'+model]
 for _,r in g.iterrows():
  if r.skipped: continue
  tol=1e-12+1e-10*abs(r.fixed_value)
  if abs(r[param+'_conditional']-r.fixed_value)>tol: bad.append((src,model,param,'fixed/conditional'))
  pp=np.array([float(r[nm+'_conditional']) for nm in names],float)
  if src=='B1': n=b1.N_params_B.to_numpy(float); d=b1.D_tokens_B.to_numpy(float); y=b1.val_loss.to_numpy(float); q=np.full(len(b1),np.nan); w=np.ones(len(b1))/len(b1)
  else: n=b6.N_params_B.to_numpy(float); d=b6.D_tokens_B.to_numpy(float); y=b6.val_loss.to_numpy(float); q=b6.Q_score.to_numpy(float); w=weights(n,d)
  sse=float(np.sum(w*(model_pred(model,pp,n,d,q)-y)**2)/float(z['sy'])**2)
  if abs(sse-float(r.SSE))>1e-8*max(1,abs(sse)): bad.append((src,model,param,'SSE'))
ck('22_profiles_fixed_and_SSE_reconstructable',not bad,json.dumps(bad[:5]))
bad=[]
for _,r in repro.iterrows():
 tol=1e-12+1e-10*abs(r.full_value)
 if abs(r.conditional_value-r.fixed_value)>tol or abs(r.fixed_value-r.full_value)>tol or not r.inside_set or not (r.SSE_profile_at_full_point<=r.SSE_full*(1+1e-6)+1e-12): bad.append(r.to_dict())
ck('22_full_fit_points_reproduce',not bad,json.dumps(bad[:3])); ck('full_points_inside_set',len(summ)==22 and all(bool(s.full_point_in_inside_set) for _,s in summ.iterrows()),str(len(summ)))
# independent MQ-add Jacobian
z=pi['B6:MQ-add']; p=np.asarray(z['params'],float); n=b6.N_params_B.to_numpy(float); d=b6.D_tokens_B.to_numpy(float); y=b6.val_loss.to_numpy(float); q=b6.Q_score.to_numpy(float); w=weights(n,d); L=float(z['Lstar']); sy=float(z['sy']); names=['E','A','B','alpha','beta','k_add']; scale=np.array([L,L,L,1,1,L]); x0=np.log(p/scale)
def residual(x): return np.sqrt(w)*(model_pred('MQ-add',np.exp(x)*scale,n,d,q)-y)/sy
J=np.empty((len(b6),6)); h=1e-5
for j in range(6):
 xp=x0.copy(); xm=x0.copy(); xp[j]+=h; xm[j]-=h; J[:,j]=(residual(xp)-residual(xm))/(2*h)
norms=np.linalg.norm(J,axis=0); s=np.linalg.svd(J/norms,compute_uv=False); cond=float(s[0]/s[-1]); rank=int(np.sum(s/s[0]>1e-8)); predv=model_pred('MQ-add',p,n,d,q); g4=json.loads((RUN/'corrected_gates/G4_corrected.json').read_text(encoding='utf-8'))['G4']; ck('MQadd_G4_jacobian_independent',rank==6 and cond<1e8 and abs(cond-g4['condition_number'])/cond<1e-3,str(cond)+'/'+str(g4['condition_number'])); ck('MQadd_G4_prediction_boundary',bool(np.isfinite(predv).all() and (predv>=0).all() and not g4['near_boundary_parameters']))
ge=json.loads((RUN/'corrected_gates/G4_corrected.json').read_text(encoding='utf-8')); ck('MQeff_eta_boundary_separate',bool(ge['MQ_eff_boundary']['at_lower_bound'] and not ge['MQ_eff_boundary']['can_enter_MQ_add_G4'] and 'eta' not in [x['parameter'] for x in ge['G4']['profile_statuses']]))
orig=json.loads((OLD/'run_summary.json').read_text(encoding='utf-8')); rec=json.loads((RUN/'corrected_gates/G1_G4_reconciliation.json').read_text(encoding='utf-8')); ck('G1_G3_field_same',orig['G1']==rec['G1'] and orig['G2']==rec['G2'] and orig['G3']==rec['G3']); ck('G4_only_MQadd_profiles',set(x['parameter'] for x in g4['profile_statuses'])==set(['E','A','B','alpha','beta','k_add']) and g4['profile_pass']==all(s.status=='PROFILE_FINITE_AND_SEPARATED' for _,s in summ[(summ.source=='B6')&(summ.model=='MQ-add')].iterrows()))
final=bool(orig['G1']['PASS'] and orig['G2']['PASS'] and orig['G3']['PASS'] and g4['PASS']); ck('final_boolean',rec['all_four_PASS']==final and rec['scientific_result']==('ACCEPT_B6_SOURCE_RELATION' if final else 'REJECT_TO_M0_6'))
om=json.loads((OLD/'output_manifest.json').read_text(encoding='utf-8')); ck('original_run_unchanged',all((OLD/x['path']).exists() and (OLD/x['path']).stat().st_size==x['bytes'] and sha(OLD/x['path'])==x['sha256'] for x in om['files']))
req=['handoff.md','run_summary.json','input_manifest.json','protected_original_run_check.json','environment.json','command_log.json','stage_status.jsonl','changes.csv','corrected_profiles/profile_grid_corrected.csv','corrected_profiles/profile_summary_corrected.csv','corrected_profiles/profile_multistart_results.csv','corrected_profiles/full_point_reproduction.csv','corrected_gates/G4_corrected.json','corrected_gates/G1_G4_reconciliation.json','identifiability_matrix_B_corrected.csv','t07_bside_contract_candidate_corrected.json','checks.json']; ck('required_files_present',all((RUN/x).exists() for x in req),str([x for x in req if not (RUN/x).exists()]))
out={'status':'PASS' if not failures else 'FAIL','run_id':'20260925T103130+08','independent_verifier':True,'imports_executor':False,'failures':failures,'checks':checks}; (RUN/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); pd.DataFrame(checks).to_csv(RUN/'verification/verifier_checks.csv',index=False,encoding='utf-8-sig'); print(json.dumps(out,ensure_ascii=False,indent=2)); sys.exit(0 if not failures else 1)
