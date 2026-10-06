# TASK-G4：Q4技术演进与前沿预测闭合

日期：2026-09-25。状态：正式执行施工单，`GAP_CLOSURE`，优先级P0。本任务与TASK-G1、TASK-G2、TASK-PAPER-PREFLIGHT相互独立。执行器不得修改T05/T08或自行宣布Q4关闭。

## 【任务目标】

以C1或C2、C3、C4及C8建立直接的Benchmark空间技术演进模型，给出规模关联与非规模关联贡献，并在明确的算力增长放缓情景下生成12/24个月开源模型能力前沿。T05/T08的Loss-Benchmark桥接继续保留，但只作为前三问Loss连接Benchmark的条件敏感性层，不再作为直接Benchmark预测是否存在的门槛。

## 【上位依据】

- 原题问题四与附录A；
- `audit/FINAL_PROJECT_STATE.md`、`audit/QUESTION_REQUIREMENT_COVERAGE.md`、`audit/FINAL_RESULT_SOURCE_OF_TRUTH.md`；
- C01/C01-R1正式审计；
- `paper/T05_RESULT_FREEZE.md`、`paper/T08_RESULT_FREEZE.md`；
- T05/T08正式run，只读。

参考成品论文不得成为模型形式、阈值、增长率或预测数字的来源。

## 【正式输入】

- C1：`F题/real_attachments/C_efficiency_evolution/leaderboard_cleaned.csv`
- C2：`F题/real_attachments/C_efficiency_evolution/leaderboard_enhanced.csv`
- C3：`F题/real_attachments/C_efficiency_evolution/leaderboard_extended_timeseries.csv`
- C4：`F题/real_attachments/C_efficiency_evolution/epoch_all_ai_models.csv`
- C8不重新解析JSON，使用：
  - `diagnostics/TASK-C01-R1/20260924T225308+08/c8_model_task_aggregate_corrected.csv`
  - `diagnostics/TASK-C01-R1/20260924T225308+08/c8_model_wide_corrected.csv`
  - `diagnostics/TASK-C01-R1/20260924T225308+08/c8_directory_aggregate_corrected.csv`
- C01的身份、日期、单位、许可、开放状态、损坏文件及join审计
- T05的`model_identity_crosswalk.csv`、`duplicate_run_resolution.csv`、`corrupt_and_partial_coverage.csv`、`taskwise_bridge_results.csv`、`validation_by_*`和冻结合同
- T08的历史分层、预测seal、模型使用与不确定性表

全部实际读取文件必须写入input manifest。

## 【输出目录与修改边界】

- 唯一运行目录：`diagnostics/TASK-G4/<run_id>/`
- 候选冻结接口：`paper/Q4_GAP_RESULT_FREEZE.md`
- 禁止修改或覆盖C01、T05、T08、T07、旧论文正文、00–05
- 不重新解析1958个C8 JSON；不重跑Loss-Benchmark桥接；不把T08删除或改写为错误

## 【G4-A：样本与时间口径预注册】

### 1. 主样本

- 主数据底座使用C2，C1只作等价性/原字段审计，不把C1和C2当两批独立观测；
- 必须使用C3提供时间维度、C4提供参数/数据/compute/开放权重/许可等元数据、C8提供六任务得分；
- 主前沿对象：`pretrained`开源权重模型；要求权重可获得，且许可证明确允许研究或复现；
- 许可证未知、开放权重不明或身份不唯一者不进入主样本，单列敏感性；
- `chat/finetuned`单独分层和敏感性，不与pretrained无条件合并；
- 六任务为IFEval、BBH、MATH Lvl 5、GPQA、MUSR、MMLU-PRO，分别建模；`six_task_mean_complete_only`仅作辅助综合能力。

### 2. 身份与日期

- 使用C01/T05冻结canonical model identity；同一模型多run保持同一组；4个损坏JSON不赋分；partial只进入实际有效任务；
- 同一模型任务有多条有效结果时沿用C01-R1的聚合，不重新择优；
- 主时间轴采用通过审计的Benchmark提交/评测日期；模型发布日期只作敏感性，不混入主时间轴；
- `forecast_origin`为主样本中身份唯一、日期不模糊、至少一个任务有效的最大观测日期；必须在拟合未来模型前写入`forecast_seal.json`；
- 12/24个月日期从该origin日历加12/24个月计算，不使用系统当前日期。

### 3. 缺失

关键N、D、compute、日期、许可和任务分数不插补。模型可进入其实际有观测的任务，分母逐任务报告。C4存在compute直接观测时优先使用；只有N和D均为观测值时才允许按`6ND`构造compute，并保留`compute_origin`字段。

## 【G4-B：候选模型与选择规则】

每个任务及辅助均值最多比较三个嵌套规格，不开展大规模搜索：

1. `M0_CONSTANT`：常数基线；
2. `M1_SCALE`：`Score=a+b_C*log10(compute)`；compute不可用的记录不进入该模型。`log10(N)`单变量仅作预注册敏感性；
3. `M2_SCALE_TIME`：`Score=a+b_C*log10(compute)+b_T*time_years`。主pretrained样本不加入类型虚拟变量；chat/finetuned另层估计，不用一个虚拟变量掩盖来源差异。

同时用相同三种协变量规格拟合0.90分位数前沿模型；均值/稳健回归用于贡献分解，0.90分位数用于能力前沿。不得追加样条、指数饱和、神经网络或后验交互。

### 验证协议

- grouped model split：canonical model为组，至少5折；
- time-out split：仅按日期预先封存的前80%训练、后20%测试，切点在读取得分结果前由日期分布确定并seal；测试集少于10个独立模型则记`NOT_EVALUABLE`；
- family-out：按模型族留一；少于3个有效模型族则记`NOT_EVALUABLE`；
- 所有候选在完全相同的可用键上比较；不得让更复杂模型通过删难样本获得优势；
- 贡献模型用MAE/RMSE/秩相关，前沿模型用pinball loss、覆盖和前沿排序稳定性。

### 升级门槛

从简单模型向复杂模型升级必须同时满足：

1. 在可评价的验证协议中，至少两个协议的主误差相对改善不低于5%；若只有一个协议可评价，不得称`VALIDATED`；
2. 任一可评价协议相对简单模型不得恶化超过10%；
3. 500次按canonical model分组bootstrap中，关键规模/时间方向至少80%一致；随机种子`20260925`；
4. 设计矩阵满秩，统一列缩放后条件数小于`1e8`；
5. 所有训练/测试、时间和family split无同模型泄漏。

每个任务选择满足门槛的最简单模型。未升级不是返工理由。即使M2未验证，也可按下文生成明确标记的情景预测，但资格必须是`SCENARIO_ONLY_UNVALIDATED`，不能改称验证预测。

## 【规模与非规模关联贡献】

对选中的均值/稳健模型，以主样本最早有效时间和对应scale中心为起点，以forecast origin和origin附近scale中心为终点：

- `Delta_scale=b_C*(logC_origin-logC_start)`；
- `Delta_non_scale=b_T*(t_origin-t_start)`；若正式模型无时间项则为0且说明原因；
- `Delta_fitted=Delta_scale+Delta_non_scale`。

分别报告：

- 有符号贡献；
- 绝对构成占比`abs(Delta_j)/(abs(Delta_scale)+abs(Delta_non_scale))`；
- 当分母近零时记`NOT_DEFINED`，不强行给比例；
- 分组bootstrap区间和模型结构敏感性。

这些量只能称`scale-associated contribution`与`non-scale-associated contribution`。不得称因果算法进步、工程进步或纯技术进步。

## 【G4-C：12/24个月前沿情景】

### 1. 时间点

按冻结forecast origin生成+12月、+24月日期，并在全部表中说明是相对最后有效观测日期。

### 2. 算力增长放缓情景

先按T08冻结规则从主样本尝试估计同族、N/D均观测、间隔90–730天的compute年化对数增长；至少3个独立模型族且至少10个有效族级区间时，用族等权分布的Q25/Q50/Q75形成slow/baseline/upper。

若仍不满足门槛，不再取消情景预测，改用执行前冻结的显式假设：

- `SLOW_ASSUMED`：年compute倍率1.0；
- `BASELINE_ASSUMED`：年compute倍率1.5；
- `UPPER_SENSITIVITY_ASSUMED`：年compute倍率2.0。

这三个数是数学情景网格，不是历史估计、不是参考论文数字，也不分配概率。执行后不得新增或删除情景。

### 3. 前沿输出

- 使用冻结的0.90分位数规格分别输出六任务及辅助综合能力的12/24月场景值；
- 每条记录保留模型资格、训练支持范围、未来compute是否OOS、时间跨度OOS和情景来源；
- 若任务样本或拟合不可用，该任务标`NOT_IDENTIFIABLE`，其余任务继续；
- 区间至少分开报告参数/重采样不确定性、模型选择不确定性、scenario structure和time extrapolation；不得合成一个伪精确CI；
- 分数超出任务理论范围时不得静默clip。保留原预测并标OOS，同时可给范围约束敏感性；
- chat/finetuned前沿仅作分层敏感性，不覆盖pretrained主前沿。

## 【G4-D：Loss-Benchmark桥接】

T05资格保持`CONDITIONAL_ASSOCIATION_ONLY`。Loss桥接只用于说明前三问Loss结果与Benchmark空间的条件联系及桥接误差，不决定直接Benchmark模型能否生成情景。禁止把T07 Loss变化直接换算成Benchmark点数；禁止宣布统一可靠桥接。

## 【必须输出】

- `run_summary.json`、`environment.json`、`input_manifest.json`、`command_log.json`、`stage_status.jsonl`
- `forecast_seal.json`、`scenario_registry.csv`
- `sample_definition_and_flow.csv`
- `model_identity_and_dedup_audit.csv`
- `license_openweight_type_audit.csv`
- `taskwise_denominators.csv`
- `split_registry.csv`、`leakage_audit.csv`
- `candidate_model_metrics.csv`
- `candidate_selection.csv`
- `taskwise_coefficients.csv`
- `scale_non_scale_contributions.csv`
- `contribution_uncertainty.csv`
- `forecast_12m_24m_taskwise.csv`
- `forecast_auxiliary_composite.csv`
- `forecast_uncertainty_components.csv`
- `support_oos_audit.csv`
- `loss_bridge_sensitivity.md`
- `checks.json`、独立`verification.json`、`handoff.md`、`code/`、`code_snapshot/`
- 最后生成`output_manifest.json`
- `paper/Q4_GAP_RESULT_FREEZE.md`

## 【检查与验收】

- C1/C2不重复计数；C3、C4、C8均有非空使用证据；
- 1958/1954/4、1854 complete、6 partial、4损坏等C8冻结事实一致；
- 六任务逐项保留，辅助均值不替代任务；
- 所有split按canonical model防泄漏；
- 选择门槛在结果前seal，执行后未移动；
- 贡献恒等式、比例定义、bootstrap分母可独立复算；
- forecast origin和情景registry早于预测结果；
- 直接Benchmark模型与Loss桥接文件、字段和资格分开；
- verifier不得导入执行模块；
- 旧C01/T05/T08产物不变，manifest最后生成。

## 【返工判据与停止条件】

只有数据泄漏、单位错误、分母错误、公式实现错误、训练/测试重叠、未使用C1/2+C3+C4+C8、不可复现、manifest失败、阈值后验修改或伪造预测数字构成返工。

预测效果差、区间宽、某任务不可识别、非规模项不显著、任务间不一致均是可接受科学结果。若身份join无法唯一完成、主样本为空、日期seal无法建立或必须改动旧run，立即停止交主控。

## 【执行器启动prompt】

请执行`tasks/TASK-G4_Q4技术演进与前沿预测闭合.md`。主分析直接使用C2/C1审计、C3、C4和C8 corrected表建立Benchmark空间的常数、scale-only、scale+time三种预注册候选，并完成group/time/family验证、规模与非规模关联贡献及12/24个月slow/baseline/upper情景。T05/T08只读，Loss桥接保持`CONDITIONAL_ASSOCIATION_ONLY`且不得控制直接Benchmark预测。允许负结果和单任务不可识别，不得后验改模型或阈值。提交`paper/Q4_GAP_RESULT_FREEZE.md`候选及独立验证，不修改00–05或论文正文。
