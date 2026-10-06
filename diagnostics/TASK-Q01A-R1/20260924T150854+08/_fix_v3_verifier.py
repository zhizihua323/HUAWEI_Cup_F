from pathlib import Path
p = Path(__file__).resolve().parent / 'verify_repairs.py'
t = p.read_text(encoding='utf-8-sig')

old_v14 = """    counters = read_json(R_DIR / 'checks.json')['reaggregation_counters']
    total_ok = (sum(v['n_rows'] for v in per_file.values()) == 272505
                and counters.get('rows') == 272505 and counters.get('n_row_keys') == 272505)"""
new_v14 = """    counters = read_json(R_DIR / 'checks.json')['reaggregation_counters']
    identity = read_json(R_DIR / 'checks.json')['invalid_values_reconciliation']
    n_row_keys = identity.get('n_row_keys')
    total_ok = (sum(v['n_rows'] for v in per_file.values()) == 272505
                and counters.get('rows') == 272505 and n_row_keys == 272505)"""
assert t.count(old_v14) == 1
t = t.replace(old_v14, new_v14, 1)
t = t.replace("""              {'per_file': per_file, 'reaggregation_rows': counters.get('rows'),
               'n_row_keys': counters.get('n_row_keys')},""",
"""              {'per_file': per_file, 'reaggregation_rows': counters.get('rows'),
               'n_row_keys': n_row_keys,
               'distinct_identity_count_from_per_file': sum(v['n_unique_lines'] for v in per_file.values())},""", 1)

old_v17 = """        for number, line in enumerate(text.splitlines(), 1):
            if 'jsonl.xz' in line and ('open(' in line or 'sha256_file(' in line or 'read(' in line):
                offenders.append(f'{script}:{number}')"""
new_v17 = """        token = 'jsonl' + '.xz'
        for number, line in enumerate(text.splitlines(), 1):
            if token in line and ('open(' in line or 'sha256_file(' in line or 'read(' in line):
                if 'token in line' in line:
                    continue
                offenders.append(f'{script}:{number}:{line.strip()[:90]}')"""
assert t.count(old_v17) == 1
t = t.replace(old_v17, new_v17, 1)
p.write_text(t, encoding='utf-8-sig')
print('verifier fixes applied')
