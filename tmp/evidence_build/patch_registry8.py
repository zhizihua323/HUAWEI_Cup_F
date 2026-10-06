import pathlib
p = pathlib.Path('tmp/evidence_build/build_registry.py')
s = p.read_text(encoding='utf-8')

# SCL-29: point at the file that actually stores the percentiles
old29 = """    unit='dimensionless', artifact='solution/outputs/scaling/cluster_bootstrap_parameters.csv', source_table='B1',
    verification=V1, verification_method='本轮由 80 条保存重采样复算分位，与 scaling_params.json 一致（diff<=5.6e-17）',"""
new29 = """    unit='dimensionless', artifact='solution/outputs/scaling/scaling_params.json', source_table='B1',
    verification=V1, verification_method='本轮由 cluster_bootstrap_parameters.csv 的 80 条保存重采样复算分位，与 scaling_params.json 完全一致（diff=0.0）',"""
assert old29 in s
s = s.replace(old29, new29)

# SCL-39: point at the file that actually stores the RMSE
old39 = """    value=qa['B7_novel_grid_validation']['RMSE'], unit='cross-entropy',
    artifact='solution/outputs/scaling/B7_novel_grid_predicted_from_B6.csv', source_table='B7/B6', verification=V1,"""
new39 = """    value=_s(qa['B7_novel_grid_validation']['RMSE']), unit='cross-entropy',
    artifact='solution/outputs/scaling/quality_audit.json', source_table='B7/B6', verification=V1,"""
assert old39 in s
s = s.replace(old39, new39)

# SCL-35..37 k / RMSE come from quality_audit.json (already cited) but k is rendered by str(); make it exact
s = s.replace("""        value=f"{t['negative_group_slopes']}|{t['positive_group_slopes']}|{t['parameters']['k']}|{t['fit']['RMSE']}",""",
              """        value=f"{t['negative_group_slopes']}|{t['positive_group_slopes']}|{repr(t['parameters']['k'])}|{repr(t['fit']['RMSE'])}",""")
# SCL-38 overlap max diff uses float64 str(); make exact
s = s.replace("""    value=f"160|{qa['overlap'][1]['max_abs_difference']}", unit='键 | cross-entropy',""",
              """    value=f"160|{repr(qa['overlap'][1]['max_abs_difference'])}", unit='键 | cross-entropy',""")
# SCL-40 compound value already uses _s(); SCL-42 median uses _s()
p.write_text(s, encoding='utf-8')
print('patched SCL-29/35-39 traceability')
