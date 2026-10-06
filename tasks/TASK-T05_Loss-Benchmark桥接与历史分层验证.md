# TASK-T05：Loss–Benchmark桥接与历史分层验证

日期：2026-09-25。状态：正式执行施工单；本文件只定义后续执行，不授权本轮运行。

## 【任务目标】

基于已经关闭的C01/C01-R1审计结果，构造可追溯的Loss–Benchmark候选样本，判断桥接关系究竟可识别为预测映射、仅能称分层条件关联，还是必须登记`NOT_IDENTIFIABLE`。本任务为T08提供规模、时间、模型族和benchmark接口，不直接进行问题四前沿预测。

## 【输入与只读边界】

- `diagnostics/TASK-C01/20260924T175553+08/`全部正式产物；
- `diagnostics/TASK-C01-R1/20260924T225308+08/c8_directory_aggregate_corrected.csv`、`c8_model_task_aggregate_corrected.csv`、`c8_model_wide_corrected.csv`及验证文件；
- C1/C2 leaderboard、C3时间序列、C4模型元数据、C5/C6 Loss–Benchmark表、C7架构上下文、C9等价表、C10许可/开放状态，只读；
- `tasks/TASK-C01-R1_C8聚合与检查器精准小修.md`及00–05。

不得重新解析1958个C8 JSON，不重跑C01，不修改`evolution_audit.py`或旧run。只写`diagnostics/TASK-T05/<run_id>/`。

## 【样本构造预注册】

1. 先建立规范模型身份表，保留原始名称、规范名、模型族、参数规模、提交/发布日期、开放权重与许可、聊天/预训练类型；无法唯一连接的记录不得模糊合并。
2. C8只使用R1 corrected表。1854个六任务完整模型可形成完整均值；6个partial只保留逐任务或`partial_task_mean`，不得进入完整六任务均值。4个损坏JSON只影响覆盖，不得赋分。
3. 95个双文件目录先登记run选择规则：若有明确时间/版本顺序则保留最新且报告另一run；若无可靠排序则按模型聚类保留全部run并在划分中同组，禁止把同模型run分到训练和测试。
4. C5/C6分别保留来源和Loss定义。只有模型身份、token位置/训练阶段、数据口径和Loss定义同时可比时才进入主桥接；其余进入分层或OOS表。
5. Medium层缺D不得默填总体中位数。缺D记录只能进入不使用D的描述层，或在外部可核来源补齐后另行登记。
6. benchmark必须保留六任务向量；完整均值只是辅指标。不同时间评测标准或leaderboard版本不得直接拼接成同一纵向真值。

## 【比较层级】

- L0：同一模型/同一评测版本内的Loss与单任务分数、六任务完整均值的描述关系；
- L1：按模型族、规模层、Loss定义和时间窗口分层的单调/线性关系；
- L2：含`log N`、可用时`log D`、模型族和时间的条件预测；
- L3：若连接和样本量支持，比较线性、单调等距回归与有限复杂度样条。样条自由度最多4，不能用高自由度黑箱吸收来源差异。

不把相关性解释为因果“技术进步”。若Loss定义之间没有可验证桥接，必须分模型报告或降级`NOT_IDENTIFIABLE`。

## 【验证协议】

1. 训练/内部验证按规范模型ID分组，禁止同模型多run泄漏。
2. 时间外验证：冻结一个日期切点，只用较早记录训练、较晚记录测试；切点须由数据覆盖预先确定并在查看指标前写入seal。
3. 留模型族验证：每次完整留出一个样本量足够的模型族；不足族只作OOS。
4. 规模外验证：按参数规模分层，至少保留一个大模型层作外推检查；Medium缺D单列。
5. C5训练、C6独立验证优先；若C5/C6并非同口径，必须改为“来源间迁移测试”，不能称普通测试集。
6. 指标报告MAE、RMSE、Spearman、校准斜率、覆盖率和分层残差；大样本不以p值作为主要门槛。

候选升级为“可执行桥接”至少需要：主方向在内部、时间外和留族验证中一致；相对常数/仅规模基线的RMSE改善至少10%；Spearman至少0.5；主要分层中不出现超过25%的方向反转；95%预测区间经验覆盖在0.85–0.98。任一不满足则降级为条件关联；身份或Loss定义无法对齐则`NOT_IDENTIFIABLE`。阈值执行后不得移动。

## 【T08接口】

必须分别输出：

- `scale_progress`：由N、D或compute解释的预测部分及不确定性；
- `non_scale_residual`：在明确条件模型下的剩余项，只能称非规模关联，不能自动称因果技术进步；
- `time_trend`：时间外验证通过后才可用于情景外推；
- `benchmark_prediction`：六任务分别及完整均值，带适用范围；
- `uncertainty`：身份匹配、Loss口径、run重复、模型误差和外推分开；
- `eligibility`：`IDENTIFIED_PREDICTIVE_BRIDGE`、`CONDITIONAL_ASSOCIATION_ONLY`或`NOT_IDENTIFIABLE`。

## 【必须输出】

- `model_identity_crosswalk.csv`、`loss_definition_catalog.csv`、`comparability_strata.csv`
- `duplicate_run_resolution.csv`、`corrupt_and_partial_coverage.csv`
- `bridge_analysis_dataset.parquet`、`split_registry.csv`及执行前seal
- `candidate_models.csv`、`validation_by_split.csv`、`validation_by_family.csv`、`validation_by_time.csv`
- `taskwise_bridge_results.csv`、`aggregate_bridge_results.csv`、`residual_audit.csv`
- `identifiability_decision.json`、`t08_bridge_contract.json`
- `run_summary.json`、`handoff.md`、`checks.json`、`verification.json`
- `code/`、`code_snapshot/`、最后生成的`output_manifest.json`

## 【独立验证与停止条件】

verifier不得导入执行模块，须独立复算连接计数、C8 corrected锚点、完整/partial分母、模型ID分组无泄漏、时间顺序、C5/C6来源角色、关键指标、资格门槛和manifest。若需要重清洗C01、无法解释C5/C6 Loss定义、同模型泄漏、损坏JSON被赋分、Medium缺D被静默填补，或需要根据测试结果改模型/阈值，立即停止交主控。不得启动T08。

