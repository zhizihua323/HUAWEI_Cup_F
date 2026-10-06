"""恢复阶段只读核验：不导入项目脚本、不拟合、不重采样、不解压 XZ。

仅在本脚本目录写入核验记录；原数据及 solution 保持不变。
"""
from pathlib import Path
from datetime import datetime
import ast
import hashlib
import itertools
import json
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import r2_score

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATA = ROOT / 'F题' / 'real_attachments'
SOL = ROOT / 'solution'
checks = []
def readj(path):
    return json.loads(path.read_text(encoding='utf-8'))
def check(name, ok, detail):
    checks.append({'check': name, 'status': 'PASS' if bool(ok) else 'FAIL', 'detail': detail})
def close(a, b):
    return np.allclose(a, b, atol=1e-10, rtol=1e-9, equal_nan=True)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

# Capture source/output evidence before writing recovery documents.
inventory = []
for path in sorted(SOL.rglob('*')):
    if path.is_file():
        st = path.stat()
        inventory.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': st.st_size,
                          'mtime_local': datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(),
                          'sha256': sha(path)})
pd.DataFrame(inventory).to_csv(OUT / 'solution_inventory.csv', index=False, encoding='utf-8-sig')
for path in sorted((SOL / 'src').glob('*.py')):
    ast.parse(path.read_text(encoding='utf-8-sig'))
check('source_syntax_only', True, 'All project src/*.py parse; none imported or executed.')

manifest = pd.read_csv(SOL / 'outputs/audit/raw_source_manifest.csv')
longdata = Path('\\\\?\\' + str(DATA.resolve()))
actual = {p.relative_to(longdata).as_posix(): p.stat().st_size for p in longdata.rglob('*') if p.is_file()}
expected = dict(zip(manifest.path, manifest.bytes.astype(int)))
check('raw_paths_and_sizes', actual == expected, {'actual_files': len(actual), 'bytes': sum(actual.values()),
       'missing': sorted(set(expected)-set(actual)), 'extra': sorted(set(actual)-set(expected)),
       'size_mismatches': [p for p in expected if p in actual and actual[p] != expected[p]]})
hashed = []
for row in manifest.itertuples(index=False):
    if Path(row.path).suffix.lower() == '.csv':
        path = longdata / row.path
        hashed.append({'path': row.path, 'same': sha(path) == row.sha256})
check('raw_csv_hashes', all(x['same'] for x in hashed), {'files_checked': len(hashed), 'mismatches': [x for x in hashed if not x['same']]})

parsed = []
for path in sorted((SOL / 'outputs').rglob('*')):
    if path.suffix == '.json':
        d = readj(path); parsed.append({'path': path.relative_to(ROOT).as_posix(), 'kind': 'json', 'entries': len(d)})
    elif path.suffix == '.csv':
        d = pd.read_csv(path); parsed.append({'path': path.relative_to(ROOT).as_posix(), 'kind': 'csv', 'rows': len(d), 'columns': len(d.columns)})
pd.DataFrame(parsed).to_csv(OUT / 'parsed_outputs.csv', index=False, encoding='utf-8-sig')
check('saved_json_csv_parse', True, {'files': len(parsed)})

mix = SOL / 'outputs/mixture'
model = readj(mix / 'model.json')
metrics = pd.read_csv(mix / 'metrics.csv')
agg = pd.read_csv(mix / 'aggregate_predictions.csv')
mixchecks = []
for label in ['train_1m','test_1m','test_60m','test_1B','est_10b','est_70b']:
    prefix, scale = label.split('_', 1)
    raw = pd.read_csv(DATA / f'A_data_value/regmix_tables/{prefix}_mixture_{scale}.csv').set_index('index')
    truth = pd.read_csv(DATA / f'A_data_value/regmix_tables/{prefix}_pile_loss_{scale}.csv').set_index('index')
    norm = pd.read_csv(mix / f'{label}_normalized_mixtures.csv').set_index('index')
    x = raw.loc[norm.index, model['features']].to_numpy(float)
    x /= x.sum(axis=1, keepdims=True)
    check('mixture_normalization_' + label, close(x, norm.to_numpy()), {'rows': len(x), 'features': x.shape[1]})
    for family in ['linear','quadratic']:
        saved = pd.read_csv(mix / f'{family}_{label}_predictions.csv').set_index('index')
        coef = pd.read_csv(mix / f'{family}_coefficients.csv').set_index('term')
        feats = x if family == 'linear' else np.column_stack([x] + [x[:,i]*x[:,j] for i,j in itertools.combinations(range(17),2)])
        pred = saved[['pred_'+c for c in coef.columns]].to_numpy()
        y = saved[['actual_'+c for c in coef.columns]].to_numpy()
        check('mixture_predictions_' + family + '_' + label,
              saved.index.equals(norm.index) and close(feats @ coef.to_numpy(), pred) and close(y, truth.loc[saved.index, coef.columns].to_numpy()),
              {'max_coefficient_prediction_error': float(np.max(np.abs(feats @ coef.to_numpy()-pred)))})
        m = metrics[(metrics.model == family) & (metrics['set'] == label)].iloc[0]
        values = {'rmse_all_domains': np.sqrt(np.mean((y-pred)**2)), 'mae_all_domains': np.mean(abs(y-pred)),
                  'r2_domain_mean': r2_score(y,pred), 'rmse_equal_domain_mean': np.sqrt(np.mean((y.mean(1)-pred.mean(1))**2)),
                  'r2_equal_domain_mean': r2_score(y.mean(1),pred.mean(1)),
                  'spearman_equal_domain_mean': spearmanr(y.mean(1),pred.mean(1)).statistic}
        a = agg[(agg.model == family) & (agg['set'] == label)].set_index('index').loc[saved.index]
        check('mixture_metrics_' + family + '_' + label,
              all(close(v,m[k]) for k,v in values.items()) and close(a.predicted_mean_loss,pred.mean(1)) and close(a.observed_or_estimated_mean_loss,y.mean(1)),
              {k: float(v) for k,v in values.items()})
        mixchecks.append({'model': family,'set': label,**{k: float(v) for k,v in values.items()}})
    
sc = SOL / 'outputs/scaling'
params = readj(sc / 'scaling_params.json')
b1 = pd.read_csv(DATA / 'B_scaling_laws/pythia_training_log_existing.csv')
preds = pd.read_csv(sc / 'B1_all_predictions.csv')
comp = pd.read_csv(sc / 'model_comparison.csv')
chosen = params['model_selection']['configuration']
s = preds[(preds.configuration == chosen) & (preds.split == 'in_sample')]
p = params['parameters']
v = p['E']+p['A']*s.N_params_B.to_numpy()**(-p['alpha'])+p['B']*s.D_tokens_B.to_numpy()**(-p['beta'])
check('B1_saved_formula_and_raw', close(v,s.prediction) and close(s[['N_params_B','D_tokens_B','val_loss']].to_numpy(),b1[['N_params_B','D_tokens_B','val_loss']].to_numpy()),
      {'n': len(s),'configuration': chosen,'max_error': float(np.max(abs(v-s.prediction)))})
for row in comp.itertuples(index=False):
    for split, prefix in [('in_sample','fit'),('leave_one_model_out','LOMO'),('last_20pct_tokens','stage')]:
        sub = preds[(preds.configuration == row.configuration) & (preds.split == split)]
        rmse = float(np.sqrt(np.mean((sub.prediction-sub.val_loss)**2)))
        check('B1_metrics_' + row.configuration + '_' + split, len(sub)==getattr(row,prefix+'_n') and close(rmse,getattr(row,prefix+'_RMSE')), {'n':len(sub),'RMSE':rmse})
boot = pd.read_csv(sc / 'cluster_bootstrap_parameters.csv')
for k, bounds in params['bootstrap_percentiles'].items():
    q = np.percentile(boot.loc[boot.success,k],[2.5,50,97.5])
    check('saved_bootstrap_quantiles_' + k,close(q,[bounds['p2_5'],bounds['median'],bounds['p97_5']]),{'saved_rows':len(boot),'successful_rows':int(boot.success.sum())})
ta = {t['id']:t for t in readj(sc / 'table_audit.json')}
qa = readj(sc / 'quality_audit.json')
bt = {k:pd.read_csv(DATA / ta[k]['file']) for k in ['B6','B7','B8']}
for k,t in bt.items():
    slopes = []
    for _,g in t.groupby(['N_params_B','D_tokens_B']):
        x,y=g.Q_score.to_numpy(),g.val_loss.to_numpy()
        slopes.append(float(np.sum((x-x.mean())*(y-y.mean()))/np.sum((x-x.mean())**2)))
    facts={'groups':len(slopes),'positive_group_slopes':sum(x>0 for x in slopes),'negative_group_slopes':sum(x<0 for x in slopes)}
    check('quality_direction_' + k,all(v==qa['table_results'][k][key] for key,v in facts.items()),facts)
for row in qa['overlap']:
    joint = bt[row['left']].merge(bt[row['right']],on=['N_params_B','D_tokens_B','Q_score'],suffixes=('_l','_r'))
    diff=abs(joint.val_loss_l-joint.val_loss_r)
    check('quality_overlap_' + row['left']+'_'+row['right'],len(joint)==row['matching_keys'] and int((diff==0).sum())==row['exact_same_loss'] and close(diff.max(),row['max_abs_difference']),{'matching_keys':len(joint),'same_loss':int((diff==0).sum()),'max_difference':float(diff.max())})

quality = SOL / 'outputs/quality'
au = readj(quality / 'audit.json')
norm = readj(quality / 'normalization.json')
dom = pd.read_csv(quality / 'domain_summary.csv')
counts = {k:int(v) for k,v in dom.groupby('scope').n.sum().items()}
check('quality_saved_counts',sum(x['rows'] for x in au['files'])==au['total_records'] and au['total_records']-au['duplicate_occurrences']==au['unique_id_sub_path_keys']==counts['all_unique'] and counts['A1_calibration']==norm['calibration_rows'] and counts['A1_calibration']+counts['A1_holdout']==counts['A1_all_unique'] and counts['A1_all_unique']+counts['extension_new_records']==counts['all_unique'],counts)
groupcols=['group_usability_mean','group_knowledge_mean','group_education_reasoning_mean']
check('quality_summary_score_definition',close(dom[groupcols].mean(axis=1),dom.Q_mean) and dom.Q_mean.between(0,1).all(),{'max_group_average_error':float(abs(dom[groupcols].mean(axis=1)-dom.Q_mean).max())})
for domain,g in dom.groupby('domain'):
    a=g[g.scope.isin(['A1_calibration','A1_holdout'])]
    whole=g[g.scope=='A1_all_unique'].iloc[0]
    check('quality_A1_aggregate_' + domain,close(np.average(a.Q_mean,weights=a.n),whole.Q_mean),{'n':int(whole.n)})
stored = manifest.set_index('path').sha256.to_dict()
check('quality_hash_records_agree',all(stored[x['file'].replace('\\','/')]==x['sha256'] for x in au['files']), 'Compared two saved hash records; compressed XZ files NOT rehashed or reread.')
missing = [n for n in ['unresolved_indicator_correlations.csv','indicator_direction_pending.csv','conditional_bootstrap.csv','verification.json','quality_features_scores.parquet','list_field_audit.csv'] if not (quality/n).exists()]

# Read original problem XML without modifying Word files.
problem = next((ROOT/'F题').glob('*.docx'))
with zipfile.ZipFile(problem) as z:
    xml=ET.fromstring(z.read('word/document.xml'))
    paragraphs=[''.join(x.itertext()) for x in xml.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')]
(OUT/'problem_text_from_docx.txt').write_text('\n'.join(paragraphs),encoding='utf-8')
result={'timestamp_local':datetime.now().astimezone().isoformat(), 'mode':'RECOVERY_ONLY_NO_MODEL_EXECUTION',
        'checks':checks,'pass_count':sum(x['status']=='PASS' for x in checks),'fail_count':sum(x['status']=='FAIL' for x in checks),
        'quality_missing_outputs':missing,'evolution_output_directory_exists':(SOL/'outputs/evolution').exists(),
        'limits':['No XZ reread; full stream row facts rely on retained prior audit.','No fits, CV, bootstrap or evolution computation rerun.','OOF domain-level prediction arrays are not persisted; OOF training execution cannot be independently reconstructed without refitting.','Source hashes describe current files, not historical code at original runtime.','Presence of output does not prove whole script completed or process exited successfully.'],
        'mixture_recomputed_metrics':mixchecks}
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pass_count':result['pass_count'],'fail_count':result['fail_count'],'failures':[x for x in checks if x['status']=='FAIL'],'quality_counts':counts,'missing_quality':missing,'evolution_outputs_exist':result['evolution_output_directory_exists']},ensure_ascii=False,indent=2))
