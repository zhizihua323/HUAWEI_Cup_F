from pathlib import Path
p = Path(__file__).resolve().parent / '_apply_patches.py'
t = p.read_text(encoding='utf-8-sig')
old = "rep('P2_trigger_group_column',\n'''    'would_Q_be_nan',\n    'would_Q_nan_trigger_features', 'q_nan_trigger_features',''',\n'''    'would_Q_be_nan',\n    'would_Q_nan_trigger_features', 'q_nan_trigger_features', 'would_Q_nan_trigger_groups',''')"
new = "rep('P2_trigger_group_column',\n'''    'would_Q_nan_trigger_features', 'q_nan_trigger_features',\n    'quality_fingerprint',''',\n'''    'would_Q_nan_trigger_features', 'q_nan_trigger_features', 'would_Q_nan_trigger_groups',\n    'quality_fingerprint',''')"
assert t.count(old) == 1, t.count(old)
p.write_text(t.replace(old, new), encoding='utf-8-sig')
print('patcher fixed')
