# TASK-PAPER-PREFLIGHT：参考文献与成品结构

日期：2026-09-25。状态：正式并行预制施工单。本任务可与TASK-G1、TASK-G2、TASK-G4并行，但不得抢先写入这些任务尚未冻结的科学结论。

## 【任务目标】

在不改变任何科学数字的前提下，完成提交级论文的结构、引文、公式、图表、AI披露和编辑问题预制，使科学冻结后可以立即进入DOCX/PDF制作。

## 【必须读取】

- 原题与《数据说明》；
- 官方论文模板与论文格式规范；
- `paper/manuscript/FULL_MANUSCRIPT_V1.md`
- `paper/manuscript/Q1_Q2_STABLE_BODY.md`
- `paper/manuscript/Q3_STABLE_BODY.md`
- `paper/manuscript/Q4_STABLE_BODY.md`
- `paper/T06_RESULT_FREEZE.md`、`T07_RESULT_FREEZE.md`、`T05_RESULT_FREEZE.md`、`T08_RESULT_FREEZE.md`
- `paper/FINAL_RESULT_INDEX.md`
- `audit/FINAL_PROJECT_STATE.md`、`QUESTION_REQUIREMENT_COVERAGE.md`、`FINAL_RESULT_SOURCE_OF_TRUTH.md`、`FINAL_ACTION_PLAN.md`
- `参考资料/2026华为杯研赛F题成品参考论文！.pdf`

参考成品论文只用于结构、信息密度、摘要组织、公式编号、图表呈现、检验章节、参考文献、AI声明和成品观感。禁止复制其文字、数值、参数、图、模型结论或未核验参考文献。

## 【输出目录与修改边界】

- 运行目录：`diagnostics/TASK-PAPER-PREFLIGHT/<run_id>/`
- 论文预制目录：`paper/preflight/`
- 不修改`FULL_MANUSCRIPT_V1.md`和三份STABLE_BODY原文件；
- 允许生成`paper/preflight/FULL_MANUSCRIPT_PREFLIGHT.md`作为清理副本；
- 不修改00–05、旧冻结接口、正式run或任何科学数字；
- 不生成最终DOCX/PDF，不画最终图。

## 【工作内容】

### 1. 成品结构与章节骨架

建立最终章节骨架，至少覆盖：封面、摘要、关键词、目录、引言/背景、问题重述、总体分析与流程图、模型假设、符号说明、Q1–Q4、统一模型检验与灵敏度、模型评价、改进/推广、参考文献、AI工具使用声明、附录/复现说明。

骨架须标注每节的数据来源、冻结接口、预期字数、图表、公式和依赖状态。G1/G2/G4位置只能放稳定占位符，不能预写结果。

### 2. 真实参考文献检索与核验

- 以题目已列文献为起点，检索经典标度律、Chinchilla、RegMix、Pythia、Benchmark/C8对应评测、数据质量评价、组成数据回归、前沿/hedonic/quantile方法等正式来源；
- 优先原始论文、正式会议/期刊和官方数据/模型文档；
- 每条至少核验作者、标题、年份、载体、DOI/正式URL；
- 不得引用搜索摘要、AI输出或参考成品论文的二手书目而不核验；
- 建立claim-to-citation map，区分“需要引用的外部事实”和“本项目数据结果”；
- 未核验条目标`UNVERIFIED`且不得进入最终正文参考文献。

### 3. 公式编号方案

建立全局公式registry，包含公式ID、所属问题、首次出现章节、符号、单位、来源/推导、是否需要正文编号。Q1–Q4公式编号必须唯一、连续或按章连续，不能保留Markdown散乱占位。

### 4. 图表registry

建立正文与附录图表registry，至少包含：编号、标题、回答的问题、源冻结接口、源CSV/JSON、绘图字段、单位、资格标签、正文引用位置、制作状态。图表不得从聊天或参考论文取数。

### 5. AI使用披露

根据官方规范准备披露草稿，列出实际使用的AI工具、版本/模型（能确认时）、使用日期、用途和人工核验责任。不得写AI代替作者完成核心建模；不得隐瞒AI参与；不确定版本标`TO_CONFIRM_BY_AUTHOR`。

### 6. V1编辑清理

只在preflight副本中：

- 标记并清理旧`BLOCKED/HOLD/CLOSED`状态冲突；
- 删除病句、重复段落和聊天式表达；
- 统一N、D、Q、p、Loss、Benchmark、FLOPs、十亿单位和物理单位；
- 把现有图表占位转成registry引用；
- 保留所有资格词和负结果；
- 对G1/G2/G4使用显式占位符，不填数字。

## 【必须输出】

- `paper/preflight/FINAL_CHAPTER_SKELETON.md`
- `paper/preflight/CITATION_MAP.csv`
- `paper/preflight/REFERENCE_VERIFICATION.csv`
- `paper/preflight/references_verified.bib`
- `paper/preflight/FORMULA_REGISTRY.csv`
- `paper/preflight/FIGURE_TABLE_REGISTRY.csv`
- `paper/preflight/AI_DISCLOSURE_DRAFT.md`
- `paper/preflight/V1_EDITORIAL_ISSUES.csv`
- `paper/preflight/FULL_MANUSCRIPT_PREFLIGHT.md`
- 运行目录内的`run_summary.json`、`input_manifest.json`、`checks.json`、`verification.json`、`handoff.md`、`output_manifest.json`

## 【检查与验收】

- 每条正文外部事实都有citation map状态；
- 每条正式参考文献均有可核验标识；
- 没有从参考论文复制句子、数字、参数或图；
- 四问冻结数字逐项保持原样；G1/G2/G4只占位；
- 公式ID与图表ID唯一；
- 图表均能追到本项目正式文件；
- 官方封面、目录、页码、AI披露和附录要求均有明确落点；
- verifier扫描未出现虚构DOI、未核验引用进入正文、旧状态被当现状、占位符被伪结果替换；
- manifest最后生成。

## 【禁止事项】

- 不修改最终科学数字或资格；
- 不替G1/G2/G4写结论；
- 不使用参考论文结果补缺；
- 不生成最终Q2/Q4预测；
- 不制作最终DOCX/PDF或最终图；
- 不修改原V1、00–05或正式run。

## 【停止条件】

发现冻结接口冲突、官方格式要求无法确认、参考文献无法核验、V1修改需要改变科学含义或必须读取尚未完成的G1/G2/G4结果时，保留占位并交主控，不得自行裁决。

## 【执行器启动prompt】

请执行`tasks/TASK-PAPER-PREFLIGHT_参考文献与成品结构.md`。只做论文结构、正式文献核验、citation map、公式与图表registry、AI披露草稿和V1清理副本。参考成品论文只能学习组织与版式，严禁复制其文字、数字、模型或结论。G1/G2/G4尚未验收的位置必须保留显式占位，不得修改任何冻结科学结果、00–05或原正文。完成后提交preflight目录和独立检查证据，不生成最终DOCX/PDF。
