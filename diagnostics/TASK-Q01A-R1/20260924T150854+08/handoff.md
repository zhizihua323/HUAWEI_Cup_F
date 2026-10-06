# TASK-Q01A-R1 精准小修交回说明

- 状态：COMPLETED_WITH_NOT_VERIFIABLE_ITEMS；run目录：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-Q01A-R1\20260924T150854+08`。本次是补证/小修，不改变原运行的 PARTIAL 与退出码 2。
- 边界：未读取、解压或哈希 A1-A3 压缩输入；未运行原 diagnose_missingness.py；未修改 R 目录与首次失败目录；未计算数值 Q；未实施任何缺失处理策略。

## 三项实质错误的修正结果
- 原始层记录数：nan_rows/posinf_rows/neginf_rows 改为异常物理记录数（事件按 file_id+source_line+field 去重）。A1 professionalism=5、A1 reasoning=13、A3_github professionalism=1；元素数保持 30/78/6（合计 114）；异常并集 19 条、两字段交集 0。
- raw_invalid 掩码：由 invalid_values 的 raw 事件重建并写回 row_masks_corrected.csv.gz，仅 19 条物理行的 raw_invalid_bits/raw_invalid_count 变化，其余列逐行比对无差异；raw 层 patterns 49 行、pairwise 629 行随之更新，提取/归一化/Q 掩码层完全未变。
- 分歧分母：range 与 ddof=0 组间 std 改为“至少 1 个有效组即可定义”，共修正 60 行（40 行 mean/std 有效 n + 20 行缺失 range 的 False 计数）。all_unique：range n=261086、std n=261086、False 计数=0、Q_mean n=261067、Q_std n=261067（ddof=1 方差除数 261066，单独成列）。19 条缺失案例仍有 2 个有效组，不再被判为 range/std 缺失。

## 独立验收（与修复脚本不同实现路径）
- verify_repairs.py 用 pandas 重算分母、用事件表独立重建原始掩码、按特征名映射复核 25/11 掩码，并逐文件核对 source_line 唯一性与 1..n 覆盖；结果见 repair_checks.json。
- C12 扩展重叠行数：A2=1419、A3=10000（只取 domain=ALL 行；域明细求和仅在核对中用于证明早期重复计数，不与 ALL 相加）。
- 旧值比对与历史结论登记见 postrun_reconciliation_reviewed.json（原 7 项逐项 + 新发现 3 项）。

## 未解决或不可验证
- C08c 历史全目录 mtime：无运行前快照，标注 NOT_VERIFIABLE，不伪造 PASS。
- 原 R 目录的 7 项 FAIL、PARTIAL、退出码 2、原 checks.json/run_summary.json/handoff.md 原样保留，本次修正以新目录提供补充证据，另行验收。
- 首次失败说明更正：the aborted attempt completed the compressed-byte hashing precondition (stage=precondition hashed_inputs=3) and then failed inside build_input_manifest because RUN_ID was undefined, i.e. before any decompression scan; it contributes no diagnostic rows

## 机器可审查入口
- raw_field_counts_corrected.csv；raw_mask_corrections.csv；row_masks_corrected.csv.gz
- missing_patterns_corrected.csv；missing_pairwise_corrected.csv；summary_denominators_corrected.csv
- missing_concentration.csv；changes.csv；repair_checks.json；postrun_reconciliation_reviewed.json；run_summary.json；output_manifest.json；input_manifest.json；environment.json；repair.log；verify.log

## 交回主控复审后另行裁决的问题（本单不做策略选择）
1. 11 个主Q特征出现非有限值时的处理原则与最低证据标准是什么？
2. 是否按域与验证角色分别处理，可接受差异如何界定？
3. 覆盖率与域间可比性的权衡标准是什么？
4. 下游汇总是否必须显式披露有效 n 与非有限占比，需要何种验证？
5. 扩展重叠副本与 A1 中同键同异常状态的记录是否视为同一证据、如何计入分母披露？
6. 现有证据是否足够，是否需要补充诊断？