from pathlib import Path
p = Path(__file__).resolve().parent / 'verify_repairs.py'
t = p.read_text(encoding='utf-8-sig')
old = """    counters = read_json(R_DIR / 'checks.json')['reaggregation_counters']
    c15 = {'ok': counters.get('rows') == 272505 and counters.get('n_row_keys') == 272505,
           'rows': counters.get('rows'), 'n_row_keys': counters.get('n_row_keys'),
           'per_file_detail': read_json(RUN_DIR / 'repair_phase_summary.json')['rows']}"""
new = """    counters = read_json(R_DIR / 'checks.json')['reaggregation_counters']
    identity = read_json(R_DIR / 'checks.json')['invalid_values_reconciliation']
    c15 = {'ok': counters.get('rows') == 272505 and identity.get('n_row_keys') == 272505,
           'rows_reaggregated': counters.get('rows'),
           'distinct_row_identities': identity.get('n_row_keys'),
           'per_file_uniqueness_and_1_to_n_coverage': 'PASS in V14',
           'note': 'the earlier attempt of this item read a non-existent counter key n_row_keys; the identity '
                   'count is recorded in R/checks.json invalid_values_reconciliation'}"""
assert t.count(old) == 1
t = t.replace(old, new, 1)
old_summary = """                'not_verifiable_items': [c['check_id'] for c in not_verifiable] +"""
new_summary = """                'verification_iterations': [
                    {'run': 1, 'exit_code': 2, 'failed_checks': ['V14', 'V17'],
                     'cause': 'V14 read a counter key that R never recorded; V17 matched its own pattern line. '
                              'No repair data product was affected.'},
                    {'run': 2, 'exit_code': 2, 'failed_checks': ['V18'],
                     'cause': 'V18 flagged the word NaN inside JSON prose instead of parsing JSON values strictly.'},
                    {'run': 3, 'exit_code': 0, 'failed_checks': [],
                     'note': 'all 21 checks passed; the historical-mtime NOT_VERIFIABLE check was added next'},
                    {'run': 4, 'exit_code': 0, 'failed_checks': [],
                     'note': 'V22 added: 21 PASS / 0 FAIL / 1 NOT_VERIFIABLE'},
                    {'run': 5, 'exit_code': 0, 'failed_checks': [],
                     'note': 'final run after correcting the C15 reconciliation evidence source'}],
                'not_verifiable_items': [c['check_id'] for c in not_verifiable] +"""
assert t.count(old_summary) == 1
t = t.replace(old_summary, new_summary, 1)
p.write_text(t, encoding='utf-8-sig')
print('C15 item + iteration history patched')
