import io
def rep(path, old, new, cnt=1):
    s = io.open(path, encoding="utf-8").read()
    assert old in s, "NOT FOUND in %s: %s" % (path, old[:120])
    io.open(path, "w", encoding="utf-8").write(s.replace(old, new, cnt))

rp = r"tmp\TASK-C01-R1-staging\repair_c01_from_artifacts.py"
vp = r"tmp\TASK-C01-R1-staging\verify_c01_repairs.py"

# A) drop the unused literal list from the repair script (it contained a forbidden-probe string)
rep(rp, '''CHECKS = []

# Checks that guard''', '''CHECKS = []

# Checks that guard''')
s = io.open(rp, encoding="utf-8").read()
s = s.replace('FORBIDDEN_STATUS_PATTERNS = ["PASS if True", "status = PASS", "== \\"PASS\\"  # constant"]\n', "")
io.open(rp, "w", encoding="utf-8").write(s)

# B1) pure-corrupt directories must be derived from the FULL parse log
rep(vp, '''        "pure_corrupt_dirs": sorted(bad_rows.groupby("directory")
                                    .apply(lambda g: int((g["parse_status"] == "ok").sum()), include_groups=False)
                                    .loc[lambda s: s == 0].index.tolist()),''',
'''        "pure_corrupt_dirs": sorted(
            pl.groupby("directory")["parse_status"]
            .apply(lambda s: int((s == "ok").sum()))
            .loc[lambda s: s == 0].index.tolist()),''')

# B2) meta-scan: assemble the probes so this file does not contain them verbatim
rep(vp, '''    forbidden = ["PASS if True", "if True:", "status = \\"PASS\\"", "raw_untouched=True", "raw_untouched = True"]
    hits = {f: {"repair": repair_src.count(f), "verify": verify_src.count(f)} for f in forbidden}
    results.append(result("V-IND-01", "neither R1 script contains a constant-PASS pattern",
                          all(v["repair"] == 0 and v["verify"] == 0 for v in hits.values()), hits,
                          {"all_zero": True}, "repair_c01_from_artifacts.py + verify_c01_repairs.py",
                          "static text scan for the forbidden constant-status idioms"))''',
'''    probes = ["PASS " + "if True", "if " + "True:", "status " + "= \\"PASS\\"",
              "raw_" + "untouched" + "=" + "True", "raw_" + "untouched " + "= True",
              "PASS" + "**"]
    hits = {p: {"repair": repair_src.count(p), "verify": verify_src.count(p)} for p in probes}
    results.append(result("V-IND-01", "neither R1 script contains a constant-PASS pattern",
                          all(v["repair"] == 0 and v["verify"] == 0 for v in hits.values()), hits,
                          {"all_zero": True}, "repair_c01_from_artifacts.py + verify_c01_repairs.py",
                          "static text scan for constant-status idioms; the probe strings are assembled "
                          "at run time so that this scanner does not match its own source"))''')

# B3) import independence checked on the AST, not on free text
rep(vp, '''    imports_repair = bool(re.search(r"^\\s*(import|from)\\s+repair_c01_from_artifacts",
                                    verify_src, re.M)) or "repair_c01_from_artifacts" in \\
        re.sub(r"#.*", "", verify_src.split("def main()")[0])
    results.append(result("V-IND-02", "the verifier does not import the production repair module",
                          not imports_repair, {"import_detected": imports_repair}, {"import_detected": False},
                          "verify_c01_repairs.py", "static import scan of the verifier source"))''',
'''    import ast as _ast
    imported_modules = []
    for _node in _ast.walk(_ast.parse(verify_src)):
        if isinstance(_node, _ast.Import):
            imported_modules += [a.name for a in _node.names]
        elif isinstance(_node, _ast.ImportFrom):
            imported_modules.append(_node.module or "")
    repair_imports = [m for m in imported_modules if "repair_c01_from_artifacts" in m]
    verify_imports = []
    for _node in _ast.walk(_ast.parse(repair_src)):
        if isinstance(_node, _ast.Import):
            verify_imports += [a.name for a in _node.names]
        elif isinstance(_node, _ast.ImportFrom):
            verify_imports.append(_node.module or "")
    reverse = [m for m in verify_imports if "verify_c01_repairs" in m]
    results.append(result("V-IND-02", "the verifier does not import the production repair module",
                          not repair_imports and not reverse,
                          {"verifier_imports_repair": repair_imports, "repair_imports_verifier": reverse,
                           "verifier_import_count": len(imported_modules)},
                          {"verifier_imports_repair": [], "repair_imports_verifier": []},
                          "verify_c01_repairs.py + repair_c01_from_artifacts.py",
                          "AST import-graph inspection (docstrings and comments are ignored)"))''')

# B4) make the handoff append idempotent
rep(vp, '''    handoff_path = R("handoff.md")
    handoff = io.open(handoff_path, encoding="utf-8").read()
    marker = "_verification results are appended by `verify_c01_repairs.py` after this file is written._"''',
'''    handoff_path = R("handoff.md")
    handoff = io.open(handoff_path, encoding="utf-8").read()
    marker = "_verification results are appended by `verify_c01_repairs.py` after this file is written._"
    heading9 = "## 9. \\u72ec\\u7acb\\u9a8c\\u8bc1\\uff08verify_c01_repairs.py\\uff09"
    cut = handoff.find(heading9)
    if cut != -1:
        base_handoff = handoff[:cut].rstrip("\\n") + "\\n\\n" + heading9 + "\\n\\n" + marker + "\\n"
    else:
        base_handoff = handoff.rstrip("\\n") + "\\n"''')
rep(vp, '''    handoff = handoff.replace(marker, "\\n".join(section))
    with io.open(handoff_path, "w", encoding="utf-8") as fh:
        fh.write(handoff)''',
'''    with io.open(handoff_path, "w", encoding="utf-8") as fh:
        fh.write(base_handoff + "\\n" + "\\n".join(section) + "\\n")''')

print("both scripts patched")
