# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import csv, hashlib, json, platform, sys
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow

RUN=Path(__file__).resolve().parents[1]
WS=RUN.parents[2]

def sha256(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def dump(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def ts(path): return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")

env={"python":sys.version.split()[0],"python_executable":sys.executable,"numpy":np.__version__,"pandas":pd.__version__,"pyarrow":pyarrow.__version__,"platform":platform.platform(),"exact_required_versions":{"python":"3.13.9","numpy":"2.3.5","pandas":"2.3.3","pyarrow":"21.0.0"},"version_check":"PASS" if (sys.version.split()[0],np.__version__,pd.__version__,pyarrow.__version__)==("3.13.9","2.3.5","2.3.3","21.0.0") else "FAIL"}
dump(RUN/"environment.json",env)
if env["version_check"]!="PASS": raise SystemExit(2)

anchor=load(RUN/"quality_anchor/q_A_anchor.json")
bridge=load(RUN/"bridge/quality_bridge_scenarios.json")
pq=load(RUN/"mixture_audit/p_q_identifiability.json")
val=pd.read_csv(RUN/"mixture_audit/regmix_fixed_model_validation.csv").set_index("scale")
reg=pd.read_csv(RUN/"scenario_registry/scenario_registry_preregistered.csv")
scen=pd.read_parquet(RUN/"scenario_registry/scenario_inputs.parquet")
checks=load(RUN/"checks.json"); ver=load(RUN/"verification.json")
if checks["summary"]["fail"]!=0 or ver["summary"]["fail"]!=0: raise SystemExit(2)

seal_time=load(RUN/"scenario_registry/SCENARIO_REGISTRY_SEAL.json")["sealed_local_time"]
metrics_read_time=ts(RUN/"mixture_audit/regmix_fixed_model_validation.csv")
stage_lines=[
 {"stage":"scenario_registry_sealed","status":"PASS","time":seal_time,"test_or_migration_metric_read":False},
 {"stage":"quality_anchor_and_H3_bridge","status":"PASS","time":ts(RUN/"bridge/quality_bridge_scenarios.json"),"test_or_migration_metric_read":False},
 {"stage":"regmix_test_and_transport_audit","status":"PASS","time":metrics_read_time,"test_or_migration_metric_read":True,"seal_preceded_this_stage":True},
 {"stage":"scenario_interface","status":"PASS","time":ts(RUN/"scenario_registry/scenario_inputs.parquet"),"test_or_migration_metric_read":True},
 {"stage":"checks","status":"PASS","time":ts(RUN/"checks.json"),"test_or_migration_metric_read":True},
 {"stage":"independent_verification","status":"PASS","time":ts(RUN/"verification.json"),"test_or_migration_metric_read":True},
 {"stage":"finalization","status":"PASS","time":datetime.now().astimezone().isoformat(timespec="seconds"),"test_or_migration_metric_read":True},
]
with (RUN/"stage_status.jsonl").open("w",encoding="utf-8",newline="") as f:
 for x in stage_lines: f.write(json.dumps(x,ensure_ascii=False)+"\n")

command_log={"run_id":RUN.name,"command_environment":"PowerShell, non-login","commands":[
 {"sequence":1,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/01_seal_registry.py","attempt":1,"status":"FAILED_BEFORE_SEAL_DUE_INTERNAL_INDEX_ERROR","test_or_migration_metric_read":False},
 {"sequence":2,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/01_seal_registry.py","attempt":2,"status":"SUCCESS_REGISTRY_SEALED","test_or_migration_metric_read":False,"seal_time":seal_time},
 {"sequence":3,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/02_quality_anchor_bridge.py","attempt":1,"status":"FAILED_AT_CDF_ENDPOINT_ASSERTION_BEFORE_OUTPUT_FREEZE","test_or_migration_metric_read":False},
 {"sequence":4,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/02_quality_anchor_bridge.py","attempt":2,"status":"SUCCESS","test_or_migration_metric_read":False},
 {"sequence":5,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/03_regmix_readonly_audit.py","attempt":1,"status":"FAILED_AT_MAPPING_DOMAIN_NAME_ASSERTION","test_or_migration_metric_read":True},
 {"sequence":6,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/03_regmix_readonly_audit.py","attempt":2,"status":"SUCCESS","test_or_migration_metric_read":True},
 {"sequence":7,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/04_scenario_interface.py","attempt":1,"status":"SUCCESS","test_or_migration_metric_read":True},
 {"sequence":8,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/05_prepare_manifests.py","attempt":1,"status":"SUCCESS","test_or_migration_metric_read":True},
 {"sequence":9,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/06_checks.py","attempt":1,"status":"SUCCESS","test_or_migration_metric_read":True},
 {"sequence":10,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/07_independent_verifier.py","attempt":1,"status":"SUCCESS","test_or_migration_metric_read":True},
 {"sequence":11,"command":"python -X utf8 diagnostics/TASK-T06E-P/20260925T075729+08/code/08_finalize.py","attempt":1,"status":"RUNNING_THEN_LAST_WRITE_OUTPUT_MANIFEST","test_or_migration_metric_read":True}
],"failed_attempts_preserved":True,"scenario_seal_before_test_metric_read":True,"random_sampling_used":False,"B_branch_run_read":False,"real_A1_A3_read":False,"RegMix_refit":False,"T07_started":False,"integration_started":False}
dump(RUN/"command_log.json",command_log)

v1=val.loc["test_1m"]
run_summary={
 "task_id":"TASK-T06E-P","run_id":RUN.name,"status":"COMPLETE_PENDING_CONTROLLER_REVIEW","scientific_upgrade_decision":"PENDING_CONTROLLER",
 "scenario_registry":{"count":len(reg),"sha256":load(RUN/"scenario_registry/SCENARIO_REGISTRY_SEAL.json")["registry_sha256"],"sealed_before_metric_read":True},
 "quality_anchor":{"selected_rows":anchor["selected_total"],"q_A_star":anchor["q_A_star"],"q_C_star_sensitivity":anchor["q_C_star_sensitivity"],"A_B_mapping":"NOT_IDENTIFIABLE"},
 "H3":{"q_A_star_mapped_Q_B":bridge["H3"]["mapped_value_at_q_A_star"],"q_A_star_support":bridge["H3"]["q_A_star_support_status"],"Q_C_uses_same_F_A":True},
 "regmix":{"selected_by_training_only":"linear","test_1m_mse_improvement":float(v1["mse_improvement_vs_domain_training_mean"]),"test_1m_spearman":float(v1["spearman_equal_domain_mean"]),"test_1m_both_criteria_pass":bool(v1["eligibility_both_criteria_pass"]),"60m_1B_role":"cross_scale_transport_report_only","10B_70B_role":"estimated_not_truth"},
 "p_Q_double_counting":{"status":pq["status"],"design_rank":pq["design_rank"],"augmented_rank":pq["design_rank_after_adding_Q_mix_column"],"relative_projection_residual":pq["Q_mix_support_indicator_relative_projection_residual"]},
 "scenario_interface":{"rows":len(scen),"numeric_loss_values_filled":int(scen.loss_prediction_in_P_branch.notna().sum()),"joint_Q_p_independent_optimizable":int(scen.joint_Q_p_independent_optimizable.sum())},
 "checks_summary":checks["summary"],"verification_summary":ver["summary"],
 "boundaries":{"real_A1_A3_read":False,"TASK_T06E_B_run_read":False,"B_model_fitted":False,"RegMix_refit":False,"T07_started":False,"integration_started":False},
 "next_action":"Controller must independently review B and P branches before any integration; this run does not declare a scientific acceptance."
}
dump(RUN/"run_summary.json",run_summary)

handoff=f"""# TASK-T06E-P handoff

**Status: COMPLETE_PENDING_CONTROLLER_REVIEW**

## 1. Execution identity

- run_id: `{RUN.name}`
- solver: `NONE`
- seed audit anchor: `20260927`; no random sampling or random optimization was consumed.
- scenario registry was sealed before any 1M/60M/1B test or migration metric was read.

## 2. Quality anchor and H3 bridge

- Selection: `evaluation_role=A1_calibration`, `is_unique_first=True`, `Q_valid=True`, finite `Q_baseline`.
- Selected rows: `{anchor['selected_total']}`; exact seven-domain set maintained.
- `q_A* = {anchor['q_A_star']}` as the equal-weight mean of seven domain means.
- `q_C* = {anchor['q_C_star_sensitivity']}` for paired sensitivity only.
- H3 maps `q_A*` to B6 Q level `{bridge['H3']['mapped_value_at_q_A_star']}` with support `{bridge['H3']['q_A_star_support_status']}`.
- H1-H4 remain scenario/direction constructs. The A/B mapping remains `NOT_IDENTIFIABLE`; no map was fit.

## 3. Frozen RegMix audit

- `model.json.reference_p` is exactly reproduced as the mean of A4-normalized training mixtures.
- Frozen linear coefficients were reused without refitting or family reselection.
- 1M: equal-domain MSE improvement `{v1['mse_improvement_vs_domain_training_mean']:.12f}`; equal-domain mean-Loss Spearman `{v1['spearman_equal_domain_mean']:.12f}`; both preregistered reporting criteria pass.
- 60M and 1B are reported as cross-scale transport only. 10B and 70B remain estimated non-truth scenarios.
- A6 and A8 form the same 256-row paired recipe cluster.
- 6 RegMix domains are mapped and 11 remain `UNMAPPED`; no fill and no 6-to-17 renormalization occurred.

## 4. p-Q identification

- The symbolic identity `theta^T p + gamma Q_mix = (theta + gamma q)^T p` holds for fixed q.
- Adding the algebraic `Q_mix` support column does not increase design rank.
- `gamma` is not separately identifiable from p coefficients. T07 may not expose Q and p as two independent optimization coordinates without a fixed-p quality intervention.

## 5. Scenario interface

- Exactly 21 preregistered scenario IDs are present; no Cartesian product was generated.
- `scenario_inputs.parquet` contains mapped quality, support state, `Delta_p` state, and parameter slots only.
- No B-side parameter or joint Loss value was filled by P.
- S07 and S17 remain `NO_NUMERIC_PREDICTION`.

## 6. Checks and independent verification

- checks: `{checks['summary']}`
- independent verifier: `{ver['summary']}`
- Code snapshot and all declared input hashes are frozen before checks/verification.
- `output_manifest.json` is generated last and read back without rewriting any registered file.

## 7. Boundaries

- Real A1-A3 were not read.
- TASK-T06E-B new runs were not read.
- No B-side model was fitted.
- No RegMix refit or quadratic reselection occurred.
- T07 was not started and no integration was performed.
- The `M0_B1` default remains `quality_enabled=false` and `mixture_transport_enabled=false`.

## 8. Controller handoff

This is a candidate P-side evidence package only. Scientific acceptance, B/P integration, and any T07 contract remain pending controller review.
"""
(RUN/"handoff.md").write_text(handoff,encoding="utf-8")

# Changes inventory is complete before the final output manifest.
files=[p for p in RUN.rglob("*") if p.is_file() and p.name!="output_manifest.json"]
with (RUN/"changes.csv").open("w",encoding="utf-8",newline="") as f:
 w=csv.writer(f); w.writerow(["path","action","scope","old_artifact_modified"])
 for p in sorted(files,key=lambda x:str(x.relative_to(RUN)).lower()): w.writerow([str(p.relative_to(RUN)).replace("\\","/"),"CREATED_OR_UPDATED_IN_RUN",'diagnostics/TASK-T06E-P/'+RUN.name,False])
 w.writerow(["output_manifest.json","GENERATED_LAST",'diagnostics/TASK-T06E-P/'+RUN.name,False])

# Verify all pre-manifest outputs that were in the intended inventory, then manifest every file except itself.
files=[p for p in RUN.rglob("*") if p.is_file() and p.name!="output_manifest.json"]
rows=[]; groups={}
for p in sorted(files,key=lambda x:str(x.relative_to(RUN)).lower()):
 rel=str(p.relative_to(RUN)).replace("\\","/"); top=rel.split("/",1)[0] if "/" in rel else "root"
 rows.append({"path":rel,"sha256":sha256(p),"bytes":p.stat().st_size,"group":top}); groups[top]=groups.get(top,0)+1
manifest={"task_id":"TASK-T06E-P","run_id":RUN.name,"generated_last":True,"self_excluded":True,"self_path":"output_manifest.json","file_count_excluding_self":len(rows),"group_counts":groups,"files":rows,"registered_file_hashes_expected_current":True,"handoff_status":"COMPLETE_PENDING_CONTROLLER_REVIEW"}
dump(RUN/"output_manifest.json",manifest)
# Read-back only; no writes after this point.
bad=[]
for r in rows:
 if sha256(RUN/r["path"])!=r["sha256"]: bad.append(r["path"])
print(json.dumps({"status":"COMPLETE_PENDING_CONTROLLER_REVIEW","manifest_count":len(rows),"readback_bad":bad},ensure_ascii=False))
if bad: raise SystemExit(2)
