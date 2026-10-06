import io
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
src = io.open(p, encoding="utf-8").read()
n0 = len(src)
fixes = [
 ("f\"- 其中文件名尾部不含闭合 `}` 或错误位置在文件末端 95% 之后的计为“疑似截断”：",
  "f\"- 其中文件名尾部不含闭合花括号或错误位置在文件末端 95% 之后的计为“疑似截断”："),
 ("Every number written by this script comes from the actual run below.\nOriginal attachments are opened read-only through extended-length (\\\\?\\\\) paths.",
  "Every number written by this script comes from the actual run below.\nOriginal attachments are opened read-only through extended-length paths."),
]
for old, new in fixes:
    if old in src:
        src = src.replace(old, new, 1)
        print("fixed:", old[:50])
    else:
        print("NOTE not found (maybe already ok):", old[:50])
io.open(p, "w", encoding="utf-8").write(src)
print("size", n0, "->", len(src))
# also scan for remaining raw braces inside f-strings heuristically
import ast
try:
    ast.parse(src)
    print("AST OK")
except SyntaxError as e:
    print("STILL BROKEN:", e.lineno, e.msg)
    print(src.splitlines()[e.lineno-1])
