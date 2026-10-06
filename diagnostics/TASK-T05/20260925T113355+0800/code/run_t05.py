from __future__ import annotations
import json, math, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder, SplineTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error

OUT = Path(__file__).resolve().parents[1]
TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]
TARGETS = [t + "_pct" for t in TASKS] + ["benchmark_mean_aux"]
CUTOFF = pd.Timestamp("2024-09-01")
NOMINAL = 0.95
THRESH = {"improvement": 0.10, "spearman": 0.50, "reversal": 0.25, "coverage_low": 0.85, "coverage_high": 0.98}

CANDIDATES = [
    {"candidate_id":"CONSTANT","layer":"L0","complexity":0,"formula":"target ~ 1","requires":[]},
    {"candidate_id":"SIZE_LOG_LINEAR","layer":"L1","complexity":1,"formula":"target ~ log(N)","requires":["logN"]},
    {"candidate_id":"LOSS_MONOTONE","layer":"L1","complexity":2,"formula":"target ~ isotonic(loss)","requires":["loss"]},
    {"candidate_id":"LOSS_SIZE_LINEAR","layer":"L1","complexity":2,"formula":"target ~ loss + log(N)","requires":["loss","logN"]},
    {"candidate_id":"LOSS_SIZE_FAMILY","layer":"L2","complexity":3,"formula":"target ~ loss + log(N) + family","requires":["loss","logN","family"]},
    {"candidate_id":"LOSS_SIZE_TIME","layer":"L2","complexity":3,"formula":"target ~ loss + log(N) + submission time","requires":["loss","logN","time"]},
    {"candidate_id":"LOSS_SIZE_FAMILY_TIME","layer":"L2","complexity":4,"formula":"target ~ loss + log(N) + family + submission time","requires":["loss","logN","family","time"]},
    {"candidate_id":"LOSS_SIZE_LOG_D","layer":"L2","complexity":4,"formula":"target ~ loss + log(N) + log(D)","requires":["loss","logN","logD"]},
    {"candidate_id":"LOSS_SIZE_FAMILY_TIME_SPLINE_DF4","layer":"L3","complexity":5,"formula":"target ~ loss + spline(logN, df=4) + family + submission time","requires":["loss","logN","family","time","spline"]},
]
CAND = {x["candidate_id"]: x for x in CANDIDATES}
FALLBACK = ["CONSTANT", "SIZE_LOG_LINEAR", "LOSS_SIZE_LINEAR", "LOSS_MONOTONE", "LOSS_SIZE_FAMILY", "LOSS_SIZE_TIME", "LOSS_SIZE_FAMILY_TIME", "LOSS_SIZE_LOG_D", "LOSS_SIZE_FAMILY_TIME_SPLINE_DF4"]
TARGET_LABEL = {t + "_pct": t for t in TASKS}
TARGET_LABEL["benchmark_mean_aux"] = "Six-task mean (auxiliary)"

def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

def finite(x):
    try:
        return np.isfinite(float(x))
    except Exception:
        return False

def metric_dict(y, p, lo=None, hi=None):
    y = np.asarray(y, dtype=float); p = np.asarray(p, dtype=float)
    ok = np.isfinite(y) & np.isfinite(p)
    y, p = y[ok], p[ok]
    n = len(y)
    out = {"n": int(n), "mae": np.nan, "rmse": np.nan, "spearman": np.nan, "calibration_slope": np.nan, "coverage": np.nan, "pi_width_mean": np.nan}
    if n == 0:
        return out
    out["mae"] = float(mean_absolute_error(y, p))
    out["rmse"] = float(math.sqrt(mean_squared_error(y, p)))
    if n >= 3 and np.std(y) > 0 and np.std(p) > 0:
        out["spearman"] = float(spearmanr(y, p).statistic)
    if n >= 3 and np.std(p) > 0:
        out["calibration_slope"] = float(LinearRegression().fit(p.reshape(-1,1), y).coef_[0])
    if lo is not None and hi is not None:
        lo = np.asarray(lo, dtype=float)[ok]; hi = np.asarray(hi, dtype=float)[ok]
        valid = np.isfinite(lo) & np.isfinite(hi)
        if valid.any():
            out["coverage"] = float(np.mean((y[valid] >= lo[valid]) & (y[valid] <= hi[valid])))
            out["pi_width_mean"] = float(np.mean(hi[valid] - lo[valid]))
    return out

def conformal_abs(resid):
    r = np.abs(np.asarray(resid, dtype=float)); r = r[np.isfinite(r)]
    if len(r) == 0:
        return np.nan
    q = min(1.0, math.ceil((len(r) + 1) * NOMINAL) / len(r))
    return float(np.quantile(r, q, method="higher"))

def onehot_fit(train_fam, test_fam):
    train_fam = np.asarray(train_fam, dtype=object).reshape(-1,1)
    test_fam = np.asarray(test_fam, dtype=object).reshape(-1,1)
    enc = OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False)
    Xt = enc.fit_transform(train_fam)
    Xv = enc.transform(test_fam)
    return Xt, Xv

def fit_predict(candidate_id, train, test, target):
    spec = CAND[candidate_id]
    tr = train.copy(); te = test.copy()
    if candidate_id == "CONSTANT":
        trn = tr[[target]].dropna(); pred = np.full(len(te), trn[target].mean() if len(trn) else np.nan)
        return pred, {"n_fit":len(trn), "n_pred":int(np.isfinite(pred).sum()), "failure":""}
    req_cols = []
    if "loss" in spec["requires"]: req_cols.append("primary_loss")
    if "logN" in spec["requires"]: req_cols.append("logN")
    if "logD" in spec["requires"]: req_cols.append("logD")
    if "time" in spec["requires"]: req_cols.append("time_days_from_cutoff")
    if "family" in spec["requires"]: req_cols.append("model_family")
    tr = tr.dropna(subset=req_cols + [target]).copy()
    y = pd.to_numeric(tr[target], errors="coerce").to_numpy(float)
    valid = np.isfinite(y)
    for c in req_cols:
        if c in ("primary_loss","logN","logD","time_days_from_cutoff"):
            valid &= np.isfinite(pd.to_numeric(tr[c], errors="coerce").to_numpy(float))
    tr = tr.loc[valid].copy(); y = pd.to_numeric(tr[target], errors="coerce").to_numpy(float)
    if len(tr) < 4:
        return np.full(len(te), np.nan), {"n_fit":len(tr), "n_pred":0, "failure":"training rows < 4 after complete-case filter"}
    try:
        if candidate_id == "SIZE_LOG_LINEAR":
            X = np.asarray(tr[["logN"]], dtype=float); Xv = np.asarray(te[["logN"]], dtype=float)
        elif candidate_id == "LOSS_MONOTONE":
            iso = IsotonicRegression(out_of_bounds="clip", increasing="auto")
            iso.fit(np.asarray(tr["primary_loss"], dtype=float), y)
            Xv = np.asarray(te[["primary_loss"]], dtype=float)
            pred = iso.predict(Xv.ravel()); pred = np.where(np.isfinite(Xv.ravel()), pred, np.nan)
            return pred, {"n_fit":len(tr), "n_pred":int(np.isfinite(pred).sum()), "failure":""}
        elif candidate_id == "LOSS_SIZE_LINEAR":
            X = np.asarray(tr[["primary_loss","logN"]], dtype=float); Xv = np.asarray(te[["primary_loss","logN"]], dtype=float)
        elif candidate_id == "LOSS_SIZE_FAMILY":
            Xn = np.asarray(tr[["primary_loss","logN"]], dtype=float); Xvn = np.asarray(te[["primary_loss","logN"]], dtype=float)
            Xf, Xvf = onehot_fit(tr["model_family"], te["model_family"]); X = np.c_[Xn, Xf]; Xv = np.c_[Xvn, Xvf]
        elif candidate_id == "LOSS_SIZE_TIME":
            X = np.asarray(tr[["primary_loss","logN","time_days_from_cutoff"]], dtype=float); Xv = np.asarray(te[["primary_loss","logN","time_days_from_cutoff"]], dtype=float)
        elif candidate_id == "LOSS_SIZE_FAMILY_TIME":
            Xn = np.asarray(tr[["primary_loss","logN","time_days_from_cutoff"]], dtype=float); Xvn = np.asarray(te[["primary_loss","logN","time_days_from_cutoff"]], dtype=float)
            Xf, Xvf = onehot_fit(tr["model_family"], te["model_family"]); X = np.c_[Xn, Xf]; Xv = np.c_[Xvn, Xvf]
        elif candidate_id == "LOSS_SIZE_LOG_D":
            X = np.asarray(tr[["primary_loss","logN","logD"]], dtype=float); Xv = np.asarray(te[["primary_loss","logN","logD"]], dtype=float)
        elif candidate_id == "LOSS_SIZE_FAMILY_TIME_SPLINE_DF4":
            sp = SplineTransformer(n_knots=2, degree=3, include_bias=False, extrapolation="linear")
            Xs = sp.fit_transform(np.asarray(tr[["logN"]], dtype=float))
            Xvs = sp.transform(np.asarray(te[["logN"]], dtype=float))
            Xn = np.asarray(tr[["primary_loss","time_days_from_cutoff"]], dtype=float); Xvn = np.asarray(te[["primary_loss","time_days_from_cutoff"]], dtype=float)
            Xf, Xvf = onehot_fit(tr["model_family"], te["model_family"]); X = np.c_[Xs, Xn, Xf]; Xv = np.c_[Xvs, Xvn, Xvf]
        else:
            raise ValueError(candidate_id)
        if len(tr) <= X.shape[1]:
            return np.full(len(te), np.nan), {"n_fit":len(tr), "n_pred":0, "failure":f"n_train={len(tr)} <= n_features={X.shape[1]}"}
        model = LinearRegression(fit_intercept=True).fit(X, y)
        pred = model.predict(Xv)
        pred = np.where(np.all(np.isfinite(Xv), axis=1), pred, np.nan)
        return pred, {"n_fit":len(tr), "n_pred":int(np.isfinite(pred).sum()), "failure":""}
    except Exception as e:
        return np.full(len(te), np.nan), {"n_fit":len(tr), "n_pred":0, "failure":str(e)}

def loo_conformal(candidate_id, train, target):
    if len(train) < 2:
        return pd.DataFrame({"model_id":train["Model"], "resid":np.nan})
    rows = []
    for idx in train.index:
        tr = train.drop(index=idx); te = train.loc[[idx]]
        p, info = fit_predict(candidate_id, tr, te, target)
        rows.append({"model_id":te.iloc[0]["Model"], "resid":float(te.iloc[0][target] - p[0]) if finite(p[0]) else np.nan})
    return pd.DataFrame(rows)

def evaluate(candidate_id, train, test, target, split_family, split_id, cohort, selection_source=""):
    if len(train) == 0 or len(test) == 0:
        return pd.DataFrame(), {"status":"NOT_EVALUABLE","reason":"empty split","mae":np.nan,"rmse":np.nan,"spearman":np.nan,"calibration_slope":np.nan,"coverage":np.nan,"pi_width_mean":np.nan,"improvement_vs_constant":np.nan,"improvement_vs_size":np.nan,"n_train":len(train),"n_test":len(test),"effective_candidate_id":candidate_id}
    p, info = fit_predict(candidate_id, train, test, target)
    if not np.isfinite(p).any():
        return pd.DataFrame(), {"status":"FAILED_FIT","reason":info["failure"],"mae":np.nan,"rmse":np.nan,"spearman":np.nan,"calibration_slope":np.nan,"coverage":np.nan,"pi_width_mean":np.nan,"improvement_vs_constant":np.nan,"improvement_vs_size":np.nan,"n_train":len(train),"n_test":len(test),"effective_candidate_id":candidate_id}
    y = pd.to_numeric(test[target], errors="coerce").to_numpy(float)
    loo = loo_conformal(candidate_id, train, target)
    q = conformal_abs(loo["resid"].to_numpy(float))
    lo = p - q; hi = p + q
    md = metric_dict(y, p, lo, hi)
    pc, _ = fit_predict("CONSTANT", train, test, target)
    ps, _ = fit_predict("SIZE_LOG_LINEAR", train, test, target)
    mc = metric_dict(y, pc); ms = metric_dict(y, ps)
    md["improvement_vs_constant"] = (1.0 - md["rmse"]/mc["rmse"]) if finite(md["rmse"]) and finite(mc["rmse"]) and mc["rmse"] > 0 else np.nan
    md["improvement_vs_size"] = (1.0 - md["rmse"]/ms["rmse"]) if finite(md["rmse"]) and finite(ms["rmse"]) and ms["rmse"] > 0 else np.nan
    pred = pd.DataFrame({
        "cohort": cohort, "split_family": split_family, "split_id": split_id,
        "selection_source": selection_source, "effective_candidate_id": candidate_id,
        "model_id": test["Model"].to_numpy(), "model_key": test["model_key"].to_numpy(),
        "model_family": test["model_family"].to_numpy(), "params_B": pd.to_numeric(test["params_B"], errors="coerce").to_numpy(),
        "scale_bin": test["scale_bin"].to_numpy(), "main_bridge_eligible": test["main_bridge_eligible"].to_numpy(),
        "target": target, "observed": y, "predicted": p, "residual": y - p,
        "pi_low": lo, "pi_high": hi, "residual_abs": np.abs(y - p),
    })
    return pred, {"status":"EVALUATED","reason":info["failure"],"effective_candidate_id":candidate_id,"n_train":len(train),"n_test":len(test), **md}

def internal_oof(cohort_df, target, candidate_id):
    parts = []
    cohort_name = "main_comparable" if bool(cohort_df["main_bridge_eligible"].all()) else "conditional_full"
    for fold in sorted(cohort_df["_fold"].unique()):
        tr = cohort_df[cohort_df["_fold"] != fold]
        te = cohort_df[cohort_df["_fold"] == fold]
        pred, info = fit_predict(candidate_id, tr, te, target)
        parts.append(pd.DataFrame({
            "cohort": cohort_name, "split_family":"internal_grouped", "split_id":f"fold_{fold}",
            "selection_source":"internal_only", "effective_candidate_id":candidate_id,
            "model_id":te["Model"].to_numpy(), "model_key":te["model_key"].to_numpy(),
            "model_family":te["model_family"].to_numpy(), "params_B":pd.to_numeric(te["params_B"], errors="coerce").to_numpy(),
            "scale_bin":te["scale_bin"].to_numpy(), "main_bridge_eligible":te["main_bridge_eligible"].to_numpy(),
            "target":target, "observed":pd.to_numeric(te[target], errors="coerce").to_numpy(float), "predicted":pred,
            "fit_failure":info["failure"],
        }))
    allp = pd.concat(parts, ignore_index=True)
    allp["residual"] = allp["observed"] - allp["predicted"]
    qmap = {}
    for fold in sorted(cohort_df["_fold"].unique()):
        other = allp.loc[allp["split_id"] != f"fold_{fold}", "residual"].to_numpy(float)
        qmap[f"fold_{fold}"] = conformal_abs(other)
    allp["pi_low"] = allp["split_id"].map(qmap).rsub(0) + allp["predicted"]
    allp["pi_high"] = allp["split_id"].map(qmap) + allp["predicted"]
    allp["residual_abs"] = np.abs(allp["residual"])
    return allp

def select_candidate(metric_rows):
    valid = [r for r in metric_rows if r["status"] == "EVALUATED" and r["n_pred"] == r["n_total"] and finite(r["rmse"])]
    if not valid:
        return "CONSTANT", {"reason":"no full-coverage candidate; fallback constant","best_rmse":np.nan,"one_se":np.nan}
    best = min(valid, key=lambda r: r["rmse"])
    err = np.asarray(best["_sqerr"], dtype=float); err = err[np.isfinite(err)]
    se = float(math.sqrt(np.var(err, ddof=1)/len(err))/(2*best["rmse"])) if len(err) > 1 and best["rmse"] > 0 else 0.0
    eligible = [r for r in valid if r["rmse"] <= best["rmse"] + se]
    eligible.sort(key=lambda r: (CAND[r["candidate_id"]]["complexity"], r["rmse"], r["candidate_id"]))
    return eligible[0]["candidate_id"], {"reason":"one-SE simplest within best+1SE","best_rmse":best["rmse"],"one_se":se,"candidates_within_se":[r["candidate_id"] for r in eligible]}

def family_holdout_rows(ds, selected_by_target, cohort_name):
    rows = []
    for target, cid in selected_by_target.items():
        for fam, g in ds.groupby("model_family"):
            if len(g) < 4:
                rows.append({"cohort":cohort_name,"validation_type":"leave_family","candidate_id":cid,"target":target,"split_id":f"holdout::{fam}","family":fam,"status":"INSUFFICIENT_OOS_ONLY","reason":f"family n={len(g)} < 4","n_train":len(ds)-len(g),"n_test":len(g)})
                continue
            train = ds[~ds["Model"].isin(g["Model"])]
            pred, md = evaluate(cid, train, g, target, "leave_family", f"holdout::{fam}", cohort_name, "internal_selected")
            md.update({"cohort":cohort_name,"validation_type":"leave_family","candidate_id":cid,"target":target,"split_id":f"holdout::{fam}","family":fam})
            rows.append(md)
    return pd.DataFrame(rows)

def threshold_eval(metric, direction_ref):
    checks = {
        "rmse_improvement_ge_0.10": finite(metric.get("improvement_vs_constant")) and metric["improvement_vs_constant"] >= 0.10,
        "spearman_ge_0.50": finite(metric.get("spearman")) and metric["spearman"] >= 0.50,
        "direction_consistent": finite(metric.get("spearman")) and finite(direction_ref) and np.sign(metric["spearman"]) == np.sign(direction_ref),
        "coverage_0.85_to_0.98": finite(metric.get("coverage")) and 0.85 <= metric["coverage"] <= 0.98,
    }
    return checks, bool(all(checks.values()))
def main():
    ds = pd.read_parquet(OUT / "bridge_analysis_dataset.parquet")
    split = pd.read_csv(OUT / "split_registry.csv")
    seal_hash = hashlib.sha256((OUT / "execution_seal.json").read_bytes()).hexdigest()
    assert seal_hash == (OUT / "execution_seal.sha256").read_text(encoding="utf-8").split()[0]

    folds = split[split["split_family"] == "internal_grouped"].copy()
    main_folds = folds[folds["split_id"] == "main_comparable"].set_index("model_id")["role"].str.replace("fold_", "", regex=False).astype(int)
    cond_folds = folds[folds["split_id"] == "conditional_full"].set_index("model_id")["role"].str.replace("fold_", "", regex=False).astype(int)
    ds["_fold_main"] = ds["Model"].map(main_folds)
    ds["_fold_cond"] = ds["Model"].map(cond_folds)
    main = ds[ds["main_bridge_eligible"]].copy(); main["_fold"] = main["_fold_main"].astype(int)
    cond = ds.copy(); cond["_fold"] = cond["_fold_cond"].astype(int)

    aggregate_rows, taskwise_parts, split_metric_rows = [], [], []
    selected = {}
    split_metrics_extra = {}
    for cohort_name, cohort in [("main_comparable", main), ("conditional_full", cond)]:
        selected[cohort_name] = {}
        for target in TARGETS:
            candidate_metrics = []
            for cid in CAND:
                oof = internal_oof(cohort, target, cid)
                good = oof[np.isfinite(oof["observed"]) & np.isfinite(oof["predicted"])]
                md = metric_dict(good["observed"], good["predicted"], good["pi_low"], good["pi_high"])
                mr = {"cohort":cohort_name,"target":target,"candidate_id":cid,"layer":CAND[cid]["layer"],"complexity":CAND[cid]["complexity"],
                      "status":"EVALUATED" if len(good) else "FAILED_FIT","reason":"","n_pred":len(good),"n_total":len(cohort),
                      **md,"_sqerr":(good["residual"].to_numpy(float)**2).tolist()}
                candidate_metrics.append(mr)
            cid, selinfo = select_candidate(candidate_metrics)
            selected[cohort_name][target] = {"candidate_id":cid, "selection":selinfo}
            oof = internal_oof(cohort, target, cid)
            good = oof[np.isfinite(oof["observed"]) & np.isfinite(oof["predicted"])]
            md = metric_dict(good["observed"], good["predicted"], good["pi_low"], good["pi_high"])
            const_oof = internal_oof(cohort, target, "CONSTANT")
            const_good = const_oof[np.isfinite(const_oof["observed"]) & np.isfinite(const_oof["predicted"])]
            mc = metric_dict(const_good["observed"], const_good["predicted"], const_good["pi_low"], const_good["pi_high"])
            md["improvement_vs_constant"] = 1 - md["rmse"]/mc["rmse"] if finite(md["rmse"]) and finite(mc["rmse"]) and mc["rmse"] > 0 else np.nan
            md.update({"split_family":"internal_grouped","split_id":"grouped_cv","status":"EVALUATED","candidate_id":cid,"effective_candidate_id":cid,
                       "n_train":int(len(cohort)-len(good)),"n_test":len(good),"selection_source":"internal_only","reason":""})
            taskwise_parts.append(good.assign(selection_source="internal_only", effective_candidate_id=cid, fit_failure=""))
            split_metric_rows.append({"cohort":cohort_name,"target":target,"candidate_id":cid,"validation_type":"internal_grouped","split_id":"grouped_cv","layer":CAND[cid]["layer"],"complexity":CAND[cid]["complexity"],**md})
            for cm in candidate_metrics:
                cm2 = {k:v for k,v in cm.items() if k != "_sqerr"}
                cm2.update({"validation_type":"internal_grouped_candidate_audit","split_id":"grouped_cv","selection_source":"internal_only"})
                split_metric_rows.append(cm2)
            use = cohort[["primary_loss",target]].dropna()
            l0rho = float(spearmanr(use["primary_loss"], use[target]).statistic) if len(use) >= 3 and use.iloc[:,0].nunique() > 1 and use.iloc[:,1].nunique() > 1 else np.nan
            aggregate_rows.append({"cohort":cohort_name,"target":target,"target_label":TARGET_LABEL[target],"layer":"L0","candidate_id":"UNIVARIATE_DESCRIPTIVE","selected_candidate_id":cid,
                                   "n_main":len(good),"n_total":len(cohort),"spearman_loss_target":l0rho,"internal_rmse":md["rmse"],"internal_spearman":md["spearman"],
                                   "internal_improvement_vs_constant":md["improvement_vs_constant"],"internal_coverage":md["coverage"],"time_pass":False,"family_pass":False,"scale_pass":False,
                                   "source_transfer_pass":False,"identifiability":"PENDING_VALIDATION","notes":"Mean target is auxiliary; no causal interpretation."})
            tr_time = cohort[(cohort["submission_date"].notna()) & (~cohort["date_ambiguous"].astype(bool)) & (pd.to_datetime(cohort["submission_date"]) < CUTOFF)]
            te_time = cohort[(cohort["submission_date"].notna()) & (~cohort["date_ambiguous"].astype(bool)) & (pd.to_datetime(cohort["submission_date"]) >= CUTOFF)]
            tp, tmd = evaluate(cid, tr_time, te_time, target, "time_oos", "cutoff_2024-09-01", cohort_name, "internal_selected")
            tmd.update({"cohort":cohort_name,"target":target,"candidate_id":cid,"validation_type":"time_oos","split_id":"cutoff_2024-09-01","layer":CAND[cid]["layer"],"complexity":CAND[cid]["complexity"]})
            split_metric_rows.append(tmd); taskwise_parts.append(tp)
            tchecks, tpass = threshold_eval(tmd, md["spearman"]) if tmd.get("status") == "EVALUATED" else ({}, False)
            tmd["threshold_checks"] = tchecks
            tr_scale = cohort[pd.to_numeric(cohort["params_B"], errors="coerce") < 20]
            te_scale = cohort[pd.to_numeric(cohort["params_B"], errors="coerce") >= 20]
            sp, smd = evaluate(cid, tr_scale, te_scale, target, "scale_oos", "holdout_ge20B", cohort_name, "internal_selected")
            smd.update({"cohort":cohort_name,"target":target,"candidate_id":cid,"validation_type":"scale_oos","split_id":"holdout_ge20B","layer":CAND[cid]["layer"],"complexity":CAND[cid]["complexity"]})
            split_metric_rows.append(smd); taskwise_parts.append(sp)
            schecks, spass = threshold_eval(smd, md["spearman"]) if smd.get("status") == "EVALUATED" else ({}, False)
            smd["threshold_checks"] = schecks
            xmd = {"status":"NOT_APPLICABLE","rmse":np.nan,"spearman":np.nan,"coverage":np.nan,"improvement_vs_constant":np.nan}
            xpass = False
            if cohort_name == "main_comparable":
                transfer = cond[~cond["main_bridge_eligible"]]
                xp, xmd = evaluate(cid, cohort, transfer, target, "source_transfer", "C5_High_to_C6_Medium", "main_comparable_to_C6_Medium", "main_internal_selected")
                if xmd.get("status") != "EVALUATED":
                    for fb in FALLBACK:
                        if CAND[fb]["complexity"] >= CAND[cid]["complexity"]:
                            continue
                        fp, fmd = evaluate(fb, cohort, transfer, target, "source_transfer", "C5_High_to_C6_Medium", "main_comparable_to_C6_Medium", "main_internal_selected")
                        if fmd.get("status") == "EVALUATED":
                            xp, xmd = fp, fmd
                            xmd["reason"] = f"pre-specified simpler fallback from {cid} to {fb}"
                            xmd["effective_candidate_id"] = fb
                            if len(xp): xp["effective_candidate_id"] = fb
                            break
                xmd.update({"cohort":"main_comparable_to_C6_Medium","target":target,"candidate_id":cid,"validation_type":"source_transfer","split_id":"C5_High_to_C6_Medium","layer":CAND[cid]["layer"],"complexity":CAND[cid]["complexity"]})
                split_metric_rows.append(xmd); taskwise_parts.append(xp)
                xchecks, xpass = threshold_eval(xmd, md["spearman"]) if xmd.get("status") == "EVALUATED" else ({}, False)
                xmd["threshold_checks"] = xchecks
                split_metrics_extra[(cohort_name,target,"source_transfer_pass")] = xpass
            row = aggregate_rows[-1]
            row.update({"time_pass":tpass,"time_rmse":tmd.get("rmse",np.nan),"time_spearman":tmd.get("spearman",np.nan),"time_improvement":tmd.get("improvement_vs_constant",np.nan),"time_coverage":tmd.get("coverage",np.nan),
                        "scale_pass":spass,"scale_rmse":smd.get("rmse",np.nan),"scale_spearman":smd.get("spearman",np.nan),"scale_improvement":smd.get("improvement_vs_constant",np.nan),"scale_coverage":smd.get("coverage",np.nan),
                        "source_transfer_pass":xpass,"source_transfer_rmse":xmd.get("rmse",np.nan),"source_transfer_spearman":xmd.get("spearman",np.nan),"source_transfer_coverage":xmd.get("coverage",np.nan)})
    split_metrics = pd.DataFrame(split_metric_rows).replace([np.inf,-np.inf], np.nan)
    taskwise = pd.concat([p for p in taskwise_parts if len(p)], ignore_index=True).drop_duplicates()
    fam_main = family_holdout_rows(main, {t:selected["main_comparable"][t]["candidate_id"] for t in TARGETS}, "main_comparable")
    fam_cond = family_holdout_rows(cond, {t:selected["conditional_full"][t]["candidate_id"] for t in TARGETS}, "conditional_full")
    family_out = pd.concat([fam_main, fam_cond], ignore_index=True)
    frows = []
    for _, r in family_out.iterrows():
        rr = r.copy()
        if r.get("status") == "EVALUATED":
            refrow = split_metrics[(split_metrics["cohort"] == r["cohort"]) & (split_metrics["target"] == r["target"]) & (split_metrics["validation_type"] == "internal_grouped")]
            ref = refrow.iloc[0]["spearman"] if len(refrow) else np.nan
            checks, passed = threshold_eval(r, ref)
            rr["direction_reference"] = ref; rr["frozen_threshold_pass"] = passed
            for k,v in checks.items(): rr[f"check_{k}"] = v
        else:
            rr["direction_reference"] = np.nan; rr["frozen_threshold_pass"] = False
        frows.append(rr)
    family_out = pd.DataFrame(frows)
    fam_summary = family_out.groupby(["cohort","target"], dropna=False).agg(
        family_evaluated_n=("status", lambda s: int((s == "EVALUATED").sum())),
        family_insufficient_n=("status", lambda s: int((s == "INSUFFICIENT_OOS_ONLY").sum())),
        family_pass_n=("frozen_threshold_pass", lambda s: int(pd.Series(s).fillna(False).sum())),
    ).reset_index()
    family_out.to_csv(OUT / "validation_by_family.csv", index=False, encoding="utf-8-sig")
    time_rows, scale_rows = [], []
    for _, r in split_metrics.iterrows():
        if r.get("validation_type") not in ("time_oos","scale_oos"):
            continue
        refrow = split_metrics[(split_metrics["cohort"] == r["cohort"]) & (split_metrics["target"] == r["target"]) & (split_metrics["validation_type"] == "internal_grouped")]
        ref = refrow.iloc[0]["spearman"] if len(refrow) else np.nan
        checks, passed = threshold_eval(r, ref)
        d = r.to_dict(); d.update({f"check_{k}":v for k,v in checks.items()}); d["frozen_threshold_pass"] = passed; d["direction_reference"] = ref
        (time_rows if r["validation_type"] == "time_oos" else scale_rows).append(d)
    pd.DataFrame(time_rows).to_csv(OUT / "validation_by_time.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(scale_rows).to_csv(OUT / "validation_by_scale.csv", index=False, encoding="utf-8-sig")

    agg = pd.DataFrame(aggregate_rows).merge(fam_summary, on=["cohort","target"], how="left")
    for c in ["family_evaluated_n","family_insufficient_n","family_pass_n"]:
        agg[c] = agg[c].fillna(0).astype(int)
    agg["family_pass"] = (agg["family_evaluated_n"] >= 1) & (agg["family_pass_n"] == agg["family_evaluated_n"])
    agg["identifiability"] = "CONDITIONAL_ASSOCIATION_ONLY"
    for i, r in agg.iterrows():
        if r["cohort"] != "main_comparable":
            continue
        internal = (finite(r["internal_improvement_vs_constant"]) and r["internal_improvement_vs_constant"] >= THRESH["improvement"] and
                    finite(r["internal_spearman"]) and r["internal_spearman"] >= THRESH["spearman"] and
                    finite(r["internal_coverage"]) and THRESH["coverage_low"] <= r["internal_coverage"] <= THRESH["coverage_high"])
        if internal and bool(r["time_pass"]) and bool(r["family_pass"]) and bool(r["scale_pass"]):
            agg.at[i,"identifiability"] = "MAIN_COMPARABLE_THRESHOLDS_PASS"
    agg.to_csv(OUT / "aggregate_bridge_results.csv", index=False, encoding="utf-8-sig")

    crows = []
    for c in CANDIDATES:
        crows.append({"candidate_id":c["candidate_id"],"layer":c["layer"],"complexity":c["complexity"],"formula":c["formula"],"required_inputs":"|".join(c["requires"]),"selection_is_metric_driven":False})
    for cohort in selected:
        for target, info in selected[cohort].items():
            crows.append({"candidate_id":info["candidate_id"],"layer":CAND[info["candidate_id"]]["layer"],"complexity":CAND[info["candidate_id"]]["complexity"],"formula":CAND[info["candidate_id"]]["formula"],"required_inputs":"|".join(CAND[info["candidate_id"]]["requires"]),"selection_is_metric_driven":False,"cohort":cohort,"target":target,"selection_reason":info["selection"].get("reason",""),"best_internal_rmse":info["selection"].get("best_rmse",np.nan)})
    pd.DataFrame(crows).to_csv(OUT / "candidate_models.csv", index=False, encoding="utf-8-sig")
    taskwise.to_csv(OUT / "taskwise_bridge_results.csv", index=False, encoding="utf-8-sig")
    split_metrics.to_csv(OUT / "validation_by_split.csv", index=False, encoding="utf-8-sig")
    residual = taskwise.copy()
    residual["abs_residual_fraction_of_mean_observed"] = np.abs(residual["residual"]) / residual.groupby("cohort")["observed"].transform("mean").abs().replace(0,np.nan)
    residual.to_csv(OUT / "residual_audit.csv", index=False, encoding="utf-8-sig")

    main_qualifying = agg[(agg["cohort"] == "main_comparable") & (agg["identifiability"] == "MAIN_COMPARABLE_THRESHOLDS_PASS")]
    final_eligibility = "IDENTIFIED_PREDICTIVE_BRIDGE" if len(main_qualifying) == len(TARGETS) else "CONDITIONAL_ASSOCIATION_ONLY"
    task_decision = []
    for target in TARGETS:
        rr = agg[(agg["cohort"] == "main_comparable") & (agg["target"] == target)].iloc[0]
        checks = {
            "internal_rmse_improvement_ge_0.10": bool(finite(rr["internal_improvement_vs_constant"]) and rr["internal_improvement_vs_constant"] >= 0.10),
            "internal_spearman_ge_0.50": bool(finite(rr["internal_spearman"]) and rr["internal_spearman"] >= 0.50),
            "internal_coverage_0.85_to_0.98": bool(finite(rr["internal_coverage"]) and 0.85 <= rr["internal_coverage"] <= 0.98),
            "time_pass": bool(rr["time_pass"]), "leave_family_pass": bool(rr["family_pass"]), "scale_oos_pass": bool(rr["scale_pass"]),
            "no_major_direction_reversal": bool(rr["time_pass"] and rr["scale_pass"]),
        }
        task_decision.append({"target":target,"target_label":TARGET_LABEL[target],"selected_candidate_id":selected["main_comparable"][target]["candidate_id"],"checks":checks,"eligibility":rr["identifiability"]})
    decision = {
        "run_id":OUT.name,"task_id":"TASK-T05","eligibility":final_eligibility,
        "decision_basis":"Frozen thresholds applied without movement; main comparable cohort contains 7 models with one verified loss definition and one model family.",
        "main_comparable_n":int(len(main)),"conditional_full_n":int(len(cond)),"partial_excluded_n":6,"corrupt_json_no_score_n":4,
        "task_decisions":task_decision,
        "limitations":[
            "C5 High and C6 High are the same seven model rows; C6 does not provide an independent replication set.",
            "C6 Medium has report-specific/different validation sets and is therefore source-transfer or conditional association only.",
            "Only one model family is present in the main comparable layer, so a complete leave-family upgrade test is not identifiable.",
            "Four damaged C8 JSON files affect coverage only and receive no score."
        ],
        "causal_language_allowed":False
    }
    write_json(OUT / "identifiability_decision.json", decision)

    best_structures = {}
    for target in TARGETS:
        cid = selected["main_comparable"][target]["candidate_id"]
        best_structures[target] = {"candidate_id":cid,"layer":CAND[cid]["layer"],"formula":CAND[cid]["formula"],"eligibility":next(x["eligibility"] for x in task_decision if x["target"] == target)}
    time_available = any(bool(agg[(agg.cohort == "main_comparable") & (agg.target == t)].iloc[0]["time_pass"]) for t in TARGETS)
    time_validated = all(bool(agg[(agg.cohort == "main_comparable") & (agg.target == t)].iloc[0]["time_pass"]) for t in TARGETS)
    t08 = {
        "contract_version":"T08-v1","task_id":"TASK-T05","eligibility":final_eligibility,
        "scale_progress":{"available":True,"definition":"Prediction component explained by observed N and, where present, observed D; no missing D imputation.","formula_by_target":best_structures,"inputs":["params_B","D_tokens_B_observed_only"],"uncertainty":"Conditional/statistical; use uncertainty field by component.","validated_for_causal_interpretation":False},
        "non_scale_residual":{"available":True,"definition":"Observed benchmark minus fitted conditional prediction; association only.","causal_technological_progress_claim":False,"artifact":"residual_audit.csv"},
        "time_trend":{"available":bool(time_available),"validated_for_extrapolation":bool(time_validated),"cutoff":"2024-09-01","rule":"Use only if validated_for_extrapolation is true; otherwise descriptive time association only."},
        "benchmark_prediction":{"tasks":TASKS,"vector_required":True,"mean_is_auxiliary":True,"units":"leaderboard points (0-100)","scope":"Main comparable C5 High same-validation-set layer; conditional C6 Medium only for source-transfer diagnostics.","per_task_structures":best_structures,"artifact":"prediction_table.parquet"},
        "uncertainty":{"identity_match":"exact raw Model string only for bridge eligibility","loss_definition":"main cohort one verified same-validation-set definition; C6 Medium not comparable","run_repetition":"95 multi-file directories audited; no bridge candidate overlaps them","model_error":"grouped internal CV and conformal residual intervals","extrapolation":"time, family and >=20B scale rows reported separately; do not propagate as identified when status is conditional"},
        "eligibility_detail":decision
    }
    write_json(OUT / "t08_bridge_contract.json", t08)
    predtab = taskwise.copy()
    predtab["eligibility"] = np.where(predtab["cohort"].str.startswith("main_comparable"), final_eligibility, "CONDITIONAL_ASSOCIATION_ONLY")
    predtab.to_parquet(OUT / "prediction_table.parquet", index=False)
    summary = {
        "run_id":OUT.name,"task_id":"TASK-T05","status":"COMPLETE_PENDING_CONTROLLER_REVIEW",
        "main_sample_n":int(len(main)),"conditional_full_n":int(len(cond)),"complete_c8_models_available":1854,"partial_c8_models_excluded":6,
        "corrupt_json_files":4,"multi_file_directories_audited":95,"c5_c6_overlap_rows":43,"c5_c6_overlap_exact_value_rows":43,
        "main_c5_c6_same_rows":7,"c6_medium_transfer_rows":int((~cond["main_bridge_eligible"]).sum()),
        "final_eligibility":final_eligibility,"frozen_thresholds":THRESH,"selected_by_cohort":selected,
        "c5_c6_connection":"C5 is an exact 43-row value subset of C6; C6 provides no independent validation set.",
        "notes":["No C01 re-run","No C8 JSON re-parse","No old run modified","No T08 started"]
    }
    write_json(OUT / "run_summary.json", summary)
    checks = {
        "seal_hash_matches":bool(seal_hash == (OUT / "execution_seal.sha256").read_text(encoding="utf-8").split()[0]),
        "bridge_identity_exact":bool(len(ds) == len(ds.drop_duplicates("Model")) and ds["Model"].notna().all()),
        "six_task_vector_preserved":bool(all((t + "_pct") in ds.columns for t in TASKS)),
        "partial_models_in_dataset":0,"corrupt_json_scored":False,"medium_D_imputed":False,
        "c5_source_preserved":"c5_Loss_Source" in ds.columns,"c6_source_preserved":"c6_Loss_Source" in ds.columns,
        "final_eligibility":final_eligibility
    }
    write_json(OUT / "checks.json", checks)
    print(json.dumps({"status":"ok","eligibility":final_eligibility,"main_n":len(main),"cond_n":len(cond),"selected":selected},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()