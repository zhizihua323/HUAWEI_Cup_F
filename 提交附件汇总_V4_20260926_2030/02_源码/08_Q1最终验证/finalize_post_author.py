# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
#!/usr/bin/env python
"""Finalize the post-author run after an orchestration-only stage-log failure. No scientific recomputation."""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST=timezone(timedelta(hours=8))
RUN_DIR=Path(__file__).resolve().parents[1]
RUN_ID=RUN_DIR.name
PROJECT=Path(__file__).resolve().parents[4]
SOURCE_RUN=PROJECT/'diagnostics'/'TASK-G1'/'20260925T204300+08'
PAPER=PROJECT/'paper'/'Q1_GAP_RESULT_FREEZE.md'

def now(): return datetime.now(CST).isoformat(timespec='seconds')
def sha_file(p,chunk=1<<20):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(chunk),b''): h.update(b)
 return h.hexdigest()
def write_json(p,o):
 t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.replace(t,p)
def check(n,ok,d): return {'check':n,'status':'PASS' if ok else 'FAIL','details':d}

def main():
 start=time.time(); stages=[]
 def stage(name,phase,**details):
  rec={'run_id':RUN_ID,'timestamp':now(),'stage':name,'status':phase,**details}
  with (RUN_DIR/'stage_status.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False,sort_keys=True)+'\n')
  stages.append(rec)
 stage('s45_recovery_finalize','start',scientific_outputs_reused=True,no_recompute=True)
 required=['environment.json','input_manifest.json','source_manifest_before.json','paper_manuscript_before.json',
           'manual_review_parse_audit.csv','manual_text_review_joined.csv','manual_validation_statistics.csv',
           'manual_case_registry.csv','code/post_author_analysis.py','code/verify_post_author.py']
 missing=[x for x in required if not (RUN_DIR/x).exists()]
 if missing: raise RuntimeError('missing pre-finalization artifacts: '+repr(missing))
 if not PAPER.exists(): raise RuntimeError('paper candidate missing')
 if (RUN_DIR/'output_manifest.json').exists(): raise RuntimeError('output manifest already exists')
 verifier=RUN_DIR/'code'/'verify_post_author.py'
 proc=subprocess.run([sys.executable,str(verifier),'--run-dir',str(RUN_DIR)],capture_output=True,text=True,encoding='utf-8')
 if proc.returncode!=0: raise RuntimeError(f'verifier failed: {proc.stdout}\n{proc.stderr}')
 verification=json.loads((RUN_DIR/'verification.json').read_text(encoding='utf-8'))
 source_manifest=json.loads((SOURCE_RUN/'output_manifest.json').read_text(encoding='utf-8'))
 source_changes=[]
 for e in source_manifest['registered_files']:
  p=SOURCE_RUN/e['path']
  if not p.exists() or p.stat().st_size!=e['bytes'] or sha_file(p)!=e['sha256']:
   source_changes.append(e['path'])
 before=json.loads((RUN_DIR/'paper_manuscript_before.json').read_text(encoding='utf-8'))
 manuscript=PROJECT/'paper'/'manuscript'
 after={str(p.relative_to(PROJECT)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':sha_file(p)} for p in sorted(manuscript.rglob('*')) if p.is_file()}
 manuscript_changes=[k for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k)]
 joined_rows=sum(1 for _ in (RUN_DIR/'manual_text_review_joined.csv').open(encoding='utf-8-sig'))-1
 stats_rows=sum(1 for _ in (RUN_DIR/'manual_validation_statistics.csv').open(encoding='utf-8-sig'))-1
 case_rows=sum(1 for _ in (RUN_DIR/'manual_case_registry.csv').open(encoding='utf-8-sig'))-1
 checks=[
  check('recovery_finalize_did_not_recompute_scientific_outputs',True,{'scientific_outputs_reused':True}),
  check('source_run_registered_files_unchanged',not source_changes,source_changes),
  check('paper_manuscript_unchanged',not manuscript_changes,manuscript_changes),
  check('joined_rows_60',joined_rows==60,{'rows':joined_rows}),
  check('statistics_rows_11',stats_rows==11,{'rows':stats_rows}),
  check('case_rows_at_most_6',case_rows<=6,{'rows':case_rows}),
  check('paper_candidate_present',PAPER.exists() and PAPER.read_text(encoding='utf-8').startswith('# Q1 Gap Result Freeze Candidate'),{'sha256':sha_file(PAPER)}),
  check('independent_verifier_passed',verification.get('status')=='PASS',verification.get('summary')),
 ]
 checks_payload={'run_id':RUN_ID,'generated_local':now(),'summary':{'total':len(checks),'pass':sum(c['status']=='PASS' for c in checks),'fail':sum(c['status']=='FAIL' for c in checks)},'checks':checks}
 write_json(RUN_DIR/'checks.json',checks_payload)
 stage('s45_recovery_finalize','complete',checks=checks_payload['summary'],no_recompute=True)
 summary={'task':'TASK-G1-POST-AUTHOR','run_id':RUN_ID,'status':'COMPLETE_PENDING_CONTROLLER_REVIEW',
          'source_run':str(SOURCE_RUN),'finished_local':now(),'duration_s':round(time.time()-start,3),
          'recovery_finalize_used':True,'scientific_outputs_reused':True,'joined_rows':joined_rows,
          'statistics_rows':stats_rows,'case_rows':case_rows,'paper_candidate':str(PAPER),
          'paper_candidate_status':'CANDIDATE_PENDING_CONTROLLER_REVIEW','checks':checks_payload['summary'],
          'verification':verification.get('summary'),'no_imputation':True,'no_resampling':True,'manual_scores_author_only':True}
 write_json(RUN_DIR/'run_summary.json',summary)
 command={'run_id':RUN_ID,'argv':sys.argv,'stages':stages,'verifier_command':[sys.executable,str(verifier),'--run-dir',str(RUN_DIR)],
          'verifier_stdout':proc.stdout,'verifier_stderr':proc.stderr,'note':'Recovery finalizer only; scientific files reused unchanged.'}
 write_json(RUN_DIR/'command_log.json',command)
 handoff=f'''# TASK-G1 post-author handoff\n\n状态：`COMPLETE_PENDING_CONTROLLER_REVIEW`。\n\n- 后作者统计保留在`manual_validation_statistics.csv`；最终收口由recovery finalizer完成，仅做验收与manifest，未重算科学结果。\n- 作者表：60个review_id，完整46条、部分1条、无效/缺失13条；无插补、无重抽样。\n- 候选冻结文件：`{PAPER}`。\n- 独立验收：{verification.get("status")}，checks={checks_payload["summary"]}。\n- Q01C/T03E旧run及paper/manuscript正文未修改。\n'''
 (RUN_DIR/'handoff.md').write_text(handoff,encoding='utf-8')
 snap=RUN_DIR/'code_snapshot'
 if snap.exists(): shutil.rmtree(snap)
 shutil.copytree(RUN_DIR/'code',snap)
 stage('s70_manifest_pending','will_generate_output_manifest_last',recovery_finalize=True)
 entries=[]
 for p in sorted(x for x in RUN_DIR.rglob('*') if x.is_file() and x.name!='output_manifest.json' and not x.name.endswith('.tmp')):
  entries.append({'path':str(p.relative_to(RUN_DIR)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha_file(p)})
 manifest={'run_id':RUN_ID,'task':'TASK-G1-POST-AUTHOR','status':'COMPLETE_PENDING_CONTROLLER_REVIEW','generated_local':now(),
           'manifest_is_last_registered_artifact':True,'registered_file_count':len(entries),'registered_files':entries,
           'external_artifacts':[{'path':str(PAPER.relative_to(PROJECT)).replace('\\','/'),'bytes':PAPER.stat().st_size,'sha256':sha_file(PAPER),'status':'CANDIDATE_PENDING_CONTROLLER_REVIEW'}],
           'verification_status':verification.get('status'),'recovery_finalize_used':True,'scientific_outputs_reused':True,
           'no_imputation':True,'no_resampling':True,'manual_scores_author_only':True}
 write_json(RUN_DIR/'output_manifest.json',manifest)
 print(json.dumps({'status':manifest['status'],'run_dir':str(RUN_DIR),'registered_files':len(entries),'checks':checks_payload['summary']},ensure_ascii=False))
 return 0

if __name__=='__main__':
 raise SystemExit(main())
