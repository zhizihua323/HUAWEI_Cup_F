# TASK-G2：Q2广义标度律与强制验证闭合

日期：2026-09-25。状态：正式执行施工单，`GAP_CLOSURE`，优先级P0。本任务与TASK-G1、TASK-G4、TASK-PAPER-PREFLIGHT相互独立。执行器只提交`COMPLETE_PENDING_CONTROLLER_REVIEW`或`STOPPED_WITH_EVIDENCE`，不得自行关闭Q2或改动T07。

## 【任务目标】

1. 使用冻结的`M0_B1`完成原题强制要求的B2/B3、B4/B5及B9/B10验证与外推审计；
2. 在不伪造统一可识别性的前提下，形成一个可正式写入论文的“分层估计、联合表达”广义标度律`L_gen(N,D,Q,p)`；
3. 明确新结果是否改变T07数值输入。

## 【上位依据】

- 原题附录A的问题二数据要求；
- `tasks/TASK-T06_尺度桥接识别性与广义缩放律方法裁决.md`
- `paper/T06_RESULT_FREEZE.md`
- `diagnostics/TASK-T06E-B-R1/20260925T103130+08/`
- `diagnostics/TASK-T06E-P/20260925T075729+08/`
- `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/`
- `paper/T07_RESULT_FREEZE.md`，只读

任何冲突以T06冻结方法与正式集成接口为准。旧`solution/outputs/scaling/`只可作为待复核线索，不得因其已有预测表而直接宣布验证完成。

## 【输入数据】

- B1：`F题/real_attachments/B_scaling_laws/pythia_training_log_existing.csv`
- B2：`F题/real_attachments/B_scaling_laws/cerebras_training_log.csv`，半合成
- B3：`F题/real_attachments/B_scaling_laws/training_trajectories/*.csv`，插值轨迹
- B4：`F题/real_attachments/B_scaling_laws/scaling_baseline.csv`，公开观测
- B5：`F题/real_attachments/B_scaling_laws/published_scaling_data.csv`，公开观测
- B6/B7/B8正式结果只从T06E-B-R1读取，不重新拟合
- B9：`F题/real_attachments/B_scaling_laws/supplementary_large_models.csv`，reported metadata
- B10：`F题/real_attachments/B_scaling_laws/supplementary_large_baseline.csv`，estimated
- T06E-INTEGRATE的`t07_model_contract.json`、`t07_parameter_table.csv`、`integrated_identifiability_matrix.csv`、`scenario_registry_filled.csv`
- 冻结RegMix模型及T06E-P的运输审计、A/B桥接、p-Q识别结果

全部实际读取文件必须写入input manifest。

## 【冻结主模型】

不得重新选择或重新拟合：

`M0_B1: L0(N_B,D_B)=E+A*N_B^(-alpha)+B*D_B^(-beta)`

- `E=1.6897975629820348`
- `A=0.3539803206065571`
- `B=1.2403055835426349`
- `alpha=0.339976581941082`
- `beta=0.2798781285468448`
- `N_B`和`D_B`均以十亿为单位
- B1支持：`N_B∈[0.070542,11.965825]`、`D_B∈[0.134,299.893]`

预测时不得clip至支持边界；任何越界逐行标`OOS`。

## 【输出目录与修改边界】

- 唯一运行目录：`diagnostics/TASK-G2/<run_id>/`
- 候选冻结接口：`paper/Q2_GAP_RESULT_FREEZE.md`
- 允许新建代码、表和验证产物；禁止修改T06、T07、旧scaling、mixture、Q01C、00–05及现有论文正文
- 不启动或重跑T07

## 【G2-A：原题强制验证】

### 1. 统一预处理规则

- 每个来源单独审计字段、单位、Loss定义、N/D定义、观测/半合成/插值/估算性质；
- 只做字段名映射和有证据的单位换算，不做损失尺度重标定；
- 同一来源的重复checkpoint/trajectory必须按模型与step聚类，不能当独立模型倍增样本；
- 真实、半合成、插值、公开文献和估算数据绝不合并计算一个总RMSE；
- B2与B3均执行；原题“B2或B3”最低要求只有在至少一个来源得到可比较验证时才算覆盖；
- B4和B5分别执行，不得因口径差异硬合并；
- B9/B10按`>10B`和`<=10B`分层，B10不得作为真值通过数。

### 2. 逐源指标

每个来源必须报告：

- 原始行数、有效行数、独立模型/轨迹/族数；
- 数据性质与可信度；
- N、D、Loss单位及转换；
- 支持内/OOS数量；
- 冻结M0_B1预测；
- RMSE、MAE、mean error、median error；
- 仅在真实Loss严格为正且尺度可比时报告相对误差，并明确公式；
- 样本不少于5且无常数退化时报告Spearman；
- 按模型族或轨迹聚类的bootstrap区间，种子`20260925`、2000次；
- 系统偏差方向与误差随N/D/step的结构；
- 最终资格：`VALIDATION_SUPPORTED`、`VALIDATION_FAILED`、`OOS_STRESS_ONLY`、`NOT_COMPARABLE`或`ESTIMATED_SCENARIO_ONLY`。

效果差、系统偏差大、跨族失败都必须保留，不能触发重拟合M0_B1。

### 3. B9/B10百亿以上讨论

必须单独输出：

- `N_B>10`的记录数、族数、D与Loss可用率；
- 位于/超出B1支持的情况；
- 若存在可比较观测Loss，报告冻结模型外推误差；
- 若只有reported metadata或estimated baseline，只报告情景偏差与资格，不把估算值升级为真值；
- 明确M0_B1能否支持百亿参数以上推断、支持到何处、主要误差来源。

## 【G2-B：GENERALIZED_CONDITIONAL_SCALING_LAW】

正式联合表达冻结为模块化、中心化形式：

`L_gen^(s)(N_B,D_B,Q_A,p)=L0_B1(N_B,D_B)+rho_Q^(s)*Delta_Q(h_s(Q_A))+tau_p^(s)*Delta_p(p;p0)`。

其中：

1. `L0_B1`的五个参数是B1来源内`IDENTIFIED_SOURCE_CONDITIONAL`；
2. `Delta_Q(Q_B)=-k_add*(Q_B-0.6)`，`k_add=0.3544081081063713`来自B6 MQ-add，仅在B6的`0.1<=Q_B<=0.6`内为来源条件关系；
3. `h_s`只能取T06已冻结的H0-H4：H0为null，H1-H3为`SCENARIO_ONLY`，H4仅方向、不可数值代入；不得估计新的A/B映射；
4. `rho_Q^(s)`只取既有scenario registry的冻结值；不得根据本任务验证表现选最优；
5. `Delta_p(p;p0)`必须来自冻结RegMix线性模型相对`p0`的contrast；1M来源内可识别，向B1运输必须乘既有`tau_p^(s)`并标`SCENARIO_ONLY`；
6. `p`满足17维单纯形。配比效应必须用可行方向`v`（`sum(v)=0`且局部保持非负）解释；不得宣称17个相互独立的坐标边际；
7. 固定领域质量`q`时`Q_mix=p^Tq`位于p的列空间。使用`Q_mix`时必须关闭独立p质量解释，或把其中一个固定为情景，禁止双重计数；
8. 该式是分层估计、联合表达，不是同一联合实验估计出的四变量模型。

### 必须给出的解析量

- `dL/dN_B=-alpha*A*N_B^(-alpha-1)`；
- `dL/dD_B=-beta*B*D_B^(-beta-1)`；
- 数值情景可用时，`dL/dQ_A=-rho_Q*k_add*h_s'(Q_A)`；不可微或H4时只给方向/有限差分；
- 对单纯形可行方向`v`，`D_v L=tau_p*c^T v`，其中`c`为冻结RegMix contrast；
- N/D局部弹性与质量局部弹性；
- 保持Loss不变时`dN_B/dQ_A=-(dL/dQ_A)/(dL/dN_B)`、`dD_B/dQ_A=-(dL/dQ_A)/(dL/dD_B)`；
- p与Q、N、D的局部替代/互补只在对应来源与情景资格内解释。

必须输出一张参数资格矩阵，逐项标记`IDENTIFIED_SOURCE_CONDITIONAL`、`SOURCE_CONDITIONAL`、`SCENARIO_CALIBRATED`、`DIRECTION_ONLY`或`NOT_IDENTIFIABLE`。

## 【G2-C：对T07的影响判定】

生成机器可读字段：

`NEW_Q2_CHANGES_T07_NUMERIC_INPUTS = YES | NO`

默认必须为`NO`。只有本任务产生经过正式验证、且数值上改变T07主合同`M0_B1`参数或已启用模块的关系，才可提出`YES`；但本任务禁止重拟合M0_B1，因此预期输出为`NO`。新的跨源验证失败、联合表达、解析导数或情景资格都不构成重跑T07的理由。执行器不得自行启动增量T07。

## 【必须输出】

- `run_summary.json`、`environment.json`、`input_manifest.json`、`command_log.json`、`stage_status.jsonl`
- `source_schema_and_units.csv`
- `validation_predictions.parquet`
- `validation_metrics_by_source.csv`
- `validation_metrics_by_family_or_trajectory.csv`
- `support_oos_audit.csv`
- `systematic_bias_audit.csv`
- `large_model_gt10b_audit.csv`
- `generalized_law_spec.json`
- `generalized_parameter_qualification.csv`
- `derivatives_elasticities_and_substitutions.md`
- `p_q_double_counting_audit.json`
- `t07_impact_decision.json`
- `checks.json`、独立`verification.json`、`handoff.md`、`code/`、`code_snapshot/`
- 最后生成`output_manifest.json`
- `paper/Q2_GAP_RESULT_FREEZE.md`

## 【检查与验收】

- verifier不得导入执行模块；
- 独立使用冻结参数复算全部预测；
- 对每个来源复算分母、单位、支持状态和误差指标；
- B2/B3至少一个获得非空可比较验证；B4、B5均有独立结论；B9、B10均有>10B审计；
- M0_B1参数逐位与T06冻结值一致；
- generalized law中的每一项均能追到B1、B6、RegMix或既有scenario registry；
- 不得出现新估计的A/B Q映射、17个独立p边际或Q/p双重计数；
- T06/T07旧产物哈希不变；manifest最后生成。

## 【失败判据与停止条件】

以下为硬停止：冻结参数或输入哈希冲突；Loss/单位无法审计却仍计算误差；训练数据泄漏进验证；B2/B3均无法比较；B4或B5被遗漏；B9/B10估算被当真值；generalized law加入无来源参数；需要重拟合M0_B1；需要修改T07数值。

验证表现差、B9/B10外推失败、某来源不可比不是工程失败，必须作为科学负结果交回。

## 【执行器启动prompt】

请执行`tasks/TASK-G2_Q2广义标度律与强制验证闭合.md`。冻结M0_B1及全部T06参数，不重拟合、不重选模型。分别完成B2、B3、B4、B5、B9、B10的来源分层验证和>10B审计，再按施工单给出“分层估计、联合表达”的`L_gen(N,D,Q,p)`及解析边际量。旧T07只读，必须单独输出是否改变T07数值输入。完成后提交`paper/Q2_GAP_RESULT_FREEZE.md`候选及独立验证证据，不修改00–05或论文正文。
