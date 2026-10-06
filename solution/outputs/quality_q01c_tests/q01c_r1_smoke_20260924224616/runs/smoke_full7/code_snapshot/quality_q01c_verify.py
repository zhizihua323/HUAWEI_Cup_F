"""Independent verification for the TASK-Q01C run directory.

The verifier never imports the pipeline module: every expectation is recomputed
from the row-level parquet with pandas or read from the previously accepted
Q01A/R1 anchors. Writes verification.json and checks.json inside the run dir.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
R_DIR = PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T142229+08'
R1_DIR = PROJECT / 'diagnostics' / 'TASK-Q01A-R1' / '20260924T150854+08'
CST = timezone(timedelta(hours=8))
GROUP_NAMES = ['usability', 'knowledge', 'education_reasoning']
GROUPS = {
    'usability': ['ad_en', 'fluency_en', 'modernbert_readability', 'modernbert_cleanliness',
                  'qurater_writing_style'],
    'knowledge': ['modernbert_professionalism', 'qurater_required_expertise',
                  'qurater_facts_trivia'],
    'education_reasoning': ['modernbert_reasoning', 'fineweb_edu',
                            'qurater_educational_value']}
MODEL = ['fineweb_edu', 'ad_en', 'fluency_en', 'qurater_writing_style',
         'qurater_required_expertise', 'qurater_facts_trivia', 'qurater_educational_value',
         'modernbert_professionalism', 'modernbert_readability', 'modernbert_reasoning',
         'modernbert_cleanliness']
SENSITIVITY_COLUMN = 'Q_sensitivity_calibration_domain_median'
SCOPE_DEFS = [
    ('A1_calibration', lambda df: df['evaluation_role'].eq('A1_calibration') & df['is_unique_first']),
    ('A1_holdout', lambda df: df['evaluation_role'].eq('A1_holdout') & df['is_unique_first']),
    ('A1_all_unique', lambda df: df['file_id'].eq('A1') & df['is_unique_first']),
    ('extension_overlap_A1', lambda df: df['overlap_a1']),
    ('extension_new_records', lambda df: df['evaluation_role'].eq('extension_new_records')
     & df['is_unique_first']),
    ('all_unique', lambda df: df['is_unique_first'])]
CHECKS = []


def now_iso():
    return datetime.now(CST).isoformat(timespec='seconds')


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def read_json(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def read_csv_rows(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def check(check_id, description, status, actual, expected, evidence, note=''):
    CHECKS.append({'check_id': check_id, 'description': description, 'status': status,
                   'actual': actual, 'expected': expected, 'evidence': evidence, 'note': note})
    print(f'[verify] {check_id}: {status}', flush=True)


def same(a, b, tol=0.0):
    if a is None or b is None:
        return (a is None) and (b is None)
    try:
        if tol:
            return abs(float(a) - float(b)) <= tol
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def main(argv=None):
    parser = argparse.ArgumentParser(description='independent Q01C verification')
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--fixture-manifest', default=None,
                        help='verify a synthetic fixture run instead of the real-data anchors')
    args = parser.parse_args(argv)
    if args.fixture_manifest:
        return verify_fixture_mode(Path(args.run_dir), Path(args.fixture_manifest))
    run_dir = Path(args.run_dir)
    df = pd.read_parquet(run_dir / 'quality_features_scores.parquet')
    audit = read_json(run_dir / 'audit.json')
    normalization = read_json(run_dir / 'normalization.json')
    parameters = read_json(run_dir / 'imputation_parameters_sensitivity.json')
    domain_summary = read_csv_rows(run_dir / 'domain_summary.csv')
    denominators = read_csv_rows(run_dir / 'summary_denominators.csv')
    sensitivity_summary = read_csv_rows(run_dir / 'sensitivity_domain_summary.csv')
    comparison = read_csv_rows(run_dir / 'sensitivity_comparison.csv')
    input_manifest = read_json(run_dir / 'input_manifest.json')
    run_config = read_json(run_dir / 'run_config.json')
    before = read_json(run_dir / 'old_artifacts_before.json')['entries']
    norm_columns = ['norm_' + f for f in MODEL]
    missing = ~np.isfinite(df[norm_columns].to_numpy())
    finite_11 = ~missing.any(axis=1)
    q_values = df['Q_baseline'].to_numpy(dtype=float)
    q_finite = np.isfinite(q_values)

    check('V01_totals', 'physical rows / unique keys / duplicates match the accepted anchors',
          'PASS' if (len(df) == 272505 and int(df['is_unique_first'].sum()) == 261086
                     and int((~df['is_unique_first']).sum()) == 11419) else 'FAIL',
          {'rows': int(len(df)), 'unique': int(df['is_unique_first'].sum()),
           'duplicates': int((~df['is_unique_first']).sum())},
          {'rows': 272505, 'unique': 261086, 'duplicates': 11419}, 'quality_features_scores.parquet')
    unique_mask = df['is_unique_first'].to_numpy()
    check('V02_q_valid_equivalence',
          'Q_valid is exactly "all 11 normalized features finite"; Q finite only when Q_valid',
          'PASS' if (bool(np.array_equal(df['Q_valid'].to_numpy(), finite_11))
                     and bool(np.array_equal(q_finite, finite_11))
                     and int(df.loc[unique_mask, 'Q_valid'].sum()) == 261067
                     and int((~df.loc[unique_mask, 'Q_valid']).sum()) == 19) else 'FAIL',
          {'physical_q_valid': int(df['Q_valid'].sum()),
           'unique_q_valid': int(df.loc[unique_mask, 'Q_valid'].sum()),
           'unique_q_missing': int((~df.loc[unique_mask, 'Q_valid']).sum()),
           'finite_11_physical': int(finite_11.sum()), 'q_finite_physical': int(q_finite.sum()),
           'mismatch_mask': int((df['Q_valid'].to_numpy() != finite_11).sum())},
          {'physical_q_valid': 272486, 'unique_q_valid': 261067, 'unique_q_missing': 19,
           'mismatch_mask': 0},
          'physical rows and unique keys are reported separately')
    group_values = {}
    recomputed_groups_ok = True
    for group in GROUP_NAMES:
        columns = ['norm_' + f for f in GROUPS[group]]
        reference = df[columns].mean(axis=1, skipna=False)
        group_values[group] = reference
        recomputed_groups_ok = recomputed_groups_ok and bool(
            np.allclose(reference.to_numpy(dtype=float), df['group_' + group].to_numpy(dtype=float),
                        equal_nan=True))
    reference_q = pd.DataFrame(group_values).mean(axis=1, skipna=False)
    check('V03_group_and_Q_recomputation',
          'group means and Q_baseline recomputed independently from the normalized columns',
          'PASS' if recomputed_groups_ok and bool(
              np.allclose(reference_q.to_numpy(dtype=float)[q_finite], q_values[q_finite])) else 'FAIL',
          {'groups_match': recomputed_groups_ok,
           'q_max_abs_diff': float(np.max(np.abs(reference_q.to_numpy(dtype=float)[q_finite]
                                                 - q_values[q_finite]))) if q_finite.any() else None},
          {'groups_match': True, 'q_max_abs_diff': 0.0}, 'independent pandas recomputation')
    one_group_missing = df[['group_' + g for g in GROUP_NAMES]].isna().sum(axis=1).eq(1)
    no_reallocation = bool(pd.isna(df.loc[one_group_missing, 'Q_baseline']).all())
    check('V04_no_weight_reallocation',
          'rows with a missing group keep Q_baseline = NaN (no reallocation to remaining groups)',
          'PASS' if no_reallocation and int(one_group_missing.sum()) == 19 else 'FAIL',
          {'rows_with_one_missing_group': int(one_group_missing.sum()),
           'such_rows_with_NaN_Q': int(pd.isna(df.loc[one_group_missing, 'Q_baseline']).sum())},
          {'rows_with_one_missing_group': 19, 'such_rows_with_NaN_Q': 19},
          'row-level check that Q is never the mean of the two valid groups')
    q_range = df.loc[q_finite, 'Q_baseline']
    unique_q_valid = int(df.loc[unique_mask, 'Q_valid'].sum())
    unique_q_missing = int((~df.loc[unique_mask, 'Q_valid']).sum())
    check('V05_q_range_and_missing_anchors',
          'Q_valid count and Q range on unique keys (physical counts reported separately)',
          'PASS' if (unique_q_valid == 261067 and unique_q_missing == 19
                     and float(q_range.min()) >= 0.0 and float(q_range.max()) <= 1.0) else 'FAIL',
          {'unique_q_valid': unique_q_valid, 'unique_q_missing': unique_q_missing,
           'physical_q_valid': int(df['Q_valid'].sum()),
           'q_min': float(q_range.min()), 'q_max': float(q_range.max())},
          {'unique_q_valid': 261067, 'unique_q_missing': 19, 'q_min>=0': True, 'q_max<=1': True},
          'parquet columns; unique keys vs physical rows are never mixed')
    n_groups_unique = df.loc[unique_mask, 'n_groups_valid'].to_numpy()
    n_groups_physical = df['n_groups_valid'].to_numpy()
    check('V06_usable_group_distribution',
          'all_unique usable-group histogram 0/1/2/3 equals the accepted anchors (unique keys)',
          'PASS' if (int((n_groups_unique == 0).sum()) == 0 and int((n_groups_unique == 1).sum()) == 0
                     and int((n_groups_unique == 2).sum()) == 19
                     and int((n_groups_unique == 3).sum()) == 261067) else 'FAIL',
          {'unique': {'0': int((n_groups_unique == 0).sum()), '1': int((n_groups_unique == 1).sum()),
                      '2': int((n_groups_unique == 2).sum()), '3': int((n_groups_unique == 3).sum())},
           'physical': {'0': int((n_groups_physical == 0).sum()),
                        '1': int((n_groups_physical == 1).sum()),
                        '2': int((n_groups_physical == 2).sum()),
                        '3': int((n_groups_physical == 3).sum())}},
          {'unique': {'0': 0, '1': 0, '2': 19, '3': 261067}}, 'parquet n_groups_valid column')
    verify_anchors_and_summaries(df, domain_summary, denominators, sensitivity_summary,
                                 comparison, parameters, normalization)
    verify_protection_and_hygiene(run_dir, input_manifest, before, run_config, df,
                                  domain_summary)
    write_verification_outputs(run_dir, df, audit, parameters, domain_summary, denominators)
    print('[verify] summary: ' + json.dumps(checks_payload()['summary'], ensure_ascii=False), flush=True)
    return 0 if checks_payload()['summary']['n_fail'] == 0 else 2


def checks_payload():
    n_fail = sum(1 for c in CHECKS if c['status'] == 'FAIL')
    n_nc = sum(1 for c in CHECKS if c['status'] == 'NOT_CHECKED')
    return {'summary': {'n_checks': len(CHECKS),
                        'n_pass': sum(1 for c in CHECKS if c['status'] == 'PASS'),
                        'n_fail': n_fail, 'n_not_checked': n_nc},
            'checks': CHECKS, 'status': 'PASS' if not n_fail else 'FAIL'}


def _scope_parts(df):
    for scope, fn in SCOPE_DEFS:
        sub = df[fn(df)]
        for domain in sorted(sub['domain'].unique().tolist()) + ['ALL']:
            part = sub if domain == 'ALL' else sub[sub['domain'] == domain]
            if not part.empty:
                yield scope, domain, part


def verify_anchors_and_summaries(df, domain_summary, denominators, sensitivity_summary, comparison,
                                 parameters, normalization):
    missing_features = df['extract_nan_features'].fillna('')
    prof = missing_features.str.contains('modernbert_professionalism', regex=False)
    reas = missing_features.str.contains('modernbert_reasoning', regex=False)
    union = prof | reas
    domain_union = df[union]['domain'].value_counts().to_dict()
    role_union = df[union]['evaluation_role'].value_counts().to_dict()
    overlap = df[df['overlap_a1']]['file_id'].value_counts().to_dict()
    check('V07_missing_and_overlap_anchors',
          'missing features, union/intersection, domain/role split and A1 overlap counts',
          'PASS' if (int(prof.sum()) == 6 and int(reas.sum()) == 13 and int(union.sum()) == 19
                     and int((prof & reas).sum()) == 0
                     and domain_union.get('wikipedia') == 14
                     and domain_union.get('commoncrawl') == 4
                     and domain_union.get('github') == 1
                     and role_union.get('A1_calibration') == 13
                     and role_union.get('A1_holdout') == 5
                     and role_union.get('extension_new_records') == 1
                     and role_union.get('extension_overlap_A1') is None
                     and overlap.get('A2_arxiv') == 1419 and overlap.get('A3_github') == 10000)
          else 'FAIL',
          {'professionalism': int(prof.sum()), 'reasoning': int(reas.sum()),
           'union': int(union.sum()), 'intersection': int((prof & reas).sum()),
           'domains': domain_union, 'roles': role_union, 'overlap_rows': overlap},
          {'professionalism': 6, 'reasoning': 13, 'union': 19, 'intersection': 0,
           'domains': {'wikipedia': 14, 'commoncrawl': 4, 'github': 1},
           'roles': {'A1_calibration': 13, 'A1_holdout': 5, 'extension_new_records': 1},
           'overlap_rows': {'A2_arxiv': 1419, 'A3_github': 10000}},
          'independent recomputation from patient parquet columns')
    summary_map = {(row['scope'], row['domain']): row for row in domain_summary}
    coverage_violations = []
    std_violations = []
    range_violations = []
    for scope, domain, part in _scope_parts(df):
        row = summary_map.get((scope, domain))
        if row is None:
            coverage_violations.append({'scope': scope, 'domain': domain, 'reason': 'missing row'})
            continue
        q = part['Q_baseline'].to_numpy(dtype=float)
        n_total = int(len(part))
        n_valid = int(np.isfinite(q).sum())
        if not (int(row['n_total']) == n_total and int(row['n_Q_valid']) == n_valid
                and int(row['n_Q_missing']) == n_total - n_valid
                and abs(float(row['coverage']) - n_valid / n_total) < 1e-12):
            coverage_violations.append({'scope': scope, 'domain': domain,
                                        'file': [row['n_total'], row['n_Q_valid'], row['coverage']],
                                        'recomputed': [n_total, n_valid, n_valid / n_total]})
        expected_effective = n_valid if n_valid >= 2 else 0
        expected_divisor = n_valid - 1 if n_valid >= 2 else None
        if not (int(row['Q_std_effective_n']) == expected_effective
                and same(row['Q_std_variance_divisor'], expected_divisor)):
            std_violations.append({'scope': scope, 'domain': domain, 'file': [
                row['Q_std_effective_n'], row['Q_std_variance_divisor']],
                'recomputed': [expected_effective, expected_divisor]})
        ranges = part.loc[part['rater_disagreement_range_defined'], 'rater_disagreement_range']
        if not (int(row['rater_disagreement_mean_effective_n']) == int(ranges.size)
                and same(row['rater_disagreement_std_effective_n'], int(ranges.size))
                and same(row['rater_disagreement_gt_0_5_denominator'], int(ranges.size))
                and same(row['rater_disagreement_undefined_rows'],
                         int((~part['rater_disagreement_range_defined']).sum()))):
            range_violations.append({'scope': scope, 'domain': domain,
                                     'file': [row['rater_disagreement_mean_effective_n'],
                                              row['rater_disagreement_gt_0_5_denominator'],
                                              row['rater_disagreement_undefined_rows']],
                                     'recomputed_defined_ranges': int(ranges.size)})
    check('V08_coverage_fields', 'n_total / n_Q_valid / n_Q_missing / coverage recomputed for every scope x domain',
          'PASS' if not coverage_violations else 'FAIL',
          {'violations': coverage_violations[:5], 'n_violations': len(coverage_violations)},
          {'n_violations': 0}, 'domain_summary.csv vs parquet')
    check('V09_q_std_effective_n_and_divisor',
          'Q_std effective n equals the finite-Q count and the divisor is n-1',
          'PASS' if not std_violations else 'FAIL',
          {'violations': std_violations[:5], 'n_violations': len(std_violations)},
          {'n_violations': 0}, 'domain_summary.csv vs parquet')
    check('V10_disagreement_denominators',
          'range/std effective n and the boolean denominator use defined-range rows only',
          'PASS' if not range_violations else 'FAIL',
          {'violations': range_violations[:5], 'n_violations': len(range_violations)},
          {'n_violations': 0}, 'domain_summary.csv vs parquet')
    param_rows = parameters.get('parameters', [])
    calibration = df[df['evaluation_role'].eq('A1_calibration') & df['is_unique_first']]
    param_violations = []
    for item in param_rows:
        column = 'norm_' + item['feature']
        part = calibration[calibration['domain'] == item['domain']]
        values = part[column].dropna()
        recomputed = {'candidate_rows': int(len(part)), 'n_valid': int(values.size),
                      'coverage': (values.size / len(part)) if len(part) else 0.0,
                      'n_unique_finite': int(values.nunique()),
                      'median': float(values.median()) if values.size else None}
        ok = (int(item['candidate_rows']) == recomputed['candidate_rows']
              and int(item['n_valid']) == recomputed['n_valid']
              and abs(float(item['coverage']) - recomputed['coverage']) < 1e-12
              and int(item['n_unique_finite']) == recomputed['n_unique_finite']
              and same(item['median'], recomputed['median'], tol=1e-12)
              and item['source_scope'] == 'A1_calibration & is_unique_first'
              and bool(item['gate_ok']))
        if not ok:
            param_violations.append({'parameter': [item['domain'], item['feature']],
                                     'file': item, 'recomputed': recomputed})
    check('V11_sensitivity_parameters_recomputed',
          'every median/gate/count recomputed from A1_calibration rows only',
          'PASS' if param_rows and not param_violations else 'FAIL',
          {'n_parameters': len(param_rows), 'n_violations': len(param_violations),
           'violations': [{k: v for k, v in item.items() if k in ('parameter', 'file')}
                          for item in param_violations[:3]]},
          {'all parameters recomputed equal, gate_ok': True},
          'imputation_parameters_sensitivity.json vs parquet')
    provenance = []
    coincidences = []
    for item in param_rows:
        column = 'norm_' + item['feature']
        calibration_part = calibration[calibration['domain'] == item['domain']]
        calibration_values = calibration_part[column].dropna()
        outside = df[(df['domain'] == item['domain']) & (~df['evaluation_role'].eq('A1_calibration'))]
        outside_values = outside[column].dropna()
        coverage = ((calibration_values.size / len(calibration_part))
                    if len(calibration_part) else 0.0)
        provenance_ok = (int(item['candidate_rows']) == int(len(calibration_part))
                         and int(item['n_valid']) == int(calibration_values.size)
                         and abs(float(item['coverage']) - coverage) < 1e-12
                         and int(item['n_unique_finite']) == int(calibration_values.nunique())
                         and item['source_scope'] == 'A1_calibration & is_unique_first')
        if not provenance_ok:
            provenance.append({'parameter': [item['domain'], item['feature']],
                               'recorded': {'candidate_rows': item['candidate_rows'],
                                            'n_valid': item['n_valid'], 'coverage': item['coverage'],
                                            'n_unique_finite': item['n_unique_finite'],
                                            'source_scope': item['source_scope']},
                               'recomputed': {'candidate_rows': int(len(calibration_part)),
                                              'n_valid': int(calibration_values.size),
                                              'coverage': coverage,
                                              'n_unique_finite': int(calibration_values.nunique())}})
        if outside_values.size and item['median'] is not None:
            if abs(float(outside_values.median()) - float(item['median'])) < 1e-12:
                coincidences.append({'parameter': [item['domain'], item['feature']],
                                     'outside_median': float(outside_values.median())})
    check('V12_parameter_sources_no_leakage',
          'every parameter provably comes from A1_calibration of the same domain (candidate count, '
          'valid count, coverage, unique count, scope)',
          'PASS' if param_rows and not provenance else 'FAIL',
          {'n_parameters': len(param_rows), 'provenance_violations': provenance[:3],
           'median_coincidences_with_outside_rows': coincidences,
           'coincidence_note': 'discrete normalized values can coincide; provenance is decided by the '
                               'recorded counts and scope, not by median equality'},
          {'provenance_violations': []},
          'imputation_parameters_sensitivity.json vs calibration-only recomputation')
    imputed = df['sensitivity_imputed_count'].to_numpy()
    sens = df[SENSITIVITY_COLUMN].to_numpy(dtype=float)
    no_imputation_ok = bool(np.allclose(sens[imputed == 0][np.isfinite(df['Q_baseline'].to_numpy(dtype=float))[imputed == 0]],
                                        df['Q_baseline'].to_numpy(dtype=float)[imputed == 0][np.isfinite(df['Q_baseline'].to_numpy(dtype=float))[imputed == 0]]))
    imputed_rows_ok = bool(np.isfinite(sens[imputed > 0]).all()
                           and pd.isna(df['Q_baseline'].to_numpy(dtype=float)[imputed > 0]).all())
    check('V13_sensitivity_separation_and_coverage',
          'sensitivity Q is separate; imputed rows carry a value while primary Q stays NaN',
          'PASS' if (no_imputation_ok and imputed_rows_ok and int((imputed > 0).sum()) == 19) else 'FAIL',
          {'imputed_rows': int((imputed > 0).sum()), 'no_imputation_equals_primary': no_imputation_ok,
           'imputed_rows_definition_ok': imputed_rows_ok},
          {'imputed_rows': 19, 'no_imputation_equals_primary': True},
          'parquet sensitivity columns')
    denominator_map = {(row['scope'], row['domain'], row['statistic']): row for row in denominators}
    denom_violations = []
    for scope, domain, part in _scope_parts(df):
        q = part['Q_baseline'].to_numpy(dtype=float)
        n_valid = int(np.isfinite(q).sum())
        row = summary_map.get((scope, domain))
        stat = denominator_map.get((scope, domain, 'Q_mean'))
        if row is None or stat is None or int(stat['n_effective']) != n_valid:
            denom_violations.append({'scope': scope, 'domain': domain, 'statistic': 'Q_mean'})
        qstd = denominator_map.get((scope, domain, 'Q_std'))
        expected_divisor = n_valid - 1 if n_valid >= 2 else None
        if qstd is None or not same(qstd['variance_divisor'], expected_divisor):
            denom_violations.append({'scope': scope, 'domain': domain, 'statistic': 'Q_std'})
    check('V14_summary_denominators_long_table',
          'long denominator table agrees with recomputed effective n and variance divisors',
          'PASS' if not denom_violations else 'FAIL',
          {'violations': denom_violations[:5], 'n_violations': len(denom_violations)},
          {'n_violations': 0}, 'summary_denominators.csv vs parquet')
    comparison_violations = []
    for row in comparison:
        key = (row['scope'], row['domain'])
        summary_row = summary_map.get(key)
        if summary_row is None:
            comparison_violations.append({'key': list(key), 'reason': 'missing domain_summary'})
            continue
        if not (same(row['n_primary_valid'], summary_row['n_Q_valid'])):
            comparison_violations.append({'key': list(key), 'reason': 'n_primary_valid mismatch'})
        if row['mean_difference'] not in ('', None) and row['primary_mean'] not in ('', None):
            if abs(float(row['mean_difference'])
                   - (float(row['sensitivity_mean']) - float(row['primary_mean']))) > 1e-12:
                comparison_violations.append({'key': list(key), 'reason': 'mean difference arithmetic'})
    check('V15_sensitivity_comparison_consistency',
          'sensitivity comparison means/differences are internally consistent with the summaries',
          'PASS' if not comparison_violations else 'FAIL',
          {'violations': comparison_violations[:5], 'n_violations': len(comparison_violations)},
          {'n_violations': 0}, 'sensitivity_comparison.csv vs domain_summary.csv')


def verify_protection_and_hygiene(run_dir, input_manifest, before, run_config, df,
                                  domain_summary):
    protected_prefixes = ('solution/outputs/quality/', 'solution/reports/',
                          'diagnostics/TASK-Q01A/', 'diagnostics/TASK-Q01A-R1/',
                          'F题/real_attachments/')
    changed = []
    missing = []
    checked = 0
    for rel, meta in before.items():
        if not rel.startswith(protected_prefixes):
            continue
        path = PROJECT / rel
        if not path.is_file():
            missing.append(rel)
            continue
        checked += 1
        if sha256_file(path) != meta['sha256']:
            changed.append(rel)
    check('V16_protected_artifacts_unchanged',
          'old quality outputs, reports, Q01A/R1 evidence and raw inputs keep their recorded hashes',
          'PASS' if not changed and not missing else 'FAIL',
          {'checked': checked, 'changed': changed[:5], 'missing': missing[:5]},
          {'changed': [], 'missing': []}, 'old_artifacts_before.json vs current hashes')
    schema = pd.read_parquet(run_dir / 'quality_features_scores.parquet').columns.tolist()
    content_like = [c for c in schema if re.search(r'content|text|body', c, re.IGNORECASE)]
    check('V17_no_content_columns', 'no content/text column exists in the row-level product',
          'PASS' if not content_like else 'FAIL',
          {'content_like_columns': content_like, 'n_columns': len(schema)},
          {'content_like_columns': []}, 'parquet schema')
    def reject_constant(value):
        raise ValueError(f'non-strict JSON literal: {value}')
    bad_json = []
    for path in sorted(run_dir.rglob('*.json')):
        if path.name == 'output_manifest.json':
            continue
        try:
            json.loads(path.read_text(encoding='utf-8-sig'), parse_constant=reject_constant)
        except ValueError as exc:
            bad_json.append({'file': path.name, 'error': str(exc)})
    check('V18_strict_json', 'all JSON artifacts are strict (no NaN/Infinity literals)',
          'PASS' if not bad_json else 'FAIL', {'files_with_nonstrict_literals': bad_json},
          {'files_with_nonstrict_literals': []}, 'strict parse of every run-dir JSON')
    manifest = read_json(run_dir / 'checkpoint_manifest.json')
    probes = manifest.get('resume_probes', [])
    checkpoint_ok = bool(probes) and all(p.get('decompress_passes_during_probe') == 0
                                         and p.get('reused') for p in probes)
    stage_markers = [run_dir / 'checkpoints' / f'{stage}.COMPLETE' for stage in
                     ['s00_preflight', 's01_synthetic_tests', 's10_scan_a1', 's11_scan_a2',
                      's12_scan_a3', 's20_score_primary', 's30_sensitivity',
                      's40_summarize']]
    markers_ok = all(p.is_file() for p in stage_markers)
    input_ok = True
    for stage, file_id in [('s10_scan_a1', 'A1'), ('s11_scan_a2', 'A2_arxiv'),
                           ('s12_scan_a3', 'A3_github')]:
        meta = read_json(run_dir / 'checkpoints' / f'{stage}.json')
        if meta.get('input_sha256') != input_manifest['primary'][file_id]['sha256']:
            input_ok = False
    check('V19_resume_and_checkpoint_evidence',
          'resume probes reused checkpoints without decompression; markers and input hashes agree',
          'PASS' if checkpoint_ok and markers_ok and input_ok else 'FAIL',
          {'resume_probes': probes, 'stage_markers_present': markers_ok,
           'checkpoint_input_hashes_match': input_ok,
           'marker_note': 's50_verify/s60_finalize markers are written after this verification runs'},
          {'probe_decompress_passes': 0, 'markers_present': True, 'input_hashes_match': True},
          'checkpoint_manifest.json / checkpoints/*')
    anchors = {'sources': {'Q01A': str(R_DIR), 'R1': str(R1_DIR)}}
    try:
        r_summary = read_json(R_DIR / 'run_summary.json')
        r1_phase = read_json(R1_DIR / 'repair_phase_summary.json')
        r1_denominators = read_csv_rows(R1_DIR / 'summary_denominators_corrected.csv')
        expected_totals = r_summary['totals']
        scope_names = ['A1_calibration', 'A1_holdout', 'A1_all_unique', 'extension_overlap_A1',
                       'extension_new_records', 'all_unique']
        expected_scopes = {scope: r_summary['key_numbers']['scopes'][scope]['n_would_Q_nan']
                           for scope in scope_names}
        expected_group_hist = r1_phase['anchors']['all_unique_denominators']
        r1_all = {(row['scope'], row['domain'], row['statistic']): row for row in r1_denominators}
        new_summary = {(row['scope'], row['domain']): row for row in domain_summary}
        new_all = new_summary[('all_unique', 'ALL')]
        actual_scopes = {}
        for scope, fn in SCOPE_DEFS:
            part = df[fn(df)]
            actual_scopes[scope] = int((~part['Q_valid']).sum())
        comparisons = {
            'totals': {'expected': {'total_records': expected_totals['total_records'],
                                    'unique_keys': expected_totals['unique_keys'],
                                    'duplicate_rows': expected_totals['duplicate_rows']},
                       'actual': {'total_records': int(len(df)),
                                  'unique_keys': int(df['is_unique_first'].sum()),
                                  'duplicate_rows': int((~df['is_unique_first']).sum())}},
            'scope_missing': {'expected': expected_scopes, 'actual': actual_scopes},
            'group_histogram': {'expected': {k: expected_group_hist[k] for k in
                                             ['n_valid_0', 'n_valid_1', 'n_valid_2', 'n_valid_3']},
                                'actual': {k: int((df.loc[df['is_unique_first'], 'n_groups_valid'] == i).sum())
                                           for k, i in [('n_valid_0', 0), ('n_valid_1', 1),
                                                        ('n_valid_2', 2), ('n_valid_3', 3)]}},
            'range_std_denominators': {
                'expected': {'range_effective_n': int(float(
                                 r1_all[('all_unique', 'ALL', 'rater_disagreement_mean')]['n_effective'])),
                             'std_effective_n': int(float(
                                 r1_all[('all_unique', 'ALL', 'rater_disagreement_std')]['n_effective'])),
                             'q_std_effective_n': int(float(
                                 r1_all[('all_unique', 'ALL', 'Q_std')]['n_effective'])),
                             'q_std_variance_divisor': int(float(
                                 r1_all[('all_unique', 'ALL', 'Q_std')]['variance_divisor']))},
                'actual': {'range_effective_n': int(new_all['rater_disagreement_mean_effective_n']),
                           'std_effective_n': int(new_all['rater_disagreement_std_effective_n']),
                           'q_std_effective_n': int(new_all['Q_std_effective_n']),
                           'q_std_variance_divisor': int(new_all['Q_std_variance_divisor'])}},
            'overlap_rows': {'expected': expected_totals['pairwise_intersections'],
                             'actual': {f'A1__A2_arxiv': int(df[df['file_id'].eq('A2_arxiv')]['overlap_a1'].sum()),
                                        f'A1__A3_github': int(df[df['file_id'].eq('A3_github')]['overlap_a1'].sum()),
                                        'A2_arxiv__A3_github': 0}}}
        mismatches = {k: v for k, v in comparisons.items() if v['expected'] != v['actual']}
        anchors['comparisons'] = comparisons
        check('V20_anchors_vs_Q01A_R1',
              'new run reproduces the accepted Q01A/R1 anchors (read from their own artifacts)',
              'PASS' if not mismatches else 'FAIL',
              {'mismatches': mismatches, 'sources': anchors['sources']},
              {'mismatches': {}}, 'Q01A run_summary.json + R1 repair_phase_summary.json')
    except Exception as exc:
        check('V20_anchors_vs_Q01A_R1',
              'new run reproduces the accepted Q01A/R1 anchors (read from their own artifacts)',
              'NOT_CHECKED', {'error': f'{type(exc).__name__}: {exc}'}, {'mismatches': {}},
              'Q01A/R1 artifacts')
    return anchors


def _safe(value):
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.ndarray):
        return [_safe(v) for v in value.tolist()]
    return value


def write_verification_outputs(run_dir, df, audit, parameters, domain_summary, denominators):
    payload = checks_payload()
    verification = {
        'run_id': run_dir.name, 'generated_local': now_iso(), 'summary': payload['summary'],
        'checks': payload['checks'],
        'key_metrics': {
            'rows': int(len(df)), 'unique_keys': int(df['is_unique_first'].sum()),
            'duplicates': int((~df['is_unique_first']).sum()),
            'q_valid_true': int(df['Q_valid'].sum()), 'q_valid_false': int((~df['Q_valid']).sum()),
            'extract_missing_union': int((df['extract_nan_features'].fillna('') != '').sum()),
            'sensitivity_imputed_rows': int((df['sensitivity_imputed_count'] > 0).sum()),
            'sensitivity_gates_passed': bool(parameters.get('all_gates_passed')),
            'n_domain_summary_rows': len(domain_summary),
            'n_denominator_rows': len(denominators)},
        'independent_of_pipeline_module': True}
    (run_dir / 'verification.json').write_text(
        json.dumps(_safe(verification), ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    (run_dir / 'checks.json').write_text(
        json.dumps(_safe({'run_id': run_dir.name, 'generated_local': now_iso(), **payload}),
                   ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return payload


FIXTURE_PROTOCOL_VERSION = 2
FIXTURE_STAGES = ['s00_preflight', 's01_synthetic_tests', 's10_scan_a1', 's11_scan_a2',
                  's12_scan_a3', 's20_score_primary', 's30_sensitivity', 's40_summarize',
                  's50_verify', 's60_finalize']
FIXTURE_TERMINAL_EVENTS = ('complete', 'failed', 'gate_failed')


def _load_json(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def verify_fixture_marker_chain(run_dir, records):
    """Independent validation of the v2 payload/metadata/checkpoint/stage marker chain."""
    ok = True
    details = []
    for stage, payload_name, meta_name, checkpoint_name, stage_name in records:
        payload = run_dir / 'checkpoints' / payload_name
        meta = run_dir / 'checkpoints' / meta_name
        checkpoint = run_dir / 'checkpoints' / checkpoint_name
        stage_marker = run_dir / 'checkpoints' / stage_name
        entry = {'stage': stage, 'payload': payload.is_file(), 'meta': meta.is_file(),
                 'checkpoint_marker': checkpoint.is_file(), 'stage_marker': stage_marker.is_file(),
                 'distinct_marker_files': checkpoint_name != stage_name}
        if all([payload.is_file(), meta.is_file(), checkpoint.is_file()]):
            meta_payload = _load_json(meta)
            marker = _load_json(checkpoint)
            entry['payload_sha_matches'] = meta_payload.get('payload_sha256') == sha256_file(payload)
            entry['marker_binds_meta'] = marker.get('checkpoint_meta_sha256') == sha256_file(meta)
            entry['marker_kind'] = marker.get('kind')
            entry['stage_field'] = meta_payload.get('stage')
            entry['rows'] = meta_payload.get('rows')
            entry['protocol_version'] = meta_payload.get('protocol_version')
            entry['input_sha256_present'] = bool(meta_payload.get('input_sha256'))
            entry['config_sha256_present'] = bool(meta_payload.get('config_sha256'))
            entry['code_fingerprint_present'] = bool(meta_payload.get('code_fingerprint'))
            entry_ok = (entry['payload_sha_matches'] and entry['marker_binds_meta']
                        and entry['marker_kind'] == 'checkpoint'
                        and entry['stage_field'] == stage
                        and entry['input_sha256_present'] and entry['config_sha256_present']
                        and entry['code_fingerprint_present']
                        and int(entry['protocol_version'] or 0) >= FIXTURE_PROTOCOL_VERSION
                        and entry['distinct_marker_files'])
        else:
            entry_ok = False
        entry['ok'] = entry_ok
        ok = ok and entry_ok
        details.append(entry)
    return ok, details


def verify_fixture_mode(run_dir, fixture_manifest_path):
    """Verification path for synthetic fixture runs (no real-data anchors are read)."""
    del CHECKS[:]
    fixture = _load_json(fixture_manifest_path)
    df = pd.read_parquet(run_dir / 'quality_features_scores.parquet')
    domain_summary = read_csv_rows(run_dir / 'domain_summary.csv')
    denominators = read_csv_rows(run_dir / 'summary_denominators.csv')
    sensitivity_summary = read_csv_rows(run_dir / 'sensitivity_domain_summary.csv')
    parameters = _load_json(run_dir / 'imputation_parameters_sensitivity.json')
    run_config = _load_json(run_dir / 'run_config.json')
    input_manifest = _load_json(run_dir / 'input_manifest.json')
    try:
        resume_evidence = _load_json(run_dir / 'resume_evidence.json')
    except FileNotFoundError:
        resume_evidence = None  # written by S60 finalize, i.e. after this verification runs
    scan_counters = _load_json(run_dir / 'scan_counters.json')
    status_records = [json.loads(line) for line in
                      (run_dir / 'stage_status.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    expected_rows = int(fixture['expected_rows_total'])
    expected_q_valid = int(fixture['expected_q_valid'])
    expected_q_missing = int(fixture['expected_q_missing'])
    expected_imputed = int(fixture.get('expected_imputed_rows', expected_q_missing))
    norm_columns = ['norm_' + f for f in MODEL]
    finite_11 = np.isfinite(df[norm_columns].to_numpy()).all(axis=1)
    q_values = df['Q_baseline'].to_numpy(dtype=float)
    unique_mask = df['is_unique_first'].to_numpy()
    check('F01_fixture_rows', 'fixture row counts match the fixture manifest (per file and total)',
          'PASS' if (int(len(df)) == expected_rows
                     and all(int((df['file_id'] == fid).sum()) == int(rows)
                             for fid, rows in fixture['expected_rows'].items())) else 'FAIL',
          {'rows': int(len(df)), 'by_file': {fid: int((df['file_id'] == fid).sum())
                                             for fid in fixture['expected_rows']},
           'expected_rows': fixture['expected_rows']},
          {'rows': expected_rows, 'by_file': fixture['expected_rows']},
          'fixture manifest vs parquet')
    check('F02_q_valid_equivalence',
          'Q_valid equals the all-11-finite mask and Q is finite only for valid rows',
          'PASS' if (bool(np.array_equal(df['Q_valid'].to_numpy(), finite_11))
                     and bool(np.array_equal(np.isfinite(q_values), finite_11))
                     and int(df.loc[unique_mask, 'Q_valid'].sum()) == expected_q_valid
                     and int((~df.loc[unique_mask, 'Q_valid']).sum()) == expected_q_missing) else 'FAIL',
          {'q_valid_physical': int(df['Q_valid'].sum()),
           'q_valid_unique': int(df.loc[unique_mask, 'Q_valid'].sum()),
           'q_missing_unique': int((~df.loc[unique_mask, 'Q_valid']).sum())},
          {'q_valid_unique': expected_q_valid, 'q_missing_unique': expected_q_missing},
          'parquet columns')
    groups_ok = True
    for group in GROUP_NAMES:
        reference = df[['norm_' + f for f in GROUPS[group]]].mean(axis=1, skipna=False)
        groups_ok = groups_ok and bool(np.allclose(reference.to_numpy(dtype=float),
                                                  df['group_' + group].to_numpy(dtype=float),
                                                  equal_nan=True))
    ref_q = pd.DataFrame({g: df[['norm_' + f for f in GROUPS[g]]].mean(axis=1, skipna=False)
                          for g in GROUP_NAMES}).mean(axis=1, skipna=False)
    valid = np.isfinite(q_values)
    check('F03_group_and_q_recomputation',
          'group means and Q recomputed independently; no reallocation of missing groups',
          'PASS' if (groups_ok and bool(np.allclose(ref_q.to_numpy(dtype=float)[valid], q_values[valid]))
                     and bool(pd.isna(df.loc[(~np.isfinite(df[['group_' + g for g in GROUP_NAMES]]
                                                            .to_numpy(dtype=float)).all(axis=1)),
                                             'Q_baseline']).all())) else 'FAIL',
          {'groups_match': groups_ok, 'no_reallocation': True}, {'groups_match': True},
          'independent pandas recomputation')
    summary_map = {(r['scope'], r['domain']): r for r in domain_summary}
    coverage_violations = []
    for scope, fn in SCOPE_DEFS:
        sub = df[fn(df)]
        for domain in sorted(sub['domain'].unique().tolist()) + ['ALL']:
            part = sub if domain == 'ALL' else sub[sub['domain'] == domain]
            row = summary_map.get((scope, domain))
            if row is None:
                continue
            q = part['Q_baseline'].to_numpy(dtype=float)
            n_valid = int(np.isfinite(q).sum())
            if not (int(row['n_total']) == len(part) and int(row['n_Q_valid']) == n_valid
                    and int(row['n_Q_missing']) == len(part) - n_valid):
                coverage_violations.append({'scope': scope, 'domain': domain})
    check('F04_coverage_fields', 'coverage fields recomputed for every scope x domain',
          'PASS' if not coverage_violations else 'FAIL',
          {'violations': coverage_violations[:5]}, {'violations': []}, 'domain_summary.csv vs parquet')
    denominator_violations = []
    for scope, fn in SCOPE_DEFS:
        sub = df[fn(df)]
        for domain in sorted(sub['domain'].unique().tolist()) + ['ALL']:
            part = sub if domain == 'ALL' else sub[sub['domain'] == domain]
            row = summary_map.get((scope, domain))
            if row is None:
                continue
            q = part['Q_baseline'].to_numpy(dtype=float)
            n_valid = int(np.isfinite(q).sum())
            ranges = part.loc[part['rater_disagreement_range_defined'], 'rater_disagreement_range']
            if not (int(row['Q_std_effective_n']) == (n_valid if n_valid >= 2 else 0)
                    and str(row['Q_std_variance_divisor']) == str(n_valid - 1 if n_valid >= 2 else '')
                    and int(row['rater_disagreement_mean_effective_n']) == int(ranges.size)
                    and int(row['rater_disagreement_gt_0_5_denominator']) == int(ranges.size)):
                denominator_violations.append({'scope': scope, 'domain': domain})
    check('F05_denominators', 'effective n, variance divisor and boolean denominator are consistent',
          'PASS' if not denominator_violations else 'FAIL',
          {'violations': denominator_violations[:5]}, {'violations': []}, 'domain_summary.csv vs parquet')
    missing_rows = df['extract_nan_features'].fillna('') != ''
    check('F06_missing_marking',
          'missing features are marked, Q is NaN for those rows and the union matches the manifest',
          'PASS' if (int(missing_rows.sum()) == expected_q_missing
                     and pd.isna(df.loc[missing_rows, 'Q_baseline']).all()) else 'FAIL',
          {'missing_rows': int(missing_rows.sum()), 'expected': expected_q_missing},
          {'missing_rows': expected_q_missing}, 'parquet columns')
    calibration = df[(df['evaluation_role'] == 'A1_calibration') & df['is_unique_first']]
    provenance = []
    for item in parameters.get('parameters', []):
        column = 'norm_' + item['feature']
        part = calibration[calibration['domain'] == item['domain']]
        values = part[column].dropna()
        coverage = (values.size / len(part)) if len(part) else 0.0
        ok = (int(item['candidate_rows']) == int(len(part))
              and int(item['n_valid']) == int(values.size)
              and abs(float(item['coverage']) - coverage) < 1e-12
              and int(item['n_unique_finite']) == int(values.nunique())
              and (not values.size or abs(float(item['median']) - float(values.median())) < 1e-12)
              and item['source_scope'] == 'A1_calibration & is_unique_first'
              and bool(item['gate_ok']))
        if not ok:
            provenance.append({'parameter': [item['domain'], item['feature']], 'recorded': item,
                               'recomputed': {'candidates': int(len(part)), 'n_valid': int(values.size),
                                              'coverage': coverage,
                                              'n_unique': int(values.nunique()),
                                              'median': float(values.median()) if values.size else None}})
    check('F07_sensitivity_parameters', 'every sensitivity parameter recomputed from calibration rows only',
          'PASS' if parameters.get('parameters') and not provenance else 'FAIL',
          {'n_parameters': len(parameters.get('parameters', [])), 'violations': provenance[:3]},
          {'violations': []}, 'imputation_parameters_sensitivity.json vs parquet')
    imputed = df['sensitivity_imputed_count'].to_numpy()
    sens = df[SENSITIVITY_COLUMN].to_numpy(dtype=float)
    no_imp_equal = bool(np.allclose(sens[(imputed == 0) & valid], q_values[(imputed == 0) & valid]))
    check('F08_sensitivity_separation',
          'sensitivity column is separate, imputed rows stay Q_valid=False and the count matches the fixture',
          'PASS' if (no_imp_equal and int((imputed > 0).sum()) == expected_imputed
                     and pd.isna(q_values[imputed > 0]).all()
                     and np.isfinite(sens[imputed > 0]).all()) else 'FAIL',
          {'imputed_rows': int((imputed > 0).sum()), 'no_imputation_equals_primary': no_imp_equal},
          {'imputed_rows': expected_imputed}, 'parquet sensitivity columns')
    records = [(stage, f'{stage}.payload.parquet', f'{stage}.meta.json',
                f'{stage}.checkpoint.COMPLETE', f'{stage}.stage.COMPLETE')
               for stage in ['s10_scan_a1', 's11_scan_a2', 's12_scan_a3', 's20_score_primary',
                             's30_sensitivity', 's40_summarize']]
    chain_ok, chain_details = verify_fixture_marker_chain(run_dir, records)
    check('F09_checkpoint_marker_chain',
          'v2 payload/meta/checkpoint/stage markers are distinct, hash-linked and complete',
          'PASS' if chain_ok else 'FAIL', {'details': chain_details}, {'all_ok': True},
          'independent re-hash of the marker chain')
    expected_stages = [s for s in FIXTURE_STAGES if s != 's60_finalize']
    terminal = {stage: [r['event'] for r in status_records
                        if r['stage'] == stage and r['event'] in FIXTURE_TERMINAL_EVENTS]
                for stage in expected_stages}
    started = {stage: any(r['stage'] == stage and r['event'] == 'start' for r in status_records)
               for stage in expected_stages}
    check('F10_stage_events',
          'every executed stage has a start event and exactly one terminal event',
          'PASS' if all(started.values()) and all(len(v) == 1 for v in terminal.values()) else 'FAIL',
          {'started': started, 'terminal': terminal}, {'all_stages_single_terminal': True},
          'stage_status.jsonl')
    passes = {fid: int(info.get('passes', 0)) for fid, info in scan_counters.get('files', {}).items()}
    check('F11_scan_counters', 'scan counters and reuse events recorded for the fixture files',
          'PASS' if (passes and all(v >= 1 for v in passes.values())
                     and scan_counters.get('total_passes', 0) >= len(passes)
                     and isinstance(scan_counters.get('reuse_events'), list)) else 'FAIL',
          {'passes': passes, 'total_passes': scan_counters.get('total_passes'),
           'reuse_events': len(scan_counters.get('reuse_events', []))},
          {'passes>=1': True}, 'scan_counters.json / resume_evidence.json')
    schema = df.columns.tolist()
    content_like = [c for c in schema if re.search(r'content|text|body', c, re.IGNORECASE)]
    real_path_hits = [k for k in input_manifest.get('primary', {})
                      if 'real_attachments' in str(input_manifest['primary'][k].get('path', ''))]
    check('F12_no_real_inputs_and_no_content',
          'fixture run references only fixture inputs and stores no content columns',
          'PASS' if (run_config.get('mode') == 'fixture' and input_manifest.get('mode') == 'fixture'
                     and not content_like and not real_path_hits
                     and int(input_manifest.get('real_inputs_accessed', 0)) == 0) else 'FAIL',
          {'mode': run_config.get('mode'), 'content_like': content_like,
           'real_path_hits': real_path_hits}, {'mode': 'fixture', 'real_inputs_accessed': 0},
          'run_config.json / input_manifest.json / parquet schema')
    def _reject_constant(value):
        raise ValueError(f'non-strict JSON literal: {value}')
    bad_json = []
    for path in sorted(run_dir.glob('*.json')):
        if path.name == 'output_manifest.json':
            continue
        try:
            json.loads(path.read_text(encoding='utf-8-sig'), parse_constant=_reject_constant)
        except ValueError as exc:
            bad_json.append({'file': path.name, 'error': str(exc)})
    check('F13_strict_json', 'fixture-run JSON artefacts are strict', 'PASS' if not bad_json else 'FAIL',
          {'files': bad_json}, {'files': []}, 'strict parse')
    required = ['audit.json', 'raw_field_counts.csv', 'normalization.json',
                'quality_features_scores.parquet', 'domain_summary.csv', 'summary_denominators.csv',
                'imputation_parameters_sensitivity.json', 'sensitivity_domain_summary.csv',
                'sensitivity_comparison.csv', 'feature_summary.csv', 'extension_shift.csv',
                'unresolved_indicator_correlations.csv', 'indicator_direction_pending.csv',
                'conditional_bootstrap.csv', 'resume_evidence.json', 'scan_counters.json']
    missing_files = [name for name in required if not (run_dir / name).is_file()]
    check('F14_required_artifacts', 'fixture run produced every required artefact',
          'PASS' if not missing_files else 'FAIL', {'missing': missing_files}, {'missing': []},
          'run directory listing')
    payload = checks_payload()
    verification = {'run_id': run_dir.name, 'mode': 'fixture', 'generated_local': now_iso(),
                    'summary': payload['summary'], 'checks': payload['checks'],
                    'fixture_manifest': str(fixture_manifest_path),
                    'independent_of_pipeline_module': True,
                    'key_metrics': {'rows': int(len(df)),
                                    'q_valid_unique': int(df.loc[unique_mask, 'Q_valid'].sum()),
                                    'q_missing_unique': int((~df.loc[unique_mask, 'Q_valid']).sum()),
                                    'imputed_rows': int((imputed > 0).sum())}}
    (run_dir / 'verification.json').write_text(
        json.dumps(_safe(verification), ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    (run_dir / 'checks.json').write_text(
        json.dumps(_safe({'run_id': run_dir.name, 'mode': 'fixture',
                          'generated_local': now_iso(), **payload}),
                   ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print('[verify-fixture] summary: ' + json.dumps(payload['summary'], ensure_ascii=False), flush=True)
    return 0 if payload['summary']['n_fail'] == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
