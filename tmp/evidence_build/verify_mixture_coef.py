import pandas as pd, numpy as np, json, itertools

mj = json.load(open('solution/outputs/mixture/model.json', encoding='utf-8'))
feats = mj['features']

def design(p, family):
    X = p.copy()
    if family == 'quadratic':
        extra = np.column_stack([p[:, i] * p[:, j] for i, j in itertools.combinations(range(p.shape[1]), 2)])
        X = np.column_stack([p, extra])
    return X

sets = ['train_1m', 'test_1m', 'test_60m', 'test_1B', 'est_10b', 'est_70b']
worst = {}
for family in ['linear', 'quadratic']:
    coef = pd.read_csv(f'solution/outputs/mixture/{family}_coefficients.csv')
    C = coef.iloc[:, 1:].to_numpy(float)
    terms = coef['term'].tolist()
    w = 0.0
    for lab in sets:
        d = pd.read_csv(f'solution/outputs/mixture/{lab}_normalized_mixtures.csv')
        p = d[feats].to_numpy(float)
        X = design(p, family)
        assert X.shape[1] == C.shape[0], (family, lab, X.shape, C.shape)
        pred = X @ C
        saved = pd.read_csv(f'solution/outputs/mixture/{family}_{lab}_predictions.csv')
        P = saved[[c for c in saved.columns if c.startswith('pred_')]].to_numpy(float)
        e = float(np.max(np.abs(pred - P)))
        w = max(w, e)
        print(f'{family:9s} {lab:9s} n={len(p):4d} max|X@coef - saved_pred| = {e:.3e}')
    worst[family] = w
print('worst per family:', worst)
