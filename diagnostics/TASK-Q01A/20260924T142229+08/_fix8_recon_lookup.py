from pathlib import Path
p = Path(__file__).resolve().parent / 'postrun_reconciliation.py'
t = p.read_text(encoding='utf-8-sig')
old = """        if (row['prior_artifact'] == 'solution/outputs/quality/audit.json'
                and row['prior_item'] == f'file:{file_id}' and row['metric'] == metric):"""
new = """        if (row['prior_artifact'] == 'solution/outputs/quality/audit.json'
                and row['prior_scope'] == f'file:{file_id}' and row['prior_item'] == metric):"""
assert t.count(old) == 1, t.count(old)
p.write_text(t.replace(old, new), encoding='utf-8-sig')
print('lookup fixed')
