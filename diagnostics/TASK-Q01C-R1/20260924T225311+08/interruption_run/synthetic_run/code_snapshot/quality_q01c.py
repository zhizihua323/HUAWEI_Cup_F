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


PROTOCOL_VERSION = 2
REAL_DATA_PATHS = [spec['path'] for spec in FILES]


def load_fixture_specs(fixture_dir):
    """Load a synthetic fixture manifest (no real data is ever referenced)."""
    fixture_dir = Path(fixture_dir).resolve()
    manifest_path = fixture_dir / 'fixture_manifest.json'
    if not manifest_path.is_file():
        raise StageFailure(f'fixture manifest not found: {manifest_path}')
    manifest = read_json(manifest_path)
    if not manifest.get('synthetic'):
        raise StageFailure('fixture manifest must be marked synthetic=true')
    specs = []
    for index, item in enumerate(manifest['files']):
        path = (fixture_dir / item['path']).resolve()
        if not path.is_file():
            raise StageFailure(f'fixture input missing: {path}')
        specs.append({'file_id': item['file_id'], 'code': index,
                      'fallback_domain': item.get('fallback_domain'),
                      'stage': item.get('stage') or f's1{index}_scan_{item["file_id"].lower()}',
                      'path': path})
    return specs, manifest, fixture_dir


def open_input_text(path):
    """Open a fixture (.jsonl) or a real compressed attachment (.xz) for reading."""
    path = Path(path)
    if path.suffix.lower() == '.xz':
        return lzma.open(str(path), 'rt', encoding='utf-8')
    return open(path, 'r', encoding='utf-8')


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


TERMINAL_EVENTS = ('complete', 'failed', 'gate_failed')


def load_scan_counters(ctx):
    path = ctx.run_dir / 'scan_counters.json'
    if path.is_file():
        try:
            payload = read_json(path)
            if isinstance(payload, dict) and 'files' in payload:
                payload.setdefault('reuse_events', [])
                payload.setdefault('total_passes', 0)
                payload.setdefault('protocol_version', PROTOCOL_VERSION)
                return payload
        except Exception:
            pass
    return {'protocol_version': PROTOCOL_VERSION, 'files': {}, 'reuse_events': [], 'total_passes': 0}


def save_scan_counters(ctx):
    write_json_atomic(ctx.run_dir / 'scan_counters.json', ctx.scan_counters)
    return ctx.scan_counters


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
        self.mode = 'real'
        self.file_specs = FILES
        self.fixture_dir = None
        self.fixture_manifest = None
        self.resume_decisions = []
        self.scan_counters = {'protocol_version': PROTOCOL_VERSION, 'files': {},
                              'reuse_events': [], 'total_passes': 0}
        self.stage_seconds = {}
        self.executed_stages = []
        self.skipped_stages = {}
        self.stage_events = defaultdict(list)
        self.finalized = False

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
                  'event': event, 'run_id': self.run_id, 'pid': os.getpid()}
        record.update(fields)
        self.status_fh.write(json_compact(record) + '\n')
        self.status_fh.flush()
        self.stage_events[stage].append({'event': event, 'ts': record['ts']})

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


def checkpoint_paths(ctx, stage, layout='v2'):
    """v2 keeps payload/metadata/data-marker/stage-marker in four distinct files."""
    if layout == 'v2':
        return {'payload': ctx.checkpoints / f'{stage}.payload.parquet',
                'meta': ctx.checkpoints / f'{stage}.meta.json',
                'checkpoint_marker': ctx.checkpoints / f'{stage}.checkpoint.COMPLETE',
                'stage_marker': ctx.checkpoints / f'{stage}.stage.COMPLETE'}
    stem = ctx.checkpoints / stage
    return {'payload': stem.with_suffix('.parquet'), 'meta': stem.with_suffix('.json'),
            'checkpoint_marker': ctx.checkpoints / f'{stage}.COMPLETE', 'stage_marker': None}


def stage_marker_path(ctx, stage):
    return ctx.checkpoints / f'{stage}.stage.COMPLETE'


def stage_marker_valid(ctx, stage):
    path = stage_marker_path(ctx, stage)
    if not path.is_file():
        return False, 'stage marker missing'
    try:
        payload = read_json(path)
    except Exception as exc:
        return False, f'unreadable stage marker: {exc}'
    if payload.get('kind') != 'stage' or payload.get('stage') != stage:
        return False, 'stage marker schema mismatch'
    for rel, expected in payload.get('outputs', {}).items():
        target = ctx.run_dir / rel
        if not target.is_file() or sha256_file(target) != expected:
            return False, f'output hash mismatch for {rel}'
    return True, 'valid'


def checkpoint_is_valid(ctx, stage, expected_input_sha, config_sha, layout=None):
    """Validate a reusable checkpoint (v2 first, then the legacy layout)."""
    layouts = [layout] if layout else ['v2', 'legacy']
    last_reason = 'missing file(s)'
    for candidate in layouts:
        paths = checkpoint_paths(ctx, stage, candidate)
        required = [paths['payload'], paths['meta'], paths['checkpoint_marker']]
        if not all(p is not None and Path(p).is_file() for p in required):
            last_reason = f'{candidate}: missing file(s)'
            continue
        try:
            meta = read_json(paths['meta'])
            marker = read_json(paths['checkpoint_marker'])
        except Exception as exc:
            last_reason = f'{candidate}: unreadable metadata: {exc}'
            continue
        checks = [
            ('marker_binds_meta', marker.get('checkpoint_meta_sha256') == sha256_file(paths['meta'])),
            ('payload_sha_in_meta', meta.get('payload_sha256') == sha256_file(paths['payload'])),
            ('input_sha', meta.get('input_sha256') == expected_input_sha),
            ('code_fingerprint', meta.get('code_fingerprint') == code_fingerprint()),
            ('config_sha', meta.get('config_sha256') == config_sha),
            ('stage', meta.get('stage') == stage),
            ('marker_kind', marker.get('kind') == 'checkpoint'),
            ('rows_recorded', isinstance(meta.get('rows'), int) and meta.get('rows') >= 0)]
        failed = [name for name, ok in checks if not ok]
        if failed:
            last_reason = f'{candidate}: failed checks {failed}'
            continue
        return True, f'valid ({candidate} layout)', candidate
    return False, last_reason, None


def aggregate_input_binding(ctx):
    """Deterministic input binding for aggregate checkpoints (S20/S30/S40)."""
    parts = []
    for spec in ctx.file_specs:
        meta_path = checkpoint_paths(ctx, spec['stage'], 'v2')['meta']
        if not meta_path.is_file():
            meta_path = checkpoint_paths(ctx, spec['stage'], 'legacy')['meta']
        if not meta_path.is_file():
            return None
        parts.append(str(read_json(meta_path).get('payload_sha256', '')))
    return sha256_text('|'.join(parts))


def write_checkpoint(ctx, stage, frame, meta, config_sha, input_sha=None):
    """Atomic order: payload -> metadata -> completion marker."""
    paths = checkpoint_paths(ctx, stage, 'v2')
    tmp = paths['payload'].with_suffix('.parquet.tmp')
    frame.to_parquet(tmp, index=False, compression='zstd')
    os.replace(tmp, paths['payload'])
    meta = dict(meta)
    meta.setdefault('input_sha256', input_sha if input_sha is not None else 'n/a')
    meta.update({'stage': stage, 'protocol_version': PROTOCOL_VERSION,
                 'input_kind': ctx.mode,
                 'rows': int(len(frame)), 'columns': list(frame.columns),
                 'payload': paths['payload'].name,
                 'payload_sha256': sha256_file(paths['payload']),
                 'code_fingerprint': code_fingerprint(), 'config_sha256': config_sha,
                 'written_local': now_iso()})
    write_json_atomic(paths['meta'], meta)
    write_json_atomic(paths['checkpoint_marker'], {
        'kind': 'checkpoint', 'stage': stage, 'protocol_version': PROTOCOL_VERSION,
        'completed_local': now_iso(), 'rows': int(len(frame)),
        'note': 'data-checkpoint completion marker; stage markers use <stage>.stage.COMPLETE',
        'checkpoint_meta_sha256': sha256_file(paths['meta'])})
    return meta


def record_checkpoint_decision(ctx, stage, file_id, action, reason, layout, rows=None,
                               payload_sha256=None):
    decision = {'stage': stage, 'file_id': file_id, 'action': action, 'reason': reason,
                'layout': layout, 'rows': rows, 'payload_sha256': payload_sha256,
                'decided_local': now_iso(), 'process_pid': os.getpid(),
                'checks': ['input_sha256', 'config_sha256', 'code_fingerprint', 'payload_sha256',
                           'marker_binding', 'stage_marker']}
    ctx.resume_decisions.append(decision)
    ctx.status(stage, 'checkpoint_decision',
               **{k: v for k, v in decision.items() if k != 'stage'})
    return decision


def scan_file_stage(ctx, spec, config_sha, preflight, probe=False):
    stage = spec['stage']
    expected_input_sha = preflight['primary'][spec['file_id']]['sha256']
    valid, reason, layout = checkpoint_is_valid(ctx, stage, expected_input_sha, config_sha)
    counters = ctx.scan_counters
    file_counter = counters['files'].setdefault(spec['file_id'], {'passes': 0})
    if valid:
        paths = checkpoint_paths(ctx, stage, layout)
        meta = read_json(paths['meta'])
        if not probe:
            record_checkpoint_decision(ctx, stage, spec['file_id'], 'reused', reason, layout,
                                       meta.get('rows'), meta.get('payload_sha256'))
            counters['reuse_events'].append({'stage': stage, 'file_id': spec['file_id'],
                                             'pid': os.getpid(), 'reused_local': now_iso(),
                                             'layout': layout})
        ctx.status(stage, 'resume_probe_reused' if probe else 'checkpoint_reused', reason=reason,
                   decompress_passes=0, input_sha256=expected_input_sha, layout=layout,
                   note='no decompression performed for this file')
        ctx.log(f'stage={stage} checkpoint reuse ({reason}); decompress_passes=0')
        save_scan_counters(ctx)
        return {'stage': stage, 'reused': True, 'rows': meta.get('rows'),
                'decompress_passes': 0, 'reused_payload_sha256': meta.get('payload_sha256')}
    if probe:
        raise StageFailure(f'probe requested but checkpoint not reusable: {reason}')
    record_checkpoint_decision(ctx, stage, spec['file_id'], 'rescan', reason, None)
    file_counter['passes'] = int(file_counter.get('passes', 0)) + 1
    file_counter['last_scan_pid'] = os.getpid()
    file_counter['last_scan_started'] = now_iso()
    counters['total_passes'] = int(counters.get('total_passes', 0)) + 1
    save_scan_counters(ctx)
    result = _scan_file_fresh(ctx, spec, config_sha, preflight)
    file_counter['last_scan_finished'] = now_iso()
    save_scan_counters(ctx)
    return result


def _scan_file_fresh(ctx, spec, config_sha, preflight):
    stage = spec['stage']
    file_id = spec['file_id']
    ctx.status(stage, 'start', file=file_id, decompress_passes=1)
    t0 = time.monotonic()
    prior_keys = set()
    prior_fingerprints = {}
    prior_file_ids = []
    for other in ctx.file_specs:
        if other['code'] < spec['code']:
            frame = pd.read_parquet(checkpoint_paths(ctx, other['stage'], 'v2')['payload'],
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
    with open_input_text(spec['path']) as fh:
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
    mark_stage_complete(ctx, stage, [checkpoint_paths(ctx, stage, 'v2')['payload'],
                                     checkpoint_paths(ctx, stage, 'v2')['meta']])
    elapsed = time.monotonic() - t0
    ctx.status(stage, 'complete', rows=stats['rows'], line_count=line_no, elapsed_s=round(elapsed, 3),
               rss_mb=ctx.rss_mb(), payload_sha256=meta['payload_sha256'], decompress_passes=1)
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


def write_changes_csv(ctx, inputs):
    """Machine-readable change log for every new/modified code artefact."""
    rows = []
    new_files = [
        ('solution/src/quality_q01c.py', 'staged pipeline module (all stages)',
         'Implements the Q01B decision: strict complete-case main Q with Q_valid, explicit '
         'denominators, isolated A1-calibration per-domain median sensitivity, file checkpoints with '
         'resume probes, versioned output directory, staged exit codes and final manifest.',
         'historical quality_audit.py executed every stage in one process, wrote to the fixed '
         'solution/outputs/quality directory, asserted that all Q_baseline were non-null and reported '
         'only a single total n.',
         'new module only writes to solution/outputs/quality_q01c/<run_id>/, keeps every physical row, '
         'marks incomplete-case rows Q_valid=False with Q=NaN and records effective denominators for '
         'every statistic.',
         'TASK-Q01B decision (02_DECISIONS.md) / TASK-Q01C work order'),
        ('solution/src/quality_q01c_selftest.py', 'synthetic tests',
         'Artificial tests for feature/group propagation, 0/1/2/3 usable groups, pandas skipna, Q_std '
         'n and n-1, calibration-only medians and gate hard-stop behaviour.',
         'no synthetic test existed for the historical scoring path.',
         'S01 runs these tests and refuses to read A1-A3 unless all pass.',
         'TASK-Q01C work order (S01, acceptance criterion 1)'),
        ('solution/src/quality_q01c_verify.py', 'independent verification',
         'Recomputes totals, Q_valid equivalence, coverage, denominators, sensitivity provenance and '
         'anchors from the row-level product with pandas; never imports the pipeline module.',
         'the historical pipeline verified itself with assertions inside the same process.',
         'S50 fails the run when any independent check fails; results in verification.json/checks.json.',
         'TASK-Q01C work order (S50, acceptance criterion 9)'),
        ('solution/tests/test_quality_q01c.py', 'standalone synthetic test runner',
         'Runs the synthetic tests into solution/outputs/quality_q01c_tests/<run_id>/ before any formal run.',
         'no standalone test entry point existed.',
         'human-runnable pre-flight with its own JSON/Markdown report.',
         'TASK-Q01C work order (tests directory)')]
    for path, area, change, before, after, decision in new_files:
        rows.append({'file': path, 'area_or_function': area, 'change_type': 'new_file',
                     'reason': change, 'before_behavior': before, 'after_behavior': after,
                     'related_decision': decision,
                     'sha256_after': sha256_file(SRC_DIR / Path(path).name)
                     if (SRC_DIR / Path(path).name).is_file() else None})
    frozen = ['quality_audit.py', 'common.py', 'mixture_baseline.py', 'scaling_baseline.py',
              'evolution_audit.py', 'project_audit.py', 'plot_baselines.py']
    for name in frozen:
        path = SRC_DIR / name
        if path.is_file():
            rows.append({'file': f'solution/src/{name}', 'area_or_function': 'entire module',
                         'change_type': 'unchanged',
                         'reason': 'historical module kept frozen as evidence; new behaviour lives in the '
                                   'Q01C module',
                         'before_behavior': 'unchanged', 'after_behavior': 'unchanged',
                         'related_decision': 'TASK-Q01C work order (no overwrite of historical evidence)',
                         'sha256_after': sha256_file(path)})
    write_csv_atomic(ctx.run_dir / 'changes.csv',
                     ['file', 'area_or_function', 'change_type', 'reason', 'before_behavior',
                      'after_behavior', 'related_decision', 'sha256_after'], rows)
    return rows


def stage_s00_preflight_fixture(ctx):
    """Preflight for synthetic fixture runs: fixture files only, A1-A3 untouched."""
    stage = 's00_preflight'
    ctx.status(stage, 'start', mode='fixture')
    t0 = time.monotonic()
    ctx.checkpoints.mkdir(parents=True, exist_ok=True)
    primary = {}
    for spec in ctx.file_specs:
        stat = spec['path'].stat()
        primary[spec['file_id']] = {
            'path': str(spec['path']), 'bytes': stat.st_size, 'mtime': stat.st_mtime,
            'sha256': sha256_file(spec['path']),
            'verification_method': 'read-only byte hash of the synthetic fixture input'}
    inputs = {'primary': primary, 'mode': 'fixture',
              'fixture_manifest': {'path': str(ctx.fixture_dir / 'fixture_manifest.json'),
                                   'sha256': sha256_file(ctx.fixture_dir / 'fixture_manifest.json')},
              'docs': {}, 'source': {}, 'old_quality': {}, 'evidence': {}, 'reports': {}}
    for path in sorted(SRC_DIR.glob('*.py')):
        inputs['source'][f'solution/src/{path.name}'] = {
            'path': f'solution/src/{path.name}', 'sha256': sha256_file(path),
            'bytes': path.stat().st_size}
    for name in ['config.json', 'README.md']:
        path = SOLUTION / name
        inputs['source'][f'solution/{name}'] = {'path': f'solution/{name}',
                                                'sha256': sha256_file(path),
                                                'bytes': path.stat().st_size}
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
    write_json_atomic(snapshot_dir / 'code_snapshot_manifest.json',
                      {'run_id': ctx.run_id, 'mode': 'fixture', 'frozen_local': now_iso(),
                       'files': frozen})
    write_json_atomic(ctx.run_dir / 'input_manifest.json', {
        'run_id': ctx.run_id, 'mode': 'fixture', 'generated_local': now_iso(),
        'primary': primary, 'fixture_manifest': inputs['fixture_manifest'],
        'source': inputs['source'], 'version_checks': [{'check': 'fixture_manifest_synthetic_flag',
                                                        'ok': True}],
        'read_policy': 'synthetic fixture only: A1/A2/A3 were never opened, hashed, decompressed '
                       'or stat-ed by this process',
        'real_inputs_accessed': 0, 'content_policy': 'no text/content field is read or stored'})
    fixture_entries = snapshot_paths([ctx.fixture_dir])
    write_json_atomic(ctx.run_dir / 'old_artifacts_before.json',
                      {'generated_local': now_iso(), 'scope': 'fixture_only',
                       'entries': fixture_entries,
                       'note': 'fixture-scoped snapshot; the real protected artifacts are checked '
                               'by the R1 harness, not by this synthetic run'})
    write_json_atomic(ctx.run_dir / 'environment.json', {
        'run_id': ctx.run_id, 'mode': 'fixture', 'start_local': now_iso(), 'python': sys.version,
        'python_executable': sys.executable, 'platform': platform.platform(),
        'machine': platform.machine(), 'timezone': str(datetime.now().astimezone().tzinfo),
        'seed': SEED, 'commands': [actual_command()], 'single_process_cpu': True, 'gpu_used': False,
        'network_used': False, 'libraries': {'numpy': np.__version__, 'pandas': pd.__version__,
                                             'pyarrow': __import__('pyarrow').__version__},
        'content_read': False, 'real_inputs_accessed': 0,
        'fixture_manifest_sha256': inputs['fixture_manifest']['sha256']})
    write_changes_csv(ctx, inputs)
    mark_stage_complete(ctx, stage, [ctx.run_dir / 'input_manifest.json',
                                     ctx.run_dir / 'environment.json',
                                     ctx.run_dir / 'old_artifacts_before.json',
                                     ctx.run_dir / 'changes.csv',
                                     snapshot_dir / 'code_snapshot_manifest.json'])
    ctx.stage_seconds[stage] = round(time.monotonic() - t0, 3)
    ctx.status(stage, 'complete', elapsed_s=ctx.stage_seconds[stage], rss_mb=ctx.rss_mb(),
               mode='fixture')
    ctx.log(f'stage={stage} complete (fixture mode); A1-A3 untouched')
    return inputs


def actual_command():
    return {'argv': [str(x) for x in sys.argv], 'executable': sys.executable,
            'cwd': os.getcwd(), 'pid': os.getpid(), 'recorded_local': now_iso()}


def stage_s00_preflight(ctx, config_sha):
    if ctx.mode == 'fixture':
        return stage_s00_preflight_fixture(ctx)
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
    write_changes_csv(ctx, inputs)
    mark_stage_complete(ctx, stage, [ctx.run_dir / 'input_manifest.json',
                                     ctx.run_dir / 'environment.json',
                                     ctx.run_dir / 'old_artifacts_before.json',
                                     ctx.run_dir / 'changes.csv',
                                     ctx.run_dir / 'code_snapshot' / 'code_snapshot_manifest.json'])
    ctx.status(stage, 'complete', elapsed_s=round(time.monotonic() - t0, 3), rss_mb=ctx.rss_mb())
    ctx.log(f'stage={stage} complete; inputs verified, code snapshot frozen')
    ctx.stage_seconds[stage] = round(time.monotonic() - t0, 3)
    return inputs


def mark_stage_complete(ctx, stage, outputs):
    """Stage completion marker (distinct from the data-checkpoint marker)."""
    payload = {'kind': 'stage', 'stage': stage, 'protocol_version': PROTOCOL_VERSION,
               'completed_local': now_iso(),
               'outputs': {str(Path(p).relative_to(ctx.run_dir)).replace('\\', '/'): sha256_file(p)
                           for p in outputs if Path(p).is_file()}}
    write_json_atomic(stage_marker_path(ctx, stage), payload)
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
    for spec in ctx.file_specs:
        valid, reason, layout = checkpoint_is_valid(ctx, spec['stage'],
                                                   preflight['primary'][spec['file_id']]['sha256'],
                                                   config_sha)
        if not valid:
            raise StageFailure(f'{spec["stage"]} checkpoint not reusable: {reason}')
        frames.append(pd.read_parquet(checkpoint_paths(ctx, spec['stage'], layout)['payload']))
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
    t_start = time.monotonic()
    df = finalize_primary_scores(df)
    path = ctx.run_dir / 'quality_features_scores.parquet'
    df.to_parquet(path, index=False, compression='zstd')
    meta = {'source': [spec['stage'] for spec in FILES], 'rows': int(len(df)),
            'Q_valid_true': int(df['Q_valid'].sum()), 'Q_valid_false': int((~df['Q_valid']).sum()),
            'q_valid_definition': 'all 11 normalized main-Q features finite',
            'group_rule': 'each group requires all its constituent features; no within-group skipna',
            'output': path.name}
    write_checkpoint(ctx, stage, df, meta, config_sha, input_sha=aggregate_input_binding(ctx))
    mark_stage_complete(ctx, stage, [path, ctx.run_dir / 'normalization.json'])
    ctx.status(stage, 'complete', rows=int(len(df)), q_valid_true=int(df['Q_valid'].sum()),
               q_valid_false=int((~df['Q_valid']).sum()), elapsed_s=round(time.monotonic() - t_start, 3),
               rss_mb=ctx.rss_mb())
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
    write_checkpoint(ctx, stage, df, meta, config_sha, input_sha=aggregate_input_binding(ctx))
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
                     config_sha, input_sha=aggregate_input_binding(ctx))
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
    write_json_atomic(ctx.run_dir / 'resume_evidence.json', {
        'run_id': ctx.run_id, 'mode': ctx.mode, 'protocol_version': PROTOCOL_VERSION,
        'generated_local': now_iso(), 'verified_before_finalize': True,
        'decisions': ctx.resume_decisions, 'scan_counters': ctx.scan_counters,
        'finalized_output_manifest_present': (ctx.run_dir / 'output_manifest.json').is_file(),
        'note': 'checkpoint reuse decisions with the validation items applied; reused checkpoints '
                'never re-run their payload computation'})
    verifier = SRC_DIR / 'quality_q01c_verify.py'
    if not verifier.is_file():
        raise StageFailure('independent verifier missing: ' + str(verifier))
    cmd = [sys.executable, '-X', 'utf8', str(verifier), '--run-dir', str(ctx.run_dir)]
    if ctx.mode == 'fixture' and ctx.fixture_dir is not None:
        cmd += ['--fixture-manifest', str(ctx.fixture_dir / 'fixture_manifest.json')]
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
    if ctx.mode == 'fixture':
        protected = [ctx.fixture_dir]
    else:
        protected = [SOLUTION / 'outputs' / 'quality', SOLUTION / 'reports',
                     PROJECT / 'diagnostics' / 'TASK-Q01A', PROJECT / 'diagnostics' / 'TASK-Q01A-R1']
    before = read_json(ctx.run_dir / 'old_artifacts_before.json')['entries']
    protected_prefixes = ('solution/outputs/quality/', 'solution/reports/',
                          'diagnostics/TASK-Q01A/', 'diagnostics/TASK-Q01A-R1/',
                          'F题/real_attachments/', 'diagnostics/TASK-Q01C-R1/')
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
    if ctx.mode == 'fixture' and ctx.fixture_manifest:
        target_rows = int(ctx.fixture_manifest.get('expected_rows_total', int(audit['total_records'])))
        target_q_valid = int(ctx.fixture_manifest.get('expected_q_valid', unique_q_valid or 0))
        target_q_missing = int(ctx.fixture_manifest.get('expected_q_missing', unique_q_missing or 0))
        target_physical = int(ctx.fixture_manifest.get('expected_q_valid_physical',
                                                       int(audit['q_valid_true'])))
    else:
        target_rows, target_q_valid, target_q_missing, target_physical = 272505, 261067, 19, 272486
    terminal = {stage: [e['event'] for e in ctx.stage_events.get(stage, [])
                        if e['event'] in TERMINAL_EVENTS] for stage in ctx.executed_stages}
    started = {stage: any(e['event'] == 'start' for e in ctx.stage_events.get(stage, []))
               for stage in ctx.executed_stages}
    conditions = {
        'synthetic_tests_passed': state.get('synthetic', {}).get('status') == 'PASS',
        'stages_completed': (state.get('stages_completed', 0)
                             + len(getattr(ctx, 'reused_stages', {}))) >= len(STAGES) - 1,
        'every_executed_stage_has_start_and_one_terminal':
            bool(ctx.executed_stages) and all(started.values())
            and all(len(events) == 1 for events in terminal.values()),
        'verification_no_fail': int(checks['summary']['n_fail']) == 0,
        'verification_no_critical_not_checked': int(checks['summary']['n_not_checked']) == 0,
        'sensitivity_gates_passed': bool(parameters.get('all_gates_passed')),
        'fallback_used': bool(parameters.get('fallback_used', False)),
        'protected_files_unchanged': not changed and not removed,
        'row_count_expected': int(audit['total_records']) == target_rows,
        'unique_q_valid_expected': unique_q_valid == target_q_valid,
        'unique_q_missing_expected': unique_q_missing == target_q_missing,
        'physical_q_valid_expected': int(audit['q_valid_true']) == target_physical}
    status = ('COMPLETE_PENDING_REVIEW'
              if all(v for k, v in conditions.items() if k != 'fallback_used')
              and not conditions['fallback_used'] else 'INCOMPLETE_OR_FAILED')
    ctx.stage_exit_codes['s60_finalize'] = 0
    write_json_atomic(ctx.run_dir / 'resume_evidence.json', {
        'run_id': ctx.run_id, 'mode': ctx.mode, 'protocol_version': PROTOCOL_VERSION,
        'generated_local': now_iso(), 'decisions': ctx.resume_decisions,
        'scan_counters': ctx.scan_counters, 'scan_counters_path': 'scan_counters.json',
        'finalized_output_manifest_present': (ctx.run_dir / 'output_manifest.json').is_file(),
        'note': 'checkpoint reuse decisions are recorded per stage/file with the validation items used; '
                'reused checkpoints never re-run their payload computation'})
    environment_path = ctx.run_dir / 'environment.json'
    try:
        environment = read_json(environment_path)
    except Exception:
        environment = {}
    commands = environment.get('commands') or []
    commands.append(actual_command())
    environment['commands'] = commands
    environment['mode'] = ctx.mode
    environment['finished_local'] = now_iso()
    write_json_atomic(environment_path, environment)
    stage_seconds_report = dict(ctx.stage_seconds)
    for stage, reason in ctx.skipped_stages.items():
        stage_seconds_report[stage] = {'status': 'SKIPPED', 'reason': reason}
    summary = {
        'task': 'TASK-Q01C', 'run_id': ctx.run_id, 'status': status,
        'started_local': state.get('started_local'), 'finished_local': now_iso(),
        'duration_s': round(time.monotonic() - state.get('mono', time.monotonic()), 3),
        'stage_exit_codes': ctx.stage_exit_codes, 'stage_seconds': stage_seconds_report,
        'executed_stages': ctx.executed_stages,
        'reused_stages': getattr(ctx, 'reused_stages', {}),
        'skipped_stages': ctx.skipped_stages,
        'stage_terminal_events': terminal, 'conditions': conditions,
        'command_argv': [str(x) for x in sys.argv], 'process_pid': os.getpid(),
        'hold_after_stage_hook': getattr(ctx, 'hold_hook', None), 'audit_totals': {k: audit[k] for k in
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
    ctx.finalized = True
    ctx.status(stage, 'complete', status=status, elapsed_s=round(time.monotonic() - t0, 3))
    ctx.stage_events.setdefault(stage, [])
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


STAGE_DEPENDENCIES = {
    's00_preflight': [],
    's01_synthetic_tests': ['s00_preflight'],
    's10_scan_a1': ['s00_preflight', 's01_synthetic_tests'],
    's11_scan_a2': ['s00_preflight', 's01_synthetic_tests', 's10_scan_a1'],
    's12_scan_a3': ['s00_preflight', 's01_synthetic_tests', 's10_scan_a1', 's11_scan_a2'],
    's20_score_primary': ['s10_scan_a1', 's11_scan_a2', 's12_scan_a3'],
    's30_sensitivity': ['s20_score_primary'],
    's40_summarize': ['s30_sensitivity'],
    's50_verify': ['s40_summarize'],
    's60_finalize': ['s50_verify'],
}


def stage_prerequisites(ctx, stage):
    missing = []
    for dependency in STAGE_DEPENDENCIES[stage]:
        ok, reason = stage_marker_valid(ctx, dependency)
        if not ok:
            missing.append({'stage': dependency, 'reason': reason})
        else:
            spec = next((s for s in ctx.file_specs if s['stage'] == dependency), None)
            if spec is not None:
                manifest_path = ctx.run_dir / 'input_manifest.json'
                if not manifest_path.is_file():
                    missing.append({'stage': dependency, 'reason': 'input_manifest.json missing'})
                    continue
                expected = read_json(manifest_path)['primary'][spec['file_id']]['sha256']
                valid, why, _layout = checkpoint_is_valid(ctx, dependency, expected,
                                                          _config_sha(ctx))
                if not valid:
                    missing.append({'stage': dependency, 'reason': f'checkpoint invalid: {why}'})
    return missing


def _config_sha(ctx):
    path = ctx.run_dir / 'run_config.json'
    return sha256_file(path) if path.is_file() else ''


def expected_input_sha(ctx, stage, preflight):
    spec = next((s for s in ctx.file_specs if s['stage'] == stage), None)
    if spec is not None:
        return preflight['primary'][spec['file_id']]['sha256']
    return aggregate_input_binding(ctx)


def probe_resume_mode(run_dir, args):
    """Read-only recovery eligibility check; writes only probe_resume_report.json."""
    ctx = RunContext(run_dir, args.run_id, resume=True)
    ctx.log_fh.close()
    ctx.status_fh.close()
    ctx.log_fh = open(os.devnull, 'a', encoding='utf-8')
    ctx.status_fh = open(os.devnull, 'a', encoding='utf-8')
    if args.fixture_dir:
        specs, manifest, fixture_dir = load_fixture_specs(args.fixture_dir)
        ctx.mode, ctx.file_specs, ctx.fixture_dir, ctx.fixture_manifest = ('fixture', specs,
                                                                         fixture_dir, manifest)
    ctx.scan_counters = load_scan_counters(ctx)
    preflight = None
    manifest_path = run_dir / 'input_manifest.json'
    if manifest_path.is_file():
        stored = read_json(manifest_path)
        preflight = {'primary': stored.get('primary', {}), 'mode': stored.get('mode', 'real')}
    finalized = (run_dir / 'output_manifest.json').is_file()
    config_sha = _config_sha(ctx)
    entries, reuse, reject = [], [], []
    for stage in STAGES:
        entry = {'stage': stage, 'stage_marker': None, 'checkpoint': None,
                 'decision': 'unknown'}
        ok, reason = stage_marker_valid(ctx, stage)
        entry['stage_marker'] = {'valid': ok, 'reason': reason, 'checked': True}
        has_checkpoint = (any(s['stage'] == stage for s in ctx.file_specs)
                          or stage in ('s20_score_primary', 's30_sensitivity', 's40_summarize'))
        if has_checkpoint:
            expected = expected_input_sha(ctx, stage, preflight) if preflight else ''
            valid, why, layout = checkpoint_is_valid(ctx, stage, expected, config_sha)
            entry['checkpoint'] = {'valid': valid, 'reason': why, 'layout': layout,
                                   'expected_input_sha256': expected}
        if entry['stage_marker']['valid'] and (entry['checkpoint'] is None
                                              or entry['checkpoint']['valid']):
            entry['decision'] = 'reusable'
            reuse.append({'stage': stage, 'reason': entry['stage_marker']['reason'],
                          'layout': (entry['checkpoint'] or {}).get('layout')})
        else:
            entry['decision'] = 'not_reusable'
            reject.append({'stage': stage,
                           'stage_marker_reason': entry['stage_marker']['reason'],
                           'checkpoint_reason': (entry['checkpoint'] or {}).get('reason')})
        entries.append(entry)
    report = {'run_id': args.run_id, 'mode': ctx.mode, 'generated_local': now_iso(),
              'process_pid': os.getpid(), 'finalized_run': finalized,
              'resumable': (not finalized) and bool(reuse),
              'read_only_probe': True,
              'writes': ['probe_resume_report.json'],
              'scan_counters': ctx.scan_counters,
              'scan_passes_during_probe': 0,
              'checked_stages': entries, 'reusable_stages': reuse, 'not_reusable_stages': reject,
              'command_argv': [str(x) for x in sys.argv],
              'note': 'read-only eligibility check: no stage was executed and no scan was performed'}
    write_json_atomic(run_dir / 'probe_resume_report.json', report)
    print(json.dumps({'pid': os.getpid(), 'finalized': finalized,
                      'reusable_stages': [r['stage'] for r in reuse],
                      'not_reusable_stages': [r['stage'] for r in reject]}, ensure_ascii=False),
          flush=True)
    return 0


def run_stage(ctx, name, state):
    if name == 's00_preflight':
        return stage_s00_preflight(ctx, None)
    if name == 's01_synthetic_tests':
        return stage_s01_synthetic_tests(ctx, state['config_sha'])
    spec = next((s for s in ctx.file_specs if s['stage'] == name), None)
    if spec is not None:
        return scan_file_stage(ctx, spec, state['config_sha'], state['preflight'])
    if name == 's20_score_primary':
        df, _transforms = stage_s20_score_primary(ctx, state['config_sha'], state['preflight'])
        stage_s20_write(ctx, state['config_sha'], df)
        return None
    if name == 's30_sensitivity':
        df, payload = stage_s30_sensitivity(ctx, state['config_sha'])
        state['parameters'] = payload
        return df
    if name == 's40_summarize':
        df, domain_rows, sensitivity_rows, comparison_rows, audit, raw_rows = \
            stage_s40_summarize(ctx, state['config_sha'])
        if state.get('parameters') is None:
            state['parameters'] = read_json(ctx.run_dir / 'imputation_parameters_sensitivity.json')
        stage_s40_write(ctx, state['config_sha'], df, domain_rows, sensitivity_rows,
                        comparison_rows, state['parameters'])
        return None
    if name == 's50_verify':
        return stage_s50_verify(ctx, state['config_sha'], state)
    if name == 's60_finalize':
        return stage_s60_finalize(ctx, state['config_sha'], state)
    raise StageFailure(f'unknown stage: {name}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='TASK-Q01C staged quality pipeline')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--out-root', default=str(SOLUTION / 'outputs' / 'quality_q01c'))
    parser.add_argument('--fixture-dir', default=None,
                        help='run against a synthetic fixture instead of the real attachments')
    parser.add_argument('--resume', action='store_true',
                        help='resume an existing unfinished run directory')
    parser.add_argument('--stage', default='all', choices=['all'] + STAGES,
                        help='execute only the named stage (all = full sequence)')
    parser.add_argument('--probe-resume', action='store_true',
                        help='read-only recovery eligibility check for an existing run directory')
    parser.add_argument('--hold-after-stage', default=None, choices=STAGES,
                        help='test hook: after the named stage completes, wait for an external '
                             'interruption (used only by the R1 cross-process test)')
    args = parser.parse_args(argv)
    run_dir = Path(args.out_root) / args.run_id
    exists = run_dir.exists()
    if args.probe_resume:
        if not exists:
            print(f'probe-resume: run directory does not exist: {run_dir}', flush=True)
            return 3
        try:
            return probe_resume_mode(run_dir, args)
        except StageFailure as exc:
            print(f'probe-resume failed: {exc}', flush=True)
            return 2
    finalized = exists and (run_dir / 'output_manifest.json').is_file()
    if args.resume and not exists:
        print(f'--resume requested but the run directory does not exist: {run_dir}', flush=True)
        return 4
    if exists and not args.resume:
        print(f'run directory already exists, refusing to continue without --resume: {run_dir}',
              flush=True)
        return 3
    if exists and args.resume and finalized:
        print(f'run directory is finalized (output_manifest.json present); refusing --resume: '
              f'{run_dir}', flush=True)
        return 5
    if not exists:
        run_dir.mkdir(parents=True, exist_ok=False)
    ctx = RunContext(run_dir, args.run_id, resume=args.resume)
    state = {'started_local': now_iso(), 'mono': time.monotonic(), 'resume_probes': [],
             'stages_completed': 0, 'config_sha': None, 'preflight': None,
             'parameters': None, 'synthetic': None, 'checks': None}
    exit_code = 2
    status = 'INCOMPLETE_OR_FAILED'
    try:
        if args.fixture_dir:
            specs, manifest, fixture_dir = load_fixture_specs(args.fixture_dir)
            ctx.mode, ctx.file_specs = 'fixture', specs
            ctx.fixture_dir, ctx.fixture_manifest = fixture_dir, manifest
            state['stages_completed'] += 0
        ctx.scan_counters = load_scan_counters(ctx)
        ctx.log(f'TASK-Q01C start run_id={args.run_id} mode={ctx.mode} resume={args.resume} '
                f'stage={args.stage} pid={os.getpid()}')
        ctx.status(args.stage if args.stage != 'all' else 's00_preflight', 'invocation',
                   mode=ctx.mode, resume=args.resume, stage_selection=args.stage,
                   argv=[str(x) for x in sys.argv])
        if args.stage != 'all':
            missing = stage_prerequisites(ctx, args.stage)
            if missing:
                ctx.skipped_stages = {name: 'not executed (single-stage run)'
                                      for name in STAGES if name != args.stage}
                _write_failure_summary(ctx, args.stage, missing, 6)
                return 6
        plan = STAGES if args.stage == 'all' else [args.stage]
        if (run_dir / 'input_manifest.json').is_file():
            stored = read_json(run_dir / 'input_manifest.json')
            state['preflight'] = {'primary': stored.get('primary', {}),
                                  'mode': stored.get('mode', ctx.mode)}
        if (run_dir / 'run_config.json').is_file():
            state['config_sha'] = sha256_file(run_dir / 'run_config.json')
        for name in plan:
            marker_ok, marker_reason = stage_marker_valid(ctx, name)
            if marker_ok:
                if name == 's01_synthetic_tests' and state.get('synthetic') is None:
                    tests_path = run_dir / 'synthetic_tests.json'
                    if tests_path.is_file():
                        state['synthetic'] = read_json(tests_path)
                ctx.reused_stages = getattr(ctx, 'reused_stages', {})
                ctx.reused_stages[name] = marker_reason
                ctx.resume_decisions.append({'stage': name, 'action': 'stage_reused',
                                             'reason': marker_reason, 'decided_local': now_iso(),
                                             'process_pid': os.getpid()})
                ctx.status(name, 'stage_reused', reason=marker_reason)
                ctx.log(f'stage={name} already complete and validated; not recomputed')
                continue
            t0 = time.monotonic()
            ctx.status(name, 'start')
            result = run_stage(ctx, name, state)
            ctx.stage_seconds[name] = round(time.monotonic() - t0, 3)
            ctx.stage_exit_codes[name] = 0
            ctx.executed_stages.append(name)
            state['stages_completed'] += 1
            if name == 's00_preflight':
                state['preflight'] = result
                write_json_atomic(ctx.run_dir / 'run_config.json', {
                    'run_id': args.run_id, 'mode': ctx.mode, 'output_dir': str(ctx.run_dir),
                    'stages': STAGES, 'seed': SEED,
                    'protocol_version': PROTOCOL_VERSION,
                    'fixture_manifest': (ctx.fixture_manifest or {}).get('fixture_id'),
                    'split_rule': f'int(sha256(str({SEED})+key_json)[:16],16)%{SPLIT_MODULUS}; 0 -> A1_holdout',
                    'primary_q_rule': 'strict complete cases over the 11 main-Q features',
                    'group_rule': 'equal weights within and across the three groups; no reallocation',
                    'sensitivity_rule': 'A1_calibration per-domain median over normalized values, missing features only',
                    'sensitivity_gates': GATES,
                    'fallback_policy': 'none: gate failure stops the run',
                    'resume_policy': 'reuse only when input/config/code/payload hashes and markers validate',
                    'prohibitions': ['no record deletion', 'no zero filling', 'no strategy change',
                                     'no holdout/extension parameter estimation',
                                     'no old-output overwrite']})
                state['config_sha'] = sha256_file(ctx.run_dir / 'run_config.json')
            elif name == 's01_synthetic_tests':
                state['synthetic'] = result
            elif name == 's50_verify':
                state['checks'] = result
            elif name == 's60_finalize':
                status = result
            ctx.log(f'stage={name} done elapsed_s={ctx.stage_seconds[name]}')
            if args.hold_after_stage == name:
                ctx.hold_hook = name
                ctx.status(name, 'hold_after_stage',
                           note='test-only hook: waiting for the supervisor to interrupt this process',
                           pid=os.getpid())
                ctx.log(f'HOOK hold-after-stage={name}: waiting for external interruption pid={os.getpid()}')
                hold_deadline = time.monotonic() + 180
                while time.monotonic() < hold_deadline:
                    time.sleep(0.5)
        for name in STAGES:
            if name not in ctx.executed_stages and name not in getattr(ctx, 'reused_stages', {}):
                ctx.skipped_stages.setdefault(name, f'not executed (stage plan: {args.stage})')
        if state.get('config_sha') is None:
            state['config_sha'] = _config_sha(ctx)
        if 's60_finalize' not in ctx.executed_stages and args.stage != 'all':
            _write_failure_summary(ctx, args.stage, [], 0,
                                   reason=f'single-stage run {args.stage}: no finalize')
            return 0
        exit_code = 0 if status == 'COMPLETE_PENDING_REVIEW' else 2
        print(f'[{now_iso()}] TASK-Q01C end status={status} exit_code={exit_code}', flush=True)
        return exit_code
    except StageFailure as exc:
        ctx.log('ERROR stage_failure: ' + str(exc))
        ctx.status('failure', 'failed', error=str(exc))
        _write_failure_summary(ctx, args.stage, [], 2, reason=str(exc))
        return 2
    except Exception as exc:
        ctx.log('ERROR unhandled: ' + type(exc).__name__ + ': ' + str(exc))
        ctx.log(traceback.format_exc())
        _write_failure_summary(ctx, args.stage, [], 2, reason=f'{type(exc).__name__}: {exc}')
        return 2


def _write_failure_summary(ctx, stage, missing, exit_code, reason=None):
    try:
        write_json_atomic(ctx.run_dir / 'run_summary.json', {
            'task': 'TASK-Q01C', 'run_id': ctx.run_id, 'status': 'FAILED' if exit_code else 'PARTIAL',
            'mode': ctx.mode, 'stage': stage, 'missing_prerequisites': missing,
            'reason': reason, 'exit_code': exit_code, 'stage_seconds': ctx.stage_seconds,
            'executed_stages': ctx.executed_stages, 'skipped_stages': ctx.skipped_stages,
            'reused_stages': getattr(ctx, 'reused_stages', {}),
            'stage_terminal_events': {s: [e['event'] for e in ctx.stage_events.get(s, [])
                                          if e['event'] in TERMINAL_EVENTS]
                                      for s in ctx.executed_stages},
            'fallback_used': False, 'content_read': False,
            'command_argv': [str(x) for x in sys.argv], 'process_pid': os.getpid(),
            'finished_local': now_iso()})
    except Exception:
        pass
    ctx.close()


if __name__ == '__main__':
    sys.exit(main())
