import os
from pathlib import Path
data = Path(r'C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\F题\real_attachments')
rglob_files = [p for p in data.rglob('*') if p.is_file()]
print('rglob_files', len(rglob_files))
ext = '\\\\?\\' + str(data.resolve())
count = 0
names = []
for root, dirs, files in os.walk(ext):
    for f in files:
        count += 1
        names.append(os.path.join(root, f))
print('ext_walk_files', count)
plain = 0
for root, dirs, files in os.walk(str(data)):
    plain += len(files)
print('plain_walk_files', plain)
rg = {str(p) for p in rglob_files}
missing = []
for n in names:
    rel = n[len(ext):].lstrip('\\')
    if str(data / rel) not in rg:
        missing.append(rel)
print('missing_from_rglob', len(missing))
for m in missing[:5]:
    print('  example', m[:120])
