"""Synthetic smoke test for the TASK-T03E PHASE B writers (no real data)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent / 'solution' / 'src'
sys.path.insert(0, str(SRC))
import t03e_preregistered_rule_sensitivity as mod  # noqa: E402

RUN = Path(__file__).resolve().parent / 't03e_smoke_run'
if RUN.exists():
    shutil.rmtree(RUN)
(RUN / 'phase_b_frozen_validation').mkdir(parents=True)
(RUN / 'metadata_preflight').mkdir(parents=True)


class FakeCtx:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)


def build_frame():
    rows = []
    def push(role, domain, key, unique, q_valid, q, x2, x3):
        rows.append({'file_id': 'F', 'source_line': key[-2:], 'key_sha256': key, 'domain': domain,
                     'evaluation_role': role, 'is_unique_first': unique, 'overlap_a1': False,
                     'Q_valid': q_valid, 'Q_baseline': q, 'rps_doc_frac_chars_top_2gram': x2,
                     'rps_doc_frac_chars_top_3gram': x3, 'dsir_books': 0.1, 'dsir_wiki': 0.2,
                     'dsir_math': 0.3})
    push('A1_calibration', 'c4', 'k01', True, True, 0.5, 1.0, 3.0)
    push('A1_calibration', 'c4', 'k02', True, True, 0.4, 2.5, 5.0)
    push('A1_calibration', 'github', 'k03', True, True, 0.6, 2.0, 2.0)
    push('A1_calibration', 'book', 'k04', True, False, float('nan'), 2.0, 2.0)
    push('A1_holdout', 'c4', 'k05', True, True, 0.3, 1.5, 3.5)
    push('A1_holdout', 'github', 'k06', True, True, 0.7, 1.5, 3.5)
    push('extension_overlap_A1', 'c4', 'k01', True, True, 0.5, 1.0, 3.0)
    push('extension_new_records', 'c4', 'k07', True, True, 0.2, 1.7, 3.7)
    push('extension_new_records', 'github', 'k08', True, True, 0.9, 1.7, 3.7)
    return pd.DataFrame(rows)


THRESHOLDS = {'c4': {'a2': 1.0, 'b2': 2.0, 'lo2': 0.5, 'hi2': 2.5, 'a3': 3.0, 'b3': 4.0,
                     'lo3': 2.5, 'hi3': 4.5, 'n_valid': 4000}}
INVENTORY = {'book': {'status': 'INSUFFICIENT_CALIBRATION', 'n_valid': 137},
             'c4': {'status': 'ACTIVE', 'n_valid': 4000},
             'commoncrawl': {'status': 'DESIGN_LABEL_ABSENT', 'n_valid': 0},
             'wikipedia': {'status': 'ACTIVE', 'n_valid': 4000}}
ACTIVE = ['c4']
ROLE_ORDER = ['A1_calibration', 'A1_holdout', 'extension_overlap_A1', 'extension_new_records']

ctx = FakeCtx(RUN)
full = build_frame()
cand = mod.apply_candidate(full, THRESHOLDS, ACTIVE, INVENTORY)
frames = {role: full[full['evaluation_role'].astype(str) == role] for role in ROLE_ORDER}
read_times = {role: '2026-09-25T00:00:0' + str(i) + '.000+08:00'
              for i, role in enumerate(ROLE_ORDER)}

role_rows, label_rows, match_rows = mod.write_domain_role_outputs(ctx, frames, read_times, INVENTORY)
scores, scores_path = mod.write_candidate_scores(ctx, full, cand, role_rows)
t06_frame, t06_payload = mod.write_t06_interface(ctx, full, scores, role_rows, 'deadbeef', 
                                                 {'status': 'NOT_IDENTIFIABLE',
                                                  'structural_reasons': ['synthetic reason']})
input_checks = [{'sha256': 'abc', 'bytes': 10, 'matches_manifest': True,
                 'manifest_sha256': 'abc'}]
frozen_calibration = frames['A1_calibration'].copy()
calib_cand = mod.apply_candidate(frozen_calibration, THRESHOLDS, ACTIVE, INVENTORY)
for column in ('p_top2gram', 'p_top3gram', 'P', 'Q_C', 'Q_support_status'):
    frozen_calibration[column] = calib_cand[column]
protected = mod.write_protected_baseline_check(ctx, input_checks, full, frames, scores,
                                               frozen_calibration)
ok, evidence = mod.coverage_consistency(full, scores, role_rows)
boundaries = mod.compute_candidate_boundaries(full, scores)
payload = {'task_status': 'COMPLETE_PENDING_REVIEW', 'run_id': 'synthetic', 'run_dir': str(RUN),
           'input_path': 'x', 'input_sha256': 'y', 'calibration_labels': ['book', 'c4'],
           'active_domains': ACTIVE, 'domains_status': {'book': 'INSUFFICIENT_CALIBRATION'},
           'thresholds': THRESHOLDS, 'bootstrap_summary': [
               {'domain': 'c4', 'n': 2, 'joint_pass_count': 200, 'required': 190, 'status': 'PASS'}],
           'freeze_manifest_sha256': 'z', 'sealed_local': 't0',
           'first_holdout_read_time': 't1', 'first_extension_read_time': 't2',
           'read_order_ok': True, 'holdout_status': 'ACCEPT_STABILITY',
           'holdout_rows': [{'domain': 'c4', 'n_valid': 1, 'spearman_C_D': 1.0,
                             'top10_jaccard_C_D': 1.0, 'penalty_mean_abs_diff': 0.0,
                             'oos_fraction': 0.0, 'status': 'PASS'}],
           'extension_status': 'MIGRATION_OK',
           'extension': {'overlap_rows': 1, 'overlap_reproduced': 1, 'overlap_mismatches': 0},
           'regmix': {'status': 'NOT_IDENTIFIABLE', 'structural_reasons': ['r']},
           'checks_summary': {'PASS': 20}, 'verification_summary': 'pending',
           'open_items': ['item']}
handoff = mod.handoff_markdown(mod.json_safe(payload))
(RUN / 'handoff_smoke.md').write_text(handoff, encoding='utf-8')

report = {
    'role_rows': len(role_rows), 'label_rows': len(label_rows), 'match_rows': len(match_rows),
    'scores_rows': int(len(scores)), 'scores_columns': list(scores.columns),
    't06_rows': int(len(t06_frame)), 't06_forbidden': t06_payload['forbidden_field_names_present'],
    'protected_status': protected['status'], 'coverage_ok': ok,
    'boundaries': boundaries, 'handoff_lines': len(handoff.splitlines()),
    'status_sequence': scores['Q_support_status'].astype(str).tolist(),
    'Q_C': [None if np.isnan(v) else float(v) for v in scores['Q_C'].to_numpy(dtype=float)],
    'in_confirmatory': scores['in_confirmatory_denominator'].tolist(),
    'denominator_n_total': scores['domain_role_n_total'].tolist(),
}
print(json.dumps(report, indent=2, ensure_ascii=False))
failures = []
if report['scores_rows'] != len(full):
    failures.append('row count')
if report['protected_status'] != 'PASS':
    failures.append('protected baseline: ' + str(report['protected_status']))
if not report['coverage_ok']:
    failures.append('coverage consistency')
if report['t06_forbidden']:
    failures.append('forbidden field names')
if len(report['status_sequence']) != len(full):
    failures.append('status length')
print('SMOKE_FAILURES=' + str(failures))
sys.exit(1 if failures else 0)
