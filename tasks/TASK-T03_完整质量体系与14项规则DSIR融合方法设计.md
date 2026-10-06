# TASK-T03正式施工单：完整质量体系与14项规则/DSIR融合方法设计

状态：**方法设计施工单已编制，未执行。** 本文件只定义候选模型、验证协议、淘汰规则和后续交付物。未获得单独执行授权前，不得运行全量计算、重新扫描A1–A3、修改现有主Q或把任何候选方案登记为最终融合方法。

编制日期：2026-09-25。所有相对路径均相对于：

`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace`

## 【任务编号】

TASK-T03。

前置可信基线：TASK-Q01C正式科学run已通过；恢复与日志机制经Q01C-R2补证后通过。现有主Q由11个模型标量特征构成，261086个唯一键中261067个`Q_valid=True`、19个`Q_valid=False`。19条缺失记录的主分析和敏感性处理已经关闭，不属于T03研究对象。

## 【任务名称】

完整质量体系：剩余11项规则指标与3项DSIR指标的语义裁决、候选融合及实证验收设计。

## 【T03建模目标】

1. 固化22个原始质量字段到25个展开标量特征的可追溯映射，并区分原始值域、提取值域、既有归一化范围和后续待统计的经验范围。
2. 对未进入主Q的14项RULES/DSIR逐项判断：能否定义质量方向、是否更适合区间最优、是否只应作为诊断或控制变量、是否证据不足。
3. 在不覆盖现有`Q_baseline`的前提下，比较至少三类完整质量候选：分层稳健融合、全特征统一融合、主Q加规则修正项；保留“主Q不变”作为必要对照。
4. 将“冲突”定义为可计算、可验证的多指标不一致与跨视角不一致，建立冲突标记、可信度和必要时拒绝给出单一分数的规则。现有`rater_disagreement_range/std`只作为基线诊断，不得称为冲突已经解决。
5. 预先冻结训练、验证、外推和重采样协议，禁止在同一数据上选权重并宣称泛化成功。
6. 为后续T06提供候选A数据质量量`Q_A`、组成分量、适用域、置信度和版本信息。T03不得假定`Q_A`与B表`Q_score`同尺度；二者的桥接、单调映射和不确定性必须另行标定。

本任务的“成功”是形成经实证支持的候选及其边界，不要求14项全部进入标量Q。若证据表明部分指标只适合诊断或域条件变量，将其排除是合格结果。

## 【输入与允许读取范围】

### 方法设计阶段只读输入

- `01_PROJECT_STATUS.md`、`02_DECISIONS.md`、`03_DATA_CATALOG.md`、`04_TASK_QUEUE.md`、`05_REVIEW_LOG.md`。
- `tasks/TASK-Q01B_质量缺失处理策略裁决.md`及Q01C/R1/R2施工单。
- `diagnostics/TASK-Q01A/20260924T142229+08/diagnostic_spec.json`。
- `solution/outputs/quality_q01c/20260924T215718+08/normalization.json`。
- `solution/outputs/quality_q01c/20260924T215718+08/feature_summary.csv`。
- `solution/outputs/quality_q01c/20260924T215718+08/indicator_direction_pending.csv`。
- `solution/outputs/quality_q01c/20260924T215718+08/unresolved_indicator_correlations.csv`。
- `solution/outputs/quality_q01c/20260924T215718+08/domain_summary.csv`及`summary_denominators.csv`。
- `solution/outputs/quality/semantic_sources/`中的README、feature order、PRRC提示词及冻结清单。
- `solution/src/quality_q01c.py`，只用于确认当前提取语义，不运行。

### 后续实证执行允许使用的主要输入

- 已验收行级表：`solution/outputs/quality_q01c/20260924T215718+08/quality_features_scores.parquet`。
- 上述正式run中的身份、域、角色、主Q、25特征、分母和诊断产物。
- 后续外部一致性阶段可只读现有RegMix/Loss产物和相应数据说明；具体可用表、连接键、训练/验证口径必须在执行前写入run config。没有可靠文档级映射时只能输出`NOT_IDENTIFIABLE`，不得模糊连接。

后续T03执行原则上不需要重新读取真实A1–A3。若发现正式行级表缺少不可替代字段，应停止并交主控决定，不得自行重新解压原始数据。

## 【禁止修改与禁止事项】

1. 不修改或覆盖现有`Q_baseline`、`Q_valid`、三个主组分数及Q01C正式run。
2. 不修改`02_DECISIONS.md`中的最终融合方法；只有后续实证通过且经主控裁决后才能登记新决定。
3. 不重新讨论、插补、删除或重加权已经关闭的19条缺失记录；所有候选的主比较使用与Q01C一致的261067个唯一完整案例，另行显式报告覆盖率。
4. 不因14项指标存在就强制全部纳入；不能定义方向或无法稳定验证的指标保留为诊断量。
5. 不把PCA主成分的正负号或方差解释为质量高低；PCA只能用于冗余结构和无监督敏感性对照。
6. 不把相关性解释为因果，不把域间均值差解释为指标造成的质量差。
7. 不在A1 calibration之外拟合变换、方向阈值或权重；A1 holdout、extension overlap和extension new不得用于调参。
8. 不使用extension数据训练权重、选择候选、设定方向或确定截断点。
9. 不使用同一批样本选择权重并报告其拟合表现为泛化结果。
10. 不将A数据的候选Q直接当作B表`Q_score`，不得在T03中假定等比例、等区间或一一对应。

## 【25展开特征/22字段结构】

### 映射和范围解释规则

- “理论/提取值域”来自字段定义和冻结提取代码；不能确认边界时明确写为“有限实数，边界未知”，不得拿校准分位点冒充原始最小值或最大值。
- 后续执行必须从正式行级表按`A1_calibration`、`A1_holdout`、`extension_overlap_A1`、`extension_new_records`和`all_unique`分别报告`min/max/p01/p05/p50/p95/p99`、唯一值数、零膨胀、截断占比及尾部指标。该经验范围只描述样本，不升级为理论范围。
- “既有截断”仅指现有11项主Q的Q01C归一化；14项当前没有获准的质量方向或归一化。
- 14项RULES/DSIR在Q01C中均完整；25项的19个不完整案例只来自`modernbert_professionalism` 6条和`modernbert_reasoning` 13条，交集0。T03不得重新处理这些缺失。

|序号|类别|原始字段|展开方式与展开特征|理论/提取值域|方向与单调语义|截断、离散或长尾|缺失|主要重复信息候选|
|---:|---|---|---|---|---|---|---|---|
|1|RULE|`rps_doc_frac_no_alph_words`|标量原样→同名特征|比例，语义上`[0,1]`；经验越界须单列|非字母比例过高可表示噪声，但代码、数学文本例外；不预设全域单调|边界堆积可能；域条件明显|已确认完整|与数字字符比例、域类型、cleanliness可能重叠|
|2|RULE|`rps_doc_mean_word_length`|标量原样|非负连续值；上界未知|过短或过长均可能异常，优先区间最优|右尾、语言与代码域差异|已确认完整|与无字母比例、词数/句数及域类型相关|
|3|RULE|`rps_doc_frac_unique_words`|标量原样|比例，语义上`[0,1]`|过低可能重复，极高可能碎片化或短文效应；优先区间型|受文档长度影响，边界值可能集中|已确认完整|与unigram entropy及top n-gram集中度重叠|
|4|RULE|`rps_doc_unigram_entropy`|标量原样|非负连续值；上界依词表/长度|高值既可能多样也可能噪声；优先区间或饱和型|长度相关、右尾|已确认完整|与unique fraction、重复集中度重叠|
|5|RULE|`rps_doc_word_count`|标量原样|非负计数|文档长度不是质量本身；只作控制、分层或饱和变换候选|离散、强右尾|已确认完整|与句数、平均词长、截断长度重叠|
|6|RULE|`rps_lines_ending_with_terminal_punctution_mark`|标量原样|比例，语义上`[0,1]`|自然散文中可能正向，代码、列表和公式中不成立；域条件/区间型|可能零膨胀或边界堆积|已确认完整|与readability、writing style、域类型重叠|
|7|RULE|`rps_lines_numerical_chars_fraction`|标量原样|比例，语义上`[0,1]`|数字密度是内容类型，不是普适质量；仅诊断/控制|零膨胀、域差异和右尾|已确认完整|与无字母比例、math/代码域及DSIR-math重叠|
|8|RULE|`rps_lines_uppercase_letter_fraction`|标量原样|比例，语义上`[0,1]`|极高可能噪声，适度大写可能合法；优先区间型|零膨胀、边界值|已确认完整|与cleanliness、格式/域类型重叠|
|9|RULE|`rps_doc_num_sentences`|标量原样|非负计数|句数主要表示长度和切分方式；只作控制/分层|离散、强右尾、依赖分句器|已确认完整|与word count高度语义重叠|
|10|RULE|`rps_doc_frac_chars_top_2gram`|标量原样|比例，语义上`[0,1]`|高集中通常表示重复，暂定负向；代码模板等域须验证|边界/零值、长度敏感|已确认完整|与top-3gram、unique fraction、entropy重叠|
|11|RULE|`rps_doc_frac_chars_top_3gram`|标量原样|比例，语义上`[0,1]`|高集中通常表示重复，暂定负向；仍需域条件验证|边界/零值、长度敏感|已确认完整|与top-2gram几乎同族，须聚类去冗余|
|12|DSIR|`dsir_books`|标量原样|有限实数；理论边界和尺度未由现有材料确认|对Books目标的相关性/重要性可能有方向，但不是普适质量|可能有极长尾；后续须报告符号、分位和变换稳定性|已确认完整|与另外两项DSIR、book域及语义内容重叠|
|13|DSIR|`dsir_wiki`|标量原样|有限实数；理论边界和尺度未确认|对Wikipedia目标的相关性/重要性，不等同通用质量|可能有极长尾|已确认完整|与其他DSIR、wikipedia域重叠|
|14|DSIR|`dsir_math`|标量原样|有限实数；理论边界和尺度未确认|对Math目标的相关性/重要性，不等同通用质量|可能有极长尾|已确认完整|与其他DSIR、数字比例、数学内容重叠|
|15|MODEL|`fineweb_edu`|长度1列表取第0项→`fineweb_edu`|有限连续值；原始边界未知；现有校准p01/p99为0.083865/3.319625|既有语义为教育价值较高更好|现有主Q按校准分位截断后映射`[0,1]`|已确认完整|与Qurater educational、reasoning重叠|
|16|MODEL|`ad_en`|二分类列表`argmax`→`ad_en`|`{0,1}`；1表示no-ad|明确正向，但仅保留类别而非置信度|二值离散|已确认完整|与cleanliness、writing style可能重叠|
|17|MODEL|`fluency_en`|二分类列表`argmax`→`fluency_en`|`{0,1}`；1表示fluent|明确正向|二值离散|已确认完整|与readability、writing style重叠|
|18|MODEL|`qurater`|索引0→`qurater_writing_style`|有限连续值；原始边界未知；校准p01/p99=-5.148438/6.222949|既有语义暂定较高更好|主Q分位截断；可能长尾|已确认完整|与fluency/readability/cleanliness重叠|
|19|MODEL|`qurater`|索引1→`qurater_required_expertise`|有限连续值；原始边界未知；校准p01/p99=-4.941406/9.5|现有主Q视为较高更好；仍代表“所需专业度”，不应自动等同所有场景质量|主Q分位截断；长尾|已确认完整|与professionalism、域难度重叠|
|20|MODEL|`qurater`|索引2→`qurater_facts_trivia`|有限连续值；原始边界未知；校准p01/p99=-4.214844/4.992076|既有语义暂定较高更好|主Q分位截断；可能长尾|已确认完整|与professionalism、知识密度重叠|
|21|MODEL|`qurater`|索引3→`qurater_educational_value`|有限连续值；原始边界未知；校准p01/p99=-4.410156/8.765625|明确教育价值方向，较高更好|主Q分位截断；长尾|已确认完整|与fineweb_edu、reasoning重叠|
|22|MODEL|`modernbert_professionalism`|6维列表`argmax`→同名等级|整数`{0,1,2,3,4,5}`|既有量表较高更专业|六级离散|6条非有限导致缺失|与required expertise/facts重叠|
|23|MODEL|`modernbert_readability`|6维列表`argmax`→同名等级|整数`{0,1,2,3,4,5}`|既有量表较高更可读|六级离散|已确认完整|与fluency/writing style重叠|
|24|MODEL|`modernbert_reasoning`|6维列表`argmax`→同名等级|整数`{0,1,2,3,4,5}`|既有量表较高推理需求/能力更强|六级离散|13条非有限导致缺失|与educational value、专业度重叠|
|25|MODEL|`modernbert_cleanliness`|6维列表`argmax`→同名等级|整数`{0,1,2,3,4,5}`|既有量表较高更干净|六级离散|已确认完整|与ad、fluency和格式规则重叠|

“重复信息候选”只是待检验假设。后续必须以域内Spearman、稳健相关、互信息、条件相关、VIF/条件数和层次聚类共同判断；不能只凭字段名字删除特征。

## 【14项语义与方向裁决框架】

### 方向状态枚举

每项只能登记为以下四类之一，并附证据等级：

1. `MONOTONIC_DIRECTION_DEFINED`：有明确质量方向，并能说明适用域和反例。
2. `INTERVAL_OR_U_SHAPED`：过低、过高或两端均可能不佳，需由A1 calibration预注册区间/样条后在holdout验证。
3. `DIAGNOSTIC_NOT_SCALAR_QUALITY`：表示长度、类型、目标域相关性或置信度，只做诊断、分层、条件变量或惩罚触发器。
4. `INSUFFICIENT_EVIDENCE`：现有语义和数据均不足，禁止进入有向单一分数。

证据分三级：字段官方/来源定义；跨域语义论证；A1 calibration拟合后由holdout和extension验证。仅有与现有主Q的相关性不能把方向升级为“已证明”。

### 当前预裁决（待实证，不是最终融合决定）

|特征|当前方向类别|允许进入候选的方式|升级或保留所需证据|
|---|---|---|---|
|`rps_doc_frac_no_alph_words`|`INTERVAL_OR_U_SHAPED`|域内区间惩罚；也可只作诊断|自然文本与代码/数学域分别验证，holdout方向不能系统反转|
|`rps_doc_mean_word_length`|`INTERVAL_OR_U_SHAPED`|稳健区间/样条，不准强制线性|校准拐点在重采样中稳定，holdout收益存在|
|`rps_doc_frac_unique_words`|`INTERVAL_OR_U_SHAPED`|长度条件下的区间指标|控制word count后仍有稳定增量信息|
|`rps_doc_unigram_entropy`|`INTERVAL_OR_U_SHAPED`|长度/域条件的饱和或区间变换|不能只因与主Q正相关就设正向|
|`rps_doc_word_count`|`DIAGNOSTIC_NOT_SCALAR_QUALITY`|控制、分层、最低充分长度门槛候选|除非外部损失验证显示跨域稳定增量，否则不进入价值分数|
|`rps_lines_ending_with_terminal_punctution_mark`|`INSUFFICIENT_EVIDENCE`，可测试区间型|自然文本域辅助；代码/公式域默认诊断|按域验证后才能升级，不允许全域统一正向|
|`rps_lines_numerical_chars_fraction`|`DIAGNOSTIC_NOT_SCALAR_QUALITY`|域/任务类型控制|数学或代码密度不能直接判为低质量|
|`rps_lines_uppercase_letter_fraction`|`INTERVAL_OR_U_SHAPED`|极端格式惩罚候选|阈值须只由calibration确定并在holdout稳定|
|`rps_doc_num_sentences`|`DIAGNOSTIC_NOT_SCALAR_QUALITY`|长度控制、分层|不得与word count重复计权|
|`rps_doc_frac_chars_top_2gram`|`MONOTONIC_DIRECTION_DEFINED`，暂定较低集中更好|重复惩罚；须允许域条件强度|若多个主要域在holdout方向反转，则降级为诊断/区间|
|`rps_doc_frac_chars_top_3gram`|`MONOTONIC_DIRECTION_DEFINED`，暂定较低集中更好|与2-gram聚类后选代表、组内平均或惩罚|禁止两项高度相关时被双重计权|
|`dsir_books`|`DIAGNOSTIC_NOT_SCALAR_QUALITY`|Books目标相关性向量或域条件分量|需确认分值生成定义和方向；不得称通用质量|
|`dsir_wiki`|`DIAGNOSTIC_NOT_SCALAR_QUALITY`|Wikipedia目标相关性向量或域条件分量|同上|
|`dsir_math`|`DIAGNOSTIC_NOT_SCALAR_QUALITY`|Math目标相关性向量或域条件分量|同上|

已有`indicator_direction_pending.csv`中14项与现有主Q的相关性只作为诊断证据。其域内相关范围大量跨零或改变符号，支持“域条件/区间/诊断”的谨慎处理，不能据此反向优化成与主Q高度相关的附属指标。

## 【候选融合方案】

所有候选必须保留以下共同输出：`Q_baseline`、新增候选分数、构成分量、有效标记、置信度、冲突标记、模型版本。候选列不得写回或复用`Q_baseline`列名。

### 候选A：分层稳健融合

结构：

1. 第一层固定现有11特征`Q_main=Q_baseline`，不重新训练其方向和权重。
2. 第二层分别构造：`Q_rule_naturalness`、`Q_rule_repetition`、`rule_length_context`和三维`DSIR_relevance_vector`。仅方向获准的规则进入有向辅助分数；长度和DSIR默认作为条件变量。
3. 第三层比较固定高层等权、受约束非负权重和可靠度加权。高层权重只在A1 calibration内选择，且应限制`Q_main`占主导，例如将规则层视为独立块而非让14项按数量压过11项。

优点：保留现有Q结构、易解释、可防止相关规则重复计权；可把DSIR保留为向量。缺点：高层分组及权重仍含主观性；区间变换和域条件可能增加复杂度。

### 候选B：全特征统一融合

只允许方向已经通过语义和calibration预筛的特征进入统一池。比较：

- 稳健等权：域等权校准、winsorize/ECDF或稳健z分数、按冗余簇等权。
- 熵权：仅作敏感性；它奖励分散度，不等于奖励质量或可靠性。
- CRITIC：仅作敏感性；对方差和低相关度赋权，可能放大长尾、域差异或噪声。
- PCA/稳健PCA：只用于冗余结构、载荷稳定性和无监督对照，不得把PC1直接命名为质量。若需要构造有向投影，方向必须由外部预注册锚点确定并在holdout验证。
- 可选受约束监督权重：只能以A1 calibration内部交叉拟合或独立外部目标训练；权重非负/有界，不能使用holdout或extension调参。

优点：能发现跨组互补信息，统一比较简洁。缺点：最易受量纲、长尾、域构成和特征数量影响；无监督权重没有质量语义；14项可能稀释主信号。该方案优先级最低，除非外部验证显著且稳定优于分层方案。

### 候选C：主Q加规则修正项

结构示意：

`Q_candidate = clip(Q_main + bonus_rules - penalty_rules, 0, 1)`。

- `penalty_rules`只由已验证的异常/重复规则触发，采用有界、稀疏、单调的惩罚；默认不因文档长度或DSIR低值扣分。
- `bonus_rules`必须比惩罚更审慎，只有存在明确方向和holdout增量证据时启用。
- DSIR优先作为目标相关性标签或T06的条件输入，不直接加到通用Q。
- 同时输出`Q_confidence`。冲突高、越过校准支持区或域外样本可以降低置信度，而不是任意改变质量值。

优点：最大限度保护Q01C主信号，规则只修正明显异常，解释直接；适合保守升级。缺点：惩罚阈值和强度需要预注册，可能漏掉规则的正向信息；clip会产生边界堆积，必须报告。

### 候选D：主Q不变的控制方案

保持`Q_baseline`，14项只输出诊断、冲突和置信度。所有融合候选必须与D比较；若增量信息或外部一致性不稳定，D是合法最终结果。

### 推荐比较优先级

1. **首选候选C**：主Q加稀疏规则修正和独立置信度。
2. **次选候选A**：分层稳健融合，并将DSIR保留为目标相关性向量。
3. **对照候选D**：主Q不变。
4. **探索候选B**：全特征统一融合，仅在严格验证后考虑。

这是后续试验顺序，不是最终Q裁决。

## 【冲突消解定义】

### 必须区分的三个对象

1. `Q_value`：候选质量中心估计。
2. `Q_confidence`：该估计在当前域、特征支持和多视角一致性下的可信度。
3. `conflict_state`：指标之间是否出现预注册的不一致。冲突高不自动等于质量低。

### 可验证冲突指标

后续至少实现并比较以下指标：

- **组间分歧基线**：现有三个主组的range和ddof=0 std，仅作诊断基线。
- **方向一致率**：对已定向特征，以A1 calibration域内中位数或预注册区间中心为参照，计算支持“较高质量”与“较低质量”的有效证据比例；区间型和诊断型特征不得被伪装成正负票。
- **稳健离散度**：对可比的方向化分量计算MAD、IQR或加权绝对偏差，避免range被单个指标支配。
- **视角冲突**：`Q_main`、规则异常层和DSIR目标相关性向量之间分别输出差异，不强制压为一个range。
- **排序冲突**：各特征族或候选模型对同一批记录的成对次序不一致率、Kendall距离或top-k重合率。
- **域外冲突**：记录是否落在A1 calibration对应域的支持区之外；越界只降低置信度，不自动判低质量。

### 冲突处理规则

1. 所有阈值只用A1 calibration确定，并在查看holdout结果前冻结。
2. 方向明确且多个独立特征族一致时，可以形成有向修正；同一冗余簇内的多个指标只算一个证据块。
3. 主Q与规则层冲突时，默认保留`Q_main`并降低`Q_confidence`；只有候选C的预注册强异常条件满足时才施加有界惩罚。
4. DSIR之间冲突表示目标域相关性不同，输出向量，不用多数票决定通用质量。
5. 冲突超过阈值但无可靠裁决依据时，标记`ABSTAIN_SCALAR_FUSION`或`HIGH_CONFLICT`，不得强行给出“已消解”的单一解释。
6. “消解成功”的验收含义是：规则可复现、冲突状态稳定、holdout及extension不出现系统性恶化，并对外部一致性提供增量信息；不能以分歧数值被机械压小作为成功。

## 【验证方案】

### 数据角色冻结

|数据角色|允许用途|禁止用途|
|---|---|---|
|A1 calibration|语义可检验部分的变换拟合、区间/阈值、冗余簇、候选超参数；必须内部交叉拟合/重采样|把同样本拟合指标当泛化性能|
|A1 holdout|一次性候选比较、稳定性和增量信息验证|重新选方向、调阈值、调权重|
|extension overlap|相同键或重叠记录的一致性、测量复现和传输检查|训练、权重选择；不得当完全独立样本|
|extension new|新记录、arxiv/github域迁移及支持区检查|训练、阈值或权重选择|
|RegMix/Loss|后续外部一致性和T06接口验证|假定与A表Q同尺度；在无可靠连接时强行监督|

### V1：A1 calibration内部稳定性

- 按域分层，域等权；同时保留样本加权结果作敏感性，不得混为主结果。
- 使用重复bootstrap或分层重采样，所有变换、阈值、聚类和权重必须在每个重采样训练部分重新拟合。
- 若做交叉验证，按联合键划分，防止重复记录跨折；报告每域有效n。
- 输出方向选择频率、阈值/拐点分布、权重分布、载荷/簇一致性和候选排序稳定性。

### V2：A1 holdout

- 使用冻结的calibration变换和权重直接评分。
- 比较候选与`Q_baseline`的分布、域内排序、top-k重合、冲突率、支持区越界率及预注册外部代理指标。
- holdout结果不得反馈到模型选择流程；若所有候选在holdout失败，保留候选D。

### V3：extension overlap

- 明确A2和A3 overlap计数及键关系，不把重叠记录当独立泛化样本。
- 对25维输入完全一致的同键，确定性候选分数必须在数值容差内一致；不一致时判实现失败。
- 输入存在差异时，报告逐特征变化、分数MAE、Spearman、ICC或一致性界限，不能只报相关系数。

### V4：extension new

- 使用冻结参数零重拟合评分。
- 分arxiv、github及可识别域报告覆盖、支持区越界、冲突、排序和分布漂移。
- 分布变化可以是真实域差异，不以“均值接近A1”为通过条件；重点检查方向、数值范围和模型行为是否失控。

### V5：域间稳定性

- 分别报告每域和域等权汇总；禁止大域掩盖小域反转。
- 对单调候选记录域内方向符号、效应量和区间；方向跨域系统反转时降级为域条件或诊断指标。
- 对区间型特征比较拐点/安全区的重采样分布；拐点不稳定时不进入标量修正。

### V6：权重与变换敏感性

- 比较等权、簇等权、受约束权重、熵权、CRITIC和PCA对照。
- 对高层权重做预注册扰动和删一特征族分析；报告候选分数Spearman、top-k Jaccard、域排名和边界堆积变化。
- 同一冗余簇被重复复制后，候选结果不应显著改变；否则判权重机制对特征数量敏感。

### V7：排序稳定性

- 报告全体与逐域Spearman/Kendall、top 1%/5%/10%及bottom 1%/5%重合、跨bootstrap名次区间。
- 排序稳定只说明复现性，不说明质量正确；必须与方向语义和外部一致性联合判断。

### V8：相对现有主Q的增量信息

- 报告候选与主Q的相关、条件相关、残差方差、互信息及规则层在控制域/长度后的增量。
- 使用交叉拟合检验候选增量能否预测预注册代理或外部目标；不能用“与主Q相关更高”作为纳入理由。
- 检查候选是否只是文档长度、域标签或主Q重复副本。若新增分量几乎完全由域/长度解释，应保留为条件变量。

### V9：与RegMix/Loss的外部一致性

- 先形成有明确样本定义的域级或配比级A质量聚合量，并记录聚合权重、覆盖率和不确定性。
- 只比较方向、排序、增量预测和时间/规模外稳定性；需要拟合映射时，训练与验证必须按RegMix既有划分或模型规模分离。
- 主比较至少包含仅用配比、配比+`Q_baseline`、配比+候选Q；使用嵌套或预冻结模型比较，报告OOF/holdout误差而非训练拟合。
- A数据Q与B表`Q_score`没有样本级配对标定时，结论限定为外部一致性或情景接口。正式尺度桥接留给T06。

## 【候选方案淘汰规则】

满足任一硬失败即淘汰该候选；实现级硬失败则停止整个执行任务：

1. 使用holdout或extension拟合方向、变换、阈值、冗余簇或权重。
2. 覆盖主Q、改变Q01C行数/身份/`Q_valid`，或重新处理19条缺失。
3. 将方向未定义特征按任意正负号并入标量分数，或把PCA/熵权/CRITIC解释成质量真值。
4. 同键同25维输入得到不同确定性分数，或计算无法由冻结参数复现。
5. 任一主要域出现未解释的方向系统反转；该指标必须降级或候选淘汰，不能用总体均值掩盖。
6. 权重/阈值在bootstrap中高度不稳定、删一特征族后排序大幅翻转、或复制冗余特征即可显著改变结果。
7. 候选主要编码域或长度，且在控制这些变量后无稳定增量信息。
8. holdout相对主Q没有可复现增量，或外部一致性只在训练样本改善而在独立划分不改善。
9. extension出现大量校准支持区外样本却仍给出高置信度，或者不报告域外状态。
10. 用减少`rater_disagreement`本身证明冲突已解决，未提供独立稳定性或外部验证。

后续执行前必须在`run_config.json`冻结数值门槛。建议至少报告而非隐藏：bootstrap方向选择率、权重变异、holdout效应区间、逐域符号一致性、权重扰动下Spearman/top-k重合、extension越界率。具体门槛应由Astra在看结果前批准；执行AI不得根据跑后结果移动门槛。

若没有候选同时通过语义、稳定性和独立验证，正式结论应是“保留现有主Q，14项作为诊断/条件信息”，不得从失败候选中强选一个。

## 【后续执行施工单结构】

后续另行编制执行单（建议编号`TASK-T03E`），至少包含以下阶段：

|阶段|工作|关键防泄漏要求|
|---|---|---|
|E00 preflight|核对正式Q01C manifest、源码、配置、身份和输出目录|不读取真实A1–A3；输入不符即停止|
|E10 semantics_profile|生成25项语义、经验范围、离散/长尾/截断与缺失表|只描述，不在此阶段选权重|
|E20 direction_tests|在A1 calibration内检验14项方向、区间和域条件|holdout/extension不可见|
|E30 redundancy|相关、互信息、VIF/条件数、聚类和簇稳定性|按域及域等权；不以字段数量加权|
|E40 candidate_fit|拟合A/B/C并生成D对照|只用calibration；参数全部冻结|
|E50 internal_resampling|bootstrap/交叉拟合及敏感性|每次重采样重做拟合步骤|
|E60 holdout_validation|一次性A1 holdout验收|禁止回调参数|
|E70 extension_validation|overlap一致性及new迁移|零重拟合；明确非独立overlap|
|E80 external_consistency|RegMix/Loss接口和独立验证|不假定A/B质量同尺度|
|E90 verify_finalize|独立复算、检查、handoff和manifest|有FAIL不得宣称最终Q|

执行单必须写明运行规模、随机种子、bootstrap次数、候选超参数网格、预注册门槛、资源上限、停止条件、恢复机制和禁止修改范围。本设计单不授权这些阶段开工。

## 【必须输出的文件】

后续正式执行run至少生成：

|文件|最低内容|
|---|---|
|`feature_semantics.csv`|22原始字段、25展开项、来源、展开、理论/经验范围、离散/长尾/截断、缺失及语义证据|
|`feature_direction_decisions.csv`|14项方向类别、证据等级、允许用途、域限制、升级/降级原因和主控状态|
|`feature_distribution_by_scope_domain.csv`|逐scope/domain经验分位、唯一值、零/边界占比及有效n|
|`redundancy_matrix.csv`|逐域和域等权的稳健相关/条件相关；每行带有效n|
|`redundancy_clusters.csv`、`cluster_diagnostics.json`|聚类成员、阈值、稳定性、VIF/条件数、代表项或簇等权规则|
|`candidate_specifications.json`|A/B/C/D公式、方向、变换、参数来源、权重约束和版本|
|`candidate_Q_scores.parquet`|唯一键、角色、域、`Q_baseline`、各候选Q、分量、置信度、冲突、支持区状态；不含正文|
|`candidate_comparison.csv`|逐scope/domain覆盖、分布、相对主Q增量、独立验证指标与结论|
|`stability_bootstrap.csv`|方向、阈值、权重、排序及簇稳定性|
|`weight_sensitivity.csv`、`ranking_stability.csv`|权重扰动、删族、top-k及域排名变化|
|`holdout_validation.csv`|冻结候选在A1 holdout的全部预注册指标|
|`extension_overlap_validation.csv`|同键输入/输出一致性及差异分解|
|`extension_new_validation.csv`|域迁移、支持区、冲突和分布变化|
|`conflict_diagnostics.csv`、`conflict_rules.json`|冲突分量、阈值来源、状态、置信度和拒绝标量规则|
|`regmix_loss_external_consistency.csv`|连接口径、覆盖、独立划分结果；不可识别时明确状态与原因|
|`t06_quality_interface.json`|候选Q名称、尺度、方向、组成、覆盖、域限制、置信度及待标定声明|
|`checks.json`、`verification.json`|检查结果、PASS/FAIL/NOT_CHECKED/NOT_VERIFIABLE及独立复算证据|
|`run_summary.json`、`handoff.md`、`output_manifest.json`|运行状态、候选去留、Astra待裁决问题和封闭清单|

`candidate_Q_scores`必须保留`Q_baseline`原值作对照，但不得修改正式Q01C文件。所有统计都显式报告`n_total/n_valid/n_missing/coverage`。

## 【验收标准】

1. 22→25映射与冻结Q01C提取逻辑逐项一致；所有范围均区分理论、经验和既有归一化范围。
2. 14项均有四类方向状态之一，没有“为了完整”而默认设为正向或负向。
3. A/B/C/D候选均有可复现公式、参数来源、限制和独立列名；现有主Q未被覆盖。
4. 数据角色严格隔离，所有训练只使用A1 calibration；holdout和extension零调参。
5. 冗余、冲突、稳定性、权重敏感性和排序稳定性均提供机器表及有效分母。
6. 冲突诊断同时输出值、置信度与冲突状态，并允许`ABSTAIN`；不把分歧变小直接称为解决。
7. 候选通过预注册淘汰规则；失败候选如实保留，不能选择性删除不利结果。
8. RegMix/Loss只作为外部一致性和接口验证；没有可靠映射时明确不可识别。
9. 独立verifier不调用候选生成函数计算“期望值”；关键映射、分数和验证指标从冻结产物另行复算。
10. 无关键FAIL；NOT_CHECKED或NOT_VERIFIABLE必须说明是否阻止最终融合裁决。执行AI只能标记`COMPLETE_PENDING_REVIEW`，最终方案由Astra裁决。

## 【失败判据与停止条件】

- 输入manifest、行数、唯一键或主Q哈希与正式Q01C不一致：立即停止。
- 需要重扫真实A1–A3才能继续：停止并交主控，不自行读取。
- 发现数据泄漏、候选覆盖主Q、方向硬编码无来源或extension参与拟合：任务失败。
- 任一候选计算出现非有限值、范围失控或身份错位：停止该候选；若影响公共输入则停止全任务。
- 外部连接键或尺度关系不能验证：外部阶段登记`NOT_IDENTIFIABLE`，不得猜测补全；其是否阻止最终Q由Astra裁决。
- 完成全部获授权输出后停止，不启动T06、不改02决定、不写论文结论。

## 【哪些问题需要Astra最终裁决】

执行AI只提交证据，不得自行决定以下事项：

1. 14项的最终方向状态，尤其是两个重复集中度指标能否升级为稳定负向，以及区间型规则的拐点是否足够稳定。
2. 三个DSIR是否只保留为目标相关性向量，还是在特定任务条件下进入辅助分数。
3. 冗余簇的最终阈值、代表项/簇等权方式，以及是否排除长度变量。
4. A、B、C或D哪一类成为后续正式候选；推荐优先级不能代替实证裁决。
5. 冲突阈值、`ABSTAIN`规则和可信度是否足以支撑“冲突已处理”的表述。
6. calibration阶段的数值门槛是否在查看holdout/extension前预注册充分。
7. holdout、域稳定性、bootstrap、权重敏感性和extension结果是否达到替换/扩展主Q的证据标准。
8. RegMix/Loss外部一致性是否具有可靠连接和独立验证，还是只能作为情景证据。
9. 是否维持`Q_baseline`为主结果、把新候选作为敏感性/附加指标；未经该裁决不得修改`02_DECISIONS.md`。
10. 交给T06的`Q_A`版本、尺度、置信区间和适用域；A数据Q与B表`Q_score`的标定另立任务，不在T03内默认完成。

## 【完成后必须交回的材料】

后续执行AI必须交回正式run目录、实际命令、冻结配置和源码、输入/输出manifest、全部候选与失败候选、数据角色隔离证据、独立验证结果、NOT_CHECKED/NOT_VERIFIABLE清单，以及逐项对应上述Astra裁决问题的`handoff.md`。在Astra正式验收前，不得把任何候选命名为“最终Q”。
