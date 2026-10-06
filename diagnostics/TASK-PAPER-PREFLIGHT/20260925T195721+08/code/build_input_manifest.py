import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
root=Path.cwd(); rd=root/'diagnostics/TASK-PAPER-PREFLIGHT'/(root/'diagnostics/TASK-PAPER-PREFLIGHT/.last_run_id').read_text(encoding='utf-8').strip()
items=[
('tasks/TASK-PAPER-PREFLIGHT_参考文献与成品结构.md','task_contract'),('F题/算力约束下提升大语言模型能力的资源配置建模.docx','problem_statement'),('F题/数据说明.pdf','data_documentation'),('附件2：“华为杯”第二十三届中国研究生数学建模竞赛论文格式规范.docx','official_format'),('附件3：“华为杯”第二十三届中国研究生数学建模竞赛论文模板.doc','official_template'),('附件4：“华为杯”第二十三届中国研究生数学建模竞赛人工智能工具及输出使用规定.docx','official_ai_policy'),('paper/manuscript/FULL_MANUSCRIPT_V1.md','frozen_input_copy_not_modified'),('paper/manuscript/Q1_Q2_STABLE_BODY.md','stable_body'),('paper/manuscript/Q3_STABLE_BODY.md','stable_body'),('paper/manuscript/Q4_STABLE_BODY.md','stable_body'),('paper/T06_RESULT_FREEZE.md','result_freeze'),('paper/T07_RESULT_FREEZE.md','result_freeze'),('paper/T05_RESULT_FREEZE.md','result_freeze'),('paper/T08_RESULT_FREEZE.md','result_freeze'),('paper/FINAL_RESULT_INDEX.md','result_index'),('audit/FINAL_PROJECT_STATE.md','project_state'),('audit/QUESTION_REQUIREMENT_COVERAGE.md','requirement_coverage'),('audit/FINAL_RESULT_SOURCE_OF_TRUTH.md','source_of_truth'),('audit/FINAL_ACTION_PLAN.md','action_plan'),('paper/manuscript/FINAL_FIGURE_TABLE_PLAN.md','figure_table_plan'),('paper/manuscript/FINAL_CLAIM_EVIDENCE_AUDIT.md','claim_evidence_audit'),('paper/data_sources.md','data_source_map'),('paper/figure_table_registry.md','legacy_asset_registry'),('参考资料/2026华为杯研赛F题成品参考论文！.pdf','form_and_layout_reference_only')]
rows=[]
for rel,role in items:
    p=root/rel
    if not p.exists():rows.append({'path':rel,'role':role,'exists':False});continue
    b=p.read_bytes(); rows.append({'path':rel,'role':role,'exists':True,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
manifest={'run_id':rd.name,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'read-only inputs for paper preflight','reference_paper_boundary':'Only organization and layout were inspected; its text, numbers, models, figures and conclusions must not be copied.','items':rows}
(rd/'input_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(len(rows))
