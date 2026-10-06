from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]
TARGETS = ["IFEval_pct", "BBH_pct", "MATH Lvl 5_pct", "GPQA_pct", "MUSR_pct", "MMLU-PRO_pct"]
AUX = "benchmark_mean_aux"
ALL_TARGETS = TARGETS + [AUX]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(path: Path, base: Path):
    m = read_json(path)
    bad = []
    for e in m.get("files", []):
        p = base / e["path"]
        if not p.exists() or p.stat().st_size != int(e["bytes"]) or sha256(p) != e["sha256"]:
            bad.append(e["path"])
    return {"entries": len(m.get("files", [])), "mismatch": bad, "status": "PASS" if not bad else "FAIL"}


def add(checks, check_id, actual, expected, evidence, note=""):
    ok = actual == expected
    checks.append({"check_id": check_id, "actual": actual, "expected": expected, "status": "PASS" if ok else "FAIL", "evidence": evidence, "note": note})
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    ws = args.workspace.resolve()
    run = ws / "diagnostics/TASK-T08" / args.run_id
    t05d = ws / "diagnostics/TASK-T05/20260925T113355+0800"
    t07d = ws / "diagnostics/TASK-T07/20260925T113744+08"
    t06d = ws / "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08"
    c01d = ws / "diagnostics/TASK-C01/20260924T175553+08"
    c01r1 = ws / "diagnostics/TASK-C01-R1/20260924T225308+08"
    checks = []
    manifests = {"T05": verify_manifest(t05d/"output_manifest.json", t05d),
                 "T07": verify_manifest(t07d/"output_manifest.json", t07d),
                 "T06": verify_manifest(t06d/"output_manifest.json", t06d),
                 "C01": verify_manifest(c01d/"output_manifest.json", c01d),
                 "C01R1": verify_manifest(c01r1/"output_manifest.json", c01r1)}
    add(checks, "frozen_manifests", {k: v["status"] for k, v in manifests.items()}, {k: "PASS" for k in manifests}, "input frozen output manifests")
    contract = read_json(t05d/"t08_bridge_contract.json")
    bridge = pd.read_parquet(t05d/"bridge_analysis_dataset.parquet")
    wide = pd.read_csv(c01r1/"c8_model_wide_corrected.csv")
    corrupt = pd.read_csv(c01d/"c8_corrupt_files.csv")
    main_bridge = bridge[bridge["main_bridge_eligible"].astype(bool)]
    cond_bridge = bridge[~bridge["main_bridge_eligible"].astype(bool)]
    add(checks, "bridge_counts", [int(len(main_bridge)), int(len(cond_bridge)), int(len(bridge))], [7, 38, 45], "T05 bridge_analysis_dataset.parquet")
    add(checks, "c8_counts", [int(wide["six_task_complete"].sum()), int((~wide["six_task_complete"].astype(bool)).sum()), int(len(corrupt))], [1854, 6, 4], "C01/C01-R1 corrected tables")
    frozen = {k: v["candidate_id"] for k, v in contract["benchmark_prediction"]["per_task_structures"].items()}
    add(checks, "constant_frozen_candidates", frozen, {t: "CONSTANT" for t in ALL_TARGETS}, "T05 t08_bridge_contract.json")
    add(checks, "time_trend_unvalidated", contract["time_trend"]["validated_for_extrapolation"], False, "T05 t08_bridge_contract.json")

    decomp = pd.read_csv(run/"scale_non_scale_decomposition.csv")
    scale_max = float(np.abs(decomp["scale_associated_component"]).max())
    identity_max = float(np.abs(decomp["observed"] - decomp["predicted"] - decomp["conditional_remainder"]).max())
    add(checks, "scale_associated_component_zero", scale_max, 0.0, "scale_non_scale_decomposition.csv")
    add(checks, "observed_identity", bool(identity_max <= 1e-10), True, "scale_non_scale_decomposition.csv", f"max_abs={identity_max}")
    add(checks, "main_decomposition_rows", int(len(decomp)), 49, "scale_non_scale_decomposition.csv")
    add(checks, "medium_D_not_imputed", int(cond_bridge["D_tokens_B"].isna().sum()), 38, "T05 bridge_analysis_dataset.parquet")

    taskwise = pd.read_csv(run/"taskwise_progress.csv")
    add(checks, "six_task_vector_plus_mean", sorted(taskwise["benchmark_task"].tolist()), sorted(ALL_TARGETS), "taskwise_progress.csv")
    forecast = pd.read_csv(run/"forecast_12m_24m_scenarios.csv")
    loss = pd.read_csv(run/"loss_space_scale_scenarios.csv")
    add(checks, "benchmark_future_eligibility", sorted(forecast["forecast_eligibility"].dropna().unique().tolist()), ["CONDITIONAL_BASELINE_ONLY"], "forecast_12m_24m_scenarios.csv")
    add(checks, "benchmark_progress_not_identifiable", sorted(forecast["progress_status"].dropna().unique().tolist()), ["NOT_IDENTIFIABLE_PROGRESS"], "forecast_12m_24m_scenarios.csv")
    add(checks, "no_benchmark_increment_numbers", int(forecast["benchmark_increment_points"].notna().sum()), 0, "forecast_12m_24m_scenarios.csv")

    records = bridge[bridge["params_B"].notna() & bridge["D_tokens_B"].notna()].copy()
    family_intervals = []
    for family, group in records.groupby("model_family"):
        group = group.sort_values(["submission_date", "params_B", "Model"], na_position="last").reset_index(drop=True)
        for i in range(len(group)-1):
            a, b = group.iloc[i], group.iloc[i+1]
            if pd.isna(a["submission_date"]) or pd.isna(b["submission_date"]) or a["date_ambiguous"] or b["date_ambiguous"]:
                continue
            days = (pd.Timestamp(b["submission_date"]) - pd.Timestamp(a["submission_date"])).days
            if 90 <= days <= 730:
                c1 = 6.0*float(a["params_B"])*1e9*float(a["D_tokens_B"])*1e9
                c2 = 6.0*float(b["params_B"])*1e9*float(b["D_tokens_B"])*1e9
                mid = pd.Timestamp(a["submission_date"]) + (pd.Timestamp(b["submission_date"])-pd.Timestamp(a["submission_date"]))/2
                family_intervals.append((family, f"{mid.year}Q{((mid.month-1)//3)+1}", math.log(c2/c1)/(days/365.25)))
    fi = pd.DataFrame(family_intervals, columns=["family", "period", "rate"])
    fam_period = fi.groupby(["family", "period"])["rate"].median().reset_index() if len(fi) else fi
    n_families = int(fam_period["family"].nunique()) if len(fam_period) else 0
    n_intervals = int(len(fam_period))
    add(checks, "growth_support_recount", [n_families, n_intervals], [1, 1], "T05 bridge dataset; recomputed independently", "expected current frozen data")
    add(checks, "growth_gate_not_identifiable", bool(n_families >= 3 and n_intervals >= 10), False, "T05 bridge dataset")
    add(checks, "no_fake_loss_growth", int(loss["growth_rate_annual_log"].notna().sum()), 0, "loss_space_scale_scenarios.csv")
    add(checks, "loss_space_not_identifiable", sorted(loss["loss_space_scale_scenario"].dropna().unique().tolist()), ["NOT_IDENTIFIABLE"], "loss_space_scale_scenarios.csv")
    add(checks, "loss_to_benchmark_conversion_zero", int(forecast["loss_to_benchmark_conversion_count"].sum() + loss["loss_to_benchmark_conversion_count"].sum()), 0, "forecast and loss output tables")

    draw = pd.read_parquet(t07d/"parameter_draw_optima.parquet")
    s00 = draw[(draw["scenario_id"].eq("S00_NULL_M0_B1")) & (draw["H"].eq(2048))]
    add(checks, "b1_whole_draw_rows", int(s00["b1_replicate"].nunique()), 80, "T07 parameter_draw_optima.parquet")
    add(checks, "b1_draw_complete_columns", bool(s00[["E","A","B","alpha","beta","N_B","D_B","predicted_loss"]].notna().all().all()), True, "T07 parameter_draw_optima.parquet")
    bounds = pd.read_csv(t07d/"support_bounds.csv").set_index("quantity")
    in_support = bool(s00["N_B"].between(bounds.loc["N_B","lower"], bounds.loc["N_B","upper"]).all() and s00["D_B"].between(bounds.loc["D_B","lower"], bounds.loc["D_B","upper"]).all())
    add(checks, "t07_draws_in_support", in_support, True, "T07 support_bounds.csv")
    implied = 6.0*s00["N_B"]*1e9*s00["D_B"]*1e9
    rel = (implied-s00["compute_cost"]).abs()/s00["compute_cost"].abs()
    add(checks, "physical_compute_units", bool(rel.max() <= 1e-10), True, "T07 parameter_draw_optima.parquet", f"max_relative_error={rel.max()}")

    usage = pd.read_csv(run/"model_identity_usage.csv")
    add(checks, "damaged_json_no_score", int(usage[usage["c8_category"].eq("DAMAGED_JSON")]["score_rows_used"].sum()), 0, "model_identity_usage.csv")
    add(checks, "partial_mean_excluded", bool(usage[~usage["c8_category"].eq("COMPLETE_SIX_TASK")]["mean_aux_used_as_task_vector"].sum() == 0), True, "model_identity_usage.csv")
    leakage = pd.read_csv(run/"leakage_audit.csv")
    add(checks, "same_model_run_leakage", int(leakage[leakage["check_id"].eq("same_run_group_cross_model_leakage")]["actual"].iloc[0]), 0, "leakage_audit.csv")
    add(checks, "same_model_split_leakage", int(leakage[leakage["check_id"].eq("same_model_duplicate_split_assignment")]["actual"].iloc[0]), 0, "leakage_audit.csv")

    seal = read_json(run/"forecast_seal.json")
    seal_dt = pd.Timestamp(seal["sealed_at_utc"])
    generated = pd.Timestamp(forecast["generated_at_utc"].iloc[0])
    add(checks, "forecast_seal_before_results", bool(seal_dt <= generated), True, "forecast_seal.json vs forecast_12m_24m_scenarios.csv")
    add(checks, "scenario_ids_unchanged", set(seal["scenario_ids"]), set(pd.read_csv(run/"scenario_registry.csv")["scenario_id"]), "forecast_seal.json vs scenario_registry.csv")
    add(checks, "scenario_horizons_frozen", sorted(forecast["horizon_months"].unique().tolist()), [12, 24], "forecast_12m_24m_scenarios.csv")
    add(checks, "forecast_origin", seal["forecast_origin_date"], "2025-03-13", "forecast_seal.json")

    uncertainty = pd.read_csv(run/"forecast_uncertainty.csv")
    comps = sorted(uncertainty["component_id"].unique().tolist())
    add(checks, "six_uncertainty_components", comps, sorted(["scaling_parameter","bridge_model_error","benchmark_conditional_association","model_family_heterogeneity","time_extrapolation","scenario_structure"]), "forecast_uncertainty.csv")
    add(checks, "no_combined_ci", bool(uncertainty["combined_ci_created"].eq(False).all()), True, "forecast_uncertainty.csv")
    checks_df = pd.DataFrame(checks)
    payload = {"task_id": "TASK-T08", "run_id": args.run_id, "verifier": "code/verify_t08.py",
        "verifier_is_independent": True, "imports_execution_module": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "environment": {"python": sys.version, "platform": platform.platform(), "pandas": pd.__version__, "numpy": np.__version__},
        "checks": checks, "n_checks": len(checks), "n_pass": int((checks_df["status"]=="PASS").sum()), "n_fail": int((checks_df["status"]=="FAIL").sum()),
        "manifest_status": "PENDING_FINAL_MANIFEST", "manifest_last_rule": "run build_manifest.py only after verification.json and handoff.md are frozen; post-manifest read-only verification must pass"}
    (run/"verification.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"n_checks": len(checks), "n_pass": payload["n_pass"], "n_fail": payload["n_fail"]}, ensure_ascii=False))
    return 1 if payload["n_fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())



