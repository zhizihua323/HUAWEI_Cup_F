# Q1/Q2 图表占位符与编号清单

> 生成日期：2026-09-25。用途：维护问题一、问题二稳定正文的图表占位符。
>
> 状态含义：READY表示正文可直接使用；PLANNED表示源数据已冻结但图/表资产尚未生成；EXISTING_NOT_FINAL表示已有旧图，但版式和结论边界未重新验收；BLOCKED表示缺少T07/T05结果。

## 1. 图占位符

| 内部编号 | 暂定图号 | 图题建议 | 目标章节 | 源文件 | 状态 | 禁止事项 |
|---|---:|---|---|---|---|---|
| FIG-GEN-01 | 图1 | 四问建模与证据分层框架 | 2 | paper/outline.md；paper/T06_RESULT_FREEZE.md | PLANNED | 不画未完成的Q3/Q4结果 |
| FIG-Q1-01 | 图2 | 质量指标方向统一、缺失传播与三组聚合流程 | 6.1—6.2 | solution/outputs/quality_q01c/20260924T215718+08/code_snapshot/quality_q01c.py；normalization.json | PLANNED | 不把Q_C画成正式主结果 |
| FIG-Q1-02 | 图3 | 领域质量分布与三组分歧诊断 | 6.4 | quality_features_scores.parquet；domain_summary.csv | PLANNED | 不把组间分歧解释为错误率 |
| FIG-Q1-03 | 图4 | RegMix同尺度预测与跨尺度误差 | 6.6 | regmix_fixed_model_validation.csv；mixture_transport_audit.csv | EXISTING_NOT_FINAL | 10B/70B必须标估算；不得画成跨规模验证通过 |
| FIG-Q2-01 | 图5 | B1经典标度律拟合与残差 | 7.2 | solution/outputs/scaling/B1_all_predictions.csv；residual_diagnostics.csv | EXISTING_NOT_FINAL | 不把近零训练误差写成泛化精度 |
| FIG-Q2-02 | 图6 | B6质量方向、留组误差与k_add profile | 7.3—7.4 | corrected_profiles/；G1_G4_reconciliation.json | PLANNED | 不把B6来源内关系外推为统一质量效应 |
| FIG-Q2-03 | 图7 | A/B桥接不可识别、H0—H4情景与B8冲突 | 7.5—7.8 | t07_model_contract.json；quality_bridge_scenarios.json；G1_G4_reconciliation.json | PLANNED | H1—H3不得标成估计映射；B8不得标成机制反转 |
| FIG-Q3-01 | 图8 | 预算—情景—配置结构图 | Q3 | 待T07 | BLOCKED | 无结果不得填充 |
| FIG-Q4-01 | 图9 | Loss—Benchmark桥接与能力前沿 | Q4 | 待T05/后续预测 | BLOCKED | 无结果不得填充 |

## 2. 表占位符

| 内部编号 | 暂定表号 | 表题建议 | 目标章节 | 源文件 | 状态 | 禁止事项 |
|---|---:|---|---|---|---|---|
| TAB-SYM-01 | 表1 | 统一符号、单位与解释状态 | 5 | paper/manuscript/Q1_Q2_STABLE_BODY.md | READY | 不把情景符号写成参数 |
| TAB-DATA-01 | 表2 | A/B/C数据来源、性质与适用范围 | 3 | paper/data_sources.md；dataset_registry.csv | READY，需压缩排版 | 不把semisynthetic/interpolated/estimated写成observational truth |
| TAB-Q1-01 | 表3 | 质量记录、唯一键、缺失与覆盖率 | 6.4 | solution/outputs/quality_q01c/20260924T215718+08/audit.json；domain_summary.csv | READY | 不以物理记录数冒充主Q有效分母 |
| TAB-Q1-02 | 表4 | 三组质量均值、分歧与高分歧比例 | 6.4 | domain_summary.csv，scope=all_unique,domain=ALL | READY | 不把等权规则写成最优规则 |
| TAB-Q1-03 | 表5 | Q_C规则敏感性留出稳定性 | 6.5 | T03E phase_b_frozen_validation/holdout_summary.json | READY | 不把Q_C写成正式质量分；扩展未测试须保留 |
| TAB-Q1-04 | 表6 | RegMix同尺度与跨尺度运输结果 | 6.6 | regmix_fixed_model_validation.csv | READY | 60M/1B非重校准；10B/70B非真值 |
| TAB-Q2-01 | 表7 | M0_B1参数、条件区间与支持范围 | 7.2 | t07_parameter_table.csv；t07_model_contract.json | READY | 条件百分位不写成全面置信区间 |
| TAB-Q2-02 | 表8 | MQ-add参数与来源范围 | 7.3 | t07_parameter_table.csv | READY | 不写成统一质量效应 |
| TAB-Q2-03 | 表9 | MQ-add的G1—G4验收 | 7.4 | corrected_gates/G1_G4_reconciliation.json | READY | 不隐藏来源内资格 |
| TAB-Q2-04 | 表10 | 结论类型、可解释范围与禁止外推 | 8.4 | paper/T06_RESULT_FREEZE.md；t07_model_contract.json | READY | 不把情景或冲突写成已识别统一结论 |
| TAB-Q2-05 | 表11 | A/B桥接与Q-p识别状态 | 7.5、7.7 | quality_bridge_scenarios.json；p_q_identifiability.json | READY | 不给H1—H3点估计；不将Q与p作为独立坐标 |
| TAB-Q3-01 | 表12 | 预算×情景配置与结构转移 | Q3 | 待T07 | BLOCKED | 无结果不得填充 |
| TAB-Q4-01 | 表13 | 规模/非规模贡献与未来前沿 | Q4 | 待T05及后续 | BLOCKED | 无结果不得填充 |
| TAB-Q1-05 | 附表A1 | 17×13线性Scheffé系数矩阵 | 附录 | solution/outputs/mixture/linear_coefficients.csv | READY | 仅作首轮冻结配比模型系数，不声称跨尺度验证 |

## 3. 编号冻结规则

1. 当前表号是按拟定正文顺序预留，不代表最终PDF编号。
2. 图/表状态必须先变为READY，才能进入最终论文。
3. 每个图/表中的数值必须能在source_map_q1_q2.md或paper/T06_RESULT_FREEZE.md中定位。
4. Q1/Q2正文中的“占位符”条目在最终排版前统一替换为真实图/表或删除空槽。
5. 不允许为了补足图号而插入未运行的Q3/Q4结果。
