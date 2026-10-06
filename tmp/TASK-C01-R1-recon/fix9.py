import io
vp = r"tmp\TASK-C01-R1-staging\verify_c01_repairs.py"
s = io.open(vp, encoding="utf-8").read()
old = '''    import tokenize as _tok
'''
new = '''    import ast as _ast
    import tokenize as _tok
'''
assert old in s
s = s.replace(old, new, 1)
# the later duplicate import is harmless but remove it for clarity
s = s.replace('''    import ast as _ast
    imported_modules = []''', '''    imported_modules = []''', 1)
io.open(vp, "w", encoding="utf-8").write(s)
print("import order fixed")
