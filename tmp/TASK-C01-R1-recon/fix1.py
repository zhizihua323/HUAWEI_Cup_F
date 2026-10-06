import io
p = r"tmp\TASK-C01-R1-staging\repair_c01_from_artifacts.py"
s = io.open(p, encoding="utf-8").read()
bad = '''    add("R1-ID-NO-IMPUTE-STATEMENT", "the frozen run recorded missingness as measured and did not impute parameters or licences",
        "NOT_VERIFIABLE" if True else None,
        {"observable": "counters only"}, "a machine-readable no-imputation certificate",
        "missingness.csv + field_audit.csv + handoff.md",
        "absence-of-action claims are not provable from summary tables; the frozen checks.json "
        "ID-04 was a hard-coded PASS", "recorded, never counted as PASS")
    CHECKS.pop()
    add_negative('''
good = '''    add_negative('''
assert bad in s
s = s.replace(bad, good, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("cleaned; 'if True' occurrences now:", s.count("if True"))
