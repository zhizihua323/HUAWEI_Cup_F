# TASK-Q01A 正式施工单：质量缺失模式诊断

状态：**施工单已编制，未执行。只有收到单独的执行指令后才能开工。**

本单编制于2026-09-24，依据已确认的恢复报告和00–05项目文档。本次仅创建本施工单，不启动数据扫描，不生成诊断结果，不恢复质量流水线。

所有相对路径均相对于：

`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace`

## 【任务编号】

TASK-Q01A。对应恢复问题P01及原待办T01的证据诊断部分。

原T01拆为两个阶段，权限边界如下：

|阶段|职责|执行权限|进入下一阶段的条件|
|---|---|---|---|
|TASK-Q01A|质量缺失模式诊断|执行型AI只产生可复核的客观证据；不得选择或实施最终处理策略|诊断材料交回主控GPT，等待审查|
|TASK-Q01B|质量缺失处理策略裁决|主控GPT在证据充分后决定最终处理策略及理由；本单不授权执行该阶段|由主控另行给出审查结论及后续施工单|

即使原04文档T01仍把“确定策略”与诊断写在同一行，本执行任务也只适用本单Q01A边界。不得以旧待办的宽泛表述扩大权限。

## 【任务名称】

质量缺失模式诊断：原始非有限值、特征失效、完整案例、评分缺失传播及汇总有效分母审计。

## 【任务背景】

恢复阶段发现：旧质量审计记录中存在含NaN的列表；现有代码将不合法列表转为NaN标量，质量组和总Q使用`skipna=False`，而`summarize()`中的均值默认跳过NaN，导出的`n`仍为总行数。旧质量终验要求全部Q非空，但没有终验文件或行级得分文件。

既有汇总显示commoncrawl、wikipedia和github存在有效特征数不足。现阶段缺少逐记录身份、缺失特征交集、完整主Q案例数、各组和总Q实际分母等证据。已有恢复数值只能作为待核对的历史基准，不能代替本任务运行结果，也不能据此认定当时在哪一行中断。

## 【目的】

建立从“原始字段异常→当前标量提取失效→归一化有效性→质量组/总Q缺失掩码→汇总有效分母”的可追溯证据链，回答谁缺失、缺什么、重叠多少、在哪些域及验证角色集中、如果只统计完整案例会少多少记录。

本任务只输出诊断事实及待裁决问题；不产生新的最终Q，不选择插补、删除、填0或任何最终处理策略。

## 【为什么现在必须先做】

1. 旧汇总的总行数不等于各统计量有效分母，必须先弄清口径，才能审查缺失处理对域比较和验证划分的影响。
2. 只知道各特征缺失数量，无法推导缺失记录并集；同一行可能缺失多个指标，不能直接相加。
3. 主Q使用11个特征，而现有审计展开为25个特征；全特征完整性与主Q完整性不是同一概念。
4. 直接续跑旧流水线可能再次在非空断言处失败，也可能生成未说明缺失覆盖率的汇总。
5. 在缺失集中程度和覆盖损失未明确前，选择最终策略会把未经论证的建模决定交给执行环节。

## 【输入文件】

以下均只读：

- `solution/src/quality_audit.py`：字段、提取、联合键、划分及统计逻辑；仅静态阅读，不运行、不直接导入。
- `solution/src/common.py`、`solution/config.json`：路径、随机种子及已有约定；仅静态读取必要内容。
- `solution/outputs/quality/audit.json`。
- `solution/outputs/quality/normalization.json`：只用于识别既有特征组和固定变换及其有效性；不重新估计分位数或权重。
- `solution/outputs/quality/domain_summary.csv`、`feature_summary.csv`、`extension_shift.csv`。
- `solution/outputs/audit/raw_source_manifest.csv`、`environment.json`。
- `recovery/2026-09-24/quality_gap_evidence.json`、`quality_missing_feature_counts.csv`、`quality_mean_discrepancies.csv`、`verification.json`。

行级`quality_features_scores.parquet`在恢复时不存在，不得假定它已生成。若执行时出现新产物或输入版本改变，先记录状态变化，停止等待主控确认版本，不自行混合新旧结果。

## 【允许读取的项目文档】

必读本施工单、`00_PROJECT_BRIEF.md`、`01_PROJECT_STATUS.md`，以及`05_REVIEW_LOG.md`中的P01/P02。需要路径、已有决定、任务依赖时才查阅`02_DECISIONS.md`、`03_DATA_CATALOG.md`、`04_TASK_QUEUE.md`和`恢复报告.md`。

不需要历史聊天、其他模块源码、成品论文、全部参考资料或互联网检索。仅在字段定义无法由许可输入澄清时，可定点查阅`F题/数据说明.pdf`中附件A字段说明；仍有歧义则登记并交回，不扩大搜索或自行重定义指标。

## 【允许读取的原始数据】

仅限以下三份文件，并仅在未来获得执行指令后读取：

|ID|路径|
|---|---|
|A1|`F题/real_attachments/A_data_value/slimpajama_quality_signal_sample.jsonl.xz`|
|A2_arxiv|`F题/real_attachments/A_data_value/slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz`|
|A3_github|`F题/real_attachments/A_data_value/slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz`|

诊断需要完整行级缺失交集；旧汇总不能提供这些信息。未来执行范围允许**每文件至多一次完整顺序解压诊断扫描**，不进行完整质量建模或训练计算。本次编制施工单不授权这次扫描。不得以抽样结果冒充全量结论。

提取字段仅限ID、sub_path、来源域、22个质量原始字段及必要的行号/类型信息。JSON解析可能经过content字段，但不得保留、输出或分析正文；不读取A18、其他A表、B表、C表。不要把原始解压文件复制到磁盘。

压缩文件SHA256须实际计算并与旧清单比较；可另做一次压缩字节顺序读取，或在解压输入层同时计数/哈希。这不是允许再次解压扫描。

## 【禁止修改的文件】

- 全部`F题/`原始材料，尤其A1–A3。
- 全部`solution/src/`、`solution/config.json`、`solution/README.md`。
- 全部`solution/outputs/`及`solution/reports/`，包括旧quality五份产物和语义来源文件。
- 已有`recovery/`内容、根目录00–05、恢复报告、本施工单及参考资料。

获准执行后的唯一写入区为新建目录：

`diagnostics/TASK-Q01A/<run_id>/`

`run_id`使用实际启动时的本机时间和唯一后缀。目录已存在时不得覆盖，另建新目录。临时文件、诊断脚本、日志、失败记录全部写在该目录。任务完成后由主控审查并维护00–05，执行AI不自行把P01标记为解决。

## 【必须检查的内容】

### 1. 原始字段与当前提取结果分别审计

覆盖全部22个原始质量字段与25个展开标量特征，不只检查已经发现异常的几个指标。字段和展开顺序以当前源码静态提取的`FIELDS`、`FEATURES`为准，保存映射；与normalization中的主Q组不符时停止，不补猜。

原始层逐字段记录：字段不存在、null、类型不符、列表长度不符、非数值元素、NaN、+Inf、-Inf。标量同时记录行数；列表分别记录异常元素数、含该异常的行数及总列表行数。异常类型可能在同一行共存，不允许将非互斥原因数量直接相加当并集。

提取层严格复述当前`get_features()`的行为，区分“原始缺失/非有限”与“因列表任一元素异常而整字段失效”。特别审查qurater的4个输出是否因同一原始列表异常共同失效；不得改为部分接受列表。对数字字符串、bool等只登记源码实际接受/拒绝行为，不替换成新的清洗规则。

每个展开特征分别统计NaN、+Inf、-Inf、非有限并集及有限值数；所有特征即使计数为零也要输出。

### 2. 行身份、重复与分层口径

每个物理记录用`file_id + source_line`唯一定位；联合业务键复现当前源码的`(str(id), str(sub_path))`及其JSON序列化/哈希。保留原始ID类型与缺失标记，避免字符串化掩盖键异常。

固定扫描顺序A1→A2→A3，复现`is_unique_first`、`overlap_a1`、当前质量字段指纹和源域判定。不删除重复记录；“唯一键视图”仅是另一个统计口径，每条物理记录仍须进入行级诊断清单。发现同键不同域或不同质量字段时记录冲突，不自行挑选代表值覆盖冲突。

划分必须复现当前代码：`SEED=20260924`，按`str(SEED)+key_json`的SHA256前16个十六进制位转整数后模5；A1余数0为holdout，其余为calibration；扩展分为overlap_A1和new_records。不得重新随机划分。输出主观测口径和唯一键口径，避免交叠样本重复计入全量唯一数。

必须包括旧汇总六个scope：`A1_calibration`、`A1_holdout`、`A1_all_unique`、`extension_overlap_A1`、`extension_new_records`、`all_unique`；各自按域分层并有ALL总计。另按file_id和evaluation_role输出物理行统计。scope存在重叠，不能把六类n简单相加当总数。

### 3. 缺失交集、并集和域集中程度

分别对“当前提取后NaN”和“当前提取后非有限”生成25特征掩码；主Q11特征另有固定子掩码。输出单特征集合大小、两两交集/并集、实际出现的完整缺失模式及模式计数；不得穷举全部2^25种组合。

输出每域/每角色的缺失数、分母、缺失率、占全部缺失记录的比例。没有缺失时占比记null并标明原因，不输出误导性的0/0。只作描述，不把“集中”推断成MCAR/MAR/MNAR或因果机制。

### 4. 11个主Q特征与三个质量组的有效性

当前组定义如下，执行时须与只读输入比对：

|组|现有特征|
|---|---|
|usability|ad_en、fluency_en、modernbert_readability、modernbert_cleanliness、qurater_writing_style|
|knowledge|modernbert_professionalism、qurater_required_expertise、qurater_facts_trivia|
|education_reasoning|modernbert_reasoning、fineweb_edu、qurater_educational_value|

分别给出每组全部构成特征有限的案例数、全部构成特征非NaN的案例数，以及11特征完整案例数。全25特征完整案例数作为另一个指标，不与11特征混用。

在固定旧normalization参数下，仅诊断各归一化输入的NaN/Inf传播、裁剪及数值有效性；不得重新拟合转换参数。要分清原始Inf、提取NaN和归一化后状态，不能假设`isfinite`与`notna`在所有层上等价。

### 5. 当前Q缺失传播及summarize的分母

依据当前运算语义，生成`would_group_*_be_nan`、`would_Q_be_nan`及其触发特征列表，只计算诊断掩码，**不计算或导出数值型Q_baseline或新质量组得分**。允许在内存中用固定旧变换检查单特征有限性；不累积全量评分结果。使用小规模人工NaN/Inf样例核验掩码与pandas传播规则，样例结果单列，不能混入真实计数。

若发现Inf或变换溢出使上述逻辑掩码不足以精确确定组/Q状态，输出异常证据并停止交回，不以生成全量Q来绕过边界，也不默认所有非有限都等于NaN。

逐scope、domain、统计量登记旧`summarize()`实际分母：

- `n`是总行数。
- `Q_mean`/各group mean的默认`skipna=True`分母为该量非NaN行数，不能自动解释成全部有限行数。
- Q标准差的有效n及`ddof=1`分母n−1；Q分位数的有效样本数。
- 分歧range/std的行内有效组数，包含0组、1组、2组、3组分布；range默认跳过NaN，std使用源码中的ddof。随后跨行平均的有效n须分别统计。
- `rater_disagreement_gt_0_5_fraction`中，缺失range比较`>0.5`会成为False；其均值分母仍可能为全部行数。记录这种行数贡献，不重新计算分歧分数或阈值结论。
- `equal_indicator_Q_mean`和`without_knowledge_Q_mean`分别按当前构成特征的缺失掩码确定分母，不因都是Q派生量而共用分母。

对于仅靠掩码无法确定的数值现象，标明不能判断，不生成缺乏依据的分母。按源码和缺失掩码核对所有分母的代数关系。

### 6. 已知异常域与complete-case计数假设

对commoncrawl、wikipedia、github输出单独对照，至少分calibration、holdout、A1全体、扩展重叠、扩展新增和全部唯一键。说明每项有效n差多少，哪些特征失效同属一行，A1与扩展是同一键重复还是新增异常；域无相应样本时记n=0，不伪造记录。

仅计算假设“主Q11特征都有限”的保留数、未覆盖数和比例，并按域/角色/来源细分；25特征全完整作为独立对照。名称使用`complete_case_count_only`，不得写成建议方案、清洗后的数据集或采用该策略的结果。不得真正删除记录、生成删行后的数据副本、评价处理后的模型效果。

## 【具体执行步骤】

1. **确认授权和版本。** 只有单独执行指令到达后启动。定点读取许可文档；创建独立run目录，记录实际开始时间。对输入源码、配置、旧quality产物、恢复证据记录SHA256。禁止联网、安装环境或启用子代理。
2. **建立独立诊断实现。** 在run目录写`diagnose_missingness.py`。静态读取并对照既有逻辑，禁止import项目模块造成写入副作用。将字段/提取/联合键/划分/掩码实现的来源和对应函数写入`diagnostic_spec.json`。不编写策略选择器或修复函数。
3. **先做轻量逻辑自检。** 用人工结构正确/错误、NaN、±Inf、重复键以及部分组缺失的样例，检查特征分类、非互斥原因、联合键、集合计数和pandas分母语义。测试只验证诊断逻辑，结果标为synthetic。不扫描原始数据作试跑后再重扫。
4. **核验原始文件版本并单遍扫描。** 计算三份压缩文件哈希；与已登记版本冲突时停止。逐行解析、记录物理身份、域、角色、重复/重叠、字段异常及25特征掩码。内存仅保留必要键、指纹、掩码和聚合计数，正文即时释放。进度写日志，每处理一个文件及固定间隔记录行数/耗时。
5. **生成客观计数。** 同时输出行级诊断清单、异常字段长表；由掩码计算交集/并集、模式、主Q与各组完整数、would-Q缺失身份、旧统计分母及complete-case损失。所有统计由脚本生成，禁止人工填写结果单元格。
6. **核对旧证据。** 比较旧audit/feature_summary/domain_summary的行数、非缺失数和口径。本单不重算旧Q均值，只把已有均值标为`prior_artifact`供定位，不能当本次重新运行结果。差异记录actual、expected、difference、scope及解释是否已证实；不修改旧表。
7. **执行独立计数验收。** 从诊断行级掩码重新聚合，核对所有CSV和JSON总量；每个异常可回指源文件行号，所有正常记录也保留。核验输入和旧产物未改动，输出文件哈希、运行结束信息及检查清单。
8. **交回并停止。** 生成精简handoff，只列事实、差异、限制和交给Q01B的问题。不得选择最终策略，不启动Q01B/T02/T03或重跑quality主脚本。

额度与资源边界：单进程CPU，无GPU、拟合、bootstrap、模型评分调用或网络。默认执行上限为20分钟墙钟、约2GiB峰值进程内存；在支持监测时记录实际RSS，否则记录监测不可用及替代观测，不能伪填峰值。触及任一边界即保存部分证据并停止，不自动加资源或反复重试。此上限是本单运行约束，不是已测性能结论；调整须由后续明确指令给出。

## 【禁止事项】

1. 不得决定、推荐或实施最终插补、删除、填0、均值/中位数替代、重权重、缺失指示建模等处理策略；必须交由主控GPT在Q01B裁决。
2. 不得静默填0，不得删除任何原始记录或异常记录，不得dropna后把剩余样本冒充全体。
3. 不得重新构造最终Q、输出新的数值型Q/质量组得分、重新估计归一化分位数、改变指标方向或权重。
4. 不得修改A1–A3，不得覆盖旧quality产物，不得调用quality_audit.py的main、stream_audit、score_quality、summarize等写出流程。
5. 不得把完整案例计数视为选择complete-case；不得以缺失率低为由直接认定删除无影响。
6. 不得根据恢复文档、估计、聊天或期望值填入运行结果；历史值必须标明出处，与本次计算分列。
7. 不得将NaN、±Inf、null、缺键、类型错误、列表异常合为无法追溯的“缺失”；可提供统一失效掩码，但原因必须保留。
8. 不得运行A/B/C其他模型、全量质量流水线、重新训练、全量打分、相关性扫描、重采样或论文生成；不得创建后台任务或自动续跑。
9. 不得宣称本任务修复了P01、证明缺失随机、确定旧中断原因或已完成题目质量评价。

## 【必须输出的文件】

以下全部放在`diagnostics/TASK-Q01A/<run_id>/`，成功状态下不得缺项；无异常的长表也须保留表头。失败时仅交已有材料及明确的未产出清单，不能用空表伪装完成。

|文件|最低内容/机器字段|
|---|---|
|`diagnose_missingness.py`|本次实际执行源码，路径自定位，只写run目录；不包含最终策略实现|
|`diagnostic_spec.json`|22→25字段映射、11主Q特征、三组、联合键/划分规则、scope定义、计数口径、源函数及哈希|
|`input_manifest.json`|实际输入路径、字节、mtime、SHA256；实际读取/未读取列表；与旧版本比对|
|`environment.json`|下节运行环境、种子、实际命令与资源限制|
|`run.log`|开始、阶段、文件、进度、耗时、警告、结束/错误栈；定期flush|
|`raw_field_counts.csv`|file_id、domain、field、n_rows、各异常行数/元素数、有限元素数、原始类型/长度分类；物理行口径|
|`feature_missing_counts.csv`|scope、domain、feature、n_total、n_nan、n_posinf、n_neginf、n_nonfinite、n_finite、rate_nonfinite；25特征全覆盖|
|`row_masks.csv.gz`|全部物理行：file_id、source_line、原始id/sub_path的JSON表示、key_sha256、domain、evaluation_role、is_unique_first、overlap_a1、各层掩码、would_group_*_be_nan、would_Q_be_nan、触发特征列表；不得含数值Q/正文|
|`invalid_values.csv.gz`|仅异常事件：行身份、field/feature、层级、reason、list_index、异常值类别及简短值表示；用于追溯，不复制全文|
|`missing_patterns.csv`|scope、domain、mask_kind、feature_mask、feature_names、n；包含全有效模式，输出实际出现组合|
|`missing_pairwise.csv`|scope、domain、mask_kind、feature_i/j、n_i、n_j、n_intersection、n_union；含对角计数和零计数|
|`validity_counts.csv`|scope、domain、n_total、25/11特征完整数、各组非NaN数/有限数、would_Q_nan数、有效主Q数、各比例|
|`summary_denominators.csv`|scope、domain、statistic、n_total、n_nonmissing、n_finite、n_effective、ddof、denominator_rule、missing_comparison_as_false_n及适用性说明|
|`known_domain_comparison.csv`|三个异常域按来源/角色/scope的具体计数差异、旧值出处、当前值、差值、重叠/新增分类；无样本明确n=0|
|`complete_case_count_only.csv`|scope、domain、feature_set（11或25）、n_total、n_complete、n_not_covered、fraction_not_covered、diagnostic_only=true|
|`comparison_with_prior.csv`|旧文件/字段、旧口径、expected_prior、actual_run、difference、match、已证实解释或unresolved；所有历史值有来源|
|`checks.json`|逐项验收PASS/FAIL/NOT_CHECKED、实际数量、容差和证据路径；人工样例检查单列|
|`run_summary.json`|COMPLETE_DIAGNOSTIC/FAILED/PARTIAL、退出码、开始结束、时长、实际读取数量、关键数值、未完成项、final_strategy_selected=false、final_Q_recomputed=false|
|`output_manifest.json`|除自身外全部交付文件的路径/字节/SHA256|
|`handoff.md`|不超过约1500中文字的事实摘要、问题、限制、文件入口及交给Q01B的待裁决问题；不得给最终策略建议|

CSV使用UTF-8（可带BOM），整数计数不得以缺失代零；JSON严格输出，不允许裸NaN/Infinity，以null加状态字段表达未定义。列表或原始ID结构用合法JSON字符串嵌入CSV，保证机器可逆读取。浮点比例必须随附分子和分母。

## 【必须记录的数值】

所有本任务结果必须来自实际诊断代码运行；施工单不预填这些结果。

1. 三文件物理行数、解析成功/失败数、唯一键数、重复出现数、跨文件交集数、同键质量/域冲突数；六scope及域/角色样本数。
2. 22字段的缺键/null/类型/长度/非数值/NaN/+Inf/−Inf计数，列表按行和元素分开；25特征的提取后各类缺失/非有限数。
3. 任意特征缺失并集、两两交集/并集、实际多特征模式计数；主Q11与全25的集合各自报告。
4. 三组、11主Q、25全特征的完整案例数和比例；每组有效与缺失掩码的交集/并集。
5. 当前逻辑将导致Q为NaN的物理行数及唯一键数、具体行身份、触发特征和来源层；所有相关集合的重叠，不重复相加。
6. 每个summarize统计量的总n、非NaN n、有限n、实际有效分母；std的n−1与比较False计数另列。
7. calibration、holdout、extension_overlap、extension_new的上述有效数；扩展合计同时保留物理行与唯一键口径，不能模糊写“extension”。
8. commoncrawl/wikipedia/github与其他域的缺失数/率及占比；已知异常在校准/留出、重复/新增之间的具体分布。
9. complete-case仅计数假设下未覆盖的行数/键数、各域各角色损失比例，不改变任何记录。
10. 与旧审计/汇总的各项计数差值、实际输入/输出字节数、耗时、资源观测和检查PASS/FAIL数量。

## 【需要记录的运行环境】

- Python可执行文件绝对路径与实际版本；优先使用现有`D:\anaconda\python.exe`，不得仅照抄旧环境JSON。
- 操作系统、架构、工作目录、时区；ISO 8601开始/结束时间和单调时钟耗时。
- 实际使用的numpy/pandas及其他第三方库版本；未使用的库不要求安装或探测。
- 脚本SHA256、相关项目输入SHA256、实际执行命令、退出码、SEED与分割规则。
- 是否启用UTF-8、单进程CPU、资源上限、实际可观测峰值内存及测量方式；不可测项明确unknown。
- 日志中的读取文件顺序、每文件解压次数、解析行数及是否出现重试。不得填入未执行的MATLAB、GPU或模型版本验证结果。

## 【验收标准】

1. 交付清单齐全可读；所有结果有实际运行记录和数据/脚本哈希；结果能够由诊断行掩码重复聚合，无需再解压原数据。
2. 每个物理记录均在row_masks保留，不因异常或重复而删行；唯一键仅另设统计视图。每条异常可定位到原文件行号。
3. 每层NaN、±Inf等类别边界清楚；非有限计数满足`n_total=n_finite+n_nonfinite`，NaN、+Inf、−Inf提取状态互斥并可相加；原始事件原因非互斥时不可强行套用该等式。
4. 缺失模式计数之和等于对应scope n；各特征边际与pairwise对角一致；并集满足容斥；11主Q完整数与相应失效并集补集一致（明确使用提取层还是归一化层）。
5. 三组的有效掩码交集与当前Q缺失传播掩码可核对；同一业务键的重复记录若异常状态不同，必须输出冲突而不能掩盖。
6. 六scope、所有来源与角色、异常域的分母均可由行级数据重建；全样本n与有效n分开，不把物理行/唯一键/角色口径混在一列。
7. 旧值比对中的每个不一致均已列出证据和是否解决；实际数值不符合历史记录时报告差异，不为了“通过”修改计数。不得以无解释的不一致标记COMPLETE_DIAGNOSTIC。
8. complete-case文件只含计数/覆盖率，不包含处理后的样本集或推荐结论；没有任何新最终Q、修改后的权重或归一化参数。
9. 对许可输入及旧quality文件执行前后哈希一致性检查。原始XZ扫描实测哈希与清单一致，结束时至少核对大小/mtime未变；若声明原始文件前后哈希一致，须实际另读压缩字节完成后验哈希，不得用mtime冒充。
10. checks中无未解决的关键计数/传播问题，run_summary如实给出最终状态；结果足以由主控审查Q01B，但不预设主控一定接受任何策略。

## 【失败判据】

- 找不到许可输入、原始SHA不符、源码/配置/旧产物版本冲突，或字段组/划分定义不一致。
- 出现无法解析行、身份键异常或同键内容冲突而没有明确诊断记录；不得静默continue后声称全部正常。解析失败须保留物理行占位及错误定位，不能以删除该行规避验收。
- 内部计数、集合、分母或旧审计比对存在未解释差异；以失败/部分诊断交回，不能捏造一致。
- 必须重建数值Q、改变当前处理逻辑或自行选最终策略才能继续时，立即交回主控；该情况不是扩权理由。
- 写入许可目录以外、删除记录、静默填0、覆盖旧结果、修改原始数据，均为任务违规，立即停止并记录影响。
- 触及资源上限、进程异常、输出磁盘不足、环境缺少必要依赖，均保留已有日志，不自动安装、升级、续跑或循环重试。

关键检查失败时诊断进程应非零退出，并在run_summary写FAILED或PARTIAL；“成功写出审计报告”不等于“所有数据检查通过”。

## 【停止条件】

当前编制轮：本施工单写入并完成文档结构核对后立即停止，**不得开始TASK-Q01A**。

未来执行轮：诊断交付和验收结束后停止；任一失败判据触发则提前停止，记录已有证据与缺口。不得自动进入Q01B、修复质量流水线、重新评分或全量建模。

Q01A成功只意味着客观诊断材料完成，不意味着P01关闭。最终策略由主控GPT在充分诊断证据下审查裁决，若证据不足则另发补充诊断单。

## 【完成后必须交回的材料】

- run目录绝对路径、`handoff.md`、`run_summary.json`、`checks.json`和`output_manifest.json`。
- 全部机器可审查CSV/JSON、压缩行级掩码及异常事件表、实际诊断源码和运行日志。
- 简洁列出：11特征完整率、各组/总Q有效分母、缺失并集及交集、异常域/角色分布、complete-case计数损失；每个数字指向输出文件，不靠文字转述孤立结论。
- 明确说明未修改哪些输入、是否有失败/未检查项、哪些结论尚不能判断。
- 向主控提出需Q01B裁决的问题：缺失处理原则、是否区分域/角色、覆盖率与可比性的权衡、分母披露及后续验证要求；**只列问题，不给最终策略或默认选项**。
- 固定交回声明：`本次仅完成缺失模式诊断；未选择或实施最终缺失处理策略，未删除记录、未填0、未生成最终Q、未覆盖旧quality产物。等待主控GPT审查TASK-Q01B。` 若任何一句不符合实际，必须改为如实披露并判失败，不能照抄虚假声明。
