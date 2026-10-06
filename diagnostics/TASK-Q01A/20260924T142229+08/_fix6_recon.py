from pathlib import Path
p = Path(__file__).resolve().parent / 'postrun_reconciliation.py'
t = p.read_text(encoding='utf-8-sig')
old = "physical_lines = sum(stats['line_count'] for stats in read_counts.values())"
new = ("physical_lines = sum(stats['rows'] + stats['invalid_json'] + stats['decode_errors']\n"
       "                     + stats['json_structure_errors'] for stats in read_counts.values())")
assert t.count(old) == 1, t.count(old)
p.write_text(t.replace(old, new), encoding='utf-8-sig')
print('reconciliation patch applied')
