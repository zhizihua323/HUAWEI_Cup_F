from pathlib import Path
import lzma,json,collections,sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path.cwd()
result=[]
for p in sorted((root/'F题').rglob('*.xz')):
    count=0;bad=[];keys=collections.Counter();domains=collections.Counter();types={}
    try:
        with lzma.open(p,'rt',encoding='utf-8') as f:
            for i,line in enumerate(f,1):
                try: obj=json.loads(line)
                except Exception as e: bad.append({'line':i,'error':str(e)});continue
                count+=1;keys.update(obj.keys());domains[str(obj.get('_source_domain','(from path)'))]+=1
                if count==1: types={k:type(v).__name__ for k,v in obj.items()}
        r={'file':str(p.relative_to(root)),'rows':count,'invalid_lines':bad,'fields':keys,'domains':domains,'first_row_types':types}
    except Exception as e:r={'file':str(p.relative_to(root)),'rows_before_error':count,'error':str(e)}
    result.append(r);print(json.dumps(r,ensure_ascii=False),flush=True)
(root/'tmp/environment_review/xz_scan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
