# TASK-Q01A 主控审查与精准小修要求

审查日期：2026-09-24。结论：**小修；尚未整体验收通过，不进入TASK-Q01B。**

本文件是审查结论和交回执行AI的小修要求，不是已经执行的小修。本轮未重扫A1–A3、未运行原诊断脚本、未选择缺失处理策略，未修改01/04/05或原运行产物。

路径均相对项目根目录：

`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace`

正式证据目录：`diagnostics/TASK-Q01A/20260924T142229+08/`，下文简称R。首次失败目录`diagnostics/TASK-Q01A/20260924T141414+08/`只作失败证据，不合并统计。

## 【TASK-Q01A审查结论】

**小修。** 7个原始FAIL大部分确实来自检查器接线、索引空间或默认值处理问题，但事后复核不能证明整份诊断已经正确。主控独立发现7个FAIL之外的三个实质错误，涉及施工单明确要求的原始异常行数、原始层缺失模式以及summarize实际分母。

原始`checks.json`的33 PASS/7 FAIL、`run_summary.json`的PARTIAL/退出码2及`handoff.md`必须保持原样。不能现在将任务标为“实质通过”；这些历史记录保留不改，修正结果应通过新的补充证据另行验收。

此次主控核验范围：只读审查许可文档、R内脚本和汇总；实际复核output_manifest的34个文件哈希、input_manifest的111个受保护文件哈希，均一致；当前诊断脚本哈希与environment记录一致。读取133条异常事件，抽查row_masks中的A1第12094行；未全量重算行掩码。用一条人工“两组有限、一组NaN”样例核对现用pandas语义，不涉及真实Q计算。对已有小型汇总表进行了计数/口径交叉检查。

## 【已确认可信的结果】

以下为现存产物、源码及相互独立的已有审计之间可对照的事实；不表示主控重新解析过XZ。

- 记录总数272505，唯一键261086，重复11419；各文件51230/17523/203752。正式日志记载解析失败0、每文件单遍解压；与旧audit及现存汇总相符。
- all_unique的11特征完整数与25特征完整数均为261067，未覆盖19，完整率0.9999272270439625。
- 提取层modernbert_professionalism失效6行，modernbert_reasoning失效13行，交集0、并集19；提取/归一化的相应缺失表和异常事件支持该结论。不能把此结论扩大成“原始层掩码也正确”。
- 唯一缺失案例分布：wikipedia14、commoncrawl4、github1；calibration13、holdout5、extension_new1、extension_overlap0。
- 三个质量组在all_unique中的有效数：usability261086、knowledge261080、education_reasoning261073。19个不完整案例均仍有两个有效组，其他261067个案例有三个有效组，没有0组或1组有效的案例。
- complete-case文件目前只是计数，没有因此删除记录。未发现生成新的最终Q或实施插补的证据；许可范围内受保护文件的当前哈希与运行前记录一致。
- 三个XZ前后哈希一致有正式C09及代码中实际前后读压缩字节哈希流程支持。本轮主控没有再次读取XZ，不能把这一项写成“主控重新计算了三文件哈希”。

## 【未确认或有风险的结果】

### R1-01：原始层nan_rows错把元素当记录

R/diagnose_missingness.py第645–649行在列表元素循环里逐元素增加`detail['nan_rows']`；随后第1933行直接输出该值。`posinf_rows`、`neginf_rows`同样存在此设计问题，虽然本次数据对应值为0。

R/raw_field_counts.csv已出现以下错误：

|文件/域/字段|现存nan_rows|应为异常记录数|NaN元素数（该数本身可保留）|
|---|---:|---:|---:|
|A1/commoncrawl/professionalism|24|4|24|
|A1/wikipedia/professionalism|6|1|6|
|A1/wikipedia/reasoning|78|13|78|
|A1/ALL/professionalism|30|5|30|
|A3_github/github及ALL/professionalism|6|1|6|

修正依据必须由已保存的raw异常事件按`file_id, source_line, field_or_feature, reason`去重计算；元素数保留事件级计数。不得仅把表中值除以6作为通用修复。

### R1-02：原始异常掩码漏记NaN

`audit_field()`为NaN/Inf写出了异常事件，却没有把它们加入返回的`reasons`；第854–865行仅在reason非空时置原始异常位。因此`row_masks.raw_invalid_bits`及`missing_patterns`的raw_field_invalid层全部为零，raw层pairwise中上述两个字段的边际/并集也都是0。

这与114条原始NaN元素事件、19条提取NaN事件以及raw_field_counts中的有效列表数直接冲突。不是检查器空变量导致的假FAIL，而是诊断派生值错误。异常事件保留了文件和行号，因此可在不读取原始XZ的前提下重建正确原始掩码。

### R1-03：分歧range/std有效分母计算错误

R/diagnose_missingness.py第1266–1271行把`norm_nonfinite`（包括NaN）传播成`group_nf_rows`，进而把“任一组缺失”都计作range/std缺失。旧`solution/src/quality_audit.py`第315–316行却使用默认skipna，两个有限组仍能计算极差和ddof=0标准差。

现存group_validity_distribution表表明all_unique全部案例至少有两个有效组，且归一化非NaN的Inf为0。因此：

|all_unique/ALL统计项|现存值|按旧逻辑应有的计数|
|---|---:|---:|
|rater_disagreement_mean有效n|261067|261086|
|rater_disagreement_std有效n|261067|261086|
|gt_0_5中“缺失range比较变False”的行数|19|0|
|gt_0_5均值分母|261086|261086（该分母本来正确）|

这里没有重算实际极差、标准差或阈值真假，只根据有效组分布和旧源码确定可计算性。本轮小表核对发现range/std共40行错误，False计数20行错误，分布在20个scope/domain组合。需对全部相应行修正，不能只修ALL。

现有C31从row_masks复读后仍调用同一个`aggregate_rows()`，能发现保存不一致，却不能检出同一函数的语义错误。人工测试验证了pandas规则，但mini_aggregate没有把该规则与输出分歧分母作端到端对照，故C06/C24/C31的PASS不足以排除此问题。

### 其他需澄清的口径

- Q_std表的`n_effective=261067`是有效样本数，不是样本方差的n−1分母。应明确另列方差除数261066及n<2时状态；不要模糊使用“分母”一列。
- C08事后检查只证明全目录路径/大小与登记一致及三个XZ哈希一致，没有检查全目录mtime前后相同。不得将它作为原C08完整命题的PASS。
- C12事后JSON的`overlap_role_row_totals`写成A2=2838、A3=20000，因把ALL汇总行与域行重复相加；正确对照数是1419和10000。主要per-file数正确，但补充证明内部仍有矛盾。
- 首次失败日志明确记录`stage=precondition hashed_inputs=3`，然后在build_input_manifest因RUN_ID缺失终止。因此应写“读取压缩字节哈希后、解压扫描前失败”，不能写“读取任何原始数据前失败”。这次失败仍不计入正式诊断样本。
- 按域/角色“占同scope全部缺失案例的比例”未显式交付；已有缺失率是域内缺失/域总n，与该比例不同。小修应补分子分母及未定义状态，避免把两者混用。
- comparison_with_prior中10条NOT_COMPARABLE是按任务要求不重算旧数值Q的条目；保留该状态即可，不应把这些条目强行变成MATCH或要求重建Q。

## 【7个FAIL的裁决】

|原检查|主控裁决|事后证据的效力与需修正处|
|---|---|---|
|C07|主要是snapshot_diff未写入ctx的接线缺陷|主控实际核对111个既有受保护文件哈希一致，支持这些文件未变；该核验只覆盖列出的文件，不凭空扩成完整目录新增文件检查。原FAIL保留|
|C08|接线缺陷加长路径覆盖不足|事后2012文件的路径/大小核对是补充证据；它替换了原mtime命题，不能说完全等价复核。拆分出“路径/大小”“三XZ哈希”“历史全目录mtime”三项，最后一项缺证据则NOT_VERIFIABLE，不重新制造历史快照|
|C11|prior_audit没有存入ctx|实际总量与旧audit相符；事后只读复核足以支持该计数比较|
|C12|同C11|主要逐文件计数一致；补充role_totals重复计数仍须修正并加入实际判定，当前事后JSON不是无矛盾的PASS证据|
|C13|同C11|实际跨文件交集1419/10000/0与旧audit一致；事后只读比较可支持该项|
|C15|row_masks_rows没有存入ctx|正式再聚合记录含272505行，n_row_keys也可用于身份覆盖证据；补充复核须显式核对文件/行号唯一性及行号覆盖，而非只用总行数推出一一对应。没有证据表明原始数据需重扫|
|C23|25维与11维bit索引错位，且零计数缺省值处理有缺陷|按feature名称映射复核的方向正确，支持提取与归一化NaN一致；原检查对不存在的零异常计数用get(...,1)也会假FAIL，修正版须显式记录0、区分未检查。该复核与R1-01/02/03无关，不能替代它们的验收|

对用户A–E问题的明确回答：A，七项多数是检查器缺陷，但C08/C12的事后补证仍不完整或含错；B，补证可支持相应部分计数，不能证明全部科学诊断正确；C，需要本文件列出的局部小修；D，目前不能认定实质验收通过，原PARTIAL保留；E，无需重扫原数据，现有证据足够完成小修，但应小修验收后才进入Q01B。

## 【是否需要重新运行】

**不需要重新执行完整诊断，不需要读取或解压A1–A3。** 小修仅使用已保存的row_masks、invalid_values及汇总文件，运行新的后处理与独立验收脚本。主控本轮没有执行这些小修。

### 执行AI小修边界

只读输入：R内全部原证据、旧quality源码及必要定义、原施工单、本审查要求。首次失败目录只读日志。禁止重新读取原始XZ（包括不必要的再次哈希）、调用原诊断main、重跑模型、产生数值Q、选择策略。

所有修改写入新目录`diagnostics/TASK-Q01A-R1/<实际run_id>/`。原两个运行目录、旧quality结果、原诊断源码、原checks及事后JSON、根目录00–05都不得覆盖。新修正代码独立保存；不得给原PARTIAL改状态。

### 仅执行以下五项小修

1. **修正原始层计数和掩码。** 用既有invalid_values的raw事件构建按行/字段异常集合，以file_id+source_line与row_masks一一连接。补齐事件域/键时只能从这个连接取得。分别输出元素数、去重记录数；修正raw_invalid掩码、raw层patterns/pairwise。读取事件CSV时禁用把字符串`nan`自动解释成空值的默认解析，否则会丢失19条extract事件的reason分类。其他已正确的提取/归一化/Q缺失掩码不得改变。
2. **修正分歧统计分母并澄清Q_std。** 在本次全部非缺失组有限的条件下，range和ddof=0组间std有至少一个有效组即可定义；0有效组才缺失。不要用any-nonfinite代替该逻辑。按全部scope/domain重建相关三项，补充Q_std有效n与n−1除数。不得计算真实组得分、Q或极差数值。
3. **补独立验收，防止同源错误自证。** 用独立的小型人工矩阵覆盖0/1/2/3个有效组和含NaN的六元素列表；先由pandas或直接集合定义取得期望，再对照待验收后处理输出，不能由同一函数生成期望和实际。检查异常事件→原始掩码→提取掩码对应、模式/交集和分母。逐文件验证row_masks源行号唯一并覆盖1..已记录物理行数；仅从既有行表核对，不访问XZ。
4. **纠正事后复核的范围和计数。** 针对7项输出新的逐项裁决：C08历史mtime无法补证则明示保留限制；C12按ALL或域明细择一汇总，不能叠加；C23按特征名映射并显式输出零计数；C07限定111文件范围。增加对R1-01/02/03的验收，不再只写7/7PASS。首次失败说明按实际日志纠正。无需追求历史全部检查变PASS。
5. **补机器可审查的缺失构成占比及交回材料。** 各scope按域/角色报告缺失数、域内缺失率、在该scope全部缺失中的份额，显式分子分母；无缺失分母用null+原因。统一修正说明，不更新建模策略。

### 必须交回的修正产物

- `repair_from_artifacts.py`与独立`verify_repairs.py`、实际运行命令/环境/日志。
- `input_manifest.json`：只读旧产物哈希；`output_manifest.json`：所有新文件哈希。
- `raw_field_counts_corrected.csv`。
- `raw_mask_corrections.csv`：稀疏修正表，逐物理行列旧/新raw_invalid_bits/count及证据；正常行默认沿用旧掩码。可选另导出完整row_masks_corrected.csv.gz，但必须保留全部物理行并证明只有许可列发生变化。
- `missing_patterns_corrected.csv`、`missing_pairwise_corrected.csv`：修正原始层，其他层保持不变并验证。
- `summary_denominators_corrected.csv`：包括明确的variance_divisor及未定义状态；统计量名字/计数口径可追溯到旧表。
- `missing_concentration.csv`：域/角色缺失率和缺失构成占比。
- `postrun_reconciliation_reviewed.json`：原7项及新发现问题分别登记，包含原命题、证据实际范围、原结果、当前核验结果和未能验证项。
- `repair_checks.json`、`changes.csv`、`run_summary.json`、`handoff.md`。changes须逐表列受影响字段/键、前后值和证据来源；交回只声明补证/小修状态，不宣称原进程退出0。

### 精确验收锚点

- 从事件去重得到原始异常19个物理记录：A1 professionalism5、A1 reasoning13、A3 professionalism1；NaN元素总数仍为114，分文件/字段为30、78、6；原始层失效并集19，两字段交集0。这些是本轮已有证据导出的核对锚点，执行AI必须以实际后处理得到，不可手填。
- 正确提取层19案例、完整261067及所有现存正确统计保持不变；修正只能改变有证据支持的原始层掩码和受影响派生项。
- all_unique两个分歧统计的有效n均为261086；因缺失range而比较为False的行数0；Q_mean有效n仍261067，Q_std有效n261067、方差除数261066。其余scope/domain遵循同一规则逐项验证。
- C12扩展重叠计数A2=1419、A3=10000，不能再次出现倍数统计。
- 所有旧文件哈希未变；无原始数据读取、无数值Q、无策略实施。未解决的关键科学计数或分母错误必须FAIL；历史mtime缺证据用NOT_VERIFIABLE并解释，不能伪填PASS。
- 若从已有证据无法完成某项修正，停止并写明缺口，交回主控，不自行扩大为全量扫描。

## 【是否允许进入TASK-Q01B】

**暂不允许。** 先完成上述局部小修并交回主控复审。通过后再更新01/04/05，并进入Q01B方法比较与裁决；即使未来裁决完成，也不因本单自动获得修改质量流水线或实施缺失处理的授权。
