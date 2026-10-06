# Q1 Gap Result Freeze Candidate

状态：`CANDIDATE_PENDING_CONTROLLER_REVIEW`。本文件只汇总既有Q01C/T03E冻结结果与作者人工文本核验；不重做主Q，不重选质量特征，不修改原论文正文。

## 1. 结论边界

- Q01C主Q保持不变：11个主特征严格完整案例，三组组内等权、组间等权，`Q_valid=False`记录不删除、不填补。
- 扩展冲突稳定性资格：`PARTIALLY_STABLE`。A2全局判据通过1/4，A3通过3/4；共同有效域分别只有1和1个，少于预注册的4域，因此域级判据为`NOT_EVALUABLE`，且未观察到一致反转。
- 该结果支持“主Q在A1内可用、但现有A2/A3扩展不能证明完整结构迁移”的限定性结论；不得写成全局稳定或跨域已证实。

## 2. 文本核验口径

- A18候选仅完成join审计，未用于抽样；其与Q01C A1内容精确匹配仅1条，且冻结映射指南只有3个direct域，不能无模糊映射覆盖6域。
- 采用Q01C正式A1原始源作为直接文本源：51,230/51,230条按`key_sha256(id,sub_path)`一一匹配，文本非空率1.0。
- 作者完成表包含60个sealed `review_id`。其中可验证四项完整评分46条、部分评分1条、越界无效候选10条、无可用评分3条。所有统计均按成对有效记录计算，不插补、不重抽样、不生成代替作者判断的评分。

|核验项|结果|允许的解释|
|---|---|---|
|Q与overall quality Spearman|n=47, rho=0.032696, 95% CI [-0.253384, 0.315957], descriptive p=0.827293|相关性描述，不是外部真值| 
|Q与readability Spearman|n=47, rho=-0.293551, 95% CI [-0.568145, 0.000325], descriptive p=0.045214|方向仅为样本内秩相关| 
|Q与completeness Spearman|n=47, rho=0.055104, 95% CI [-0.290693, 0.362965], descriptive p=0.712964|方向仅为样本内秩相关| 
|Q与contamination Spearman|n=46, rho=0.058878, 95% CI [-0.252439, 0.371249], descriptive p=0.697513|污染分数越低越好，正相关表示Q越高污染越多| 
|高Q vs 低Q overall|n_high=22, n_low=25, median diff=0.000000, Cliff delta=0.101818 [-0.225500, 0.405455], p=0.535430|同域上下四分位定义的抽样层比较| 
|高Q vs 低Q readability|n_high=22, n_low=25, median diff=0.000000, Cliff delta=-0.092727 [-0.374636, 0.198182], p=0.561760|描述性组间差异| 
|高Q vs 低Q completeness|n_high=22, n_low=25, median diff=0.000000, Cliff delta=0.089091 [-0.241864, 0.410909], p=0.593650|描述性组间差异| 
|高Q vs 低Q contamination|n_high=22, n_low=24, median diff=0.000000, Cliff delta=-0.022727 [-0.310606, 0.265152], p=0.889490|越高表示污染越强| 
|高冲突 vs 低冲突人工异常率|n_high=13, n_low=33, risk diff=0.006993 [-0.284382, 0.298368], Fisher OR=0.972222, p=1.000000|异常定义为contamination≥1或overall≤2| 
|高冲突 vs 低冲突污染阳性率|n_high=13, n_low=33, risk diff=0.006993 [-0.284382, 0.300991], Fisher OR=0.972222, p=1.000000|contamination≥1| 
|高冲突 vs 低冲突低总体质量率|n_high=14, n_low=33, risk diff=0.041126 [-0.090909, 0.214286], Fisher OR=0.406250, p=0.511563|overall≤2| 

## 3. 对论文的冻结建议

1. Q1质量结论继续使用Q01C主Q；扩展冲突稳定性只可用于限制和敏感性说明，不能升级为跨A2/A3稳定结论。
2. A18文本核验不是全量强制验证；论文应明确其为可选附件候选审计，并标注当前作者文本核验有效样本未达到60条完整评分。
3. 人工相关性与组间差异结果应原样报告，包括弱相关、方向不一致或无差异；不得解释为因果，也不得据此修改主Q或重抽样。
4. 若主论文需要引用人工核验，应使用`manual_validation_statistics.csv`中的成对`n`和限制字段，不得抽取单一有利指标。

## 4. 证据入口

- 稳定性：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-G1\20260925T204300+08\stability_decision.json`
- 抽样seal：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-G1\20260925T204300+08\sampling_seal.json`
- 后作者统计：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-G1\20260925T223500+08\manual_validation_statistics.csv`
- 作者解析审计：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-G1\20260925T223500+08\manual_review_parse_audit.csv`
- 独立验收：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-G1\20260925T223500+08\verification.json`
