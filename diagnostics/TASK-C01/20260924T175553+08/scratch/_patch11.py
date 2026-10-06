import io, ast
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
s = io.open(p, encoding="utf-8").read()
old = '''            nan_mismatch = int((a.isna() != b.isna()).sum())
            neg_b = int((b.astype(float) < 0).sum())
            note = (f"max abs diff={maxdiff}; rows equal to <=1e-12: {int((np.abs(a.astype(float)-b.astype(float)) <= 1e-12).sum())}; "
                    f"rows where only one side is missing={nan_mismatch}; negative values in C9 column={neg_b}")'''
new = '''            nan_mismatch = int((a.isna() != b.isna()).sum())
            neg_a = int((a.astype(float) < 0).sum())
            neg_b = int((b.astype(float) < 0).sum())
            note = (f"max abs diff={maxdiff}; rows equal to <=1e-12: {int((np.abs(a.astype(float)-b.astype(float)) <= 1e-12).sum())}; "
                    f"rows where only one side is missing={nan_mismatch}; negatives in C9 side={neg_a}; negatives in C1 side={neg_b}"
                    + ("; NOTE the C9 side uses -1 as a missing sentinel where C1 has NaN" if neg_a and nan_mismatch else ""))'''
assert old in s
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AST OK")
