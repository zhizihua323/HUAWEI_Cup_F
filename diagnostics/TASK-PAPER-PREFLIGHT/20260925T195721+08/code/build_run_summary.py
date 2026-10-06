import json
from datetime import datetime,timezone
from pathlib import Path
root=Path.cwd(); rid=(root/'diagnostics/TASK-PAPER-PREFLIGHT/.last_run_id').read_text(encoding='utf-8').strip(); rd=root/'diagnostics/TASK-PAPER-PREFLIGHT'/rid
summary={
 'task_id':'TASK-PAPER-PREFLIGHT','run_id':rid,'status':'COMPLETE_PENDING_CONTROLLER_REVIEW',
 'started_local':'2026-09-25T19:57:21+08:00','finished_local':'2026-09-25T20:12:00+08:00',
 'scope':['chapter skeleton','formal reference verification','citation map','formula registry','figure/table registry','AI disclosure draft','V1 editorial clean copy'],
 'explicitly_not_performed':['final DOCX/PDF generation','final figure generation','new scientific modeling','G1/G2/G4 result substitution','modification of FULL_MANUSCRIPT_V1 or 00-05','modification of formal scientific runs'],
 'outputs':{'paper_preflight_files':9,'references_verified':28,'citation_rows':24,'formula_rows':37,'figure_table_rows':25,'editorial_issue_rows':21},
 'scientific_boundaries':{'G1':'EXPLICIT_PLACEHOLDER_PENDING_CONTROLLER_REVIEW','G2':'EXPLICIT_PLACEHOLDER_PENDING_CONTROLLER_REVIEW','G4':'EXPLICIT_PLACEHOLDER_PENDING_CONTROLLER_REVIEW','frozen_numbers':'UNCHANGED','final_render_created':False},
 'verification':{'checks_file':'checks.json','verification_file':'verification.json','status':'PASS','n_checks':39,'n_fail':0},
 'network_verification':['Crossref DOI metadata','arXiv official API','OpenReview official API','PMLR official pages','DBLP/OpenAlex attempted; OpenAlex rate-limited and not used as sole evidence','official Hugging Face dataset API','official Epoch AI CSV endpoint','OpenAI official Codex documentation'],
 'catalogue_corrections':['RegMix: official record is Qian Liu et al., ICLR 2025 Spotlight; task text says Xia et al., ICML 2024.','MuSR: official recorded venue is ICLR 2024 Spotlight, not ICML 2024.','Hoffmann/Kaplan/IFEval entries retain official preprint status where conference metadata was not independently confirmed.'],
 'manifest_status':'PENDING_FINAL_GENERATION',
 'generated_at_utc':datetime.now(timezone.utc).isoformat()}
(rd/'run_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
handoff='''# TASK-PAPER-PREFLIGHT 交接说明\n\n## 状态\n\n`COMPLETE_PENDING_CONTROLLER_REVIEW`。已完成章节骨架、正式文献核验、citation map、公式registry、图表registry、AI披露草稿和V1清理副本；未生成最终DOCX/PDF或最终图。\n\n## 科学边界\n\n- `FULL_MANUSCRIPT_V1.md`、三份稳定正文、T05/T06/T07/T08冻结接口和00-05均未修改。\n- 四问冻结数字按原V1保留；预检副本重编号只改变章节号，不改变科学数值。\n- G1、G2、G4均保留显式占位：`【G1_PENDING】`、`【G2_PENDING】`、`【G4_PENDING】`。\n- 参考成品论文只用于组织与版式观察，未引用其文字、数字、模型、图或结论。\n\n## 关键校正\n\n- RegMix官方记录为Qian Liu等，ICLR 2025 Spotlight；题面所写“Xia et al., ICML 2024”未沿用。\n- MuSR官方记录为ICLR 2024 Spotlight。\n- Chinchilla、Kaplan与IFEval在未确认正式会议元数据时，按官方预印本状态登记，不虚构会议页码或DOI。\n\n## 独立检查\n\n`checks.json`和`verification.json`记录39项检查全部通过，覆盖必交文件、引用可解析性、ID唯一性、公式编号、来源路径、旧状态清理、关键资格词、数字token、最终文件禁止和官方结构落点。\n\n## 后续动作\n\n1. G1/G2/G4分别完成主控验收后，以各自`*_GAP_RESULT_FREEZE.md`替换对应占位。\n2. 从`references_verified.bib`中只导出正文实际引用条目，并按首次引用顺序编号；未使用的quantile/hedonic/frontier/DSIR候选不进入最终表。\n3. 按`FIGURE_TABLE_REGISTRY.csv`生成最终图，不从参考论文或聊天取数。\n4. 作者补齐AI底层模型精确版本、机构发布日期和关键输入/后处理记录。\n5. 通过后才进入DOCX/PDF制作，设置摘要页页码1、页脚居中、无页眉，并做最终渲染QA。\n'''
(rd/'handoff.md').write_text(handoff,encoding='utf-8')
print('ok')
