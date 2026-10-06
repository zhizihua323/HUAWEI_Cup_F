from __future__ import annotations
import hashlib, json, sys
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

RUN=Path(__file__).resolve().parents[1]
WS=RUN.parents[2]
checks=[]
def add(cid,ok,observed,method): checks.append({"check_id":cid,"status":"PASS" if ok else "FAIL","observed":observed,"method":method})
def sha256(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()
def read_csv_rt(path, **kwargs):
 kwargs.setdefault('float_precision','round_trip')
 return pd.read_csv(path, **kwargs)
def ranks(x):
 x=np.asarray(x,float); o=np.argsort(x,kind="stable"); r=np.empty(len(x),float); i=0
 while i<len(x):
  j=i+1
  while j<len(x) and x[o[j]]==x[o[i]]: j+=1
  r[o[i:j]]=0.5*((i+1)+j); i=j
 return r
def spear(x,y):
 rx,ry=ranks(x),ranks(y)
 return float(np.corrcoef(rx,ry)[0,1])

D=["arxiv","book","c4","commoncrawl","github","stackexchange","wikipedia"]
iface=pd.read_parquet(WS/"diagnostics/TASK-T03E/20260925T020032+08/t06_quality_interface.parquet",columns=["domain","evaluation_role","is_unique_first","Q_valid","Q_baseline","Q_C"])
sel=iface.loc[iface.evaluation_role.eq("A1_calibration") & iface.is_unique_first.eq(True) & iface.Q_valid.eq(True) & np.isfinite(iface.Q_baseline.to_numpy(float))].copy()
means=[float(sel.loc[sel.domain.eq(d),"Q_baseline"].mean()) for d in D]
qstar=float(np.mean(means)); anchor=json.loads((RUN/"quality_anchor/q_A_anchor.json").read_text(encoding="utf-8"))
add("V-Q-ANCHOR",len(sel)==40930 and np.isclose(qstar,anchor["q_A_star"],rtol=0,atol=1e-15),{"n":len(sel),"seven_domain_means":means,"q_A_star":qstar},"explicit seven-domain count formula on T03E Parquet")

arrays={d:np.sort(sel.loc[sel.domain.eq(d),"Q_baseline"].to_numpy(float),kind="stable") for d in D}
qgrid=np.unique(np.sort(sel.Q_baseline.to_numpy(float),kind="stable"))
fdom=np.vstack([np.searchsorted(arrays[d],qgrid,side="right").astype(float)/len(arrays[d]) for d in D])
fa=fdom.mean(axis=0)
stored=read_csv_rt(RUN/"bridge/A_equal_domain_ecdf.csv")
add("V-A-CDF",len(qgrid)==len(stored) and np.allclose(qgrid,stored.q.to_numpy(float),rtol=0,atol=1e-15) and np.allclose(fa,stored.F_A_equal_domain.to_numpy(float),rtol=0,atol=1e-15),{"rows":len(stored),"max_q_diff":float(np.max(np.abs(qgrid-stored.q.to_numpy(float)))),"max_fa_diff":float(np.max(np.abs(fa-stored.F_A_equal_domain.to_numpy(float))))},"explicit <= counts with side=right and 1/7 domain weights")

b6=read_csv_rt(WS/"F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv",usecols=["Q_score"])
bu=np.unique(np.sort(b6.Q_score.to_numpy(float),kind="stable")); fb=np.arange(1,len(bu)+1,dtype=float)/len(bu)
bstore=read_csv_rt(RUN/"bridge/B6_unique_Q_ecdf.csv")
add("V-B6-CDF",len(bu)==8 and np.array_equal(bu,bstore.Q_score.to_numpy(float)) and np.array_equal(fb,bstore.F_B.to_numpy(float)),{"levels":bu.tolist(),"weights":(fb-fb[0]).tolist()[:2]},"unique Q levels only; grid duplicates excluded from CDF")

qmin=float(qgrid.min()); qmax=float(qgrid.max())
def cdf_at(q):
 return 0.0 if q<qmin else (1.0 if q>qmax else float(fa[np.searchsorted(qgrid,q,side="right")-1]))
def h3_at(q):
 f=cdf_at(q); j=max(1,min(8,int(np.ceil(8.0*f)))); st="IN_SUPPORT" if qmin<=q<=qmax else ("OUT_OF_SUPPORT_LOW" if q<qmin else "OUT_OF_SUPPORT_HIGH")
 return float(bu[j-1]),st,st=="IN_SUPPORT"
h=read_csv_rt(RUN/"bridge/H3_mapping_steps.csv")
exp=[]
for _,r in h.iterrows():
    sk=str(r["source_kind"])
    if sk=="support_sentinel_low": exp.append((float(bu[0]),"OUT_OF_SUPPORT_LOW",False))
    elif sk=="support_sentinel_high": exp.append((float(bu[-1]),"OUT_OF_SUPPORT_HIGH",False))
    else: exp.append(h3_at(float(r["q"])))
ok=(np.array([float(x[0]) for x in exp])==h.mapped_Q_B.to_numpy(float)).all() and (np.array([x[1] for x in exp])==h.support_status.to_numpy()).all() and (np.array([bool(x[2]) for x in exp])==h.usable_for_numeric_prediction.to_numpy(bool)).all()
add("V-H3",ok,{"mapping_rows":len(h),"q_A_star_mapped":h3_at(qstar)[0]},"independent ceil(8F_A) inverse and support predicates")
bridge=json.loads((RUN/"bridge/quality_bridge_scenarios.json").read_text(encoding="utf-8")); qc=anchor["q_C_star_sensitivity"]; hqc=h3_at(qc)
add("V-QC-SAME-FA",np.isclose(bridge["H3"]["mapped_value_at_q_C_star_using_same_F_A"],hqc[0],rtol=0,atol=0) and bridge["H3"]["qc_star_uses_same_F_A"] is True,{"q_C_star":qc,"Q_B_from_same_F_A":hqc[0],"F_A_at_q_C_star":cdf_at(qc)},"F_A evaluated from Q_baseline CDF only")

model=json.loads((WS/"solution/outputs/mixture/model.json").read_text(encoding="utf-8")); coeff=np.asarray(model["models"]["linear"]["coefficients"],float)
a4=read_csv_rt(WS/"F题/real_attachments/A_data_value/regmix_tables/train_mixture_1m.csv"); p4=a4.iloc[:,1:].to_numpy(float); p4=p4/p4.sum(axis=1,keepdims=True)
add("V-P0",np.array_equal(p4.mean(axis=0),np.asarray(model["reference_p"],float)),{"max_abs_diff":float(np.max(np.abs(p4.mean(axis=0)-np.asarray(model["reference_p"],float))))},"A4 row normalization then column mean")

sets={"train_1m":("regmix_tables/train_mixture_1m.csv","regmix_tables/train_pile_loss_1m.csv","linear_train_1m_predictions.csv"),"test_1m":("regmix_tables/test_mixture_1m.csv","regmix_tables/test_pile_loss_1m.csv","linear_test_1m_predictions.csv"),"test_60m":("regmix_tables/test_mixture_60m.csv","regmix_tables/test_pile_loss_60m.csv","linear_test_60m_predictions.csv"),"test_1B":("regmix_tables/test_mixture_1B.csv","regmix_tables/test_pile_loss_1B.csv","linear_test_1B_predictions.csv"),"est_10b":("regmix_tables/est_mixture_10b.csv","regmix_tables/est_pile_loss_10b.csv","linear_est_10b_predictions.csv"),"est_70b":("regmix_tables/est_mixture_70b.csv","regmix_tables/est_pile_loss_70b.csv","linear_est_70b_predictions.csv")}
val=read_csv_rt(RUN/"mixture_audit/regmix_fixed_model_validation.csv").set_index("scale")
max_saved=0.0; max_metric=0.0; metrics_seen={}
for s,(mr,lr,pr) in sets.items():
 raw=read_csv_rt(WS/"F题/real_attachments/A_data_value"/mr); p=raw.iloc[:,1:].to_numpy(float); p=p/p.sum(axis=1,keepdims=True); pred=p@coeff.T
 saved=read_csv_rt(WS/"solution/outputs/mixture"/pr); sp=saved[[c for c in saved if c.startswith("pred_")]].to_numpy(float)
 max_saved=max(max_saved,float(np.max(np.abs(pred-sp))))
 loss=read_csv_rt(WS/"F题/real_attachments/A_data_value"/lr); y=loss.iloc[:,1:].to_numpy(float); pm=pred.mean(axis=1); om=y.mean(axis=1); rho=spear(om,pm); rmse=float(np.sqrt(np.mean((pm-om)**2))); metrics_seen[s]={"rmse":rmse,"spearman":rho}; max_metric=max(max_metric,abs(rmse-float(val.loc[s,"rmse_equal_domain_mean"])),abs(rho-float(val.loc[s,"spearman_equal_domain_mean"])))
add("V-REGMIX-PREDICTIONS",max_saved<=1e-12 and max_metric<=1e-12,{"max_saved_prediction_diff":max_saved,"max_metric_diff":max_metric,"metrics":metrics_seen},"direct p @ frozen coefficient transpose; independent rank averages")

mp=read_csv_rt(RUN/"mixture_audit/domain_mapping_coverage.csv"); qi=np.zeros(17,float); qi[mp.index[mp.mapped].to_numpy(int)]=1.0; qmix=p4@qi
u,sv,_=np.linalg.svd(p4,full_matrices=False); tol=np.finfo(float).eps*max(p4.shape)*sv[0]; r=int((sv>tol).sum()); proj=u[:,:r]@(u[:,:r].T@qmix); rel=float(np.linalg.norm(qmix-proj)/np.linalg.norm(qmix)); rank_aug=int(np.linalg.matrix_rank(np.column_stack([p4,qmix]),tol=tol))
add("V-PQ",rank_aug==r and rel<=1e-14,{"rank":r,"augmented_rank":rank_aug,"relative_residual":rel},"numpy.linalg.svd projection and rank")

seal=json.loads((RUN/"scenario_registry/SCENARIO_REGISTRY_SEAL.json").read_text(encoding="utf-8")); regpath=RUN/"scenario_registry/scenario_registry_preregistered.csv"; scen=pd.read_parquet(RUN/"scenario_registry/scenario_inputs.parquet")
ids=seal["scenario_ids_in_order"]
add("V-SCENARIOS",sha256(regpath)==seal["registry_sha256"] and len(ids)==21 and read_csv_rt(regpath).scenario_id.tolist()==ids and scen.scenario_id.tolist()==ids and scen.loss_prediction_in_P_branch.isna().all() and not scen.joint_Q_p_independent_optimizable.any(),{"scenario_count":len(ids),"numeric_loss_filled":int(scen.loss_prediction_in_P_branch.notna().sum())},"registry hash, ID order, and scenario-input slot audit")

manifest=json.loads((RUN/"input_manifest.json").read_text(encoding="utf-8")); snap=json.loads((RUN/"code_snapshot/code_snapshot_manifest.json").read_text(encoding="utf-8")); freeze=json.loads((RUN/"freeze_manifest.json").read_text(encoding="utf-8"))
input_ok=all(sha256(WS/x["path"])==x["sha256"] for x in manifest["files"]); snap_ok=all(sha256(RUN/"code_snapshot"/x["name"])==x["sha256"] for x in snap["files"]); freeze_ok=freeze["input_manifest_sha256"]==sha256(RUN/"input_manifest.json") and freeze["source_snapshot_manifest_sha256"]==sha256(RUN/"code_snapshot/code_snapshot_manifest.json")
add("V-MANIFEST-SNAPSHOT",input_ok and snap_ok and freeze_ok,{"input_hashes_match":input_ok,"snapshot_hashes_match":snap_ok,"freeze_links_match":freeze_ok},"independent SHA256 verification; final output manifest read-back happens after finalization")
add("V-NO-B-READ",all("TASK-T06E-B" not in x["path"] and "slimpajama_quality" not in x["path"] for x in manifest["files"]),{"declared_inputs":len(manifest["files"])},"input manifest path audit")
checks_out=json.loads((RUN/"checks.json").read_text(encoding="utf-8")); add("V-CHECKS-ZERO-FAIL",checks_out["summary"]["fail"]==0 and checks_out["summary"]["not_checked"]==0,checks_out["summary"],"read checks.json summary")

fails=[x for x in checks if x["status"]!="PASS"]
out={"verifier":"independent_standalone_no_execution_module_import","summary":{"total":len(checks),"pass":len(checks)-len(fails),"fail":len(fails),"not_checked":0},"checks":checks,"created_local_time":datetime.now().astimezone().isoformat(timespec="seconds")}
(RUN/"verification.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out["summary"],ensure_ascii=False))
if fails: raise SystemExit(2)





