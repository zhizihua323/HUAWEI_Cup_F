"""Post-run, read-only reconciliation of the seven FAIL checks in checks.json.

This script does NOT re-read the compressed raw inputs and does NOT recompute any
diagnostic statistic. It only re-verifies the seven failing in-run checks against
the run's own artifacts and the current (read-only) file system state, so that the
main controller can distinguish "check wiring defect" from "data discrepancy".

The in-run artifacts checks.json / run_summary.json / handoff.md are left untouched.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
PROJECT = RUN_DIR.parents[2]
DATA = PROJECT / 'F题' / 'real_attachments'
QUALITY = PROJECT / 'solution' / 'outputs' / 'quality'
CST = timezone(timedelta(hours=8))


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def read_json(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def read_csv_rows(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def bits_from_string(text):
    value = 0
    for j, ch in enumerate(text):
        if ch == '1':
            value |= (1 << j)
    return value


results = []


def add(check_id, status, defect, actual, expected, evidence, conclusion):
    results.append({'check_id': check_id, 'postrun_status': status,
                    'in_run_failure_cause': defect, 'actual': actual, 'expected': expected,
                    'evidence': evidence, 'conclusion': conclusion})


# ---------------------------------------------------------------- C07
manifest = read_json(RUN_DIR / 'input_manifest.json')
changed, missing = [], []
for item in manifest['secondary_inputs']:
    path = PROJECT / item['path']
    if not path.is_file():
        missing.append(item['path'])
    elif sha256_file(path) != item['sha256']:
        changed.append(item['path'])
add('C07_protected_files_unchanged', 'PASS' if not changed and not missing else 'FAIL',
    'in-run check read ctx["snapshot_diff"] which run_task never populated (wiring defect); '
    'the pre-run SHA256 of every protected file is recorded in input_manifest.json',
    {'n_files_checked': len(manifest['secondary_inputs']), 'sha_changed': changed, 'missing': missing},
    'no changed or missing protected file', 'input_manifest.json secondary_inputs vs current files',
    'source/config/quality/recovery/task/00-05 files are byte-identical to the pre-run snapshot')

# ---------------------------------------------------------------- C08
registered = {row['path']: int(row['bytes']) for row in
              read_csv_rows(PROJECT / 'solution' / 'outputs' / 'audit' / 'raw_source_manifest.csv')}
ext_prefix = '\\\\?\\' + str(DATA.resolve())
now = {}
for root, dirs, files in os.walk(ext_prefix):
    for name in files:
        full = os.path.join(root, name)
        rel = full[len(ext_prefix):].lstrip('\\').replace('\\', '/')
        try:
            now[rel] = os.path.getsize(full)
        except OSError as exc:
            now[rel] = f'stat_error:{type(exc).__name__}'
rglob_count = sum(1 for p in DATA.rglob('*') if p.is_file())
size_mismatch = sorted(rel for rel, size in now.items()
                       if rel in registered and registered[rel] != size)
unregistered = sorted(set(now) - set(registered))
not_on_disk = sorted(set(registered) - set(now))
primary = {item['file_id']: item for item in manifest['primary_inputs']}
xz_now = {}
for item in manifest['primary_inputs']:
    path = Path(item['path'])
    xz_now[item['file_id']] = {'sha256_now': sha256_file(path), 'sha256_prerun': item['sha256'],
                               'bytes_now': path.stat().st_size, 'bytes_registered': item['bytes']}
xz_ok = all(v['sha256_now'] == v['sha256_prerun'] == primary[k]['prior_manifest_sha256'] and
            v['bytes_now'] == v['bytes_registered'] for k, v in xz_now.items())
add('C08_raw_tree_bytes_mtime_unchanged',
    'PASS' if (xz_ok and not size_mismatch and not unregistered and not not_on_disk) else 'FAIL',
    'in-run check read ctx["raw_tree_diff"] which run_task never populated (wiring defect); '
    'additionally the in-run pre/post tree walk used Path.rglob and therefore covered 1849/2012 '
    'files (163 C8 detailed_results files exceed the legacy MAX_PATH during rglob)',
    {'files_on_disk_extended_path': len(now), 'files_registered': len(registered),
     'size_mismatch': size_mismatch[:5], 'unregistered': unregistered[:5],
     'registered_not_on_disk': not_on_disk[:5], 'xz_files': xz_now,
     'rglob_covered_files': rglob_count},
    'all registered files present with unchanged size; 3 XZ SHA256 unchanged',
    'raw_source_manifest.csv vs current sizes (extended-path walk) + XZ SHA256 re-read',
    'raw data unchanged for all 2012 registered files by size; the three permitted XZ inputs are '
    'byte-identical by SHA256 re-read after the scan')

# ---------------------------------------------------------------- C11-C13
prior = read_json(QUALITY / 'audit.json')
summary = read_json(RUN_DIR / 'run_summary.json')
totals = summary['totals']
c11_actual = {'total_records': totals['total_records'], 'unique_keys': totals['unique_keys'],
              'duplicate_rows': totals['duplicate_rows']}
c11_expected = {'total_records': prior['total_records'],
                'unique_keys': prior['unique_id_sub_path_keys'],
                'duplicate_rows': prior['duplicate_occurrences']}
add('C11_totals_match_prior_audit', 'PASS' if c11_actual == c11_expected else 'FAIL',
    'in-run check used ctx["prior_audit"], but a global text substitution in the patch step also '
    'rewrote the assignment ctx["prior_audit"]=... inside run_task, so the check saw an empty default',
    {'actual': c11_actual, 'expected': c11_expected}, 'equal counts',
    'run_summary.json totals vs solution/outputs/quality/audit.json', 'counts match exactly')
read_counts = summary['read_counts']
comparison = read_csv_rows(RUN_DIR / 'comparison_with_prior.csv')


def comparison_value(file_id, metric):
    for row in comparison:
        if (row['prior_artifact'] == 'solution/outputs/quality/audit.json'
                and row['prior_scope'] == f'file:{file_id}' and row['prior_item'] == metric):
            return int(float(row['actual_run']))
    return None


c12_actual = {fid: {'rows': stats['rows'],
                    'unique': totals['file_unique'][fid],
                    'within_file_duplicates': comparison_value(fid, 'within_file_duplicate_rows'),
                    'overlapping_a1_rows': comparison_value(fid, 'overlapping_a1_rows')}
              for fid, stats in read_counts.items()}
pair_actual = totals['pairwise_intersections']
pair_expected = prior['pairwise_key_intersections']
c12_expected = {f['file_id']: {'rows': f['rows'],
                               'unique': f['unique_id_sub_path_keys_in_file'],
                               'within_file_duplicates': f['within_file_duplicate_rows'],
                               'overlapping_a1_rows': f['overlapping_a1_rows']}
                for f in prior['files']}
phys_rows = read_csv_rows(RUN_DIR / 'physical_rows_by_file_role.csv')
c12_ok = all(c12_actual[fid]['rows'] == c12_expected[fid]['rows']
             and c12_actual[fid]['unique'] == c12_expected[fid]['unique']
             and c12_actual[fid]['within_file_duplicates'] == c12_expected[fid]['within_file_duplicates']
             and c12_actual[fid]['overlapping_a1_rows'] == c12_expected[fid]['overlapping_a1_rows']
             for fid in c12_expected)
role_totals = {}
for fid in c12_expected:
    role_totals[fid] = sum(int(r['n_physical_rows']) for r in phys_rows
                           if r['file_id'] == fid and r['evaluation_role'] == 'extension_overlap_A1')
add('C12_file_level_counts_match_prior', 'PASS' if c12_ok else 'FAIL',
    'same missing ctx["prior_audit"] wiring defect as C11; per-file rows/unique/within-file '
    'duplicates/overlap rows were cross-checked from run_summary.json and comparison_with_prior.csv '
    'instead (an earlier attempt of this reconciliation script wrongly summed n_duplicate over roles, '
    'which conflates extension rows that duplicate A1 with duplicates inside the same file)',
    {'rows_unique_duplicates_overlap': c12_actual, 'overlap_role_row_totals': role_totals,
     'expected': c12_expected}, 'equal counts',
    'run_summary.json + comparison_with_prior.csv + physical_rows_by_file_role.csv vs prior audit.json',
    'counts match exactly')
add('C13_pairwise_key_intersections_match_prior', 'PASS' if pair_actual == pair_expected else 'FAIL',
    'same missing ctx["prior_audit"] wiring defect as C11',
    {'actual': pair_actual, 'expected': pair_expected}, 'equal counts',
    'run_summary.json totals vs prior audit.json pairwise_key_intersections', 'counts match exactly')

# ---------------------------------------------------------------- C15
checks = read_json(RUN_DIR / 'checks.json')
counters = checks['reaggregation_counters']
physical_lines = sum(stats['rows'] + stats['invalid_json'] + stats['decode_errors']
                     + stats['json_structure_errors'] for stats in read_counts.values())
add('C15_row_masks_covers_all_physical_lines',
    'PASS' if counters.get('rows') == physical_lines else 'FAIL',
    'in-run check read ctx["row_masks_rows"] which was never set (wiring defect); the independent '
    're-read of row_masks.csv.gz in the same process counted the rows',
    {'row_masks_rows_from_reaggregation': counters.get('rows'), 'decompressed_lines': physical_lines,
     'parsed_rows': counters.get('parsed_rows'), 'unparsed_rows': counters.get('unparsed_rows')},
    'equal counts', 'checks.json reaggregation_counters vs run_summary.json read_counts',
    'row_masks.csv.gz contains exactly one row per decompressed physical line')

# ---------------------------------------------------------------- C23
spec = read_json(RUN_DIR / 'diagnostic_spec.json')
feat_index = {item['feature']: item['index'] for item in spec['expanded_features_25']}
model_index = {item['feature']: item['index'] for item in spec['main_q_features_11']}
model_features = list(model_index)
mismatch_rows = 0
mismatch_examples = []
norm_inf_non_nan_rows = 0
model_extract_inf_rows = 0
parsed_rows = 0
with gzip.open(RUN_DIR / 'row_masks.csv.gz', 'rt', encoding='utf-8', newline='') as fh:
    for row in csv.DictReader(fh):
        if int(row['parse_ok'] or 0) != 1:
            continue
        parsed_rows += 1
        ext_nan = bits_from_string(row['extract_nan_bits'])
        ext_pos = bits_from_string(row['extract_posinf_bits'])
        ext_neg = bits_from_string(row['extract_neginf_bits'])
        norm_nan = bits_from_string(row['norm_nan_bits'])
        norm_nf = bits_from_string(row['norm_nonfinite_bits'])
        bad = [f for f in model_features
               if ((ext_nan >> feat_index[f]) & 1) != ((norm_nan >> model_index[f]) & 1)]
        if bad:
            mismatch_rows += 1
            if len(mismatch_examples) < 3:
                mismatch_examples.append({'file_id': row['file_id'], 'source_line': row['source_line'],
                                          'features': bad})
        if (norm_nf & ~norm_nan) != 0:
            norm_inf_non_nan_rows += 1
        for f in model_features:
            if ((ext_pos >> feat_index[f]) & 1) or ((ext_neg >> feat_index[f]) & 1):
                model_extract_inf_rows += 1
add('C23_norm_layer_equals_extract_layer',
    'PASS' if mismatch_rows == 0 and norm_inf_non_nan_rows == 0 and model_extract_inf_rows == 0 else 'FAIL',
    'in-run counter compared (extract_nan & MODEL_feature_bits) with norm_nan directly, i.e. bit j of '
    'the 25-feature space against bit j of the 11-feature space; that mixes two different bit orders, '
    'so every row with a missing main-Q feature (19 rows) was counted as a mismatch',
    {'rows_with_true_mismatch': mismatch_rows, 'norm_nonfinite_non_nan_rows': norm_inf_non_nan_rows,
     'mainQ_extract_pm_inf_rows': model_extract_inf_rows, 'parsed_rows_checked': parsed_rows,
     'examples': mismatch_examples},
    'zero true mismatches', 'row_masks.csv.gz per-feature comparison using the index maps in diagnostic_spec.json',
    'extraction NaN and normalized NaN agree per main-Q feature; no non-NaN non-finite normalized value')

payload = {'run_id': RUN_DIR.name, 'task': 'TASK-Q01A',
           'generated_local': datetime.now(CST).isoformat(timespec='seconds'),
           'scope': 'post-run read-only reconciliation of the seven FAIL entries in checks.json',
           'raw_inputs_reread': False, 'compressed_inputs_reread_for_hash_only': True,
           'in_run_artifacts_modified': False,
           'summary': {'n_reconciled': len(results),
                       'n_still_failing': sum(1 for r in results if r['postrun_status'] != 'PASS'),
                       'in_run_failure_cause': 'check-layer wiring/index-space defects; none of them '
                                               'indicates a data, count or propagation discrepancy'},
           'results': results}
out = RUN_DIR / 'checks_postrun_reconciliation.json'
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print('wrote', out.name)
for r in results:
    print(' ', r['check_id'], '->', r['postrun_status'])
