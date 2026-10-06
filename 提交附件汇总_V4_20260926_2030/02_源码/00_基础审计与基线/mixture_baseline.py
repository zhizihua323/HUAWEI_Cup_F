# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
"""A4-A15 audit and leakage-aware mixture regression baselines.

AI-assisted: OpenAI Codex, OpenAI, 2026-09-24. Exact model/version and
release date await verification; see README. No source data are modified.
Mixture polynomial uses Scheffe linear terms and distinct pair products,
not an intercept plus all 17 dependent proportions. No logarithmic pseudo-count.
"""
from pathlib import Path
import hashlib
import json
import itertools
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import KFold, GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from common import DATA, SEED, output_dir, save_json, write_report, configure_stdout

FAMILIES = ['linear', 'quadratic']
ALPHAS = np.logspace(-5, 3, 9)

def features(p, family):
    if family == 'linear': return p
    return np.column_stack([p] + [p[:, i]*p[:, j] for i,j in itertools.combinations(range(p.shape[1]),2)])

def estimator(alpha=1):
    return make_pipeline(StandardScaler(with_mean=False), Ridge(alpha=alpha, fit_intercept=False))

def train_search(x,y,seed=SEED):
    cv=KFold(n_splits=5, shuffle=True, random_state=seed)
    return GridSearchCV(estimator(), {'ridge__alpha':ALPHAS}, scoring='neg_mean_squared_error', cv=cv, n_jobs=1).fit(x,y)

def recipe_hashes(p):
    return [hashlib.sha256(np.round(row,12).astype('<f8').tobytes()).hexdigest() for row in p]

def evaluate(y,pred):
    a,b=y.mean(axis=1),pred.mean(axis=1)
    rho=float(spearmanr(a,b).statistic) if np.std(b)>1e-12 else None
    return {'n':len(y),'rmse_all_domains':float(np.sqrt(mean_squared_error(y,pred))),
            'mae_all_domains':float(mean_absolute_error(y,pred)),
            'r2_domain_mean':float(r2_score(y,pred)),
            'rmse_equal_domain_mean':float(np.sqrt(mean_squared_error(a,b))),
            'r2_equal_domain_mean':float(r2_score(a,b)),
            'spearman_equal_domain_mean':rho}

def main():
    configure_stdout(); out=output_dir('mixture')
    folder=DATA/'A_data_value'/'regmix_tables'
    labels=['train_1m','test_1m','test_60m','test_1B','est_10b','est_70b']
    sets={}; audit=[]; columns=None; losscols=None; train_hashes=set()
    for label in labels:
        prefix,scale=label.split('_',1)
        pfile=folder/f'{prefix}_mixture_{scale}.csv'; yfile=folder/f'{prefix}_pile_loss_{scale}.csv'
        p=pd.read_csv(pfile); y=pd.read_csv(yfile)
        pc=[c for c in p.columns if c.startswith('train_the_pile_')]
        yc=[c for c in y.columns if c.startswith('metric/')]
        if columns is None:columns=pc;losscols=yc
        assert pc==columns and yc==losscols
        assert not p['index'].duplicated().any() and not y['index'].duplicated().any()
        assert set(p['index'])==set(y['index'])
        joined=p.merge(y,on='index',validate='one_to_one',sort=False)
        raw=joined[pc].to_numpy(float); target=joined[yc].to_numpy(float)
        assert np.isfinite(raw).all() and np.isfinite(target).all() and (raw>=0).all()
        sums=raw.sum(axis=1); assert (sums>0).all()
        norm=raw/sums[:,None]; hashes=recipe_hashes(norm)
        if label=='train_1m': train_hashes=set(hashes)
        audit.append({'set':label,'rows':len(norm),'mixture_columns':len(pc),'loss_columns':len(yc),
                      'raw_sum_min':float(sums.min()),'raw_sum_max':float(sums.max()),
                      'max_abs_sum_error':float(np.max(np.abs(sums-1))),
                      'zero_fraction':float((raw==0).mean()),'duplicate_normalized_recipes':len(hashes)-len(set(hashes)),
                      'recipes_identical_to_training':len(set(hashes)&train_hashes),
                      'nature':'estimated_loss_training_recipe_subset' if prefix=='est' else 'observed',
                      'p_sha256':hashlib.sha256(pfile.read_bytes()).hexdigest(),
                      'loss_sha256':hashlib.sha256(yfile.read_bytes()).hexdigest()})
        sets[label]=(norm,target,joined['index'].to_numpy(),hashes)
        normalized=pd.DataFrame(norm,columns=pc);normalized.insert(0,'index',joined['index'])
        normalized.to_csv(out/f'{label}_normalized_mixtures.csv',index=False)
    save_json(out/'audit.json',audit)
    p_train,y_train,ids,_=sets['train_1m']; n=len(p_train)
    assert len(set(recipe_hashes(p_train)))==n, 'Switch to grouped CV when recipes repeat'
    folds=KFold(5,shuffle=True,random_state=SEED)
    metrics=[]; selections=[]; oofs={}; all_domain_metrics=[]
    for family in FAMILIES:
        x=features(p_train,family); oof=np.empty_like(y_train)
        for fold,(tr,va) in enumerate(folds.split(x)):
            search=train_search(x[tr],y_train[tr],SEED+fold+1)
            oof[va]=search.predict(x[va])
            selections.append({'family':family,'outer_fold':fold,'alpha':search.best_params_['ridge__alpha']})
        oofs[family]=oof
        metrics.append({'model':family,'set':'train_nested_oof',**evaluate(y_train,oof)})
    # Family selection is confined to the training data. Its selected OOF score
    # can be optimistic after choosing the family; test_1m is final confirmation.
    selected=min(FAMILIES,key=lambda name:mean_squared_error(y_train,oofs[name]))
    final_models={}; parameter_export={}; predictions=[]
    for family in FAMILIES:
        search=train_search(features(p_train,family),y_train)
        fitted=search.best_estimator_; final_models[family]=fitted
        coef=fitted.named_steps['ridge'].coef_/fitted.named_steps['standardscaler'].scale_[None,:]
        terms=[c.removeprefix('train_the_pile_') for c in pc]
        if family=='quadratic': terms+= [f'{terms[i]}*{terms[j]}' for i,j in itertools.combinations(range(17),2)]
        param=pd.DataFrame(coef.T,index=terms,columns=losscols);param.index.name='term'
        param.to_csv(out/f'{family}_coefficients.csv')
        parameter_export[family]={'alpha':search.best_params_['ridge__alpha'],'terms':terms,'coefficients':coef.tolist()}
        for label,(p,y,idx,_) in sets.items():
            pred=fitted.predict(features(p,family))
            status='training_fit' if label=='train_1m' else 'external_estimate_comparison' if label.startswith('est') else 'independent_1m_test' if label=='test_1m' else 'zero_shot_cross_scale'
            metrics.append({'model':family,'set':label,'role':status,**evaluate(y,pred)})
            for j,col in enumerate(losscols):
                all_domain_metrics.append({'model':family,'set':label,'domain':col,'rmse':float(np.sqrt(mean_squared_error(y[:,j],pred[:,j]))),'r2':float(r2_score(y[:,j],pred[:,j])), 'spearman':float(spearmanr(y[:,j],pred[:,j]).statistic)})
            for i,recipe_id in enumerate(idx):
                predictions.append({'model':family,'set':label,'index':int(recipe_id),'observed_or_estimated_mean_loss':float(y[i].mean()),'predicted_mean_loss':float(pred[i].mean()),'truth_kind':'estimated' if label.startswith('est') else 'observed'})
            detail=pd.DataFrame({'index':idx})
            for j,col in enumerate(losscols):detail['actual_'+col]=y[:,j];detail['pred_'+col]=pred[:,j]
            detail.to_csv(out/f'{family}_{label}_predictions.csv',index=False)
    # Constant reference is fit only to the training responses.
    for label,(_,y,_,_) in sets.items():
        metrics.append({'model':'training_domain_means','set':label,**evaluate(y,np.tile(y_train.mean(axis=0),(len(y),1)))})
    pd.DataFrame(metrics).to_csv(out/'metrics.csv',index=False)
    pd.DataFrame(all_domain_metrics).to_csv(out/'domain_metrics.csv',index=False)
    pd.DataFrame(predictions).to_csv(out/'aggregate_predictions.csv',index=False)
    save_json(out/'model.json',{'selected_by_training_only':selected,'objective':'equal_weight_mean_MSE_across_13_validation_domains','test_usage':'not_used_for_selection','units':'validation_cross_entropy_as_provided','features':pc,'reference_p':p_train.mean(axis=0).tolist(),'models':parameter_export,'outer_selections':selections})
    # Paired bootstrap uncertainty on test set, conditional on fitted models.
    rng=np.random.default_rng(SEED); p,y,idx,_=sets['test_1m']; pr=final_models[selected].predict(features(p,selected))
    samples=[]
    for _ in range(500):
        draw=rng.integers(0,len(y),len(y)); m=evaluate(y[draw],pr[draw]); samples.append([m['rmse_equal_domain_mean'],m['r2_equal_domain_mean'],m['spearman_equal_domain_mean']])
    cis=np.quantile(samples,[.025,.975],axis=0)
    save_json(out/'test_1m_conditional_intervals.json',{'model':selected,'resamples':500,'confidence':.95,'scope':'test-row sampling, conditional on fixed model; not full pipeline uncertainty','metrics':['rmse_equal_domain_mean','r2_equal_domain_mean','spearman_equal_domain_mean'],'lower':cis[0],'upper':cis[1]})
    # Describe the best *observed training recipe*, not an unvalidated new optimum.
    best=int(np.argmin(y_train.mean(axis=1)))
    save_json(out/'observed_training_reference.json',{'role':'descriptive_observed_training_best_not_global_optimum','index':int(ids[best]),'mean_loss':float(y_train[best].mean()),'p':dict(zip(pc,p_train[best]))})
    displayed=pd.DataFrame(metrics).query("model == @selected and set != 'train_1m'")
    rows='\n'.join(f"| {r['set']} | {r['n']} | {r['rmse_equal_domain_mean']:.4f} | {r['r2_equal_domain_mean']:.4f} | {r['spearman_equal_domain_mean']:.4f} |" for r in displayed.to_dict('records'))
    write_report('mixture_baseline.md',f'''# 配比数据审计与首轮基线

所有12张配比/Loss表通过index一一核对；17个配比变量保留零值，逐行除以行和以修正原表舍入误差。没有替换原文件。13个Loss按等权均值作为本轮总体目标，同时保存各验证域结果；等权是分析选择，不是题目给定事实。

线性与二次Scheffe混合多项式均不含额外截距，二次项仅使用不同域之间的乘积。使用训练集内5折嵌套交叉验证选择惩罚参数，最终模型族由训练OOF误差选择：**{selected}**。测试表没有用于调参。模型族选择后的OOF仍可能乐观，1M独立检验才是主要确认。

| 数据 | 行数 | 等权平均Loss RMSE | R² | Spearman |
|---|---:|---:|---:|---:|
{rows}

60M和1B结果是未经重校准的跨规模迁移，绝对误差与配方排序相关性必须分别解释。est两组是模型估算的外推Loss，不能称为真实独立验证。审计表记录了与训练配比的重叠数。

本轮尚未将Q加入配比模型：质量域与配方域缺少完整可验证映射，而且域级固定Q可能与p共线。尚未宣称任一配方为全局最优。`observed_training_reference.json`仅记录训练数据中实际观测均值最小的一行，不可当作独立检验结论。

Bootstrap区间仅反映固定模型下测试行抽样的不确定性，未包含模型选择、质量映射或跨规模偏差。后续需研究更合适的非线性表示与受数据支持范围约束的优化，再决定是否进入论文主模型。
''')
    print(json.dumps({'selected':selected,'metrics':displayed.to_dict('records'),'audit':audit},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
