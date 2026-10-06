# 最终图表资产索引

状态：`SCIENCE_CLOSED`。本目录仅包含表达层资产；未重拟合、未改阈值、未重新筛选模型、未裁剪负值。

## 核心图（7 幅）

| 编号 | 标题 | 问题 | 图型 | 资格 | 交付 |
|---|---|---|---|---|---|
| FIG-01 | 四问建模主线与证据资格闭环 | 总体 | 结构图 | `PREFLIGHT_FRAMEWORK` | [fig01_framework.png](fig01_framework.png) · [fig01_framework.svg](fig01_framework.svg) · [fig01_framework.pdf](fig01_framework.pdf) · [fig01_framework_caption.md](fig01_framework_caption.md) · [fig01_framework_source_map.json](fig01_framework_source_map.json) |
| FIG-02 | Q1 质量构造、扩展稳定性与人工盲审 | Q1 | 非对称混合图 | `PARTIALLY_STABLE; DESCRIPTIVE_MANUAL_VALIDATION` | [fig02_q1_quality_validation.png](fig02_q1_quality_validation.png) · [fig02_q1_quality_validation.svg](fig02_q1_quality_validation.svg) · [fig02_q1_quality_validation.pdf](fig02_q1_quality_validation.pdf) · [fig02_q1_quality_validation_caption.md](fig02_q1_quality_validation_caption.md) · [fig02_q1_quality_validation_source_map.json](fig02_q1_quality_validation_source_map.json) |
| FIG-03 | Q1 RegMix 配比预测及跨尺度运输 | Q1 | 定量网格 | `SAME_SCALE_TEST; TRANSPORT_ONLY` | [fig03_q1_regmix_transport.png](fig03_q1_regmix_transport.png) · [fig03_q1_regmix_transport.svg](fig03_q1_regmix_transport.svg) · [fig03_q1_regmix_transport.pdf](fig03_q1_regmix_transport.pdf) · [fig03_q1_regmix_transport_caption.md](fig03_q1_regmix_transport_caption.md) · [fig03_q1_regmix_transport_source_map.json](fig03_q1_regmix_transport_source_map.json) |
| FIG-04 | Q2 B1 来源内拟合与分来源外部验证资格 | Q2 | 定量网格 | `SOURCE_INTERNAL; VALIDATION_FAILED/SUPPORTED; OOS_ONLY` | [fig04_q2_fit_validation.png](fig04_q2_fit_validation.png) · [fig04_q2_fit_validation.svg](fig04_q2_fit_validation.svg) · [fig04_q2_fit_validation.pdf](fig04_q2_fit_validation.pdf) · [fig04_q2_fit_validation_caption.md](fig04_q2_fit_validation_caption.md) · [fig04_q2_fit_validation_source_map.json](fig04_q2_fit_validation_source_map.json) |
| FIG-05 | Q3 三档预算冻结支持域内条件最优 | Q3 | 定量网格 | `CONDITIONAL_OPTIMUM` | [fig05_q3_budget_optima.png](fig05_q3_budget_optima.png) · [fig05_q3_budget_optima.svg](fig05_q3_budget_optima.svg) · [fig05_q3_budget_optima.pdf](fig05_q3_budget_optima.pdf) · [fig05_q3_budget_optima_caption.md](fig05_q3_budget_optima_caption.md) · [fig05_q3_budget_optima_source_map.json](fig05_q3_budget_optima_source_map.json) |
| FIG-06 | Q4 六任务及辅助均值的 12/24 月三情景 | Q4 | 定量网格 | `SCENARIO_ONLY_UNVALIDATED` | [fig06_q4_scenarios.png](fig06_q4_scenarios.png) · [fig06_q4_scenarios.svg](fig06_q4_scenarios.svg) · [fig06_q4_scenarios.pdf](fig06_q4_scenarios.pdf) · [fig06_q4_scenarios_caption.md](fig06_q4_scenarios_caption.md) · [fig06_q4_scenarios_source_map.json](fig06_q4_scenarios_source_map.json) |
| FIG-07 | 全文结果资格与解释边界 | 总体 | 资格矩阵 | `SCIENCE_CLOSED` | [fig07_qualification_map.png](fig07_qualification_map.png) · [fig07_qualification_map.svg](fig07_qualification_map.svg) · [fig07_qualification_map.pdf](fig07_qualification_map.pdf) · [fig07_qualification_map_caption.md](fig07_qualification_map_caption.md) · [fig07_qualification_map_source_map.json](fig07_qualification_map_source_map.json) |

每幅图的独立入口脚本为 `generate_fig01.py` 至 `generate_fig07.py`；共享绘图实现位于 `build_final_figures.py`。FIG-02、FIG-04、FIG-06 分别优先落实最终补丁合同中图 2、图 4、图 7 的强制重做要求。

## 核心表（9 张）

| 编号 | 标题 | 问题 | 资格 | 交付 |
|---|---|---|---|---|
| TAB-01 | 四问结果接口与最终资格 | 总体 | `SCIENCE_CLOSED` | [table01_overview.csv](../final_tables/table01_overview.csv) · [table01_overview.docx](../final_tables/table01_overview.docx) · [table01_overview_caption.md](../final_tables/table01_overview_caption.md) · [table01_overview_source_map.json](../final_tables/table01_overview_source_map.json) |
| TAB-02 | Q1 质量代理构造与主分母 | Q1 | `OPERATIONAL_PROXY` | [table02_q1_quality_definition.csv](../final_tables/table02_q1_quality_definition.csv) · [table02_q1_quality_definition.docx](../final_tables/table02_q1_quality_definition.docx) · [table02_q1_quality_definition_caption.md](../final_tables/table02_q1_quality_definition_caption.md) · [table02_q1_quality_definition_source_map.json](../final_tables/table02_q1_quality_definition_source_map.json) |
| TAB-03 | Q1 扩展稳定性与作者盲审 | Q1 | `PARTIALLY_STABLE; PAIRWISE_COMPLETE` | [table03_q1_extension_manual.csv](../final_tables/table03_q1_extension_manual.csv) · [table03_q1_extension_manual.docx](../final_tables/table03_q1_extension_manual.docx) · [table03_q1_extension_manual_caption.md](../final_tables/table03_q1_extension_manual_caption.md) · [table03_q1_extension_manual_source_map.json](../final_tables/table03_q1_extension_manual_source_map.json) |
| TAB-04 | Q1 RegMix 同尺度检验与跨尺度运输 | Q1 | `SAME_SCALE_TEST; TRANSPORT_ONLY` | [table04_q1_regmix_transport.csv](../final_tables/table04_q1_regmix_transport.csv) · [table04_q1_regmix_transport.docx](../final_tables/table04_q1_regmix_transport.docx) · [table04_q1_regmix_transport_caption.md](../final_tables/table04_q1_regmix_transport_caption.md) · [table04_q1_regmix_transport_source_map.json](../final_tables/table04_q1_regmix_transport_source_map.json) |
| TAB-05 | Q2 M0 B1 参数与经验支持框 | Q2 | `IDENTIFIED_SOURCE_CONDITIONAL` | [table05_q2_parameters_support.csv](../final_tables/table05_q2_parameters_support.csv) · [table05_q2_parameters_support.docx](../final_tables/table05_q2_parameters_support.docx) · [table05_q2_parameters_support_caption.md](../final_tables/table05_q2_parameters_support_caption.md) · [table05_q2_parameters_support_source_map.json](../final_tables/table05_q2_parameters_support_source_map.json) |
| TAB-06 | Q2 分来源验证结果与资格 | Q2 | `SOURCE_SPECIFIC_QUALIFICATION` | [table06_q2_validation.csv](../final_tables/table06_q2_validation.csv) · [table06_q2_validation.docx](../final_tables/table06_q2_validation.docx) · [table06_q2_validation_caption.md](../final_tables/table06_q2_validation_caption.md) · [table06_q2_validation_source_map.json](../final_tables/table06_q2_validation_source_map.json) |
| TAB-07 | Q3 三档预算正式主结果 | Q3 | `CONDITIONAL_OPTIMUM` | [table07_q3_budget_optima.csv](../final_tables/table07_q3_budget_optima.csv) · [table07_q3_budget_optima.docx](../final_tables/table07_q3_budget_optima.docx) · [table07_q3_budget_optima_caption.md](../final_tables/table07_q3_budget_optima_caption.md) · [table07_q3_budget_optima_source_map.json](../final_tables/table07_q3_budget_optima_source_map.json) |
| TAB-08 | Q4 选中贡献模型与端点分解 | Q4 | `NOT_DEFINED_SHARES; M2_GATE_FAILED` | [table08_q4_models_contributions.csv](../final_tables/table08_q4_models_contributions.csv) · [table08_q4_models_contributions.docx](../final_tables/table08_q4_models_contributions.docx) · [table08_q4_models_contributions_caption.md](../final_tables/table08_q4_models_contributions_caption.md) · [table08_q4_models_contributions_source_map.json](../final_tables/table08_q4_models_contributions_source_map.json) |
| TAB-09 | Q4 十二和二十四个月三情景 | Q4 | `SCENARIO_ONLY_UNVALIDATED` | [table09_q4_scenarios.csv](../final_tables/table09_q4_scenarios.csv) · [table09_q4_scenarios.docx](../final_tables/table09_q4_scenarios.docx) · [table09_q4_scenarios_caption.md](../final_tables/table09_q4_scenarios_caption.md) · [table09_q4_scenarios_source_map.json](../final_tables/table09_q4_scenarios_source_map.json) |

表格构建脚本为 `paper/final_tables/build_final_tables.py`。TAB-03、TAB-06、TAB-09 分别落实最终补丁合同中表 3、表 6、表 9 的强制替换要求。

## 统一规范

- 图宽 182.9 mm，PNG 为 600 dpi，同时交付保留可编辑文字的 SVG 和 PDF。
- 中文字体优先 Microsoft YaHei；颜色以低饱和蓝、青、玫红和灰为主，并用线型、标记与网纹确保黑白打印仍可区分。
- Q4 主预测保留原始负值；所有未来数值醒目标注 `SCENARIO_ONLY_UNVALIDATED`。
- 每项资产均有独立 caption、source map 和最小源数据；统一映射见 `figure_table_source_map.csv`。
