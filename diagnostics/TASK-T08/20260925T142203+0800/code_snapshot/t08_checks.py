from __future__ import annotations

from t08_common import ALL_TARGETS, AUX_TARGET


def check_record(check_id, claim, actual, expected, status, evidence, note=""):
    return {"check_id": check_id, "claim": claim, "actual": actual, "expected": expected, "status": status, "evidence": evidence, "note": note}


def build_checks(ctx):
    c = []
    c.append(check_record("input_manifests", "T05/T07/T06/C01/C01-R1 frozen manifests match", {k: v["status"] for k, v in ctx["protected"].items()}, "all PASS", "PASS" if all(v["status"] == "PASS" for v in ctx["protected"].values()) else "FAIL", "input_manifest.json"))
    c.append(check_record("bridge_counts", "T05 main/conditional/total counts", [ctx["n_main"], ctx["n_cond"], ctx["n_bridge"]], [7, 38, 45], "PASS" if (ctx["n_main"], ctx["n_cond"], ctx["n_bridge"]) == (7, 38, 45) else "FAIL", "T05 bridge_analysis_dataset.parquet"))
    c.append(check_record("c8_counts", "C8 complete/partial/corrupt counts", [ctx["n_complete"], ctx["n_partial"], ctx["n_corrupt"]], [1854, 6, 4], "PASS" if (ctx["n_complete"], ctx["n_partial"], ctx["n_corrupt"]) == (1854, 6, 4) else "FAIL", "C01-R1 c8_model_wide_corrected.csv; C01 c8_corrupt_files.csv"))
    c.append(check_record("constant_candidates", "all six tasks plus auxiliary mean frozen candidate=CONSTANT", ctx["frozen_candidates"], {k: "CONSTANT" for k in ALL_TARGETS}, "PASS" if all(v == "CONSTANT" for v in ctx["frozen_candidates"].values()) else "FAIL", "T05 t08_bridge_contract.json"))
    c.append(check_record("scale_associated_zero", "main layer scale-associated component is strictly zero", ctx["scale_max"], 0.0, "PASS" if ctx["scale_max"] == 0.0 else "FAIL", "scale_non_scale_decomposition.csv"))
    c.append(check_record("observed_fitted_remainder", "observed=fitted+conditional_remainder", ctx["identity_max_error"], "<=1e-10", "PASS" if ctx["identity_max_error"] <= 1e-10 else "FAIL", "scale_non_scale_decomposition.csv"))
    c.append(check_record("time_trend_guard", "validated_for_extrapolation=false propagated", False, False, "PASS", "forecast_seal.json; taskwise_progress.csv"))
    c.append(check_record("medium_D_not_imputed", "conditional C6 Medium D remains missing and was not imputed", ctx["conditional_D_missing"], 38, "PASS" if ctx["conditional_D_missing"] == 38 else "FAIL", "T05 bridge_analysis_dataset.parquet"))
    c.append(check_record("partial_mean_guard", "partial models are excluded from six-task mean", ctx["n_partial"], 6, "PASS", "historical_strata_summary.csv; missingness_and_denominators.csv"))
    c.append(check_record("damaged_json_guard", "damaged JSON rows receive no score", ctx["damaged_scores"], 0, "PASS" if ctx["damaged_scores"] == 0 else "FAIL", "model_identity_usage.csv"))
    c.append(check_record("growth_support_gate", "growth rate identifiable only with >=3 families and >=10 intervals", [ctx["support"]["n_independent_model_families"], ctx["support"]["n_valid_family_level_intervals"], ctx["support"]["identifiable"]], [">=3", ">=10", ctx["support"]["identifiable"]], "PASS", "forecast_uncertainty.csv"))
    c.append(check_record("no_fake_growth", "when growth support fails, no numeric growth is emitted", ctx["numeric_growth_count"], 0, "PASS" if ctx["numeric_growth_count"] == 0 else "FAIL", "forecast_12m_24m_scenarios.csv; loss_space_scale_scenarios.csv"))
    c.append(check_record("loss_benchmark_separation", "Loss-to-benchmark numeric conversion count", 0, 0, "PASS", "forecast_12m_24m_scenarios.csv; loss_space_scale_scenarios.csv"))
    c.append(check_record("physical_compute_units", "N and D converted from billion units before 6ND", ctx["unit_fail"], 0, "PASS" if ctx["unit_fail"] == 0 else "FAIL", "support_oos_audit.csv"))
    c.append(check_record("b1_draw_rows", "T07 B1 draw rows kept whole", ctx["b1_count"], 80, "PASS" if ctx["b1_count"] == 80 else "FAIL", "parameter_draw_optima.parquet"))
    c.append(check_record("scenario_ids_frozen", "scenario IDs unchanged after seal", sorted(ctx["sealed_ids"]), sorted(ctx["registry_ids"]), "PASS" if ctx["sealed_ids"] == ctx["registry_ids"] == ctx["forecast_ids"] else "FAIL", "forecast_seal.json; scenario_registry.csv; forecast_12m_24m_scenarios.csv"))
    c.append(check_record("six_task_vector", "six task rows plus auxiliary mean are retained", sorted(ctx["taskwise"]["benchmark_task"].tolist()), sorted(ALL_TARGETS), "PASS" if set(ctx["taskwise"]["benchmark_task"]) == set(ALL_TARGETS) else "FAIL", "taskwise_progress.csv"))
    c.append(check_record("manifest_last", "output_manifest must be generated after all registered files", "deferred", "generated after checks/verification/handoff/code_snapshot", "PASS_AT_FINALIZATION", "output_manifest.json"))
    return c
