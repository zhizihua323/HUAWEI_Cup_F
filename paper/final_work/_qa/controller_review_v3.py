"""Read-only editorial QA of V3. Does not change the manuscript or scientific assets."""
from pathlib import Path
from zipfile import ZipFile
from collections import Counter
import json, re, hashlib
from lxml import etree
from pypdf import PdfReader
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_qa' / 'controller_v3'
OUT.mkdir(exist_ok=True)
docx = ROOT / 'FINAL_MANUSCRIPT_V3.docx'
pdf = ROOT / 'FINAL_MANUSCRIPT_V3.pdf'
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
def attr(e, key): return e.get('{'+NS['w']+'}'+key)
def tx(e): return ''.join(e.xpath('.//w:t/text()', namespaces=NS))
with ZipFile(docx) as z:
    root = etree.fromstring(z.read('word/document.xml'))
    styles = etree.fromstring(z.read('word/styles.xml'))
    instructions = root.xpath('//w:instrText/text()', namespaces=NS)
    instructions += root.xpath('//w:fldSimple/@w:instr', namespaces=NS)
    bookmarks = set(root.xpath('//w:bookmarkStart/@w:name', namespaces=NS))
    links = root.xpath('//w:hyperlink/@w:anchor', namespaces=NS)
    heads=[]
    style_map={attr(s,'styleId'):s for s in styles.xpath('//w:style',namespaces=NS)}
    for p in root.xpath('//w:body/w:p',namespaces=NS):
        ids=p.xpath('./w:pPr/w:pStyle/@w:val',namespaces=NS)
        if ids and ids[0] in style_map:
            s=style_map[ids[0]]
            level=s.xpath('./w:pPr/w:outlineLvl/@w:val',namespaces=NS)
            if level and int(level[0])<3: heads.append({'style':ids[0],'level':level[0],'text':tx(p)})
    report={
      'document_sha256':hashlib.sha256(docx.read_bytes()).hexdigest(),
      'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
      'toc_fields':[s for s in instructions if re.search(r'\bTOC\b',s)],
      'internal_hyperlinks':len(links),
      'missing_bookmark_targets':sorted(set(links)-bookmarks),
      'headings':heads,
      'equations':len(root.xpath('//m:oMath',namespaces=NS)),
      'tables':len(root.xpath('//w:tbl',namespaces=NS)),
      'track_changes':len(root.xpath('//w:ins|//w:del',namespaces=NS)),
      'comments_parts':[n for n in z.namelist() if re.search(r'word/comments[^/]*\.xml$',n)],
      'headers':{n:tx(etree.fromstring(z.read(n))) for n in z.namelist() if re.match(r'word/header\d+\.xml$',n)},
      'core_properties':z.read('docProps/core.xml').decode('utf-8') if 'docProps/core.xml' in z.namelist() else None,
    }
pages=[]
d=PdfReader(pdf)
report['pdf_pages']=len(d.pages)
report['pdf_outline']=str(d.outline)
link_counts=Counter()
for i,p in enumerate(d.pages):
    text=p.extract_text() or ''
    links=[]
    for ref in p.get('/Annots',[]):
        a=ref.get_object()
        if a.get('/Subtype')=='/Link':
            action=a.get('/A',{})
            kind=str(action.get('/S','/Dest' if '/Dest' in a else 'unknown'))
            links.append({'kind':kind,'target':str(a.get('/Dest',action.get('/D',action.get('/URI',''))))})
            link_counts[kind]+=1
    pages.append({'page':i+1,'text':text,'links':links,'characters':len(text)})
report['pdf_link_kind_counts']=dict(link_counts)
poppler=Path(r'C:\Users\28762\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe')
subprocess.run([str(poppler),'-png','-r','90',str(pdf),str(OUT/'page')],check=True)
(OUT/'document_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['headings','pdf_outline','core_properties']},ensure_ascii=False,indent=2))
