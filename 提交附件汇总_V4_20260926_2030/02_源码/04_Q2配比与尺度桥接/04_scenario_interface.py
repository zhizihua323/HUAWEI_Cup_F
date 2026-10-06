# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

RUN = Path(__file__).resolve().parents[1]
WS = RUN.parents[2]
REG_PATH = RUN / "scenario_registry/scenario_registry_preregistered.csv"
SEAL_PATH = RUN / "scenario_registry/SCENARIO_REGISTRY_SEAL.json"
REG = pd.read_csv(REG_PATH)
SEAL = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
if hashlib.sha256(REG_PATH.read_bytes()).hexdigest() != SEAL["registry_sha256"]:
    raise RuntimeError("scenario registry hash mismatch")
expected_ids = list(SEAL["scenario_ids_in_order"])
if len(expected_ids) != 21 or REG["scenario_id"].tolist() != expected_ids:
    raise RuntimeError("scenario registry ID set/order mismatch")

q_anchor = json.loads((RUN / "quality_anchor/q_A_anchor.json").read_text(encoding="utf-8"))
bridge = json.loads((RUN / "bridge/quality_bridge_scenarios.json").read_text(encoding="utf-8"))
qq = q_anchor["q_A_star"]; qc = q_anchor["q_C_star_sensitivity"]
support_min = bridge["Q_support"]["Q_baseline_calibration_min"]
support_max = bridge["Q_support"]["Q_baseline_calibration_max"]
h3_steps = pd.read_csv(RUN / "bridge/H3_mapping_steps.csv", float_precision="round_trip")
model = json.loads((WS / "solution/outputs/mixture/model.json").read_text(encoding="utf-8"))
features = list(model["features"])
p0 = np.asarray(model["reference_p"], dtype=float)
if len(features) != 17 or len(p0) != 17 or not np.isclose(p0.sum(), 1.0, rtol=0, atol=1e-15):
    raise RuntimeError("invalid frozen 17-domain p0")

def h3_at(q: float) -> tuple[float, str, bool]:
    known = h3_steps.loc[h3_steps["source_kind"].eq("Q_baseline_calibration")].copy()
    if q < support_min:
        return float(known.iloc[0]["mapped_Q_B"]), "OUT_OF_SUPPORT_LOW", False
    if q > support_max:
        return float(known.iloc[-1]["mapped_Q_B"]), "OUT_OF_SUPPORT_HIGH", False
    pos = int(np.searchsorted(known["q"].to_numpy(float), q, side="right") - 1)
    pos = max(0, min(pos, len(known) - 1))
    row = known.iloc[pos]
    return float(row["mapped_Q_B"]), str(row["support_status"]), bool(row["usable_for_numeric_prediction"])

def h2_at(q: float, b: float) -> float:
    return float(0.6 + b * (q - qq))

def bridge_value(bridge_name: str, q_source: str, b: float | None) -> tuple[float | None, str, bool]:
    if bridge_name == "H0":
        return None, "NOT_APPLICABLE_NULL", False
    if bridge_name == "H4":
        return None, "DIRECTION_ONLY_NOT_NUMERIC", False
    q = qq if q_source == "Q_baseline" else qc
    if bridge_name == "H1":
        return float(q), "ASSUMPTION_DEFINED_NO_SUPPORT_ESTIMATE", True
    if bridge_name == "H2":
        return h2_at(q, float(b)), "ASSUMPTION_DEFINED_NO_SUPPORT_ESTIMATE", True
    if bridge_name == "H3":
        return h3_at(q)
    raise RuntimeError(f"unknown bridge {bridge_name}")

scenario_rows = []
for _, r in REG.iterrows():
    sid = str(r["scenario_id"])
    bridge_name = str(r["bridge"])
    qsrc = str(r["q_source"])
    b = None if pd.isna(r["h_parameter_b"]) else float(r["h_parameter_b"])
    q_input = qq if qsrc == "Q_baseline" else (qc if qsrc == "Q_C" else None)
    mapped_q, support_status, mapping_usable = bridge_value(bridge_name, qsrc, b)
    if sid == "S10_RHOQ_00":
        quality_enabled = False
    else:
        quality_enabled = bridge_name not in {"H0", "H4"} and qsrc in {"Q_baseline", "Q_C"} and float(r["rho_Q"]) != 0.0
    numeric_status = "B_SIDE_PARAMETER_SLOT_PENDING"
    if sid in {"S07_H4_DIRECTION_ONLY", "S17_B8_REVERSE_COMMON_SUPPORT"}:
        numeric_status = "NO_NUMERIC_PREDICTION"
    elif sid in {"S00_NULL_M0_B1"}:
        numeric_status = "MODEL_DEFAULT_PENDING_CONTROLLER_B1_FILL"
    elif sid in {"S14_MIX_TAU05", "S15_MIX_TAU10", "S16_MIX_TAUM10_STRESS"}:
        numeric_status = "MIXTURE_TRANSPORT_SLOT_PENDING"
    scenario_rows.append({
        "scenario_order": int(r["scenario_order"]),
        "scenario_id": sid,
        "family": str(r["family"]),
        "base_scenario": str(r["base_scenario"]),
        "bridge": bridge_name,
        "q_source": qsrc,
        "q_input_at_reference": q_input,
        "h_parameter_b": b,
        "mapped_Q_B_at_reference": mapped_q,
        "support_status_at_reference": support_status,
        "mapping_usable_at_reference": bool(mapping_usable),
        "r_B1_fixed_scenario": None if pd.isna(r["r_B1"]) else float(r["r_B1"]),
        "rho_Q_fixed_scenario": None if pd.isna(r["rho_Q"]) else float(r["rho_Q"]),
        "quality_transport": str(r["quality_transport"]),
        "transport_parameter": str(r["transport_parameter"]) if not pd.isna(r["transport_parameter"]) else None,
        "tau_p_fixed_scenario": None if pd.isna(r["tau_p"]) else float(r["tau_p"]),
        "quality_effect_enabled": bool(quality_enabled),
        "p_fixed_at_p0": True,
        "delta_p_vector_sum": 0.0,
        "mixture_transport_enabled_in_default_model": False,
        "requires_fixed_p_quality_intervention": bool(quality_enabled),
        "joint_Q_p_independent_optimizable": False,
        "B6_quality_parameter_slot": "PENDING_BRANCH_B_NOT_FILLED_BY_P" if (quality_enabled and bridge_name in {"H1","H2","H3"}) else None,
        "B8_common_support_slot": "PENDING_BRANCH_B_NO_LEGACY_k_MINUS_20" if sid == "S17_B8_REVERSE_COMMON_SUPPORT" else None,
        "numeric_prediction_status": numeric_status,
        "loss_prediction_in_P_branch": None,
        "eligibility": str(r["eligibility"]),
        "registry_seal_sha256": SEAL["registry_sha256"],
        "no_B_model_fitted_in_P": True,
    })
scenarios = pd.DataFrame(scenario_rows)
if len(scenarios) != 21 or set(scenarios["scenario_id"]) != set(expected_ids):
    raise RuntimeError("scenario_inputs row set mismatch")
scenarios.to_parquet(RUN / "scenario_registry/scenario_inputs.parquet", index=False)

# P-branch identifiability matrix.
id_rows = [
    ("q_A_star", "DESCRIPTIVE_RECOMPUTED_SOURCE_STATISTIC", "A1_calibration_only", True, "Seven-domain equal-weight mean; not a fitted parameter."),
    ("F_A_equal_domain_CDF", "EMPIRICAL_REFERENCE_DETERMINISTIC", "A1_calibration_only", True, "Seven domain ECDFs each weighted 1/7."),
    ("F_B_unique_Q_CDF", "EMPIRICAL_DESIGN_CDF_DETERMINISTIC", "B6_design_levels_only", True, "Eight unique Q levels each weighted 1/8."),
    ("H0", "IDENTIFIED_NULL_BASELINE", "no_map", False, "k=0 baseline; no quality effect."),
    ("H1", "SCENARIO_ONLY", "identity_assumption", False, "Identity is not identified across A and B."),
    ("H2", "SCENARIO_ONLY", "fixed_b", False, "b is fixed at 0.5, 1, or 2 by preregistration."),
    ("H3", "SCENARIO_ONLY", "equal_domain_ECDF_quantile_map", False, "Empirical quantile coupling does not identify A-to-B correspondence."),
    ("H4", "DIRECTION_ONLY_NOT_OPTIMIZABLE", "B6_direction_only", False, "No A-side numeric Loss benefit."),
    ("A_B_mapping", "NOT_IDENTIFIABLE", "no_join_key_and_no_fixed_p_quality_variation", False, "No estimated map is produced."),
    ("r_B1", "FIXED_SCENARIO", "registry", False, "Values 0.2, 0.6, 0.9 are scenarios, not estimates."),
    ("rho_Q", "FIXED_SCENARIO", "registry", False, "Values 0, 0.5, 1 are scenarios, not estimates."),
    ("tau_p", "FIXED_SCENARIO", "registry", False, "Values -1, 0, 0.5, 1 are scenarios; -1 is stress only."),
    ("k_add_B6", "PARAMETER_SLOT_PENDING_CONTROLLER", "branch_B_candidate_not_read_by_P", False, "P registers a slot and does not fill a B-side value."),
    ("eta_B6", "PARAMETER_SLOT_PENDING_CONTROLLER", "branch_B_candidate_not_read_by_P", False, "Effective-data transport must be filled later by the controller."),
    ("RegMix_linear_coefficients", "FROZEN_EXISTING_MODEL_SOURCE_CONDITIONAL", "solution/outputs/mixture/model.json", True, "Reused without refitting or model-family reselection."),
    ("RegMix_1M_mixture_effects", "IDENTIFIED_WITHIN_SOURCE_1M", "A6/A7_frozen_linear_predictions", True, "Only same-scale RegMix mixture effect is supported."),
    ("RegMix_cross_scale_mixture_effects", "SCENARIO_ONLY", "A8-A11_reporting", False, "60M/1B are cross-scale transport diagnostics, not recalibration."),
    ("Q_mix_gamma", "NOT_IDENTIFIABLE", "p_Q_double_counting", False, "Q_mix lies in the p column space for fixed q."),
    ("B8_reverse_direction", "DIRECTION_ONLY_NOT_OPTIMIZABLE", "common_support_slot_pending", False, "No legacy boundary k=-20 and no out-of-support numeric generation."),
    ("10B_70B_estimates", "ESTIMATED_SCENARIO_NOT_TRUTH", "A12-A15", False, "They are not validation truths or pass counts."),
]
idmat = pd.DataFrame(id_rows, columns=["component","status","evidence_source","numeric_use_allowed_in_P","constraint"])
idmat.to_csv(RUN / "identifiability_matrix_P.csv", index=False, encoding="utf-8")

cond = json.loads((WS / "solution/outputs/mixture/test_1m_conditional_intervals.json").read_text(encoding="utf-8"))
unc = {
    "run_id": RUN.name,
    "principle": "Components are kept separate and are not combined into a single confidence interval.",
    "components": [
        {"name":"q_A_anchor","type":"descriptive deterministic recomputation","uncertainty_claim":None,"note":"No bootstrap or random resampling was performed in P."},
        {"name":"A_equal_domain_CDF","type":"empirical deterministic reference","uncertainty_claim":None,"note":"Ties retained; each domain contributes weight 1/7."},
        {"name":"B6_unique_Q_CDF","type":"empirical design-level reference","uncertainty_claim":None,"note":"Repeated N-D grid occurrences do not add weight."},
        {"name":"A_to_B_bridge","type":"scenario assumption uncertainty","uncertainty_claim":None,"note":"H1-H3 are SCENARIO_ONLY; mapping status is NOT_IDENTIFIABLE."},
        {"name":"RegMix_linear_model","type":"frozen existing model uncertainty","uncertainty_claim":None,"note":"Existing test_1m interval is carried only as a frozen conditional artifact."},
        {"name":"RegMix_cross_scale_transport","type":"structural transport uncertainty","uncertainty_claim":None,"note":"60M and 1B are reported without recalibration or selection."},
        {"name":"B8_conflict","type":"direction conflict uncertainty","uncertainty_claim":None,"note":"Reverse direction remains a common-support slot; no probability assigned."},
        {"name":"p_Q_double_counting","type":"structural non-identifiability","uncertainty_claim":None,"note":"Fixed q makes Q_mix a p-column-space identity."},
        {"name":"B_side_parameters","type":"pending controller integration slot","uncertainty_claim":None,"note":"P does not read or estimate B1/B6/B7/B8 parameters."}
    ],
    "frozen_existing_conditional_interval": {
        "source": "solution/outputs/mixture/test_1m_conditional_intervals.json",
        "scope": cond["scope"],
        "model": cond["model"],
        "metrics": cond["metrics"],
        "lower": cond["lower"],
        "upper": cond["upper"],
        "reused_not_recomputed_in_P": True
    },
    "probabilities_assigned_to_scenarios": False,
    "scenario_averaging_performed": False,
}
(RUN / "uncertainty_components_P.json").write_text(json.dumps(unc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

contract = {
    "contract_status": "CANDIDATE_P_ONLY_PENDING_CONTROLLER",
    "task_id": "TASK-T06E-P",
    "run_id": RUN.name,
    "primary_model": {"name":"M0_B1","quality_enabled":False,"mixture_transport_enabled":False,"meaning":"Identified default only for controller integration; no B1 parameters are estimated in this branch."},
    "units": {"physical_N_multiplier":1e9,"physical_D_multiplier":1e9,"note":"B-table values are billions and must not be inserted directly into 6ND."},
    "quality": {
        "official_main_Q":"Q_baseline",
        "q_A_star":qq,
        "calibration_support":[support_min,support_max],
        "Q_C_role":"SENSITIVITY_ONLY",
        "Q_C_star":qc,
        "A_to_B_mapping_status":"NOT_IDENTIFIABLE",
        "H0":"k=0 and no map call",
        "H1":"h(q)=q SCENARIO_ONLY",
        "H2":"h(q)=0.6+b*(q-q_A_star), b fixed in {0.5,1,2} SCENARIO_ONLY",
        "H3":"h(q)=F_B^{-1}(F_A(q)); equal-domain A CDF and B6 unique-level CDF SCENARIO_ONLY",
        "H4":"DIRECTION_ONLY_NOT_OPTIMIZABLE",
        "out_of_support":"UNUSABLE; never silently clip or fill a missing domain",
        "Q_C_reuses_same_q_A_star_and_F_A":True
    },
    "mixture": {
        "feature_order":features,
        "p0":p0.tolist(),
        "p_simplex_required":True,
        "preserve_zero_values":True,
        "linear_model_frozen":True,
        "model_family_reselection_allowed":False,
        "within_1M_effect_status":"SUPPORTED_BY_FROZEN_SOURCE_CONDITIONAL_LINEAR_MODEL",
        "cross_scale_effect_status":"SCENARIO_ONLY",
        "p_Q_joint_independent_optimization_allowed":False,
        "missing_quality_domain_policy":"UNMAPPED; do not fill; do not renormalize six mapped domains as a 17-domain total"
    },
    "scenario_registry": {
        "path":"scenario_registry/scenario_registry_preregistered.csv",
        "seal_path":"scenario_registry/SCENARIO_REGISTRY_SEAL.json",
        "seal_sha256":SEAL["registry_sha256"],
        "scenario_count":21,
        "scenario_ids":expected_ids,
        "no_add_delete_reorder_after_seal":True,
        "cartesian_product_generated":False
    },
    "pending_controller_parameters": {
        "B1_parameters":"SOURCE-SPECIFIC_PENDING",
        "B6_k_add_or_eta":"SOURCE-SPECIFIC_PENDING",
        "B8_reverse_common_support":"DIRECTION_ONLY_PENDING",
        "A_B_map":"NOT_IDENTIFIABLE_SCENARIO_ONLY"
    },
    "allowed_numeric_prediction_status": {
        "quality_scenarios":"B_SIDE_PARAMETER_SLOT_PENDING",
        "S07_S17":"NO_NUMERIC_PREDICTION"
    },
    "forbidden": [
        "Do not combine Q and p as independently tunable coordinates without a fixed-p quality intervention.",
        "Do not average scenario parameters or assign scenario probabilities without evidence.",
        "Do not select a scenario by lowest Loss.",
        "Do not use 10B or 70B estimated outputs as truth.",
        "Do not start T07 from this candidate contract."
    ]
}
(RUN / "t07_candidate/t07_scenario_contract_candidate.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

stage = {
    "status":"PASS",
    "scenario_count":len(scenarios),
    "scenario_ids_exact":scenarios["scenario_id"].tolist()==expected_ids,
    "quality_enabled_scenarios":int(scenarios["quality_effect_enabled"].sum()),
    "numeric_prediction_filled_in_P":int(scenarios["loss_prediction_in_P_branch"].notna().sum()),
    "joint_Q_p_independent_optimizable_scenarios":int(scenarios["joint_Q_p_independent_optimizable"].sum()),
    "B_side_values_filled_in_P":False,
    "T07_started":False,
    "integration_started":False,
}
(RUN / "t07_candidate/stage_summary.json").write_text(json.dumps(stage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(stage, ensure_ascii=False))

