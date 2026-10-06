import io, ast
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
s = io.open(p, encoding="utf-8").read()

def rep(old, new):
    global s
    assert old in s, old[:80]
    s = s.replace(old, new, 1)

rep('''        "c5_c6": {"n_merged_on_model": int(len(ctx["c5c6"]["n_merged"])) if isinstance(ctx["c5c6"]["n_merged"], int) else ctx["c5c6"]["n_merged"],''',
    '''        "c5_c6": {"n_merged_on_model": ctx["c5c6"]["n_merged"],''')

rep('''         "likely_truncated": int(ctx["parse_log"].likely_truncated.fillna(False).sum())},''',
    '''         "likely_truncated": int(ctx["parse_log"].likely_truncated.eq(True).sum())},''')
rep('''            "likely_truncated": int(log_df.likely_truncated.fillna(False).sum()),''',
    '''            "likely_truncated": int(log_df.likely_truncated.eq(True).sum()),''')
rep('''        f"- 其中文件名尾部不含闭合花括号或错误位置在文件末端 95% 之后的计为“疑似截断”：{int(log_df.likely_truncated.fillna(False).sum())} 个。", "",''',
    '''        f"- 其中文件名尾部不含闭合花括号或错误位置在文件末端 95% 之后的计为“疑似截断”：{int(log_df.likely_truncated.eq(True).sum())} 个。", "",''')

rep('''    entries = write_manifest()
    log(f"[manifest] {len(entries)} artifacts listed in output_manifest.json")
    end = datetime.now(TZ)
    log(f"[done] finished {end.isoformat()}  duration={(end - START).total_seconds():.1f}s")
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as handle:
        handle.write("\\n".join(LOG_LINES) + "\\n")''',
'''    end = datetime.now(TZ)
    log(f"[done] finished {end.isoformat()}  duration={(end - START).total_seconds():.1f}s")
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as handle:
        handle.write("\\n".join(LOG_LINES) + "\\n")
    entries = write_manifest()
    print(f"[manifest] {len(entries)} artifacts listed in output_manifest.json", flush=True)''')

io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AST OK")
