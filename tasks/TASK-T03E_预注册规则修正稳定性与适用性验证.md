# TASK-T03E正式施工单：预注册规则修正稳定性与适用性验证

状态：**施工单已编制，未执行。** 只有收到单独执行指令后才能开工。

编制日期：2026-09-25。所有相对路径均相对于：

`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace`

## 【任务编号】

TASK-T03E。

上位依据：

1. `tasks/TASK-T03_完整质量体系与14项规则DSIR融合方法设计.md`；
2. Astra在查看任何T03实证结果前完成的方法学预注册裁决。

两者冲突时，以Astra预注册裁决和本施工单冻结的定义为准。

## 【任务名称】

在不改变正式主Q的前提下，对固定top-2gram/top-3gram重复规则簇形成的有界惩罚候选进行两阶段、预冻结的稳定性与适用性验证。

## 【正式研究定位】

TASK-T03E不寻找“更优真实质量Q”，也不声称A1中存在可供监督学习的文档级真实质量标签。

正式主结果固定为：

\[
D=Q_{\mathrm{baseline}}.
\]

唯一确认性候选固定为：

\[
C=Q_{\mathrm{baseline}}(1-0.02P),
\]

其中`P`只来自top-2gram/top-3gram固定冗余簇。C即使通过本任务全部检查，也只能登记为：

**预注册规则敏感性候选（preregistered rule-sensitivity candidate）**。

本任务不得把C改名为`final_Q`、`improved_Q`、`true_quality`或正式主Q，不得把稳定性解释为真实质量改善。

本轮研究范围同时冻结如下：

- A、B候选不拟合、不比较、不进入holdout；
- 不运行PCA、熵权、CRITIC或其他权重选优；
- DSIR仅保留为`DSIR_relevance_vector=(dsir_books, dsir_wiki, dsir_math)`；
- `word_count`、`num_sentences`等长度指标只作控制或诊断；
- 不以与`Q_baseline`的相关性确定任何规则指标的质量方向；
- RegMix/Loss只做连接与识别性检查，不训练新桥接模型。

## 【输入文件】

### 主要数据输入

唯一允许用于候选计算的正式行级输入为：

`solution/outputs/quality_q01c/20260924T215718+08/quality_features_scores.parquet`

该文件已通过TASK-Q01C主控验收。执行前必须从同一正式run的`output_manifest.json`核对其路径、大小和SHA256，不得以其他run、历史`solution/outputs/quality/`或测试fixture替代。

### 允许只读的项目证据

- `tasks/TASK-T03_完整质量体系与14项规则DSIR融合方法设计.md`；
- 本施工单；
- `solution/outputs/quality_q01c/20260924T215718+08/`中的`input_manifest.json`、`output_manifest.json`、`run_config.json`、`normalization.json`、`domain_summary.csv`、`summary_denominators.csv`、`feature_summary.csv`和`quality_baseline_q01c.md`；
- `diagnostics/TASK-Q01A/20260924T142229+08/diagnostic_spec.json`，只用于核对22→25映射和角色定义；
- `solution/outputs/quality/semantic_sources/`，只用于字段语义和来源说明；
- `solution/outputs/mixture/`及相关只读数据说明，仅在PHASE B的RegMix/Loss识别性检查中使用，不得拟合新模型。

### 禁止作为输入

- 真实A1、A2、A3压缩文件及其解压内容；
- 任何TASK-T03E运行之外临时生成的holdout/extension摘要；
- 原T03设计中被Astra排除的A/B候选结果；
- 以`Q_baseline`为监督目标学习出来的方向、U型曲线、权重或阈值。

如果正式行级Parquet缺少身份、域、角色、唯一键、`Q_baseline`、`Q_valid`、top-2gram、top-3gram或三项DSIR中的任一必要列，立即停止并交主控；不得重新读取A1–A3补齐。

## 【不可变基线】

以下列的名称、类型、逐行值、行序关联和身份关系均为受保护基线：

- `Q_baseline`；
- `Q_valid`；
- 文件、来源行号、id/sub_path联合键或其冻结哈希；
- `evaluation_role`；
- `domain`；
- `is_unique_first`及重叠标记；
- 原25个展开特征。

19条`Q_valid=False`记录不得插补、删除、重新评分或进入候选有效样本。其`Q_C`继续为NaN，支持状态登记为`Q_INVALID_PRESERVED`。所有主比较只使用正式Q01C口径下`Q_valid=True & is_unique_first=True`的对应角色记录。

执行前和结束后必须比较正式Q01C行级文件的SHA256；正式run本身完全只读。候选结果写入独立T03E目录。

## 【输出目录与防覆盖规则】

正式输出根目录固定为：

`diagnostics/TASK-T03E/<run_id>/`

`run_id`使用实际启动时间和唯一后缀。目录已存在时必须失败退出，禁止覆盖或复用同名目录。失败run保留其日志、错误状态和已冻结证据，不得删除或与后续run混合。

正式目录至少包含：

- `metadata_preflight/`：只含calibration分区和域标签核验；
- `phase_a_calibration_freeze/`：只含calibration分析及冻结包；
- `phase_b_frozen_validation/`：holdout、extension和识别性检查；
- `code_snapshot/`：实际运行和独立验收源码；
- `access_log.jsonl`、`command_log.json`、`stage_status.jsonl`、`run.log`；
- 最终`checks.json`、`verification.json`、`run_summary.json`、`handoff.md`和`output_manifest.json`。

freeze seal生成后，冻结包只能读取，不能在原路径修改、补写或重新生成。需要重做PHASE A时必须创建全新run。

## 【允许新建的代码】

建议在`solution/src/`或本任务专用目录中新增：

- `t03e_preregistered_rule_sensitivity.py`：元数据门禁、PHASE A和PHASE B执行入口；
- `t03e_verify.py`：完全独立的只读验收器；
- 必要的人工fixture和专项测试。

执行脚本与验收脚本必须分离。`t03e_verify.py`不得导入执行脚本、候选生成函数、阈值函数或bootstrap汇总函数来构造expected。两个脚本的源码与依赖清单必须在freeze前复制到`code_snapshot/`并登记SHA256。

## 【禁止修改的文件】

- 全部`F题/`原始材料；
- TASK-Q01C、Q01C-R1、Q01C-R2所有正式、候选和失败run；
- `solution/outputs/quality/`及Q01A/R1证据；
- `Q_baseline`及其正式源文件；
- 00–05项目管理文档；
- 配比、缩放、C模块、优化和论文源码或产物。

执行AI不得更新项目状态、不得登记最终融合决定。完成后只能报告`COMPLETE_PENDING_REVIEW`。

## 【执行前域标签核验】

### 分区门禁与防泄漏解释

“阈值计算前核对实际domain标签”和“第一次holdout读取必须晚于freeze seal”同时成立时，冻结前只能核对**A1 calibration中实际出现的精确domain标签**。全表domain全集和逐角色样本数必须在seal之后，按holdout→extension的规定顺序生成；不得为了提前得到全角色计数而在freeze前读取holdout或extension元数据。

在PHASE A之前设置`CALIBRATION_PARTITION_PREFLIGHT`：

- 对正式Parquet发出逻辑谓词`evaluation_role == A1_calibration`，只允许返回calibration行；
- 读取calibration所需的身份键、`domain`、`evaluation_role`、`is_unique_first`和后续PHASE A规定的分析列；
- 输出calibration精确域标签、逐域总行数、唯一首见数和有效数；
- 生成calibration键集合哈希承诺；
- 开始、列投影、过滤条件、进程PID、命令和结束时间写入`access_log.jsonl`。

PHASE A候选计算进程只能获得A1 calibration行。若底层Parquet读取器因row-group布局需要解码包含其他角色的物理页，程序仍不得向分析层返回、统计、缓存或输出任何非calibration行；必须在任何数组构造前断言分析层全部记录均为`A1_calibration`，在进入唯一键分析后再断言`is_unique_first=True`。访问日志需区分存储层解码与分析层可见行。

freeze seal之后，PHASE B第一次读取holdout时才生成holdout域标签与计数；完成holdout验收并冻结输出后，第一次读取extension时再生成extension域标签与计数。二者合并calibration清单后形成最终domain标签全集及逐角色样本数。任何非calibration行在seal前进入分析层都属于FAIL。

### 精确标签匹配

预注册设计域字符串固定为：

- `book`
- `c4`
- `commoncrawl`
- `wikipedia`

freeze前必须输出：

- `calibration_domain_labels.csv`：A1 calibration中的domain精确字符串全集；
- `calibration_domain_inventory.csv`：calibration逐域总行数、唯一首见数和有效数；
- `calibration_domain_label_match.csv`：四个设计名称与calibration实际标签的逐字符精确匹配结果。

seal后必须按访问顺序补充并最终输出：

- `actual_domain_labels_all_roles.csv`：calibration、holdout、extension合并后的精确字符串全集；
- `domain_role_inventory.csv`：逐`domain × evaluation_role`的总行数、唯一首见数和可分析数；
- `domain_label_match_all_roles.csv`：设计名称与全角色实际标签的精确匹配结果及首次出现角色。

禁止小写化后替换、前后缀匹配、模糊匹配、别名推断或将`book`现场改成`books`。设计标签不存在时登记`DESIGN_LABEL_ABSENT`；标签存在但calibration有效n不足时登记`INSUFFICIENT_CALIBRATION`。二者均不得通过改换域名、合并域或借用其他域参数来补救。

如果实际domain值无法被稳定解析为一个精确字符串，或同一行出现多个冲突域标识，立即停止。精确不存在本身可被可靠登记，不等同于“无法对应”；只有存在歧义或冲突时触发停止条件。

未应用规则的域，包括但不限于`github`、`arxiv`、`stackexchange`，均满足：

\[
Q_C=Q_{\mathrm{baseline}},
\]

且`Q_support_status=RULE_NOT_APPLICABLE`。这些域中的Spearman=1、top-k完全一致或零修正不得计入active correction通过率、确认性域数或迁移成功证据。

## 【冻结候选C】

### 有效样本与域资格

对设计域`d`，calibration有效行定义为：

`evaluation_role == A1_calibration & is_unique_first == True & Q_valid == True & Q_baseline有限 & top2gram有限 & top3gram有限`。

其中：

- `top2gram = rps_doc_frac_chars_top_2gram`；
- `top3gram = rps_doc_frac_chars_top_3gram`。

域资格冻结为：

1. 实际标签与设计名称精确匹配；
2. calibration有效n至少1000；
3. 两项指标均满足`q0.99 > q0.95`。

处理规则：

- 标签不存在：`DESIGN_LABEL_ABSENT`，不施加规则；
- calibration有效n<1000：`INSUFFICIENT_CALIBRATION`，不施加规则；
- n≥1000但任一指标`q0.99 <= q0.95`：`CALIBRATION_DEGENERATE`，primary C资格失败；
- 禁止使用其他域参数、全局参数或现场fallback；
- 至少存在一个获准active domain，且所有达到n≥1000的实际设计域都没有分位退化，才可能生成`CALIBRATION_QUALIFIED_PENDING_VALIDATION`；否则生成`CALIBRATION_REJECTED_KEEP_D`。

不满足样本门槛的设计域不会使其他合格域自动失败，但必须从active域集合中排除并显式报告。active域集合必须在freeze包中冻结，PHASE B不得改变。

### 分位定义

所有分位数使用所选Python/NumPy版本的线性插值定义，即与`numpy.quantile(..., method='linear')`等价。环境、库版本和实际实现写入`environment.json`。

对每个active domain `d`：

\[
a_{2d}=q_{0.95}(x_{2d}),\quad b_{2d}=q_{0.99}(x_{2d}),
\]

\[
a_{3d}=q_{0.95}(x_{3d}),\quad b_{3d}=q_{0.99}(x_{3d}).
\]

单项惩罚固定为：

\[
p_{jd}(x)=
\begin{cases}
0,&x\le a_{jd},\\
\dfrac{x-a_{jd}}{b_{jd}-a_{jd}},&a_{jd}<x<b_{jd},\\
1,&x\ge b_{jd}.
\end{cases}
\]

固定冗余簇惩罚为：

\[
P=\frac{p_{2d}+p_{3d}}{2}.
\]

primary候选固定为：

\[
Q_C=Q_{\mathrm{baseline}}(1-0.02P).
\]

禁止bonus、禁止clip、禁止学习lambda、禁止根据相关性改变方向。lambda敏感性网格固定为`{0, 0.01, 0.02, 0.05}`，只能报告，不得择优。PHASE B只验收lambda=0.02和D。

### 支持区和状态

每个active domain分别由calibration估计：

\[
[q_{0.005},q_{0.995}]
\]

作为top-2gram和top-3gram各自的经验支持区。任一指标越界时：

`Q_support_status=OUT_OF_SUPPORT`。

越界只改变支持状态，不重新归一化、不追加惩罚、不改变lambda。其他状态枚举固定为：

- `SUPPORTED`；
- `OUT_OF_SUPPORT`；
- `RULE_NOT_APPLICABLE`；
- `INSUFFICIENT_CALIBRATION`；
- `DESIGN_LABEL_ABSENT`；
- `Q_INVALID_PRESERVED`。

如果达到n≥1000却分位退化，PHASE A整体拒绝，不进入可评分的`CALIBRATION_DEGENERATE`候选状态。

## 【Bootstrap精确定义】

### 抽样单位和随机数

- 只在A1 calibration唯一有效键内按active domain分别bootstrap；
- 每个域每次从该域n个唯一键中有放回抽取n个键；
- 总次数固定200；主种子固定`20260925`；
- 域按实际精确标签字典序排列；
- 每个`domain × replicate`的子种子由字符串`20260925|<domain>|<replicate>`的SHA256前16个十六进制字符转为无符号整数，交给NumPy `PCG64`；
- replicate编号固定为0–199；算法、库版本和子种子清单写入`bootstrap_seed_manifest.csv`。

### 固定reference rows

稳定性不能在不同重采样行集合之间直接比较。对每个active domain：

1. 用完整calibration有效行估计full-calibration参数；
2. 在按冻结联合键升序排列的同一批完整calibration有效行上计算`P_ref`和`Q_C_ref`；
3. 每个bootstrap只用重采样行估计`q95/q99`；
4. 将该bootstrap参数应用到上述同一批固定reference rows，得到`P_b`和`Q_C_b`；
5. 只在这一固定记录集合上计算稳定性。

逐bootstrap指标固定为：

- `penalty_mae = mean(abs(P_b - P_ref))`；
- `rank_spearman`：分别按`(-Q_C, frozen_joint_key)`做确定性全排序，得到无并列序位，再用序位计算Spearman；
- `top10_jaccard`：令`k=max(1, ceil(0.10*n))`，取同一确定性排序前k个联合键，计算交并比。

任一`q99<=q95`记为该bootstrap三项联合失败，不使用临时分位、抖动或其他fallback。

每个active domain必须至少190/200次bootstrap同时满足：

- `penalty_mae <= 0.10`；
- `rank_spearman >= 0.98`；
- `top10_jaccard >= 0.85`。

不能把三项分别满足190次但联合满足不足190次写成通过。逐次明细、逐域联合通过次数和失败原因必须全部保存。

## 【真正两阶段冻结】

### 阶段结构

本任务由calibration分区门禁、PHASE A和PHASE B组成。确认性分析严格物理分为两个独立进程阶段。

#### CALIBRATION_PARTITION_PREFLIGHT

执行：

- 输入manifest和正式行级文件版本核验；
- 只返回A1 calibration行；
- 输出calibration域标签、计数和精确设计标签匹配；
- 生成calibration键集合的哈希承诺；
- 记录逻辑谓词、返回角色、列投影和访问时间；
- 禁止创建holdout/extension键承诺、标签清单或计数，因为这会构成freeze前读取。

#### PHASE A：CALIBRATION_FREEZE

只允许分析A1 calibration唯一首见行，执行：

- calibration经验范围；
- active域资格判定；
- q95/q99/q005/q995；
- 200次bootstrap；
- lambda网格描述性敏感性；
- 单调性、边界及冗余复制人工测试；
- calibration资格判定；
- 创建不可修改冻结包。

PHASE A必须输出：

- `frozen_primary_spec.json`；
- `frozen_thresholds.csv`；
- `frozen_active_domains.csv`；
- `preregistered_acceptance.json`；
- `bootstrap_seed_manifest.csv`；
- `bootstrap_stability_detail.csv`；
- `bootstrap_stability_summary.csv`；
- `lambda_sensitivity_calibration.csv`；
- `prior_exposure.md`；
- `code_snapshot/`；
- `freeze_manifest.json`；
- `FREEZE_SEALED.json`；
- `phase_a_summary.json`。

`freeze_manifest.json`至少登记：候选公式、lambda、固定网格、设计域、实际active域、全部分位阈值、支持区、验收门槛、随机数算法和种子、行选择规则、联合键定义、源数据SHA256、源码SHA256、配置SHA256及冻结包中每个文件的路径/大小/SHA256。

为避免哈希循环，`freeze_manifest.json`不登记自身和`FREEZE_SEALED.json`，也不登记PHASE B期间仍会追加的全局日志。它只登记在seal前已经关闭的PHASE A不可变文件和`code_snapshot/`。`FREEZE_SEALED.json`再登记`freeze_manifest.json`的SHA256；seal自身生成后不得修改。

`FREEZE_SEALED.json`至少包含freeze manifest的SHA256、seal时间、进程PID、实际命令、PHASE A状态及以下二者之一：

- `CALIBRATION_QUALIFIED_PENDING_VALIDATION`；
- `CALIBRATION_REJECTED_KEEP_D`。

生成seal前关闭冻结包全部文件。seal后禁止改写被冻结文件。若PHASE A拒绝，立即停止正式分析，不读取holdout或extension特征值，不尝试A/B、换lambda、改阈值或减少失败域。

#### PHASE B：FROZEN_VALIDATION

只有`FREEZE_SEALED.json`存在、状态合格、freeze manifest哈希匹配且全部冻结文件哈希匹配时才允许启动。

PHASE B启动顺序固定为：

1. 验证freeze seal；
2. 记录独立进程PID和实际命令；
3. 首次读取A1 holdout的行数据，并立即记录`first_holdout_read_time`；同时生成holdout域标签与计数；
4. 完成holdout验收并冻结其输出；
5. 首次读取extension行数据，记录`first_extension_read_time`；同时生成extension域标签与计数；
6. 完成overlap/new验证；
7. 做RegMix/Loss连接与识别性检查；
8. 生成T06接口、PHASE B摘要和交回材料。

必须满足：

`FREEZE_SEALED.time < first_holdout_read_time < first_extension_read_time`。

任何冻结参数、active域、公式、lambda、阈值、门槛、代码或配置在holdout读取后变化，整项任务FAIL。PHASE B不得调用任何调参、阈值估计或候选选择入口。

### 建议命令接口

实际执行命令必须由程序从`argv`原样记录。建议接口如下：

```powershell
python solution/src/t03e_preregistered_rule_sensitivity.py calibration-preflight --input "solution/outputs/quality_q01c/20260924T215718+08/quality_features_scores.parquet" --run-dir "diagnostics/TASK-T03E/<run_id>"

python solution/src/t03e_preregistered_rule_sensitivity.py calibration-freeze --run-dir "diagnostics/TASK-T03E/<run_id>" --seed 20260925 --bootstrap-replicates 200

python solution/src/t03e_preregistered_rule_sensitivity.py frozen-validation --run-dir "diagnostics/TASK-T03E/<run_id>" --freeze-seal "diagnostics/TASK-T03E/<run_id>/phase_a_calibration_freeze/FREEZE_SEALED.json"

python solution/src/t03e_verify.py --run-dir "diagnostics/TASK-T03E/<run_id>"
```

真实命令可以调整脚本位置，但三种模式、同一run目录和两个独立分析进程不可合并。不得用同进程函数调用模拟两阶段冻结。

## 【prior exposure】

必须生成`prior_exposure.md`并纳入freeze manifest。内容必须明确写出：

- 项目历史中已经查看过部分A1 holdout汇总；
- 本次禁止使用这些历史摘要调参，但无法将本阶段描述为从未接触过的全新盲测；
- 本阶段的准确称呼是“参数冻结后的验证”；
- holdout结果只用于预注册accept/reject；
- extension只用于迁移与复现，不参与模型选择。

不得删除、弱化、改写为“完全盲测”或把历史接触描述成无关紧要。

## 【Holdout验收】

只比较：

- C：lambda=0.02的冻结候选；
- D：原`Q_baseline`。

holdout有效行定义与calibration相同，但角色改为`A1_holdout`。确认性验收只对freeze中已经登记为active correction且holdout有效n≥200的域进行。未施加规则的域、样本不足域和标签不存在域不进入通过率。

逐active域冻结门槛为：

- `Spearman(C,D) >= 0.98`，使用`(-score, frozen_joint_key)`确定性序位；
- `top10% Jaccard(C,D) >= 0.85`，`k=max(1,ceil(0.10*n))`；
- `abs(mean(P_holdout)-mean(P_calibration)) <= 0.05`；
- `OUT_OF_SUPPORT比例 <= 0.05`，分母为该域holdout有效行。

全局状态按以下优先级唯一确定：

1. 实现、哈希、冻结或输入完整性失败：`FAIL`；
2. 任一有n≥200的active域违反任一门槛：`REJECT_KEEP_D`；
3. 任一active域holdout有效n<200且没有门槛失败：`INSUFFICIENT_EVIDENCE_KEEP_D`；
4. 所有active域均n≥200且全部门槛通过：`ACCEPT_STABILITY`。

`ACCEPT_STABILITY`只表示预注册修正规则在冻结后的holdout上保持保守和稳定，不表示C优于D或更接近真实质量。任何失败只能回退D，不得切换A/B、改变域、重选lambda、改变分位或重新定义top-k。

## 【Extension验证】

### extension overlap

overlap只做复现与一致性，不作为独立泛化样本。对满足以下条件的配对：

- 同一冻结联合键；
- domain精确相同；
- `Q_baseline`、top-2gram、top-3gram数值相同；
- 同一冻结候选版本；

必须满足：

`abs(Q_C_left-Q_C_right) <= 1e-12`。

若相关输入不完全相同，输出逐字段差异和不可直接复现原因，不用高相关替代相等检查。

### extension new

只在实际存在freeze active correction域时评价迁移。逐active域有效n建议至少200；不足时登记`INSUFFICIENT_EXTENSION_EVIDENCE`，不宣布迁移成功。

对n≥200的active域：

- `OUT_OF_SUPPORT比例 <= 0.05`；
- `Spearman(C,D) >= 0.98`；
- `top10% Jaccard(C,D) >= 0.85`。

任一门槛不满足，登记`MIGRATION_FAILED_KEEP_D`，不得调参。

若extension new仅包含`RULE_NOT_APPLICABLE`、`INSUFFICIENT_CALIBRATION`或`DESIGN_LABEL_ABSENT`域，正式状态必须是：

`NOT_TESTED_FOR_ACTIVE_CORRECTION`。

这些域中C=D产生的Spearman=1、top-k完全一致或零OOS不能表述为迁移成功。

## 【规则簇与必须人工测试】

top-2gram和top-3gram永远是一个固定冗余簇。簇总权重由`P=(p2+p3)/2`固定；复制任一成员不得增加簇权重、改变P或改变Q_C。

在读取正式行级表的分析数值前，先用小型人工fixture测试：

1. `P`始终位于`[0,1]`；
2. 对有限有效行，`Q_C <= Q_baseline`；
3. 对有限有效行，`Q_C >= 0.98 * Q_baseline`；
4. lambda=0时`Q_C == D`，容差`1e-12`；
5. `RULE_NOT_APPLICABLE`域`Q_C == D`，容差`1e-12`；
6. 复制top-2gram或top-3gram输入后，`max_abs_delta(Q_C) <= 1e-12`；
7. 不产生新的零值，即`count(D>0 & Q_C==0)==0`；
8. D中原有零值保持零；
9. `Q_valid=False`行保持`Q_C=NaN`和`Q_INVALID_PRESERVED`；
10. 输入`Q_baseline`逐行不变；
11. 输入`Q_valid`逐行不变；
12. 惩罚函数在固定其他输入时对top-2gram和top-3gram分别单调非减；
13. Q_C在固定其他输入时对两项集中度分别单调非增；
14. `q99<=q95`、未知域、标签缺失和n不足均触发预注册状态，不能fallback。

人工测试必须使用独立手算expected或直接公式，不得让同一被测函数同时生成actual和expected。

正式数据阶段再次逐行核验上述1–11项，并报告实际分母。

## 【lambda敏感性】

只在calibration上固定报告`lambda ∈ {0,0.01,0.02,0.05}`：

- 平均、最大和分位惩罚；
- 相对D的确定性序位Spearman；
- top-10% Jaccard；
- 新增零值数；
- 按域的边界与支持状态。

primary始终是0.02。网格结果不得用来修改primary、缩小active域或设定holdout门槛。PHASE B禁止再次比较lambda网格。

## 【RegMix/Loss连接与识别性检查】

本任务只检查连接关系和是否存在可识别的独立质量变化，不训练新的桥接、回归、分类、缩放或损失预测模型。

至少检查并记录：

1. A质量域与RegMix域的映射是否有正式来源和唯一关系；
2. 聚合质量是否只是固定域质量`q_d`按配比`w_d`的线性组合：

\[
Q_{mix}=\sum_d w_dq_d;
\]

3. 既有模型是否已经包含全部配比向量`w`；
4. 是否存在同配比下独立质量变化、跨时间质量变化、文档选择变化或其他独立识别来源；
5. A数据Q与B表`Q_score`是否存在可靠样本级或实验级配对。

若`q_d`固定，且模型已经包含完整`w`，则`Q_mix`是`w`的确定函数，增加`Q_mix`后的训练拟合变化不能解释为独立质量信息。没有同配比下独立变化、可靠连接或其他识别来源时，输出：

`status=NOT_IDENTIFIABLE`

并在`regmix_loss_identifiability.json`中记录具体原因、已核对输入和需要T06补充的识别条件。不得因`NOT_IDENTIFIABLE`而强行拟合，也不得把它写成C失败；它表示本任务无法验证真实质量增量。

## 【T06接口】

正式输出`t06_quality_interface.parquet`及`t06_quality_interface.json`，至少同时保存：

- `Q_baseline`：当前正式主Q；
- `Q_C`：预注册规则敏感性候选；
- `DSIR_relevance_vector`：`dsir_books`、`dsir_wiki`、`dsir_math`三维辅助量；
- `Q_support_status`；
- `P`、`p_top2gram`、`p_top3gram`；
- 候选版本、active域和冻结参数版本；
- `Q_valid`、域、角色、唯一键及必要覆盖字段。

接口说明必须写明：

- 正式主Q仍为`Q_baseline`；
- `Q_C`没有独立真实质量标签验证，只能作预注册规则敏感性候选；
- DSIR是目标相关性向量，不是通用质量分量；
- A数据Q与B表`Q_score`仍需T06单独标定；
- 本任务的RegMix/Loss识别性状态。

禁止出现`final_Q`、`best_Q`或暗示自动替换主Q的字段名。

## 【必须输出的文件】

正式run至少输出：

|文件或目录|最低内容|
|---|---|
|`input_manifest.json`|正式Q01C输入、允许阅读证据、大小、mtime、SHA256和实际访问状态|
|`environment.json`|Python、NumPy、PyArrow/Pandas、平台、时区、CPU、内存和分位实现|
|`run_config.json`|任务范围、公式、lambda、网格、设计域、门槛、角色和随机种子|
|`command_log.json`|所有进程实际argv、PID、开始/结束时间和退出码|
|`access_log.jsonl`|逐次数据访问的时间、进程、文件、列投影、角色过滤和目的|
|`stage_status.jsonl`、`run.log`|元数据门禁、PHASE A、seal、PHASE B和verify事件|
|`metadata_preflight/calibration_domain_labels.csv`|calibration的domain精确字符串全集|
|`metadata_preflight/calibration_domain_inventory.csv`|calibration逐域计数及口径|
|`metadata_preflight/calibration_domain_label_match.csv`|四个设计标签与calibration标签的精确匹配|
|`metadata_preflight/calibration_key_commitment.json`|calibration键集合计数和哈希承诺|
|`phase_a_calibration_freeze/calibration_feature_profile.csv`|calibration范围、分位、唯一值及有效n|
|`phase_a_calibration_freeze/frozen_thresholds.csv`|active域的q95/q99/q005/q995和来源n|
|`phase_a_calibration_freeze/frozen_primary_spec.json`|C/D公式、状态枚举、active域和适用范围|
|`phase_a_calibration_freeze/frozen_active_domains.csv`|四个设计域的精确标签、n、资格及原因|
|`phase_a_calibration_freeze/bootstrap_seed_manifest.csv`|200次逐域确定性子种子|
|`phase_a_calibration_freeze/bootstrap_stability_detail.csv`|逐域逐replicate三项指标和联合PASS|
|`phase_a_calibration_freeze/bootstrap_stability_summary.csv`|逐域联合通过数和资格|
|`phase_a_calibration_freeze/lambda_sensitivity_calibration.csv`|固定网格描述结果，不选优|
|`phase_a_calibration_freeze/artificial_tests.json`|规则簇、边界、复制和fallback人工测试|
|`phase_a_calibration_freeze/preregistered_acceptance.json`|全部不可移动门槛和状态优先级|
|`phase_a_calibration_freeze/prior_exposure.md`|历史holdout接触限制|
|`phase_a_calibration_freeze/freeze_manifest.json`|冻结包文件、参数、代码、配置和输入哈希|
|`phase_a_calibration_freeze/FREEZE_SEALED.json`|seal哈希、时间、PID、命令和PHASE A结论|
|`phase_b_frozen_validation/holdout_validation.csv`|逐active域C/D验收和实际分母|
|`phase_b_frozen_validation/holdout_summary.json`|唯一holdout结论及失败原因|
|`phase_b_frozen_validation/extension_overlap_validation.csv`|同键一致性与输入差异|
|`phase_b_frozen_validation/extension_new_validation.csv`|active域迁移、OOS和排序预算|
|`phase_b_frozen_validation/extension_summary.json`|迁移、证据不足或未测试状态|
|`phase_b_frozen_validation/actual_domain_labels_all_roles.csv`|seal后按顺序合并的全角色domain精确标签全集|
|`phase_b_frozen_validation/domain_role_inventory.csv`|逐domain×role计数及首次读取时间|
|`phase_b_frozen_validation/domain_label_match_all_roles.csv`|设计标签在全角色中的精确匹配与首次出现角色|
|`phase_b_frozen_validation/regmix_loss_identifiability.json`|连接与识别性裁决|
|`candidate_Q_scores.parquet`|D、C、P、两项分量、支持状态、身份和分母字段|
|`t06_quality_interface.parquet/json`|正式T06接口及限制|
|`protected_baseline_check.json`|Q01C输入hash及逐行受保护列一致性|
|`checks.json`、`verification.json`|执行检查和独立复算结果|
|`run_summary.json`、`handoff.md`|任务状态、PHASE A/B结论、限制和主控待审项|
|`output_manifest.json`|除自身外最终文件路径、大小和SHA256|

失败run只输出已经真实产生的文件和失败状态，不用空文件伪装后续阶段完成。

`candidate_Q_scores.parquet`必须保留正式输入的全部272505条物理记录及原身份顺序关联，不删行、不去重覆盖。确认性统计只选择唯一首见有效行；重复物理行仍保留候选列。19条`Q_valid=False`记录的C保持NaN。最终先关闭运行日志、`run_summary.json`、`handoff.md`、checks和verification，再由独立finalizer最后生成`output_manifest.json`；manifest排除自身，生成后不得继续修改任何登记文件。

## 【随机种子、运行规模与资源预算】

- 主随机种子：`20260925`；
- bootstrap：每个active domain 200次；
- lambda网格：4个固定值，只在calibration报告；
- 输入规模：只处理正式Q01C行级Parquet中所需列，预期不超过正式272505条物理行；确认性分析使用唯一首见有效行；
- 并行：允许按域并行bootstrap，但每个domain×replicate子种子固定，1线程与并行结果必须一致；
- CPU预算：最多使用可见逻辑核的50%，上限8个worker；
- 内存预算：峰值RSS建议不超过8 GiB；超限前停止并保留证据，不通过交换或全表复制规避；
- 墙钟预算：metadata preflight 15分钟、PHASE A 90分钟、PHASE B 45分钟、独立verify 30分钟；任一阶段超时则保存`TIME_BUDGET_EXCEEDED`并停止；
- 输出预算：不含源码快照时建议不超过2 GiB；不得复制原始Parquet或正文。

资源预算是停止与复现边界，不得通过降低bootstrap次数、删除域或放宽门槛来“完成”。需要改变预算时停止并交主控重新发单。

## 【独立验收】

`t03e_verify.py`必须独立完成：

1. 从正式行级输入独立复算domain标签和逐角色计数；
2. 核对freeze前分析层只出现calibration行，holdout/extension的首次读取均在seal之后；
3. 独立复算calibration有效n、q95/q99/q005/q995；
4. 独立复算每行p2、p3、P和Q_C；
5. 独立重建确定性排序、top-10%集合及holdout验收；
6. 使用保存的bootstrap参数和固定reference rows复算稳定性摘要；不得调用执行脚本的惩罚或汇总函数；
7. 核对分位退化replicate被计为联合失败；
8. 核对冗余复制测试和所有数学边界；
9. 核对未应用域C=D且未被计入active证据；
10. 核对extension overlap、新记录状态和实际分母；
11. 核对freeze seal早于第一次holdout/extension读取，冻结文件在seal后哈希不变；
12. 核对holdout后没有参数、代码、配置或阈值改写；
13. 核对`Q_baseline`、`Q_valid`、身份和正式输入hash未变化；
14. 核对RegMix/Loss没有启动新拟合，`NOT_IDENTIFIABLE`原因完整；
15. 核对所有输出的`n_total/n_valid/n_missing/coverage`与行级结果一致；
16. 核对输出manifest生成后登记文件未继续修改。

verifier的expected公式必须在独立源码内明确实现，不能从`candidate_Q_scores.parquet`反向当作expected，也不能以执行脚本退出0代替验收。

## 【验收结论枚举】

执行AI最终任务状态只能是以下之一：

- `COMPLETE_PENDING_REVIEW`：获授权阶段全部完成、机器检查无关键FAIL，等待主控；
- `CALIBRATION_REJECTED_KEEP_D`：PHASE A不合格，未读取验证数值；
- `REJECT_KEEP_D`：holdout或迁移预注册门槛失败；
- `INSUFFICIENT_EVIDENCE_KEEP_D`：holdout有效n不足，不能宣布总体确认性通过；
- `FAILED`：泄漏、输入、冻结、实现、哈希、数值或独立验收失败。

即使holdout状态为`ACCEPT_STABILITY`，任务总状态仍只能为`COMPLETE_PENDING_REVIEW`，且正式主结果仍为D。

RegMix/Loss的`NOT_IDENTIFIABLE`是一个允许且必须诚实输出的方法结论；只要没有强行拟合、原因和检查完整，它不自动令工程任务失败，但它阻止“外部质量增量已验证”的声明。

## 【FAIL规则】

发生任一项即FAIL或按规定拒绝，不能现场修正后继续同一run：

1. 正式输入路径/hash与Q01C manifest不一致；
2. 重新读取、扫描、stat或hash真实A1–A3；
3. 修改正式Q01C、00–05或其他受保护产物；
4. calibration门禁向分析层返回任何非calibration行；
5. PHASE A唯一键分析内出现非calibration或非唯一首见行；
6. freeze seal前读取holdout/extension的Q或特征值；
7. seal后冻结文件、参数、active域、代码、配置或门槛变化；
8. calibration拒绝后仍读取验证数值或尝试补救；
9. 模糊域匹配、改域名、合并域或借用其他域阈值；
10. 选择lambda、运行A/B、PCA、熵权或CRITIC选优；
11. bonus、clip、额外惩罚或未授权fallback；
12. P、Q_C出现预期外非有限值或违反数学边界；
13. 复制冗余特征改变簇权重或Q_C；
14. 未应用域被计入active correction通过证据；
15. holdout失败后改参数、换候选或重新定义门槛；
16. extension参与模型选择或阈值估计；
17. RegMix/Loss不可识别时仍强行拟合；
18. verifier导入执行模块自证、关键检查有FAIL或manifest不一致。

## 【NOT_IDENTIFIABLE / NOT_TESTED规则】

- `NOT_IDENTIFIABLE`只用于缺少独立质量变化、可靠连接或尺度标定的RegMix/Loss外部关系，并必须附结构性原因；
- `NOT_TESTED_FOR_ACTIVE_CORRECTION`只用于extension没有任何active correction适用域；
- `INSUFFICIENT_EXTENSION_EVIDENCE`用于实际有active域但该域有效n不足200；
- 这些状态不得改写为PASS，也不得用C=D的完美一致填补；
- `NOT_IDENTIFIABLE`阻止外部质量提升主张；`NOT_TESTED`和`INSUFFICIENT`阻止迁移成功主张。

## 【停止条件】

出现以下任一情况立即停止，保存当前run、错误栈、访问日志和阶段状态：

- 需要重新读取A1–A3；
- `Q_baseline`、`Q_valid`或身份基线发生变化；
- freeze前读取holdout/extension分析数值；
- 发现holdout/extension曾被当前run用于参数选择；
- holdout后参数或冻结文件发生变化；
- calibration资格失败；
- calibration失败后程序试图读取holdout补救；
- 实际域标签存在歧义，无法与预注册设计域可靠对应；
- 候选产生非有限值、越界或违反边界；
- 外部连接不可识别但脚本试图强行拟合；
- 资源或墙钟预算达到上限；
- 独立验收出现关键FAIL。

正常完成全部获授权输出后也必须停止，不启动T06、不修改02决定、不写最终论文结论。

## 【完成后必须交回的材料】

执行AI必须交回：

- 正式run绝对路径和run_id；
- metadata、PHASE A、freeze seal、PHASE B和verify的实际命令、PID、时间和退出码；
- domain精确标签及逐角色计数；
- active域资格及全部冻结阈值；
- 200次bootstrap逐次和汇总结果；
- 冻结包与seal哈希；
- 第一次holdout/extension读取时间及访问日志；
- holdout唯一accept/reject结论；
- extension overlap/new状态；
- RegMix/Loss识别性状态；
- 受保护基线未变化证据；
- 独立checks、verification和最终manifest；
- `prior_exposure.md`；
- T06接口及其限制说明；
- 所有FAIL、NOT_IDENTIFIABLE、NOT_TESTED和INSUFFICIENT状态。

交回说明必须再次写明：**C仅为预注册规则敏感性候选，D=`Q_baseline`仍是正式主结果。** 执行AI只能提交`COMPLETE_PENDING_REVIEW`或相应失败/拒绝状态，不得宣布Q_C成为最终Q。
