from pathlib import Path
import sys,json,struct,hashlib,collections,re
sys.stdout.reconfigure(encoding='utf-8')
root=Path.cwd(); out=root/'tmp/environment_review'
sys.path.insert(0,str(out/'deps'))
import olefile, pyarrow.parquet as pq
for p in root.rglob('*.doc'):
    if 'tmp' in p.relative_to(root).parts:continue
    try:
        ole=olefile.OleFileIO(p); w=ole.openstream('WordDocument').read()
        tab=ole.openstream('1Table' if struct.unpack_from('<H',w,10)[0]&0x200 else '0Table').read()
        fc,lcb=struct.unpack_from('<II',w,418); clx=tab[fc:fc+lcb];pos=0
        while clx[pos]==1:pos+=3+struct.unpack_from('<H',clx,pos+1)[0]
        if clx[pos]!=2:raise ValueError('No piece table')
        sz=struct.unpack_from('<I',clx,pos+1)[0]; plc=clx[pos+5:pos+5+sz]; n=(sz-4)//12
        cps=struct.unpack_from('<'+'I'*(n+1),plc); chunks=[]
        for i in range(n):
            rawfc=struct.unpack_from('<I',plc,4*(n+1)+8*i+2)[0]; compressed=bool(rawfc&0x40000000); start=rawfc&0x3fffffff; length=cps[i+1]-cps[i]
            if compressed:start//=2
            chunks.append(w[start:start+length*(1 if compressed else 2)].decode('cp1252' if compressed else 'utf-16le',errors='replace'))
        txt=''.join(chunks)[:struct.unpack_from('<I',w,76)[0]].replace('\r','\n')
        (out/(p.stem+'.txt')).write_text(txt,encoding='utf-8')
        print('DOC',p.name,txt[:6000])
    except Exception as e:print('DOC_ERROR',p.name,str(e))
p=next((root/'F题').rglob('*.parquet')); table=pq.read_table(p)
print('PARQUET',table.num_rows,table.num_columns,table.column_names)
inventory=json.loads((out/'inventory.json').read_text(encoding='utf-8'))
for x in inventory:
    if x['file'].endswith('model_architecture_metadata.csv'):
        i=x['columns'].index('max_position_embeddings')
        import csv
        with (root/x['file']).open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        print('CONTEXT_LENGTHS',sorted({int(r['max_position_embeddings']) for r in rows if r['max_position_embeddings']}))
    if x['file'].endswith('README.md'):
        print('README',x['file'],'chars',len(x['text']),'tail',x['text'][-240:])
manifest=json.loads((root/'F题/real_attachments/source_manifest.json').read_text(encoding='utf-8'))
print('MANIFEST entries',len(manifest),'source links',sum('source'in x for x in manifest),'notes',[(x['file'],x.get('note')) for x in manifest if x.get('note')][:12])
for p in out.glob('AI*.txt'):
    t=p.read_text(encoding='utf-8');print('PROMPT DOCUMENT',p.name,t[:1200],t[-400:])
for p in out.glob('HL03*.txt'):
    t=p.read_text(encoding='utf-8'); print('HL03 ABSTRACT',t[:3000]);print('HL03 OUTLINE','\n'.join(l for l in t.splitlines() if re.match(r'^\d+(?:\.\d+)?\s+[\u4e00-\u9fff]',l))[:2500])
# Render source PDFs for internal inspection without modifying them.
import pypdfium2 as pdfium
for p in [root/'F题/数据说明.pdf',*list((root/'参考资料').glob('*.pdf'))]:
    d=pdfium.PdfDocument(p)
    pg=d[8 if p.name=='数据说明.pdf' else 0]
    pg.render(scale=1.2).to_pil().save(out/(p.stem+'.png'))
