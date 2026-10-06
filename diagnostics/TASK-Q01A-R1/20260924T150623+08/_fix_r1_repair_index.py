from pathlib import Path
p = Path(__file__).resolve().parent / 'repair_from_artifacts.py'
t = p.read_text(encoding='utf-8-sig')
old_head = """    raw_events = events['raw_events']
    fields = {name: i for i, name in enumerate(FIELD_ORDER)}"""
new_head = """    raw_events = events['raw_events']
    event_index = {}
    for (file_id, line, field), entry in raw_events.items():
        event_index.setdefault((file_id, line), {})[field] = entry
    fields = {name: i for i, name in enumerate(FIELD_ORDER)}"""
assert t.count(old_head) == 1
t = t.replace(old_head, new_head, 1)

old_lookup = """            if parse_ok:
                event_fields = [key[2] for key in raw_events if key[0] == file_id and key[1] == line]
                event_bits = set_bits(event_fields, fields) if event_fields else 0
            else:
                event_bits = 0"""
new_lookup = """            row_events = event_index.get((file_id, line), {})
            event_fields = sorted(row_events)
            if parse_ok and event_fields:
                event_bits = set_bits(event_fields, fields)
            else:
                event_bits = 0"""
assert t.count(old_lookup) == 1
t = t.replace(old_lookup, new_lookup, 1)

old_reasons = """                reasons = sorted({r for key, entry in raw_events.items()
                                  if key[0] == file_id and key[1] == line
                                  for r in entry['reasons']})"""
new_reasons = """                reasons = sorted({r for entry in row_events.values() for r in entry['reasons']})"""
assert t.count(old_reasons) == 1
t = t.replace(old_reasons, new_reasons, 1)

old_evidence = """                    'evidence_event_rows': sum(raw_events[(file_id, line, f)]['n_events']
                                               for f in event_fields),
                    'nan_elements_by_field': '|'.join(
                        f"{f}:{raw_events[(file_id, line, f)]['nan_elements']}"
                        for f in sorted(event_fields)
                        if raw_events[(file_id, line, f)]['nan_elements']),"""
new_evidence = """                    'evidence_event_rows': sum(row_events[f]['n_events'] for f in event_fields),
                    'nan_elements_by_field': '|'.join(
                        f"{f}:{row_events[f]['nan_elements']}"
                        for f in event_fields if row_events[f]['nan_elements']),"""
assert t.count(old_evidence) == 1
t = t.replace(old_evidence, new_evidence, 1)
p.write_text(t, encoding='utf-8-sig')
print('event index patch applied')
