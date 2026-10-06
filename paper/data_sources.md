# 数据与证据来源表

> 建立时间：2026-09-24。所有原始路径均相对 `F题/real_attachments/`。
>
> 表中的 `files`、`bytes`、`nature` 来自 `solution/outputs/audit/dataset_registry.csv` 的 `file_count`、`bytes`、`nature_as_documented` 字段；文件级路径、大小和哈希由 `raw_source_manifest.csv` 与 `recovery/2026-09-24/verification.json` 交叉检查。它们是数据清单事实，不是模型结果。
>
> `observed`、`真实` 等标签仅表示附件说明文件的来源口径，不构成外部真实性认证。半合成、插值、估算和外推数据必须保留原标签。

## 1. 原始数据来源状态定义

| 状态 | 解释 | 是否可作最终证据 |
|---|---|---|
| `MANIFEST_VERIFIED` | 路径、大小及适用哈希已核验 | 仅可作为数据清单证据 |
| `BASELINE_OUTPUT` | 有首轮运行产物，且适用指标已复算/一致性核验 | 只能按首轮基线边界引用 |
| `PARTIAL_OUTPUT` | 有部分运行产物，但关键终验或分母未闭合 | 否；只可报告审计事实 |
| `SOURCE_LOADED_ONLY` | 仅确认文件存在/大小，未完成本项目建模处理 | 否 |
| `NOT_PROCESSED` | 数据列为输入，但当前没有输出证据 | 否 |

## 2. A 表：质量与领域配比

来源表依据：`solution/outputs/audit/dataset_registry.csv`；行级清单依据：`solution/outputs/audit/raw_source_manifest.csv`。

| ID | 原始路径 | 说明文件性质 | files | bytes | 目标问题 | 当前状态与用途 |
|---|---|--:|--:|--:|--:|---|
| A1 | `A_data_value/slimpajama_quality_signal_sample.jsonl.xz` | observed | 1 | 103349792 | 1 | `PARTIAL_OUTPUT`；保留审计计数，不把现有 Q 作最终结果 |
| A2 | `A_data_value/slimpajama_quality_extended/arxiv_*.jsonl.xz` | observed | 1 | 3652724 | 1 | `PARTIAL_OUTPUT`；扩展 arxiv 分支参与审计 |
| A3 | `A_data_value/slimpajama_quality_extended/github_*.jsonl.xz` | observed | 1 | 37618172 | 1 | `PARTIAL_OUTPUT`；扩展 github 分支参与审计 |
| A4 | `A_data_value/regmix_tables/train_mixture_1m.csv` | observed | 1 | 46412 | 1 | `BASELINE_OUTPUT`；配比训练表 |
| A5 | `A_data_value/regmix_tables/train_pile_loss_1m.csv` | observed | 1 | 121898 | 1 | `BASELINE_OUTPUT`；配比训练 Loss 表 |
| A6 | `A_data_value/regmix_tables/test_mixture_1m.csv` | observed | 1 | 23537 | 1 | `BASELINE_OUTPUT`；1M 检验配比 |
| A7 | `A_data_value/regmix_tables/test_pile_loss_1m.csv` | observed | 1 | 61175 | 1 | `BASELINE_OUTPUT`；1M 检验 Loss |
| A8 | `A_data_value/regmix_tables/test_mixture_60m.csv` | observed | 1 | 23537 | 1 | `BASELINE_OUTPUT`；60M 迁移检验配比 |
| A9 | `A_data_value/regmix_tables/test_pile_loss_60m.csv` | observed | 1 | 61827 | 1 | `BASELINE_OUTPUT`；60M 迁移检验 Loss |
| A10 | `A_data_value/regmix_tables/test_mixture_1B.csv` | observed | 1 | 6393 | 1 | `BASELINE_OUTPUT`；1B 迁移检验配比 |
| A11 | `A_data_value/regmix_tables/test_pile_loss_1B.csv` | observed | 1 | 10639 | 1 | `BASELINE_OUTPUT`；1B 迁移检验 Loss |
| A12 | `A_data_value/regmix_tables/est_mixture_10b.csv` | training_subset | 1 | 6113 | 1 | `SOURCE_LOADED_ONLY`；估算输入，不是独立真值 |
| A13 | `A_data_value/regmix_tables/est_pile_loss_10b.csv` | estimated | 1 | 6467 | 1 | `SOURCE_LOADED_ONLY`；估算 Loss，不能作验证真值 |
| A14 | `A_data_value/regmix_tables/est_mixture_70b.csv` | training_subset | 1 | 6113 | 1 | `SOURCE_LOADED_ONLY`；估算输入，不是独立真值 |
| A15 | `A_data_value/regmix_tables/est_pile_loss_70b.csv` | estimated | 1 | 6467 | 1 | `SOURCE_LOADED_ONLY`；估算 Loss，不能作验证真值 |
| A16 | `A_data_value/domain_mapping_guide.csv` | reference_mapping | 1 | 1296 | 1 | `SOURCE_LOADED_ONLY`；仅作跨域映射参考，映射有效性未验收 |
| A17 | `A_data_value/regmix_domain_summary.csv` | observed_summary | 1 | 1265 | 1 | `SOURCE_LOADED_ONLY`；当前未用于最终结论 |
| A18 | `A_data_value/regmix_domain_sample.jsonl.xz` | observed_text | 1 | 165293312 | 1 | `NOT_PROCESSED`；可选文本验证尚无结果 |

## 3. B 表：标度律与质量补充

来源表依据：`solution/outputs/audit/dataset_registry.csv`。B1 主拟合与校验证据见 `solution/outputs/scaling/`；B2、B3、B4、B5 的既有预测不能自动升级为独立真值验证。

| ID | 原始路径 | 说明文件性质 | files | bytes | 目标问题 | 当前状态与用途 |
|---|---|--:|--:|--:|--:|---|
| B1 | `B_scaling_laws/pythia_training_log_existing.csv` | observed | 1 | 111459 | 2 | `BASELINE_OUTPUT`；经典标度律主拟合，附件标注真实轨迹 |
| B2 | `B_scaling_laws/cerebras_training_log.csv` | semisynthetic | 1 | 89643 | 2 | `BASELINE_OUTPUT`；族外情景检查，不是真实新实验 |
| B3 | `B_scaling_laws/training_trajectories/*.csv` | interpolated | 8 | 112320 | 2 | `BASELINE_OUTPUT`；由 B1 得到的插值，不是独立验证 |
| B4 | `B_scaling_laws/scaling_baseline.csv` | published_observed | 1 | 1421 | 2 | `BASELINE_OUTPUT`；跨族绝对 Loss 口径未统一 |
| B5 | `B_scaling_laws/published_scaling_data.csv` | published_observed | 1 | 1967 | 2 | `BASELINE_OUTPUT`；文献绝对 Loss 口径未统一 |
| B6 | `B_scaling_laws/supplementary_NQ_experiment.csv` | semisynthetic | 1 | 13670 | 2 | `PARTIAL_OUTPUT`；质量方向与情景分析，不能作已标定 Q |
| B7 | `B_scaling_laws/supplementary_NQ_experiment_expanded.csv` | semisynthetic | 1 | 17154 | 2 | `PARTIAL_OUTPUT`；含 B6 重复点，不能作独立重复实验 |
| B8 | `B_scaling_laws/supplementary_NQ_experiment_large.csv` | semisynthetic_with_extrapolation | 1 | 81268 | 2 | `PARTIAL_OUTPUT`；共同网格方向与 B6/B7 冲突，未解决 |
| B9 | `B_scaling_laws/supplementary_large_models.csv` | reported_metadata | 1 | 13400 | 2 | `SOURCE_LOADED_ONLY`；仅作大模型覆盖与口径讨论 |
| B10 | `B_scaling_laws/supplementary_large_baseline.csv` | estimated | 1 | 4744 | 2 | `SOURCE_LOADED_ONLY`；估算值，不能验证生成律 |
| B11 | `B_scaling_laws/open_model_family_metadata.csv` | metadata | 1 | 1975 | 2 | `SOURCE_LOADED_ONLY`；辅助元数据 |
| B12 | `B_scaling_laws/pythia_checkpoint_index.csv` | metadata | 1 | 117698 | 2 | `SOURCE_LOADED_ONLY`；辅助检查点索引 |

## 4. C 表：技术演进与 Benchmark

来源表依据：`solution/outputs/audit/dataset_registry.csv`。恢复阶段未运行 `evolution_audit.py` 的建模分析，因此 C 数据统一为 `SOURCE_LOADED_ONLY` 或 `NOT_PROCESSED`，不能引用源码模板中的统计文字。

| ID | 原始路径 | 说明文件性质 | files | bytes | 目标问题 | 当前状态与用途 |
|---|---|--:|--:|--:|--:|---|
| C1 | `C_efficiency_evolution/leaderboard_cleaned.csv` | observed | 1 | 1011558 | 4 | `SOURCE_LOADED_ONLY`；尚未完成身份、类型和时间审计 |
| C2 | `C_efficiency_evolution/leaderboard_enhanced.csv` | observed_plus_metadata_matching | 1 | 1036749 | 4 | `SOURCE_LOADED_ONLY`；尚未完成匹配质量审计 |
| C3 | `C_efficiency_evolution/leaderboard_extended_timeseries.csv` | mixed | 1 | 826723 | 4 | `SOURCE_LOADED_ONLY`；混合口径和时间轴未验收 |
| C4 | `C_efficiency_evolution/epoch_all_ai_models.csv` | reported_metadata | 1 | 6671403 | 4 | `SOURCE_LOADED_ONLY`；算力/数据量/开源字段未逐项审计 |
| C5 | `C_efficiency_evolution/loss_benchmark_bridge.csv` | mixed_comparability | 1 | 11807 | 4 | `NOT_PROCESSED`；桥接可比性未分级验收 |
| C6 | `C_efficiency_evolution/loss_benchmark_bridge_expanded.csv` | mixed_comparability | 1 | 19124 | 4 | `NOT_PROCESSED`；桥接与误差传播未完成 |
| C7 | `C_efficiency_evolution/model_architecture_metadata.csv` | metadata | 1 | 2357 | 3,4 | `SOURCE_LOADED_ONLY`；问题三仅作上下文可行值依据，尚未用于优化 |
| C8 | `C_efficiency_evolution/detailed_results/**/*.json` | observed_evaluation | 1958 | 228862701 | 4 | `NOT_PROCESSED`；未做逐任务聚合；长路径与损坏日志处理未完成 |
| C9 | `C_efficiency_evolution/data/*.parquet` | observed_evaluation | 1 | 1109997 | 4 | `SOURCE_LOADED_ONLY`；辅助数据尚未接入 |
| C10 | `C_efficiency_evolution/pythia*eval_details/README.md` | documentation_only | 7 | 487670 | 4 | `SOURCE_LOADED_ONLY`；仅文档，不是模型结果 |

## 5. 已有派生证据入口

| 派生证据 | 覆盖范围 | 可复用边界 |
|---|---|---|
| `solution/outputs/audit/manifest_summary.json` | 2012 文件、551191693 字节、40 个逻辑编号 | 只证明清单口径 |
| `recovery/2026-09-24/verification.json` | 68 项检查：65 PASS、3 FAIL | 与已列检查项绑定；不代表端到端复跑 |
| `solution/outputs/quality/audit.json` | A1–A3 行数、唯一键、重复次数和字段审计 | 只作部分质量审计事实；有效分母未闭合 |
| `solution/outputs/quality/feature_summary.csv` | 质量特征覆盖/分母 | 存在非有限值和分母问题；不得下游采用 |
| `solution/outputs/mixture/metrics.csv` | 线性/二次配比基线与各数据表指标 | 首轮基线；不能称全局最优 |
| `solution/outputs/scaling/scaling_params.json` | B1 参数、观测范围、质量情景 | 参数为主拟合输出；情景为 `UNVALIDATED_SCENARIO_ONLY` |
| `solution/outputs/scaling/model_comparison.csv` | B1 四种配置拟合/验证比较 | 选择配置为探索性，无独立最终测试集 |
| `solution/outputs/scaling/quality_audit.json` | B6/B7/B8 方向、重叠与冲突 | 冲突未解决；不得无说明合并 |
| `solution/outputs/evolution/` | 不存在 | 不能建立 C 结果证据 |
| 问三输出目录 | 不存在 | 不能建立优化结果证据 |

## 6. 数据使用矩阵

| 数据 | 问题一 | 问题二 | 问题三 | 问题四 | 当前结论 |
|---|:--:|:--:|:--:|:--:|---|
| A1–A3 | 必需 | 经问题一接口 | 经 Q 接口 | 间接 | 质量结果部分完成，不可最终采用 |
| A4–A15 | 必需 | 经 p 接口 | 经 p 接口 | 间接 | 配比首轮基线存在；未完成广义接口 |
| A16 | 映射参考 | 来源统一 | 来源统一 | 间接 | 映射规则尚未验收 |
| A17–A18 | 可选/辅助 | 经问题一接口 | 间接 | 间接 | A18 未处理 |
| B1 | 否 | 主拟合 | 参数接口 | 经桥接/演化 | 经典基线存在，不是广义律 |
| B2–B5 | 否 | 验证/讨论 | 约束外推边界 | 经桥接 | 存在既有预测，但验证口径有限 |
| B6–B8 | Q 语义可能相关 | 质量补充 | 情景输入 | 间接 | 方向冲突，不能当已标定关系 |
| B9–B12 | 否 | 外推/元数据辅助 | 边界 | 间接 | 仅审计/讨论 |
| C1–C4 | 否 | 否 | C7 辅助 | 必需 | C 分析未运行 |
| C5–C6 | 否 | 否 | 间接 | 桥接必需 | 未完成可比性和误差分析 |
| C7 | 否 | 否 | Lctx 可行值 | 辅助 | 未用于优化结果 |
| C8–C10 | 否 | 否 | 否 | C8 必需 | 未聚合，未验证 |

## 7. 外部文献与引用来源

当前没有“已经完成逐字核验并可直接入参考文献”的外部来源清单。题目参考文献条目和 `参考资料/` 中的其他论文均不能自动视为已核验来源，参考论文中的数字也不能登记为本项目结果。

进入正文前的来源门槛：

1. 数据集出处、版本、访问日期和许可；
2. 方法原论文的正式作者、题名、出处、年份和页码/DOI；
3. 若引用他人图表、代码或数据，注明获取位置与复用条件；
4. 对附件说明中的条目与出版记录冲突时，以可核验出版记录为准并保留差异记录。

## 8. 数值来源规则

- 原始数据文件只读；不改写、不覆盖。
- 每个进入论文数值都必须映射到 `paper/result_registry.md`。
- 同一数值有多个来源时，登记主来源和核验来源，不合并冲突口径。
- 半合成、插值、估算、外推点必须使用不同符号/线型/表注，并在图注中写明。
- 派生结果必须保存代码、输入版本、输出文件和中间表；仅有控制台聊天记录不算证据。
