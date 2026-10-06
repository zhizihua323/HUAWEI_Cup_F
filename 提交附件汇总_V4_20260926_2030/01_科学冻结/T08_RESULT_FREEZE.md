# T08 问题四结果冻结接口

日期：2026-09-25。资格：TASK-T08主控最终验收通过并关闭。本文件是论文问题四的唯一正式结果口径；正式证据目录为`diagnostics/TASK-T08/20260925T142203+0800/`。

## 【问题四正式资格】

- benchmark bridge：`CONDITIONAL_ASSOCIATION_ONLY`
- time trend：`UNVALIDATED_FOR_EXTRAPOLATION`
- future progress：`NOT_IDENTIFIABLE_PROGRESS`
- benchmark未来输出：`CONDITIONAL_BASELINE_ONLY`

现有数据支持条件关联和历史描述，不支持统一Loss→Benchmark预测桥接、因果技术进步分解或经过验证的时间外推。

## 【forecast origin】

预测原点为`2025-03-13`，来自通过身份和日期审计的C1/C2/C8记录最大观测日期，并由C8最大有效评测时间戳同日复核。

- 12个月情景时点：`2026-03-13`
- 24个月情景时点：`2027-03-13`

二者均是相对最后观测日期2025-03-13的12/24个月情景时点，不是相对系统当前日期。

## 【benchmark主结果】

正式主可比层包含7个C5 High/Pythia模型。六个任务及辅助均值的冻结候选均为`CONSTANT`。条件基线和区间为：

| benchmark | 常数基线/点 | 条件区间/点 | 角色 |
|---|---:|---:|---|
| IFEval | 22.165078 | [18.533524, 26.172209] | 正式任务向量 |
| BBH | 30.840380 | [29.197147, 32.272010] | 正式任务向量 |
| MATH Lvl 5 | 1.068192 | [0.345274, 1.747950] | 正式任务向量 |
| GPQA | 25.491371 | [24.646453, 26.300336] | 正式任务向量 |
| MUSR | 36.451247 | [32.974301, 39.625850] | 正式任务向量 |
| MMLU-PRO | 11.284195 | [11.045743, 11.501670] | 正式任务向量 |
| 六任务均值 | 21.216744 | [20.737287, 21.656458] | 仅辅助汇总 |

这些区间是冻结主层常数模型的条件区间，不是可迁移的未来预测区间。

## 【规模/非规模分解】

正式定义为：

`scale_associated_component = m_t(x_i)-m_t(x_ref)`

`conditional_remainder = observed-m_t(x_i)`

由于正式benchmark模型对全部任务均为常数，49条模型×目标记录的`scale_associated_component`严格等于0，且`observed=fitted+conditional_remainder`的最大独立复算误差为`3.55e-15`。

这表示现有主可比样本不足以支持benchmark空间中的规模预测项，不表示规模对模型能力没有作用。`conditional_remainder`只能称“条件剩余项”或“非规模关联残差”，不能解释为算法、工程或因果技术进步。

## 【Loss空间】

`M0_B1`缩放规律继续单独适用于其B1来源支持域，条件情景固定为`S00_NULL_M0_B1`、`H=2048`。它与benchmark空间严格分开。

历史compute增长识别数据只有7条观测N/D记录、1个模型族、6个相邻候选区间和1个有效族级区间；未达到至少3个独立模型族和10个有效族级区间的冻结门槛。因此没有生成12/24个月的N、D、compute或Loss数值，Loss→benchmark数值转换次数为0。

## 【未来预测】

保守、基准、积极三种年化对数增长率均为`NOT_IDENTIFIABLE`。三种情景在12个月和24个月时点的benchmark增量均为`NOT_IDENTIFIABLE_PROGRESS`。

允许报告冻结的`CONDITIONAL_BASELINE_ONLY`，但不得把常数基线写成未来能力点预测。时间外推状态固定为`UNVALIDATED`。

## 【不确定性】

以下六类不确定性分别报告，不合成为单一置信区间：

1. `scaling_parameter`
2. `bridge_model_error`
3. `benchmark_conditional_association`
4. `model_family_heterogeneity`
5. `time_extrapolation`
6. `scenario_structure`

## 【主要限制】

- 主可比层只有7个Pythia模型；
- 主层只有一个模型族；
- 时间外验证未通过；
- 没有可靠留模型族验证；
- 没有主层大规模外验证；
- 历史compute增长支持不足；
- C6 Medium的38条D保持缺失，不能补入正式规模模型；
- 4个损坏JSON不赋分，6个partial只用于实际有效任务。

## 【论文禁止表述】

不得写：

- “规模对benchmark贡献为零”；
- “非规模残差就是算法进步”；
- “预测未来12/24个月benchmark会达到某数值”；
- “Loss下降可以转换成benchmark提升”；
- “时间趋势已被验证”；
- “未来compute增长率已经估计出来”。

正式run的独立verifier为32/32 PASS；内部检查无FAIL；output manifest 38/38当前匹配；8项源码与snapshot逐文件一致。

