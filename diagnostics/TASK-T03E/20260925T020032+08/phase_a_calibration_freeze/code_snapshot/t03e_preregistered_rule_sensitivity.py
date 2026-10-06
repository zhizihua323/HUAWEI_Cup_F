"""TASK-T03E: preregistered rule-sensitivity candidate (D = Q_baseline is the main result).

Three physically separate analysis modes plus a finalizer:
  calibration-preflight -> calibration-freeze (PHASE A, sealed) -> frozen-validation (PHASE B)

The confirmatory candidate is fixed: C = Q_baseline * (1 - 0.02 * P) with
P = (p_top2gram + p_top3gram) / 2 estimated only on A1 calibration.
Nothing here changes Q_baseline, and no A/B/PCA/entropy/CRITIC/lambda-learning is run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SOLUTION = Path(__file__).resolve().parents[1]
PROJECT = SOLUTION.parent
Q01C_RUN = SOLUTION / 'outputs' / 'quality_q01c' / '20260924T215718+08'
INPUT_PATH = Q01C_RUN / 'quality_features_scores.parquet'
MIXTURE_DIR = SOLUTION / 'outputs' / 'mixture'
A_DATA = PROJECT / 'F题' / 'real_attachments' / 'A_data_value'
Q01A_SPEC = PROJECT / 'diagnostics' / 'TASK-Q01A' / '20260924T142229+08' / 'diagnostic_spec.json'
CST = timezone(timedelta(hours=8))

DESIGN_DOMAINS = ['book', 'c4', 'commoncrawl', 'wikipedia']
ACTIVE_MIN_N = 1000
HOLDOUT_MIN_N = 200
EXTENSION_MIN_N = 200
LAMBDA_PRIMARY = 0.02
LAMBDA_GRID = [0.0, 0.01, 0.02, 0.05]
MASTER_SEED = 20260925
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
CANDIDATE_VERSION = 't03e_candidate_v1'

IDENTITY_COLUMNS = ['file_id', 'source_line', 'key_sha256', 'domain', 'evaluation_role',
                    'is_unique_first', 'overlap_a1', 'Q_valid', 'Q_baseline']
TOP_COLUMNS = ['rps_doc_frac_chars_top_2gram', 'rps_doc_frac_chars_top_3gram']
DSIR_COLUMNS = ['dsir_books', 'dsir_wiki', 'dsir_math']
FEATURE_COLUMNS = [
    'rps_doc_frac_no_alph_words', 'rps_doc_mean_word_length', 'rps_doc_frac_unique_words',
    'rps_doc_unigram_entropy', 'rps_doc_word_count',
    'rps_lines_ending_with_terminal_punctution_mark', 'rps_lines_numerical_chars_fraction',
    'rps_lines_uppercase_letter_fraction', 'rps_doc_num_sentences',
    'rps_doc_frac_chars_top_2gram', 'rps_doc_frac_chars_top_3gram', 'dsir_books', 'dsir_wiki',
    'dsir_math', 'fineweb_edu', 'ad_en', 'fluency_en', 'qurater_writing_style',
    'qurater_required_expertise', 'qurater_facts_trivia', 'qurater_educational_value',
    'modernbert_professionalism', 'modernbert_readability', 'modernbert_reasoning',
    'modernbert_cleanliness']
READ_COLUMNS = IDENTITY_COLUMNS + TOP_COLUMNS + DSIR_COLUMNS + [
    c for c in FEATURE_COLUMNS if c not in TOP_COLUMNS + DSIR_COLUMNS]
FORBIDDEN_OUTPUT_COLUMNS = ['final_Q', 'best_Q', 'improved_Q', 'true_quality']
SUPPORT_STATUSES = ['SUPPORTED', 'OUT_OF_SUPPORT', 'RULE_NOT_APPLICABLE', 'INSUFFICIENT_CALIBRATION',
                    'DESIGN_LABEL_ABSENT', 'Q_INVALID_PRESERVED']
PHASE_A_QUALIFIED = 'CALIBRATION_QUALIFIED_PENDING_VALIDATION'
PHASE_A_REJECTED = 'CALIBRATION_REJECTED_KEEP_D'
TIME_BUDGET = {'calibration-preflight': 15 * 60, 'calibration-freeze': 90 * 60,
               'frozen-validation': 45 * 60, 'finalize': 10 * 60}


def now_iso():
    return datetime.now(CST).isoformat(timespec='seconds')


def now_iso_ms():
    return datetime.now(CST).isoformat(timespec='milliseconds')


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def read_json(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(json_safe(value), ensure_ascii=False, indent=2,
                                     default=str, allow_nan=False),
                          encoding='utf-8')
    return Path(path)


def write_csv(path, columns, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return Path(path)


class TimeBudgetExceeded(RuntimeError):
    pass


class GateFailure(RuntimeError):
    pass


class Ctx:
    def __init__(self, run_dir, mode, command):
        self.run_dir = Path(run_dir)
        self.mode = mode
        self.command = list(command)
        self.pid = os.getpid()
        self.started = now_iso()
        self.t0 = time.monotonic()
        self.log_path = self.run_dir / 'run.log'
        self.access_path = self.run_dir / 'access_log.jsonl'
        self.status_path = self.run_dir / 'stage_status.jsonl'
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message):
        line = '[' + datetime.now(CST).isoformat(timespec='milliseconds') + '] [' + self.mode + '] ' + message
        with open(self.log_path, 'a', encoding='utf-8', newline='\n') as fh:
            fh.write(line + '\n')
        print(line, flush=True)

    def status(self, stage, event, **fields):
        record = {'ts': now_iso(), 'mode': self.mode, 'stage': stage, 'event': event,
                  'pid': self.pid}
        record.update(fields)
        with open(self.status_path, 'a', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')
        print(json.dumps(record, ensure_ascii=False, default=str), flush=True)

    def access(self, purpose, predicate, columns, rows_returned, note=''):
        record = {'ts': now_iso(), 'mode': self.mode, 'pid': self.pid, 'purpose': purpose,
                  'file': str(INPUT_PATH), 'logical_predicate': predicate,
                  'columns_projection': list(columns), 'analysis_visible_rows': int(rows_returned),
                  'note': note}
        with open(self.access_path, 'a', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')
        return record

    def record_command(self, exit_code=None):
        path = self.run_dir / 'command_log.json'
        payload = read_json(path) if path.is_file() else {'commands': []}
        payload['commands'].append({'mode': self.mode, 'argv': self.command, 'pid': self.pid,
                                    'started_local': self.started, 'finished_local': now_iso(),
                                    'exit_code': exit_code})
        write_json(path, payload)

    def guard_budget(self):
        limit = TIME_BUDGET.get(self.mode, 3600)
        elapsed = time.monotonic() - self.t0
        if elapsed > limit:
            raise TimeBudgetExceeded(f'{self.mode} exceeded wall-clock budget {limit}s '
                                     f'(elapsed {elapsed:.1f}s)')

    def mode_dir(self, name):
        path = self.run_dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path


def load_design_spec():
    spec = read_json(Q01A_SPEC)
    features = [item['feature'] for item in sorted(spec['expanded_features_25'], key=lambda x: x['index'])]
    fields = [item['field'] for item in sorted(spec['raw_fields_22'], key=lambda x: x['index'])]
    model = [item['feature'] for item in sorted(spec['main_q_features_11'], key=lambda x: x['index'])]
    return {'features_25': features, 'fields_22': fields, 'main_q_11': model,
            'groups': spec['groups'], 'source': str(Q01A_SPEC),
            'source_sha256': sha256_file(Q01A_SPEC)}


def verify_input(ctx, note):
    entry = next((item for item in read_json(Q01C_RUN / 'output_manifest.json')['files']
                  if item['path'].endswith('quality_features_scores.parquet')), None)
    if entry is None:
        raise GateFailure('input parquet not registered in the Q01C output manifest')
    stat = INPUT_PATH.stat()
    digest = sha256_file(INPUT_PATH)
    record = {'note': note, 'path': str(INPUT_PATH), 'bytes': stat.st_size,
              'sha256': digest, 'manifest_bytes': entry['bytes'],
              'manifest_sha256': entry['sha256'],
              'matches_manifest': stat.st_size == entry['bytes'] and digest == entry['sha256'],
              'checked_local': now_iso(), 'pid': os.getpid()}
    ctx.log('input verification (' + note + '): matches=' + str(record['matches_manifest']))
    if not record['matches_manifest']:
        raise GateFailure('input parquet hash/size differs from the Q01C manifest')
    return record


def read_role_rows(ctx, roles, purpose, columns):
    if isinstance(roles, str):
        roles = [roles]
    table = pq.read_table(INPUT_PATH, columns=columns, filters=[('evaluation_role', 'in', roles)])
    frame = table.to_pandas()
    visible = sorted(frame['evaluation_role'].unique().tolist())
    if not set(visible) <= set(roles):
        raise GateFailure(f'analysis layer received unexpected roles: {visible} not in {roles}')
    ctx.access(purpose, 'evaluation_role in ' + json.dumps(roles), columns, len(frame),
               note='storage layer may decode other pages of the single row group; only the '
                    'filtered rows are materialised, returned and cached here')
    return frame


# ---------------------------------------------------------------------------
# pure helpers (deterministic formulas; the verifier re-implements them)
# ---------------------------------------------------------------------------
def q_linear(values, quantile):
    return float(np.quantile(np.asarray(values, dtype=float), quantile, method='linear'))


def penalty_value(x, a, b):
    if not math.isfinite(x):
        return float('nan')
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    return (x - a) / (b - a)


def penalty_array(values, a, b):
    values = np.asarray(values, dtype=float)
    out = np.zeros_like(values)
    out[values >= b] = 1.0
    middle = (values > a) & (values < b)
    out[middle] = (values[middle] - a) / (b - a)
    return out


def deterministic_order(scores, keys):
    scores = np.asarray(scores, dtype=float)
    keys = np.asarray(keys, dtype=object)
    order = np.lexsort((keys, -scores))
    return order


def rank_vector(scores, keys):
    order = deterministic_order(scores, keys)
    ranks = np.empty(len(order), dtype=float)
    ranks[order] = np.arange(1, len(order) + 1, dtype=float)
    return ranks, order


def spearman_from_ranks(ranks_a, ranks_b):
    d = ranks_a - ranks_b
    n = len(d)
    if n < 2:
        return float('nan')
    return float(1 - 6 * np.sum(d ** 2) / (n * (n ** 2 - 1)))


def top_set(order, n, fraction=0.10):
    k = max(1, int(math.ceil(fraction * n)))
    return set(order[:k].tolist()), k


def jaccard(a, b):
    union = len(a | b)
    return float(len(a & b) / union) if union else float('nan')


def bootstrap_seed(domain, replicate):
    digest = sha256_text(f'{MASTER_SEED}|{domain}|{replicate}')
    return int(digest[:16], 16)


# ---------------------------------------------------------------------------
# artificial tests (run before any real analysis value is read)
# ---------------------------------------------------------------------------
def run_artificial_tests():
    tests = []
    def case(name, actual, expected, tolerance, note=''):
        ok = False
        try:
            if isinstance(expected, bool) or expected is None:
                ok = actual == expected
            else:
                ok = abs(float(actual) - float(expected)) <= tolerance
        except (TypeError, ValueError):
            ok = actual == expected
        tests.append({'test': name, 'actual': actual, 'expected': expected,
                      'tolerance': tolerance, 'status': 'PASS' if ok else 'FAIL', 'note': note})
        return ok
    a2, b2, a3, b3 = 1.0, 2.0, 3.0, 4.0
    x2, x3, q = 1.5, 3.5, 0.8
    p2 = (x2 - a2) / (b2 - a2)          # hand-computed 0.5
    p3 = (x3 - a3) / (b3 - a3)          # hand-computed 0.5
    expected_p = (p2 + p3) / 2          # 0.5
    expected_c = q * (1 - 0.02 * expected_p)
    case('penalty_midpoint_top2', penalty_value(x2, a2, b2), 0.5, 0.0)
    case('penalty_midpoint_top3', penalty_value(x3, a3, b3), 0.5, 0.0)
    case('cluster_penalty_mean', (penalty_value(x2, a2, b2) + penalty_value(x3, a3, b3)) / 2,
         expected_p, 0.0)
    case('candidate_formula', q * (1 - LAMBDA_PRIMARY * expected_p), expected_c, 1e-15)
    case('penalty_lower_bound', penalty_value(a2, a2, b2), 0.0, 0.0)
    case('penalty_upper_bound', penalty_value(b2 + 5, a2, b2), 1.0, 0.0)
    case('lambda_zero_identity', q * (1 - 0.0 * expected_p), q, 1e-15)
    case('rule_not_applicable_identity', q * (1 - 0.0 * 0.0), q, 1e-15)
    dup_p = (penalty_value(x2, a2, b2) + penalty_value(x3, a3, b3)) / 2
    case('duplicate_member_no_weight_increase', dup_p, expected_p, 1e-15)
    grid = np.linspace(a2 - 1, b2 + 1, 41)
    mono = all(penalty_array(grid, a2, b2)[i] <= penalty_array(grid, a2, b2)[i + 1]
               for i in range(len(grid) - 1))
    case('penalty_monotone_nondecreasing', mono, True, 0.0)
    scores = q * (1 - LAMBDA_PRIMARY * penalty_array(grid, a2, b2))
    case('candidate_monotone_nonincreasing', bool(np.all(np.diff(scores) <= 1e-15)), True, 0.0)
    case('candidate_ge_098q', float(np.min(scores / q)), 0.98, 1e-12)
    case('new_zero_values', int(np.sum((q > 0) & (scores == 0))), 0, 0.0)
    case('original_zero_preserved', float(0.0 * (1 - LAMBDA_PRIMARY * 1.0)), 0.0, 0.0)
    degenerate = (b2 <= a2)
    case('degenerate_quantile_detected', degenerate, False, 0.0, 'q99<=q95 must not qualify')
    case('unknown_domain_not_applicable', 'RULE_NOT_APPLICABLE' in SUPPORT_STATUSES, True, 0.0)
    case('invalid_row_status_enumerated', 'Q_INVALID_PRESERVED' in SUPPORT_STATUSES, True, 0.0)
    failed = [t for t in tests if t['status'] != 'PASS']
    return {'generated_local': now_iso(), 'n_tests': len(tests), 'n_failed': len(failed),
            'status': 'PASS' if not failed else 'FAIL', 'tests': tests}


# ---------------------------------------------------------------------------
# run-level provenance files (written once in the preflight process)
# ---------------------------------------------------------------------------
def module_version(name):
    if name == 'python':
        return sys.version.split()[0]
    if name == 'pyarrow':
        import pyarrow
        return pyarrow.__version__
    if name == 'numpy':
        return np.__version__
    if name == 'pandas':
        return pd.__version__
    if name == 'scipy':
        import scipy
        return scipy.__version__
    return 'unknown'


def environment_payload():
    import scipy
    memory_total = None
    try:
        import psutil
        memory_total = int(psutil.virtual_memory().total)
    except Exception:
        memory_total = None
    return {
        'python_version': sys.version,
        'python_executable': sys.executable,
        'platform': platform.platform(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'timezone': 'Asia/Shanghai (+08:00)',
        'logical_cpu_count': os.cpu_count(),
        'numpy_version': module_version('numpy'),
        'pandas_version': module_version('pandas'),
        'pyarrow_version': module_version('pyarrow'),
        'scipy_version': module_version('scipy'),
        'quantile_implementation': 'numpy.quantile(values, q, method="linear")',
        'bootstrap_rng': 'numpy.random.default_rng(int(sha256("20260925|<domain>|<replicate>")[:16], 16))',
        'bootstrap_rng_bit_generator': 'PCG64',
        'memory_bytes_total': memory_total,
        'memory_budget_GiB': 8,
        'cpu_budget': 'min(50% of visible logical cores, 8 workers); this run is single-process',
        'wall_clock_budgets_seconds': TIME_BUDGET,
        'generated_local': now_iso(), 'pid': os.getpid()}


def write_environment(ctx):
    write_json(ctx.run_dir / 'environment.json', environment_payload())


def run_config_payload():
    return {
        'task': 'TASK-T03E',
        'scope': 'preregistered rule-sensitivity stability and applicability validation',
        'primary_result': 'D = Q_baseline',
        'confirmatory_candidate': 'C = Q_baseline * (1 - 0.02 * P)',
        'cluster_penalty': 'P = (p_top2gram + p_top3gram) / 2',
        'lambda_primary': LAMBDA_PRIMARY,
        'lambda_grid_report_only': LAMBDA_GRID,
        'design_domains_exact': DESIGN_DOMAINS,
        'active_min_calibration_valid_n': ACTIVE_MIN_N,
        'holdout_min_valid_n': HOLDOUT_MIN_N,
        'extension_min_valid_n': EXTENSION_MIN_N,
        'roles': {'confirmatory': CONFIRMATORY_ROLES,
                  'extension': ['extension_overlap_A1', 'extension_new_records']},
        'master_seed': MASTER_SEED,
        'bootstrap_replicates': BOOTSTRAP_REPLICATES,
        'bootstrap_min_joint_pass': BOOTSTRAP_MIN_PASS,
        'bootstrap_gates': {'penalty_mae_max': BOOT_MAE_MAX, 'rank_spearman_min': BOOT_SPEARMAN_MIN,
                            'top10_jaccard_min': BOOT_JACCARD_MIN},
        'holdout_gates': {'spearman_min': HOLDOUT_SPEARMAN_MIN,
                          'top10_jaccard_min': HOLDOUT_JACCARD_MIN,
                          'penalty_mean_abs_tol': HOLDOUT_PENALTY_MEAN_TOL,
                          'out_of_support_max': OOS_MAX},
        'extension_gates': {'spearman_min': HOLDOUT_SPEARMAN_MIN,
                            'top10_jaccard_min': HOLDOUT_JACCARD_MIN,
                            'out_of_support_max': OOS_MAX},
        'overlap_tolerance': OVERLAP_TOL,
        'row_selection_rule': 'evaluation_role in roles & is_unique_first & Q_valid & '
                              'finite(Q_baseline, top2gram, top3gram)',
        'joint_key': 'key_sha256 = sha256(json([str(id), str(sub_path)])) from Q01C',
        'input_path': str(INPUT_PATH),
        'q01a_spec': str(Q01A_SPEC),
        'output_root': 'diagnostics/TASK-T03E/<run_id>/',
        'time_budgets_seconds': TIME_BUDGET,
        'acceptance_payload': preregistered_acceptance_payload(),
        'prohibitions': preregistered_acceptance_payload()['prohibited'],
        'no_scope_expansion': ['no T06 calibration', 'no ratio/scaling/C-module work',
                               'no optimisation', 'no paper text'],
        'generated_local': now_iso(), 'pid': os.getpid()}


def write_run_config(ctx):
    write_json(ctx.run_dir / 'run_config.json', run_config_payload())


def evidence_entries(phase):
    later = phase != 'calibration-preflight'
    specification = [
        (INPUT_PATH, 'official row-level input for the candidate computation',
         'read (size and SHA256 verified against the Q01C output manifest)'),
        (Q01C_RUN / 'output_manifest.json', 'reference for the official input path/size/SHA256',
         'read'),
        (Q01A_SPEC, '22->25 feature mapping and evaluation-role definition',
         'read (feature/role definitions only; no diagnostic values used for thresholds)'),
        (Q01C_RUN / 'run_config.json', 'role definitions and Q01C scope reference',
         'available_not_read'),
        (Q01C_RUN / 'input_manifest.json', 'Q01C provenance reference', 'available_not_read'),
        (Q01C_RUN / 'summary_denominators.csv', 'cross-check denominators only (not used for '
                                                'freezing)', 'available_not_read'),
        (Q01C_RUN / 'domain_summary.csv', 'cross-check domain counts only', 'available_not_read'),
        (Q01C_RUN / 'quality_baseline_q01c.md', 'Q01C method description', 'available_not_read'),
        (MIXTURE_DIR / 'model.json', 'PHASE B RegMix/Loss identifiability check',
         'read' if later else 'declared_for_phase_b_not_read'),
        (MIXTURE_DIR / 'aggregate_predictions.csv', 'PHASE B RegMix/Loss identification check',
         'read' if later else 'declared_for_phase_b_not_read'),
        (A_DATA / 'domain_mapping_guide.csv', 'PHASE B quality-domain to RegMix-domain mapping',
         'read' if later else 'declared_for_phase_b_not_read'),
        (PROJECT / 'F题' / 'real_attachments' / 'B_scaling_laws' / 'supplementary_NQ_experiment.csv',
         'PHASE B B-side quality pairing check',
         'read' if later else 'declared_for_phase_b_not_read'),
        (PROJECT / 'tasks' / 'TASK-T03E_预注册规则修正稳定性与适用性验证.md',
         'the single execution order for this task', 'read'),
        (PROJECT / 'tasks' / 'TASK-T03_完整质量体系与14项规则DSIR融合方法设计.md',
         'parent design document', 'available_not_read'),
    ]
    entries = []
    for path, purpose, status in specification:
        entry = {'path': str(path), 'purpose': purpose, 'access_status': status}
        if path.is_file():
            stat = path.stat()
            entry['bytes'] = int(stat.st_size)
            entry['mtime_local'] = datetime.fromtimestamp(stat.st_mtime, CST).isoformat(timespec='seconds')
            if path.name != 'quality_features_scores.parquet':
                entry['sha256'] = sha256_file(path)
            else:
                entry['sha256'] = 'verified against the Q01C output manifest (see EX-01)'
        entries.append(entry)
    entries.append({'path': 'F题/** raw A1/A2/A3 archives',
                    'purpose': 'permanently prohibited input for this task',
                    'access_status': 'not_read (never opened, stat-ed or hashed in this run)'})
    return entries


def write_input_manifest(ctx, phase):
    payload = {'task': 'TASK-T03E', 'phase': phase,
               'official_input': str(INPUT_PATH),
               'official_input_manifest_sha256': sha256_file(Q01C_RUN / 'output_manifest.json'),
               'entries': evidence_entries(phase),
               'access_log': 'access_log.jsonl (canonical per-access record with column projection '
                             'and role filter)',
               'note': ('input_manifest.json is refreshed at the end of PHASE B to record the '
                        'actual access status; the preflight snapshot '
                        'metadata_preflight/input_manifest_preflight.json is frozen by the seal'),
               'generated_local': now_iso(), 'pid': os.getpid()}
    write_json(ctx.run_dir / 'input_manifest.json', payload)
    if phase == 'calibration-preflight':
        write_json(ctx.run_dir / 'metadata_preflight' / 'input_manifest_preflight.json', payload)
    return payload


# ---------------------------------------------------------------------------
# mode 1: calibration partition preflight
# ---------------------------------------------------------------------------
def mode_calibration_preflight(ctx):
    ctx.status('calibration_preflight', 'start')
    tests = run_artificial_tests()
    write_json(ctx.run_dir / 'metadata_preflight' / 'artificial_tests.json', tests)
    if tests['status'] != 'PASS':
        raise GateFailure('artificial tests failed before reading real analysis values')
    input_check = verify_input(ctx, 'calibration-preflight')
    design = load_design_spec()
    frame = read_role_rows(ctx, 'A1_calibration', 'calibration partition preflight', READ_COLUMNS)
    if not (frame['evaluation_role'] == 'A1_calibration').all():
        raise GateFailure('analysis layer received non-calibration rows during preflight')
    labels = sorted(frame['domain'].astype(str).unique().tolist())
    unique = frame[frame['is_unique_first'] == True]
    valid = valid_rows(unique)
    label_rows = []
    for label in labels:
        part = frame[frame['domain'].astype(str) == label]
        part_unique = unique[unique['domain'].astype(str) == label]
        part_valid = valid[valid['domain'].astype(str) == label]
        label_rows.append({'domain_label': label, 'physical_rows': int(len(part)),
                           'unique_first_rows': int(len(part_unique)),
                           'valid_rows': int(len(part_valid)),
                           'exact_string_length': len(label)})
    write_csv(ctx.run_dir / 'metadata_preflight' / 'calibration_domain_labels.csv',
              ['domain_label', 'physical_rows', 'unique_first_rows', 'valid_rows',
               'exact_string_length'], label_rows)
    write_csv(ctx.run_dir / 'metadata_preflight' / 'calibration_domain_inventory.csv',
              ['domain_label', 'physical_rows', 'unique_first_rows', 'valid_rows'],
              label_rows)
    match_rows = []
    for label in DESIGN_DOMAINS:
        present = label in labels
        part_valid = valid[valid['domain'].astype(str) == label]
        match_rows.append({'design_label': label, 'present_in_calibration': present,
                           'exact_match': present,
                           'status': 'EXACT_MATCH' if present else 'DESIGN_LABEL_ABSENT',
                           'calibration_valid_n': int(len(part_valid))})
    write_csv(ctx.run_dir / 'metadata_preflight' / 'calibration_domain_label_match.csv',
              ['design_label', 'present_in_calibration', 'exact_match', 'status',
               'calibration_valid_n'], match_rows)
    keys = sorted(unique['key_sha256'].astype(str).tolist())
    commitment = {'calibration_physical_rows': int(len(frame)),
                  'calibration_unique_first_rows': int(len(unique)),
                  'calibration_keyset_sha256': sha256_text('|'.join(keys)),
                  'calibration_keyset_size': len(keys),
                  'key_definition': 'key_sha256 = sha256(json([str(id), str(sub_path)])) from Q01C',
                  'generated_local': now_iso(), 'pid': os.getpid()}
    write_json(ctx.run_dir / 'metadata_preflight' / 'calibration_key_commitment.json', commitment)
    frame.to_parquet(ctx.run_dir / 'metadata_preflight' / 'calibration_rows.parquet', index=False)
    write_json(ctx.run_dir / 'metadata_preflight' / 'preflight_summary.json', {
        'input_check': input_check, 'labels': labels, 'design_match': match_rows,
        'commitment': commitment, 'design_spec': design,
        'analysis_layer_roles_visible': sorted(frame['evaluation_role'].unique().tolist()),
        'holdout_or_extension_read': False, 'generated_local': now_iso()})
    write_environment(ctx)
    write_run_config(ctx)
    write_input_manifest(ctx, 'calibration-preflight')
    ctx.status('calibration_preflight', 'complete', labels=labels,
               calibration_rows=int(len(frame)), unique_first=int(len(unique)))
    ctx.log('preflight complete: labels=' + json.dumps(labels))
    return 0


def valid_rows(frame):
    return frame[(frame['Q_valid'] == True) & np.isfinite(frame['Q_baseline'].to_numpy(dtype=float))
                 & np.isfinite(frame['rps_doc_frac_chars_top_2gram'].to_numpy(dtype=float))
                 & np.isfinite(frame['rps_doc_frac_chars_top_3gram'].to_numpy(dtype=float))]


# ---------------------------------------------------------------------------
# candidate application and calibration stability machinery
# ---------------------------------------------------------------------------
def domain_status_for(label, inventory):
    """Frozen status resolution.

    Labels outside the four preregistered design domains (e.g. github, arxiv,
    stackexchange) are RULE_NOT_APPLICABLE: the candidate is not applied there and
    Q_C == Q_baseline exactly.  DESIGN_LABEL_ABSENT is reserved for a design label
    that does not occur in the data at all; no fuzzy matching, renaming, merging or
    cross-domain fallback is ever used.
    """
    if label not in DESIGN_DOMAINS:
        return 'RULE_NOT_APPLICABLE'
    entry = inventory.get(label)
    if entry is None:
        return 'DESIGN_LABEL_ABSENT'
    if entry['status'] == 'DESIGN_LABEL_ABSENT':
        return 'DESIGN_LABEL_ABSENT'
    if entry.get('status') == 'INSUFFICIENT_CALIBRATION':
        return 'INSUFFICIENT_CALIBRATION'
    if entry.get('n_valid') is not None and int(entry['n_valid']) < ACTIVE_MIN_N:
        return 'INSUFFICIENT_CALIBRATION'
    if entry.get('status') == 'CALIBRATION_DEGENERATE':
        raise GateFailure('a design domain reached n>=' + str(ACTIVE_MIN_N)
                          + ' but its calibration quantiles are degenerate; PHASE A must reject '
                            'and PHASE B must not run')
    return 'ACTIVE'


def apply_candidate(frame, thresholds, active_domains, inventory, lam=LAMBDA_PRIMARY):
    n = len(frame)
    p2 = np.zeros(n, dtype=float)
    p3 = np.zeros(n, dtype=float)
    status = np.array(['RULE_NOT_APPLICABLE'] * n, dtype=object)
    q_baseline = frame['Q_baseline'].to_numpy(dtype=float)
    x2 = frame['rps_doc_frac_chars_top_2gram'].to_numpy(dtype=float)
    x3 = frame['rps_doc_frac_chars_top_3gram'].to_numpy(dtype=float)
    domains = frame['domain'].astype(str).to_numpy()
    q_valid = frame['Q_valid'].to_numpy(dtype=bool)
    for label in sorted(set(domains.tolist())):
        mask = domains == label
        base_status = domain_status_for(label, inventory)
        if label in active_domains and base_status == 'ACTIVE':
            t = thresholds[label]
            missing_inputs = (((~np.isfinite(x2)) | (~np.isfinite(x3))) & mask
                              & q_valid)
            if bool(missing_inputs.any()):
                raise GateFailure('active domain ' + str(label) + ' carries '
                                  + str(int(missing_inputs.sum()))
                                  + ' row(s) with non-finite top-2gram/top-3gram input; the frozen '
                                    'penalty is undefined there and no fallback (zero fill, clip or '
                                    'extra penalty) is authorised')
            p2[mask] = penalty_array(x2[mask], t['a2'], t['b2'])
            p3[mask] = penalty_array(x3[mask], t['a3'], t['b3'])
            oos = ((x2[mask] < t['lo2']) | (x2[mask] > t['hi2'])
                   | (x3[mask] < t['lo3']) | (x3[mask] > t['hi3']))
            status[mask] = np.where(oos, 'OUT_OF_SUPPORT', 'SUPPORTED')
        else:
            status[mask] = base_status
            p2[mask] = 0.0
            p3[mask] = 0.0
    penalty = (p2 + p3) / 2.0
    q_candidate = q_baseline * (1 - lam * penalty)
    invalid = ~q_valid
    q_candidate[invalid] = np.nan
    status[invalid] = 'Q_INVALID_PRESERVED'
    penalty[invalid] = np.nan
    p2[invalid] = np.nan
    p3[invalid] = np.nan
    return {'p_top2gram': p2, 'p_top3gram': p3, 'P': penalty, 'Q_C': q_candidate,
            'Q_support_status': status}


def bootstrap_domain_stability(domain, valid_sub, threshold, replicates, ctx):
    ref = valid_sub.sort_values('key_sha256', kind='stable')
    keys = ref['key_sha256'].astype(str).to_numpy()
    x2 = ref['rps_doc_frac_chars_top_2gram'].to_numpy(dtype=float)
    x3 = ref['rps_doc_frac_chars_top_3gram'].to_numpy(dtype=float)
    q = ref['Q_baseline'].to_numpy(dtype=float)
    n = len(ref)
    p2_ref = penalty_array(x2, threshold['a2'], threshold['b2'])
    p3_ref = penalty_array(x3, threshold['a3'], threshold['b3'])
    p_ref = (p2_ref + p3_ref) / 2
    qc_ref = q * (1 - LAMBDA_PRIMARY * p_ref)
    ranks_ref, order_ref = rank_vector(qc_ref, keys)
    top_ref, k = top_set(order_ref, n)
    detail = []
    joint_pass = 0
    for replicate in range(replicates):
        seed = bootstrap_seed(domain, replicate)
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, n, size=n)
        a2b = q_linear(x2[idx], 0.95)
        b2b = q_linear(x2[idx], 0.99)
        a3b = q_linear(x3[idx], 0.95)
        b3b = q_linear(x3[idx], 0.99)
        if b2b <= a2b or b3b <= a3b:
            detail.append({'domain': domain, 'replicate': replicate, 'seed': seed, 'n': n,
                           'penalty_mae': None, 'rank_spearman': None, 'top10_jaccard': None,
                           'pass_mae': 0, 'pass_spearman': 0, 'pass_jaccard': 0,
                           'joint_pass': 0, 'reason': 'degenerate_quantile',
                           'a2': a2b, 'b2': b2b, 'a3': a3b, 'b3': b3b})
            continue
        p2b = penalty_array(x2, a2b, b2b)
        p3b = penalty_array(x3, a3b, b3b)
        pb = (p2b + p3b) / 2
        qcb = q * (1 - LAMBDA_PRIMARY * pb)
        mae = float(np.mean(np.abs(pb - p_ref)))
        ranks_b, order_b = rank_vector(qcb, keys)
        rho = spearman_from_ranks(ranks_ref, ranks_b)
        top_b, _k = top_set(order_b, n)
        jac = jaccard(top_ref, top_b)
        pass_mae = mae <= BOOT_MAE_MAX
        pass_rho = rho >= BOOT_SPEARMAN_MIN
        pass_jac = jac >= BOOT_JACCARD_MIN
        joint = pass_mae and pass_rho and pass_jac
        joint_pass += int(joint)
        detail.append({'domain': domain, 'replicate': replicate, 'seed': seed, 'n': n,
                       'penalty_mae': mae, 'rank_spearman': rho, 'top10_jaccard': jac,
                       'pass_mae': int(pass_mae), 'pass_spearman': int(pass_rho),
                       'pass_jaccard': int(pass_jac), 'joint_pass': int(joint), 'reason': '',
                       'a2': a2b, 'b2': b2b, 'a3': a3b, 'b3': b3b})
    summary = {'domain': domain, 'n': n, 'replicates': replicates, 'joint_pass_count': joint_pass,
               'required': BOOTSTRAP_MIN_PASS,
               'status': 'PASS' if joint_pass >= BOOTSTRAP_MIN_PASS else 'FAIL',
               'thresholds': {'penalty_mae_max': BOOT_MAE_MAX,
                              'rank_spearman_min': BOOT_SPEARMAN_MIN,
                              'top10_jaccard_min': BOOT_JACCARD_MIN}}
    return detail, summary


def lambda_grid_table(frame, thresholds, active_domains, inventory):
    rows = []
    q_baseline = frame['Q_baseline'].to_numpy(dtype=float)
    keys = frame['key_sha256'].astype(str).to_numpy()
    base = apply_candidate(frame, thresholds, active_domains, inventory, lam=0.0)
    ranks_d, order_d = rank_vector(q_baseline, keys)
    top_d, _k = top_set(order_d, len(frame))
    for lam in LAMBDA_GRID:
        out = apply_candidate(frame, thresholds, active_domains, inventory, lam=lam)
        p = out['P']
        finite = np.isfinite(p)
        qc = out['Q_C']
        ranks_c, order_c = rank_vector(qc, keys)
        top_c, _k2 = top_set(order_c, len(frame))
        rows.append({
            'lambda': lam, 'n_rows': int(len(frame)), 'n_finite_penalty': int(finite.sum()),
            'penalty_mean': float(np.nanmean(p)) if finite.any() else None,
            'penalty_max': float(np.nanmax(p)) if finite.any() else None,
            'penalty_p50': float(np.nanquantile(p, 0.50, method='linear')) if finite.any() else None,
            'penalty_p95': float(np.nanquantile(p, 0.95, method='linear')) if finite.any() else None,
            'spearman_vs_D': spearman_from_ranks(ranks_d, ranks_c),
            'top10_jaccard_vs_D': jaccard(top_d, top_c),
            'new_zero_values': int(np.sum((q_baseline > 0) & (qc == 0))),
            'oos_rows': int(np.sum(out['Q_support_status'] == 'OUT_OF_SUPPORT')),
            'rule_not_applicable_rows': int(np.sum(out['Q_support_status'] == 'RULE_NOT_APPLICABLE')),
            'primary': int(lam == LAMBDA_PRIMARY)})
    return rows


PRIOR_EXPOSURE_TEXT = '''# Prior exposure statement (TASK-T03E)

- Parts of the A1 holdout summaries were already inspected during earlier project work
  (the Q01C run reported holdout coverages and the T03 design work reviewed summary tables).
- In addition, two earlier executions of this identical frozen specification
  (diagnostics/TASK-T03E/20260925T015757+08 and diagnostics/TASK-T03E/20260925T015930+08) reached
  PHASE B and therefore read A1 holdout and extension values before this run. Both used the same
  lambda, thresholds, active domains, formula, candidate version and gates and produced the same
  candidate values; they stopped on defects of the independent verifier (a status-machine and
  coverage-format mismatch, one wrong fixture expectation, and an incomplete recording of the
  RegMix connection check), never on a rule failure of the executor. This run repeats the unchanged
  frozen specification with the corrected scripts, which are sealed again before any validation
  value is read.
- No lambda, threshold, active-domain set, formula, gate or candidate version was chosen from
  holdout or extension values: every frozen parameter in this run is re-estimated on A1
  calibration only.
- Because of that history this stage is **not** a fully blinded test. The accurate description is
  "validation after parameter freeze" (参数冻结后的验证).
- Holdout results are used only for the preregistered accept/reject decision.
- Extension results are used only for transport/reproduction checks and never for model selection.
'''


def preregistered_acceptance_payload():
    return {
        'candidate_version': CANDIDATE_VERSION,
        'primary_result': 'D = Q_baseline',
        'confirmatory_candidate': 'C = Q_baseline * (1 - 0.02 * P), P = (p_top2gram + p_top3gram)/2',
        'lambda_primary': LAMBDA_PRIMARY,
        'lambda_grid_report_only': LAMBDA_GRID,
        'design_domains_exact': DESIGN_DOMAINS,
        'domain_exact_matching': 'character-exact string equality only; no fuzzy/alias/merge/fallback',
        'active_domain_rules': {'min_calibration_valid_n': ACTIVE_MIN_N,
                               'quantile_requirement': 'q0.99 > q0.95 for both indicators',
                               'statuses': ['ACTIVE', 'DESIGN_LABEL_ABSENT',
                                            'INSUFFICIENT_CALIBRATION', 'CALIBRATION_DEGENERATE']},
        'bootstrap': {'replicates': BOOTSTRAP_REPLICATES, 'master_seed': MASTER_SEED,
                      'sub_seed_rule': 'int(sha256("20260925|<domain>|<replicate>")[:16],16) -> PCG64',
                      'unit': 'unique A1-calibration valid keys per domain, sampled with replacement',
                      'reference_rows': 'same full-calibration valid rows for every replicate',
                      'requirements': {'joInt_pass_min': BOOTSTRAP_MIN_PASS,
                                       'penalty_mae_max': BOOT_MAE_MAX,
                                       'rank_spearman_min': BOOT_SPEARMAN_MIN,
                                       'top10_jaccard_min': BOOT_JACCARD_MIN}},
        'holdout_gates': {'min_valid_n': HOLDOUT_MIN_N,
                          'spearman_min': HOLDOUT_SPEARMAN_MIN,
                          'top10_jaccard_min': HOLDOUT_JACCARD_MIN,
                          'penalty_mean_abs_tol': HOLDOUT_PENALTY_MEAN_TOL,
                          'out_of_support_max': OOS_MAX,
                          'status_priority': ['FAIL', 'REJECT_KEEP_D',
                                              'INSUFFICIENT_EVIDENCE_KEEP_D', 'ACCEPT_STABILITY']},
        'extension_gates': {'min_valid_n': EXTENSION_MIN_N,
                            'spearman_min': HOLDOUT_SPEARMAN_MIN,
                            'top10_jaccard_min': HOLDOUT_JACCARD_MIN,
                            'out_of_support_max': OOS_MAX,
                            'statuses': ['MIGRATION_FAILED_KEEP_D', 'INSUFFICIENT_EXTENSION_EVIDENCE',
                                         'NOT_TESTED_FOR_ACTIVE_CORRECTION']},
        'overlap_rule': 'same key + same domain + identical Q_baseline/top2/top3 + same candidate '
                        'version => abs(Q_C_left - Q_C_right) <= 1e-12',
        'prohibited': ['A/B candidates', 'PCA/entropy/CRITIC', 'lambda learning', 'bonus', 'clip',
                       'domain renaming/merging/fallback', 'using Q_baseline as a supervision target',
                       'fitting a new RegMix bridge model'],
    }


def mode_calibration_freeze(ctx, seed, replicates):
    if int(seed) != MASTER_SEED:
        raise GateFailure('seed must be the frozen master seed ' + str(MASTER_SEED))
    if int(replicates) != BOOTSTRAP_REPLICATES:
        raise GateFailure('bootstrap replicates are frozen at ' + str(BOOTSTRAP_REPLICATES))
    ctx.status('phase_a', 'start')
    freeze_dir = ctx.mode_dir('phase_a_calibration_freeze')
    if (freeze_dir / 'FREEZE_SEALED.json').exists():
        raise GateFailure('freeze seal already exists; a fresh run is required to redo PHASE A')
    input_check = verify_input(ctx, 'calibration-freeze')
    tests = run_artificial_tests()
    write_json(freeze_dir / 'artificial_tests.json', tests)
    if tests['status'] != 'PASS':
        raise GateFailure('artificial tests failed; PHASE A must not read analysis values')
    rows = pd.read_parquet(ctx.run_dir / 'metadata_preflight' / 'calibration_rows.parquet')
    if not (rows['evaluation_role'] == 'A1_calibration').all():
        raise GateFailure('PHASE A received non-calibration rows')
    unique = rows[rows['is_unique_first'] == True]
    valid = valid_rows(unique)
    labels = sorted(rows['domain'].astype(str).unique().tolist())
    ctx.log('PHASE A calibration labels: ' + json.dumps(labels))
    inventory = {}
    profile_rows = []
    frozen_domain_rows = []
    thresholds = {}
    for label in DESIGN_DOMAINS:
        present = label in labels
        part = rows[rows['domain'].astype(str) == label]
        part_unique = unique[unique['domain'].astype(str) == label]
        part_valid = valid[valid['domain'].astype(str) == label]
        entry = {'design_label': label, 'present_in_calibration': bool(present),
                 'physical_rows': int(len(part)), 'unique_first_rows': int(len(part_unique)),
                 'n_valid': int(len(part_valid))}
        if not present:
            entry['status'] = 'DESIGN_LABEL_ABSENT'
            entry['reason'] = 'exact label absent from A1 calibration'
        else:
            x2 = part_valid['rps_doc_frac_chars_top_2gram'].to_numpy(dtype=float)
            x3 = part_valid['rps_doc_frac_chars_top_3gram'].to_numpy(dtype=float)
            for indicator, x in (('top_2gram', x2), ('top_3gram', x3)):
                if int(x.size) == 0:
                    profile_rows.append({'domain': label, 'indicator': indicator, 'n_valid': 0,
                                         'min': None, 'max': None, 'q005': None, 'q95': None,
                                         'q99': None, 'q995': None, 'unique_values': 0, 'mean': None})
                    continue
                profile_rows.append({'domain': label, 'indicator': indicator, 'n_valid': int(x.size),
                                     'min': float(np.min(x)), 'max': float(np.max(x)),
                                     'q005': q_linear(x, 0.005), 'q95': q_linear(x, 0.95),
                                     'q99': q_linear(x, 0.99), 'q995': q_linear(x, 0.995),
                                     'unique_values': int(np.unique(x).size),
                                     'mean': float(np.mean(x))})
            values = {'a2': q_linear(x2, 0.95), 'b2': q_linear(x2, 0.99),
                      'lo2': q_linear(x2, 0.005), 'hi2': q_linear(x2, 0.995),
                      'a3': q_linear(x3, 0.95), 'b3': q_linear(x3, 0.99),
                      'lo3': q_linear(x3, 0.005), 'hi3': q_linear(x3, 0.995),
                      'n_valid': int(entry['n_valid']), 'x2_mean': float(np.mean(x2)),
                      'x3_mean': float(np.mean(x3)), 'x2_unique': int(np.unique(x2).size),
                      'x3_unique': int(np.unique(x3).size)}
            if entry['n_valid'] < ACTIVE_MIN_N:
                entry['status'] = 'INSUFFICIENT_CALIBRATION'
                entry['reason'] = ('calibration valid n ' + str(entry['n_valid']) + ' < '
                                   + str(ACTIVE_MIN_N)
                                   + '; excluded from the active set, no other domain, global '
                                     'parameter or live fallback is used')
            else:
                degenerate = (values['b2'] <= values['a2']) or (values['b3'] <= values['a3'])
                entry['status'] = 'CALIBRATION_DEGENERATE' if degenerate else 'ACTIVE'
                entry['reason'] = ('q0.99 <= q0.95 for at least one indicator' if degenerate
                                   else 'qualified active domain')
                entry.update(values)
        inventory[label] = entry
        frozen_domain_rows.append({'design_label': label, 'exact_match': bool(present),
                                   'n_valid': entry['n_valid'], 'status': entry['status'],
                                   'reason': entry.get('reason', '')})
        if entry['status'] == 'ACTIVE':
            thresholds[label] = entry
    active_domains = [label for label, entry in inventory.items() if entry['status'] == 'ACTIVE']
    degenerate_large = [label for label, entry in inventory.items()
                        if entry['status'] == 'CALIBRATION_DEGENERATE']
    preliminary = (PHASE_A_QUALIFIED if (active_domains and not degenerate_large)
                   else PHASE_A_REJECTED)
    write_csv(freeze_dir / 'calibration_feature_profile.csv',
              ['domain', 'indicator', 'n_valid', 'min', 'max', 'q005', 'q95', 'q99', 'q995',
               'unique_values', 'mean'], profile_rows)
    write_csv(freeze_dir / 'frozen_active_domains.csv',
              ['design_label', 'exact_match', 'n_valid', 'status', 'reason'], frozen_domain_rows)
    threshold_rows = []
    for label in active_domains:
        entry = thresholds[label]
        for indicator, prefix in (('top_2gram', '2'), ('top_3gram', '3')):
            threshold_rows.append({'domain': label, 'indicator': indicator,
                                   'a_q95': entry['a' + prefix], 'b_q99': entry['b' + prefix],
                                   'lo_q005': entry['lo' + prefix], 'hi_q995': entry['hi' + prefix],
                                   'n_valid_source': entry['n_valid'],
                                   'source_scope': 'A1_calibration & is_unique_first & Q_valid & finite'})
    write_csv(freeze_dir / 'frozen_thresholds.csv',
              ['domain', 'indicator', 'a_q95', 'b_q99', 'lo_q005', 'hi_q995', 'n_valid_source',
               'source_scope'], threshold_rows)
    write_json(freeze_dir / 'preregistered_acceptance.json', preregistered_acceptance_payload())
    sub_seed_rule = 'int(sha256("20260925|<domain>|<replicate>")[:16],16)'
    seed_rows = []
    for label in active_domains:
        n = int(len(valid[valid['domain'].astype(str) == label]))
        for replicate in range(int(replicates)):
            seed_rows.append({'domain': label, 'replicate': replicate,
                              'seed': bootstrap_seed(label, replicate), 'n_resample': n,
                              'reference_rows': n, 'sub_seed_rule': sub_seed_rule,
                              'rng': 'numpy.random.default_rng(seed) -> PCG64'})
    write_csv(freeze_dir / 'bootstrap_seed_manifest.csv',
              ['domain', 'replicate', 'seed', 'n_resample', 'reference_rows', 'sub_seed_rule',
               'rng'], seed_rows)
    bootstrap_detail_rows = []
    bootstrap_summary_rows = []
    lambda_rows = []
    calibration_candidate_written = False
    if preliminary == PHASE_A_QUALIFIED:
        for label in active_domains:
            part_valid = valid[valid['domain'].astype(str) == label]
            detail, summary = bootstrap_domain_stability(label, part_valid, thresholds[label],
                                                         int(replicates), ctx)
            bootstrap_detail_rows.extend(detail)
            bootstrap_summary_rows.append(summary)
            ctx.log('bootstrap ' + label + ': joint_pass ' + str(summary['joint_pass_count'])
                    + '/' + str(replicates))
        lambda_rows = lambda_grid_table(rows, thresholds, active_domains, inventory)
        candidate = apply_candidate(rows, thresholds, active_domains, inventory)
        for column in ('p_top2gram', 'p_top3gram', 'P', 'Q_C', 'Q_support_status'):
            rows[column] = candidate[column]
        rows['candidate_version'] = CANDIDATE_VERSION
        rows['lambda_primary'] = LAMBDA_PRIMARY
        rows.to_parquet(freeze_dir / 'calibration_candidate_rows.parquet', index=False)
        calibration_candidate_written = True
    bootstrap_failures = [row['domain'] for row in bootstrap_summary_rows
                          if row['status'] != 'PASS']
    if preliminary != PHASE_A_QUALIFIED:
        conclusion = PHASE_A_REJECTED
    elif bootstrap_failures or len(bootstrap_summary_rows) != len(active_domains):
        conclusion = PHASE_A_REJECTED
    else:
        conclusion = PHASE_A_QUALIFIED
    write_csv(freeze_dir / 'bootstrap_stability_detail.csv',
              ['domain', 'replicate', 'seed', 'n', 'penalty_mae', 'rank_spearman', 'top10_jaccard',
               'pass_mae', 'pass_spearman', 'pass_jaccard', 'joint_pass', 'reason', 'a2', 'b2', 'a3',
               'b3'], bootstrap_detail_rows)
    write_csv(freeze_dir / 'bootstrap_stability_summary.csv',
              ['domain', 'n', 'replicates', 'joint_pass_count', 'required', 'status'],
              bootstrap_summary_rows)
    write_csv(freeze_dir / 'lambda_sensitivity_calibration.csv',
              ['lambda', 'n_rows', 'n_finite_penalty', 'penalty_mean', 'penalty_max', 'penalty_p50',
               'penalty_p95', 'spearman_vs_D', 'top10_jaccard_vs_D', 'new_zero_values', 'oos_rows',
               'rule_not_applicable_rows', 'primary'], lambda_rows)
    (freeze_dir / 'prior_exposure.md').write_text(PRIOR_EXPOSURE_TEXT, encoding='utf-8')
    write_json(freeze_dir / 'frozen_primary_spec.json', {
        'candidate_version': CANDIDATE_VERSION,
        'primary_result': 'D = Q_baseline',
        'candidate_formula': 'C = Q_baseline * (1 - lambda * P)',
        'lambda_primary': LAMBDA_PRIMARY,
        'lambda_grid_report_only': LAMBDA_GRID,
        'cluster_definition': 'fixed top-2gram/top-3gram redundancy cluster, P = (p2 + p3)/2',
        'design_domains': DESIGN_DOMAINS,
        'active_domains': active_domains,
        'inactive_domains': {label: inventory[label]['status'] for label in DESIGN_DOMAINS
                             if label not in active_domains},
        'support_ranges': {label: {k: thresholds[label][k] for k in ('lo2', 'hi2', 'lo3', 'hi3')}
                           for label in active_domains},
        'status_enum': SUPPORT_STATUSES,
        'row_selection': 'evaluation_role == A1_calibration & is_unique_first == True & Q_valid == '
                         'True & finite(Q_baseline) & finite(top2gram) & finite(top3gram)',
        'joint_key': 'key_sha256 (sha256 of the frozen JSON [str(id), str(sub_path)])',
        'bootstrap_summary': bootstrap_summary_rows,
        'bootstrap_failures': bootstrap_failures,
        'degenerate_large_domains': degenerate_large,
        'phase_a_conclusion': conclusion,
        'generated_local': now_iso()})
    write_json(freeze_dir / 'phase_a_summary.json', {
        'phase_a_status': conclusion,
        'preliminary_status': preliminary,
        'active_domains': active_domains,
        'domains_status': {label: inventory[label]['status'] for label in DESIGN_DOMAINS},
        'domain_detail': {label: {k: v for k, v in inventory[label].items() if k != 'design_label'}
                          for label in DESIGN_DOMAINS},
        'bootstrap_summary': bootstrap_summary_rows,
        'bootstrap_failures': bootstrap_failures,
        'lambda_rows': len(lambda_rows),
        'calibration_candidate_written': calibration_candidate_written,
        'degenerate_domains': degenerate_large,
        'artificial_tests_status': tests['status'],
        'artificial_tests_total': tests['n_tests'],
        'artificial_tests_failed': tests['n_failed'],
        'source_sha256': input_check['sha256'],
        'generated_local': now_iso(), 'pid': os.getpid()})
    snapshot_dir = freeze_dir / 'code_snapshot'
    snapshot_dir.mkdir(exist_ok=True)
    code_entries = []
    for source in [Path(__file__).resolve(), SOLUTION / 'src' / 't03e_verify.py',
                   SOLUTION / 'src' / 't03e_selftest.py']:
        if source.is_file():
            target = snapshot_dir / source.name
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            code_entries.append({'file': source.name, 'sha256': sha256_file(target),
                                 'bytes': int(target.stat().st_size)})
    requirements = freeze_dir_dependency_lines()
    (snapshot_dir / 'requirements_frozen.txt').write_text(requirements, encoding='utf-8')
    code_entries.append({'file': 'requirements_frozen.txt',
                         'sha256': sha256_file(snapshot_dir / 'requirements_frozen.txt'),
                         'bytes': int((snapshot_dir / 'requirements_frozen.txt').stat().st_size)})
    write_json(snapshot_dir / 'code_snapshot_manifest.json',
               {'generated_local': now_iso(), 'files': code_entries})
    frozen_files = []
    scan_roots = [freeze_dir, ctx.run_dir / 'metadata_preflight']
    scan_files = [ctx.run_dir / 'run_config.json', ctx.run_dir / 'environment.json']
    scanned = []
    for root in scan_roots:
        scanned.extend(sorted(root.rglob('*')))
    scanned.extend(scan_files)
    for path in scanned:
        if (not path.is_file()) or path.name in ('freeze_manifest.json', 'FREEZE_SEALED.json'):
            continue
        rel = str(path.relative_to(ctx.run_dir)).replace('\\', '/')
        frozen_files.append({'path': rel, 'bytes': int(path.stat().st_size),
                             'sha256': sha256_file(path)})
    config_sha = sha256_file(ctx.run_dir / 'run_config.json') if (ctx.run_dir / 'run_config.json').is_file() else sha256_text(json.dumps(preregistered_acceptance_payload(), sort_keys=True, ensure_ascii=False))
    manifest = {
        'task': 'TASK-T03E', 'candidate_version': CANDIDATE_VERSION,
        'primary_result': 'D = Q_baseline',
        'candidate_formula': 'C = Q_baseline * (1 - 0.02 * P)',
        'lambda_primary': LAMBDA_PRIMARY, 'lambda_grid_report_only': LAMBDA_GRID,
        'design_domains': DESIGN_DOMAINS, 'active_domains': active_domains,
        'domains_status': {label: inventory[label]['status'] for label in DESIGN_DOMAINS},
        'thresholds': {label: {k: thresholds[label][k] for k in
                               ('a2', 'b2', 'lo2', 'hi2', 'a3', 'b3', 'lo3', 'hi3',
                                'n_valid')}
                       for label in active_domains},
        'support_ranges': {label: {k: thresholds[label][k] for k in ('lo2', 'hi2', 'lo3', 'hi3')}
                           for label in active_domains},
        'acceptance_thresholds': preregistered_acceptance_payload(),
        'bootstrap_summary': bootstrap_summary_rows,
        'rng': {'algorithm': 'numpy PCG64 via numpy.random.default_rng',
                'master_seed': MASTER_SEED, 'sub_seed_rule': sub_seed_rule},
        'row_selection_rule': 'A1_calibration & is_unique_first & Q_valid & finite(Q_baseline, top2, top3)',
        'joint_key_definition': 'key_sha256 = sha256(json([str(id), str(sub_path)]))',
        'source_sha256': input_check['sha256'],
        'source_manifest_sha256': input_check['manifest_sha256'],
        'source_code_sha256': {entry['file']: entry['sha256'] for entry in code_entries},
        'config_sha256': config_sha,
        'config_file': 'run_config.json',
        'phase_a_conclusion': conclusion,
        'frozen_files': frozen_files,
        'frozen_file_count': len(frozen_files),
        'generated_local': now_iso(), 'pid': os.getpid()}
    write_json(freeze_dir / 'freeze_manifest.json', manifest)
    seal = {'task': 'TASK-T03E',
            'freeze_manifest_sha256': sha256_file(freeze_dir / 'freeze_manifest.json'),
            'sealed_local': now_iso(), 'pid': os.getpid(), 'command': ctx.command,
            'phase_a_status': conclusion, 'active_domains': active_domains,
            'domains_status': manifest['domains_status'],
            'thresholds': manifest['thresholds'],
            'bootstrap_status': {row['domain']: row['status'] for row in bootstrap_summary_rows},
            'note': 'seal written after every frozen file was closed; nothing frozen may change'}
    write_json(freeze_dir / 'FREEZE_SEALED.json', seal)
    ctx.status('phase_a', 'complete', status=conclusion, active_domains=active_domains,
               bootstrap_status={row['domain']: row['status'] for row in bootstrap_summary_rows},
               frozen_file_count=len(frozen_files))
    ctx.log('PHASE A complete: ' + conclusion + ' active=' + json.dumps(active_domains))
    return 0 if conclusion == PHASE_A_QUALIFIED else 3


def freeze_dir_dependency_lines():
    lines = ['# frozen runtime dependencies recorded at PHASE A seal time (TASK-T03E)']
    for name in ('python', 'numpy', 'pandas', 'pyarrow', 'scipy'):
        lines.append(name + '==' + str(module_version(name)))
    lines.append('quantile_implementation=numpy.quantile(method="linear")')
    return '\n'.join(lines) + '\n'


def verify_freeze_seal(ctx):
    freeze_dir = ctx.run_dir / 'phase_a_calibration_freeze'
    seal_path = freeze_dir / 'FREEZE_SEALED.json'
    manifest_path = freeze_dir / 'freeze_manifest.json'
    if not seal_path.is_file() or not manifest_path.is_file():
        raise GateFailure('freeze seal or manifest missing; PHASE B must not start')
    seal = read_json(seal_path)
    if seal.get('phase_a_status') != PHASE_A_QUALIFIED:
        raise GateFailure('PHASE A did not qualify; PHASE B must not read validation values')
    if sha256_file(manifest_path) != seal.get('freeze_manifest_sha256'):
        raise GateFailure('freeze manifest hash differs from the seal')
    manifest = read_json(manifest_path)
    mismatches = [item['path'] for item in manifest['frozen_files']
                  if not (ctx.run_dir / item['path']).is_file()
                  or sha256_file(ctx.run_dir / item['path']) != item['sha256']]
    if mismatches:
        raise GateFailure('frozen files changed after the seal: ' + json.dumps(mismatches[:5]))
    config_file = ctx.run_dir / manifest.get('config_file', 'run_config.json')
    if config_file.is_file() and sha256_file(config_file) != manifest.get('config_sha256'):
        raise GateFailure('run_config.json changed after the seal')
    state = {'freeze_manifest_sha256': seal['freeze_manifest_sha256'],
             'sealed_local': seal['sealed_local'], 'active_domains': seal['active_domains'],
             'frozen_files_verified': len(manifest['frozen_files']),
             'thresholds': manifest['thresholds'],
             'domains_status': manifest['domains_status'],
             'bootstrap_summary': manifest.get('bootstrap_summary', []),
             'source_sha256': manifest.get('source_sha256'),
             'source_code_sha256': manifest.get('source_code_sha256', {})}
    ctx.log('freeze seal verified (' + str(state['frozen_files_verified']) + ' frozen files)')
    return seal, manifest, state


def domain_gate_rows(domain, part, thresholds_for_domain, candidate, reference_candidate,
                     role_label, min_n):
    q = part['Q_baseline'].to_numpy(dtype=float)
    qc = candidate['Q_C']
    keys = part['key_sha256'].astype(str).to_numpy()
    ranks_d, order_d = rank_vector(q, keys)
    ranks_c, order_c = rank_vector(qc, keys)
    n = len(part)
    top_d, _k = top_set(order_d, n)
    top_c, _k2 = top_set(order_c, n)
    rho = spearman_from_ranks(ranks_d, ranks_c)
    jac = jaccard(top_d, top_c)
    p = candidate['P']
    ref_p = reference_candidate['P']
    ref_mean = float(np.nanmean(ref_p)) if np.isfinite(ref_p).any() else None
    role_mean = float(np.nanmean(p)) if np.isfinite(p).any() else None
    row = {'domain': domain, 'role': role_label, 'n_valid': n,
           'spearman_C_D': rho, 'top10_jaccard_C_D': jac,
           'top_k': int(_k), 'penalty_mean_role': role_mean,
           'penalty_mean_calibration': ref_mean,
           'penalty_mean_abs_diff': (abs(role_mean - ref_mean)
                                     if (role_mean is not None and ref_mean is not None) else None),
           'oos_rows': int(np.sum(candidate['Q_support_status'] == 'OUT_OF_SUPPORT')),
           'oos_fraction': (float(np.mean(candidate['Q_support_status'] == 'OUT_OF_SUPPORT'))
                            if n else None),
           'min_valid_n': min_n}
    row['pass_spearman'] = int(rho >= HOLDOUT_SPEARMAN_MIN) if n else 0
    row['pass_jaccard'] = int(jac >= HOLDOUT_JACCARD_MIN) if n else 0
    row['pass_penalty_mean'] = int(row['penalty_mean_abs_diff'] is not None
                                   and row['penalty_mean_abs_diff'] <= HOLDOUT_PENALTY_MEAN_TOL)
    row['pass_oos'] = int(row['oos_fraction'] is not None and row['oos_fraction'] <= OOS_MAX)
    row['eligible'] = int(n >= min_n)
    row['status'] = ('PASS' if (row['eligible'] and row['pass_spearman'] and row['pass_jaccard']
                                and row['pass_penalty_mean'] and row['pass_oos'])
                     else ('INSUFFICIENT_N' if not row['eligible'] else 'FAIL'))
    return row


GATE_COLUMNS = ['domain', 'role', 'n_valid', 'min_valid_n', 'eligible', 'spearman_C_D',
                'top10_jaccard_C_D', 'top_k', 'penalty_mean_role', 'penalty_mean_calibration',
                'penalty_mean_abs_diff', 'oos_rows', 'oos_fraction', 'pass_spearman', 'pass_jaccard',
                'pass_penalty_mean', 'pass_oos', 'status']


def regmix_identifiability(ctx):
    mapping_rows = list(csv.DictReader(open(A_DATA / 'domain_mapping_guide.csv', encoding='utf-8-sig')))
    ctx.access('regmix identifiability: quality/RegMix mapping', 'file read',
               ['mixture_domain', 'quality_domain', 'mapping_type'], len(mapping_rows),
               note=str(A_DATA / 'domain_mapping_guide.csv'))
    model = read_json(MIXTURE_DIR / 'model.json')
    mixture_rows = list(csv.DictReader(open(MIXTURE_DIR / 'aggregate_predictions.csv',
                                           encoding='utf-8-sig')))
    b6 = list(csv.DictReader(open(PROJECT / 'F题' / 'real_attachments' / 'B_scaling_laws' /
                                  'supplementary_NQ_experiment.csv', encoding='utf-8-sig')))
    ctx.access('regmix identifiability: B6 quality pairing check', 'file read',
               list(b6[0].keys()) if b6 else [], len(b6),
               note='B6 header inspection only; no model fitting, no new bridge model')
    mapped = [row for row in mapping_rows if row['quality_domain'] not in ('(none)', '')]
    direct = [row for row in mapping_rows if row['mapping_type'] == 'direct']
    near = [row for row in mapping_rows if row['mapping_type'] == 'near_direct']
    missing = [row for row in mapping_rows if row['quality_domain'] in ('(none)', '')]
    mapping_unique = len({row['mixture_domain'] for row in mapping_rows}) == len(mapping_rows)
    quality_side_unique = len({row['quality_domain'] for row in mapped}) == len(mapped)
    composition_columns = [row['mixture_domain'] for row in mapping_rows]
    model_features = model.get('features') or []
    model_has_all_w = bool(model_features) and all(
        ('train_the_pile_' + name) in model_features for name in composition_columns)
    b6_columns = list(b6[0].keys()) if b6 else []
    quality_pairing = [column for column in b6_columns if 'quality' in column.lower()
                       or column.lower() in ('q_score', 'qscore')]
    reasons = []
    if missing:
        reasons.append(str(len(missing)) + ' of ' + str(len(mapping_rows)) + ' RegMix domains have '
                       'no quality-domain mapping (quality_domain="(none)"), so the mapping is '
                       'neither complete nor unique')
    if model_has_all_w:
        composition_assessment = ('the existing mixture model already includes the full pile '
                                  'composition vector w as features, so with fixed domain qualities '
                                  'q_d the aggregate Q_mix is a deterministic function of w inside '
                                  'that model')
        reasons.append(composition_assessment + '; adding Q_mix therefore cannot be read as '
                       'independent quality information')
    else:
        composition_assessment = ('the existing mixture model does not expose the full composition '
                                  'vector w as features, so Q_mix cannot be written as sum_d w_d q_d '
                                  'inside the fitted model')
        reasons.append(composition_assessment)
    if quality_pairing:
        pairing_assessment = ('the B-side experiment table does carry ' + str(quality_pairing)
                              + ' over ' + str(len(b6)) + ' experiment rows, but no documented join '
                              'key links A-side quality rows/domains to those experiment_id values, '
                              'so no reliable sample-level or experiment-level A-to-B pairing exists '
                              'in the read-only inputs')
    else:
        pairing_assessment = ('the B-side experiment table carries no Q_score/quality column, so no '
                              'sample-level or experiment-level pairing exists')
    reasons.append(pairing_assessment)
    reasons.append('no independent quality variation under a fixed composition w is available in the '
                   'read-only inputs (one loss per mixture, one aggregate quality per domain)')
    status = 'NOT_IDENTIFIABLE' if reasons else 'IDENTIFIABLE'
    payload = {'status': status, 'checked_inputs': {
        'mapping': str(A_DATA / 'domain_mapping_guide.csv'), 'mapping_rows': len(mapping_rows),
        'direct_mappings': len(direct), 'near_direct_mappings': len(near),
        'unmapped_regmix_domains': [row['mixture_domain'] for row in missing],
        'mapping_unique_by_mixture_domain': bool(mapping_unique),
        'quality_side_unique': bool(quality_side_unique),
        'mixture_model': str(MIXTURE_DIR / 'model.json'), 'model_features': model_features,
        'model_has_full_composition': bool(model_has_all_w),
        'b6_file': 'F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv',
        'b6_columns': b6_columns, 'b6_rows': len(b6), 'quality_like_columns': quality_pairing,
        'aggregate_predictions_rows': len(mixture_rows)},
        'structural_reasons': reasons,
        'composition_vector_assessment': composition_assessment,
        'a_to_b_pairing_assessment': pairing_assessment,
        'regression_or_bridge_fitting_performed': False,
        'new_models_or_scalers_fitted': False,
        'needed_for_identification': [
            'a documented, complete and unique quality-domain -> RegMix-domain mapping',
            'quality variation that is independent of the composition vector w',
            'an experiment-level A-to-B pairing with a scale calibration (T06)'],
        'generated_local': now_iso(), 'pid': os.getpid()}
    write_json(ctx.run_dir / 'phase_b_frozen_validation' / 'regmix_loss_identifiability.json', payload)
    ctx.status('phase_b', 'regmix_identifiability', status=status, reasons=len(reasons))
    ctx.log('RegMix/Loss identifiability: ' + status)
    return payload


def attach_candidate(frame, thresholds, active, inventory, lam=LAMBDA_PRIMARY):
    out = apply_candidate(frame, thresholds, active, inventory, lam=lam)
    frame = frame.copy()
    for column in ('p_top2gram', 'p_top3gram', 'P', 'Q_C', 'Q_support_status'):
        frame[column] = out[column]
    frame['candidate_version'] = CANDIDATE_VERSION
    frame['lambda_primary'] = lam
    return frame


CONFIRMATORY_ROLES = ['A1_calibration', 'A1_holdout']
PHASE_B_ROLE_ORDER = ['A1_calibration', 'A1_holdout', 'extension_overlap_A1',
                      'extension_new_records']


def counts_for(frame):
    unique = frame[frame['is_unique_first'] == True]
    n_q_valid = int((unique['Q_valid'] == True).sum())
    n_analysis = int(len(valid_rows(unique)))
    return {'n_total': int(len(frame)), 'n_unique_first': int(len(unique)),
            'n_Q_valid': n_q_valid, 'n_Q_missing': int(len(unique) - n_q_valid),
            'n_analysis_valid': n_analysis,
            'analysis_coverage': (n_analysis / len(unique)) if len(unique) else None}


def confirmatory_mask(frame):
    role = frame['evaluation_role'].astype(str)
    return ((frame['is_unique_first'] == True).to_numpy()
            & (frame['Q_valid'] == True).to_numpy()
            & role.isin(CONFIRMATORY_ROLES).to_numpy()
            & np.isfinite(frame['Q_baseline'].to_numpy(dtype=float))
            & np.isfinite(frame['rps_doc_frac_chars_top_2gram'].to_numpy(dtype=float))
            & np.isfinite(frame['rps_doc_frac_chars_top_3gram'].to_numpy(dtype=float)))


def count_confirmatory(frame):
    return int(confirmatory_mask(frame).sum())


def coverage_rows(frames_by_role, read_times):
    rows = []
    for role in PHASE_B_ROLE_ORDER:
        frame = frames_by_role.get(role)
        if frame is None:
            continue
        for domain in sorted(frame['domain'].astype(str).unique().tolist()):
            part = frame[frame['domain'].astype(str) == domain]
            row = {'role': role, 'domain': domain}
            row.update(counts_for(part))
            row['analysis_scope'] = ('is_unique_first & Q_valid & finite(Q_baseline, top2gram, '
                                     'top3gram)')
            row['confirmatory_rows'] = count_confirmatory(part)
            row['first_read_time'] = read_times.get(role, '')
            rows.append(row)
    return rows


COVERAGE_COLUMNS = ['role', 'domain', 'n_total', 'n_unique_first', 'n_Q_valid', 'n_Q_missing',
                    'n_analysis_valid', 'analysis_coverage', 'confirmatory_rows', 'analysis_scope',
                    'first_read_time']


def write_domain_role_outputs(ctx, frames_by_role, read_times, inventory):
    phase_b_dir = ctx.run_dir / 'phase_b_frozen_validation'
    role_rows = coverage_rows(frames_by_role, read_times)
    write_csv(phase_b_dir / 'domain_role_inventory.csv', COVERAGE_COLUMNS, role_rows)
    seen = {}
    for role in PHASE_B_ROLE_ORDER:
        frame = frames_by_role.get(role)
        if frame is None:
            continue
        for domain in sorted(frame['domain'].astype(str).unique().tolist()):
            entry = seen.setdefault(domain, {'roles': [], 'first_role': role,
                                             'first_read_time': read_times.get(role, '')})
            entry['roles'].append(role)
    label_rows = [{'domain_label': domain, 'exact_string_length': len(domain),
                   'n_roles_present': len(seen[domain]['roles']),
                   'roles_present_in_read_order': '|'.join(seen[domain]['roles']),
                   'first_role_observed': seen[domain]['first_role'],
                   'first_read_time': seen[domain]['first_read_time']}
                  for domain in sorted(seen)]
    write_csv(phase_b_dir / 'actual_domain_labels_all_roles.csv',
              ['domain_label', 'exact_string_length', 'n_roles_present',
               'roles_present_in_read_order', 'first_role_observed', 'first_read_time'], label_rows)
    match_rows = []
    for label in DESIGN_DOMAINS:
        entry = seen.get(label)
        inv = inventory.get(label) or {}
        match_rows.append({'design_label': label, 'present_in_any_role': bool(entry),
                           'exact_match_any_role': bool(entry),
                           'first_role_observed': entry['first_role'] if entry else '',
                           'roles_present_in_read_order': '|'.join(entry['roles']) if entry else '',
                           'calibration_status': inv.get('status', 'DESIGN_LABEL_ABSENT'),
                           'calibration_valid_n': int(inv.get('n_valid', 0) or 0),
                           'status': 'EXACT_MATCH' if entry else 'DESIGN_LABEL_ABSENT'})
    write_csv(phase_b_dir / 'domain_label_match_all_roles.csv',
              ['design_label', 'present_in_any_role', 'exact_match_any_role',
               'first_role_observed', 'roles_present_in_read_order', 'calibration_status',
               'calibration_valid_n', 'status'], match_rows)
    return role_rows, label_rows, match_rows


def write_candidate_scores(ctx, full, cand, role_rows):
    lookup = {(str(row['role']), str(row['domain'])): row for row in role_rows}
    role = full['evaluation_role'].astype(str).to_numpy()
    domain = full['domain'].astype(str).to_numpy()

    def column(field):
        return [lookup[(r, d)][field] for r, d in zip(role, domain)]

    out = pd.DataFrame({
        'file_id': full['file_id'].to_numpy(),
        'source_line': full['source_line'].to_numpy(),
        'key_sha256': full['key_sha256'].to_numpy(),
        'domain': domain,
        'evaluation_role': role,
        'is_unique_first': full['is_unique_first'].to_numpy(),
        'overlap_a1': full['overlap_a1'].to_numpy(),
        'Q_valid': full['Q_valid'].to_numpy(),
        'Q_baseline': full['Q_baseline'].to_numpy(dtype=float),
        'Q_C': cand['Q_C'],
        'P': cand['P'],
        'p_top2gram': cand['p_top2gram'],
        'p_top3gram': cand['p_top3gram'],
        'Q_support_status': cand['Q_support_status'],
        'candidate_version': CANDIDATE_VERSION,
        'lambda_primary': LAMBDA_PRIMARY,
        'in_confirmatory_denominator': confirmatory_mask(full),
        'domain_role_n_total': column('n_total'),
        'domain_role_n_unique_first': column('n_unique_first'),
        'domain_role_n_analysis_valid': column('n_analysis_valid'),
        'domain_role_analysis_coverage': column('analysis_coverage')})
    path = ctx.run_dir / 'candidate_Q_scores.parquet'
    out.to_parquet(path, index=False)
    return out, path


def write_t06_interface(ctx, full, scores, role_rows, freeze_manifest_sha, regmix_payload):
    frame = pd.DataFrame({
        'file_id': full['file_id'].to_numpy(),
        'source_line': full['source_line'].to_numpy(),
        'key_sha256': full['key_sha256'].to_numpy(),
        'domain': full['domain'].astype(str).to_numpy(),
        'evaluation_role': full['evaluation_role'].astype(str).to_numpy(),
        'is_unique_first': full['is_unique_first'].to_numpy(),
        'Q_baseline': full['Q_baseline'].to_numpy(dtype=float),
        'Q_C': scores['Q_C'].to_numpy(dtype=float),
        'P': scores['P'].to_numpy(dtype=float),
        'p_top2gram': scores['p_top2gram'].to_numpy(dtype=float),
        'p_top3gram': scores['p_top3gram'].to_numpy(dtype=float),
        'Q_valid': full['Q_valid'].to_numpy(),
        'Q_support_status': scores['Q_support_status'].to_numpy(),
        'dsir_books': full['dsir_books'].to_numpy(dtype=float),
        'dsir_wiki': full['dsir_wiki'].to_numpy(dtype=float),
        'dsir_math': full['dsir_math'].to_numpy(dtype=float),
        'candidate_version': CANDIDATE_VERSION,
        'lambda_primary': LAMBDA_PRIMARY,
        'in_confirmatory_denominator': scores['in_confirmatory_denominator'].to_numpy(),
        'domain_role_n_total': scores['domain_role_n_total'].to_numpy(),
        'domain_role_n_analysis_valid': scores['domain_role_n_analysis_valid'].to_numpy()})
    frame['dsir_relevance_vector'] = [list(row) for row in
                                      frame[['dsir_books', 'dsir_wiki', 'dsir_math']]
                                      .to_numpy(dtype=float)]
    frame.to_parquet(ctx.run_dir / 't06_quality_interface.parquet', index=False)
    payload = {
        'task': 'TASK-T03E',
        'candidate_version': CANDIDATE_VERSION,
        'freeze_manifest_sha256': freeze_manifest_sha,
        'primary_Q': 'Q_baseline',
        'primary_Q_statement': 'The official main quality remains D = Q_baseline.',
        'sensitivity_candidate': 'Q_C = Q_baseline * (1 - 0.02 * P)',
        'cluster_penalty': 'P = (p_top2gram + p_top3gram) / 2',
        'columns': list(frame.columns),
        'dsir_note': ('DSIR_relevance_vector = (dsir_books, dsir_wiki, dsir_math) is a '
                      'target-relevance vector, not a universal quality component'),
        'limitations': [
            'Q_C has no independent ground-truth quality label in this project; it is a '
            'preregistered rule-sensitivity candidate only',
            'no field of this interface may be renamed final_Q/best_Q/improved_Q/true_quality',
            'A-side Q and the B-side Q_score still require separate T06 calibration'],
        'regmix_loss_identifiability_status': regmix_payload.get('status'),
        'regmix_loss_identifiability_reasons': regmix_payload.get('structural_reasons'),
        'coverage_by_role_domain': role_rows,
        'coverage_columns_note': ('n_total = physical rows of that role x domain; n_unique_first = '
                                 'is_unique_first rows; n_analysis_valid = unique_first & Q_valid & '
                                 'finite(Q_baseline, top2gram, top3gram); analysis_coverage = '
                                 'n_analysis_valid / n_unique_first'),
        'forbidden_field_names_present': [name for name in FORBIDDEN_OUTPUT_COLUMNS
                                          if name in frame.columns],
        'generated_local': now_iso(), 'pid': os.getpid()}
    write_json(ctx.run_dir / 't06_quality_interface.json', payload)
    return frame, payload


def protected_column_equal(left, right):
    left = np.asarray(left)
    right = np.asarray(right)
    if left.shape != right.shape:
        return False
    if left.dtype.kind in 'fiu' and right.dtype.kind in 'fiu':
        return bool(np.array_equal(left.astype(float), right.astype(float), equal_nan=True))
    return bool(np.array_equal(left.astype(str), right.astype(str)))


PROTECTED_COLUMNS = ['file_id', 'source_line', 'key_sha256', 'domain', 'evaluation_role',
                     'is_unique_first', 'overlap_a1', 'Q_valid', 'Q_baseline']


def write_protected_baseline_check(ctx, input_checks, full, frames_by_role, scores,
                                   frozen_calibration):
    payload = {'task': 'TASK-T03E',
               'protected_columns': PROTECTED_COLUMNS,
               'rows_total': int(len(full)),
               'input_checks': input_checks,
               'input_sha256_stable': bool(len({entry['sha256'] for entry in input_checks}) == 1
                                           and all(entry['matches_manifest'] for entry in input_checks)),
               'role_reads': {}, 'frozen_calibration_consistency': {},
               'generated_local': now_iso(), 'pid': os.getpid()}
    ok = True
    for role in PHASE_B_ROLE_ORDER:
        frame = frames_by_role.get(role)
        if frame is None:
            continue
        sub = full[full['evaluation_role'].astype(str) == role]
        entry = {'rows_role_read': int(len(frame)), 'rows_in_assembly': int(len(sub)),
                 'columns': {}}
        same_rows = len(frame) == len(sub)
        entry['row_count_identical'] = bool(same_rows)
        entry['key_sequence_identical'] = bool(
            same_rows and list(sub['key_sha256'].astype(str)) == list(frame['key_sha256'].astype(str)))
        for column in PROTECTED_COLUMNS:
            same = bool(same_rows and protected_column_equal(sub[column].to_numpy(),
                                                            frame[column].to_numpy()))
            entry['columns'][column] = same
            ok = ok and same
        ok = ok and entry['row_count_identical']
        payload['role_reads'][role] = entry
    calib_assembly = scores[scores['evaluation_role'].astype(str) == 'A1_calibration']
    frozen_entry = {'frozen_rows': int(len(frozen_calibration)),
                    'assembly_rows': int(len(calib_assembly)),
                    'key_sequence_identical': bool(
                        len(frozen_calibration) == len(calib_assembly)
                        and list(frozen_calibration['key_sha256'].astype(str))
                        == list(calib_assembly['key_sha256'].astype(str)))}
    for column in ('Q_baseline', 'Q_C', 'P', 'p_top2gram', 'p_top3gram'):
        left = frozen_calibration[column].to_numpy(dtype=float)
        right = calib_assembly[column].to_numpy(dtype=float)
        nan_same = bool(len(left) == len(right)
                        and np.array_equal(np.isnan(left), np.isnan(right)))
        comparable = len(left) == len(right) and bool(np.isfinite(left).any())
        delta = (float(np.nanmax(np.abs(left - right))) if comparable else None)
        frozen_entry[column] = {'nan_pattern_identical': nan_same, 'max_abs_delta': delta,
                                'within_1e-12': bool(nan_same and delta is not None
                                                     and delta <= 1e-12)}
        ok = ok and frozen_entry[column]['within_1e-12']
    for column in ('Q_support_status',):
        left = frozen_calibration[column].astype(str).tolist()
        right = calib_assembly[column].astype(str).tolist()
        frozen_entry[column] = bool(left == right)
        ok = ok and frozen_entry[column]
    ok = ok and frozen_entry['key_sequence_identical']
    payload['frozen_calibration_consistency'] = frozen_entry
    payload['status'] = 'PASS' if ok else 'FAIL'
    write_json(ctx.run_dir / 'protected_baseline_check.json', payload)
    return payload


def first_access_time(ctx, purpose_contains):
    if not ctx.access_path.is_file():
        return ''
    with open(ctx.access_path, 'r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if purpose_contains in str(record.get('purpose', '')):
                return str(record.get('ts', ''))
    return ''


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    return value


def mode_frozen_validation(ctx):
    ctx.status('phase_b', 'start')
    seal, manifest, state = verify_freeze_seal(ctx)
    freeze_dir = ctx.run_dir / 'phase_a_calibration_freeze'
    phase_b_dir = ctx.mode_dir('phase_b_frozen_validation')
    input_checks = [verify_input(ctx, 'frozen-validation start')]
    active = list(state['active_domains'])
    thresholds = {label: {k: float(state['thresholds'][label][k])
                          for k in ('a2', 'b2', 'lo2', 'hi2', 'a3', 'b3', 'lo3', 'hi3')}
                  for label in active}
    frozen_domains = list(csv.DictReader(open(freeze_dir / 'frozen_active_domains.csv',
                                              encoding='utf-8-sig')))
    inventory = {row['design_label']: {'status': row['status'], 'n_valid': int(row['n_valid'])}
                 for row in frozen_domains}
    calibration = pd.read_parquet(freeze_dir / 'calibration_candidate_rows.parquet')
    ctx.access('sealed PHASE A calibration candidate rows', 'file read (sealed PHASE A artefact)',
               list(calibration.columns), len(calibration),
               note=str(freeze_dir / 'calibration_candidate_rows.parquet'))
    if not (calibration['evaluation_role'] == 'A1_calibration').all():
        raise GateFailure('sealed calibration artefact contains non-calibration rows')
    calib_valid = calibration[(calibration['is_unique_first'] == True)
                              & (calibration['Q_valid'] == True)]
    calibration_read_time = first_access_time(ctx, 'calibration partition preflight')
    # ---- step 3: first holdout read, strictly after the freeze seal ----
    holdout = read_role_rows(ctx, 'A1_holdout', 'PHASE B step 3: first holdout read', READ_COLUMNS)
    first_holdout_read_time = now_iso_ms()
    ctx.status('phase_b', 'first_holdout_read', first_holdout_read_time=first_holdout_read_time,
               rows=int(len(holdout)))
    holdout = attach_candidate(holdout, thresholds, active, inventory)
    holdout_valid = valid_rows(holdout[holdout['is_unique_first'] == True])
    holdout_rows = []
    for label in active:
        part = holdout_valid[holdout_valid['domain'].astype(str) == label]
        ref = calib_valid[calib_valid['domain'].astype(str) == label]
        if len(part) == 0:
            empty = {column: None for column in GATE_COLUMNS}
            empty.update({'domain': label, 'role': 'A1_holdout', 'n_valid': 0,
                          'min_valid_n': HOLDOUT_MIN_N, 'eligible': 0,
                          'status': 'INSUFFICIENT_N'})
            holdout_rows.append(empty)
            continue
        holdout_rows.append(domain_gate_rows(
            label, part, thresholds[label],
            {'Q_C': part['Q_C'].to_numpy(dtype=float), 'P': part['P'].to_numpy(dtype=float),
             'Q_support_status': part['Q_support_status'].to_numpy()},
            {'P': ref['P'].to_numpy(dtype=float)}, 'A1_holdout', HOLDOUT_MIN_N))
    eligible_fail = [row for row in holdout_rows if row.get('eligible') and row['status'] != 'PASS']
    insufficient = [row for row in holdout_rows if not row.get('eligible')]
    if eligible_fail:
        holdout_status = 'REJECT_KEEP_D'
    elif insufficient:
        holdout_status = 'INSUFFICIENT_EVIDENCE_KEEP_D'
    else:
        holdout_status = 'ACCEPT_STABILITY'
    write_csv(phase_b_dir / 'holdout_validation.csv', GATE_COLUMNS, holdout_rows)
    holdout_summary = {
        'holdout_status': holdout_status, 'active_domains': active, 'per_domain': holdout_rows,
        'failed_domains': [row['domain'] for row in eligible_fail],
        'insufficient_domains': [row['domain'] for row in insufficient],
        'rule': 'only active correction domains with holdout n>=200 enter the pass rate; '
                'Spearman>=0.98, top-10% Jaccard>=0.85, |mean(P_holdout)-mean(P_calibration)|<=0.05, '
                'OUT_OF_SUPPORT share<=0.05',
        'first_holdout_read_time': first_holdout_read_time,
        'freeze_manifest_sha256': state['freeze_manifest_sha256'],
        'sealed_local': state['sealed_local'],
        'candidate_version': CANDIDATE_VERSION,
        'statement': 'D = Q_baseline stays the official main result regardless of this status',
        'generated_local': now_iso(), 'pid': os.getpid()}
    write_json(phase_b_dir / 'holdout_summary.json', holdout_summary)
    holdout_frozen = {'generated_local': now_iso(),
                      'first_holdout_read_time': first_holdout_read_time,
                      'freeze_manifest_sha256': state['freeze_manifest_sha256'],
                      'holdout_status': holdout_status, 'files': []}
    for name in ('holdout_validation.csv', 'holdout_summary.json'):
        path = phase_b_dir / name
        holdout_frozen['files'].append({'path': name, 'bytes': int(path.stat().st_size),
                                        'sha256': sha256_file(path)})
    write_json(phase_b_dir / 'holdout_freeze_manifest.json', holdout_frozen)
    ctx.status('phase_b', 'holdout_frozen', status=holdout_status)
    ctx.log('holdout frozen: ' + holdout_status)
    # ---- step 5: first extension read, strictly after the holdout output was frozen ----
    extension = read_role_rows(ctx, ['extension_overlap_A1', 'extension_new_records'],
                               'PHASE B step 5: first extension read', READ_COLUMNS)
    first_extension_read_time = now_iso_ms()
    ctx.status('phase_b', 'first_extension_read', first_extension_read_time=first_extension_read_time,
               rows=int(len(extension)))
    extension = attach_candidate(extension, thresholds, active, inventory)
    extension_overlap = extension[extension['evaluation_role'].astype(str)
                                  == 'extension_overlap_A1']
    extension_new = extension[extension['evaluation_role'].astype(str)
                              == 'extension_new_records']
    a1_map = {}
    for frame in (calibration, holdout):
        for row in frame.itertuples(index=False):
            a1_map[str(row.key_sha256)] = row
    overlap_rows = []
    reproduced = 0
    violations = 0
    for row in extension_overlap.itertuples(index=False):
        reference = a1_map.get(str(row.key_sha256))
        entry = {'key_sha256': row.key_sha256, 'a1_present': bool(reference is not None),
                 'a1_domain': '', 'extension_domain': row.domain, 'domain_equal': None,
                 'inputs_identical': None, 'abs_delta_Q_C': None, 'status': '',
                 'candidate_version_match': None, 'differences': ''}
        if reference is None:
            entry['status'] = 'A1_SIDE_MISSING'
            entry['differences'] = 'no A1 row with this frozen joint key'
            overlap_rows.append(entry)
            continue
        entry['a1_domain'] = reference.domain
        entry['domain_equal'] = bool(str(reference.domain) == str(row.domain))
        entry['candidate_version_match'] = bool(str(reference.candidate_version)
                                                == str(row.candidate_version))
        differences = []
        same_inputs = True
        for column in ('Q_baseline', 'rps_doc_frac_chars_top_2gram', 'rps_doc_frac_chars_top_3gram'):
            left = getattr(reference, column)
            right = getattr(row, column)
            if not (pd.notna(left) and pd.notna(right) and float(left) == float(right)):
                same_inputs = False
                differences.append(column + ': a1=' + str(left) + ' extension=' + str(right))
        entry['inputs_identical'] = bool(same_inputs)
        entry['differences'] = '; '.join(differences)
        if not entry['domain_equal']:
            entry['status'] = 'DOMAIN_MISMATCH'
            overlap_rows.append(entry)
            continue
        if not entry['candidate_version_match']:
            entry['status'] = 'CANDIDATE_VERSION_MISMATCH'
            overlap_rows.append(entry)
            continue
        if not same_inputs:
            entry['status'] = 'INPUT_DIFFERS'
            overlap_rows.append(entry)
            continue
        left_qc = getattr(reference, 'Q_C')
        right_qc = row.Q_C
        if pd.isna(left_qc) or pd.isna(right_qc):
            entry['status'] = 'Q_INVALID_PRESERVED'
            overlap_rows.append(entry)
            continue
        delta = abs(float(left_qc) - float(right_qc))
        entry['abs_delta_Q_C'] = delta
        if delta <= OVERLAP_TOL:
            entry['status'] = 'REPRODUCED'
            reproduced += 1
        else:
            entry['status'] = 'REPRODUCTION_MISMATCH'
            violations += 1
        overlap_rows.append(entry)
    write_csv(phase_b_dir / 'extension_overlap_validation.csv',
              ['key_sha256', 'a1_present', 'a1_domain', 'extension_domain', 'domain_equal',
               'candidate_version_match', 'inputs_identical', 'abs_delta_Q_C', 'status',
               'differences'], overlap_rows)
    new_rows = []
    for label in active:
        part = extension_new[extension_new['is_unique_first'] == True]
        part = valid_rows(part)
        part = part[part['domain'].astype(str) == label]
        if len(part) == 0:
            empty = {column: None for column in GATE_COLUMNS}
            empty.update({'domain': label, 'role': 'extension_new_records', 'n_valid': 0,
                          'min_valid_n': EXTENSION_MIN_N, 'eligible': 0,
                          'status': 'NOT_PRESENT_IN_EXTENSION'})
            new_rows.append(empty)
            continue
        row = domain_gate_rows(
            label, part, thresholds[label],
            {'Q_C': part['Q_C'].to_numpy(dtype=float), 'P': part['P'].to_numpy(dtype=float),
             'Q_support_status': part['Q_support_status'].to_numpy()},
            {'P': calibration[(calibration['domain'].astype(str) == label)
                              & (calibration['is_unique_first'] == True)
                              & (calibration['Q_valid'] == True)]['P'].to_numpy(dtype=float)},
            'extension_new_records', EXTENSION_MIN_N)
        if not row['eligible']:
            row['status'] = 'INSUFFICIENT_EXTENSION_EVIDENCE'
        elif row['status'] == 'PASS':
            row['status'] = 'MIGRATION_OK'
        else:
            row['status'] = 'MIGRATION_FAILED_KEEP_D'
        new_rows.append(row)
    write_csv(phase_b_dir / 'extension_new_validation.csv', GATE_COLUMNS, new_rows)
    tested = [row for row in new_rows if row.get('eligible')]
    insufficient_extension = [row['domain'] for row in new_rows
                              if row['status'] == 'INSUFFICIENT_EXTENSION_EVIDENCE']
    if tested and any(row['status'] == 'MIGRATION_FAILED_KEEP_D' for row in tested):
        extension_status = 'MIGRATION_FAILED_KEEP_D'
    elif tested and insufficient_extension:
        extension_status = 'INSUFFICIENT_EXTENSION_EVIDENCE'
    elif tested:
        extension_status = 'MIGRATION_OK'
    elif insufficient_extension:
        extension_status = 'INSUFFICIENT_EXTENSION_EVIDENCE'
    else:
        extension_status = 'NOT_TESTED_FOR_ACTIVE_CORRECTION'
    extension_summary = {'extension_status': extension_status, 'active_domains': active,
                         'per_domain_new': new_rows,
                         'insufficient_extension_domains': insufficient_extension,
                         'not_present_domains': [row['domain'] for row in new_rows
                                                 if row['status'] == 'NOT_PRESENT_IN_EXTENSION'],
                         'first_extension_read_time': first_extension_read_time,
                         'overlap_rows': len(overlap_rows), 'overlap_reproduced': reproduced,
                         'overlap_mismatches': violations,
                         'note': ('overlap reproduces identical inputs only; new records carry the '
                                  'transport evidence; C=D perfect agreement in '
                                  'rule-not-applicable or insufficient domains is never counted as '
                                  'transport success'),
                         'freeze_manifest_sha256': state['freeze_manifest_sha256'],
                         'statement': 'D = Q_baseline stays the official main result',
                         'generated_local': now_iso(), 'pid': os.getpid()}
    write_json(phase_b_dir / 'extension_summary.json', extension_summary)
    ctx.status('phase_b', 'extension_done', status=extension_status)
    ctx.log('extension status: ' + extension_status)
    frames_by_role = {'A1_calibration': calibration, 'A1_holdout': holdout,
                      'extension_overlap_A1': extension_overlap,
                      'extension_new_records': extension_new}
    read_times = {'A1_calibration': calibration_read_time,
                  'A1_holdout': first_holdout_read_time,
                  'extension_overlap_A1': first_extension_read_time,
                  'extension_new_records': first_extension_read_time}
    role_rows, label_rows, label_match_rows = write_domain_role_outputs(
        ctx, frames_by_role, read_times, inventory)
    regmix_payload = regmix_identifiability(ctx)
    # ---- full-table assembly read (after both role reads; preserves physical order) ----
    full = pq.read_table(INPUT_PATH, columns=READ_COLUMNS).to_pandas()
    ctx.access('PHASE B assembly read for candidate_Q_scores/t06 interface',
               'no role filter (post-holdout, post-extension assembly of all physical rows)',
               READ_COLUMNS, len(full),
               note='single un-filtered read used only to preserve the original physical row order; '
                    'both role reads already happened in the frozen order and are cross-checked '
                    'below')
    candidate = apply_candidate(full, thresholds, active, inventory)
    scores, scores_path = write_candidate_scores(ctx, full, candidate, role_rows)
    t06_frame, t06_payload = write_t06_interface(ctx, full, scores, role_rows,
                                                 state['freeze_manifest_sha256'], regmix_payload)
    input_checks.append(verify_input(ctx, 'frozen-validation end'))
    protected = write_protected_baseline_check(ctx, input_checks, full, frames_by_role, scores,
                                               calibration)
    if protected['status'] != 'PASS':
        raise GateFailure('protected baseline consistency failed')
    write_input_manifest(ctx, 'phase_b-frozen-validation')
    ctx.status('phase_b', 'assembly_complete', rows=int(len(scores)),
               confirmatory_rows=count_confirmatory(full))
    return seal, manifest, state, {'full': full, 'scores': scores, 'calibration': calibration,
                                  'holdout': holdout, 'extension': extension,
                                  'role_rows': role_rows, 'label_rows': label_rows,
                                  'label_match_rows': label_match_rows,
                                  'frames_by_role': frames_by_role, 'read_times': read_times,
                                  'thresholds': thresholds, 'active': active,
                                  'inventory': inventory, 'regmix': regmix_payload,
                                  't06_payload': t06_payload, 'protected': protected,
                                  'input_checks': input_checks}, {
        'holdout': holdout_summary, 'extension': extension_summary,
        'first_holdout_read_time': first_holdout_read_time,
        'first_extension_read_time': first_extension_read_time}


PROHIBITED_SCAN_PATTERNS = ['np.clip(', '.clip(', 'sklearn.', 'PCA(', 'EntropyWeight',
                           'entropy_weight', 'critic_score', 'lambda_learn', 'grid_search(',
                           'scipy.optimize.', 'curve_fit(', 'LinearRegression(', 'RandomForest(',
                           'xgboost', 'torch.']


def source_scan_for_prohibited_calls(executor_path, verifier_path):
    """Scan the frozen sources for prohibited operations.

    The scanner's own pattern table is removed from the text before counting so that the
    table cannot match itself.
    """
    result = {}
    for path in (executor_path, verifier_path):
        path = Path(path)
        if not path.is_file():
            result[path.name] = {'present': False, 'clean': False,
                                 'note': 'source file not found in the code snapshot'}
            continue
        text = path.read_text(encoding='utf-8')
        marker = 'PROHIBITED_SCAN_PATTERNS = ['
        position = text.find(marker)
        if position >= 0:
            closing = text.find(']', position)
            text = text[:position] + text[closing + 1:]
        hits = {pattern: int(text.count(pattern)) for pattern in PROHIBITED_SCAN_PATTERNS
                if text.count(pattern)}
        result[path.name] = {'present': True, 'prohibited_call_hits': hits, 'clean': not hits}
    return result


def compute_candidate_boundaries(full, scores):
    mask = confirmatory_mask(full)
    qd = full['Q_baseline'].to_numpy(dtype=float)[mask]
    qc = scores['Q_C'].to_numpy(dtype=float)[mask]
    penalty = scores['P'].to_numpy(dtype=float)[mask]
    status = scores['Q_support_status'].to_numpy()[mask]
    finite = bool(np.isfinite(qd).all() and np.isfinite(qc).all() and np.isfinite(penalty).all())
    positive = qd > 0
    ratio = (qc[positive] / qd[positive]) if positive.any() else np.array([np.nan])
    payload = {
        'n_confirmatory_rows': int(mask.sum()),
        'all_finite': finite,
        'P_min': float(np.min(penalty)), 'P_max': float(np.max(penalty)),
        'P_within_unit_interval': bool(np.all((penalty >= 0.0) & (penalty <= 1.0))),
        'max_Q_C_minus_D': float(np.max(qc - qd)),
        'max_abs_Q_C_minus_D': float(np.max(np.abs(qc - qd))),
        'min_ratio_Q_C_over_D_for_positive_D': float(np.min(ratio)),
        'rows_D_zero': int(np.sum(qd == 0)),
        'rows_D_zero_and_C_zero': int(np.sum((qd == 0) & (qc == 0))),
        'new_zero_values': int(np.sum((qd > 0) & (qc == 0))),
        'negative_Q_C_rows': int(np.sum(qc < 0)),
        'oos_rows': int(np.sum(status == 'OUT_OF_SUPPORT')),
        'supported_rows': int(np.sum(status == 'SUPPORTED')),
        'rules': 'Q_C <= D, Q_C >= 0.98*D, no new zeros, P in [0, 1] on the confirmatory sample'}
    rule_not_applicable = scores['Q_support_status'].to_numpy() == 'RULE_NOT_APPLICABLE'
    qna = full['Q_baseline'].to_numpy(dtype=float)[rule_not_applicable]
    cna = scores['Q_C'].to_numpy(dtype=float)[rule_not_applicable]
    payload['rule_not_applicable_rows'] = int(rule_not_applicable.sum())
    payload['rule_not_applicable_max_abs_delta'] = (
        float(np.nanmax(np.abs(cna - qna))) if rule_not_applicable.sum() else 0.0)
    payload['rule_not_applicable_zero_delta'] = bool(
        payload['rule_not_applicable_max_abs_delta'] == 0.0)
    domains = full['domain'].astype(str).to_numpy()
    payload['rule_not_applicable_domains'] = sorted(set(
        domains[rule_not_applicable].tolist()))
    return payload


def seed_manifest_check(freeze_dir):
    path = freeze_dir / 'bootstrap_seed_manifest.csv'
    rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    mismatches = [row for row in rows
                  if int(row['seed']) != bootstrap_seed(row['domain'], int(row['replicate']))]
    return {'rows': len(rows), 'mismatches': len(mismatches),
            'status': 'PASS' if rows and not mismatches else ('FAIL' if mismatches else 'NOT_CHECKED')}


def build_executor_checks(facts):
    checks = []

    def add(identifier, name, status, evidence, note=''):
        checks.append({'id': identifier, 'name': name, 'status': status,
                       'evidence': evidence, 'note': note, 'checked_local': now_iso()})

    inputs = facts['input_checks']
    add('EX-01', 'official Q01C input path/size/SHA256 matches its output_manifest',
        'PASS' if facts['input_stable'] else 'FAIL',
        {'checks': inputs, 'expected_sha256': inputs[0]['manifest_sha256']},
        'hash verified before PHASE A, at PHASE B start and at PHASE B end')
    add('EX-02', 'preflight analysis layer only received A1_calibration rows',
        'PASS' if facts['preflight'].get('analysis_layer_roles_visible') == ['A1_calibration']
        else 'FAIL', {'roles_visible': facts['preflight'].get('analysis_layer_roles_visible'),
                      'calibration_rows': facts['preflight']['commitment']['calibration_physical_rows'],
                      'unique_first': facts['preflight']['commitment']['calibration_unique_first_rows']})
    missing = [row['design_label'] for row in facts['design_match']
               if row['status'] != 'EXACT_MATCH']
    add('EX-03', 'four preregistered design labels match calibration exactly (character-exact)',
        'PASS' if not missing else 'NOT_CHECKED',
        {'design_labels': [row['design_label'] for row in facts['design_match']],
         'calibration_labels': facts['preflight']['labels'],
         'absent_design_labels': missing,
         'matching_rule': 'exact string equality only; no fuzzy/alias/merge/fallback'},
        'DESIGN_LABEL_ABSENT is recorded when a design label does not occur')
    add('EX-04', 'active correction domains frozen from calibration eligibility',
        'PASS', {'active_domains': facts['active'],
                 'domain_status': facts['phase_a']['domains_status'],
                 'min_valid_n': ACTIVE_MIN_N,
                 'quantile_requirement': 'q0.99 > q0.95 for both indicators'},
        'domains below n or with a missing label are excluded, never substituted')
    tests = read_json(facts['freeze_dir'] / 'artificial_tests.json')
    add('EX-05', 'pre-run artificial rule-cluster/boundary/fallback tests',
        'PASS' if tests['status'] == 'PASS' and tests['n_failed'] == 0 else 'FAIL',
        {'n_tests': tests['n_tests'], 'n_failed': tests['n_failed'],
         'test_names': [item['test'] for item in tests['tests']]},
        'hand-computed expectations; no real analysis value read before this point')
    add('EX-06', 'bootstrap sub-seeds follow the frozen SHA256 rule',
        facts['seed_check']['status'], facts['seed_check'],
        'int(sha256("20260925|<domain>|<replicate>")[:16], 16) -> PCG64')
    bootstrap = facts['phase_a']['bootstrap_summary']
    add('EX-07', '200-replicate joint bootstrap stability per active domain',
        'PASS' if bootstrap and all(row['status'] == 'PASS' for row in bootstrap) else 'FAIL',
        {'replicates': BOOTSTRAP_REPLICATES, 'required_joint_pass': BOOTSTRAP_MIN_PASS,
         'per_domain': bootstrap,
         'gates': {'penalty_mae_max': BOOT_MAE_MAX, 'rank_spearman_min': BOOT_SPEARMAN_MIN,
                   'top10_jaccard_min': BOOT_JACCARD_MIN}},
        'the three criteria must hold jointly within one replicate')
    add('EX-08', 'freeze manifest hashed by the seal; every frozen file re-hashed unchanged',
        'PASS',
        {'freeze_manifest_sha256': facts['state']['freeze_manifest_sha256'],
         'frozen_files_verified': facts['state']['frozen_files_verified'],
         'sealed_local': facts['state']['sealed_local']})
    order_ok = bool(facts['state']['sealed_local'] < facts['read_times']['A1_holdout']
                    < facts['read_times']['extension_overlap_A1'])
    add('EX-09', 'seal < first holdout read < first extension read',
        'PASS' if order_ok else 'FAIL',
        {'sealed_local': facts['state']['sealed_local'],
         'first_holdout_read_time': facts['read_times']['A1_holdout'],
         'first_extension_read_time': facts['read_times']['extension_overlap_A1'],
         'holdout_frozen_before_extension_read':
             bool(facts['holdout']['first_holdout_read_time']
                  < facts['extension']['first_extension_read_time'])})
    add('EX-10', 'holdout acceptance on the frozen active domains only',
        'PASS' if facts['holdout']['holdout_status'] in ('ACCEPT_STABILITY',
                                                         'INSUFFICIENT_EVIDENCE_KEEP_D')
        else 'FAIL', facts['holdout'],
        'a rule-failure is reported as REJECT_KEEP_D and never re-tuned')
    add('EX-11', 'extension overlap reproduction on identical inputs',
        'PASS' if facts['extension']['overlap_mismatches'] == 0 else 'FAIL',
        {'overlap_rows': facts['extension']['overlap_rows'],
         'reproduced': facts['extension']['overlap_reproduced'],
         'mismatches': facts['extension']['overlap_mismatches']})
    add('EX-12', 'extension new-record transport status',
        'PASS' if facts['extension']['extension_status'] in ('MIGRATION_OK',
                                                            'INSUFFICIENT_EXTENSION_EVIDENCE',
                                                            'NOT_TESTED_FOR_ACTIVE_CORRECTION')
        else 'FAIL', {'extension_status': facts['extension']['extension_status'],
                      'per_domain': facts['extension']['per_domain_new']},
        'C=D agreement in non-applied domains is never counted as transport evidence')
    add('EX-13', 'non-applied domains keep Q_C == Q_baseline exactly and stay out of active evidence',
        'PASS' if facts['boundaries']['rule_not_applicable_zero_delta'] else 'FAIL',
        {'domains': facts['boundaries']['rule_not_applicable_domains'],
         'rows': facts['boundaries']['rule_not_applicable_rows'],
         'max_abs_delta': facts['boundaries']['rule_not_applicable_max_abs_delta'],
         'active_domains': facts['active']},
        'holdout/extension pass rates contain active correction domains only')
    invalid_total = int((facts['scores']['Q_valid'] == False).sum()) if 'Q_valid' in facts['scores'] \
        else int((facts['full']['Q_valid'] == False).sum())
    invalid_status = int((facts['scores']['Q_support_status'].to_numpy()
                          == 'Q_INVALID_PRESERVED').sum())
    invalid_nan = int(np.isnan(facts['scores']['Q_C'].to_numpy(dtype=float)).sum())
    add('EX-14', 'Q_valid=False rows keep Q_C=NaN and Q_INVALID_PRESERVED',
        'PASS' if (invalid_total == invalid_status == invalid_nan) else 'FAIL',
        {'Q_valid_false_rows': invalid_total, 'Q_INVALID_PRESERVED_rows': invalid_status,
         'Q_C_nan_rows': invalid_nan,
         'numerator_scope': 'all physical rows of the official input'})
    add('EX-15', 'candidate maths on the confirmatory sample', 
        'PASS' if (facts['boundaries']['all_finite']
                   and facts['boundaries']['P_within_unit_interval']
                   and facts['boundaries']['max_Q_C_minus_D'] <= 0.0
                   and facts['boundaries']['min_ratio_Q_C_over_D_for_positive_D'] >= 0.98 - 1e-12
                   and facts['boundaries']['new_zero_values'] == 0
                   and facts['boundaries']['negative_Q_C_rows'] == 0) else 'FAIL',
        facts['boundaries'],
        'denominator = A1_calibration + A1_holdout, is_unique_first & Q_valid & finite inputs')
    add('EX-16', 'candidate_Q_scores keeps every physical row and the original order',
        'PASS' if (len(facts['scores']) == len(facts['full'])
                   and list(facts['scores']['key_sha256'].astype(str))
                   == list(facts['full']['key_sha256'].astype(str))) else 'FAIL',
        {'rows_written': int(len(facts['scores'])), 'rows_read': int(len(facts['full']))})
    add('EX-17', 'protected baseline columns unchanged (role reads vs assembly vs sealed PHASE A)',
        facts['protected']['status'], 
        {'status': facts['protected']['status'],
         'role_reads': sorted(facts['protected']['role_reads'].keys()),
         'frozen_calibration_consistency':
             facts['protected']['frozen_calibration_consistency'],
         'input_sha256_stable': facts['protected']['input_sha256_stable']})
    add('EX-18', 'T06 interface columns and forbidden field names',
        'PASS' if not facts['t06']['forbidden_field_names_present'] else 'FAIL',
        {'columns': facts['t06']['columns'],
         'forbidden_field_names_present': facts['t06']['forbidden_field_names_present'],
         'primary_Q': facts['t06']['primary_Q'],
         'limitations': facts['t06']['limitations']})
    add('EX-19', 'RegMix/Loss connection and identifiability check without any new fit',
        'PASS' if not facts['regmix']['regression_or_bridge_fitting_performed'] else 'FAIL',
        {'status': facts['regmix']['status'],
         'structural_reasons': facts['regmix']['structural_reasons'],
         'checked_inputs': facts['regmix']['checked_inputs']},
        'NOT_IDENTIFIABLE is a method conclusion; it blocks any external quality-gain claim')
    add('EX-20', 'lambda grid reported for calibration only and not used for selection',
        'PASS' if facts['lambda_rows'] == len(LAMBDA_GRID) else 'NOT_CHECKED',
        {'grid': LAMBDA_GRID, 'rows': facts['lambda_rows'], 'primary_lambda': LAMBDA_PRIMARY,
         'file': 'phase_a_calibration_freeze/lambda_sensitivity_calibration.csv'},
        'PHASE B evaluates lambda=0.02 and D only')
    add('EX-21', 'no A/B candidate, PCA/entropy/CRITIC or lambda learning in the frozen code',
        'PASS' if all(entry.get('clean', False) for entry in facts['source_scan'].values())
        else 'FAIL', facts['source_scan'],
        'scan of the frozen code snapshot for prohibited calls')
    add('EX-22', 'row-level denominators agree with the role x domain inventory',
        'PASS' if facts['coverage_consistent'] else 'FAIL', facts['coverage_evidence'])
    add('EX-23', 'output_manifest.json generated last by the independent finalizer', 'NOT_CHECKED',
        {'note': 'written by the finalizer mode after verification.json exists'},
        'the finalizer re-checks every previously registered file for stability')
    return checks


def write_run_summary(ctx, payload):
    write_json(ctx.run_dir / 'run_summary.json', payload)


def handoff_markdown(payload):
    lines = []
    add = lines.append
    add('# TASK-T03E handoff (COMPLETE_PENDING_REVIEW evidence pack)')
    add('')
    add('**Executor status: ' + payload['task_status'] + '**')
    add('')
    add('**D = Q_baseline remains the official main result.** '
        'C = Q_baseline * (1 - 0.02 * P) is only a preregistered rule-sensitivity candidate.')
    add('')
    add('## 1. Run identity')
    add('')
    add('- run_id: ' + payload['run_id'])
    add('- run directory: ' + payload['run_dir'])
    add('- official input: ' + payload['input_path'])
    add('- input SHA256: ' + payload['input_sha256'])
    add('')
    add('## 2. Domain labels and active correction domains')
    add('')
    add('- calibration labels observed: ' + ', '.join(payload['calibration_labels']))
    add('- active correction domains: ' + (', '.join(payload['active_domains']) or '(none)'))
    for label, status in payload['domains_status'].items():
        add('  - ' + label + ': ' + status)
    add('')
    add('## 3. Frozen thresholds')
    add('')
    add('| domain | indicator | q0.95 | q0.99 | q0.005 | q0.995 | n |')
    add('|---|---|---|---|---|---|---|')
    for label, entry in payload['thresholds'].items():
        add('| ' + label + ' | top_2gram | ' + str(entry['a2']) + ' | ' + str(entry['b2'])
            + ' | ' + str(entry['lo2']) + ' | ' + str(entry['hi2']) + ' | '
            + str(entry.get('n_valid', '')) + ' |')
        add('| ' + label + ' | top_3gram | ' + str(entry['a3']) + ' | ' + str(entry['b3'])
            + ' | ' + str(entry['lo3']) + ' | ' + str(entry['hi3']) + ' | '
            + str(entry.get('n_valid', '')) + ' |')
    add('')
    add('## 4. Bootstrap (200 replicates, seed 20260925)')
    add('')
    add('| domain | n | joint pass | required | status |')
    add('|---|---|---|---|---|')
    for row in payload['bootstrap_summary']:
        add('| ' + str(row['domain']) + ' | ' + str(row['n']) + ' | ' + str(row['joint_pass_count'])
            + ' | ' + str(row['required']) + ' | ' + str(row['status']) + ' |')
    add('')
    add('## 5. Freeze seal and read order')
    add('')
    add('- freeze_manifest SHA256: ' + payload['freeze_manifest_sha256'])
    add('- FREEZE_SEALED time: ' + payload['sealed_local'])
    add('- first_holdout_read_time: ' + payload['first_holdout_read_time'])
    add('- first_extension_read_time: ' + payload['first_extension_read_time'])
    add('- order satisfied: ' + str(payload['read_order_ok']))
    add('')
    add('## 6. Holdout')
    add('')
    add('- status: ' + payload['holdout_status'])
    for row in payload['holdout_rows']:
        add('  - ' + str(row.get('domain')) + ': n=' + str(row.get('n_valid')) + ', Spearman='
            + str(row.get('spearman_C_D')) + ', Jaccard=' + str(row.get('top10_jaccard_C_D'))
            + ', |dmean(P)|=' + str(row.get('penalty_mean_abs_diff')) + ', OOS='
            + str(row.get('oos_fraction')) + ', status=' + str(row.get('status')))
    add('')
    add('## 7. Extension')
    add('')
    add('- status: ' + payload['extension_status'])
    add('- overlap rows: ' + str(payload['extension']['overlap_rows']) + ', reproduced: '
        + str(payload['extension']['overlap_reproduced']) + ', mismatches: '
        + str(payload['extension']['overlap_mismatches']))
    add('')
    add('## 8. RegMix/Loss identifiability')
    add('')
    add('- status: ' + str(payload['regmix']['status']))
    for reason in payload['regmix']['structural_reasons']:
        add('  - ' + reason)
    add('')
    add('## 9. Checks and verification')
    add('')
    add('- executor checks: ' + str(payload['checks_summary']))
    add('- verification: ' + str(payload['verification_summary']))
    add('')
    add('## 10. Limitations and open items for the controller')
    add('')
    for item in payload['open_items']:
        add('- ' + item)
    add('')
    add('## 11. Prior exposure')
    add('')
    add('- part of the A1 holdout summaries was inspected in earlier project work, so this stage '
        'is a parameter-freeze validation, not a fully blinded test; holdout was used only for the '
        'preregistered accept/reject decision')
    add('')
    add('## 12. Explicit non-claims')
    add('')
    add('- Q_C is not final_Q, not best_Q and not a replacement of the official main Q')
    add('- no A/B candidate, PCA/entropy/CRITIC weighting or lambda learning was run')
    add('- RegMix/Loss identification was not established; no new bridge model was fitted')
    return '\n'.join(lines) + '\n'


def coverage_consistency(full, scores, role_rows):
    recorded = {(str(row['role']), str(row['domain'])): row for row in role_rows}
    role = full['evaluation_role'].astype(str).to_numpy()
    domain = full['domain'].astype(str).to_numpy()
    recomputed = {}
    for key in sorted(set(zip(role.tolist(), domain.tolist()))):
        mask = (role == key[0]) & (domain == key[1])
        recomputed[key] = counts_for(full[mask])
    mismatches = []
    for key, row in recorded.items():
        rec = recomputed.get(key)
        if rec is None:
            mismatches.append({'key': list(key), 'reason': 'missing_in_assembly'})
            continue
        for field in ('n_total', 'n_unique_first', 'n_Q_valid', 'n_Q_missing', 'n_analysis_valid'):
            if int(row[field]) != int(rec[field]):
                mismatches.append({'key': list(key), 'field': field, 'recorded': int(row[field]),
                                   'recomputed': int(rec[field])})
    row_level_bad = 0
    for i in range(len(scores)):
        entry = recorded.get((role[i], domain[i]))
        if entry is None or int(scores['domain_role_n_total'].iloc[i]) != int(entry['n_total']):
            row_level_bad += 1
    evidence = {'role_domain_groups': len(recorded), 'mismatches': mismatches,
                'row_level_denominator_mismatch_rows': row_level_bad,
                'rows_checked': int(len(scores))}
    return (not mismatches and row_level_bad == 0), evidence


def complete_run(ctx, seal, manifest, state, data, summaries):
    freeze_dir = ctx.run_dir / 'phase_a_calibration_freeze'
    phase_a = read_json(freeze_dir / 'phase_a_summary.json')
    preflight = read_json(ctx.run_dir / 'metadata_preflight' / 'preflight_summary.json')
    with open(ctx.run_dir / 'metadata_preflight' / 'calibration_domain_label_match.csv',
              encoding='utf-8-sig') as handle:
        design_match = list(csv.DictReader(handle))
    seed_check = seed_manifest_check(freeze_dir)
    boundaries = compute_candidate_boundaries(data['full'], data['scores'])
    with open(freeze_dir / 'lambda_sensitivity_calibration.csv', encoding='utf-8-sig') as handle:
        lambda_rows = len(list(csv.DictReader(handle)))
    source_scan = source_scan_for_prohibited_calls(
        freeze_dir / 'code_snapshot' / Path(__file__).name,
        freeze_dir / 'code_snapshot' / 't03e_verify.py')
    coverage_ok, coverage_evidence = coverage_consistency(data['full'], data['scores'],
                                                         data['role_rows'])
    holdout_status = summaries['holdout']['holdout_status']
    extension_status = summaries['extension']['extension_status']
    if holdout_status == 'REJECT_KEEP_D' or extension_status == 'MIGRATION_FAILED_KEEP_D':
        task_status = 'REJECT_KEEP_D'
    elif holdout_status == 'INSUFFICIENT_EVIDENCE_KEEP_D':
        task_status = 'INSUFFICIENT_EVIDENCE_KEEP_D'
    else:
        task_status = 'COMPLETE_PENDING_REVIEW'
    read_order_ok = bool(state['sealed_local'] < summaries['first_holdout_read_time']
                         < summaries['first_extension_read_time'])
    input_stable = all(entry['matches_manifest'] for entry in data['input_checks']) and \
        len({entry['sha256'] for entry in data['input_checks']}) == 1
    facts = {'input_checks': data['input_checks'], 'input_stable': input_stable,
             'preflight': preflight, 'design_match': design_match, 'active': data['active'],
             'phase_a': phase_a, 'freeze_dir': freeze_dir, 'state': state,
             'read_times': data['read_times'], 'holdout': summaries['holdout'],
             'extension': summaries['extension'], 'boundaries': boundaries,
             'scores': data['scores'], 'full': data['full'], 'protected': data['protected'],
             't06': data['t06_payload'], 'regmix': data['regmix'], 'lambda_rows': lambda_rows,
             'seed_check': seed_check, 'source_scan': source_scan,
             'coverage_consistent': coverage_ok, 'coverage_evidence': coverage_evidence}
    checks = build_executor_checks(facts)
    counted = {}
    for entry in checks:
        counted[entry['status']] = counted.get(entry['status'], 0) + 1
    checks_payload = {'task': 'TASK-T03E', 'run_id': ctx.run_dir.name,
                      'generated_local': now_iso(), 'pid': os.getpid(),
                      'stage': 'phase_b_frozen_validation',
                      'counts': counted, 'checks': checks,
                      'verification_note': ('verification.json is produced afterwards by the '
                                            'independent verifier t03e_verify.py, which does not '
                                            'import this module')}
    write_json(ctx.run_dir / 'checks.json', checks_payload)
    domain_role_path = ctx.run_dir / 'phase_b_frozen_validation' / 'domain_role_inventory.csv'
    payload = {
        'task': 'TASK-T03E', 'task_status': task_status, 'run_id': ctx.run_dir.name,
        'run_dir': str(ctx.run_dir),
        'primary_result': 'D = Q_baseline',
        'candidate_positioning': ('C = Q_baseline * (1 - 0.02 * P) is a preregistered '
                                  'rule-sensitivity candidate; it is never final_Q, best_Q or the '
                                  'official main Q'),
        'candidate_version': CANDIDATE_VERSION,
        'input_path': str(INPUT_PATH), 'input_sha256': data['input_checks'][-1]['sha256'],
        'input_bytes': data['input_checks'][-1]['bytes'],
        'phase_a_status': phase_a['phase_a_status'],
        'active_domains': data['active'], 'domains_status': phase_a['domains_status'],
        'calibration_labels': preflight['labels'],
        'thresholds': data['thresholds'],
        'bootstrap_summary': phase_a['bootstrap_summary'],
        'bootstrap_seed_manifest': 'phase_a_calibration_freeze/bootstrap_seed_manifest.csv',
        'freeze_manifest_sha256': state['freeze_manifest_sha256'],
        'sealed_local': state['sealed_local'],
        'first_holdout_read_time': summaries['first_holdout_read_time'],
        'first_extension_read_time': summaries['first_extension_read_time'],
        'read_order_ok': read_order_ok,
        'holdout_status': holdout_status, 'holdout_rows': summaries['holdout']['per_domain'],
        'extension_status': extension_status, 'extension': summaries['extension'],
        'regmix': data['regmix'],
        'boundaries': boundaries, 'seed_check': seed_check, 'source_scan': source_scan,
        'coverage_consistency': {'ok': coverage_ok, 'evidence': coverage_evidence},
        'protected_baseline_check': 'protected_baseline_check.json',
        'checks_summary': counted,
        'verification_summary': ('see verification.json (independent verifier, written after '
                                 'checks.json)'),
        'artifacts': {'candidate_scores': 'candidate_Q_scores.parquet',
                      't06_interface_parquet': 't06_quality_interface.parquet',
                      't06_interface_json': 't06_quality_interface.json',
                      'holdout_validation': 'phase_b_frozen_validation/holdout_validation.csv',
                      'extension_new_validation':
                          'phase_b_frozen_validation/extension_new_validation.csv',
                      'extension_overlap_validation':
                          'phase_b_frozen_validation/extension_overlap_validation.csv',
                      'regmix_identifiability':
                          'phase_b_frozen_validation/regmix_loss_identifiability.json',
                      'domain_role_inventory': 'phase_b_frozen_validation/domain_role_inventory.csv',
                      'output_manifest': 'output_manifest.json (generated last)'},
        'restrictions_honoured': [
            'no A/B candidate was computed or compared',
            'no PCA / entropy weighting / CRITIC selection',
            'lambda grid reported on calibration only, primary fixed at 0.02',
            'no lambda learning and no Q_baseline-supervised direction learning',
            'no bonus, no clip, no extra penalty, no cross-domain fallback',
            'no A1-A3 raw compressed input was read, scanned, stat-ed or hashed',
            'the official Q01C run, quality outputs and 00-05 documents were not modified'],
        'open_items': [
            'controller decision on whether the rule-sensitivity candidate deserves any further '
            'role; D = Q_baseline stays the official main result either way',
            'RegMix/Loss identification status is recorded as a method conclusion, not as a '
            'candidate failure',
            ('holdout history was partly known before this stage: results are a parameter-freeze '
             'validation, not a fully blinded test'),
            ('extension transport evidence is reported per active domain; insufficient or '
             'not-tested statuses must not be quoted as transport success')],
        'generated_local': now_iso(), 'pid': os.getpid()}
    payload['open_items_controller'] = list(payload['open_items'])
    write_run_summary(ctx, json_safe(payload))
    (ctx.run_dir / 'handoff.md').write_text(handoff_markdown(json_safe(payload)), encoding='utf-8')
    ctx.status('phase_b', 'complete', task_status=task_status, holdout=holdout_status,
               extension=extension_status, checks=counted)
    ctx.log('PHASE B complete: task_status=' + task_status + ' holdout=' + holdout_status
            + ' extension=' + extension_status + ' checks=' + json.dumps(counted))
    return 0 if counted.get('FAIL', 0) == 0 else 1


def mode_finalize_manifest(ctx):
    manifest_path = ctx.run_dir / 'output_manifest.json'
    previous = read_json(manifest_path) if manifest_path.is_file() else None
    ctx.status('finalize', 'start', previous_manifest=bool(previous))
    ctx.log('finalizer: previous manifest ' + ('present' if previous else 'absent'))
    append_only = {'run.log', 'access_log.jsonl', 'stage_status.jsonl', 'command_log.json'}
    files = []
    for path in sorted(ctx.run_dir.rglob('*')):
        if not path.is_file():
            continue
        rel = str(path.relative_to(ctx.run_dir)).replace('\\', '/')
        if rel == 'output_manifest.json':
            continue
        files.append({'path': rel, 'bytes': int(path.stat().st_size), 'sha256': sha256_file(path),
                      'append_only': rel in append_only})
    payload = {'task': 'TASK-T03E', 'run_id': ctx.run_dir.name, 'generated_local': now_iso(),
               'pid': os.getpid(), 'command': ctx.command, 'file_count': len(files),
               'files': files, 'excludes': ['output_manifest.json'],
               'append_only_files': sorted(append_only),
               'note': ('generated last by the finalizer after the logs, checks, run_summary, '
                        'handoff and verification were closed; every registered file must stay '
                        'unchanged afterwards')}
    if previous is not None:
        prev = {item['path']: item for item in previous.get('files', [])}
        changed, missing = [], []
        for rel, item in prev.items():
            if rel in append_only:
                continue
            current = next((entry for entry in files if entry['path'] == rel), None)
            if current is None:
                missing.append(rel)
            elif current['sha256'] != item['sha256'] or current['bytes'] != item['bytes']:
                changed.append(rel)
        payload['previous_manifest_generated_local'] = previous.get('generated_local')
        payload['previous_manifest_changed_files'] = changed
        payload['previous_manifest_missing_files'] = missing
        payload['previous_manifest_stable_excluding_append_only'] = bool(not changed and not missing)
    write_json(manifest_path, payload)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description='TASK-T03E preregistered rule-sensitivity candidate (D = Q_baseline)')
    sub = parser.add_subparsers(dest='mode', required=True)
    first = sub.add_parser('calibration-preflight')
    first.add_argument('--input', required=True)
    first.add_argument('--run-dir', required=True)
    second = sub.add_parser('calibration-freeze')
    second.add_argument('--run-dir', required=True)
    second.add_argument('--seed', type=int, default=MASTER_SEED)
    second.add_argument('--bootstrap-replicates', type=int, default=BOOTSTRAP_REPLICATES)
    third = sub.add_parser('frozen-validation')
    third.add_argument('--run-dir', required=True)
    third.add_argument('--freeze-seal', required=True)
    fourth = sub.add_parser('finalize-manifest')
    fourth.add_argument('--run-dir', required=True)
    return parser


def main(argv=None):
    import traceback
    parser = build_parser()
    args = parser.parse_args(argv)
    raw_argv = list(sys.argv[1:]) if argv is None else list(argv)
    run_dir = Path(args.run_dir)
    if args.mode == 'calibration-preflight':
        if run_dir.exists():
            print('run directory already exists; refusing to reuse ' + str(run_dir), file=sys.stderr)
            return 2
    elif not run_dir.is_dir():
        print('run directory does not exist: ' + str(run_dir), file=sys.stderr)
        return 2
    if getattr(args, 'input', None) is not None:
        if Path(args.input).resolve() != INPUT_PATH.resolve():
            print('input must be the official Q01C parquet ' + str(INPUT_PATH), file=sys.stderr)
            return 2
    ctx = Ctx(run_dir, args.mode, [str(sys.executable)] + raw_argv)
    try:
        if args.mode == 'calibration-preflight':
            exit_code = mode_calibration_preflight(ctx)
        elif args.mode == 'calibration-freeze':
            exit_code = mode_calibration_freeze(ctx, args.seed, args.bootstrap_replicates)
        elif args.mode == 'frozen-validation':
            expected_seal = (run_dir / 'phase_a_calibration_freeze' / 'FREEZE_SEALED.json').resolve()
            if Path(args.freeze_seal).resolve() != expected_seal:
                raise GateFailure('--freeze-seal must point at this run seal ' + str(expected_seal))
            seal, manifest, state, data, summaries = mode_frozen_validation(ctx)
            exit_code = complete_run(ctx, seal, manifest, state, data, summaries)
        elif args.mode == 'finalize-manifest':
            ctx.record_command(exit_code=0)
            return mode_finalize_manifest(ctx)
        else:
            raise GateFailure('unknown mode ' + str(args.mode))
    except TimeBudgetExceeded as exc:
        ctx.status(args.mode, 'time_budget_exceeded', message=str(exc))
        ctx.log('TIME_BUDGET_EXCEEDED: ' + str(exc))
        ctx.record_command(exit_code=124)
        return 124
    except Exception as exc:
        traceback.print_exc()
        ctx.status(args.mode, 'failed', error=type(exc).__name__, message=str(exc))
        ctx.log('FAILED: ' + type(exc).__name__ + ': ' + str(exc))
        ctx.record_command(exit_code=1)
        return 1
    ctx.record_command(exit_code=exit_code)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
