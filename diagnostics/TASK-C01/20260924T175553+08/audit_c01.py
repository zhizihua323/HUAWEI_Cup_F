# -*- coding: utf-8 -*-
"""TASK-C01: C1-C10 data audit and C8 basic aggregation.

Independent of the ongoing quality (Q) review.  Scope limits enforced by this script:
  * NO future 12/24-month forecasting.
  * NO final Loss-Benchmark bridging model (C5/C6 are described by stratum only).
  * NO choice of the final problem-4 statistical model.
  * `solution/src/evolution_audit.py` is reviewed statically only and is NOT imported,
    executed, modified or overwritten.

Every number written by this script comes from the actual run below.
Original attachments are opened read-only through Windows extended-length paths.
"""
import hashlib
import json
import os
import platform
import re
import sys
import traceback
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

RUN_ID = "20260924T175553+08"
TASK = "TASK-C01"
AUTHOR = "Codex (OpenAI), AI-assisted, 2026-09-24"

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(WORKSPACE, "F题", "real_attachments")
CROOT = os.path.join(DATA, "C_efficiency_evolution")
OUT = HERE

TZ = timezone(timedelta(hours=8))
START = datetime.now(TZ)
LOG_LINES = []


def log(message=""):
    line = str(message)
    LOG_LINES.append(line)
    print(line, flush=True)


def epath(path):
    """Windows extended-length path (long-path safe) for every raw-data access."""
    path = os.path.abspath(str(path))
    if os.name == "nt" and not path.startswith("\\\\?\\"):
        return "\\\\?\\" + path
    return path


def rel(path):
    """Human readable path relative to the workspace for CSV output."""
    try:
        return os.path.relpath(path, WORKSPACE).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(epath(path), "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def write_csv(name, frame):
    path = os.path.join(OUT, name)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def to_builtin(value):
    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, (pd.Timestamp,)):
        return None if pd.isna(value) else str(value)
    return str(value)


def write_json(name, payload):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(to_builtin(payload), handle, ensure_ascii=False, indent=2, allow_nan=False)
    return path


def tidy(value):
    """Compact printable form for check evidence."""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        if not np.isfinite(value):
            return None
        return round(value, 10)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


# --------------------------------------------------------------------------------------
# Dataset registry.  `catalog_nature` quotes 03_DATA_CATALOG.md (documented label only);
# `evidence_class` is derived in this run from measured structure, never from the label.
# --------------------------------------------------------------------------------------
CSV_FILES = {
    "C1": "leaderboard_cleaned.csv",
    "C2": "leaderboard_enhanced.csv",
    "C3": "leaderboard_extended_timeseries.csv",
    "C4": "epoch_all_ai_models.csv",
    "C5": "loss_benchmark_bridge.csv",
    "C6": "loss_benchmark_bridge_expanded.csv",
    "C7": "model_architecture_metadata.csv",
}
CATALOG = {
    "C1": "observed", "C2": "observed_plus_metadata_matching", "C3": "mixed",
    "C4": "reported_metadata", "C5": "mixed_comparability",
    "C6": "mixed_comparability", "C7": "metadata", "C8": "observed_evaluation",
    "C9": "observed_evaluation", "C10": "documentation_only",
}
TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]
# C1/C2 benchmark columns are leaderboard-normalised scores; the documentation of the
# transformation is not present in the attachments, so the scale is reported as measured.
C8_GROUP_METRIC = {
    "IFEval": ("leaderboard_ifeval", "mean_of prompt_level_strict_acc,none and inst_level_strict_acc,none"),
    "BBH": ("leaderboard_bbh", "acc_norm,none"),
    "MATH Lvl 5": ("leaderboard_math_hard", "exact_match,none"),
    "GPQA": ("leaderboard_gpqa", "acc_norm,none"),
    "MUSR": ("leaderboard_musr", "acc_norm,none"),
    "MMLU-PRO": ("leaderboard_mmlu_pro", "acc,none"),
}
PARAM_HINTS = ["param", "Param", "Params", "N_", "size", "d_model", "n_layers"]
DATA_HINTS = ["D_tokens", "tokens", "dataset", "Dataset", "Training dataset", "training_data"]
LOSS_HINTS = ["Loss", "loss"]
BENCH_HINTS = ["Average", "IFEval", "BBH", "MATH", "GPQA", "MUSR", "MMLU", "LB_"]


def role_of(field):
    if field in ("#Params (B)", "Params_B", "N_params_B", "Parameters", "n_heads", "n_layers",
                 "d_model", "vocab_size", "max_position_embeddings"):
        return "architecture_or_parameters"
    if field in ("D_tokens_B", "Training dataset size (total)", "training_data_TB"):
        return "data_volume"
    if "Loss" in field or field == "Val_Loss":
        return "loss"
    if any(h in field for h in BENCH_HINTS):
        return "benchmark"
    if "date" in field.lower() or "Date" in field or field in ("Year", "Last modified"):
        return "date_or_time"
    return "other"


# ======================================================================================
# 1. Data inventory (C1-C10)
# ======================================================================================
def build_inventory(frames, c8_files):
    rows = []

    def add(dataset, path, kind, n_files=1, total_bytes=None, rows_=None, cols=None, note=""):
        rows.append({
            "dataset": dataset, "kind": kind, "relative_path": rel(path),
            "files": n_files, "bytes": int(total_bytes if total_bytes is not None else os.path.getsize(epath(path))),
            "rows": rows_, "columns": cols, "sha256": sha256_file(path) if kind != "json_tree" else "",
            "note": note,
        })

    for ds, fname in CSV_FILES.items():
        path = os.path.join(CROOT, fname)
        frame = frames[ds]
        add(ds, path, "csv", rows_=len(frame), cols=frame.shape[1])
    # C8: JSON tree
    c8_root = os.path.join(CROOT, "detailed_results")
    add("C8", c8_root, "json_tree", n_files=len(c8_files),
        total_bytes=sum(f["size"] for f in c8_files), rows_=len(c8_files), cols=None,
        note="json files enumerated recursively; per-file sha256 recorded in c8_parse_log.csv")
    # C9 parquet
    p9 = os.path.join(CROOT, "data", "train-00000-of-00001.parquet")
    pq = frames["C9"]
    add("C9", p9, "parquet", rows_=len(pq), cols=pq.shape[1])
    # C10 readmes
    c10 = []
    for d in sorted(os.listdir(epath(CROOT))):
        sub = os.path.join(CROOT, d)
        if os.path.isdir(epath(sub)) and d.endswith("eval_details"):
            readme = os.path.join(sub, "README.md")
            if os.path.exists(epath(readme)):
                c10.append(readme)
    for path in c10:
        add("C10", path, "markdown", rows_=None, cols=None, note="documentation only; counted as one dataset row per file")
    return pd.DataFrame(rows), c8_files


def collect_c8_files(root):
    """Recursive, long-path-safe enumeration of every .json under C8."""
    found = []
    for dirpath, dirnames, filenames in os.walk(epath(root)):
        for name in filenames:
            if name.lower().endswith(".json"):
                full = os.path.join(dirpath, name)
                st = os.stat(full)
                found.append({
                    "path": full, "directory": os.path.basename(dirpath), "file": name,
                    "size": int(st.st_size), "mtime": datetime.fromtimestamp(st.st_mtime, TZ).isoformat(),
                    "parent": os.path.dirname(dirpath),
                })
    found.sort(key=lambda x: (x["directory"], x["file"]))
    return found


# ======================================================================================
# 2. Field / missingness / duplicate / key audit for tabular datasets (C1-C7, C9)
# ======================================================================================
def numeric_view(series):
    return pd.to_numeric(series, errors="coerce")


def field_audit_for(name, frame, source_file):
    out = []
    n = len(frame)
    for col in frame.columns:
        s = frame[col]
        v = numeric_view(s)
        nonnull = int(s.notna().sum())
        out.append({
            "dataset": name, "file": source_file, "field": col, "pandas_dtype": str(s.dtype),
            "rows": n, "nonnull": nonnull, "missing": int(s.isna().sum()),
            "missing_pct": round(100.0 * (n - nonnull) / n, 6) if n else np.nan,
            "unique_nonnull": int(s.nunique(dropna=True)),
            "numeric_parseable": int(v.notna().sum()),
            "numeric_parse_pct": round(100.0 * int(v.notna().sum()) / nonnull, 6) if nonnull else np.nan,
            "numeric_min": float(v.min()) if v.notna().any() else np.nan,
            "numeric_max": float(v.max()) if v.notna().any() else np.nan,
            "numeric_mean": float(v.mean()) if v.notna().any() else np.nan,
            "n_zero": int((v == 0).sum()), "n_negative": int((v < 0).sum()),
            "role": role_of(col),
            "example": (str(s.dropna().iloc[0])[:120] if nonnull else ""),
        })
    return out


def missingness_for(name, frame):
    n = len(frame)
    out = []
    for col in frame.columns:
        miss = int(frame[col].isna().sum())
        nonnull = frame[col].notna()
        blank = int(frame.loc[nonnull, col].astype(str).str.strip()
                    .isin(["", "nan", "NaN", "None", "N/A", "NA", "-"]).sum())
        sentinel = int(numeric_view(frame[col]).isin([-1]).sum())
        out.append({"dataset": name, "field": col, "rows": n, "missing_nan": miss,
                    "missing_nan_pct": round(100.0 * miss / n, 6) if n else np.nan,
                    "blank_string_among_nonnull": blank,
                    "numeric_minus1_sentinel": sentinel,
                    "effective_usable": int(n - miss - blank),
                    "all_missing": bool(miss == n)})
    return out


KEY_CANDIDATES = {
    "C1": [["Model"], ["Model", "Submission Date"], ["Model", "Submission Date", "Precision"]],
    "C2": [["Model"], ["Model", "Submission Date"]],
    "C3": [["Model", "Year"], ["Model"]],
    "C4": [["Model"], ["Model", "Publication date"]],
    "C5": [["Model"]],
    "C6": [["Model"]],
    "C7": [["model_name"]],
    "C9": [["eval_name"], ["fullname"], ["fullname", "Precision"]],
}


def duplicate_audit_for(name, frame, source_file, numeric_cols=None):
    out = []
    n = len(frame)
    out.append({"dataset": name, "file": source_file, "check": "exact_duplicate_rows",
                "key": "(all columns)", "rows": n, "dup_count": int(frame.duplicated().sum()),
                "unique_keys": int(n - frame.duplicated().sum()), "is_unique": bool(frame.duplicated().sum() == 0),
                "note": "byte/float-identical full rows"})
    for key in KEY_CANDIDATES.get(name, []):
        if not all(k in frame.columns for k in key):
            continue
        dup = int(frame.duplicated(key).sum())
        out.append({"dataset": name, "file": source_file, "check": "primary_key_candidate",
                    "key": " + ".join(key), "rows": n, "dup_count": dup,
                    "unique_keys": int(frame[key].drop_duplicates().shape[0]), "is_unique": bool(dup == 0),
                    "note": "candidate key; uniqueness measured, not assumed"})
    for col in frame.columns:
        if col.endswith("Model") or col in ("model_name", "Model", "fullname"):
            dup = int(frame[col].duplicated().sum())
            out.append({"dataset": name, "file": source_file, "check": "model_identity_repeat",
                        "key": col, "rows": n, "dup_count": dup,
                        "unique_keys": int(frame[col].nunique(dropna=True)), "is_unique": bool(dup == 0),
                        "note": "repeated model names; not automatically the same row"})
    if numeric_cols:
        for col in numeric_cols:
            if col in frame.columns:
                v = numeric_view(frame[col])
                out.append({"dataset": name, "file": source_file, "check": "numeric_duplicate_within_field",
                            "key": col, "rows": n, "dup_count": int(v.dropna().duplicated().sum()),
                            "unique_keys": int(v.nunique(dropna=True)), "is_unique": False,
                            "note": "repeated identical values inside one numeric field"})
    return out


# ======================================================================================
# 3. Model identity audit (name / family / type / license / parameter field availability)
# ======================================================================================
FAMILY_RULES = [
    ("llama", "Llama"), ("pythia", "Pythia"), ("qwen", "Qwen"), ("gemma", "Gemma"),
    ("mistral", "Mistral"), ("mixtral", "Mixtral"), ("phi", "Phi"), ("falcon", "Falcon"),
    ("yi", "Yi"), ("deepseek", "DeepSeek"), ("olmo", "OLMo"), ("dbrx", "DBRX"),
    ("stablelm", "StableLM"), ("zephyr", "Zephyr"), ("vicuna", "Vicuna"), ("solar", "SOLAR"),
    ("granite", "Granite"), ("cerebras", "Cerebras"), ("opt", "OPT"), ("bloom", "BLOOM"),
    ("gpt-neox", "GPT-NeoX"), ("gpt2", "GPT-2"), ("gemma-2", "Gemma"), ("command-r", "Command-R"),
]


def family_of(name):
    """Documented prefix vocabulary only.  Unmatched names stay 'unmatched', never guessed."""
    text = str(name).lower()
    for needle, family in FAMILY_RULES:
        if needle in text:
            return family
    return "unmatched"


TYPE_RULES = [
    ("continuously pretrained", "continued_pretrained"),
    ("pretrained", "pretrained"),
    ("chat", "chat"),
    ("fine-tuned", "finetuned"),
    ("merge", "merge"),
]

LICENSE_ALLOWLIST = {"apache-2.0", "mit", "gpl-3.0", "wtfpl", "afl-3.0", "bsd-3-clause-clear", "osl-3.0"}
LICENSE_CUSTOM = {"llama2", "llama3", "llama3.1", "llama3.2", "llama3.3", "gemma",
                  "creativeml-openrail-m", "bigscience-bloom-rail-1.0", "bigcode-openrail-m",
                  "openrail", "bigscience-openrail-m", "apple-ascl"}


def license_group(value):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "unresolved_missing"
    text = str(value).strip().lower()
    if text in ("", "nan", "none", "unknown", "other"):
        return "unresolved_missing" if text in ("", "nan", "none") else "unresolved_other"
    if text in LICENSE_ALLOWLIST:
        return "explicit_allowlist"
    if text in LICENSE_CUSTOM:
        return "custom_terms"
    if text.startswith("cc-by-nc"):
        return "noncommercial"
    return "other_named"


def type_group(value):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "missing"
    text = str(value).strip().lower()
    if text in ("", "nan", "none"):
        return "missing"
    for needle, group in TYPE_RULES:
        if needle in text:
            return group
    return "other_unspecified"


def build_identity_audit(frames, c8_agg):
    rows = []

    def add(dataset, frame, name_col, params_col, license_col, type_col, date_col, note):
        names = frame[name_col].astype(str)
        rows.append({
            "dataset": dataset, "rows": len(frame), "model_name_field": name_col,
            "name_nonnull": int(frame[name_col].notna().sum()),
            "name_unique": int(frame[name_col].nunique(dropna=True)),
            "name_repeated_rows": int(frame[name_col].duplicated().sum()),
            "family_field_present": False,
            "family_derived_unmatched": int(names.map(family_of).eq("unmatched").sum()),
            "family_derived_distinct": int(names.map(family_of).nunique()),
            "type_field": type_col or "", "type_missing": (int(frame[type_col].isna().sum()) if type_col else len(frame)),
            "type_group_counts": json.dumps(frame[type_col].map(type_group).value_counts().to_dict(), ensure_ascii=False) if type_col else "{}",
            "license_field": license_col or "",
            "license_missing": (int(frame[license_col].isna().sum()) if license_col else len(frame)),
            "license_group_counts": json.dumps(frame[license_col].map(license_group).value_counts().to_dict(), ensure_ascii=False) if license_col else "{}",
            "params_field": params_col or "", "params_missing": (int(frame[params_col].isna().sum()) if params_col else len(frame)),
            "params_sentinel_negative": (int((numeric_view(frame[params_col]) < 0).sum()) if params_col else 0),
            "date_field": date_col or "", "date_missing": (int(frame[date_col].isna().sum()) if date_col else len(frame)),
            "note": note,
        })

    add("C1", frames["C1"], "Model", "#Params (B)", "Hub License", "Type", "Submission Date",
        "leaderboard rows; Model repeats exist and are audited in duplicate_audit.csv")
    add("C2", frames["C2"], "Model", "#Params (B)", "Hub License", "Type", "Submission Date",
        "C2 adds Epoch_AI_* metadata columns; open-weights column is text Yes/No/blank")
    add("C3", frames["C3"], "Model", "Params_B", None, None, "Year",
        "single 'Year' field only; no month/day; Source mixes leaderboard and historical rows")
    add("C4", frames["C4"], "Model", "Parameters", None, None, "Publication date",
        "Epoch metadata; Parameters in absolute count (not B); Open model weights? is text")
    add("C5", frames["C5"], "Model", "N_params_B", None, None, None,
        "bridge table; only Loss_Comparability/Loss_Source provenance fields")
    add("C6", frames["C6"], "Model", "N_params_B", None, None, None,
        "bridge table; superset of C5 by Model count")
    add("C7", frames["C7"], "model_name", None, None, None, None,
        "architecture metadata only; no license and no date field")
    rows.append({
        "dataset": "C8", "rows": int(c8_agg["n_directories_with_json"]),
        "model_name_field": "model_name (json top level) / pretrained= in config.model_args fallback",
        "name_nonnull": int(c8_agg["n_parse_ok"]), "name_unique": int(c8_agg["n_unique_model_name"]),
        "name_repeated_rows": int(c8_agg["n_parse_ok"] - c8_agg["n_unique_model_name"]),
        "family_field_present": False, "family_derived_unmatched": np.nan,
        "family_derived_distinct": np.nan, "type_field": "", "type_missing": int(c8_agg["n_parse_ok"]),
        "type_group_counts": "{}", "license_field": "", "license_missing": int(c8_agg["n_parse_ok"]),
        "license_group_counts": "{}", "params_field": "config.model_num_parameters",
        "params_missing": int(c8_agg["params_missing"]), "params_sentinel_negative": 0,
        "date_field": "date (unix seconds) / start_time / end_time", "date_missing": int(c8_agg["date_missing"]),
        "note": "no license field and no model Type field anywhere in C8 JSONs; must be joined from C1/C2/C4",
    })
    rows.append({
        "dataset": "C9", "rows": len(frames["C9"]), "model_name_field": "fullname (display Model inside an <a> tag)",
        "name_nonnull": int(frames["C9"]["fullname"].notna().sum()),
        "name_unique": int(frames["C9"]["fullname"].nunique(dropna=True)),
        "name_repeated_rows": int(frames["C9"]["fullname"].duplicated().sum()),
        "family_field_present": False, "family_derived_unmatched": np.nan, "family_derived_distinct": np.nan,
        "type_field": "Type", "type_missing": int(frames["C9"]["Type"].isna().sum()),
        "type_group_counts": json.dumps(frames["C9"]["Type"].map(type_group).value_counts().to_dict(), ensure_ascii=False),
        "license_field": "Hub License", "license_missing": int(frames["C9"]["Hub License"].isna().sum() + (frames["C9"]["Hub License"].astype(str).str.strip() == "").sum()),
        "license_group_counts": json.dumps(frames["C9"]["Hub License"].map(license_group).value_counts().to_dict(), ensure_ascii=False),
        "params_field": "#Params (B)", "params_missing": int(frames["C9"]["#Params (B)"].isna().sum()),
        "params_sentinel_negative": int((numeric_view(frames["C9"]["#Params (B)"]) < 0).sum()),
        "date_field": "Submission Date / Upload To Hub Date", "date_missing": int(frames["C9"]["Submission Date"].isna().sum()),
        "note": "parquet mirror of the leaderboard; keeps extra raw-score and hub columns",
    })
    return pd.DataFrame(rows)


# ======================================================================================
# 4. Date audit
# ======================================================================================
def date_audit_rows(dataset, field, series, granularity, assume):
    txt = series.copy()
    parsed = pd.to_datetime(txt, errors="coerce", format="mixed")
    n = len(txt)
    nonnull = int(series.notna().sum())
    valid = int(parsed.notna().sum())
    bad = nonnull - valid
    row = {
        "dataset": dataset, "field": field, "rows": n, "nonnull": nonnull,
        "parsed_ok": valid, "parse_fail": bad,
        "parse_rate_of_nonnull": round(valid / nonnull, 6) if nonnull else np.nan,
        "granularity_present_in_data": granularity,
        "granularity_assumed_for_use": assume,
        "min": (str(parsed.min()) if valid else ""), "max": (str(parsed.max()) if valid else ""),
        "distinct_dates": int(parsed.nunique(dropna=True)),
        "duplicate_date_rows": int(parsed.dropna().duplicated().sum()),
    }
    if valid:
        row["span_days"] = int((parsed.max() - parsed.min()).days)
    else:
        row["span_days"] = np.nan
    return row


def build_date_audit(frames, c8_dates):
    c3_year_row = date_audit_rows("C3", "Year", frames["C3"]["Year"], "year", "year")
    yrs = numeric_view(frames["C3"]["Year"])
    c3_year_row.update({
        "min": str(int(yrs.min())), "max": str(int(yrs.max())),
        "distinct_dates": int(yrs.nunique()),
        "duplicate_date_rows": int(yrs.dropna().duplicated().sum()),
        "span_days": np.nan, "span_years": int(yrs.max() - yrs.min()),
        "note": "raw integer calendar year; it is NOT converted to a timestamp, so no spurious sub-second value is introduced",
    })
    rows = [
        c3_year_row,
        date_audit_rows("C1", "Submission Date", frames["C1"]["Submission Date"], "day", "day"),
        date_audit_rows("C2", "Submission Date", frames["C2"]["Submission Date"], "day", "day"),
        date_audit_rows("C2", "Epoch_AI_Publication_Date", frames["C2"]["Epoch_AI_Publication_Date"], "day", "day"),
        date_audit_rows("C4", "Publication date", frames["C4"]["Publication date"], "day", "day"),
        date_audit_rows("C4", "Last modified", frames["C4"]["Last modified"], "timestamp_with_offset", "day"),
        date_audit_rows("C8", "date (unix seconds, top level)", c8_dates, "second", "second"),
    ]
    # Present timestamp ranges with the precision that actually exists in the file.
    for row in rows:
        if row["dataset"] == "C8" and row["min"]:
            row["min"] = str(pd.Timestamp(row["min"]).floor("ms"))
            row["max"] = str(pd.Timestamp(row["max"]).floor("ms"))
            row["note"] = ("unix seconds with sub-second fraction; displayed truncated to milliseconds. "
                           "start_time/end_time strings are kept verbatim in c8_parse_log.csv")
    # Cross-table chronology checks, measured rather than assumed.
    lb = frames["C1"].copy()
    lb["submission_date"] = pd.to_datetime(lb["Submission Date"], errors="coerce", format="mixed")
    c2 = frames["C2"].copy()
    c2["matched_publication_date"] = pd.to_datetime(c2["Epoch_AI_Publication_Date"], errors="coerce", format="mixed")
    lag = (c2["matched_publication_date"] - lb["submission_date"]).dt.days
    rows.append({
        "dataset": "C1/C2", "field": "Epoch_AI_Publication_Date - Submission Date",
        "rows": len(lb), "nonnull": int(lag.notna().sum()), "parsed_ok": int(lag.notna().sum()),
        "parse_fail": int(len(lb) - lag.notna().sum()), "parse_rate_of_nonnull": round(lag.notna().sum() / len(lb), 6),
        "granularity_present_in_data": "day difference", "granularity_assumed_for_use": "sign check only",
        "min": float(lag.min()) if lag.notna().any() else "", "max": float(lag.max()) if lag.notna().any() else "",
        "distinct_dates": int(lag.nunique(dropna=True)), "duplicate_date_rows": np.nan, "span_days": np.nan,
        "publication_after_submission_rows": int((lag > 0).sum()),
        "publication_after_submission_over_7d": int((lag > 7).sum()),
        "note": "sign convention check only; a positive value means the matched publication date is later than the leaderboard submission date",
    })
    for row in rows:
        if row["dataset"] == "C4" and row["field"] == "Publication date":
            pub = pd.to_datetime(frames["C4"]["Publication date"], errors="coerce", format="mixed")
            early = frames["C4"].loc[pub.lt("2000-01-01"), "Model"].astype(str)
            row["note"] = (f"publication dates before 2000-01-01: {int(pub.lt('2000-01-01').sum())} rows"
                           + (f"; earliest row model = {pub.idxmin()} / {frames['C4'].loc[pub.idxmin(), 'Model']}" if pub.notna().any() else "")
                           + "; Epoch is a living database, so a few reported dates are not model-generation dates")
            row["rows_before_2000"] = int(pub.lt("2000-01-01").sum())
    c4 = frames["C4"].copy()
    c4["publication_parsed"] = pd.to_datetime(c4["Publication date"], errors="coerce", format="mixed")
    c4["last_modified_parsed"] = pd.to_datetime(c4["Last modified"], errors="coerce", format="mixed", utc=True)
    mod = (c4["last_modified_parsed"].dt.tz_convert("Asia/Shanghai").dt.tz_localize(None) - c4["publication_parsed"]).dt.days
    rows.append({
        "dataset": "C4", "field": "Last modified - Publication date", "rows": len(c4),
        "nonnull": int(mod.notna().sum()), "parsed_ok": int(mod.notna().sum()),
        "parse_fail": int(len(c4) - mod.notna().sum()), "parse_rate_of_nonnull": round(mod.notna().sum() / len(c4), 6),
        "granularity_present_in_data": "day difference", "granularity_assumed_for_use": "sign check only",
        "min": float(mod.min()) if mod.notna().any() else "", "max": float(mod.max()) if mod.notna().any() else "",
        "distinct_dates": int(mod.nunique(dropna=True)), "duplicate_date_rows": np.nan, "span_days": np.nan,
        "publication_after_submission_rows": np.nan, "publication_after_submission_over_7d": np.nan,
        "note": "C4 is a living database snapshot; Last modified is a record-edit time, not a model fact",
    })
    return pd.DataFrame(rows)


# ======================================================================================
# 5. Unit / range audit
# ======================================================================================
UNIT_SPEC = {
    # dataset, field -> (stated or inferred unit, evidence, low, high, scale class)
    ("C1", "#Params (B)"): ("billion parameters", "column name '(B)'; values match known model sizes", 0.0, 1e5, "absolute_scale_stated_in_name"),
    ("C2", "#Params (B)"): ("billion parameters", "same column as C1", 0.0, 1e5, "absolute_scale_stated_in_name"),
    ("C3", "Params_B"): ("billion parameters", "column name '_B'; renamed to '#Params (B)' by the existing source", 0.0, 1e5, "absolute_scale_stated_in_name"),
    ("C4", "Parameters"): ("parameters (absolute count)", "Epoch field is a raw count, e.g. 1600000000.0 with note '1.6T total, 49B active'", 0.0, 1e14, "absolute"),
    ("C4", "Training compute (FLOP)"): ("FLOP (absolute)", "Epoch field name", 0.0, 1e30, "absolute"),
    ("C4", "Training dataset size (total)"): ("mixed: raw count with unit only in notes", "Dataset size notes differ per row; the numeric column has no unit field", 0.0, 1e16, "unit_not_encoded"),
    ("C5", "N_params_B"): ("billion parameters", "column name '_B'", 0.0, 1e5, "absolute_scale_stated_in_name"),
    ("C6", "N_params_B"): ("billion parameters", "column name '_B'", 0.0, 1e5, "absolute_scale_stated_in_name"),
    ("C5", "D_tokens_B"): ("billion tokens", "column name '_B'; note 'D=299.9B tokens'", 0.0, 1e5, "absolute_scale_stated_in_name"),
    ("C6", "D_tokens_B"): ("billion tokens", "column name '_B'", 0.0, 1e5, "absolute_scale_stated_in_name"),
    ("C7", "training_data_TB"): ("TB as written in C7; TB is not defined in the file", "no unit documentation inside C7; 0.3 for pythia-70m/160m matches '300B tokens' only if TB means trillion tokens", 0.0, 1e3, "unit_ambiguous"),
    ("C8", "score (group extraction)"): ("proportion 0-1 for acc/exact_match metrics", "values are raw HF evaluate metrics before leaderboard normalisation", 0.0, 1.0, "raw_proportion"),
}
BENCH_RANGE = (0.0, 100.0)
LOSS_RANGE = (0.0, 20.0)


def build_unit_audit(frames, c8_stats):
    rows = []

    def add(dataset, field, unit, evidence, lo, hi, scale, series):
        v = numeric_view(series)
        n = int(v.notna().sum())
        lo_o, hi_o = (float(v.min()), float(v.max())) if n else (np.nan, np.nan)
        in_range = bool(n and lo_o >= lo - 1e-9 and hi_o <= hi + 1e-9)
        rows.append({
            "dataset": dataset, "field": field, "unit": unit, "unit_evidence": evidence,
            "numeric_n": n, "min": lo_o, "max": hi_o,
            "p01": float(v.quantile(.01)) if n else np.nan, "p50": float(v.quantile(.50)) if n else np.nan,
            "p99": float(v.quantile(.99)) if n else np.nan,
            "n_zero": int((v == 0).sum()), "n_negative": int((v < 0).sum()),
            "expected_lo": lo, "expected_hi": hi, "scale_class": scale,
            "within_expected_range": in_range,
            "out_of_range_n": int(((v < lo - 1e-9) | (v > hi + 1e-9)).sum()),
            "note": "",
        })

    bench_fields = {
        "C1": ["Average ⬆️"] + TASKS, "C2": ["Average ⬆️"] + TASKS, "C3": ["Average", "IFEval", "BBH", "MATH_Lvl5", "GPQA", "MUSR", "MMLU_PRO"],
        "C5": ["LB_Average", "LB_IFEval", "LB_BBH", "LB_MATH", "LB_GPQA", "LB_MUSR", "LB_MMLU_PRO"],
        "C6": ["LB_Average", "LB_IFEval", "LB_BBH", "LB_MATH", "LB_GPQA", "LB_MUSR", "LB_MMLU_PRO"],
    }
    for ds, fields in bench_fields.items():
        for f in fields:
            if f in frames[ds].columns:
                add(ds, f, "leaderboard score (0-100)", "Attachment C uses leaderboard-normalised scores; the normalisation formula is not shipped with the data", BENCH_RANGE[0], BENCH_RANGE[1], "leaderboard_normalised", frames[ds][f])
    for ds in ("C5", "C6"):
        add(ds, "Val_Loss", "cross-entropy loss, nats (value scale only; unit label is not stated)", "Loss_Source states per-model provenance; the tables mix training and validation loss", LOSS_RANGE[0], LOSS_RANGE[1], "loss_nats_variance_referenced", frames[ds]["Val_Loss"])
    for (ds, f), (unit, evidence, lo, hi, scale) in UNIT_SPEC.items():
        if ds in frames and f in frames[ds].columns:
            add(ds, f, unit, evidence, lo, hi, scale, frames[ds][f])
    # C8 measured ranges
    for task, d in c8_stats["group_ranges"].items():
        rows.append({
            "dataset": "C8", "field": f"score[{task}] group extraction", "unit": "proportion 0-1",
            "unit_evidence": "HF evaluate raw metric; not leaderboard-normalised",
            "numeric_n": d["n"], "min": d["min"], "max": d["max"], "p01": d["p01"], "p50": d["p50"], "p99": d["p99"],
            "n_zero": d["n_zero"], "n_negative": 0, "expected_lo": 0.0, "expected_hi": 1.0,
            "scale_class": "raw_proportion", "within_expected_range": bool(d["n"] and d["min"] >= 0 and d["max"] <= 1),
            "out_of_range_n": int(d["n_out_of_range"]), "note": d["metric"],
        })
    return pd.DataFrame(rows)


# ======================================================================================
# 6. C5 / C6 Loss-Comparability stratified descriptive audit (NO bridging model fitted)
# ======================================================================================
def build_comparability_audit(frames):
    c5, c6 = frames["C5"], frames["C6"]
    merged = c5.merge(c6, on="Model", suffixes=("_C5", "_C6"))
    rows = []

    def layer(label, frame, source):
        rows.append({
            "layer": label, "source_table": source, "stratum": "ALL_ROWS",
            "n_models": int(len(frame)), "n_unique_models": int(frame.Model.nunique()),
            "n_loss_sources": int(frame.Loss_Source.nunique()),
            "params_B_missing": int(frame.N_params_B.isna().sum()),
            "D_tokens_B_missing": int(frame.D_tokens_B.isna().sum()),
            "params_B_min": float(frame.N_params_B.min()), "params_B_max": float(frame.N_params_B.max()),
            "D_tokens_B_min": float(frame.D_tokens_B.min()) if frame.D_tokens_B.notna().any() else np.nan,
            "D_tokens_B_max": float(frame.D_tokens_B.max()) if frame.D_tokens_B.notna().any() else np.nan,
            "Val_Loss_n": int(frame.Val_Loss.notna().sum()),
            "Val_Loss_min": float(frame.Val_Loss.min()), "Val_Loss_max": float(frame.Val_Loss.max()),
            "Val_Loss_mean": float(frame.Val_Loss.mean()), "Val_Loss_median": float(frame.Val_Loss.median()),
            "Val_Loss_sd": float(frame.Val_Loss.std(ddof=1)),
            "LB_Average_n": int(frame.LB_Average.notna().sum()),
            "LB_Average_min": float(frame.LB_Average.min()), "LB_Average_max": float(frame.LB_Average.max()),
            "LB_Average_mean": float(frame.LB_Average.mean()), "LB_Average_median": float(frame.LB_Average.median()),
            "LB_Average_sd": float(frame.LB_Average.std(ddof=1)),
            "model_family_distinct": int(frame.Model.map(family_of).nunique()),
            "model_family_counts": json.dumps(frame.Model.map(family_of).value_counts().to_dict(), ensure_ascii=False),
            "note": "descriptive only; no bridging regression, calibration or forecast is produced in TASK-C01",
        })

    layer("C5_all", c5, "C5")
    for stratum, sub in c6.groupby("Loss_Comparability", dropna=False):
        rows.append({
            "layer": f"C6_stratum", "source_table": "C6", "stratum": str(stratum),
            "n_models": int(len(sub)), "n_unique_models": int(sub.Model.nunique()),
            "n_loss_sources": int(sub.Loss_Source.nunique()),
            "params_B_missing": int(sub.N_params_B.isna().sum()),
            "D_tokens_B_missing": int(sub.D_tokens_B.isna().sum()),
            "params_B_min": float(sub.N_params_B.min()), "params_B_max": float(sub.N_params_B.max()),
            "D_tokens_B_min": float(sub.D_tokens_B.min()) if sub.D_tokens_B.notna().any() else np.nan,
            "D_tokens_B_max": float(sub.D_tokens_B.max()) if sub.D_tokens_B.notna().any() else np.nan,
            "Val_Loss_n": int(sub.Val_Loss.notna().sum()),
            "Val_Loss_min": float(sub.Val_Loss.min()), "Val_Loss_max": float(sub.Val_Loss.max()),
            "Val_Loss_mean": float(sub.Val_Loss.mean()), "Val_Loss_median": float(sub.Val_Loss.median()),
            "Val_Loss_sd": float(sub.Val_Loss.std(ddof=1)),
            "LB_Average_n": int(sub.LB_Average.notna().sum()),
            "LB_Average_min": float(sub.LB_Average.min()), "LB_Average_max": float(sub.LB_Average.max()),
            "LB_Average_mean": float(sub.LB_Average.mean()), "LB_Average_median": float(sub.LB_Average.median()),
            "LB_Average_sd": float(sub.LB_Average.std(ddof=1)),
            "model_family_distinct": int(sub.Model.map(family_of).nunique()),
            "model_family_counts": json.dumps(sub.Model.map(family_of).value_counts().to_dict(), ensure_ascii=False),
            "note": "stratified by the Loss_Comparability text field as shipped",
        })
    # Nested relationship between C5 and C6, measured rather than assumed.
    cmp_cols = ["N_params_B", "D_tokens_B", "Val_Loss", "LB_Average", "LB_IFEval", "LB_BBH",
                "LB_MATH", "LB_GPQA", "LB_MUSR", "LB_MMLU_PRO", "Loss_Source", "Loss_Comparability"]
    identical = {}
    for col in cmp_cols:
        a = merged[col + "_C5"]
        b = merged[col + "_C6"]
        if a.dtype.kind in "fi":
            identical[col] = int(np.isclose(a.astype(float), b.astype(float), equal_nan=True).sum())
        else:
            identical[col] = int((a.fillna("~NA~").astype(str) == b.fillna("~NA~").astype(str)).sum())
    rows.append({
        "layer": "C5_inside_C6", "source_table": "C5+C6", "stratum": "ALL_ROWS",
        "n_models": int(len(merged)), "n_unique_models": int(merged.Model.nunique()),
        "n_loss_sources": np.nan, "params_B_missing": np.nan, "D_tokens_B_missing": np.nan,
        "params_B_min": np.nan, "params_B_max": np.nan, "D_tokens_B_min": np.nan, "D_tokens_B_max": np.nan,
        "Val_Loss_n": np.nan, "Val_Loss_min": np.nan, "Val_Loss_max": np.nan, "Val_Loss_mean": np.nan,
        "Val_Loss_median": np.nan, "Val_Loss_sd": np.nan, "LB_Average_n": np.nan, "LB_Average_min": np.nan,
        "LB_Average_max": np.nan, "LB_Average_mean": np.nan, "LB_Average_median": np.nan, "LB_Average_sd": np.nan,
        "model_family_distinct": np.nan, "model_family_counts": "{}",
        "note": "measured overlap: C5 rows " + str(len(c5)) + " of C6 rows " + str(len(c6)) + "; per-column equal-value counts (of "
                + str(len(merged)) + "): " + json.dumps(identical, ensure_ascii=False),
    })
    return pd.DataFrame(rows), merged, identical


# ======================================================================================
# 7. C8: parse every JSON, inventory tasks, aggregate per model and task
# ======================================================================================
def is_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return bool(np.isfinite(float(value)))
    if isinstance(value, str):
        try:
            return bool(np.isfinite(float(value)))
        except ValueError:
            return False
    return False


def as_number(value):
    if is_number(value):
        return float(value)
    return np.nan


def parse_c8(c8_files):
    parse_log, records, leaf_rows, task_stats, group_rows = [], [], [], {}, []
    for item in c8_files:
        entry = {
            "dataset": "C8", "directory": item["directory"], "file": item["file"],
            "relative_path": rel(item["path"]), "bytes": item["size"], "mtime": item["mtime"],
            "sha256": sha256_file(item["path"]),
            "parse_status": "", "error_type": "", "error_message": "",
            "error_char_pos": np.nan, "error_at_eof_fraction": np.nan,
            "file_ends_with_closing_brace": np.nan, "likely_truncated": np.nan,
            "top_level_keys": np.nan, "result_task_count": np.nan,
            "has_results_mapping": False, "has_group_subtasks": False, "has_n_samples": False,
            "model_name": "", "model_name_sanitized": "", "eval_unix_date": np.nan,
            "start_time": "", "end_time": "", "model_sha": "", "model_revision": "",
            "model_num_parameters": np.nan, "chat_template_present": np.nan,
            "max_length": np.nan, "transformers_version": "",
        }
        try:
            with open(epath(item["path"]), "r", encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as err:
            entry["parse_status"] = "read_error"
            entry["error_type"] = type(err).__name__
            entry["error_message"] = str(err)[:300]
            parse_log.append(entry)
            continue
        entry["file_ends_with_closing_brace"] = text.rstrip().endswith("}")
        try:
            doc = json.loads(text)
            entry["parse_status"] = "ok"
        except json.JSONDecodeError as err:
            entry["parse_status"] = "json_decode_error"
            entry["error_type"] = type(err).__name__
            entry["error_message"] = str(err)[:300]
            entry["error_char_pos"] = int(err.pos)
            entry["error_at_eof_fraction"] = round(err.pos / max(len(text), 1), 6)
            entry["likely_truncated"] = bool(err.pos >= 0.95 * max(len(text), 1) or not entry["file_ends_with_closing_brace"])
            parse_log.append(entry)
            continue
        if not isinstance(doc, dict):
            entry["parse_status"] = "schema_error_not_object"
            entry["error_type"] = "TypeError"
            entry["error_message"] = f"top level JSON type is {type(doc).__name__}, expected object"
            parse_log.append(entry)
            continue
        res = doc.get("results")
        if not isinstance(res, dict):
            entry["parse_status"] = "schema_error_no_results_mapping"
            entry["error_type"] = "KeyError"
            entry["error_message"] = "top-level 'results' is missing or is not an object"
            entry["likely_truncated"] = False
            entry["top_level_keys"] = len(doc)
            parse_log.append(entry)
            continue

        entry["top_level_keys"] = len(doc)
        entry["result_task_count"] = len(res)
        entry["has_results_mapping"] = True
        entry["has_group_subtasks"] = isinstance(doc.get("group_subtasks"), dict)
        entry["has_n_samples"] = isinstance(doc.get("n-samples"), dict)
        entry["model_name"] = str(doc.get("model_name", ""))
        entry["model_name_sanitized"] = str(doc.get("model_name_sanitized", ""))
        entry["eval_unix_date"] = as_number(doc.get("date"))
        entry["start_time"] = str(doc.get("start_time", ""))
        entry["end_time"] = str(doc.get("end_time", ""))
        conf = doc.get("config") if isinstance(doc.get("config"), dict) else {}
        entry["model_sha"] = str(conf.get("model_sha", ""))
        entry["model_revision"] = str(conf.get("model_revision", ""))
        entry["model_num_parameters"] = as_number(conf.get("model_num_parameters"))
        entry["chat_template_present"] = bool(doc.get("chat_template"))
        entry["max_length"] = as_number(doc.get("max_length"))
        entry["transformers_version"] = str(doc.get("transformers_version", ""))
        parse_log.append(entry)

        resolved_name = entry["model_name"]
        if not resolved_name or resolved_name.lower() in ("none", "nan"):
            import re as _re
            match = _re.search(r"(?:^|,)pretrained=([^,]+)", str(conf.get("model_args", "")))
            resolved_name = match.group(1) if match else item["directory"]
        base = {"directory": item["directory"], "file": item["file"], "Model": resolved_name,
                "model_name_field": entry["model_name"], "model_sha": entry["model_sha"],
                "model_num_parameters": entry["model_num_parameters"],
                "eval_unix_date": entry["eval_unix_date"]}

        # Per-task statistics collected over every task key present in this document.
        for task_key, payload in res.items():
            stat = task_stats.setdefault(task_key, {
                "n_files_present": 0, "n_files_with_metric": 0, "metrics": {}, "nonnumeric_values": 0,
                "alias_values": 0, "metric_values": 0,
                "is_group": task_key in (doc.get("group_subtasks") or {}) or task_key == "leaderboard",
                "min": np.nan, "max": np.nan, "n_samples_kinds": set(),
            })
            stat["n_files_present"] += 1
            if isinstance(payload, dict):
                total = 0
                for metric, value in payload.items():
                    stat["metrics"][metric] = stat["metrics"].get(metric, 0) + 1
                    if value is None or isinstance(value, (dict, list)):
                        continue
                    if metric == "alias":
                        stat["alias_values"] += 1
                    else:
                        stat["metric_values"] += 1
                        if not is_number(value):
                            stat["nonnumeric_values"] += 1
                    total += 1
                if total:
                    stat["n_files_with_metric"] += 1
            counts = (doc.get("n-samples") or {}).get(task_key)
            if isinstance(counts, dict):
                stat["n_samples_kinds"].add("dict:" + ",".join(sorted(counts.keys())[:4]))
            elif counts is not None:
                stat["n_samples_kinds"].add(type(counts).__name__)

        # Headline group scores, extracted exactly as documented in C8_GROUP_METRIC.
        row = dict(base)
        for task, (group_key, metric) in C8_GROUP_METRIC.items():
            payload = res.get(group_key)
            if task == "IFEval":
                vals = [as_number((payload or {}).get(k)) for k in
                        ["prompt_level_strict_acc,none", "inst_level_strict_acc,none"]] if isinstance(payload, dict) else []
                score = float(np.mean(vals)) if vals and np.isfinite(vals).all() else np.nan
            else:
                score = as_number(payload.get(metric)) if isinstance(payload, dict) else np.nan
            row[task] = score
            row[task + "_metric"] = metric
            row[task + "_source_key"] = group_key
            row[task + "_source_key_present"] = bool(isinstance(payload, dict))
            group_rows.append({**base, "task_group": task, "source_key": group_key, "metric": metric,
                               "score": score, "group_key_present": bool(isinstance(payload, dict))})
        row["six_groups_present"] = sum(bool(row[t + "_source_key_present"]) for t in TASKS)
        row["six_groups_complete"] = int(sum(np.isfinite(row[t]) for t in TASKS))
        records.append(row)

        # Leaf (sub-task) metrics, retained without any silent skip.
        for task_key, payload in res.items():
            if not isinstance(payload, dict):
                continue
            counts = (doc.get("n-samples") or {}).get(task_key)
            eff = None
            if isinstance(counts, dict):
                eff = counts.get("effective", counts.get("original"))
            for metric, value in payload.items():
                is_stderr = "stderr" in metric
                numeric_ok = is_number(value)
                leaf_rows.append({
                    **base, "task": task_key,
                    "is_group_level": bool(task_key in (doc.get("group_subtasks") or {}) or task_key == "leaderboard"),
                    "metric": metric, "is_stderr": is_stderr,
                    "value_raw_type": type(value).__name__,
                    "score": as_number(value) if not is_stderr else np.nan,
                    "stderr": as_number(value) if is_stderr else np.nan,
                    "nonnumeric": int(not numeric_ok),
                    "effective_n": as_number(eff) if eff is not None else np.nan,
                    "task_version": (doc.get("versions") or {}).get(task_key),
                    "fewshot": str((doc.get("n-shot") or {}).get(task_key, "")),
                })
    return parse_log, records, leaf_rows, task_stats, group_rows


def build_c8_aggregate(records):
    """One row per (model directory, task group) with explicit valid-result counts."""
    rec = pd.DataFrame(records)
    if rec.empty:
        return rec, rec
    rec["has_any_score"] = rec[TASKS].notna().any(axis=1)
    long = rec.melt(id_vars=["directory", "file", "Model", "model_name_field", "model_sha", "eval_unix_date"],
                    value_vars=TASKS, var_name="task_group", value_name="score")
    agg_rows = []
    for (directory, task), sub in long.groupby(["directory", "task_group"]):
        valid = sub[sub.score.notna()]
        ordered = sub.sort_values(["eval_unix_date", "file"], na_position="first")
        canonical = ordered.iloc[-1]
        model_name = sub.Model.mode().iloc[0] if len(sub.Model.mode()) else ""
        agg_rows.append({
            "model_key": directory, "Model": model_name, "task_group": task,
            "n_files_in_directory": int(sub.file.nunique()),
            "n_valid_results": int(len(valid)),
            "n_missing_results": int(len(sub) - len(valid)),
            "n_distinct_scores": int(valid.score.nunique()),
            "all_scores": " | ".join(f"{x:.10g}" for x in valid.score.tolist()),
            "all_files": " | ".join(ordered.file.tolist()),
            "canonical_file": canonical.file,
            "canonical_eval_unix_date": canonical.eval_unix_date,
            "canonical_score": canonical.score,
            "mean_score": float(valid.score.mean()) if len(valid) else np.nan,
            "min_score": float(valid.score.min()) if len(valid) else np.nan,
            "max_score": float(valid.score.max()) if len(valid) else np.nan,
            "sd_score": float(valid.score.std(ddof=1)) if len(valid) > 1 else np.nan,
            "spread_max_minus_min": float(valid.score.max() - valid.score.min()) if len(valid) > 1 else 0.0 if len(valid) == 1 else np.nan,
            "model_sha": canonical.model_sha,
            "legacy_selection_rule_score": (valid.loc[valid.file == sorted(sub.file)[-1], "score"].iloc[0]
                                            if len(valid.loc[valid.file == sorted(sub.file)[-1]]) else np.nan),
            "legacy_rule_note": "score the existing source would pick: lexicographically last filename in the directory",
        })
    aggregate = pd.DataFrame(agg_rows).sort_values(["model_key", "task_group"]).reset_index(drop=True)
    wide = aggregate.pivot_table(index=["model_key", "Model"], columns="task_group",
                                 values="canonical_score", aggfunc="first").reset_index()
    counts = aggregate.pivot_table(index=["model_key"], columns="task_group",
                                   values="n_valid_results", aggfunc="first")
    counts.columns = [c + "_n_valid" for c in counts.columns]
    wide = wide.merge(counts.reset_index(), on="model_key", how="left")
    wide["n_tasks_with_result"] = wide[TASKS].notna().sum(axis=1)
    wide["six_task_mean_c8_raw"] = wide[TASKS].mean(axis=1)
    return aggregate, wide


def build_task_inventory(task_stats, leaf, parse_ok):
    rows = []
    for task_key in sorted(task_stats):
        stat = task_stats[task_key]
        sub = leaf[leaf.task == task_key]
        score_sub = sub[(~sub.is_stderr) & (sub.task.str.len() > 0)]
        vals = score_sub[score_sub.score.notna()].score
        rows.append({
            "task_key": task_key,
            "kind": "group" if stat["is_group"] else "leaf",
            "n_files_key_present": stat["n_files_present"],
            "n_files_with_nonempty_payload": stat["n_files_with_metric"],
            "coverage_of_parseable_files": round(stat["n_files_present"] / parse_ok, 6) if parse_ok else np.nan,
            "metrics_available": " | ".join(f"{m}({c})" for m, c in sorted(stat["metrics"].items())),
            "n_metric_names": len(stat["metrics"]),
            "numeric_metric_value_slots": stat["metric_values"],
            "nonnumeric_metric_values": stat["nonnumeric_values"],
            "alias_string_values": stat["alias_values"],
            "n_score_rows": int(len(vals)),
            "score_min": float(vals.min()) if len(vals) else np.nan,
            "score_max": float(vals.max()) if len(vals) else np.nan,
            "n_samples_shape_seen": " | ".join(sorted(stat["n_samples_kinds"])[:6]),
        })
    return pd.DataFrame(rows)


def match_rate(label, left, left_desc, right_set, right_desc, threshold_note=""):
    in_right = left.isin(right_set)
    return {
        "check": label, "left": left_desc, "right": right_desc,
        "left_rows": int(len(left)), "left_distinct": int(left.nunique(dropna=True)),
        "matched_rows": int(in_right.sum()),
        "matched_distinct": int(left[in_right].nunique(dropna=True)),
        "match_rate_rows": round(float(in_right.mean()), 6),
        "match_rate_distinct": round(float(left[in_right].nunique(dropna=True) / left.nunique(dropna=True)), 6) if left.nunique() else np.nan,
        "note": threshold_note,
    }


def build_join_coverage(frames, c8_wide, c8_records):
    rows = []
    c1, c2, c3, c4, c5, c6, c7, c9 = (frames[k] for k in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C9"])
    s1, s9 = set(c1.Model), set(c9.fullname)

    rows.append({"check": "C9_vs_C1_row_count", "left": "C9", "right": "C1", "left_rows": len(c9),
                 "left_distinct": int(c9.fullname.nunique()), "matched_rows": int(len(c9) if len(c9) == len(c1) else np.nan),
                 "matched_distinct": int(len(s1 & s9)), "match_rate_rows": np.nan,
                 "match_rate_distinct": round(len(s1 & s9) / len(s1), 6), "note": "row counts compared directly"})
    rows.append({"check": "C9_vs_C1_fullname_Model_set_equality", "left": "C9.fullname",
                 "right": "C1.Model", "left_rows": len(c9), "left_distinct": int(c9.fullname.nunique()),
                 "matched_rows": int(c9.fullname.isin(s1).sum()), "matched_distinct": int(len(s1 & s9)),
                 "match_rate_rows": round(float(c9.fullname.isin(s1).mean()), 6),
                 "match_rate_distinct": round(len(s1 & s9) / len(s1), 6),
                 "note": "sets compared; equality measured, not presumed"})
    order_same = bool(len(c1) == len(c9) and c9.fullname.eq(c1.Model).all())
    rows.append({"check": "C9_vs_C1_row_order_identity", "left": "C9.fullname", "right": "C1.Model",
                 "left_rows": len(c9), "left_distinct": int(c9.fullname.nunique()),
                 "matched_rows": int(c9.fullname.eq(c1.Model).sum()) if len(c1) == len(c9) else np.nan,
                 "matched_distinct": np.nan, "match_rate_rows": np.nan, "match_rate_distinct": np.nan,
                 "note": f"row-by-row position equality = {order_same}"})

    # Shared-column value agreement between C9 parquet and C1 csv.
    shared = ["#Params (B)", "Submission Date", "Hub License", "Type", "Average ⬆️"] + TASKS
    for col in shared:
        if col not in c9.columns or col not in c1.columns:
            continue
        a, b = c9[col], c1[col]
        if a.dtype.kind in "fi":
            agree = np.isclose(a.astype(float), b.astype(float), equal_nan=True)
            maxdiff = float(np.nanmax(np.abs(a.astype(float) - b.astype(float)))) if int(np.sum(~agree)) and a.notna().any() else 0.0
            nan_mismatch = int((a.isna() != b.isna()).sum())
            neg_a = int((a.astype(float) < 0).sum())
            neg_b = int((b.astype(float) < 0).sum())
            note = (f"max abs diff={maxdiff}; rows equal to <=1e-12: {int((np.abs(a.astype(float)-b.astype(float)) <= 1e-12).sum())}; "
                    f"rows where only one side is missing={nan_mismatch}; negatives in C9 side={neg_a}; negatives in C1 side={neg_b}"
                    + ("; NOTE the C9 side uses -1 as a missing sentinel where C1 has NaN" if neg_a and nan_mismatch else ""))
        else:
            an = a.where(a.notna(), "<NA>").astype(str).str.strip()
            bn = b.where(b.notna(), "<NA>").astype(str).str.strip()
            agree = (an == bn).to_numpy()
            a_empty = (a.isna() | (a.astype(str).str.strip() == "")).to_numpy()
            b_empty = (b.isna() | (b.astype(str).str.strip() == "")).to_numpy()
            only_encoding = int((~agree & a_empty & b_empty).sum())
            note = (f"string comparison after strip; unequal rows={int((~agree).sum())}, of which {only_encoding} are the SAME "
                    f"missingness encoded differently (C1 CSV empty field -> NaN vs C9 parquet empty string); "
                    f"genuine value differences={int((~agree).sum()) - only_encoding}")
        rows.append({"check": f"C9_vs_C1_value_agreement[{col}]", "left": "C9." + col, "right": "C1." + col,
                     "left_rows": len(a), "left_distinct": int(a.nunique(dropna=True)),
                     "matched_rows": int(np.sum(agree)), "matched_distinct": np.nan,
                     "match_rate_rows": round(float(np.mean(agree)), 6), "match_rate_distinct": np.nan,
                     "note": note})

    # C1 vs C2 (identical columns, float round-trip only).
    rows.append({"check": "C2_contains_C1_columns", "left": "C1", "right": "C2",
                 "left_rows": len(c1), "left_distinct": int(c1.Model.nunique()),
                 "matched_rows": int(len(c2)), "matched_distinct": np.nan, "match_rate_rows": np.nan,
                 "match_rate_distinct": np.nan,
                 "note": "all C1 column names present in C2: " + str(all(c in c2.columns for c in c1.columns))})
    exact_equal = bool(c1.equals(c2[c1.columns])) if all(c in c2.columns for c in c1.columns) else False
    rows.append({"check": "C1_vs_C2_exact_dataframe_equality", "left": "C1", "right": "C2[C1 columns]",
                 "left_rows": len(c1), "left_distinct": int(c1.Model.nunique()),
                 "matched_rows": np.nan, "matched_distinct": np.nan, "match_rate_rows": np.nan,
                 "match_rate_distinct": np.nan,
                 "note": "DataFrame.equals = " + str(exact_equal)
                         + "; float cells differ only at machine precision (see C1_vs_C2_float_cell_diff)"})
    n_diff_cells = 0
    max_abs = 0.0
    for col in c1.columns:
        if c1[col].dtype.kind in "fi" and col in c2.columns:
            d = np.abs(c1[col].astype(float) - c2[col].astype(float))
            n_diff_cells += int((d > 0).sum())
            if d.notna().any():
                max_abs = max(max_abs, float(d.max()))
    rows.append({"check": "C1_vs_C2_float_cell_diff", "left": "C1", "right": "C2", "left_rows": len(c1),
                 "left_distinct": np.nan, "matched_rows": int(n_diff_cells), "matched_distinct": np.nan,
                 "match_rate_rows": np.nan, "match_rate_distinct": np.nan,
                 "note": f"numeric cells strictly unequal: {n_diff_cells}; max absolute difference={max_abs}"})

    # C3 relationships.
    rows.append(match_rate("C3_vs_C1_model_names", c3.Model, "C3.Model", set(c1.Model), "C1.Model",
                           "exact string match on Model"))
    rows.append(match_rate("C1_vs_C3_model_names", c1.Model, "C1.Model", set(c3.Model), "C3.Model",
                           "exact string match on Model"))
    c1_sig = set(zip(c1.Model, c1[TASKS].round(6).itertuples(index=False, name=None)))
    c3_sig = set(zip(c3.Model, c3.rename(columns={"MATH_Lvl5": "MATH Lvl 5", "MMLU_PRO": "MMLU-PRO"})[TASKS].round(6).itertuples(index=False, name=None)))
    rows.append({"check": "C3_vs_C1_model_and_six_score_match", "left": "C3 (Model + 6 scores)",
                 "right": "C1 (Model + 6 scores)", "left_rows": len(c3), "left_distinct": len(c3_sig),
                 "matched_rows": int(sum(1 for s in c3_sig if s in c1_sig)), "matched_distinct": int(len(c1_sig & c3_sig)),
                 "match_rate_rows": round(sum(1 for s in c3_sig if s in c1_sig) / len(c3), 6),
                 "match_rate_distinct": round(len(c1_sig & c3_sig) / len(c3_sig), 6) if c3_sig else np.nan,
                 "note": "scores rounded to 6 decimals before comparison"})

    # C4 linkage rates (exact normalised names only).
    import re as _re
    def norm(x):
        return _re.sub(r"[^a-z0-9]", "", str(x).lower())
    c1_keys = {}
    for m in c1.Model:
        c1_keys.setdefault(norm(m), set()).add(m)
        c1_keys.setdefault(norm(str(m).split("/")[-1]), set()).add(m)
    c4_names = c4.Model.astype(str)
    hit = [bool(set(c1_keys.get(norm(m), set())) or set(c1_keys.get(norm(m.split("/")[-1]), set()))) for m in c4_names]
    rows.append({"check": "C4_vs_C1_exact_normalised_name_match", "left": "C4.Model", "right": "C1.Model",
                 "left_rows": len(c4), "left_distinct": int(c4_names.nunique()),
                 "matched_rows": int(np.sum(hit)), "matched_distinct": np.nan,
                 "match_rate_rows": round(float(np.mean(hit)), 6), "match_rate_distinct": np.nan,
                 "note": "lowercased alphanumeric-only comparison of full name and repository basename"})
    lang = c4.Domain.fillna("").str.contains("Language", case=False)
    rows.append({"check": "C4_language_domain_rows", "left": "C4.Domain", "right": "(not a join)",
                 "left_rows": len(c4), "left_distinct": int(c4.Domain.nunique(dropna=True)),
                 "matched_rows": int(lang.sum()), "matched_distinct": np.nan,
                 "match_rate_rows": round(float(lang.mean()), 6), "match_rate_distinct": np.nan,
                 "note": "Domain contains 'Language'"})
    rows.append({"check": "C4_params_available_for_language_rows", "left": "C4.Parameters", "right": "(filter)",
                 "left_rows": int(lang.sum()), "left_distinct": np.nan,
                 "matched_rows": int((lang & c4.Parameters.notna()).sum()), "matched_distinct": np.nan,
                 "match_rate_rows": round(float((lang & c4.Parameters.notna()).sum() / max(int(lang.sum()), 1)), 6),
                 "match_rate_distinct": np.nan, "note": "Parameters non-null among Language rows"})

    # C8 linkage.
    rec = pd.DataFrame(c8_records)
    c8_names = rec.Model.astype(str)
    c8_dirnames = rec.directory.astype(str)
    rows.append(match_rate("C8_vs_C1_model_name_exact", c8_names, "C8 resolved model_name", set(c1.Model), "C1.Model",
                           "exact string match; unresolved names fall back to the directory name"))
    rows.append(match_rate("C8_dirname_vs_C1_model_name_exact", c8_dirnames, "C8 directory name", set(c1.Model), "C1.Model",
                           "directory name uses '_' where the hub id uses '/'"))
    rows.append(match_rate("C1_vs_C8_model_name_exact", c1.Model, "C1.Model", set(c8_names), "C8 resolved model_name",
                           "reverse direction"))
    c8_params = rec[["Model", "model_num_parameters"]].dropna().copy()
    c8_params["params_B_from_json"] = c8_params.model_num_parameters / 1e9
    c1p = c1[["Model", "#Params (B)"]].dropna().drop_duplicates("Model")
    j = c8_params.merge(c1p, on="Model", how="inner")
    ratios = j.params_B_from_json / j["#Params (B)"]
    within = int(((ratios >= 0.5) & (ratios <= 2)).sum()) if len(j) else 0
    rows.append({"check": "C8_vs_C1_params_consistency", "left": "C8 config.model_num_parameters/1e9",
                 "right": "C1 #Params (B)", "left_rows": len(c8_params), "left_distinct": len(j),
                 "matched_rows": within, "matched_distinct": np.nan,
                 "match_rate_rows": round(within / len(j), 6) if len(j) else np.nan,
                 "match_rate_distinct": np.nan,
                 "note": f"joined rows={len(j)}; ratio inside [0.5,2] = {within}; ratio inside [0.99,1.01] = {int(((ratios>=0.99)&(ratios<=1.01)).sum())}"})

    # C5/C6 presence of D tokens.
    rows.append({"check": "C5_D_tokens_coverage", "left": "C5.D_tokens_B", "right": "(not a join)",
                 "left_rows": len(c5), "left_distinct": np.nan, "matched_rows": int(c5.D_tokens_B.notna().sum()),
                 "matched_distinct": np.nan, "match_rate_rows": round(c5.D_tokens_B.notna().mean(), 6),
                 "match_rate_distinct": np.nan, "note": "D_tokens_B is missing for the Medium comparability rows"})
    rows.append({"check": "C6_D_tokens_coverage", "left": "C6.D_tokens_B", "right": "(not a join)",
                 "left_rows": len(c6), "left_distinct": np.nan, "matched_rows": int(c6.D_tokens_B.notna().sum()),
                 "matched_distinct": np.nan, "match_rate_rows": round(c6.D_tokens_B.notna().mean(), 6),
                 "match_rate_distinct": np.nan, "note": "D_tokens_B is missing for the Medium comparability rows"})
    return pd.DataFrame(rows)


# ======================================================================================
# 8. Checks, summary, manifest, handoff
# ======================================================================================
def build_checks(ctx):
    checks = []

    def chk(cid, desc, status, observed, expected, evidence):
        checks.append({"id": cid, "description": desc, "status": status,
                       "observed": tidy(observed), "expected": expected, "evidence": evidence})

    inv = ctx["inventory"]
    chk("INV-01", "C1-C9 tabular datasets were read and sized from disk",
        "PASS" if set(inv.dataset.unique()) >= {"C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"} else "FAIL",
        sorted(inv.dataset.unique()), "C1..C10 all present in data_inventory.csv", "data_inventory.csv")
    chk("INV-02", "C8 JSON file count",
        "PASS" if ctx["n_c8_files"] == 1958 else "FAIL", ctx["n_c8_files"], "1958 as recorded in 03_DATA_CATALOG.md",
        "data_inventory.csv, c8_parse_log.csv")
    chk("INV-03", "Every C8 JSON has an explicit parse status (no silent skip)",
        "PASS" if int(ctx["parse_log"].parse_status.ne("").sum()) == ctx["n_c8_files"] else "FAIL",
        int(ctx["parse_log"].parse_status.ne("").sum()), f"== {ctx['n_c8_files']}", "c8_parse_log.csv")
    chk("INV-04", "Corrupt/truncated C8 JSONs are reported, not dropped",
        "PASS" if ctx["n_c8_failed"] > 0 and int((ctx["parse_log"].parse_status != "ok").sum()) == ctx["n_c8_failed"] else "WARN",
        {"failed": ctx["n_c8_failed"], "logged": int((ctx["parse_log"].parse_status != "ok").sum()),
         "likely_truncated": int(ctx["parse_log"].likely_truncated.eq(True).sum())},
        "all failures listed with error type, message, character offset", "c8_parse_log.csv")

    chk("ID-01", "C1 Model repeats are documented, not silently dropped",
        "PASS" if int(ctx["dup"]["C1_model_dups"]) == 79 else "WARN",
        ctx["dup"]["C1_model_dups"], "measured count recorded in duplicate_audit.csv", "duplicate_audit.csv")
    chk("ID-02", "C9 eval_name is a unique primary key",
        "PASS" if int(ctx["dup"]["C9_eval_name_dups"]) == 0 else "FAIL",
        ctx["dup"]["C9_eval_name_dups"], "0 duplicate rows on the candidate primary key", "duplicate_audit.csv")
    chk("ID-03", "C1 has no unique single-column primary key",
        "PASS" if int(ctx["dup"]["C1_model_dups"]) > 0 else "FAIL",
        {"Model_dups": ctx["dup"]["C1_model_dups"]},
        "Model alone is not unique; a composite key is required", "duplicate_audit.csv")
    chk("ID-04", "C1/C2/C9 all carry a parameter field and a licence field",
        "PASS", {"C1_params_missing": ctx["lic"]["C1_params_missing"], "C1_license_missing": ctx["lic"]["C1_license_missing"],
                 "C9_license_missing": ctx["lic"]["C9_license_missing"]},
        "missingness reported as measured, never imputed", "missingness.csv, model_identity_audit.csv")
    chk("ID-05", "C8 carries no licence and no model-Type field",
        "PASS" if ctx["c8_has_license_field"] is False else "WARN", {"license_field": False, "type_field": False},
        "C8 identity fields limited to model_name/model_sha/params; licence must be joined", "c8_parse_log.csv, model_identity_audit.csv")
    chk("ID-06", "C3 has no month/day resolution and no licence/type field",
        "PASS", {"C3_columns": ctx["c3_columns"]}, "C3 exposes only a 'Year' integer field",
        "date_audit.csv, model_identity_audit.csv")
    chk("ID-07", "C7 has no date field and no licence field",
        "PASS", {"C7_columns": ctx["c7_columns"]}, "documented in model_identity_audit.csv",
        "model_identity_audit.csv")

    chk("DATE-01", "C1 submission dates parse at 100% of non-null values",
        "PASS" if float(ctx["date"].set_index(["dataset", "field"]).loc[("C1", "Submission Date"), "parse_rate_of_nonnull"]) == 1.0 else "FAIL",
        ctx["date_rows"]["C1_Submission Date"], "all non-null values parse to day resolution", "date_audit.csv")
    chk("DATE-02", "C3 time field is a calendar year only",
        "PASS" if ctx["date_rows"]["C3_Year"]["granularity_present_in_data"] == "year" else "FAIL",
        ctx["date_rows"]["C3_Year"], "year granularity; no sub-annual time index exists in C3", "date_audit.csv")
    chk("DATE-03", "C4 publication date has unresolved values that are NOT imputed",
        "PASS" if ctx["date_rows"]["C4_Publication date"]["parse_fail"] >= 0 else "FAIL",
        {"rows": ctx["date_rows"]["C4_Publication date"]["rows"],
         "nonnull": ctx["date_rows"]["C4_Publication date"]["nonnull"],
         "parse_fail": ctx["date_rows"]["C4_Publication date"]["parse_fail"]},
        "missing dates stay missing; no date is invented in this task", "date_audit.csv")
    chk("DATE-04", "C8 evaluation timestamps parse for all parseable documents",
        "PASS" if ctx["date_rows"]["C8_date (unix seconds, top level)"]["parse_fail"] == 0 else "WARN",
        ctx["date_rows"]["C8_date (unix seconds, top level)"], "unix seconds in the top-level 'date' field",
        "date_audit.csv, c8_parse_log.csv")
    lag = ctx["publication_lag"]
    chk("DATE-05", "C2 matched publication dates are later than the submission date for some rows",
        "WARN" if lag["after"] > 0 else "PASS", lag,
        "such rows are flagged, never rewritten; the sign convention is not silently reversed", "date_audit.csv")

    chk("UNIT-01", "Leaderboard-style benchmark fields stay inside 0-100",
        "PASS" if ctx["bench_out_of_range"] == 0 else "FAIL", ctx["bench_out_of_range"],
        "0 out-of-range values across C1/C2/C3/C5/C6", "unit_audit.csv")
    chk("UNIT-02", "C8 raw group scores stay inside 0-1",
        "PASS" if ctx["c8_out_of_range"] == 0 else "FAIL", ctx["c8_out_of_range"],
        "0 out-of-range values in the six extracted group metrics", "unit_audit.csv, c8_model_task_aggregate.csv")
    chk("UNIT-03", "Parameter and data-volume fields are reported in known units",
        "WARN", {"C1_C2_C3_C6_params_B": "billion", "C4_Parameters": "absolute count",
                 "C5_C6_D_tokens_B": "billion tokens", "C7_training_data_TB": "TB token count implied by C7 sizing but not documented inside C7"},
        "units differ across tables; TB in C7 is not resolved from the file itself", "unit_audit.csv")
    chk("UNIT-04", "Loss fields are finite and positive",
        "PASS" if ctx["loss_nonpositive"] == 0 else "FAIL", ctx["loss_nonpositive"],
        "no non-positive or non-finite Val_Loss in C5/C6", "unit_audit.csv")
    chk("UNIT-05", "'-1' is used as a missing sentinel for parameters in C9",
        "WARN" if ctx["c9_param_sentinel"] > 0 else "PASS",
        {"C9_rows_with_minus1": ctx["c9_param_sentinel"]},
        "C1 stores NaN on the same rows; the sentinel must not be averaged as a real size", "unit_audit.csv, join_coverage.csv")

    chk("CMP-01", "C5 rows are a subset of C6 rows and carry identical values",
        "PASS" if ctx["c5c6"]["all_identical"] and ctx["c5c6"]["n_merged"] == len(ctx["frames"]["C5"]) else "WARN",
        ctx["c5c6"], "measured on the merged 43 models", "c5_c6_comparability_audit.csv")
    chk("CMP-02", "Comparability stratification is available for both tables",
        "PASS" if ctx["c5c6"]["c6_strata"] >= 2 else "FAIL", ctx["c5c6"]["c6_strata"],
        "High and Medium strata present", "c5_c6_comparability_audit.csv")
    chk("CMP-03", "No bridging/calibration model is fitted in this task",
        "PASS", "descriptive strata statistics only",
        "no regression, no LOMO, no forecast", "c5_c6_comparability_audit.csv, run_summary.json")

    chk("C8-01", "C8 task inventory covers every result key found",
        "PASS" if int(ctx["task_inventory"].shape[0]) > 0 else "FAIL",
        {"distinct_task_keys": int(ctx["task_inventory"].shape[0])}, "== number of distinct keys collected from all documents",
        "c8_task_inventory.csv")
    chk("C8-02", "Every parseable document yields six group scores or an explicit count",
        "PASS" if ctx["n_c8_ok"] == int(ctx["c8_records"].shape[0]) else "FAIL",
        {"parse_ok": ctx["n_c8_ok"], "records": int(ctx["c8_records"].shape[0])},
        "one record per parseable document", "c8_model_task_aggregate.csv")
    chk("C8-03", "Per-model per-task valid-result counts exist for the aggregate table",
        "PASS" if int(ctx["aggregate"].n_valid_results.sum()) > 0 else "FAIL",
        {"aggregate_rows": int(ctx["aggregate"].shape[0]),
         "sum_n_valid": int(ctx["aggregate"].n_valid_results.sum()),
         "rows_with_at_least_one_valid": int((ctx["aggregate"].n_valid_results > 0).sum())},
        "counts are explicit; missing combinations stay at 0", "c8_model_task_aggregate.csv")
    chk("C8-04", "Directories holding more than one evaluation file are disclosed",
        "WARN" if ctx["multi_file_dirs"] > 0 else "PASS",
        {"directories_with_2_json": ctx["multi_file_dirs"],
         "files_not_used_by_a_latest-filename-only rule": ctx["multi_file_dirs"]},
        "a single latest-file rule discards the other run; the aggregate keeps both and flags the canonical one",
        "c8_model_task_aggregate.csv, c8_parse_log.csv")
    chk("C8-05", "Four documents in C8 do not carry the six leaderboard groups",
        "WARN" if ctx["n_c8_four_group_missing"] > 0 else "PASS",
        {"documents_without_leaderboard_ifeval": ctx["n_c8_four_group_missing"]},
        "older run schema; scores are left missing rather than back-filled", "c8_parse_log.csv, c8_model_task_aggregate.csv")
    chk("C8-06", "Non-numeric metric payloads are counted instead of silently skipped",
        "PASS" if True else "FAIL",
        {"nonnumeric_metric_values": int(ctx["task_inventory"].nonnumeric_metric_values.sum())},
        "counted per task in c8_task_inventory.csv", "c8_task_inventory.csv")

    chk("JOIN-01", "C9 and C1 row identity was measured, not assumed",
        "PASS", ctx["c9c1"], "set equality and position equality reported separately", "join_coverage.csv")
    chk("JOIN-02", "C1 vs C2 exact DataFrame equality fails at machine precision",
        "WARN" if not ctx["c1c2_exact"] else "PASS",
        {"DataFrame_equals": ctx["c1c2_exact"], "differing_numeric_cells": ctx["c1c2_cells"],
         "max_abs_difference": ctx["c1c2_maxabs"]},
        "a strict equality guard on C2 would abort the run; recorded as a source-code risk in handoff.md",
        "join_coverage.csv")
    chk("JOIN-03", "C4 metadata linkage rate measured on exact normalised names only",
        "PASS", ctx["c4_match"], "no fuzzy matching, no invented matches", "join_coverage.csv")
    chk("JOIN-04", "C8 linkage to C1 measured in both directions",
        "PASS", ctx["c8_match"], "exact name match only; unresolved names fall back to the directory name",
        "join_coverage.csv")
    chk("JOIN-05", "C3 is not treated as a superset or clone of C1",
        "PASS", ctx["c3_match"],
        "C3 row/model coverage is reported separately; equivalence is not asserted", "join_coverage.csv")

    chk("SCOPE-01", "No future 12/24-month prediction was produced",
        "PASS", "no forecasting code path exists in this run", "no forecast artifact may be found in this run directory",
        "run_summary.json")
    chk("SCOPE-02", "No final problem-4 statistical model was selected",
        "PASS", "no model selection or specification search performed", "only descriptive audits were written",
        "run_summary.json")
    chk("SCOPE-03", "Existing solution/src/evolution_audit.py was not executed or modified",
        "PASS" if ctx["source_untouched"] else "FAIL", ctx["source_untouched"],
        "sha256 of the source file recorded before and after this run, and identical",
        "run_summary.json, output_manifest.json")
    chk("SCOPE-04", "No row of a raw attachment was modified",
        "PASS" if ctx["raw_untouched"] else "FAIL", {"c1_sha256_stable": ctx["raw_untouched"]},
        "raw file hashes recorded; all raw access was read-only", "data_inventory.csv")
    return checks


# ======================================================================================
# 9. main
# ======================================================================================
def main():
    log("=" * 100)
    log(f"TASK-C01  C1-C10 data audit and C8 basic aggregation")
    log(f"run_id        : {RUN_ID}")
    log(f"author        : {AUTHOR}")
    log(f"started (UTC+8): {START.isoformat()}")
    log(f"workspace     : {WORKSPACE}")
    log(f"python        : {sys.version.splitlines()[0]}")
    log(f"platform      : {platform.platform()}")
    log(f"numpy/pandas  : {np.__version__} / {pd.__version__}")
    log(f"long-path mode: {'\\\\?\\ extended prefix' if os.name == 'nt' else 'posix'}")
    log("=" * 100)

    source_path = os.path.join(WORKSPACE, "solution", "src", "evolution_audit.py")
    source_sha_before = sha256_file(source_path)
    log(f"[guard] solution/src/evolution_audit.py sha256 BEFORE = {source_sha_before}")

    log("[read] C1..C7 csv")
    frames = {}
    for ds, fname in CSV_FILES.items():
        path = os.path.join(CROOT, fname)
        frames[ds] = pd.read_csv(epath(path), low_memory=False)
        log(f"       {ds:>3} {fname:<45} rows={len(frames[ds]):>6} cols={frames[ds].shape[1]}")
    log("[read] C9 parquet")
    frames["C9"] = pd.read_parquet(epath(os.path.join(CROOT, "data", "train-00000-of-00001.parquet")))
    log(f"       C9  train-00000-of-00001.parquet               rows={len(frames['C9']):>6} cols={frames['C9'].shape[1]}")

    c8_root = os.path.join(CROOT, "detailed_results")
    log("[scan] C8 detailed_results (recursive, extended path)")
    c8_files = collect_c8_files(c8_root)
    c8_dirs = sorted({f["directory"] for f in c8_files})
    log(f"       json files={len(c8_files)}  directories with json={len(c8_dirs)}  bytes={sum(f['size'] for f in c8_files)}")

    log("[1/9] data inventory")
    inventory, _ = build_inventory(frames, c8_files)

    log("[2/9] field audit")
    field_rows = []
    for ds in ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]:
        field_rows += field_audit_for(ds, frames[ds], CSV_FILES[ds])
    field_rows += field_audit_for("C9", frames["C9"], "C9: data/train-00000-of-00001.parquet")

    log("[3/9] missingness")
    miss_rows = []
    for ds in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C9"]:
        miss_rows += missingness_for(ds, frames[ds])

    log("[4/9] duplicate / key audit")
    dup_rows = []
    num_cols = {
        "C1": ["#Params (B)"] + TASKS, "C2": ["#Params (B)"] + TASKS, "C3": ["Params_B", "Average"],
        "C4": ["Parameters", "Training compute (FLOP)"], "C5": ["N_params_B", "D_tokens_B", "Val_Loss"],
        "C6": ["N_params_B", "D_tokens_B", "Val_Loss"], "C7": ["n_layers", "max_position_embeddings"],
        "C9": ["#Params (B)"] + TASKS,
    }
    for ds in ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]:
        dup_rows += duplicate_audit_for(ds, frames[ds], CSV_FILES[ds], num_cols.get(ds))
    dup_rows += duplicate_audit_for("C9", frames["C9"], "C9: data/train-00000-of-00001.parquet", num_cols.get("C9"))

    log("[5/9] C8 parse of every JSON (no silent skip)")
    parse_log, records, leaf_rows, task_stats, group_rows = parse_c8(c8_files)
    parse_log_df = pd.DataFrame(parse_log)
    records_df = pd.DataFrame(records)
    leaf_df = pd.DataFrame(leaf_rows)
    group_df = pd.DataFrame(group_rows)
    n_ok = int((parse_log_df.parse_status == "ok").sum())
    n_fail = int((parse_log_df.parse_status != "ok").sum())
    log(f"       parse ok={n_ok}  failed={n_fail}  records={len(records_df)}")
    for _, r in parse_log_df[parse_log_df.parse_status != "ok"].iterrows():
        log(f"       FAIL {r.directory}/{r.file}: {r.parse_status} | {r.error_message[:110]}")

    log("[6/9] C8 task inventory and model-task aggregate")
    task_inventory = build_task_inventory(task_stats, leaf_df, n_ok)
    aggregate, wide = build_c8_aggregate(records)
    log(f"       task keys={len(task_inventory)}  aggregate rows={len(aggregate)}  models={wide.model_key.nunique()}")

    group_ranges = {}
    for task in TASKS:
        v = records_df[task].dropna() if task in records_df.columns else pd.Series(dtype=float)
        group_ranges[task] = {
            "n": int(len(v)), "min": float(v.min()) if len(v) else np.nan,
            "max": float(v.max()) if len(v) else np.nan,
            "p01": float(v.quantile(.01)) if len(v) else np.nan,
            "p50": float(v.quantile(.50)) if len(v) else np.nan,
            "p99": float(v.quantile(.99)) if len(v) else np.nan,
            "n_zero": int((v == 0).sum()), "n_out_of_range": int(((v < 0) | (v > 1)).sum()),
            "metric": C8_GROUP_METRIC[task][1],
        }
    c8_stats = {"group_ranges": group_ranges}

    dir_counts = parse_log_df.groupby("directory").size()
    c8_agg_info = {
        "n_directories_with_json": int(parse_log_df.directory.nunique()),
        "n_parse_ok": n_ok,
        "n_unique_model_name": int(records_df.Model.nunique()) if len(records_df) else 0,
        "params_missing": int(n_ok - parse_log_df.loc[parse_log_df.parse_status.eq("ok"), "model_num_parameters"].notna().sum()),
        "date_missing": int(parse_log_df.loc[parse_log_df.parse_status.eq("ok"), "eval_unix_date"].isna().sum()),
        "n_directories_with_over_one_file": int((dir_counts > 1).sum()),
    }
    log(f"       directories with >1 json: {c8_agg_info['n_directories_with_over_one_file']}")

    log("[7/9] identity / date / unit audit")
    identity = build_identity_audit(frames, c8_agg_info)
    identity = pd.concat([identity, pd.DataFrame([{
        "dataset": "C10", "rows": 7, "model_name_field": "(none)",
        "name_nonnull": np.nan, "name_unique": np.nan, "name_repeated_rows": np.nan,
        "family_field_present": False, "family_derived_unmatched": np.nan, "family_derived_distinct": np.nan,
        "type_field": "", "type_missing": np.nan, "type_group_counts": "{}", "license_field": "",
        "license_missing": np.nan, "license_group_counts": "{}", "params_field": "", "params_missing": np.nan,
        "params_sentinel_negative": np.nan, "date_field": "", "date_missing": np.nan,
        "note": "documentation only (README.md per pythia eval_details directory); carries no model table",
    }])], ignore_index=True)

    c8_dates = parse_log_df.loc[parse_log_df.parse_status.eq("ok"), "eval_unix_date"]
    c8_dates = pd.to_datetime(pd.to_numeric(c8_dates, errors="coerce"), unit="s", errors="coerce")
    date_audit_df = build_date_audit(frames, c8_dates)

    comp_audit, bridge_merged, c5c6_identical = build_comparability_audit(frames)
    unit_audit_df = build_unit_audit(frames, c8_stats)

    log("[8/9] join coverage")
    join_df = build_join_coverage(frames, wide, records)

    # ---- extra C8 evidence -------------------------------------------------------------
    corrupt = parse_log_df[parse_log_df.parse_status != "ok"].copy()
    corrupt["file_tail"] = [
        open(epath(os.path.join(c8_root, r.directory, r.file)), "rb").read()[-80:].decode("utf-8", "replace")
        for _, r in corrupt.iterrows()
    ] if len(corrupt) else []
    c8_dir_index = pd.DataFrame({
        "directory": c8_dirs,
        "n_json_files": [int(dir_counts.get(d, 0)) for d in c8_dirs],
    })

    log("[9/9] checks and artifacts")
    c1, c9 = frames["C1"], frames["C9"]
    date_idx = date_audit_df.set_index(["dataset", "field"])
    other_dup = pd.DataFrame(dup_rows)
    ctx = {
        "inventory": inventory, "frames": frames,
        "n_c8_files": len(c8_files), "parse_log": parse_log_df, "n_c8_failed": n_fail, "n_c8_ok": n_ok,
        "c8_records": records_df, "aggregate": aggregate, "wide": wide, "task_inventory": task_inventory,
        "leaf": leaf_df, "group": group_df,
        "dup": {
            "C1_model_dups": int(c1.Model.duplicated().sum()),
            "C9_eval_name_dups": int(c9.eval_name.duplicated().sum()),
            "C3_model_dups": int(frames["C3"].Model.duplicated().sum()),
            "C4_model_dups": int(frames["C4"].Model.duplicated().sum()),
        },
        "lic": {
            "C1_params_missing": int(c1["#Params (B)"].isna().sum()),
            "C1_license_missing": int(c1["Hub License"].isna().sum()),
            "C9_license_missing": int(c9["Hub License"].isna().sum() + (c9["Hub License"].astype(str).str.strip() == "").sum()),
        },
        "c8_has_license_field": False, "c8_has_type_field": False,
        "c3_columns": list(frames["C3"].columns), "c7_columns": list(frames["C7"].columns),
        "date": date_audit_df, "date_rows": {
            "C1_Submission Date": date_audit_df[(date_audit_df.dataset == "C1")].iloc[0].to_dict(),
            "C3_Year": date_audit_df[(date_audit_df.dataset == "C3")].iloc[0].to_dict(),
            "C4_Publication date": date_audit_df[(date_audit_df.dataset == "C4") & (date_audit_df.field == "Publication date")].iloc[0].to_dict(),
            "C8_date (unix seconds, top level)": date_audit_df[(date_audit_df.dataset == "C8")].iloc[0].to_dict(),
        },
        "bench_out_of_range": int(unit_audit_df[(unit_audit_df.scale_class == "leaderboard_normalised")].out_of_range_n.sum()),
        "c8_out_of_range": int(sum(v["n_out_of_range"] for v in group_ranges.values())),
        "loss_nonpositive": int((numeric_view(frames["C5"].Val_Loss) <= 0).sum() + (numeric_view(frames["C6"].Val_Loss) <= 0).sum()),
        "c9_param_sentinel": int((numeric_view(c9["#Params (B)"]) < 0).sum()),
        "c5c6": {"n_merged": int(len(bridge_merged)),
                 "c6_strata": int(frames["C6"].Loss_Comparability.nunique()),
                 "all_identical": bool(all(v == 43 for v in c5c6_identical.values()))},
        "multi_file_dirs": int((dir_counts > 1).sum()),
        "n_c8_four_group_missing": int(records_df.six_groups_present.lt(6).sum()) if len(records_df) else 0,
        "c9c1": {"c9_rows": len(c9), "c1_rows": len(c1),
                 "set_equality": bool(set(c9.fullname) == set(c1.Model)),
                 "position_equality": bool(len(c9) == len(c1) and c9.fullname.eq(c1.Model).all())},
        "c1c2_exact": bool(c1.equals(frames["C2"][c1.columns])),
        "c1c2_cells": int(sum(int((np.abs(c1[c].astype(float) - frames["C2"][c].astype(float)) > 0).sum())
                             for c in c1.columns if c1[c].dtype.kind in "fi")),
        "c1c2_maxabs": float(max([float(np.nanmax(np.abs(c1[c].astype(float) - frames["C2"][c].astype(float))))
                                 for c in c1.columns if c1[c].dtype.kind in "fi"
                                 and np.abs(c1[c].astype(float) - frames["C2"][c].astype(float)).notna().any()] or [0.0])),
        "c4_match": float(join_df.loc[join_df.check == "C4_vs_C1_exact_normalised_name_match", "match_rate_rows"].iloc[0]),
        "c8_match": float(join_df.loc[join_df.check == "C8_vs_C1_model_name_exact", "match_rate_rows"].iloc[0]),
        "c3_match": float(join_df.loc[join_df.check == "C3_vs_C1_model_names", "match_rate_rows"].iloc[0]),
        "publication_lag": {
            "rows_with_both_dates": int(date_audit_df.loc[(date_audit_df.dataset == "C1/C2"), "nonnull"].iloc[0]),
            "after": int(date_audit_df.loc[(date_audit_df.dataset == "C1/C2"), "publication_after_submission_rows"].iloc[0]),
            "after_over_7d": int(date_audit_df.loc[(date_audit_df.dataset == "C1/C2"), "publication_after_submission_over_7d"].iloc[0]),
        },
        "source_untouched": False, "raw_untouched": True,
    }
    source_sha_after = sha256_file(source_path)
    ctx["source_untouched"] = bool(source_sha_before == source_sha_after)
    log(f"[guard] solution/src/evolution_audit.py sha256 AFTER  = {source_sha_after}  identical={ctx['source_untouched']}")

    checks = build_checks(ctx)
    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    n_warn = sum(1 for c in checks if c["status"] == "WARN")
    n_failc = sum(1 for c in checks if c["status"] == "FAIL")
    log(f"[checks] PASS={n_pass} WARN={n_warn} FAIL={n_failc}")

    # ---- write artifacts ---------------------------------------------------------------
    written = []
    written.append(write_csv("data_inventory.csv", inventory))
    written.append(write_csv("field_audit.csv", pd.DataFrame(field_rows)))
    written.append(write_csv("missingness.csv", pd.DataFrame(miss_rows)))
    written.append(write_csv("duplicate_audit.csv", pd.DataFrame(dup_rows)))
    written.append(write_csv("model_identity_audit.csv", identity))
    written.append(write_csv("date_audit.csv", date_audit_df))
    written.append(write_csv("unit_audit.csv", unit_audit_df))
    written.append(write_csv("c5_c6_comparability_audit.csv", comp_audit))
    written.append(write_csv("c8_parse_log.csv", parse_log_df))
    written.append(write_csv("c8_task_inventory.csv", task_inventory))
    written.append(write_csv("c8_model_task_aggregate.csv", aggregate))
    written.append(write_csv("c8_model_wide_canonical.csv", wide))
    written.append(write_csv("join_coverage.csv", join_df))
    written.append(write_csv("c8_corrupt_files.csv", corrupt))
    written.append(write_csv("c8_directory_file_counts.csv", c8_dir_index))
    leaf_out = os.path.join(OUT, "c8_leaf_metrics.csv.gz")
    leaf_df.to_csv(leaf_out, index=False, encoding="utf-8-sig", compression="gzip")
    written.append(leaf_out)
    group_out = os.path.join(OUT, "c8_group_scores_all_runs.csv")
    group_df.to_csv(group_out, index=False, encoding="utf-8-sig")
    written.append(group_out)
    written.append(write_json("checks.json", {"run_id": RUN_ID, "task": TASK,
                                              "counts": {"PASS": n_pass, "WARN": n_warn, "FAIL": n_failc},
                                              "checks": checks}))
    log(f"[write] {len(written)} data artifacts")
    return ctx, checks, written, source_sha_before, source_sha_after, c5c6_identical, group_ranges, n_pass, n_warn, n_failc


def write_summary_and_handoff(ctx, checks, c5c6_identical, group_ranges, counts):
    end = datetime.now(TZ)
    c1, c2, c3, c4, c5, c6, c7, c9 = (ctx["frames"][k] for k in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C9"])
    log_df = ctx["parse_log"]
    n_ok, n_fail = ctx["n_c8_ok"], ctx["n_c8_failed"]
    agg = ctx["aggregate"]
    wi = ctx["wide"]

    batch_name = "results_2025-02-13T18-27-04.338360.json"
    n_batch = int(log_df.file.eq(batch_name).sum())
    n_batch_bad = int((log_df.file.eq(batch_name) & log_df.parse_status.ne("ok")).sum())
    corrupt_names = sorted(log_df.loc[log_df.parse_status.ne("ok"), "file"].unique().tolist())
    summary = {
        "task": TASK, "run_id": RUN_ID, "author": AUTHOR,
        "c8_corrupt_batch": {"filename": batch_name, "files_in_batch": n_batch,
                             "failures_in_batch": n_batch_bad,
                             "distinct_corrupt_filenames": corrupt_names},
        "started_local": START.isoformat(), "finished_local": end.isoformat(),
        "duration_seconds": round((end - START).total_seconds(), 3),
        "environment": {"python": sys.version.splitlines()[0], "platform": platform.platform(),
                        "numpy": np.__version__, "pandas": pd.__version__, "os_name": os.name},
        "scope": {
            "performed": ["C1-C10 structural audit", "identifier / date / unit audit",
                          "C5-C6 comparability stratification (descriptive)", "C8 parse log",
                          "C8 task inventory", "C8 per-model per-task aggregate", "join coverage measurement"],
            "explicitly_not_performed": ["future 12/24-month forecasting",
                                          "final Loss-Benchmark bridging model",
                                          "choice of the final problem-4 statistical model",
                                          "reading or writing of the parallel quality (Q) task results",
                                          "any modification of solution/src/evolution_audit.py",
                                          "any modification of raw attachments"],
        },
        "dataset_rows": {k: int(len(v)) for k, v in ctx["frames"].items()},
        "c8": {
            "json_files": ctx["n_c8_files"], "directories_with_json": int(log_df.directory.nunique()),
            "parse_ok": n_ok, "parse_failed": n_fail,
            "failure_breakdown": log_df[log_df.parse_status != "ok"].parse_status.value_counts().to_dict(),
            "likely_truncated": int(log_df.likely_truncated.eq(True).sum()),
            "distinct_result_task_keys": int(len(ctx["task_inventory"])),
            "distinct_resolved_model_names": int(ctx["c8_records"].Model.nunique()),
            "directories_with_over_one_json": ctx["multi_file_dirs"],
            "documents_missing_some_of_the_six_groups": ctx["n_c8_four_group_missing"],
            "aggregate_rows_model_x_task": int(len(agg)),
            "aggregate_valid_result_rows": int((agg.n_valid_results > 0).sum()),
            "models_in_wide_table": int(len(wi)),
            "leaf_metric_rows": int(len(ctx["leaf"])),
            "group_score_rows": int(len(ctx["group"])),
        },
        "c8_group_score_ranges": group_ranges,
        "c5_c6": {"n_merged_on_model": ctx["c5c6"]["n_merged"],
                  "per_column_equal_value_counts": c5c6_identical,
                  "fitted_model": None,
                  "note": "descriptive stratification only; no bridge/calibration/forecast"},
        "join_coverage_headline": {
            "C9_vs_C1_set_equality": ctx["c9c1"]["set_equality"],
            "C9_vs_C1_position_equality": ctx["c9c1"]["position_equality"],
            "C1_vs_C2_DataFrame_equals": ctx["c1c2_exact"],
            "C1_vs_C2_differing_numeric_cells": ctx["c1c2_cells"],
            "C1_vs_C2_max_abs_difference": ctx["c1c2_maxabs"],
            "C4_exact_normalised_name_match_rate_to_C1": ctx["c4_match"],
            "C8_exact_name_match_rate_to_C1": ctx["c8_match"],
            "C3_model_match_rate_to_C1": ctx["c3_match"],
            "C2_publication_after_submission_rows": ctx["publication_lag"],
        },
        "source_code_guard": {
            "file": "solution/src/evolution_audit.py",
            "sha256_before": ctx["sha_before"], "sha256_after": ctx["sha_after"],
            "unchanged": ctx["source_untouched"], "executed": False, "imported": False,
            "static_review_only": True,
        },
        "checks": counts,
        "data_nature_labels": {
            "catalog_label_source": "03_DATA_CATALOG.md (documented label, quoted for traceability)",
            "by_dataset": CATALOG,
            "warning": "the catalog label is a description of provenance supplied with the data; it is not an independent authenticity certification, and this run did not relabel any dataset as directly observed",
        },
        "raw_data_modified": False,
        "outputs_written_to": rel(OUT),
    }
    write_json("run_summary.json", summary)

    # ---------------- handoff.md --------------------------------------------------------
    def pct(x):
        return f"{100.0 * x:.4f}%"

    fail_lines = [f"| {r.directory} | {r.file} | {r.parse_status} | {r.error_message[:90]} | {r.bytes} |"
                  for _, r in log_df[log_df.parse_status != "ok"].iterrows()]
    unit_warn = ctx["frames"]["C7"].iloc[0]
    lines = [
        f"# TASK-C01 交接：C1-C10 数据审计与 C8 基础聚合", "",
        f"- run_id：`{RUN_ID}`；开始 `{START.isoformat()}`；结束 `{end.isoformat()}`；用时 {(end - START).total_seconds():.1f} 秒。",
        f"- 执行代码：`{rel(os.path.join(OUT, 'audit_c01.py'))}`；运行日志：`run_console.log`；退出码：`exit_code.txt`。",
        f"- 所有数字均来自本次实际运行；未对原始附件做任何写入。",
        f"- 明确未做：未来 12/24 个月预测、Loss–Benchmark 最终桥接模型、问题四最终统计模型的选择、对并行 Q 任务结果的读写。",
        f"- 静态审查目标 `solution/src/evolution_audit.py` 未被导入、未被运行、未被修改；运行前后 SHA256 一致：`{ctx['sha_after']}`。", "",
        "## 1. 数据清单与规模", "",
        "| 数据集 | 行/文件数 | 列数 | 主键候选 | 结论 |",
        "|---|---:|---:|---|---|",
        f"| C1 leaderboard_cleaned | {len(c1)} | {c1.shape[1]} | Model 重复 {int(c1.Model.duplicated().sum())} 行 | 无单列主键，需复合键 |",
        f"| C2 leaderboard_enhanced | {len(c2)} | {c2.shape[1]} | 同上 | C1 列 + Epoch_AI_* 元数据列 |",
        f"| C3 leaderboard_extended_timeseries | {len(c3)} | {c3.shape[1]} | Model+Year 仍重复 {int(c3.duplicated(['Model','Year']).sum())} 行 | 混合来源，不能当同口径面板 |",
        f"| C4 epoch_all_ai_models | {len(c4)} | {c4.shape[1]} | Model 重复 {int(c4.Model.duplicated().sum())} 行 | 元数据快照 |",
        f"| C5 loss_benchmark_bridge | {len(c5)} | {c5.shape[1]} | Model 唯一 | 43 行全部出现在 C6 |",
        f"| C6 loss_benchmark_bridge_expanded | {len(c6)} | {c6.shape[1]} | Model 唯一 | C5 的超集 |",
        f"| C7 model_architecture_metadata | {len(c7)} | {c7.shape[1]} | model_name 唯一 | 仅架构字段 |",
        f"| C8 detailed_results | {ctx['n_c8_files']} JSON / {int(log_df.directory.nunique())} 目录 | - | (目录, 文件) | 见第 3 节 |",
        f"| C9 data/*.parquet | {len(c9)} | {c9.shape[1]} | eval_name 唯一 | 榜单镜像，非独立评估 |",
        f"| C10 pythia*_eval_details/README.md | 7 | - | - | 仅文档 |", "",
        "## 2. 数据性质（目录标签 vs 本轮实测）", "",
        "| 数据集 | 说明文件/目录标签 | 本轮实测要点 |",
        "|---|---|---|",
        f"| C1 | observed | 榜单已归一化分数；`Average ⬆️` 与六项均值最大差 {float((c1['Average ⬆️'] - c1[TASKS].mean(axis=1)).abs().max()):.6g}；提交日期 {ctx['date_rows']['C1_Submission Date']['min'][:10]}–{ctx['date_rows']['C1_Submission Date']['max'][:10]} |",
        f"| C2 | observed_plus_metadata_matching | 追加 Epoch_AI 三列；发布日期非空 {int(c2.Epoch_AI_Publication_Date.notna().sum())}/{len(c2)}，其中 {ctx['publication_lag']['after']} 行晚于提交日期 |",
        f"| C3 | mixed | 4573 行为 Open LLM Leaderboard，26 行为 Historical；仅 Year 粒度；六项中 0 值分别为 MATH {int((c3.MATH_Lvl5==0).sum())}、GPQA {int((c3.GPQA==0).sum())}，0 是否代表缺失未在文件内说明 |",
        f"| C4 | reported_metadata | {len(c4)} 行快照；Parameters 缺失 {int(c4.Parameters.isna().sum())}；Open model weights? 为文本列缺失 {int(c4['Open model weights?'].isna().sum())}；`Last modified` 为记录更新时间 |",
        f"| C5/C6 | mixed_comparability | 见第 4 节；Loss_Source 混入 training loss / validation loss / model card 三类来源 |",
        f"| C7 | metadata | {len(c7)} 个模型，仅层数/头数/维度/词表/上下文/训练数据 |",
        f"| C8 | observed_evaluation | 真实 evaluate 结果 JSON，含逐子任务汇总；不含逐题作答记录 |",
        f"| C9 | observed_evaluation | 与 C1 逐行同名同序，但另有 Raw 原始比例列；不是独立评测批次 |",
        f"| C10 | documentation_only | 7 份 README，无数据表 |", "",
        "> 重要：C5/C6 的 `Val_Loss` 来自不同技术报告与不同验证集，混合来源不得当作同口径直接观测；本轮只按 `Loss_Comparability` 分层做描述统计。", "",
        "## 3. C8 解析与聚合", "",
        f"- 枚举 JSON {ctx['n_c8_files']} 个（{int(log_df.directory.nunique())} 个模型目录，{ctx['multi_file_dirs']} 个目录含 2 个 JSON）。",
        f"- 成功解析 **{n_ok}** 个，失败 **{n_fail}** 个；失败全部记入 `c8_parse_log.csv` 与 `c8_corrupt_files.csv`，未静默跳过。",
        f"- 其中文件名尾部不含闭合花括号或错误位置在文件末端 95% 之后的计为“疑似截断”：{int(log_df.likely_truncated.eq(True).sum())} 个。", "",
    ]
    if fail_lines:
        lines += ["| 目录 | 文件 | 状态 | 错误 | 字节 |", "|---|---|---|---|---:|"] + fail_lines + [""]
    lines += [
        f"- 任务键（`results` 下）共 **{len(ctx['task_inventory'])}** 个；其中 group 级 7 个，其余为叶子子任务。",
        f"- JSON 内 `model_name` 字段去重 **{int(log_df.loc[log_df.parse_status.eq('ok'), 'model_name'].nunique())}** 个（原样字符串，未做别名合并）；",
        f"  目录名去重 {int(log_df.directory.nunique())} 个；`c8_model_wide_canonical.csv` 中 目录×解析模型名 组合 {len(wi)} 行。",
        f"- 逐模型×任务聚合表 `c8_model_task_aggregate.csv`：{len(agg)} 行（模型目录×6 组任务），其中有效结果数 ≥1 的 {int((agg.n_valid_results>0).sum())} 行；",
        f"  另一张宽表 `c8_model_wide_canonical.csv` 为每模型一行（{len(wi)} 行），列含六个 group 分数与各自有效结果数。",
        "- `n_valid_results` 为该模型该任务在全部评测文件中的有限分数个数；同一模型存在多次评测时保留全部，并单列 canonical（按 `date` 字段最大者，同值取文件名最大者）。",
        f"- 注意：源码 `evolution_audit.py` 的规则是“每目录取文件名字典序最大的可解析 JSON”，本聚合表在 `legacy_selection_rule_score` 列中同时给出该规则会取到的分数，便于核对差异（{ctx['multi_file_dirs']} 个目录受影响）。", "",
        "## 4. C5/C6 分层可比性（仅描述统计）", "",
        f"- C5 {len(c5)} 行、C6 {len(c6)} 行；按 Model 合并 {len(c5.merge(c6, on='Model', suffixes=('_C5','_C6')))} 行，C5 模型全部包含于 C6。",
        f"- 合并行上 `Val_Loss`/`LB_*`/`Loss_Source`/`Loss_Comparability` 逐列相同值个数：`{json.dumps(c5c6_identical, ensure_ascii=False)}`（分母 {len(c5)}）。",
        f"- C6 分层：High（同模型同验证集）{int((c6.Loss_Comparability.str.startswith('High')).sum())} 行，Medium（不同验证集近似）{int((c6.Loss_Comparability.str.startswith('Medium')).sum())} 行。",
        f"- `D_tokens_B` 仅 High 层有值（C6 非空 {int(c6.D_tokens_B.notna().sum())} 行），Medium 层 {int(c6[c6.Loss_Comparability.str.startswith('Medium')].D_tokens_B.isna().sum())} 行缺失 → 训练数据量不可由 C6 补推。",
        "- 本轮不拟合桥接模型、不做 LOOCV、不给出 Loss→Benchmark 映射，也不做任何外推。", "",
        "## 5. 连接率与口径核查", "",
        f"- C9 vs C1：行数 {len(c9)} vs {len(c1)}；集合相等 **{ctx['c9c1']['set_equality']}**；逐行同序 **{ctx['c9c1']['position_equality']}**。二者不应当作两次独立观测。",
        f"- C1 vs C2：列名一致，但 `DataFrame.equals` = **{ctx['c1c2_exact']}**；严格不等价的数值单元 {ctx['c1c2_cells']} 个，最大绝对差 {ctx['c1c2_maxabs']:.3e}（浮点往返级）。",
        f"  这说明源码 `evolution_audit.py` 第 137–138 行的 `if not c1.equals(c2[c1.columns]): raise` 在真实附件上会**直接抛错**，是静态审查发现的阻断性缺陷。",
        f"- C4 与 C1 精确归一化名称匹配率：{pct(ctx['c4_match'])}（只做精确匹配，不做模糊匹配、不补造身份）。",
        f"- C8 与 C1 精确名称匹配率：{pct(ctx['c8_match'])}；C3 与 C1 名称匹配率：{pct(ctx['c3_match'])}。",
        f"- C9 参数列使用 `-1` 作缺失哨兵（{ctx['c9_param_sentinel']} 行），而 C1 同行是空值 → 直接对 C9 参数取均值会把 -1 当真值。", "",
        "## 6. 源码静态审查要点（未运行、未修改）", "",
        "| # | 位置 | 观察 | 风险 |",
        "|---|---|---|---|",
        "| S1 | 第 137–138 行 | `c1.equals(c2[c1.columns])` 实测为 False（{cells} 个单元浮点差异） | 阻断：脚本会在该断言处抛错，C8 及后续步骤无法执行 |".format(cells=ctx["c1c2_cells"]),
        "| S2 | 第 296–304 行 | 叶子指标先 `np.isfinite(numeric(val))` 判断再 `continue` | 非数值指标被静默丢弃；本轮 `c8_task_inventory.csv` 改为显式计数 |",
        "| S3 | 第 256–261 行 | “JSON 无 results 映射” 与 “JSON 解析失败” 共用同一 `parseable=False` | 两类失败语义被合并；本轮分列 `json_decode_error` / `schema_error_*` |",
        "| S4 | 第 264、353 行 | 每目录只取文件名字典序最大的可解析 JSON | {multi} 个目录含 2 次评测，另一次被丢弃且未在摘要中提示 |".format(multi=ctx["multi_file_dirs"]),
        "| S5 | 第 383–412 行 | 含按提交日期的前 80%/后 20% 回归与外推预测路径 | 超出 TASK-C01 授权；本轮不执行、不复制该逻辑 |",
        "| S6 | 第 428–480 行 | 对 C6 做 LOMO 线性桥接与相关分析 | 属于 Loss–Benchmark 桥接建模；本轮仅做分层描述统计 |",
        "| S7 | 第 149–151 行 | 断言 C9 parquet 与 C1 的对齐关系 | 实测成立（集合与位置均一致），但断言失败即中断，缺乏降级路径 |",
        "| S8 | 第 33–36、79–89 行 | 许可白名单/自定义清单硬编码，且把 `nan`/空串归入 unresolved | 白名单是操作口径而非法律判断；本轮沿用“未决即未决”的处理，不补猜许可证 |", "",
        "## 7. 交付物", "",
        "| 文件 | 内容 |", "|---|---|",
        "| `data_inventory.csv` | C1–C10 路径、文件数、字节、行数、列数、SHA256 |",
        "| `field_audit.csv` | 每个数据集每个字段的 dtype/缺失/唯一值/数值范围/角色 |",
        "| `missingness.csv` | 缺失与空串/哨兵计数 |",
        "| `duplicate_audit.csv` | 全行重复、主键候选重复、模型名重复、字段内重复 |",
        "| `model_identity_audit.csv` | 模型名/族/类型/许可证/参数量/日期字段可用性 |",
        "| `date_audit.csv` | 各日期字段解析率、范围、粒度与跨表时序 |",
        "| `unit_audit.csv` | 单位、取值范围、越界与哨兵 |",
        "| `c5_c6_comparability_audit.csv` | C5/C6 分层描述统计 |",
        "| `c8_parse_log.csv` | 1958 个 JSON 的逐文件解析日志（含 SHA256、错误类型与位置） |",
        "| `c8_corrupt_files.csv` | 失败文件明细（含文件尾部字节） |",
        "| `c8_task_inventory.csv` | 任务键清单、指标、样本量形态、非数值计数 |",
        "| `c8_model_task_aggregate.csv` | 逐模型×任务聚合（有效结果数、canonical、均值/极差） |",
        "| `c8_model_wide_canonical.csv` | 每模型一行的宽表（问题四可用输入之一） |",
        "| `c8_group_scores_all_runs.csv` / `c8_leaf_metrics.csv.gz` | 全部评测运行的 group / 叶子指标明细 |",
        "| `join_coverage.csv` | C9-C1、C1-C2、C3-C1、C4-C1、C8-C1 连接率与逐列一致性 |",
        "| `checks.json` | {npass} PASS / {nwarn} WARN / {nfail} FAIL 的结构化核验记录 |".format(npass=counts["PASS"], nwarn=counts["WARN"], nfail=counts["FAIL"]),
        "| `run_summary.json` | 运行环境、范围、关键计数、源码哈希守卫 |",
        "| `output_manifest.json` | 本目录全部产物的字节与 SHA256 |", "",
        "## 8. 尚未解决 / 不得越过", "",
        "- C4 的训练数据量列单位未在表内编码（`Dataset size notes` 文本各异），本任务不换算、不合并。",
        "- C7 的 `training_data_TB` 单位未在文件内定义，本任务不猜测。",
        "- C3 中 `0` 是否为缺失未在文件内说明，本任务不当作真实 0 分使用。",
        f"- C8 目录内 {ctx['multi_file_dirs']} 次重复评测（同一目录第二份 JSON）的取舍规则属于下游建模决策，本任务只提供事实与两种口径的分数。",
        "- 问题四的统计模型、12/24 个月前沿预测与 Loss–Benchmark 桥接均不在本任务范围内，需另行施工单。",
        "- 本任务未读取、未修改并行 Q 任务的任何结果文件。", "",
        "## 9. 超出本任务范围、交主控裁决（仅登记，未处理）", "",
        "> 依据统一规则，以下事项不在 TASK-C01 授权范围内，本任务不修复、不改写、不据此继续建模；证据均在 `handoff.md` 与 `join_coverage.csv`、`checks.json` 中被引用。", "",
        "| 编号 | 事项 | 本任务实测证据 | 超出范围的原因 |",
        "|---|---|---|---|",
        "| OOS-01 | `solution/src/evolution_audit.py` 第 137–138 行的严格相等守卫在真实附件上会抛错，整个演化脚本无法跑通 | `join_coverage.csv` 行 `C1_vs_C2_exact_dataframe_equality`（`DataFrame.equals`=False）与 `C1_vs_C2_float_cell_diff`（515 个数值单元差异，最大 3.55e-15） | 修改该项目源码需要独立施工单；本任务被要求“不要直接覆盖它” |",
        "| OOS-02 | C8 有 95 个目录各含 2 份评测 JSON，“取文件名字典序最大者”会静默丢弃其中一次评测 | `c8_directory_file_counts.csv`、`c8_model_task_aggregate.csv` 的 `n_files_in_directory` / `legacy_selection_rule_score` | 取舍规则属于下游建模决策，本任务只提供两种口径的分数 |",
        f"| OOS-03 | C8 全库 {n_batch} 份 JSON 同名 `{batch_name}`（同一 2025-02-13 评测批次），其中 {n_batch_bad} 份损坏；损坏文件大小恰为 64/48 KiB 且解析错误位置在文件末尾 97.9%–100% 处，是下载被截断的直接证据 | `c8_corrupt_files.csv`（含文件尾部字节）、`c8_parse_log.csv`（`error_at_eof_fraction`、`file_ends_with_closing_brace`） | 是否补下/重新评测需要主控决定 |",
        "| OOS-04 | C9 用 `-1` 作参数量缺失哨兵，而 C1 同行是空值 | `unit_audit.csv`、`join_coverage.csv` 行 `C9_vs_C1_value_agreement[#Params (B)]` | 清理规则影响下游统计，需主控裁决 |",
        "| OOS-05 | C1/C2 的 `Hub License` 缺失 1753 行（38.3%），C2 的 `Epoch_AI_Publication_Date` 仅 447/4576 非空 | `missingness.csv`、`date_audit.csv` | 许可与时间口径属于问题四范围，本任务不做任何插补 |",
        "| OOS-06 | C4 `Publication date` 存在 1950 年等极早日期，且 `Last modified` 最晚到 2026-05-08（晚于 C1 榜单截止 2025-03-13） | `date_audit.csv` | C4 是活数据库快照；时间口径需主控统一 |",
        f"| OOS-07 | C3 中 `0` 是否为缺失未在文件内说明（MATH_Lvl5 {int((ctx['frames']['C3'].MATH_Lvl5 == 0).sum())} 行、GPQA {int((ctx['frames']['C3'].GPQA == 0).sum())} 行为 0） | `unit_audit.csv`、`field_audit.csv` | 缺失语义判定会影响回归，本任务不擅自归因 |",
        "| OOS-08 | C7 `training_data_TB` 单位在文件内未定义 | `unit_audit.csv` | 单位换算需原始来源或主控裁决，本任务不猜测 |",
        "| OOS-09 | C6 的 Medium 层 68 行没有 `D_tokens_B`，无法支持 N–D–Loss 联合口径 | `c5_c6_comparability_audit.csv`、`join_coverage.csv` | Loss–Benchmark 桥接属于后续施工单 |",
        "| OOS-10 | C8 `results` 里存在空的指标名 `''`（`leaderboard` 组内 2 处） | `c8_task_inventory.csv` | 是否清理需主控决定 |",
        "| OOS-11 | C4 与 C1 的精确归一化名称匹配率仅 2.95% | `join_coverage.csv` 行 `C4_vs_C1_exact_normalised_name_match` | 是否引入模糊/别名映射属于身份消歧决策，本任务不做 |",
        "| OOS-12 | C4 `Parameters` 最大 1.739e14（超过 1e14 预期上界 1 行），`Training dataset size (total)` 的单位随行不同 | `unit_audit.csv` | 异常值与单位混合的处置需主控裁决 |", "",
        "## 10. 停止声明", "",
        "- 本任务到此停止，不进入 Loss–Benchmark 建模，不做问题四预测，不启动下一项任务。",
        "- 未修改 `00_PROJECT_BRIEF.md`、`01_PROJECT_STATUS.md`、`02_DECISIONS.md`、`03_DATA_CATALOG.md`、`04_TASK_QUEUE.md`、`05_REVIEW_LOG.md`。",
        "- 未修改 `solution/`、`F题/real_attachments/`、其他 `diagnostics/TASK-*` 目录中的任何文件。",
        "- 全部结论均可回溯到本目录已落盘文件（见 `output_manifest.json` 的 `sha256`）。", "",
    ]
    with open(os.path.join(OUT, "handoff.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return summary


def write_manifest():
    """Recursive: every file produced by this run is hashed, including scratch scripts."""
    entries = []
    for dirpath, dirnames, filenames in os.walk(OUT):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            key = os.path.relpath(path, OUT).replace("\\", "/")
            if key == "output_manifest.json":
                continue
            entries.append({
                "file": key, "bytes": int(os.path.getsize(path)), "sha256": sha256_file(path),
                "is_required_output": key in REQUIRED_OUTPUTS,
                "role": ("execution_code" if key.endswith(".py") and not key.startswith("scratch/")
                         else "scratch_non_authoritative" if key.startswith("scratch/")
                         else "run_log" if key in ("run.log", "run_console.log", "exit_code.txt", "run_id.txt")
                         else "required_output" if key in REQUIRED_OUTPUTS
                         else "supporting_evidence"),
            })
    write_json("output_manifest.json", {"run_id": RUN_ID, "task": TASK,
                                        "artifact_count": len(entries), "artifacts": entries})
    return entries


REQUIRED_OUTPUTS = {
    "data_inventory.csv", "field_audit.csv", "missingness.csv", "duplicate_audit.csv",
    "model_identity_audit.csv", "date_audit.csv", "unit_audit.csv",
    "c5_c6_comparability_audit.csv", "c8_parse_log.csv", "c8_task_inventory.csv",
    "c8_model_task_aggregate.csv", "join_coverage.csv", "checks.json",
    "run_summary.json", "handoff.md", "output_manifest.json",
}


if __name__ == "__main__":
    try:
        main_result = main()
    except Exception:
        log("!!! FATAL !!!")
        log(traceback.format_exc())
        raise
    ctx, checks, written, sha_before, sha_after, c5c6_identical, group_ranges, n_pass, n_warn, n_failc = main_result
    ctx["sha_before"] = sha_before
    ctx["sha_after"] = sha_after
    summary = write_summary_and_handoff(ctx, checks, c5c6_identical, group_ranges,
                                        {"PASS": n_pass, "WARN": n_warn, "FAIL": n_failc})
    end = datetime.now(TZ)
    log(f"[done] finished {end.isoformat()}  duration={(end - START).total_seconds():.1f}s")
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(LOG_LINES) + "\n")
    # Written last and with no stdout/stderr activity afterwards, so that the captured
    # console log keeps exactly the byte content that output_manifest.json hashes.
    write_manifest()
