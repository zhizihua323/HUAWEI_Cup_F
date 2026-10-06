# FINAL RESULT SOURCE OF TRUTH

日期：2026-09-25。  
优先级规则：论文数字只能从本文件列出的冻结接口和正式run读取；登记表、旧run、superseded run和聊天记录不能自行覆盖。

## 1. Q1唯一真源

Q1没有单独一份名为`Q1_RESULT_FREEZE.md`的文件，实际唯一真源是三部分：

1. **主质量科学run**：`solution/outputs/quality_q01c/20260924T215718+08/`
   - 272505物理记录；261086唯一键；261067主Q有效；19缺失。
   - 主Q为11特征严格完整案例、三组等权。
   - 质量记录、有效分母、组统计、冲突诊断以`domain_summary.csv`、`quality_features_scores.parquet`、`audit.json`为准。
2. **规则敏感性正式run**：`diagnostics/TASK-T03E/20260925T020032+08/`
   - `Q_C=Q_baseline*(1-0.02P)`仅是预注册敏感性候选，不是正式主Q。
   - c4/commoncrawl/wikipedia的holdout稳定性和extension active-correction未测试状态以本run为准。
3. **Q1配比与跨尺度运输**：`paper/T06_RESULT_FREEZE.md`
   - 1M MSE改善55.03%；Spearman=0.62507。
   - 60M RMSE≈1.5173；1B RMSE≈3.1889；仅运输诊断。
   - 6域映射、11域未映射；Q_mix与p独立效应不可识别。

**Q1缺口**：没有覆盖扩展集冲突稳定性的冻结结果；A18原文可靠性检查没有结果。

## 2. Q2唯一真源

**主导文件**：`paper/T06_RESULT_FREEZE.md`  
**正式集成run**：`diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/`

冻结内容：

- 主模型：B1来源内`M0_B1`。
- 参数：E=1.6897975629820348；A=0.3539803206065571；B=1.2403055835426349；alpha=0.339976581941082；beta=0.2798781285468448。
- B6质量候选：`k_add=0.3544081081063713`；G1=43/45；G2改善33.13%/32.41%；G3=200/200；G4满秩。
- A/B质量桥接：`NOT_IDENTIFIABLE`；H1–H3情景；H4只保留方向。
- RegMix向B1：`SCENARIO_ONLY`；Q_mix与p不能独立解释。
- B8：`CONFLICT_EVIDENCE`。
- 质量模型只在B6来源内、0.1≤Q_score≤0.6有条件支持；MQ-eff为弱可识别敏感性。

**冲突记录**：Q1_Q2稳定正文和正式T06都承认不存在统一可识别的L(N,D,Q,p)，但`paper/outline.md`、`paper/open_questions.md`仍把它写成未完成的BLOCKED/HOLD项。此为文档状态冲突，不是数字冲突；科学真源仍为T06。

## 3. Q3唯一真源

**主导文件**：`paper/T07_RESULT_FREEZE.md`  
**正式run**：`diagnostics/TASK-T07/20260925T113744+08/`

冻结内容：

| 预算 | N_B | D_B | Loss | 支持状态 |
|---:|---:|---:|---:|---|
| 1e18 | 0.078248576 | 1.993850677 | 3.553996156 | 内点 |
| 1e20 | 0.625922700 | 24.925757775 | 2.609142026 | 内点 |
| 1e22 | 5.202388053 | 299.893000000 | 2.143211279 | D触B1支持上界 |

- Hcrit=6/eta=30000。
- 最大预算相对越界9.403629568e-13；最大KKT residual=2.7932317030401693e-8。
- Q为`NOT_IDENTIFIED_NOT_OPTIMIZED`；p为`FIXED_P0_NOT_OPTIMIZED`。
- S01/S03质量成本、S14/S15/S16配比、S17 B8均为情景或冲突。
- M0_B1参数不确定性为80个整行draw；质量情景为200个B1/B6整行组合，不是联合后验。

**冲突记录**：旧图表登记仍把Q3图标为BLOCKED；与T07正式run冲突，应废弃旧状态。

## 4. Q4唯一真源

**桥接**：`paper/T05_RESULT_FREEZE.md` + `diagnostics/TASK-T05/20260925T113355+0800/`  
**分解/未来**：`paper/T08_RESULT_FREEZE.md` + `diagnostics/TASK-T08/20260925T142203+0800/`

冻结内容：

- bridge：`CONDITIONAL_ASSOCIATION_ONLY`。
- 样本：C8完整1854、partial 6、损坏4；桥接45；主层7；迁移层38。
- 六任务主模型均为`CONSTANT`；六任务均值和条件区间以T08为准。
- scale_associated_component=0；conditional_remainder只能称条件剩余项/非规模关联残差。
- time trend：`UNVALIDATED_FOR_EXTRAPOLATION`。
- future progress：`NOT_IDENTIFIABLE_PROGRESS`；12/24个月时点为2026-03-13/2027-03-13，但不给数值增量。
- 六类不确定性分列，不合成单一置信区间。

## 5. 数字冲突扫描结果

未发现T06/T07/T05/T08与`FULL_MANUSCRIPT_V1.md`之间的核心数字冲突。已逐项核对：

- Q1：272505、261086、261067、19、55.03%、0.62507、1.5173、3.1889。
- Q2：E/A/B/alpha/beta、k_add、G1–G4、q_A*。
- Q3：三档N/D/Loss、Hcrit、KKT residual、预算越界。
- Q4：1854/6/4、45/7/38、六任务基线、49×0、3.55e-15、2025-03-13、2026-03-13、2027-03-13。

## 6. 需要统一的状态冲突

以下文件不是科学真源，但会误导后续作者：

| 文件 | 过期/冲突内容 | 处理 |
|---|---|---|
| `00_PROJECT_BRIEF.md` | 称当前没有项目论文正文 | 更新为V1已存在、待成品化 |
| `paper/FINAL_RESULT_INDEX.md` | 写Q4尚待撰写 | 已有Q4_STABLE_BODY和FULL_MANUSCRIPT_V1，需更新 |
| `paper/outline.md` | Q3/Q4 BLOCKED，参考文献HOLD | 标为历史或更新 |
| `paper/open_questions.md` | OQ-01…OQ-18大多已关闭 | 更新关闭状态 |
| `paper/data_sources.md` | Q1仍为PARTIAL_OUTPUT、A18 NOT_PROCESSED | 区分“已产出”与“仍缺的文本验证” |
| `paper/symbols.md` | Q_A、Q_B、Q3/Q4符号仍标PARTIAL/RESERVED | 与V1统一 |
| `paper/figure_table_registry.md` | Q3/Q4仍BLOCKED | 重建最终图表登记 |
| `solution/README.md` | 当前阶段仍写“数据审计和首轮基线” | 更新项目阶段与复现入口 |
| `solution/config.json` | `stage=audit_and_first_baselines` | 更新或标记为历史配置 |
