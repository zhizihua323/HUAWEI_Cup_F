#!/usr/bin/env python
"""TASK-G1 stage 1: freeze Q1 extension-conflict stability and seal a blinded author review package."""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy import stats

CST = timezone(timedelta(hours=8))
SEED = 20260925
BOOTSTRAP_REPLICATES = 2000
HIGH_CONFLICT_THRESHOLD = 0.5
PROJECT = Path(__file__).resolve().parents[4]
Q01C_RUN = PROJECT / 'solution' / 'outputs' / 'quality_q01c' / '20260924T215718+08'
T03E_RUN = PROJECT / 'diagnostics' / 'TASK-T03E' / '20260925T020032+08'
PARQUET = Q01C_RUN / 'quality_features_scores.parquet'
A1_SOURCE = PROJECT / 'F题' / 'real_attachments' / 'A_data_value' / 'slimpajama_quality_signal_sample.jsonl.xz'
A2_SOURCE = PROJECT / 'F题' / 'real_attachments' / 'A_data_value' / 'slimpajama_quality_extended' / 'arxiv_part-6777d8857c6e-000486.jsonl.xz'
A3_SOURCE = PROJECT / 'F题' / 'real_attachments' / 'A_data_value' / 'slimpajama_quality_extended' / 'github_part-6777d8857c6e-000275.jsonl.xz'
A18_SOURCE = PROJECT / 'F题' / 'real_attachments' / 'A_data_value' / 'regmix_domain_sample.jsonl.xz'
ACTIVE_DOMAINS = ['c4', 'commoncrawl', 'wikipedia']
SCOPE_ORDER = ['A1_sample', 'A2_extension', 'A3_extension', 'extension_overlap', 'extension_new', 'all_unique']
GROUP_COLUMNS = ['group_usability', 'group_knowledge', 'group_education_reasoning']
AUTHOR_COLUMNS = ['readability_1to5', 'completeness_1to5', 'contamination_0to2', 'overall_quality_1to5', 'review_notes_optional']
BLIND_COLUMNS = ['review_id', 'text_redacted'] + AUTHOR_COLUMNS
RUN_ID = '20260925T200018+08'


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec='seconds')


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode('utf-8'))


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def write_json_atomic(path: Path, payload) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def write_csv_atomic(path: Path, frame: pd.DataFrame) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    frame.to_csv(tmp, index=False, encoding='utf-8-sig', lineterminator='\n')
    os.replace(tmp, path)


def finite_values(values) -> np.ndarray:
    arr = pd.to_numeric(pd.Series(values), errors='coerce').to_numpy(dtype=float)
    return arr[np.isfinite(arr)]


def qstats(values) -> dict:
    a = finite_values(values)
    if a.size == 0:
        return {'n': 0, 'mean': None, 'median': None, 'std': None, 'q1': None, 'q3': None,
                'iqr': None, 'p10': None, 'p25': None, 'p50': None, 'p75': None, 'p90': None}
    q = np.quantile(a, [0.10, 0.25, 0.50, 0.75, 0.90])
    return {
        'n': int(a.size), 'mean': float(a.mean()), 'median': float(np.median(a)),
        'std': float(a.std(ddof=1)) if a.size >= 2 else None,
        'q1': float(q[1]), 'q3': float(q[3]), 'iqr': float(q[3] - q[1]),
        'p10': float(q[0]), 'p25': float(q[1]), 'p50': float(q[2]),
        'p75': float(q[3]), 'p90': float(q[4]),
    }

def conflict_direction_counts(part: pd.DataFrame) -> Counter:
    sub = part[GROUP_COLUMNS].apply(pd.to_numeric, errors='coerce')
    out = Counter()
    for _, row in sub.iterrows():
        vals = row.to_numpy(dtype=float)
        if not np.isfinite(vals).all():
            continue
        pairs = [(0, 1), (0, 2), (1, 2)]
        choices = []
        for i, j in pairs:
            delta = vals[i] - vals[j]
            name = f'{GROUP_COLUMNS[i]}__{GROUP_COLUMNS[j]}'
            choices.append((abs(delta), delta, name))
        _, delta, name = max(choices, key=lambda x: x[0])
        a, b = name.split('__')
        out[f'{a}>{b}' if delta > 0 else f'{b}>{a}'] += 1
    return out


def core_metrics(part: pd.DataFrame) -> dict:
    q = qstats(part['Q_baseline'])
    ranges = qstats(part['rater_disagreement_range'])
    stds = qstats(part['rater_disagreement_std'])
    defined = pd.to_numeric(part['rater_disagreement_range'], errors='coerce')
    hc = defined > HIGH_CONFLICT_THRESHOLD
    hc_den = int(defined.notna().sum())
    hc_n = int(hc.sum())
    row = {
        'n_physical': int(len(part)), 'n_unique': int(part['key_sha256'].nunique()),
        'n_Q_valid': q['n'], 'n_Q_missing': int(len(part) - q['n']),
        'coverage': float(q['n'] / len(part)) if len(part) else None,
        'Q_mean': q['mean'], 'Q_median': q['median'], 'Q_std': q['std'],
        'Q_q1': q['q1'], 'Q_q3': q['q3'], 'Q_iqr': q['iqr'],
        'Q_p10': q['p10'], 'Q_p25': q['p25'], 'Q_p50': q['p50'],
        'Q_p75': q['p75'], 'Q_p90': q['p90'],
        'high_conflict_n': hc_n, 'high_conflict_denominator': hc_den,
        'high_conflict_rate': float(hc_n / hc_den) if hc_den else None,
        'range_n': ranges['n'], 'range_mean': ranges['mean'], 'range_median': ranges['median'],
        'range_q1': ranges['q1'], 'range_q3': ranges['q3'], 'range_iqr': ranges['iqr'],
        'std_n': stds['n'], 'std_mean': stds['mean'], 'std_median': stds['median'],
        'std_q1': stds['q1'], 'std_q3': stds['q3'], 'std_iqr': stds['iqr'],
        'group_usability_mean': None, 'group_knowledge_mean': None,
        'group_education_reasoning_mean': None,
        'diff_usability_knowledge': None, 'diff_usability_education_reasoning': None,
        'diff_knowledge_education_reasoning': None,
        'max_abs_group_pair': None, 'group_direction': None,
        'dominant_conflict_pair': None, 'dominant_conflict_pair_coverage': None,
        'top2_conflict_pair_coverage': None,
    }
    versions = {c: qstats(part[c]) for c in GROUP_COLUMNS}
    for c in GROUP_COLUMNS:
        row[f'{c}_mean'] = versions[c]['mean']
    if all(versions[c]['n'] > 0 for c in GROUP_COLUMNS):
        u = versions['group_usability']['mean']
        k = versions['group_knowledge']['mean']
        e = versions['group_education_reasoning']['mean']
        diffs = {'usability__knowledge': u - k, 'usability__education_reasoning': u - e,
                 'knowledge__education_reasoning': k - e}
        row['diff_usability_knowledge'] = diffs['usability__knowledge']
        row['diff_usability_education_reasoning'] = diffs['usability__education_reasoning']
        row['diff_knowledge_education_reasoning'] = diffs['knowledge__education_reasoning']
        key, val = max(diffs.items(), key=lambda kv: abs(kv[1]))
        a, b = key.split('__')
        row['max_abs_group_pair'] = abs(val)
        row['group_direction'] = f'{a}>{b}' if val > 0 else f'{b}>{a}'
    counts = conflict_direction_counts(part)
    total = sum(counts.values())
    if total:
        ordered = counts.most_common()
        row['dominant_conflict_pair'] = ordered[0][0]
        row['dominant_conflict_pair_coverage'] = ordered[0][1] / total
        row['top2_conflict_pair_coverage'] = sum(n for _, n in ordered[:2]) / total
    return row


def make_scope_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        'A1_sample': (df['file_id'] == 'A1') & df['is_unique_first'],
        'A2_extension': df['file_id'] == 'A2_arxiv',
        'A3_extension': df['file_id'] == 'A3_github',
        'extension_overlap': df['overlap_a1'],
        'extension_new': (df['evaluation_role'] == 'extension_new_records') & df['is_unique_first'],
        'all_unique': df['is_unique_first'],
    }


def scope_denominators(df: pd.DataFrame, masks: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for scope in SCOPE_ORDER:
        part = df[masks[scope]]
        q_ok = part['Q_valid'] & pd.to_numeric(part['Q_baseline'], errors='coerce').notna()
        domains = set(part['domain'].dropna().astype(str))
        rows.append({
            'scope': scope, 'physical_rows': int(len(part)), 'unique_keys': int(part['key_sha256'].nunique()),
            'Q_valid': int(q_ok.sum()), 'Q_missing': int((~q_ok).sum()),
            'coverage': float(q_ok.mean()) if len(part) else None,
            'domain_count': int(len(domains)), 'active_domain_count': int(len(domains & set(ACTIVE_DOMAINS))),
            'overlap_rows_excluded_from_all_unique': int(11419 if scope == 'all_unique' else 0),
            'definition': {
                'A1_sample': 'file_id=A1 & is_unique_first',
                'A2_extension': 'file_id=A2_arxiv; physical rows are unique within A1->A2 read order',
                'A3_extension': 'file_id=A3_github; physical rows are unique within A1->A3 read order',
                'extension_overlap': 'overlap_a1=True extension occurrences only',
                'extension_new': 'evaluation_role=extension_new_records & is_unique_first',
                'all_unique': 'is_unique_first; overlap occurrences excluded from denominator',
            }[scope],
        })
    return pd.DataFrame(rows)

def stability_summary_rows(df: pd.DataFrame, masks: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for scope in SCOPE_ORDER:
        part = df[masks[scope]]
        data_sets = [('ALL', part), ('ACTIVE_DOMAIN', part[part['domain'].isin(ACTIVE_DOMAINS)])]
        for subset_type, sub in data_sets:
            row = {'scope': scope, 'subset_type': subset_type,
                   'subset': 'ALL' if subset_type == 'ALL' else '|'.join(ACTIVE_DOMAINS)}
            row.update(core_metrics(sub))
            row['domain_count_subset'] = int(sub['domain'].nunique())
            rows.append(row)
    return pd.DataFrame(rows)


def domain_table(df: pd.DataFrame, masks: dict[str, pd.Series], all_high_rate: float | None) -> pd.DataFrame:
    rows = []
    for scope in SCOPE_ORDER:
        for domain, sub in df[masks[scope]].groupby('domain', dropna=False):
            row = {'scope': scope, 'domain': str(domain), 'is_active_domain': str(domain) in ACTIVE_DOMAINS}
            row.update(core_metrics(sub))
            if row['high_conflict_rate'] is None or all_high_rate is None:
                row['direction_vs_all_unique'] = None
            elif row['high_conflict_rate'] > all_high_rate:
                row['direction_vs_all_unique'] = 'HIGH'
            elif row['high_conflict_rate'] < all_high_rate:
                row['direction_vs_all_unique'] = 'LOW'
            else:
                row['direction_vs_all_unique'] = 'EQUAL'
            rows.append(row)
    return pd.DataFrame(rows)


def distribution_distances(df: pd.DataFrame, masks: dict[str, pd.Series]) -> pd.DataFrame:
    pairs = [('A1_sample', 'A2_extension'), ('A1_sample', 'A3_extension'), ('A1_sample', 'all_unique'),
             ('A2_extension', 'A3_extension'), ('A2_extension', 'all_unique'),
             ('A3_extension', 'all_unique'), ('extension_overlap', 'extension_new')]
    rows = []
    for a, b in pairs:
        x = finite_values(df.loc[masks[a], 'Q_baseline'])
        y = finite_values(df.loc[masks[b], 'Q_baseline'])
        if x.size and y.size:
            ks = float(stats.ks_2samp(x, y, alternative='two-sided', method='asymp').statistic)
            wd = float(stats.wasserstein_distance(x, y))
        else:
            ks = None
            wd = None
        rows.append({'scope_a': a, 'scope_b': b, 'n_a': int(x.size), 'n_b': int(y.size),
                     'ks_statistic': ks, 'wasserstein_distance': wd,
                     'interpretation_limit': 'descriptive frozen-result distance only; p-values are not used for stability decisions'})
    return pd.DataFrame(rows)


def global_stability_decision(df: pd.DataFrame, masks: dict[str, pd.Series], domains: pd.DataFrame) -> dict:
    a1 = core_metrics(df[masks['A1_sample']])
    reports = {}
    for ext in ['A2_extension', 'A3_extension']:
        x = core_metrics(df[masks[ext]])
        criteria = {
            'high_conflict_rate_absdiff_le_0_05': abs(x['high_conflict_rate'] - a1['high_conflict_rate']) <= 0.05,
            'range_median_absdiff_le_0_10': abs(x['range_median'] - a1['range_median']) <= 0.10,
            'std_median_absdiff_le_0_05': abs(x['std_median'] - a1['std_median']) <= 0.05,
            'conflict_pair_consistent': (x['dominant_conflict_pair'] == a1['dominant_conflict_pair']) or
                                        (abs(x['top2_conflict_pair_coverage'] - a1['top2_conflict_pair_coverage']) <= 0.10),
        }
        n_pass = int(sum(criteria.values()))
        a1d = domains[(domains.scope == 'A1_sample') & domains.high_conflict_rate.notna()][['domain', 'high_conflict_rate', 'direction_vs_all_unique']]
        ed = domains[(domains.scope == ext) & domains.high_conflict_rate.notna()][['domain', 'high_conflict_rate', 'direction_vs_all_unique']]
        common = a1d.merge(ed, on='domain', suffixes=('_a1', '_ext')).sort_values('domain')
        if len(common) >= 4:
            rho = float(stats.spearmanr(common['high_conflict_rate_a1'], common['high_conflict_rate_ext']).statistic)
            consistent = (common['direction_vs_all_unique_a1'] == common['direction_vs_all_unique_ext'])
            direction_rate = float(consistent.mean())
            domain_pass = bool(np.isfinite(rho) and rho >= 0.50 and direction_rate >= 0.70)
            domain_status = 'EVALUABLE'
        else:
            rho = None
            direction_rate = None
            domain_pass = False
            domain_status = 'NOT_EVALUABLE'
        reports[ext] = {
            'global_criteria': criteria, 'global_pass_count': n_pass, 'common_domain_count': int(len(common)),
            'common_domain_high_conflict_spearman': rho,
            'common_domain_direction_consistency_rate': direction_rate,
            'domain_level_status': domain_status, 'domain_level_pass': domain_pass,
            'qualified': bool(n_pass >= 3 and domain_pass),
            'group_direction': x['group_direction'], 'a1_group_direction': a1['group_direction']}
    a2, a3 = reports['A2_extension'], reports['A3_extension']
    a1_pair = a1['group_direction']
    def opposite(pair):
        if not pair or '>' not in pair:
            return None
        left, right = pair.split('>', 1)
        return f'{right}>{left}'
    reversal = bool(a2['group_direction'] == opposite(a1_pair) and a3['group_direction'] == opposite(a1_pair))
    if a2['qualified'] and a3['qualified']:
        status = 'STABLE'
    elif (a2['global_pass_count'] < 3 and a3['global_pass_count'] < 3) or reversal:
        status = 'NOT_STABLE'
    else:
        status = 'PARTIALLY_STABLE'
    if status == 'PARTIALLY_STABLE' and 'NOT_EVALUABLE' in [a2['domain_level_status'], a3['domain_level_status']]:
        note = 'PARTIALLY_STABLE because at least one domain-level test is not evaluable and no consistent reversal was observed.'
    else:
        note = f'Decision follows preregistered global and domain-level gates. a1_group_direction={a1_pair}.'
    return {'status': status, 'a1_metrics': a1, 'extension_reports': reports,
            'consistent_direction_reversal': reversal, 'decision_note': note,
            'high_conflict_threshold': HIGH_CONFLICT_THRESHOLD}


def q01c_high_conflict_threshold() -> float:
    text = (Q01C_RUN / 'code_snapshot' / 'quality_q01c.py').read_text(encoding='utf-8')
    m = re.search(r'boolean_defined\s*=\s*ranges\s*>\s*([0-9.]+)', text)
    if not m:
        raise RuntimeError('cannot recover Q01C high-conflict threshold from frozen code')
    return float(m.group(1))

def bootstrap_draws(rng: np.random.Generator, part: pd.DataFrame, replicates: int) -> dict[str, np.ndarray]:
    domains = sorted(part['domain'].dropna().astype(str).unique())
    q_parts, rng_parts, std_parts = [], [], []
    for d in domains:
        sub = part[part['domain'].astype(str) == d]
        q_parts.append(finite_values(sub['Q_baseline']))
        rng_parts.append(finite_values(sub['rater_disagreement_range']))
        std_parts.append(finite_values(sub['rater_disagreement_std']))
    metrics = {k: np.empty(replicates, dtype=float) for k in
               ['Q_mean', 'Q_median', 'Q_std', 'high_conflict_rate', 'range_median', 'std_median']}
    for rep in range(replicates):
        q = np.concatenate([a[rng.integers(0, a.size, a.size)] if a.size else a for a in q_parts]) if any(a.size for a in q_parts) else np.array([], dtype=float)
        rr = np.concatenate([a[rng.integers(0, a.size, a.size)] if a.size else a for a in rng_parts]) if any(a.size for a in rng_parts) else np.array([], dtype=float)
        ss = np.concatenate([a[rng.integers(0, a.size, a.size)] if a.size else a for a in std_parts]) if any(a.size for a in std_parts) else np.array([], dtype=float)
        metrics['Q_mean'][rep] = q.mean() if q.size else np.nan
        metrics['Q_median'][rep] = np.median(q) if q.size else np.nan
        metrics['Q_std'][rep] = q.std(ddof=1) if q.size >= 2 else np.nan
        metrics['high_conflict_rate'][rep] = (rr > HIGH_CONFLICT_THRESHOLD).mean() if rr.size else np.nan
        metrics['range_median'][rep] = np.median(rr) if rr.size else np.nan
        metrics['std_median'][rep] = np.median(ss) if ss.size else np.nan
    return metrics


def bootstrap_stability(df: pd.DataFrame, masks: dict[str, pd.Series]) -> tuple[pd.DataFrame, dict[str, dict[str, np.ndarray]]]:
    draws, rng = {}, np.random.default_rng(SEED)
    for scope in SCOPE_ORDER:
        draws[scope] = bootstrap_draws(rng, df[masks[scope]], BOOTSTRAP_REPLICATES)
    rows = []
    for scope in SCOPE_ORDER:
        estimate = core_metrics(df[masks[scope]])
        for metric, values in draws[scope].items():
            vals = values[np.isfinite(values)]
            rows.append({'record_type': 'scope_interval', 'scope_a': scope, 'scope_b': '', 'metric': metric,
                         'estimate': estimate.get(metric), 'difference_estimate': None,
                         'bootstrap_median': float(np.median(vals)) if vals.size else None,
                         'ci_low_2_5pct': float(np.quantile(vals, 0.025)) if vals.size else None,
                         'ci_high_97_5pct': float(np.quantile(vals, 0.975)) if vals.size else None,
                         'share_gt_zero': None, 'replicates_requested': BOOTSTRAP_REPLICATES,
                         'replicates_finite': int(vals.size), 'seed': SEED,
                         'sampling_rule': 'domain-stratified unique-key resampling with replacement'})
    comparisons = [('A2_extension', 'A1_sample'), ('A3_extension', 'A1_sample'),
                   ('extension_overlap', 'extension_new'), ('all_unique', 'A1_sample')]
    for a, b in comparisons:
        est_a, est_b = core_metrics(df[masks[a]]), core_metrics(df[masks[b]])
        for metric in draws[a]:
            diff = draws[a][metric] - draws[b][metric]
            vals = diff[np.isfinite(diff)]
            rows.append({'record_type': 'difference_interval', 'scope_a': a, 'scope_b': b, 'metric': metric,
                         'estimate': est_a.get(metric),
                         'difference_estimate': (est_a.get(metric) - est_b.get(metric)) if est_a.get(metric) is not None and est_b.get(metric) is not None else None,
                         'bootstrap_median': float(np.median(vals)) if vals.size else None,
                         'ci_low_2_5pct': float(np.quantile(vals, 0.025)) if vals.size else None,
                         'ci_high_97_5pct': float(np.quantile(vals, 0.975)) if vals.size else None,
                         'share_gt_zero': float((vals > 0).mean()) if vals.size else None,
                         'replicates_requested': BOOTSTRAP_REPLICATES, 'replicates_finite': int(vals.size), 'seed': SEED,
                         'sampling_rule': 'independent domain-stratified unique-key resampling with replacement'})
    return pd.DataFrame(rows), draws

def parse_a18_and_text_join(df: pd.DataFrame, masks: dict[str, pd.Series]) -> pd.DataFrame:
    a1_meta = df.loc[masks['A1_sample'], ['key_sha256', 'domain']].drop_duplicates('key_sha256')
    a1_keys = set(a1_meta['key_sha256'])
    a1_hash_to_keys = defaultdict(set)
    a1_rows = a1_nonempty = a1_matched = 0
    with lzma.open(A1_SOURCE, 'rt', encoding='utf-8') as fh:
        for line in fh:
            a1_rows += 1
            x = json.loads(line)
            key = sha256_text(json.dumps((str(x.get('id', '')), str(x.get('sub_path', ''))), ensure_ascii=False, separators=(',', ':')))
            content = x.get('content')
            if isinstance(content, str) and content:
                a1_nonempty += 1
                a1_hash_to_keys[sha256_text(content)].add(key)
            if key in a1_keys:
                a1_matched += 1
    a1_domains = a1_meta['domain'].nunique()

    a18_rows = a18_blank = 0
    a18_hash_counts = Counter()
    a18_hash_domains = defaultdict(Counter)
    with lzma.open(A18_SOURCE, 'rt', encoding='utf-8') as fh:
        for line in fh:
            a18_rows += 1
            x = json.loads(line)
            text = x.get('text')
            if not isinstance(text, str) or not text:
                a18_blank += 1
                continue
            h = sha256_text(text)
            a18_hash_counts[h] += 1
            a18_hash_domains[h][str(x.get('_source_domain', ''))] += 1
    matched = set(a18_hash_counts) & set(a1_hash_to_keys)
    matched_a18 = int(sum(a18_hash_counts[h] for h in matched))
    matched_keys = set()
    for h in matched:
        matched_keys.update(a1_hash_to_keys[h])
    one_one = sum(1 for h in matched if a18_hash_counts[h] == 1 and len(a1_hash_to_keys[h]) == 1)
    one_many = sum(1 for h in matched if a18_hash_counts[h] == 1 and len(a1_hash_to_keys[h]) > 1)
    many_one = sum(1 for h in matched if a18_hash_counts[h] > 1 and len(a1_hash_to_keys[h]) == 1)
    many_many = sum(1 for h in matched if a18_hash_counts[h] > 1 and len(a1_hash_to_keys[h]) > 1)
    a18_domains = sorted({d for c in a18_hash_domains.values() for d in c})
    rows = [
        {'candidate_id': 'A18_regmix_domain_sample', 'path': str(A18_SOURCE.relative_to(PROJECT)).replace('\\', '/'),
         'join_method': 'exact sha256(text) to A1 content only', 'total_rows': a18_rows,
         'unique_candidate_keys': int(len(a18_hash_counts)), 'matching_q01c_keys': int(len(matched_keys)),
         'matched_candidate_rows': matched_a18, 'one_to_one_pairs': int(one_one),
         'one_to_many_pairs': int(one_many), 'many_to_one_pairs': int(many_one),
         'many_to_many_pairs': int(many_many), 'text_nonempty_rows': int(a18_rows - a18_blank),
         'text_nonempty_rate': float((a18_rows - a18_blank) / a18_rows),
         'mapped_domains': '|'.join(a18_domains), 'join_status': 'TEXT_JOINABLE_NOT_SELECTED',
         'decision_note': 'Exact content match exists, but the frozen mapping guide has only 3 direct quality-domain labels and exact join to Q01C A1 reaches only 1 key; it cannot supply 6 domains without fuzzy/alias mapping.'},
        {'candidate_id': 'Q01C_A1_raw_source', 'path': str(A1_SOURCE.relative_to(PROJECT)).replace('\\', '/'),
         'join_method': 'frozen key_sha256(id,sub_path) plus exact content', 'total_rows': a1_rows,
         'unique_candidate_keys': int(len(a1_hash_to_keys)), 'matching_q01c_keys': int(a1_matched),
         'matched_candidate_rows': int(a1_matched), 'one_to_one_pairs': int(a1_nonempty),
         'one_to_many_pairs': 0, 'many_to_one_pairs': 0, 'many_to_many_pairs': 0,
         'text_nonempty_rows': int(a1_nonempty), 'text_nonempty_rate': float(a1_nonempty / a1_rows),
         'mapped_domains': int(a1_domains), 'join_status': 'SELECTED_ONE_TO_ONE',
         'decision_note': 'Direct Q01C source; every A1 sample key has source content and no fuzzy matching is used.'}
    ]
    for label, path in [('Q01C_A2_raw_source', A2_SOURCE), ('Q01C_A3_raw_source', A3_SOURCE)]:
        key_col = 'A2_extension' if label == 'Q01C_A2_raw_source' else 'A3_extension'
        expected = set(df.loc[masks[key_col], 'key_sha256'])
        total = nonempty = matched_count = 0
        with lzma.open(path, 'rt', encoding='utf-8') as fh:
            for line in fh:
                total += 1
                x = json.loads(line)
                key = sha256_text(json.dumps((str(x.get('id', '')), str(x.get('sub_path', ''))), ensure_ascii=False, separators=(',', ':')))
                if key in expected:
                    matched_count += 1
                content = x.get('content')
                if isinstance(content, str) and content:
                    nonempty += 1
        rows.append({'candidate_id': label, 'path': str(path.relative_to(PROJECT)).replace('\\', '/'),
                     'join_method': 'frozen key_sha256(id,sub_path)', 'total_rows': total,
                     'unique_candidate_keys': total, 'matching_q01c_keys': matched_count,
                     'matched_candidate_rows': matched_count, 'one_to_one_pairs': 0, 'one_to_many_pairs': 0,
                     'many_to_one_pairs': 0, 'many_to_many_pairs': 0, 'text_nonempty_rows': nonempty,
                     'text_nonempty_rate': float(nonempty / total) if total else None,
                     'mapped_domains': int(df.loc[masks[key_col], 'domain'].nunique()),
                     'join_status': 'TEXT_ABSENT' if nonempty == 0 else 'KEY_JOINABLE_TEXT_PRESENT',
                     'decision_note': 'The extension source records do not carry a content field, so they cannot supply author-review text.'})
    return pd.DataFrame(rows)

def redact_text(text: str) -> tuple[str, int]:
    replacements = 0
    def sub(pattern, repl, value):
        nonlocal replacements
        new, n = re.subn(pattern, repl, value)
        replacements += n
        return new
    out = text.replace('\r\n', '\n').replace('\r', '\n').replace('\x00', '')
    out = sub(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[EMAIL_REDACTED]', out)
    out = sub(r'(?i)\bhttps?://[^\s<>"\']+', '[URL_REDACTED]', out)
    out = sub(r'(?i)\bwww\.[^\s<>"\']+', '[URL_REDACTED]', out)
    return out, replacements


def sample_blind_package(df: pd.DataFrame, masks: dict[str, pd.Series]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    a1 = df.loc[masks['A1_sample']].copy()
    a1 = a1[a1['Q_valid'] & pd.to_numeric(a1['Q_baseline'], errors='coerce').notna()].copy()
    a1['domain_q25'] = a1.groupby('domain')['Q_baseline'].transform(lambda x: x.quantile(0.25))
    a1['domain_q75'] = a1.groupby('domain')['Q_baseline'].transform(lambda x: x.quantile(0.75))
    a1['q_high_domain'] = a1['Q_baseline'] >= a1['domain_q75']
    a1['q_low_domain'] = a1['Q_baseline'] <= a1['domain_q25']
    a1['high_conflict'] = pd.to_numeric(a1['rater_disagreement_range'], errors='coerce') > HIGH_CONFLICT_THRESHOLD
    a1['low_conflict'] = ~a1['high_conflict']
    strata = {
        'highQ_lowConflict': {'n': 20, 'mask': a1['q_high_domain'] & a1['low_conflict']},
        'lowQ_lowConflict': {'n': 20, 'mask': a1['q_low_domain'] & a1['low_conflict']},
        'highConflict_highQ': {'n': 10, 'mask': a1['high_conflict'] & a1['q_high_domain']},
        'highConflict_lowQ': {'n': 10, 'mask': a1['high_conflict'] & a1['q_low_domain']},
    }
    selected, quota_report = [], {}
    for stratum, spec in strata.items():
        sub = a1[spec['mask']].copy()
        pools = {}
        for domain, g in sub.groupby('domain'):
            tag = f'{SEED}|{stratum}|{domain}'
            seed_material = int.from_bytes(hashlib.sha256(tag.encode('utf-8')).digest()[:8], 'big')
            vals = g.sort_values('key_sha256')['key_sha256'].tolist()
            order = np.random.default_rng(seed_material).permutation(len(vals))
            pools[str(domain)] = [vals[i] for i in order]
        chosen = []
        cursor = {d: 0 for d in pools}
        while len(chosen) < spec['n']:
            progressed = False
            for domain in sorted(pools):
                if len(chosen) >= spec['n']:
                    break
                if cursor[domain] < len(pools[domain]):
                    chosen.append(pools[domain][cursor[domain]])
                    cursor[domain] += 1
                    progressed = True
            if not progressed:
                break
        if len(chosen) != spec['n']:
            raise RuntimeError(f'cannot satisfy frozen quota {stratum}: {len(chosen)}/{spec["n"]}')
        selected.extend((key, stratum) for key in chosen)
        quota_report[stratum] = {'target': int(spec['n']), 'selected': int(len(chosen))}
    if len(selected) < 48 or len(selected) > 60:
        raise RuntimeError(f'sealed blind sample size outside allowed range: {len(selected)}')
    order_rng = np.random.default_rng(SEED)
    selected = [selected[i] for i in order_rng.permutation(len(selected))]
    key_to_meta = a1.set_index('key_sha256').to_dict('index')
    rows = []
    for idx, (key, stratum) in enumerate(selected):
        meta = key_to_meta[key]
        rows.append({'review_id': f'G1-{idx + 1:03d}', 'key_sha256': key, 'domain': meta['domain'],
                     'file_id': meta['file_id'], 'sampling_stratum': stratum,
                     'Q_baseline': float(meta['Q_baseline']), 'q_high_domain': bool(meta['q_high_domain']),
                     'q_low_domain': bool(meta['q_low_domain']), 'high_conflict': bool(meta['high_conflict'])})
    sample_keys = {r['key_sha256'] for r in rows}
    texts = {}
    with lzma.open(A1_SOURCE, 'rt', encoding='utf-8') as fh:
        for line in fh:
            x = json.loads(line)
            key = sha256_text(json.dumps((str(x.get('id', '')), str(x.get('sub_path', ''))), ensure_ascii=False, separators=(',', ':')))
            if key in sample_keys:
                texts[key] = x.get('content')
    if set(texts) != sample_keys:
        raise RuntimeError('not all selected source texts could be reconstructed')
    records = []
    for row in rows:
        original = texts[row['key_sha256']]
        redacted, redactions = redact_text(original)
        records.append({**row, 'text_redacted': redacted, 'redaction_count': int(redactions),
                        'original_text_sha256': sha256_text(original), 'redacted_text_sha256': sha256_text(redacted)})
    seal_records = [{k: r[k] for k in ['review_id', 'key_sha256', 'domain', 'sampling_stratum',
                                      'original_text_sha256', 'redacted_text_sha256', 'redaction_count']} for r in records]
    domain_counts = Counter(r['domain'] for r in records)
    max_permitted = math.floor(0.20 * len(records))
    if len(domain_counts) < 6:
        raise RuntimeError(f'blind sample covers only {len(domain_counts)} domains')
    if max(domain_counts.values()) > max_permitted:
        raise RuntimeError('blind sample violates 20% single-domain cap')
    seal = {'task': 'TASK-G1', 'seal_version': 'g1_text_blind_seal_v1', 'generated_local': now_iso(),
            'seed': SEED, 'sampling_frame': 'Q01C A1_sample with Q_valid=True and finite Q_baseline',
            'high_conflict_threshold': HIGH_CONFLICT_THRESHOLD,
            'q_grouping': 'within-domain Q quartiles: high >= q75, low <= q25',
            'target_n': 60, 'actual_n': len(records), 'quota_report': quota_report,
            'domain_counts': dict(sorted(domain_counts.items())), 'single_domain_cap': max_permitted,
            'text_source': str(A1_SOURCE.relative_to(PROJECT)).replace('\\', '/'),
            'join_rule': 'frozen key_sha256(id,sub_path), exact direct source mapping',
            'redaction_rule': 'only email/URL masking and CR/control normalization; no rewriting',
            'records': seal_records, 'ratings_generated_by_executor': False,
            'seal_statement': 'This seal was written before manual_text_review_blind.csv and before any author ratings.'}
    key_df = pd.DataFrame(records)[['review_id', 'key_sha256', 'domain', 'file_id', 'sampling_stratum',
                                    'Q_baseline', 'q_high_domain', 'q_low_domain', 'high_conflict',
                                    'original_text_sha256', 'redacted_text_sha256', 'redaction_count']]
    blind = pd.DataFrame([{'review_id': r['review_id'], 'text_redacted': r['text_redacted'],
                           **{c: '' for c in AUTHOR_COLUMNS}} for r in records], columns=BLIND_COLUMNS)
    return blind, key_df, seal

def environment_payload(run_id: str) -> dict:
    return {'run_id': run_id, 'generated_local': now_iso(), 'python_version': sys.version,
            'python_executable': sys.executable, 'platform': platform.platform(),
            'processor': platform.processor(), 'cpu_count': os.cpu_count(),
            'numpy': np.__version__, 'pandas': pd.__version__, 'scipy': scipy.__version__,
            'project_root': str(PROJECT), 'timezone': 'Asia/Shanghai'}


def build_input_manifest(run_id: str) -> dict:
    paths = [
        (PARQUET, 'Q01C primary scored parquet', 'official frozen input'),
        (Q01C_RUN / 'domain_summary.csv', 'Q01C domain summary', 'official frozen input'),
        (Q01C_RUN / 'summary_denominators.csv', 'Q01C denominator summary', 'official frozen input'),
        (Q01C_RUN / 'run_config.json', 'Q01C config', 'official frozen input'),
        (Q01C_RUN / 'input_manifest.json', 'Q01C input manifest', 'official frozen input'),
        (Q01C_RUN / 'output_manifest.json', 'Q01C output manifest', 'official frozen input'),
        (Q01C_RUN / 'code_snapshot' / 'quality_q01c.py', 'Q01C frozen code', 'definition authority'),
        (T03E_RUN / 'run_config.json', 'T03E config and active-domain freeze', 'official frozen input'),
        (T03E_RUN / 'phase_b_frozen_validation' / 'extension_overlap_validation.csv', 'T03E overlap evidence', 'official frozen input'),
        (T03E_RUN / 'phase_b_frozen_validation' / 'extension_new_validation.csv', 'T03E extension evidence', 'official frozen input'),
        (T03E_RUN / 'phase_b_frozen_validation' / 'actual_domain_labels_all_roles.csv', 'T03E domain labels', 'official frozen input'),
        (A1_SOURCE, 'Q01C A1 raw source', 'direct text source'),
        (A2_SOURCE, 'Q01C A2 raw source', 'text-join audit candidate'),
        (A3_SOURCE, 'Q01C A3 raw source', 'text-join audit candidate'),
        (A18_SOURCE, 'A18 optional text sample', 'text-join audit candidate')]
    entries = []
    for path, role, scope in paths:
        entries.append({'path': str(path.relative_to(PROJECT)).replace('\\', '/'), 'bytes': path.stat().st_size,
                        'mtime': path.stat().st_mtime, 'sha256': sha256_file(path), 'role': role, 'scope': scope})
    return {'run_id': run_id, 'generated_local': now_iso(), 'project_root': str(PROJECT),
            'inputs': entries, 'hash_algorithm': 'sha256', 'read_only': True}


def snapshot_protected() -> dict:
    result = {'q01c_run': {}, 't03e_run': {}, 'root_docs': {}, 'paper_files': {}}
    for root in [Q01C_RUN, T03E_RUN]:
        key = 'q01c_run' if root == Q01C_RUN else 't03e_run'
        for p in sorted(x for x in root.rglob('*') if x.is_file()):
            result[key][str(p.relative_to(PROJECT)).replace('\\', '/')] = {'bytes': p.stat().st_size, 'sha256': sha256_file(p)}
    names = [(0, 'PROJECT_BRIEF'), (1, 'PROJECT_STATUS'), (2, 'DECISIONS'), (3, 'DATA_CATALOG'), (4, 'TASK_QUEUE'), (5, 'REVIEW_LOG')]
    for i, name in names:
        p = PROJECT / f'{i:02d}_{name}.md'
        result['root_docs'][p.name] = {'bytes': p.stat().st_size, 'sha256': sha256_file(p)}
    for p in sorted(x for x in (PROJECT / 'paper').rglob('*') if x.is_file()):
        result['paper_files'][str(p.relative_to(PROJECT)).replace('\\', '/')] = {'bytes': p.stat().st_size, 'sha256': sha256_file(p)}
    return result


def compare_protected(before: dict, after: dict) -> dict:
    changes = {}
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key, {}), after.get(key, {})
        changed = []
        for rel in sorted(set(b) | set(a)):
            if b.get(rel, {}).get('sha256') != a.get(rel, {}).get('sha256'):
                changed.append({'path': rel, 'before': b.get(rel), 'after': a.get(rel)})
        changes[key] = changed
    return changes

def check_item(name: str, passed: bool, details) -> dict:
    return {'check': name, 'status': 'PASS' if passed else 'FAIL', 'details': details}


def build_checks(df, masks, denoms, text_audit, seal, blind, protected_changes, verification):
    q_invalid = int((~df['Q_valid']).sum())
    overlap_keys = set(df.loc[masks['extension_overlap'], 'key_sha256'])
    ext_overlap = pd.read_csv(T03E_RUN / 'phase_b_frozen_validation' / 'extension_overlap_validation.csv')
    overlap_evidence = set(ext_overlap['key_sha256'].astype(str))
    selected_blind = set(blind['review_id'])
    seal_ids = {r['review_id'] for r in seal['records']}
    author_values = blind[AUTHOR_COLUMNS]
    author_values_nonblank = int(((author_values.notna()) & (~author_values.isin([None, '']))).sum().sum())
    forbidden = [c for c in blind.columns if any(token in c.lower() for token in ['q_baseline', 'conflict', 'group_', 'key_sha256', 'domain'])]
    checks = [
        check_item('Q01C_T03E_protected_hashes_unchanged', all(not v for v in protected_changes.values()), protected_changes),
        check_item('Q01C_row_count_272505', len(df) == 272505, {'rows': int(len(df))}),
        check_item('unique_keys_261086', int(df['is_unique_first'].sum()) == 261086, {'unique': int(df['is_unique_first'].sum())}),
        check_item('Q_invalid_19', q_invalid == 19 and int((~df.loc[df.is_unique_first, 'Q_valid']).sum()) == 19,
                   {'physical_invalid': q_invalid, 'unique_invalid': int((~df.loc[df.is_unique_first, 'Q_valid']).sum())}),
        check_item('overlap_11419_removed_from_all_unique', len(overlap_keys) == 11419 and overlap_evidence == overlap_keys,
                   {'q01c_overlap_keys': len(overlap_keys), 't03e_overlap_keys': len(overlap_evidence), 'intersection': len(overlap_keys & overlap_evidence)}),
        check_item('high_conflict_threshold_frozen_0_5', q01c_high_conflict_threshold() == HIGH_CONFLICT_THRESHOLD,
                   {'threshold': HIGH_CONFLICT_THRESHOLD, 'source': 'Q01C summarize_scope boolean_defined = ranges > 0.5'}),
        check_item('scope_denominators_constructed',
                   set(denoms.scope) == set(SCOPE_ORDER) and int(denoms.loc[denoms.scope.eq('all_unique'), 'physical_rows'].iloc[0]) == 261086,
                   denoms[['scope', 'physical_rows', 'unique_keys', 'Q_valid', 'Q_missing']].to_dict(orient='records')),
        check_item('text_join_audit_has_selected_direct_source',
                   bool(((text_audit.candidate_id == 'Q01C_A1_raw_source') & (text_audit.join_status == 'SELECTED_ONE_TO_ONE')).any()),
                   text_audit.to_dict(orient='records')),
        check_item('blind_sample_size_48_to_60', 48 <= int(seal['actual_n']) <= 60, {'actual_n': int(seal['actual_n'])}),
        check_item('blind_review_ids_sealed_unique',
                   len(selected_blind) == len(blind) == len(seal_ids) and selected_blind == seal_ids,
                   {'blind': len(selected_blind), 'seal': len(seal_ids)}),
        check_item('blind_has_no_Q_conflict_key_or_domain_columns', not forbidden, {'forbidden_columns': forbidden, 'columns': list(blind.columns)}),
        check_item('author_rating_columns_blank_no_AI_ratings', author_values_nonblank == 0, {'nonblank_cells': author_values_nonblank}),
        check_item('sampling_domain_coverage_and_cap',
                   len(seal['domain_counts']) >= 6 and max(seal['domain_counts'].values()) <= seal['single_domain_cap'],
                   {'domain_counts': seal['domain_counts'], 'cap': seal['single_domain_cap']}),
        check_item('independent_verifier_passed', verification.get('status') == 'PASS',
                   {'status': verification.get('status'), 'fail_count': verification.get('summary', {}).get('fail')}),
    ]
    summary = {'total': len(checks), 'pass': sum(c['status'] == 'PASS' for c in checks),
               'fail': sum(c['status'] == 'FAIL' for c in checks), 'not_checked': 0}
    return {'run_id': RUN_ID, 'generated_local': now_iso(), 'summary': summary, 'checks': checks}


def copy_code_snapshot(run_dir: Path) -> None:
    dst = run_dir / 'code_snapshot'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(run_dir / 'code', dst)


def write_manifest(run_dir: Path, run_id: str, status: str, verification: dict) -> dict:
    entries = []
    for p in sorted(x for x in run_dir.rglob('*') if x.is_file() and x.name != 'output_manifest.json' and not x.name.endswith('.tmp')):
        entries.append({'path': str(p.relative_to(run_dir)).replace('\\', '/'), 'bytes': p.stat().st_size, 'sha256': sha256_file(p)})
    payload = {'run_id': run_id, 'task': 'TASK-G1', 'status': status, 'generated_local': now_iso(),
               'manifest_is_last_registered_artifact': True, 'output_manifest_excluded_from_self_hash': True,
               'registered_file_count': len(entries), 'registered_files': entries,
               'blind_sha256': next(e['sha256'] for e in entries if e['path'] == 'manual_text_review_blind.csv'),
               'sampling_seal_sha256': next(e['sha256'] for e in entries if e['path'] == 'sampling_seal.json'),
               'verification_status': verification.get('status'), 'post_author_review_required': True,
               'no_manual_ratings_generated': True}
    write_json_atomic(run_dir / 'output_manifest.json', payload)
    return payload

def main() -> int:
    global RUN_ID
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    RUN_ID = run_dir.name
    start = time.time()
    stage_path = run_dir / 'stage_status.jsonl'
    seen_stages = []

    def stage(name: str, phase: str, **details):
        rec = {'run_id': RUN_ID, 'timestamp': now_iso(), 'stage': name, 'status': phase, **details}
        with stage_path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n')
        seen_stages.append(rec)

    try:
        stage('s00_preflight', 'start')
        if q01c_high_conflict_threshold() != HIGH_CONFLICT_THRESHOLD:
            raise RuntimeError('Q01C frozen threshold changed')
        env = environment_payload(RUN_ID)
        write_json_atomic(run_dir / 'environment.json', env)
        input_manifest = build_input_manifest(RUN_ID)
        write_json_atomic(run_dir / 'input_manifest.json', input_manifest)
        protected_before = snapshot_protected()
        write_json_atomic(run_dir / 'protected_before.json', protected_before)
        stage('s00_preflight', 'complete', inputs=len(input_manifest['inputs']),
              protected_files=sum(len(v) for v in protected_before.values()))

        stage('s10_conflict_stability', 'start')
        columns = ['key_sha256', 'file_id', 'source_line', 'id_json', 'sub_path_json', 'domain', 'domain_source',
                   'is_unique_first', 'overlap_a1', 'evaluation_role', 'Q_valid', 'Q_baseline',
                   'rater_disagreement_range', 'rater_disagreement_std'] + GROUP_COLUMNS
        df = pd.read_parquet(PARQUET, columns=columns)
        masks = make_scope_masks(df)
        denoms = scope_denominators(df, masks)
        summary = stability_summary_rows(df, masks)
        all_rate = float(core_metrics(df[masks['all_unique']])['high_conflict_rate'])
        domains = domain_table(df, masks, all_rate)
        decisions = global_stability_decision(df, masks, domains)
        distances = distribution_distances(df, masks)
        boot, draws = bootstrap_stability(df, masks)
        overlap_new = summary[summary.scope.isin(['extension_overlap', 'extension_new'])].copy()
        overlap_new = overlap_new[overlap_new.subset_type.eq('ALL')].drop(columns=['subset_type'])
        write_csv_atomic(run_dir / 'scope_denominators.csv', denoms)
        write_csv_atomic(run_dir / 'conflict_stability_summary.csv', summary)
        write_csv_atomic(run_dir / 'conflict_by_domain.csv', domains)
        write_csv_atomic(run_dir / 'overlap_new_comparison.csv', overlap_new)
        write_csv_atomic(run_dir / 'distribution_distances.csv', distances)
        write_csv_atomic(run_dir / 'bootstrap_stability.csv', boot)
        write_json_atomic(run_dir / 'stability_decision.json', decisions)
        stage('s10_conflict_stability', 'complete', status=decisions['status'], scopes=len(denoms),
              bootstrap_replicates=BOOTSTRAP_REPLICATES)

        stage('s20_text_join_audit', 'start')
        text_audit = parse_a18_and_text_join(df, masks)
        write_csv_atomic(run_dir / 'text_join_audit.csv', text_audit)
        stage('s20_text_join_audit', 'complete', candidates=len(text_audit), selected_source='Q01C_A1_raw_source')

        stage('s30_sampling_seal', 'start')
        blind, key_df, seal = sample_blind_package(df, masks)
        write_json_atomic(run_dir / 'sampling_seal.json', seal)
        write_csv_atomic(run_dir / 'manual_review_key.csv', key_df)
        stage('s30_sampling_seal', 'complete', n=seal['actual_n'], domains=len(seal['domain_counts']))

        stage('s40_blind_package', 'start')
        write_csv_atomic(run_dir / 'manual_text_review_blind.csv', blind)
        instructions = f'''# G1 文本盲审说明\n\n状态：`WAITING_FOR_AUTHOR_REVIEW`。本文件不是模型评分结果，执行器不会生成任何人工评分。\n\n## 作者任务\n\n1. 请只查看 `manual_text_review_blind.csv`，不要查看 `manual_review_key.csv`、Q、Q分位、高冲突标签或组三分数。\n2. 对每条 `text_redacted` 独立判断并填写：\n   - `readability_1to5`：1–5整数。\n   - `completeness_1to5`：1–5整数。\n   - `contamination_0to2`：0无污染、1可疑、2明显垃圾/广告/模板污染。\n   - `overall_quality_1to5`：1–5整数。\n   - `review_notes_optional`：可选短备注，不得用于替代评分。\n3. 不要使用AI、规则、模型或他人自动评分替代作者判断。\n4. 将原盲审表另存为 `manual_text_review_completed.csv`，不要把完成值写回原始 `manual_text_review_blind.csv`。\n5. 完成后交回原始blind表哈希与completed表；执行器只对有效填写记录做统计，不因结果方向而重新抽样。\n\n## 文本说明\n\n原始文本只做电子邮件、URL和非必要控制字符的必要脱敏；未改写正文。若文本中仍有敏感信息，请仅作为审阅材料处理。\n\n共 {seal['actual_n']} 条，覆盖 {len(seal['domain_counts'])} 个domain，单一domain不超过{seal['single_domain_cap']}条。采样种子、配额、review_id和SHA256已冻结在 `sampling_seal.json`；seal时间早于任何人工评分文件。\n\n## 停止条件\n\n执行器现在停止于作者判断节点。收到有效的 `manual_text_review_completed.csv` 之前，不进行人工结果统计，也不生成 `paper/Q1_GAP_RESULT_FREEZE.md`。\n'''
        (run_dir / 'manual_review_instructions.md').write_text(instructions, encoding='utf-8')
        stage('s40_blind_package', 'complete', rows=len(blind), columns=list(blind.columns), no_ratings=True)

        stage('s50_checks_preverify', 'start')
        protected_after = snapshot_protected()
        protected_changes = compare_protected(protected_before, protected_after)
        write_json_atomic(run_dir / 'protected_after.json', protected_after)
        verifier = run_dir / 'code' / 'verify_g1.py'
        proc = subprocess.run([sys.executable, str(verifier), '--run-dir', str(run_dir)],
                              capture_output=True, text=True, encoding='utf-8')
        if proc.returncode != 0:
            raise RuntimeError(f'independent verifier failed rc={proc.returncode}: {proc.stdout}\n{proc.stderr}')
        verification = json.loads((run_dir / 'verification.json').read_text(encoding='utf-8'))
        checks = build_checks(df, masks, denoms, text_audit, seal, blind, protected_changes, verification)
        write_json_atomic(run_dir / 'checks.json', checks)
        stage('s50_checks_preverify', 'complete', checks=checks['summary'])

        stage('s60_author_wait', 'start')
        status = 'WAITING_FOR_AUTHOR_REVIEW'
        run_summary = {'task': 'TASK-G1', 'run_id': RUN_ID, 'status': status,
                       'started_local': datetime.fromtimestamp(start, CST).isoformat(timespec='seconds'),
                       'finished_local': now_iso(), 'duration_s': round(time.time() - start, 3),
                       'stability_decision': decisions['status'], 'stability_details': decisions,
                       'text_source': 'Q01C_A1_raw_source', 'text_join_audit': text_audit.to_dict(orient='records'),
                       'blind_package': {'n': int(seal['actual_n']), 'domains': seal['domain_counts'],
                                         'single_domain_cap': seal['single_domain_cap'], 'seed': SEED},
                       'manual_ratings_generated_by_executor': False, 'author_review_required': True,
                       'next_input': str(run_dir / 'manual_text_review_completed.csv'),
                       'paper_freeze_candidate_generated': False, 'checks': checks['summary'],
                       'verification': verification.get('summary'), 'artifacts': REQUIRED_OUTPUTS,
                       'prohibitions_respected': ['no Q01C/T03E rerun', 'no main-Q rewrite',
                                                  'no paper text edit', 'no 00-05 edit', 'no AI manual ratings']}
        write_json_atomic(run_dir / 'run_summary.json', run_summary)
        command_log = {'run_id': RUN_ID, 'argv': sys.argv, 'cwd': str(Path.cwd()), 'python': sys.executable,
                       'started_local': datetime.fromtimestamp(start, CST).isoformat(timespec='seconds'),
                       'finished_local': now_iso(), 'stages': seen_stages,
                       'verifier_command': [sys.executable, str(verifier), '--run-dir', str(run_dir)],
                       'verifier_stdout': proc.stdout, 'verifier_stderr': proc.stderr}
        write_json_atomic(run_dir / 'command_log.json', command_log)
        handoff = f'''# TASK-G1 handoff\n\n状态：`WAITING_FOR_AUTHOR_REVIEW`\n\n- run_id：`{RUN_ID}`\n- 扩展冲突稳定性：`{decisions['status']}`；阈值固定为Q01C的`>{HIGH_CONFLICT_THRESHOLD}`。\n- 文本join：选择`Q01C_A1_raw_source`；A18仅完成候选审计，未用于抽样。\n- 盲审包：{seal['actual_n']}条，覆盖{len(seal['domain_counts'])}个domain；seal已先于盲审表和人工评分生成。\n- 盲审表不包含Q、Q分位、高冲突标签、组三分数、原始主键或模型预测；人工评分列全部留空。\n- 独立验收：{verification.get('status')}，fail={verification.get('summary', {}).get('fail')}。\n- 执行器没有生成任何人工评分，也没有生成`paper/Q1_GAP_RESULT_FREEZE.md`。\n\n## 作者下一步\n\n请按`manual_review_instructions.md`完成`manual_text_review_blind.csv`的副本，另存为`manual_text_review_completed.csv`，保持原始blind表不变。完成后交回执行器，继续人工结果统计和paper候选；届时不得重抽样或删除不利结果。\n\n## 机器入口\n\n`run_summary.json`、`sampling_seal.json`、`manual_text_review_blind.csv`、`manual_review_key.csv`、`checks.json`、`verification.json`、`output_manifest.json`。\n'''
        (run_dir / 'handoff.md').write_text(handoff, encoding='utf-8')
        copy_code_snapshot(run_dir)
        stage('s60_author_wait', 'waiting_for_author', status=status, next_input=run_summary['next_input'])
        stage('s70_manifest_pending', 'will_generate_output_manifest_last', registered_pending=True)
        manifest = write_manifest(run_dir, RUN_ID, status, verification)
        print(json.dumps({'status': status, 'run_dir': str(run_dir), 'stability': decisions['status'],
                          'blind_n': seal['actual_n'], 'registered_files': manifest['registered_file_count']},
                         ensure_ascii=False))
        return 0
    except Exception as exc:
        stage('ERROR', 'stopped_with_evidence', error=repr(exc))
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
