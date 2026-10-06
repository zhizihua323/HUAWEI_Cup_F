# PAPER V1 核心图表规划

> 生成日期：2026-09-25。原则：只保留直接支撑结论的图表；诊断图下放附录。所有质量、配比和跨源结果必须保留SCENARIO_ONLY或对应资格标签。
>
> 图表编号按正文首次出现顺序规划；最终排版时再冻结。

## 1. 核心图

| 图号 | 优先级 | 图题 | 正文位置 | 数据来源 | 状态 |
|---:|---|---|---|---|---|
| 图1 | P0 | 四问建模主线与证据分层框架 | 第2章 | paper/FINAL_RESULT_INDEX.md；四份T06/T07/T05/T08冻结接口 | 待绘制 |
| 图2 | P0 | 问题一：质量处理、冲突诊断与同尺度配比 | 第4章 | Q01C正式科学run；T03E冻结验证；T06 RegMix运输审计 | 待绘制，复用已有配比诊断并重作 |
| 图3 | P0 | 问题二：M0_B1缩放主模型、B6来源内质量关系与识别边界 | 第5章 | T06_RESULT_FREEZE.md；T06集成参数与G1—G4 | 待绘制 |
| 图4 | P0 | 问题三：三档预算的条件最优N_B、D_B与Loss | 第6章 | T07 budget_scenario_optima.csv；T07_RESULT_FREEZE.md | 待绘制 |
| 图5 | P1 | 问题三：H敏感性与活跃边界变化 | 第6章 | T07 context_sensitivity.csv；structural_transition_diagnostics.csv | 待绘制 |
| 图6 | P0 | 问题四：桥接识别、六任务条件基线与未来资格 | 第7章 | T05 identifiability_decision.json；T08 taskwise_progress.csv；forecast_12m_24m_scenarios.csv | 待绘制 |
| 图7 | P1 | 全文不确定性分层 | 第7—8章 | T07 uncertainty_summary.csv；T08 forecast_uncertainty.csv；T05 verification.json | 待绘制 |

## 2. 核心表

| 表号 | 优先级 | 表题 | 正文位置 | 数据来源 | 状态 |
|---:|---|---|---|---|---|
| 表1 | P0 | 数据来源、单位与统一符号 | 第3章 | paper/data_sources.md；Q01C数据清单；T06/T07单位接口；T05/T08样本接口 | 正文表已写，待排版 |
| 表2 | P0 | 问题一质量评价与配比结果 | 第4章 | Q01C audit/domain_summary；T03E holdout；T06 RegMix | 正文表已写，待排版 |
| 表3 | P0 | 问题二M0_B1参数与来源支持 | 第5章 | T06 t07_parameter_table.csv；t07_model_contract.json | 正文表已写，待排版 |
| 表4 | P0 | 问题二来源内质量G1—G4与跨源资格 | 第5章 | T06 corrected_gates/G1_G4_reconciliation.json；P分支identifiability矩阵 | 正文表已写，待排版 |
| 表5 | P0 | 问题三三档预算正式主结果 | 第6章 | T07 budget_scenario_optima.csv；T07_RESULT_FREEZE.md | 正文表已写，待排版 |
| 表6 | P0 | 问题三成本分项、预算可行性与KKT | 第6章 | T07 budget_scenario_optima.csv；kkt_boundary_checks.csv；verification.json | 正文表已写，待排版 |
| 表7 | P1 | 问题三H敏感性全表 | 第6章/附录 | T07 context_sensitivity.csv | 正文表已写，待排版 |
| 表8 | P1 | 问题三质量成本、配比运输与B8冲突情景 | 第6章/附录 | T07 quality_cost_sensitivity.csv；budget_scenario_optima.csv | 正文表已写，待排版 |
| 表9 | P0 | 问题四六任务条件基线与条件区间 | 第7章 | T08 taskwise_progress.csv；t08_paper_interface.json | 正文表已写，待排版 |
| 表10 | P0 | 问题四规模/非规模分解、时间外与六类不确定性 | 第7章 | T08 scale_non_scale_decomposition.csv；forecast_uncertainty.csv；T05 t08_bridge_contract.json | 正文表已写，待排版 |
| 附表A1 | P2 | RegMix 17×13系数矩阵 | 附录 | solution/outputs/mixture/linear_coefficients.csv | 待排版 |
| 附表A2 | P2 | 复现实验、源码版本与AI使用记录 | 附录 | 最终归档与AI披露材料 | 待整理 |

## 3. 下放到附录或删除的图表

- 质量问题诊断的逐字段相关性图、缺失模式图、扩展分层图：仅作附录诊断。
- RegMix完整逐域残差、全部多起点轨迹：不进入正文。
- B1/B6逐参数profile日志：仅在需要解释G4时放附录。
- T07所有21情景×预算×H的完整表：正文只保留主表和关键敏感性，其余入复现附件。
- T08 931行历史分层表：正文只保留分层规则和代表性的有效分母摘要。
- 六类不确定性的原始draw分布图：正文保留汇总，详细分布入附录。

## 4. 缺口清单

- 图1—图7均需实际绘图或重绘。
- 表1—表10需统一编号、单位、字体和表注。
- 图4、图6必须有支持域/识别边界标注。
- 所有SCENARIO_ONLY结果在图注中保留限定词。
- 参考文献和正式引用待人工核验后填入。
