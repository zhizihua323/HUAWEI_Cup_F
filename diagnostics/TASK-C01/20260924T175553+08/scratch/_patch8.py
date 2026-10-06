import io, ast
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
s = io.open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert old in s, "NOT FOUND: " + old[:110]
    s = s.replace(old, new, 1)

rep('''        "duplicate_date_rows": int(yrs.dropna().duplicated().sum()),
        "span_days": int(yrs.max() - yrs.min()),''',
    '''        "duplicate_date_rows": int(yrs.dropna().duplicated().sum()),
        "span_days": np.nan, "span_years": int(yrs.max() - yrs.min()),''')

rep('''        f"| OOS-03 | C8 全库 {n_batch} 份文件同名 `{batch_name}`，其中 {n_batch_bad} 份损坏（疑似同一批下载被截断） | `c8_corrupt_files.csv`、`c8_parse_log.csv` | 是否补下/重新评测需要主控决定 |",''',
    '''        f"| OOS-03 | C8 全库 {n_batch} 份 JSON 同名 `{batch_name}`（同一 2025-02-13 评测批次），其中 {n_batch_bad} 份损坏；损坏文件大小恰为 64/48 KiB 且解析错误位置在文件末尾 97.9%–100% 处，是下载被截断的直接证据 | `c8_corrupt_files.csv`（含文件尾部字节）、`c8_parse_log.csv`（`error_at_eof_fraction`、`file_ends_with_closing_brace`） | 是否补下/重新评测需要主控决定 |",''')

rep('''        f"- 解析出的模型名（`model_name`）去重 **{int(ctx['c8_records'].Model.nunique())}** 个；目录名去重 {int(log_df.directory.nunique())} 个。",''',
    '''        f"- JSON 内 `model_name` 字段去重 **{int(log_df.loc[log_df.parse_status.eq('ok'), 'model_name'].nunique())}** 个（原样字符串，未做别名合并）；",
        f"  目录名去重 {int(log_df.directory.nunique())} 个；`c8_model_wide_canonical.csv` 中 目录×解析模型名 组合 {len(wi)} 行。",''')

io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AST OK, chars", len(s))
