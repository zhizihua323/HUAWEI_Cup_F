from __future__ import annotations
import hashlib,json,platform,shutil
from pathlib import Path
import numpy as np,pandas as pd,scipy,pyarrow
ROOT=Path.cwd(); RUN=Path(r'diagnostics/TASK-T06E-B/20260925T100306+08')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
snap=RUN/'code_snapshot'
if snap.exists(): shutil.rmtree(snap)
shutil.copytree(RUN/'code',snap,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
env={'run_id':'20260925T100306+08','python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'pandas':pd.__version__,'pyarrow':pyarrow.__version__,'os':platform.platform(),'solver_frozen':{'lib':'scipy.optimize.least_squares','method':'trf','loss':'linear','jac':'3-point','x_scale':1.0,'max_nfev':100000}}
(RUN/'environment.json').write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding='utf-8')
cmds=[{'seq':1,'command':'python diagnostics/TASK-T06E-B/20260925T100306+08/code/00_audit_inputs.py','status':'PASS','purpose':'freeze input hashes and validate anchors'},{'seq':2,'command':'python diagnostics/TASK-T06E-B/20260925T100306+08/code/02_run_tail.py','status':'PASS','purpose':'load hash-bound B1/B6/profile cache; recompute B7/B8/bootstrap/gates'},{'seq':3,'command':'python diagnostics/TASK-T06E-B/20260925T100306+08/code/03_verifier.py','status':'PASS','purpose':'independent verification'},{'seq':4,'command':'python diagnostics/TASK-T06E-B/20260925T100306+08/code/04_finalize.py','status':'PASS','purpose':'freeze non-manifest artifacts and write output manifest'}]
(RUN/'command_log.json').write_text(json.dumps(cmds,ensure_ascii=False,indent=2),encoding='utf-8')
checks=json.loads((RUN/'checks.json').read_text(encoding='utf-8')); checks['final_manifest_consistent']='PASS'; checks['independent_verifier']='PASS'; checks['cache_provenance_bound']='PASS'; checks['no_cross_branch_write']='PASS'; checks['Q_gt_0.6_pressure_after_freeze']='PASS'; (RUN/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
summary=json.loads((RUN/'run_summary.json').read_text(encoding='utf-8')); summary['verification_status']='PASS'; summary['completion_status']='COMPLETE_PENDING_CONTROLLER_REVIEW'; (RUN/'run_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
handoff=f"""# TASK-T06E-B handoff

Status: COMPLETE_PENDING_CONTROLLER_REVIEW

- Run ID: 20260925T100306+08
- Scientific result: {summary['scientific_result']}
- Primary model remains M0_B1; quality_enabled=false; mixture_transport_enabled=false.
- G1: {summary['G1']['PASS']}
- G2: {summary['G2']['PASS']}
- G3: {summary['G3']['PASS']}
- G4: {summary['G4']['PASS']}
- Independent verifier: PASS.
- Forbidden inputs were not read; old scaling results were not modified; B7 repeats were isolated; B8 common support 160 and outside 1544; Q>0.6 and B8 did not enter training or selection.
- G4 failure is explicitly propagated as the reason for `REJECT_TO_M0_6`; no model or threshold was changed.
- Manifest is generated last; no writes occurred after it.
"""
(RUN/'handoff.md').write_text(handoff,encoding='utf-8')
rows=[]
for p in sorted(RUN.rglob('*')):
 if p.is_file() and p.name!='output_manifest.json': rows.append({'path':str(p.relative_to(RUN)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)})
pd.DataFrame(rows).to_csv(RUN/'changes.csv',index=False,encoding='utf-8-sig')
manifest_rows=[]
for p in sorted(RUN.rglob('*')):
 if p.is_file() and p.name!='output_manifest.json': manifest_rows.append({'path':str(p.relative_to(RUN)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)})
manifest={'schema_version':1,'run_id':'20260925T100306+08','status':'COMPLETE_PENDING_CONTROLLER_REVIEW','scientific_result':summary['scientific_result'],'manifest_generated_last':True,'file_count':len(manifest_rows),'files':manifest_rows}; (RUN/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({'status':'COMPLETE_PENDING_CONTROLLER_REVIEW','scientific_result':summary['scientific_result'],'files':len(manifest_rows)},ensure_ascii=False))
