import csv,json,re,unicodedata
from pathlib import Path
root=Path.cwd(); rd=root/'diagnostics/TASK-PAPER-PREFLIGHT'/(root/'diagnostics/TASK-PAPER-PREFLIGHT/.last_run_id').read_text(encoding='utf-8').strip(); raw=rd/'raw_metadata'
by_doi={}
for name in ['crossref_exact.json','crossref_meeusen.json']:
 p=raw/name
 if not p.exists():continue
 obj=json.loads(p.read_text(encoding='utf-8'))
 arr=obj if isinstance(obj,list) else [obj]
 for x in arr:
  if isinstance(x,dict) and x.get('DOI'):by_doi[x['DOI'].lower()]=x
sr=json.loads((raw/'crossref_search.json').read_text(encoding='utf-8'))
for q in sr:
 for x in q.get('items',[]) or []:
  if x.get('DOI'):by_doi[x['DOI'].lower()]=x
def norm(s):return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower()).strip()
rows=[]
for r in csv.DictReader((root/'paper/preflight/REFERENCE_VERIFICATION.csv').open(encoding='utf-8-sig')):
 if not r['doi']:continue
 m=by_doi.get(r['doi'].lower()); ti=' '.join(m.get('title') or []) if m else ''; yr=(m.get('issued',{}).get('date-parts') or [[None]])[0][0] if m else None
 rows.append({'reference_key':r['reference_key'],'doi':r['doi'],'crossref_found':bool(m),'title_match':norm(ti)==norm(r['title']),'expected_title':r['title'],'crossref_title':ti,'expected_year':int(r['year']),'crossref_year':yr,'year_match':str(yr)==r['year'],'status':'PASS' if m and norm(ti)==norm(r['title']) and str(yr)==r['year'] else 'REVIEW'})
summary={'total_doi_refs':len(rows),'pass':sum(x['status']=='PASS' for x in rows),'review':sum(x['status']!='PASS' for x in rows),'rows':rows}
(rd/'reference_metadata_recheck.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
