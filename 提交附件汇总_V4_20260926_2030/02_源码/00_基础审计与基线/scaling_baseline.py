# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
"""Audit B1--B12 and fit independently validated first-pass scaling models.

AI-assisted: OpenAI Codex / OpenAI / 2026-09-24.
Exact model version and release date are unknown and require verification.
Raw attachments are read-only. Model provenance follows the supplied data manual;
half-synthetic, interpolated and estimated rows never enter the B1 main fit.
Run: D:\\anaconda\\python.exe solution/src/scaling_baseline.py
"""
from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import DATA, SEED, output_dir, save_json, write_report, configure_stdout

ROOT = DATA / 'B_scaling_laws'
OUT = output_dir('scaling')
TABLES = {
 'B1': ('pythia_training_log_existing.csv', '标注为真实轨迹：说明文件口径，来源及变换待核验'),
 'B2': ('cerebras_training_log.csv', '半合成：模型族外情景验证'),
 'B4': ('scaling_baseline.csv', '真实：公开跨族收敛点，绝对损失口径不保证一致'),
 'B5': ('published_scaling_data.csv', '真实：文献整理，绝对损失口径不保证一致'),
 'B6': ('supplementary_NQ_experiment.csv', '半合成：质量情景'),
 'B7': ('supplementary_NQ_experiment_expanded.csv', '半合成：含B6重复点'),
 'B8': ('supplementary_NQ_experiment_large.csv', '半合成：含calibrated/extrapolated标记'),
 'B9': ('supplementary_large_models.csv', '真实公开元数据：含缺失及计算口径差异'),
 'B10': ('supplementary_large_baseline.csv', '估算：非独立观测'),
 'B11': ('open_model_family_metadata.csv', '真实元数据：辅助'),
 'B12': ('pythia_checkpoint_index.csv', '真实索引：辅助'),
}
KEYS = ['E', 'A', 'B', 'alpha', 'beta']


def clean_json(v):
    """Convert non-finite audit values to JSON null, never a fabricated zero."""
    if isinstance(v, dict): return {str(k): clean_json(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, np.ndarray)): return [clean_json(x) for x in v]
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (float, np.floating)): return float(v) if np.isfinite(v) else None
    return v


def audit_table(tag, path, provenance):
    df = pd.read_csv(path)
    numeric = df.select_dtypes(include='number')
    audit = {'id': tag, 'file': str(path.relative_to(DATA)), 'provenance': provenance,
             'rows': len(df), 'columns': list(df.columns), 'duplicate_rows': int(df.duplicated().sum()),
             'missing_by_column': df.isna().sum().to_dict(),
             'numeric_ranges': {c: {'min': numeric[c].min(), 'max': numeric[c].max(),
                                   'nonfinite_nonmissing': int((~np.isfinite(numeric[c]) & numeric[c].notna()).sum())}
                                for c in numeric},
             'units': {c: u for c, u in {'N_params_B': '1e9 parameters', 'D_tokens_B': '1e9 tokens',
                         'C_FLOPs_1e21': '1e21 FLOPs', 'FLOPs': 'FLOPs', 'val_loss': 'cross-entropy; source-dependent',
                         'Q_score': 'provided dimensionless score; not calibrated to A quality'}.items() if c in df}}
    if {'N_params_B','D_tokens_B'}.issubset(df):
        key = ['N_params_B','D_tokens_B'] + (['Q_score'] if 'Q_score' in df else [])
        audit['duplicate_NDQ_keys'] = int(df.duplicated(key).sum())
        for c in key: audit.setdefault('nonpositive_input_count', {})[c] = int((df[c] <= 0).sum())
        if 'C_FLOPs_1e21' in df or 'FLOPs' in df:
            col = 'C_FLOPs_1e21' if 'C_FLOPs_1e21' in df else 'FLOPs'
            observed = df[col] * (1e21 if col == 'C_FLOPs_1e21' else 1.)
            expected = 6e18 * df.N_params_B * df.D_tokens_B
            ratio = observed / expected
            valid = np.isfinite(ratio) & (expected > 0)
            # Four-decimal C_1e21 logs can have large relative error at tiny N*D.
            audit['compute_ratio_to_6ND'] = {'n': int(valid.sum()), 'quantiles': ratio[valid].quantile([0,.05,.5,.95,1]).to_dict(),
                                         'relative_difference_above_5pct': int(((ratio-1).abs()[valid] > .05).sum())}
            result = df.copy()
            result['C_reported_FLOPs'] = observed
            result['C_6ND_FLOPs'] = expected
            result['ratio_reported_to_6ND'] = ratio
            if col == 'C_FLOPs_1e21':
                result['abs_difference_in_1e21'] = (observed-expected).abs()/1e21
                result['within_C_rounding_0.00005'] = result.abs_difference_in_1e21 <= .00005 + 1e-10
                audit['compute_ratio_to_6ND']['within_rounding_fraction'] = float(result['within_C_rounding_0.00005'].mean())
            result.to_csv(OUT/f'{tag}_compute_audit.csv', index=False, encoding='utf-8-sig')
    for c in ['data_type','family','interpolated']:
        if c in df: audit[f'{c}_counts'] = df[c].value_counts(dropna=False).to_dict()
    return df, clean_json(audit)


def predict(params, n, d, q=None):
    n, d = np.asarray(n), np.asarray(d)
    effective_d = d if q is None else d*np.exp(params['k']*(np.asarray(q)-params.get('Q_ref',.5)))
    return params['E'] + params['A']*n**(-params['alpha']) + params['B']*effective_d**(-params['beta'])


def weights(df, mode):
    if mode == 'point': return np.ones(len(df))
    # Ten equal log-token bins per size. Nonempty cells have equal total weight.
    edges = np.linspace(np.log10(df.D_tokens_B.min())-1e-10,np.log10(df.D_tokens_B.max())+1e-10,11)
    bins = pd.cut(np.log10(df.D_tokens_B), edges, labels=False)
    cells = df.N_params_B.astype(str)+'|'+bins.astype(str)
    w = 1/cells.map(cells.value_counts()).to_numpy()
    return w/w.mean()


def fit_model(df, loss='linear', weight_mode='point', nstarts=10, seed=SEED, quality=False):
    n, d, y = [df[c].to_numpy(float) for c in ['N_params_B','D_tokens_B','val_loss']]
    q = df.Q_score.to_numpy(float) if quality else None
    w = np.sqrt(weights(df,weight_mode))
    lb = np.log([1e-6,1e-6,1e-6,.005,.005])
    ub = np.log([10.,100.,100.,3.,3.])
    if quality: lb, ub = np.r_[lb,-20.], np.r_[ub,20.]
    def decode(z):
        p = dict(zip(KEYS,np.exp(z[:5])))
        if quality: p.update(k=float(z[5]), Q_ref=.5)
        return p
    def residual(z): return w*(predict(decode(z),n,d,q)-y)
    rng = np.random.default_rng(seed)
    starts = [np.log([1.6,.5,1.2,.3,.3])]
    starts += [np.log([rng.uniform(.05,2),rng.uniform(.1,2),rng.uniform(.1,3),rng.uniform(.07,.7),rng.uniform(.07,.7)]) for _ in range(nstarts-1)]
    if quality: starts = [np.r_[s,rng.uniform(-2,2)] for s in starts]
    results=[]
    for start in starts:
        fit=least_squares(residual,start,bounds=(lb,ub),loss=loss,f_scale=.10,max_nfev=1800,
                          ftol=1e-10,xtol=1e-10,gtol=1e-10)
        results.append(fit)
    best = min(results,key=lambda x:x.cost)
    p = decode(best.x)
    return p, {'optimizer_success':bool(best.success),'objective':float(best.cost),
               'n_starts': nstarts,'n_successful_starts':sum(x.success for x in results),
               'objective_min':float(min(x.cost for x in results)), 'objective_max':float(max(x.cost for x in results)),
               'jacobian_condition_number':float(np.linalg.cond(best.jac)),
               'near_bound_parameters':[k for k,z,l,u in zip(KEYS+(['k'] if quality else []),best.x,lb,ub) if min(z-l,u-z)<.01],
               'loss':loss,'weight_mode':weight_mode}


def metrics(y,p):
    y,p=np.asarray(y),np.asarray(p); r=p-y
    ss=float(np.sum((y-y.mean())**2))
    return {'n':len(y),'RMSE':float(np.sqrt(np.mean(r*r))),'MAE':float(np.mean(np.abs(r))),
            'bias_pred_minus_actual':float(r.mean()),'R2':float(1-np.sum(r*r)/ss) if ss>0 else None,
            'max_abs_error':float(np.max(np.abs(r)))}


def add_predictions(df,p):
    result=df.copy()
    result['prediction']=predict(p,df.N_params_B,df.D_tokens_B,df.Q_score if 'k' in p else None)
    result['residual_pred_minus_actual']=result.prediction-result.val_loss
    return result


def validate_configs(b1):
    comparisons=[]; fold_rows=[]; prediction_rows=[]; fitted={}
    for weight_mode in ['point','logD_equal_bins']:
        for loss in ['linear','soft_l1']:
            label=f'{weight_mode}__{loss}'
            print('Fitting',label,flush=True)
            p, info=fit_model(b1,loss,weight_mode,12)
            fitted[label]={'parameters':p,**info,'in_sample':metrics(b1.val_loss,predict(p,b1.N_params_B,b1.D_tokens_B))}
            full=add_predictions(b1,p); full['configuration']=label; full['split']='in_sample'
            prediction_rows.append(full)
            lomo=[]
            for size in sorted(b1.N_params_B.unique()):
                train=b1[b1.N_params_B!=size]; test=b1[b1.N_params_B==size]
                fp, _=fit_model(train,loss,weight_mode,5)
                pred=add_predictions(test,fp); pred['configuration']=label; pred['split']='leave_one_model_out'
                prediction_rows.append(pred)
                fold_rows.append({'configuration':label,'split':'leave_one_model_out','held_out_N_B':size,**metrics(test.val_loss,pred.prediction)})
                lomo.append(pred)
            # Chronological extrapolation: train at <=80% final tokens, test later.
            dmax=b1.groupby('N_params_B').D_tokens_B.transform('max')
            mask=b1.D_tokens_B<=.8*dmax
            fp,_=fit_model(b1[mask],loss,weight_mode,8)
            pred=add_predictions(b1[~mask],fp); pred['configuration']=label; pred['split']='last_20pct_tokens'
            prediction_rows.append(pred)
            for size, group in pred.groupby('N_params_B'):
                fold_rows.append({'configuration':label,'split':'last_20pct_tokens','held_out_N_B':size,**metrics(group.val_loss,group.prediction)})
            m=metrics(pd.concat(lomo).val_loss,pd.concat(lomo).prediction)
            stage=metrics(pred.val_loss,pred.prediction)
            comparisons.append({'configuration':label,**{f'fit_{k}':v for k,v in fitted[label]['in_sample'].items()},
                                **{f'LOMO_{k}':v for k,v in m.items()},**{f'stage_{k}':v for k,v in stage.items()},
                                'validation_selection_score':(m['RMSE']+stage['RMSE'])/2})
    comparisons=pd.DataFrame(comparisons).sort_values('validation_selection_score')
    comparisons.to_csv(OUT/'model_comparison.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(fold_rows).to_csv(OUT/'validation_by_model.csv',index=False,encoding='utf-8-sig')
    predictions=pd.concat(prediction_rows,ignore_index=True)
    predictions.to_csv(OUT/'B1_all_predictions.csv',index=False,encoding='utf-8-sig')
    save_json(OUT/'all_fits.json',clean_json(fitted))
    return comparisons,fitted,predictions


def quality_audit(data, main_params):
    reports={}; all_slopes=[]; all_fit=[]; quality_parameters={}
    for tag in ['B6','B7','B8']:
        df=data[tag]
        slopes=[]
        for (n,d), group in df.groupby(['N_params_B','D_tokens_B']):
            group=group.sort_values('Q_score')
            slope=float(np.polyfit(group.Q_score,group.val_loss,1)[0])
            delta=group.val_loss.diff().dropna()
            slopes.append({'table':tag,'N_params_B':n,'D_tokens_B':d,'n':len(group),'linear_slope_dL_dQ':slope,
                           'spearman_Q_loss':float(spearmanr(group.Q_score,group.val_loss).statistic),
                           'increasing_adjacent_pairs':int((delta>0).sum()),'decreasing_adjacent_pairs':int((delta<0).sum()),
                           'first_loss':group.val_loss.iloc[0],'last_loss':group.val_loss.iloc[-1]})
        s=pd.DataFrame(slopes); all_slopes.append(s)
        p,info=fit_model(df,loss='linear',nstarts=12,quality=True)
        pred=add_predictions(df,p); pred['table']=tag; all_fit.append(pred)
        reports[tag]={'groups':len(s),'positive_group_slopes':int((s.linear_slope_dL_dQ>0).sum()),
                      'negative_group_slopes':int((s.linear_slope_dL_dQ<0).sum()),
                      'median_group_slope':float(s.linear_slope_dL_dQ.median()),
                      'adjacent_increase_fraction':float(s.increasing_adjacent_pairs.sum()/(s.increasing_adjacent_pairs.sum()+s.decreasing_adjacent_pairs.sum())),
                      'parameters':p,'fit':metrics(df.val_loss,pred.prediction),**info}
        quality_parameters[tag]=p
    key=['N_params_B','D_tokens_B','Q_score']
    overlap=[]
    for left,right in [('B6','B7'),('B6','B8'),('B7','B8')]:
        join=data[left].merge(data[right],on=key,suffixes=('_left','_right'))
        row={'left':left,'right':right,'matching_keys':len(join)}
        if len(join):
            delta=join.val_loss_left-join.val_loss_right
            row.update(exact_same_loss=int((delta.abs()<1e-12).sum()), max_abs_difference=float(delta.abs().max()),mean_abs_difference=float(delta.abs().mean()))
        overlap.append(row)
    pd.concat(all_slopes).to_csv(OUT/'quality_within_ND_slopes.csv',index=False,encoding='utf-8-sig')
    pd.concat(all_fit).to_csv(OUT/'quality_scenario_predictions.csv',index=False,encoding='utf-8-sig')
    # B7 contains B6; no doubled fitting and no claim of independent validation.
    # Estimate B6 parameter k and transfer it only as an explicit scenario to B1.
    qp=quality_parameters['B6']
    transfer={**main_params,'k':qp['k'],'Q_ref':.5}
    # B7's additional Q grid tests only interpolation within a related generator.
    new_b7=data['B7'].merge(data['B6'][key],on=key,how='left',indicator=True)
    new_b7=new_b7[new_b7['_merge']=='left_only'].drop(columns='_merge')
    novel_pred=add_predictions(new_b7,qp)
    novel_pred.to_csv(OUT/'B7_novel_grid_predicted_from_B6.csv',index=False,encoding='utf-8-sig')
    quality_cv=[]
    for n in sorted(data['B6'].N_params_B.unique()):
        train=data['B6'][data['B6'].N_params_B!=n]
        test=data['B6'][data['B6'].N_params_B==n]
        cp,_=fit_model(train,nstarts=5,quality=True)
        quality_cv.append({'split':'leave_one_N_B_out','heldout':float(n),**metrics(test.val_loss,predict(cp,test.N_params_B,test.D_tokens_B,test.Q_score))})
    train=data['B6'][data['B6'].Q_score<=.6]; test=data['B6'][data['B6'].Q_score>.6]
    cp,_=fit_model(train,nstarts=8,quality=True)
    quality_cv.append({'split':'Q_train_le_0.6_test_gt_0.6','heldout':None,**metrics(test.val_loss,predict(cp,test.N_params_B,test.D_tokens_B,test.Q_score))})
    pd.DataFrame(quality_cv).to_csv(OUT/'quality_B6_validation.csv',index=False,encoding='utf-8-sig')
    quality={'formula':'E + A*N_B^(-alpha) + B*(D_B*exp(k*(Q-Q_ref)))^(-beta)',
             'table_results':reports,'overlap':overlap,'transfer_scenario':transfer,
             'B7_novel_grid_validation':{'status':'related half-synthetic generator; not independent empirical validation',**metrics(novel_pred.val_loss,novel_pred.prediction)},
             'B6_grouped_validation':quality_cv,
             'transfer_status':'UNVALIDATED_SCENARIO_ONLY',
             'transfer_assumptions':['B6 effective-token quality coefficient transfers to B1.',
                                     'A-derived Q is mapped to B Q_score; identity mapping is not empirically calibrated.',
                                     'Pythia reference corpus is assigned Q_ref=0.5 for scenario anchoring only.'],
             'warning':'B8 has the opposite quality direction to B6/B7. Its E and k hit fitting bounds; diagnostic fit is unsuitable for Q3. Never pool these tables.'}
    save_json(OUT/'quality_audit.json',clean_json(quality))
    return quality


def make_figures(b1, chosen, predictions, quality):
    fig,axes=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
    colors=plt.get_cmap('viridis')(np.linspace(.05,.95,8))
    for color,(n,g) in zip(colors,b1.groupby('N_params_B')):
        axes[0].scatter(g.D_tokens_B,g.val_loss,s=8,alpha=.45,color=color)
        ds=np.geomspace(g.D_tokens_B.min(),g.D_tokens_B.max(),200)
        axes[0].plot(ds,predict(chosen,n,ds),color=color,label=f'{n:.3g}B')
        axes[1].scatter(g.D_tokens_B,predict(chosen,g.N_params_B,g.D_tokens_B)-g.val_loss,s=8,color=color,alpha=.5)
    axes[0].set(xscale='log',xlabel='Training tokens (billions)',ylabel='Validation loss',title='B1: all checkpoints retained')
    axes[0].legend(ncol=2,fontsize=8)
    axes[1].axhline(0,color='black',lw=.8)
    axes[1].set(xscale='log',xlabel='Training tokens (billions)',ylabel='Predicted - observed loss',title='Residual dependence on training stage')
    for ext in ['png','pdf']: fig.savefig(OUT/f'scaling_fit_residuals.{ext}',dpi=200)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,4),layout='constrained')
    for tag,color in zip(['B6','B7','B8'],['#2874A6','#E67E22','#943126']):
        s=pd.read_csv(OUT/'quality_within_ND_slopes.csv'); s=s[s.table==tag]
        ax.scatter(s.N_params_B,s.linear_slope_dL_dQ,label=tag,alpha=.5,s=16,color=color)
    ax.axhline(0,color='black',lw=.8); ax.set(xscale='log',xlabel='Parameters (billions)',ylabel='Within-(N,D) slope of loss vs Q',title='Half-synthetic quality direction audit')
    ax.legend()
    for ext in ['png','pdf']: fig.savefig(OUT/f'quality_direction_audit.{ext}',dpi=200)
    plt.close(fig)


def main():
    configure_stdout(); OUT.mkdir(parents=True,exist_ok=True)
    data={}; audits=[]
    for tag,(filename,provenance) in TABLES.items():
        data[tag],audit=audit_table(tag,ROOT/filename,provenance); audits.append(audit)
    parts=[]
    for file in sorted((ROOT/'training_trajectories').glob('*.csv')):
        df,audit=audit_table('B3',file,'插值：源于B1检查点，非独立验证')
        df['file']=file.name; parts.append(df); audits.append(audit)
    data['B3']=pd.concat(parts,ignore_index=True)
    save_json(OUT/'table_audit.json',audits)
    pd.DataFrame([{'id':a['id'],'file':a['file'],'rows':a['rows'],'duplicate_rows':a['duplicate_rows'],
                   'missing_cells':sum(a['missing_by_column'].values()),'provenance':a['provenance']} for a in audits]).to_csv(OUT/'table_audit_summary.csv',index=False,encoding='utf-8-sig')
    b1=data['B1']
    comparisons,fitted,predictions=validate_configs(b1)
    # Avoid crediting a robust method for numerical noise (1% near-tie rule).
    near=comparisons[comparisons.validation_selection_score<=1.01*comparisons.validation_selection_score.min()]
    priority=['point__linear','point__soft_l1','logD_equal_bins__linear','logD_equal_bins__soft_l1']
    selected=next(c for c in priority if c in near.configuration.values)
    chosen=fitted[selected]['parameters']
    external=[]
    for tag in ['B2','B3','B4','B5','B10']:
        pred=add_predictions(data[tag],chosen); pred.to_csv(OUT/f'{tag}_predictions.csv',index=False,encoding='utf-8-sig')
        external.append({'table':tag,'group':'all',**metrics(pred.val_loss,pred.prediction)})
        for col in ['family','N_params_B']:
            if col in pred:
                for group,g in pred.groupby(col): external.append({'table':tag,'group':f'{col}={group}',**metrics(g.val_loss,g.prediction)})
    pd.DataFrame(external).to_csv(OUT/'external_validation.csv',index=False,encoding='utf-8-sig')
    q=quality_audit(data,chosen)
    # Cluster bootstrap resamples whole model trajectories, not correlated rows.
    rng=np.random.default_rng(SEED+1); sizes=b1.N_params_B.unique(); bootstrap=[]
    print('Cluster bootstrap: 80 replicates; 8 observed model sizes.',flush=True)
    for i in range(80):
        sampled=rng.choice(sizes,len(sizes),replace=True)
        boot=pd.concat([b1[b1.N_params_B==n] for n in sampled],ignore_index=True)
        bp,bi=fit_model(boot,fitted[selected]['loss'],fitted[selected]['weight_mode'],3,SEED+i)
        bootstrap.append({'replicate':i,'unique_sizes':len(set(sampled)),**bp,'success':bi['optimizer_success']})
    bootdf=pd.DataFrame(bootstrap); bootdf.to_csv(OUT/'cluster_bootstrap_parameters.csv',index=False,encoding='utf-8-sig')
    intervals={k:{'p2_5':float(bootdf[k].quantile(.025)),'median':float(bootdf[k].median()),'p97_5':float(bootdf[k].quantile(.975))} for k in KEYS}
    diagnostics=[]
    pred=add_predictions(b1,chosen)
    residual=pred.residual_pred_minus_actual
    precision={'val_loss_csv_decimal_places':4,'loss_rounding_half_unit':.00005,
               'D_tokens_B_csv_decimal_places':3,'D_rounding_half_unit_B':.0005,
               'residual_quantiles':residual.quantile([0,.01,.05,.5,.95,.99,1]).to_dict(),
               'abs_residual_quantiles':residual.abs().quantile([0,.5,.9,.95,.99,1]).to_dict(),
               'fraction_abs_residual_le_loss_half_rounding_unit':float((residual.abs()<=.00005).mean()),
               'rmse_in_loss_rounding_half_units':float(np.sqrt(np.mean(residual**2))/.00005),
               'interpretation':'Near-deterministic scaling signature. Source and any transformations require verification; tiny errors do not establish an independently discovered empirical law.'}
    save_json(OUT/'B1_precision_residual_audit.json',clean_json(precision))
    for n,g in pred.groupby('N_params_B'):
        r=g.sort_values('D_tokens_B').residual_pred_minus_actual.to_numpy()
        diagnostics.append({'N_params_B':n,**metrics(g.val_loss,g.prediction),
                            'residual_spearman_logD':float(spearmanr(np.log(g.D_tokens_B),g.residual_pred_minus_actual).statistic),
                            'durbin_watson_descriptive':float(np.sum(np.diff(r)**2)/np.sum(r*r))})
    pd.DataFrame(diagnostics).to_csv(OUT/'residual_diagnostics.csv',index=False,encoding='utf-8-sig')
    payload={'schema_version':1,'source':'B1 only','formula':'E + A*N_B**(-alpha) + B*D_B**(-beta)',
             'units':{'N_B':'1e9 parameters','D_B':'1e9 tokens','loss':'B1 cross entropy'},
             'parameters':chosen,'observed_ranges':{'N_B':[float(b1.N_params_B.min()),float(b1.N_params_B.max())],
                                                   'D_B':[float(b1.D_tokens_B.min()),float(b1.D_tokens_B.max())]},
             'model_selection':{'configuration':selected,'criterion':'mean of pooled leave-one-model-out RMSE and last-20%-tokens RMSE; within 1% prefer simpler point-weighted linear loss',
                                'data_use':'all 1176 B1 checkpoints; no random row split; validation-guided choice is exploratory',
                                'comparison_file':'model_comparison.csv'},
             'bootstrap_percentiles':intervals,'bootstrap_caution':'Only 8 trajectory clusters; descriptive conditional intervals, not reliable broad population confidence.',
             'quality_scenario':q['transfer_scenario'],'quality_scenario_status':q['transfer_status'],
             'quality_assumptions':q['transfer_assumptions'],
             'not_included':['A-derived quality scale calibration','domain mixture transfer','architecture/family offsets'],
             'limitations':['B1 is labeled real by the attachment manual, but its near-deterministic law signature requires source/transformation verification.',
                            'Extrapolation beyond observed N,D unsupported by B1 alone.','B2 is half-synthetic and B3 interpolated, neither independent empirical validation.',
                            'B4/B5 cross-family loss comparisons have uncontrolled tokenizer and validation-corpus differences.',
                            'B10 losses are estimates and cannot validate the generating law.','B8 quality trend must be checked separately.']}
    save_json(OUT/'scaling_params.json',clean_json(payload))
    make_figures(b1,chosen,predictions,q)
    lines=['# B 数据审计与经典标度律首轮基线（2026-09-24）','',
           '这是可复现的探索性基线，不是定稿模型。来源性质采用赛题数据说明；没有把半合成、插值或估算点加入 B1 主拟合。',
           '运行：`D:\\anaconda\\python.exe solution/src/scaling_baseline.py`。结果保存在 `solution/outputs/scaling/`。','',
           '## 数据审计','', '|表|记录数|整行重复|缺失单元格|性质|','|---|---:|---:|---:|---|']
    for a in audits: lines.append(f"|{a['id']} {Path(a['file']).name}|{a['rows']}|{a['duplicate_rows']}|{sum(a['missing_by_column'].values())}|{a['provenance']}|")
    lines += ['', '单位：N_params_B、D_tokens_B 分别为十亿参数、十亿 token；C_FLOPs_1e21 为 10²¹ FLOPs。换算公式为 C_21=0.006 N_B D_B。完整逐字段缺失、范围和计算量比值见 table_audit.json；不能把所有缺失填成零。',
              'B1/B2 的微小预算处日志取整会放大相对误差，另列绝对舍入误差。B9 的 FLOPs 可能反映激活参数、实际训练过程或公开估计口径，不强行改写成 6ND。','',
              '## 主拟合与结构化验证','',
              '模型为 L=E+A N_B^{-α}+B D_B^{-β}。五个参数均取对数优化保证正数，每次拟合多起点。比较普通最小二乘与 soft-L1（尺度0.10），以及原始检查点等权与每个模型十个 logD 区间等权。全部早期训练点保留。',
              '留一模型验证按 N 分组；时间验证以每个模型末次 D 的80%划界，仅用早期训练预测末20%。不随机拆分高度相关的检查点。配置按两类验证整体RMSE均值选择，在最优分数1%内优先普通最小二乘、原始点等权，避免把数值误差视为稳健估计改进。这是一轮探索性模型选择，没有独立最终测试集。','',
              '|配置|拟合RMSE|留模型RMSE|末20%训练RMSE|','|---|---:|---:|---:|']
    for r in comparisons.itertuples(): lines.append(f'|{r.configuration}|{r.fit_RMSE:.6f}|{r.LOMO_RMSE:.6f}|{r.stage_RMSE:.6f}|')
    lines += ['',f'选中：**{selected}**；参数（N、D使用十亿单位）为：', '', '```json',json.dumps(chosen,ensure_ascii=False,indent=2),'```','',
              f"**B1只能称为附件标注的真实轨迹。** 拟合RMSE约{np.sqrt(np.mean(residual**2)):.7f}，为Loss四位小数半舍入单位0.00005的{precision['rmse_in_loss_rounding_half_units']:.2f}倍；这种近乎严格幂律的现象需要追查原始来源及是否经过变换。D本身仅保留三位小数，也会传播误差。接近1的R²不能作为独立发现新规律的强证据。完整残差分位数见B1_precision_residual_audit.json。",'',
              '各模型误差见 validation_by_model.csv；所有预测见 B1_all_predictions.csv；残差自相关及随 logD 的相关见 residual_diagnostics.csv。参数 bootstrap 以完整模型轨迹为重采样单元，共80次；只有8个规模簇，区间只是条件稳定性描述，不能作为广泛适用的严格置信区间。',
              '', '## 族外、插值与大规模外推','', '|数据|RMSE|平均偏差（预测−原值）|解释边界|','|---|---:|---:|---|']
    contexts={'B2':'半合成族外情景，非真实新实验','B3':'源于B1的插值，非独立证据','B4':'不同模型族/验证语料/分词器不可直接同口径','B5':'文献绝对损失口径未统一','B10':'由模型估算的Loss，不能当验证真值'}
    for row in external:
        if row['group']=='all': lines.append(f"|{row['table']}|{row['RMSE']:.5f}|{row['bias_pred_minus_actual']:.5f}|{contexts[row['table']]}|")
    lines += ['', 'B9 用于记录大模型的 N、D 和 FLOPs 覆盖范围及缺失；B10只作估算值对照，不用它证明百亿以上外推准确。对Q3超过 B1 规模范围的配置必须标记外推，尤其不能把接近零的训练误差当真实泛化保证。', '',
              '## 质量效应核查','', '|数据|固定(N,D)组数|斜率为负组数|斜率为正组数|相邻Q升高但Loss升高比例|拟合k|','|---|---:|---:|---:|---:|---:|']
    for tag,r in q['table_results'].items(): lines.append(f"|{tag}|{r['groups']}|{r['negative_group_slopes']}|{r['positive_group_slopes']}|{r['adjacent_increase_fraction']:.3f}|{r['parameters']['k']:.5f}|")
    lines += ['', '逐组方向用组内直线斜率和 Spearman 排名核查，允许噪声导致局部非单调。质量情景式为 L=E+A N_B^{-α}+B[D_B exp(k(Q−0.5))]^{-β}，k>0对应提升Q降低损失，k<0为相反方向。每个表独立拟合，不合并互相矛盾的质量规律。', '',
              '重叠核查：','```json', json.dumps(q['overlap'],ensure_ascii=False,indent=2),'```','',
              '**B6与B7不得作为独立重复实验。B8如与B6/B7在共同网格上给出相反质量方向，则不应无说明地取平均，更不能把它用于证明“质量越高损失越低”。**',
              f"B7不在B6中的90个新增Q网格点，使用仅在B6拟合的参数预测，RMSE={q['B7_novel_grid_validation']['RMSE']:.5f}；仍属于同源半合成插值检验。B6按规模留一及用Q≤0.6预测Q>0.6的结果见quality_B6_validation.csv。B8的诊断模型E与k触及边界，不适合提供问题三参数。",'',
              '', '供Q3的 scaling_params.json 包含 B1 参数及一个单独标记的质量迁移情景：取 B6 估得 k，假定可迁移到 B1，把 Pythia 的未知参考质量暂定为0.5。该情景尚未实证验证，A评分与B的Q_score不能直接视为同尺度；主报告必须保留映射与k=0等敏感性分析。此处尚未引入领域配比p。', '',
              '## 公式与下一步接口','',
              '令 X=A N_B^{-α}，Y=B[D_B exp(k(Q−Qref))]^{-β}，则 ∂L/∂N_B=−αX/N_B，∂L/∂D_B=−βY/D_B，∂L/∂Q=−βkY。对应损失弹性为 −αX/L、−βY/L、−βkQY/L。物理 N、D 的导数需除以10⁹。',
              '质量提升 δ 相当于参数扩张：X_new=X−Y[1−exp(−βkδ)]。当 X_new>0 时 N_new=N_B(X/X_new)^(1/α)，等于0只在参数趋于无穷时达到，小于0不存在有限参数替代；δ还需满足Q可行边界。该推导依赖上述特定情景模型，不等于已证实的现实替代率。',
              '下一步需建立A质量与B质量的标定情景、配比到损失的跨来源迁移检验、外部文献原值核查、模型结构及外推不确定性。', '',
              'AI辅助记录：OpenAI Codex / OpenAI / 2026-09-24；精确模型版本与发布日期未知待核对。建模、推导及结论需由参赛者理解、核验并据官方规范披露。']
    write_report('scaling_baseline.md','\n'.join(lines)+'\n')
    print(json.dumps(clean_json({'selected':selected,'parameters':chosen,'comparison':comparisons.to_dict('records'),
                               'quality':{k:{x:r[x] for x in ['positive_group_slopes','negative_group_slopes','median_group_slope']} for k,r in q['table_results'].items()}}),ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__': main()
