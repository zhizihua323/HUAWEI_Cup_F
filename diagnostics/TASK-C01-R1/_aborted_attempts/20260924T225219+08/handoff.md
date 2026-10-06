# TASK-C01-R1 交接：C8 聚合与检查器精准小修

- run_id：`20260924T225219+08`；绝对路径：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-C01-R1\20260924T225219+08`
- 执行代码：`repair_c01_from_artifacts.py`, `verify_c01_repairs.py`（均在本目录，另有 `code_snapshot/`）
- 运行时间：2026-09-24T22:52:20.447906+08:00 至 2026-09-24T22:52:23.958748+08:00
- 输入仅限冻结的 TASK-C01 产物；**未重新解析任何 C8 JSON，未重扫 C1–C10，未运行 `audit_c01.py`**。

## 1. 输入与原目录不变证据

- 输入文件 22 个，全部位于 `diagnostics\TASK-C01\20260924T175553+08`；逐个路径/字节/SHA256 与原 manifest 对应项见 `input_manifest.json`。
- 输入与原 manifest 不一致的数量：**1**。
- 原 C01 目录：比对 46 个文件，hash 不一致 0 个，缺失 0 个，新增 0 个，`unchanged=True`。
- 是否读取过任何 C1–C10 原始文件：**False**（`guard_read()` 记录的 24 次读取全部在 C01 目录内）。
- `solution/src/evolution_audit.py` 当前 SHA256 = `8204d5b140c8fd70a2b40bb6611eb5a977e8d8dfce639b26e99baf213b2d6453`，与冻结 run 登记值完全一致。

## 2. 三张 corrected 表与 schema

| 表 | 行数 | 说明 |
|---|---:|---|
| `c8_directory_aggregate_corrected.csv` | 1863 | 每目录一行，文件总数/成功/失败、有效与缺失 group score、损坏传播字段 |
| `c8_model_task_aggregate_corrected.csv` | 11160 | 模型×任务，补目录覆盖并重定义 `n_missing_results` |
| `c8_model_wide_corrected.csv` | 1860 | 每模型一行，严格区分完整六任务均值与部分任务均值 |

字段语义见 `schema.md`。关键约定：`six_task_mean_complete_only` 仅在 `n_tasks_valid == 6` 时有值；`partial_task_mean` 仅在 1≤n≤5 时有值；原 skipna 行均值保留为 `legacy_partial_or_complete_mean`，仅供追溯。

## 3. 三类表的目录覆盖对照（四个损坏目录）

| directory | n_files_total | parse_success | parse_failed | has_parse_failure | has_any_parseable_file | source_parse_incomplete | n_results_valid | n_results_missing |
|---|---:|---:|---:|---|---|---|---:|---:|
| `DreadPoor_Winter_Dawn-8B-TIES` | 2 | 1 | 1 | True | True | True | 6 | 0 |
| `FINGU-AI_Chocolatine-Fusion-14B` | 1 | 0 | 1 | True | False | True | 0 | 0 |
| `Intel_neural-chat-7b-v3-3` | 1 | 0 | 1 | True | False | True | 0 | 0 |
| `L-RAGE_3_PRYMMAL-ECE-7B-SLERP-V1` | 1 | 0 | 1 | True | False | True | 0 | 0 |

- 纯损坏目录 3 个（无任何可解析文件），全部保留在 corrected 目录表中，`n_files_parse_success=0`、`n_results_valid=0`；因无法从损坏文件或目录名推断模型身份，它们不进入模型宽表。
- `DreadPoor_Winter_Dawn-8B-TIES` 有另一份可解析文件，贡献 6 个有效 group score，其 6 行模型任务全部带 `source_parse_incomplete=True`。
- 损坏文件 4 个逐文件传播校验均通过，无静默丢失（见 `repaired_checks.json` 的 `R1-C8-PROPAGATION`、`R1-C8-PURE-CORRUPT-ROW`）。

## 4. 完整/部分模型对照与均值列验证

| model_key | n_tasks_valid | six_task_complete | six_task_mean_complete_only | partial_task_mean | legacy_partial_or_complete_mean |
|---|---:|---|---|---|---|
| `HuggingFaceH4_zephyr-7b-alpha` | 2 | False | None | 0.23764376149449545 | 0.23764376149449545 |
| `HuggingFaceH4_zephyr-7b-gemma-v0.1` | 1 | False | None | 0.4620725568477695 | 0.4620725568477695 |
| `HuggingFaceTB_SmolLM2-135M` | 3 | False | None | 0.10110642629675015 | 0.10110642629675015 |
| `Lil-R_2_PRYMMAL-ECE-7B-SLERP` | 3 | False | None | 0.457249683230526 | 0.457249683230526 |
| `google_gemma-7b-it` | 1 | False | None | 0.362089914945322 | 0.362089914945322 |
| `mistralai_Mistral-7B-v0.3` | 1 | False | None | 0.4511369553896893 | 0.4511369553896893 |

- `n_tasks_valid` 分布：`{'1': 3, '2': 1, '3': 2, '6': 1854}`；完整 1854 个，部分 6 个。
- `six_task_mean_complete_only` 有限值 1854 个；6 个部分模型全部为空。
- `partial_task_mean` 有限值 6 个，且仅出现在部分模型行。
- 原 `six_task_mean_c8_raw` 在 6 个部分模型上仍有数值（这正是本次修复的动因），现已改名 `legacy_partial_or_complete_mean` 并与原列逐值一致。

## 5. 原检查器恒真/硬编码项的逐项修复

| 原 check | 处置 | 新 check | 说明 |
|---|---|---|---|
| `INV-01` | REPAIRED_AND_VERIFIED | `R1-C8-FILE-TOTAL`, `R1-C8-DIR-COUNT` | the constant set-membership test is replaced by an explicit count comparison against the frozen parse log |
| `INV-02` | REPAIRED_AND_VERIFIED | `R1-C8-FILE-TOTAL`, `R1-C8-DIR-COUNT` | 1958 is now recomputed from the parse log; the work order anchor is the expected side |
| `INV-03` | REPAIRED_AND_VERIFIED | `R1-C8-FILE-STATUS` | emptiness of the status column is now tested instead of implied by row count |
| `INV-04` | REPAIRED_AND_VERIFIED | `R1-C8-CORRUPT-SET`, `R1-C8-PROPAGATION` | the failure set is now cross-checked against the corrupt-file list and traced into the corrected table |
| `ID-01` | REPAIRED_AND_VERIFIED | `R1-ID-C1-DUP` | two artifacts must agree on the repeated-model count |
| `ID-02` | REPAIRED_AND_VERIFIED | `R1-ID-C9-KEY` | three artifacts must agree that eval_name is unique and complete |
| `ID-03` | REPAIRED_AND_VERIFIED | `R1-ID-C1-DUP` | folded into the cross-artifact duplicate identity check |
| `ID-04` | REPAIRED_AND_VERIFIED | `R1-ID-MISSINGNESS` | the hard-coded PASS is replaced by a cross-artifact recomputation of the same counters |
| `ID-04b` | DOWNGRADED_NOT_VERIFIABLE | `R1-ID-NO-IMPUTE-STATEMENT` | the 'no imputation' half of ID-04 has no machine evidence and is now NOT_VERIFIABLE |
| `ID-05` | REPAIRED_AND_VERIFIED | `R1-ID-C8-FIELDS` | the constant False in the producer context is replaced by a schema scan of two C8 artifacts |
| `ID-06` | REPAIRED_AND_VERIFIED | `R1-ID-C3-FIELDS` | field list recomputed from two artifacts |
| `ID-07` | REPAIRED_AND_VERIFIED | `R1-ID-C7-FIELDS` | field list recomputed from two artifacts |
| `DATE-01` | REPAIRED_AND_VERIFIED | `R1-DATE-C1-COVERAGE` | coverage reconciled across three artifacts |
| `DATE-02` | REPAIRED_AND_VERIFIED | `R1-DATE-C3-GRANULARITY` | granularity and dtype cross-checked across two artifacts |
| `DATE-03` | REPAIRED_AND_VERIFIED | `R1-DATE-C4-COUNTS` | the always-true 'parse_fail >= 0' condition is replaced by four-way arithmetic reconciliation |
| `DATE-03b` | DOWNGRADED_NOT_VERIFIABLE | `R1-DATE-NO-IMPUTE` | the 'not imputed' half is not provable from summary tables |
| `DATE-04` | REPAIRED_AND_VERIFIED | `R1-DATE-C8-COVERAGE` | timestamp coverage agreed across two artifacts |
| `DATE-05` | PARTIALLY_REPAIRED | `R1-DATE-C2-COVERAGE` | the denominator is cross-checked; the count of publication-after-submission rows stays single-source |
| `UNIT-01` | REPAIRED_AND_VERIFIED | `R1-UNIT-BENCH-RANGE` | ranges recomputed from two artifacts |
| `UNIT-02` | REPAIRED_AND_VERIFIED | `R1-UNIT-C8-RANGE` | range recomputed from the row-level group detail |
| `UNIT-03` | SPLIT | `R1-UNIT-LABELS-PRESENT`, `R1-UNIT-LABEL-CORRECTNESS` | the hard-coded WARN is split into a verifiable presence test and a NOT_VERIFIABLE correctness statement |
| `UNIT-04` | REPAIRED_AND_VERIFIED | `R1-UNIT-LOSS` | positivity and counts recomputed from two artifacts |
| `UNIT-05` | REPAIRED_AND_VERIFIED | `R1-UNIT-C9-SENTINEL` | sentinel count corroborated by three artifacts |
| `CMP-01` | SPLIT | `R1-CMP-C5-C6-OVERLAP`, `R1-CMP-IDENTICAL-VALUES` | cardinality containment is verified; the value-identity claim is single-source and downgraded |
| `CMP-02` | REPAIRED_AND_VERIFIED | `R1-CMP-STRATA` | stratum size corroborated by a second artifact |
| `CMP-03` | REPAIRED_AND_VERIFIED | `R1-CMP-NO-BRIDGE-ARTIFACTS`, `R1-CMP-NO-BRIDGE-CODE` | the hard-coded PASS is replaced by an artifact-name/schema scan and a static source scan |
| `C8-01` | REPAIRED_AND_VERIFIED | `R1-C8-TASKKEYS` | the weak non-empty test is replaced by a set equality test |
| `C8-02` | REPAIRED_AND_VERIFIED | `R1-C8-GROUP-GRIDSET` | grid equality between two artifacts |
| `C8-03` | REPAIRED_AND_VERIFIED | `R1-C8-MT-ROWS`, `R1-C8-MT-VALID-ROWS`, `R1-C8-MT-ZERO-ROWS`, `R1-C8-MT-SUM`, `R1-C8-MT-RECOMPUTE` | all counts compared against the work-order anchors and re-derived per key |
| `C8-04` | REPAIRED_AND_VERIFIED | `R1-C8-DIR-ONE-FILE`, `R1-C8-DIR-TWO-FILE` | the multi-file count is now cross-checked against the directory counts artifact |
| `C8-05` | REPAIRED_AND_VERIFIED | `R1-C8-GROUP-KEY-MISSING` | the missing-group count is cross-checked against the zero-result rows |
| `C8-06` | REPAIRED_AND_VERIFIED | `R1-C8-NONNUMERIC` | the 'PASS if True' constant is replaced by a two-artifact reconciliation of the non-numeric counter |
| `JOIN-01` | SPLIT | `R1-JOIN-C9C1-MODELS`, `R1-JOIN-C9C1-ROWORDER` | cardinality is corroborated by two artifacts; row-order and cell equality are single-source |
| `JOIN-02` | DOWNGRADED_NOT_CHECKED | `R1-JOIN-C1C2-FLOAT`, `R1-JOIN-C1C2-ROWS` | row counts are cross-checked, but the float-equality quantities cannot be rebuilt without the raw CSVs |
| `JOIN-03` | SPLIT | `R1-JOIN-C4-ROWS`, `R1-JOIN-C4-RATE` | row count is cross-checked; the match rate is single-source |
| `JOIN-04` | SPLIT | `R1-C8-X-DIRMODEL`, `R1-JOIN-C8C1-RATE` | coverage set identity is verified inside R1; the C8-to-C1 rate is single-source |
| `JOIN-05` | REPAIRED_AND_VERIFIED | `R1-JOIN-C3-SHAPE` | shape, source vocabulary and field list recomputed from three artifacts |
| `SCOPE-01` | REPAIRED_AND_VERIFIED | `R1-SCOPE-NO-FORECAST-ARTIFACT` | the constant PASS is replaced by a scan of the complete frozen artifact list |
| `SCOPE-02` | REPAIRED_AND_VERIFIED | `R1-SCOPE-NO-PROBLEM4-ARTIFACT` | the constant PASS is replaced by an artifact-name scan plus the frozen scope declaration |
| `SCOPE-03` | REPAIRED_AND_VERIFIED | `R1-SCOPE-EVOLUTION-SHA` | the source hash is re-checked against two frozen registrations |
| `SCOPE-04` | DOWNGRADED_NOT_VERIFIABLE | `R1-SCOPE-RAW-HISTORICAL`, `R1-SCOPE-R1-NO-RAW` | the historical raw-untouched claim becomes NOT_VERIFIABLE; R1's own read-only behaviour is checked separately |

## 6. 检查器结果

- `repaired_checks.json`：共 88 项；PASS 79，WARN 0，FAIL 0，NOT_CHECKED 5，NOT_VERIFIABLE 4。
- 关键 C8 项（`key_c8_item=true`）：{'PASS': 44, 'WARN': 0, 'FAIL': 0, 'NOT_CHECKED': 0, 'NOT_VERIFIABLE': 0}，不允许出现 NOT_CHECKED / NOT_VERIFIABLE。

### FAIL

无。

### WARN

无。

### NOT_CHECKED

- `R1-JOIN-C1C2-FLOAT`：echoed as single-source evidence, never counted as PASS
- `R1-JOIN-C9C1-ROWORDER`：duplicate_audit.csv corroborates cardinality only
- `R1-JOIN-C4-RATE`：recorded as a single-source quantity, never counted as PASS
- `R1-JOIN-C8C1-RATE`：recorded as a single-source quantity, never counted as PASS
- `R1-CMP-IDENTICAL-VALUES`：the original CMP-01 asserted the equality as a PASS; R1 records it as single-source

### NOT_VERIFIABLE

- `R1-DATE-NO-IMPUTE`：kept as a recorded statement, never counted as PASS
- `R1-SCOPE-RAW-HISTORICAL`：the frozen checks.json SCOPE-04 was a hard-coded True; R1 records the historical claim as NOT_VERIFIABLE instead of manufacturing a PASS. R1's own read-only behaviour is covered separately by R1-SCOPE-R1-NO-RAW
- `R1-ID-NO-IMPUTE-STATEMENT`：replaces the hard-coded PASS of the original ID-04 second half; never counted as PASS
- `R1-UNIT-LABEL-CORRECTNESS`：replaces the hard-coded WARN of the original UNIT-03 for the label-correctness part; the numeric range part is covered by the PASS checks above

## 7. OOS-01 至 OOS-12（仅登记，本任务不裁决）

原 C01（现为 R1 前置）在 `handoff.md` 第 9 节登记了 OOS-01–OOS-12。这些方法与口径问题仍未裁决，本任务未修改其任何一项，也未据此继续建模：

| 编号 | 本 R1 可确认的相关事实 |
|---|---|
| OOS-01 | `solution/src/evolution_audit.py` 仍与冻结 run 登记的 SHA256 一致（`8204d5b140c8…`），R1 未修改、未运行该文件 |
| OOS-02 | 95 个双文件目录的取舍规则仍未裁决；corrected 表同时保留 canonical 与 legacy 两种口径分数，未新增第三种规则 |
| OOS-03 | 损坏文件仍为 4 个，均属同一同名批次；R1 未重新下载或重评 |
| OOS-04–OOS-12 | 未裁决；本次仅将可从两个以上产物复算的部分升为 PASS，单來源部分统一降为 NOT_CHECKED |

## 8. 停止声明

- 本任务未重新解析 1958 个 JSON，未重扫 C1–C10，未运行 `audit_c01.py`。
- 未修改原 TASK-C01 目录、`solution/`、`F题/`、`00`–`05` 项目文档及 Q01A/Q01B/Q01C 产物。
- 未开始 Loss–Benchmark 建模、时间预测或问题四建模。

## 9. 独立验证（verify_c01_repairs.py）

_verification results are appended by `verify_c01_repairs.py` after this file is written._

- 独立验证器：`verify_c01_repairs.py`（不导入修复模块，不调用其任何函数）
- 独立核验 39 项：PASS 39，FAIL 0，总体 `COMPLETE_PENDING_REVIEW`
- 方法：本文件自己从冻结 TASK-C01 产物重算每个期望值（parse log、损坏清单、目录计数、group score 明细、model×task 表），再与 corrected 表逐键对比；未采用任何修复函数。

| verification_id | 状态 | 声明 |
|---|---|---|
| `V-C8-01` | PASS | 1958 files = 1954 parseable + 4 failed |
| `V-C8-02` | PASS | 1863 directories; 1768 with one JSON and 95 with two |
| `V-C8-03` | PASS | directory set identical between the two frozen artifacts |
| `V-C8-04` | PASS | 4 damaged directories; 3 of them have no parseable file |
| `V-C8-05` | PASS | 11724 task slots, 11699 finite, 25 missing |
| `V-C8-06` | PASS | DreadPoor contributes 6 finite scores; the other three damaged directories contribute 0 |
| `V-CDT-01` | PASS | corrected directory table covers exactly the frozen directory set |
| `V-CDT-02` | PASS | per-directory file identity total == success + failed |
| `V-CDT-03` | PASS | sum of n_results_valid equals the independent finite recount |
| `V-CDT-04` | PASS | n_results_missing equals parseable slots minus valid results |
| `V-CDT-05` | PASS | all four corrupt files are propagated into coverage |
| `V-CDT-06` | PASS | the three pure-corrupt directories stay visible with zero coverage |
| `V-MT-01` | PASS | corrected model x task table keeps the frozen key set |
| `V-MT-02` | PASS | corrected n_valid_results equals an independent per-key recount |
| `V-MT-03` | PASS | corrected n_missing_results uses the parseable-file denominator |
| `V-MT-04` | PASS | coverage fields of every model x task row trace back to the corrected directory table |
| `V-MT-05` | PASS | the damaged directory that still has data flags all six of its rows |
| `V-MT-06` | PASS | the multi-run source columns are preserved, not re-decided |
| `V-WIDE-01` | PASS | the wide table rebuilds the six task scores from the frozen model x task table |
| `V-WIDE-02` | PASS | n_tasks_valid, complete flag, complete mean and partial mean all reproduce independently |
| `V-WIDE-03` | PASS | n_tasks_valid distribution is 1:3, 2:1, 3:2, 6:1854 |
| `V-WIDE-04` | PASS | 1854 complete models and 6 partial models |
| `V-WIDE-05` | PASS | no partial model carries a six-task mean |
| `V-WIDE-06` | PASS | partial_task_mean is populated exactly on the six partial models |
| `V-WIDE-07` | PASS | the legacy skipna column is preserved and still carries the old partial values |
| `V-WIDE-08` | PASS | no model identity was invented for a pure-corrupt directory |
| `V-NN-01` | PASS | non-numeric metric count reconciles across two frozen artifacts |
| `V-IND-01` | PASS | neither R1 script implements a constant-PASS pattern in code |
| `V-IND-02` | PASS | the verifier does not import the production repair module |
| `V-IND-03` | PASS | no PASS in the repaired checker is missing its actual/expected pair |
| `V-IND-04` | PASS | the repaired checker uses only the allowed status vocabulary |
| `V-IND-05` | PASS | no key C8 item is FAIL, NOT_CHECKED or NOT_VERIFIABLE |
| `V-SUM-01` | PASS | run_summary.json declares the same file accounting as the independent recount |
| `V-SUM-02` | PASS | run_summary.json declares the same wide-table numbers as the corrected table |
| `V-SUM-03` | PASS | the repair declares that it never read a raw attachment |
| `V-IN-01` | PASS | every declared input is inside the frozen C01 directory; every input except the manifest itself matches the hash archived in that manifest |
| `V-IND-06` | PASS | the key C8 item set is non-empty and covers the file, corruption, coverage and completeness families |
| `V-MAP-01` | PASS | every original check id has a documented repair disposition |
| `V-MAP-02` | PASS | every constant or single-source original check was either repaired or explicitly downgraded |

无失败项；完整 actual/expected/证据见 `verification.json`。

校验器本身的退出码无法写回它自己最后生成的 manifest；该码由调度程序记录并在交回材料中声明。
