from pathlib import Path
import json
import numpy as np
import pandas as pd
root = Path.cwd()
run = root / 'diagnostics/TASK-T07/20260925T113744+08'
contract = json.loads((root / 'diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json').read_text(encoding='utf-8'))
model = json.loads((root / 'solution/outputs/mixture/model.json').read_text(encoding='utf-8'))
p0 = np.asarray(contract['mixture']['p0'], dtype=float)
a4raw = pd.read_csv(root / 'F题/real_attachments/A_data_value/regmix_tables/train_mixture_1m.csv')
features = list(contract['mixture']['feature_order'])
a4 = a4raw[features].to_numpy(float)
a4 = a4 / a4.sum(axis=1, keepdims=True)

def p_for(row):
    if str(row['scenario_id']).startswith('S14'):
        return a4[135]
    if str(row['scenario_id']).startswith('S15'):
        return a4[135]
    if str(row['scenario_id']).startswith('S16'):
        return a4[428]
    return p0

for name in ['optimization_results.parquet']:
    d = pd.read_parquet(run / name)
    vals = np.vstack([p_for(r) for _, r in d.iterrows()])
    for j in range(17):
        d[f'p_{j}'] = vals[:, j]
    d['p_sum'] = vals.sum(axis=1)
    d['p_min'] = vals.min(axis=1)
    d.to_parquet(run / name, index=False)
for name in ['budget_scenario_optima.csv','transport_failure_sensitivity.csv','support_oos_audit.csv']:
    d = pd.read_csv(run / name)
    vals = np.vstack([p_for(r) for _, r in d.iterrows()])
    for j in range(17):
        d[f'p_{j}'] = vals[:, j]
    d['p_sum'] = vals.sum(axis=1)
    d['p_min'] = vals.min(axis=1)
    d.to_csv(run / name, index=False, encoding='utf-8-sig')
print('enriched')
