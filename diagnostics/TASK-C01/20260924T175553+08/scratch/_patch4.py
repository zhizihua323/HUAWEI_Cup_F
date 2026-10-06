import io, ast
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
s = io.open(p, encoding="utf-8").read()
old = """    for (ds, f), (unit, evidence, lo, hi, scale) in UNIT_SPEC.items():
        if f in frames[ds].columns:
            add(ds, f, unit, evidence, lo, hi, scale, frames[ds][f])"""
new = """    for (ds, f), (unit, evidence, lo, hi, scale) in UNIT_SPEC.items():
        if ds in frames and f in frames[ds].columns:
            add(ds, f, unit, evidence, lo, hi, scale, frames[ds][f])"""
assert old in s
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AST OK")
