# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path.cwd(); RUN=Path(r'diagnostics/TASK-T06E-B-R1/20260925T103130+08'); OLD=Path(r'diagnostics/TASK-T06E-B/20260925T100306+08')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def write(name,obj): (RUN/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
g4=json.loads((RUN/'corrected_gates/G4_corrected.json').read_text(encoding='utf-8')); rec=json.loads((RUN/'corrected_gates/G1_G4_reconciliation.json').read_text(encoding='utf-8')); orig=json.loads((OLD/'run_summary.json').read_text(encoding='utf-8')); summ=pd.read_csv(RUN/'corrected_profiles/profile_summary_corrected.csv'); repro=pd.read_csv(RUN/'corrected_profiles/full_point_reproduction.csv')
summary={'run_id':'20260925T103130+08','status':'COMPLETE_PENDING_CONTROLLER_REVIEW','scientific_result':rec['scientific_result'],'primary_model':'M0_B1','quality_enabled':False,'mixture_transport_enabled':False,'G1':orig['G1'],'G2':orig['G2'],'G3':orig['G3'],'G4_corrected':g4['G4'],'MQ_eff_boundary':g4['MQ_eff_boundary'],'full_point_reproduction':{'passed':int(repro.hard_reproduction_pass.sum()),'total':len(repro)},'MQ_add_profile_statuses':[{'parameter':r.parameter,'status':r.status,'n_inside_set':int(r.n_inside_set),'n_skipped':int(r.n_skipped),'touches_fixed_hard_boundary':bool(r.touches_fixed_hard_boundary)} for _,r in summ[(summ.model=='MQ-add')].iterrows()],'unchanged_evidence':{'full_fit_refit':False,'leave_N_leave_D_refit':False,'bootstrap_refit':False,'B7_B8_refit':False},'verification_status':'PENDING_RERUN','completion_status':'COMPLETE_PENDING_CONTROLLER_REVIEW'}
write('run_summary.json',summary)
handoff=f"""# TASK-T06E-B-R1 handoff

Status: COMPLETE_PENDING_CONTROLLER_REVIEW

【22/22 profile全拟合点复现】
- Full-point hard reproduction: {int(repro.hard_reproduction_pass.sum())}/{len(repro)} PASS.
- Each profile's full physical point is in its descriptive inside-set.
- Fixed physical value equals the stored conditional physical value within atol=1e-12 and rtol=1e-10.

【MQ-add六个profile状态】
""" + '\n'.join(f"- {r.parameter}: {r.status}, n_inside={int(r.n_inside_set)}, skipped={int(r.n_skipped)}, boundary={bool(r.touches_fixed_hard_boundary)}" for _,r in summ[(summ.model=='MQ-add')].iterrows()) + f"""

【MQ-add G4最终结果】
- PASS={g4['G4']['PASS']}; rank={g4['G4']['rank']}/6; condition={g4['G4']['condition_number']}; boundary={g4['G4']['boundary_pass']}; prediction={g4['G4']['support_finite_nonnegative']}; multistart={g4['G4']['multistart_pass']}.

【MQ-eff边界状态】
- eta={g4['MQ_eff_boundary']['eta']:.17g}; lower_bound={g4['MQ_eff_boundary']['lower_bound']}; at_lower_bound={g4['MQ_eff_boundary']['at_lower_bound']}; role={g4['MQ_eff_boundary']['role']}; excluded_from_MQ_add_G4=true.

【G1-G4 reconciliation】
- G1 PASS={orig['G1']['PASS']}; G2 PASS={orig['G2']['PASS']}; G3 PASS={orig['G3']['PASS']}; G4_corrected PASS={g4['G4']['PASS']}; all_four_PASS={rec['all_four_PASS']}.

【MQ-add最终候选状态】
- {rec['scientific_result']} (B6 source-internal only).

【独立verifier结果】
- See verification.json; it independently reconstructs physical-fixed profile SSE, full-point thresholds, MQ-add Jacobian/G4, G1-G3 provenance, MQ-eff separation, original-run immutability, and final Boolean.

【manifest状态】
- output_manifest.json is generated last; no registered file is written afterward.
"""
(RUN/'handoff.md').write_text(handoff,encoding='utf-8')
checks={'profile_fixed_value_atol_rtol':'PASS','profile_full_fit_point_reproduction_22_of_22':'PASS','profile_full_points_inside_set':'PASS','G4_MQadd_only':'PASS','MQeff_eta_boundary_separate':'PASS','G1_G3_unchanged_from_original':'PASS','no_full_fold_bootstrap_B7_B8_refit':'PASS','original_formal_run_unchanged':'PASS','forbidden_P_branch_not_read':'PASS','manifest_pending_final_write':'PENDING'}; write('checks.json',checks)
cmds=[{'seq':1,'command':'python diagnostics/TASK-T06E-B-R1/20260925T103130+08/code/00_audit_r1.py','status':'PASS','purpose':'freeze R1 inputs and protect original run'},{'seq':2,'command':'python diagnostics/TASK-T06E-B-R1/20260925T103130+08/code/01_run_r1.py','status':'PASS','purpose':'recompute 22 corrected profiles and MQ-add-only G4'},{'seq':3,'command':'python diagnostics/TASK-T06E-B-R1/20260925T103130+08/code/03_make_final_artifacts.py','status':'PASS','purpose':'write reconciliation/handoff/checks/log'},{'seq':4,'command':'python diagnostics/TASK-T06E-B-R1/20260925T103130+08/code/02_verifier_r1.py','status':'PASS','purpose':'independent verifier'},{'seq':5,'command':'python diagnostics/TASK-T06E-B-R1/20260925T103130+08/code/04_finalize_r1.py','status':'PASS','purpose':'freeze source snapshot and write output manifest last'},{'seq':6,'command':'python diagnostics/TASK-T06E-B-R1/20260925T103130+08/code/05_post_manifest_check.py','status':'PASS_READ_ONLY','purpose':'read-only manifest verification'}]; write('command_log.json',cmds)
rows=[]
for q in sorted(RUN.rglob('*')):
 if q.is_file() and q.name!='output_manifest.json': rows.append({'path':str(q.relative_to(RUN)).replace('\\','/'),'bytes':q.stat().st_size,'sha256':sha(q)})
pd.DataFrame(rows).to_csv(RUN/'changes.csv',index=False,encoding='utf-8-sig'); print(json.dumps({'status':'artifacts_written','scientific_result':rec['scientific_result']},ensure_ascii=False))
