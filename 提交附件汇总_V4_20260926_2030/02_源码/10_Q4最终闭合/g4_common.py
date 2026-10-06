# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

RUN_ID = "20260925T195716+0800"
TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[4]
RUN_DIR = Path(__file__).resolve().parents[1]

TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]
AUX_TARGET = "six_task_mean_complete_only"
ALL_TARGETS = TASKS + [AUX_TARGET]
SCENARIO_IDS = ["SLOW", "BASELINE", "UPPER_SENSITIVITY"]
HORIZONS = [12, 24]
SEED = 20260925
BOOTSTRAP_DRAWS = 500
ALPHA = 0.10

C1 = ROOT / "F题/real_attachments/C_efficiency_evolution/leaderboard_cleaned.csv"
C2 = ROOT / "F题/real_attachments/C_efficiency_evolution/leaderboard_enhanced.csv"
C3 = ROOT / "F题/real_attachments/C_efficiency_evolution/leaderboard_extended_timeseries.csv"
C4 = ROOT / "F题/real_attachments/C_efficiency_evolution/epoch_all_ai_models.csv"
C01_R1 = ROOT / "diagnostics/TASK-C01-R1/20260924T225308+08"
T05 = ROOT / "diagnostics/TASK-T05/20260925T113355+0800"
T08 = ROOT / "diagnostics/TASK-T08/20260925T142203+0800"

FORMAL_INPUTS = [
    ROOT / "tasks/TASK-G4_Q4技术演进与前沿预测闭合.md",
    ROOT / "audit/FINAL_PROJECT_STATE.md",
    ROOT / "audit/QUESTION_REQUIREMENT_COVERAGE.md",
    ROOT / "audit/FINAL_RESULT_SOURCE_OF_TRUTH.md",
    ROOT / "paper/T05_RESULT_FREEZE.md",
    ROOT / "paper/T08_RESULT_FREEZE.md",
    C1, C2, C3, C4,
    C01_R1 / "c8_model_task_aggregate_corrected.csv",
    C01_R1 / "c8_model_wide_corrected.csv",
    C01_R1 / "c8_directory_aggregate_corrected.csv",
    C01_R1 / "run_summary.json",
    C01_R1 / "verification.json",
    T05 / "model_identity_crosswalk.csv",
    T05 / "duplicate_run_resolution.csv",
    T05 / "corrupt_and_partial_coverage.csv",
    T05 / "taskwise_bridge_results.csv",
    T05 / "validation_by_family.csv",
    T05 / "validation_by_scale.csv",
    T05 / "validation_by_split.csv",
    T05 / "validation_by_time.csv",
    T05 / "execution_seal.json",
    T05 / "t08_bridge_contract.json",
    T08 / "historical_strata_summary.csv",
    T08 / "forecast_seal.json",
    T08 / "scenario_registry.csv",
    T08 / "loss_space_scale_scenarios.csv",
    T08 / "forecast_12m_24m_scenarios.csv",
    T08 / "taskwise_progress.csv",
    T08 / "forecast_uncertainty.csv",
    T08 / "scale_non_scale_decomposition.csv",
    T08 / "support_oos_audit.csv",
    T08 / "t08_paper_interface.json",
]


def local_now() -> datetime:
    return datetime.now(TZ)


def iso_local(dt: datetime | None = None) -> str:
    return (dt or local_now()).astimezone(TZ).isoformat()


def iso_utc(dt: datetime | None = None) -> str:
    x = dt or datetime.now(timezone.utc)
    if x.tzinfo is None:
        x = x.replace(tzinfo=timezone.utc)
    return x.astimezone(timezone.utc).isoformat()


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if pd.isna(value):
            return None
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        if pd.isna(value):
            return None
        return value.isoformat()
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(json_safe(payload), fh, ensure_ascii=False, indent=2, allow_nan=False)
        fh.write("\n")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(json_safe(row), ensure_ascii=False, allow_nan=False) + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def manifest_entry(path: Path) -> dict[str, Any]:
    return {"path": relpath(path), "bytes": int(path.stat().st_size), "sha256": sha256_file(path)}


def build_input_manifest() -> dict[str, Any]:
    missing = [relpath(p) for p in FORMAL_INPUTS if not p.exists()]
    return {
        "run_id": RUN_ID,
        "created_local": iso_local(),
        "root": str(ROOT),
        "file_count": int(sum(p.exists() for p in FORMAL_INPUTS)),
        "missing_count": len(missing),
        "missing": missing,
        "files": [manifest_entry(p) for p in FORMAL_INPUTS if p.exists()],
    }


def environment_payload() -> dict[str, Any]:
    import scipy
    import sklearn
    import statsmodels
    return {
        "run_id": RUN_ID,
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "sklearn": sklearn.__version__,
        "statsmodels": statsmodels.__version__,
        "timezone": "Asia/Shanghai (UTC+08:00)",
        "created_local": iso_local(),
        "network_access_used": False,
    }


def write_stage(stage: str, status: str, **extra: Any) -> None:
    append_jsonl(RUN_DIR / "stage_status.jsonl", {
        "run_id": RUN_ID,
        "stage": stage,
        "status": status,
        "timestamp_local": iso_local(),
        **extra,
    })


def normalize_alnum(value: Any) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip().lower()
    s = s.replace("meta-llama/", "").replace("meta-llama", "llama")
    s = re.sub(r"^meta[\/_-]*", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def model_basename(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().split("/")[-1]


def normalize_model_alias(value: Any) -> str:
    s = model_basename(value)
    s = re.sub(r"^meta[_-]*llama", "llama", s, flags=re.I)
    s = re.sub(r"^meta[_-]*", "", s, flags=re.I)
    return normalize_alnum(s)


def extract_hf_repo(value: Any) -> str:
    if pd.isna(value):
        return ""
    m = re.search(r"huggingface\.co/([^/\s?#]+/[^/\s?#]+)", str(value), flags=re.I)
    return m.group(1).strip("/").lower() if m else ""


def parse_plain_number(value: Any) -> float:
    if pd.isna(value):
        return np.nan
    s = str(value).strip().replace(" ", "").replace(",", "")
    try:
        x = float(s)
    except Exception:
        return np.nan
    return x if np.isfinite(x) and x > 0 else np.nan


def parse_dataset_tokens(value: Any) -> float:
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if not s:
        return np.nan
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", s):
        v = float(s)
        return v if v > 0 else np.nan
    parts = [x.strip() for x in s.split(",") if x.strip()]
    if len(parts) >= 2 and len(set(parts)) == 1 and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", parts[0]):
        v = float(parts[0])
        return v if v > 0 else np.nan
    return np.nan


def parse_date(value: Any) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    x = pd.to_datetime(value, errors="coerce")
    if pd.isna(x):
        return pd.NaT
    if getattr(x, "tzinfo", None) is not None:
        x = x.tz_convert(TZ).tz_localize(None)
    return pd.Timestamp(x).normalize()


def unix_to_local_date(value: Any) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    try:
        x = pd.to_datetime(float(value), unit="s", utc=True)
    except Exception:
        return pd.NaT
    return x.tz_convert(TZ).tz_localize(None).normalize()


def safe_quantile(values: Iterable[Any], q: float) -> float:
    s = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna()
    if len(s) == 0:
        return np.nan
    return float(s.quantile(q))


def metric_mae(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(y) - np.asarray(p))))


def metric_rmse(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def pinball(y: np.ndarray, p: np.ndarray, q: float = 0.90) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    d = y - p
    return float(np.mean(np.maximum(q * d, (q - 1) * d)))


def safe_spearman(y: np.ndarray, p: np.ndarray) -> float:
    if len(y) < 3 or len(np.unique(y)) < 2 or len(np.unique(p)) < 2:
        return np.nan
    from scipy.stats import spearmanr
    v = spearmanr(y, p).statistic
    return float(v) if np.isfinite(v) else np.nan


def design_matrix(frame: pd.DataFrame, spec: str) -> np.ndarray:
    cols = [np.ones(len(frame), dtype=float)]
    if spec in ("M1_SCALE", "M2_SCALE_TIME"):
        cols.append(pd.to_numeric(frame["log10_compute"], errors="coerce").to_numpy(float))
    if spec == "M2_SCALE_TIME":
        cols.append(pd.to_numeric(frame["time_years"], errors="coerce").to_numpy(float))
    return np.column_stack(cols)


def fit_ols(frame: pd.DataFrame, target: str, spec: str) -> dict[str, Any]:
    y = pd.to_numeric(frame[target], errors="coerce").to_numpy(float)
    X = design_matrix(frame, spec)
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    if len(y) < max(3, X.shape[1] + 1):
        return {"status": "NOT_IDENTIFIABLE", "n": int(len(y)), "coef": None, "pred": None}
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    return {"status": "OK", "n": int(len(y)), "coef": beta.tolist(), "pred": pred,
            "residual": y - pred, "rank": int(rank), "p": int(X.shape[1])}


def fit_quantile(frame: pd.DataFrame, target: str, spec: str, q: float = 0.90) -> dict[str, Any]:
    import warnings
    import statsmodels.api as sm
    y = pd.to_numeric(frame[target], errors="coerce").to_numpy(float)
    X = design_matrix(frame, spec)
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    max_iter = 2000
    if len(y) < max(8, X.shape[1] + 3):
        return {"status": "NOT_IDENTIFIABLE", "n": int(len(y)), "coef": None, "iterations": 0}
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fit = sm.QuantReg(y, X).fit(q=q, max_iter=max_iter, p_tol=1e-8)
        warning_names = [type(w.message).__name__ for w in caught]
        iterations = int(getattr(fit, "iterations", 0))
        if warning_names or iterations >= max_iter:
            return {
                "status": "NOT_IDENTIFIABLE", "n": int(len(y)), "coef": None,
                "iterations": iterations, "reason": "quantile_optimizer_not_converged",
                "warnings": "|".join(warning_names),
            }
        beta = np.asarray(fit.params, dtype=float)
        if not np.isfinite(beta).all():
            raise ValueError("non-finite quantile coefficients")
        return {"status": "OK", "n": int(len(y)), "coef": beta.tolist(), "iterations": iterations}
    except Exception as exc:
        return {"status": "NOT_IDENTIFIABLE", "n": int(len(y)), "coef": None, "reason": str(exc)}

def fit_robust(frame: pd.DataFrame, target: str, spec: str) -> dict[str, Any]:
    import statsmodels.api as sm
    y = pd.to_numeric(frame[target], errors="coerce").to_numpy(float)
    X = design_matrix(frame, spec)
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    if len(y) < max(8, X.shape[1] + 3):
        return {"status": "NOT_IDENTIFIABLE", "n": int(len(y)), "coef": None}
    try:
        fit = sm.RLM(y, X, M=sm.robust.norms.HuberT()).fit()
        beta = np.asarray(fit.params, dtype=float)
        if not np.isfinite(beta).all():
            raise ValueError("non-finite robust coefficients")
        return {"status": "OK", "n": int(len(y)), "coef": beta.tolist()}
    except Exception as exc:
        return {"status": "NOT_IDENTIFIABLE", "n": int(len(y)), "coef": None, "reason": str(exc)}


def predict_design(frame: pd.DataFrame, spec: str, coef: list[float] | np.ndarray) -> np.ndarray:
    return design_matrix(frame, spec) @ np.asarray(coef, dtype=float)


def condition_number(frame: pd.DataFrame, spec: str) -> tuple[bool, float, int, int]:
    X = design_matrix(frame, spec)
    if spec == "M0_CONSTANT":
        return True, 1.0, X.shape[1], X.shape[1]
    Z = X.copy()
    for j in range(1, Z.shape[1]):
        s = np.std(Z[:, j])
        if not np.isfinite(s) or s <= 1e-15:
            return False, np.inf, int(np.linalg.matrix_rank(X)), int(X.shape[1])
        Z[:, j] = (Z[:, j] - np.mean(Z[:, j])) / s
    rank = int(np.linalg.matrix_rank(Z))
    cond = float(np.linalg.cond(Z))
    return bool(rank == Z.shape[1] and np.isfinite(cond) and cond < 1e8), cond, rank, int(Z.shape[1])


def choose_center(frame: pd.DataFrame, center: pd.Timestamp, days: int = 365) -> float:
    d = pd.to_datetime(frame["score_date"], errors="coerce")
    v = pd.to_numeric(frame["log10_compute"], errors="coerce")
    mask = d.between(center - pd.Timedelta(days=days), center + pd.Timedelta(days=days)) & v.notna()
    sub = frame.loc[mask, ["score_date", "log10_compute"]].copy()
    if len(sub) >= 3:
        return float(pd.to_numeric(sub["log10_compute"], errors="coerce").median())
    tmp = frame.loc[v.notna(), ["score_date", "log10_compute"]].copy()
    if tmp.empty:
        return np.nan
    tmp["distance"] = (pd.to_datetime(tmp["score_date"], errors="coerce") - center).abs()
    tmp = tmp.sort_values(["distance", "log10_compute"]).head(3)
    return float(pd.to_numeric(tmp["log10_compute"], errors="coerce").median())


def write_code_snapshot() -> None:
    import shutil
    snap = RUN_DIR / "code_snapshot"
    snap.mkdir(parents=True, exist_ok=True)
    for src in sorted((RUN_DIR / "code").glob("*.py")):
        shutil.copy2(src, snap / src.name)
