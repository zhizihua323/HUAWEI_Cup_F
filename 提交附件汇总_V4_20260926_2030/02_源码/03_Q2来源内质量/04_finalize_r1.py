# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import hashlib,json,shutil
from pathlib import Path
import pandas as pd
r=Path(r'diagnostics/TASK-T06E-B-R1/20260925T103130+08')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
v=json.loads((r/'verification.json').read_text(encoding='utf-8'))
if v.get('status')!='PASS': raise SystemExit('VERIFIER_NOT_PASS')
snap=r/'code_snapshot'
if snap.exists(): shutil.rmtree(snap)
shutil.copytree(r/'code',snap,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
checks=json.loads((r/'checks.json').read_text(encoding='utf-8')); checks.pop('manifest_pending_final_write',None); checks.update({'manifest_generated_last_after_checks':'PASS','independent_verifier':'PASS','post_manifest_read_only_check':'REGISTERED_COMMAND_FINAL_STEP'}); (r/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
s=json.loads((r/'run_summary.json').read_text(encoding='utf-8')); s['verification_status']='PASS'; s['completion_status']='COMPLETE_PENDING_CONTROLLER_REVIEW'; (r/'run_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
rows=[]
for q in sorted(r.rglob('*')):
 if q.is_file() and q.name!='output_manifest.json': rows.append({'path':str(q.relative_to(r)).replace('\\','/'),'bytes':q.stat().st_size,'sha256':sha(q)})
pd.DataFrame(rows).to_csv(r/'changes.csv',index=False,encoding='utf-8-sig')
manifest_rows=[]
for q in sorted(r.rglob('*')):
 if q.is_file() and q.name!='output_manifest.json': manifest_rows.append({'path':str(q.relative_to(r)).replace('\\','/'),'bytes':q.stat().st_size,'sha256':sha(q)})
manifest={'schema_version':1,'run_id':'20260925T103130+08','status':'COMPLETE_PENDING_CONTROLLER_REVIEW','scientific_result':s['scientific_result'],'manifest_generated_last':True,'file_count':len(manifest_rows),'files':manifest_rows}; (r/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({'status':'COMPLETE_PENDING_CONTROLLER_REVIEW','scientific_result':s['scientific_result'],'manifest_files':len(manifest_rows)},ensure_ascii=False))
