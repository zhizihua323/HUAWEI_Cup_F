import pathlib
p = pathlib.Path('tmp/evidence_build/build_registry.py')
s = p.read_text(encoding='utf-8')

old = """met = pd.read_csv(MIX / 'metrics.csv')
def M(model, s, col):
    r = met[(met.model == model) & (met.set == s)]
    return float(r[col].iloc[0])"""
new = """met = pd.read_csv(MIX / 'metrics.csv')
def _s(x):
    \"\"\"Full round-trip decimal text (pandas/numpy str() truncates to 16 sig digits).\"\"\"
    return repr(float(x))
def M(model, s, col):
    r = met[(met.model == model) & (met.set == s)]
    return _s(r[col].iloc[0])"""
assert old in s
s = s.replace(old, new)

old2 = """def MC(cfg, col):
    return float(mc[mc.configuration == cfg][col].iloc[0])
ev = pd.read_csv(SCL / 'external_validation.csv')
def EV(tag, col):
    return float(ev[(ev.table == tag) & (ev.group == 'all')][col].iloc[0])"""
new2 = """def MC(cfg, col):
    return _s(mc[mc.configuration == cfg][col].iloc[0])
ev = pd.read_csv(SCL / 'external_validation.csv')
def EV(tag, col):
    return _s(ev[(ev.table == tag) & (ev.group == 'all')][col].iloc[0])"""
assert old2 in s
s = s.replace(old2, new2)

old3 = 'value=f"{float(_r.median())}|'
new3 = 'value=f"{_s(_r.median())}|'
assert old3 in s
s = s.replace(old3, new3)

old4 = """    value=f"{float(qb6[qb6.split=='Q_train_le_0.6_test_gt_0.6'].RMSE.iloc[0])}|{float(qb6[qb6.split=='Q_train_le_0.6_test_gt_0.6'].bias_pred_minus_actual.iloc[0])}","""
new4 = """    value=f"{_s(qb6[qb6.split=='Q_train_le_0.6_test_gt_0.6'].RMSE.iloc[0])}|{_s(qb6[qb6.split=='Q_train_le_0.6_test_gt_0.6'].bias_pred_minus_actual.iloc[0])}","""
assert old4 in s
s = s.replace(old4, new4)
p.write_text(s, encoding='utf-8')
print('patched build_registry.py -> full-precision text')
