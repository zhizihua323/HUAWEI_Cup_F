from pathlib import Path
p = Path(__file__).resolve().parent / 'diagnose_missingness.py'
t = p.read_text(encoding='utf-8-sig')
old = """    with gzip.open(RUN_DIR / 'row_masks.csv.gz', 'rt', encoding='utf-8', newline='') as fh:
        row_header = next(csv.reader(fh), [])
    if forbidden_columns & set(row_header):
        header_violations.append('row_masks.csv.gz')"""
new = """    row_masks_path = RUN_DIR / 'row_masks.csv.gz'
    if row_masks_path.exists():
        with gzip.open(row_masks_path, 'rt', encoding='utf-8', newline='') as fh:
            row_header = next(csv.reader(fh), [])
        if forbidden_columns & set(row_header):
            header_violations.append('row_masks.csv.gz')
    else:
        header_violations.append('row_masks.csv.gz missing')"""
assert t.count(old) == 1, t.count(old)
p.write_text(t.replace(old, new), encoding='utf-8-sig')
print('C33 guard patched')
