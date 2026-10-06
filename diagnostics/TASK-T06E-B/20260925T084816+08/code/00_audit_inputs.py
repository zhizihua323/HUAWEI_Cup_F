from __future__ import annotations
import hashlib, json, math, os, platform, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import scipy, pyarrow

ROOT = Path.cwd()
RUN = Path(r"diagnostics/TASK-T06E-B/20260925T084816+08")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def key_hash(df: pd.DataFrame, cols: list[str]) -> str:
    x = df[cols].copy()
    x = x.sort_values(cols, kind='mergesort').reset_index(drop=True)
    return hashlib.sha256(x.to_csv(index=False, float_format='%.17g', lineterminator='\n').encode()).hexdigest()

def records_from_df(df: pd.DataFrame, cols: list[str]) -> list[tuple]:
    return [tuple(float(v) if isinstance(v, (int,float,np.number)) else v for v in r) for r in df[cols].itertuples(index=False, name=None)]

required = {
 't06e': ROOT/'tasks/TASK-T06E_来源内缩放律与质量条件关系验证_尺度桥接情景及T07接口.md',
 't06_method': ROOT/'tasks/TASK-T06_尺度桥接识别性与广义缩放律方法裁决.md',
 'brief': ROOT/'00_PROJECT_BRIEF.md',
 'status': ROOT/'01_PROJECT_STATUS.md',
 'decisions': ROOT/'02_DECISIONS.md',
 'catalog': ROOT/'03_DATA_CATALOG.md',
 'queue': ROOT/'04_TASK_QUEUE.md',
 'review': ROOT/'05_REVIEW_LOG.md',
 'data_notes': ROOT/'tmp/environment_review/数据说明.txt',
 'b1': ROOT/'F题/real_attachments/B_scaling_laws/pythia_training_log_existing.csv',
 'b6': ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv',
 'b7': ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment_expanded.csv',
 'b8': ROOT/'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment_large.csv',
 'scaling_params': ROOT/'solution/outputs/scaling/scaling_params.json',
 'model_comparison': ROOT/'solution/outputs/scaling/model_comparison.csv',
 'quality_audit': ROOT/'solution/outputs/scaling/quality_audit.json',
 'quality_B6_validation': ROOT/'solution/outputs/scaling/quality_B6_validation.csv',
 'quality_within_ND_slopes': ROOT/'solution/outputs/scaling/quality_within_ND_slopes.csv',
 'quality_scenario_predictions': ROOT/'solution/outputs/scaling/quality_scenario_predictions.csv',
 'external_validation': ROOT/'solution/outputs/scaling/external_validation.csv',
 'validation_by_model': ROOT/'solution/outputs/scaling/validation_by_model.csv',
 'bootstrap_existing': ROOT/'solution/outputs/scaling/cluster_bootstrap_parameters.csv',
 'scaling_report': ROOT/'solution/reports/scaling_baseline.md',
}
missing = [str(p) for p in required.values() if not p.exists()]
if missing:
    raise SystemExit('MISSING_REQUIRED_INPUTS\n'+'\n'.join(missing))

versions = {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__, 'pandas': pd.__version__, 'pyarrow': pyarrow.__version__}
expected = {'python':'3.13.9','numpy':'2.3.5','scipy':'1.16.3','pandas':'2.3.3','pyarrow':'21.0.0'}
if versions != expected:
    raise SystemExit('ENVIRONMENT_MISMATCH '+json.dumps(versions))

b1 = pd.read_csv(required['b1'])
b6 = pd.read_csv(required['b6'])
b7 = pd.read_csv(required['b7'])
b8 = pd.read_csv(required['b8'])
qgrid = sorted(set(np.round(b6.Q_score.astype(float), 12)))
qexpected = [0.1,0.2,0.3,0.4,0.6,0.8,0.9,1.0]
nd6 = b6[['N_params_B','D_tokens_B']].drop_duplicates()
nd8 = b8[['N_params_B','D_tokens_B']].drop_duplicates()
keys6 = records_from_df(b6, ['N_params_B','D_tokens_B','Q_score'])
keys7 = records_from_df(b7, ['N_params_B','D_tokens_B','Q_score'])
keys8 = records_from_df(b8, ['N_params_B','D_tokens_B','Q_score'])
set6, set7, set8 = set(keys6), set(keys7), set(keys8)
overlap67 = set6 & set7
overlap68 = set6 & set8
new90 = set7 - set6
b6map = {(float(n),float(d),float(q)):float(y) for n,d,q,y in b6[['N_params_B','D_tokens_B','Q_score','val_loss']].itertuples(index=False,name=None)}
b7map = {(float(n),float(d),float(q)):float(y) for n,d,q,y in b7[['N_params_B','D_tokens_B','Q_score','val_loss']].itertuples(index=False,name=None)}
b8map = {(float(n),float(d),float(q)):float(y) for n,d,q,y in b8[['N_params_B','D_tokens_B','Q_score','val_loss']].itertuples(index=False,name=None)}
loss_diffs67 = [abs(b7map[k]-b6map[k]) for k in overlap67]
loss_diffs68 = [abs(b8map[k]-b6map[k]) for k in overlap68]
anchors = {
 'B1_rows': len(b1), 'B1_N_unique': int(b1.N_params_B.nunique()), 'B1_N_min': float(b1.N_params_B.min()), 'B1_N_max': float(b1.N_params_B.max()),
 'B1_D_min': float(b1.D_tokens_B.min()), 'B1_D_max': float(b1.D_tokens_B.max()),
 'B6_rows': len(b6), 'B6_N_unique': int(b6.N_params_B.nunique()), 'B6_D_unique': int(b6.D_tokens_B.nunique()), 'B6_ND_groups': int(nd6.shape[0]),
 'B6_Q_levels': qgrid, 'B6_Q_train_le_0.6_rows': int((b6.Q_score<=0.6).sum()), 'B6_Q_stress_gt_0.6_rows': int((b6.Q_score>0.6).sum()),
 'B7_rows': len(b7), 'B7_B6_exact_overlap_keys': len(overlap67), 'B7_new_keys': len(new90), 'B7_overlap_exact_loss_count': int(sum(x==0 for x in loss_diffs67)),
 'B7_overlap_max_abs_loss_diff': max(loss_diffs67) if loss_diffs67 else None,
 'B8_rows': len(b8), 'B8_ND_groups': int(nd8.shape[0]), 'B8_B6_common_keys': len(overlap68), 'B8_B6_loss_exact_count': int(sum(x==0 for x in loss_diffs68)),
 'B8_B6_max_abs_loss_diff': max(loss_diffs68) if loss_diffs68 else None,
 'B6_loss_all_finite_positive': bool(np.isfinite(b6.val_loss).all() and (b6.val_loss>0).all()),
 'B1_loss_all_finite_positive': bool(np.isfinite(b1.val_loss).all() and (b1.val_loss>0).all()),
}
fail=[]
if len(b1)!=1176 or anchors['B1_N_unique']!=8: fail.append('B1 anchors')
if not (math.isclose(anchors['B1_N_min'],0.070542,rel_tol=0,abs_tol=1e-12) and math.isclose(anchors['B1_N_max'],11.965825,rel_tol=0,abs_tol=1e-12)): fail.append('B1 N range')
if not (math.isclose(anchors['B1_D_min'],0.134,rel_tol=0,abs_tol=1e-12) and math.isclose(anchors['B1_D_max'],299.893,rel_tol=0,abs_tol=1e-12)): fail.append('B1 D range')
if len(b6)!=360 or anchors['B6_N_unique']!=9 or anchors['B6_D_unique']!=5 or anchors['B6_ND_groups']!=45: fail.append('B6 grid')
if qgrid != qexpected: fail.append('B6 Q levels')
if anchors['B6_Q_train_le_0.6_rows']!=225 or anchors['B6_Q_stress_gt_0.6_rows']!=135: fail.append('B6 Q partition')
if len(b7)!=450 or len(overlap67)!=360 or len(new90)!=90 or anchors['B7_overlap_exact_loss_count']!=360: fail.append('B7 repeat isolation')
if len(b8)!=1704 or anchors['B8_ND_groups']!=150 or len(overlap68)!=160: fail.append('B8 partition')
if fail:
    audit_payload={'status':'FAIL','failures':fail,'anchors':anchors}
    (RUN/'input_audit.json').write_text(json.dumps(audit_payload,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit('INPUT_ANCHOR_FAIL '+','.join(fail))

input_manifest={
 'schema_version':1,
 'run_id':'20260925T084816+08',
 'created_at':'2026-09-25T07:57:43+08:00',
 'input_boundary':{'forbidden_reads_not_performed':['TASK-T06E-P new runs','A-side T03E interface','A1-A17','RegMix artifacts']},
 'inputs':[{'role':k,'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha256(p)} for k,p in required.items()],
 'old_scaling_protection':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted((ROOT/'solution/outputs/scaling').glob('*')) if p.is_file()],
}
(RUN/'input_manifest.json').write_text(json.dumps(input_manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(RUN/'input_audit.json').write_text(json.dumps({'status':'PASS','anchors':anchors,'overlap_checks':{'B6_B7_exact_loss_max_abs_diff':anchors['B7_overlap_max_abs_loss_diff'],'B6_B8_exact_loss_max_abs_diff':anchors['B8_B6_max_abs_loss_diff']},'units':{'N':'1e9 parameters','D':'1e9 tokens','loss':'source validation cross-entropy'},'source_labels':{'B1':'observed','B6':'semisynthetic','B7':'semisynthetic_with_B6_repeats','B8':'semisynthetic_with_extrapolation'}},ensure_ascii=False,indent=2),encoding='utf-8')

solver_config={
 'schema_version':1,'run_id':'20260925T084816+08','solver':'scipy.optimize.least_squares',
 'versions':versions,'method':'trf','loss':'linear','jac':'3-point','x_scale':1.0,
 'ftol':1e-12,'xtol':1e-12,'gtol':1e-12,'max_nfev':100000,'dtype':'float64',
 'q_train_max':0.6,'q_reference':0.6,
 'weights':{'B1':'point_equal','B6':'N_D_group_equal_then_normalized','residual_scale':'sqrt(weight)*(pred-y)/s_y','s_y':'max(IQR(y_train),1e-8)'},
 'multistart':{'full_and_folds_total':33,'bootstrap_total':9,'profile_total':9,'sobol_internal_fraction':[0.05,0.95]},
 'parameter_bounds':{'E_A_B_k_relative_to_Lstar':[1e-8,1e3],'alpha_beta':[1e-4,4.0],'eta':[1e-6,50.0]},
 'seeds':{'base_multistart':20260926,'base_bootstrap':20260925,'model_offsets':{'M0':0,'MQ-add':100000,'MQ-eff':200000},'stage_offsets':{'full':0,'leave_N':10000,'leave_D':20000,'bootstrap':30000,'profile':40000}},
 'profile':{'grid_points_per_positive_parameter':41,'include_optimum':True,'k_add_and_eta_zero_endpoint':True,'descriptive_chi2_threshold':3.841458820694124},
 'gates':{'G1_min_negative_fraction':0.80,'G2_min_macro_improvement':0.05,'G2_fold_ratio_limit':1.10,'G3_replicates':200,'G3_min_success':190,'G3_success_direction_fraction':0.90,'G4_jacobian_relative_singular_threshold':1e-8,'G4_condition_limit':1e8},
 'stop_conditions':['input_anchor_or_hash_mismatch','need_to_change_model_gate_boundary_solver_profile','Q_gt_0.6_or_B7_or_B8_feedback','M0_MQ_fold_keys_differ','B7_repeats_enter_denominator','no_finite_converged_solution','old_artifact_change_or_forbidden_write','joint_mapping_parameter_attempt','post_manifest_write']
}
(RUN/'config/solver_config.json').write_text(json.dumps(solver_config,ensure_ascii=False,indent=2),encoding='utf-8')
model_registry={
 'schema_version':1,'primary_model':'M0_B1','quality_enabled':False,'mixture_transport_enabled':False,
 'models':{
  'M0_B1':{'formula':'E+A*N^(-alpha)+B*D^(-beta)','source':'B1','parameters':['E','A','B','alpha','beta'],'role':'primary_source_baseline'},
  'M0_6':{'formula':'E+A*N^(-alpha)+B*D^(-beta)','source':'B6','parameters':['E','A','B','alpha','beta'],'role':'same-fold_null'},
  'MQ-add':{'formula':'E+A*N^(-alpha)+B*D^(-beta)-k_add*(Q-0.6)','source':'B6','parameters':['E','A','B','alpha','beta','k_add'],'constraint':'k_add>=0','role':'main_quality_candidate'},
  'MQ-eff':{'formula':'E+A*N^(-alpha)+B*D^(-beta)*exp(-eta*(Q-0.6))','source':'B6','parameters':['E','A','B','alpha','beta','eta'],'constraint':'eta>=0','role':'sensitivity_only','derived':'k_eff=eta/beta'}
 },
 'forbidden':['MQ-eff as replacement main candidate','joint B6-B8 fit','old k=-20 propagation','Q>0.6/B7/B8 model selection','B7 repeats in denominators','cross-source A/B mapping estimation']
}
(RUN/'config/model_registry.json').write_text(json.dumps(model_registry,ensure_ascii=False,indent=2),encoding='utf-8')

freeze_files={
 'status':'PASS','run_id':'20260925T084816+08','boundary':'only diagnostics/TASK-T06E-B/20260925T084816+08/ written',
 'configuration_frozen_before_fit':True,
 'training_support':{'B6_Q_max':0.6,'rows':225,'stress_rows':135,'stress_first_prediction_after_full_model_freeze':True},
 'split_registry':{'B1_leave_N_folds':8,'B1_late_token_folds':8,'B6_leave_N_folds':9,'B6_leave_D_folds':5},
 'bootstrap':{'replicates':200,'N_clusters':9},'B7':{'repeat_keys':360,'new_keys':90},'B8':{'common_keys':160,'stress_only_rows':1544},
 'input_hashes':{k:sha256(p) for k,p in required.items()},'t06_method_sha256':sha256(required['t06_method'])
}
(RUN/'freeze_manifest.json').write_text(json.dumps(freeze_files,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','run_id':'20260925T084816+08','anchors':anchors},ensure_ascii=False,indent=2))


