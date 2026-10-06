# PAPER V1 核心Claim–Evidence审计

> 生成日期：2026-09-25。审计对象：paper/manuscript/FULL_MANUSCRIPT_V1.md。
>
> 来源优先级：paper/FINAL_RESULT_INDEX.md指定的T06、T07、T05、T08冻结接口；Q1的细粒度计数沿用已验收Q1稳定正文。未从旧run或聊天记录挑选新数字。

## 1. 核心Claim

| claim | section | value | source_freeze_file | qualification | status |
|---|---|---|---|---|---|
| Q1主质量采用11特征与三组等权 | 4.1—4.2 | 11特征；组内/组间等权 | Q1_Q2_STABLE_BODY.md | 正式Q_baseline | 已验收稳定正文 |
| Q1物理记录与唯一键 | 4.4 | 272505物理记录；261086唯一键；11419重复 | Q1_Q2_STABLE_BODY.md | 操作性质量分母 | 已验收稳定正文 |
| Q1主质量完整案例 | 4.4 | 261067有效；19缺失；覆盖率0.9999272270439625 | Q1_Q2_STABLE_BODY.md；T08未复用该分母 | 严格完整案例 | 已验收稳定正文 |
| Q1质量锚点 | 5.5 | q_A*=0.5695341857475174 | T06_RESULT_FREEZE.md | A侧描述统计，不是A/B映射参数 | 冻结 |
| Q1配比同尺度结果 | 4.6 | 1M MSE改善0.5502593290；Spearman=0.6250743877 | T06_RESULT_FREEZE.md | 1M同尺度 | 冻结 |
| Q1跨尺度配比运输 | 4.6 | 60M RMSE=1.5173310792；1B RMSE=3.1889453478 | T06_RESULT_FREEZE.md | 运输诊断，不重校准 | 冻结 |
| Q2主模型参数 | 5.2 | E=1.6897975629820348; A_N=0.3539803206065571; B_D=1.2403055835426349; α_N=0.339976581941082; β_D=0.2798781285468448 | T06_RESULT_FREEZE.md | B1来源内条件关系 | 冻结 |
| Q2B6质量系数 | 5.3 | k_add=0.3544081081063713 | T06_RESULT_FREEZE.md | B6来源内，0.1≤Q_score≤0.6 | 冻结 |
| Q2G1 | 5.4 | 43/45组负方向 | T06_RESULT_FREEZE.md | B6来源内方向门槛 | 冻结 |
| Q2G2 | 5.4 | leave-N RMSE 0.0791587→0.0529372，改善33.13%；leave-D 0.0818619→0.0553288，改善32.41% | T06_RESULT_FREEZE.md | 来源内留组验证 | 冻结 |
| Q2G3 | 5.4 | 200/200成功且方向一致 | T06_RESULT_FREEZE.md | 条件重采样稳定性 | 冻结 |
| Q2G4 | 5.4 | 6/6满秩；条件数53.94407500777401；profile有限分离 | T06_RESULT_FREEZE.md | 数值可识别性 | 冻结 |
| Q2A/B桥接 | 5.5 | NOT_IDENTIFIABLE | T06_RESULT_FREEZE.md | 无统一点估计 | 冻结 |
| Q2质量与配比共线 | 5.7 | 设计秩与加入Q_mix后秩均为17 | T06_RESULT_FREEZE.md | Q与完整p不能独立寻优 | 冻结 |
| Q3三档主结果 | 6.6 | 1e18:(0.078248576,1.993850677,3.553996156); 1e20:(0.625922700,24.925757775,2.609142026); 1e22:(5.202388053,299.893000000,2.143211279) | T07_RESULT_FREEZE.md | 冻结M0_B1、H=2048、Q/p不优化的条件最优 | 冻结 |
| Q31e22边界 | 6.6 | D_B=299.893000000为B1支持上界 | T07_RESULT_FREEZE.md | 边界解，不外推 | 冻结 |
| Q3KKT与可行性 | 6.6 | 最大相对预算越界9.403629568e−13；最大KKT残差2.7932317030401693e−8；等式残差9.403629568e−13 | T07_RESULT_FREEZE.md | 未通过clip或扩域修正 | 冻结 |
| Q3H临界 | 6.7 | H_crit=30000 | T07_RESULT_FREEZE.md | η=2e−4 | 冻结 |
| Q3质量成本 | 6.8 | 三类G函数均未识别为真实成本；S03在1e20/1e22选择Q=0.6但配置不同 | T07_RESULT_FREEZE.md | SCENARIO_ONLY | 冻结 |
| Q3配比运输 | 6.9 | S14/S15 Δp=−0.694347；S16 Δp=0.353477 | T07_RESULT_FREEZE.md | SCENARIO_ONLY | 冻结 |
| Q3B8 | 6.10 | S17三预算均NO_NUMERIC_OPTIMUM | T07_RESULT_FREEZE.md | 冲突证据 | 冻结 |
| Q3参数不确定性 | 6.11 | 80个B1整行draw；三档Loss条件分位见正文 | T07_RESULT_FREEZE.md | 条件描述，不设联合后验 | 冻结 |
| Q3质量情景不确定性 | 6.11 | S01/S03使用200个B1/B6条件整行组合 | T07_RESULT_FREEZE.md | NOT_JOINT_POSTERIOR | 冻结 |
| Q4桥接资格 | 7.2 | CONDITIONAL_ASSOCIATION_ONLY | T05_RESULT_FREEZE.md | 不是可识别统一预测桥 | 冻结 |
| Q4桥接样本 | 7.2 | 1854完整C8；6 partial；4损坏；45桥接模型；7主层；38迁移层 | T05_RESULT_FREEZE.md | 主层与迁移层分开 | 冻结 |
| Q4主Benchmark模型 | 7.3 | 六个任务及辅助均值均为CONSTANT | T05_RESULT_FREEZE.md；T08_RESULT_FREEZE.md | 条件基线 | 冻结 |
| Q4六任务基线 | 7.3 | 见表Q4-1 | T08_RESULT_FREEZE.md | 六任务向量；辅助均值仅辅助 | 冻结 |
| Q4规模关联项 | 7.4 | 49条记录严格为0 | T08_RESULT_FREEZE.md | 仅表示样本不足以支持Benchmark空间规模预测项 | 冻结 |
| Q4分解误差 | 7.5 | observed=fitted+conditional_remainder最大误差3.55e−15 | T08_RESULT_FREEZE.md | 非规模关联残差/条件剩余项 | 冻结 |
| Q4时间外 | 7.7 | 2024-09-01切点，5训练/2测试，未通过 | T05_RESULT_FREEZE.md | UNVALIDATED_FOR_EXTRAPOLATION | 冻结 |
| Q4预测原点 | 7.8 | 2025-03-13 | T08_RESULT_FREEZE.md | 最后观测日期 | 冻结 |
| Q4情景时点 | 7.8 | 12个月=2026-03-13；24个月=2027-03-13 | T08_RESULT_FREEZE.md | 相对预测原点，不是当前日期 | 冻结 |
| Q4未来进展 | 7.8—7.9 | 三种增长率均NOT_IDENTIFIABLE；Benchmark增量均NOT_IDENTIFIABLE_PROGRESS | T08_RESULT_FREEZE.md | 不生成未来数值 | 冻结 |
| Q4Loss空间 | 7.9 | 7条N/D记录、1族、6候选区间、1有效族级区间 | T08_RESULT_FREEZE.md | 支持不足，Loss→Benchmark转换次数0 | 冻结 |
| Q4六类不确定性 | 7.10 | scaling_parameter; bridge_model_error; benchmark_conditional_association; model_family_heterogeneity; time_extrapolation; scenario_structure | T08_RESULT_FREEZE.md | 分开报告，不合成单一区间 | 冻结 |
| 全文Q/p联合边界 | 5.7；6.1 | Q与完整p不独立优化 | T06_RESULT_FREEZE.md；T07_RESULT_FREEZE.md | 正式主模型默认关闭 | 冻结 |

## 2. 禁用表述扫描

扫描对象：FULL_MANUSCRIPT_V1.md。规则：不机械替换；若出现于明确的限界否定陈述，保留并在表中说明；若形成肯定结论，必须改写或删除。

| 搜索词 | 命中数 | 命中位置/上下文 | 判断 |
|---|---:|---|---|
| 因果 | 4 | 问题一冲突解释、问题二质量条件边界；均为“不赋予/不能替代因果解释” | 允许的限界否定，不作肯定主张 |
| 证明 | 7 | 外推、映射、冲突与条件最优边界；均为“不能证明/不构成证明” | 允许的限界否定 |
| 普适 | 0 | — | 无 |
| 唯一最优 | 0 | — | 无 |
| 预测未来 | 0 | — | 无 |
| 规模贡献为零 | 0 | — | 无 |
| 算法进步 | 0 | — | 无 |
| 工程进步 | 0 | — | 无 |
| 质量一定提高 | 0 | — | 无 |
| 已标定 | 0 | — | 无 |
| 跨规模验证 | 1 | 4.6说明1M结果不能写成跨规模验证 | 允许的限界否定 |
| 准确预测 | 0 | — | 无 |

## 3. 审计结论

- 核心数字均能回溯到T06、T07、T05、T08冻结接口，或已验收的Q1稳定正文。
- 未从旧run、superseded结果或口头汇报补入新数字。
- Q4六任务向量未被均值替代，未来输出未生成N、D、Loss或Benchmark增量。
- 全文保留A侧Q_baseline与B侧Q_score的尺度区分，保留十亿变量与物理成本变量的单位区分。
- 在正式排版前仍需完成：图1—图7绘制，表1—表10排版，参考文献核验与模板格式检查。
