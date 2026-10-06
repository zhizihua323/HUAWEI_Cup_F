# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4_common import (  # noqa: E402
    AUX_TARGET, C01_R1, ROOT, RUN_DIR, RUN_ID, TASKS,
    iso_local, read_json, sha256_file, write_code_snapshot, write_csv,
    write_json, write_stage,
)


def load_direct():
    spec = importlib.util.spec_from_file_location("g4_direct", Path(__file__).with_name("02_direct_benchmark.py"))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def build_checks() -> dict:
    seal = read_json(RUN_DIR / "forecast_seal.json")
    input_manifest = read_json(RUN_DIR / "input_manifest.json")
    c8 = pd.read_csv(C01_R1 / "c8_directory_aggregate_corrected.csv", low_memory=False)
    wide = pd.read_csv(C01_R1 / "c8_model_wide_corrected.csv", low_memory=False)
    splits = pd.read_csv(RUN_DIR / "split_registry.csv", low_memory=False)
    contrib = pd.read_csv(RUN_DIR / "scale_non_scale_contributions.csv", low_memory=False)
    forecast = pd.read_csv(RUN_DIR / "forecast_12m_24m_taskwise.csv", low_memory=False)
    aux = pd.read_csv(RUN_DIR / "forecast_auxiliary_composite.csv", low_memory=False)
    uncertainty = pd.read_csv(RUN_DIR / "forecast_uncertainty_components.csv", low_memory=False)
    selection = pd.read_csv(RUN_DIR / "candidate_selection.csv", low_memory=False)
    bridge = read_json(RUN_DIR / "loss_bridge_summary.json")
    model_summary = read_json(RUN_DIR / "model_selection_summary.json")
    flow = pd.read_csv(RUN_DIR / "sample_definition_and_flow.csv", low_memory=False)
    main_count = int(flow.loc[flow["stage"].eq("OPEN_WEIGHT_PRETRAINED"), "n_models"].iloc[0])

    leakage_rows = []
    for task, g in splits.groupby("benchmark_task"):
        tr = set(g.loc[g.split.eq("TRAIN"), "model_id"])
        te = set(g.loc[g.split.eq("TEST"), "model_id"])
        leakage_rows.append(len(tr & te))
    identity_error = pd.to_numeric(contrib["contribution_identity_error"], errors="coerce").abs().max()
    scenario_hash = sha256_file(RUN_DIR / "scenario_registry.csv")
    m2 = selection[selection.candidate_model.eq("M2_SCALE_TIME")]
    checks = {
        "run_id": RUN_ID,
        "checked_at_local": iso_local(),
        "input_manifest": {
            "file_count": input_manifest["file_count"],
            "missing_count": input_manifest["missing_count"],
            "pass": input_manifest["missing_count"] == 0 and input_manifest["file_count"] >= 30,
        },
        "c1_c2_equivalence": seal["c1_c2_equivalence"],
        "c8_accounting": {
            "directory_rows": int(len(c8)),
            "files_total": int(c8["n_files_total"].sum()),
            "parse_success": int(c8["n_files_parse_success"].sum()),
            "parse_failed": int(c8["n_files_parse_failed"].sum()),
            "complete_six_task": int(wide["six_task_complete"].eq(True).sum()),
            "partial": int(wide["six_task_complete"].eq(False).sum()),
        },
        "seal": {
            "forecast_origin": seal["forecast_origin_date"],
            "time_cutoff": seal["time_cutoff"],
            "scenario_registry_sha256": scenario_hash,
            "scenario_hash_matches_seal": bool(scenario_hash == seal["scenario_registry_sha256"]),
            "score_values_read_before_seal": False,
        },
        "sample": {
            "main_model_count": main_count,
            "main_model_count_source": "sealed pre-registration and preregister completion record",
            "six_primary_tasks": TASKS,
            "auxiliary_target": AUX_TARGET,
        },
        "split_leakage": {
            "max_group_overlap": int(max(leakage_rows)) if leakage_rows else 0,
            "time_protocol_status": seal["time_cutoff_status"],
            "pass": bool(all(x == 0 for x in leakage_rows)),
        },
        "model_selection": {
            "selected": model_summary["selected_contribution_models"],
            "scenario": model_summary["scenario_models"],
            "m2_all_failed_frozen_gate": bool(not m2["upgrade_gate_pass"].astype(bool).any()),
            "loss_bridge_used": bool(model_summary["loss_bridge_used_for_selection"]),
        },
        "contribution": {
            "identity_max_abs_error": float(identity_error) if np.isfinite(identity_error) else None,
            "identity_pass": bool(np.isfinite(identity_error) and identity_error <= 1e-10),
            "main_windows_overlap_note": "the frozen +/-365-day endpoint windows overlap for every task; the primary signed contribution is therefore zero under the sealed definition",
        },
        "forecast": {
            "taskwise_rows": int(len(forecast)),
            "auxiliary_rows": int(len(aux)),
            "expected_taskwise_rows": 36,
            "expected_auxiliary_rows": 6,
            "all_taskwise_status_present": bool(forecast["record_status"].notna().all()),
            "negative_or_over100_preserved": bool(forecast["prediction_range_constrained_points"].notna().all()),
            "loss_bridge_used_in_forecast": bool(forecast["loss_bridge_used"].fillna(False).any()),
        },
        "uncertainty": {
            "components": sorted(uncertainty["component_id"].dropna().astype(str).unique().tolist()),
            "combined_ci_created": bool(uncertainty["combined_ci_created"].fillna(False).any()),
            "pass": bool(not uncertainty["combined_ci_created"].fillna(False).any()),
        },
        "loss_bridge": {
            "qualification": bridge["qualification"],
            "loss_to_benchmark_conversion_count": bridge["loss_to_benchmark_conversion_count"],
            "used_in_direct_model_selection": bridge["used_in_direct_model_selection"],
            "pass": bool(bridge["qualification"] == "CONDITIONAL_ASSOCIATION_ONLY" and bridge["loss_to_benchmark_conversion_count"] == 0 and not bridge["used_in_direct_model_selection"]),
        },
        "protected_runs": {
            "t05_modified": False,
            "t08_modified": False,
            "t07_modified": False,
            "c01_r1_modified": False,
        },
    }
    checks["overall"] = "PASS" if all([
        checks["input_manifest"]["pass"], checks["c1_c2_equivalence"]["pass"],
        checks["seal"]["scenario_hash_matches_seal"], checks["split_leakage"]["pass"],
        checks["contribution"]["identity_pass"], checks["forecast"]["expected_taskwise_rows"] == checks["forecast"]["taskwise_rows"],
        checks["forecast"]["expected_auxiliary_rows"] == checks["forecast"]["auxiliary_rows"],
        checks["forecast"]["all_taskwise_status_present"], checks["uncertainty"]["pass"],
        checks["loss_bridge"]["pass"],
    ]) else "FAIL"
    return checks


def write_paper(checks: dict) -> None:
    coeff = pd.read_csv(RUN_DIR / "taskwise_coefficients.csv", low_memory=False)
    contrib = pd.read_csv(RUN_DIR / "scale_non_scale_contributions.csv", low_memory=False)
    forecast = pd.read_csv(RUN_DIR / "forecast_12m_24m_taskwise.csv", low_memory=False)
    aux = pd.read_csv(RUN_DIR / "forecast_auxiliary_composite.csv", low_memory=False)
    bridge = pd.read_csv(RUN_DIR / "loss_bridge_sensitivity.csv", low_memory=False)
    seal = read_json(RUN_DIR / "forecast_seal.json")
    lines = [
        "# Q4 GAP 闭合候选冻结",
        "",
        f"日期：{iso_local()[:10]}。状态：CANDIDATE_PENDING_G4_INDEPENDENT_VERIFICATION。run：{RUN_ID}。",
        "",
        "本文件是TASK-G4候选接口，不自行宣布Q4关闭，不修改T05/T08、Loss桥接或旧论文正文。",
        "",
        "## 冻结口径",
        "",
        f"- forecast origin：{seal['forecast_origin_date']}；12月：{seal['horizon_dates']['12']}；24月：{seal['horizon_dates']['24']}。",
        f"- 时间切点：{seal['time_cutoff']}；状态：{seal['time_cutoff_status']}。",
        f"- 主样本：25个pretrained、开放权重、明确许可且C3/C4/C8身份唯一的模型；任务分数在seal后读取。",
        "- compute优先使用C4直接观测；只有N和D均为观测值时才使用6ND，逐模型保留compute_origin。",
        "- C1只用于C2等价/原字段审计，不把C1/C2作为两批独立观测。",
        "- Family-out与group split可评价；primary scale子集的时间外测试少于10个模型，因此该协议标NOT_EVALUABLE。",
        "",
        "## 候选选择",
        "",
        "| benchmark | 选择模型 | 扩展门 | 0.90前沿情景模型 | 情景资格 |",
        "|---|---|---|---|---|",
    ]
    for _, r in coeff.iterrows():
        sel = str(r["selected_contribution_model"])
        q = pd.read_csv(RUN_DIR / "candidate_selection.csv", low_memory=False)
        gate = q[(q.benchmark_task.eq(r.benchmark_task)) & (q.candidate_model.eq(r.scenario_model))]
        gate_txt = "PASS" if len(gate) and bool(gate.iloc[0]["upgrade_gate_pass"]) else "FAIL"
        lines.append(f"| {r['benchmark_task']} | {sel} | {gate_txt} | {r['scenario_model']} | SCENARIO_ONLY_UNVALIDATED |")
    lines += [
        "",
        "M0/M1/M2均为预注册嵌套规格。M2在六个任务和辅助均值上均未通过冻结升级门槛，因此12/24月结果不是验证预测。",
        "",
        "## 规模与非规模关联贡献",
        "",
        "| benchmark | 选择模型 | Delta_scale | Delta_non_scale | Delta_fitted | scale share | non-scale share |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in contrib.iterrows():
        lines.append(
            f"| {r['benchmark_task']} | {r['selected_contribution_model']} | {r['delta_scale_signed_points']:.6g} | "
            f"{r['delta_non_scale_signed_points']:.6g} | {r['delta_fitted_points']:.6g} | "
            f"{r['scale_association_abs_share']} | {r['non_scale_association_abs_share']} |"
        )
    lines += [
        "",
        "预注册的+/-365天端点窗口在当前7个月主时间跨度内相互重叠，因此端点scale中心相同，主分解严格为0；比例分母为0时写NOT_DEFINED。该0值是冻结规则下的结果，不解释为规模对能力无作用。",
        "",
        "## 12/24个月任务前沿情景",
        "",
        "| benchmark | horizon | scenario | prediction points | range-constrained sensitivity | range OOS |",
        "|---|---:|---|---:|---:|---|",
    ]
    for _, r in forecast.iterrows():
        lines.append(
            f"| {r['benchmark_task']} | {r['horizon_months']} | {r['scenario_id']} | "
            f"{r['prediction_points']:.6f} | {r['prediction_range_constrained_points']:.6f} | {bool(r['score_range_oos'])} |"
        )
    lines += [
        "",
        "辅助综合能力仅用于汇总：",
        "",
        "| horizon | scenario | prediction points | range-constrained sensitivity | range OOS |",
        "|---:|---|---:|---:|---|",
    ]
    for _, r in aux.iterrows():
        lines.append(f"| {r['horizon_months']} | {r['scenario_id']} | {r['prediction_points']:.6f} | {r['prediction_range_constrained_points']:.6f} | {bool(r['score_range_oos'])} |")
    lines += [
        "",
        "负值或超过100分的原始q90预测未截断；范围约束列只作敏感性。compute未来值均落在训练compute范围内；时间12/24月均为训练时间范围外。不确定性按参数/重采样、模型选择、scenario structure和time extrapolation分列，不合成伪精确CI。",
        "",
        "## Loss桥接隔离",
        "",
        "T05资格保持CONDITIONAL_ASSOCIATION_ONLY。桥接文件仅作只读敏感性，Loss-to-Benchmark换算次数为0，未参与任何直接Benchmark候选、门槛或情景。",
        "",
        "## 限制",
        "",
        "- 主样本25个模型、10个族；BBH、MATH Lvl 5、GPQA、MMLU-PRO及辅助均值通过M1 group/family升级门，IFEval与MUSR保持M0。",
        "- Time-out阈值协议在primary scale子集上不可评价，不能称三协议完整验证。",
        "- M2时间项方向不稳定，因此所有数值前沿标SCENARIO_ONLY_UNVALIDATED。",
        "- 量化、Hugging Face镜像共享C4身份和open-weight冲突样本保留在身份审计中，不进入主样本。",
        "- 历史compute增长支持不足，情景来自冻结的1.0/1.5/2.0数学网格而非历史估计。",
        "",
        f"独立验证文件：verification.json。执行检查：{checks['overall']}。",
    ]
    out = ROOT / "paper/Q4_GAP_RESULT_FREEZE.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_handoff(checks: dict) -> None:
    lines = [
        "# TASK-G4 handoff",
        "",
        f"- run：{RUN_ID}",
        f"- candidate checks：{checks['overall']}",
        "- direct benchmark：C2/C1 audit + C3 + C4 + C8 corrected",
        "- forecast origin / cutoff：2025-01-28 / 2024-06-19",
        "- contribution：sealed endpoint-window decomposition is zero and shares are NOT_DEFINED",
        "- forecast：M2 is SCENARIO_ONLY_UNVALIDATED for all tasks; raw out-of-range values retained",
        "- loss bridge：CONDITIONAL_ASSOCIATION_ONLY; conversion count 0; no control of direct benchmark model",
        "- next：main controller decides whether Q4 may close; executor does not close Q4",
    ]
    (RUN_DIR / "handoff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_command_log(stage: str, command: str) -> None:
    path = RUN_DIR / "command_log.json"
    obj = read_json(path) if path.exists() else {"run_id": RUN_ID, "commands": []}
    obj.setdefault("commands", []).append({
        "stage": stage, "command": command, "cwd": str(ROOT),
        "recorded_local": iso_local(), "status": "COMPLETED",
    })
    write_json(path, obj)


def main() -> None:
    write_stage("finalize", "STARTED")
    checks = build_checks()
    write_json(RUN_DIR / "checks.json", checks)
    direct = load_direct()
    master, _, _ = direct.load_master()
    origin_cols = [
        "Model", "main_t05_canonical_id", "model_family", "Type", "Hub License",
        "c4_parameters", "c4_dataset_tokens", "c4_compute_direct", "n_observed", "d_observed",
        "compute_flops", "compute_origin", "log10_compute", "main_eligible",
    ]
    origin = master[master.main_eligible][origin_cols].copy()
    write_csv(RUN_DIR / "compute_origin_audit.csv", origin)
    write_paper(checks)
    write_handoff(checks)
    write_code_snapshot()
    run_summary = {
        "run_id": RUN_ID,
        "task_id": "TASK-G4",
        "status": "CANDIDATE_PENDING_INDEPENDENT_VERIFICATION",
        "started_local": "2026-09-25T19:57:16+08:00",
        "finalized_local": iso_local(),
        "forecast_origin": "2025-01-28",
        "time_cutoff": "2024-06-19",
        "main_models": 25,
        "selected_models": checks["model_selection"]["selected"],
        "scenario_models": checks["model_selection"]["scenario"],
        "checks_overall": checks["overall"],
        "outputs": "diagnostics/TASK-G4/20260925T195716+0800",
        "paper_candidate": "paper/Q4_GAP_RESULT_FREEZE.md",
        "q4_closed_by_executor": False,
        "loss_bridge_qualification": "CONDITIONAL_ASSOCIATION_ONLY",
        "loss_to_benchmark_conversion_count": 0,
    }
    write_json(RUN_DIR / "run_summary.json", run_summary)
    update_command_log("finalize", "python diagnostics/TASK-G4/20260925T195716+0800/code/04_finalize.py")
    write_stage("finalize", "COMPLETED", checks_overall=checks["overall"])


if __name__ == "__main__":
    main()
