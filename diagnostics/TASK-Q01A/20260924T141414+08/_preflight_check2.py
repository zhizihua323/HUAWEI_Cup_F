import sys, json
from pathlib import Path
RUN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN_DIR))
import diagnose_missingness as dm

class P:
    def __call__(self, m): pass
log = P()
prior_audit = dm.read_json(dm.QUALITY_OUT / 'audit.json')
fake_file_stats = {}
fake_key_sets = {}
fake_raw_prior = {}
fake_raw_detail = {}
for f in prior_audit['files']:
    fid = f['file_id']
    fake_file_stats[fid] = {'rows': f['rows'], 'invalid_json': 0, 'decode_errors': 0,
                            'json_structure_errors': 0, 'line_count': f['rows'],
                            'source_domain_missing': 0, 'within_file_duplicate_rows': f['within_file_duplicate_rows'],
                            'overlap_a1_rows': f['overlapping_a1_rows'], 'quality_conflicting_rows': 0,
                            'domain_collision_rows': 0, 'duplicate_mask_conflict_rows': 0,
                            'fingerprint_error_rows': 0, 'domains': f['domains'],
                            'decompress_passes': 1, 'retries': 0, 'elapsed_s': 0.0}
    fake_key_sets[fid] = set()
    for dom in f['domains']:
        fake_raw_prior[(f['code'] if 'code' in f else {'A1':0,'A2_arxiv':1,'A3_github':2}[fid], dom)] = {x: dm.empty_prior_stats() for x in dm.FIELDS}
        fake_raw_detail[({'A1':0,'A2_arxiv':1,'A3_github':2}[fid], dom)] = {x: dm.empty_detail_stats() for x in dm.FIELDS}
diag_view = {'prior_audit': prior_audit,
             'prior_domain_summary': dm.read_csv_rows(dm.QUALITY_OUT / 'domain_summary.csv'),
             'prior_feature_summary': dm.read_csv_rows(dm.QUALITY_OUT / 'feature_summary.csv'),
             'prior_extension_shift': dm.read_csv_rows(dm.QUALITY_OUT / 'extension_shift.csv'),
             'prior_recovery_deficits': dm.read_json(dm.RECOVERY / 'quality_gap_evidence.json')['feature_deficits'],
             'prior_mean_discrepancies': dm.read_csv_rows(dm.RECOVERY / 'quality_mean_discrepancies.csv'),
             'raw_prior': fake_raw_prior, 'raw_detail': fake_raw_detail, 'file_stats': fake_file_stats}
totals = {'total_records': prior_audit['total_records'], 'unique_keys': prior_audit['unique_id_sub_path_keys'],
          'duplicate_rows': prior_audit['duplicate_occurrences'],
          'pairwise_intersections': dict(prior_audit['pairwise_key_intersections']),
          'quality_conflicts': 0, 'domain_collisions': 0,
          'file_unique': {f['file_id']: f['unique_id_sub_path_keys_in_file'] for f in prior_audit['files']}}
group_stats = {('A1_calibration', 'commoncrawl'): {'n': 7691, 'complete11': 7691, 'complete25': 7691,
                                                   'n_valid_mainQ_11': 7691,
                                                   'nan_counts': {f: 0 for f in dm.FEATURES},
                                                   'nan_by_category': {f: {'A1': 0, 'extension_new': 0, 'extension_overlap': 0} for f in dm.FEATURES},
                                                   'n_by_category': {'A1': 7691, 'extension_new': 0, 'extension_overlap': 0}}}
comp = dm.build_prior_comparison(diag_view, group_stats, totals)
known = dm.build_known_domain_comparison(diag_view, group_stats)
print('comparison rows:', len(comp))
print('known rows:', len(known), 'example:', json.dumps(known[0], ensure_ascii=False)[:300] if known else None)
print('match counts:', {m: sum(1 for r in comp if r['match'] == m) for m in ('MATCH', 'MISMATCH', 'NOT_COMPARABLE')})
ctx = {'status': 'COMPLETE_DIAGNOSTIC', 'errors': [], 'unfinished': [], 'stage_seconds': {},
       'prior_audit': prior_audit}
checks = dm.build_checks(log, ctx)
print('checks:', len(checks), {s: sum(1 for c in checks if c['status'] == s) for s in ('PASS', 'FAIL', 'NOT_CHECKED')})
fails = [c['check_id'] for c in checks if c['status'] == 'FAIL']
print('failing (expected without a scan):', fails)
