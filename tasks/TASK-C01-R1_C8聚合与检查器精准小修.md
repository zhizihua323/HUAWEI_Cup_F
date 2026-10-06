# TASK-C01-R1正式施工单：C8聚合与检查器精准小修

状态：**施工单已编制，未执行。只有收到单独执行指令后才能开工。**

本施工单与`TASK-Q01C-R1`相互独立，可由两个执行AI并行执行。执行本任务时不得读取、写入或依赖`diagnostics/TASK-Q01C-R1/`中的任何产物。

## 【任务编号】

TASK-C01-R1。

前置任务：TASK-C01正式审计run已完成，主控只读审查结论为“小修”。C1–C10基础事实、C8解析日志和C5/C6可比性事实可复用；本任务只做既有C01产物的后处理、C8口径修正和检查器补证。

## 【任务名称】

TASK-C01 C8聚合与检查器精准小修。

## 【任务性质】

已有C01产物的后处理和检查器小修。不得重新扫描原始数据，不得进入后续建模。

## 【任务背景】

原正式目录为：

`diagnostics/TASK-C01/20260924T175553+08/`

原run确认了1958个C8 JSON中1954个解析成功、4个解析失败，并保留了逐文件parse log、损坏文件清单、六任务group score明细和模型聚合表。但主控审查发现：

1. 目录级表只记录`n_json_files`，没有把解析成功、失败和有效结果数分开。
2. 损坏JSON没有充分传播到目录和模型覆盖统计。
3. 宽表的`six_task_mean_c8_raw`使用行均值，6个缺任务模型仍获得数值，容易被误解为完整六任务均值。
4. 原检查器中存在恒真或硬编码PASS，包括`raw_untouched`、C8-06、DATE-03、CMP-03以及若干JOIN/SCOPE项。
5. 无法由现有证据验证的事项应记NOT_CHECKED或NOT_VERIFIABLE，而不是制造PASS。

## 【目的】

1. 从现有C01机器产物重建明确的C8目录覆盖统计。
2. 将解析失败传播到目录、模型任务和模型宽表的覆盖字段。
3. 严格区分完整六任务均值与部分任务均值。
4. 重写检查器，使每个PASS都有可复查的actual、expected和evidence。
5. 对无法事后补证的历史事项诚实标记NOT_CHECKED或NOT_VERIFIABLE。
6. 保留OOS-01至OOS-12等后续方法问题，不在本任务中解决。

## 【为什么现在必须先做】

C8宽表是问题四后续建模的候选输入。如果缺任务模型的skipna均值被当作完整六任务均值，或损坏文件没有进入覆盖字段，后续排序、趋势和回归会混入不可比记录。检查器中的恒真PASS也会掩盖证据不足。

## 【输入文件】

原正式目录完全只读。允许读取：

- `handoff.md`
- `run_summary.json`
- `checks.json`
- `output_manifest.json`
- `data_inventory.csv`
- `field_audit.csv`
- `missingness.csv`
- `duplicate_audit.csv`
- `model_identity_audit.csv`
- `date_audit.csv`
- `unit_audit.csv`
- `c5_c6_comparability_audit.csv`
- `c8_parse_log.csv`
- `c8_corrupt_files.csv`
- `c8_directory_file_counts.csv`
- `c8_task_inventory.csv`
- `c8_group_scores_all_runs.csv`
- `c8_leaf_metrics.csv.gz`
- `c8_model_task_aggregate.csv`
- `c8_model_wide_canonical.csv`
- `join_coverage.csv`
- `audit_c01.py`，仅用于定位原聚合/检查逻辑，禁止修改

允许只读核对`solution/src/evolution_audit.py`的当前SHA256与原run登记值；不得运行、导入或修改该文件。

## 【禁止读取或重扫的原始数据】

- 不重新解析1958个C8 JSON。
- 不重新打开C8 JSON以抽查内容。
- 不重扫C1–C10原始CSV、Parquet、JSON或README。
- 不以“独立复核”为由重新运行`audit_c01.py`。

所有修正必须只从原正式目录的现有产物得到。

## 【禁止修改的文件和目录】

- `diagnostics/TASK-C01/20260924T175553+08/`全部文件。
- `solution/src/evolution_audit.py`。
- 全部`F题/`原始材料。
- `00_PROJECT_BRIEF.md`至`05_REVIEW_LOG.md`。
- Q01A/Q01B/Q01C及其R1证据和源码。
- 配比、质量、缩放、预测、优化和论文模块。

## 【允许修改范围】

原正式目录外可新建：

- `diagnostics/TASK-C01-R1/<run_id>/repair_c01_from_artifacts.py`
- `diagnostics/TASK-C01-R1/<run_id>/verify_c01_repairs.py`
- 必要的只读输入适配、schema说明和专项测试

不得把修复直接写回`audit_c01.py`或原CSV/JSON。不得修改`evolution_audit.py`。

## 【R1输出目录】

正式R1目录固定为：

`diagnostics/TASK-C01-R1/<run_id>/`

目录存在时必须失败退出，禁止覆盖。所有corrected、checks、verification、代码快照和日志必须位于该目录。

## 【C8口径定义】

### 文件口径

- `n_files_total`：目录中`c8_parse_log.csv`登记的JSON文件数。
- `n_files_parse_success`：`parse_status == "ok"`的文件数。
- `n_files_parse_failed`：`parse_status != "ok"`的文件数。
- 每个目录必须满足：`n_files_total = n_files_parse_success + n_files_parse_failed`。

### 有效结果口径

- `n_results_valid`：该目录在`c8_group_scores_all_runs.csv`中六个规定任务的**有限group score单元数**。
- `n_results_missing`：解析成功文件应产生的六任务槽位数减去`n_results_valid`。
- 解析失败文件不生成伪任务分数，不得把失败文件计作六个缺失任务来和“解析成功但缺任务”混为一谈；文件失败由独立字段传播。

### 模型六任务口径

- `n_tasks_valid`：模型宽表中六个任务得分为有限值的个数。
- `six_task_complete`：当且仅当`n_tasks_valid == 6`。
- `six_task_mean_complete_only`：仅当`six_task_complete=True`时计算六个任务的算术均值；否则必须为空/NaN。
- `partial_task_mean`：若保留，仅在`1 <= n_tasks_valid < 6`时计算，并必须在字段说明和报告中称为“部分任务均值”；完整模型行可留空，避免与完整均值混淆。
- 不得把`DataFrame.mean(axis=1)`的默认skipna结果命名或解释为完整六任务均值。

## 【损坏JSON传播要求】

1. 四个失败文件必须继续逐文件保留目录、文件名、SHA256、错误类型、错误位置和疑似截断证据。
2. 目录级corrected表必须包含`has_parse_failure`、失败数和成功数。
3. 有可解析文件的损坏目录可保留其有效分数，但必须同时带`source_parse_incomplete=True`。
4. 只有损坏文件、没有任何可解析文件的目录必须保留目录行，`n_files_parse_success=0`、`n_results_valid=0`，不得从覆盖统计中消失。
5. 模型身份只能来自已经解析成功的产物；不得从损坏JSON或目录名猜造模型名。
6. 三个没有可解析文件的损坏目录可不进入模型宽表，但必须在目录级表和handoff中单独列出。

## 【必须生成的corrected表】

### `c8_directory_aggregate_corrected.csv`

每个目录一行，至少包含：

- directory
- n_files_total
- n_files_parse_success
- n_files_parse_failed
- has_parse_failure
- has_any_parseable_file
- n_results_valid
- n_results_missing
- source_parse_incomplete

### `c8_model_task_aggregate_corrected.csv`

以原模型×六任务表为基础，至少补充：

- 对应目录文件总数/成功数/失败数
- source_parse_incomplete
- n_valid_results
- n_missing_results
- canonical分数是否有限
- 完整的来源键，不得丢失原多次评测信息

不得重新决定95个多文件目录的下游取舍规则；原canonical和legacy列可以保留，但必须明确只是既有两种口径。

### `c8_model_wide_corrected.csv`

至少包含：

- model_key / Model
- 六个任务分数
- 六个任务各自的有效结果数
- n_tasks_valid
- six_task_complete
- six_task_mean_complete_only
- partial_task_mean（如保留）
- n_files_total / n_files_parse_success / n_files_parse_failed
- source_parse_incomplete

原`six_task_mean_c8_raw`可作为`legacy_partial_or_complete_mean`保留用于追溯，但不得再作为正式六任务均值。

## 【检查器精准小修要求】

新检查器必须与生产修复逻辑独立：

- 不得导入`repair_c01_from_artifacts.py`。
- 不得调用同一个聚合函数同时生成actual和expected。
- 必须从parse log、corrupt list、group score明细、directory counts等原始既有产物独立复算。
- 所有检查都必须包含：`check_id`、`status`、`claim`、`actual`、`expected`、`evidence`、`verification_method`和`limitations`。
- 禁止`PASS if True`、预设`raw_untouched=True`、无条件`PASS`或只因文件存在而PASS。

### 必须修复的检查

1. **raw_untouched / SCOPE-04**：原run没有完整的运行前后原始附件hash快照时，不得补造PASS。只能登记历史`NOT_VERIFIABLE`；R1自身可以证明“只读原C01目录且没有访问原始C1–C10”。
2. **C8-06**：从`c8_task_inventory.csv`与`c8_leaf_metrics.csv.gz`独立核对非数值计数，不得恒真PASS。
3. **DATE-03**：至少交叉核对C4行数、Publication date非空数、解析成功数、解析失败数与`missingness.csv`；“未插补”若缺少直接证据，必须拆成可验证计数和NOT_VERIFIABLE声明。
4. **CMP-03**：通过输出manifest、C5/C6表schema、run summary及代码静态证据验证是否生成桥接/预测产物；证据不足时NOT_CHECKED，不得硬编码PASS。
5. **JOIN相关检查**：能从现有两份独立产物复算的必须复算；只有同一生产表自报、无法独立重建的，标记NOT_CHECKED/NOT_VERIFIABLE。
6. **SCOPE相关检查**：通过输出manifest、文件allowlist、源码hash和R1访问日志验证；不得仅引用原run文字声明。
7. 其他原有常量PASS也应一并清理，不能只修点名项后留下同类问题。

## 【独立复算步骤】

1. 从`c8_parse_log.csv`按目录独立汇总文件总数、成功数、失败数。
2. 将`c8_corrupt_files.csv`与parse log失败集合做双向集合核对。
3. 从`c8_group_scores_all_runs.csv`独立计算每目录、每任务的有限结果数和缺失槽位。
4. 与`c8_directory_file_counts.csv`的目录集合和文件总数核对。
5. 从`c8_model_task_aggregate.csv`独立构造模型六任务透视表，不调用修复脚本的透视函数。
6. 从六任务列复算`n_tasks_valid`、完整标记、完整均值和部分均值。
7. 将损坏目录覆盖字段传播到模型任务表和宽表；三类表的目录覆盖必须可追溯。
8. 从`c8_task_inventory.csv`和`c8_leaf_metrics.csv.gz`复核非数值指标计数。
9. 从现有date、join、C5/C6、manifest和run summary证据重建checks；不可重建的检查诚实降为NOT_CHECKED/NOT_VERIFIABLE。

## 【精确验收锚点】

### C8文件和目录

- JSON文件总数：1958。
- 解析成功：1954。
- 解析失败：4。
- JSON目录数：1863。
- 1个JSON的目录：1768。
- 2个JSON的目录：95。
- 失败涉及4个目录；其中1个目录有另一份成功文件，3个目录没有任何成功文件。

四个损坏目录必须为：

- `DreadPoor_Winter_Dawn-8B-TIES`：2文件、1成功、1失败。
- `FINGU-AI_Chocolatine-Fusion-14B`：1文件、0成功、1失败。
- `Intel_neural-chat-7b-v3-3`：1文件、0成功、1失败。
- `L-RAGE_3_PRYMMAL-ECE-7B-SLERP-V1`：1文件、0成功、1失败。

### C8任务结果

- 解析成功文件×六任务槽位：11724。
- 有限group score：11699。
- 缺失group score槽位：25。
- corrected目录表`n_results_valid`合计必须为11699。
- `DreadPoor_Winter_Dawn-8B-TIES`的成功文件提供6个有限group score；另外三个纯损坏目录为0。

### 模型任务与宽表

- 模型×任务聚合行：11160。
- `n_valid_results > 0`的模型任务行：11135。
- `n_valid_results == 0`的模型任务行：25。
- `n_valid_results`总和：11699。
- 模型宽表行数：1860。
- `n_tasks_valid`分布：`{1: 3, 2: 1, 3: 2, 6: 1854}`。
- `six_task_complete=True`：1854。
- `six_task_complete=False`：6。
- `six_task_mean_complete_only`有限值数：1854；6个partial模型必须为空。
- 若保留`partial_task_mean`，其有限值数必须为6，且不得被命名为六任务均值。

### 其他既有事实

- C1/C2行数均为4576；严格`DataFrame.equals=False`。
- C1/C2严格不同数值单元515个，最大绝对差`3.552713678800501e-15`。
- C9与C1模型集合相等且逐行同序；该结论不得被解释为独立评测。
- C5为43行、C6为75行，按Model合并43行；本R1拟合桥接模型数必须为0。
- `c8_task_inventory.csv`的`nonnumeric_metric_values`合计为7806；必须由两个既有产物交叉核对后才能PASS。

## 【必须输出的文件】

R1目录至少包含：

- `c8_directory_aggregate_corrected.csv`
- `c8_model_task_aggregate_corrected.csv`
- `c8_model_wide_corrected.csv`
- `repaired_checks.json`
- `verification.json`
- `changes.csv`
- `input_manifest.json`
- `protected_original_run_check.json`
- `environment.json`
- `run.log`
- `run_summary.json`
- `handoff.md`
- `repair_c01_from_artifacts.py`
- `verify_c01_repairs.py`
- `code_snapshot/`
- `output_manifest.json`

可增加schema说明、coverage reconciliation和NOT_VERIFIABLE清单，但不得省略上述核心文件。

## 【必须记录的数值】

- 输入文件路径、字节、SHA256和原manifest对应项。
- 目录数、文件总数、解析成功/失败、有效/缺失group score。
- 四个损坏目录的逐目录覆盖字段。
- 模型任务行数、有效/零结果行数、`n_valid_results`总和。
- `n_tasks_valid`分布、完整模型数、部分模型数。
- 完整均值与部分均值的有限值数。
- 每个repaired check的actual、expected、status和证据路径。
- PASS/WARN/FAIL/NOT_CHECKED/NOT_VERIFIABLE各自数量。
- 原C01目录R1前后hash变化、缺失和新增文件数。
- 是否读取过任何C1–C10原始文件，必须为False。

## 【验收标准】

只有同时满足以下条件，R1才可标记`COMPLETE_PENDING_REVIEW`：

1. 原C01目录前后完全不变。
2. 未重新解析任何C8 JSON，未重扫C1–C10。
3. corrected目录表覆盖1863个目录并满足1958=1954+4。
4. 四个损坏文件和四个损坏目录全部传播，无静默丢失。
5. 11699个有限group score、25个缺失槽位可从明细独立复算。
6. 1854个完整模型和6个partial模型区分正确。
7. 6个partial模型的`six_task_mean_complete_only`全部为空。
8. 新检查器没有恒真、硬编码PASS或共享生产聚合函数自证。
9. 关键C8修复项为0 FAIL、0 NOT_CHECKED、0 NOT_VERIFIABLE。
10. 历史上确实无法补证的非关键项允许NOT_VERIFIABLE，但必须单列且不计PASS。
11. OOS-01至OOS-12只登记，不执行方法裁决或后续建模。
12. 最终output manifest生成后全部文件hash一致。

## 【FAIL / NOT_VERIFIABLE规则】

### 必须FAIL

- 打开或重新解析任一原始C8 JSON。
- 重扫C1–C10或重新运行`audit_c01.py`。
- 修改原C01目录、`evolution_audit.py`或任何原始附件。
- 文件总数、成功数、失败数无法满足1958=1954+4且无已确认解释。
- 四个损坏文件未全部传播到目录覆盖。
- 用skipna均值填入`six_task_mean_complete_only`的partial模型。
- 6个partial模型仍被标记为six-task complete。
- verifier导入生产修复模块或调用同一聚合函数生成期望值。
- 任何检查继续使用`PASS if True`、预设True或无证据硬编码PASS。
- 为得到预期锚点修改原始或原C01产物。

### 应记NOT_CHECKED / NOT_VERIFIABLE

- 现有产物不包含足够字段，无法独立复算某项JOIN事实：记NOT_CHECKED。
- 原run缺少历史运行前后证据，无法证明原始附件当时未被修改：记NOT_VERIFIABLE。
- 只能由原run文字声明支持、没有机器证据的范围性结论：记NOT_CHECKED或NOT_VERIFIABLE。

不得把NOT_CHECKED或NOT_VERIFIABLE计为PASS。关键C8计数、损坏传播、完整均值和模型覆盖不允许使用这两种状态。

## 【停止条件】

1. 发现必须重新打开原始C8 JSON才能完成修复时立即停止，交主控裁决。
2. 发现现有产物之间的目录、文件或group score集合冲突且无法解释时停止，不自行补造记录。
3. 原C01目录任一文件发生变化时立即停止并标记FAIL。
4. 关键C8独立复核出现FAIL时停止，保留全部证据，不修改验收锚点。
5. 发现修复需要选择95个多文件目录的最终取舍规则时停止；该问题属于OOS-02。
6. 完成交付后停止，不更新00–05，不运行Loss–Benchmark、时间预测或问题四建模。

## 【完成后必须交回的材料】

- R1绝对路径和run_id。
- 输入与原C01目录未变化的manifest证据。
- 三张corrected表及schema说明。
- 四个损坏目录传播对照。
- 六任务完整/部分模型对照和均值列验证。
- 原检查器恒真/硬编码项的逐项修复说明。
- repaired checks与独立verification结果。
- 全部FAIL、WARN、NOT_CHECKED、NOT_VERIFIABLE清单及原因。
- changes、run summary、handoff和output manifest复核结果。

施工单编制完成后停止。本文件本身不授权执行TASK-C01-R1。
