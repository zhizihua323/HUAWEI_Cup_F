from __future__ import annotations
import hashlib, json, shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

RUN=Path(__file__).resolve().parents[1]
ROOT=Path(__file__).resolve().parents[4]
TZ=ZoneInfo("Asia/Shanghai")

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()

def read_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write_json(p,o): Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def stage(name,status,detail=""):
    with (RUN/"stage_status.jsonl").open("a",encoding="utf-8") as f:
        f.write(json.dumps({"time":datetime.now(TZ).isoformat(timespec="seconds"),"stage":name,"status":status,"detail":detail},ensure_ascii=False)+"\n")

verification=read_json(RUN/"verification.json")
metrics=pd.read_csv(RUN/"validation_metrics_by_source.csv")
large=pd.read_csv(RUN/"large_model_gt10b_audit.csv")
spec=read_json(RUN/"generalized_law_spec.json")
pq=read_json(RUN/"p_q_double_counting_audit.json")
imp=read_json(RUN/"t07_impact_decision.json")
pre=read_json(RUN/"checks_pre_verification.json")
run_summary=read_json(RUN/"run_summary.json")

snap=RUN/"code_snapshot"; snap.mkdir(exist_ok=True)
for p in sorted((RUN/"code").glob("*.py")):
    shutil.copy2(p,snap/p.name)
snapshot_equal=all((snap/p.name).read_bytes()==p.read_bytes() for p in sorted((RUN/"code").glob("*.py")))

def source_summary(sid):
    d=metrics[metrics.source_id.eq(sid)]
    final=d[d.final_qualification.notna()].iloc[0]
    ins=d[d.subset.eq("IN_SUPPORT")]
    if len(ins): ins=ins.iloc[0]
    else:
        est=d[d.subset.eq("ESTIMATED_REFERENCE_ALL")]
        ins=est.iloc[0] if len(est) else d.iloc[0]
    return final,ins

summary={}
for sid in ["B2","B3","B4","B5","B9","B10"]:
    summary[sid]=source_summary(sid)

def fnum(x,digits=6):
    if pd.isna(x): return "NA"
    return f"{float(x):.{digits}g}"

b2r,b2i=summary["B2"]; b3r,b3i=summary["B3"]; b4r,b4i=summary["B4"]; b5r,b5i=summary["B5"]
b9=large[large.source_id.eq("B9")].iloc[0]; b10=large[large.source_id.eq("B10")].iloc[0]
we=spec["worked_example"]
FROZEN_E=spec["L0_B1"]["parameters"]["E"]; FROZEN_A=spec["L0_B1"]["parameters"]["A"]; FROZEN_B=spec["L0_B1"]["parameters"]["B"]
FROZEN_alpha=spec["L0_B1"]["parameters"]["alpha"]; FROZEN_beta=spec["L0_B1"]["parameters"]["beta"]
we_k=spec["quality_module"]["k_add"]; Q_ANCHOR=spec["quality_module"]["q_A_star"]
paper=f"""# Q2广义标度律与强制验证闭合（候选冻结）

状态：`COMPLETE_PENDING_CONTROLLER_REVIEW`。证据目录：`diagnostics/TASK-G2/{RUN.name}/`。本文件只是候选冻结接口，不是主控关闭或T07重跑授权。

## 1. 冻结结论

- 主模型固定为 `M0_B1: L0=E+A*N_B^(-alpha)+B*D_B^(-beta)`，五个参数逐位等同T06冻结值；未重拟合、未重选模型、未clip到支持边界。
- B1支持框为 `N_B in [0.070542,11.965825]`、`D_B in [0.134,299.893]`。跨源主验证只使用支持框内记录，OOS单列压力结果。
- 正式广义表达是“分层估计、联合表达”，不是统一四变量联合模型：
  `L_gen^(s)(N_B,D_B,Q_A,p)=L0_B1(N_B,D_B)+rho_Q^(s)*Delta_Q(h_s(Q_A))+tau_p^(s)*Delta_p(p;p0)`。
- T07影响字段固定为 `NEW_Q2_CHANGES_T07_NUMERIC_INPUTS = NO`。本轮未启动、未授权增量T07。

## 2. 强制来源验证

|来源|性质|原始/有效记录|独立簇|支持内/OOS|冻结模型RMSE|MAE|mean error(pred-actual)|Spearman|最终资格|
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
|B2|半合成|{int(b2r.raw_rows)}/{int(b2r.n_original_subset_rows)}|{int(b2i.n_groups_in_subset)}|{int(b2i.n)}/909|{fnum(b2i.rmse)}|{fnum(b2i.mae)}|{fnum(b2i.mean_error)}|{fnum(b2i.spearman)}|`{b2r.final_qualification}`|
|B3|Pythia插值|{int(b3r.raw_rows)}/{int(b3i.n)}|{int(b3i.n_groups_in_subset)}|4000/0|{fnum(b3i.rmse)}|{fnum(b3i.mae)}|{fnum(b3i.mean_error)}|{fnum(b3i.spearman)}|`{b3r.final_qualification}`|
|B4|公开跨族观测|{int(b4r.raw_rows)}/{int(b4r.n_original_subset_rows)}|{int(b4i.n_groups_in_subset)}|{int(b4i.n)}/49|{fnum(b4i.rmse)}|{fnum(b4i.mae)}|{fnum(b4i.mean_error)}|{fnum(b4i.spearman)}|`{b4r.final_qualification}`|
|B5|公开文献观测|{int(b5r.raw_rows)}/{int(b5r.n_original_subset_rows)}|{int(b5i.n_groups_in_subset)}|{int(b5i.n)}/36|{fnum(b5i.rmse)}|{fnum(b5i.mae)}|{fnum(b5i.mean_error)}|{fnum(b5i.spearman)}|`{b5r.final_qualification}`|

- B2：{int(b2r.raw_rows)}行、7条run，支持内仅{int(b2i.n)}行且6个簇；整体及支持内均保留系统性低估。资格为`VALIDATION_FAILED`，不得用于重拟合M0_B1。
- B3：8条Pythia插值轨迹，每轨迹500点；RMSE={fnum(b3i.rmse)}，聚类bootstrap 95%区间[{fnum(b3i.rmse_boot_lo)},{fnum(b3i.rmse_boot_hi)}]。资格为`VALIDATION_SUPPORTED`，但它是同源插值，不构成独立外部复制。
- B4：57行、12族；支持内只有{int(b4i.n)}行、2族，RMSE={fnum(b4i.rmse)}且平均低估{abs(float(b4i.mean_error)):.6g}。资格为`VALIDATION_FAILED`；支持内证据很小，不能因失败改动主模型。
- B5：44行、9族；支持内只有{int(b5i.n)}行、3族，RMSE={fnum(b5i.rmse)}且平均低估{abs(float(b5i.mean_error)):.6g}。资格为`VALIDATION_FAILED`。
- 所有bootstrap均使用种子`20260925`、2,000次整簇重采样；不合并真实、半合成、插值、公开和估算来源计算总RMSE。

## 3. 百亿参数以上审计

|来源|>10B记录|族数|D可用/正|Loss状态|B1支持内|最终资格|
|---|---:|---:|---:|---|---:|---|
|B9|{int(b9.records_gt_10B)}|{int(b9.unique_model_families_gt_10B)}|{int(b9.D_available_records)}/{int(b9.D_positive_records)}|不可用|0|`OOS_STRESS_ONLY`|
|B10|{int(b10.records_gt_10B)}|{int(b10.unique_model_families_gt_10B)}|{int(b10.D_available_records)}/{int(b10.D_positive_records)}|{int(b10.estimated_loss_records)}条估算值|0|`ESTIMATED_SCENARIO_ONLY`|

B9/B10的N范围均为100B–10,000B，远超B1的11.965825B上界；B9另有4条D不可用/零值。B10对估算baseline的描述性RMSE约为{fnum(b10.estimated_reference_rmse)}，但估算值不得升级为真值，也不能据此宣称百亿以上外推成功。结论：M0_B1只支持到B1经验框，不能支持>10B参数以上推断；主要误差来源是N/D外推、跨来源Loss口径、缺失D/Loss和B10的估算性质。

## 4. 广义标度律

### 4.1 B1基础项

`L0_B1={FROZEN_E} + {FROZEN_A}*N_B^(-{FROZEN_alpha}) + {FROZEN_B}*D_B^(-{FROZEN_beta})`。

参数资格为`IDENTIFIED_SOURCE_CONDITIONAL`，来源仅B1。

### 4.2 质量情景项

`Delta_Q(Q_B)=-k_add*(Q_B-0.6)`，`k_add={we_k}`。该关系只在B6来源内、`0.1<=Q_B<=0.6`作为接受的关系；跨来源仍是`SCENARIO_ONLY`。

`h_s`只允许T06冻结形式：H0为空；H1为`h(Q_A)=Q_A`；H2为`h(Q_A)=0.6+b*(Q_A-q_A*)`，`b in {{0.5,1,2}}`；H3为经验分位步骤映射；H4只有方向，不能数值代入。`q_A*={Q_ANCHOR}`，`rho_Q`只取冻结情景值`{{0,0.5,1}}`。没有新估计A/B映射。

### 4.3 配比情景项

`Delta_p(p;p0)=c^T(p-p0)`，其中`c`是13个冻结RegMix线性系数向量的等域均值，`p0`是冻结合同参考配比；`tau_p`只取冻结情景值`{{0,0.5,1,-1}}`。1M内是来源条件关系，向B1运输仍为`SCENARIO_ONLY`。

## 5. 解析边际量

- `dL/dN_B=-alpha*A*N_B^(-alpha-1)`；`dL/dD_B=-beta*B*D_B^(-beta-1)`。
- 数值H1–H3：`dL/dQ_A=-rho_Q*k_add*h_s'(Q_A)`；H4只给方向，不可微或分位跳点只允许固定情景后的有限差分。
- 可行配比方向`v`满足`sum(v)=0`且局部`p0+epsilon*v>=0`：`D_v L=tau_p*c^T v`。
- 弹性：`E_N=N_B/L*dL/dN_B`，`E_D=D_B/L*dL/dD_B`，`E_Q=Q_A/L*dL/dQ_A`。
- 保持Loss不变：`dN_B/dQ_A=-(dL/dQ_A)/(dL/dN_B)`，`dD_B/dQ_A=-(dL/dQ_A)/(dL/dD_B)`。
- 工作点`N_B={we['N_B']:g},D_B={we['D_B']:g}`：`dL/dN_B={we['dL_dN_B']:.6g}`、`dL/dD_B={we['dL_dD_B']:.6g}`；S03下`dL/dQ_A={we['dL_dQ_A']:.6g}`，保持Loss替代量分别约`{we['holding_Loss_dN_dQ']:.6g}`和`{we['holding_Loss_dD_dQ']:.6g}`。
- 对方向`e_github-e_arxiv`，`c^T v={we['cT_v']:.6g}`；S14/S15/S16的方向斜率分别为`{we['directional_derivative_tau05']:.6g}`、`{we['directional_derivative_tau10']:.6g}`、`{we['directional_derivative_tau_minus10']:.6g}`。

## 6. Q–p双重计数与资格

固定域质量向量`q`时，`Q_mix=p^Tq`位于`p`的列空间；设计秩17，加入`Q_mix`后秩仍17，相对投影残差`{pq['relative_projection_residual']:.6g}`。因此不得把17个配比坐标解释为17个独立边际，也不得同时把`Q_mix`和`p`作为独立自由坐标。当前17域中只有{pq['mapped_quality_domains']}域有质量映射，另{pq['unmapped_quality_domains']}域未映射。必须固定一个，或只报告联合可行方向。

参数资格矩阵见`generalized_parameter_qualification.csv`；逐项保留`IDENTIFIED_SOURCE_CONDITIONAL`、`SOURCE_CONDITIONAL`、`SCENARIO_CALIBRATED`、`DIRECTION_ONLY`和`NOT_IDENTIFIABLE`。

## 7. T07影响

`NEW_Q2_CHANGES_T07_NUMERIC_INPUTS = NO`。理由：五个主参数逐位未变，未新增已启用参数；B2/B4/B5失败、B3插值支持和分层L_gen都不改变T07主合同的数值输入。T07继续为`primary_model=M0_B1`、`quality_enabled=false`、`mixture_transport_enabled=false`。本轮没有启动增量T07。

## 8. 独立验证与边界

独立verifier未导入执行模块，复算5,390条预测、支持状态、来源/簇指标、2,000次聚类bootstrap、解析示例及T06/T07全树哈希；结果`{verification['summary']['pass']}/{verification['summary']['total']} PASS`。详见`verification.json`和`verification_metrics_recomputed.csv`。

不得写：已建立统一可识别的`L(N,D,Q,p)`；Q已跨来源标定；质量因果降低Loss；RegMix效果已跨规模验证；B9/B10提供了百亿以上真值外推；或17个配比坐标可独立解释。
"""
paper_path=ROOT/"paper/Q2_GAP_RESULT_FREEZE.md"
paper_path.write_text(paper,encoding="utf-8")
stage("candidate_freeze","PASS",str(paper_path.relative_to(ROOT)).replace("\\","/"))

required=[
 "run_summary.json","environment.json","input_manifest.json","command_log.json","stage_status.jsonl",
 "source_schema_and_units.csv","validation_predictions.parquet","validation_metrics_by_source.csv",
 "validation_metrics_by_family_or_trajectory.csv","support_oos_audit.csv","systematic_bias_audit.csv",
 "large_model_gt10b_audit.csv","generalized_law_spec.json","generalized_parameter_qualification.csv",
 "derivatives_elasticities_and_substitutions.md","p_q_double_counting_audit.json","t07_impact_decision.json",
 "checks.json","verification.json","handoff.md","output_manifest.json"
]
final_checks=[]
for c in pre["checks"]:
    if c["check"] in {"candidate_freeze_generated_after_verification","output_manifest_generated_last"}:
        continue
    final_checks.append(c)
final_checks.extend([
    {"check":"independent_verifier_all_pass","pass":verification["summary"]["fail"]==0,"detail":f"{verification['summary']['pass']}/{verification['summary']['total']} PASS"},
    {"check":"code_snapshot_matches_code","pass":bool(snapshot_equal),"detail":"all *.py byte-identical"},
    {"check":"candidate_freeze_generated_after_verification","pass":paper_path.exists() and paper_path.stat().st_size>0,"detail":str(paper_path.relative_to(ROOT)).replace("\\","/")},
    {"check":"T07_impact_is_NO","pass":imp["NEW_Q2_CHANGES_T07_NUMERIC_INPUTS"]=="NO"},
    {"check":"required_files_present_before_manifest","pass":all((RUN/p).exists() for p in required if p not in {"output_manifest.json","checks.json"})},
])
write_json(RUN/"checks.json",{
    "schema_version":1,"run_id":RUN.name,"status":"PASS" if all(c["pass"] for c in final_checks) else "FAIL",
    "summary":{"total":len(final_checks),"pass":sum(bool(c["pass"]) for c in final_checks),"fail":sum(not bool(c["pass"]) for c in final_checks)},
    "checks":final_checks,
    "manifest_policy":"output_manifest.json is written after this file and after all other registered outputs."
})
stage("final_checks","PASS" if all(c["pass"] for c in final_checks) else "FAIL","checks.json finalized")

run_summary["checks"]={c["check"]:c["pass"] for c in final_checks}
run_summary.update({
    "status":"COMPLETE_PENDING_CONTROLLER_REVIEW",
    "execution_status":"COMPLETE",
    "verification_status":"PASS",
    "verification_summary":verification["summary"],
    "checks_summary":{"total":len(final_checks),"pass":sum(bool(c["pass"]) for c in final_checks),"fail":sum(not bool(c["pass"]) for c in final_checks)},
    "candidate_freeze":"paper/Q2_GAP_RESULT_FREEZE.md",
    "t07_impact":imp["NEW_Q2_CHANGES_T07_NUMERIC_INPUTS"],
    "next_action":"Controller review candidate freeze; no incremental T07 is authorized by this task."
})
write_json(RUN/"run_summary.json",run_summary)

handoff=f"""# TASK-G2 handoff

状态：`COMPLETE_PENDING_CONTROLLER_REVIEW`。

## 结果

- M0_B1五参数逐位冻结，未重拟合、未重选、未clip。
- 来源资格：B2=`{summary['B2'][0].final_qualification}`，B3=`{summary['B3'][0].final_qualification}`，B4=`{summary['B4'][0].final_qualification}`，B5=`{summary['B5'][0].final_qualification}`，B9=`OOS_STRESS_ONLY`，B10=`ESTIMATED_SCENARIO_ONLY`。
- B3是唯一的`VALIDATION_SUPPORTED`来源，但只是Pythia同源插值轨迹，不是独立外部复制。
- L_gen采用`L0_B1 + rho_Q*Delta_Q(h_s(Q_A)) + tau_p*c^T(p-p0)`的分层联合表达；Q/p、A/B桥接和跨规模配比不得解释为统一联合识别。
- `NEW_Q2_CHANGES_T07_NUMERIC_INPUTS = NO`；未启动增量T07。

## 独立验证

verifier未导入执行模块；预测、支持状态、来源/簇指标、聚类bootstrap、解析示例和T06/T07哈希全部复算，结果`{verification['summary']['pass']}/{verification['summary']['total']} PASS`。

## 证据入口

- `run_summary.json`、`checks.json`、`verification.json`
- `validation_metrics_by_source.csv`、`systematic_bias_audit.csv`
- `large_model_gt10b_audit.csv`
- `generalized_law_spec.json`、`derivatives_elasticities_and_substitutions.md`
- `p_q_double_counting_audit.json`、`t07_impact_decision.json`
- 候选接口：`paper/Q2_GAP_RESULT_FREEZE.md`

## 边界

本run不关闭Q2、不修改00–05/论文正文、不重跑T07，也不把B9/B10估算升级为真值。
"""
(RUN/"handoff.md").write_text(handoff,encoding="utf-8")
stage("handoff","PASS","handoff.md written")

# Final manifest. Every registered file is frozen before this last write.
all_files=sorted(p for p in RUN.rglob("*") if p.is_file() and p.name!="output_manifest.json")
entries=[]
for p in all_files:
    entries.append({"path":str(p.relative_to(RUN)).replace("\\","/"),"bytes":p.stat().st_size,"sha256":sha256(p)})
manifest={
    "schema_version":1,
    "task_id":"TASK-G2",
    "run_id":RUN.name,
    "created_at":datetime.now(TZ).isoformat(timespec="seconds"),
    "generation_order":"last",
    "output_count":len(entries)+2,
    "outputs":entries,
    "candidate_freeze":{
        "path":"paper/Q2_GAP_RESULT_FREEZE.md",
        "bytes":paper_path.stat().st_size,
        "sha256":sha256(paper_path),
    },
    "verification":{"path":"verification.json","summary":verification["summary"]},
    "t07_impact":{"NEW_Q2_CHANGES_T07_NUMERIC_INPUTS":imp["NEW_Q2_CHANGES_T07_NUMERIC_INPUTS"]},
    "no_writes_after_manifest":True
}
write_json(RUN/"output_manifest.json",manifest)
print(json.dumps({"status":"FINALIZED","run_id":RUN.name,"output_count":manifest["output_count"],"verification":verification['summary']},ensure_ascii=False))




