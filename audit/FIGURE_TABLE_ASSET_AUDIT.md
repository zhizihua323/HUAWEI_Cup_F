# FIGURE TABLE ASSET AUDIT

日期：2026-09-25。  
结论：**正式正文图0个，正式正文表0个（表格数据存在于Markdown和CSV，但未完成竞赛排版与验收）**。

## 1. 实际图像资产

| 资产 | 类型 | 状态 | 是否可用 | 源数据 |
|---|---|---|---|---|
| `solution/outputs/figures/mixture_baseline_diagnostics.png/.pdf/.svg` | 配比预测-实际诊断 | `EXISTING_NOT_FINAL` | 可复用但必须重绘/加限定 | `solution/outputs/mixture/aggregate_predictions.csv`、`metrics.csv` |
| `solution/outputs/scaling/scaling_fit_residuals.png/.pdf` | B1标度残差 | `EXISTING_NOT_FINAL` | 可复用但必须显示数据精度边界 | `B1_all_predictions.csv`、`residual_diagnostics.csv` |
| `solution/outputs/scaling/quality_direction_audit.png/.pdf` | B6/B7/B8方向冲突 | `DIAGNOSTIC_ONLY` | 只能在明确冲突标注下使用 | `quality_audit.json`、`quality_within_ND_slopes.csv` |
| `paper/` | 正文图 | 无 | 否 | 无 |
| `diagnostics/TASK-T05/T07/T08` | 正式run | 只有CSV/JSON/Parquet，无图形 | 数据具备，图未绘制 | 见下表 |

库存数字：8个PNG、1个SVG、7个PDF（含参考资料与三大项目图），但项目正式图仍是0。

## 2. 当前图表占位与缺口

- `FULL_MANUSCRIPT_V1.md` 有6个图占位。
- `FINAL_FIGURE_TABLE_PLAN.md` 建议7个正文图，缺图2、5、7中的部分已可通过现有T06/T07/T08绘制。
- `FULL_MANUSCRIPT_V1.md` 有19个Markdown表块，但17处含“表占位/待排版”字样。
- `figure_table_registry.md` 仍列大量`BLOCKED`，其中Q3/Q4的阻断条件已完成；该登记表已过期。

## 3. 正式表的源数据状态

| 建议表 | 内容 | 源文件 | 状态 |
|---|---|---|---|
| 表1 | 数据来源、单位、可信度 | `paper/data_sources.md`; `dataset_registry.csv` | 数据已有，待排版 |
| 表2 | Q1质量记录与分组 | Q01C `domain_summary.csv` | 数据已有，待排版 |
| 表3 | Q1配比/运输 | T06E-P `regmix_fixed_model_validation.csv`; `metrics.csv` | 数据已有 |
| 表4 | Q2 M0_B1参数与支持 | T06集成 `t07_parameter_table.csv` | 数据已有 |
| 表5 | Q2 G1–G4与资格 | T06E-B-R1 `corrected_gates`; `G1_G4_reconciliation.json` | 数据已有 |
| 表6 | Q3三档主结果 | T07 `budget_scenario_optima.csv` | 数据已有 |
| 表7 | Q3成本/KKT/边界 | T07 `budget_feasibility_proof.csv`; `kkt_boundary_checks.csv` | 数据已有 |
| 表8 | Q3 H/质量/配比/B8 | T07 `context_sensitivity.csv`; `quality_cost_sensitivity.csv` | 数据已有 |
| 表9 | Q4六任务基线/区间 | T08 `taskwise_progress.csv`; `t08_paper_interface.json` | 数据已有 |
| 表10 | Q4分解、时间外、不确定性 | T08 `scale_non_scale_decomposition.csv`; `forecast_uncertainty.csv` | 数据已有 |
| 附表A1 | 17×13 RegMix系数 | `solution/outputs/mixture/linear_coefficients.csv` | 数据已有 |
| 附表A2 | 源码/环境/AI披露 | 最终归档材料 | 待整理 |

## 4. 哪些图已有数据、只差绘制

| 图 | 缺什么 | 能否不补实验绘制 |
|---|---|---|
| 图1 四问证据流 | 绘图脚本 | 可以，数据来自冻结接口 |
| 图2 Q1质量/冲突/配比 | 扩展冲突表、正式主Q数据 | 部分可，扩展冲突冻结后完成 |
| 图3 Q2 M0_B1+B6+识别边界 | 绘图脚本 | 可以，T06/T06E-B-R1数据完整 |
| 图4 Q3三档N/D/Loss | 绘图脚本 | 可以，T07数据完整 |
| 图5 Q3 H敏感性 | 绘图脚本 | 可以，T07 `context_sensitivity.csv` |
| 图6 Q4桥接/六任务/未来资格 | 绘图脚本 | 可以画出“不可识别”状态，但若要求预测值，数据不足 |
| 图7 全文不确定性 | 绘图脚本 | 可以，T07/T08源数据完整 |

## 5. 哪些图若生成需要重新实验

- 需要新增未来12/24个月Benchmark数值预测的图：当前不能从T08补绘；需新增预注册benchmark空间建模和时间外验证。
- 需要扩展集冲突稳定性图的正式版本：可先只读Q01C现有Parquet，未必需要新实验。
- 需要B2/B4/B5外推验证图：需先完成冻结模型迁移审计。
- 需要真实质量文本标签图的图：A18核验未完成，不能先画成“已验证”。

## 6. 最终推荐

| 类别 | 推荐数量 | 说明 |
|---|---:|---|
| 正文图 | 7 | 图1–图7；优先级P0/P1 |
| 正文表 | 10 | 表1–表10；全部已有数据或冻结接口 |
| 附录图 | 4 | Q1质量诊断、B1残差/profile、T07情景draw、T08分层/不确定性 |
| 附录表 | 5 | RegMix系数、run registry、数据/哈希清单、依赖/环境、AI使用披露 |

正文图不得使用参考论文图片；附录图不得把B8/SCENARIO_ONLY画成已验证机制。
