# -*- coding: utf-8 -*-
"""Exactness audit of evidence/baseline_result_registry.csv:
every numeric token in `value` must appear verbatim in a cited/underlying artifact file."""
import csv, re, pathlib

rows = list(csv.DictReader(open('evidence/baseline_result_registry.csv', encoding='utf-8-sig')))
roots = [pathlib.Path('solution/outputs/mixture'), pathlib.Path('solution/outputs/scaling'),
         pathlib.Path('F题/real_attachments/A_data_value/regmix_tables'),
         pathlib.Path('F题/real_attachments/B_scaling_laws'), pathlib.Path('recovery/2026-09-24'), pathlib.Path('evidence')]
corpus = {}
for root in roots:
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in ('.csv', '.json'):
            try:
                corpus[p] = p.read_text(encoding='utf-8-sig', errors='ignore')
            except Exception:
                pass
print('text sources loaded:', len(corpus))

num = re.compile(r'-?\d+\.\d+(?:[eE][-+]?\d+)?|-?\d+')
problems = []
for r in rows:
    src = pathlib.Path(r['artifact'])
    if not src.exists() or src.is_dir():
        cited = [t for p, t in corpus.items()]
    else:
        cited = []
    toks = [t for t in num.findall(r['value'])]
    toks = [t for t in toks if len(t) >= 2 and t not in ('0.5',)]  # keep 0.5 too, actually
    toks = num.findall(r['value'])
    # a value must be findable in the *cited* artifact, else anywhere in the corpus
    own = corpus.get(pathlib.Path(r['artifact']), '')
    for t in toks:
        if t in own:
            continue
        where = [str(p) for p, txt in corpus.items() if t in txt]
        if not where:
            problems.append((r['result_id'], r['value'], t, 'NOT FOUND ANYWHERE'))
print()
print('== tokens not found in the cited artifact (found elsewhere / nowhere) ==')
for r in rows:
    own = corpus.get(pathlib.Path(r['artifact']), '')
    miss = [t for t in num.findall(r['value']) if own and t not in own]
    if miss and own:
        print(' ', r['result_id'], '| value=', r['value'], '| tokens not in cited file:', miss)
print()
print('tokens found nowhere:', [p for p in problems])
