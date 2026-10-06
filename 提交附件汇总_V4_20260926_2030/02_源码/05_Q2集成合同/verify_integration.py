# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path.cwd()
RUN = ROOT / "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08"
B = ROOT / "diagnostics/TASK-T06E-B/20260925T100306+08"
BR1 = ROOT / "diagnostics/TASK-T06E-B-R1/20260925T103130+08"
P = ROOT / "diagnostics/TASK-T06E-P/20260925T075729+08"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def manifest_ok(root: Path) -> tuple[bool, int]:
    m = json.loads((root / "output_manifest.json").read_text(encoding="utf-8"))
    bad = 0
    for item in m["files"]:
        path = root / item["path"]
        if not path.exists() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            bad += 1
    return bad == 0, bad


checks: list[dict] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append({"check": name, "status": "PASS" if condition else "FAIL", "detail": detail})


for label, root in [("B", B), ("B_R1", BR1), ("P", P)]:
    ok, bad = manifest_ok(root)
    check(f"protected_{label}_manifest_current", ok, f"mismatch_count={bad}")

registry = pd.read_csv(P / "scenario_registry/scenario_registry_preregistered.csv")
filled = pd.read_csv(RUN / "scenario_registry_filled.csv")
pred = pd.read_parquet(RUN / "scenario_predictions.parquet")
contract = json.loads((RUN / "t07_model_contract.json").read_text(encoding="utf-8"))
summary = json.loads((RUN / "run_summary.json").read_text(encoding="utf-8"))
r1 = json.loads((BR1 / "corrected_gates/G1_G4_reconciliation.json").read_text(encoding="utf-8"))
parameters = pd.read_csv(RUN / "t07_parameter_table.csv")
source_params = pd.read_csv(B / "fit/scaling_parameters_by_source.csv")

expected_ids = registry.sort_values("scenario_order")["scenario_id"].tolist()
check("scenario_registry_exact_21", len(expected_ids) == 21 and filled["scenario_id"].tolist() == expected_ids and pred["scenario_id"].tolist() == expected_ids)
check("no_scenario_cartesian_expansion", len(filled) == 21 and filled["scenario_id"].is_unique)
check("R1_all_four_pass", r1["all_four_PASS"] is True and r1["scientific_result"] == "ACCEPT_B6_SOURCE_RELATION")
check("primary_contract_frozen_null", contract["primary_model"]["name"] == "M0_B1" and contract["primary_model"]["quality_enabled"] is False and contract["primary_model"]["mixture_transport_enabled"] is False)
check("bridge_not_identifiable", contract["quality"]["A_B_mapping_status"] == "NOT_IDENTIFIABLE")
check("MQ_add_source_only", contract["quality"]["MQ_add_B6"]["qualification"] == "B6_SOURCE_CONDITIONAL_ACCEPTED" and contract["quality"]["MQ_add_B6"]["cross_source_use"] == "SCENARIO_ONLY")
check("MQ_eff_boundary_sensitivity", contract["quality"]["MQ_eff"]["eta_at_lower_bound"] is True and "SENSITIVITY_ONLY" in contract["quality"]["MQ_eff"]["qualification"])
check("B8_conflict_parallel", "CONFLICT_EVIDENCE" in contract["quality"]["B8"] and "never average" in contract["uncertainty"]["B8_propagation"])
check("joint_Q_p_forbidden", contract["joint_Q_p"]["independent_optimization_allowed"] is False)
check("q_A_star_exact", abs(contract["quality"]["q_A_star"] - 0.5695341857475174) < 1e-15)
check("units_for_compute_present", contract["units"]["N_physical"] == "N_B*1e9" and contract["units"]["D_physical"] == "D_B*1e9" and contract["units"]["training_compute"].startswith("6*"))

b1_src = source_params[(source_params["source"] == "B1") & (source_params["model"] == "M0_B1") & (source_params["task_id"] == "B1_full")].iloc[0]
param_ok = True
for name in ["E", "A", "B", "alpha", "beta"]:
    val = parameters[(parameters["module"] == "M0_B1") & (parameters["parameter"] == name)]["value"]
    param_ok &= len(val) == 1 and abs(float(val.iloc[0]) - float(b1_src[name])) <= 1e-15
check("B1_parameters_byte_source_consistent", param_ok)

add_src = source_params[(source_params["source"] == "B6") & (source_params["model"] == "MQ-add") & (source_params["task_id"] == "B6_full_MQ-add")].iloc[0]
kvals = filled.loc[filled["quality_parameter_qualification"].eq("B6_SOURCE_CONDITIONAL_ACCEPTED"), "k_add_B6"]
check("MQ_add_parameter_slots_filled", len(kvals) > 0 and np.allclose(kvals.to_numpy(float), float(add_src["k_add"]), rtol=0, atol=1e-15))
check("direction_only_scenarios_non_numeric", set(pred.loc[pred["numeric_status_integrated"].eq("NO_NUMERIC_PREDICTION"), "scenario_id"]) == {"S07_H4_DIRECTION_ONLY", "S17_B8_REVERSE_COMMON_SUPPORT"})
check("no_full_loss_fabricated", pred["full_loss_at_reference"].isna().all() and pred["baseline_loss"].isna().all())
check("no_joint_Q_p_enabled", not filled["joint_Q_p_independent_optimizable"].any())
check("summary_matches_contract", summary["primary_model"] == "M0_B1" and summary["quality_enabled"] is False and summary["mixture_transport_enabled"] is False and summary["scenario_count"] == 21)

source_text = (RUN / "code/integrate.py").read_text(encoding="utf-8")
forbidden = ["least_squares(", "curve_fit(", ".fit(", "minimize("]
check("integration_contains_no_model_fit", not any(token in source_text for token in forbidden), str([x for x in forbidden if x in source_text]))

failures = [x for x in checks if x["status"] == "FAIL"]
verification = {
    "status": "PASS" if not failures else "FAIL",
    "independent_verifier": True,
    "imports_integration_executor": False,
    "checks_total": len(checks),
    "pass": len(checks) - len(failures),
    "fail": len(failures),
    "checks": checks,
}
(RUN / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
(RUN / "checks.json").write_text(
    json.dumps({"status": verification["status"], "checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8"
)
if failures:
    raise SystemExit("INTEGRATION_VERIFICATION_FAILED")
print(json.dumps({"status": "PASS", "checks": len(checks)}, ensure_ascii=False))
