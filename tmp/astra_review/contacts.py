from PIL import Image,ImageOps,ImageDraw
from pathlib import Path
import json
base=Path('tmp/astra_review')
fs=sorted(base.glob('current-*.png'))
print('rendered',len(fs))
for ns in [[1,2,3],[16,17,18],[23,24,25]]:
    sheet=Image.new('RGB',(1420,1035*((len(ns)+1)//2)),'white')
    for k,n in enumerate(ns):
        im=ImageOps.contain(Image.open(fs[n-1]),(700,1000))
        sheet.paste(im,(k%2*710,k//2*1035+25))
        ImageDraw.Draw(sheet).text((k%2*710,k//2*1035+5),'PDF '+str(n),fill='black')
    sheet.save(base/f'current-contact-{ns[0]}.jpg')
p=json.loads((base/'reference2020_pages.json').read_text(encoding='utf-8'))
for i,t in enumerate(p[:42]):
    print(i+1,' / '.join(l for l in t.splitlines() if l.strip().startswith('图 '))[:160])
