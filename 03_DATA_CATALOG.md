# 数据与产物目录

> 恢复登记时间：2026-09-24T13:32:13+08:00（Asia/Shanghai）。最近更新：2026-09-25。T08正式run已验收并关闭；四问科学结果均有冻结接口，下一阶段为论文最终整合。


## 原始材料与清点口径

原始题目/说明：`F题/算力约束下提升大语言模型能力的资源配置建模.docx`、`F题/数据说明.pdf`。桌面阅读包、根目录附件1–4及参考模板见00。历史阅读缓存和格式扫描见 `tmp/environment_review/工作环境熟悉记录.md`、`inventory.json`、`xz_scan.json`、各文档TXT；它们是历史检查记录，非本轮重新全量解析结果。

本轮确认 `F题/real_attachments/` 2012个文件、551191693字节，与 `solution/outputs/audit/raw_source_manifest.csv` 的路径及大小逐个一致；全部41个原始CSV的SHA256一致。XZ、C8全部JSON及Parquet只核对存在/大小，本轮未全部重哈希或重新解码。三份质量XZ的质量审计SHA与旧清单相同，只说明两份旧记录一致。

历史环境记录的2028个“原始工作区文件”包含题目、说明及参考材料，不是当前包含solution/tmp/recovery后的文件总数；不能混用口径。40个编号是逻辑数据集，不等于40个文件。下表来自已存在的 `dataset_registry.csv`；每项性质是资料口径，不是独立来源认证。

|编号|原始路径（相对F题/real_attachments）|说明文件中的性质|文件数|字节|
|---|---|---|---:|---:|
|A1|`A_data_value/slimpajama_quality_signal_sample.jsonl.xz`|observed|1|103349792|
|A2|`A_data_value/slimpajama_quality_extended/arxiv_*.jsonl.xz`|observed|1|3652724|
|A3|`A_data_value/slimpajama_quality_extended/github_*.jsonl.xz`|observed|1|37618172|
|A4|`A_data_value/regmix_tables/train_mixture_1m.csv`|observed|1|46412|
|A5|`A_data_value/regmix_tables/train_pile_loss_1m.csv`|observed|1|121898|
|A6|`A_data_value/regmix_tables/test_mixture_1m.csv`|observed|1|23537|
|A7|`A_data_value/regmix_tables/test_pile_loss_1m.csv`|observed|1|61175|
|A8|`A_data_value/regmix_tables/test_mixture_60m.csv`|observed|1|23537|
|A9|`A_data_value/regmix_tables/test_pile_loss_60m.csv`|observed|1|61827|
|A10|`A_data_value/regmix_tables/test_mixture_1B.csv`|observed|1|6393|
|A11|`A_data_value/regmix_tables/test_pile_loss_1B.csv`|observed|1|10639|
|A12|`A_data_value/regmix_tables/est_mixture_10b.csv`|training_subset|1|6113|
|A13|`A_data_value/regmix_tables/est_pile_loss_10b.csv`|estimated|1|6467|
|A14|`A_data_value/regmix_tables/est_mixture_70b.csv`|training_subset|1|6113|
|A15|`A_data_value/regmix_tables/est_pile_loss_70b.csv`|estimated|1|6467|
|A16|`A_data_value/domain_mapping_guide.csv`|reference_mapping|1|1296|
|A17|`A_data_value/regmix_domain_summary.csv`|observed_summary|1|1265|
|A18|`A_data_value/regmix_domain_sample.jsonl.xz`|observed_text|1|165293312|
|B1|`B_scaling_laws/pythia_training_log_existing.csv`|observed|1|111459|
|B2|`B_scaling_laws/cerebras_training_log.csv`|semisynthetic|1|89643|
|B3|`B_scaling_laws/training_trajectories/*.csv`|interpolated|8|112320|
|B4|`B_scaling_laws/scaling_baseline.csv`|published_observed|1|1421|
|B5|`B_scaling_laws/published_scaling_data.csv`|published_observed|1|1967|
|B6|`B_scaling_laws/supplementary_NQ_experiment.csv`|semisynthetic|1|13670|
|B7|`B_scaling_laws/supplementary_NQ_experiment_expanded.csv`|semisynthetic|1|17154|
|B8|`B_scaling_laws/supplementary_NQ_experiment_large.csv`|semisynthetic_with_extrapolation|1|81268|
|B9|`B_scaling_laws/supplementary_large_models.csv`|reported_metadata|1|13400|
|B10|`B_scaling_laws/supplementary_large_baseline.csv`|estimated|1|4744|
|B11|`B_scaling_laws/open_model_family_metadata.csv`|metadata|1|1975|
|B12|`B_scaling_laws/pythia_checkpoint_index.csv`|metadata|1|117698|
|C1|`C_efficiency_evolution/leaderboard_cleaned.csv`|observed|1|1011558|
|C2|`C_efficiency_evolution/leaderboard_enhanced.csv`|observed_plus_metadata_matching|1|1036749|
|C3|`C_efficiency_evolution/leaderboard_extended_timeseries.csv`|mixed|1|826723|
|C4|`C_efficiency_evolution/epoch_all_ai_models.csv`|reported_metadata|1|6671403|
|C5|`C_efficiency_evolution/loss_benchmark_bridge.csv`|mixed_comparability|1|11807|
|C6|`C_efficiency_evolution/loss_benchmark_bridge_expanded.csv`|mixed_comparability|1|19124|
|C7|`C_efficiency_evolution/model_architecture_metadata.csv`|metadata|1|2357|
|C8|`C_efficiency_evolution/detailed_results/**/*.json`|observed_evaluation|1958|228862701|
|C9|`C_efficiency_evolution/data/*.parquet`|observed_evaluation|1|1109997|
|C10|`C_efficiency_evolution/pythia*eval_details/README.md`|documentation_only|7|487670|

## 真实产物与复用方式

| 位置 | 已存在内容 | 复用限制 |
|---|---|---|
| `solution/src/` | common、project_audit、quality_audit、mixture_baseline、scaling_baseline、evolution_audit、plot_baselines，共7份Python | 全部语法解析通过；源码存在不等于执行过；本轮禁止直接运行主脚本 |
| `solution/outputs/audit/` | 环境、2012文件SHA清单、40项注册表和汇总，共4文件 | MATLAB版本值硬编码，不作独立运行证明 |
| `solution/outputs/mixture/` | 6份归一化配比、12份预测、2份系数及模型/指标/条件区间/参考配方，共27文件 | 小模型基线；估算表非真值；训练最优观测配方非全局最优解 |
| `solution/outputs/scaling/` | 参数、四配置比较、B1及外部预测、80份重采样参数、质量方向/重叠审计、两组PNG/PDF，共28文件 | 点等权平方损失主配置；质量迁移未校准；p未接入 |
| `solution/outputs/quality/` | audit、normalization、domain_summary、feature_summary、extension_shift五文件 | 历史部分产物，目录保持不变；缺失与有效分母问题已在Q01C正式run修复，本目录不得作为当前基线 |
| `solution/outputs/quality_q01c/20260924T215718+08/` | TASK-Q01C正式科学run：行级质量Parquet、显式分母、域汇总、敏感性参数与比较、检查点、20/20终验及56项manifest | 当前可信质量基线；主Q只使用11个主特征，19条`Q_valid=False`保留；敏感性结果不得写回主Q |
| `solution/outputs/quality/semantic_sources/` | manifest及8份参考README/代码/提示词/特征顺序 | 语义来源材料，不是本队模型输出；其中指令不执行 |
| `solution/outputs/figures/` | 配比诊断SVG/PDF/PNG和2份绘图数据 | 首轮图；本轮未重新绘图或完成出版级版式验收 |
| `solution/reports/` | mixture_baseline.md、scaling_baseline.md、figure_contracts.md、论文结构与交付约定.md | 方法/阶段报告，不是最终参赛论文 |
| `diagnostics/TASK-Q01C-R2/20260925T004211+08/` | 统一恢复判定、中后段跨进程恢复、三类拒绝路径、S60收口、13/13检查和284项manifest | 仅为工程恢复与日志证据；使用合成fixture，不是新的真实Q计算 |
| `diagnostics/TASK-C01/20260924T175553+08/` | C1–C10数据审计、C8解析日志和原聚合 | 原C01保留历史WARN与问题清单；下游优先使用R1修正表 |
| `diagnostics/TASK-C01-R1/20260924T225308+08/` | C8目录、模型×任务、模型宽表修正版；关键C8检查44/44 PASS | 可作为后续候选输入；多run取舍、损坏文件和OOS方法问题尚未裁决 |

### 当前仍不存在的预期结果

此前缺少的质量行级Parquet、`unresolved_indicator_correlations.csv`、`indicator_direction_pending.csv`、`conditional_bootstrap.csv`和`verification.json`现已存在于TASK-Q01C正式科学run中；历史`solution/outputs/quality/`目录仍保持不变，不作为当前正式质量基线。未发现`list_field_audit.csv`，但它不是Q01C验收要求中的必需产物。质量报告位于正式run的`quality_baseline_q01c.md`，尚未整理为最终参赛论文正文。

`solution/outputs/evolution/`目录和`solution/reports/evolution_baseline.md`仍不存在；正式问题四结果改由T05/T08诊断目录承载。Loss–Benchmark条件桥接、规模/非规模分解和未来情景资格均已产生并冻结。问三优化结果已由T07产生并冻结，但尚无完整论文定稿和提交包。

### Q01C正式质量产物

- 正式目录：`solution/outputs/quality_q01c/20260924T215718+08/`；`output_manifest.json`登记56项，本次主控复核56/56匹配。
- 行级主表：`quality_features_scores.parquet`，272505条物理记录全部保留；主Q有效272486、无效19。唯一键261086个，其中主Q有效261067、无效19。
- 汇总与分母：`domain_summary.csv`、`summary_denominators.csv`、`feature_summary.csv`、`extension_shift.csv`。所有scope/domain按`Q_valid`显式报告覆盖字段。
- 敏感性证据：`imputation_parameters_sensitivity.json`、`imputation_applied_counts.csv`、`sensitivity_domain_summary.csv`、`sensitivity_comparison.csv`。参数只来自A1 calibration对应域/特征；无holdout、extension、global或其他域fallback。
- 工程证据：`checks.json`、`verification.json`、`checkpoint_manifest.json`、`stage_status.jsonl`、`run_summary.json`和`code_snapshot/`。科学run保留历史主命令缺失限制。

### Q01C-R2工程补证

- 正式目录：`diagnostics/TASK-Q01C-R2/20260925T004211+08/`；当前manifest 284/284匹配，manifest之后无登记文件继续修改。
- 合成跨进程run：`midstage_interruption/midstage_run/`，其manifest 66/66匹配。P1=14452在S30完成后终止，P2=15776复用S10至S30并完成S40/S50/S60。
- 三类拒绝证据：`rejection_tests/payload_hash/`、`config_mismatch/`、`code_fingerprint/`；正常`--resume`和probe均非零退出，检查点未被覆盖，新增计算为0。
- R2未读取、stat、hash、扫描或解压真实A1–A3；该结论的证据等级是fixture路径隔离和代码/命令审计，不是对真实文件的探测。

### C01-R1修正候选输入

- `c8_directory_aggregate_corrected.csv`：1863个目录，明确区分文件总数、解析成功、解析失败及有限结果数；四个损坏目录均传播。
- `c8_model_task_aggregate_corrected.csv`：11160个模型×任务键，11135个有有限结果、25个零结果，`n_valid_results`合计11699。
- `c8_model_wide_corrected.csv`：1860个模型；1854个六任务完整，6个partial；`six_task_mean_complete_only`仅对完整模型有限，partial使用明确命名的`partial_task_mean`。
- 原始C8事实为1958份JSON、1954成功、4失败、11724槽位、11699有限和25缺失。95个双文件目录取舍等OOS问题仍未裁决，因此修正表是候选输入而非最终建模口径决定。

### T03E正式质量候选与T06接口

正式run：`diagnostics/TASK-T03E/20260925T020032+08/`。

- `candidate_Q_scores.parquet`：272505条物理记录，保留正式Q01C身份、`Q_baseline`和`Q_valid`；新增`Q_C`、P、两个簇分量和支持状态。19条`Q_valid=False`记录的D/C均为NaN。
- `t06_quality_interface.parquet`与`t06_quality_interface.json`：供T06使用的质量侧候选接口，同时保存D、C、三维DSIR向量、域/角色/唯一键、覆盖字段及识别性限制；不得把C解释为正式Q。
- `phase_a_calibration_freeze/`：calibration门禁、固定阈值、200次逐域bootstrap、验收门槛、源码快照、freeze manifest和seal。
- `phase_b_frozen_validation/`：冻结后的holdout、extension overlap/new及RegMix/Loss识别性结果。
- `checks.json`：22 PASS、1 NOT_CHECKED；EX-23由最终独立finalizer和主控哈希复核覆盖。
- `verification.json`：独立验收17/17 PASS，验收器没有导入执行模块。
- `output_manifest.json`：最终正式manifest为2026-09-25T02:00:56+08:00生成的53项版本；当前53/53路径、大小、SHA256一致，生成后无登记文件改写。

字段语义修正：`rps_doc_frac_chars_top_2gram`和`rps_doc_frac_chars_top_3gram`只能登记为“来源给出的top word n-gram字符集中度数值”；来源未说明百分数或理论尺度，状态为`THEORETICAL_SCALE_NOT_VERIFIED`。正式经验值明显非`[0,1]`，论文和后续数据字典不得继续写`[0,1]`，也不得自行写成`[0,100]`。

历史run `diagnostics/TASK-T03E/20260925T015757+08/`与`diagnostics/TASK-T03E/20260925T015930+08/`标记为`SUPERSEDED`并只读保留。其候选Parquet和冻结阈值与正式run一致；后续重新生成的manifest及append-only日志属于历史交付封装变更，没有改变冻结科学包。

### 本轮恢复证据

- `recovery/2026-09-24/solution_inventory.csv`：恢复前solution每个文件的路径、字节、mtime、SHA256。
- `recovery/2026-09-24/parsed_outputs.csv`：实际读通的64份JSON/CSV产物及结构。
- `recovery/2026-09-24/verification.json`：68项轻量核验及65通过/3失败明细，含复算配比指标。
- `recovery/2026-09-24/quality_gap_evidence.json`、`quality_missing_feature_counts.csv`、`quality_mean_discrepancies.csv`：新发现的质量缺失/分母证据。
- `recovery/2026-09-24/problem_text_from_docx.txt`：从原始题目DOCX只读提取，公式保真需回看Word。
- `recovery/2026-09-24/recover_verify.py`、`inspect_quality_gap.py`：本轮实际执行的只读核验脚本。
- `recovery/2026-09-24/write_recovery_docs.py`：文档生成脚本；后续手工维护文档后不要直接重跑，以免覆盖更新。

### 现存模型输出逐文件清单

下列路径逐项存在，内容是否可采纳仍以状态表和核验日志为准。完整时间及哈希在上述清单中。

- `solution/outputs/audit/dataset_registry.csv`
- `solution/outputs/audit/environment.json`
- `solution/outputs/audit/manifest_summary.json`
- `solution/outputs/audit/raw_source_manifest.csv`
- `solution/outputs/figures/mixture_baseline_diagnostics.pdf`
- `solution/outputs/figures/mixture_baseline_diagnostics.png`
- `solution/outputs/figures/mixture_baseline_diagnostics.svg`
- `solution/outputs/figures/mixture_rank_source.csv`
- `solution/outputs/figures/mixture_scatter_source.csv`
- `solution/outputs/mixture/aggregate_predictions.csv`
- `solution/outputs/mixture/audit.json`
- `solution/outputs/mixture/domain_metrics.csv`
- `solution/outputs/mixture/est_10b_normalized_mixtures.csv`
- `solution/outputs/mixture/est_70b_normalized_mixtures.csv`
- `solution/outputs/mixture/linear_coefficients.csv`
- `solution/outputs/mixture/linear_est_10b_predictions.csv`
- `solution/outputs/mixture/linear_est_70b_predictions.csv`
- `solution/outputs/mixture/linear_test_1B_predictions.csv`
- `solution/outputs/mixture/linear_test_1m_predictions.csv`
- `solution/outputs/mixture/linear_test_60m_predictions.csv`
- `solution/outputs/mixture/linear_train_1m_predictions.csv`
- `solution/outputs/mixture/metrics.csv`
- `solution/outputs/mixture/model.json`
- `solution/outputs/mixture/observed_training_reference.json`
- `solution/outputs/mixture/quadratic_coefficients.csv`
- `solution/outputs/mixture/quadratic_est_10b_predictions.csv`
- `solution/outputs/mixture/quadratic_est_70b_predictions.csv`
- `solution/outputs/mixture/quadratic_test_1B_predictions.csv`
- `solution/outputs/mixture/quadratic_test_1m_predictions.csv`
- `solution/outputs/mixture/quadratic_test_60m_predictions.csv`
- `solution/outputs/mixture/quadratic_train_1m_predictions.csv`
- `solution/outputs/mixture/test_1B_normalized_mixtures.csv`
- `solution/outputs/mixture/test_1m_conditional_intervals.json`
- `solution/outputs/mixture/test_1m_normalized_mixtures.csv`
- `solution/outputs/mixture/test_60m_normalized_mixtures.csv`
- `solution/outputs/mixture/train_1m_normalized_mixtures.csv`
- `solution/outputs/quality/audit.json`
- `solution/outputs/quality/domain_summary.csv`
- `solution/outputs/quality/extension_shift.csv`
- `solution/outputs/quality/feature_summary.csv`
- `solution/outputs/quality/normalization.json`
- `solution/outputs/scaling/all_fits.json`
- `solution/outputs/scaling/B10_predictions.csv`
- `solution/outputs/scaling/B1_all_predictions.csv`
- `solution/outputs/scaling/B1_compute_audit.csv`
- `solution/outputs/scaling/B1_precision_residual_audit.json`
- `solution/outputs/scaling/B2_compute_audit.csv`
- `solution/outputs/scaling/B2_predictions.csv`
- `solution/outputs/scaling/B3_predictions.csv`
- `solution/outputs/scaling/B4_predictions.csv`
- `solution/outputs/scaling/B5_predictions.csv`
- `solution/outputs/scaling/B7_novel_grid_predicted_from_B6.csv`
- `solution/outputs/scaling/B9_compute_audit.csv`
- `solution/outputs/scaling/cluster_bootstrap_parameters.csv`
- `solution/outputs/scaling/external_validation.csv`
- `solution/outputs/scaling/model_comparison.csv`
- `solution/outputs/scaling/quality_audit.json`
- `solution/outputs/scaling/quality_B6_validation.csv`
- `solution/outputs/scaling/quality_direction_audit.pdf`
- `solution/outputs/scaling/quality_direction_audit.png`
- `solution/outputs/scaling/quality_scenario_predictions.csv`
- `solution/outputs/scaling/quality_within_ND_slopes.csv`
- `solution/outputs/scaling/residual_diagnostics.csv`
- `solution/outputs/scaling/scaling_fit_residuals.pdf`
- `solution/outputs/scaling/scaling_fit_residuals.png`
- `solution/outputs/scaling/scaling_params.json`
- `solution/outputs/scaling/table_audit.json`
- `solution/outputs/scaling/table_audit_summary.csv`
- `solution/outputs/scaling/validation_by_model.csv`

## TASK-T06正式产物

- `diagnostics/TASK-T06E-B/20260925T100306+08/`：B1/B6主拟合、折分、bootstrap、B7新增90点和B8冲突审计。原run的profile/G4结论保留为历史，不直接作为最终科学裁决。
- `diagnostics/TASK-T06E-B-R1/20260925T103130+08/`：profile物理坐标和MQ-add专属G4修正；86项manifest当前匹配，22/22全拟合点复现，MQ-add最终来源内通过。
- `diagnostics/TASK-T06E-P/20260925T075729+08/`：七域等权q_A锚点、H0–H4、RegMix运输审计、p–Q识别性与21情景seal；49项manifest当前匹配。
- `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/`：主控集成。核心接口为`t07_model_contract.json`、`t07_parameter_table.csv`、`scenario_registry_filled.csv`、`scenario_predictions.parquet`；独立验证21/21 PASS，manifest 23/23匹配。
- `paper/T06_RESULT_FREEZE.md`：问题二唯一论文冻结口径。
- `tasks/TASK-T07_算力约束下资源配置联合优化.md`、`tasks/TASK-T05_Loss-Benchmark桥接与历史分层验证.md`：已执行施工单；正式结果见下列T07/T05条目。

## TASK-T07与TASK-T05正式产物

- `diagnostics/TASK-T07/20260925T113744+08/`：问三预算×情景优化正式run。核心表为`budget_scenario_optima.csv`、`optimization_results.parquet`、`kkt_boundary_checks.csv`、`context_sensitivity.csv`、`quality_cost_sensitivity.csv`、`parameter_draw_optima.parquet`和`uncertainty_summary.csv`；独立验证39/39 PASS，output manifest 39/39当前匹配。
- `paper/T07_RESULT_FREEZE.md`：问题三唯一论文冻结口径。
- `diagnostics/TASK-T05/20260925T113355+0800/`：Loss–Benchmark桥接正式run。核心表为`bridge_analysis_dataset.parquet`、`split_registry.csv`、`taskwise_bridge_results.csv`、`residual_audit.csv`、`identifiability_decision.json`和`t08_bridge_contract.json`；独立验证28/28 PASS，output manifest 34/34当前匹配。
- `paper/T05_RESULT_FREEZE.md`：T08及论文问题四的桥接边界冻结口径。
- `tasks/TASK-T08_规模与非规模进步分解及未来情景预测.md`：已执行施工单；正式结果见下列T08条目。

## TASK-T08正式产物与最终论文索引

- `diagnostics/TASK-T08/20260925T142203+0800/`：问题四正式run。核心表为`scale_non_scale_decomposition.csv`、`historical_strata_summary.csv`、`taskwise_progress.csv`、`forecast_12m_24m_scenarios.csv`、`forecast_uncertainty.csv`及`loss_space_scale_scenarios.csv`；独立验证32/32 PASS，manifest 38/38当前匹配。
- `paper/T08_RESULT_FREEZE.md`：问题四唯一正式冻结口径。
- `paper/FINAL_RESULT_INDEX.md`：执行-PAPER唯一科学结果入口，索引T06/T07/T05/T08四份冻结接口和现有Q1–Q3稳定正文。
