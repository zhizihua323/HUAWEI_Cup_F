# 核验与问题日志

> 恢复登记时间：2026-09-24T13:32:13+08:00（Asia/Shanghai）。最近更新：2026-09-25。TASK-T08最终复审通过并关闭；Q1–Q4科学建模链全部关闭，下一阶段为论文整合与最终审阅。


## 本轮实际执行的核验

2026-09-24 13:25–13:27（本机时区）：使用用户Python执行 `recovery/2026-09-24/recover_verify.py` 和 `inspect_quality_gap.py`，两脚本均退出0；主脚本的退出0只表示生成审计成功，内部有3项明确FAIL。详见verification.json。首次临时控制台读取遇到GBK输出编码错误，随后使用 `-X utf8` 完成；这不是上轮模型中断日志。

|核验|结果|证据/范围|
|---|---|---|
|原数据清单|通过|2012路径及字节全部匹配，合计551191693字节；41个CSV的SHA256全部相同|
|源码静态解析|通过|7份src/*.py可由ast.parse解析，不导入、不执行项目模块|
|输出可读性|通过|64份既有JSON/CSV读通；不是对每张图或每条科学结论的全面验收|
|配比标准化、实际y、系数预测及指标|通过|6套×2模型：原始CSV→归一化→保存系数乘积→预测、13域误差/均值误差/R²/秩相关；aggregate_predictions一致|
|B1参数及验证指标|通过|1176条主配置公式与原B1一致；4配置×3划分的样本数/RMSE由保存预测复算一致|
|B1保存重采样汇总|通过|80条保存参数的2.5/50/97.5分位与参数JSON一致，未重新重采样|
|B6/B7/B8方向与交集|通过|45/45/150固定ND组方向及360/160/224交集复核；不重新拟合非线性模型|
|质量计数|通过|272505-11419=261086；40943+10287=51230；51230+209856=261086|
|质量均值恒等/按总n聚合|3项失败|总Q与组均值不完全一致；A1 commoncrawl、wikipedia两域合并不一致；P01解释原因|

数值比较一般使用绝对容差1e-10、相对容差1e-9；不能以“差值小”抹去有效分母不同的问题。检查通过只涵盖检查项，不等于旧脚本端到端复跑通过。

## TASK-Q01A 最终复审（2026-09-24）

结论：**通过；项目层登记为“经R1补证后验收通过”**。原正式运行`diagnostics/TASK-Q01A/20260924T142229+08/`继续保留`PARTIAL`和退出码2；R1没有把历史失败改写成成功。R1正式修正目录为`diagnostics/TASK-Q01A-R1/20260924T150854+08/`，两个前置失败R1目录未纳入统计。

复审只读取既有产物和脚本，没有读取、解压或重扫A1–A3，也没有运行原诊断。确认事项如下：

- 原R目录34个文件与其清单哈希一致；复审开始时，原input manifest登记的111个受保护项目文件哈希一致。之后01、04、05仅因本次通过后的授权登记而修改。
- R1的repair与verify均退出0；`repair_checks.json`为21 PASS、0 FAIL、1 NOT_VERIFIABLE。唯一不可验证项是原运行前没有全目录mtime快照，无法事后证明历史mtime完全未变。
- 原始异常事件可独立重建为19个物理记录、114个NaN元素：A1 professionalism 5条/30元素，A1 reasoning 13条/78元素，A3 github professionalism 1条/6元素；两字段交集0。
- `raw_field_counts_corrected.csv`的域级和ALL计数可由事件按记录去重及按元素计数复算；19个事件记录键与`raw_mask_corrections.csv`完全一致，新raw掩码与`row_masks_corrected.csv.gz`逐行一致。
- 排除唯一获准修正的`raw_field_invalid`层后，`missing_patterns`的316个非raw键和`missing_pairwise`的39100个非raw键及值与原R一致。校正后的raw模式和pairwise可由事件掩码复算。
- all_unique为261086；11特征完整数和25特征完整数均为261067，未覆盖19。19条均有2个有效质量组，261067条有3组，0/1组有效案例为0。
- all_unique/ALL的分歧range与ddof=0组间std有效数均为261086，缺失range比较为False的行数为0；Q_mean和Q_std有效数均为261067，Q_std方差除数为261066。主控按50个scope/domain组合逐项核对，同一规则均已传播。
- extension overlap按ALL单列为A2=1419、A3=10000，没有与域明细重复相加。
- `verify_repairs.py`未导入修复脚本，独立重建事件、掩码、模式、分母及行号覆盖；人工测试覆盖0/1/2/3个有效组和含NaN的六元素列表；272505物理行按file/source_line唯一并覆盖各文件1..N。

保留两项限制。第一，历史全目录mtime只能记为`NOT_VERIFIABLE`，不能制造事前快照；它不影响现存数据表、掩码、分母之间的可复算性，因此不阻止验收。第二，R1的`output_manifest.json`中`verify.log`和`verify_console.log`在清单生成后继续追加，当前哈希与清单不一致；其余31项一致。该问题只影响日志封装的最终哈希，不影响脚本、校正数据表或检查结果，故记录为非阻断性交付限制，不修改R1目录。

## TASK-Q01C-R2 最终主控复审（2026-09-25）

结论：**通过**。项目层统一登记为“科学结果经Q01C验收可信，恢复与日志机制经R2补证后通过”。本次只读审查正式R2目录`diagnostics/TASK-Q01C-R2/20260925T004211+08/`及既有只读证据，没有运行R2脚本、访问真实A1–A3、重算真实Q或敏感性结果，也没有修改任何既有run。

- `validate_stage`是统一阶段复用判定入口；正常`--resume`、`--stage`前置依赖和`--probe-resume`均调用该入口。返回值区分`REUSABLE`、`NOT_STARTED`、`INVALID`。s10/s11/s12/s20/s30/s40的数据检查点均检查输入绑定、配置、代码指纹、payload、meta和checkpoint marker；`INVALID`直接以非零状态停止，没有静默重算路径。
- 不可变链为S20绑定S10/S11/S12、S30绑定S20、S40绑定S30。S30与S40的首次运行及恢复均从上游checkpoint payload取输入；全局`quality_features_scores.parquet`仅是物化输出，不决定S20/S30/S40能否恢复。stage marker只绑定阶段局部不可变输出及checkpoint identity。
- 跨进程证据确认P1=14452、P2=15776；P1在S30合法checkpoint完成后由外部终止，P2在同一run目录以正常`--resume`恢复。s10/s11/s12/s20/s30新增计算次数均为0，payload/meta/checkpoint marker/stage marker哈希不变，随后S40/S50/S60完成。
- payload哈希损坏、配置不匹配、代码指纹不匹配三类独立正常`--resume`均得到`INVALID`并非零退出；损坏阶段及以后新增计算为0，损坏checkpoint没有被覆盖、删除或自动修复，probe与resume的核心判定一致。
- 合成正式run的`run_summary.json`已包含S60耗时、执行阶段、终态和退出码；`stage_status.jsonl`按每次finalizer调用记录start及唯一terminal。R2独立终验包含S60，没有通过集合运算排除它。summary与日志先冻结，manifest最后生成，之后无登记文件改写。
- 当前独立核对R2 manifest 284/284、原Q01C科学run 56/56、Q01C-R1 138/138均匹配；旧Q01C失败/候选run在受保护快照归一化路径分隔符后为476/476、缺失0、新增0、变化0。C01及C01-R1现有manifest也保持匹配。
- R2自检存在两个报告层盲点：`verification.json`生成时code snapshot尚未填充，故记录`snapshot_files=0`；`protected_artifacts_check.json`未统一Windows路径分隔符，产生476 removed与476 added但仍标PASS。主控已用冻结后的9项snapshot清单、关键源码逐项哈希及路径归一化前后清单独立补核，均一致。这两点不改变恢复实证、科学结果或受保护产物，但须保留在审查记录中，不能把原自检表述为无缺陷。
- 接受默认关闭的`--hold-after-stage`测试钩子；不同PID的多次finalizer事件按独立调用评价，每次均有唯一terminal，不需要再改日志；生产S50保留在S60之前，S60之后由独立只读R2 verifier补验，避免重新引入manifest循环依赖。

历史正式Q01C主命令仍为`NOT_VERIFIABLE`，不补造；Q01A原PARTIAL及此前失败/候选run继续保留。TASK-Q01C、Q01C-R1、Q01C-R2与T02至此关闭，允许进入T03的方法设计，但本轮没有执行T03。

## TASK-C01/C01-R1 最终状态登记（2026-09-25）

结论：**通过并关闭**。原C01目录继续保留最初“小修”历史，C01-R1修正表作为后续候选输入。经既有正式复审确认：1958=1954+4；1863个目录；11724个模型任务结果槽位中11699个有限、25个缺失；11160个模型×任务键中11135个有效、25个零结果；宽表1860个模型，其中1854个六任务完整、6个partial。四个损坏目录已传播，`six_task_mean_complete_only`仅在1854个完整模型上有限，partial的该字段均为NaN，另用明确命名的`partial_task_mean`表示部分任务均值。关键C8检查44/44 PASS，原C01目录及`evolution_audit.py`保持不变。

仍需转交具体建模分支的范围外问题包括：95个双文件目录的run取舍、4个损坏JSON的统计处置、C5/C6桥接方法、时间外验证切分、模型身份与日期边界，以及Loss–Benchmark、时间预测和问题四模型本身。它们不阻止数据审计关闭，但在相应建模分支裁决前，C01-R1表只能作为候选输入。

## TASK-T03E 最终主控复审（2026-09-25）

结论：**通过；T03/T03E关闭**。正式结果目录为`diagnostics/TASK-T03E/20260925T020032+08/`。本次只读复审没有运行T03E、读取真实A1–A3、修改正式/旧run或重算全量质量流水线；只从冻结行级产物和Q01C正式Parquet做最小独立复算。

- 预注册未漂移：D=`Q_baseline`；唯一候选为`Q_C=Q_baseline*(1-0.02P)`，`P=(p_top2gram+p_top3gram)/2`。没有bonus、clip、lambda学习、A/B候选或PCA/熵权/CRITIC选优；DSIR没有进入标量Q。
- 272505条物理行全部保留，身份序列和`Q_baseline`逐行一致；272486条物理行`Q_valid=True`，19条无效行的D/C均为NaN。活动域公式的最大独立复算误差为`5.56e-17`，P最大误差为`2.22e-16`；非活动域242864条有效物理行严格C=D。
- 精确域标签为arxiv、book、c4、commoncrawl、github、stackexchange、wikipedia。book calibration有效n=137，登记`INSUFFICIENT_CALIBRATION`；active域仅c4、commoncrawl、wikipedia。
- freeze seal时间02:00:35，第一次holdout读取02:00:40.710，第一次extension读取02:00:40.902。冻结包哈希保持一致。Phase A分析层只物化40943条A1 calibration记录；存储层单row-group可能解码其他页，但没有把非calibration行返回分析层。
- 三个active域bootstrap均为200/200联合PASS。主控按冻结键排序，独立抽查每域replicate 0、37、199；q95/q99参数、penalty MAE、确定性Spearman与top10 Jaccard均与登记值一致到浮点精度。
- holdout独立复算全部通过：c4 n=1959、Spearman=0.9999883272、Jaccard=1、mean-P差=0.0046029845、OOS=0.0066360；commoncrawl n=1948、0.9999688802、0.9897959184、0.0031678850、0.0143737；wikipedia n=1973、0.9999829992、1、0.0008853537、0.00810948。结论仅为`ACCEPT_STABILITY`，不表示C优于D。
- extension overlap为11419/11419复现；extension new只有arxiv和github，没有任何active域，故状态为`NOT_TESTED_FOR_ACTIVE_CORRECTION`，不能写成迁移成功。
- RegMix/Loss的`NOT_IDENTIFIABLE`成立：11/17域无质量映射，完整配比下`Q_mix`是w的确定函数，A/B没有正式连接键，也没有固定配比下的独立质量变化。没有训练新模型，问题转交T06识别设计。
- `t03e_verify.py`在自身源码内重新实现惩罚、排序、bootstrap和验收逻辑，没有导入执行模块；17/17 PASS可信。执行检查的EX-23为`NOT_CHECKED`，由主控独立核对最终manifest补证。
- 正式最终manifest是02:00:56生成的第二次53项版本；早期版本为provisional。当前53/53大小和SHA256匹配，manifest之后没有登记文件改写。`verification.json`、`checks.json`、`run_summary.json`和`handoff.md`均在最终manifest之前冻结。
- 两个旧run `20260925T015757+08`和`20260925T015930+08`标记`SUPERSEDED`并保留。三次run的候选Parquet、冻结阈值、lambda、active域、公式及门槛一致；变化仅涉及verifier、prior-exposure说明和RegMix识别性记录。旧run后续重生成manifest并追加finalizer日志属于历史封装变更；冻结科学包mtime和seal未变。
- top-2gram/top-3gram来源只说明为top word n-gram字符集中度，未给出百分比或理论边界；正式值明显非`[0,1]`。量纲登记为`THEORETICAL_SCALE_NOT_VERIFIED`，禁止猜测`[0,100]`。T03E惩罚基于域内q95/q99，语义表修正不改变现存数值结果。

保留限制：历史holdout曾被先前项目工作及两个superseded run接触，故只能称“参数冻结后的验证”，不能称全新盲测；C没有独立真实质量标签；extension active correction未测试；RegMix/Loss外部增量不可识别；A侧Q与B侧`Q_score`仍须T06标定。`access_log.jsonl`的两条RegMix记录把`file`字段误写成Q01C Parquet，但`note`、输入manifest、输出识别性文件和源码均记录了实际mapping/B6输入；该日志字段缺陷不改变已复算的科学结果，后续不得沿用该写法。

## 问题清单

### P01 / 已关闭：质量非有限指标与有效分母

`feature_summary.csv` 中，A1/commoncrawl 的modernbert_professionalism有效9636/9640；A1/wikipedia同指标9999/10000、modernbert_reasoning有效9987/10000；扩展新增github的modernbert_professionalism有效193751/193752。原audit同时记录上述列表含NaN元素，完整列表分别缺5、13、1行（不同指标行可能重叠，不能直接求和宣称缺失总Q行数）。

当前 `quality_audit.py`：get_features将非有限列表变NaN；score_quality的组均值与总Q使用skipna=False；summarize却用默认跳过NaN的mean并把n写成总行数。因此组均值和Q均值的有效样本集合可能不同，总n也不是有效Q样本数。本轮最大“组均值平均−Q_mean”绝对差为6.5524745873e-5；按总n合并校准/留出时commoncrawl差4.7303650330e-8、wikipedia差5.9910697514e-9。两份细表及原始证据在recovery目录。

`verify()`第442行的历史逻辑曾要求Q_baseline全部非空，与缺失传播不相容；不能反推旧中断点。TASK-Q01A/R1已查明19个缺失记录、特征交集、三组有效性和各统计分母；Q01B已裁决方法，Q01C正式run已按严格完整案例实施，保留全部底层记录并显式报告覆盖率。科学结果经Q01C验收可信，恢复与日志机制经R2补证后通过。

### P02 / 已关闭：阶段日志、检查点与恢复机制

Q01C正式run已有行级Parquet、阶段状态、检查点、源码快照、命令与终验。R2又补齐统一复用判定、不可变checkpoint链、三类硬拒绝、中后段跨进程恢复和S60/manifest收口。原Q01C主命令缺失仍为历史`NOT_VERIFIABLE`，不影响当前恢复机制验收。

### P03 / T06已裁决传播方式：B表质量规律冲突

B6来源内MQ-add经R1修正后通过G1–G4；B8仍给出反向冲突。两者不合并、不平均。B8固定为`CONFLICT_EVIDENCE`，不传播旧k=-20；T07并列保留B6、k=0和B8方向冲突。冲突本身没有被“解决”为统一参数。

### P04 / 证据限制 / 未解决：B1异常贴合与迁移不足

B1拟合RMSE约1.46496e-4，近似确定幂律需查原始来源/变换。B2外部RMSE约1.24308，B4/B5约0.29267/0.19760；B3插值与B10估算不能作为新真实实验佐证。现存输出可作为探索性结果，不能写成普适准确。外部RMSE本轮读取既有表，未全面复算所有外部预测。

### P05 / T06已关闭但统一桥接仍不可识别：Q、p与广义律

T06确认A侧Q与B侧`Q_score`无可估计桥接，H1–H3只能是情景；RegMix向B1运输也是情景，Q_mix与完整p不能分别识别。正式联合主模型保持M0_B1。该结论允许T07做条件情景优化，但不允许宣称已验证统一L(N,D,Q,p)。

### P06 / 文档口径 / 未修复：选择指标易被误读

mixture_baseline.md的“13个Loss等权均值作为总体目标”不足以区分两种运算顺序。实际族选择是先算各域MSE再平均；报告表展示的是先平均Loss再算RMSE。线性在前者较优，二次在后者及1M测试较优并不自相矛盾。model.json、metrics.csv和源码有明确证据。恢复文档澄清，原报告未改。

### P07 / 可复现性 / 待补证据

环境JSON的MATLAB版本来自源码硬编码，不能证明许可、工具箱或运行成功；没有MATLAB结果。当前源码与输出没有绑定的历史提交/哈希，绘图脚本修改时间晚于部分图文件，不能声称当前代码原封不动生成每一份旧输出。本轮补存当前哈希快照；后续须记录每次运行的源码版本。没有最终依赖锁或统一复跑入口。

### P08 / 已关闭：C模块问题四建模

C01/C01-R1、T05和T08均已关闭。问题四正式结论为条件关联、时间外推未验证和未来进步不可识别；规模关联主分量为0只表示现有主样本不能支持该预测项。`solution/outputs/evolution/`虽仍不存在，但正式T08结果由诊断run和`paper/T08_RESULT_FREEZE.md`承载，不再阻塞科学链关闭。

## 未做的校验

该次T03E最终复审没有读取真实A1–A3、运行T03E、重新训练或重跑全量质量计算；bootstrap只从冻结calibration行和固定种子抽查9个代表重复。当时尚未执行T05/T06、Loss–Benchmark、演化预测、问三求解或论文生成；T06的后续状态以本文件后附的T06复审节为准。没有验证全部外部文献真值、OOF逐域残差或出版版式。没有把参考资料或聊天里的结果补进输出。后续新发现需追加证据和关闭条件，不覆盖既有历史。

## TASK-T06E-B-R1与T06集成复审（2026-09-25）

结论：**B-R1通过；T06主控集成通过并关闭**。

- R1正式目录为`diagnostics/TASK-T06E-B-R1/20260925T103130+08/`。主控独立核对22个全拟合点，固定物理值、conditional值及SSE阈值全部通过；926条完成profile行的固定值一致性为0失败。
- 修正G4只包含MQ-add的E/A/B/alpha/beta/k_add六项；Jacobian 6/6满秩，条件数53.944075，预测有限非负，正式参数不触边，profile均有限分离。MQ-eff eta=1e-6触下界，已从MQ-add G4隔离。
- G1=43/45，G2 leave-N和leave-D分别改善33.13%与32.41%，G3=200/200，G4 PASS，因此MQ-add最终为`ACCEPT_B6_SOURCE_RELATION`，资格精确为B6来源内条件关系。
- R1源码与snapshot一致；R1 86/86、原B 104/104、P 49/49 manifest当前匹配。G1–G3来自原B run，未重拟合；旧失败结论原样保留。
- 集成目录`diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/`没有模型拟合或预算优化，只填充P分支预注册的21个槽位。独立verifier 21/21 PASS，manifest 23/23匹配。
- 最终联合默认：M0_B1，质量关闭，配比运输关闭。A/B bridge=`NOT_IDENTIFIABLE`；RegMix→B1=`SCENARIO_ONLY`；B8=`CONFLICT_EVIDENCE`；Q与完整p禁止同时独立寻优。

本轮编制了T07与T05正式施工单，并生成`paper/T06_RESULT_FREEZE.md`。没有执行T07、T05或T08；旧“没有执行T06”的记录只描述此前复审时点，现由本节取代。

## TASK-T07最终主控验收（2026-09-25）

结论：**通过并关闭**。本次只读审查`diagnostics/TASK-T07/20260925T113744+08/`，没有重跑优化。

- 正式预算为1e18、1e20、1e22 FLOPs；N、D均先从十亿单位转换为实际数量。主控独立复算`6ND`、`2e-4NDH`和总成本，最大相对误差在浮点精度内。
- S00/H=2048三档`N_B/D_B/Loss`与执行器报告一致；最高预算D=299.893达到B1支持上界。S00的Q为`NOT_IDENTIFIED_NOT_OPTIMIZED`、p为`FIXED_P0_NOT_OPTIMIZED`。
- 主表75行=69 OPTIMAL+6 NO_NUMERIC_OPTIMUM；S07与S17各三档保持无数值结果。没有Q和完整p同时自由优化，数值最优行没有支持域越界，p和为1且最小分量不小于0。
- 最大相对预算越界`9.403629568e-13`，最大KKT residual `2.7932317030401693e-08`。`H_crit=30000`及五个H候选均正确传播；这里只按活跃约束变化报告结构转移。
- 参数不确定性中S00每预算80个B1整行draw；质量情景每预算/成本组合200个B1/B6条件整行组合。独立verifier逐行对照保存的来源draw，没有逐参数独立抽样。
- 独立verifier未导入执行模块，39/39 PASS。正式manifest 39/39当前匹配，`code/`与`code_snapshot/`五项逐文件相同。

## TASK-T05最终主控验收（2026-09-25）

结论：**通过并关闭**。最终资格为`CONDITIONAL_ASSOCIATION_ONLY`。本次只读审查`diagnostics/TASK-T05/20260925T113355+0800/`，没有重跑桥接。

- C8锚点为1854完整、6 partial、4损坏JSON；损坏JSON和partial均未获完整六任务分数。桥接Parquet有45行，其中7行`main_comparable`、38行`conditional_source_transfer_only`。
- C5是C6精确43行、10共同字段逐值一致的子集；主层C5/C6相同行为7，不能把C6 High当独立测试。主层只使用同一Loss定义和验证口径的Pythia最终checkpoint。
- 主层7行的D均为观测299.893B；条件层38行D与logD均为空，未发生插补。95个多文件目录已审计，桥接候选没有使用这些目录。
- 时间切点2024-09-01的seal哈希匹配，seal文件mtime早于最早指标文件。split registry中未发现同一模型同时出现在同一划分的训练和测试角色。
- 主层六任务及辅助均值全部选择CONSTANT。时间外、留模型族和主层规模外升级条件均未满足；`time_trend.validated_for_extrapolation=false`必须原样传播。
- 独立verifier未导入`run_t05`或`t05_common`，28/28 PASS。正式manifest 34/34当前匹配，四项源码与snapshot相同。

冲刺模式下未发现公式、单位、泄漏、缺失处理、支持域、verifier或manifest的实质问题。结果不漂亮、样本少和常数模型均按预注册作为科学限制接受，不开返工。

## TASK-T08最终主控验收（2026-09-25）

结论：**通过并关闭**。本次只读审查`diagnostics/TASK-T08/20260925T142203+0800/`，没有重新拟合、运行T08脚本或修改T05/T07。

- 主控从T05身份交叉表独立筛出10792条C1/C2/C8 exact-raw、日期不模糊记录，最大提交日期为2025-03-13；C8有效评测最大时间为同日18:16:04 UTC。因此forecast origin及2026-03-13、2027-03-13两个情景时点正确。
- 独立重建增长支持：7条观测N/D、1个Pythia族、6个相邻候选、1个90–730天有效族级区间，未达到3族/10区间门槛。三种增长率均为空，没有改用全榜时间趋势、参数量增长、手工倍率或外部假设。
- 49条主层模型×目标记录均为CONSTANT，规模关联分量严格为0；`observed=fitted+conditional_remainder`最大误差`3.55e-15`。所有命名守卫均为非规模关联残差/条件剩余项。
- 42条benchmark情景全部为`CONDITIONAL_BASELINE_ONLY`和`NOT_IDENTIFIABLE_PROGRESS`；6条Loss空间情景均无增长率、compute、N、D或Loss数值，Loss→benchmark转换为0。
- 六任务向量和辅助均值分开。931个历史分层中665个`n<5`单元全部标记`INSUFFICIENT_N`；6个partial不进入完整均值，4个损坏JSON赋分为0，38个条件层Medium的D/logD均为空，同模型泄漏为0。
- 六类不确定性分别存在，未生成合并CI；7条时间外推记录全部为`UNVALIDATED`。
- 独立verifier未导入执行模块，32/32 PASS；内部18项检查为17 PASS和1项finalization后满足，无FAIL。input manifest 30/30、output manifest 38/38当前匹配，manifest晚于全部登记文件；8项源码与snapshot一致。

T08至此关闭；`Q1 CLOSED`、`Q2 CLOSED`、`Q3 CLOSED`、`Q4 CLOSED`。后续不得新增科学建模任务，项目转入`PAPER INTEGRATION + FINAL REVIEW`。
