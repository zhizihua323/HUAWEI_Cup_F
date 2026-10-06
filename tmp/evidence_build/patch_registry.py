import re, pathlib
p = pathlib.Path('tmp/evidence_build/build_registry.py')
s = p.read_text(encoding='utf-8')

s = s.replace("dataset='6 sets', data_nature='mixed', split_role='reproducibility_check', n=1214,",
              "dataset='6 sets', data_nature='mixed', split_role='reproducibility_check', n=1214,")

old = """add(result_id='SCL-42', module='scaling', item='B9 大模型元数据计算量口径差异', config_or_model='-',
    dataset='B9', data_nature='reported_metadata', split_role='metadata_coverage_check', n=132,
    metric='ratio_reported_to_6ND_range',
    value=f"{float(b9.ratio_reported_to_6ND.min())}..{float(b9.ratio_reported_to_6ND.max())}",
    unit='比值', artifact='solution/outputs/scaling/B9_compute_audit.csv', source_table='B9', verification=V3,
    verification_method='读取保存审计（含 15 个缺失单元格）',
    claim_level=C, caveat='比值跨度大，反映激活参数/训练过程/公开估计口径差异，不能强行改写为 6ND',
    interface='成本约束建模须显式声明采用哪套 FLOPs 口径')"""
new = """_r = b9.ratio_reported_to_6ND.replace([float('inf')], pd.NA).dropna()
add(result_id='SCL-42', module='scaling', item='B9 大模型元数据计算量口径差异', config_or_model='-',
    dataset='B9', data_nature='reported_metadata', split_role='metadata_coverage_check', n=132,
    metric='ratio_reported_to_6ND_median|n_ratio_lt_0.5|n_ratio_gt_2|n_no_D',
    value=f"{float(_r.median())}|{int((_r < 0.5).sum())}|{int((_r > 2).sum())}|{int((b9.D_tokens_B == 0).sum())}",
    unit='比值 | 行 | 行 | 行', artifact='solution/outputs/scaling/B9_compute_audit.csv', source_table='B9',
    verification=V3, verification_method='读取保存审计（含 15 个缺失单元格、11 行无报告 FLOPs）',
    claim_level=C, caveat='中位数约 1 但分布两极分化：44/121 低于 0.5、12/121 高于 2，个别行口径明显异常，不能强行改写为 6ND',
    interface='成本约束建模须显式声明采用哪套 FLOPs 口径')"""
assert old in s
s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('patched')
