# EXPERIMENT RUN REGISTRY

审计时间：2026-09-25。  
分类：`CANONICAL`、`SUPERSEDED`、`FAILED`、`EXPLORATORY`、`DO_NOT_USE`。  
说明：`FAILED`不等于科学发现失败；科学拒绝结果若被正式冻结，可作为合格结果保留。

## 论文最终应使用的run

| 论文部分 | 唯一应使用的run |
|---|---|
| Q1质量主结果 | `solution/outputs/quality_q01c/20260924T215718+08/` |
| Q1规则敏感性 | `diagnostics/TASK-T03E/20260925T020032+08/` |
| Q1配比和Q2基础标度 | `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/`，其B侧来自T06E-B-R1，P侧来自T06E-P |
| C8底座 | `diagnostics/TASK-C01/20260924T175553+08/` + `diagnostics/TASK-C01-R1/20260924T225308+08/` |
| Q2质量条件关系 | `diagnostics/TASK-T06E-B-R1/20260925T103130+08/` |
| Q2跨源/配比情景 | `diagnostics/TASK-T06E-P/20260925T075729+08/` |
| Q3 | `diagnostics/TASK-T07/20260925T113744+08/` |
| Q4桥接 | `diagnostics/TASK-T05/20260925T113355+0800/` |
| Q4分解/未来资格 | `diagnostics/TASK-T08/20260925T142203+0800/` |

## 任务注册表

| task | run_id | 目的 | 输入 | 主要输出 | checks | verifier | manifest | R1/R2 | 最终状态 | 分类 | 论文章节 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TASK-Q01A | `20260924T142229+08` | 质量缺失模式诊断 | A1–A3旧质量产物 | 缺失交叉表、已知域比较 | 原run PARTIAL | 后续R1补验 | 有 | R1 | 原run历史 | `SUPERSEDED` | 4.1/4.2追溯 |
| TASK-Q01A-R1 | `20260924T150854+08` | 掩码/分母精准小修 | Q01A产物 | 修正缺失表 | 21 PASS, 1 NOT_VERIFIABLE | 有独立verify | 有 | R1 | 通过复审 | `CANONICAL`（Q01A审计） | 4.1/4.2 |
| TASK-Q01B | 无run | 缺失处理策略裁决 | Q01A/R1 | 决策文档 | 文档审查 | 不适用 | 不适用 | 无 | 方法已裁决 | `METHOD_ONLY` | 4.1 |
| TASK-Q01C | `20260924T213625+08`…`20260924T215211+08` | 质量流水线早期尝试 | A1–A3 | 早期失败/不完整产物 | FAILED/INCOMPLETE | 部分 | 部分 | 无 | 不可进入正文 | `DO_NOT_USE` | 无 |
| TASK-Q01C | `20260924T215718+08` | 全量质量评分正式run | A1–A3 | 272505行级得分；261086唯一键；261067主Q有效 | 20/20 PASS | 独立verify 20/20 | 56/56匹配 | R2 | 验收关闭 | `CANONICAL` | 4.1–4.4 |
| TASK-Q01C-R1 | `20260924T225031+08`…`20260924T225550+08` | 恢复/检查点工程修复 | Q01C产物 | interruption/rejection证据 | 多轮失败到补证 | R2最终验收 | 有 | R1后R2 | 中间工程历史 | `SUPERSEDED`（由R2补证） | 附录复现 |
| TASK-Q01C-R2 | `20260925T004211+08` | 恢复一致性与S60收口 | Q01C/R1 | checkpoint链、三类拒绝、S60 | 13/13 PASS | 独立verify | 284项匹配 | R2 | 通过关闭 | `CANONICAL`（工程） | 附录复现 |
| TASK-C01 | `20260924T175553+08` | C1–C10审计、C8解析/聚合 | C1–C10 | 原始C8聚合、损坏清单 | 原检查有小修项 | C01-R1重验 | 有 | R1 | 原始产物保留 | `CANONICAL`（原始解析）+检查语义`SUPERSEDED` | Q4样本底座 |
| TASK-C01-R1 | `20260924T225308+08` | C8聚合与检查器修正 | C01产物 | corrected目录/模型任务/宽表 | 79 PASS,0 FAIL;5 NOT_CHECKED;4 NOT_VERIFIABLE | 39/39 PASS | 18/18匹配 | R1 | 通过关闭 | `CANONICAL` | Q4样本底座 |
| TASK-T03 | 无独立run | 14规则/DSIR方法设计 | Q01C/语义源 | 预注册设计 | 文档审查 | 不适用 | 不适用 | T03E | 方法完成 | `METHOD_ONLY` | 4.5 |
| TASK-T03E | `20260925T015757+08`、`20260925T015930+08` | 预注册规则稳定性 | Q01C行级数据 | 早期完整但被重跑取代 | 部分 | 无最终地位 | 有 | 无 | 历史 | `SUPERSEDED` | 无 |
| TASK-T03E | `20260925T020032+08` | 正式规则敏感性验证 | Q01C Parquet | bootstrap、holdout、extension状态 | 22 PASS+1 finalizer | 17/17 PASS | 53/53匹配 | finalizer | 通过关闭 | `CANONICAL` | 4.5 |
| TASK-T06E-B | `20260925T075743+08`…`20260925T095019+08` | B分支构建过程 | B1/B6/B7/B8 | 多轮中间产物 | 过程性 | 部分 | 部分 | 无 | 历史 | `EXPLORATORY`/`DO_NOT_USE` | 无 |
| TASK-T06E-B | `20260925T100306+08` | B1/B6/B7/B8原始正式科学run | B表 | MQ-add/MQ-eff、G1–G4、B7/B8 | 完整；G4 FAIL | 有独立verifier | 104项匹配 | R1 | 科学结果为`REJECT_TO_M0_6` | `SUPERSEDED`（profile/G4由R1取代） | Q2追溯 |
| TASK-T06E-B-R1 | `20260925T103130+08` | profile坐标和G4修正 | B原run | 22/22复现；MQ-add G4 PASS；k_add | R1 PASS | 独立verifier | 86/86匹配 | R1 | 通过关闭 | `CANONICAL`（Q2 B侧） | 5.3–5.5 |
| TASK-T06E-P | `20260925T075729+08` | 质量锚点、H桥接、RegMix运输、21情景 | A质量、B6、RegMix | q_A*、H0–H4、Q-p识别、情景registry | 32/32 PASS | 12/12 PASS | 49/49匹配 | 无 | 通过 | `CANONICAL`（Q2 P侧） | 5.5–5.8、Q3情景接口 |
| TASK-T06E-INTEGRATE | `20260925T110904+08` | 分支集成与T07合同冻结 | B-R1、P | 21情景填槽、T07合同 | 21/21 PASS | 21/21 PASS | 23/23匹配 | 无 | COMPLETE | `CANONICAL`（Q2总入口） | Q2、Q3输入 |
| TASK-T05 | `20260925T113355+0800` | Loss–Benchmark桥接与历史分层验证 | C01/R1、C4–C6 | 45模型桥接；7主层；六任务CONSTANT；资格 | checks PASS | 28/28 PASS | 34/34匹配 | 无 | 通过关闭 | `CANONICAL`（Q4桥接） | 7.2–7.3 |
| TASK-T07 | `20260925T113744+08` | 三档预算资源配置优化 | T06合同、C7 | 21情景×3预算×5H；KKT；draw | 18项PASS | 39/39 PASS | 39/39匹配 | 无 | 通过关闭 | `CANONICAL`（Q3） | 6.1–6.13 |
| TASK-T08 | `20260925T141338+0800`、`20260925T141913+0800` | Q4早期构建 | T05/T07 | 早期产物 | 过程性 | 部分 | 部分 | 无 | 历史 | `SUPERSEDED` | 无 |
| TASK-T08 | `20260925T142203+0800` | Q4分解、历史分层、未来资格 | T05/T07/T06/C01 | 49分解、931分层、42未来情景、六类不确定性 | 18项；0 FAIL | 32/32 PASS | 38/38匹配 | 无 | 通过关闭 | `CANONICAL`（Q4最终） | 7.1–7.12 |

## 运行证据完整性

独立复核8个正式manifest共347项：缺失0、大小不一致0、SHA256不一致0。

- Q01C：56/56
- T03E：53/53
- T05：34/34
- T06E-B-R1：86/86
- T06E-INTEGRATE：23/23
- T07：39/39
- T08：38/38
- C01-R1：18/18

## 不得进入最终论文的run/目录

- `diagnostics/**/_aborted_attempts/**`
- `diagnostics/TASK-Q01C-R1/20260924T225031+08` 至 `225339+08` 的失败/拒绝路径，除非作为恢复性附录证据
- `diagnostics/TASK-T03E/20260925T015757+08`、`20260925T015930+08`
- `diagnostics/TASK-T06E-B/20260925T075743+08` 至 `20260925T095019+08`
- `diagnostics/TASK-T08/20260925T141338+0800`、`20260925T141913+0800`
- `solution/outputs/quality_q01c/20260924T213625+08` 至 `214745+08`
- `tmp/**`
- 所有未进入manifest的临时CSV/PNG/日志
