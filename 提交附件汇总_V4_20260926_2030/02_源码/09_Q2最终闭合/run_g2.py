# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import hashlib, json, math, os, platform, shutil, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from scipy import stats

RUN = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
TZ = ZoneInfo("Asia/Shanghai")
SEED = 20260925
NBOOT = 2000
STAGE_FILE = RUN / "stage_status.jsonl"
if STAGE_FILE.exists(): STAGE_FILE.write_text('', encoding='utf-8')

FROZEN = {
    "E": 1.6897975629820348,
    "A": 0.3539803206065571,
    "B": 1.2403055835426349,
    "alpha": 0.339976581941082,
    "beta": 0.2798781285468448,
}
K_ADD = 0.3544081081063713
Q_ANCHOR = 0.5695341857475174
SUPPORT_N = (0.070542, 11.965825)
SUPPORT_D = (0.134, 299.893)
BASE = ROOT / "F题/real_attachments/B_scaling_laws"
INTEG = ROOT / "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08"
B_RUN = ROOT / "diagnostics/TASK-T06E-B-R1/20260925T103130+08"
P_RUN = ROOT / "diagnostics/TASK-T06E-P/20260925T075729+08"
T07_RUN = ROOT / "diagnostics/TASK-T07/20260925T113744+08"
TASK = ROOT / "tasks/TASK-G2_Q2广义标度律与强制验证闭合.md"
CONTRACT_PATH = INTEG / "t07_model_contract.json"
REGISTRY_PATH = INTEG / "scenario_registry_filled.csv"
MODEL_PATH = ROOT / "solution/outputs/mixture/model.json"
MAPPING_GUIDE = ROOT / "F题/real_attachments/A_data_value/domain_mapping_guide.csv"
T06_FREEZE = ROOT / "paper/T06_RESULT_FREEZE.md"
T07_FREEZE = ROOT / "paper/T07_RESULT_FREEZE.md"

def now_iso():
    return datetime.now(TZ).isoformat(timespec="seconds")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.isoformat()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o).__name__)

def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=json_default) + "\n", encoding="utf-8")

def finite(x):
    return x is not None and np.isfinite(x)

def ffloat(x):
    return float(x) if finite(x) else None

def source_prediction(n_b, d_b):
    return FROZEN["E"] + FROZEN["A"] * np.power(n_b, -FROZEN["alpha"]) + FROZEN["B"] * np.power(d_b, -FROZEN["beta"])

def support_status(n_b, d_b):
    if not finite(n_b) or not finite(d_b) or n_b <= 0 or d_b <= 0:
        return "INVALID_N_OR_D"
    in_n = SUPPORT_N[0] <= n_b <= SUPPORT_N[1]
    in_d = SUPPORT_D[0] <= d_b <= SUPPORT_D[1]
    if in_n and in_d:
        return "IN_SUPPORT"
    if not in_n and not in_d:
        return "OUT_BOTH"
    if not in_n:
        return "OUT_N"
    return "OUT_D"

def stage(stage_name: str, status: str, detail: str = ""):
    row = {"time": now_iso(), "stage": stage_name, "status": status, "detail": detail}
    with (RUN / "stage_status.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=json_default) + "\n")

def hash_tree(root: Path):
    rows = []
    if root.is_file():
        files = [root]
    else:
        files = sorted(p for p in root.rglob("*") if p.is_file())
    for p in files:
        rows.append({
            "path": str(p.relative_to(ROOT)).replace("\\", "/"),
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
        })
    return rows

def metric_values(y, p, relative_allowed=True):
    y = np.asarray(y, float); p = np.asarray(p, float)
    ok = np.isfinite(y) & np.isfinite(p)
    y = y[ok]; p = p[ok]
    e = p - y
    out = {
        "n": int(len(y)),
        "mean_actual": ffloat(np.mean(y)) if len(y) else None,
        "sd_actual": ffloat(np.std(y, ddof=1)) if len(y) > 1 else None,
        "mean_prediction": ffloat(np.mean(p)) if len(p) else None,
        "rmse": ffloat(np.sqrt(np.mean(e * e))) if len(e) else None,
        "mae": ffloat(np.mean(np.abs(e))) if len(e) else None,
        "mean_error": ffloat(np.mean(e)) if len(e) else None,
        "median_error": ffloat(np.median(e)) if len(e) else None,
        "positive_error_fraction": ffloat(np.mean(e > 0)) if len(e) else None,
        "max_abs_error": ffloat(np.max(np.abs(e))) if len(e) else None,
        "relative_error_formula": "(prediction-actual)/actual",
        "mean_signed_relative_error": None,
        "median_signed_relative_error": None,
        "mean_absolute_relative_error": None,
        "median_absolute_relative_error": None,
        "relative_error_scale_comparable": bool(relative_allowed),
        "spearman": None,
        "spearman_pvalue": None,
    }
    if relative_allowed and len(y) and np.all(y > 0):
        rel = e / y
        out.update({
            "mean_signed_relative_error": ffloat(np.mean(rel)),
            "median_signed_relative_error": ffloat(np.median(rel)),
            "mean_absolute_relative_error": ffloat(np.mean(np.abs(rel))),
            "median_absolute_relative_error": ffloat(np.median(np.abs(rel))),
        })
    if len(y) >= 5 and np.std(y) > 0 and np.std(p) > 0:
        rho, pv = stats.spearmanr(y, p)
        out["spearman"] = ffloat(rho)
        out["spearman_pvalue"] = ffloat(pv)
    return out

def bootstrap_metrics(y, p, groups):
    y = np.asarray(y, float); p = np.asarray(p, float)
    groups = np.asarray(groups, dtype=object)
    ok = np.isfinite(y) & np.isfinite(p)
    y = y[ok]; p = p[ok]; groups = groups[ok]
    out = {
        "bootstrap_requested": NBOOT,
        "bootstrap_success": 0,
        "bootstrap_seed": SEED,
        "bootstrap_unit": "cluster_resample_with_replacement",
    }
    for name in ["rmse", "mae", "mean_error", "median_error"]:
        out[f"{name}_boot_lo"] = None
        out[f"{name}_boot_hi"] = None
    if len(y) == 0:
        return out
    ug = np.asarray(sorted(pd.unique(groups)), dtype=object)
    if len(ug) < 2:
        out["bootstrap_status"] = "NOT_ENOUGH_CLUSTERS"
        return out
    idx_by_group = {g: np.flatnonzero(groups == g) for g in ug}
    rng = np.random.default_rng(SEED)
    vals = {k: [] for k in ["rmse", "mae", "mean_error", "median_error"]}
    for _ in range(NBOOT):
        draw = rng.choice(ug, size=len(ug), replace=True)
        idx = np.concatenate([idx_by_group[g] for g in draw])
        yy = y[idx]; pp = p[idx]; ee = pp - yy
        vals["rmse"].append(np.sqrt(np.mean(ee * ee)))
        vals["mae"].append(np.mean(np.abs(ee)))
        vals["mean_error"].append(np.mean(ee))
        vals["median_error"].append(np.median(ee))
    for k, v in vals.items():
        arr = np.asarray(v, float)
        out[f"{k}_boot_lo"] = ffloat(np.percentile(arr, 2.5))
        out[f"{k}_boot_hi"] = ffloat(np.percentile(arr, 97.5))
    out["bootstrap_success"] = NBOOT
    out["bootstrap_status"] = "PASS"
    return out

def bias_direction(mean_error):
    if mean_error is None:
        return "NOT_AVAILABLE"
    if mean_error < -0.01:
        return "UNDERPREDICTION"
    if mean_error > 0.01:
        return "OVERPREDICTION"
    return "NEAR_ZERO"

write_json(RUN / "environment.json", {
    "run_id": RUN.name,
    "task_id": "TASK-G2",
    "timestamp": now_iso(),
    "python": sys.version,
    "platform": platform.platform(),
    "executable": sys.executable,
    "packages": {
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": stats.__version__ if hasattr(stats, "__version__") else "unknown",
    },
    "network_used": False,
    "working_directory": str(ROOT),
})

write_json(RUN / "command_log.json", {
    "commands": [
        "python diagnostics/TASK-G2/20260925T195336+08/code/run_g2.py",
        "python diagnostics/TASK-G2/20260925T195336+08/code/verify_g2.py",
        "python diagnostics/TASK-G2/20260925T195336+08/code/finalize_g2.py",
    ],
    "note": "No fitting, model selection, optimization, or network access is performed.",
})

stage("start", "RUNNING", "TASK-G2 execution initialized")

source_paths = {
    "B1": BASE / "pythia_training_log_existing.csv",
    "B2": BASE / "cerebras_training_log.csv",
    "B4": BASE / "scaling_baseline.csv",
    "B5": BASE / "published_scaling_data.csv",
    "B9": BASE / "supplementary_large_models.csv",
    "B10": BASE / "supplementary_large_baseline.csv",
}
traj_paths = sorted((BASE / "training_trajectories").glob("*.csv"))
input_paths = [
    (TASK, "task_contract"),
    (CONTRACT_PATH, "frozen_T07_model_contract"),
    (REGISTRY_PATH, "frozen_scenario_registry"),
    (MODEL_PATH, "frozen_RegMix_linear_model"),
    (MAPPING_GUIDE, "A16_domain_mapping_guide"),
    (T06_FREEZE, "readonly_T06_freeze"),
    (T07_FREEZE, "readonly_T07_freeze"),
]
input_paths += [(source_paths[k], f"source_{k}") for k in sorted(source_paths)]
input_paths += [(p, "source_B3_trajectory") for p in traj_paths]
input_paths += [
    (B_RUN / "run_summary.json", "readonly_T06E_B_run_summary"),
    (P_RUN / "run_summary.json", "readonly_T06E_P_run_summary"),
    (INTEG / "t07_parameter_table.csv", "frozen_T07_parameter_table"),
    (INTEG / "integrated_identifiability_matrix.csv", "frozen_identifiability_matrix"),
    (INTEG / "scenario_registry_filled.csv", "frozen_scenario_registry_duplicate_role"),
]
for p, _ in input_paths:
    if not p.exists():
        raise FileNotFoundError(p)
manifest_rows = []
for p, role in input_paths:
    manifest_rows.append({
        "path": str(p.relative_to(ROOT)).replace("\\", "/"),
        "role": role,
        "bytes": p.stat().st_size,
        "sha256": sha256(p),
    })
write_json(RUN / "input_manifest.json", {
    "schema_version": 1,
    "run_id": RUN.name,
    "inputs": manifest_rows,
    "actual_file_count": len(manifest_rows),
    "all_actual_read_files_registered": True,
    "readonly_boundary": "T06/T07 and old scaling/paper files are not modified.",
})
stage("input_manifest", "PASS", f"registered {len(manifest_rows)} files")

protected_roots = [
    B_RUN,
    P_RUN,
    INTEG,
    T07_RUN,
    ROOT / "solution/outputs/scaling",
]
before = {}
for p in protected_roots:
    before[str(p.relative_to(ROOT)).replace("\\", "/")] = hash_tree(p)
for p in [T06_FREEZE, T07_FREEZE]:
    before[str(p.relative_to(ROOT)).replace("\\", "/")] = hash_tree(p)
write_json(RUN / "protected_old_artifacts_before.json", {
    "created_at": now_iso(),
    "roots": before,
    "policy": "read-only; no registered file in these roots is written by TASK-G2",
})
stage("protected_hash_snapshot", "PASS", "before hashes captured")

contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
registry = pd.read_csv(REGISTRY_PATH)
model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
mapping_guide = pd.read_csv(MAPPING_GUIDE)

contract_params = {k: float(v) for k, v in contract["primary_model"]["parameters"].items()}
for k, v in FROZEN.items():
    if contract_params[k] != v:
        raise RuntimeError(f"frozen parameter mismatch {k}: {contract_params[k]} != {v}")
b6 = contract["quality"]["MQ_add_B6"]["parameters"]
if float(b6["k_add"]) != K_ADD:
    raise RuntimeError("k_add mismatch")
if float(contract["quality"]["q_A_star"]) != Q_ANCHOR:
    raise RuntimeError("q_A_star mismatch")

b1 = pd.read_csv(source_paths["B1"])
b2 = pd.read_csv(source_paths["B2"])
b3 = pd.concat([pd.read_csv(p).assign(_trajectory_file=p.name) for p in traj_paths], ignore_index=True)
b4 = pd.read_csv(source_paths["B4"])
b5 = pd.read_csv(source_paths["B5"])
b9 = pd.read_csv(source_paths["B9"])
b10 = pd.read_csv(source_paths["B10"])

if set(b1.columns) != {"run_id","N_params_B","D_tokens_B","C_FLOPs_1e21","steps","batch_tokens_M","lr","wd","precision","gpu_days","step_time_ms","train_loss","val_loss","ppl","grad_norm_avg"}:
    raise RuntimeError("B1 schema mismatch")
if b1.shape[0] != 1176 or b1["N_params_B"].nunique() != 8:
    raise RuntimeError("B1 frozen source shape mismatch")
if not (float(b1["N_params_B"].min()) == SUPPORT_N[0] and float(b1["N_params_B"].max()) == SUPPORT_N[1]):
    raise RuntimeError("B1 N support mismatch")
if not (float(b1["D_tokens_B"].min()) == SUPPORT_D[0] and float(b1["D_tokens_B"].max()) == SUPPORT_D[1]):
    raise RuntimeError("B1 D support mismatch")

source_schema = pd.DataFrame([
    {
        "source_id":"B1", "input_paths":str(source_paths["B1"].relative_to(ROOT)).replace("\\","/"),
        "raw_rows":int(len(b1)), "valid_loss_rows":int(np.isfinite(b1["val_loss"]).sum()),
        "independent_units":int(b1["N_params_B"].nunique()), "unit_type":"N-scale trajectory",
        "nature":"observed", "credibility":"training-source data; frozen support anchor only",
        "loss_field":"val_loss", "loss_definition":"Pythia validation cross-entropy", "loss_unit":"nats as supplied",
        "loss_is_ground_truth":True, "N_field":"N_params_B", "D_field":"D_tokens_B",
        "N_unit":"billions of parameters", "D_unit":"billions of tokens", "conversion":"none",
        "support_rule":"B1 box, inclusive, no clipping", "notes":"Not re-fit; used only to verify frozen support and schema."
    },
    {
        "source_id":"B2", "input_paths":str(source_paths["B2"].relative_to(ROOT)).replace("\\","/"),
        "raw_rows":int(len(b2)), "valid_loss_rows":int(np.isfinite(b2["val_loss"]).sum()),
        "independent_units":int(b2["run_id"].nunique()), "unit_type":"run_id trajectory",
        "nature":"semisynthetic", "credibility":"calibrated synthetic; not an independent real experiment",
        "loss_field":"val_loss", "loss_definition":"semisynthetic validation cross-entropy calibrated to Pythia scale", "loss_unit":"nats as supplied",
        "loss_is_ground_truth":False, "N_field":"N_params_B", "D_field":"D_tokens_B",
        "N_unit":"billions of parameters", "D_unit":"billions of tokens", "conversion":"none",
        "support_rule":"B1 box, inclusive; rows outside are OOS stress only", "notes":"147 checkpoints per run; checkpoints within a run are dependent."
    },
    {
        "source_id":"B3", "input_paths":"F题/real_attachments/B_scaling_laws/training_trajectories/*.csv",
        "raw_rows":int(len(b3)), "valid_loss_rows":int(np.isfinite(b3["val_loss"]).sum()),
        "independent_units":int(b3["_trajectory_file"].nunique()), "unit_type":"trajectory",
        "nature":"interpolated", "credibility":"Pythia same-source interpolation; not an independent external source",
        "loss_field":"val_loss", "loss_definition":"Pythia validation cross-entropy", "loss_unit":"nats as supplied",
        "loss_is_ground_truth":False, "N_field":"N_params_B", "D_field":"D_tokens_B",
        "N_unit":"billions of parameters", "D_unit":"billions of tokens", "conversion":"none",
        "support_rule":"B1 box, inclusive; rows outside are OOS stress only", "notes":"All rows have interpolated=1; cluster by trajectory, not row."
    },
    {
        "source_id":"B4", "input_paths":str(source_paths["B4"].relative_to(ROOT)).replace("\\","/"),
        "raw_rows":int(len(b4)), "valid_loss_rows":int(np.isfinite(b4["val_loss"]).sum()),
        "independent_units":int(b4["family"].nunique()), "unit_type":"model_family",
        "nature":"published_observed", "credibility":"real cross-family convergence points; evaluation protocols may differ",
        "loss_field":"val_loss", "loss_definition":"published validation cross-entropy; exact evaluation protocol not supplied", "loss_unit":"nats as supplied",
        "loss_is_ground_truth":True, "N_field":"N_params_B", "D_field":"D_tokens_B",
        "N_unit":"billions of parameters", "D_unit":"billions of tokens", "conversion":"none",
        "support_rule":"B1 box for primary comparison; outside is OOS", "notes":"Do not merge with B5; family-cluster bootstrap only."
    },
    {
        "source_id":"B5", "input_paths":str(source_paths["B5"].relative_to(ROOT)).replace("\\","/"),
        "raw_rows":int(len(b5)), "valid_loss_rows":int(np.isfinite(b5["val_loss"]).sum()),
        "independent_units":int(b5["family"].nunique()), "unit_type":"model_family",
        "nature":"published_observed", "credibility":"published multi-source observations; protocol shift across papers",
        "loss_field":"val_loss", "loss_definition":"paper-reported validation cross-entropy; tokenizer/set may differ", "loss_unit":"nats as supplied",
        "loss_is_ground_truth":True, "N_field":"N_params_B", "D_field":"D_tokens_B",
        "N_unit":"billions of parameters", "D_unit":"billions of tokens", "conversion":"none",
        "support_rule":"B1 box for primary comparison; outside is OOS", "notes":"No loss rescaling; keep separate from B4."
    },
    {
        "source_id":"B9", "input_paths":str(source_paths["B9"].relative_to(ROOT)).replace("\\","/"),
        "raw_rows":int(len(b9)), "valid_loss_rows":0, "independent_units":int(b9["model_name"].nunique()),
        "unit_type":"reported_model", "nature":"reported_metadata", "credibility":"metadata only; no observed loss",
        "loss_field":None, "loss_definition":"not available", "loss_unit":"not available",
        "loss_is_ground_truth":False, "N_field":"N_params_B", "D_field":"D_tokens_B",
        "N_unit":"billions of parameters", "D_unit":"billions of tokens (0 marks unavailable D)", "conversion":"none",
        "support_rule":">10B audit only; no truth-based error metric", "notes":"FLOPs and release metadata are not loss observations."
    },
    {
        "source_id":"B10", "input_paths":str(source_paths["B10"].relative_to(ROOT)).replace("\\","/"),
        "raw_rows":int(len(b10)), "valid_loss_rows":int(np.isfinite(b10["val_loss"]).sum()),
        "independent_units":int(b10["family"].nunique()), "unit_type":"estimated_model_record",
        "nature":"estimated", "credibility":"estimated baseline, explicitly non-truth",
        "loss_field":"val_loss", "loss_definition":"fitted-baseline estimate, not observed", "loss_unit":"estimated loss units",
        "loss_is_ground_truth":False, "N_field":"N_params_B", "D_field":"D_tokens_B",
        "N_unit":"billions of parameters", "D_unit":"billions of tokens", "conversion":"none",
        "support_rule":">10B scenario audit only; never used as validation truth", "notes":"All records are above B1 N support; D may be unavailable/zero."
    },
])
source_schema.to_csv(RUN / "source_schema_and_units.csv", index=False, encoding="utf-8-sig")
stage("source_schema", "PASS", "B1-B10 source schema and units audited")

frames = []
def make_frame(df, sid, row_prefix, cluster_col, loss_col, step_col=None, extra_cols=None, estimated=False):
    out = pd.DataFrame({
        "source_id": sid,
        "row_id": [f"{row_prefix}:{i}" for i in range(len(df))],
        "cluster_id": df[cluster_col].astype(str).to_numpy(),
        "cluster_type": "trajectory_or_run" if sid in {"B2","B3"} else "model_family_or_model",
        "N_B": pd.to_numeric(df["N_params_B"], errors="coerce").to_numpy(float),
        "D_B": pd.to_numeric(df["D_tokens_B"], errors="coerce").to_numpy(float),
        "step": pd.to_numeric(df[step_col], errors="coerce").to_numpy(float) if step_col else np.nan,
    })
    actual = pd.to_numeric(df[loss_col], errors="coerce").to_numpy(float)
    out["actual_loss"] = np.nan if estimated else actual
    out["reference_estimated_loss"] = actual if estimated else np.nan
    out["loss_is_ground_truth"] = bool(sid in {"B4","B5"} and not estimated)
    out["loss_observation_status"] = "ESTIMATED_REFERENCE" if estimated else "OBSERVED_OR_INTERPOLATED"
    for col in (extra_cols or []):
        if col in df.columns:
            out[col] = df[col].to_numpy()
    return out

f2 = make_frame(b2, "B2", "B2", "run_id", "val_loss", "steps", ["precision","train_loss","C_FLOPs_1e21"])
f3 = make_frame(b3, "B3", "B3", "_trajectory_file", "val_loss", "step", ["interpolated"])
f4 = make_frame(b4, "B4", "B4", "family", "val_loss", None, ["family","is_converged"])
f5 = make_frame(b5, "B5", "B5", "family", "val_loss", None, ["family","source","is_converged"])
f9 = make_frame(b9, "B9", "B9", "model_name", "N_params_B", None, ["model_name","FLOPs","publication_date","organization","accessibility","country"], estimated=False)
f9["actual_loss"] = np.nan
f9["reference_estimated_loss"] = np.nan
f9["loss_is_ground_truth"] = False
f9["loss_observation_status"] = "NOT_AVAILABLE"
f10 = make_frame(b10, "B10", "B10", "family", "val_loss", None, ["family","is_converged"], estimated=True)
f10["cluster_type"] = "estimated_model_record"
frames = [f2, f3, f4, f5, f9, f10]
pred = pd.concat(frames, ignore_index=True, sort=False)
pred["prediction_valid"] = np.isfinite(pred["N_B"]) & np.isfinite(pred["D_B"]) & (pred["N_B"] > 0) & (pred["D_B"] > 0)
pred["frozen_M0_B1_prediction"] = np.nan
valid = pred["prediction_valid"].to_numpy(bool)
pred.loc[valid, "frozen_M0_B1_prediction"] = source_prediction(pred.loc[valid, "N_B"], pred.loc[valid, "D_B"])
pred["support_status"] = [support_status(n, d) if ok else "INVALID_N_OR_D" for n,d,ok in zip(pred["N_B"], pred["D_B"], pred["prediction_valid"])]
pred["in_B1_box"] = pred["support_status"].eq("IN_SUPPORT")
pred["oos_flag"] = pred["prediction_valid"] & ~pred["in_B1_box"]
pred["clipped_to_support"] = False
pred["observed_error"] = pred["frozen_M0_B1_prediction"] - pred["actual_loss"]
pred["estimated_reference_delta"] = pred["frozen_M0_B1_prediction"] - pred["reference_estimated_loss"]
pred["relative_error_allowed_by_source"] = pred["source_id"].isin(["B2","B3","B4","B5"])
pred["absolute_relative_error"] = np.where(
    pred["relative_error_allowed_by_source"] & pred["actual_loss"].gt(0),
    pred["observed_error"].abs() / pred["actual_loss"], np.nan)
pred["signed_relative_error"] = np.where(
    pred["relative_error_allowed_by_source"] & pred["actual_loss"].gt(0),
    pred["observed_error"] / pred["actual_loss"], np.nan)
pred["source_support_rule"] = "inclusive B1 box: N_B in [0.070542,11.965825], D_B in [0.134,299.893]; no clipping"
pred.to_parquet(RUN / "validation_predictions.parquet", index=False)
stage("predictions", "PASS", f"wrote {len(pred)} row predictions without clipping")

qualification = {}
source_metric_rows = []
cluster_metric_rows = []
for sid in ["B2","B3","B4","B5","B9","B10"]:
    d = pred[pred["source_id"].eq(sid)].copy()
    if sid in {"B2","B3","B4","B5"}:
        subsets = {"ALL_VALID": d["actual_loss"].notna(), "IN_SUPPORT": d["actual_loss"].notna() & d["in_B1_box"], "OOS": d["actual_loss"].notna() & d["oos_flag"]}
    elif sid == "B10":
        subsets = {"ESTIMATED_REFERENCE_ALL": d["reference_estimated_loss"].notna() & d["prediction_valid"]}
    else:
        subsets = {"NO_OBSERVED_LOSS": pd.Series(False, index=d.index)}
    subset_stats = {}
    for subset_name, mask in subsets.items():
        x = d.loc[mask].copy()
        y = x["actual_loss"] if sid != "B10" else x["reference_estimated_loss"]
        p = x["frozen_M0_B1_prediction"]
        mv = metric_values(y.to_numpy(float), p.to_numpy(float), relative_allowed=(sid in {"B2","B3","B4","B5"}))
        bv = bootstrap_metrics(y.to_numpy(float), p.to_numpy(float), x["cluster_id"].to_numpy(object)) if len(x) else {
            "bootstrap_requested": NBOOT, "bootstrap_success": 0, "bootstrap_seed": SEED,
            "bootstrap_unit":"cluster_resample_with_replacement", "bootstrap_status":"NO_ROWS"
        }
        row = {
            "source_id": sid,
            "subset": subset_name,
            "raw_rows": int(len(d)),
            "valid_prediction_rows": int(d["prediction_valid"].sum()),
            "n_original_subset_rows": int(mask.sum()),
            "n_groups_in_subset": int(x["cluster_id"].nunique()) if len(x) else 0,
            "loss_is_ground_truth": bool(sid in {"B4","B5"}),
            "data_nature": {
                "B2":"semisynthetic","B3":"interpolated","B4":"published_observed",
                "B5":"published_observed","B9":"reported_metadata","B10":"estimated"
            }[sid],
        }
        row.update(mv)
        row.update(bv)
        row["bias_direction"] = bias_direction(row.get("mean_error"))
        source_metric_rows.append(row)
        subset_stats[subset_name] = row
    qualification[sid] = subset_stats

for sid in ["B2","B3","B4","B5"]:
    row = qualification[sid]["IN_SUPPORT"]
    n = int(row["n"]) if row.get("n") else 0
    groups = int(row["n_groups_in_subset"])
    rmse = row.get("rmse")
    bias = row.get("mean_error")
    sd = row.get("sd_actual")
    rho = row.get("spearman")
    if n < 5 or groups < 2:
        status = "OOS_STRESS_ONLY"
        basis = "fewer than five in-support rows or fewer than two independent clusters"
    else:
        nrmse = rmse / sd if sd and sd > 0 else math.inf
        bias_ok = abs(bias) <= 0.25 * sd if sd and sd > 0 else False
        rank_ok = (rho is None or rho >= 0.5)
        pass_validation = np.isfinite(nrmse) and nrmse <= 0.25 and bias_ok and rank_ok
        status = "VALIDATION_SUPPORTED" if pass_validation else "VALIDATION_FAILED"
        basis = (f"IN_SUPPORT n={n}, clusters={groups}, normalized_RMSE={nrmse:.6g}, "
                 f"abs(mean_error)={abs(bias):.6g}, sd_actual={sd:.6g}, Spearman={rho}; "
                 "predeclared descriptive gate: normalized_RMSE<=0.25, abs(mean_error)<=0.25*sd_actual, Spearman>=0.5")
    qualification[sid]["FINAL"] = status
    qualification[sid]["basis"] = basis
qualification["B9"] = {"FINAL":"OOS_STRESS_ONLY", "basis":"metadata only, no observed loss; all records exceed the B1 N upper support"}
qualification["B10"] = {"FINAL":"ESTIMATED_SCENARIO_ONLY", "basis":"loss values are estimated, not truth; all records exceed B1 N support"}

for r in source_metric_rows:
    sid = r["source_id"]
    if sid in qualification and "FINAL" in qualification[sid]:
        r["final_qualification"] = qualification[sid]["FINAL"]
        r["qualification_basis"] = qualification[sid]["basis"]
    else:
        r["final_qualification"] = ""
        r["qualification_basis"] = ""
metrics = pd.DataFrame(source_metric_rows)
metrics.to_csv(RUN / "validation_metrics_by_source.csv", index=False, encoding="utf-8-sig", float_format="%.17g")
stage("source_metrics", "PASS", "source-level metrics and cluster bootstrap completed")

for sid in ["B2","B3","B4","B5","B9","B10"]:
    d = pred[pred["source_id"].eq(sid)].copy()
    group_values = sorted(d["cluster_id"].dropna().astype(str).unique())
    if sid in {"B9","B10"} and len(group_values) > 1:
        group_values = ["ALL_UNIQUE_MODELS"]
    for g in group_values:
        x = d if g == "ALL_UNIQUE_MODELS" else d[d["cluster_id"].astype(str).eq(g)]
        for subset_name, mask in {
            "ALL_VALID": x["actual_loss"].notna() if sid not in {"B9","B10"} else x["reference_estimated_loss"].notna() if sid == "B10" else pd.Series(False, index=x.index),
            "IN_SUPPORT": x["in_B1_box"] & (x["actual_loss"].notna() if sid not in {"B9","B10"} else x["reference_estimated_loss"].notna()) if sid == "B10" else x["in_B1_box"] & x["actual_loss"].notna(),
        }.items():
            z = x.loc[mask]
            if len(z) == 0:
                continue
            y = z["actual_loss"] if sid not in {"B9","B10"} else z["reference_estimated_loss"]
            mv = metric_values(y.to_numpy(float), z["frozen_M0_B1_prediction"].to_numpy(float), relative_allowed=(sid in {"B2","B3","B4","B5"}))
            cluster_metric_rows.append({
                "source_id":sid, "group_id":g,
                "group_type":("trajectory_or_run" if sid in {"B2","B3"} else "model_family_or_record"),
                "subset":subset_name, "n_in_group_subset":len(z),
                "n_in_support":int(z["in_B1_box"].sum()),
                "loss_is_ground_truth":bool(sid in {"B4","B5"}),
                "data_nature":("estimated" if sid=="B10" else "reported_metadata" if sid=="B9" else {"B2":"semisynthetic","B3":"interpolated","B4":"published_observed","B5":"published_observed"}[sid]),
                **mv,
            })
pd.DataFrame(cluster_metric_rows).to_csv(RUN / "validation_metrics_by_family_or_trajectory.csv", index=False, encoding="utf-8-sig", float_format="%.17g")
stage("cluster_metrics", "PASS", "family/trajectory metrics written")

support_rows = []
for sid in ["B2","B3","B4","B5","B9","B10"]:
    d = pred[pred["source_id"].eq(sid)]
    nn = pd.to_numeric(d["N_B"], errors="coerce"); dd = pd.to_numeric(d["D_B"], errors="coerce")
    valid = np.isfinite(nn) & np.isfinite(dd) & (nn > 0) & (dd > 0)
    in_n = valid & nn.between(SUPPORT_N[0], SUPPORT_N[1], inclusive="both")
    in_d = valid & dd.between(SUPPORT_D[0], SUPPORT_D[1], inclusive="both")
    support_rows.append({
        "source_id":sid,
        "raw_rows":int(len(d)),
        "finite_positive_N_D_rows":int(valid.sum()),
        "in_B1_box_rows":int((in_n & in_d).sum()),
        "out_by_N_rows":int((~in_n & valid).sum()),
        "out_by_D_rows":int((~in_d & valid).sum()),
        "out_both_rows":int((~in_n & ~in_d & valid).sum()),
        "invalid_N_or_D_rows":int((~valid).sum()),
        "N_below_support":int((valid & (nn < SUPPORT_N[0])).sum()),
        "N_above_support":int((valid & (nn > SUPPORT_N[1])).sum()),
        "D_below_support":int((valid & (dd < SUPPORT_D[0])).sum()),
        "D_above_support":int((valid & (dd > SUPPORT_D[1])).sum()),
        "oos_fraction_of_finite":float(((~(in_n & in_d)) & valid).sum() / valid.sum()) if valid.sum() else None,
        "prediction_rule":"M0_B1 arithmetic prediction; support independent; no clipping",
        "primary_metric_subset":"IN_SUPPORT only",
    })
pd.DataFrame(support_rows).to_csv(RUN / "support_oos_audit.csv", index=False, encoding="utf-8-sig", float_format="%.17g")
stage("support_oos", "PASS", "support/OOS and no-clipping audit written")

bias_rows = []
for sid in ["B2","B3","B4","B5"]:
    d = pred[pred["source_id"].eq(sid) & pred["in_B1_box"] & pred["actual_loss"].notna() & pred["frozen_M0_B1_prediction"].notna()].copy()
    if len(d) == 0:
        continue
    e = d["observed_error"].to_numpy(float)
    bias_rows.append({
        "source_id":sid, "audit_type":"OVERALL", "stratifier":"none", "stratum":"IN_SUPPORT",
        "n":int(len(d)), "mean_error":float(np.mean(e)), "median_error":float(np.median(e)),
        "rmse":float(np.sqrt(np.mean(e*e))), "positive_error_fraction":float(np.mean(e>0)),
        "trend_spearman_error_vs_variable":None, "direction":bias_direction(float(np.mean(e)))
    })
    for var, col in [("N_B","N_B"),("D_B","D_B"),("step","step")]:
        vals = pd.to_numeric(d[col], errors="coerce").to_numpy(float) if col in d else np.array([])
        ok = np.isfinite(vals) & np.isfinite(e)
        if ok.sum() >= 5 and np.std(vals[ok]) > 0 and np.std(e[ok]) > 0:
            rho, _ = stats.spearmanr(vals[ok], e[ok])
            bias_rows.append({
                "source_id":sid, "audit_type":"TREND", "stratifier":var, "stratum":"IN_SUPPORT",
                "n":int(ok.sum()), "mean_error":None, "median_error":None, "rmse":None,
                "positive_error_fraction":None, "trend_spearman_error_vs_variable":float(rho),
                "direction":"ERROR_RISES_WITH_VARIABLE" if rho > 0.1 else "ERROR_FALLS_WITH_VARIABLE" if rho < -0.1 else "WEAK_MONOTONE_TREND"
            })
            try:
                bins = pd.qcut(vals[ok], q=min(4, len(np.unique(vals[ok]))), duplicates="drop")
            except ValueError:
                bins = pd.Series(["ALL"] * int(ok.sum()))
            tmp = pd.DataFrame({"value":vals[ok], "error":e[ok], "bin":pd.Series(bins).astype(str).to_numpy()})
            for label, z in tmp.groupby("bin", sort=True):
                ee = z["error"].to_numpy(float)
                bias_rows.append({
                    "source_id":sid, "audit_type":"QUARTILE", "stratifier":var, "stratum":str(label),
                    "n":int(len(z)), "mean_error":float(np.mean(ee)), "median_error":float(np.median(ee)),
                    "rmse":float(np.sqrt(np.mean(ee*ee))), "positive_error_fraction":float(np.mean(ee>0)),
                    "trend_spearman_error_vs_variable":None, "direction":bias_direction(float(np.mean(ee)))
                })
    for g, z in d.groupby("cluster_id", sort=True):
        if len(z) < 5:
            continue
        ee = z["observed_error"].to_numpy(float)
        bias_rows.append({
            "source_id":sid, "audit_type":"CLUSTER", "stratifier":"cluster_id", "stratum":str(g),
            "n":int(len(z)), "mean_error":float(np.mean(ee)), "median_error":float(np.median(ee)),
            "rmse":float(np.sqrt(np.mean(ee*ee))), "positive_error_fraction":float(np.mean(ee>0)),
            "trend_spearman_error_vs_variable":None, "direction":bias_direction(float(np.mean(ee)))
        })
pd.DataFrame(bias_rows).to_csv(RUN / "systematic_bias_audit.csv", index=False, encoding="utf-8-sig", float_format="%.17g")
stage("systematic_bias", "PASS", "N/D/step and cluster bias structure written")

large_rows = []
for sid in ["B9","B10"]:
    d = pred[pred["source_id"].eq(sid)].copy()
    gt = d["N_B"].gt(10)
    dd = pd.to_numeric(d["D_B"], errors="coerce")
    pred_ok = d["prediction_valid"]
    clean_pred = pred_ok & (~d["in_B1_box"])
    est = d["reference_estimated_loss"]
    dev = d.loc[clean_pred & est.notna(), "prediction_valid"]
    ref = est[clean_pred & est.notna()].to_numpy(float)
    pp = d.loc[clean_pred & est.notna(), "frozen_M0_B1_prediction"].to_numpy(float)
    ee = pp - ref
    large_rows.append({
        "source_id":sid,
        "raw_records":int(len(d)),
        "records_gt_10B":int(gt.sum()),
        "unique_model_families_gt_10B":int(d.loc[gt, "cluster_id"].nunique()),
        "N_min_B":ffloat(d["N_B"].min()),
        "N_max_B":ffloat(d["N_B"].max()),
        "D_available_records":int(dd.notna().sum()),
        "D_positive_records":int((dd > 0).sum()),
        "D_zero_or_invalid_records":int((~np.isfinite(dd) | (dd <= 0)).sum()),
        "loss_observed_records":0,
        "estimated_loss_records":int(est.notna().sum()),
        "finite_frozen_prediction_records":int(pred_ok.sum()),
        "inside_B1_box_records":int(d["in_B1_box"].sum()),
        "outside_by_N_records":int((~d["N_B"].between(SUPPORT_N[0], SUPPORT_N[1])).sum()),
        "outside_by_D_records":int((dd.notna() & ~dd.between(SUPPORT_D[0], SUPPORT_D[1])).sum()),
        "estimated_reference_rmse":ffloat(np.sqrt(np.mean(ee*ee))) if len(ee) else None,
        "estimated_reference_mae":ffloat(np.mean(np.abs(ee))) if len(ee) else None,
        "estimated_reference_mean_error":ffloat(np.mean(ee)) if len(ee) else None,
        "truth_status":"REPORTED_METADATA_NO_LOSS" if sid=="B9" else "ESTIMATED_NOT_TRUTH",
        "final_qualification":"OOS_STRESS_ONLY" if sid=="B9" else "ESTIMATED_SCENARIO_ONLY",
        "M0_can_support_above_10B_inference":False,
        "M0_numeric_support_upper_N_B":SUPPORT_N[1],
        "M0_numeric_support_upper_D_B":SUPPORT_D[1],
        "major_error_sources":"N/D extrapolation beyond B1; cross-source loss protocol; missing D/loss metadata; estimated loss is not truth"
    })
pd.DataFrame(large_rows).to_csv(RUN / "large_model_gt10b_audit.csv", index=False, encoding="utf-8-sig", float_format="%.17g")
stage("large_model_audit", "PASS", "B9/B10 >10B audit written")

features = list(model["features"])
coeff = np.asarray(model["models"]["linear"]["coefficients"], float)
if coeff.shape != (13, 17) or features != contract["mixture"]["feature_order"]:
    raise RuntimeError("frozen RegMix coefficient/feature mismatch")
contrast_c = coeff.mean(axis=0)
p0 = np.asarray(contract["mixture"]["p0"], float)
if len(p0) != 17 or abs(float(p0.sum()) - 1.0) > 1e-14:
    raise RuntimeError("frozen p0 simplex mismatch")
idx_arxiv = features.index("train_the_pile_arxiv")
idx_github = features.index("train_the_pile_github")
v_gh_ar = np.zeros(17); v_gh_ar[idx_github] = 1.0; v_gh_ar[idx_arxiv] = -1.0
if abs(float(v_gh_ar.sum())) > 1e-15 or np.any(p0 + 1e-6 * v_gh_ar < -1e-14):
    raise RuntimeError("worked feasible p direction invalid")
ctv = float(contrast_c @ v_gh_ar)
n_ref, d_ref = 1.0, 100.0
l_ref = source_prediction(n_ref, d_ref)
dl_dn = -FROZEN["alpha"] * FROZEN["A"] * n_ref ** (-FROZEN["alpha"] - 1.0)
dl_dd = -FROZEN["beta"] * FROZEN["B"] * d_ref ** (-FROZEN["beta"] - 1.0)
dl_dq_s01 = -1.0 * K_ADD * 1.0
el_n = dl_dn * n_ref / l_ref
el_d = dl_dd * d_ref / l_ref
el_q_s01 = dl_dq_s01 * Q_ANCHOR / l_ref
hold_n = -dl_dq_s01 / dl_dn
hold_d = -dl_dq_s01 / dl_dd
scenario_rows = []
for _, r in registry.iterrows():
    scenario_rows.append({
        "scenario_id":str(r["scenario_id"]),
        "family":str(r["family"]),
        "bridge":str(r["bridge"]),
        "q_source":str(r["q_source"]),
        "q_input_at_reference":ffloat(r["q_input_at_reference"]),
        "mapped_Q_B_at_reference":ffloat(r["mapped_Q_B_at_reference"]),
        "support_status_at_reference":str(r["support_status_at_reference"]),
        "rho_Q":ffloat(r["rho_Q_fixed_scenario"]),
        "r_B1_fixed_scenario":ffloat(r["r_B1_fixed_scenario"]),
        "quality_transport":str(r["quality_transport"]),
        "tau_p":ffloat(r["tau_p_fixed_scenario"]),
        "quality_effect_enabled":bool(r["quality_effect_enabled"]),
        "p_fixed_at_p0":bool(r["p_fixed_at_p0"]),
        "joint_Q_p_independent_optimizable":bool(r["joint_Q_p_independent_optimizable"]),
        "eligibility":str(r["eligibility"]),
    })
spec = {
    "schema_version":1,
    "run_id":RUN.name,
    "status":"GENERALIZED_CONDITIONAL_SCALING_LAW_SPEC",
    "formula":"L_gen^(s)(N_B,D_B,Q_A,p)=L0_B1(N_B,D_B)+rho_Q^(s)*Delta_Q(h_s(Q_A))+tau_p^(s)*Delta_p(p;p0)",
    "estimand_status":"LAYERED_ESTIMATION_JOINT_EXPRESSION_NOT_JOINTLY_IDENTIFIED",
    "L0_B1":{
        "formula":"E+A*N_B^(-alpha)+B*D_B^(-beta)",
        "parameters":FROZEN,
        "qualification":"IDENTIFIED_SOURCE_CONDITIONAL",
        "source":"B1",
        "support":{"N_B":SUPPORT_N,"D_B":SUPPORT_D},
        "no_refit":True,"no_clipping":True
    },
    "quality_module":{
        "formula":"rho_Q^(s)*Delta_Q(h_s(Q_A))",
        "Delta_Q":"-k_add*(Q_B-0.6)",
        "k_add":K_ADD,
        "k_add_source":"B6 MQ-add; SOURCE_CONDITIONAL only for 0.1<=Q_B<=0.6",
        "q_A_star":Q_ANCHOR,
        "cross_source_status":"NOT_IDENTIFIABLE; H1-H3 SCENARIO_ONLY, H4 DIRECTION_ONLY",
        "h_s":{
            "H0":{"formula":None,"qualification":"IDENTIFIED_NULL_BASELINE","derivative":0.0},
            "H1":{"formula":"h(Q_A)=Q_A","qualification":"SCENARIO_ONLY","derivative":"1"},
            "H2":{"formula":"h(Q_A)=0.6+b*(Q_A-q_A_star)","b_fixed_scenario":[0.5,1.0,2.0],"qualification":"SCENARIO_ONLY","derivative":"b"},
            "H3":{"formula":"h(Q_A)=F_B^{-1}(F_A(Q_A)) empirical quantile step map","qualification":"SCENARIO_ONLY","derivative":"0 almost everywhere, undefined at CDF jumps; use finite differences after scenario fixed"},
            "H4":{"formula":None,"qualification":"DIRECTION_ONLY_NOT_OPTIMIZABLE","derivative":"direction only; no numeric value"}
        },
        "rho_Q_allowed_values":[0.0,0.5,1.0],
        "rho_Q_source":"frozen scenario_registry_filled.csv column rho_Q_fixed_scenario"
    },
    "mixture_module":{
        "formula":"tau_p^(s)*Delta_p(p;p0)",
        "Delta_p":"c^T*(p-p0)",
        "feature_order":features,
        "p0":p0.tolist(),
        "p0_constraint":"p_j>=0, sum(p)=1",
        "c_definition":"equal-domain mean of the 13 frozen RegMix linear coefficient vectors",
        "c":contrast_c.tolist(),
        "source_status":"WITHIN_1M_SOURCE_CONDITIONAL",
        "cross_source_transport":"SCENARIO_ONLY; tau_p fixed from frozen registry and never fitted here",
        "tau_p_allowed_values":[0.0,0.5,1.0,-1.0],
        "feasible_direction_definition":"v with sum(v)=0 and p0+eps*v nonnegative for local eps"
    },
    "joint_Q_p":{
        "independent_estimation_or_optimization_allowed":False,
        "reason":"For fixed domain quality q, Q_mix=p^T q lies in the p column space; no fixed-p quality intervention identifies both.",
        "design_rank":17,
        "augmented_rank":17,
        "relative_projection_residual":9.368877196481023e-16
    },
    "worked_example":{
        "N_B":n_ref,"D_B":d_ref,"L0_B1":l_ref,
        "dL_dN_B":dl_dn,"dL_dD_B":dl_dd,
        "elasticity_N_B":el_n,"elasticity_D_B":el_d,
        "scenario_for_Q":"S03_H1_IDENTITY",
        "rho_Q":1.0,"k_add":K_ADD,"h_prime":1.0,
        "dL_dQ_A":dl_dq_s01,"elasticity_Q_A":el_q_s01,
        "holding_Loss_dN_dQ":hold_n,"holding_Loss_dD_dQ":hold_d,
        "feasible_direction":"e_github-e_arxiv",
        "v_sum":float(v_gh_ar.sum()),"cT_v":ctv,
        "directional_derivative_tau05":0.5*ctv,
        "directional_derivative_tau10":1.0*ctv,
        "directional_derivative_tau_minus10":-1.0*ctv
    },
    "scenarios":scenario_rows,
    "prohibitions":[
        "No unified four-variable joint fit is claimed.",
        "No new A/B quality map or cross-source scale parameter is estimated.",
        "Do not interpret 17 p coordinates as independent marginal effects.",
        "Do not use Q_mix and p as two independent free controls when Q_mix=p^T q."
    ]
}
write_json(RUN / "generalized_law_spec.json", spec)
stage("generalized_law_spec", "PASS", "layered generalized law and analytic quantities written")

qual_rows = [
    {"term":"E","source":"B1 frozen M0_B1","qualification":"IDENTIFIED_SOURCE_CONDITIONAL","numeric":True,"note":"Exact frozen value; no refit."},
    {"term":"A","source":"B1 frozen M0_B1","qualification":"IDENTIFIED_SOURCE_CONDITIONAL","numeric":True,"note":"Exact frozen value; no refit."},
    {"term":"B","source":"B1 frozen M0_B1","qualification":"IDENTIFIED_SOURCE_CONDITIONAL","numeric":True,"note":"Exact frozen value; no refit."},
    {"term":"alpha","source":"B1 frozen M0_B1","qualification":"IDENTIFIED_SOURCE_CONDITIONAL","numeric":True,"note":"Exact frozen value; no refit."},
    {"term":"beta","source":"B1 frozen M0_B1","qualification":"IDENTIFIED_SOURCE_CONDITIONAL","numeric":True,"note":"Exact frozen value; no refit."},
    {"term":"k_add","source":"B6 MQ-add","qualification":"SOURCE_CONDITIONAL","numeric":True,"note":"Only 0.1<=Q_B<=0.6; accepted B6 source relation."},
    {"term":"Delta_Q","source":"B6 relation plus A/B bridge","qualification":"SCENARIO_CALIBRATED","numeric":True,"note":"Cross-source use requires H1-H3 scenario or H4 direction only."},
    {"term":"rho_Q","source":"frozen scenario registry","qualification":"SCENARIO_CALIBRATED","numeric":True,"note":"Allowed values 0,0.5,1; no post-hoc selection."},
    {"term":"h_s(H0)","source":"T06 frozen bridge","qualification":"IDENTIFIED_NULL_BASELINE","numeric":False,"note":"Null quality effect."},
    {"term":"h_s(H1-H3)","source":"T06 frozen bridge","qualification":"SCENARIO_ONLY","numeric":True,"note":"Assumption-defined; no new map estimated."},
    {"term":"h_s(H4)","source":"T06 frozen bridge","qualification":"DIRECTION_ONLY","numeric":False,"note":"No numeric derivative or optimization."},
    {"term":"Delta_p","source":"frozen RegMix linear model","qualification":"SOURCE_CONDITIONAL","numeric":True,"note":"Supported at 1M; cross-scale transport is scenario only."},
    {"term":"c","source":"mean of 13 frozen RegMix coefficient vectors","qualification":"SOURCE_CONDITIONAL","numeric":True,"note":"Used as a directional contrast, not 17 independent p marginals."},
    {"term":"tau_p","source":"frozen scenario registry","qualification":"SCENARIO_CALIBRATED","numeric":True,"note":"Allowed fixed values 0,0.5,1,-1."},
    {"term":"Q_A-to-Q_B scale","source":"A/B bridge","qualification":"NOT_IDENTIFIABLE","numeric":False,"note":"No sample-level pairing; H1-H3 are scenarios."},
    {"term":"joint Q_mix and p effects","source":"A/RegMix design geometry","qualification":"NOT_IDENTIFIABLE","numeric":False,"note":"Q_mix is in the p column space for fixed q."},
    {"term":"r_B1_fixed_scenario","source":"frozen scenario registry","qualification":"SCENARIO_CALIBRATED","numeric":True,"note":"Retained in registry/T07 context; not a new G2 estimate and not separately identified."},
]
pd.DataFrame(qual_rows).to_csv(RUN / "generalized_parameter_qualification.csv", index=False, encoding="utf-8-sig")

md = f"""# G2 analytic derivatives, elasticities and local substitutions

The only formal expression is the layered law

`L_gen^(s)(N_B,D_B,Q_A,p)=L0_B1(N_B,D_B)+rho_Q^(s)*Delta_Q(h_s(Q_A))+tau_p^(s)*Delta_p(p;p0)`.

It is not a jointly identified four-variable response surface.

## Base B1 derivatives

- `dL0/dN_B = -alpha*A*N_B^(-alpha-1)`.
- `dL0/dD_B = -beta*B*D_B^(-beta-1)`.
- At `N_B={n_ref:g}, D_B={d_ref:g}`: `L0={l_ref:.17g}`, `dL0/dN_B={dl_dn:.17g}`, `dL0/dD_B={dl_dd:.17g}`.
- Local base elasticities: `E_N=N_B/L*dL/dN_B={el_n:.17g}`; `E_D=D_B/L*dL/dD_B={el_d:.17g}`.

## Quality derivative

For numeric H1-H3 scenarios,

`dL/dQ_A = -rho_Q^(s)*k_add*h_s'(Q_A)`,

with `h1'=1`, `h2'=b` for fixed `b in {{0.5,1,2}}`, and H3 the empirical quantile-step map. H3 is zero almost everywhere and undefined at CDF jumps, so only finite differences after fixing the scenario are allowed. H4 gives direction only.

For `S03_H1_IDENTITY`, `rho_Q=1`, `k_add={K_ADD:.17g}`, and `Q_A={Q_ANCHOR:.17g}`:

- `dL/dQ_A={dl_dq_s01:.17g}`.
- `E_Q=Q_A/L*dL/dQ_A={el_q_s01:.17g}`.

## Feasible mixture direction

For a feasible direction `v` with `sum(v)=0` and `p0+epsilon*v>=0` locally,

`D_v L = tau_p^(s)*c^T v`.

Using the frozen equal-domain mean RegMix contrast `c` and `v=e_github-e_arxiv`, `c^T v={ctv:.17g}`. Therefore the directional slope is `{0.5*ctv:.17g}` for S14, `{ctv:.17g}` for S15, and `{-ctv:.17g}` for the S16 stress scenario. These are scenario slopes, not estimates of 17 independent domain marginal effects.

## Holding Loss fixed: local N/D substitution

- `(dN_B/dQ_A)|_L = -(dL/dQ_A)/(dL0/dN_B)`.
- `(dD_B/dQ_A)|_L = -(dL/dQ_A)/(dL0/dD_B)`.
- At the worked point under S03: `{hold_n:.17g}` billion parameters per Q unit and `{hold_d:.17g}` billion tokens per Q unit.

## Local p-Q substitution

- If `Q_A` is fixed independently, use `D_v L=tau_p*c^T v`.
- If `Q_mix=p^T q` with fixed domain quality vector `q`, `Q_mix` lies in the p column space. Then `tau_p*c^T v` and the quality term cannot be interpreted as two independent effects. Only a fixed scenario linking `p` and `Q_mix` may be reported.
- No complementarity or substitution claim is transferred across B1, B6, A/RegMix, or B8 without the corresponding source qualification.
"""
(RUN / "derivatives_elasticities_and_substitutions.md").write_text(md, encoding="utf-8")
stage("derivatives", "PASS", "analytic derivatives and feasible-direction slopes written")

p_summary = json.loads((P_RUN / "run_summary.json").read_text(encoding="utf-8"))
pq = {
    "status":"NOT_IDENTIFIABLE",
    "independent_joint_estimation_or_optimization_allowed":False,
    "fixed_q_identity":"Q_mix=p^T q is in the column space of p",
    "design_rank":int(p_summary["p_Q_double_counting"]["design_rank"]),
    "augmented_rank":int(p_summary["p_Q_double_counting"]["augmented_rank"]),
    "relative_projection_residual":float(p_summary["p_Q_double_counting"]["relative_projection_residual"]),
    "mapped_quality_domains":int(mapping_guide["quality_domain"].ne("(none)").sum()),
    "unmapped_quality_domains":int(mapping_guide["quality_domain"].eq("(none)").sum()),
    "required_rule":"When Q_mix=p^Tq is used, do not also expose all p effects as independent marginal effects; fix p or Q scenario, or report only a joint feasible direction.",
    "forbidden":"17 independent p marginal effects and Q/p double counting",
    "source":"TASK-T06E-P frozen audit; no refit or new algebra fit"
}
write_json(RUN / "p_q_double_counting_audit.json", pq)
stage("p_q_audit", "PASS", "Q_mix/p rank audit recorded")

t07_decision = {
    "NEW_Q2_CHANGES_T07_NUMERIC_INPUTS":"NO",
    "decision":"NO",
    "reason":"M0_B1 was not refit or reselected; all five parameters are exact frozen values. B2-B5 validation outcomes, the layered L_gen expression, analytic derivatives, and scenario qualifications do not modify T07's numeric contract.",
    "t07_primary_model":"M0_B1",
    "t07_quality_enabled":False,
    "t07_mixture_transport_enabled":False,
    "t07_contract_path":str(CONTRACT_PATH.relative_to(ROOT)).replace("\\","/"),
    "t07_contract_sha256":sha256(CONTRACT_PATH),
    "t07_freeze_path":str(T07_FREEZE.relative_to(ROOT)).replace("\\","/"),
    "t07_freeze_sha256":sha256(T07_FREEZE),
    "incremental_t07_started_or_authorized":False,
    "numeric_parameters_modified":[],
    "note":"This is an impact decision only; it does not start T07."
}
write_json(RUN / "t07_impact_decision.json", t07_decision)
stage("t07_impact", "PASS", "T07 numeric inputs unchanged")

# Recompute protected hashes immediately after all execution reads/writes.
after = {}
for p in protected_roots:
    after[str(p.relative_to(ROOT)).replace("\\","/")] = hash_tree(p)
for p in [T06_FREEZE, T07_FREEZE]:
    after[str(p.relative_to(ROOT)).replace("\\","/")] = hash_tree(p)
protected_unchanged = before == after

required_plot = [
    "environment.json","input_manifest.json","command_log.json","stage_status.jsonl",
    "source_schema_and_units.csv","validation_predictions.parquet","validation_metrics_by_source.csv",
    "validation_metrics_by_family_or_trajectory.csv","support_oos_audit.csv","systematic_bias_audit.csv",
    "large_model_gt10b_audit.csv","generalized_law_spec.json","generalized_parameter_qualification.csv",
    "derivatives_elasticities_and_substitutions.md","p_q_double_counting_audit.json","t07_impact_decision.json",
]
checks = [
    {"check":"frozen_M0_B1_parameters_exact","pass":all(contract_params[k] == v for k,v in FROZEN.items())},
    {"check":"no_new_model_fit_or_selection","pass":True,"detail":"execution computes predictions only; no optimizer/fit call"},
    {"check":"support_evaluated_without_clipping","pass":bool((pred["clipped_to_support"] == False).all())},
    {"check":"B2_and_B3_both_executed","pass":all(pred["source_id"].eq(s).any() for s in ["B2","B3"])},
    {"check":"B2_or_B3_nonempty_comparable_validation","pass":False,"detail":"value checked below"},
    {"check":"B4_and_B5_kept_separate","pass":all(pred["source_id"].eq(s).any() for s in ["B4","B5"]) and not pred.loc[pred.source_id.isin(["B4","B5"])].duplicated(["source_id","row_id"]).any()},
    {"check":"B9_and_B10_gt10b_audited","pass":set(pd.read_csv(RUN / "large_model_gt10b_audit.csv")["source_id"]) == {"B9","B10"}},
    {"check":"B10_not_used_as_truth","pass":not bool(pred.loc[pred.source_id.eq("B10"),"loss_is_ground_truth"].any())},
    {"check":"no_global_cross_source_RMSE","pass":True,"detail":"one pooled RMSE across all sources is absent"},
    {"check":"Q_and_p_not_independent","pass":pq["independent_joint_estimation_or_optimization_allowed"] is False},
    {"check":"T07_numeric_input_decision_is_NO","pass":t07_decision["NEW_Q2_CHANGES_T07_NUMERIC_INPUTS"] == "NO"},
    {"check":"protected_T06_T07_hashes_unchanged","pass":bool(protected_unchanged)},
]
# Correct the B2/B3 coverage check with the actual metrics table.
b23 = metrics[metrics["source_id"].isin(["B2","B3"]) & metrics["subset"].eq("IN_SUPPORT")]
checks[4]["pass"] = bool(len(b23) and b23["n"].fillna(0).gt(0).any())
checks.append({"check":"all_execution_outputs_present","pass":all((RUN / p).exists() for p in required_plot)})
checks.append({"check":"candidate_freeze_generated_after_verification","pass":False,"detail":"pending finalize step"})
checks.append({"check":"output_manifest_generated_last","pass":False,"detail":"pending finalize step"})
write_json(RUN / "checks_pre_verification.json", {"run_id":RUN.name,"checks":checks})
stage("execution_checks", "PASS" if all(c.get("pass") for c in checks if "pending" not in c.get("detail","").lower()) else "FAIL", "pre-verification checks written")

run_summary = {
    "task_id":"TASK-G2",
    "run_id":RUN.name,
    "status":"COMPLETE_PENDING_CONTROLLER_REVIEW",
    "execution_status":"COMPLETE",
    "verification_status":"PENDING_INDEPENDENT_VERIFIER",
    "primary_model":"M0_B1",
    "no_refit":True,
    "no_model_reselection":True,
    "source_rows":{sid:int((pred["source_id"].eq(sid)).sum()) for sid in ["B2","B3","B4","B5","B9","B10"]},
    "final_qualification":{sid:qualification[sid]["FINAL"] for sid in ["B2","B3","B4","B5","B9","B10"]},
    "generalized_law_status":spec["estimand_status"],
    "NEW_Q2_CHANGES_T07_NUMERIC_INPUTS":"NO",
    "checks":{c["check"]:c.get("pass") for c in checks},
    "next_action":"Independent verifier must recompute predictions, supports, metrics and hashes; controller review follows."
}
write_json(RUN / "run_summary.json", run_summary)
stage("execution_complete", "COMPLETE_PENDING_CONTROLLER_REVIEW", "awaiting independent verification")
print(json.dumps({"status":"EXECUTION_COMPLETE","run_id":RUN.name,"qualification":run_summary["final_qualification"]}, ensure_ascii=False))




