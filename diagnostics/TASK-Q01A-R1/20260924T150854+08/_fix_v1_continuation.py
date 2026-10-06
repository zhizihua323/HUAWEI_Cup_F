from pathlib import Path
p = Path(__file__).resolve().parent / 'verify_repairs.py'
t = p.read_text(encoding='utf-8-sig')
bad = """        expected_lines = int(stats['rows']) + int(stats['invalid_json']) + int(stats['decode_errors']) \\\\
            + int(stats['json_structure_errors'])"""
good = """        expected_lines = (int(stats['rows']) + int(stats['invalid_json'])
                          + int(stats['decode_errors']) + int(stats['json_structure_errors']))"""
assert t.count(bad) == 1, t.count(bad)
t = t.replace(bad, good, 1)
p.write_text(t, encoding='utf-8-sig')
print('continuation fixed')
