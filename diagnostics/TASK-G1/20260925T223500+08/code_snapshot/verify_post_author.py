#!/usr/bin/env python
"""Independent verifier for the post-author G1 continuation. Does not import executor code."""
from __future__ import annotations
import argparse, hashlib, json, math, re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

SEED = 20260925

def sha_file(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def sha_text(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()

def parse_ratings(completed, blind):
    text = completed.read_bytes().decode('gb18030')
    ids = list(re.finditer(r'(?<![A-Za-z0-9])G1-\d{3}(?![A-Za-z0-9])', text))
    tail_pat = re.compile(r'^\s*"\s*,\s*([0-9]*)\s*,\s*([0-9]*)\s*,\s*([0-9]*)\s*,\s*([0-9]*)')
    cand_pat = re.compile(r'(?<![0-9])([0-9]*)\s*,\s*([0-9]*)\s*,\s*([0-9]*)\s*,\s*([0-9]*)\s*(?:,\s*){4,}(?=\r?\n|$)')
    def conv(v): return [int(x) if x not in (None, '') else None for x in v]
    def plausible(v):
        a,b,c,d=v
        return sum(x is not None for x in v)>=2 and (a is None or 0<=a<=5) and (b is None or 0<=b<=5) and (c is None or 0<=c<=2) and (d is None or 0<=d<=5)
    def valid(v):
        a,b,c,d=v
        return sum(x is not None for x in v)>=2 and (a is None or 1<=a<=5) and (b is None or 1<=b<=5) and (c is None or 0<=c<=2) and (d is None or 1<=d<=5)
    bmap = blind.set_index('review_id').text_redacted.to_dict(); rows=[]
    for i,m in enumerate(ids):
        rid=m.group(0); seg=text[m.start():(ids[i+1].start() if i+1<len(ids) else len(text))]; source=bmap[rid]
        chars=[]; pos=[]
        for j,ch in enumerate(seg):
            if not ch.isspace(): chars.append(ch); pos.append(j)
        norm=''.join(chars); found=None
        for k in [300,250,200,150,120,100,80,60,40,20]:
            probe=''.join(source[-k:].split()); at=norm.rfind(probe)
            if at>=0: found=(k,pos[at+len(probe)-1]+1); break
        selected=None; method='missing'; raw=''; cstart=None
        if found:
            mt=tail_pat.match(seg[found[1]:found[1]+100])
            if mt:
                v=conv(mt.groups()); raw=','.join('' if x is None else str(x) for x in v)
                if valid(v): selected=v; method='tail_boundary_valid'
                elif plausible(v): selected=[None]*4; method='tail_boundary_invalid'
        if selected is None and method=='missing':
            c=[]
            for x in cand_pat.finditer(seg):
                v=conv(x.groups())
                if plausible(v): c.append((sum(z is not None for z in v),-x.start(),v,x.start()))
            if c:
                chosen=max(c); v=chosen[2]; cstart=chosen[3]; raw=','.join('' if x is None else str(x) for x in v)
                if valid(v): selected=v; method='structural_valid'
                else: selected=[None]*4; method='structural_invalid'
        if selected is None: selected=[None]*4
        status='valid_complete' if all(x is not None for x in selected) else ('valid_partial' if any(x is not None for x in selected) else method)
        rows.append({'review_id':rid,'parse_status':status,'parse_method':method,'candidate_start':cstart,'raw_candidate':raw,
                     'readability_1to5':selected[0],'completeness_1to5':selected[1],
                     'contamination_0to2':selected[2],'overall_quality_1to5':selected[3]})
    return pd.DataFrame(rows)

def item(name, passed, details): return {'check': name, 'status': 'PASS' if passed else 'FAIL', 'details': details}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-dir',required=True); args=ap.parse_args()
    rd=Path(args.run_dir).resolve(); root=rd.parents[2]; source=root/'diagnostics'/'TASK-G1'/'20260925T204300+08'
    checks=[]; inp=json.loads((rd/'input_manifest.json').read_text(encoding='utf-8'))
    frozen=rd/'input_author_manual_text_review_completed.csv'; original=source/'manual_text_review_completed.csv'
    checks.append(item('frozen_author_copy_matches_source_bytes', sha_file(frozen)==sha_file(original)==inp['author_source_sha256'],
                       {'frozen':sha_file(frozen),'source':sha_file(original),'manifest':inp['author_source_sha256']}))
    source_manifest=json.loads((source/'output_manifest.json').read_text(encoding='utf-8'))
    changed=[]
    for e in source_manifest['registered_files']:
        p=source/e['path']
        if not p.exists() or sha_file(p)!=e['sha256'] or p.stat().st_size!=e['bytes']:
            changed.append({'path':e['path'],'expected':e['sha256'],'got':sha_file(p) if p.exists() else None})
    checks.append(item('sealed_source_run_registered_files_unchanged',not changed,changed))
    blind=pd.read_csv(source/'manual_text_review_blind.csv',dtype={'review_id':str})
    ratings=parse_ratings(frozen,blind)
    joined=pd.read_csv(rd/'manual_text_review_joined.csv',dtype={'review_id':str})
    key=pd.read_csv(source/'manual_review_key.csv',dtype={'review_id':str})
    checks.append(item('author_review_ids_complete_unique',len(ratings)==60 and ratings.review_id.is_unique and set(ratings.review_id)==set(blind.review_id),
                       {'n':len(ratings),'unique':int(ratings.review_id.nunique())}))
    checks.append(item('joined_file_matches_independent_author_parse',
                       joined.review_id.tolist()==ratings.review_id.tolist() and
                       joined[['readability_1to5','completeness_1to5','contamination_0to2','overall_quality_1to5']].fillna(-999).equals(ratings[['readability_1to5','completeness_1to5','contamination_0to2','overall_quality_1to5']].fillna(-999)),
                       ratings.parse_status.value_counts().to_dict()))
    counts=ratings.parse_status.value_counts().to_dict()
    checks.append(item('manual_parse_status_counts_frozen',counts.get('valid_complete',0)==46 and counts.get('valid_partial',0)==1 and counts.get('structural_invalid',0)+counts.get('tail_boundary_invalid',0)+counts.get('missing',0)==13,counts))
    checks.append(item('no_imputation_and_invalid_values_excluded',
                       int(joined[['readability_1to5','completeness_1to5','contamination_0to2','overall_quality_1to5']].notna().sum().min()) >= 46 and
                       joined.loc[joined.rating_parse_status.str.contains('invalid|missing',na=False), ['readability_1to5','completeness_1to5','contamination_0to2','overall_quality_1to5']].notna().sum().sum()==0,
                       {'nonnull_each':joined[['readability_1to5','completeness_1to5','contamination_0to2','overall_quality_1to5']].notna().sum().to_dict()}))
    # Independently recompute the four rank correlations.
    recomputed={}
    for col in ['overall_quality_1to5','readability_1to5','completeness_1to5','contamination_0to2']:
        z=joined[['Q_baseline',col]].dropna(); rho,p=stats.spearmanr(z.Q_baseline,z[col]); recomputed[col]=(len(z),float(rho),float(p))
    st=pd.read_csv(rd/'manual_validation_statistics.csv')
    stat_ok=True; detail=[]
    for col,(n,rho,p) in recomputed.items():
        row=st[st.analysis.eq('spearman_Q_vs_'+({'overall_quality_1to5':'overall_quality','readability_1to5':'readability','completeness_1to5':'completeness','contamination_0to2':'contamination'}[col]))]
        good=len(row)==1 and int(row.iloc[0].n_a)==n and abs(float(row.iloc[0].estimate)-rho)<1e-12 and abs(float(row.iloc[0].p_value_descriptive)-p)<1e-12
        stat_ok &= good; detail.append({'metric':col,'recomputed':[n,rho,p],'stored':row.to_dict(orient='records'),'match':good})
    checks.append(item('manual_rank_statistics_match_independent_recompute',stat_ok,detail))
    cases=pd.read_csv(rd/'manual_case_registry.csv')
    case_fail=[]
    blind_map=blind.set_index('review_id').text_redacted.to_dict()
    for _,r in cases.iterrows():
        expected=re.sub(r'\s+',' ',blind_map[r.review_id]).strip()[:240]
        if r.short_redacted_excerpt!=expected or r.excerpt_sha256!=sha_text(expected): case_fail.append(r.review_id)
    checks.append(item('case_registry_rows_use_review_id_and_sealed_redacted_excerpt',len(cases)<=6 and not case_fail,{'rows':len(cases),'failures':case_fail}))
    paper=root/'paper'/'Q1_GAP_RESULT_FREEZE.md'
    ptext=paper.read_text(encoding='utf-8') if paper.exists() else ''
    checks.append(item('paper_candidate_exists_with_required_boundaries',
                       paper.exists() and 'CANDIDATE_PENDING_CONTROLLER_REVIEW' in ptext and 'PARTIALLY_STABLE' in ptext and '不得解释为因果' in ptext and 'not' not in ptext.lower()[:0],
                       {'path':str(paper),'bytes':paper.stat().st_size if paper.exists() else None}))
    before=json.loads((rd/'paper_manuscript_before.json').read_text(encoding='utf-8'))
    manuscript=root/'paper'/'manuscript'; after={str(p.relative_to(root)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':sha_file(p)} for p in sorted(manuscript.rglob('*')) if p.is_file()}
    checks.append(item('paper_manuscript_unchanged',before==after,{'changes':[k for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k)]}))
    pre=['input_manifest.json','environment.json','manual_review_parse_audit.csv','manual_text_review_joined.csv','manual_validation_statistics.csv','manual_case_registry.csv']
    checks.append(item('preverification_artifacts_present',all((rd/x).exists() for x in pre),{'missing':[x for x in pre if not (rd/x).exists()]}))
    summary={'total':len(checks),'pass':sum(c['status']=='PASS' for c in checks),'fail':sum(c['status']=='FAIL' for c in checks)}
    payload={'run_id':rd.name,'generated_local':__import__('datetime').datetime.now().astimezone().isoformat(timespec='seconds'),
             'status':'PASS' if summary['fail']==0 else 'FAIL','summary':summary,'verifier_imports_executor':False,
             'checks':checks,'independent_parse_counts':counts,'independent_correlations':recomputed,
             'note':'Verifier ran before output_manifest.json by design.'}
    (rd/'verification.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'summary':summary},ensure_ascii=False))
    return 0 if payload['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
