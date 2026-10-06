import pathlib
p = pathlib.Path('evidence/mixture_evidence.md')
s = p.read_text(encoding='utf-8')
old = '（157 行 = 13 域 × 12 组 + …）'
new = '（157 行含表头，即 13 域 × 12 组 = 156 行）'
assert old in s
p.write_text(s.replace(old, new), encoding='utf-8')
print('patched')
