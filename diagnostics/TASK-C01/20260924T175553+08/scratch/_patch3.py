import io, ast
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
s = io.open(p, encoding="utf-8").read()
lines = s.splitlines(True)
for i, ln in enumerate(lines):
    if ln.startswith("Original attachments are opened read-only"):
        lines[i] = "Original attachments are opened read-only through Windows extended-length paths.\n"
        print("replaced line", i + 1)
s = "".join(lines)
io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AST OK")
