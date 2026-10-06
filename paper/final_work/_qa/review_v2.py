from pathlib import Path
import json,re,sys
import pdfplumber
from PIL import Image,ImageOps,ImageDraw,ImageFont
qa=Path(__file__).resolve().parent
folder=qa/(sys.argv[1] if len(sys.argv)>1 else 'v2_render_1')
pdf=folder/'FINAL_MANUSCRIPT_V2.pdf'
src=(qa.parent/'FINAL_MANUSCRIPT_V2_INTEGRATED.md').read_text(encoding='utf-8')
heads=[l.lstrip('# ') for l in src.splitlines()[1:] if l.startswith('# ') or l.startswith('## ')]+['参考文献']
pg={};summ=[];alltext=[]
with pdfplumber.open(pdf) as d:
    for n,p in enumerate(d.pages,1):
        txt=p.extract_text() or '';alltext.append(txt)
        lines=txt.splitlines();norm=lambda x:re.sub(r'\s+','',x)
        # Heading only, not a TOC entry with a page number.
        for h in heads:
            if any(norm(line)==norm(h) for line in lines):pg[h]=n
        summ.append({'page':n,'chars':len(txt),'first':lines[:3],'last':lines[-3:], 'images':len(p.images)})
(qa/'v2_heading_pages.json').write_text(json.dumps(pg,ensure_ascii=False,indent=2),encoding='utf-8')
(folder/'page_text.json').write_text(json.dumps(alltext,ensure_ascii=False,indent=2),encoding='utf-8')
(folder/'page_summary.json').write_text(json.dumps(summ,ensure_ascii=False,indent=2),encoding='utf-8')
font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',24)
paths=sorted(folder.glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1]))
for start in range(0,len(paths),6):
    sheet=Image.new('RGB',(1200,1740),'#dedede')
    for k,p in enumerate(paths[start:start+6]):
        im=Image.open(p).convert('RGB');im.thumbnail((580,820))
        x=(k%2)*600+(600-im.width)//2;y=(k//2)*580 # use 3 rows of 580; crop thumbnail properly below
        im=Image.open(p).convert('RGB');im.thumbnail((560,535))
        x=(k%2)*600+(600-im.width)//2;y=(k//2)*580+30
        sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text(((k%2)*600+15,(k//2)*580+4),p.stem,fill='black',font=font)
    sheet.save(folder/f'contact-{start//6+1}.jpg',quality=90)
print(json.dumps({'pages':len(summ),'headings_found':len(pg),'heads_expected':len(heads),'page_info':summ},ensure_ascii=False))
