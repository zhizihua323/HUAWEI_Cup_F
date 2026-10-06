from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path.cwd()
RUN = ROOT / "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08"
B = ROOT / "diagnostics/TASK-T06E-B/20260925T100306+08"
BR1 = ROOT / "diagnostics/TASK-T06E-B-R1/20260925T103130+08"
P = ROOT / "diagnostics/TASK-T06E-P/20260925T075729+08"
T06 = ROOT / "tasks/TASK-T06_尺度桥接识别性与广义缩放律方法裁决.md"
T06E = ROOT / "tasks/TASK-T06E_来源内缩放律与质量条件关系验证_尺度桥接情景及T07接口.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def manifest_state(root: Path) -> dict:
    manifest_path = root / "output_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad = []
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.exists():
            bad.append({"path": item["path"], "reason": "MISSING"})
        elif path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            bad.append({"path": item["path"], "reason": "HASH_OR_SIZE_MISMATCH"})
    return {
        "manifest_path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": sha256(manifest_path),
        "declared_file_count": manifest.get("file_count", len(manifest["files"])),
        "entry_count": len(manifest["files"]),
        "mismatch_count": len(bad),
        "status": "PASS" if not bad else "FAIL",
    }


for required in (B, BR1, P, T06, T06E):
    if not required.exists():
        raise SystemExit(f"MISSING_INPUT: {required}")

b_state = manifest_state(B)
r1_state = manifest_state(BR1)
p_state = manifest_state(P)
if any(x["status"] != "PASS" for x in (b_state, r1_state, p_state)):
    raise SystemExit("BRANCH_MANIFEST_MISMATCH")

recon = pd.DataFrame(
    [
        {"branch": "TASK-T06E-B", **b_state},
        {"branch": "TASK-T06E-B-R1", **r1_state},
        {"branch": "TASK-T06E-P", **p_state},
    ]
)
recon.to_csv(RUN / "branch_manifest_reconciliation.csv", index=False, encoding="utf-8-sig")

registry = pd.read_csv(P / "scenario_registry/scenario_registry_preregistered.csv")
scenario_inputs = pd.read_parquet(P / "scenario_registry/scenario_inputs.parquet")
if len(registry) != 21 or registry["scenario_id"].tolist() != scenario_inputs["scenario_id"].tolist():
    raise SystemExit("SCENARIO_REGISTRY_MISMATCH")

seal = json.loads((P / "scenario_registry/SCENARIO_REGISTRY_SEAL.json").read_text(encoding="utf-8"))
p_contract = json.loads((P / "t07_candidate/t07_scenario_contract_candidate.json").read_text(encoding="utf-8"))
r1_contract = json.loads((BR1 / "t07_bside_contract_candidate_corrected.json").read_text(encoding="utf-8"))
b_uncertainty = json.loads((B / "uncertainty_components_B.json").read_text(encoding="utf-8"))
p_uncertainty = json.loads((P / "uncertainty_components_P.json").read_text(encoding="utf-8"))
input_audit = json.loads((B / "input_audit.json").read_text(encoding="utf-8"))
p_summary = json.loads((P / "run_summary.json").read_text(encoding="utf-8"))

params = pd.read_csv(B / "fit/scaling_parameters_by_source.csv")
full = params[params["stage"].eq("full")]


def get_full(source: str, model: str, task_id: str | None = None) -> pd.Series:
    rows = full[(full["source"] == source) & (full["model"] == model)]
    if task_id is not None:
        rows = rows[rows["task_id"] == task_id]
    if len(rows) != 1:
        raise SystemExit(f"EXPECTED_ONE_FULL_ROW:{source}:{model}:{task_id}:{len(rows)}")
    return rows.iloc[0]


b1 = get_full("B1", "M0_B1", "B1_full")
b6_m0 = get_full("B6", "M0_6", "B6_full_M0_6")
b6_add = get_full("B6", "MQ-add", "B6_full_MQ-add")
b6_eff = get_full("B6", "MQ-eff", "B6_full_MQ-eff")

if r1_contract["scientific_result"] != "ACCEPT_B6_SOURCE_RELATION":
    raise SystemExit("R1_NOT_ACCEPTED")

b_id = pd.read_csv(BR1 / "identifiability_matrix_B_corrected.csv")
p_id = pd.read_csv(P / "identifiability_matrix_P.csv")
b_rows = []
for _, row in b_id.iterrows():
    b_rows.append(
        {
            "branch": "B_R1",
            "component": row["module"],
            "parameter": row["parameter"],
            "status": row["status"],
            "source": row["source"],
            "role": row["role"],
            "numeric_use_in_T07": bool(row["can_enter_T07_identified"]),
            "restriction": "Source-conditional; B6 quality terms remain scenario-only when transported across sources.",
        }
    )
for _, row in p_id.iterrows():
    b_rows.append(
        {
            "branch": "P",
            "component": row["component"],
            "parameter": row["component"],
            "status": row["status"],
            "source": row["evidence_source"],
            "role": "bridge_or_mixture_interface",
            "numeric_use_in_T07": bool(row["numeric_use_allowed_in_P"]),
            "restriction": row["constraint"],
        }
    )
ident = pd.DataFrame(b_rows)
ident.to_csv(RUN / "integrated_identifiability_matrix.csv", index=False, encoding="utf-8-sig")

k_add = float(b6_add["k_add"])
eta_b6 = float(b6_eff["eta"])
beta_b6 = float(b6_eff["beta"])
beta_b1 = float(b1["beta"])
eta_keep_k_target = eta_b6 / beta_b6 * beta_b1

filled = scenario_inputs.copy()
filled["B1_E"] = float(b1["E"])
filled["B1_A"] = float(b1["A"])
filled["B1_B"] = float(b1["B"])
filled["B1_alpha"] = float(b1["alpha"])
filled["B1_beta"] = beta_b1
filled["k_add_B6"] = np.nan
filled["eta_B6_sensitivity"] = np.nan
filled["eta_transport_value"] = np.nan
filled["quality_parameter_qualification"] = "NOT_APPLICABLE"
filled["cross_source_qualification"] = "SCENARIO_ONLY"
filled["B8_conflict_qualification"] = "NOT_APPLICABLE"
for idx, row in filled.iterrows():
    sid = row["scenario_id"]
    quality_enabled = bool(row["quality_effect_enabled"])
    rho = row["rho_Q_fixed_scenario"]
    if quality_enabled and pd.notna(rho) and float(rho) != 0.0:
        filled.at[idx, "k_add_B6"] = k_add
        filled.at[idx, "eta_B6_sensitivity"] = eta_b6
        filled.at[idx, "quality_parameter_qualification"] = "B6_SOURCE_CONDITIONAL_ACCEPTED"
        if row["quality_transport"] == "effective_data_keep_eta":
            filled.at[idx, "eta_transport_value"] = eta_b6
        elif row["quality_transport"] == "effective_data_keep_k":
            filled.at[idx, "eta_transport_value"] = eta_keep_k_target
    if sid in ("S00_NULL_M0_B1", "S10_RHOQ_00"):
        filled.at[idx, "cross_source_qualification"] = "IDENTIFIED_NULL_BASELINE"
    if sid == "S17_B8_REVERSE_COMMON_SUPPORT":
        filled.at[idx, "B8_conflict_qualification"] = "CONFLICT_EVIDENCE_DIRECTION_ONLY"
        filled.at[idx, "cross_source_qualification"] = "NO_NUMERIC_PREDICTION"

filled.to_csv(RUN / "scenario_registry_filled.csv", index=False, encoding="utf-8-sig")

pred = filled.copy()
pred["prediction_scope"] = "REGISTERED_REFERENCE_EFFECT_ONLY; N,D,p budget point not supplied"
pred["baseline_loss"] = np.nan
pred["quality_delta_loss_at_reference"] = np.nan
pred["effective_D_multiplier_at_reference"] = np.nan
pred["mixture_delta_loss_at_reference"] = np.nan
pred["full_loss_at_reference"] = np.nan
pred["numeric_status_integrated"] = "REQUIRES_T07_N_D_AND_FEASIBLE_P"
for idx, row in pred.iterrows():
    sid = row["scenario_id"]
    if sid in ("S00_NULL_M0_B1", "S10_RHOQ_00"):
        pred.at[idx, "quality_delta_loss_at_reference"] = 0.0
        pred.at[idx, "effective_D_multiplier_at_reference"] = 1.0
        pred.at[idx, "numeric_status_integrated"] = "NULL_EFFECT_FIXED; FULL_LOSS_REQUIRES_N_D"
    elif sid in ("S07_H4_DIRECTION_ONLY", "S17_B8_REVERSE_COMMON_SUPPORT"):
        pred.at[idx, "numeric_status_integrated"] = "NO_NUMERIC_PREDICTION"
    elif row["family"] == "mixture_transport_univariate":
        pred.at[idx, "numeric_status_integrated"] = "SCENARIO_ONLY; REQUIRES_FEASIBLE_P_VECTOR"
    elif bool(row["quality_effect_enabled"]) and pd.notna(row["mapped_Q_B_at_reference"]):
        dq = float(row["mapped_Q_B_at_reference"]) - 0.6
        rho = float(row["rho_Q_fixed_scenario"])
        r_b1 = float(row["r_B1_fixed_scenario"])
        if row["quality_transport"] == "additive":
            pred.at[idx, "quality_delta_loss_at_reference"] = -rho * r_b1 * k_add * dq
            pred.at[idx, "numeric_status_integrated"] = "SCENARIO_EFFECT_AT_ANCHOR; FULL_LOSS_REQUIRES_N_D"
        else:
            eta = float(row["eta_transport_value"])
            pred.at[idx, "effective_D_multiplier_at_reference"] = float(np.exp(rho * r_b1 * eta * dq))
            pred.at[idx, "numeric_status_integrated"] = "SENSITIVITY_MULTIPLIER_AT_ANCHOR; FULL_LOSS_REQUIRES_N_D"
pred.to_parquet(RUN / "scenario_predictions.parquet", index=False)

uncertainty = {
    "schema_version": 1,
    "combining_rule": "Keep statistical, structural, bridge, transport, and conflict components separate; do not form one CI or scenario probability.",
    "B_branch": b_uncertainty,
    "P_branch": p_uncertainty,
    "R1_profile_correction": {
        "MQ_add_profiles": "6/6 PROFILE_FINITE_AND_SEPARATED",
        "G4": "PASS",
        "condition_number": r1_contract["G4_corrected"]["condition_number"],
        "MQ_eff_eta": eta_b6,
        "MQ_eff_eta_boundary": True,
    },
    "controller_rules": {
        "A_B_bridge": "NOT_IDENTIFIABLE",
        "RegMix_to_B1": "SCENARIO_ONLY",
        "B8": "CONFLICT_EVIDENCE; no probability and no legacy k=-20",
        "joint_Q_p": "NOT_INDEPENDENTLY_OPTIMIZABLE",
    },
}
write_json(RUN / "uncertainty_components.json", uncertainty)

support_rows = [
    ["M0_B1", "N", input_audit["anchors"]["B1_N_min"], input_audit["anchors"]["B1_N_max"], "billion parameters", "Outside range is extrapolation"],
    ["M0_B1", "D", input_audit["anchors"]["B1_D_min"], input_audit["anchors"]["B1_D_max"], "billion tokens", "Outside range is extrapolation"],
    ["MQ-add_B6", "Q_score", 0.1, 0.6, "B6 design scale", "Q>0.6 is frozen stress only"],
    ["A_quality", "Q_baseline", p_contract["quality"]["calibration_support"][0], p_contract["quality"]["calibration_support"][1], "A-side unitless", "No cross-source equality implied"],
    ["mixture", "p", 0.0, 1.0, "17-simplex", "sum(p)=1; preserve zeros; exact feature order in contract"],
    ["joint_Q_p", "free_coordinates", np.nan, np.nan, "structural", "Forbidden without fixed-p quality intervention"],
    ["B8", "quality direction", np.nan, np.nan, "conflict evidence", "Common support and OOS retained separately; no numeric reverse parameter"],
]
pd.DataFrame(support_rows, columns=["module", "quantity", "lower", "upper", "unit", "rule"]).to_csv(
    RUN / "support_and_extrapolation_rules.csv", index=False, encoding="utf-8-sig"
)

validation = pd.read_csv(P / "mixture_audit/regmix_fixed_model_validation.csv")


def metric(scale: str, col: str) -> float:
    row = validation[validation["scale"] == scale]
    if len(row) != 1:
        raise SystemExit(f"MISSING_REGMIX_METRIC:{scale}")
    return float(row.iloc[0][col])


contract = {
    "schema_version": 1,
    "task": "TASK-T06E-INTEGRATE",
    "run_id": "20260925T110904+08",
    "status": "FROZEN_FOR_T07_WORK_ORDER",
    "primary_model": {
        "name": "M0_B1",
        "formula": "L=E+A*N_B^(-alpha)+B*D_B^(-beta)",
        "parameters": {x: float(b1[x]) for x in ["E", "A", "B", "alpha", "beta"]},
        "qualification": "IDENTIFIED_SOURCE_CONDITIONAL_B1",
        "quality_enabled": False,
        "mixture_transport_enabled": False,
    },
    "units": {
        "N_B": "billions of parameters",
        "D_B": "billions of tokens",
        "N_physical": "N_B*1e9",
        "D_physical": "D_B*1e9",
        "training_compute": "6*N_physical*D_physical FLOPs",
        "loss": "source validation cross-entropy; do not assume cross-source comparability without audit",
    },
    "support": {
        "B1_N_B": [input_audit["anchors"]["B1_N_min"], input_audit["anchors"]["B1_N_max"]],
        "B1_D_B": [input_audit["anchors"]["B1_D_min"], input_audit["anchors"]["B1_D_max"]],
        "B6_Q_score_confirmatory": [0.1, 0.6],
        "A_Q_baseline_calibration": p_contract["quality"]["calibration_support"],
        "oos_rule": "Any violated source support is explicitly OUT_OF_SUPPORT; never silently clip.",
    },
    "quality": {
        "main_A_definition": "Q_baseline",
        "sensitivity_A_definition": "Q_C",
        "q_A_star": p_contract["quality"]["q_A_star"],
        "A_B_mapping_status": "NOT_IDENTIFIABLE",
        "MQ_add_B6": {
            "formula": "L=M0_6-k_add*(Q_score-0.6)",
            "parameters": {x: float(b6_add[x]) for x in ["E", "A", "B", "alpha", "beta", "k_add"]},
            "qualification": "B6_SOURCE_CONDITIONAL_ACCEPTED",
            "cross_source_use": "SCENARIO_ONLY",
            "G1_to_G4": [True, True, True, True],
        },
        "MQ_eff": {
            "formula": "L=E+A*N_B^(-alpha)+B*(D_B*exp[-eta*(Q_score-0.6)])^(-beta)",
            "eta": eta_b6,
            "eta_at_lower_bound": True,
            "qualification": "SENSITIVITY_ONLY_WEAKLY_IDENTIFIED",
        },
        "bridges": {"H0": "IDENTIFIED_NULL_BASELINE", "H1": "SCENARIO_ONLY", "H2": "SCENARIO_ONLY", "H3": "SCENARIO_ONLY", "H4": "DIRECTION_ONLY_NOT_OPTIMIZABLE"},
        "B8": "CONFLICT_EVIDENCE; preserve B6 direction, k=0, and B8 reverse direction in parallel",
    },
    "mixture": {
        "feature_order": p_contract["mixture"]["feature_order"],
        "p0": p_contract["mixture"]["p0"],
        "constraint": "p_j>=0 and sum_j p_j=1; preserve zero values",
        "within_1M_status": "SUPPORTED_BY_FROZEN_SOURCE_CONDITIONAL_LINEAR_MODEL",
        "test_1M_mse_improvement": metric("test_1m", "mse_improvement_vs_domain_training_mean"),
        "test_1M_spearman": metric("test_1m", "spearman_equal_domain_mean"),
        "RMSE_60M": metric("test_60m", "rmse_equal_domain_mean"),
        "RMSE_1B": metric("test_1B", "rmse_equal_domain_mean"),
        "transport_to_B1": "SCENARIO_ONLY",
        "tau_p": "FIXED_SCENARIO_ONLY",
        "mixture_transport_enabled": False,
    },
    "joint_Q_p": {
        "independent_optimization_allowed": False,
        "reason": "For fixed domain quality q, Q_mix=p^Tq lies in the p column space; no fixed-p quality intervention is observed.",
        "required_action": "Choose a scenario with Q fixed/derived or p fixed; do not expose both as independent controls.",
    },
    "scenario_registry": {
        "count": 21,
        "ids": registry["scenario_id"].tolist(),
        "seal_sha256": p_contract["scenario_registry"]["seal_sha256"],
        "path": "scenario_registry_filled.csv",
        "no_posthoc_add_delete": True,
    },
    "uncertainty": {
        "joint_draws": "Use saved B1 8-cluster draws and B6 9-N-cluster draws within their source roles; keep structural scenarios separate.",
        "scenario_probabilities": "PROHIBITED_WITHOUT_EVIDENCE",
        "B8_propagation": "Report a separate reverse-direction stress result, never average with B6.",
        "Q_definition_sensitivity": ["Q_baseline", "Q_C"],
    },
    "T07_rules": {
        "primary_model": "M0_B1",
        "quality_enabled": False,
        "mixture_transport_enabled": False,
        "required_budget_count_min": 3,
        "cost_terms": ["6*N_physical*D_physical", "quality_cost_scenario", "attention_context_cost_scenario"],
        "optimization_output": "budget-by-scenario optima with support, boundary, marginal gain, and uncertainty labels; no single universal optimum",
    },
    "provenance": {
        "B_run": str(B.relative_to(ROOT)).replace("\\", "/"),
        "B_R1_run": str(BR1.relative_to(ROOT)).replace("\\", "/"),
        "P_run": str(P.relative_to(ROOT)).replace("\\", "/"),
        "T06_sha256": sha256(T06),
        "T06E_sha256": sha256(T06E),
    },
}
write_json(RUN / "t07_model_contract.json", contract)

boot = pd.read_csv(B / "bootstrap/bootstrap_summary.csv")
parameter_rows = []


def add_parameters(module: str, source: str, row: pd.Series, names: list[str], status: str, t07_role: str) -> None:
    b_row = boot[(boot["source"] == source) & (boot["model"] == row["model"])]
    for name in names:
        qlo = qmed = qhi = np.nan
        if len(b_row) == 1 and f"{name}_p2_5" in b_row.columns:
            qlo = b_row.iloc[0][f"{name}_p2_5"]
            qmed = b_row.iloc[0][f"{name}_median"]
            qhi = b_row.iloc[0][f"{name}_p97_5"]
        parameter_rows.append(
            {
                "module": module,
                "parameter": name,
                "value": float(row[name]),
                "p2_5": qlo,
                "median": qmed,
                "p97_5": qhi,
                "source": source,
                "qualification": status,
                "T07_role": t07_role,
                "estimated_or_scenario": "estimated_source_conditional" if "SCENARIO" not in status else "scenario_only",
            }
        )


add_parameters("M0_B1", "B1", b1, ["E", "A", "B", "alpha", "beta"], "IDENTIFIED_SOURCE_CONDITIONAL", "PRIMARY")
add_parameters("M0_6", "B6", b6_m0, ["E", "A", "B", "alpha", "beta"], "IDENTIFIED_SOURCE_CONDITIONAL", "B6_NULL_REFERENCE")
add_parameters("MQ_add_B6", "B6", b6_add, ["E", "A", "B", "alpha", "beta", "k_add"], "B6_SOURCE_CONDITIONAL_ACCEPTED; CROSS_SOURCE_SCENARIO_ONLY", "QUALITY_SCENARIO")
add_parameters("MQ_eff_B6", "B6", b6_eff, ["E", "A", "B", "alpha", "beta", "eta"], "SENSITIVITY_ONLY; ETA_AT_LOWER_BOUND", "SENSITIVITY")
parameter_rows.extend(
    [
        {"module": "A_quality_anchor", "parameter": "q_A_star", "value": p_contract["quality"]["q_A_star"], "p2_5": np.nan, "median": np.nan, "p97_5": np.nan, "source": "A1_calibration_7_domain_equal", "qualification": "DESCRIPTIVE_RECOMPUTED_SOURCE_STATISTIC", "T07_role": "BRIDGE_ANCHOR", "estimated_or_scenario": "descriptive"},
        {"module": "bridge", "parameter": "r_B1", "value": np.nan, "p2_5": np.nan, "median": np.nan, "p97_5": np.nan, "source": "scenario_registry", "qualification": "FIXED_SCENARIO {0.2,0.6,0.9}", "T07_role": "SCENARIO_ONLY", "estimated_or_scenario": "scenario_only"},
        {"module": "bridge", "parameter": "rho_Q", "value": np.nan, "p2_5": np.nan, "median": np.nan, "p97_5": np.nan, "source": "scenario_registry", "qualification": "FIXED_SCENARIO {0,0.5,1}", "T07_role": "SCENARIO_ONLY", "estimated_or_scenario": "scenario_only"},
        {"module": "mixture_transport", "parameter": "tau_p", "value": np.nan, "p2_5": np.nan, "median": np.nan, "p97_5": np.nan, "source": "scenario_registry", "qualification": "FIXED_SCENARIO {-1,0,0.5,1}; -1 stress", "T07_role": "SCENARIO_ONLY", "estimated_or_scenario": "scenario_only"},
    ]
)
pd.DataFrame(parameter_rows).to_csv(RUN / "t07_parameter_table.csv", index=False, encoding="utf-8-sig")

input_manifest = {
    "schema_version": 1,
    "run_id": "20260925T110904+08",
    "inputs": [
        {"path": str(x.relative_to(ROOT)).replace("\\", "/"), "bytes": x.stat().st_size, "sha256": sha256(x)}
        for x in [
            B / "output_manifest.json",
            BR1 / "output_manifest.json",
            P / "output_manifest.json",
            P / "scenario_registry/SCENARIO_REGISTRY_SEAL.json",
            P / "scenario_registry/scenario_registry_preregistered.csv",
            P / "scenario_registry/scenario_inputs.parquet",
            B / "fit/scaling_parameters_by_source.csv",
            B / "bootstrap/bootstrap_summary.csv",
            BR1 / "identifiability_matrix_B_corrected.csv",
            BR1 / "t07_bside_contract_candidate_corrected.json",
            T06,
            T06E,
        ]
    ],
}
write_json(RUN / "input_manifest.json", input_manifest)
write_json(
    RUN / "environment.json",
    {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "solver": "NONE",
        "model_refit": False,
    },
)
write_json(
    RUN / "run_summary.json",
    {
        "run_id": "20260925T110904+08",
        "status": "COMPLETE",
        "B_R1_review": "PASS",
        "MQ_add": "ACCEPT_B6_SOURCE_RELATION",
        "MQ_add_qualification": "IDENTIFIED_SOURCE_CONDITIONAL_B6; CROSS_SOURCE_SCENARIO_ONLY",
        "MQ_eff": "SENSITIVITY_ONLY; ETA_AT_LOWER_BOUND",
        "A_B_bridge": "NOT_IDENTIFIABLE",
        "RegMix_to_B1": "SCENARIO_ONLY",
        "B8": "CONFLICT_EVIDENCE",
        "primary_model": "M0_B1",
        "quality_enabled": False,
        "mixture_transport_enabled": False,
        "scenario_count": 21,
        "model_refit": False,
        "optimization_started": False,
    },
)
write_json(
    RUN / "command_log.json",
    {"commands": [{"argv": ["python", "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/code/integrate.py"], "purpose": "controller integration without fitting"}]},
)
(RUN / "stage_status.jsonl").write_text(
    json.dumps({"stage": "integrate", "event": "start", "run_id": "20260925T110904+08"}) + "\n" +
    json.dumps({"stage": "integrate", "event": "complete", "run_id": "20260925T110904+08"}) + "\n",
    encoding="utf-8",
)
print(json.dumps({"status": "INTEGRATED_PENDING_VERIFICATION", "scenarios": len(filled)}, ensure_ascii=False))
