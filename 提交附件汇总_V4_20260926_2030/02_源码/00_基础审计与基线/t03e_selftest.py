# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
"""TASK-T03E fixture self-test (synthetic only; hand-computed expectations).

This script never reads the official row-level Parquet or any A1-A3 archive.
It exercises the pure candidate/penalty helpers of
t03e_preregistered_rule_sensitivity.py on small hand-built fixtures whose
expected values are written out literally (or derived from the frozen formula
by hand, not by the function under test).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t03e_preregistered_rule_sensitivity as mod  # noqa: E402

RESULTS = []


def check(name, actual, expected, tolerance=0.0, note=''):
    if isinstance(expected, bool) or isinstance(actual, bool):
        ok = bool(actual) == bool(expected)
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        ok = abs(float(actual) - float(expected)) <= tolerance
    else:
        ok = actual == expected
    RESULTS.append({'test': name, 'actual': actual, 'expected': expected,
                    'tolerance': tolerance, 'status': 'PASS' if ok else 'FAIL', 'note': note})
    return ok


def fixture_frame():
    rows = []
    def push(domain, role, unique, q_valid, q, x2, x3, key):
        rows.append({'file_id': 'f', 'source_line': key, 'key_sha256': key, 'domain': domain,
                     'evaluation_role': role, 'is_unique_first': unique, 'overlap_a1': False,
                     'Q_valid': q_valid, 'Q_baseline': q,
                     'rps_doc_frac_chars_top_2gram': x2, 'rps_doc_frac_chars_top_3gram': x3,
                     'dsir_books': 0.1, 'dsir_wiki': 0.2, 'dsir_math': 0.3})
    push('c4', 'A1_calibration', True, True, 0.50, 0.50, 0.50, 'k01')
    push('c4', 'A1_calibration', True, True, 0.40, 1.50, 3.50, 'k02')
    push('c4', 'A1_calibration', True, True, 0.30, 3.00, 3.00, 'k03')
    push('c4', 'A1_calibration', True, False, float('nan'), 2.00, 2.00, 'k04')
    push('book', 'A1_calibration', True, True, 0.60, 9.00, 9.00, 'k05')
    push('github', 'A1_calibration', True, True, 0.70, 9.00, 9.00, 'k06')
    push('c4', 'A1_calibration', True, True, 0.00, 9.00, 9.00, 'k07')
    push('c4', 'A1_calibration', True, True, 0.20, 2.50, 5.00, 'k08')
    return pd.DataFrame(rows)


# The n_valid entries below are declared fixture parameters (a domain that is
# eligible has n_valid >= ACTIVE_MIN_N); they are not derived from the handful of
# toy rows, which only exercise the frozen formula and the status machine.
THRESHOLDS = {'c4': {'a2': 1.0, 'b2': 2.0, 'a3': 3.0, 'b3': 4.0, 'lo2': 0.5, 'hi2': 2.5,
                     'lo3': 2.5, 'hi3': 4.5, 'n_valid': 4000}}
INVENTORY = {'book': {'status': 'INSUFFICIENT_CALIBRATION', 'n_valid': 137},
             'c4': {'status': 'ACTIVE', 'n_valid': 4000},
             'commoncrawl': {'status': 'DESIGN_LABEL_ABSENT', 'n_valid': 0},
             'wikipedia': {'status': 'ACTIVE', 'n_valid': 4000}}
ACTIVE = ['c4', 'wikipedia']


def run():
    # 1. penalty bounds and midpoints, hand-computed
    check('penalty_below_a', mod.penalty_value(0.5, 1.0, 2.0), 0.0)
    check('penalty_at_a', mod.penalty_value(1.0, 1.0, 2.0), 0.0)
    check('penalty_midpoint', mod.penalty_value(1.5, 1.0, 2.0), 0.5, 1e-15)
    check('penalty_at_b', mod.penalty_value(2.0, 1.0, 2.0), 1.0)
    check('penalty_above_b', mod.penalty_value(9.0, 1.0, 2.0), 1.0)
    grid = np.linspace(0.0, 3.0, 61)
    pen = mod.penalty_array(grid, 1.0, 2.0)
    check('penalty_monotone', bool(np.all(np.diff(pen) >= 0.0)), True)
    check('penalty_in_unit_interval', bool(np.all((pen >= 0.0) & (pen <= 1.0))), True)
    # 2. cluster mean and fixed weight (duplication must not change P)
    p2 = mod.penalty_value(1.5, 1.0, 2.0)
    p3 = mod.penalty_value(3.5, 3.0, 4.0)
    check('cluster_mean_hand', (p2 + p3) / 2, 0.5, 1e-15)
    check('duplicate_member_no_extra_weight', (p2 + p3 + p2) / 2 - (p2 / 2), (p2 + p3) / 2, 1e-15,
          'adding a third copy of the same member must not be part of the frozen rule')
    # 3. lambda = 0 identity and candidate bounds
    cand0 = mod.apply_candidate(fixture_frame(), THRESHOLDS, ACTIVE, INVENTORY, lam=0.0)
    frame = fixture_frame()
    q = frame['Q_baseline'].to_numpy(dtype=float)
    finite = np.isfinite(q)
    check('lambda_zero_identity', float(np.nanmax(np.abs(cand0['Q_C'][finite] - q[finite]))), 0.0,
          1e-15)
    cand = mod.apply_candidate(fixture_frame(), THRESHOLDS, ACTIVE, INVENTORY)
    qc = cand['Q_C']
    check('candidate_le_D', float(np.nanmax(qc[finite] - q[finite])), 0.0, 1e-15)
    positive = finite & (q > 0)
    min_ratio = float(np.nanmin(qc[positive] / q[positive]))
    check('candidate_ge_098_D', bool(min_ratio >= 0.98 - 1e-12), True, note='min ratio='
          + repr(min_ratio))
    check('full_penalty_saturates_hand', float(cand['P'][7]), 1.0, 1e-15)
    check('full_penalty_candidate_hand', float(qc[7]), 0.20 * 0.98, 1e-15)
    check('boundary_row_out_of_support', str(cand['Q_support_status'][7]), 'OUT_OF_SUPPORT')
    check('no_new_zero', int(np.sum((q > 0) & (qc == 0))), 0)
    check('existing_zero_kept', float(qc[6]), 0.0, 0.0)
    # 4. statuses
    status = cand['Q_support_status']
    check('github_rule_not_applicable', str(status[5]), 'RULE_NOT_APPLICABLE')
    check('book_insufficient_calibration', str(status[4]), 'INSUFFICIENT_CALIBRATION')
    check('q_invalid_preserved', str(status[3]), 'Q_INVALID_PRESERVED')
    check('q_invalid_nan', bool(np.isnan(qc[3])), True)
    check('github_identity_hand', float(qc[5]), 0.70, 1e-15)
    check('book_identity_hand', float(qc[4]), 0.60, 1e-15)
    check('c4_midpoint_penalty_hand', float(cand['P'][1]), 0.5, 1e-15)
    check('c4_candidate_hand', float(qc[1]), 0.40 * (1 - 0.02 * 0.5), 1e-15)
    check('c4_oos_row', str(status[2]), 'OUT_OF_SUPPORT')
    # 5. degenerate / unknown / missing label / fallback guards
    degenerate = dict(INVENTORY)
    degenerate['c4'] = {'status': 'CALIBRATION_DEGENERATE', 'n_valid': 4000}
    try:
        mod.domain_status_for('c4', degenerate)
        check('degenerate_raises', False, True)
    except mod.GateFailure:
        check('degenerate_raises', True, True)
    absent = dict(INVENTORY)
    absent['c4'] = {'status': 'DESIGN_LABEL_ABSENT', 'n_valid': 0}
    check('design_label_absent_status', mod.domain_status_for('c4', absent), 'DESIGN_LABEL_ABSENT')
    check('unknown_domain_not_applicable', mod.domain_status_for('arxiv', INVENTORY),
          'RULE_NOT_APPLICABLE')
    bad = fixture_frame()
    bad.loc[0, 'rps_doc_frac_chars_top_2gram'] = float('nan')
    try:
        mod.apply_candidate(bad, THRESHOLDS, ACTIVE, INVENTORY)
        check('non_finite_active_input_raises', False, True)
    except mod.GateFailure:
        check('non_finite_active_input_raises', True, True)
    # 6. ordering / spearman / jaccard on hand fixtures
    keys = np.array(['b', 'a', 'c'], dtype=object)
    order = mod.deterministic_order(np.array([0.5, 0.5, 0.9]), keys)
    check('deterministic_order_hand', list(order.tolist()), [2, 1, 0],
          note='0.9 first, then the tied 0.5 pair broken by the frozen key order a<b')
    ranks_a, _ = mod.rank_vector(np.array([1.0, 2.0, 3.0]), np.array(['x', 'y', 'z'], dtype=object))
    ranks_b, _ = mod.rank_vector(np.array([1.0, 2.0, 3.0]), np.array(['x', 'y', 'z'], dtype=object))
    check('spearman_identity_hand', mod.spearman_from_ranks(ranks_a, ranks_b), 1.0, 1e-15)
    check('jaccard_identical_hand', mod.jaccard({1, 2}, {1, 2}), 1.0, 1e-15)
    check('jaccard_disjoint_hand', mod.jaccard({1}, {2}), 0.0, 1e-15)
    top, k = mod.top_set(np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]), 10)
    check('top_k_ceil_hand', k, 1)
    # 7. bootstrap seed rule (recomputed independently with hashlib)
    expected_seed = int(hashlib.sha256('20260925|c4|7'.encode('utf-8')).hexdigest()[:16], 16)
    check('bootstrap_seed_matches_sha256', mod.bootstrap_seed('c4', 7), expected_seed)
    check('bootstrap_seed_string', mod.bootstrap_seed('c4', 7),
          int(hashlib.sha256('20260925|c4|7'.encode()).hexdigest()[:16], 16))
    # 8. access time helper on synthetic log
    class FakeCtx:
        def __init__(self, path):
            self.access_path = path
    tmp = Path(__file__).resolve().parent.parent.parent / 'tmp' / 't03e_selftest_access.jsonl'
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text('{"ts": "t1", "purpose": "other"}\n{"ts": "t2", "purpose": "calibration '
                   'partition preflight"}\n', encoding='utf-8')
    check('first_access_time_hand', mod.first_access_time(FakeCtx(tmp), 'calibration partition'),
          't2')
    failed = [item for item in RESULTS if item['status'] != 'PASS']
    for item in RESULTS:
        print(('PASS ' if item['status'] == 'PASS' else 'FAIL ') + item['test'] + ' actual='
              + repr(item['actual']) + ' expected=' + repr(item['expected']))
    print('TOTAL=' + str(len(RESULTS)) + ' FAILED=' + str(len(failed)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(run())
