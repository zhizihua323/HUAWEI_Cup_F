import pathlib
p = pathlib.Path('tmp/evidence_build/build_registry.py')
s = p.read_text(encoding='utf-8')
pairs = [
 ("met = pd.read_csv(MIX / 'metrics.csv')", "RT = dict(float_precision='round_trip')  # default 'high' parser can shift the last digits\nmet = pd.read_csv(MIX / 'metrics.csv', **RT)"),
 ("mc = pd.read_csv(SCL / 'model_comparison.csv')", "mc = pd.read_csv(SCL / 'model_comparison.csv', **RT)"),
 ("ev = pd.read_csv(SCL / 'external_validation.csv')", "ev = pd.read_csv(SCL / 'external_validation.csv', **RT)"),
 ("qb6 = pd.read_csv(SCL / 'quality_B6_validation.csv')", "qb6 = pd.read_csv(SCL / 'quality_B6_validation.csv', **RT)"),
 ("b9 = pd.read_csv(SCL / 'B9_compute_audit.csv')", "b9 = pd.read_csv(SCL / 'B9_compute_audit.csv', **RT)"),
]
for old, new in pairs:
    assert old in s, old
    s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('patched round_trip parsing')
