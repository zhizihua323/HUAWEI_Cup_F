# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
"""Synthetic (artificial) tests for the TASK-Q01C pipeline rules.

All expectations are derived either from pandas itself or from the documented
Q01B rules; the pipeline functions are only used as the "actual" side. No real
data is touched here: the tests run before A1-A3 may be read.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import quality_q01c as qc  # noqa: E402  (module under test, used as "actual")

RESULTS = []


def case(name, ok, detail):
    RESULTS.append({'test': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})


def base_frame(rows, domains=None, roles=None, unique=None):
    frame = pd.DataFrame(rows)
    for feature in qc.MODEL:
        if 'norm_' + feature not in frame.columns:
            frame['norm_' + feature] = 0.5
    if 'domain' not in frame.columns:
        frame['domain'] = domains if domains is not None else 'commoncrawl'
    if 'evaluation_role' not in frame.columns:
        frame['evaluation_role'] = roles if roles is not None else 'A1_calibration'
    if 'is_unique_first' not in frame.columns:
        frame['is_unique_first'] = unique if unique is not None else True
    if 'extract_nan_features' not in frame.columns:
        frame['extract_nan_features'] = ['' for _ in range(len(frame))]
    frame['extract_nan_features'] = frame['extract_nan_features'].fillna('')
    return frame


def scored(frame):
    return qc.finalize_primary_scores(frame.copy())


def test_all_valid():
    frame = base_frame([{} for _ in range(3)])
    out = scored(frame)
    expected_q = float(np.mean([out['group_usability'].iloc[0], out['group_knowledge'].iloc[0],
                                out['group_education_reasoning'].iloc[0]]))
    case('all_11_features_valid', bool(out['Q_valid'].all())
         and out['Q_missing_feature_count'].eq(0).all()
         and math.isclose(float(out['Q_baseline'].iloc[0]), 0.5, abs_tol=1e-12),
         {'Q_valid': out['Q_valid'].tolist(), 'Q_baseline': out['Q_baseline'].tolist(),
          'expected_group_mean': expected_q})


def test_single_missing(feature, group):
    frame = base_frame([{}, {}])
    frame.loc[0, 'norm_' + feature] = np.nan
    frame.loc[0, 'extract_nan_features'] = feature
    out = scored(frame)
    row = out.iloc[0]
    other_groups = [g for g in qc.GROUP_NAMES if g != group]
    no_reallocation = math.isnan(row['group_' + group]) and math.isnan(row['Q_baseline'])
    case(f'missing_{feature}_propagates', (not bool(row['Q_valid']))
         and int(row['Q_missing_feature_count']) == 1
         and row['Q_missing_features'] == feature
         and int(row['n_groups_valid']) == 2
         and no_reallocation
         and all(np.isfinite(row['group_' + g]) for g in other_groups)
         and bool(row['rater_disagreement_range_defined']),
         {'Q_valid': bool(row['Q_valid']), 'n_groups_valid': int(row['n_groups_valid']),
          'missing_features': row['Q_missing_features'],
          'group_values': {g: row['group_' + g] for g in qc.GROUP_NAMES},
          'range_defined': bool(row['rater_disagreement_range_defined'])})


def test_two_missing_one_group():
    frame = base_frame([{}])
    frame.loc[0, 'norm_modernbert_professionalism'] = np.nan
    frame.loc[0, 'norm_modernbert_reasoning'] = np.nan
    frame.loc[0, 'extract_nan_features'] = 'modernbert_professionalism|modernbert_reasoning'
    out = scored(frame)
    row = out.iloc[0]
    case('two_missing_features_one_valid_group', int(row['n_groups_valid']) == 1
         and int(row['Q_missing_feature_count']) == 2 and not bool(row['Q_valid'])
         and bool(row['rater_disagreement_range_defined'])
         and float(row['rater_disagreement_std']) == 0.0,
         {'n_groups_valid': int(row['n_groups_valid']),
          'std': float(row['rater_disagreement_std']),
          'range': float(row['rater_disagreement_range'])})


def test_zero_valid_groups():
    frame = base_frame([{}, {}])
    frame.loc[0, 'norm_ad_en'] = np.nan
    frame.loc[0, 'norm_modernbert_professionalism'] = np.nan
    frame.loc[0, 'norm_modernbert_reasoning'] = np.nan
    out = scored(frame)
    row = out.iloc[0]
    case('zero_valid_groups_range_undefined', int(row['n_groups_valid']) == 0
         and not bool(row['rater_disagreement_range_defined'])
         and math.isnan(row['rater_disagreement_range'])
         and math.isnan(row['rater_disagreement_std']),
         {'n_groups_valid': int(row['n_groups_valid']),
          'range_defined': bool(row['rater_disagreement_range_defined'])})


def test_pandas_skipna_agreement():
    values = [[0.2, 0.4, 0.6], [0.2, np.nan, 0.6], [0.2, np.nan, np.nan], [np.nan] * 3]
    frame = base_frame([{} for _ in values])
    for i, (usability, knowledge, education) in enumerate(values):
        frame.loc[i, 'norm_ad_en'] = usability
        frame.loc[i, 'norm_fluency_en'] = usability
        frame.loc[i, 'norm_modernbert_readability'] = usability
        frame.loc[i, 'norm_modernbert_cleanliness'] = usability
        frame.loc[i, 'norm_qurater_writing_style'] = usability
        frame.loc[i, 'norm_modernbert_professionalism'] = knowledge
        frame.loc[i, 'norm_qurater_required_expertise'] = knowledge
        frame.loc[i, 'norm_qurater_facts_trivia'] = knowledge
        frame.loc[i, 'norm_modernbert_reasoning'] = education
        frame.loc[i, 'norm_fineweb_edu'] = education
        frame.loc[i, 'norm_qurater_educational_value'] = education
    out = scored(frame)
    reference = pd.DataFrame(values, columns=qc.GROUP_NAMES)
    expected_range = (reference.max(axis=1) - reference.min(axis=1)).tolist()
    expected_std0 = reference.std(axis=1, ddof=0).tolist()
    actual_range = out['rater_disagreement_range'].tolist()
    actual_std0 = out['rater_disagreement_std'].tolist()
    ok = all((math.isnan(a) and math.isnan(b)) or math.isclose(a, b)
             for a, b in zip(expected_range, actual_range)) and \
        all((math.isnan(a) and math.isnan(b)) or math.isclose(a, b)
            for a, b in zip(expected_std0, actual_std0))
    case('disagreement_matches_pandas_skipna', ok,
         {'expected_range': expected_range, 'actual_range': actual_range,
          'expected_std0': expected_std0, 'actual_std0': actual_std0})


def test_q_std_divisor():
    frame = base_frame([{}, {}, {}])
    out = scored(frame)
    one = qc.summarize_scope(out.iloc[[0]].copy(), 'Q_baseline')
    two = qc.summarize_scope(out.iloc[[0, 1]].copy(), 'Q_baseline')
    expected_std = float(np.std([out['Q_baseline'].iloc[0], out['Q_baseline'].iloc[1]], ddof=1))
    case('q_std_effective_n_and_divisor', one['Q_std_status'] == 'UNDEFINED_N_LT_2'
         and one['Q_std_effective_n'] == 0 and two['Q_std_effective_n'] == 2
         and two['Q_std_variance_divisor'] == 1
         and math.isclose(two['Q_std'], expected_std),
         {'one': one['Q_std_status'], 'two_n': two['Q_std_effective_n'],
          'two_divisor': two['Q_std_variance_divisor'], 'std': two['Q_std']})


def calibration_frame(n_calibration=200, n_holdout=50, feature='modernbert_professionalism',
                      domain='github', unique_values=(0.0, 0.2, 0.4, 0.6, 1.0),
                      missing_in_calibration=0, holdout_value=1.0):
    rows = []
    rng = np.random.default_rng(12345)
    for i in range(n_calibration):
        missing = i < missing_in_calibration
        value = float('nan') if missing else unique_values[i % len(unique_values)]
        rows.append({'norm_' + feature: value, 'domain': domain,
                     'evaluation_role': 'A1_calibration', 'is_unique_first': True,
                     'extract_nan_features': feature if missing else ''})
    for i in range(n_holdout):
        rows.append({'norm_' + feature: holdout_value, 'domain': domain,
                     'evaluation_role': 'A1_holdout', 'is_unique_first': True,
                     'extract_nan_features': ''})
    return base_frame(rows)


def test_calibration_only_parameters():
    frame = calibration_frame(missing_in_calibration=1)
    params_before = qc.compute_sensitivity_parameters(frame)
    mutated = frame.copy()
    mutated.loc[mutated['evaluation_role'] != 'A1_calibration', 'norm_modernbert_professionalism'] = -999.0
    params_after = qc.compute_sensitivity_parameters(mutated)
    key = ('github', 'modernbert_professionalism')
    same = (params_before[key]['median'] == params_after[key]['median']
            and params_before[key]['n_valid'] == params_after[key]['n_valid']
            and params_before[key]['source_scope'] == 'A1_calibration & is_unique_first')
    calibration_only = frame[(frame['evaluation_role'] == 'A1_calibration')]['norm_modernbert_professionalism']
    case('sensitivity_parameters_calibration_only', same
         and math.isclose(params_before[key]['median'], float(calibration_only.median())),
         {'median_before': params_before[key]['median'], 'median_after': params_after[key]['median'],
          'calibration_median': float(calibration_only.median()),
          'candidates': params_before[key]['candidate_rows']})


def test_gate_failures():
    small = calibration_frame(n_calibration=50, missing_in_calibration=1)
    params_small = qc.compute_sensitivity_parameters(small)
    small_ok = params_small[('github', 'modernbert_professionalism')]['gate_ok']
    low_coverage = calibration_frame(n_calibration=200, missing_in_calibration=100)
    params_cov = qc.compute_sensitivity_parameters(low_coverage)
    coverage = params_cov[('github', 'modernbert_professionalism')]['coverage']
    single_value = calibration_frame(n_calibration=200, unique_values=(0.4,), missing_in_calibration=1)
    params_single = qc.compute_sensitivity_parameters(single_value)
    raised = False
    try:
        qc.require_all_gates(params_small)
    except qc.StageFailure:
        raised = True
    case('gate_hard_stop_no_fallback', (not small_ok) and raised and coverage < 0.95
         and (not params_cov[('github', 'modernbert_professionalism')]['gate_ok'])
         and (not params_single[('github', 'modernbert_professionalism')]['gate_ok']),
         {'small_n_valid': params_small[('github', 'modernbert_professionalism')]['n_valid'],
          'coverage_case': coverage, 'single_value_unique': params_single[
              ('github', 'modernbert_professionalism')]['n_unique_finite'],
          'gate_stop_raised': raised})


def multi_role_frame(domain='github', feature='modernbert_professionalism',
                     n_calibration=200, n_holdout=30, n_overlap=20, n_new=20,
                     missing_in_calibration=1):
    """Rows covering all four roles used by the recovery/sensitivity isolation test."""
    rows = []
    for index in range(n_calibration):
        missing = index < missing_in_calibration
        rows.append({'norm_' + feature: float('nan') if missing else (index % 5) * 0.2,
                     'domain': domain, 'evaluation_role': 'A1_calibration', 'is_unique_first': True,
                     'extract_nan_features': feature if missing else ''})
    for role, count, value in [('A1_holdout', n_holdout, 1.0),
                               ('extension_overlap_A1', n_overlap, 1.0),
                               ('extension_new_records', n_new, 1.0)]:
        for index in range(count):
            rows.append({'norm_' + feature: value, 'domain': domain, 'evaluation_role': role,
                         'is_unique_first': True, 'extract_nan_features': ''})
    return base_frame(rows)


def test_extension_role_isolation():
    domain, feature = 'github', 'modernbert_professionalism'
    frame = multi_role_frame(domain=domain, feature=feature)
    baseline = qc.compute_sensitivity_parameters(frame)[(domain, feature)]
    role_counts = {str(k): int(v) for k, v in frame['evaluation_role'].value_counts().items()}
    tracked = ['candidate_rows', 'n_valid', 'coverage', 'n_unique_finite', 'median', 'gate_ok',
               'source_scope']
    per_role = {}
    identical = True
    provenance = True
    for role in ['A1_holdout', 'extension_overlap_A1', 'extension_new_records']:
        mutated = frame.copy()
        mutated.loc[mutated['evaluation_role'] == role, 'norm_' + feature] = 0.0
        parameters = qc.compute_sensitivity_parameters(mutated)[(domain, feature)]
        per_role[role] = {key: parameters[key] for key in tracked}
        identical = identical and all(parameters[key] == baseline[key] for key in tracked)
        calibration_values = mutated[(mutated['evaluation_role'] == 'A1_calibration')][
            'norm_' + feature].dropna()
        provenance = provenance and (
            parameters['candidate_rows'] == int((mutated['evaluation_role'] == 'A1_calibration').sum())
            and parameters['n_valid'] == int(calibration_values.size)
            and parameters['source_scope'] == 'A1_calibration & is_unique_first')
    small = multi_role_frame(n_calibration=50, missing_in_calibration=1)
    params_small = qc.compute_sensitivity_parameters(small)[(domain, feature)]
    raised = False
    try:
        qc.require_all_gates({(domain, feature): params_small})
    except qc.StageFailure:
        raised = True
    case('extension_role_isolation',
         identical and provenance and raised and (not params_small['gate_ok']),
         {'role_counts': role_counts, 'baseline': {k: baseline[k] for k in tracked},
          'per_role_after_extreme_mutation': per_role,
          'provenance_calibration_only': provenance,
          'gate_failure_hard_stop_raised': raised,
          'small_case_n_valid': params_small['n_valid']})


def run_all_tests():
    del RESULTS[:]
    test_all_valid()
    test_single_missing('modernbert_professionalism', 'knowledge')
    test_single_missing('modernbert_reasoning', 'education_reasoning')
    test_two_missing_one_group()
    test_zero_valid_groups()
    test_pandas_skipna_agreement()
    test_q_std_divisor()
    test_calibration_only_parameters()
    test_gate_failures()
    test_extension_role_isolation()
    n_failed = sum(1 for r in RESULTS if r['status'] != 'PASS')
    return {'status': 'PASS' if not n_failed else 'FAIL', 'n_tests': len(RESULTS),
            'n_failed': n_failed, 'tests': list(RESULTS)}
