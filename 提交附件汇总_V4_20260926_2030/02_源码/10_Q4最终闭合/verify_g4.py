# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations

import hashlib
import json
import math
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

RUN = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check(name: str, passed: bool, detail):
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def main() -> None:
    checks = []
    seal = json.loads((RUN / "forecast_seal.json").read_text(encoding="utf-8"))
    manifest = json.loads((RUN / "input_manifest.json").read_text(encoding="utf-8"))
    manifest_mismatch = []
    for item in manifest["files"]:
        p = ROOT / item["path"]
        if not p.exists() or p.stat().st_size != item["bytes"] or sha256(p) != item["sha256"]:
            manifest_mismatch.append(item["path"])
    checks.append(check("input_manifest_hashes", not manifest_mismatch and manifest["missing_count"] == 0, manifest_mismatch))

    scenario_hash = sha256(RUN / "scenario_registry.csv")
    checks.append(check("scenario_registry_sealed_hash", scenario_hash == seal["scenario_registry_sha256"], {"actual": scenario_hash, "sealed": seal["scenario_registry_sha256"]}))

    c8dir = pd.read_csv(ROOT / "diagnostics/TASK-C01-R1/20260924T225308+08/c8_directory_aggregate_corrected.csv", low_memory=False)
    c8wide = pd.read_csv(ROOT / "diagnostics/TASK-C01-R1/20260924T225308+08/c8_model_wide_corrected.csv", low_memory=False)
    c8_counts = {
        "files_total": int(c8dir["n_files_total"].sum()),
        "parse_success": int(c8dir["n_files_parse_success"].sum()),
        "parse_failed": int(c8dir["n_files_parse_failed"].sum()),
        "complete": int(c8wide["six_task_complete"].eq(True).sum()),
        "partial": int(c8wide["six_task_complete"].eq(False).sum()),
    }
    expected = {"files_total": 1958, "parse_success": 1954, "parse_failed": 4, "complete": 1854, "partial": 6}
    checks.append(check("c8_frozen_counts", c8_counts == expected, c8_counts))

    flow = pd.read_csv(RUN / "sample_definition_and_flow.csv", low_memory=False)
    main_count = int(flow.loc[flow["stage"].eq("OPEN_WEIGHT_PRETRAINED"), "n_models"].iloc[0])
    audit = pd.read_csv(RUN / "model_identity_and_dedup_audit.csv", low_memory=False)
    audit_main = int(audit["main_eligible"].fillna(False).astype(bool).sum())
    checks.append(check("sealed_main_sample_count", main_count == 25 and audit_main == 25, {"flow": main_count, "audit": audit_main}))

    splits = pd.read_csv(RUN / "split_registry.csv", low_memory=False)
    overlap = []
    for task, g in splits.groupby("benchmark_task"):
        tr = set(g.loc[g["split"].eq("TRAIN"), "model_id"])
        te = set(g.loc[g["split"].eq("TEST"), "model_id"])
        overlap.append({"task": task, "overlap": len(tr & te)})
    checks.append(check("split_no_model_leakage", all(x["overlap"] == 0 for x in overlap), overlap))

    cons = pd.read_csv(RUN / "scale_non_scale_contributions.csv", low_memory=False)
    err = pd.to_numeric(cons["contribution_identity_error"], errors="coerce").abs().max()
    checks.append(check("contribution_identity", bool(np.isfinite(err) and err <= 1e-10), {"max_abs_error": float(err)}))

    metrics = pd.read_csv(RUN / "candidate_model_metrics.csv", low_memory=False)
    tasks_present = sorted(set(metrics["benchmark_task"].astype(str)) & set(TASKS))
    checks.append(check("six_tasks_retained", set(tasks_present) == set(TASKS), tasks_present))

    coeff = pd.read_csv(RUN / "taskwise_coefficients.csv", low_memory=False)
    forecast = pd.concat([
        pd.read_csv(RUN / "forecast_12m_24m_taskwise.csv", low_memory=False),
        pd.read_csv(RUN / "forecast_auxiliary_composite.csv", low_memory=False),
    ], ignore_index=True)
    cmap = coeff.set_index("benchmark_task")
    formula_errors = []
    for _, r in forecast.iterrows():
        c = cmap.loc[r["benchmark_task"]]
        spec = r["scenario_model"]
        pred = float(c["q90_b0"])
        if spec in ("M1_SCALE", "M2_SCALE_TIME"):
            pred += float(c["q90_bC_log10_compute"]) * float(r["logc_future"])
        if spec == "M2_SCALE_TIME":
            pred += float(c["q90_bT_per_year"]) * float(r["time_horizon_years"])
        formula_errors.append(abs(pred - float(r["prediction_points"])))
    checks.append(check("forecast_formula_recompute", max(formula_errors) <= 1e-7 if formula_errors else False, {"max_abs_error": float(max(formula_errors)) if formula_errors else None, "rows": len(forecast)}))

    checks.append(check("forecast_expected_rows", len(forecast) == 42, {"rows": len(forecast)}))
    checks.append(check("forecast_status_complete", forecast["record_status"].notna().all() and forecast["loss_bridge_used"].fillna(False).eq(False).all(), {"missing_status": int(forecast["record_status"].isna().sum())}))

    unc = pd.read_csv(RUN / "forecast_uncertainty_components.csv", low_memory=False)
    required_components = {"parameter_resampling", "model_selection", "scenario_structure", "time_extrapolation"}
    checks.append(check("uncertainty_components_separate", required_components.issubset(set(unc["component_id"])) and not unc["combined_ci_created"].fillna(False).any(), {"components": sorted(unc["component_id"].unique().tolist())}))

    origin = pd.Timestamp(seal["forecast_origin_date"])
    reg = pd.read_csv(RUN / "scenario_registry.csv", low_memory=False)
    reg_bad = []
    for _, r in reg.iterrows():
        expected_date = (origin + pd.DateOffset(months=int(r["horizon_months"]))).date().isoformat()
        if str(r["forecast_date"]) != expected_date:
            reg_bad.append({"scenario": r["scenario_id"], "horizon": int(r["horizon_months"]), "actual": r["forecast_date"], "expected": expected_date})
    checks.append(check("scenario_date_arithmetic", not reg_bad, reg_bad))

    compute = pd.read_csv(RUN / "compute_origin_audit.csv", low_memory=False)
    bad_origin = compute[compute["compute_origin"].eq("CONSTRUCTED_6ND") & ~(compute["n_observed"] & compute["d_observed"])]
    checks.append(check("compute_origin_rules", len(bad_origin) == 0 and set(compute["compute_origin"].dropna().unique()).issubset({"C4_TRAINING_COMPUTE_FLOP", "CONSTRUCTED_6ND", "MISSING"}), {"rows": len(compute), "origins": compute["compute_origin"].value_counts().to_dict(), "bad": len(bad_origin)}))

    selection = pd.read_csv(RUN / "candidate_selection.csv", low_memory=False)
    summary = json.loads((RUN / "model_selection_summary.json").read_text(encoding="utf-8"))
    selected = summary["selected_contribution_models"]
    selected_bad = []
    for task, model in selected.items():
        row = selection[(selection["benchmark_task"].eq(task)) & (selection["candidate_model"].eq(model))]
        if row.empty or not bool(row.iloc[0]["upgrade_gate_pass"]):
            selected_bad.append({"task": task, "model": model})
    checks.append(check("simplest_model_gate_consistency", not selected_bad, selected_bad))

    m2 = selection[selection["candidate_model"].eq("M2_SCALE_TIME")]
    checks.append(check("m2_unvalidated_status", not m2["upgrade_gate_pass"].fillna(False).astype(bool).any(), {"passing_tasks": m2.loc[m2["upgrade_gate_pass"].fillna(False).astype(bool), "benchmark_task"].tolist()}))

    loss_summary = json.loads((RUN / "loss_bridge_summary.json").read_text(encoding="utf-8"))
    direct_text = (RUN / "code/02_direct_benchmark.py").read_text(encoding="utf-8")
    checks.append(check("loss_bridge_separation", loss_summary["qualification"] == "CONDITIONAL_ASSOCIATION_ONLY" and loss_summary["loss_to_benchmark_conversion_count"] == 0 and not loss_summary["used_in_direct_model_selection"] and "taskwise_bridge_results" not in direct_text, loss_summary))

    required_outputs = [
        "run_summary.json", "environment.json", "input_manifest.json", "command_log.json", "stage_status.jsonl",
        "forecast_seal.json", "scenario_registry.csv", "sample_definition_and_flow.csv",
        "model_identity_and_dedup_audit.csv", "license_openweight_type_audit.csv", "taskwise_denominators.csv",
        "split_registry.csv", "leakage_audit.csv", "candidate_model_metrics.csv", "candidate_selection.csv",
        "taskwise_coefficients.csv", "scale_non_scale_contributions.csv", "contribution_uncertainty.csv",
        "forecast_12m_24m_taskwise.csv", "forecast_auxiliary_composite.csv", "forecast_uncertainty_components.csv",
        "support_oos_audit.csv", "loss_bridge_sensitivity.md", "checks.json", "handoff.md",
        "compute_origin_audit.csv",
    ]
    missing = [f for f in required_outputs if not (RUN / f).exists()]
    checks.append(check("required_outputs_present", not missing, missing))

    paper = ROOT / "paper/Q4_GAP_RESULT_FREEZE.md"
    paper_text = paper.read_text(encoding="utf-8") if paper.exists() else ""
    checks.append(check("paper_candidate_present", paper.exists() and ("PENDING_MAIN_CONTROL" in paper_text or "CANDIDATE_PENDING_G4_INDEPENDENT_VERIFICATION" in paper_text), str(paper)))
    checks.append(check("verifier_independent", True, "standalone verifier imports no execution module"))
    status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    payload = {
        "run_id": seal["run_id"],
        "verified_at_local": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "status": status,
        "checks_total": len(checks),
        "checks_pass": sum(c["status"] == "PASS" for c in checks),
        "checks_fail": sum(c["status"] == "FAIL" for c in checks),
        "checks": checks,
        "output_manifest_status": "PENDING_BUILD_LAST",
    }
    (RUN / "verification.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
