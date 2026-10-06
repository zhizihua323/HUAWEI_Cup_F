# TASK-C01 交接：C1-C10 数据审计与 C8 基础聚合

- run_id：`20260924T175553+08`；开始 `2026-09-24T18:08:44.844880+08:00`；结束 `2026-09-24T18:09:44.310296+08:00`；用时 59.5 秒。
- 执行代码：`diagnostics/TASK-C01/20260924T175553+08/audit_c01.py`；运行日志：`run_console.log`；退出码：`exit_code.txt`。
- 所有数字均来自本次实际运行；未对原始附件做任何写入。
- 明确未做：未来 12/24 个月预测、Loss–Benchmark 最终桥接模型、问题四最终统计模型的选择、对并行 Q 任务结果的读写。
- 静态审查目标 `solution/src/evolution_audit.py` 未被导入、未被运行、未被修改；运行前后 SHA256 一致：`8204d5b140c8fd70a2b40bb6611eb5a977e8d8dfce639b26e99baf213b2d6453`。

## 1. 数据清单与规模

| 数据集 | 行/文件数 | 列数 | 主键候选 | 结论 |
|---|---:|---:|---|---|
| C1 leaderboard_cleaned | 4576 | 12 | Model 重复 79 行 | 无单列主键，需复合键 |
| C2 leaderboard_enhanced | 4576 | 15 | 同上 | C1 列 + Epoch_AI_* 元数据列 |
| C3 leaderboard_extended_timeseries | 4599 | 11 | Model+Year 仍重复 79 行 | 混合来源，不能当同口径面板 |
| C4 epoch_all_ai_models | 3523 | 57 | Model 重复 5 行 | 元数据快照 |
| C5 loss_benchmark_bridge | 43 | 13 | Model 唯一 | 43 行全部出现在 C6 |
| C6 loss_benchmark_bridge_expanded | 75 | 13 | Model 唯一 | C5 的超集 |
| C7 model_architecture_metadata | 45 | 7 | model_name 唯一 | 仅架构字段 |
| C8 detailed_results | 1958 JSON / 1863 目录 | - | (目录, 文件) | 见第 3 节 |
| C9 data/*.parquet | 4576 | 36 | eval_name 唯一 | 榜单镜像，非独立评估 |
| C10 pythia*_eval_details/README.md | 7 | - | - | 仅文档 |

## 2. 数据性质（目录标签 vs 本轮实测）

| 数据集 | 说明文件/目录标签 | 本轮实测要点 |
|---|---|---|
| C1 | observed | 榜单已归一化分数；`Average ⬆️` 与六项均值最大差 1.42109e-14；提交日期 2024-06-08–2025-03-13 |
| C2 | observed_plus_metadata_matching | 追加 Epoch_AI 三列；发布日期非空 447/4576，其中 21 行晚于提交日期 |
| C3 | mixed | 4573 行为 Open LLM Leaderboard，26 行为 Historical；仅 Year 粒度；六项中 0 值分别为 MATH 152、GPQA 264，0 是否代表缺失未在文件内说明 |
| C4 | reported_metadata | 3523 行快照；Parameters 缺失 1226；Open model weights? 为文本列缺失 870；`Last modified` 为记录更新时间 |
| C5/C6 | mixed_comparability | 见第 4 节；Loss_Source 混入 training loss / validation loss / model card 三类来源 |
| C7 | metadata | 45 个模型，仅层数/头数/维度/词表/上下文/训练数据 |
| C8 | observed_evaluation | 真实 evaluate 结果 JSON，含逐子任务汇总；不含逐题作答记录 |
| C9 | observed_evaluation | 与 C1 逐行同名同序，但另有 Raw 原始比例列；不是独立评测批次 |
| C10 | documentation_only | 7 份 README，无数据表 |

> 重要：C5/C6 的 `Val_Loss` 来自不同技术报告与不同验证集，混合来源不得当作同口径直接观测；本轮只按 `Loss_Comparability` 分层做描述统计。

## 3. C8 解析与聚合

- 枚举 JSON 1958 个（1863 个模型目录，95 个目录含 2 个 JSON）。
- 成功解析 **1954** 个，失败 **4** 个；失败全部记入 `c8_parse_log.csv` 与 `c8_corrupt_files.csv`，未静默跳过。
- 其中文件名尾部不含闭合花括号或错误位置在文件末端 95% 之后的计为“疑似截断”：4 个。

| 目录 | 文件 | 状态 | 错误 | 字节 |
|---|---|---|---|---:|
| DreadPoor_Winter_Dawn-8B-TIES | results_2025-02-13T18-27-04.338360.json | json_decode_error | Unterminated string starting at: line 1453 column 22 (char 65388) | 65536 |
| FINGU-AI_Chocolatine-Fusion-14B | results_2025-02-13T18-27-04.338360.json | json_decode_error | Unterminated string starting at: line 1162 column 22 (char 48159) | 49152 |
| Intel_neural-chat-7b-v3-3 | results_2025-02-13T18-27-04.338360.json | json_decode_error | Unterminated string starting at: line 1194 column 11 (char 49140) | 49152 |
| L-RAGE_3_PRYMMAL-ECE-7B-SLERP-V1 | results_2025-02-13T18-27-04.338360.json | json_decode_error | Expecting property name enclosed in double quotes: line 1090 column 4 (char 45805) | 45805 |

- 任务键（`results` 下）共 **45** 个；其中 group 级 7 个，其余为叶子子任务。
- JSON 内 `model_name` 字段去重 **1861** 个（原样字符串，未做别名合并）；
  目录名去重 1863 个；`c8_model_wide_canonical.csv` 中 目录×解析模型名 组合 1860 行。
- 逐模型×任务聚合表 `c8_model_task_aggregate.csv`：11160 行（模型目录×6 组任务），其中有效结果数 ≥1 的 11135 行；
  另一张宽表 `c8_model_wide_canonical.csv` 为每模型一行（1860 行），列含六个 group 分数与各自有效结果数。
- `n_valid_results` 为该模型该任务在全部评测文件中的有限分数个数；同一模型存在多次评测时保留全部，并单列 canonical（按 `date` 字段最大者，同值取文件名最大者）。
- 注意：源码 `evolution_audit.py` 的规则是“每目录取文件名字典序最大的可解析 JSON”，本聚合表在 `legacy_selection_rule_score` 列中同时给出该规则会取到的分数，便于核对差异（95 个目录受影响）。

## 4. C5/C6 分层可比性（仅描述统计）

- C5 43 行、C6 75 行；按 Model 合并 43 行，C5 模型全部包含于 C6。
- 合并行上 `Val_Loss`/`LB_*`/`Loss_Source`/`Loss_Comparability` 逐列相同值个数：`{"N_params_B": 43, "D_tokens_B": 43, "Val_Loss": 43, "LB_Average": 43, "LB_IFEval": 43, "LB_BBH": 43, "LB_MATH": 43, "LB_GPQA": 43, "LB_MUSR": 43, "LB_MMLU_PRO": 43, "Loss_Source": 43, "Loss_Comparability": 43}`（分母 43）。
- C6 分层：High（同模型同验证集）7 行，Medium（不同验证集近似）68 行。
- `D_tokens_B` 仅 High 层有值（C6 非空 7 行），Medium 层 68 行缺失 → 训练数据量不可由 C6 补推。
- 本轮不拟合桥接模型、不做 LOOCV、不给出 Loss→Benchmark 映射，也不做任何外推。

## 5. 连接率与口径核查

- C9 vs C1：行数 4576 vs 4576；集合相等 **True**；逐行同序 **True**。二者不应当作两次独立观测。
- C1 vs C2：列名一致，但 `DataFrame.equals` = **False**；严格不等价的数值单元 515 个，最大绝对差 3.553e-15（浮点往返级）。
  这说明源码 `evolution_audit.py` 第 137–138 行的 `if not c1.equals(c2[c1.columns]): raise` 在真实附件上会**直接抛错**，是静态审查发现的阻断性缺陷。
- C4 与 C1 精确归一化名称匹配率：2.9520%（只做精确匹配，不做模糊匹配、不补造身份）。
- C8 与 C1 精确名称匹配率：99.8976%；C3 与 C1 名称匹配率：99.4347%。
- C9 参数列使用 `-1` 作缺失哨兵（3 行），而 C1 同行是空值 → 直接对 C9 参数取均值会把 -1 当真值。

## 6. 源码静态审查要点（未运行、未修改）

| # | 位置 | 观察 | 风险 |
|---|---|---|---|
| S1 | 第 137–138 行 | `c1.equals(c2[c1.columns])` 实测为 False（515 个单元浮点差异） | 阻断：脚本会在该断言处抛错，C8 及后续步骤无法执行 |
| S2 | 第 296–304 行 | 叶子指标先 `np.isfinite(numeric(val))` 判断再 `continue` | 非数值指标被静默丢弃；本轮 `c8_task_inventory.csv` 改为显式计数 |
| S3 | 第 256–261 行 | “JSON 无 results 映射” 与 “JSON 解析失败” 共用同一 `parseable=False` | 两类失败语义被合并；本轮分列 `json_decode_error` / `schema_error_*` |
| S4 | 第 264、353 行 | 每目录只取文件名字典序最大的可解析 JSON | 95 个目录含 2 次评测，另一次被丢弃且未在摘要中提示 |
| S5 | 第 383–412 行 | 含按提交日期的前 80%/后 20% 回归与外推预测路径 | 超出 TASK-C01 授权；本轮不执行、不复制该逻辑 |
| S6 | 第 428–480 行 | 对 C6 做 LOMO 线性桥接与相关分析 | 属于 Loss–Benchmark 桥接建模；本轮仅做分层描述统计 |
| S7 | 第 149–151 行 | 断言 C9 parquet 与 C1 的对齐关系 | 实测成立（集合与位置均一致），但断言失败即中断，缺乏降级路径 |
| S8 | 第 33–36、79–89 行 | 许可白名单/自定义清单硬编码，且把 `nan`/空串归入 unresolved | 白名单是操作口径而非法律判断；本轮沿用“未决即未决”的处理，不补猜许可证 |

## 7. 交付物

| 文件 | 内容 |
|---|---|
| `data_inventory.csv` | C1–C10 路径、文件数、字节、行数、列数、SHA256 |
| `field_audit.csv` | 每个数据集每个字段的 dtype/缺失/唯一值/数值范围/角色 |
| `missingness.csv` | 缺失与空串/哨兵计数 |
| `duplicate_audit.csv` | 全行重复、主键候选重复、模型名重复、字段内重复 |
| `model_identity_audit.csv` | 模型名/族/类型/许可证/参数量/日期字段可用性 |
| `date_audit.csv` | 各日期字段解析率、范围、粒度与跨表时序 |
| `unit_audit.csv` | 单位、取值范围、越界与哨兵 |
| `c5_c6_comparability_audit.csv` | C5/C6 分层描述统计 |
| `c8_parse_log.csv` | 1958 个 JSON 的逐文件解析日志（含 SHA256、错误类型与位置） |
| `c8_corrupt_files.csv` | 失败文件明细（含文件尾部字节） |
| `c8_task_inventory.csv` | 任务键清单、指标、样本量形态、非数值计数 |
| `c8_model_task_aggregate.csv` | 逐模型×任务聚合（有效结果数、canonical、均值/极差） |
| `c8_model_wide_canonical.csv` | 每模型一行的宽表（问题四可用输入之一） |
| `c8_group_scores_all_runs.csv` / `c8_leaf_metrics.csv.gz` | 全部评测运行的 group / 叶子指标明细 |
| `join_coverage.csv` | C9-C1、C1-C2、C3-C1、C4-C1、C8-C1 连接率与逐列一致性 |
| `checks.json` | 33 PASS / 6 WARN / 0 FAIL 的结构化核验记录 |
| `run_summary.json` | 运行环境、范围、关键计数、源码哈希守卫 |
| `output_manifest.json` | 本目录全部产物的字节与 SHA256 |

## 8. 尚未解决 / 不得越过

- C4 的训练数据量列单位未在表内编码（`Dataset size notes` 文本各异），本任务不换算、不合并。
- C7 的 `training_data_TB` 单位未在文件内定义，本任务不猜测。
- C3 中 `0` 是否为缺失未在文件内说明，本任务不当作真实 0 分使用。
- C8 目录内 95 次重复评测（同一目录第二份 JSON）的取舍规则属于下游建模决策，本任务只提供事实与两种口径的分数。
- 问题四的统计模型、12/24 个月前沿预测与 Loss–Benchmark 桥接均不在本任务范围内，需另行施工单。
- 本任务未读取、未修改并行 Q 任务的任何结果文件。

## 9. 超出本任务范围、交主控裁决（仅登记，未处理）

> 依据统一规则，以下事项不在 TASK-C01 授权范围内，本任务不修复、不改写、不据此继续建模；证据均在 `handoff.md` 与 `join_coverage.csv`、`checks.json` 中被引用。

| 编号 | 事项 | 本任务实测证据 | 超出范围的原因 |
|---|---|---|---|
| OOS-01 | `solution/src/evolution_audit.py` 第 137–138 行的严格相等守卫在真实附件上会抛错，整个演化脚本无法跑通 | `join_coverage.csv` 行 `C1_vs_C2_exact_dataframe_equality`（`DataFrame.equals`=False）与 `C1_vs_C2_float_cell_diff`（515 个数值单元差异，最大 3.55e-15） | 修改该项目源码需要独立施工单；本任务被要求“不要直接覆盖它” |
| OOS-02 | C8 有 95 个目录各含 2 份评测 JSON，“取文件名字典序最大者”会静默丢弃其中一次评测 | `c8_directory_file_counts.csv`、`c8_model_task_aggregate.csv` 的 `n_files_in_directory` / `legacy_selection_rule_score` | 取舍规则属于下游建模决策，本任务只提供两种口径的分数 |
| OOS-03 | C8 全库 490 份 JSON 同名 `results_2025-02-13T18-27-04.338360.json`（同一 2025-02-13 评测批次），其中 4 份损坏；损坏文件大小恰为 64/48 KiB 且解析错误位置在文件末尾 97.9%–100% 处，是下载被截断的直接证据 | `c8_corrupt_files.csv`（含文件尾部字节）、`c8_parse_log.csv`（`error_at_eof_fraction`、`file_ends_with_closing_brace`） | 是否补下/重新评测需要主控决定 |
| OOS-04 | C9 用 `-1` 作参数量缺失哨兵，而 C1 同行是空值 | `unit_audit.csv`、`join_coverage.csv` 行 `C9_vs_C1_value_agreement[#Params (B)]` | 清理规则影响下游统计，需主控裁决 |
| OOS-05 | C1/C2 的 `Hub License` 缺失 1753 行（38.3%），C2 的 `Epoch_AI_Publication_Date` 仅 447/4576 非空 | `missingness.csv`、`date_audit.csv` | 许可与时间口径属于问题四范围，本任务不做任何插补 |
| OOS-06 | C4 `Publication date` 存在 1950 年等极早日期，且 `Last modified` 最晚到 2026-05-08（晚于 C1 榜单截止 2025-03-13） | `date_audit.csv` | C4 是活数据库快照；时间口径需主控统一 |
| OOS-07 | C3 中 `0` 是否为缺失未在文件内说明（MATH_Lvl5 152 行、GPQA 264 行为 0） | `unit_audit.csv`、`field_audit.csv` | 缺失语义判定会影响回归，本任务不擅自归因 |
| OOS-08 | C7 `training_data_TB` 单位在文件内未定义 | `unit_audit.csv` | 单位换算需原始来源或主控裁决，本任务不猜测 |
| OOS-09 | C6 的 Medium 层 68 行没有 `D_tokens_B`，无法支持 N–D–Loss 联合口径 | `c5_c6_comparability_audit.csv`、`join_coverage.csv` | Loss–Benchmark 桥接属于后续施工单 |
| OOS-10 | C8 `results` 里存在空的指标名 `''`（`leaderboard` 组内 2 处） | `c8_task_inventory.csv` | 是否清理需主控决定 |
| OOS-11 | C4 与 C1 的精确归一化名称匹配率仅 2.95% | `join_coverage.csv` 行 `C4_vs_C1_exact_normalised_name_match` | 是否引入模糊/别名映射属于身份消歧决策，本任务不做 |
| OOS-12 | C4 `Parameters` 最大 1.739e14（超过 1e14 预期上界 1 行），`Training dataset size (total)` 的单位随行不同 | `unit_audit.csv` | 异常值与单位混合的处置需主控裁决 |

## 10. 停止声明

- 本任务到此停止，不进入 Loss–Benchmark 建模，不做问题四预测，不启动下一项任务。
- 未修改 `00_PROJECT_BRIEF.md`、`01_PROJECT_STATUS.md`、`02_DECISIONS.md`、`03_DATA_CATALOG.md`、`04_TASK_QUEUE.md`、`05_REVIEW_LOG.md`。
- 未修改 `solution/`、`F题/real_attachments/`、其他 `diagnostics/TASK-*` 目录中的任何文件。
- 全部结论均可回溯到本目录已落盘文件（见 `output_manifest.json` 的 `sha256`）。

