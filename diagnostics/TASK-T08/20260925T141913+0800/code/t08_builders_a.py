from __future__ import annotations

import math
import pandas as pd
import numpy as np

from t08_common import ALL_TARGETS, AUX_TARGET, TASKS, TASK_TARGETS, q1_q3_iqr, safe_quantile, empty


def scale_bin(value) -> str:
    if empty(value):
        return "UNKNOWN"
    v = float(value)
    if v <= 3.0:
        return "<=3B"
    if v < 20.0:
        return ">3B to <20B"
    return ">=20B"


def time_window(value, ambiguous: bool) -> str:
    if ambiguous or pd.isna(value):
        return "UNKNOWN_OR_AMBIGUOUS"
    ts = pd.Timestamp(value)
    if ts < pd.Timestamp("2024-01-01"):
        return "PRE_2024"
    if ts <= pd.Timestamp("2024-06-30"):
        return "2024_H1"
    if ts <= pd.Timestamp("2024-12-31"):
        return "2024_H2"
    if ts <= pd.Timestamp("2025-03-13"):
        return "2025_Q1"
    return "AFTER_FORECAST_ORIGIN"


def consensus_value(values, missing_label="UNKNOWN", conflict_label="CONFLICTING") -> str:
    vals = sorted({str(v).strip() for v in values if not empty(v)})
    if not vals:
        return missing_label
    if len(vals) == 1:
        return vals[0]
    return conflict_label


def compute_main_decomposition(residual: pd.DataFrame, x_ref: dict) -> pd.DataFrame:
    main = residual[
        residual["cohort"].eq("main_comparable")
        & residual["split_family"].eq("internal_grouped")
    ].copy()
    main["x_ref_params_B"] = float(x_ref["params_B"])
    main["x_ref_D_tokens_B"] = float(x_ref["D_tokens_B"])
    main["reference_conditional_prediction"] = main["predicted"].astype(float)
    main["scale_associated_component"] = 0.0
    main["conditional_remainder"] = main["observed"].astype(float) - main["predicted"].astype(float)
    main["identity_error"] = main["observed"] - (main["predicted"] + main["conditional_remainder"])
    main["target_role"] = np.where(main["target"].eq(AUX_TARGET), "AUXILIARY_ONLY", "PRIMARY_TASK_VECTOR")
    main["conditional_interval_low"] = main["pi_low"]
    main["conditional_interval_high"] = main["pi_high"]
    main["naming_guard"] = "NON_SCALE_ASSOCIATED_RESIDUAL_OR_CONDITIONAL_REMAINDER"
    main["eligibility"] = "CONDITIONAL_ASSOCIATION_ONLY"
    return main[[
        "cohort", "split_family", "split_id", "selection_source", "effective_candidate_id",
        "model_id", "model_key", "model_family", "params_B", "scale_bin",
        "x_ref_params_B", "x_ref_D_tokens_B", "target", "target_role",
        "observed", "predicted", "reference_conditional_prediction",
        "scale_associated_component", "conditional_remainder", "identity_error",
        "conditional_interval_low", "conditional_interval_high", "naming_guard", "eligibility",
    ]].sort_values(["target", "model_id"]).reset_index(drop=True)


def build_historical_base(crosswalk: pd.DataFrame, wide: pd.DataFrame) -> pd.DataFrame:
    c8meta = crosswalk[crosswalk["source_table"].eq("C8")].drop_duplicates("canonical_model_id").copy()
    meta = crosswalk[crosswalk["source_table"].isin(["C1", "C2"])].copy()
    open_consensus = meta.groupby("canonical_model_id")["open_weights"].agg(
        lambda s: consensus_value(s, "UNKNOWN_OPEN_WEIGHTS", "CONFLICTING_OPEN_WEIGHTS")
    ).rename("open_weights_status")
    license_consensus = meta.groupby("canonical_model_id")["hub_license"].agg(
        lambda s: "LICENSE_RECORDED" if any(not empty(v) for v in s) else "UNKNOWN_LICENSE"
    ).rename("license_status")
    license_name = meta.groupby("canonical_model_id")["hub_license"].agg(
        lambda s: consensus_value(s, "UNKNOWN_LICENSE", "CONFLICTING_LICENSE")
    ).rename("license_value")
    c8meta = c8meta.join(open_consensus, on="canonical_model_id").join(license_consensus, on="canonical_model_id").join(license_name, on="canonical_model_id")
    base = wide.merge(
        c8meta[["c8_model_key", "canonical_model_id", "canonical_name", "model_family", "params_B",
                "submission_date", "date_ambiguous", "hub_license", "open_weights",
                "open_weights_status", "license_status", "license_value", "match_status"]],
        left_on="model_key", right_on="c8_model_key", how="left", validate="one_to_one"
    )
    base["submission_date"] = pd.to_datetime(base["submission_date"], errors="coerce")
    base["date_ambiguous"] = base["date_ambiguous"].fillna(True).astype(bool)
    base["parameter_scale_bin"] = base["params_B"].map(scale_bin)
    base["time_window"] = [time_window(d, a) for d, a in zip(base["submission_date"], base["date_ambiguous"])]
    base["c8_category"] = np.where(base["six_task_complete"].astype(bool), "COMPLETE_SIX_TASK", "PARTIAL_VALID_TASK")
    for task, target in TASK_TARGETS.items():
        base[target] = pd.to_numeric(base[task], errors="coerce") * 100.0
    mean = pd.to_numeric(base["six_task_mean_complete_only"], errors="coerce") * 100.0
    base[AUX_TARGET] = np.where(base["six_task_complete"].astype(bool), mean, np.nan)
    return base


def build_historical_strata(base: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dimensions = [
        ("model_family", "model_family"),
        ("parameter_scale_bin", "parameter_scale_bin"),
        ("open_weights_status", "open_weights_status"),
        ("license_status", "license_status"),
        ("time_window", "time_window"),
    ]
    for target in ALL_TARGETS:
        for dimension, column in dimensions:
            values = sorted(base[column].fillna("UNKNOWN").astype(str).unique().tolist())
            for value in values:
                subset = base[base[column].fillna("UNKNOWN").astype(str).eq(value)]
                n_models = int(len(subset))
                status = "OBSERVED_DESCRIPTION" if n_models >= 5 else "INSUFFICIENT_N"
                scores = pd.to_numeric(subset[target], errors="coerce").dropna()
                q1, q3, iqr = q1_q3_iqr(scores) if status == "OBSERVED_DESCRIPTION" else (None, None, None)
                rows.append({
                    "stratum_dimension": dimension, "stratum_value": value, "benchmark_task": target,
                    "target_role": "AUXILIARY_ONLY" if target == AUX_TARGET else "PRIMARY_TASK_VECTOR",
                    "n_models": n_models, "n_complete_models": int(subset["six_task_complete"].sum()),
                    "n_partial_models": int((~subset["six_task_complete"].astype(bool)).sum()),
                    "n_valid_scores": int(len(scores)), "n_missing_scores": n_models - int(len(scores)),
                    "missing_rate": (n_models - len(scores)) / n_models if n_models else None,
                    "median_score_pct": safe_quantile(scores, 0.50) if status == "OBSERVED_DESCRIPTION" else None,
                    "q1_score_pct": q1, "q3_score_pct": q3, "iqr_score_pct": iqr,
                    "unit": "leaderboard points (0-100) from C8 raw fraction x 100",
                    "status": status,
                    "eligibility": "OBSERVED_DESCRIPTION" if status == "OBSERVED_DESCRIPTION" else "INSUFFICIENT_N",
                    "partial_rule": "partial models enter only actually valid tasks; never the six-task mean",
                    "damaged_json_rule": "four damaged JSON files affect coverage only and receive no score",
                })
        scores = pd.to_numeric(base[target], errors="coerce").dropna()
        q1, q3, iqr = q1_q3_iqr(scores)
        n_models = int(len(base))
        rows.append({
            "stratum_dimension": "benchmark_task", "stratum_value": target, "benchmark_task": target,
            "target_role": "AUXILIARY_ONLY" if target == AUX_TARGET else "PRIMARY_TASK_VECTOR",
            "n_models": n_models, "n_complete_models": int(base["six_task_complete"].sum()),
            "n_partial_models": int((~base["six_task_complete"].astype(bool)).sum()),
            "n_valid_scores": int(len(scores)), "n_missing_scores": n_models - int(len(scores)),
            "missing_rate": (n_models - len(scores)) / n_models,
            "median_score_pct": safe_quantile(scores, 0.50), "q1_score_pct": q1, "q3_score_pct": q3, "iqr_score_pct": iqr,
            "unit": "leaderboard points (0-100) from C8 raw fraction x 100",
            "status": "OBSERVED_DESCRIPTION", "eligibility": "OBSERVED_DESCRIPTION",
            "partial_rule": "partial models enter only actually valid tasks; never the six-task mean",
            "damaged_json_rule": "four damaged JSON files affect coverage only and receive no score",
        })
    return pd.DataFrame(rows)


def build_taskwise_progress(main: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in ALL_TARGETS:
        q = main[main["target"].eq(target)]
        low = float(pd.to_numeric(q["conditional_interval_low"], errors="coerce").mean())
        high = float(pd.to_numeric(q["conditional_interval_high"], errors="coerce").mean())
        q1, q3, iqr = q1_q3_iqr(pd.to_numeric(q["conditional_remainder"], errors="coerce"))
        rows.append({
            "benchmark_task": target, "target_role": "AUXILIARY_ONLY" if target == AUX_TARGET else "PRIMARY_TASK_VECTOR",
            "n_main_models": int(q["model_id"].nunique()),
            "constant_baseline_points": float(pd.to_numeric(q["observed"], errors="coerce").mean()),
            "conditional_interval_low_points": low, "conditional_interval_high_points": high,
            "scale_associated_component_mean_points": float(q["scale_associated_component"].mean()),
            "scale_associated_component_max_abs_points": float(q["scale_associated_component"].abs().max()),
            "conditional_remainder_median_points": safe_quantile(q["conditional_remainder"], 0.50),
            "conditional_remainder_q1_points": q1, "conditional_remainder_q3_points": q3,
            "conditional_remainder_iqr_points": iqr,
            "time_trend_validated_for_extrapolation": False, "time_extrapolation_status": "UNVALIDATED",
            "benchmark_future_eligibility": "CONDITIONAL_BASELINE_ONLY",
            "progress_12m_status": "NOT_IDENTIFIABLE_PROGRESS",
            "progress_24m_status": "NOT_IDENTIFIABLE_PROGRESS",
            "benchmark_increment_12m_points": None, "benchmark_increment_24m_points": None,
            "eligibility": "CONDITIONAL_ASSOCIATION_ONLY",
        })
    return pd.DataFrame(rows)


def build_growth_support(bridge: pd.DataFrame):
    records = bridge[bridge["params_B"].notna() & bridge["D_tokens_B"].notna()].copy()
    records["N_physical"] = pd.to_numeric(records["params_B"], errors="coerce") * 1e9
    records["D_physical"] = pd.to_numeric(records["D_tokens_B"], errors="coerce") * 1e9
    records["compute_proxy_flops"] = 6.0 * records["N_physical"] * records["D_physical"]
    family_period = []
    detail = []
    for family, group in records.groupby("model_family", dropna=False):
        group = group.sort_values(["submission_date", "params_B", "Model"], na_position="last").reset_index(drop=True)
        for i in range(len(group) - 1):
            a, b = group.iloc[i], group.iloc[i + 1]
            if a["date_ambiguous"] or b["date_ambiguous"] or pd.isna(a["submission_date"]) or pd.isna(b["submission_date"]):
                continue
            dt = (pd.Timestamp(b["submission_date"]) - pd.Timestamp(a["submission_date"])).days
            valid = 90 <= dt <= 730
            rate = None
            if valid and a["compute_proxy_flops"] > 0 and b["compute_proxy_flops"] > 0:
                rate = math.log(float(b["compute_proxy_flops"]) / float(a["compute_proxy_flops"])) / (dt / 365.25)
                midpoint = pd.Timestamp(a["submission_date"]) + (pd.Timestamp(b["submission_date"]) - pd.Timestamp(a["submission_date"])) / 2
                family_period.append({
                    "model_family": family, "period": f"{midpoint.year}Q{((midpoint.month - 1) // 3) + 1}",
                    "annual_log_growth": rate, "start_model": a["Model"], "end_model": b["Model"],
                })
            detail.append({
                "model_family": family, "start_model": a["Model"], "end_model": b["Model"],
                "start_date": pd.Timestamp(a["submission_date"]).date().isoformat(),
                "end_date": pd.Timestamp(b["submission_date"]).date().isoformat(),
                "interval_days": dt, "rule_90_to_730_days": valid,
                "N_observed": True, "D_observed": True, "annual_log_growth": rate,
                "status": "VALID_PAIR" if valid else "EXCLUDED_INTERVAL",
            })
    med = pd.DataFrame(family_period)
    if len(med):
        med = med.groupby(["model_family", "period"], as_index=False).agg(
            annual_log_growth=("annual_log_growth", "median"),
            n_pairs_in_family_period=("annual_log_growth", "size"),
        )
    n_families = int(med["model_family"].nunique()) if len(med) else 0
    n_intervals = int(len(med))
    identifiable = bool(n_families >= 3 and n_intervals >= 10)
    support = {
        "n_observed_ND_records": int(len(records)), "n_observed_ND_families": int(records["model_family"].nunique()),
        "n_candidate_adjacent_pairs": int(len(detail)), "n_valid_family_level_intervals": n_intervals,
        "n_independent_model_families": n_families, "min_families_required": 3,
        "min_family_level_intervals_required": 10, "identifiable": identifiable,
        "conservative_growth_rate_annual_log": None, "base_growth_rate_annual_log": None,
        "optimistic_growth_rate_annual_log": None,
        "reason_if_not_identifiable": None if identifiable else "fewer than 3 independent model families or fewer than 10 valid family-level intervals; no imputation or external growth assumptions allowed",
    }
    if identifiable:
        family_medians = med.groupby("model_family")["annual_log_growth"].median()
        support["conservative_growth_rate_annual_log"] = float(family_medians.quantile(0.25))
        support["base_growth_rate_annual_log"] = float(family_medians.quantile(0.50))
        support["optimistic_growth_rate_annual_log"] = float(family_medians.quantile(0.75))
    return support, pd.DataFrame(detail)
