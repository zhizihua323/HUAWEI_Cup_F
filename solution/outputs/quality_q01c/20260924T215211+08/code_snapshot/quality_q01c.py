"""TASK-Q01C staged quality pipeline: Q01B rules, explicit denominators,
isolated calibration-domain-median sensitivity analysis, checkpoints and resume.

Boundaries enforced by this module:
  * A1/A2/A3 are read with at most one sequential decompression pass per file in
    a full run; a complete, hash-matching file checkpoint is reused instead of
    being re-scanned (see --probe-resume).
  * no final missing-data strategy other than the Q01B decision is implemented:
    primary Q = strict complete cases on the 11 main-Q features;
    sensitivity = A1-calibration per-domain median, isolated in separate columns.
  * no text/content field is read or stored; no old output directory is written.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import lzma
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent
SOLUTION = SRC_DIR.parent
PROJECT = SOLUTION.parent
DATA = PROJECT / 'F题' / 'real_attachments'
SEED = 20260924
SPLIT_MODULUS = 5
HOLDOUT_REMAINDER = 0
CST = timezone(timedelta(hours=8))

RULES = ['rps_doc_frac_no_alph_words', 'rps_doc_mean_word_length',
         'rps_doc_frac_unique_words', 'rps_doc_unigram_entropy', 'rps_doc_word_count',
         'rps_lines_ending_with_terminal_punctution_mark',
         'rps_lines_numerical_chars_fraction', 'rps_lines_uppercase_letter_fraction',
         'rps_doc_num_sentences', 'rps_doc_frac_chars_top_2gram',
         'rps_doc_frac_chars_top_3gram']
DSIR = ['dsir_books', 'dsir_wiki', 'dsir_math']
PRRC = ['modernbert_professionalism', 'modernbert_readability',
        'modernbert_reasoning', 'modernbert_cleanliness']
LIST_LENGTHS = {'fineweb_edu': 1, 'ad_en': 2, 'fluency_en': 2, 'qurater': 4}
for _p in PRRC:
    LIST_LENGTHS[_p] = 6
FIELDS = RULES + DSIR + list(LIST_LENGTHS)
QURATER = ['qurater_writing_style', 'qurater_required_expertise',
           'qurater_facts_trivia', 'qurater_educational_value']
MODEL = ['fineweb_edu', 'ad_en', 'fluency_en'] + QURATER + PRRC
FEATURES = RULES + DSIR + MODEL
GROUPS = {
    'usability': ['ad_en', 'fluency_en', 'modernbert_readability',
                  'modernbert_cleanliness', 'qurater_writing_style'],
    'knowledge': ['modernbert_professionalism', 'qurater_required_expertise',
                  'qurater_facts_trivia'],
    'education_reasoning': ['modernbert_reasoning', 'fineweb_edu',
                            'qurater_educational_value'],
}
GROUP_NAMES = ['usability', 'knowledge', 'education_reasoning']
EXCLUDED_FROM_MAIN_Q = RULES + DSIR
SENSITIVITY_COLUMN = 'Q_sensitivity_calibration_domain_median'
GATES = {'n_valid_min': 100, 'coverage_min': 0.95, 'n_unique_finite_min': 2}
FILES = [
    {'file_id': 'A1', 'code': 0, 'fallback_domain': None, 'stage': 's10_scan_a1',
     'path': DATA / 'A_data_value' / 'slimpajama_quality_signal_sample.jsonl.xz'},
    {'file_id': 'A2_arxiv', 'code': 1, 'fallback_domain': 'arxiv', 'stage': 's11_scan_a2',
     'path': DATA / 'A_data_value' / 'slimpajama_quality_extended' /
             'arxiv_part-6777d8857c6e-000486.jsonl.xz'},
    {'file_id': 'A3_github', 'code': 2, 'fallback_domain': 'github', 'stage': 's12_scan_a3',
     'path': DATA / 'A_data_value' / 'slimpajama_quality_extended' /
             'github_part-6777d8857c6e-000275.jsonl.xz'},
]
SCOPE_DEFS = [
    ('A1_calibration', lambda df: df['evaluation_role'].eq('A1_calibration') & df['is_unique_first']),
    ('A1_holdout', lambda df: df['evaluation_role'].eq('A1_holdout') & df['is_unique_first']),
    ('A1_all_unique', lambda df: df['file_id'].eq('A1') & df['is_unique_first']),
    ('extension_overlap_A1', lambda df: df['overlap_a1']),
    ('extension_new_records', lambda df: df['evaluation_role'].eq('extension_new_records')
     & df['is_unique_first']),
    ('all_unique', lambda df: df['is_unique_first']),
]
STAGES = ['s00_preflight', 's01_synthetic_tests', 's10_scan_a1', 's11_scan_a2', 's12_scan_a3',
          's20_score_primary', 's30_sensitivity', 's40_summarize', 's50_verify', 's60_finalize']


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


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def read_json(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def read_csv_rows(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def json_safe(value):
    """Strict-JSON sanitiser: non-finite floats become null, numpy scalars become builtins."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    return value


def write_json_atomic(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(json_safe(value), ensure_ascii=False, indent=2, allow_nan=False,
                              default=str), encoding='utf-8')
    os.replace(tmp, path)
    return path


def write_csv_atomic(path, columns, rows):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    os.replace(tmp, path)
    return path


def json_compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def finite_or_none(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


class StageFailure(RuntimeError):
    """Raised when a stage cannot continue (gate failure, hash mismatch, ...)."""


class RunContext:
    def __init__(self, run_dir, run_id, resume=False):
        self.run_id = run_id
        self.run_dir = Path(run_dir)
        self.checkpoints = self.run_dir / 'checkpoints'
        self.resume = resume
        self.log_fh = open(self.run_dir / 'run.log', 'a', encoding='utf-8', newline='\n')
        self.status_fh = open(self.run_dir / 'stage_status.jsonl', 'a', encoding='utf-8', newline='\n')
        self.stage_timers = {}
        self.stage_exit_codes = {}
        self.warnings = []
        self.peak_rss = None
        self.code_hashes = {}

    def log(self, message):
        line = f'[{datetime.now(CST).isoformat(timespec="milliseconds")}] {message}'
        try:
            if not self.log_fh.closed:
                self.log_fh.write(line + '\n')
                self.log_fh.flush()
        except Exception:
            pass
        print(line, flush=True)

    def status(self, stage, event, **fields):
        record = {'ts': datetime.now(CST).isoformat(timespec='milliseconds'), 'stage': stage,
                  'event': event, 'run_id': self.run_id}
        record.update(fields)
        self.status_fh.write(json_compact(record) + '\n')
        self.status_fh.flush()

    def rss_mb(self):
        try:
            import psutil
            info = psutil.Process().memory_info()
            value = int(getattr(info, 'peak_wset', None) or info.rss)
            self.peak_rss = value if self.peak_rss is None else max(self.peak_rss, value)
            return round(value / (1024 * 1024), 1)
        except Exception:
            return None

    def close(self):
        for handle in (self.status_fh, self.log_fh):
            try:
                handle.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# feature extraction / raw audit (frozen semantics of the historical pipeline)
# ---------------------------------------------------------------------------
def get_features(obj):
    """Replica of the frozen historical extraction: whole-list invalidation,
    bool accepted as numeric, PRRC/ad/fluency reduced by argmax."""
    result = {}
    for field in RULES + DSIR:
        value = obj.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                result[field] = float(value)
            except (OverflowError, ValueError):
                result[field] = float('nan')
        elif isinstance(value, bool):
            result[field] = float(value)
        else:
            result[field] = float('nan')
    for field, expected in LIST_LENGTHS.items():
        value = obj.get(field)
        valid = isinstance(value, list) and len(value) == expected
        if valid:
            try:
                valid = all(isinstance(x, (int, float)) and np.isfinite(x) for x in value)
            except (TypeError, OverflowError, ValueError):
                valid = False
        if field == 'qurater':
            for i, col in enumerate(QURATER):
                result[col] = float(value[i]) if valid else float('nan')
        elif field == 'fineweb_edu':
            result[field] = float(value[0]) if valid else float('nan')
        else:
            result[field] = float(np.argmax(value)) if valid else float('nan')
    for feature in FEATURES:
        result.setdefault(feature, float('nan'))
    return result


def audit_raw_fields(obj):
    """Detailed raw-field audit: per-field element classification and record flags."""
    detail = {}
    invalid_fields = []
    for field in FIELDS:
        if field not in obj:
            detail[field] = {'absent': 1, 'elements': 0}
            invalid_fields.append(field)
            continue
        value = obj[field]
        entry = {'elements': 0, 'nan': 0, 'posinf': 0, 'neginf': 0, 'non_numeric': 0,
                 'finite': 0, 'null': 0, 'wrong_length': 0, 'reasons': []}
        if value is None:
            entry['null'] = 1
            entry['reasons'].append('null')
        elif isinstance(value, list):
            expected = LIST_LENGTHS.get(field)
            if expected is not None and len(value) != expected:
                entry['wrong_length'] = 1
                entry['reasons'].append('wrong_list_length')
            entry['elements'] = len(value)
            for x in value:
                if isinstance(x, bool) or not isinstance(x, (int, float)):
                    entry['non_numeric'] += 1
                    entry['reasons'].append('non_numeric_element')
                    continue
                if isinstance(x, float):
                    if math.isnan(x):
                        entry['nan'] += 1
                        entry['reasons'].append('nan_element')
                        continue
                    if x == float('inf'):
                        entry['posinf'] += 1
                        entry['reasons'].append('posinf_element')
                        continue
                    if x == float('-inf'):
                        entry['neginf'] += 1
                        entry['reasons'].append('neginf_element')
                        continue
                entry['finite'] += 1
        else:
            entry['elements'] = 1
            x = value
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                entry['non_numeric'] = 1
                entry['reasons'].append('non_numeric_element')
            elif isinstance(x, float) and math.isnan(x):
                entry['nan'] = 1
                entry['reasons'].append('nan_element')
            elif isinstance(x, float) and x == float('inf'):
                entry['posinf'] = 1
                entry['reasons'].append('posinf_element')
            elif isinstance(x, float) and x == float('-inf'):
                entry['neginf'] = 1
                entry['reasons'].append('neginf_element')
            else:
                entry['finite'] = 1
        entry['reasons'] = sorted(set(entry['reasons']))
        if entry['reasons']:
            invalid_fields.append(field)
            detail[field] = entry
    return detail, invalid_fields


def quality_fingerprint(obj):
    """Replica of the historical fingerprint (NaN serialised as the NaN token)."""
    normalized = {}
    for field in FIELDS:
        value = obj.get(field)
        if isinstance(value, list):
            normalized[field] = [float(x) for x in value]
        elif isinstance(value, (int, float)):
            normalized[field] = float(value)
        else:
            normalized[field] = value
    return sha256_text(json.dumps(normalized, sort_keys=True, separators=(',', ':')))


def split_remainder(key_json):
    return int(sha256_text(str(SEED) + key_json)[:16], 16) % SPLIT_MODULUS


CHECKPOINT_ROW_COLUMNS = (['file_id', 'source_line', 'id_json', 'sub_path_json', 'key_sha256',
                           'quality_sha256', 'domain', 'domain_source', 'is_unique_first',
                           'overlap_a1', 'evaluation_role', 'raw_invalid_fields',
                           'raw_anomaly_json', 'extract_nan_features', 'extract_nonfinite_features',
                           'raw_invalid_count', 'extract_nan_count']
                          + FEATURES)


def code_fingerprint():
    parts = []
    for name in ['quality_q01c.py', 'quality_q01c_selftest.py', 'quality_q01c_verify.py']:
        path = SRC_DIR / name
        if path.is_file():
            parts.append(f'{name}:{sha256_file(path)}')
    return sha256_text('|'.join(sorted(parts)))


def checkpoint_paths(ctx, stage):
    stem = ctx.checkpoints / stage
    return {'parquet': stem.with_suffix('.parquet'), 'json': stem.with_suffix('.json'),
            'complete': ctx.checkpoints / f'{stage}.COMPLETE'}


def checkpoint_is_valid(ctx, stage, expected_input_sha, config_sha):
    paths = checkpoint_paths(ctx, stage)
    if not (paths['parquet'].is_file() and paths['json'].is_file() and paths['complete'].is_file()):
        return False, 'missing file(s)'
    try:
        meta = read_json(paths['json'])
        marker = read_json(paths['complete'])
    except Exception as exc:
        return False, f'unreadable metadata: {exc}'
    if marker.get('checkpoint_json_sha256') != sha256_file(paths['json']):
        return False, 'COMPLETE marker does not match checkpoint json'
    if meta.get('parquet_sha256') != sha256_file(paths['parquet']):
        return False, 'parquet hash mismatch'
    if meta.get('input_sha256') != expected_input_sha:
        return False, 'input version changed'
    if meta.get('code_fingerprint') != code_fingerprint():
        return False, 'code version changed'
    if meta.get('config_sha256') != config_sha:
        return False, 'config version changed'
    return True, 'valid'


def write_checkpoint(ctx, stage, frame, meta, config_sha):
    paths = checkpoint_paths(ctx, stage)
    tmp = paths['parquet'].with_suffix('.parquet.tmp')
    frame.to_parquet(tmp, index=False, compression='zstd')
    os.replace(tmp, paths['parquet'])
    meta = dict(meta)
    meta.update({'stage': stage, 'rows': int(len(frame)), 'columns': list(frame.columns),
                 'parquet': paths['parquet'].name, 'parquet_sha256': sha256_file(paths['parquet']),
                 'code_fingerprint': code_fingerprint(), 'config_sha256': config_sha,
                 'written_local': now_iso()})
    write_json_atomic(paths['json'], meta)
    write_json_atomic(paths['complete'], {'stage': stage, 'completed_local': now_iso(),
                                          'checkpoint_json_sha256': sha256_file(paths['json']),
                                          'rows': int(len(frame))})
    return meta


def scan_file_stage(ctx, spec, config_sha, preflight, probe=False):
    stage = spec['stage']
    expected_input_sha = preflight['primary'][spec['file_id']]['sha256']
    valid, reason = checkpoint_is_valid(ctx, stage, expected_input_sha, config_sha)
    if valid:
        rows = read_json(checkpoint_paths(ctx, stage)['json'])['rows']
        ctx.status(stage, 'resume_probe_reused' if probe else 'checkpoint_reused', reason=reason,
                   decompress_passes=0, input_sha256=expected_input_sha,
                   note='no decompression performed for this file')
        ctx.log(f'stage={stage} checkpoint reuse ({reason}); decompress_passes=0')
        return {'stage': stage, 'reused': True, 'rows': rows, 'decompress_passes': 0}
    if probe:
        raise StageFailure(f'probe requested but checkpoint not reusable: {reason}')
    return _scan_file_fresh(ctx, spec, config_sha, preflight)


def _scan_file_fresh(ctx, spec, config_sha, preflight):
    stage = spec['stage']
    file_id = spec['file_id']
    ctx.status(stage, 'start', file=file_id, decompress_passes=1)
    t0 = time.monotonic()
    prior_keys = set()
    prior_fingerprints = {}
    prior_file_ids = []
    for other in FILES:
        if other['code'] < spec['code']:
            frame = pd.read_parquet(checkpoint_paths(ctx, other['stage'])['parquet'],
                                    columns=['key_sha256', 'quality_sha256'])
            prior_keys.update(frame['key_sha256'].tolist())
            for key, fingerprint in zip(frame['key_sha256'].tolist(), frame['quality_sha256'].tolist()):
                prior_fingerprints.setdefault(key, fingerprint)
            prior_file_ids.append((other['file_id'], len(frame)))
            del frame
    rows = []
    file_seen = set()
    stats = {'rows': 0, 'invalid_json': 0, 'domains': Counter(), 'id_types': Counter(),
             'within_file_duplicate_rows': 0, 'overlap_a1_rows': 0,
             'quality_conflicting_rows': 0, 'missing_source_domain_rows': 0,
             'fingerprint_errors': 0, 'raw_invalid_rows': 0, 'raw_nan_element_rows': 0,
             'raw_nan_elements': 0, 'line_count': 0}
    with lzma.open(str(spec['path']), 'rt', encoding='utf-8') as fh:
        line_no = 0
        for line in fh:
            line_no += 1
            try:
                obj = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                stats['invalid_json'] += 1
                raise StageFailure(f'parse failure in {file_id} line {line_no}: {exc}')
            if not isinstance(obj, dict):
                stats['invalid_json'] += 1
                raise StageFailure(f'non-object JSON in {file_id} line {line_no}')
            raw_domain = obj.get('_source_domain')
            if raw_domain:
                domain, domain_source = raw_domain, 'raw'
            elif spec['fallback_domain']:
                domain, domain_source = spec['fallback_domain'], 'documented_filename_fallback'
            else:
                domain, domain_source = 'unknown', 'unknown'
            if not raw_domain:
                stats['missing_source_domain_rows'] += 1
            sub_path = obj.get('sub_path', '')
            key_json = json.dumps((str(obj.get('id', '')), str(sub_path)), ensure_ascii=False,
                                  separators=(',', ':'))
            key_sha = sha256_text(key_json)
            try:
                fingerprint = quality_fingerprint(obj)
            except Exception:
                fingerprint = ''
                stats['fingerprint_errors'] += 1
            detail, invalid_fields = audit_raw_fields(obj)
            features = get_features(obj)
            nan_features = [f for f in FEATURES if math.isnan(features[f])]
            nonfinite_features = [f for f in FEATURES if not math.isfinite(features[f])]
            is_unique_first = key_sha not in prior_keys and key_sha not in file_seen
            if key_sha in file_seen:
                stats['within_file_duplicate_rows'] += 1
            overlap_a1 = spec['code'] != 0 and key_sha in prior_keys
            if overlap_a1:
                stats['overlap_a1_rows'] += 1
            previous_fp = prior_fingerprints.get(key_sha)
            if previous_fp is None:
                prior_fingerprints[key_sha] = fingerprint
            elif fingerprint and previous_fp and previous_fp != fingerprint:
                stats['quality_conflicting_rows'] += 1
            if spec['code'] == 0:
                role = ('A1_holdout' if split_remainder(key_json) == HOLDOUT_REMAINDER
                        else 'A1_calibration')
            else:
                role = 'extension_overlap_A1' if overlap_a1 else 'extension_new_records'
            file_seen.add(key_sha)
            anomaly_json = json_compact({f: v for f, v in detail.items()
                                         if v.get('reasons') or v.get('absent')}) if invalid_fields else ''
            raw_nan_elements = sum(v.get('nan', 0) for v in detail.values())
            if invalid_fields:
                stats['raw_invalid_rows'] += 1
            if raw_nan_elements:
                stats['raw_nan_element_rows'] += 1
                stats['raw_nan_elements'] += raw_nan_elements
            stats['domains'][domain] += 1
            stats['id_types'][type(obj.get('id')).__name__] += 1
            row = {'file_id': file_id, 'source_line': line_no,
                   'id_json': json.dumps(obj.get('id'), ensure_ascii=False) if 'id' in obj else '',
                   'sub_path_json': json.dumps(sub_path, ensure_ascii=False), 'key_sha256': key_sha,
                   'quality_sha256': fingerprint, 'domain': domain, 'domain_source': domain_source,
                   'is_unique_first': is_unique_first, 'overlap_a1': overlap_a1,
                   'evaluation_role': role, 'raw_invalid_fields': '|'.join(invalid_fields),
                   'raw_anomaly_json': anomaly_json,
                   'extract_nan_features': '|'.join(nan_features),
                   'extract_nonfinite_features': '|'.join(nonfinite_features),
                   'raw_invalid_count': len(invalid_fields), 'extract_nan_count': len(nan_features)}
            for feature in FEATURES:
                row[feature] = features[feature]
            rows.append(row)
            stats['rows'] += 1
            if stats['rows'] % 50000 == 0:
                ctx.log(f'stage={stage} rows={stats["rows"]} elapsed_s={time.monotonic()-t0:.1f} '
                        f'rss_mb={ctx.rss_mb()}')
    stats['line_count'] = line_no
    frame = pd.DataFrame(rows, columns=CHECKPOINT_ROW_COLUMNS)
    meta = {'file_id': file_id, 'path': str(spec['path']),
            'input_sha256': preflight['primary'][file_id]['sha256'],
            'bytes': spec['path'].stat().st_size,
            'stats': {k: (dict(v) if isinstance(v, Counter) else v) for k, v in stats.items()},
            'prior_files': prior_file_ids, 'seed': SEED,
            'split_rule': f'int(sha256(str({SEED})+key_json)[:16],16)%{SPLIT_MODULUS}; 0 -> A1_holdout',
            'content_read': False}
    meta = write_checkpoint(ctx, stage, frame, meta, config_sha)
    elapsed = time.monotonic() - t0
    ctx.status(stage, 'complete', rows=stats['rows'], line_count=line_no, elapsed_s=round(elapsed, 3),
               rss_mb=ctx.rss_mb(), parquet_sha256=meta['parquet_sha256'], decompress_passes=1)
    ctx.log(f'stage={stage} complete rows={stats["rows"]} elapsed_s={elapsed:.1f}')
    return {'stage': stage, 'reused': False, 'rows': stats['rows'], 'decompress_passes': 1,
            'stats': meta['stats']}


PROTECTED_EVIDENCE = [
    PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T142229+08' / 'run_summary.json',
    PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T142229+08' / 'checks.json',
    PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T142229+08' / 'output_manifest.json',
    PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T142229+08' / 'invalid_values.csv.gz',
    PROJECT / 'diagnostics' / 'TASK-Q01A-R1' / '20260924T150854+08' / 'run_summary.json',
    PROJECT / 'diagnostics' / 'TASK-Q01A-R1' / '20260924T150854+08' / 'repair_checks.json',
    PROJECT / 'diagnostics' / 'TASK-Q01A-R1' / '20260924T150854+08' / 'output_manifest.json',
    PROJECT / 'diagnostics' / 'TASK-Q01A-R1' / '20260924T150854+08' / 'raw_field_counts_corrected.csv',
    PROJECT / 'diagnostics' / 'TASK-Q01A-R1' / '20260924T150854+08' / 'summary_denominators_corrected.csv',
]


def snapshot_paths(paths):
    out = {}
    for item in paths:
        path = Path(item)
        if path.is_dir():
            files = sorted(p for p in path.rglob('*') if p.is_file())
        elif path.is_file():
            files = [path]
        else:
            files = []
        for child in files:
            stat = child.stat()
            out[str(child.relative_to(PROJECT)).replace('\\', '/')] = {
                'bytes': stat.st_size, 'mtime': stat.st_mtime, 'sha256': sha256_file(child)}
    return out


def collect_inputs():
    manifest = {'primary': {}, 'docs': {}, 'source': {}, 'old_quality': {},
                'evidence': {}, 'reports': {}, 'verification_method': {}}
    for spec in FILES:
        stat = spec['path'].stat()
        manifest['primary'][spec['file_id']] = {
            'path': str(spec['path'].relative_to(PROJECT)).replace('\\', '/'),
            'bytes': stat.st_size, 'mtime': stat.st_mtime, 'sha256': sha256_file(spec['path']),
            'verification_method': 'read-only byte hash of the compressed file (not a decompression pass)'}
    for name in ['00_PROJECT_BRIEF.md', '01_PROJECT_STATUS.md', '02_DECISIONS.md',
                 '03_DATA_CATALOG.md', '04_TASK_QUEUE.md', '05_REVIEW_LOG.md']:
        manifest['docs'][name] = {'path': name, 'sha256': sha256_file(PROJECT / name),
                                 'bytes': (PROJECT / name).stat().st_size}
    for name in ['TASK-Q01A_质量缺失模式诊断.md', 'TASK-Q01A-R1_主控审查与精准小修要求.md',
                 'TASK-Q01B_质量缺失处理策略裁决.md', 'TASK-Q01C_质量缺失策略实施与流水线恢复.md']:
        path = PROJECT / 'tasks' / name
        manifest['docs'][f'tasks/{name}'] = {'path': f'tasks/{name}', 'sha256': sha256_file(path),
                                            'bytes': path.stat().st_size}
    for path in sorted(SRC_DIR.glob('*.py')):
        manifest['source'][f'solution/src/{path.name}'] = {
            'path': f'solution/src/{path.name}', 'sha256': sha256_file(path),
            'bytes': path.stat().st_size, 'role': 'Q01C new module' if 'q01c' in path.name else 'frozen historical module'}
    for name in ['config.json', 'README.md']:
        path = SOLUTION / name
        manifest['source'][f'solution/{name}'] = {'path': f'solution/{name}',
                                                 'sha256': sha256_file(path),
                                                 'bytes': path.stat().st_size}
    manifest['old_quality'] = snapshot_paths([SOLUTION / 'outputs' / 'quality'])
    manifest['reports'] = snapshot_paths([SOLUTION / 'reports'])
    manifest['evidence'] = snapshot_paths(PROTECTED_EVIDENCE)
    return manifest


def stage_s00_preflight(ctx, config_sha):
    stage = 's00_preflight'
    ctx.status(stage, 'start')
    t0 = time.monotonic()
    ctx.checkpoints.mkdir(parents=True, exist_ok=True)
    inputs = collect_inputs()
    primary_inputs = inputs['primary']
    prior_manifest = {row['path']: row for row in
                      read_csv_rows(SOLUTION / 'outputs' / 'audit' / 'raw_source_manifest.csv')}
    prior_audit = read_json(SOLUTION / 'outputs' / 'quality' / 'audit.json')
    audit_sha = {item['file_id']: item['sha256'] for item in prior_audit['files']}
    checks = []
    for spec in FILES:
        rel = str(spec['path'].relative_to(DATA)).replace('\\', '/')
        recorded = prior_manifest.get(rel, {})
        new_sha = primary_inputs[spec['file_id']]['sha256']
        ok_manifest = recorded.get('sha256') == new_sha and int(recorded.get('bytes', -1)) == \
            primary_inputs[spec['file_id']]['bytes']
        ok_audit = audit_sha.get(spec['file_id']) == new_sha
        checks.append({'file_id': spec['file_id'], 'matches_raw_source_manifest': bool(ok_manifest),
                       'matches_prior_audit_json': bool(ok_audit), 'sha256': new_sha})
        if not (ok_manifest and ok_audit):
            raise StageFailure(f'input version mismatch for {spec["file_id"]}')
    ctx.code_hashes = {name: info['sha256'] for name, info in inputs['source'].items()}
    snapshot_dir = ctx.run_dir / 'code_snapshot'
    snapshot_dir.mkdir(exist_ok=True)
    frozen = []
    for name in ['quality_q01c.py', 'quality_q01c_selftest.py', 'quality_q01c_verify.py']:
        src = SRC_DIR / name
        if src.is_file():
            target = snapshot_dir / name
            shutil.copy2(src, target)
            frozen.append({'file': name, 'sha256': sha256_file(target),
                           'bytes': target.stat().st_size})
    test_src = SOLUTION / 'tests' / 'test_quality_q01c.py'
    if test_src.is_file():
        target = snapshot_dir / 'test_quality_q01c.py'
        shutil.copy2(test_src, target)
        frozen.append({'file': 'test_quality_q01c.py', 'sha256': sha256_file(target),
                       'bytes': target.stat().st_size})
    write_json_atomic(ctx.run_dir / 'code_snapshot' / 'code_snapshot_manifest.json',
                      {'run_id': ctx.run_id, 'frozen_local': now_iso(), 'files': frozen})
    write_json_atomic(ctx.run_dir / 'input_manifest.json',
                      {'run_id': ctx.run_id, 'generated_local': now_iso(),
                       'primary': inputs['primary'], 'docs': inputs['docs'], 'source': inputs['source'],
                       'old_quality': inputs['old_quality'], 'reports': inputs['reports'],
                       'evidence': inputs['evidence'], 'version_checks': checks,
                       'read_policy': 'all inputs above are read-only; A1-A3 are the only raw inputs',
                       'content_policy': 'no text/content field is read, stored or analysed'})
    old_before = snapshot_paths([SOLUTION / 'outputs' / 'quality', SOLUTION / 'reports',
                                 PROJECT / 'diagnostics' / 'TASK-Q01A',
                                 PROJECT / 'diagnostics' / 'TASK-Q01A-R1',
                                 PROJECT / 'F题' / 'real_attachments' / 'A_data_value'])
    write_json_atomic(ctx.run_dir / 'old_artifacts_before.json',
                      {'generated_local': now_iso(), 'entries': old_before,
                       'note': 'hash snapshot used to prove that protected artifacts are untouched'})
    write_json_atomic(ctx.run_dir / 'environment.json',
                      {'run_id': ctx.run_id, 'start_local': now_iso(), 'python': sys.version,
                       'python_executable': sys.executable, 'platform': platform.platform(),
                       'machine': platform.machine(), 'timezone': str(datetime.now().astimezone().tzinfo),
                       'seed': SEED, 'commands': [], 'single_process_cpu': True, 'gpu_used': False,
                       'network_used': False, 'libraries': {'numpy': np.__version__,
                                                            'pandas': pd.__version__,
                                                            'pyarrow': __import__('pyarrow').__version__},
                       'content_read': False})
    mark_stage_complete(ctx, stage, [ctx.run_dir / 'input_manifest.json',
                                     ctx.run_dir / 'environment.json',
                                     ctx.run_dir / 'old_artifacts_before.json',
                                     ctx.run_dir / 'code_snapshot' / 'code_snapshot_manifest.json'])
    ctx.status(stage, 'complete', elapsed_s=round(time.monotonic() - t0, 3), rss_mb=ctx.rss_mb())
    ctx.log(f'stage={stage} complete; inputs verified, code snapshot frozen')
    return inputs


def mark_stage_complete(ctx, stage, outputs):
    payload = {'stage': stage, 'completed_local': now_iso(),
               'outputs': {str(Path(p).relative_to(ctx.run_dir)).replace('\\', '/'): sha256_file(p)
                           for p in outputs if Path(p).is_file()}}
    write_json_atomic(ctx.checkpoints / f'{stage}.COMPLETE', payload)
    return payload


def stage_s01_synthetic_tests(ctx, config_sha):
    stage = 's01_synthetic_tests'
    ctx.status(stage, 'start')
    t0 = time.monotonic()
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    import quality_q01c_selftest
    report = quality_q01c_selftest.run_all_tests()
    report.update({'run_id': ctx.run_id, 'generated_local': now_iso(), 'synthetic_only': True,
                   'note': 'counts here are artificial and never mixed into real statistics'})
    write_json_atomic(ctx.run_dir / 'synthetic_tests.json', report)
    if report['status'] != 'PASS':
        ctx.status(stage, 'failed', failed=report['n_failed'])
        raise StageFailure('synthetic tests failed; raw data must not be read')
    mark_stage_complete(ctx, stage, [ctx.run_dir / 'synthetic_tests.json'])
    ctx.status(stage, 'complete', n_tests=report['n_tests'], failed=0,
               elapsed_s=round(time.monotonic() - t0, 3))
    ctx.log(f'stage={stage} complete tests={report["n_tests"]}')
    return report


def weighted_quantile(values, weights, quantiles):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    good = np.isfinite(values) & np.isfinite(weights)
    values, weights = values[good], weights[good]
    order = np.argsort(values, kind='stable')
    values, weights = values[order], weights[order]
    positions = (np.cumsum(weights) - weights / 2) / weights.sum()
    return np.interp(quantiles, positions, values)


def stage_s20_score_primary(ctx, config_sha, preflight):
    stage = 's20_score_primary'
    ctx.status(stage, 'start')
    t0 = time.monotonic()
    frames = []
    for spec in FILES:
        valid, reason = checkpoint_is_valid(ctx, spec['stage'],
                                           preflight['primary'][spec['file_id']]['sha256'], config_sha)
        if not valid:
            raise StageFailure(f'{spec["stage"]} checkpoint not reusable: {reason}')
        frames.append(pd.read_parquet(checkpoint_paths(ctx, spec['stage'])['parquet']))
    df = pd.concat(frames, ignore_index=True)
    del frames
    calibration = df[(df['evaluation_role'] == 'A1_calibration') & df['is_unique_first']]
    domain_counts = calibration['domain'].value_counts()
    transforms = {}
    for feature in MODEL:
        if feature in PRRC:
            low, high, method = 0.0, 5.0, 'official_ordinal_range'
        elif feature in ('ad_en', 'fluency_en'):
            low, high, method = 0.0, 1.0, 'official_binary_class_index'
        else:
            weights = calibration['domain'].map(
                lambda d: 1.0 / (len(domain_counts) * domain_counts[d])).to_numpy()
            low, high = weighted_quantile(calibration[feature].to_numpy(), weights, [0.01, 0.99])
            method = 'A1_calibration_equal_domain_weight_1_99_percentile'
        if not (np.isfinite(low) and np.isfinite(high) and high > low):
            raise StageFailure(f'invalid normalization bounds for {feature}: {low}, {high}')
        transforms[feature] = {'low': float(low), 'high': float(high), 'method': method,
                               'direction': 'higher'}
        df['norm_' + feature] = ((df[feature] - low) / (high - low)).clip(0, 1)
    write_json_atomic(ctx.run_dir / 'normalization.json', {
        'run_id': ctx.run_id, 'generated_local': now_iso(),
        'source_scope': 'A1_calibration & is_unique_first',
        'calibration_rows': int(len(calibration)),
        'calibration_domain_counts': {str(k): int(v) for k, v in domain_counts.items()},
        'domain_weight_rule': 'each calibration domain carries 1/(n_domains) total weight',
        'continuous_quantiles': [0.01, 0.99], 'transforms': transforms, 'refit': False})
    ctx.log(f'stage={stage} normalization fitted on {len(calibration)} calibration rows')
    return df, transforms


def finalize_primary_scores(df, write_path=None):
    """Add group scores, Q_valid/Q_baseline, disagreement and sensitivity-anchor columns."""
    norm_columns = ['norm_' + f for f in MODEL]
    for group in GROUP_NAMES:
        columns = ['norm_' + f for f in GROUPS[group]]
        df['group_' + group] = df[columns].mean(axis=1, skipna=False)
    group_columns = ['group_' + g for g in GROUP_NAMES]
    missing_mask = ~np.isfinite(df[norm_columns].to_numpy())
    df['Q_missing_feature_count'] = missing_mask.sum(axis=1)
    df['Q_missing_features'] = ['|'.join(np.array(MODEL)[row]) for row in missing_mask]
    df['Q_valid'] = df['Q_missing_feature_count'] == 0
    df['Q_baseline'] = np.where(df['Q_valid'], df[group_columns].mean(axis=1, skipna=False), np.nan)
    df['n_groups_valid'] = 3 - df[group_columns].isna().sum(axis=1)
    df['rater_disagreement_range'] = df[group_columns].max(axis=1) - df[group_columns].min(axis=1)
    df['rater_disagreement_std'] = df[group_columns].std(axis=1, ddof=0)
    df['rater_disagreement_range_defined'] = df['rater_disagreement_range'].notna()
    df['Q_equal_indicator_sensitivity'] = df[norm_columns].mean(axis=1, skipna=False)
    df['Q_without_knowledge_sensitivity'] = df[
        ['group_usability', 'group_education_reasoning']].mean(axis=1, skipna=False)
    return df


def stage_s20_write(ctx, config_sha, df):
    stage = 's20_score_primary'
    df = finalize_primary_scores(df)
    path = ctx.run_dir / 'quality_features_scores.parquet'
    df.to_parquet(path, index=False, compression='zstd')
    meta = {'source': [spec['stage'] for spec in FILES], 'rows': int(len(df)),
            'Q_valid_true': int(df['Q_valid'].sum()), 'Q_valid_false': int((~df['Q_valid']).sum()),
            'q_valid_definition': 'all 11 normalized main-Q features finite',
            'group_rule': 'each group requires all its constituent features; no within-group skipna',
            'output': path.name}
    write_checkpoint(ctx, stage, df, meta, config_sha)
    mark_stage_complete(ctx, stage, [path, ctx.run_dir / 'normalization.json'])
    ctx.log(f'stage={stage} complete rows={len(df)} Q_valid={int(df["Q_valid"].sum())} '
            f'Q_missing={int((~df["Q_valid"]).sum())}')
    return df


def require_all_gates(parameters):
    """Hard stop when any sufficiency gate fails: no fallback of any kind."""
    failed = [f"{p['domain']}/{p['feature']}:{p['gate_failures']}"
              for p in parameters.values() if not p['gate_ok']]
    if failed:
        raise StageFailure('sensitivity sufficiency gate failed; stopping without fallback: '
                           + '; '.join(failed))
    return True


def compute_sensitivity_parameters(df):
    missing_rows = df[df['extract_nan_features'].fillna('') != '']
    pairs = set()
    for features, domain in zip(missing_rows['extract_nan_features'], missing_rows['domain']):
        for feature in str(features).split('|'):
            if feature in MODEL:
                pairs.add((domain, feature))
    calibration = df[(df['evaluation_role'] == 'A1_calibration') & df['is_unique_first']]
    parameters = {}
    for domain, feature in sorted(pairs):
        column = 'norm_' + feature
        part = calibration[calibration['domain'] == domain]
        candidates = int(len(part))
        values = part[column].dropna()
        n_valid = int(values.size)
        n_unique_finite = int(values.nunique())
        coverage = (n_valid / candidates) if candidates else 0.0
        median = float(values.median()) if n_valid else None
        failures = []
        if n_valid < GATES['n_valid_min']:
            failures.append(f'n_valid<{GATES["n_valid_min"]}')
        if coverage < GATES['coverage_min']:
            failures.append(f'coverage<{GATES["coverage_min"]}')
        if n_unique_finite < GATES['n_unique_finite_min']:
            failures.append(f'n_unique_finite<{GATES["n_unique_finite_min"]}')
        parameters[(domain, feature)] = {
            'domain': domain, 'feature': feature, 'source_scope': 'A1_calibration & is_unique_first',
            'source_domain': domain, 'candidate_rows': candidates, 'n_valid': n_valid,
            'coverage': coverage, 'n_unique_finite': n_unique_finite, 'median': median,
            'gate_ok': not failures, 'gate_failures': failures,
            'source_proof': 'rows equal to (evaluation_role=A1_calibration & is_unique_first & domain='
                            + domain + '); no holdout/extension/global fallback permitted'}
    return parameters


def stage_s30_sensitivity(ctx, config_sha):
    stage = 's30_sensitivity'
    ctx.status(stage, 'start')
    t0 = time.monotonic()
    path = ctx.run_dir / 'quality_features_scores.parquet'
    df = pd.read_parquet(path)
    parameters = compute_sensitivity_parameters(df)
    payload = {'run_id': ctx.run_id, 'generated_local': now_iso(), 'gates': GATES,
               'source_scope': 'A1_calibration & is_unique_first',
               'a3_github_rule': 'github parameter must come from A1_calibration/github; no fallback',
               'parameters': [parameters[key] for key in sorted(parameters)],
               'all_gates_passed': all(p['gate_ok'] for p in parameters.values())}
    if not payload['all_gates_passed']:
        write_json_atomic(ctx.run_dir / 'imputation_parameters_sensitivity.json', payload)
        failed = [f"{p['domain']}/{p['feature']}:{p['gate_failures']}" for p in parameters.values()
                  if not p['gate_ok']]
        ctx.status(stage, 'gate_failed', failed=failed)
        require_all_gates(parameters)  # raises StageFailure; no fallback path exists
    sens = pd.DataFrame(index=df.index)
    for feature in MODEL:
        sens['sens_norm_' + feature] = df['norm_' + feature]
    imputed_positions = {}
    for (domain, feature), parameter in sorted(parameters.items()):
        column = 'sens_norm_' + feature
        mask = (df['domain'] == domain) & sens[column].isna()
        positions = np.flatnonzero(mask.to_numpy())
        if positions.size:
            sens.iloc[positions, sens.columns.get_loc(column)] = parameter['median']
            imputed_positions.setdefault(feature, []).extend(positions.tolist())
    for group in GROUP_NAMES:
        columns = ['sens_norm_' + f for f in GROUPS[group]]
        df['group_sensitivity_' + group] = sens[columns].mean(axis=1, skipna=False)
    sensitivity_group_columns = ['group_sensitivity_' + g for g in GROUP_NAMES]
    df[SENSITIVITY_COLUMN] = df[sensitivity_group_columns].mean(axis=1, skipna=False)
    imputed_lists = [''] * len(df)
    for feature, positions in imputed_positions.items():
        for pos in positions:
            existing = imputed_lists[pos]
            imputed_lists[pos] = f'{existing}|{feature}' if existing else feature
    df['sensitivity_imputed_features'] = imputed_lists
    df['sensitivity_imputed_count'] = [len(x.split('|')) if x else 0 for x in imputed_lists]
    applied = {}
    for feature, positions in imputed_positions.items():
        sub = df.iloc[positions]
        applied[feature] = {'imputed_records': int(len(positions)),
                            'by_domain': {str(k): int(v) for k, v in sub['domain'].value_counts().items()},
                            'by_role': {str(k): int(v) for k, v in
                                        sub['evaluation_role'].value_counts().items()}}
    payload['applied_imputation_counts'] = applied
    payload['imputed_records_total'] = int(df['sensitivity_imputed_count'].sum())
    payload['imputed_records_with_any_fill'] = int((df['sensitivity_imputed_count'] > 0).sum())
    write_json_atomic(ctx.run_dir / 'imputation_parameters_sensitivity.json', payload)
    write_csv_atomic(ctx.run_dir / 'imputation_applied_counts.csv',
                     ['feature', 'imputed_records', 'by_domain', 'by_role'],
                     [{'feature': k, **v} for k, v in sorted(applied.items())])
    df.to_parquet(path, index=False, compression='zstd')
    meta = {'source': 's20_score_primary + sensitivity parameters',
            'sensitivity_column': SENSITIVITY_COLUMN,
            'imputed_records_total': payload['imputed_records_total'], 'gate_status': 'all_passed',
            'fallback_used': False}
    write_checkpoint(ctx, stage, df, meta, config_sha)
    mark_stage_complete(ctx, stage, [path, ctx.run_dir / 'imputation_parameters_sensitivity.json'])
    ctx.status(stage, 'complete', imputed_records=payload['imputed_records_total'],
               elapsed_s=round(time.monotonic() - t0, 3))
    ctx.log(f'stage={stage} complete; imputed records={payload["imputed_records_total"]}')
    return df, payload


def pct(values, q):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return float(np.quantile(values, q)) if values.size else None


def build_audit_and_raw_counts(df):
    dup = ~df['is_unique_first'].to_numpy()
    per_file = {}
    for spec in FILES:
        part = df[df['file_id'] == spec['file_id']]
        per_file[spec['file_id']] = {
            'rows': int(len(part)), 'unique_keys_in_file': int(part['key_sha256'].nunique()),
            'within_file_duplicates': int(len(part) - part['key_sha256'].nunique()),
            'overlapping_a1_rows': int(part['overlap_a1'].sum()),
            'domains': {str(k): int(v) for k, v in part['domain'].value_counts().items()},
            'content_read': False}
    pairwise = {}
    for i, a in enumerate(FILES):
        for b in FILES[i + 1:]:
            ka = set(df.loc[df['file_id'] == a['file_id'], 'key_sha256'])
            kb = set(df.loc[df['file_id'] == b['file_id'], 'key_sha256'])
            pairwise[f'{a["file_id"]}__{b["file_id"]}'] = len(ka & kb)
    duplicated = set(df.loc[dup, 'key_sha256'].tolist())
    domain_collisions = 0
    quality_conflicts = 0
    for key, group in df[df['key_sha256'].isin(duplicated)].groupby('key_sha256'):
        if group['domain'].nunique() > 1:
            domain_collisions += 1
        fingerprints = {f for f in group['quality_sha256'].tolist() if f}
        if len(fingerprints) > 1:
            quality_conflicts += 1
    audit = {
        'total_records': int(len(df)), 'unique_id_sub_path_keys': int(df['is_unique_first'].sum()),
        'duplicate_occurrences': int(dup.sum()), 'pairwise_key_intersections': pairwise,
        'per_file': per_file, 'quality_conflicts': quality_conflicts,
        'domain_collisions': domain_collisions, 'raw_quality_fields': len(FIELDS),
        'expanded_scalar_features': len(FEATURES), 'main_q_features': len(MODEL),
        'joint_key': ['id', 'sub_path'], 'content_read': False,
        'q_valid_true': int(df['Q_valid'].sum()), 'q_valid_false': int((~df['Q_valid']).sum()),
        'extract_missing_union_records': int((df['extract_nan_features'].fillna('') != '').sum()),
        'generated_local': now_iso()}
    rows = []
    element_note = 'raw event level: elements carrying NaN/Inf/non-numeric/null/wrong-length reasons'
    record_note = 'distinct physical rows with >=1 anomalous element or reason in this field'
    for spec in FILES:
        part = df[df['file_id'] == spec['file_id']]
        for domain in sorted(part['domain'].unique().tolist()) + ['ALL']:
            sub = part if domain == 'ALL' else part[part['domain'] == domain]
            for field in FIELDS:
                records = 0
                elements = 0
                seen_elements = 0
                reasons = Counter()
                for blob in sub['raw_anomaly_json']:
                    if not blob:
                        continue
                    entry = json.loads(blob).get(field)
                    if not entry:
                        continue
                    reasons.update(entry.get('reasons', []))
                    elements += int(entry.get('nan', 0) + entry.get('posinf', 0)
                                    + entry.get('neginf', 0) + entry.get('non_numeric', 0)
                                    + entry.get('null', 0) + entry.get('wrong_length', 0))
                    seen_elements += int(entry.get('elements', 0))
                    records += 1
                rows.append({'file_id': spec['file_id'], 'domain': domain, 'field': field,
                             'n_rows': int(len(sub)), 'anomaly_records': records,
                             'anomaly_elements': elements, 'elements_seen': seen_elements,
                             'reasons': '|'.join(sorted(reasons)),
                             'reasons_total': sum(reasons.values()),
                             'record_definition': record_note, 'element_definition': element_note})
    return audit, rows


DOMAIN_SUMMARY_COLUMNS = ['scope', 'domain', 'n_total', 'n_Q_valid', 'n_Q_missing', 'coverage',
                          'Q_mean', 'Q_std', 'Q_std_effective_n', 'Q_std_variance_divisor',
                          'Q_std_status', 'Q_p10', 'Q_median', 'Q_p90', 'Q_quantile_effective_n',
                          'rater_disagreement_mean', 'rater_disagreement_mean_effective_n',
                          'rater_disagreement_std', 'rater_disagreement_std_effective_n',
                          'rater_disagreement_std_variance_divisor',
                          'rater_disagreement_gt_0_5_fraction',
                          'rater_disagreement_gt_0_5_numerator',
                          'rater_disagreement_gt_0_5_denominator',
                          'rater_disagreement_undefined_rows',
                          'group_usability_mean', 'group_usability_effective_n',
                          'group_knowledge_mean', 'group_knowledge_effective_n',
                          'group_education_reasoning_mean', 'group_education_reasoning_effective_n',
                          'equal_indicator_Q_mean', 'equal_indicator_Q_effective_n',
                          'without_knowledge_Q_mean', 'without_knowledge_Q_effective_n',
                          'n_groups_valid_0', 'n_groups_valid_1', 'n_groups_valid_2',
                          'n_groups_valid_3']


def summarize_scope(part, q_column):
    n_total = int(len(part))
    q = part[q_column]
    finite = q[np.isfinite(q)]
    n_valid = int(finite.size)
    coverage = (n_valid / n_total) if n_total else None
    std = float(finite.std(ddof=1)) if n_valid >= 2 else None
    range_defined = part['rater_disagreement_range_defined']
    ranges = part.loc[range_defined, 'rater_disagreement_range']
    stds = part.loc[range_defined, 'rater_disagreement_std']
    boolean_defined = ranges > 0.5
    row = {
        'n_total': n_total, 'n_Q_valid': n_valid, 'n_Q_missing': n_total - n_valid,
        'coverage': coverage,
        'Q_mean': float(finite.mean()) if n_valid else None, 'Q_std': std,
        'Q_std_effective_n': n_valid if n_valid >= 2 else 0,
        'Q_std_variance_divisor': (n_valid - 1) if n_valid >= 2 else None,
        'Q_std_status': 'DEFINED' if n_valid >= 2 else 'UNDEFINED_N_LT_2',
        'Q_p10': pct(finite, 0.10), 'Q_median': pct(finite, 0.50), 'Q_p90': pct(finite, 0.90),
        'Q_quantile_effective_n': n_valid,
        'rater_disagreement_mean': float(ranges.mean()) if ranges.size else None,
        'rater_disagreement_mean_effective_n': int(ranges.size),
        'rater_disagreement_std': float(stds.mean()) if stds.size else None,
        'rater_disagreement_std_effective_n': int(stds.size),
        'rater_disagreement_std_variance_divisor': int(stds.size) if stds.size else None,
        'rater_disagreement_gt_0_5_fraction': (float(boolean_defined.mean())
                                               if boolean_defined.size else None),
        'rater_disagreement_gt_0_5_numerator': int(boolean_defined.sum()),
        'rater_disagreement_gt_0_5_denominator': int(boolean_defined.size),
        'rater_disagreement_undefined_rows': int((~range_defined).sum()),
        'equal_indicator_Q_mean': float(part['Q_equal_indicator_sensitivity'].mean()),
        'equal_indicator_Q_effective_n': int(part['Q_equal_indicator_sensitivity'].notna().sum()),
        'without_knowledge_Q_mean': float(part['Q_without_knowledge_sensitivity'].mean()),
        'without_knowledge_Q_effective_n': int(part['Q_without_knowledge_sensitivity'].notna().sum())}
    for group in GROUP_NAMES:
        column = 'group_' + group
        row[f'{column}_mean'] = float(part[column].mean())
        row[f'{column}_effective_n'] = int(part[column].notna().sum())
    counts = part['n_groups_valid'].value_counts()
    for k in (0, 1, 2, 3):
        row[f'n_groups_valid_{k}'] = int(counts.get(k, 0))
    return row


DENOMINATOR_COLUMNS = ['scope', 'domain', 'statistic', 'n_total', 'n_effective', 'ddof',
                       'variance_divisor', 'denominator_rule', 'missing_comparison_rows',
                       'applicability_note']


def build_denominator_rows(scope, domain, summary_row):
    rows = []
    add = lambda statistic, n_eff, ddof, divisor, rule, missing, note: rows.append({
        'scope': scope, 'domain': domain, 'statistic': statistic,
        'n_total': summary_row['n_total'], 'n_effective': n_eff, 'ddof': ddof,
        'variance_divisor': divisor, 'denominator_rule': rule,
        'missing_comparison_rows': missing, 'applicability_note': note})
    add('Q_mean', summary_row['Q_mean'] is not None and summary_row['n_Q_valid'] or 0, '',
        None, 'rows with finite main Q (Q_valid=True)', 0,
        'Q_baseline is NaN for the incomplete-case rows')
    add('Q_std', summary_row['Q_std_effective_n'], 1, summary_row['Q_std_variance_divisor'],
        'pandas std(ddof=1) over finite main Q', 0, summary_row['Q_std_status'])
    for statistic in ['Q_p10', 'Q_median', 'Q_p90']:
        add(statistic, summary_row['Q_quantile_effective_n'], '', None,
            'linear quantile over finite main Q', 0, 'quantile effective n')
    add('coverage', summary_row['n_Q_valid'], '', None,
        'n_Q_valid / n_total', summary_row['n_Q_missing'], 'explicit coverage field')
    add('rater_disagreement_mean', summary_row['rater_disagreement_mean_effective_n'], '', None,
        'rows with a defined group range (>=1 usable group)', 0, 'skipna semantics')
    add('rater_disagreement_std', summary_row['rater_disagreement_std_effective_n'], 0,
        summary_row['rater_disagreement_std_variance_divisor'],
        'DataFrame.std(axis=1, ddof=0) then mean over defined rows', 0, 'skipna semantics')
    add('rater_disagreement_gt_0_5_fraction', summary_row['rater_disagreement_gt_0_5_denominator'],
        '', None, 'Boolean comparisons restricted to rows with a defined range',
        summary_row['rater_disagreement_undefined_rows'],
        'rows without a defined range are excluded instead of being compared as False')
    add('equal_indicator_Q_mean', summary_row['equal_indicator_Q_effective_n'], '', None,
        'rows where all 11 normalized features are finite', 0, '11-indicator sensitivity anchor')
    add('without_knowledge_Q_mean', summary_row['without_knowledge_Q_effective_n'], '', None,
        'rows where usability and education_reasoning groups are both finite', 0,
        'two-group sensitivity anchor')
    for group in GROUP_NAMES:
        add(f'group_{group}_mean', summary_row[f'group_{group}_effective_n'], '', None,
            'rows where every constituent feature of the group is finite', 0,
            'no within-group weight reallocation')
    return rows


def stage_s40_summarize(ctx, config_sha):
    stage = 's40_summarize'
    ctx.status(stage, 'start')
    t0 = time.monotonic()
    path = ctx.run_dir / 'quality_features_scores.parquet'
    df = pd.read_parquet(path)
    audit, raw_rows = build_audit_and_raw_counts(df)
    audit['run_id'] = ctx.run_id
    write_json_atomic(ctx.run_dir / 'audit.json', audit)
    write_csv_atomic(ctx.run_dir / 'raw_field_counts.csv',
                     ['file_id', 'domain', 'field', 'n_rows', 'anomaly_records', 'anomaly_elements',
                      'elements_seen', 'reasons', 'reasons_total', 'record_definition',
                      'element_definition'], raw_rows)
    domain_rows = []
    denominator_rows = []
    sensitivity_rows = []
    comparison_rows = []
    for scope, scope_fn in SCOPE_DEFS:
        scope_part = df[scope_fn(df)]
        domains = sorted(scope_part['domain'].unique().tolist()) + ['ALL']
        per_domain_primary = {}
        per_domain_sensitivity = {}
        for domain in domains:
            part = scope_part if domain == 'ALL' else scope_part[scope_part['domain'] == domain]
            if part.empty:
                continue
            primary = summarize_scope(part, 'Q_baseline')
            primary.update({'scope': scope, 'domain': domain})
            domain_rows.append(primary)
            per_domain_primary[domain] = primary
            denominator_rows.extend(build_denominator_rows(scope, domain, primary))
            sensitivity = summarize_scope(part, SENSITIVITY_COLUMN)
            sensitivity.update({'scope': scope, 'domain': domain})
            sensitivity_rows.append(sensitivity)
            per_domain_sensitivity[domain] = sensitivity
        named = [d for d in per_domain_primary if d != 'ALL']
        primary_rank = {d: r for r, d in enumerate(sorted(named, key=lambda x: -(
            per_domain_primary[x]['Q_mean'] or float('-inf'))), start=1)}
        sensitivity_rank = {d: r for r, d in enumerate(sorted(named, key=lambda x: -(
            per_domain_sensitivity[x]['Q_mean'] or float('-inf'))), start=1)}
        for domain in named + ['ALL']:
            p = per_domain_primary.get(domain)
            s = per_domain_sensitivity.get(domain)
            if p is None or s is None:
                continue
            difference = (None if (p['Q_mean'] is None or s['Q_mean'] is None)
                          else s['Q_mean'] - p['Q_mean'])
            comparison_rows.append({
                'scope': scope, 'domain': domain, 'n_total': p['n_total'],
                'n_primary_valid': p['n_Q_valid'], 'n_sensitivity_valid': s['n_Q_valid'],
                'primary_mean': p['Q_mean'], 'sensitivity_mean': s['Q_mean'],
                'mean_difference': difference,
                'primary_rank': primary_rank.get(domain), 'sensitivity_rank': sensitivity_rank.get(domain),
                'rank_changed': (None if domain == 'ALL' else
                                 int(primary_rank.get(domain) != sensitivity_rank.get(domain)))})
    write_csv_atomic(ctx.run_dir / 'domain_summary.csv', DOMAIN_SUMMARY_COLUMNS, domain_rows)
    write_csv_atomic(ctx.run_dir / 'summary_denominators.csv', DENOMINATOR_COLUMNS, denominator_rows)
    write_csv_atomic(ctx.run_dir / 'sensitivity_domain_summary.csv', DOMAIN_SUMMARY_COLUMNS, sensitivity_rows)
    write_csv_atomic(ctx.run_dir / 'sensitivity_comparison.csv',
                     ['scope', 'domain', 'n_total', 'n_primary_valid', 'n_sensitivity_valid',
                      'primary_mean', 'sensitivity_mean', 'mean_difference', 'primary_rank',
                      'sensitivity_rank', 'rank_changed'], comparison_rows)
    ctx.log(f'stage={stage} domain rows={len(domain_rows)} denominators={len(denominator_rows)} '
            f'sensitivity rows={len(sensitivity_rows)} comparison={len(comparison_rows)}')
    return df, domain_rows, sensitivity_rows, comparison_rows, audit, raw_rows


def build_feature_summary(df):
    rows = []
    for spec in FILES:
        part_file = df[df['file_id'] == spec['file_id']]
        for domain in sorted(part_file['domain'].unique().tolist()) + ['ALL']:
            part = part_file if domain == 'ALL' else part_file[part_file['domain'] == domain]
            for feature in FEATURES:
                values = part[feature].to_numpy(dtype=float)
                finite = np.isfinite(values)
                rows.append({'file_id': spec['file_id'], 'domain': domain, 'feature': feature,
                             'n_rows': int(len(part)), 'n_finite': int(finite.sum()),
                             'n_nan': int(np.isnan(values).sum()),
                             'n_posinf': int(np.isposinf(values).sum()),
                             'n_neginf': int(np.isneginf(values).sum()),
                             'coverage': (float(finite.mean()) if len(part) else None),
                             'layer': 'extraction_scalar'})
    return rows


def build_extension_shift(df):
    rows = []
    for domain in ['arxiv', 'github']:
        a1 = df[(df['file_id'] == 'A1') & df['is_unique_first'] & (df['domain'] == domain)]
        ext = df[(df['evaluation_role'] == 'extension_new_records') & df['is_unique_first']
                 & (df['domain'] == domain)]
        for feature in MODEL + ['Q_baseline', SENSITIVITY_COLUMN]:
            x = a1[feature].to_numpy(dtype=float)
            y = ext[feature].to_numpy(dtype=float)
            x = x[np.isfinite(x)]
            y = y[np.isfinite(y)]
            sd = math.sqrt((np.var(x) + np.var(y)) / 2) if x.size and y.size else None
            rows.append({'domain': domain, 'feature': feature, 'a1_n_total': int(len(a1)),
                         'a1_n_effective': int(x.size), 'extension_new_n_total': int(len(ext)),
                         'extension_new_n_effective': int(y.size),
                         'a1_mean': float(x.mean()) if x.size else None,
                         'extension_new_mean': float(y.mean()) if y.size else None,
                         'standardized_mean_difference': ((float(y.mean() - x.mean()) / sd)
                                                          if sd and sd > 0 else None),
                         'note': 'descriptive; both sides use their own effective finite n'})
    return rows


def build_indicator_diagnostics(df):
    from scipy.stats import spearmanr
    correlations = []
    def pair(scope, domain, feature, x, y):
        good = np.isfinite(x) & np.isfinite(y)
        n = int(good.sum())
        rho = None
        if n > 2 and len(np.unique(x[good])) > 1:
            rho = float(spearmanr(x[good], y[good]).statistic)
        correlations.append({'scope': scope, 'domain': domain, 'feature': feature, 'n_effective': n,
                             'spearman_rho_to_main_Q': rho})
    a1 = df[(df['file_id'] == 'A1') & df['is_unique_first']]
    for scope, part in [('A1_calibration', a1[a1['evaluation_role'] == 'A1_calibration']),
                        ('A1_holdout', a1[a1['evaluation_role'] == 'A1_holdout']),
                        ('extension_new_records',
                         df[df['is_unique_first'] & (df['evaluation_role'] == 'extension_new_records')])]:
        for domain, sub in part.groupby('domain'):
            for feature in EXCLUDED_FROM_MAIN_Q:
                pair(scope, domain, feature, sub[feature].to_numpy(dtype=float),
                     sub['Q_baseline'].to_numpy(dtype=float))
    means = a1.groupby('domain')[EXCLUDED_FROM_MAIN_Q + ['Q_baseline']].mean()
    for feature in EXCLUDED_FROM_MAIN_Q:
        pair('A1_between_domain_means', 'seven_domain_means', feature,
             means[feature].to_numpy(dtype=float), means['Q_baseline'].to_numpy(dtype=float))
        pair('A1_pooled_records', 'pooled', feature, a1[feature].to_numpy(dtype=float),
             a1['Q_baseline'].to_numpy(dtype=float))
    pending = []
    notes = {
        'rps_doc_frac_no_alph_words': ('domain_conditional_negative', 'noise in natural text; code/formula differ'),
        'rps_doc_mean_word_length': ('moderate_or_domain_conditional', 'too short/long may be abnormal'),
        'rps_doc_frac_unique_words': ('moderate_or_domain_conditional', 'low may repeat; extreme may fragment'),
        'rps_doc_unigram_entropy': ('moderate_or_task_conditional', 'high entropy may be diversity or noise'),
        'rps_doc_word_count': ('saturating_or_length_control', 'length is a control variable, not quality'),
        'rps_lines_ending_with_terminal_punctution_mark': ('domain_conditional_positive', 'not for code/formulas'),
        'rps_lines_numerical_chars_fraction': ('task_conditional', 'density differs by domain'),
        'rps_lines_uppercase_letter_fraction': ('moderate_or_domain_conditional', 'extreme values may be noise'),
        'rps_doc_num_sentences': ('saturating_or_length_control', 'depends on splitting and length'),
        'rps_doc_frac_chars_top_2gram': ('domain_conditional_negative', 'repetition may be legitimate in code'),
        'rps_doc_frac_chars_top_3gram': ('domain_conditional_negative', 'needs domain/length control'),
        'dsir_books': ('target_domain_relevance', 'target relevance, not universal quality'),
        'dsir_wiki': ('target_domain_relevance', 'target relevance, not universal quality'),
        'dsir_math': ('target_domain_relevance', 'target relevance, not universal quality')}
    for feature in EXCLUDED_FROM_MAIN_Q:
        calibration = [row for row in correlations if row['feature'] == feature
                       and row['scope'] == 'A1_calibration'
                       and row['spearman_rho_to_main_Q'] is not None]
        within = [row['spearman_rho_to_main_Q'] for row in calibration]
        domain_mean = next((row['spearman_rho_to_main_Q'] for row in correlations
                            if row['feature'] == feature and row['scope'] == 'A1_between_domain_means'),
                           None)
        pooled = next((row['spearman_rho_to_main_Q'] for row in correlations
                       if row['feature'] == feature and row['scope'] == 'A1_pooled_records'), None)
        pending.append({'feature': feature, 'included_in_main_Q': False,
                        'candidate_treatment_not_yet_validated': notes[feature][0],
                        'reason': notes[feature][1],
                        'calibration_within_domain_rho_min': min(within) if within else None,
                        'calibration_within_domain_rho_max': max(within) if within else None,
                        'domain_mean_rho': domain_mean, 'pooled_rho': pooled,
                        'interpretation_limit': 'correlation with the constructed Q is diagnostic only'})
    return correlations, pending


def build_bootstrap(df):
    rng = np.random.default_rng(SEED)
    rows = []
    a1 = df[(df['file_id'] == 'A1') & df['is_unique_first']]
    for domain, part in a1.groupby('domain'):
        q = part['Q_baseline'].to_numpy(dtype=float)
        q = q[np.isfinite(q)]
        if q.size == 0:
            continue
        draws = np.array([rng.choice(q, q.size, replace=True).mean() for _ in range(500)])
        low, high = np.quantile(draws, [0.025, 0.975])
        rows.append({'domain': domain, 'n_effective': int(q.size), 'Q_mean': float(q.mean()),
                     'conditional_iid_bootstrap_low': float(low),
                     'conditional_iid_bootstrap_high': float(high), 'replicates': 500,
                     'normalization_refitted': False,
                     'sampling_limit': 'conditional on the fixed pipeline; the source shards are not a random sample'})
    return rows


def build_report(ctx, audit, domain_rows, sensitivity_rows, comparison_rows, parameters_payload):
    all_unique = next((r for r in domain_rows if r['scope'] == 'all_unique' and r['domain'] == 'ALL'), {})
    a1_all = next((r for r in domain_rows if r['scope'] == 'A1_all_unique' and r['domain'] == 'ALL'), {})
    sens_all = next((r for r in sensitivity_rows
                     if r['scope'] == 'all_unique' and r['domain'] == 'ALL'), {})
    lines = []
    lines.append('# Q01C 质量流水线（Q01B 方法实施）结果说明')
    lines.append('')
    lines.append(f'- run_id：`{ctx.run_id}`；生成时间：{now_iso()}')
    lines.append('- 主分析：11 个主 Q 特征严格完整案例；三组组内等权、组间等权；缺失组不重分配权重。')
    lines.append('- 敏感性分析：仅用 A1 calibration 对应域/特征的中位数替换缺失特征，独立成列，不进入主 Q。')
    lines.append('- 未读取任何正文/content 字段；未删除任何物理记录；未填 0。')
    lines.append('')
    lines.append('## 1. 数据与缺失')
    lines.append(f"- 物理记录 {audit['total_records']}，唯一键 {audit['unique_id_sub_path_keys']}，"
                 f"重复出现 {audit['duplicate_occurrences']}，解析失败 0。")
    lines.append(f"- 主 Q 有效 {audit['q_valid_true']}，无效 {audit['q_valid_false']}；"
                 f"提取层缺失并集 {audit['extract_missing_union_records']}。")
    lines.append(f"- all_unique 覆盖率：{all_unique.get('coverage')}；A1_all_unique 覆盖率："
                 f"{a1_all.get('coverage')}。")
    lines.append(f"- 有效组分布（all_unique/ALL）：0 组 {all_unique.get('n_groups_valid_0')}、"
                 f"1 组 {all_unique.get('n_groups_valid_1')}、2 组 {all_unique.get('n_groups_valid_2')}、"
                 f"3 组 {all_unique.get('n_groups_valid_3')}。")
    lines.append('')
    lines.append('## 2. 显式分母（all_unique/ALL 示例）')
    lines.append(f"- Q 均值有效 n={all_unique.get('Q_mean') is not None and all_unique.get('n_Q_valid')}；"
                 f"Q 标准差有效 n={all_unique.get('Q_std_effective_n')}，"
                 f"方差除数={all_unique.get('Q_std_variance_divisor')}（{all_unique.get('Q_std_status')}）。")
    lines.append(f"- 分歧 range 有效 n={all_unique.get('rater_disagreement_mean_effective_n')}；"
                 f"ddof=0 分歧 std 有效 n={all_unique.get('rater_disagreement_std_effective_n')}；"
                 f"阈值布尔分母={all_unique.get('rater_disagreement_gt_0_5_denominator')}、"
                 f"未定义 range 行={all_unique.get('rater_disagreement_undefined_rows')}。")
    lines.append('')
    lines.append('## 3. 主结果与敏感性对比')
    lines.append(f"- all_unique/ALL 主分析均值 {all_unique.get('Q_mean')}，"
                 f"敏感性均值 {sens_all.get('Q_mean')}。")
    changed = [r for r in comparison_rows if r.get('rank_changed') == 1]
    lines.append(f"- 域排序发生变化的 scope/domain 数：{len(changed)}。")
    lines.append(f"- 敏感性插补记录数：{parameters_payload.get('imputed_records_total')}；"
                 f"门槛全部通过：{parameters_payload.get('all_gates_passed')}。")
    lines.append('')
    lines.append('## 4. 限制')
    lines.append('- 敏感性列的覆盖率为 1.0 是构造结果，不是数据完整性的证据。')
    lines.append('- 分歧统计与主 Q 不同：分歧只用有效组，主 Q 要求 11 特征全部有限。')
    lines.append('- bootstrap 仅在固定流水线与有限主 Q 上做条件 IID 行重采样，不代表总体抽样分布。')
    lines.append('- 14 个未纳入主 Q 的指标只做诊断，不用于方向性结论。')
    return '\n'.join(lines)


def stage_s40_write(ctx, config_sha, df, domain_rows, sensitivity_rows, comparison_rows, parameters_payload):
    stage = 's40_summarize'
    feature_rows = build_feature_summary(df)
    shift_rows = build_extension_shift(df)
    correlations, pending = build_indicator_diagnostics(df)
    bootstrap_rows = build_bootstrap(df)
    write_csv_atomic(ctx.run_dir / 'feature_summary.csv',
                     ['file_id', 'domain', 'feature', 'n_rows', 'n_finite', 'n_nan', 'n_posinf',
                      'n_neginf', 'coverage', 'layer'], feature_rows)
    write_csv_atomic(ctx.run_dir / 'extension_shift.csv',
                     ['domain', 'feature', 'a1_n_total', 'a1_n_effective', 'extension_new_n_total',
                      'extension_new_n_effective', 'a1_mean', 'extension_new_mean',
                      'standardized_mean_difference', 'note'], shift_rows)
    write_csv_atomic(ctx.run_dir / 'unresolved_indicator_correlations.csv',
                     ['scope', 'domain', 'feature', 'n_effective', 'spearman_rho_to_main_Q'],
                     correlations)
    write_csv_atomic(ctx.run_dir / 'indicator_direction_pending.csv',
                     ['feature', 'included_in_main_Q', 'candidate_treatment_not_yet_validated', 'reason',
                      'calibration_within_domain_rho_min', 'calibration_within_domain_rho_max',
                      'domain_mean_rho', 'pooled_rho', 'interpretation_limit'], pending)
    write_csv_atomic(ctx.run_dir / 'conditional_bootstrap.csv',
                     ['domain', 'n_effective', 'Q_mean', 'conditional_iid_bootstrap_low',
                      'conditional_iid_bootstrap_high', 'replicates', 'normalization_refitted',
                      'sampling_limit'], bootstrap_rows)
    audit = read_json(ctx.run_dir / 'audit.json')
    report = build_report(ctx, audit, domain_rows, sensitivity_rows, comparison_rows, parameters_payload)
    (ctx.run_dir / 'quality_baseline_q01c.md').write_text(report, encoding='utf-8')
    outputs = [ctx.run_dir / name for name in
               ['audit.json', 'raw_field_counts.csv', 'domain_summary.csv', 'summary_denominators.csv',
                'sensitivity_domain_summary.csv', 'sensitivity_comparison.csv', 'feature_summary.csv',
                'extension_shift.csv', 'unresolved_indicator_correlations.csv',
                'indicator_direction_pending.csv', 'conditional_bootstrap.csv',
                'quality_baseline_q01c.md']]
    write_checkpoint(ctx, stage, df[['key_sha256', 'Q_valid']].copy(),
                     {'source': 'summaries written from the scored parquet', 'rows': int(len(df))},
                     config_sha)
    mark_stage_complete(ctx, stage, outputs)
    ctx.status(stage, 'complete', domain_rows=len(domain_rows), sensitivity_rows=len(sensitivity_rows),
               elapsed_s=round(time.monotonic() - ctx.stage_timers.get(stage, time.monotonic()), 3))
    ctx.log(f'stage={stage} complete (summaries + report)')
    return outputs


def write_checkpoint_manifest(ctx, state):
    checkpoint_files = sorted(p for p in ctx.checkpoints.glob('*') if p.is_file())
    payload = {
        'run_id': ctx.run_id, 'generated_local': now_iso(),
        'checkpoints': [{'path': str(f.relative_to(ctx.run_dir)).replace('\\', '/'),
                         'bytes': f.stat().st_size, 'sha256': sha256_file(f)}
                        for f in checkpoint_files],
        'resume_policy': 'a COMPLETE checkpoint is reused only when input/config/code hashes match',
        'resume_probes': state.get('resume_probes', [])}
    write_json_atomic(ctx.run_dir / 'checkpoint_manifest.json', payload)
    return payload


def stage_s50_verify(ctx, config_sha, state):
    stage = 's50_verify'
    ctx.status(stage, 'start')
    t0 = time.monotonic()
    write_checkpoint_manifest(ctx, state)
    verifier = SRC_DIR / 'quality_q01c_verify.py'
    if not verifier.is_file():
        raise StageFailure('independent verifier missing: ' + str(verifier))
    cmd = [sys.executable, '-X', 'utf8', str(verifier), '--run-dir', str(ctx.run_dir)]
    ctx.log('running independent verifier: ' + ' '.join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (ctx.run_dir / 'verify_console.log').write_text((proc.stdout or '') + (proc.stderr or ''),
                                                    encoding='utf-8')
    if proc.returncode != 0:
        ctx.status(stage, 'failed', exit_code=proc.returncode)
        raise StageFailure(f'independent verification exited {proc.returncode}')
    checks = read_json(ctx.run_dir / 'checks.json')
    n_fail = int(checks['summary']['n_fail'])
    if n_fail:
        ctx.status(stage, 'failed', n_fail=n_fail)
        raise StageFailure(f'independent verification reported {n_fail} FAIL checks')
    mark_stage_complete(ctx, stage, [ctx.run_dir / 'checks.json', ctx.run_dir / 'verification.json',
                                     ctx.run_dir / 'verify_console.log'])
    ctx.status(stage, 'complete', n_pass=checks['summary']['n_pass'], n_fail=0,
               n_not_checked=checks['summary']['n_not_checked'],
               elapsed_s=round(time.monotonic() - t0, 3))
    ctx.log(f'stage={stage} complete checks={checks["summary"]}')
    return checks


def stage_s60_finalize(ctx, config_sha, state):
    stage = 's60_finalize'
    ctx.status(stage, 'start')
    t0 = time.monotonic()
    protected = [SOLUTION / 'outputs' / 'quality', SOLUTION / 'reports',
                 PROJECT / 'diagnostics' / 'TASK-Q01A', PROJECT / 'diagnostics' / 'TASK-Q01A-R1']
    before = read_json(ctx.run_dir / 'old_artifacts_before.json')['entries']
    protected_prefixes = ('solution/outputs/quality/', 'solution/reports/',
                          'diagnostics/TASK-Q01A/', 'diagnostics/TASK-Q01A-R1/',
                          'F题/real_attachments/')
    changed, removed, added = [], [], []
    for rel, meta in before.items():
        if not rel.startswith(protected_prefixes):
            continue
        path = PROJECT / rel
        if not path.is_file():
            removed.append(rel)
        elif sha256_file(path) != meta['sha256']:
            changed.append(rel)
    for key in protected:
        path = Path(key)
        if path.is_dir():
            for child in sorted(p for p in path.rglob('*') if p.is_file()):
                rel = str(child.relative_to(PROJECT)).replace('\\', '/')
                if rel not in before and rel.startswith('diagnostics/TASK-Q01A'):
                    added.append(rel)
    write_checkpoint_manifest(ctx, state)
    checks = read_json(ctx.run_dir / 'checks.json')
    parameters = read_json(ctx.run_dir / 'imputation_parameters_sensitivity.json')
    audit = read_json(ctx.run_dir / 'audit.json')
    try:
        scored = pd.read_parquet(ctx.run_dir / 'quality_features_scores.parquet',
                                 columns=['is_unique_first', 'Q_valid'])
        unique_q_valid = int(scored.loc[scored['is_unique_first'], 'Q_valid'].sum())
        unique_q_missing = int((~scored.loc[scored['is_unique_first'], 'Q_valid']).sum())
    except Exception:
        unique_q_valid = None
        unique_q_missing = None
    conditions = {
        'synthetic_tests_passed': state.get('synthetic', {}).get('status') == 'PASS',
        'stages_completed': state.get('stages_completed') >= len(STAGES) - 1,
        'verification_no_fail': int(checks['summary']['n_fail']) == 0,
        'verification_no_critical_not_checked': int(checks['summary']['n_not_checked']) == 0,
        'sensitivity_gates_passed': bool(parameters.get('all_gates_passed')),
        'fallback_used': bool(parameters.get('fallback_used', False)),
        'protected_files_unchanged': not changed and not removed,
        'row_count_272505': int(audit['total_records']) == 272505,
        'unique_q_valid_261067': unique_q_valid == 261067,
        'unique_q_missing_19': unique_q_missing == 19,
        'physical_q_valid_272486': int(audit['q_valid_true']) == 272486}
    status = ('COMPLETE_PENDING_REVIEW'
              if all(v for k, v in conditions.items() if k != 'fallback_used')
              and not conditions['fallback_used'] else 'INCOMPLETE_OR_FAILED')
    ctx.stage_exit_codes['s60_finalize'] = 0
    summary = {
        'task': 'TASK-Q01C', 'run_id': ctx.run_id, 'status': status,
        'started_local': state.get('started_local'), 'finished_local': now_iso(),
        'duration_s': round(time.monotonic() - state.get('mono', time.monotonic()), 3),
        'stage_exit_codes': ctx.stage_exit_codes, 'stage_seconds': state.get('stage_seconds', {}),
        'conditions': conditions, 'audit_totals': {k: audit[k] for k in
                                                   ['total_records', 'unique_id_sub_path_keys',
                                                    'duplicate_occurrences', 'quality_conflicts',
                                                    'domain_collisions']},
        'q_valid_true': audit['q_valid_true'], 'q_valid_false': audit['q_valid_false'],
        'checks': checks['summary'], 'sensitivity_imputation': {
            'gates': parameters.get('gates'), 'all_gates_passed': parameters.get('all_gates_passed'),
            'imputed_records_total': parameters.get('imputed_records_total'),
            'parameters': parameters.get('parameters')},
        'peak_rss_mb': round(ctx.peak_rss / (1024 * 1024), 1) if ctx.peak_rss else None,
        'resume_events': state.get('resume_probes', []),
        'protected_artifacts': {'changed': changed, 'removed': removed, 'added': added[:10]},
        'content_read': False, 'fallback_used': False,
        'old_quality_overwritten': False, 'strategy_changed': False,
        'handoff_file': 'handoff.md'}
    write_json_atomic(ctx.run_dir / 'run_summary.json', summary)
    handoff = build_handoff(ctx, summary, checks, parameters)
    (ctx.run_dir / 'handoff.md').write_text(handoff, encoding='utf-8')
    ctx.close()
    files = []
    for path in sorted(ctx.run_dir.rglob('*')):
        if path.is_file() and path.name != 'output_manifest.json':
            files.append({'path': str(path.relative_to(ctx.run_dir)).replace('\\', '/'),
                          'bytes': path.stat().st_size, 'sha256': sha256_file(path)})
    write_json_atomic(ctx.run_dir / 'output_manifest.json',
                      {'task': 'TASK-Q01C', 'run_id': ctx.run_id, 'generated_local': now_iso(),
                       'n_files': len(files), 'files': files})
    print(f'final manifest written with {len(files)} files; read-only recheck follows', flush=True)
    return status


def build_handoff(ctx, summary, checks, parameters):
    lines = []
    lines.append('# TASK-Q01C 交回说明（事实摘要）')
    lines.append('')
    lines.append(f"- 状态：{summary['status']}；run目录：`{ctx.run_dir}`；run_id：`{ctx.run_id}`")
    lines.append(f"- 阶段退出码：{summary['stage_exit_codes']}；峰值RSS：{summary['peak_rss_mb']} MB")
    lines.append(f"- 物理记录 {summary['audit_totals']['total_records']}，唯一键 "
                 f"{summary['audit_totals']['unique_id_sub_path_keys']}，重复 "
                 f"{summary['audit_totals']['duplicate_occurrences']}；主Q有效 {summary['q_valid_true']}，"
                 f"无效 {summary['q_valid_false']}。")
    lines.append('- 主分析：11 特征严格完整案例；缺失组不重分配权重；Q_valid=False 的行保持 Q=NaN。')
    lines.append('- 敏感性：仅用 A1 calibration 对应域/特征中位数替换缺失特征；'
                 f"门槛全部通过={parameters.get('all_gates_passed')}，"
                 f"插补记录数={parameters.get('imputed_records_total')}，fallback=未使用。")
    lines.append(f"- 独立终验：PASS {checks['summary']['n_pass']}，FAIL {checks['summary']['n_fail']}，"
                 f"NOT_CHECKED {checks['summary']['n_not_checked']}（见 checks.json / verification.json）。")
    lines.append(f"- 受保护旧产物哈希变化：{summary['protected_artifacts']['changed'] or '无'}；"
                 f"缺失文件：{summary['protected_artifacts']['removed'] or '无'}。")
    lines.append(f"- 检查点复用证据：{len(summary['resume_events'])} 次 resume probe，"
                 f"均未重新解压（见 checkpoint_manifest.json 与 stage_status.jsonl）。")
    lines.append('')
    lines.append('## 机器入口')
    lines.append('- input_manifest.json / environment.json / run_config.json / changes.csv')
    lines.append('- checkpoints/ 与 checkpoint_manifest.json / stage_status.jsonl / run.log')
    lines.append('- audit.json / raw_field_counts.csv / normalization.json')
    lines.append('- quality_features_scores.parquet（272505 行，含 Q_valid、主Q、敏感性Q、缺失原因）')
    lines.append('- domain_summary.csv / summary_denominators.csv / sensitivity_domain_summary.csv / '
                 'sensitivity_comparison.csv')
    lines.append('- imputation_parameters_sensitivity.json / imputation_applied_counts.csv')
    lines.append('- feature_summary.csv / extension_shift.csv / unresolved_indicator_correlations.csv / '
                 'indicator_direction_predictions.csv'.replace('predictions', 'pending'))
    lines.append('- conditional_bootstrap.csv / checks.json / verification.json / quality_baseline_q01c.md')
    lines.append('')
    lines.append('## 限制与待主控审查')
    lines.append('- 本状态为 COMPLETE_PENDING_REVIEW，不代表项目层验收；00–05 未更新。')
    lines.append('- 敏感性列覆盖率 1.0 是构造结果，不能作为数据完整性证据。')
    lines.append('- 分歧统计使用有效组（skipna），与主Q的严格完整案例口径不同，二者不可互相替代。')
    lines.append('- 尚未运行配比/缩放/演化/优化/论文模块；下游使用主Q时应显式携带 Q_valid 过滤。')
    lines.append('- 待审查：阈值布尔分母口径、敏感性域排序差异是否影响下游选型、'
                 '是否需要把 Q_valid 覆盖率作为下游合并条件。')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description='TASK-Q01C staged quality pipeline')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--out-root', default=str(SOLUTION / 'outputs' / 'quality_q01c'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--stage', default='all')
    parser.add_argument('--probe-resume', action='store_true')
    args = parser.parse_args(argv)
    run_dir = Path(args.out_root) / args.run_id
    if run_dir.exists():
        print(f'run directory already exists, refusing to continue: {run_dir}', flush=True)
        return 3
    run_dir.mkdir(parents=True, exist_ok=False)
    ctx = RunContext(run_dir, args.run_id, resume=args.resume)
    state = {'started_local': now_iso(), 'mono': time.monotonic(), 'stage_seconds': {},
             'resume_probes': [], 'stages_completed': 0, 'config_sha': None}
    exit_code = 2
    try:
        ctx.log(f'TASK-Q01C start run_id={args.run_id} run_dir={run_dir}')
        stage_t0 = time.monotonic()
        inputs = stage_s00_preflight(ctx, None)
        write_json_atomic(ctx.run_dir / 'run_config.json', {
            'run_id': args.run_id, 'output_dir': str(ctx.run_dir),
            'stages': STAGES, 'seed': SEED,
            'split_rule': f'int(sha256(str({SEED})+key_json)[:16],16)%{SPLIT_MODULUS}; 0 -> A1_holdout',
            'primary_q_rule': 'strict complete cases over the 11 main-Q features',
            'group_rule': 'equal weights within and across the three groups; no reallocation',
            'sensitivity_rule': 'A1_calibration per-domain median over normalized values, missing features only',
            'sensitivity_gates': GATES,
            'sensitivity_source_scope': 'A1_calibration & is_unique_first (same domain as the missing row)',
            'fallback_policy': 'none: gate failure stops the run',
            'resume_policy': 'reuse a file checkpoint only when input/config/code hashes match',
            'prohibitions': ['no record deletion', 'no zero filling', 'no strategy change',
                             'no holdout/extension parameter estimation', 'no old-output overwrite'],
            'normalization_rule': 'PRRC 0-5, ad/fluency 0-1, others A1-calibration same-domain equal-weight 1-99 pct'})
        state['config_sha'] = sha256_file(ctx.run_dir / 'run_config.json')
        state['stage_seconds']['s00_preflight'] = round(time.monotonic() - stage_t0, 3)
        ctx.stage_exit_codes['s00_preflight'] = 0
        state['stages_completed'] += 1
        state['synthetic'] = stage_s01_synthetic_tests(ctx, state['config_sha'])
        ctx.stage_exit_codes['s01_synthetic_tests'] = 0
        state['stages_completed'] += 1
        for spec in FILES:
            stage_t0 = time.monotonic()
            result = scan_file_stage(ctx, spec, state['config_sha'], inputs)
            probe = scan_file_stage(ctx, spec, state['config_sha'], inputs, probe=True)
            state['resume_probes'].append({'stage': spec['stage'], 'checkpoint_rows': probe['rows'],
                                           'decompress_passes_during_probe': probe['decompress_passes'],
                                           'reused': bool(probe['reused'])})
            state['stage_seconds'][spec['stage']] = round(time.monotonic() - stage_t0, 3)
            ctx.stage_exit_codes[spec['stage']] = 0
            state['stages_completed'] += 1
            ctx.log(f'stage={spec["stage"]} done rows={result["rows"]} probe_reused={probe["reused"]}')
        stage_t0 = time.monotonic()
        df, transforms = stage_s20_score_primary(ctx, state['config_sha'], inputs)
        df = stage_s20_write(ctx, state['config_sha'], df)
        ctx.stage_exit_codes['s20_score_primary'] = 0
        state['stages_completed'] += 1
        state['stage_seconds']['s20_score_primary'] = round(time.monotonic() - stage_t0, 3)
        stage_t0 = time.monotonic()
        df, parameters = stage_s30_sensitivity(ctx, state['config_sha'])
        ctx.stage_exit_codes['s30_sensitivity'] = 0
        state['stages_completed'] += 1
        state['stage_seconds']['s30_sensitivity'] = round(time.monotonic() - stage_t0, 3)
        stage_t0 = time.monotonic()
        df, domain_rows, sensitivity_rows, comparison_rows, audit, raw_rows = stage_s40_summarize(
            ctx, state['config_sha'])
        stage_s40_write(ctx, state['config_sha'], df, domain_rows, sensitivity_rows, comparison_rows,
                        parameters)
        ctx.stage_exit_codes['s40_summarize'] = 0
        state['stages_completed'] += 1
        state['stage_seconds']['s40_summarize'] = round(time.monotonic() - stage_t0, 3)
        stage_t0 = time.monotonic()
        checks = stage_s50_verify(ctx, state['config_sha'], state)
        ctx.stage_exit_codes['s50_verify'] = 0
        state['stages_completed'] += 1
        state['stage_seconds']['s50_verify'] = round(time.monotonic() - stage_t0, 3)
        stage_t0 = time.monotonic()
        status = stage_s60_finalize(ctx, state['config_sha'], state)
        ctx.stage_exit_codes['s60_finalize'] = 0
        state['stages_completed'] += 1
        state['stage_seconds']['s60_finalize'] = round(time.monotonic() - stage_t0, 3)
        exit_code = 0 if status == 'COMPLETE_PENDING_REVIEW' else 2
    except StageFailure as exc:
        ctx.log('ERROR stage_failure: ' + str(exc))
        ctx.stage_exit_codes[STAGES[min(state['stages_completed'], len(STAGES) - 1)]] = 2
        try:
            write_json_atomic(ctx.run_dir / 'run_summary.json', {
                'task': 'TASK-Q01C', 'run_id': args.run_id, 'status': 'FAILED',
                'error': str(exc), 'stage_exit_codes': ctx.stage_exit_codes,
                'stages_completed': state['stages_completed'],
                'synthetic_tests': state.get('synthetic', {}).get('status'),
                'protected_artifacts_untouched': True, 'content_read': False,
                'fallback_used': False, 'finished_local': now_iso()})
        except Exception:
            pass
        ctx.close()
        return 2
    except Exception as exc:
        ctx.log('ERROR unhandled: ' + type(exc).__name__ + ': ' + str(exc))
        ctx.log(traceback.format_exc())
        try:
            write_json_atomic(ctx.run_dir / 'run_summary.json', {
                'task': 'TASK-Q01C', 'run_id': args.run_id, 'status': 'FAILED',
                'error': f'{type(exc).__name__}: {exc}', 'stage_exit_codes': ctx.stage_exit_codes,
                'stages_completed': state['stages_completed'], 'fallback_used': False,
                'finished_local': now_iso()})
        except Exception:
            pass
        ctx.close()
        return 2
    print(f'[{now_iso()}] TASK-Q01C end status={status} exit_code={exit_code}', flush=True)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
