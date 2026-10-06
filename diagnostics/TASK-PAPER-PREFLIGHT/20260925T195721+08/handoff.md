# TASK-PAPER-PREFLIGHT 交接说明

## 状态

`COMPLETE_PENDING_CONTROLLER_REVIEW`。已完成章节骨架、正式文献核验、citation map、公式registry、图表registry、AI披露草稿和V1清理副本；未生成最终DOCX/PDF或最终图。

## 科学边界

- `FULL_MANUSCRIPT_V1.md`、三份稳定正文、T05/T06/T07/T08冻结接口和00-05均未修改。
- 四问冻结数字按原V1保留；预检副本重编号只改变章节号，不改变科学数值。
- G1、G2、G4均保留显式占位：`【G1_PENDING】`、`【G2_PENDING】`、`【G4_PENDING】`。
- 参考成品论文只用于组织与版式观察，未引用其文字、数字、模型、图或结论。

## 关键校正

- RegMix官方记录为Qian Liu等，ICLR 2025 Spotlight；题面所写“Xia et al., ICML 2024”未沿用。
- MuSR官方记录为ICLR 2024 Spotlight。
- Chinchilla、Kaplan与IFEval在未确认正式会议元数据时，按官方预印本状态登记，不虚构会议页码或DOI。

## 独立检查

`checks.json`和`verification.json`记录39项检查全部通过，覆盖必交文件、引用可解析性、ID唯一性、公式编号、来源路径、旧状态清理、关键资格词、数字token、最终文件禁止和官方结构落点。

## 后续动作

1. G1/G2/G4分别完成主控验收后，以各自`*_GAP_RESULT_FREEZE.md`替换对应占位。
2. 从`references_verified.bib`中只导出正文实际引用条目，并按首次引用顺序编号；未使用的quantile/hedonic/frontier/DSIR候选不进入最终表。
3. 按`FIGURE_TABLE_REGISTRY.csv`生成最终图，不从参考论文或聊天取数。
4. 作者补齐AI底层模型精确版本、机构发布日期和关键输入/后处理记录。
5. 通过后才进入DOCX/PDF制作，设置摘要页页码1、页脚居中、无页眉，并做最终渲染QA。
