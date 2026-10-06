"""只读定位已保存质量汇总中的有效样本数缺口，不读取原始 XZ。"""
from pathlib import Path
from datetime import datetime
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
Q=ROOT/'solution/outputs/quality'
summary=pd.read_csv(Q/'domain_summary.csv')
features=pd.read_csv(Q/'feature_summary.csv')
audit=json.loads((Q/'audit.json').read_text(encoding='utf-8'))
summary['group_mean_minus_Q_mean']=summary[['group_usability_mean','group_knowledge_mean','group_education_reasoning_mean']].mean(axis=1)-summary.Q_mean
summary.loc[abs(summary.group_mean_minus_Q_mean)>1e-10,['scope','domain','n','Q_mean','group_mean_minus_Q_mean']].to_csv(OUT/'quality_mean_discrepancies.csv',index=False,encoding='utf-8-sig')
deficits=[]
for _,row in features.iterrows():
    counts=row[[c for c in features.columns if c.endswith('__count')]]
    total=int(counts.max())
    for c,v in counts.items():
        if v<total:
            deficits.append({'file_id':row.file_id,'domain':row.domain,'feature':c.removesuffix('__count'),
                             'unique_group_rows':total,'nonmissing_count':int(v),'missing_count':total-int(v)})
pd.DataFrame(deficits).to_csv(OUT/'quality_missing_feature_counts.csv',index=False,encoding='utf-8-sig')
aggregate=[]
for domain in ['commoncrawl','wikipedia']:
    g=summary[summary.domain.eq(domain)]
    parts=g[g.scope.isin(['A1_calibration','A1_holdout'])]
    saved=float(g.loc[g.scope.eq('A1_all_unique'),'Q_mean'].iloc[0])
    weighted=float(np.average(parts.Q_mean,weights=parts.n))
    aggregate.append({'domain':domain,'weighted_by_total_rows':weighted,'saved_all_mean':saved,'difference':weighted-saved})
out={'timestamp_local':datetime.now().astimezone().isoformat(),'source':'saved audits + summary CSVs + static code inspection; no raw records reread',
     'feature_deficits':deficits,'aggregation_discrepancies':aggregate,
     'raw_list_audit':[{'file_id':f['file_id'],'field':k,'list_rows':f['rows'],'valid_finite_list_rows':v['valid_list_rows'],'nan_elements':v['nan']}
                       for f in audit['files'] for k,v in f['fields'].items() if v['nan'] and v['types'].get('list')],
     'confirmed_code_behavior':{'get_features':'Nonfinite list -> NaN scalar','score_quality':'Group and Q row means use skipna=False',
                                'summarize':'n is total rows; Q.mean() and group.mean() silently skip NaN',
                                'verify':'Requires Q_baseline.notna().all() (line 442)'},
     'interpretation':'Existing saved summaries contain different effective denominators. Total n is not valid-Q n. Under current code, nonfinite required features propagate to missing Q; the all-nonmissing assertion conflicts with these data. This is not evidence that the interrupted run reached that assertion.',
     'unconfirmed':['Exact identities and count of unique rows with any missing Q; overlaps between missing features unavailable without row artifact.','Actual exception, termination point, and quota interruption time.'],
     'action_taken':'Registered only; original code and outputs unchanged.'}
(OUT/'quality_gap_evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
