# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import hashlib,json,platform,shutil
from pathlib import Path
import numpy as np,pandas as pd,scipy,pyarrow
ROOT=Path.cwd(); RUN=Path(r'diagnostics/TASK-T06E-B-R1/20260925T103130+08'); OLD=Path(r'diagnostics/TASK-T06E-B/20260925T100306+08')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def write_json(name,obj): (RUN/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
required={
 't06':ROOT/'tasks/TASK-T06_尺度桥接识别性与广义缩放律方法裁决.md',
 't06e':ROOT/'tasks/TASK-T06E_来源内缩放律与质量条件关系验证_尺度桥接情景及T07接口.md',
 'r1':ROOT/'tasks/TASK-T06E-B-R1_profile坐标与G4门槛精准小修.md',
 'b1':ROOT/'F题/real_attachments/B_scaling_laws/pythia_training_log_existing.csv',
 'b6':ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv'}
for k,p in required.items():
 if not p.exists(): raise SystemExit('MISSING_INPUT '+k)
orig_files=['fit/scaling_parameters_by_source.csv','fit/full_fit_predictions.parquet','validation/candidate_comparison.csv','validation/validation_splits.csv','bootstrap/bootstrap_summary.csv','profiles/profile_inputs.json','profiles/jacobian_diagnostics.csv','config/solver_config.json','run_summary.json','checks.json','verification.json','output_manifest.json']
orig={f:{'sha256':sha(OLD/f),'bytes':(OLD/f).stat().st_size} for f in orig_files}
# Verify the old run's complete manifest independently before using it as frozen evidence.
om=json.loads((OLD/'output_manifest.json').read_text(encoding='utf-8')); mism=[]
for row in om['files']:
 q=OLD/row['path']
 if (not q.exists()) or q.stat().st_size!=row['bytes'] or sha(q)!=row['sha256']: mism.append(row['path'])
if mism: raise SystemExit('ORIGINAL_RUN_MANIFEST_MISMATCH '+','.join(mism[:10]))
manifest={'schema_version':1,'run_id':'20260925T103130+08','purpose':'TASK-T06E-B-R1 precise correction','read_only_sources':{k:{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for k,p in required.items()},'original_run':{'path':'diagnostics/TASK-T06E-B/20260925T100306+08','files':orig,'manifest_file_count':om['file_count'],'manifest_hash':sha(OLD/'output_manifest.json')},'forbidden_reads_not_performed':['TASK-T06E-P','A-side T03E interface','A1-A17','Q>0.6/B7/B8 profile data','T07/T05 inputs']}
write_json('input_manifest.json',manifest)
protected={'status':'PASS','original_run_manifest_count':om['file_count'],'original_run_manifest_current':True,'original_run_files_sha256':orig,'original_run_manifest_sha256':sha(OLD/'output_manifest.json'),'original_run_modified':False,'forbidden_paths_not_read':manifest['forbidden_reads_not_performed']}
write_json('protected_original_run_check.json',protected)
env={'run_id':'20260925T103130+08','python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'pandas':pd.__version__,'pyarrow':pyarrow.__version__,'original_manifest_hash':sha(OLD/'output_manifest.json')}
write_json('environment.json',env)
shutil.copyfile(OLD/'config/solver_config.json',RUN/'config/solver_config.json')
# Freeze the exact full-fit point inputs used by all R1 profiles.
pi=json.loads((OLD/'profiles/profile_inputs.json').read_text(encoding='utf-8')); write_json('config/profile_inputs_frozen.json',pi)
print(json.dumps({'status':'PASS','original_manifest_count':om['file_count'],'original_manifest_hash':sha(OLD/'output_manifest.json')},ensure_ascii=False))
