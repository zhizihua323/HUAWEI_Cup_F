from pathlib import Path
p = Path(__file__).resolve().parent / 'diagnose_missingness.py'
t = p.read_text(encoding='utf-8-sig')
old = """         'mismatch_features': [f for f in FEATURES if event_nan[f] != expected_nan[f]][:5]},"""
new = """         'mismatch_features': [f for f in FEATURES if event_nan.get(f) != expected_nan.get(f, 0)][:5]},"""
assert t.count(old) == 1, t.count(old)
p.write_text(t.replace(old, new), encoding='utf-8-sig')
print('C32 guard patched')
