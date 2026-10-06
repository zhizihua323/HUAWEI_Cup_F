# TASK-G2 handoff

状态：`COMPLETE_PENDING_CONTROLLER_REVIEW`。

## 结果

- M0_B1五参数逐位冻结，未重拟合、未重选、未clip。
- 来源资格：B2=`VALIDATION_FAILED`，B3=`VALIDATION_SUPPORTED`，B4=`VALIDATION_FAILED`，B5=`VALIDATION_FAILED`，B9=`OOS_STRESS_ONLY`，B10=`ESTIMATED_SCENARIO_ONLY`。
- B3是唯一的`VALIDATION_SUPPORTED`来源，但只是Pythia同源插值轨迹，不是独立外部复制。
- L_gen采用`L0_B1 + rho_Q*Delta_Q(h_s(Q_A)) + tau_p*c^T(p-p0)`的分层联合表达；Q/p、A/B桥接和跨规模配比不得解释为统一联合识别。
- `NEW_Q2_CHANGES_T07_NUMERIC_INPUTS = NO`；未启动增量T07。

## 独立验证

verifier未导入执行模块；预测、支持状态、来源/簇指标、聚类bootstrap、解析示例和T06/T07哈希全部复算，结果`55/55 PASS`。

## 证据入口

- `run_summary.json`、`checks.json`、`verification.json`
- `validation_metrics_by_source.csv`、`systematic_bias_audit.csv`
- `large_model_gt10b_audit.csv`
- `generalized_law_spec.json`、`derivatives_elasticities_and_substitutions.md`
- `p_q_double_counting_audit.json`、`t07_impact_decision.json`
- 候选接口：`paper/Q2_GAP_RESULT_FREEZE.md`

## 边界

本run不关闭Q2、不修改00–05/论文正文、不重跑T07，也不把B9/B10估算升级为真值。
