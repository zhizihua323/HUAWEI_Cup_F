from pathlib import Path
p = Path(__file__).resolve().parent / 'postrun_reconciliation.py'
t = p.read_text(encoding='utf-8-sig')
old_start = t.index("read_counts = summary['read_counts']")
old_end = t.index("add('C12_file_level_counts_match_prior'")
new_block = '''read_counts = summary['read_counts']
comparison = read_csv_rows(RUN_DIR / 'comparison_with_prior.csv')


def comparison_value(file_id, metric):
    for row in comparison:
        if (row['prior_artifact'] == 'solution/outputs/quality/audit.json'
                and row['prior_item'] == f'file:{file_id}' and row['metric'] == metric):
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
'''
t = t[:old_start] + new_block + t[old_end:]
t = t.replace("""add('C12_file_level_counts_match_prior', 'PASS' if c12_ok else 'FAIL',
    'same missing ctx["prior_audit"] wiring defect as C11; per-file rows/unique/duplicates were '
    'cross-checked from run_summary.json and physical_rows_by_file_role.csv instead',
    {'rows_unique_duplicates': c12_actual, 'overlap_rows_by_file': overlap_actual,
     'expected': c12_expected}, 'equal counts',
    'run_summary.json + physical_rows_by_file_role.csv vs prior audit.json', 'counts match exactly')""",
"""add('C12_file_level_counts_match_prior', 'PASS' if c12_ok else 'FAIL',
    'same missing ctx["prior_audit"] wiring defect as C11; per-file rows/unique/within-file '
    'duplicates/overlap rows were cross-checked from run_summary.json and comparison_with_prior.csv '
    'instead (an earlier attempt of this reconciliation script wrongly summed n_duplicate over roles, '
    'which conflates extension rows that duplicate A1 with duplicates inside the same file)',
    {'rows_unique_duplicates_overlap': c12_actual, 'overlap_role_row_totals': role_totals,
     'expected': c12_expected}, 'equal counts',
    'run_summary.json + comparison_with_prior.csv + physical_rows_by_file_role.csv vs prior audit.json',
    'counts match exactly')""")
p.write_text(t, encoding='utf-8-sig')
print('C12 reconciliation patched')
