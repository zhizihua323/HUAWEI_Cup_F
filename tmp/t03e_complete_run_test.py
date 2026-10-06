"""Synthetic end-to-end test of complete_run/build_executor_checks/handoff (no real data)."""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent / 'solution' / 'src'
sys.path.insert(0, str(SRC))
import t03e_preregistered_rule_sensitivity as mod  # noqa: E402

RUN = Path(__file__).resolve().parent / 't03e_complete_run'
if RUN.exists():
    shutil.rmtree(RUN)
FREEZE = RUN / 'phase_a_calibration_freeze'
PRE = RUN / 'metadata_preflight'
PHASE_B = RUN / 'phase_b_frozen_validation'
for path in (FREEZE / 'code_snapshot', PRE, PHASE_B):
    path.mkdir(parents=True, exist_ok=True)


class FakeCtx:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.mode = 'synthetic'
        self.command = ['python', 'synthetic']
        self.status_path = self.run_dir / 'stage_status.jsonl'
        self.access_path = self.run_dir / 'access_log.jsonl'
        self.log_path = self.run_dir / 'run.log'

    def log(self, message):
        pass

    def status(self, stage, event, **fields):
        pass

    def access(self, *args, **kwargs):
        return {}


def build_frame():
    rows = []
    def push(role, domain, key, unique, q_valid, q, x2, x3):
        rows.append({'file_id': 'F', 'source_line': key[-2:], 'key_sha256': key, 'domain': domain,
                     'evaluation_role': role, 'is_unique_first': unique, 'overlap_a1': False,
                     'Q_valid': q_valid, 'Q_baseline': q, 'rps_doc_frac_chars_top_2gram': x2,
                     'rps_doc_frac_chars_top_3gram': x3, 'dsir_books': 0.1, 'dsir_wiki': 0.2,
                     'dsir_math': 0.3})
    for index in range(3):
        push('A1_calibration', 'c4', 'k%02d' % index, True, True, 0.5 - 0.05 * index,
             1.0 + 0.2 * index, 3.0 + 0.2 * index)
    push('A1_calibration', 'github', 'k90', True, True, 0.6, 2.0, 2.0)
    push('A1_calibration', 'book', 'k91', True, False, float('nan'), 2.0, 2.0)
    for index in range(3):
        push('A1_holdout', 'c4', 'h%02d' % index, True, True, 0.4 - 0.05 * index,
             1.2 + 0.2 * index, 3.2 + 0.2 * index)
    push('A1_holdout', 'github', 'h90', True, True, 0.7, 1.5, 3.5)
    push('extension_overlap_A1', 'c4', 'k00', True, True, 0.5, 1.0, 3.0)
    push('extension_new_records', 'c4', 'n00', True, True, 0.2, 1.7, 3.7)
    push('extension_new_records', 'github', 'n90', True, True, 0.9, 1.7, 3.7)
    return pd.DataFrame(rows)


THRESHOLDS = {'c4': {'a2': 1.0, 'b2': 2.0, 'lo2': 0.5, 'hi2': 2.5, 'a3': 3.0, 'b3': 4.0,
                     'lo3': 2.5, 'hi3': 4.5}}
INVENTORY = {'book': {'status': 'INSUFFICIENT_CALIBRATION', 'n_valid': 137},
             'c4': {'status': 'ACTIVE', 'n_valid': 4000},
             'commoncrawl': {'status': 'DESIGN_LABEL_ABSENT', 'n_valid': 0},
             'wikipedia': {'status': 'ACTIVE', 'n_valid': 4000}}
ACTIVE = ['c4']
ROLES = ['A1_calibration', 'A1_holdout', 'extension_overlap_A1', 'extension_new_records']

ctx = FakeCtx(RUN)
full = build_frame()
candidate = mod.apply_candidate(full, THRESHOLDS, ACTIVE, INVENTORY)
frames = {role: full[full['evaluation_role'].astype(str) == role] for role in ROLES}
read_times = {role: '2026-09-25T00:00:0' + str(i) + '.000+08:00'
              for i, role in enumerate(ROLES)}
role_rows, _, _ = mod.write_domain_role_outputs(ctx, frames, read_times, INVENTORY)
scores, _ = mod.write_candidate_scores(ctx, full, candidate, role_rows)
frozen_calibration = frames['A1_calibration'].copy()
calib_candidate = mod.apply_candidate(frozen_calibration, THRESHOLDS, ACTIVE, INVENTORY)
for column in ('p_top2gram', 'p_top3gram', 'P', 'Q_C', 'Q_support_status'):
    frozen_calibration[column] = calib_candidate[column]
input_checks = [{'note': 'synthetic', 'path': 'x', 'bytes': 10, 'sha256': 'a' * 64,
                 'manifest_bytes': 10, 'manifest_sha256': 'a' * 64, 'matches_manifest': True,
                 'checked_local': 't', 'pid': 1}]
protected = mod.write_protected_baseline_check(ctx, input_checks, full, frames, scores,
                                               frozen_calibration)
t06_frame, t06_payload = mod.write_t06_interface(ctx, full, scores, role_rows, 'f' * 64,
                                                 {'status': 'NOT_IDENTIFIABLE',
                                                  'structural_reasons': ['synthetic']})
# frozen artefacts that complete_run reads
mod.write_csv(PRE / 'calibration_domain_label_match.csv',
              ['design_label', 'present_in_calibration', 'exact_match', 'status',
               'calibration_valid_n'],
              [{'design_label': 'book', 'present_in_calibration': True, 'exact_match': True,
                'status': 'EXACT_MATCH', 'calibration_valid_n': 0},
               {'design_label': 'c4', 'present_in_calibration': True, 'exact_match': True,
                'status': 'EXACT_MATCH', 'calibration_valid_n': 3},
               {'design_label': 'commoncrawl', 'present_in_calibration': False,
                'exact_match': False, 'status': 'DESIGN_LABEL_ABSENT', 'calibration_valid_n': 0},
               {'design_label': 'wikipedia', 'present_in_calibration': True, 'exact_match': True,
                'status': 'EXACT_MATCH', 'calibration_valid_n': 4000}])
mod.write_json(PRE / 'preflight_summary.json',
               {'analysis_layer_roles_visible': ['A1_calibration'], 'labels': ['book', 'c4',
                                                                              'github'],
                'commitment': {'calibration_physical_rows': 5, 'calibration_unique_first_rows': 5},
                'design_match': [], 'input_check': input_checks[0], 'holdout_or_extension_read': False,
                'generated_local': 't'})
mod.write_json(FREEZE / 'phase_a_summary.json',
               {'phase_a_status': mod.PHASE_A_QUALIFIED, 'bootstrap_summary': [
                   {'domain': 'c4', 'n': 3, 'replicates': 200, 'joint_pass_count': 200,
                    'required': 190, 'status': 'PASS'}],
                'domains_status': {label: INVENTORY[label]['status'] for label in
                                   mod.DESIGN_DOMAINS},
                'active_domains': ACTIVE, 'lambda_rows': 4,
                'artificial_tests_status': 'PASS'})
mod.write_csv(FREEZE / 'frozen_thresholds.csv',
              ['domain', 'indicator', 'a_q95', 'b_q99', 'lo_q005', 'hi_q995', 'n_valid_source',
               'source_scope'],
              [{'domain': 'c4', 'indicator': 'top_2gram', 'a_q95': 1.0, 'b_q99': 2.0,
                'lo_q005': 0.5, 'hi_q995': 2.5, 'n_valid_source': 4000, 'source_scope': 'x'},
               {'domain': 'c4', 'indicator': 'top_3gram', 'a_q95': 3.0, 'b_q99': 4.0,
                'lo_q005': 2.5, 'hi_q995': 4.5, 'n_valid_source': 4000, 'source_scope': 'x'}])
mod.write_csv(FREEZE / 'lambda_sensitivity_calibration.csv',
              ['lambda', 'n_rows', 'n_finite_penalty', 'penalty_mean', 'penalty_max',
               'penalty_p50', 'penalty_p95', 'spearman_vs_D', 'top10_jaccard_vs_D',
               'new_zero_values', 'oos_rows', 'rule_not_applicable_rows', 'primary'],
              [{'lambda': value, 'primary': int(value == 0.02)} for value in mod.LAMBDA_GRID])
tests = mod.run_artificial_tests()
mod.write_json(FREEZE / 'artificial_tests.json', tests)
seed_rows = []
for replicate in range(mod.BOOTSTRAP_REPLICATES):
    seed_rows.append({'domain': 'c4', 'replicate': replicate,
                      'seed': mod.bootstrap_seed('c4', replicate), 'n_resample': 3,
                      'reference_rows': 3, 'sub_seed_rule': 'x', 'rng': 'x'})
mod.write_csv(FREEZE / 'bootstrap_seed_manifest.csv',
              ['domain', 'replicate', 'seed', 'n_resample', 'reference_rows', 'sub_seed_rule',
               'rng'], seed_rows)
snapshot = FREEZE / 'code_snapshot'
for name in ('t03e_preregistered_rule_sensitivity.py', 't03e_verify.py', 't03e_selftest.py'):
    shutil.copy2(SRC / name, snapshot / name)
state = {'sealed_local': '2026-09-25T00:00:00+08:00', 'freeze_manifest_sha256': 'f' * 64,
         'frozen_files_verified': 10, 'thresholds': THRESHOLDS, 'active_domains': ACTIVE,
         'domains_status': {label: INVENTORY[label]['status'] for label in mod.DESIGN_DOMAINS},
         'source_code_sha256': {}}
holdout_rows = [{'domain': 'c4', 'role': 'A1_holdout', 'n_valid': 3, 'min_valid_n': 200,
                 'eligible': 0, 'spearman_C_D': None, 'top10_jaccard_C_D': None,
                 'penalty_mean_role': None, 'penalty_mean_calibration': None,
                 'penalty_mean_abs_diff': None, 'oos_rows': None, 'oos_fraction': None,
                 'pass_spearman': 0, 'pass_jaccard': 0, 'pass_penalty_mean': 0, 'pass_oos': 0,
                 'status': 'INSUFFICIENT_N'}]
summaries = {'holdout': {'holdout_status': 'INSUFFICIENT_EVIDENCE_KEEP_D', 'per_domain': holdout_rows,
                         'first_holdout_read_time': '2026-09-25T00:00:02.000+08:00'},
             'extension': {'extension_status': 'INSUFFICIENT_EXTENSION_EVIDENCE',
                           'overlap_rows': 1, 'overlap_reproduced': 1, 'overlap_mismatches': 0,
                           'per_domain_new': [], 'first_extension_read_time':
                               '2026-09-25T00:00:03.000+08:00'},
             'first_holdout_read_time': '2026-09-25T00:00:02.000+08:00',
             'first_extension_read_time': '2026-09-25T00:00:03.000+08:00'}
data = {'full': full, 'scores': scores, 'role_rows': role_rows, 'read_times': read_times,
        'active': ACTIVE, 'thresholds': THRESHOLDS, 'inventory': INVENTORY,
        'regmix': {'status': 'NOT_IDENTIFIABLE', 'structural_reasons': ['synthetic'],
                   'regression_or_bridge_fitting_performed': False,
                   'new_models_or_scalers_fitted': False, 'checked_inputs': {}},
        't06_payload': t06_payload, 'protected': protected, 'input_checks': input_checks,
        'calibration': frozen_calibration, 'holdout': frames['A1_holdout'],
        'extension': frames['extension_overlap_A1']}
manifest = {'frozen_files': [], 'config_sha256': 'x', 'config_file': 'run_config.json'}
code = mod.complete_run(ctx, {'sealed_local': state['sealed_local']}, manifest, state, data,
                        summaries)
print('complete_run returned', code)
payload = json.load(open(RUN / 'run_summary.json', encoding='utf-8'))
print('task_status', payload['task_status'])
print('checks_summary', payload['checks_summary'])
failed = [item['id'] for item in json.load(open(RUN / 'checks.json', encoding='utf-8'))['checks']
          if item['status'] == 'FAIL']
print('FAILED_CHECKS', failed)
print('handoff_bytes', (RUN / 'handoff.md').stat().st_size)
sys.exit(1 if failed else 0)
