# Q1/Q2论文冲刺写作 Handoff

- 状态：COMPLETE_STOPPED
- 日期：2026-09-25
- 停止条件：已完成稳定章节与Q1/Q2正文，等待T07/T05结果，不启动后续任务。

## 1. 交付文件

| 文件 | 内容 |
|---|---|
| paper/manuscript/Q1_Q2_STABLE_BODY.md | 问题重述、问题分析、数据说明、模型假设、符号说明、问题一完整正文、问题二完整正文、问题二结果分析、模型优缺点与限制 |
| paper/manuscript/source_map_q1_q2.md | 正文数值与状态的来源文件、字段和位置映射 |
| paper/manuscript/figure_table_placeholders_q1_q2.md | Q1/Q2图表占位符、状态与编号规则 |

## 2. 问题二正式口径

问题二严格采用paper/T06_RESULT_FREEZE.md：

- 正式主模型：M0_B1，quality_enabled=false，mixture_transport_enabled=false。
- B6质量候选：MQ-add，仅获B6来源内条件资格。
- A/B桥接：NOT_IDENTIFIABLE。
- H1—H3：SCENARIO_ONLY，不是估计映射。
- RegMix向B1：SCENARIO_ONLY，不是跨尺度验证。
- Q_mix与完整p：不可作为两个独立自由坐标。
- B8：CONFLICT_EVIDENCE，不表示真实机制反转。
- MQ-eff：敏感性候选，不能替代MQ-add。

## 3. 问题一正式口径

问题一采用Q01C正式科学run和T03E冻结验证：

- 正式主质量：Q_baseline。
- 主质量11特征，三组组内等权、组间等权。
- 主质量严格完整案例，缺失不填零、不重分配权重。
- Q_C只作规则敏感性，不替换Q_baseline。
- 1M配比关系具有同尺度支持；60M/1B只作运输诊断；10B/70B为估算非真值。
- A18文本验证和Q_C扩展主动修正未冻结，正文保留占位符。

## 4. 明确未写入的内容

- 未填写问题三预算最优配置、结构转移或统一最优模型。
- 未填写问题四贡献分解、Loss—Benchmark桥接参数或未来12/24个月预测。
- 未把A/B质量映射写成已估计参数。
- 未把MQ-add写成统一质量因果效应。
- 未把RegMix写成跨规模验证。
- 未把B8写成机制反转。
- 未写最终摘要。

## 5. 校验状态

- 正文禁用表述扫描：T06禁止句的肯定式未出现。
- 所有引用数值均在source_map_q1_q2.md或paper/T06_RESULT_FREEZE.md中有实际文件来源。
- 图表占位符均标明READY、PLANNED、EXISTING_NOT_FINAL或BLOCKED。
- 00–05项目管理文档未被本任务修改。
- 其他TASK输出目录未被本任务修改。

## 6. 等待项

- T07：问题三预算优化与结构转移。
- T05：Loss—Benchmark桥接与历史分层验证。
- 后续任务：A18文本验证、C模块建模、问题四预测与最终论文收口。

## 7. Claim-evidence map

| 主要论断 | 证据 | 状态 |
|---|---|---|
| Q_baseline是A侧正式操作性质量指标 | Q01C正式run、domain_summary.csv、audit.json、verification.json | supported，限于操作性评分 |
| 严格完整案例与缺失显式传播已完成 | Q01C audit/domain summary与独立验证 | supported |
| Q_C只作规则敏感性 | T03E冻结规则与留出验证 | supported，非正式主质量 |
| RegMix在1M同尺度具有预测支持 | T06 P分支regmix_fixed_model_validation.csv | supported，限1M |
| RegMix跨尺度运输尚未验证 | 60M/1B运输记录与T06冻结状态 | supported boundary |
| M0_B1是问题二正式主模型 | T06_RESULT_FREEZE.md与T06集成contract | supported，来源内条件 |
| MQ-add仅获B6来源内资格 | B-R1 G1—G4与T06集成 | supported，来源内 |
| A/B质量尺度不可识别 | P分支bridge qualification、T06合同 | supported non-identifiability |
| H1—H3仅为情景 | bridge scenarios与T06合同 | scenario-only |
| Q_mix与完整p不能独立优化 | p_q_identifiability与T06合同 | supported non-identifiability |
| B8是冲突证据 | B6/B8共同支持方向冲突 | unresolved conflict，未合并 |


---

# Q3写作交接（2026-09-25）

- 状态：COMPLETE_STOPPED
- 正式口径：paper/T07_RESULT_FREEZE.md
- 正式证据：diagnostics/TASK-T07/20260925T113744+08/
- 新增文件：
  - paper/manuscript/Q3_STABLE_BODY.md
  - paper/manuscript/source_map_q3.md
  - paper/manuscript/figure_table_placeholders_q3.md
- 三档主表已锁定为1e18、1e20、1e22；1e22的D_B=299.893000000为B1支持上界。
- Q3主模型只优化N_B、D_B；Q与p不优化，所有质量/配比结果标记SCENARIO_ONLY。
- KKT、成本分项、H敏感性、三类质量成本、配比运输、B8冲突和参数draw均已写入正文。
- 禁用表述扫描：0命中。
- T07正式数字复核：主表、H表、质量成本、配比运输、不确定性均与T07 CSV/JSON一致。
- 未使用T05/T08结果，未填写问题四结果。
- 停止等待T08冻结结果。
