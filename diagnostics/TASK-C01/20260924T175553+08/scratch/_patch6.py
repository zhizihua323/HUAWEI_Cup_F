import io, ast
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
s = io.open(p, encoding="utf-8").read()

def rep(old, new):
    global s
    assert old in s, "NOT FOUND: " + old[:100]
    s = s.replace(old, new, 1)

# --- F1: C3 Year must stay a calendar year, not a nanosecond epoch --------------
rep('''def build_date_audit(frames, c8_dates):
    rows = [
        date_audit_rows("C1", "Submission Date", frames["C1"]["Submission Date"], "day", "day"),''',
'''def build_date_audit(frames, c8_dates):
    c3_year_row = date_audit_rows("C3", "Year", frames["C3"]["Year"], "year", "year")
    yrs = numeric_view(frames["C3"]["Year"])
    c3_year_row.update({
        "min": str(int(yrs.min())), "max": str(int(yrs.max())),
        "distinct_dates": int(yrs.nunique()),
        "duplicate_date_rows": int(yrs.dropna().duplicated().sum()),
        "span_days": int(yrs.max() - yrs.min()),
        "note": "raw integer calendar year; it is NOT converted to a timestamp, so no spurious sub-second value is introduced",
    })
    rows = [
        c3_year_row,
        date_audit_rows("C1", "Submission Date", frames["C1"]["Submission Date"], "day", "day"),''')
rep('''        date_audit_rows("C3", "Year", frames["C3"]["Year"], "year", "year"),
''', "")
rep('''        date_audit_rows("C8", "date (unix seconds, top level)", c8_dates, "second", "second"),
    ]''',
'''        date_audit_rows("C8", "date (unix seconds, top level)", c8_dates, "second", "second"),
    ]
    # Present timestamp ranges with the precision that actually exists in the file.
    for row in rows:
        if row["dataset"] == "C8" and row["min"]:
            row["min"] = str(pd.Timestamp(row["min"]).floor("ms"))
            row["max"] = str(pd.Timestamp(row["max"]).floor("ms"))
            row["note"] = ("unix seconds with sub-second fraction; displayed truncated to milliseconds. "
                           "start_time/end_time strings are kept verbatim in c8_parse_log.csv")''')
rep('''    c4 = frames["C4"].copy()
    c4["publication_parsed"] = pd.to_datetime(c4["Publication date"], errors="coerce", format="mixed")''',
'''    for row in rows:
        if row["dataset"] == "C4" and row["field"] == "Publication date":
            pub = pd.to_datetime(frames["C4"]["Publication date"], errors="coerce", format="mixed")
            early = frames["C4"].loc[pub.lt("2000-01-01"), "Model"].astype(str)
            row["note"] = (f"publication dates before 2000-01-01: {int(pub.lt('2000-01-01').sum())} rows"
                           + (f"; earliest row model = {pub.idxmin()} / {frames['C4'].loc[pub.idxmin(), 'Model']}" if pub.notna().any() else "")
                           + "; Epoch is a living database, so a few reported dates are not model-generation dates")
            row["rows_before_2000"] = int(pub.lt("2000-01-01").sum())
    c4 = frames["C4"].copy()
    c4["publication_parsed"] = pd.to_datetime(c4["Publication date"], errors="coerce", format="mixed")''')

# --- F2: non-numeric metric counting must separate `alias` from numeric metrics ---
rep('''            stat = task_stats.setdefault(task_key, {
                "n_files_present": 0, "n_files_with_metric": 0, "metrics": {}, "nonnumeric_values": 0,''',
'''            stat = task_stats.setdefault(task_key, {
                "n_files_present": 0, "n_files_with_metric": 0, "metrics": {}, "nonnumeric_values": 0,
                "alias_values": 0, "metric_values": 0,''')
rep('''                    if not is_number(value):
                        stat["nonnumeric_values"] += 1
                    total += 1''',
'''                    if metric == "alias":
                        stat["alias_values"] += 1
                    else:
                        stat["metric_values"] += 1
                        if not is_number(value):
                            stat["nonnumeric_values"] += 1
                    total += 1''')
rep('''            "nonnumeric_metric_values": stat["nonnumeric_values"],''',
'''            "numeric_metric_value_slots": stat["metric_values"],
            "nonnumeric_metric_values": stat["nonnumeric_values"],
            "alias_string_values": stat["alias_values"],''')

# --- F3: manifest must cover the whole run directory, including scratch -----------
rep('''def write_manifest(extra_exclude=("output_manifest.json",)):
    entries = []
    for name in sorted(os.listdir(OUT)):
        path = os.path.join(OUT, name)
        if not os.path.isfile(path):
            continue
        entries.append({"file": name, "bytes": int(os.path.getsize(path)),
                        "sha256": sha256_file(path),
                        "is_required_output": name in REQUIRED_OUTPUTS or name in ("audit_c01.py", "run.log")})
    write_json("output_manifest.json", {"run_id": RUN_ID, "task": TASK,
                                        "artifact_count": len(entries), "artifacts": entries})
    return entries''',
'''def write_manifest():
    """Recursive: every file produced by this run is hashed, including scratch scripts."""
    entries = []
    for dirpath, dirnames, filenames in os.walk(OUT):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            key = os.path.relpath(path, OUT).replace("\\\\", "/")
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
    return entries''')

io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AST OK, chars", len(s))
