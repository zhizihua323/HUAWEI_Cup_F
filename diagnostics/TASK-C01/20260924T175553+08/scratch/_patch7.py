import io, ast
p = r"diagnostics\TASK-C01\20260924T175553+08\audit_c01.py"
s = io.open(p, encoding="utf-8").read()

def rep(old, new):
    global s
    assert old in s, "NOT FOUND: " + old[:100]
    s = s.replace(old, new, 1)

# report the shared filename of the corrupt batch
rep('''    summary = {
        "task": TASK, "run_id": RUN_ID, "author": AUTHOR,''',
'''    batch_name = "results_2025-02-13T18-27-04.338360.json"
    n_batch = int(log_df.file.eq(batch_name).sum())
    n_batch_bad = int((log_df.file.eq(batch_name) & log_df.parse_status.ne("ok")).sum())
    corrupt_names = sorted(log_df.loc[log_df.parse_status.ne("ok"), "file"].unique().tolist())
    summary = {
        "task": TASK, "run_id": RUN_ID, "author": AUTHOR,
        "c8_corrupt_batch": {"filename": batch_name, "files_in_batch": n_batch,
                             "failures_in_batch": n_batch_bad,
                             "distinct_corrupt_filenames": corrupt_names},''')

# extend the handoff with the escalation block
rep('''        "- 本任务未读取、未修改并行 Q 任务的任何结果文件。", "",
    ]''',
'''        "- 本任务未读取、未修改并行 Q 任务的任何结果文件。", "",
        "## 9. 超出本任务范围、交主控裁决（仅登记，未处理）", "",
        "> 依据统一规则，以下事项不在 TASK-C01 授权范围内，本任务不修复、不改写、不据此继续建模；证据均在 `handoff.md` 与 `join_coverage.csv`、`checks.json` 中被引用。", "",
        "| 编号 | 事项 | 本任务实测证据 | 超出范围的原因 |",
        "|---|---|---|---|",
        "| OOS-01 | `solution/src/evolution_audit.py` 第 137–138 行的严格相等守卫在真实附件上会抛错，整个演化脚本无法跑通 | `join_coverage.csv` 行 `C1_vs_C2_exact_dataframe_equality`（`DataFrame.equals`=False）与 `C1_vs_C2_float_cell_diff`（515 个数值单元差异，最大 3.55e-15） | 修改该项目源码需要独立施工单；本任务被要求“不要直接覆盖它” |",
        "| OOS-02 | C8 有 95 个目录各含 2 份评测 JSON，“取文件名字典序最大者”会静默丢弃其中一次评测 | `c8_directory_file_counts.csv`、`c8_model_task_aggregate.csv` 的 `n_files_in_directory` / `legacy_selection_rule_score` | 取舍规则属于下游建模决策，本任务只提供两种口径的分数 |",
        f"| OOS-03 | C8 全库 {n_batch} 份文件同名 `{batch_name}`，其中 {n_batch_bad} 份损坏（疑似同一批下载被截断） | `c8_corrupt_files.csv`、`c8_parse_log.csv` | 是否补下/重新评测需要主控决定 |",
        "| OOS-04 | C9 用 `-1` 作参数量缺失哨兵，而 C1 同行是空值 | `unit_audit.csv`、`join_coverage.csv` 行 `C9_vs_C1_value_agreement[#Params (B)]` | 清理规则影响下游统计，需主控裁决 |",
        "| OOS-05 | C1/C2 的 `Hub License` 缺失 1753 行（38.3%），C2 的 `Epoch_AI_Publication_Date` 仅 447/4576 非空 | `missingness.csv`、`date_audit.csv` | 许可与时间口径属于问题四范围，本任务不做任何插补 |",
        "| OOS-06 | C4 `Publication date` 存在 1950 年等极早日期，且 `Last modified` 最晚到 2026-05-08（晚于 C1 榜单截止 2025-03-13） | `date_audit.csv` | C4 是活数据库快照；时间口径需主控统一 |",
        "| OOS-07 | C3 中 `0` 是否为缺失未在文件内说明（MATH_Lvl5 {c3z_math} 行、GPQA {c3z_gpqa} 行为 0） | `unit_audit.csv`、`field_audit.csv` | 缺失语义判定会影响回归，本任务不擅自归因 |",
        "| OOS-08 | C7 `training_data_TB` 单位在文件内未定义 | `unit_audit.csv` | 单位换算需原始来源或主控裁决，本任务不猜测 |",
        "| OOS-09 | C6 的 Medium 层 68 行没有 `D_tokens_B`，无法支持 N–D–Loss 联合口径 | `c5_c6_comparability_audit.csv`、`join_coverage.csv` | Loss–Benchmark 桥接属于后续施工单 |",
        "| OOS-10 | C8 `results` 里存在空的指标名 `''`（`leaderboard` 组内 2 处） | `c8_task_inventory.csv` | 是否清理需主控决定 |",
        "| OOS-11 | C4 与 C1 的精确归一化名称匹配率仅 2.95% | `join_coverage.csv` 行 `C4_vs_C1_exact_normalised_name_match` | 是否引入模糊/别名映射属于身份消歧决策，本任务不做 |",
        "| OOS-12 | C4 `Parameters` 最大 1.739e14（超过 1e14 预期上界 1 行），`Training dataset size (total)` 的单位随行不同 | `unit_audit.csv` | 异常值与单位混合的处置需主控裁决 |", "",
        "## 10. 停止声明", "",
        "- 本任务到此停止，不进入 Loss–Benchmark 建模，不做问题四预测，不启动下一项任务。",
        "- 未修改 `00_PROJECT_BRIEF.md`、`01_PROJECT_STATUS.md`、`02_DECISIONS.md`、`03_DATA_CATALOG.md`、`04_TASK_QUEUE.md`、`05_REVIEW_LOG.md`。",
        "- 未修改 `solution/`、`F题/real_attachments/`、其他 `diagnostics/TASK-*` 目录中的任何文件。",
        "- 全部结论均可回溯到本目录已落盘文件（见 `output_manifest.json` 的 `sha256`）。", "",
    ]'''.replace("{c3z_math}", "{int((ctx['frames']['C3'].MATH_Lvl5 == 0).sum())}")
   .replace("{c3z_gpqa}", "{int((ctx['frames']['C3'].GPQA == 0).sum())}"))
# the block above is a plain string, so prefix it as an f-string by marking the two lines
rep('"| OOS-07 | C3 中 `0` 是否为缺失未在文件内说明（MATH_Lvl5 {int((ctx[\'frames\'][\'C3\'].MATH_Lvl5 == 0).sum())} 行、GPQA {int((ctx[\'frames\'][\'C3\'].GPQA == 0).sum())} 行为 0） | `unit_audit.csv`、`field_audit.csv` | 缺失语义判定会影响回归，本任务不擅自归因 |",',
    'f"| OOS-07 | C3 中 `0` 是否为缺失未在文件内说明（MATH_Lvl5 {int((ctx[\'frames\'][\'C3\'].MATH_Lvl5 == 0).sum())} 行、GPQA {int((ctx[\'frames\'][\'C3\'].GPQA == 0).sum())} 行为 0） | `unit_audit.csv`、`field_audit.csv` | 缺失语义判定会影响回归，本任务不擅自归因 |",')

io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AST OK, chars", len(s))
