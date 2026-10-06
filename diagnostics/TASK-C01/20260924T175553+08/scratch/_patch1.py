import io, sys
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
src = io.open(p, encoding="utf-8").read()
orig = src

def rep(old, new, count=1):
    global src
    assert src.count(old) >= 1, "NOT FOUND: " + old[:90]
    src = src.replace(old, new, count)

# P1: import re at top level
rep("import platform\nimport sys\n", "import platform\nimport re\nimport sys\n")

# P2: Epochs is a count, not a date
rep('if "date" in field.lower() or "Date" in field or field in ("Year", "Last modified", "Epochs"):',
    'if "date" in field.lower() or "Date" in field or field in ("Year", "Last modified"):')

# P3: correct blank/sentinel counting for missingness.csv
rep('''        miss = int(frame[col].isna().sum())
        blank = int(frame[col].astype(str).str.strip().isin(["", "nan", "NaN", "None", "-", "N/A", "NA"]).sum())
        out.append({"dataset": name, "field": col, "rows": n, "missing_nan": miss,
                    "missing_nan_pct": round(100.0 * miss / n, 6) if n else np.nan,
                    "blank_or_sentinel_string": blank - (miss if frame[col].dtype.kind in "fi" else 0),
                    "all_missing": bool(miss == n)})''',
'''        miss = int(frame[col].isna().sum())
        nonnull = frame[col].notna()
        blank = int(frame.loc[nonnull, col].astype(str).str.strip()
                    .isin(["", "nan", "NaN", "None", "N/A", "NA", "-"]).sum())
        sentinel = int(numeric_view(frame[col]).isin([-1]).sum())
        out.append({"dataset": name, "field": col, "rows": n, "missing_nan": miss,
                    "missing_nan_pct": round(100.0 * miss / n, 6) if n else np.nan,
                    "blank_string_among_nonnull": blank,
                    "numeric_minus1_sentinel": sentinel,
                    "effective_usable": int(n - miss - blank),
                    "all_missing": bool(miss == n)})''')

# P4: build_inventory takes already-loaded frames
rep('''def build_inventory():
    rows = []''', '''def build_inventory(frames, c8_files):
    rows = []''')
rep('''    for ds, fname in CSV_FILES.items():
        path = os.path.join(CROOT, fname)
        frame = pd.read_csv(epath(path), low_memory=False)
        add(ds, path, "csv", rows_=len(frame), cols=frame.shape[1])
    # C8: JSON tree
    c8_root = os.path.join(CROOT, "detailed_results")
    c8_files = collect_c8_files(c8_root)
    add("C8", c8_root, "json_tree"''', '''    for ds, fname in CSV_FILES.items():
        path = os.path.join(CROOT, fname)
        frame = frames[ds]
        add(ds, path, "csv", rows_=len(frame), cols=frame.shape[1])
    # C8: JSON tree
    c8_root = os.path.join(CROOT, "detailed_results")
    add("C8", c8_root, "json_tree"''')
rep('''    p9 = os.path.join(CROOT, "data", "train-00000-of-00001.parquet")
    pq = pd.read_parquet(epath(p9))
    add("C9", p9, "parquet", rows_=len(pq), cols=pq.shape[1])''',
'''    p9 = os.path.join(CROOT, "data", "train-00000-of-00001.parquet")
    pq = frames["C9"]
    add("C9", p9, "parquet", rows_=len(pq), cols=pq.shape[1])''')

# P5: carry model_num_parameters into the C8 records
rep('''        base = {"directory": item["directory"], "file": item["file"], "Model": resolved_name,
                "model_name_field": entry["model_name"], "model_sha": entry["model_sha"],
                "eval_unix_date": entry["eval_unix_date"]}''',
'''        base = {"directory": item["directory"], "file": item["file"], "Model": resolved_name,
                "model_name_field": entry["model_name"], "model_sha": entry["model_sha"],
                "model_num_parameters": entry["model_num_parameters"],
                "eval_unix_date": entry["eval_unix_date"]}''')
rep('''    long = rec.melt(id_vars=["directory", "file", "Model", "model_name_field", "model_sha", "eval_unix_date"],
                    value_vars=TASKS, var_name="task_group", value_name="score")
    long = long.merge(rec[["directory", "file", "six_groups_complete", "model_num_parameters"]
                           if "model_num_parameters" in rec.columns else ["directory", "file", "six_groups_complete"]],
                      on=["directory", "file"], how="left")''',
'''    long = rec.melt(id_vars=["directory", "file", "Model", "model_name_field", "model_sha", "eval_unix_date"],
                    value_vars=TASKS, var_name="task_group", value_name="score")''')

# P6: unit audit signature + drop dead code
rep("def build_unit_audit(frames, bridge, c8_stats):", "def build_unit_audit(frames, c8_stats):")
rep('''    if bridge["value_range_rows"]:
        pass
    return pd.DataFrame(rows)''', '''    return pd.DataFrame(rows)''')

# P7: params_missing among parseable documents only
rep('''        "params_missing": int(records_df.shape[0] - (parse_log_df.model_num_parameters.notna().sum())) if len(records_df) else 0,''',
'''        "params_missing": int(n_ok - parse_log_df.loc[parse_log_df.parse_status.eq("ok"), "model_num_parameters"].notna().sum()),''')

# P8: hardcoded duplicate-run count -> measured value
rep('"- C8 目录内 95 次重复评测的取舍规则属于下游建模决策，本任务只提供事实与两种口径的分数。",',
    'f"- C8 目录内 {ctx[\'multi_file_dirs\']} 次重复评测（同一目录第二份 JSON）的取舍规则属于下游建模决策，本任务只提供事实与两种口径的分数。",')

# P9: main call sites
rep("    inventory, _ = build_inventory(c8_files)", "    inventory, _ = build_inventory(frames, c8_files)")
rep("    unit_audit_df = build_unit_audit(frames, None, c8_stats)", "    unit_audit_df = build_unit_audit(frames, c8_stats)")

io.open(p, "w", encoding="utf-8").write(src)
print("patched OK; size %d -> %d" % (len(orig), len(src)))
