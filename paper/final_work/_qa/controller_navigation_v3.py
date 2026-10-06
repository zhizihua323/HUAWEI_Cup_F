"""Independently check rendered TOC destinations and embedded final figure bytes."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from pypdf import PdfReader
import hashlib, json, re

root = Path(__file__).resolve().parents[1]
docx = root / 'FINAL_MANUSCRIPT_V3.docx'
pdf = root / 'FINAL_MANUSCRIPT_V3.pdf'
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def norm(s): return re.sub(r'\s+', '', s)
with ZipFile(docx) as z:
    xml = etree.fromstring(z.read('word/document.xml'))
    toc = {}
    for h in xml.xpath('//w:hyperlink[@w:anchor]', namespaces=ns):
        s = ''.join(h.xpath('.//w:t/text()', namespaces=ns))
        m = re.match(r'^(.*?)(\d+)\s*$', s)
        if m: toc[norm(m[1])] = int(m[2])
    media_hashes = {hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
d = PdfReader(pdf)
checked = []
for page in d.pages:
    for ref in page.get('/Annots', []):
        a = ref.get_object()
        if '/Dest' not in a: continue
        label = str(a.get('/Contents', ''))
        key = norm(label)
        if key not in toc: continue
        dest = a['/Dest']
        target = d.get_page_number(dest[0].get_object()) + 1
        checked.append({'entry': label, 'printed_page': toc[key], 'target_page': target, 'match': toc[key] == target})
figs = []
for p in sorted((root.parent / 'final_figures' / 'submission_v3').glob('fig*.png')):
    figs.append({'file': p.name, 'byte_exact_embedded': hashlib.sha256(p.read_bytes()).hexdigest() in media_hashes})
result = {'docx_sha256': hashlib.sha256(docx.read_bytes()).hexdigest(), 'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(), 'toc_items': len(toc), 'toc_navigation': checked, 'all_toc_pages_correct': len(checked) == len(toc) == 41 and all(x['match'] for x in checked), 'figures': figs, 'all_final_figures_embedded': len(figs) == 5 and all(x['byte_exact_embedded'] for x in figs)}
(root / '_qa' / 'controller_v3' / 'final_navigation_and_assets.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['toc_navigation', 'figures']}, ensure_ascii=False))
