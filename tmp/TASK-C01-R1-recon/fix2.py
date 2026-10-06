import io
p = r"tmp\TASK-C01-R1-staging\verify_c01_repairs.py"
s = io.open(p, encoding="utf-8").read()
bad = '''    results.append(result("V-C8-06", "DreadPoor contributes 6 finite scores; the other three damaged directories contribute 0",
                          True, None, None, "c8_group_scores_all_runs.csv", "per-directory recount"))
    results.pop()
'''
good = '''    finite_per_dir = gs.groupby("directory")["score"].apply(lambda s: int(s.notna().sum())).to_dict()
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
'''
assert bad in s
s = s.replace(bad, good, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("patched v1 ending; 'results.pop' occurrences:", s.count("results.pop"))
