# 结果登记表

> 建立时间：2026-09-24。此表是论文数字的唯一登记入口。未在本表登记并审查的数字，不得进入摘要、正文、图表、图注或结论。
>
> “已验证”只表示该数值与指定文件字段、行级选择和已执行核验一致；不表示模型已经被最终验收。`review_status` 决定该数值可用于什么位置。聊天记忆、参考论文、源码中的待写模板和文件名均不是数值来源。

## 1. 登记字段

| 字段 | 必填 | 规则 |
|---|:--:|---|
| `result_id` | 是 | 永久唯一编号；发现错误时新增修订记录，不覆写旧证据 |
| `problem` | 是 | `GLOBAL`、`Q1`、`Q2`、`Q3`、`Q4` |
| `description` | 是 | 精确描述事实，不扩大解释 |
| `value` | 是 | 原始精度或规定显示精度；不得省略未列出的舍入规则 |
| `unit` | 是 | 文件、字节、行、参数、token、Loss、无量纲等 |
| `source_file` | 是 | 相对项目根目录的实际文件 |
| `source_field` | 是 | JSON 字段路径或 CSV 列，并包含必要筛选条件 |
| `verification_status` | 是 | `PASS`、`PARTIAL`、`FAIL`、`PENDING`，附核验项/范围 |
| `review_status` | 是 | 明确允许用途；未批准用途默认禁止 |
| `source_locator` | 是 | JSON/CSV 行、工作表或运行产物定位信息 |

## 2. 数据清单类已登记结果

| result_id | problem | description | value | unit | source_file | source_field | verification_status | review_status | source_locator |
|---|---|---|---|---|---|---|---|---|---|
| `RES-DATA-001` | GLOBAL | 原始工作区实际文件数 | 2012 | 文件 | `solution/outputs/audit/manifest_summary.json` | `files` | PASS：`raw_paths_and_sizes` | APPROVED：仅数据清单 | JSON 根对象 |
| `RES-DATA-002` | GLOBAL | 原始工作区实际字节数 | 551191693 | 字节 | `solution/outputs/audit/manifest_summary.json` | `bytes` | PASS：`raw_paths_and_sizes` | APPROVED：仅数据清单 | JSON 根对象 |
| `RES-DATA-003` | GLOBAL | 逻辑数据编号数 | 40 | 项 | `solution/outputs/audit/manifest_summary.json` | `registry_entries` | PASS：`dataset_registry`一致性 | APPROVED：仅数据清单 | JSON 根对象 |
| `RES-DATA-004` | GLOBAL | 纳入 SHA256 核验的原始 CSV 数 | 41 | 文件 | `recovery/2026-09-24/verification.json` | `checks[check=raw_csv_hashes].detail.files_checked` | PASS：`raw_csv_hashes` | APPROVED：仅完整性核验 | JSON checks 数组 |
| `RES-DATA-005` | GLOBAL | 本轮轻量核验总数 | 68 | 项 | `recovery/2026-09-24/verification.json` | `checks` 数组长度 | PASS：文件和数组可解析 | APPROVED：仅恢复核验范围 | JSON 根对象 |
| `RES-DATA-006` | GLOBAL | 本轮轻量核验通过数 | 65 | 项 | `recovery/2026-09-24/verification.json` | `checks[status=PASS]` 计数 | PASS：逐项状态一致 | APPROVED：仅恢复核验范围 | JSON checks 数组 |
| `RES-DATA-007` | GLOBAL | 本轮轻量核验失败数 | 3 | 项 | `recovery/2026-09-24/verification.json` | `checks[status=FAIL]` 计数 | PASS：逐项状态一致 | APPROVED：仅用于声明质量缺口 | JSON checks 数组 |

## 3. 问题一：质量审计已登记事实

> 以下数字只证明 A1–A3 的审计计数与算术关系；不能据此宣布综合质量分 `Q_A` 已验收。质量结果受 `quality_summary_score_definition`、`quality_A1_aggregate_commoncrawl`、`quality_A1_aggregate_wikipedia` 三项 FAIL 和有效分母问题约束。

| result_id | problem | description | value | unit | source_file | source_field | verification_status | review_status | source_locator |
|---|---|---|---|---|---|---|---|---|---|
| `RES-Q1-QUAL-001` | Q1 | A1 读取记录数 | 51230 | 行 | `solution/outputs/quality/audit.json` | `files[file_id=A1].rows` | PASS：`quality_saved_counts` 与算术关系 | AUDIT_ONLY：不得当最终 Q 分母 | JSON 文件数组 A1 |
| `RES-Q1-QUAL-002` | Q1 | A2 arxiv 扩展记录数 | 17523 | 行 | `solution/outputs/quality/audit.json` | `files[file_id=A2_arxiv].rows` | PASS：`quality_saved_counts` 与算术关系 | AUDIT_ONLY：不得当最终 Q 分母 | JSON 文件数组 A2 |
| `RES-Q1-QUAL-003` | Q1 | A3 github 扩展记录数 | 203752 | 行 | `solution/outputs/quality/audit.json` | `files[file_id=A3_github].rows` | PASS：`quality_saved_counts` 与算术关系 | AUDIT_ONLY：不得当最终 Q 分母 | JSON 文件数组 A3 |
| `RES-Q1-QUAL-004` | Q1 | A1–A3 总记录数 | 272505 | 行 | `solution/outputs/quality/audit.json` | `total_records` | PASS：`quality_saved_counts` 与算术关系 | AUDIT_ONLY：不得当最终模型样本数 | JSON 根对象 |
| `RES-Q1-QUAL-005` | Q1 | 联合键唯一记录数 | 261086 | 行 | `solution/outputs/quality/audit.json` | `unique_id_sub_path_keys` | PASS：`quality_saved_counts` 与算术关系 | AUDIT_ONLY：不得当最终 Q 有效分母 | JSON 根对象 |
| `RES-Q1-QUAL-006` | Q1 | 重复出现次数 | 11419 | 次 | `solution/outputs/quality/audit.json` | `duplicate_occurrences` | PASS：`quality_saved_counts` 与算术关系 | AUDIT_ONLY：不得当缺失数 | JSON 根对象 |
| `RES-Q1-QUAL-007` | Q1 | A1 与 A2 arxiv 联合键交集 | 1419 | 行 | `solution/outputs/quality/audit.json` | `pairwise_key_intersections.A1__A2_arxiv` | PASS：`quality_saved_counts` 与算术关系 | AUDIT_ONLY：仅重叠事实 | JSON 根对象 |
| `RES-Q1-QUAL-008` | Q1 | A1 与 A3 github 联合键交集 | 10000 | 行 | `solution/outputs/quality/audit.json` | `pairwise_key_intersections.A1__A3_github` | PASS：`quality_saved_counts` 与算术关系 | AUDIT_ONLY：仅重叠事实 | JSON 根对象 |
| `RES-Q1-QUAL-009` | Q1 | A2 arxiv 与 A3 github 联合键交集 | 0 | 行 | `solution/outputs/quality/audit.json` | `pairwise_key_intersections.A2_arxiv__A3_github` | PASS：`quality_saved_counts` 与算术关系 | AUDIT_ONLY：仅重叠事实 | JSON 根对象 |
| `RES-Q1-QUAL-010` | Q1 | 原始质量字段数 | 22 | 字段 | `solution/outputs/quality/audit.json` | `raw_quality_fields` | PASS：`quality_saved_counts` | AUDIT_ONLY：字段计数，不是已完成融合数 | JSON 根对象 |
| `RES-Q1-QUAL-011` | Q1 | 展开的标量特征数 | 25 | 特征 | `solution/outputs/quality/audit.json` | `expanded_scalar_features` | PASS：`quality_saved_counts` | AUDIT_ONLY：不等于最终主 Q 特征数 | JSON 根对象 |

## 4. 问题一：配比首轮基线已登记结果

> 这些结果只能称“首轮配比基线”。`test_1m` 为独立检验；`test_60m`、`test_1B` 是未经大尺度重校准的跨规模迁移；不得称全局最优。

| result_id | problem | description | value | unit | source_file | source_field | verification_status | review_status | source_locator |
|---|---|---|---|---|---|---|---|---|---|
| `RES-Q1-MIX-001` | Q1 | 1M 训练配比归一化数据行数 | 512 | 行 | `solution/outputs/mixture/train_1m_normalized_mixtures.csv` | CSV 数据行数 | PASS：`mixture_normalization_train_1m` | APPROVED：仅基线输入规模 | CSV 除表头外全部行 |
| `RES-Q1-MIX-002` | Q1 | 1M 独立检验配比行数 | 256 | 行 | `solution/outputs/mixture/test_1m_normalized_mixtures.csv` | CSV 数据行数 | PASS：`mixture_normalization_test_1m` | APPROVED：仅基线输入规模 | CSV 除表头外全部行 |
| `RES-Q1-MIX-003` | Q1 | 60M 跨规模迁移检验行数 | 256 | 行 | `solution/outputs/mixture/test_60m_normalized_mixtures.csv` | CSV 数据行数 | PASS：`mixture_normalization_test_60m` | APPROVED：仅迁移输入规模 | CSV 除表头外全部行 |
| `RES-Q1-MIX-004` | Q1 | 1B 跨规模迁移检验行数 | 64 | 行 | `solution/outputs/mixture/test_1B_normalized_mixtures.csv` | CSV 数据行数 | PASS：`mixture_normalization_test_1B` | APPROVED：仅迁移输入规模 | CSV 除表头外全部行 |
| `RES-Q1-MIX-005` | Q1 | 线性模型 1M 独立检验逐域等权 RMSE | 0.2269777772847171 | Loss 单位 | `solution/outputs/mixture/metrics.csv` | `rmse_equal_domain_mean` | PASS：`mixture_metrics_linear_test_1m` 并由保存预测复算 | APPROVED_AS_BASELINE：不得称最终模型 | `model=linear,set=test_1m` |
| `RES-Q1-MIX-006` | Q1 | 线性模型 1M 独立检验逐域等权 R² | 0.3319216143105982 | 无量纲 | `solution/outputs/mixture/metrics.csv` | `r2_equal_domain_mean` | PASS：`mixture_metrics_linear_test_1m` 并由保存预测复算 | APPROVED_AS_BASELINE：不得称最终模型 | `model=linear,set=test_1m` |
| `RES-Q1-MIX-007` | Q1 | 线性模型 1M 独立检验逐域等权 Spearman | 0.6250743877317463 | 相关系数 | `solution/outputs/mixture/metrics.csv` | `spearman_equal_domain_mean` | PASS：`mixture_metrics_linear_test_1m` 并由保存预测复算 | APPROVED_AS_BASELINE：不得称最终模型 | `model=linear,set=test_1m` |
| `RES-Q1-MIX-008` | Q1 | 线性模型 60M 跨规模迁移逐域等权 RMSE | 1.5173310791562076 | Loss 单位 | `solution/outputs/mixture/metrics.csv` | `rmse_equal_domain_mean` | PASS：`mixture_metrics_linear_test_60m` 并由保存预测复算 | APPROVED_AS_TRANSFER_DIAGNOSTIC：不得称稳定迁移 | `model=linear,set=test_60m` |
| `RES-Q1-MIX-009` | Q1 | 线性模型 1B 跨规模迁移逐域等权 RMSE | 3.188945347793164 | Loss 单位 | `solution/outputs/mixture/metrics.csv` | `rmse_equal_domain_mean` | PASS：`mixture_metrics_linear_test_1B` 并由保存预测复算 | APPROVED_AS_TRANSFER_DIAGNOSTIC：不得称稳定迁移 | `model=linear,set=test_1B` |
| `RES-Q1-MIX-010` | Q1 | 训练内嵌套 5 折所选模型族 | linear | 类别 | `solution/outputs/mixture/model.json` | `selected_by_training_only` | PASS：模型选择字段与源码规则一致 | APPROVED_AS_BASELINE：不是最终模型结论 | JSON 根字段 |
| `RES-Q1-MIX-011` | Q1 | 训练内嵌套 5 折选择目标 | equal_weight_mean_MSE_across_13_validation_domains | 类别 | `solution/outputs/mixture/model.json` | `objective` | PASS：字段可读且与恢复决定 D04 一致 | APPROVED_AS_BASELINE：不得改成先平均 Loss 再算 RMSE | JSON 根字段 |

## 5. 问题二：B1 经典标度律首轮基线已登记结果

> 这些数值是 B1 上的经典 `L(N,D)` 首轮拟合与验证结果，不是含 Q、p 的广义标度律。B1 近乎确定性的拟合形态仍需核验来源与变换，不能宣称为独立发现或外推精度保证。

| result_id | problem | description | value | unit | source_file | source_field | verification_status | review_status | source_locator |
|---|---|---|---|---|---|---|---|---|---|
| `RES-Q2-SCL-001` | Q2 | B1 经典标度律不可约损失参数 | 1.6897975629820348 | Loss 单位 | `solution/outputs/scaling/scaling_params.json` | `parameters.E` | PASS：`B1_saved_formula_and_raw` | APPROVED_AS_CLASSIC_BASELINE：不是最终广义律 | JSON 根对象 |
| `RES-Q2-SCL-002` | Q2 | B1 参数量幂律系数 | 0.35398032060655715 | 与所用 N_B、Loss 尺度相关 | `solution/outputs/scaling/scaling_params.json` | `parameters.A` | PASS：`B1_saved_formula_and_raw` | APPROVED_AS_CLASSIC_BASELINE：不是最终广义律 | JSON 根对象 |
| `RES-Q2-SCL-003` | Q2 | B1 数据量幂律系数 | 1.2403055835426349 | 与所用 D_B、Loss 尺度相关 | `solution/outputs/scaling/scaling_params.json` | `parameters.B` | PASS：`B1_saved_formula_and_raw` | APPROVED_AS_CLASSIC_BASELINE：不是最终广义律 | JSON 根对象 |
| `RES-Q2-SCL-004` | Q2 | B1 参数量指数 | 0.33997658194108205 | 无量纲 | `solution/outputs/scaling/scaling_params.json` | `parameters.alpha` | PASS：`B1_saved_formula_and_raw` | APPROVED_AS_CLASSIC_BASELINE：不是最终广义律 | JSON 根对象 |
| `RES-Q2-SCL-005` | Q2 | B1 数据量指数 | 0.27987812854684485 | 无量纲 | `solution/outputs/scaling/scaling_params.json` | `parameters.beta` | PASS：`B1_saved_formula_and_raw` | APPROVED_AS_CLASSIC_BASELINE：不是最终广义律 | JSON 根对象 |
| `RES-Q2-SCL-006` | Q2 | B1 观测参数规模范围 | 0.070542–11.965825 | 10^9 参数 | `solution/outputs/scaling/scaling_params.json` | `observed_ranges.N_B` | PASS：`B1_saved_formula_and_raw` | APPROVED_AS_BASELINE：仅已观测范围 | JSON 根对象 |
| `RES-Q2-SCL-007` | Q2 | B1 观测数据规模范围 | 0.134–299.893 | 10^9 token | `solution/outputs/scaling/scaling_params.json` | `observed_ranges.D_B` | PASS：`B1_saved_formula_and_raw` | APPROVED_AS_BASELINE：仅已观测范围 | JSON 根对象 |
| `RES-Q2-SCL-008` | Q2 | B1 主拟合配置 | point__linear | 类别 | `solution/outputs/scaling/scaling_params.json` | `model_selection.configuration` | PASS：配置与 `model_comparison.csv` 一致 | APPROVED_AS_EXPLORATORY_SELECTION：无独立最终测试集 | JSON 根对象 |
| `RES-Q2-SCL-009` | Q2 | B1 主拟合使用检查点数 | 1176 | 点 | `solution/outputs/scaling/model_comparison.csv` | `fit_n` | PASS：`B1_metrics_point__linear_in_sample` | APPROVED_AS_CLASSIC_BASELINE | `configuration=point__linear` |
| `RES-Q2-SCL-010` | Q2 | 固定模型内拟合 RMSE | 0.00014649608992588822 | Loss 单位 | `solution/outputs/scaling/model_comparison.csv` | `fit_RMSE` | PASS：`B1_metrics_point__linear_in_sample` | APPROVED_AS_CLASSIC_BASELINE：不是泛化精度 | `configuration=point__linear` |
| `RES-Q2-SCL-011` | Q2 | 留一模型验证 RMSE | 0.00015117977861670508 | Loss 单位 | `solution/outputs/scaling/model_comparison.csv` | `LOMO_RMSE` | PASS：`B1_metrics_point__linear_leave_one_model_out` | APPROVED_AS_EXPLORATORY_VALIDATION | `configuration=point__linear` |
| `RES-Q2-SCL-012` | Q2 | 每个模型末 20% token 验证 RMSE | 0.00010909749164734156 | Loss 单位 | `solution/outputs/scaling/model_comparison.csv` | `stage_RMSE` | PASS：`B1_metrics_point__linear_last_20pct_tokens` | APPROVED_AS_EXPLORATORY_VALIDATION | `configuration=point__linear` |
| `RES-Q2-SCL-013` | Q2 | 保存的模型簇 bootstrap 次数 | 80 | 次 | `solution/outputs/scaling/cluster_bootstrap_parameters.csv` | CSV 数据行数 | PASS：`saved_bootstrap_quantiles_E` 至 `saved_bootstrap_quantiles_beta` | APPROVED_AS_DESCRIPTIVE_ONLY：仅 8 个轨迹簇，不是广泛置信区间 | CSV 除表头外全部行 |
| `RES-Q2-SCL-014` | Q2 | B1 Loss 字段小数位数 | 4 | 位 | `solution/outputs/scaling/B1_precision_residual_audit.json` | `val_loss_csv_decimal_places` | PASS：精度审计文件可读且与报告一致 | APPROVED_FOR_PRECISION_LIMITATION | JSON 根对象 |
| `RES-Q2-SCL-015` | Q2 | B1 数据量字段小数位数 | 3 | 位 | `solution/outputs/scaling/B1_precision_residual_audit.json` | `D_tokens_B_csv_decimal_places` | PASS：精度审计文件可读且与报告一致 | APPROVED_FOR_PRECISION_LIMITATION | JSON 根对象 |
| `RES-Q2-SCL-016` | Q2 | Loss 半舍入单位 | 0.00005 | Loss 单位 | `solution/outputs/scaling/B1_precision_residual_audit.json` | `loss_rounding_half_unit` | PASS：精度审计文件可读 | APPROVED_FOR_PRECISION_LIMITATION | JSON 根对象 |
| `RES-Q2-SCL-017` | Q2 | 拟合 RMSE 相对于 Loss 半舍入单位的倍数 | 2.929921798517764 | 倍 | `solution/outputs/scaling/B1_precision_residual_audit.json` | `rmse_in_loss_rounding_half_units` | PASS：精度审计文件可读 | APPROVED_FOR_PRECISION_LIMITATION：不能据此证明真实外推精度 | JSON 根对象 |

## 6. 问题二：质量趋势与来源冲突的已登记诊断

> 这些是已复算的诊断事实，不是已解决的 Q 规律。B6/B7 与 B8 方向相反，禁止合并或无说明取平均，禁止把 B8 用于问三参数。

| result_id | problem | description | value | unit | source_file | source_field | verification_status | review_status | source_locator |
|---|---|---|---|---|---|---|---|---|---|
| `RES-Q2-CONF-001` | Q2 | B6 固定 N,D 组内斜率方向计数 | 45 组为负，0 组为正 | 组 | `solution/outputs/scaling/quality_audit.json` | `table_results.B6.negative_group_slopes`; `positive_group_slopes` | PASS：`quality_direction_B6` | DIAGNOSTIC_ONLY_UNRESOLVED | JSON `table_results.B6` |
| `RES-Q2-CONF-002` | Q2 | B7 固定 N,D 组内斜率方向计数 | 45 组为负，0 组为正 | 组 | `solution/outputs/scaling/quality_audit.json` | `table_results.B7.negative_group_slopes`; `positive_group_slopes` | PASS：`quality_direction_B7` | DIAGNOSTIC_ONLY_UNRESOLVED | JSON `table_results.B7` |
| `RES-Q2-CONF-003` | Q2 | B8 固定 N,D 组内斜率方向计数 | 150 组为正，0 组为负 | 组 | `solution/outputs/scaling/quality_audit.json` | `table_results.B8.positive_group_slopes`; `negative_group_slopes` | PASS：`quality_direction_B8` | DIAGNOSTIC_ONLY_UNRESOLVED | JSON `table_results.B8` |
| `RES-Q2-CONF-004` | Q2 | B6 与 B7 的匹配联合键数 | 360 | 键 | `solution/outputs/scaling/quality_audit.json` | `overlap[left=B6,right=B7].matching_keys` | PASS：`quality_overlap_B6_B7` | DIAGNOSTIC_ONLY_UNRESOLVED | JSON `overlap` 数组 |
| `RES-Q2-CONF-005` | Q2 | B6 与 B7 完全相同的 Loss 数 | 360 | 键 | `solution/outputs/scaling/quality_audit.json` | `overlap[left=B6,right=B7].exact_same_loss` | PASS：`quality_overlap_B6_B7` | DIAGNOSTIC_ONLY_UNRESOLVED | JSON `overlap` 数组 |
| `RES-Q2-CONF-006` | Q2 | B6 与 B8 的匹配联合键数 | 160 | 键 | `solution/outputs/scaling/quality_audit.json` | `overlap[left=B6,right=B8].matching_keys` | PASS：`quality_overlap_B6_B8` | DIAGNOSTIC_ONLY_UNRESOLVED | JSON `overlap` 数组 |
| `RES-Q2-CONF-007` | Q2 | B6 与 B8 完全相同的 Loss 数 | 0 | 键 | `solution/outputs/scaling/quality_audit.json` | `overlap[left=B6,right=B8].exact_same_loss` | PASS：`quality_overlap_B6_B8` | DIAGNOSTIC_ONLY_UNRESOLVED | JSON `overlap` 数组 |
| `RES-Q2-CONF-008` | Q2 | B6 与 B8 匹配键上的最大绝对 Loss 差 | 2.5769 | Loss 单位 | `solution/outputs/scaling/quality_audit.json` | `overlap[left=B6,right=B8].max_abs_difference` | PASS：`quality_overlap_B6_B8` | DIAGNOSTIC_ONLY_UNRESOLVED：不得取平均掩盖冲突 | JSON `overlap` 数组 |
| `RES-Q2-CONF-009` | Q2 | B8 质量诊断拟合触界参数 | E, k | 参数名 | `solution/outputs/scaling/quality_audit.json` | `table_results.B8.near_bound_parameters` | PASS：`quality_direction_B8` | DIAGNOSTIC_ONLY_UNRESOLVED：不得给问题三使用 | JSON `table_results.B8` |

## 7. 补充登记：首轮线性配比系数表

> 若正文或附录引用该系数矩阵，应整体引用此登记项及其源文件；不得只抄其中若干数字而脱离模型选择与基线边界。

| result_id | problem | description | value | unit | source_file | source_field | verification_status | review_status | source_locator |
|---|---|---|---|---|---|---|---|---|---|
| `RES-Q1-MIX-012` | Q1 | 线性 Scheffé 首轮基线系数矩阵 | 17 行 × 13 个验证域系数 | 模型系数 | `solution/outputs/mixture/linear_coefficients.csv` | `term` 及 13 个 `metric/*_val_loss` 列 | PASS：`mixture_predictions_linear_train_1m` 中系数复算最大绝对误差 `2.6645352591003757e-15` | APPROVED_AS_BASELINE：不得称最终模型或因果效应 | CSV 除表头外全部行与系数列 |

## 8. 存在文件但不得进入已验证结果表的数值

这些文件包含数值或可能被误读为结果，但因来源性质、未完成验证或审查状态不满足条件。若后续论文确需引用，必须先新增审计、在本表中登记，并取得新的审查状态。

| 文件/对象 | 现有性质 | 不得登记/使用的原因 | 当前处置 |
|---|---|---|---|
| `solution/outputs/quality/domain_summary.csv`、`feature_summary.csv`、`normalization.json` | 部分质量产物 | 有效分母未闭合，且合计恒等检查失败；缺行级输出 | 只作审计线索，先修复/重跑并终验 |
| `solution/outputs/scaling/scaling_params.json` 的 `quality_scenario` | `UNVALIDATED_SCENARIO_ONLY` | B6 系数迁移到 B1、A–B Q 映射和 `Q_ref=0.5` 均未实证标定 | 只能在明确情景分析中另加结果 ID；不得写已标定广义律 |
| `solution/outputs/scaling/quality_scenario_predictions.csv` | 情景预测 | 依赖未验证质量迁移和参考点假设 | 保留为源码/产物线索；进入论文前单独核验 |
| `solution/outputs/scaling/external_validation.csv` 中 B2/B3/B4/B5/B10 指标 | 既有外部/迁移计算 | 半合成、插值或口径差异；恢复阶段未全部重拟合或逐项复核 | 需标注来源性质并另建验证；不得作独立真值 |
| `solution/outputs/mixture/observed_training_reference.json` | 训练观测内最小参考 | 不是独立检验或全局最优 | 不得当最终推荐配比 |
| `solution/outputs/mixture/quadratic_*` | 二次模型比较产物 | 未被训练内目标选为首轮主基线 | 可作敏感性比较，但不能替换线性基线或在测试后择优选模 |
| `solution/outputs/mixture/est_*`、A12–A15 | 估算输入/输出 | 不是独立观测真值 | 只可作外推讨论，不可作验证真值 |
| `solution/src/evolution_audit.py` 中的报告模板 | 源码计划文本 | 没有对应运行输出；模板语句不是统计结果 | 不得摘抄为 C 结果 |
| 问三求解目录 | 不存在 | 没有 N、D、Q、p 联合最优解或预算结果 | 问三章节保持 BLOCKED |
| 未来 12/24 个月预测对象 | 不存在 | 没有 C 审计、桥接、时间外检验和不确定性传播 | 不得写任何预测数字或趋势结论 |

## 9. 未完成问题对应的结果占位（无值）

| 问题 | 所需结果 | result_id | value | 当前状态 |
|---|---|---|---|---|
| Q1 | 最终质量分 `Q_A`、方向/冲突规则和文本验证 | 未分配 | PENDING | 无可登记终验结果 |
| Q1 | 含 Q 的配比关系与全局/受约束最优配比 | 未分配 | PENDING | 仅有首轮配比基线 |
| Q2 | 完整 `L(N,D,Q,p)` 参数与验证 | 未分配 | PENDING | p 未接入，Q 未标定 |
| Q2 | 边际效用、弹性和规模/质量替代条件 | 未分配 | PENDING | 完整模型未完成 |
| Q3 | 至少三档预算联合配置与结构转移 | 未分配 | PENDING | 无求解输出 |
| Q4 | C8 逐任务聚合、桥接、贡献分解 | 未分配 | PENDING | 无 C 运行输出 |
| Q4 | 12/24 个月前沿与不确定性 | 未分配 | PENDING | 无可验证预测 |

## 10. 新增结果的强制流程

1. 先保存原始运行 stdout/stderr、退出码、输入哈希、源码版本和输出清单。
2. 从实际文件读取数值，不根据聊天、截图记忆或报告转述填写。
3. 新增唯一 `result_id`，填写值、单位、来源文件、来源字段和定位条件。
4. 由独立核验脚本复算或至少核对来源字段；把核验命令/结果写入 `verification_status`。
5. 在 `review_status` 中明确允许用途和禁止用途，再由论文写作环节引用。
6. 若修订原值，保留旧记录并新增修正记录；不得覆盖历史证据。


## 11. 2026-09-25 Q1/Q2论文冲刺结果映射

问题二正文的正式数值以paper/T06_RESULT_FREEZE.md及其正式集成目录为准；问题一正文数值以Q01C正式科学run和T03E冻结验证为准。正文逐项映射见paper/manuscript/source_map_q1_q2.md。上表早期问题二质量迁移条目若与T06冻结的状态冲突，问题二写作以T06口径为准。


## 12. 2026-09-25 Q3论文冲刺结果映射

问题三正文的三档主结果、KKT/H敏感性、质量成本、配比运输、B8冲突和参数不确定性以paper/T07_RESULT_FREEZE.md及diagnostics/TASK-T07/20260925T113744+08/为准。逐项映射见paper/manuscript/source_map_q3.md。T08尚未执行，问题四继续保留占位。


## 13. 2026-09-25 Q4与最终V1结果映射

问题四正文只使用paper/T05_RESULT_FREEZE.md和paper/T08_RESULT_FREEZE.md。逐项映射见paper/manuscript/source_map_q4.md；全文Claim–Evidence审计见paper/manuscript/FINAL_CLAIM_EVIDENCE_AUDIT.md；全文入口见paper/manuscript/FULL_MANUSCRIPT_V1.md。
