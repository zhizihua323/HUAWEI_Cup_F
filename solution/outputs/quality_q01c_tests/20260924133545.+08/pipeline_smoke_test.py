"""In-memory smoke test of the Q01C pure summarisation functions (no real data)."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd

SOLUTION = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SOLUTION / 'src'))
import quality_q01c as qc

rng = np.random.default_rng(7)
n = 40
rows = {
    'file_id': ['A1'] * 20 + ['A3_github'] * 20,
    'source_line': list(range(1, 21)) * 2,
    'id_json': ['"x"'] * n, 'sub_path_json': ['"p"'] * n,
    'key_sha256': [f'k{i:03d}' for i in range(n)], 'quality_sha256': [f'q{i:03d}' for i in range(n)],
    'domain': ['commoncrawl'] * 10 + ['wikipedia'] * 10 + ['github'] * 20,
    'domain_source': ['raw'] * n,
    'is_unique_first': [True] * n, 'overlap_a1': [False] * n,
    'evaluation_role': ['A1_calibration'] * 20 + ['extension_new_records'] * 20,
    'raw_invalid_fields': [''] * n, 'raw_anomaly_json': [''] * n,
    'extract_nan_features': [''] * n, 'extract_nonfinite_features': [''] * n,
    'raw_invalid_count': [0] * n, 'extract_nan_count': [0] * n}
for feature in qc.FEATURES:
    rows[feature] = rng.random(n)
rows['extract_nan_features'][3] = 'modernbert_professionalism'
rows['extract_nan_count'][3] = 1
frame = pd.DataFrame(rows)
for feature in qc.MODEL:
    frame['norm_' + feature] = frame[feature]
frame.loc[3, 'norm_modernbert_professionalism'] = np.nan
frame = qc.finalize_primary_scores(frame)
params = qc.compute_sensitivity_parameters(frame)
qc.require_all_gates(params)
audit, raw_rows = qc.build_audit_and_raw_counts(frame)
domain_rows = []
denominator_rows = []
for scope, fn in qc.SCOPE_DEFS:
    part = frame[fn(frame)]
    if part.empty:
        continue
    row = qc.summarize_scope(part, 'Q_baseline')
    row.update({'scope': scope, 'domain': 'ALL'})
    domain_rows.append(row)
    denominator_rows.extend(qc.build_denominator_rows(scope, 'ALL', row))
feature_rows = qc.build_feature_summary(frame)
shift_rows = qc.build_extension_shift(frame)
correlations, pending = qc.build_indicator_diagnostics(frame)
bootstrap = qc.build_bootstrap(frame)
ctx = SimpleNamespace(run_id='smoke')
report = qc.build_report(ctx, audit, domain_rows, domain_rows, [], {'all_gates_passed': True,
                                                                   'imputed_records_total': 1})
assert audit['total_records'] == n
assert int(frame['Q_valid'].sum()) == n - 1
assert len(raw_rows) > 0 and len(feature_rows) > 0 and len(shift_rows) > 0
assert len(correlations) > 0 and len(pending) == len(qc.EXCLUDED_FROM_MAIN_Q) and len(bootstrap) > 0
assert 'Q01C' in report
print('SMOKE_OK', json_dump := {'rows': n, 'q_valid': int(frame['Q_valid'].sum()),
                                'denominator_rows': len(denominator_rows),
                                'bootstrap_rows': len(bootstrap)})
