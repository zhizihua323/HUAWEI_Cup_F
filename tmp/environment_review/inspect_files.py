from pathlib import Path
import json, csv, lzma, zipfile, hashlib, collections, importlib.util, logging, sys
logging.disable(logging.CRITICAL)
sys.stdout.reconfigure(encoding='utf-8')
from lxml import etree
from pypdf import PdfReader

root=Path('\\\\?\\'+str(Path.cwd()))
out=root/'tmp'/'environment_review'
out.mkdir(parents=True,exist_ok=True)
files=sorted(p for p in root.rglob('*') if p.is_file() and 'tmp' not in p.relative_to(root).parts)
inventory=[]
for p in files:
    rel=p.relative_to(root).as_posix()
    r={'file':rel,'bytes':p.stat().st_size}
    try:
        if p.suffix=='.pdf':
            d=PdfReader(p); texts=[page.extract_text() or '' for page in d.pages]
            r.update(pages=len(texts),text_chars=sum(map(len,texts)))
            (out/(p.stem+'.txt')).write_text('\n\n'.join(f'PAGE {i+1}\n{t}' for i,t in enumerate(texts)),encoding='utf-8',errors='replace')
        elif p.suffix in ('.docx','.doc'):
            if zipfile.is_zipfile(p):
                with zipfile.ZipFile(p) as z:
                    if 'word/document.xml' not in z.namelist():
                        r['archive_entries']=z.namelist()
                        inventory.append(r)
                        continue
                    xml=etree.fromstring(z.read('word/document.xml'))
                    paras=[''.join(e.itertext()) for e in xml.xpath('//*[local-name()="p"]')]
                    # Preserve text and equation tokens in document order, without formatting metadata.
                    paras=[''.join(e.xpath('.//*[local-name()="t"]/text()')) for e in xml.xpath('//*[local-name()="p"]')]
                    r.update(paragraphs=len(paras),equations=len(xml.xpath('//*[local-name()="oMath"]')),images=len([n for n in z.namelist() if n.startswith('word/media/')]))
                    (out/(p.stem+'.txt')).write_text('\n'.join(paras),encoding='utf-8')
            else:
                r['magic']=p.read_bytes()[:16].hex()
                r['status']='legacy_doc_needs_extraction'
        elif p.suffix=='.csv':
            with p.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.reader(f); hdr=next(reader); rows=list(reader)
            r.update(rows=len(rows),columns=hdr,ragged_rows=sum(len(x)!=len(hdr) for x in rows),sample=rows[:1])
        elif p.suffix=='.json':
            obj=json.loads(p.read_text(encoding='utf-8-sig'))
            r['keys']=list(obj) if isinstance(obj,dict) else f'list[{len(obj)}]'
            if isinstance(obj,dict) and isinstance(obj.get('results'),dict): r['tasks']=list(obj['results'])
        elif p.suffix=='.xz':
            r['status']='pending_stream_scan'
        elif p.suffix in ('.md','.txt'):
            txt=p.read_text(encoding='utf-8-sig'); r['text']=txt
        elif p.suffix=='.parquet':
            r['status']='needs_parquet_reader'
        else:
            r['magic']=p.read_bytes()[:20].hex()
    except Exception as e: r['error']=str(e)
    inventory.append(r)
(out/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'total_files':len(files),'bytes':sum(x['bytes'] for x in inventory),'extensions':dict(collections.Counter(p.suffix for p in files)),'errors':[x for x in inventory if 'error'in x],'documents':[x for x in inventory if Path(x['file']).suffix in ('.pdf','.docx','.doc')],'other':[x for x in inventory if Path(x['file']).suffix not in ('.pdf','.docx','.doc','.json','.csv','.md','.txt','.xz','.parquet')]},ensure_ascii=False,indent=2))
