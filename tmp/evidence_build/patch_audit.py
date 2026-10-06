import pathlib
q = pathlib.Path('tmp/evidence_build/audit_registry_exactness.py')
s = q.read_text(encoding='utf-8')
old = "pathlib.Path('recovery/2026-09-24')]"
new = "pathlib.Path('recovery/2026-09-24'), pathlib.Path('evidence')]"
if old in s:
    s = s.replace(old, new)
    q.write_text(s, encoding='utf-8')
    print('corpus now includes evidence/')
else:
    print('already patched')
