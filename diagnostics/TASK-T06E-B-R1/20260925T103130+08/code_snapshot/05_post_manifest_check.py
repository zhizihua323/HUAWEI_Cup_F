from __future__ import annotations
import hashlib,json,pathlib,sys
r=pathlib.Path(r'diagnostics/TASK-T06E-B-R1/20260925T103130+08')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
m=json.loads((r/'output_manifest.json').read_text(encoding='utf-8')); bad=[]
for x in m['files']:
 q=r/x['path']
 if not q.exists() or q.stat().st_size!=x['bytes'] or sha(q)!=x['sha256']: bad.append(x['path'])
cur=[q for q in r.rglob('*') if q.is_file() and q.name!='output_manifest.json']
print(json.dumps({'status':'PASS' if not bad and len(cur)==m['file_count'] else 'FAIL','manifest_hash':sha(r/'output_manifest.json'),'registered_files':m['file_count'],'current_nonmanifest_files':len(cur),'mismatches':bad,'scientific_result':m['scientific_result']},ensure_ascii=False)); sys.exit(0 if not bad and len(cur)==m['file_count'] else 1)
