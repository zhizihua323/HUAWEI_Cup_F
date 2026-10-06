import io, ast
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
s = io.open(p, encoding="utf-8").read()
old = '''    entries = write_manifest()
    print(f"[manifest] {len(entries)} artifacts listed in output_manifest.json", flush=True)'''
new = '''    # Written last and with no stdout/stderr activity afterwards, so that the captured
    # console log keeps exactly the byte content that output_manifest.json hashes.
    write_manifest()'''
assert old in s
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AST OK")
