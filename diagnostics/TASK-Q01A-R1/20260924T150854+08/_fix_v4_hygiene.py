from pathlib import Path
p = Path(__file__).resolve().parent / 'verify_repairs.py'
t = p.read_text(encoding='utf-8-sig')
old = """    json_hits = []
    for path in sorted(RUN_DIR.glob('*.json')):
        if path.name == 'output_manifest.json':
            continue
        text = path.read_text(encoding='utf-8')
        if re.search(r'\\bNaN\\b|\\bInfinity\\b', text):
            json_hits.append(path.name)"""
new = """    json_hits = []

    def reject_constant(value):
        raise ValueError(f'non-strict JSON literal: {value}')

    for path in sorted(RUN_DIR.glob('*.json')):
        if path.name == 'output_manifest.json':
            continue
        text = path.read_text(encoding='utf-8')
        try:
            json.loads(text, parse_constant=reject_constant)
        except ValueError as exc:
            json_hits.append({'file': path.name, 'error': str(exc)})"""
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new, 1)
t = t.replace("""              {'csv_with_q_columns': hits, 'json_with_nan_or_infinity': json_hits}, 'none',""",
              """              {'csv_with_q_columns': hits, 'json_with_nonstrict_literals': json_hits}, 'none',""", 1)
p.write_text(t, encoding='utf-8-sig')
print('hygiene check fixed')
