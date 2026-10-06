# TASK-Q01C-R1正式施工单：恢复机制与日志精准小修

状态：**施工单已编制，未执行。只有收到单独执行指令后才能开工。**

本施工单与`TASK-C01-R1`相互独立，可由两个执行AI并行执行。执行本任务时不得读取、写入或依赖`diagnostics/TASK-C01-R1/`中的任何产物。

## 【任务编号】

TASK-Q01C-R1。

前置任务：TASK-Q01C科学计算已形成正式成功run，但主控最终审查结论为“小修”。主Q、缺失传播、显式分母和敏感性分析均已通过；本任务只修复跨进程恢复、检查点封闭和日志证据。

## 【任务名称】

TASK-Q01C恢复机制与日志精准小修。

## 【任务性质】

纯工程恢复/日志小修。不得重新计算、改变或重新解释任何质量科学结果。

## 【任务背景】

TASK-Q01C正式科学run为：

`solution/outputs/quality_q01c/20260924T215718+08/`

主控审查已经确认该run的质量数值、敏感性结果、代码快照、56项输出manifest和受保护文件证据可信，但发现以下工程缺口：

1. `--resume`、`--stage`和`--probe-resume`虽被解析，但没有真实参与主流程；只要run目录存在，程序即无条件退出。
2. 三次resume probe发生在同一进程、紧接检查点写入之后，只能证明即时重读，不能证明进程中断后的跨进程恢复。
3. S20/S30/S40的hash-linked `COMPLETE`标记被同名阶段完成标记覆盖，不能继续通过现有检查点校验函数。
4. `environment.json.commands`为空，正式主命令没有落盘。
5. `stage_status.jsonl`缺少S20、S60的完整结束事件，`run_summary.stage_seconds`缺少S01、S60。
6. 人工插补来源隔离测试覆盖holdout扰动，但没有显式构造extension角色扰动。

这些问题不否定现有科学结果，但在修复和实证前，Q01C/T02恢复任务不能关闭。

## 【目的】

1. 实现可对“已有但未完成”的run目录进行真实跨进程恢复的入口。
2. 使`--resume`、`--stage`和`--probe-resume`具有清晰、可测试、可记录的实际行为。
3. 保证阶段完成标记与检查点hash链不会互相覆盖。
4. 补齐真实主命令、阶段事件、耗时和退出状态记录。
5. 用小型合成fixture完成“两进程中断→恢复”实证，不接触A1–A3。
6. 补齐extension角色插补来源隔离人工测试。

## 【为什么现在必须先做】

后续任务需要依赖质量流水线的可恢复性和审计日志。若在没有真实跨进程恢复证据的情况下关闭T02，下一次中断仍可能迫使全量重扫，也无法判断哪些检查点可安全复用。

## 【输入文件】

### 只读方法与审查依据

- `tasks/TASK-Q01C_质量缺失策略实施与流水线恢复.md`
- `tasks/TASK-Q01B_质量缺失处理策略裁决.md`
- `02_DECISIONS.md`
- TASK-Q01C正式run中的：
  - `run_summary.json`
  - `checks.json`
  - `verification.json`
  - `checkpoint_manifest.json`
  - `stage_status.jsonl`
  - `environment.json`
  - `run_config.json`
  - `output_manifest.json`
  - `code_snapshot/`

### 允许修改的当前源码

- `solution/src/quality_q01c.py`
- `solution/src/quality_q01c_selftest.py`
- `solution/src/quality_q01c_verify.py`，仅当恢复/日志检查确需调整时
- `solution/tests/test_quality_q01c.py`
- 可在`solution/tests/`新建名称含`q01c_r1`的合成fixture、两进程测试或测试驱动脚本

不得修改正式run内的源码快照。当前源码的修正必须在新的R1目录中另存快照和前后哈希。

## 【绝对禁止读取的数据】

下列三个文件不得被打开、读取、扫描、解压、哈希或stat后用于版本判定：

- A1：`F题/real_attachments/A_data_value/slimpajama_quality_signal_sample.jsonl.xz`
- A2：`F题/real_attachments/A_data_value/slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz`
- A3：`F题/real_attachments/A_data_value/slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz`

验证resume只能使用小型合成fixture。不得以“只做字节哈希”为由读取A1–A3。

## 【禁止修改的文件和目录】

- `solution/outputs/quality_q01c/20260924T215718+08/`全部文件。
- 该目录之前的7个失败、未完成或候选run。
- `solution/outputs/quality/`历史产物。
- TASK-Q01A、Q01A-R1及Q01B证据。
- 全部`F题/`原始材料。
- `00_PROJECT_BRIEF.md`至`05_REVIEW_LOG.md`。
- 配比、缩放、演化、优化和论文模块源码及产物。
- `diagnostics/TASK-C01/`和任何`TASK-C01-R1`目录。

## 【允许修改范围】

只允许：

1. 修复Q01C的CLI流程控制、检查点协议、恢复入口和日志记录。
2. 增加不读取真实数据的合成fixture与测试。
3. 在新的R1证据目录中写入测试、日志、检查和交回材料。

不得改变11个主Q特征、三组结构、归一化、缺失策略、插补门槛、域/角色定义或任何科学汇总函数的数值语义。若工程修复不可避免地触及科学函数，必须停止并交主控裁决。

## 【R1输出目录】

正式R1目录固定为：

`diagnostics/TASK-Q01C-R1/<run_id>/`

`run_id`使用实际启动时间和唯一后缀。目录存在时必须失败退出，禁止覆盖。

合成中断run必须放在该R1目录的子目录，例如：

- `synthetic_fixture/`
- `interruption_run/`
- `code_snapshot/`

不得写入正式科学run。

## 【必须实现的CLI契约】

### `--resume`

- 只有显式给出`--resume`时，才允许打开已有且未完成的run目录。
- 必须拒绝恢复已经finalize且manifest封闭的正式成功run。
- 必须先校验输入fixture、配置、源码/恢复协议版本、检查点metadata、数据文件hash和完成标记，再决定复用。
- 已完成且校验通过的检查点不得重算；校验失败必须停止，不得静默重扫或降级。
- 正在执行但没有合法完成标记的阶段必须从该阶段重新开始。

### `--stage`

- 必须真实决定本次进程执行或停止的阶段范围。
- 不得只解析参数后忽略。
- 阶段依赖不足时必须失败并写明缺少的前置检查点。
- 合成两进程试验中必须实际使用该参数或等价的显式阶段选择，且日志能证明其作用。

### `--probe-resume`

- 必须执行只读的恢复资格检查，或与`--resume`组合后记录检查点复用判定。
- 必须记录被检查阶段、校验项、复用/拒绝原因及扫描次数。
- 不得在同一进程刚写完检查点后立即调用并把结果冒充跨进程恢复。

## 【检查点协议修复要求】

1. 数据检查点完成标记和阶段完成标记必须使用不同文件名或兼容的统一schema，不能相互覆盖。
2. 每个可复用检查点至少绑定：
   - stage
   - fixture/input SHA256
   - config SHA256
   - code或checkpoint-protocol fingerprint
   - payload SHA256
   - 行数/记录数
   - 完成时间
3. `checkpoint_is_valid()`或等价验证器必须能验证S20/S30/S40产生的标记；不得因为字段被覆盖而必然失败。
4. 原子写入顺序必须是：payload → metadata → 最终完成标记。
5. 不完整临时文件、缺失marker、hash不符、配置或代码版本不符时不得复用。

## 【日志修复要求】

1. 新R1运行必须记录真实执行命令，包括：
   - R1主命令
   - 第一合成进程命令
   - 第二恢复进程命令
   - 独立验证命令
2. 命令须由实际`sys.argv`和解释器路径生成，不得事后手填；敏感参数如存在须脱敏。
3. `stage_status.jsonl`对每个实际阶段必须存在`start`以及`complete`或`fail/interrupted`终态。
4. 被外部终止的第一进程无法自行写fail时，监督进程必须写独立的终止证据，包含PID、终止时间、退出码和当时最后一个合法checkpoint。
5. `run_summary.stage_seconds`必须覆盖全部实际执行阶段；未执行阶段必须显式记录`SKIPPED`及原因，不得直接遗漏。
6. 不允许伪造TASK-Q01C历史主命令。原正式run命令缺失继续登记为历史限制。
7. 最终manifest生成前关闭所有被纳入hash的日志；生成后不得继续追加。

## 【合成跨进程中断→恢复测试】

必须使用不含任何A1–A3数据的小型fixture，并通过实际操作系统子进程验证。

### 第一进程

1. 使用真实Q01C恢复入口和合成fixture启动进程P1。
2. P1至少生成一个合法、hash-linked、可复用的扫描检查点。
3. 测试监督器在确认完成标记已落盘后人为终止P1，或使用等价的外部中断机制。
4. 保存P1命令、PID、stdout/stderr、stage log、退出码、终止时间及检查点终止前hash。

### 第二进程

1. 使用不同PID的独立进程P2，对同一合成run目录执行`--resume`。
2. P2必须校验并复用P1的完成检查点。
3. P2对已经完成的模拟扫描阶段新增扫描次数必须为0；累计扫描计数不得增加。
4. P2应完成后续fixture阶段并正常finalize。
5. 保存P2命令、PID、stdout/stderr、stage log、退出码及检查点恢复后hash。

### 必须证明

- P1和P2为两个不同操作系统进程。
- 使用同一run目录。
- P1检查点在P2前已经存在且合法。
- P2复用前后payload和完成标记hash不变。
- P2已完成阶段扫描次数为0。
- P2没有读取任何真实A1–A3路径。
- 静态代码审查或同进程probe不能替代以上证据。

## 【extension插补来源隔离人工测试】

必须构造至少含以下角色的合成行：

- A1 calibration
- A1 holdout
- extension overlap
- extension new

固定calibration数据后，分别把holdout、extension overlap和extension new中的目标特征改成极端值。每次修改后都必须证明：

- calibration对应域/特征的候选n、有效n、覆盖率、唯一值数和中位数完全不变；
- 插补参数没有从非calibration角色取值；
- 门槛失败时仍硬停止且没有fallback。

该测试只允许使用人工小数据，不得读取正式Parquet重新计算敏感性结果。

## 【正式科学run的只读回归证据】

R1只允许把正式run作为不可变回归基线：

- 核对正式run的`output_manifest.json`和登记的56项hash；
- 核对正式run状态、20/20终验和已登记关键计数；
- 核对正式run目录在R1前后没有变化。

不得加载正式行级Parquet重新计算主Q、敏感性Q、分母或域汇总。

## 【必须输出的文件】

R1目录至少包含：

- `handoff.md`
- `run_summary.json`
- `checks.json`
- `verification.json`
- `changes.csv`
- `input_manifest.json`
- `environment.json`
- `command_log.json`
- `stage_status.jsonl`
- `checkpoint_manifest.json`
- `resume_evidence.json`
- `protected_artifacts_check.json`
- `extension_isolation_test.json`
- `synthetic_fixture/`，含fixture定义、输入hash和扫描计数器
- `interruption_run/process_1/`，含命令、PID、日志、退出码和终止证据
- `interruption_run/process_2/`，含命令、PID、日志、退出码和恢复证据
- `code_snapshot/`，含修改后源码、测试和SHA256清单
- `output_manifest.json`

可增加必要的机器证据，但不得用文字说明替代JSON/CSV检查。

## 【必须记录的数值】

- P1/P2 PID、开始/结束时间、退出码。
- 每个fixture阶段的start/complete/fail/interrupted事件数。
- P1终止时与P2启动时的检查点大小、行数和SHA256。
- 第一进程模拟扫描次数、第二进程对已完成阶段的新增扫描次数、累计扫描次数。
- 复用检查点数、拒绝检查点数及逐项原因。
- 每阶段实际耗时或`SKIPPED`状态。
- extension隔离测试中每个角色的行数及修改前后参数。
- 正式科学run的56项manifest匹配数和不匹配数。
- 修改前后源码SHA256。

## 【精确验收锚点】

1. 正式科学run目录仍为`solution/outputs/quality_q01c/20260924T215718+08/`，原manifest登记56项，R1前后均须56/56匹配。
2. 不产生新的真实A1/A2/A3扫描记录；对这三个文件的读取、解压、哈希次数均为0。
3. 合成恢复必须由两个不同PID完成。
4. P2对P1已完成检查点的新增模拟扫描次数必须严格等于0。
5. P1检查点在P2前后hash完全一致。
6. `--resume`、`--stage`、`--probe-resume`均至少有一项可观察行为证据，不能仅有参数解析证据。
7. 所有实际阶段均有start和唯一终态；`run_summary.stage_seconds`不得漏掉已执行阶段。
8. extension角色极端值改变后，calibration参数逐字段完全不变。
9. S20/S30/S40检查点完成标记不再被阶段完成标记覆盖，独立校验均PASS。
10. 正式科学结果和正式run内容零变化。

## 【验收标准】

只有同时满足以下条件，R1才可标记`COMPLETE_PENDING_REVIEW`：

1. 合成P1被中断、P2跨进程恢复的实证完整。
2. P2没有重新执行已完成的模拟扫描。
3. CLI三个恢复参数均真实参与流程控制。
4. 检查点hash链和阶段marker协议通过独立验证。
5. 主命令、两个子进程命令、阶段事件和耗时记录完整。
6. extension来源隔离测试全部PASS。
7. 正式成功run及之前7个run全部未变化。
8. 独立验证不得导入生产恢复模块来同时生成actual和expected。
9. 关键恢复检查为0 FAIL、0 NOT_CHECKED、0 NOT_VERIFIABLE。
10. R1 output manifest生成后全部登记文件hash一致。

## 【FAIL / NOT_VERIFIABLE规则】

### 必须FAIL

- 读取、哈希、解压或扫描A1–A3。
- 重新运行正式全量质量流水线。
- 重新计算真实主Q或真实敏感性结果。
- 修改正式成功run或之前7个run。
- P2与P1不是两个独立进程。
- P2重新执行已完成模拟扫描，或扫描计数无法证明为0。
- `--resume`仍不能打开未完成run目录。
- 检查点hash不符仍被复用。
- S20/S30/S40 marker仍被覆盖。
- extension角色变化改变calibration插补参数。
- 主命令或阶段终态在新R1中缺失。
- 为通过检查而改写既有科学锚点。

### 可记NOT_VERIFIABLE

仅限TASK-Q01C历史正式run中从未落盘、现在无法诚实补证的历史主命令。不得事后猜测或手填为PASS。

本R1新产生的跨进程恢复、命令、阶段日志、检查点和extension测试均不得记NOT_VERIFIABLE；缺证据即FAIL。

## 【停止条件】

1. 发现任何代码修改可能改变科学数值语义时立即停止，交主控裁决。
2. 任何A1–A3路径被实际打开时立即停止并标记FAIL。
3. 合成P2发生重新扫描时立即停止，不得用第三次运行掩盖。
4. 正式run或旧run任一hash变化时立即停止。
5. 关键恢复检查出现FAIL时保留证据并停止，不自动放宽验收规则。
6. 交齐R1证据后停止，不更新00–05，不启动T03或其他建模。

## 【完成后必须交回的材料】

- R1绝对路径和run_id。
- 修改文件、原因、前后SHA256和代码快照。
- P1/P2实际命令、PID、日志、退出码和中断/恢复时间线。
- 检查点复用及扫描计数证据。
- `--resume`、`--stage`、`--probe-resume`实际行为证据。
- extension来源隔离测试结果。
- 正式科学run和旧run未变化的证据。
- 全部checks、verification和output manifest复核结果。
- 明确保留的历史NOT_VERIFIABLE项。

施工单编制完成后停止。本文件本身不授权执行TASK-Q01C-R1。
