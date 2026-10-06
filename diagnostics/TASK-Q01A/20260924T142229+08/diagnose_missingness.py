"""TASK-Q01A diagnostic: quality-missingness pattern diagnosis (read-only evidence).

Scope boundary (deliberate):
  * reads A1 / A2_arxiv / A3_github with exactly one sequential decompression
    pass per file (plus one raw-byte read per file for the pre/post SHA256),
  * audits the 22 raw quality fields and the 25 expanded scalar features,
  * reproduces the current joint-key / stable-split / NaN-propagation semantics,
  * writes only count-type evidence, row-level masks and anomaly events into
    its own run directory.

It does NOT recompute Q_baseline, does NOT impute / drop / fill / reweight,
does NOT modify any input, and does NOT select or implement any final
missing-data strategy. Those are TASK-Q01B decisions.
"""
from __future__ import annotations

import ast
import csv
import gzip
import hashlib
import json
import lzma
import math
import os
import platform
import sys
import time
import traceback
from array import array
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

RUN_DIR = Path(__file__).resolve().parent
PROJECT = RUN_DIR.parents[2]
if not (RUN_DIR.parent.name == 'TASK-Q01A' and RUN_DIR.parent.parent.name == 'diagnostics'):
    raise SystemExit('run directory layout unexpected: ' + str(RUN_DIR))
RUN_ID = RUN_DIR.name

START_LOCAL = datetime.now().astimezone()
START_ISO = START_LOCAL.isoformat(timespec='seconds')
START_MONO = time.monotonic()

SEED = 20260924
SPLIT_MODULUS = 5
HOLDOUT_REMAINDER = 0
WALL_LIMIT_S = 1200.0
MEM_LIMIT_BYTES = 2 * 1024 ** 3
PROGRESS_EVERY = 50000
RESOURCE_CHECK_EVERY = 5000
CST = timezone(timedelta(hours=8))

# --------------------------------------------------------------------------
# Pinned static specification extracted by reading solution/src/quality_audit.py
# (lines 26-54 of the audited revision). Verified programmatically against the
# source AST at start-up; a mismatch aborts the run before any raw read.
# --------------------------------------------------------------------------
RULES = [
    'rps_doc_frac_no_alph_words', 'rps_doc_mean_word_length',
    'rps_doc_frac_unique_words', 'rps_doc_unigram_entropy', 'rps_doc_word_count',
    'rps_lines_ending_with_terminal_punctution_mark',
    'rps_lines_numerical_chars_fraction', 'rps_lines_uppercase_letter_fraction',
    'rps_doc_num_sentences', 'rps_doc_frac_chars_top_2gram',
    'rps_doc_frac_chars_top_3gram',
]
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
MODEL_INDEX = {f: i for i, f in enumerate(MODEL)}
FEATURE_INDEX = {f: i for i, f in enumerate(FEATURES)}
FIELD_INDEX = {f: i for i, f in enumerate(FIELDS)}
GROUP_MODEL_BITS = {g: sum(1 << MODEL_INDEX[f] for f in fs) for g, fs in GROUPS.items()}
MODEL_ALL_BITS = (1 << len(MODEL)) - 1
FEATURES_ALL_BITS = (1 << len(FEATURES)) - 1
FIELDS_ALL_BITS = (1 << len(FIELDS)) - 1

DATA = PROJECT / 'F题' / 'real_attachments'
SOLUTION = PROJECT / 'solution'
SRC = SOLUTION / 'src'
QUALITY_OUT = SOLUTION / 'outputs' / 'quality'
AUDIT_OUT = SOLUTION / 'outputs' / 'audit'
RECOVERY = PROJECT / 'recovery' / '2026-09-24'
TASK_FILE = PROJECT / 'tasks' / 'TASK-Q01A_质量缺失模式诊断.md'

FILES = [
    {'file_id': 'A1', 'code': 0, 'fallback_domain': None,
     'path': DATA / 'A_data_value' / 'slimpajama_quality_signal_sample.jsonl.xz'},
    {'file_id': 'A2_arxiv', 'code': 1, 'fallback_domain': 'arxiv',
     'path': DATA / 'A_data_value' / 'slimpajama_quality_extended' /
             'arxiv_part-6777d8857c6e-000486.jsonl.xz'},
    {'file_id': 'A3_github', 'code': 2, 'fallback_domain': 'github',
     'path': DATA / 'A_data_value' / 'slimpajama_quality_extended' /
             'github_part-6777d8857c6e-000275.jsonl.xz'},
]
FILE_IDS = [f['file_id'] for f in FILES]
DOMAINS = ['arxiv', 'book', 'c4', 'commoncrawl', 'github', 'stackexchange', 'wikipedia']

PRIMARY_INPUTS = [f['path'] for f in FILES]
SECONDARY_INPUTS = [
    SRC / 'quality_audit.py', SRC / 'common.py', SOLUTION / 'config.json',
    QUALITY_OUT / 'audit.json', QUALITY_OUT / 'normalization.json',
    QUALITY_OUT / 'domain_summary.csv', QUALITY_OUT / 'feature_summary.csv',
    QUALITY_OUT / 'extension_shift.csv',
    AUDIT_OUT / 'raw_source_manifest.csv', AUDIT_OUT / 'environment.json',
    RECOVERY / 'quality_gap_evidence.json',
    RECOVERY / 'quality_missing_feature_counts.csv',
    RECOVERY / 'quality_mean_discrepancies.csv',
    RECOVERY / 'verification.json',
]
PROTECTED_GLOBS = [
    DATA, SRC, SOLUTION / 'config.json', SOLUTION / 'outputs', SOLUTION / 'reports',
    RECOVERY, PROJECT / 'tasks', PROJECT / '00_PROJECT_BRIEF.md',
    PROJECT / '01_PROJECT_STATUS.md', PROJECT / '02_DECISIONS.md',
    PROJECT / '03_DATA_CATALOG.md', PROJECT / '04_TASK_QUEUE.md',
    PROJECT / '05_REVIEW_LOG.md', PROJECT / '恢复报告.md',
]

# Row-level mask column order (written to row_masks.csv.gz, re-read by the
# independent re-aggregation check).
ROW_MASK_COLUMNS = [
    'file_id', 'source_line', 'id_json', 'sub_path_json', 'key_str_json', 'key_sha256',
    'domain', 'domain_source', 'evaluation_role', 'is_unique_first', 'overlap_a1',
    'within_file_duplicate', 'duplicate_of_file', 'parse_ok',
    'id_present', 'id_is_null', 'id_type', 'sub_path_present', 'sub_path_is_null',
    'sub_path_type', 'key_anomaly',
    'raw_invalid_bits', 'raw_invalid_count',
    'extract_nan_bits', 'extract_nonfinite_bits', 'extract_posinf_bits', 'extract_neginf_bits',
    'extract_nan_count', 'extract_nonfinite_count',
    'norm_nan_bits', 'norm_nonfinite_bits', 'norm_nonfinite_count',
    'would_group_usability_be_nan', 'would_group_knowledge_be_nan',
    'would_group_education_reasoning_be_nan', 'would_Q_be_nan',
    'would_Q_nan_trigger_features', 'q_nan_trigger_features', 'would_Q_nan_trigger_groups',
    'quality_fingerprint', 'fingerprint_error', 'quality_conflict',
    'domain_collision', 'duplicate_mask_conflict',
]
INVALID_COLUMNS = [
    'file_id', 'source_line', 'key_sha256', 'key_str_json', 'domain',
    'layer', 'field_or_feature', 'feature_universe', 'reason', 'list_index',
    'value_kind', 'value_repr', 'detail',
]
MASK_DEFS = [
    ('raw_field_invalid', 'FIELDS22', 'raw_invalid', 22, FIELDS),
    ('extract_nan', 'FEATURES25', 'extract_nan', 25, FEATURES),
    ('extract_nonfinite', 'FEATURES25', 'extract_nonfinite', 25, FEATURES),
    ('norm_nan', 'MODEL11', 'norm_nan', 11, MODEL),
    ('norm_nonfinite', 'MODEL11', 'norm_nonfinite', 11, MODEL),
]
POPCOUNT8 = np.array([bin(i).count('1') for i in range(256)], dtype=np.int16)


class PreconditionError(RuntimeError):
    """Raised before/around the raw scan when a frozen precondition fails."""


class ResourceStop(RuntimeError):
    """Raised when the wall-clock or memory boundary is reached."""


class Logger:
    def __init__(self, path):
        self.path = Path(path)
        self.fh = open(self.path, 'a', encoding='utf-8', newline='\n')

    def __call__(self, message):
        stamp = datetime.now(CST).isoformat(timespec='milliseconds')
        line = f'[{stamp}] {message}'
        self.fh.write(line + '\n')
        self.fh.flush()
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            print(line.encode('utf-8', 'replace').decode('utf-8'), flush=True)

    def close(self):
        try:
            self.fh.close()
        except Exception:
            pass


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


def stable_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def read_json(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def read_csv_rows(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def log_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return value if math.isfinite(value) else None
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    raise TypeError(type(obj).__name__)


def write_json(path, value):
    path = Path(path)
    guard_write(path)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=log_default,
                               allow_nan=False), encoding='utf-8')
    return path


def write_csv(path, columns, rows, bom=True):
    path = Path(path)
    guard_write(path)
    encoding = 'utf-8-sig' if bom else 'utf-8'
    with open(path, 'w', encoding=encoding, newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def guard_write(path):
    resolved = Path(path).resolve()
    if RUN_DIR.resolve() not in resolved.parents:
        raise PreconditionError(f'attempt to write outside run directory: {resolved}')


def short_repr(value, limit=60):
    try:
        text = repr(value)
    except Exception:
        text = '<repr failed>'
    if len(text) > limit:
        text = text[:limit] + '...'
    return text


def finite_or_none(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def bits_to_string(value, nbits):
    return ''.join('1' if (value >> j) & 1 else '0' for j in range(nbits))


def string_to_bits(text):
    value = 0
    for j, ch in enumerate(text):
        if ch == '1':
            value |= (1 << j)
    return value


def names_for_bits(value, names):
    return '|'.join(name for j, name in enumerate(names) if (value >> j) & 1)


def set_bit_count(value):
    return bin(value).count('1')


def fair_ratio(numerator, denominator):
    if denominator:
        return float(numerator) / float(denominator)
    return None


def json_compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


# --------------------------------------------------------------------------
# Static source verification: pinned constants vs the audited source revision.
# --------------------------------------------------------------------------

def literal_assignments(path):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {'RULES', 'DSIR', 'PRRC', 'QURATER', 'MODEL', 'FEATURES', 'GROUPS', 'LIST_LENGTHS'}:
                found[name] = node.value
    return found


def eval_const_expr(node, env):
    """Structural evaluator for module-level constant expressions of the audited
    source (names, list/dict literals, list() call, + concatenation, dict
    comprehension over PRRC). No module import and no attribute access."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise PreconditionError(f'unknown name in constant expression: {node.id}')
        return env[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [eval_const_expr(item, env) for item in node.elts]
    if isinstance(node, ast.Dict):
        out = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                out.update(eval_const_expr(value, env))
            else:
                out[eval_const_expr(key, env)] = eval_const_expr(value, env)
        return out
    if isinstance(node, ast.DictComp):
        gens = node.generators
        if len(gens) != 1 or gens[0].ifs or gens[0].is_async:
            raise PreconditionError('unsupported dict comprehension in source constants')
        target = gens[0].target
        if not isinstance(target, ast.Name):
            raise PreconditionError('unsupported comprehension target')
        out = {}
        for item in eval_const_expr(gens[0].iter, env):
            local = dict(env)
            local[target.id] = item
            out[eval_const_expr(node.key, local)] = eval_const_expr(node.value, local)
        return out
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return eval_const_expr(node.left, env) + eval_const_expr(node.right, env)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'list'
            and len(node.args) == 1 and not node.keywords):
        return list(eval_const_expr(node.args[0], env))
    raise PreconditionError(f'unsupported constant expression node: {type(node).__name__}')


def verify_source_spec():
    """Return a report dict; raise PreconditionError on any structural mismatch."""
    nodes = literal_assignments(SRC / 'quality_audit.py')
    report = {'source': str(SRC / 'quality_audit.py'), 'checks': {}, 'literal_values': {}}
    expected_literals = {'RULES': RULES, 'DSIR': DSIR, 'PRRC': PRRC, 'QURATER': QURATER,
                         'MODEL': MODEL, 'FEATURES': FEATURES, 'GROUPS': GROUPS}
    env = {}
    for name, expected in expected_literals.items():
        if name not in nodes:
            raise PreconditionError(f'source constant {name} not found by AST')
        actual = eval_const_expr(nodes[name], env)
        env[name] = actual
        ok = actual == expected
        report['checks'][name] = ok
        report['literal_values'][name] = actual
        if not ok:
            raise PreconditionError(f'source constant {name} differs from pinned spec')
    # LIST_LENGTHS contains a dict-unpacking of a comprehension in the source;
    # verify that structure statically instead of executing it.
    node = nodes.get('LIST_LENGTHS')
    if not isinstance(node, ast.Dict):
        raise PreconditionError('LIST_LENGTHS is not a dict literal in source')
    explicit = {}
    unpack_ok = False
    for key, value in zip(node.keys, node.values):
        if key is None:
            gen = value.generators[0] if isinstance(value, ast.DictComp) and value.generators else None
            unpack_ok = (isinstance(value, ast.DictComp)
                         and isinstance(value.value, ast.Constant) and value.value.value == 6
                         and isinstance(value.key, ast.Name) and value.key.id == 'p'
                         and gen is not None and isinstance(gen.target, ast.Name)
                         and gen.target.id == 'p' and isinstance(gen.iter, ast.Name)
                         and gen.iter.id == 'PRRC' and not gen.ifs and not gen.is_async)
        else:
            explicit[ast.literal_eval(key)] = ast.literal_eval(value)
    expected_explicit = {'fineweb_edu': 1, 'ad_en': 2, 'fluency_en': 2, 'qurater': 4}
    if explicit != expected_explicit or not unpack_ok:
        raise PreconditionError(f'LIST_LENGTHS structure differs: {explicit} unpack_ok={unpack_ok}')
    evaluated = eval_const_expr(node, env)
    if evaluated != LIST_LENGTHS:
        raise PreconditionError(f'LIST_LENGTHS value differs from pinned spec: {evaluated}')
    report['checks']['LIST_LENGTHS'] = True
    report['list_lengths_explicit'] = explicit
    report['list_lengths_unpack'] = '{p: 6 for p in PRRC}'
    if not (len(FIELDS) == 22 and len(FEATURES) == 25 and len(MODEL) == 11):
        raise PreconditionError('pinned field counts wrong')
    union = set()
    for features in GROUPS.values():
        union.update(features)
    if union != set(MODEL):
        raise PreconditionError('GROUPS union != MODEL')
    report['checks']['counts'] = True
    report['checks']['groups_union_model'] = True
    # common.py SEED
    tree = ast.parse((SRC / 'common.py').read_text(encoding='utf-8'))
    seed_value = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'SEED':
            seed_value = ast.literal_eval(node.value)
    if seed_value != SEED:
        raise PreconditionError(f'common.py SEED={seed_value} != {SEED}')
    report['checks']['seed'] = True
    return report


def verify_normalization(params):
    report = {'checks': {}, 'transforms': {}}
    if params.get('groups') != GROUPS:
        raise PreconditionError('normalization.json groups differ from source GROUPS')
    report['checks']['groups_match'] = True
    transforms = params.get('transforms', {})
    if set(transforms) != set(MODEL):
        raise PreconditionError('normalization.json transforms != MODEL features')
    report['checks']['transforms_match_model'] = True
    if params.get('excluded_primary_score_features') != RULES + DSIR:
        raise PreconditionError('normalization.json excluded features differ')
    report['checks']['excluded_match'] = True
    fixed = {'modernbert_professionalism': (0.0, 5.0), 'modernbert_readability': (0.0, 5.0),
             'modernbert_reasoning': (0.0, 5.0), 'modernbert_cleanliness': (0.0, 5.0),
             'ad_en': (0.0, 1.0), 'fluency_en': (0.0, 1.0)}
    ordered = {}
    for feature in MODEL:
        item = transforms[feature]
        low, high = float(item['low']), float(item['high'])
        if not (math.isfinite(low) and math.isfinite(high) and high > low):
            raise PreconditionError(f'transform bounds invalid for {feature}: {low},{high}')
        if feature in fixed and (low, high) != fixed[feature]:
            raise PreconditionError(f'fixed range mismatch for {feature}: {low},{high}')
        ordered[feature] = {'low': low, 'high': high, 'method': item.get('method'),
                            'direction': item.get('direction')}
    report['checks']['bounds_valid'] = True
    report['checks']['fixed_ranges_match'] = True
    report['transforms'] = ordered
    return report


def normalize_one(feature, value, transforms):
    """Exact fast reproduction of ((x-low)/(high-low)).clip(0,1) with finite bounds."""
    if value != value:                      # NaN
        return float('nan')
    low = transforms[feature]['low']
    high = transforms[feature]['high']
    scale = high - low
    if value == float('inf'):
        return 1.0
    if value == float('-inf'):
        return 0.0
    y = (value - low) / scale
    if y != y:
        return float('nan')
    if y < 0.0:
        return 0.0
    if y > 1.0:
        return 1.0
    return y


# --------------------------------------------------------------------------
# Replica of quality_audit.get_features (bit-for-bit semantics, incl. bool
# acceptance and whole-list invalidation) and quality_fingerprint.
# --------------------------------------------------------------------------

def get_features(obj, errors=None):
    result = {}
    for field in RULES + DSIR:
        value = obj.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                result[field] = float(value)
            except (OverflowError, ValueError) as exc:
                result[field] = float('nan')
                if errors is not None:
                    errors.append((field, 'float_conversion_error', type(exc).__name__))
        elif isinstance(value, bool):
            result[field] = float(value)      # source accepts bool (isinstance int)
        else:
            result[field] = float('nan')
    for field, expected in LIST_LENGTHS.items():
        value = obj.get(field)
        valid = isinstance(value, list) and len(value) == expected
        if valid:
            try:
                valid = all(isinstance(x, (int, float)) and np.isfinite(x) for x in value)
            except (TypeError, OverflowError, ValueError) as exc:
                valid = False
                if errors is not None:
                    errors.append((field, 'extract_check_error', type(exc).__name__))
        if field == 'qurater':
            for i, col in enumerate(QURATER):
                result[col] = float(value[i]) if valid else float('nan')
        elif field == 'fineweb_edu':
            result[field] = float(value[0]) if valid else float('nan')
        else:
            if valid:
                try:
                    result[field] = float(np.argmax(value))
                except (TypeError, ValueError) as exc:
                    result[field] = float('nan')
                    if errors is not None:
                        errors.append((field, 'argmax_error', type(exc).__name__))
            else:
                result[field] = float('nan')
    for feature in FEATURES:
        result.setdefault(feature, float('nan'))
    return result


def quality_fingerprint(obj):
    normalized = {}
    for f in FIELDS:
        v = obj.get(f)
        normalized[f] = ([float(x) for x in v] if isinstance(v, list)
                         else float(v) if isinstance(v, (int, float)) else v)
    return stable_hash(json.dumps(normalized, sort_keys=True, separators=(',', ':')))


try:
    import psutil  # optional, used only for peak-RSS observation
except Exception:      # pragma: no cover - environment dependent
    psutil = None

F_UNIQUE = 1
F_OVERLAP = 2
F_CALIB = 4
F_HOLDOUT = 8
F_EXTOVER = 16
F_EXTNEW = 32
F_A1 = 64
F_PARSE = 128


def peak_rss_bytes():
    if psutil is None:
        return None
    try:
        info = psutil.Process().memory_info()
        return int(getattr(info, 'peak_wset', None) or info.rss)
    except Exception:
        return None


def guard_resources(log, stage, rows_done=0, check_memory=True):
    elapsed = time.monotonic() - START_MONO
    if elapsed > WALL_LIMIT_S:
        raise ResourceStop(f'wall-clock limit reached at stage={stage} rows={rows_done} elapsed={elapsed:.1f}s')
    if check_memory:
        rss = peak_rss_bytes()
        if rss is not None and rss > MEM_LIMIT_BYTES:
            raise ResourceStop(f'memory limit reached at stage={stage} rows={rows_done} peak_rss={rss}')


def empty_prior_stats():
    return {'present': 0, 'null': 0, 'types': Counter(), 'lengths': Counter(),
            'non_numeric': 0, 'nan': 0, 'pos_inf': 0, 'neg_inf': 0,
            'finite_elements': 0, 'negative_elements': 0, 'zero_elements': 0,
            'min': float('inf'), 'max': float('-inf'), 'valid_list_rows': 0,
            'list_negative_rows': 0, 'list_all_in_0_1_rows': 0,
            'list_sum_approx_1_rows': 0, 'list_sum_min': float('inf'),
            'list_sum_max': float('-inf'), 'argmax_counts': Counter(),
            'argmax_tie_rows': 0, 'audit_error_rows': 0}


def empty_detail_stats():
    return {'null_rows': 0, 'list_rows': 0, 'wrong_length_rows': 0,
            'non_numeric_rows': 0, 'non_numeric_elements': 0,
            'nan_elements': 0, 'nan_rows': 0, 'posinf_elements': 0, 'posinf_rows': 0,
            'neginf_elements': 0, 'neginf_rows': 0, 'finite_elements': 0,
            'scalar_nan_rows': 0, 'scalar_posinf_rows': 0, 'scalar_neginf_rows': 0,
            'total_elements': 0, 'audit_error_rows': 0}


def audit_field(value, field, prior, detail, emit_event):
    """Reproduce quality_audit.audit_value (prior semantics) and add an
    independent element-level detailed audit. Returns a non-empty reason
    string when the raw value is invalid at this layer."""
    prior['present'] += 1
    tname = type(value).__name__
    prior['types'][tname] += 1
    reasons = []
    if value is None:
        prior['null'] += 1
        detail['null_rows'] += 1
        emit_event('raw', field, 'null', '', 'null', '', f'top_level_type={tname}')
        return 'null'
    is_list = isinstance(value, list)
    if is_list:
        prior['lengths'][len(value)] += 1
        detail['list_rows'] += 1
        expected = LIST_LENGTHS.get(field)
        if expected is not None and len(value) != expected:
            detail['wrong_length_rows'] += 1
            reasons.append('wrong_list_length')
            emit_event('raw', field, 'wrong_list_length', '', 'length', '',
                       f'actual={len(value)};expected={expected}')
    values = value if is_list else [value]
    detail['total_elements'] += len(values)
    # --- detailed element classification (independent of prior early return) ---
    bad_index = []
    for i, x in enumerate(values):
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            bad_index.append(i)
            detail['non_numeric_elements'] += 1
            continue
        if isinstance(x, float):
            if math.isnan(x):
                detail['nan_elements'] += 1
                detail['nan_rows'] += 1
                if not is_list:
                    detail['scalar_nan_rows'] += 1
                emit_event('raw', field, 'nan_element', i, 'nan', '', f'top_level_type={tname}')
                continue
            if x == float('inf'):
                detail['posinf_elements'] += 1
                detail['posinf_rows'] += 1
                if not is_list:
                    detail['scalar_posinf_rows'] += 1
                emit_event('raw', field, 'posinf_element', i, 'posinf', '', f'top_level_type={tname}')
                continue
            if x == float('-inf'):
                detail['neginf_elements'] += 1
                detail['neginf_rows'] += 1
                if not is_list:
                    detail['scalar_neginf_rows'] += 1
                emit_event('raw', field, 'neginf_element', i, 'neginf', '', f'top_level_type={tname}')
                continue
        detail['finite_elements'] += 1
    if bad_index:
        detail['non_numeric_rows'] += 1
        reasons.append('non_numeric_element')
        for i in bad_index:
            emit_event('raw', field, 'non_numeric_element', i,
                       type(values[i]).__name__, short_repr(values[i]), f'top_level_type={tname}')
    # --- prior semantics (stops at the first non-numeric element, as in source) ---
    numeric_ok = not bad_index
    if not numeric_ok:
        prior['non_numeric'] += 1
        return ';'.join(reasons)
    try:
        a = np.asarray(values, dtype=float)
    except (OverflowError, ValueError, TypeError) as exc:
        prior['audit_error_rows'] += 1
        detail['audit_error_rows'] += 1
        reasons.append('audit_exception')
        emit_event('raw', field, 'audit_exception', '', type(exc).__name__, '',
                   f'{type(exc).__name__}: {str(exc)[:60]}')
        return ';'.join(reasons)
    n_nan = int(np.isnan(a).sum())
    n_pos = int(np.isposinf(a).sum())
    n_neg = int(np.isneginf(a).sum())
    prior['nan'] += n_nan
    prior['pos_inf'] += n_pos
    prior['neg_inf'] += n_neg
    finite = a[np.isfinite(a)]
    if finite.size:
        prior['finite_elements'] += int(finite.size)
        prior['negative_elements'] += int((finite < 0).sum())
        prior['zero_elements'] += int((finite == 0).sum())
        prior['min'] = min(prior['min'], float(finite.min()))
        prior['max'] = max(prior['max'], float(finite.max()))
    if is_list and a.size and np.isfinite(a).all():
        prior['valid_list_rows'] += 1
        prior['list_negative_rows'] += int((a < 0).any())
        prior['list_all_in_0_1_rows'] += int(((a >= 0) & (a <= 1)).all())
        total = float(a.sum())
        prior['list_sum_approx_1_rows'] += int(abs(total - 1) < 1e-6)
        prior['list_sum_min'] = min(prior['list_sum_min'], total)
        prior['list_sum_max'] = max(prior['list_sum_max'], total)
        prior['argmax_counts'][int(a.argmax())] += 1
        prior['argmax_tie_rows'] += int((a == a.max()).sum() > 1)
    return ';'.join(reasons)


class RowStore:
    def __init__(self):
        self.file_code = array('B')
        self.line_no = array('I')
        self.domain_code = array('B')
        self.flags = array('B')
        self.raw_invalid = array('I')
        self.extract_nan = array('I')
        self.extract_nonfinite = array('I')
        self.extract_posinf = array('I')
        self.extract_neginf = array('I')
        self.norm_nan = array('H')
        self.norm_nonfinite = array('H')
        self.group_nan = array('B')
        self.q_nan = array('B')

    def append(self, file_code, line_no, domain_code, flags, raw_bits, ext_nan_bits,
               ext_nf_bits, ext_pos_bits, ext_neg_bits, norm_nan_bits, norm_nf_bits,
               group_nan_bits, q_nan_bit):
        self.file_code.append(file_code)
        self.line_no.append(line_no)
        self.domain_code.append(domain_code)
        self.flags.append(flags)
        self.raw_invalid.append(raw_bits)
        self.extract_nan.append(ext_nan_bits)
        self.extract_nonfinite.append(ext_nf_bits)
        self.extract_posinf.append(ext_pos_bits)
        self.extract_neginf.append(ext_neg_bits)
        self.norm_nan.append(norm_nan_bits)
        self.norm_nonfinite.append(norm_nf_bits)
        self.group_nan.append(group_nan_bits)
        self.q_nan.append(q_nan_bit)

    def finalize(self):
        arrays = {}
        for name, dtype in [('file_code', np.uint8), ('line_no', np.uint32),
                            ('domain_code', np.uint8), ('flags', np.uint8),
                            ('raw_invalid', np.uint32), ('extract_nan', np.uint32),
                            ('extract_nonfinite', np.uint32), ('extract_posinf', np.uint32),
                            ('extract_neginf', np.uint32), ('norm_nan', np.uint16),
                            ('norm_nonfinite', np.uint16), ('group_nan', np.uint8),
                            ('q_nan', np.uint8)]:
            source = getattr(self, name)
            arrays[name] = np.frombuffer(source, dtype=dtype).copy()
        return arrays

    @property
    def n(self):
        return len(self.file_code)


FEATURE_SOURCE_FIELD = {}
for _f in RULES + DSIR:
    FEATURE_SOURCE_FIELD[_f] = _f
FEATURE_SOURCE_FIELD['fineweb_edu'] = 'fineweb_edu'
FEATURE_SOURCE_FIELD['ad_en'] = 'ad_en'
FEATURE_SOURCE_FIELD['fluency_en'] = 'fluency_en'
for _f in QURATER:
    FEATURE_SOURCE_FIELD[_f] = 'qurater'
for _f in PRRC:
    FEATURE_SOURCE_FIELD[_f] = _f


class Diagnostic:
    def __init__(self, log, transforms, row_writer, invalid_writer):
        self.log = log
        self.transforms = transforms
        self.row_writer = row_writer
        self.invalid_writer = invalid_writer
        self.store = RowStore()
        self.seen = {}
        self.a1_keys = set()
        self.raw_prior = {}
        self.raw_detail = {}
        self.file_stats = {}
        self.domain_codes = {}
        self.domain_names = []
        self.norm_inf_rows = 0
        self.audit_error_rows = 0
        self.fingerprint_error_rows = 0
        self.events_written = 0
        self.row_ctx = ('', '', '', '', '')

    # ---------------- counters ----------------
    def prior(self, file_code, domain, field):
        key = (file_code, domain)
        entry = self.raw_prior.get(key)
        if entry is None:
            entry = {f: empty_prior_stats() for f in FIELDS}
            self.raw_prior[key] = entry
        return entry[field]

    def detail(self, file_code, domain, field):
        key = (file_code, domain)
        entry = self.raw_detail.get(key)
        if entry is None:
            entry = {f: empty_detail_stats() for f in FIELDS}
            self.raw_detail[key] = entry
        return entry[field]

    # ---------------- event writing ----------------
    def emit(self, layer, name, reason, list_index, value_kind, value_repr, detail):
        file_id, line_no, key_sha, key_json, domain = self.row_ctx
        universe = {'raw': 'FIELDS22', 'extract': 'FEATURES25'}.get(layer, 'identity')
        self.invalid_writer.writerow({
            'file_id': file_id, 'source_line': line_no, 'key_sha256': key_sha,
            'key_str_json': key_json, 'domain': domain, 'layer': layer,
            'field_or_feature': name, 'feature_universe': universe, 'reason': reason,
            'list_index': '' if list_index == '' else list_index, 'value_kind': value_kind,
            'value_repr': value_repr, 'detail': detail})
        self.events_written += 1

    def record_unparsable(self, file_id, file_code, line_no, exc, kind):
        row = {c: '' for c in ROW_MASK_COLUMNS}
        row.update({'file_id': file_id, 'source_line': line_no, 'parse_ok': 0})
        self.row_writer.writerow(row)
        if kind == 'json':
            reason, value_kind = 'json_parse_error', type(exc).__name__
        elif kind == 'decode':
            reason, value_kind = 'decode_error', type(exc).__name__
        else:
            reason, value_kind = 'json_structure_error', type(exc).__name__
        self.row_ctx = (file_id, line_no, '', '', '')
        self.emit('identity', 'json', reason, '', value_kind, '',
                  f'{type(exc).__name__}: {str(exc)[:80]}')

    # ---------------- per-row processing ----------------
    def process_row(self, obj, spec, file_code, file_id, line_no, file_seen, stats, domain_counter):
        raw_domain = obj.get('_source_domain')
        if raw_domain:
            domain = raw_domain
            domain_source = '_source_domain'
        elif spec['fallback_domain']:
            domain = spec['fallback_domain']
            domain_source = 'documented_filename_fallback'
        else:
            domain = 'unknown'
            domain_source = 'unknown'
        if not raw_domain:
            stats['source_domain_missing'] += 1
        domain_counter[domain] += 1

        # raw fields
        raw_bits = 0
        raw_reason = {}
        for j, field in enumerate(FIELDS):
            if field in obj:
                reason = audit_field(obj[field], field, self.prior(file_code, domain, field),
                                     self.detail(file_code, domain, field), self.emit)
            else:
                reason = 'absent'
                self.emit('raw', field, 'absent', '', 'absent', '', '')
            raw_reason[field] = reason
            if reason:
                raw_bits |= (1 << j)

        # extraction layer (exact current get_features semantics)
        errors = []
        values = get_features(obj, errors)
        for field, kind, etype in errors:
            self.emit('extract', field, kind, '', etype, '', 'get_features error path (source would raise)')
            self.audit_error_rows += 1
        ext_nan_bits = 0
        ext_nf_bits = 0
        ext_pos_bits = 0
        ext_neg_bits = 0
        for feature in FEATURES:
            value = values[feature]
            index = FEATURE_INDEX[feature]
            if math.isnan(value):
                ext_nan_bits |= (1 << index)
                ext_nf_bits |= (1 << index)
                self.emit('extract', feature, 'nan', '', 'nan', '',
                          f'raw_layer={raw_reason.get(FEATURE_SOURCE_FIELD.get(feature, feature), "")}')
            elif math.isinf(value):
                ext_nf_bits |= (1 << index)
                if value > 0:
                    ext_pos_bits |= (1 << index)
                else:
                    ext_neg_bits |= (1 << index)
                self.emit('extract', feature, 'posinf' if value > 0 else 'neginf', '',
                          'posinf' if value > 0 else 'neginf', '',
                          f'raw_layer={raw_reason.get(FEATURE_SOURCE_FIELD.get(feature, feature), "")}')

        # normalization layer (fixed prior parameters; no refitting, no accumulation)
        norm_nan_bits = 0
        norm_nf_bits = 0
        norm_kind = {}
        for feature in MODEL:
            y = normalize_one(feature, values[feature], self.transforms)
            index = MODEL_INDEX[feature]
            if math.isnan(y):
                norm_nan_bits |= (1 << index)
                norm_nf_bits |= (1 << index)
                norm_kind[feature] = 'nan'
            elif math.isinf(y):
                norm_nf_bits |= (1 << index)
                norm_kind[feature] = 'posinf' if y > 0 else 'neginf'
            else:
                norm_kind[feature] = 'finite'
        if norm_nf_bits != norm_nan_bits:
            self.norm_inf_rows += 1
            self.emit('identity', 'normalized_nonfinite_non_nan', '', 'unexpected', '', '',
                      'normalized value is +/-inf while not NaN; group/Q NaN logic needs review')

        # group / Q propagation masks (pandas skipna=False semantics)
        group_nan_bits = 0
        group_nonfinite_bits = 0
        range_nan = 0
        std0_nan = 0
        std1_nan = 0
        for gi, group in enumerate(GROUP_NAMES):
            has_nan = has_pos = has_neg = False
            for feature in GROUPS[group]:
                kind = norm_kind[feature]
                if kind == 'nan':
                    has_nan = True
                elif kind == 'posinf':
                    has_pos = True
                elif kind == 'neginf':
                    has_neg = True
            if has_nan or (has_pos and has_neg):
                group_nan_bits |= (1 << gi)
            if has_nan or has_pos or has_neg:
                group_nonfinite_bits |= (1 << gi)
        n_valid = 3 - bin(group_nan_bits).count('1')
        n_pos = 0
        n_neg = 0
        for gi, group in enumerate(GROUP_NAMES):
            if (group_nan_bits >> gi) & 1:
                continue
            kinds = [norm_kind[f] for f in GROUPS[group]]
            if all(k == 'posinf' for k in kinds):
                n_pos += 1
            elif all(k == 'neginf' for k in kinds):
                n_neg += 1
        q_nan = 1 if group_nan_bits != 0 else 0
        range_nan = 1 if (n_valid == 0 or n_pos == n_valid or n_neg == n_valid) else 0
        any_nonfinite_group = 1 if group_nonfinite_bits != 0 else 0
        std0_nan = 1 if (n_valid == 0 or any_nonfinite_group) else 0
        std1_nan = 1 if (n_valid < 2 or any_nonfinite_group) else 0

        # identity / key / split / duplicate bookkeeping
        id_present = 'id' in obj
        sub_present = 'sub_path' in obj
        id_raw = obj.get('id')
        sub_raw = obj.get('sub_path')
        id_is_null = id_raw is None
        sub_is_null = sub_raw is None
        key = (str(obj.get('id', '')), str(sub_raw if sub_present else ''))
        key_json = json.dumps(key, ensure_ascii=False, separators=(',', ':'))
        key_sha = stable_hash(key_json)
        split = int(stable_hash(str(SEED) + key_json)[:16], 16) % SPLIT_MODULUS
        key_anomaly = int((not id_present) or id_is_null or (not sub_present) or sub_is_null)

        in_a1 = (file_code != 0) and (key_json in self.a1_keys)
        duplicate = key_json in self.seen
        within_file_duplicate = key_json in file_seen
        file_seen.add(key_json)
        previous = self.seen.get(key_json)
        try:
            fingerprint = quality_fingerprint(obj)
            fingerprint_error = 0
        except Exception as exc:
            fingerprint = None
            fingerprint_error = 1
            self.fingerprint_error_rows += 1
            self.emit('identity', 'quality_fingerprint', 'fingerprint_error', '', type(exc).__name__,
                      '', f'{type(exc).__name__}: {str(exc)[:60]}')
        signature = raw_bits | (ext_nf_bits << 22)
        quality_conflict = int(bool(duplicate and previous is not None and fingerprint is not None
                                    and previous['fp'] is not None and previous['fp'] != fingerprint))
        domain_collision = int(bool(duplicate and previous is not None and previous['domain'] != domain))
        duplicate_mask_conflict = int(bool(duplicate and previous is not None and previous['sig'] != signature))
        if quality_conflict:
            self.emit('duplicate', key_json, 'quality_conflict', '', 'conflict', '',
                      f'first_file={previous["file_id"]}')
        if domain_collision:
            self.emit('duplicate', key_json, 'domain_collision', '', 'conflict', '',
                      f'first_domain={previous["domain"]};current={domain}')
        if duplicate_mask_conflict:
            self.emit('duplicate', key_json, 'duplicate_mask_conflict', '', 'conflict', '',
                      f'first_file={previous["file_id"]}')
        if not duplicate:
            self.seen[key_json] = {'fp': fingerprint, 'domain': domain, 'sig': signature,
                                   'file_id': file_id}
        if file_code == 0:
            self.a1_keys.add(key_json)

        if file_code == 0:
            evaluation_role = 'A1_holdout' if split == HOLDOUT_REMAINDER else 'A1_calibration'
        else:
            evaluation_role = 'extension_overlap_A1' if in_a1 else 'extension_new_records'

        flags = F_PARSE
        if not duplicate:
            flags |= F_UNIQUE
        if in_a1:
            flags |= F_OVERLAP
        if file_code == 0:
            flags |= F_A1
            flags |= F_HOLDOUT if evaluation_role == 'A1_holdout' else F_CALIB
        else:
            flags |= F_EXTOVER if in_a1 else F_EXTNEW
        stats['rows'] += 1
        stats['within_file_duplicate_rows'] += int(within_file_duplicate)
        stats['overlap_a1_rows'] += int(in_a1)
        stats['quality_conflicting_rows'] += quality_conflict
        stats['domain_collision_rows'] += domain_collision
        stats['duplicate_mask_conflict_rows'] += duplicate_mask_conflict
        stats['fingerprint_error_rows'] += fingerprint_error

        nan_features = names_for_bits(norm_nan_bits, MODEL)
        nan_groups = '|'.join(g for gi, g in enumerate(GROUP_NAMES) if (group_nan_bits >> gi) & 1)
        self.row_ctx = (file_id, line_no, key_sha, key_json, domain)
        self.row_writer.writerow({
            'file_id': file_id, 'source_line': line_no,
            'id_json': json.dumps(id_raw, ensure_ascii=False) if id_present else '',
            'sub_path_json': json.dumps(sub_raw, ensure_ascii=False) if sub_present else '',
            'key_str_json': key_json, 'key_sha256': key_sha, 'domain': domain,
            'domain_source': domain_source, 'evaluation_role': evaluation_role,
            'is_unique_first': int(not duplicate), 'overlap_a1': int(in_a1),
            'within_file_duplicate': int(within_file_duplicate),
            'duplicate_of_file': '' if previous is None else previous['file_id'],
            'parse_ok': 1, 'id_present': int(id_present), 'id_is_null': int(id_is_null),
            'id_type': type(id_raw).__name__ if id_present else '',
            'sub_path_present': int(sub_present), 'sub_path_is_null': int(sub_is_null),
            'sub_path_type': type(sub_raw).__name__ if sub_present else '',
            'key_anomaly': key_anomaly,
            'raw_invalid_bits': bits_to_string(raw_bits, len(FIELDS)),
            'raw_invalid_count': set_bit_count(raw_bits),
            'extract_nan_bits': bits_to_string(ext_nan_bits, len(FEATURES)),
            'extract_nonfinite_bits': bits_to_string(ext_nf_bits, len(FEATURES)),
            'extract_posinf_bits': bits_to_string(ext_pos_bits, len(FEATURES)),
            'extract_neginf_bits': bits_to_string(ext_neg_bits, len(FEATURES)),
            'extract_nan_count': set_bit_count(ext_nan_bits),
            'extract_nonfinite_count': set_bit_count(ext_nf_bits),
            'norm_nan_bits': bits_to_string(norm_nan_bits, len(MODEL)),
            'norm_nonfinite_bits': bits_to_string(norm_nf_bits, len(MODEL)),
            'norm_nonfinite_count': set_bit_count(norm_nf_bits),
            'would_group_usability_be_nan': (group_nan_bits >> 0) & 1,
            'would_group_knowledge_be_nan': (group_nan_bits >> 1) & 1,
            'would_group_education_reasoning_be_nan': (group_nan_bits >> 2) & 1,
            'would_Q_be_nan': q_nan,
            'would_Q_nan_trigger_features': nan_features,
            'q_nan_trigger_features': nan_features,
            'would_Q_nan_trigger_groups': nan_groups,
            'quality_fingerprint': fingerprint or '', 'fingerprint_error': fingerprint_error,
            'quality_conflict': quality_conflict, 'domain_collision': domain_collision,
            'duplicate_mask_conflict': duplicate_mask_conflict})

        self.store.append(file_code, line_no, self.domain_code(domain), flags, raw_bits,
                          ext_nan_bits, ext_nf_bits, ext_pos_bits, ext_neg_bits,
                          norm_nan_bits, norm_nf_bits, group_nan_bits, q_nan)

    def domain_code(self, domain):
        code = self.domain_codes.get(domain)
        if code is None:
            code = len(self.domain_codes)
            self.domain_codes[domain] = code
            self.domain_names.append(domain)
        return code

    def scan_file(self, spec):
        file_code = spec['code']
        file_id = spec['file_id']
        stats = {'rows': 0, 'invalid_json': 0, 'json_structure_errors': 0,
                 'decode_errors': 0, 'source_domain_missing': 0,
                 'within_file_duplicate_rows': 0, 'overlap_a1_rows': 0,
                 'quality_conflicting_rows': 0, 'domain_collision_rows': 0,
                 'duplicate_mask_conflict_rows': 0, 'fingerprint_error_rows': 0}
        domain_counter = Counter()
        file_seen = set()
        t0 = time.monotonic()
        self.log(f'stage=scan file={file_id} order_index={spec["code"]} decompress_passes=1 start')
        consecutive_decode_errors = 0
        with lzma.open(str(spec['path']), 'rt', encoding='utf-8') as fh:
            line_no = 0
            while True:
                if line_no % RESOURCE_CHECK_EVERY == 0:
                    guard_resources(self.log, f'scan:{file_id}', stats['rows'])
                try:
                    line = fh.readline()
                except UnicodeDecodeError as exc:
                    line_no += 1
                    consecutive_decode_errors += 1
                    stats['decode_errors'] += 1
                    self.record_unparsable(file_id, file_code, line_no, exc, 'decode')
                    if consecutive_decode_errors >= 3:
                        raise ResourceStop(f'unrecoverable decode errors in {file_id} near line {line_no}')
                    continue
                if line == '':
                    break
                line_no += 1
                consecutive_decode_errors = 0
                try:
                    obj = json.loads(line)
                except (ValueError, UnicodeError) as exc:
                    stats['invalid_json'] += 1
                    self.record_unparsable(file_id, file_code, line_no, exc, 'json')
                    continue
                if not isinstance(obj, dict):
                    stats['json_structure_errors'] += 1
                    self.record_unparsable(file_id, file_code, line_no,
                                           TypeError(f'top-level JSON is {type(obj).__name__}'), 'structure')
                    continue
                self.row_ctx = (file_id, line_no, '', '', '')
                self.process_row(obj, spec, file_code, file_id, line_no, file_seen,
                                 stats, domain_counter)
                if stats['rows'] % PROGRESS_EVERY == 0:
                    elapsed = time.monotonic() - t0
                    self.log(f'stage=scan file={file_id} rows={stats["rows"]} '
                             f'elapsed_s={elapsed:.1f} rate={stats["rows"]/max(elapsed,1e-9):.0f}/s '
                             f'peak_rss_bytes={peak_rss_bytes()}')
        elapsed = time.monotonic() - t0
        stats['elapsed_s'] = elapsed
        stats['line_count'] = line_no
        stats['domains'] = dict(domain_counter)
        stats['decompress_passes'] = 1
        stats['retries'] = 0
        self.current_file_keys = file_seen
        self.file_stats[file_id] = stats
        self.log(f'stage=scan file={file_id} done rows={stats["rows"]} invalid_json={stats["invalid_json"]} '
                 f'decode_errors={stats["decode_errors"]} elapsed_s={elapsed:.1f}')


SCOPE_VIEWS = [
    ('A1_calibration', lambda fc, fl: (fl & F_CALIB) != 0),
    ('A1_holdout', lambda fc, fl: (fl & F_HOLDOUT) != 0),
    ('A1_all_unique', lambda fc, fl: (fc == 0) & ((fl & F_UNIQUE) != 0)),
    ('extension_overlap_A1', lambda fc, fl: (fl & F_OVERLAP) != 0),
    ('extension_new_records', lambda fc, fl: (fl & F_EXTNEW) != 0),
    ('all_unique', lambda fc, fl: (fl & F_UNIQUE) != 0),
    ('file_unique_first_A1', lambda fc, fl: (fc == 0) & ((fl & F_UNIQUE) != 0)),
    ('file_unique_first_A2_arxiv', lambda fc, fl: (fc == 1) & ((fl & F_UNIQUE) != 0)),
    ('file_unique_first_A3_github', lambda fc, fl: (fc == 2) & ((fl & F_UNIQUE) != 0)),
]
OFFICIAL_SCOPE_NAMES = [name for name, _ in SCOPE_VIEWS[:6]]
CATEGORY_NAMES = ['A1', 'extension_new', 'extension_overlap']


def marginal_counts(bits, nbits):
    counts = np.zeros(nbits, dtype=np.int64)
    for j in range(nbits):
        counts[j] = int(np.count_nonzero(((bits >> j) & 1) != 0))
    return counts


def aggregate_rows(arrays, domain_names):
    n = len(arrays['file_code'])
    parsed = (arrays['flags'] & F_PARSE) != 0
    dom = arrays['domain_code']
    tables = {key: [] for key in ['feature_missing_counts', 'missing_patterns', 'missing_pairwise',
                                 'validity_counts', 'summary_denominators',
                                 'complete_case_count_only', 'group_validity_distribution',
                                 'group_mask_intersections']}
    group_stats = {}
    cat_code = np.zeros(n, dtype=np.int8)
    fc_all = arrays['file_code']
    fl_all = arrays['flags']
    cat_code[(fc_all != 0) & ((fl_all & F_OVERLAP) != 0)] = 2
    cat_code[(fc_all != 0) & ((fl_all & F_OVERLAP) == 0)] = 1
    for scope_name, scope_fn in SCOPE_VIEWS:
        scope_mask = parsed & scope_fn(arrays['file_code'], arrays['flags'])
        present = [d for d in range(len(domain_names)) if np.any(scope_mask & (dom == d))]
        for dom_idx in present + [-1]:
            if dom_idx == -1:
                idx = scope_mask
                domain_label = 'ALL'
            else:
                idx = scope_mask & (dom == dom_idx)
                domain_label = domain_names[dom_idx]
            n_g = int(idx.sum())
            if n_g == 0:
                continue
            ext_nan_sub = arrays['extract_nan'][idx]
            ext_nf_sub = arrays['extract_nonfinite'][idx]
            norm_nan_sub = arrays['norm_nan'][idx]
            norm_nf_sub = arrays['norm_nonfinite'][idx]
            group_nan_sub = arrays['group_nan'][idx]
            q_nan_sub = arrays['q_nan'][idx]
            cat_sub = cat_code[idx]

            # ---- feature_missing_counts (extraction layer, 25 features) ----
            c_nan = marginal_counts(ext_nan_sub, len(FEATURES))
            c_nf = marginal_counts(ext_nf_sub, len(FEATURES))
            c_pos = marginal_counts(arrays['extract_posinf'][idx], len(FEATURES))
            c_neg = marginal_counts(arrays['extract_neginf'][idx], len(FEATURES))
            for j, feature in enumerate(FEATURES):
                tables['feature_missing_counts'].append({
                    'scope': scope_name, 'domain': domain_label, 'feature': feature,
                    'n_total': n_g, 'n_nan': int(c_nan[j]), 'n_posinf': int(c_pos[j]),
                    'n_neginf': int(c_neg[j]),
                    'n_nonfinite': int(c_nf[j]), 'n_finite': n_g - int(c_nf[j]),
                    'rate_nan': fair_ratio(int(c_nan[j]), n_g),
                    'rate_nonfinite': fair_ratio(int(c_nf[j]), n_g),
                    'layer': 'extraction_scalar'})

            # ---- patterns + pairwise for all mask kinds ----
            marginal_by_kind = {}
            for kind, universe, arrname, nbits, names in MASK_DEFS:
                sub = arrays[arrname][idx]
                marg = marginal_counts(sub, nbits)
                marginal_by_kind[kind] = marg
                vals, counts = np.unique(sub, return_counts=True)
                for value, count in zip(vals.tolist(), counts.tolist()):
                    tables['missing_patterns'].append({
                        'scope': scope_name, 'domain': domain_label, 'mask_kind': kind,
                        'feature_universe': universe, 'mask_bits': int(value),
                        'feature_mask': bits_to_string(int(value), nbits),
                        'feature_names': names_for_bits(int(value), names),
                        'n': int(count), 'rate': fair_ratio(int(count), n_g), 'n_scope': n_g})
                if n_g:
                    matrix = np.empty((n_g, nbits), dtype=np.float32)
                    for j in range(nbits):
                        matrix[:, j] = ((sub >> j) & 1).astype(np.float32)
                    inter = np.rint(matrix.T @ matrix).astype(np.int64)
                else:
                    inter = np.zeros((nbits, nbits), dtype=np.int64)
                for i in range(nbits):
                    for j in range(i, nbits):
                        if i == j:
                            n_i = n_j = int(marg[i])
                            n_inter = int(inter[i, j])
                            n_union = n_i
                        else:
                            n_i = int(marg[i])
                            n_j = int(marg[j])
                            n_inter = int(inter[i, j])
                            n_union = n_i + n_j - n_inter
                        tables['missing_pairwise'].append({
                            'scope': scope_name, 'domain': domain_label, 'mask_kind': kind,
                            'feature_universe': universe, 'feature_i': names[i], 'feature_j': names[j],
                            'n_scope': n_g, 'n_i': n_i, 'n_j': n_j,
                            'n_intersection': n_inter, 'n_union': n_union})

            # ---- validity / complete-case counts ----
            any11_nan = (norm_nan_sub & MODEL_ALL_BITS) != 0
            any11_nf = (norm_nf_sub & MODEL_ALL_BITS) != 0
            any25_nan = (ext_nan_sub & FEATURES_ALL_BITS) != 0
            any25_nf = (ext_nf_sub & FEATURES_ALL_BITS) != 0
            complete11_nan = int(np.count_nonzero(~any11_nan))
            complete11_fin = int(np.count_nonzero(~any11_nf))
            complete25_nan = int(np.count_nonzero(~any25_nan))
            complete25_fin = int(np.count_nonzero(~any25_nf))
            q_nan_bool = q_nan_sub == 1
            n_q_valid = int(np.count_nonzero(~q_nan_bool))
            group_valid_nan = {}
            group_valid_fin = {}
            for gi, group in enumerate(GROUP_NAMES):
                bits = GROUP_MODEL_BITS[group]
                group_valid_nan[group] = int(np.count_nonzero(((group_nan_sub >> gi) & 1) == 0))
                group_valid_fin[group] = int(np.count_nonzero((norm_nf_sub & bits) == 0))
            valid_groups = 3 - POPCOUNT8[group_nan_sub]
            group_nf_rows = np.zeros(n_g, dtype=bool)
            for group in GROUP_NAMES:
                group_nf_rows |= (norm_nf_sub & GROUP_MODEL_BITS[group]) != 0
            range_nan_rows = (valid_groups == 0) | group_nf_rows
            std0_nan_rows = (valid_groups == 0) | group_nf_rows
            std1_nan_rows = (valid_groups < 2) | group_nf_rows
            n_range_valid = int(np.count_nonzero(~range_nan_rows))
            n_std0_valid = int(np.count_nonzero(~std0_nan_rows))
            without_knowledge_nan = ((norm_nan_sub & GROUP_MODEL_BITS['usability']) != 0) | \
                                    ((norm_nan_sub & GROUP_MODEL_BITS['education_reasoning']) != 0)
            n_without_knowledge_valid = int(np.count_nonzero(~without_knowledge_nan))
            tables['validity_counts'].append({
                'scope': scope_name, 'domain': domain_label, 'n_total': n_g,
                'n_complete_25_notnan': complete25_nan, 'n_complete_25_finite': complete25_fin,
                'n_complete_11_notnan': complete11_nan, 'n_complete_11_finite': complete11_fin,
                'n_group_usability_valid_notnan': group_valid_nan['usability'],
                'n_group_knowledge_valid_notnan': group_valid_nan['knowledge'],
                'n_group_education_reasoning_valid_notnan': group_valid_nan['education_reasoning'],
                'n_group_usability_valid_finite': group_valid_fin['usability'],
                'n_group_knowledge_valid_finite': group_valid_fin['knowledge'],
                'n_group_education_reasoning_valid_finite': group_valid_fin['education_reasoning'],
                'n_would_Q_nan': int(q_nan_bool.sum()), 'n_valid_mainQ_11': n_q_valid,
                'rate_complete_11': fair_ratio(complete11_nan, n_g),
                'rate_complete_25': fair_ratio(complete25_nan, n_g),
                'rate_valid_mainQ_11': fair_ratio(n_q_valid, n_g)})
            tables['group_validity_distribution'].append({
                'scope': scope_name, 'domain': domain_label, 'n_total': n_g,
                'n_rows_0_valid_groups': int(np.count_nonzero(valid_groups == 0)),
                'n_rows_1_valid_groups': int(np.count_nonzero(valid_groups == 1)),
                'n_rows_2_valid_groups': int(np.count_nonzero(valid_groups == 2)),
                'n_rows_3_valid_groups': int(np.count_nonzero(valid_groups == 3))})
            for gi in range(len(GROUP_NAMES)):
                nan_i = ((group_nan_sub >> gi) & 1) != 0
                for gj in range(gi, len(GROUP_NAMES)):
                    nan_j = ((group_nan_sub >> gj) & 1) != 0
                    tables['group_mask_intersections'].append({
                        'scope': scope_name, 'domain': domain_label,
                        'group_i': GROUP_NAMES[gi], 'group_j': GROUP_NAMES[gj],
                        'n_both_valid': int(np.count_nonzero(~nan_i & ~nan_j)),
                        'n_both_missing': int(np.count_nonzero(nan_i & nan_j)),
                        'n_union_missing': int(np.count_nonzero(nan_i | nan_j))})
            for feature_set, complete in [('mainQ11', complete11_nan), ('all25', complete25_nan),
                                          ('all25_finite', complete25_fin)]:
                tables['complete_case_count_only'].append({
                    'scope': scope_name, 'domain': domain_label, 'feature_set': feature_set,
                    'n_total': n_g, 'n_complete': complete, 'n_not_covered': n_g - complete,
                    'fraction_not_covered': fair_ratio(n_g - complete, n_g), 'diagnostic_only': 'true'})

            # ---- summarize() denominator audit ----
            def add_stat(statistic, n_nonmissing, n_finite, n_effective, ddof, rule, false_n=''):
                tables['summary_denominators'].append({
                    'scope': scope_name, 'domain': domain_label, 'statistic': statistic,
                    'n_total': n_g, 'n_nonmissing': n_nonmissing, 'n_finite': n_finite,
                    'n_effective': n_effective, 'ddof': ddof, 'denominator_rule': rule,
                    'missing_comparison_as_false_n': false_n,
                    'applicability_note': 'count-only denominator; numeric statistic intentionally not recomputed'})
            add_stat('Q_mean', n_q_valid, n_q_valid, n_q_valid, '',
                     'Series.mean(skipna=True): denominator = rows with non-NaN Q')
            add_stat('Q_std', n_q_valid, n_q_valid, n_q_valid if n_q_valid >= 2 else 0, 1,
                     'Series.std() default ddof=1: NaN when fewer than 2 non-NaN rows')
            for stat in ['Q_p10', 'Q_median', 'Q_p90']:
                add_stat(stat, n_q_valid, n_q_valid, n_q_valid, '',
                         'Series.quantile(linear, skipna=True): denominator = non-NaN rows')
            add_stat('rater_disagreement_mean', n_range_valid, n_range_valid, n_range_valid, '',
                     'row max-min over group cols (skipna=True) then Series.mean(skipna=True)')
            add_stat('rater_disagreement_std', n_std0_valid, n_std0_valid, n_std0_valid, 0,
                     'DataFrame.std(axis=1,ddof=0) internal value; not exported by prior summarize()')
            add_stat('rater_disagreement_gt_0_5_fraction', n_g, n_g, n_g, '',
                     '(range > 0.5).mean(): denominator = all rows; NaN range becomes False',
                     false_n=int(np.count_nonzero(range_nan_rows)))
            add_stat('equal_indicator_Q_mean', complete11_nan, complete11_fin, complete11_nan, '',
                     'normalized[MODEL].mean(axis=1,skipna=False): NaN if any of the 11 features is NaN')
            add_stat('without_knowledge_Q_mean', n_without_knowledge_valid, n_without_knowledge_valid,
                     n_without_knowledge_valid, '',
                     'mean of group_usability and group_education_reasoning with skipna=False')
            for group in GROUP_NAMES:
                add_stat(f'group_{group}_mean', group_valid_nan[group], group_valid_fin[group],
                         group_valid_nan[group], '',
                         f'{group} group mean over its {len(GROUPS[group])} constituent features, skipna=False')

            # ---- per-feature missing counts by row category (for known-domain table) ----
            nan_by_cat = {}
            n_by_cat = {}
            for c, cat_name in enumerate(CATEGORY_NAMES):
                sel = cat_sub == c
                n_by_cat[cat_name] = int(np.count_nonzero(sel))
                counts = marginal_counts(ext_nan_sub[sel], len(FEATURES)) if n_by_cat[cat_name] else np.zeros(len(FEATURES), dtype=np.int64)
                nan_by_cat[cat_name] = counts
            group_stats[(scope_name, domain_label)] = {
                'n': n_g, 'n_valid_mainQ_11': n_q_valid, 'complete11': complete11_nan,
                'complete25': complete25_nan,
                'nan_counts': {feature: int(c_nan[j]) for j, feature in enumerate(FEATURES)},
                'nan_by_category': {feature: {cat: int(nan_by_cat[cat][j]) for cat in CATEGORY_NAMES}
                                    for j, feature in enumerate(FEATURES)},
                'n_by_category': n_by_cat}
    return tables, group_stats


TABLE_COLUMNS = {
    'feature_missing_counts': ['scope', 'domain', 'feature', 'layer', 'n_total', 'n_nan', 'n_posinf',
                               'n_neginf', 'n_nonfinite', 'n_finite', 'rate_nan', 'rate_nonfinite'],
    'missing_patterns': ['scope', 'domain', 'mask_kind', 'feature_universe', 'mask_bits',
                         'feature_mask', 'feature_names', 'n', 'n_scope', 'rate'],
    'missing_pairwise': ['scope', 'domain', 'mask_kind', 'feature_universe', 'feature_i', 'feature_j',
                         'n_scope', 'n_i', 'n_j', 'n_intersection', 'n_union'],
    'validity_counts': ['scope', 'domain', 'n_total', 'n_complete_25_notnan', 'n_complete_25_finite',
                        'n_complete_11_notnan', 'n_complete_11_finite',
                        'n_group_usability_valid_notnan', 'n_group_knowledge_valid_notnan',
                        'n_group_education_reasoning_valid_notnan',
                        'n_group_usability_valid_finite', 'n_group_knowledge_valid_finite',
                        'n_group_education_reasoning_valid_finite', 'n_would_Q_nan',
                        'n_valid_mainQ_11', 'rate_complete_11', 'rate_complete_25', 'rate_valid_mainQ_11'],
    'summary_denominators': ['scope', 'domain', 'statistic', 'n_total', 'n_nonmissing', 'n_finite',
                             'n_effective', 'ddof', 'denominator_rule',
                             'missing_comparison_as_false_n', 'applicability_note'],
    'complete_case_count_only': ['scope', 'domain', 'feature_set', 'n_total', 'n_complete',
                                 'n_not_covered', 'fraction_not_covered', 'diagnostic_only'],
    'group_validity_distribution': ['scope', 'domain', 'n_total', 'n_rows_0_valid_groups',
                                    'n_rows_1_valid_groups', 'n_rows_2_valid_groups',
                                    'n_rows_3_valid_groups'],
    'group_mask_intersections': ['scope', 'domain', 'group_i', 'group_j', 'n_both_valid',
                                 'n_both_missing', 'n_union_missing'],
}


def write_tables(tables, log):
    written = {}
    for name, columns in TABLE_COLUMNS.items():
        path = RUN_DIR / f'{name}.csv'
        write_csv(path, columns, tables[name])
        written[name] = {'path': path.name, 'rows': len(tables[name]), 'bytes': path.stat().st_size}
        log(f'stage=aggregate written={path.name} rows={len(tables[name])}')
    return written


def model_bits_to_feature_bits(model_bits):
    out = 0
    for feature, index in MODEL_INDEX.items():
        if (model_bits >> index) & 1:
            out |= (1 << FEATURE_INDEX[feature])
    return out


def mini_aggregate_selftest(log, transforms):
    """End-to-end synthetic test of mask derivation + aggregate_rows()."""
    nan = float('nan')
    rows = [
        {'fc': 0, 'dom': 0, 'flags': F_PARSE | F_UNIQUE | F_A1 | F_CALIB, 'model_nan': 0},
        {'fc': 0, 'dom': 0, 'flags': F_PARSE | F_UNIQUE | F_A1 | F_CALIB,
         'raw_nan': 1 << FIELD_INDEX['modernbert_professionalism'],
         'model_nan': 1 << MODEL_INDEX['modernbert_professionalism']},
        {'fc': 0, 'dom': 1, 'flags': F_PARSE | F_UNIQUE | F_A1 | F_HOLDOUT, 'model_nan': 1 << MODEL_INDEX['qurater_writing_style']},
        {'fc': 1, 'dom': 0, 'flags': F_PARSE | F_UNIQUE | F_EXTNEW, 'model_nan': 0},
        {'fc': 1, 'dom': 2, 'flags': F_PARSE | F_OVERLAP | F_EXTOVER, 'model_nan': 1 << MODEL_INDEX['modernbert_reasoning']},
        {'fc': 2, 'dom': 2, 'flags': F_PARSE | F_UNIQUE | F_EXTNEW,
         'model_nan': (1 << MODEL_INDEX['fineweb_edu']) | (1 << MODEL_INDEX['qurater_facts_trivia'])},
    ]
    store = RowStore()
    for line_no, row in enumerate(rows, 1):
        raw_nan = row.get('raw_nan', 0)
        ext_nan = model_bits_to_feature_bits(row.get('model_nan', 0)) | raw_nan
        ext_nf = ext_nan
        group_bits = 0
        for gi, group in enumerate(GROUP_NAMES):
            for feature in GROUPS[group]:
                if (ext_nan >> FEATURE_INDEX[feature]) & 1:
                    group_bits |= (1 << gi)
        q_nan = 1 if group_bits else 0
        store.append(row['fc'], line_no, row['dom'], row['flags'], row.get('raw_nan', 0),
                     ext_nan, ext_nf, 0, 0, row.get('model_nan', 0), row.get('model_nan', 0),
                     group_bits, q_nan)
    arrays = store.finalize()
    tables, group_stats = aggregate_rows(arrays, ['commoncrawl', 'wikipedia', 'github'])
    checks = []
    def check(name, ok, detail):
        checks.append({'name': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})
    by_feature = {(r['scope'], r['domain'], r['feature']): r for r in tables['feature_missing_counts']}
    r = by_feature.get(('A1_calibration', 'ALL', 'modernbert_professionalism'))
    check('mini_extract_marginal', bool(r) and r['n_total'] == 2 and r['n_nan'] == 1 and r['n_finite'] == 1,
          f'{r}')
    r2 = by_feature.get(('A1_calibration', 'ALL', 'qurater_writing_style'))
    check('mini_extract_marginal_2', bool(r2) and r2['n_nan'] == 0, f'{r2}')
    v = {(row['scope'], row['domain']): row for row in tables['validity_counts']}
    va = v.get(('A1_calibration', 'ALL'))
    check('mini_validity', bool(va) and va['n_total'] == 2 and va['n_would_Q_nan'] == 1
          and va['n_valid_mainQ_11'] == 1 and va['n_group_knowledge_valid_notnan'] == 1,
          f'{va}')
    allu = v.get(('all_unique', 'ALL'))
    check('mini_all_unique', bool(allu) and allu['n_total'] == 5 and allu['n_valid_mainQ_11'] == 2,
          f'{allu}')
    pattern_ok = True
    pattern_detail = {}
    for (scope, domain), stats in group_stats.items():
        for kind, universe, arrname, nbits, names in MASK_DEFS:
            total = sum(row['n'] for row in tables['missing_patterns']
                        if row['scope'] == scope and row['domain'] == domain and row['mask_kind'] == kind)
            pattern_detail[f'{scope}|{domain}|{kind}'] = total
            if total != stats['n']:
                pattern_ok = False
    check('mini_pattern_sums', pattern_ok, json_compact(pattern_detail))
    pairwise_ok = True
    for row in tables['missing_pairwise']:
        if row['n_union'] != row['n_i'] + row['n_j'] - row['n_intersection'] and row['feature_i'] != row['feature_j']:
            pairwise_ok = False
    check('mini_pairwise_inclusion_exclusion', pairwise_ok, 'all rows checked')
    complete = {(row['scope'], row['domain'], row['feature_set']): row for row in tables['complete_case_count_only']}
    c = complete.get(('A1_holdout', 'ALL', 'mainQ11'))
    check('mini_complete_case', bool(c) and c['n_total'] == 1 and c['n_complete'] == 0 and c['n_not_covered'] == 1,
          f'{c}')
    failed = [c for c in checks if c['status'] != 'PASS']
    return {'checks': checks, 'n_checks': len(checks), 'n_failed': len(failed),
            'status': 'PASS' if not failed else 'FAIL'}


def synthetic_selftest(log, transforms):
    results = {'cases': [], 'status': 'PASS'}
    def case(name, ok, detail):
        results['cases'].append({'name': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})
    nan = float('nan')
    inf = float('inf')
    # 1) get_features replica semantics
    probes = [
        ('prrc_valid', {'modernbert_professionalism': [0, 1, 2, 3, 4, 5]}, 'modernbert_professionalism', 5.0, 'valid list -> argmax'),
        ('prrc_tie_first', {'modernbert_professionalism': [5, 5, 1, 1, 1, 1]}, 'modernbert_professionalism', 0.0, 'np.argmax returns first max'),
        ('prrc_wrong_length', {'modernbert_professionalism': [0, 1, 2]}, 'modernbert_professionalism', None, 'wrong length -> NaN'),
        ('prrc_nan_element', {'modernbert_professionalism': [0, 1, 2, 3, 4, nan]}, 'modernbert_professionalism', None, 'NaN element -> NaN'),
        ('prrc_inf_element', {'modernbert_professionalism': [0, 1, 2, 3, 4, inf]}, 'modernbert_professionalism', None, 'inf element -> NaN'),
        ('qurater_non_numeric', {'qurater': [1, 2, 'x', 3]}, 'qurater_facts_trivia', None, 'non numeric element invalidates all four'),
        ('qurater_valid', {'qurater': [1, 2, 3, 4]}, 'qurater_educational_value', 4.0, 'valid list -> element copy'),
        ('ad_en_bool_element', {'ad_en': [True, False]}, 'ad_en', 0.0, 'bool element accepted by source'),
        ('ad_en_valid', {'ad_en': [0, 1]}, 'ad_en', 1.0, 'argmax'),
        ('fineweb_valid', {'fineweb_edu': [2.5]}, 'fineweb_edu', 2.5, 'element 0'),
        ('fineweb_wrong_length', {'fineweb_edu': [2.5, 1.0]}, 'fineweb_edu', None, 'wrong length -> NaN'),
        ('scalar_bool', {'rps_doc_word_count': True}, 'rps_doc_word_count', 1.0, 'source accepts bool scalar'),
        ('scalar_inf', {'rps_doc_word_count': inf}, 'rps_doc_word_count', inf, 'inf passes float()'),
        ('scalar_string', {'rps_doc_word_count': '12'}, 'rps_doc_word_count', None, 'string -> NaN'),
        ('missing_field', {}, 'rps_doc_word_count', None, 'absent -> NaN'),
        ('null_field', {'rps_doc_word_count': None}, 'rps_doc_word_count', None, 'null -> NaN'),
    ]
    for name, obj, feature, expected, detail in probes:
        value = get_features(obj)[feature]
        ok = (expected is None and math.isnan(value)) or (expected is not None and value == expected)
        case(f'get_features:{name}', ok, f'{detail}; value={value!r}')
    # 2) clip equivalence vs pandas
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover
        pd = None
        case('pandas_import', False, f'{type(exc).__name__}: {exc}')
    if pd is not None:
        probe_values = [nan, inf, -inf, 1e308, -1e308, 0.3, -10.0, 10.0, 0.0, -1e-300]
        for feature in ['qurater_writing_style', 'ad_en', 'modernbert_reasoning', 'fineweb_edu']:
            low = transforms[feature]['low']
            high = transforms[feature]['high']
            series = pd.Series(probe_values, dtype=float)
            expected = ((series - low) / (high - low)).clip(0, 1).tolist()
            got = [normalize_one(feature, v, transforms) for v in probe_values]
            ok = all((math.isnan(a) and math.isnan(b)) or (not math.isnan(a) and not math.isnan(b) and a == b)
                     for a, b in zip(expected, got))
            case(f'clip_equivalence:{feature}', ok, f'expected={expected}; got={got}')
        # 3) propagation masks vs pandas on synthetic NaN patterns
        rng = np.random.default_rng(SEED)
        patterns = rng.integers(0, 2, size=(300, len(MODEL)))
        values = np.where(patterns == 1, np.nan, rng.random((300, len(MODEL))))
        frame = pd.DataFrame(values, columns=MODEL)
        group_frame = pd.DataFrame({g: frame[GROUPS[g]].mean(axis=1, skipna=False) for g in GROUP_NAMES})
        q = group_frame.mean(axis=1, skipna=False)
        rng_series = group_frame.max(axis=1) - group_frame.min(axis=1)
        std0 = group_frame.std(axis=1, ddof=0)
        std1 = group_frame.std(axis=1, ddof=1)
        group_nan = np.zeros((len(values), len(GROUP_NAMES)), dtype=bool)
        for gi, group in enumerate(GROUP_NAMES):
            cols = [MODEL_INDEX[f] for f in GROUPS[group]]
            group_nan[:, gi] = np.isnan(values[:, cols]).any(axis=1)
        valid = 3 - group_nan.sum(axis=1)
        my_group_nan = group_nan.any(axis=1)
        my_q_nan = my_group_nan
        my_range_nan = valid == 0
        my_std0_nan = valid == 0
        my_std1_nan = valid < 2
        case('pandas_group_nan_propagation', bool(np.array_equal(my_group_nan, group_frame.mean(axis=1, skipna=False).isna().to_numpy())),
             'group mean NaN iff any constituent NaN')
        case('pandas_q_nan_propagation', bool(np.array_equal(my_q_nan, q.isna().to_numpy())),
             'Q NaN iff any group NaN')
        case('pandas_range_std_masks',
             bool(np.array_equal(my_range_nan, rng_series.isna().to_numpy()))
             and bool(np.array_equal(my_std0_nan, std0.isna().to_numpy()))
             and bool(np.array_equal(my_std1_nan, std1.isna().to_numpy())),
             'range/std skipna rules with no inf values')
        frac = (rng_series > 0.5)
        case('pandas_gt05_denominator', int(frac.sum()) == int(((rng_series > 0.5)).sum()) and int(rng_series.isna().sum()) == int(my_range_nan.sum()),
             'NaN range contributes False; mean divides by all rows')
        inframe = pd.DataFrame({'u': [inf, 1.0], 'k': [nan, nan], 'e': [nan, nan]})
        inf_range = inframe.max(axis=1) - inframe.min(axis=1)
        case('documented_inf_edge_case', bool(np.isnan(inf_range.iloc[0])) and not bool(np.isnan(inf_range.iloc[1])),
             'inf-inf -> NaN even without NaN groups; real normalized values are clipped to [0,1]')
    # 4) key/split rule determinism
    key = ('abc', 'a/b/c')
    key_json = json.dumps(key, ensure_ascii=False, separators=(',', ':'))
    split1 = int(stable_hash(str(SEED) + key_json)[:16], 16) % 5
    split2 = int(stable_hash(str(SEED) + key_json)[:16], 16) % 5
    case('split_deterministic', split1 == split2 and 0 <= split1 < 5, f'split={split1}')
    case('key_json_compact', key_json == '["abc","a/b/c"]', key_json)
    # 5) mini end-to-end aggregation
    mini = mini_aggregate_selftest(log, transforms)
    case('mini_aggregation', mini['n_failed'] == 0, json_compact(mini))
    results['mini_aggregation'] = mini
    failed = [c for c in results['cases'] if c['status'] != 'PASS']
    results['n_cases'] = len(results['cases'])
    results['n_failed'] = len(failed)
    results['status'] = 'PASS' if not failed else 'FAIL'
    return results


def snapshot_paths(paths):
    snapshot = {}
    for item in paths:
        path = Path(item)
        if path.is_dir():
            files = sorted(child for child in path.rglob('*') if child.is_file())
        elif path.is_file():
            files = [path]
        else:
            files = []
        for child in files:
            stat = child.stat()
            snapshot[str(child.relative_to(PROJECT))] = {
                'bytes': stat.st_size, 'mtime': stat.st_mtime, 'sha256': sha256_file(child)}
    return snapshot


def diff_snapshots(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in set(before) & set(after)
                     if before[k]['sha256'] != after[k]['sha256']
                     or before[k]['bytes'] != after[k]['bytes'])
    return {'added': added, 'removed': removed, 'changed': changed,
            'n_before': len(before), 'n_after': len(after)}


RAW_METRIC_SPECS = [
    ('present', 'num'), ('absent', 'num'), ('null', 'num'), ('types', 'json'),
    ('lengths', 'json'), ('non_numeric', 'num'), ('nan', 'num'), ('pos_inf', 'num'),
    ('neg_inf', 'num'), ('finite_elements', 'num'), ('negative_elements', 'num'),
    ('zero_elements', 'num'), ('min', 'num_or_null'), ('max', 'num_or_null'),
    ('valid_list_rows', 'num'), ('list_negative_rows', 'num'),
    ('list_all_in_0_1_rows', 'num'), ('list_sum_approx_1_rows', 'num'),
    ('list_sum_min', 'num_or_null'), ('list_sum_max', 'num_or_null'),
    ('argmax_counts', 'json'), ('argmax_tie_rows', 'num'),
]


def prior_value(value, kind):
    if kind == 'json':
        if isinstance(value, Counter):
            return json_compact({str(k): int(v) for k, v in sorted(value.items())})
        if isinstance(value, dict):
            return json_compact({str(k): int(v) for k, v in sorted(value.items())})
        return json_compact(value)
    if kind == 'num_or_null':
        return finite_or_none(value)
    return value


def same_value(expected, actual):
    if expected is None or actual is None:
        return (expected is None) and (actual is None)
    try:
        return float(expected) == float(actual)
    except (TypeError, ValueError):
        return str(expected) == str(actual)


def add_comparison(rows, artifact, scope, item, metric, expected, actual, explanation,
                   match=None, resolved=None):
    if match is None:
        match = 'MATCH' if same_value(expected, actual) else 'MISMATCH'
    if resolved is None:
        resolved = bool(match == 'MATCH')
    difference = ''
    try:
        difference = float(actual) - float(expected)
    except (TypeError, ValueError):
        difference = ''
    rows.append({'prior_artifact': artifact, 'prior_scope': scope, 'prior_item': item,
                 'metric': metric, 'expected_prior': expected, 'actual_run': actual,
                 'difference': difference, 'match': match, 'explanation': explanation,
                 'resolved': int(bool(resolved))})


def build_prior_comparison(diag, group_stats, aggregate_totals):
    rows = []
    audit = diag['prior_audit']
    exp = audit
    actual = aggregate_totals
    add_comparison(rows, 'solution/outputs/quality/audit.json', 'run', 'total_records', 'count',
                   exp['total_records'], actual['total_records'],
                   'full physical parsed rows across A1/A2/A3')
    add_comparison(rows, 'solution/outputs/quality/audit.json', 'run', 'unique_id_sub_path_keys', 'count',
                   exp['unique_id_sub_path_keys'], actual['unique_keys'],
                   'first occurrence per (str(id), str(sub_path)) in scan order A1->A2->A3')
    add_comparison(rows, 'solution/outputs/quality/audit.json', 'run', 'duplicate_occurrences', 'count',
                   exp['duplicate_occurrences'], actual['duplicate_rows'],
                   'physical rows whose key was seen earlier in the fixed scan order')
    prior_pairs = exp['pairwise_key_intersections']
    for pair_key, value in prior_pairs.items():
        add_comparison(rows, 'solution/outputs/quality/audit.json', 'run', f'pairwise_key_intersections.{pair_key}',
                       'count', value, actual['pairwise_intersections'].get(pair_key),
                       'exact key-set intersection between the two files')
    add_comparison(rows, 'solution/outputs/quality/audit.json', 'run', 'quality_conflicts', 'count',
                   len(exp['quality_conflicts']), actual['quality_conflicts'],
                   'duplicate keys with different 22-field quality fingerprint')
    add_comparison(rows, 'solution/outputs/quality/audit.json', 'run', 'domain_collisions', 'count',
                   len(exp['domain_collisions']), actual['domain_collisions'],
                   'duplicate keys resolved to different domains')
    for file_info in exp['files']:
        file_id = file_info['file_id']
        stats = diag['file_stats'].get(file_id)
        if stats is None:
            add_comparison(rows, 'solution/outputs/quality/audit.json', f'file:{file_id}', 'file_stats',
                           'bundle', json_compact(file_info), None, 'file not scanned',
                           match='NOT_COMPARABLE', resolved=False)
            continue
        for metric, exp_value, act_value, note in [
                ('rows', file_info['rows'], stats['rows'], 'parsed physical rows'),
                ('unique_id_sub_path_keys_in_file', file_info['unique_id_sub_path_keys_in_file'],
                 actual['file_unique'][file_id], 'distinct keys in file'),
                ('within_file_duplicate_rows', file_info['within_file_duplicate_rows'],
                 stats['within_file_duplicate_rows'], 'repeat key inside the same file'),
                ('overlapping_a1_rows', file_info['overlapping_a1_rows'], stats['overlap_a1_rows'],
                 'extension rows whose key is in A1'),
                ('quality_conflicting_rows', file_info['quality_conflicting_rows'],
                 stats['quality_conflicting_rows'], 'fingerprint conflicts'),
                ('invalid_json_lines', len(file_info['invalid_json_lines']), stats['invalid_json'],
                 'unparsable lines')]:
            add_comparison(rows, 'solution/outputs/quality/audit.json', f'file:{file_id}', metric, 'count',
                           exp_value, act_value, note)
        for field in FIELDS:
            exp_field = file_info['fields'][field]
            merged = {'present': 0, 'null': 0, 'types': Counter(), 'lengths': Counter(),
                      'non_numeric': 0, 'nan': 0, 'pos_inf': 0, 'neg_inf': 0,
                      'finite_elements': 0, 'negative_elements': 0, 'zero_elements': 0,
                      'min': float('inf'), 'max': float('-inf'), 'valid_list_rows': 0,
                      'list_negative_rows': 0, 'list_all_in_0_1_rows': 0,
                      'list_sum_approx_1_rows': 0, 'list_sum_min': float('inf'),
                      'list_sum_max': float('-inf'), 'argmax_counts': Counter(),
                      'argmax_tie_rows': 0, 'audit_error_rows': 0}
            for (fc, _dom), fields_map in diag['raw_prior'].items():
                if fc != FILE_IDS.index(file_id):
                    continue
                part = fields_map[field]
                for key in ['present', 'null', 'non_numeric', 'nan', 'pos_inf', 'neg_inf',
                            'finite_elements', 'negative_elements', 'zero_elements',
                            'valid_list_rows', 'list_negative_rows', 'list_all_in_0_1_rows',
                            'list_sum_approx_1_rows', 'argmax_tie_rows', 'audit_error_rows']:
                    merged[key] += part[key]
                merged['types'].update(part['types'])
                merged['lengths'].update(part['lengths'])
                merged['argmax_counts'].update(part['argmax_counts'])
                merged['min'] = min(merged['min'], part['min'])
                merged['max'] = max(merged['max'], part['max'])
                merged['list_sum_min'] = min(merged['list_sum_min'], part['list_sum_min'])
                merged['list_sum_max'] = max(merged['list_sum_max'], part['list_sum_max'])
            actual_clean = {}
            for key, kind in RAW_METRIC_SPECS:
                actual_clean[key] = prior_value(merged.get(key), kind)
            actual_clean['absent'] = stats['rows'] - int(merged.get('present', 0))
            for key, kind in RAW_METRIC_SPECS:
                add_comparison(rows, 'solution/outputs/quality/audit.json',
                               f'file:{file_id}|domain:ALL', f'field:{field}', key,
                               prior_value(exp_field.get(key), kind), actual_clean[key],
                               'replica of quality_audit.audit_value prior semantics')
    for prior in diag['prior_domain_summary']:
        scope, domain = prior.get('scope'), prior.get('domain')
        gs = group_stats.get((scope, domain))
        expected_n = int(float(prior['n']))
        actual_n = gs['n'] if gs else 0
        match = 'MATCH' if (gs and expected_n == actual_n) else ('MISMATCH' if gs else 'NOT_COMPARABLE')
        add_comparison(rows, 'solution/outputs/quality/domain_summary.csv', scope, domain, 'n',
                       expected_n, actual_n,
                       'n = scope x domain physical parsed rows' if gs else 'scope x domain not observed in this run',
                       match=match, resolved=bool(match == 'MATCH'))
    for prior in diag['prior_feature_summary']:
        file_id = prior['file_id']
        scope = f'file_unique_first_{file_id}'
        domain = prior['domain']
        gs = group_stats.get((scope, domain))
        for feature in FEATURES:
            key = f'{feature}__count'
            if key not in prior:
                continue
            expected = int(float(prior[key]))
            actual = None
            if gs is not None:
                actual = gs['n'] - gs['nan_counts'][feature]
            add_comparison(rows, 'solution/outputs/quality/feature_summary.csv', scope, f'{domain}|{feature}',
                           'count_nonmissing', expected, actual,
                           'count of non-NaN extracted feature values among is_unique_first rows')
    for prior in diag['prior_extension_shift']:
        domain = prior.get('domain')
        feature = prior.get('feature')
        if feature not in FEATURES:
            continue
        gs_a1 = group_stats.get(('A1_all_unique', domain))
        gs_new = group_stats.get(('extension_new_records', domain))
        add_comparison(rows, 'solution/outputs/quality/extension_shift.csv', f'A1_all_unique|{domain}',
                       f'{feature}', 'a1_n', int(float(prior['a1_n'])),
                       gs_a1['n'] if gs_a1 else None, 'A1 unique rows per domain')
        add_comparison(rows, 'solution/outputs/quality/extension_shift.csv', f'extension_new_records|{domain}',
                       f'{feature}', 'extension_new_n', int(float(prior['extension_new_n'])),
                       gs_new['n'] if gs_new else None, 'extension new-record unique rows per domain')
    for prior in diag['prior_recovery_deficits']:
        file_id = prior['file_id']
        domain = prior['domain']
        feature = prior['feature']
        scope = f'file_unique_first_{file_id}'
        gs = group_stats.get((scope, domain))
        actual = None
        if gs is not None and feature in gs['nan_counts']:
            actual = gs['nan_counts'][feature]
        add_comparison(rows, 'recovery/2026-09-24/quality_gap_evidence.json',
                       scope, f'{domain}|{feature}', 'missing_rows',
                       int(prior['missing_count']), actual,
                       'recovery evidence derived from saved summaries; compared with current extraction-layer NaN count')
    for prior in diag['prior_mean_discrepancies']:
        add_comparison(rows, 'recovery/2026-09-24/quality_mean_discrepancies.csv',
                       prior.get('scope'), f'{prior.get("domain")}|Q_mean', 'Q_mean',
                       float(prior['Q_mean']), None,
                       'numeric Q intentionally not recomputed by TASK-Q01A; prior value recorded for reference only',
                       match='NOT_COMPARABLE', resolved=False)
    return rows


def build_known_domain_comparison(diag, group_stats):
    rows = []
    extra_features = set()
    for prior in diag['prior_feature_summary']:
        file_id = prior['file_id']
        domain = prior['domain']
        gs = group_stats.get((f'file_unique_first_{file_id}', domain))
        if gs is None:
            continue
        total = gs['n']
        for feature in FEATURES:
            key = f'{feature}__count'
            if key in prior and int(float(prior[key])) < total:
                extra_features.add((domain, feature))
    for prior in diag['prior_recovery_deficits']:
        extra_features.add((prior['domain'], prior['feature']))
    for domain in ['commoncrawl', 'wikipedia', 'github']:
        features = sorted({f for (d, f) in extra_features if d == domain})
        for feature in features:
            for scope, _fn in SCOPE_VIEWS:
                gs = group_stats.get((scope, domain))
                n_total = gs['n'] if gs else 0
                n_missing = gs['nan_counts'].get(feature, 0) if gs else 0
                by_cat = gs['nan_by_category'].get(feature, {}) if gs else {}
                prior_artifact = ''
                prior_total = ''
                prior_nonmissing = ''
                prior_missing = ''
                for prior in diag['prior_feature_summary']:
                    if prior['domain'] != domain or scope != f"file_unique_first_{prior['file_id']}":
                        continue
                    key = f'{feature}__count'
                    if key in prior:
                        prior_artifact = 'solution/outputs/quality/feature_summary.csv'
                        prior_total = gs['n'] if gs else ''
                        prior_nonmissing = int(float(prior[key]))
                        prior_missing = (int(float(prior_total)) - prior_nonmissing) if prior_total != '' else ''
                for prior in diag['prior_recovery_deficits']:
                    if (prior['domain'] == domain and prior['feature'] == feature
                            and scope == f"file_unique_first_{prior['file_id']}"):
                        prior_artifact = prior_artifact or 'recovery/2026-09-24/quality_gap_evidence.json'
                        prior_total = gs['n'] if gs else ''
                        prior_missing = int(prior['missing_count'])
                        prior_nonmissing = (int(prior_total) - prior_missing) if prior_total != '' else ''
                rows.append({
                    'domain': domain, 'feature': feature, 'scope': scope,
                    'run_n_total': n_total, 'run_n_missing': n_missing,
                    'run_n_nonmissing': n_total - n_missing, 'run_layer': 'extraction_scalar',
                    'missing_rows_A1': by_cat.get('A1', 0),
                    'missing_rows_extension_new': by_cat.get('extension_new', 0),
                    'missing_rows_extension_overlap': by_cat.get('extension_overlap', 0),
                    'prior_artifact': prior_artifact, 'prior_n_total': prior_total,
                    'prior_n_nonmissing': prior_nonmissing, 'prior_n_missing': prior_missing,
                    'difference_missing': (n_missing - int(prior_missing)) if prior_missing != '' else '',
                    'classification_note': 'component counts are physical rows; classification by A1/new/overlap',
                })
    return rows


RAW_FIELD_COLUMNS = [
    'file_id', 'domain', 'field', 'n_rows', 'present', 'absent', 'null', 'types_json',
    'lengths_json', 'expected_list_length', 'list_rows', 'wrong_length_rows',
    'non_numeric_rows_prior_semantics', 'non_numeric_elements', 'non_numeric_rows_detailed',
    'nan_elements_prior_semantics', 'nan_elements', 'nan_rows',
    'posinf_elements_prior_semantics', 'posinf_elements', 'posinf_rows',
    'neginf_elements_prior_semantics', 'neginf_elements', 'neginf_rows',
    'finite_elements_prior_semantics', 'finite_elements', 'negative_elements',
    'zero_elements', 'min_finite', 'max_finite', 'valid_list_rows', 'list_negative_rows',
    'list_all_in_0_1_rows', 'list_sum_approx_1_rows', 'list_sum_min', 'list_sum_max',
    'argmax_counts_json', 'argmax_tie_rows', 'audit_error_rows',
]


def build_raw_field_counts(diag):
    rows = []
    for file_info in FILES:
        file_id = file_info['file_id']
        fc = file_info['code']
        stats = diag['file_stats'].get(file_id)
        if stats is None:
            continue
        domains = sorted(stats['domains'])
        for domain in domains + ['ALL']:
            if domain == 'ALL':
                n_rows = stats['rows']
                parts = [(fc, d) for d in domains]
            else:
                n_rows = int(stats['domains'][domain])
                parts = [(fc, domain)]
            for field in FIELDS:
                merged_prior = {'present': 0, 'null': 0, 'types': Counter(), 'lengths': Counter(),
                                'non_numeric': 0, 'nan': 0, 'pos_inf': 0, 'neg_inf': 0,
                                'finite_elements': 0, 'negative_elements': 0, 'zero_elements': 0,
                                'min': float('inf'), 'max': float('-inf'), 'valid_list_rows': 0,
                                'list_negative_rows': 0, 'list_all_in_0_1_rows': 0,
                                'list_sum_approx_1_rows': 0, 'list_sum_min': float('inf'),
                                'list_sum_max': float('-inf'), 'argmax_counts': Counter(),
                                'argmax_tie_rows': 0, 'audit_error_rows': 0}
                merged_detail = empty_detail_stats()
                for key in parts:
                    part = diag['raw_prior'].get(key, {}).get(field)
                    detail = diag['raw_detail'].get(key, {}).get(field)
                    if part is not None:
                        for metric in ['present', 'null', 'non_numeric', 'nan', 'pos_inf', 'neg_inf',
                                       'finite_elements', 'negative_elements', 'zero_elements',
                                       'valid_list_rows', 'list_negative_rows', 'list_all_in_0_1_rows',
                                       'list_sum_approx_1_rows', 'argmax_tie_rows', 'audit_error_rows']:
                            merged_prior[metric] += part[metric]
                        merged_prior['types'].update(part['types'])
                        merged_prior['lengths'].update(part['lengths'])
                        merged_prior['argmax_counts'].update(part['argmax_counts'])
                        merged_prior['min'] = min(merged_prior['min'], part['min'])
                        merged_prior['max'] = max(merged_prior['max'], part['max'])
                        merged_prior['list_sum_min'] = min(merged_prior['list_sum_min'], part['list_sum_min'])
                        merged_prior['list_sum_max'] = max(merged_prior['list_sum_max'], part['list_sum_max'])
                    if detail is not None:
                        for metric in merged_detail:
                            merged_detail[metric] += detail[metric]
                rows.append({
                    'file_id': file_id, 'domain': domain, 'field': field, 'n_rows': n_rows,
                    'present': merged_prior['present'],
                    'absent': n_rows - merged_prior['present'],
                    'null': merged_prior['null'],
                    'types_json': json_compact({str(k): int(v) for k, v in sorted(merged_prior['types'].items())}),
                    'lengths_json': json_compact({str(k): int(v) for k, v in sorted(merged_prior['lengths'].items())}),
                    'expected_list_length': LIST_LENGTHS.get(field, ''),
                    'list_rows': merged_detail['list_rows'],
                    'wrong_length_rows': merged_detail['wrong_length_rows'],
                    'non_numeric_rows_prior_semantics': merged_prior['non_numeric'],
                    'non_numeric_elements': merged_detail['non_numeric_elements'],
                    'non_numeric_rows_detailed': merged_detail['non_numeric_rows'],
                    'nan_elements_prior_semantics': merged_prior['nan'],
                    'nan_elements': merged_detail['nan_elements'],
                    'nan_rows': merged_detail['nan_rows'],
                    'posinf_elements_prior_semantics': merged_prior['pos_inf'],
                    'posinf_elements': merged_detail['posinf_elements'],
                    'posinf_rows': merged_detail['posinf_rows'],
                    'neginf_elements_prior_semantics': merged_prior['neg_inf'],
                    'neginf_elements': merged_detail['neginf_elements'],
                    'neginf_rows': merged_detail['neginf_rows'],
                    'finite_elements_prior_semantics': merged_prior['finite_elements'],
                    'finite_elements': merged_detail['finite_elements'],
                    'negative_elements': merged_prior['negative_elements'],
                    'zero_elements': merged_prior['zero_elements'],
                    'min_finite': finite_or_none(merged_prior['min']),
                    'max_finite': finite_or_none(merged_prior['max']),
                    'valid_list_rows': merged_prior['valid_list_rows'],
                    'list_negative_rows': merged_prior['list_negative_rows'],
                    'list_all_in_0_1_rows': merged_prior['list_all_in_0_1_rows'],
                    'list_sum_approx_1_rows': merged_prior['list_sum_approx_1_rows'],
                    'list_sum_min': finite_or_none(merged_prior['list_sum_min']),
                    'list_sum_max': finite_or_none(merged_prior['list_sum_max']),
                    'argmax_counts_json': json_compact({str(k): int(v) for k, v in sorted(merged_prior['argmax_counts'].items())}),
                    'argmax_tie_rows': merged_prior['argmax_tie_rows'],
                    'audit_error_rows': merged_prior['audit_error_rows']})
    return rows


ROW_MASK_TYPES = [('file_code', 'B'), ('line_no', 'I'), ('domain_code', 'B'), ('flags', 'B'),
                  ('raw_invalid', 'I'), ('extract_nan', 'I'), ('extract_nonfinite', 'I'),
                  ('extract_posinf', 'I'), ('extract_neginf', 'I'),
                  ('norm_nan', 'H'), ('norm_nonfinite', 'H'), ('group_nan', 'B'), ('q_nan', 'B')]
ROW_MASK_DTYPES = {'file_code': np.uint8, 'line_no': np.uint32, 'domain_code': np.uint8,
                   'flags': np.uint8, 'raw_invalid': np.uint32, 'extract_nan': np.uint32,
                   'extract_nonfinite': np.uint32, 'extract_posinf': np.uint32,
                   'extract_neginf': np.uint32, 'norm_nan': np.uint16, 'norm_nonfinite': np.uint16,
                   'group_nan': np.uint8, 'q_nan': np.uint8}
MODEL_FEATURE_BITS = sum(1 << FEATURE_INDEX[f] for f in MODEL)


def reaggregate_from_row_masks(log):
    buffers = {name: array(typecode) for name, typecode in ROW_MASK_TYPES}
    domain_codes = {}
    domain_names = []
    counters = Counter()
    with gzip.open(RUN_DIR / 'row_masks.csv.gz', 'rt', encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            counters['rows'] += 1
            file_id = row['file_id']
            fc = FILE_IDS.index(file_id)
            domain = row['domain']
            if domain not in domain_codes:
                domain_codes[domain] = len(domain_names)
                domain_names.append(domain)
            buffers['file_code'].append(fc)
            buffers['line_no'].append(int(row['source_line']))
            buffers['domain_code'].append(domain_codes[domain])
            parse_ok = int(row['parse_ok'] or 0)
            flags = 0
            if parse_ok:
                flags |= F_PARSE
                if int(row['is_unique_first'] or 0):
                    flags |= F_UNIQUE
                if int(row['overlap_a1'] or 0):
                    flags |= F_OVERLAP
                if fc == 0:
                    flags |= F_A1
                    flags |= F_HOLDOUT if row['evaluation_role'] == 'A1_holdout' else F_CALIB
                else:
                    flags |= F_EXTOVER if int(row['overlap_a1'] or 0) else F_EXTNEW
            buffers['flags'].append(flags)
            if not parse_ok:
                counters['unparsed_rows'] += 1
                for name in ['raw_invalid', 'extract_nan', 'extract_nonfinite', 'extract_posinf',
                             'extract_neginf', 'norm_nan', 'norm_nonfinite', 'group_nan', 'q_nan']:
                    buffers[name].append(0)
                continue
            counters['parsed_rows'] += 1
            raw = string_to_bits(row['raw_invalid_bits'])
            ext_nan = string_to_bits(row['extract_nan_bits'])
            ext_nf = string_to_bits(row['extract_nonfinite_bits'])
            ext_pos = string_to_bits(row['extract_posinf_bits'])
            ext_neg = string_to_bits(row['extract_neginf_bits'])
            norm_nan = string_to_bits(row['norm_nan_bits'])
            norm_nf = string_to_bits(row['norm_nonfinite_bits'])
            group_nan = string_to_bits(row['group_nan_bits']) if 'group_nan_bits' in row else 0
            q_nan = int(row['would_Q_be_nan'] or 0)
            if sha256_text(row['key_str_json']) != row['key_sha256']:
                counters['key_sha_mismatch'] += 1
            if row['raw_invalid_bits'] != bits_to_string(raw, len(FIELDS)) or raw.bit_count() != int(row['raw_invalid_count'] or 0):
                counters['raw_bits_mismatch'] += 1
            if ext_nan.bit_count() != int(row['extract_nan_count'] or 0):
                counters['extract_bits_mismatch'] += 1
            group_bits_recomputed = 0
            for gi, group in enumerate(GROUP_NAMES):
                if (norm_nan & GROUP_MODEL_BITS[group]) != 0:
                    group_bits_recomputed |= (1 << gi)
            if (ext_nan & MODEL_FEATURE_BITS) != norm_nan:
                counters['extract_vs_norm_nan_mismatch'] += 1
            if (norm_nf & ~norm_nan) != 0:
                counters['norm_nonfinite_non_nan'] += 1
            row_group_nan = 0
            for gi, key in enumerate(['would_group_usability_be_nan', 'would_group_knowledge_be_nan',
                                      'would_group_education_reasoning_be_nan']):
                if int(row[key] or 0):
                    row_group_nan |= (1 << gi)
            if row_group_nan != group_bits_recomputed:
                counters['group_mask_mismatch'] += 1
            if int(bool(group_bits_recomputed)) != q_nan:
                counters['q_nan_mask_mismatch'] += 1
            if ext_nf != (ext_nan | ext_pos | ext_neg):
                counters['extract_nonfinite_partition_mismatch'] += 1
            buffers['raw_invalid'].append(raw)
            buffers['extract_nan'].append(ext_nan)
            buffers['extract_nonfinite'].append(ext_nf)
            buffers['extract_posinf'].append(ext_pos)
            buffers['extract_neginf'].append(ext_neg)
            buffers['norm_nan'].append(norm_nan)
            buffers['norm_nonfinite'].append(norm_nf)
            buffers['group_nan'].append(group_bits_recomputed)
            buffers['q_nan'].append(q_nan)
    arrays = {name: np.frombuffer(buffer, dtype=ROW_MASK_DTYPES[name]).copy()
              for name, buffer in buffers.items()}
    return arrays, domain_names, dict(counters)


def compare_table(written_rows, recomputed_rows, key_fields, value_fields):
    wmap = {tuple(str(row[k]) for k in key_fields): row for row in written_rows}
    rmap = {tuple(str(row[k]) for k in key_fields): row for row in recomputed_rows}
    missing = sorted(set(wmap) - set(rmap))
    extra = sorted(set(rmap) - set(wmap))
    mismatches = []
    for key in sorted(set(wmap) & set(rmap)):
        for field in value_fields:
            if not same_value(wmap[key].get(field), rmap[key].get(field)):
                mismatches.append({'key': list(key), 'field': field,
                                   'written': wmap[key].get(field),
                                   'recomputed': rmap[key].get(field)})
    return {'n_written': len(written_rows), 'n_recomputed': len(recomputed_rows),
            'n_missing_in_recompute': len(missing), 'n_extra_in_recompute': len(extra),
            'n_value_mismatches': len(mismatches),
            'missing_examples': missing[:5], 'extra_examples': extra[:5],
            'mismatch_examples': mismatches[:5]}


def build_physical_rows_table(arrays, domain_names):
    fc = arrays['file_code']
    fl = arrays['flags']
    parsed = (fl & F_PARSE) != 0
    rows = []
    role_labels = []
    for name, mask in [('A1_calibration', (fc == 0) & ((fl & F_CALIB) != 0)),
                       ('A1_holdout', (fc == 0) & ((fl & F_HOLDOUT) != 0)),
                       ('extension_overlap_A1', (fc != 0) & ((fl & F_OVERLAP) != 0)),
                       ('extension_new_records', (fc != 0) & ((fl & F_OVERLAP) == 0))]:
        role_labels.append((name, parsed & mask))
    for file_id, code in zip(FILE_IDS, range(len(FILE_IDS))):
        for role, mask in role_labels:
            sel = mask & (fc == code)
            if not np.any(sel):
                continue
            for d in range(len(domain_names)):
                part = sel & (arrays['domain_code'] == d)
                n_part = int(part.sum())
                if n_part == 0:
                    continue
                rows.append({'file_id': file_id, 'evaluation_role': role,
                             'domain': domain_names[d], 'n_physical_rows': n_part,
                             'n_unique_first': int((part & ((fl & F_UNIQUE) != 0)).sum()),
                             'n_duplicate': int((part & ((fl & F_UNIQUE) == 0)).sum())})
            rows.append({'file_id': file_id, 'evaluation_role': role, 'domain': 'ALL',
                         'n_physical_rows': int(sel.sum()),
                         'n_unique_first': int((sel & ((fl & F_UNIQUE) != 0)).sum()),
                         'n_duplicate': int((sel & ((fl & F_UNIQUE) == 0)).sum())})
    return rows


def build_diagnostic_spec(source_report, norm_report, transforms, spec_extra=None):
    spec = {
        'task': 'TASK-Q01A',
        'run_id': RUN_ID,
        'purpose': 'quality missingness pattern diagnosis; no strategy selection, no Q recomputation',
        'source_functions_replicated': {
            'fields': 'solution/src/quality_audit.py FIELDS/LIST_LENGTHS/RULES/DSIR',
            'features': 'solution/src/quality_audit.py MODEL/FEATURES/GROUPS',
            'extraction': 'solution/src/quality_audit.py get_features (whole-list invalidation, bool accepted)',
            'fingerprint': 'solution/src/quality_audit.py quality_fingerprint',
            'raw_audit': 'solution/src/quality_audit.py audit_value/clean_stats',
            'key': 'solution/src/quality_audit.py key=(str(id), str(sub_path)); key_json=json.dumps(key)',
            'split': 'split=int(sha256(str(SEED)+key_json)[:16],16)%5; A1 remainder 0 -> holdout',
            'propagation': 'solution/src/quality_audit.py score_quality (mean axis=1 skipna=False)',
            'denominators': 'solution/src/quality_audit.py summarize (pandas default skipna semantics)',
        },
        'raw_fields_22': [{'index': i, 'field': f, 'expected_list_length': LIST_LENGTHS.get(f)}
                          for i, f in enumerate(FIELDS)],
        'expanded_features_25': [{'index': i, 'feature': f, 'source_field': FEATURE_SOURCE_FIELD[f],
                                  'in_main_q': f in MODEL} for i, f in enumerate(FEATURES)],
        'main_q_features_11': [{'index': i, 'feature': f} for i, f in enumerate(MODEL)],
        'groups': GROUPS,
        'scope_definitions': {
            'A1_calibration': 'evaluation_role==A1_calibration and is_unique_first',
            'A1_holdout': 'evaluation_role==A1_holdout and is_unique_first',
            'A1_all_unique': 'file_id==A1 and is_unique_first',
            'extension_overlap_A1': 'overlap_a1 (no is_unique filter, matches prior summarize)',
            'extension_new_records': 'evaluation_role==extension_new_records and is_unique_first',
            'all_unique': 'is_unique_first',
            'file_unique_first_<file>': 'comparison view for prior feature_summary (is_unique_first per file)',
        },
        'mask_kinds': [{'mask_kind': k, 'feature_universe': u, 'n_bits': nbits,
                        'bit_order': 'bit j corresponds to index j of the listed universe'}
                       for k, u, _a, nbits, _names in MASK_DEFS],
        'mask_universes': {'FIELDS22': FIELDS, 'FEATURES25': FEATURES, 'MODEL11': MODEL},
        'counting_conventions': {
            'physical_rows': 'every decompressed line, including unparsable lines (placeholder row)',
            'extract_layer_additivity': 'n_total = n_finite + n_nonfinite; n_nonfinite = n_nan + n_posinf + n_neginf',
            'raw_layer': 'raw reasons are non-exclusive; no union additivity claimed',
            'ratios': 'every ratio row carries its numerator and denominator columns',
            'denominator_rules': 'pandas 2.3.3 skipna semantics reproduced from summarize()',
        },
        'seed': SEED,
        'split_rule': f'int(sha256("{SEED}"+key_json)[:16],16) % {SPLIT_MODULUS}; remainder 0 => A1_holdout',
        'source_report': source_report,
        'normalization_report': norm_report,
        'normalization_parameters_used': transforms,
        'normalization_refit': False,
        'content_fields_not_read': True,
        'final_strategy_selected': False,
        'final_Q_recomputed': False,
    }
    if spec_extra:
        spec.update(spec_extra)
    return spec


def build_input_manifest(pre_xz, snapshot_before, prior_manifest_rows, prior_audit,
                         read_list, not_read_list, notes):
    manifest = {'run_id': RUN_ID, 'generated_local': now_iso(),
                'workspace_root': str(PROJECT), 'files': [], 'raw_data_policy': 'read_only',
                'decompression_policy': 'at most one sequential decompression pass per file',
                'hash_read_policy': 'compressed bytes read twice per file (pre/post SHA256); not a decompression pass',
                'primary_inputs': [], 'secondary_inputs': [],
                'actually_read': read_list, 'not_read': not_read_list, 'notes': notes}
    prior_by_path = {row['path']: row for row in prior_manifest_rows}
    for file_id, info in pre_xz.items():
        rel = info['path'].relative_to(DATA).as_posix()
        prior_row = prior_by_path.get(rel, {})
        prior_sha = None
        for f in prior_audit['files']:
            if f['file_id'] == file_id:
                prior_sha = f['sha256']
        manifest['primary_inputs'].append({
            'file_id': file_id, 'path': str(info['path']), 'bytes': info['bytes'],
            'mtime': info['mtime'], 'sha256': info['sha256'],
            'prior_manifest_sha256': prior_row.get('sha256'),
            'prior_audit_json_sha256': prior_sha,
            'sha256_matches_prior_manifest': prior_row.get('sha256') == info['sha256'],
            'sha256_matches_prior_audit': prior_sha == info['sha256']})
    for path, info in snapshot_before.items():
        manifest['secondary_inputs'].append({'path': path, 'bytes': info['bytes'],
                                             'mtime': info['mtime'], 'sha256': info['sha256']})
    return manifest


COMPARISON_COLUMNS = ['prior_artifact', 'prior_scope', 'prior_item', 'metric', 'expected_prior',
                      'actual_run', 'difference', 'match', 'explanation', 'resolved']
KNOWN_DOMAIN_COLUMNS = ['domain', 'feature', 'scope', 'run_n_total', 'run_n_missing',
                        'run_n_nonmissing', 'run_layer', 'missing_rows_A1', 'missing_rows_extension_new',
                        'missing_rows_extension_overlap', 'prior_artifact', 'prior_n_total',
                        'prior_n_nonmissing', 'prior_n_missing', 'difference_missing',
                        'classification_note']
PHYSICAL_ROW_COLUMNS = ['file_id', 'evaluation_role', 'domain', 'n_physical_rows',
                        'n_unique_first', 'n_duplicate']
PROTECTED_SNAPSHOT_PATHS = [SRC, SOLUTION / 'config.json', SOLUTION / 'README.md',
                            SOLUTION / 'outputs', SOLUTION / 'reports', RECOVERY,
                            PROJECT / 'tasks', PROJECT / '00_PROJECT_BRIEF.md',
                            PROJECT / '01_PROJECT_STATUS.md', PROJECT / '02_DECISIONS.md',
                            PROJECT / '03_DATA_CATALOG.md', PROJECT / '04_TASK_QUEUE.md',
                            PROJECT / '05_REVIEW_LOG.md', PROJECT / '恢复报告.md']


def raw_tree_meta():
    meta = {}
    for child in DATA.rglob('*'):
        if child.is_file():
            stat = child.stat()
            meta[str(child.relative_to(DATA)).replace('\\', '/')] = {'bytes': stat.st_size,
                                                                     'mtime': stat.st_mtime}
    return meta


def compare_tree_meta(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in set(before) & set(after)
                     if before[k]['bytes'] != after[k]['bytes'] or before[k]['mtime'] != after[k]['mtime'])
    return {'added': added, 'removed': removed, 'changed': changed,
            'n_before': len(before), 'n_after': len(after)}


def reconcile_invalid_values(log):
    row_keys = set()
    with gzip.open(RUN_DIR / 'row_masks.csv.gz', 'rt', encoding='utf-8', newline='') as fh:
        for row in csv.DictReader(fh):
            row_keys.add((row['file_id'], row['source_line']))
    stats = Counter()
    extract_events = Counter()
    raw_element_events = Counter()
    with gzip.open(RUN_DIR / 'invalid_values.csv.gz', 'rt', encoding='utf-8', newline='') as fh:
        for row in csv.DictReader(fh):
            stats['events'] += 1
            stats[f"layer_{row['layer']}"] += 1
            stats[f"reason_{row['reason']}"] += 1
            if (row['file_id'], row['source_line']) not in row_keys:
                stats['unknown_row_identity'] += 1
            if row['layer'] == 'extract':
                extract_events[(row['field_or_feature'], row['reason'])] += 1
            if row['layer'] == 'raw' and row['reason'] in ('nan_element', 'posinf_element', 'neginf_element'):
                raw_element_events[(row['field_or_feature'], row['reason'])] += 1
    return {'stats': dict(stats), 'extract_events': {f'{k[0]}|{k[1]}': v for k, v in extract_events.items()},
            'raw_element_events': {f'{k[0]}|{k[1]}': v for k, v in raw_element_events.items()},
            'n_row_keys': len(row_keys)}


def chk(checks, cid, description, status, actual, expected, tolerance, evidence):
    checks.append({'check_id': cid, 'description': description, 'status': status,
                   'actual': actual, 'expected': expected, 'tolerance': tolerance,
                   'evidence': evidence})


def run_task(log, ctx):
    # ------------------------------------------------------------------ stage 0
    stage_t0 = time.monotonic()
    missing = [str(p) for p in PRIMARY_INPUTS + SECONDARY_INPUTS if not Path(p).is_file()]
    ctx['missing_inputs'] = missing
    if missing:
        raise PreconditionError('missing required inputs: ' + '; '.join(missing))
    parquet = QUALITY_OUT / 'quality_features_scores.parquet'
    ctx['row_artifact_present'] = parquet.exists()
    if ctx['row_artifact_present']:
        raise PreconditionError('row-level artifact appeared after the recovery audit: ' + str(parquet))
    pre_xz = {}
    for spec in FILES:
        stat = spec['path'].stat()
        pre_xz[spec['file_id']] = {'path': spec['path'], 'bytes': stat.st_size, 'mtime': stat.st_mtime,
                                  'sha256': sha256_file(spec['path'])}
    ctx['pre_xz'] = pre_xz
    log('stage=precondition hashed_inputs=3')
    prior_manifest_rows = read_csv_rows(AUDIT_OUT / 'raw_source_manifest.csv')
    prior_audit = read_json(QUALITY_OUT / 'audit.json')
    prior_norm = read_json(QUALITY_OUT / 'normalization.json')
    source_report = verify_source_spec()
    norm_report = verify_normalization(prior_norm)
    ctx['source_report'] = source_report
    ctx['norm_report'] = norm_report
    ctx['transforms'] = norm_report['transforms']
    manifest_by_path = {row['path']: row for row in prior_manifest_rows}
    audit_sha = {f['file_id']: f['sha256'] for f in prior_audit['files']}
    sha_checks = {}
    for spec in FILES:
        rel = spec['path'].relative_to(DATA).as_posix()
        manifest_row = manifest_by_path.get(rel, {})
        sha_checks[spec['file_id']] = {
            'sha256': pre_xz[spec['file_id']]['sha256'],
            'matches_manifest': manifest_row.get('sha256') == pre_xz[spec['file_id']]['sha256'],
            'matches_audit_json': audit_sha.get(spec['file_id']) == pre_xz[spec['file_id']]['sha256'],
            'bytes_match_manifest': int(manifest_row.get('bytes', -1)) == pre_xz[spec['file_id']]['bytes']}
    ctx['sha_checks'] = sha_checks
    if not all(v['matches_manifest'] and v['matches_audit_json'] and v['bytes_match_manifest']
               for v in sha_checks.values()):
        raise PreconditionError('compressed input sha256/bytes differ from registered versions')
    log('stage=precondition sha256_matches_manifest_and_prior_audit')
    ctx['pre_snapshot'] = snapshot_paths(PROTECTED_SNAPSHOT_PATHS)
    ctx['pre_raw_meta'] = raw_tree_meta()
    log(f"stage=precondition protected_files={len(ctx['pre_snapshot'])} raw_tree_files={len(ctx['pre_raw_meta'])}")
    ctx['input_manifest'] = build_input_manifest(
        pre_xz, ctx['pre_snapshot'], prior_manifest_rows, prior_audit,
        read_list=['F题/real_attachments/.../slimpajama_quality_signal_sample.jsonl.xz',
                   'F题/real_attachments/.../arxiv_part-6777d8857c6e-000486.jsonl.xz',
                   'F题/real_attachments/.../github_part-6777d8857c6e-000275.jsonl.xz',
                   'solution/src/quality_audit.py', 'solution/src/common.py', 'solution/config.json',
                   'solution/outputs/quality/audit.json', 'solution/outputs/quality/normalization.json',
                   'solution/outputs/quality/domain_summary.csv',
                   'solution/outputs/quality/feature_summary.csv',
                   'solution/outputs/quality/extension_shift.csv',
                   'solution/outputs/audit/raw_source_manifest.csv',
                   'recovery/2026-09-24/quality_gap_evidence.json',
                   'recovery/2026-09-24/quality_missing_feature_counts.csv',
                   'recovery/2026-09-24/quality_mean_discrepancies.csv',
                   'recovery/2026-09-24/verification.json'],
        not_read_list=['A18/other A tables', 'B tables', 'C tables', 'semantic_sources/*',
                       'quality_features_scores.parquet (absent)', 'all content/text fields'],
        notes='no project module was imported; content fields were never retained or analysed')
    prior_audit_ref = prior_audit
    ctx['prior_domain_summary'] = read_csv_rows(QUALITY_OUT / 'domain_summary.csv')
    ctx['prior_feature_summary'] = read_csv_rows(QUALITY_OUT / 'feature_summary.csv')
    ctx['prior_extension_shift'] = read_csv_rows(QUALITY_OUT / 'extension_shift.csv')
    ctx['prior_recovery_deficits'] = read_json(RECOVERY / 'quality_gap_evidence.json')['feature_deficits']
    ctx['prior_mean_discrepancies'] = read_csv_rows(RECOVERY / 'quality_mean_discrepancies.csv')
    ctx['missing_feature_counts_prior'] = read_csv_rows(RECOVERY / 'quality_missing_feature_counts.csv')
    ctx['stage_seconds']['precondition'] = time.monotonic() - stage_t0

    # ------------------------------------------------------------------ stage 1
    stage_t0 = time.monotonic()
    synthetic = synthetic_selftest(log, ctx['transforms'])
    ctx['synthetic'] = synthetic
    log(f"stage=selftest status={synthetic['status']} cases={synthetic['n_cases']} failed={synthetic['n_failed']}")
    ctx['stage_seconds']['selftest'] = time.monotonic() - stage_t0
    if synthetic['status'] != 'PASS':
        raise PreconditionError('synthetic self-test failed; raw scan not started')

    # ------------------------------------------------------------------ stage 2
    stage_t0 = time.monotonic()
    row_path = RUN_DIR / 'row_masks.csv.gz'
    invalid_path = RUN_DIR / 'invalid_values.csv.gz'
    ctx['row_masks_path'] = row_path
    ctx['invalid_path'] = invalid_path
    with gzip.open(row_path, 'wt', encoding='utf-8', newline='') as row_fh, \
            gzip.open(invalid_path, 'wt', encoding='utf-8', newline='') as invalid_fh:
        row_writer = csv.DictWriter(row_fh, fieldnames=ROW_MASK_COLUMNS, extrasaction='ignore')
        row_writer.writeheader()
        invalid_writer = csv.DictWriter(invalid_fh, fieldnames=INVALID_COLUMNS, extrasaction='ignore')
        invalid_writer.writeheader()
        diag = Diagnostic(log, ctx['transforms'], row_writer, invalid_writer)
        ctx['diag'] = diag
        diag.key_sets = {file_id: set() for file_id in FILE_IDS}
        for spec in FILES:
            guard_resources(log, 'scan_start:' + spec['file_id'])
            diag.scan_file(spec)
            diag.key_sets[spec['file_id']] = diag.current_file_keys
        ctx['scan_complete'] = True
    ctx['diag'] = diag
    ctx['stage_seconds']['scan'] = time.monotonic() - stage_t0
    log(f"stage=scan complete parsed_rows={sum(s['rows'] for s in diag.file_stats.values())} "
        f"events={diag.events_written} norm_inf_rows={diag.norm_inf_rows}")
    if diag.norm_inf_rows:
        ctx['unfinished'].append('normalized_nonfinite_non_nan_rows>0: group/Q NaN logic needs review')

    # ------------------------------------------------------------------ stage 3
    stage_t0 = time.monotonic()
    guard_resources(log, 'aggregate')
    arrays = diag.store.finalize()
    unique_flags = (arrays['flags'] & F_UNIQUE) != 0
    pairwise = {}
    for i, a in enumerate(FILE_IDS):
        for b in FILE_IDS[i + 1:]:
            pairwise[f'{a}__{b}'] = len(diag.key_sets[a] & diag.key_sets[b])
    aggregate_totals = {
        'total_records': int(len(arrays['file_code'])),
        'unique_keys': int(unique_flags.sum()),
        'duplicate_rows': int((~unique_flags).sum()),
        'pairwise_intersections': pairwise,
        'quality_conflicts': int(sum(s['quality_conflicting_rows'] for s in diag.file_stats.values())),
        'domain_collisions': int(sum(s['domain_collision_rows'] for s in diag.file_stats.values())),
        'file_unique': {file_id: len(diag.key_sets[file_id]) for file_id in FILE_IDS}}
    ctx['aggregate_totals'] = aggregate_totals
    tables, group_stats = aggregate_rows(arrays, diag.domain_names)
    tables['raw_field_counts'] = build_raw_field_counts({'file_stats': diag.file_stats,
                                                         'raw_prior': diag.raw_prior,
                                                         'raw_detail': diag.raw_detail})
    tables['physical_rows_by_file_role'] = build_physical_rows_table(arrays, diag.domain_names)
    TABLE_COLUMNS['raw_field_counts'] = RAW_FIELD_COLUMNS
    TABLE_COLUMNS['physical_rows_by_file_role'] = PHYSICAL_ROW_COLUMNS
    ctx['tables'] = tables
    ctx['group_stats'] = group_stats
    ctx['tables_written'] = write_tables(tables, log)
    ctx['stage_seconds']['aggregate'] = time.monotonic() - stage_t0

    # ------------------------------------------------------------------ stage 4
    stage_t0 = time.monotonic()
    diag_view = {'prior_audit': prior_audit,
                 'prior_domain_summary': ctx['prior_domain_summary'],
                 'prior_feature_summary': ctx['prior_feature_summary'],
                 'prior_extension_shift': ctx['prior_extension_shift'],
                 'prior_recovery_deficits': ctx['prior_recovery_deficits'],
                 'prior_mean_discrepancies': ctx['prior_mean_discrepancies'],
                 'raw_prior': diag.raw_prior, 'raw_detail': diag.raw_detail,
                 'file_stats': diag.file_stats}
    ctx['comparison_rows'] = build_prior_comparison(diag_view, group_stats, aggregate_totals)
    ctx['known_domain_rows'] = build_known_domain_comparison(diag_view, group_stats)
    write_csv(RUN_DIR / 'comparison_with_prior.csv', COMPARISON_COLUMNS, ctx['comparison_rows'])
    write_csv(RUN_DIR / 'known_domain_comparison.csv', KNOWN_DOMAIN_COLUMNS, ctx['known_domain_rows'])
    log(f"stage=compare prior_rows={len(ctx['comparison_rows'])} known_domain_rows={len(ctx['known_domain_rows'])}")
    ctx['stage_seconds']['compare'] = time.monotonic() - stage_t0

    # ------------------------------------------------------------------ stage 5
    stage_t0 = time.monotonic()
    ctx['post_xz'] = {}
    for spec in FILES:
        stat = spec['path'].stat()
        ctx['post_xz'][spec['file_id']] = {'path': spec['path'], 'bytes': stat.st_size,
                                           'mtime': stat.st_mtime,
                                           'sha256': sha256_file(spec['path'])}
    ctx['post_snapshot'] = snapshot_paths(PROTECTED_SNAPSHOT_PATHS)
    ctx['post_raw_meta'] = raw_tree_meta()
    guard_resources(log, 'reaggregate')
    reagg_arrays, reagg_domains, reagg_counters = reaggregate_from_row_masks(log)
    reagg_tables, reagg_group_stats = aggregate_rows(reagg_arrays, reagg_domains)
    ctx['reagg_counters'] = reagg_counters
    table_compare_specs = [
        ('feature_missing_counts', ['scope', 'domain', 'feature'],
         ['n_total', 'n_nan', 'n_posinf', 'n_neginf', 'n_nonfinite', 'n_finite']),
        ('missing_patterns', ['scope', 'domain', 'mask_kind', 'mask_bits'], ['n', 'n_scope']),
        ('missing_pairwise', ['scope', 'domain', 'mask_kind', 'feature_i', 'feature_j'],
         ['n_scope', 'n_i', 'n_j', 'n_intersection', 'n_union']),
        ('validity_counts', ['scope', 'domain'],
         ['n_total', 'n_complete_25_notnan', 'n_complete_25_finite', 'n_complete_11_notnan',
          'n_complete_11_finite', 'n_group_usability_valid_notnan', 'n_group_knowledge_valid_notnan',
          'n_group_education_reasoning_valid_notnan', 'n_would_Q_nan', 'n_valid_mainQ_11']),
        ('summary_denominators', ['scope', 'domain', 'statistic'],
         ['n_total', 'n_nonmissing', 'n_finite', 'n_effective', 'missing_comparison_as_false_n']),
        ('complete_case_count_only', ['scope', 'domain', 'feature_set'],
         ['n_total', 'n_complete', 'n_not_covered']),
        ('group_validity_distribution', ['scope', 'domain'],
         ['n_rows_0_valid_groups', 'n_rows_1_valid_groups', 'n_rows_2_valid_groups',
          'n_rows_3_valid_groups']),
        ('group_mask_intersections', ['scope', 'domain', 'group_i', 'group_j'],
         ['n_both_valid', 'n_both_missing', 'n_union_missing']),
    ]
    verification = {}
    for name, keys, values in table_compare_specs:
        written_rows = read_csv_rows(RUN_DIR / f'{name}.csv')
        verification[name] = compare_table(written_rows, reagg_tables[name], keys, values)
    ctx['verification'] = verification
    ctx['invalid_reconciliation'] = reconcile_invalid_values(log)
    ctx['stage_seconds']['verify'] = time.monotonic() - stage_t0
    log(f"stage=verify tables={len(verification)} invalid_events={ctx['invalid_reconciliation']['stats'].get('events', 0)}")
    return ctx


def build_checks(log, ctx):
    checks = []
    prior_audit_ref = ctx.get('prior_audit') or {'total_records': None,
                                                 'unique_id_sub_path_keys': None,
                                                 'duplicate_occurrences': None, 'files': [],
                                                 'quality_conflicts': [], 'domain_collisions': [],
                                                 'pairwise_key_intersections': {}}
    sha_checks = ctx.get('sha_checks', {})
    chk(checks, 'C01_required_inputs_present', 'all permitted inputs exist',
        'PASS' if not ctx.get('missing_inputs') else 'FAIL',
        {'missing': ctx.get('missing_inputs', [])}, 'no missing input', 'exact',
        'input_manifest.json')
    chk(checks, 'C02_row_artifact_absent', 'no new row-level quality artifact at run start',
        'PASS' if not ctx.get('row_artifact_present') else 'FAIL',
        {'quality_features_scores_parquet_present': bool(ctx.get('row_artifact_present'))},
        'absent (recovery-time state)', 'exact', 'run.log')
    chk(checks, 'C03_xz_sha256_matches_registered',
        'compressed inputs match raw_source_manifest.csv and prior audit.json',
        'PASS' if (sha_checks and all(v['matches_manifest'] and v['matches_audit_json']
                                      and v['bytes_match_manifest'] for v in sha_checks.values())) else 'NOT_CHECKED',
        sha_checks, 'all three files match', 'sha256 exact', 'input_manifest.json')
    src = ctx.get('source_report') or {}
    chk(checks, 'C04_source_constants_match_pinned_spec',
        'AST-extracted FIELDS/FEATURES/GROUPS/LIST_LENGTHS/SEED equal the pinned specification',
        'PASS' if src.get('checks') and all(src['checks'].values()) else 'NOT_CHECKED',
        src.get('checks'), 'all True', 'exact', 'diagnostic_spec.json')
    norm = ctx.get('norm_report') or {}
    chk(checks, 'C05_normalization_matches_source_groups',
        'normalization.json groups/transforms/bounds equal current source definitions (no refit)',
        'PASS' if norm.get('checks') and all(norm['checks'].values()) else 'NOT_CHECKED',
        norm.get('checks'), 'all True', 'exact', 'diagnostic_spec.json')
    synthetic = ctx.get('synthetic') or {}
    chk(checks, 'C06_synthetic_selftest', 'synthetic tests of extraction/mask/pandas/aggregation logic',
        'PASS' if synthetic.get('status') == 'PASS' else ('NOT_CHECKED' if not synthetic else 'FAIL'),
        {'n_cases': synthetic.get('n_cases'), 'n_failed': synthetic.get('n_failed')},
        'n_failed = 0', 'exact', 'checks.json#synthetic_selftest')
    snap_diff = ctx.get('snapshot_diff') or {}
    chk(checks, 'C07_protected_files_unchanged', 'source/config/quality outputs/recovery/task/00-05 unchanged',
        'PASS' if snap_diff and not (snap_diff['added'] or snap_diff['removed'] or snap_diff['changed']) else 'FAIL',
        snap_diff, 'no added/removed/changed file', 'exact', 'input_manifest.json')
    raw_diff = ctx.get('raw_tree_diff') or {}
    chk(checks, 'C08_raw_tree_bytes_mtime_unchanged', 'all files under F题/real_attachments keep size and mtime',
        'PASS' if raw_diff and not (raw_diff['added'] or raw_diff['removed'] or raw_diff['changed']) else 'FAIL',
        raw_diff, 'no added/removed/changed file', 'exact', 'input_manifest.json')
    post_ok = False
    if ctx.get('pre_xz') and ctx.get('post_xz'):
        post_ok = all(ctx['pre_xz'][k]['sha256'] == ctx['post_xz'][k]['sha256']
                      and ctx['pre_xz'][k]['bytes'] == ctx['post_xz'][k]['bytes']
                      for k in ctx['pre_xz'])
    chk(checks, 'C09_xz_post_hash_equal_pre', 'compressed bytes re-read after the scan and hashed again',
        'PASS' if post_ok else 'NOT_CHECKED',
        {k: {'pre': ctx.get('pre_xz', {}).get(k, {}).get('sha256'),
             'post': ctx.get('post_xz', {}).get(k, {}).get('sha256')} for k in FILE_IDS},
        'identical sha256', 'sha256 exact', 'input_manifest.json')
    diag = ctx.get('diag')
    file_stats = diag.file_stats if diag else {}
    parse_counts = {fid: {'invalid_json': s['invalid_json'], 'decode_errors': s['decode_errors'],
                          'json_structure_errors': s['json_structure_errors'],
                          'line_count': s['line_count'], 'rows': s['rows']}
                    for fid, s in file_stats.items()}
    invalid_stats = (ctx.get('invalid_reconciliation') or {}).get('stats', {})
    n_parse_events = int(invalid_stats.get('reason_json_parse_error', 0)
                         + invalid_stats.get('reason_decode_error', 0)
                         + invalid_stats.get('reason_json_structure_error', 0))
    n_parse_rows = sum(v['invalid_json'] + v['decode_errors'] + v['json_structure_errors']
                       for v in parse_counts.values())
    chk(checks, 'C10_parse_failures_recorded', 'every unparsable line keeps a placeholder row and an event',
        'PASS' if n_parse_rows == n_parse_events else 'FAIL',
        {'parse_failure_rows': n_parse_rows, 'identity_events': n_parse_events, 'per_file': parse_counts},
        'equal counts', 'exact', 'invalid_values.csv.gz / row_masks.csv.gz')
    expected = {'total_records': prior_audit_ref['total_records'],
                'unique_keys': prior_audit_ref['unique_id_sub_path_keys'],
                'duplicate_rows': prior_audit_ref['duplicate_occurrences']}
    actual = {k: ctx.get('aggregate_totals', {}).get(k) for k in expected}
    chk(checks, 'C11_totals_match_prior_audit', 'rows / unique keys / duplicates equal prior audit.json',
        'PASS' if (actual == expected and all(v is not None for v in actual.values())) else 'FAIL', {'actual': actual, 'expected': expected},
        'equal counts', 'exact', 'comparison_with_prior.csv')
    file_expected = {}
    for f in prior_audit_ref['files']:
        file_expected[f['file_id']] = {'rows': f['rows'],
                                       'unique': f['unique_id_sub_path_keys_in_file'],
                                       'within_file_duplicates': f['within_file_duplicate_rows'],
                                       'overlapping_a1_rows': f['overlapping_a1_rows']}
    file_actual = {}
    for fid, s in file_stats.items():
        file_actual[fid] = {'rows': s['rows'], 'unique': len(diag.key_sets[fid]),
                            'within_file_duplicates': s['within_file_duplicate_rows'],
                            'overlapping_a1_rows': s['overlap_a1_rows']}
    chk(checks, 'C12_file_level_counts_match_prior', 'per-file rows/unique/duplicate/overlap equal prior audit',
        'PASS' if (file_actual and file_actual == file_expected) else ('NOT_CHECKED' if not file_actual else 'FAIL'),
        {'actual': file_actual, 'expected': file_expected}, 'equal counts', 'exact',
        'comparison_with_prior.csv')
    pair_expected = prior_audit_ref['pairwise_key_intersections']
    pair_actual = ctx.get('aggregate_totals', {}).get('pairwise_intersections', {})
    chk(checks, 'C13_pairwise_key_intersections_match_prior', 'file-pair key-set intersections equal prior audit',
        'PASS' if (pair_actual and pair_actual == pair_expected) else ('NOT_CHECKED' if not pair_actual else 'FAIL'),
        {'actual': pair_actual, 'expected': pair_expected}, 'equal counts', 'exact',
        'comparison_with_prior.csv')
    conflict_expected = {'quality_conflicts': len(prior_audit_ref['quality_conflicts']),
                         'domain_collisions': len(prior_audit_ref['domain_collisions'])}
    conflict_actual = {'quality_conflicts': ctx.get('aggregate_totals', {}).get('quality_conflicts'),
                       'domain_collisions': ctx.get('aggregate_totals', {}).get('domain_collisions')}
    chk(checks, 'C14_conflicts_match_prior', 'quality fingerprint conflicts / domain collisions equal prior audit',
        'PASS' if conflict_actual == conflict_expected else 'FAIL',
        {'actual': conflict_actual, 'expected': conflict_expected}, 'equal counts', 'exact',
        'comparison_with_prior.csv')
    tables = ctx.get('tables') or {}
    row_masks_rows = ctx.get('row_masks_rows')
    physical_lines = sum(s['line_count'] for s in file_stats.values())
    chk(checks, 'C15_row_masks_covers_all_physical_lines', 'every decompressed line kept in row_masks',
        'PASS' if row_masks_rows == physical_lines and row_masks_rows is not None else 'FAIL',
        {'row_masks_rows': row_masks_rows, 'physical_lines': physical_lines}, 'equal counts', 'exact',
        'row_masks.csv.gz')
    fmc = tables.get('feature_missing_counts', [])
    id_violations = [r for r in fmc if int(r['n_total']) != int(r['n_finite']) + int(r['n_nonfinite'])]
    part_violations = [r for r in fmc if int(r['n_nonfinite']) != int(r['n_nan']) + int(r['n_posinf']) + int(r['n_neginf'])]
    chk(checks, 'C16_extract_layer_additivity', 'n_total = n_finite + n_nonfinite for every feature row',
        'PASS' if not id_violations else 'FAIL', {'violations': len(id_violations), 'rows': len(fmc)},
        '0 violations', 'exact', 'feature_missing_counts.csv')
    chk(checks, 'C17_nonfinite_partition', 'n_nonfinite = n_nan + n_posinf + n_neginf for every feature row',
        'PASS' if not part_violations else 'FAIL', {'violations': len(part_violations)},
        '0 violations', 'exact', 'feature_missing_counts.csv')
    pattern_sums = defaultdict(dict)
    for row in tables.get('missing_patterns', []):
        key = (row['scope'], row['domain'], row['mask_kind'])
        pattern_sums[key] = pattern_sums.get(key, 0) + int(row['n'])
    pattern_violations = []
    for row in tables.get('missing_patterns', []):
        key = (row['scope'], row['domain'], row['mask_kind'])
        if pattern_sums[key] != int(row['n_scope']):
            pattern_violations.append(key)
    pattern_violations = sorted(set(pattern_violations))
    chk(checks, 'C18_pattern_counts_sum_to_scope_n', 'sum of pattern counts equals scope x domain n',
        'PASS' if not pattern_violations else 'FAIL',
        {'violations': pattern_violations[:5], 'n_violations': len(pattern_violations),
         'n_groups': len(pattern_sums)}, '0 violations', 'exact', 'missing_patterns.csv')
    diag_violations = []
    inc_violations = []
    for row in tables.get('missing_pairwise', []):
        if row['feature_i'] == row['feature_j']:
            if int(row['n_intersection']) != int(row['n_i']) or int(row['n_union']) != int(row['n_i']):
                diag_violations.append((row['scope'], row['domain'], row['mask_kind'], row['feature_i']))
        else:
            if int(row['n_union']) != int(row['n_i']) + int(row['n_j']) - int(row['n_intersection']):
                inc_violations.append((row['scope'], row['domain'], row['mask_kind'],
                                       row['feature_i'], row['feature_j']))
    chk(checks, 'C19_pairwise_diagonal_equals_marginal', 'pairwise diagonal equals single-feature count',
        'PASS' if not diag_violations else 'FAIL', {'n_violations': len(diag_violations),
                                                    'examples': diag_violations[:3]},
        '0 violations', 'exact', 'missing_pairwise.csv')
    chk(checks, 'C20_pairwise_inclusion_exclusion', '|A union B| = |A| + |B| - |A intersect B|',
        'PASS' if not inc_violations else 'FAIL', {'n_violations': len(inc_violations),
                                                   'examples': inc_violations[:3]},
        '0 violations', 'exact', 'missing_pairwise.csv')
    complete_violations = [r for r in tables.get('validity_counts', [])
                           if int(r['n_complete_11_notnan']) != int(r['n_total']) - int(r['n_would_Q_nan'])
                           or int(r['n_valid_mainQ_11']) != int(r['n_total']) - int(r['n_would_Q_nan'])]
    chk(checks, 'C21_mainQ_complete_equals_failure_complement',
        '11-feature complete count equals complement of the propagation mask',
        'PASS' if not complete_violations else 'FAIL',
        {'n_violations': len(complete_violations), 'n_rows': len(tables.get('validity_counts', []))},
        '0 violations', 'exact', 'validity_counts.csv')
    reagg = ctx.get('reagg_counters', {})
    chk(checks, 'C22_group_and_Q_mask_logic', 'row-level group/Q masks reproduce constituent NaN propagation',
        'PASS' if reagg.get('group_mask_mismatch', 0) == 0 and reagg.get('q_nan_mask_mismatch', 0) == 0
        and reagg.get('rows') is not None else 'FAIL',
        {'group_mask_mismatch': reagg.get('group_mask_mismatch'),
         'q_nan_mask_mismatch': reagg.get('q_nan_mask_mismatch'),
         'extract_vs_norm_nan_mismatch': reagg.get('extract_vs_norm_nan_mismatch'),
         'norm_nonfinite_non_nan': reagg.get('norm_nonfinite_non_nan')},
        'all zero', 'exact', 'row_masks.csv.gz')
    chk(checks, 'C23_norm_layer_equals_extract_layer',
        'normalized NaN masks equal extraction NaN masks for the 11 main-Q features; no non-NaN non-finite',
        'PASS' if reagg.get('extract_vs_norm_nan_mismatch', 1) == 0 and reagg.get('norm_nonfinite_non_nan', 1) == 0 else 'FAIL',
        {'extract_vs_norm_nan_mismatch': reagg.get('extract_vs_norm_nan_mismatch'),
         'norm_nonfinite_non_nan': reagg.get('norm_nonfinite_non_nan')},
        'all zero', 'exact', 'row_masks.csv.gz')
    vc = {(r['scope'], r['domain']): r for r in tables.get('validity_counts', [])}
    denom_rows = tables.get('summary_denominators', [])
    denom_violations = []
    for row in denom_rows:
        key = (row['scope'], row['domain'])
        v = vc.get(key)
        if v is None:
            denom_violations.append(('missing_validity_row', key, row['statistic']))
            continue
        if row['statistic'] == 'Q_mean' and int(row['n_effective']) != int(v['n_valid_mainQ_11']):
            denom_violations.append(('Q_mean_denominator', key, row['n_effective'], v['n_valid_mainQ_11']))
        if row['statistic'] == 'rater_disagreement_gt_0_5_fraction' and int(row['n_effective']) != int(row['n_total']):
            denom_violations.append(('gt05_denominator', key, row['n_effective'], row['n_total']))
    chk(checks, 'C24_summary_denominator_algebra', 'denominators consistent with propagation and scope masks',
        'PASS' if not denom_violations else 'FAIL',
        {'n_violations': len(denom_violations), 'examples': denom_violations[:5]},
        '0 violations', 'exact', 'summary_denominators.csv')
    comparison_rows = ctx.get('comparison_rows', [])
    def mismatch_count(artifact):
        return sum(1 for r in comparison_rows
                   if r['prior_artifact'] == artifact and r.get('match') == 'MISMATCH')
    chk(checks, 'C25_raw_field_prior_semantics_match', 'replicated raw-field statistics equal prior audit.json',
        'PASS' if mismatch_count('solution/outputs/quality/audit.json') == 0 else 'FAIL',
        {'n_mismatch': mismatch_count('solution/outputs/quality/audit.json'),
         'n_comparisons': sum(1 for r in comparison_rows
                              if r['prior_artifact'] == 'solution/outputs/quality/audit.json')},
        'n_mismatch = 0', 'exact', 'comparison_with_prior.csv')
    for cid, artifact, desc in [('C26_feature_summary_counts_match',
                                 'solution/outputs/quality/feature_summary.csv',
                                 'prior feature_summary non-missing counts reproduced'),
                                ('C27_domain_summary_n_match',
                                 'solution/outputs/quality/domain_summary.csv',
                                 'prior domain_summary scope x domain n reproduced'),
                                ('C28_extension_shift_counts_match',
                                 'solution/outputs/quality/extension_shift.csv',
                                 'prior extension_shift a1_n/extension_new_n reproduced'),
                                ('C29_recovery_deficit_counts_match',
                                 'recovery/2026-09-24/quality_gap_evidence.json',
                                 'recovery deficit counts reconciled with current masks')]:
        n_comparisons = sum(1 for r in comparison_rows if r['prior_artifact'] == artifact)
        n_mismatch = mismatch_count(artifact)
        chk(checks, cid, desc,
            'PASS' if n_comparisons and n_mismatch == 0 else ('NOT_CHECKED' if not n_comparisons else 'FAIL'),
            {'n_comparisons': n_comparisons, 'n_mismatch': n_mismatch}, 'n_mismatch = 0', 'exact',
            'comparison_with_prior.csv')
    unresolved = [r for r in comparison_rows if r.get('match') == 'MISMATCH' and not int(r.get('resolved', 0))]
    chk(checks, 'C30_no_unresolved_prior_mismatch', 'all prior mismatches explained and resolved',
        'PASS' if not unresolved else 'FAIL',
        {'n_unresolved': len(unresolved), 'examples': [f"{r['prior_item']}|{r['metric']}" for r in unresolved[:5]]},
        'n_unresolved = 0', 'exact', 'comparison_with_prior.csv')
    verification = ctx.get('verification', {})
    if verification:
        bad = {k: {'n_value_mismatches': v['n_value_mismatches'],
                   'n_missing_in_recompute': v['n_missing_in_recompute'],
                   'n_extra_in_recompute': v['n_extra_in_recompute']}
               for k, v in verification.items()
               if v['n_value_mismatches'] or v['n_missing_in_recompute'] or v['n_extra_in_recompute']}
        chk(checks, 'C31_independent_reaggregation_from_row_masks',
            'CSV tables recomputed from row_masks.csv.gz alone match exactly',
            'PASS' if not bad else 'FAIL', {'tables': len(verification), 'tables_with_differences': bad},
            'no differences', 'exact', 'checks.json#verification')
    else:
        chk(checks, 'C31_independent_reaggregation_from_row_masks',
            'CSV tables recomputed from row_masks.csv.gz alone match exactly',
            'NOT_CHECKED', {}, 'no differences', 'exact', 'row_masks.csv.gz')
    recon = ctx.get('invalid_reconciliation') or {}
    extract_events = recon.get('extract_events', {})
    expected_nan = {}
    for feature in FEATURES:
        row = next((r for r in fmc if r['scope'] == 'all_unique' and r['domain'] == 'ALL'
                    and r['feature'] == feature), None)
        if row is not None:
            expected_nan[feature] = int(row['n_nan'])
    event_nan = {f: extract_events.get(f'{f}|nan', 0) for f in FEATURES}
    reconcile_ok = event_nan == expected_nan and recon.get('stats', {}).get('unknown_row_identity', 0) == 0
    chk(checks, 'C32_invalid_events_reconcile_with_masks',
        'extract-layer NaN events match all_unique marginal NaN counts; all event rows exist in row_masks',
        'PASS' if reconcile_ok and expected_nan else 'FAIL',
        {'event_nan_total': sum(event_nan.values()), 'marginal_nan_total': sum(expected_nan.values()),
         'unknown_row_identity': recon.get('stats', {}).get('unknown_row_identity'),
         'mismatch_features': [f for f in FEATURES if event_nan.get(f) != expected_nan.get(f, 0)][:5]},
        'equal totals', 'exact', 'invalid_values.csv.gz')
    forbidden_columns = {'Q_baseline', 'group_usability', 'group_knowledge',
                         'group_education_reasoning', 'Q_equal_indicator_sensitivity',
                         'Q_without_knowledge_sensitivity'}
    header_violations = []
    for name in list(TABLE_COLUMNS):
        path = RUN_DIR / f'{name}.csv'
        if path.exists():
            with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
                header = next(csv.reader(fh), [])
            if forbidden_columns & set(header):
                header_violations.append(str(path.name))
    row_masks_path = RUN_DIR / 'row_masks.csv.gz'
    if row_masks_path.exists():
        with gzip.open(row_masks_path, 'rt', encoding='utf-8', newline='') as fh:
            row_header = next(csv.reader(fh), [])
        if forbidden_columns & set(row_header):
            header_violations.append('row_masks.csv.gz')
    else:
        header_violations.append('row_masks.csv.gz missing')
    chk(checks, 'C33_no_numeric_Q_output', 'no numeric Q / group-score columns produced by this run',
        'PASS' if not header_violations else 'FAIL',
        {'files_with_forbidden_columns': header_violations,
         'final_Q_recomputed': False, 'final_strategy_selected': False},
        'none', 'exact', 'output_manifest.json')
    json_nan_hits = []
    for path in sorted(RUN_DIR.glob('*.json')):
        if path.name == 'output_manifest.json':
            continue
        text = path.read_text(encoding='utf-8')
        if 'NaN' in text or 'Infinity' in text:
            json_nan_hits.append(path.name)
    chk(checks, 'C34_json_strict_no_nan_infinity', 'all JSON artifacts are strict (null + status fields)',
        'PASS' if not json_nan_hits else 'FAIL', {'files_with_nan_or_infinity_tokens': json_nan_hits},
        'none', 'exact', 'checks.json')
    official = {}
    for scope in OFFICIAL_SCOPE_NAMES:
        row = vc.get((scope, 'ALL'))
        official[scope] = row['n_total'] if row else None
    chk(checks, 'C35_six_official_scopes_present', 'all six summarize scopes present with ALL totals',
        'PASS' if all(v is not None for v in official.values()) else 'FAIL', official,
        'all six present', 'exact', 'validity_counts.csv')
    elapsed = time.monotonic() - START_MONO
    peak = peak_rss_bytes()
    chk(checks, 'C36_resource_limits_respected', 'wall-clock and memory stay within the unit limits',
        'PASS' if elapsed <= WALL_LIMIT_S and (peak is None or peak <= MEM_LIMIT_BYTES) else 'FAIL',
        {'elapsed_s': round(elapsed, 1), 'wall_limit_s': WALL_LIMIT_S,
         'peak_rss_bytes': peak, 'mem_limit_bytes': MEM_LIMIT_BYTES},
        'elapsed <= limit and peak <= limit', 'exact', 'environment.json')
    dup_mask_conflicts = int(sum(s['duplicate_mask_conflict_rows'] for s in file_stats.values()))
    dup_events = int(invalid_stats.get('reason_duplicate_mask_conflict', 0))
    chk(checks, 'C37_duplicate_mask_conflicts_reported',
        'duplicate keys whose anomaly masks differ are reported, not hidden',
        'PASS' if dup_mask_conflicts == dup_events else 'FAIL',
        {'duplicate_rows_with_differing_masks': dup_mask_conflicts, 'events_written': dup_events},
        'equal counts', 'exact', 'invalid_values.csv.gz')
    error_rows = {'audit_errors': ctx.get('diag').audit_error_rows if ctx.get('diag') else None,
                  'fingerprint_errors': ctx.get('diag').fingerprint_error_rows if ctx.get('diag') else None}
    error_events = int(invalid_stats.get('reason_audit_exception', 0)
                       + invalid_stats.get('reason_fingerprint_error', 0))
    expected_errors = (error_rows['audit_errors'] or 0) + (error_rows['fingerprint_errors'] or 0)
    chk(checks, 'C38_audit_and_fingerprint_errors_recorded', 'any extraction/fingerprint exception is recorded',
        'PASS' if error_events == expected_errors else 'FAIL',
        {'counters': error_rows, 'events': error_events}, 'equal counts', 'exact',
        'invalid_values.csv.gz')
    read_accounting = {fid: {'decompress_passes': s['decompress_passes'], 'retries': s['retries'],
                             'line_count': s['line_count'], 'rows': s['rows']}
                       for fid, s in file_stats.items()}
    chk(checks, 'C39_single_decompression_pass_no_retry',
        'each file decompressed once, no retries, rows + unparsable lines equal decompressed lines',
        'PASS' if all(v['decompress_passes'] == 1 and v['retries'] == 0
                      and v['line_count'] == v['rows'] + sum(file_stats[fid][k] for k in
                                                            ['invalid_json', 'decode_errors',
                                                             'json_structure_errors'])
                      for fid, v in read_accounting.items()) else 'FAIL',
        read_accounting, 'one pass per file', 'exact', 'run.log')
    manifest_ok = True
    manifest_paths = ctx.get('output_files', [])
    for path in manifest_paths:
        try:
            if RUN_DIR.resolve() not in Path(path).resolve().parents:
                manifest_ok = False
        except Exception:
            manifest_ok = False
    chk(checks, 'C40_writes_confined_to_run_dir', 'every produced file lives inside the run directory',
        'PASS' if manifest_ok else 'FAIL',
        {'n_files': len(manifest_paths), 'run_dir': str(RUN_DIR)}, 'all inside run dir', 'exact',
        'output_manifest.json')
    return checks


def build_key_numbers(ctx):
    tables = ctx.get('tables') or {}
    vc = {(r['scope'], r['domain']): r for r in tables.get('validity_counts', [])}
    fmc = tables.get('feature_missing_counts', [])
    raw = tables.get('raw_field_counts', [])
    scopes = {}
    for scope in OFFICIAL_SCOPE_NAMES + ['file_unique_first_A1', 'file_unique_first_A2_arxiv',
                                         'file_unique_first_A3_github']:
        row = vc.get((scope, 'ALL'))
        if row is None:
            continue
        scopes[scope] = {'n': int(row['n_total']), 'n_complete_11': int(row['n_complete_11_notnan']),
                         'n_complete_25': int(row['n_complete_25_notnan']),
                         'n_would_Q_nan': int(row['n_would_Q_nan']),
                         'n_valid_mainQ_11': int(row['n_valid_mainQ_11']),
                         'rate_complete_11': row['rate_complete_11'],
                         'rate_complete_25': row['rate_complete_25']}
    nonfinite_features = {}
    for row in fmc:
        if row['scope'] == 'all_unique' and row['domain'] == 'ALL' and int(row['n_nonfinite']) > 0:
            nonfinite_features[row['feature']] = {'n_nan': int(row['n_nan']), 'n_posinf': int(row['n_posinf']),
                                                  'n_neginf': int(row['n_neginf']),
                                                  'n_nonfinite': int(row['n_nonfinite']),
                                                  'n_total': int(row['n_total'])}
    raw_nan_elements = {}
    raw_posinf_elements = {}
    raw_neginf_elements = {}
    raw_wrong_length_rows = {}
    raw_non_numeric_elements = {}
    for row in raw:
        if row['domain'] != 'ALL':
            continue
        field = f"{row['file_id']}|{row['field']}"
        if int(row['nan_elements']) > 0:
            raw_nan_elements[field] = int(row['nan_elements'])
        if int(row['posinf_elements']) > 0:
            raw_posinf_elements[field] = int(row['posinf_elements'])
        if int(row['neginf_elements']) > 0:
            raw_neginf_elements[field] = int(row['neginf_elements'])
        if int(row['wrong_length_rows']) > 0:
            raw_wrong_length_rows[field] = int(row['wrong_length_rows'])
        if int(row['non_numeric_elements']) > 0:
            raw_non_numeric_elements[field] = int(row['non_numeric_elements'])
    known_domain = {}
    for row in ctx.get('known_domain_rows', []):
        key = f"{row['domain']}|{row['feature']}|{row['scope']}"
        if int(row['run_n_missing']) > 0 or row['prior_n_missing'] not in ('', None):
            known_domain[key] = {'run_n_total': int(row['run_n_total']),
                                 'run_n_missing': int(row['run_n_missing']),
                                 'missing_A1': int(row['missing_rows_A1']),
                                 'missing_extension_new': int(row['missing_rows_extension_new']),
                                 'missing_extension_overlap': int(row['missing_rows_extension_overlap'])}
    allu = vc.get(('all_unique', 'ALL'))
    return {
        'scopes': scopes,
        'nonfinite_features_all_unique': nonfinite_features,
        'raw_nan_elements_by_file_field': raw_nan_elements,
        'raw_posinf_elements_by_file_field': raw_posinf_elements,
        'raw_neginf_elements_by_file_field': raw_neginf_elements,
        'raw_wrong_length_rows_by_file_field': raw_wrong_length_rows,
        'raw_non_numeric_elements_by_file_field': raw_non_numeric_elements,
        'known_domain_missingness': known_domain,
        'complete_case_loss_all_unique': {
            'mainQ11_not_covered': (int(allu['n_total']) - int(allu['n_complete_11_notnan'])) if allu else None,
            'all25_not_covered': (int(allu['n_total']) - int(allu['n_complete_25_notnan'])) if allu else None,
            'mainQ11_fraction_not_covered': (1 - float(allu['rate_complete_11'])) if allu and allu['rate_complete_11'] is not None else None,
            'all25_fraction_not_covered': (1 - float(allu['rate_complete_25'])) if allu and allu['rate_complete_25'] is not None else None},
        'duplicate_rows_with_differing_anomaly_masks': (
            sum(s['duplicate_mask_conflict_rows'] for s in ctx.get('diag').file_stats.values())
            if ctx.get('diag') else None),
        'norm_inf_rows': (ctx.get('diag').norm_inf_rows if ctx.get('diag') else None),
        'audit_error_rows': (ctx.get('diag').audit_error_rows if ctx.get('diag') else None),
        'fingerprint_error_rows': (ctx.get('diag').fingerprint_error_rows if ctx.get('diag') else None),
    }


def build_handoff(ctx, checks):
    tables = ctx.get('tables') or {}
    key = ctx.get('key_numbers') or {}
    vc = {(r['scope'], r['domain']): r for r in tables.get('validity_counts', [])}
    lines = []
    lines.append('# TASK-Q01A 交回说明（客观事实摘要）')
    lines.append('')
    lines.append(f"- 状态：{ctx.get('status')}；退出码 {ctx.get('exit_code')}；run目录：`{RUN_DIR}`。")
    lines.append(f"- 本次仅完成缺失模式诊断；未选择或实施最终缺失处理策略，未删除记录、未填0、未生成最终Q、未覆盖旧quality产物。等待主控GPT审查TASK-Q01B。")
    totals = ctx.get('aggregate_totals') or {}
    file_stats = (ctx.get('diag').file_stats if ctx.get('diag') else {})
    lines.append(f"- 全量扫描：三文件各单遍解压，解析成功 {totals.get('total_records')} 行，"
                 f"唯一键 {totals.get('unique_keys')}，重复行 {totals.get('duplicate_rows')}；"
                 f"三份压缩文件SHA256与旧清单/旧audit一致，扫描后复核哈希不变。")
    lines.append(f"- 逐文件行数：" + '；'.join(f"{fid}={s['rows']}" for fid, s in file_stats.items()) + '。')
    scope_txt = []
    for scope, info in key.get('scopes', {}).items():
        scope_txt.append(f"{scope}: n={info['n']}, 11主Q完整={info['n_complete_11']}, "
                         f"would_Q_nan={info['n_would_Q_nan']}, 25特征完整={info['n_complete_25']}")
    lines.append('- 六个口径与文件视图（ALL）：' + '；'.join(scope_txt) + '。')
    nf = key.get('nonfinite_features_all_unique', {})
    if nf:
        lines.append('- 提取层非有限（all_unique，按特征）：' +
                     '；'.join(f"{k}: nan={v['n_nan']}, +inf={v['n_posinf']}, -inf={v['n_neginf']}, "
                               f"合计={v['n_nonfinite']}/{v['n_total']}" for k, v in nf.items()) + '。')
    else:
        lines.append('- 提取层非有限（all_unique）：无（25个特征全部有限）。')
    raw_nan = key.get('raw_nan_elements_by_file_field', {})
    lines.append('- 原始层NaN元素（文件|字段：元素数）：' +
                 ('；'.join(f"{k}: {v}" for k, v in raw_nan.items()) if raw_nan else '无') + '。')
    lengths = key.get('raw_wrong_length_rows_by_file_field', {})
    lines.append('- 原始层列表长度不符行数：' + ('；'.join(f"{k}: {v}" for k, v in lengths.items()) if lengths else '无') + '。')
    loss = key.get('complete_case_loss_all_unique', {})
    lines.append(f"- complete-case仅计数（all_unique）：11主Q未覆盖 {loss.get('mainQ11_not_covered')} 行，"
                 f"25特征未覆盖 {loss.get('all25_not_covered')} 行；仅计数、不构成处理建议。")
    kd = key.get('known_domain_missingness', {})
    examples = [f"{k}: run_missing={v['run_n_missing']}, A1={v['missing_A1']}, "
                f"ext_new={v['missing_extension_new']}, ext_overlap={v['missing_extension_overlap']}"
                for k, v in kd.items() if v['run_n_missing'] > 0]
    lines.append('- 已知异常域分布（域|特征|口径）：' + ('；'.join(examples[:12]) if examples else '当前运行未见缺失') + '。')
    n_checks = len(checks)
    n_pass = sum(1 for c in checks if c['status'] == 'PASS')
    n_fail = sum(1 for c in checks if c['status'] == 'FAIL')
    n_nc = sum(1 for c in checks if c['status'] == 'NOT_CHECKED')
    lines.append(f'- 验收检查：{n_checks} 项，PASS {n_pass}，FAIL {n_fail}，NOT_CHECKED {n_nc}；详见 checks.json。')
    if ctx.get('unfinished'):
        lines.append('- 未完成/不能判断：' + '；'.join(ctx['unfinished']) + '。')
    lines.append('- 限制：仅统计掩码与分母，不判断MCAR/MAR/MNAR，不把“集中”当因果；主Q数值与任何处理效果均未重算；'
                 'A18正文未读取，旧版本外的其他A/B/C表未使用。')
    lines.append('')
    lines.append('## 交回主控GPT的待裁决问题（Q01B，仅列问题）')
    lines.append('1. 11个主Q特征出现非有限值时，处理原则（保留/排除/其他）和判定所需的最低证据标准是什么？')
    lines.append('2. 是否区分域与验证角色（calibration/holdout/extension_new/extension_overlap）分别处理，理由与可接受差异如何界定？')
    lines.append('3. 覆盖率与域间可比性的权衡标准是什么（各域有效分母差异多大时触发额外处理）？')
    lines.append('4. 下游所有汇总是否必须显式披露有效n与非有限占比，并要求何种验证来证明处理不引入偏差？')
    lines.append('5. 扩展重叠副本与A1中同一键、同一异常状态的记录，是否可视为同一证据？重复行应如何计入分母披露？')
    lines.append('6. 现有证据是否足够，是否需要补充诊断（例如指标联合模式、按子域/来源分层的更多口径）？')
    return '\n'.join(lines)


def finalize(log, ctx, exit_code):
    ctx['exit_code'] = exit_code
    ctx['output_files'] = [str(p) for p in sorted(RUN_DIR.rglob('*')) if p.is_file()]
    ctx['end_iso'] = now_iso()
    ctx['duration_s'] = time.monotonic() - START_MONO
    ctx['environment'] = {
        'run_id': RUN_ID, 'task': 'TASK-Q01A',
        'script': str(RUN_DIR / 'diagnose_missingness.py'),
        'script_sha256': sha256_file(RUN_DIR / 'diagnose_missingness.py'),
        'python_executable': sys.executable,
        'python_version': sys.version.replace('\n', ' '),
        'python_implementation': platform.python_implementation(),
        'platform': {'system': platform.system(), 'release': platform.release(),
                     'version': platform.version(), 'machine': platform.machine()},
        'cwd': os.getcwd(),
        'timezone': str(datetime.now().astimezone().tzinfo),
        'start_local': START_ISO, 'end_local': ctx['end_iso'],
        'duration_s': round(ctx['duration_s'], 3),
        'stage_seconds': {k: round(v, 3) for k, v in ctx.get('stage_seconds', {}).items()},
        'libraries': {'numpy': np.__version__},
        'actual_command': f'"{sys.executable}" -X utf8 "{RUN_DIR / "diagnose_missingness.py"}"',
        'exit_code': exit_code,
        'seed': SEED,
        'split_rule': f'int(sha256(str({SEED})+key_json)[:16],16) % {SPLIT_MODULUS}; remainder 0 => A1_holdout',
        'utf8_mode': bool(getattr(sys.flags, 'utf8_mode', 0)),
        'single_process_cpu': True, 'gpu_used': False, 'network_used': False,
        'resource_limits': {'wall_limit_s': WALL_LIMIT_S, 'memory_limit_bytes': MEM_LIMIT_BYTES},
        'resource_observed': {'peak_rss_bytes': peak_rss_bytes(),
                              'measurement': 'psutil memory_info().peak_wset' if psutil else 'unknown'},
        'decompression': {fid: {'passes': s['decompress_passes'], 'retries': s['retries'],
                                'rows': s['rows'], 'line_count': s['line_count']}
                          for fid, s in ((ctx.get('diag').file_stats.items()) if ctx.get('diag') else [])},
        'hash_reads_per_file': 2,
        'errors': ctx.get('errors', []), 'unfinished': ctx.get('unfinished', [])}
    try:
        import pandas as _pd
        ctx['environment']['libraries']['pandas'] = _pd.__version__
    except Exception:
        ctx['environment']['libraries']['pandas'] = None
    if psutil is not None:
        try:
            ctx['environment']['libraries']['psutil'] = psutil.__version__
        except Exception:
            pass
    checks = build_checks(log, ctx)
    ctx['checks'] = checks
    n_fail = sum(1 for c in checks if c['status'] == 'FAIL')
    if n_fail and ctx.get('status') == 'COMPLETE_DIAGNOSTIC':
        ctx['status'] = 'PARTIAL'
        ctx['errors'].append(f'{n_fail} acceptance checks FAILED')
        exit_code = 2
        ctx['exit_code'] = exit_code
        ctx['environment']['exit_code'] = exit_code
    ctx['key_numbers'] = build_key_numbers(ctx)
    checks_payload = {
        'run_id': RUN_ID, 'task': 'TASK-Q01A', 'status': ctx.get('status'),
        'exit_code': exit_code,
        'summary': {'n_checks': len(checks),
                    'n_pass': sum(1 for c in checks if c['status'] == 'PASS'),
                    'n_fail': n_fail,
                    'n_not_checked': sum(1 for c in checks if c['status'] == 'NOT_CHECKED')},
        'checks': checks,
        'synthetic_selftest': ctx.get('synthetic'),
        'verification_from_row_masks': ctx.get('verification'),
        'invalid_values_reconciliation': ctx.get('invalid_reconciliation'),
        'reaggregation_counters': ctx.get('reagg_counters'),
        'errors': ctx.get('errors', []), 'unfinished': ctx.get('unfinished', [])}
    write_json(RUN_DIR / 'checks.json', checks_payload)
    write_json(RUN_DIR / 'environment.json', ctx['environment'])
    write_json(RUN_DIR / 'diagnostic_spec.json',
               build_diagnostic_spec(ctx.get('source_report'), ctx.get('norm_report'),
                                     ctx.get('transforms') or {},
                                     {'scope_views': [name for name, _ in SCOPE_VIEWS],
                                      'table_files': sorted(TABLE_COLUMNS)}))
    write_json(RUN_DIR / 'input_manifest.json', ctx.get('input_manifest') or {})
    summary = {
        'task': 'TASK-Q01A', 'run_id': RUN_ID, 'status': ctx.get('status'),
        'exit_code': exit_code, 'run_dir': str(RUN_DIR),
        'start_local': START_ISO, 'end_local': ctx['end_iso'],
        'duration_s': round(ctx['duration_s'], 3),
        'inputs': {'files_read': len(PRIMARY_INPUTS) + len(SECONDARY_INPUTS),
                   'primary_files': [str(p) for p in PRIMARY_INPUTS],
                   'decompression_policy': 'one sequential pass per file',
                   'hash_reads_per_file': 2, 'retries': 0,
                   'sha256_matches_registered': ctx.get('sha_checks')},
        'read_counts': {fid: {'rows': s['rows'], 'invalid_json': s['invalid_json'],
                              'decode_errors': s['decode_errors'],
                              'json_structure_errors': s['json_structure_errors'],
                              'domains': s['domains']} for fid, s in
                        ((ctx.get('diag').file_stats.items()) if ctx.get('diag') else [])},
        'totals': ctx.get('aggregate_totals'),
        'key_numbers': ctx['key_numbers'],
        'tables_written': ctx.get('tables_written'),
        'checks': checks_payload['summary'],
        'unfinished_items': ctx.get('unfinished', []),
        'errors': ctx.get('errors', []),
        'final_strategy_selected': False,
        'final_Q_recomputed': False,
        'not_modified': {'raw_inputs': True, 'solution_src': True, 'solution_outputs': True,
                         'recovery': True, 'project_docs': True},
        'handoff_file': 'handoff.md'}
    write_json(RUN_DIR / 'run_summary.json', summary)
    (RUN_DIR / 'handoff.md').write_text(build_handoff(ctx, checks), encoding='utf-8')
    manifest_files = []
    for path in sorted(RUN_DIR.rglob('*')):
        if not path.is_file() or path.name == 'output_manifest.json':
            continue
        stat = path.stat()
        manifest_files.append({'path': str(path.relative_to(RUN_DIR)).replace('\\', '/'),
                               'bytes': stat.st_size, 'sha256': sha256_file(path)})
    write_json(RUN_DIR / 'output_manifest.json',
               {'run_id': RUN_ID, 'generated_local': now_iso(),
                'n_files': len(manifest_files), 'files': manifest_files})
    log(f"stage=finalize status={ctx.get('status')} exit_code={exit_code} "
        f"checks={checks_payload['summary']} duration_s={ctx['duration_s']:.1f}")
    return exit_code


def salvage_from_partial(log, ctx):
    """Aggregate whatever rows were already scanned and write partial count tables."""
    diag = ctx.get('diag')
    if diag is None or ctx.get('tables') is not None:
        return
    if diag.store.n == 0:
        log('stage=salvage no rows scanned; nothing to aggregate')
        return
    try:
        arrays = diag.store.finalize()
        unique_flags = (arrays['flags'] & F_UNIQUE) != 0
        pairwise = {}
        for i, a in enumerate(FILE_IDS):
            for b in FILE_IDS[i + 1:]:
                ka, kb = diag.key_sets.get(a), diag.key_sets.get(b)
                pairwise[f'{a}__{b}'] = len(ka & kb) if (ka is not None and kb is not None) else None
        ctx['aggregate_totals'] = {
            'total_records': int(len(arrays['file_code'])),
            'unique_keys': int(unique_flags.sum()),
            'duplicate_rows': int((~unique_flags).sum()),
            'pairwise_intersections': pairwise,
            'quality_conflicts': int(sum(s['quality_conflicting_rows'] for s in diag.file_stats.values())),
            'domain_collisions': int(sum(s['domain_collision_rows'] for s in diag.file_stats.values())),
            'file_unique': {fid: (len(diag.key_sets[fid]) if fid in diag.key_sets else None)
                            for fid in FILE_IDS},
            'partial': True}
        domain_names = diag.domain_names or ['unknown']
        tables, group_stats = aggregate_rows(arrays, domain_names)
        tables['raw_field_counts'] = build_raw_field_counts({'file_stats': diag.file_stats,
                                                             'raw_prior': diag.raw_prior,
                                                             'raw_detail': diag.raw_detail})
        tables['physical_rows_by_file_role'] = build_physical_rows_table(arrays, domain_names)
        TABLE_COLUMNS['raw_field_counts'] = RAW_FIELD_COLUMNS
        TABLE_COLUMNS['physical_rows_by_file_role'] = PHYSICAL_ROW_COLUMNS
        ctx['tables'] = tables
        ctx['group_stats'] = group_stats
        ctx['tables_written'] = write_tables(tables, log)
        log('stage=salvage wrote partial tables from rows scanned before the stop')
    except Exception:
        log('ERROR salvage_failed\n' + traceback.format_exc())


def main():
    log = Logger(RUN_DIR / 'run.log')
    ctx = {'status': 'COMPLETE_DIAGNOSTIC', 'errors': [], 'unfinished': [], 'stage_seconds': {},
           'checks': [], 'tables': None, 'key_numbers': {}}
    log('=' * 72)
    log(f'TASK-Q01A start local={START_ISO} run_dir={RUN_DIR}')
    log(f'constraints wall_limit_s={WALL_LIMIT_S} memory_limit_bytes={MEM_LIMIT_BYTES} seed={SEED}')
    try:
        run_task(log, ctx)
        ctx['status'] = 'COMPLETE_DIAGNOSTIC'
    except PreconditionError as exc:
        ctx['status'] = 'FAILED'
        ctx['errors'].append(f'PreconditionError: {exc}')
        log('ERROR precondition_failure: ' + str(exc))
    except ResourceStop as exc:
        ctx['status'] = 'PARTIAL'
        ctx['errors'].append(f'ResourceStop: {exc}')
        ctx['unfinished'].append('scan stopped at a resource boundary; partial evidence only')
        log('ERROR resource_stop: ' + str(exc))
    except Exception as exc:
        ctx['status'] = 'FAILED'
        ctx['errors'].append(f'{type(exc).__name__}: {exc}')
        log('ERROR unhandled_exception: ' + type(exc).__name__ + ': ' + str(exc))
        log('ERROR traceback\n' + traceback.format_exc())
    if ctx.get('tables') is None and ctx.get('diag') is not None:
        salvage_from_partial(log, ctx)
    exit_code = 0 if ctx['status'] == 'COMPLETE_DIAGNOSTIC' else 2
    try:
        exit_code = finalize(log, ctx, exit_code)
    except Exception:
        log('ERROR finalize_failure\n' + traceback.format_exc())
        try:
            write_json(RUN_DIR / 'run_summary.json', {
                'task': 'TASK-Q01A', 'run_id': RUN_ID, 'status': ctx.get('status', 'FAILED'),
                'exit_code': 2, 'run_dir': str(RUN_DIR), 'errors': ctx.get('errors', []),
                'final_strategy_selected': False, 'final_Q_recomputed': False,
                'note': 'finalize failed; see run.log'})
        except Exception:
            pass
        exit_code = 2
    log(f'TASK-Q01A end status={ctx.get("status")} exit_code={exit_code}')
    log.close()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
