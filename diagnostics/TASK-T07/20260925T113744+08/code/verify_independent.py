from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

ROOT = Path.cwd()
RUN = ROOT / "diagnostics/TASK-T07/20260925T113744+08"
INTEG = ROOT / "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08"
B = ROOT / "diagnostics/TASK-T06E-B/20260925T100306+08"
P = ROOT / "diagnostics/TASK-T06E-P/20260925T075729+08"
ETA = 2e-4
HCRIT = 6.0 / ETA
BUDGETS = [1e18, 1e20, 1e22]
HS = [2048, 4096, 8192, 32768, 131072]
NLO, NHI = 0.070542, 11.965825
DLO, DHI = 0.134, 299.893
QLO, QHI = 0.04888888888888889, 0.9805414146077935
QBL, QBU = 0.1, 0.6
Q0 = 0.5695341857475174


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def g(q: float, name: str) -> float:
    if name == "G_EXP":
        return 1e7 * math.exp(6.0 * q)
    if name == "G_POWER":
        return 5e9 * q ** 4
    if name == "G_LOG":
        return 2e9 * math.log1p(10.0 * q)
    return float("nan")


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


contract = json.loads((INTEG / "t07_model_contract.json").read_text(encoding="utf-8"))
table = pd.read_csv(INTEG / "t07_parameter_table.csv")
registry = pd.read_csv(INTEG / "scenario_registry_filled.csv")
preds = pd.read_parquet(INTEG / "scenario_predictions.parquet")
draws = pd.read_parquet(B / "bootstrap/parameter_draws.parquet")
a4raw = pd.read_csv(ROOT / "F题/real_attachments/A_data_value/regmix_tables/train_mixture_1m.csv")
model = json.loads((ROOT / "solution/outputs/mixture/model.json").read_text(encoding="utf-8"))
features = list(contract["mixture"]["feature_order"])
a4 = a4raw[features].to_numpy(float)
a4 = a4 / a4.sum(axis=1, keepdims=True)
p0 = np.asarray(contract["mixture"]["p0"], dtype=float)
coeff = np.asarray(model["models"]["linear"]["coefficients"], dtype=float)
h3 = pd.read_csv(P / "bridge/H3_mapping_steps.csv")
results = pd.read_parquet(RUN / "optimization_results.parquet")
paper = pd.read_csv(RUN / "budget_scenario_optima.csv")
kkt = pd.read_csv(RUN / "kkt_boundary_checks.csv")
drawopt = pd.read_parquet(RUN / "parameter_draw_optima.parquet")
unc = pd.read_csv(RUN / "uncertainty_summary.csv")
structural = pd.read_csv(RUN / "structural_transition_diagnostics.csv")
quality = pd.read_csv(RUN / "quality_cost_sensitivity.csv")
context = pd.read_csv(RUN / "context_sensitivity.csv")
transport = pd.read_csv(RUN / "transport_failure_sensitivity.csv")
support = pd.read_csv(RUN / "support_oos_audit.csv")
feas = pd.read_csv(RUN / "feasibility_audit.csv")
checks: list[dict] = []


def add(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"check": name, "status": "PASS" if bool(ok) else "FAIL", "detail": str(detail)})


def params_from(module: str) -> dict:
    d = table[table["module"].eq(module)]
    return {str(r["parameter"]): float(r["value"]) for _, r in d.iterrows() if pd.notna(r["value"])}


def mapping_ok(row: pd.Series, qa: float, qb: float) -> tuple[bool, str]:
    bridge = str(row["bridge"])
    if not (QLO <= qa <= QHI):
        return False, "Q_A_OOS"
    if bridge == "H1":
        exp = qa
    elif bridge == "H2":
        exp = 0.6 + float(row["h_parameter_b"]) * (qa - Q0)
    elif bridge == "H3":
        d = h3[h3["source_kind"].eq("Q_baseline_calibration")].copy()
        pos = int(np.searchsorted(d["q"].to_numpy(float), qa, side="right") - 1)
        pos = max(0, min(pos, len(d) - 1))
        exp = float(d.iloc[pos]["mapped_Q_B"])
        if not bool(d.iloc[pos]["usable_for_numeric_prediction"]):
            return False, "H3_NOT_USABLE"
    else:
        return False, f"UNEXPECTED_BRIDGE_{bridge}"
    if abs(exp - qb) > 1e-10:
        return False, f"MAPPING_VALUE_MISMATCH:{exp}:{qb}"
    return (QBL - 1e-12 <= qb <= QBU + 1e-12), f"qB={qb}"


def cost_of(n: float, d: float, q: float | None, h: int, cf: str) -> tuple[float, float, float]:
    comp = 6e18 * n * d
    attn = ETA * 1e18 * n * d * h
    qual = 0.0
    if q is not None:
        diff = g(q, cf) - g(Q0, cf)
        tol = 1e-12 * max(1.0, abs(g(Q0, cf)))
        qual = 1e9 * d * max(diff if diff > tol else 0.0, 0.0)
    return comp, qual, attn


def loss_of(row: pd.Series, n: float, d: float, qa: float | None, qb: float, prow: pd.Series) -> float:
    pr = params_from("M0_B1")
    base = pr["E"] + pr["A"] * n ** (-pr["alpha"]) + pr["B"] * d ** (-pr["beta"])
    if str(row["family"]) == "mixture_transport_univariate":
        p = prow[[f"p_{i}" for i in range(17)]].to_numpy(float)
        return base + float(row["tau_p_fixed_scenario"]) * float(coeff.mean(axis=0) @ (p - p0))
    if bool(row["quality_effect_enabled"]):
        rho = float(row["rho_Q_fixed_scenario"])
        rb = float(row["r_B1_fixed_scenario"])
        if str(row["quality_transport"]) == "additive":
            k = float(table[(table["module"].eq("MQ_add_B6")) & (table["parameter"].eq("k_add"))]["value"].iloc[0])
            return base - rho * rb * k * (qb - 0.6)
        eta = float(table[(table["module"].eq("MQ_eff_B6")) & (table["parameter"].eq("eta"))]["value"].iloc[0])
        if str(row["quality_transport"]) == "effective_data_keep_k":
            beta6 = float(table[(table["module"].eq("MQ_eff_B6")) & (table["parameter"].eq("beta"))]["value"].iloc[0])
            eta = eta / beta6 * pr["beta"]
        m = math.exp(rho * rb * eta * (qb - 0.6))
        return pr["E"] + pr["A"] * n ** (-pr["alpha"]) + pr["B"] * (d * m) ** (-pr["beta"])
    return base


def independent_s00(budget: float, h: int, pr: dict) -> tuple[float, float]:
    a = 1e18 * (6.0 + ETA * h)
    lo = max(NLO, budget / (a * DHI))
    hi = min(NHI, budget / (a * DLO))
    def deriv(s: float) -> float:
        n = math.exp(s)
        d = budget / (a * n)
        return -pr["alpha"] * pr["A"] * n ** (-pr["alpha"]) + pr["beta"] * a * pr["B"] * n * d ** (1 - pr["beta"]) / budget
    def obj(s: float) -> float:
        n = math.exp(s); d = budget / (a * n)
        return pr["E"] + pr["A"] * n ** (-pr["alpha"]) + pr["B"] * d ** (-pr["beta"])
    slo, shi = math.log(lo), math.log(hi)
    cands = [slo, shi]
    dlo = deriv(slo); dhi = deriv(shi)
    if dlo < 0 < dhi:
        cands.append(float(brentq(deriv, slo, shi, xtol=1e-14, rtol=1e-15, maxiter=200)))
    s = min(cands, key=obj)
    n = math.exp(s)
    return n, budget / (a * n)

# Input and registry checks
add("frozen_contract_primary_model", contract["primary_model"]["name"] == "M0_B1" and contract["T07_rules"]["primary_model"] == "M0_B1")
add("parameter_table_primary_present", set(["E", "A", "B", "alpha", "beta"]).issubset(set(table[table["module"].eq("M0_B1")]["parameter"])))
add("scenario_registry_exact_21", len(registry) == 21 and registry["scenario_id"].tolist() == contract["scenario_registry"]["ids"])
add("scenario_predictions_exact_21", preds["scenario_id"].tolist() == contract["scenario_registry"]["ids"])
add("H_values_exact", sorted(pd.read_csv(RUN / "config/budgets.csv")["budget_flops"].tolist()) == sorted(BUDGETS))
add("H_values_and_Hcrit", sorted(pd.read_csv(RUN / "context_sensitivity.csv")["H"].unique().tolist()) == sorted(HS) and abs(HCRIT - 30000.0) <= 1e-12, f"Hcrit={HCRIT}")
problem = (ROOT / "recovery/2026-09-24/problem_text_from_docx.txt").read_text(encoding="utf-8", errors="replace")
add("original_cost_formula_present", all(x in problem for x in ["6ND", "ηNDLctx", "Lctxcrit=6/η", "5×109", "2×109"]))
input_manifest = json.loads((RUN / "input_manifest.json").read_text(encoding="utf-8"))
in_hash_bad = []
for item in input_manifest["inputs"]:
    path = ROOT / item["path"]
    if not path.exists() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
        in_hash_bad.append(item["path"])
add("input_manifest_hashes_current", len(in_hash_bad) == 0, str(in_hash_bad))

# Required outputs
required = ["run_summary.json", "environment.json", "input_manifest.json", "command_log.json", "stage_status.jsonl", "config/budgets.csv", "config/optimization_matrix.csv", "config/cost_functions.json", "feasibility_audit.csv", "unit_conversion_audit.csv", "optimization_results.parquet", "budget_scenario_optima.csv", "solver_multistart.csv", "kkt_boundary_checks.csv", "marginal_returns.csv", "structural_transition_diagnostics.csv", "support_oos_audit.csv", "parameter_draw_optima.parquet", "uncertainty_summary.csv", "quality_cost_sensitivity.csv", "context_sensitivity.csv", "transport_failure_sensitivity.csv", "t08_or_paper_interface.json", "handoff.md", "checks.json"]
missing = [x for x in required if not (RUN / x).exists()]
add("required_outputs_present", len(missing) == 0, str(missing))

# Scenario and forbidden-status checks
ids_out = set(results["scenario_id"])
add("all_21_scenarios_executed_or_statused", ids_out == set(registry["scenario_id"]), f"{len(ids_out)}")
s17 = results[results["scenario_id"].eq("S17_B8_REVERSE_COMMON_SUPPORT")]
add("S17_no_numeric_optimum", len(s17) == 3 and s17["status"].eq("NO_NUMERIC_OPTIMUM").all() and s17[["N_B", "D_B", "Q_A", "predicted_loss"]].isna().all().all())
s07 = results[results["scenario_id"].eq("S07_H4_DIRECTION_ONLY")]
add("S07_no_numeric_optimum", len(s07) == 3 and s07["status"].eq("NO_NUMERIC_OPTIMUM").all() and s07[["N_B", "D_B", "Q_A", "predicted_loss"]].isna().all().all())
scan_bad = []
for f in RUN.rglob("*"):
    if f.is_file() and f.suffix.lower() in {".json", ".csv", ".md", ".txt"} and f.name != "output_manifest.json":
        txt = f.read_text(encoding="utf-8", errors="ignore")
        if "k=-20" in txt:
            scan_bad.append(str(f.relative_to(RUN)))
add("legacy_numeric_marker_absent", len(scan_bad) == 0, str(scan_bad))
add("quality_and_mixture_scenario_only", results.loc[results["scenario_id"].str.startswith(("S0", "S1", "X")), "uncertainty_label"].astype(str).str.contains("SCENARIO_ONLY|DRAW|STRUCTURAL").all())

# Independent recomputation of every numeric row
reg_lookup = registry.set_index("scenario_id")
bad_budget = []
bad_cost = []
bad_loss = []
bad_support = []
bad_simplex = []
for _, r in results.iterrows():
    if r["status"] != "OPTIMAL":
        continue
    reg = reg_lookup.loc[r["scenario_id"]]
    cf = str(r["cost_function"])
    if cf == "NOT_APPLICABLE":
        cf = "G_EXP"
    n = float(r["N_B"]); d = float(r["D_B"])
    qa = None if pd.isna(r["Q_A"]) else float(r["Q_A"])
    qb = float(r["Q_B"]) if pd.notna(r["Q_B"]) else float("nan")
    comp, qual, attn = cost_of(n, d, qa, int(r["H"]), cf)
    total = comp + qual + attn
    if total > float(r["budget_flops"]) * (1 + 1e-9):
        bad_budget.append((r["scenario_id"], r["budget_flops"], r["H"], total))
    if abs(comp - float(r["compute_cost"])) > max(1e-3, 1e-12 * abs(comp)) or abs(qual - float(r["quality_cost"])) > max(1e-3, 1e-12 * max(1.0, abs(qual))) or abs(attn - float(r["attention_cost"])) > max(1e-3, 1e-12 * abs(attn)):
        bad_cost.append((r["scenario_id"], r["budget_flops"], r["H"], comp, qual, attn))
    if bool(reg["quality_effect_enabled"]):
        okmap, msg = mapping_ok(reg, qa, qb)
        if not okmap:
            bad_support.append((r["scenario_id"], "Q", msg))
    loss = loss_of(reg, n, d, qa, qb, r)
    if abs(loss - float(r["predicted_loss"])) > 1e-9:
        bad_loss.append((r["scenario_id"], r["budget_flops"], r["H"], loss, float(r["predicted_loss"])))
    if not (NLO - 1e-12 <= n <= NHI + 1e-12 and DLO - 1e-12 <= d <= DHI + 1e-12):
        bad_support.append((r["scenario_id"], "ND", (n, d)))
    p = r[[f"p_{i}" for i in range(17)]].to_numpy(float)
    if p.min() < -1e-14 or abs(p.sum() - 1.0) > 1e-10:
        bad_simplex.append((r["scenario_id"], r["budget_flops"], r["H"], p.min(), p.sum()))
add("budget_feasibility_independent", len(bad_budget) == 0, str(bad_budget[:3]))
add("three_cost_terms_independent", len(bad_cost) == 0, str(bad_cost[:3]))
add("predicted_loss_independent", len(bad_loss) == 0, str(bad_loss[:3]))
add("support_independent", len(bad_support) == 0, str(bad_support[:3]))
add("p_simplex_independent", len(bad_simplex) == 0, str(bad_simplex[:3]))

# S00 analytical first-order checks for all budgets and H values.
s00 = results[results["scenario_id"].eq("S00_NULL_M0_B1") & results["status"].eq("OPTIMAL")].copy()
pr = params_from("M0_B1")
s00_err = []
for _, r in s00.iterrows():
    n, d = independent_s00(float(r["budget_flops"]), int(r["H"]), pr)
    s00_err.append(max(abs(n - float(r["N_B"])) / n, abs(d - float(r["D_B"])) / d))
add("S00_analytic_first_order", len(s00) == 15 and max(s00_err) < 1e-6, f"n={len(s00)},max_rel={max(s00_err) if s00_err else None}")

# KKT and multistart checks.
add("KKT_residuals_small", float(kkt["kkt_residual"].max()) < 1e-4 and float(kkt["equality_residual"].abs().max()) < 1e-8, f"max={kkt['kkt_residual'].max()}")
add("KKT_at_least_three_budgets", set(kkt["budget_flops"]).issuperset(set(BUDGETS)), str(sorted(set(kkt["budget_flops"]))))
add("multistart_rows_present", len(pd.read_csv(RUN / "solver_multistart.csv")) >= 20, str(len(pd.read_csv(RUN / "solver_multistart.csv"))))

# Cost function formula checks.
probe = 0.73
gvals = {name: g(probe, name) for name in ["G_EXP", "G_POWER", "G_LOG"]}
add("three_g_functions_exercised", len(quality["cost_function"].unique()) >= 3 and set(gvals) == {"G_EXP", "G_POWER", "G_LOG"}, str(gvals))
add("H_crossing_marked", set(context["H_regime"].unique()).issuperset({"BELOW_H_CRIT_COMPUTE_DOMINANT", "ABOVE_H_CRIT_ATTENTION_DOMINANT"}), str(context["H_regime"].unique()))

# Whole-row draw checks: every numerical draw must exactly equal one saved source row.
b1rows = draws[(draws["source"].eq("B1")) & (draws["model"].eq("M0_B1"))].set_index("replicate")
bad_draw = []
for _, r in drawopt.iterrows():
    if int(r["b1_replicate"]) not in b1rows.index:
        bad_draw.append((r["scenario_id"], int(r["draw_id"]), "B1_REPLICATE_MISSING"))
        continue
    br = b1rows.loc[int(r["b1_replicate"])]
    for c in ["E", "A", "B", "alpha", "beta"]:
        if abs(float(r[c]) - float(br[c])) > 1e-15:
            bad_draw.append((r["scenario_id"], int(r["draw_id"]), c))
    if pd.notna(r["b6_replicate"]):
        model_name = "MQ-eff" if str(r["scenario_id"]) in {"S12_EFF_KEEP_ETA", "S13_EFF_KEEP_K", "X03_H3_EFF"} else "MQ-add"
        q = draws[(draws["source"].eq("B6")) & (draws["model"].eq(model_name)) & (draws["replicate"].eq(int(r["b6_replicate"])))]
        if len(q) != 1:
            bad_draw.append((r["scenario_id"], int(r["draw_id"]), "B6_REPLICATE_MISSING"))
        else:
            qr = q.iloc[0]
            if model_name == "MQ-add" and abs(float(r["k_add"]) - float(qr["k_add"])) > 1e-15:
                bad_draw.append((r["scenario_id"], int(r["draw_id"]), "k_add"))
            if model_name == "MQ-eff" and abs(float(r["eta_transport"]) - float(qr["eta"])) > 1e-15 and str(r["scenario_id"]) != "S13_EFF_KEEP_K":
                bad_draw.append((r["scenario_id"], int(r["draw_id"]), "eta"))
add("draws_are_saved_whole_rows", len(bad_draw) == 0, str(bad_draw[:5]))
qual_draws = drawopt[drawopt["scenario_id"].str.startswith("S01")].groupby(["budget_flops", "cost_function"])["draw_id"].nunique()
add("quality_200_conditional_draws", int(qual_draws.min()) == 200, str(qual_draws.to_dict()))
null_draws = drawopt[drawopt["scenario_id"].eq("S00_NULL_M0_B1")].groupby("budget_flops")["draw_id"].nunique()
add("null_80_row_draws", int(null_draws.min()) == 80 and int(null_draws.max()) == 80, str(null_draws.to_dict()))
add("uncertainty_failures_zero", float(unc["failure_fraction"].max()) <= 1e-12, f"max_failure={unc['failure_fraction'].max()}")
add("uncertainty_summary_has_percentiles", all(x in unc.columns for x in ["N_B_p2_5", "N_B_median", "N_B_p97_5", "Loss_p2_5", "Loss_median", "Loss_p97_5"]))

# Q/p joint-free and null-flat-direction checks.
joint_bad = []
for _, r in results[results["status"].eq("OPTIMAL")].iterrows():
    fam = str(r["family"])
    if fam in {"quality_reference", "quality_univariate", "extreme_combination"}:
        if r["p_status"] != "FIXED_P0_NOT_OPTIMIZED":
            joint_bad.append((r["scenario_id"], r["p_status"]))
    if fam == "mixture_transport_univariate":
        if r["Q_status"] not in {"NOT_IDENTIFIED_NOT_OPTIMIZED", "NOT_OPTIMIZED"}:
            joint_bad.append((r["scenario_id"], r["Q_status"]))
add("Q_p_not_jointly_free", len(joint_bad) == 0, str(joint_bad[:5]))
s00rows = results[results["scenario_id"].eq("S00_NULL_M0_B1")]
add("null_Q_p_not_arbitrarily_optimized", s00rows["Q_status"].eq("NOT_IDENTIFIED_NOT_OPTIMIZED").all() and s00rows["p_status"].eq("FIXED_P0_NOT_OPTIMIZED").all())

# Structural transitions and context sensitivity.
add("structural_diagnostics_present", len(structural) > 0 and int(structural["structural_transition"].sum()) > 0)
add("context_sensitivity_has_all_H", set(context["H"].unique()) == set(HS))
add("quality_cost_sensitivity_has_three_g", set(quality["cost_function"].unique()) == {"G_EXP", "G_POWER", "G_LOG"})
add("transport_failure_stress_present", len(transport) == 9 and transport["failure_stress"].sum() == 3)

# Manifest and interface checks.
interface = json.loads((RUN / "t08_or_paper_interface.json").read_text(encoding="utf-8"))
add("t08_interface_not_started", interface.get("handoff_to_T08", "").startswith("T08 NOT STARTED"))
checks_json = json.loads((RUN / "checks.json").read_text(encoding="utf-8"))
add("execution_checks_pass", checks_json.get("status") == "PASS")
manifest_path = RUN / "output_manifest.json"
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_bad = []
    for item in manifest.get("files", []):
        path = RUN / item["path"]
        if not path.exists() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            manifest_bad.append(item["path"])
    add("output_manifest_current", len(manifest_bad) == 0, str(manifest_bad[:5]))
else:
    add("output_manifest_current", False, "MISSING_PRELIMINARY_MANIFEST")

status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
verification = {
    "schema_version": 1,
    "task": "TASK-T07",
    "run_id": RUN.name,
    "status": status,
    "verifier_imports_execution_module": False,
    "independently_recomputed": [
        "predicted_loss",
        "three_cost_terms",
        "budget_feasibility",
        "support_status",
        "p_simplex",
        "S00_analytic_first_order",
        "three_g_functions",
        "H_critical",
        "whole_row_parameter_draws",
    ],
    "checks": checks,
}
write_json(RUN / "verification.json", verification)
print(json.dumps({"status": status, "check_count": len(checks), "failed": [c for c in checks if c["status"] != "PASS"]}, ensure_ascii=False))
