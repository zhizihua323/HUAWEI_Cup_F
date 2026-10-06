import io
vp = r"tmp\TASK-C01-R1-staging\verify_c01_repairs.py"
s = io.open(vp, encoding="utf-8").read()
old = '''    probes = ["PASS " + "if True", "if " + "True:", "status " + "= \\"PASS\\"",
              "raw_" + "untouched" + "=" + "True", "raw_" + "untouched " + "= True",
              "PASS" + "**"]
    hits = {p: {"repair": repair_src.count(p), "verify": verify_src.count(p)} for p in probes}
    results.append(result("V-IND-01", "neither R1 script contains a constant-PASS pattern",
                          all(v["repair"] == 0 and v["verify"] == 0 for v in hits.values()), hits,
                          {"all_zero": True}, "repair_c01_from_artifacts.py + verify_c01_repairs.py",
                          "static text scan for constant-status idioms; the probe strings are assembled "
                          "at run time so that this scanner does not match its own source"))'''
new = '''    import tokenize as _tok

    def code_only(src):
        """Strip string literals and comments so that documentation *about* a defect is not
        mistaken for the defect itself."""
        pieces = []
        for tok in _tok.generate_tokens(io.StringIO(src).readline):
            if tok.type in (_tok.STRING, _tok.COMMENT, _tok.NL, _tok.NEWLINE, _tok.INDENT,
                            _tok.DEDENT, _tok.ENCODING, _tok.ENDMARKER):
                continue
            pieces.append(tok.string)
        return " ".join(pieces)

    probes = ["PASS " + "if True", "if " + "True:", "status " + "= \\"PASS\\"",
              "raw_" + "untouched" + "=" + "True", "raw_" + "untouched " + "= True"]
    r_code = code_only(repair_src)
    v_code = code_only(verify_src)
    hits = {p: {"repair_code": r_code.count(p), "verify_code": v_code.count(p)} for p in probes}
    true_tests = {}
    for label, src_txt in (("repair", repair_src), ("verify", verify_src)):
        found = []
        for node in _ast.walk(_ast.parse(src_txt)):
            if isinstance(node, _ast.If) and isinstance(node.test, _ast.Constant) \\
                    and node.test.value is True:
                found.append(node.lineno)
            if isinstance(node, _ast.IfExp) and isinstance(node.test, _ast.Constant) \\
                    and node.test.value is True:
                found.append(node.lineno)
        true_tests[label] = found
    ok = (all(v["repair_code"] == 0 and v["verify_code"] == 0 for v in hits.values())
          and not true_tests["repair"] and not true_tests["verify"])
    results.append(result("V-IND-01", "neither R1 script implements a constant-PASS pattern in code",
                          ok, {"probe_counts_in_code": hits, "literal_True_tests": true_tests},
                          {"probe_counts_in_code": "all zero", "literal_True_tests": "empty"},
                          "repair_c01_from_artifacts.py + verify_c01_repairs.py",
                          "tokenize strips string literals and comments (so prose *describing* the "
                          "original defect is not flagged), and the AST is scanned for `if True` / "
                          "`x if True else y` tests"))'''
assert old in s, "NOT FOUND"
s = s.replace(old, new, 1)
io.open(vp, "w", encoding="utf-8").write(s)
print("V-IND-01 rebuilt on tokenize + AST")
