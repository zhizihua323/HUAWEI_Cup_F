from pathlib import Path
p = Path(__file__).resolve().parent / 'repair_from_artifacts.py'
t = p.read_text(encoding='utf-8-sig')
new_id = p.parent.name
t = t.replace("RUN_ID = '20260924T150813+08'", f"RUN_ID = '{new_id}'", 1)
old_loop = """        for (fid, line, fname), entry in raw_events.items():
            if fid != file_id or fname != field:
                continue
            row_domain = domain_by_line.get((fid, line), '')"""
new_loop = """        for (fid, line, fname), entry in raw_events.items():
            if fid != file_id or fname != field:
                continue
            row_domain = domain_by_line.get((fid, int(line)), '')"""
assert t.count(old_loop) == 1
t = t.replace(old_loop, new_loop, 1)
assert "RUN_ID = '" in t
p.write_text(t, encoding='utf-8-sig')
print('patched for run', new_id)
