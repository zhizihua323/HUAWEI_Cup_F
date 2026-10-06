"""Apply targeted fixes to diagnose_missingness.py inside this run directory."""
import sys
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
TARGET = RUN_DIR / 'diagnose_missingness.py'
text = TARGET.read_text(encoding='utf-8-sig')
ops = []

def rep(name, old, new, expect=1):
    global text
    n = text.count(old)
    if n != expect:
        raise SystemExit(f'PATCH FAILED {name}: expected {expect} occurrences, found {n}')
    text = text.replace(old, new)
    ops.append((name, n))

# P1 float() conversion error capture in get_features (source would raise)
rep('P1_get_features_overflow',
'''        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result[field] = float(value)
        elif isinstance(value, bool):''',
'''        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                result[field] = float(value)
            except (OverflowError, ValueError) as exc:
                result[field] = float('nan')
                if errors is not None:
                    errors.append((field, 'float_conversion_error', type(exc).__name__))
        elif isinstance(value, bool):''')

# P2 row_masks columns
rep('P2_mask_columns',
'''    'extract_nan_bits', 'extract_nonfinite_bits', 'extract_nan_count', 'extract_nonfinite_count',''',
'''    'extract_nan_bits', 'extract_nonfinite_bits', 'extract_posinf_bits', 'extract_neginf_bits',
    'extract_nan_count', 'extract_nonfinite_count',''')
rep('P2_trigger_group_column',
'''    'would_Q_nan_trigger_features', 'q_nan_trigger_features',
    'quality_fingerprint',''',
'''    'would_Q_nan_trigger_features', 'q_nan_trigger_features', 'would_Q_nan_trigger_groups',
    'quality_fingerprint',''')

# P3 store arrays for posinf/neginf
rep('P3_store_init',
'''        self.extract_nonfinite = array('I')
        self.norm_nan = array('H')''',
'''        self.extract_nonfinite = array('I')
        self.extract_posinf = array('I')
        self.extract_neginf = array('I')
        self.norm_nan = array('H')''')
rep('P3_store_append_sig',
'''    def append(self, file_code, line_no, domain_code, flags, raw_bits, ext_nan_bits,
               ext_nf_bits, norm_nan_bits, norm_nf_bits, group_nan_bits, q_nan_bit):''',
'''    def append(self, file_code, line_no, domain_code, flags, raw_bits, ext_nan_bits,
               ext_nf_bits, ext_pos_bits, ext_neg_bits, norm_nan_bits, norm_nf_bits,
               group_nan_bits, q_nan_bit):''')
rep('P3_store_append_body',
'''        self.extract_nonfinite.append(ext_nf_bits)
        self.norm_nan.append(norm_nan_bits)''',
'''        self.extract_nonfinite.append(ext_nf_bits)
        self.extract_posinf.append(ext_pos_bits)
        self.extract_neginf.append(ext_neg_bits)
        self.norm_nan.append(norm_nan_bits)''')
rep('P3_store_finalize',
'''                            ('extract_nonfinite', np.uint32), ('norm_nan', np.uint16),''',
'''                            ('extract_nonfinite', np.uint32), ('extract_posinf', np.uint32),
                            ('extract_neginf', np.uint32), ('norm_nan', np.uint16),''')
rep('P3_extract_bits_init',
'''        ext_nan_bits = 0
        ext_nf_bits = 0
        for feature in FEATURES:''',
'''        ext_nan_bits = 0
        ext_nf_bits = 0
        ext_pos_bits = 0
        ext_neg_bits = 0
        for feature in FEATURES:''')
rep('P3_extract_inf_branch',
'''            elif math.isinf(value):
                ext_nf_bits |= (1 << index)''',
'''            elif math.isinf(value):
                ext_nf_bits |= (1 << index)
                if value > 0:
                    ext_pos_bits |= (1 << index)
                else:
                    ext_neg_bits |= (1 << index)''')
rep('P3_store_append_call',
'''        self.store.append(file_code, line_no, self.domain_code(domain), flags, raw_bits,
                          ext_nan_bits, ext_nf_bits, norm_nan_bits, norm_nf_bits,
                          group_nan_bits, q_nan)''',
'''        self.store.append(file_code, line_no, self.domain_code(domain), flags, raw_bits,
                          ext_nan_bits, ext_nf_bits, ext_pos_bits, ext_neg_bits,
                          norm_nan_bits, norm_nf_bits, group_nan_bits, q_nan)''')
rep('P3_row_columns',
'''            'extract_nan_bits': bits_to_string(ext_nan_bits, len(FEATURES)),
            'extract_nonfinite_bits': bits_to_string(ext_nf_bits, len(FEATURES)),''',
'''            'extract_nan_bits': bits_to_string(ext_nan_bits, len(FEATURES)),
            'extract_nonfinite_bits': bits_to_string(ext_nf_bits, len(FEATURES)),
            'extract_posinf_bits': bits_to_string(ext_pos_bits, len(FEATURES)),
            'extract_neginf_bits': bits_to_string(ext_neg_bits, len(FEATURES)),''')

# P4 aggregation uses posinf/neginf marginals
rep('P4_marginals',
'''            c_nan = marginal_counts(ext_nan_sub, len(FEATURES))
            c_nf = marginal_counts(ext_nf_sub, len(FEATURES))''',
'''            c_nan = marginal_counts(ext_nan_sub, len(FEATURES))
            c_nf = marginal_counts(ext_nf_sub, len(FEATURES))
            c_pos = marginal_counts(arrays['extract_posinf'][idx], len(FEATURES))
            c_neg = marginal_counts(arrays['extract_neginf'][idx], len(FEATURES))''')
rep('P4_posneg_values',
'''                    'n_total': n_g, 'n_nan': int(c_nan[j]), 'n_posinf': 0, 'n_neginf': 0,''',
'''                    'n_total': n_g, 'n_nan': int(c_nan[j]), 'n_posinf': int(c_pos[j]),
                    'n_neginf': int(c_neg[j]),''')

# P5 expose per-file key set for pairwise intersections
rep('P5_current_file_keys',
'''        self.file_stats[file_id] = stats''',
'''        self.current_file_keys = file_seen
        self.file_stats[file_id] = stats''')

# P6 mini selftest realism
rep('P6_mini_row1',
'''        {'fc': 0, 'dom': 0, 'flags': F_PARSE | F_UNIQUE | F_A1 | F_CALIB, 'raw_nan': 1 << FIELD_INDEX['modernbert_professionalism']},''',
'''        {'fc': 0, 'dom': 0, 'flags': F_PARSE | F_UNIQUE | F_A1 | F_CALIB,
         'raw_nan': 1 << FIELD_INDEX['modernbert_professionalism'],
         'model_nan': 1 << MODEL_INDEX['modernbert_professionalism']},''')
rep('P6_mini_unused_line',
'''        model_nan = row.get('model_nan', 0) or model_bits_to_feature_bits(row.get('raw_nan', 0))
        raw_nan = row.get('raw_nan', 0)''',
'''        raw_nan = row.get('raw_nan', 0)''')

# P7 remove stray loop
rep('P7_stray_loop',
'''    for domain, feature in group_stats:
        gs = group_stats[(domain, feature)]
    for domain in ['commoncrawl', 'wikipedia', 'github']:''',
'''    for domain in ['commoncrawl', 'wikipedia', 'github']:''')

# P8 prior attachment only on the matching file view
rep('P8_prior_feature_scope',
'''                    if prior['domain'] != domain or prior['file_id'] not in scope:
                        continue''',
'''                    if prior['domain'] != domain or scope != f"file_unique_first_{prior['file_id']}":
                        continue''')
rep('P8_prior_recovery_scope',
'''                    if prior['domain'] == domain and prior['feature'] == feature and scope.endswith(prior['file_id']):''',
'''                    if (prior['domain'] == domain and prior['feature'] == feature
                            and scope == f"file_unique_first_{prior['file_id']}"):''')

# P9 build_checks tolerates missing prior audit
rep('P9_prior_ref_insert',
'''def build_checks(log, ctx):
    checks = []''',
'''def build_checks(log, ctx):
    checks = []
    prior_audit_ref = ctx.get('prior_audit') or {'total_records': None,
                                                 'unique_id_sub_path_keys': None,
                                                 'duplicate_occurrences': None, 'files': [],
                                                 'quality_conflicts': [], 'domain_collisions': [],
                                                 'pairwise_key_intersections': {}}''')
n_prior = text.count("ctx['prior_audit']")
if n_prior < 1:
    raise SystemExit('PATCH FAILED P9_replace: no ctx[prior_audit] occurrences')
text = text.replace("ctx['prior_audit']", 'prior_audit_ref')
ops.append(('P9_prior_ref_replace', n_prior))

# P10 stricter vacuous-pass guards
rep('P10_c11',
'''        'PASS' if actual == expected else 'FAIL', {'actual': actual, 'expected': expected},''',
'''        'PASS' if (actual == expected and all(v is not None for v in actual.values())) else 'FAIL', {'actual': actual, 'expected': expected},''')
rep('P10_c12',
'''        'PASS' if file_actual == file_expected else 'FAIL',''',
'''        'PASS' if (file_actual and file_actual == file_expected) else ('NOT_CHECKED' if not file_actual else 'FAIL'),''')
rep('P10_c13',
'''        'PASS' if pair_actual == pair_expected else 'FAIL',''',
'''        'PASS' if (pair_actual and pair_actual == pair_expected) else ('NOT_CHECKED' if not pair_actual else 'FAIL'),''')

# P11 duplicate mask conflict counter
rep('P11_dup_conflicts',
'''        'duplicate_rows_with_differing_anomaly_masks': ctx.get('duplicate_mask_conflicts'),''',
'''        'duplicate_rows_with_differing_anomaly_masks': (
            sum(s['duplicate_mask_conflict_rows'] for s in ctx.get('diag').file_stats.values())
            if ctx.get('diag') else None),''')

# P12 output file list for the confinement check
rep('P12_output_files',
'''def finalize(log, ctx, exit_code):
    ctx['exit_code'] = exit_code''',
'''def finalize(log, ctx, exit_code):
    ctx['exit_code'] = exit_code
    ctx['output_files'] = [str(p) for p in sorted(RUN_DIR.rglob('*')) if p.is_file()]''')

# P13 expose diagnostic early for salvage
rep('P13_ctx_diag',
'''        diag = Diagnostic(log, ctx['transforms'], row_writer, invalid_writer)
        diag.key_sets = {file_id: set() for file_id in FILE_IDS}''',
'''        diag = Diagnostic(log, ctx['transforms'], row_writer, invalid_writer)
        ctx['diag'] = diag
        diag.key_sets = {file_id: set() for file_id in FILE_IDS}''')

TARGET.write_text(text, encoding='utf-8-sig')
print('patches applied:')
for name, n in ops:
    print(f'  {name}: {n}')
print('bytes:', TARGET.stat().st_size)
