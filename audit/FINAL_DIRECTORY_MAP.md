# FINAL DIRECTORY MAP

审计时间：2026-09-25 16:41 +08:00  
范围：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace`  
方式：只读扫描目录、文本、PDF、DOCX、DOC COM 模板、JSON/CSV/图像元数据；未运行拟合、优化、bootstrap 或训练。

## 1. 根目录资产图

| 路径 | 角色 | 正式 | 冻结 | 仍在使用 | 历史/废弃 | 论文需要 | 附件需要 | 审计判断 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `00_PROJECT_BRIEF.md` | 项目简报/入口 | 管理文档 | 否 | 是 | 部分段落已过期 | 间接 | 是 | 仍有用，但正文已存在后“当前没有本项目论文正文”等状态过期 |
| `01_PROJECT_STATUS.md` | 当前状态 | 管理文档 | 否 | 是 | 否 | 间接 | 是 | Q1–Q4关闭状态与正式run一致；仍以“下一步PAPER”描述 |
| `02_DECISIONS.md` | 决策记录 | 管理文档 | 否 | 是 | 否 | 间接 | 是 | 科学口径与T06/T07冻结合同基本一致 |
| `03_DATA_CATALOG.md` | 数据/产物目录 | 管理文档 | 否 | 是 | 否 | 间接 | 是 | 含正式run入口和输出清单，适合作为目录底图 |
| `04_TASK_QUEUE.md` | 任务队列 | 管理文档 | 否 | 是 | 下一步状态已过期 | 间接 | 是 | 仍写“下一P0为PAPER”，实际V1已生成 |
| `05_REVIEW_LOG.md` | 核验日志 | 管理文档 | 否 | 是 | 否 | 间接 | 是 | 保留P04/P07未解决项，这是当前重要风险来源 |
| `F题/` | 官方题目、数据说明、原始附件 | 原始输入 | 只读 | 是 | 否 | 是 | 否（原始数据不重传） | 题目和 `real_attachments/` 的真源；原数据约526 MB |
| `参考资料/` | 模板、成品论文、AI检测提示 | 参考材料 | 否 | 是 | 非项目结果 | 仅格式/结构参考 | 否 | 8个文件、约19.31 MB；两篇成品论文PDF实际可读 |
| `diagnostics/` | 正式run、修正run、失败run | 一部分正式 | 部分是 | 是 | 大量中间/失败run | 是 | 仅精选 | 2738文件、约486 MB；正式run和失败run混存，附件必须筛选 |
| `solution/` | 源码、首轮基线、Q01C正式质量run | 一部分正式 | 部分是 | 是 | 早期基线/临时run多 | 是 | 仅精选 | 1515文件、约1.61 GB；`README.md` 和 `config.json` 仍停留在首轮基线阶段 |
| `paper/` | 正文、冻结接口、登记表 | 论文工作区 | 冻结接口是 | 是 | 部分登记表过期 | 是 | 是 | 26文件、约0.27 MB；只有Markdown，无最终DOCX/PDF/图文件 |
| `evidence/` | 首轮基线的证据汇总 | 历史正式摘要 | 否 | 仅追溯 | 是 | 仅追溯 | 可选 | 最终数字应以T05–T08冻结接口为准 |
| `recovery/` | 恢复审计 | 历史审计 | 否 | 仅追溯 | 是 | 否 | 可用于复现说明 | 保留恢复时的原始核验背景 |
| `tmp/` | 临时、重构、fixture、环境缓存 | 否 | 否 | 否 | 是 | 否 | 否 | 约23.61 MB；附件应排除。扫描 `tmp/environment_review/deps` 时部分目录权限受限 |

## 2. `paper/` 关键资产

| 路径 | 角色 | 状态 |
|---|---|---|
| `paper/FINAL_RESULT_INDEX.md` | 四问最终科学结果入口 | 正式；指定T06/T07/T05/T08为唯一科学真源 |
| `paper/T06_RESULT_FREEZE.md` | Q2冻结接口 | 正式、冻结 |
| `paper/T07_RESULT_FREEZE.md` | Q3冻结接口 | 正式、冻结 |
| `paper/T05_RESULT_FREEZE.md` | Q4桥接冻结接口 | 正式、冻结 |
| `paper/T08_RESULT_FREEZE.md` | Q4分解/未来资格冻结接口 | 正式、冻结 |
| `paper/manuscript/FULL_MANUSCRIPT_V1.md` | 当前全文V1 | 完整初稿级；非提交稿 |
| `paper/manuscript/Q1_Q2_STABLE_BODY.md` | Q1/Q2稳定正文 | 科学数字基本冻结；有A18/扩展冲突占位 |
| `paper/manuscript/Q3_STABLE_BODY.md` | Q3稳定正文 | 与T07一致；有排版占位 |
| `paper/manuscript/Q4_STABLE_BODY.md` | Q4稳定正文 | 与T05/T08一致；写明无可识别未来数值 |
| `paper/manuscript/source_map_q*.md` | 数字到证据映射 | 有效；Q4使用T05/T08 |
| `paper/manuscript/FINAL_CLAIM_EVIDENCE_AUDIT.md` | Claim–Evidence审计 | 有效，但只覆盖核心claim |
| `paper/manuscript/FINAL_FIGURE_TABLE_PLAN.md` | 最终图表计划 | 最新计划：7正文图、10正文表、2附表；均未完成最终版 |
| `paper/result_registry.md` | 结果登记 | 含历史段落和后续覆盖映射；不能单独作为最终数字真源 |
| `paper/figure_table_registry.md` | 图表登记 | 旧状态仍含大量`BLOCKED`，与T05–T08已完成事实冲突；必须重建 |
| `paper/outline.md` | 早期总纲 | 多数状态已过期，仍写Q3/Q4 BLOCKED |
| `paper/open_questions.md` | 早期问题清单 | 大量OQ已由正式run关闭，文件未同步 |
| `paper/data_sources.md` | 数据来源 | Q01C/T03E完成后仍保留PARTIAL/NOT_PROCESSED旧口径 |
| `paper/symbols.md` | 符号约定 | 部分“RESERVED/PARTIAL”状态过期 |

## 3. 正式run目录

| 任务 | 正式run | 角色 |
|---|---|---|
| Q1质量恢复与计分 | `solution/outputs/quality_q01c/20260924T215718+08/` | Q1主质量科学run；56项manifest复核匹配 |
| Q1规则敏感性 | `diagnostics/TASK-T03E/20260925T020032+08/` | 预注册规则稳定性；53项manifest复核匹配 |
| C侧数据审计 | `diagnostics/TASK-C01/20260924T175553+08/` | 原始C8解析产物 |
| C侧聚合修正 | `diagnostics/TASK-C01-R1/20260924T225308+08/` | C8修正聚合；18项manifest复核匹配 |
| Q2质量关系 | `diagnostics/TASK-T06E-B/20260925T100306+08/` | 原科学run；profile/G4由R1取代 |
| Q2质量关系修正 | `diagnostics/TASK-T06E-B-R1/20260925T103130+08/` | MQ-add来源内正式通过；86项manifest复核匹配 |
| Q2配比/桥接情景 | `diagnostics/TASK-T06E-P/20260925T075729+08/` | 21情景冻结合同 |
| Q2正式集成 | `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/` | T07合同；23项manifest复核匹配 |
| Q3优化 | `diagnostics/TASK-T07/20260925T113744+08/` | 三档预算；39项manifest复核匹配 |
| Q4桥接 | `diagnostics/TASK-T05/20260925T113355+0800/` | CONDITIONAL_ASSOCIATION_ONLY；34项manifest复核匹配 |
| Q4分解/未来资格 | `diagnostics/TASK-T08/20260925T142203+0800/` | 常数基线、NOT_IDENTIFIABLE_PROGRESS；38项manifest复核匹配 |

## 4. 目录层面结论

1. 科学证据主体存在，不是只有计划：Q1、Q2、Q3、Q4均有实际run、源码快照、检查、verifier和manifest。
2. 论文交付物主体不存在：没有最终DOCX/PDF、正式排版源、最终图、正式参考文献、正式附件包。
3. 管理文档与论文工作区存在明显状态冲突：旧计划文件仍写BLOCKED/HOLD，而正式run已冻结。
4. 当前最重要的是把“科学结论冻结”与“可提交成品”之间的缺口补齐，而不是继续增加模型。

## 5. 本次独立manifest复核

对Q01C、T03E、T05、T06E-B-R1、T06E-INTEGRATE、T07、T08、C01-R1共347个manifest登记项逐项复核路径、大小和SHA256：缺失0、大小不一致0、哈希不一致0。
