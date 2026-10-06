import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
root=Path.cwd(); rid=(root/'diagnostics/TASK-PAPER-PREFLIGHT/.last_run_id').read_text(encoding='utf-8').strip(); rd=root/'diagnostics/TASK-PAPER-PREFLIGHT'/rid
files=[]
for base,cat in [(root/'paper/preflight','deliverable'),(rd,'run_evidence')]:
    if base.exists():
        for p in sorted(base.rglob('*')):
            if p.is_file() and p.name!='output_manifest.json': files.append((p,cat))
entries=[]
for p,cat in files:
    b=p.read_bytes(); entries.append({'path':str(p.relative_to(root)).replace('\\','/'),'category':cat,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
manifest={'run_id':rid,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'status':'FINAL_MANIFEST','generated_last':True,'self_excluded':True,'self_path':'diagnostics/TASK-PAPER-PREFLIGHT/'+rid+'/output_manifest.json','n_entries':len(entries),'entries':entries,'final_docx_pdf_created':False,'reference_paper_content_copied':False}
(rd/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(len(entries))
