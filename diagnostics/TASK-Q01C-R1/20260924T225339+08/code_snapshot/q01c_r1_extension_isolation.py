"""TASK-Q01C-R1 extension-role imputation isolation test (synthetic only).

Builds a synthetic frame with A1_calibration / A1_holdout / extension_overlap_A1 /
extension_new_records rows, mutates the target feature to extreme values in each
non-calibration role in turn, and proves that the calibration parameter set
(candidates, valid n, coverage, unique finite values, median) is bit-identical.
Also proves that a failing sufficiency gate still hard-stops.
No real parquet or attachment is read.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOLUTION = Path(__file__).resolve().parents[1]
SRC = SOLUTION / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import quality_q01c as qc            # noqa: E402
import quality_q01c_selftest as st    # noqa: E402

CST = timezone(timedelta(hours=8))
DOMAIN = 'github'
FEATURE = 'modernbert_professionalism'
ROLES = ['A1_holdout', 'extension_overlap_A1', 'extension_new_records']
TRACKED = ['candidate_rows', 'n_valid', 'coverage', 'n_unique_finite', 'median', 'gate_ok',
           'source_scope']


def main(argv=None):
    parser = argparse.ArgumentParser(description='Q01C-R1 extension isolation test')
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    frame = st.multi_role_frame(domain=DOMAIN, feature=FEATURE)
    role_counts = {str(k): int(v) for k, v in frame['evaluation_role'].value_counts().items()}
    baseline = qc.compute_sensitivity_parameters(frame)[(DOMAIN, FEATURE)]
    per_role = {}
    all_identical = True
    provenance_ok = True
    for role in ROLES:
        mutated = frame.copy()
        mutated.loc[mutated['evaluation_role'] == role, 'norm_' + FEATURE] = 0.0
        parameters = qc.compute_sensitivity_parameters(mutated)[(DOMAIN, FEATURE)]
        per_role[role] = {key: parameters[key] for key in TRACKED}
        all_identical = all_identical and all(parameters[key] == baseline[key] for key in TRACKED)
        calibration_values = mutated[mutated['evaluation_role'] == 'A1_calibration'][
            'norm_' + FEATURE].dropna()
        provenance_ok = provenance_ok and (
            parameters['candidate_rows'] == int((mutated['evaluation_role'] == 'A1_calibration').sum())
            and parameters['n_valid'] == int(calibration_values.size)
            and parameters['source_scope'] == 'A1_calibration & is_unique_first')
    small = st.multi_role_frame(n_calibration=50, missing_in_calibration=1)
    params_small = qc.compute_sensitivity_parameters(small)[(DOMAIN, FEATURE)]
    hard_stop = False
    try:
        qc.require_all_gates({(DOMAIN, FEATURE): params_small})
    except qc.StageFailure:
        hard_stop = True
    status = 'PASS' if (all_identical and provenance_ok and hard_stop
                        and not params_small['gate_ok']) else 'FAIL'
    payload = {
        'test': 'extension_role_isolation', 'status': status,
        'generated_local': datetime.now(CST).isoformat(timespec='seconds'),
        'source': 'synthetic rows only (quality_q01c_selftest.multi_role_frame); no real parquet read',
        'domain': DOMAIN, 'feature': FEATURE,
        'role_row_counts': role_counts,
        'baseline_parameters': {key: baseline[key] for key in TRACKED},
        'after_extreme_mutation': per_role,
        'calibration_parameters_identical_after_every_mutation': all_identical,
        'parameters_sourced_from_calibration_only': provenance_ok,
        'gate_failure_hard_stop': hard_stop,
        'small_sample_gate': params_small}
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': status, 'identical': all_identical,
                      'provenance': provenance_ok, 'hard_stop': hard_stop,
                      'out': str(args.out)}, ensure_ascii=False), flush=True)
    return 0 if status == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
