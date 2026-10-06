# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
"""TASK-T03E independent verifier (read-only, never imports the executor).

Every expectation below is recomputed from the official Q01C row-level Parquet
with formulas re-implemented inside this file; nothing is imported from
t03e_preregistered_rule_sensitivity.py and no expected value is taken from the
executor outputs.  The verifier only writes verification.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SOLUTION = Path(__file__).resolve().parents[1]
PROJECT = SOLUTION.parent
Q01C_RUN = SOLUTION / 'outputs' / 'quality_q01c' / '20260924T215718+08'
INPUT_PATH = Q01C_RUN / 'quality_features_scores.parquet'
CST = timezone(timedelta(hours=8))

DESIGN_DOMAINS = ['book', 'c4', 'commoncrawl', 'wikipedia']
ACTIVE_MIN_N = 1000
HOLDOUT_MIN_N = 200
EXTENSION_MIN_N = 200
LAMBDA_PRIMARY = 0.02
BOOTSTRAP_REPLICATES = 200
BOOTSTRAP_MIN_PASS = 190
BOOT_MAE_MAX = 0.10
BOOT_SPEARMAN_MIN = 0.98
BOOT_JACCARD_MIN = 0.85
HOLDOUT_SPEARMAN_MIN = 0.98
HOLDOUT_JACCARD_MIN = 0.85
HOLDOUT_PENALTY_MEAN_TOL = 0.05
OOS_MAX = 0.05
OVERLAP_TOL = 1e-12
VALUE_TOL = 1e-12
MASTER_SEED = 20260925

ROLES = ['A1_calibration', 'A1_holdout', 'extension_overlap_A1', 'extension_new_records']
COLUMNS = ['file_id', 'source_line', 'key_sha256', 'domain', 'evaluation_role',
           'is_unique_first', 'overlap_a1', 'Q_valid', 'Q_baseline',
           'rps_doc_frac_chars_top_2gram', 'rps_doc_frac_chars_top_3gram']


def now_iso():
    return datetime.now(CST).isoformat(timespec='seconds')


def sha256_file(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(chunk), b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    with open(path, 'r', encoding='utf-8-sig') as handle:
        return json.load(handle)


def read_rows(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def is_hex_sha256(text):
    text = str(text)
    return len(text) == 64 and all(character in '0123456789abcdef' for character in text.lower())


def penalty(values, lower, upper):
    """Independent implementation of the frozen piecewise linear penalty."""
    values = np.asarray(values, dtype=float)
    result = np.zeros(values.shape, dtype=float)
    above = values >= upper
    middle = (values > lower) & (values < upper)
    result[above] = 1.0
    result[middle] = (values[middle] - lower) / (upper - lower)
    return result


def deterministic_order(scores, keys):
    return np.lexsort((np.asarray(keys, dtype=object), -np.asarray(scores, dtype=float)))


def rank_positions(scores, keys):
    order = deterministic_order(scores, keys)
    ranks = np.empty(len(order), dtype=float)
    ranks[order] = np.arange(1, len(order) + 1, dtype=float)
    return ranks, order


def spearman_rank_difference(ranks_a, ranks_b):
    n = len(ranks_a)
    if n < 2:
        return float('nan')
    delta = np.asarray(ranks_a, dtype=float) - np.asarray(ranks_b, dtype=float)
    return float(1.0 - 6.0 * float(np.sum(delta ** 2)) / (n * (n ** 2 - 1)))


def spearman_scipy(ranks_a, ranks_b):
    ranks_a = np.asarray(ranks_a, dtype=float)
    ranks_b = np.asarray(ranks_b, dtype=float)
    a = ranks_a - ranks_a.mean()
    b = ranks_b - ranks_b.mean()
    denominator = math.sqrt(float(np.sum(a ** 2)) * float(np.sum(b ** 2)))
    return float(np.sum(a * b) / denominator) if denominator else float('nan')


def top_keys(order, n, fraction=0.10):
    k = max(1, int(math.ceil(fraction * n)))
    return set(order[:k].tolist()), k


def jaccard(left, right):
    union = len(left | right)
    return float(len(left & right) / union) if union else float('nan')


def bootstrap_subseed(domain, replicate):
    digest = hashlib.sha256(('20260925|' + str(domain) + '|' + str(replicate)).encode('utf-8'))
    return int(digest.hexdigest()[:16], 16)


def valid_mask(frame):
    return ((frame['is_unique_first'].to_numpy() == True)
            & (frame['Q_valid'].to_numpy() == True)
            & np.isfinite(frame['Q_baseline'].to_numpy(dtype=float))
            & np.isfinite(frame['rps_doc_frac_chars_top_2gram'].to_numpy(dtype=float))
            & np.isfinite(frame['rps_doc_frac_chars_top_3gram'].to_numpy(dtype=float)))


def counts_for(frame):
    unique = frame[frame['is_unique_first'].to_numpy() == True]
    n_q_valid = int((unique['Q_valid'].to_numpy() == True).sum())
    n_analysis = int(valid_mask(unique).sum())
    return {'n_total': int(len(frame)), 'n_unique_first': int(len(unique)),
            'n_Q_valid': n_q_valid, 'n_Q_missing': int(len(unique) - n_q_valid),
            'n_analysis_valid': n_analysis,
            'analysis_coverage': (n_analysis / len(unique)) if len(unique) else None}


def close(left, right, tolerance=VALUE_TOL):
    if isinstance(left, str) and left.strip() == '':
        left = None
    if isinstance(right, str) and right.strip() == '':
        right = None
    if left is None or right is None:
        return left is None and right is None
    try:
        left_value = float(left)
        right_value = float(right)
    except (TypeError, ValueError):
        return str(left) == str(right)
    if math.isnan(left_value) or math.isnan(right_value):
        return math.isnan(left_value) and math.isnan(right_value)
    return abs(left_value - right_value) <= tolerance


def sanitise(value):
    """NaN/Inf are not valid JSON: record them as null instead of writing invalid literals."""
    if isinstance(value, dict):
        return {str(key): sanitise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitise(item) for item in value]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    return value


def row_result(identifier, name, status, evidence, note=''):
    return {'id': identifier, 'name': name, 'status': status, 'evidence': evidence,
            'note': note, 'checked_local': now_iso()}


class Verifier:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.freeze_dir = self.run_dir / 'phase_a_calibration_freeze'
        self.phase_b_dir = self.run_dir / 'phase_b_frozen_validation'
        self.preflight_dir = self.run_dir / 'metadata_preflight'
        self.results = []
        self.input = None
        self.scores = None
        self.frozen_manifest = None
        self.seal = None
        self.thresholds = None
        self.active = None

    # ------------------------------------------------------------------ setup
    def load(self):
        self.input = pq.read_table(INPUT_PATH, columns=COLUMNS).to_pandas()
        self.scores = pq.read_table(self.run_dir / 'candidate_Q_scores.parquet').to_pandas()
        self.frozen_manifest = read_json(self.freeze_dir / 'freeze_manifest.json')
        self.seal = read_json(self.freeze_dir / 'FREEZE_SEALED.json')
        self.thresholds = {label: {key: float(value) for key, value in entry.items()}
                           for label, entry in self.frozen_manifest['thresholds'].items()}
        self.active = list(self.frozen_manifest['active_domains'])

    def add(self, identifier, name, status, evidence, note=''):
        self.results.append(row_result(identifier, name, status, evidence, note))

    def recompute_candidate(self, frame, lam=LAMBDA_PRIMARY):
        x2 = frame['rps_doc_frac_chars_top_2gram'].to_numpy(dtype=float)
        x3 = frame['rps_doc_frac_chars_top_3gram'].to_numpy(dtype=float)
        q = frame['Q_baseline'].to_numpy(dtype=float)
        domains = frame['domain'].astype(str).to_numpy()
        q_valid = frame['Q_valid'].to_numpy() == True
        p2 = np.zeros(len(frame), dtype=float)
        p3 = np.zeros(len(frame), dtype=float)
        status = np.array(['RULE_NOT_APPLICABLE'] * len(frame), dtype=object)
        declared = self.frozen_manifest.get('domains_status', {})
        for label in sorted(set(domains.tolist())):
            mask = domains == label
            if label not in DESIGN_DOMAINS:
                base_status = 'RULE_NOT_APPLICABLE'
            elif label not in declared:
                base_status = 'DESIGN_LABEL_ABSENT'
            elif declared[label] == 'DESIGN_LABEL_ABSENT':
                base_status = 'DESIGN_LABEL_ABSENT'
            elif declared[label] == 'INSUFFICIENT_CALIBRATION':
                base_status = 'INSUFFICIENT_CALIBRATION'
            elif declared[label] == 'CALIBRATION_DEGENERATE':
                base_status = 'CALIBRATION_DEGENERATE'
            elif label in self.active:
                base_status = 'ACTIVE'
            else:
                base_status = 'RULE_NOT_APPLICABLE'
            if base_status == 'ACTIVE':
                entry = self.thresholds[label]
                p2[mask] = penalty(x2[mask], entry['a2'], entry['b2'])
                p3[mask] = penalty(x3[mask], entry['a3'], entry['b3'])
                oos = ((x2[mask] < entry['lo2']) | (x2[mask] > entry['hi2'])
                       | (x3[mask] < entry['lo3']) | (x3[mask] > entry['hi3']))
                status[mask] = np.where(oos, 'OUT_OF_SUPPORT', 'SUPPORTED')
            else:
                status[mask] = base_status
        p = (p2 + p3) / 2.0
        qc = q * (1.0 - lam * p)
        invalid = ~q_valid
        qc[invalid] = np.nan
        p[invalid] = np.nan
        p2[invalid] = np.nan
        p3[invalid] = np.nan
        status[invalid] = 'Q_INVALID_PRESERVED'
        return {'p2': p2, 'p3': p3, 'P': p, 'Q_C': qc, 'status': status}

    def calibration_valid(self):
        frame = self.input[(self.input['evaluation_role'].astype(str) == 'A1_calibration')]
        mask = valid_mask(frame)
        return frame[mask].sort_values('key_sha256', kind='stable')


    # ------------------------------------------------------- V01 labels/counts
    def check_domain_labels(self):
        recorded = {(row['role'], row['domain']): row
                    for row in read_rows(self.phase_b_dir / 'domain_role_inventory.csv')}
        mismatches = []
        seen = set()
        role_series = self.input['evaluation_role'].astype(str)
        domain_series = self.input['domain'].astype(str)
        for (role, domain), part in self.input.groupby([role_series, domain_series], sort=True):
            role = str(role)
            domain = str(domain)
            seen.add((role, domain))
            row = recorded.get((role, domain))
            if row is None:
                mismatches.append({'key': [role, domain], 'reason': 'missing_from_inventory'})
                continue
            recomputed = counts_for(part)
            for field in ('n_total', 'n_unique_first', 'n_Q_valid', 'n_Q_missing', 'n_analysis_valid'):
                if int(row[field]) != int(recomputed[field]):
                    mismatches.append({'key': [role, domain], 'field': field,
                                       'recorded': int(row[field]),
                                       'recomputed': int(recomputed[field])})
            if not close(row['analysis_coverage'], recomputed['analysis_coverage']):
                mismatches.append({'key': [role, domain], 'field': 'analysis_coverage',
                                   'recorded': row['analysis_coverage'],
                                   'recomputed': recomputed['analysis_coverage']})
        extra = [list(key) for key in recorded if key not in seen]
        all_labels = sorted(set(domain_series.tolist()))
        recorded_labels = sorted(row['domain_label'] for row in
                                 read_rows(self.phase_b_dir / 'actual_domain_labels_all_roles.csv'))
        calibration_labels = sorted(set(domain_series[self.input['evaluation_role'].astype(str)
                                                      == 'A1_calibration'].tolist()))
        preflight_labels = sorted(row['domain_label'] for row in
                                  read_rows(self.preflight_dir / 'calibration_domain_labels.csv'))
        preflight_rows = sorted(row['domain_label'] for row in
                                read_rows(self.preflight_dir / 'calibration_domain_inventory.csv'))
        design_match = read_rows(self.preflight_dir / 'calibration_domain_label_match.csv')
        match_status = {row['design_label']: row['status'] for row in design_match}
        expected_missing = [label for label in DESIGN_DOMAINS if label not in calibration_labels]
        recorded_missing = [label for label, status in match_status.items()
                            if status != 'EXACT_MATCH']
        status = 'PASS' if (not mismatches and not extra and all_labels == recorded_labels
                            and calibration_labels == preflight_labels == preflight_rows
                            and sorted(expected_missing) == sorted(recorded_missing)) else 'FAIL'
        evidence = {'role_domain_groups_checked': len(seen), 'mismatches': mismatches,
                    'groups_only_in_output': extra, 'labels_all_roles': all_labels,
                    'labels_recorded': recorded_labels,
                    'calibration_labels_recomputed': calibration_labels,
                    'calibration_labels_recorded': preflight_labels,
                    'design_labels_absent': expected_missing}
        self.add('V01', 'domain labels and per-role x domain counts recomputed from the input',
                 status, evidence,
                 'character-exact string comparison only; DESIGN_LABEL_ABSENT is recorded, never '
                 'fixed by renaming or merging')

    # ------------------------------------------------- V02 freeze before reads
    def check_freeze_before_reads(self):
        access = [json.loads(line) for line in
                  (self.run_dir / 'access_log.jsonl').read_text(encoding='utf-8').splitlines()
                  if line.strip()]
        seal_time = datetime.fromisoformat(self.seal['sealed_local'])
        violations = []
        for record in access:
            when = datetime.fromisoformat(record['ts'])
            if when >= seal_time:
                continue
            predicate = str(record.get('logical_predicate', ''))
            if 'A1_holdout' in predicate or 'extension' in predicate:
                violations.append({'ts': record['ts'], 'purpose': record.get('purpose'),
                                   'predicate': predicate})
        preflight = pd.read_parquet(self.preflight_dir / 'calibration_rows.parquet')
        preflight_roles = sorted(preflight['evaluation_role'].astype(str).unique().tolist())
        sealed_calibration = pd.read_parquet(self.freeze_dir / 'calibration_candidate_rows.parquet')
        sealed_roles = sorted(sealed_calibration['evaluation_role'].astype(str).unique().tolist())
        holdout_summary = read_json(self.phase_b_dir / 'holdout_summary.json')
        extension_summary = read_json(self.phase_b_dir / 'extension_summary.json')
        times = {'sealed_local': seal_time,
                 'first_holdout_read_time':
                     datetime.fromisoformat(holdout_summary['first_holdout_read_time']),
                 'first_extension_read_time':
                     datetime.fromisoformat(extension_summary['first_extension_read_time'])}
        order_ok = (times['sealed_local'] < times['first_holdout_read_time']
                    < times['first_extension_read_time'])
        holdout_freeze = read_json(self.phase_b_dir / 'holdout_freeze_manifest.json')
        frozen_before_extension = (datetime.fromisoformat(holdout_freeze['generated_local'])
                                   <= times['first_extension_read_time'])
        status = 'PASS' if (not violations and preflight_roles == ['A1_calibration']
                            and sealed_roles == ['A1_calibration'] and order_ok
                            and frozen_before_extension) else 'FAIL'
        evidence = {'pre_seal_non_calibration_accesses': violations,
                    'preflight_roles': preflight_roles, 'sealed_calibration_roles': sealed_roles,
                    'read_order': {key: value.isoformat() for key, value in times.items()},
                    'order_satisfied': bool(order_ok),
                    'holdout_outputs_frozen_before_extension_read': bool(frozen_before_extension),
                    'access_records': len(access)}
        self.add('V02', 'no holdout/extension value was visible before the freeze seal and the frozen '
                 'read order holds', status, evidence)

    # -------------------------------------------------- V03 calibration quantiles
    def check_calibration_quantiles(self):
        calib = self.calibration_valid()
        rows = read_rows(self.freeze_dir / 'frozen_thresholds.csv')
        mismatches = []
        checked = 0
        for row in rows:
            label = row['domain']
            column = ('rps_doc_frac_chars_top_2gram' if row['indicator'] == 'top_2gram'
                      else 'rps_doc_frac_chars_top_3gram')
            values = calib[calib['domain'].astype(str) == label][column].to_numpy(dtype=float)
            expected = {'a_q95': np.quantile(values, 0.95, method='linear'),
                        'b_q99': np.quantile(values, 0.99, method='linear'),
                        'lo_q005': np.quantile(values, 0.005, method='linear'),
                        'hi_q995': np.quantile(values, 0.995, method='linear'),
                        'n_valid_source': len(values)}
            for key, value in expected.items():
                checked += 1
                if not close(row[key], value):
                    mismatches.append({'domain': label, 'indicator': row['indicator'], 'field': key,
                                       'recorded': row[key], 'recomputed': value})
            for key in ('a_q95', 'b_q99', 'lo_q005', 'hi_q995'):
                if not close(row[key], self.thresholds[label][{'a_q95': 'a2', 'b_q99': 'b2',
                                                              'lo_q005': 'lo2',
                                                              'hi_q995': 'hi2'}[key]
                                                          if row['indicator'] == 'top_2gram' else
                                                              {'a_q95': 'a3', 'b_q99': 'b3',
                                                               'lo_q005': 'lo3',
                                                               'hi_q995': 'hi3'}[key]]):
                    mismatches.append({'domain': label, 'indicator': row['indicator'],
                                       'field': key, 'recorded': row[key],
                                       'manifest': 'differs'})
        active_counts = {}
        for label in self.active:
            active_counts[label] = int((calib['domain'].astype(str) == label).sum())
            if active_counts[label] < ACTIVE_MIN_N:
                mismatches.append({'domain': label, 'reason': 'active but calibration n below '
                                                              + str(ACTIVE_MIN_N)})
        for label in DESIGN_DOMAINS:
            part = calib[calib['domain'].astype(str) == label]
            if len(part) >= ACTIVE_MIN_N:
                for column in ('rps_doc_frac_chars_top_2gram', 'rps_doc_frac_chars_top_3gram'):
                    values = part[column].to_numpy(dtype=float)
                    if not np.quantile(values, 0.99, method='linear') > np.quantile(values, 0.95,
                                                                                   method='linear'):
                        mismatches.append({'domain': label, 'column': column,
                                           'reason': 'q0.99 <= q0.95 but domain is not rejected'})
        status = 'PASS' if not mismatches else 'FAIL'
        self.add('V03', 'calibration n, q0.95/q0.99/q0.005/q0.995 and domain eligibility '
                 'recomputed independently', status,
                 {'values_checked': checked, 'mismatches': mismatches, 'active_n': active_counts,
                  'active_domains': self.active,
                  'manifest_thresholds': self.frozen_manifest['thresholds']})

    # ------------------------------------------------------ V04 row level arithmetic
    def check_row_level_candidate(self):
        recalculated = self.recompute_candidate(self.input)
        recorded = self.scores
        alignment = {'rows_recorded': int(len(recorded)), 'rows_input': int(len(self.input))}
        alignment['key_sequence_identical'] = bool(
            list(recorded['key_sha256'].astype(str)) == list(self.input['key_sha256'].astype(str)))
        alignment['domain_sequence_identical'] = bool(
            list(recorded['domain'].astype(str)) == list(self.input['domain'].astype(str)))
        alignment['role_sequence_identical'] = bool(
            list(recorded['evaluation_role'].astype(str))
            == list(self.input['evaluation_role'].astype(str)))
        alignment['Q_baseline_identical'] = bool(np.array_equal(
            recorded['Q_baseline'].to_numpy(dtype=float),
            self.input['Q_baseline'].to_numpy(dtype=float), equal_nan=True))
        column_report = {}
        worst = 0.0
        for recorded_column, recalculated_key in (('p_top2gram', 'p2'), ('p_top3gram', 'p3'),
                                                 ('P', 'P'), ('Q_C', 'Q_C')):
            left = recorded[recorded_column].to_numpy(dtype=float)
            right = recalculated[recalculated_key]
            nan_same = bool(np.array_equal(np.isnan(left), np.isnan(right)))
            finite = np.isfinite(left) & np.isfinite(right)
            delta = float(np.max(np.abs(left[finite] - right[finite]))) if finite.any() else 0.0
            worst = max(worst, delta)
            column_report[recorded_column] = {'nan_pattern_identical': nan_same,
                                              'max_abs_delta': delta,
                                              'value_mismatch_rows': int(np.sum(
                                                  finite & (np.abs(left - right) > VALUE_TOL))),
                                              'nan_pattern_mismatch_rows': int(np.sum(
                                                  np.isnan(left) != np.isnan(right)))}
        status_mismatch = int((recorded['Q_support_status'].astype(str).to_numpy()
                               != recalculated['status']).sum())
        status = 'PASS' if (all(item['nan_pattern_identical'] and item['max_abs_delta'] <= VALUE_TOL
                                and item['value_mismatch_rows'] == 0
                                for item in column_report.values())
                            and status_mismatch == 0
                            and alignment['key_sequence_identical']
                            and alignment['Q_baseline_identical']) else 'FAIL'
        self.add('V04', 'per-row p_top2gram, p_top3gram, P and Q_C recomputed for every physical row',
                 status, {'alignment': alignment, 'columns': column_report,
                          'worst_abs_delta': worst, 'status_mismatch_rows': status_mismatch,
                          'tolerance': VALUE_TOL,
                          'formula': 'C = D * (1 - 0.02 * (p2 + p3)/2), p_j piecewise linear '
                                     'between the frozen q0.95 and q0.99'})

    # --------------------------------------------- V05 holdout gates
    def check_holdout_gates(self):
        recorded = {row['domain']: row
                    for row in read_rows(self.phase_b_dir / 'holdout_validation.csv')}
        holdout = self.input[self.input['evaluation_role'].astype(str) == 'A1_holdout']
        recomputed_candidate = self.recompute_candidate(holdout)
        calibration = self.input[self.input['evaluation_role'].astype(str) == 'A1_calibration']
        calibration_candidate = self.recompute_candidate(calibration)
        calibration_frame = calibration.assign(P=calibration_candidate['P'])
        holdout_frame = holdout.assign(Q_C=recomputed_candidate['Q_C'],
                                       P=recomputed_candidate['P'],
                                       status=recomputed_candidate['status'])
        mismatches = []
        domains_report = {}
        for label in self.active:
            part = holdout_frame[(holdout_frame['domain'].astype(str) == label)
                                 & valid_mask(holdout_frame)]
            reference = calibration_frame[(calibration_frame['domain'].astype(str) == label)
                                          & (calibration_frame['Q_valid'].to_numpy() == True)]
            row = recorded.get(label)
            if row is None:
                mismatches.append({'domain': label, 'reason': 'missing_from_holdout_validation'})
                continue
            n = len(part)
            if n == 0:
                if row['status'] != 'INSUFFICIENT_N' or int(row['n_valid']) != 0:
                    mismatches.append({'domain': label, 'reason': 'empty domain not reported as '
                                                                  'INSUFFICIENT_N'})
                domains_report[label] = {'n_valid': 0}
                continue
            keys = part['key_sha256'].astype(str).to_numpy()
            ranks_d, order_d = rank_positions(part['Q_baseline'].to_numpy(dtype=float), keys)
            ranks_c, order_c = rank_positions(part['Q_C'].to_numpy(dtype=float), keys)
            rho_a = spearman_rank_difference(ranks_d, ranks_c)
            rho_b = spearman_scipy(ranks_d, ranks_c)
            top_d, k = top_keys(order_d, n)
            top_c, k2 = top_keys(order_c, n)
            jac = jaccard(top_d, top_c)
            penalty_mean_role = float(np.nanmean(part['P'].to_numpy(dtype=float)))
            penalty_mean_reference = float(np.nanmean(reference['P'].to_numpy(dtype=float)))
            penalty_delta = abs(penalty_mean_role - penalty_mean_reference)
            oos = float(np.mean(part['status'].to_numpy() == 'OUT_OF_SUPPORT'))
            checks = {'n_valid': n == int(row['n_valid']),
                      'spearman': close(row['spearman_C_D'], rho_a),
                      'spearman_two_implementations': close(rho_a, rho_b, 1e-9),
                      'jaccard': close(row['top10_jaccard_C_D'], jac),
                      'top_k': int(row['top_k']) == k == k2,
                      'penalty_mean_role': close(row['penalty_mean_role'], penalty_mean_role),
                      'penalty_mean_calibration': close(row['penalty_mean_calibration'],
                                                        penalty_mean_reference),
                      'penalty_mean_abs_diff': close(row['penalty_mean_abs_diff'], penalty_delta),
                      'oos_fraction': close(row['oos_fraction'], oos),
                      'top_k_ceiling': k == max(1, int(math.ceil(0.10 * n)))}
            failed = [key for key, ok in checks.items() if not ok]
            if failed:
                mismatches.append({'domain': label, 'failed': failed})
            expected_gates = {'pass_spearman': rho_a >= HOLDOUT_SPEARMAN_MIN,
                              'pass_jaccard': jac >= HOLDOUT_JACCARD_MIN,
                              'pass_penalty_mean': penalty_delta <= HOLDOUT_PENALTY_MEAN_TOL,
                              'pass_oos': oos <= OOS_MAX}
            for key, value in expected_gates.items():
                if int(row[key]) != int(value):
                    mismatches.append({'domain': label, 'field': key,
                                       'recorded': int(row[key]), 'recomputed': int(value)})
            eligible = n >= HOLDOUT_MIN_N
            if int(row['eligible']) != int(eligible):
                mismatches.append({'domain': label, 'field': 'eligible'})
            expected_status = ('PASS' if (eligible and all(expected_gates.values()))
                               else ('INSUFFICIENT_N' if not eligible else 'FAIL'))
            if row['status'] != expected_status:
                mismatches.append({'domain': label, 'field': 'status', 'recorded': row['status'],
                                   'recomputed': expected_status})
            domains_report[label] = {'n_valid': n, 'spearman': rho_a, 'jaccard': jac,
                                     'penalty_delta': penalty_delta, 'oos_fraction': oos,
                                     'expected_status': expected_status}
        summary = read_json(self.phase_b_dir / 'holdout_summary.json')
        failed_domains = [label for label, item in domains_report.items()
                          if item.get('expected_status') == 'FAIL']
        insufficient = [label for label, item in domains_report.items()
                        if item.get('n_valid', 0) < HOLDOUT_MIN_N]
        expected_summary = ('REJECT_KEEP_D' if failed_domains
                            else ('INSUFFICIENT_EVIDENCE_KEEP_D' if insufficient
                                  else 'ACCEPT_STABILITY'))
        summary_ok = summary['holdout_status'] == expected_summary
        also_active_only = set(recorded) <= set(self.active)
        status = 'PASS' if (not mismatches and summary_ok and also_active_only) else 'FAIL'
        self.add('V05', 'deterministic ordering, top-10% sets and holdout accept/reject recomputed',
                 status, {'domains': domains_report, 'mismatches': mismatches,
                          'recorded_holdout_status': summary['holdout_status'],
                          'recomputed_holdout_status': expected_summary,
                          'only_active_domains_entered_the_pass_rate': bool(also_active_only),
                          'gate_values': {'spearman_min': HOLDOUT_SPEARMAN_MIN,
                                          'jaccard_min': HOLDOUT_JACCARD_MIN,
                                          'penalty_mean_tol': HOLDOUT_PENALTY_MEAN_TOL,
                                          'oos_max': OOS_MAX}})

# (methods continue the Verifier class below)
    # ------------------------------------------------------- V06/V07 bootstrap
    def check_bootstrap(self):
        seeds = read_rows(self.freeze_dir / 'bootstrap_seed_manifest.csv')
        details = read_rows(self.freeze_dir / 'bootstrap_stability_detail.csv')
        summaries = {row['domain']: row for row in
                     read_rows(self.freeze_dir / 'bootstrap_stability_summary.csv')}
        seed_mismatch = [{'domain': row['domain'], 'replicate': row['replicate']}
                         for row in seeds
                         if int(row['seed']) != bootstrap_subseed(row['domain'],
                                                                  int(row['replicate']))]
        seed_index = {(row['domain'], int(row['replicate'])): int(row['seed']) for row in seeds}
        detail_index = {}
        for row in details:
            detail_index.setdefault(row['domain'], {})[int(row['replicate'])] = row
        calib = self.calibration_valid()
        mismatches = []
        report = {}
        degenerate_report = {}
        for label in self.active:
            reference = calib[calib['domain'].astype(str) == label]
            keys = reference['key_sha256'].astype(str).to_numpy()
            x2 = reference['rps_doc_frac_chars_top_2gram'].to_numpy(dtype=float)
            x3 = reference['rps_doc_frac_chars_top_3gram'].to_numpy(dtype=float)
            q = reference['Q_baseline'].to_numpy(dtype=float)
            n = len(reference)
            entry = self.thresholds[label]
            p_reference = (penalty(x2, entry['a2'], entry['b2'])
                           + penalty(x3, entry['a3'], entry['b3'])) / 2.0
            qc_reference = q * (1.0 - LAMBDA_PRIMARY * p_reference)
            ranks_reference, order_reference = rank_positions(qc_reference, keys)
            top_reference, _ = top_keys(order_reference, n)
            joint = 0
            degenerates = 0
            recorded_rows = 0
            for replicate in range(BOOTSTRAP_REPLICATES):
                seed = seed_index.get((label, replicate))
                if seed is None:
                    mismatches.append({'domain': label, 'replicate': replicate,
                                       'reason': 'seed manifest row missing'})
                    continue
                rng = np.random.default_rng(seed)
                index = rng.integers(0, n, size=n)
                a2 = float(np.quantile(x2[index], 0.95, method='linear'))
                b2 = float(np.quantile(x2[index], 0.99, method='linear'))
                a3 = float(np.quantile(x3[index], 0.95, method='linear'))
                b3 = float(np.quantile(x3[index], 0.99, method='linear'))
                recorded = detail_index.get(label, {}).get(replicate)
                if recorded is not None:
                    recorded_rows += 1
                if b2 <= a2 or b3 <= a3:
                    degenerates += 1
                    if recorded is not None:
                        if (int(recorded['joint_pass']) != 0 or int(recorded['pass_mae']) != 0
                                or int(recorded['pass_spearman']) != 0
                                or int(recorded['pass_jaccard']) != 0
                                or recorded['reason'] != 'degenerate_quantile'):
                            mismatches.append({'domain': label, 'replicate': replicate,
                                               'reason': 'degenerate replicate not counted as a '
                                                         'joint failure'})
                    continue
                p_bootstrap = (penalty(x2, a2, b2) + penalty(x3, a3, b3)) / 2.0
                qc_bootstrap = q * (1.0 - LAMBDA_PRIMARY * p_bootstrap)
                mae = float(np.mean(np.abs(p_bootstrap - p_reference)))
                ranks_bootstrap, order_bootstrap = rank_positions(qc_bootstrap, keys)
                rho = spearman_rank_difference(ranks_reference, ranks_bootstrap)
                top_bootstrap, _ = top_keys(order_bootstrap, n)
                jac = jaccard(top_reference, top_bootstrap)
                passed = bool(mae <= BOOT_MAE_MAX and rho >= BOOT_SPEARMAN_MIN
                              and jac >= BOOT_JACCARD_MIN)
                joint += int(passed)
                if recorded is not None:
                    comparisons = {'a2': close(recorded['a2'], a2), 'b2': close(recorded['b2'], b2),
                                   'a3': close(recorded['a3'], a3), 'b3': close(recorded['b3'], b3),
                                   'penalty_mae': close(recorded['penalty_mae'], mae),
                                   'rank_spearman': close(recorded['rank_spearman'], rho, 1e-9),
                                   'top10_jaccard': close(recorded['top10_jaccard'], jac),
                                   'joint_pass': int(recorded['joint_pass']) == int(passed)}
                    failed = [key for key, ok in comparisons.items() if not ok]
                    if failed:
                        mismatches.append({'domain': label, 'replicate': replicate,
                                           'failed': failed,
                                           'recorded_mae': recorded['penalty_mae'],
                                           'recomputed_mae': mae})
            summary = summaries.get(label)
            if summary is None:
                mismatches.append({'domain': label, 'reason': 'summary row missing'})
            else:
                if int(summary['joint_pass_count']) != joint:
                    mismatches.append({'domain': label, 'field': 'joint_pass_count',
                                       'recorded': int(summary['joint_pass_count']),
                                       'recomputed': joint})
                if int(summary['n']) != n:
                    mismatches.append({'domain': label, 'field': 'n', 'recorded': int(summary['n']),
                                       'recomputed': n})
                expected_status = 'PASS' if joint >= BOOTSTRAP_MIN_PASS else 'FAIL'
                if summary['status'] != expected_status:
                    mismatches.append({'domain': label, 'field': 'status',
                                       'recorded': summary['status'],
                                       'recomputed': expected_status})
            if recorded_rows != BOOTSTRAP_REPLICATES:
                mismatches.append({'domain': label, 'reason': 'detail rows incomplete',
                                   'recorded_rows': recorded_rows})
            report[label] = {'n': n, 'joint_pass_recomputed': joint,
                             'joint_pass_recorded': (int(summary['joint_pass_count'])
                                                     if summary else None),
                             'required': BOOTSTRAP_MIN_PASS, 'degenerate_replicates': degenerates}
            degenerate_report[label] = degenerates
        self.bootstrap_cache = {'report': report, 'degenerate': degenerate_report,
                                'mismatches': mismatches, 'seed_mismatch': seed_mismatch,
                                'detail_rows': len(details), 'seed_rows': len(seeds)}
        status = 'PASS' if (not mismatches and not seed_mismatch
                            and len(seed_index) == len(self.active) * BOOTSTRAP_REPLICATES) else 'FAIL'
        self.add('V06', 'bootstrap stability recomputed from the frozen seeds and the fixed '
                 'calibration reference rows', status,
                 {'per_domain': report, 'mismatches': mismatches[:20],
                  'mismatch_count': len(mismatches), 'seed_mismatches': len(seed_mismatch),
                  'seed_rule': 'int(sha256("20260925|<domain>|<replicate>")[:16],16) -> PCG64',
                  'reference_rows': 'same full-calibration valid rows for every replicate',
                  'joint_rule': 'all three criteria must hold in the same replicate',
                  'gates': {'mae_max': BOOT_MAE_MAX, 'spearman_min': BOOT_SPEARMAN_MIN,
                            'jaccard_min': BOOT_JACCARD_MIN}})

    def check_degenerate_replicates(self):
        cache = self.bootstrap_cache
        details = read_rows(self.freeze_dir / 'bootstrap_stability_detail.csv')
        recorded_degenerate = [row for row in details if row.get('reason') == 'degenerate_quantile']
        bad = [row for row in recorded_degenerate if int(row['joint_pass']) != 0]
        recomputed_total = sum(cache['degenerate'].values())
        status = 'PASS' if not bad and len(recorded_degenerate) == recomputed_total else 'FAIL'
        self.add('V07', 'a replicate with q0.99 <= q0.95 is counted as a joint failure, never as a '
                 'pass and never with a temporary quantile', status,
                 {'recorded_degenerate_replicates': len(recorded_degenerate),
                  'recomputed_degenerate_replicates': recomputed_total,
                  'per_domain': cache['degenerate'],
                  'degenerate_rows_recorded_as_failure': len(recorded_degenerate) - len(bad),
                  'violations': len(bad)})

    # ------------------------------------------------------------- V08 fixtures
    def check_fixtures_and_bounds(self):
        fixture_failures = []
        def expect(name, actual, expected, tolerance=0.0):
            if not close(actual, expected, tolerance):
                fixture_failures.append({'name': name, 'actual': actual, 'expected': expected})
        expect('penalty_at_lower', penalty(np.array([1.0]), 1.0, 2.0)[0], 0.0)
        expect('penalty_midpoint', penalty(np.array([1.5]), 1.0, 2.0)[0], 0.5)
        expect('penalty_at_upper', penalty(np.array([2.0]), 1.0, 2.0)[0], 1.0)
        expect('penalty_above_upper', penalty(np.array([7.0]), 1.0, 2.0)[0], 1.0)
        grid = np.linspace(0.0, 3.0, 121)
        penalties = penalty(grid, 1.0, 2.0)
        expect('fixture_penalty_monotone', bool(np.all(np.diff(penalties) >= 0.0)), True)
        expect('fixture_penalty_range', bool(np.all((penalties >= 0.0) & (penalties <= 1.0))), True)
        cluster = (penalty(np.array([1.5]), 1.0, 2.0)[0] + penalty(np.array([3.5]), 3.0, 4.0)[0]) / 2
        expect('fixture_cluster_mean', cluster, 0.5)
        expect('fixture_duplicate_row_same_penalty',
               penalty(np.array([1.5, 1.5]), 1.0, 2.0)[0],
               penalty(np.array([1.5]), 1.0, 2.0)[0])
        expect('fixture_cluster_two_members_only',
               float(np.mean([penalty(np.array([1.5]), 1.0, 2.0)[0],
                              penalty(np.array([3.5]), 3.0, 4.0)[0]])), cluster)
        q = np.array([0.8, 0.8, 0.0, 1.0])
        p = np.array([0.5, 1.0, 1.0, 0.0])
        candidate = q * (1.0 - LAMBDA_PRIMARY * p)
        expect('fixture_candidate_le_D', bool(np.all(candidate <= q)), True)
        expect('fixture_candidate_ge_098D', bool(np.all(candidate >= 0.98 * q)), True)
        expect('fixture_lambda_zero_identity',
               float(np.max(np.abs(q * (1.0 - 0.0 * p) - q))), 0.0, 1e-15)
        expect('fixture_no_new_zero', int(np.sum((q > 0) & (candidate == 0))), 0)
        expect('fixture_original_zero_preserved', float(candidate[2]), 0.0)
        expect('fixture_hand_value', float(q[0] * (1.0 - 0.02 * 0.5)), 0.792, 1e-15)
        tests = read_json(self.freeze_dir / 'artificial_tests.json')
        recorded_failures = [item['test'] for item in tests['tests'] if item['status'] != 'PASS']
        expected_values = {'penalty_midpoint_top2': 0.5, 'penalty_midpoint_top3': 0.5,
                           'cluster_penalty_mean': 0.5, 'penalty_lower_bound': 0.0,
                           'penalty_upper_bound': 1.0, 'lambda_zero_identity': 0.8,
                           'new_zero_values': 0, 'candidate_ge_098q': 0.98,
                           'duplicate_member_no_weight_increase': 0.5,
                           'candidate_formula': 0.8 * (1 - 0.02 * 0.5)}
        spot_errors = []
        for item in tests['tests']:
            if item['test'] in expected_values:
                if not close(item['actual'], expected_values[item['test']], 1e-12):
                    spot_errors.append({'test': item['test'], 'actual': item['actual'],
                                        'independent_expectation': expected_values[item['test']]})
        status = 'PASS' if (not fixture_failures and not recorded_failures and not spot_errors
                            and tests['status'] == 'PASS') else 'FAIL'
        self.add('V08', 'redundancy-cluster, boundary and monotonicity fixtures recomputed '
                 'independently', status,
                 {'independent_fixture_failures': fixture_failures,
                  'executor_artificial_tests': {'n_tests': tests['n_tests'],
                                                'n_failed': tests['n_failed'],
                                                'failed_names': recorded_failures},
                  'spot_check_errors': spot_errors,
                  'cluster_rule': 'P = (p_top2gram + p_top3gram)/2, duplicating a member must not '
                                  'change P or Q_C'})

    # ------------------------------------------------ V09 non-applied domains
    def check_non_applied_domains(self):
        status_column = self.scores['Q_support_status'].astype(str).to_numpy()
        q_d = self.scores['Q_baseline'].to_numpy(dtype=float)
        q_c = self.scores['Q_C'].to_numpy(dtype=float)
        domains = self.scores['domain'].astype(str).to_numpy()
        names = sorted(set(domains[status_column == 'RULE_NOT_APPLICABLE'].tolist()))
        mask = status_column == 'RULE_NOT_APPLICABLE'
        finite = mask & np.isfinite(q_d) & np.isfinite(q_c)
        max_delta = float(np.max(np.abs(q_c[finite] - q_d[finite]))) if finite.any() else 0.0
        non_finite_rows = int(np.sum(mask & ~(np.isfinite(q_d) & np.isfinite(q_c))))
        application = read_rows(self.freeze_dir / 'frozen_active_domains.csv')
        excluded = [row for row in application if row['status'] != 'ACTIVE']
        holdout_domains = {row['domain'] for row in
                           read_rows(self.phase_b_dir / 'holdout_validation.csv')}
        extension_domains = {row['domain'] for row in
                             read_rows(self.phase_b_dir / 'extension_new_validation.csv')}
        leaked = sorted((holdout_domains | extension_domains) - set(self.active))
        status = 'PASS' if (max_delta == 0.0 and not leaked) else 'FAIL'
        self.add('V09', 'non-applied domains keep Q_C == D exactly and never enter the active '
                 'correction evidence', status,
                 {'rule_not_applicable_domains': names,
                  'rule_not_applicable_rows': int(mask.sum()),
                  'max_abs_delta': max_delta, 'non_finite_rows_excluded': non_finite_rows,
                  'excluded_design_domains': [(row['design_label'], row['status'])
                                              for row in excluded],
                  'domains_in_holdout_or_extension_pass_rate': sorted(holdout_domains
                                                                      | extension_domains),
                  'active_domains': self.active, 'leaked_into_evidence': leaked})

    # ------------------------------------------------------------- V10 extension
    def check_extension(self):
        extension = self.input[self.input['evaluation_role'].astype(str).isin(
            ['extension_overlap_A1', 'extension_new_records'])]
        a1 = self.input[self.input['evaluation_role'].astype(str).isin(
            ['A1_calibration', 'A1_holdout'])]
        extension_candidate = self.recompute_candidate(extension)
        a1_candidate = self.recompute_candidate(a1)
        extension_frame = extension.assign(Q_C=extension_candidate['Q_C'],
                                          P=extension_candidate['P'],
                                          status=extension_candidate['status'])
        a1_frame = a1.assign(Q_C=a1_candidate['Q_C'], P=a1_candidate['P'],
                             status=a1_candidate['status'])
        a1_index = {str(row.key_sha256): row for row in a1_frame.itertuples(index=False)}
        recorded_overlap = {row['key_sha256']: row for row in
                            read_rows(self.phase_b_dir / 'extension_overlap_validation.csv')}
        mismatches = []
        reproduced = 0
        violations = 0
        same_value = lambda left, right: (math.isnan(float(left)) and math.isnan(float(right))) \
            or float(left) == float(right)
        for row in extension_frame[extension_frame['evaluation_role'].astype(str)
                                   == 'extension_overlap_A1'].itertuples(index=False):
            reference = a1_index.get(str(row.key_sha256))
            recorded = recorded_overlap.get(str(row.key_sha256))
            if recorded is None:
                mismatches.append({'key': row.key_sha256, 'reason': 'missing in output'})
                continue
            if reference is None:
                expected = 'A1_SIDE_MISSING'
            elif str(reference.domain) != str(row.domain):
                expected = 'DOMAIN_MISMATCH'
            elif not (same_value(reference.Q_baseline, row.Q_baseline)
                      and same_value(reference.rps_doc_frac_chars_top_2gram,
                                     row.rps_doc_frac_chars_top_2gram)
                      and same_value(reference.rps_doc_frac_chars_top_3gram,
                                     row.rps_doc_frac_chars_top_3gram)):
                expected = 'INPUT_DIFFERS'
            elif math.isnan(float(reference.Q_C)) or math.isnan(float(row.Q_C)):
                expected = 'Q_INVALID_PRESERVED'
            else:
                delta = abs(float(reference.Q_C) - float(row.Q_C))
                if delta <= OVERLAP_TOL:
                    expected = 'REPRODUCED'
                    reproduced += 1
                else:
                    expected = 'REPRODUCTION_MISMATCH'
                    violations += 1
            if recorded['status'] != expected:
                mismatches.append({'key': row.key_sha256, 'recorded': recorded['status'],
                                   'recomputed': expected})
        recorded_new = {row['domain']: row for row in
                        read_rows(self.phase_b_dir / 'extension_new_validation.csv')}
        expected_new = {}
        for label in self.active:
            part = extension_frame[(extension_frame['evaluation_role'].astype(str)
                                    == 'extension_new_records')
                                   & (extension_frame['domain'].astype(str) == label)
                                   & valid_mask(extension_frame)]
            row = recorded_new.get(label)
            if row is None:
                mismatches.append({'domain': label, 'reason': 'missing extension row'})
                continue
            n = len(part)
            if n == 0:
                expected_status = 'NOT_PRESENT_IN_EXTENSION'
                expected_new[label] = {'n_valid': 0, 'status': expected_status}
                if row['status'] != expected_status or int(row['n_valid']) != 0:
                    mismatches.append({'domain': label, 'recorded': row['status'],
                                       'recomputed': expected_status})
                continue
            keys = part['key_sha256'].astype(str).to_numpy()
            ranks_d, order_d = rank_positions(part['Q_baseline'].to_numpy(dtype=float), keys)
            ranks_c, order_c = rank_positions(part['Q_C'].to_numpy(dtype=float), keys)
            rho = spearman_rank_difference(ranks_d, ranks_c)
            jac = jaccard(top_keys(order_d, n)[0], top_keys(order_c, n)[0])
            oos = float(np.mean(part['status'].to_numpy() == 'OUT_OF_SUPPORT'))
            if n < EXTENSION_MIN_N:
                expected_status = 'INSUFFICIENT_EXTENSION_EVIDENCE'
            elif rho >= HOLDOUT_SPEARMAN_MIN and jac >= HOLDOUT_JACCARD_MIN and oos <= OOS_MAX:
                expected_status = 'MIGRATION_OK'
            else:
                expected_status = 'MIGRATION_FAILED_KEEP_D'
            expected_new[label] = {'n_valid': n, 'spearman': rho, 'jaccard': jac,
                                   'oos_fraction': oos, 'status': expected_status,
                                   'top_k': top_keys(order_d, n)[1]}
            if row['status'] != expected_status:
                mismatches.append({'domain': label, 'recorded': row['status'],
                                   'recomputed': expected_status})
            for field, value in (('n_valid', n), ('spearman_C_D', rho),
                                 ('top10_jaccard_C_D', jac), ('oos_fraction', oos)):
                if not close(row[field], value):
                    mismatches.append({'domain': label, 'field': field, 'recorded': row[field],
                                       'recomputed': value})
        statuses = [item['status'] for item in expected_new.values()]
        if any(item == 'MIGRATION_FAILED_KEEP_D' for item in statuses):
            expected_extension = 'MIGRATION_FAILED_KEEP_D'
        elif any(item == 'MIGRATION_OK' for item in statuses) and any(
                item == 'INSUFFICIENT_EXTENSION_EVIDENCE' for item in statuses):
            expected_extension = 'INSUFFICIENT_EXTENSION_EVIDENCE'
        elif any(item == 'MIGRATION_OK' for item in statuses):
            expected_extension = 'MIGRATION_OK'
        elif any(item == 'INSUFFICIENT_EXTENSION_EVIDENCE' for item in statuses):
            expected_extension = 'INSUFFICIENT_EXTENSION_EVIDENCE'
        else:
            expected_extension = 'NOT_TESTED_FOR_ACTIVE_CORRECTION'
        summary = read_json(self.phase_b_dir / 'extension_summary.json')
        summary_ok = (summary['extension_status'] == expected_extension
                      and int(summary['overlap_reproduced']) == reproduced
                      and int(summary['overlap_mismatches']) == violations)
        status = 'PASS' if (not mismatches and summary_ok) else 'FAIL'
        self.add('V10', 'extension overlap reproduction and new-record transport status recomputed',
                 status, {'per_domain_new': expected_new, 'mismatches': mismatches[:20],
                          'mismatch_count': len(mismatches),
                          'recorded_extension_status': summary['extension_status'],
                          'recomputed_extension_status': expected_extension,
                          'overlap_reproduced_recomputed': reproduced,
                          'overlap_mismatches_recomputed': violations,
                          'overlap_rule': 'same frozen key + same domain + identical '
                                          'Q_baseline/top2/top3 => |dQ_C| <= 1e-12'})

    # ---------------------------------------- V11 frozen artefacts unchanged
    def check_frozen_artifacts(self):
        seal_ok = sha256_file(self.freeze_dir / 'freeze_manifest.json') \
            == self.seal['freeze_manifest_sha256']
        changed = []
        for item in self.frozen_manifest['frozen_files']:
            path = self.run_dir / item['path']
            if not path.is_file():
                changed.append({'path': item['path'], 'reason': 'missing'})
            elif sha256_file(path) != item['sha256'] or int(path.stat().st_size) != int(item['bytes']):
                changed.append({'path': item['path'], 'reason': 'hash_or_size_changed'})
        config_path = self.run_dir / self.frozen_manifest.get('config_file', 'run_config.json')
        config_ok = config_path.is_file() and sha256_file(config_path) \
            == self.frozen_manifest.get('config_sha256')
        frozen_thresholds = read_rows(self.freeze_dir / 'frozen_thresholds.csv')
        threshold_ok = True
        for row in frozen_thresholds:
            entry = self.thresholds[row['domain']]
            keys = ({'a_q95': 'a2', 'b_q99': 'b2', 'lo_q005': 'lo2', 'hi_q995': 'hi2'}
                    if row['indicator'] == 'top_2gram'
                    else {'a_q95': 'a3', 'b_q99': 'b3', 'lo_q005': 'lo3', 'hi_q995': 'hi3'})
            for source, target in keys.items():
                if not close(row[source], entry[target]):
                    threshold_ok = False
        seal_thresholds_ok = all(close(self.seal['thresholds'][label][key],
                                       self.frozen_manifest['thresholds'][label][key])
                                 for label in self.active
                                 for key in self.frozen_manifest['thresholds'][label])
        status = 'PASS' if (seal_ok and not changed and config_ok and threshold_ok
                            and seal_thresholds_ok) else 'FAIL'
        self.add('V11', 'freeze seal hashes the manifest and every pre-seal artefact keeps its '
                 'sealed hash', status,
                 {'seal_manifest_hash_matches': bool(seal_ok),
                  'frozen_files_checked': len(self.frozen_manifest['frozen_files']),
                  'changed_files': changed, 'run_config_hash_matches': bool(config_ok),
                  'thresholds_consistent_with_frozen_csv_and_seal': bool(threshold_ok
                                                                         and seal_thresholds_ok)})

    # ------------------------------------- V12 no post-read parameter rewrite
    def check_no_post_read_rewrite(self):
        snapshot_dir = self.freeze_dir / 'code_snapshot'
        snapshot_manifest = read_json(snapshot_dir / 'code_snapshot_manifest.json')
        current = {'t03e_preregistered_rule_sensitivity.py':
                   self.frozen_manifest['source_code_sha256'].get(
                       't03e_preregistered_rule_sensitivity.py')}
        drift = []
        for entry in snapshot_manifest['files']:
            path = snapshot_dir / entry['file']
            if not path.is_file():
                drift.append({'file': entry['file'], 'reason': 'snapshot missing'})
                continue
            if sha256_file(path) != entry['sha256']:
                drift.append({'file': entry['file'], 'reason': 'snapshot hash changed'})
            live = SOLUTION / 'src' / entry['file']
            if live.is_file() and entry['file'].endswith('.py'):
                if sha256_file(live) != entry['sha256']:
                    drift.append({'file': entry['file'],
                                  'reason': 'live source differs from the sealed snapshot'})
        acceptance = read_json(self.freeze_dir / 'preregistered_acceptance.json')
        freeze_manifest_acceptance = self.frozen_manifest['acceptance_thresholds']
        acceptance_ok = json.dumps(acceptance, sort_keys=True) \
            == json.dumps(freeze_manifest_acceptance, sort_keys=True)
        version_ok = ({'candidate_version': 't03e_candidate_v1'} ==
                      {'candidate_version': self.scores['candidate_version'].astype(str).unique()
                       .tolist()[0] if len(self.scores['candidate_version'].astype(str).unique()) == 1
                       else None})
        lambda_ok = bool((self.scores['lambda_primary'].to_numpy(dtype=float)
                          == LAMBDA_PRIMARY).all())
        status = 'PASS' if (not drift and acceptance_ok and version_ok and lambda_ok) else 'FAIL'
        self.add('V12', 'no parameter, code, configuration or threshold was rewritten after the '
                 'holdout was read', status,
                 {'sealed_code_snapshot_drift': drift,
                  'acceptance_payload_identical_to_manifest': bool(acceptance_ok),
                  'single_candidate_version': bool(version_ok), 'lambda_primary_rows': bool(lambda_ok),
                  'sealed_config_sha256':
                      self.frozen_manifest.get('config_sha256'),
                  'seal_time': self.seal['sealed_local']})

    # -------------------------------------------- V13 protected baseline intact
    def check_protected_baseline(self):
        input_manifest = read_json(Q01C_RUN / 'output_manifest.json')
        entry = next(item for item in input_manifest['files']
                     if item['path'].endswith('quality_features_scores.parquet'))
        current_hash = sha256_file(INPUT_PATH)
        recorded = self.scores
        comparisons = {}
        comparisons['key_sha256'] = bool(np.array_equal(
            recorded['key_sha256'].astype(str).to_numpy(),
            self.input['key_sha256'].astype(str).to_numpy()))
        comparisons['file_id'] = bool(np.array_equal(recorded['file_id'].astype(str).to_numpy(),
                                                    self.input['file_id'].astype(str).to_numpy()))
        comparisons['source_line'] = bool(np.array_equal(recorded['source_line'].astype(str).to_numpy(),
                                                        self.input['source_line'].astype(str).to_numpy()))
        comparisons['Q_valid'] = bool(np.array_equal(recorded['Q_valid'].to_numpy() == True,
                                                    self.input['Q_valid'].to_numpy() == True))
        comparisons['Q_baseline'] = bool(np.array_equal(recorded['Q_baseline'].to_numpy(dtype=float),
                                                       self.input['Q_baseline'].to_numpy(dtype=float),
                                                       equal_nan=True))
        invalid = self.input['Q_valid'].to_numpy() == False
        invalid_c_nan = bool(np.isnan(recorded['Q_C'].to_numpy(dtype=float)[invalid]).all())
        invalid_status = bool((recorded['Q_support_status'].astype(str).to_numpy()[invalid]
                               == 'Q_INVALID_PRESERVED').all())
        protected_json = read_json(self.run_dir / 'protected_baseline_check.json')
        status = 'PASS' if (all(comparisons.values()) and invalid_c_nan and invalid_status
                            and current_hash == entry['sha256']
                            and current_hash == self.frozen_manifest['source_sha256']
                            and protected_json['status'] == 'PASS') else 'FAIL'
        self.add('V13', 'Q_baseline, Q_valid, identity keys and the official input hash are '
                 'unchanged', status,
                 {'comparisons': comparisons, 'input_sha256_now': current_hash,
                  'input_sha256_expected': entry['sha256'],
                  'Q_valid_false_rows': int(invalid.sum()),
                  'Q_valid_false_rows_with_nan_Q_C': invalid_c_nan,
                  'Q_valid_false_rows_with_Q_INVALID_PRESERVED': invalid_status,
                  'protected_baseline_check_json_status': protected_json['status']})

    # -------------------------------------- V14 RegMix no new fit
    def check_regmix_no_fit(self):
        payload = read_json(self.phase_b_dir / 'regmix_loss_identifiability.json')
        manifest = read_json(self.run_dir / 'input_manifest.json')
        drift = []
        for entry in manifest.get('entries', []):
            digest = str(entry.get('sha256', ''))
            if is_hex_sha256(digest):
                path = Path(entry['path'])
                if path.is_file() and sha256_file(path) != digest:
                    drift.append(entry['path'])
        reasons = payload.get('structural_reasons') or []
        status = 'PASS' if (payload.get('regression_or_bridge_fitting_performed') is False
                            and payload.get('new_models_or_scalers_fitted') is False
                            and payload.get('status') in ('NOT_IDENTIFIABLE', 'IDENTIFIABLE')
                            and reasons and not drift) else 'FAIL'
        self.add('V14', 'RegMix/Loss connection checked without any new fit and without rewriting '
                 'the read-only evidence', status,
                 {'status_value': payload.get('status'), 'structural_reasons': reasons,
                  'regression_or_bridge_fitting_performed':
                      payload.get('regression_or_bridge_fitting_performed'),
                  'read_only_input_hash_drift': drift,
                  'checked_inputs': payload.get('checked_inputs')},
                 'NOT_IDENTIFIABLE is a method conclusion and must not be rewritten as a pass')

    # --------------------------------------------- V15 coverage denominators
    def check_coverage_fields(self):
        role = self.input['evaluation_role'].astype(str).to_numpy()
        domain = self.input['domain'].astype(str).to_numpy()
        recomputed = {}
        for key in sorted(set(zip(role.tolist(), domain.tolist()))):
            mask = (role == key[0]) & (domain == key[1])
            recomputed[key] = counts_for(self.input[mask])
        recorded = {(row['role'], row['domain']): row for row in
                    read_rows(self.phase_b_dir / 'domain_role_inventory.csv')}
        mismatches = []
        for key, value in recomputed.items():
            row = recorded.get(key)
            if row is None:
                mismatches.append({'key': list(key), 'reason': 'missing_from_inventory'})
                continue
            for field in ('n_total', 'n_unique_first', 'n_Q_valid', 'n_Q_missing', 'n_analysis_valid'):
                if int(row[field]) != int(value[field]):
                    mismatches.append({'key': list(key), 'field': field,
                                       'recorded': int(row[field]),
                                       'recomputed': int(value[field])})
            if not close(row['analysis_coverage'], value['analysis_coverage']):
                mismatches.append({'key': list(key), 'field': 'analysis_coverage',
                                   'recorded': row['analysis_coverage'],
                                   'recomputed': value['analysis_coverage']})
        row_level_bad = 0
        n_total = self.scores['domain_role_n_total'].to_numpy()
        n_valid = self.scores['domain_role_n_analysis_valid'].to_numpy()
        for i in range(len(self.scores)):
            entry = recomputed.get((role[i], domain[i]))
            if entry is None or int(n_total[i]) != int(entry['n_total']) \
                    or int(n_valid[i]) != int(entry['n_analysis_valid']):
                row_level_bad += 1
        interface = read_json(self.run_dir / 't06_quality_interface.json')
        interface_rows = {(row['role'], row['domain']): row
                          for row in interface.get('coverage_by_role_domain', [])}
        interface_bad = [list(key) for key, value in recomputed.items()
                         if key not in interface_rows
                         or int(interface_rows[key]['n_total']) != int(value['n_total'])
                         or int(interface_rows[key]['n_analysis_valid']) != int(value['n_analysis_valid'])]
        status = 'PASS' if (not mismatches and row_level_bad == 0 and not interface_bad) else 'FAIL'
        self.add('V15', 'n_total/n_Q_valid/n_analysis_valid/coverage agree between the row-level '
                 'scores, the role x domain inventory and the T06 interface', status,
                 {'role_domain_groups': len(recomputed), 'mismatches': mismatches,
                  'row_level_denominator_mismatch_rows': row_level_bad,
                  't06_interface_mismatches': interface_bad})

    # -------------------------------------------------------- V16 manifest
    def check_manifest(self):
        path = self.run_dir / 'output_manifest.json'
        if not path.is_file():
            self.manifest_expected = {'present': False}
            self.add('V16', 'output manifest completeness and stability', 'NOT_VERIFIABLE',
                     {'reason': 'output_manifest.json has not been generated yet'})
            return
        manifest = read_json(path)
        registered = {item['path']: item for item in manifest['files']}
        all_files = set()
        for candidate in sorted(self.run_dir.rglob('*')):
            if candidate.is_file():
                all_files.add(str(candidate.relative_to(self.run_dir)).replace('\\', '/'))
        expected = all_files - {'output_manifest.json', 'verification.json'}
        missing = sorted(expected - set(registered))
        unexpected = sorted(set(registered) - expected)
        hash_mismatch = []
        for rel, item in registered.items():
            candidate = self.run_dir / rel
            if not candidate.is_file():
                hash_mismatch.append({'path': rel, 'reason': 'registered file missing'})
            elif sha256_file(candidate) != item['sha256'] \
                    or int(candidate.stat().st_size) != int(item['bytes']):
                hash_mismatch.append({'path': rel, 'reason': 'hash or size changed'})
        self.manifest_expected = {
            'present': True, 'generated_local': manifest.get('generated_local'),
            'registered_files': len(registered),
            'files': [{'path': rel, 'sha256': item['sha256'], 'bytes': item['bytes']}
                      for rel, item in sorted(registered.items())],
            'generated_after_verification': 'finalizer regenerates the manifest once '
                                            'verification.json exists and records '
                                            'previous_manifest_stable_excluding_append_only'}
        status = 'PASS' if (not missing and not unexpected and not hash_mismatch) else 'FAIL'
        self.add('V16', 'output manifest lists every artefact except itself with matching hashes',
                 status, {'registered_files': len(registered), 'missing_from_manifest': missing,
                          'unexpected_in_manifest': unexpected,
                          'hash_or_size_mismatches': hash_mismatch,
                          'append_only_files': manifest.get('append_only_files'),
                          'verification_json_written_after_manifest': True})

    # ------------------------------------------- V17 executor checks summary
    def check_executor_checks(self):
        payload = read_json(self.run_dir / 'checks.json')
        checks = payload['checks']
        failures = [item['id'] for item in checks if item['status'] == 'FAIL']
        deferred = [item['id'] for item in checks if item['status'] == 'NOT_CHECKED']
        status = 'PASS' if (not failures and len(checks) >= 20) else 'FAIL'
        self.add('V17', 'executor checks.json contains no critical FAIL and covers the frozen '
                 'check list', status,
                 {'check_count': len(checks), 'failed_ids': failures,
                  'not_checked_ids': deferred, 'counts': payload.get('counts')})


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='TASK-T03E independent verifier')
    parser.add_argument('--run-dir', required=True)
    return parser.parse_args(argv)


def main(argv=None):
    import traceback
    args = parse_args(argv)
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print('run directory does not exist: ' + str(run_dir), file=sys.stderr)
        return 2
    verifier = Verifier(run_dir)
    started = now_iso()
    order = [('V01', verifier.check_domain_labels),
             ('V02', verifier.check_freeze_before_reads),
             ('V03', verifier.check_calibration_quantiles),
             ('V04', verifier.check_row_level_candidate),
             ('V05', verifier.check_holdout_gates),
             ('V06', verifier.check_bootstrap),
             ('V07', verifier.check_degenerate_replicates),
             ('V08', verifier.check_fixtures_and_bounds),
             ('V09', verifier.check_non_applied_domains),
             ('V10', verifier.check_extension),
             ('V11', verifier.check_frozen_artifacts),
             ('V12', verifier.check_no_post_read_rewrite),
             ('V13', verifier.check_protected_baseline),
             ('V14', verifier.check_regmix_no_fit),
             ('V15', verifier.check_coverage_fields),
             ('V16', verifier.check_manifest),
             ('V17', verifier.check_executor_checks)]
    verifier.manifest_expected = {'present': False}
    verifier.bootstrap_cache = {'report': {}, 'degenerate': {}, 'mismatches': [],
                                'seed_mismatch': [], 'detail_rows': 0, 'seed_rows': 0}
    try:
        verifier.load()
        loaded = True
        load_error = None
    except Exception as exc:
        loaded = False
        load_error = type(exc).__name__ + ': ' + str(exc)
        traceback.print_exc()
    if loaded:
        for identifier, function in order:
            try:
                function()
            except Exception as exc:
                traceback.print_exc()
                verifier.add(identifier, function.__name__, 'NOT_VERIFIABLE',
                             {'error': type(exc).__name__ + ': ' + str(exc)},
                             'the verifier raised while recomputing this item')
    else:
        for identifier, function in order:
            verifier.add(identifier, function.__name__, 'NOT_VERIFIABLE',
                         {'error': 'verifier could not load the run artefacts: ' + str(load_error)})
    deduplicated = {}
    rank = {'FAIL': 0, 'NOT_VERIFIABLE': 1, 'PASS': 2}
    for item in verifier.results:
        existing = deduplicated.get(item['id'])
        if existing is None or rank[item['status']] < rank[existing['status']]:
            deduplicated[item['id']] = item
    results = [deduplicated[key] for key in sorted(deduplicated)]
    counts = {}
    for item in results:
        counts[item['status']] = counts.get(item['status'], 0) + 1
    if counts.get('FAIL'):
        overall = 'FAIL'
    elif counts.get('NOT_VERIFIABLE'):
        overall = 'NOT_VERIFIABLE'
    else:
        overall = 'PASS'
    payload = {'task': 'TASK-T03E', 'artifact': 'verification.json',
               'verifier': 't03e_verify.py (independent re-implementation; the executor module is '
                           'never imported)',
               'run_id': run_dir.name, 'run_dir': str(run_dir),
               'input_path': str(INPUT_PATH), 'input_sha256_now': sha256_file(INPUT_PATH),
               'started_local': started, 'finished_local': now_iso(),
               'status': overall, 'counts': counts, 'checks': results,
               'manifest_expected': getattr(verifier, 'manifest_expected', {'present': False}),
               'statement': ('D = Q_baseline is the official main result; Q_C is only a '
                             'preregistered rule-sensitivity candidate'),
               'ordering_note': ('verification.json is written after checks.json/run_summary/handoff '
                                 'and after the first output_manifest.json; the finalizer then '
                                 'regenerates output_manifest.json so that it also covers this file '
                                 'and records previous_manifest_stable_excluding_append_only')}
    verification_path = run_dir / 'verification.json'
    with open(verification_path, 'w', encoding='utf-8') as handle:
        json.dump(sanitise(payload), handle, ensure_ascii=False, indent=2, default=str,
                  allow_nan=False)
    print('verification status: ' + overall + ' counts=' + json.dumps(counts))
    for item in results:
        print(item['id'] + ' ' + item['status'] + ' ' + item['name'])
    return 0 if overall == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
