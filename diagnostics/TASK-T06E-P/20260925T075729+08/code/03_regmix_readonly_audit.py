from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

RUN = Path(__file__).resolve().parents[1]
WS = RUN.parents[2]
OUT = RUN / "mixture_audit"
OUT.mkdir(exist_ok=True)
RAW = WS / "F题/real_attachments/A_data_value"
MIX = WS / "solution/outputs/mixture"
MODEL_PATH = MIX / "model.json"

model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
features = list(model["features"])
linear = model["models"]["linear"]
coeff = np.asarray(linear["coefficients"], dtype=float)  # 13 x 17

sets = {
    "train_1m": ("regmix_tables/train_mixture_1m.csv", "regmix_tables/train_pile_loss_1m.csv", "linear_train_1m_predictions.csv", "training_fit", "training_only"),
    "test_1m": ("regmix_tables/test_mixture_1m.csv", "regmix_tables/test_pile_loss_1m.csv", "linear_test_1m_predictions.csv", "independent_1m_test", "deployment_test"),
    "test_60m": ("regmix_tables/test_mixture_60m.csv", "regmix_tables/test_pile_loss_60m.csv", "linear_test_60m_predictions.csv", "zero_shot_cross_scale", "cross_scale_transport"),
    "test_1B": ("regmix_tables/test_mixture_1B.csv", "regmix_tables/test_pile_loss_1B.csv", "linear_test_1B_predictions.csv", "zero_shot_cross_scale", "cross_scale_transport"),
    "est_10b": ("regmix_tables/est_mixture_10b.csv", "regmix_tables/est_pile_loss_10b.csv", "linear_est_10b_predictions.csv", "estimated_scenario", "estimated_not_truth"),
    "est_70b": ("regmix_tables/est_mixture_70b.csv", "regmix_tables/est_pile_loss_70b.csv", "linear_est_70b_predictions.csv", "estimated_scenario", "estimated_not_truth"),
}

def normalized_from_raw(mixture_path: Path) -> tuple[pd.DataFrame, np.ndarray]:
    raw = pd.read_csv(mixture_path)
    if list(raw.columns[1:]) != features:
        raise RuntimeError(f"mixture order mismatch: {mixture_path}")
    p = raw.iloc[:, 1:].to_numpy(float)
    sums = p.sum(axis=1)
    if (sums <= 0).any() or not np.isfinite(p).all():
        raise RuntimeError(f"invalid mixture table: {mixture_path}")
    return raw[["index"]].copy(), p / sums[:, None]

def rankdata_average(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="stable")
    ranks = np.empty(len(x), dtype=float)
    i = 0
    while i < len(x):
        j = i + 1
        while j < len(x) and x[order[j]] == x[order[i]]:
            j += 1
        ranks[order[i:j]] = 0.5 * ((i + 1) + j)
        i = j
    return ranks

def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = rankdata_average(np.asarray(x, dtype=float))
    ry = rankdata_average(np.asarray(y, dtype=float))
    if np.std(rx) == 0 or np.std(ry) == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])

def metrics_for(y: np.ndarray, pred: np.ndarray, train_mean: np.ndarray) -> dict:
    err = pred - y
    pred_mean = pred.mean(axis=1)
    obs_mean = y.mean(axis=1)
    dom_ss_res = np.sum(err ** 2, axis=0)
    dom_ss_tot = np.sum((y - y.mean(axis=0)) ** 2, axis=0)
    dom_mse = dom_ss_res / len(y)
    dom_mse_base = np.sum((y - train_mean) ** 2, axis=0) / len(y)
    r2_domains = 1.0 - dom_ss_res / dom_ss_tot
    mse_equal_domains = float(dom_mse.mean())
    base_mse_equal_domains = float(dom_mse_base.mean())
    return {
        "n": int(len(y)),
        "rmse_all_domains": float(np.sqrt(np.mean(err ** 2))),
        "mae_all_domains": float(np.mean(np.abs(err))),
        "r2_domain_mean": float(r2_domains.mean()),
        "rmse_equal_domain_mean": float(np.sqrt(np.mean((pred_mean - obs_mean) ** 2))),
        "mae_equal_domain_mean": float(np.mean(np.abs(pred_mean - obs_mean))),
        "r2_equal_domain_mean": float(1.0 - np.sum((pred_mean - obs_mean) ** 2) / np.sum((obs_mean - obs_mean.mean()) ** 2)),
        "spearman_equal_domain_mean": spearman(obs_mean, pred_mean),
        "mse_equal_domain_means": mse_equal_domains,
        "baseline_mse_equal_domain_means": base_mse_equal_domains,
        "mse_improvement_vs_domain_training_mean": float(1.0 - mse_equal_domains / base_mse_equal_domains),
        "abs_loss_error_equal_domain_mean": float(np.mean(np.abs(pred_mean - obs_mean))),
    }

_, train_p = normalized_from_raw(RAW / sets["train_1m"][0])
recomputed_p0 = train_p.mean(axis=0)
model_p0 = np.asarray(model["reference_p"], dtype=float)
if not np.array_equal(recomputed_p0, model_p0):
    raise RuntimeError("A4-normalized p0 does not exactly match model.reference_p")
ref_rows = []
for i, d in enumerate(features):
    ref_rows.append({
        "domain_order": i,
        "mixture_feature_column": d,
        "mixture_domain": d.removeprefix("train_the_pile_"),
        "raw_column": i + 1,
        "recomputed_p0_A4_normalized_mean": recomputed_p0[i],
        "model_json_reference_p": model_p0[i],
        "abs_difference": abs(recomputed_p0[i] - model_p0[i]),
        "exact_float64_match": bool(recomputed_p0[i] == model_p0[i]),
        "p0_nonnegative": bool(model_p0[i] >= 0),
        "p0_preserves_zero_values": bool((recomputed_p0[i] == 0) or (model_p0[i] != 0)),
    })
pd.DataFrame(ref_rows).to_csv(OUT / "reference_p_reconciliation.csv", index=False, encoding="utf-8")

# Frozen training-domain means are computed from A5 only and never re-estimated from tests.
train_loss = pd.read_csv(RAW / sets["train_1m"][1])
loss_columns = list(train_loss.columns[1:])
if len(loss_columns) != 13:
    raise RuntimeError("expected 13 validation Loss columns")
train_mean = train_loss[loss_columns].to_numpy(float).mean(axis=0)
if not np.isfinite(train_mean).all():
    raise RuntimeError("non-finite training-domain mean")

summary_rows = []
long_rows = []
repro_rows = []
scale_store = {}
for scale, (mix_rel, loss_rel, pred_rel, role, support_role) in sets.items():
    _, p = normalized_from_raw(RAW / mix_rel)
    loss = pd.read_csv(RAW / loss_rel)
    y = loss[loss_columns].to_numpy(float)
    pred = p @ coeff.T
    saved = pd.read_csv(MIX / pred_rel)
    saved_pred_cols = [c for c in saved.columns if c.startswith("pred_")]
    saved_pred = saved[saved_pred_cols].to_numpy(float)
    if saved_pred.shape != pred.shape:
        raise RuntimeError(f"saved prediction shape mismatch for {scale}")
    max_pred_diff = float(np.max(np.abs(pred - saved_pred)))
    if max_pred_diff > 1e-12:
        raise RuntimeError(f"prediction reproduction mismatch for {scale}: {max_pred_diff}")
    m = metrics_for(y, pred, train_mean)
    m.update({
        "model": "linear",
        "scale": scale,
        "role": role,
        "support_role": support_role,
        "uses_frozen_linear_coefficients": True,
        "refit_or_reselected": False,
        "truth_kind": "observed" if scale in {"train_1m","test_1m"} else ("observed_cross_scale" if scale in {"test_60m","test_1B"} else "estimated_not_truth"),
        "deployment_test_1m": scale == "test_1m",
        "cross_scale_transport": scale in {"test_60m","test_1B"},
        "estimated_not_truth": scale in {"est_10b","est_70b"},
        "saved_prediction_max_abs_difference": max_pred_diff,
    })
    if scale == "test_1m":
        m["criterion_mse_improvement_ge_5pct"] = bool(m["mse_improvement_vs_domain_training_mean"] >= 0.05)
        m["criterion_spearman_ge_0.5"] = bool(m["spearman_equal_domain_mean"] >= 0.5)
        m["eligibility_both_criteria_pass"] = bool(m["criterion_mse_improvement_ge_5pct"] and m["criterion_spearman_ge_0.5"])
    else:
        m["criterion_mse_improvement_ge_5pct"] = None
        m["criterion_spearman_ge_0.5"] = None
        m["eligibility_both_criteria_pass"] = None
    summary_rows.append(m)
    scale_store[scale] = {"p": p, "y": y, "pred": pred, "index": loss["index"].to_numpy(), "mix_index": pd.read_csv(RAW / mix_rel)["index"].to_numpy()}
    for j, dcol in enumerate(loss_columns):
        model_mse = float(np.mean((pred[:, j] - y[:, j]) ** 2))
        base_mse = float(np.mean((y[:, j] - train_mean[j]) ** 2))
        long_rows.append({
            "scale": scale,
            "role": role,
            "support_role": support_role,
            "domain_order": j,
            "validation_domain": dcol,
            "n": int(len(y)),
            "truth_kind": "estimated_not_truth" if scale in {"est_10b","est_70b"} else "observed",
            "domain_training_mean_baseline": float(train_mean[j]),
            "domain_model_mse": model_mse,
            "domain_baseline_mse": base_mse,
            "domain_mse_improvement": float(1.0 - model_mse / base_mse),
            "domain_model_rmse": float(np.sqrt(model_mse)),
            "domain_baseline_rmse": float(np.sqrt(base_mse)),
            "domain_spearman": spearman(y[:, j], pred[:, j]),
            "domain_mae": float(np.mean(np.abs(pred[:, j] - y[:, j]))),
        })
sdf = pd.DataFrame(summary_rows)
sdf.to_csv(OUT / "regmix_fixed_model_validation.csv", index=False, encoding="utf-8")
pd.DataFrame(long_rows).to_csv(OUT / "mixture_transport_audit.csv", index=False, encoding="utf-8")

# A6 and A8 recipes: test whether they form the same paired recipe cluster by index.
a6 = scale_store["test_1m"]; a8 = scale_store["test_60m"]
if not np.array_equal(a6["mix_index"], a8["mix_index"]):
    pair_ok = False
    max_pair_diff = float("nan")
else:
    pair_delta = np.abs(a6["p"] - a8["p"])
    max_pair_diff = float(pair_delta.max())
    pair_ok = bool(max_pair_diff == 0)
cross_rows = []
for row_i, idx in enumerate(a6["mix_index"]):
    cross_rows.append({
        "index": int(idx),
        "test_1m_row": row_i,
        "test_60m_row": row_i,
        "max_abs_normalized_p_delta": float(np.max(np.abs(a6["p"][row_i] - a8["p"][row_i]))) if pair_ok or np.array_equal(a6["mix_index"], a8["mix_index"]) else None,
        "exact_recipe_match": bool(np.array_equal(a6["p"][row_i], a8["p"][row_i])),
        "same_recipe_cluster_for_transport_audit": bool(pair_ok),
    })
pd.DataFrame(cross_rows).to_csv(OUT / "cross_scale_recipe_pairs.csv", index=False, encoding="utf-8")

# Mapping coverage: keep all 17 domains and explicit UNMAPPED state.
mapping = pd.read_csv(RAW / "domain_mapping_guide.csv")
quality_map = dict(zip(mapping["mixture_domain"], mapping["quality_domain"]))
map_type = dict(zip(mapping["mixture_domain"], mapping["mapping_type"]))
coverage_rows = []
for i, d in enumerate(features):
    short_domain = d.removeprefix("train_the_pile_")
    qd = quality_map.get(short_domain, "(none)")
    mt = map_type.get(short_domain, "missing")
    mapped = qd not in {"(none)", None, ""} and not pd.isna(qd)
    coverage_rows.append({
        "domain_order": i,
        "mixture_feature_column": d,
        "mixture_domain": short_domain,
        "quality_domain": qd if mapped else "UNMAPPED",
        "mapping_type_raw": mt,
        "coverage_class": "direct" if mt == "direct" else ("near" if mt == "near_direct" else ("none" if not mapped else mt)),
        "mapped": bool(mapped),
        "full_17_domain_quality_fill_performed": False,
        "renormalized_6_domains_as_17_performed": False,
    })
coverage = pd.DataFrame(coverage_rows)
coverage.to_csv(OUT / "domain_mapping_coverage.csv", index=False, encoding="utf-8")
if int((~coverage["mapped"]).sum()) != 11:
    raise RuntimeError("expected exactly 11 unmapped RegMix domains")

# p-Q column-space identity: use a support indicator for algebra only, never a quality value.
mapped_idx = np.flatnonzero(coverage["mapped"].to_numpy(bool))
q_support_indicator = np.zeros(len(features), dtype=float)
q_support_indicator[mapped_idx] = 1.0
qmix_support = train_p @ q_support_indicator
u, s, vt = np.linalg.svd(train_p, full_matrices=False)
tol = np.finfo(float).eps * max(train_p.shape) * (s[0] if len(s) else 0.0)
rank = int(np.sum(s > tol))
u_rank = u[:, :rank]
proj = u_rank @ (u_rank.T @ qmix_support)
residual = qmix_support - proj
relative_residual = float(np.linalg.norm(residual) / max(np.linalg.norm(qmix_support), np.finfo(float).tiny))
aug = np.column_stack([train_p, qmix_support])
rank_aug = int(np.linalg.matrix_rank(aug, tol=tol))
pq = {
    "status": "NOT_IDENTIFIABLE",
    "symbolic_identity": "theta^T p + gamma Q_mix = (theta + gamma q)^T p for fixed q",
    "design_matrix": "512 normalized A4 training recipes x 17 RegMix domains; no intercept",
    "design_rank": rank,
    "design_shape": list(train_p.shape),
    "qix_indicator_role": "ALGEBRAIC_SUPPORT_INDICATOR_ONLY_NOT_A_DOMAIN_QUALITY_VECTOR",
    "mapped_domain_count": int(len(mapped_idx)),
    "unmapped_domain_count": int(len(features) - len(mapped_idx)),
    "Q_mix_support_indicator_relative_projection_residual": relative_residual,
    "Q_mix_support_indicator_absolute_projection_residual": float(np.linalg.norm(residual)),
    "design_rank_after_adding_Q_mix_column": rank_aug,
    "rank_increase_from_Q_mix": rank_aug - rank,
    "gamma_separately_identifiable_from_theta": False,
    "null_direction": "Any supported vector added through Q_mix is absorbed by the p coefficients for the mapped columns.",
    "full_17_domain_Q_mix_available": False,
    "missing_domains_fill": "UNMAPPED_NOT_FILLED",
    "six_mapped_domains_renormalized_to_total_quality": False,
    "change_classes": [
        {"class": "p_direct_mixture_effect", "support": "DIRECTLY_SUPPORTED_BY_FROZEN_REGMIX_LINEAR_MODEL_WITHIN_SCALE"},
        {"class": "fixed_p_quality_change", "support": "NO_QUALITY_INTERVENTION_DATA"},
        {"class": "p_mechanical_Q_mix_change", "support": "DETERMINISTIC_ONLY_WITH_COMPLETE_Q; UNAVAILABLE_FOR_11_UNMAPPED_DOMAINS"}
    ],
    "T07_rule": "If Q and p are both present, mark REQUIRES_FIXED_P_QUALITY_INTERVENTION; never expose them as two independently tunable coordinates without feasibility evidence.",
}
(OUT / "p_q_identifiability.json").write_text(json.dumps(pq, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

test1 = sdf.loc[sdf["scale"].eq("test_1m")].iloc[0]
if not bool(test1["eligibility_both_criteria_pass"]):
    raise RuntimeError("frozen linear model failed preregistered 1M reporting criteria")
stage = {
    "status": "PASS",
    "p0_exact_match": bool(np.array_equal(recomputed_p0, model_p0)),
    "p0_max_abs_difference": float(np.max(np.abs(recomputed_p0 - model_p0))),
    "unmapped_domain_count": int((~coverage["mapped"]).sum()),
    "mapped_domain_count": int(coverage["mapped"].sum()),
    "test_1m_mse_improvement": float(test1["mse_improvement_vs_domain_training_mean"]),
    "test_1m_spearman": float(test1["spearman_equal_domain_mean"]),
    "test_1m_both_criteria_pass": bool(test1["eligibility_both_criteria_pass"]),
    "test_60m_transport_role": "REPORT_ONLY_NOT_RECALIBRATED",
    "test_1B_transport_role": "REPORT_ONLY_NOT_RECALIBRATED",
    "est_10b_70b_truth_status": "ESTIMATED_NOT_TRUTH",
    "A6_A8_same_recipe_cluster": pair_ok,
    "p_q_status": pq["status"],
    "linear_refit": False,
    "quadratic_reselected": False,
}
(OUT / "stage_summary.json").write_text(json.dumps(stage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(stage, ensure_ascii=False))

