from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4_common import (  # noqa: E402
    ALL_TARGETS, AUX_TARGET, BOOTSTRAP_DRAWS, C01_R1, C2, C3, C4, HORIZONS,
    RUN_DIR, RUN_ID, SCENARIO_IDS, SEED, T05, T08, TASKS,
    choose_center, condition_number, design_matrix, fit_ols, fit_quantile,
    fit_robust, iso_local, metric_mae, metric_rmse, parse_date,
    parse_dataset_tokens, pinball, predict_design, read_json, safe_quantile,
    safe_spearman, sha256_file, unix_to_local_date, write_csv, write_json,
    write_stage,
)

SPECS = ["M0_CONSTANT", "M1_SCALE", "M2_SCALE_TIME"]
PRIMARY_PROTOCOLS = ["GROUPED_5FOLD", "TIME_OUT_80_20", "LEAVE_ONE_FAMILY_OUT"]
CUTOFF = None
ORIGIN = None
SEAL_HASH = None
SCENARIO_HASH = None


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def load_master():
    pre = load_module(Path(__file__).with_name("01_preregister.py"), "g4_preregister")
    c2 = pd.read_csv(C2, low_memory=False)
    c3 = pd.read_csv(C3, low_memory=False)
    c4 = pd.read_csv(C4, low_memory=False)
    c8_wide = pd.read_csv(C01_R1 / "c8_model_wide_corrected.csv", low_memory=False)
    c8_task = pd.read_csv(C01_R1 / "c8_model_task_aggregate_corrected.csv", low_memory=False)
    cross = pd.read_csv(T05 / "model_identity_crosswalk.csv", low_memory=False)
    c2u, _ = pre.dedupe_c2_with_audit(c2, cross)
    c3u, _ = pre.dedupe_c3(c3)
    c4_match = pre.match_c4(c2u, c4)
    task_long = c8_task.copy()
    task_long["score_date"] = task_long["canonical_eval_unix_date"].map(unix_to_local_date)
    task_long["task_valid"] = task_long["canonical_score_finite"].fillna(False).astype(bool)
    task_dates = task_long[task_long.task_valid].groupby(["Model", "task_group"], as_index=False).agg(score_date=("score_date", "max"))
    valid_counts = task_long[task_long.task_valid].groupby("Model").size().rename("n_tasks_valid_pre_score")
    master = c2u.merge(c3u[["Model", "c3_year", "c3_year_status"]], on="Model", how="left", validate="one_to_one")
    master = master.merge(c4_match, on="Model", how="left", validate="one_to_one")
    master = master.merge(
        c8_wide[["Model", "n_tasks_valid", "six_task_complete", "partial_task_mean", "model_key"]],
        on="Model", how="left", validate="one_to_one",
    )
    master = master.merge(valid_counts, left_on="Model", right_index=True, how="left")
    master = master.merge(cross.loc[cross.source_table.eq("C8"), [
        "original_name", "canonical_model_id", "model_family"
    ]].rename(columns={
        "original_name": "Model", "canonical_model_id": "t05_c8_canonical_id",
        "model_family": "t05_c8_model_family",
    }), on="Model", how="left", validate="one_to_one")
    master["c2_present"] = True
    master["c8_present"] = master["n_tasks_valid"].notna()
    master["main_t05_canonical_id"] = master["_canonical_model_id_t05"].fillna(master["t05_c8_canonical_id"])
    master["model_family"] = master["t05_c8_model_family"]
    master["submission_date"] = master["Submission Date"].map(parse_date)
    master["date_ambiguous"] = master["_c2_duplicate_status"].eq("DUPLICATES_METADATA_CONFLICT")
    master["c4_parameters"] = pd.to_numeric(master["Parameters"], errors="coerce")
    master["c4_compute_direct"] = pd.to_numeric(master["Training compute (FLOP)"], errors="coerce")
    master["c4_dataset_tokens"] = master["Training dataset size (total)"].map(parse_dataset_tokens)
    master["n_observed"] = master["c4_parameters"].gt(0).fillna(False)
    master["d_observed"] = master["c4_dataset_tokens"].gt(0).fillna(False)
    master["compute_flops"] = np.nan
    master["compute_origin"] = "MISSING"
    direct = master["c4_compute_direct"].gt(0).fillna(False)
    prox = (~direct) & master["n_observed"] & master["d_observed"]
    master.loc[direct, "compute_flops"] = master.loc[direct, "c4_compute_direct"]
    master.loc[direct, "compute_origin"] = "C4_TRAINING_COMPUTE_FLOP"
    master.loc[prox, "compute_flops"] = 6.0 * master.loc[prox, "c4_parameters"] * master.loc[prox, "c4_dataset_tokens"]
    master.loc[prox, "compute_origin"] = "CONSTRUCTED_6ND"
    master["compute_observed"] = master["compute_flops"].gt(0).fillna(False)
    master["log10_compute"] = np.log10(master["compute_flops"].where(master["compute_flops"].gt(0)))
    master["log10_N"] = np.log10(master["c4_parameters"].where(master["c4_parameters"].gt(0)))
    c2_open = master["Epoch_AI_Open_Weights"].fillna("").astype(str).str.strip().str.lower()
    c4_open = master["Open model weights?"].fillna("").astype(str).str.strip().str.lower()
    lic = master["Hub License"].fillna("").astype(str).str.strip().str.lower()
    master["license_explicit"] = master["Hub License"].notna() & ~lic.isin(["", "unknown", "other", "nan"])
    master["type_pretrained"] = master["Type"].fillna("").astype(str).eq("🟢 pretrained")
    master["type_chat_or_finetuned"] = master["Type"].fillna("").astype(str).isin([
        "💬 chat models (RLHF, DPO, IFT, ...)", "🔶 fine-tuned on domain-specific datasets",
    ])
    master["open_weights_yes"] = c2_open.eq("yes") | c4_open.eq("yes")
    master["open_weights_no"] = c2_open.eq("no") | c4_open.eq("no")
    master["c3_unique"] = master["c3_year_status"].eq("UNIQUE_YEAR")
    master["identity_t05_unique"] = master["main_t05_canonical_id"].notna()
    master["main_eligible"] = (
        master["c8_present"] & master["c3_unique"] & master["c4_identity_status"].eq("UNIQUE")
        & master["identity_t05_unique"] & ~master["date_ambiguous"] & master["type_pretrained"]
        & master["open_weights_yes"] & ~master["open_weights_no"] & master["license_explicit"]
        & master["n_tasks_valid"].gt(0)
    )
    master["other_open_sensitivity_eligible"] = (
        master["c8_present"] & master["c3_unique"] & master["c4_identity_status"].eq("UNIQUE")
        & master["identity_t05_unique"] & ~master["date_ambiguous"] & master["type_chat_or_finetuned"]
        & master["open_weights_yes"] & ~master["open_weights_no"] & master["license_explicit"]
        & master["n_tasks_valid"].gt(0)
    )
    return master, task_long, task_dates


def task_frame(master: pd.DataFrame, c8_task: pd.DataFrame, c8_wide: pd.DataFrame, target: str, cutoff: pd.Timestamp) -> pd.DataFrame:
    if target in TASKS:
        q = c8_task[c8_task.task_group.eq(target)].copy()
        q["target_points"] = pd.to_numeric(q["canonical_score"], errors="coerce") * 100.0
        q["score_date"] = q["canonical_eval_unix_date"].map(unix_to_local_date)
        q = q[q["canonical_score_finite"].fillna(False).astype(bool)]
    else:
        q = c8_wide[["Model", "six_task_mean_complete_only"]].copy()
        q["task_group"] = AUX_TARGET
        q["target_points"] = pd.to_numeric(q["six_task_mean_complete_only"], errors="coerce") * 100.0
        q = q.dropna(subset=["target_points"])
        dates = c8_task[c8_task.canonical_score_finite.fillna(False).astype(bool)].groupby("Model")["canonical_eval_unix_date"].max().rename("score_date")
        q = q.merge(dates, left_on="Model", right_index=True, how="left")
        q["score_date"] = q["score_date"].map(unix_to_local_date)
    q = q.merge(master, on="Model", how="inner", validate="many_to_one")
    q = q[q["main_eligible"]].copy()
    q = q.rename(columns={"task_group": "benchmark_task"})
    q["target_role"] = "AUXILIARY_ONLY" if target == AUX_TARGET else "PRIMARY_TASK_VECTOR"
    q = q.dropna(subset=["target_points", "score_date"])
    if q.empty:
        return q
    t0 = pd.Timestamp(q["score_date"].min()).normalize()
    q["time_years"] = (pd.to_datetime(q["score_date"]) - t0).dt.total_seconds() / (365.2425 * 86400.0)
    q["split_time"] = np.where(pd.to_datetime(q["score_date"]) < cutoff, "TRAIN", "TEST")
    return q.reset_index(drop=True)


def design_with_sensitivity(frame: pd.DataFrame, spec: str) -> np.ndarray:
    if spec == "M1_LOG_N":
        return np.column_stack([
            np.ones(len(frame), dtype=float),
            pd.to_numeric(frame["log10_N"], errors="coerce").to_numpy(float),
        ])
    return design_matrix(frame, spec)


def fit_spec(frame: pd.DataFrame, target: str, spec: str, kind: str) -> dict[str, Any]:
    if kind == "MEAN_OLS":
        if spec == "M1_LOG_N":
            y = pd.to_numeric(frame["target_points"], errors="coerce").to_numpy(float)
            X = design_with_sensitivity(frame, spec)
            ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
            y, X = y[ok], X[ok]
            if len(y) < 3:
                return {"status": "NOT_IDENTIFIABLE", "n": int(len(y)), "coef": None}
            beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
            return {"status": "OK", "n": int(len(y)), "coef": beta.tolist(), "rank": int(rank), "p": int(X.shape[1])}
        return fit_ols(frame, "target_points", spec)
    if kind == "QUANTILE_0.90":
        if spec == "M1_LOG_N":
            y = pd.to_numeric(frame["target_points"], errors="coerce").to_numpy(float)
            X = design_with_sensitivity(frame, spec)
            ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
            y, X = y[ok], X[ok]
            if len(y) < 8:
                return {"status": "NOT_IDENTIFIABLE", "n": int(len(y)), "coef": None}
            import warnings
            import statsmodels.api as sm
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    fit = sm.QuantReg(y, X).fit(q=0.90, max_iter=2000, p_tol=1e-8)
                warning_names = [type(w.message).__name__ for w in caught]
                iterations = int(getattr(fit, "iterations", 0))
                beta = np.asarray(fit.params, dtype=float)
                ok_fit = bool(not warning_names and iterations < 2000 and np.isfinite(beta).all())
                return {"status": "OK" if ok_fit else "NOT_IDENTIFIABLE", "n": int(len(y)),
                        "coef": beta.tolist() if ok_fit else None, "iterations": iterations,
                        "warnings": "|".join(warning_names)}
            except Exception as exc:
                return {"status": "NOT_IDENTIFIABLE", "n": int(len(y)), "coef": None, "reason": str(exc)}
        return fit_quantile(frame, "target_points", spec, q=0.90)
    raise ValueError(kind)


def predict_spec(frame: pd.DataFrame, spec: str, coef: Any) -> np.ndarray:
    return design_with_sensitivity(frame, spec) @ np.asarray(coef, dtype=float)


def fold_indices(frame: pd.DataFrame, protocol: str, cutoff: pd.Timestamp):
    status = "EVALUABLE"
    folds = []
    if protocol == "GROUPED_5FOLD":
        groups = frame["main_t05_canonical_id"].astype(str).to_numpy()
        n_groups = len(np.unique(groups))
        if n_groups < 5 or len(frame) < 10:
            return folds, "NOT_EVALUABLE"
        gkf = GroupKFold(n_splits=5)
        for tr, te in gkf.split(frame, groups=groups):
            folds.append((np.asarray(tr), np.asarray(te)))
    elif protocol == "TIME_OUT_80_20":
        tr = np.flatnonzero(pd.to_datetime(frame["score_date"]) < cutoff)
        te = np.flatnonzero(pd.to_datetime(frame["score_date"]) >= cutoff)
        if len(te) < 10:
            return [], "NOT_EVALUABLE"
        folds = [(tr, te)]
    elif protocol == "LEAVE_ONE_FAMILY_OUT":
        families = frame["model_family"].astype(str).unique().tolist()
        if len(families) < 3:
            return [], "NOT_EVALUABLE"
        for fam in families:
            te = np.flatnonzero(frame["model_family"].astype(str).eq(fam))
            tr = np.flatnonzero(~frame["model_family"].astype(str).eq(fam))
            if len(tr) >= max(6, 1) and len(te) >= 1:
                folds.append((tr, te))
    else:
        raise ValueError(protocol)
    return folds, status


def cv_metrics(frame: pd.DataFrame, target: str, spec: str, kind: str, protocol: str, cutoff: pd.Timestamp) -> dict[str, Any]:
    folds, status = fold_indices(frame, protocol, cutoff)
    if status != "EVALUABLE":
        return {"protocol": protocol, "status": status, "n": 0, "n_train": 0, "n_test": 0,
                "mae": np.nan, "rmse": np.nan, "pinball": np.nan, "coverage": np.nan,
                "spearman": np.nan, "max_abs_error": np.nan, "fold_count": 0}
    pred = np.full(len(frame), np.nan, dtype=float)
    n_train = []
    n_test = []
    for tr, te in folds:
        fit = fit_spec(frame.iloc[tr], target, spec, kind)
        n_train.append(int(len(tr)))
        n_test.append(int(len(te)))
        if fit.get("status") != "OK" or fit.get("coef") is None:
            continue
        pred[te] = predict_spec(frame.iloc[te], spec, fit["coef"])
    mask = np.isfinite(pred) & pd.to_numeric(frame["target_points"], errors="coerce").notna().to_numpy()
    if mask.sum() == 0:
        return {"protocol": protocol, "status": "NOT_IDENTIFIABLE", "n": 0,
                "n_train": int(np.median(n_train)) if n_train else 0,
                "n_test": int(np.median(n_test)) if n_test else 0,
                "mae": np.nan, "rmse": np.nan, "pinball": np.nan, "coverage": np.nan,
                "spearman": np.nan, "max_abs_error": np.nan, "fold_count": len(folds)}
    y = pd.to_numeric(frame.loc[mask, "target_points"], errors="coerce").to_numpy(float)
    p = pred[mask]
    out = {
        "protocol": protocol, "status": "EVALUABLE", "n": int(mask.sum()),
        "n_train": int(np.median(n_train)) if n_train else 0,
        "n_test": int(np.median(n_test)) if n_test else 0,
        "mae": metric_mae(y, p), "rmse": metric_rmse(y, p),
        "pinball": pinball(y, p, 0.90) if kind == "QUANTILE_0.90" else np.nan,
        "coverage": float(np.mean(y <= p)) if kind == "QUANTILE_0.90" else np.nan,
        "spearman": safe_spearman(y, p),
        "max_abs_error": float(np.max(np.abs(y - p))),
        "fold_count": len(folds),
    }
    return out


def bootstrap_coefficients(frame: pd.DataFrame, target: str, spec: str, rng: np.random.Generator) -> pd.DataFrame:
    if spec == "M0_CONSTANT":
        return pd.DataFrame({"draw": [0], "b0": [float(pd.to_numeric(frame["target_points"], errors="coerce").mean())], "bC": [0.0], "bT": [0.0]})
    groups = sorted(frame["main_t05_canonical_id"].astype(str).unique().tolist())
    rows = []
    for draw in range(BOOTSTRAP_DRAWS):
        chosen = rng.choice(groups, size=len(groups), replace=True)
        parts = [frame[frame["main_t05_canonical_id"].astype(str).eq(g)] for g in chosen]
        sample = pd.concat(parts, ignore_index=True) if parts else frame.iloc[0:0]
        fit = fit_spec(sample, target, spec, "MEAN_OLS")
        if fit.get("status") != "OK" or fit.get("coef") is None:
            continue
        b = np.asarray(fit["coef"], dtype=float)
        rows.append({"draw": draw, "b0": float(b[0]), "bC": float(b[1]) if len(b) > 1 else 0.0,
                     "bT": float(b[2]) if len(b) > 2 else 0.0})
    return pd.DataFrame(rows)


def direction_consistency(frame: pd.DataFrame, target: str, spec: str, rng: np.random.Generator) -> tuple[float, int]:
    if spec == "M0_CONSTANT":
        return 1.0, 0
    full = fit_spec(frame, target, spec, "MEAN_OLS")
    if full.get("status") != "OK":
        return np.nan, 0
    beta = np.asarray(full["coef"], dtype=float)
    draws = bootstrap_coefficients(frame, target, spec, rng)
    if draws.empty:
        return np.nan, 0
    signs = []
    for idx, name in [(1, "bC"), (2, "bT")]:
        if idx < len(beta) and abs(beta[idx]) > 1e-12 and name in draws:
            signs.append(float(np.mean(np.sign(draws[name].to_numpy(float)) == np.sign(beta[idx]))))
    return (float(np.min(signs)) if signs else np.nan), int(len(draws))


def relative_improvement(base: float, candidate: float) -> float:
    if not np.isfinite(base) or not np.isfinite(candidate) or abs(base) <= 1e-15:
        return np.nan
    return float((base - candidate) / base)


def build_candidate_outputs(task_frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    metric_rows = []
    selection_rows = []
    selected = {}
    scenario_choice = {}
    for target, full in task_frames.items():
        scale = full[full["compute_observed"] & full["time_years"].notna()].copy()
        cv_frames = {"M0_CONSTANT": scale, "M1_SCALE": scale, "M2_SCALE_TIME": scale,
                     "M1_LOG_N": full[full["log10_N"].notna()].copy()}
        rng = np.random.default_rng(SEED)
        metric_cache = {}
        for spec in SPECS + ["M1_LOG_N"]:
            frame = cv_frames[spec]
            for kind in ["MEAN_OLS", "QUANTILE_0.90"]:
                for protocol in PRIMARY_PROTOCOLS:
                    m = cv_metrics(frame, target, spec, kind, protocol, CUTOFF)
                    metric_cache[(spec, kind, protocol)] = m
                    metric_rows.append({
                        "benchmark_task": target,
                        "target_role": "AUXILIARY_ONLY" if target == AUX_TARGET else "PRIMARY_TASK_VECTOR",
                        "model_spec": spec,
                        "estimator_kind": kind,
                        "selection_eligible": bool(spec in SPECS),
                        "protocol": protocol,
                        **m,
                    })
        selection_meta = {}
        for cand in ["M1_SCALE", "M2_SCALE_TIME"]:
            base = "M0_CONSTANT" if cand == "M1_SCALE" else "M1_SCALE"
            rows = []
            improvements = {}
            for protocol in PRIMARY_PROTOCOLS:
                bm = metric_cache[(base, "MEAN_OLS", protocol)]
                cm = metric_cache[(cand, "MEAN_OLS", protocol)]
                bq = metric_cache[(base, "QUANTILE_0.90", protocol)]
                cq = metric_cache[(cand, "QUANTILE_0.90", protocol)]
                evaluable = bool(bm["status"] == cm["status"] == bq["status"] == cq["status"] == "EVALUABLE")
                imp_mean = relative_improvement(bm["rmse"], cm["rmse"]) if evaluable else np.nan
                imp_q = relative_improvement(bq["pinball"], cq["pinball"]) if evaluable else np.nan
                improvements[protocol] = {"evaluable": evaluable, "mean_rmse_improvement": imp_mean, "q90_pinball_improvement": imp_q}
            evaluable_protocols = [p for p in PRIMARY_PROTOCOLS if improvements[p]["evaluable"]]
            passing = [p for p in evaluable_protocols if improvements[p]["mean_rmse_improvement"] >= 0.05 and improvements[p]["q90_pinball_improvement"] >= 0.05]
            degrading = [p for p in evaluable_protocols if improvements[p]["mean_rmse_improvement"] < -0.10 or improvements[p]["q90_pinball_improvement"] < -0.10]
            passed_rank, cond, rank, p = condition_number(scale, cand)
            consistency, draws_ok = direction_consistency(scale, target, cand, rng)
            direction_pass = bool(np.isfinite(consistency) and consistency >= 0.80)
            gate = bool(len(evaluable_protocols) >= 2 and len(passing) >= 2 and not degrading and passed_rank and direction_pass)
            selection_meta[cand] = {
                "comparison_base": base, "evaluable_protocols": len(evaluable_protocols),
                "passing_protocols": len(passing), "passing_protocol_names": "|".join(passing),
                "degrading_protocols": "|".join(degrading),
                "direction_consistency": consistency, "bootstrap_draws_ok": draws_ok,
                "design_full_rank": bool(rank == p), "condition_number": cond,
                "upgrade_gate_pass": gate,
            }
            selection_rows.append({
                "benchmark_task": target, "candidate_model": cand, "comparison_base": base,
                "n_scale_fit": int(len(scale)),
                "n_evaluable_protocols": len(evaluable_protocols),
                "n_protocols_with_dual_ge_5pct": len(passing),
                "protocols_passing": "|".join(passing),
                "protocols_degrading_gt_10pct": "|".join(degrading),
                "direction_consistency": consistency,
                "bootstrap_draws_ok": int(draws_ok),
                "design_full_rank": bool(rank == p), "condition_number": cond,
                "upgrade_gate_pass": gate,
                "selection_status": "PASS_UPGRADE_GATE" if gate else "FAIL_UPGRADE_GATE",
                "mean_rmse_improvement_group": improvements["GROUPED_5FOLD"]["mean_rmse_improvement"],
                "q90_pinball_improvement_group": improvements["GROUPED_5FOLD"]["q90_pinball_improvement"],
                "mean_rmse_improvement_time": improvements["TIME_OUT_80_20"]["mean_rmse_improvement"],
                "q90_pinball_improvement_time": improvements["TIME_OUT_80_20"]["q90_pinball_improvement"],
                "mean_rmse_improvement_family": improvements["LEAVE_ONE_FAMILY_OUT"]["mean_rmse_improvement"],
                "q90_pinball_improvement_family": improvements["LEAVE_ONE_FAMILY_OUT"]["q90_pinball_improvement"],
            })
        m0_rows = []
        for protocol in PRIMARY_PROTOCOLS:
            mt = metric_cache[("M0_CONSTANT", "MEAN_OLS", protocol)]
            qt = metric_cache[("M0_CONSTANT", "QUANTILE_0.90", protocol)]
            m0_rows.append(f"{protocol}:{mt['status']}/{qt['status']}")
        selection_rows.append({
            "benchmark_task": target, "candidate_model": "M0_CONSTANT", "comparison_base": "",
            "n_scale_fit": int(len(scale)), "n_evaluable_protocols": int(sum(metric_cache[("M0_CONSTANT", "MEAN_OLS", p)]["status"] == "EVALUABLE" for p in PRIMARY_PROTOCOLS)),
            "n_protocols_with_dual_ge_5pct": 0, "protocols_passing": "", "protocols_degrading_gt_10pct": "",
            "direction_consistency": 1.0, "bootstrap_draws_ok": BOOTSTRAP_DRAWS,
            "design_full_rank": True, "condition_number": 1.0, "upgrade_gate_pass": True,
            "selection_status": "BASELINE_ALWAYS_AVAILABLE", "protocol_summary": "|".join(m0_rows),
        })
        if selection_meta["M2_SCALE_TIME"]["upgrade_gate_pass"]:
            sel = "M2_SCALE_TIME"
        elif selection_meta["M1_SCALE"]["upgrade_gate_pass"]:
            sel = "M1_SCALE"
        else:
            sel = "M0_CONSTANT"
        qfit = fit_spec(scale, target, "M2_SCALE_TIME", "QUANTILE_0.90") if len(scale) else {"status": "NOT_IDENTIFIABLE"}
        scen = "M2_SCALE_TIME" if qfit.get("status") == "OK" else sel
        selected[target] = sel
        scenario_choice[target] = {
            "model": scen,
            "qualification": "SCENARIO_VALIDATED" if scen == sel and scen == "M2_SCALE_TIME" else (
                "SCENARIO_ONLY_UNVALIDATED" if scen == "M2_SCALE_TIME" else "VALIDATED_ASSOCIATION_MODEL"
            ),
        }
    metrics_df = pd.DataFrame(metric_rows)
    selection_df = pd.DataFrame(selection_rows).sort_values(["benchmark_task", "candidate_model"]).reset_index(drop=True)
    return metrics_df, selection_df, {"selected": selected, "scenario": scenario_choice}


def fit_frame(frame: pd.DataFrame, spec: str) -> pd.DataFrame:
    if spec == "M0_CONSTANT":
        return frame[pd.to_numeric(frame["target_points"], errors="coerce").notna()].copy()
    if spec == "M1_SCALE":
        return frame[frame["compute_observed"] & frame["log10_compute"].notna()].copy()
    if spec == "M2_SCALE_TIME":
        return frame[frame["compute_observed"] & frame["log10_compute"].notna() & frame["time_years"].notna()].copy()
    if spec == "M1_LOG_N":
        return frame[frame["log10_N"].notna()].copy()
    raise ValueError(spec)


def contribution_for_fit(frame: pd.DataFrame, target: str, spec: str, coef: np.ndarray, origin: pd.Timestamp) -> dict[str, Any]:
    if frame.empty or coef is None:
        return {"status": "NOT_IDENTIFIABLE"}
    start = pd.Timestamp(frame["score_date"].min()).normalize()
    if spec == "M0_CONSTANT":
        return {"status": "OK", "t_start": start, "t_origin": origin, "logc_start": np.nan,
                "logc_origin": np.nan, "delta_scale": 0.0, "delta_non_scale": 0.0,
                "delta_fitted": 0.0, "non_scale_reason": "MODEL_HAS_NO_TIME_TERM_AND_NO_SCALE_TERM"}
    c_start = choose_center(frame, start, 365)
    c_origin = choose_center(frame, origin, 365)
    bC = float(coef[1]) if len(coef) > 1 else 0.0
    bT = float(coef[2]) if len(coef) > 2 else 0.0
    ds = bC * (c_origin - c_start) if np.isfinite(c_start) and np.isfinite(c_origin) else np.nan
    dt_years = (origin - start).total_seconds() / (365.2425 * 86400.0)
    dns = bT * dt_years if spec == "M2_SCALE_TIME" else 0.0
    reason = "MODEL_HAS_NO_TIME_TERM" if spec != "M2_SCALE_TIME" else ""
    return {"status": "OK", "t_start": start, "t_origin": origin, "logc_start": c_start,
            "logc_origin": c_origin, "delta_scale": ds, "delta_non_scale": dns,
            "delta_fitted": ds + dns, "non_scale_reason": reason}


def bootstrap_contribution(frame: pd.DataFrame, target: str, spec: str, origin: pd.Timestamp, rng: np.random.Generator) -> pd.DataFrame:
    if spec == "M0_CONSTANT":
        return pd.DataFrame([{"delta_scale": 0.0, "delta_non_scale": 0.0, "delta_fitted": 0.0}] * BOOTSTRAP_DRAWS)
    groups = sorted(frame["main_t05_canonical_id"].astype(str).unique().tolist())
    rows = []
    for _ in range(BOOTSTRAP_DRAWS):
        chosen = rng.choice(groups, size=len(groups), replace=True)
        sample = pd.concat([frame[frame["main_t05_canonical_id"].astype(str).eq(g)] for g in chosen], ignore_index=True)
        fit = fit_spec(sample, target, spec, "MEAN_OLS")
        if fit.get("status") != "OK" or fit.get("coef") is None:
            continue
        c = contribution_for_fit(sample, target, spec, np.asarray(fit["coef"], dtype=float), origin)
        if c.get("status") == "OK":
            rows.append({
                "delta_scale": c["delta_scale"], "delta_non_scale": c["delta_non_scale"],
                "delta_fitted": c["delta_fitted"],
            })
    return pd.DataFrame(rows)


def build_contributions(task_frames: dict[str, pd.DataFrame], selected: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    coeff_rows = []
    contrib_rows = []
    unc_rows = []
    for target, full in task_frames.items():
        spec = selected[target]
        frame = fit_frame(full, spec)
        mean_fit = fit_spec(frame, target, spec, "MEAN_OLS")
        qspec = "M2_SCALE_TIME" if fit_spec(frame, target, "M2_SCALE_TIME", "QUANTILE_0.90").get("status") == "OK" else spec
        qframe = fit_frame(full, qspec)
        qfit = fit_spec(qframe, target, qspec, "QUANTILE_0.90")
        robust = fit_robust(frame, "target_points", spec)
        passed, cond, rank, p = condition_number(frame, spec)
        if mean_fit.get("status") == "OK":
            coef = np.asarray(mean_fit["coef"], dtype=float)
            c = contribution_for_fit(frame, target, spec, coef, ORIGIN)
        else:
            coef = np.array([])
            c = {"status": "NOT_IDENTIFIABLE"}
        b0 = float(coef[0]) if len(coef) > 0 else np.nan
        bC = float(coef[1]) if len(coef) > 1 else 0.0
        bT = float(coef[2]) if len(coef) > 2 else 0.0
        rc = np.asarray(robust["coef"], dtype=float) if robust.get("status") == "OK" else np.array([])
        r_b0 = float(rc[0]) if len(rc) > 0 else np.nan
        r_bC = float(rc[1]) if len(rc) > 1 else 0.0
        r_bT = float(rc[2]) if len(rc) > 2 else 0.0
        qcoef = np.asarray(qfit["coef"], dtype=float) if qfit.get("status") == "OK" else np.array([])
        coeff_rows.append({
            "benchmark_task": target, "target_role": "AUXILIARY_ONLY" if target == AUX_TARGET else "PRIMARY_TASK_VECTOR",
            "selected_contribution_model": spec, "scenario_model": qspec,
            "n_fit": int(len(frame)), "fit_status": mean_fit.get("status"),
            "mean_b0": b0, "mean_bC_log10_compute": bC, "mean_bT_per_year": bT,
            "robust_status": robust.get("status"), "robust_b0": r_b0,
            "robust_bC_log10_compute": r_bC, "robust_bT_per_year": r_bT,
            "quantile_status": qfit.get("status"), "quantile_q": 0.90 if qfit.get("status") == "OK" else np.nan,
            "q90_b0": float(qcoef[0]) if len(qcoef) > 0 else np.nan,
            "q90_bC_log10_compute": float(qcoef[1]) if len(qcoef) > 1 else 0.0,
            "q90_bT_per_year": float(qcoef[2]) if len(qcoef) > 2 else 0.0,
            "design_full_rank": bool(rank == p), "condition_number": cond,
            "t_start": c.get("t_start"), "t_origin": c.get("t_origin"),
            "logc_start_center": c.get("logc_start"), "logc_origin_center": c.get("logc_origin"),
        })
        abs_den = abs(c.get("delta_scale", np.nan)) + abs(c.get("delta_non_scale", np.nan)) if c.get("status") == "OK" else np.nan
        signed_den_defined = bool(np.isfinite(abs_den) and abs_den > 1e-12)
        ds_share = abs(c["delta_scale"]) / abs_den if signed_den_defined else np.nan
        dns_share = abs(c["delta_non_scale"]) / abs_den if signed_den_defined else np.nan
        contrib_rows.append({
            "benchmark_task": target, "target_role": "AUXILIARY_ONLY" if target == AUX_TARGET else "PRIMARY_TASK_VECTOR",
            "selected_contribution_model": spec,
            "delta_scale_signed_points": c.get("delta_scale", np.nan),
            "delta_non_scale_signed_points": c.get("delta_non_scale", np.nan),
            "delta_fitted_points": c.get("delta_fitted", np.nan),
            "scale_association_abs_share": ds_share if signed_den_defined else "NOT_DEFINED",
            "non_scale_association_abs_share": dns_share if signed_den_defined else "NOT_DEFINED",
            "share_denominator": abs_den,
            "non_scale_reason": c.get("non_scale_reason", ""),
            "contribution_identity_error": (c.get("delta_fitted", np.nan) - (c.get("delta_scale", np.nan) + c.get("delta_non_scale", np.nan))) if c.get("status") == "OK" else np.nan,
        })
        rng = np.random.default_rng(SEED + 17)
        boot = bootstrap_contribution(frame, target, spec, ORIGIN, rng)
        for component, col in [("contrib_bootstrap_scale", "delta_scale"), ("contrib_bootstrap_non_scale", "delta_non_scale"), ("contrib_bootstrap_fitted", "delta_fitted")]:
            v = pd.to_numeric(boot[col], errors="coerce") if col in boot else pd.Series(dtype=float)
            unc_rows.append({
                "benchmark_task": target, "component_id": component, "selected_model": spec,
                "draws_ok": int(len(v)), "low_5pct": safe_quantile(v, 0.05), "median": safe_quantile(v, 0.50),
                "high_95pct": safe_quantile(v, 0.95), "status": "EVALUABLE" if len(v) else "NOT_IDENTIFIABLE",
                "notes": "canonical-model grouped bootstrap; fixed endpoint windows; no threshold change",
            })
        if robust.get("status") == "OK":
            rc2 = contribution_for_fit(frame, target, spec, rc, ORIGIN)
            unc_rows.append({
                "benchmark_task": target, "component_id": "robust_structure_sensitivity", "selected_model": spec,
                "draws_ok": 1, "low_5pct": np.nan, "median": rc2.get("delta_fitted", np.nan),
                "high_95pct": np.nan, "status": "DESCRIPTIVE",
                "notes": f"scale={rc2.get('delta_scale', np.nan)}; non_scale={rc2.get('delta_non_scale', np.nan)}",
            })
    return pd.DataFrame(coeff_rows), pd.DataFrame(contrib_rows), pd.DataFrame(unc_rows)


def forecast_origin_prediction(frame: pd.DataFrame, target: str, spec: str, coef: np.ndarray, logc_origin: float) -> float:
    if spec == "M0_CONSTANT":
        return float(coef[0])
    row = frame.iloc[[0]].copy()
    row["log10_compute"] = logc_origin
    row["time_years"] = 0.0
    return float(predict_spec(row, spec, coef)[0])


def build_forecasts(task_frames: dict[str, pd.DataFrame], selection_info: dict, scenario_registry: pd.DataFrame, seal: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scen_map = scenario_registry.set_index(["scenario_id", "horizon_months"]).to_dict("index")
    all_forecast_rows = []
    uncertainty_rows = []
    support_rows = []
    parameter_rows = []
    horizon_dates = seal["horizon_dates"]
    for target, full in task_frames.items():
        selected = selection_info["selected"][target]
        scenario_model = selection_info["scenario"][target]["model"]
        scenario_qualification = selection_info["scenario"][target]["qualification"]
        fit_df = fit_frame(full, scenario_model)
        qfit = fit_spec(fit_df, target, scenario_model, "QUANTILE_0.90")
        if qfit.get("status") != "OK" or qfit.get("coef") is None or fit_df.empty:
            for sid in SCENARIO_IDS:
                for h in HORIZONS:
                    all_forecast_rows.append({
                        "benchmark_task": target, "target_role": "AUXILIARY_ONLY" if target == AUX_TARGET else "PRIMARY_TASK_VECTOR",
                        "scenario_id": sid, "horizon_months": h, "forecast_origin": ORIGIN.date().isoformat(),
                        "forecast_date": horizon_dates[str(h)], "prediction_points": np.nan,
                        "record_status": "NOT_IDENTIFIABLE", "forecast_eligibility": "NOT_IDENTIFIABLE",
                        "scenario_model": scenario_model, "selected_contribution_model": selected,
                        "loss_bridge_used": False,
                    })
            continue
        qcoef = np.asarray(qfit["coef"], dtype=float)
        scale_train = fit_df if scenario_model != "M0_CONSTANT" else full[full["log10_compute"].notna()]
        support_min = float(scale_train["log10_compute"].min()) if len(scale_train) else np.nan
        support_max = float(scale_train["log10_compute"].max()) if len(scale_train) else np.nan
        if scenario_model == "M0_CONSTANT":
            logc_origin = np.nan
            logc_origin_90 = np.nan
        else:
            win = scale_train[pd.to_datetime(scale_train["score_date"]).between(ORIGIN - pd.Timedelta(days=365), ORIGIN)]
            logc_origin = float(pd.to_numeric(win["log10_compute"], errors="coerce").median()) if len(win) >= 3 else (float(scale_train["log10_compute"].max()) if len(scale_train) else np.nan)
            logc_origin_90 = float(pd.to_numeric(win["log10_compute"], errors="coerce").quantile(0.90)) if len(win) >= 3 else logc_origin
        origin_pred = forecast_origin_prediction(fit_df, target, scenario_model, qcoef, logc_origin if scenario_model != "M0_CONSTANT" else np.nan)
        scenario_values = {}
        for sid in SCENARIO_IDS:
            for h in HORIZONS:
                sv = scen_map[(sid, h)]
                forecast_date = pd.Timestamp(sv["forecast_date"]).normalize()
                time_h = (forecast_date - ORIGIN).total_seconds() / (365.2425 * 86400.0)
                logc_future = logc_origin if scenario_model == "M0_CONSTANT" else logc_origin + math.log10(float(sv["annual_multiplier"])) * time_h
                row = fit_df.iloc[[0]].copy() if len(fit_df) else full.iloc[[0]].copy()
                row["log10_compute"] = logc_future
                row["time_years"] = time_h
                pred = float(predict_spec(row, scenario_model, qcoef)[0])
                clipped = float(np.clip(pred, 0.0, 100.0))
                time_contrib = float(qcoef[2] * time_h) if scenario_model == "M2_SCALE_TIME" and len(qcoef) > 2 else 0.0
                compute_oos = bool(scenario_model != "M0_CONSTANT" and np.isfinite(logc_future) and (logc_future < support_min or logc_future > support_max))
                time_oos = bool(scenario_model == "M2_SCALE_TIME" and time_h > float(fit_df["time_years"].max()))
                range_oos = bool(pred < 0.0 or pred > 100.0)
                rec = {
                    "benchmark_task": target,
                    "target_role": "AUXILIARY_ONLY" if target == AUX_TARGET else "PRIMARY_TASK_VECTOR",
                    "scenario_id": sid, "scenario_order": int(sv["scenario_order"]),
                    "horizon_months": h, "forecast_origin": ORIGIN.date().isoformat(),
                    "forecast_date": forecast_date.date().isoformat(),
                    "selected_contribution_model": selected, "scenario_model": scenario_model,
                    "model_qualification": scenario_qualification,
                    "record_status": "SCENARIO_FORECAST",
                    "forecast_eligibility": scenario_qualification,
                    "progress_status": "SCENARIO_NUMERIC_UNVALIDATED" if scenario_qualification == "SCENARIO_ONLY_UNVALIDATED" else "VALIDATED_ASSOCIATION_SCENARIO",
                    "prediction_points": pred, "prediction_range_constrained_points": clipped,
                    "forecast_origin_points": origin_pred, "increment_from_origin_points": pred - origin_pred,
                    "score_range_oos": range_oos,
                    "logc_origin": logc_origin, "logc_origin_q90": logc_origin_90,
                    "logc_future": logc_future, "annual_multiplier": float(sv["annual_multiplier"]),
                    "annual_log_growth": float(sv["annual_log_growth"]),
                    "growth_source": sv["growth_source"],
                    "compute_support_min": support_min, "compute_support_max": support_max,
                    "compute_future_oos": compute_oos,
                    "time_train_min_years": float(fit_df["time_years"].min()) if len(fit_df) else np.nan,
                    "time_train_max_years": float(fit_df["time_years"].max()) if len(fit_df) else np.nan,
                    "time_horizon_years": time_h, "time_future_oos": time_oos,
                    "time_term_contribution_points": time_contrib,
                    "n_fit": int(len(fit_df)), "q90_status": qfit["status"],
                    "scenario_registry_sha256": SCENARIO_HASH,
                    "seal_sha256": SEAL_HASH, "loss_bridge_used": False,
                }
                all_forecast_rows.append(rec)
                scenario_values[(sid, h)] = pred
                support_rows.append({
                    "benchmark_task": target, "scenario_id": sid, "horizon_months": h,
                    "scenario_model": scenario_model, "prediction_points": pred,
                    "compute_support_min": support_min, "compute_support_max": support_max,
                    "logc_future": logc_future, "compute_future_oos": compute_oos,
                    "time_train_max_years": float(fit_df["time_years"].max()) if len(fit_df) else np.nan,
                    "time_horizon_years": time_h, "time_future_oos": time_oos,
                    "score_range_oos": range_oos, "range_constrained_prediction_points": clipped,
                    "status": "OOS_FLAGGED" if (compute_oos or time_oos or range_oos) else "IN_SUPPORT",
                })
        # parameter/resampling and model-selection uncertainty
        groups = sorted(fit_df["main_t05_canonical_id"].astype(str).unique().tolist())
        rng = np.random.default_rng(SEED + 29)
        boot_pred = {sid: {h: [] for h in HORIZONS} for sid in SCENARIO_IDS}
        for _ in range(BOOTSTRAP_DRAWS):
            chosen = rng.choice(groups, size=len(groups), replace=True)
            sample = pd.concat([fit_df[fit_df["main_t05_canonical_id"].astype(str).eq(g)] for g in chosen], ignore_index=True)
            bf = fit_spec(sample, target, scenario_model, "QUANTILE_0.90")
            if bf.get("status") != "OK" or bf.get("coef") is None:
                continue
            bc = np.asarray(bf["coef"], dtype=float)
            for sid in SCENARIO_IDS:
                for h in HORIZONS:
                    sv = scen_map[(sid, h)]
                    forecast_date = pd.Timestamp(sv["forecast_date"]).normalize()
                    time_h = (forecast_date - ORIGIN).total_seconds() / (365.2425 * 86400.0)
                    logc_future = logc_origin if scenario_model == "M0_CONSTANT" else logc_origin + math.log10(float(sv["annual_multiplier"])) * time_h
                    rr = fit_df.iloc[[0]].copy()
                    rr["log10_compute"] = logc_future
                    rr["time_years"] = time_h
                    boot_pred[sid][h].append(float(predict_spec(rr, scenario_model, bc)[0]))
        for h in HORIZONS:
            for sid in SCENARIO_IDS:
                vals = pd.Series(boot_pred[sid][h], dtype=float)
                parameter_rows.append({
                    "benchmark_task": target, "horizon_months": h, "scenario_id": sid,
                    "component_id": "parameter_resampling", "selected_or_scenario_model": scenario_model,
                    "n": int(len(vals)), "value": scenario_values[(sid, h)],
                    "low": safe_quantile(vals, 0.05), "high": safe_quantile(vals, 0.95),
                    "status": "EVALUABLE" if len(vals) else "NOT_IDENTIFIABLE",
                    "source_reference": "500 canonical-model grouped bootstrap of q90 model",
                    "combined_ci_created": False,
                })
            candidate_vals = []
            for spec in SPECS:
                ff = fit_frame(full, spec)
                fq = fit_spec(ff, target, spec, "QUANTILE_0.90")
                if fq.get("status") != "OK" or fq.get("coef") is None or ff.empty:
                    continue
                # Reuse origin-scale level for comparability.
                sv = scen_map[("BASELINE", h)]
                fdate = pd.Timestamp(sv["forecast_date"]).normalize()
                th = (fdate - ORIGIN).total_seconds() / (365.2425 * 86400.0)
                lc = logc_origin if spec != "M0_CONSTANT" else np.nan
                if spec != "M0_CONSTANT":
                    lc = logc_origin + math.log10(1.5) * th
                rr = ff.iloc[[0]].copy()
                rr["log10_compute"] = lc
                rr["time_years"] = th
                candidate_vals.append(float(predict_spec(rr, spec, np.asarray(fq["coef"], dtype=float))[0]))
            uncertainty_rows.append({
                "benchmark_task": target, "horizon_months": h, "scenario_id": "BASELINE",
                "component_id": "model_selection", "selected_or_scenario_model": scenario_model,
                "n": len(candidate_vals), "value": scenario_values[("BASELINE", h)],
                "low": float(np.min(candidate_vals)) if candidate_vals else np.nan,
                "high": float(np.max(candidate_vals)) if candidate_vals else np.nan,
                "status": "RANGE_ONLY_NOT_CI" if candidate_vals else "NOT_IDENTIFIABLE",
                "source_reference": "M0/M1/M2 pre-registered candidate range",
                "combined_ci_created": False,
            })
            scenario_pts = [scenario_values[(sid, h)] for sid in SCENARIO_IDS]
            uncertainty_rows.append({
                "benchmark_task": target, "horizon_months": h, "scenario_id": "ALL",
                "component_id": "scenario_structure", "selected_or_scenario_model": scenario_model,
                "n": len(scenario_pts), "value": scenario_values[("BASELINE", h)],
                "low": float(np.min(scenario_pts)), "high": float(np.max(scenario_pts)),
                "status": "RANGE_ONLY_NOT_CI",
                "source_reference": "frozen 1.0/1.5/2.0 or historical quantile grid",
                "combined_ci_created": False,
            })
            time_contrib = float(qcoef[2] * ((pd.Timestamp(horizon_dates[str(h)]) - ORIGIN).total_seconds() / (365.2425 * 86400.0))) if scenario_model == "M2_SCALE_TIME" and len(qcoef) > 2 else 0.0
            uncertainty_rows.append({
                "benchmark_task": target, "horizon_months": h, "scenario_id": "ALL",
                "component_id": "time_extrapolation", "selected_or_scenario_model": scenario_model,
                "n": int(len(fit_df)), "value": time_contrib, "low": np.nan, "high": np.nan,
                "status": "OUT_OF_SUPPORT" if scenario_model == "M2_SCALE_TIME" and ((pd.Timestamp(horizon_dates[str(h)]) - ORIGIN).days / 365.2425) > float(fit_df["time_years"].max()) else "IN_SUPPORT",
                "source_reference": "q90 time coefficient times horizon; not added to other components",
                "combined_ci_created": False,
            })
    return pd.DataFrame(all_forecast_rows), pd.DataFrame(parameter_rows), pd.DataFrame(uncertainty_rows), pd.DataFrame(support_rows)


def stratified_sensitivity(master: pd.DataFrame, c8_task: pd.DataFrame, target: str) -> dict[str, Any]:
    q = c8_task[c8_task.task_group.eq(target)].copy()
    q["target_points"] = pd.to_numeric(q["canonical_score"], errors="coerce") * 100.0
    q["score_date"] = q["canonical_eval_unix_date"].map(unix_to_local_date)
    q = q[q["canonical_score_finite"].fillna(False).astype(bool)]
    q = q.merge(master, on="Model", how="inner", validate="many_to_one")
    q = q[q["other_open_sensitivity_eligible"] & q["compute_observed"]].copy()
    if len(q) < 8:
        return {"benchmark_task": target, "cohort": "CHAT_FINETUNED_OPEN_SENSITIVITY", "status": "NOT_IDENTIFIABLE", "n": len(q)}
    t0 = pd.Timestamp(q["score_date"].min()).normalize()
    q["time_years"] = (pd.to_datetime(q["score_date"]) - t0).dt.total_seconds() / (365.2425 * 86400.0)
    q = q[q["time_years"].notna()].copy()
    fit = fit_spec(q, "target_points", "M2_SCALE_TIME", "QUANTILE_0.90")
    if fit.get("status") != "OK":
        return {"benchmark_task": target, "cohort": "CHAT_FINETUNED_OPEN_SENSITIVITY", "status": fit["status"], "n": len(q)}
    c = np.asarray(fit["coef"], dtype=float)
    return {
        "benchmark_task": target, "cohort": "CHAT_FINETUNED_OPEN_SENSITIVITY", "status": "DESCRIPTIVE_ONLY",
        "n": len(q), "model_spec": "M2_SCALE_TIME", "q90_b0": c[0], "q90_bC": c[1], "q90_bT": c[2],
        "date_min": q["score_date"].min().date().isoformat(), "date_max": q["score_date"].max().date().isoformat(),
        "used_to_override_main_frontier": False,
    }


def main() -> None:
    global CUTOFF, ORIGIN, SEAL_HASH, SCENARIO_HASH
    write_stage("direct_benchmark", "STARTED")
    seal = read_json(RUN_DIR / "forecast_seal.json")
    scenario_registry = pd.read_csv(RUN_DIR / "scenario_registry.csv", low_memory=False)
    SEAL_HASH = sha256_file(RUN_DIR / "forecast_seal.json")
    SCENARIO_HASH = sha256_file(RUN_DIR / "scenario_registry.csv")
    if SCENARIO_HASH != seal["scenario_registry_sha256"]:
        raise RuntimeError("scenario registry hash mismatch; stop before modeling")
    CUTOFF = pd.Timestamp(seal["time_cutoff"]).normalize()
    ORIGIN = pd.Timestamp(seal["forecast_origin_date"]).normalize()
    master, c8_task, _ = load_master()
    main_models = set(master.loc[master.main_eligible, "Model"])
    audit = pd.read_csv(RUN_DIR / "model_identity_and_dedup_audit.csv", low_memory=False)
    audit_main = set(audit.loc[audit.main_eligible.astype(bool), "Model"])
    if main_models != audit_main:
        raise RuntimeError("main sample differs from sealed pre-registration audit")
    if len(main_models) != 25:
        raise RuntimeError(f"sealed main sample count changed: {len(main_models)}")
    if pd.Timestamp(seal["forecast_origin_date"]) != ORIGIN:
        raise RuntimeError("forecast origin mismatch")

    task_frames = {t: task_frame(master, c8_task, pd.read_csv(C01_R1 / "c8_model_wide_corrected.csv", low_memory=False), t, CUTOFF) for t in ALL_TARGETS}
    metrics_df, selection_df, selection_info = build_candidate_outputs(task_frames)
    coeff_df, contrib_df, contrib_unc = build_contributions(task_frames, selection_info["selected"])
    forecast_df, parameter_unc, component_unc, support_df = build_forecasts(task_frames, selection_info, scenario_registry, seal)
    main_forecast = forecast_df[forecast_df.benchmark_task.isin(TASKS)].copy()
    aux_forecast = forecast_df[forecast_df.benchmark_task.eq(AUX_TARGET)].copy()
    write_csv(RUN_DIR / "candidate_model_metrics.csv", metrics_df)
    write_csv(RUN_DIR / "candidate_selection.csv", selection_df)
    write_csv(RUN_DIR / "taskwise_coefficients.csv", coeff_df)
    write_csv(RUN_DIR / "scale_non_scale_contributions.csv", contrib_df)
    write_csv(RUN_DIR / "contribution_uncertainty.csv", contrib_unc)
    write_csv(RUN_DIR / "forecast_12m_24m_taskwise.csv", main_forecast)
    write_csv(RUN_DIR / "forecast_auxiliary_composite.csv", aux_forecast)
    write_csv(RUN_DIR / "forecast_uncertainty_components.csv", pd.concat([parameter_unc, component_unc], ignore_index=True))
    write_csv(RUN_DIR / "support_oos_audit.csv", support_df)
    strat_rows = [stratified_sensitivity(master, c8_task, t) for t in TASKS]
    pd.DataFrame(strat_rows).to_csv(RUN_DIR / "stratified_sensitivity.csv", index=False, encoding="utf-8", lineterminator="\n")
    selection_compact = selection_info["selected"]
    scenario_compact = selection_info["scenario"]
    write_json(RUN_DIR / "model_selection_summary.json", {
        "run_id": RUN_ID, "sealed_origin": ORIGIN.date().isoformat(),
        "selected_contribution_models": selection_compact,
        "scenario_models": scenario_compact,
        "seal_sha256": SEAL_HASH, "scenario_registry_sha256": SCENARIO_HASH,
        "loss_bridge_used_for_selection": False,
    })
    write_stage(
        "direct_benchmark", "COMPLETED", n_main_models=len(main_models),
        selected_models=selection_compact, scenario_models=scenario_compact,
        forecast_rows=len(forecast_df), seal_sha256=SEAL_HASH,
    )


if __name__ == "__main__":
    main()
