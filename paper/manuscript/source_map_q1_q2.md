# Q1/Q2 正文证据映射

> 用途：为 paper/manuscript/Q1_Q2_STABLE_BODY.md 中的每个数值和关键状态提供实际文件定位。
>
> 问题二正式口径以 paper/T06_RESULT_FREEZE.md 和 diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/ 下的集成证据为准。问题一主体结果以 solution/outputs/quality_q01c/20260924T215718+08/ 与 diagnostics/TASK-T03E/20260925T020032+08/ 的冻结验证为准。未冻结内容不进入正文数值。

## A. 数据清单与质量分母

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/位置 | 状态 |
|---|---|---:|---|---|---|
| DATA-A1 | A1记录数 | 51230 | solution/outputs/quality_q01c/20260924T215718+08/audit.json | per_file.A1.rows | 冻结 |
| DATA-A2 | A2记录数 | 17523 | 同上 | per_file.A2_arxiv.rows | 冻结 |
| DATA-A3 | A3记录数 | 203752 | 同上 | per_file.A3_github.rows | 冻结 |
| DATA-TOTAL | 物理记录总数 | 272505 | 同上 | total_records | 冻结 |
| DATA-UNIQUE | 唯一键数 | 261086 | 同上 | unique_id_sub_path_keys | 冻结 |
| DATA-DUP | 重复出现数 | 11419 | 同上 | duplicate_occurrences | 冻结 |
| DATA-OVER-A1A2 | A1/A2 arxiv重叠 | 1419 | 同上 | pairwise_key_intersections.A1__A2_arxiv | 冻结 |
| DATA-OVER-A1A3 | A1/A3 github重叠 | 10000 | 同上 | pairwise_key_intersections.A1__A3_github | 冻结 |
| DATA-OVER-A2A3 | A2/A3重叠 | 0 | 同上 | pairwise_key_intersections.A2_arxiv__A3_github | 冻结 |
| DATA-FEAT | 原始质量字段/展开标量/主特征数 | 22 / 25 / 11 | 同上 | raw_quality_fields / expanded_scalar_features / main_q_features | 冻结 |
| DATA-MISS | 主Q有效/无效物理记录数 | 272486 / 19 | 同上 | q_valid_true / q_valid_false | 冻结 |
| DATA-UNIQUE-MISS | 唯一记录主Q有效/缺失数 | 261067 / 19 | solution/outputs/quality_q01c/20260924T215718+08/domain_summary.csv | scope=all_unique, domain=ALL 的 n_Q_valid/n_Q_missing | 冻结 |
| DATA-COV | all_unique主Q覆盖率 | 0.9999272270439625 | 同上 | coverage | 冻结 |

## B. 问题一质量结果与敏感性

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/位置 | 状态 |
|---|---|---:|---|---|---|
| Q1-MEAN | all_unique主Q均值 | 0.4959665403209771 | solution/outputs/quality_q01c/20260924T215718+08/domain_summary.csv | scope=all_unique,domain=ALL,Q_mean | 冻结科学结果 |
| Q1-STD | all_unique主Q标准差 | 0.14955387815663584 | 同上 | Q_std | 冻结科学结果 |
| Q1-MED | all_unique主Q中位数 | 0.48247852816491466 | 同上 | Q_median | 冻结科学结果 |
| Q1-P10 | all_unique主Q 10%分位 | 0.32164589603454746 | 同上 | Q_p10 | 冻结科学结果 |
| Q1-P90 | all_unique主Q 90%分位 | 0.681334413298976 | 同上 | Q_p90 | 冻结科学结果 |
| Q1-GROUP-U | usability组均值/有效n | 0.603019195964164 / 261086 | 同上 | group_usability_mean / group_usability_effective_n | 冻结科学结果 |
| Q1-GROUP-K | knowledge组均值/有效n | 0.5341024804018979 / 261080 | 同上 | group_knowledge_mean / group_knowledge_effective_n | 冻结科学结果 |
| Q1-GROUP-R | education_reasoning组均值/有效n | 0.3507774096831335 / 261073 | 同上 | group_education_reasoning_mean / group_education_reasoning_effective_n | 冻结科学结果 |
| Q1-DIS-MEAN | 平均组间分歧范围 | 0.3030181779626825 | 同上 | rater_disagreement_mean | 冻结诊断 |
| Q1-DIS-FRAC | 组间范围>0.5比例 | 0.06342737642003018 | 同上 | rater_disagreement_gt_0_5_fraction | 冻结诊断 |
| Q1-QA-STAR | A1校准七域等权锚点 | 0.5695341857475174 | diagnostics/TASK-T06E-P/20260925T075729+08/quality_anchor/q_A_anchor.json | q_A_star | T06冻结 |
| Q1-QC-RULE | 规则敏感性公式 | Q_C=Q_baseline(1−0.02P), P=(p2+p3)/2 | diagnostics/TASK-T03E/20260925T020032+08/phase_a_calibration_freeze/frozen_primary_spec.json | primary_result / candidate_formula / cluster_definition / lambda_primary | T03E冻结 |
| Q1-QC-ACTIVE | 活跃域 | c4, commoncrawl, wikipedia | 同上 | active_domains | T03E冻结 |
| Q1-QC-C4 | c4留出验证 | n=1959, Spearman=0.9999883272381607, Jaccard=1.0, 平均罚项绝对差=0.0046029844992003, OOS=0.006636038795303726 | diagnostics/TASK-T03E/20260925T020032+08/phase_b_frozen_validation/holdout_summary.json | per_domain[domain=c4] | T03E冻结 |
| Q1-QC-CC | commoncrawl留出验证 | n=1948, Spearman=0.9999688802130032, Jaccard=0.9897959183673469, 平均罚项绝对差=0.003167884968536889, OOS=0.014373716632443531 | 同上 | per_domain[domain=commoncrawl] | T03E冻结 |
| Q1-QC-WIKI | wikipedia留出验证 | n=1973, Spearman=0.999982999217464, Jaccard=1.0, 平均罚项绝对差=0.0008853537485004649, OOS=0.008109477952356817 | 同上 | per_domain[domain=wikipedia] | T03E冻结 |
| Q1-QC-EXT | 扩展主动修正状态 | NOT_TESTED_FOR_ACTIVE_CORRECTION | diagnostics/TASK-T03E/20260925T020032+08/handoff.md | Extension状态 | T03E冻结 |

## C. 问题一配比结果

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/位置 | 状态 |
|---|---|---:|---|---|---|
| MIX-N | 1M训练/1M检验/60M检验/1B检验/10B估算/70B估算行数 | 512 / 256 / 256 / 64 / 63 / 63 | diagnostics/TASK-T06E-P/20260925T075729+08/mixture_audit/regmix_fixed_model_validation.csv | n列按scale筛选 | T06冻结 |
| MIX-1M-MSE | 1M相对域训练均值MSE改善 | 0.5502593290109576 | 同上 | scale=test_1m，mse_improvement_vs_domain_training_mean | T06冻结 |
| MIX-1M-RHO | 1M逐域等权Spearman | 0.6250743877317463 | 同上 | scale=test_1m，spearman_equal_domain_mean | T06冻结 |
| MIX-60M-RMSE | 60M逐域等权RMSE | 1.5173310791562076 | 同上 | scale=test_60m，rmse_equal_domain_mean | T06冻结，运输诊断 |
| MIX-1B-RMSE | 1B逐域等权RMSE | 3.188945347793164 | 同上 | scale=test_1B，rmse_equal_domain_mean | T06冻结，运输诊断 |
| MIX-COEF | 冻结线性配比系数矩阵 | 17行×13验证域系数 | solution/outputs/mixture/linear_coefficients.csv | term与13个metric/*_val_loss列 | T06复用，未重拟合 |
| MIX-MAP | 质量映射域数/未映射域数 | 6 / 11 | diagnostics/TASK-T06E-P/20260925T075729+08/mixture_audit/stage_summary.json | mapped_domain_count / unmapped_domain_count | T06冻结 |
| MIX-QP-RANK | p设计与加入Q_mix后的秩 | 17 / 17 | diagnostics/TASK-T06E-P/20260925T075729+08/run_summary.json | p_Q_double_counting.design_rank / augmented_rank | T06冻结 |
| MIX-QP-RES | Q_mix投影相对残差 | 9.368877196481023e-16 | 同上 | p_Q_double_counting.relative_projection_residual | T06冻结 |

## D. 问题二正式主模型

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/位置 | 状态 |
|---|---|---:|---|---|---|
| Q2-B1-PARAMS | M0_B1参数 | E=1.6897975629820348; A=0.3539803206065571; B=1.2403055835426349; alpha=0.339976581941082; beta=0.2798781285468448 | diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json | primary_model.parameters | T06冻结 |
| Q2-B1-CI | M0_B1条件重采样2.5%/97.5% | 见正文表Q2-1 | diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_parameter_table.csv | module=M0_B1，p2_5/p97_5 | T06冻结 |
| Q2-B1-SUPPORT | N_B/D_B支持范围 | N_B 0.070542—11.965825; D_B 0.134—299.893 | diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json | support.B1_N_B / support.B1_D_B | T06冻结 |
| Q2-MQ-ADD-PARAMS | MQ-add参数 | E_6=1.576717897667643; A_6=0.6003432829036089; B_6=1.3555803863625686; alpha_6=0.2721341490204682; beta_6=0.2912041980912658; k_add=0.3544081081063713 | diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_parameter_table.csv | module=MQ_add_B6 | T06冻结 |
| Q2-G1 | 质量方向门槛 | 43/45组为负，2组为正，负比例0.9555556 | diagnostics/TASK-T06E-B-R1/20260925T103130+08/corrected_gates/G1_G4_reconciliation.json | G1 | T06冻结 |
| Q2-G2-N | leave-N宏RMSE与改善 | 0.0791586657229001→0.0529372278724645，相对改善0.3312516401201782 | 同上 | G2.leave_N | T06冻结 |
| Q2-G2-D | leave-D宏RMSE与改善 | 0.0818619439862219→0.0553287699778896，相对改善0.3241209860933431 | 同上 | G2.leave_D | T06冻结 |
| Q2-G3 | 重采样稳定性 | 成功200/200，方向一致200/200 | 同上 | G3 | T06冻结 |
| Q2-G4 | 数值识别性 | 6/6满秩，条件数53.94407500777401，六个profile有限分离且不触边 | 同上 | G4_corrected | T06冻结 |
| Q2-MQ-EFF | MQ-eff eta | 1.0000000000000025e-06，触下界 | diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json | quality.MQ_eff.eta / eta_at_lower_bound | T06冻结 |
| Q2-BRIDGE | A/B桥接状态 | NOT_IDENTIFIABLE | 同上 | quality.A_B_mapping_status | T06冻结 |
| Q2-H | H0—H4状态与情景定义 | H0无映射零模型；H1：h(q)=q；H2：h(q)=0.6+b(q−q_A*), b∈{0.5,1,2}；H3：h(q)=F_B^(−1)(F_A(q))；H4仅方向 | 同上 | quality.bridges；diagnostics/TASK-T06E-P/20260925T075729+08/bridge/quality_bridge_scenarios.json | T06冻结 |
| Q2-B6-SUPPORT | B6确认质量范围 | Q_score≤0.6（设计水平最小值0.1） | diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json | support.B6_Q_score_confirmatory | T06冻结 |
| Q2-B8 | B8角色 | CONFLICT_EVIDENCE | 同上 | quality.B8 | T06冻结 |

## E. 图表占位符

图表本身不是计算证据。所有拟用图表必须回到对应源数据，并由 figure_table_placeholders_q1_q2.md 管理。
