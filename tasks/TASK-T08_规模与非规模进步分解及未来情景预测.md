# TASK-T08：规模与非规模进步分解及未来情景预测

日期：2026-09-25。状态：正式执行施工单；本文件只冻结后续方法与验收范围，本轮不执行。

## 【任务目标】

在TASK-T05与TASK-T07已经验收的识别边界内，完成问题四的历史分层、规模关联分解和未来12/24个月情景预测。任务必须保留六任务benchmark向量，并把“由规模变量条件解释的部分”和“条件剩余项”分开。现有数据不能识别因果技术进步，也没有可靠的统一Loss→Benchmark桥接，因此不得把剩余项命名为算法进步，不得把Loss空间预测换算成benchmark点数。

## 【冻结前提】

1. TASK-T05最终资格为`CONDITIONAL_ASSOCIATION_ONLY`。主可比层只有7个C5 High/Pythia模型；六个任务及辅助均值均选择`CONSTANT`。时间外验证、留模型族升级和主层大规模外验证均未通过或不可识别。
2. `time_trend.validated_for_extrapolation=false`。未来12/24个月只能输出`SCENARIO_FORECAST`，不能称统计意义上的已验证时间外预测。
3. TASK-T07的正式主模型是`M0_B1`，只在Loss空间和B1支持域内有来源条件资格。质量、配比及A/B桥接均为`SCENARIO_ONLY`。
4. T05的六任务向量是正式benchmark对象，`benchmark_mean_aux`只能作为辅助汇总。
5. 旧Q1/Q2冻结结果、T05/T07正式run、C01/C01-R1和T06正式结果全部只读。

## 【强制输入】

- `diagnostics/TASK-T05/20260925T113355+0800/t08_bridge_contract.json`
- `diagnostics/TASK-T05/20260925T113355+0800/bridge_analysis_dataset.parquet`
- `diagnostics/TASK-T05/20260925T113355+0800/prediction_table.parquet`
- `diagnostics/TASK-T05/20260925T113355+0800/residual_audit.csv`
- `diagnostics/TASK-T05/20260925T113355+0800/split_registry.csv`
- `diagnostics/TASK-T05/20260925T113355+0800/model_identity_crosswalk.csv`
- `diagnostics/TASK-T05/20260925T113355+0800/identifiability_decision.json`
- `diagnostics/TASK-T07/20260925T113744+08/t08_or_paper_interface.json`
- `diagnostics/TASK-T07/20260925T113744+08/budget_scenario_optima.csv`
- `diagnostics/TASK-T07/20260925T113744+08/uncertainty_summary.csv`
- `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json`
- C01/C01-R1已经验收的C1/C2/C3/C4/C8候选表及身份、日期、许可、开放状态审计结果，只读。

执行只允许写入`diagnostics/TASK-T08/<run_id>/`。不得重跑T05/T07，不得重新解析C8 JSON，不得重新选择桥接模型，不得启动论文定稿或修改Q1/Q2冻结文件。

## 【核心估计量与命名】

对模型`i`和任务`t`，以T05冻结模型得到条件预测`m_t(x_i)`。定义：

- `scale_associated_component_it = m_t(x_i) - m_t(x_ref)`；
- `conditional_remainder_it = y_it - m_t(x_i)`。

其中`x`只含冻结模型允许使用的观测N、观测D或compute，`x_ref`必须在执行前登记且位于支持域。当前T05主模型为常数，所以主分析中`scale_associated_component=0`；这是一项正式结果，禁止改用未通过选择的候选来制造非零规模贡献。`conditional_remainder`只能称“非规模关联残差”或“条件剩余项”，不能称因果算法/工程进步。

另行计算Loss空间的`M0_B1`规模情景变化，但必须使用不同字段和图层，名称为`loss_space_scale_scenario`。它不得与benchmark条件剩余项相加，也不得转换为benchmark点数。

## 【历史分层】

按以下维度对六任务分别报告样本数、缺失率、中位数、IQR及必要的描述性差异：

- 模型族；
- 参数规模层（沿用T05冻结边界：`<=3B`、`>3B且<20B`、`>=20B`）；
- 开放权重/许可状态，未知单列；
- 时间窗口，日期模糊或缺失单列；
- benchmark任务。

任何分层单元`n<5`不得报告稳定均值比较，只登记`INSUFFICIENT_N`并保留原始计数。相同模型的多个run必须保持同组；4个损坏JSON不赋分，6个partial只进入其实际有效任务，不进入六任务完整均值。

## 【未来12/24个月情景预注册】

### 1. 预测原点

以身份唯一、日期不模糊且通过C01审计的可用记录中的最大观测日期为`forecast_origin`，在读取任何未来情景结果前写入`forecast_seal.json`。12个月和24个月均从该日期计算，不得改用当前系统日期或赛题日期以改善结果。

### 2. 历史规模变化率

只对同一模型族内可排序、间隔90–730天、N与D均为观测值的相邻记录计算`compute_proxy=6*N*D`及年化对数变化率。不得插补D。每个模型族对每个时间段最多贡献一条，先在族内取中位数，再在模型族之间形成独立分布，避免大族重复加权。

若独立变化至少来自3个模型族且有效族级区间不少于10个，冻结：

- 保守场景：年化对数变化率的25%分位；
- 基准场景：50%分位；
- 积极场景：75%分位。

分位数在`scenario_registry.csv`冻结后不得移动。若支持不足，则三种情景的数值增长率均记为`NOT_IDENTIFIABLE`，只允许列出历史支持范围，不得临时改用参数规模增长、外部传闻或手工倍率补齐。

### 3. 规模与Loss情景

在增长率可识别时，按`C_h=C_origin*exp(g*h)`得到12/24个月compute情景；`C_origin`必须来自同一历史规则，不得选取结果最好的模型。使用T07的S00/M0_B1和`H=2048`求条件N/D配置，并复算物理成本。N、D或compute超出B1/T07支持域时标记`OOS`，不得clip或扩大边界后继续称预测。

### 4. benchmark情景

由于T05冻结模型为常数且时间趋势未通过，benchmark正式输出只允许：

- `CONDITIONAL_BASELINE_ONLY`：报告六任务主可比层常数基线及其条件区间；
- `NOT_IDENTIFIABLE_PROGRESS`：12/24个月benchmark增量不提供数值；
- 对Loss空间规模情景给出并列说明，但不做Loss→benchmark换算。

禁止用C6 Medium条件模型、未选中的SIZE/LOSS模型或全榜时间回归生成主benchmark预测。探索性分层图可以保留，但必须标`DESCRIPTIVE_NOT_FORECAST`。

## 【不确定性分层】

不得合成单一置信区间。至少分别输出：

1. `scaling_parameter`：T07保存的B1整行80 draws；
2. `bridge_model_error`：T05常数模型的条件误差和覆盖，不升级为可迁移预测误差；
3. `benchmark_conditional_association`：六任务残差的分层差异；
4. `model_family_heterogeneity`：族间描述差异及小样本标记；
5. `time_extrapolation`：由于时间外验证失败，状态固定为`UNVALIDATED`；
6. `scenario_structure`：保守/基准/积极增长假设及支持不足/OOS状态。

## 【验证与防泄漏】

- 完全沿用T05模型ID、run group、日期cutoff和主/条件层角色，不得重新随机拆分。
- 同模型的任何run不得跨历史比较的训练/验证侧；不得把C5/C6相同43行或C6 High相同7行当独立证据。
- 独立复算每条`observed = fitted + conditional_remainder`恒等式，容差`1e-10`。
- 核对主层所有任务的冻结候选均为`CONSTANT`，据此主层scale-associated居中分量必须为0。
- 核对六任务向量完整性；均值列不得替代任何单任务结论。
- 核对未来情景ID在执行前seal，执行后不得新增、删除或重命名不利情景。
- 复算compute单位、预算可行性和支持状态；不得把十亿单位直接代入`6ND`。
- 独立verifier不得导入执行模块，必须直接读取冻结输入和最终表复算计数、恒等式、场景增长率、支持/OOS、分层资格和manifest。

## 【必须输出】

- `run_summary.json`、`environment.json`、`input_manifest.json`、`command_log.json`、`stage_status.jsonl`
- `forecast_seal.json`、`scenario_registry.csv`、`model_identity_usage.csv`
- `scale_non_scale_decomposition.csv`
- `historical_strata_summary.csv`
- `taskwise_progress.csv`
- `forecast_12m_24m_scenarios.csv`
- `forecast_uncertainty.csv`
- `loss_space_scale_scenarios.csv`
- `support_oos_audit.csv`、`leakage_audit.csv`、`missingness_and_denominators.csv`
- `t08_paper_interface.json`
- `checks.json`、`verification.json`、`handoff.md`
- `code/`、`code_snapshot/`、最后生成的`output_manifest.json`

所有表必须包含资格或状态字段，明确区分`OBSERVED_DESCRIPTION`、`CONDITIONAL_ASSOCIATION_ONLY`、`SCENARIO_FORECAST`、`OOS`、`NOT_IDENTIFIABLE`。`t08_paper_interface.json`必须给出可写入正文的结论、不可写表述、六任务结果入口、预测原点、支持范围和六类不确定性。

## 【关键检查与验收锚点】

1. T05主样本=7、条件层=38、总桥接完整模型=45；C8完整/partial/损坏=1854/6/4。
2. 主层六任务及辅助均值的冻结模型全部为`CONSTANT`；主层规模关联居中分量逐行严格为0。
3. `time_trend.validated_for_extrapolation=false`原样传播；所有12/24月记录均为`SCENARIO_FORECAST`或`NOT_IDENTIFIABLE`。
4. Medium缺D不插补；同模型run跨侧泄漏=0；损坏JSON赋分=0。
5. M0_B1仅在Loss空间使用；Loss→benchmark数值转换次数=0。
6. 六任务分别输出且分母明确；均值只作辅助。
7. 三个情景ID及12/24月组合在执行前冻结；不满足历史支持门槛时不得产生伪数值增长率。
8. B1参数draw保持整行；不确定性六类分列，不合并为单一CI。
9. output manifest在summary、日志、checks、verification和handoff冻结后最后生成，生成后不再改写登记文件。

## 【禁止事项】

- 不得重选T05候选、移动阈值或将CONSTANT结果视为失败后改用SIZE模型；
- 不得把`conditional_remainder`称为因果技术进步；
- 不得把C6 Medium当作独立同口径测试；
- 不得用简单时间回归生成确定性未来预测；
- 不得插补Medium的D、损坏C8结果或日期；
- 不得将Loss空间改善换算为benchmark点数；
- 不得将T07质量/配比情景当已识别的历史解释变量；
- 不得因题目要求预测而强行产生不可识别的数字。

## 【停止条件】

发现T05/T07输入哈希变化、身份映射冲突、同模型泄漏、D被插补、冻结候选不再是常数、情景seal晚于结果、Loss与benchmark被无桥接合并、支持不足却仍生成数值时间增长率、或需要修改既有正式run时立即停止并交主控。任务结束后只提交待审产物，不直接改论文、00–05或启动下一任务。

