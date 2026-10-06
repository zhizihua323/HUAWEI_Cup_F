# -*- coding: utf-8 -*-
"""TASK evidence-baselines: consolidated READ-ONLY verification record.
Reads existing saved artifacts only. Fits nothing, writes nothing except this JSON.
"""
import json, csv, hashlib, pathlib, itertools
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from scipy.stats import spearmanr

RT = dict(float_precision='round_trip')   # default 'high' parser shifts last digits
ROOT = pathlib.Path('.')
MIX = ROOT / 'solution/outputs/mixture'
SCL = ROOT / 'solution/outputs/scaling'
RAW_A = ROOT / 'F题/real_attachments/A_data_value/regmix_tables'
rec = {}

def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

# ---------- 1. raw mixture table hashes vs saved audit ----------
audit = json.load(open(MIX / 'audit.json', encoding='utf-8'))
prefix = {'train_1m': ('train', '1m'), 'test_1m': ('test', '1m'), 'test_60m': ('test', '60m'),
          'test_1B': ('test', '1B'), 'est_10b': ('est', '10b'), 'est_70b': ('est', '70b')}
h = []
for a in audit:
    pre, sc = prefix[a['set']]
    pf, yf = RAW_A / f'{pre}_mixture_{sc}.csv', RAW_A / f'{pre}_pile_loss_{sc}.csv'
    h.append({'set': a['set'], 'rows_saved': a['rows'],
              'p_sha256_match': sha(pf) == a['p_sha256'], 'loss_sha256_match': sha(yf) == a['loss_sha256'],
              'recipes_identical_to_training_saved': a['recipes_identical_to_training']})
rec['mixture_raw_hash_check'] = {'all_match': all(x['p_sha256_match'] and x['loss_sha256_match'] for x in h), 'detail': h}
rec['mixture_structural_facts'] = {
    'test_1m_mixture_file_sha256': sha(RAW_A / 'test_mixture_1m.csv'),
    'test_60m_mixture_file_sha256': sha(RAW_A / 'test_mixture_60m.csv'),
    'test_1m_and_test_60m_mixture_identical': sha(RAW_A / 'test_mixture_1m.csv') == sha(RAW_A / 'test_mixture_60m.csv'),
    'est_10b_and_est_70b_mixture_identical': sha(RAW_A / 'est_mixture_10b.csv') == sha(RAW_A / 'est_mixture_70b.csv'),
}

# ---------- 2. mixture recipe overlap ----------
def norm(label):
    d = pd.read_csv(MIX / f'{label}_normalized_mixtures.csv', **RT)
    return d[[c for c in d.columns if c.startswith('train_the_pile_')]]
tr = set(map(tuple, norm('train_1m').to_numpy()))
ov = {}
for lab in ['test_1m', 'test_60m', 'test_1B', 'est_10b', 'est_70b']:
    s = set(map(tuple, norm(lab).to_numpy()))
    ov[lab] = {'n_recipes': len(s), 'overlap_with_train': len(s & tr)}
rec['mixture_recipe_overlap'] = ov

# ---------- 3. mixture metrics recomputed from saved per-row predictions ----------
met = pd.read_csv(MIX / 'metrics.csv', **RT)
mm = []
for _, row in met.iterrows():
    if row['model'] == 'training_domain_means':
        continue
    f = MIX / f"{row['model']}_{row['set']}_predictions.csv"
    if not f.exists():
        mm.append({'model': row['model'], 'set': row['set'], 'status': 'NO_PER_ROW_FILE'})
        continue
    d = pd.read_csv(f, **RT)
    Y = d[[c for c in d.columns if c.startswith('actual_')]].to_numpy(float)
    P = d[[c for c in d.columns if c.startswith('pred_')]].to_numpy(float)
    a, b = Y.mean(axis=1), P.mean(axis=1)
    chk = {'n': len(Y), 'rmse_all_domains': np.sqrt(mean_squared_error(Y, P)),
           'mae_all_domains': mean_absolute_error(Y, P), 'r2_domain_mean': r2_score(Y, P),
           'rmse_equal_domain_mean': np.sqrt(mean_squared_error(a, b)),
           'r2_equal_domain_mean': r2_score(a, b),
           'spearman_equal_domain_mean': spearmanr(a, b).statistic}
    md = max(abs(float(chk[k]) - float(row[k])) for k in chk)
    mm.append({'model': row['model'], 'set': row['set'], 'status': 'RECOMPUTED', 'max_abs_diff': md})
rec['mixture_metrics_recompute'] = {'worst': max(x['max_abs_diff'] for x in mm if x['status'] == 'RECOMPUTED'), 'detail': mm}

# ---------- 4. exported coefficients reproduce saved predictions ----------
coef_res = {}
for family in ['linear', 'quadratic']:
    coef = pd.read_csv(MIX / f'{family}_coefficients.csv', **RT)
    C = coef.iloc[:, 1:].to_numpy(float)
    w = 0.0
    for lab in prefix:
        p = norm(lab).to_numpy(float)
        X = np.column_stack([p, np.column_stack([p[:, i] * p[:, j] for i, j in itertools.combinations(range(p.shape[1]), 2)])]) if family == 'quadratic' else p
        pred = X @ C
        saved = pd.read_csv(MIX / f'{family}_{lab}_predictions.csv', **RT)
        P = saved[[c for c in saved.columns if c.startswith('pred_')]].to_numpy(float)
        w = max(w, float(np.max(np.abs(pred - P))))
    coef_res[family] = w
rec['mixture_coefficients_reproduce_predictions'] = {'max_abs_diff': max(coef_res.values()), 'by_family': coef_res}

# ---------- 5. B1 saved predictions reproduce saved metrics ----------
def met6(y, p):
    y = np.asarray(y); p = np.asarray(p); r = p - y
    ss = float(np.sum((y - y.mean()) ** 2))
    return {'n': len(y), 'RMSE': float(np.sqrt(np.mean(r * r))), 'MAE': float(np.mean(np.abs(r))),
            'bias_pred_minus_actual': float(r.mean()), 'R2': float(1 - np.sum(r * r) / ss),
            'max_abs_error': float(np.max(np.abs(r)))}
b1 = pd.read_csv(SCL / 'B1_all_predictions.csv', **RT)
mcmp = pd.read_csv(SCL / 'model_comparison.csv', **RT)
b1res = {}
for _, row in mcmp.iterrows():
    c = row['configuration']
    s = b1[(b1.configuration == c) & (b1.split == 'in_sample')]
    r = met6(s.val_loss, s.prediction)
    b1res[c] = {'rows_in_saved_prediction_file': int(len(s)), 'max_abs_diff_vs_model_comparison':
                max(abs(r[k] - float(row[f'fit_{k}'])) for k in ['n','RMSE','MAE','bias_pred_minus_actual','R2','max_abs_error'])}
sel = b1[(b1.configuration == 'point__linear') & (b1.split == 'leave_one_model_out')]
stg = b1[(b1.configuration == 'point__linear') & (b1.split == 'last_20pct_tokens')]
row = mcmp[mcmp.configuration == 'point__linear'].iloc[0]
rec['B1_recompute'] = {'per_config_in_sample_max_diff': b1res,
    'lomo_pooled_RMSE_recomputed': met6(sel.val_loss, sel.prediction)['RMSE'],
    'lomo_pooled_RMSE_saved': float(row['LOMO_RMSE']),
    'stage_pooled_RMSE_recomputed': met6(stg.val_loss, stg.prediction)['RMSE'],
    'stage_pooled_RMSE_saved': float(row['stage_RMSE']),
    'prediction_file_rows': int(len(b1))}

# ---------- 6. bootstrap percentiles from saved resamples ----------
bs = pd.read_csv(SCL / 'cluster_bootstrap_parameters.csv', **RT)
sp = json.load(open(SCL / 'scaling_params.json', encoding='utf-8'))
bw = {}
for k in ['E', 'A', 'B', 'alpha', 'beta']:
    lo, md, hi = np.percentile(bs[k], [2.5, 50, 97.5]); s = sp['bootstrap_percentiles'][k]
    bw[k] = max(abs(lo - s['p2_5']), abs(md - s['median']), abs(hi - s['p97_5']))
rec['bootstrap_percentile_recompute'] = {'rows': int(len(bs)), 'success': int(bs.success.sum()),
    'max_abs_diff': max(bw.values()), 'by_parameter': bw}

# ---------- 7. parameters cross-file identity ----------
af = json.load(open(SCL / 'all_fits.json', encoding='utf-8'))
rec['parameters_cross_file'] = {
    'all_fits_point__linear_vs_scaling_params_max_diff':
        max(abs(af['point__linear']['parameters'][k] - sp['parameters'][k]) for k in sp['parameters']),
    'quality_scenario_k_vs_B6_k_diff':
        abs(json.load(open(SCL / 'quality_audit.json', encoding='utf-8'))['table_results']['B6']['parameters']['k'] - sp['quality_scenario']['k'])}

# ---------- 8. external validation all-rows recomputed ----------
ev = pd.read_csv(SCL / 'external_validation.csv', **RT)
ex = {}
for tag, f in [('B2','B2_predictions.csv'), ('B3','B3_predictions.csv'), ('B4','B4_predictions.csv'),
               ('B5','B5_predictions.csv'), ('B10','B10_predictions.csv')]:
    d = pd.read_csv(SCL / f, **RT)
    r = met6(d.val_loss, d.prediction)
    srow = ev[(ev.table == tag) & (ev.group == 'all')].iloc[0]
    ex[tag] = {'recomputed_RMSE': r['RMSE'], 'saved_RMSE': float(srow['RMSE']),
               'recomputed_bias': r['bias_pred_minus_actual'], 'saved_bias': float(srow['bias_pred_minus_actual']),
               'max_abs_diff': max(abs(r[k] - float(srow[k])) for k in ['n','RMSE','MAE','bias_pred_minus_actual','R2','max_abs_error'])}
rec['external_validation_recompute'] = {'worst': max(v['max_abs_diff'] for v in ex.values()), 'detail': ex}

# ---------- 9. quality direction + scenario recompute ----------
qa = json.load(open(SCL / 'quality_audit.json', encoding='utf-8'))
sl = pd.read_csv(SCL / 'quality_within_ND_slopes.csv', **RT)
qd = {}
for t in ['B6', 'B7', 'B8']:
    g = sl[sl.table == t]
    qd[t] = {'groups': int(len(g)), 'neg_slopes': int((g.linear_slope_dL_dQ < 0).sum()),
             'pos_slopes': int((g.linear_slope_dL_dQ > 0).sum()),
             'saved_neg': qa['table_results'][t]['negative_group_slopes'],
             'saved_pos': qa['table_results'][t]['positive_group_slopes']}
p6 = qa['table_results']['B6']['parameters']
sc = pd.read_csv(SCL / 'quality_scenario_predictions.csv', **RT)
sc6 = sc[sc.table == 'B6']
pred = p6['E'] + p6['A']*sc6.N_params_B**(-p6['alpha']) + p6['B']*(sc6.D_tokens_B*np.exp(p6['k']*(sc6.Q_score-p6['Q_ref'])))**(-p6['beta'])
nov = pd.read_csv(SCL / 'B7_novel_grid_predicted_from_B6.csv', **RT)
npred = p6['E'] + p6['A']*nov.N_params_B**(-p6['alpha']) + p6['B']*(nov.D_tokens_B*np.exp(p6['k']*(nov.Q_score-0.5)))**(-p6['beta'])
rec['quality_recompute'] = {'direction_counts': qd,
    'B6_scenario_rows': int(len(sc6)), 'B6_scenario_max_abs_diff': float(np.max(np.abs(pred - sc6.prediction))),
    'B7_novel_grid_rows': int(len(nov)), 'B7_novel_grid_RMSE_recomputed': float(np.sqrt(np.mean((npred - nov.val_loss)**2))),
    'B7_novel_grid_RMSE_saved': qa['B7_novel_grid_validation']['RMSE']}

# ---------- 10. no-change proof ----------
inv = list(csv.DictReader(open('recovery/2026-09-24/solution_inventory.csv', encoding='utf-8-sig')))
bad = [r['path'] for r in inv if not pathlib.Path(r['path']).exists() or sha(r['path']) != r['sha256']]
cc = json.load(open('recovery/2026-09-24/completion_check.json', encoding='utf-8'))
badoc = [d['path'] for d in cc['project_docs'] if sha(d['path']) != d['sha256']]
rec['no_change_proof'] = {'solution_files_checked': len(inv), 'solution_files_changed': len(bad),
                          'project_docs_checked': len(cc['project_docs']), 'project_docs_changed': len(badoc),
                          'changed_paths': bad + badoc, 'models_rerun': False}

# ---------- 11. provenance hashes of what was read ----------
rec['provenance_sha256'] = {str(p): sha(p) for p in [
    MIX/'metrics.csv', MIX/'model.json', MIX/'audit.json', MIX/'test_1m_conditional_intervals.json',
    SCL/'model_comparison.csv', SCL/'scaling_params.json', SCL/'B1_all_predictions.csv',
    SCL/'external_validation.csv', SCL/'quality_audit.json', SCL/'cluster_bootstrap_parameters.csv',
    SCL/'B1_precision_residual_audit.json']}

rec['meta'] = {'task': 'baseline evidence cards (mixture + scaling)',
               'date_local': '2026-09-24 Asia/Shanghai', 'mode': 'read-only verification; no model fitted',
               'float_parse_policy': "pandas float_precision='round_trip' (default 'high' can shift last digits)",
               'scripts': ['tmp/evidence_build/verify_mixture_metrics.py', 'tmp/evidence_build/verify_mixture_coef.py',
                           'tmp/evidence_build/verify_scaling.py', 'tmp/evidence_build/verify_no_changes.py',
                           'tmp/evidence_build/build_verification_record.py']}

pathlib.Path('evidence/verification_record.json').write_text(
    json.dumps(rec, ensure_ascii=False, indent=2), encoding='utf-8')
print('written evidence/verification_record.json')
print('mixture metrics worst diff :', rec['mixture_metrics_recompute']['worst'])
print('coef->prediction worst diff:', rec['mixture_coefficients_reproduce_predictions']['max_abs_diff'])
print('B1 per-config worst diff   :', max(v['max_abs_diff_vs_model_comparison'] for v in b1res.values()))
print('bootstrap worst diff       :', rec['bootstrap_percentile_recompute']['max_abs_diff'])
print('external worst diff        :', rec['external_validation_recompute']['worst'])
print('quality diff               :', rec['quality_recompute']['B6_scenario_max_abs_diff'])
print('no-change                  :', rec['no_change_proof'])
