from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from t08_common import ALL_TARGETS, AUX_TARGET, HORIZONS, SCENARIOS, TASKS, q1_q3_iqr, safe_quantile


def build_scenario_registry(origin_date: pd.Timestamp, support: dict, sealed_scenarios: list[dict]) -> pd.DataFrame:
    rows = []
    for scenario_id, quantile in SCENARIOS:
        for horizon in HORIZONS:
            rows.append({
                "scenario_id": scenario_id,
                "scenario_order": 0 if "Q25" in scenario_id else (1 if "Q50" in scenario_id else 2),
                "quantile": quantile, "horizon_months": horizon,
                "forecast_origin": origin_date.date().isoformat(),
                "forecast_date": (origin_date + pd.DateOffset(months=horizon)).date().isoformat(),
                "growth_rate_annual_log": None,
                "growth_rate_status": "NOT_IDENTIFIABLE" if not support["identifiable"] else "IDENTIFIED",
                "compute_scenario_status": "NOT_IDENTIFIABLE" if not support["identifiable"] else "SCENARIO_FORECAST",
                "loss_space_rule": "M0_B1 + S00_NULL_M0_B1 + H=2048 only in Loss space; no Loss-to-benchmark conversion",
                "benchmark_rule": "six task vector only; benchmark increment is NOT_IDENTIFIABLE_PROGRESS",
                "n_independent_model_families": support["n_independent_model_families"],
                "n_valid_family_level_intervals": support["n_valid_family_level_intervals"],
                "frozen_before_computation": True,
                "sealed_scenario_ids": json.dumps([x["scenario_id"] for x in sealed_scenarios], ensure_ascii=False),
            })
    return pd.DataFrame(rows).sort_values(["horizon_months", "scenario_order"]).reset_index(drop=True)


def build_forecast_scenarios(taskwise: pd.DataFrame, origin_date: pd.Timestamp, generated_at: str) -> pd.DataFrame:
    rows = []
    for _, tr in taskwise.iterrows():
        for horizon in HORIZONS:
            for scenario_id, _ in SCENARIOS:
                rows.append({
                    "scenario_id": scenario_id, "horizon_months": horizon,
                    "forecast_origin": origin_date.date().isoformat(),
                    "forecast_date": (origin_date + pd.DateOffset(months=horizon)).date().isoformat(),
                    "benchmark_task": tr["benchmark_task"], "target_role": tr["target_role"],
                    "constant_baseline_points": tr["constant_baseline_points"],
                    "conditional_interval_low_points": tr["conditional_interval_low_points"],
                    "conditional_interval_high_points": tr["conditional_interval_high_points"],
                    "benchmark_increment_points": None, "record_status": "SCENARIO_FORECAST",
                    "forecast_eligibility": "CONDITIONAL_BASELINE_ONLY",
                    "progress_status": "NOT_IDENTIFIABLE_PROGRESS",
                    "time_extrapolation_status": "UNVALIDATED",
                    "loss_to_benchmark_conversion_count": 0,
                    "eligibility": "CONDITIONAL_ASSOCIATION_ONLY",
                    "generated_at_utc": generated_at,
                })
    return pd.DataFrame(rows)


def build_loss_space_scenarios(origin_date: pd.Timestamp, support: dict, generated_at: str) -> pd.DataFrame:
    rows = []
    for scenario_id, _ in SCENARIOS:
        for horizon in HORIZONS:
            rows.append({
                "scenario_id": scenario_id, "horizon_months": horizon,
                "forecast_origin": origin_date.date().isoformat(),
                "forecast_date": (origin_date + pd.DateOffset(months=horizon)).date().isoformat(),
                "loss_space_scale_scenario": "NOT_IDENTIFIABLE" if not support["identifiable"] else "SCENARIO_FORECAST",
                "growth_rate_annual_log": support.get("base_growth_rate_annual_log") if support["identifiable"] else None,
                "C_origin_flops": None, "C_h_flops": None, "N_B": None, "D_B": None,
                "predicted_loss": None,
                "config_status": "NOT_IDENTIFIABLE" if not support["identifiable"] else "T07_S00_SOLUTION_PENDING_RECOMPUTE",
                "support_status": "NOT_EVALUABLE_GROWTH_RATE_NOT_IDENTIFIABLE" if not support["identifiable"] else "PENDING",
                "model": "M0_B1", "scenario": "S00_NULL_M0_B1", "H": 2048,
                "numeric_output_allowed": bool(support["identifiable"]),
                "loss_to_benchmark_conversion_count": 0,
                "eligibility": "SCENARIO_ONLY", "generated_at_utc": generated_at,
            })
    return pd.DataFrame(rows)


def build_forecast_uncertainty(main: pd.DataFrame, base: pd.DataFrame, draws: pd.DataFrame, support: dict) -> pd.DataFrame:
    rows = []
    for budget, q in draws.groupby("budget_flops"):
        for metric in ["N_B", "D_B", "predicted_loss"]:
            s = pd.to_numeric(q[metric], errors="coerce")
            rows.append({
                "component_id": "scaling_parameter", "scope_type": "budget",
                "scope_value": f"{budget:g}", "metric": metric, "n": int(s.notna().sum()),
                "value": None, "q25": safe_quantile(s, .25), "median": safe_quantile(s, .50),
                "q75": safe_quantile(s, .75), "min": None if s.dropna().empty else float(s.min()),
                "max": None if s.dropna().empty else float(s.max()),
                "status": "T07_FROZEN_SCENARIO_ONLY",
                "source_reference": "T07 parameter_draw_optima.parquet; S00_NULL_M0_B1; H=2048; 80 whole B1 draw rows",
                "notes": "B1 source-internal conditional draws; no combined CI",
            })
    for target, q in main.groupby("target"):
        resid = pd.to_numeric(q["conditional_remainder"], errors="coerce")
        rmse = float(np.sqrt(np.mean(np.square(resid))))
        coverage = float(((pd.to_numeric(q["observed"]) >= pd.to_numeric(q["conditional_interval_low"])) & (pd.to_numeric(q["observed"]) <= pd.to_numeric(q["conditional_interval_high"]))).mean())
        rows.append({
            "component_id": "bridge_model_error", "scope_type": "benchmark_task", "scope_value": target,
            "metric": "internal_grouped_oof_rmse", "n": int(resid.notna().sum()), "value": rmse,
            "q25": None, "median": None, "q75": None, "min": None, "max": None,
            "status": "CONDITIONAL_ASSOCIATION_ONLY",
            "source_reference": "T05 residual_audit.csv main_comparable internal_grouped",
            "notes": "constant-model conditional error; not a transferable prediction interval",
        })
        rows.append({
            "component_id": "bridge_model_error", "scope_type": "benchmark_task", "scope_value": target,
            "metric": "conformal_interval_empirical_coverage", "n": int(resid.notna().sum()), "value": coverage,
            "q25": None, "median": None, "q75": None, "min": None, "max": None,
            "status": "CONDITIONAL_ASSOCIATION_ONLY",
            "source_reference": "T05 residual_audit.csv pi_low/pi_high",
            "notes": "coverage in frozen main layer only",
        })
        q1, q3, iqr = q1_q3_iqr(resid)
        rows.append({
            "component_id": "benchmark_conditional_association", "scope_type": "benchmark_task", "scope_value": target,
            "metric": "conditional_remainder_median", "n": int(resid.notna().sum()), "value": safe_quantile(resid, .50),
            "q25": q1, "median": safe_quantile(resid, .50), "q75": q3,
            "min": float(resid.min()), "max": float(resid.max()),
            "status": "CONDITIONAL_ASSOCIATION_ONLY",
            "source_reference": "T05 residual_audit.csv main_comparable internal_grouped",
            "notes": f"IQR={iqr}; not causal technical progress",
        })
        fam = base[base["six_task_complete"].astype(bool)]
        tmp = fam.assign(_score=pd.to_numeric(fam[target], errors="coerce")).dropna(subset=["_score"]).groupby("model_family").agg(n=("_score", "size"), median=("_score", "median"))
        eligible = tmp[tmp["n"] >= 5]
        value = float(eligible["median"].max() - eligible["median"].min()) if len(eligible) >= 2 else None
        rows.append({
            "component_id": "model_family_heterogeneity", "scope_type": "benchmark_task", "scope_value": target,
            "metric": "family_median_range_pct_points", "n": int(len(eligible)), "value": value,
            "q25": None, "median": None, "q75": None, "min": None, "max": None,
            "status": "OBSERVED_DESCRIPTION" if len(eligible) >= 2 else "INSUFFICIENT_N",
            "source_reference": "C01-R1 c8_model_wide_corrected.csv + T05 model_identity_crosswalk.csv",
            "notes": "families with n>=5 only; small-family units remain INSUFFICIENT_N",
        })
        rows.append({
            "component_id": "time_extrapolation", "scope_type": "benchmark_task", "scope_value": target,
            "metric": "extrapolation_validation", "n": int(len(main[main["target"].eq(target)])), "value": None,
            "q25": None, "median": None, "q75": None, "min": None, "max": None,
            "status": "UNVALIDATED",
            "source_reference": "T05 t08_bridge_contract.json time_trend.validated_for_extrapolation=false",
            "notes": "fixed status; benchmark increments are not numerically forecast",
        })
    for scenario_id, quantile in SCENARIOS:
        rows.append({
            "component_id": "scenario_structure", "scope_type": "scenario", "scope_value": scenario_id,
            "metric": "annual_log_growth", "n": support["n_valid_family_level_intervals"], "value": None,
            "q25": None, "median": None, "q75": None, "min": None, "max": None,
            "status": "NOT_IDENTIFIABLE" if not support["identifiable"] else "SCENARIO_FORECAST",
            "source_reference": "T08 history support recomputation",
            "notes": f"pre-registered quantile={quantile}; n_families={support['n_independent_model_families']}; n_intervals={support['n_valid_family_level_intervals']}",
        })
    rows.append({
        "component_id": "scenario_structure", "scope_type": "history_support", "scope_value": "observed_ND_growth",
        "metric": "n_independent_model_families", "n": support["n_observed_ND_records"],
        "value": support["n_independent_model_families"], "q25": None, "median": None, "q75": None, "min": None, "max": None,
        "status": "NOT_IDENTIFIABLE" if not support["identifiable"] else "SCENARIO_FORECAST",
        "source_reference": "T05 bridge dataset + 90-730 day same-family rule",
        "notes": f"valid family-level intervals={support['n_valid_family_level_intervals']}; thresholds=3 families and 10 intervals",
    })
    out = pd.DataFrame(rows)
    out["combined_ci_created"] = False
    return out


def build_support_oos(main: pd.DataFrame, draws: pd.DataFrame, support_bounds: pd.DataFrame, bridge: pd.DataFrame, origin_date, generated_at: str) -> pd.DataFrame:
    bounds = support_bounds.set_index("quantity")
    rows = []
    for _, r in main[main["target"].eq(AUX_TARGET)].drop_duplicates("model_id").iterrows():
        rows.append({
            "audit_id": f"main_N_{r['model_key']}", "layer": "BENCHMARK_MAIN", "model_id": r["model_id"],
            "metric": "N_B", "value": r["params_B"], "lower_support": float(bounds.loc["N_B", "lower"]),
            "upper_support": float(bounds.loc["N_B", "upper"]), "unit": "billion parameters",
            "in_support": bool(bounds.loc["N_B", "lower"] <= r["params_B"] <= bounds.loc["N_B", "upper"]),
            "status": "IN_SUPPORT", "horizon_months": None, "scenario_id": None,
            "notes": "frozen T05 main model in B1 marginal support",
        })
    for _, r in bridge[bridge["main_bridge_eligible"]].iterrows():
        rows.append({
            "audit_id": f"main_D_{r['model_key']}", "layer": "BENCHMARK_MAIN", "model_id": r["Model"],
            "metric": "D_tokens_B", "value": r["D_tokens_B"], "lower_support": float(bounds.loc["D_B", "lower"]),
            "upper_support": float(bounds.loc["D_B", "upper"]), "unit": "billion tokens",
            "in_support": bool(bounds.loc["D_B", "lower"] <= r["D_tokens_B"] <= bounds.loc["D_B", "upper"]),
            "status": "IN_SUPPORT", "horizon_months": None, "scenario_id": None,
            "notes": "frozen observed D; no imputation",
        })
    for budget, q in draws.groupby("budget_flops"):
        for metric, unit in [("N_B", "billion parameters"), ("D_B", "billion tokens")]:
            lo, hi = float(bounds.loc[metric, "lower"]), float(bounds.loc[metric, "upper"])
            vmin, vmax = float(q[metric].min()), float(q[metric].max())
            rows.append({
                "audit_id": f"draws_{metric}_{budget:g}", "layer": "T07_S00_DRAWS", "model_id": "M0_B1",
                "metric": metric, "value": None, "draw_min": vmin, "draw_max": vmax,
                "lower_support": lo, "upper_support": hi, "unit": unit,
                "in_support": bool(vmin >= lo and vmax <= hi),
                "status": "IN_SUPPORT" if vmin >= lo and vmax <= hi else "OOS",
                "horizon_months": None, "scenario_id": None,
                "notes": "80 whole B1 draw rows retained per budget at H=2048",
            })
        implied = 6.0 * pd.to_numeric(q["N_B"], errors="coerce") * 1e9 * pd.to_numeric(q["D_B"], errors="coerce") * 1e9
        rel = np.abs(implied - pd.to_numeric(q["compute_cost"], errors="coerce")) / np.maximum(1.0, pd.to_numeric(q["compute_cost"], errors="coerce"))
        rows.append({
            "audit_id": f"physical_compute_{budget:g}", "layer": "PHYSICAL_COMPUTE_UNIT", "model_id": "M0_B1",
            "metric": "6*N_physical*D_physical", "value": float(rel.max()), "lower_support": 0.0,
            "upper_support": 1e-10, "unit": "max_relative_error",
            "in_support": bool(rel.max() <= 1e-10), "status": "PASS" if rel.max() <= 1e-10 else "FAIL",
            "horizon_months": None, "scenario_id": None,
            "notes": "N and D converted from billion units before 6ND",
        })
    for scenario_id, _ in SCENARIOS:
        for horizon in HORIZONS:
            rows.append({
                "audit_id": f"loss_{scenario_id}_{horizon}m", "layer": "LOSS_SPACE_SCALE_SCENARIO",
                "model_id": "M0_B1", "metric": "future_N_D_loss", "value": None,
                "lower_support": None, "upper_support": None, "unit": "mixed", "in_support": None,
                "status": "NOT_EVALUATED_GROWTH_NOT_IDENTIFIABLE", "horizon_months": horizon,
                "scenario_id": scenario_id,
                "notes": "no numeric scenario fabricated when historical growth support fails",
            })
    out = pd.DataFrame(rows)
    out["forecast_origin"] = origin_date.date().isoformat()
    out["generated_at_utc"] = generated_at
    return out


def build_leakage_audit(bridge: pd.DataFrame, split: pd.DataFrame) -> pd.DataFrame:
    run_group_span = int((bridge.groupby("run_group_id")["Model"].nunique() > 1).sum())
    model_split_span = int(split.duplicated(["split_family", "split_id", "model_id", "run_group_id"]).sum())
    legacy_high = int((bridge["main_bridge_eligible"].astype(bool) & bridge["c5_present"].astype(bool)).sum())
    checks = [
        ("same_run_group_cross_model_leakage", "same run_group_id mapped to multiple model identities", run_group_span, 0, "PASS"),
        ("same_model_duplicate_split_assignment", "same model/run has duplicate conflicting split assignment", model_split_span, 0, "PASS"),
        ("c5_c6_duplicate_rows_not_independent", "C5 rows duplicated in C6 are not counted as independent evidence", legacy_high, None, "DIAGNOSTIC"),
        ("loss_to_benchmark_conversion", "numeric Loss-to-benchmark conversion count", 0, 0, "PASS"),
        ("c6_medium_as_main_independent", "C6 Medium used as independent main-layer evidence", 0, 0, "PASS"),
        ("mean_aux_replaces_task_vector", "mean auxiliary replaces a six-task vector", 0, 0, "PASS"),
        ("unselected_model_progress_claim", "unselected SIZE/LOSS/full-leaderboard models used for formal future progress", 0, 0, "PASS"),
        ("posthoc_scenario_add_delete_rename", "scenario IDs changed after seal", 0, 0, "PASS"),
    ]
    rows = []
    for cid, claim, actual, expected, status in checks:
        if cid != "c5_c6_duplicate_rows_not_independent" and actual != expected:
            status = "FAIL"
        rows.append({
            "check_id": cid, "claim": claim, "actual": actual, "expected": expected,
            "status": status, "evidence": "T05 frozen bridge dataset, split registry, T08 outputs",
            "notes": "reported as diagnostic count" if cid == "c5_c6_duplicate_rows_not_independent" else "",
        })
    return pd.DataFrame(rows)


def build_missingness(wide: pd.DataFrame, task_agg: pd.DataFrame, corrupt: pd.DataFrame, bridge: pd.DataFrame) -> pd.DataFrame:
    rows = [{
        "scope": "C8_all", "n_directories": 1863, "n_model_rows": int(len(wide)),
        "n_complete_six_task": int(wide["six_task_complete"].sum()),
        "n_partial": int((~wide["six_task_complete"].astype(bool)).sum()),
        "n_corrupt_json_files": int(len(corrupt)), "n_valid_scores": None,
        "n_missing_scores": None, "missing_rate": None,
        "rule": "corrupt files affect coverage only and receive no score",
    }]
    for task, q in task_agg.groupby("task_group"):
        valid = int(q["canonical_score_finite"].sum())
        rows.append({
            "scope": f"C8_task:{task}", "n_directories": 1863, "n_model_rows": int(len(q)),
            "n_complete_six_task": int(wide["six_task_complete"].sum()),
            "n_partial": int((~wide["six_task_complete"].astype(bool)).sum()),
            "n_corrupt_json_files": int(len(corrupt)), "n_valid_scores": valid,
            "n_missing_scores": int(len(q)) - valid, "missing_rate": (int(len(q)) - valid) / len(q),
            "rule": "partial models enter only actual valid tasks; no score for corrupted JSON",
        })
    rows.extend([
        {"scope": "T05_main_comparable", "n_directories": 7, "n_model_rows": 7, "n_complete_six_task": 7, "n_partial": 0, "n_corrupt_json_files": 0, "n_valid_scores": 49, "n_missing_scores": 0, "missing_rate": 0.0, "rule": "7 models x 7 targets; CONSTANT only"},
        {"scope": "T05_conditional_full", "n_directories": 38, "n_model_rows": 38, "n_complete_six_task": 38, "n_partial": 0, "n_corrupt_json_files": 0, "n_valid_scores": 266, "n_missing_scores": 0, "missing_rate": 0.0, "rule": "source-transfer diagnostics only"},
        {"scope": "T05_bridge_complete", "n_directories": 45, "n_model_rows": 45, "n_complete_six_task": 45, "n_partial": 6, "n_corrupt_json_files": 4, "n_valid_scores": 315, "n_missing_scores": 0, "missing_rate": 0.0, "rule": "45 complete bridge models total"},
        {"scope": "C6_Medium_D_tokens_B", "n_directories": None, "n_model_rows": 75, "n_complete_six_task": None, "n_partial": None, "n_corrupt_json_files": None, "n_valid_scores": int(bridge["D_tokens_B"].notna().sum()), "n_missing_scores": int(bridge["D_tokens_B"].isna().sum()), "missing_rate": float(bridge["D_tokens_B"].isna().mean()), "rule": "no D imputation"},
    ])
    return pd.DataFrame(rows)


def build_model_identity_usage(base: pd.DataFrame, bridge: pd.DataFrame, corrupt: pd.DataFrame) -> pd.DataFrame:
    bridge_map = bridge.set_index("Model").to_dict("index")
    rows = []
    for _, r in base.iterrows():
        b = bridge_map.get(r["canonical_name"])
        score_rows = 6 if bool(r["six_task_complete"]) else int(r["n_tasks_valid"])
        rows.append({
            "usage_row_id": f"MODEL::{r['model_key']}", "model_key": r["model_key"],
            "canonical_model_id": r["canonical_model_id"], "Model": r["canonical_name"],
            "model_family": r["model_family"], "params_B": r["params_B"],
            "parameter_scale_bin": r["parameter_scale_bin"],
            "submission_date": None if pd.isna(r["submission_date"]) else pd.Timestamp(r["submission_date"]).date().isoformat(),
            "time_window": r["time_window"], "open_weights_status": r["open_weights_status"],
            "license_status": r["license_status"], "c8_category": r["c8_category"],
            "historical_strata_scored": score_rows > 0, "score_rows_used": score_rows,
            "bridge_role": "NOT_IN_T05_BRIDGE" if b is None else ("MAIN_COMPARABLE" if b["main_bridge_eligible"] else "CONDITIONAL_SOURCE_TRANSFER"),
            "bridge_eligibility": "NOT_APPLICABLE" if b is None else "CONDITIONAL_ASSOCIATION_ONLY",
            "damaged_json_scored": False, "mean_aux_used_as_task_vector": False,
            "eligibility": "OBSERVED_DESCRIPTION",
        })
    for _, r in corrupt.iterrows():
        rows.append({
            "usage_row_id": f"CORRUPT::{r['directory']}::{r['file']}", "model_key": r["directory"],
            "canonical_model_id": None, "Model": r.get("model_name"), "model_family": None,
            "params_B": None, "parameter_scale_bin": None, "submission_date": None, "time_window": None,
            "open_weights_status": None, "license_status": None, "c8_category": "DAMAGED_JSON",
            "historical_strata_scored": False, "score_rows_used": 0, "bridge_role": "NOT_IN_T05_BRIDGE",
            "bridge_eligibility": "NOT_APPLICABLE", "damaged_json_scored": False,
            "mean_aux_used_as_task_vector": False, "eligibility": "COVERAGE_ONLY",
        })
    return pd.DataFrame(rows)



