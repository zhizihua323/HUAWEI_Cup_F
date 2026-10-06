import pandas as pd, numpy as np, json
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

def met(y, p):
    y = np.asarray(y); p = np.asarray(p); r = p - y
    ss = float(np.sum((y - y.mean())**2))
    return {'n': len(y), 'RMSE': float(np.sqrt(np.mean(r*r))), 'MAE': float(np.mean(np.abs(r))),
            'bias': float(r.mean()), 'R2': float(1 - np.sum(r*r)/ss) if ss > 0 else None,
            'maxae': float(np.max(np.abs(r)))}

# --- 1. B1: recompute saved-metric values from saved per-row predictions ---
b1 = pd.read_csv('solution/outputs/scaling/B1_all_predictions.csv')
mc = pd.read_csv('solution/outputs/scaling/model_comparison.csv')
print('B1_all_predictions columns:', list(b1.columns))
worst = 0.0
for _, row in mc.iterrows():
    c = row['configuration']
    sub = b1[(b1.configuration == c) & (b1.split == 'in_sample')]
    r = met(sub.val_loss, sub.prediction)
    pairs = [('fit_n', 'n'), ('fit_RMSE', 'RMSE'), ('fit_MAE', 'MAE'),
             ('fit_bias_pred_minus_actual', 'bias'), ('fit_R2', 'R2'), ('fit_max_abs_error', 'maxae')]
    for col, k in pairs:
        worst = max(worst, abs(r[k] - row[col]))
print(f'B1 in-sample metrics recomputed for {len(mc)} configs from saved predictions; worst diff={worst:.3e}')
lomo = b1[(b1.configuration == 'point__linear') & (b1.split == 'leave_one_model_out')]
r = met(lomo.val_loss, lomo.prediction)
print('point__linear LOMO from saved predictions:', {k: round(v, 12) for k, v in r.items()})
print('  saved LOMO row:', {k: round(float(mc[mc.configuration=="point__linear"][f"LOMO_{k}"].iloc[0]), 12) for k in ['n','RMSE','MAE','bias_pred_minus_actual','R2','max_abs_error']})
stage = b1[(b1.configuration == 'point__linear') & (b1.split == 'last_20pct_tokens')]
r2 = met(stage.val_loss, stage.prediction)
print('point__linear last20% from saved predictions:', {k: round(v, 12) for k, v in r2.items()})
print()

# --- 2. external validation: recompute "all" rows from prediction files ---
for tag, f in [('B2', 'B2_predictions.csv'), ('B3', 'B3_predictions.csv'), ('B4', 'B4_predictions.csv'),
               ('B5', 'B5_predictions.csv'), ('B10', 'B10_predictions.csv')]:
    d = pd.read_csv(f'solution/outputs/scaling/{f}')
    r = met(d.val_loss, d.prediction)
    print(f'{tag:4s} n={r["n"]:5d} RMSE={r["RMSE"]:.6f} bias={r["bias"]:.6f} R2={r["R2"]:.6f}')
print()

# --- 3. B2 residual pattern: near-constant offset? ---
d2 = pd.read_csv('solution/outputs/scaling/B2_predictions.csv')
print('B2 bias across size groups (pred-actual):')
print(d2.groupby('N_params_B').apply(lambda g: float((g.prediction - g.val_loss).mean()), include_groups=False).round(4).to_string())
print()

# --- 4. quality scenario predictions vs B6 fit parameters ---
q = json.load(open('solution/outputs/scaling/quality_audit.json', encoding='utf-8'))
p6 = q['table_results']['B6']['parameters']
d6 = pd.read_csv('solution/outputs/scaling/quality_scenario_predictions.csv')
d6 = d6[d6.table == 'B6'].copy()
pred = p6['E'] + p6['A']*d6.N_params_B**(-p6['alpha']) + p6['B']*(d6.D_tokens_B*np.exp(p6['k']*(d6.Q_score - p6['Q_ref'])))**(-p6['beta'])
print('max |recomputed - saved prediction| for B6 scenario rows:', float(np.max(np.abs(pred - d6.prediction))))
print('B6 scenario rows:', len(d6))
print()

# --- 5. B7 novel grid ---
nov = pd.read_csv('solution/outputs/scaling/B7_novel_grid_predicted_from_B6.csv')
print('B7_novel_grid rows:', len(nov), '| columns:', list(nov.columns)[:8])
p6b = q['table_results']['B6']['parameters']
if {'N_params_B','D_tokens_B','Q_score','val_loss'}.issubset(nov.columns):
    pr = p6b['E'] + p6b['A']*nov.N_params_B**(-p6b['alpha']) + p6b['B']*(nov.D_tokens_B*np.exp(p6b['k']*(nov.Q_score-0.5)))**(-p6b['beta'])
    print('novel-grid RMSE recomputed from B6 params:', float(np.sqrt(np.mean((pr-nov.val_loss)**2))))
