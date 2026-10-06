# 图表编号、来源与状态清单

> 建立时间：2026-09-24。本表只管理论文图表，不产生图形或结果。
>
> 编号分两层：稳定内部 ID 用于协作与追踪；`预留正文号`用于当前章节顺序。最终 PDF 冻结前可整体重排，但一旦正文引用即不得随意改号。
>
> 任何图表中的数字必须先在 `paper/result_registry.md` 登记。状态不是 `READY` 或 `BASELINE_READY` 的图表不得进入最终论文。

## 1. 状态定义

| 状态 | 含义 | 可否进正文 |
|---|---|---|
| `READY` | 图/表内容与来源已核验，版式和图注验收通过 | 可 |
| `BASELINE_READY` | 只呈现已登记首轮基线结果，文字明确非最终模型 | 可，须带限制说明 |
| `EXISTING_NOT_FINAL` | 已有文件，但版式、图注或科学边界尚未验收 | 暂不可 |
| `DIAGNOSTIC_ONLY` | 只展示已登记诊断事实，不表达最终机制结论 | 暂不可，需专项批准 |
| `BLOCKED` | 缺少关键数据、模型或验证结果 | 不可 |
| `PLANNED` | 只有内容计划，尚无资产 | 不可 |

## 2. 图编号清单

| 内部 ID | 预留正文号 | 图名/内容 | 目标章节 | 主来源 | 关联 result_id | 状态 | 生成/验收条件 |
|---|---:|---|---|---|---|---|---|
| `FIG-DATA-01` | 图 1 | 原始数据、编号族与四问证据流 | 4 | `paper/data_sources.md`；`solution/outputs/audit/dataset_registry.csv` | `RES-DATA-001` 至 `RES-DATA-007` | `PLANNED` | 仅画来源类别和依赖，不画未核验统计量 |
| `FIG-Q1-QUAL-01` | 图 2 | 质量指标方向统一、缺失/冲突处理与聚合流程 | 5.1 | 待质量终验输出 | 待分配 | `BLOCKED` | 有效分母、缺失策略、冲突规则和文本验证均冻结 |
| `FIG-Q1-MIX-01` | 图 3 | 1M 独立检验预测-实际与跨表迁移诊断 | 5.1、6 | `solution/outputs/mixture/aggregate_predictions.csv`；`metrics.csv`；`solution/outputs/figures/mixture_*_source.csv` | `RES-Q1-MIX-005` 至 `RES-Q1-MIX-009` | `EXISTING_NOT_FINAL` | 现有 `mixture_baseline_diagnostics.png/pdf/svg` 重做版式与图注验收；10B/70B 必须标估算 |
| `FIG-Q2-SCL-01` | 图 4 | B1 经典标度律残差与检查点诊断 | 5.2、6 | `solution/outputs/scaling/B1_all_predictions.csv`；`residual_diagnostics.csv`；`B1_precision_residual_audit.json` | `RES-Q2-SCL-001` 至 `RES-Q2-SCL-017` | `EXISTING_NOT_FINAL` | 现有 `scaling_fit_residuals.png/pdf` 复核；显示数据精度和近确定性警示 |
| `FIG-Q2-CONF-01` | 图 5 | B6/B7 与 B8 质量方向冲突及共同网格 | 5.2 | `solution/outputs/scaling/quality_audit.json`；`quality_within_ND_slopes.csv`；`B7_novel_grid_predicted_from_B6.csv` | `RES-Q2-CONF-001` 至 `RES-Q2-CONF-009` | `DIAGNOSTIC_ONLY` | 不合并方向；B8 明确标为半合成含外推；需图注验收 |
| `FIG-Q3-OPT-01` | 图 6 | 三档预算下最优配置与结构转移 | 5.3 | 待联合优化输出 | 待分配 | `BLOCKED` | 求解器、预算可行性、单纯形约束和敏感性均完成 |
| `FIG-Q3-SENS-01` | 图 7 | 成本函数与 `L_ctx` 敏感性 | 5.3、6 | 待联合优化输出 | 待分配 | `BLOCKED` | 成本函数至少完成题目三类比较和上下文可行值敏感性 |
| `FIG-Q4-EVOL-01` | 图 8 | 规模/非规模贡献与能力前沿 | 5.4 | 待 C 模块、桥接和预测输出 | 待分配 | `BLOCKED` | 时间外/分层检验、误差传播和 12/24 月预测完成 |

### 已存在图像文件清单

| 内部 ID | 现有文件 | 当前用途 |
|---|---|---|
| `FIG-Q1-MIX-01` | `solution/outputs/figures/mixture_baseline_diagnostics.png`、`.pdf`、`.svg` | 首轮配比基线候选图，尚未出版级验收 |
| `FIG-Q2-SCL-01` | `solution/outputs/scaling/scaling_fit_residuals.png`、`.pdf` | 首轮 B1 基线候选图，尚未出版级验收 |
| `FIG-Q2-CONF-01` | `solution/outputs/scaling/quality_direction_audit.png`、`.pdf` | 质量方向冲突诊断候选图，未解决冲突前仅内部使用 |

## 3. 表编号清单

| 内部 ID | 预留正文号 | 表名/内容 | 目标章节 | 主来源 | 关联 result_id | 状态 | 生成/验收条件 |
|---|---:|---|---|---|---|---|---|
| `TAB-SYM-01` | 表 1 | 统一符号、单位与命名冲突 | 3 | `paper/symbols.md` | 不涉结果值 | `READY` | 全文符号一致性检查 |
| `TAB-DATA-01` | 表 2 | A、B、C 数据来源与可信度边界 | 4 | `paper/data_sources.md`；`dataset_registry.csv` | `RES-DATA-001` 至 `RES-DATA-004` | `READY` | 每个来源保留说明文件性质 |
| `TAB-DATA-02` | 表 3 | 四问数据使用矩阵 | 4、7 | `paper/data_sources.md` | 不涉模型结果值 | `READY` | 不把 `SOURCE_LOADED_ONLY` 写成已完成 |
| `TAB-Q1-MIX-01` | 表 4 | 配比首轮基线指标与跨规模迁移 | 5.1、6 | `solution/outputs/mixture/metrics.csv` | `RES-Q1-MIX-005` 至 `RES-Q1-MIX-009` | `BASELINE_READY` | 标题明确“首轮基线”；1M/60M/1B 分列并标注迁移口径 |
| `TAB-Q1-QUAL-01` | 表 5 | 质量记录、去重、覆盖和有效分母 | 5.1、7 | 待质量终验输出 | 待分配 | `BLOCKED` | 有效分母闭合；行级/域级覆盖可追踪 |
| `TAB-Q1-QUAL-02` | 表 6 | 指标方向、冲突定义、消解与文本验证 | 5.1、6 | 待质量终验输出 | 待分配 | `BLOCKED` | 冲突规则和 A18 文本验证验收 |
| `TAB-Q2-SCL-01` | 表 7 | B1 经典标度律参数与三类验证 | 5.2、6 | `scaling_params.json`；`model_comparison.csv`；`B1_precision_residual_audit.json` | `RES-Q2-SCL-001` 至 `RES-Q2-SCL-017` | `BASELINE_READY` | 标题明确为经典 `L(N,D)`，不写广义律 |
| `TAB-Q2-CONF-01` | 表 8 | B6/B7/B8 方向、重叠与冲突 | 5.2、7 | `solution/outputs/scaling/quality_audit.json` | `RES-Q2-CONF-001` 至 `RES-Q2-CONF-009` | `DIAGNOSTIC_ONLY` | 保留冲突，不用“平均方向” |
| `TAB-Q3-OPT-01` | 表 9 | 至少三档预算的最优配置与可行域 | 5.3 | 待联合优化输出 | 待分配 | `BLOCKED` | 所有单位按物理 N、D 核验 |
| `TAB-Q3-SENS-01` | 表 10 | 质量成本函数、上下文和外推敏感性 | 5.3、6 | 待联合优化输出 | 待分配 | `BLOCKED` | 含 k=0/映射敏感性及边界说明 |
| `TAB-Q4-DATA-01` | 表 11 | 开源、模型类型、时间与可比性分层 | 5.4、4 | 待 C 审计输出 | 待分配 | `BLOCKED` | 身份匹配与去重审计完成 |
| `TAB-Q4-DECOMP-01` | 表 12 | 规模与非规模技术进步贡献 | 5.4、6 | 待 C 模块与桥接输出 | 待分配 | `BLOCKED` | 识别假设、时间外/分层检验和不确定性完成 |
| `TAB-Q4-FORE-01` | 表 13 | 12/24 个月前沿与不确定性 | 5.4、7 | 待预测输出 | 待分配 | `BLOCKED` | 桥接误差传播和情景口径完成 |
| `TAB-APP-REPRO-01` | 附表 A1 | 运行环境、源码版本、输出与复现入口 | 附录 | 待最终归档 | 不涉结果值 | `PLANNED` | 依赖锁、脚本入口、AI 披露和输出清单冻结 |
| `TAB-APP-RES-01` | 附表 A2 | 结果登记摘要 | 附录 | `paper/result_registry.md` | 全部已登记项 | `PLANNED` | 与正文数字逐项交叉核对 |

## 4. 图表准入规则

1. 图表中的每个数值必须回指 `result_id` 或明确标为输入常数。
2. 半合成、插值、估计、外推必须在图例/表注和正文中同时标注。
3. 不得用推测数据补空、平滑掉来源冲突或只展示有利区间。
4. 每个图/表必须有源数据文件；只有图片而没有源数据不得进入最终论文。
5. B6/B7/B8 不得画成一条合并质量曲线；冲突必须保留。
6. 首轮配比和 B1 图表的标题、图注必须写“首轮基线”或等价限定。
7. 问三、问四在没有运行输出前只允许保留本清单空位，禁止在正文插图占位。
8. 图表重绘不得改变登记数值；若改变模型、筛选或口径，必须新增 result_id。

## 5. 编号冻结流程

1. 先确认章节顺序和每个图表的准入状态。
2. 再将本表预留号按正文首次出现顺序重新连续编号。
3. 图题、表题、正文 callout、交叉引用、附录和结果登记表同步更新。
4. 全文搜索旧编号和 `TBD`/`待分配`，确保最终 PDF 中没有未解决占位。
5. 冻结后任何新增图表必须整体重排编号并再次做交叉引用检查。


## 6. 2026-09-25 Q1/Q2写作阶段占位符

本阶段新增的稳定正文和图表占位符入口为：

- paper/manuscript/Q1_Q2_STABLE_BODY.md
- paper/manuscript/figure_table_placeholders_q1_q2.md
- paper/manuscript/source_map_q1_q2.md

对于问题一、问题二，上表早期状态若与本阶段T06冻结或T03E/Q01C正式结果冲突，以本阶段文件和paper/T06_RESULT_FREEZE.md为准。问题三、问题四仍为BLOCKED。


## 7. 2026-09-25 Q3写作阶段占位符

问题三稳定正文与占位符入口：

- paper/manuscript/Q3_STABLE_BODY.md
- paper/manuscript/figure_table_placeholders_q3.md
- paper/manuscript/source_map_q3.md

问题三唯一正式结果口径为paper/T07_RESULT_FREEZE.md。所有质量、配比、B8冲突与跨源结果均为SCENARIO_ONLY或冲突证据，不覆盖Q1/Q2既有冻结口径。


## 8. 2026-09-25 Q4与PAPER V1整合

问题四正文与全文V1入口：

- paper/manuscript/Q4_STABLE_BODY.md
- paper/manuscript/source_map_q4.md
- paper/manuscript/figure_table_placeholders_q4.md
- paper/manuscript/FINAL_FIGURE_TABLE_PLAN.md
- paper/manuscript/FULL_MANUSCRIPT_V1.md
- paper/manuscript/FINAL_CLAIM_EVIDENCE_AUDIT.md

Q4图表资格遵循T05/T08：bridge=CONDITIONAL_ASSOCIATION_ONLY；time trend=UNVALIDATED_FOR_EXTRAPOLATION；future progress=NOT_IDENTIFIABLE_PROGRESS；主模型CONSTANT。
