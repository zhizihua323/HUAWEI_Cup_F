# 问题三图表占位符与编号清单

> 生成日期：2026-09-25。T07正式证据目录：diagnostics/TASK-T07/20260925T113744+08/。
>
> 状态：READY表示源数据已冻结且正文已写；PLANNED表示尚需排版或绘图；BLOCKED表示未有结果。所有质量与配比图/表必须保留SCENARIO_ONLY标注。

## 1. 图占位符

| 内部编号 | 暂定图号 | 图题建议 | 目标章节 | 源文件 | 状态 | 禁止事项 |
|---|---:|---|---|---|---|---|
| FIG-Q3-01 | 图Q3-1 | 三档预算下的N_B、D_B与Loss变化 | 7.15 | budget_scenario_optima.csv；t08_or_paper_interface.json | READY | 不称唯一全局最优；标明1e22 D上界 |
| FIG-Q3-02 | 图Q3-2 | 主结果KKT残差、活跃边界与预算位置 | 7.14—7.15 | kkt_boundary_checks.csv；budget_feasibility_proof.csv | READY | 不把数值内点粉饰成无边界 |
| FIG-Q3-03 | 图Q3-3 | H敏感性：训练主导与注意力主导 | 7.16 | context_sensitivity.csv；structural_transition_diagnostics.csv | READY | “结构转移”只按活跃约束/弹性排序解释，不写物理相变 |
| FIG-Q3-04 | 图Q3-4 | 三类质量成本S01/S03情景比较 | 7.17 | quality_cost_sensitivity.csv | PLANNED，SCENARIO_ONLY | 不把G_EXP写成真实或最好成本函数 |
| FIG-Q3-05 | 图Q3-5 | 配比运输情景与B8冲突状态 | 7.18—7.19 | budget_scenario_optima.csv；transport_failure_sensitivity.csv | PLANNED，SCENARIO_ONLY | 不命名“方案135”；不把S16写成反向最优策略 |
| FIG-Q3-06 | 图Q3-6 | 主结果参数draw分布与Loss区间 | 7.20 | parameter_draw_optima.parquet；uncertainty_summary.csv | PLANNED | 不把条件draw写成联合后验 |
| FIG-Q4-01 | 图Q4-1 | Loss—Benchmark桥接与未来前沿 | Q4 | 待T08冻结结果 | BLOCKED | Q4占位，不得用T07替代 |

## 2. 表占位符

| 内部编号 | 暂定表号 | 表题建议 | 目标章节 | 源文件 | 状态 | 禁止事项 |
|---|---:|---|---|---|---|---|
| TAB-Q3-01 | 表Q3-1 | 三档正式主结果 | 7.15 | budget_scenario_optima.csv | READY | 必须保留1e22 D上界说明 |
| TAB-Q3-02 | 表Q3-2 | 成本分项、Lagrange乘子与KKT | 7.15 | budget_scenario_optima.csv；kkt_boundary_checks.csv | READY | 预算残差与数值容差须同时说明 |
| TAB-Q3-03 | 表Q3-3 | 上下文H敏感性全表 | 7.16 | context_sensitivity.csv | READY | 不把离散H结果外推为连续函数 |
| TAB-Q3-04 | 表Q3-4 | S03三类质量成本情景 | 7.17 | quality_cost_sensitivity.csv | READY，SCENARIO_ONLY | 不选真实/最好成本函数 |
| TAB-Q3-05 | 表Q3-5 | 配比运输情景 | 7.18 | budget_scenario_optima.csv | READY，SCENARIO_ONLY | 不称普适最优配方 |
| TAB-Q3-06 | 表Q3-6 | 参数不确定性 | 7.20 | uncertainty_summary.csv | READY | 不写成联合后验或情景概率 |
| TAB-Q3-07 | 表Q3-7 | 模型限制与禁用解释 | 7.22 | paper/T07_RESULT_FREEZE.md | READY | 保留B8冲突和Q/p不可联合优化 |
| TAB-Q4-01 | 表Q4-1 | 问题四桥接与能力预测 | Q4 | 待T08冻结结果 | BLOCKED | Q4占位 |

## 3. 关键写作规则

1. 主表数字必须以paper/T07_RESULT_FREEZE.md和budget_scenario_optima.csv为准。
2. 所有质量、配比和跨源结果必须写SCENARIO_ONLY。
3. 1e22的D_B=299.893是B1支持上界，必须标明边界。
4. G_EXP、G_POWER、G_LOG仅作假设比较，不能写真实或最优。
5. S17为NO_NUMERIC_OPTIMUM，不得转写为反向最优策略。
6. 参数draw是条件稳定性描述，不是联合后验或概率情景。
7. Q4内容继续保留占位符，T07不代替T08。
