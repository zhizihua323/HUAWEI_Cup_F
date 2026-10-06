"""TASK-Q01A-R1 precision repair, derived only from the saved artifacts of run R.

Hard boundaries enforced here:
  * A1-A3 compressed inputs are never opened, decompressed, read or hashed; only
    their size/mtime are recorded for the "no touch" statement.
  * the original run directory R is opened read-only and never written to;
  * no numeric Q, no group score, no range/std numeric value is computed;
  * no missing-data strategy is selected or implemented.

Repairs (per the main-controller review):
  1. raw-layer anomaly record counts + raw_invalid mask, rebuilt from the saved
     invalid_values.csv.gz raw events joined to row_masks.csv.gz by
     (file_id, source_line); element counts are kept as event counts.
  2. disagreement range/std effective denominators (defined when at least one
     group is usable) + explicit Q_std effective n and variance divisor.
  5. domain/role missing share table.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

RUN_ID = '20260924T150623+08'
RUN_DIR = Path(__file__).resolve().parent
PROJECT = RUN_DIR.parents[2]
assert RUN_DIR.parent.name == 'TASK-Q01A-R1' and RUN_DIR.parent.parent.name == 'diagnostics'
assert RUN_DIR.name == RUN_ID
R_DIR = PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T142229+08'
FAILED_DIR = PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T141414+08'
QUALITY = PROJECT / 'solution' / 'outputs' / 'quality'
SRC = PROJECT / 'solution' / 'src'
CST = timezone(timedelta(hours=8))
START_LOCAL = datetime.now(CST)
START_MONO = time.monotonic()
POPCOUNT8 = np.array([bin(i).count('1') for i in range(256)], dtype=np.int16)


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


def write_csv(path, columns, rows):
    path = Path(path)
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False,
                                     default=str), encoding='utf-8')
    return Path(path)


def bits_to_string(value, nbits):
    return ''.join('1' if (value >> j) & 1 else '0' for j in range(nbits))


def set_bits(names, index_map):
    value = 0
    for name in names:
        value |= (1 << index_map[name])
    return value


class Logger:
    def __init__(self, path):
        self.fh = open(path, 'a', encoding='utf-8', newline='\n')

    def __call__(self, message):
        line = f'[{datetime.now(CST).isoformat(timespec="milliseconds")}] {message}'
        self.fh.write(line + '\n')
        self.fh.flush()
        print(line, flush=True)

    def close(self):
        self.fh.close()


LOG = None


def log(message):
    if LOG is not None:
        LOG(message)
    else:
        print(message, flush=True)


# ---------------------------------------------------------------------------
# read-only input inventory (no compressed input is opened)
# ---------------------------------------------------------------------------
SPEC = read_json(R_DIR / 'diagnostic_spec.json')
FIELD_ORDER = [item['field'] for item in sorted(SPEC['raw_fields_22'], key=lambda x: x['index'])]
FIELD_INDEX = {name: i for i, name in enumerate(FIELD_ORDER)}
FEATURE_ORDER = [item['feature'] for item in sorted(SPEC['expanded_features_25'], key=lambda x: x['index'])]
FEATURE_INDEX = {name: i for i, name in enumerate(FEATURE_ORDER)}
MODEL_ORDER = [item['feature'] for item in sorted(SPEC['main_q_features_11'], key=lambda x: x['index'])]
GROUPS = SPEC['groups']
assert len(FIELD_ORDER) == 22 and len(FEATURE_ORDER) == 25 and len(MODEL_ORDER) == 11
assert FIELD_ORDER[0] == 'rps_doc_frac_no_alph_words'
GROUP_NAMES = ['usability', 'knowledge', 'education_reasoning']

RAW_ANOMALY_REASONS = {'absent', 'null', 'wrong_list_length', 'non_numeric_element',
                       'nan_element', 'posinf_element', 'neginf_element', 'audit_exception'}
ELEMENT_REASON_KEY = {'nan_element': 'nan_elements', 'posinf_element': 'posinf_elements',
                      'neginf_element': 'neginf_elements'}

READ_ONLY_INPUTS = [R_DIR / name for name in sorted(os.listdir(R_DIR))]
READ_ONLY_INPUTS += [FAILED_DIR / 'run.log', SRC / 'quality_audit.py', SRC / 'common.py',
                     QUALITY / 'audit.json', QUALITY / 'feature_summary.csv',
                     QUALITY / 'domain_summary.csv',
                     PROJECT / 'tasks' / 'TASK-Q01A_质量缺失模式诊断.md',
                     PROJECT / 'tasks' / 'TASK-Q01A-R1_主控审查与精准小修要求.md']
COMPRESSED_INPUTS = [
    PROJECT / 'F题' / 'real_attachments' / 'A_data_value' / 'slimpajama_quality_signal_sample.jsonl.xz',
    PROJECT / 'F题' / 'real_attachments' / 'A_data_value' / 'slimpajama_quality_extended' /
    'arxiv_part-6777d8857c6e-000486.jsonl.xz',
    PROJECT / 'F题' / 'real_attachments' / 'A_data_value' / 'slimpajama_quality_extended' /
    'github_part-6777d8857c6e-000275.jsonl.xz',
]


def parse_bits(text, nbits):
    value = 0
    if not text:
        return 0
    for j, ch in enumerate(text):
        if ch == '1':
            value |= (1 << j)
    return value


def load_events():
    """Read the saved anomaly events with the csv module (no NA coercion).

    pandas' default NA parsing would turn the literal string "nan" in the
    value_kind/reason columns into a missing value and destroy the classification
    of the 19 extraction events, so the csv module is used deliberately.
    """
    raw_events = {}
    extract_events = {}
    identity_events = {}
    element_totals = {}
    reason_totals = {}
    n_events = 0
    with gzip.open(R_DIR / 'invalid_values.csv.gz', 'rt', encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            n_events += 1
            layer = row['layer']
            name = row['field_or_feature']
            reason = row['reason']
            file_id = row['file_id']
            line = row['source_line']
            key = (file_id, line, name)
            if layer == 'raw':
                entry = raw_events.setdefault(key, {'reasons': set(), 'n_events': 0,
                                                    'nan_elements': 0, 'posinf_elements': 0,
                                                    'neginf_elements': 0, 'non_numeric_elements': 0})
                entry['reasons'].add(reason)
                entry['n_events'] += 1
                if reason == 'nan_element':
                    entry['nan_elements'] += 1
                elif reason == 'posinf_element':
                    entry['posinf_elements'] += 1
                elif reason == 'neginf_element':
                    entry['neginf_elements'] += 1
                elif reason == 'non_numeric_element':
                    entry['non_numeric_elements'] += 1
                reason_totals[(file_id, name, reason)] = reason_totals.get((file_id, name, reason), 0) + 1
                if reason in ELEMENT_REASON_KEY:
                    element_totals[(file_id, name)] = element_totals.get((file_id, name), 0) + 1
            elif layer == 'extract':
                extract_events[(name, reason)] = extract_events.get((name, reason), 0) + 1
            else:
                identity_events[(name, reason)] = identity_events.get((name, reason), 0) + 1
    return {'n_events': n_events, 'raw_events': raw_events, 'extract_events': extract_events,
            'identity_events': identity_events, 'element_totals': element_totals,
            'reason_totals': reason_totals}


def pass_row_masks(events):
    """Stream R/row_masks.csv.gz once, write the corrected copy and collect arrays."""
    raw_events = events['raw_events']
    event_index = {}
    for (file_id, line, field), entry in raw_events.items():
        event_index.setdefault((file_id, line), {})[field] = entry
    fields = {name: i for i, name in enumerate(FIELD_ORDER)}
    arrays = {name: [] for name in ['file_code', 'line', 'domain_code', 'role_code', 'flags',
                                    'valid_groups', 'q_nan', 'raw_old', 'raw_new', 'extract_nan']}
    domain_codes = {}
    domain_names = []
    role_codes = {}
    role_names = []
    corrections = []
    old_bits_without_event_evidence = 0
    column_diffs = {}
    source_lines = {}
    n_rows = 0
    with gzip.open(R_DIR / 'row_masks.csv.gz', 'rt', encoding='utf-8', newline='') as fin, \
            gzip.open(RUN_DIR / 'row_masks_corrected.csv.gz', 'wt', encoding='utf-8', newline='') as fout:
        reader = csv.DictReader(fin)
        columns = list(reader.fieldnames)
        writer = csv.DictWriter(fout, fieldnames=columns, extrasaction='raise')
        writer.writeheader()
        for row in reader:
            n_rows += 1
            file_id = row['file_id']
            line = row['source_line']
            parse_ok = int(row['parse_ok'] or 0)
            row_events = event_index.get((file_id, line), {})
            event_fields = sorted(row_events)
            if parse_ok and event_fields:
                event_bits = set_bits(event_fields, fields)
            else:
                event_bits = 0
            old_bits = parse_bits(row['raw_invalid_bits'], len(FIELD_ORDER))
            new_bits = old_bits | event_bits
            if old_bits & ~new_bits:
                old_bits_without_event_evidence += 1
            if new_bits != old_bits:
                reasons = sorted({r for entry in row_events.values() for r in entry['reasons']})
                corrections.append({
                    'file_id': file_id, 'source_line': line, 'domain': row['domain'],
                    'evaluation_role': row['evaluation_role'],
                    'old_raw_invalid_bits': bits_to_string(old_bits, len(FIELD_ORDER)),
                    'old_raw_invalid_count': int(row['raw_invalid_count'] or 0),
                    'new_raw_invalid_bits': bits_to_string(new_bits, len(FIELD_ORDER)),
                    'new_raw_invalid_count': bin(new_bits).count('1'),
                    'changed_fields': '|'.join(sorted(event_fields)),
                    'reasons': '|'.join(reasons),
                    'evidence_event_rows': sum(row_events[f]['n_events'] for f in event_fields),
                    'nan_elements_by_field': '|'.join(
                        f"{f}:{row_events[f]['nan_elements']}"
                        for f in event_fields if row_events[f]['nan_elements']),
                    'evidence_source': 'invalid_values.csv.gz'})
            out = dict(row)
            out['raw_invalid_bits'] = bits_to_string(new_bits, len(FIELD_ORDER))
            out['raw_invalid_count'] = bin(new_bits).count('1')
            for column in columns:
                if column in ('raw_invalid_bits', 'raw_invalid_count'):
                    continue
                if out.get(column, '') != row.get(column, ''):
                    column_diffs[column] = column_diffs.get(column, 0) + 1
            writer.writerow(out)
            domain = row['domain']
            if domain not in domain_codes:
                domain_codes[domain] = len(domain_names)
                domain_names.append(domain)
            role = row['evaluation_role'] or 'unparsed'
            if role not in role_codes:
                role_codes[role] = len(role_names)
                role_names.append(role)
            file_code = {'A1': 0, 'A2_arxiv': 1, 'A3_github': 2}[file_id]
            flags = 0
            if parse_ok:
                flags |= 1
                if int(row['is_unique_first'] or 0):
                    flags |= 2
                if int(row['overlap_a1'] or 0):
                    flags |= 4
            valid_groups = 0
            if parse_ok:
                for key in ['would_group_usability_be_nan', 'would_group_knowledge_be_nan',
                            'would_group_education_reasoning_be_nan']:
                    valid_groups += 1 - int(row[key] or 0)
            arrays['file_code'].append(file_code)
            arrays['line'].append(int(line))
            arrays['domain_code'].append(domain_codes[domain])
            arrays['role_code'].append(role_codes[role])
            arrays['flags'].append(flags)
            arrays['valid_groups'].append(valid_groups if parse_ok else 0)
            arrays['q_nan'].append(int(row['would_Q_be_nan'] or 0) if parse_ok else 0)
            arrays['raw_old'].append(old_bits)
            arrays['raw_new'].append(new_bits)
            arrays['extract_nan'].append(parse_bits(row['extract_nan_bits'], len(FEATURE_ORDER))
                                         if parse_ok else 0)
            source_lines.setdefault(file_id, []).append(int(line))
    packed = {name: np.asarray(values, dtype=np.uint32) for name, values in arrays.items()}
    return {'arrays': packed, 'domain_names': domain_names, 'role_names': role_names,
            'corrections': corrections, 'columns': columns,
            'old_bits_without_event_evidence': old_bits_without_event_evidence,
            'unchanged_column_diffs': column_diffs, 'n_rows': n_rows,
            'source_lines': source_lines}


SCOPES = [
    ('A1_calibration', 'role_A1_calibration'),
    ('A1_holdout', 'role_A1_holdout'),
    ('A1_all_unique', 'file_A1_unique'),
    ('extension_overlap_A1', 'overlap'),
    ('extension_new_records', 'role_extension_new_unique'),
    ('all_unique', 'unique'),
    ('file_unique_first_A1', 'file_A1_unique'),
    ('file_unique_first_A2_arxiv', 'file_A2_unique'),
    ('file_unique_first_A3_github', 'file_A3_unique'),
]


def scope_masks(packed, role_names):
    file_code = packed['file_code']
    flags = packed['flags']
    role_code = packed['role_code']
    role_index = {name: i for i, name in enumerate(role_names)}
    parse_ok = (flags & 1) != 0
    unique = (flags & 2) != 0
    overlap = (flags & 4) != 0
    by_role = {name: role_code == index for name, index in role_index.items()}
    masks = {}
    for scope, rule in SCOPES:
        if rule == 'role_A1_calibration':
            mask = parse_ok & unique & by_role.get('A1_calibration', np.zeros_like(unique))
        elif rule == 'role_A1_holdout':
            mask = parse_ok & unique & by_role.get('A1_holdout', np.zeros_like(unique))
        elif rule == 'file_A1_unique':
            mask = parse_ok & unique & (file_code == 0)
        elif rule == 'overlap':
            mask = parse_ok & overlap
        elif rule == 'role_extension_new_unique':
            mask = parse_ok & unique & by_role.get('extension_new_records', np.zeros_like(unique))
        elif rule == 'unique':
            mask = parse_ok & unique
        elif rule == 'file_A2_unique':
            mask = parse_ok & unique & (file_code == 1)
        elif rule == 'file_A3_unique':
            mask = parse_ok & unique & (file_code == 2)
        else:
            raise AssertionError(rule)
        masks[scope] = mask
    return masks


def raw_mask_aggregates(packed, masks, domain_names):
    """Patterns and pairwise counts for the corrected raw_field_invalid mask."""
    patterns = {}
    pairwise = {}
    for scope, scope_mask in masks.items():
        domains = [d for d in range(len(domain_names)) if np.any(scope_mask & (packed['domain_code'] == d))]
        for domain in domains + [-1]:
            idx = scope_mask if domain == -1 else scope_mask & (packed['domain_code'] == domain)
            label = 'ALL' if domain == -1 else domain_names[domain]
            sub = packed['raw_new'][idx]
            n = int(sub.size)
            if n == 0:
                continue
            values, counts = np.unique(sub, return_counts=True)
            patterns[(scope, label)] = {int(v): int(c) for v, c in zip(values, counts)}
            matrix = np.zeros((n, len(FIELD_ORDER)), dtype=np.float32)
            for j in range(len(FIELD_ORDER)):
                matrix[:, j] = ((sub >> j) & 1).astype(np.float32)
            inter = np.rint(matrix.T @ matrix).astype(np.int64)
            marg = np.rint(matrix.sum(axis=0)).astype(np.int64)
            pairwise[(scope, label)] = {'n': n, 'marginal': marg, 'intersection': inter}
    return patterns, pairwise


def group_denominator_aggregates(packed, masks, domain_names):
    out = {}
    for scope, scope_mask in masks.items():
        domains = [d for d in range(len(domain_names)) if np.any(scope_mask & (packed['domain_code'] == d))]
        for domain in domains + [-1]:
            idx = scope_mask if domain == -1 else scope_mask & (packed['domain_code'] == domain)
            label = 'ALL' if domain == -1 else domain_names[domain]
            valid = packed['valid_groups'][idx]
            out[(scope, label)] = {
                'n_total': int(valid.size),
                'n_valid_0': int((valid == 0).sum()),
                'n_valid_1': int((valid == 1).sum()),
                'n_valid_2': int((valid == 2).sum()),
                'n_valid_3': int((valid == 3).sum()),
                'n_range_defined': int((valid >= 1).sum()),
                'n_std0_defined': int((valid >= 1).sum()),
                'n_false_from_missing_range': int((valid == 0).sum()),
                'n_q_nonmissing': int((packed['q_nan'][idx] == 0).sum()),
                'n_q_missing': int((packed['q_nan'][idx] == 1).sum()),
            }
    return out


def build_raw_field_counts_corrected(events, domain_by_line, r_rows):
    """Correct nan_rows / posinf_rows / neginf_rows to anomaly RECORD counts.

    Record counts and element counts come from the saved raw events grouped by
    (file_id, source_line, field); the domain is joined from row_masks.
    """
    raw_events = events['raw_events']
    rows = []
    cross_check = {}
    for row in r_rows:
        file_id = row['file_id']
        domain = row['domain']
        field = row['field']
        record_counts = {'nan_element': set(), 'posinf_element': set(), 'neginf_element': set(),
                         'non_numeric_element': set(), 'null': set(), 'wrong_list_length': set()}
        element_counts = {'nan_element': 0, 'posinf_element': 0, 'neginf_element': 0,
                          'non_numeric_element': 0}
        for (fid, line, fname), entry in raw_events.items():
            if fid != file_id or fname != field:
                continue
            row_domain = domain_by_line.get((fid, line), '')
            if domain != 'ALL' and row_domain != domain:
                continue
            for reason, bucket in record_counts.items():
                if reason in entry['reasons']:
                    bucket.add(line)
            element_counts['nan_element'] += entry['nan_elements']
            element_counts['posinf_element'] += entry['posinf_elements']
            element_counts['neginf_element'] += entry['neginf_elements']
            element_counts['non_numeric_element'] += entry['non_numeric_elements']
        corrected = dict(row)
        corrected['nan_rows_prior_erroneous'] = row['nan_rows']
        corrected['posinf_rows_prior_erroneous'] = row['posinf_rows']
        corrected['neginf_rows_prior_erroneous'] = row['neginf_rows']
        corrected['nan_rows'] = len(record_counts['nan_element'])
        corrected['posinf_rows'] = len(record_counts['posinf_element'])
        corrected['neginf_rows'] = len(record_counts['neginf_element'])
        corrected['record_count_basis'] = 'distinct (file_id, source_line) with >=1 event for that field/reason'
        corrected['element_count_basis'] = 'event rows in invalid_values.csv.gz (unchanged from R)'
        corrected['evidence_source'] = 'invalid_values.csv.gz joined to row_masks.csv.gz by (file_id, source_line)'
        keys = [(file_id, domain, field, 'nan', row['nan_rows'], corrected['nan_rows'],
                 row['nan_elements'], element_counts['nan_element']),
                (file_id, domain, field, 'posinf', row['posinf_rows'], corrected['posinf_rows'],
                 row['posinf_elements'], element_counts['posinf_element']),
                (file_id, domain, field, 'neginf', row['neginf_rows'], corrected['neginf_rows'],
                 row['neginf_elements'], element_counts['neginf_element']),
                (file_id, domain, field, 'null', row['null'], len(record_counts['null']), None, None),
                (file_id, domain, field, 'wrong_list_length', row['wrong_length_rows'],
                 len(record_counts['wrong_list_length']), None, None),
                (file_id, domain, field, 'non_numeric_rows', row['non_numeric_rows_detailed'],
                 len(record_counts['non_numeric_element']), None, None),
                (file_id, domain, field, 'non_numeric_elements', row['non_numeric_elements'], None,
                 None, element_counts['non_numeric_element'])]
        for key in keys:
            cross_check[key] = key
        rows.append(corrected)
    columns = list(r_rows[0].keys()) + ['nan_rows_prior_erroneous', 'posinf_rows_prior_erroneous',
                                        'neginf_rows_prior_erroneous', 'record_count_basis',
                                        'element_count_basis', 'evidence_source']
    return rows, columns, cross_check


def event_cross_check(cross_check):
    """Recompute event-derived counts and compare with R's stored values where the
    semantic is already per-record (null, wrong length, non numeric row/element)."""
    mismatches = []
    for (_fid, domain, field, metric, prior_value, event_record_count, prior_elements,
         event_elements) in cross_check:
        if metric in ('null', 'wrong_list_length', 'non_numeric_rows'):
            if prior_value is not None and event_record_count is not None and int(float(prior_value)) != event_record_count:
                mismatches.append({'metric': metric, 'file_id': _fid, 'domain': domain,
                                   'field': field, 'stored': prior_value,
                                   'from_events': event_record_count})
        if metric in ('nan', 'posinf', 'neginf') and prior_elements is not None and event_elements is not None:
            if int(float(prior_elements)) != event_elements:
                mismatches.append({'metric': f'{metric}_elements', 'file_id': _fid, 'domain': domain,
                                   'field': field, 'stored': prior_elements,
                                   'from_events': event_elements})
        if metric == 'non_numeric_elements' and prior_elements is not None and event_elements is not None:
            if int(float(prior_elements)) != event_elements:
                mismatches.append({'metric': metric, 'file_id': _fid, 'domain': domain,
                                   'field': field, 'stored': prior_elements,
                                   'from_events': event_elements})
    return mismatches


def build_patterns_corrected(r_patterns, raw_patterns):
    rows = []
    kept = 0
    for row in r_patterns:
        if row['mask_kind'] == 'raw_field_invalid':
            continue
        kept += 1
        item = dict(row)
        item['changed_from_prior'] = 0
        rows.append(item)
    prior_by_key = {(row['scope'], row['domain'], row['mask_kind'], int(row['mask_bits'])): row
                    for row in r_patterns}
    n_changed = 0
    for (scope, domain), counts in raw_patterns.items():
        n_scope = sum(counts.values())
        for mask_value, count in sorted(counts.items()):
            names = '|'.join(name for j, name in enumerate(FIELD_ORDER) if (mask_value >> j) & 1)
            key = (scope, domain, 'raw_field_invalid', mask_value)
            prior = prior_by_key.get(key)
            changed = 0 if (prior is not None and int(prior['n']) == count) else 1
            n_changed += changed
            rows.append({'scope': scope, 'domain': domain, 'mask_kind': 'raw_field_invalid',
                         'feature_universe': 'FIELDS22', 'mask_bits': mask_value,
                         'feature_mask': bits_to_string(mask_value, len(FIELD_ORDER)),
                         'feature_names': names, 'n': count, 'n_scope': n_scope,
                         'rate': (count / n_scope) if n_scope else None,
                         'changed_from_prior': changed})
    columns = list(r_patterns[0].keys()) + ['changed_from_prior']
    return rows, columns, kept, n_changed


def build_pairwise_corrected(r_pairwise, raw_pairwise):
    rows = []
    kept = 0
    for row in r_pairwise:
        if row['mask_kind'] == 'raw_field_invalid':
            continue
        kept += 1
        item = dict(row)
        item['changed_from_prior'] = 0
        rows.append(item)
    prior_by_key = {(row['scope'], row['domain'], row['mask_kind'], row['feature_i'], row['feature_j']): row
                    for row in r_pairwise}
    n_changed = 0
    for (scope, domain), agg in raw_pairwise.items():
        n_scope = agg['n']
        marg = agg['marginal']
        inter = agg['intersection']
        for i in range(len(FIELD_ORDER)):
            for j in range(i, len(FIELD_ORDER)):
                n_i = int(marg[i])
                n_j = int(marg[j])
                n_inter = int(inter[i, j])
                n_union = n_i if i == j else n_i + n_j - n_inter
                key = (scope, domain, 'raw_field_invalid', FIELD_ORDER[i], FIELD_ORDER[j])
                prior = prior_by_key.get(key)
                changed = 0 if (prior is not None and int(prior['n_i']) == n_i
                                and int(prior['n_j']) == n_j
                                and int(prior['n_intersection']) == n_inter
                                and int(prior['n_union']) == n_union) else 1
                n_changed += changed
                rows.append({'scope': scope, 'domain': domain, 'mask_kind': 'raw_field_invalid',
                             'feature_universe': 'FIELDS22', 'feature_i': FIELD_ORDER[i],
                             'feature_j': FIELD_ORDER[j], 'n_scope': n_scope, 'n_i': n_i, 'n_j': n_j,
                             'n_intersection': n_inter, 'n_union': n_union,
                             'changed_from_prior': changed})
    columns = list(r_pairwise[0].keys()) + ['changed_from_prior']
    return rows, columns, kept, n_changed


def build_summary_denominators_corrected(r_summary, denom_aggs):
    rows = []
    n_changed = 0
    for row in r_summary:
        item = dict(row)
        key = (row['scope'], row['domain'])
        agg = denom_aggs.get(key)
        prior_effective = row['n_effective']
        prior_false = row['missing_comparison_as_false_n']
        statistic = row['statistic']
        change_reason = ''
        if agg is not None and statistic == 'rater_disagreement_mean':
            if int(row['n_effective']) != agg['n_range_defined']:
                change_reason = ('range is defined with >=1 usable group (pandas skipna); the prior '
                                 'implementation treated any missing group as undefined')
            item['n_nonmissing'] = agg['n_range_defined']
            item['n_finite'] = agg['n_range_defined']
            item['n_effective'] = agg['n_range_defined']
        elif agg is not None and statistic == 'rater_disagreement_std':
            if int(row['n_effective']) != agg['n_std0_defined']:
                change_reason = ('ddof=0 group std is defined with >=1 usable group (pandas skipna); '
                                 'the prior implementation treated any missing group as undefined')
            item['n_nonmissing'] = agg['n_std0_defined']
            item['n_finite'] = agg['n_std0_defined']
            item['n_effective'] = agg['n_std0_defined']
        elif agg is not None and statistic == 'rater_disagreement_gt_0_5_fraction':
            if int(row['missing_comparison_as_false_n']) != agg['n_false_from_missing_range']:
                change_reason = ('only rows with zero usable groups produce a missing range whose '
                                 'comparison becomes False')
            item['missing_comparison_as_false_n'] = agg['n_false_from_missing_range']
            item['n_effective'] = agg['n_total']
        item['prior_n_effective'] = prior_effective
        item['prior_missing_comparison_as_false_n'] = prior_false
        ddof = row['ddof']
        n_eff = item['n_effective']
        if statistic == 'Q_std':
            item['variance_divisor'] = (int(n_eff) - 1) if (n_eff not in ('', None) and int(n_eff) >= 2) else None
            item['variance_divisor_rule'] = 'ddof=1: variance divisor = n_effective - 1'
            item['status'] = 'DEFINED' if (n_eff not in ('', None) and int(n_eff) >= 2) else 'UNDEFINED_N_LT_2'
            item['status_reason'] = 'pandas Series.std() default ddof=1'
        elif statistic == 'rater_disagreement_std':
            item['variance_divisor'] = int(n_eff) if (n_eff not in ('', None) and int(n_eff) >= 1) else None
            item['variance_divisor_rule'] = 'ddof=0: variance divisor = n_effective (rows with >=1 usable group)'
            item['status'] = 'DEFINED' if (n_eff not in ('', None) and int(n_eff) >= 1) else 'UNDEFINED_NO_USABLE_GROUP'
            item['status_reason'] = 'DataFrame.std(axis=1, ddof=0) with skipna=True'
        else:
            item['variance_divisor'] = None
            item['variance_divisor_rule'] = 'not a variance statistic'
            item['status'] = 'DEFINED' if (n_eff not in ('', None) and int(n_eff) > 0) else 'UNDEFINED_EMPTY'
            item['status_reason'] = 'mean / quantile / fraction over non-missing rows'
        item['changed_from_prior'] = 1 if (str(item['n_effective']) != str(prior_effective)
                                           or str(item['missing_comparison_as_false_n']) != str(prior_false)) else 0
        item['correction_reason'] = change_reason
        n_changed += item['changed_from_prior']
        rows.append(item)
    columns = list(r_summary[0].keys()) + ['prior_n_effective',
                                           'prior_missing_comparison_as_false_n', 'variance_divisor',
                                           'variance_divisor_rule', 'status', 'status_reason',
                                           'changed_from_prior', 'correction_reason']
    return rows, columns, n_changed


def build_missing_concentration(packed, masks, domain_names, role_names):
    rows = []
    role_code = packed['role_code']
    for scope, scope_mask in masks.items():
        n_scope = int(scope_mask.sum())
        for mask_kind, values in [('would_Q_be_nan', packed['q_nan']),
                                  ('raw_field_invalid', (packed['raw_new'] != 0).astype(np.uint32))]:
            missing = values.astype(bool) & scope_mask
            n_scope_missing = int(missing.sum())
            for domain_index in list(range(len(domain_names))) + [-1]:
                domain_label = 'ALL' if domain_index == -1 else domain_names[domain_index]
                domain_sel = scope_mask if domain_index == -1 else scope_mask & (packed['domain_code'] == domain_index)
                if not np.any(domain_sel):
                    continue
                for role_index in list(range(len(role_names))) + [-1]:
                    role_label = 'ALL' if role_index == -1 else role_names[role_index]
                    sel = domain_sel if role_index == -1 else domain_sel & (role_code == role_index)
                    n_group = int(sel.sum())
                    if n_group == 0:
                        continue
                    n_missing = int((missing & sel).sum())
                    undefined = None
                    if n_scope_missing == 0:
                        undefined = 'scope has no missing records for this mask_kind (share denominator is 0)'
                    if n_group == 0:
                        undefined = 'empty group (rate denominator is 0)'
                    rows.append({
                        'scope': scope, 'mask_kind': mask_kind,
                        'layer': 'normalization_propagation' if mask_kind == 'would_Q_be_nan'
                                 else 'raw_events_rebuilt',
                        'domain': domain_label, 'evaluation_role': role_label,
                        'n_group_total': n_group, 'n_missing': n_missing,
                        'rate_within_group': (n_missing / n_group) if n_group else None,
                        'n_scope_total': n_scope, 'n_scope_missing': n_scope_missing,
                        'share_of_scope_missing': (n_missing / n_scope_missing) if n_scope_missing else None,
                        'rate_numerator': n_missing,
                        'rate_denominator': n_group,
                        'share_numerator': n_missing,
                        'share_denominator': n_scope_missing,
                        'undefined_reason': undefined,
                        'notes': 'share = share of all missing records of this mask_kind inside the scope'})
    return rows


CHANGES_COLUMNS = ['table', 'key', 'field', 'prior_value', 'corrected_value', 'change_type',
                   'evidence_source', 'affected_rows', 'note']


def build_changes(r_raw_prior, r_raw_new, corrections, patterns_prior, patterns_new,
                  pairwise_prior, pairwise_new, denominators_prior, denominators_new):
    rows = []
    for prior, new in zip(r_raw_prior, r_raw_new):
        for field, prior_key in [('nan_rows', 'nan_rows_prior_erroneous'),
                                 ('posinf_rows', 'posinf_rows_prior_erroneous'),
                                 ('neginf_rows', 'neginf_rows_prior_erroneous')]:
            if str(prior[field]) != str(new[field]):
                rows.append({'table': 'raw_field_counts_corrected.csv',
                             'key': f"{prior['file_id']}|{prior['domain']}|{prior['field']}",
                             'field': field, 'prior_value': prior[field], 'corrected_value': new[field],
                             'change_type': 'element_count_replaced_by_record_count',
                             'evidence_source': 'invalid_values.csv.gz raw events joined to row_masks.csv.gz',
                             'affected_rows': 1,
                             'note': 'prior value kept in column ' + prior_key + '; element count remains in the *_elements columns'})
    for item in corrections:
        rows.append({'table': 'row_masks_corrected.csv.gz',
                     'key': f"{item['file_id']}|{item['source_line']}",
                     'field': 'raw_invalid_bits;raw_invalid_count',
                     'prior_value': f"{item['old_raw_invalid_bits']};{item['old_raw_invalid_count']}",
                     'corrected_value': f"{item['new_raw_invalid_bits']};{item['new_raw_invalid_count']}",
                     'change_type': 'raw_anomaly_event_added_to_mask',
                     'evidence_source': 'invalid_values.csv.gz raw events (same file_id/source_line/field)',
                     'affected_rows': 1,
                     'note': f"changed_fields={item['changed_fields']}; reasons={item['reasons']}; nan_elements={item['nan_elements_by_field']}"})
    prior_patterns = {(row['scope'], row['domain'], row['mask_kind'], row['mask_bits']): row
                      for row in patterns_prior}
    for row in patterns_new:
        if row['mask_kind'] != 'raw_field_invalid':
            continue
        key = (row['scope'], row['domain'], row['mask_kind'], row['mask_bits'])
        prior = prior_patterns.get(key)
        if prior is None or str(prior['n']) != str(row['n']):
            rows.append({'table': 'missing_patterns_corrected.csv',
                         'key': f"{row['scope']}|{row['domain']}|raw_field_invalid|{row['mask_bits']}",
                         'field': 'n', 'prior_value': (prior or {}).get('n', 'MISSING_ROW'),
                         'corrected_value': row['n'], 'change_type': 'raw_layer_pattern_rebuilt',
                         'evidence_source': 'row_masks_corrected.csv.gz raw_invalid_bits',
                         'affected_rows': 1, 'note': f"feature_names={row['feature_names']}"})
    prior_pairs = {(row['scope'], row['domain'], row['mask_kind'], row['feature_i'], row['feature_j']): row
                   for row in pairwise_prior}
    for row in pairwise_new:
        if row['mask_kind'] != 'raw_field_invalid':
            continue
        key = (row['scope'], row['domain'], row['mask_kind'], row['feature_i'], row['feature_j'])
        prior = prior_pairs.get(key)
        changed = (prior is None or str(prior['n_i']) != str(row['n_i'])
                   or str(prior['n_j']) != str(row['n_j'])
                   or str(prior['n_intersection']) != str(row['n_intersection'])
                   or str(prior['n_union']) != str(row['n_union']))
        if changed:
            rows.append({'table': 'missing_pairwise_corrected.csv',
                         'key': f"{row['scope']}|{row['domain']}|raw_field_invalid|{row['feature_i']}|{row['feature_j']}",
                         'field': 'n_i;n_j;n_intersection;n_union',
                         'prior_value': (f"{(prior or {}).get('n_i')};{(prior or {}).get('n_j')};"
                                         f"{(prior or {}).get('n_intersection')};{(prior or {}).get('n_union')}"),
                         'corrected_value': f"{row['n_i']};{row['n_j']};{row['n_intersection']};{row['n_union']}",
                         'change_type': 'raw_layer_pairwise_rebuilt',
                         'evidence_source': 'row_masks_corrected.csv.gz raw_invalid_bits',
                         'affected_rows': 1, 'note': ''})
    denominator_keys = ['n_nonmissing', 'n_finite', 'n_effective', 'missing_comparison_as_false_n']
    for prior, new in zip(denominators_prior, denominators_new):
        changed_fields = [k for k in denominator_keys if str(prior.get(k, '')) != str(new.get(k, ''))]
        if changed_fields:
            rows.append({'table': 'summary_denominators_corrected.csv',
                         'key': f"{new['scope']}|{new['domain']}|{new['statistic']}",
                         'field': ';'.join(changed_fields),
                         'prior_value': ';'.join(str(prior.get(k, '')) for k in changed_fields),
                         'corrected_value': ';'.join(str(new.get(k, '')) for k in changed_fields),
                         'change_type': 'disagreement_denominator_corrected',
                         'evidence_source': 'row_masks.csv.gz would_group_*_be_nan masks + pandas skipna semantics',
                         'affected_rows': 1, 'note': new.get('correction_reason', '')})
    return rows


def main():
    global LOG
    LOG = Logger(RUN_DIR / 'repair.log')
    log(f'TASK-Q01A-R1 repair start local={now_iso()} run_dir={RUN_DIR}')
    log('boundary: no compressed input (A1-A3) is opened, decompressed or hashed in this script')
    errors = []
    input_manifest = {'run_id': RUN_ID, 'phase': 'repair_from_artifacts',
                      'generated_local': now_iso(), 'read_only_inputs': [],
                      'compressed_inputs_not_read': [], 'notes': []}
    for path in READ_ONLY_INPUTS:
        if not Path(path).is_file():
            errors.append(f'missing read-only input: {path}')
            continue
        stat = Path(path).stat()
        input_manifest['read_only_inputs'].append({
            'path': str(Path(path).relative_to(PROJECT)).replace('\\', '/'),
            'bytes': stat.st_size, 'mtime': stat.st_mtime, 'sha256': sha256_file(path)})
    for path in COMPRESSED_INPUTS:
        stat = Path(path).stat()
        input_manifest['compressed_inputs_not_read'].append({
            'path': str(Path(path).relative_to(PROJECT)).replace('\\', '/'),
            'bytes': stat.st_size, 'mtime': stat.st_mtime,
            'content_read': False, 'content_hashed': False,
            'note': 'stat only (size/mtime); no open/read/decompress/hash in TASK-Q01A-R1'})
    input_manifest['notes'].append('pandas default NA parsing is not used for invalid_values.csv.gz (csv module) '
                                   'so that the literal "nan" in reason/value_kind is preserved')
    input_manifest['errors'] = errors
    write_json(RUN_DIR / 'input_manifest.json', input_manifest)
    if errors:
        log(f'FATAL: {len(errors)} missing inputs')
        write_json(RUN_DIR / 'repair_phase_summary.json', {'status': 'FAILED', 'errors': errors})
        return 2
    events = load_events()
    log(f"stage=events rows={events['n_events']} raw_event_keys={len(events['raw_events'])} "
        f"extract_events={sum(events['extract_events'].values())} identity_events={sum(events['identity_events'].values())}")
    packed_info = pass_row_masks(events)
    log(f"stage=row_masks rows={packed_info['n_rows']} corrections={len(packed_info['corrections'])} "
        f"unchanged_column_diffs={packed_info['unchanged_column_diffs']}")
    if packed_info['unchanged_column_diffs']:
        errors.append('columns other than raw_invalid_bits/raw_invalid_count changed: '
                      + json.dumps(packed_info['unchanged_column_diffs']))
    packed = packed_info['arrays']
    domain_names = packed_info['domain_names']
    role_names = packed_info['role_names']
    masks = scope_masks(packed, role_names)
    raw_patterns, raw_pairwise = raw_mask_aggregates(packed, masks, domain_names)
    denom_aggs = group_denominator_aggregates(packed, masks, domain_names)
    file_by_code = {0: 'A1', 1: 'A2_arxiv', 2: 'A3_github'}
    domain_by_line = {(file_by_code[int(f)], int(l)): domain_names[int(d)]
                      for f, l, d in zip(packed['file_code'], packed['line'], packed['domain_code'])}
    r_raw = read_csv_rows(R_DIR / 'raw_field_counts.csv')
    raw_corrected, raw_columns, cross_check = build_raw_field_counts_corrected(
        events, domain_by_line, r_raw)
    write_csv(RUN_DIR / 'raw_field_counts_corrected.csv', raw_columns, raw_corrected)
    mismatch = event_cross_check(cross_check)
    log(f'stage=raw_field_counts rows={len(raw_corrected)} event_cross_check_mismatches={len(mismatch)}')
    write_csv(RUN_DIR / 'raw_mask_corrections.csv',
              ['file_id', 'source_line', 'domain', 'evaluation_role', 'old_raw_invalid_bits',
               'old_raw_invalid_count', 'new_raw_invalid_bits', 'new_raw_invalid_count',
               'changed_fields', 'reasons', 'evidence_event_rows', 'nan_elements_by_field',
               'evidence_source'],
              sorted(packed_info['corrections'], key=lambda x: (x['file_id'], int(x['source_line']))))
    r_patterns = read_csv_rows(R_DIR / 'missing_patterns.csv')
    patterns_corrected, pattern_columns, patterns_kept, patterns_changed = build_patterns_corrected(
        r_patterns, raw_patterns)
    write_csv(RUN_DIR / 'missing_patterns_corrected.csv', pattern_columns, patterns_corrected)
    r_pairwise = read_csv_rows(R_DIR / 'missing_pairwise.csv')
    pairwise_corrected, pairwise_columns, pairwise_kept, pairwise_changed = build_pairwise_corrected(
        r_pairwise, raw_pairwise)
    write_csv(RUN_DIR / 'missing_pairwise_corrected.csv', pairwise_columns, pairwise_corrected)
    r_denominators = read_csv_rows(R_DIR / 'summary_denominators.csv')
    denominators_corrected, denominator_columns, denominators_changed = build_summary_denominators_corrected(
        r_denominators, denom_aggs)
    write_csv(RUN_DIR / 'summary_denominators_corrected.csv', denominator_columns, denominators_corrected)
    concentration = build_missing_concentration(packed, masks, domain_names, role_names)
    write_csv(RUN_DIR / 'missing_concentration.csv',
              ['scope', 'mask_kind', 'layer', 'domain', 'evaluation_role', 'n_group_total',
               'n_missing', 'rate_within_group', 'n_scope_total', 'n_scope_missing',
               'share_of_scope_missing', 'rate_numerator', 'rate_denominator', 'share_numerator',
               'share_denominator', 'undefined_reason', 'notes'], concentration)
    log(f'stage=tables patterns_kept={patterns_kept} patterns_changed={patterns_changed} '
        f'pairwise_kept={pairwise_kept} pairwise_changed={pairwise_changed} '
        f'denominators_changed={denominators_changed} concentration_rows={len(concentration)}')
    record_fields = {}
    for (service_file, line, field), entry in events['raw_events'].items():
        record_fields.setdefault((service_file, line, field), set()).update(entry['reasons'])
    per_field_rows = {}
    for (service_file, line, field) in record_fields:
        per_field_rows[(service_file, field)] = per_field_rows.get((service_file, field), 0) + 1
    union_rows = {}
    for (service_file, line, field) in record_fields:
        union_rows.setdefault(service_file, set()).add(line)
    prof_records = {(f, l) for (f, l, field) in record_fields if field == 'modernbert_professionalism'}
    reason_records = {(f, l) for (f, l, field) in record_fields if field == 'modernbert_reasoning'}
    nan_elements_by_field = {f'{k[0]}|{k[1]}': v for k, v in sorted(events['element_totals'].items())}
    all_unique_mask = masks['all_unique']
    all_unique_raw = packed['raw_new'][all_unique_mask]
    prof_bit = ((all_unique_raw >> FIELD_INDEX['modernbert_professionalism']) & 1).astype(bool)
    reason_bit = ((all_unique_raw >> FIELD_INDEX['modernbert_reasoning']) & 1).astype(bool)
    anchors = {
        'raw_anomaly_record_counts_by_file_field': {f'{k[0]}|{k[1]}': v for k, v in sorted(per_field_rows.items())},
        'raw_anomaly_union_records': {k: len(v) for k, v in sorted(union_rows.items())},
        'raw_anomaly_union_total': len({(f, l) for (f, l, _field) in record_fields}),
        'two_field_union_records': len(prof_records | reason_records),
        'two_field_intersection_records': len(prof_records & reason_records),
        'nan_element_totals_by_file_field': nan_elements_by_field,
        'nan_element_grand_total': sum(events['element_totals'].values()),
        'all_unique_raw_union': int((all_unique_raw != 0).sum()),
        'all_unique_raw_intersection_two_fields': int((prof_bit & reason_bit).sum()),
        'all_unique_denominators': denom_aggs.get(('all_unique', 'ALL')),
        'denominator_rule_check': {
            'q_std_n_effective': next(int(row['n_effective']) for row in denominators_corrected
                                      if row['scope'] == 'all_unique' and row['domain'] == 'ALL'
                                      and row['statistic'] == 'Q_std'),
            'q_std_variance_divisor': next(row['variance_divisor'] for row in denominators_corrected
                                           if row['scope'] == 'all_unique' and row['domain'] == 'ALL'
                                           and row['statistic'] == 'Q_std'),
            'range_mean_n_effective': next(int(row['n_effective']) for row in denominators_corrected
                                           if row['scope'] == 'all_unique' and row['domain'] == 'ALL'
                                           and row['statistic'] == 'rater_disagreement_mean'),
            'range_std_n_effective': next(int(row['n_effective']) for row in denominators_corrected
                                          if row['scope'] == 'all_unique' and row['domain'] == 'ALL'
                                          and row['statistic'] == 'rater_disagreement_std'),
            'false_from_missing_range': next(int(row['missing_comparison_as_false_n'])
                                             for row in denominators_corrected
                                             if row['scope'] == 'all_unique' and row['domain'] == 'ALL'
                                             and row['statistic'] == 'rater_disagreement_gt_0_5_fraction')}}
    expected_anchors = {'A1|modernbert_professionalism': 5, 'A1|modernbert_reasoning': 13,
                        'A3_github|modernbert_professionalism': 1}
    anchor_ok = all(anchors['raw_anomaly_record_counts_by_file_field'].get(k) == v
                    for k, v in expected_anchors.items())
    anchor_ok = anchor_ok and anchors['raw_anomaly_union_total'] == 19
    anchor_ok = anchor_ok and anchors['two_field_intersection_records'] == 0
    anchor_ok = anchor_ok and anchors['nan_element_grand_total'] == 114
    anchor_ok = anchor_ok and anchors['denominator_rule_check']['range_mean_n_effective'] == 261086
    anchor_ok = anchor_ok and anchors['denominator_rule_check']['range_std_n_effective'] == 261086
    anchor_ok = anchor_ok and anchors['denominator_rule_check']['false_from_missing_range'] == 0
    anchor_ok = anchor_ok and anchors['denominator_rule_check']['q_std_n_effective'] == 261067
    anchor_ok = anchor_ok and anchors['denominator_rule_check']['q_std_variance_divisor'] == 261066
    log(f'stage=anchors ok={anchor_ok} anchors={json.dumps(anchors, ensure_ascii=False, default=str)[:900]}')
    changes = build_changes(r_raw, raw_corrected, packed_info['corrections'], r_patterns,
                            patterns_corrected, r_pairwise, pairwise_corrected,
                            r_denominators, denominators_corrected)
    write_csv(RUN_DIR / 'changes.csv', CHANGES_COLUMNS, changes)
    log(f'stage=changes rows={len(changes)}')
    environment = {
        'run_id': RUN_ID, 'phase': 'repair_from_artifacts', 'start_local': START_LOCAL.isoformat(timespec='seconds'),
        'end_local': now_iso(), 'duration_s': round(time.monotonic() - START_MONO, 3),
        'script': str(RUN_DIR / 'repair_from_artifacts.py'),
        'script_sha256': sha256_file(RUN_DIR / 'repair_from_artifacts.py'),
        'python_executable': sys.executable, 'python_version': sys.version.replace('\n', ' '),
        'platform': f'{platform.system()} {platform.release()} {platform.machine()}',
        'command': f'"{sys.executable}" -X utf8 "{RUN_DIR / "repair_from_artifacts.py"}"',
        'libraries': {'numpy': np.__version__}, 'single_process_cpu': True, 'network_used': False,
        'gpu_used': False, 'compressed_inputs_opened': 0, 'raw_inputs_opened': 0,
        'original_run_modified': False, 'numeric_Q_computed': False, 'strategy_selected': False}
    write_json(RUN_DIR / 'environment.json', environment)
    phase = {'run_id': RUN_ID, 'phase': 'repair_from_artifacts',
             'status': 'COMPLETED' if anchor_ok else 'ANCHOR_MISMATCH',
             'errors': errors, 'event_cross_check_mismatches': mismatch, 'anchors': anchors,
             'tables': {'raw_field_counts_corrected': len(raw_corrected),
                        'raw_mask_corrections': len(packed_info['corrections']),
                        'missing_patterns_corrected': len(patterns_corrected),
                        'missing_pairwise_corrected': len(pairwise_corrected),
                        'summary_denominators_corrected': len(denominators_corrected),
                        'missing_concentration': len(concentration), 'changes': len(changes)},
             'rows': {'row_masks': packed_info['n_rows'], 'parsed': int((packed['flags'] & 1).sum())},
             'boundary_evidence': {'compressed_inputs_opened': 0, 'compressed_inputs_hashed': 0,
                                   'unchanged_columns_outside_permitted':
                                       packed_info['unchanged_column_diffs']},
             'numeric_Q_computed': False, 'strategy_selected': False}
    write_json(RUN_DIR / 'repair_phase_summary.json', phase)
    log(f'stage=done status={phase["status"]} errors={errors}')
    LOG.close()
    return 0 if anchor_ok and not errors and not mismatch else 2


if __name__ == '__main__':
    sys.exit(main())
