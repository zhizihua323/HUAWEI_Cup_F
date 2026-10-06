from pathlib import Path
p = Path(__file__).resolve().parent / 'diagnose_missingness.py'
t = p.read_text(encoding='utf-8-sig')
anchor = """if not (RUN_DIR.parent.name == 'TASK-Q01A' and RUN_DIR.parent.parent.name == 'diagnostics'):
    raise SystemExit('run directory layout unexpected: ' + str(RUN_DIR))"""
assert t.count(anchor) == 1
if 'RUN_ID = RUN_DIR.name' not in t:
    t = t.replace(anchor, anchor + "\nRUN_ID = RUN_DIR.name", 1)
p.write_text(t, encoding='utf-8-sig')
print('RUN_ID defined for new run dir:', p.parent.name)
