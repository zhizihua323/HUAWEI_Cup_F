# -*- coding: utf-8 -*-
"""Read-only cross-check: do Q1/Q2 numbers registered in paper/result_registry.md
match the cited solution artifact, and my evidence registry?"""
import re, pathlib, csv

paper = pathlib.Path('paper/result_registry.md').read_text(encoding='utf-8')
rows = []
for line in paper.splitlines():
    if not line.startswith('| `RES-'): continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    rows.append(cells)
print('paper registry rows parsed:', len(rows), '| sample widths:', sorted({len(r) for r in rows}))

mine = list(csv.DictReader(open('evidence/baseline_result_registry.csv', encoding='utf-8-sig')))
mine_vals = {r['result_id']: r['value'] for r in mine}

targets = [r for r in rows if r[0].strip('`').startswith(('RES-Q1-MIX', 'RES-Q2-SCL', 'RES-Q2-CONF'))]
print('Q1/Q2 rows to check:', len(targets))
print()
miss_in_artifact, miss_in_mine, checked = [], [], 0
for c in targets:
    rid = c[0].strip('`')
    desc, val, unit, src = c[2], c[3], c[4], c[5]
    if not re.search(r'\d', val):
        continue
    checked += 1
    p = pathlib.Path(src)
    hit_artifact = False
    if p.exists():
        txt = ''
        if p.suffix.lower() == '.csv':
            txt = p.read_text(encoding='utf-8-sig', errors='ignore')
        elif p.suffix.lower() == '.json':
            txt = p.read_text(encoding='utf-8', errors='ignore')
        hit_artifact = val in txt
        # allow the first number of a range/compound cell
        if not hit_artifact:
            first = re.split(r'[–−~～]|,\s', val)[0].strip()
            hit_artifact = first in txt
    else:
        hit_artifact = None
    hit_mine = any(val in v or v in val for v in mine_vals.values()) or val in json_dump if False else any(val in v for v in mine_vals.values())
    if hit_artifact is False: miss_in_artifact.append((rid, desc[:40], val, src))
    if not hit_mine: miss_in_mine.append((rid, desc[:40], val))
print('numeric Q1/Q2 rows checked:', checked)
print()
print('== value string NOT found in cited artifact (need manual look) ==')
for r in miss_in_artifact: print('  ', r)
print()
print('== value string not present in my evidence registry ==')
for r in miss_in_mine: print('  ', r)
