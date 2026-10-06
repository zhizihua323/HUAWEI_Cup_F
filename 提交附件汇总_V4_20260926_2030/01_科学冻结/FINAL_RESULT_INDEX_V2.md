# FINAL RESULT INDEX V2

日期：2026-09-25  
状态：`SCIENCE_CLOSED`  
用途：论文、图表和提交附件的最终科学结果索引。若本文件与旧状态登记、聊天记录或候选说明冲突，以本文件列出的最终冻结接口及其正式 run 为准。

## 最终状态

| 问题 | 最终状态 | 最终主接口 |
|---|---|---|
| Q1 | `CLOSED_WITH_LIMITATION` | `paper/Q1_GAP_RESULT_FREEZE.md` |
| Q2 | `CLOSED_WITH_LIMITATION` | `paper/Q2_GAP_RESULT_FREEZE.md` |
| Q3 | `CLOSED_WITH_LIMITATION` | `paper/T07_RESULT_FREEZE.md` |
| Q4 | `CLOSED_WITH_SCENARIO_LIMITATION` | `paper/Q4_GAP_RESULT_FREEZE.md` |

## Q1：质量评价、冲突与配比

按下列顺序读取：

1. `paper/Q1_GAP_RESULT_FREEZE.md`：扩展冲突稳定性与作者盲审的最终接口；
2. `solution/outputs/quality_q01c/20260924T215718+08/`：11特征主Q、分母和行级结果；
3. `diagnostics/TASK-T03E/20260925T020032+08/`：规则修正敏感性；
4. `paper/T06_RESULT_FREEZE.md`：RegMix同尺度检验及跨尺度运输边界。

G1证据：

- 扩展稳定性与抽样seal：`diagnostics/TASK-G1/20260925T204300+08/`；
- 作者评分解析与统计：`diagnostics/TASK-G1/20260925T223500+08/`。

最终资格：主Q是A侧操作性质量代理；扩展冲突仅`PARTIALLY_STABLE`；人工核验未显示稳定正向一致性，不能把Q称为人工真值。

## Q2：来源内缩放律与条件广义表达

按下列顺序读取：

1. `paper/Q2_GAP_RESULT_FREEZE.md`：B2/B3/B4/B5/B9/B10强制验证及最终资格；
2. `paper/T06_RESULT_FREEZE.md`：M0_B1、B6质量关系、A/B尺度桥接和RegMix运输的冻结定义；
3. `diagnostics/TASK-G2/20260925T195336+08/`：行级预测、来源指标、支持域和独立复算。

最终资格：`M0_B1`为B1来源内主模型；正式表达只能称“分层估计、联合表达的条件广义标度律”。不得称统一的四变量模型已获多源验证。G2没有改变T07数值输入。

## Q3：算力预算下的条件优化

唯一正式接口：

- `paper/T07_RESULT_FREEZE.md`；
- `diagnostics/TASK-T07/20260925T113744+08/`。

最终资格：冻结M0_B1、B1经验支持、指定预算和外生H下的条件最优N/D。Q未识别且未优化，p固定为p0；质量、配比和B8均只作情景或冲突分析。

## Q4：Benchmark分解与未来情景

按下列顺序读取：

1. `paper/Q4_GAP_RESULT_FREEZE.md`：25模型直接Benchmark候选、端点分解和12/24月数值情景的最终接口；
2. `paper/T05_RESULT_FREEZE.md`：Loss–Benchmark桥接资格；
3. `paper/T08_RESULT_FREEZE.md`：7模型主可比层、历史compute增长不可识别及六类不确定性；
4. `diagnostics/TASK-G4/20260925T195716+0800/`：预注册seal、模型选择、预测、分解与独立复算。

G4是T08之后的缺口闭合：它没有升级Loss桥接，也没有把情景变成已验证预测。直接Benchmark情景的预测原点为`2025-01-28`，12/24月日期为`2026-01-28`和`2027-01-28`；T08的`2025-03-13`仅属于原历史compute增长识别接口。论文不得混用两套原点。

最终资格：所有G4未来数值均为`SCENARIO_ONLY_UNVALIDATED`；M2全部未通过升级门槛；Loss到Benchmark数值转换次数为0。

## 版本优先级与禁止回退

- `paper/FINAL_SCIENTIFIC_FREEZE.md`给出最终裁决和不可越过的资格边界。
- `paper/FINAL_PAPER_PATCH_CONTRACT.md`给出SHOWCASE正文、图和表的强制替换规则。
- `audit/CURRENT_STATE_SNAPSHOT_20260925.md`、`audit/FINAL_RESULT_SOURCE_OF_TRUTH.md`和`audit/QUESTION_REQUIREMENT_COVERAGE.md`保留为G1/G2/G4执行前的历史审计；其中关于缺口仍未完成的状态已被本次验收取代。
- `paper/FINAL_RESULT_INDEX.md`为旧版索引，不得覆盖本文件。
- 不得从旧run、执行器口头输出、参考论文或SHOWCASE旧图表中另选数字。
- 自本文件生效起，禁止新增科学实验、重拟合、重选模型或移动验收阈值。

