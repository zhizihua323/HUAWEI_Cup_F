# -*- coding: utf-8 -*-
"""Build evidence/baseline_result_registry.csv by READING saved artifacts only.
No model is fitted here; every numeric value is copied from an existing saved file.
"""
import json, csv, pathlib
import pandas as pd

OUT = pathlib.Path('evidence'); OUT.mkdir(exist_ok=True)
MIX = pathlib.Path('solution/outputs/mixture')
SCL = pathlib.Path('solution/outputs/scaling')

RT = dict(float_precision='round_trip')  # default 'high' parser can shift the last digits
met = pd.read_csv(MIX / 'metrics.csv', **RT)
def _s(x):
    """Full round-trip decimal text (pandas/numpy str() truncates to 16 sig digits)."""
    return repr(float(x))
def M(model, s, col):
    r = met[(met.model == model) & (met.set == s)]
    return _s(r[col].iloc[0])

mix_audit = {r['set']: r for r in json.load(open(MIX / 'audit.json', encoding='utf-8'))}
sp = json.load(open(SCL / 'scaling_params.json', encoding='utf-8'))
P = sp['parameters']
qa = json.load(open(SCL / 'quality_audit.json', encoding='utf-8'))
mc = pd.read_csv(SCL / 'model_comparison.csv', **RT)
def MC(cfg, col):
    return _s(mc[mc.configuration == cfg][col].iloc[0])
ev = pd.read_csv(SCL / 'external_validation.csv', **RT)
def EV(tag, col):
    return _s(ev[(ev.table == tag) & (ev.group == 'all')][col].iloc[0])
prec = json.load(open(SCL / 'B1_precision_residual_audit.json', encoding='utf-8'))
ci = json.load(open(MIX / 'test_1m_conditional_intervals.json', encoding='utf-8'))
otr = json.load(open(MIX / 'observed_training_reference.json', encoding='utf-8'))
qb6 = pd.read_csv(SCL / 'quality_B6_validation.csv', **RT)
b9 = pd.read_csv(SCL / 'B9_compute_audit.csv', **RT)
VR = json.load(open('evidence/verification_record.json', encoding='utf-8'))

V1 = 'V1_本轮复算'
V2 = 'V2_恢复轮核验'
V3 = 'V3_仅落盘记录'
V4 = 'V4_不可复算_需重拟合'
A = 'A_可用_附边界'
B = 'B_探索性'
C = 'C_仅内部参考'
D = 'D_禁止用于论文结论'

rows = []
def add(**k):
    rows.append(k)

# ---------------- mixture ----------------
add(result_id='MIX-01', module='mixture', item='线性模型 1M 独立检验（等权Loss RMSE）', config_or_model='linear',
    dataset='test_1m', data_nature='observed', split_role='independent_1m_test', n=256,
    metric='rmse_equal_domain_mean', value=M('linear','test_1m','rmse_equal_domain_mean'), unit='val cross-entropy',
    artifact='solution/outputs/mixture/metrics.csv', source_table='A6/A7',
    verification=V1, verification_method='本轮由 linear_test_1m_predictions.csv 复算，diff<=2.3e-16',
    claim_level=A, caveat='1M 配方与训练零重叠、未用于调参，是真正独立检验；但仍属同一 Pythia 语料/口径',
    interface='广义模型标定层可用此集作为唯一独立混合检验点')
add(result_id='MIX-02', module='mixture', item='线性模型 1M 独立检验（R2/秩相关）', config_or_model='linear',
    dataset='test_1m', data_nature='observed', split_role='independent_1m_test', n=256,
    metric='r2_equal_domain_mean|spearman_equal_domain_mean',
    value='0.3319216143105982|0.6250743877317463', unit='1 | 1',
    artifact='solution/outputs/mixture/metrics.csv', source_table='A6/A7',
    verification=V1, verification_method='本轮复算，diff<=2.3e-16',
    claim_level=A, caveat='为 13 域 Loss 先平均再算 R2/相关；与 pooled 口径不同（见 P06）',
    interface='排序指标须与绝对误差分开报告')
add(result_id='MIX-03', module='mixture', item='线性模型 60M 跨规模迁移（未重标定）', config_or_model='linear',
    dataset='test_60m', data_nature='observed', split_role='zero_shot_cross_scale', n=256,
    metric='rmse_equal_domain_mean|r2_equal_domain_mean|spearman_equal_domain_mean',
    value=f"{M('linear','test_60m','rmse_equal_domain_mean')}|{M('linear','test_60m','r2_equal_domain_mean')}|{M('linear','test_60m','spearman_equal_domain_mean')}",
    unit='val cross-entropy | 1 | 1',
    artifact='solution/outputs/mixture/metrics.csv', source_table='A8/A9',
    verification=V1, verification_method='本轮复算，diff<=1.5e-14',
    claim_level=B, caveat='RMSE 约 1.52（1M 为 0.227）约 6.7 倍；R2 为 -47；且该 256 条配方与 1M 检验配方字节完全相同，不是独立配方样本',
    interface='迁移层必须在跨规模上重标定；禁止把 B1 尺度的结论直接外推')
add(result_id='MIX-04', module='mixture', item='线性模型 1B 跨规模迁移（未重标定）', config_or_model='linear',
    dataset='test_1B', data_nature='observed', split_role='zero_shot_cross_scale', n=64,
    metric='rmse_equal_domain_mean|r2_equal_domain_mean|spearman_equal_domain_mean',
    value=f"{M('linear','test_1B','rmse_equal_domain_mean')}|{M('linear','test_1B','r2_equal_domain_mean')}|{M('linear','test_1B','spearman_equal_domain_mean')}",
    unit='val cross-entropy | 1 | 1',
    artifact='solution/outputs/mixture/metrics.csv', source_table='A10/A11',
    verification=V1, verification_method='本轮复算，diff<=4.5e-16',
    claim_level=C, caveat='1B 的 RMSE 比同口径常数基线（3.1195）更差，说明绝对损失迁移失败；不得表述为“模型在 1B 有效”',
    interface='进入广义模型前必须有可验证的跨规模标定层')
add(result_id='MIX-05', module='mixture', item='10B 估算材料对照', config_or_model='linear',
    dataset='est_10b', data_nature='estimated_loss_training_recipe_subset', split_role='external_estimate_comparison', n=63,
    metric='rmse_equal_domain_mean|spearman_equal_domain_mean',
    value=f"{M('linear','est_10b','rmse_equal_domain_mean')}|{M('linear','est_10b','spearman_equal_domain_mean')}",
    unit='val cross-entropy | 1', artifact='solution/outputs/mixture/metrics.csv', source_table='A12/A13',
    verification=V1, verification_method='本轮复算，diff<=4.6e-13',
    claim_level=D, caveat='Loss 为估算值，且 63 条配方全部来自训练集（重叠 63/63）；既非独立样本也非真值',
    interface='仅可与估算材料做一致性对照，不得作为验证证据')
add(result_id='MIX-06', module='mixture', item='70B 估算材料对照', config_or_model='linear',
    dataset='est_70b', data_nature='estimated_loss_training_recipe_subset', split_role='external_estimate_comparison', n=63,
    metric='rmse_equal_domain_mean|spearman_equal_domain_mean',
    value=f"{M('linear','est_70b','rmse_equal_domain_mean')}|{M('linear','est_70b','spearman_equal_domain_mean')}",
    unit='val cross-entropy | 1', artifact='solution/outputs/mixture/metrics.csv', source_table='A14/A15',
    verification=V1, verification_method='本轮复算，diff<=2.3e-13',
    claim_level=D, caveat='同 est_10b；秩相关为负（约 -0.52），与训练集重叠，不能证明大尺度配方排序能力',
    interface='仅作量级对照，禁止进入论文结论')
for lab, tag, cl, cav in [('test_1m','MIX-07',A,'常数基线只由训练响应拟合；1M 上线性优于该基线'),
                          ('test_60m','MIX-08',B,'60M 上线性仅比常数基线好 0.02，R2 均约 -47，绝对迁移实质失败'),
                          ('test_1B','MIX-09',C,'1B 上线性（3.1889）比常数基线（3.1195）更差'),
                          ('est_10b','MIX-10',C,'估算材料上线性亦不如常数基线'),
                          ('est_70b','MIX-11',C,'估算材料上线性亦不如常数基线')]:
    add(result_id=tag, module='mixture', item=f'常数参照基线 training_domain_means（{lab}）', config_or_model='training_domain_means',
        dataset=lab, data_nature='observed' if not lab.startswith('est') else 'estimated_loss_training_recipe_subset',
        split_role='reference_baseline', n=int(float(M('training_domain_means',lab,'n'))),
        metric='rmse_equal_domain_mean', value=M('training_domain_means',lab,'rmse_equal_domain_mean'),
        unit='val cross-entropy', artifact='solution/outputs/mixture/metrics.csv', source_table='A5',
        verification=V1, verification_method='常数由 train_1m 域均值给出，数值读取自 metrics.csv（未重拟合模型）',
        claim_level=cl, caveat=cav, interface='任何新模型必须同时报告该平凡基线')
add(result_id='MIX-12', module='mixture', item='训练内嵌套5折 OOF（族选择依据）', config_or_model='linear',
    dataset='train_nested_oof', data_nature='observed', split_role='nested_oof_training_only', n=512,
    metric='rmse_equal_domain_mean|r2_equal_domain_mean|spearman_equal_domain_mean',
    value=f"{M('linear','train_nested_oof','rmse_equal_domain_mean')}|{M('linear','train_nested_oof','r2_equal_domain_mean')}|{M('linear','train_nested_oof','spearman_equal_domain_mean')}",
    unit='val cross-entropy | 1 | 1', artifact='solution/outputs/mixture/metrics.csv', source_table='A4/A5',
    verification=V4, verification_method='无逐行 OOF 预测落盘，复算需重新拟合（本轮禁止）',
    claim_level=B, caveat='族内选择后 OOF 可能乐观；该数字不可独立复现',
    interface='后续须落盘 OOF 逐行预测，才能作为可复用选择证据')
add(result_id='MIX-13', module='mixture', item='族选择结果与惩罚参数', config_or_model='linear',
    dataset='train_1m', data_nature='observed', split_role='selection_record', n=512,
    metric='selected_family|ridge_alpha',
    value='linear|1.0', unit='- | -', artifact='solution/outputs/mixture/model.json', source_table='A4/A5',
    verification=V3, verification_method='model.json 记录 selected_by_training_only=linear；OOF 预测未落盘，选择过程无法复算',
    claim_level=B, caveat='族选择只用了训练数据；不得因二次族在测试集更好而改称训练选了二次',
    interface='选择规则与目标函数须随广义模型一并冻结并可复现')
add(result_id='MIX-14', module='mixture', item='二次族最终惩罚参数', config_or_model='quadratic',
    dataset='train_1m', data_nature='observed', split_role='model_parameter', n=512,
    metric='ridge_alpha', value=0.1, unit='-', artifact='solution/outputs/mixture/model.json', source_table='A4/A5',
    verification=V3, verification_method='model.json/all_fits 记录；未重拟合', claim_level=C,
    caveat='二次族未被选为主族，其测试表现属事后观察', interface='保留为对照族，不得事后替换主族')
add(result_id='MIX-15', module='mixture', item='二次族 1M 独立检验（事后观察）', config_or_model='quadratic',
    dataset='test_1m', data_nature='observed', split_role='independent_1m_test', n=256,
    metric='rmse_equal_domain_mean|spearman_equal_domain_mean',
    value=f"{M('quadratic','test_1m','rmse_equal_domain_mean')}|{M('quadratic','test_1m','spearman_equal_domain_mean')}",
    unit='val cross-entropy | 1', artifact='solution/outputs/mixture/metrics.csv', source_table='A6/A7',
    verification=V1, verification_method='本轮由 quadratic_test_1m_predictions.csv 复算',
    claim_level=B, caveat='该族在训练 OOF 上并不优于线性（pooled MSE 更大）；此表是事后观察，不能作为选型依据',
    interface='若论文改用二次族，必须重新走训练内选择并说明事后性')
add(result_id='MIX-16', module='mixture', item='导出系数可复现保存预测', config_or_model='linear+quadratic',
    dataset='6 sets', data_nature='mixed', split_role='reproducibility_check', n=1214,
    metric='max_abs_error_X_beta_vs_saved_prediction',
    value=_s(VR['mixture_coefficients_reproduce_predictions']['max_abs_diff']), unit='val cross-entropy',
    artifact='evidence/verification_record.json',
    source_table='A4-A15', verification=V1,
    verification_method='本轮用 normalized_mixtures x 导出系数 逐套复算 12 组预测；结果落盘于 evidence/verification_record.json',
    claim_level=A, caveat='只证明“系数×配比=保存预测”的算术一致，不证明模型正确',
    interface='系数矩阵是广义模型可调用的最小接口')
add(result_id='MIX-17', module='mixture', item='1M 检验条件自助区间（仅行抽样）', config_or_model='linear',
    dataset='test_1m', data_nature='observed', split_role='uncertainty_scenario', n=256,
    metric='rmse_equal_domain_mean_ci95|r2_ci95|spearman_ci95',
    value=f"{ci['lower'][0]}..{ci['upper'][0]}|{ci['lower'][1]}..{ci['upper'][1]}|{ci['lower'][2]}..{ci['upper'][2]}",
    unit='val cross-entropy | 1 | 1', artifact='solution/outputs/mixture/test_1m_conditional_intervals.json',
    source_table='A6/A7', verification=V3,
    verification_method='500 次行重采样的保存区间；本轮仅确认 mode/resamples/字段结构',
    claim_level=C, caveat='固定模型下的测试行抽样不确定性，不含族选择、质量映射、跨规模偏差；不是全流程置信区间',
    interface='不确定性口径须与模型选择不确定性分开声明')
add(result_id='MIX-18', module='mixture', item='结构性事实：1M 与 60M 检验配方完全相同', config_or_model='-',
    dataset='test_1m vs test_60m', data_nature='observed', split_role='design_fact', n=256,
    metric='sha256_p_mixture_equal', value='True (197267b7d6f15367e2f46c881e564c35b0d34e51b1754bb09d07e650cf8e1ce8)',
    unit='-', artifact='solution/outputs/mixture/audit.json', source_table='A6/A8', verification=V1,
    verification_method='本轮对原始 CSV 直接计算 SHA256，与 audit.json 记录一致',
    claim_level=A, caveat='60M 与 1M 不是两次独立配方抽样，只是同一配方在另一规模下的损失；不能当两个独立证据计数',
    interface='跨规模验证应设计为配方×规模的配对结构并据此做不确定性')
add(result_id='MIX-19', module='mixture', item='结构性事实：估算集配方全部来自训练集', config_or_model='-',
    dataset='est_10b vs est_70b vs train_1m', data_nature='training_subset', split_role='design_fact', n=63,
    metric='recipes_identical_to_training', value='63/63（两套估算集配方字节相同）', unit='-',
    artifact='solution/outputs/mixture/audit.json', source_table='A12/A14/A4', verification=V1,
    verification_method='本轮归一化后逐行比对，并校验两套估算配比文件 SHA256 相同（880c7ca1...）',
    claim_level=A, caveat='估算集在“配方”维度是训练内样本，其对照不构成样本外证据',
    interface='估算材料只能作为情景对照，须在广义模型中标明 in-sample 维度')
add(result_id='MIX-20', module='mixture', item='训练集观测最优行（描述性）', config_or_model='-',
    dataset='train_1m index=170', data_nature='observed', split_role='descriptive_reference', n=1,
    metric='mean_loss', value=otr['mean_loss'], unit='val cross-entropy',
    artifact='solution/outputs/mixture/observed_training_reference.json', source_table='A4-A7',
    verification=V3, verification_method='保存文件自带 role=descriptive_observed_training_best_not_global_optimum',
    claim_level=D, caveat='只是训练数据中观测均值最小的一行，不是全局最优，也不是独立检验结果',
    interface='若用于问三优化，须与优化解、约束可行性并列比较')
add(result_id='MIX-21', module='mixture', item='测试集与训练集配方重叠计数', config_or_model='-',
    dataset='test_1m/test_60m/test_1B', data_nature='observed', split_role='design_fact', n=576,
    metric='overlap_with_training', value='0/256|0/256|0/64', unit='-',
    artifact='solution/outputs/mixture/audit.json', source_table='A4/A6/A8/A10', verification=V1,
    verification_method='本轮归一化后逐行比对配方集合',
    claim_level=A, caveat='重叠为 0 只说明配方不同，不排除同域同分布或语料重复',
    interface='独立检验的前提条件之一，须在论文中显式声明')

# ---------------- scaling: B1 主拟合 ----------------
for i, (k, unit) in enumerate([('E','cross-entropy'),('A','cross-entropy'),('B','cross-entropy'),
                               ('alpha','dimensionless'),('beta','dimensionless')], start=22):
    add(result_id=f'SCL-{i:02d}-{k}', module='scaling', item=f'B1 主拟合参数 {k}', config_or_model='point__linear',
        dataset='B1 (1176 checkpoints)', data_nature='observed(标注真实轨迹)', split_role='main_fit_all_data', n=1176,
        metric=k, value=P[k], unit=unit, artifact='solution/outputs/scaling/scaling_params.json',
        source_table='B1', verification=V2,
        verification_method='恢复轮按保存公式复算 1176 条，max_error=8.9e-16；本轮核对 all_fits 与 scaling_params 一致（diff=0）',
        claim_level=B, caveat='参数建立在近乎确定性拟合上；来源与变换待核验，不能当独立发现的新规律',
        interface='广义模型的 N/D 主项参数即来源于此')
add(result_id='SCL-27', module='scaling', item='B1 拟合/留模型/时间外 RMSE', config_or_model='point__linear',
    dataset='B1', data_nature='observed(标注真实轨迹)', split_role='fit|leave_one_model_out|last_20pct_tokens', n=1176,
    metric='fit_RMSE|LOMO_RMSE|stage_RMSE',
    value=f"{MC('point__linear','fit_RMSE')}|{MC('point__linear','LOMO_RMSE')}|{MC('point__linear','stage_RMSE')}",
    unit='cross-entropy', artifact='solution/outputs/scaling/model_comparison.csv', source_table='B1',
    verification=V1, verification_method='本轮由 B1_all_predictions.csv 复算，LOMO/时间外 pooled RMSE 完全一致（diff<=8.8e-16）',
    claim_level=B, caveat='RMSE 约等于该表损失四位小数的 2.93 个半舍入单位；近乎严格幂律需追查来源，不等于泛化精度',
    interface='作为 L(N,D) 项拟合质量的上界提示，不可当作外推精度承诺')
add(result_id='SCL-28', module='scaling', item='B1 拟合异常贴合的数值尺度', config_or_model='point__linear',
    dataset='B1', data_nature='observed', split_role='precision_audit', n=1176,
    metric='rmse_in_loss_half_units|frac_abs_resid_le_half_unit', value=f"{prec['rmse_in_loss_rounding_half_units']}|{prec['fraction_abs_residual_le_loss_half_rounding_unit']}",
    unit='半舍入单位 | 比例', artifact='solution/outputs/scaling/B1_precision_residual_audit.json', source_table='B1',
    verification=V3, verification_method='读取保存审计；本轮未重算分位',
    claim_level=A, caveat='val_loss 仅 4 位小数（半单位 5e-5），D 仅 3 位小数（半单位 5e-3 B tokens），残差与数据精度同阶',
    interface='任何“拟合极好”的表述都必须附此精度说明')
add(result_id='SCL-29', module='scaling', item='参数自助分位（仅 8 个规模簇）', config_or_model='point__linear',
    dataset='B1', data_nature='observed', split_role='bootstrap_cluster_descriptive', n=80,
    metric='alpha_p2.5|alpha_median|alpha_p97.5',
    value=f"{sp['bootstrap_percentiles']['alpha']['p2_5']}|{sp['bootstrap_percentiles']['alpha']['median']}|{sp['bootstrap_percentiles']['alpha']['p97_5']}",
    unit='dimensionless', artifact='solution/outputs/scaling/scaling_params.json', source_table='B1',
    verification=V1, verification_method='本轮由 cluster_bootstrap_parameters.csv 的 80 条保存重采样复算分位，与 scaling_params.json 完全一致（diff=0.0）',
    claim_level=C, caveat='只有 8 个轨迹簇，区间是条件稳定性描述，不能当总体置信区间',
    interface='不确定性须与来源标定、结构选择分别表述')
# ---------------- scaling: 外部材料 ----------------
for tag, rid, cl, cav in [('B2','SCL-30',C,'半合成、族外情景；偏离呈近似恒定水平差，说明绝对损失口径不可直接比较'),
                          ('B3','SCL-31',D,'由 B1 检查点插值而来，非独立证据，不得计入验证'),
                          ('B4','SCL-32',C,'真实公开跨族收敛点，但分词器/验证语料/绝对损失口径不一致'),
                          ('B5','SCL-33',C,'文献整理数据，绝对损失口径未统一'),
                          ('B10','SCL-34',D,'Loss 为模型估算值，不能用于证明外推准确')]:
    add(result_id=rid, module='scaling', item=f'{tag} 外部材料对照', config_or_model='point__linear',
        dataset=tag, data_nature={'B2':'semisynthetic','B3':'interpolated','B4':'published_observed','B5':'published_observed','B10':'estimated'}[tag],
        split_role='external_comparison_no_recalibration', n=int(float(EV(tag,'n'))),
        metric='RMSE|bias_pred_minus_actual', value=f"{EV(tag,'RMSE')}|{EV(tag,'bias_pred_minus_actual')}",
        unit='cross-entropy', artifact='solution/outputs/scaling/external_validation.csv', source_table=tag,
        verification=V1, verification_method='本轮由对应 *_predictions.csv 复算 all 组指标，与保存表一致',
        claim_level=cl, caveat=cav, interface='外部迁移必须分层标定；B4/B5 只能用于形态对照')
# ---------------- scaling: 质量方向 ----------------
for tag, rid, slides, cl, cav in [('B6','SCL-35',-1,B,'45/45 组斜率为负；k 未触界，作为当前情景 k 的来源'),
                                  ('B7','SCL-36',-1,B,'与 B6 完全重复 360 点，仅新增 90 个 Q 网格点；不得当独立重复实验'),
                                  ('B8','SCL-37',1,D,'150/150 组斜率为正，方向与 B6/B7 相反；E 与 k 触界、条件数约 1.08e7，不适合提供问三参数')]:
    t = qa['table_results'][tag]
    add(result_id=rid, module='scaling', item=f'{tag} 质量方向与拟合', config_or_model='quality_scenario_fit',
        dataset=tag, data_nature='semisynthetic', split_role='separate_table_analysis_no_pooling', n=t['fit']['n'],
        metric='groups_neg|groups_pos|k|RMSE',
        value=f"{t['negative_group_slopes']}|{t['positive_group_slopes']}|{repr(t['parameters']['k'])}|{repr(t['fit']['RMSE'])}",
        unit='组 | 组 | 无量纲 | cross-entropy', artifact='solution/outputs/scaling/quality_audit.json',
        source_table=tag, verification=V1,
        verification_method='本轮由 quality_within_ND_slopes.csv 复核 45/45/150 组方向，与保存审计一致',
        claim_level=cl, caveat=cav, interface='Q 方向与大小在进入广义模型前必须解决该冲突并保留敏感性')
add(result_id='SCL-38', module='scaling', item='B6 与 B8 在共同网格上的冲突', config_or_model='overlap_audit',
    dataset='B6 vs B8', data_nature='semisynthetic', split_role='conflict_evidence', n=160,
    metric='matching_keys|max_abs_difference',
    value=f"160|{repr(qa['overlap'][1]['max_abs_difference'])}", unit='键 | cross-entropy',
    artifact='solution/outputs/scaling/quality_audit.json', source_table='B6/B8', verification=V2,
    verification_method='恢复轮复核 360/160/224 交集与最大差；本轮读取一致',
    claim_level=C, caveat='160 个 NDQ 键上两表 Loss 不同（最大差 2.5769），来源差异未知，不能合并或取平均',
    interface='广义模型需对来源分层或引入来源偏移项')
add(result_id='SCL-39', module='scaling', item='B7 新增 Q 网格点插值检验（B6 参数）', config_or_model='quality_scenario_fit',
    dataset='B7 novel 90 points', data_nature='semisynthetic', split_role='same_source_interpolation', n=90,
    metric='RMSE',
    value=_s(qa['B7_novel_grid_validation']['RMSE']), unit='cross-entropy',
    artifact='solution/outputs/scaling/quality_audit.json', source_table='B7/B6', verification=V1,
    verification_method='本轮用 B6 保存参数复算该 90 点 RMSE，与保存值一致',
    claim_level=C, caveat='与训练同源半合成，不能升级为经验验证', interface='仅作情景稳健性检查')
add(result_id='SCL-40', module='scaling', item='B6 质量外推（训练 Q<=0.6 预测 Q>0.6）', config_or_model='quality_scenario_fit',
    dataset='B6', data_nature='semisynthetic', split_role='within_table_extrapolation', n=135,
    metric='RMSE|bias_pred_minus_actual',
    value=f"{_s(qb6[qb6.split=='Q_train_le_0.6_test_gt_0.6'].RMSE.iloc[0])}|{_s(qb6[qb6.split=='Q_train_le_0.6_test_gt_0.6'].bias_pred_minus_actual.iloc[0])}",
    unit='cross-entropy', artifact='solution/outputs/scaling/quality_B6_validation.csv', source_table='B6',
    verification=V3, verification_method='读取保存结果；本轮未重拟合 B6',
    claim_level=C, caveat='高 Q 段误差与正偏差都明显放大（RMSE 0.0956），Q 外推不可靠',
    interface='Q 可行域边界与不确定性须在问三显式约束')
add(result_id='SCL-41', module='scaling', item='质量迁移情景状态', config_or_model='quality_scenario',
    dataset='B1 + B6 k', data_nature='semisynthetic', split_role='unvalidated_scenario', n=1176,
    metric='status|k|Q_ref', value=f"{sp['quality_scenario_status']}|{sp['quality_scenario']['k']}|{sp['quality_scenario']['Q_ref']}",
    unit='- | 无量纲 | 无量纲', artifact='solution/outputs/scaling/scaling_params.json', source_table='B1/B6',
    verification=V3, verification_method='保存文件自带状态标记；本轮核对与 quality_audit 一致',
    claim_level=D, caveat='A 评分与 B 的 Q_score 无实证标定、Q_ref=0.5 为情景锚点、p 未接入；不得称已完成 Q 标定',
    interface='必须保留 k=0 与映射敏感性分析，作为广义模型的情景分支')
_r = b9.ratio_reported_to_6ND.replace([float('inf')], pd.NA).dropna()
add(result_id='SCL-42', module='scaling', item='B9 大模型元数据计算量口径差异', config_or_model='-',
    dataset='B9', data_nature='reported_metadata', split_role='metadata_coverage_check', n=132,
    metric='ratio_reported_to_6ND_median|n_ratio_lt_0.5|n_ratio_gt_2|n_no_D',
    value=f"{_s(_r.median())}|{int((_r < 0.5).sum())}|{int((_r > 2).sum())}|{int((b9.D_tokens_B == 0).sum())}",
    unit='比值 | 行 | 行 | 行', artifact='solution/outputs/scaling/B9_compute_audit.csv', source_table='B9',
    verification=V3, verification_method='读取保存审计（含 15 个缺失单元格、11 行无报告 FLOPs）',
    claim_level=C, caveat='中位数约 1 但分布两极分化：44/121 低于 0.5、12/121 高于 2，个别行口径明显异常，不能强行改写为 6ND',
    interface='成本约束建模须显式声明采用哪套 FLOPs 口径')
add(result_id='SCL-43', module='scaling', item='广义律 L(N,D,Q,p) 尚未形成', config_or_model='-',
    dataset='-', data_nature='gap', split_role='gap', n=0, metric='missing_components',
    value='p 未接入缩放模型；Q 为未标定情景；无跨来源标定；无独立最终测试集', unit='-',
    artifact='solution/outputs/scaling/scaling_params.json', source_table='-', verification=V3,
    verification_method='由 not_included/limitations 字段与本轮核对确认',
    claim_level=D, caveat='当前只有 L(N,D) 主拟合 + 未验证 Q 情景，不能表述为已建立 L(N,D,Q,p)',
    interface='进入问三前必须补齐 p 映射、Q 标定与来源分层')
# ---------------- cross-module gaps ----------------
for rid, item, val, cl, cav in [('GAP-01','A 质量与 B 的 Q_score 无配对实证标定','identity mapping uncalibrated',D,'D07/D12：域映射与共线性问题未解决'),
                                ('GAP-02','配比 p 尚未进入缩放律','p not in scaling model',D,'配比模块与缩放模块目前是两条独立证据链'),
                                ('GAP-03','问三联合优化未实现','no solver / no budget scenarios',D,'现有参数只能作为候选接口')]:
    add(result_id=rid, module='cross', item=item, config_or_model='-', dataset='-', data_nature='gap', split_role='gap', n=0,
        metric='status', value=val, unit='-', artifact='02_DECISIONS.md;04_TASK_QUEUE.md', source_table='-',
        verification=V2, verification_method='由既有决定文档与本轮核对确认', claim_level=cl, caveat=cav,
        interface='广义模型/问三的前置条件')

cols = ['result_id','module','item','config_or_model','dataset','data_nature','split_role','n','metric','value','unit',
        'artifact','source_table','verification','verification_method','claim_level','caveat','interface']
with open(OUT/'baseline_result_registry.csv','w',newline='',encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in rows:
        assert set(r) == set(cols), (r.get('result_id'), set(cols) ^ set(r))
        w.writerow(r)
print('rows written:', len(rows))
print('mixture rows:', sum(1 for r in rows if r['module']=='mixture'))
print('scaling rows:', sum(1 for r in rows if r['module']=='scaling'))
print('cross rows:', sum(1 for r in rows if r['module']=='cross'))
