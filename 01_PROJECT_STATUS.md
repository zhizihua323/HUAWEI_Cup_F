# 项目状态

> 恢复登记时间：2026-09-24T13:32:13+08:00（Asia/Shanghai）。最近更新：2026-09-25，TASK-T08最终验收通过并关闭。Q1、Q2、Q3、Q4科学建模链全部关闭；下一P0为`PAPER INTEGRATION + FINAL REVIEW`。


## 已确认的实际状态

“产物齐备”仅指该轮基线输出存在并通过所述核验，不代表整道题完成，也不证明进程正常退出。

| 模块 | 状态 | 证据与完成范围 | 尚缺内容 |
|---|---|---|---|
| 环境与原始数据目录审计 | 已有产物，本轮部分复核通过 | `outputs/audit/` 四文件；2012 文件/551191693 字节/40 编号；本轮路径大小及 41 CSV 哈希一致 | MATLAB 独立日志、可锁定依赖、正式运行日志 |
| A1–A3 质量 | Q01C科学结果可信；T03/T03E方法与实证已关闭 | 正式科学run `solution/outputs/quality_q01c/20260924T215718+08/`保留272505条物理记录和261086个唯一键，主Q有效261067、缺失19；T03E确认D=`Q_baseline`，C仅作规则敏感性候选 | T06确认A/B质量尺度`NOT_IDENTIFIABLE`；active correction仍缺extension-new证据 |
| 配比 | 首轮基线产物齐备 | `outputs/mixture/` 27文件，报告和图存在；12组模型/数据预测由系数复算一致 | Q 接入、可靠跨规模迁移、全局配置优化与更完整验证 |
| B 缩放律/T06 | T06已关闭，来源内关系与联合边界已冻结 | B1主模型参数保留；B6 MQ-add经G1–G4通过，资格仅为`B6_SOURCE_CONDITIONAL_ACCEPTED`；集成run `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/`有21项独立检查、23项manifest | 不存在已验证的统一L(N,D,Q,p)；跨来源质量和配比只能做情景 |
| C演化/T05/T08 | T08已通过并关闭；问题四结果冻结 | T05桥接仅条件关联；T08正式run `diagnostics/TASK-T08/20260925T142203+0800/`确认规模项为0、增长率不可识别、未来仅条件基线 | 规模项为0不表示规模无作用；条件剩余项非因果；不得生成未来数值进步 |
| 问三优化 | T07已通过并关闭；Q3结果冻结 | `diagnostics/TASK-T07/20260925T113744+08/`；75行主表、69 OPTIMAL、6 NO_NUMERIC_OPTIMUM；独立验证39/39 PASS，manifest 39/39 | 质量、配比和B8均保留情景资格；不得写成统一识别效应或唯一全局最优 |
| 论文与提交 | 仅结构约定 | `reports/论文结构与交付约定.md` | 本项目论文正文、排版源文件、最终PDF、复现入口与附件包 |

上表 `src/`、`outputs/`、`reports/` 均以 `solution/` 为前缀。初期 `tmp/environment_review` 中对原数据的格式扫描不能替代模型结果。

## 可以引用的基线数字及边界

配比模型训练512行、检验1M/60M各256行、1B 64行、估算10B/70B各63行。按训练OOF的13域平均 MSE 选择线性模型。1M检验的平均Loss RMSE=0.2269777773，R²=0.3319216143，Spearman=0.6250743877；60M、1B的同一RMSE分别为1.5173310792、3.1889453478。大尺度绝对损失迁移较差。对应 `solution/outputs/mixture/metrics.csv` 与逐行预测，本轮均复算核对。OOF完整逐域预测未保存，本轮未重拟合OOF。

B1 最终登记配置为 `point__linear`，不是把比较表第一行直接当选中配置。`scaling_params.json` 给出：E=1.6897975629820348，A=0.35398032060655715，B=1.2403055835426349，α=0.33997658194108205，β=0.27987812854684485。单位为十亿参数/十亿tokens。B1有1176点、8个规模，拟合/留模型/末20%token RMSE为0.0001464961/0.0001511798/0.0001090975；预测文件与参数、原始B1核对一致。近乎确定的幂律形态需核验来源，不能作为真实外推精度保证。

质量审计记录：A1=51230，A2=17523，A3=203752；重复出现11419次、唯一键261086个。A1校准40943、留出10287；扩展新键209856。TASK-Q01C正式科学run保留全部272505条物理记录，其中主Q有效272486、无效19；唯一键口径主Q有效261067、无效19。异常仅涉及modernbert_professionalism 6条和modernbert_reasoning 13条，交集0。19条主Q均为NaN且`Q_valid=False`；敏感性列单独计算，没有写回主Q。全部scope/domain显式报告`n_total/n_Q_valid/n_Q_missing/coverage`。该科学结果已经验收，剩余14项规则/DSIR融合属于T03新方法设计，不属于Q01C缺失修复。

T03E正式run将唯一确认性候选冻结为`Q_C=Q_baseline*(1-0.02P)`，其中`P=(p_top2gram+p_top3gram)/2`。active域仅为c4、commoncrawl、wikipedia；book因calibration有效n=137而不适用，其余域为`RULE_NOT_APPLICABLE`且C=D。三个active域bootstrap均为200/200联合通过，冻结后的holdout状态为`ACCEPT_STABILITY`；该结论仅表示规则修正稳定且保守。extension overlap 11419/11419复现，但extension new没有active域，正式状态为`NOT_TESTED_FOR_ACTIVE_CORRECTION`。RegMix/Loss外部质量增量为`NOT_IDENTIFIABLE`。

## 历史中断边界（已被Q01C正式run取代）

最近一组模型产物是质量文件：`audit.json` 修改时间为2026-09-24 08:10:44，`normalization.json`为08:10:45，三份汇总CSV为08:10:46–47（本机时间，精确时间见恢复清单）。按当前 `quality_audit.main()` 的写出顺序，可确认持久化证据到 `summarize()`；其后的 `unresolved_indicator_diagnostics()` 尚无第一份预期输出。

上述mtime和中断判断只描述Q01C之前的历史旧产物，不能再代表当前质量模块状态。现已存在正式`verification.json`、行级Parquet、质量报告、阶段日志和检查点；原先无法定位的历史进程仍不得事后补造，但不再阻塞质量科学结果与工程恢复机制验收。`solution/outputs/evolution/`仍不存在；C01/C01-R1提供的是审计与候选输入，不等于已经完成演化建模。

## 本次恢复完成项

已读材料/代码/既有报告，保存源码与产物哈希清单；轻量一致性检查68项：65通过、3项失败。三项失败均涉及质量汇总有效分母，后续静态核查发现其与全分数非空断言不相容。未修改原数据、模型源码或旧输出；未拟合、未重跑交叉验证/重采样、未执行演化或优化。新增恢复产物见03。本轮到文档完成即停止。

## TASK-Q01A / Q01B 最新状态

- TASK-Q01A正式诊断目录仍保持`PARTIAL`和退出码2；该历史记录未改写。TASK-Q01A-R1只用已保存产物补证，未重新读取或解压A1–A3。
- 主控最终复审确认原R目录34个文件未变、复审开始时111个受保护项目文件未变；复审通过后，仅按授权更新本文件、04和05。
- R1科学诊断结果通过。历史全目录mtime因运行前没有快照而保留`NOT_VERIFIABLE`，不影响计数、掩码和分母的科学正确性。
- TASK-Q01B方法裁决已完成：主分析对11个主Q特征采用严格完整案例口径，但不删除底层记录；19条记录保留缺失标记和缺失原因，Q相关汇总必须同时报告总样本数与有效样本数。A1校准集域内中位数插补仅作为敏感性分析。Q01B裁决阶段本身未改代码；其后已由Q01C按该决定实施并验收。

## TASK-Q01C / R1 / R2最终状态

- 项目层统一登记为：**科学结果经Q01C验收可信，恢复与日志机制经R2补证后通过**。TASK-Q01C、Q01C-R1、Q01C-R2整体关闭；质量恢复与日志任务T02不再单列。
- 正式科学run为`solution/outputs/quality_q01c/20260924T215718+08/`，原manifest 56/56当前匹配；R1正式run 138/138匹配；R2正式run `diagnostics/TASK-Q01C-R2/20260925T004211+08/`的manifest 284/284匹配。
- R2以合成fixture证明P1/P2跨进程中后段恢复：P1在S30合法checkpoint后终止，P2复用S10/S11/S12/S20/S30且新增计算均为0，再完成S40/S50/S60。payload、config和code fingerprint三类损坏均由正常`--resume`硬停止。
- S60已经进入最终`stage_seconds`、`executed_stages`、`stage_terminal_events`和`stage_exit_codes`；manifest生成后没有登记文件继续变化。
- 历史正式Q01C主命令从未落盘，继续保留`NOT_VERIFIABLE`。R2自检中的code snapshot计数为0，以及保护快照路径分隔符导致的removed/added各476项，均由本次主控用现存文件独立复核：9项源码快照中抽查的关键6项逐字节一致，归一化路径后476项0缺失、0新增、0差异。两项属于检查报告盲点，不改变验收结论。

## TASK-C01 / C01-R1最终状态

- TASK-C01经C01-R1修正后通过并关闭。原C01目录46项manifest和R1目录18项manifest当前均匹配。
- C8事实口径：1958份JSON=1954成功+4失败，共1863目录；11724个任务槽位中11699个有限、25个缺失；模型×任务11160行，11135行有有限结果；宽表1860模型，其中1854个六任务完整、6个partial。
- `c8_directory_aggregate_corrected.csv`、`c8_model_task_aggregate_corrected.csv`、`c8_model_wide_corrected.csv`可作为后续候选输入。95个双文件目录的取舍、4个损坏JSON、身份/日期/单位及桥接口径等OOS问题仍需在相应建模分支前裁决。

## TASK-T06最终状态

- TASK-T06E-B原run的profile坐标与G4聚合缺陷由`diagnostics/TASK-T06E-B-R1/20260925T103130+08/`修正。22/22全拟合点复现，926条完成profile行的物理固定值与conditional值一致；MQ-add六个profile均为`PROFILE_FINITE_AND_SEPARATED`。
- MQ-add的G1=43/45、G2 leave-N改善33.13%、leave-D改善32.41%、G3=200/200、G4 corrected PASS，最终为`ACCEPT_B6_SOURCE_RELATION`，严格限B6来源内。MQ-eff eta触及1e-6下界，只作敏感性。
- P分支冻结`q_A*=0.5695341857475174`、21个情景、A/B bridge=`NOT_IDENTIFIABLE`。RegMix 1M来源内可用；60M/1B只作迁移，10B/70B只作估算；Q_mix与完整p不能分别识别。
- 集成run只填参数槽位，没有重拟合或优化。正式T07合同为`primary_model=M0_B1`、`quality_enabled=false`、`mixture_transport_enabled=false`；B6、B8、桥接和配比均分情景传播。

## 当前下一步

下一P0是最终论文整合与审阅。执行-PAPER必须从`paper/FINAL_RESULT_INDEX.md`进入，只使用T06、T07、T05、T08四份冻结接口；不再启动新的科学建模任务或重选结果。

## TASK-T07最终状态

- 正式run为`diagnostics/TASK-T07/20260925T113744+08/`。预算固定为1e18、1e20、1e22 FLOPs，H固定候选为2048、4096、8192、32768、131072，`H_crit=30000`。
- S00/H=2048三档条件最优分别为：`(N_B,D_B,Loss)=(0.078248576,1.993850677,3.553996156)`、`(0.625922700,24.925757775,2.609142026)`、`(5.202388053,299.893000000,2.143211279)`；最高预算触及D支持上界。
- 成本按实际N、D复算一致；最大相对预算越界`9.403629568e-13`，最大KKT residual `2.7932317030401693e-08`。Q与完整p没有同时自由优化，S17保持无数值最优。
- B1使用每预算80个整行draw，质量情景使用200个B1/B6条件整行组合，没有逐参数独立抽样或联合后验表述。正式manifest 39/39匹配，源码与snapshot一致。

## TASK-T05最终状态

- 正式run为`diagnostics/TASK-T05/20260925T113355+0800/`，最终资格`CONDITIONAL_ASSOCIATION_ONLY`。C8完整/partial/损坏为1854/6/4；损坏记录不赋分。
- 45个完整桥接模型含7个C5 High/Pythia主层和38个C6 Medium条件来源迁移层。C5为C6精确43行子集，C6 High不构成独立证据；Medium的D均未观测且未插补。
- 主层六任务和辅助均值全部选择CONSTANT。时间切点2024-09-01在指标前seal；时间外、留族和规模外证据不足，不允许升级为预测桥接，`time_trend.validated_for_extrapolation=false`。
- 分组登记未发现同模型跨训练/测试；独立verifier 28/28 PASS，manifest 34/34匹配，源码与snapshot一致。

## TASK-T08最终状态

- 正式run为`diagnostics/TASK-T08/20260925T142203+0800/`。预测原点由身份唯一、日期明确的C1/C2/C8记录和C8评测时间共同确定为2025-03-13；12/24个月时点为2026-03-13和2027-03-13。
- 历史规模增长支持只有7条观测N/D记录、1个模型族、6个相邻候选和1个有效族级区间，未达到3族/10区间门槛；三种增长率、未来N/D/Loss及benchmark进步均不可识别。
- 主层49条模型×目标分解全部使用CONSTANT，`scale_associated_component=0`；恒等式最大复算误差`3.55e-15`。这表示主样本不能支持benchmark规模预测项，不表示规模无效。
- 六任务向量分别保留，均值只作辅助；条件剩余项只作非规模关联残差。六类不确定性分开报告，时间外推固定`UNVALIDATED`。
- 独立verifier 32/32 PASS；内部检查0 FAIL；input manifest 30/30、output manifest 38/38当前匹配；8项源码与snapshot一致。

## 四问科学链状态

`Q1 CLOSED`、`Q2 CLOSED`、`Q3 CLOSED`、`Q4 CLOSED`。后续工作仅限论文全文整合、版式、引用、图表、复现附件和最终审阅。
