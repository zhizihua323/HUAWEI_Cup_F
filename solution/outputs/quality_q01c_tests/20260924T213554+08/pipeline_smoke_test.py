"""In-memory smoke test of the Q01C summarisation functions (no real data)."""
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
per_domain = 400
domains = ['commoncrawl'] * per_domain + ['wikipedia'] * per_domain + ['github'] * per_domain
roles = ['A1_calibration'] * (3 * per_domain) + ['extension_new_records'] * 60
all_domains = domains + ['github'] * 60
n = len(all_domains)
rows = {
    'file_id': ['A1'] * (3 * per_domain) + ['A3_github'] * 60,
    'source_line': list(range(1, n + 1)),
    'id_json': ['"x"'] * n, 'sub_path_json': ['"p"'] * n,
    'key_sha256': [f'k{i:05d}' for i in range(n)],
    'quality_sha256': [f'q{i:05d}' for i in range(n)],
    'domain': all_domains, 'domain_source': ['raw'] * n,
    'is_unique_first': [True] * n, 'overlap_a1': [False] * n,
    'evaluation_role': roles,
    'raw_invalid_fields': [''] * n, 'raw_anomaly_json': [''] * n,
    'extract_nan_features': [''] * n, 'extract_nonfinite_features': [''] * n,
    'raw_invalid_count': [0] * n, 'extract_nan_count': [0] * n}
for feature in qc.FEATURES:
    rows[feature] = rng.random(n)
missing_index = per_domain + 5
rows['extract_nan_features'][missing_index] = 'modernbert_professionalism'
rows['extract_nan_count'][missing_index] = 1
frame = pd.DataFrame(rows)
for feature in qc.MODEL:
    frame['norm_' + feature] = frame[feature]
frame.loc[missing_index, 'norm_modernbert_professionalism'] = np.nan
frame = qc.finalize_primary_scores(frame)
frame[qc.SENSITIVITY_COLUMN] = frame['Q_baseline']
frame['sensitivity_imputed_count'] = 0
frame['sensitivity_imputed_features'] = ''
params = qc.compute_sensitivity_parameters(frame)
qc.require_all_gates(params)
audit, raw_rows = qc.build_audit_and_raw_counts(frame)
domain_rows = []
sensitivity_rows = []
denominator_rows = []
for scope, fn in qc.SCOPE_DEFS:
    part = frame[fn(frame)]
    if part.empty:
        continue
    row = qc.summarize_scope(part, 'Q_baseline')
    row.update({'scope': scope, 'domain': 'ALL'})
    domain_rows.append(row)
    denominator_rows.extend(qc.build_denominator_rows(scope, 'ALL', row))
    srow = qc.summarize_scope(part.assign(**{qc.SENSITIVITY_COLUMN: part['Q_baseline']}),
                              qc.SENSITIVITY_COLUMN)
    srow.update({'scope': scope, 'domain': 'ALL'})
    sensitivity_rows.append(srow)
feature_rows = qc.build_feature_summary(frame)
shift_rows = qc.build_extension_shift(frame)
correlations, pending = qc.build_indicator_diagnostics(frame)
bootstrap = qc.build_bootstrap(frame)
ctx = SimpleNamespace(run_id='smoke')
report = qc.build_report(ctx, audit, domain_rows, sensitivity_rows, [],
                         {'all_gates_passed': True, 'imputed_records_total': 1})
assert audit['total_records'] == n
assert int(frame['Q_valid'].sum()) == n - 1
assert len(raw_rows) > 0 and len(feature_rows) > 0 and len(shift_rows) > 0
assert len(correlations) > 0 and len(pending) == len(qc.EXCLUDED_FROM_MAIN_Q) and len(bootstrap) > 0
assert params[('wikipedia', 'modernbert_professionalism')]['gate_ok'] is True
assert 'Q01C' in report
print('SMOKE_OK', {'rows': n, 'q_valid': int(frame['Q_valid'].sum()),
                   'n_parameters': len(params), 'denominator_rows': len(denominator_rows),
                   'bootstrap_rows': len(bootstrap), 'feature_rows': len(feature_rows),
                   'shift_rows': len(shift_rows), 'domain_rows': len(domain_rows)})
