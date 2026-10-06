import io, ast
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
s = io.open(p, encoding="utf-8").read()
old = '''        if a.dtype.kind in "fi":
            agree = np.isclose(a.astype(float), b.astype(float), equal_nan=True)
            maxdiff = float(np.nanmax(np.abs(a.astype(float) - b.astype(float)))) if int(np.sum(~agree)) and a.notna().any() else 0.0
            how = "numeric within 1e-8 abs/1e-5 rel"
            small = int((np.abs(a.astype(float) - b.astype(float)) <= 1e-12).sum())
            note = f"max abs diff={maxdiff}; rows equal to <=1e-12: {small}"
        else:
            an = a.where(a.notna(), "<NA>").astype(str).str.strip()
            bn = b.where(b.notna(), "<NA>").astype(str).str.strip()
            agree = (an == bn).to_numpy()
            note = "string comparison after strip; missing rendered as <NA>"'''
new = '''        if a.dtype.kind in "fi":
            agree = np.isclose(a.astype(float), b.astype(float), equal_nan=True)
            maxdiff = float(np.nanmax(np.abs(a.astype(float) - b.astype(float)))) if int(np.sum(~agree)) and a.notna().any() else 0.0
            nan_mismatch = int((a.isna() != b.isna()).sum())
            neg_b = int((b.astype(float) < 0).sum())
            note = (f"max abs diff={maxdiff}; rows equal to <=1e-12: {int((np.abs(a.astype(float)-b.astype(float)) <= 1e-12).sum())}; "
                    f"rows where only one side is missing={nan_mismatch}; negative values in C9 column={neg_b}")
        else:
            an = a.where(a.notna(), "<NA>").astype(str).str.strip()
            bn = b.where(b.notna(), "<NA>").astype(str).str.strip()
            agree = (an == bn).to_numpy()
            a_empty = (a.isna() | (a.astype(str).str.strip() == "")).to_numpy()
            b_empty = (b.isna() | (b.astype(str).str.strip() == "")).to_numpy()
            only_encoding = int((~agree & a_empty & b_empty).sum())
            note = (f"string comparison after strip; unequal rows={int((~agree).sum())}, of which {only_encoding} are the SAME "
                    f"missingness encoded differently (C1 CSV empty field -> NaN vs C9 parquet empty string); "
                    f"genuine value differences={int((~agree).sum()) - only_encoding}")'''
assert old in s
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AST OK")
