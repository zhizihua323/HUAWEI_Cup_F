import hashlib, csv, json, pathlib
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

inv = list(csv.DictReader(open('recovery/2026-09-24/solution_inventory.csv', encoding='utf-8-sig')))
mism, missing, ok = [], [], 0
for r in inv:
    p = pathlib.Path(r['path'])
    if not p.exists():
        missing.append(str(p)); continue
    if sha(p) == r['sha256']:
        ok += 1
    else:
        mism.append(str(p))
print('solution inventory rows:', len(inv))
print('unchanged:', ok, '| mismatched:', len(mism), '| missing:', len(missing))
for m in mism + missing: print('  ', m)

cc = json.load(open('recovery/2026-09-24/completion_check.json', encoding='utf-8'))
bad = [d['path'] for d in cc['project_docs'] if sha(d['path']) != d['sha256']]
print('project docs unchanged:', len(cc['project_docs']) - len(bad), '/', len(cc['project_docs']), '| changed:', bad)

import pandas as pd
reg = pd.read_csv('evidence/baseline_result_registry.csv')
print()
print('registry shape:', reg.shape)
print('claim_level counts:', reg.claim_level.value_counts().to_dict())
print('verification counts:', reg.verification.value_counts().to_dict())
print('null cells:', int(reg.isna().sum().sum()))
