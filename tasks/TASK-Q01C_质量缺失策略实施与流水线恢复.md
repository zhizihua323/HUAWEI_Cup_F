# TASK-Q01C正式施工单：质量缺失策略实施与流水线恢复

状态：**施工单已编制，未执行。只有收到单独执行指令后才能开工。**

编制日期：2026-09-24。所有相对路径均相对于：

`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace`

## 【任务编号】

TASK-Q01C。

前置任务：TASK-Q01A经R1补证后验收通过；TASK-Q01B方法裁决已完成并登记到`02_DECISIONS.md`。

本任务吸收原计划T02“日志与检查点增强”和原T03中的质量流水线恢复部分，不再为日志另开一次全量运行。

## 【任务名称】

按Q01B策略修改质量流水线，生成严格完整案例主Q、隔离的校准域内中位数敏感性分析，并完成可恢复运行、显式分母和端到端验证。

## 【任务背景】

旧`solution/src/quality_audit.py`已经实现A1–A3读取、11特征归一化、三组等权Q、域汇总和部分诊断，但存在以下已确认问题：

1. 11个主Q特征中有19个唯一记录不完整；旧验证却断言全部`Q_baseline`非空。
2. 旧`summarize()`中的`n`是总行数，Q均值、标准差和分位数实际使用pandas跳过NaN后的有效样本，分母没有显式登记。
3. 分歧range/std可以在两个有效组上计算，不能因第三组缺失而一并视为缺失。
4. 旧流水线将多个阶段连续执行并写入固定`solution/outputs/quality/`目录，缺少阶段退出码、错误栈、源码/输入哈希和可复用检查点；上次中断无法精确恢复。
5. 旧产物是历史证据，不能被新运行覆盖。

TASK-Q01A/R1已经确认：272505条物理记录、261086个唯一键、11特征完整261067条、缺失19条；缺失仅涉及modernbert_professionalism 6条和modernbert_reasoning 13条，交集0。Q01B已确定处理方法，本任务不得重新选择策略。

## 【目的】

1. 把Q01B裁决准确写入可运行代码，同时保留全部底层记录和缺失证据。
2. 使所有Q相关汇总显式、机器可审查地报告总样本数与有效分母。
3. 将校准域内中位数插补严格隔离为敏感性分析，杜绝验证集或扩展集泄漏。
4. 在同一次正式运行中补齐日志、阶段状态、检查点、输入/源码/输出清单和失败留痕。
5. 生成新的版本化质量产物并完成端到端验收；旧quality产物与Q01A/R1证据保持不变。

## 【正式方法约束】

以下规则来自Q01B，执行AI无权更改：

1. 主分析使用11个主Q特征严格完整案例。11特征全部有限时`Q_valid=True`并计算主Q，否则`Q_valid=False`且主Q保持NaN。
2. 19条异常记录必须保留在行级产物中，不得删除、填0或覆盖异常原因。
3. 三个质量组继续固定组内等权、组间等权。不得把缺失组的权重重分配给剩余两组。
4. Q相关统计必须报告`n_total`、`n_Q_valid`、`n_Q_missing`、`coverage=n_Q_valid/n_total`。Q均值、标准差、分位数和区间只使用`Q_valid=True`记录；标准差同时登记有效n和`n-1`方差除数。
5. 分歧range和ddof=0组间std按现有skipna语义使用有效质量组计算，并逐行保存`n_groups_valid`。有至少一个有效组时可定义；本批数据预期所有记录至少有两个有效组。分歧统计不得替代缺失的主Q。
6. 校准域内中位数插补只生成独立的敏感性Q列和独立汇总，不得覆盖主Q、主组得分或主报告口径。
7. 每个敏感性插补参数只能从`A1_calibration & is_unique_first`中对应`domain + feature`的有限归一化值估计。禁止使用holdout、extension overlap、extension new或全体数据估计参数。
8. 对每个实际需要插补的域/特征，参数充分性门槛预先固定为：`n_valid >= 100`、`coverage >= 0.95`且`n_unique_finite >= 2`。A3 github必须使用A1 calibration/github对应特征；若任一门槛不满足，立即停止并交主控裁决，不得使用全局中位数、其他域、其他角色、填0或任何自动fallback。
9. 现有归一化规则不因缺失策略而重选：PRRC使用官方0–5范围，ad/fluency使用0–1范围，其余主Q特征的1%–99%分位参数只由A1 calibration按既定域等权规则估计。

## 【输入文件】

以下文件在执行期间只读：

- `00_PROJECT_BRIEF.md`、`01_PROJECT_STATUS.md`、`02_DECISIONS.md`、`03_DATA_CATALOG.md`、`04_TASK_QUEUE.md`、`05_REVIEW_LOG.md`。
- `tasks/TASK-Q01A_质量缺失模式诊断.md`。
- `tasks/TASK-Q01A-R1_主控审查与精准小修要求.md`。
- `tasks/TASK-Q01B_质量缺失处理策略裁决.md`。
- `diagnostics/TASK-Q01A/20260924T142229+08/`正式运行证据。
- `diagnostics/TASK-Q01A-R1/20260924T150854+08/`正式R1证据。
- `solution/src/quality_audit.py`、`solution/src/common.py`、`solution/config.json`、`solution/README.md`。
- `solution/outputs/quality/`现有历史产物，只用于回归比较和输入版本核验。
- `solution/outputs/quality/semantic_sources/`及其清单。

两个Q01A-R1前置失败目录和Q01A首次失败目录只能作为失败历史阅读，不得与正式统计混合。

## 【允许读取的原始数据】

只有正式执行获授权后，才允许读取以下三份原始文件：

|ID|路径|
|---|---|
|A1|`F题/real_attachments/A_data_value/slimpajama_quality_signal_sample.jsonl.xz`|
|A2_arxiv|`F题/real_attachments/A_data_value/slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz`|
|A3_github|`F题/real_attachments/A_data_value/slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz`|

正式成功运行中每个文件至多完成一次顺序解压。不得复制完整解压文件到磁盘，不得保存正文。允许保存ID、sub_path、哈希、域、角色、25个提取特征、缺失原因和评分所需字段。

压缩文件版本可通过只读字节哈希或既有受信清单核对；无论采用哪种方式，必须记录实际核验方法。压缩字节哈希不计作解压扫描。

## 【允许修改或新建的代码】

- 可修改`solution/src/quality_audit.py`，实现Q01B规则、显式分母、版本化输出、阶段化执行和恢复入口。
- 可在`solution/src/`新建名称明确的Q01C运行/清单辅助脚本。
- 可在`solution/tests/`新建Q01C专项测试。
- 除非现有接口无法安全传入输出目录，不修改`solution/src/common.py`；确需修改时必须在`changes.csv`逐项说明，且不得改变其他模块的默认输出行为。

所有被修改或新建的代码必须复制到正式run目录的`code_snapshot/`并记录SHA256。代码修改不等于任务完成，必须经过后述测试和正式运行验收。

## 【禁止修改的文件】

- 全部`F题/`原始材料。
- `solution/outputs/quality/`现有历史产物及`solution/reports/quality_baseline.md`。
- Q01A、Q01A-R1所有正式与失败运行目录。
- 既有恢复证据和任务文档。
- 配比、缩放、演化及优化模块源码和产物。

执行AI不得更新00–05项目文档、不得把Q01C标记为验收通过。完成后由主控审查并更新管理文档。

## 【运行目录与防覆盖规则】

正式输出根目录固定为：

`solution/outputs/quality_q01c/<run_id>/`

`run_id`使用实际启动时间和唯一后缀。目录存在时必须失败退出，禁止覆盖或复用同名目录。人工测试可写入：

`solution/outputs/quality_q01c_tests/<run_id>/`

测试目录和正式目录不得混合。正式报告、日志、检查点、行级结果、机器检查和交回材料全部放入正式run目录，避免再次写入旧quality目录。

## 【必须修改的行为】

### 1. 主Q与缺失标记

- 新增布尔列`Q_valid`，其定义必须等价于11个归一化主Q特征全部有限。
- 新增`Q_missing_feature_count`和可逆的`Q_missing_features`；19条异常记录必须能追溯到具体特征。
- `Q_baseline`仅在`Q_valid=True`时为有限值；`Q_valid=False`时必须为NaN。
- 三个主组分数仍要求本组全部构成特征有限，不得组内skipna计算主组分数。
- 新增`n_groups_valid`。分歧range/std可在有效组上计算，主Q仍要求三组全部有效。

### 2. 显式分母

- `domain_summary.csv`每个scope/domain至少包含`n_total`、`n_Q_valid`、`n_Q_missing`、`coverage`、`Q_std_effective_n`和`Q_std_variance_divisor`。
- 所有跳过NaN的统计量必须有对应有效n列或独立长表`summary_denominators.csv`，不能共用一个含义不明的`n`。
- `rater_disagreement_gt_0_5_fraction`必须明确布尔分母；当前有至少一个有效组的记录均有range，不得把不存在的range静默比较成False。
- `extension_shift.csv`、相关性、bootstrap和报告表中的样本数必须是相应统计量的实际有效数。

### 3. 敏感性分析隔离

- 主结果列保持`Q_baseline`，敏感性结果使用不同名称，例如`Q_sensitivity_calibration_domain_median`。
- 保存`imputation_parameters_sensitivity.json`，逐域/特征记录候选总数、有限数、覆盖率、唯一有限值数、中位数、来源scope及门槛判定。
- 只对缺失特征进行替代；观测到的有限值不得被重写。
- 单独输出`sensitivity_domain_summary.csv`和`sensitivity_comparison.csv`，至少比较主分析与敏感性分析的有效数、域均值差、域排序变化及all_unique结果。
- 报告必须把插补结果称为敏感性分析，不得写成主Q、修复后的真实值或完整观测。

### 4. 旧终验逻辑

- 删除或替换“全部Q非空”的错误断言，改为核验`Q_valid`与11特征有限掩码完全一致、预期19条无主Q、其余主Q有限且在[0,1]。
- overlap复现、校准/留出键隔离、新扩展键隔离、记录数和联合键唯一性检查继续保留。
- 验证主Q未对缺失组重分权，敏感性参数未引用holdout/extension。

## 【日志与可恢复检查点要求】

运行必须拆为以下阶段，每阶段只能在输出、行数、关键计数和哈希校验通过后原子写入`COMPLETE`标记：

|阶段|最低输出|恢复规则|
|---|---|---|
|S00 preflight|输入/源码哈希、环境、命令、输出目录排他检查|任何版本不符即停止|
|S01 synthetic_tests|人工缺失、分母、插补来源和防fallback测试|未通过不得读取XZ|
|S10 scan_A1|A1完整特征检查点、审计、键状态及清单|检查点完整且哈希匹配时可复用|
|S11 scan_A2|A2完整特征检查点及与A1重叠状态|只能在S10有效后运行|
|S12 scan_A3|A3完整特征检查点及与A1重叠状态|只能在S10有效后运行|
|S20 score_primary|固定归一化参数、主组、Q及缺失标记|只从S10–S12检查点读取|
|S30 sensitivity|门槛审核、参数和独立敏感性列|任何门槛失败即停止，无fallback|
|S40 summarize|主汇总、敏感性汇总、诊断和报告|所有分母必须显式|
|S50 verify|端到端机器检查和证据对照|存在FAIL则不得标记完成|
|S60 finalize|run summary、交回说明、封闭日志、最终manifest|完成后不得再写被哈希文件|

每个XZ文件完成扫描后保存独立checkpoint及SHA256。进程中断时，可复用已经完整结束且输入/源码/配置哈希匹配的文件级checkpoint；正在扫描但未完成的文件不得标记完成，只重启该文件。不得因恢复而重扫已经验收的完整文件。

`run.log`和`stage_status.jsonl`必须及时flush，记录阶段开始/结束、输入/输出、记录数、耗时、内存观测、警告、异常栈和退出码。主进程及每个子命令的实际命令行必须落盘。

最终输出清单只能在所有被纳入哈希的日志和结果关闭后由独立finalizer生成；生成后不得继续追加这些文件。`output_manifest.json`排除自身。对清单的只读复核输出到控制台或清单之外，避免再次出现日志追加导致清单哈希陈旧。

## 【具体执行步骤】

1. **授权与预检。** 收到单独执行指令后创建唯一run目录。读取本施工单和Q01B决定；核对输入、源码、旧quality产物及Q01A/R1关键证据的哈希。记录Python、依赖、平台、时区、CPU及可获得的内存信息。
2. **先修改代码，不碰原始数据。** 实现版本化输出、阶段入口、Q有效标记、显式分母、敏感性隔离、检查点和终验。保存变更前后源码哈希及机器可读`changes.csv`。
3. **运行人工测试。** 至少覆盖：11特征全有效；professionalism缺失；reasoning缺失；两者同时缺失；0/1/2/3个有效组；Q不重分权；分歧统计skipna；Q标准差n与n−1；域内中位数只读calibration；A3 github门槛失败时硬停止；holdout/extension值被故意改变但插补参数不变。
4. **执行一次正式顺序扫描。** 按A1→A2→A3读取，每文件完成即校验和封闭checkpoint。解析失败、计数或版本不符时停止，不继续评分。
5. **构建主Q。** 只从文件级checkpoint加载；按固定归一化规则评分，生成主组、`Q_valid`和`Q_baseline`。不删除任何行。
6. **审核并构建敏感性分析。** 先输出每个所需域/特征的充分性表；全部通过后才能计算校准域内中位数敏感性列。失败时保存证据并停止，不进入汇总。
7. **生成汇总、诊断和报告。** 主结果和敏感性结果分表输出；所有统计使用各自明确的有效分母。bootstrap只能从有限主Q抽样，不能把NaN带入重采样数组。
8. **独立终验。** 验收脚本不得调用被测汇总函数生成期望值；从行级产物独立复算关键计数、分母、域汇总和插补参数来源。与Q01A/R1锚点比较。
9. **封闭和交回。** 关闭日志，写run summary与handoff，最后生成并复核output manifest。停止，不更新00–05，不运行其他模块。

## 【禁止事项】

1. 不得重新选择缺失处理策略或把敏感性插补升级为主分析。
2. 不得静默填0、删除19条记录、dropna后冒充全体或重分配三组权重。
3. 不得使用holdout、extension、全局或其他域数据估计敏感性插补参数。
4. A3 github的A1 calibration/github对应样本不足时不得fallback；必须失败停止并交主控。
5. 不得重新定义11个主Q特征、三组结构、指标方向、归一化范围或域等权校准方法。
6. 不得覆盖`solution/outputs/quality/`、旧报告、诊断目录或任何原始文件。
7. 不得并行启动多个正式全量扫描，不得反复解压同一已完成文件，不得把人工测试计数混入真实统计。
8. 不得运行配比、缩放、演化、优化或论文生成，不得联网获取新数据或安装新依赖。
9. 不得只因进程退出0就宣称通过；检查清单存在FAIL或关键项NOT_CHECKED时任务不得标记完成。

## 【必须输出的文件】

正式run目录至少包含：

|文件或目录|最低内容|
|---|---|
|`code_snapshot/`|实际运行源码和专项测试的冻结副本|
|`input_manifest.json`|原始输入、项目文档、源码、旧产物和Q01A/R1证据的路径、大小、mtime、SHA256及实际读取状态|
|`environment.json`|Python、依赖、平台、时区、种子、命令、资源限制|
|`run_config.json`|run_id、阶段、输出目录、Q01B规则、充分性门槛、恢复策略|
|`changes.csv`|修改文件、函数/区域、修改原因、前后行为及关联决定|
|`run.log`、`stage_status.jsonl`|逐阶段日志、异常栈、耗时、退出码和完成标记|
|`checkpoints/`、`checkpoint_manifest.json`|A1/A2/A3和评分阶段检查点、行数、哈希、依赖版本及可恢复状态|
|`audit.json`、`raw_field_counts.csv`|物理记录、联合键、重复/交叠、逐字段异常记录数和元素数|
|`normalization.json`|只由A1 calibration得到的固定变换及来源计数|
|`quality_features_scores.parquet`|全部272505条物理记录、25特征、主组、`n_groups_valid`、`Q_valid`、主Q、敏感性Q、身份/域/角色/缺失原因；不含正文|
|`domain_summary.csv`|六scope逐域主分析结果和四类覆盖字段|
|`summary_denominators.csv`|每个统计量的总n、有效n、ddof/方差除数、缺失比较规则|
|`imputation_parameters_sensitivity.json`|逐域/特征的calibration样本、门槛判定、中位数及来源证明|
|`sensitivity_domain_summary.csv`|敏感性Q的独立域汇总|
|`sensitivity_comparison.csv`|主分析与敏感性分析的覆盖、均值差、域排序变化和关键结论对照|
|`feature_summary.csv`、`extension_shift.csv`|有效分母已澄清的特征和扩展差异|
|`unresolved_indicator_correlations.csv`、`indicator_direction_pending.csv`|14项未纳入主Q指标的诊断，口径保持非方向证明|
|`conditional_bootstrap.csv`|只对有限主Q进行的条件IID行重采样及有效n|
|`verification.json`、`checks.json`|独立终验结果、PASS/FAIL/NOT_CHECKED及证据|
|`quality_baseline_q01c.md`|方法、覆盖率、主结果、敏感性、限制及产物说明|
|`run_summary.json`|状态、退出码、阶段耗时、关键计数、失败/未完成项、是否使用fallback|
|`handoff.md`|事实摘要、限制、运行入口、关键结果及主控待审项|
|`output_manifest.json`|除自身外最终交付文件的路径、大小与SHA256；生成后文件封闭|

允许在run目录增加必要的机器中间文件，但不得省略上述核心产物。失败运行保留已经产生的真实文件和失败状态，不用空文件伪装完成。

## 【必须记录的数值】

所有数值必须来自实际运行，不得手填预期值。至少记录：

- 每文件及合计物理行、解析成功/失败、唯一键、重复、A1交叠、域和角色计数。
- 25特征及11主Q特征逐scope/domain的有限、NaN、Inf和完整案例数。
- `Q_valid`真/假数量；主Q缺失特征、组及其交并集。
- 0/1/2/3个有效组的行数；分歧range/std及阈值统计的实际有效分母。
- 每个Q统计的四类覆盖字段，Q_std有效n与方差除数。
- 每个敏感性插补参数的来源域、特征、候选n、有效n、覆盖率、唯一值数、中位数和门槛结果。
- 实际插补的记录数/元素数，按域、角色和特征分列；主Q中不得出现插补计数。
- 主分析与敏感性分析逐域均值差、all_unique均值差、域排序是否变化。
- 每阶段墙钟时间、峰值RSS或监测不可用说明、实际命令和退出码。

## 【验收锚点】

以下是Q01A/R1已经验收的对照值。正式运行必须由新代码实际得到并比较，不能直接复制：

- 物理记录272505；唯一键261086；重复11419；解析失败0。
- all_unique的11特征完整261067、缺失19；25特征完整261067。
- professionalism缺失6，reasoning缺失13，交集0、并集19。
- 缺失域：wikipedia14、commoncrawl4、github1。
- 缺失角色：A1 calibration 13、A1 holdout 5、extension new 1、extension overlap 0。
- 19条各有2个有效质量组；261067条有3组；0/1组为0。
- all_unique分歧range/std有效n均为261086；主Q均值/标准差有效n均为261067；Q_std方差除数261066。
- extension overlap：A2=1419、A3=10000。

任何不一致必须输出实际值、期望值、差值、涉及行身份及原因；不得为通过验收而修改锚点。

## 【验收标准】

任务只有同时满足以下条件才可由执行AI标记`COMPLETE_PENDING_REVIEW`：

1. 人工测试全部PASS，并覆盖缺失传播、分母、插补来源隔离和硬停止行为。
2. 三文件成功顺序读取，记录/键/缺失锚点与Q01A/R1一致；无原始文件变化。
3. 行级产物保留272505条；all_unique主Q有效261067、无效19；无静默填0、删行或组权重重分配。
4. 所有Q相关表均有四类覆盖字段，且能从行级`Q_valid`独立复算。
5. 敏感性参数全部只来自A1 calibration对应域/特征；A3 github前置样本门槛通过；没有fallback。
6. 主分析与敏感性分析列、汇总、报告完全分离。
7. 旧quality、Q01A/R1及原始数据哈希保持不变。
8. 阶段日志、退出码、检查点、输入/输出清单完整；中断恢复没有重扫已完成文件。
9. 独立终验无FAIL；关键检查无NOT_CHECKED。允许与科学正确性无关且无法补证的历史限制继续登记，但不得用其掩盖当前运行缺证据。
10. 最终manifest生成后所有被列文件哈希保持一致，特别是日志不再追加。

## 【失败判据】

发生任一项即失败或部分失败，保存证据并停止：

- 输入版本、源码版本或检查点依赖与登记不一致。
- 人工测试失败仍继续读取原始数据。
- 任一原始文件解析失败或新运行关键计数无法与已验收锚点解释一致。
- 19条底层记录被删除、填0、获得主Q或导致组权重重分配。
- Q汇总继续使用总行数冒充有效分母。
- 敏感性参数读取holdout/extension或发生任何未授权fallback。
- A1 calibration对应域/特征未通过充分性门槛仍继续插补。
- 覆盖旧quality产物、原诊断证据或原始数据。
- 检查点损坏仍被复用，或已完成文件在无版本变化时被重复解压。
- 独立终验有FAIL，输出manifest缺文件/哈希不符，或运行结束后继续修改被哈希文件。

## 【停止条件】

1. 达到失败判据时立即停止，保留run目录、错误栈、阶段状态和已完成检查点，不自动换策略或重跑全量。
2. A3 github或其他实际缺失域/特征不满足插补充分性门槛时，停止并交主控裁决。
3. 发现实际缺失特征、行数、域或角色分布超出Q01A/R1证据时，停止；不得把新增异常自动纳入旧19条策略。
4. 正式运行完成并交齐材料后停止，不启动T03扩展研究、配比、缩放、演化、优化或论文工作。

## 【完成后必须交回的材料】

- 正式run目录绝对路径和run_id。
- 实际执行命令、开始/结束时间、各阶段退出码及是否发生恢复。
- 代码变更清单与冻结源码哈希。
- 原始数据、旧quality、Q01A/R1未变化的证据。
- 主Q覆盖、显式分母、分歧分母和19条缺失传播的机器结果。
- 敏感性参数来源、充分性门槛、插补数量及主/敏感性差异。
- 全部检查结果、失败/NOT_CHECKED项、输出manifest复核结果。
- `handoff.md`和主控需要重点审查的风险，不得自行更新00–05或宣布项目层最终验收。

施工单编制完成后停止。本文件本身不授权执行TASK-Q01C。
