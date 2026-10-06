import pathlib
p = pathlib.Path('tmp/evidence_build/build_registry.py')
s = p.read_text(encoding='utf-8')

anchor = "b9 = pd.read_csv(SCL / 'B9_compute_audit.csv', **RT)"
if 'VR = json.load' not in s:
    assert anchor in s
    s = s.replace(anchor, anchor + "\nVR = json.load(open('evidence/verification_record.json', encoding='utf-8'))")

old = """    metric='max_abs_error_X_beta_vs_saved_prediction', value=5.5067062021407764e-14, unit='val cross-entropy',
    artifact='solution/outputs/mixture/linear_coefficients.csv',
    source_table='A4-A15', verification=V1,
    verification_method='本轮用 normalized_mixtures x 导出系数 逐套复算 12 组预测',"""
new = """    metric='max_abs_error_X_beta_vs_saved_prediction',
    value=_s(VR['mixture_coefficients_reproduce_predictions']['max_abs_diff']), unit='val cross-entropy',
    artifact='evidence/verification_record.json',
    source_table='A4-A15', verification=V1,
    verification_method='本轮用 normalized_mixtures x 导出系数 逐套复算 12 组预测；结果落盘于 evidence/verification_record.json',"""
assert old in s, 'MIX-16 block not matched'
s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('patched MIX-16 + VR load')
