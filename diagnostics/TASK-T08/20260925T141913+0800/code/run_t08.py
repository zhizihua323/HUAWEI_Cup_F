from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CODE_DIR = Path(__file__).resolve().parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
from t08_common import (ALL_TARGETS, AUX_TARGET, HORIZONS, RUN_ID, SCENARIOS, TASKS,
                        append_jsonl, iso_local, iso_utc, read_json, relpath, sha256_file,
                        verify_output_manifest, write_csv, write_json)
from t08_builders_a import build_growth_support, build_historical_base, build_historical_strata, build_taskwise_progress, compute_main_decomposition
from t08_builders_b import (build_forecast_scenarios, build_forecast_uncertainty, build_leakage_audit,
                            build_loss_space_scenarios, build_missingness, build_model_identity_usage,
                            build_scenario_registry, build_support_oos)
from t08_checks import build_checks

WORKSPACE = Path(__file__).resolve().parents[4]
T05_DIR = WORKSPACE / "diagnostics/TASK-T05/20260925T113355+0800"
T07_DIR = WORKSPACE / "diagnostics/TASK-T07/20260925T113744+08"
T06_DIR = WORKSPACE / "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08"
C01_DIR = WORKSPACE / "diagnostics/TASK-C01/20260924T175553+08"
C01R1_DIR = WORKSPACE / "diagnostics/TASK-C01-R1/20260924T225308+08"
T05 = {"contract": T05_DIR/"t08_bridge_contract.json", "bridge": T05_DIR/"bridge_analysis_dataset.parquet",
       "prediction": T05_DIR/"prediction_table.parquet", "residual": T05_DIR/"residual_audit.csv",
       "split": T05_DIR/"split_registry.csv", "crosswalk": T05_DIR/"model_identity_crosswalk.csv",
       "decision": T05_DIR/"identifiability_decision.json", "manifest": T05_DIR/"output_manifest.json"}
T07 = {"interface": T07_DIR/"t08_or_paper_interface.json", "budget_optima": T07_DIR/"budget_scenario_optima.csv",
       "uncertainty": T07_DIR/"uncertainty_summary.csv", "support_bounds": T07_DIR/"support_bounds.csv",
       "unit_audit": T07_DIR/"unit_conversion_audit.csv", "parameter_draws": T07_DIR/"parameter_draw_optima.parquet",
       "manifest": T07_DIR/"output_manifest.json"}
T06 = {"contract": T06_DIR/"t07_model_contract.json", "manifest": T06_DIR/"output_manifest.json"}
C01 = {"wide": C01R1_DIR/"c8_model_wide_corrected.csv", "task_aggregate": C01R1_DIR/"c8_model_task_aggregate_corrected.csv",
       "corrupt": C01_DIR/"c8_corrupt_files.csv", "identity_audit": C01_DIR/"model_identity_audit.csv",
       "date_audit": C01_DIR/"date_audit.csv", "missingness": C01_DIR/"missingness.csv",
       "parse_log": C01_DIR/"c8_parse_log.csv", "manifest": C01_DIR/"output_manifest.json", "r1_manifest": C01R1_DIR/"output_manifest.json"}
RAW = {"C1": WORKSPACE/"F题/real_attachments/C_efficiency_evolution/leaderboard_cleaned.csv",
       "C2": WORKSPACE/"F题/real_attachments/C_efficiency_evolution/leaderboard_enhanced.csv",
       "C3": WORKSPACE/"F题/real_attachments/C_efficiency_evolution/leaderboard_extended_timeseries.csv",
       "C4": WORKSPACE/"F题/real_attachments/C_efficiency_evolution/epoch_all_ai_models.csv"}


def stage(root, name, status, artifact=None, detail=None):
    append_jsonl(root/"stage_status.jsonl", {"run_id": RUN_ID, "stage": name, "status": status,
        "timestamp_local": iso_local(), "timestamp_utc": iso_utc(), "artifact": artifact, "detail": detail or {}})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--run-id", default=RUN_ID)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    root = workspace/"diagnostics"/"TASK-T08"/args.run_id
    root.mkdir(parents=True, exist_ok=True)
    if (root/"forecast_seal.json").exists():
        raise RuntimeError("refusing to overwrite an existing sealed T08 run")
    stage(root, "initialize", "STARTED", detail={"workspace": str(workspace)})
    protected = {"TASK-T05": verify_output_manifest(T05["manifest"], T05_DIR),
                 "TASK-T07": verify_output_manifest(T07["manifest"], T07_DIR),
                 "TASK-T06E-INTEGRATE": verify_output_manifest(T06["manifest"], T06_DIR),
                 "TASK-C01": verify_output_manifest(C01["manifest"], C01_DIR),
                 "TASK-C01-R1": verify_output_manifest(C01["r1_manifest"], C01R1_DIR)}
    if any(v["status"] != "PASS" for v in protected.values()):
        raise RuntimeError(f"frozen manifest mismatch: {protected}")
    paths = []
    for role, mapping in [("TASK-T05", T05), ("TASK-T07", T07), ("TASK-T06E-INTEGRATE", T06), ("TASK-C01/C01-R1", C01), ("readonly_metadata", RAW)]:
        for key, path in mapping.items():
            if key not in {"manifest", "r1_manifest"}:
                paths.append((role, path))
    paths += [("protected_manifest", T05["manifest"]), ("protected_manifest", T07["manifest"]),
              ("protected_manifest", T06["manifest"]), ("protected_manifest", C01["manifest"]), ("protected_manifest", C01["r1_manifest"])]
    inputs = []
    for role, path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        inputs.append({"role": role, "path": relpath(path, workspace), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    input_manifest = {"task_id": "TASK-T08", "run_id": args.run_id, "generated_at_utc": iso_utc(),
                      "workspace": str(workspace), "inputs": inputs, "protected_manifest_checks": protected,
                      "no_t05_t07_refit": True, "no_c8_json_reparse": True}
    write_json(root/"input_manifest.json", input_manifest)
    stage(root, "input_manifest", "PASS", "input_manifest.json", {"n_inputs": len(inputs)})

    contract = read_json(T05["contract"]); read_json(T05["decision"]); read_json(T07["interface"]); read_json(T06["contract"])
    bridge = pd.read_parquet(T05["bridge"]); pd.read_parquet(T05["prediction"]); residual = pd.read_csv(T05["residual"])
    split = pd.read_csv(T05["split"]); crosswalk = pd.read_csv(T05["crosswalk"]); wide = pd.read_csv(C01["wide"])
    task_agg = pd.read_csv(C01["task_aggregate"]); corrupt = pd.read_csv(C01["corrupt"]); parse_log = pd.read_csv(C01["parse_log"])
    support_bounds = pd.read_csv(T07["support_bounds"]); pd.read_csv(T07["budget_optima"]); draws_all = pd.read_parquet(T07["parameter_draws"])
    main_bridge = bridge[bridge["main_bridge_eligible"].astype(bool)].copy()
    cond_bridge = bridge[~bridge["main_bridge_eligible"].astype(bool)].copy()
    frozen = {k: v["candidate_id"] for k, v in contract["benchmark_prediction"]["per_task_structures"].items()}
    if contract["eligibility"] != "CONDITIONAL_ASSOCIATION_ONLY" or contract["time_trend"]["validated_for_extrapolation"] is not False:
        raise RuntimeError("T05 eligibility/time guard changed")
    if set(frozen) != set(ALL_TARGETS) or any(v != "CONSTANT" for v in frozen.values()):
        raise RuntimeError("T05 CONSTANT target vector changed")
    if (len(main_bridge), len(cond_bridge), len(bridge)) != (7, 38, 45):
        raise RuntimeError("T05 bridge counts changed")
    if len(wide) != 1860 or int(wide["six_task_complete"].sum()) != 1854 or int((~wide["six_task_complete"].astype(bool)).sum()) != 6 or len(corrupt) != 4:
        raise RuntimeError("C8 corrected counts changed")

    origin_rows = crosswalk[crosswalk["source_table"].isin(["C1", "C2", "C8"]) & crosswalk["match_status"].eq("exact_raw") & (~crosswalk["date_ambiguous"].astype(bool))].copy()
    origin_rows["submission_date"] = pd.to_datetime(origin_rows["submission_date"], errors="coerce")
    origin_rows = origin_rows[origin_rows["submission_date"].notna()]
    submission_max = origin_rows["submission_date"].max()
    parse_ok = parse_log[parse_log["parse_status"].eq("ok")].copy()
    parse_ok["eval_timestamp"] = pd.to_datetime(parse_ok["eval_unix_date"], unit="s", errors="coerce", utc=True).dt.tz_convert("UTC")
    eval_max = parse_ok["eval_timestamp"].max()
    submission_date = pd.Timestamp(submission_max).date()
    origin_date = pd.Timestamp(max(submission_date, eval_max.date()))
    if origin_date != pd.Timestamp("2025-03-13"):
        raise RuntimeError(f"unexpected forecast origin {origin_date}")
    x_ref = {"definition": "constant-model reference point; m_t(x) ignores x", "params_B": float(main_bridge["params_B"].median()),
             "D_tokens_B": float(main_bridge["D_tokens_B"].median()), "N_physical": float(main_bridge["params_B"].median())*1e9,
             "D_physical": float(main_bridge["D_tokens_B"].median())*1e9, "in_support": True}
    sealed = [{"scenario_id": sid, "definition_quantile": q, "horizons_months": HORIZONS,
               "growth_rate_status": "TO_BE_EVALUATED_AFTER_SEAL"} for sid, q in SCENARIOS]
    seal = {"seal_version": "T08-v1", "task_id": "TASK-T08", "run_id": args.run_id,
            "sealed_at_local": iso_local(), "sealed_at_utc": iso_utc(), "forecast_origin_date": origin_date.date().isoformat(),
            "forecast_origin_rule": "maximum day-granularity observation date among C01-audited, identity-unique, non-ambiguous C1/C2/C8 records; C8 eval timestamps verified for the same date",
            "origin_submission_max": pd.Timestamp(submission_max).date().isoformat(), "origin_c8_eval_max": eval_max.isoformat(),
            "horizon_dates": {str(h): (origin_date+pd.DateOffset(months=h)).date().isoformat() for h in HORIZONS},
            "scenario_ids": [x["scenario_id"] for x in sealed], "scenarios": sealed,
            "frozen_model": "T05 CONSTANT for all six tasks and auxiliary mean", "frozen_eligibility": "CONDITIONAL_ASSOCIATION_ONLY",
            "time_trend_validated_for_extrapolation": False, "main_scale_reference": x_ref,
            "loss_benchmark_separation": True, "loss_to_benchmark_conversion_allowed": False,
            "growth_rate_rule": {"same_model_family": True, "sortable_dates": True, "interval_days": [90, 730],
                                 "N_observed": True, "D_observed": True, "D_imputation_allowed": False,
                                 "compute_formula": "6*N_physical*D_physical", "family_period_aggregation": "median within model family and period, then independent family distribution",
                                 "min_independent_families": 3, "min_family_level_intervals": 10},
            "manifest_guards": {k: {"status": v["status"], "entries": v["entries"], "mismatch_count": v["mismatch_count"]} for k, v in protected.items()}}
    write_json(root/"forecast_seal.json", seal)
    stage(root, "forecast_seal", "FROZEN", "forecast_seal.json", {"forecast_origin": origin_date.date().isoformat(), "scenario_ids": seal["scenario_ids"]})
    support, growth_detail = build_growth_support(bridge)
    registry = build_scenario_registry(origin_date, support, sealed)
    write_csv(root/"scenario_registry.csv", registry)
    stage(root, "scenario_registry", "FROZEN", "scenario_registry.csv", {"rows": len(registry), "identifiable": support["identifiable"]})

    main_decomp = compute_main_decomposition(residual, x_ref); write_csv(root/"scale_non_scale_decomposition.csv", main_decomp)
    stage(root, "scale_non_scale_decomposition", "PASS", "scale_non_scale_decomposition.csv", {"rows": len(main_decomp)})
    base = build_historical_base(crosswalk, wide); strata = build_historical_strata(base); write_csv(root/"historical_strata_summary.csv", strata)
    stage(root, "historical_strata_summary", "PASS", "historical_strata_summary.csv", {"rows": len(strata)})
    taskwise = build_taskwise_progress(main_decomp); write_csv(root/"taskwise_progress.csv", taskwise)
    stage(root, "taskwise_progress", "PASS", "taskwise_progress.csv", {"rows": len(taskwise)})
    generated = iso_utc(); forecast = build_forecast_scenarios(taskwise, origin_date, generated); write_csv(root/"forecast_12m_24m_scenarios.csv", forecast)
    loss = build_loss_space_scenarios(origin_date, support, generated); write_csv(root/"loss_space_scale_scenarios.csv", loss)
    stage(root, "forecast_scenarios", "PASS", "forecast_12m_24m_scenarios.csv;loss_space_scale_scenarios.csv", {"benchmark_rows": len(forecast), "loss_rows": len(loss)})
    draws = draws_all[(draws_all["scenario_id"].eq("S00_NULL_M0_B1")) & (draws_all["H"].eq(2048))].copy()
    uncertainty = build_forecast_uncertainty(main_decomp, base, draws, support); write_csv(root/"forecast_uncertainty.csv", uncertainty)
    stage(root, "forecast_uncertainty", "PASS", "forecast_uncertainty.csv", {"rows": len(uncertainty)})
    s00 = draws_all[(draws_all["scenario_id"].eq("S00_NULL_M0_B1")) & (draws_all["H"].eq(2048))].copy()
    oos = build_support_oos(main_decomp, s00, support_bounds, bridge, origin_date, generated); write_csv(root/"support_oos_audit.csv", oos)
    leakage = build_leakage_audit(bridge, split); write_csv(root/"leakage_audit.csv", leakage)
    missing = build_missingness(wide, task_agg, corrupt, bridge); write_csv(root/"missingness_and_denominators.csv", missing)
    usage = build_model_identity_usage(base, bridge, corrupt); write_csv(root/"model_identity_usage.csv", usage)
    stage(root, "audits", "PASS", "support_oos_audit.csv;leakage_audit.csv;missingness_and_denominators.csv;model_identity_usage.csv", {"rows": [len(oos), len(leakage), len(missing), len(usage)]})

    write_json(root/"environment.json", {"task_id": "TASK-T08", "run_id": args.run_id, "python": sys.version,
        "platform": platform.platform(), "pandas": pd.__version__, "numpy": np.__version__, "timezone": "Asia/Shanghai",
        "generated_at_local": iso_local(), "generated_at_utc": iso_utc(), "workspace": str(workspace)})
    write_json(root/"command_log.json", {"task_id": "TASK-T08", "run_id": args.run_id,
        "commands": [{"stage": "execution", "command": f"python {root/'code/run_t08.py'} --workspace {workspace} --run-id {args.run_id}", "run_at_utc": iso_utc()}],
        "no_t05_t07_refit": True, "no_network": True})

    ctx = {"protected": protected, "n_main": len(main_bridge), "n_cond": len(cond_bridge), "n_bridge": len(bridge),
           "n_complete": int(wide["six_task_complete"].sum()), "n_partial": int((~wide["six_task_complete"].astype(bool)).sum()),
           "n_corrupt": len(corrupt), "frozen_candidates": frozen, "scale_max": float(main_decomp["scale_associated_component"].abs().max()),
           "identity_max_error": float(main_decomp["identity_error"].abs().max()), "conditional_D_missing": int(cond_bridge["D_tokens_B"].isna().sum()),
           "damaged_scores": int(usage[usage["c8_category"].eq("DAMAGED_JSON")]["score_rows_used"].sum()), "support": support,
           "numeric_growth_count": int(forecast["benchmark_increment_points"].notna().sum() + loss["growth_rate_annual_log"].notna().sum()),
           "unit_fail": int((oos[oos["layer"].eq("PHYSICAL_COMPUTE_UNIT")]["status"] != "PASS").sum()), "b1_count": int(draws["b1_replicate"].nunique()),
           "sealed_ids": set(seal["scenario_ids"]), "registry_ids": set(registry["scenario_id"]), "forecast_ids": set(forecast["scenario_id"]), "taskwise": taskwise}
    checks = build_checks(ctx); checks_df = pd.DataFrame(checks)
    write_json(root/"checks.json", {"task_id": "TASK-T08", "run_id": args.run_id, "checks": checks, "n_checks": len(checks),
        "n_pass": int((checks_df["status"] == "PASS").sum()), "n_fail": int((checks_df["status"] == "FAIL").sum()), "generated_at_utc": iso_utc()})
    stage(root, "checks", "PASS", "checks.json", {"n_checks": len(checks), "n_fail": int((checks_df["status"] == "FAIL").sum())})

    task_entries = {r["benchmark_task"]: {"baseline_points": r["constant_baseline_points"],
        "conditional_interval_low_points": r["conditional_interval_low_points"], "conditional_interval_high_points": r["conditional_interval_high_points"],
        "scale_associated_component_mean_points": r["scale_associated_component_mean_points"],
        "conditional_remainder_median_points": r["conditional_remainder_median_points"],
        "future_eligibility": r["benchmark_future_eligibility"], "progress_12m_status": r["progress_12m_status"],
        "progress_24m_status": r["progress_24m_status"]} for _, r in taskwise.iterrows()}
    paper = {"task_id": "TASK-T08", "run_id": args.run_id, "status": "COMPLETE_PENDING_CONTROLLER_REVIEW",
        "forecast_origin": origin_date.date().isoformat(), "eligibility": "CONDITIONAL_ASSOCIATION_ONLY",
        "time_extrapolation": "UNVALIDATED",
        "allowed_core_conclusions": ["The frozen main benchmark model is CONSTANT for all six tasks and the auxiliary mean.",
            "The main-layer scale-associated component is exactly zero.",
            "Observed benchmark values decompose as fitted constant plus a non-scale associated residual/conditional remainder.",
            "Future benchmark progress is NOT_IDENTIFIABLE_PROGRESS; only the conditional baseline can be displayed.",
            "Loss-space scaling scenarios are separate and are not identifiable because historical compute-growth support failed."],
        "prohibited_wording": ["algorithmic progress", "engineering progress", "causal technological progress", "validated time-trend forecast",
            "Loss improvement converted to benchmark points", "six-task mean replacing the task vector"],
        "taskwise_entries": task_entries, "support": {"benchmark_main_models": 7, "benchmark_conditional_models": 38,
            "bridge_complete_models": 45, "c8_complete_partial_corrupt": [1854, 6, 4],
            "growth_model_families": support["n_independent_model_families"], "growth_family_level_intervals": support["n_valid_family_level_intervals"],
            "loss_space_support": "NOT_EVALUABLE_GROWTH_RATE_NOT_IDENTIFIABLE"},
        "uncertainty_components": ["scaling_parameter", "bridge_model_error", "benchmark_conditional_association", "model_family_heterogeneity", "time_extrapolation", "scenario_structure"],
        "loss_benchmark_conversion_count": 0}
    write_json(root/"t08_paper_interface.json", paper)
    summary = {"task_id": "TASK-T08", "run_id": args.run_id, "status": "COMPLETE_PENDING_CONTROLLER_REVIEW",
        "forecast_origin": origin_date.date().isoformat(), "forecast_origin_rule": seal["forecast_origin_rule"],
        "historical_growth_support": support, "main_benchmark": {"eligibility": "CONDITIONAL_ASSOCIATION_ONLY", "models": 7,
            "tasks": TASKS, "auxiliary_mean": AUX_TARGET, "all_frozen_candidates": "CONSTANT", "scale_associated_component": 0.0,
            "conditional_remainder_name": "non-scale associated residual / conditional remainder", "benchmark_future_eligibility": "CONDITIONAL_BASELINE_ONLY",
            "benchmark_progress": "NOT_IDENTIFIABLE_PROGRESS"},
        "loss_space": {"model": "M0_B1", "scenario": "S00_NULL_M0_B1", "H": 2048,
            "growth_rate_status": "NOT_IDENTIFIABLE" if not support["identifiable"] else "IDENTIFIED",
            "numerical_loss_scenarios_emitted": bool(support["identifiable"]), "loss_to_benchmark_conversion_count": 0},
        "counts": {"c8_complete": int(wide["six_task_complete"].sum()), "c8_partial": int((~wide["six_task_complete"].astype(bool)).sum()),
            "c8_corrupt_json": len(corrupt), "t05_main": len(main_bridge), "t05_conditional": len(cond_bridge), "t05_total": len(bridge),
            "output_rows": {"scale_non_scale_decomposition": len(main_decomp), "historical_strata_summary": len(strata), "taskwise_progress": len(taskwise),
                            "forecast_12m_24m_scenarios": len(forecast), "forecast_uncertainty": len(uncertainty),
                            "loss_space_scale_scenarios": len(loss), "support_oos_audit": len(oos)}},
        "checks_file": "checks.json", "verification_file": "verification.json", "generated_at_utc": iso_utc()}
    write_json(root/"run_summary.json", summary)
    stage(root, "run_summary", "PASS", "run_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


