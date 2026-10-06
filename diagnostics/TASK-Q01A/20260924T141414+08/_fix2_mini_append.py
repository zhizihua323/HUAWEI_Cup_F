from pathlib import Path
p = Path(__file__).resolve().parent / 'diagnose_missingness.py'
t = p.read_text(encoding='utf-8-sig')
old = """        store.append(row['fc'], line_no, row['dom'], row['flags'], row.get('raw_nan', 0),
                     ext_nan, ext_nf, row.get('model_nan', 0), row.get('model_nan', 0),
                     group_bits, q_nan)"""
new = """        store.append(row['fc'], line_no, row['dom'], row['flags'], row.get('raw_nan', 0),
                     ext_nan, ext_nf, 0, 0, row.get('model_nan', 0), row.get('model_nan', 0),
                     group_bits, q_nan)"""
assert t.count(old) == 1, t.count(old)
p.write_text(t.replace(old, new), encoding='utf-8-sig')
print('fixed mini append signature')
