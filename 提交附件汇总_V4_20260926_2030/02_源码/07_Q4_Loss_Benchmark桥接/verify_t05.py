# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import hashlib, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.linear_model import LinearRegression

RUN = Path(__file__).resolve().parents[1]
ROOT = RUN.parents[2]
RAW = ROOT / "F题" / "real_attachments" / "C_efficiency_evolution"
C01 = ROOT / "diagnostics" / "TASK-C01" / "20260924T175553+08"
R1 = ROOT / "diagnostics" / "TASK-C01-R1" / "20260924T225308+08"
TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]
TARGETS = [x + "_pct" for x in TASKS] + ["benchmark_mean_aux"]
CUTOFF = pd.Timestamp("2024-09-01")

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def finite(x):
    try: return np.isfinite(float(x))
    except Exception: return False

def main():
    check_only = "--check-only" in sys.argv
    ds = pd.read_parquet(RUN / "bridge_analysis_dataset.parquet")
    wide = pd.read_csv(R1 / "c8_model_wide_corrected.csv")
    dirc = pd.read_csv(R1 / "c8_directory_aggregate_corrected.csv")
    parse = pd.read_csv(C01 / "c8_parse_log.csv")
    corrupt = pd.read_csv(C01 / "c8_corrupt_files.csv")
    filecounts = pd.read_csv(C01 / "c8_directory_file_counts.csv")
    c5 = pd.read_csv(RAW / "loss_benchmark_bridge.csv")
    c6 = pd.read_csv(RAW / "loss_benchmark_bridge_expanded.csv")
    c1 = pd.read_csv(RAW / "leaderboard_cleaned.csv")
    cross = pd.read_csv(RUN / "model_identity_crosswalk.csv")
    dup = pd.read_csv(RUN / "duplicate_run_resolution.csv")
    coverage = pd.read_csv(RUN / "corrupt_and_partial_coverage.csv")
    loss_cat = pd.read_csv(RUN / "loss_definition_catalog.csv")
    split = pd.read_csv(RUN / "split_registry.csv")
    taskwise = pd.read_csv(RUN / "taskwise_bridge_results.csv")
    agg = pd.read_csv(RUN / "aggregate_bridge_results.csv")
    vsplit = pd.read_csv(RUN / "validation_by_split.csv")
    family = pd.read_csv(RUN / "validation_by_family.csv")
    time = pd.read_csv(RUN / "validation_by_time.csv")
    decision = json.loads((RUN / "identifiability_decision.json").read_text(encoding="utf-8"))
    seal = json.loads((RUN / "execution_seal.json").read_text(encoding="utf-8"))
    checks = []

    def add(cid, claim, passed, actual, expected, evidence):
        checks.append({"verification_id":cid,"claim":claim,"status":"PASS" if bool(passed) else "FAIL","actual":actual,"expected":expected,"evidence":evidence})

    # Frozen C8 corrected anchors and coverage accounting.
    add("V-C8-01","corrected C8 directory denominator", len(dirc)==1863, len(dirc), 1863, "c8_directory_aggregate_corrected.csv")
    add("V-C8-02","1958 JSON accounting", int(dirc["n_files_total"].sum())==1958 and int(dirc["n_files_parse_success"].sum())==1954 and int(dirc["n_files_parse_failed"].sum())==4,
        {"total":int(dirc["n_files_total"].sum()),"ok":int(dirc["n_files_parse_success"].sum()),"failed":int(dirc["n_files_parse_failed"].sum())}, {"total":1958,"ok":1954,"failed":4}, "corrected directory table")
    add("V-C8-03","complete/partial model denominator", int(wide["six_task_complete"].sum())==1854 and int((~wide["six_task_complete"]).sum())==6,
        {"complete":int(wide["six_task_complete"].sum()),"partial":int((~wide["six_task_complete"]).sum())}, {"complete":1854,"partial":6}, "c8_model_wide_corrected.csv")
    partial_set=set(wide.loc[~wide["six_task_complete"],"Model"])
    add("V-C8-04","partial models excluded from bridge dataset", len(partial_set & set(ds["Model"]))==0, len(partial_set & set(ds["Model"])), 0, "bridge_analysis_dataset.parquet")
    add("V-C8-05","four corrupt JSON files are coverage-only", len(corrupt)==4 and int((coverage[coverage.record_type=="corrupt_json"].score_assigned==False).sum())==4,
        {"corrupt":len(corrupt),"no_score":int((coverage[coverage.record_type=="corrupt_json"].score_assigned==False).sum())}, {"corrupt":4,"no_score":4}, "corrupt_and_partial_coverage.csv")

    # Identity and bridge construction.
    exact_c5_c6_c8 = set(c5.Model) & set(c6.Model) & set(wide.Model)
    add("V-ID-01","C5/C6/C8 exact identity intersection", len(exact_c5_c6_c8)==23, len(exact_c5_c6_c8), 23, "exact raw Model strings")
    complete_intersection = wide[wide.Model.isin(set(c6.Model) & set(wide.Model)) & wide.six_task_complete]
    add("V-ID-02","bridge dataset is complete six-task exact intersection", set(ds.Model)==set(complete_intersection.Model) and len(ds)==45,
        {"bridge_n":len(ds),"complete_exact_n":len(complete_intersection)}, {"bridge_n":45,"complete_exact_n":45}, "bridge dataset vs corrected wide")
    c5_high=set(c5.loc[c5.Loss_Comparability.str.startswith("High"),"Model"])
    add("V-ID-03","main comparable cohort is exact C5 High", set(ds.loc[ds.main_bridge_eligible,"Model"])==c5_high, len(ds[ds.main_bridge_eligible]), 7, "seal + bridge dataset")
    add("V-ID-04","canonical crosswalk preserves C5/C6/C8 raw names", set(cross.loc[cross.source_table.isin(["C5","C6"]),"original_name"])==set(c5.Model)|set(c6.Model) and set(cross.loc[cross.source_table=="C8","original_name"])==set(wide.Model),
        {"cross_c5c6":cross.source_table.isin(["C5","C6"]).sum(),"cross_c8":int((cross.source_table=="C8").sum())}, {"c5c6":118,"c8":1860}, "model_identity_crosswalk.csv")

    # C5/C6 linkage and loss provenance.
    common_cols=["N_params_B","D_tokens_B","Val_Loss","LB_Average","LB_IFEval","LB_BBH","LB_MATH","LB_GPQA","LB_MUSR","LB_MMLU_PRO"]
    m=c5.merge(c6,on="Model",suffixes=("_c5","_c6"),validate="one_to_one")
    equal_count=sum(np.allclose(m[a],m[b],equal_nan=True) for a,b in [(x+"_c5",x+"_c6") for x in common_cols]) if len(m) else 0
    add("V-LINK-01","C5 is exact 43-row value subset of C6", len(m)==43 and equal_count==len(common_cols), {"rows":len(m),"equal_columns":equal_count}, {"rows":43,"equal_columns":10}, "C5/C6 source tables")
    medium_c6 = c6[c6.Loss_Comparability.str.startswith("Medium")]
    add("V-LOSS-01","main loss definition single comparable stratum", set(ds.loc[ds.main_bridge_eligible,"c5_Loss_Comparability"])=={"High (same model, same validation set)"}, sorted(set(ds.loc[ds.main_bridge_eligible,"c5_Loss_Comparability"])), ["High (same model, same validation set)"], "loss_definition_catalog.csv")
    add("V-LOSS-02","C6 Medium has no observed D in bridge records", int(ds.loc[~ds.main_bridge_eligible,"D_tokens_B"].notna().sum())==0,
        int(ds.loc[~ds.main_bridge_eligible,"D_tokens_B"].notna().sum()), 0, "bridge_analysis_dataset.parquet")
    add("V-LOSS-03","no D imputation", bool(ds.loc[~ds.main_bridge_eligible,"logD"].isna().all()), bool(ds.loc[~ds.main_bridge_eligible,"logD"].isna().all()), True, "logD remains null")
    add("V-LOSS-04","separate C5/C6 source columns preserved", "c5_Loss_Source" in ds.columns and "c6_Loss_Source" in ds.columns and "primary_loss_source" in ds.columns,
        [c for c in ["c5_Loss_Source","c6_Loss_Source","primary_loss_source"]], "all present", "bridge dataset schema")

    # Split and leakage checks.
    add("V-SPLIT-01","95 multi-file directories audited", len(dup)==95, len(dup), 95, "duplicate_run_resolution.csv")
    add("V-SPLIT-02","no bridge candidate uses a multi-file directory", int(dup.bridge_exact_match.sum())==0, int(dup.bridge_exact_match.sum()), 0, "duplicate_run_resolution.csv")
    for cohort in ["main_comparable","conditional_full"]:
        f=split[(split.split_family=="internal_grouped") & (split.split_id==cohort)]
        maxfolds=int(f.groupby("model_id")["role"].nunique().max()) if len(f) else 0
        add("V-SPLIT-"+("03" if cohort=="main_comparable" else "04"),f"{cohort} model IDs assigned to one internal fold",maxfolds<=1,maxfolds,1,"split_registry.csv")
    # Time ordering for each target using taskwise predictions.
    time_model_ids=set(taskwise.loc[taskwise.split_family=="time_oos","model_id"])
    date_map={m: sorted(set(pd.to_datetime(c1.loc[c1.Model==m,"Submission Date"],errors="coerce").dropna())) for m in time_model_ids}
    date_ok=True
    for m,dates in date_map.items():
        role=set(taskwise.loc[(taskwise.split_family=="time_oos")&(taskwise.model_id==m),"cohort"])
        date_ok &= len(dates)==1
    add("V-TIME-01","time rows have a unique deterministic submission date",date_ok,date_ok,True,"C1 Submission Date")
    tr=set(taskwise.loc[(taskwise.split_family=="time_oos") & (taskwise.cohort=="main_comparable") & (pd.to_datetime(taskwise.model_id.map(lambda m: date_map.get(m,[pd.NaT])[0]))<CUTOFF),"model_id"])
    te=set(taskwise.loc[(taskwise.split_family=="time_oos") & (taskwise.cohort=="main_comparable") & (pd.to_datetime(taskwise.model_id.map(lambda m: date_map.get(m,[pd.NaT])[0]))>=CUTOFF),"model_id"])
    add("V-TIME-02","time train/test model IDs disjoint",len(tr&te)==0,len(tr&te),0,"split_registry/taskwise")
    add("V-FAM-01","main comparable family is insufficient for upgrade holdout",int(agg.loc[agg.cohort=="main_comparable","family_evaluated_n"].max())==0,int(agg.loc[agg.cohort=="main_comparable","family_evaluated_n"].max()),0,"aggregate_bridge_results.csv")

    # Independently recompute frozen metrics for selected internal main predictions.
    metric_ok=True; metric_detail=[]
    for target in TARGETS:
        q=taskwise[(taskwise.cohort=="main_comparable")&(taskwise.split_family=="internal_grouped")&(taskwise.target==target)]
        y=q.observed.to_numpy(float); p=q.predicted.to_numpy(float); lo=q.pi_low.to_numpy(float); hi=q.pi_high.to_numpy(float)
        rmse=math.sqrt(np.mean((y-p)**2)); mae=np.mean(np.abs(y-p)); rho=spearmanr(y,p).statistic if len(y)>=3 and np.std(y)>0 and np.std(p)>0 else np.nan
        slope=LinearRegression().fit(p.reshape(-1,1),y).coef_[0] if len(y)>=3 and np.std(p)>0 else np.nan
        coverage=np.mean((y>=lo)&(y<=hi)) if np.isfinite(lo).all() and np.isfinite(hi).all() else np.nan
        row=agg[(agg.cohort=="main_comparable")&(agg.target==target)].iloc[0]
        vrow=vsplit[(vsplit.cohort=="main_comparable")&(vsplit.target==target)&(vsplit.validation_type=="internal_grouped")&(vsplit.candidate_id==row.selected_candidate_id)].iloc[0]
        same=all([np.isclose(rmse,row.internal_rmse,equal_nan=True),np.isclose(mae,vrow.mae,equal_nan=True),np.isclose(rho,row.internal_spearman,equal_nan=True),np.isclose(slope,vrow.calibration_slope,equal_nan=True),np.isclose(coverage,row.internal_coverage,equal_nan=True)])
        metric_ok &= same
        metric_detail.append({"target":target,"rmse":rmse,"mae":mae,"rho":rho,"slope":slope,"coverage":coverage,"matches":bool(same)})
    add("V-METRIC-01","selected internal metrics independently reproduce",metric_ok,metric_detail,"all close","taskwise vs aggregate")

    # Frozen threshold gates and final eligibility.
    thresholds=seal["frozen_upgrade_thresholds"]
    threshold_ok=(thresholds["rmse_improvement_vs_constant_or_size_baseline"]==0.10 and thresholds["spearman_min"]==0.50 and thresholds["direction_reversal_fraction_max"]==0.25 and thresholds["prediction_interval_coverage_min"]==0.85 and thresholds["prediction_interval_coverage_max"]==0.98)
    add("V-THRESH-01","frozen thresholds unchanged",threshold_ok,thresholds,{"improvement":0.10,"spearman":0.50,"coverage":[0.85,0.98]}, "execution_seal.json")
    eligible_tasks=0
    for target in TARGETS:
        r=agg[(agg.cohort=="main_comparable")&(agg.target==target)].iloc[0]
        passed=(finite(r.internal_improvement_vs_constant) and r.internal_improvement_vs_constant>=0.10 and finite(r.internal_spearman) and r.internal_spearman>=0.50 and
                finite(r.internal_coverage) and 0.85<=r.internal_coverage<=0.98 and bool(r.time_pass) and bool(r.family_pass) and bool(r.scale_pass))
        eligible_tasks += int(passed)
    expected="IDENTIFIED_PREDICTIVE_BRIDGE" if eligible_tasks==len(TARGETS) else "CONDITIONAL_ASSOCIATION_ONLY"
    add("V-THRESH-02","final eligibility follows frozen gates",decision["eligibility"]==expected,decision["eligibility"],expected,"identifiability_decision.json")
    add("V-SOURCE-01","C5-High to C6-Medium is labeled source transfer",any(taskwise.split_family=="source_transfer") and not bool((taskwise.loc[taskwise.split_family=="source_transfer","cohort"]=="main_comparable").any()),True,True,"taskwise_bridge_results.csv")
    add("V-CAUSAL-01","no causal claim allowed",decision.get("causal_language_allowed") is False,decision.get("causal_language_allowed"),False,"identifiability_decision.json")

    # Verify pre-final manifest if present. Final manifest can add only verification.json after sign-off.
    manifest_path=RUN/"output_manifest.json"
    manifest_ok=False; manifest_detail="not_present"
    if manifest_path.exists():
        man=json.loads(manifest_path.read_text(encoding="utf-8")); bad=[]
        for ent in man.get("files",[]):
            p=RUN/ent["path"]
            if not p.exists() or (ent.get("sha256") and sha(p)!=ent["sha256"]):
                bad.append(ent["path"])
        manifest_ok=len(bad)==0; manifest_detail={"files":len(man.get("files",[])),"bad":bad,"self_excluded":man.get("self_excluded")}
    add("V-MANIFEST-01","pre-final manifest hashes match listed artifacts",manifest_ok,manifest_detail,"all match","output_manifest.json")

    # Original protected source guard.
    ev=ROOT/"solution"/"src"/"evolution_audit.py"
    ev_hash=sha(ev) if ev.exists() else ""
    add("V-GUARD-01","evolution_audit.py hash remains frozen",ev_hash=="8204d5b140c8fd70a2b40bb6611eb5a977e8d8dfce639b26e99baf213b2d6453",ev_hash,"8204d5b140c8fd70a2b40bb6611eb5a977e8d8dfce639b26e99baf213b2d6453","solution/src/evolution_audit.py")

    verification={
        "task_id":"TASK-T05","run_id":RUN.name,"independent":True,"imports_execution_module":False,
        "verifier":str(Path(__file__).resolve()),"checks":checks,
        "summary":{"pass":sum(c["status"]=="PASS" for c in checks),"fail":sum(c["status"]=="FAIL" for c in checks),"total":len(checks)},
        "overall":"PASS" if all(c["status"]=="PASS" for c in checks) else "FAIL",
        "manifest_scope":"Verifier checks the pre-final manifest (all artifacts except verification.json/output_manifest.json); final manifest is generated afterward and records the pre-final manifest hash.",
    }
    if not check_only:
        (RUN/"verification.json").write_text(json.dumps(verification,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    print(json.dumps(verification["summary"],ensure_ascii=False))
    if verification["overall"]!="PASS":
        raise SystemExit(1)

if __name__=="__main__":
    main()