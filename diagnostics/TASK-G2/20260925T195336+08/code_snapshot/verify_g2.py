from __future__ import annotations
import hashlib, json, math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from scipy import stats

RUN = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
TZ = ZoneInfo("Asia/Shanghai")
SEED = 20260925
NBOOT = 2000
BASE = ROOT / "F题/real_attachments/B_scaling_laws"
INTEG = ROOT / "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08"
P_RUN = ROOT / "diagnostics/TASK-T06E-P/20260925T075729+08"
T07_RUN = ROOT / "diagnostics/TASK-T07/20260925T113744+08"
T06_FREEZE = ROOT / "paper/T06_RESULT_FREEZE.md"
T07_FREEZE = ROOT / "paper/T07_RESULT_FREEZE.md"
FROZEN = {"E":1.6897975629820348,"A":0.3539803206065571,"B":1.2403055835426349,"alpha":0.339976581941082,"beta":0.2798781285468448}
K_ADD = 0.3544081081063713
Q_ANCHOR = 0.5695341857475174
SUPPORT_N = (0.070542, 11.965825)
SUPPORT_D = (0.134, 299.893)

def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def hash_tree(root: Path):
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    return [{"path":str(p.relative_to(ROOT)).replace("\\","/"),"bytes":p.stat().st_size,"sha256":sha256(p)} for p in files]

def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def close(a,b,tol=1e-12):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a)-float(b)) <= tol * max(1.0, abs(float(a)), abs(float(b)))

def pred_formula(n,d):
    return FROZEN["E"]+FROZEN["A"]*np.power(n,-FROZEN["alpha"])+FROZEN["B"]*np.power(d,-FROZEN["beta"])

def support_state(n,d):
    if not np.isfinite(n) or not np.isfinite(d) or n <= 0 or d <= 0:
        return "INVALID_N_OR_D"
    inn = SUPPORT_N[0] <= n <= SUPPORT_N[1]
    ind = SUPPORT_D[0] <= d <= SUPPORT_D[1]
    if inn and ind: return "IN_SUPPORT"
    if not inn and not ind: return "OUT_BOTH"
    if not inn: return "OUT_N"
    return "OUT_D"

def metric(y,p,relative=True):
    y=np.asarray(y,float); p=np.asarray(p,float)
    ok=np.isfinite(y)&np.isfinite(p); y=y[ok]; p=p[ok]; e=p-y
    d={"n":int(len(y))}
    for k,v in {"mean_actual":np.mean(y) if len(y) else None,"sd_actual":np.std(y,ddof=1) if len(y)>1 else None,
                "mean_prediction":np.mean(p) if len(p) else None,"rmse":np.sqrt(np.mean(e*e)) if len(e) else None,
                "mae":np.mean(np.abs(e)) if len(e) else None,"mean_error":np.mean(e) if len(e) else None,
                "median_error":np.median(e) if len(e) else None,"max_abs_error":np.max(np.abs(e)) if len(e) else None}.items():
        d[k]=float(v) if v is not None and np.isfinite(v) else None
    d["mean_absolute_relative_error"]=float(np.mean(np.abs(e/y))) if relative and len(y) and np.all(y>0) else None
    if len(y)>=5 and np.std(y)>0 and np.std(p)>0:
        rho,pv=stats.spearmanr(y,p); d["spearman"]=float(rho); d["spearman_pvalue"]=float(pv)
    else:
        d["spearman"]=None; d["spearman_pvalue"]=None
    return d

def bootstrap(y,p,g):
    y=np.asarray(y,float); p=np.asarray(p,float); g=np.asarray(g,dtype=object)
    ok=np.isfinite(y)&np.isfinite(p); y=y[ok]; p=p[ok]; g=g[ok]
    out={"bootstrap_requested":NBOOT,"bootstrap_success":0,"bootstrap_seed":SEED}
    for n in ["rmse","mae","mean_error","median_error"]:
        out[n+"_boot_lo"]=None; out[n+"_boot_hi"]=None
    ug=np.asarray(sorted(pd.unique(g)),dtype=object)
    if len(ug)<2:
        return out
    ix={x:np.flatnonzero(g==x) for x in ug}; rng=np.random.default_rng(SEED)
    vals={n:[] for n in ["rmse","mae","mean_error","median_error"]}
    for _ in range(NBOOT):
        draw=rng.choice(ug,size=len(ug),replace=True)
        ii=np.concatenate([ix[x] for x in draw]); yy=y[ii]; pp=p[ii]; ee=pp-yy
        vals["rmse"].append(np.sqrt(np.mean(ee*ee))); vals["mae"].append(np.mean(np.abs(ee)))
        vals["mean_error"].append(np.mean(ee)); vals["median_error"].append(np.median(ee))
    for n,v in vals.items():
        out[n+"_boot_lo"]=float(np.percentile(v,2.5)); out[n+"_boot_hi"]=float(np.percentile(v,97.5))
    out["bootstrap_success"]=NBOOT
    return out

checks=[]
def check(name,condition,detail=""):
    checks.append({"check":name,"pass":bool(condition),"detail":str(detail)})

contract=read_json(INTEG/"t07_model_contract.json")
for k,v in FROZEN.items():
    check("frozen_param_"+k, float(contract["primary_model"]["parameters"][k]) == v, contract["primary_model"]["parameters"][k])
check("k_add_frozen", float(contract["quality"]["MQ_add_B6"]["parameters"]["k_add"]) == K_ADD)
check("q_anchor_frozen", float(contract["quality"]["q_A_star"]) == Q_ANCHOR)

b2=pd.read_csv(BASE/"cerebras_training_log.csv")
traj=sorted((BASE/"training_trajectories").glob("*.csv"))
b3=pd.concat([pd.read_csv(p).assign(_f=p.name) for p in traj],ignore_index=True)
b4=pd.read_csv(BASE/"scaling_baseline.csv")
b5=pd.read_csv(BASE/"published_scaling_data.csv")
b9=pd.read_csv(BASE/"supplementary_large_models.csv")
b10=pd.read_csv(BASE/"supplementary_large_baseline.csv")
raw_frames=[]
def raw_frame(df,sid,cluster,loss,step=None,estimated=False):
    z=pd.DataFrame({"source_id":sid,"row_id":[f"{sid}:{i}" for i in range(len(df))],
                    "cluster_id":df[cluster].astype(str).to_numpy(),"N_B":df["N_params_B"].to_numpy(float),
                    "D_B":df["D_tokens_B"].to_numpy(float)})
    z["step"]=df[step].to_numpy(float) if step else np.nan
    z["actual_loss"]=np.nan if estimated or loss not in df.columns else df[loss].to_numpy(float)
    z["reference_estimated_loss"]=df[loss].to_numpy(float) if estimated else np.nan
    return z
raw_frames=[raw_frame(b2,"B2","run_id","val_loss","steps"),raw_frame(b3,"B3","_f","val_loss","step"),
            raw_frame(b4,"B4","family","val_loss"),raw_frame(b5,"B5","family","val_loss"),
            raw_frame(b9,"B9","model_name","N_params_B"),raw_frame(b10,"B10","family","val_loss",estimated=True)]
raw_frames[-2]["actual_loss"]=np.nan
raw=pd.concat(raw_frames,ignore_index=True)
out=pd.read_parquet(RUN/"validation_predictions.parquet")
key=["source_id","row_id"]
check("prediction_row_count",len(out)==5390,len(out))
check("prediction_row_keys_unique",not out.duplicated(key).any(),"source_id+row_id")
check("prediction_keys_match_raw",set(map(tuple,out[key].to_numpy()))==set(map(tuple,raw[key].to_numpy())))
merged=out.merge(raw,on=key,suffixes=("_out","_raw"),validate="one_to_one")
for c in ["N_B","D_B","actual_loss","reference_estimated_loss"]:
    check("roundtrip_"+c,np.allclose(merged[c+"_out"].to_numpy(float),merged[c+"_raw"].to_numpy(float),rtol=0,atol=0,equal_nan=True))
valid=np.isfinite(merged["N_B_raw"])&np.isfinite(merged["D_B_raw"])&(merged["N_B_raw"]>0)&(merged["D_B_raw"]>0)
expected=np.full(len(merged),np.nan)
expected[valid]=pred_formula(merged.loc[valid,"N_B_raw"],merged.loc[valid,"D_B_raw"])
check("prediction_recompute",np.allclose(merged["frozen_M0_B1_prediction"],expected,rtol=1e-14,atol=1e-14,equal_nan=True),
      float(np.nanmax(np.abs(merged["frozen_M0_B1_prediction"]-expected))))
ss=np.array([support_state(n,d) if ok else "INVALID_N_OR_D" for n,d,ok in zip(merged["N_B_raw"],merged["D_B_raw"],valid)],dtype=object)
check("support_status_recompute",(merged["support_status"].astype(str).to_numpy()==ss).all())
check("no_support_clipping",not merged["clipped_to_support"].astype(bool).any())
check("observed_error_identity",np.allclose(merged["observed_error"],merged["frozen_M0_B1_prediction"]-merged["actual_loss_out"],rtol=1e-14,atol=1e-14,equal_nan=True))
rel=np.where((merged["actual_loss_out"]>0)&merged["source_id"].isin(["B2","B3","B4","B5"]),np.abs(merged["frozen_M0_B1_prediction"]-merged["actual_loss_out"])/merged["actual_loss_out"],np.nan)
check("relative_error_formula",np.allclose(merged["absolute_relative_error"],rel,rtol=1e-14,atol=1e-14,equal_nan=True))
check("B10_not_truth",not merged.loc[merged.source_id.eq("B10"),"loss_is_ground_truth"].astype(bool).any())
check("B9_no_invented_loss",merged.loc[merged.source_id.eq("B9"),["actual_loss_out","reference_estimated_loss_out"]].isna().all().all())

metrics_pub=pd.read_csv(RUN/"validation_metrics_by_source.csv")
metric_rows=[]; mismatch=[]
for sid in ["B2","B3","B4","B5","B9","B10"]:
    d=out[out.source_id.eq(sid)].copy()
    if sid in {"B2","B3","B4","B5"}:
        subsets={"ALL_VALID":d.actual_loss.notna(),"IN_SUPPORT":d.actual_loss.notna()&d.in_B1_box,"OOS":d.actual_loss.notna()&d.oos_flag}
    elif sid=="B10":
        subsets={"ESTIMATED_REFERENCE_ALL":d.reference_estimated_loss.notna()&d.prediction_valid}
    else:
        subsets={"NO_OBSERVED_LOSS":pd.Series(False,index=d.index)}
    for name,mask in subsets.items():
        x=d.loc[mask]; y=x.actual_loss if sid!="B10" else x.reference_estimated_loss
        mv=metric(y.to_numpy(float),x.frozen_M0_B1_prediction.to_numpy(float),relative=sid in {"B2","B3","B4","B5"})
        bv=bootstrap(y.to_numpy(float),x.frozen_M0_B1_prediction.to_numpy(float),x.cluster_id.to_numpy(object)) if len(x) else {"bootstrap_success":0,"bootstrap_requested":NBOOT,"bootstrap_seed":SEED}
        row={"source_id":sid,"subset":name,**mv,**bv}; metric_rows.append(row)
        pub=metrics_pub[(metrics_pub.source_id==sid)&(metrics_pub.subset==name)]
        if len(pub)!=1:
            mismatch.append(f"missing published metric {sid}/{name}"); continue
        for c,v in row.items():
            if c in ["source_id","subset"] or v is None: continue
            if c not in pub.columns or not close(v,pub.iloc[0][c]):
                mismatch.append(f"{sid}/{name}/{c}: {v} != {pub.iloc[0].get(c)}")
pd.DataFrame(metric_rows).to_csv(RUN/"verification_metrics_recomputed.csv",index=False,encoding="utf-8-sig",float_format="%.17g")
check("metrics_and_cluster_bootstrap_match",not mismatch,"; ".join(mismatch[:20]))

support_pub=pd.read_csv(RUN/"support_oos_audit.csv")
large_pub=pd.read_csv(RUN/"large_model_gt10b_audit.csv")
support_bad=[]
for sid in ["B2","B3","B4","B5","B9","B10"]:
    d=out[out.source_id.eq(sid)]; n=d.N_B.to_numpy(float); dd=d.D_B.to_numpy(float)
    v=np.isfinite(n)&np.isfinite(dd)&(n>0)&(dd>0)
    inn=v&(n>=SUPPORT_N[0])&(n<=SUPPORT_N[1]); ind=v&(dd>=SUPPORT_D[0])&(dd<=SUPPORT_D[1])
    got={"source_id":sid,"raw_rows":len(d),"finite_positive_N_D_rows":int(v.sum()),"in_B1_box_rows":int((inn&ind).sum()),
         "out_by_N_rows":int(((~inn)&v).sum()),"out_by_D_rows":int(((~ind)&v).sum()),"out_both_rows":int(((~inn)&(~ind)&v).sum()),
         "invalid_N_or_D_rows":int((~v).sum()),"N_above_support":int((v&(n>SUPPORT_N[1])).sum()),
         "D_above_support":int((v&(dd>SUPPORT_D[1])).sum())}
    pub=support_pub[support_pub.source_id.eq(sid)].iloc[0]
    for k,x in got.items():
        if k=="source_id": continue
        if int(pub[k])!=x: support_bad.append(f"{sid}/{k}:{pub[k]}!={x}")
check("support_oos_counts_match",not support_bad,"; ".join(support_bad))
large_bad=[]
for sid in ["B9","B10"]:
    d=out[out.source_id.eq(sid)]; gt=d.N_B.gt(10); dd=d.D_B; ref=d.reference_estimated_loss
    pub=large_pub[large_pub.source_id.eq(sid)].iloc[0]
    got={"records_gt_10B":int(gt.sum()),"unique_model_families_gt_10B":int(d.loc[gt,"cluster_id"].nunique()),
         "D_available_records":int(dd.notna().sum()),"D_positive_records":int((dd>0).sum()),
         "D_zero_or_invalid_records":int((~np.isfinite(dd)|(dd<=0)).sum()),"loss_observed_records":0,
         "estimated_loss_records":int(ref.notna().sum()),"finite_frozen_prediction_records":int(d.prediction_valid.sum()),
         "inside_B1_box_records":int(d.in_B1_box.sum())}
    for k,x in got.items():
        if int(pub[k])!=x: large_bad.append(f"{sid}/{k}:{pub[k]}!={x}")
check("large_model_audit_counts_match",not large_bad,"; ".join(large_bad))
check("B9_no_truth_upgrade",large_pub.loc[large_pub.source_id.eq("B9"),"truth_status"].iloc[0]=="REPORTED_METADATA_NO_LOSS")
check("B10_no_truth_upgrade",large_pub.loc[large_pub.source_id.eq("B10"),"truth_status"].iloc[0]=="ESTIMATED_NOT_TRUTH")
check("above_10B_not_supported",not large_pub["M0_can_support_above_10B_inference"].astype(bool).any())

spec=read_json(RUN/"generalized_law_spec.json")
model=read_json(ROOT/"solution/outputs/mixture/model.json")
c=np.asarray(model["models"]["linear"]["coefficients"],float).mean(axis=0)
check("generalized_law_base_frozen",all(float(spec["L0_B1"]["parameters"][k])==v for k,v in FROZEN.items()))
check("generalized_law_k_add_frozen",float(spec["quality_module"]["k_add"])==K_ADD)
check("generalized_law_c_frozen",np.allclose(np.asarray(spec["mixture_module"]["c"],float),c,rtol=0,atol=1e-15))
check("generalized_law_p0_simplex",abs(float(np.sum(spec["mixture_module"]["p0"]))-1.0)<1e-15)
check("Q_p_not_independent",spec["joint_Q_p"]["independent_estimation_or_optimization_allowed"] is False)
we=spec["worked_example"]
n0=float(we["N_B"]); d0=float(we["D_B"]); L0=pred_formula(n0,d0)
dlN=-FROZEN["alpha"]*FROZEN["A"]*n0**(-FROZEN["alpha"]-1); dlD=-FROZEN["beta"]*FROZEN["B"]*d0**(-FROZEN["beta"]-1)
dlQ=-1.0*K_ADD*1.0
check("worked_L0",close(we["L0_B1"],L0))
check("worked_dLdN",close(we["dL_dN_B"],dlN))
check("worked_dLdD",close(we["dL_dD_B"],dlD))
check("worked_dLdQ",close(we["dL_dQ_A"],dlQ))
check("worked_hold_N",close(we["holding_Loss_dN_dQ"],-dlQ/dlN))
check("worked_hold_D",close(we["holding_Loss_dD_dQ"],-dlQ/dlD))
features=list(model["features"]); vv=np.zeros(17); vv[features.index("train_the_pile_github")]=1; vv[features.index("train_the_pile_arxiv")]=-1
check("worked_feasible_direction",close(we["v_sum"],0.0) and close(we["cT_v"],float(c@vv)))
for k,tau in [("directional_derivative_tau05",0.5),("directional_derivative_tau10",1.0),("directional_derivative_tau_minus10",-1.0)]:
    check("worked_"+k,close(we[k],tau*float(c@vv)))

qual_pub=pd.read_csv(RUN/"validation_metrics_by_source.csv")
final={sid:qual_pub[(qual_pub.source_id==sid)&(qual_pub.final_qualification.notna())].final_qualification.iloc[0] for sid in ["B2","B3","B4","B5","B9","B10"]}
expected_final={"B2":"VALIDATION_FAILED","B3":"VALIDATION_SUPPORTED","B4":"VALIDATION_FAILED","B5":"VALIDATION_FAILED","B9":"OOS_STRESS_ONLY","B10":"ESTIMATED_SCENARIO_ONLY"}
check("qualification_labels_match_gates",final==expected_final,json.dumps(final))
check("at_least_one_comparable_B2_or_B3",((final["B2"]!="NOT_COMPARABLE") or (final["B3"]!="NOT_COMPARABLE")) and final["B3"]=="VALIDATION_SUPPORTED")

imp=read_json(RUN/"t07_impact_decision.json")
check("T07_impact_exact_NO",imp["NEW_Q2_CHANGES_T07_NUMERIC_INPUTS"]=="NO")
check("T07_contract_hash_matches",imp["t07_contract_sha256"]==sha256(INTEG/"t07_model_contract.json"))
check("T07_freeze_hash_matches",imp["t07_freeze_sha256"]==sha256(T07_FREEZE))
check("T07_not_started",imp["incremental_t07_started_or_authorized"] is False)

before=read_json(RUN/"protected_old_artifacts_before.json")
protected_roots=[ROOT/"diagnostics/TASK-T06E-B-R1/20260925T103130+08",ROOT/"diagnostics/TASK-T06E-P/20260925T075729+08",
                 INTEG,T07_RUN,ROOT/"solution/outputs/scaling"]
after={}
for p in protected_roots: after[str(p.relative_to(ROOT)).replace("\\","/")]=hash_tree(p)
for p in [T06_FREEZE,T07_FREEZE]: after[str(p.relative_to(ROOT)).replace("\\","/")]=hash_tree(p)
write_json=json.dumps
(RUN/"protected_old_artifacts_after.json").write_text(json.dumps({"checked_at":datetime.now(TZ).isoformat(timespec="seconds"),"roots":after},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
check("protected_T06_T07_hashes_unchanged",after==before["roots"],"before/after full file hash trees")

run_src=(RUN/"code/run_g2.py").read_text(encoding="utf-8")
for token in ["scipy.optimize","curve_fit(","least_squares(",".fit(","minimize("]:
    check("no_fit_token_"+token.replace("(","_"),token not in run_src)
check("no_executor_import",not any(str(x).endswith("run_g2") for x in __import__("sys").modules))

pass_n=sum(c["pass"] for c in checks); fail_n=len(checks)-pass_n
verification={
    "schema_version":1,"run_id":RUN.name,"created_at":datetime.now(TZ).isoformat(timespec="seconds"),
    "verifier":"independent_verify_g2.py","imports_executor":False,"seed":SEED,"bootstrap_replicates":NBOOT,
    "summary":{"total":len(checks),"pass":pass_n,"fail":fail_n,"not_checked":0},
    "checks":checks,
    "scope":{
        "predictions_recomputed":int(len(out)),
        "raw_sources":["B2","B3","B4","B5","B9","B10"],
        "metrics_recomputed":"validation_metrics_by_source.csv including cluster bootstrap",
        "generalized_law":"worked analytic quantities and frozen coefficient vector recomputed",
        "protected_hashes":"full before/after hash trees for T06E, T06 freeze, T07 run and T07 freeze",
        "not_checked_by_verifier":["candidate paper text","final output_manifest.json"]
    }
}
(RUN/"verification.json").write_text(json.dumps(verification,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(verification["summary"],ensure_ascii=False))
if fail_n:
    raise SystemExit(2)



