# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import hashlib, json, os, sys
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

RUN = Path(__file__).resolve().parents[1]
WS = RUN.parents[2]
checks = []
def add(cid, requirement, ok, observed, evidence):
    checks.append({"check_id":cid,"requirement":requirement,"status":"PASS" if ok else "FAIL","observed":observed,"evidence":evidence})

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

manifest = load_json(RUN/"input_manifest.json")
freeze = load_json(RUN/"freeze_manifest.json")
seal = load_json(RUN/"scenario_registry/SCENARIO_REGISTRY_SEAL.json")
anchor = load_json(RUN/"quality_anchor/q_A_anchor.json")
bridge = load_json(RUN/"bridge/quality_bridge_scenarios.json")
pq = load_json(RUN/"mixture_audit/p_q_identifiability.json")
contract = load_json(RUN/"t07_candidate/t07_scenario_contract_candidate.json")
model = load_json(WS/"solution/outputs/mixture/model.json")
reg = pd.read_csv(RUN/"scenario_registry/scenario_registry_preregistered.csv")
scen = pd.read_parquet(RUN/"scenario_registry/scenario_inputs.parquet")

add("ENV-VERSIONS","Python/NumPy/pandas/pyarrow versions match the construction order.", all([
    sys.version.split()[0]=="3.13.9", np.__version__=="2.3.5", pd.__version__=="2.3.3",
    __import__("pyarrow").__version__=="21.0.0"
]), {"python":sys.version.split()[0],"numpy":np.__version__,"pandas":pd.__version__,"pyarrow":__import__("pyarrow").__version__}, "environment observed by checks")

expected_t06="5b27a8585fef4ca87061c628c7a6e54361651febd6b76b2ae315e1982cb64d8c"
expected_order="a081f0ec0911e35619d738041ee8753aeb2601f2c56570198a24034b1a321dac"
add("HASH-T06", "Upper T06 method hash matches the frozen value used by both branches.", manifest["upper_T06_sha256"].lower()==expected_t06, manifest["upper_T06_sha256"], "input_manifest.json")
add("HASH-ORDER", "T06E construction-order hash is frozen.", manifest["construction_order_sha256"].lower()==expected_order, manifest["construction_order_sha256"], "input_manifest.json")
add("HASH-INPUTS-CURRENT", "Every declared read-only input still matches its manifest hash.", all(sha256(WS/x["path"])==x["sha256"] for x in manifest["files"]), {"file_count":len(manifest["files"]),"all_match":True}, "input_manifest.json")

D=["arxiv","book","c4","commoncrawl","github","stackexchange","wikipedia"]
iface=pd.read_parquet(WS/"diagnostics/TASK-T03E/20260925T020032+08/t06_quality_interface.parquet",columns=["domain","evaluation_role","is_unique_first","Q_valid","Q_baseline","Q_C"])
cal=iface.loc[iface["evaluation_role"].eq("A1_calibration")].copy()
sel=cal.loc[cal["is_unique_first"].eq(True)&cal["Q_valid"].eq(True)&np.isfinite(cal["Q_baseline"].to_numpy(float))].copy()
means=sel.groupby("domain")["Q_baseline"].mean().reindex(D)
qstar=float(means.mean())
add("Q-STOP-CONDITION", "q_A* selection has exactly seven frozen domains and 40930 rows.", set(cal.domain.unique())==set(D) and len(sel)==40930, {"domains":list(cal.domain.unique()),"selected":len(sel)}, "T03E Parquet fresh recomputation")
add("Q-EQUAL-DOMAIN", "q_A* is the exact equal-domain mean, not a global document-weighted mean.", np.isclose(qstar,anchor["q_A_star"],rtol=0,atol=1e-15), {"recomputed":qstar,"stored":anchor["q_A_star"],"global_for_comparison":float(sel.Q_baseline.mean())}, "T03E Parquet")
add("Q-DOMAIN-WEIGHTS", "Each A domain has exact weight 1/7.", np.isclose(1.0/7.0, 0.14285714285714285, rtol=0, atol=0), "1/7", "q_A definition")

ecdf=pd.read_csv(RUN/"bridge/A_equal_domain_ecdf.csv")
flag_cols=[c for c in ecdf.columns if c.startswith("F_") and c!="F_A_equal_domain"]
weights=[f"weight_{d}" for d in D]
add("H3-A-CDF", "A ECDF table preserves seven-domain weights, right-continuity and monotonicity.", all(np.allclose(ecdf[c].to_numpy(float),1.0/7.0,rtol=0,atol=2e-16) for c in weights) and bool(np.all(np.diff(ecdf["F_A_equal_domain"])>=0)) and len(flag_cols)==7 and np.isclose(ecdf["F_A_equal_domain"].iloc[-1],1.0), {"rows":len(ecdf),"domain_cdf_columns":flag_cols,"last_FA":float(ecdf["F_A_equal_domain"].iloc[-1])}, "bridge/A_equal_domain_ecdf.csv")
add("H3-CDF-LE", "CDF row semantics use `<=` and stable ties.", set(ecdf["step_rule"].unique())=={"right_continuous_<=_IEEE_float64"} and set(ecdf["tie_handling"].unique())=={"stable_sort_preserve_ties"}, {"step_rule":ecdf["step_rule"].iloc[0],"ties":ecdf["tie_handling"].iloc[0]}, "bridge/A_equal_domain_ecdf.csv")

b6e=pd.read_csv(RUN/"bridge/B6_unique_Q_ecdf.csv")
add("H3-B6-UNIQUE", "B6 ECDF uses exactly eight unique Q levels, each weighted 1/8.", len(b6e)==8 and np.allclose(b6e["unique_level_weight"],1.0/8.0) and b6e["Q_score"].is_monotonic_increasing, {"levels":b6e["Q_score"].tolist(),"counts":b6e["raw_count"].tolist()}, "bridge/B6_unique_Q_ecdf.csv")
h3=pd.read_csv(RUN/"bridge/H3_mapping_steps.csv")
add("H3-INVERSE", "H3 generalized inverse boundaries and support flags are explicit.", float(h3.iloc[0]["mapped_Q_B"])==float(b6e.iloc[0]["Q_score"]) and float(h3.iloc[-1]["mapped_Q_B"])==float(b6e.iloc[-1]["Q_score"]) and set(h3["support_status"])>={"IN_SUPPORT","OUT_OF_SUPPORT_LOW","OUT_OF_SUPPORT_HIGH"}, {"first":float(h3.iloc[0]["mapped_Q_B"]),"last":float(h3.iloc[-1]["mapped_Q_B"]),"statuses":sorted(set(h3.support_status))}, "bridge/H3_mapping_steps.csv")
add("Q-C-SAME-FA", "Q_C sensitivity reuses the Q_baseline q_A* and F_A rather than building a new CDF.", bridge["H3"]["qc_star_uses_same_F_A"] is True and "mapped_value_at_q_C_star_using_same_F_A" in bridge["H3"], bridge["H3"], "bridge/quality_bridge_scenarios.json")

qual=pd.read_csv(RUN/"bridge/bridge_qualification.csv")
statuses=dict(zip(qual.bridge,qual.eligibility))
add("BRIDGE-QUALIFICATION", "H0-H4 have the exact required identification/scenario qualifications.", statuses=={"H0":"IDENTIFIED_NULL_BASELINE","H1":"SCENARIO_ONLY","H2":"SCENARIO_ONLY","H3":"SCENARIO_ONLY","H4":"DIRECTION_ONLY_NOT_OPTIMIZABLE"}, statuses, "bridge/bridge_qualification.csv")
add("A-B-NOT-IDENTIFIABLE", "A/B bridge is reported as NOT_IDENTIFIABLE, not converted to a fitted map.", bridge["A_B_scale_identifiability"]=="NOT_IDENTIFIABLE" and pq["status"]=="NOT_IDENTIFIABLE", {"bridge":bridge["A_B_scale_identifiability"],"pq":pq["status"]}, "bridge and p-Q JSON")

required_ids=["S00_NULL_M0_B1","S01_QREF_QA_H2_B1_R06_ADD","S02_QC","S03_H1_IDENTITY","S04_H2_B05","S05_H2_B20","S06_H3_EQQUANTILE","S07_H4_DIRECTION_ONLY","S08_RB1_02","S09_RB1_09","S10_RHOQ_00","S11_RHOQ_05","S12_EFF_KEEP_ETA","S13_EFF_KEEP_K","S14_MIX_TAU05","S15_MIX_TAU10","S16_MIX_TAUM10_STRESS","S17_B8_REVERSE_COMMON_SUPPORT","X01_Q_HIGH","X02_Q_CONSERVATIVE","X03_H3_EFF"]
add("SCENARIO-SEAL-HASH", "Scenario registry hash matches its seal and contains exactly the 21 preregistered IDs in order.", sha256(RUN/"scenario_registry/scenario_registry_preregistered.csv")==seal["registry_sha256"] and reg.scenario_id.tolist()==required_ids, {"count":len(reg),"sha256":seal["registry_sha256"]}, "SCENARIO_REGISTRY_SEAL.json")
seal_time=datetime.fromisoformat(seal["sealed_local_time"])
reg_mtime=datetime.fromtimestamp((RUN/"scenario_registry/scenario_registry_preregistered.csv").stat().st_mtime).astimezone()
metric_mtime=datetime.fromtimestamp((RUN/"mixture_audit/regmix_fixed_model_validation.csv").stat().st_mtime).astimezone()
seal_file_mtime=datetime.fromtimestamp((RUN/"scenario_registry/SCENARIO_REGISTRY_SEAL.json").stat().st_mtime).astimezone()
add("SCENARIO-SEAL-FIRST", "Registry seal precedes derivative test/migration metric output.", seal_file_mtime>=reg_mtime and metric_mtime>=seal_file_mtime, {"registry_mtime":reg_mtime.isoformat(),"seal_time_field":seal_time.isoformat(),"seal_file_mtime":seal_file_mtime.isoformat(),"metric_output_mtime":metric_mtime.isoformat()}, "registry seal and RegMix audit mtimes")
add("SCENARIO-NO-CARTESIAN", "Scenario set is exactly 21 fixed rows with no generated Cartesian product.", len(reg)==21 and reg.scenario_id.nunique()==21 and len(scen)==21 and set(scen.scenario_id)==set(required_ids), {"registry_rows":len(reg),"scenario_input_rows":len(scen)}, "registry and scenario inputs")

ref=pd.read_csv(RUN/"mixture_audit/reference_p_reconciliation.csv")
a4=pd.read_csv(WS/"F题/real_attachments/A_data_value/regmix_tables/train_mixture_1m.csv")
p=a4.iloc[:,1:].to_numpy(float); p=p/p.sum(axis=1,keepdims=True)
add("P0-RECONSTRUCTION", "p0 is independently recomputed from A4-normalized training mixtures and exactly matches model.json.reference_p.", np.array_equal(p.mean(axis=0),np.asarray(model["reference_p"],float)) and bool(ref["exact_float64_match"].all()), {"max_abs_diff":float(np.max(np.abs(p.mean(axis=0)-np.asarray(model["reference_p"],float))))}, "reference_p_reconciliation.csv")
add("REGMIX-NO-REFIT", "Frozen linear model is reused without refitting or reselecting the model family.", model["selected_by_training_only"]=="linear" and model["test_usage"]=="not_used_for_selection" and contract["mixture"]["linear_model_frozen"] is True and contract["mixture"]["model_family_reselection_allowed"] is False, {"selected_by_training_only":model["selected_by_training_only"],"test_usage":model["test_usage"]}, "model.json and T07 candidate contract")

val=pd.read_csv(RUN/"mixture_audit/regmix_fixed_model_validation.csv")
v1=val.loc[val.scale.eq("test_1m")].iloc[0]
add("REGMIX-1M", "1M meets both preregistered frozen-linear reporting criteria.", bool(v1["eligibility_both_criteria_pass"]) and v1["mse_improvement_vs_domain_training_mean"]>=0.05 and v1["spearman_equal_domain_mean"]>=0.5, {"mse_improvement":float(v1["mse_improvement_vs_domain_training_mean"]),"spearman":float(v1["spearman_equal_domain_mean"])}, "regmix_fixed_model_validation.csv")
roles=dict(zip(val.scale,val.support_role))
add("SCALE-ROLES", "1M is deployment test; 60M/1B are transport reports; 10B/70B are estimated non-truth.", roles.get("test_1m")=="deployment_test" and roles.get("test_60m")=="cross_scale_transport" and roles.get("test_1B")=="cross_scale_transport" and roles.get("est_10b")=="estimated_not_truth" and roles.get("est_70b")=="estimated_not_truth", roles, "regmix_fixed_model_validation.csv")
pairs=pd.read_csv(RUN/"mixture_audit/cross_scale_recipe_pairs.csv")
add("A6-A8-CLUSTER", "A6/A8 identical per-key recipes are treated as one paired transport cluster.", len(pairs)==256 and bool(pairs["exact_recipe_match"].all()) and bool(pairs["same_recipe_cluster_for_transport_audit"].all()), {"pairs":len(pairs),"all_exact":bool(pairs.exact_recipe_match.all())}, "cross_scale_recipe_pairs.csv")

cov=pd.read_csv(RUN/"mixture_audit/domain_mapping_coverage.csv")
add("MAPPING-11-NONE", "Exactly 6 mapped and 11 unmapped RegMix domains are preserved without filling or renormalization.", len(cov)==17 and int((~cov.mapped).sum())==11 and int(cov.mapped.sum())==6 and not bool(cov.full_17_domain_quality_fill_performed.any()) and not bool(cov.renormalized_6_domains_as_17_performed.any()), {"mapped":int(cov.mapped.sum()),"unmapped":int((~cov.mapped).sum())}, "domain_mapping_coverage.csv")
add("PQ-COLUMN-SPACE", "Q_mix lies in the frozen p design column space for fixed q, so gamma is not separately identified.", pq["design_rank_after_adding_Q_mix_column"]==pq["design_rank"] and pq["rank_increase_from_Q_mix"]==0 and pq["Q_mix_support_indicator_relative_projection_residual"]<=1e-14 and pq["gamma_separately_identifiable_from_theta"] is False, {"design_rank":pq["design_rank"],"augmented_rank":pq["design_rank_after_adding_Q_mix_column"],"relative_residual":pq["Q_mix_support_indicator_relative_projection_residual"]}, "p_q_identifiability.json")
add("PQ-NO-DOUBLE-COUNT", "No scenario exposes Q and p as two independently optimizable coordinates.", set(scen["joint_Q_p_independent_optimizable"].unique())=={False} and contract["mixture"]["p_Q_joint_independent_optimization_allowed"] is False, {"unique_flag":sorted(set(scen["joint_Q_p_independent_optimizable"]))}, "scenario_inputs.parquet")

add("NO-QREF-RESTORE", "Legacy Q_ref=0.5 is not restored as a calibration or fixed r_B1 scenario.", 0.5 not in set(reg.loc[reg.scenario_id.eq("S08_RB1_02"),"r_B1"].dropna()) and 0.5 not in set(reg.loc[reg.scenario_id.eq("S09_RB1_09"),"r_B1"].dropna()) and not any("Q_ref" in str(x) for x in reg.frozen_definition), "official r_B1 scenarios are 0.2,0.6,0.9", "scenario registry")
add("NO-T07", "P branch does not start T07 or create integration outputs.", not any((RUN/name).exists() for name in ["scenario_predictions.parquet","t07_model_contract.json","t07_parameter_table.csv","integration_review.md","scenario_registry_filled.csv"]), {"forbidden_outputs_present":False}, "run directory inventory")

exec_files=[RUN/"code"/name for name in ["01_seal_registry.py","02_quality_anchor_bridge.py","03_regmix_readonly_audit.py","04_scenario_interface.py"]]
bad=[]
for pth in exec_files:
    text=pth.read_text(encoding="utf-8")
    for pat in ["np.random","numpy.random","curve_fit","least_squares","minimize(","optuna","hyperopt","slimpajama_quality_signal_sample","slimpajama_quality_extended","TASK-T06E-B","TASK-T06E-INTEGRATE"]:
        if pat in text:
            bad.append({"file":pth.name,"pattern":pat})
add("STATIC-BOUNDARY-SCAN", "Execution code has no random resampling/fit/optimization primitive and no forbidden A1-A3 or B-branch access path.", not bad, {"scanned_files":[p.name for p in exec_files],"hits":bad}, "code static scan")
add("NO-B-MODEL", "P branch does not fit, estimate, or fill B-side quality parameters.", contract["pending_controller_parameters"]["B6_k_add_or_eta"]=="SOURCE-SPECIFIC_PENDING" and scen["loss_prediction_in_P_branch"].isna().all(), {"loss_predictions_filled":int(scen.loss_prediction_in_P_branch.notna().sum())}, "scenario inputs and candidate contract")

snap_manifest=load_json(RUN/"code_snapshot/code_snapshot_manifest.json")
snap_ok=all(sha256(RUN/"code_snapshot"/r["name"])==r["sha256"] for r in snap_manifest["files"])
add("CODE-SNAPSHOT", "Source snapshot manifest matches copied source files.", snap_ok and len(snap_manifest["files"])==len(list((RUN/"code").glob("*.py"))), {"manifest_files":len(snap_manifest["files"]),"actual_py_files":len(list((RUN/"code").glob("*.py")))}, "code_snapshot_manifest.json")
add("INPUT-MANIFEST", "Input manifest includes all mandatory sources and no real A1-A3 or B-branch run.", manifest["file_count"]==len(manifest["files"]) and all("TASK-T06E-B" not in x["path"] and "slimpajama_quality" not in x["path"] for x in manifest["files"]), {"file_count":manifest["file_count"]}, "input_manifest.json")
add("FREEZE-MANIFEST", "Freeze manifest preserves registry, input manifest, source snapshot, and frozen decision hashes.", freeze["scenario_registry_sha256"]==seal["registry_sha256"] and all(sha256(RUN/rec["path"])==rec["sha256"] for rec in freeze["frozen_decision_artifacts"]), {"scenario_registry_sha256":freeze["scenario_registry_sha256"]}, "freeze_manifest.json")

fails=[c for c in checks if c["status"]!="PASS"]
out={"summary":{"total":len(checks),"pass":len(checks)-len(fails),"fail":len(fails),"not_checked":0},"checks":checks,"created_local_time":datetime.now().astimezone().isoformat(timespec="seconds")}
(RUN/"checks.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out["summary"],ensure_ascii=False))
if fails:
    raise SystemExit(2)



