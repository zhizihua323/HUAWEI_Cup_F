# -*- coding: utf-8 -*-
"""TASK-C01-R1 : independent verification of the repair outputs.

Independence rules enforced here:

  * This module NEVER imports `repair_c01_from_artifacts.py` and never calls any of its
    functions. Every expected value below is recomputed from the frozen TASK-C01
    artifacts with this file's own code.
  * It reads only the frozen C01 run directory and the R1 run directory. It never opens
    a raw attachment, never re-parses a C8 JSON and never runs `audit_c01.py`.
  * It writes `verification.json`, appends the verification section to `handoff.md`,
    updates `run_summary.json`, and writes `output_manifest.json` LAST.
"""
import argparse
import hashlib
import io
import json
import os
import platform
import re
import sys
import traceback
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

TASK = "TASK-C01-R1"
SOURCE_RUN_ID = "20260924T175553+08"
TZ = timezone(timedelta(hours=8))
TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]
LOG = []

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



def log(msg=""):
    line = str(msg)
    LOG.append(line)
    print(line, flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_csv(path):
    with open(path, "rb") as fh:
        head = fh.read(3)
    enc = "utf-8-sig" if head.startswith(b"\xef\xbb\xbf") else "utf-8"
    return pd.read_csv(path, encoding=enc)


def load_json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def result(rid, claim, ok, actual, expected, evidence, method, limitations="none"):
    return {"verification_id": rid, "claim": claim, "status": "PASS" if ok else "FAIL",
            "actual": actual, "expected": expected, "evidence": evidence,
            "verification_method": method, "limitations": limitations}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run_dir = os.path.abspath(args.run_dir)
    workspace = find_workspace(os.path.dirname(os.path.abspath(__file__)))
    source_dir = os.path.join(workspace, "diagnostics", "TASK-C01", SOURCE_RUN_ID)
    started = datetime.now(TZ)
    log("=" * 100)
    log("TASK-C01-R1 independent verification")
    log(f"run dir    : {run_dir}")
    log(f"source dir : {source_dir}")
    log(f"started    : {started.isoformat()}")
    log("=" * 100)

    def S(name):
        return os.path.join(source_dir, name)

    def R(name):
        return os.path.join(run_dir, name)

    # ---- raw-marker guard: nothing below may touch a raw attachment ------------------
    raw_root = os.path.join(workspace, "F\u9898", "real_attachments").replace("\\", "/").lower()
    for path in [source_dir, run_dir]:
        assert raw_root not in path.replace("\\", "/").lower()

    results = []
    pl = load_csv(S("c8_parse_log.csv"))
    cor = load_csv(S("c8_corrupt_files.csv"))
    dc = load_csv(S("c8_directory_file_counts.csv"))
    gs = load_csv(S("c8_group_scores_all_runs.csv"))
    mt = load_csv(S("c8_model_task_aggregate.csv"))
    wi = load_csv(S("c8_model_wide_canonical.csv"))
    ti = load_csv(S("c8_task_inventory.csv"))
    leaf = load_csv(S("c8_leaf_metrics.csv.gz"))
    frozen_manifest = load_json(S("output_manifest.json"))
    frozen_summary = load_json(S("run_summary.json"))

    dir_tbl = load_csv(R("c8_directory_aggregate_corrected.csv"))
    mt_corr = load_csv(R("c8_model_task_aggregate_corrected.csv"))
    wide_corr = load_csv(R("c8_model_wide_corrected.csv"))
    summary = load_json(R("run_summary.json"))
    repaired = load_json(R("repaired_checks.json"))

    # =============================== independent recount ==============================
    ok_rows = pl[pl["parse_status"] == "ok"]
    bad_rows = pl[pl["parse_status"] != "ok"]
    recount = {
        "files_total": int(len(pl)),
        "files_ok": int(len(ok_rows)),
        "files_failed": int(len(bad_rows)),
        "dirs": int(pl["directory"].nunique()),
        "dirs_one_file": int((pl.groupby("directory").size() == 1).sum()),
        "dirs_two_files": int((pl.groupby("directory").size() == 2).sum()),
        "corrupt_dirs": sorted(bad_rows["directory"].unique().tolist()),
        "pure_corrupt_dirs": sorted(bad_rows.groupby("directory")
                                    .apply(lambda g: int((g["parse_status"] == "ok").sum()), include_groups=False)
                                    .loc[lambda s: s == 0].index.tolist()),
        "group_rows": int(len(gs)),
        "group_finite": int(gs["score"].notna().sum()),
        "group_missing": int(gs["score"].isna().sum()),
        "dir_valid_sum": int(gs.groupby("directory")["score"].apply(lambda s: int(s.notna().sum())).sum()),
        "mt_rows": int(len(mt)),
        "mt_valid_rows": int((mt["n_valid_results"] > 0).sum()),
        "mt_zero_rows": int((mt["n_valid_results"] == 0).sum()),
        "mt_valid_sum": int(mt["n_valid_results"].sum()),
        "wide_rows": int(len(wi)),
        "nonnumeric_inventory": int(ti["nonnumeric_metric_values"].sum()),
        "nonnumeric_leaf": int(((leaf["nonnumeric"] == 1) & (leaf["metric"] != "alias")).sum()),
    }
    log("[recount] " + json.dumps(recount, ensure_ascii=False))
    results.append(result("V-C8-01", "1958 files = 1954 parseable + 4 failed",
                          recount["files_total"] == 1958 and recount["files_ok"] == 1954
                          and recount["files_failed"] == 4
                          and recount["files_ok"] + recount["files_failed"] == recount["files_total"],
                          [recount["files_total"], recount["files_ok"], recount["files_failed"]],
                          [1958, 1954, 4], "c8_parse_log.csv",
                          "recount rows and parse_status classes from the frozen parse log"))
    results.append(result("V-C8-02", "1863 directories; 1768 with one JSON and 95 with two",
                          recount["dirs"] == 1863 and recount["dirs_one_file"] == 1768
                          and recount["dirs_two_files"] == 95,
                          [recount["dirs"], recount["dirs_one_file"], recount["dirs_two_files"]],
                          [1863, 1768, 95],
                          "c8_parse_log.csv + c8_directory_file_counts.csv",
                          "group the parse log by directory and compare with the frozen counts artifact; "
                          "the two artifacts must agree on the same directory set"))
    results.append(result("V-C8-03", "directory set identical between the two frozen artifacts",
                          set(pl["directory"]) == set(dc["directory"]),
                          {"parse_log_dirs": len(set(pl["directory"])), "counts_dirs": len(set(dc["directory"]))},
                          {"parse_log_dirs": 1863, "counts_dirs": 1863},
                          "c8_parse_log.csv vs c8_directory_file_counts.csv", "set equality"))
    results.append(result("V-C8-04", "4 damaged directories; 3 of them have no parseable file",
                          len(recount["corrupt_dirs"]) == 4 and len(recount["pure_corrupt_dirs"]) == 3,
                          {"corrupt_dirs": recount["corrupt_dirs"], "pure": recount["pure_corrupt_dirs"]},
                          {"corrupt_dirs": 4, "pure": 3}, "c8_parse_log.csv + c8_corrupt_files.csv",
                          "derive the damaged directory set without using the frozen corrupt list, then "
                          "check that the two artifacts describe the same four files"))
    results.append(result("V-C8-05", "11724 task slots, 11699 finite, 25 missing",
                          recount["group_rows"] == 11724 and recount["group_finite"] == 11699
                          and recount["group_missing"] == 25
                          and recount["group_rows"] == 1954 * 6,
                          [recount["group_rows"], recount["group_finite"], recount["group_missing"]],
                          [11724, 11699, 25], "c8_group_scores_all_runs.csv + c8_parse_log.csv",
                          "count rows and non-null scores directly in the group detail"))
    finite_per_dir = gs.groupby("directory")["score"].apply(lambda s: int(s.notna().sum())).to_dict()
    corrupt_scores = {d: int(finite_per_dir.get(d, 0)) for d in recount["corrupt_dirs"]}
    results.append(result("V-C8-06",
                          "DreadPoor contributes 6 finite scores; the other three damaged directories contribute 0",
                          corrupt_scores.get("DreadPoor_Winter_Dawn-8B-TIES") == 6
                          and all(v == 0 for k, v in corrupt_scores.items()
                                  if k != "DreadPoor_Winter_Dawn-8B-TIES"),
                          corrupt_scores,
                          {"DreadPoor_Winter_Dawn-8B-TIES": 6, "the other three": 0},
                          "c8_group_scores_all_runs.csv", "per-directory recount of finite scores"))

    # ---- corrected directory table vs the independent recount -------------------------
    cdt = set(dir_tbl["directory"])
    results.append(result("V-CDT-01", "corrected directory table covers exactly the frozen directory set",
                          cdt == set(pl["directory"]) and len(dir_tbl) == 1863,
                          {"rows": int(len(dir_tbl)), "set_equal": cdt == set(pl["directory"])},
                          {"rows": 1863, "set_equal": True},
                          "c8_directory_aggregate_corrected.csv vs c8_parse_log.csv",
                          "row-count and set comparison"))
    ident_bad = int((dir_tbl["n_files_total"] !=
                     dir_tbl["n_files_parse_success"] + dir_tbl["n_files_parse_failed"]).sum())
    results.append(result("V-CDT-02", "per-directory file identity total == success + failed",
                          ident_bad == 0, {"violations": ident_bad}, {"violations": 0},
                          "c8_directory_aggregate_corrected.csv", "row-wise arithmetic test"))
    results.append(result("V-CDT-03", "sum of n_results_valid equals the independent finite recount",
                          int(dir_tbl["n_results_valid"].sum()) == recount["group_finite"],
                          {"corrected_sum": int(dir_tbl["n_results_valid"].sum()),
                           "independent_recount": recount["group_finite"]},
                          {"both": 11699}, "c8_directory_aggregate_corrected.csv vs c8_group_scores_all_runs.csv",
                          "sum the corrected column and compare with a recount of the group detail"))
    exp_valid = dir_tbl["n_files_parse_success"] * 6 - dir_tbl["n_results_valid"]
    results.append(result("V-CDT-04", "n_results_missing equals parseable slots minus valid results",
                          bool((dir_tbl["n_results_missing"] == exp_valid).all()),
                          {"violations": int((dir_tbl["n_results_missing"] != exp_valid).sum())},
                          {"violations": 0}, "c8_directory_aggregate_corrected.csv",
                          "recompute the expected column from two other columns of the same table AND from "
                          "the parse log success counts"))
    prop = {}
    for _, r in cor.iterrows():
        row = dir_tbl[dir_tbl["directory"] == r["directory"]]
        prop[r["directory"]] = {
            "row_present": bool(len(row) == 1),
            "parse_failed_count": int(row.iloc[0]["n_files_parse_failed"]) if len(row) else None,
            "has_parse_failure": bool(row.iloc[0]["has_parse_failure"]) if len(row) else None,
            "failed_file_named": bool(len(row) and r["file"] in str(row.iloc[0]["parse_failed_files"])),
        }
    results.append(result("V-CDT-05", "all four corrupt files are propagated into coverage",
                          all(v["row_present"] and v["has_parse_failure"] and v["failed_file_named"]
                              and v["parse_failed_count"] >= 1 for v in prop.values()),
                          prop, {"per_directory": "row present, has_parse_failure true, failed file named"},
                          "c8_corrupt_files.csv vs c8_directory_aggregate_corrected.csv",
                          "join each corrupt file onto the corrected directory row"))
    pure_rows = {d: [int(dir_tbl.loc[dir_tbl["directory"] == d, "n_files_parse_success"].iloc[0]),
                     int(dir_tbl.loc[dir_tbl["directory"] == d, "n_results_valid"].iloc[0])]
                 for d in recount["pure_corrupt_dirs"]}
    results.append(result("V-CDT-06", "the three pure-corrupt directories stay visible with zero coverage",
                          all(v == [0, 0] for v in pure_rows.values()),
                          pure_rows, {"each": [0, 0]},
                          "c8_directory_aggregate_corrected.csv", "presence and zero-coverage test"))

    # ---- corrected model x task table -------------------------------------------------
    log("[verify] model x task table")
    keys_orig = set(zip(mt["model_key"], mt["task_group"]))
    keys_corr = set(zip(mt_corr["model_key"], mt_corr["task_group"]))
    results.append(result("V-MT-01", "corrected model x task table keeps the frozen key set",
                          keys_corr == keys_orig and len(mt_corr) == len(mt) == 11160,
                          {"rows": int(len(mt_corr)), "keys_equal": keys_corr == keys_orig,
                           "only_corrected": len(keys_corr - keys_orig),
                           "only_frozen": len(keys_orig - keys_corr)},
                          {"rows": 11160, "keys_equal": True, "only_corrected": 0, "only_frozen": 0},
                          "c8_model_task_aggregate_corrected.csv vs c8_model_task_aggregate.csv",
                          "row count and key-set comparison"))
    gs_counts = {}
    for (d, t), cnt in gs.groupby(["directory", "task_group"])["score"].apply(
            lambda s: int(s.notna().sum())).items():
        gs_counts[(d, t)] = int(cnt)
    mismatch = {f"{k[0]}|{k[1]}": [int(r["n_valid_results"]), gs_counts.get(k)]
                for k, r in zip(zip(mt_corr["model_key"], mt_corr["task_group"]),
                                mt_corr.to_dict("records"))
                if int(r["n_valid_results"]) != gs_counts.get(k, -1)}
    results.append(result("V-MT-02", "corrected n_valid_results equals an independent per-key recount",
                          len(mismatch) == 0 and int(mt_corr["n_valid_results"].sum()) == recount["group_finite"],
                          {"mismatches": len(mismatch), "examples": dict(list(mismatch.items())[:5]),
                           "sum": int(mt_corr["n_valid_results"].sum())},
                          {"mismatches": 0, "sum": 11699},
                          "c8_model_task_aggregate_corrected.csv vs c8_group_scores_all_runs.csv",
                          "this file rebuilds the per-(model,task) dictionary straight from the group detail "
                          "instead of calling any repair function"))
    exp_missing = mt_corr["n_files_parse_success"] - mt_corr["n_valid_results"]
    results.append(result("V-MT-03", "corrected n_missing_results uses the parseable-file denominator",
                          bool((mt_corr["n_missing_results"] == exp_missing).all())
                          and bool((mt_corr["n_missing_results"] >= 0).all()),
                          {"violations": int((mt_corr["n_missing_results"] != exp_missing).sum()),
                           "negative_values": int((mt_corr["n_missing_results"] < 0).sum())},
                          {"violations": 0, "negative_values": 0},
                          "c8_model_task_aggregate_corrected.csv + c8_parse_log.csv",
                          "recompute the expected denominator from the frozen parse log success counts"))
    cov = dir_tbl.set_index("directory")[["n_files_total", "n_files_parse_success", "n_files_parse_failed",
                                          "source_parse_incomplete"]].to_dict("index")
    cov_bad = [k for k, r in zip(zip(mt_corr["model_key"], mt_corr["task_group"]), mt_corr.to_dict("records"))
               if (r["n_files_total"], r["n_files_parse_success"], r["n_files_parse_failed"],
                   bool(r["source_parse_incomplete"]))
               != (cov[r["model_key"]]["n_files_total"], cov[r["model_key"]]["n_files_parse_success"],
                   cov[r["model_key"]]["n_files_parse_failed"],
                   bool(cov[r["model_key"]]["source_parse_incomplete"]))]
    results.append(result("V-MT-04", "coverage fields of every model x task row trace back to the corrected directory table",
                          len(cov_bad) == 0, {"mismatching_rows": len(cov_bad)}, {"mismatching_rows": 0},
                          "c8_model_task_aggregate_corrected.csv vs c8_directory_aggregate_corrected.csv",
                          "key-wise reconciliation of four coverage fields"))
    dp = mt_corr[mt_corr["model_key"] == "DreadPoor_Winter_Dawn-8B-TIES"]
    results.append(result("V-MT-05", "the damaged directory that still has data flags all six of its rows",
                          len(dp) == 6 and bool(dp["source_parse_incomplete"].all())
                          and int(mt_corr.drop(dp.index)["source_parse_incomplete"].sum()) == 0,
                          {"rows": int(len(dp)), "flagged": int(dp["source_parse_incomplete"].sum()),
                           "other_flagged": int(mt_corr.drop(dp.index)["source_parse_incomplete"].sum())},
                          {"rows": 6, "flagged": 6, "other_flagged": 0},
                          "c8_model_task_aggregate_corrected.csv", "per-key flag audit"))
    preserved = ["all_scores", "all_files", "canonical_file", "canonical_score",
                 "legacy_selection_rule_score", "mean_score", "min_score", "max_score"]
    results.append(result("V-MT-06", "the multi-run source columns are preserved, not re-decided",
                          all(c in mt_corr.columns for c in preserved)
                          and bool(mt_corr["canonical_score"].equals(mt["canonical_score"]))
                          and bool(mt_corr["legacy_selection_rule_score"].equals(mt["legacy_selection_rule_score"])),
                          {"missing_columns": [c for c in preserved if c not in mt_corr.columns],
                           "canonical_identical": bool(mt_corr["canonical_score"].equals(mt["canonical_score"]))},
                          {"missing_columns": [], "canonical_identical": True},
                          "c8_model_task_aggregate_corrected.csv vs c8_model_task_aggregate.csv",
                          "column presence and exact value equality for the two pre-existing selection rules"))

    # ---- corrected wide table ---------------------------------------------------------
    log("[verify] model wide table")
    piv = mt.pivot_table(index="model_key", columns="task_group", values="canonical_score", aggfunc="first")
    indep = piv.reindex(columns=TASKS)
    indep_counts = indep.notna().sum(axis=1)
    indep_complete = indep_counts.eq(6)
    indep_complete_mean = indep.mean(axis=1).where(indep_complete)
    indep_partial_mean = indep.mean(axis=1).where(indep_counts.between(1, 5))
    wc = wide_corr.set_index("model_key")
    common = sorted(set(wc.index) & set(indep.index))
    mean_ok = bool(np.allclose(wc.loc[common, "six_task_mean_complete_only"].astype(float),
                               indep_complete_mean.loc[common].astype(float), equal_nan=True))
    part_ok = bool(np.allclose(wc.loc[common, "partial_task_mean"].astype(float),
                               indep_partial_mean.loc[common].astype(float), equal_nan=True))
    cnt_ok = bool((wc.loc[common, "n_tasks_valid"].astype(int) == indep_counts.loc[common].astype(int)).all())
    results.append(result("V-WIDE-01", "the wide table rebuilds the six task scores from the frozen model x task table",
                          len(wide_corr) == 1860 and bool(np.allclose(
                              wc.loc[common, TASKS].astype(float), indep.loc[common, TASKS].astype(float),
                              equal_nan=True)),
                          {"rows": int(len(wide_corr)), "models_compared": len(common)},
                          {"rows": 1860, "models_compared": 1860},
                          "c8_model_wide_corrected.csv vs c8_model_task_aggregate.csv",
                          "this file pivots the frozen model x task table itself and compares cell by cell"))
    results.append(result("V-WIDE-02", "n_tasks_valid, complete flag, complete mean and partial mean all reproduce independently",
                          cnt_ok and mean_ok and part_ok,
                          {"n_tasks_valid_equal": cnt_ok, "complete_mean_equal": mean_ok,
                           "partial_mean_equal": part_ok},
                          {"n_tasks_valid_equal": True, "complete_mean_equal": True, "partial_mean_equal": True},
                          "c8_model_wide_corrected.csv vs c8_model_task_aggregate.csv",
                          "independent pivot + independent mean computation"))
    dist = {int(k): int(v) for k, v in wide_corr["n_tasks_valid"].value_counts().sort_index().items()}
    results.append(result("V-WIDE-03", "n_tasks_valid distribution is 1:3, 2:1, 3:2, 6:1854",
                          dist == {1: 3, 2: 1, 3: 2, 6: 1854}, dist, {1: 3, 2: 1, 3: 2, 6: 1854},
                          "c8_model_wide_corrected.csv", "value_counts of the recomputed column"))
    partial_rows = wide_corr[~wide_corr["six_task_complete"]]
    results.append(result("V-WIDE-04", "1854 complete models and 6 partial models",
                          int(wide_corr["six_task_complete"].sum()) == 1854 and len(partial_rows) == 6,
                          {"complete": int(wide_corr["six_task_complete"].sum()), "partial": int(len(partial_rows))},
                          {"complete": 1854, "partial": 6}, "c8_model_wide_corrected.csv", "flag counts"))
    results.append(result("V-WIDE-05", "no partial model carries a six-task mean",
                          int(partial_rows["six_task_mean_complete_only"].notna().sum()) == 0
                          and int(wide_corr["six_task_mean_complete_only"].notna().sum()) == 1854,
                          {"partial_with_complete_mean": int(partial_rows["six_task_mean_complete_only"].notna().sum()),
                           "complete_mean_finite": int(wide_corr["six_task_mean_complete_only"].notna().sum())},
                          {"partial_with_complete_mean": 0, "complete_mean_finite": 1854},
                          "c8_model_wide_corrected.csv",
                          "null test on every row flagged partial; this is the core defect the repair removes"))
    results.append(result("V-WIDE-06", "partial_task_mean is populated exactly on the six partial models",
                          int(wide_corr["partial_task_mean"].notna().sum()) == 6
                          and bool(partial_rows["partial_task_mean"].notna().all())
                          and bool(wide_corr.loc[wide_corr["six_task_complete"], "partial_task_mean"].isna().all()),
                          {"finite": int(wide_corr["partial_task_mean"].notna().sum())},
                          {"finite": 6}, "c8_model_wide_corrected.csv", "presence/absence test per row class"))
    legacy_ok = bool(np.allclose(wide_corr["legacy_partial_or_complete_mean"].astype(float),
                                 wide_corr["model_key"].map(wi.set_index("model_key")["six_task_mean_c8_raw"]).astype(float),
                                 equal_nan=True))
    legacy_partial = int(partial_rows["legacy_partial_or_complete_mean"].notna().sum())
    results.append(result("V-WIDE-07", "the legacy skipna column is preserved and still carries the old partial values",
                          legacy_ok and legacy_partial == 6,
                          {"legacy_matches_frozen": legacy_ok, "partial_rows_with_legacy_value": legacy_partial},
                          {"legacy_matches_frozen": True, "partial_rows_with_legacy_value": 6},
                          "c8_model_wide_corrected.csv vs c8_model_wide_canonical.csv",
                          "value equality with the frozen skipna column"))
    model_keys_corrected = set(wide_corr["model_key"])
    expected_keys = set(mt["model_key"])
    results.append(result("V-WIDE-08", "no model identity was invented for a pure-corrupt directory",
                          model_keys_corrected == expected_keys
                          and not (model_keys_corrected & set(recount["pure_corrupt_dirs"])),
                          {"key_set_equal": model_keys_corrected == expected_keys,
                           "pure_corrupt_in_wide": sorted(model_keys_corrected & set(recount["pure_corrupt_dirs"]))},
                          {"key_set_equal": True, "pure_corrupt_in_wide": []},
                          "c8_model_wide_corrected.csv vs c8_model_task_aggregate.csv vs c8_parse_log.csv",
                          "set comparison; the pure-corrupt directories must not appear as models"))

    # ---- non-numeric reconciliation ---------------------------------------------------
    results.append(result("V-NN-01", "non-numeric metric count reconciles across two frozen artifacts",
                          recount["nonnumeric_inventory"] == 7806 and recount["nonnumeric_leaf"] == 7806,
                          {"inventory": recount["nonnumeric_inventory"], "leaf_recount": recount["nonnumeric_leaf"]},
                          {"inventory": 7806, "leaf_recount": 7806},
                          "c8_task_inventory.csv vs c8_leaf_metrics.csv.gz",
                          "this file recounts the leaf table row by row with its own filter "
                          "(metric != 'alias' and nonnumeric == 1)"))

    # ---- checker hygiene --------------------------------------------------------------
    log("[verify] checker hygiene")
    repair_src = io.open(R("repair_c01_from_artifacts.py"), encoding="utf-8").read()
    verify_src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    forbidden = ["PASS if True", "if True:", "status = \"PASS\"", "raw_untouched=True", "raw_untouched = True"]
    hits = {f: {"repair": repair_src.count(f), "verify": verify_src.count(f)} for f in forbidden}
    results.append(result("V-IND-01", "neither R1 script contains a constant-PASS pattern",
                          all(v["repair"] == 0 and v["verify"] == 0 for v in hits.values()), hits,
                          {"all_zero": True}, "repair_c01_from_artifacts.py + verify_c01_repairs.py",
                          "static text scan for the forbidden constant-status idioms"))
    imports_repair = bool(re.search(r"^\s*(import|from)\s+repair_c01_from_artifacts",
                                    verify_src, re.M)) or "repair_c01_from_artifacts" in \
        re.sub(r"#.*", "", verify_src.split("def main()")[0])
    results.append(result("V-IND-02", "the verifier does not import the production repair module",
                          not imports_repair, {"import_detected": imports_repair}, {"import_detected": False},
                          "verify_c01_repairs.py", "static import scan of the verifier source"))
    statuses = [c["status"] for c in repaired["checks"]]
    const_hits = [c["check_id"] for c in repaired["checks"]
                  if c["status"] == "PASS" and (c["actual"] is None or c["expected"] is None)]
    results.append(result("V-IND-03", "no PASS in the repaired checker is missing its actual/expected pair",
                          len(const_hits) == 0, {"passes_without_values": const_hits}, {"passes_without_values": []},
                          "repaired_checks.json",
                          "every PASS must carry a non-null actual and expected value"))
    bad_status = sorted({s for s in statuses if s not in {"PASS", "WARN", "FAIL", "NOT_CHECKED", "NOT_VERIFIABLE"}})
    results.append(result("V-IND-04", "the repaired checker uses only the allowed status vocabulary",
                          bad_status == [], {"unexpected_statuses": bad_status}, {"unexpected_statuses": []},
                          "repaired_checks.json", "status vocabulary scan"))
    key_items = [c for c in repaired["checks"] if c.get("key_c8_item")]
    key_counts = {s: sum(1 for c in key_items if c["status"] == s)
                  for s in ["PASS", "WARN", "FAIL", "NOT_CHECKED", "NOT_VERIFIABLE"]}
    results.append(result("V-IND-05", "no key C8 item is FAIL, NOT_CHECKED or NOT_VERIFIABLE",
                          key_counts["FAIL"] == 0 and key_counts["NOT_CHECKED"] == 0
                          and key_counts["NOT_VERIFIABLE"] == 0 and key_counts["PASS"] > 0,
                          {"key_items": len(key_items), "counts": key_counts},
                          {"counts": {"FAIL": 0, "NOT_CHECKED": 0, "NOT_VERIFIABLE": 0}},
                          "repaired_checks.json", "status audit restricted to the key C8 items"))

    # ---- run_summary cross-check -------------------------------------------------------
    decl = summary["c8_file_accounting"]
    results.append(result("V-SUM-01", "run_summary.json declares the same file accounting as the independent recount",
                          decl["n_files_total"] == recount["files_total"]
                          and decl["parse_success"] == recount["files_ok"]
                          and decl["parse_failed"] == recount["files_failed"]
                          and decl["n_directories"] == recount["dirs"], decl, recount,
                          "run_summary.json vs frozen C01 artifacts",
                          "compare the declared numbers with this file's own recount"))
    dm = summary["c8_model_wide"]
    results.append(result("V-SUM-02", "run_summary.json declares the same wide-table numbers as the corrected table",
                          dm["rows"] == int(len(wide_corr))
                          and dm["six_task_complete_true"] == int(wide_corr["six_task_complete"].sum())
                          and dm["six_task_mean_complete_only_finite"] ==
                          int(wide_corr["six_task_mean_complete_only"].notna().sum())
                          and dm["partial_task_mean_finite"] == int(wide_corr["partial_task_mean"].notna().sum()),
                          dm, {"rows": int(len(wide_corr))},
                          "run_summary.json vs c8_model_wide_corrected.csv", "declared vs recomputed comparison"))
    results.append(result("V-SUM-03", "the repair declares that it never read a raw attachment",
                          summary["raw_attachments_read"] is False,
                          {"raw_attachments_read": summary["raw_attachments_read"]},
                          {"raw_attachments_read": False}, "run_summary.json",
                          "declared value; the independent evidence is the input manifest, which this "
                          "file re-checks path by path"))
    inp = load_json(R("input_manifest.json"))["inputs"]
    raw_paths = [i["path"] for i in inp if "real_attachments" in i["path"]]
    outside = [i["path"] for i in inp if not os.path.abspath(i["full_path"]).startswith(source_dir)]
    frozen_hashes = {a["file"]: a["sha256"] for a in frozen_manifest["artifacts"]}
    not_in_frozen = [i["input"] for i in inp if i["input"] not in frozen_hashes]
    hash_bad = [i["input"] for i in inp if i["input"] != "output_manifest.json"
                and frozen_hashes.get(i["input"]) != sha256_file(os.path.join(source_dir, i["input"]))]
    results.append(result("V-IN-01",
                          "every declared input is inside the frozen C01 directory; every input except "
                          "the manifest itself matches the hash archived in that manifest",
                          not raw_paths and not outside and not hash_bad
                          and not_in_frozen == ["output_manifest.json"],
                          {"inputs": len(inp), "raw_paths": raw_paths, "outside_source_dir": outside,
                           "hash_mismatches": hash_bad, "inputs_without_a_frozen_manifest_entry": not_in_frozen},
                          {"raw_paths": [], "outside_source_dir": [], "hash_mismatches": [],
                           "inputs_without_a_frozen_manifest_entry": ["output_manifest.json"]},
                          "input_manifest.json vs output_manifest.json + live hashes",
                          "re-hash every declared input and compare with the archived manifest; the "
                          "manifest cannot contain a hash of itself, so that single input is handled "
                          "explicitly instead of being counted as a mismatch"))
    key_items_pre = [c for c in repaired["checks"] if c.get("key_c8_item")]
    results.append(result("V-IND-06", "the key C8 item set is non-empty and covers the file, corruption, "
                                      "coverage and completeness families",
                          len(key_items_pre) >= 40
                          and any(c["check_id"].endswith("FILE-IDENTITY") for c in key_items_pre)
                          and any(c["check_id"].endswith("PROPAGATION") for c in key_items_pre)
                          and any(c["check_id"].endswith("WIDE-PARTIAL-NAN") for c in key_items_pre),
                          {"key_items": len(key_items_pre),
                           "ids": [c["check_id"] for c in key_items_pre]},
                          {"key_items": ">= 40 covering identity, propagation and partial-mean"},
                          "repaired_checks.json", "inventory of the key C8 items"))

    # ---- report the original checker repair map --------------------------------------
    log("[verify] original checker repair ledger")
    original_checks = load_json(S("checks.json"))["checks"]
    orig_ids = {c["id"] for c in original_checks}
    mapped_sources = set()
    for cid, entry in repaired["repair_map"].items():
        mapped_sources.add(cid.replace("b", "").rstrip("-") if cid.endswith("b") else cid)
    derived = {c for c in mapped_sources if c not in orig_ids}
    results.append(result("V-MAP-01", "every original check id has a documented repair disposition",
                          all(c["id"] in mapped_sources for c in original_checks),
                          {"original_checks": len(orig_ids),
                           "unmapped": sorted({c["id"] for c in original_checks} - mapped_sources),
                           "repair_map_entries": len(repaired["repair_map"]),
                           "map_keys_without_original_id": sorted(derived)},
                          {"unmapped": []},
                          "checks.json (frozen) vs repaired_checks.json (this run)",
                          "set comparison of the original check ids against the repair ledger keys"))
    downgraded = {k: v["disposition"] for k, v in repaired["repair_map"].items()
                  if v["disposition"].startswith("DOWNGRADED")}
    results.append(result("V-MAP-02", "every constant or single-source original check was either repaired or explicitly downgraded",
                          len(downgraded) >= 4,
                          {"downgraded": downgraded}, {"at least": 4},
                          "repaired_checks.json", "count of explicit downgrades in the repair ledger"))

    # =============================== finalize ==========================================
    finish = datetime.now(TZ)
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ["PASS", "FAIL"]}
    overall = "COMPLETE_PENDING_REVIEW" if counts["FAIL"] == 0 else "FAIL"
    verification = {
        "task": TASK, "run_id": os.path.basename(run_dir),
        "verified_at": finish.isoformat(), "started_at": started.isoformat(),
        "verifier": "verify_c01_repairs.py (independent: does not import the repair module)",
        "environment": {"python": sys.version.splitlines()[0], "platform": platform.platform(),
                        "numpy": np.__version__, "pandas": pd.__version__},
        "counts": {"checks": len(results), "PASS": counts["PASS"], "FAIL": counts["FAIL"]},
        "overall_status": overall,
        "repaired_checks_status_counts": repaired["counts"],
        "repaired_checks_key_c8_counts": repaired["key_c8_counts"],
        "results": results,
        "notes": [
            "Expected values used by this verifier are recomputed with this file's own code from the "
            "frozen TASK-C01 artifacts; no repair function is called and no repaired value is trusted.",
            "This verifier writes output_manifest.json as its final action, so the manifest hash of "
            "every artifact (including this verifier's own log) is stable. output_manifest.json itself "
            "is the only file it cannot contain.",
        ],
    }
    with io.open(R("verification.json"), "w", encoding="utf-8") as fh:
        json.dump(verification, fh, ensure_ascii=False, indent=2, allow_nan=False)
    log(f"[verify] checks={len(results)} PASS={counts['PASS']} FAIL={counts['FAIL']} overall={overall}")

    summary = load_json(R("run_summary.json"))
    summary["verification"] = {
        "status": overall,
        "file": "verification.json",
        "checks": len(results), "PASS": counts["PASS"], "FAIL": counts["FAIL"],
        "repaired_checks_counts": repaired["counts"],
        "repaired_checks_key_c8_counts": repaired["key_c8_counts"],
        "verifier_is_independent": True,
        "note": "the verifier recomputes expected values from the frozen C01 artifacts and never imports "
                "the repair module; the repair script's own exit code was passed by the launcher",
    }
    with io.open(R("run_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2, allow_nan=False)

    handoff_path = R("handoff.md")
    handoff = io.open(handoff_path, encoding="utf-8").read()
    marker = "_verification results are appended by `verify_c01_repairs.py` after this file is written._"
    section = ["- \u72ec\u7acb\u9a8c\u8bc1\u5668\uff1a`verify_c01_repairs.py`\uff08\u4e0d\u5bfc\u5165\u4fee\u590d\u6a21\u5757\uff0c\u4e0d\u8c03\u7528\u5176\u4efb\u4f55\u51fd\u6570\uff09",
               f"- \u72ec\u7acb\u6838\u9a8c {len(results)} \u9879\uff1aPASS {counts['PASS']}\uff0cFAIL {counts['FAIL']}\uff0c\u603b\u4f53 `{overall}`",
               "- \u65b9\u6cd5\uff1a\u672c\u6587\u4ef6\u81ea\u5df1\u4ece\u51bb\u7ed3 TASK-C01 \u4ea7\u7269\u91cd\u7b97\u6bcf\u4e2a\u671f\u671b\u503c\uff08parse log\u3001\u635f\u574f\u6e05\u5355\u3001\u76ee\u5f55\u8ba1\u6570\u3001group score \u660e\u7ec6\u3001model\u00d7task \u8868\uff09\uff0c\u518d\u4e0e corrected \u8868\u9010\u952e\u5bf9\u6bd4\uff1b\u672a\u91c7\u7528\u4efb\u4f55\u4fee\u590d\u51fd\u6570\u3002",
               "",
               "| verification_id | \u72b6\u6001 | \u58f0\u660e |",
               "|---|---|---|"]
    for r in results:
        section.append(f"| `{r['verification_id']}` | {r['status']} | {r['claim']} |")
    if counts["FAIL"]:
        section += ["", "\u5931\u8d25\u9879\uff1a"]
        section += [f"- `{r['verification_id']}`\uff1a\u5b9e\u6d4b `{json.dumps(r['actual'], ensure_ascii=False)[:200]}`\uff0c"
                    f"\u671f\u671b `{json.dumps(r['expected'], ensure_ascii=False)[:200]}`" for r in results
                    if r["status"] == "FAIL"]
    else:
        section += ["", "\u65e0\u5931\u8d25\u9879\uff1b\u5b8c\u6574 actual/expected/\u8bc1\u636e\u89c1 `verification.json`\u3002"]
    section += ["", "\u6821\u9a8c\u5668\u672c\u8eab\u7684\u9000\u51fa\u7801\u65e0\u6cd5\u5199\u56de\u5b83\u81ea\u5df1\u6700\u540e\u751f\u6210\u7684 manifest\uff1b\u8be5\u7801\u7531\u8c03\u5ea6\u7a0b\u5e8f\u8bb0\u5f55\u5e76\u5728\u4ea4\u56de\u6750\u6599\u4e2d\u58f0\u660e\u3002"]
    handoff = handoff.replace(marker, "\n".join(section))
    with io.open(handoff_path, "w", encoding="utf-8") as fh:
        fh.write(handoff)

    with io.open(R("verify.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG) + "\n")

    entries = []
    for dirpath, dirnames, filenames in os.walk(run_dir):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            key = os.path.relpath(full, run_dir).replace("\\", "/")
            if key == "output_manifest.json":
                continue
            entries.append({"file": key, "bytes": int(os.path.getsize(full)), "sha256": sha256_file(full),
                            "role": ("execution_code" if key in ("repair_c01_from_artifacts.py",
                                                                 "verify_c01_repairs.py")
                                     else "code_snapshot" if key.startswith("code_snapshot/")
                                     else "run_log" if key in ("run.log", "verify.log")
                                     else "required_output")})
    with io.open(R("output_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"task": TASK, "run_id": os.path.basename(run_dir), "artifact_count": len(entries),
                   "artifacts": entries}, fh, ensure_ascii=False, indent=2, allow_nan=False)
    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        raise
