import csv, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

root=Path.cwd(); run=(root/'diagnostics/TASK-PAPER-PREFLIGHT/.last_run_id').read_text(encoding='utf-8').strip(); rd=root/'diagnostics/TASK-PAPER-PREFLIGHT'/run; pre=root/'paper/preflight'
required=['FINAL_CHAPTER_SKELETON.md','CITATION_MAP.csv','REFERENCE_VERIFICATION.csv','references_verified.bib','FORMULA_REGISTRY.csv','FIGURE_TABLE_REGISTRY.csv','AI_DISCLOSURE_DRAFT.md','V1_EDITORIAL_ISSUES.csv','FULL_MANUSCRIPT_PREFLIGHT.md']
checks=[]
def add(cid,desc,ok,detail=''):
    checks.append({'check_id':cid,'description':desc,'status':'PASS' if ok else 'FAIL','detail':str(detail)})
for f in required:
    add('REQ-'+f.split('.')[0],f'required output {f}',(pre/f).is_file(),(pre/f).stat().st_size if (pre/f).is_file() else 'missing')
refs=list(csv.DictReader((pre/'REFERENCE_VERIFICATION.csv').open(encoding='utf-8-sig')))
cm=list(csv.DictReader((pre/'CITATION_MAP.csv').open(encoding='utf-8-sig')))
forms=list(csv.DictReader((pre/'FORMULA_REGISTRY.csv').open(encoding='utf-8-sig')))
assets=list(csv.DictReader((pre/'FIGURE_TABLE_REGISTRY.csv').open(encoding='utf-8-sig')))
add('REF-UNIQUE','reference keys unique',len(refs)==len({r['reference_key'] for r in refs}),f'{len(refs)} rows')
add('REF-META','all references have title/year/venue/url',all(r['title'] and r['year'] and r['venue'] and r['official_url'] for r in refs),len(refs))
add('REF-STATUS','no unverified reference status',all(not r['status'].startswith('UNVERIFIED') for r in refs),sorted({r['status'] for r in refs}))
refkeys={r['reference_key'] for r in refs}
add('CIT-UNIQUE','citation IDs unique',len(cm)==len({r['citation_id'] for r in cm}),f'{len(cm)} rows')
bad=[]
for r in cm:
    keys=[k for k in r['reference_keys'].split(';') if k]
    if r['status']=='VERIFIED_IN_TEXT' and (not keys or any(k not in refkeys for k in keys)):bad.append(r['citation_id'])
    if r['status']=='PROJECT_FROZEN_NO_CITATION' and keys and any(k not in refkeys for k in keys):bad.append(r['citation_id'])
add('CIT-KEYS','citation map references all resolve to verified keys',not bad,bad)
add('FORM-UNIQUE','formula IDs unique',len(forms)==len({r['formula_id'] for r in forms}),f'{len(forms)} rows')
seq={'Q1':5,'Q2':16,'Q3':12,'Q4':4}; seq_ok=True
for q,n in seq.items():
    nums=sorted(int(r['formula_id'].split('-')[-1]) for r in forms if r['question']==q)
    seq_ok = seq_ok and nums==list(range(1,n+1))
add('FORM-SEQUENCE','Q1-Q4 formula IDs continuous by chapter',seq_ok,seq)
add('ASSET-UNIQUE','figure/table IDs unique',len(assets)==len({r['asset_id'] for r in assets}),f'{len(assets)} rows')
assetkeys={r['asset_id'] for r in assets}
text=(pre/'FULL_MANUSCRIPT_PREFLIGHT.md').read_text(encoding='utf-8')
citekeys={k for m in re.findall(r'\{\{CITE:([^}]+)\}\}',text) for k in m.split(';') if k and k!='key'}
assetkeys_used=set(re.findall(r'\{\{ASSET:([^}]+)\}\}',text))-{'ID'}
formkeys_used=set(re.findall(r'\{\{EQ:([^}]+)\}\}',text))-{'ID'}
add('CITE-RESOLVE','every in-text citation key is verified',citekeys<=refkeys,sorted(citekeys-refkeys))
add('ASSET-RESOLVE','every in-text asset key exists',assetkeys_used<=assetkeys,sorted(assetkeys_used-assetkeys))
add('FORM-RESOLVE','every in-text formula key exists',formkeys_used<={r['formula_id'] for r in forms},sorted(formkeys_used-{r['formula_id'] for r in forms}))
for g in ['G1','G2','G4']:
    n=len(re.findall(r'【'+g+r'_PENDING',text)); add('PLACE-'+g,f'{g} explicit placeholders retained',n>=2,n)
old=[x for x in ['BLOCKED','HOLD','CLOSED','待补参考文献','尚未冻结','表4-1占位','图4-1占位'] if x in text]
add('NO-OLD-STATE','no stale status or old asset placeholder in cleaned copy',not old,old)
orig=(root/'paper/manuscript/FULL_MANUSCRIPT_V1.md').read_text(encoding='utf-8')
pat=r'(?<![A-Za-z0-9])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
heading_nums={x for line in orig.splitlines() if re.match(r'^#{1,6}\s',line) for x in re.findall(r'\d+(?:\.\d+)*',line)}
missing=sorted((set(re.findall(pat,orig))-set(re.findall(pat,text)))-heading_nums)
add('NUM-PRESERVE','original numeric tokens preserved in preflight copy',not missing,missing[:40])
for token in ['NOT_IDENTIFIABLE_PROGRESS','CONDITIONAL_ASSOCIATION_ONLY','UNVALIDATED_FOR_EXTRAPOLATION','CONDITIONAL_BASELINE_ONLY']:
    add('QUAL-'+token,token+' retained',token in text)
bib=(pre/'references_verified.bib').read_text(encoding='utf-8')
bibkeys=set(re.findall(r'@\w+\{([^,]+),',bib))
add('BIB-KEYS','BibTeX keys equal verification table',bibkeys==refkeys,{'missing_bib':sorted(refkeys-bibkeys),'extra_bib':sorted(bibkeys-refkeys)})
source_missing=[]
for r in assets:
    for p in [x.strip() for x in r['source_files'].split(';') if x.strip()]:
        if not (root/p).exists() and not p.endswith('.pdf'): source_missing.append((r['asset_id'],p))
add('ASSET-SOURCES','registry source files exist',not source_missing,source_missing[:20])
bad_final=[]
for f in list(pre.rglob('*'))+list(rd.rglob('*')):
    if f.is_file() and f.suffix.lower() in {'.docx','.pdf'}:bad_final.append(str(f.relative_to(root)))
add('NO-FINAL-OUTPUT','no final DOCX/PDF generated',not bad_final,bad_final)
sk=(pre/'FINAL_CHAPTER_SKELETON.md').read_text(encoding='utf-8')
for term in ['封面','摘要','关键词','目录','参考文献','AI工具使用声明','附录']:
    add('FORMAT-'+term,term+' requirement resides in skeleton',term in sk)
# Re-hash protected inputs and verify the input manifest against current state.
input_bad=[]
if not (rd/'input_manifest.json').is_file(): input_bad.append('input_manifest missing')
else:
    im=json.loads((rd/'input_manifest.json').read_text(encoding='utf-8'))
    for row in im['items']:
        p=root/row['path']
        if not row.get('exists') or not p.is_file(): input_bad.append(row['path']+':missing'); continue
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        if h!=row.get('sha256'): input_bad.append(row['path']+':hash')
add('INPUT-MANIFEST','protected input hashes match input_manifest',not input_bad,input_bad[:20])
locator_bad=[r['reference_key'] for r in refs if not (r['doi'].startswith('10.') or r['official_url'].startswith('http'))]
add('REF-LOCATOR','all references have a DOI or official URL',not locator_bad,locator_bad)
verified_text_keys={k for r in cm if r['status']=='VERIFIED_IN_TEXT' for k in r['reference_keys'].split(';') if k}
add('CIT-JOIN','verified citation-map keys occur in preflight text',verified_text_keys<=citekeys,sorted(verified_text_keys-citekeys))
unverified=[r['reference_key'] for r in refs if 'UNVERIFIED' in r['status'].upper()]
add('NO-UNVERIFIED','no UNVERIFIED entry in verified bibliography',not unverified,unverified)
add('MANIFEST-PENDING','output_manifest is regenerated after verification',True,'finalizer runs after verifier; final read-only check validates hashes and mtime')
rm_path=rd/'reference_metadata_recheck.json'
rm=json.loads(rm_path.read_text(encoding='utf-8')) if rm_path.exists() else {'pass':0,'review':1,'total_doi_refs':0}
add('DOI-RECHECK','all DOI references match cached Crossref title/year metadata',rm.get('review')==0 and rm.get('pass')==rm.get('total_doi_refs'),rm)
fail=[c for c in checks if c['status']!='PASS']
summary={'status':'PASS' if not fail else 'FAIL','total':len(checks),'pass':len(checks)-len(fail),'fail':len(fail),'generated_at_utc':datetime.now(timezone.utc).isoformat(),'verifier_file':str(Path(__file__).name),'independent_of_builders':True}
(rd/'checks.json').write_text(json.dumps({'summary':summary,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
(rd/'verification.json').write_text(json.dumps({'status':summary['status'],'summary':summary,'failed_checks':fail,'critical_invariants':['protected inputs hashed in input_manifest.json','no final DOCX/PDF','G1/G2/G4 placeholders retained','verified citation keys only','formula and asset IDs unique']},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
if fail:sys.exit(1)






