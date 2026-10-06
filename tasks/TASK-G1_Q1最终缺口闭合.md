# TASK-G1：Q1最终缺口闭合

日期：2026-09-25。状态：正式执行施工单，`GAP_CLOSURE`。本任务与TASK-G2、TASK-G4、TASK-PAPER-PREFLIGHT相互独立，可并行执行。执行完成后状态只能为`COMPLETE_PENDING_CONTROLLER_REVIEW`、`WAITING_FOR_AUTHOR_REVIEW`或`STOPPED_WITH_EVIDENCE`，不得自行宣布Q1关闭。

## 【任务目标】

只关闭两个缺口：

1. 使用既有Q01C行级结果检验A1抽样集的冲突结构在A2/A3扩展集中的稳定性；
2. 建立最小、可重复、由作者本人完成判断的原始文本可靠性核验。

本任务不得重做Q01C、不得重选主质量特征、不得改变主Q或冲突阈值、不得用AI判断冒充人工标签。

## 【上位依据与优先级】

1. 原题与《数据说明》；
2. `audit/FINAL_PROJECT_STATE.md`、`audit/QUESTION_REQUIREMENT_COVERAGE.md`、`audit/FINAL_RESULT_SOURCE_OF_TRUTH.md`；
3. Q01C正式科学run：`solution/outputs/quality_q01c/20260924T215718+08/`；
4. T03E正式run：`diagnostics/TASK-T03E/20260925T020032+08/`；
5. `paper/FINAL_RESULT_INDEX.md`及现有冻结接口。

发生冲突时按上述顺序处理，并在handoff中逐项登记，不得自行拼接旧run数字。

## 【正式输入】

- `solution/outputs/quality_q01c/20260924T215718+08/quality_features_scores.parquet`
- 同run的`domain_summary.csv`、`summary_denominators.csv`、`run_config.json`、`input_manifest.json`、`output_manifest.json`、`code_snapshot/`
- `diagnostics/TASK-T03E/20260925T020032+08/phase_b_frozen_validation/extension_overlap_validation.csv`
- 同目录的`extension_new_validation.csv`、`extension_summary.json`、`actual_domain_labels_all_roles.csv`
- A1/A2/A3来源、role、overlap/new标识，以Q01C行级字段和正式manifest为准
- 可映射原始文本的首选来源：`F题/real_attachments/A_data_value/regmix_domain_sample.jsonl.xz`（A18）；如Q01C正式来源中已有更直接、可验证的文本映射，可替代A18，但必须先输出join覆盖审计

## 【冻结科学定义】

- 主Q：11个主特征严格完整案例；
- 三个质量组：沿用Q01C的原组定义；
- 聚合：组内冻结规则、组三等权；
- 缺失：严格传播，`Q_valid=False`的19条记录保留且主Q为NaN；
- 冲突：沿用Q01C的`rater_disagreement_range`、`rater_disagreement_std`和冻结高冲突阈值；
- 去重：`all_unique`按Q01C唯一键口径；物理行和唯一键不得混用；
- 不得使用`Q_C`替换`Q_baseline`。

## 【输出目录与允许修改范围】

- 唯一运行目录：`diagnostics/TASK-G1/<run_id>/`
- 最终候选冻结接口：`paper/Q1_GAP_RESULT_FREEZE.md`
- 允许创建盲审文件副本供作者填写；不得覆盖生成时的原始盲审表
- 禁止修改Q01C、T03E、T06及任何旧run；禁止修改00–05和现有论文正文

## 【G1-A：扩展冲突稳定性】

### 1. 必须分别报告的scope

- `A1_sample`
- `A2_extension`
- `A3_extension`
- `extension_overlap`
- `extension_new`
- `all_unique`

每个scope必须明确：物理行数、唯一键数、Q有效数、Q缺失数、coverage、域数、active域数。overlap记录不得再次作为独立样本增加all_unique分母。

### 2. 必须复算的指标

- `Q_baseline`的n、均值、中位数、标准差、IQR及预注册分位点；
- 高冲突数与比例；
- 三组range和std的均值、中位数、IQR；
- 三个组均值及两两差；
- 造成最大组间差异的组对及方向；
- 按domain和active-domain重复上述核心指标；
- overlap与new差异；
- A1、A2、A3及all_unique之间的分布距离：至少报告KS统计量和Wasserstein距离，但不以p值作为稳定性结论。

### 3. 预注册稳定性判据

高冲突阈值必须从Q01C配置读取。扩展集相对A1的全局稳定性按以下四项判断：

1. 高冲突率绝对差不超过5个百分点；
2. `rater_disagreement_range`中位数绝对差不超过0.10；
3. `rater_disagreement_std`中位数绝对差不超过0.05；
4. 最大冲突组对的主导类别一致，或第一、第二类别合计覆盖率差不超过10个百分点。

域级稳定性仅在至少4个共同有效域时评价：共同域高冲突率Spearman不低于0.50，且至少70%的共同域保持相对all_unique总体的高/低方向。共同域不足时记`NOT_EVALUABLE`，不得补域或降阈值。

最终资格：

- `STABLE`：A2与A3各自在至少3/4个全局判据上通过，且可评价的域级判据通过；
- `PARTIALLY_STABLE`：仅一个扩展集达到上述要求，或域级判据不可评价/未通过但全局指标未出现一致反转；
- `NOT_STABLE`：A2、A3均少于3/4通过，或关键冲突方向在二者中出现一致反转；
- 数据结构不足时使用`NOT_EVALUABLE`，不得强行归入STABLE。

必须另做分层bootstrap，随机种子`20260925`，重复2000次；按唯一键重采样并保持domain分层。区间只用于稳定性说明，不得事后改变上述阈值。

## 【G1-B：MINIMAL_REPRODUCIBLE_TEXT_CHECK】

### 1. 文本映射预审计

先只做键和覆盖审计，输出每个候选文本来源与Q01C唯一键的：总数、唯一数、匹配数、一对一/一对多/多对一数、文本非空率及各domain覆盖。若不存在可验证的一对一或可按冻结规则确定的映射，停止并返回`TEXT_NOT_JOINABLE`，不得模糊匹配或人工猜键。

### 2. 抽样冻结

- 随机种子：`20260925`；
- 目标样本数：60；若满足全部分层条件的可映射样本不足，允许降至48，并在抽样前冻结实际n及原因；低于48则停止交主控；
- 高/低Q在domain内按有效Q的上、下四分位定义，避免被域差异替代；
- 高冲突沿用Q01C阈值；低冲突从非高冲突记录中抽样；
- 建议配额：20条高Q低冲突、20条低Q低冲突、20条高冲突；高冲突层内尽量平衡高/低Q；
- 至少覆盖6个有文本且有有效Q的主要domain；任何单一domain不超过样本的20%；若数据不允许，冻结可行配额并明确偏离原因；
- 抽样、配额、review_id和SHA256必须在任何人工评分发生前写入`sampling_seal.json`。

### 3. 盲审包

生成只含`review_id`、必要的domain提示（如会泄露来源偏见则另置映射表）、脱敏文本和以下作者填写列的`manual_text_review_blind.csv`：

- `readability_1to5`
- `completeness_1to5`
- `contamination_0to2`（0无明显污染、1可疑、2明显垃圾/广告/模板污染）
- `overall_quality_1to5`
- `review_notes_optional`

盲审表不得含Q、Q分位、高冲突标签、组三分数、原始主键或模型预测。另生成`manual_review_instructions.md`，要求作者独立完成，不使用AI自动评分。原始文本只做必要脱敏，不得改写。

执行器完成盲审包后应将状态置为`WAITING_FOR_AUTHOR_REVIEW`并停止。作者将完成表另存为`manual_text_review_completed.csv`后，执行器方可继续统计。

### 4. 人工结果统计

只对有效填写记录计算：

- Q与`overall_quality_1to5`的Spearman及bootstrap区间；
- Q与可读性、完整性的秩相关；
- contamination与Q的方向关系；
- 高Q与低Q组的人工评分差异和效应量；
- 高冲突文本的人工异常率，与低冲突组对照；
- 至多6个典型成功/失败案例，只以review_id和经脱敏短摘录呈现。

相关性低、方向不一致或人工异常率无差异均为允许的科学结果，不得返工抽样或删除不利案例。

## 【必须输出】

- `run_summary.json`、`environment.json`、`input_manifest.json`、`command_log.json`、`stage_status.jsonl`
- `scope_denominators.csv`
- `conflict_stability_summary.csv`
- `conflict_by_domain.csv`
- `overlap_new_comparison.csv`
- `distribution_distances.csv`
- `bootstrap_stability.csv`
- `text_join_audit.csv`
- `sampling_seal.json`
- `manual_text_review_blind.csv`
- `manual_review_key.csv`（与盲审表分离、限制读取）
- `manual_review_instructions.md`
- 作者填写后：`manual_text_review_joined.csv`、`manual_validation_statistics.csv`、`manual_case_registry.csv`
- `checks.json`、独立`verification.json`、`handoff.md`、`code/`、`code_snapshot/`
- 最后生成`output_manifest.json`
- 全部阶段完成后生成`paper/Q1_GAP_RESULT_FREEZE.md`

## 【独立验收与硬检查】

- verifier不得导入主执行模块；
- 独立复算各scope分母、19条Q无效记录、overlap去重和高冲突阈值；
- 验证抽样seal早于人工评分文件，review_id无重复且盲审列不泄露Q/冲突；
- 验证人工评价列由作者填写，执行代码不得生成这些值；
- 检查Q01C与T03E正式产物哈希未变；
- manifest必须最后生成，生成后不得改写登记文件。

## 【禁止事项】

- 不重扫或重算A1–A3质量特征；
- 不修改11特征、三组权重、缺失策略、主Q或冲突阈值；
- 不用AI、规则或模型生成“人工”评分；
- 不按人工结果重新抽样；
- 不把相关性解释为因果或外部真值；
- 不把A18的可选性质写成全量强制验证；
- 不覆盖旧run、00–05或论文正文。

## 【停止条件】

输入哈希变化、Q01C字段不足、scope无法唯一构造、文本无法可靠join、盲审样本少于48、人工表未完成、发现评分泄漏或必须改变冻结定义时立即停止并提交证据。不得为赶进度制造人工结果。

## 【执行器启动prompt】

请执行`tasks/TASK-G1_Q1最终缺口闭合.md`。严格复用Q01C/T03E冻结定义，不重做主Q。先完成扩展冲突稳定性与文本join审计，再生成已seal的48–60条盲审包；到需要作者人工判断时以`WAITING_FOR_AUTHOR_REVIEW`停止。作者填写后再完成统计和`paper/Q1_GAP_RESULT_FREEZE.md`候选。不得用AI文本判断替代作者，不得修改旧run、00–05或论文正文。
