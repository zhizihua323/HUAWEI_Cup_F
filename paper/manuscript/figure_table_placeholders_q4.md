# 问题四图表占位符与编号清单

> Q4唯一冻结接口：paper/T05_RESULT_FREEZE.md、paper/T08_RESULT_FREEZE.md。正式证据目录：diagnostics/TASK-T05/20260925T113355+0800/、diagnostics/TASK-T08/20260925T142203+0800/。
>
> 所有Benchmark未来输出为CONDITIONAL_BASELINE_ONLY；未来进展为NOT_IDENTIFIABLE_PROGRESS。不得出现未来Benchmark增量、N、D、Loss或compute的伪数值。

## 1. 图占位符

| 内部编号 | 暂定图号 | 图题建议 | 目标章节 | 源文件 | 状态 | 禁止事项 |
|---|---:|---|---|---|---|---|
| FIG-Q4-01 | 图Q4-1 | Loss–Benchmark可识别性判断流程 | 7.2 | T05 identifiability_decision.json；T05 aggregate_bridge_results.csv | READY | 不画未选中的SIZE/LOSS预测曲线 |
| FIG-Q4-02 | 图Q4-2 | 六任务常数基线与条件区间 | 7.3 | T08 taskwise_progress.csv；T08 t08_paper_interface.json | READY | 六任务不能压缩为均值；区间不是未来预测区间 |
| FIG-Q4-03 | 图Q4-3 | 规模关联项与非规模关联残差分解 | 7.4—7.5 | T08 scale_non_scale_decomposition.csv | READY | 0项只表示主可比样本不足；不写成规模无效 |
| FIG-Q4-04 | 图Q4-4 | 历史分层、样本分母与时间外状态 | 7.6—7.7 | T08 historical_strata_summary.csv；leakage_audit.csv；T05 split_registry.csv | PLANNED | 样本不足层不得合并或补值 |
| FIG-Q4-05 | 图Q4-5 | 12/24个月情景时点与NOT_IDENTIFIABLE状态 | 7.8—7.9 | T08 forecast_12m_24m_scenarios.csv；loss_space_scale_scenarios.csv | READY | 不生成未来数值点或区间 |
| FIG-Q4-06 | 图Q4-6 | 六类不确定性分层 | 7.10 | T08 forecast_uncertainty.csv | READY | 不合成单一置信区间 |
| FIG-Q4-07 | 图Q4-7 | Loss空间与Benchmark空间分离 | 7.9 | T08 t08_paper_interface.json；loss_space_scale_scenarios.csv | READY | Loss↔Benchmark转换次数为0 |

## 2. 表占位符

| 内部编号 | 暂定表号 | 表题建议 | 目标章节 | 源文件 | 状态 | 禁止事项 |
|---|---:|---|---|---|---|---|
| TAB-Q4-01 | 表Q4-1 | 六任务CONSTANT条件基线与条件区间 | 7.3 | T08 taskwise_progress.csv；T05 aggregate_bridge_results.csv | READY | 均值只作辅助 |
| TAB-Q4-02 | 表Q4-2 | Loss–Benchmark识别资格与样本边界 | 7.2 | T05 run_summary.json；identifiability_decision.json | READY | 不称可靠统一预测桥 |
| TAB-Q4-03 | 表Q4-3 | 规模/非规模分解定义与残差 | 7.4—7.5 | T08 scale_non_scale_decomposition.csv | READY | 残差不得写为机制或因果进步 |
| TAB-Q4-04 | 表Q4-4 | 历史分层与有效分母 | 7.6 | historical_strata_summary.csv；missingness_and_denominators.csv | READY | 样本不足层标INSUFFICIENT_N |
| TAB-Q4-05 | 表Q4-5 | 时间外验证与12/24月情景资格 | 7.7—7.8 | T05 t08_bridge_contract.json；T08 forecast_12m_24m_scenarios.csv | READY | 时间为情景时点，不是系统当下相对日期 |
| TAB-Q4-06 | 表Q4-6 | 六类不确定性 | 7.10 | forecast_uncertainty.csv | READY | 不合成单一区间 |
| TAB-Q4-07 | 表Q4-7 | Loss空间规模情景 | 7.9 | loss_space_scale_scenarios.csv | READY | 增长率NOT_IDENTIFIABLE，不生成N/D/Loss |

## 3. 关键写作规则

1. benchmark bridge固定为CONDITIONAL_ASSOCIATION_ONLY。
2. time trend固定为UNVALIDATED_FOR_EXTRAPOLATION。
3. future progress固定为NOT_IDENTIFIABLE_PROGRESS。
4. forecast origin为2025-03-13；12/24个月时点分别为2026-03-13和2027-03-13。
5. IFEval、BBH、MATH Lvl 5、GPQA、MUSR、MMLU-PRO分别报告；benchmark_mean_aux仅辅助。
6. 主benchmark模型为CONSTANT；规模关联项等于0，只表示主可比样本支持不足。
7. conditional_remainder只能称条件剩余项或非规模关联残差。
8. 不生成未来N、D、compute、Loss或Benchmark增量数值。
