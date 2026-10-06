import pandas as pd, numpy as np, json, pathlib
from sklearn.metrics import mean_squared_error, r2_score
from scipy.stats import spearmanr

# ---------- 1. mixture metrics recomputation from saved predictions ----------
m = pd.read_csv('solution/outputs/mixture/metrics.csv')
rows, skipped = [], []
for _, row in m.iterrows():
    if row['model'] == 'training_domain_means':
        continue
    f = f"solution/outputs/mixture/{row['model']}_{row['set']}_predictions.csv"
    if not pathlib.Path(f).exists():
        skipped.append((row['model'], row['set']))
        continue
    d = pd.read_csv(f)
    Y = d[[c for c in d.columns if c.startswith('actual_')]].to_numpy(float)
    P = d[[c for c in d.columns if c.startswith('pred_')]].to_numpy(float)
    assert Y.shape == P.shape and Y.shape[0] == int(row['n']), (f, Y.shape, row['n'])
    per = [np.sqrt(mean_squared_error(Y[:, j], P[:, j])) for j in range(Y.shape[1])]
    r2s = [r2_score(Y[:, j], P[:, j]) for j in range(Y.shape[1])]
    sps = [spearmanr(Y[:, j], P[:, j]).statistic for j in range(Y.shape[1])]
    chk = {'rmse_all_domains': np.sqrt(mean_squared_error(Y.ravel(), P.ravel())),
           'mae_all_domains': np.mean(np.abs(Y.ravel() - P.ravel())),
           'rmse_equal_domain_mean': np.mean(per),
           'r2_domain_mean': np.mean(r2s),
           'r2_equal_domain_mean': np.mean(r2s),
           'spearman_equal_domain_mean': np.mean(sps)}
    worst = max(abs(chk[k] - row[k]) for k in chk)
    rows.append((row['model'], row['set'], int(row['n']), worst))
    print(f"{row['model']:9s} {row['set']:18s} n={int(row['n']):4d} maxdiff={worst:.3e}")
print('recomputed model/set combos:', len(rows), '| worst mismatch:', max(r[3] for r in rows))
print('NOT re-verifiable (no per-row prediction file saved):', skipped)
print()

# ---------- 2. recipe overlap ----------
def norm_recipes(label):
    d = pd.read_csv(f'solution/outputs/mixture/{label}_normalized_mixtures.csv')
    pc = [c for c in d.columns if c.startswith('train_the_pile_')]
    return d[pc].round(12)
tr = norm_recipes('train_1m'); trset = set(map(tuple, tr.to_numpy()))
for lab in ['test_1m', 'test_60m', 'test_1B', 'est_10b', 'est_70b']:
    o = norm_recipes(lab); oset = set(map(tuple, o.to_numpy()))
    print(f'{lab:9s} recipes={len(oset):4d} overlap_with_train={len(oset & trset):4d}')
print('test_1m recipe matrix identical to test_60m:',
      np.array_equal(norm_recipes('test_1m').to_numpy(), norm_recipes('test_60m').to_numpy()))
print('est_10b recipe matrix identical to est_70b:',
      np.array_equal(norm_recipes('est_10b').to_numpy(), norm_recipes('est_70b').to_numpy()))
print()

# ---------- 3. scaling params consistency ----------
af = json.load(open('solution/outputs/scaling/all_fits.json', encoding='utf-8'))
sp = json.load(open('solution/outputs/scaling/scaling_params.json', encoding='utf-8'))
pl = af['point__linear']['parameters']
print('all_fits point__linear vs scaling_params max abs diff:',
      max(abs(pl[k] - sp['parameters'][k]) for k in pl))
print('point__linear success:', af['point__linear']['optimizer_success'],
      'successful starts:', af['point__linear']['n_successful_starts'])
q = json.load(open('solution/outputs/scaling/quality_audit.json', encoding='utf-8'))
print('B6 k diff vs scaling scenario k:',
      abs(q['table_results']['B6']['parameters']['k'] - sp['quality_scenario']['k']))
print('scenario status:', sp['quality_scenario_status'], '| transfer_status:', q['transfer_status'])
print('B8 near-bound params:', q['table_results']['B8']['near_bound_parameters'],
      '| B8 k:', q['table_results']['B8']['parameters']['k'])
print('B8 jacobian cond:', q['table_results']['B8']['jacobian_condition_number'])
print()

# ---------- 4. bootstrap ----------
bs = pd.read_csv('solution/outputs/scaling/cluster_bootstrap_parameters.csv')
print('bootstrap rows:', len(bs), 'success:', int(bs.success.sum()),
      'distinct cluster sizes used:', sorted(bs.unique_sizes.unique()))
worst = 0
for k in ['E', 'A', 'B', 'alpha', 'beta']:
    lo, md, hi = np.percentile(bs[k], [2.5, 50, 97.5]); s = sp['bootstrap_percentiles'][k]
    w = max(abs(lo - s['p2_5']), abs(md - s['median']), abs(hi - s['p97_5'])); worst = max(worst, w)
    print(f'  {k:6s} maxdiff={w:.3e}')
print('bootstrap worst diff:', worst)
print()

# ---------- 5. external validation all-rows ----------
ev = pd.read_csv('solution/outputs/scaling/external_validation.csv')
print(ev[ev.group == 'all'][['table', 'n', 'RMSE', 'MAE', 'bias_pred_minus_actual', 'R2']].to_string(index=False))
print()

# ---------- 6. quality direction ----------
sl = pd.read_csv('solution/outputs/scaling/quality_within_ND_slopes.csv')
for t in ['B6', 'B7', 'B8']:
    g = sl[sl.table == t]
    print(f'{t}: groups={len(g)} neg={(g.linear_slope_dL_dQ < 0).sum()} pos={(g.linear_slope_dL_dQ > 0).sum()}')
print()

# ---------- 7. B1 predictions inventory ----------
b1 = pd.read_csv('solution/outputs/scaling/B1_all_predictions.csv')
print('B1_all_predictions rows:', len(b1), '| configs:', list(b1.configuration.unique()), '| splits:', list(b1.split.unique()))
print(b1.groupby(['configuration', 'split']).size().to_string())
print()
b1p = json.load(open('solution/outputs/scaling/B1_precision_residual_audit.json', encoding='utf-8'))
print('B1 rounding audit: loss dp=', b1p['val_loss_csv_decimal_places'],
      'rmse_in_half_units=', b1p['rmse_in_loss_rounding_half_units'],
      'frac_abs_resid_le_half_unit=', b1p['fraction_abs_residual_le_loss_half_rounding_unit'])
