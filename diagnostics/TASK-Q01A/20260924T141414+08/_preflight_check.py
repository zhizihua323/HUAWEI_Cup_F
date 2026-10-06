import sys, json
from pathlib import Path
RUN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN_DIR))
import diagnose_missingness as dm

class P:
    def __call__(self, m): pass
log = P()
transforms = dm.verify_normalization(dm.read_json(dm.QUALITY_OUT / 'normalization.json'))['transforms']
syn = dm.synthetic_selftest(log, transforms)
print('synthetic status:', syn['status'], 'cases:', syn['n_cases'], 'failed:', syn['n_failed'])
for c in syn['cases']:
    if c['status'] != 'PASS':
        print('  FAIL', c['name'], c['detail'][:200])
print('mini:', json.dumps(syn['mini_aggregation'], ensure_ascii=False)[:400])
src = dm.verify_source_spec()
print('source spec checks:', src['checks'])
