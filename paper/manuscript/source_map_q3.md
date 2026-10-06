# 问题三正文证据映射

> 唯一正式结果口径：paper/T07_RESULT_FREEZE.md。
>
> 正式证据目录：diagnostics/TASK-T07/20260925T113744+08/。本表把问题三正文数值映射到实际CSV、JSON和字段，不使用执行器口头汇报。

## A. 模型、成本、单位与约束

| evidence_id | 正文事实 | 数值/公式 | 来源文件 | 来源字段/行 | 状态 |
|---|---|---|---|---|---|
| Q3-MODEL | 正式主模型 | M0_B1 | diagnostics/TASK-T07/20260925T113744+08/t08_or_paper_interface.json | primary_model | T07冻结 |
| Q3-B1-PARAMS | M0_B1参数 | E=1.6897975629820348; A=0.3539803206065571; B=1.2403055835426349; alpha=0.339976581941082; beta=0.2798781285468448 | diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json | primary_model.parameters | T06合同，T07只读 |
| Q3-COST | 总成本公式与eta | C=6ND+D[g(Q_A)-g(Q0)]_+ + eta*N*D*H; eta=0.0002 | diagnostics/TASK-T07/20260925T113744+08/config/cost_functions.json | cost_equation / eta | T07冻结 |
| Q3-Q0 | A侧质量基线 | 0.5695341857475174 | 同上 | Q0 | T07冻结 |
| Q3-HCRIT | 上下文临界值 | 30000.0 | 同上 | H_crit；unit_conversion_audit.csv formula=H_crit=6/eta | T07冻结 |
| Q3-UNIT | 单位转换 | N_phys=N_B*1e9; D_phys=D_B*1e9 | diagnostics/TASK-T07/20260925T113744+08/unit_conversion_audit.csv | N_physical / D_physical | T07冻结 |
| Q3-SUPPORT | N/D/Q/p支持范围与规则 | N_B[0.070542,11.965825]; D_B[0.134,299.893]; Q_A[0.04888888888888889,0.9805414146077935]; Q_B[0.1,0.6]; p∈[0,1], sum p=1 | diagnostics/TASK-T07/20260925T113744+08/support_bounds.csv | quantity= N_B,D_B,Q_A,Q_B,p | T07冻结 |
| Q3-BUDGETS | 预算集合 | 1e18,1e20,1e22 | diagnostics/TASK-T07/20260925T113744+08/config/budgets.csv | budget_flops | T07冻结 |
| Q3-HSET | H集合 | 2048,4096,8192,32768,131072 | diagnostics/TASK-T07/20260925T113744+08/config/optimization_matrix.csv | H唯一值 | T07冻结 |
| Q3-METHOD | 优化方法 | coarse+multistart+SLSQP；固定Q用KKT约化；不clip | diagnostics/TASK-T07/20260925T113744+08/code/t07_run.py | minimize(...method=SLSQP)；coarse_null/coarse_quality | T07冻结源码 |
| Q3-QP-STATUS | 主模型Q/p状态 | Q=NOT_IDENTIFIED_NOT_OPTIMIZED；p=FIXED_P0_NOT_OPTIMIZED | diagnostics/TASK-T07/20260925T113744+08/budget_scenario_optima.csv | S00行的Q_status/p_status | T07冻结 |

## B. 三档正式主结果与成本分项

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/行 | 状态 |
|---|---|---|---|---|---|
| Q3-MAIN | 三档主表N_B,D_B,Loss | 1e18:0.078248576,1.993850677,3.553996156; 1e20:0.625922700,24.925757775,2.609142026; 1e22:5.202388053,299.893000000,2.143211279 | diagnostics/TASK-T07/20260925T113744+08/budget_scenario_optima.csv | S00_NULL_M0_B1,H=2048,各预算：N_B,D_B,predicted_loss | T07冻结 |
| Q3-COSTS | 三项成本、总成本、Lagrange乘子、KKT | 1e18: compute=9.360958562161432e17,attn=6.390414378435537e16,total=1.0000000000004984e18,lambda=2.861674496588243e-19; 1e20: compute=9.360958562156764e19,attn=6.390414378432351e18,total=1e20,lambda=1.4112576940719197e-21; 1e22: compute=9.360958562156764e21,attn=6.390414378432351e20,total=1e22,lambda=6.86967135433064e-24 | 同上 | S00 rows: compute_cost, attention_cost, total_cost, lagrange_multiplier | T07冻结 |
| Q3-KKT | KKT/边界状态 | KKT residual 1.3638901985160255e-8,2.3597247318359207e-9,0；1e22 active_bounds=[1], D_UPPER; 1e18 H=32768 N_LOWER | kkt_boundary_checks.csv | S00 rows H=2048；context_sensitivity.csv H=32768 | T07冻结 |
| Q3-VERIFY | 数值可行性 | max_relative_budget_violation=9.403629568e-13; max_kkt_residual=2.7932317030401693e-8; max_abs_equality_residual=9.403629568e-13; 39/39 PASS | t08_or_paper_interface.json；verification.json | key_numbers / status | T07冻结 |

## C. 上下文H敏感性

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/行 | 状态 |
|---|---|---|---|---|---|
| Q3-H | H全表 | 见Q3正文表Q3-2，覆盖三种预算×五个H | context_sensitivity.csv | scenario_id=S00_NULL_M0_B1；列N_B,D_B,predicted_loss,active_constraints,H_regime,compute_vs_attention_ratio | T07冻结 |
| Q3-H-CRIT | H临界与结构变化 | H_crit=30000；H<30000为compute-dominant，H>30000为attention-dominant | cost_functions.json；structural_transition_diagnostics.csv | H_crit；transition_dimension=H，active_constraint_set_changed/elasticity_order_changed | T07冻结 |
| Q3-H-1E18-BOUNDARY | 1e18 H=32768 N下界活跃 | N_B=0.070542 | context_sensitivity.csv | S00,1e18,H=32768：N_B,active_constraints | T07冻结 |
| Q3-H-1E22-BOUNDARY | 1e22 H=2048,4096 D上界活跃 | D_B=299.893；H=8192时D转为内点 | context_sensitivity.csv | S00,1e22,H=2048/4096/8192：D_B,active_constraints | T07冻结 |

## D. 三类质量成本情景

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/行 | 状态 |
|---|---|---|---|---|---|
| Q3-GFUN | 三类质量成本函数 | G_EXP=1e7 exp(6Q); G_POWER=5e9 Q^4; G_LOG=2e9 ln(1+10Q) | config/cost_functions.json | functions | T07冻结 |
| Q3-S01 | S01退化质量参考 | Q_A=Q0，Q_B=0.6，quality_cost=0，N/D/Loss与null一致 | quality_cost_sensitivity.csv | scenario_id=S01；budget×cost_function，Q_A/Q_B/quality_cost/N_B/D_B/predicted_loss | T07冻结，SCENARIO_ONLY |
| Q3-S03 | S03非退化质量 | 表Q3-3的全部N/D/Q/Loss/质量成本值 | quality_cost_sensitivity.csv | scenario_id=S03_H1_IDENTITY；三预算×三函数 | T07冻结，SCENARIO_ONLY |
| Q3-S03-ROLE | 三类成本无真实/最优排序 | None selected | quality_cost_sensitivity.csv；config/cost_functions.json | quality_cost_function_selected / selection_rule | T07冻结 |

## E. 配比运输、B8与不确定性

| evidence_id | 正文事实 | 数值 | 来源文件 | 来源字段/行 | 状态 |
|---|---|---|---|---|---|
| Q3-MIXFORMULA | 配比运输修正 | Δp=coeff.mean(axis=0)*(p-p0) | code/t07_run.py | mixture_delta | T07冻结源码 |
| Q3-S14-S16 | 配比情景 | S14/S15 Δp=-0.694347；S16 Δp=0.353477；三预算Loss见正文表Q3-4 | budget_scenario_optima.csv | S14/S15/S16,H=2048：p_mixture_delta,predicted_loss | T07冻结，SCENARIO_ONLY |
| Q3-B8 | B8冲突 | 三预算均NO_NUMERIC_OPTIMUM | budget_scenario_optima.csv | S17,status=NO_NUMERIC_OPTIMUM,reason=DIRECTION_ONLY_NO_NUMERIC_OPTIMUM | T07冻结，CONFLICT |
| Q3-UNC | 参数不确定性 | 80个B1整行draw；N/D/Loss2.5%/50%/97.5%见正文表Q3-5 | uncertainty_summary.csv | S00,三预算，N_B/D_B/Loss分位 | T07冻结 |
| Q3-Q-UNC | 质量情景不确定性 | 200个B1/B6条件整行组合；NOT_JOINT_POSTERIOR | verification.json；uncertainty_summary.csv | quality_200_conditional_draws；uncertainty_label | T07冻结 |
| Q3-NOPROB | 不给情景分配概率、不合并 | None | run_summary.json；t08_or_paper_interface.json | scenario_count/numeric status；qualification | T07冻结 |
