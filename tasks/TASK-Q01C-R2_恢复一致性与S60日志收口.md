# TASK-Q01C-R2正式施工单：恢复一致性与S60日志收口

状态：**施工单已编制，未执行。只有收到单独执行指令后才能开工。**

本任务是TASK-Q01C-R1最终复审后的最后一轮精准工程小修。任务范围仅限恢复资格判定一致性、中后段不可变检查点恢复、stage marker职责以及S60日志和manifest收口。不得借本任务重新计算、修改或解释任何真实质量科学结果。

## 【任务编号】

TASK-Q01C-R2。

## 【任务名称】

TASK-Q01C恢复一致性与S60日志收口。

## 【任务性质】

纯工程修复与合成fixture验证。不得改变Q计算公式、归一化、缺失处理、敏感性分析、分母口径、域/角色定义或任何科学数值语义。

## 【任务背景】

TASK-Q01C正式科学run为：

`solution/outputs/quality_q01c/20260924T215718+08/`

TASK-Q01C-R1正式run为：

`diagnostics/TASK-Q01C-R1/20260924T225550+08/`

R1已经用两个不同操作系统进程证明了S10完成后的中断恢复，并修复了checkpoint marker与stage marker文件名冲突。但最终复审发现：

1. 正常`--resume`主循环、`--stage`前置依赖检查和`--probe-resume`尚未统一使用同一套完整恢复资格判定；正常主循环仍可能只凭stage marker跳过阶段。
2. S20的stage marker仍绑定会被S30合法改写的全局`quality_features_scores.parquet`，导致已完成阶段可能被误判为未完成。
3. S30/S40恢复仍需明确从上游不可变checkpoint payload取得输入，而不是依赖可变的全局materialized output。
4. S60虽然执行并形成终态，但其耗时和执行状态未进入最终冻结的`run_summary`；R1验收器还主动将S60排除在完整性检查之外。

已通过的真实科学结果不属于本任务范围。历史正式Q01C主命令缺失继续记为`NOT_VERIFIABLE`，不得事后补造。

## 【目的】

1. 建立唯一、可审计的stage reuse validation入口，并让正常`--resume`、`--stage`前置依赖检查和`--probe-resume`共同调用。
2. 让S20、S30、S40真正依据不可变checkpoint链恢复。
3. 明确checkpoint marker与stage marker的职责边界，消除对后续会合法改写文件的错误绑定。
4. 在manifest封闭前完整记录S60状态、耗时和终态。
5. 仅用小型合成fixture证明中后段跨进程恢复、三种拒绝路径和S60日志闭环。

## 【输入文件】

### 允许读取的施工单与审查依据

- `tasks/TASK-Q01C_质量缺失策略实施与流水线恢复.md`
- `tasks/TASK-Q01C-R1_恢复机制与日志精准小修.md`
- `tasks/TASK-Q01C-R2_恢复一致性与S60日志收口.md`
- `02_DECISIONS.md`，仅用于确认既有Q方法边界，不得修改。

### 允许只读使用的正式科学run证据

仅允许读取以下目录中用于回归保护的manifest、摘要、检查与工程日志：

- `solution/outputs/quality_q01c/20260924T215718+08/output_manifest.json`
- 同目录中由该manifest登记的56项已有产物，仅用于逐项hash一致性核对。
- `run_summary.json`
- `checks.json`
- `verification.json`
- `checkpoint_manifest.json`
- `stage_status.jsonl`
- `environment.json`
- `run_config.json`
- `code_snapshot/`

不得加载该正式run的行级Parquet重新计算Q、敏感性结果、分母或域汇总。

### 允许只读使用的R1证据

- `diagnostics/TASK-Q01C-R1/20260924T225550+08/`中的全部已有文件，仅用于理解R1实现、建立保护快照和回归核验。
- 应重点参考`handoff.md`、`run_summary.json`、`checks.json`、`verification.json`、`checkpoint_manifest.json`、`resume_evidence.json`、`stage_status.jsonl`、`code_snapshot/`和`output_manifest.json`。

### 允许修改的当前源码

仅允许在确有必要时修改：

- `solution/src/quality_q01c.py`
- `solution/src/quality_q01c_selftest.py`
- `solution/src/quality_q01c_verify.py`
- `solution/tests/test_quality_q01c.py`
- 可在`solution/tests/`新建名称明确含`q01c_r2`的合成fixture、跨进程测试、拒绝路径测试或独立验收脚本。

所有修改后源码和测试必须复制到新R2目录的`code_snapshot/`并登记SHA256。不得修改任何既有run内的code snapshot。

## 【绝对禁止读取的数据】

以下三个真实文件不得被任何R2进程打开、读取、扫描、解压、hash或stat，也不得为了“版本判定”“保护检查”或“输入绑定”访问其文件系统元数据：

- A1：`F题/real_attachments/A_data_value/slimpajama_quality_signal_sample.jsonl.xz`
- A2：`F题/real_attachments/A_data_value/slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz`
- A3：`F题/real_attachments/A_data_value/slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz`

既有JSON或Markdown中出现这些路径文本，不授权解析、规范化或探测对应真实文件。全部动态验证必须使用新建的小型合成fixture。

## 【禁止修改的文件和目录】

- `solution/outputs/quality_q01c/20260924T215718+08/`全部文件。
- `diagnostics/TASK-Q01C-R1/20260924T225550+08/`全部文件。
- TASK-Q01C此前7个失败、未完成或候选run，以及其他既有Q01C run。
- `solution/outputs/quality/`历史产物。
- TASK-Q01A、TASK-Q01A-R1和TASK-Q01B证据。
- `F题/`下全部原始材料。
- `diagnostics/TASK-C01/`、`diagnostics/TASK-C01-R1/`及其全部产物。
- `solution/src/evolution_audit.py`以及C01相关源码。
- `00_PROJECT_BRIEF.md`至`05_REVIEW_LOG.md`。
- 配比、缩放、演化、优化和论文模块源码及产物。

不得删除、重命名、覆盖或“清理”任何既有成功、失败或候选run。

## 【允许修改范围】

只允许：

1. 统一Q01C恢复资格验证入口及其调用关系。
2. 修复S20/S30/S40不可变checkpoint输入绑定与恢复读取路径。
3. 修正stage marker的局部输出职责。
4. 修复S60状态、耗时、终态和最终manifest的落盘顺序。
5. 增加只使用合成fixture的测试和独立验收。
6. 在新的R2证据目录中保存日志、检查、源码快照和交回材料。

若修改需要触及任何科学计算公式或会改变现有科学数值语义，必须立即停止并交主控裁决。

## 【R2输出目录】

新建且仅写入：

`diagnostics/TASK-Q01C-R2/<run_id>/`

`run_id`必须使用实际启动时间和唯一后缀。目录已存在时必须失败退出，禁止覆盖。合成fixture、各中断/恢复run、拒绝路径run和源码快照均放在该R2目录下。失败尝试若产生目录，必须原样保留并明确标识，不得与最终正式R2证据混合。

## 【统一恢复资格判定】

### 唯一入口

必须建立一个唯一的stage reuse validation入口。可以是单一函数，也可以是一个公开入口调用少量纯辅助函数，但不得存在三套口径不同的判断逻辑。

以下三个流程必须调用该入口并消费同一种结构化判定结果：

- 正常`--resume`主循环；
- `--stage`的前置依赖检查；
- `--probe-resume`。

判定结果至少区分：

- `REUSABLE`：全部必需校验通过，可以复用；
- `NOT_STARTED`：该阶段没有完成证据，允许在前置依赖通过后首次执行；
- `INVALID`：存在已完成/部分完成证据，但hash、输入、配置、代码或schema校验失败，必须硬停止。

`INVALID`不得被解释成“重新计算即可修复”。正常`--resume`遇到`INVALID`必须非零退出，不得静默重算、自动降级、删除旧标记或覆盖损坏证据。

### 拥有data checkpoint的阶段

以下阶段不得仅凭`stage_marker_valid`判定可复用：

- `s10_scan_a1`
- `s11_scan_a2`
- `s12_scan_a3`
- `s20_score_primary`
- `s30_sensitivity`
- `s40_summarize`

统一入口必须完成并明确记录至少以下校验：

- stage名称和协议/schema版本；
- 输入绑定SHA256；
- config SHA256；
- code或checkpoint-protocol fingerprint；
- payload存在性、行数和SHA256；
- metadata存在性、字段完整性和SHA256；
- checkpoint marker存在性、类型以及对metadata的绑定；
- stage marker存在性、类型以及其登记的阶段局部不可变输出。

任何一项损坏或不匹配均为`INVALID`。不得只在probe中做完整校验，而让正常resume使用较弱判断。

## 【中后段不可变checkpoint链】

### S20

- S20输入绑定必须由已经完整验证的S10、S11、S12不可变checkpoint共同构成。
- 绑定应使用稳定、可复算、顺序明确的上游checkpoint identity，例如规范化组合上游stage、payload SHA256、metadata SHA256及必要协议字段。
- 恢复S20前必须先通过统一入口验证S10/S11/S12。

### S30

- S30输入绑定必须指向S20不可变checkpoint。
- S30首次计算和恢复后的下游读取必须从S20 checkpoint payload取得阶段输入。
- 不得把后来可能被S30改写的全局`quality_features_scores.parquet`旧哈希作为S20可恢复性的必要条件或唯一证据。

### S40

- S40输入绑定必须指向S30不可变checkpoint。
- S40首次计算和恢复后的下游读取必须从S30 checkpoint payload取得阶段输入。
- 不得仅依赖全局`quality_features_scores.parquet`判断S30或S40是否可恢复。

### materialized output

若最终仍需生成`quality_features_scores.parquet`，该文件只能作为面向最终产物的materialized output。它可以在明确的物化步骤中由最后一个适用的不可变checkpoint产生，但不得成为S20/S30/S40恢复资格的唯一证据，也不得使上游stage marker因后续合法覆盖而失效。

不得借重构输入路径改变任何列、排序、数据类型、公式、阈值或数值语义。合成测试应比较中断恢复结果与同fixture一次性运行结果，要求科学相关输出逐字段或按规定容差一致；容差规则不得在本任务中放宽。

## 【checkpoint marker与stage marker职责】

### checkpoint marker

checkpoint marker只证明不可变数据checkpoint可复用，必须绑定对应metadata，并由metadata绑定payload、输入、config、代码指纹、行数和stage。

写入顺序必须保持原子性：

`payload → metadata → checkpoint marker`

### stage marker

stage marker只证明阶段状态及阶段局部不可变输出已经完成。它可以绑定该阶段不会被后续阶段合法改写的局部文件。

stage marker不得绑定后续阶段会合法覆盖的全局文件。尤其不得再次让S20 marker绑定会被S30改写的`quality_features_scores.parquet`。

若某阶段没有独立的局部非数据输出，stage marker应只记录阶段身份、协议、完成时间和对应checkpoint identity，不得为了填充`outputs`字段而绑定可变文件。

## 【S60日志与manifest收口】

S60必须在`run_summary.json`最终冻结前，把自身实际执行信息写入：

- `stage_seconds.s60_finalize`，必须为非缺失、非负的实际耗时；
- `executed_stages`，必须包含`s60_finalize`；
- `stage_terminal_events.s60_finalize`，必须含唯一终态；
- `stage_exit_codes.s60_finalize`，必须记录实际退出码。

`stage_status.jsonl`中S60必须有start和唯一terminal。允许保留来源可区分的重复start；本任务不为美化日志扩大改动范围，但验收器必须按来源或事件语义正确统计，并确保terminal唯一。

独立验收器不得使用`STAGES - {'s60_finalize'}`、硬编码例外或任何等价方式主动排除S60。其“所有阶段完整”断言必须显式包含S60。

必须避免manifest循环依赖：

1. 在生成最终manifest之前完成并关闭所有会被纳入hash的run summary、stage status、日志、检查和命令记录。
2. 最终manifest最后生成，登记此前已冻结的文件；manifest本身可按既有约定不登记自身。
3. manifest生成后不得继续追加或改写任何被manifest登记的文件。
4. manifest后的核验只能只读执行，若需保存新的核验输出，则必须在manifest生成前完成，不能事后破坏封闭性。

## 【保留且不再扩修的R1事项】

1. `--hold-after-stage`允许作为显式、默认关闭的测试钩子保留。不得进入正常生产默认路径。
2. 重复start若来源可区分且terminal唯一，不作为本轮阻塞项；无需为日志外观扩大改动范围。
3. 历史正式Q01C主命令继续记为`NOT_VERIFIABLE`，不得猜测、回填或伪造成PASS。
4. R1已经通过的extension角色隔离测试不要求重做，除非本次代码修改直接触及其调用路径；即便重做也只能使用合成数据。

## 【必须执行的合成fixture测试】

全部测试必须使用不含真实A1–A3内容和路径访问的小型fixture，并通过真实命令行入口执行。

### A. 中后段跨进程恢复

1. P1使用真实Q01C入口和合成fixture运行，至少完成S20或S30的合法不可变checkpoint；优先在S30完成后使用`--hold-after-stage`等待外部终止，以同时覆盖S20→S30绑定。
2. 监督进程确认对应payload、metadata、checkpoint marker及stage marker均已落盘且完整校验通过后，外部终止P1。
3. P2必须是不同PID的独立操作系统进程，使用同一run目录和显式`--resume`继续。
4. P2必须通过统一入口复用所有已完成checkpoint。对每个已完成阶段记录新增计算次数，必须严格为0。
5. P2完成后续阶段和S60收口。
6. P1终止前与P2完成后，已完成checkpoint的payload、metadata和checkpoint marker SHA256必须完全一致。
7. 必须保存P1/P2真实命令、PID、起止时间、退出码、标准输出、外部终止证据、逐阶段计算计数和逐项reuse validation结果。

同进程即时probe、静态代码检查或只验证S10恢复均不能替代本测试。

### B. 三类拒绝路径

以互相隔离的合成run副本分别制造以下异常：

1. checkpoint payload内容或登记hash损坏；
2. config SHA256不匹配；
3. code/checkpoint-protocol fingerprint不匹配。

每种异常至少使用正常`--resume`入口启动一个独立进程，并证明：

- 统一验证入口返回`INVALID`并指出具体失败项；
- 进程非零退出；
- 损坏阶段及后续阶段新增计算次数均为0；
- 没有删除、覆盖、重写或“修复”损坏checkpoint；
- 没有自动回退到重新计算；
- probe与正常resume对同一异常给出一致的核心判定。

不得通过仅修改测试期望值、直接调用验证函数或mock掉正常CLI流程来代替真实拒绝路径。

### C. S60完整性

完整运行一个合成fixture后，必须证明：

- `run_summary.stage_seconds`含非缺失的`s60_finalize`实际耗时；
- `run_summary.executed_stages`含`s60_finalize`；
- `run_summary.stage_terminal_events.s60_finalize`含唯一terminal；
- `stage_status.jsonl`对S60存在start与唯一terminal；
- 独立verifier的全阶段集合明确包含S60，没有排除表达式；
- 生成manifest后，被登记文件均未再变化。

## 【独立验收要求】

独立verifier不得导入生产恢复模块来同时生成actual和expected。允许用标准库和独立读取逻辑：

- 重新计算payload、metadata、checkpoint marker和stage marker的SHA256关系；
- 独立解析阶段事件并检查S60；
- 独立读取计算计数器；
- 对比P1/P2进程、命令、时间线和退出码；
- 检查三个拒绝run在失败前后是否零重算、零覆盖；
- 检查源码中三个CLI流程是否都汇入唯一验证入口；
- 检查验收器没有排除S60的代码路径。

不得以生产函数返回“通过”作为同一检查的expected。静态检查可作为补充，不能代替跨进程行为证据。

## 【回归保护】

1. 原TASK-Q01C科学run的原manifest登记56项，R2前后均须56/56匹配。
2. TASK-Q01C-R1正式run必须完整保持不变。应依据其既有`output_manifest.json`及R2启动时建立的只读保护清单核对，不得在R1目录写入新文件。
3. 此前失败、未完成和候选Q01C run均不得变化。
4. 不得读取、stat、hash、扫描或解压真实A1–A3，因此不得把它们纳入R2保护快照。
5. 不得访问或修改C01、C01-R1。
6. 当前源码修改前后SHA256必须登记；R2目录中的code snapshot必须与实际执行源码逐字节一致。

## 【必须输出的文件】

R2正式目录至少包含：

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
- `synthetic_fixture/`
- `midstage_interruption/process_1/`
- `midstage_interruption/process_2/`
- `rejection_tests/payload_hash/`
- `rejection_tests/config_mismatch/`
- `rejection_tests/code_fingerprint/`
- `s60_closure_test/`
- `code_snapshot/`
- `output_manifest.json`

其中各进程目录必须含真实命令、PID、stdout/stderr、退出码和必要状态快照。可增加必要的机器可审查JSON/CSV，但不得只用文字说明替代结构化证据。

## 【必须记录的数值】

- P1、P2及三个拒绝进程的PID、开始/结束时间、退出码。
- P1终止时最后一个合法checkpoint及其stage、行数、payload/meta/marker SHA256。
- P2逐阶段`REUSABLE`、`NOT_STARTED`、`INVALID`数量及原因。
- P2对已完成S10/S11/S12/S20/S30/S40中各阶段的新增计算次数。
- 三个拒绝案例失败前后的逐阶段计算次数和checkpoint hash。
- S60的start数、terminal数、终态、`stage_seconds`和exit code。
- 原科学run manifest匹配数，必须为56/56。
- R1正式run manifest匹配数与不匹配清单，必须全部匹配、0不匹配。
- R2 output manifest登记数和当前不匹配数。
- 修改前后各源码SHA256，以及code snapshot一致性结果。
- 真实A1–A3访问声明：opened/read/stat/hash/decompress/scan均为0；该声明须同时说明验证依据是fixture路径隔离与代码/命令审计，而不是对真实文件执行探测。

## 【精确验收锚点】

1. 正常`--resume`、`--stage`前置依赖和`--probe-resume`调用同一stage reuse validation入口。
2. S10/S11/S12/S20/S30/S40的复用均同时验证input/config/code/payload/meta/checkpoint marker，不存在仅凭stage marker复用的路径。
3. 对已有损坏或不匹配证据返回`INVALID`并硬停止；仅真正未开始的阶段可以在依赖满足后首次执行。
4. S20绑定已验证的S10/S11/S12 checkpoint；S30绑定并读取S20 checkpoint；S40绑定并读取S30 checkpoint。
5. S20/S30/S40 stage marker均不绑定后续阶段会合法改写的全局文件。
6. 中后段恢复由两个不同OS进程完成；P2对P1已完成阶段的新增计算次数逐项为0。
7. payload hash损坏、config不匹配和code fingerprint不匹配三条正常resume路径均非零退出、零重算、零覆盖。
8. S60出现在最终`stage_seconds`、`executed_stages`、`stage_terminal_events`和`stage_exit_codes`中；stage status有start与唯一terminal。
9. 独立verifier显式验收全部STAGES并包含S60，没有任何排除S60的集合运算或硬编码例外。
10. 最终manifest生成后所有被登记文件保持不变，R2 output manifest当前核对0不匹配。
11. 原TASK-Q01C科学run保持56/56一致；R1正式run和全部既有Q01C run零变化。
12. 真实A1–A3未被read、stat、hash、扫描或解压；真实Q和真实敏感性结果均未重新计算。

## 【验收标准】

只有同时满足以下条件，R2才可标记`COMPLETE_PENDING_REVIEW`：

1. 唯一恢复资格入口已经在三个CLI流程中真实生效。
2. 中后段不可变checkpoint链和跨进程恢复行为证据完整。
3. 三种损坏/不匹配拒绝路径均由正常CLI实测为硬停止。
4. S60日志与摘要完整，manifest封闭顺序正确。
5. 合成一次性运行与中断恢复运行的科学相关输出一致，且没有修改科学计算语义。
6. 独立验收不导入生产恢复模块自证，关键检查0 FAIL、0 NOT_CHECKED、0 NOT_VERIFIABLE。
7. 正式科学run、R1正式run、旧失败/候选run及C01证据均未变化。
8. R2 output manifest全部匹配。

## 【FAIL / NOT_VERIFIABLE规则】

### 必须FAIL

- 对真实A1–A3执行read、stat、hash、扫描或解压。
- 重新运行真实全量质量流水线或重新计算真实Q/敏感性结果。
- 修改任何既有科学run、R1 run或失败/候选run。
- 修改或访问C01/C01-R1范围内文件用于本任务计算。
- 三个CLI流程仍存在不同的reuse资格口径。
- 任一data checkpoint阶段仅凭stage marker被判定可复用。
- 检查失败后发生静默重算、自动降级或覆盖旧checkpoint。
- S30/S40恢复仍从可变全局文件而非上游不可变checkpoint取得阶段输入。
- stage marker仍绑定后续会合法改写的全局文件。
- P2不是独立进程，或P2重新计算P1已完成阶段。
- 三种拒绝路径有任一未通过正常`--resume`实测。
- 最终run summary遗漏S60，或验收器主动排除S60。
- manifest生成后继续改写被登记文件。
- 为通过工程检查而改变任何科学公式、阈值或数值语义。

### 可保留NOT_VERIFIABLE

仅限历史正式TASK-Q01C从未落盘、现在无法诚实补证的原始主命令。该项沿用历史记录，不属于R2新检查。

R2新产生的统一验证、中后段恢复、拒绝路径、S60日志、命令、进程、检查点和manifest证据均不得记为`NOT_VERIFIABLE`或`NOT_CHECKED`；缺证据即FAIL。

## 【停止条件】

1. 发现修改会改变科学数值语义时立即停止并交主控裁决。
2. 任何R2进程尝试访问真实A1–A3路径时立即停止并标记FAIL。
3. 正式科学run、R1 run、旧Q01C run或C01范围任一文件发生变化时立即停止。
4. 统一验证入口将`INVALID`降级为重算时立即停止，不得以补跑掩盖。
5. 中后段P2对已完成阶段新增计算次数不为0时立即停止。
6. 任一拒绝测试没有硬停止或覆盖了损坏证据时立即停止。
7. S60仍无法在manifest前完整冻结时停止，不得通过验收器排除S60。
8. 交齐R2证据后停止，不更新00–05，不启动T03、T05或问题四建模。

## 【完成后必须交回的材料】

- R2正式目录绝对路径和run_id。
- 修改文件列表、修改原因、前后SHA256及code snapshot。
- 唯一stage reuse validation入口的调用关系和结构化判定schema。
- S20←S10/S11/S12、S30←S20、S40←S30的输入绑定与独立复算证据。
- 中后段P1/P2实际命令、PID、时间线、退出码、检查点hash和零重算计数。
- payload、config、code fingerprint三种拒绝路径的命令、日志、判定和零覆盖证据。
- S60最终摘要、事件和耗时证据。
- manifest封闭前后hash核对结果。
- 原科学run 56/56、R1正式run及旧run未变化的证据。
- 全部checks、verification、output manifest及明确保留的历史`NOT_VERIFIABLE`项。

施工单生成后停止。本文件本身不授权执行TASK-Q01C-R2。
