from __future__ import annotations
import hashlib, json
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

RUN = Path(__file__).resolve().parents[1]
WS = RUN.parents[2]
RID = RUN.name
T03 = WS / "diagnostics/TASK-T03E/20260925T020032+08/t06_quality_interface.parquet"
B6 = WS / "F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv"
DOMAINS = ["arxiv", "book", "c4", "commoncrawl", "github", "stackexchange", "wikipedia"]
M = 8
EXPECTED_N = 40930
qout = RUN / "quality_anchor"
bout = RUN / "bridge"
qout.mkdir(exist_ok=True); bout.mkdir(exist_ok=True)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

interface = pd.read_parquet(T03, columns=["domain","evaluation_role","is_unique_first","Q_valid","Q_baseline","Q_C"])
cal = interface.loc[interface["evaluation_role"].eq("A1_calibration")].copy()
selected_mask = (cal["is_unique_first"].eq(True) & cal["Q_valid"].eq(True) & np.isfinite(cal["Q_baseline"].to_numpy(float)))
sel = cal.loc[selected_mask].copy()
observed_domains = set(cal["domain"].astype(str).unique())
if set(DOMAINS) != observed_domains:
    raise RuntimeError(f"calibration domain mismatch: expected={DOMAINS}, observed={sorted(observed_domains)}")
if len(sel) != EXPECTED_N:
    raise RuntimeError(f"selected calibration count mismatch: expected={EXPECTED_N}, observed={len(sel)}")
if not np.isfinite(sel["Q_C"].to_numpy(float)).all():
    raise RuntimeError("Q_C is not finite on q_A* calibration selection")

stats_rows = []
for d in DOMAINS:
    dc = cal.loc[cal["domain"].eq(d)]
    ds = sel.loc[sel["domain"].eq(d)]
    if len(ds) == 0:
        raise RuntimeError(f"empty selected domain: {d}")
    stats_rows.append({
        "domain": d,
        "domain_order": DOMAINS.index(d),
        "n_total": int(len(dc)),
        "n_unique_first": int(dc["is_unique_first"].eq(True).sum()),
        "n_Q_valid_after_unique": int((dc["is_unique_first"].eq(True) & dc["Q_valid"].eq(True)).sum()),
        "n_selected": int(len(ds)),
        "selected_fraction_of_n_total": float(len(ds) / len(dc)),
        "mu_d_Q_baseline": float(ds["Q_baseline"].mean()),
        "mu_d_Q_C": float(ds["Q_C"].mean()),
        "equal_weight_contribution_Q_baseline": float(ds["Q_baseline"].mean() / 7.0),
        "equal_weight_contribution_Q_C": float(ds["Q_C"].mean() / 7.0),
        "weight": 1.0 / 7.0,
        "selection_scope": "evaluation_role=A1_calibration & is_unique_first=True & Q_valid=True & finite(Q_baseline)",
    })
stats = pd.DataFrame(stats_rows)
qstar = float(stats["mu_d_Q_baseline"].mean())
qcstar = float(stats["mu_d_Q_C"].mean())
global_mean = float(sel["Q_baseline"].mean())
stats.to_csv(qout / "q_A_anchor_by_domain.csv", index=False, encoding="utf-8", float_format="%.17g")
write_json(qout / "q_A_anchor.json", {
    "run_id": RID,
    "q_A_star": qstar,
    "q_C_star_sensitivity": qcstar,
    "seven_domain_equal_weight": 1.0 / 7.0,
    "domains_in_frozen_order": DOMAINS,
    "selected_total": int(len(sel)),
    "expected_selected_total": EXPECTED_N,
    "domain_sample_weighted_global_mean_for_comparison_only": global_mean,
    "domain_weighting_used": "EQUAL_DOMAIN",
    "document_weighting_used": False,
    "Q_C_role": "SENSITIVITY_ONLY_USES_SAME_SELECTION",
    "status": "PASS",
})

# Stable per-domain ECDF on the union of Q_baseline calibration values.
all_q = sel["Q_baseline"].to_numpy(float)
q_grid = np.unique(np.sort(all_q, kind="stable"))
if not len(q_grid):
    raise RuntimeError("empty q_grid")
domain_cdf = {}
for d in DOMAINS:
    x = np.sort(sel.loc[sel["domain"].eq(d), "Q_baseline"].to_numpy(float), kind="stable")
    domain_cdf[d] = np.searchsorted(x, q_grid, side="right").astype(float) / float(len(x))
mat = np.vstack([domain_cdf[d] for d in DOMAINS])
f_a = mat.mean(axis=0)
if not np.allclose(mat[:, -1], 1.0, rtol=0, atol=0):
    raise RuntimeError("one or more domain CDFs do not end at 1")
if not np.all(np.diff(f_a) >= 0):
    raise RuntimeError("F_A is not monotone")
ecdf = pd.DataFrame({"q": q_grid, "F_A_equal_domain": f_a})
for d in DOMAINS:
    ecdf[f"F_{d}"] = domain_cdf[d]
for d in DOMAINS:
    ecdf[f"weight_{d}"] = 1.0 / 7.0
ecdf["step_rule"] = "right_continuous_<=_IEEE_float64"
ecdf["tie_handling"] = "stable_sort_preserve_ties"
ecdf.to_csv(bout / "A_equal_domain_ecdf.csv", index=False, encoding="utf-8", float_format="%.17g")

b6 = pd.read_csv(B6, usecols=["N_params_B","D_tokens_B","Q_score"])
if b6["Q_score"].isna().any() or not np.isfinite(b6["Q_score"].to_numpy(float)).all():
    raise RuntimeError("B6 Q_score contains non-finite values")
unique_b = np.unique(np.sort(b6["Q_score"].to_numpy(float), kind="stable"))
if len(unique_b) != M:
    raise RuntimeError(f"B6 unique Q count mismatch: expected={M}, observed={len(unique_b)}")
counts = np.array([int((b6["Q_score"].to_numpy(float) == b).sum()) for b in unique_b], dtype=int)
if not np.all(counts == counts[0]):
    raise RuntimeError("B6 unique Q levels are not equally repeated in the raw grid")
if b6.duplicated(["N_params_B","D_tokens_B","Q_score"]).any():
    raise RuntimeError("B6 contains duplicate N-D-Q keys")
f_b = np.arange(1, M + 1, dtype=float) / float(M)
b6_ecdf = pd.DataFrame({
    "b_index_1based": np.arange(1, M + 1, dtype=int),
    "Q_score": unique_b,
    "raw_count": counts,
    "unique_level_weight": 1.0 / M,
    "F_B": f_b,
    "generalized_inverse_lower_u": (np.arange(0, M, dtype=float) / float(M)),
    "generalized_inverse_upper_u": f_b,
})
b6_ecdf.to_csv(bout / "B6_unique_Q_ecdf.csv", index=False, encoding="utf-8", float_format="%.17g")

qmin = float(all_q.min()); qmax = float(all_q.max())
sentinels = np.array([np.nextafter(qmin, -np.inf), np.nextafter(qmax, np.inf)], dtype=float)
step_q = np.unique(np.concatenate([q_grid, sentinels]))
idx = np.maximum(1, np.ceil(M * np.interp(step_q, q_grid, f_a)).astype(int))
idx = np.minimum(idx, M)
mapped = unique_b[idx - 1]
support = np.where(step_q < qmin, "OUT_OF_SUPPORT_LOW", np.where(step_q > qmax, "OUT_OF_SUPPORT_HIGH", "IN_SUPPORT"))
usable = np.array([s == "IN_SUPPORT" for s in support], dtype=bool)
h3 = pd.DataFrame({
    "q": step_q,
    "F_A_from_Q_baseline_calibration": np.interp(step_q, q_grid, f_a),
    "m": M,
    "unclipped_index_1based": idx,
    "mapped_Q_B": mapped,
    "support_status": support,
    "boundary_rule": "u=0 returns b1; u=1 returns bm; out-of-support remains non-usable",
    "usable_for_numeric_prediction": usable,
    "source_kind": np.where(step_q < qmin, "support_sentinel_low", np.where(step_q > qmax, "support_sentinel_high", "Q_baseline_calibration")),
})
h3.to_csv(bout / "H3_mapping_steps.csv", index=False, encoding="utf-8", float_format="%.17g")

def cdf_value(q: float) -> float:
    return float(f_a[np.searchsorted(q_grid, q, side="right") - 1]) if q >= qmin else 0.0

def h3_value(q: float) -> tuple[float, str, bool]:
    f = 0.0 if q < qmin else (1.0 if q > qmax else cdf_value(q))
    j = int(max(1, min(M, int(np.ceil(M * f)))))
    st = "IN_SUPPORT" if qmin <= q <= qmax else ("OUT_OF_SUPPORT_LOW" if q < qmin else "OUT_OF_SUPPORT_HIGH")
    return float(unique_b[j - 1]), st, st == "IN_SUPPORT"

def h2_value(q: float, b: float) -> float:
    return float(0.6 + b * (q - qstar))

h3_star, h3_star_support, h3_star_usable = h3_value(qstar)
h3_qc_star, h3_qc_support, h3_qc_usable = h3_value(qcstar)
bridge = {
    "run_id": RID,
    "q_A_star": qstar,
    "q_C_star_sensitivity": qcstar,
    "H0": {"definition": "k=0; no map call", "eligibility": "IDENTIFIED_NULL_BASELINE", "mapped_value_at_anchor": None},
    "H1": {"definition": "h(q)=q", "eligibility": "SCENARIO_ONLY", "mapped_value_at_q_A_star": qstar, "mapped_value_at_q_C_star": qcstar},
    "H2": {"definition": "h(q)=0.6+b*(q-q_A_star)", "b_fixed_set": [0.5, 1.0, 2.0], "eligibility": "SCENARIO_ONLY", "mapped_value_at_q_A_star_for_all_b": 0.6, "qc_star_mapped_b_1": h2_value(qcstar,1.0), "qc_star_mapped_b_05": h2_value(qcstar,0.5)},
    "H3": {"definition": "h(q)=F_B^{-1}(F_A(q))", "eligibility": "SCENARIO_ONLY", "mapped_value_at_q_A_star": h3_star, "q_A_star_support_status": h3_star_support, "q_A_star_usable": h3_star_usable, "qc_star_uses_same_F_A": True, "mapped_value_at_q_C_star_using_same_F_A": h3_qc_star, "q_C_star_support_status": h3_qc_support, "q_C_star_usable": h3_qc_usable},
    "H4": {"definition": "retain B6 direction only; no A-side numeric benefit", "eligibility": "DIRECTION_ONLY_NOT_OPTIMIZABLE", "numeric_prediction": False},
    "A_B_scale_identifiability": "NOT_IDENTIFIABLE",
    "bridge_values_are_scenarios_not_estimated_parameters": True,
    "Q_support": {"Q_baseline_calibration_min": qmin, "Q_baseline_calibration_max": qmax, "B6_unique_Q_min": float(unique_b.min()), "B6_unique_Q_max": float(unique_b.max())},
    "CDF_rules": {"A_equal_domain_weights": [1.0/7.0]*7, "A_operator": "<=", "B_unique_level_weights": [1.0/8.0]*8, "B6_raw_grid_duplicates_ignored_for_CDF": True},
}
write_json(bout / "quality_bridge_scenarios.json", bridge)

qual = pd.DataFrame([
    {"bridge":"H0","eligibility":"IDENTIFIED_NULL_BASELINE","estimated_or_calibrated":False,"numeric_loss_available_in_P":False,"reason":"Defines k=0 without invoking a cross-source map."},
    {"bridge":"H1","eligibility":"SCENARIO_ONLY","estimated_or_calibrated":False,"numeric_loss_available_in_P":False,"reason":"Identity is an assumption; no observed A-to-B correspondence identifies it."},
    {"bridge":"H2","eligibility":"SCENARIO_ONLY","estimated_or_calibrated":False,"numeric_loss_available_in_P":False,"reason":"b in {0.5,1,2} is fixed by scenario registry and is not fit."},
    {"bridge":"H3","eligibility":"SCENARIO_ONLY","estimated_or_calibrated":False,"numeric_loss_available_in_P":False,"reason":"F_A and F_B are empirical CDFs, but cross-source correspondence is not identified."},
    {"bridge":"H4","eligibility":"DIRECTION_ONLY_NOT_OPTIMIZABLE","estimated_or_calibrated":False,"numeric_loss_available_in_P":False,"reason":"Retains B6 direction only and produces no A-side numeric benefit."},
])
qual.to_csv(bout / "bridge_qualification.csv", index=False, encoding="utf-8")

summary = {
    "status": "PASS",
    "selected_total": int(len(sel)),
    "domains": DOMAINS,
    "q_A_star": qstar,
    "q_C_star": qcstar,
    "q_A_baseline_min": qmin,
    "q_A_baseline_max": qmax,
    "B6_unique_Q": [float(x) for x in unique_b],
    "B6_unique_Q_count": int(len(unique_b)),
    "H3_q_A_star_mapped_Q": h3_star,
    "H3_q_A_star_support_status": h3_star_support,
    "Q_C_same_F_A": True,
    "A_B_scale_status": "NOT_IDENTIFIABLE",
}
write_json(bout / "stage_summary.json", summary)
print(json.dumps(summary, ensure_ascii=False))


