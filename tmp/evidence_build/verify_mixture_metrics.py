import pandas as pd, numpy as np, pathlib
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from scipy.stats import spearmanr

m = pd.read_csv('solution/outputs/mixture/metrics.csv')
worst_all = 0.0; n_ok = 0
for _, row in m.iterrows():
    if row['model'] == 'training_domain_means':
        continue
    f = f"solution/outputs/mixture/{row['model']}_{row['set']}_predictions.csv"
    if not pathlib.Path(f).exists():
        print(f"SKIP  {row['model']:9s} {row['set']:18s} (no per-row prediction file)")
        continue
    d = pd.read_csv(f)
    Y = d[[c for c in d.columns if c.startswith('actual_')]].to_numpy(float)
    P = d[[c for c in d.columns if c.startswith('pred_')]].to_numpy(float)
    a, b = Y.mean(axis=1), P.mean(axis=1)
    chk = {'n': len(Y),
           'rmse_all_domains': np.sqrt(mean_squared_error(Y, P)),
           'mae_all_domains': mean_absolute_error(Y, P),
           'r2_domain_mean': r2_score(Y, P),
           'rmse_equal_domain_mean': np.sqrt(mean_squared_error(a, b)),
           'r2_equal_domain_mean': r2_score(a, b),
           'spearman_equal_domain_mean': spearmanr(a, b).statistic}
    w = max(abs(chk[k] - row[k]) for k in chk)
    worst_all = max(worst_all, w); n_ok += 1
    print(f"{row['model']:9s} {row['set']:18s} n={int(row['n']):4d} maxdiff={w:.3e}")
print(f"\nchecked {n_ok} model/set combos from saved per-row predictions; worst diff = {worst_all:.3e}")
