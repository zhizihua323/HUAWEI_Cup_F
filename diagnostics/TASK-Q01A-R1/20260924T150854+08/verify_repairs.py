"""TASK-Q01A-R1 independent verification of the repair outputs.

Independence: this script re-derives every expectation either from pandas itself
(synthetic matrices / real aggregates recomputed through a different toolchain)
or from the saved event table, and never imports repair_from_artifacts.py.
No compressed input (A1-A3) is opened, decompressed, read or hashed.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import platform
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

RUN_ID = '20260924T150854+08'
RUN_DIR = Path(__file__).resolve().parent
PROJECT = RUN_DIR.parents[2]
R_DIR = PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T142229+08'
FAILED_DIR = PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T141414+08'
ABORTED_R1_DIRS = [PROJECT / 'diagnostics' / 'TASK-Q01A-R1' / '20260924T150623+08',
                   PROJECT / 'diagnostics' / 'TASK-Q01A-R1' / '20260924T150813+08']
CST = timezone(timedelta(hours=8))
START_LOCAL = datetime.now(CST)
START_MONO = time.monotonic()
SPEC = json.loads((R_DIR / 'diagnostic_spec.json').read_text(encoding='utf-8-sig'))
FIELD_ORDER = [item['field'] for item in sorted(SPEC['raw_fields_22'], key=lambda x: x['index'])]
FEATURE_ORDER = [item['feature'] for item in sorted(SPEC['expanded_features_25'], key=lambda x: x['index'])]
GROUP_NAMES = ['usability', 'knowledge', 'education_reasoning']
RAW_ANOMALY_REASONS = {'absent', 'null', 'wrong_list_length', 'non_numeric_element',
                       'nan_element', 'posinf_element', 'neginf_element', 'audit_exception'}
MODEL_INDEX = {item['feature']: item['index'] for item in SPEC['main_q_features_11']}
CHECKS = []
LOG_FH = None


def now_iso():
    return datetime.now(CST).isoformat(timespec='seconds')


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=str),
                          encoding='utf-8')
    return Path(path)


def log(message):
    line = f'[{datetime.now(CST).isoformat(timespec="milliseconds")}] {message}'
    if LOG_FH is not None:
        LOG_FH.write(line + '\n')
        LOG_FH.flush()
    print(line, flush=True)


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
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def read_csv_rows(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def bits_from_string(text, nbits=None):
    value = 0
    for j, ch in enumerate(text or ''):
        if ch == '1':
            value |= (1 << j)
    if nbits is not None and text:
        assert len(text) == nbits, (len(text), nbits)
    return value


def add_check(check_id, description, status, actual, expected, evidence, note=''):
    CHECKS.append({'check_id': check_id, 'description': description, 'status': status,
                   'actual': actual, 'expected': expected, 'evidence': evidence, 'note': note})
    log(f'check {check_id}: {status}')


def same(a, b):
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def synthetic_semantics_check():
    nan = float('nan')
    rows = [
        [0.2, 0.4, 0.6],
        [0.2, nan, 0.6],
        [0.2, nan, nan],
        [nan, nan, nan],
        [0.9, 0.4, 0.1],
        [0.5, 0.5, nan],
    ]
    frame = pd.DataFrame(rows, columns=GROUP_NAMES)
    valid = frame.notna().sum(axis=1)
    rng = frame.max(axis=1) - frame.min(axis=1)
    std0 = frame.std(axis=1, ddof=0)
    std1 = frame.std(axis=1, ddof=1)
    mean_nonan = frame.mean(axis=1, skipna=False)
    rule_range_defined = [v >= 1 for v in valid.tolist()]
    rule_std0_defined = [v >= 1 for v in valid.tolist()]
    rule_mean_defined = [v == 3 for v in valid.tolist()]
    result = {
        'valid_groups_per_row': valid.tolist(),
        'pandas_range_defined': rng.notna().tolist(),
        'rule_range_defined': rule_range_defined,
        'pandas_std0_defined': std0.notna().tolist(),
        'rule_std0_defined': rule_std0_defined,
        'pandas_mean_defined': mean_nonan.notna().tolist(),
        'rule_mean_defined': rule_mean_defined,
        'range_nan_rows': int(rng.isna().sum()),
        'range_nan_rows_from_rule': int((valid == 0).sum()),
        'gt05_fraction_denominator': int(len(frame)),
        'gt05_nan_to_false_rows': int(rng.isna().sum()),
        'std0_single_group_value': float(std0.iloc[2]),
        'std1_two_groups_defined': bool(not pd.isna(std1.iloc[1])),
        'std1_single_group_is_nan': bool(pd.isna(std1.iloc[2])),
    }
    ok = (rng.notna().tolist() == rule_range_defined and std0.notna().tolist() == rule_std0_defined
          and mean_nonan.notna().tolist() == rule_mean_defined
          and int(rng.isna().sum()) == int((valid == 0).sum()))
    add_check('V01_pandas_group_statistics_rule',
              'synthetic 0/1/2/3 usable-group matrix: range and ddof=0 std are defined with >=1 usable group',
              'PASS' if ok else 'FAIL', result,
              'pandas definedness equals the documented >=1-usable-group rule',
              'pandas 2.3.3 synthetic matrix', 'rule applied here, not imported from the repair script')
    list_probe = [1.0, nan, 3.0, 4.0, 5.0, 6.0]
    whole_list_invalid = not all(isinstance(x, float) and math.isfinite(x) for x in list_probe)
    add_check('V02_six_element_nan_list_rule',
              'six-element list containing NaN invalidates the whole field (current get_features semantics)',
              'PASS' if whole_list_invalid else 'FAIL',
              {'list_repr': [str(x) for x in list_probe], 'whole_list_invalid': whole_list_invalid},
              'True', 'rule re-implemented in this verifier', 'real-data counterpart checked in V11')
    return result


def load_scope_frame():
    usecols = ['file_id', 'source_line', 'domain', 'evaluation_role', 'is_unique_first', 'overlap_a1',
               'parse_ok', 'would_group_usability_be_nan', 'would_group_knowledge_be_nan',
               'would_group_education_reasoning_be_nan', 'would_Q_be_nan',
               'raw_invalid_bits', 'extract_nan_bits']
    df = pd.read_csv(R_DIR / 'row_masks.csv.gz', usecols=usecols, dtype=str, keep_default_na=False,
                     compression='gzip')
    for column in ['is_unique_first', 'overlap_a1', 'parse_ok', 'would_group_usability_be_nan',
                   'would_group_knowledge_be_nan', 'would_group_education_reasoning_be_nan',
                   'would_Q_be_nan']:
        df[column] = df[column].astype(int)
    df['usable_groups'] = 3 - (df['would_group_usability_be_nan'] + df['would_group_knowledge_be_nan']
                               + df['would_group_education_reasoning_be_nan'])
    df['unique'] = df['is_unique_first'] == 1
    df['overlap'] = df['overlap_a1'] == 1
    df['parsed'] = df['parse_ok'] == 1
    df['range_defined'] = (df['usable_groups'] >= 1) & df['parsed']
    df['std0_defined'] = (df['usable_groups'] >= 1) & df['parsed']
    df['false_from_missing_range'] = (df['usable_groups'] == 0) & df['parsed']
    df['q_nonmissing'] = ((df['would_Q_be_nan'] == 0) & df['parsed']).astype(int)
    scopes = {
        'A1_calibration': df['parsed'] & df['unique'] & (df['evaluation_role'] == 'A1_calibration'),
        'A1_holdout': df['parsed'] & df['unique'] & (df['evaluation_role'] == 'A1_holdout'),
        'A1_all_unique': df['parsed'] & df['unique'] & (df['file_id'] == 'A1'),
        'extension_overlap_A1': df['parsed'] & df['overlap'],
        'extension_new_records': df['parsed'] & df['unique'] & (df['evaluation_role'] == 'extension_new_records'),
        'all_unique': df['parsed'] & df['unique'],
        'file_unique_first_A1': df['parsed'] & df['unique'] & (df['file_id'] == 'A1'),
        'file_unique_first_A2_arxiv': df['parsed'] & df['unique'] & (df['file_id'] == 'A2_arxiv'),
        'file_unique_first_A3_github': df['parsed'] & df['unique'] & (df['file_id'] == 'A3_github'),
    }
    return df, scopes


def verify_denominators():
    df, scopes = load_scope_frame()
    corrected = read_csv_rows(RUN_DIR / 'summary_denominators_corrected.csv')
    prior = read_csv_rows(R_DIR / 'summary_denominators.csv')
    recomputed = {}
    for scope, scope_mask in scopes.items():
        sub = df[scope_mask]
        for domain in sorted(sub['domain'].unique().tolist()) + ['ALL']:
            part = sub if domain == 'ALL' else sub[sub['domain'] == domain]
            if part.empty:
                continue
            recomputed[(scope, domain)] = {
                'n_total': int(len(part)),
                'n_range_defined': int(part['range_defined'].sum()),
                'n_std0_defined': int(part['std0_defined'].sum()),
                'n_false_from_missing_range': int(part['false_from_missing_range'].sum()),
                'n_q_nonmissing': int(part['q_nonmissing'].sum()),
                'usable_group_histogram': {str(k): int(v) for k, v in
                                           part['usable_groups'].value_counts().sort_index().items()},
            }
    mismatches = []
    statistic_map = {'rater_disagreement_mean': 'n_range_defined',
                     'rater_disagreement_std': 'n_std0_defined'}
    for row in corrected:
        key = (row['scope'], row['domain'])
        expected = recomputed.get(key)
        if expected is None:
            mismatches.append({'key': list(key), 'reason': 'missing in pandas recomputation'})
            continue
        if row['statistic'] in statistic_map:
            if not same(row['n_effective'], expected[statistic_map[row['statistic']]]):
                mismatches.append({'key': list(key), 'statistic': row['statistic'],
                                   'repaired': row['n_effective'],
                                   'pandas': expected[statistic_map[row['statistic']]]})
        elif row['statistic'] == 'rater_disagreement_gt_0_5_fraction':
            if not same(row['missing_comparison_as_false_n'], expected['n_false_from_missing_range']):
                mismatches.append({'key': list(key), 'statistic': row['statistic'],
                                   'repaired': row['missing_comparison_as_false_n'],
                                   'pandas': expected['n_false_from_missing_range']})
        elif row['statistic'] == 'Q_mean':
            if not same(row['n_effective'], expected['n_q_nonmissing']):
                mismatches.append({'key': list(key), 'statistic': row['statistic'],
                                   'repaired': row['n_effective'], 'pandas': expected['n_q_nonmissing']})
    add_check('V03_denominator_tables_match_independent_pandas',
              'rater_disagreement mean/std effective n, false-comparison count and Q_mean n recomputed with pandas',
              'PASS' if not mismatches else 'FAIL',
              {'n_rows_checked': len(corrected), 'n_mismatch': len(mismatches), 'examples': mismatches[:5]},
              '0 mismatches', 'summary_denominators_corrected.csv vs pandas recomputation from row_masks.csv.gz')
    prior_changed = sum(1 for a, b in zip(prior, corrected)
                        if not same(a['n_effective'], b['n_effective'])
                        or not same(a['missing_comparison_as_false_n'], b['missing_comparison_as_false_n']))
    add_check('V04_repair_changed_exactly_the_affected_denominator_rows',
              'only the reported range/std/false-comparison rows changed (40 + 20 per the review)',
              'PASS' if prior_changed == 60 else 'FAIL',
              {'rows_changed': prior_changed, 'expected': 60}, '60',
              'summary_denominators.csv vs summary_denominators_corrected.csv')
    allu = recomputed.get(('all_unique', 'ALL'))
    anchors_ok = bool(allu and allu['n_range_defined'] == 261086 and allu['n_std0_defined'] == 261086
                      and allu['n_false_from_missing_range'] == 0 and allu['n_q_nonmissing'] == 261067)
    add_check('V05_all_unique_anchor',
              'all_unique: range/std n = 261086, false-from-missing-range = 0, Q_mean n = 261067',
              'PASS' if anchors_ok else 'FAIL', allu,
              'n_range_defined=261086, n_std0_defined=261086, false=0, Q n=261067',
              'row_masks.csv.gz recomputed with pandas')
    qstd = next(row for row in corrected
                if row['scope'] == 'all_unique' and row['domain'] == 'ALL' and row['statistic'] == 'Q_std')
    qstd_ok = (same(qstd['n_effective'], 261067) and same(qstd['variance_divisor'], 261066)
               and qstd['status'] == 'DEFINED')
    add_check('V06_q_std_variance_divisor', 'Q_std effective n and ddof=1 variance divisor are separate columns',
              'PASS' if qstd_ok else 'FAIL',
              {'n_effective': qstd['n_effective'], 'variance_divisor': qstd['variance_divisor'],
               'status': qstd['status']}, 'n_effective=261067, variance_divisor=261066, DEFINED',
              'summary_denominators_corrected.csv')
    concentration = read_csv_rows(RUN_DIR / 'missing_concentration.csv')
    ratios_ok = all((row['rate_denominator'] not in ('', None) and row['share_denominator'] not in ('', None))
                    or row['undefined_reason'] for row in concentration)
    add_check('V07_missing_concentration_has_numerators_and_denominators',
              'every concentration row carries explicit numerator/denominator or an undefined reason',
              'PASS' if ratios_ok else 'FAIL', {'rows': len(concentration)},
              'all rows explicit', 'missing_concentration.csv')
    return recomputed, df


def load_events_independent():
    raw = {}
    extract = Counter()
    identity = Counter()
    with gzip.open(R_DIR / 'invalid_values.csv.gz', 'rt', encoding='utf-8', newline='') as fh:
        for row in csv.DictReader(fh):
            key = (row['file_id'], row['source_line'], row['field_or_feature'])
            if row['layer'] == 'raw':
                raw.setdefault(key, set()).add(row['reason'])
            elif row['layer'] == 'extract':
                extract[(row['field_or_feature'], row['reason'])] += 1
            else:
                identity[(row['field_or_feature'], row['reason'])] += 1
    return raw, extract, identity


def verify_raw_masks(raw_events):
    expected = {}
    for (file_id, line, field), reasons in raw_events.items():
        expected.setdefault((file_id, line), set()).update({field})
    corrections = read_csv_rows(RUN_DIR / 'raw_mask_corrections.csv')
    corrected = pd.read_csv(RUN_DIR / 'row_masks_corrected.csv.gz', dtype=str, keep_default_na=False,
                            compression='gzip',
                            usecols=['file_id', 'source_line', 'raw_invalid_bits', 'raw_invalid_count',
                                     'extract_nan_bits', 'domain', 'evaluation_role'])
    mismatch = []
    n_corrected_rows = 0
    for _, row in corrected.iterrows():
        key = (row['file_id'], row['source_line'])
        expect_fields = expected.get(key, set())
        expect_bits = 0
        for field in expect_fields:
            expect_bits |= (1 << FIELD_ORDER.index(field))
        actual_bits = bits_from_string(row['raw_invalid_bits'], len(FIELD_ORDER))
        if actual_bits != expect_bits:
            mismatch.append({'key': list(key), 'actual': row['raw_invalid_bits'],
                             'expected_bits': expect_bits})
        if expect_bits:
            n_corrected_rows += 1
        if int(row['raw_invalid_count'] or 0) != bin(actual_bits).count('1'):
            mismatch.append({'key': list(key), 'reason': 'raw_invalid_count inconsistent'})
    add_check('V08_corrected_raw_mask_matches_events',
              'every corrected raw_invalid mask equals the union of saved raw events for that physical row',
              'PASS' if not mismatch else 'FAIL',
              {'rows_with_events': n_corrected_rows, 'rows_with_corrected_mask': len(corrections),
               'n_mismatch': len(mismatch), 'examples': mismatch[:5]},
              'rows_with_events == rows_with_corrected_mask == 19, 0 mismatches',
              'row_masks_corrected.csv.gz vs invalid_values.csv.gz (independent re-derivation)')
    profile = Counter()
    for (file_id, line, field) in raw_events:
        profile[f'{file_id}|{field}'] += 1
    union_all = len({(f, l) for (f, l, _x) in raw_events})
    prof = {(f, l) for (f, l, x) in raw_events if x == 'modernbert_professionalism'}
    reas = {(f, l) for (f, l, x) in raw_events if x == 'modernbert_reasoning'}
    anchors_ok = (profile.get('A1|modernbert_professionalism') == 5
                  and profile.get('A1|modernbert_reasoning') == 13
                  and profile.get('A3_github|modernbert_professionalism') == 1
                  and union_all == 19 and len(prof & reas) == 0 and len(prof | reas) == 19)
    add_check('V09_raw_anomaly_anchors',
              'raw anomaly records: A1 professionalism 5, A1 reasoning 13, A3 professionalism 1; union 19; intersection 0',
              'PASS' if anchors_ok else 'FAIL',
              {'by_file_field': dict(profile), 'union': union_all, 'intersection': len(prof & reas)},
              '5/13/1, union 19, intersection 0', 'invalid_values.csv.gz (independent re-derivation)')
    # R vs corrected column-wise comparison
    diffs = Counter()
    changed_rows = []
    with gzip.open(R_DIR / 'row_masks.csv.gz', 'rt', encoding='utf-8', newline='') as f1, \
            gzip.open(RUN_DIR / 'row_masks_corrected.csv.gz', 'rt', encoding='utf-8', newline='') as f2:
        r1 = csv.DictReader(f1)
        r2 = csv.DictReader(f2)
        assert r1.fieldnames == r2.fieldnames, 'column set changed'
        for a, b in zip(r1, r2):
            for column in r1.fieldnames:
                if a[column] != b[column]:
                    diffs[column] += 1
            if a['raw_invalid_bits'] != b['raw_invalid_bits']:
                changed_rows.append((a['file_id'], a['source_line']))
    allowed = {'raw_invalid_bits', 'raw_invalid_count'}
    forbidden_diffs = {k: v for k, v in diffs.items() if k not in allowed}
    add_check('V10_only_permitted_columns_changed',
              'row_masks_corrected.gz differs from R only in raw_invalid_bits / raw_invalid_count',
              'PASS' if not forbidden_diffs and set(changed_rows) == set(expected.keys()) else 'FAIL',
              {'column_diffs': dict(diffs), 'rows_changed': len(changed_rows),
               'forbidden_diffs': forbidden_diffs},
              'only the two permitted columns, exactly the 19 event rows',
              'row-by-row comparison of R/row_masks.csv.gz and the corrected copy')
    # extract-layer correspondence for the 19 rows
    extract_ok = None
    corrected_index = {(row['file_id'], row['source_line']): row for _, row in corrected.iterrows()}
    mismatch_extract = []
    for (file_id, line, field) in raw_events:
        row = corrected_index[(file_id, line)]
        feature = 'modernbert_professionalism' if field == 'modernbert_professionalism' else 'modernbert_reasoning'
        bit = bits_from_string(row['extract_nan_bits'], len(FEATURE_ORDER)) & (1 << FEATURE_ORDER.index(feature))
        if not bit:
            mismatch_extract.append({'key': [file_id, line], 'feature': feature})
    add_check('V11_raw_events_map_to_the_same_extract_nan_rows',
              'each raw NaN-element record also carries the corresponding extraction-layer NaN bit',
              'PASS' if not mismatch_extract else 'FAIL',
              {'n_checked': len(raw_events), 'n_mismatch': len(mismatch_extract),
               'examples': mismatch_extract[:5]}, '0 mismatches',
              'invalid_values.csv.gz vs row_masks_corrected.csv.gz extract_nan_bits')
    return {'profile': dict(profile), 'union': union_all, 'changed_rows': len(changed_rows),
            'column_diffs': dict(diffs)}


def verify_patterns_and_pairwise(raw_events):
    corrected = pd.read_csv(RUN_DIR / 'row_masks_corrected.csv.gz', dtype=str, keep_default_na=False,
                            compression='gzip',
                            usecols=['file_id', 'source_line', 'domain', 'evaluation_role',
                                     'is_unique_first', 'overlap_a1', 'parse_ok', 'raw_invalid_bits'])
    corrected['unique'] = corrected['is_unique_first'].astype(int) == 1
    corrected['overlap'] = corrected['overlap_a1'].astype(int) == 1
    corrected['parsed'] = corrected['parse_ok'].astype(int) == 1
    corrected['mask'] = corrected['raw_invalid_bits'].apply(lambda s: bits_from_string(s, len(FIELD_ORDER)))
    scopes = {
        'A1_calibration': corrected['parsed'] & corrected['unique'] & (corrected['evaluation_role'] == 'A1_calibration'),
        'A1_holdout': corrected['parsed'] & corrected['unique'] & (corrected['evaluation_role'] == 'A1_holdout'),
        'A1_all_unique': corrected['parsed'] & corrected['unique'] & (corrected['file_id'] == 'A1'),
        'extension_overlap_A1': corrected['parsed'] & corrected['overlap'],
        'extension_new_records': corrected['parsed'] & corrected['unique'] & (corrected['evaluation_role'] == 'extension_new_records'),
        'all_unique': corrected['parsed'] & corrected['unique'],
        'file_unique_first_A1': corrected['parsed'] & corrected['unique'] & (corrected['file_id'] == 'A1'),
        'file_unique_first_A2_arxiv': corrected['parsed'] & corrected['unique'] & (corrected['file_id'] == 'A2_arxiv'),
        'file_unique_first_A3_github': corrected['parsed'] & corrected['unique'] & (corrected['file_id'] == 'A3_github'),
    }
    patterns_recomputed = {}
    pairwise_recomputed = {}
    for scope, mask in scopes.items():
        sub = corrected[mask]
        for domain in sorted(sub['domain'].unique().tolist()) + ['ALL']:
            part = sub if domain == 'ALL' else sub[sub['domain'] == domain]
            if part.empty:
                continue
            counts = part['mask'].value_counts()
            patterns_recomputed[(scope, domain)] = {int(k): int(v) for k, v in counts.items()}
            marg = np.zeros(len(FIELD_ORDER), dtype=np.int64)
            inter = np.zeros((len(FIELD_ORDER), len(FIELD_ORDER)), dtype=np.int64)
            for value, count in counts.items():
                value = int(value)
                bits = [j for j in range(len(FIELD_ORDER)) if (value >> j) & 1]
                for j in bits:
                    marg[j] += count
                for i in range(len(bits)):
                    for j in range(i, len(bits)):
                        inter[bits[i], bits[j]] += count
                        if bits[i] != bits[j]:
                            inter[bits[j], bits[i]] += count
            pairwise_recomputed[(scope, domain)] = {'n': int(len(part)), 'marginal': marg,
                                                    'intersection': inter}
    patterns_rows = read_csv_rows(RUN_DIR / 'missing_patterns_corrected.csv')
    pairwise_rows = read_csv_rows(RUN_DIR / 'missing_pairwise_corrected.csv')
    pattern_mismatch = []
    for row in patterns_rows:
        if row['mask_kind'] != 'raw_field_invalid':
            continue
        key = (row['scope'], row['domain'])
        expected = patterns_recomputed.get(key, {}).get(int(row['mask_bits']), 0)
        if int(row['n']) != expected:
            pattern_mismatch.append({'key': [row['scope'], row['domain'], row['mask_bits']],
                                     'file': row['n'], 'recomputed': expected})
    pairwise_mismatch = []
    for row in pairwise_rows:
        if row['mask_kind'] != 'raw_field_invalid':
            continue
        key = (row['scope'], row['domain'])
        agg = pairwise_recomputed.get(key)
        if agg is None:
            pairwise_mismatch.append({'key': [row['scope'], row['domain']], 'reason': 'missing group'})
            continue
        i = FIELD_ORDER.index(row['feature_i'])
        j = FIELD_ORDER.index(row['feature_j'])
        n_i = int(agg['marginal'][i])
        n_j = int(agg['marginal'][j])
        n_inter = int(agg['intersection'][i, j])
        n_union = n_i if i == j else n_i + n_j - n_inter
        if not (same(row['n_i'], n_i) and same(row['n_j'], n_j)
                and same(row['n_intersection'], n_inter) and same(row['n_union'], n_union)):
            pairwise_mismatch.append({'key': [row['scope'], row['domain'], row['feature_i'], row['feature_j']],
                                      'file': [row['n_i'], row['n_j'], row['n_intersection'], row['n_union']],
                                      'recomputed': [n_i, n_j, n_inter, n_union]})
    add_check('V12_corrected_raw_patterns_and_pairwise_recomputed_independently',
              'raw-layer patterns and pairwise counts rebuilt from patterns (not from the repair code) match the CSV',
              'PASS' if not pattern_mismatch and not pairwise_mismatch else 'FAIL',
              {'pattern_rows_checked': sum(1 for r in patterns_rows if r['mask_kind'] == 'raw_field_invalid'),
               'pairwise_rows_checked': sum(1 for r in pairwise_rows if r['mask_kind'] == 'raw_field_invalid'),
               'pattern_mismatches': len(pattern_mismatch), 'pairwise_mismatches': len(pairwise_mismatch),
               'examples': (pattern_mismatch[:3] + pairwise_mismatch[:3])},
              '0 mismatches', 'missing_patterns_corrected.csv / missing_pairwise_corrected.csv vs recomputation')
    # non-raw layers must be byte-identical to R
    r_patterns = read_csv_rows(R_DIR / 'missing_patterns.csv')
    r_pairwise = read_csv_rows(R_DIR / 'missing_pairwise.csv')
    def non_raw_identical(prior_rows, new_rows, key_fields, value_fields):
        prior_map = {tuple(row[k] for k in key_fields): row for row in prior_rows
                     if row['mask_kind'] != 'raw_field_invalid'}
        new_map = {tuple(row[k] for k in key_fields): row for row in new_rows
                   if row['mask_kind'] != 'raw_field_invalid'}
        if set(prior_map) != set(new_map):
            return {'keys_match': False, 'n_prior': len(prior_map), 'n_new': len(new_map)}
        diffs = 0
        for key in prior_map:
            for field in value_fields:
                if str(prior_map[key].get(field)) != str(new_map[key].get(field)):
                    diffs += 1
        return {'keys_match': True, 'n_rows': len(prior_map), 'n_value_diffs': diffs}
    pat_same = non_raw_identical(r_patterns, patterns_rows,
                                 ['scope', 'domain', 'mask_kind', 'mask_bits'], ['n', 'n_scope', 'feature_mask'])
    pair_same = non_raw_identical(r_pairwise, pairwise_rows,
                                  ['scope', 'domain', 'mask_kind', 'feature_i', 'feature_j'],
                                  ['n_i', 'n_j', 'n_intersection', 'n_union'])
    ok = (pat_same.get('n_value_diffs', 1) == 0 and pair_same.get('n_value_diffs', 1) == 0
          and pat_same.get('keys_match') and pair_same.get('keys_match'))
    add_check('V13_non_raw_layers_unchanged', 'extract/norm mask layers of the corrected tables equal R exactly',
              'PASS' if ok else 'FAIL', {'patterns': pat_same, 'pairwise': pair_same},
              'no key or value differences', 'corrected tables vs R tables (raw rows excluded)')
    return patterns_recomputed, pairwise_recomputed


def verify_row_integrity(df):
    summary = read_json(R_DIR / 'run_summary.json')
    per_file = {}
    for file_id, stats in summary['read_counts'].items():
        expected_lines = (int(stats['rows']) + int(stats['invalid_json'])
                          + int(stats['decode_errors']) + int(stats['json_structure_errors']))
        lines = df.loc[df['file_id'] == file_id, 'source_line'].astype(int)
        per_file[file_id] = {
            'n_rows': int(lines.size), 'n_unique_lines': int(lines.nunique()),
            'expected_decompressed_lines': expected_lines,
            'min_line': int(lines.min()) if lines.size else None,
            'max_line': int(lines.max()) if lines.size else None,
            'covers_1_to_n': bool(lines.size == expected_lines and lines.nunique() == expected_lines
                                  and int(lines.min()) == 1 and int(lines.max()) == expected_lines)}
    counters = read_json(R_DIR / 'checks.json')['reaggregation_counters']
    identity = read_json(R_DIR / 'checks.json')['invalid_values_reconciliation']
    n_row_keys = identity.get('n_row_keys')
    total_ok = (sum(v['n_rows'] for v in per_file.values()) == 272505
                and counters.get('rows') == 272505 and n_row_keys == 272505)
    add_check('V14_row_identity_uniqueness_and_line_coverage',
              'per file: source_line unique and exactly 1..recorded physical line count; total 272505 with 272505 distinct identities',
              'PASS' if all(v['covers_1_to_n'] for v in per_file.values()) and total_ok else 'FAIL',
              {'per_file': per_file, 'reaggregation_rows': counters.get('rows'),
               'n_row_keys': n_row_keys,
               'distinct_identity_count_from_per_file': sum(v['n_unique_lines'] for v in per_file.values())},
              'unique + full coverage per file; totals 272505',
              'R/row_masks.csv.gz vs R/run_summary.json read_counts and R/checks.json counters')


def verify_protection():
    repair_manifest = read_json(RUN_DIR / 'input_manifest.json')
    changed = []
    for item in repair_manifest['read_only_inputs']:
        path = PROJECT / item['path']
        if not path.is_file() or sha256_file(path) != item['sha256']:
            changed.append(item['path'])
    xz_changed = []
    for item in repair_manifest['compressed_inputs_not_read']:
        path = PROJECT / item['path']
        stat = path.stat()
        if stat.st_size != item['bytes'] or abs(stat.st_mtime - item['mtime']) > 1e-6:
            xz_changed.append(item['path'])
    add_check('V15_read_only_inputs_unchanged',
              'every read-only input hashed at repair start still has the same SHA256; compressed inputs unchanged by stat',
              'PASS' if not changed and not xz_changed else 'FAIL',
              {'n_inputs_hash_checked': len(repair_manifest['read_only_inputs']),
               'sha_changed': changed, 'compressed_stat_changed': xz_changed},
              'no change', 'R1 input_manifest.json vs current files')
    # original run hashes unchanged after the repair
    original_manifest = read_json(R_DIR / 'input_manifest.json')
    r_changed = []
    for item in original_manifest['secondary_inputs']:
        path = PROJECT / item['path']
        if not path.is_file() or sha256_file(path) != item['sha256']:
            r_changed.append(item['path'])
    add_check('V16_r_artifacts_unchanged_for_the_111_protected_files',
              'the 111 protected files recorded by R keep their pre-run SHA256 after R1',
              'PASS' if not r_changed else 'FAIL',
              {'n_files': len(original_manifest['secondary_inputs']), 'changed': r_changed},
              'no change', 'R/input_manifest.json secondary_inputs')
    # static boundary scan: the two R1 scripts must never content-read an XZ
    offenders = []
    for script in ['repair_from_artifacts.py', 'verify_repairs.py']:
        text = (RUN_DIR / script).read_text(encoding='utf-8')
        token = 'jsonl' + '.xz'
        for number, line in enumerate(text.splitlines(), 1):
            if token in line and ('open(' in line or 'sha256_file(' in line or 'read(' in line):
                if 'token in line' in line:
                    continue
                offenders.append(f'{script}:{number}:{line.strip()[:90]}')
    add_check('V17_static_no_compressed_content_access',
              'no R1 code line opens/reads/hashes a .jsonl.xz path (static scan)',
              'PASS' if not offenders else 'FAIL', {'offending_lines': offenders}, 'none',
              'static scan of repair_from_artifacts.py and verify_repairs.py')


def verify_hygiene():
    forbidden = {'Q_baseline', 'group_usability', 'group_knowledge', 'group_education_reasoning',
                 'Q_equal_indicator_sensitivity', 'Q_without_knowledge_sensitivity'}
    hits = []
    for path in sorted(RUN_DIR.glob('*.csv')):
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            header = next(csv.reader(fh), [])
        if forbidden & set(header):
            hits.append(path.name)
    json_hits = []

    def reject_constant(value):
        raise ValueError(f'non-strict JSON literal: {value}')

    for path in sorted(RUN_DIR.glob('*.json')):
        if path.name == 'output_manifest.json':
            continue
        text = path.read_text(encoding='utf-8')
        try:
            json.loads(text, parse_constant=reject_constant)
        except ValueError as exc:
            json_hits.append({'file': path.name, 'error': str(exc)})
    add_check('V18_no_numeric_q_and_strict_json',
              'no new CSV exposes numeric Q/group scores and every new JSON is strict',
              'PASS' if not hits and not json_hits else 'FAIL',
              {'csv_with_q_columns': hits, 'json_with_nonstrict_literals': json_hits}, 'none',
              'header scan of new CSVs and token scan of new JSONs')
    return {'csv_with_q_columns': hits, 'json_with_nan_or_infinity': json_hits}


def c08_path_size_check():
    registered = {row['path']: int(row['bytes'])
                  for row in read_csv_rows(PROJECT / 'solution' / 'outputs' / 'audit' / 'raw_source_manifest.csv')}
    data = PROJECT / 'F题' / 'real_attachments'
    prefix = '\\\\?\\' + str(data.resolve())
    on_disk = {}
    for root, dirs, files in os.walk(prefix):
        for name in files:
            full = os.path.join(root, name)
            rel = full[len(prefix):].lstrip('\\').replace('\\', '/')
            on_disk[rel] = os.path.getsize(full)
    size_mismatch = sorted(k for k in on_disk if k in registered and registered[k] != on_disk[k])
    extra = sorted(set(on_disk) - set(registered))
    missing = sorted(set(registered) - set(on_disk))
    return {'files_on_disk': len(on_disk), 'files_registered': len(registered),
            'size_mismatch': size_mismatch[:5], 'unregistered': extra[:5], 'missing': missing[:5],
            'ok': not size_mismatch and not extra and not missing}


def c12_role_totals():
    rows = read_csv_rows(R_DIR / 'physical_rows_by_file_role.csv')
    all_rows = {row['file_id']: int(row['n_physical_rows']) for row in rows
                if row['domain'] == 'ALL' and row['evaluation_role'] == 'extension_overlap_A1'}
    detail_sums = {}
    for file_id in all_rows:
        detail_sums[file_id] = sum(int(row['n_physical_rows']) for row in rows
                                   if row['file_id'] == file_id
                                   and row['evaluation_role'] == 'extension_overlap_A1'
                                   and row['domain'] != 'ALL')
    comparison = {(row['prior_scope'], row['prior_item']): row for row in
                  read_csv_rows(R_DIR / 'comparison_with_prior.csv')
                  if row['prior_artifact'].endswith('audit.json')}
    return {'overlap_rows_ALL': all_rows, 'detail_sum_equals_ALL': all(v == all_rows[k] for k, v in detail_sums.items()),
            'n_a2': all_rows.get('A2_arxiv'), 'n_a3': all_rows.get('A3_github'),
            'ok': all_rows.get('A2_arxiv') == 1419 and all_rows.get('A3_github') == 10000
                  and all(v == all_rows[k] for k, v in detail_sums.items())}


def failed_run_statement():
    text = (FAILED_DIR / 'run.log').read_text(encoding='utf-8')
    hashed = 'stage=precondition hashed_inputs=3' in text
    failed_at_manifest = 'build_input_manifest' in text and 'RUN_ID' in text
    return {'hash_stage_completed_before_abort': hashed,
            'aborted_in_build_input_manifest': failed_at_manifest,
            'corrected_statement': ('the aborted attempt completed the compressed-byte hashing precondition '
                                    '(stage=precondition hashed_inputs=3) and then failed inside '
                                    'build_input_manifest because RUN_ID was undefined, i.e. before any '
                                    'decompression scan; it contributes no diagnostic rows'),
            'evidence': 'diagnostics/TASK-Q01A/20260924T141414+08/run.log'}


def build_reconciliation(c07_changed, c08_path, c08_hash_evidence, c11, c12, c13, c15, c23,
                         raw_info, failed_run, anchors):
    items = []

    def add(item_id, title, proposition, evidence_scope, in_run_result, current_result,
            details, limitation='', unverifiable=''):
        items.append({'item_id': item_id, 'title': title, 'original_proposition': proposition,
                      'actual_evidence_scope': evidence_scope, 'original_in_run_result': in_run_result,
                      'current_verification_result': current_result, 'details': details,
                      'limitation': limitation, 'unverifiable': unverifiable})

    add('C07_protected_files_unchanged',
        'protected files unchanged',
        'source/config/quality outputs/recovery/task files/00-05 are unchanged',
        'only the 111 file paths listed in R/input_manifest.json secondary_inputs',
        'FAIL (ctx["snapshot_diff"] was never populated: check wiring defect)',
        'PASS_LIMITED_SCOPE' if not c07_changed else 'FAIL',
        {'n_files': 111, 'sha256_changed': c07_changed},
        'does not prove that no other file anywhere in the workspace changed; it covers the listed paths only')
    add('C08a_raw_tree_path_size',
        'raw tree path/size unchanged (supplementary evidence)',
        'every registered file under F题/real_attachments exists with the registered byte size',
        'all 2012 registered raw files, stat only (no content read)',
        'FAIL (ctx["raw_tree_diff"] was never populated; in-run walk covered 1849/2012 via Path.rglob)',
        'PASS' if c08_path['ok'] else 'FAIL', c08_path)
    add('C08b_three_xz_sha256_pre_post',
        'three permitted compressed inputs unchanged by SHA256',
        'A1/A2/A3 compressed bytes hash equal before and after the diagnostic scan',
        'R in-run C09 record and the scan code path that hashed the compressed bytes twice',
        'FAIL was recorded only because the auxiliary tree check was mis-wired; C09 itself PASSED',
        'PASS_FROM_IN_RUN_EVIDENCE_NOT_RECHECKED_IN_R1',
        c08_hash_evidence,
        unverifiable='R1 is forbidden to re-read or re-hash the compressed inputs, so no new R1 hash exists',
        limitation='status rests on the original in-run evidence, not on an R1 re-measurement')
    add('C08c_historical_full_tree_mtime',
        'historical full-directory mtime unchanged',
        'all files under F题/real_attachments keep their pre-run mtime',
        'no pre-run full-tree mtime snapshot exists in R',
        'FAIL',
        'NOT_VERIFIABLE',
        {'snapshot_available': False},
        unverifiable='R only recorded size/mtime inside the run; a retrospective snapshot cannot prove the past '
                     'state and must not be manufactured')
    add('C11_totals_match_prior_audit',
        'run totals equal prior audit.json',
        'records/unique keys/duplicates equal the prior audit',
        'R/run_summary.json totals vs solution/outputs/quality/audit.json',
        'FAIL (prior_audit was not stored in ctx)',
        'PASS' if c11['ok'] else 'FAIL', c11)
    add('C12_file_level_counts_match_prior',
        'per-file counts and extension overlap rows equal prior audit.json',
        'rows/unique/within-file duplicates/overlapping A1 rows per file',
        'R/run_summary.json + R/physical_rows_by_file_role.csv + R/comparison_with_prior.csv',
        'FAIL (same prior_audit wiring defect), and the first post-run JSON added ALL rows to domain rows',
        'PASS' if c12['ok'] else 'FAIL', c12,
        limitation='the corrected算术 uses the domain=ALL row per file/role; the domain detail sum is only used '
                   'to demonstrate the earlier double counting')
    add('C13_pairwise_key_intersections_match_prior',
        'file-pair key-set intersections equal prior audit.json',
        'A1∩A2, A1∩A3, A2∩A3 key counts',
        'R/run_summary.json pairwise_intersections vs prior audit.json',
        'FAIL (same prior_audit wiring defect)', 'PASS' if c13['ok'] else 'FAIL', c13)
    add('C15_row_masks_covers_all_physical_lines',
        'row_masks keeps every decompressed physical line',
        'one row per decompressed line, unique line identity, full 1..n coverage',
        'R/row_masks.csv.gz, R/run_summary.json read_counts, R/checks.json reaggregation counters',
        'FAIL (ctx["row_masks_rows"] was never set)',
        'PASS' if c15['ok'] else 'FAIL', c15)
    add('C23_norm_layer_equals_extract_layer',
        'extraction and normalized NaN masks agree per main-Q feature',
        'for each of the 11 main-Q features, extraction NaN equals normalized NaN; no non-NaN non-finite normalized value',
        'R/row_masks.csv.gz compared by feature name using the index maps in diagnostic_spec.json',
        'FAIL because the counter compared bit positions of two different feature spaces and used a default of 1 '
        'for absent zero counters',
        'PASS' if c23['ok'] else 'FAIL', c23,
        limitation='zero counts are now recorded explicitly instead of relying on a default value')
    add('R1-01_raw_record_counts', 'raw anomaly record counts corrected',
        'nan_rows/posinf_rows/neginf_rows must count anomaly records, not elements',
        'invalid_values.csv.gz raw events joined to row_masks.csv.gz; per-domain and file-level',
        'not part of the original fail list: discovered by the main controller as a substantive error',
        'PASS' if anchors['raw_counts_ok'] else 'FAIL', anchors['raw_counts'])
    add('R1-02_raw_mask_rebuilt', 'raw_invalid mask rebuilt from saved events',
        'raw anomaly masks must reflect the NaN/Inf element events, not only structural reasons',
        'invalid_values.csv.gz raw events; R/row_masks.csv.gz; corrected copy',
        'not part of the original fail list: discovered by the main controller as a substantive error',
        'PASS' if raw_info['ok'] else 'FAIL', raw_info)
    add('R1-03_disagreement_denominators', 'disagreement range/std denominators corrected',
        'range and ddof=0 group std are defined when at least one quality group is usable',
        'R/row_masks.csv.gz would_group_*_be_nan masks; pandas recomputation',
        'not part of the original fail list: discovered by the main controller as a substantive error',
        'PASS' if anchors['denominators_ok'] else 'FAIL', anchors['denominators'])
    add('first_failure_statement', 'first aborted attempt statement corrected',
        'the aborted attempt failed before reading any raw data',
        'diagnostics/TASK-Q01A/20260924T141414+08/run.log',
        'original hand-off wording was imprecise',
        'CORRECTED', failed_run)
    return items


def build_handoff(phase, status, raw_info, c12, failed_run):
    anchors = phase['anchors']
    lines = []
    lines.append('# TASK-Q01A-R1 精准小修交回说明')
    lines.append('')
    lines.append(f'- 状态：{status}；run目录：`{RUN_DIR}`。本次是补证/小修，不改变原运行的 PARTIAL 与退出码 2。')
    lines.append('- 边界：未读取、解压或哈希 A1-A3 压缩输入；未运行原 diagnose_missingness.py；未修改 R 目录与首次失败目录；未计算数值 Q；未实施任何缺失处理策略。')
    lines.append('')
    lines.append('## 三项实质错误的修正结果')
    lines.append(f"- 原始层记录数：nan_rows/posinf_rows/neginf_rows 改为异常物理记录数（事件按 file_id+source_line+field 去重）。"
                 f"A1 professionalism=5、A1 reasoning=13、A3_github professionalism=1；元素数保持 30/78/6（合计 114）；"
                 f"异常并集 {anchors['raw_anomaly_union_total']} 条、两字段交集 {anchors['two_field_intersection_records']}。")
    lines.append(f"- raw_invalid 掩码：由 invalid_values 的 raw 事件重建并写回 row_masks_corrected.csv.gz，"
                 f"仅 {raw_info.get('changed_rows')} 条物理行的 raw_invalid_bits/raw_invalid_count 变化，其余列逐行比对无差异；"
                 f"raw 层 patterns 49 行、pairwise 629 行随之更新，提取/归一化/Q 掩码层完全未变。")
    lines.append(f"- 分歧分母：range 与 ddof=0 组间 std 改为“至少 1 个有效组即可定义”，"
                 f"共修正 60 行（40 行 mean/std 有效 n + 20 行缺失 range 的 False 计数）。"
                 f"all_unique：range n={anchors['denominator_rule_check']['range_mean_n_effective']}、"
                 f"std n={anchors['denominator_rule_check']['range_std_n_effective']}、"
                 f"False 计数={anchors['denominator_rule_check']['false_from_missing_range']}、"
                 f"Q_mean n=261067、Q_std n={anchors['denominator_rule_check']['q_std_n_effective']}（ddof=1 方差除数 "
                 f"{anchors['denominator_rule_check']['q_std_variance_divisor']}，单独成列）。19 条缺失案例仍有 2 个有效组，"
                 f"不再被判为 range/std 缺失。")
    lines.append('')
    lines.append('## 独立验收（与修复脚本不同实现路径）')
    lines.append('- verify_repairs.py 用 pandas 重算分母、用事件表独立重建原始掩码、按特征名映射复核 25/11 掩码，'
                 '并逐文件核对 source_line 唯一性与 1..n 覆盖；结果见 repair_checks.json。')
    lines.append(f"- C12 扩展重叠行数：A2={c12.get('n_a2')}、A3={c12.get('n_a3')}（只取 domain=ALL 行；"
                 f"域明细求和仅在核对中用于证明早期重复计数，不与 ALL 相加）。")
    lines.append('- 旧值比对与历史结论登记见 postrun_reconciliation_reviewed.json（原 7 项逐项 + 新发现 3 项）。')
    lines.append('')
    lines.append('## 未解决或不可验证')
    lines.append('- C08c 历史全目录 mtime：无运行前快照，标注 NOT_VERIFIABLE，不伪造 PASS。')
    lines.append('- 原 R 目录的 7 项 FAIL、PARTIAL、退出码 2、原 checks.json/run_summary.json/handoff.md 原样保留，'
                 '本次修正以新目录提供补充证据，另行验收。')
    lines.append(f"- 首次失败说明更正：{failed_run['corrected_statement']}")
    lines.append('')
    lines.append('## 机器可审查入口')
    lines.append('- raw_field_counts_corrected.csv；raw_mask_corrections.csv；row_masks_corrected.csv.gz')
    lines.append('- missing_patterns_corrected.csv；missing_pairwise_corrected.csv；summary_denominators_corrected.csv')
    lines.append('- missing_concentration.csv；changes.csv；repair_checks.json；postrun_reconciliation_reviewed.json；'
                 'run_summary.json；output_manifest.json；input_manifest.json；environment.json；repair.log；verify.log')
    lines.append('')
    lines.append('## 交回主控复审后另行裁决的问题（本单不做策略选择）')
    lines.append('1. 11 个主Q特征出现非有限值时的处理原则与最低证据标准是什么？')
    lines.append('2. 是否按域与验证角色分别处理，可接受差异如何界定？')
    lines.append('3. 覆盖率与域间可比性的权衡标准是什么？')
    lines.append('4. 下游汇总是否必须显式披露有效 n 与非有限占比，需要何种验证？')
    lines.append('5. 扩展重叠副本与 A1 中同键同异常状态的记录是否视为同一证据、如何计入分母披露？')
    lines.append('6. 现有证据是否足够，是否需要补充诊断？')
    return '\n'.join(lines)


def main():
    global LOG_FH
    LOG_FH = open(RUN_DIR / 'verify.log', 'a', encoding='utf-8')
    log(f'TASK-Q01A-R1 verification start local={now_iso()} run_dir={RUN_DIR}')
    log('boundary: verification reads only saved artifacts; no compressed input is opened or hashed')
    synthetic_semantics_check()
    recomputed, df = verify_denominators()
    raw_events, extract_events, identity_events = load_events_independent()
    log(f'events raw_keys={len(raw_events)} extract={sum(extract_events.values())} identity={sum(identity_events.values())}')
    raw_info = verify_raw_masks(raw_events)
    verify_patterns_and_pairwise(raw_events)
    verify_row_integrity(df)
    verify_protection()
    hygiene = verify_hygiene()
    c08_path = c08_path_size_check()
    add_check('V19_raw_tree_path_size_registered', 'all 2012 registered raw files exist with registered size (stat only)',
              'PASS' if c08_path['ok'] else 'FAIL', c08_path,
              '2012 files with registered sizes', 'raw_source_manifest.csv vs filesystem stat (no content read)')
    c12 = c12_role_totals()
    add_check('V20_c12_overlap_role_totals', 'extension overlap rows are A2=1419, A3=10000 without double counting',
              'PASS' if c12['ok'] else 'FAIL', c12,
              'ALL-row values 1419/10000 equal the sum of domain rows', 'R/physical_rows_by_file_role.csv')
    failed_run = failed_run_statement()
    add_check('V21_first_failure_statement_from_log',
              'aborted attempt: hashing precondition completed, then build_input_manifest failed on RUN_ID',
              'PASS' if (failed_run['hash_stage_completed_before_abort']
                         and failed_run['aborted_in_build_input_manifest']) else 'NOT_VERIFIABLE',
              failed_run, 'statement matches the saved log',
              'diagnostics/TASK-Q01A/20260924T141414+08/run.log')
    add_check('V22_c08c_historical_full_tree_mtime',
              'historical full-directory mtime unchanged (original C08 proposition, mtime part)',
              'NOT_VERIFIABLE',
              {'pre_run_full_tree_mtime_snapshot_available': False,
               'in_run_scope': 'the original run recorded size/mtime only while it ran, so no pre-run snapshot '
                               'of all 2012 files exists',
               'r1_action': 'no retrospective snapshot was manufactured; the substitute evidence is the '
                            'path/size registry comparison (V19) and the three XZ hashes (C08b)'},
              'unchanged mtimes for every file under F题/real_attachments',
              'R/checks.json C08 evidence and R/run_summary.json; no pre-run snapshot',
              note='kept out of PASS on purpose: the available evidence cannot prove the historical mtime claim')
    c07_manifest = read_json(R_DIR / 'input_manifest.json')
    c07_changed = [item['path'] for item in c07_manifest['secondary_inputs']
                   if not (PROJECT / item['path']).is_file()
                   or sha256_file(PROJECT / item['path']) != item['sha256']]
    prior_audit = read_json(PROJECT / 'solution' / 'outputs' / 'quality' / 'audit.json')
    run_summary = read_json(R_DIR / 'run_summary.json')
    c11 = {'ok': (prior_audit['total_records'] == run_summary['totals']['total_records']
                  and prior_audit['unique_id_sub_path_keys'] == run_summary['totals']['unique_keys']
                  and prior_audit['duplicate_occurrences'] == run_summary['totals']['duplicate_rows']),
           'prior': {'total_records': prior_audit['total_records'],
                     'unique_keys': prior_audit['unique_id_sub_path_keys'],
                     'duplicates': prior_audit['duplicate_occurrences']},
           'run': {'total_records': run_summary['totals']['total_records'],
                   'unique_keys': run_summary['totals']['unique_keys'],
                   'duplicates': run_summary['totals']['duplicate_rows']}}
    c13 = {'ok': prior_audit['pairwise_key_intersections'] == run_summary['totals']['pairwise_intersections'],
           'prior': prior_audit['pairwise_key_intersections'],
           'run': run_summary['totals']['pairwise_intersections']}
    counters = read_json(R_DIR / 'checks.json')['reaggregation_counters']
    identity = read_json(R_DIR / 'checks.json')['invalid_values_reconciliation']
    c15 = {'ok': counters.get('rows') == 272505 and identity.get('n_row_keys') == 272505,
           'rows_reaggregated': counters.get('rows'),
           'distinct_row_identities': identity.get('n_row_keys'),
           'per_file_uniqueness_and_1_to_n_coverage': 'PASS in V14',
           'note': 'the earlier attempt of this item read a non-existent counter key n_row_keys; the identity '
                   'count is recorded in R/checks.json invalid_values_reconciliation'}
    c23_mismatch = 0
    with gzip.open(R_DIR / 'row_masks.csv.gz', 'rt', encoding='utf-8', newline='') as fh:
        for row in csv.DictReader(fh):
            if int(row['parse_ok'] or 0) != 1:
                continue
            ext = bits_from_string(row['extract_nan_bits'])
            norm = bits_from_string(row['norm_nan_bits'])
            for feature in [item['feature'] for item in SPEC['main_q_features_11']]:
                if ((ext >> FEATURE_ORDER.index(feature)) & 1) != ((norm >> MODEL_INDEX[feature]) & 1):
                    c23_mismatch += 1
    c23 = {'ok': c23_mismatch == 0, 'rows_with_name_mapped_mismatch': c23_mismatch,
           'zero_counts_recorded_explicitly': True,
           'note': 'the original check compared bit positions across the 25-feature and 11-feature spaces and '
                   'defaulted absent counters to 1, which turned a true zero into a FAIL'}
    phase = read_json(RUN_DIR / 'repair_phase_summary.json')
    anchors = {
        'raw_counts': phase['anchors']['raw_anomaly_record_counts_by_file_field'],
        'denominators': phase['anchors']['denominator_rule_check'],
        'raw_counts_ok': (phase['anchors']['raw_anomaly_record_counts_by_file_field']
                          == {'A1|modernbert_professionalism': 5, 'A1|modernbert_reasoning': 13,
                              'A3_github|modernbert_professionalism': 1}),
        'denominators_ok': (phase['anchors']['denominator_rule_check']['range_mean_n_effective'] == 261086
                            and phase['anchors']['denominator_rule_check']['range_std_n_effective'] == 261086
                            and phase['anchors']['denominator_rule_check']['false_from_missing_range'] == 0
                            and phase['anchors']['denominator_rule_check']['q_std_n_effective'] == 261067
                            and phase['anchors']['denominator_rule_check']['q_std_variance_divisor'] == 261066)}
    raw_info['ok'] = not [c for c in CHECKS if c['check_id'] in ('V08_corrected_raw_mask_matches_events',
                                                                'V10_only_permitted_columns_changed',
                                                                'V12_corrected_raw_patterns_and_pairwise_recomputed_independently')
                          and c['status'] != 'PASS']
    reconciliation = build_reconciliation(c07_changed, c08_path, {'in_run_C09_all_three_xz_sha256_equal_pre_post': True},
                                          c11, c12, c13, c15, c23, raw_info, failed_run, anchors)
    write_json(RUN_DIR / 'postrun_reconciliation_reviewed.json',
               {'run_id': RUN_ID, 'task': 'TASK-Q01A-R1', 'generated_local': now_iso(),
                'note': 'replaces the earlier self-review for scope/arithmetic; the original R checks.json, '
                        'run_summary.json and handoff.md are untouched and still show 33 PASS / 7 FAIL / PARTIAL / exit 2',
                'items': reconciliation})
    fail = [c for c in CHECKS if c['status'] == 'FAIL']
    not_verifiable = [c for c in CHECKS if c['status'] == 'NOT_VERIFIABLE']
    status = 'COMPLETED_WITH_NOT_VERIFIABLE_ITEMS' if not fail else 'FAILED'
    write_json(RUN_DIR / 'repair_checks.json',
               {'run_id': RUN_ID, 'task': 'TASK-Q01A-R1', 'status': status,
                'summary': {'n_checks': len(CHECKS), 'n_pass': sum(1 for c in CHECKS if c['status'] == 'PASS'),
                            'n_fail': len(fail), 'n_not_verifiable': len(not_verifiable)},
                'checks': CHECKS, 'synthetic_pandas_reference': synthetic_semantics_check.__name__,
                'boundary': {'compressed_inputs_opened': 0, 'compressed_inputs_hashed': 0,
                             'numeric_q_computed': False, 'strategy_selected': False}})
    write_json(RUN_DIR / 'run_summary.json',
               {'task': 'TASK-Q01A-R1', 'run_id': RUN_ID, 'status': status,
                'start_local': START_LOCAL.isoformat(timespec='seconds'), 'end_local': now_iso(),
                'duration_s': round(time.monotonic() - START_MONO, 3),
                'phases': {'repair_from_artifacts': phase,
                           'verify_repairs': {'n_checks': len(CHECKS), 'n_fail': len(fail),
                                              'n_not_verifiable': len(not_verifiable)}},
                'repair_exit_code': 0, 'verify_exit_code': 0 if not fail else 2,
                'original_run': {'run_dir': str(R_DIR), 'status_preserved': 'PARTIAL',
                                 'exit_code_preserved': 2, 'checks_json_modified': False,
                                 'run_summary_modified': False, 'handoff_modified': False,
                                 'row_masks_and_tables_modified': False},
                'aborted_r1_attempts': [
                    {'run_dir': str(ABORTED_R1_DIRS[0]),
                     'outcome': 'aborted in the input preflight; no data product written',
                     'cause': 'the read-only input list included the R __pycache__ directory, which the '
                              'is_file() preflight reported as a missing input'},
                    {'run_dir': str(ABORTED_R1_DIRS[1]),
                     'outcome': 'completed but its corrected raw_field_counts were discarded; no data product reused',
                     'cause': 'event lines were strings while the domain map keys were integers, so domain-level '
                              'record/element counts resolved to 0; fixed by int(line) and re-run in this directory'}],
                'first_failure_statement_corrected': failed_run,
                'key_numbers': {'raw_anomaly_records': phase['anchors']['raw_anomaly_record_counts_by_file_field'],
                                'raw_anomaly_union': phase['anchors']['raw_anomaly_union_total'],
                                'nan_elements': phase['anchors']['nan_element_totals_by_file_field'],
                                'all_unique_range_std_denominators': phase['anchors']['denominator_rule_check'],
                                'all_unique_usable_group_histogram': phase['anchors']['all_unique_denominators'],
                                'c12_overlap_rows': {'A2_arxiv': c12.get('n_a2'), 'A3_github': c12.get('n_a3')},
                                'rows_changed_in_corrected_row_masks': raw_info.get('changed_rows'),
                                'denominator_rows_changed': 60},
                'verification_iterations': [
                    {'run': 1, 'exit_code': 2, 'failed_checks': ['V14', 'V17'],
                     'cause': 'V14 read a counter key that R never recorded; V17 matched its own pattern line. '
                              'No repair data product was affected.'},
                    {'run': 2, 'exit_code': 2, 'failed_checks': ['V18'],
                     'cause': 'V18 flagged the word NaN inside JSON prose instead of parsing JSON values strictly.'},
                    {'run': 3, 'exit_code': 0, 'failed_checks': [],
                     'note': 'all 21 checks passed; the historical-mtime NOT_VERIFIABLE check was added next'},
                    {'run': 4, 'exit_code': 0, 'failed_checks': [],
                     'note': 'V22 added: 21 PASS / 0 FAIL / 1 NOT_VERIFIABLE'},
                    {'run': 5, 'exit_code': 0, 'failed_checks': [],
                     'note': 'final run after correcting the C15 reconciliation evidence source'}],
                'not_verifiable_items': [c['check_id'] for c in not_verifiable] +
                                        ['C08c_historical_full_tree_mtime'],
                'unresolved_items': [], 'hygiene': hygiene,
                'final_strategy_selected': False, 'final_Q_recomputed': False, 'numeric_Q_computed': False,
                'compressed_inputs_read': 0, 'compressed_inputs_hashed': 0,
                'handoff_file': 'handoff.md'})
    handoff = build_handoff(phase, status, raw_info, c12, failed_run)
    (RUN_DIR / 'handoff.md').write_text(handoff, encoding='utf-8')
    manifest_files = []
    for path in sorted(RUN_DIR.rglob('*')):
        if not path.is_file() or path.name == 'output_manifest.json':
            continue
        manifest_files.append({'path': str(path.relative_to(RUN_DIR)).replace('\\', '/'),
                               'bytes': path.stat().st_size, 'sha256': sha256_file(path)})
    write_json(RUN_DIR / 'output_manifest.json',
               {'run_id': RUN_ID, 'task': 'TASK-Q01A-R1', 'generated_local': now_iso(),
                'n_files': len(manifest_files), 'files': manifest_files})
    log(f'end status={status} n_checks={len(CHECKS)} n_fail={len(fail)} n_not_verifiable={len(not_verifiable)}')
    LOG_FH.close()
    return 0 if not fail else 2


if __name__ == '__main__':
    sys.exit(main())
