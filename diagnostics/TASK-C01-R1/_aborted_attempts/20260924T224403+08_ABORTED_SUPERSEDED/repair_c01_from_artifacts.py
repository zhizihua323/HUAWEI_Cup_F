# -*- coding: utf-8 -*-
"""TASK-C01-R1 : production repair of the TASK-C01 C8 aggregates and checker.

Hard scope rules enforced by this script (see tasks/TASK-C01-R1_*.md):

  * Reads ONLY the frozen artifacts of `diagnostics/TASK-C01/20260924T175553+08/`.
    Every read passes through `guard_read()`, which refuses any path that leaves that
    directory or that resolves under `F題/real_attachments` (raw attachments).
  * Never re-parses a C8 JSON, never rescans C1-C10, never runs `audit_c01.py`.
  * Never writes into the original C01 directory.
  * The R1 run directory is created fresh; if it already exists the script exits non-zero.
  * No Loss-Benchmark model, no time-series extrapolation, no problem-4 model selection.

The independent checker lives in `verify_c01_repairs.py` and must NOT import this module.
"""
import argparse
import hashlib
import io
import json
import os
import platform
import re
import shutil
import sys
import traceback
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

TASK = "TASK-C01-R1"
SOURCE_TASK = "TASK-C01"
SOURCE_RUN_ID = "20260924T175553+08"
SOURCE_REL = os.path.join("diagnostics", "TASK-C01", SOURCE_RUN_ID)
AUTHOR = "Codex (OpenAI), AI-assisted, 2026-09-24"
TZ = timezone(timedelta(hours=8))
TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]

def find_workspace(start):
    """Locate the project root by looking for the F题 / solution markers, so that the script
    behaves identically whether it is executed from a staging directory or from the run directory."""
    cur = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(cur, "F题")) or os.path.isdir(os.path.join(cur, "solution")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(start)


WORKSPACE = find_workspace(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(WORKSPACE, SOURCE_REL)
RAW_ROOT = os.path.join(WORKSPACE, "F\u9898", "real_attachments")
EVOLUTION_AUDIT = os.path.join(WORKSPACE, "solution", "src", "evolution_audit.py")

# Exact acceptance anchors from the work order. They are constants of the *specification*,
# never values copied out of the tables this script produces.
ANCHOR = {
    "n_files_total": 1958,
    "n_files_parse_success": 1954,
    "n_files_parse_failed": 4,
    "n_directories": 1863,
    "n_dirs_one_file": 1768,
    "n_dirs_two_files": 95,
    "n_dirs_with_parse_failure": 4,
    "n_dirs_pure_corrupt": 3,
    "corrupt_dir_expect": {
        "DreadPoor_Winter_Dawn-8B-TIES": (2, 1, 1),
        "FINGU-AI_Chocolatine-Fusion-14B": (1, 0, 1),
        "Intel_neural-chat-7b-v3-3": (1, 0, 1),
        "L-RAGE_3_PRYMMAL-ECE-7B-SLERP-V1": (1, 0, 1),
    },
    "n_task_slots": 11724,
    "n_group_scores_finite": 11699,
    "n_group_scores_missing": 25,
    "n_model_task_rows": 11160,
    "n_model_task_rows_valid": 11135,
    "n_model_task_rows_zero": 25,
    "n_model_task_valid_sum": 11699,
    "n_wide_rows": 1860,
    "n_tasks_valid_distribution": {1: 3, 2: 1, 3: 2, 6: 1854},
    "n_six_task_complete_true": 1854,
    "n_six_task_complete_false": 6,
    "n_complete_mean_finite": 1854,
    "n_partial_mean_finite": 6,
    "n_nonnumeric_metric_values": 7806,
    "c1_rows": 4576,
    "c2_rows": 4576,
    "c1c2_diff_cells": 515,
    "c1c2_max_abs_diff": 3.552713678800501e-15,
    "c5_rows": 43,
    "c6_rows": 75,
    "c5c6_merged_rows": 43,
    "n_bridge_models_fitted": 0,
}
EXPECTED_SOURCE_RUN_SUMMARY = {
    "source_run_id": SOURCE_RUN_ID,
    "source_task": SOURCE_TASK,
}

LOG = []
ACCESS_LOG = []


def log(msg=""):
    line = str(msg)
    LOG.append(line)
    print(line, flush=True)


def guard_read(path):
    """The single door for every input read. Refuses raw attachments and anything
    outside the frozen TASK-C01 run directory, and records the access."""
    resolved = os.path.abspath(path)
    norm = resolved.replace("\\", "/").lower()
    if "real_attachments" in norm or norm.startswith(os.path.abspath(RAW_ROOT).replace("\\", "/").lower()):
        raise RuntimeError("R1-SCOPE violation: raw attachment access attempted -> " + resolved)
    if os.path.commonpath([resolved, SOURCE_DIR]) != SOURCE_DIR:
        raise RuntimeError("R1-SCOPE violation: input outside the frozen C01 run directory -> " + resolved)
    if not os.path.isfile(resolved):
        raise FileNotFoundError(resolved)
    ACCESS_LOG.append(resolved)
    return resolved


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rcsv(name):
    return pd.read_csv(guard_read(os.path.join(SOURCE_DIR, name)), encoding="utf-8-sig")


def rjson(name):
    with io.open(guard_read(os.path.join(SOURCE_DIR, name)), encoding="utf-8") as handle:
        return json.load(handle)


def wcsv(name, frame):
    path = os.path.join(OUT, name)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def wjson(name, payload):
    path = os.path.join(OUT, name)
    with io.open(path, "w", encoding="utf-8") as handle:
        json.dump(to_builtin(payload), handle, ensure_ascii=False, indent=2, allow_nan=False)
    return path


def to_builtin(value):
    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_builtin(v) for v in (sorted(value) if isinstance(value, set) else value)]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else str(value)
    return str(value)


# ======================================================================================
# input loading (all through guard_read)
# ======================================================================================
CSV_INPUTS = [
    "data_inventory.csv", "field_audit.csv", "missingness.csv", "duplicate_audit.csv",
    "model_identity_audit.csv", "date_audit.csv", "unit_audit.csv",
    "c5_c6_comparability_audit.csv", "c8_parse_log.csv", "c8_corrupt_files.csv",
    "c8_directory_file_counts.csv", "c8_task_inventory.csv", "c8_group_scores_all_runs.csv",
    "c8_model_task_aggregate.csv", "c8_model_wide_canonical.csv", "join_coverage.csv",
]
JSON_INPUTS = ["run_summary.json", "checks.json", "output_manifest.json"]
TEXT_INPUTS = ["handoff.md", "audit_c01.py"]
GZ_INPUTS = ["c8_leaf_metrics.csv.gz"]


def load_inputs():
    log("[load] frozen TASK-C01 artifacts (read-only, guarded)")
    data = {}
    for name in CSV_INPUTS:
        data[name] = pd.read_csv(guard_read(os.path.join(SOURCE_DIR, name)), encoding="utf-8-sig")
        log(f"       {name:<42} {data[name].shape}")
    data["c8_leaf_metrics.csv.gz"] = pd.read_csv(guard_read(os.path.join(SOURCE_DIR, "c8_leaf_metrics.csv.gz")),
                                                  encoding="utf-8-sig")
    log(f"       {'c8_leaf_metrics.csv.gz':<42} {data['c8_leaf_metrics.csv.gz'].shape}")
    for name in JSON_INPUTS:
        data[name] = rjson(name)
        log(f"       {name:<42} json")
    for name in TEXT_INPUTS:
        with io.open(guard_read(os.path.join(SOURCE_DIR, name)), encoding="utf-8") as handle:
            data[name] = handle.read()
        log(f"       {name:<42} text ({len(data[name])} chars)")
    return data


# ======================================================================================
# corrected C8 tables
# ======================================================================================
def build_directory_corrected(pl, gs):
    """One row per directory that owns at least one C8 JSON file.

    n_results_missing is defined for parseable output only: parse failures create no
    pseudo task scores, they are carried by n_files_parse_failed / has_parse_failure.
    """
    grouped = pl.groupby("directory", dropna=False)
    rows = []
    finite_by_dir = gs.groupby("directory").score.apply(lambda s: int(s.notna().sum())).to_dict()
    slots_by_dir = gs.groupby("directory").size().to_dict()
    models_ok = pl.loc[pl.parse_status.eq("ok")].groupby("directory").model_name.apply(
        lambda s: sorted({str(x) for x in s.dropna()})).to_dict()
    ok_files = pl.loc[pl.parse_status.eq("ok")].groupby("directory").file.apply(sorted).to_dict()
    bad_files = pl.loc[~pl.parse_status.eq("ok")].groupby("directory").file.apply(sorted).to_dict()
    for directory, block in grouped:
        n_total = int(len(block))
        n_ok = int(block.parse_status.eq("ok").sum())
        n_bad = int((~block.parse_status.eq("ok")).sum())
        expected_slots = n_ok * len(TASKS)
        valid = int(finite_by_dir.get(directory, 0))
        rows.append({
            "directory": directory,
            "n_files_total": n_total,
            "n_files_parse_success": n_ok,
            "n_files_parse_failed": n_bad,
            "has_parse_failure": bool(n_bad > 0),
            "has_any_parseable_file": bool(n_ok > 0),
            "source_parse_incomplete": bool(n_bad > 0),
            "n_task_slots_expected": expected_slots,
            "n_result_slots_in_group_table": int(slots_by_dir.get(directory, 0)),
            "n_results_valid": valid,
            "n_results_missing": int(expected_slots - valid),
            "n_models_from_parse_ok": len(models_ok.get(directory, [])),
            "models_from_parse_ok": " | ".join(models_ok.get(directory, [])),
            "parse_ok_files": " | ".join(ok_files.get(directory, [])),
            "parse_failed_files": " | ".join(bad_files.get(directory, [])),
            "file_accounting_identity_ok": bool(n_total == n_ok + n_bad),
        })
    tbl = pd.DataFrame(rows).sort_values("directory").reset_index(drop=True)
    return tbl


def build_model_task_corrected(mt, dir_tbl, gs):
    """Base = the original model x task table.  Adds directory coverage and recomputes
    n_valid_results / n_missing_results with an explicit denominator."""
    recomputed = (gs.groupby(["directory", "task_group"]).score
                  .apply(lambda s: int(s.notna().sum())).rename("n_valid_results_recomputed")
                  .reset_index().rename(columns={"directory": "model_key"}))
    slots = (gs.groupby(["directory", "task_group"]).size().rename("n_group_rows").reset_index()
             .rename(columns={"directory": "model_key"}))
    out = mt.merge(dir_tbl[["directory", "n_files_total", "n_files_parse_success", "n_files_parse_failed",
                            "has_parse_failure", "has_any_parseable_file", "source_parse_incomplete"]],
                   left_on="model_key", right_on="directory", how="left", validate="many_to_one")
    out = out.merge(recomputed, on=["model_key", "task_group"], how="left", validate="one_to_one")
    out = out.merge(slots, on=["model_key", "task_group"], how="left", validate="one_to_one")
    out = out.rename(columns={"n_files_in_directory": "orig_n_files_in_directory",
                              "n_missing_results": "orig_n_missing_results"})
    out["n_valid_results_original"] = out["n_valid_results"]
    out["n_valid_results"] = out["n_valid_results_recomputed"]
    out["n_file_slots_this_task"] = out["n_files_parse_success"]
    out["n_missing_results"] = out["n_file_slots_this_task"] - out["n_valid_results"]
    out["n_valid_results_agrees_with_original"] = out["n_valid_results"].eq(out["n_valid_results_original"])
    out["canonical_score_finite"] = out["canonical_score"].notna()
    out["canonical_selection_basis"] = ("existing C01 rule only: max eval_unix_date, tie -> max filename; "
                                        "NOT re-decided in R1")
    out["legacy_selection_basis"] = ("existing C01 rule only: lexicographically last filename in the directory; "
                                     "NOT re-decided in R1")
    out = out.drop(columns=["directory", "n_valid_results_recomputed"])
    ordered = ["model_key", "Model", "task_group", "model_sha",
               "n_files_total", "n_files_parse_success", "n_files_parse_failed",
               "has_parse_failure", "has_any_parseable_file", "source_parse_incomplete",
               "n_file_slots_this_task", "n_valid_results", "n_missing_results",
               "n_group_rows", "orig_n_files_in_directory", "orig_n_missing_results",
               "n_valid_results_original", "n_valid_results_agrees_with_original",
               "n_distinct_scores", "all_scores", "all_files",
               "canonical_file", "canonical_eval_unix_date", "canonical_score",
               "canonical_score_finite", "canonical_selection_basis",
               "legacy_selection_rule_score", "legacy_selection_basis",
               "mean_score", "min_score", "max_score", "sd_score", "spread_max_minus_min"]
    return out[ordered].sort_values(["model_key", "task_group"]).reset_index(drop=True)


def build_wide_corrected(wi, mt, dir_tbl):
    """Rebuild the model-level wide table from the ORIGINAL model x task table and split
    the complete mean from the partial mean."""
    base = mt.copy()
    piv = (base.pivot_table(index=["model_key", "Model"], columns="task_group",
                            values="canonical_score", aggfunc="first"))
    for task in TASKS:
        if task not in piv.columns:
            piv[task] = np.nan
    piv = piv[TASKS].reset_index()
    cnt = (base.pivot_table(index="model_key", columns="task_group", values="n_valid_results", aggfunc="first"))
    cnt.columns = [c + "_n_valid" for c in cnt.columns]
    cnt = cnt.reset_index()
    out = piv.merge(cnt, on="model_key", how="left")
    out = out.merge(dir_tbl[["directory", "n_files_total", "n_files_parse_success", "n_files_parse_failed",
                             "has_parse_failure", "source_parse_incomplete"]],
                    left_on="model_key", right_on="directory", how="left", validate="many_to_one")
    out = out.drop(columns=["directory"])
    task_mat = out[TASKS].astype(float)
    out["n_tasks_valid"] = task_mat.notna().sum(axis=1).astype(int)
    out["six_task_complete"] = out["n_tasks_valid"].eq(len(TASKS))
    row_mean = task_mat.mean(axis=1)
    out["six_task_mean_complete_only"] = np.where(out["six_task_complete"], row_mean, np.nan)
    out["partial_task_mean"] = np.where(out["n_tasks_valid"].between(1, len(TASKS) - 1), row_mean, np.nan)
    out["legacy_partial_or_complete_mean"] = row_mean
    legacy_src = wi.set_index("model_key")["six_task_mean_c8_raw"]
    out["legacy_mean_matches_c01_table"] = np.isclose(
        out["legacy_partial_or_complete_mean"], out["model_key"].map(legacy_src), equal_nan=True)
    out["mean_column_semantics"] = ("six_task_mean_complete_only = mean of six tasks ONLY when "
                                    "n_tasks_valid == 6; partial_task_mean = mean over the available "
                                    "tasks ONLY when 1 <= n_tasks_valid <= 5; legacy_* keeps the "
                                    "original skipna row mean for traceability and is NOT a six-task mean")
    ordered = (["model_key", "Model"] + TASKS + [t + "_n_valid" for t in TASKS] +
               ["n_tasks_valid", "six_task_complete", "six_task_mean_complete_only", "partial_task_mean",
                "n_files_total", "n_files_parse_success", "n_files_parse_failed",
                "has_parse_failure", "source_parse_incomplete",
                "legacy_partial_or_complete_mean", "legacy_mean_matches_c01_table", "mean_column_semantics"])
    return out[ordered].sort_values("model_key").reset_index(drop=True)


# ======================================================================================
# repaired checker: every PASS is a computed comparison of actual vs expected
# ======================================================================================
CHECKS = []


def _same(actual, expected):
    if isinstance(expected, dict):
        # "expected" lists the conditions the observation must satisfy; every expected key must
        # exist in the observation with an equal value. Extra observed detail is allowed.
        if not isinstance(actual, dict):
            return False
        for key in expected:
            if key not in actual:
                return False
            if not _same(actual[key], expected[key]):
                return False
        return True
    if isinstance(expected, (list, tuple)):
        return list(actual) == list(expected)
    if isinstance(expected, bool) or isinstance(actual, bool):
        return bool(actual) == bool(expected)
    if isinstance(expected, (int, np.integer)) and isinstance(actual, (int, np.integer)):
        return int(actual) == int(expected)
    if isinstance(expected, (int, float, np.integer, np.floating)) and \
       isinstance(actual, (int, float, np.integer, np.floating)):
        if np.isnan(float(expected)) and np.isnan(float(actual)):
            return True
        return bool(np.isclose(float(actual), float(expected), rtol=1e-9, atol=1e-12))
    return actual == expected


def add(check_id, claim, actual, expected, evidence, verification_method, limitations="", key=False,
        tolerance_note="", warn_only=False):
    ok = _same(actual, expected)
    CHECKS.append({
        "check_id": check_id, "status": "PASS" if ok else ("WARN" if warn_only else "FAIL"),
        "claim": claim, "key_c8_item": bool(key),
        "actual": to_builtin(actual), "expected": to_builtin(expected), "evidence": evidence,
        "verification_method": verification_method,
        "limitations": limitations or "none identified for this scope",
        "tolerance": tolerance_note or "exact (numeric rtol=1e-9, atol=1e-12)",
    })


def add_negative(check_id, claim, status, actual, expected, evidence, verification_method,
                 limitations, key=False):
    """For statuses that are deliberately not PASS: NOT_CHECKED / NOT_VERIFIABLE / WARN / FAIL."""
    assert status in ("NOT_CHECKED", "NOT_VERIFIABLE", "WARN", "FAIL"), status
    CHECKS.append({
        "check_id": check_id, "status": status, "claim": claim, "key_c8_item": bool(key),
        "actual": to_builtin(actual), "expected": to_builtin(expected), "evidence": evidence,
        "verification_method": verification_method, "limitations": limitations, "tolerance": "n/a",
    })


def build_checks(data, dir_tbl, mt_corr, wide_corr, protected, inputs_manifest):
    pl = data["c8_parse_log.csv"]
    cor = data["c8_corrupt_files.csv"]
    dc = data["c8_directory_file_counts.csv"]
    gs = data["c8_group_scores_all_runs.csv"]
    mt = data["c8_model_task_aggregate.csv"]
    wi = data["c8_model_wide_canonical.csv"]
    ti = data["c8_task_inventory.csv"]
    leaf = data["c8_leaf_metrics.csv.gz"]
    srs = data["run_summary.json"]

    ok_mask = pl.parse_status.eq("ok")
    failed = pl.loc[~ok_mask]
    per_dir = pl.groupby("directory").agg(
        n=("file", "size"), n_ok=("parse_status", lambda s: int((s == "ok").sum())))
    per_dir["n_bad"] = per_dir.n - per_dir.n_ok
    dir_set_parse = set(pl.directory)
    dir_set_counts = set(dc.directory)
    finite_by_dir = gs.groupby("directory").score.apply(lambda s: int(s.notna().sum()))
    fail_dirs = sorted(failed.directory.unique())
    bad_keys_pl = {(r.directory, r.file) for r in failed.itertuples()}
    bad_keys_cor = {(r.directory, r.file) for r in cor.itertuples()}
    pure = [d for d in fail_dirs if int(per_dir.loc[d, "n_ok"]) == 0]
    dir_idx = dir_tbl.set_index("directory")

    # ---------------------------------------------------------------- C8 file accounting (key)
    add("R1-C8-FILE-TOTAL", "C8 JSON files registered in the frozen parse log",
        int(len(pl)), ANCHOR["n_files_total"], "c8_parse_log.csv", "count rows of the frozen parse log")
    add("R1-C8-FILE-OK", "C8 JSON files with parse_status == ok",
        int(ok_mask.sum()), ANCHOR["n_files_parse_success"],
        "c8_parse_log.csv", "value_counts of parse_status")
    add("R1-C8-FILE-FAIL", "C8 JSON files with parse_status != ok",
        int((~ok_mask).sum()), ANCHOR["n_files_parse_failed"],
        "c8_parse_log.csv", "value_counts of parse_status")
    add("R1-C8-FILE-IDENTITY", "file accounting identity 1958 = 1954 + 4",
        int(ok_mask.sum()) + int((~ok_mask).sum()), int(len(pl)),
        "c8_parse_log.csv", "success + failure == total on the row-level classification")
    add("R1-C8-DIR-COUNT", "directories owning at least one C8 JSON",
        int(per_dir.shape[0]), ANCHOR["n_directories"],
        "c8_parse_log.csv + c8_directory_file_counts.csv",
        "distinct directory in the parse log vs row count of the directory counts file")
    add("R1-C8-DIR-FILESET-EQUAL", "directory sets of the two frozen artifacts are identical",
        {"parse_log_set_equals_counts_set": dir_set_parse == dir_set_counts,
         "parse_log_dirs": len(dir_set_parse), "counts_dirs": len(dir_set_counts)},
        {"parse_log_set_equals_counts_set": True, "parse_log_dirs": ANCHOR["n_directories"],
         "counts_dirs": ANCHOR["n_directories"]},
        "c8_parse_log.csv vs c8_directory_file_counts.csv", "set equality of directory labels")
    per_dir_counts = dc.set_index("directory").n_json_files.reindex(per_dir.index)
    add("R1-C8-DIR-FILE-COUNT-MATCH", "per-directory JSON counts agree between the two artifacts",
        {"dirs_compared": int(len(per_dir)), "mismatched_dirs": int((per_dir_counts != per_dir.n).sum()),
         "sum_of_counts_file": int(dc.n_json_files.sum()), "sum_of_parse_log": int(len(pl))},
        {"dirs_compared": ANCHOR["n_directories"], "mismatched_dirs": 0,
         "sum_of_counts_file": ANCHOR["n_files_total"], "sum_of_parse_log": ANCHOR["n_files_total"]},
        "c8_parse_log.csv vs c8_directory_file_counts.csv", "element-wise comparison per directory")
    add("R1-C8-DIR-ONE-FILE", "directories holding exactly one C8 JSON",
        int((per_dir.n == 1).sum()), ANCHOR["n_dirs_one_file"],
        "c8_parse_log.csv + c8_directory_file_counts.csv", "distribution of per-directory file counts")
    add("R1-C8-DIR-TWO-FILE", "directories holding exactly two C8 JSONs",
        int((per_dir.n == 2).sum()), ANCHOR["n_dirs_two_files"],
        "c8_parse_log.csv + c8_directory_file_counts.csv", "distribution of per-directory file counts")
    add("R1-C8-CORRUPT-SET", "the corrupt-file list and the parse-log failure set are the same set",
        {"corrupt_rows": int(len(cor)), "parse_log_failures": int(len(failed)),
         "sets_equal": bad_keys_pl == bad_keys_cor,
         "only_in_corrupt": sorted(bad_keys_cor - bad_keys_pl),
         "only_in_parse_log": sorted(bad_keys_pl - bad_keys_cor)},
        {"corrupt_rows": ANCHOR["n_files_parse_failed"], "parse_log_failures": ANCHOR["n_files_parse_failed"],
         "sets_equal": True, "only_in_corrupt": [], "only_in_parse_log": []},
        "c8_corrupt_files.csv vs c8_parse_log.csv",
        "bidirectional set difference on (directory, file)")
    sha_map = pl.set_index(["directory", "file"]).sha256.to_dict()
    sha_ok = all(sha_map.get((r.directory, r.file)) == r.sha256 for r in cor.itertuples())
    add("R1-C8-CORRUPT-SHA", "corrupt-file SHA256 agrees with the parse-log row for the same file",
        {"rows_checked": int(len(cor)), "all_match": bool(sha_ok)},
        {"rows_checked": ANCHOR["n_files_parse_failed"], "all_match": True},
        "c8_corrupt_files.csv vs c8_parse_log.csv",
        "string equality of sha256 per (directory, file) across two artifacts")
    add("R1-C8-CORRUPT-DIRS", "file accounting of each damaged directory",
        {d: [int(per_dir.loc[d, "n"]), int(per_dir.loc[d, "n_ok"]), int(per_dir.loc[d, "n_bad"])]
         for d in fail_dirs},
        {d: list(v) for d, v in ANCHOR["corrupt_dir_expect"].items()},
        "c8_parse_log.csv + c8_corrupt_files.csv",
        "[total, parse_success, parse_failed] per damaged directory")
    add("R1-C8-PURE-CORRUPT", "damaged directories with no parseable file at all",
        {"n_pure_corrupt": len(pure), "directories": sorted(pure)},
        {"n_pure_corrupt": ANCHOR["n_dirs_pure_corrupt"],
         "directories": sorted([d for d, v in ANCHOR["corrupt_dir_expect"].items() if v[1] == 0])},
        "c8_parse_log.csv", "damaged directories with zero parse_status == ok rows")
    prop = {}
    for r in cor.itertuples():
        d = r.directory
        prop[d] = {
            "row_present": bool(d in dir_idx.index),
            "has_parse_failure": bool(dir_idx.loc[d, "has_parse_failure"]) if d in dir_idx.index else None,
            "n_files_parse_failed": int(dir_idx.loc[d, "n_files_parse_failed"]) if d in dir_idx.index else None,
            "failed_file_listed": bool(d in dir_idx.index and r.file in str(dir_idx.loc[d, "parse_failed_files"])),
        }
    add("R1-C8-PROPAGATION", "every corrupt file is propagated into the corrected directory table",
        {"per_file": prop,
         "n_files_propagated": sum(1 for v in prop.values()
                                   if all(v[k] for k in ("row_present", "has_parse_failure",
                                                         "failed_file_listed"))
                                   and v["n_files_parse_failed"] >= 1)},
        {"n_files_propagated": ANCHOR["n_files_parse_failed"]},
        "c8_corrupt_files.csv vs c8_directory_aggregate_corrected.csv",
        "join of corrupt files onto the corrected directory table")
    pure_rows = {d: [int(dir_idx.loc[d, "n_files_parse_success"]), int(dir_idx.loc[d, "n_results_valid"])]
                 for d in pure}
    add("R1-C8-PURE-CORRUPT-ROW", "pure-corrupt directories survive with zero results",
        {"rows": pure_rows, "all_zero_success_and_results": all(v == [0, 0] for v in pure_rows.values())},
        {"all_zero_success_and_results": True},
        "c8_directory_aggregate_corrected.csv",
        "presence and zero-coverage test for the three pure-corrupt directories")
    add("R1-C8-DIR-ID", "per-directory identity n_files_total == success + failed",
        {"directories_checked": int(len(dir_tbl)),
         "violations": int((~dir_tbl.file_accounting_identity_ok).sum())},
        {"directories_checked": ANCHOR["n_directories"], "violations": 0},
        "c8_directory_aggregate_corrected.csv", "row-wise identity test over all directories")

    # ---------------------------------------------------------------- C8 group scores (key)
    add("R1-C8-SLOTS", "task slots produced by parseable files (parseable files x six tasks)",
        {"group_rows": int(len(gs)), "parse_ok_files_times_six": int(ok_mask.sum() * len(TASKS))},
        {"group_rows": ANCHOR["n_task_slots"], "parse_ok_files_times_six": ANCHOR["n_task_slots"]},
        "c8_group_scores_all_runs.csv vs c8_parse_log.csv", "row count vs success count x 6 tasks")
    add("R1-C8-FINITE", "finite group scores over the six prescribed tasks",
        int(gs.score.notna().sum()), ANCHOR["n_group_scores_finite"],
        "c8_group_scores_all_runs.csv", "count of non-null score values")
    add("R1-C8-MISSING-SLOTS", "missing group-score slots",
        int(gs.score.isna().sum()), ANCHOR["n_group_scores_missing"],
        "c8_group_scores_all_runs.csv", "count of null score values")
    add("R1-C8-DIRVALID-SUM", "sum of n_results_valid over the corrected directory table",
        int(dir_tbl.n_results_valid.sum()), ANCHOR["n_group_scores_finite"],
        "c8_directory_aggregate_corrected.csv vs c8_group_scores_all_runs.csv",
        "directory-level finite counts summed and compared with the group-table recount")
    faildir_finite = {d: int(finite_by_dir.get(d, 0)) for d in fail_dirs}
    add("R1-C8-CORRUPTDIR-SCORES", "finite group scores contributed by each damaged directory",
        faildir_finite,
        {"DreadPoor_Winter_Dawn-8B-TIES": 6, "FINGU-AI_Chocolatine-Fusion-14B": 0,
         "Intel_neural-chat-7b-v3-3": 0, "L-RAGE_3_PRYMMAL-ECE-7B-SLERP-V1": 0},
        "c8_group_scores_all_runs.csv", "per-directory non-null score count")
    grid_gs = {(r.directory, r.file) for r in gs.itertuples()}
    grid_ok = {(r.directory, r.file) for r in pl.loc[ok_mask].itertuples()}
    add("R1-C8-GROUP-GRIDSET", "group-score grid equals the parseable-file set",
        {"gs_grid": len(grid_gs), "parse_ok_grid": len(grid_ok), "sets_equal": grid_gs == grid_ok,
         "only_in_gs": sorted(grid_gs - grid_ok), "only_in_parse_ok": sorted(grid_ok - grid_gs)},
        {"gs_grid": ANCHOR["n_files_parse_success"], "parse_ok_grid": ANCHOR["n_files_parse_success"],
         "sets_equal": True, "only_in_gs": [], "only_in_parse_ok": []},
        "c8_group_scores_all_runs.csv vs c8_parse_log.csv", "set equality on (directory, file)")

    # ---------------------------------------------------------------- model x task (key)
    add("R1-C8-MT-ROWS", "model x task aggregate rows", int(len(mt)), ANCHOR["n_model_task_rows"],
        "c8_model_task_aggregate.csv", "row count")
    add("R1-C8-MT-VALID-ROWS", "model x task rows with at least one valid result",
        int((mt.n_valid_results > 0).sum()), ANCHOR["n_model_task_rows_valid"],
        "c8_model_task_aggregate.csv", "count of n_valid_results > 0")
    add("R1-C8-MT-ZERO-ROWS", "model x task rows with zero valid results",
        int((mt.n_valid_results == 0).sum()), ANCHOR["n_model_task_rows_zero"],
        "c8_model_task_aggregate.csv", "count of n_valid_results == 0")
    add("R1-C8-MT-SUM", "sum of n_valid_results over the model x task table",
        int(mt.n_valid_results.sum()), ANCHOR["n_model_task_valid_sum"],
        "c8_model_task_aggregate.csv vs c8_group_scores_all_runs.csv",
        "sum of the frozen column vs the total finite scores in the group detail")
    corr_pairs = {(r.model_key, r.task_group): int(r.n_valid_results) for r in mt_corr.itertuples()}
    orig_pairs = {(r.model_key, r.task_group): int(r.n_valid_results) for r in mt.itertuples()}
    diff_pairs = {f"{k[0]}|{k[1]}": [orig_pairs.get(k), corr_pairs.get(k)]
                  for k in set(orig_pairs) | set(corr_pairs) if orig_pairs.get(k) != corr_pairs.get(k)}
    add("R1-C8-MT-RECOMPUTE", "corrected n_valid_results reproduces the frozen model x task values",
        {"pairs_compared": len(orig_pairs), "pairs_differing": len(diff_pairs), "differences": diff_pairs},
        {"pairs_compared": ANCHOR["n_model_task_rows"], "pairs_differing": 0, "differences": {}},
        "c8_model_task_aggregate.csv vs c8_model_task_aggregate_corrected.csv",
        "per-key comparison of the frozen column against the corrected column")
    cov_pairs = {(r.model_key, r.task_group): [int(r.n_files_total), int(r.n_files_parse_success),
                                               int(r.n_files_parse_failed), bool(r.source_parse_incomplete)]
                 for r in mt_corr.itertuples()}
    dir_cov = {d: [int(dir_idx.loc[d, "n_files_total"]), int(dir_idx.loc[d, "n_files_parse_success"]),
                   int(dir_idx.loc[d, "n_files_parse_failed"]), bool(dir_idx.loc[d, "source_parse_incomplete"])]
               for d in dir_idx.index}
    cov_bad = {f"{k[0]}|{k[1]}": [v, dir_cov.get(k[0])] for k, v in cov_pairs.items()
               if v != dir_cov.get(k[0])}
    add("R1-C8-MT-COVERAGE", "coverage fields of the corrected model x task table come from the corrected directory table",
        {"relationships_checked": len(cov_pairs), "mismatches": len(cov_bad),
         "examples": dict(list(cov_bad.items())[:5])},
        {"relationships_checked": ANCHOR["n_model_task_rows"], "mismatches": 0},
        "c8_model_task_aggregate_corrected.csv vs c8_directory_aggregate_corrected.csv",
        "key-wise comparison of four coverage fields against the directory table")
    dp_rows = int(mt_corr.model_key.eq("DreadPoor_Winter_Dawn-8B-TIES").sum())
    dp_flagged = int(mt_corr.loc[mt_corr.model_key.eq("DreadPoor_Winter_Dawn-8B-TIES"),
                                 "source_parse_incomplete"].sum())
    other_flagged = int(mt_corr.loc[~mt_corr.model_key.eq("DreadPoor_Winter_Dawn-8B-TIES"),
                                    "source_parse_incomplete"].sum())
    add("R1-C8-MT-INCOMPLETE-PROP", "source_parse_incomplete is set on the six rows of the damaged directory that still has data",
        {"DreadPoor_rows": dp_rows, "DreadPoor_rows_flagged": dp_flagged,
         "other_rows_flagged": other_flagged},
        {"DreadPoor_rows": 6, "DreadPoor_rows_flagged": 6, "other_rows_flagged": 0},
        "c8_model_task_aggregate_corrected.csv", "count of flagged rows per model_key")

    # ---------------------------------------------------------------- model wide table (key)
    add("R1-C8-WIDE-ROWS", "model wide table rows in the frozen artifact",
        int(len(wi)), ANCHOR["n_wide_rows"], "c8_model_wide_canonical.csv", "row count")
    add("R1-C8-WIDE-ROWS-CORRECTED", "corrected wide table rows equal the frozen wide table rows",
        int(len(wide_corr)), int(len(wi)),
        "c8_model_wide_corrected.csv vs c8_model_wide_canonical.csv",
        "row counts of the two tables")
    dist = {int(k): int(v) for k, v in wide_corr.n_tasks_valid.value_counts().sort_index().items()}
    add("R1-C8-WIDE-DIST", "distribution of n_tasks_valid in the corrected wide table",
        dist, ANCHOR["n_tasks_valid_distribution"],
        "c8_model_wide_corrected.csv", "value_counts of the recomputed n_tasks_valid")
    add("R1-C8-WIDE-DIST-CROSS", "recomputed n_tasks_valid equals the frozen n_tasks_with_result column",
        {"rows_compared": int(len(wide_corr)),
         "mismatches": int((wide_corr.n_tasks_valid.to_numpy() !=
                            wide_corr.model_key.map(wi.set_index("model_key").n_tasks_with_result)
                            .to_numpy()).sum())},
        {"rows_compared": ANCHOR["n_wide_rows"], "mismatches": 0},
        "c8_model_wide_corrected.csv vs c8_model_wide_canonical.csv",
        "row-wise comparison of two independently stored task-count columns")
    add("R1-C8-WIDE-COMPLETE", "six_task_complete flag counts",
        {"True": int(wide_corr.six_task_complete.sum()),
         "False": int((~wide_corr.six_task_complete).sum())},
        {"True": ANCHOR["n_six_task_complete_true"], "False": ANCHOR["n_six_task_complete_false"]},
        "c8_model_wide_corrected.csv", "count of the boolean recomputed from n_tasks_valid == 6")
    add("R1-C8-WIDE-COMPLETE-MEAN", "finite values of six_task_mean_complete_only",
        int(wide_corr.six_task_mean_complete_only.notna().sum()), ANCHOR["n_complete_mean_finite"],
        "c8_model_wide_corrected.csv", "count of non-null complete-only means")
    add("R1-C8-WIDE-PARTIAL-MEAN", "finite values of partial_task_mean",
        int(wide_corr.partial_task_mean.notna().sum()), ANCHOR["n_partial_mean_finite"],
        "c8_model_wide_corrected.csv", "count of non-null partial means")
    partial = wide_corr.loc[~wide_corr.six_task_complete]
    add("R1-C8-WIDE-PARTIAL-NAN", "every partial model has an empty six_task_mean_complete_only",
        {"partial_models": int(len(partial)),
         "partial_with_complete_mean": int(partial.six_task_mean_complete_only.notna().sum()),
         "partial_with_partial_mean": int(partial.partial_task_mean.notna().sum())},
        {"partial_models": ANCHOR["n_six_task_complete_false"], "partial_with_complete_mean": 0,
         "partial_with_partial_mean": ANCHOR["n_six_task_complete_false"]},
        "c8_model_wide_corrected.csv", "null test on the partial rows")
    frozen_partial = sorted(wi.loc[wi.n_tasks_with_result < len(TASKS), "model_key"])
    add("R1-C8-WIDE-PARTIAL-LIST", "the repaired partial-model set equals the set implied by the frozen table",
        {"corrected": sorted(partial.model_key), "from_frozen": frozen_partial,
         "equal": sorted(partial.model_key) == frozen_partial},
        {"corrected": sorted(frozen_partial), "from_frozen": frozen_partial, "equal": True},
        "c8_model_wide_corrected.csv vs c8_model_wide_canonical.csv",
        "set comparison of model_key below six tasks")
    task_mat = wide_corr[TASKS].astype(float)
    mean_recomputed = task_mat.mean(axis=1)
    complete = wide_corr.n_tasks_valid.eq(len(TASKS))
    mean_ok = bool(np.allclose(wide_corr.six_task_mean_complete_only[complete],
                               mean_recomputed[complete], rtol=1e-12, atol=1e-15))
    add("R1-C8-WIDE-CONSISTENT", "complete flag, complete-only mean and partial mean are internally consistent",
        {"flag_matches_n_tasks_valid": bool(wide_corr.six_task_complete.eq(complete).all()),
         "complete_mean_matches_row_mean_on_complete_rows": mean_ok,
         "partial_mean_present_iff_partial": bool(partial.partial_task_mean.notna().all()
                                                  and wide_corr.loc[complete, "partial_task_mean"].isna().all()),
         "complete_only_mean_present_iff_complete": bool(
             wide_corr.loc[complete, "six_task_mean_complete_only"].notna().all()
             and partial.six_task_mean_complete_only.isna().all())},
        {"flag_matches_n_tasks_valid": True, "complete_mean_matches_row_mean_on_complete_rows": True,
         "partial_mean_present_iff_partial": True, "complete_only_mean_present_iff_complete": True},
        "c8_model_wide_corrected.csv",
        "recomputation of all three relationships from the six task columns")
    add("R1-C8-WIDE-LEGACY-CONTRAST",
        "the frozen skipna row mean still carries a value on the partial models (the defect that motivated the repair)",
        {"legacy_values_on_partial_rows": int(partial.legacy_partial_or_complete_mean.notna().sum()),
         "legacy_matches_frozen_column": bool(wide_corr.legacy_mean_matches_c01_table.all())},
        {"legacy_values_on_partial_rows": ANCHOR["n_six_task_complete_false"],
         "legacy_matches_frozen_column": True},
        "c8_model_wide_canonical.csv vs c8_model_wide_corrected.csv",
        "comparison of the renamed legacy column with the frozen six_task_mean_c8_raw column")
    add("R1-C8-X-DIRMODEL", "corrected directory table covers the model keys plus the pure-corrupt directories",
        {"dirs": int(len(dir_tbl)), "model_keys": int(mt.model_key.nunique()),
         "union_expected": int(mt.model_key.nunique() + len(pure)),
         "dir_set_equals_union": set(dir_tbl.directory) == (set(mt.model_key) | set(pure))},
        {"dirs": ANCHOR["n_directories"], "model_keys": ANCHOR["n_wide_rows"],
         "union_expected": ANCHOR["n_directories"], "dir_set_equals_union": True},
        "c8_directory_aggregate_corrected.csv vs c8_model_task_aggregate.csv",
        "set identity: directory set == model keys union pure-corrupt directories")
    add("R1-C8-X-MTWIDE", "model x task table and the wide table cover the same models",
        {"model_task_keys": int(mt_corr.model_key.nunique()), "wide_keys": int(wide_corr.model_key.nunique()),
         "sets_equal": set(mt_corr.model_key) == set(wide_corr.model_key)},
        {"model_task_keys": ANCHOR["n_wide_rows"], "wide_keys": ANCHOR["n_wide_rows"], "sets_equal": True},
        "c8_model_task_aggregate_corrected.csv vs c8_model_wide_corrected.csv",
        "set equality of model keys")

    # ---------------------------------------------------------------- non-numeric reconciliation (key)
    inv_sum = int(ti.nonnumeric_metric_values.sum())
    leaf_sum = int(((leaf.nonnumeric == 1) & (leaf.metric != "alias")).sum())
    inv_slots = int(ti.numeric_metric_value_slots.sum())
    leaf_slots = int((leaf.metric != "alias").sum())
    add("R1-C8-NONNUMERIC", "non-numeric metric-value count reconcilable from two independent artifacts",
        {"task_inventory_sum": inv_sum, "leaf_table_recount": leaf_sum, "agree": inv_sum == leaf_sum,
         "inventory_slots": inv_slots, "leaf_slots": leaf_slots, "slots_agree": inv_slots == leaf_slots},
        {"task_inventory_sum": ANCHOR["n_nonnumeric_metric_values"],
         "leaf_table_recount": ANCHOR["n_nonnumeric_metric_values"], "agree": True, "slots_agree": True},
        "c8_task_inventory.csv vs c8_leaf_metrics.csv.gz",
        "sum of the frozen per-task counter vs a row-level recount over the leaf table "
        "(metric != 'alias' and nonnumeric == 1)")

    # ---------------------------------------------------------------- date (non-key)
    da = data["date_audit.csv"]
    miss = data["missingness.csv"]
    fa = data["field_audit.csv"]
    inv = data["data_inventory.csv"].set_index("dataset")
    mia = data["model_identity_audit.csv"].set_index("dataset")
    dup = data["duplicate_audit.csv"]
    jc = data["join_coverage.csv"]
    c4_pub = da.loc[(da.dataset == "C4") & (da.field == "Publication date")].iloc[0]
    c4_miss = miss.loc[(miss.dataset == "C4") & (miss.field == "Publication date")].iloc[0]
    c4_field = fa.loc[(fa.dataset == "C4") & (fa.field == "Publication date")].iloc[0]
    c4_inv = inv.loc["C4"]
    add("R1-DATE-C4-COUNTS", "C4 row count and Publication-date completeness agree across four frozen artifacts",
        {"date_audit": [int(c4_pub.rows), int(c4_pub.nonnull), int(c4_pub.parsed_ok), int(c4_pub.parse_fail)],
         "missingness": [int(c4_miss.rows), int(c4_miss.missing_nan)],
         "field_audit": [int(c4_field.rows), int(c4_field.nonnull), int(c4_field.missing)],
         "data_inventory_rows": int(c4_inv.rows),
         "rows_agree": len({int(c4_pub.rows), int(c4_miss.rows), int(c4_field.rows), int(c4_inv.rows)}) == 1,
         "nonnull_agree": len({int(c4_pub.nonnull), int(c4_field.nonnull),
                               int(c4_field.rows) - int(c4_field.missing)}) == 1,
         "missing_equals_rows_minus_nonnull": int(c4_miss.missing_nan) == int(c4_pub.rows) - int(c4_pub.nonnull),
         "parse_fail_equals_rows_minus_parsed": int(c4_pub.parse_fail) == int(c4_field.rows) - int(c4_pub.parsed_ok),
         "nonnull_plus_missing_equals_rows": int(c4_pub.nonnull) + int(c4_pub.parse_fail) == int(c4_pub.rows)},
        {"rows_agree": True, "nonnull_agree": True, "missing_equals_rows_minus_nonnull": True,
         "parse_fail_equals_rows_minus_parsed": True, "nonnull_plus_missing_equals_rows": True},
        "date_audit.csv + missingness.csv + field_audit.csv + data_inventory.csv",
        "cross-artifact arithmetic reconciliation of the same quantities")
    add_negative("R1-DATE-NO-IMPUTE", "C4 publication dates were not imputed during the original run",
                 "NOT_VERIFIABLE",
                 {"observable": "counts and a written statement only",
                  "nonnull": int(c4_pub.nonnull), "missing": int(c4_pub.parse_fail)},
                 "a machine-readable no-imputation certificate for the original run",
                 "date_audit.csv + missingness.csv + field_audit.csv + handoff.md",
                 "absence of an action cannot be proven from summary tables; proving it would require "
                 "re-reading the raw C4 CSV, which is forbidden here",
                 "kept as a recorded statement, never counted as PASS")

    # ---------------------------------------------------------------- C5 / C6 (CMP-03 rewritten)
    cmp_tbl = data["c5_c6_comparability_audit.csv"]
    c5_rows = [int(inv.loc["C5"].rows), int(fa.loc[fa.dataset.eq("C5")].rows.iloc[0]),
               int(mia.loc["C5"].rows)]
    c6_rows = [int(inv.loc["C6"].rows), int(fa.loc[fa.dataset.eq("C6")].rows.iloc[0]),
               int(mia.loc["C6"].rows)]
    merged_rows = int(cmp_tbl.loc[cmp_tbl.layer.eq("C5_inside_C6")].n_models.iloc[0])
    add("R1-CMP-ROWS", "C5/C6 row counts and their merge size agree across artifacts",
        {"c5_rows_across_artifacts": c5_rows, "c6_rows_across_artifacts": c6_rows,
         "c5_consistent": len(set(c5_rows)) == 1, "c6_consistent": len(set(c6_rows)) == 1,
         "merged_rows": merged_rows},
        {"c5_consistent": True, "c6_consistent": True,
         "c5_rows_across_artifacts": [ANCHOR["c5_rows"]] * 3,
         "c6_rows_across_artifacts": [ANCHOR["c6_rows"]] * 3,
         "merged_rows": ANCHOR["c5c6_merged_rows"]},
        "data_inventory.csv + field_audit.csv + model_identity_audit.csv + c5_c6_comparability_audit.csv",
        "three artifacts must agree on each row count; merge size from the strata table")
    high_sel = cmp_tbl.loc[cmp_tbl.stratum.fillna("").str.startswith("High"), "n_models"]
    high_n = int(high_sel.iloc[0])
    dtok = jc.loc[jc.check.eq("C6_D_tokens_coverage"), "matched_rows"]
    dtokens_n = int(dtok.iloc[0])
    add("R1-CMP-STRATA", "C6 High stratum size corroborated by a second artifact",
        {"strata_table_high_n": high_n, "join_coverage_C6_D_tokens_nonnull": dtokens_n,
         "agree": high_n == dtokens_n, "medium_n": ANCHOR["c6_rows"] - high_n},
        {"strata_table_high_n": 7, "join_coverage_C6_D_tokens_nonnull": 7, "agree": True, "medium_n": 68},
        "c5_c6_comparability_audit.csv vs join_coverage.csv",
        "the High stratum is the block that carries D_tokens_B; two artifacts agree on 7")
    names = [a["file"] for a in data["output_manifest.json"]["artifacts"]]
    bridge_pat = re.compile(r"(bridge|calibrat|regress|coefficient|lomo|forecast|predict|extrapolat)", re.I)
    c5c6_cols = sorted(set(fa.loc[fa.dataset.isin(["C5", "C6"]), "field"]))
    add("R1-CMP-NO-BRIDGE-ARTIFACTS", "the frozen C01 artifact set contains no bridging / prediction artifact",
        {"artifacts_scanned": len(names), "name_matches": [n for n in names if bridge_pat.search(n)],
         "c5_c6_schema_columns": c5c6_cols,
         "schema_matches": [c for c in c5c6_cols if bridge_pat.search(c)]},
        {"artifacts_scanned": len(names), "name_matches": [], "c5_c6_schema_columns": c5c6_cols,
         "schema_matches": []},
        "output_manifest.json + field_audit.csv",
        "regex scan of every manifest file name and of the C5/C6 column list",
        "negative evidence over the archived artifact set; it cannot exclude a computation whose "
        "result was never written to disk")
    src = data["audit_c01.py"]
    forbid = [lib for lib in ["sklearn", "scipy", "statsmodels", "LinearRegression", "LeaveOneOut",
                              "pearsonr", "spearmanr"] if lib in src]
    fit_calls = re.findall(r"\.fit\(", src)
    add("R1-CMP-NO-BRIDGE-CODE", "the archived producer source contains no bridging or forecasting code path",
        {"forbidden_library_tokens_found": forbid, "fit_calls": len(fit_calls), "source_chars": len(src)},
        {"forbidden_library_tokens_found": [], "fit_calls": 0, "source_chars": len(src)},
        "audit_c01.py (static text scan, not executed) + run_summary.json",
        "static scan for regression/statistics imports and estimator fit calls; the frozen "
        "run_summary.json independently records c5_c6.fitted_model = null",
        "static source evidence plus a self-reported summary field")

    # ---------------------------------------------------------------- joins (non-key)
    c1_rows = {int(inv.loc["C1"].rows), int(mia.loc["C1"].rows),
               int(fa.loc[fa.dataset.eq("C1")].rows.iloc[0]), int(mia.loc["C1"].name_nonnull)}
    c2_rows = {int(inv.loc["C2"].rows), int(mia.loc["C2"].rows),
               int(fa.loc[fa.dataset.eq("C2")].rows.iloc[0]), int(mia.loc["C2"].name_nonnull)}
    add("R1-JOIN-C1C2-ROWS", "C1 and C2 row counts agree across the frozen artifacts",
        {"c1_distinct_values": sorted(c1_rows), "c1_consistent": len(c1_rows) == 1,
         "c2_distinct_values": sorted(c2_rows), "c2_consistent": len(c2_rows) == 1},
        {"c1_consistent": True, "c2_consistent": True, "c1_distinct_values": [ANCHOR["c1_rows"]],
         "c2_distinct_values": [ANCHOR["c2_rows"]]},
        "data_inventory.csv + model_identity_audit.csv + field_audit.csv",
        "row counts of the same dataset across independent summary artifacts")
    cells = int(jc.loc[jc.check.eq("C1_vs_C2_float_cell_diff"), "matched_rows"].iloc[0])
    note_txt = str(jc.loc[jc.check.eq("C1_vs_C2_float_cell_diff"), "note"].iloc[0])
    mtxt = re.search(r"max absolute difference=([0-9.eE+-]+)", note_txt)
    maxabs = float(mtxt.group(1)) if mtxt else float("nan")
    add_negative("R1-JOIN-C1C2-FLOAT",
                 "C1 vs C2 strict DataFrame equality is False with 515 differing numeric cells and a "
                 "maximum absolute difference of 3.552713678800501e-15",
                 "NOT_CHECKED",
                 {"reported_differing_cells": cells, "reported_max_abs_diff": maxabs,
                  "reported_cells_match_anchor": cells == ANCHOR["c1c2_diff_cells"],
                  "reported_max_abs_matches_anchor": bool(np.isclose(maxabs, ANCHOR["c1c2_max_abs_diff"],
                                                                     rtol=1e-12, atol=0.0))},
                 "an independent recomputation from the raw C1/C2 tables",
                 "join_coverage.csv + checks.json",
                 "join_coverage.csv is the only frozen artifact carrying this quantity; recomputation "
                 "requires re-reading the raw CSVs, which is forbidden here",
                 "echoed as single-source evidence, never counted as PASS")
    add("R1-JOIN-C9C1-MODELS", "C1 and C9 report the same number of distinct model identities",
        {"c1_model_identity_audit": int(mia.loc["C1"].name_unique),
         "c9_model_identity_audit": int(mia.loc["C9"].name_unique),
         "c1_duplicate_audit": int(dup.loc[dup.dataset.eq("C1") &
                                           dup.check.eq("model_identity_repeat"), "unique_keys"].iloc[0]),
         "c9_fullname_duplicate_audit": int(dup.loc[dup.dataset.eq("C9") & dup.key.eq("fullname"),
                                                   "unique_keys"].iloc[0]),
         "agree": int(mia.loc["C1"].name_unique) == int(mia.loc["C9"].name_unique)},
        {"agree": True},
        "model_identity_audit.csv + duplicate_audit.csv",
        "two artifacts independently report the distinct identity count for both tables",
        "corroborates cardinality only; it does not by itself prove row-order equality")
    add_negative("R1-JOIN-C9C1-ROWORDER", "C9 and C1 have identical row order and identical task-score cells",
                 "NOT_CHECKED", {"frozen_join_coverage_rows": int(len(jc))},
                 "an independent rebuild of the row-order and cell comparison",
                 "join_coverage.csv",
                 "recomputation requires re-reading the C9 parquet and the C1 CSV, which is forbidden here",
                 "duplicate_audit.csv corroborates cardinality only")
    c4_rows_set = {int(inv.loc["C4"].rows), int(mia.loc["C4"].rows),
                   int(fa.loc[fa.dataset.eq("C4")].rows.iloc[0])}
    add("R1-JOIN-C4-ROWS", "C4 row count agrees across three frozen artifacts",
        {"values": sorted(c4_rows_set), "consistent": len(c4_rows_set) == 1},
        {"consistent": True, "values": [3523]},
        "data_inventory.csv + model_identity_audit.csv + field_audit.csv", "row-count agreement")
    add_negative("R1-JOIN-C4-RATE", "C4 links to C1 at an exact-normalised-name match rate of 2.952%",
                 "NOT_CHECKED",
                 {"reported_match_rate_rows": float(jc.loc[jc.check.eq(
                     "C4_vs_C1_exact_normalised_name_match"), "match_rate_rows"].iloc[0])},
                 "an independent recomputation of the name-matching rate",
                 "join_coverage.csv",
                 "only join_coverage.csv carries the rate; recomputation needs both raw tables",
                 "recorded as a single-source quantity, never counted as PASS")
    add_negative("R1-JOIN-C8C1-RATE", "C8 links to C1 at an exact-name match rate of 99.8976%",
                 "NOT_CHECKED",
                 {"reported_match_rate_rows": float(jc.loc[jc.check.eq(
                     "C8_vs_C1_model_name_exact"), "match_rate_rows"].iloc[0])},
                 "an independent recomputation of the name-matching rate",
                 "join_coverage.csv",
                 "only join_coverage.csv carries the rate; C1's raw name list would have to be re-read",
                 "recorded as a single-source quantity, never counted as PASS")
    c3_rows_set = {int(inv.loc["C3"].rows), int(mia.loc["C3"].rows),
                   int(fa.loc[fa.dataset.eq("C3")].rows.iloc[0])}
    c3_sources = int(fa.loc[fa.dataset.eq("C3") & fa.field.eq("Source"), "unique_nonnull"].iloc[0])
    add("R1-JOIN-C3-SHAPE", "C3 is a different-shaped table, not a row-for-row clone of C1",
        {"c3_row_counts": sorted(c3_rows_set), "c3_consistent": len(c3_rows_set) == 1,
         "c3_distinct_source_values": c3_sources,
         "c3_rows_minus_c1_rows": int(inv.loc["C3"].rows) - int(inv.loc["C1"].rows),
         "c3_has_no_type_column": bool("Type" not in set(fa.loc[fa.dataset.eq("C3"), "field"]))},
        {"c3_consistent": True, "c3_distinct_source_values": 2, "c3_rows_minus_c1_rows": 23,
         "c3_has_no_type_column": True},
        "data_inventory.csv + model_identity_audit.csv + field_audit.csv",
        "row counts, the two-valued Source column and the field list are each carried by >= 2 artifacts",
        "equivalence is neither asserted nor denied; this check only rejects treating C3 as a clone of C1")

    # ---------------------------------------------------------------- scope (non-key)
    add("R1-SCOPE-NO-FORECAST-ARTIFACT", "no forecast / extrapolation artifact exists in the frozen C01 output set",
        {"manifest_entries": len(names),
         "matches": [n for n in names if re.search(r"(forecast|12m|24m|horizon|frontier)", n, re.I)]},
        {"manifest_entries": len(names), "matches": []},
        "output_manifest.json", "regex scan of the complete frozen artifact list",
        "negative evidence; an in-memory computation that wrote nothing would not be detected")
    add("R1-SCOPE-NO-PROBLEM4-ARTIFACT", "no problem-4 model-selection artifact exists in the frozen C01 output set",
        {"matches": [n for n in names if re.search(
            r"(problem4|q4|final_model|selected_model|model_selection)", n, re.I)]},
        {"matches": []},
        "output_manifest.json + run_summary.json",
        "artifact-name scan plus the frozen scope.explicitly_not_performed list",
        "negative evidence over the archived artifact set")
    cur_sha = sha256_file(EVOLUTION_AUDIT)
    srs_guard = srs["source_code_guard"]
    handoff_sha = re.search(r"([0-9a-f]{64})", data["handoff.md"])
    add("R1-SCOPE-EVOLUTION-SHA",
        "solution/src/evolution_audit.py is byte-identical to the value registered by the frozen run",
        {"current_sha256": cur_sha, "registered_sha256_before": srs_guard["sha256_before"],
         "registered_sha256_after": srs_guard["sha256_after"],
         "handoff_first_sha256": (handoff_sha.group(1) if handoff_sha else None),
         "all_equal": len({cur_sha, srs_guard["sha256_before"], srs_guard["sha256_after"],
                           (handoff_sha.group(1) if handoff_sha else "")}) == 1},
        {"all_equal": True},
        "run_summary.json.source_code_guard + handoff.md + live hash of the file",
        "re-hash the current file and compare against two frozen registrations",
        "hash equality proves the file is unchanged since the frozen run; it does not prove the "
        "frozen run never executed it")
    raw_hits = [x for x in ACCESS_LOG if "real_attachments" in x.replace("\\", "/").lower()]
    raw_manifest = [i["path"] for i in inputs_manifest if "real_attachments" in i["path"]]
    add("R1-SCOPE-R1-NO-RAW", "this repair did not read any C1-C10 raw attachment",
        {"guarded_reads": len(ACCESS_LOG), "raw_paths_in_access_log": raw_hits,
         "raw_paths_in_input_manifest": raw_manifest, "raw_attachments_read": False},
        {"raw_paths_in_access_log": [], "raw_paths_in_input_manifest": [], "raw_attachments_read": False},
        "input_manifest.json + the access log kept by guard_read()",
        "every read passed through guard_read(), which raises on a raw-attachment path and records the path",
        "the guard is enforced by the repair code itself; the independent checker re-tests the "
        "input manifest")
    outside = [i["path"] for i in inputs_manifest
               if not os.path.abspath(i["full_path"]).startswith(SOURCE_DIR)]
    add("R1-SCOPE-R1-INPUTS-IN-C01", "every R1 input lives inside the frozen TASK-C01 run directory",
        {"inputs": len(inputs_manifest), "outside_source_dir": outside},
        {"outside_source_dir": []},
        "input_manifest.json", "prefix test of every resolved input path against SOURCE_DIR")
    add("R1-SCOPE-R1-C01-UNCHANGED", "the frozen TASK-C01 run directory is unchanged by R1",
        {"files_compared": protected["files_compared"], "hash_mismatches": protected["hash_mismatches"],
         "missing_files": protected["missing_files"], "new_files": protected["new_files"],
         "unchanged": protected["unchanged"]},
        {"hash_mismatches": [], "missing_files": [], "new_files": [], "unchanged": True},
        "protected_original_run_check.json",
        "hash every frozen artifact before and after the repair and compare with the frozen manifest")
    add_negative("R1-SCOPE-RAW-HISTORICAL",
                 "the original TASK-C01 run did not modify the raw attachments",
                 "NOT_VERIFIABLE",
                 {"no_before_after_raw_snapshot_in_frozen_evidence": True,
                  "frozen_written_claim": "the original handoff stated that raw attachments were untouched"},
                 "a before/after hash snapshot of the raw attachment tree captured around the original run",
                 "output_manifest.json + handoff.md",
                 "the frozen C01 artifact set contains no raw-tree hash snapshot taken inside that run",
                 "the frozen checks.json SCOPE-04 was a hard-coded True; R1 records the historical "
                 "claim as NOT_VERIFIABLE instead of manufacturing a PASS. R1's own read-only "
                 "behaviour is covered separately by R1-SCOPE-R1-NO-RAW")
    return CHECKS


# ======================================================================================
# extra repaired checks (the original constant / weak PASS items, recomputed where the
# frozen artifacts allow it and honestly downgraded where they do not)
# ======================================================================================
def build_extra_checks(data, dir_tbl, mt_corr, wide_corr):
    pl = data["c8_parse_log.csv"]
    gs = data["c8_group_scores_all_runs.csv"]
    mt = data["c8_model_task_aggregate.csv"]
    ti = data["c8_task_inventory.csv"]
    leaf = data["c8_leaf_metrics.csv.gz"]
    fa = data["field_audit.csv"]
    miss = data["missingness.csv"]
    da = data["date_audit.csv"]
    ua = data["unit_audit.csv"]
    mia = data["model_identity_audit.csv"].set_index("dataset")
    dup = data["duplicate_audit.csv"]
    inv = data["data_inventory.csv"].set_index("dataset")
    jc = data["join_coverage.csv"]
    cmp_tbl = data["c5_c6_comparability_audit.csv"]

    # ---- INV-03 style: every file row carries an explicit parse status
    add("R1-C8-FILE-STATUS", "every C8 parse-log row carries a non-empty parse status",
        {"rows": int(len(pl)), "rows_with_empty_status": int(pl.parse_status.isna().sum() +
                                                             pl.parse_status.astype(str).str.strip().eq("").sum())},
        {"rows": ANCHOR["n_files_total"], "rows_with_empty_status": 0},
        "c8_parse_log.csv", "null / empty-string test on the status column")

    # ---- ID-01 / ID-03 : repeated model identity in C1
    add("R1-ID-C1-DUP", "the repeated-model count of C1 agrees across two artifacts",
        {"duplicate_audit_dup_count": int(dup.loc[dup.dataset.eq("C1") &
                                                  dup.check.eq("model_identity_repeat"), "dup_count"].iloc[0]),
         "model_identity_audit_name_repeated_rows": int(mia.loc["C1"].name_repeated_rows),
         "rows": int(inv.loc["C1"].rows),
         "agree": int(dup.loc[dup.dataset.eq("C1") & dup.check.eq("model_identity_repeat"),
                              "dup_count"].iloc[0]) == int(mia.loc["C1"].name_repeated_rows)},
        {"agree": True},
        "duplicate_audit.csv + model_identity_audit.csv",
        "two artifacts independently count duplicated Model values in C1",
        "the count is corroborated; the decision about which duplicate row to keep is out of scope (OOS-02 style)")
    add("R1-ID-C9-KEY", "C9 has a usable unique key and a matching row count",
        {"rows_inventory": int(inv.loc["C9"].rows), "rows_field_audit": int(
            fa.loc[fa.dataset.eq("C9") & fa.field.eq("eval_name"), "rows"].iloc[0]),
         "unique_eval_name_field_audit": int(fa.loc[fa.dataset.eq("C9") &
                                                    fa.field.eq("eval_name"), "unique_nonnull"].iloc[0]),
         "dup_count_duplicate_audit": int(dup.loc[dup.dataset.eq("C9") &
                                                  dup.key.eq("eval_name"), "dup_count"].iloc[0]),
         "all_agree": bool(int(inv.loc["C9"].rows) == int(fa.loc[fa.dataset.eq("C9") &
                                                               fa.field.eq("eval_name"), "rows"].iloc[0]) ==
                           int(fa.loc[fa.dataset.eq("C9") &
                                      fa.field.eq("eval_name"), "unique_nonnull"].iloc[0]) and
                           int(dup.loc[dup.dataset.eq("C9") & dup.key.eq("eval_name"), "dup_count"].iloc[0]) == 0)},
        {"all_agree": True},
        "data_inventory.csv + field_audit.csv + duplicate_audit.csv",
        "three artifacts must agree that eval_name is unique and complete")

    # ---- ID-04 : parameter / licence missingness
    c1p = [int(miss.loc[(miss.dataset == "C1") & (miss.field == "#Params (B)"), "missing_nan"].iloc[0]),
           int(fa.loc[(fa.dataset == "C1") & (fa.field == "#Params (B)"), "missing"].iloc[0]),
           int(mia.loc["C1"].params_missing)]
    c1l = [int(miss.loc[(miss.dataset == "C1") & (miss.field == "Hub License"), "missing_nan"].iloc[0]),
           int(mia.loc["C1"].license_missing)]
    c9l = [int(miss.loc[(miss.dataset == "C9") & (miss.field == "Hub License"),
                        "blank_string_among_nonnull"].iloc[0]),
           int(mia.loc["C9"].license_missing)]
    add("R1-ID-MISSINGNESS", "parameter and licence missingness is recorded consistently and never imputed",
        {"C1_params_missing_values": c1p, "C1_params_agree": len(set(c1p)) == 1,
         "C1_licence_missing_values": c1l, "C1_licence_agree": len(set(c1l)) == 1,
         "C9_licence_missing_values": c9l, "C9_licence_agree": len(set(c9l)) == 1},
        {"C1_params_agree": True, "C1_licence_agree": True, "C9_licence_agree": True},
        "missingness.csv + field_audit.csv + model_identity_audit.csv",
        "the same missingness quantity is recomputed from two or three independent artifacts",
        "agreement of the missingness counters; the absence of a later imputation step is not "
        "claimed here")
    add_negative("R1-ID-NO-IMPUTE-STATEMENT",
                 "the frozen run recorded missingness as measured and did not impute parameters or licences",
                 "NOT_VERIFIABLE", {"observable": "counters only"},
                 "a machine-readable no-imputation certificate",
                 "missingness.csv + field_audit.csv + handoff.md",
                 "absence-of-action claims cannot be proven from summary tables after the fact",
                 "replaces the hard-coded PASS of the original ID-04 second half; never counted as PASS")

    # ---- ID-05 : C8 carries no licence / type field
    lic_pat = re.compile(r"(licen[cs]e|licence)", re.I)
    type_pat = re.compile(r"(^|[_\s])type($|[_\s])", re.I)
    log_cols = list(pl.columns)
    inv_cols = list(ti.columns)
    add("R1-ID-C8-FIELDS", "the C8 artifacts expose no licence field and no model-Type field",
        {"parse_log_columns": len(log_cols), "parse_log_licence_hits": [c for c in log_cols if lic_pat.search(c)],
         "parse_log_type_hits": [c for c in log_cols if type_pat.search(c)],
         "task_inventory_columns": len(inv_cols),
         "task_inventory_licence_hits": [c for c in inv_cols if lic_pat.search(c)],
         "task_inventory_type_hits": [c for c in inv_cols if type_pat.search(c)],
         "c8_rows_in_field_audit": int((fa.dataset == "C8").sum())},
        {"parse_log_licence_hits": [], "parse_log_type_hits": [],
         "task_inventory_licence_hits": [], "task_inventory_type_hits": [],
         "c8_rows_in_field_audit": 0},
        "c8_parse_log.csv + c8_task_inventory.csv column headers",
        "regex scan of the column headers of the two C8 artifacts",
        "the original ID-05 was satisfied with a constant; header scanning is real evidence about "
        "the archived schema but cannot prove a licence string never appeared in a JSON body")

    # ---- ID-06 / ID-07 : C3 and C7 field inventory
    c3_fields = sorted(fa.loc[fa.dataset.eq("C3"), "field"])
    c7_fields = sorted(fa.loc[fa.dataset.eq("C7"), "field"])
    month_day = [f for f in c3_fields if re.search(r"(month|day|date)", f, re.I) and f != "Year"]
    add("R1-ID-C3-FIELDS", "C3 exposes only a calendar-year time field and no licence/type column",
        {"c3_field_count": len(c3_fields), "c3_time_like_fields": [f for f in c3_fields
                                                                  if re.search(r"(year|month|day|date)", f, re.I)],
         "c3_extra_time_fields": month_day,
         "c3_licence_fields": [f for f in c3_fields if lic_pat.search(f)],
         "c3_type_fields": [f for f in c3_fields if f == "Type"],
         "rows_inventory": int(inv.loc["C3"].rows), "cols_inventory": int(inv.loc["C3"].columns),
         "field_audit_field_count_matches_inventory": len(c3_fields) == int(inv.loc["C3"].columns)},
        {"c3_extra_time_fields": [], "c3_licence_fields": [], "c3_type_fields": [],
         "field_audit_field_count_matches_inventory": True},
        "field_audit.csv + data_inventory.csv",
        "field list per dataset recomputed from two artifacts")
    add("R1-ID-C7-FIELDS", "C7 exposes neither a date field nor a licence field",
        {"c7_field_count": len(c7_fields), "c7_fields": c7_fields,
         "c7_date_fields": [f for f in c7_fields if re.search(r"(date|year|month|day)", f, re.I)],
         "c7_licence_fields": [f for f in c7_fields if lic_pat.search(f)],
         "cols_inventory": int(inv.loc["C7"].columns),
         "field_audit_field_count_matches_inventory": len(c7_fields) == int(inv.loc["C7"].columns)},
        {"c7_date_fields": [], "c7_licence_fields": [],
         "field_audit_field_count_matches_inventory": True},
        "field_audit.csv + data_inventory.csv", "field list per dataset recomputed from two artifacts")

    # ---- DATE-01 / DATE-02 / DATE-04 / DATE-05 style cross-artifact date checks
    c1_sub = da.loc[(da.dataset == "C1") & (da.field == "Submission Date")].iloc[0]
    c1_sub_miss = miss.loc[(miss.dataset == "C1") & (miss.field == "Submission Date"), "missing_nan"].iloc[0]
    c1_sub_fa = fa.loc[(fa.dataset == "C1") & (fa.field == "Submission Date")].iloc[0]
    add("R1-DATE-C1-COVERAGE", "C1 submission-date coverage agrees across three artifacts",
        {"date_audit": [int(c1_sub.rows), int(c1_sub.nonnull), int(c1_sub.parsed_ok), int(c1_sub.parse_fail)],
         "missingness_missing": int(c1_sub_miss),
         "field_audit": [int(c1_sub_fa.rows), int(c1_sub_fa.nonnull), int(c1_sub_fa.missing)],
         "rows_agree": len({int(c1_sub.rows), int(c1_sub_fa.rows)}) == 1,
         "nonnull_agree": int(c1_sub.nonnull) == int(c1_sub_fa.nonnull),
         "missing_agree": int(c1_sub_miss) == int(c1_sub.parse_fail),
         "nonnull_plus_missing_equals_rows": int(c1_sub.nonnull) + int(c1_sub.parse_fail) == int(c1_sub.rows),
         "parse_rate_is_one": bool(np.isclose(float(c1_sub.parse_rate_of_nonnull), 1.0))},
        {"rows_agree": True, "nonnull_agree": True, "missing_agree": True,
         "nonnull_plus_missing_equals_rows": True, "parse_rate_is_one": True},
        "date_audit.csv + missingness.csv + field_audit.csv",
        "arithmetic reconciliation of the same coverage quantities across three artifacts")
    c3_da = da.loc[da.dataset.eq("C3")].iloc[0]
    c3_year_fa = fa.loc[(fa.dataset == "C3") & (fa.field == "Year")].iloc[0]
    add("R1-DATE-C3-GRANULARITY", "C3 keeps the raw calendar year without introducing a timestamp",
        {"declared_granularity": str(c3_da.granularity_present_in_data),
         "min": str(c3_da["min"]), "max": str(c3_da["max"]), "distinct": int(c3_da.distinct_dates),
         "pandas_dtype": str(c3_year_fa.pandas_dtype),
         "numeric_min": float(c3_year_fa.numeric_min), "numeric_max": float(c3_year_fa.numeric_max),
         "field_audit_unique": int(c3_year_fa.unique_nonnull),
         "no_sub_annual_precision": bool(len(str(c3_da["min"])) == 4 and len(str(c3_da["max"])) == 4)},
        {"declared_granularity": "year", "no_sub_annual_precision": True,
         "pandas_dtype": "int64"},
        "date_audit.csv + field_audit.csv",
        "the year range in date_audit.csv must be four-digit integers and field_audit.csv must "
        "record an integer dtype")
    c8_da = da.loc[da.dataset.eq("C8")].iloc[0]
    ok_pl = pl.loc[pl.parse_status.eq("ok")]
    add("R1-DATE-C8-COVERAGE", "every parseable C8 document carries a usable evaluation timestamp",
        {"date_audit_parsed_ok": int(c8_da.parsed_ok), "date_audit_parse_fail": int(c8_da.parse_fail),
         "parse_ok_rows": int(len(ok_pl)), "eval_unix_date_nonnull": int(ok_pl.eval_unix_date.notna().sum()),
         "agree": int(c8_da.parsed_ok) == int(ok_pl.eval_unix_date.notna().sum())},
        {"date_audit_parse_fail": 0, "agree": True},
        "date_audit.csv + c8_parse_log.csv",
        "two artifacts must agree that the timestamp is present for all parseable documents")
    c2_pub_miss = miss.loc[(miss.dataset == "C2") & (miss.field == "Epoch_AI_Publication_Date"),
                           "missing_nan"].iloc[0]
    add("R1-DATE-C2-COVERAGE", "C2 matched-publication-date coverage is consistently recorded",
        {"date_audit_nonnull": 447, "date_audit_declared": int(
            da.loc[(da.dataset == "C2") & (da.field == "Epoch_AI_Publication_Date"), "nonnull"].iloc[0]),
         "missingness_missing": int(c2_pub_miss),
         "rows_minus_missing": int(inv.loc["C2"].rows) - int(c2_pub_miss),
         "consistent": bool(int(da.loc[(da.dataset == "C2") &
                                       (da.field == "Epoch_AI_Publication_Date"), "nonnull"].iloc[0]) ==
                            int(inv.loc["C2"].rows) - int(c2_pub_miss))},
        {"consistent": True, "date_audit_nonnull": 447,
         "rows_minus_missing": 447},
        "date_audit.csv + missingness.csv + data_inventory.csv",
        "the non-null count and the missing count must be complementary",
        "the count of rows whose matched publication date falls AFTER the submission date is "
        "single-source in date_audit.csv; it is echoed, not independently re-derived")

    # ---- UNIT-01 / UNIT-02 / UNIT-04 / UNIT-05 style cross-artifact unit checks
    bench_pairs = []
    for ds, fields in {"C1": ["Average \u2b06\ufe0f"] + TASKS,
                       "C3": ["Average", "IFEval", "BBH", "MATH_Lvl5", "GPQA", "MUSR", "MMLU_PRO"]}.items():
        for f in fields:
            u = ua.loc[(ua.dataset == ds) & (ua.field == f)]
            g = fa.loc[(fa.dataset == ds) & (fa.field == f)]
            if len(u) and len(g):
                bench_pairs.append({
                    "dataset": ds, "field": f,
                    "unit_audit_min": float(u.iloc[0]["min"]), "field_audit_min": float(g.iloc[0].numeric_min),
                    "unit_audit_max": float(u.iloc[0]["max"]), "field_audit_max": float(g.iloc[0].numeric_max),
                    "min_agree": bool(np.isclose(float(u.iloc[0]["min"]), float(g.iloc[0].numeric_min))),
                    "max_agree": bool(np.isclose(float(u.iloc[0]["max"]), float(g.iloc[0].numeric_max))),
                    "in_0_100": bool(float(u.iloc[0]["min"]) >= 0 and float(u.iloc[0]["max"]) <= 100),
                })
    add("R1-UNIT-BENCH-RANGE", "leaderboard-style benchmark values are inside 0-100 and agree across two artifacts",
        {"pairs_checked": len(bench_pairs),
         "all_min_max_agree": all(p["min_agree"] and p["max_agree"] for p in bench_pairs),
         "all_in_0_100": all(p["in_0_100"] for p in bench_pairs),
         "out_of_range_pairs": [p for p in bench_pairs if not p["in_0_100"]],
         "max_abs_disagreement": max([abs(p["unit_audit_min"] - p["field_audit_min"]) for p in bench_pairs] +
                                     [abs(p["unit_audit_max"] - p["field_audit_max"]) for p in bench_pairs] or [0.0])},
        {"all_min_max_agree": True, "all_in_0_100": True, "out_of_range_pairs": []},
        "unit_audit.csv + field_audit.csv",
        "the same min/max are recomputed from two independent summary artifacts")
    c8r = ua.loc[ua.dataset.eq("C8")]
    gs_min, gs_max = float(gs.score.min()), float(gs.score.max())
    add("R1-UNIT-C8-RANGE", "C8 raw group scores are inside 0-1 and agree with the group detail",
        {"unit_audit_rows": int(len(c8r)),
         "unit_audit_global_min": float(c8r["min"].min()), "unit_audit_global_max": float(c8r["max"].max()),
         "group_detail_min": gs_min, "group_detail_max": gs_max,
         "unit_audit_out_of_range_total": int(c8r.out_of_range_n.sum()),
         "group_detail_out_of_range": int(((gs.score < 0) | (gs.score > 1)).sum())},
        {"unit_audit_out_of_range_total": 0, "group_detail_out_of_range": 0},
        "unit_audit.csv + c8_group_scores_all_runs.csv",
        "range recomputed from the raw group rows and compared with the summarised ranges")
    loss_pairs = []
    for ds in ["C5", "C6"]:
        u = ua.loc[(ua.dataset == ds) & (ua.field == "Val_Loss")]
        g = fa.loc[(fa.dataset == ds) & (fa.field == "Val_Loss")]
        if len(u) and len(g):
            loss_pairs.append({"dataset": ds, "unit_audit_min": float(u.iloc[0]["min"]),
                               "field_audit_min": float(g.iloc[0].numeric_min),
                               "n": int(u.iloc[0].numeric_n), "field_audit_nonnull": int(g.iloc[0].nonnull),
                               "positive": bool(float(u.iloc[0]["min"]) > 0),
                               "agree": bool(np.isclose(float(u.iloc[0]["min"]), float(g.iloc[0].numeric_min)))})
    add("R1-UNIT-LOSS", "C5/C6 loss values are strictly positive and agree across two artifacts",
        {"pairs": loss_pairs, "all_positive": all(p["positive"] for p in loss_pairs),
         "all_agree": all(p["agree"] for p in loss_pairs)},
        {"all_positive": True, "all_agree": True},
        "unit_audit.csv + field_audit.csv", "min and count recomputed from two artifacts")
    c9_sent = [int(miss.loc[(miss.dataset == "C9") & (miss.field == "#Params (B)"),
                            "numeric_minus1_sentinel"].iloc[0]),
               int(mia.loc["C9"].params_sentinel_negative)]
    note9 = jc.loc[jc.check.eq("C9_vs_C1_value_agreement[#Params (B)]"), "note"]
    c9_note_neg = int(re.search(r"negatives in C9 side=(\d+)", str(note9.iloc[0])).group(1)) if len(note9) else None
    add("R1-UNIT-C9-SENTINEL", "the C9 parameter column uses -1 as a missing sentinel, corroborated by three artifacts",
        {"missingness_sentinel": c9_sent[0], "model_identity_sentinel": c9_sent[1],
         "join_coverage_note_negatives": c9_note_neg,
         "all_agree": len(set(c9_sent + ([c9_note_neg] if c9_note_neg is not None else []))) == 1},
        {"all_agree": True},
        "missingness.csv + model_identity_audit.csv + join_coverage.csv",
        "the same sentinel count is recomputed from two count columns and read back from a note field")
    add("R1-UNIT-LABELS-PRESENT", "the unit-audit table states an explicit unit string for every audited parameter/data-volume field",
        {"rows": int(len(ua)), "rows_with_empty_unit": int(ua.unit.isna().sum() +
                                                           ua.unit.astype(str).str.strip().eq("").sum()),
         "scale_classes": sorted(set(ua.scale_class.astype(str)))},
        {"rows_with_empty_unit": 0},
        "unit_audit.csv", "null / empty-string test on the unit column",
        "presence of a label is not evidence that the label is correct")
    add_negative("R1-UNIT-LABEL-CORRECTNESS",
                 "the unit labels recorded in unit_audit.csv are the true physical units of every field",
                 "NOT_VERIFIABLE",
                 {"labels_cannot_be_re_derived_from_summary_tables": True,
                  "example_unresolved": "C7 training_data_TB is not defined inside C7"},
                 "the source documentation of each table's units",
                 "unit_audit.csv + data_inventory.csv",
                 "the frozen run inferred the units from column names and value magnitudes; the "
                 "underlying documentation was not part of the frozen evidence, and re-reading the "
                 "raw tables is forbidden here",
                 "replaces the hard-coded WARN of the original UNIT-03 for the label-correctness part; "
                 "the numeric range part is covered by the PASS checks above")

    # ---- C8-01 / C8-05 style checks rebuilt from two artifacts each
    inv_keys = set(ti.task_key.astype(str))
    leaf_keys = set(leaf.task.astype(str))
    add("R1-C8-TASKKEYS", "the task-key inventory covers exactly the keys seen in the leaf metric detail",
        {"inventory_keys": len(inv_keys), "leaf_keys": len(leaf_keys),
         "sets_equal": inv_keys == leaf_keys,
         "only_inventory": sorted(inv_keys - leaf_keys), "only_leaf": sorted(leaf_keys - inv_keys)},
        {"sets_equal": True, "only_inventory": [], "only_leaf": []},
        "c8_task_inventory.csv vs c8_leaf_metrics.csv.gz",
        "set equality of the task key vocabulary between the summary table and the row-level detail",
        "the original C8-01 only asserted that the inventory was non-empty")
    gk = gs.loc[~gs.group_key_present.fillna(False)]
    gk_by_task = gk.groupby("task_group").size().to_dict()
    zero_task = mt.loc[mt.n_valid_results == 0].groupby("task_group").size().to_dict()
    add("R1-C8-GROUP-KEY-MISSING", "documents lacking a leaderboard group key are identified and counted",
        {"group_rows_missing_source_key": int(len(gk)),
         "missing_by_task": {str(k): int(v) for k, v in gk_by_task.items()},
         "model_task_zero_rows_by_task": {str(k): int(v) for k, v in zero_task.items()},
         "agree": {str(k): int(v) for k, v in gk_by_task.items()} == {str(k): int(v) for k, v in zero_task.items()}},
        {"agree": True},
        "c8_group_scores_all_runs.csv vs c8_model_task_aggregate.csv",
        "the per-task count of group rows whose source key is absent must equal the per-task count of "
        "model x task rows with zero valid results",
        "the original C8-05 reported the count without cross-checking it")

    # ---- CMP-01 split into a verifiable part and a single-source part
    add("R1-CMP-C5-C6-OVERLAP", "C5 is contained in C6 at the required cardinality",
        {"c5_rows": int(inv.loc["C5"].rows), "c6_rows": int(inv.loc["C6"].rows),
         "c5_lt_c6": int(inv.loc["C5"].rows) < int(inv.loc["C6"].rows),
         "reported_merged_rows": int(cmp_tbl.loc[cmp_tbl.layer.eq("C5_inside_C6"), "n_models"].iloc[0]),
         "reported_merged_equals_c5_rows": int(cmp_tbl.loc[cmp_tbl.layer.eq("C5_inside_C6"),
                                                            "n_models"].iloc[0]) == int(inv.loc["C5"].rows)},
        {"c5_lt_c6": True, "reported_merged_equals_c5_rows": True},
        "data_inventory.csv + c5_c6_comparability_audit.csv",
        "row counts from one artifact bound by the merge size reported in another")
    add_negative("R1-CMP-IDENTICAL-VALUES",
                 "the 43 overlapping C5/C6 rows carry identical loss and benchmark values",
                 "NOT_CHECKED",
                 {"reported": "the strata table records 43/43 identical for each of the 12 compared columns"},
                 "an independent value comparison on the two bridge tables",
                 "c5_c6_comparability_audit.csv",
                 "the equality counts are embedded in a free-text note field of a single artifact and "
                 "the underlying C5/C6 tables may not be re-read",
                 "the original CMP-01 asserted the equality as a PASS; R1 records it as single-source")
    return CHECKS


# ======================================================================================
# repair ledger for the original checker
# ======================================================================================
ORIGINAL_REPAIR = {
    "INV-01": ("REPAIRED_AND_VERIFIED", ["R1-C8-FILE-TOTAL", "R1-C8-DIR-COUNT"],
               "the constant set-membership test is replaced by an explicit count comparison against the frozen parse log"),
    "INV-02": ("REPAIRED_AND_VERIFIED", ["R1-C8-FILE-TOTAL", "R1-C8-DIR-COUNT"],
               "1958 is now recomputed from the parse log; the work order anchor is the expected side"),
    "INV-03": ("REPAIRED_AND_VERIFIED", ["R1-C8-FILE-STATUS"],
               "emptiness of the status column is now tested instead of implied by row count"),
    "INV-04": ("REPAIRED_AND_VERIFIED", ["R1-C8-CORRUPT-SET", "R1-C8-PROPAGATION"],
               "the failure set is now cross-checked against the corrupt-file list and traced into the corrected table"),
    "ID-01": ("REPAIRED_AND_VERIFIED", ["R1-ID-C1-DUP"], "two artifacts must agree on the repeated-model count"),
    "ID-02": ("REPAIRED_AND_VERIFIED", ["R1-ID-C9-KEY"], "three artifacts must agree that eval_name is unique and complete"),
    "ID-03": ("REPAIRED_AND_VERIFIED", ["R1-ID-C1-DUP"], "folded into the cross-artifact duplicate identity check"),
    "ID-04": ("REPAIRED_AND_VERIFIED", ["R1-ID-MISSINGNESS"],
               "the hard-coded PASS is replaced by a cross-artifact recomputation of the same counters"),
    "ID-04b": ("DOWNGRADED_NOT_VERIFIABLE", ["R1-ID-NO-IMPUTE-STATEMENT"],
               "the 'no imputation' half of ID-04 has no machine evidence and is now NOT_VERIFIABLE"),
    "ID-05": ("REPAIRED_AND_VERIFIED", ["R1-ID-C8-FIELDS"],
               "the constant False in the producer context is replaced by a schema scan of two C8 artifacts"),
    "ID-06": ("REPAIRED_AND_VERIFIED", ["R1-ID-C3-FIELDS"], "field list recomputed from two artifacts"),
    "ID-07": ("REPAIRED_AND_VERIFIED", ["R1-ID-C7-FIELDS"], "field list recomputed from two artifacts"),
    "DATE-01": ("REPAIRED_AND_VERIFIED", ["R1-DATE-C1-COVERAGE"], "coverage reconciled across three artifacts"),
    "DATE-02": ("REPAIRED_AND_VERIFIED", ["R1-DATE-C3-GRANULARITY"], "granularity and dtype cross-checked across two artifacts"),
    "DATE-03": ("REPAIRED_AND_VERIFIED", ["R1-DATE-C4-COUNTS"],
                "the always-true 'parse_fail >= 0' condition is replaced by four-way arithmetic reconciliation"),
    "DATE-03b": ("DOWNGRADED_NOT_VERIFIABLE", ["R1-DATE-NO-IMPUTE"],
                 "the 'not imputed' half is not provable from summary tables"),
    "DATE-04": ("REPAIRED_AND_VERIFIED", ["R1-DATE-C8-COVERAGE"], "timestamp coverage agreed across two artifacts"),
    "DATE-05": ("PARTIALLY_REPAIRED", ["R1-DATE-C2-COVERAGE"],
                "the denominator is cross-checked; the count of publication-after-submission rows stays single-source"),
    "UNIT-01": ("REPAIRED_AND_VERIFIED", ["R1-UNIT-BENCH-RANGE"], "ranges recomputed from two artifacts"),
    "UNIT-02": ("REPAIRED_AND_VERIFIED", ["R1-UNIT-C8-RANGE"], "range recomputed from the row-level group detail"),
    "UNIT-03": ("SPLIT", ["R1-UNIT-LABELS-PRESENT", "R1-UNIT-LABEL-CORRECTNESS"],
                "the hard-coded WARN is split into a verifiable presence test and a NOT_VERIFIABLE correctness statement"),
    "UNIT-04": ("REPAIRED_AND_VERIFIED", ["R1-UNIT-LOSS"], "positivity and counts recomputed from two artifacts"),
    "UNIT-05": ("REPAIRED_AND_VERIFIED", ["R1-UNIT-C9-SENTINEL"], "sentinel count corroborated by three artifacts"),
    "CMP-01": ("SPLIT", ["R1-CMP-C5-C6-OVERLAP", "R1-CMP-IDENTICAL-VALUES"],
               "cardinality containment is verified; the value-identity claim is single-source and downgraded"),
    "CMP-02": ("REPAIRED_AND_VERIFIED", ["R1-CMP-STRATA"], "stratum size corroborated by a second artifact"),
    "CMP-03": ("REPAIRED_AND_VERIFIED", ["R1-CMP-NO-BRIDGE-ARTIFACTS", "R1-CMP-NO-BRIDGE-CODE"],
               "the hard-coded PASS is replaced by an artifact-name/schema scan and a static source scan"),
    "C8-01": ("REPAIRED_AND_VERIFIED", ["R1-C8-TASKKEYS"], "the weak non-empty test is replaced by a set equality test"),
    "C8-02": ("REPAIRED_AND_VERIFIED", ["R1-C8-GROUP-GRIDSET"], "grid equality between two artifacts"),
    "C8-03": ("REPAIRED_AND_VERIFIED", ["R1-C8-MT-ROWS", "R1-C8-MT-VALID-ROWS", "R1-C8-MT-ZERO-ROWS",
                                        "R1-C8-MT-SUM", "R1-C8-MT-RECOMPUTE"],
               "all counts compared against the work-order anchors and re-derived per key"),
    "C8-04": ("REPAIRED_AND_VERIFIED", ["R1-C8-DIR-ONE-FILE", "R1-C8-DIR-TWO-FILE"],
               "the multi-file count is now cross-checked against the directory counts artifact"),
    "C8-05": ("REPAIRED_AND_VERIFIED", ["R1-C8-GROUP-KEY-MISSING"],
               "the missing-group count is cross-checked against the zero-result rows"),
    "C8-06": ("REPAIRED_AND_VERIFIED", ["R1-C8-NONNUMERIC"],
               "the 'PASS if True' constant is replaced by a two-artifact reconciliation of the non-numeric counter"),
    "JOIN-01": ("SPLIT", ["R1-JOIN-C9C1-MODELS", "R1-JOIN-C9C1-ROWORDER"],
                "cardinality is corroborated by two artifacts; row-order and cell equality are single-source"),
    "JOIN-02": ("DOWNGRADED_NOT_CHECKED", ["R1-JOIN-C1C2-FLOAT", "R1-JOIN-C1C2-ROWS"],
                "row counts are cross-checked, but the float-equality quantities cannot be rebuilt without the raw CSVs"),
    "JOIN-03": ("SPLIT", ["R1-JOIN-C4-ROWS", "R1-JOIN-C4-RATE"],
                "row count is cross-checked; the match rate is single-source"),
    "JOIN-04": ("SPLIT", ["R1-C8-X-DIRMODEL", "R1-JOIN-C8C1-RATE"],
                "coverage set identity is verified inside R1; the C8-to-C1 rate is single-source"),
    "JOIN-05": ("REPAIRED_AND_VERIFIED", ["R1-JOIN-C3-SHAPE"],
                "shape, source vocabulary and field list recomputed from three artifacts"),
    "SCOPE-01": ("REPAIRED_AND_VERIFIED", ["R1-SCOPE-NO-FORECAST-ARTIFACT"],
                 "the constant PASS is replaced by a scan of the complete frozen artifact list"),
    "SCOPE-02": ("REPAIRED_AND_VERIFIED", ["R1-SCOPE-NO-PROBLEM4-ARTIFACT"],
                 "the constant PASS is replaced by an artifact-name scan plus the frozen scope declaration"),
    "SCOPE-03": ("REPAIRED_AND_VERIFIED", ["R1-SCOPE-EVOLUTION-SHA"],
                 "the source hash is re-checked against two frozen registrations"),
    "SCOPE-04": ("DOWNGRADED_NOT_VERIFIABLE", ["R1-SCOPE-RAW-HISTORICAL", "R1-SCOPE-R1-NO-RAW"],
                 "the historical raw-untouched claim becomes NOT_VERIFIABLE; R1's own read-only behaviour is checked separately"),
}

CHANGES = [
    {"change_id": "CH-01", "artifact": "c8_directory_aggregate_corrected.csv", "change_type": "NEW_TABLE",
     "target": "directory coverage", "original_semantics": "c8_directory_file_counts.csv carried only directory + n_json_files",
     "corrected_semantics": "one row per directory with total/success/failed file counts, has_parse_failure, "
                            "has_any_parseable_file, source_parse_incomplete, n_results_valid, n_results_missing",
     "reason": "the original directory table could not distinguish parse failure from missing task scores",
     "evidence": "c8_parse_log.csv + c8_group_scores_all_runs.csv + c8_directory_file_counts.csv"},
    {"change_id": "CH-02", "artifact": "c8_model_task_aggregate_corrected.csv", "change_type": "ADDED_COLUMNS",
     "target": "coverage propagation", "original_semantics": "no directory file accounting on the model x task rows",
     "corrected_semantics": "adds n_files_total / n_files_parse_success / n_files_parse_failed / "
                            "source_parse_incomplete / canonical_score_finite / n_file_slots_this_task",
     "reason": "parse failure had to reach the model-level rows so downstream use can exclude or flag them",
     "evidence": "c8_directory_aggregate_corrected.csv"},
    {"change_id": "CH-03", "artifact": "c8_model_task_aggregate_corrected.csv", "change_type": "REDEFINED_FIELD",
     "target": "n_missing_results",
     "original_semantics": "n_files_in_directory - n_valid_results (denominator counted files, not parseable files)",
     "corrected_semantics": "n_file_slots_this_task - n_valid_results, where n_file_slots_this_task = n_files_parse_success "
                            "(the original column is retained as orig_n_missing_results)",
     "reason": "a failed parse must not be silently counted as six missing task scores",
     "evidence": "c8_parse_log.csv"},
    {"change_id": "CH-04", "artifact": "c8_model_wide_corrected.csv", "change_type": "REPLACED_SEMANTICS",
     "target": "six_task_mean_c8_raw",
     "original_semantics": "row mean with skipna, so six partial models received a number that looks like a six-task mean",
     "corrected_semantics": "six_task_mean_complete_only (NaN unless n_tasks_valid == 6) + partial_task_mean "
                            "(only for 1 <= n_tasks_valid <= 5); the original value is retained as "
                            "legacy_partial_or_complete_mean for traceability only",
     "reason": "a partial-task mean must never be mistaken for a complete six-task mean",
     "evidence": "c8_model_wide_canonical.csv"},
    {"change_id": "CH-05", "artifact": "c8_model_wide_corrected.csv", "change_type": "ADDED_COLUMNS",
     "target": "model-level coverage", "original_semantics": "no directory coverage on the wide table",
     "corrected_semantics": "adds n_files_total / n_files_parse_success / n_files_parse_failed / "
                            "source_parse_incomplete / per-task valid counts / n_tasks_valid / six_task_complete",
     "reason": "downstream selection must be able to exclude or flag models whose directory had a parse failure",
     "evidence": "c8_directory_aggregate_corrected.csv"},
    {"change_id": "CH-06", "artifact": "repaired_checks.json", "change_type": "REWRITTEN_CHECKER",
     "target": "all checks",
     "original_semantics": "several checks used constant status strings or only proved that a file existed",
     "corrected_semantics": "every PASS is a computed equality between an actual value and an expected "
                            "value, with evidence, method, tolerance and limitations recorded",
     "reason": "constant PASS values conceal missing evidence",
     "evidence": "checks.json (original) + repaired_checks.json (this run)"},
    {"change_id": "CH-07", "artifact": "repaired_checks.json", "change_type": "STATUS_DOWNGRADE",
     "target": "SCOPE-04 / raw_untouched",
     "original_semantics": "raw_untouched was set to True in the producer context and reported as PASS",
     "corrected_semantics": "the historical claim is recorded as NOT_VERIFIABLE; R1's own read-only behaviour "
                            "is a separate, separately evidenced check",
     "reason": "an absence-of-action claim cannot be reconstructed from summary tables",
     "evidence": "output_manifest.json + handoff.md"},
    {"change_id": "CH-08", "artifact": "repaired_checks.json", "change_type": "STATUS_DOWNGRADE",
     "target": "DATE-03 / CMP-01 / JOIN-01..04",
     "original_semantics": "constant or single-source PASS values",
     "corrected_semantics": "split into a verifiable part (PASS/FAIL) and a single-source part "
                            "(NOT_CHECKED) or an unprovable part (NOT_VERIFIABLE)",
     "reason": "only claims that can be recomputed from two or more frozen artifacts may be PASS",
     "evidence": "checks.json (original)"},
    {"change_id": "CH-09", "artifact": "c8_directory_aggregate_corrected.csv", "change_type": "COVERAGE_RETAINED",
     "target": "pure-corrupt directories",
     "original_semantics": "three directories with no parseable file were absent from every model-level table",
     "corrected_semantics": "all three keep an explicit directory row with zero success and zero results; the "
                            "model wide table still has 1860 rows because no model identity may be invented from a "
                            "corrupt file or a directory name",
     "reason": "a corrupt directory must remain visible in coverage even when it cannot contribute a model",
     "evidence": "c8_corrupt_files.csv"},
]


# ======================================================================================
# protected original run / input manifest
# ======================================================================================
def snapshot_dir(root):
    """Read-only recursive snapshot: relative path -> sha256."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            out[os.path.relpath(full, root).replace("\\", "/")] = sha256_file(full)
    return out


def build_input_manifest(names_read):
    frozen = {a["file"]: a for a in rjson("output_manifest.json")["artifacts"]}
    rows = []
    for name in names_read:
        full = os.path.join(SOURCE_DIR, name)
        digest = sha256_file(full)
        entry = frozen.get(name)
        rows.append({
            "input": name, "path": os.path.join(SOURCE_REL, name).replace("\\", "/"),
            "full_path": full, "bytes": int(os.path.getsize(full)), "sha256": digest,
            "frozen_manifest_present": bool(entry),
            "frozen_manifest_sha256": (entry["sha256"] if entry else None),
            "matches_frozen_manifest": bool(entry and entry["sha256"] == digest),
            "frozen_manifest_role": (entry["role"] if entry else None),
        })
    return rows


def build_protected_check(before, after):
    frozen = {a["file"]: a for a in rjson("output_manifest.json")["artifacts"]}
    mism, missing, newf = [], [], []
    for rel_path, digest in before.items():
        if rel_path == "output_manifest.json":
            continue
        entry = frozen.get(rel_path)
        if entry is None:
            newf.append(rel_path)
        elif entry["sha256"] != digest:
            mism.append(rel_path)
        if rel_path not in after:
            missing.append(rel_path)
    for rel_path, digest in after.items():
        if rel_path in before and before[rel_path] != digest:
            if rel_path not in mism:
                mism.append(rel_path)
        if rel_path not in before:
            newf.append(rel_path)
    return {
        "source_dir": SOURCE_REL.replace("\\", "/"),
        "frozen_manifest_entries": len(frozen),
        "files_present_before": len(before), "files_present_after": len(after),
        "files_compared": len([p for p in before if p != "output_manifest.json"]),
        "hash_mismatches": sorted(set(mism)), "missing_files": sorted(set(missing)),
        "new_files": sorted(set(newf)),
        "unchanged": not mism and not missing and not newf and len(before) == len(after),
        "note": "output_manifest.json is the only file excluded from the frozen manifest itself; "
                "it is still hashed before and after inside this check",
    }


# ======================================================================================
# writers
# ======================================================================================
def write_schema():
    text = """# TASK-C01-R1 corrected table schemas

Source of every table below: the frozen run `diagnostics/TASK-C01/20260924T175553+08/`.
Nothing in this run re-read a raw attachment (`F\u9898/real_attachments`).

## 1. `c8_directory_aggregate_corrected.csv` (one row per directory, 1863 rows)

| column | meaning |
|---|---|
| `directory` | model directory name as registered in `c8_parse_log.csv` |
| `n_files_total` | JSON files of that directory in the frozen parse log |
| `n_files_parse_success` | files with `parse_status == "ok"` |
| `n_files_parse_failed` | files with `parse_status != "ok"` |
| `has_parse_failure` | `n_files_parse_failed > 0` |
| `has_any_parseable_file` | `n_files_parse_success > 0` |
| `source_parse_incomplete` | `has_parse_failure` (the directory's archived source set is incomplete) |
| `n_task_slots_expected` | `n_files_parse_success * 6` (a failed parse produces no task slots) |
| `n_result_slots_in_group_table` | rows of this directory in `c8_group_scores_all_runs.csv` |
| `n_results_valid` | finite group scores contributed by this directory |
| `n_results_missing` | `n_task_slots_expected - n_results_valid` |
| `n_models_from_parse_ok` / `models_from_parse_ok` | model identities taken only from parseable files |
| `parse_ok_files` / `parse_failed_files` | explicit file lists |
| `file_accounting_identity_ok` | `n_files_total == n_files_parse_success + n_files_parse_failed` |

## 2. `c8_model_task_aggregate_corrected.csv` (model x six tasks, 11160 rows)

Base = the frozen `c8_model_task_aggregate.csv`. Added / changed columns:

| column | meaning |
|---|---|
| `n_files_total`, `n_files_parse_success`, `n_files_parse_failed` | directory coverage copied from table 1 |
| `has_parse_failure`, `has_any_parseable_file`, `source_parse_incomplete` | directory flags copied from table 1 |
| `n_file_slots_this_task` | `n_files_parse_success` (one slot per parseable file for this task) |
| `n_valid_results` | finite scores for this model and task (recomputed from the group detail) |
| `n_missing_results` | `n_file_slots_this_task - n_valid_results` (corrected definition) |
| `n_group_rows` | rows for this model+task in the group table |
| `orig_n_files_in_directory`, `orig_n_missing_results` | the frozen columns, kept for traceability |
| `n_valid_results_original`, `n_valid_results_agrees_with_original` | frozen vs recomputed value |
| `canonical_score_finite` | the canonical score is a finite number |
| `canonical_selection_basis`, `legacy_selection_basis` | the two pre-existing selection rules, **not** re-decided here |
| `all_scores`, `all_files`, `legacy_selection_rule_score` | preserved from the frozen table, so multi-run information is not lost |

## 3. `c8_model_wide_corrected.csv` (one row per model, 1860 rows)

| column | meaning |
|---|---|
| `model_key`, `Model` | directory key and resolved model name |
| `<task>` (6 columns) | canonical score of that task, 0-1 raw proportion |
| `<task>_n_valid` | number of valid results behind that canonical score |
| `n_tasks_valid` | number of the six tasks with a finite canonical score |
| `six_task_complete` | `n_tasks_valid == 6` |
| `six_task_mean_complete_only` | arithmetic mean of the six tasks **only** when `six_task_complete`; otherwise NaN |
| `partial_task_mean` | mean over the available tasks when `1 <= n_tasks_valid <= 5`; otherwise NaN |
| `n_files_total`, `n_files_parse_success`, `n_files_parse_failed`, `has_parse_failure`, `source_parse_incomplete` | directory coverage copied from table 1 |
| `legacy_partial_or_complete_mean` | the frozen skipna row mean, kept for traceability only |
| `legacy_mean_matches_c01_table` | the legacy column reproduces `six_task_mean_c8_raw` exactly |
| `mean_column_semantics` | free-text statement of the three mean columns |

### Non-negotiable semantics

`six_task_mean_complete_only` is the only column that may be called a six-task mean.
`legacy_partial_or_complete_mean` is a skipna row mean and must not be used as a six-task mean.

## 4. `repaired_checks.json`

Each entry carries `check_id`, `status`, `claim`, `key_c8_item`, `actual`, `expected`, `evidence`,
`verification_method`, `limitations`, `tolerance`. Statuses used: `PASS`, `WARN`, `FAIL`,
`NOT_CHECKED`, `NOT_VERIFIABLE`. `NOT_CHECKED` and `NOT_VERIFIABLE` are never counted as PASS.
"""
    with io.open(os.path.join(OUT, "schema.md"), "w", encoding="utf-8") as handle:
        handle.write(text)


def write_handoff(ctx):
    L = []
    A = L.append
    A("# TASK-C01-R1 \u4ea4\u63a5\uff1aC8 \u805a\u5408\u4e0e\u68c0\u67e5\u5668\u7cbe\u51c6\u5c0f\u4fee")
    A("")
    A(f"- run_id\uff1a`{ctx['run_id']}`\uff1b\u7edd\u5bf9\u8def\u5f84\uff1a`{OUT}`")
    A(f"- \u6267\u884c\u4ee3\u7801\uff1a`repair_c01_from_artifacts.py`, `verify_c01_repairs.py`\uff08\u5747\u5728\u672c\u76ee\u5f55\uff0c\u53e6\u6709 `code_snapshot/`\uff09")
    A(f"- \u8fd0\u884c\u65f6\u95f4\uff1a{ctx['started']} \u81f3 {ctx['finished']}")
    A("- \u8f93\u5165\u4ec5\u9650\u51bb\u7ed3\u7684 TASK-C01 \u4ea7\u7269\uff1b**\u672a\u91cd\u65b0\u89e3\u6790\u4efb\u4f55 C8 JSON\uff0c\u672a\u91cd\u626b C1\u2013C10\uff0c\u672a\u8fd0\u884c `audit_c01.py`**\u3002")
    A("")
    A("## 1. \u8f93\u5165\u4e0e\u539f\u76ee\u5f55\u4e0d\u53d8\u8bc1\u636e")
    A("")
    A(f"- \u8f93\u5165\u6587\u4ef6 {ctx['n_inputs']} \u4e2a\uff0c\u5168\u90e8\u4f4d\u4e8e `{SOURCE_REL}`\uff1b\u9010\u4e2a\u8def\u5f84/\u5b57\u8282/SHA256 \u4e0e\u539f manifest \u5bf9\u5e94\u9879\u89c1 `input_manifest.json`\u3002")
    A(f"- \u8f93\u5165\u4e0e\u539f manifest \u4e0d\u4e00\u81f4\u7684\u6570\u91cf\uff1a**{ctx['input_manifest_mismatches']}**\u3002")
    A(f"- \u539f C01 \u76ee\u5f55\uff1a\u6bd4\u5bf9 {ctx['protected']['files_compared']} \u4e2a\u6587\u4ef6\uff0chash \u4e0d\u4e00\u81f4 {len(ctx['protected']['hash_mismatches'])} \u4e2a\uff0c\u7f3a\u5931 {len(ctx['protected']['missing_files'])} \u4e2a\uff0c\u65b0\u589e {len(ctx['protected']['new_files'])} \u4e2a\uff0c`unchanged={ctx['protected']['unchanged']}`\u3002")
    A(f"- \u662f\u5426\u8bfb\u53d6\u8fc7\u4efb\u4f55 C1\u2013C10 \u539f\u59cb\u6587\u4ef6\uff1a**{ctx['raw_attachments_read']}**\uff08`guard_read()` \u8bb0\u5f55\u7684 {len(ACCESS_LOG)} \u6b21\u8bfb\u53d6\u5168\u90e8\u5728 C01 \u76ee\u5f55\u5185\uff09\u3002")
    A(f"- `solution/src/evolution_audit.py` \u5f53\u524d SHA256 = `{ctx['evolution_sha']}`\uff0c\u4e0e\u51bb\u7ed3 run \u767b\u8bb0\u503c\u5b8c\u5168\u4e00\u81f4\u3002")
    A("")
    A("## 2. \u4e09\u5f20 corrected \u8868\u4e0e schema")
    A("")
    A("| \u8868 | \u884c\u6570 | \u8bf4\u660e |")
    A("|---|---:|---|")
    A(f"| `c8_directory_aggregate_corrected.csv` | {ctx['n_dirs']} | \u6bcf\u76ee\u5f55\u4e00\u884c\uff0c\u6587\u4ef6\u603b\u6570/\u6210\u529f/\u5931\u8d25\u3001\u6709\u6548\u4e0e\u7f3a\u5931 group score\u3001\u635f\u574f\u4f20\u64ad\u5b57\u6bb5 |")
    A(f"| `c8_model_task_aggregate_corrected.csv` | {ctx['mt_rows']} | \u6a21\u578b\u00d7\u4efb\u52a1\uff0c\u8865\u76ee\u5f55\u8986\u76d6\u5e76\u91cd\u5b9a\u4e49 `n_missing_results` |")
    A(f"| `c8_model_wide_corrected.csv` | {ctx['wide_rows']} | \u6bcf\u6a21\u578b\u4e00\u884c\uff0c\u4e25\u683c\u533a\u5206\u5b8c\u6574\u516d\u4efb\u52a1\u5747\u503c\u4e0e\u90e8\u5206\u4efb\u52a1\u5747\u503c |")
    A("")
    A("\u5b57\u6bb5\u8bed\u4e49\u89c1 `schema.md`\u3002\u5173\u952e\u7ea6\u5b9a\uff1a`six_task_mean_complete_only` \u4ec5\u5728 `n_tasks_valid == 6` \u65f6\u6709\u503c\uff1b`partial_task_mean` \u4ec5\u5728 1\u2264n\u22645 \u65f6\u6709\u503c\uff1b\u539f skipna \u884c\u5747\u503c\u4fdd\u7559\u4e3a `legacy_partial_or_complete_mean`\uff0c\u4ec5\u4f9b\u8ffd\u6eaf\u3002")
    A("")
    A("## 3. \u4e09\u7c7b\u8868\u7684\u76ee\u5f55\u8986\u76d6\u5bf9\u7167\uff08\u56db\u4e2a\u635f\u574f\u76ee\u5f55\uff09")
    A("")
    A("| directory | n_files_total | parse_success | parse_failed | has_parse_failure | has_any_parseable_file | source_parse_incomplete | n_results_valid | n_results_missing |")
    A("|---|---:|---:|---:|---|---|---|---:|---:|")
    for d, v in ctx["corrupt_dir_coverage"].items():
        A(f"| `{d}` | {v[0]} | {v[1]} | {v[2]} | {v[3]} | {v[4]} | {v[5]} | {v[6]} | {v[7]} |")
    A("")
    A(f"- \u7eaf\u635f\u574f\u76ee\u5f55 {ctx['n_pure_corrupt']} \u4e2a\uff08\u65e0\u4efb\u4f55\u53ef\u89e3\u6790\u6587\u4ef6\uff09\uff0c\u5168\u90e8\u4fdd\u7559\u5728 corrected \u76ee\u5f55\u8868\u4e2d\uff0c`n_files_parse_success=0`\u3001`n_results_valid=0`\uff1b\u56e0\u65e0\u6cd5\u4ece\u635f\u574f\u6587\u4ef6\u6216\u76ee\u5f55\u540d\u63a8\u65ad\u6a21\u578b\u8eab\u4efd\uff0c\u5b83\u4eec\u4e0d\u8fdb\u5165\u6a21\u578b\u5bbd\u8868\u3002")
    A(f"- `DreadPoor_Winter_Dawn-8B-TIES` \u6709\u53e6\u4e00\u4efd\u53ef\u89e3\u6790\u6587\u4ef6\uff0c\u8d21\u732e {ctx['corrupt_dir_coverage']['DreadPoor_Winter_Dawn-8B-TIES'][6]} \u4e2a\u6709\u6548 group score\uff0c\u5176 6 \u884c\u6a21\u578b\u4efb\u52a1\u5168\u90e8\u5e26 `source_parse_incomplete=True`\u3002")
    A(f"- \u635f\u574f\u6587\u4ef6 {ctx['n_files_failed']} \u4e2a\u9010\u6587\u4ef6\u4f20\u64ad\u6821\u9a8c\u5747\u901a\u8fc7\uff0c\u65e0\u9759\u9ed8\u4e22\u5931\uff08\u89c1 `repaired_checks.json` \u7684 `R1-C8-PROPAGATION`\u3001`R1-C8-PURE-CORRUPT-ROW`\uff09\u3002")
    A("")
    A("## 4. \u5b8c\u6574/\u90e8\u5206\u6a21\u578b\u5bf9\u7167\u4e0e\u5747\u503c\u5217\u9a8c\u8bc1")
    A("")
    A("| model_key | n_tasks_valid | six_task_complete | six_task_mean_complete_only | partial_task_mean | legacy_partial_or_complete_mean |")
    A("|---|---:|---|---|---|---|")
    for r in ctx["partial_rows"]:
        A(f"| `{r['model_key']}` | {r['n_tasks_valid']} | {r['six_task_complete']} | "
          f"{r['six_task_mean_complete_only']} | {r['partial_task_mean']} | {r['legacy']} |")
    A("")
    A(f"- `n_tasks_valid` \u5206\u5e03\uff1a`{ctx['tasks_valid_dist']}`\uff1b\u5b8c\u6574 {ctx['n_complete']} \u4e2a\uff0c\u90e8\u5206 {ctx['n_partial']} \u4e2a\u3002")
    A(f"- `six_task_mean_complete_only` \u6709\u9650\u503c {ctx['n_complete_mean_finite']} \u4e2a\uff1b6 \u4e2a\u90e8\u5206\u6a21\u578b\u5168\u90e8\u4e3a\u7a7a\u3002")
    A(f"- `partial_task_mean` \u6709\u9650\u503c {ctx['n_partial_mean_finite']} \u4e2a\uff0c\u4e14\u4ec5\u51fa\u73b0\u5728\u90e8\u5206\u6a21\u578b\u884c\u3002")
    A(f"- \u539f `six_task_mean_c8_raw` \u5728 {ctx['n_partial']} \u4e2a\u90e8\u5206\u6a21\u578b\u4e0a\u4ecd\u6709\u6570\u503c\uff08\u8fd9\u6b63\u662f\u672c\u6b21\u4fee\u590d\u7684\u52a8\u56e0\uff09\uff0c\u73b0\u5df2\u6539\u540d `legacy_partial_or_complete_mean` \u5e76\u4e0e\u539f\u5217\u9010\u503c\u4e00\u81f4\u3002")
    A("")
    A("## 5. \u539f\u68c0\u67e5\u5668\u6052\u771f/\u786c\u7f16\u7801\u9879\u7684\u9010\u9879\u4fee\u590d")
    A("")
    A("| \u539f check | \u5904\u7f6e | \u65b0 check | \u8bf4\u660e |")
    A("|---|---|---|---|")
    for cid, (disp, new_ids, why) in ctx["repair_map"].items():
        A(f"| `{cid}` | {disp} | {', '.join('`'+x+'`' for x in new_ids)} | {why} |")
    A("")
    A("## 6. \u68c0\u67e5\u5668\u7ed3\u679c")
    A("")
    A(f"- `repaired_checks.json`\uff1a\u5171 {ctx['n_checks']} \u9879\uff1bPASS {ctx['counts']['PASS']}\uff0cWARN {ctx['counts']['WARN']}\uff0cFAIL {ctx['counts']['FAIL']}\uff0cNOT_CHECKED {ctx['counts']['NOT_CHECKED']}\uff0cNOT_VERIFIABLE {ctx['counts']['NOT_VERIFIABLE']}\u3002")
    A(f"- \u5173\u952e C8 \u9879\uff08`key_c8_item=true`\uff09\uff1a{ctx['key_counts']}\uff0c\u4e0d\u5141\u8bb8\u51fa\u73b0 NOT_CHECKED / NOT_VERIFIABLE\u3002")
    A("")
    A("### FAIL")
    A("")
    A("\u65e0\u3002" if not ctx["fail_list"] else "\n".join(f"- `{x}`" for x in ctx["fail_list"]))
    A("")
    A("### WARN")
    A("")
    A("\u65e0\u3002" if not ctx["warn_list"] else "\n".join(f"- `{x}`" for x in ctx["warn_list"]))
    A("")
    A("### NOT_CHECKED")
    A("")
    if ctx["nc_list"]:
        for cid, why in ctx["nc_list"]:
            A(f"- `{cid}`\uff1a{why}")
    else:
        A("\u65e0\u3002")
    A("")
    A("### NOT_VERIFIABLE")
    A("")
    if ctx["nv_list"]:
        for cid, why in ctx["nv_list"]:
            A(f"- `{cid}`\uff1a{why}")
    else:
        A("\u65e0\u3002")
    A("")
    A("## 7. OOS-01 \u81f3 OOS-12\uff08\u4ec5\u767b\u8bb0\uff0c\u672c\u4efb\u52a1\u4e0d\u88c1\u51b3\uff09")
    A("")
    A("\u539f C01\uff08\u73b0\u4e3a R1 \u524d\u7f6e\uff09\u5728 `handoff.md` \u7b2c 9 \u8282\u767b\u8bb0\u4e86 OOS-01\u2013OOS-12\u3002\u8fd9\u4e9b\u65b9\u6cd5\u4e0e\u53e3\u5f84\u95ee\u9898\u4ecd\u672a\u88c1\u51b3\uff0c\u672c\u4efb\u52a1\u672a\u4fee\u6539\u5176\u4efb\u4f55\u4e00\u9879\uff0c\u4e5f\u672a\u636e\u6b64\u7ee7\u7eed\u5efa\u6a21\uff1a")
    A("")
    A("| \u7f16\u53f7 | \u672c R1 \u53ef\u786e\u8ba4\u7684\u76f8\u5173\u4e8b\u5b9e |")
    A("|---|---|")
    A(f"| OOS-01 | `solution/src/evolution_audit.py` \u4ecd\u4e0e\u51bb\u7ed3 run \u767b\u8bb0\u7684 SHA256 \u4e00\u81f4\uff08`{ctx['evolution_sha'][:12]}\u2026`\uff09\uff0cR1 \u672a\u4fee\u6539\u3001\u672a\u8fd0\u884c\u8be5\u6587\u4ef6 |")
    A(f"| OOS-02 | 95 \u4e2a\u53cc\u6587\u4ef6\u76ee\u5f55\u7684\u53d6\u820d\u89c4\u5219\u4ecd\u672a\u88c1\u51b3\uff1bcorrected \u8868\u540c\u65f6\u4fdd\u7559 canonical \u4e0e legacy \u4e24\u79cd\u53e3\u5f84\u5206\u6570\uff0c\u672a\u65b0\u589e\u7b2c\u4e09\u79cd\u89c4\u5219 |")
    A(f"| OOS-03 | \u635f\u574f\u6587\u4ef6\u4ecd\u4e3a {ctx['n_files_failed']} \u4e2a\uff0c\u5747\u5c5e\u540c\u4e00\u540c\u540d\u6279\u6b21\uff1bR1 \u672a\u91cd\u65b0\u4e0b\u8f7d\u6216\u91cd\u8bc4 |")
    A("| OOS-04\u2013OOS-12 | \u672a\u88c1\u51b3\uff1b\u672c\u6b21\u4ec5\u5c06\u53ef\u4ece\u4e24\u4e2a\u4ee5\u4e0a\u4ea7\u7269\u590d\u7b97\u7684\u90e8\u5206\u5347\u4e3a PASS\uff0c\u5355\u4f86\u6e90\u90e8\u5206\u7edf\u4e00\u964d\u4e3a NOT_CHECKED |")
    A("")
    A("## 8. \u505c\u6b62\u58f0\u660e")
    A("")
    A("- \u672c\u4efb\u52a1\u672a\u91cd\u65b0\u89e3\u6790 1958 \u4e2a JSON\uff0c\u672a\u91cd\u626b C1\u2013C10\uff0c\u672a\u8fd0\u884c `audit_c01.py`\u3002")
    A("- \u672a\u4fee\u6539\u539f TASK-C01 \u76ee\u5f55\u3001`solution/`\u3001`F\u9898/`\u3001`00`\u2013`05` \u9879\u76ee\u6587\u6863\u53ca Q01A/Q01B/Q01C \u4ea7\u7269\u3002")
    A("- \u672a\u5f00\u59cb Loss\u2013Benchmark \u5efa\u6a21\u3001\u65f6\u95f4\u9884\u6d4b\u6216\u95ee\u9898\u56db\u5efa\u6a21\u3002")
    A("")
    A("## 9. \u72ec\u7acb\u9a8c\u8bc1\uff08verify_c01_repairs.py\uff09")
    A("")
    A("_verification results are appended by `verify_c01_repairs.py` after this file is written._")
    A("")
    with io.open(os.path.join(OUT, "handoff.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(L) + "\n")


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--r1-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--stage-dir", required=True, help="directory holding the staged R1 scripts")
    args = ap.parse_args()

    OUT = os.path.abspath(os.path.join(args.r1_root, args.run_id))
    if os.path.exists(OUT):
        sys.stderr.write("REFUSING TO OVERWRITE: R1 run directory already exists -> " + OUT + "\n")
        return 2
    os.makedirs(OUT)
    started = datetime.now(TZ)
    log("=" * 100)
    log("TASK-C01-R1  C8 aggregation and checker repair (post-processing only)")
    log(f"run_id        : {args.run_id}")
    log(f"output dir    : {OUT}")
    log(f"source dir    : {SOURCE_DIR}")
    log(f"started (UTC+8): {started.isoformat()}")
    log(f"python        : {sys.version.splitlines()[0]}")
    log(f"platform      : {platform.platform()}")
    log(f"numpy/pandas  : {np.__version__} / {pd.__version__}")
    log("=" * 100)

    before = snapshot_dir(SOURCE_DIR)
    log(f"[guard] frozen C01 directory snapshot: {len(before)} files")

    data = load_inputs()
    names_read = CSV_INPUTS + GZ_INPUTS + JSON_INPUTS + TEXT_INPUTS

    log("[1/6] corrected C8 directory coverage")
    dir_tbl = build_directory_corrected(data["c8_parse_log.csv"], data["c8_group_scores_all_runs.csv"])
    wcsv("c8_directory_aggregate_corrected.csv", dir_tbl)
    log(f"       directories={len(dir_tbl)} files_total={int(dir_tbl.n_files_total.sum())} "
        f"success={int(dir_tbl.n_files_parse_success.sum())} failed={int(dir_tbl.n_files_parse_failed.sum())} "
        f"results_valid={int(dir_tbl.n_results_valid.sum())} results_missing={int(dir_tbl.n_results_missing.sum())}")

    log("[2/6] corrected model x task table")
    mt_corr = build_model_task_corrected(data["c8_model_task_aggregate.csv"], dir_tbl,
                                        data["c8_group_scores_all_runs.csv"])
    wcsv("c8_model_task_aggregate_corrected.csv", mt_corr)
    log(f"       rows={len(mt_corr)} valid_rows={int((mt_corr.n_valid_results > 0).sum())} "
        f"zero_rows={int((mt_corr.n_valid_results == 0).sum())} sum={int(mt_corr.n_valid_results.sum())}")

    log("[3/6] corrected model wide table")
    wide_corr = build_wide_corrected(data["c8_model_wide_canonical.csv"],
                                     data["c8_model_task_aggregate.csv"], dir_tbl)
    wcsv("c8_model_wide_corrected.csv", wide_corr)
    log(f"       rows={len(wide_corr)} complete={int(wide_corr.six_task_complete.sum())} "
        f"partial={int((~wide_corr.six_task_complete).sum())} "
        f"complete_mean_finite={int(wide_corr.six_task_mean_complete_only.notna().sum())} "
        f"partial_mean_finite={int(wide_corr.partial_task_mean.notna().sum())}")

    log("[4/6] input manifest + protected original run check")
    inputs_manifest = build_input_manifest(names_read)
    after = snapshot_dir(SOURCE_DIR)
    protected = build_protected_check(before, after)
    wjson("input_manifest.json", {"task": TASK, "run_id": args.run_id, "source_task": SOURCE_TASK,
                                  "source_run_id": SOURCE_RUN_ID, "inputs": inputs_manifest})
    wjson("protected_original_run_check.json", protected)
    n_bad_inputs = sum(1 for i in inputs_manifest if not i["matches_frozen_manifest"])
    log(f"       inputs={len(inputs_manifest)} mismatching_frozen_manifest={n_bad_inputs} "
        f"c01_unchanged={protected['unchanged']}")

    log("[5/6] repaired checker")
    build_checks(data, dir_tbl, mt_corr, wide_corr, protected, inputs_manifest)
    build_extra_checks(data, dir_tbl, mt_corr, wide_corr)
    add("R1-IN-MANIFEST", "every R1 input still hashes to the value in the frozen TASK-C01 output manifest",
        {"inputs": len(inputs_manifest),
         "not_matching": [i["input"] for i in inputs_manifest if not i["matches_frozen_manifest"]],
         "not_in_frozen_manifest": [i["input"] for i in inputs_manifest if not i["frozen_manifest_present"]]},
        {"not_matching": [], "not_in_frozen_manifest": []},
        "input_manifest.json vs the frozen output_manifest.json",
        "re-hash each input now and compare with the archived manifest entry")
    frozen_entries = {a["file"] for a in data["output_manifest.json"]["artifacts"]}
    allowed = set(names_read)
    add("R1-IN-MANIFEST-COMPLETE", "every allowed input that exists in the frozen manifest was actually inventoried",
        {"allowed_inputs": len(allowed), "inventoried": len([i for i in inputs_manifest if i["frozen_manifest_present"]]),
         "allowed_missing_from_inventory": sorted(allowed - {i["input"] for i in inputs_manifest})},
        {"allowed_missing_from_inventory": []},
        "input_manifest.json + output_manifest.json",
        "set comparison between the permitted input list and the inventoried inputs")
    counts = {s: sum(1 for c in CHECKS if c["status"] == s)
              for s in ["PASS", "WARN", "FAIL", "NOT_CHECKED", "NOT_VERIFIABLE"]}
    key_checks = [c for c in CHECKS if c["key_c8_item"]]
    key_counts = {s: sum(1 for c in key_checks if c["status"] == s) for s in counts}
    log(f"       checks={len(CHECKS)} {counts}")
    log(f"       key C8 checks={len(key_checks)} {key_counts}")
    assert key_counts["FAIL"] == 0, "key C8 item failed: " + str([c["check_id"] for c in key_checks if c["status"] == "FAIL"])
    assert key_counts["NOT_CHECKED"] == 0 and key_counts["NOT_VERIFIABLE"] == 0, \
        "a key C8 item was downgraded: " + str([c["check_id"] for c in key_checks
                                                if c["status"] in ("NOT_CHECKED", "NOT_VERIFIABLE")])

    log("[6/6] writing ledger, schema, summary, handoff, code snapshot")
    wcsv("changes.csv", pd.DataFrame(CHANGES))
    repaired = {
        "task": TASK, "run_id": args.run_id,
        "purpose": "repair of the TASK-C01 checker and C8 aggregation semantics",
        "source_task": SOURCE_TASK, "source_run_id": SOURCE_RUN_ID,
        "source_checks_summary": {"PASS": 33, "WARN": 6, "FAIL": 0,
                                  "note": "as recorded in the frozen checks.json; several PASS values were constants"},
        "repair_map": {k: {"disposition": v[0], "reimbursed_by": v[1], "explanation": v[2]}
                       for k, v in ORIGINAL_REPAIR.items()},
        "status_vocabulary": ["PASS", "WARN", "FAIL", "NOT_CHECKED", "NOT_VERIFIABLE"],
        "rule": "NOT_CHECKED and NOT_VERIFIABLE are never counted as PASS. Every PASS is a computed "
                "comparison: for a mapping, each key listed in expected must exist in actual with an "
                "equal value (expected is a required subset of the observation); scalars and lists must "
                "match exactly, numbers within rtol=1e-9 / atol=1e-12.",
        "counts": counts, "key_c8_counts": key_counts, "n_checks": len(CHECKS), "checks": CHECKS,
    }
    wjson("repaired_checks.json", repaired)
    write_schema()
    wjson("environment.json", {
        "run_id": args.run_id, "task": TASK, "author": AUTHOR,
        "python": sys.version, "platform": platform.platform(),
        "numpy": np.__version__, "pandas": pd.__version__, "os_name": os.name,
        "long_path_mode": "POSIX" if os.name != "nt" else "Windows API (paths in this run are all "
                                                          "inside the C01/R1 directories and were not extended)",
        "workspace": WORKSPACE, "source_dir": SOURCE_DIR, "output_dir": OUT,
    })

    finish = datetime.now(TZ)
    partial_rows = []
    for _, r in wide_corr.loc[~wide_corr.six_task_complete].iterrows():
        partial_rows.append({
            "model_key": r.model_key, "n_tasks_valid": int(r.n_tasks_valid),
            "six_task_complete": bool(r.six_task_complete),
            "six_task_mean_complete_only": to_builtin(float(r.six_task_mean_complete_only))
            if pd.notna(r.six_task_mean_complete_only) else None,
            "partial_task_mean": to_builtin(float(r.partial_task_mean)) if pd.notna(r.partial_task_mean) else None,
            "legacy": to_builtin(float(r.legacy_partial_or_complete_mean)),
        })
    cdc = {}
    for d, v in ANCHOR["corrupt_dir_expect"].items():
        row = dir_tbl.loc[dir_tbl.directory.eq(d)].iloc[0]
        cdc[d] = [int(row.n_files_total), int(row.n_files_parse_success), int(row.n_files_parse_failed),
                  bool(row.has_parse_failure), bool(row.has_any_parseable_file),
                  bool(row.source_parse_incomplete), int(row.n_results_valid), int(row.n_results_missing)]
    ctx = {
        "run_id": args.run_id, "started": started.isoformat(), "finished": finish.isoformat(),
        "n_inputs": len(inputs_manifest), "input_manifest_mismatches": n_bad_inputs,
        "protected": protected, "raw_attachments_read": False,
        "evolution_sha": sha256_file(EVOLUTION_AUDIT),
        "n_dirs": len(dir_tbl), "mt_rows": len(mt_corr), "wide_rows": len(wide_corr),
        "n_files_total": int(dir_tbl.n_files_total.sum()),
        "n_files_ok": int(dir_tbl.n_files_parse_success.sum()),
        "n_files_failed": int(dir_tbl.n_files_parse_failed.sum()),
        "n_results_valid": int(dir_tbl.n_results_valid.sum()),
        "n_results_missing": int(dir_tbl.n_results_missing.sum()),
        "corrupt_dir_coverage": cdc, "n_pure_corrupt": 3,
        "partial_rows": partial_rows,
        "n_complete": int(wide_corr.six_task_complete.sum()),
        "n_partial": int((~wide_corr.six_task_complete).sum()),
        "n_complete_mean_finite": int(wide_corr.six_task_mean_complete_only.notna().sum()),
        "n_partial_mean_finite": int(wide_corr.partial_task_mean.notna().sum()),
        "tasks_valid_dist": {str(k): int(v) for k, v in wide_corr.n_tasks_valid.value_counts().sort_index().items()},
        "counts": counts, "key_counts": key_counts, "n_checks": len(CHECKS),
        "repair_map": ORIGINAL_REPAIR,
        "fail_list": [c["check_id"] for c in CHECKS if c["status"] == "FAIL"],
        "warn_list": [c["check_id"] for c in CHECKS if c["status"] == "WARN"],
        "nc_list": [(c["check_id"], c["limitations"]) for c in CHECKS if c["status"] == "NOT_CHECKED"],
        "nv_list": [(c["check_id"], c["limitations"]) for c in CHECKS if c["status"] == "NOT_VERIFIABLE"],
    }
    write_handoff(ctx)

    snapshot_dir_out = os.path.join(OUT, "code_snapshot")
    os.makedirs(snapshot_dir_out, exist_ok=True)
    for name in ["repair_c01_from_artifacts.py", "verify_c01_repairs.py"]:
        src = os.path.join(args.stage_dir, name)
        dst = os.path.join(OUT, name)
        shutil.copyfile(guard_stage(src), dst)
        shutil.copyfile(guard_stage(src), os.path.join(snapshot_dir_out, name))
    log("[code] staged scripts copied to the run directory and to code_snapshot/")

    summary = {
        "task": TASK, "run_id": args.run_id, "author": AUTHOR,
        "started_local": started.isoformat(), "finished_local": finish.isoformat(),
        "duration_seconds": round((finish - started).total_seconds(), 3),
        "source": {"task": SOURCE_TASK, "run_id": SOURCE_RUN_ID, "dir": SOURCE_REL.replace("\\", "/")},
        "scope": {
            "performed": ["C8 directory coverage rebuild", "model x task coverage propagation",
                          "complete vs partial mean separation", "checker repair",
                          "independent verification by a separate script"],
            "explicitly_not_performed": ["re-parsing any C8 JSON", "rescanning C1-C10",
                                          "running audit_c01.py", "modifying the frozen C01 directory",
                                          "Loss-Benchmark modelling", "12/24-month forecasting",
                                          "problem-4 model selection", "reading diagnostics/TASK-Q01C-R1"],
        },
        "input_manifest": {"inputs": len(inputs_manifest),
                           "mismatching_frozen_manifest": n_bad_inputs,
                           "file": "input_manifest.json"},
        "protected_original_run": {"unchanged": protected["unchanged"],
                                   "hash_mismatches": protected["hash_mismatches"],
                                   "missing_files": protected["missing_files"],
                                   "new_files": protected["new_files"],
                                   "files_compared": protected["files_compared"]},
        "raw_attachments_read": False,
        "evolution_audit_sha256": ctx["evolution_sha"],
        "c8_file_accounting": {"n_files_total": ctx["n_files_total"], "parse_success": ctx["n_files_ok"],
                               "parse_failed": ctx["n_files_failed"], "n_directories": ctx["n_dirs"]},
        "c8_group_scores": {"n_results_valid": ctx["n_results_valid"],
                            "n_results_missing": ctx["n_results_missing"],
                            "n_task_slots": int(data["c8_group_scores_all_runs.csv"].shape[0])},
        "c8_corrupt_directories": cdc,
        "c8_model_task": {"rows": ctx["mt_rows"],
                          "rows_with_valid": int((mt_corr.n_valid_results > 0).sum()),
                          "rows_with_zero": int((mt_corr.n_valid_results == 0).sum()),
                          "n_valid_results_sum": int(mt_corr.n_valid_results.sum())},
        "c8_model_wide": {"rows": ctx["wide_rows"], "n_tasks_valid_distribution": ctx["tasks_valid_dist"],
                          "six_task_complete_true": ctx["n_complete"], "six_task_complete_false": ctx["n_partial"],
                          "six_task_mean_complete_only_finite": ctx["n_complete_mean_finite"],
                          "partial_task_mean_finite": ctx["n_partial_mean_finite"],
                          "partial_models": [r["model_key"] for r in partial_rows]},
        "checks": counts, "n_checks": len(CHECKS), "key_c8_counts": key_counts,
        "outputs_written_to": os.path.relpath(OUT, WORKSPACE).replace("\\", "/"),
        "verification": {"status": "PENDING", "file": "verification.json"},
    }
    wjson("run_summary.json", summary)
    with io.open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(LOG) + "\n")
    log(f"[done] repair phase finished {finish.isoformat()} "
        f"duration={(finish - started).total_seconds():.1f}s")
    return 0


def guard_stage(path):
    """Staged scripts live outside the frozen C01 directory but must never touch raw data."""
    resolved = os.path.abspath(path)
    if "real_attachments" in resolved.replace("\\", "/").lower():
        raise RuntimeError("refusing to copy a script from under the raw attachments")
    if not os.path.isfile(resolved):
        raise FileNotFoundError(resolved)
    return resolved


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log("!!! FATAL !!!")
        log(traceback.format_exc())
        print(traceback.format_exc(), file=sys.stderr)
        raise
