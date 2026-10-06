# 问题四正文证据映射

> 唯一正式接口：paper/T05_RESULT_FREEZE.md、paper/T08_RESULT_FREEZE.md。
> T05正式目录：diagnostics/TASK-T05/20260925T113355+0800/。
> T08正式目录：diagnostics/TASK-T08/20260925T142203+0800/。

## A. 桥接资格与样本

| evidence_id | 正文事实 | 数值/状态 | 来源文件 | 来源字段/行 | 资格 |
|---|---|---|---|---|---|
| Q4-BRIDGE-ELIG | 桥接资格 | CONDITIONAL_ASSOCIATION_ONLY | T05 identifiability_decision.json | final_eligibility | 正式冻结 |
| Q4-C8 | C8完整/partial/损坏 | 1854 / 6 / 4 | T05 run_summary.json | complete_c8_models_available / partial_c8_models_excluded / corrupt_json_files | 正式冻结 |
| Q4-BRIDGE-N | 桥接模型总数/主层/迁移层 | 45 / 7 / 38 | T05 run_summary.json | conditional_full_n / main_sample_n / c6_medium_transfer_rows | 正式冻结 |
| Q4-MODEL | 六任务主模型 | CONSTANT | T05 aggregate_bridge_results.csv | cohort=main_comparable,target九个目标,selected_candidate_id | 正式冻结 |
| Q4-TIMEOUT | 时间外验证 | 5训练/2测试，未通过 | T05 handoff.md；verification.json | time train/test、time_pass | 正式冻结 |
| Q4-FAMILY | 留模型族验证 | 不可识别 | T05 run_summary.json；T08 run_summary.json | main只有一个Pythia族 | 正式冻结 |

## B. 六任务条件基线

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/行 | 资格 |
|---|---|---|---|---|---|
| Q4-VECTOR | 六任务及辅助均值基线与条件区间 | 见Q4正文表Q4-1 | T08 t08_paper_interface.json；taskwise_progress.csv | taskwise_entries；每任务baseline/interval | CONDITIONAL_ASSOCIATION_ONLY |
| Q4-STATUS | 未来进展状态 | 12m/24m均为NOT_IDENTIFIABLE_PROGRESS | T08 taskwise_progress.csv | progress_12m_status/progress_24m_status | 正式冻结 |

## C. 规模/非规模分解

| evidence_id | 正文事实 | 数值/定义 | 来源文件 | 来源字段/行 | 资格 |
|---|---|---|---|---|---|
| Q4-SCALE-DEF | 规模关联项定义 | m_t(x_i)-m_t(x_ref) | T08 run_summary.json；t08_paper_interface.json | main_benchmark.scale_associated_component；allowed_core_conclusions | 正式冻结 |
| Q4-SCALE-ZERO | 49条记录规模关联项 | 0.0，最大值0.0 | T08 scale_non_scale_decomposition.csv | scale_associated_component_mean/max_abs_points | 条件识别结果 |
| Q4-DECOMP | 观测分解恒等 | observed=fitted+conditional_remainder；最大误差3.55e-15 | T08 run_summary.json；scale_non_scale_decomposition.csv | 独立复算字段 | 正式冻结 |
| Q4-REMAINDER | 条件剩余项名称 | non-scale associated residual / conditional remainder | T08 t08_paper_interface.json | allowed_core_conclusions | 正式冻结 |

## D. 历史分层与时间外

| evidence_id | 正文事实 | 数值/状态 | 来源文件 | 来源字段/行 | 资格 |
|---|---|---|---|---|---|
| Q4-STRATA | 历史分层 | 按模型族、规模、开放/许可、时间和任务描述 | historical_strata_summary.csv | stratum_dimension/stratum_value/n_models/n_valid_scores/status | OBSERVED_DESCRIPTION |
| Q4-MISSING | 缺失与损坏 | 6 partial/4 corrupt；不赋分 | missingness_and_denominators.csv；T05 handoff.md | partial_rule/damaged_json_rule | 正式冻结 |
| Q4-TIMEOUT | 切点与失败 | 2024-09-01，5/2，未通过 | T05 t08_bridge_contract.json；verification.json | time_trend.validated_for_extrapolation=false | UNVALIDATED |

## E. 未来情景时点

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/行 | 资格 |
|---|---|---|---|---|---|
| Q4-ORIGIN | 预测原点 | 2025-03-13 | T08 run_summary.json | forecast_origin | 正式冻结 |
| Q4-12M | 12个月情景时点 | 2026-03-13 | T08 forecast_12m_24m_scenarios.csv | forecast_date,horizon_months=12 | SCENARIO_FORECAST |
| Q4-24M | 24个月情景时点 | 2027-03-13 | T08 forecast_12m_24m_scenarios.csv | forecast_date,horizon_months=24 | SCENARIO_FORECAST |
| Q4-GROWTH | 三类年化对数增长率 | NOT_IDENTIFIABLE | T08 run_summary.json | conservative/base/optimistic growth rate | NOT_IDENTIFIABLE |
| Q4-NO-FUTURE-NUM | 未来N/D/Loss/Benchmark增量 | 均无数值预测 | T08 loss_space_scale_scenarios.csv；forecast_12m_24m_scenarios.csv | numeric_output_allowed=False；increment为NOT_IDENTIFIABLE_PROGRESS | 正式冻结 |

## F. Loss空间与不确定性

| evidence_id | 正文事实 | 数值/状态 | 来源文件 | 来源字段/行 | 资格 |
|---|---|---|---|---|---|
| Q4-LOSS-SPACE | Loss空间模型/情景/H | M0_B1 / S00_NULL_M0_B1 / 2048 | T08 run_summary.json | loss_space | 来源内条件模型 |
| Q4-GROWTH-SUPPORT | 历史增长支持 | 7条N/D记录、1族、6个相邻区间、1个有效族级区间；门槛3族/10区间 | T08 run_summary.json | historical_growth_support | NOT_IDENTIFIABLE |
| Q4-CONV | Loss→Benchmark转换次数 | 0 | T08 run_summary.json | loss_to_benchmark_conversion_count | 正式冻结 |
| Q4-UNC | 六类不确定性 | scaling_parameter; bridge_model_error; benchmark_conditional_association; model_family_heterogeneity; time_extrapolation; scenario_structure | T08 forecast_uncertainty.csv；t08_paper_interface.json | component_id | 不合并区间 |
| Q4-COUNT | T08输出行数 | decomposition49；strata931；progress7；forecast42；uncertainty48；loss6；support29 | T08 run_summary.json | output_rows | 正式冻结 |
